"""Steps 6-7 for one page: animate the pieces and render the page movie.

   python3 scripts/animate.py NN test [t ...]     a few frames into work/pageNN/prev/
   python3 scripts/animate.py NN render           every frame, then out/pageNN.mp4 (frames deleted after)
   SF_TEXT=syl+eng python3 scripts/animate.py NN render     another text combination (out/pageNN_syl+eng.mp4)

Page 27 has its own beats (scripts/page27_beats.py); every other page is driven by pages/NN.json:

  "pieces":  {name: selector}                  see build_pieces.py
  "depth":   {name: factor}                    camera parallax, 0.35 far trees ... 1.0 things that travel (default 0.85)
  "pivot":   {name: "bottom"|"center"|"top"|[x,y]}   the point a piece turns and scales about (default bottom centre)
  "camera":  {"zoom": [1.0, 1.035], "focus": [0.5, 0.5], "drift": 24}
  "motions": {name: [motion, ...]}             the story beat, one or two motions per page

A motion is {"type": ..., "at": T, "dur": seconds, ...}. T is seconds into the narration, or "p3" (start of
phrase 3), "p3e" (its end), "p3w2" (start of word 2 of phrase 3), each optionally "+0.5"/"-0.5".
Types (all add up; offsets in page pixels, angles in degrees):
  move     dx, dy                       ease: "smooth" | "linear" | "in" | "out" | "steps:N" (stop-motion)
  rotate   deg                          same eases
  scale    sx, sy                       factor reached at the end
  fade     to (alpha 0..1); "from" sets the start alpha (default 1)
  hide     the piece is not on the page before "at"; it is placed (drops in) at "at"
  away     the piece leaves the page at "at" (instant)
  sway     amp (deg), freq (Hz)         runs from "at" (default the start) to "until"; 12 steps a second
  flicker  amp (deg)                    flame: two sines, plus a breathing squash
  bob      amp (px), freq
  jab      dx, dy, count                quick out-and-back thrusts over dur, stepped
  shake    amp (px), freq
  path     pts [[x,y],...]              the pivot travels through these page points over dur
  glint    a brightening flash for dur
  fall     dy, deg                      gravity drop over dur
  swap     with: other piece name; this piece hides and the other appears at "at"
"""
import sys, os, json, math, hashlib, re
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frame as F
from frame import M, PW, PH, LEAD, TAIL, smooth, quant, stepped

n = int(sys.argv[1])
HERE = F.HERE; S = f'{HERE}/work/page{n:02d}'
timing = json.load(open(f'{S}/timing{n:02d}.json'))
NARR = F.audio_duration(n)
TOTAL = LEAD + NARR + TAIL

def T(spec):
    """resolve a time spec to seconds into the video"""
    if spec is None: return 0.0
    if isinstance(spec, (int, float)): return LEAD + float(spec)
    m = re.fullmatch(r'p(\d+)(e|w(\d+))?([+-][\d.]+)?', spec)
    if not m:
        if spec == 'start': return 0.0
        if spec == 'end': return TOTAL
        return LEAD + float(spec)
    ph = timing[int(m.group(1)) - 1]
    if m.group(2) == 'e': t = ph['end']
    elif m.group(3): t = ph['words'][int(m.group(3)) - 1]['start']
    else: t = ph['start']
    return LEAD + t + (float(m.group(4)) if m.group(4) else 0.0)

def ease(u, kind='smooth'):
    u = min(max(u, 0.0), 1.0)
    if kind == 'linear': return u
    if kind == 'in': return u * u
    if kind == 'out': return 1 - (1 - u) ** 2
    if kind.startswith('steps'): return stepped(u, int(kind.split(':')[1]))
    return smooth(u)

def seed(name, k=0):
    h = hashlib.md5(f'{name}{k}'.encode()).digest()
    return int.from_bytes(h[:4], 'little') / 2 ** 32

