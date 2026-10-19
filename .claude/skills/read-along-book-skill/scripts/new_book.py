#!/usr/bin/env python3
"""Start a new read-along book folder: copies the page template, build scripts and fonts, and writes the spreadsheet.

    cd "My Book/Read Along"
    python3 /path/to/read-along-book-skill/scripts/new_book.py "Trick or Treat, Danny!" \
        --title-syl "ᏗᏓᎶᏅᎮᏍᎩ ᏃᎴ ᏗᏓᏁ, ᏕᏂᎵ!" --title-phon "Didalonvhesgi nole Didane, Denili!" \
        --credit "Written by … · Translated and read by … · Edited by …" \
        --lines lines.tsv

Put the page pictures in images/ first (page-01.jpg, page-02.jpg, … — the number is the page number, page 1 = cover)
and the narration in audio/narration.mp3. lines.tsv is optional: one sentence per line, tab-separated
    page <TAB> syllabary <TAB> phonetics <TAB> English
(a header line is skipped). Without it the Sentences sheet is written empty for you to fill in.
Existing files are never overwritten unless --force.
"""
import argparse, glob, os, re, shutil, sys
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('title', help='English title (also names the spreadsheet and the single-file version)')
    ap.add_argument('--title-syl', default='')
    ap.add_argument('--title-phon', default='')
    ap.add_argument('--credit', default='')
    ap.add_argument('--lines', help='TSV: page, syllabary, phonetics, English')
    ap.add_argument('--folder', default='.')
    ap.add_argument('--no-title-line', action='store_true', help='the cover has no spoken title in the narration')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    folder = os.path.abspath(a.folder)
    os.makedirs(os.path.join(folder, 'images'), exist_ok=True)
    os.makedirs(os.path.join(folder, 'audio'), exist_ok=True)
    os.makedirs(os.path.join(folder, 'text'), exist_ok=True)

    for name in ('template.html', 'build_book.py', 'build_standalone.py'):
        dst = os.path.join(folder, name)
        if a.force or not os.path.exists(dst): shutil.copy(os.path.join(ASSETS, name), dst)
    if a.force or not os.path.exists(os.path.join(folder, 'fonts')):
        shutil.copytree(os.path.join(ASSETS, 'fonts'), os.path.join(folder, 'fonts'), dirs_exist_ok=True)

    # pages from the pictures already in images/
    images = sorted(glob.glob(os.path.join(folder, 'images', '*.*')))
    pages = []
    for i, p in enumerate(images):
        m = re.search(r'(\d+)(?!.*\d)', os.path.basename(p))
        pages.append((int(m.group(1)) if m else i + 1, 'images/' + os.path.basename(p)))
    pages.sort()
    if not pages: print('note: images/ is empty; add page-01.jpg … and fill the Pages sheet, or run again with --force')

    # sentences
    sent = []
    if a.lines:
        for raw in open(a.lines, encoding='utf-8-sig'):
            parts = raw.rstrip('\n').split('\t')
            if len(parts) < 2 or not parts[0].strip() or parts[0].strip().lower() in ('page', 'pg'): continue
            while len(parts) < 4: parts.append('')
            sent.append([p.strip() for p in parts[:4]])

    bold, yellow, wrap = Font(bold=True), PatternFill('solid', fgColor='FFF4B8'), Alignment(wrap_text=True, vertical='top')
    chr_font = Font(name='Noto Sans Cherokee')
    wb = Workbook()
    ws = wb.active; ws.title = 'Sentences'
    ws.append(['Line', 'Page', 'Start (s)', 'End (s)', 'Phonetics', 'Syllabary', 'English', 'Check notes'])
    first_page = pages[0][0] if pages else 1
    if not a.no_title_line:
        ws.append(['title', first_page, 0, None, a.title_phon, a.title_syl, a.title, 'Spoken title over the cover when Begin is pressed; set its End to where the title ends (or delete this row if the narration has no title).'])
    if sent:
        for n, (page, syl, phon, en) in enumerate(sent, 1):
            ws.append([n, int(float(page)) if re.fullmatch(r'\d+(\.0+)?', page) else page, None, None, phon, syl, en, 'Timing guessed (not yet timed); tap along in Time it mode.'])
    else:
        for n in range(1, 4): ws.append([n, '', None, None, '', '', '', 'Fill in page, phonetics, syllabary, English; delete spare rows.'])
    for c in ws[1]: c.font = bold
    for i, w in enumerate([6, 6, 9, 9, 46, 46, 46, 60], 1): ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row: c.alignment = wrap
        row[5].font = chr_font
        if row[7].value: row[7].fill = yellow
    ws.freeze_panes = 'A2'

    wp = wb.create_sheet('Pages')
    wp.append(['Page', 'Image file', 'Caption zone top', 'Caption zone bottom', 'Motion', 'Description', 'Effect'])
    for i, (num, img) in enumerate(pages):
        wp.append([num, img, 0.72, 0.88, 'hold' if i == 0 or i == len(pages) - 1 else 'zoom in', '', ''])
    for c in wp[1]: c.font = bold
    for i, w in enumerate([6, 20, 16, 18, 10, 50, 10], 1): wp.column_dimensions[get_column_letter(i)].width = w

    wsett = wb.create_sheet('Settings')
    wsett.append(['Setting', 'Value', 'What it does'])
    for r in [
        ('title_syl', a.title_syl, 'Title in the top bar (syllabary)'),
        ('title_phon', a.title_phon, 'Title in the top bar (phonetics)'),
        ('title_en', a.title, 'English title on the cover; also names the single-file version unless file_name is set'),
        ('credit', a.credit, 'Credit line on the cover: author, translator, reader, editor, copyright'),
        ('file_name', '', 'Name for the single-file version (build_standalone.py); blank = title_en + .html'),
        ('audio', 'audio/narration.mp3', 'The one narration file; Start and End on the Sentences sheet are seconds into it'),
        ('pause_seconds', 1.5, 'Pause after a page finishes before Play all turns the page'),
        ('text_default', 'on', 'on or off: is the text showing when the book opens'),
        ('show_syllabary', 'yes', 'yes/no: syllabary line in the caption'),
        ('show_phonetics', 'yes', 'yes/no: phonetics line in the caption'),
        ('show_english', 'yes', 'yes/no: English line in the caption'),
        ('fade_seconds', 0.6, 'How long the caption takes to fade in and out'),
        ('line_gap_seconds', 0, 'Seconds taken off the end of the last line on a page (0: the ends already stop in the pause)'),
        ('bg_color', '', 'Background colour around the page, e.g. #1f1e33 (blank = navy)'),
        ('accent_color', '', 'Button colour, e.g. #f08a2e (blank = orange)'),
        ('storage_key', '', 'Name under which a browser remembers this book’s text choices and tapped timings (blank = the title)'),
    ]: wsett.append(list(r))
    for c in wsett[1]: c.font = bold
    for i, w in enumerate([18, 60, 80], 1): wsett.column_dimensions[get_column_letter(i)].width = w

    wh = wb.create_sheet('How to edit')
    for line in [
        f'{a.title}: read-along book, how to edit',
        '',
        'Sentences sheet: one row per sentence. Edit Phonetics, Syllabary and English freely. Page says which picture the line belongs to.',
        'Start and End are seconds into audio/narration.mp3. Lines on the same page play one after another from the first Start to the last End.',
        'Check notes (yellow) mark lines to look at (a spelling question, a guessed timing). Clear a note once you have checked it.',
        '',
        'Easiest way to fix the timing: open index.html, press Time it, press Play, then tap the space bar the moment each line starts.',
        'Finish offers timings.csv. Save it in this folder, then: python3 scripts/apply_timings.py (writes the times into this sheet) and python3 build_book.py.',
        '',
        'Pages sheet: Caption zone top/bottom say where on the page (0 = top, 1 = bottom) the live caption sits, usually where the printed text was.',
        'Motion: zoom in, zoom out, pan left, pan right, drift, hold. Effect: flicker (candle light) or blank. Description is the picture’s alt text.',
        '',
        'Rebuild after editing (Terminal, in this folder):',
        '    python3 build_book.py',
        '    python3 build_standalone.py        (optional: one file with everything inside)',
    ]: wh.append([line])
    wh['A1'].font = bold
    wh.column_dimensions['A'].width = 120

    safe = re.sub(r'[^\w\s-]', '', a.title).strip() or 'book'
    out = os.path.join(folder, f'{safe} sentences.xlsx')
    if os.path.exists(out) and not a.force: sys.exit(f'{out} exists; use --force to replace it')
    wb.save(out)
    print(f'wrote {os.path.basename(out)} with {len(pages)} pages and {len(sent)} sentences; template, build scripts and fonts are in {folder}')


if __name__ == '__main__':
    main()
