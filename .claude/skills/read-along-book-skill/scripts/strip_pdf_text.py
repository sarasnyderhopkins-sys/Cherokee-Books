#!/usr/bin/env python3
"""Make clean page pictures from a picture-book PDF whose text sits in its own layer over the artwork.

    python3 scripts/strip_pdf_text.py "book.pdf" --pages 1,5-24 --out images [--dpi 150] [--keep-images]

For each page it removes every text object (BT … ET) and, unless --keep-images, every image draw after the first
(Photoshop PDFs often paint the text as a clip over a second, flat-colour image), then renders the page with
pdftoppm to images/page-NN.jpg (NN = the PDF page number). Needs pypdf and poppler (pdftoppm).
Always look at the pictures afterwards: if a page lost artwork, rerun it with --keep-images; if text remains,
it is part of the artwork and needs retouching instead.
"""
import argparse, os, re, shutil, subprocess, sys, tempfile
from pypdf import PdfReader, PdfWriter
from pypdf.generic import StreamObject


def page_set(spec, n):
    out = set()
    for tok in spec.split(','):
        tok = tok.strip()
        if not tok: continue
        if '-' in tok: a, b = tok.split('-'); out.update(range(int(a), int(b) + 1))
        else: out.add(int(tok))
    return sorted(p for p in out if 1 <= p <= n)


def clean(data, keep_images):
    data = re.sub(rb'\bBT\b.*?\bET\b', b'', data, flags=re.S)                 # text objects
    if not keep_images:
        draws = list(re.finditer(rb'/([^\s/]+)\s+Do\b', data))
        for m in draws[1:]:                                                   # keep the first picture only
            data = data[:m.start()] + b' ' * (m.end() - m.start()) + data[m.end():]
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('--pages', default='', help='e.g. 1,5-24 (default: all)')
    ap.add_argument('--out', default='images')
    ap.add_argument('--dpi', type=int, default=150)
    ap.add_argument('--keep-images', action='store_true')
    ap.add_argument('--prefix', default='page-')
    a = ap.parse_args()
    reader = PdfReader(a.pdf)
    wanted = page_set(a.pages, len(reader.pages)) if a.pages else list(range(1, len(reader.pages) + 1))
    writer = PdfWriter(clone_from=reader)
    for n in wanted:
        page = writer.pages[n - 1]
        contents = page.get_contents()
        if contents is None: continue
        s = StreamObject(); s.set_data(clean(contents.get_data(), a.keep_images))
        page.replace_contents(s)
    os.makedirs(a.out, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        clean_pdf = os.path.join(tmp, 'clean.pdf')
        with open(clean_pdf, 'wb') as f: writer.write(f)
        for n in wanted:
            base = os.path.join(tmp, f'p{n}')
            subprocess.run(['pdftoppm', '-f', str(n), '-l', str(n), '-r', str(a.dpi), '-jpeg', '-jpegopt', 'quality=88', '-singlefile', clean_pdf, base], check=True)
            dst = os.path.join(a.out, f'{a.prefix}{n:02d}.jpg')
            shutil.move(base + '.jpg', dst)
            print('wrote', dst)


if __name__ == '__main__':
    main()
