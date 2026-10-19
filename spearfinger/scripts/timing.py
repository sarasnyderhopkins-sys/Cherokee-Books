import json, re, sys, csv
S=sys.argv[1]
ph = json.load(open(f'{S}/phrases27.json'))
# pauses (-24 dB, >=0.2s) as (start,end)
pauses = [(2.654,3.019),(3.777,4.257),(4.875,5.225),(6.015,6.627),(9.177,9.442),(11.183,11.592),(12.250,12.500),(13.989,14.290),(14.731,15.097),(15.433,15.749),(16.938,17.176),(18.026,18.546),(19.760,20.454),(21.377,21.641),(21.965,22.795),(23.472,23.815),(25.037,25.411),(26.353,26.645),(27.193,27.396),(27.934,28.468),(29.484,29.807),(30.583,31.325),(31.817,32.195),(33.027,33.302),(33.972,34.575),(36.175,36.384),(37.068,37.333),(37.977,38.335),(39.545,39.813),(42.432,42.724),(43.728,43.961),(45.203,45.579),(46.656,46.982),(47.426,47.746),(48.579,48.959),(49.261,49.496),(50.279,50.654),(51.250,51.68)]
END=51.25
# speech chunks
chunks=[]; t=0.0
for a,b in pauses:
    if a>t+0.05: chunks.append((t,a))
    t=b
if END>t: chunks.append((t,END))
def nsyl(w): return sum(1 for ch in w if 'Ꭰ'<=ch<='Ᏽ' and ch!='Ꮝ') or 1
words=[]  # (phrase_idx, word_idx, syl)
for i,p in enumerate(ph):
    for j,w in enumerate(p['syl'].split()):
        words.append((i,j,nsyl(w)))
total = sum(w[2] for w in words)
speech = sum(b-a for a,b in chunks)
# map syllable cursor -> time via chunks
def syl_to_time(s):
    frac = s/total*speech; acc=0
    for a,b in chunks:
        if acc+(b-a) >= frac: return a+(frac-acc)
        acc += b-a
    return END
cur=0; out=[]
for i,p in enumerate(ph):
    ws=p['syl'].split(); ps=p['pho'].split()
    wt=[]
    for j,w in enumerate(ws):
        n=nsyl(w); t0=syl_to_time(cur); t1=syl_to_time(cur+n); cur+=n
        wt.append(dict(syl=w, pho=ps[j] if j<len(ps) else '', start=round(t0,2), end=round(t1,2)))
    out.append(dict(idx=i+1, start=wt[0]['start'], end=wt[-1]['end'], words=wt, eng=p['eng']))
# snap phrase boundaries to the nearest pause start when within 0.6s
for k in range(len(out)-1):
    e=out[k]['end']; best=min(pauses, key=lambda pz: abs(pz[0]-e))
    if abs(best[0]-e)<0.6:
        out[k]['end']=round(best[0],2); out[k+1]['start']=round(best[1],2)
        out[k]['words'][-1]['end']=out[k]['end']; out[k+1]['words'][0]['start']=out[k+1]['start']
json.dump(out, open(f'{S}/timing27.json','w'), ensure_ascii=False, indent=1)
with open(f'{S}/timing27.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['phrase','start','end','syllabary','phonetic','english'])
    for p in out: w.writerow([p['idx'],p['start'],p['end'],' '.join(x['syl'] for x in p['words']),' '.join(x['pho'] for x in p['words']),p['eng']])
for p in out: print(p['idx'], p['start'], p['end'], p['eng'])
print('chunks', len(chunks), 'speech s', round(speech,1), 'syllables', total)