def render_fn():
    if n == 27:
        import page27_beats
        return page27_beats.make(timing, TOTAL)
    cfg = json.load(open(f'{HERE}/pages/{n:02d}.json'))
    man = json.load(open(f'{S}/pieces/manifest.json'))
    paper = Image.open(f'{S}/pieces/paper.png').convert('RGBA')
    PAD = 10
    pieces = {}
    for d in man:
        im = Image.open(f"{S}/pieces/{d['name']}.png").convert('RGBA')
        padded = Image.new('RGBA', (im.width + 2 * PAD, im.height + 2 * PAD), (0, 0, 0, 0)); padded.paste(im, (PAD, PAD))
        pv = cfg.get('pivot', {}).get(d['name'], 'bottom')
        piv = {'bottom': d['pivot'], 'center': d['center'], 'top': d['top']}.get(pv, pv) if isinstance(pv, str) else pv
        pieces[d['name']] = dict(d, img=padded, shadow=make_shadow(padded), x=d['x'] - PAD, y=d['y'] - PAD, pivot=piv)
    order = [d['name'] for d in sorted(man, key=lambda d: d['z'])]
    depth = cfg.get('depth', {})
    motions = {k: [dict(m, _t=T(m.get('at')), _until=T(m['until']) if 'until' in m else TOTAL) for m in v]
               for k, v in cfg.get('motions', {}).items()}
    swaps_in = {m['with']: m['_t'] for v in motions.values() for m in v if m['type'] == 'swap'}
    hidden = {k: min(m['_t'] for m in v if m['type'] == 'hide') for k, v in motions.items() if any(m['type'] == 'hide' for m in v)}
    for k, t in swaps_in.items(): hidden[k] = t
    drift = cfg.get('camera', {}).get('drift', 24)
    N = len(order)

    def render_page(t):
        canvas = Image.new('RGBA', (PW + 2 * M, PH + 2 * M), (0, 0, 0, 0))
        canvas.alpha_composite(paper, (M, M))
        u = t / TOTAL
        camx = -drift / 2 + drift * smooth(u)
        tq = quant(t)
        for i, name in enumerate(order):
            p = pieces[name]; ms = motions.get(name, [])
            # placement: pieces drop onto the page during the lead-in, or when they first appear
            t_in = hidden.get(name, 0.12 + 1.25 * i / max(N, 1))
            if t < t_in: continue
            if any(m['type'] == 'away' and t >= m['_t'] for m in ms): continue
            if any(m['type'] == 'swap' and t >= m['_t'] for m in ms): continue
            e = stepped((t - t_in) / 0.22, 3)
            dx = camx * (depth.get(name, 0.85) - 0.65); dy = -14 * (1 - e)
            shadow = (2 + 5 * (1 - e), 3 + 7 * (1 - e))
            rot = 0.0; sx = sy = 1.0; alpha = 1.0; glint = 0.0
            for m in ms:
                ty = m['type']; t0 = m['_t']; dur = m.get('dur', 1.0); k = m.get('ease', 'smooth')
                uu = (t - t0) / dur if dur > 0 else float(t >= t0)
                if ty == 'move': f = ease(uu, k); dx += m.get('dx', 0) * f; dy += m.get('dy', 0) * f
                elif ty == 'rotate': rot += m['deg'] * ease(uu, k)
                elif ty == 'scale':
                    f = ease(uu, k); sx *= 1 + (m.get('sx', 1) - 1) * f; sy *= 1 + (m.get('sy', 1) - 1) * f
                elif ty == 'fade':
                    a0 = m.get('from', 1.0); alpha *= a0 + (m['to'] - a0) * ease(uu, k)
                elif ty in ('sway', 'flicker', 'bob', 'shake'):
                    if t < t0 or t > m['_until']: continue
                    tt = tq - t0; ph = seed(name, 1) * 6.28
                    ramp = smooth((t - t0) / 0.6) * (1 - smooth((t - m['_until'] + 0.6) / 0.6) if m['_until'] < TOTAL else 1)
                    if ty == 'sway':
                        rot += ramp * m.get('amp', 1.5) * math.sin(2 * math.pi * m.get('freq', 0.5) * tt + ph)
                    elif ty == 'flicker':
                        A = m.get('amp', 2.0); r0, r1, r2 = seed(name, 1), seed(name, 2), seed(name, 3)
                        rot += ramp * (A * math.sin(2 * math.pi * (0.55 + 0.5 * r0) * tt + r1 * 6.28)
                                       + 0.45 * A * math.sin(2 * math.pi * (2.1 + 0.8 * r2) * tt + r0 * 6.28))
                        sy *= 1 + ramp * 0.04 * math.sin(2 * math.pi * (0.8 + 0.6 * r1) * tt + r2 * 6.28)
                    elif ty == 'bob':
                        dy += ramp * m.get('amp', 6) * math.sin(2 * math.pi * m.get('freq', 0.8) * tt + ph)
                    else:
                        dx += ramp * m.get('amp', 3) * math.sin(2 * math.pi * m.get('freq', 6) * tt + ph)
                        dy += ramp * m.get('amp', 3) * 0.6 * math.sin(2 * math.pi * m.get('freq', 6) * 1.3 * tt)
                elif ty == 'jab':
                    if 0 <= uu <= 1:
                        c = m.get('count', 3); w = (uu * c) % 1.0
                        f = stepped(1 - abs(2 * w - 1), 3)
                        dx += m.get('dx', 0) * f; dy += m.get('dy', 0) * f
                elif ty == 'path':
                    pts = np.array(m['pts'], float)
                    if t >= t0:
                        seg = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
                        s = ease(uu, k) * seg[-1]
                        j = min(max(np.searchsorted(seg, s), 1), len(pts) - 1)
                        w = (s - seg[j - 1]) / max(seg[j] - seg[j - 1], 1e-6)
                        x, y = pts[j - 1] * (1 - w) + pts[j] * w
                        dx += x - p['pivot'][0]; dy += y - p['pivot'][1]
                elif ty == 'glint':
                    if 0 <= uu <= 1: glint = max(glint, math.sin(math.pi * uu))
                elif ty == 'fall':
                    f = ease(uu, 'in'); dy += m.get('dy', 200) * f; rot += m.get('deg', 0) * f
            if alpha <= 0.01: continue
            img = p['img']; shimg = None
            if glint > 0:
                img = ImageEnhance.Brightness(img).enhance(1 + 0.6 * glint)
                shimg = p['shadow']
            place(canvas, p, rot, sx, sy, dx, dy, shadow, img, alpha, shimg)
        return canvas
    return render_page, cfg.get('camera')

