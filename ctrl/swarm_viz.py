#!/usr/bin/env python3
# 편대 위협회피 동적 HTML 뷰 -- tactical.py 가 실제로 시뮬한 궤적을 Canvas 애니메이션으로.
#
# viz.py 가 단일 드론 검사 3D(Three.js)를 내듯, 여기는 N대 편대의 전술 스택
# (계획->MPC->편대수행)을 2D 캔버스 애니메이션으로 낸다. 정지 이미지가 아니라
# requestAnimationFrame 루프로 편대가 움직이고, 세 계획(중심만/편대폭/폭+실행마진)을
# 토글해 바깥 드론이 위협을 관통하는지 전원 회피하는지 눈으로 비교한다.
#
# 수치는 지어내지 않는다 -- ctrl.model.tactical 이 실제로 돌린 궤적·여유다.
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from ctrl.model import tactical as T

_템플릿 = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>편대 위협회피</title>
<style>
  :root{--bg:#0e1116;--fg:#e6edf3;--muted:#9aa7b4;--acc:#4aa8ff;--red:#ff5a5a;--grid:#1c232d;--panel:#161b22;}
  @media (prefers-color-scheme:light){:root:not([data-theme=dark]){--bg:#f6f8fa;--fg:#1f2328;--muted:#57606a;--acc:#0969da;--red:#cf222e;--grid:#e5e9ef;--panel:#fff;}}
  *{box-sizing:border-box} html,body{margin:0}
  body{background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;padding:12px 16px}
  h1{font-size:16px;margin:.2em 0 .1em} .sub{color:var(--muted);font-size:12px;margin-bottom:10px}
  .wrap{max-width:900px;margin:0 auto}
  canvas{width:100%;height:auto;background:var(--panel);border-radius:10px;display:block;border:1px solid var(--grid)}
  .row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:10px 0}
  button{background:var(--panel);color:var(--fg);border:1px solid var(--grid);border-radius:8px;padding:6px 12px;cursor:pointer;font-size:13px}
  button.on{border-color:var(--acc);color:var(--acc)}
  .stat{font-variant-numeric:tabular-nums} .ok{color:var(--acc)} .bad{color:var(--red)}
  input[type=range]{flex:1;min-width:120px}
</style></head>
<body><div class="wrap">
<h1>무인체계 편대 위협회피 — 계획 → MPC → 편대수행</h1>
<div class="sub">5대 V편대가 바람 속에서 MPC 중심궤적을 따라 위협원을 회피. 계획 마진을 바꿔 비교 — 바깥 드론이 위협에 닿으면 <b class="bad">빨강</b>.</div>
<div class="row" id="cases"></div>
<canvas id="cv" width="900" height="420"></canvas>
<div class="row">
  <button id="play">⏸ 멈춤</button>
  <button id="speed">속도 1×</button>
  <input type="range" id="scrub" min="0" max="100" value="0">
  <span class="stat" id="read"></span>
</div>
<div class="sub" id="verdict"></div>
</div>
<script>
const D = /*__DATA__*/null;
const cv=document.getElementById('cv'), ctx=cv.getContext('2d');
let ci=D.cases.length-1, tf=0, playing=true, speed=1;
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
let minx=-1,maxx=13,minz=-3,maxz=6;
function W2S(p){const w=cv.width,h=cv.height,pad=28;
  const sx=(w-2*pad)/(maxx-minx), sz=(h-2*pad)/(maxz-minz), s=Math.min(sx,sz);
  return [pad+(p[0]-minx)*s, h-pad-(p[1]-minz)*s];}
function dist(a,b){return Math.hypot(a[0]-b[0],a[1]-b[1]);}
const palette=['#4aa8ff','#5ad1a0','#f0c14a','#c98bff','#ff9e64'];
function draw(){
  const w=cv.width,h=cv.height; ctx.clearRect(0,0,w,h);
  const c=D.cases[ci]; const frames=c.traj; const N=D.N;
  const ti=Math.min(Math.floor(tf), frames.length-1);
  const tc=W2S(D.threat.c); const rpx=dist(W2S([D.threat.c[0]+D.threat.R,D.threat.c[1]]),tc);
  ctx.beginPath();ctx.arc(tc[0],tc[1],rpx,0,7);ctx.fillStyle='rgba(255,90,90,.16)';ctx.fill();
  ctx.strokeStyle=css('--red');ctx.setLineDash([6,5]);ctx.lineWidth=1.4;ctx.stroke();ctx.setLineDash([]);
  ctx.fillStyle=css('--red');ctx.font='12px sans-serif';ctx.fillText('위협',tc[0]-12,tc[1]-rpx-6);
  ctx.beginPath();c.center.forEach((p,i)=>{const s=W2S(p);i?ctx.lineTo(s[0],s[1]):ctx.moveTo(s[0],s[1]);});
  ctx.strokeStyle=css('--muted');ctx.globalAlpha=.5;ctx.lineWidth=1;ctx.stroke();ctx.globalAlpha=1;
  for(let i=0;i<N;i++){ctx.beginPath();for(let k=0;k<=ti;k++){const s=W2S(frames[k][i]);k?ctx.lineTo(s[0],s[1]):ctx.moveTo(s[0],s[1]);}
    ctx.strokeStyle=palette[i%palette.length];ctx.globalAlpha=.35;ctx.lineWidth=1;ctx.stroke();ctx.globalAlpha=1;}
  const fr=frames[ti];
  ctx.strokeStyle=css('--grid');ctx.lineWidth=1.2;
  for(let i=1;i<N;i++){const a=W2S(fr[0]),b=W2S(fr[i]);ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();}
  for(let i=0;i<N;i++){const s=W2S(fr[i]);const hit=dist(fr[i],D.threat.c)<D.threat.R;
    ctx.beginPath();ctx.arc(s[0],s[1],i===0?7:5,0,7);
    ctx.fillStyle=hit?css('--red'):palette[i%palette.length];ctx.fill();
    if(i===0){ctx.strokeStyle=css('--fg');ctx.lineWidth=1.5;ctx.stroke();}}
  const st=W2S(D.start),gl=W2S(D.goal);
  ctx.fillStyle='#5ad1a0';ctx.beginPath();ctx.arc(st[0],st[1],5,0,7);ctx.fill();
  ctx.fillStyle='#5ad1a0';ctx.font='16px sans-serif';ctx.fillText('★',gl[0]-6,gl[1]+5);
  document.getElementById('read').innerHTML=`t=${ti}  최악여유 <b class="${c.clr<0?'bad':'ok'}">${c.clr>0?'+':''}${c.clr}m</b>  ·  편대유지 ${c.fe}m`;
}
function loop(){if(playing){tf+=0.7*speed;if(tf>=D.cases[ci].traj.length)tf=0;
  document.getElementById('scrub').value=100*tf/D.cases[ci].traj.length;draw();}requestAnimationFrame(loop);}
function buildCases(){const box=document.getElementById('cases');box.innerHTML='';
  D.cases.forEach((c,i)=>{const b=document.createElement('button');b.textContent=`${c.name} (Rplan ${c.Rplan})`;
    b.className=i===ci?'on':'';b.onclick=()=>{ci=i;tf=0;buildCases();updateVerdict();};box.appendChild(b);});}
function updateVerdict(){const c=D.cases[ci];
  document.getElementById('verdict').innerHTML = c.clr<0
    ? `<b class="bad">✗ 바깥 드론이 위협을 ${(-c.clr).toFixed(2)}m 관통.</b> 계획이 편대 폭·실행오차를 덜 반영함.`
    : `<b class="ok">✓ 전원 회피(여유 +${c.clr}m).</b> 필요 마진 = 위협반경 + 편대 반폭 + 실행오차(바람+유지).`;}
document.getElementById('play').onclick=e=>{playing=!playing;e.target.textContent=playing?'⏸ 멈춤':'▶ 재생';};
document.getElementById('speed').onclick=e=>{speed=speed>=4?0.5:speed*2;e.target.textContent='속도 '+speed+'×';};
document.getElementById('scrub').oninput=e=>{tf=D.cases[ci].traj.length*e.target.value/100;playing=false;
  document.getElementById('play').textContent='▶ 재생';draw();};
buildCases();updateVerdict();loop();
</script></body></html>"""


def 페이로드(start=(0, 0), goal=(12, 0), threat_c=(6, 0), R=2.0, stride=2):
    """세 계획(중심만/편대폭/폭+실행마진)의 실제 시뮬 궤적을 담은 dict."""
    offsets = T.편대오프셋_V()
    half_w = float(np.abs(offsets[:, 1]).max())
    cases = [("중심만", R), ("편대폭", R + half_w), ("폭+실행마진", R + half_w + 0.8)]
    out = []
    for name, Rplan in cases:
        wps = T.계획(start, goal, threat_c, Rplan)
        C = T.mpc_중심궤적(wps, goal)
        traj, fe = T.편대수행(C, offsets)
        clr = T.최악_위협여유(traj, threat_c, R)
        out.append({
            "name": name, "Rplan": round(float(Rplan), 2),
            "fe": round(fe, 3), "clr": round(clr, 3),
            "center": [[round(float(p[0]), 3), round(float(p[1]), 3)] for p in C[::stride]],
            "traj": [[[round(float(x), 3), round(float(z), 3)] for x, z in frame]
                     for frame in traj[::stride]],
        })
    return {"threat": {"c": list(threat_c), "R": R},
            "start": list(start), "goal": list(goal), "N": len(offsets), "cases": out}


def 만들기(out_html: str, **kw):
    """편대 애니메이션 HTML 을 out_html 에 쓴다. (경로, 요약dict) 반환."""
    p = 페이로드(**kw)
    html = _템플릿.replace("/*__DATA__*/null", json.dumps(p, ensure_ascii=False))
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)
    요약 = {c["name"]: {"Rplan": c["Rplan"], "fe": c["fe"], "clr": c["clr"]} for c in p["cases"]}
    return out_html, 요약


if __name__ == "__main__":
    import tempfile, os
    h = os.path.join(tempfile.mkdtemp(), "편대.html")
    _, 요약 = 만들기(h)
    print("HTML:", h)
    for k, v in 요약.items():
        print(f"  {k:10} Rplan={v['Rplan']} 유지={v['fe']} 최악여유={v['clr']}")
