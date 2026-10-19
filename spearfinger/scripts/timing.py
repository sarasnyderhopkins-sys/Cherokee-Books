"""Step 5: first-pass phrase and word timings for one page.

   python3 scripts/timing.py NN        (from the spearfinger folder)

Reads text/phrasesNN.json and assets-src/Spearfinger_NN.mp3. Finds the pauses in the track
(ffmpeg silencedetect, -30 dB, 0.18 s), puts each phrase boundary on a pause (dynamic programming:
prefer long pauses close to where the syllable count says the boundary should fall), then spreads the
words of each phrase over its speech in proportion to syllable count. Starts sit 0.1 s before the
sound and phrase ends 0.1 s after it, so the highlight never runs ahead of the voice.
Writes work/pageNN/timingNN.json (for the renderer) and timingNN.csv (for people to correct).
Whisper cannot transcribe Cherokee, so this is a first pass: listen and fix the CSV, then
   python3 scripts/timing.py NN --from-csv     to rebuild the JSON from the corrected CSV.
"""
import json, re, sys, os, csv, subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARGIN = 0.10

def nsyl(w): return sum(1 for ch in w if 'Ꭰ' <= ch <= 'Ᏼ' and ch != 'Ꮝ') or 1

def silences(audio, db=-30, d=0.18):
    out = subprocess.run(['ffmpeg', '-hide_banner', '-i', audio, '-af', f'silencedetect=n={db}dB:d={d}', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', out)]
    ends = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', out)]
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', audio],
                               capture_output=True, text=True).stdout)
    if len(ends) < len(starts): ends.append(dur)
    return list(zip(starts, ends)), dur

def word_times(ws, t0, t1, chunks):
    """spread words over the speech between t0 and t1 (skipping pauses) by syllable count"""
    cs = [(max(a, t0), min(b, t1)) for a, b in chunks if b > t0 and a < t1]
    if not cs: cs = [(t0, t1)]
    speech = sum(b - a for a, b in cs); total = sum(nsyl(w) for w in ws)
    def at(s):
        f = s / total * speech; acc = 0
        for a, b in cs:
            if acc + (b - a) >= f - 1e-9: return a + (f - acc)
            acc += b - a
        return cs[-1][1]
    out = []; cur = 0
    for w in ws:
        n = nsyl(w); out.append((at(cur), at(cur + n))); cur += n
    return out

