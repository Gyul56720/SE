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

import re
import json
import sys
import time
import traceback
from pathlib import Path

뿌리 = Path(__file__).resolve().parent
저장소 = 뿌리.parent
sys.path.insert(0, str(저장소))

from house import people    # noqa: E402
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


def 설계하기(요청: str, 메일: bool = False, to=None) -> dict:
    """자연어 요청 -> 제안서.  **RTL 은 짓지 않는다** -- 사람이 승인해야 짓는다.

    제안서도 **메일로 나간다.** 사용자(2026-09-21): "이메일로 보고서 자동으로 보내야지."
    백그라운드로 도는 일의 결과를 사람이 보려면 채널을 다시 뒤지거나 `!회사 상태` 를
    쳐야 했다 -- 다 된 보고서가 디스크에만 남아 있는 것은 낸 것이 아니다.
    """
    from house import arch as ARCH
    r = ARCH.돌리기(요청)
    r.setdefault("사람", people.ETHAN)     # 스펙에서 RTL 로 가는 자리가 Ethan 이다
    # **사람 글을 그대로 제목에 넣지 않는다.** 이 값이 메일 제목이 된다.
    # `.strip()[:60]` 은 가운데 줄바꿈을 그대로 남기고, 실측 2026-09-22 에 그것이
    # 메일을 터뜨렸다 -- 제안서는 멀쩡히 나왔는데:
    #
    #     ValueError: Header values may not contain linefeed or carriage return characters
    #
    # 자연어 요청이 회사에 바로 닿게 되면서(#356) 요청이 **여러 줄**로 들어온 것이다.
    # `mailer.바깥글()` 이 줄바꿈을 누르고 대괄호를 괄호로 바꾼다(자리표 관문).
    import mailer as _M
    r.setdefault("과제", _M.바깥글(요청, 60) or "새 회로")
    r["키"] = "arch"
    if 메일:
        m = 메일보내기(r, to=to, 특이사항=_제안서특이사항(r))
        r["메일"] = m
        print(f"    메일: {m}", flush=True)
    _적기({"키": "arch", "이름": "설계 제안서", "됐나": True, "pdf": str(r["pdf"]),
         "쪽": r.get("쪽"), "요청": 요청[:200], "선행조사": str(r.get("선행조사")),
         "메일": bool(메일) and bool(r.get("메일", {}).get("됐나"))})
    return r


def _제안서특이사항(r: dict) -> list:
    """제안서 메일의 2번 항목. **아직 모르는 칸을 맨 앞에 올린다** -- 그것이 사람이
    해야 할 일의 전부이고, 안 올리면 첨부를 안 열고 '됐구나' 로 읽힌다."""
    줄 = [f"This is a proposal, not a design. No RTL has been written yet.",
         f"Report: {r.get('쪽', '?')} pages, {r.get('그림수', '?')} figures."]
    for x in (r.get("모른다") or [])[:6]:
        줄.append("Needs your decision: " + str(x))
    if r.get("선행조사"):
        줄.append(f"Prior-art file: {r['선행조사']}")
    return 줄


# **누가 회로를 받고 누가 못 받는지 묻는 길.**
#
# 실측 2026-09-22. 사용자가 MERA 스펙을 넣고 다섯 명을 돌렸는데 **`NSW-FIR v1.0`
# 보고서 13쪽**이 왔다. 따라가 보니 끊긴 데가 세 겹이었다.
#
#   1. `!회사 전체` 가 `--회로` 를 안 넘겼다           (고침)
#   2. `한명()` 이 넘기려 해도 **에이전트가 그 인자를 안 받는다** (TypeError)
#   3. 그래서 기본 회로로 돌고, 그 사실이 **로그에만** 적혔다
#
# 3번이 가장 나쁘다. 사람은 제 스펙이 돈 줄 알고 13쪽을 읽는다. 제목이
# `NSW-FIR` 인 것을 봐도 "회사가 붙인 이름인가" 로 읽힌다 -- 다른 회로라고
# 아무 데도 안 적혀 있으니까.
#
# **못 하는 것을 못 한다고 말하는 길을 먼저 낸다.** 다섯 에이전트를 회로마다
# 돌게 만드는 것은 각자의 RTL·테스트벤치·분석이 걸린 큰 일이고, 그 전에
# **엉뚱한 보고서 다섯 장을 내는 것부터 막아야 한다.**
def 회로를받나(키: str) -> bool:
    """그 직무의 `돌리기()` 가 `회로=` 를 받나. 못 물어보면 **안 받는 것으로 본다**."""
    import importlib
    import inspect
    if 키 not in 직무:
        return False
    try:
        m = importlib.import_module(직무[키][0])
        서명 = inspect.signature(getattr(m, 직무[키][1]))
    except Exception:                                        # noqa: BLE001
        return False
    p = 서명.parameters.get("회로")
    return p is not None or any(
        x.kind is inspect.Parameter.VAR_KEYWORD for x in 서명.parameters.values())


