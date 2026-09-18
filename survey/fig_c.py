import sys, json; sys.path.insert(0,'/home/user/survey')
from figs import *
F={}

# Fig 13: SHA-256
b=txt(230,14,"SHA-224/256 compression: schedule and round function are separate dataflow stages",8.5,"middle",'font-style="italic"')
b+=box(10,26,90,34,"message pad","512-bit blocks",fs=8.5)
b+=arr(100,43,124,43)
b+=box(124,26,96,34,"W[0..63] schedule","σ0/σ1 recurrence",fs=8.5)
b+=arr(220,43,244,43)
b+=box(244,26,96,34,"64 rounds","a..h working regs",fs=8.5)
b+=arr(340,43,364,43)
b+=box(364,26,90,34,"H += a..h","digest update",fs=8.5)
b+=poly([(409,60),(409,82),(292,82),(292,60)])
b+=txt(350,96,"per block",8.5,"middle",'font-style="italic"')
b+=box(124,102,216,30,"hls::stream between stages → schedule and rounds overlap",fs=8.5,fill="#f2f2f2")
b+=txt(10,150,"53 HLS pragmas in 854 lines — the densest pragma ratio in the corpus",8.5)
F[13]=(svg(470,160,b),"Structure of sha224_256.hpp. Message expansion and the round loop are separate stream-connected stages so that they execute concurrently.")

# Fig 14: array partitioning
b=txt(210,14,"why UNROLL needs ARRAY_PARTITION",9,"middle",'font-style="italic"')
b+=txt(20,34,"(a) single memory: 2 ports",8.5)
for i in range(8):
    b+=f'<rect x="{20+i*20}" y="42" width="20" height="20" fill="#eee" stroke="#000" stroke-width="0.5"/>'
    b+=txt(30+i*20,56,str(i),8,"middle")
b+=box(60,72,80,20,"2 ports only",fs=8)
b+=txt(20,108,"4 parallel accesses → serialised, II = 4",8.5,style='fill="#000"')
b+=txt(240,34,"(b) cyclic, factor = 4",8.5)
for k in range(4):
    for i in range(2):
        idx=k+i*4
        b+=f'<rect x="{240+k*44+i*20}" y="42" width="20" height="20" fill="#dcdcdc" stroke="#000" stroke-width="0.5"/>'
        b+=txt(250+k*44+i*20,56,str(idx),8,"middle")
    b+=f'<rect x="{238+k*44}" y="40" width="44" height="24" fill="none" stroke="#000" stroke-width="1.3"/>'
    b+=txt(260+k*44,76,f"bank {k}",7.5,"middle")
b+=txt(240,108,"4 banks × 2 ports → 4 accesses/cycle, II = 1",8.5)
b+=txt(20,130,"cyclic  : a[i] → bank (i mod factor)      block : contiguous chunks      complete : every element a register",8.5,family=MONO)
F[14]=(svg(430,142,b),"Array partitioning. Unrolling is legal only when the memory can deliver the required number of accesses per cycle; cyclic partitioning is used when the access stride is one.")

# Fig 15: pragma bar chart from real data
inv=json.load(open("/home/user/survey/inventory.json"))
agg={}
for f in inv["files"]:
    for k,v in f["pragmas"].items(): agg[k]=agg.get(k,0)+v
items=sorted(agg.items(), key=lambda kv:-kv[1])[:14]
mx=items[0][1]; W=250
b=txt(200,14,"HLS pragma frequency across 11,917 lines",9,"middle",'font-style="italic"')
for i,(k,v) in enumerate(items):
    y=26+i*15
    b+=txt(118,y+9,k,8,"end",family=MONO)
    w=W*v/mx
    b+=f'<rect x="124" y="{y}" width="{w:.1f}" height="11" fill="#c9c9c9" stroke="#000" stroke-width="0.5"/>'
    b+=txt(128+w,y+9,str(v),8)
F[15]=(svg(400,26+len(items)*15+10,b),"Measured pragma frequency over the whole corpus. PIPELINE, INLINE, UNROLL and ARRAY_PARTITION dominate; DEPENDENCE and LOOP_TRIPCOUNT mark the places where the tool must be told something it cannot infer.")

