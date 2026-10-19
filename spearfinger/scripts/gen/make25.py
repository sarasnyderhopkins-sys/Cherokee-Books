import json, numpy as np
S='/home/claude/Cherokee-Books/spearfinger'
c=np.load(f'{S}/work/page25/comps25.npy')
arrows=[([4647,5563],(285,60,411,300)),([4661,5577],(1020,88,1126,300)),([4664,5582],(805,94,848,295)),
 ([4671,14924],(485,102,574,307)),([4725,5592],(96,177,246,358)),([4736,15400],(660,21,700,241)),
 ([4736,4828],(718,191,763,405)),([5607,15562],(1021,243,1188,405)),([4741,4959],(855,308,929,491)),
 ([5630,15690],(109,415,300,562)),([5634,15694],(970,420,1128,594)),([4749,5671],(337,466,488,649)),
 ([5080,5737],(389,698,525,846))]
pieces={}; motions={}; depth={}
# release order: staggered between p4w3 and p4w8
starts=["p4w3","p4w3+0.35","p4w4","p4w4+0.3","p4w5","p4w5+0.3","p4w6","p4w6+0.3","p4w7","p4w7+0.25","p4w8","p4w8+0.3","p4w8+0.6"]
order=[5,3,0,7,2,9,4,11,1,6,8,10,12]
D=260
for k,(ids,(x0,y0,x1,y1)) in enumerate(arrows):
    box=[x0-2,y0-2,x1+3,y1+3]
    sub=c[box[1]:box[3],box[0]:box[2]]
    m=np.isin(sub,ids); ys,xs=np.nonzero(m); xs=xs+box[0]; ys=ys+box[1]
    fm=sub==ids[0]; fy,fx=np.nonzero(fm); fcx=fx.mean()+box[0]; fcy=fy.mean()+box[1]
    pts=np.c_[xs,ys].astype(float); cen=pts.mean(0)
    u,s,vt=np.linalg.svd(pts-cen,full_matrices=False); d=vt[0]
    if d[1]<0: d=-d   # every arrow in this picture points downward
    name=f'arrow{k+1:02d}'
    pieces[name]={"ids":ids,"cut":box}
    depth[name]=1.0
    t=starts[order.index(k)]
    dx,dy=round(-d[0]*D),round(-d[1]*D)
    motions[name]=[{"type":"move","at":0,"dur":0,"dx":dx,"dy":dy},
                   {"type":"hide","at":t},
                   {"type":"move","at":t,"dur":0.45,"dx":-dx,"dy":-dy,"ease":"linear"}]
cfg=json.load(open(f'{S}/pages/25.json'))
cfg['pieces'].update(pieces); cfg['depth'].update(depth); cfg['motions'].update(motions)
json.dump(cfg,open(f'{S}/pages/25.json','w'),indent=1)
