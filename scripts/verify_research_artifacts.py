"""Render every final research page and verify the frozen quality population."""
import hashlib,json
from pathlib import Path
import fitz
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]

def main():
    pilot=ROOT/'output/research/phase1_pilot'
    assert json.loads((pilot/'progress.json').read_text())['complete']
    assert len(list(pilot.glob('0[1-7]_*.csv')))==7
    assert json.loads((pilot/'decision.json').read_text())['clinical_release_justified'] is False
    out=ROOT/'output/pdf/qa';out.mkdir(parents=True,exist_ok=True)
    report={}
    for stem,prefix in [('neoguard-eos-research-paper','paper'),('neoguard-phase1-pilot','pilot')]:
        path=ROOT/'output/pdf'/(stem+'.pdf');doc=fitz.open(path)
        for i,page in enumerate(doc):
            assert page.get_text().strip()
            for b in page.get_text('blocks'):
                assert b[0]>=0 and b[1]>=0 and b[2]<=page.rect.width+1 and b[3]<=page.rect.height+1
            page.get_pixmap(matrix=fitz.Matrix(1.4,1.4),alpha=False).save(out/f'{prefix}-final-{i+1:02}.png')
        contacts=[]
        for start in range(0,len(doc),8):
            board=Image.new('RGB',(1400,1050),'#dfe6eb');draw=ImageDraw.Draw(board)
            for slot,index in enumerate(range(start,min(start+8,len(doc)))):
                im=Image.open(out/f'{prefix}-final-{index+1:02}.png');im.thumbnail((338,490))
                x=slot%4*350+6;y=slot//4*525+22
                board.paste(im,(x,y));draw.text((x,y-16),str(index+1),fill='black')
            target=out/f'{prefix}-final-contact-{start//8+1}.jpg';board.save(target);contacts.append(str(target))
        report[stem]={'pages':len(doc),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'all_pages_rendered':True,'outside_page_blocks':0,'contacts':contacts}
    (ROOT/'output/research/final_paper_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
