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

Live at https://wespeakcherokee.org/books/ (shelf), with each book at its folder name, e.g.
https://wespeakcherokee.org/books/danny/ (Sara, 2026-11-01: resources live under paths of the hub, not subdomains).
A static site with no build step, in the Vercel project `wespeakcherokee-books` (team `sara-snyder-hopkins`,
Deployment Protection "Only Preview Deployments"). The hub's `vercel.json` passes `/books/…` through to
`wespeakcherokee-books.vercel.app`, and adds the trailing slash itself (`/books/danny` → `/books/danny/`) so the
book's relative images and audio load. The old address books.wespeakcherokee.org stays attached to this project only to
redirect (307) to the same page under `/books/`; that redirect is in `vercel.json` here. Keep every link in a book
relative, never starting with `/`. Pushes to `main` don't deploy (`git.deploymentEnabled: false`); deploy from the
Vercel connector or dashboard.
The books are public pages: no hub sign-in.