def 회로되는사람들() -> dict:
    """{직무키: 받나}. 봇이 **돌리기 전에** 물어서 사람에게 말한다."""
    return {k: 회로를받나(k) for k in 직무}


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
    # **`회로=` 를 받는지는 서명으로 본다. TypeError 로 판단하지 않는다.**
    #
    # 실측 2026-09-25: 옛 판은 `except TypeError` 로 잡아서 기본 회로로 넘어갔다.
    # 그런데 에이전트 **안에서** 난 TypeError(`sum(None)`)도 똑같이 잡혔고,
    # aim_chain 을 맡겼는데 **FIR 보고서가 그 이름표를 달고 나왔다.**
    # 안에서 난 오류를 '인자를 못 받는다' 로 읽는 것은 거짓 초록을 만드는 길이다.
    import inspect as _insp
    받나 = 회로를받나(키)
    if 회로 and not 받나:
        print(f"!! {키}: `회로=` 를 안 받는다 -- 기본 회로로 돌린다", flush=True)
    r = 함(*인자, 회로=회로) if (회로 and 받나) else 함(*인자)
    if not isinstance(r, dict):                  # 예전 꼴 -- 경로만 돌려주던 것
        r = {"pdf": r}
    r.setdefault("사람", people.BY_KEY[키])
    r["키"] = 키
    r["초"] = round(time.time() - t0, 1)
    return r


def 승인하기(키: str = "", 바퀴: int = 3, 메일: bool = False, to=None,
          누가: str = "") -> dict:
    """**사람이 승인한 스펙으로 RTL·TB 를 짓는다.** 제안서 다음 칸이다.

    사용자(2026-09-22): 제안서를 보고 "하나로 진행" -- 이대로 승인.
    그런데 그 칸을 탈 길이 없었다. 흐름 그림에는 `사람 승인 -> RTL·TB 생성` 이
    있는데 명령이 없었고, `!회사 rtl` 은 **고정 회로**를 돌릴 뿐 승인한 스펙을
    안 본다. 그림이 약속한 것을 코드가 안 하고 있었다.

    **제안서를 낸 그 스펙 그대로 짓는다**(`arch.스펙두기` 가 둔 것). 요청 글을
    다시 읽지 않는다 -- 다시 읽으면 모델이 또 다르게 채우고, 그러면 **사람이 본
    것과 다른 것을 짓게 된다.**

    관문은 `gen.짓기` 안에 있다(몇 개인지는 `gen.관문번호들()` 이 센다). 하나라도 빨가면 **등록하지 않는다** --
    반쯤 된 RTL 위에 다음 단계를 쌓지 않는다.
    """
    t0 = time.time()
    from house import arch as ARCH
    from house import gen as GEN
    키 = (키 or "").strip()
    if not 키:
        둔것 = ARCH.둔스펙들()
        if len(둔것) != 1:
            return {"됐나": False, "까닭":
                    ("승인할 제안서가 없다 -- 먼저 `!회사 설계 <요청>` 을 돌려라"
                     if not 둔것 else
                     f"둔 스펙이 {len(둔것)}개다. 어느 것인지 대라: {', '.join(둔것)}"),
                    "둔것": 둔것}
        키 = 둔것[0]
    s = ARCH.스펙꺼내기(키)
    if s is None:
        return {"됐나": False, "까닭": f"`{키}` 로 둔 스펙이 없다", "둔것": ARCH.둔스펙들()}
    쓸 = GEN.쓸수있나()
    if not 쓸["됨"]:
        # **못 지으면 못 짓는다고 한다.** 빈 RTL 을 내놓지 않는다.
        return {"됐나": False, "까닭": 쓸["말"], "키": 키}
    # **승인 이력을 먼저 남긴다.** 관문 0 이 이것을 본다 -- 없으면 안 짓는다.
    # 누가 승인했는지는 **증명하지 못한다**(디스코드 이름을 적을 뿐이다).
    # 이 기록이 죄는 것은 *사람이 본 제안서와 지금 짓는 스펙이 같은가* 다.
    from house import approve as AP
    적 = AP.승인적기(키, 누가 or "(이름 없음)")
    if not 적.get("됐나"):
        return {"됐나": False, "까닭": f"승인 이력을 못 남겼다 -- {적.get('까닭')}",
                "키": 키}
    주기 = 10.0
    for 목 in (s.목표 or []):
        m = re.search(r"([\d.]+)\s*(?:MHz|㎒)", str(목.get("값", "")), re.I)
        if m:
            try:
                주기 = 1000.0 / float(m.group(1))       # MHz -> ns
            except (ValueError, ZeroDivisionError):
                pass
            break
    r = GEN.짓기(s, 키, 바퀴=바퀴, 주기_ns=주기)
    r["키"] = 키
    r["초"] = round(time.time() - t0, 1)
    r["주기_ns"] = 주기
    _원장적기({"키": f"gen:{키}", "됐나": r.get("됐나"), "바퀴수": r.get("바퀴수"),
             "top": r.get("top"), "RTL": r.get("RTL"), "TB": r.get("TB"),
             "초": r["초"]})
    return r


