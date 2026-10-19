# Spearfinger read-along movie

A motion-graphics read-along of the Spearfinger picture book: 27 cut-paper
illustrations, the 27 narration tracks, and the Cherokee text from the gloss,
animated "paper-theatre" style and rendered as a movie (and, later, as an
interactive page).

Page 27 (the fire scene) is finished as the style sample:
`page27_sample.mp4`. Everything below describes how to take the other 26 pages
through the same pipeline and assemble the whole book.

## Folder layout

```
SpearfingerTotal/
  Spearfinger Illustrations and Audio/
    Spearfinger042109_001.tif … _027.tif   the 27 pages, 1200 x ~945 px, 300 dpi
    SpearfingerWCU0009.tif                  larger scan (2400 px), cover or poster
    Spearfinger009.jpg                      small web copy of page 9
    Spearfinger030408.pdf                   the printed book layout (syllabary text)
    Spearfinger.mov                         2009 slideshow, 640x480, for reference only
    SpearfingerSound/1 … 27 Audio Track.aiff   narration, one track per page
  SpfingerGloss121808.doc                   syllabary + phonetics + English, every page
  ReadAlong/                                THIS FOLDER (all new work goes here)
    README.md
    page27_sample.mp4                       the finished sample
    page27_timing.csv                       phrase timings for page 27, first pass
    audio/Spearfinger_01.mp3 … _27.mp3      cleaned narration (see "Audio")
    audio/loudness_report.csv
    scripts/                                the pipeline (see below)
    work/page27/                            layers and data for page 27
```

Track N narrates page N. Durations run 8 s (page 9) to 52 s (page 27), about
12 minutes in all.

## What the sample does, and the rules it follows

* **Paper theatre.** Every cut shape is its own layer with a soft synthetic
  shadow. Pieces slide, drift, tilt or are "placed" on the page. Nothing bends
  or warps: paper does not do that.
* **Stepped motion.** Character beats (flames, a figure moving) run at 12 steps
  a second so they read as stop-motion. Camera drift and text are smooth (24 fps).
* **Gentle camera.** One slow drift plus a 3.5 % zoom over the page. Layers move
  at different rates: trees 0.35, people 0.65, the action 0.85, notes 1.0.
* **One story beat per page**, timed to the narration. Page 27: the song path
  draws itself out of the fire when "the people heard songs" and notes travel
  up it; the listeners lean in; Spearfinger sinks into the fire.
* **Read-along column.** The 4:3 page sits on a cream card at the left of a
  16:9 frame; the right column shows the text for each phrase, scrolling so
  the current phrase is centred, with the current word highlighted.
* **Three text lines, each toggleable.** Syllabary, phonetics and English are
  three separate lines that the viewer can switch on or off independently.
  In the interactive version they are real toggles (see below). A movie file
  cannot toggle, so the renderer takes a `--text` option naming the lines to
  show (`syl`, `syl+pho`, `syl+eng`, `syl+pho+eng`, `eng`, ...) and the book is
  exported in whichever combinations are wanted; the column re-flows and
  re-centres for the lines that are present. Default for the first export:
  all three. The sample shows all three.
* **Lead-in.** Pieces are placed on the page during the first 1.8 s, then the
  narration starts. All phrase times in the CSVs are seconds into the
  narration, not into the video.

## Requirements

* Python 3.11+ with `pillow`, `numpy`, `scipy` (a venv is fine).
* `ffmpeg` / `ffprobe` on the PATH.
* Fonts. `scripts/animate.py` has the font paths at the top. On a Mac it uses
  the bundled Plantagenet Cherokee, Charter and Georgia. On Linux/cloud, install
  Noto Sans Cherokee (syllabary) and Noto Serif (phonetics/English) and change
  `FONT_DIR` and the four `font(...)` lines. Do not copy Apple's fonts off the Mac.
* About 1 GB of scratch space per page for frames (JPEG), deleted after encoding.

## The pipeline, page by page

The scripts were written for page 27 and still have "27" in a few file names
(`p27.png`, `comps27.*`, `path27.json`, `timing27.json`, `phrases27.json`).
**Step 0 is to make them take a page number** (one `PAGE` variable per script,
and one `pages/NN.json` config holding the piece groups and the story beat), so
that the steps below are the same command for every page. Nothing else about
them is page-specific except what is marked below.

### 1. Export the scan
`sips -s format png Spearfinger042109_0NN.tif --out work/pageNN/pNN.png`
(or Pillow). Keep the full 1200 px width; do not crop.

### 2. Segment into cut pieces
```
python segment.py work/pageNN/pNN.png  work/pageNN/compsNN.json  work/pageNN/compsNN.npy  work/pageNN/components_preview.png
```
It separates paper from paper-cut (white vs everything else), k-means the
colours into 12 classes (seeded with the book's palette; add a seed colour if a
page has a new paper colour, e.g. the purple robe or the autumn oranges),
labels connected components per class, absorbs specks under 400 px into their
neighbours, and prints every component with its id, colour, area and bounding
box. Open `components_preview.png`: each piece is numbered.

