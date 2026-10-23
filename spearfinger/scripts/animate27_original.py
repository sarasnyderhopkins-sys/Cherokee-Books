import json, math, sys, os, hashlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

S = os.path.dirname(os.path.abspath(__file__))
OUT_W, OUT_H = 1920, 1080
FPS = 24
PW, PH = 1200, 940
M = 80                      # working margin around the page
LEAD, NARR, TAIL = 1.8, 51.68, 2.6
TOTAL = LEAD + NARR + TAIL
CARD = (48, 48, 1256, 984)
COL_X, COL_W = 1352, 520
CREAM = (241, 235, 224)
INK = (40, 38, 39)
FADED = (168, 162, 154)
PILL = (246, 221, 140)
RULE = (205, 196, 182)

FONT_DIR = '/System/Library/Fonts/Supplemental/'
def font(name, size): return ImageFont.truetype(FONT_DIR + name, size)
F_SYL = font('PlantagenetCherokee.ttf', 40)
F_PHO = font('Charter.ttc', 25)
F_ENG = font('Georgia Italic.ttf', 24)
F_CAP = font('Georgia.ttf', 19)
F_CAPS = font('PlantagenetCherokee.ttf', 22)

# ---------- assets ----------
man = json.load(open(f'{S}/pieces/manifest.json'))
timing = json.load(open(f'{S}/timing27.json'))
pathj = json.load(open(f'{S}/path27.json'))
PATH_PTS = np.array(pathj['pts']); PATH_ARC = np.array(pathj['arc']); PATH_L = pathj['L']
arcmap = np.load(f'{S}/path_arc.npy')
paper = Image.open(f'{S}/pieces/paper.png').convert('RGBA')

PAD = 10
pieces = {}
for d in man:
    im = Image.open(f"{S}/pieces/{d['name']}.png").convert('RGBA')
    padded = Image.new('RGBA', (im.width+2*PAD, im.height+2*PAD), (0,0,0,0)); padded.paste(im, (PAD,PAD))
    a = padded.split()[3].filter(ImageFilter.GaussianBlur(2.2)).point(lambda v: int(v*0.32))
    sh = Image.new('RGBA', padded.size, (30,20,15,255)); sh.putalpha(a)
    pieces[d['name']] = dict(d, img=padded, shadow=sh, x=d['x']-PAD, y=d['y']-PAD)
ORDER = [d['name'] for d in sorted(man, key=lambda d: d['z'])]
N = len(ORDER)
path_piece = pieces['path']
path_arc_crop = arcmap[path_piece['y']+PAD:path_piece['y']+PAD+path_piece['img'].height-2*PAD,
                       path_piece['x']+PAD:path_piece['x']+PAD+path_piece['img'].width-2*PAD]
path_arc_pad = np.full((path_piece['img'].height, path_piece['img'].width), -1, np.float32)
path_arc_pad[PAD:-PAD, PAD:-PAD] = path_arc_crop

