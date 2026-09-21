# -*- coding: utf-8 -*-
"""house/run -- 다섯 명을 돌리고, 보고서를 내고, 메일로 보낸다.

    python3 house/run.py                 다섯 명 전부 (오래 걸린다)
    python3 house/run.py rtl dv          고른 사람만
    python3 house/run.py --빠르게        각 에이전트의 빠른 설정으로
    python3 house/run.py --메일 rtl      끝나고 메일까지 (첨부 = 그 PDF)

**메일을 먼저 보내고 일하지 않는다.** 보고서 PDF 가 실제로 생긴 뒤에만 보낸다 --
house/report.py 의 `보내기_첨부` 가 첨부 없는 발송을 거부한다(이 회사는 글만 보내지
않는다). 그림이 0 장인 보고서도 거부된다(house/report.py 의 `html()`).
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

뿌리 = Path(__file__).resolve().parent
저장소 = 뿌리.parent
sys.path.insert(0, str(저장소))

from house import people as 사람들    # noqa: E402
from house import report as RPT       # noqa: E402

원장 = 뿌리 / "ledger.jsonl"

# 키 -> (모듈경로, 함수이름).  늦게 들인다 -- 한 사람만 돌릴 때 다섯 벌을 안 물린다.
직무 = {
    "rtl": ("house.rtl.agent", "돌리기"),
    "dv":  ("house.dv.agent", "돌리기"),
    "syn": ("house.syn.agent", "돌리기"),
    "dft": ("house.dft.agent", "돌리기"),
    "pd":  ("house.pd.agent", "돌리기"),
}
차례 = ["rtl", "dv", "syn", "dft", "pd"]      # 흐름 순서 (설계 -> 검증 -> 합성 -> DFT -> PD)


def 설계하기(요청: str) -> dict:
    """자연어 요청 -> 제안서.  **RTL 은 짓지 않는다** -- 사람이 승인해야 짓는다."""
    from house import arch as ARCH
    r = ARCH.돌리기(요청)
    _적기({"키": "arch", "이름": "설계 제안서", "됐나": True, "pdf": str(r["pdf"]),
         "쪽": r.get("쪽"), "요청": 요청[:200], "선행조사": str(r.get("선행조사"))})
    return r


def 한명(키: str, 빠르게=False, 회로=None) -> dict:
    import importlib
    if 키 not in 직무:
        raise KeyError(f"모르는 직무: {키}")
    모듈이름, 함수 = 직무[키]
    m = importlib.import_module(모듈이름)
    t0 = time.time()
    # **DV 만 인자 꼴이 다르다.** 검증은 '빠르게/보통/밤새' 라는 규모를 받는다 --
    # 수만 번 던지는 것이 이 직무의 본업이라 켜고 끄는 값이 아니라 눈금이다.
    함 = getattr(m, 함수)
    인자 = ("빠르게" if 빠르게 else "보통",) if 키 == "dv" else (빠르게,)
    try:
        r = 함(*인자, 회로=회로) if 회로 else 함(*인자)
    except TypeError:
        # 아직 회로 인자를 안 받는 에이전트 -- 기본 회로로 돈다. **조용히 넘어가지 않는다.**
        if 회로:
            print(f"!! {키}: 아직 `회로=` 를 안 받는다 -- 기본 회로로 돌린다", flush=True)
        r = 함(*인자)
    if not isinstance(r, dict):                  # 예전 꼴 -- 경로만 돌려주던 것
        r = {"pdf": r}
    r.setdefault("사람", 사람들.키로[키])
    r["키"] = 키
    r["초"] = round(time.time() - t0, 1)
    return r


def 메일보내기(r: dict, 특이사항=None, to=None) -> dict:
    p = r["사람"]
    pdf = Path(r["pdf"])
    if not pdf.exists():
        return {"됐나": False, "보냈나": False, "까닭": f"보고서 PDF 가 없다: {pdf}"}
    과제 = r.get("과제") or "NSW-FIR v1.0"
    제목 = RPT.메일제목(p, 과제)
    본문 = RPT.메일본문(
        p, 과제,
        [s.replace("<b>", "").replace("</b>", "") for s in (r.get("요약") or [])],
        특이사항 or _특이사항(r),
        첨부이름=pdf.name)
    r = RPT.보내기(p, 제목, 본문, [pdf], to=to)
    # mailer 는 {"보냈나": ...} 로 답한다. 위쪽은 "됐나" 로 읽으므로 맞춰 준다.
    if "됐나" not in r:
        r = dict(r, 됐나=bool(r.get("보냈나")),
                 까닭=r.get("말") or ", ".join(r.get("필요한것") or []))
    return r


def _특이사항(r: dict) -> list:
    """보고서가 '못 닫았다' 고 적은 것을 메일 2번 항목으로 올린다.

    **메일에 좋은 소식만 적지 않는다.** 보고서 안에 경고를 적어 두고 메일에는
    안 적으면, 읽는 사람은 첨부를 안 열고 '됐구나' 로 읽는다.
    """
    줄 = [f"보고서 {r.get('쪽', '?')}쪽, 그림 {r.get('그림수', '?')}장, "
         f"표 {r.get('표수', '?')}개. 모든 그림은 실제 실행 결과에서 그렸습니다.",
         f"도구 실행 시간 {r.get('초')} s."]
    for s in (r.get("요약") or []):
        t = s.replace("<b>", "").replace("</b>", "")
        if any(k in t for k in ("못", "실패", "미달", "안 ", "남은")):
            줄.append("확인 요청: " + t)
    return 줄


def 돌리기(키들=None, 빠르게=False, 메일=False, to=None, 회로=None) -> list:
    키들 = [k for k in (키들 or 차례) if k in 직무] or 차례
    낸것 = []
    for k in 키들:
        p = 사람들.키로[k]
        print(f"\n=== {p.이름} ({p.팀}) 시작 ===", flush=True)
        try:
            r = 한명(k, 빠르게, 회로=회로)
        except Exception as e:                               # noqa: BLE001
            print(f"!!! {p.이름} 실패: {type(e).__name__}: {e}", flush=True)
            traceback.print_exc()
            낸것.append({"키": k, "사람": p, "됐나": False,
                       "까닭": f"{type(e).__name__}: {e}"[:300]})
            _적기({"키": k, "이름": p.이름, "됐나": False,
                 "까닭": f"{type(e).__name__}: {e}"[:300]})
            continue
        r["됐나"] = True
        print(f"--- {p.이름}: {r['pdf']} ({r.get('쪽')}쪽, "
              f"그림 {r.get('그림수')}, 표 {r.get('표수')}, {r['초']} s)", flush=True)
        if 메일:
            m = 메일보내기(r, to=to)
            r["메일"] = m
            print(f"    메일: {m}", flush=True)
        낸것.append(r)
        _적기({"키": k, "이름": p.이름, "됐나": True, "pdf": str(r["pdf"]),
             "쪽": r.get("쪽"), "그림": r.get("그림수"), "표": r.get("표수"),
             "초": r["초"], "메일": bool(메일) and r.get("메일", {}).get("됐나")})
    return 낸것


def _적기(줄: dict) -> None:
    원장.parent.mkdir(parents=True, exist_ok=True)
    줄 = dict(줄)
    줄.setdefault("때", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    with open(원장, "a", encoding="utf-8") as f:
        f.write(json.dumps(줄, ensure_ascii=False) + "\n")


def 요약글(낸것: list) -> str:
    줄 = [f"**{사람들.회사}** — 이번 실행 {len(낸것)}명"]
    for r in 낸것:
        p = r["사람"]
        if not r.get("됐나"):
            줄.append(f"· ❌ **{p.이름}** ({p.팀}) — 실패: {r.get('까닭')}")
            continue
        메 = r.get("메일")
        꼬 = ""
        if 메 is not None:
            꼬 = " · 📧 보냄" if 메.get("됐나") else f" · 📧 못 보냄({메.get('까닭', '')[:40]})"
        줄.append(f"· ✅ **{p.이름}** ({p.팀}) — `{Path(r['pdf']).name}` "
                 f"{r.get('쪽')}쪽 / 그림 {r.get('그림수')} / 표 {r.get('표수')} / {r['초']}s{꼬}")
    return "\n".join(줄)


if __name__ == "__main__":
    av = sys.argv[1:]
    if "--설계" in av:
        요청 = " ".join(av[av.index("--설계") + 1:]).strip()
        if not 요청:
            print("!! `--설계` 뒤에 무엇을 만들지 적어라")
            raise SystemExit(2)
        r = 설계하기(요청)
        print(f"제안서 -> {r['pdf']}  ({r.get('쪽')} 쪽, 그림 {r.get('그림수')}, "
              f"표 {r.get('표수')})")
        print(f"선행조사 -> {r.get('선행조사')}")
        for t in (r.get("요약") or []):
            print(" · " + t.replace("<b>", "").replace("</b>", ""))
        raise SystemExit(0)
    회 = None
    if "--회로" in av:
        i = av.index("--회로")
        회 = av[i + 1] if i + 1 < len(av) else None
        av = av[:i] + av[i + 2:]
    인자 = [a for a in av if not a.startswith("--")]
    낸 = 돌리기(인자 or None, 빠르게=("--빠르게" in sys.argv),
             메일=("--메일" in sys.argv), 회로=회)
    print("\n" + 요약글(낸))
