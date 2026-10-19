---
name: read-along-book-skill
description: Build a Cherokee read-along picture book (a web page plus a single offline file) from page pictures, one narration recording and the sentences in syllabary, phonetics and English, in the format of the Halloween picture book and Trick or Treat, Danny. Use for any read-along, picture book, animated book or story page with audio and captions, and for fixing timings, text or pages in one that exists.
---

# Read-along book

One HTML page per book: a cover with **Begin**, one picture per page fitted inside a navy stage, a live caption
(syllabary / phonetics / English, each switchable) sitting where the printed text used to be and fading with the
voice, one narration file in which every sentence has a Start and an End, **Play all** with a pause between pages,
arrows, swipe and keys, and a **Time it** mode where she taps along to fix the timing herself. A spreadsheet is the
source of all text, times and settings; `build_book.py` turns it into `index.html`; `build_standalone.py` makes one
file (10–20 MB) that plays from a USB stick. Finished examples: `Cher231/Halloween Picture Book/` and
`Cher231/Trick or Treat Danny/Read Along/` (same copies in the project folder).

Details live in `references/format.md` (folder, spreadsheet, page behaviour), `references/timing.md` (how Start/End
are found; the clipped-audio lesson) and `references/sources.md` (pages from PDFs, text from Word, sound from video).

## Skill files

- `assets/template.html`, `assets/build_book.py`, `assets/build_standalone.py`, `assets/fonts/`: copied into every book folder by `scripts/new_book.py`. Change them here when the change is for every book.
- `scripts/new_book.py` title → book folder with spreadsheet, template, build scripts, fonts.
- `scripts/strip_pdf_text.py` layered PDF → clean `images/page-NN.jpg`.
- `scripts/detect_pauses.py` narration → `text/silences*.txt`.
- `scripts/guess_timings.py` first-draft Start/End from the pauses (and page turns from a video).
- `scripts/apply_timings.py` her taps (`timings.csv` from Time it, or pasted raw taps with `--raw`) → spreadsheet.
- `scripts/make_narration.py` separately recorded line clips → one narration file with Start/End.
- `scripts/check_book.js` headless-browser smoke test with screenshots (needs Playwright; optional).

All scripts run from inside the book folder: `python3 /path/to/read-along-book-skill/scripts/<name>.py …`. They need
Python 3 with openpyxl (pypdf for the PDF one), ffmpeg/ffprobe and poppler; her Mac has all of these.

## Making a book

1. **Look over her folder first** and say what you found: which PDF or pictures are final (newest date unless she
   says otherwise), which recording, whether a video exists, which Word file has the text. Check her own materials
   before writing any Cherokee; Siyo and Sgi, never Osiyo and Wado. Doubts about spelling, pronunciation or a
   recording are questions to her, not statements.
2. **Pages** → `images/page-NN.jpg`, NN = the book's page number, cover = 1. Layered PDF: `strip_pdf_text.py`.
   Flattened PDF: `pdftoppm -r 150 -jpeg`. Her generated pictures: rename. Decide which pages to leave out (credits,
   title page, blanks) and say so; default is story pages plus front and back cover.
3. **Narration** → `audio/narration.mp3` (from a video: `ffmpeg -i x.mov -vn -ar 48000 -b:a 192k`). Line clips instead:
   make the spreadsheet first, then `make_narration.py`.
4. **Sentences** → `lines.tsv` (page, syllabary, phonetics, English; one sentence per line). Where the PDF and the Word
   file differ, the PDF wins and the difference goes in Check notes. Syllabary that Claude typed is marked unconfirmed.
5. `new_book.py "Title" --title-syl … --title-phon … --credit … --lines lines.tsv`, then fill the **Pages** sheet:
   caption zone (where the printed text was), motion, description.
6. **Timing**: `detect_pauses.py`, then `guess_timings.py` (with `--turns` from a video when there is one), build, and
   deliver that as the first draft; she taps along in Time it, then `apply_timings.py` and rebuild. Starts sit
   0.15 s before the first sound and ends 0.15 s after the last, measured on the quietest pause list; never tighter.
7. **Build and check**: `python3 build_book.py`, `python3 build_standalone.py`, `node scripts/check_book.js .`
   (or open index.html), look at the screenshots, play the first, a middle and the last page and listen for cuts.
8. **Deliver**: publish `index.html` as an artifact (root = book folder, files = images and audio), copy the folder to
   her Mac (`Cher231/<Book>/Read Along/`) and the project folder, and reply with the link, what is guessed, and the
   questions only she can answer (narrator and credit line, title spelling, text differences, pages left out, hosting).
   Later passes (her taps, her rulings) are edits to the spreadsheet, then rebuild, republish, recopy; put her rulings
   in project memory.

## Fixing a book that exists

- Text, spelling, which lines show: edit the Sentences or Settings sheet, `python3 build_book.py`, `python3 build_standalone.py`.
- Timing: she presses Time it on the page she wants to fix and taps; `apply_timings.py timings.csv` (or paste → `--raw`).
  Compare page starts and ends with the previous version before delivering: a start that got later or an end that got
  earlier needs a reason. Delete any `timings.csv` once applied.
- A new picture: replace the file in `images/`, keep the name.
- Behaviour for every book: change `assets/template.html` in this skill, copy it into the book folder, rebuild.

## Pitfalls already met

- Edges set at -32 dB pauses, or any shaving off the last End, clip words; she hears it at once. Use the margins.
- One `pic.onload` handler left over from the cover fired on later pages and skipped them in Play all; the template
  guards page loads with a generation counter and `decode()`. Keep that when editing.
- `Number(setting) || default` turns a deliberate 0 into the default. Check for empty before defaulting.
- Safari and iPad need the first tap to unlock audio; the template does a silent play/pause on Begin.
- The claude.ai artifact viewer blocks downloads: Time it shows the CSV in a text box there instead.
- Her Mac does not let a session overwrite a file she made; Claude's own earlier outputs may be replaced. New
  versions of her files land as copies until she OKs a swap.
- A 9 GB ProRes video: read it in place on her Mac, in chunks under the 180 s call limit; never copy it.
