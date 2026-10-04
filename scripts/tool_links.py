#!/usr/bin/env python3
"""Deterministic internal links to tool pages (requirements §35-13, rule R1).

link_tools() inserts one /tools/{slug}/ link at the first mention of each catalog
tool in article HTML. It never touches text inside an existing <a>, a heading,
a <blockquote> (quotes must stay unaltered, §17 ⑤) or <code>/<pre>. LLM-free.
"""

from __future__ import annotations

import html
import json
import os
import pathlib
import re
from typing import Any, Iterable, Mapping

ROOT = pathlib.Path(__file__).resolve().parent.parent
CATALOG_CANDIDATES = (ROOT / "data" / "tools.json", ROOT / "catalog" / "tools.json")
SKIP_TAGS = {"a", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "code", "pre"}
TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)[^>]*?(/?)>")


def load_catalog(env: Mapping[str, str] | None = None) -> list[dict[str, Any]] | None:
    """Tools from AINAVI_TOOLS_FILE, data/tools.json, then catalog/tools.json; None if none load."""
    env = os.environ if env is None else env
    candidates: list[pathlib.Path] = []
    if env.get("AINAVI_TOOLS_FILE"):
        candidates.append(pathlib.Path(env["AINAVI_TOOLS_FILE"]))
    candidates.extend(CATALOG_CANDIDATES)
    for path in candidates:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        tools = data.get("tools") if isinstance(data, dict) else None
        if isinstance(tools, list) and all(
                isinstance(t, dict) and isinstance(t.get("slug"), str)
                and isinstance(t.get("name"), str) for t in tools):
            return tools
    return None


def _name_pattern(name: str) -> re.Pattern[str]:
    escaped = re.escape(name)
    # Latin names must not be part of a longer alphanumeric word (e.g. "n8n" in "n8nx").
    return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])")


def _segments(content: str) -> Iterable[tuple[bool, str]]:
    """Yield (is_tag, text) pieces of the HTML in order."""
    pos = 0
    for match in TAG_RE.finditer(content):
        if match.start() > pos:
            yield False, content[pos:match.start()]
        yield True, match.group(0)
        pos = match.end()
    if pos < len(content):
        yield False, content[pos:]


def _linkable_text(content: str) -> Iterable[tuple[int, bool, str]]:
    """Yield (index, linkable, piece); text is linkable only outside SKIP_TAGS."""
    depth = 0
    for index, (is_tag, piece) in enumerate(_segments(content)):
        if is_tag:
            match = TAG_RE.match(piece)
            name = match.group(2).lower() if match else ""
            if name in SKIP_TAGS and not match.group(3):
                depth += -1 if match.group(1) else 1
                depth = max(depth, 0)
            yield index, False, piece
        else:
            yield index, depth == 0, piece


def link_tools(content: str, tools: list[Mapping[str, Any]]) -> tuple[str, list[str]]:
    """Insert a link at the first linkable mention of each tool; returns (html, linked slugs)."""
    pieces = [piece for _, _, piece in _linkable_text(content)]
    flags = [linkable for _, linkable, _ in _linkable_text(content)]
    linked: list[str] = []
    already = {m.group(1) for m in re.finditer(r'href="/tools/([^/"]+)/"', content)}
    # longer names first so "Stable Diffusion" wins over a shorter overlapping name
    for tool in sorted(tools, key=lambda t: -len(t["name"])):
        slug, name = tool["slug"], tool["name"]
        if slug in already:
            continue
        pattern = _name_pattern(name)
        for i, piece in enumerate(pieces):
            if not flags[i]:
                continue
            match = pattern.search(piece)
            if not match:
                continue
            anchor = (f'<a href="/tools/{html.escape(slug)}/">'
                      f"{match.group(0)}</a>")
            before, after = piece[:match.start()], piece[match.end():]
            # split so the inserted anchor is never re-scanned by a later tool
            pieces[i:i + 1] = [before, anchor, after]
            flags[i:i + 1] = [True, False, True]
            linked.append(slug)
            break
    return "".join(pieces), linked


def missing_tool_links(content: str, tools: list[Mapping[str, Any]]) -> list[str]:
    """Slugs of tools mentioned in linkable text but never linked to /tools/{slug}/."""
    linked = {m.group(1) for m in re.finditer(r'href="/tools/([^/"]+)/"', content)}
    text = "\n".join(piece for _, linkable, piece in _linkable_text(content) if linkable)
    missing = []
    for tool in tools:
        if tool["slug"] not in linked and _name_pattern(tool["name"]).search(text):
            missing.append(tool["slug"])
    return sorted(missing)
