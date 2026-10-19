#!/usr/bin/env python3
"""Build sentences.json for the Trick or Treat Danny read-along.

Sources (all copied from her Mac):
  text/syllabary-conversion.txt  her Word file: English / phonetics / syllabary per sentence (Oct 11 2019)
  text/pdf-text-by-page.tsv      text layer of the Oct 24 2019 FINAL REVISED PDF, page by page (wins)
  text/silences.txt              pauses in the movie sound track (ffmpeg silencedetect)
"""
import json, re, unicodedata, difflib, itertools, os

HERE = os.path.dirname(os.path.abspath(__file__))
T = lambda n: os.path.join(HERE, 'text', n)

# ---------- her Word file: triplets ----------
raw = [l.rstrip('\n') for l in open(T('syllabary-conversion.txt'), encoding='utf-8') if l.strip()]
raw = raw[2:]  # title lines
trip = [raw[i:i + 3] for i in range(0, len(raw) - len(raw) % 3, 3)]
sent = []
for en, ph, sy in trip:
    en, ph, sy = (re.sub(r'\s+', ' ', x).strip() for x in (en, ph, sy))
    if sent and not re.search(r'[.!?”\]]\s*$', sent[-1]['en']):   # continuation of the previous sentence
        sent[-1]['en'] += ' ' + en; sent[-1]['phon_docx'] += ' ' + ph; sent[-1]['syl_docx'] += ' ' + sy
    else:
        sent.append({'en': en, 'phon_docx': ph, 'syl_docx': sy})
for s in sent:
    s['en'] = s['en'].replace('  [Can make up Cherokee names instead.]', '').strip()

# ---------- the final PDF, page by page ----------
pages = {}
for line in open(T('pdf-text-by-page.tsv'), encoding='utf-8'):
    p, _, txt = line.rstrip('\n').partition('\t')
    p = int(p)
    if not 5 <= p <= 24: continue
    txt = txt.strip()
    if txt.startswith('”') or txt.startswith('"'):          # a closing quote pushed to its own line
        pages[p] = pages[p].rstrip() + txt
    else:
        pages[p] = (pages.get(p, '') + ' ' + txt).strip()

def nospace(s): return re.sub(r'\s+', '', s)

# one long string for the PDF with page offsets, and one for her sentences with sentence offsets
pdf_chars, pdf_page, pdf_space_before = [], [], []
for p in sorted(pages):
    prev_space = False
    for ch in pages[p]:
        if ch.isspace(): prev_space = True; continue
        pdf_chars.append(ch); pdf_page.append(p); pdf_space_before.append(prev_space); prev_space = False
doc_chars, doc_sent, doc_space_before = [], [], []
for i, s in enumerate(sent):
    prev_space = False
    for ch in s['syl_docx']:
        if ch.isspace(): prev_space = True; continue
        doc_chars.append(ch); doc_sent.append(i); doc_space_before.append(prev_space); prev_space = False

A, B = ''.join(doc_chars), ''.join(pdf_chars)
sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
match_of_pdf = [None] * len(B)     # pdf index -> doc index when equal
sent_of_pdf = [None] * len(B)
diff_sent = {}
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal':
        for k in range(i2 - i1):
            match_of_pdf[j1 + k] = i1 + k; sent_of_pdf[j1 + k] = doc_sent[i1 + k]
    else:
        if tag == 'insert' and i1 > 0 and all(c in '.,!?”' for c in B[j1:j2]):
            target = doc_sent[i1 - 1]          # punctuation the PDF adds belongs to the sentence before it
        else:
            target = doc_sent[min(i1, len(doc_sent) - 1)]
        touched = set(doc_sent[i1:i2]) or {target}
        for s in touched: diff_sent.setdefault(s, []).append((tag, A[i1:i2], B[j1:j2]))
        for j in range(j1, j2): sent_of_pdf[j] = target
# fill gaps (inserted pdf chars) with the previous sentence
last = 0
for j in range(len(B)):
    if sent_of_pdf[j] is None: sent_of_pdf[j] = last
    last = sent_of_pdf[j]

# rebuild each sentence's syllabary from the PDF characters, spaced like her Word file
for i, s in enumerate(sent):
    js = [j for j in range(len(B)) if sent_of_pdf[j] == i]
    out = ''
    for n, j in enumerate(js):
        d = match_of_pdf[j]
        space = (doc_space_before[d] if d is not None else pdf_space_before[j]) if n else False
        if n and B[j] in ',.!?”' : space = False
        if n and B[j - 1] == '“': space = False
        out += (' ' if space else '') + B[j]
    s['syl'] = out
    pg = [pdf_page[j] for j in js]
    s['page'] = max(set(pg), key=pg.count) if pg else None
    s['note'] = ''
    if i in diff_sent:
        parts = []
        for tag, a, b in diff_sent[i]:
            parts.append(f'Word file “{a}” → PDF “{b}”' if a and b else (f'PDF adds “{b}”' if b else f'PDF drops “{a}”'))
        s['note'] = 'Syllabary taken from the Oct 24 PDF; differs from the Word file: ' + '; '.join(parts)

# ---------- phonetics ----------
def roman(ch):
    try:
        n = unicodedata.name(ch)
    except ValueError:
        return ch
    if n.startswith('CHEROKEE LETTER '):
        return n[16:].lower()
    return ch
def transliterate(syl):
    words = []
    for w in syl.split(' '):
        words.append(''.join(roman(c) for c in w))
    return ' '.join(words)
