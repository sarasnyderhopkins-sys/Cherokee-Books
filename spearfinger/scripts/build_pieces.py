"""Step 3 for one page: cut the named pieces out of the scan.

   python3 scripts/build_pieces.py NN        (from the spearfinger folder)

Reads pages/NN.json "pieces": {name: selector}. A selector is a list of component ids from
work/pageNN/compsNN.json, or a dict:
   {"box": [x0,y0,x1,y1]}           every component whose centre lies in the box
   {"ids": [...], "box": [...], "add": [...], "drop": [...], "min_area": 0, "cut": [x0,y0,x1,y1]}
"cut" keeps only the pixels inside that box (splits a component that joins two shapes).
A component goes to the first piece that claims it. Components no piece claims stay painted on the
paper layer and never move; the pieces are inpainted out of the paper.

Writes work/pageNN/pieces/<name>.png (RGBA, with a 12 px underfill of its own colour wherever another piece
covers it), paper.png, manifest.json (position, z-order, pivot) and prev/rest_composite.png.
Z-order: pieces whose cut edges touch are ordered by the cut-edge shadows (the darker edge is underneath);
"back" and "front" lists in the page file override that.
"fill": "nearest" fills the holes with the nearest outside colour instead of a blur (flat colours, no smudge).
"""
import sys, json, os, itertools
from PIL import Image
import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
n = int(sys.argv[1]); S = f'{HERE}/work/page{n:02d}'
cfg = json.load(open(f'{HERE}/pages/{n:02d}.json'))
im = np.asarray(Image.open(f'{S}/p{n:02d}.png').convert('RGB')).astype(np.float32)
H, W, _ = im.shape
comp = np.load(f'{S}/comps{n:02d}.npy')
info = {d['id']: d for d in json.load(open(f'{S}/comps{n:02d}.json'))['comps']}
lum = im.mean(2)
mn, mx = im.min(2), im.max(2)
clean_paper = (mn > 215) & ((mx - mn) < 22)
os.makedirs(f'{S}/pieces', exist_ok=True); os.makedirs(f'{S}/prev', exist_ok=True)
for f in os.listdir(f'{S}/pieces'): os.remove(f'{S}/pieces/{f}')

# ---- resolve selectors ----
claimed = set(); masks = {}; names = []
for name, sel in cfg['pieces'].items():
    if isinstance(sel, list): sel = {'ids': sel}
    ids = list(sel.get('ids', []))
    if 'box' in sel:
        x0, y0, x1, y1 = sel['box']
        ids += [i for i, d in info.items() if x0 <= d['cx'] <= x1 and y0 <= d['cy'] <= y1 and d['area'] >= sel.get('min_area', 0)]
    ids += sel.get('add', [])
    ids = [i for i in dict.fromkeys(ids) if i not in claimed and i not in sel.get('drop', []) and i in info]
    m = np.isin(comp, ids)
    if 'cut' in sel:
        x0, y0, x1, y1 = sel['cut']; keep = np.zeros_like(m); keep[y0:y1, x0:x1] = True; m &= keep
    if not m.any(): print('EMPTY piece', name); continue
    if 'cut' not in sel: claimed.update(ids)
    masks[name] = m; names.append(name)
    print(f'{name:16s} ids {ids}')

# ---- z-order from cut-edge shadows ----
def interior_lum(m):
    e = ndi.binary_erosion(m, iterations=4)
    return np.median(lum[e]) if e.any() else np.median(lum[m])
med = {g: interior_lum(masks[g]) for g in names}
dil = {g: ndi.binary_dilation(masks[g], iterations=3) for g in names}
score = {g: 0.0 for g in names}
for a, b in itertools.combinations(names, 2):
    band_a = masks[a] & dil[b]; band_b = masks[b] & dil[a]
    if band_a.sum() < 30 or band_b.sum() < 30: continue
    da = lum[band_a].mean() - med[a]; db = lum[band_b].mean() - med[b]
    score[a] += db - da; score[b] -= db - da          # >0: a is darker at the shared edge, so a is behind b
order = sorted(names, key=lambda g: -score[g])
back = [g for g in cfg.get('back', []) if g in order]; front = [g for g in cfg.get('front', []) if g in order]
order = back + [g for g in order if g not in back and g not in front] + front
print('z-order (back->front):', order)

