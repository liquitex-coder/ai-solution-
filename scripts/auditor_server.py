#!/usr/bin/env python3
"""HTTP callee for the n8n Claim Auditor Gate."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

try:
    from . import content_audit, memory_init
except ImportError:  # Direct execution leaves scripts/ as sys.path[0].
    import content_audit
    import memory_init


DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "memory.db"


class AuditorHTTPServer(ThreadingHTTPServer):
    """Threaded server with optional, lock-protected memory storage."""

    def __init__(self, address: tuple[str, int], handler: type[BaseHTTPRequestHandler],
                 db_path: Path):
        super().__init__(address, handler)
        self.db_path = db_path
        self.db_lock = threading.Lock()
        self.memory_db = False
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
            print(f"auditor memory database write failed: {exc}", file=sys.stderr,
                  flush=True)
            self.memory_db = False
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
        "service": "claim-auditor-gate",
        "memory_db": handler.server.memory_db,
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

    result = content_audit.audit(content, source_urls)
    verdict = result["verdict"]
    fact_id = None
    if verdict != "PASS":
        first_reason = result["reasons"][0] if result["reasons"] else ""
        pieces = first_reason.split(":")
        fail_reason = ":".join(pieces[:2]) if len(pieces) >= 3 else first_reason
        fact_id = handler.server.store_fact(
            content=content[:500],
            source_url=source_urls[0] if source_urls else "",
            confidence="UNVERIFIABLE" if verdict == "UNVERIFIABLE" else "LOW",
            verdict=verdict,
            fail_reason=fail_reason,
            skill_ref=skill_ref,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        )
    handler._send_json(200, {
        "verdict": verdict,
        "reasons": result["reasons"],
        "skill_ref": skill_ref,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "fact_id": fact_id,
    })
    return 200, verdict, skill_ref


ROUTES: dict[tuple[str, str], Callable[[AuditorRequestHandler], tuple[Any, Any, Any]]] = {
    ("GET", "/health"): health,
    ("POST", "/audit"): audit,
}


def make_server(bind: str, port: int, db_path: str | Path) -> ThreadingHTTPServer:
    """Create the gate server; an unavailable DB leaves auditing available."""
    return AuditorHTTPServer((bind, port), AuditorRequestHandler, Path(db_path))


def main() -> None:
    bind = os.environ.get("CLAIM_AUDITOR_BIND", "0.0.0.0")
    port = int(os.environ.get("CLAIM_AUDITOR_PORT", "8090"))
    configured_db = Path(os.environ.get("CLAIM_MEMORY_DB", "data/memory.db"))
    db_path = configured_db if configured_db.is_absolute() else DEFAULT_DB.parent.parent / configured_db
    server = make_server(bind, port, db_path)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
