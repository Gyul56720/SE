"""Discord Markdown to PDF test."""

from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest

root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import discord_pdf

class TestDiscordPdf(unittest.TestCase):
    def test_format_markdown_as_pdf(self):
        sample_md = '# Header\nSample markdown content'
        pdf_path = discord_pdf.format_markdown_as_pdf(sample_md)
        try:
            self.assertTrue(os.path.exists(pdf_path), 'file must exist')
            self.assertGreater(os.path.getsize(pdf_path), 0, 'file must not be empty')
            with open(pdf_path, 'rb') as fp:
                self.assertEqual(fp.read(4), b'%PDF', 'header must be %PDF')
        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

if __name__ == '__main__':
    unittest.main()
