import sys, json
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
S=sys.argv[1]
comp=np.load(f'{S}/comps27.npy'); H,W=comp.shape
path=np.isin(comp,[5782,5564,5467,5998,5990])
ctrl=[(752,432),(700,420),(640,408),(575,418),(520,434),(486,440),(440,433),(395,412),(355,378),(332,338),(319,302),(325,268),(352,246),(392,232),(460,225),(560,228),(650,232),(720,238),(790,236),(850,226),(880,196),(886,152),(866,116),(825,99),(788,100),(752,86),(716,56),(702,26),(696,2)]
# snap control points to the ridge of the path (max distance-transform within 25px)
dt=ndi.distance_transform_edt(path)
snapped=[]
for x,y in ctrl:
    x0,x1=max(0,x-25),min(W,x+26); y0,y1=max(0,y-25),min(H,y+26)
    win=dt[y0:y1,x0:x1]
    if win.max()<=0: snapped.append((x,y)); continue
    iy,ix=np.unravel_index(np.argmax(win),win.shape); snapped.append((x0+ix,y0+iy))
pts=np.array(snapped,float)
# Catmull-Rom resample to ~2px spacing
def cr(p0,p1,p2,p3,t):
    t2=t*t;t3=t2*t
    return 0.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t2+(-p0+3*p1-3*p2+p3)*t3)
dense=[]
P=np.vstack([pts[0],pts,pts[-1]])
for i in range(1,len(P)-2):
    seg=np.linalg.norm(P[i+1]-P[i]); n=max(2,int(seg/2))
    for k in range(n): dense.append(cr(P[i-1],P[i],P[i+1],P[i+2],k/n))
dense.append(P[-2]); dense=np.array(dense)
# recentre each point on the centroid of nearby path pixels that are closest to it
pys,pxs=np.nonzero(path); pp=np.c_[pxs,pys].astype(float)
for it in range(4):
    tree=cKDTree(dense); dd,ii=tree.query(pp)
    ok=dd<22
    delta=np.zeros_like(dense); cnt=np.zeros(len(dense))
    np.add.at(delta,ii[ok],pp[ok]-dense[ii[ok]]); np.add.at(cnt,ii[ok],1)
    moved=cnt>3
    dense[moved]=dense[moved]+delta[moved]/cnt[moved,None]*0.8
    # smooth along the line
    sm=dense.copy(); sm[1:-1]=(dense[:-2]+2*dense[1:-1]+dense[2:])/4; dense=sm
# smooth along the line, then resample evenly
for c in range(2): dense[:,c]=ndi.gaussian_filter1d(dense[:,c], 6, mode='nearest')
seglen=np.linalg.norm(np.diff(dense,axis=0),axis=1); arc0=np.concatenate([[0],np.cumsum(seglen)])
samples=np.arange(0,arc0[-1],2.0)
dense=np.c_[np.interp(samples,arc0,dense[:,0]),np.interp(samples,arc0,dense[:,1])]
seglen=np.linalg.norm(np.diff(dense,axis=0),axis=1); arc=np.concatenate([[0],np.cumsum(seglen)])
L=float(arc[-1])
# arc-length per path pixel
ys,xs=np.nonzero(path); tree=cKDTree(dense); d,idx=tree.query(np.c_[xs,ys])
arcmap=np.full((H,W),-1,np.float32); arcmap[ys,xs]=arc[idx]
np.save(f'{S}/path_arc.npy',arcmap)
json.dump(dict(pts=dense.round(2).tolist(),arc=arc.round(2).tolist(),L=L,ctrl=[[int(a),int(b)] for a,b in snapped]),open(f'{S}/path27.json','w'))
print('L',round(L,1),'points',len(dense),'max snap dist',float(d.max()))
# preview
pv=Image.open(f'{S}/p27.png').convert('RGB'); px=pv.load()
for x,y in dense.astype(int):
    for dx in (-1,0,1):
        for dy in (-1,0,1):
            if 0<=x+dx<W and 0<=y+dy<H: px[x+dx,y+dy]=(255,0,0)
pv.crop((280,0,960,480)).save(f'{S}/prev/path_check.png')
