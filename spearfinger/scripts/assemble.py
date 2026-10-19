"""Step 8: join the title card, the 27 page movies and the credits into the book.

   python3 scripts/assemble.py                -> out/Spearfinger.mp4 (1080p) and out/Spearfinger-720p.mp4
   SF_TEXT=syl+eng python3 scripts/assemble.py   joins the pageNN_syl+eng.mp4 versions instead

Every page fades up from the cream backdrop and back down to it, so the pages simply follow each other
(a dip to cream between pages). All clips share codec settings, so they are joined without re-encoding.
"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frame as F

OUT = f'{F.HERE}/out'
suffix = '' if F.TEXT == ['syl', 'pho', 'eng'] else '_' + '+'.join(F.TEXT)
clips = [f'{OUT}/title.mp4'] + [f'{OUT}/page{n:02d}{suffix}.mp4' for n in range(1, 28)] + [f'{OUT}/credits.mp4']
missing = [c for c in clips if not os.path.exists(c)]
if missing:
    sys.exit('missing: ' + ', '.join(os.path.basename(c) for c in missing))
lst = f'{OUT}/concat{suffix}.txt'
open(lst, 'w').write(''.join(f"file '{c}'\n" for c in clips))
big = f'{OUT}/Spearfinger{suffix}.mp4'
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy',
                '-movflags', '+faststart', big], check=True)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', big, '-vf', 'scale=1280:720:flags=lanczos',
                '-c:v', 'libx264', '-preset', 'slow', '-crf', '22', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', f'{OUT}/Spearfinger{suffix}-720p.mp4'], check=True)
os.remove(lst)
dur = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', big],
                     capture_output=True, text=True).stdout.strip()
print('wrote', big, f'({float(dur)/60:.1f} min) and the 720p copy')