PUNCT = '“”"\',.!?-'
def core(w): return w.strip(PUNCT)
def lead(w): return w[:len(w) - len(w.lstrip(PUNCT))]
def trail(w): return w[len(w.rstrip(PUNCT)):]
for s in sent:
    if nospace(s['syl']) == nospace(s['syl_docx']):
        s['phon'] = s['phon_docx']; continue
    # word by word: keep her phonetics for every word the PDF left alone, re-spell only the changed words
    dw = [core(w).replace('tᎥ', 'Ꮫ') for w in s['syl_docx'].split()]   # her file's stray Latin t = Ꮫ (tv)
    pw = s['phon_docx'].split()
    her = dict(zip(dw, pw)) if len(dw) == len(pw) else {}
    out, changed = [], []
    for w in s['syl'].split():
        c = core(w)
        if c in her:
            out.append(lead(w) + core(her[c]) + trail(w))
        else:
            t = transliterate(c)
            if c and c[0] == s['syl'].split()[0][0] and w == s['syl'].split()[0]: t = t[:1].upper() + t[1:]
            for name in ('denili', 'lusi', 'magi', 'tsosaya'):
                if t == name: t = t.capitalize()
            out.append(lead(w) + t + trail(w)); changed.append(f'{c} = {t}')
    s['phon'] = ' '.join(out)
    if changed: s['note'] += ' Phonetics re-spelled for: ' + ', '.join(changed) + ' (check).'

# ---------- timing ----------
sil = [tuple(float(x) for x in re.match(r'([\d.]+)-([\d.]+)\(([\d.]+)\)', t).groups())
       for t in open(T('silences.txt'), encoding='utf-8').read().split('\n')[1].split()]
change = {5: 10, 6: 35, 7: 54, 8: 62, 9: 75, 10: 100, 11: 123, 12: 144, 13: 156, 14: 162, 15: 173, 16: 179,
          17: 196, 18: 209, 19: 224, 20: 238, 21: 256, 22: 270, 23: 289, 24: 301, 25: 324}   # page turns seen in the movie (s)
def nearest_silence(t):
    best = min(sil, key=lambda s: 0 if s[0] <= t <= s[1] else min(abs(s[0] - t), abs(s[1] - t)))
    dist = 0 if best[0] <= t <= best[1] else min(abs(best[0] - t), abs(best[1] - t))
    return best, dist
bounds = {}
timing_notes = {}
for p, t in change.items():
    s, dist = nearest_silence(t)
    bounds[p] = s
    if dist > 1.0: timing_notes[p] = dist
spans = {p: (bounds[p][1], bounds[p + 1][0]) for p in range(5, 25)}

def weight(s):
    return sum(1 for c in s['syl'] if 'CHEROKEE' in unicodedata.name(c, '')) or 1
fine = [tuple(float(x) for x in re.match(r'([\d.]+)-([\d.]+)\(([\d.]+)\)', t).groups())
        for t in open(T('silences-fine.txt'), encoding='utf-8').read().split('\n')[1].split()] if os.path.exists(T('silences-fine.txt')) else sil
for p in range(5, 25):
    ls = [s for s in sent if s['page'] == p]
    a, b = spans[p]
    inside = [x for x in fine if a < x[0] and x[1] < b]
    n = len(ls)
    if n <= 1:
        for s in ls: s['start'], s['end'] = a, b
        continue
    W = [weight(s) for s in ls]; tot = sum(W); acc = 0; expected = []
    for w in W[:-1]:
        acc += w; expected.append(a + (b - a) * acc / tot)
    if len(inside) >= n - 1:
        best, best_cost = None, None
        for combo in itertools.combinations(inside, n - 1):
            cost = sum(abs((x[0] + x[1]) / 2 - e) for x, e in zip(combo, expected)) - 2 * sum(x[2] for x in combo)
            st = [a] + [c[1] for c in combo]; en = [c[0] for c in combo] + [b]
            for w, s0, e0 in zip(W, st, en):            # nobody reads faster than ~0.12 s a syllable
                d = e0 - s0
                if d < 0.12 * w: cost += 10 * (0.12 * w - d)
                if d > 0.7 * w: cost += (d - 0.7 * w)
            if best_cost is None or cost < best_cost: best, best_cost = combo, cost
        cuts = list(best)
        starts = [a] + [c[1] for c in cuts]; ends = [c[0] for c in cuts] + [b]
    else:
        starts = [a] + expected; ends = expected + [b]
        for s in ls: s['note'] += ' Timing guessed (not enough pauses found); please check.'
    for s, st, en in zip(ls, starts, ends):
        s['start'], s['end'] = round(st, 2), round(en, 2)
for p, d in timing_notes.items():
    for s in sent:
        if s['page'] == p and s is next(x for x in sent if x['page'] == p):
            s['note'] += f' Page turn in the movie is {d:.1f} s from the nearest pause; start time may need a nudge.'

for k, s in enumerate(sent, 1): s['line'] = k
json.dump({'sentences': sent, 'spans': spans}, open(os.path.join(HERE, 'sentences.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(sent), 'sentences')
for s in sent:
    print(f"{s['line']:2d} p{s['page']} {s['start']:7.2f}-{s['end']:7.2f}  {s['syl']}")
    print(f"      {s['phon']}")
    print(f"      {s['en']}")
    if s['note']: print(f"      NOTE: {s['note'].strip()}")
