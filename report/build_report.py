"""Construye el informe Word/PDF desde `report/informe.md` (LG-03).

Formato acordado en el plan: Times New Roman 12, subtítulos negros en negrita,
párrafos justificados y figuras con su explicación. Solo convierte el subconjunto
de Markdown que usa el informe (títulos, párrafos, listas, tablas, imágenes,
bloques de código, negrita, cursiva y código en línea).

Uso, desde la raíz del repositorio:
    python main.py figures
    python report/build_report.py            # report/build/informe_proyecto_f1.docx
    python report/build_report.py --pdf      # además PDF con LibreOffice (soffice)

Las salidas quedan en `report/build/`, fuera de Git: el Word y el PDF se entregan
por fuera del repositorio, como indica el plan.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

REPORT_DIR = Path(__file__).resolve().parent
SOURCE = REPORT_DIR / 'informe.md'
BUILD = REPORT_DIR / 'build'
LOGO = REPORT_DIR / 'assets/logo_uvg.png'
FONT = 'Times New Roman'
INLINE = re.compile(r'(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*|\[[^\]]+\]\([^)]+\))')
LINK = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')


def set_font(run, size=12, bold=None, italic=None, mono=False):
    name = 'Consolas' if mono else FONT
    run.font.name = name
    run.element.rPr.rFonts.set(qn('w:eastAsia'), name)
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor(0, 0, 0)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def add_inline(paragraph, text, size=12, bold=False):
    for piece in INLINE.split(text):
        if not piece:
            continue
        if piece.startswith('**') and piece.endswith('**'):
            set_font(paragraph.add_run(piece[2:-2]), size, bold=True)
        elif piece.startswith('`') and piece.endswith('`'):
            set_font(paragraph.add_run(piece[1:-1]), size - 1, bold=bold, mono=True)
        elif piece.startswith('*') and piece.endswith('*') and len(piece) > 2:
            set_font(paragraph.add_run(piece[1:-1]), size, bold=bold, italic=True)
        elif link := LINK.fullmatch(piece):
            set_font(paragraph.add_run(link.group(1)), size, bold=bold)
        else:
            set_font(paragraph.add_run(piece), size, bold=bold)


def new_list_numbering(doc, paragraph):
    """Instancia de numeración nueva que reinicia en 1.

    El estilo 'List Number' comparte un solo contador en todo el documento, así que sin
    esto cada lista numerada continúa la anterior (Conclusiones empezaba en 6).
    """
    numbering = doc.part.numbering_part.element
    style_num_id = paragraph.style.element.pPr.numPr.numId.val
    abstract_id = next(num.abstractNumId.val for num in numbering.num_lst if num.numId == style_num_id)
    num = numbering.add_num(abstract_id)
    num.add_lvlOverride(ilvl=0).add_startOverride(1)
    return num.numId


def set_list_numbering(paragraph, num_id):
    num_pr = paragraph._p.get_or_add_pPr().get_or_add_numPr()
    num_pr.get_or_add_ilvl().val = 0
    num_pr.get_or_add_numId().val = num_id


def body_paragraph(doc, text, style=None, align=WD_ALIGN_PARAGRAPH.JUSTIFY, size=12):
    paragraph = doc.add_paragraph(style=style)
    paragraph.alignment = align
    paragraph.paragraph_format.space_after = Pt(6)
    add_inline(paragraph, text, size)
    return paragraph


def add_heading(doc, text, level):
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(12 if level <= 2 else 8)
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph.paragraph_format.keep_with_next = True
    if level == 1:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(paragraph.add_run(text), {1: 16, 2: 13}.get(level, 12), bold=True)


def add_table(doc, rows):
    cells = [[c.strip() for c in row.strip().strip('|').split('|')] for row in rows]
    header, body = cells[0], [r for r in cells[2:]]
    table = doc.add_table(rows=1 + len(body), cols=len(header))
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, value in enumerate(header):
        cell = table.rows[0].cells[j]
        cell.text = ''
        add_inline(cell.paragraphs[0], value, 10, bold=True)
    for i, row in enumerate(body, start=1):
        for j, value in enumerate(row[:len(header)]):
            cell = table.rows[i].cells[j]
            cell.text = ''
            add_inline(cell.paragraphs[0], value, 10)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_code(doc, lines):
    for line in lines:
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.left_indent = Cm(0.5)
        set_font(paragraph.add_run(line), 9, mono=True)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_image(doc, target):
    path = (REPORT_DIR / target).resolve()
    if not path.exists():
        body_paragraph(doc, f'[Figura no disponible: {target}. Ejecutar `python main.py figures`.]')
        return
    doc.add_picture(str(path), width=Cm(15.5))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


COVER_HEADER = (
    ('UNIVERSIDAD DEL VALLE DE GUATEMALA', 14, True),
    ('Modelación y Simulación', 14, True),
    ('Erick Marroquín', 12, False),
    ('Sección: 20', 12, False),
)


def cover(doc, title, meta):
    for line, size, bold in COVER_HEADER:
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_font(paragraph.add_run(line), size, bold=bold)
    if LOGO.exists():
        doc.add_picture(str(LOGO), width=Cm(6))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        doc.add_paragraph()
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_inline(paragraph, title, 22, bold=True)
    doc.add_paragraph()
    for line in meta:
        body_paragraph(doc, line, align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_page_break()


def build_docx(source: Path, out: Path) -> Path:
    lines = source.read_text(encoding='utf-8').splitlines()
    doc = Document()
    for section in doc.sections:
        section.top_margin = section.bottom_margin = Cm(2.5)
        section.left_margin = section.right_margin = Cm(2.5)
    normal = doc.styles['Normal']
    normal.font.name = FONT
    normal.font.size = Pt(12)

    title = lines[0].lstrip('# ').strip()
    meta, i = [], 1
    while i < len(lines) and not lines[i].startswith('## '):
        if lines[i].strip() and not lines[i].startswith('> '):
            meta.append(lines[i])
        i += 1
    cover(doc, title, meta)

    list_num_id = None
    while i < len(lines):
        line = lines[i]
        if line.startswith('```'):
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                block.append(lines[i])
                i += 1
            add_code(doc, block)
        elif line.startswith('|'):
            block = []
            while i < len(lines) and lines[i].startswith('|'):
                block.append(lines[i])
                i += 1
            add_table(doc, block)
            continue
        elif line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            add_heading(doc, line.lstrip('# ').strip(), level)
        elif match := re.match(r'!\[[^\]]*\]\(([^)]+)\)', line):
            add_image(doc, match.group(1))
        elif re.match(r'\d+\. ', line):
            paragraph = body_paragraph(doc, re.sub(r'^\d+\. ', '', line), style='List Number')
            if line.startswith('1. ') or list_num_id is None:
                list_num_id = new_list_numbering(doc, paragraph)
            set_list_numbering(paragraph, list_num_id)
        elif line.startswith('- '):
            body_paragraph(doc, line[2:], style='List Bullet')
        elif line.startswith('> '):
            paragraph = body_paragraph(doc, line[2:], size=11)
            paragraph.paragraph_format.left_indent = Cm(0.8)
        elif line.strip():
            body_paragraph(doc, line)
        i += 1
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    return out


def to_pdf(docx: Path) -> Path:
    soffice = shutil.which('soffice') or shutil.which('libreoffice')
    default = Path('C:/Program Files/LibreOffice/program/soffice.exe')
    if soffice is None and default.exists():
        soffice = str(default)
    if soffice is None:
        sys.exit('No se encontró LibreOffice (soffice). Exportar el .docx a PDF desde Word.')
    subprocess.run([soffice, '--headless', '--convert-to', 'pdf', '--outdir', str(docx.parent), str(docx)],
                   check=True, capture_output=True)
    return docx.with_suffix('.pdf')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--pdf', action='store_true', help='Convertir también a PDF con LibreOffice')
    args = parser.parse_args()
    docx = build_docx(SOURCE, BUILD / 'informe_proyecto_f1.docx')
    print(f'Word: {docx}')
    if args.pdf:
        print(f'PDF: {to_pdf(docx)}')


if __name__ == '__main__':
    main()
