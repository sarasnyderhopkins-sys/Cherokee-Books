# Spearfinger movie: decisions and things to check

Built overnight on 19 October 2026 without stopping to ask. Sara's rulings are
marked **(Sara)**; everything else is a judgment call made while building and
is open to change.

## Sara's rulings

* Build the paper-theatre movie, text column beside the picture, word-by-word
  highlighting. **(Sara)**
* Syllabary from the July 2008 PDF; phonetics from the December 2008 gloss;
  mismatches logged in `text/check-log.md`. **(Sara)**
* Spearfinger's name as the PDF spells it, without the li:
  ᎪᏍᏓᏱ ᏗᎦᏘᏍᏙᏗ ᎦᏰᏌᏛᎢ, including the title card. **(Sara)**
* Cover picture: the uploaded `SpearfingerWCU0009.tif`. **(Sara)** It is the
  same picture as page 9, so the title card uses the page 9 scan.
* Credit line, plus "Digital book created by Sara Snyder Hopkins". **(Sara)**
* Page 27 text follows the PDF. **(Sara)**

## Text calls to check

* **The English phrase splits are mine.** Each page's English was divided to
  match the Cherokee phrase breaks (`text/phrase_breaks.json`). A Cherokee
  speaker should confirm both where the phrases break and the English under
  each.
* **Two name typos in the PDF were corrected**: ᏗᎦᏥᏙᏗ (page 3) and ᏗᎦᎢᏍᏙᏗ to
  ᏗᎦᏘᏍᏙᏗ. Both are listed in the check log.
* **Phonetics can disagree with the syllabary above them.** 168 words are
  spelled differently in the PDF and the gloss; the phonetic line shows the
  gloss's form. 6 PDF words have no gloss entry and show a plain
  transliteration without tone or length marks.
* **The recording may follow a different text.** The narration is from April
  2009, after both the PDF (July 2008) and the gloss (December 2008). Where
  Nannie reads the later wording, the column will not match what is heard.

## Timing

* All 27 pages have **first-pass timings** from pause detection and syllable
  counts. No tool can recognise Cherokee speech, so each page needs a listen;
  the fix is a CSV edit (see README, step 4).

## Additions not asked for

* The credits end with a short colophon: © 2008 Luzene Hill; Galohisdi Press,
  Cullowhee, North Carolina, 2008; Western Carolina University Cherokee
  Language Program, with support from the Cherokee Preservation Foundation
  (from the book's colophon and production notes). Remove it in
  `scripts/cards.py` if unwanted.
* The text column fades softly at its top and bottom edges.

## Pictures: known rough spots

Moving a cut piece uncovers paper the scan never showed; the gap is filled by
blurring the surrounding paper. Small moves hide it, larger ones can leave a
faint pale ghost. Known spots:

* Pages 2, 5, 10: faint ghosts or streaks where pieces moved.
* Page 4: the shape-change is a shudder and flash rather than a swap of
  pieces (the monster and old woman are not separate shapes on the page).
* Page 12: smears around the jab, kept short so they barely show.
* Page 13: the men stay still; only the group motion is animated.
* Page 14: Spearfinger's arm is part of the fog shape, so "disappears into the
  fog" is the arm drawing back and the blade fading. A faint sliver at the
  fog's lower edge.
* Page 15: a thin pale strip at the left edge while the woman leans.
* Page 17: the big fire is not animated (its flames are woven through the
  logs); faint marks where the branch carrier was.
* Page 18: the hobble is small because a tree trunk runs behind her shawl.
* Page 19: a faint ghost where the top leaf was.

Each page's beat is the `"beat"` line in `pages/NN.json`.