### 3. Name the pieces (the only hand step per page)
In `build_pieces.py`, the `groups` dict maps names to component ids
(move it to `pages/NN.json` in step 0). Decide:

* **Depth tier** of each group (far: trees, clouds, distant ground; mid: people,
  bushes; action: the thing the page is about; front: anything that travels).
* **Which pieces animate on their own** (each flame tongue was its own group
  on page 27, named `flame_<id>`, so they could flicker independently).
* **What must stay joined.** Two shapes of the same paper that touch become one
  component (page 27: the right tree trunk and both listeners' black hair).
  Either keep them as one layer, or split the component with a hand-drawn
  polygon mask. Splitting is worth it only when the two parts need different
  motion.

`build_pieces.py` then writes `work/pageNN/pieces/<name>.png` (RGBA, cropped),
`paper.png` (the page with every hole inpainted and the cut shadows removed)
and `manifest.json` (position, z-order, pivot at the bottom centre of each
piece). It also orders overlapping pieces by reading the real cut-edge shadows
(the piece whose edge is darker is underneath) and gives every piece a 12 px
"underfill" of its own colour wherever it is hidden by a piece in front, so a
small movement never shows white paper. It prints the mean difference between
the rebuilt page and the scan; expect under 0.5 (page 27: 0.27).

### 4. Text for the page
Make `work/pageNN/phrasesNN.json`: a list of phrases, each with `syl`
(syllabary), `pho` (phonetics) and `eng`. Copy from `SpfingerGloss121808.doc`
(convert with `textutil -convert txt`). The gloss is marked up: `*` on a line
means it changed; `*x*` one letter changed, `**` a letter deleted, `*word` a
word changed, `*` alone a word deleted. Write the corrected form and drop the
marks. A phrase is a natural spoken unit of 3 to 8 words, one English clause.
The syllabary and phonetic word counts must match (they highlight together).

The gloss is from Dec 2008 and the narration from April 2009. Where the gloss
says the lines "change a lot" (page 27, and check others), the recording may
not match the text. Sara decides what the column shows.

### 5. Timing
```
python timing.py work/pageNN   (after step 0; it reads phrasesNN.json)
```
It finds pauses in the track (`ffmpeg silencedetect`, -24 dB, 0.2 s), spreads
the phrases over the speech between pauses in proportion to syllable count,
snaps phrase boundaries to the nearest pause, and splits words inside a phrase
the same way. Output: `timingNN.json` (used by the renderer) and
`timingNN.csv` (for people). **This is a first pass only.** Whisper cannot
transcribe Cherokee (it was tried: it hallucinates), so every page needs a
listen: play the page, note where the highlight runs ahead or behind, fix the
start/end seconds in the CSV, rebuild the JSON. Correct the cleaned MP3 or the
AIFF, it makes no difference, the timing is identical (see "Audio").

### 6. The story beat
In `animate.py`, `render_page(t)` holds the page 27 beats as code (flames,
sinking figure, song path, notes, leaning listeners, placement intro). For each
new page add one beat function keyed by page number (or a small vocabulary in
`pages/NN.json`: `flicker`, `slide`, `tilt`, `reveal`, `travel along path`,
`drop`, `grow`, with a start time taken from a phrase number). Keep it to one
or two motions per page; the narration carries the story.

A beat sheet from the English text (to confirm against each picture):

| Page | Text | Suggested beat |
|---|---|---|
| 1 | Cherokee lived in peace in the mountain forests | mother and daughter walk a step forward; corn leaves sway |
| 2 | ... one thing disturbed them: Spearfinger | Spearfinger's piece slides in from the edge on her name |
| 3 | magic, always hungry, liked children's livers | her finger extends; a slow menacing tilt |
| 4 | she roamed and could change shape | monster piece swaps to old-woman piece on "change" |
| 5 | spring, children picking strawberries, the grandmother appears | girl's hand reaches a berry; Spearfinger rises from behind the hill |
| 6 | "Come, little girl, let me comb your hair" | her hand beckons (small rotation) |
| 7 | child lays head down, old woman strokes hair with the spear finger | hand strokes; finger glints (a lighter copy flashed for 2 frames) |
| 8 | child asleep, she stabs and takes the liver | a sharp downward thrust, 3 frames, then a hold |
| 9 | "Liver, I eat" song | sung words appear one by one; 8 s page, keep it still otherwise |
| 10 | hunter sees her walking, singing | she walks across (stepped slide); notes rise |
| 11 | autumn, smoke above the trees, burning leaves | smoke pieces drift up; a leaf or two falls |
| 12 | she loved fog and smoke, easier to hide | a fog layer drifts over her and she fades behind it |
| 13 | never safe, stayed in groups of two or more | the group pieces draw together |
| 14 | she sneaks up on someone alone, cuts the liver, vanishes into fog | slow creep from behind, then she slides off into fog |
| 15 | the great council decides to stop her | people pieces turn toward the centre, one by one |
| 16 | trap her in a pit, all warriors shoot at once | arrows slide in a short distance toward her |
| 17 | dig the pit, cover it, build the fire, hide in the laurels | branches placed over the pit; smoke rises |
| 18 | an old woman comes hobbling along the trail | hobble: two-frame rocking slide along the path |
| 19 | she falls through and turns back into Spearfinger | drop into the pit; swap to the monster piece at the bottom |
| 20 | screams and claws at the pit with her finger | jabbing finger, stepped, in several directions |
| 21 | hunters shoot, arrows break on her stony skin | arrows fly in, snap into two pieces, fall |
| 22 | a titmouse perches and sings "un, un, un" | bird lands (slide down a branch), beak opens on each "un" |
| 23 | hunters aim at her heart, arrows break | arrows to the chest, break, fall |
| 24 | they cut the titmouse's tongue; it is a liar to this day | bird's tongue piece removed; bird flutters off |
| 25 | a chickadee lands on her right hand | chickadee flies down (travel along a curve) to the hand |
| 26 | her heart is in her palm; an arrow strikes it; she dies | one arrow travels to the palm; she slumps (tilt and sink) |
| 27 | thrown on the fire; songs of healing come from the flames | DONE: flames, song path, notes, listeners lean |

### 7. Render and encode
```
python animate.py test 0.6 1.5 9 28.5 44       # a few frames to check, in prev/
python animate.py render work/pageNN/frames    # all frames, 8 processes
ffmpeg -framerate 24 -i work/pageNN/frames/f%05d.jpg -i audio/Spearfinger_NN.mp3 \
  -filter_complex "[1:a]adelay=1800|1800,apad[a]" -map 0:v -map "[a]" \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k \
  -shortest -movflags +faststart pageNN.mp4
```
Page 27 took about 4 minutes to render on an 8-core Mac. Look at the test
frames before the full render; the things that go wrong are a piece in the
wrong z-order (a halo of colour where it overlaps), a hole where a moved piece
used to be (extend the underfill or inpaint, as was done for the song path),
and text spilling out of its column (long phrases: split them).

### 8. Assemble the book
* Title card from `SpearfingerWCU0009.tif` with the syllabary title
  ᎪᏍᏓᏱ ᏗᎦᎵᏘᏍᏙᏗ ᎦᏰᏌᏛᎢ and the credits as they stand on the gloss cover
  page (the ᎤᏃᎮᏢᎢ ᏃᎴ ᏧᏥᎶᏍᏓᏅᎢ and ᎤᎾᏥᏔᏅᎯ lines). Sara confirms the names
  and their English forms before anything is rendered.
* Join the 27 page movies with a 0.8 s cross-dissolve or a page-turn between
  them (`ffmpeg xfade` / `acrossfade`, or render a single timeline).
* End with the English text of each page as a scrolling afterword, or skip it.
* Deliverables: a 1080p MP4 for showing, and a smaller 720p for the web.

## Audio

`audio/Spearfinger_NN.mp3` are the narration tracks, processed on 19 Oct 2026:

* The AIFFs were stereo with identical channels, so the MP3s are **mono**.
* High-pass at 75 Hz (rumble), light spectral noise reduction (8 dB, the
  recordings have room hiss), gentle compression (2:1 above -20 dB, soft knee,
  12 ms attack, 180 ms release), then loudness normalisation to **-19 LUFS
  integrated, -1.5 dBTP true peak** (the spoken-word standard for mono; the
  equivalent of -16 LUFS stereo). The source tracks ranged from -14.6 to
  -21.8 LUFS, with peaks up to -0.4 dB.
* MP3 at VBR quality 3 (about 90 kb/s mono), 44.1 kHz.
* **No trimming or padding**, so every MP3 starts at the same instant as its
  AIFF and the phrase timings apply to both.
* `audio/loudness_report.csv` lists the before and after figures per track.

If a track needs a different treatment (a louder breath, a click), redo just
that one with the same chain; it is one ffmpeg command, recorded in the
session notes and easy to repeat from the parameters above.

## Interactive version (later)

The same layers and timing files can drive a web page: each piece an absolutely
positioned `<img>` moved with CSS keyframes, the audio in an `<audio>` element,
and the text column highlighting from `timingNN.json` with a click on any word
seeking to its start. That gives a tap-to-hear study page for the site with no
re-rendering.

The page carries three toggles, Syllabary, Phonetics and English, each on or
off on its own, remembered between visits. Any combination is allowed,
including all off (picture and voice only). The current-word highlight follows
whichever of the syllabary and phonetic lines are visible; the English is
highlighted by phrase. Default on first visit: all three on.

## Open questions for Sara

1. Page 27 timings: does the highlight stay with the narrator? Do the last three
   phrases match what is read?
2. Which text combinations should the movie be exported in (the interactive
   page has toggles; a movie file does not)?
3. Title and credit spellings in syllabary (taken from the gloss cover page,
   unverified).
4. Which pages, if any, should stay completely still (pages 8 and 9 are the
   darkest moments; stillness may be stronger than motion).
