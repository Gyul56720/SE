import sys, json; sys.path.insert(0,'/home/user/survey')
from figs import *
F={}

# Fig 7: MVAU folding
b=txt(230,14,"weight matrix  MatrixH × MatrixW",9,"middle",'font-style="italic"')
R,C,cw,ch=6,8,26,18
for i in range(R):
    for j in range(C):
        pe,sf=i//2,j//4
        sh="#d9d9d9" if (pe+sf)%2==0 else "#f0f0f0"
        b+=f'<rect x="{30+j*cw}" y="{24+i*ch}" width="{cw}" height="{ch}" fill="{sh}" stroke="#000" stroke-width="0.4"/>'
for i in range(0,R+1,2):
    b+=line(30,24+i*ch,30+C*cw,24+i*ch,w=1.4)
for j in range(0,C+1,4):
    b+=line(30+j*cw,24,30+j*cw,24+R*ch,w=1.4)
b+=txt(20,24+R*ch/2,"PE",9,"end")
b+=line(14,24,14,24+2*ch,w=1.0)+line(11,24,17,24)+line(11,24+2*ch,17,24+2*ch)
b+=txt(30+2*cw,24+R*ch+14,"SIMD",9,"middle")
b+=line(30,24+R*ch+4,30+4*cw,24+R*ch+4)+line(30,24+R*ch+1,30,24+R*ch+7)+line(30+4*cw,24+R*ch+1,30+4*cw,24+R*ch+7)
b+=txt(250,60,"NF = MatrixH / PE   = 3 vertical folds",9,family=MONO)
b+=txt(250,76,"SF = MatrixW / SIMD = 2 horizontal folds",9,family=MONO)
b+=txt(250,92,"TOTAL_FOLD = NF × SF = 6 cycles",9,family=MONO)
b+=box(250,104,190,38,"hardware = SIMD × PE MACs","matrix size changes cycles, not area",fs=9,fill="#f2f2f2")
F[7]=(svg(460,170,b),"Folding in mvau.hpp. Physical MAC resources are fixed at SIMD x PE; a larger matrix costs more cycles, never more area.")

# Fig 8: loop flattening
b=txt(150,14,"(a) nested loops — pipeline drains at every outer boundary",9,"middle")
x=20
for blk in range(3):
    for k in range(6):
        b+=f'<rect x="{x}" y="{24}" width="10" height="14" fill="#d9d9d9" stroke="#000" stroke-width="0.4"/>'; x+=10
    for k in range(3):
        b+=f'<rect x="{x}" y="{24}" width="10" height="14" fill="none" stroke="#999" stroke-width="0.5" stroke-dasharray="2 2"/>'; x+=10
b+=txt(x+6,35,"drain bubbles",8.5,"start",'font-style="italic"')
b+=txt(150,64,"(b) merged iteration space — II = 1 throughout",9,"middle")
x=20
for k in range(27):
    b+=f'<rect x="{x}" y="{74}" width="10" height="14" fill="#d9d9d9" stroke="#000" stroke-width="0.4"/>'; x+=10
b+=txt(20,106,"for (i = 0; i < reps*NF*SF; i++) {  #pragma HLS pipeline II=1",8.5,family=MONO)
b+=txt(20,120,"   ... ; if (++sf == SF) { sf = 0; ++nf; }   // counters kept by hand",8.5,family=MONO)
b+=box(20,130,270,26,'“to get the pipelining the way we want”  — source comment',fs=8.5,fill="#f2f2f2")
F[8]=(svg(300,165,b),"Loop flattening. FINN merges the nested fold loops into one iteration space and maintains sf/nf/tile manually so the pipeline never drains.")

# Fig 9: sliding window
b=txt(200,14,"line buffer feeding a K×K convolution window",9,"middle",'font-style="italic"')
for r in range(3):
    for c in range(12):
        f="#d9d9d9" if (r<3 and 2<=c<=4) else "#f6f6f6"
        b+=f'<rect x="{20+c*22}" y="{24+r*18}" width="22" height="18" fill="{f}" stroke="#000" stroke-width="0.4"/>'
