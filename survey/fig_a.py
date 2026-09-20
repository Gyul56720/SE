import sys; sys.path.insert(0,'/home/user/survey')
from figs import *
F = {}

# ---- Fig 1: taxonomy
b = box(20,14,300,26,"Industrial HLS C++ IP corpus  (25 files, 11,917 lines)",fs=12)
b += line(170,40,170,56)
xs=[(20,"AMD Vitis Solver","4 files / 3,598 ln","Apache-2.0"),
    (130,"AMD Vitis Security","4 files / 1,966 ln","Apache-2.0"),
    (240,"Xilinx FINN-hlslib","16 files / 6,528 ln","BSD-3-Clause")]
b += line(40,56,300,56)
for x,n,c,l in xs:
    cx=x+50
    b += line(cx,56,cx,70)+box(x,70,100,42,n,c,fs=9.5)
    b += txt(cx,126,l,8,"middle",'fill="#444"')
leaf={20:["cholesky.hpp","qrf.hpp","svd.hpp","potrf.hpp"],
      130:["aes.hpp","sha224_256.hpp","types.hpp","utils.hpp"],
      240:["mvau / vvau","slidingwindow","streamtools","+12 more"]}
for x,items in leaf.items():
    for i,s in enumerate(items):
        b += txt(x+50,142+i*12,s,8,"middle",family=MONO)
F[1]=(svg(340,200,b),"Taxonomy of the analysed corpus. Three independently maintained IP families, two licences.")

# ---- Fig 2: Cholesky ARCH 0/1/2
b=""
rows=[("ARCH 0","choleskyBasic","packed 1-D L","II = INNER_II","lowest area / highest latency"),
      ("ARCH 1","choleskyAlt","packed 1-D L + reciprocal diag","II = INNER_II","address arithmetic per iteration"),
      ("ARCH 2","choleskyAlt2","full 2-D L + partial-sum arrays","II=1 + UNROLL","ARRAY_PARTITION cyclic required")]
for i,(a,f,m,ii,note) in enumerate(rows):
    y=16+i*56
    b+=box(14,y,52,40,a,fs=11,fill="#f2f2f2")
    b+=box(74,y,86,40,f,fs=9)
    b+=box(168,y,120,40,m,fs=8.5)
    b+=box(296,y,86,40,ii,fs=8.5)
    b+=txt(392,y+24,note,8.5)
    b+=arr(66,y+20,74,y+20)+arr(160,y+20,168,y+20)+arr(288,y+20,296,y+20)
b+=txt(14,190,"area → increases downward,   latency → decreases downward",9,style='font-style="italic"')
F[2]=(svg(600,205,b),"The three Cholesky architectures selected by CholeskyTraits::ARCH. Identical mathematics, three distinct circuits.")

# ---- Fig 3: packed vs 2-D memory
b=""
N=5; c=22
for i in range(N):
    for j in range(N):
        if j<=i:
            b+=f'<rect x="{20+j*c}" y="{30+i*c}" width="{c}" height="{c}" fill="#e8e8e8" stroke="#000" stroke-width="0.6"/>'
        else:
            b+=f'<rect x="{20+j*c}" y="{30+i*c}" width="{c}" height="{c}" fill="#fff" stroke="#bbb" stroke-width="0.5" stroke-dasharray="2 2"/>'
b+=txt(20+N*c/2,22,"logical L (lower triangular)",9,"middle")
b+=txt(20+N*c/2,30+N*c+14,"N² words if stored as 2-D",8.5,"middle",'fill="#444"')
x0=200
b+=txt(x0+60,22,"ARCH 0/1 : packed 1-D",9,"middle")
k=0
for i in range(N):
    for j in range(i+1):
        b+=f'<rect x="{x0+k*11}" y="{34}" width="11" height="18" fill="#e8e8e8" stroke="#000" stroke-width="0.5"/>'
        k+=1
b+=txt(x0,66,f"L_internal[(N²−N)/2] = {k} words",8.5)
b+=txt(x0,80,"index:  i_off = ((i−1)²−(i−1))/2 + (i−1)",8.5,family=MONO)
b+=txt(x0,94,"→ address arithmetic every iteration",8.5,'fill="#444"' and "",'font-style="italic"')
b+=txt(x0+60,120,"ARCH 2 : plain 2-D",9,"middle")
for i in range(N):
    for j in range(N):
        b+=f'<rect x="{x0+j*11}" y="{130+i*11}" width="11" height="11" fill="{"#e8e8e8" if j<=i else "#fafafa"}" stroke="#000" stroke-width="0.4"/>'