# rebuild the path's hidden parts: fill the centreline corridor (locally measured width) wherever the path is not visible
from scipy.spatial import cKDTree as _KD
_tree = _KD(PATH_PTS)
_pim = np.array(path_piece['img']); _H,_W = _pim.shape[:2]
_vis = path_arc_pad >= 0
_vy,_vx = np.nonzero(_vis)
_dv,_iv = _tree.query(np.c_[_vx+path_piece['x'], _vy+path_piece['y']])
_arcv = PATH_ARC[_iv]
BIN = 40.0
_nb = int(PATH_L//BIN)+1
_hw = np.full(_nb, np.nan)
for k in range(_nb):
    m = (_arcv >= k*BIN) & (_arcv < (k+1)*BIN)
    if m.sum() > 40: _hw[k] = np.percentile(_dv[m], 85)
_ok = ~np.isnan(_hw); _hw = np.interp(np.arange(_nb), np.nonzero(_ok)[0], _hw[_ok])
_yy,_xx = np.mgrid[0:_H,0:_W]
_comp = np.load(f'{S}/comps27.npy')
_cov = np.zeros((_H,_W),bool)
_cy0,_cx0 = path_piece['y'], path_piece['x']
_sy0,_sx0 = max(0,-_cy0), max(0,-_cx0)
_sub = _comp[max(0,_cy0):_cy0+_H, max(0,_cx0):_cx0+_W] > 0
_cov[_sy0:_sy0+_sub.shape[0], _sx0:_sx0+_sub.shape[1]] = _sub
_cand = ~_vis & _cov
_cy,_cx = np.nonzero(_cand)
_d,_idx = _tree.query(np.c_[_cx+path_piece['x'], _cy+path_piece['y']], distance_upper_bound=20)
_in = np.isfinite(_d)
_cy,_cx,_d,_idx = _cy[_in],_cx[_in],_d[_in],_idx[_in]
_hwl = _hw[np.minimum((PATH_ARC[_idx]//BIN).astype(int), _nb-1)]
_feather = np.clip((_hwl + 0.5 - _d)/1.2, 0, 1)
_keep = _feather > 0
_cy,_cx,_feather,_idx = _cy[_keep],_cx[_keep],_feather[_keep],_idx[_keep]
_med = np.median(_pim[...,:3][_vis], axis=0)
_rng = np.random.default_rng(5)
_tex = np.clip(_med[None,:] + _rng.normal(0,4.5,(len(_cy),1)), 0, 255)
# clear old underfill entirely, then write the corridor
_pim[...,3][~_vis] = 0
_pim[_cy,_cx,:3] = _tex.astype(np.uint8); _pim[_cy,_cx,3] = (255*_feather).astype(np.uint8)
path_arc_pad[~_vis] = -1
path_arc_pad[_cy,_cx] = PATH_ARC[_idx]
print('path half-width by bin: min %.1f median %.1f max %.1f ; corridor px %d' % (_hw.min(), np.median(_hw), _hw.max(), len(_cy)))
path_piece['img'] = Image.fromarray(_pim)
_a = path_piece['img'].split()[3].filter(ImageFilter.GaussianBlur(2.2)).point(lambda v: int(v*0.32))
path_piece['shadow'] = Image.new('RGBA', path_piece['img'].size, (30,20,15,255)); path_piece['shadow'].putalpha(_a)

def depth_of(name):
    if name in ('left_tree','right_group'): return 0.35
    if name in ('left_person','left_bush'): return 0.65
    if name in ('path','note1','note2','note3'): return 1.0
    return 0.85

def seed(name, k=0):
    h = hashlib.md5(f'{name}{k}'.encode()).digest()
    return int.from_bytes(h[:4],'little')/2**32

def smooth(u): u=min(max(u,0.0),1.0); return u*u*(3-2*u)
def quant(t, fps=12): return math.floor(t*fps)/fps
def stepped(u, steps=3): return math.floor(min(max(u,0),1)*steps)/steps

# ---------- transforms ----------
def xform(im, px, py, rot=0.0, sx=1.0, sy=1.0, dx=0.0, dy=0.0):
    """Scale about pivot (px,py), rotate about pivot, translate; returns (image, ox0, oy0) in piece-local coords."""
    w,h = im.size
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    def fwd(x,y):
        X=(x-px)*sx; Y=(y-py)*sy
        return (c*X - s*Y + px + dx, s*X + c*Y + py + dy)
    cs=[fwd(0,0),fwd(w,0),fwd(0,h),fwd(w,h)]
    ox0=math.floor(min(p[0] for p in cs)); oy0=math.floor(min(p[1] for p in cs))
    ox1=math.ceil(max(p[0] for p in cs)); oy1=math.ceil(max(p[1] for p in cs))
    W_,H_ = max(1,ox1-ox0), max(1,oy1-oy0)
    if rot==0 and sx==1 and sy==1:
        return im, ox0, oy0
    a = c/sx; b = s/sx; cc = (c/sx)*(ox0-px-dx) + (s/sx)*(oy0-py-dy) + px
    d = -s/sy; e = c/sy; f = (-s/sy)*(ox0-px-dx) + (c/sy)*(oy0-py-dy) + py
    out = im.transform((W_,H_), Image.AFFINE, (a,b,cc,d,e,f), resample=Image.BILINEAR)
    return out, ox0, oy0

def blit(canvas, im, x, y):
    cw,ch = canvas.size; w,h = im.size
    x0,y0 = max(x,0), max(y,0); x1,y1 = min(x+w,cw), min(y+h,ch)
    if x1<=x0 or y1<=y0: return
    src = im if (x0==x and y0==y and x1==x+w and y1==y+h) else im.crop((x0-x,y0-y,x1-x,y1-y))
    canvas.alpha_composite(src, (x0,y0))

def place(canvas, p, rot=0.0, sx=1.0, sy=1.0, dx=0.0, dy=0.0, shadow=(2,3), img=None, alpha=None):
    img = img if img is not None else p['img']
    px, py = p['pivot'][0]-p['x'], p['pivot'][1]-p['y']
    shadow_img = p['shadow']
    if img is not p['img']:
        a = img.split()[3].filter(ImageFilter.GaussianBlur(2.2)).point(lambda v: int(v*0.32))
        shadow_img = Image.new('RGBA', img.size, (30,20,15,255)); shadow_img.putalpha(a)
    sh, sx0, sy0 = xform(shadow_img, px, py, rot, sx, sy, dx, dy)
    blit(canvas, sh, int(p['x']+sx0+shadow[0]+M), int(p['y']+sy0+shadow[1]+M))
    im, ox0, oy0 = xform(img, px, py, rot, sx, sy, dx, dy)
    if alpha is not None and alpha < 1:
        im = im.copy(); im.putalpha(im.split()[3].point(lambda v: int(v*alpha)))
    blit(canvas, im, int(p['x']+ox0+M), int(p['y']+oy0+M))

def path_point(s):
    s = min(max(s,0), PATH_L)
    i = np.searchsorted(PATH_ARC, s); i = min(max(i,1), len(PATH_ARC)-1)
    u = (s-PATH_ARC[i-1])/max(PATH_ARC[i]-PATH_ARC[i-1],1e-6)
    return PATH_PTS[i-1]*(1-u)+PATH_PTS[i]*u

# ---------- story timing ----------
SONGS_T = LEAD + 25.0          # "...the people heard" -> songs rise
HEAL_T  = LEAD + 39.8          # "healing medicine songs came" -> more notes
NOTE_IMGS = ['note1','note2','note3']
def note_schedule():
    out=[]; t=SONGS_T+0.8; k=0
    while t < TOTAL:
        out.append((t, NOTE_IMGS[k%3])); k+=1
        t += 2.4 if t < HEAL_T else 1.3
    return out
NOTES = note_schedule()
NOTE_TRAVEL = 9.0

# ---------- page composite ----------
def render_page(t):
    canvas = Image.new('RGBA', (PW+2*M, PH+2*M), (0,0,0,0))
    canvas.alpha_composite(paper, (M,M))
    u = t/TOTAL
    camx = -12 + 24*smooth(u)
    tq = quant(t)
    for i,name in enumerate(ORDER):
        p = pieces[name]
        if name.startswith('note'): continue
        t_in = 0.12 + 1.25*i/N
        if t < t_in: continue
        e = stepped((t-t_in)/0.22, 3)
        dy_in = -14*(1-e); shadow = (2+5*(1-e), 3+7*(1-e))
        dx = camx*(depth_of(name)-0.65)
        rot=0.0; sx=sy=1.0; dy=dy_in
        if name.startswith('flame'):
            h = p['h']; r0,r1,r2 = seed(name,1), seed(name,2), seed(name,3)
            A = min(max(260.0/h, 0.8), 2.2)
            rot = A*math.sin(2*math.pi*(0.55+0.5*r0)*tq + r1*6.28) + 0.45*A*math.sin(2*math.pi*(2.1+0.8*r2)*tq + r0*6.28)
            As = 0.025 + 0.03*min(150.0/h,1)
            sy = 1 + As*math.sin(2*math.pi*(0.8+0.6*r1)*tq + r2*6.28)
        elif name == 'spearfinger':
            uu = smooth((t-LEAD-8)/40)
            rot = 2.5*math.sin(2*math.pi*0.9*tq + 1.0)
            sy = 1 - 0.18*uu; sx = 1 - 0.08*uu; dy += 14*uu
        elif name == 'left_person':
            rot = -1.6*smooth((t-SONGS_T)/2.5)
        elif name == 'right_group':
            rot = 0.6*smooth((t-SONGS_T)/2.5)
        elif name == 'path':
            if t < SONGS_T: continue
            L = PATH_L*smooth((t-SONGS_T)/3.5)
            im = p['img'].copy()
            a = np.asarray(im.split()[3]).astype(np.float32)
            a = np.where((path_arc_pad>=0)&(path_arc_pad<=L), a, np.where(path_arc_pad<0, a, 0))
            # pixels outside the arc map (underfill fringe) only show once their neighbours do
            im.putalpha(Image.fromarray(a.astype(np.uint8)))
            if L < PATH_L*0.999:
                # hide fringe beyond the drawn tip
                mask = (path_arc_pad<0)
                am = np.asarray(im.split()[3]).astype(np.float32)
                am[mask & (np.asarray(p['img'].split()[3])>0)] = 0
                im.putalpha(Image.fromarray(am.astype(np.uint8)))
            place(canvas, p, dx=dx, dy=dy, shadow=shadow, img=im)
            continue
        place(canvas, p, rot=rot, sx=sx, sy=sy, dx=dx, dy=dy, shadow=shadow)
    # travelling notes
    for (t0,name) in NOTES:
        if t < t0: continue
        s = (t-t0)/NOTE_TRAVEL*PATH_L
        if s >= PATH_L: continue
        p = pieces[name]
        x,y = path_point(s)
        cx, cy = p['x']+p['img'].width/2, p['y']+p['img'].height/2
        bob = 9*math.sin(2*math.pi*0.9*t + seed(name)*6.28)
        fade = min((t-t0)/0.4, 1.0)
        place(canvas, p, rot=bob, dx=x-cx + camx*0.35, dy=y-cy, shadow=(2,3), alpha=fade)
    return canvas, u

# ---------- text column ----------
def wrap_words(words, fnt, width):
    lines=[]; cur=[]; w=0
    for wd in words:
        ww = fnt.getlength(wd); sp = fnt.getlength(' ') if cur else 0
        if cur and w+sp+ww > width:
            lines.append(cur); cur=[wd]; w=ww
        else:
            cur.append(wd); w += sp+ww
    if cur: lines.append(cur)
    return lines

def layout_column():
    blocks=[]; y=0
    for ph in timing:
        syl=[w['syl'] for w in ph['words']]; pho=[w['pho'] for w in ph['words']]
        b=dict(ph=ph, y=y, items=[])
        yy=0
        for lines,fnt,lh,kind in ((wrap_words(syl,F_SYL,COL_W),F_SYL,54,'syl'),(wrap_words(pho,F_PHO,COL_W),F_PHO,34,'pho')):
            wi=0
            for ln in lines:
                x=0
                for wd in ln:
                    b['items'].append(dict(kind=kind, idx=wi, text=wd, x=x, y=yy, w=fnt.getlength(wd), fnt=fnt))
                    x += fnt.getlength(wd)+fnt.getlength(' '); wi+=1
                yy += lh
            yy += 4
        for ln in wrap_words(ph['eng'].split(),F_ENG,COL_W):
            b['items'].append(dict(kind='eng', idx=-1, text=' '.join(ln), x=0, y=yy, fnt=F_ENG)); yy += 32
        b['h']=yy; blocks.append(b); y += yy + 44
    return blocks
BLOCKS = layout_column()

def current_phrase(t):
    tn = t-LEAD; cur=None; last_change=None
    for i,ph in enumerate(timing):
        if tn >= ph['start']: cur=i; last_change=ph['start']+LEAD
    return cur, last_change

def draw_column(frame, t):
    dr = ImageDraw.Draw(frame)
    cx = COL_X; top=CARD[1]; H = CARD[3]
    # caption
    dr.text((cx, top+2), 'ᎪᏍᏓᏱ ᏗᎦᎵᏘᏍᏙᏗ ᎦᏰᏌᏛᎢ', font=F_CAPS, fill=FADED)
    dr.text((cx, top+30), 'Spearfinger  ·  page 27', font=F_CAP, fill=FADED)
    dr.line((cx, top+62, cx+COL_W, top+62), fill=RULE, width=1)
    cur, tc = current_phrase(t)
    # scroll target: centre current block in the column window
    win_top, win_h = top+90, H-110
    def centre(i): b=BLOCKS[i]; return b['y']+b['h']/2
    if cur is None: scroll = centre(0)
    else:
        target = centre(cur)
        prev = centre(cur-1) if cur>0 else centre(0)
        scroll = prev + (target-prev)*smooth((t-tc)/0.55)
    off = win_h/2 - scroll
    col = Image.new('RGBA', (COL_W+24, win_h), (0,0,0,0)); cd = ImageDraw.Draw(col)
    tn = t-LEAD
    for i,b in enumerate(BLOCKS):
        by = off + b['y']
        if by + b['h'] < -20 or by > win_h+20: continue
        ph=b['ph']; active = (i==cur)
        wi=-1
        if active:
            for k,w in enumerate(ph['words']):
                if w['start'] <= tn < w['end']: wi=k
            if tn >= ph['words'][-1]['end']: wi=-2
        for it in b['items']:
            x = 12+it['x']; y = by+it['y']
            col_ = INK if active else FADED
            if it['kind'] in ('syl','pho') and active and it['idx']==wi:
                h = 46 if it['kind']=='syl' else 30
                cd.rounded_rectangle((x-6, y-2, x+it['w']+6, y+h), radius=8, fill=PILL)
            if it['kind']=='eng': col_ = (95,88,80) if active else FADED
            cd.text((x,y), it['text'], font=it['fnt'], fill=col_)
    frame.alpha_composite(col, (cx-12, win_top))

# ---------- frame ----------
BACK = None
def backdrop():
    global BACK
    if BACK is None:
        rng = np.random.default_rng(7)
        n = rng.normal(0,2.2,(OUT_H,OUT_W,1))
        b = np.clip(np.array(CREAM,float)[None,None,:]+n,0,255).astype(np.uint8)
        BACK = Image.fromarray(b).convert('RGBA')
        # card shadow
        sh = Image.new('L',(OUT_W,OUT_H),0); d=ImageDraw.Draw(sh)
        d.rectangle((CARD[0]+2,CARD[1]+8,CARD[0]+CARD[2]+2,CARD[1]+CARD[3]+10), fill=70)
        sh = sh.filter(ImageFilter.GaussianBlur(10))
        dark = Image.new('RGBA',(OUT_W,OUT_H),(40,30,20,255)); dark.putalpha(sh)
        BACK.alpha_composite(dark)
    return BACK

def render_frame(t):
    frame = backdrop().copy()
    page, u = render_page(t)
    zoom = 1 + 0.035*smooth(u)
    scale = CARD[3]/PH*zoom
    pg = page.crop((M,M,M+PW,M+PH)).resize((round(PW*scale), round(PH*scale)), Image.LANCZOS)
    # crop to card, centred
    cx0 = (pg.width-CARD[2])//2; cy0 = (pg.height-CARD[3])//2
    pg = pg.crop((cx0,cy0,cx0+CARD[2],cy0+CARD[3]))
    frame.alpha_composite(pg, (CARD[0],CARD[1]))
    draw_column(frame, t)
    if t > TOTAL-1.0:
        a = int(255*smooth((t-(TOTAL-1.0))/1.0))
        frame.alpha_composite(Image.new('RGBA',(OUT_W,OUT_H),CREAM+(a,)))
    return frame.convert('RGB')

def work(args):
    i, t, out = args
    render_frame(t).save(out, quality=93)
    return i

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'test':
        for t in [float(x) for x in sys.argv[2:]]:
            render_frame(t).save(f'{S}/prev/test_{t:05.1f}.jpg', quality=92)
            print('rendered', t)
    else:
        from multiprocessing import Pool
        outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
        n = int(TOTAL*FPS)
        jobs = [(i, i/FPS, f'{outdir}/f{i:05d}.jpg') for i in range(n)]
        with Pool(8) as pool:
            for k,_ in enumerate(pool.imap_unordered(work, jobs, chunksize=8)):
                if k % 120 == 0: print(k, '/', n, flush=True)
        print('done', n)
