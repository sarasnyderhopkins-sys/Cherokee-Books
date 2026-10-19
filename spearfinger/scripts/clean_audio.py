import subprocess, json, re, sys, os, csv
D = '/Users/slsnyder/Downloads/C02Z129YJWF2/SpearfingerTotal/Spearfinger Illustrations and Audio/SpearfingerSound'
O = '/Users/slsnyder/Downloads/C02Z129YJWF2/SpearfingerTotal/ReadAlong/audio'
os.makedirs(O, exist_ok=True)
CHAIN = "pan=mono|c0=0.5*c0+0.5*c1,highpass=f=75,afftdn=nr=8:nf=-42:tn=1,acompressor=threshold=-20dB:ratio=2:attack=12:release=180:knee=5"
TARGET = "I=-19:TP=-1.5:LRA=9"
def measure(path, chain):
    af = (chain + ',' if chain else '') + f"loudnorm={TARGET}:print_format=json"
    r = subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',path,'-af',af,'-f','null','-'], capture_output=True, text=True)
    m = re.search(r'\{.*\}', r.stderr, re.S)
    return json.loads(m.group(0))
rows = []
for i in range(1, 28):
    src = f'{D}/{i} Audio Track.aiff'; out = f'{O}/Spearfinger_{i:02d}.mp3'
    m = measure(src, CHAIN)
    ln = (f"loudnorm={TARGET}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=summary")
    r = subprocess.run(['ffmpeg','-y','-hide_banner','-nostats','-i',src,'-af',f"{CHAIN},{ln},aresample=44100",
                        '-ac','1','-c:a','libmp3lame','-q:a','3',out], capture_output=True, text=True)
    if r.returncode != 0: print('FAILED', i, r.stderr[-600:]); sys.exit(1)
    v = measure(out, '')
    orig = measure(src, '')
    rows.append([f'{i:02d}', orig['input_i'], orig['input_tp'], v['input_i'], v['input_tp'], v['input_lra']])
    print(f"{i:02d}: source {orig['input_i']} LUFS / {orig['input_tp']} dBTP  ->  mp3 {v['input_i']} LUFS / {v['input_tp']} dBTP  LRA {v['input_lra']}", flush=True)
with open(f'{O}/loudness_report.csv','w',newline='') as f:
    w = csv.writer(f); w.writerow(['track','source_lufs','source_true_peak_db','mp3_lufs','mp3_true_peak_db','mp3_lra']); w.writerows(rows)
