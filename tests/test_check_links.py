from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_links import extract_markdown_links, validate_local_targets


class LinkCheckerTests(unittest.TestCase):
    def test_extracts_document_and_image_links(self) -> None:
        markdown = (
            "[guide](docs/USAGE.md#inputs)\n"
            "![badge](https://img.shields.io/badge/test-pass-green)\n"
            "[mail](mailto:security@example.com)\n"
        )
        self.assertEqual(
            extract_markdown_links(markdown),
            (
                "docs/USAGE.md#inputs",
                "https://img.shields.io/badge/test-pass-green",
                "mailto:security@example.com",
            ),
        )

    def test_reports_only_missing_local_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "README.md").write_text(
                "[exists](docs/guide.md#quick-start)\n[missing](docs/nope.md)\n",
                encoding="utf-8",
            )
            (root / "docs").mkdir()
            (root / "docs/guide.md").write_text("# Quick start\n", encoding="utf-8")

            self.assertEqual(
                validate_local_targets(root),
                ("README.md -> docs/nope.md",),
            )


if __name__ == "__main__":
    unittest.main()
