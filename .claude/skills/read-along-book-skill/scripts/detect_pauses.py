#!/usr/bin/env python3
"""Find the pauses in the narration at three loudness thresholds (needs ffmpeg).

    python3 scripts/detect_pauses.py                     (audio/narration.mp3 → text/silences*.txt in the book folder)
    python3 scripts/detect_pauses.py audio/narration.mp3 --out text

Writes silences-fine.txt (-32 dB, ≥0.25 s: hears every little gap), silences.txt (-35 dB, ≥0.35 s) and
silences-strict.txt (-38 dB, ≥0.3 s: edges hug the words least). Each file: a header line, then "start-end(length)" tokens.
build_book.py embeds them so Time it mode can put line starts and ends just outside the pauses.
"""
import argparse, os, re, subprocess

SETS = [('silences-fine.txt', -32, 0.25), ('silences.txt', -35, 0.35), ('silences-strict.txt', -38, 0.3)]


def detect(audio, db, dur):
    cmd = ['ffmpeg', '-hide_banner', '-nostats', '-i', audio, '-af', f'silencedetect=noise={db}dB:d={dur}', '-f', 'null', '-']
    log = subprocess.run(cmd, capture_output=True, text=True).stderr
    starts, out = [], []
    for line in log.split('\n'):
        m = re.search(r'silence_start: ([\d.]+)', line)
        if m: starts.append(float(m.group(1)))
        m = re.search(r'silence_end: ([\d.]+) \| silence_duration: ([\d.]+)', line)
        if m and starts: a = starts.pop(0); b = float(m.group(1)); out.append((a, b))
    if starts: out.append((starts[0], starts[0] + 999))      # silence running to the end of the file
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('audio', nargs='?', default='audio/narration.mp3')
    ap.add_argument('--out', default='text')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for name, db, dur in SETS:
        p = detect(a.audio, db, dur)
        toks = ' '.join(f'{s:.2f}-{e:.2f}({e - s:.2f})' for s, e in p)
        with open(os.path.join(a.out, name), 'w', encoding='utf-8') as f:
            f.write(f'{len(p)} silences (ffmpeg silencedetect noise={db}dB d={dur} on {os.path.basename(a.audio)})\n{toks}\n')
        print(f'{name}: {len(p)} pauses')


if __name__ == '__main__':
    main()
