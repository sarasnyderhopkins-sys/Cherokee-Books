"""Step 1-2 for one page: export the scan and segment it into numbered pieces.
   python3 scripts/prep_page.py NN      (from the spearfinger folder)"""
import sys, os, subprocess
from PIL import Image
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
n = int(sys.argv[1]); W = f'{HERE}/work/page{n:02d}'
os.makedirs(f'{W}/pieces', exist_ok=True); os.makedirs(f'{W}/prev', exist_ok=True)
im = Image.open(f'{HERE}/assets-src/Spearfinger042109_{n:03d}.tif').convert('RGB')
im.save(f'{W}/p{n:02d}.png')
print(n, im.size)
subprocess.run([sys.executable, f'{HERE}/scripts/segment.py', f'{W}/p{n:02d}.png', f'{W}/comps{n:02d}.json',
                f'{W}/comps{n:02d}.npy', f'{W}/components_preview.png'], check=True, stdout=open(f'{W}/segment_log.txt', 'w'))
