import json
S='/home/claude/Cherokee-Books/spearfinger'
P=[470,365]   # where the arrow strikes the palm
pieces={
 "arrow_hit": {"ids":[6515,6533,12041,12109,5459],"cut":[136,34,492,362]},
 "arrow_a": {"ids":[4563,5255],"cut":[303,0,397,159]},
 "arrow_b": {"ids":[4576,5259],"cut":[0,83,117,174]},
 "splash": {"ids":[6183,6207],"cut":[360,334,476,446]},
}
drops={
 "drop_a": ({"ids":[3794]},[455,293]),
 "drop_b": ({"ids":[6172]},[236,337]),
 "drop_c": ({"ids":[6205]},[489,382]),
 "drop_d": ({"ids":[786,11751],"cut":[536,435,562,481]},[549,458]),
 "drop_e": ({"ids":[11856,11751],"cut":[611,436,676,558]},[643,497]),
 "drop_f": ({"ids":[786,6207],"cut":[282,457,354,559]},[318,508]),
 "drop_g": ({"ids":[786],"cut":[162,563,195,609]},[178,586]),
 "drop_h": ({"ids":[786],"cut":[274,744,294,787]},[284,765]),
}
HIT="p5w3"
def fly(dx,dy,at,dur,ease="linear"):
    return [{"type":"move","at":0,"dur":0,"dx":-dx,"dy":-dy},{"type":"hide","at":at},
            {"type":"move","at":at,"dur":dur,"dx":dx,"dy":dy,"ease":ease}]
motions={
 # the striking arrow slides in along its own line (fletch 160,60 -> head 480,350)
 "arrow_hit": fly(220,199,HIT+"-0.4",0.4),
 "arrow_a": fly(150,260,"p5w2+0.6",0.45),
 "arrow_b": fly(250,135,"p5w2+1.2",0.45),
 "splash": [{"type":"hide","at":HIT}],
}
for k,(sel,c) in drops.items():
    pieces[k]=sel
    f=0.65; dx=round((c[0]-P[0])*f); dy=round((c[1]-P[1])*f)
    i=list(drops).index(k)
    motions[k]=fly(dx,dy,HIT+"+%.2f"%(0.02+0.04*i),0.35,"out")
cfg={"beat":"On 'an arrow struck her soft palm' the arrow slides in along its line and strikes her raised palm; blood splashes out from the hand in drops (two other arrows fly past just before).",
 "pieces":pieces,
 "depth":{k:1.0 for k in pieces},
 "camera":{"zoom":[1.0,1.05],"focus":[0.38,0.35]},
 "motions":motions}
json.dump(cfg,open(f'{S}/pages/26.json','w'),indent=1)
