import sys, json, itertools
from PIL import Image
import numpy as np
from scipy import ndimage as ndi
S = sys.argv[1]
im = np.asarray(Image.open(f'{S}/p27.png').convert('RGB')).astype(np.float32)
H,W,_ = im.shape
comp = np.load(f'{S}/comps27.npy')
lum = im.mean(2)
mn, mx = im.min(2), im.max(2)
clean_paper = (mn > 215) & ((mx-mn) < 22)
groups = {
 'left_tree':[1,2441], 'right_group':[3,2520,8197,8883,5465],
 'left_person':[8352,911,988,5464,6065], 'left_bush':[5382,775],
 'fire_base':[885,11816,3192,3193,11312,11513],
 'spearfinger':[2994,6653,6794,6911,6605,3050],
 'path':[5782,5564,5467,5998,5990], 'note1':[2373],'note2':[2670],'note3':[2873],
}
flames = [1236,1221,3298,3244,880,884,879,881,983,7419,7450,7502,7498,7439,7562,7547,7552,11974,11975,11976,11977,11973,12039,1322,1418]
for f in flames: groups[f'flame_{f}'] = [f]
masks = {g: np.isin(comp, ids) for g,ids in groups.items()}
# --- z-order among fire pieces via cut-edge shadow heuristic ---
fire = ['fire_base','spearfinger'] + [f'flame_{f}' for f in flames]
def interior_lum(m):
    e = ndi.binary_erosion(m, iterations=4)
    return np.median(lum[e]) if e.any() else np.median(lum[m])
med = {g: interior_lum(masks[g]) for g in fire}
dil = {g: ndi.binary_dilation(masks[g], iterations=3) for g in fire}
behind = {}  # (a,b) -> score>0 means a is behind b
for a,b in itertools.combinations(fire,2):
    ma, mb = masks[a], masks[b]
    band_a = ma & dil[b]; band_b = mb & dil[a]      # a's pixels near b, b's pixels near a
    if band_a.sum() < 30 or band_b.sum() < 30: continue
    da = lum[band_a].mean() - med[a]; db = lum[band_b].mean() - med[b]
    behind[(a,b)] = db - da   # >0 : a darker near edge -> a behind b
# order by net "behindness"
score = {g:0.0 for g in fire}
for (a,b),s in behind.items():
    score[a] += s; score[b] -= s
fire_order = sorted(fire, key=lambda g: -score[g])   # most-behind first
fire_order.remove('fire_base'); fire_order.insert(0,'fire_base')
order = ['left_tree','right_group','left_person','left_bush'] + fire_order + ['path','note1','note2','note3']
print('fire z-order (back->front):', fire_order)
# --- paper layer: multi-scale normalized-convolution fill + synthetic grain ---
hole = ndi.binary_dilation(~clean_paper, iterations=3)
pm = (~hole).astype(np.float32)
fill = np.zeros_like(im); conf = np.zeros((H,W),np.float32)
for sig in (25, 60, 150):
    den = ndi.gaussian_filter(pm, sig)
    for c in range(3):
        num = ndi.gaussian_filter(im[:,:,c]*pm, sig)
        est = num/np.maximum(den,1e-4)
        take = (conf < 0.2) & (den > 0.2)
        fill[:,:,c] = np.where(take, est, fill[:,:,c])
    conf = np.where((conf<0.2)&(den>0.2), den, conf)
mean_paper = im[~hole].mean(0)
for c in range(3): fill[:,:,c] = np.where(conf<0.2, mean_paper[c], fill[:,:,c])
rng = np.random.default_rng(3)
noise = ndi.gaussian_filter(rng.normal(0, 3.2, (H,W)), 0.8)
grain = np.stack([noise*1.0, noise*0.95, noise*0.9], -1)
paper = np.where(hole[...,None], np.clip(fill+grain,0,255), im)
Image.fromarray(paper.astype(np.uint8)).save(f'{S}/pieces/paper.png')
# --- pieces with underfill ---
manifest = []
front_union = np.zeros((H,W),bool)
for g in reversed(order):      # walk front->back accumulating "in front" masks
    pass
infront = {}
acc = np.zeros((H,W),bool)
for g in reversed(order):
    infront[g] = acc.copy(); acc |= masks[g]
for z,g in enumerate(order):
    m = masks[g]
    if not m.any(): print('EMPTY', g); continue
    under = ndi.binary_dilation(m, iterations=12) & ~clean_paper & infront[g] & ~m
    ys,xs = np.nonzero(m|under)
    x0,y0,x1,y1 = xs.min(), ys.min(), xs.max()+1, ys.max()+1
    rgba = np.zeros((y1-y0, x1-x0, 4), np.uint8)
    sub = im[y0:y1, x0:x1]; ms = m[y0:y1,x0:x1]; us = under[y0:y1,x0:x1]
    medc = np.median(im[ndi.binary_erosion(m,iterations=2) if ndi.binary_erosion(m,iterations=2).any() else m], axis=0)
    rgba[...,:3] = np.where(ms[...,None], sub, medc).astype(np.uint8)
    rgba[...,3] = np.where(ms|us, 255, 0)
    Image.fromarray(rgba).save(f'{S}/pieces/{g}.png')
    mys, mxs = np.nonzero(m)
    manifest.append(dict(name=g, z=z, x=int(x0), y=int(y0), w=int(x1-x0), h=int(y1-y0),
        pivot=[int(mxs.mean()), int(mys.max())], area=int(m.sum()), under=int(under.sum())))
json.dump(manifest, open(f'{S}/pieces/manifest.json','w'), indent=1)
print('pieces', len(manifest))
# sanity composite at rest
canvas = paper.copy()
for d in manifest:
    p = np.asarray(Image.open(f"{S}/pieces/{d['name']}.png")).astype(np.float32)
    a = p[...,3:4]/255
    reg = canvas[d['y']:d['y']+d['h'], d['x']:d['x']+d['w']]
    canvas[d['y']:d['y']+d['h'], d['x']:d['x']+d['w']] = reg*(1-a)+p[...,:3]*a
Image.fromarray(canvas.astype(np.uint8)).save(f'{S}/prev/rest_composite.png')
diff = np.abs(canvas-im).mean()
print('mean abs diff vs original', diff)