# Fig 16: streamtools width conversion
b=txt(220,14,"stream width conversion (streamtools.h)",9,"middle",'font-style="italic"')
for i in range(3):
    b+=f'<rect x="{20+i*34}" y="30" width="34" height="22" fill="#dcdcdc" stroke="#000" stroke-width="0.6"/>'
b+=txt(54,68,"IN_WIDTH = 32",8.5,"middle",family=MONO)
b+=arr(126,41,158,41)
b+=box(158,26,92,30,"DWC","ratio = IN/OUT",fs=9)
b+=arr(250,41,282,41)
for i in range(6):
    b+=f'<rect x="{282+i*17}" y="30" width="17" height="22" fill="#eee" stroke="#000" stroke-width="0.6"/>'
b+=txt(333,68,"OUT_WIDTH = 16",8.5,"middle",family=MONO)
b+=txt(20,92,"also in this file: padding, cropping, duplication, limiting, FIFO insertion,",8.5)
b+=txt(20,105,"and lane interleaving — 23 functions in 1,008 lines, all hls::stream to hls::stream",8.5)
F[16]=(svg(420,118,b),"Stream utilities. Width conversion decouples the natural word size of neighbouring stages so that each can be folded independently.")

# Fig 17: thresholding activation
b=txt(210,14,"multi-threshold activation replaces multiply-accumulate scaling",8.5,"middle",'font-style="italic"')
b+=box(16,28,84,32,"accu (wide)",None,fs=9)
b+=arr(100,44,132,44)
b+=box(132,24,110,40,"compare against","T[0] < T[1] < ... < T[n]",fs=8.5)
b+=arr(242,44,274,44)
b+=box(274,28,90,32,"index  (log₂ n bits)",None,fs=8.5)
b+=txt(16,84,"Thresholding<...>::activate(nf, pe, accu)  — activations.hpp, 19 class definitions",8.5,family=MONO)
b+=box(16,94,348,26,"quantised activation becomes a comparator tree: no multiplier, no dequantise step",fs=8.5,fill="#f2f2f2")
F[17]=(svg(380,130,b),"Threshold-based activation in activations.hpp. For quantised networks the activation and re-quantisation collapse into a single comparator tree.")

# Fig 18: TMR
b=txt(190,14,"tmrcheck.hpp — triple modular redundancy with error flag",8.5,"middle",'font-style="italic"')
for i in range(3):
    b+=box(16,26+i*34,80,26,f"replica {i}",fs=9)
    b+=arr(96,39+i*34,132,73)
b+=box(132,58,76,30,"majority","2-of-3 vote",fs=8.5)
b+=arr(208,73,244,73)
b+=box(244,58,76,30,"output",fs=9)
b+=arr(170,88,170,114)
b+=box(120,114,100,26,"error flag",fs=8.5,fill="#f2f2f2")
b+=txt(330,60,"safety / radiation",8.5)
b+=txt(330,74,"hardened deployments",8.5)
b+=txt(330,88,"cost: 3× area",8.5)
F[18]=(svg(430,150,b),"Triple modular redundancy in tmrcheck.hpp: the corpus ships a fault-tolerance option as an ordinary library component.")

# Fig 19: unified pattern
b=txt(250,14,"the pattern common to all three families",9,"middle",'font-style="italic"')
rows=[("1","parameterise","template args or a Traits struct carrying internal types AND architecture switches"),
      ("2","separate state","one entry point that prepares reusable state, another that streams data"),
      ("3","fold","fixed hardware = P×Q; problem size maps to cycles, not area"),
      ("4","flatten","merge nested loops into one iteration space so the pipeline never drains"),
      ("5","bank","partition every array the unrolled loop touches, cyclically along the access stride"),
      ("6","remove division","store reciprocals; replace / by × and >> "),
      ("7","report failure","return a status code the caller can act on"),
      ("8","separate debug","guard printf and assertions with #ifndef __SYNTHESIS__")]
for i,(n,k,v) in enumerate(rows):
    y=26+i*21
    b+=box(16,y,20,17,n,fs=9,fill="#eee")
    b+=txt(44,y+12,k,9,style='font-weight="bold"')
    b+=txt(132,y+12,v,8.5)
F[19]=(svg(560,26+len(rows)*21+8,b),"The eight recurring design moves observed in every family of the corpus, independent of application domain.")

json.dump({str(k):{"svg":v[0],"cap":v[1]} for k,v in F.items()}, open("figs_c.json","w"))
print("figures", sorted(F))