# ---- paper: inpaint where the pieces were (multi-scale normalised convolution + grain) ----
union = np.zeros((H, W), bool)
for g in names: union |= masks[g]
hole = ndi.binary_dilation(union, iterations=3)
pm = (~hole).astype(np.float32)
fill = np.zeros_like(im); conf = np.zeros((H, W), np.float32)
for sig in (12, 30, 70, 160):
    den = ndi.gaussian_filter(pm, sig)
    for c in range(3):
        num = ndi.gaussian_filter(im[:, :, c] * pm, sig)
        est = num / np.maximum(den, 1e-4)
        take = (conf < 0.2) & (den > 0.2)
        fill[:, :, c] = np.where(take, est, fill[:, :, c])
    conf = np.where((conf < 0.2) & (den > 0.2), den, conf)
mean_paper = im[clean_paper].mean(0) if clean_paper.any() else im.mean((0, 1))
for c in range(3): fill[:, :, c] = np.where(conf < 0.2, mean_paper[c], fill[:, :, c])
# where the hole sat on white paper, use plain paper colour rather than a blur of the piece's neighbours
near_paper = ndi.gaussian_filter(clean_paper.astype(np.float32), 20) > 0.55
fill = np.where((hole & near_paper)[..., None], mean_paper[None, None, :] * 0.6 + fill * 0.4, fill)
if cfg.get('fill') == 'nearest':
    # flat cut-paper colours: each hole pixel takes the colour of the nearest pixel outside the hole, so a
    # hole that straddles skin and paper splits cleanly instead of blurring into a smudge
    idx = ndi.distance_transform_edt(hole, return_distances=False, return_indices=True)
    near = ndi.median_filter(im, size=(5, 5, 1))[idx[0], idx[1]]
    fill = ndi.gaussian_filter(near, (1.2, 1.2, 0))
rng = np.random.default_rng(3)
noise = ndi.gaussian_filter(rng.normal(0, 3.2, (H, W)), 0.8)
grain = np.stack([noise * 1.0, noise * 0.95, noise * 0.9], -1)
paper = np.where(hole[..., None], np.clip(fill + grain, 0, 255), im)
Image.fromarray(paper.astype(np.uint8)).save(f'{S}/pieces/paper.png')

# ---- pieces with underfill ----
infront = {}; acc = np.zeros((H, W), bool)
for g in reversed(order):
    infront[g] = acc.copy(); acc |= masks[g]
manifest = []
for z, g in enumerate(order):
    m = masks[g]
    under = ndi.binary_dilation(m, iterations=12) & ~clean_paper & infront[g] & ~m
    ys, xs = np.nonzero(m | under)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    rgba = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
    sub = im[y0:y1, x0:x1]; ms = m[y0:y1, x0:x1]; us = under[y0:y1, x0:x1]
    er = ndi.binary_erosion(m, iterations=2)
    medc = np.median(im[er if er.any() else m], axis=0)
    rgba[..., :3] = np.where(ms[..., None], sub, medc).astype(np.uint8)
    rgba[..., 3] = np.where(ms | us, 255, 0)
    Image.fromarray(rgba).save(f'{S}/pieces/{g}.png')
    mys, mxs = np.nonzero(m)
    manifest.append(dict(name=g, z=z, x=int(x0), y=int(y0), w=int(x1 - x0), h=int(y1 - y0),
                         pivot=[int(mxs.mean()), int(mys.max())], center=[int(mxs.mean()), int(mys.mean())],
                         top=[int(mxs.mean()), int(mys.min())], area=int(m.sum()), under=int(under.sum())))
json.dump(manifest, open(f'{S}/pieces/manifest.json', 'w'), indent=1)
canvas = paper.copy()
for d in manifest:
    p = np.asarray(Image.open(f"{S}/pieces/{d['name']}.png")).astype(np.float32)
    a = p[..., 3:4] / 255
    reg = canvas[d['y']:d['y'] + d['h'], d['x']:d['x'] + d['w']]
    canvas[d['y']:d['y'] + d['h'], d['x']:d['x'] + d['w']] = reg * (1 - a) + p[..., :3] * a
Image.fromarray(canvas.astype(np.uint8)).save(f'{S}/prev/rest_composite.png')
Image.fromarray(paper.astype(np.uint8)).resize((600, 470)).save(f'{S}/prev/paper_small.png')
print('pieces', len(manifest), ' mean abs diff vs scan %.2f' % np.abs(canvas - im).mean())
