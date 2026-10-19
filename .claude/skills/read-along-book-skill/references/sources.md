# Getting pages, text and sound out of her source files

Her message usually says: look over the folder first. Do that before building anything: list the folder on her Mac,
note dates (the newest dated file is the final version unless she says otherwise), and tell her what you found and
what you will use. Her books so far: a story recorded by a speaker with the pictures shown in a video, or a set of
sentences recorded line by line with new pictures made in Copilot or Firefly.

## Pages

- **Photoshop / InDesign PDF with the text in its own layer** (Trick or Treat, Danny: `/Im0 Do` picture, then `BT 7 Tr … ET`
  text used as a clip, then `/Im1 Do` a flat colour fill through the clip): `scripts/strip_pdf_text.py book.pdf --pages 5-24`
  removes the text objects and every image draw after the first, then renders with pdftoppm at 150 dpi. Look at every
  page afterwards. If a page lost artwork, rerun that page with `--keep-images`.
- **Flattened PDF or scans** (text baked into the picture): render with `pdftoppm -r 150 -jpeg`; the printed text stays,
  so either set `text_default` to off and place the caption elsewhere, or ask her for the layered file.
- **Pictures she generated** (Copilot Designer PNGs, Firefly): copy and rename to `images/page-NN.jpg` (convert with PIL,
  quality 88). Keep the originals in `build/` or leave them where they are.
- Caption zone = where the printed text sat on that page (measure on a contact sheet: `pdftoppm -r 30` or PIL thumbnails
  in a grid, note top/bottom fractions). Don't trust PIL for CMYK JPEGs (colours invert); render with pdftoppm instead.

New art for a book she is making from a transcript: she wants a loose hand-drawn pencil-and-watercolour picture-book
look, "not too exact and AI", no page of Grandma holding a book (the pictures are the book). Copilot prompts for her
to run; she generates, Claude lays out. Save prompts as a .md beside the book.

## Text

- Her Word files hold English / phonetics / syllabary triplets per sentence (sometimes a sentence wraps onto a second
  triplet: merge a triplet into the previous one when the previous English does not end in . ! ? ” ]).
- Where the final PDF's text and the Word file differ, the PDF wins; write each difference into Check notes
  (e.g. "Word file “Ꮣ” → PDF “Ꮵ”"). Text from a PDF comes out one short line at a time: join lines until a sentence end,
  and attach a stray leading ” or . to the previous sentence.
- Syllabary that Claude typed or converted (a cover title read off artwork, a transliteration) is unconfirmed: say so in
  the note and the reply. Reverse transliteration (syllabary → phonetics) uses `unicodedata` names
  (CHEROKEE LETTER TSI → tsi) but her phonetics spell some syllables differently (ukatv not ukadv): keep her spelling
  and patch only the words that changed.
- Check her materials first for any Cherokee word; Siyo and Sgi, not Osiyo and Wado. Spelling and recording doubts are
  questions to her, never statements.

## Sound

- From a video: `ffmpeg -i book.mov -vn -ar 48000 -b:a 192k audio/narration.mp3`. ProRes files are huge; copy nothing,
  read in place on her Mac (device_bash, 180 s per call, so chunk long jobs).
- From line clips (her Logic exports: 192 kbps MP3, silence trimmed, 0.5 s quiet each end, WAVs untouched):
  `scripts/make_narration.py "clips/line *.mp3"` joins them with 0.7 s gaps, writes Start/End and the pause lists.
- Whisper only runs on her Mac and only knows English; Cherokee comes out garbled. Use it, if at all, to find where
  English or numbers are, and check everything against the audio by ear (hers).
- Missing recordings: the page simply skips untimed lines (warning from build_book.py); deliver anyway and list them.

## Delivering

1. Build, standalone, check_book.js, look at the screenshots.
2. Publish index.html as an artifact (private; she shares it herself). Keep the same artifact for later versions.
3. Copy the folder to her Mac under `Cher231/<Book>/Read Along/` and to the project's shared folder.
4. Reply: the link, where the files are, what is machine-guessed, and the questions only she can answer: narrator and
   credit line, title spelling, PDF-vs-Word differences, which pages (credits, title page, blank) to leave out, hosting.
5. Expect a second pass: her taps for timing (apply_timings.py), her spelling rulings (edit the sheet, clear the note),
   then rebuild, republish, recopy, and record her rulings in project memory.
