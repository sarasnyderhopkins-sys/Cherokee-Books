# Timing: how Start and End are found, and the lesson learned

## Pauses

`scripts/detect_pauses.py` runs ffmpeg's silencedetect three times on the narration:

| File | Threshold | Min length | Use |
|---|---|---|---|
| `text/silences-fine.txt` | -32 dB | 0.25 s | Hears every little gap, even between clauses. Used to understand where a tap belongs. |
| `text/silences.txt` | -35 dB | 0.35 s | Middle ground. First-draft page cuts. |
| `text/silences-strict.txt` | -38 dB | 0.3 s | A pause has to be really quiet, so its edges hug the words least. Preferred for the actual Start/End. |

A quieter threshold gives a *shorter* pause (soft word onsets and fading tails count as sound), so line edges taken from
it clip less. Pauses separated by a blip under 0.1 s count as one.

## The boundary rule (`_common.boundary`, same code in the page)

For the gap before a sentence: take the quietest list that hears a pause in that gap (-38, then -35, then -32 dB),
then **start = pause end − 0.15 s** and **previous line's end = pause start + 0.15 s** (margins shrink to fit a very short pause).
The last line of the book ends at the start of the closing silence + 0.15 s. `line_gap_seconds` stays 0.

Why: the first delivery of Trick or Treat, Danny set edges exactly at -32 dB pause boundaries and shaved 0.15 s more off
every page end. She heard clipped word starts and ends on many pages and said the machine guess (which had used the
-35 dB list with no shaving) was better. Never cut tighter than this rule; when in doubt, widen.

## Machine first draft (`scripts/guess_timings.py`)

Speech segments between pauses ≥ 0.45 s are shared out among the lines in proportion to sentence length (Cherokee
letters, or vowel groups in the phonetics), and each cut is snapped to the nearest pause. If a video of the book exists,
pass `--turns "page:seconds,…"`: page starts then snap to the pause nearest each page turn, which makes the first draft
good enough to show her (on Danny, 42 of 51 starts within 1.5 s; every page start right).

Getting page turns from a video (her books come as a ProRes .mov from the same recording session):

    ffmpeg -ss 0 -t 170 -i book.mov -vf "fps=1,scale=240:-1" -q:v 5 frames/f%04d.jpg     # in chunks; a 9 GB file is slow
    # then in Python: PIL, grayscale, mean absolute difference between consecutive frames >= 1.5 → a page turn at that second
    #   from PIL import Image, ImageChops, ImageStat
    #   ImageStat.Stat(ImageChops.difference(im, prev)).mean[0]

Also check the video's sound against the separate recording if both exist (Danny's .wav ran 3.02 s off after 8 s; the
.mov sound was used).

## Her taps (`Time it` mode → `scripts/apply_timings.py`)

She taps space when she hears each line start. Taps come 0.3–1.0 s after the first sound, so the page (and
`apply_timings.py --raw` for taps she pastes as text) moves each tap back to the end of the last pause within 1.3 s
before it; a tap inside a pause with no such burst means the line starts when that pause ends. Then the boundary rule
widens both sides. Expect one or two taps to land on a clause inside the previous sentence (on Danny, "no usqualv…"
sounded like the next line's "nole sgili…"); if a tapped start is impossibly early for its page, keep the page turn and
say so in Check notes and in the reply, and ask her to re-tap just that page (Time it starts from the page being viewed
and Finish saves only the lines marked).

`timings.csv` from the page already has the corrected times: `apply_timings.py` without `--raw` just copies them in,
fixes the End of the line before the first one, clears timing notes, deletes the csv. Rebuild afterwards.

## Checking

- Every page's first Start should be earlier than any sound of its first word, and the last End later than the last
  word's tail. Compare a new timing pass with the previous one page by page before delivering: a start that got later
  or an end that got earlier needs a reason.
- Play the first page, a middle page and the last page in a browser (or `scripts/check_book.js`) and listen for cuts.
