# The book format in detail

## Folder (one per book, e.g. `Cher231/Trick or Treat Danny/Read Along/`)

| Path | What |
|---|---|
| `<Title> sentences.xlsx` | The source of everything editable: sentences, times, pages, settings. Exactly one .xlsx in the folder. |
| `template.html` | The page. Copied from the skill's `assets/`; edit only to change behaviour for every future book too (then copy the change back to the skill). |
| `build_book.py` | Spreadsheet + template → `index.html`. Run after every spreadsheet edit. |
| `build_standalone.py` | `index.html` → one file (`<file_name or title_en>.html`, 10–20 MB) with pictures, audio and fonts embedded; opens from a USB stick or an email with no internet. |
| `index.html` | The built page. Needs `images/`, `audio/`, `fonts/` beside it. This is what gets published as an artifact or put on the hub. |
| `images/page-NN.jpg` | One picture per page, NN = the book's page number (cover = 1). Portrait or landscape both work; ~1275 px on the long side is plenty. |
| `audio/narration.mp3` | The one recording. 192 kbps, 48 kHz. |
| `fonts/` | Noto Sans Cherokee 400/600 (Cherokee + Latin subsets), Nunito 400/600/700, Patrick Hand 400, and `fonts.css`. Only the standalone build uses them; index.html loads the same fonts from Google. |
| `text/` | Pause lists written by `scripts/detect_pauses.py` (`silences-fine.txt` -32 dB, `silences.txt` -35 dB, `silences-strict.txt` -38 dB). Embedded by build_book.py for Time it mode. |
| `build/` | Anything used to make the book but not needed to run it: source dumps, alignment scripts, probe sheets, screenshots from check_book.js. |
| `timings.csv` | Temporary: written by Time it mode, consumed by `scripts/apply_timings.py`, which deletes it. Never leave one lying around (build_book.py would silently prefer it over the spreadsheet). |

## Spreadsheet

**Sentences** (one row per spoken sentence; the row order is the reading order):

| Column | Meaning |
|---|---|
| Line | 1, 2, 3 … or `title` for the spoken title that plays over the cover when Begin is pressed. |
| Page | Book page number the sentence belongs to (several rows may share a page). |
| Start (s), End (s) | Seconds into audio/narration.mp3. Lines on one page play continuously from the first Start to the last End; the caption changes at each Start. The page stops at the last End, so End must sit inside the pause after the last word (see timing.md). |
| Phonetics, Syllabary, English | The three caption lines. Syllabary cell font is Noto Sans Cherokee. |
| Check notes | Yellow when filled: anything she should look at (a PDF-vs-Word difference, a guessed timing, syllabary Claude typed). She clears notes as she checks them. |

**Pages** (one row per picture, in order):

| Column | Meaning |
|---|---|
| Page | Book page number; must match the Sentences Page values. Pages with no sentences are shown silently (Play all moves on after 3 s). |
| Image file | `images/page-NN.jpg` |
| Caption zone top, bottom | Fractions of the page height (0 top, 1 bottom) between which the live caption is centred, normally where the printed text was on that page. Cover: low (0.72–0.86) so it clears the Begin panel. |
| Motion | `zoom in`, `zoom out`, `pan left`, `pan right`, `drift`, `hold` (cover and back cover: hold). Very gentle (3.5 % zoom over 22 s). |
| Description | Alt text for the picture. |
| Effect | blank or `flicker` (slow brightness flicker, for candle or jack-o'-lantern pages). |

**Settings** (Setting, Value, What it does): `title_syl`, `title_phon` (top bar), `title_en` (cover and default file name), `credit` (cover line: Written by · Translated by · Read by · Edited by · © year), `file_name` (standalone file name, optional), `audio`, `pause_seconds` (Play all pause between pages, 1.5), `text_default` on/off, `show_syllabary` / `show_phonetics` / `show_english` yes/no, `fade_seconds` (0.6), `line_gap_seconds` (0; seconds shaved off a page's last End, keep 0), `bg_color`, `accent_color` (optional colours; default navy and orange), `storage_key` (optional name for the browser's memory of text choices and tapped timings).

**How to edit**: plain-language instructions for her, written by new_book.py.

## What the page does

- Cover: picture + English title + credit + **Begin**. Begin plays the `title` line (if any) over the cover, then turns to page 1 and plays it.
- Each page: picture fitted inside the stage (portrait books get a tall page with the navy around it), caption panel at the caption zone, lines play in order with a short dip between captions. Arrows, swipe, ← → keys, space replays the page.
- **Text** pill hides the caption; ᏣᎳᎩ / phonetics / English chips choose the lines. Remembered per browser.
- **Play all**: plays every page in turn with `pause_seconds` between; stops at the back cover and returns to the cover. P key.
- **Time it**: timing mode. Play, tap space at each line's first sound, ← → nudge the last tap 0.2 s, Back one, Hear this line, Finish and save (saves to the browser and offers `timings.csv`; inside the claude.ai artifact viewer it shows the CSV in a text box to copy, because the viewer blocks downloads). Taps are moved back to the start of the speech they reacted to (people tap 0.3–1 s late) and widened by the margins before saving.
- Full screen button (F). Safari and iPad: the first tap also unlocks audio (a silent play/pause).
- Fonts: Noto Sans Cherokee for syllabary, Nunito for phonetics and controls, Patrick Hand (handwriting) for English.
- Live-update hook: when republished as an artifact the viewer keeps the page the reader was on.

## Building

```
python3 build_book.py                # → index.html
python3 build_standalone.py          # → "<title>.html" (one file)
node scripts/check_book.js .         # optional: opens it in headless Chromium, screenshots in build/shots
```
Needs Python 3 with openpyxl (her Mac has it); the standalone build needs nothing else.

## Publishing

- Artifact: publish `index.html` with the book folder as root and `images/…`, `audio/…` as files (fonts are not needed, Google Fonts serves them). Republish the same path to keep the URL; images and audio stay uploaded.
- Her Mac: the book folder under `Cher231/<Book>/Read Along/` (device_commit_files with the project copy as stagedPath). Also keep a copy in the project's shared folder.
- Hosting on wespeakcherokee.org (a subdomain per book or game) was discussed but not set up as of 2026-10-19.
