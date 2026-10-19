"""Shared helpers for the read-along scripts: finding the spreadsheet, pause lists, snapping timings."""
import glob, os, re, subprocess, sys

MARGIN = 0.15          # seconds of lead before the first sound and of tail after the last


def find_xlsx(folder, arg=None):
    if arg: return arg if os.path.isabs(arg) else os.path.join(folder, arg)
    books = [p for p in glob.glob(os.path.join(folder, '*.xlsx')) if not os.path.basename(p).startswith('~$')]
    if len(books) != 1: sys.exit(f'expected one .xlsx in {folder}, found {len(books)}; pass --xlsx "name.xlsx"')
    return books[0]


def key_of(v):
    k = ('' if v is None else str(v)).strip().lower()
    return str(int(float(k))) if re.fullmatch(r'\d+(\.0+)?', k) else k


def load_pauses(path, merge_gap=0.1):
    """Read a text/silences*.txt list → [(start, end), ...]; pauses separated by a blip under merge_gap s count as one."""
    if not os.path.exists(path): return []
    body = open(path, encoding='utf-8').read().split('\n')
    out = []
    for t in (body[1] if len(body) > 1 else '').split():
        m = re.match(r'([\d.]+)-([\d.]+)\(', t)
        if m: out.append((float(m.group(1)), float(m.group(2))))
    out.sort()
    merged = []
    for a, b in out:
        if merged and a - merged[-1][1] < merge_gap: merged[-1] = (merged[-1][0], b)
        else: merged.append((a, b))
    return merged


def pause_lists(folder):
    """fine (-32 dB), coarse (-35 dB), strict (-38 dB) lists from text/ or build/text/."""
    def first(*names):
        for n in names:
            for sub in ('text', 'build/text'):
                p = os.path.join(folder, sub, n)
                if os.path.exists(p): return load_pauses(p)
        return []
    return {'fine': first('silences-fine.txt', 'silences.txt'), 'coarse': first('silences.txt'), 'strict': first('silences-strict.txt')}


def onset(tap, fine, window=1.3):
    """Start of the speech a tap reacted to: the end of the last pause within `window` s before the tap
    (taps come 0.3-1.0 s after the first sound); a tap inside a pause with no such burst = that pause's end."""
    prev = [s for s in fine if s[1] <= tap + 0.05 and tap - s[1] <= window]
    if prev: return prev[-1][1]
    for s in fine:
        if s[0] <= tap <= s[1]: return s[1]
    return max(0.0, tap - 0.4)


def pause_at(t, lst):
    """The pause that ends at or just before t (the gap before speech starting at t)."""
    c = [s for s in lst if s[0] - 0.05 <= t and s[1] <= t + 0.03 and t - s[1] <= 0.8]
    return c[-1] if c else None


def boundary(on, lists):
    """(end of the line before, start of this line) around a speech onset.
    Uses the quietest pause list that hears a pause in that gap (-38, then -35, then -32 dB) and widens by MARGIN each side."""
    pf = pause_at(on, lists['fine'])
    pz = None
    for name in ('strict', 'coarse'):
        q = pause_at(on, lists[name])
        if q and (pf is None or q[0] >= pf[0] - 0.05): pz = q; break
    pz = pz or pf
    if pz is None: return round(on - 0.25, 2), round(on - MARGIN, 2)
    a, b = pz
    m = min(MARGIN, max(0.03, (b - a) / 2 - 0.03))
    return round(a + m, 2), round(b - m, 2)


def end_after(t, lists, within=15.0):
    """Where a line ends when nothing follows it: the next real pause after t, plus the margin."""
    for name in ('strict', 'coarse', 'fine'):
        after = [s for s in lists[name] if s[0] > t + 0.3 and s[0] - t < within]
        if after: return round(after[0][0] + MARGIN, 2)
    return round(t + 4, 2)


def ffprobe_duration(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def syllables(phon, syl=''):
    """Rough length of a line for sharing out time: Cherokee letters if there are any, else vowel groups in the phonetics."""
    n = len(re.findall(r'[Ꭰ-᏿ꭰ-ꮿ]', syl or ''))
    if n: return n
    return max(1, len(re.findall(r'[aeiouv]+', (phon or '').lower())))
