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
# connected components per class
comp = np.zeros((H,W), np.int32); n=0; info=[]
for c in range(len(cent)):
    m = cls==c
    if not m.any(): continue
    l, k = ndi.label(m)
    for i in range(1,k+1):
        mm = l==i
        a = int(mm.sum())
        n+=1; comp[mm]=n
        ys,xs = np.nonzero(mm)
        info.append(dict(id=n, cls=c, color=[int(v) for v in cent[c]], area=a, bbox=[int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())], cx=int(xs.mean()), cy=int(ys.mean())))
# absorb small comps into the neighbouring large comp
MIN=400
small = np.zeros(n+1,bool)
for d in info:
    if d['area']<MIN: small[d['id']]=True
big = comp.copy(); big[small[comp]] = 0
# grow big labels into small/edge pixels via nearest big pixel
dist, (iy,ix) = ndi.distance_transform_edt(big==0, return_indices=True)
filled = big[iy,ix]
comp2 = np.where(nonp, filled, 0)
keep = [d for d in info if d['area']>=MIN]
# recompute stats
for d in keep:
    mm = comp2==d['id']; ys,xs=np.nonzero(mm)
    d['area']=int(mm.sum()); d['bbox']=[int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())]; d['cx']=int(xs.mean()); d['cy']=int(ys.mean())
keep.sort(key=lambda d:-d['area'])
json.dump(dict(W=W,H=H,comps=keep), open(sys.argv[2],'w'))
np.save(sys.argv[3], comp2)
# preview
rng = np.random.default_rng(1)
cols = rng.integers(40,230,(n+1,3)); cols[0]=[250,250,250]
pv = Image.fromarray(cols[comp2].astype(np.uint8))
dr = ImageDraw.Draw(pv)
try: f = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 18)
except: f = ImageFont.load_default()
for d in keep:
    dr.text((d['cx']-8,d['cy']-9), str(d['id']), fill=(0,0,0), font=f)
    dr.text((d['cx']-9,d['cy']-10), str(d['id']), fill=(255,255,255), font=f)
pv.save(sys.argv[4])
for d in keep: print(d['id'], d['color'], 'area',d['area'],'bbox',d['bbox'],'c',d['cx'],d['cy'])
print('paper px', int(paper.sum()), 'nonpaper', int(nonp.sum()), 'comps', len(keep))
