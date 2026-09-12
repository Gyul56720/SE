import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

def test_goal_pdf_discord():
    import discord_pdf
    pdf_path = discord_pdf.format_markdown_as_pdf("# Test Title\nSome content here")
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 0

if __name__ == "__main__":
    test_goal_pdf_discord()
    print("OK")