def main():
    n = int(sys.argv[1]); W = f'{HERE}/work/page{n:02d}'; os.makedirs(W, exist_ok=True)
    phrases = json.load(open(f'{HERE}/text/phrases{n:02d}.json'))
    audio = f'{HERE}/assets-src/Spearfinger_{n:02d}.mp3'
    if '--from-csv' in sys.argv:
        rows = list(csv.DictReader(open(f'{W}/timing{n:02d}.csv')))
        sil, dur = silences(audio)
        chunks = speech_chunks(sil, dur)
        out = []
        for i, (p, r) in enumerate(zip(phrases, rows)):
            out.append(build_phrase(i, p, float(r['start']), float(r['end']), chunks))
        save(n, W, out); return
    # the tracks' noise floors differ: take the quietest threshold that finds enough pauses
    nwords = sum(len(p['syl'].split(' ')) for p in phrases)
    for db in (-34, -31, -28, -26, -24, -22, -20, -18):
        sil, dur = silences(audio, db)
        chunks = speech_chunks(sil, dur)
        sp0, sp1 = chunks[0][0], chunks[-1][1]
        inner = [(a, b) for a, b in sil if a > sp0 + 0.05 and b < sp1 - 0.05]
        if len(inner) >= max(3 * (len(phrases) - 1), nwords // 3): break
    # target boundary times from cumulative syllables over speech time
    syl = [sum(nsyl(w) for w in p['syl'].split(' ')) for p in phrases]
    speech = sum(b - a for a, b in chunks)
    def syl_time(s):
        f = s / sum(syl) * speech; acc = 0
        for a, b in chunks:
            if acc + (b - a) >= f: return a + (f - acc)
            acc += b - a
        return sp1
    targets = []; acc = 0
    for s in syl[:-1]:
        acc += s; targets.append(syl_time(acc))
    K = len(targets)
    # a boundary may also fall where the syllable count puts it, with no pause found (scored as a 0 s pause, minus a little)
    inner = sorted(inner + [(t, t) for t in targets])
    P = len(inner)
    if K and P >= K:
        # DP over boundaries: each phrase boundary sits in a pause; reward long pauses, penalise distance from the
        # syllable-count estimate and implausible speaking rates (seconds per syllable) for the phrase it closes
        rate = speech / sum(syl)
        def node(k, j):
            a, b = inner[j]; mid = (a + b) / 2
            return (0.8 * min(b - a, 1.0) if b > a else -0.4) - 3.0 * abs(mid - targets[k]) / (speech / len(phrases))
        def edge(k, t_prev_end, a_cur):
            d = a_cur - t_prev_end; r = d / syl[k] / rate        # 1.0 = average rate
            return -4.0 * max(0, 0.55 - r) - 1.5 * max(0, r - 1.8)
        INF = float('-inf')
        best = [[INF] * P for _ in range(K)]; back = [[-1] * P for _ in range(K)]
        for j in range(P): best[0][j] = node(0, j) + edge(0, sp0, inner[j][0])
        for k in range(1, K):
            for j in range(P):
                for i in range(j):
                    if best[k - 1][i] == INF: continue
                    v = best[k - 1][i] + node(k, j) + edge(k, inner[i][1], inner[j][0])
                    if v > best[k][j]: best[k][j] = v; back[k][j] = i
        def final(j): return best[K - 1][j] + edge(K, inner[j][1], sp1) if best[K - 1][j] > INF else INF
        j = max(range(P), key=final); picks = []
        for k in range(K - 1, -1, -1): picks.append(j); j = back[k][j]
        bounds = [inner[j] for j in picks[::-1]]
    else:
        bounds = [(t, t) for t in targets]
    out = []; t0 = sp0
    for i, p in enumerate(phrases):
        if i < K: t1, nxt = bounds[i]
        else: t1, nxt = sp1, None
        out.append(build_phrase(i, p, t0, t1, chunks))
        if nxt is not None: t0 = nxt
    save(n, W, out)
    print(f'page {n}: {db} dB, speech {sp0:.2f}-{sp1:.2f} s, {len(inner)} pauses, {len(phrases)} phrases')

def speech_chunks(sil, dur):
    chunks = []; t = 0.0
    for a, b in sil:
        if a > t + 0.05: chunks.append((t, a))
        t = b
    if dur > t + 0.05: chunks.append((t, dur))
    return [(a, b) for a, b in chunks if b - a > 0.06] or [(0, dur)]

def build_phrase(i, p, t0, t1, chunks):
    ws = p['syl'].split(' '); ps = p['pho'].split(' ')
    wt = word_times(ws, t0, t1, chunks)
    words = [dict(syl=w, pho=ps[j] if j < len(ps) else '', start=round(max(0, a - (MARGIN if j == 0 else 0)), 2),
                  end=round(b + (MARGIN if j == len(ws) - 1 else 0), 2)) for j, (w, (a, b)) in enumerate(zip(ws, wt))]
    return dict(idx=i + 1, start=words[0]['start'], end=words[-1]['end'], words=words, eng=p['eng'])

def save(n, W, out):
    json.dump(out, open(f'{W}/timing{n:02d}.json', 'w'), ensure_ascii=False, indent=1)
    with open(f'{W}/timing{n:02d}.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['phrase', 'start', 'end', 'syllabary', 'phonetic', 'english'])
        for p in out: w.writerow([p['idx'], p['start'], p['end'], ' '.join(x['syl'] for x in p['words']), ' '.join(x['pho'] for x in p['words']), p['eng']])

if __name__ == '__main__':
    main()