def make_shadow(im):
    a = im.split()[3].filter(ImageFilter.GaussianBlur(2.2)).point(lambda v: int(v * 0.32))
    sh = Image.new('RGBA', im.size, (30, 20, 15, 255)); sh.putalpha(a)
    return sh

def xform(im, px, py, rot=0.0, sx=1.0, sy=1.0, dx=0.0, dy=0.0):
    w, h = im.size
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    def fwd(x, y):
        X = (x - px) * sx; Y = (y - py) * sy
        return (c * X - s * Y + px + dx, s * X + c * Y + py + dy)
    cs = [fwd(0, 0), fwd(w, 0), fwd(0, h), fwd(w, h)]
    ox0 = math.floor(min(p[0] for p in cs)); oy0 = math.floor(min(p[1] for p in cs))
    ox1 = math.ceil(max(p[0] for p in cs)); oy1 = math.ceil(max(p[1] for p in cs))
    if abs(rot) < 1e-3 and abs(sx - 1) < 1e-4 and abs(sy - 1) < 1e-4:
        return im, round(dx), round(dy)
    W_, H_ = max(1, ox1 - ox0), max(1, oy1 - oy0)
    a = c / sx; b = s / sx; cc = (c / sx) * (ox0 - px - dx) + (s / sx) * (oy0 - py - dy) + px
    d = -s / sy; e = c / sy; f = (-s / sy) * (ox0 - px - dx) + (c / sy) * (oy0 - py - dy) + py
    return im.transform((W_, H_), Image.AFFINE, (a, b, cc, d, e, f), resample=Image.BILINEAR), ox0, oy0

def blit(canvas, im, x, y):
    cw, ch = canvas.size; w, h = im.size
    x0, y0 = max(x, 0), max(y, 0); x1, y1 = min(x + w, cw), min(y + h, ch)
    if x1 <= x0 or y1 <= y0: return
    src = im if (x0 == x and y0 == y and x1 == x + w and y1 == y + h) else im.crop((x0 - x, y0 - y, x1 - x, y1 - y))
    canvas.alpha_composite(src, (x0, y0))

def place(canvas, p, rot, sx, sy, dx, dy, shadow, img, alpha, shimg=None):
    px, py = p['pivot'][0] - p['x'], p['pivot'][1] - p['y']
    sh = shimg or p['shadow']
    if alpha < 1:
        sh = sh.copy(); sh.putalpha(sh.split()[3].point(lambda v: int(v * alpha)))
    s_im, sx0, sy0 = xform(sh, px, py, rot, sx, sy, dx, dy)
    blit(canvas, s_im, int(p['x'] + sx0 + shadow[0] + M), int(p['y'] + sy0 + shadow[1] + M))
    im, ox0, oy0 = xform(img, px, py, rot, sx, sy, dx, dy)
    if alpha < 1:
        im = im.copy(); im.putalpha(im.split()[3].point(lambda v: int(v * alpha)))
    blit(canvas, im, int(p['x'] + ox0 + M), int(p['y'] + oy0 + M))

if __name__ == '__main__':
    rp, cam = render_fn()
    F.main(F.Movie(n, rp, TOTAL, timing, cam), n)
