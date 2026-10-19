# Cherokee-Books

The shelf of Cherokee read-along picture books for wespeakcherokee.org. Each book is a static folder built with the
read-along skill: one page (`index.html`) with the pictures, one narration recording, and live syllabary / phonetics /
English captions that follow the voice.

| Folder | Book |
|---|---|
| `danny/` | Didalonvhesgi nole Didane, Denili! (Trick or Treat, Danny!) — translated and read by Wiggins “Inoli” Blackfox |
| `halloween/` | Danaligvdulvsgv Ditsilosdanv (Halloween pictures) — spoken by Tom Belt |

`index.html` at the root is the shelf; `python3 make_shelf.py` rewrites it from whatever book folders exist.

## Adding or fixing a book

The skill lives in `.claude/skills/read-along-book-skill/` and Claude Code loads it automatically when working in this
repository (on a Mac or in the cloud). In short: pictures into `images/page-NN.jpg`, narration into `audio/narration.mp3`,
sentences into a spreadsheet, `python3 build_book.py`, then she taps along in the page's Time it mode to fix the timing.
Read the skill's `SKILL.md` and `references/` for the details; `scripts/new_book.py` starts a book folder.

Each book folder keeps everything needed to rebuild it: the spreadsheet (the source of all text and times),
`template.html`, `build_book.py`, `build_standalone.py`, `images/`, `audio/`, `fonts/` and, when there was one, a
`build/` folder with the source dumps. The single-file offline versions (`<Title>.html`, 10–20 MB) are not committed;
`python3 build_standalone.py` inside a book folder makes one in a few seconds.

## Hosting

Live at https://books.wespeakcherokee.org/ (shelf), with each book at its folder name, e.g.
https://books.wespeakcherokee.org/danny/. A static site with no build step: the Vercel project `wespeakcherokee-books`
(team `sara-snyder-hopkins`) is linked to this repository, so every push to `main` redeploys within a minute.
`vercel.json` adds the trailing slash so `…/danny` becomes `…/danny/` and the book's relative images and audio load.
The books are public pages: no hub sign-in.