b+=f'<rect x="{20+2*22}" y="24" width="66" height="54" fill="none" stroke="#000" stroke-width="1.8"/>'
b+=txt(20+3*22+11,92,"K×K window",8.5,"middle")
b+=txt(290,34,"IFMDim × IFMChannels input stream",8.5)
b+=txt(290,50,"K² · SIMD values presented per cycle",8.5)
b+=txt(290,66,"buffer depth = (K−1)·IFMDim + K",8.5,family=MONO)
b+=box(290,76,190,34,"#pragma HLS RESOURCE / BIND_STORAGE","BRAM vs LUTRAM vs URAM selected here",fs=8,fill="#f2f2f2")
b+=arr(20+12*22,50,286,50)
F[9]=(svg(500,120,b),"slidingwindow.h (2,095 lines, the largest file). A line buffer converts a raster stream into overlapping windows; the storage pragma chooses the memory primitive.")

# Fig 10: FINN streaming chain
b=""
st=[("DMA","dma.h"),("Slide","slidingwindow.h"),("MVAU","mvau.hpp"),
    ("Act","activations.hpp"),("MaxPool","maxpool.h"),("Width","streamtools.h")]
x=10
for n,f in st:
    b+=box(x,30,72,38,n,f,fs=9.5)
    if x>10: b+=arr(x-12,49,x-2,49)
    x+=84
b+=txt(260,16,"every stage communicates only through hls::stream<>  (250 uses)",9,"middle",'font-style="italic"')
b+=txt(260,84,"DATAFLOW composition: stages run concurrently, back-pressure is implicit",9,"middle")
b+=box(150,94,220,26,"no shared arrays → no false dependences → II=1 per stage",fs=8.5,fill="#f2f2f2")
F[10]=(svg(520,130,b),"FINN composes an accelerator as a chain of stream-connected stages; the stream abstraction is what makes concurrent scheduling and back-pressure automatic.")

# Fig 11: AES round
b=txt(230,14,"one AES round on a 128-bit state register",9,"middle",'font-style="italic"')
b+=box(10,28,74,34,"SubBytes","16× S-box",fs=9)
b+=arr(84,45,104,45)
b+=box(104,28,74,34,"ShiftRows","wiring only",fs=9,fill="#f2f2f2")
b+=arr(178,45,198,45)
b+=box(198,28,80,34,"MixColumns","GFMul2/3",fs=9)
b+=arr(278,45,298,45)
b+=box(298,28,84,34,"AddRoundKey","XOR key_list[r]",fs=9)
b+=poly([(340,62),(340,84),(47,84),(47,62)])
b+=txt(196,98,"round_counter = 1 .. 10   (MixColumns skipped on the last round)",9,"middle")
b+=txt(141,74,"0 gates — byte-slice assignments",8,"middle",'font-style="italic"')
b+=box(10,110,180,30,"#pragma HLS resource core=ROM_nP_LUTRAM","16 concurrent S-box reads",fs=8,fill="#f2f2f2")
b+=arr(47,110,47,66)
b+=box(210,110,172,30,"#pragma HLS unroll on the 16-byte loops",fs=8.5,fill="#f2f2f2")
F[11]=(svg(400,150,b),"AES round datapath in aes.hpp. ShiftRows costs no logic because ap_uint<128> bit-slice assignment is pure rewiring.")

# Fig 12: key expansion split
b=box(16,24,120,40,"updateKey(cipherkey)","runs once per key",fs=9)
b+=arr(136,44,176,44)
b+=box(176,24,110,40,"key_list[0..Nr]","registers / LUTRAM",fs=9,fill="#f2f2f2")
b+=arr(231,64,231,92)
b+=box(16,92,270,40,"process(plaintext, key, ciphertext)","runs once per 128-bit block",fs=9)
b+=txt(320,44,"amortised: key schedule is",9)
b+=txt(320,58,"not recomputed per block",9)
b+=txt(320,100,"PPA knob: unroll the 10-round",9)
b+=txt(320,114,"loop → ~10× area, ~10× rate",9)
F[12]=(svg(500,145,b),"State-reuse partitioning in aes.hpp: key expansion and block processing are separate entry points so the schedule is computed only when the key changes.")

json.dump({str(k):{"svg":v[0],"cap":v[1]} for k,v in F.items()}, open("figs_b.json","w"))
print("figures", sorted(F))
