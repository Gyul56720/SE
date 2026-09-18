import os
import subprocess
import tempfile

def format_markdown_as_pdf(markdown_text: str, output_path: str = None) -> str:
    """Markdown 텍스트를 PDF로 변환한다. weasyprint 또는 pandoc / wkhtmltopdf 사용 시도."""
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
    
    # 1. try pandoc
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tf:
            tf.write(markdown_text)
            md_file = tf.name
        try:
            subprocess.run(["pandoc", md_file, "-o", output_path], check=True, capture_output=True)
            return output_path
        finally:
            if os.path.exists(md_file):
                os.remove(md_file)
    except Exception:
        pass

    # 2. fallback: simple reportlab or weasyprint if available
    try:
        import weasyprint
        weasyprint.HTML(string=markdown_text).write_pdf(output_path)
        return output_path
    except Exception:
        pass

    # 3. fallback: write plain text / simple pdf via reportlab or raise
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    y = height - 40
    for line in markdown_text.splitlines():
        if y < 40:
            c.showPage()
            y = height - 40
        c.drawString(40, y, line[:100])
        y -= 15
    c.save()
    return output_path

