#!/usr/bin/env python3
"""Bundle the built book into ONE file that works anywhere, with no folder beside it.

Run it from this folder after build_book.py:
    python3 build_standalone.py
It reads index.html and writes "Halloween Picture Book.html" with every picture, recording
and font embedded. The fonts come from the fonts/ folder; if that folder is missing the
file keeps loading them from Google Fonts (then it needs internet for the fonts only).
"""
import base64, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'index.html')
OUT = os.path.join(HERE, 'Halloween Picture Book.html')
FONTS = os.path.join(HERE, 'fonts')
MIME = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp',
        '.mp3': 'audio/mpeg', '.m4a': 'audio/mp4', '.wav': 'audio/wav', '.woff2': 'font/woff2', '.woff': 'font/woff'}


def data_uri(path):
    ext = os.path.splitext(path)[1].lower()
    with open(path, 'rb') as f:
        return f'data:{MIME.get(ext, "application/octet-stream")};base64,' + base64.b64encode(f.read()).decode()


def main():
    if not os.path.exists(SRC):
        sys.exit('index.html not found; run build_book.py first')
    html = open(SRC, encoding='utf-8').read()

    # pictures and recordings: the "images/..." and "audio/..." names inside the page data
    missing = []
    def swap(m):
        rel = m.group(1)
        path = os.path.join(HERE, rel)
        if not os.path.exists(path):
            missing.append(rel)
            return m.group(0)
        return '"' + data_uri(path) + '"'
    html, n = re.subn(r'"((?:images|audio)/[^"]+)"', swap, html)

    # fonts
    css_path = os.path.join(FONTS, 'fonts.css')
    links = re.compile(r'<link rel="preconnect"[^>]*>\s*|<link rel="stylesheet" href="https://fonts\.googleapis\.com[^"]*">\s*')
    if os.path.exists(css_path):
        css = open(css_path, encoding='utf-8').read()
        css = re.sub(r'url\(([^)]+)\)', lambda m: 'url(' + data_uri(os.path.join(FONTS, m.group(1).strip('\'"'))) + ')', css)
        html = links.sub('', html, count=2)          # drop the two preconnects
        html = links.sub('<style>\n' + css + '</style>\n', html, count=1)
        fonts_note = 'fonts embedded'
    else:
        fonts_note = 'fonts/ folder missing, fonts still load from Google'

    if not html.lstrip().lower().startswith('<!doctype'):
        html = '<!doctype html>\n' + html
    open(OUT, 'w', encoding='utf-8').write(html)
    size = os.path.getsize(OUT) / 1e6
    print(f'wrote {os.path.basename(OUT)}: {n} files embedded, {fonts_note}, {size:.1f} MB')
    for m in missing:
        print(f'warning: file not found, left as a link: {m}')


if __name__ == '__main__':
    main()
