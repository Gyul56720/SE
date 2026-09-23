# -*- coding: utf-8 -*-
"""house/pd/agent -- Kenji Tanaka (Physical Design) 의 업무와 보고서.

하는 일:
  1. 플로어플랜 · 전원 계획 (코어 치수 · 행 · 스트라이프를 IR/EM 으로 재서)
  2. 배치 (전역 + 합법화) 와 HPWL
  3. CTS (클럭 트리 · 삽입지연 · 스큐 · OCV · 균형의 값)
  4. 배선 (전역 → 상세 → 탐색수리, 혼잡도)
  5. 사인오프 (배선 전/후 타이밍 · 밀도 · DRC)
  6. GDSII 출력과 **왕복 검증** (쓴 도형 수 = 되읽은 도형 수)

lab/se 의 구현을 쓰되, 결과를 **좌표 그대로 그림으로** 낸다 -- 레이아웃은
수보다 그림이 먼저다.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

뿌리 = Path(__file__).resolve().parent
집 = 뿌리.parent
저장소 = 집.parent
sys.path.insert(0, str(저장소))
sys.path.insert(0, str(저장소 / "lab" / "se"))

from house import people    # noqa: E402
from house import report as RPT       # noqa: E402
from house import synth as SYN        # noqa: E402
from house import viz as V            # noqa: E402
from house import sch as SCH          # noqa: E402
from house.pd import gds as GDS       # noqa: E402


def 일하기(빠르게=False, 설계=None) -> dict:
    import liberty as L
    import netlist as NL
    import floorplan as FP
    import place as PL
    import cts as CT
    import route as RT
    import signoff as SO

    from house import designs as DES
    d = 설계 or DES.NSW_FIR
    R = {"시작": time.time(), "설계": d.키, "설계이름": d.이름, "top": d.top}
    # **FIR 의 이름을 되돌이값으로 쓰지 않는다.** `d.파라` 는 대개 비어 있어서
    # (실측: nsw_fir 도 `{}`) 이 되돌이값이 **늘 쓰이고 있었다** -- 다른 회로에도
    # `TAPS=8 · STAGES=3 · GATE_POLICY=1` 이 넘어간다.
    합 = SYN.합성(DES.파라기본(d) or None, 설계=d)
    R["합성"] = 합
    if not 합.get("됐나"):
        R["초"] = round(time.time() - R["시작"], 1)
        return R
    lb = L.라이브러리(str(SYN.LIB))
    nl = NL.넷리스트(합["json"], lb)
    R["넷리스트"] = nl.요약()

    # --- 플로어플랜 ---
    fp = FP.플로어플랜(nl)
    R["fp"] = fp.요약()
    R["스트라이프스윕"] = []
    for N in (2, 4, 8, 16, 32):
        try:
            R["스트라이프스윕"].append({
                "N": N, "IR폭": round(fp.스트라이프폭_IR(N), 4),
                "EM폭": round(fp.스트라이프폭_EM(N), 4),
                "쓸폭": round(fp.스트라이프폭(N), 4), "무는것": fp.무는것(N),
                "레일강하_mV": round(fp.레일강하(N) * 1e3, 4)})
        except Exception as e:                               # noqa: BLE001
            R["스트라이프스윕"].append({"N": N, "오류": f"{type(e).__name__}"})
    try:
        R["그리드"] = fp.그리드풀기()
    except Exception as e:                                   # noqa: BLE001
        R["그리드"] = {"오류": str(e)[:100]}
    try:
        R["트랙"] = fp.트랙공급()
    except Exception as e:                                   # noqa: BLE001
        R["트랙"] = {"오류": str(e)[:100]}

    # --- 배치 ---
    t0 = time.time()
    p = PL.배치기(nl, fp)
    R["배치"] = p.돌리기()
    R["배치초"] = round(time.time() - t0, 2)
    # 셀 좌표를 그림용으로 뽑는다
    셀들 = []
    플롭이름 = {i.이름 for i in nl.플롭들}
    for 이름, inst in list(nl.인스턴스.items())[:6000]:
        x, y = getattr(inst, "x", None), getattr(inst, "y", None)
        if x is None or y is None:
            continue
        w = p.폭.get(이름, 0.66)
        종 = ("icg" if "LAT" in str(inst.종류)
              else ("seq" if 이름 in 플롭이름 else "comb"))
        셀들.append((x, y, w, PL.행높이, 종))
    R["셀좌표"] = 셀들
    R["행들"] = [k * PL.행높이 for k in range(fp.행수)][:200]

    # --- CTS ---
    t0 = time.time()
    ct = CT.클럭트리(nl, p)
    R["cts"] = ct.요약()
    R["cts초"] = round(time.time() - t0, 2)
    try:
        R["잎도착"] = [round(v * 1e3, 3) for v in ct.잎도착().values()][:4000]
    except Exception:                                        # noqa: BLE001
        R["잎도착"] = []

    # --- 배선 ---
    t0 = time.time()
    rt = RT.배선기(nl, p, fp)
    전역 = rt.전역()
    R["배선"] = rt.요약()
    R["탐색수리"] = rt.탐색수리()
    R["배선초"] = round(time.time() - t0, 2)
    try:
        수 = rt.수요()
        # gcell 격자를 히트맵으로
        격자 = []
        칸수 = int(len(수) ** 0.5) if isinstance(수, (list, tuple)) else 0
        if isinstance(수, dict):
            xs = sorted({k[0] for k in 수})
            ys = sorted({k[1] for k in 수})
            격자 = [[수.get((x, y), 0) for x in xs] for y in ys]
        R["혼잡격자"] = 격자[:40]
    except Exception:                                        # noqa: BLE001
        R["혼잡격자"] = []

    # --- 그림용 좌표: 배선 선분과 클럭 트리 가지 ---
    try:
        g = rt.g
        선 = []
        for nid, 길 in list(rt.경로.items())[:2200]:
            for k in range(len(길) - 1):
                (i0, j0), (i1, j1) = 길[k], 길[k + 1]
                선.append(((i0 + 0.5) * g, (j0 + 0.5) * g,
                          (i1 + 0.5) * g, (j1 + 0.5) * g, (k % 4)))
        R["배선선분"] = 선[:9000]
    except Exception:                                        # noqa: BLE001
        R["배선선분"] = []
    try:
        가지 = []
        for 색인, 마 in enumerate(ct.마디):
            for 자 in 마[2]:
                가지.append((마[0], 마[1], ct.마디[자][0], ct.마디[자][1]))
        R["클럭가지"] = 가지[:4000]
        R["클럭버퍼"] = [(마[0], 마[1]) for 마 in ct.마디 if 마[3] == "버퍼"][:1200]
    except Exception:                                        # noqa: BLE001
        R["클럭가지"], R["클럭버퍼"] = [], []

    # --- 사인오프 ---
    t0 = time.time()
    so = SO.사인오프(nl, p, fp, rt)
    try:
        R["사인오프"] = so.돌리기()
    except Exception as e:                                   # noqa: BLE001
        R["사인오프"] = {"오류": f"{type(e).__name__}: {e}"}
    try:
        전, 후, 표류, _후분석 = so.전후()
        R["전후"] = {
            "배선전_최악슬랙_ps": round(전.최악슬랙 * 1e3, 2),
            "배선후_최악슬랙_ps": round(후.최악슬랙 * 1e3, 2),
            "끝점수": len(표류),
            "표류_평균_ps": round(sum(t[0] for t in 표류) / len(표류) * 1e3, 2) if 표류 else 0.0,
            "표류_최악_ps": round(표류[0][0] * 1e3, 2) if 표류 else 0.0,
        }
        R["표류들_ps"] = [round(t[0] * 1e3, 3) for t in 표류]
        # **사인오프가 실제로 판정한 회로**를 회로도로 그리려고 임계경로를 꺼낸다.
        # 배선 기생이 들어간 '후' 쪽이다 -- 사인오프는 그것으로 판정한다.
        R["임계경로"] = SCH.경로뽑기(nl, 후.임계경로, 몇=13)
        R["임계"] = {"주기_ps": round(후.주기 * 1e3, 1),
                   "슬랙_ps": round(후.최악슬랙 * 1e3, 1),
                   "위반수": 후.위반수, "단수": len(후.임계경로),
                   "전_슬랙_ps": round(전.최악슬랙 * 1e3, 1)}
        R["표류최악10"] = [[t[1][0] + "/" + t[1][1], round(t[2] * 1e3, 2),
                        round(t[3] * 1e3, 2), round(t[0] * 1e3, 2)]
                       for t in 표류[:10]]
    except Exception as e:                                   # noqa: BLE001
        R["전후"] = {"오류": f"{type(e).__name__}: {e}"[:160]}
        R["표류들_ps"], R["표류최악10"], R["임계경로"] = [], [], []
    try:
        R["밀도"] = so.밀도()
    except Exception as e:                                   # noqa: BLE001
        R["밀도"] = {"오류": str(e)[:120]}
    R["사인오프초"] = round(time.time() - t0, 2)

    # --- GDSII ---
    t0 = time.time()
    W = R["fp"].get("코어_um")
    try:
        폭, 높이 = (W if isinstance(W, (list, tuple)) else (float(str(W).split("x")[0]),
                                                          float(str(W).split("x")[-1])))
    except Exception:                                        # noqa: BLE001
        폭, 높이 = 120.0, 126.0
    _탑 = R.get("top") or "nsw_fir"
    lib = GDS.라이브러리(_탑.upper())
    lib.구조시작(_탑)
    lib.사각("BOUNDARY", 0, 0, 폭, 높이)
    for y in R["행들"]:
        lib.사각("M1", 0, y, 폭, 0.6)                       # 전원 레일
    N = R["fp"].get("스트라이프수", 8) or 8
    for i in range(int(N)):
        x = 폭 * (i + 0.5) / int(N)
        lib.선("M2", [(x, 0), (x, 높이)], 폭=max(R["fp"].get("스트라이프폭_um", 0.6) or 0.6, 0.3))
    for (x, y, w, h, 종) in 셀들[:4000]:
        lib.사각("POLY" if 종 == "comb" else ("DIFF" if 종 == "seq" else "CONT"),
                x, y, max(w, 0.2), 4.2)
    lib.글("TEXT", 1.0, 높이 - 2.0,
          f"{R.get('설계이름') or 'NSW-FIR v1.0'} / Nowon Silicon Works")
    R["gds길"] = str(RPT.내는곳 / f"{_탑}.gds")
    R["gds"] = GDS.왕복확인(lib, RPT.내는곳 / f"{_탑}.gds")
    R["gds초"] = round(time.time() - t0, 2)
    R["코어"] = (폭, 높이)

    R["초"] = round(time.time() - R["시작"], 1)
    return R


def 보고서(m: dict) -> RPT.보고서:
    P = people.KENJI
    # **제목이 회로 이름을 따라간다** -- 실측 2026-09-22 의 그 사고.
    _이름 = m.get("설계이름") or "NSW-FIR v1.0"
    _탑2 = m.get("top") or "nsw_fir"
    R = RPT.보고서(P, f"{_이름} 물리 설계 · 사인오프 · GDSII 보고서",
                 f"{_탑2} IP",
                 "플로어플랜 · 전원계획 · 배치 · CTS · 배선 · 사인오프 · GDSII")
    R.업무초 = m.get("초")
    if not m.get("합성", {}).get("됐나"):
        R.절("합성 실패")
        R.그림(V.빈그림("합성이 안 돼 물리 설계를 시작하지 못했다"))
        return R

    fp = m["fp"]
    배 = m["배치"]
    ct = m["cts"]
    rt = m["배선"]
    g = m["gds"]

    R.요약(f"코어 {m['코어'][0]:.1f} × {m['코어'][1]:.1f} µm, 행 {fp.get('행수')}개, "
          f"점유율 {fp.get('점유율', 0.7)*100 if isinstance(fp.get('점유율'), float) else fp.get('점유율')}")
    R.요약(f"배치 — HPWL {배.get('HPWL_전역_um', 0):,.0f} → {배.get('HPWL_합법_um', 0):,.0f} µm "
          f"(합법화), 겹침 {배.get('겹침')}개, 자리 맞음 {배.get('자리맞음')}")
    R.요약(f"CTS — 삽입지연 {ct.get('삽입지연_ps')} ps, 스큐 {ct.get('스큐_ps')} ps "
          f"({ct.get('스큐_ps',0)/max(ct.get('삽입지연_ps',1),1)*100:.1f} %), "
          f"균형에 버퍼 {ct.get('균형맞추기',{}).get('끼운버퍼')}개")
    R.요약(f"배선 — 총 {rt.get('총배선길이_um', 0):,.0f} µm, 우회비 "
          f"{rt.get('우회비_배선길이/HPWL')}, 넘친 칸 {rt.get('넘친칸')}개")
    R.요약(f"<b>GDSII 왕복 검증 {'통과' if g['맞나'] else '실패'}</b> — "
          f"{g['바이트']:,} 바이트, 도형 {sum(g['읽은것'].values()):,}개, "
          f"층 {len(g['층별도형'])}종")

    # ---------------- 0. 흐름 ----------------
    R.절("0. 이번에 실제로 돈 물리 설계 흐름")
    R.그림(V.흐름([f"합성 넷리스트\\n{m['넷리스트'].get('인스턴스', 0):,} 셀",
                f"플로어플랜\\n{m['코어'][0]:.0f}×{m['코어'][1]:.0f} µm",
                f"배치\\nHPWL {배.get('HPWL_합법_um', 0)/1e3:,.0f} k µm",
                f"CTS\\n스큐 {ct.get('스큐_ps')} ps",
                f"배선\\n{rt.get('총배선길이_um', 0)/1e3:,.0f} k µm",
                f"사인오프\\n밀도·타이밍",
                f"GDSII\\n{g['바이트']/1e3:,.0f} kB"],
               "이번 실행에서 실제로 돈 단계와 그 단계가 낸 수", 폭=640),
         "<b>이 그림의 수는 전부 이번 실행에서 잰 것이다</b> — 가정이 아니다. "
         f"단계별 소요: 플로어플랜 즉시, 배치 {m['배치초']} s, CTS {m['cts초']} s, "
         f"배선 {m['배선초']} s, 사인오프 {m['사인오프초']} s, GDSII {m['gds초']} s.",
         "lab/se/{floorplan,place,cts,route,signoff}.py + house/pd/gds.py")

    # ---------------- 1. 플로어플랜 ----------------
    R.절("1. 플로어플랜과 전원 계획")
    try:
        코폭, 코높 = m["코어"]
        다 = fp.get("다이_um") or [코폭 * 1.3, 코높 * 1.3]
        N스 = max(int(fp.get("스트라이프수", 8) or 8), 1)
        ox = (다[0] - 코폭) / 2
        R.그림(V.플로어플랜도([다[0], 다[1]], [코폭, 코높],
                       [ox + 코폭 * (i + 0.5) / N스 for i in range(N스)],
                       float(fp.get("스트라이프폭_um", 0.6) or 0.6),
                       가로스트라이프=5,
                       링폭=float(fp.get("링폭_um", 2.0) or 2.0),
                       패드수=32,
                       제목="플로어플랜 — 다이 · 패드 링 · 전원 링 · 스트라이프 · 코어",
                       폭=470),
             f"강의 화면의 그 플로어플랜 그림이고, <b>치수는 이 설계에서 잰 것</b>이다. "
             f"코어 {코폭:.1f}×{코높:.1f} µm 가 다이 {다[0]:.0f}×{다[1]:.0f} µm 안에 들고, "
             f"둘레에 I/O 패드 32개와 코너 셀 4개, 그 안쪽에 전원 링 2겹, "
             f"코어를 가로세로로 가르는 전원 스트라이프 {N스}개(폭 "
             f"{fp.get('스트라이프폭_um')} µm)가 있다. "
             f"<b>{'패드 제한 다이' if fp.get('패드제한다이') else '코어 제한 다이'}</b> — "
             + ("패드 링 둘레가 코어보다 커서 다이 치수를 패드가 정했다. "
                "이때는 코어를 더 줄여도 다이가 안 준다." if fp.get("패드제한다이")
                else "코어가 다이를 정한다."),
             "lab/se/floorplan.py + house/viz.py 플로어플랜도()")
        R.그림(V.전원계획([다[0], 다[1]], [코폭, 코높],
                      [ox + 코폭 * (i + 0.5) / N스 for i in range(N스)],
                      float(fp.get("스트라이프폭_um", 0.6) or 0.6),
                      링폭=float(fp.get("링폭_um", 2.0) or 2.0),
                      행수=min(int(fp.get("행수", 0) or 0), 68),
                      제목="다이 · 코어 · 전원 계획 (실제 치수)", 폭=440),
             f"코어 {코폭:.1f}×{코높:.1f} µm 가 다이 {다[0]:.0f}×{다[1]:.0f} µm 안에 든다. "
             f"세로 보라선이 전원 스트라이프 {N스}개(폭 {fp.get('스트라이프폭_um')} µm), "
             f"주황 테두리가 전원 링(폭 {fp.get('링폭_um')} µm)이다. "
             f"<b>{'패드 제한 다이' if fp.get('패드제한다이') else '코어 제한 다이'}</b> — "
             + ("패드 링 둘레가 코어보다 커서 다이 치수를 패드가 정했다. "
                "이때 코어를 더 줄여도 다이는 안 준다." if fp.get("패드제한다이")
                else "코어가 다이를 정한다."),
             "lab/se/floorplan.py")
    except Exception as e:                                   # noqa: BLE001
        R.그림(V.빈그림(f"플로어플랜 그림 실패: {type(e).__name__}: {e}"[:90]))
    R.표(["항목", "값"], [[k, str(v)] for k, v in fp.items()],
        "플로어플랜 요약.", "lab/se/floorplan.py")
    스 = [x for x in m["스트라이프스윕"] if "오류" not in x]
    if 스:
        R.그림(V.선([x["N"] for x in 스],
                  [("IR 로 정해지는 폭", [x["IR폭"] for x in 스]),
                   ("EM 으로 정해지는 폭", [x["EM폭"] for x in 스]),
                   ("실제 쓸 폭", [x["쓸폭"] for x in 스])],
                  "스트라이프 수에 대한 필요 폭", "스트라이프 수", "폭 (µm)", 폭=580, 로그y=True),
             "<b>무는 것이 바뀌는 자리가 보인다.</b> 스트라이프가 적으면 IR 이, 많으면 "
             "최소폭이 문다. 셋 중 가장 큰 것이 실제로 써야 하는 폭이다.",
             "lab/se/floorplan.py (IR·EM·최소폭)")
        R.표(["스트라이프 수", "IR 폭 (µm)", "EM 폭 (µm)", "쓸 폭 (µm)", "무는 것", "레일 강하 (mV)"],
            [[x["N"], x["IR폭"], x["EM폭"], x["쓸폭"], x["무는것"], x["레일강하_mV"]] for x in 스],
            "스트라이프 스윕. <b>총 금속 폭은 스트라이프 수를 따라 안 바뀐다</b> — "
            "N 개로 나눠도 N 분의 1 씩이라 합은 같다. 스트라이프 수가 사는 것은 "
            "<b>레일 강하</b>이고, 그것이 마지막 칸이다.", "lab/se/floorplan.py", 강조열=[4, 5])
    if isinstance(m.get("그리드"), dict) and "오류" not in m["그리드"]:
        R.표(["항목", "값"], [[k, str(v)] for k, v in m["그리드"].items()],
            "전원 그리드를 저항 사다리로 직접 풀어 본 것 — <b>닫힌 꼴의 독립 대조</b>다.",
            "lab/se/floorplan.py 그리드풀기() (numpy 선형 풀이)")

    # ---------------- 2. 배치 ----------------
    R.절("2. 배치")
    if m["셀좌표"]:
        R.그림(V.레이아웃(m["코어"], m["행들"], m["셀좌표"][:3500], 제목="배치 결과 (실제 좌표)",
                     폭=560),
             f"셀 {len(m['셀좌표']):,}개의 실제 배치 좌표. 빨강이 플롭, 파랑이 조합, "
             f"주황이 ICG 래치다. <b>클럭을 받는 것(빨강)이 어디 모여 있는지</b>가 "
             f"CTS 의 삽입지연을 정한다.", "lab/se/place.py")
    R.표(["항목", "값", "뜻"],
        [["전역 HPWL", f"{배.get('HPWL_전역_um', 0):,.1f} µm", "연속 문제의 답 — 아무도 못 이룬다"],
         ["합법화 HPWL", f"{배.get('HPWL_합법_um', 0):,.1f} µm", "행·자리에 물린 실제 값"],
         ["합법화 증가", f"{(배.get('HPWL_합법_um',0)/max(배.get('HPWL_전역_um',1),1e-9)-1)*100:+.1f} %",
          "<b>이 계단이 크면 밀도가 너무 높다는 신호다</b>"],
         ["겹침", f"{배.get('겹침')}", "0 이어야 한다"],
         ["자리 맞음", f"{배.get('자리맞음')}", "모든 셀이 SITE 경계에 물렸나"],
         ["배치 시간", f"{m['배치초']} s", ""]],
        "배치 결과.", "lab/se/place.py", 강조열=[1])

    # ---------------- 3. CTS ----------------
    R.절("3. 클럭 트리 합성 (CTS)")
    R.표(["항목", "값"], [[k, str(v)] for k, v in ct.items() if k != "균형맞추기"],
        "클럭 트리 요약.", "lab/se/cts.py")
    균 = ct.get("균형맞추기", {})
    if 균:
        R.그림(V.막대(["삽입지연", "스큐 (균형 전)", "스큐 (균형 후)", "OCV 스큐"],
                   [ct.get("삽입지연_ps", 0), ct.get("스큐_ps", 0),
                    균.get("맞춘뒤_스큐_ps", 0), ct.get("OCV스큐_ps", 0)],
                   "클럭 트리 — 균형을 맞추기 전과 후", "ps",
                   색들=["#4a7fb5", "#e05c3e", "#2e9e6b", "#c88a2e"], 폭=560),
             f"버퍼 {균.get('끼운버퍼')}개를 끼워 스큐를 {ct.get('스큐_ps')} ps → "
             f"{균.get('맞춘뒤_스큐_ps')} ps 로 줄였다"
             f"({(1 - (균.get('맞춘뒤_스큐_ps') or 0) / max(ct.get('스큐_ps') or 1, 1e-9)) * 100:.0f} % 감소). "
             f"<b>공짜가 아니다</b> — 클럭 전력이 {ct.get('클럭전력_uW')} µW 에서 "
             f"{균.get('전력_늘어난비', 0) * 100:+.1f} % 늘었다. "
             "OCV 스큐는 균형으로 못 지운다(공통 경로가 아닌 몫이다).",
             "lab/se/cts.py 균형맞추기() · OCV스큐()")
        R.표(["항목", "값"], [[k, str(v)] for k, v in 균.items()],
            "<b>스큐는 공짜가 아니다.</b> 균형을 맞추는 데 버퍼가 들고, 그 버퍼는 "
            "주기마다 뒤집힌다 — 스큐를 전력으로 산다.", "lab/se/cts.py 균형맞추기()", 강조열=[1])
    if m.get("클럭가지"):
        R.그림(V.레이아웃뷰어(m["코어"], m["셀좌표"][:2500],
                        클럭=m["클럭가지"][:3000],
                        제목="CTS 뷰어 — 클럭 넷 하이라이트", 폭=560, 층수=1),
             f"<b>클럭 트리를 실제 좌표로 그린 것</b>이다. 흰 선이 클럭 가지이고 "
             f"(버퍼 {len(m.get('클럭버퍼') or []):,}개, 총 가지 길이 "
             f"{ct.get('총가지길이_um', 0):,.0f} µm), 붉은 점이 그것을 받는 플롭 "
             f"{ct.get('잎(플롭)', 0):,}개다. 상용 P&R 뷰어에서 클럭 넷을 "
             f"하이라이트했을 때 보이는 그 그림이다. "
             f"<b>선이 길고 사방으로 뻗은 것이 스큐 {ct.get('스큐_ps')} ps 의 까닭</b>이다 — "
             f"플롭이 코어 전체에 흩어져 있어 가지 길이가 고르지 않다. "
             f"클럭 인지 배치로 플롭을 모으면 이 그림이 먼저 달라진다.",
             "lab/se/cts.py 의 실제 트리 좌표")
    if m["잎도착"]:
        R.그림(V.히스토그램(m["잎도착"], 26, "클럭 잎 도착 시각 분포", "도착 (ps)", "플롭 수", 폭=580),
             f"분포의 폭이 곧 스큐다. 삽입지연 {ct.get('삽입지연_ps')} ps 에 대해 "
             f"스큐 {ct.get('스큐_ps')} ps — <b>OCV 를 걸면 이것이 커진다</b>"
             f"(Marcus 의 §4.2: 공통 경로가 지워지지 않는 몫).", "lab/se/cts.py")

    # ---------------- 4. 배선 ----------------
    R.절("4. 배선")
    R.표(["항목", "값"], [[k, str(v)] for k, v in rt.items()],
        "배선 요약.", "lab/se/route.py")
    수리 = m.get("탐색수리")
    if isinstance(수리, dict):
        R.표(["항목", "값"], [[k, str(v)] for k, v in 수리.items()],
            "탐색 수리(rip-up & reroute). <b>비가 1 에 가까워지면 위반을 고치는 것이 "
            "아니라 옮기고 있는 것</b>이고, 그때는 위로 올라가야 한다(점유율·배치·층).",
            "lab/se/route.py 탐색수리()", 강조열=[1])
    기록 = rt.get("전역_바퀴별_넘친칸") or []
    if len(기록) >= 2:
        R.그림(V.선(list(range(1, len(기록) + 1)), [("넘친 칸 수", list(기록))],
                  "전역 배선 바퀴별 남은 위반", "바퀴", "넘친 gcell 수", 폭=560),
             "벌점을 올리며 다시 배선하는 고리다. <b>단조롭게 줄지 않는다</b> — "
             "그래서 lab/se/route.py 는 가장 좋았던 해를 붙들어 두고 끝에 되돌린다"
             f"(되돌림: {rt.get('최선으로_되돌림')}). "
             "줄다 멈추면 그것은 배선이 아니라 배치·점유율·층 수의 문제다.",
             "lab/se/route.py 전역()")
    if m.get("배선선분"):
        R.그림(V.레이아웃뷰어(m["코어"], m["셀좌표"][:3000],
                        배선=m["배선선분"][:7000],
                        제목="레이아웃 뷰어 — 배선 후", 폭=560, 층수=4),
             f"<b>배치된 셀 위에 전역 배선 경로를 층 색으로 얹은 것</b>이다. "
             f"넷 {rt.get('배선한_넷', 0):,}개, 총 배선 길이 "
             f"{rt.get('총배선길이_um', 0):,.0f} µm. 강의 화면의 그 빽빽한 레이아웃 "
             "그림이 왜 그렇게 빽빽한지가 여기서 보인다 — <b>셀보다 배선이 자리를 "
             "더 먹는다</b>. 색이 층이고, 층을 늘리는 것이 혼잡을 푸는 세 방법 중 "
             "하나다(나머지는 점유율을 낮추는 것과 배치를 다시 하는 것).",
             "lab/se/route.py 의 실제 경로 좌표")
    if m["혼잡격자"]:
        R.그림(V.히트맵(m["혼잡격자"], "gcell 배선 수요 지도", 폭=460,
                    색낮음="#eef4fb", 색높음="#c0392b"),
             "빨간 칸이 수요가 높은 gcell 이다. <b>전역 비가 낮아도 국소적으로 막힌다</b> — "
             "배선은 평균이 아니라 최악 칸에서 진다.", "lab/se/route.py 수요()")

    # ---------------- 5. 사인오프 ----------------
    R.절("5. 사인오프")
    so = m.get("사인오프")
    if isinstance(so, dict) and "오류" not in so:
        R.표(["항목", "값"], [[k, str(v)] for k, v in so.items()],
            "사인오프 검사 결과.", "lab/se/signoff.py")
    전후 = m.get("전후")
    if isinstance(전후, dict) and "오류" not in 전후:
        표류 = m.get("표류들_ps") or []
        if 표류:
            R.그림(V.히스토그램(표류, 칸수=26, 제목="끝점 슬랙 표류 (배선후 − 배선전)",
                            x이름="ps", 폭=620),
                 f"끝점 {len(표류):,}개의 슬랙이 배선으로 얼마나 밀렸나. "
                 f"평균 {전후['표류_평균_ps']} ps, 최악 {전후['표류_최악_ps']} ps. "
                 "<b>배선 전 타이밍은 낙관적이다</b> — 기생이 붙으면 임계경로가 길어진다. "
                 "이 분포가 물리 인지 합성을 쓰는 까닭이다.",
                 "lab/se/signoff.py 전후()")
        R.표(["항목", "값"], [[k, str(v)] for k, v in 전후.items()],
            "배선 전/후 타이밍 요약.", "lab/se/signoff.py")
        if m.get("표류최악10"):
            R.표(["끝점", "배선전 슬랙 ps", "배선후 슬랙 ps", "표류 ps"],
                [[a, f"{b:.2f}", f"{c:.2f}", f"{d:.2f}"]
                 for a, b, c, d in m["표류최악10"]],
                "가장 많이 밀린 끝점 10개.", "lab/se/signoff.py 전후()")
    밀 = m.get("밀도")
    if isinstance(밀, dict) and "오류" not in 밀:
        낮, 높 = 0.20, 0.70
        R.그림(V.게이지묶음([
            ("금속 밀도 평균", 밀.get("평균", 0), f"{밀.get('평균', 0) * 100:.1f} %", "#4a7fb5"),
            ("금속 밀도 최대", 밀.get("최대", 0), f"{밀.get('최대', 0) * 100:.1f} %", "#c88a2e"),
            ("창 아래 칸 (채움 필요)", 밀.get("창_아래_칸", 0) / max(밀.get("칸", 1), 1),
             f"{밀.get('창_아래_칸', 0):,} / {밀.get('칸', 0):,}", "#e05c3e"),
            ("창 위 칸 (CMP 위반)", 밀.get("창_위_칸", 0) / max(밀.get("칸", 1), 1),
             f"{밀.get('창_위_칸', 0):,} / {밀.get('칸', 0):,}", "#2e9e6b"),
        ], f"금속 밀도 사인오프 (창 {낮*100:.0f}–{높*100:.0f} %)", 폭=560),
             "CMP 는 금속이 너무 없어도(딤플) 너무 많아도(디싱) 진다. "
             f"<b>창 아래 칸 {밀.get('창_아래_칸', 0):,}개에는 더미 금속을 채워야 한다</b> — "
             "그리고 더미는 결합 용량을 늘려 타이밍을 다시 건드린다. 이것이 사인오프가 "
             "한 바퀴로 안 끝나는 까닭이다.", "lab/se/signoff.py 밀도()")
        R.표(["항목", "값"], [[k, str(v)] for k, v in 밀.items()],
            "밀도 검사 (CMP 창).", "lab/se/signoff.py 밀도()")

    # ---------------- 5.5 사인오프 회로도 ----------------
    경 = m.get("임계경로") or []
    임 = m.get("임계") or {}
    if 경:
        R.소절("5.1 사인오프 회로도 — 판정이 걸린 바로 그 회로")
        # **셀 수를 글에 적지 않는다.** 실측 2026-09-23: 한 문단에 `3,500개` 와
        # `4,308셀` 이 같이 박혀 있었는데, 그 실행의 실제 셀 수는 **4,313** 이었다.
        # 합성 결과는 실행마다 바뀌는 수다 -- 글에 굳히면 조용히 틀려 간다.
        _셀수 = len(m.get("셀좌표") or [])
        _그린수 = min(_셀수, 3500)
        R.글(f"레이아웃 그림(그림 3)은 셀이 <b>어디 있나</b>를 보이지 그것이 "
            f"<b>무엇인지</b>는 안 보인다 — 빨간 네모 {_그린수:,}개는 회로도가 "
            f"아니다. 그래서 사인오프가 실제로 판정한 회로, 곧 <b>배선 기생이 "
            f"들어간 뒤의 임계경로</b>를 게이트 기호로 그린다. {_셀수:,}셀을 다 "
            f"그리면 아무도 못 읽고, 이 한 경로가 주기를 정한다.")
        R.그림(SCH.경로도(경, "배선 후 임계경로 (사인오프 판정 대상)", 폭=640,
                      주기_ps=임.get("주기_ps"), 슬랙_ps=임.get("슬랙_ps"), 한줄=7),
             f"발사 플롭에서 포착 플롭까지 <b>{임.get('단수')}단</b>"
             + (f" (그림에는 앞뒤 {len(경)}단만, 가운데는 합으로 접었다)"
                if any("생략" in str(x.get('셀', '')) for x in 경) else "")
             + f". 기호 밑의 <b>+ps 가 그 셀에서 실제로 잰 지연</b>이고 Σ 는 누적 도착이다. "
             "<b>칸이 진할수록 그 셀이 느리다</b> — 어디를 고쳐야 하는지가 그림에서 바로 읽힌다. "
             f"주기 {임.get('주기_ps'):,.0f} ps 에 대해 슬랙 "
             f"<b>{임.get('슬랙_ps'):+,.0f} ps</b>, 위반 끝점 {임.get('위반수'):,}개. "
             f"배선 전에는 슬랙이 {임.get('전_슬랙_ps'):+,.0f} ps 였다 — "
             f"<b>기생이 {임.get('전_슬랙_ps',0)-임.get('슬랙_ps',0):,.0f} ps 를 먹었다</b>.",
             "lab/se/sta.py 되짚기() + house/sch.py 경로도()")
        느린 = sorted([x for x in 경 if not str(x.get("셀", "")).startswith("…")],
                   key=lambda x: -(x.get("증분_ps") or 0))[:6]
        R.표(["셀", "핀 이음", "그 셀의 지연 (ps)", "누적 도착 (ps)", "주기에서 차지하는 비"],
            [[x["셀"], x.get("이음") or "—", f"{x.get('증분_ps',0):,.1f}",
              f"{x.get('도착_ps',0):,.0f}",
              f"{(x.get('증분_ps') or 0)/max(임.get('주기_ps') or 1,1)*100:.1f} %"]
             for x in 느린],
            "임계경로에서 <b>가장 느린 셀 6개</b>. 회로도에서 진한 칸이 이것들이다. "
            "<b>한 셀이 주기의 몇 %를 먹는지</b>가 고칠 자리를 정한다 — "
            "구동을 키우거나(X1→X4), 부하를 나누거나, 논리를 다시 쓰거나.",
            "lab/se/sta.py", 강조열=[2, 4])
    # 사인오프 판정 판
    항 = []
    슬 = 임.get("슬랙_ps")
    if 슬 is not None:
        항.append(("타이밍 (setup)", "OK" if 슬 >= 0 else "NG", f"슬랙 {슬:+,.0f} ps",
                  "≥ 0 ps", "lab/se/sta.py"))
    if isinstance(밀, dict) and "오류" not in 밀:
        항.append(("금속 밀도 (CMP)",
                  "NG" if (밀.get("창_위_칸") or 밀.get("창_아래_칸")) else "OK",
                  f"평균 {밀.get('평균',0)*100:.1f} % / 창 밖 "
                  f"{(밀.get('창_아래_칸',0)+밀.get('창_위_칸',0)):,}칸",
                  "20–70 %", "lab/se/signoff.py"))
    넘 = rt.get("넘친칸")
    if 넘 is not None:
        항.append(("배선 혼잡", "OK" if 넘 == 0 else "NG", f"넘친 gcell {넘:,}칸",
                  "0칸", "lab/se/route.py"))
    항.append(("셀 겹침 (배치 합법성)", "OK" if not 배.get("겹침") else "NG",
              f"{배.get('겹침')}개", "0개", "lab/se/place.py"))
    삽2 = ct.get("삽입지연_ps") or 1
    맞2 = (ct.get("균형맞추기") or {}).get("맞춘뒤_스큐_ps") or 0
    항.append(("클럭 스큐", "OK" if 맞2 / 삽2 <= 0.10 else "NG",
              f"{맞2:,.0f} ps ({맞2/삽2*100:.0f} %)", "≤ 10 %", "lab/se/cts.py"))
    ir = (m.get("fp") or {}).get("그리드해_mV")
    예 = (m.get("fp") or {}).get("IR예산_mV")
    if ir is not None and 예:
        항.append(("IR 강하", "OK" if ir <= 예 else "NG", f"{ir:,.1f} mV",
                  f"{예:,.0f} mV", "lab/se/floorplan.py"))
    항.append(("GDSII 왕복", "OK" if g["맞나"] else "NG",
              f"도형 {sum(g['읽은것'].values()):,}개 / {g['바이트']:,} B",
              "쓴 것 = 읽은 것", "house/pd/gds.py"))
    항.append(("DRC", "-", "기하를 안 낸다", "—", "없음"))
    항.append(("LVS", "-", "스케매틱 대조를 안 했다", "—", "없음"))
    항.append(("안테나", "-", "안 봤다", "—", "없음"))
    R.그림(SCH.사인오프판(항, "사인오프 판정표 — 무엇을 보고 무엇을 안 봤나", 폭=580),
         "<b>초록만 있는 판은 사인오프가 아니다.</b> 빨강(위반)과 회색(안 함)을 "
         "같은 판에 올려야 이 설계가 어디까지 왔는지가 한눈에 보인다. "
         f"통과 {sum(1 for x in 항 if x[1]=='OK')}개 · "
         f"위반 {sum(1 for x in 항 if x[1]=='NG')}개 · "
         f"<b>안 한 것 {sum(1 for x in 항 if x[1]=='-')}개</b>. "
         "안 한 것을 판에서 빼면 초록이 늘지만 그것은 판정이 아니라 분식이다.",
         "house/sch.py 사인오프판()")

    # ---------------- 6. GDSII ----------------
    R.절("6. GDSII — 냈다고 말하려면 되읽어야 한다")
    R.글("klayout·magic 이 없다. 그래서 <b>GDSII stream 규격대로 바이트를 직접 적고</b>, "
        "같은 파일을 파서로 되읽어 도형 수와 층이 맞는지 확인했다. "
        "'GDS 를 냈다' 는 말을 확인할 수 있게 만드는 유일한 방법이다.")
    R.표(["항목", "쓴 것", "되읽은 것", "맞나"],
        [[k, g["쓴것"][k], g["읽은것"][k], "OK" if g["쓴것"][k] == g["읽은것"][k] else "불일치"]
         for k in g["쓴것"]],
        f"<b>왕복 검증 {'통과' if g['맞나'] else '실패'}</b>. "
        f"라이브러리 <code>{g['라이브러리']}</code>, {g['바이트']:,} 바이트, "
        f"레코드 {g['레코드수']:,}개, 좌표점 {g['좌표점수']:,}개.",
        "house/pd/gds.py", 강조열=[3])
    층이름 = {v[0]: k for k, v in GDS.층.items()}
    R.그림(V.막대([층이름.get(k, f"L{k}") for k in sorted(g["층별도형"])],
               [g["층별도형"][k] for k in sorted(g["층별도형"])],
               "GDSII 층별 도형 수", "도형", 폭=520, 값글=False),
         "실제로 파일에 들어간 층별 도형 수. 되읽어서 센 값이다.", "house/pd/gds.py 읽기()")
    R.코드(f"""$ ls -la {m.get('gds길') or (RPT.내는곳 / 'nsw_fir.gds')}
  {g['바이트']:,} bytes

