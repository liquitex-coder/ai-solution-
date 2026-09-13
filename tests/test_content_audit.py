"""Tests for the content_audit WARN-only drift fixes (requirements §32-1)."""

import unittest

from scripts.content_audit import audit

FILLER = ("AIツールの活用は業務の効率化に役立つ場面が増えています。"
          "導入の際は自社の課題を整理し、小さく試してから広げるのが安全です。"
          "運用ルールとレビュー体制をあわせて整備することが重要です。")
LONG = FILLER * 3


def _quote_ratio_content(quote_len: int) -> str:
    """§32-1 D1: an article whose blockquote share is quote_len chars long."""
    quote_text = LONG[:quote_len]
    return (
        f"<h2>導入の背景</h2><p>{FILLER}</p>"
        f"<h2>専門家の見解</h2><blockquote>{quote_text}</blockquote>"
        f"<h2>まとめと出典</h2><p>{FILLER}詳細は"
        f'<a href="https://example.com/source-article">出典</a>を参照してください。</p>'
    )


class QuoteRatioBoundaryTests(unittest.TestCase):
    def test_30_percent_quote_share_passes(self):
        result = audit(_quote_ratio_content(92))
        self.assertEqual(result["verdict"], "PASS")

    def test_35_percent_quote_share_fails(self):
        result = audit(_quote_ratio_content(115))
        self.assertEqual(result["verdict"], "FAIL")


class VerbatimCopyWarningTests(unittest.TestCase):
    QUOTE_DIFFERS = "生成AIの導入は業務効率化に直結し多くの企業が注目している最新の技術動向である"
    QUOTE_IDENTICAL = "生成AIの導入は業務効率化に直結する"

    def _content(self, quote: str) -> str:
        return (
            "<h2>A</h2><h2>B</h2><h2>C</h2>"
            f"<blockquote>{quote}</blockquote>"
            '<a href="https://example.test/src">source</a>'
        )

    def test_warns_when_quote_is_altered_from_source(self):
        content = self._content(self.QUOTE_DIFFERS)
        source_text = ("全く関係のない別の話題についての文章がここに書かれています。"
                        "天気の話や食べ物の話など、引用文とは無関係な内容です。")
        result = audit(content, source_text=source_text, source_lang="ja")
        self.assertTrue(any(r.startswith("WARN:VERBATIM_COPY") for r in result["reasons"]))

    def test_no_warning_when_quote_is_verbatim_in_source(self):
        content = self._content(self.QUOTE_IDENTICAL)
        source_text = f"前置き部分のテキストです。{self.QUOTE_IDENTICAL}という記述がそのまま含まれています。"
        result = audit(content, source_text=source_text, source_lang="ja")
        self.assertFalse(any(r.startswith("WARN:VERBATIM_COPY") for r in result["reasons"]))

    def test_warning_never_changes_verdict(self):
        content = self._content(self.QUOTE_DIFFERS)
        source_text = ("全く関係のない別の話題についての文章がここに書かれています。"
                        "天気の話や食べ物の話など、引用文とは無関係な内容です。")
        with_source = audit(content, source_text=source_text, source_lang="ja")
        without_source = audit(content)
        self.assertTrue(any(r.startswith("WARN:VERBATIM_COPY") for r in with_source["reasons"]))
        self.assertEqual(with_source["verdict"], without_source["verdict"])


class TranslationLabelWarningTests(unittest.TestCase):
    SOURCE_URL = "https://example.cn/article"

    def test_zh_without_label_warns(self):
        content = "<h2>A</h2><h2>B</h2><h2>C</h2><p>本文には翻訳である旨の記載がありません。</p>"
        result = audit(content, source_urls=[self.SOURCE_URL], source_lang="zh")
        self.assertIn("WARN:MISSING_TRANSLATION_LABEL", result["reasons"])

    def test_zh_with_label_and_url_has_no_warning(self):
        content = (f"<h2>A</h2><h2>B</h2><h2>C</h2>"
                   f"<p>本記事は{self.SOURCE_URL}の翻訳です。</p>")
        result = audit(content, source_urls=[self.SOURCE_URL], source_lang="zh")
        self.assertNotIn("WARN:MISSING_TRANSLATION_LABEL", result["reasons"])

    def test_ja_default_never_checks_translation_label(self):
        content = "<h2>A</h2><h2>B</h2><h2>C</h2><p>翻訳ラベルの言及なし。</p>"
        result = audit(content)
        self.assertNotIn("WARN:MISSING_TRANSLATION_LABEL", result["reasons"])


if __name__ == "__main__":
    unittest.main()
