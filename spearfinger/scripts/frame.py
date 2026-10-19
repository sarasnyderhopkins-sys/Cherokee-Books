"""What every page of the movie shares: the 16:9 frame, the cream card with the page on it, the gentle camera,
the read-along text column, and the render / encode commands.

A page module supplies render_page(t) -> RGBA image of the page (PW+2M x PH+2M, page at offset M), where t is
seconds into the page's video (the narration starts at LEAD).
"""
import json, math, os, sys, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_W, OUT_H = 1920, 1080
FPS = 24
PW, PH = 1200, 940
M = 80                      # working margin around the page
LEAD, TAIL = 1.8, 2.6
CARD = (48, 48, 1256, 984)
COL_X, COL_W = 1352, 520
CREAM = (241, 235, 224)
INK = (40, 38, 39)
FADED = (168, 162, 154)
PILL = (246, 221, 140)
RULE = (205, 196, 182)
TITLE_SYL = 'ᎪᏍᏓᏱ ᏗᎦᏘᏍᏙᏗ ᎦᏰᏌᏛᎢ'      # as printed in the July 2008 proof (Sara, 19 Oct 2026)

FONT_DIR = f'{HERE}/fonts/'
def font(name, size, weight=None):
    f = ImageFont.truetype(FONT_DIR + name, size)
    if weight:
        try: f.set_variation_by_name(weight)
        except Exception: pass
    return f
F_SYL = font('NotoSansCherokee-VF.ttf', 38)
F_PHO = font('NotoSerif-VF.ttf', 24)
F_ENG = font('NotoSerif-Italic-VF.ttf', 23)
F_CAP = font('NotoSerif-VF.ttf', 18)
F_CAPS = font('NotoSansCherokee-VF.ttf', 21)

# text modes: which lines the column shows (a movie cannot toggle, so each export picks one)
TEXT = os.environ.get('SF_TEXT', 'syl+pho+eng').split('+')

def smooth(u): u = min(max(u, 0.0), 1.0); return u * u * (3 - 2 * u)
def quant(t, fps=12): return math.floor(t * fps) / fps
def stepped(u, steps=3): return math.floor(min(max(u, 0), 1) * steps) / steps

def audio_duration(n):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
                                 f'{HERE}/assets-src/Spearfinger_{n:02d}.mp3'], capture_output=True, text=True).stdout)

# ---------- text column ----------
def wrap_words(words, fnt, width):
    lines = []; cur = []; w = 0
    for wd in words:
        ww = fnt.getlength(wd); sp = fnt.getlength(' ') if cur else 0
        if cur and w + sp + ww > width:
            lines.append(cur); cur = [wd]; w = ww
        else:
            cur.append(wd); w += sp + ww
    if cur: lines.append(cur)
    return lines

class Column:
    def __init__(self, page, timing):
        self.page = page; self.timing = timing
        self.blocks = self.layout()

    def layout(self):
        blocks = []; y = 0
        for ph in self.timing:
            syl = [w['syl'] for w in ph['words']]; pho = [w['pho'] for w in ph['words']]
            b = dict(ph=ph, y=y, items=[]); yy = 0
            rows = []
            if 'syl' in TEXT: rows.append((wrap_words(syl, F_SYL, COL_W), F_SYL, 52, 'syl'))
            if 'pho' in TEXT: rows.append((wrap_words(pho, F_PHO, COL_W), F_PHO, 34, 'pho'))
            for lines, fnt, lh, kind in rows:
                wi = 0
                for ln in lines:
                    x = 0
                    for wd in ln:
                        b['items'].append(dict(kind=kind, idx=wi, text=wd, x=x, y=yy, w=fnt.getlength(wd), fnt=fnt))
                        x += fnt.getlength(wd) + fnt.getlength(' '); wi += 1
                    yy += lh
                yy += 4
            if 'eng' in TEXT:
                for ln in wrap_words(ph['eng'].split(), F_ENG, COL_W):
                    b['items'].append(dict(kind='eng', idx=-1, text=' '.join(ln), x=0, y=yy, fnt=F_ENG)); yy += 32
            b['h'] = yy; blocks.append(b); y += yy + 44
        return blocks

    def current(self, t):
        tn = t - LEAD; cur = None; last = None
        for i, ph in enumerate(self.timing):
            if tn >= ph['start']: cur = i; last = ph['start'] + LEAD
        return cur, last

    def draw(self, frame, t):
        dr = ImageDraw.Draw(frame)
        cx = COL_X; top = CARD[1]; H = CARD[3]
        dr.text((cx, top + 2), TITLE_SYL, font=F_CAPS, fill=FADED)
        dr.text((cx, top + 32), f'Spearfinger  ·  page {self.page}', font=F_CAP, fill=FADED)
        dr.line((cx, top + 64, cx + COL_W, top + 64), fill=RULE, width=1)
        cur, tc = self.current(t)
        win_top, win_h = top + 90, H - 110
        centre = lambda i: self.blocks[i]['y'] + self.blocks[i]['h'] / 2
        if cur is None: scroll = centre(0)
        else:
            target = centre(cur); prev = centre(cur - 1) if cur > 0 else centre(0)
            scroll = prev + (target - prev) * smooth((t - tc) / 0.55)
        off = win_h / 2 - scroll
        col = Image.new('RGBA', (COL_W + 24, win_h), (0, 0, 0, 0)); cd = ImageDraw.Draw(col)
        tn = t - LEAD
        for i, b in enumerate(self.blocks):
            by = off + b['y']
            if by + b['h'] < -20 or by > win_h + 20: continue
            ph = b['ph']; active = (i == cur); wi = -1
            if active:
                for k, w in enumerate(ph['words']):
                    if w['start'] <= tn < w['end']: wi = k
            for it in b['items']:
                x = 12 + it['x']; y = by + it['y']
                c = INK if active else FADED
                if it['kind'] in ('syl', 'pho') and active and it['idx'] == wi:
                    h = 48 if it['kind'] == 'syl' else 32
                    cd.rounded_rectangle((x - 6, y - 1, x + it['w'] + 6, y + h), radius=8, fill=PILL)
                if it['kind'] == 'eng': c = (95, 88, 80) if active else FADED
                cd.text((x, y), it['text'], font=it['fnt'], fill=c)
        frame.alpha_composite(col, (cx - 12, win_top))