b+=txt(x0+70,150,"N² words, no index math",8.5)
b+=txt(x0+70,163,"→ II is no longer address-bound",8.5,style='font-style="italic"')
F[3]=(svg(420,200,b),"Memory organisation trade-off in cholesky.hpp. ARCH 2 spends 2x memory to remove the per-iteration address computation that limits the initiation interval.")

# ---- Fig 4: ARCH2 column sweep
b=""
b+=box(16,20,90,30,"A[j][j]","diagonal read",fs=9)
b+=box(16,64,90,30,"square_sum_array[j]",None,fs=8)
b+=arr(106,35,140,35)+arr(106,79,140,60)
b+=box(140,20,96,46,"sqrt / rsqrt","reciprocal stored",fs=9)
b+=arr(236,43,272,43)
b+=box(272,20,96,46,"diag_internal[j]","1/L[j][j]",fs=9)
b+=txt(320,80,"division replaced by multiply",8.5,"middle",'font-style="italic"')
b+=box(40,118,300,58,"",fs=9)
b+=txt(50,134,"row_loop i = 0 .. N−1   (UNROLL FACTOR)",9,family=MONO)
b+=txt(50,150,"prod = L_internal[i][j] × conj(diag_internal[j])",8.5,family=MONO)
b+=txt(50,166,"product_sum_array[i] += prod ;  square_sum_array[i] += |prod|²",8.5,family=MONO)
b+=arr(190,66,190,118)
b+=txt(196,96,"per-column broadcast",8.5)
b+=box(378,118,120,58,"ARRAY_PARTITION","cyclic, factor = UNROLL_FACTOR",fs=8.5,fill="#f2f2f2")
b+=arr(370,147,378,147)
b+=txt(438,190,"banking is what makes UNROLL legal",8.5,"middle",'font-style="italic"')
F[4]=(svg(520,205,b),"choleskyAlt2 dataflow. Partial sums for every row are carried in arrays and updated during one column sweep; cyclic partitioning provides the simultaneous ports the unrolled loop needs.")

# ---- Fig 5: QRF Givens
b=""
b+=txt(120,16,"Givens rotation annihilates one sub-diagonal element",9,"middle",'font-style="italic"')
for i in range(4):
    for j in range(4):
        fill="#e8e8e8" if j>=i else ("#fff" if (i,j)!=(3,0) else "#bbb")
        b+=f'<rect x="{20+j*26}" y="{26+i*26}" width="26" height="26" fill="{fill}" stroke="#000" stroke-width="0.6"/>'
b+=txt(33,45,"r",9,"middle")
b+=txt(33,123,"x",9,"middle")
b+=arr(130,70,170,70)
b+=box(170,54,90,32,"qrf_givens()","c, s, r",fs=9)
b+=arr(260,70,300,70)
for i in range(4):
    for j in range(4):
        fill="#e8e8e8" if j>=i else "#fff"
        b+=f'<rect x="{300+j*26}" y="{26+i*26}" width="26" height="26" fill="{fill}" stroke="#000" stroke-width="0.6"/>'
b+=txt(313,123,"0",9,"middle")
b+=txt(160,148,"Gᵀ · A  applied to two rows at a time;  qrf_mm() is the 2×2 product",9,"middle")
b+=txt(160,162,"extra_pass / use_mag arguments select the magnitude-only variant",9,"middle",'fill="#444"')
F[5]=(svg(440,175,b),"Givens-rotation QR in qrf.hpp. Each rotation zeroes one element; qrf_mm applies the 2x2 rotation to a row pair.")

# ---- Fig 6: SVD Jacobi
b=""
b+=txt(150,16,"two-sided Jacobi: sweep over index pairs (p,q)",9,"middle",'font-style="italic"')
b+=box(16,28,86,40,"calc_angle()","cₗ, sₗ, cᵣ, sᵣ",fs=9)
b+=arr(102,48,140,48)
b+=box(140,28,96,40,"rotate rows p,q",None,fs=9)
b+=arr(236,48,274,48)
b+=box(274,28,96,40,"rotate cols p,q",None,fs=9)
b+=poly([(322,68),(322,92),(59,92),(59,68)])
b+=txt(190,106,"repeat until off-diagonal norm < tol  —  trip count is data dependent",9,"middle")
b+=box(96,118,190,34,"#pragma HLS loop_tripcount","tool cannot know the bound",fs=8.5,fill="#f2f2f2")
b+=txt(190,166,"svdBasic : one pair at a time      svdPairs : independent pairs in parallel",8.5,"middle")
F[6]=(svg(400,180,b),"Two-sided Jacobi SVD in svd.hpp. The iteration count depends on the data, which is why loop_tripcount appears; svdPairs exploits that disjoint index pairs commute.")

import json
json.dump({str(k):{"svg":v[0],"cap":v[1]} for k,v in F.items()}, open("figs_a.json","w"))
print("figures", sorted(F))
