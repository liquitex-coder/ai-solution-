#!/usr/bin/env python3
"""HTTP callee for the n8n Auditor Gate (ai-solution's own content gate)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

try:
    from . import content_audit, kroki_embed, memory_init
except ImportError:  # Direct execution leaves scripts/ as sys.path[0].
    import content_audit
    import kroki_embed
    import memory_init


DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "memory.db"


class AuditorHTTPServer(ThreadingHTTPServer):
    """Threaded server with optional, lock-protected memory storage."""

    def __init__(self, address: tuple[str, int], handler: type[BaseHTTPRequestHandler],
                 db_path: Path, token: str = ""):
        super().__init__(address, handler)
        self.db_path = db_path
        self.token = token
        self.db_lock = threading.Lock()
        self.memory_db = False
        if not self.token:
            print("AINAVI_GATE_TOKEN not set - unauthenticated mode (sandbox only)",
                  file=sys.stderr, flush=True)
        try:
            conn = memory_init.connect(db_path)
            try:
                memory_init.ensure_schema(conn)
            finally:
                conn.close()
            self.memory_db = True
        except Exception as exc:
            print(f"auditor memory database unavailable: {exc}", file=sys.stderr,
                  flush=True)

    def store_fact(self, **kwargs: Any) -> int | None:
        if not self.memory_db:
            return None
        try:
            with self.db_lock:
                conn = memory_init.connect(self.db_path)
                try:
                    return memory_init.insert_fact(conn, **kwargs)
                finally:
                    conn.close()
        except Exception as exc:
            # Transient write failures (e.g. "database is locked") must not
            # permanently disable future writes; only startup availability
            # (self.memory_db, set once in __init__) gates /health.
            print(f"auditor memory database write failed: {exc}", file=sys.stderr,
                  flush=True)
            return None

    def find_prior_fact(self, content_hash: str) -> int | None:
        """§32-1 D5: look up a prior non-PASS verdict for this exact content hash."""
        if not self.memory_db:
            return None
        try:
            with self.db_lock:
                conn = memory_init.connect(self.db_path)
                try:
                    row = conn.execute(
                        "SELECT id FROM facts WHERE content_hash = ? AND verdict != 'PASS' "
                        "ORDER BY id DESC LIMIT 1",
                        (content_hash,),
                    ).fetchone()
                    return row[0] if row else None
                finally:
                    conn.close()
        except Exception as exc:
            # A lookup failure must never block the gate: treat as "not found".
            print(f"auditor memory database read failed: {exc}", file=sys.stderr,
                  flush=True)
            return None

    def server_close(self) -> None:
        super().server_close()


class AuditorRequestHandler(BaseHTTPRequestHandler):
    server: AuditorHTTPServer

    def log_message(self, format: str, *args: object) -> None:
        """Suppress BaseHTTPRequestHandler's body-adjacent stderr logging."""

    def do_GET(self) -> None:
        self._dispatch()

    def do_POST(self) -> None:
        self._dispatch()

    def _authorized(self) -> bool:
        token = self.server.token
        if not token:
            return True
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return False
        return hmac.compare_digest(
            header[len("Bearer "):].encode("utf-8"), token.encode("utf-8"))

    def _dispatch(self) -> None:
        started = time.monotonic()
        path = urlsplit(self.path).path
        status = 404
        verdict = None
        skill_ref = None
        try:
            route = ROUTES.get((self.command, path))
            if route is None:
                self._send_json(404, {"error": "unknown path or method"})
            elif (self.command, path) in AUTH_REQUIRED_ROUTES and not self._authorized():
                status = 401
                self._send_json(401, {"error": "unauthorized"})
            else:
                status, verdict, skill_ref = route(self)
        except Exception as exc:
            # A malformed request must not terminate a worker thread or expose details.
            print(f"auditor request handling failed: {exc}", file=sys.stderr, flush=True)
            status = 400
            self._send_json(status, {"error": "invalid request"})
        finally:
            elapsed = round((time.monotonic() - started) * 1000, 3)
            print(json.dumps({
                "path": path,
                "status": status,
                "verdict": verdict,
                "skill_ref": skill_ref,
                "ms": elapsed,
            }, ensure_ascii=False), flush=True)

    def _read_json(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if length <= 0:
            return None
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def _send_json(self, status: int, body: dict[str, Any]) -> None:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def health(handler: AuditorRequestHandler) -> tuple[int, None, None]:
    handler._send_json(200, {
        "status": "ok",
        "service": "ainavi-auditor-gate",
        "memory_db": handler.server.memory_db,
        "auth": bool(handler.server.token),
    })
    return 200, None, None


def audit(handler: AuditorRequestHandler) -> tuple[int, str | None, str | None]:
    payload = handler._read_json()
    if payload is None:
        handler._send_json(400, {"error": "invalid JSON body"})
        return 400, None, None
    content = payload.get("content")
    if not isinstance(content, str):
        handler._send_json(400, {"error": "content must be a string"})
        return 400, None, None

    source_urls = payload.get("source_urls", [])
    if not isinstance(source_urls, list):
        source_urls = []
    source_urls = [url for url in source_urls if isinstance(url, str) and url]
    skill_ref = payload.get("skill_ref", "")
    if not isinstance(skill_ref, str):
        skill_ref = ""
    source_text = payload.get("source_text")
    if not isinstance(source_text, str):
        source_text = None
    source_lang = payload.get("source_lang")
    if not isinstance(source_lang, str):
        source_lang = None

    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    # §32-1 D5: a previously rejected submission is still re-scored (verdict
    # is never skipped), but resubmitting the identical content is flagged as
    # a WARN and does not write a second facts row for the same hash.
    rejected_fact_id = handler.server.find_prior_fact(content_hash)

    result = content_audit.audit(content, source_urls, source_text, source_lang)
    verdict = result["verdict"]
    reasons = list(result["reasons"])
    fact_id = rejected_fact_id
    if rejected_fact_id is not None:
        reasons.append(f"WARN:ALREADY_REJECTED:{rejected_fact_id}")
    elif verdict != "PASS":
        first_reason = reasons[0] if reasons else ""
        pieces = first_reason.split(":")
        fail_reason = ":".join(pieces[:2]) if len(pieces) >= 3 else first_reason
        fact_id = handler.server.store_fact(
            content=content[:500],
            source_url=source_urls[0] if source_urls else "",
            confidence="UNVERIFIABLE" if verdict == "UNVERIFIABLE" else "LOW",
            verdict=verdict,
            fail_reason=fail_reason,
            skill_ref=skill_ref,
            content_hash=content_hash,
        )
    handler._send_json(200, {
        "verdict": verdict,
        "reasons": reasons,
        "skill_ref": skill_ref,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "fact_id": fact_id,
    })
    return 200, verdict, skill_ref


def embed_diagrams_route(handler: AuditorRequestHandler) -> tuple[int, None, None]:
    payload = handler._read_json()
    if payload is None:
        handler._send_json(400, {"error": "invalid JSON body"})
        return 400, None, None
    content = payload.get("content")
    if not isinstance(content, str):
        handler._send_json(400, {"error": "content must be a string"})
        return 400, None, None

    converted, count = kroki_embed.embed_diagrams(content)
    handler._send_json(200, {"content": converted, "diagrams": count})
    return 200, None, None


ROUTES: dict[tuple[str, str], Callable[[AuditorRequestHandler], tuple[Any, Any, Any]]] = {
    ("GET", "/health"): health,
    ("POST", "/audit"): audit,
    ("POST", "/embed-diagrams"): embed_diagrams_route,
}

# §28-2 (v2.4): write paths require auth when AINAVI_GATE_TOKEN is set; /health never does.
AUTH_REQUIRED_ROUTES = {("POST", "/audit"), ("POST", "/embed-diagrams")}


def make_server(bind: str, port: int, db_path: str | Path, token: str = "") -> ThreadingHTTPServer:
    """Create the gate server; an unavailable DB leaves auditing available."""
    return AuditorHTTPServer((bind, port), AuditorRequestHandler, Path(db_path), token)


def resolve_port(env: Mapping[str, str]) -> int:
    """§28-2 port row: AINAVI_GATE_PORT -> PORT (Render/Fly.io) -> 8090."""
    return int(env.get("AINAVI_GATE_PORT") or env.get("PORT") or "8090")


def main() -> None:
    bind = os.environ.get("AINAVI_GATE_BIND", "0.0.0.0")
    port = resolve_port(os.environ)
    token = os.environ.get("AINAVI_GATE_TOKEN", "")
    configured_db = Path(os.environ.get("AINAVI_GATE_MEMORY_DB", "data/memory.db"))
    db_path = configured_db if configured_db.is_absolute() else DEFAULT_DB.parent.parent / configured_db
    server = make_server(bind, port, db_path, token)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
