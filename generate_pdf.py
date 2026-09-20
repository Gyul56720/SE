import sys
import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Nanum fonts
font_dir = "/usr/share/fonts/truetype/nanum"
pdfmetrics.registerFont(TTFont("NanumGothic", os.path.join(font_dir, "NanumGothic.ttf")))
pdfmetrics.registerFont(TTFont("NanumGothicBold", os.path.join(font_dir, "NanumGothicBold.ttf")))
pdfmetrics.registerFont(TTFont("NanumSquareB", os.path.join(font_dir, "NanumSquareB.ttf")))

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("NanumGothic", 8)
        self.setFillColor(colors.HexColor("#718096"))
        page_text = f"{self._pageNumber} / {page_count}"
        self.drawRightString(A4[0] - 40, 25, page_text)
        self.drawString(40, 25, "EECS-IP-001 | Semiconductor IP Design (한국어 번역본)")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(40, 36, A4[0] - 40, 36)
        self.restoreState()

def clean_md(text):
    # Convert markdown formatting to reportlab XML tags
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    text = text.replace('$', '')
    # escape ampersands if not part of xml entities
    text = re.sub(r'&(?![a-zA-Z]+;)', '&amp;', text)
    return text

def build_pdf(md_file, pdf_file):
    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='NanumSquareB',
        fontSize=18,
        leading=24,
        textColor=colors.HexColor('#1A365D'),
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='NanumGothic',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#4A5568'),
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='NanumGothicBold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#2B6CB0'),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='NanumGothicBold',
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor('#2D3748'),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    h3_style = ParagraphStyle(
        'Heading3_Custom',
        parent=styles['Normal'],
        fontName='NanumGothicBold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#2D3748'),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='NanumGothic',
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor('#1A202C'),
        spaceAfter=5
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3
    )

    callout_style = ParagraphStyle(
        'Callout_Custom',
        parent=body_style,
        fontName='NanumGothic',
        fontSize=8.5,
        leading=12.5,
        textColor=colors.HexColor('#2C5282'),
        backColor=colors.HexColor('#EBF8FF'),
        borderColor=colors.HexColor('#3182CE'),
        borderWidth=0.8,
        borderPadding=6,
        spaceBefore=6,
        spaceAfter=6
    )

    cell_style = ParagraphStyle(
        'Cell_Custom',
        parent=styles['Normal'],
        fontName='NanumGothic',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#2D3748')
    )

    cell_bold_style = ParagraphStyle(
        'Cell_Bold_Custom',
        parent=styles['Normal'],
        fontName='NanumGothicBold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1A202C')
    )

    story = []

    with open(md_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    in_table = False
    table_data = []

    for line in lines:
        raw_line = line
        line = line.strip()

        # Handle tables
        if line.startswith('|'):
            in_table = True
            if '---' in line:
                continue
            parts = [p.strip() for p in line.split('|')[1:-1]]
            row_cells = []
            for p in parts:
                clean_p = clean_md(p)
                if any(k in p for k in ['단계', '계층', 'Input', 'Role', 'Phase', 'Unit', '입력', '출력', '주요']):
                    row_cells.append(Paragraph(clean_p, cell_bold_style))
                else:
                    row_cells.append(Paragraph(clean_p, cell_style))
            table_data.append(row_cells)
            continue
        else:
            if in_table and table_data:
                col_num = len(table_data[0])
                if col_num == 4:
                    col_widths = [100, 110, 130, 170]
                elif col_num == 3:
                    col_widths = [130, 180, 200]
                else:
                    col_widths = None
                t = Table(table_data, colWidths=col_widths)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EDF2F7')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#1A202C')),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
                    ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor('#A0AEC0')),
                    ('TOPPADDING', (0,0), (-1,-1), 4),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ]))
                story.append(Spacer(1, 4))
                story.append(t)
                story.append(Spacer(1, 6))
                in_table = False
                table_data = []

        if not line:
            story.append(Spacer(1, 3))
            continue

        if line.startswith('# '):
            clean_text = clean_md(line[2:])
            story.append(Paragraph(clean_text, title_style))
            story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2B6CB0'), spaceBefore=2, spaceAfter=8))
        elif line.startswith('## '):
            clean_text = clean_md(line[3:])
            story.append(Paragraph(clean_text, h1_style))
        elif line.startswith('### '):
            clean_text = clean_md(line[4:])
            story.append(Paragraph(clean_text, h2_style))
        elif line.startswith('#### '):
            clean_text = clean_md(line[5:])
            story.append(Paragraph(clean_text, h3_style))
        elif line.startswith('> '):
            clean_text = clean_md(line[2:])
            story.append(Paragraph(clean_text, callout_style))
        elif line.startswith('- ') or line.startswith('* '):
            clean_text = clean_md(line[2:])
            story.append(Paragraph(f"• {clean_text}", bullet_style))
        else:
            clean_text = clean_md(line)
            story.append(Paragraph(clean_text, body_style))

    if in_table and table_data:
        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EDF2F7')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
            ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor('#A0AEC0')),
        ]))
        story.append(t)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {pdf_file}")

if __name__ == '__main__':
    build_pdf('translations/IP_Design_Textbook_KR.md', 'translations/IP_Design_Textbook_KR.pdf')
