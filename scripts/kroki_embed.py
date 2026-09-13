#!/usr/bin/env python3
"""Mermaid -> Kroki diagram embedding (requirements §31). Stdlib only, no network.

Usage:
  python3 scripts/kroki_embed.py --stdin
  python3 scripts/kroki_embed.py --content-file article.html
As a library: embed_diagrams(html, base_url=None) -> (converted_html, diagram_count)
"""

from __future__ import annotations

import argparse
import base64
import html as html_lib
import os
import re
import sys
import zlib

DEFAULT_KROKI_BASE_URL = "https://kroki.io"
MAX_URL_LENGTH = 4000

_FENCE_RE = re.compile(
    r"```mermaid\n(?P<fence>.*?)```"
    r'|<pre><code class="language-mermaid">(?P<precode>.*?)</code></pre>',
    re.DOTALL,
)


def _encode(source: str) -> str:
    compressed = zlib.compress(source.encode("utf-8"), 9)
    return base64.urlsafe_b64encode(compressed).decode("ascii")


def embed_diagrams(html: str, base_url: str | None = None) -> tuple[str, int]:
    """Replace mermaid fences with Kroki-rendered <figure> embeds.

    Conversion never touches the network: rendering happens in the reader's
    browser via a GET to the Kroki URL embedded in the <img> tag.
    """
    resolved_base = (
        base_url if base_url is not None
        else os.environ.get("KROKI_BASE_URL", DEFAULT_KROKI_BASE_URL)
    )
    count = 0

    def _replace(match: re.Match) -> str:
        nonlocal count
        source = match.group("fence")
        if source is None:
            source = html_lib.unescape(match.group("precode"))
        url = f"{resolved_base}/mermaid/svg/{_encode(source)}"
        if len(url) > MAX_URL_LENGTH:
            return f'<pre class="mermaid-fallback">{html_lib.escape(source)}</pre>'
        count += 1
        return (f'<figure class="ai-navi-diagram">'
                f'<img src="{url}" alt="図解" loading="lazy"></figure>')

    converted = _FENCE_RE.sub(_replace, html)
    return converted, count


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--content-file")
    args = ap.parse_args()
    if args.stdin:
        content = sys.stdin.read()
    elif args.content_file:
        content = open(args.content_file, encoding="utf-8").read()
    else:
        ap.error("--stdin or --content-file required")
    converted, count = embed_diagrams(content)
    sys.stdout.write(converted)
    print(count, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
