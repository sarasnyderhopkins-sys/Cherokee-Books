"""Build the text column for every page.

Syllabary: the July 2008 proof, sources/spearfinger readable1.pdf (Sara's ruling, 19 Oct 2026).
Phonetics and word glosses: the December 2008 gloss, SpfingerGloss121808.doc.
Phrase breaks and English: text/phrase_breaks.json.
Writes text/phrasesNN.json (one per page) and text/check-log.md (every place the PDF and the gloss disagree).

Run from the spearfinger folder:  python3 scripts/make_text.py   (needs soffice and pdftotext)
"""
import json, re, os, subprocess, difflib, html, tempfile, unicodedata
import docx

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = f'{HERE}/sources/spearfinger readable1.pdf'
DOC = f'{HERE}/SpfingerGloss121808.doc'
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
CHER = re.compile('[Ꭰ-᏿]')
PUN = '.,!?;:“”"‘’…\'()–-'

# ---------- the gloss ----------
def read_gloss():
    tmp = tempfile.mkdtemp()
    subprocess.run(['soffice', '--headless', '--convert-to', 'docx', '--outdir', tmp, DOC], capture_output=True, timeout=180)
    d = docx.Document(f'{tmp}/SpfingerGloss121808.docx')
    txt = lambda el: ''.join(x.text or '' for x in el.iter() if x.tag == W + 't')
    pages = {}; cur = None
    for el in d.element.body.iterchildren():
        tag = el.tag[len(W):]
        if tag == 'p':
            t = txt(el).strip()
            m = re.fullmatch(r'\*?\s*(\d+)\.\s*', t)
            if m: cur = pages.setdefault(int(m.group(1)), {'cols': [], 'english': []}); continue
            if cur is not None and t and not t.startswith('*') and cur['cols']: cur['english'].append(t)
        elif tag == 'tbl' and cur is not None:
            rows = [[txt(c).strip() for c in r.findall(W + 'tc')] for r in el.findall('.//' + W + 'tr')]
            for i, syl in enumerate(rows[0]):
                if not CHER.search(syl): continue      # '*' alone = word deleted; '...' = punctuation column
                cell = lambda r: rows[r][i].strip() if len(rows) > r and i < len(rows[r]) else ''
                cur['cols'].append({'gsyl': syl.replace('*', ''), 'pho': cell(1).replace('*', ''), 'gloss': cell(2), 'marked': '*' in syl})
    return pages

# ---------- the PDF (two book pages per spread) ----------
def read_pdf():
    out = {}
    for k in range(3, 19):
        bb = subprocess.run(['pdftotext', '-f', str(k), '-l', str(k), '-bbox-layout', PDF, '-'], capture_output=True, text=True).stdout
        for blk in re.findall(r'<block (.*?)</block>', bb, re.S):
            x0 = float(re.search(r'xMin="([\d.]+)"', blk).group(1)); x1 = float(re.search(r'xMax="([\d.]+)"', blk).group(1))
            lines = [' '.join(html.unescape(w) for w in re.findall(r'<word[^>]*>(.*?)</word>', ln)) for ln in re.findall(r'<line.*?</line>', blk, re.S)]
            text = ' '.join(lines).strip()
            if not CHER.search(text): continue
            left = (x0 + x1) / 2 < 612
            if k == 3: page = None if left else 1
            elif k <= 15: page = 2 * (k - 3) + (0 if left else 1)
            elif k == 16: page = 26
            else: page = 27                       # pdf 17 and the last line on pdf 18
            if page: out.setdefault(page, []).append(text)
    return {p: ' '.join(v) for p, v in out.items()}

# PDF typos in Spearfinger's name, set to the PDF's own usual spelling ᏗᎦᏘᏍᏙᏗ (Sara: use the PDF spelling)
NAME_FIX = {'ᏗᎦᏥᏙᏗ': 'ᏗᎦᏘᏍᏙᏗ', 'ᏗᎦᎢᏍᏙᏗ': 'ᏗᎦᏘᏍᏙᏗ'}

# plain transliteration, only for a PDF word the gloss has no phonetics for
ROWS = {'': 'ᎠᎡᎢᎣᎤᎥ', 'g': 'ᎦᎨᎩᎪᎫᎬ', 'h': 'ᎭᎮᎯᎰᎱᎲ', 'l': 'ᎳᎴᎵᎶᎷᎸ', 'm': 'ᎹᎺᎻᎼᎽ', 'n': 'ᎾᏁᏂᏃᏄᏅ', 'gw': 'ᏆᏇᏈᏉᏊᏋ',
        's': 'ᏌᏎᏏᏐᏑᏒ', 'd': 'ᏓᏕᏗᏙᏚᏛ', 'dl': 'ᏜᏞᏟᏠᏡᏢ', 'ts': 'ᏣᏤᏥᏦᏧᏨ', 'w': 'ᏩᏪᏫᏬᏭᏮ', 'y': 'ᏯᏰᏱᏲᏳᏴ'}