# ---------- frame ----------
_BACK = None
def backdrop():
    global _BACK
    if _BACK is None:
        rng = np.random.default_rng(7)
        n = rng.normal(0, 2.2, (OUT_H, OUT_W, 1))
        b = np.clip(np.array(CREAM, float)[None, None, :] + n, 0, 255).astype(np.uint8)
        _BACK = Image.fromarray(b).convert('RGBA')
        sh = Image.new('L', (OUT_W, OUT_H), 0); d = ImageDraw.Draw(sh)
        d.rectangle((CARD[0] + 2, CARD[1] + 8, CARD[0] + CARD[2] + 2, CARD[1] + CARD[3] + 10), fill=70)
        sh = sh.filter(ImageFilter.GaussianBlur(10))
        dark = Image.new('RGBA', (OUT_W, OUT_H), (40, 30, 20, 255)); dark.putalpha(sh)
        _BACK.alpha_composite(dark)
    return _BACK

class Movie:
    """one page: render_page(t) from the page module, the camera, the column"""
    def __init__(self, page, render_page, total, timing, camera=None):
        self.page = page; self.render_page = render_page; self.total = total
        self.column = Column(page, timing)
        self.camera = camera or {}

    def frame(self, t):
        frame = backdrop().copy()
        pg = self.render_page(t)
        u = t / self.total
        z0, z1 = self.camera.get('zoom', [1.0, 1.035])
        zoom = z0 + (z1 - z0) * smooth(u)
        fx, fy = self.camera.get('focus', [0.5, 0.5])       # zoom centre, fraction of the page
        scale = CARD[3] / PH * zoom
        pg = pg.crop((M, M, M + PW, M + PH)).resize((round(PW * scale), round(PH * scale)), Image.LANCZOS)
        cx0 = int((pg.width - CARD[2]) * fx); cy0 = int((pg.height - CARD[3]) * fy)
        cx0 = min(max(cx0, 0), pg.width - CARD[2]); cy0 = min(max(cy0, 0), pg.height - CARD[3])
        pg = pg.crop((cx0, cy0, cx0 + CARD[2], cy0 + CARD[3]))
        frame.alpha_composite(pg, (CARD[0], CARD[1]))
        self.column.draw(frame, t)
        if t > self.total - 1.0:
            a = int(255 * smooth((t - (self.total - 1.0)) / 1.0))
            frame.alpha_composite(Image.new('RGBA', (OUT_W, OUT_H), CREAM + (a,)))
        if t < 0.5:
            a = int(255 * (1 - smooth(t / 0.5)))
            frame.alpha_composite(Image.new('RGBA', (OUT_W, OUT_H), CREAM + (a,)))
        return frame.convert('RGB')

_MOVIE = None
def _work(args):
    i, t, out = args
    _MOVIE.frame(t).save(out, quality=93)
    return i

def main(movie, n):
    global _MOVIE
    _MOVIE = movie
    W = f'{HERE}/work/page{n:02d}'
    mode = sys.argv[2] if len(sys.argv) > 2 else 'test'
    if mode == 'test':
        os.makedirs(f'{W}/prev', exist_ok=True)
        ts = [float(x) for x in sys.argv[3:]] or [0.6, 1.5, LEAD + 2, movie.total / 2, movie.total - 3]
        for t in ts:
            movie.frame(t).save(f'{W}/prev/test_{t:05.1f}.jpg', quality=90); print('rendered', t)
    elif mode in ('render', 'movie'):
        from multiprocessing import Pool
        outdir = f'{W}/frames'; os.makedirs(outdir, exist_ok=True)
        for f in os.listdir(outdir): os.remove(f'{outdir}/{f}')
        nfr = int(movie.total * FPS)
        jobs = [(i, i / FPS, f'{outdir}/f{i:05d}.jpg') for i in range(nfr)]
        with Pool(int(os.environ.get('SF_PROCS', os.cpu_count()))) as pool:
            for k, _ in enumerate(pool.imap_unordered(_work, jobs, chunksize=6)):
                if k % 240 == 0: print(k, '/', nfr, flush=True)
        suffix = '' if TEXT == ['syl', 'pho', 'eng'] else '_' + '+'.join(TEXT)
        out = f'{HERE}/out/page{n:02d}{suffix}.mp4'; os.makedirs(f'{HERE}/out', exist_ok=True)
        lead_ms = int(LEAD * 1000)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', f'{outdir}/f%05d.jpg',
                        '-i', f'{HERE}/assets-src/Spearfinger_{n:02d}.mp3',
                        '-filter_complex', f'[1:a]adelay={lead_ms}|{lead_ms},apad[a]', '-map', '0:v', '-map', '[a]',
                        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2', '-shortest', '-movflags', '+faststart', out], check=True)
        for f in os.listdir(outdir): os.remove(f'{outdir}/{f}')
        os.rmdir(outdir)
        print('wrote', out)