def _원장적기(줄: dict):
    try:
        원장.parent.mkdir(parents=True, exist_ok=True)
        줄 = dict(줄, 때=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        with open(원장, "a", encoding="utf-8") as f:
            f.write(json.dumps(줄, ensure_ascii=False) + "\n")
    except OSError:
        pass


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
        attachment_name=pdf.name)
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
    # **다섯이 줄줄이 같은 까닭으로 죽기 전에 한 번 묻는다.**
    _p = RPT.PDF된다()
    if not _p["된다"]:
        print(f"!! PDF 를 못 만든다: {_p['까닭']}\n   고치는 법: {_p['고치는법']}\n"
              f"   (그래도 돌린다 -- HTML 은 남는다)", flush=True)
    try:
        from house import synth as _SYN
        _l = _SYN.라이브러리확인()
        if not (_l["있었나"] or _l["만들었나"]):
            print(f"!! 표준셀 라이브러리가 없다: {_l.get('까닭', '')}\n"
                  f"   -> 합성·STA·DFT·PD 가 전부 막힌다", flush=True)
        elif _l["만들었나"]:
            print(f"·  표준셀 라이브러리를 새로 만들었다: {_l['길']}", flush=True)
    except Exception as _e:                                  # noqa: BLE001
        print(f"!! 라이브러리 확인 실패: {type(_e).__name__}: {_e}", flush=True)
    낸것 = []
    for k in 키들:
        p = people.BY_KEY[k]
        print(f"\n=== {p.name} ({p.team}) 시작 ===", flush=True)
        try:
            r = 한명(k, 빠르게, 회로=회로)
        except Exception as e:                               # noqa: BLE001
            print(f"!!! {p.name} 실패: {type(e).__name__}: {e}", flush=True)
            traceback.print_exc()
            낸것.append({"키": k, "사람": p, "됐나": False,
                       "까닭": f"{type(e).__name__}: {e}"[:300]})
            _적기({"키": k, "이름": p.name, "됐나": False,
                 "까닭": f"{type(e).__name__}: {e}"[:300]})
            continue
        r["됐나"] = True
        print(f"--- {p.name}: {r['pdf']} ({r.get('쪽')}쪽, "
              f"그림 {r.get('그림수')}, 표 {r.get('표수')}, {r['초']} s)", flush=True)
        if 메일:
            m = 메일보내기(r, to=to)
            r["메일"] = m
            print(f"    메일: {m}", flush=True)
        낸것.append(r)
        _적기({"키": k, "이름": p.name, "됐나": True, "pdf": str(r["pdf"]),
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
    줄 = [f"**{people.COMPANY}** — 이번 실행 {len(낸것)}명"]
    for r in 낸것:
        p = r["사람"]
        if not r.get("됐나"):
            줄.append(f"· ❌ **{p.name}** ({p.team}) — 실패: {r.get('까닭')}")
            continue
        메 = r.get("메일")
        꼬 = ""
        if 메 is not None:
            꼬 = " · 📧 보냄" if 메.get("됐나") else f" · 📧 못 보냄({메.get('까닭', '')[:40]})"
        줄.append(f"· ✅ **{p.name}** ({p.team}) — `{Path(r['pdf']).name}` "
                 f"{r.get('쪽')}쪽 / 그림 {r.get('그림수')} / 표 {r.get('표수')} / {r['초']}s{꼬}")
    return "\n".join(줄)


# **깃발은 이름으로 안다 -- 생김새로 알지 않는다.**
#
# 실측 2026-09-22. 첨부를 이어 붙인 요청은 이렇게 시작한다:
#
#     ----- 첨부: 1551960619576459374_spec.md -----
#     # MERA-1 v1.0 Event Recorder Core ...
#
# 이것은 argv 한 덩어리인데 `--` 로 시작한다. 그래서 `x.startswith("--")` 로 깃발을
# 거르던 줄이 **요청 전체를 버렸다.** 요청이 빈 글이 되어 종료코드 2 로 즉사했고,
# 디스코드에는 "못 띄웠다" 만 떴다 -- 2,851자를 제대로 읽어 놓고 그 다음 칸에서 졌다.
#
# 생김새로 거르면 사용자 글이 깃발처럼 보이는 날 진다. 이름으로 거른다.
_깃발 = {"--메일", "--메일없이", "--빠르게", "--전부", "--설계", "--승인", "--회로",
       "--누가"}


def 요청읽기(av: "list[str]") -> "str | None":
    """`--설계` 의 값. 깃발이 없으면 None, 있는데 비었으면 빈 글.

    **이 조각이 함수인 까닭**: 첫 판은 `__main__` 안에 있었고, 그래서 검사가 닿지
    못했다. 닿지 못하는 자리에서 요청 전체를 버리는 버그가 났다(실측 2026-09-22).
    두 꼴을 다 받는다 -- `--설계 <글…>` 과 `--설계=<글>`.
    """
    for i, x in enumerate(av):
        if x == "--설계":
            return " ".join(y for y in av[i + 1:] if y not in _깃발).strip()
        if x.startswith("--설계="):
            return x[len("--설계="):].strip()
    return None


if __name__ == "__main__":
    av = sys.argv[1:]
    # 두 꼴을 다 받는다. `--설계=<글>` 은 그 글이 그 깃발의 값이라는 것이 argv 안에서
    # 확정되므로 **글이 무엇으로 시작하든 안 잃는다** -- 봇은 이 꼴로 준다.
    요청 = 요청읽기(av)
    if 요청 is not None:
        if not 요청:
            print("!! `--설계` 뒤에 무엇을 만들지 적어라")
            raise SystemExit(2)
        r = 설계하기(요청, 메일=("--메일" in sys.argv))
        print(f"제안서 -> {r['pdf']}  ({r.get('쪽')} 쪽, 그림 {r.get('그림수')}, "
              f"표 {r.get('표수')})")
        print(f"선행조사 -> {r.get('선행조사')}")
        for t in (r.get("요약") or []):
            print(" · " + t.replace("<b>", "").replace("</b>", ""))
        raise SystemExit(0)
    if "--승인" in av:
        i = av.index("--승인")
        키 = av[i + 1] if i + 1 < len(av) and av[i + 1] not in _깃발 else ""
        _누 = [a.split("=", 1)[1] for a in av if a.startswith("--누가=")]
        r = 승인하기(키, 메일=("--메일" in sys.argv), 누가=(_누[0] if _누 else ""))
        if not r.get("됐나"):
            print(f"!! 못 지었다: {r.get('까닭')}")
            for 바 in (r.get("이력") or [])[-2:]:
                print(f"   바퀴 {바.get('바퀴')}: {바.get('오류') or 바.get('관문')}")
            raise SystemExit(1)
        print(f"RTL -> {r.get('RTL')}\nTB  -> {r.get('TB')}")
        from house import gen as _G
        print(f"관문 {len(_G.관문번호들())}개 통과 · {r.get('바퀴수')} 바퀴 · {r.get('초')} s "
              f"· 목표 주기 {r.get('주기_ns')} ns")
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