TR = {ch: c + 'aeiouv'[i] for c, s in ROWS.items() for i, ch in enumerate(s)}
TR.update({'Ꭷ': 'ka', 'Ꮏ': 'hna', 'Ꮐ': 'nah', 'Ꮝ': 's', 'Ꮤ': 'ta', 'Ꮦ': 'te', 'Ꮨ': 'ti', 'Ꮭ': 'tla', 'Ꮬ': 'dla', 'Ꮽ': 'mv', 'Ꮔ': 'nu'})
def translit(w): return ''.join(TR.get(ch, ch if ch in PUN else '') for ch in w)

def norm(w): return w.replace('*', '').strip(PUN + ' ')

def main():
    gloss = read_gloss(); pdf = read_pdf()
    breaks = json.load(open(f'{HERE}/text/phrase_breaks.json'))
    log = ['# Spearfinger text check', '',
           'The syllabary in the movie follows the July 2008 proof (`sources/spearfinger readable1.pdf`); the phonetics come',
           'from the December 2008 gloss (`SpfingerGloss121808.doc`). This list is every word where the two disagree, so the',
           'phonetic line under it may not match the syllabary shown. Made by `scripts/make_text.py`.', '',
           'Status: **differs** = PDF and gloss spell the word differently (phonetics shown are the gloss\'s, for the gloss spelling);',
           '**PDF only** = the word is not in the gloss (phonetics shown are a plain transliteration, no tone or length marks);',
           '**gloss only** = the gloss has a word the PDF does not (not shown in the movie).', '']
    total = {'differs': 0, 'PDF only': 0, 'gloss only': 0, 'name typo': 0}
    for n in range(1, 28):
        cols = gloss[n]['cols']
        pw = [w for w in pdf[n].replace('...', '… ').split() if CHER.search(w)]
        rows = []
        for i, w in enumerate(pw):
            core = norm(w)
            if core in NAME_FIX:
                pw[i] = w.replace(core, NAME_FIX[core]); total['name typo'] += 1
                rows.append(f'| {i+1} | {w} | | | name typo in the PDF, shown as {NAME_FIX[core]} |')
        a = [norm(c['gsyl']) for c in cols]; b = [norm(w) for w in pw]
        words = []
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            k = min(i2 - i1, j2 - j1) if op == 'replace' else (i2 - i1 if op == 'equal' else 0)
            for x in range(j2 - j1):
                j = j1 + x
                if x < k:
                    c = cols[i1 + x]
                    st = 'same' if op == 'equal' else 'differs'
                    words.append(dict(syl=pw[j], pho=c['pho'], gloss=c['gloss'], status=st, gsyl=c['gsyl']))
                else:
                    words.append(dict(syl=pw[j], pho=translit(pw[j]), gloss='', status='PDF only', gsyl=''))
            for i in range(i1 + k, i2):
                rows.append(f"| – | | {cols[i]['gsyl']} | {cols[i]['pho']} | gloss only |"); total['gloss only'] += 1
        for i, w in enumerate(words):
            if w['status'] == 'differs':
                rows.append(f"| {i+1} | {w['syl']} | {w['gsyl']} | {w['pho']} | differs |"); total['differs'] += 1
            elif w['status'] == 'PDF only':
                rows.append(f"| {i+1} | {w['syl']} | | {w['pho']} | PDF only |"); total['PDF only'] += 1
        # phrases
        phrases = []; start = 0
        for last, eng in breaks[str(n)]:
            ws = words[start:last]; start = last
            phrases.append({'syl': ' '.join(w['syl'] for w in ws),
                            'pho': ' '.join((w['pho'] or '–').replace(' ', ' ') for w in ws),
                            'eng': eng,
                            'gloss': [w['gloss'] for w in ws]})
        assert start == len(words), (n, start, len(words))
        for p in phrases: assert len(p['syl'].split(' ')) == len(p['pho'].split(' ')), (n, p)
        json.dump(phrases, open(f'{HERE}/text/phrases{n:02d}.json', 'w'), ensure_ascii=False, indent=1)
        log += [f'## Page {n}', '']
        if rows:
            log += ['| Word | PDF syllabary (shown) | Gloss syllabary | Phonetics shown | Status |', '|---|---|---|---|---|']
            log += sorted(rows, key=lambda r: int(r.split('|')[1]) if r.split('|')[1].strip().isdigit() else 999)
        else:
            log.append('PDF and gloss agree.')
        log.append('')
    k = log.index('## Page 1')
    log[k:k] = [f"Totals: {total['differs']} words differ, {total['PDF only']} PDF only, {total['gloss only']} gloss only, {total['name typo']} name typos fixed.", '']
    open(f'{HERE}/text/check-log.md', 'w').write('\n'.join(log) + '\n')
    print(total)

if __name__ == '__main__':
    main()
