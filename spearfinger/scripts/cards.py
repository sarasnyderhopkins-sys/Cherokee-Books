"""The title card and the end credits, in the same frame as the pages.

   python3 scripts/cards.py            -> out/title.mp4, out/credits.mp4

Title card: the page 9 picture (Sara's choice of cover, 19 Oct 2026) on the cream card, the printed title and the
makers in the column. Credits: Sara's credit line (19 Oct 2026) and the publisher and sponsor from the colophon.
"""
import os, subprocess, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frame as F
from frame import OUT_W, OUT_H, CARD, COL_X, COL_W, CREAM, INK, FADED, RULE, FPS, smooth, font

HERE = F.HERE
F_TITLE_SYL = font('NotoSansCherokee-VF.ttf', 38, 'Medium')
F_TITLE = font('NotoSerif-VF.ttf', 46)
F_ROLE = font('NotoSerif-Italic-VF.ttf', 22)
F_NAME = font('NotoSerif-VF.ttf', 27)
F_SMALL = font('NotoSerif-VF.ttf', 20)

MAKERS = [('Adapted and illustrated by', 'Luzene Hill'),
          ('Told in Cherokee by', 'Nannie Taylor'),
          ('Edited by', 'Hartwell Francis')]
CREDITS = [('Adapted and illustrated by', 'Luzene Hill'),
           ('Told in Cherokee by', 'Nannie Taylor'),
           ('Edited by', 'Hartwell Francis'),
           ('Digital book created by', 'Sara Snyder Hopkins')]
COLOPHON = ['© 2008 Luzene Hill',
            'Galohisdi Press, Cullowhee, North Carolina, 2008',
            'Western Carolina University Cherokee Language Program,',
            'with support from the Cherokee Preservation Foundation']

_PLAIN = None
def plain():
    global _PLAIN
    if _PLAIN is None:
        import numpy as np
        n = np.random.default_rng(7).normal(0, 2.2, (OUT_H, OUT_W, 1))
        _PLAIN = Image.fromarray(np.clip(np.array(CREAM, float)[None, None, :] + n, 0, 255).astype(np.uint8)).convert('RGBA')
    return _PLAIN

cover = Image.open(f'{HERE}/assets-src/Spearfinger042109_009.tif').convert('RGB')

def centered(d, y, text, fnt, fill, x0=COL_X, w=COL_W):
    d.text((x0 + (w - fnt.getlength(text)) / 2, y), text, font=fnt, fill=fill)

def title_frame(t, total):
    fr = F.backdrop().copy()
    zoom = 1 + 0.03 * smooth(t / total)
    scale = CARD[3] / cover.height * zoom
    pg = cover.resize((round(cover.width * scale), round(cover.height * scale)), Image.LANCZOS)
    cx0 = (pg.width - CARD[2]) // 2; cy0 = (pg.height - CARD[3]) // 2
    fr.paste(pg.crop((cx0, cy0, cx0 + CARD[2], cy0 + CARD[3])), (CARD[0], CARD[1]))
    layer = Image.new('RGBA', (OUT_W, OUT_H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    y = 300
    centered(d, y, F.TITLE_SYL, F_TITLE_SYL, INK); y += 86
    centered(d, y, 'Spearfinger', F_TITLE, INK); y += 92
    d.line((COL_X + 140, y, COL_X + COL_W - 140, y), fill=RULE, width=1); y += 40
    for role, name in MAKERS:
        centered(d, y, role, F_ROLE, FADED); y += 32
        centered(d, y, name, F_NAME, INK); y += 56
    a = smooth((t - 0.6) / 1.2)
    layer.putalpha(layer.split()[3].point(lambda v: int(v * a)))
    fr.alpha_composite(layer)
    fade(fr, t, total)
    return fr.convert('RGB')

def credits_frame(t, total):
    fr = plain().copy()
    layer = Image.new('RGBA', (OUT_W, OUT_H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    y = 190
    centered(d, y, F.TITLE_SYL, F_TITLE_SYL, INK, 0, OUT_W); y += 80
    centered(d, y, 'Spearfinger', F_TITLE, INK, 0, OUT_W); y += 100
    for role, name in CREDITS:
        centered(d, y, role, F_ROLE, FADED, 0, OUT_W); y += 32
        centered(d, y, name, F_NAME, INK, 0, OUT_W); y += 62
    y += 20
    for line in COLOPHON:
        centered(d, y, line, F_SMALL, FADED, 0, OUT_W); y += 32
    a = smooth((t - 0.3) / 1.0)
    layer.putalpha(layer.split()[3].point(lambda v: int(v * a)))
    fr.alpha_composite(layer)
    fade(fr, t, total)
    return fr.convert('RGB')

def fade(fr, t, total):
    if t > total - 1.2:
        a = int(255 * smooth((t - (total - 1.2)) / 1.2))
        fr.alpha_composite(Image.new('RGBA', (OUT_W, OUT_H), CREAM + (a,)))
    if t < 0.5:
        a = int(255 * (1 - smooth(t / 0.5)))
        fr.alpha_composite(Image.new('RGBA', (OUT_W, OUT_H), CREAM + (a,)))

def render(name, fn, total):
    d = f'{HERE}/work/cards/{name}'; os.makedirs(d, exist_ok=True); os.makedirs(f'{HERE}/out', exist_ok=True)
    for i in range(int(total * FPS)):
        fn(i / FPS, total).save(f'{d}/f{i:05d}.jpg', quality=93)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', f'{d}/f%05d.jpg',
                    '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-map', '0:v', '-map', '1:a',
                    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2', '-shortest', '-movflags', '+faststart',
                    f'{HERE}/out/{name}.mp4'], check=True)
    for f in os.listdir(d): os.remove(f'{d}/{f}')
    print('wrote', name)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        os.makedirs(f'{HERE}/work/cards', exist_ok=True)
        title_frame(4.0, 7.0).save(f'{HERE}/work/cards/title_test.jpg', quality=90)
        credits_frame(4.0, 9.0).save(f'{HERE}/work/cards/credits_test.jpg', quality=90)
    else:
        render('title', title_frame, 7.0)
        render('credits', credits_frame, 9.0)
