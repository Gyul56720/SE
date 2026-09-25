#!/usr/bin/env python3
# sim 출력(json) -> 자체완결 인터랙티브 HTML 생성기.
#
# **나도 봇도 같은 도구를 쓴다.** 봇이 "검사 시뮬 HTML 만들어줘" 하면 이걸 돌려 파일 하나를
# 내고, discord_bot_server 가 그 파일을 채널에 올린다(bot_tools.마지막그림 경유). 데이터는
# HTML 에 박아 자체완결로 만든다 -- 파일 하나만 열면 된다.
#
# 씀:
#   python3 ctrl/viz.py 검사3d ctrl/model/검사3d.json out.html
#   (첫 인자 = 템플릿 종류; 지금은 '검사3d'(항공기 결함검사 드론) 하나)
import sys, json, pathlib

TEMPLATES = {"검사3d": "항공기 결함검사 드론"}


def 만들기(종류: str, 데이터경로: str, 출력경로: str) -> str:
    if 종류 not in TEMPLATES:
        raise SystemExit(f"모르는 종류: {종류} (있는 것: {list(TEMPLATES)})")
    data = json.loads(pathlib.Path(데이터경로).read_text(encoding="utf-8"))
    html = _검사3d_템플릿().replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    pathlib.Path(출력경로).write_text(html, encoding="utf-8")
    return 출력경로


def _검사3d_템플릿() -> str:
    return r"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>항공기 결함검사 드론</title>
