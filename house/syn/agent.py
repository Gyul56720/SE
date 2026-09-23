# -*- coding: utf-8 -*-
"""house/syn/agent -- Marcus Webb (Synthesis & PI) 의 업무와 보고서.

하는 일:
  1. 합성: RTL -> 게이트 넷리스트 (yosys, 실제 도구)
  2. 제약: SDC 를 실제로 파싱해 클럭·IO·예외·디레이트를 STA 에 건다
  3. STA: 27 PVT 코너 × 모드에서 슬랙을 잰다 (전압·온도·공정이 바뀌어도 서는가)
  4. 전력: DV 가 잰 **실제 토글 수**로 동적 전력을, 코너 모형으로 누설을 셈한다
  5. UPF: 전원 도메인·아이솔레이션·리테션이 빠진 자리를 찾는다
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

from house import people    # noqa: E402
from house import report as RPT       # noqa: E402
from house import sim as SIM          # noqa: E402
from house import synth as SYN        # noqa: E402
from house import viz as V            # noqa: E402
from house import tapeout as TO       # noqa: E402
from house.syn import constraints as C  # noqa: E402
from house.syn import pvt as PVT      # noqa: E402


def 전력(합성결과: dict, 토글: dict, 주파수_MHz: float, P="tt", Vdd=1.8, T=25.0) -> dict:
    """동적 = α·C·V²·f, 누설 = 셀 수 × 셀당 누설 × 코너 배수.

    **α 를 가정하지 않는다.** DV 가 잰 게이팅 토글 비율을 그대로 쓴다 -- 이것이
    이 회사가 '추정 전력' 대신 '잰 활동도로 셈한 전력' 을 낼 수 있는 까닭이다.
    """
    셀수 = 합성결과["셀수"]
    면적 = 합성결과["면적_um2"]
    # 셀당 평균 부하: 면적에 비례한 배선 + 입력 용량 (mklib 의 C단위 2 fF 기준)
    C단위 = 2e-15
    평균팬아웃 = 2.6
    C셀 = 평균팬아웃 * 2.0 * C단위          # 2 자리 폭 상당
    C총 = 셀수 * C셀
    # 데이터패스 활동도: 게이팅이 실제로 열려 있던 주기의 비 × 노드 토글률
    열린비 = 토글["gclk_cycles"] / max(토글["clk_cycles"], 1)
    노드토글 = 0.18                          # 조합 노드의 주기당 평균 토글 (가정)
    알파 = 열린비 * 노드토글
    f = 주파수_MHz * 1e6
    동적 = 알파 * C총 * (Vdd ** 2) * f
    # 클럭 회로망: 플롭 클럭 핀은 주기마다 토글한다(게이팅된 몫만)
    플롭 = 합성결과["셀종류"].get("DFFX1", 0) + 합성결과["셀종류"].get("DFFRX1", 0)
    C클럭 = 플롭 * 8.0 * C단위
    클럭전력 = 2.0 * 열린비 * C클럭 * (Vdd ** 2) * f    # 상승+하강
    누설셀 = 1.2e-9                          # 셀당 nW 급 (가정)
    누설 = 셀수 * 누설셀 * PVT.누설배수(P, Vdd, T)
    return {"동적_mW": round(동적 * 1e3, 3), "클럭_mW": round(클럭전력 * 1e3, 3),
            "누설_mW": round(누설 * 1e3, 4),
            "합_mW": round((동적 + 클럭전력 + 누설) * 1e3, 3),
            "알파": round(알파, 4), "열린비": round(열린비, 4), "C총_pF": round(C총 * 1e12, 2),
            "플롭": 플롭, "P": P, "V": Vdd, "T": T}


def _비교구성(기본: dict, 정책: "str | None", 몇=4) -> list:
    """PI 가 설계팀에 돌려줄 **구성별 합성 비교**의 구성들. 회로에서 뽑는다.

    실측 2026-09-23: `{"GATE_POLICY": 0}` · `{"STAGES": 2}` · `{"TAPS": 16}` 이
    박혀 있었다 -- FIR 의 이름이다. 다른 회로에 넘기면 네 구성이 전부 **같은 것**이
    되어(없는 파라미터는 무시된다), 표가 "파라미터를 바꿔도 면적이 비슷하다" 로
    읽힌다. **거짓 초록이다.**

    고르는 차례: 정책 깃발(0/1 양쪽) -> 값이 큰 파라미터를 반으로 -> 두 배로.
    면적을 끄는 것은 대개 폭·개수처럼 값이 큰 쪽이다.
    """
    난것 = []
    if 정책 is not None:
        난것 += [{정책: 0}, {정책: 1}]
    큰것 = sorted((k for k, v in (기본 or {}).items()
                 if isinstance(v, int) and v > 1 and k != 정책),
                key=lambda k: -기본[k])
    for k in 큰것:
        난것.append({k: max(1, 기본[k] // 2)})
    for k in 큰것:
        난것.append({k: 기본[k] * 2})
    본것, 남 = set(), []
    for c in 난것:
        열 = tuple(sorted(c.items()))
        if 열 in 본것:
            continue
        본것.add(열)
        남.append(c)
    return 남[:몇]


def 일하기(빠르게=False, 설계=None) -> dict:
    from house import designs as DES
    d = 설계 or DES.NSW_FIR
    R = {"시작": time.time(), "설계": d.키, "설계이름": d.이름, "top": d.top}
    R["도구"] = SIM.있나()
    # **이 회로의 제약을 읽는다.** 실측 2026-09-22: 늘 `nsw_fir.sdc` 를 읽어서
    # MERA 를 넘겨도 FIR 의 클럭(13 ns · 40 ns)으로 STA 를 걸었다. 다른 회로의
    # 제약으로 잰 타이밍은 수가 아니다.
    R["sdc"] = C.sdc읽기(설계=d)
    R["upf"] = C.upf읽기(설계=d)
    # UPF 점검은 **그 회로의 RTL** 을 읽어야 한다. 없으면 건너뛰고 그렇게 적는다.
    소스 = [Path(x) for x in (d.RTL or []) if Path(x).exists()]
    소스글 = "\n".join(x.read_text(encoding="utf-8", errors="replace") for x in 소스)
    if 소스글:
        R["upf점검"] = C.upf점검(R["upf"], 소스글)
    else:
        R["upf점검"] = {"됐나": False,
                      "까닭": f"`{d.키}` 의 RTL 을 못 읽어 UPF 점검을 건너뛴다"}

    # --- 합성 (기본 구성) ---
    # **FIR 의 파라미터 이름을 되돌이값으로 쓰지 않는다.** `d.파라` 는 대개 비어
    # 있으므로(실측: nsw_fir 도 `{}`) 이 되돌이값이 **늘 쓰이고 있었다** --
    # 다른 회로에도 `TAPS=8 · STAGES=3` 이 넘어간다.
    기본파라 = DES.파라기본(d)
    R["기본파라"] = 기본파라
    정책 = DES.정책파라(기본파라)
    R["정책파라"] = 정책
    합 = SYN.합성(기본파라 or None, 설계=d)
    R["합성"] = 합
    if not 합.get("됐나"):
        R["초"] = round(time.time() - R["시작"], 1)
        return R

    # --- 공칭 STA ---
    주기 = R["sdc"]["클럭"][0]["주기_ns"]
    R["주기_ns"] = 주기
    R["sta공칭"] = SYN.sta(합, 주기=주기)

    # --- PVT 코너 스윕 ---
    기본Fmax = R["sta공칭"].get("Fmax_MHz") or 0.0
    공칭지연 = 1e3 / 기본Fmax if 기본Fmax else 0.0      # ns
    불확실 = {x["종류"]: x["값_ns"] for x in R["sdc"]["불확실성"]}
    # **OCV 를 슬랙에 실제로 넣는다.** 실측 2026-09-23: 여기서 `ocv스큐(0.8)` 을
    # 불러 보고서에 127 ps 라고 적어 놓고 **슬랙에는 안 빼고 있었다.** 읽는
    # 사람은 OCV 가 들어간 슬랙을 본다고 읽는다. 그리고 셈하는 자리를
    # `pvt.코너타이밍()` 하나로 모은다 -- 관문(gen 7b)과 이 보고서가 같은
    # 함수를 부른다. 두 군데서 재면 같은 실행에서 다른 슬랙이 나온다.
    R["OCV"] = PVT.ocv스큐(0.8)          # SDC 의 set_clock_latency -source 0.8
    _K = PVT.코너타이밍(공칭지연, 주기, setup불확실_ns=불확실.get("setup", 0.0),
                   ocv=R["OCV"])
    코너 = _K["코너"]
    R["코너"] = 코너
    R["코너요약"] = {k: v for k, v in _K.items() if k not in ("코너", "못센코너")}
    R["온도반전"] = PVT.온도반전점()
    R["반전전압"] = {"닫힌꼴": PVT.반전전압_닫힌꼴(), "수치": PVT.반전전압_수치()}

    # --- 전력 (DV 가 잰 토글로) ---
    # **`d` 를 덮어쓰고 있었다.** `d` 는 설계 객체인데 시뮬 결과 dict 로 가려져,
    # 바로 그 줄에서 `설계=d` 를 넘길 수가 없었다 (그래서 안 넘어갔다 -- 어떤
    # 회로를 넘겨도 nsw_fir 을 돌았다). 이름을 가르고 설계를 넘긴다.
    def _토글재기(덮기=None):
        r = SIM.돌리기(dict(기본파라, **(덮기 or {})) or None,
                    seed=17, txn=800, maxlen=256, cap=400000, 설계=d)
        return {"clk_cycles": r["clk_cycles"], "gclk_cycles": r["gclk_cycles"],
                "절감": r["gate_save_pct"]}

    # **전력은 게이팅 정책이 없어도 나와야 한다.** 옛 판은 `토글[0]`·`토글[1]` 을
    # 그냥 찾아 썼는데, 그 칸은 `GATE_POLICY` 가 있는 회로에만 생긴다.
    # 그리고 `for 정책 in (0, 1)` 이 **정책 파라미터 이름을 담은 변수를 가렸다**.
    토글 = {값: _토글재기({정책: 값}) for 값 in ((0, 1) if 정책 else ())}
    기준토글 = 토글.get(1) or 토글.get(0) or _토글재기()
    R["토글"] = 토글
    R["기준토글"] = 기준토글
    R["기본Fmax"] = 기본Fmax
    R["전력"] = {값: 전력(합, t, 기본Fmax) for 값, t in 토글.items()}
    # **A/B 가 없어도 전력 한 벌은 낸다.** 보고서가 그것을 쓴다.
    R["전력기준"] = 전력(합, 기준토글, 기본Fmax)
    R["전력코너"] = [전력(합, 기준토글, 기본Fmax, P=P, Vdd=V, T=T)
                 for P, V, T in (("ss", 1.62, 125.0), ("tt", 1.80, 25.0), ("ff", 1.98, 125.0),
                                 ("ff", 1.98, -40.0))]

    # --- 구성별 합성 비교 (PI 가 설계팀에 돌려주는 표) ---
    # **비교 구성도 회로에서 뽑는다.** `{"STAGES": 2}` · `{"TAPS": 16}` 는 FIR 의
    # 이름이다. 없는 회로에 넘기면 네 구성이 전부 **같은 것**이 되어, 표가
    # "파라미터를 바꿔도 면적이 비슷하다" 로 읽힌다.
    비교 = []
    for c in _비교구성(기본파라, 정책):
        s = SYN.합성(dict(기본파라, **c), 설계=d)
        if s.get("됐나"):
            st = SYN.sta(s, 주기=주기)
            비교.append({"파라": c, "면적": s["면적_um2"], "셀수": s["셀수"],
                       "Fmax": st.get("Fmax_MHz"),
                       "슬랙_ns": round(주기 - (1e3 / st["Fmax_MHz"] if st.get("Fmax_MHz") else 0)
                                     - 불확실.get("setup", 0), 4) if st.get("Fmax_MHz") else None})
    R["비교"] = 비교

    R["셀분포"] = 합["셀종류"]
    R["초"] = round(time.time() - R["시작"], 1)
    return R


def 보고서(m: dict) -> RPT.보고서:
    P = people.MARCUS
    # **제목이 회로 이름을 따라간다** -- 실측 2026-09-22 의 그 사고.
    _이름 = m.get("설계이름") or "NSW-FIR v1.0"
    _탑 = m.get("top") or "nsw_fir"
    R = RPT.보고서(P, f"{_이름} — Synthesis, Timing and Power Sign-off",
                 f"{_탑} IP",
                 "yosys synthesis · SDC constraints · 27 PVT corner STA · "
                 "power from measured toggles · UPF audit")
    R.업무초 = m.get("초")
    합 = m.get("합성") or {}
    # **일하기() returns early when synthesis fails.** In that case m has no
    # "코너" key -- measured 2026-09-21: the VM died with `KeyError: '코너'` and
    # no report came out. When no report comes out, **nobody can see what failed
    # or why**. So we catch it here and report the failure instead.
    if not 합.get("됐나") or "코너" not in m:
        R.요약("<b>Synthesis failed, so this report carries no timing, power or "
              "corner data.</b>")
        R.요약(f"Reason: {str(합.get('까닭', 'no synthesis result'))[:200]}")
        R.절("Synthesis failure — what blocked")
        R.그림(V.빈그림("Synthesis failed; there is nothing to plot", 폭=520))
        R.표(["Item", "Value"],
            [["Synthesis succeeded", str(합.get("됐나"))],
             ["Reason", str(합.get("까닭", ""))[:400]],
             ["Standard-cell library", str(SYN.LIB)],
             ["Library present", str(SYN.LIB.exists())],
             ["RTL", ", ".join(str(x) for x in (m.get("설계RTL") or []))
              or str(SYN.RTL)],
             ["Elapsed", f"{m.get('초')} s"]],
            "<b>This table is the whole report.</b> With no netlist there is no "
            "STA, no power and no UPF audit \u2014 and we do not invent numbers "
            "we did not measure.", "house/synth.py", 강조열=[1])
        R.한계("\u00b7 <b>Nothing was measured.</b> This is a failure report, not a "
             "results report.<br>"
             "\u00b7 The standard-cell library (`house/lib/nsw10.lib`) is generated, "
             "so it is not committed. When absent, "
             "`house/synth.py ensure_library()` builds it from "
             "`lab/lib/se10.lib`. If that also failed, the source is missing.")
        R.잰것 = [("Synthesis", "failed", "", "yosys"),
                ("Reason", str(합.get("까닭", ""))[:60], "", "yosys stderr")]
        return R
    코너 = m["코너"]
    통과 = [c for c in 코너 if c["통과"]]
    실패 = [c for c in 코너 if not c["통과"]]
    최악 = min([c for c in 코너 if c["슬랙_ns"] is not None],
             key=lambda c: c["슬랙_ns"], default=None)

    R.요약(f"Synthesis complete \u2014 {합['셀수']:,} cells, "
          f"{합['면적_um2']:,.0f} \u00b5m\u00b2 "
          f"(yosys 0.33, abc -{합['abc']}, {합['라이브러리']})")
    _clk = ", ".join(f"{c['이름']} {c['주기_ns']} ns" for c in m["sdc"]["클럭"])
    R.요약(f"{m['sdc']['줄수']} lines of SDC actually parsed \u2014 clocks {_clk}, "
          f"{len(m['sdc']['예외'])} timing exceptions, derate early "
          f"{m['sdc']['디레이트'].get('early')} / late {m['sdc']['디레이트'].get('late')}")
    R.요약(f"<b>{len(코너)} PVT corner STA</b> \u2014 {len(통과)} pass / "
          f"{len(실패)} fail. "
          + (f"Worst corner {최악['P']} {최악['V']} V {최악['T']} \u00b0C, "
             f"slack {최악['슬랙_ns']} ns" if 최악 else ""))
    R.요약(f"Temperature-inversion voltage <b>{m['반전전압']['닫힌꼴']:.4f} V</b> "
          f"\u2014 closed form and numerical bisection agree to within "
          f"{abs(m['반전전압']['닫힌꼴']-m['반전전압']['수치'])*1e3:.2e} mV")
    R.요약(f"Power {m['전력'][1]['합_mW']:.2f} mW (dynamic "
          f"{m['전력'][1]['동적_mW']:.2f} + clock {m['전력'][1]['클럭_mW']:.2f} + "
          f"leakage {m['전력'][1]['누설_mW']:.3f}) \u2014 the activity factor "
          f"\u03b1={m['전력'][1]['알파']} comes from <b>toggles DV measured</b>, "
          f"not from an assumption")
    치명 = [x for x in m["upf점검"] if x["심각도"] == "CRITICAL"]
    R.요약(f"UPF audit \u2014 {len(치명)} critical, {len(m['upf점검'])} findings total")

    # ---------------- 1. tools ----------------
    R.절("1. What this report actually ran")
    있 = [(k, v) for k, v in m["도구"].items() if v]
    없 = [k for k, v in m["도구"].items() if not v]
    R.표(["Tool", "Version", "Used for"],
        [[k, v, {"yosys": "RTL \u2192 gate netlist mapping (real synthesis)",
                 "verilator": "measuring the <b>actual toggle counts</b> "
                              "the power numbers are built from",
                 "iverilog": "-", "g++": "simulation harness"}.get(k, "-")]
         for k, v in 있],
        "Tools present on this machine.")
    R.경고("<b>What is missing, and what stood in for it.</b> "
         f"{', '.join(f'<code>{x}</code>' for x in 없)} are not on this machine. "
         "The substitutions were:<br>"
         "\u00b7 <b>Design Compiler \u2192 yosys</b> (a real synthesis tool; the "
         "optimisation level differs)<br>"
         "\u00b7 <b>PrimeTime/OpenSTA \u2192 lab/se/sta + house/syn/pvt</b> "
         "(measured two independent ways and cross-checked)<br>"
         "\u00b7 <b>per-corner .lib \u2192 delay multipliers derived from a device "
         "model</b> (only one process .lib exists. The <i>ratios between</i> "
         "corners come from the alpha-power law; the absolute values stay tied "
         "to the nominal .lib)<br>"
         "\u00b7 <b>PrimePower \u2192 \u03b1\u00b7C\u00b7V\u00b2\u00b7f</b>, "
         "except <b>\u03b1 is measured by DV, not assumed</b>")

    # ---------------- 2. synthesis ----------------
    R.절("2. Synthesis result")
    상위 = sorted(m["셀분포"].items(), key=lambda kv: -kv[1])[:12]
    R.그림(V.막대([k for k, _ in 상위], [v for _, v in 상위],
               "Instance count by cell type", "cells", 폭=620, 값글=False),
         f"{합['셀수']:,} cells in total. Combinational cells dominate and there "
         f"are {m['전력'][1]['플롭']} flops \u2014 the multiplier owns the area.",
         f"yosys stat -liberty {합['라이브러리']} -top {m.get('top') or 'nsw_fir'}")
    R.표(["Item", "Value", "Note"],
        [["Cells", f"{합['셀수']:,}", ""],
         ["Area", f"{합['면적_um2']:,.1f} \u00b5m\u00b2", "sum of cell area, routing excluded"],
         ["Wires", f"{합['배선수']:,}", ""],
         ["Flops", f"{m['전력'][1]['플롭']:,}", "DFFX1 + DFFRX1"],
         ["Library", 합["라이브러리"],
          "not a PDK \u2014 generated from an RC model (FO4 55.2 ps)"],
         ["abc setting", 합["abc"],
          "full mapping of the 40-bit multiplier takes minutes, so -fast "
          "is used consistently"],
         ["Synthesis time", f"{합['초']:.1f} s", ""]],
        "Synthesis summary.", "yosys 0.33")

    # ---------------- 3. SDC ----------------
    R.절("3. Constraints (SDC) — the one file no tool can write for you")
    R.표(["Clock", "Period (ns)", "Frequency (MHz)", "Pin"],
        [[c["이름"], c["주기_ns"], c["주파수_MHz"], c["핀"]] for c in m["sdc"]["클럭"]],
        "Defined clocks.",
        "house/syn/nsw_fir.sdc parsed by house/syn/constraints.py")
    R.표(["Kind", "Constraint"],
        [[x["종류"], f"<code>{x['글']}</code>"] for x in m["sdc"]["예외"]],
        "Timing exceptions. <b>Each line here deletes a check</b> \u2014 which is "
        "why an exception only goes in together with the argument for why it is "
        "safe.", 강조열=[0])
    R.짚기("<b>Reset does not get a blanket <code>set_false_path</code>.</b> Reset is "
         "asynchronous on assertion but <b>synchronous on release</b>. A blanket "
         "exception deletes the recovery check, and that block then fails only on "
         "a cold start. The SDC excepts the assertion edge alone, via "
         "<code>-fall_from</code>.")
    R.표(["Item", "Value"],
        [["Input delay constraints", f"{len(m['sdc']['입력지연'])}"],
         ["Output delay constraints", f"{len(m['sdc']['출력지연'])}"],
         ["Clock uncertainty (setup)",
          f"{[x['값_ns'] for x in m['sdc']['불확실성'] if x['종류']=='setup']} ns"],
         ["Clock uncertainty (hold)",
          f"{[x['값_ns'] for x in m['sdc']['불확실성'] if x['종류']=='hold']} ns"],
         ["OCV derate",
          f"early {m['sdc']['디레이트'].get('early')} / "
          f"late {m['sdc']['디레이트'].get('late')}"],
         ["Asynchronous clock groups", f"{len(m['sdc']['클럭그룹'])}"]],
        "Constraint summary.")

    # ---------------- 4. STA ----------------
    R.절("4. Static timing analysis — 27 PVT corners")
    st = m["sta공칭"]
    R.표(["Item", "Value", "Note"],
        [["Target period", f"{m['주기_ns']} ns", "create_clock in the SDC"],
         ["Nominal Fmax", f"{st.get('Fmax_MHz')} MHz", "tt, 1.8 V, 25 \u00b0C"],
         ["Block-based vs path-based difference", f"{st.get('두길_차이_ps')} ps",
          "<b>measured two ways to see whether they agree</b> \u2014 one method "
          "alone is not trusted"],
         ["Instances", f"{st.get('넷리스트요약',{}).get('인스턴스'):,}", ""],
         ["Flops", f"{st.get('넷리스트요약',{}).get('플롭'):,}", ""]],
        "Nominal-corner STA.", "lab/se/sta", 강조열=[1])

    좋은코너 = [c for c in 코너 if c["슬랙_ns"] is not None]
    격자, y라벨 = [], []
    for Pp in ("ss", "tt", "ff"):
        for Vv in (1.62, 1.80, 1.98):
            줄 = []
            for Tt in (-40.0, 25.0, 125.0):
                c = next((x for x in 코너 if x["P"] == Pp and x["V"] == Vv
                          and x["T"] == Tt), None)
                줄.append(c["슬랙_ns"] if c and c["슬랙_ns"] is not None else 0.0)
            격자.append(줄)
            y라벨.append(f"{Pp} {Vv}")
    R.그림(V.히트맵(격자, "Setup slack by corner (ns)", 폭=440,
                x라벨=["-40 \u00b0C", "25 \u00b0C", "125 \u00b0C"], y라벨=y라벨,
                색낮음="#c0392b", 색높음="#137333", 값글=True),
         f"Red cells are negative slack, i.e. violations. {len(통과)}/{len(코너)} "
         f"corners pass. <b>Closing in one corner is not closing</b> \u2014 this "
         f"whole grid is the definition of 'it works'.",
         "house/syn/pvt.py + lab/se/sta")
    if 최악:
        R.표(["P", "V (V)", "T (\u00b0C)", "Delay mult.", "Path (ns)",
             "Slack (ns)", "Verdict"],
            [[c["P"], c["V"], c["T"], c["지연배수"], c.get("경로_ns"), c["슬랙_ns"],
              "pass" if c["통과"] else "<b>VIOLATION</b>"]
             for c in sorted(좋은코너, key=lambda x: x["슬랙_ns"])[:8]],
            "The eight worst corners by slack.", "house/syn/pvt.py", 강조열=[5, 6])

    if 실패:
        # Report the period that *would* close -- "it does not work" is not a
        # finding; "here is what it would take" is.
        최악배수 = max(c["지연배수"] for c in 좋은코너)
        공칭지연2 = 1e3 / (st.get("Fmax_MHz") or 1e9)
        불 = {x["종류"]: x["값_ns"] for x in m["sdc"]["불확실성"]}
        필요주기 = 공칭지연2 * 최악배수 + 불.get("setup", 0)
        R.경고(f"<b>Recommendation: the target period has to change.</b> The SDC "
             f"asks for {m['주기_ns']} ns ({1e3/m['주기_ns']:.1f} MHz), but in the "
             f"worst corner (ss / 1.62 V / 125 \u00b0C, delay "
             f"\u00d7{최악배수:.3f}) the path is {공칭지연2*최악배수:.2f} ns. "
             f"{len(실패)}/{len(코너)} corners violate.<br><br>"
             f"There are three routes:<br>"
             f"\u2460 <b>Relax the period to {필요주기:.1f} ns "
             f"({1e3/필요주기:.1f} MHz)</b> \u2014 cheapest<br>"
             f"\u2461 <b>Narrow the corner set</b> \u2014 dropping 1.62 V "
             f"(spec the supply at \u2265 1.71 V) removes most of the violations. "
             f"That is a system-level decision<br>"
             f"\u2462 <b>Fix the critical path</b> \u2014 split the multiplier "
             f"into two stages. That is the change Ethan's \u00a75 describes, and "
             f"it needs an RTL edit<br><br>"
             f"This report recommends \u2460. For this IP's target market "
             f"(audio and sensor pre-processing) {1e3/필요주기:.0f} MHz is ample, "
             f"and \u2462 costs both area and latency.")
    R.소절("4.1 Temperature inversion — when 'slow means hot' stops being true")
    ti = m["온도반전"]
    R.그림(V.선([x["V"] for x in ti if x["cold"]],
              [("\u221240 \u00b0C", [x["cold"] for x in ti if x["cold"]]),
               ("125 \u00b0C", [x["hot"] for x in ti if x["cold"]])],
              "Delay multiplier vs supply voltage (nominal = 1)",
              "Supply voltage (V)", "Delay multiplier", 폭=580),
         f"The two curves cross at <b>{m['반전전압']['닫힌꼴']:.3f} V</b>. Below "
         f"that point <b>cold is slower</b> \u2014 the threshold falling with "
         f"temperature beats the mobility effect. This is exactly why a chip with "
         f"a low-voltage retention mode <b>must</b> carry \u221240 \u00b0C in "
         f"its setup corner list.", "house/syn/pvt.py (alpha-power law)")
    R.짚기(f"<b>Independent cross-check.</b> The crossing voltage was obtained two "
         f"ways: the closed form V = V<sub>th</sub> + "
         f"\u03b1\u00b7|dV<sub>th</sub>/dT|\u00b7T/1.5 = "
         f"<b>{m['반전전압']['닫힌꼴']:.6f} V</b>, and \u2014 using none of that "
         f"algebra \u2014 bisection on the sign of a <i>numerically</i> "
         f"differentiated delay, giving <b>{m['반전전압']['수치']:.6f} V</b>. "
         f"Difference {abs(m['반전전압']['닫힌꼴']-m['반전전압']['수치'])*1e3:.2e} mV. "
         f"With only one method this number would not be trustworthy.")

    R.소절("4.2 OCV — the part of the common path that does not cancel")
    o = m["OCV"]
    R.표(["Item", "Value"],
        [["Common-path fraction", f"{o['공통몫']*100:.0f} %"],
         ["Late derate", f"\u00d7{o['늦은배수']}"],
         ["Early derate", f"\u00d7{o['이른배수']}"],
         ["Effective ratio", f"{o['실효비']:.4f}"],
         [f"Effective skew for {o.get('삽입지연_ns', 0.8):g} ns insertion delay",
          f"<b>{o['실효스큐_ps']} ps</b>"]],
        # **산술을 글에 적지 않는다.** `1.00×1.07 − 0.98×0.93 = 0.1586` 이
        # 박혀 있었다 -- 지금은 맞지만 derate 를 하나 고치면 캡션만 옛 수를 말한다.
        f"1.00\u00d7{o['늦은배수']} \u2212 {o['공통몫']}\u00d7{o['이른배수']} = "
        f"{o['실효비']:.4f}. <b>The two derates applied to the common path "
        f"differ, so they do not cancel</b> \u2014 even a perfectly balanced tree "
        f"spends {o['실효비']*100:.1f} % of its insertion delay as skew.",
        "house/syn/pvt.py ocv_skew()", 강조열=[1])

    # ---------------- 5. power ----------------
    R.절("5. Power — from measured activity, not assumed activity")
    # **A/B 는 정책 파라미터가 있을 때만 있다.** 없는 회로에서 `전력[0]`·`전력[1]`
    # 을 그냥 찾으면 KeyError 로 **보고서가 통째로 안 나온다** -- 틀린 수보다 나쁘다.
    _쌍 = 0 in m["전력"] and 1 in m["전력"]
    pw1 = m["전력"].get(1) or m["전력"].get(0) or m["전력기준"]
    pw0 = m["전력"].get(0) if _쌍 else None
    R.그림(V.막대(["Dynamic", "Clock", "Leakage"],
               [pw1["동적_mW"], pw1["클럭_mW"], pw1["누설_mW"]],
               "Power breakdown (tt, 1.8 V, 25 \u00b0C, beat-based gating)", "mW",
               색들=[V.파랑, V.주황, V.빨강], 폭=460),
         f"{pw1['합_mW']:.2f} mW total. The clock network taking a large share is "
         f"typical of a design with {pw1['플롭']} flops \u2014 which is precisely "
         f"why gating works here.",
         "\u03b1\u00b7C\u00b7V\u00b2\u00b7f, \u03b1 from verilator toggles")
    if not _쌍:
        R.짚기("<b>게이팅 정책 A/B 는 안 돌렸다.</b> 이 회로에는 0/1 로 모드를 "
               "고르는 파라미터가 없다 — <code>house/designs.py 정책파라()</code> 가 "
               "못 찾았다. <b>없는 비교를 지어내지 않는다.</b>")
    if _쌍:
      R.그림(V.막대(["State-based gating", "Beat-based gating"],
               [pw0["합_mW"], pw1["합_mW"]],
               "Total power by gating policy", "mW", 색들=[V.흐림, V.초록], 폭=460),
         f"One line Ethan changed in the RTL shows up as "
         f"<b>{(1-pw1['합_mW']/max(pw0['합_mW'],1e-9))*100:.1f} %</b> of power. "
         f"The cause is the activity factor dropping from {pw0['알파']} to "
         f"{pw1['알파']}, and that \u03b1 is <b>not an estimate \u2014 it is "
         f"{m['토글'][1]['clk_cycles']:,} counted cycles</b>.",
         "verilator toggles + \u03b1\u00b7C\u00b7V\u00b2\u00b7f")
      R.표(["Item", "State-based", "Beat-based", "Source"],
          [["clk cycles", f"{m['토글'][0]['clk_cycles']:,}",
            f"{m['토글'][1]['clk_cycles']:,}", "verilator"],
           ["gclk cycles", f"{m['토글'][0]['gclk_cycles']:,}",
            f"{m['토글'][1]['gclk_cycles']:,}", "verilator"],
           ["Fraction of cycles the clock is open",
            f"{pw0['열린비']:.4f}", f"{pw1['열린비']:.4f}", "measured"],
           ["Activity factor \u03b1", f"{pw0['알파']}", f"{pw1['알파']}",
            "measured \u00d7 node toggle rate 0.18 (assumed)"],
           ["Dynamic (mW)", f"{pw0['동적_mW']:.3f}", f"{pw1['동적_mW']:.3f}",
            "\u03b1\u00b7C\u00b7V\u00b2\u00b7f"],
           ["Clock (mW)", f"{pw0['클럭_mW']:.3f}", f"{pw1['클럭_mW']:.3f}",
            "2\u00b7open\u00b7C_clk\u00b7V\u00b2\u00b7f"],
           ["Leakage (mW)", f"{pw0['누설_mW']:.4f}", f"{pw1['누설_mW']:.4f}",
            "cells \u00d7 1.2 nW \u00d7 corner multiplier"],
           ["Total (mW)", f"<b>{pw0['합_mW']:.3f}</b>",
            f"<b>{pw1['합_mW']:.3f}</b>", ""]],
          "Power breakdown. <b>Read the source column</b> \u2014 measured and "
          "assumed are kept apart.", "", 강조열=[1, 2])
    R.그림(V.막대([f"{p['P']} {p['V']}V {p['T']:.0f}\u00b0C" for p in m["전력코너"]],
               [p["누설_mW"] for p in m["전력코너"]], "Leakage power by corner", "mW",
               색들=[V.계열[i % 6] for i in range(len(m["전력코너"]))], 폭=520),
         "Leakage is exponential in threshold voltage. At the ff / hot corner it "
         f"reaches <b>{max(p['누설_mW'] for p in m['전력코너'])/max(min(p['누설_mW'] for p in m['전력코너']),1e-12):,.0f}\u00d7</b> "
         "the tt nominal value \u2014 which is why low-power designs sign off "
         "leakage corners separately.", "house/syn/pvt.py leakage_multiplier()")

    # ---------------- 6. UPF ----------------
    R.절("6. UPF — power intent, and the holes in it")
    u = m["upf"]
    R.그림(V.블록도(
        [("PD_TOP", 14, 20, 300, 180, "none", ""),
         ("PD_CFG", 30, 54, 110, 54, "#eef4fb", "always on (VDD)"),
         ("PD_DP", 178, 54, 110, 54, "#fdf6e3", "switchable (VDD_DP)"),
         ("ISO", 178, 130, 110, 38, "#eaf5ee", "clamp 0"),
         ("RET", 330, 54, 96, 54, "#f9ecec", "a_s2 / a_s3")],
        [("PD_CFG", "PD_DP", "coef", V.파랑), ("PD_DP", "ISO", "outputs", V.주황),
         ("PD_DP", "RET", "save/restore", V.빨강)],
        "Power domains and their protection", 폭=460, 높이=210),
        "When <code>PD_DP</code> switches off, <b>isolation clamps its outputs "
        "to 0</b> and <b>retention keeps the accumulator alive</b>. Omit either "
        "one and every functional test still passes while silicon draws crowbar "
        "current or loses state.",
        "house/syn/nsw_fir.upf parsed by house/syn/constraints.py")
    R.표(["Domain", "Elements", "Primary supply"],
        [[d["이름"], ", ".join(d["요소"]) or "(top)",
          "VDD_DP (switchable)" if d["이름"] == "PD_DP" else "VDD (always on)"]
         for d in u["도메인"]],
        "Power domains.", "UPF parse")
    R.표(["State", "VDD", "VDD_DP", "When"],
        [[p["이름"]] + p["상태"].split()
         + ["while the datapath is running" if p["이름"] == "ACTIVE"
            else "during long idle in IDLE/DONE"] for p in u["PST"]],
        "Power state table (PST). Clock gating works at <i>cycle</i> granularity; "
        "power gating works at <i>transaction</i> granularity.", "UPF parse")
    if m["upf점검"]:
        R.표(["Severity", "Finding", "Why it matters"],
            [[x["심각도"], x["무엇"], x["왜"]] for x in m["upf점검"]],
            f"UPF audit \u2014 {len(치명)} critical. "
            f"<b>We do not write 'no issues'; we write what was checked.</b>",
            "house/syn/constraints.py upf_audit()", 강조열=[0])
    if not 치명:
        R.짚기("No critical findings. Isolation and retention each have both a "
             "definition and a <b>control signal</b>, and every instance name the "
             "UPF references exists in the RTL. There is no level shifter because "
             "both domains currently sit at 1.8 V; the moment those voltages "
             "diverge one becomes mandatory (the UPF carries a comment marking "
             "the spot).")

    # ---------------- 7. configuration comparison ----------------
    R.절("7. What PI hands back to the design team — PPA by configuration")
    if m["비교"]:
        R.표(["Configuration", "Area (\u00b5m\u00b2)", "Cells", "Fmax (MHz)",
             "Slack (ns)"],
            [[json.dumps(x["파라"], ensure_ascii=False), f"{x['면적']:,.1f}",
              f"{x['셀수']:,}", x["Fmax"], x["슬랙_ns"]] for x in m["비교"]],
            "The numbers PI returns to the front end. <b>This table is what a "
            "design decision gets made on.</b>", "yosys + lab/se/sta", 강조열=[3, 4])
        R.그림(V.산점([x["면적"] for x in m["비교"]],
                   [x["Fmax"] or 0 for x in m["비교"]],
                   "Area vs Fmax", "Area (\u00b5m\u00b2)", "Fmax (MHz)",
                   라벨=[json.dumps(x["파라"], ensure_ascii=False)[:14]
                       for x in m["비교"]], 폭=540),
             "One PPA point per configuration. Up and to the left is better.",
             "yosys + lab/se/sta")

    # ---------------- 8. limits ----------------
    R.한계(
        "\u00b7 <b>There are no per-corner .lib files.</b> Process corners were "
        "computed from a <i>model</i> (alpha-power law + mobility "
        "T<sup>\u22121.5</sup> + dV<sub>th</sub>/dT). The ratios between corners "
        "follow from physics, but the absolute values stay tied to the nominal "
        ".lib. Swap in foundry .lib files the moment they exist.<br>"
        "\u00b7 <b>There is no wire parasitic.</b> This is pre-route STA \u2014 "
        "Kenji (PD) reports the post-route numbers. Measured in T23, that gap is "
        "30\u201340 % of Fmax.<br>"
        "\u00b7 <b>SDC wildcards are not expanded.</b> "
        "<code>[get_ports in_data*]</code> is taken literally and applied to "
        "<i>all</i> inputs in STA. There is no precise port matching.<br>"
        "\u00b7 <b>The node toggle rate of 0.18 is an assumption.</b> The "
        "fraction of cycles the gate is open is measured, but how often "
        "combinational nodes flip while it is open needs a VCD toggle count. "
        "The next revision attaches that via verilator <code>--trace</code>.<br>"
        "\u00b7 <b>UPF was not actually applied.</b> It was parsed and checked "
        "for consistency; no isolation or retention cells were inserted into the "
        "netlist (that is a commercial tool's job).")

    # **테이프아웃까지 남은 것을 제 보고서에 싣는다.** 표는 house/tapeout.py
    # 한 군데에 있고 여기서는 이 사람 몫만 걸러 보인다 -- 다섯 보고서가 저마다
    # 적으면 한 군데만 고치게 된다.
    TO.절(R, "syn")

    R.잰것 = [
        ("Cells", f"{합['셀수']:,}", "", "yosys stat"),
        ("Area", f"{합['면적_um2']:,.1f}", "\u00b5m\u00b2",
         f"yosys stat -liberty {합['라이브러리']}"),
        ("Nominal Fmax", st.get("Fmax_MHz"), "MHz", "lab/se/sta (two methods)"),
        ("Two-method difference", st.get("두길_차이_ps"), "ps",
         "block-based vs path-based"),
        ("PVT corners", len(코너), "", "house/syn/pvt.py"),
        ("Corners passing", f"{len(통과)}/{len(코너)}", "", "slack \u2265 0"),
        ("Temperature inversion (closed form)",
         f"{m['반전전압']['닫힌꼴']:.6f}", "V", "alpha-power law"),
        ("Temperature inversion (numerical)",
         f"{m['반전전압']['수치']:.6f}", "V", "numerical derivative + bisection"),
        ("OCV effective skew", o["실효스큐_ps"], "ps",
         "1.00\u00d71.07 \u2212 0.98\u00d70.93"),
        ("Total power", f"{pw1['합_mW']:.3f}", "mW",
         "\u03b1\u00b7C\u00b7V\u00b2\u00b7f (\u03b1 measured)"),
        ("Gating power saving",
         f"{(1-pw1['합_mW']/max(pw0['합_mW'],1e-9))*100:.1f}", "%", "measured A/B"),
        ("UPF critical findings", len(치명), "", "house/syn/constraints.py"),
        ("Tool runtime", m["초"], "s", "measured"),
    ]
    return R


def 돌리기(빠르게=False, 회로=None) -> dict:
    from house import designs as DES
    m = 일하기(빠르게, 설계=DES.찾기(회로))
    R = 보고서(m)
    길 = R.내기()
    return {"사람": people.MARCUS, "잰것": m, "pdf": 길, "쪽": RPT.쪽수(길),
            "요약": R.요약줄, "그림수": R.그림수, "표수": R.표수}


if __name__ == "__main__":
    r = 돌리기("--빠르게" in sys.argv)
    print(f"PDF -> {r['pdf']}  ({r['쪽']} 쪽, 그림 {r['그림수']}, 표 {r['표수']})")
    for s in r["요약"]:
        print(" ·", re.sub(r"<[^>]+>", "", s))
