#!/bin/sh
# Rebuild and render the whole book from the page files. Run from the spearfinger folder.
#   sh scripts/render_all.sh            all pages      sh scripts/render_all.sh 3 7 12     just those pages
# Then: python3 scripts/assemble.py
set -e
PAGES=${*:-$(seq 1 27)}
for n in $PAGES; do
  nn=$(printf %02d $n)
  if [ "$n" != 27 ]; then
    [ -f work/page$nn/comps$nn.npy ] || python3 scripts/prep_page.py $n
    python3 scripts/build_pieces.py $n > work/page$nn/build_log.txt
  fi
  [ -f work/page$nn/timing$nn.json ] || python3 scripts/timing.py $n
  python3 scripts/animate.py $n render | tail -1
done
[ -f out/title.mp4 ] || python3 scripts/cards.py