<style>
:root{--bg:#0d1117;--panel:#161c26;--ink:#e7edf5;--muted:#93a1b5;--line:#26303f;
--primary:#5aa0e6;--accent:#e08a2c;--good:#43c088;--warn:#e0b13a;--bad:#e0605a;--sky:#0b1420;}
*{box-sizing:border-box}html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Noto Sans KR",system-ui,sans-serif;overflow:hidden}
#app{display:grid;grid-template-columns:1fr 300px;height:100%}
@media(max-width:720px){#app{grid-template-columns:1fr;grid-template-rows:1fr auto}}
.view{position:relative;background:radial-gradient(circle at 50% 30%,#12202e,#0a0f16)}
#cv{display:block;width:100%;height:100%;touch-action:none;cursor:grab}#cv:active{cursor:grabbing}
.top{position:absolute;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;
padding:10px 14px;background:linear-gradient(#0d1117cc,transparent);pointer-events:none}
.brand{font-weight:800;font-size:.92rem;letter-spacing:.02em}
.brand span{color:var(--accent)}
.status{font-size:.72rem;color:var(--good);font-weight:700;display:flex;align-items:center;gap:6px}
.status .led{width:8px;height:8px;border-radius:50%;background:var(--good);box-shadow:0 0 8px var(--good)}
.cams{position:absolute;top:44px;right:12px;display:flex;flex-direction:column;gap:5px}
.cams button{font:inherit;font-size:.72rem;font-weight:700;padding:6px 10px;border-radius:8px;border:1px solid var(--line);
background:#161c26cc;color:var(--ink);cursor:pointer;backdrop-filter:blur(6px)}
.cams button.on{background:var(--primary);color:#04101c;border-color:transparent}
.hud{position:absolute;left:12px;bottom:12px;background:#0d1117cc;border:1px solid var(--line);border-radius:10px;
padding:9px 12px;font-size:.74rem;font-variant-numeric:tabular-nums;backdrop-filter:blur(6px);min-width:150px}
.hud .r{display:flex;justify-content:space-between;gap:12px;padding:1px 0}.hud b{color:var(--primary)}
.feed{position:absolute;right:12px;bottom:12px;width:150px;height:110px;border:1px solid var(--line);border-radius:8px;
overflow:hidden;background:#04101c}
.feed canvas{width:100%;height:100%}
.feed .cap{position:absolute;top:4px;left:6px;font-size:.62rem;color:var(--bad);font-weight:700;text-shadow:0 1px 2px #000}
.feed .rec{position:absolute;top:5px;right:6px;width:7px;height:7px;border-radius:50%;background:var(--bad);animation:blink 1s infinite}
@keyframes blink{50%{opacity:.3}}
/* 패널 */
.panel{background:var(--panel);border-left:1px solid var(--line);display:flex;flex-direction:column;overflow-y:auto}
@media(max-width:720px){.panel{border-left:0;border-top:1px solid var(--line);max-height:44vh}}
.sec{padding:12px 14px;border-bottom:1px solid var(--line)}
.sec h3{margin:0 0 8px;font-size:.72rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.big{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.stat{background:#0d1117;border:1px solid var(--line);border-radius:9px;padding:8px 10px}
.stat .k{font-size:.66rem;color:var(--muted)}.stat .v{font-size:1.15rem;font-weight:800;font-variant-numeric:tabular-nums}
.stat .v.good{color:var(--good)}
.cov{height:8px;background:#0d1117;border-radius:99px;overflow:hidden;margin-top:6px}
.cov i{display:block;height:100%;background:linear-gradient(90deg,var(--primary),var(--good));width:0}
.def{display:flex;align-items:center;gap:9px;padding:8px 0;border-bottom:1px solid var(--line);opacity:.35;transition:opacity .4s}
.def:last-child{border-bottom:0}.def.on{opacity:1}
.def .ic{width:26px;height:26px;border-radius:7px;display:grid;place-items:center;font-size:.9rem;flex:0 0 auto}
.def .t{font-size:.82rem;font-weight:700}.def .s{font-size:.68rem;color:var(--muted)}
.sev{font-size:.62rem;font-weight:700;padding:.1em .5em;border-radius:99px;margin-left:auto}
.sev.높음{background:var(--bad);color:#fff}.sev.중간{background:var(--warn);color:#20160a}.sev.낮음{background:var(--muted);color:#0d1117}
.tel .r{display:flex;justify-content:space-between;font-size:.76rem;font-variant-numeric:tabular-nums;padding:2px 0}
.tel .lab{color:var(--muted)}
.ctrls{display:flex;gap:8px;align-items:center;padding:10px 14px}
.ctrls button{font:inherit;font-weight:700;border:0;border-radius:8px;padding:7px 12px;cursor:pointer}
.play{background:var(--primary);color:#04101c;min-width:52px}
.spd{background:#0d1117;color:var(--ink);border:1px solid var(--line)!important}
input[type=range]{flex:1;accent-color:var(--accent);min-width:70px}
.note{font-size:.66rem;color:var(--muted);padding:8px 14px;line-height:1.5}
.note code{background:#0d1117;color:var(--primary);padding:.05em .35em;border-radius:4px}
</style>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;800&display=swap">
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head><body>
<div id="app">
  <div class="view">
    <canvas id="cv"></canvas>
    <div class="top">
      <div class="brand">✈ AeroScan <span>· 드론 결함검사</span></div>
      <div class="status"><span class="led"></span><span id="st">SCANNING</span></div>
    </div>
    <div class="cams">
      <button id="c_orbit" class="on">궤도</button>
      <button id="c_follow">추적</button>
      <button id="c_drone">드론뷰</button>
    </div>
    <div class="hud">
      <div class="r"><span>비행시간</span><b id="ht">0.0s</b></div>
      <div class="r"><span>고도</span><b id="halt">0.0 m</b></div>
      <div class="r"><span>표면거리</span><b id="hsurf">— m</b></div>
      <div class="r"><span>웨이포인트</span><b id="hwp">0/0</b></div>
    </div>
    <div class="feed">
      <canvas id="feed"></canvas>
      <div class="cap" id="feedcap"></div><div class="rec"></div>
    </div>
  </div>
  <div class="panel">
    <div class="sec">
      <h3>검사 현황</h3>
      <div class="big">
        <div class="stat"><div class="k">커버리지</div><div class="v good" id="cov">0%</div></div>
        <div class="stat"><div class="k">결함 검출</div><div class="v" id="dc">0/0</div></div>
      </div>
      <div class="cov"><i id="covbar"></i></div>
    </div>
    <div class="sec">
      <h3>검출된 결함</h3>
      <div id="deflist"></div>
    </div>
    <div class="sec">
      <h3>물리 규격 검증</h3>
      <div class="tel">
        <div class="r"><span class="lab">GSD @표준거리</span><span id="sgsd">—</span></div>
        <div class="r"><span class="lab">스와스</span><span id="sswath">—</span></div>
        <div class="r"><span class="lab">표준거리 범위</span><span id="sstand">—</span></div>
      </div>
      <div id="veriflist" style="margin-top:8px"></div>
    </div>
    <div class="sec tel">
      <h3>제어 텔레메트리 (PI-SSM)</h3>
      <div class="r"><span class="lab">위치 X·Y·Z</span><span id="tp">0,0,0</span></div>
      <div class="r"><span class="lab">추종 오차</span><span id="te">0.00 m</span></div>
      <div class="r"><span class="lab">상태 h (‖적분‖)</span><span id="th">0.00</span></div>
      <div class="r"><span class="lab">속도</span><span id="tv">0.0 m/s</span></div>
    </div>
    <div class="ctrls">
      <button class="play" id="play">❚❚</button>
      <input type="range" id="scrub" min="0" value="0">
      <button class="spd" id="spd">1×</button>
    </div>
    <div class="note">드론 궤적은 <code>3축 PI-SSM</code> 제어 정책이 검사 경로를 추종한 실측.
    결함 표식은 근접검출 데모(실제 비전 아님). 이 재귀는 <code>ssm/scan_mac</code> 하드웨어가 처리.</div>
  </div>
</div>
<script>
const D=/*__DATA__*/null;
const css=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const AC=D.AC,P=D.p,H=D.h,WP=D.웨이포인트,DEF=D.결함,T=D.t,N=T.length,tmax=T[N-1];
const cv=document.getElementById("cv");
let renderer,scene,camera,drone,props=[],ac,pathLine,trailLine,shadow;
let feedR,feedS,feedC,feedCam;
let idx=0,playing=true,speed=1,last=performance.now(),cam="orbit";
let orbit={theta:0.7,phi:1.0,r:20,tgt:new THREE.Vector3(0,1,0)};
const V=a=>new THREE.Vector3(a[0],a[1],a[2]);
const col=v=>new THREE.Color(v);
const DEFSTATE=DEF.map(()=>false);

function build(){
  renderer=new THREE.WebGLRenderer({canvas:cv,antialias:true});renderer.setPixelRatio(Math.min(2,devicePixelRatio));
  renderer.setClearColor(0x000000,0);
  scene=new THREE.Scene();scene.fog=new THREE.Fog(0x0a0f16,26,60);
  camera=new THREE.PerspectiveCamera(50,2,0.1,200);
  scene.add(new THREE.AmbientLight(0xffffff,0.65));
  const d1=new THREE.DirectionalLight(0xbfd4ee,0.8);d1.position.set(8,16,10);scene.add(d1);
  const d2=new THREE.DirectionalLight(0x3a5878,0.4);d2.position.set(-10,4,-8);scene.add(d2);
  buildAircraft();buildGround();buildPath();buildDrone();buildFeed();
  document.getElementById("scrub").max=N-1;buildDefList();buildSpec();
  resize();update();loop();
}
function buildGround(){
  const g=new THREE.GridHelper(60,30,0x1b2836,0x141d28);g.position.y=-AC.동체반경-3.2;scene.add(g);
}
function buildAircraft(){
  ac=new THREE.Group();
  const skin=new THREE.MeshStandardMaterial({color:0xdfe6ee,metalness:.55,roughness:.42});
  const skin2=new THREE.MeshStandardMaterial({color:0xc6d0da,metalness:.5,roughness:.5});
  const L=AC.동체길이,R=AC.동체반경;
  // 날개·미익 치수는 그리기용 -- B737 비율로 동체에서 유도(물리 스키마엔 없음)
  const span=L*0.45, wx=-L*0.05, sw=L*0.15, vth=R*3.0;
  // 동체(x축)
  const fus=new THREE.Mesh(new THREE.CylinderGeometry(R,R,L,32),skin);
  fus.rotation.z=Math.PI/2;ac.add(fus);
  // 코(원뿔)
  const nose=new THREE.Mesh(new THREE.ConeGeometry(R,R*2.2,32),skin);
  nose.rotation.z=Math.PI/2;nose.position.x=AC.코x-R*0.9;ac.add(nose);
  // 꼬리 원뿔
  const tail=new THREE.Mesh(new THREE.ConeGeometry(R,R*3,32),skin);
  tail.rotation.z=-Math.PI/2;tail.position.x=AC.꼬리x+R*1.2;ac.add(tail);
  for(const s of[1,-1]){
    const wing=new THREE.Mesh(new THREE.BoxGeometry(3.2,0.18,span),skin2);
    wing.position.set(wx-sw*0.5,-R*0.3,s*(span/2+R*0.4));
    wing.rotation.y=s*0.32;ac.add(wing);
    // 엔진
    const eng=new THREE.Mesh(new THREE.CylinderGeometry(0.5,0.5,1.6,16),skin2);
    eng.rotation.z=Math.PI/2;eng.position.set(wx-sw*0.4,-R*0.7,s*(span*0.45));ac.add(eng);
  }
  // 수직미익
  const vt=new THREE.Mesh(new THREE.BoxGeometry(2.6,vth,0.16),skin2);
  vt.position.set(AC.꼬리x-1.4,R*0.4+vth/2,0);vt.rotation.z=0.25;ac.add(vt);
  // 수평미익
  for(const s of[1,-1]){const ht=new THREE.Mesh(new THREE.BoxGeometry(1.8,0.14,3),skin2);
    ht.position.set(AC.꼬리x-0.6,R*0.5,s*1.7);ht.rotation.y=s*0.3;ac.add(ht);}
  // 창문 줄(점선 느낌)
  const wmat=new THREE.MeshStandardMaterial({color:0x2a3a4a,emissive:0x101820});
  for(let x=AC.코x+3;x<AC.꼬리x-2;x+=1.1){const w=new THREE.Mesh(new THREE.BoxGeometry(0.14,0.18,0.02),wmat);w.position.set(x,R*0.35,R*0.98);ac.add(w);}
  scene.add(ac);
}
function buildPath(){
  const pts=WP.map(V);
  pathLine=new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),new THREE.LineDashedMaterial({color:col(css("--primary")),dashSize:0.4,gapSize:0.25,transparent:true,opacity:.5}));
  pathLine.computeLineDistances();scene.add(pathLine);
  WP.forEach(w=>{const m=new THREE.Mesh(new THREE.SphereGeometry(0.1,10,10),new THREE.MeshBasicMaterial({color:col(css("--primary")),transparent:true,opacity:.6}));m.position.copy(V(w));scene.add(m);});
  // 결함 표식
  window._defMk=DEF.map(d=>{
    const c=d.심각==="높음"?col(css("--bad")):d.심각==="중간"?col(css("--warn")):col(css("--muted"));
    const g=new THREE.Group();
    const ring=new THREE.Mesh(new THREE.TorusGeometry(0.35,0.04,8,24),new THREE.MeshBasicMaterial({color:c}));ring.rotation.x=Math.PI/2;g.add(ring);
    const dot=new THREE.Mesh(new THREE.SphereGeometry(0.12,12,12),new THREE.MeshBasicMaterial({color:c}));g.add(dot);
    g.position.copy(V(d.pos));g.visible=false;g.scale.setScalar(0.01);scene.add(g);return{g,c};
  });
  // 지나온 궤적
  trailLine=new THREE.Line(new THREE.BufferGeometry().setFromPoints([V(P[0])]),new THREE.LineBasicMaterial({color:col(css("--accent"))}));scene.add(trailLine);
}
function buildDrone(){
  drone=new THREE.Group();
  drone.add(new THREE.Mesh(new THREE.BoxGeometry(0.3,0.1,0.3),new THREE.MeshStandardMaterial({color:0x1a2230,emissive:col(css("--accent")),emissiveIntensity:.25})));
  for(const[a,b]of[[.22,.22],[-.22,.22],[.22,-.22],[-.22,-.22]]){
    const arm=new THREE.Mesh(new THREE.BoxGeometry(0.03,0.03,0.03),new THREE.MeshStandardMaterial({color:0x0d1117}));arm.position.set(a,0.02,b);drone.add(arm);
    const pr=new THREE.Mesh(new THREE.TorusGeometry(0.1,0.015,6,18),new THREE.MeshStandardMaterial({color:0x2a3646}));pr.rotation.x=Math.PI/2;pr.position.set(a,0.05,b);drone.add(pr);props.push(pr);
  }
  // 스캔 콘(아래로)
  const cone=new THREE.Mesh(new THREE.ConeGeometry(0.5,1.2,20,1,true),new THREE.MeshBasicMaterial({color:col(css("--accent")),transparent:true,opacity:.12,side:THREE.DoubleSide}));
  cone.position.y=-0.6;drone.add(cone);window._scan=cone;
  scene.add(drone);
  shadow=new THREE.Mesh(new THREE.CircleGeometry(0.3,20),new THREE.MeshBasicMaterial({color:0x000000,transparent:true,opacity:.2}));shadow.rotation.x=-Math.PI/2;scene.add(shadow);
}
function buildFeed(){
  feedC=document.getElementById("feed");feedR=new THREE.WebGLRenderer({canvas:feedC,antialias:true});
  feedR.setPixelRatio(1);feedR.setSize(150,110,false);feedCam=new THREE.PerspectiveCamera(42,150/110,0.05,60);
}
function buildDefList(){
  const box=document.getElementById("deflist");box.innerHTML="";
  DEF.forEach((d,i)=>{
    const icon=d.종류==="균열"?"⚡":d.종류==="눌림"?"🔨":d.종류==="부식"?"🟤":"🔩";
    const c=d.심각==="높음"?"var(--bad)":d.심각==="중간"?"var(--warn)":"var(--muted)";
    const el=document.createElement("div");el.className="def";el.id="def"+i;
    el.innerHTML=`<div class="ic" style="background:${c};color:#fff">${icon}</div>
      <div><div class="t">${d.종류} · ${d.크기mm}mm</div><div class="s">봄거리 ${d.봄거리_m}m · GSD ${d.GSD_mm}mm (최소 ${d.최소검출_mm})</div></div>
      <span class="sev ${d.심각}">${d.심각}</span>`;
    box.appendChild(el);
  });
  document.getElementById("dc").textContent="0/"+DEF.length;
}
function buildSpec(){
  const m=D.지표,S=D.SPEC;
  document.getElementById("sgsd").textContent=m.GSD표준_mm+"mm (최소검출 "+m.최소검출표준_mm+")";
  document.getElementById("sswath").textContent=m.스와스표준_m+"m";
  document.getElementById("sstand").textContent=m.표준거리min_m+"~"+m.표준거리max_m+"m (밴드 "+S.d_min_m+"~"+S.d_max_m+")";
  const box=document.getElementById("veriflist");box.innerHTML="";
  const 라벨={표준거리_밴드:"표준거리 밴드",속도_한계:"속도 ≤ v_max",결함_전부검출:"결함 전부검출",커버리지_목표:"커버리지 목표"};
  Object.entries(m.검증).forEach(([k,ok])=>{
    const el=document.createElement("div");el.className="def on";el.style.padding="5px 0";
    el.innerHTML=`<div class="ic" style="width:20px;height:20px;background:${ok?'var(--good)':'var(--bad)'};color:#fff;font-size:.75rem">${ok?'✓':'✗'}</div>
      <div class="t" style="font-size:.78rem">${라벨[k]||k}</div>
      <span class="sev" style="margin-left:auto;background:${ok?'var(--good)':'var(--bad)'};color:#fff">${ok?'PASS':'FAIL'}</span>`;
    box.appendChild(el);
  });
}
function resize(){const w=cv.clientWidth,h=cv.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();}
function camPos(){
  const dp=V(P[idx]);
  if(cam==="follow"){orbit.tgt.lerp(dp,0.15);camera.position.set(dp.x-5,dp.y+3,dp.z-5);camera.lookAt(orbit.tgt);return;}
  if(cam==="drone"){camera.position.copy(dp);
    // 항공기 중심을 본다
    camera.lookAt(new THREE.Vector3(dp.x*0.3,0,0));return;}
  const o=orbit;camera.position.set(o.tgt.x+o.r*Math.sin(o.phi)*Math.cos(o.theta),o.tgt.y+o.r*Math.cos(o.phi),o.tgt.z+o.r*Math.sin(o.phi)*Math.sin(o.theta));camera.lookAt(o.tgt);
}
function nearestSurfaceDist(p){
  // 동체 축(x)까지 반경거리 - 반경 (근사 표면거리)
  const rr=Math.hypot(p[1],p[2]);return Math.max(0,rr-AC.동체반경);
}
function update(){
  const p=P[idx],v=V(p);drone.position.copy(v);
  shadow.position.set(v.x,-AC.동체반경-3.19,v.z);
  trailLine.geometry.setFromPoints(P.slice(0,idx+1).map(V));
  // 웨이포인트 진행
  const wpDone=Math.min(WP.length,Math.floor((idx/(N-1))*WP.length)+1);
  // 결함 검출 진행
  let detected=0;
  DEF.forEach((d,i)=>{
    if(d.검출 && idx>=d.검출idx){ if(!DEFSTATE[i]){DEFSTATE[i]=true;document.getElementById("def"+i).classList.add("on");window._defMk[i].g.visible=true;}
      const mk=window._defMk[i].g; if(mk.scale.x<1)mk.scale.setScalar(Math.min(1,mk.scale.x+0.08));
      mk.children[0].rotation.z+=0.05; detected++;}
  });
  document.getElementById("dc").textContent=detected+"/"+DEF.length;
  // HUD -- 표면거리는 시뮬이 낸 standoff 를 그대로
  const surf=(D.standoff&&D.standoff[idx]!=null)?D.standoff[idx]:nearestSurfaceDist(p);
  document.getElementById("ht").textContent=T[idx].toFixed(1)+"s";
  document.getElementById("halt").textContent=p[1].toFixed(1)+" m";
  document.getElementById("hsurf").textContent=surf.toFixed(2)+" m";
  document.getElementById("hwp").textContent=wpDone+"/"+WP.length;
  const cov=Math.round(wpDone/WP.length*100);
  document.getElementById("cov").textContent=cov+"%";document.getElementById("covbar").style.width=cov+"%";
  // 텔레메트리
  const he=H[idx];const hn=Math.hypot(he[0],he[1],he[2]);
  document.getElementById("tp").textContent=p.map(x=>x.toFixed(1)).join(", ");
  document.getElementById("th").textContent=hn.toFixed(2);
  const sp=idx>0?Math.hypot(...p.map((x,j)=>(x-P[idx-1][j])/((T[idx]-T[idx-1])||1))):0;
  document.getElementById("tv").textContent=sp.toFixed(1)+" m/s";
  // 추종오차 = 가장 가까운 웨이포인트 거리(근사)
  let me=1e9;WP.forEach(w=>{const dd=Math.hypot(w[0]-p[0],w[1]-p[1],w[2]-p[2]);if(dd<me)me=dd;});
  document.getElementById("te").textContent=me.toFixed(2)+" m";
  document.getElementById("scrub").value=idx;
  // 상태/피드
  const near=DEF.find((d,i)=>d.검출 && Math.abs(idx-d.검출idx)<6);
  const stEl=document.getElementById("st");
  document.getElementById("feedcap").textContent=near?("⚠ "+near.종류+" 감지"):"";
  stEl.textContent=near?"DEFECT FOUND":"SCANNING";stEl.style.color=near?"var(--bad)":"var(--good)";
  if(window._scan)window._scan.material.opacity=near?0.28:0.1;
}
function renderFeed(){
  const p=V(P[idx]);feedCam.position.copy(p);
  feedCam.lookAt(new THREE.Vector3(p.x,0,0)); // 동체 표면을 향해
  feedR.render(scene,feedCam);
}
function loop(){
  requestAnimationFrame(loop);const now=performance.now(),dt=(now-last)/1000;last=now;
  props.forEach(pr=>pr.rotation.z+=0.8*speed);
  if(playing){idx+=Math.max(1,Math.round(dt/0.06*speed));if(idx>=N)idx=0;update();}
  camPos();renderer.render(scene,camera);renderFeed();
}
// 조작
let drag=null;
cv.addEventListener("pointerdown",e=>{if(cam!=="orbit")return;drag={x:e.clientX,y:e.clientY};cv.setPointerCapture(e.pointerId);});
cv.addEventListener("pointermove",e=>{if(!drag)return;orbit.theta-=(e.clientX-drag.x)*0.008;orbit.phi=Math.max(0.2,Math.min(1.45,orbit.phi-(e.clientY-drag.y)*0.006));drag={x:e.clientX,y:e.clientY};});
cv.addEventListener("pointerup",()=>drag=null);
cv.addEventListener("wheel",e=>{e.preventDefault();orbit.r=Math.max(8,Math.min(45,orbit.r*(1+Math.sign(e.deltaY)*0.08)));},{passive:false});
document.getElementById("play").onclick=function(){playing=!playing;this.textContent=playing?"❚❚":"▶";};
document.getElementById("scrub").oninput=function(){playing=false;document.getElementById("play").textContent="▶";idx=+this.value;update();};
document.getElementById("spd").onclick=function(){speed=speed>=2?0.5:speed*2;this.textContent=speed+"×";};
function setCam(m){cam=m;["orbit","follow","drone"].forEach(k=>document.getElementById("c_"+k).classList.toggle("on",k===m));if(m==="orbit")orbit={theta:0.7,phi:1.0,r:20,tgt:new THREE.Vector3(0,1,0)};}
document.getElementById("c_orbit").onclick=()=>setCam("orbit");
document.getElementById("c_follow").onclick=()=>setCam("follow");
document.getElementById("c_drone").onclick=()=>setCam("drone");
window.addEventListener("resize",()=>renderer&&resize());
build();
</script></body></html>"""


if __name__ == "__main__":
    종류 = sys.argv[1] if len(sys.argv) > 1 else "검사3d"
    데이터 = sys.argv[2] if len(sys.argv) > 2 else "ctrl/model/검사3d.json"
    출력 = sys.argv[3] if len(sys.argv) > 3 else "ctrl/model/검사3d.html"
    p = 만들기(종류, 데이터, 출력)
    print(f"HTML 생성: {p} ({pathlib.Path(p).stat().st_size} bytes)")
