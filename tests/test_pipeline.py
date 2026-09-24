#!/usr/bin/env python3
"""
Automated Pipeline & Verification Test Suite for enterprise-blueprint-docs.
"""

import sys
import unittest
from pathlib import Path
import tempfile

# Add scripts directory to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from generate_pdf import (
    preprocess_markdown,
    extract_title_from_md,
    find_chrome_binary,
    build_html_document,
    convert_markdown_to_pdf,
    THEME_PRESETS,
)

class TestEnterpriseBlueprintDocs(unittest.TestCase):

    def test_preprocess_markdown_alerts(self):
        sample_md = "> [!NOTE]\n> This is a test note alert.\n> Line 2."
        processed = preprocess_markdown(sample_md)
        self.assertIn('<div class="gcp-callout note">', processed)
        self.assertIn('This is a test note alert.', processed)
        self.assertIn('Line 2.', processed)

    def test_preprocess_pagebreak(self):
        sample_md = "Section 1\n<!-- pagebreak -->\nSection 2"
        processed = preprocess_markdown(sample_md)
        self.assertIn('<div class="page-break"></div>', processed)

    def test_extract_title(self):
        sample_md = "# Solution Blueprint: Project Alpha\n\nSome body text."
        title = extract_title_from_md(sample_md, "Fallback")
        self.assertEqual(title, "Solution Blueprint: Project Alpha")

    def test_find_chrome_binary(self):
        chrome_bin = find_chrome_binary()
        self.assertIsNotNone(chrome_bin, "Chrome binary should be located on system")
        self.assertTrue(Path(chrome_bin).exists())

    def test_build_html_document(self):
        sample_md = "# Test Document\n\nHello world!"
        theme = THEME_PRESETS["industry"]
        html = build_html_document(sample_md, "Test Title", theme)
        self.assertIn("<title>Test Title</title>", html)
        self.assertIn(theme["brand_primary"], html)
        self.assertIn("marked.parse", html)
        self.assertIn("mermaid.initialize", html)
        self.assertIn("renderMathInElement", html)

    def test_end_to_end_conversion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            test_md = tmp_path / "TEST_BLUEPRINT.md"
            test_pdf = tmp_path / "TEST_BLUEPRINT.pdf"
            
            test_md.write_text("""# Solution Blueprint: Automated Test

## Section 1: Overview
> [!NOTE]
> Architecture statement.

```mermaid
graph LR
    A[Input] --> B[Output]
```

Math formula:
$$S(X, Y) = \\frac{|X \\cap Y|}{|X \\cup Y|}$$
""", encoding="utf-8")

            theme = THEME_PRESETS["default"]
            success, gen_html, gen_pdf = convert_markdown_to_pdf(
                input_md=test_md,
                output_pdf=test_pdf,
                theme_cfg=theme,
                verbose=False
            )
            self.assertTrue(success)
            self.assertIsNotNone(gen_pdf)
            self.assertTrue(gen_pdf.exists())
            self.assertGreater(gen_pdf.stat().st_size, 1000)

if __name__ == "__main__":
    unittest.main()
