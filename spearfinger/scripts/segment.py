import sys, json
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from scipy import ndimage as ndi
from scipy.cluster.vq import kmeans2
im = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(np.float32)
H,W,_ = im.shape
mn = im.min(2); mx = im.max(2)
paper = (mn > 185) & ((mx-mn) < 30)           # white paper incl. light cut shadows
paper = ndi.binary_opening(paper, iterations=1)
nonp = ~paper
# color classes (seeded from palette)
seeds = np.array([[67,85,80],[124,38,45],[199,110,36],[40,39,40],[168,56,69],[139,149,92],[52,78,136],[160,154,146],[234,203,97],[206,190,169],[90,110,70],[245,170,60]],np.float32)
pix = im[nonp]
cent, lab = kmeans2(pix, seeds, minit='matrix', iter=20)
cls = np.full((H,W), -1, np.int32); cls[nonp] = lab
# connected components per class (vectorised: bincount + find_objects, not one mask per component)
comp = np.zeros((H,W), np.int32); n=0
for c in range(len(cent)):
    m = cls==c
    if not m.any(): continue
    l, k = ndi.label(m)
    comp[m] = l[m] + n
    n += k
cnt = np.bincount(comp.ravel(), minlength=n+1)
# absorb small comps into the neighbouring large comp
MIN=400
small = cnt < MIN; small[0] = False
big = comp.copy(); big[small[comp]] = 0
# grow big labels into small/edge pixels via nearest big pixel
dist, (iy,ix) = ndi.distance_transform_edt(big==0, return_indices=True)
filled = big[iy,ix]
comp2 = np.where(nonp, filled, 0)
cls_of = np.zeros(n+1, np.int32); cls_of[comp[nonp]] = cls[nonp]
area = np.bincount(comp2.ravel(), minlength=n+1)
ys_, xs_ = np.mgrid[0:H,0:W]
sx = np.bincount(comp2.ravel(), weights=xs_.ravel(), minlength=n+1)
sy = np.bincount(comp2.ravel(), weights=ys_.ravel(), minlength=n+1)
keep = []
for i, sl in enumerate(ndi.find_objects(comp2), start=1):
    if sl is None or area[i] == 0: continue
    c = cls_of[i]
    keep.append(dict(id=i, cls=int(c), color=[int(v) for v in cent[c]], area=int(area[i]),
                     bbox=[int(sl[1].start), int(sl[0].start), int(sl[1].stop-1), int(sl[0].stop-1)],
                     cx=int(sx[i]/area[i]), cy=int(sy[i]/area[i])))
keep.sort(key=lambda d:-d['area'])
json.dump(dict(W=W,H=H,comps=keep), open(sys.argv[2],'w'))
np.save(sys.argv[3], comp2)
# preview
rng = np.random.default_rng(1)
cols = rng.integers(40,230,(n+1,3)); cols[0]=[250,250,250]
pv = Image.fromarray(cols[comp2].astype(np.uint8))
dr = ImageDraw.Draw(pv)
f = None
for fp in ('/System/Library/Fonts/Helvetica.ttc', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
    try: f = ImageFont.truetype(fp, 18); break
    except OSError: pass
if f is None: f = ImageFont.load_default()
for d in keep:
    dr.text((d['cx']-8,d['cy']-9), str(d['id']), fill=(0,0,0), font=f)
    dr.text((d['cx']-9,d['cy']-10), str(d['id']), fill=(255,255,255), font=f)
pv.save(sys.argv[4])
for d in keep: print(d['id'], d['color'], 'area',d['area'],'bbox',d['bbox'],'c',d['cx'],d['cy'])
print('paper px', int(paper.sum()), 'nonpaper', int(nonp.sum()), 'comps', len(keep))
