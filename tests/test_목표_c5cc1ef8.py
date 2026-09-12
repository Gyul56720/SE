"""Discord Markdown to PDF test."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add repo root to sys.path
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import discord_pdf
import discord_bot_server

sample_md = '# Header' + chr(10) + 'Sample markdown content'

# Check if discord_pdf provides format_markdown_as_pdf
pdf_path = discord_pdf.format_markdown_as_pdf(sample_md)
assert os.path.exists(pdf_path), 'file must exist'
assert os.path.getsize(pdf_path) > 0, 'file must not be empty'
try:
    with open(pdf_path, 'rb') as fp:
        assert fp.read(4) == b'%PDF', 'header must be %PDF'
finally:
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

print('OK')