$ python3 -c "from house.pd import gds; print(gds.읽기('{m.get('gds길') or (RPT.내는곳 / 'nsw_fir.gds')}'))"
  라이브러리: {g['라이브러리']}
  구조: {json.dumps(g['구조'], ensure_ascii=False)}
  도형: {json.dumps(g['읽은것'], ensure_ascii=False)}
  레코드: {g['레코드수']:,}   좌표점: {g['좌표점수']:,}""",
        "GDSII 파일과 그것을 되읽은 결과")

    # ---------------- 6.5 아직 못 닫은 것 ----------------
    R.절("7. 아직 사인오프를 못 통과한 것 — 다음 되돌이의 과제")
    삽, 스 = ct.get("삽입지연_ps") or 1, ct.get("스큐_ps") or 0
    맞춘 = (ct.get("균형맞추기") or {}).get("맞춘뒤_스큐_ps") or 0
    넘 = rt.get("넘친칸") or 0
    칸 = (rt.get("gcell") or [1, 1])
    항목 = []
    if 맞춘 / max(삽, 1e-9) > 0.10:
        항목.append(["클럭 스큐", f"{맞춘:.0f} ps ({맞춘/삽*100:.0f} % of 삽입지연)",
                   "10 % 이하", "<b>못 닫음</b>",
                   "클럭을 안 보고 배치한 탓이다. 플롭이 코어 전체에 흩어져 "
                   "가지 길이가 길다. 다음 되돌이에서 클럭 인지 배치(플롭 군집화)를 "
                   "먼저 하고 CTS 를 다시 돌려야 한다."])
    if 넘 > 0:
        항목.append(["배선 혼잡", f"넘친 gcell {넘:,} / {칸[0]*칸[1]:,}칸",
                   "0칸", "<b>못 닫음</b>",
                   f"점유율 {fp.get('점유율')} 에서 신호층 4 층으로는 모자란다. "
                   "고를 수 있는 것은 셋뿐이다 — 점유율을 낮춰 코어를 키우거나, "
                   "층을 늘리거나, 배치를 혼잡 인지로 다시 한다."])
    if 배.get("겹침"):
        항목.append(["셀 겹침", f"{배.get('겹침')}개", "0개", "<b>못 닫음</b>",
                   "합법화가 끝나고도 겹치면 합법화가 거짓말을 한 것이다."])
    if 항목:
        R.표(["항목", "잰 값", "받아들일 값", "판정", "왜 이렇게 됐고 무엇을 해야 하나"],
            항목, "<b>이 표가 이 보고서에서 가장 중요하다.</b> 위의 모든 수는 "
            "'돌았다'를 보이지만 이 표는 '아직 못 쓴다'를 보인다. "
            "초록불만 적은 보고서는 검사하지 않은 초록불이다.",
            "lab/se/{cts,route,place}.py", 강조열=[3])
        R.경고("이 설계는 <b>지금 상태로 테이프아웃할 수 없다</b> — 위 표의 항목이 남아 있다. "
             "GDSII 가 나온 것은 '흐름이 끝까지 돌았다'는 뜻이지 '쓸 수 있다'는 뜻이 아니다.")
    else:
        R.짚기("이번 되돌이에서 스큐·혼잡·겹침이 모두 기준 안에 들었다.")

    # ---------------- 8. 한계 ----------------
    R.한계(
        "· <b>상용 P&amp;R 이 아니다.</b> 배치기·CTS·배선기는 이 저장소의 교육용 구현이다. "
        "절대 품질을 Innovus·ICC2 와 견주면 안 된다 — 구성 사이의 비만 읽어야 한다.<br>"
        "· <b>DRC·LVS 를 안 했다.</b> 배선이 트랙 수를 내지 기하를 내지 않으므로 "
        "제조 가능성을 주장할 수 없다. GDSII 는 <b>도형이 들어 있고 규격대로 읽힌다</b>는 "
        "것만 증명한다.<br>"
        "· <b>추출 모형이 하나다.</b> 배선 R·C 가 마이크로미터당 상수 하나에서 나온다. "
        "독립 대조가 없다.<br>"
        "· <b>안테나·밀도 채움을 안 넣었다.</b> 넣으면 추출이 다시 필요하고, "
        "그 되돌이는 아직 안 돈다.<br>"
        "· <b>GDSII 에 실제 셀 기하가 없다.</b> 셀을 직사각형으로 그렸다 — "
        "표준셀 GDS 라이브러리가 없기 때문이다. 층 배정과 좌표는 진짜다.")

    R.잰것 = [
        ("코어 치수", f"{m['코어'][0]:.1f} × {m['코어'][1]:.1f}", "µm", "lab/se/floorplan.py"),
        ("행 수", fp.get("행수"), "행", "lab/se/floorplan.py"),
        ("HPWL (합법화 후)", f"{배.get('HPWL_합법_um', 0):,.1f}", "µm", "lab/se/place.py"),
        ("겹침", 배.get("겹침"), "개", "lab/se/place.py"),
        ("클럭 삽입지연", ct.get("삽입지연_ps"), "ps", "lab/se/cts.py"),
        ("클럭 스큐", ct.get("스큐_ps"), "ps", "lab/se/cts.py"),
        ("총 배선 길이", f"{rt.get('총배선길이_um', 0):,.0f}", "µm", "lab/se/route.py"),
        ("우회비", rt.get("우회비_배선길이/HPWL"), "×", "배선길이 / HPWL"),
        ("넘친 gcell", rt.get("넘친칸"), "칸", "lab/se/route.py"),
        ("GDSII 크기", f"{g['바이트']:,}", "바이트", "house/pd/gds.py"),
        ("GDSII 도형", f"{sum(g['읽은것'].values()):,}", "개", "되읽어서 센 값"),
        ("GDSII 왕복 검증", "통과" if g["맞나"] else "실패", "", "house/pd/gds.py 왕복확인()"),
        ("도구 실행 시간", m["초"], "s", "실측"),
    ]
    return R


def 돌리기(빠르게=False, 회로=None) -> dict:
    from house import designs as DES
    m = 일하기(빠르게, 설계=DES.찾기(회로))
    R = 보고서(m)
    길 = R.내기()
    return {"사람": people.KENJI, "잰것": m, "pdf": 길, "쪽": RPT.쪽수(길),
            "요약": R.요약줄, "그림수": R.그림수, "표수": R.표수}


if __name__ == "__main__":
    r = 돌리기("--빠르게" in sys.argv)
    print(f"PDF -> {r['pdf']}  ({r['쪽']} 쪽, 그림 {r['그림수']}, 표 {r['표수']})")
    for s in r["요약"]:
        print(" ·", re.sub(r"<[^>]+>", "", s))
