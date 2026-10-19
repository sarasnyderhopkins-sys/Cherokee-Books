#!/usr/bin/env python3
"""Join separately recorded line clips into one narration file and write each line's Start/End into the spreadsheet.

    python3 scripts/make_narration.py "clips/line *.mp3" [--gap 0.7] [--title-clip clips/title.mp3] [--xlsx FILE]

Clips are taken in natural filename order (line 1, line 2, … line 10) and matched to the Sentences rows in order
(the 'title' row takes --title-clip if given). Output: audio/narration.mp3 (192 kbps, 48 kHz) with `gap` seconds of
silence between clips, Start/End filled in, and the pause lists refreshed (detect_pauses.py). Needs ffmpeg and ffprobe.
Her clip convention: 192 kbps MP3, silence trimmed, 0.5 s quiet at each end; WAVs untouched.
"""
import argparse, glob, os, re, subprocess, sys
from openpyxl import load_workbook
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ffprobe_duration, find_xlsx, key_of
import detect_pauses


def natural(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', os.path.basename(s))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('clips', help='glob for the line clips, in quotes')
    ap.add_argument('--gap', type=float, default=0.7)
    ap.add_argument('--title-clip')
    ap.add_argument('--xlsx')
    ap.add_argument('--out', default='audio/narration.mp3')
    a = ap.parse_args()
    folder = os.getcwd()
    xlsx = find_xlsx(folder, a.xlsx)
    clips = sorted(glob.glob(a.clips), key=natural)
    if not clips: sys.exit(f'no clips match {a.clips}')

    wb = load_workbook(xlsx)
    ws = wb['Sentences']
    rows = [(key_of(r[0].value), r) for r in ws.iter_rows(min_row=2) if key_of(r[0].value)]
    title_row = next((r for k, r in rows if k == 'title'), None)
    line_rows = [r for k, r in rows if k != 'title']
    if len(line_rows) != len(clips):
        print(f'warning: {len(clips)} clips but {len(line_rows)} sentence rows; matching in order as far as they go')

    plan = []                                                   # (row, clip)
    if a.title_clip and title_row is not None: plan.append((title_row, a.title_clip))
    plan += list(zip(line_rows, clips))

    t = 0.0
    inputs, filters = [], []
    for i, (row, clip) in enumerate(plan):
        d = ffprobe_duration(clip)
        row[2].value, row[3].value = round(t, 2), round(t + d, 2)
        if len(row) > 7 and row[7].value: row[7].value = re.sub(r'\s*Timing guessed[^.]*\.', '', str(row[7].value)).strip() or None
        inputs += ['-i', clip]
        filters.append(f'[{i}:a]aresample=48000,aformat=channel_layouts=stereo,apad=pad_dur={a.gap}[a{i}]')
        t += d + a.gap
    fc = ';'.join(filters) + ';' + ''.join(f'[a{i}]' for i in range(len(plan))) + f'concat=n={len(plan)}:v=0:a=1[out]'
    os.makedirs(os.path.dirname(os.path.join(folder, a.out)) or '.', exist_ok=True)
    subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error'] + inputs + ['-filter_complex', fc, '-map', '[out]',
                    '-c:a', 'libmp3lame', '-b:a', '192k', os.path.join(folder, a.out)], check=True)
    for r in wb['Settings'].iter_rows(min_row=2):
        if r[0].value == 'audio': r[1].value = a.out
    wb.save(xlsx)
    print(f'wrote {a.out} ({t - a.gap:.1f} s) and Start/End for {len(plan)} lines into {os.path.basename(xlsx)}')
    sys.argv = ['detect_pauses.py', os.path.join(folder, a.out), '--out', os.path.join(folder, 'text')]
    detect_pauses.main()


if __name__ == '__main__':
    main()
