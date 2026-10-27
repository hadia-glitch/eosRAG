"""Render the versioned Markdown methods paper as a readable standalone PDF."""
from pathlib import Path
import re
import shutil
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Flowable, KeepTogether, Table, TableStyle, Image, PageBreak
from PIL import Image as PILImage

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/research/manuscript.md'
OUTPUT = ROOT / 'output/pdf/neoguard-eos-research-paper.pdf'
TEAL = colors.HexColor('#087F8C')
NAVY = colors.HexColor('#16324F')


class Architecture(Flowable):
    def __init__(self):
        super().__init__()
        self.width, self.height = 475, 180

    def draw(self):
        c = self.canv
        rows = [
            'Clinician session -> encounter ownership -> field-limited case history',
            'Prediction branch: causal features -> pinned calibrated ML -> estimate / abstain',
            'Evidence branch: reviewed registry -> text + vector [+ concept graph] -> passages',
            'LangGraph: structured claims -> source auditor || safety auditor -> release gate',
            'Clinician review: traceable discussion points OR explicit withholding',
        ]
        for i, row in enumerate(rows):
            y = 150 - i * 31
            c.setFillColor(colors.HexColor('#F0F7F8') if i < 4 else colors.HexColor('#E7EFF7'))
            c.setStrokeColor(TEAL if i < 4 else NAVY)
            c.roundRect(0, y, self.width, 24, 4, fill=1, stroke=1)
            c.setFillColor(NAVY)
            c.setFont('Helvetica', 8.5)
            c.drawCentredString(self.width / 2, y + 9, row)
            if i in (0, 2, 3):
                c.setStrokeColor(TEAL)
                c.line(self.width/2, y, self.width/2, y-6)
        c.setFont('Helvetica-Oblique', 8)
        c.drawString(0, 0, 'Figure 1. Separate prediction and evidence branches share authorized clinical observations.')


def markup(text):
    text = escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    return text


def header(canvas, doc):
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.setFont('Helvetica-Bold', 8)
    canvas.drawString(54, h - 30, 'NEOGUARD EOS  /  RESEARCH SOFTWARE EVALUATION')
    canvas.setStrokeColor(TEAL)
    canvas.setLineWidth(1)
    canvas.line(54, h - 39, w - 54, h - 39)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#536272'))
    canvas.drawString(54, 27, getattr(doc,'report_date','25 October 2026')+'  |  Original research software report')
    canvas.drawRightString(w - 54, 27, str(doc.page))
    canvas.restoreState()


def main(source=SOURCE,output=OUTPUT,*,copy_alias=True,include_architecture=True,report_date='25 October 2026',references_new_page=True):
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = {
        'title': ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=21, leading=26, textColor=NAVY, spaceAfter=16),
        'h2': ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=NAVY, spaceBefore=16, spaceAfter=7, keepWithNext=True),
        'h3': ParagraphStyle('h3', fontName='Helvetica-Bold', fontSize=10.5, leading=14, textColor=NAVY, spaceBefore=9, spaceAfter=6, keepWithNext=True),
        'body': ParagraphStyle('body', fontName='Times-Roman', fontSize=10.5, leading=14.5, spaceAfter=8, splitLongWords=True,allowWidows=0,allowOrphans=0),
        'meta': ParagraphStyle('meta', fontName='Helvetica', fontSize=9, leading=13, textColor=TEAL, spaceAfter=12),
        'reference': ParagraphStyle('reference', fontName='Times-Roman', fontSize=9, leading=11, spaceAfter=4, splitLongWords=True),
        'table': ParagraphStyle('table',fontName='Helvetica',fontSize=7.5,leading=10,splitLongWords=True),
        'caption': ParagraphStyle('caption',fontName='Helvetica',fontSize=8.5,leading=11,textColor=NAVY,spaceBefore=8,spaceAfter=7,keepWithNext=True),
    }
    story = []
    in_references = False
    for block in re.split(r'\n\s*\n', source.read_text(encoding='utf-8').strip()):
        text = ' '.join(block.splitlines())
        if text.startswith('# '):
            story.append(Paragraph(markup(text[2:]), styles['title']))
        elif text.startswith('## '):
            in_references = text == '## References'
            if in_references and references_new_page:story.append(PageBreak())
            heading=Paragraph(markup(text[3:]),styles['h2'])
            if text.startswith('## 4.') and include_architecture:
                story.append(KeepTogether([heading,Spacer(1,8),Architecture(),Spacer(1,8)]))
            else:story.append(heading)
        elif text.startswith('### '):
            story.append(Paragraph(markup(text[4:]),styles['h3']))
        elif text=='[[ARCHITECTURE]]':
            pass  # Kept together with the section heading above.
        elif text.startswith('|'):
            rows=[]
            for row in block.splitlines():
                cells=[c.strip() for c in row.strip().strip('|').split('|')]
                if all(re.fullmatch(r':?-+:?',c) for c in cells):continue
                rows.append([Paragraph(markup(c),styles['table']) for c in cells])
            count=len(rows[0]);width=A4[0]-108
            weights=[1.6]+[1]*(count-1) if count>2 else [1,1.5]
            headings=[c.strip() for c in block.splitlines()[0].strip().strip('|').split('|')]
            if headings==['Guideline','Arm','Judged / quality N','Grounding','Fidelity','Completeness','Actionability','Uncertainty','Unsafe claims']:
                weights=[.85,1.3,.95,.95,.85,1.25,1.15,1.05,.9]
            widths=[width*w/sum(weights) for w in weights]
            t=Table(rows,colWidths=widths,repeatRows=1,hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E7EFF7')),('VALIGN',(0,0),(-1,-1),'TOP'),
                                   ('LINEBELOW',(0,0),(-1,0),.7,TEAL),('LINEBELOW',(0,-1),(-1,-1),.5,TEAL),
                                   ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F6F8FA')]),
                                   ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
                                   ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
            if len(rows)<=10:
                prefix=[]
                while story and isinstance(story[-1],Paragraph) and story[-1].style.name in {'h2','h3','caption'}:
                    prefix.insert(0,story.pop())
                story.append(KeepTogether([*prefix,t,Spacer(1,8)]))
            else:
                story.extend([t,Spacer(1,8)])
        elif text.startswith('!['):
            m=re.fullmatch(r'!\[(.*?)\]\((.*?)\)',text)
            if not m:raise ValueError('Malformed figure block')
            path=ROOT/m[2]
            with PILImage.open(path) as im:w,h=im.size
            width=A4[0]-108
            story.append(KeepTogether([Image(str(path),width=width,height=width*h/w),Paragraph(markup(m[1]),styles['caption']),Spacer(1,6)]))
        elif text.startswith('Table '):
            story.append(Paragraph(markup(text),styles['caption']))
        elif text.startswith('**Technical') or text.startswith('**Original') or text.startswith('Version 1.'):
            story.append(Paragraph(markup(text), styles['meta']))
        else:
            story.append(Paragraph(markup(text), styles['reference'] if in_references else styles['body']))
    doc = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=54, rightMargin=54, topMargin=56, bottomMargin=48,
                            title=source.read_text(encoding='utf8').splitlines()[0].lstrip('# '),
                            author='NeoGuard EOS project', pageCompression=1)
    doc.report_date=report_date
    doc.build(story, onFirstPage=header, onLaterPages=header)
    # Keep the earlier artifact link current, rather than leaving a stale report.
    if copy_alias:shutil.copyfile(output,output.with_name('neoguard-eos-methods-paper.pdf'))
    print(output)


if __name__ == '__main__':
    main()
