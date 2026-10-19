# Spearfinger read-along movie

A paper-theatre read-along movie of the Spearfinger picture book
(ᎪᏍᏓᏱ ᏗᎦᏘᏍᏙᏗ ᎦᏰᏌᏛᎢ): the 27 cut-paper illustrations, Nannie Taylor's 27
narration tracks, and the Cherokee text in a column beside the picture with the
current word highlighted. The book is a title card, 27 page movies and the
credits, joined into `out/Spearfinger.mp4` (1080p) and
`out/Spearfinger-720p.mp4`.

Decisions taken while building it, and what still needs a person, are in
[DECISIONS.md](DECISIONS.md). The text check (PDF syllabary against the gloss
phonetics) is [text/check-log.md](text/check-log.md).

## Folder layout

```
spearfinger/
  assets-src/Spearfinger042109_001.tif … _027.tif   the 27 pages, 1200 x ~945 px
  assets-src/Spearfinger_01.mp3 … _27.mp3           cleaned narration, one track per page (see "Audio")
  sources/spearfinger readable1.pdf                 July 2008 proof: the syllabary shown in the movie
  SpfingerGloss121808.doc                           Dec 2008 gloss: the phonetics shown
  fonts/                                            Noto Sans Cherokee, Noto Serif, Noto Serif Italic
  text/phrase_breaks.json                           where each page's phrases end, and their English
  text/phrasesNN.json, text/check-log.md            made by make_text.py
  pages/NN.json                                     pieces, depth and story beat of pages 1–26
  scripts/                                          the pipeline (below)
  work/pageNN/                                      per-page data; timingNN.json/.csv are committed,
                                                    the rest is rebuilt by the scripts
  work/page27/                                      page 27's hand-built layers (committed)
  out/                                              rendered movies (not committed)
```

## The look

* **Paper theatre.** Every cut shape is its own layer. Pieces slide, tilt,
  sway, drop or are placed on the page; nothing bends or warps.
* **Stepped motion.** Character motion runs at 12 steps a second so it reads as
  stop-motion; camera drift and text are smooth (24 fps).
* **Gentle camera.** A slow zoom of about 3.5 % over each page, with parallax
  (far trees move less than the figures).
* **One story beat per page**, timed to words in the narration. Each page's
  beat is described in the `"beat"` line of `pages/NN.json`.
* **Read-along column.** The page sits on a cream card at the left of the 16:9
  frame; the column on the right shows syllabary, phonetics and English for
  each phrase, scrolls so the current phrase is centred, fades at its top and
  bottom edges, and highlights the current word in both Cherokee lines.
* **Lead-in.** Each page fades up and the narration starts 1.8 s in; it ends
  2.6 s after the narration with a fade to cream, so pages follow each other
  with a dip to cream.

## Requirements

Python 3.11+ with `pillow`, `numpy`, `scipy` (and `python-docx` for
`make_text.py`), `ffmpeg`/`ffprobe`, `pdftotext` (poppler) and LibreOffice
(`soffice`, to read the .doc). Fonts are in `fonts/`. Frames need about 1 GB of
scratch space per page while rendering; they are deleted after encoding.

## Rebuilding the book

Run everything from the `spearfinger` folder.

```
python3 scripts/make_text.py          # text/phrasesNN.json + text/check-log.md
sh scripts/render_all.sh              # all 27 pages (or: sh scripts/render_all.sh 3 7 12)
python3 scripts/cards.py              # title card and credits
python3 scripts/assemble.py           # out/Spearfinger.mp4 and out/Spearfinger-720p.mp4
```

`render_all.sh` runs, for each page, the steps below that are not already
done. To redo one page after changing its page file:
`python3 scripts/build_pieces.py NN && python3 scripts/animate.py NN render`.

### 1. Text — `make_text.py`

Takes the syllabary from the July 2008 PDF (left half of each spread, read with
`pdftotext -bbox-layout`) and the phonetics from the December 2008 gloss,
aligns the two word by word, and splits each page into phrases at the word
numbers in `text/phrase_breaks.json`, which also holds the English for each
phrase. Every word where the PDF and the gloss disagree is listed in
`text/check-log.md`. To change a phrase break or an English line, edit
`phrase_breaks.json` and rerun.

### 2. Scan and segment — `prep_page.py NN`

Converts the TIF to `work/pageNN/pNN.png` and runs `segment.py`, which
separates paper-cut from paper, k-means the colours, labels the connected
components and writes `compsNN.json/.npy` and `components_preview.png` (every
component numbered).

### 3. Pieces — `build_pieces.py NN`

`pages/NN.json` `"pieces"` names the pieces that move, each a list of component
ids or a selector (`box`, `ids`, `add`, `drop`, `min_area`, `cut`; see the
script's docstring). Components no piece claims stay painted on the paper.
The script cuts the pieces out, inpaints the paper behind them, orders
overlapping pieces from the real cut-edge shadows (`"back"`/`"front"`
override), gives each piece a 12 px underfill so small moves never show a
hole, and prints the mean difference between the rebuilt page and the scan
(all pages are under 0.5).

### 4. Timing — `timing.py NN`

Finds the pauses in the track with `ffmpeg silencedetect` (trying stricter
thresholds until there are enough), places phrase boundaries on pauses close
to where the syllable count says they should fall, and spreads the words of
each phrase by syllable count. Output: `work/pageNN/timingNN.json` (used by
the renderer) and `timingNN.csv` (for people).

**This is a first pass.** Whisper cannot transcribe Cherokee, so nothing
listens to the words. Every page needs a listen: note where the highlight runs
ahead or behind, correct the seconds in the CSV, then
`python3 scripts/timing.py NN --from-csv` and re-render the page.

### 5. Animate and render — `animate.py NN test|render`

`test` writes a few frames to `work/pageNN/prev/`; `render` writes every frame
and encodes `out/pageNN.mp4` with the narration. The motion vocabulary (move,
rotate, scale, fade, hide, away, sway, flicker, bob, jab, shake, path, glint,
fall, swap) and the time specs (`"p3"` start of phrase 3, `"p3w2"` word 2,
`"p3e"` its end) are documented at the top of the script. Page 27 keeps its
own hand-made beats in `page27_beats.py`. `frame.py` holds what every page
shares: the frame, card, camera, fades and the text column.

Another text combination: `SF_TEXT=syl+eng sh scripts/render_all.sh` then
`SF_TEXT=syl+eng python3 scripts/assemble.py` (writes `Spearfinger_syl+eng.mp4`).

### 6. Cards and assembly — `cards.py`, `assemble.py`

The title card shows the cover picture (page 9) with the printed title and the
makers; the credits add Sara's credit line and the colophon. `assemble.py`
joins title, pages 1–27 and credits without re-encoding, then makes the 720p
copy.

## Audio

`assets-src/Spearfinger_NN.mp3` are the narration tracks, processed on
19 Oct 2026 by `scripts/clean_audio.py` from the April 2009 AIFFs: mono (the
AIFF channels were identical), high-pass at 75 Hz, light noise reduction,
gentle 2:1 compression, loudness normalised to -19 LUFS / -1.5 dBTP, MP3 VBR
q3. No trimming, so every timing applies to the AIFF as well.

## Interactive version (later)

The same pieces, page files and timing files can drive a web page: each piece
an absolutely positioned image moved with CSS keyframes, the audio in an
`<audio>` element, and the text column highlighting from `timingNN.json`, with
a tap on any word seeking to it and toggles for syllabary, phonetics and
English.
