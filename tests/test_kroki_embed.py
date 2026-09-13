"""Tests for the stdlib Mermaid -> Kroki diagram embedding module."""

import base64
import hashlib
import html
import json
import re
import tempfile
import threading
import unittest
import zlib
from pathlib import Path
from urllib.request import Request, urlopen

from scripts.auditor_server import make_server
from scripts.kroki_embed import embed_diagrams


def _oversized_source() -> str:
    """A long, high-entropy mermaid "source" that never compresses under 4000 chars."""
    seed = b"kroki-oversized-diagram-test-seed"
    chunks = []
    for _ in range(200):
        seed = hashlib.sha256(seed).digest()
        chunks.append(seed.hex())
    return "".join(chunks)


class KrokiEmbedTests(unittest.TestCase):
    def test_single_fence_becomes_figure_and_roundtrips(self):
        source = "graph TD; A-->B"
        content = f"<h2>a</h2>\n```mermaid\n{source}\n```\n"
        converted, count = embed_diagrams(content)
        self.assertEqual(count, 1)
        self.assertIn('<figure class="ai-navi-diagram">', converted)
        match = re.search(r'src="[^"]*/mermaid/svg/([^"]+)"', converted)
        self.assertIsNotNone(match)
        decoded = zlib.decompress(base64.urlsafe_b64decode(match.group(1))).decode("utf-8")
        self.assertEqual(decoded.rstrip("\n"), source)

    def test_no_fence_is_unchanged(self):
        content = "<h2>a</h2><p>no diagrams here</p>"
        converted, count = embed_diagrams(content)
        self.assertEqual(converted, content)
        self.assertEqual(count, 0)

    def test_oversized_diagram_falls_back_to_pre(self):
        source = _oversized_source()
        content = f"```mermaid\n{source}\n```"
        converted, count = embed_diagrams(content)
        self.assertEqual(count, 0)
        self.assertIn('<pre class="mermaid-fallback">', converted)
        self.assertNotIn("kroki.io", converted)

    def test_pre_code_variant_is_matched_and_unescaped(self):
        source = "graph TD; A-->B"
        escaped = html.escape(source)
        content = f'<pre><code class="language-mermaid">{escaped}</code></pre>'
        converted, count = embed_diagrams(content)
        self.assertEqual(count, 1)
        match = re.search(r'src="[^"]*/mermaid/svg/([^"]+)"', converted)
        self.assertIsNotNone(match)
        decoded = zlib.decompress(base64.urlsafe_b64decode(match.group(1))).decode("utf-8")
        self.assertEqual(decoded, source)

    def test_embed_diagrams_endpoint_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.db"
            server = make_server("127.0.0.1", 0, db_path)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base_url = f"http://127.0.0.1:{server.server_address[1]}"
                source = "graph TD; A-->B"
                content = f"<h2>a</h2>\n```mermaid\n{source}\n```\n"
                direct_content, direct_count = embed_diagrams(content)

                request = Request(
                    base_url + "/embed-diagrams",
                    data=json.dumps({"content": content}).encode("utf-8"),
                    method="POST",
                )
                with urlopen(request) as response:
                    body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(body["diagrams"], direct_count)
                self.assertEqual(body["content"], direct_content)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == "__main__":
    unittest.main()
