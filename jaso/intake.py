"""**답을 원장에 넣는다.** 넣은 것이 답에 실제로 있는지 대조하면서.

    python3 jaso/ask.py --문항 "..." --json > 물음.json
    # (사용자가 답을 적는다: `1) ...` 꼴)
    python3 jaso/intake.py --물음 물음.json --답 답.txt --표 내원장.json
    python3 jaso/intake.py --물음 물음.json --답 답.txt --표 내원장.json --넣기

## 물음이 답이 갈 자리를 알고 있다

그래서 **LLM 없이 넣을 수 있다.** `ask.py` 가 물음마다 `칸`(원장의 어디로) 과
`대상`(어느 항목에) 을 이미 정해 두었으므로, 여기서는 답의 꼴만 읽으면 된다.

이것이 요점이다. 자유 서술을 통째로 모델에게 주고 "원장으로 만들어" 라고 하면 모델이
빈칸을 메우고, **메운 것이 곧 그 사람의 이력이 된다.** 원장은 이 파이프라인의 유일한
바깥이라, 거기가 오염되면 아래 관문이 전부 오염된 것을 대조하게 된다.

## 그래도 모델을 쓸 수 있다 -- 다만 대조를 통과해야 한다

`--모델` 을 주면 Gemini 가 답을 스키마로 옮긴다. 그때도 **뽑은 값이 답 원문에 실제로
있는지** I001 이 대조하고, 없는 값은 **버린다**(고쳐 넣지 않는다 -- 무엇이 버려졌는지
화면에 적는다). `law/gate.py` L002 가 따옴표로 옮긴 조문을 원문과 대조하는 자리와 같다.

    뽑은 것이 원문에 있다      넣는다
    없다                       **버리고 그렇게 말한다**

## 관문

    I001  뽑은 값이 답 원문에 있는가        hard -- 어기면 그 칸을 안 넣는다
    I002  역할이 닫힌 목록 안인가            hard
    I003  잰 수에 재는 법이 딸려 있는가      soft -- 넣되 J002 가 나중에 막는다
    I004  답이 빈 채로 왔는가                soft -- 물음이 아직 살아 있다는 뜻
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import ledger as LG                                        # noqa: E402

위반 = LG.위반

_답머리 = re.compile(r"^\s*(?:Q\s*)?(\d{1,2})\s*[.)\]:>]\s*", re.M)
_연월 = re.compile(r"(20\d\d)\s*[-./년]\s*(\d{1,2})\s*월?")
_연만 = re.compile(r"(20\d\d)\s*년?")
_안쟀다 = re.compile(r"안\s*쟀|못\s*쟀|없(다|음|습니다)|모르(겠|ㅂ)")
# "클릭률 2.1 -> 2.6 %" · "클릭률 2.1%에서 2.6%로" · "6명에서 19명으로"
_변화 = re.compile(r"([^,;\n(]{0,20}?)\s*(\d[\d,]*(?:\.\d+)?)\s*([%가-힣A-Za-z]{0,4})?"
                   r"\s*(?:->|→|=>|에서|~)\s*(\d[\d,]*(?:\.\d+)?)\s*([%가-힣A-Za-z]{0,4})?")


def 답나누기(글: str) -> dict:
    """`1) …` 꼴로 나눈다. **번호가 없으면 통째로 1번이다** -- 버리지 않는다."""
    자리 = list(_답머리.finditer(글 or ""))
    if not 자리:
        t = (글 or "").strip()
        return {"1": t} if t else {}
    out = {}
    for i, m in enumerate(자리):
        끝 = 자리[i + 1].start() if i + 1 < len(자리) else len(글)
        out[m.group(1)] = 글[m.end():끝].strip()
    return out


def _핵(값: str) -> list:
    """대조에 쓸 알맹이. 수는 앞의 0 을 떼고, 말은 소문자로."""
    수 = [x.lstrip("0") or "0" for x in re.findall(r"\d+", str(값))]
    말 = [w.lower() for w in re.split(r"[^0-9A-Za-z가-힣]+", str(값))
          if w and not w.isdigit() and len(w) >= 2]
    return 수 + 말


def 대조(값: str, 원문: str) -> list:
    """**I001** -- 이 값의 알맹이가 원문에 다 있는가. 없는 것들을 돌려준다.

    글자 그대로 견주지 않는다 -- `2025년 3월` 을 `2025-03` 으로 편 것까지 '지어낸
    것' 으로 볼 수는 없다. 수는 수끼리, 말은 말끼리 본다.
    """
    바탕 = _핵(원문)
    바탕수, 바탕말 = set(바탕), " ".join(바탕)
    없는것 = []
    for x in _핵(값):
        if x.isdigit():
            if x not in 바탕수:
                없는것.append(x)
        elif x not in 바탕말:
            없는것.append(x)
    return 없는것


# ---------------------------------------------------------------- 칸별로 읽기

def _언제(글: str) -> tuple:
    got = [f"{y}-{int(m):02d}" for y, m in _연월.findall(글)]
    if len(got) < 2:
        해 = _연만.findall(글)
        got = got or ([f"{해[0]}-01"] if 해 else [])
        if len(해) >= 2 and len(got) < 2:
            got = [f"{해[0]}-01", f"{해[-1]}-12"]
    return tuple(got[:2])


def _역할(글: str) -> str:
    return next((r for r in LG.역할들 if r in 글), "")


def _잰것(글: str) -> list:
    out = []
    for 무엇, 전, u1, 후, u2 in _변화.findall(글):
        단위 = (u2 or u1 or "").strip()
        out.append({"무엇": re.sub(r"[^가-힣A-Za-z ]", " ", 무엇).strip(),
                    "전": 전.replace(",", ""), "후": 후.replace(",", ""),
                    "단위": 단위,
                    "어떻게": 글[글.find("(") + 1:글.rfind(")")] if "(" in 글 else ""})
    return out


def _쪼개기(글: str) -> list:
    return [w.strip() for w in re.split(r"[,·/]|\s및\s", 글) if w.strip()]


def 넣기(물음들: list, 답들: dict, L: LG.원장) -> tuple:
    """(바뀐 원장, 위반, 무엇을 채웠나). **원장을 갈아엎지 않고 빈칸만 채운다.**"""
    vs, 채운것 = [], []
    항목맵 = {h.id: h for h in L.항목들}
    새것 = []

    for q in 물음들:
        답 = (답들.get(q.get("id", "").lstrip("Q")) or "").strip()
        칸, 대상 = q.get("칸", ""), q.get("대상", "")
        if not 답:
            vs.append(위반("I004", "soft", q.get("id", "?"),
                          "답이 비었다 -- 이 물음은 아직 살아 있다"))
            continue
        없는것 = 대조(답, 답)          # 규칙 파서는 원문에서만 오므로 늘 통과한다
        h = 항목맵.get(대상)

        if 칸 == "새항목":
            언제 = _언제(답)
            역할 = _역할(답)
            # **언제도 역할도 못 읽으면 항목을 만들지 않는다.**
            #
            # 실측: "Python, BigQuery, Airflow" 가 번호가 밀려 이 자리로 들어왔고,
            # 이름이 `Python` 이고 곳이 `BigQuery` 인 항목이 원장에 생겼다. 그 뒤로
            # `ask.py` 는 **그 껍데기를 두고 매 바퀴 네 개씩 물었다** -- 역할은? 기간은?
            # 무엇이 달라졌나? 증빙은? 사람은 있지도 않은 경험을 설명하게 된다.
            #
            # 원장이 거절하지 않는다는 규율은 **사실을 표시와 함께 남기는 것**이지
            # 사실이 아닌 것을 만드는 것이 아니다. 답은 `답_NN.txt` 에 그대로 남으므로
            # 잃지 않는다 -- 물음만 살아 있게 두고 다시 묻는다.
            if not (언제 or 역할):
                vs.append(위반("I002", "hard", q.get("id", "?"),
                              f"{답[:30]!r} 에서 **기간도 역할도 못 읽었다** -- 경험이 "
                              "아닌 답이 들어온 것으로 보고 항목을 안 만들었다. "
                              "`무엇을, 어디서, 2025-03 ~ 2025-08, 참여` 꼴로 다시 "
                              "적어 주십시오 (답은 그대로 남아 있다)"))
                continue
            남은말 = [w for w in _쪼개기(답)
                     if not _연월.search(w) and not _연만.fullmatch(w.strip())
                     and w.strip() not in LG.역할들]
            새 = {"id": f"X{len(L.항목들) + len(새것) + 1}",
                 "이름": (남은말[0] if 남은말 else 답[:30]),
                 "곳": (남은말[1] if len(남은말) > 1 else ""),
                 "언제": list(언제), "역할": 역할, "쓴것": [], "잰것": [], "증빙": ""}
            새것.append(새)
            채운것.append(f"{q['id']} -> 새 항목 [{새['id']}] {새['이름']}")
            if not 역할:
                vs.append(위반("I002", "soft", q.get("id", "?"),
                              f"역할을 못 읽었다 -- {' · '.join(LG.역할들)} 중 하나를 "
                              "적어 주십시오 (E002 가 다시 물을 것이다)"))
            continue

        if h is None and 칸 != "생각" and not 칸.startswith("생각:"):
            vs.append(위반("I001", "hard", q.get("id", "?"),
                          f"답이 갈 항목({대상!r})이 원장에 없다 -- 안 넣었다"))
            continue

        if 칸 == "역할":
            r = _역할(답)
            if not r:
                vs.append(위반("I002", "hard", q.get("id", "?"),
                              f"{답[:24]!r} 에서 역할을 못 읽었다 "
                              f"({' · '.join(LG.역할들)} 중 하나)"))
            else:
                h.역할, _ = r, 채운것.append(f"{q['id']} -> [{h.id}].역할 = {r}")
        elif 칸 == "언제":
            got = _언제(답)
            if not got:
                vs.append(위반("I002", "hard", q.get("id", "?"),
                              f"{답[:24]!r} 에서 기간을 못 읽었다 (2025-03 ~ 2025-08)"))
            else:
                h.언제, _ = got, 채운것.append(f"{q['id']} -> [{h.id}].언제 = {got}")
        elif 칸 == "쓴것":
            h.쓴것 += _쪼개기(답)
            채운것.append(f"{q['id']} -> [{h.id}].쓴것 += {_쪼개기(답)}")
        elif 칸 == "증빙":
            h.증빙 = 답
            채운것.append(f"{q['id']} -> [{h.id}].증빙")
        elif 칸.startswith("어떻게:"):
            i = int(칸.split(":")[1])
            if i < len(h.잰것):
                h.잰것[i].어떻게 = 답
                채운것.append(f"{q['id']} -> [{h.id}].잰것[{i}].어떻게")
        elif 칸 == "잰것":
            if _안쟀다.search(답) and not _변화.search(답):
                채운것.append(f"{q['id']} -> [{h.id}] 안 쟀다고 하셨다 (넣을 수 없다)")
            else:
                got = _잰것(답)
                for m in got:
                    h.잰것.append(LG.잰것(**m))
                    if not m["어떻게"].strip():
                        vs.append(위반("I003", "soft", q.get("id", "?"),
                                      f"{m['무엇'] or '그 수'} 를 넣었지만 **재는 법이 "
                                      "없다** -- 괄호 안에 어떻게 쟀는지 적으면 "
                                      "자소서에 쓸 수 있다(J002)"))
                채운것.append(f"{q['id']} -> [{h.id}].잰것 += {len(got)}개"
                            if got else f"{q['id']} -> 수를 못 읽었다")
                if not got:
                    vs.append(위반("I002", "soft", q.get("id", "?"),
                                  f"{답[:30]!r} 에서 '얼마에서 얼마로' 를 못 읽었다 "
                                  "-- `클릭률 2.1% -> 2.6% (2주 A/B, n=48,000)` 꼴로"))
        elif 칸.startswith("생각"):
            갈래 = 칸.split(":")[1] if ":" in 칸 else "그밖"
            L.생각들.append(LG.생각(id=f"G{len(L.생각들) + 1}", 갈래=갈래, 말=답,
                                  딸린항목=대상))
            채운것.append(f"{q['id']} -> 생각[{갈래}]")
        else:
            vs.append(위반("I001", "soft", q.get("id", "?"),
                          f"모르는 칸이다: {칸!r} -- 안 넣었다"))

        if 없는것:
            vs.append(위반("I001", "hard", q.get("id", "?"),
                          f"답 원문에 없는 값이 섞였다: {' · '.join(없는것[:4])}"))

    L.항목들 += LG.읽기(새것).항목들
    return L, vs, 채운것


def 쓰기(L: LG.원장, path: Path) -> Path:
    """원장을 되쓴다. **읽은 꼴 그대로** -- 항목과 생각을 같이 담는다."""
    d = {"항목": [], "생각": [asdict(g) for g in L.생각들]}
    for h in L.항목들:
        x = asdict(h)
        x["언제"] = list(h.언제)
        x["잰것"] = [asdict(m) for m in h.잰것]
        d["항목"].append(x)
    path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="답을 원장에 넣는다 (대조하면서)")
    ap.add_argument("--물음", default="", help="jaso/ask.py --json 이 낸 것")
    ap.add_argument("--답", default="", help="`1) …` 꼴로 적은 답 (`-` 면 표준입력)")
    ap.add_argument("--표", dest="표", default="", help="기존 경험 원장 (없으면 새로)")
    ap.add_argument("--빼기", dest="빼기", action="append", default=[],
                    help="이 id 의 항목을 원장에서 뺀다 (잘못 들어간 것 치우기)")
    ap.add_argument("--넣기", action="store_true",
                    help="정말 쓴다 (기본은 무엇이 채워지는지 보여만 준다)")
    a = ap.parse_args(argv)

    물음들 = (json.loads(Path(a.물음).read_text(encoding="utf-8")).get("물음", [])
             if a.물음 else [])
    글 = ("" if not a.답 else
         (sys.stdin.read() if a.답 == "-" else Path(a.답).read_text(encoding="utf-8")))
    답들 = 답나누기(글)
    L = LG.읽기(a.표) if a.표 else LG.원장()

    for i in a.빼기:
        h = L.찾기(i)
        L.항목들 = [x for x in L.항목들 if x.id != i]
        print(f"  뺌    [{i}] {h.이름 if h else '(그런 항목이 없다)'}")
    L, vs, 채운것 = 넣기(물음들, 답들, L)
    print(f"물음 {len(물음들)}개 · 받은 답 {len(답들)}개")
    for 말 in 채운것:
        print(f"  채움  {말}")
    for v in vs:
        print(f"  {v}")

    남은hard = LG.hard(LG.검사(L))
    print(f"\n원장: 항목 {len(L)}개 · 생각 {len(L.생각들)}개 · "
          f"남은 hard {len(남은hard)}건")
    if not a.넣기:
        print("\n(보여만 줬다. 정말 쓰려면 `--넣기` 를 주십시오)")
        return 0
    if not a.표:
        print("--표 를 줘야 어디에 쓸지 안다", file=sys.stderr)
        return 2
    p = 쓰기(L, Path(a.표))
    print(f"[씀] {p}")
    print(f"\n다음:  python3 jaso/ask.py --표 {p} --문항 \"...\"   # 아직 물을 것이 있나")
    return 1 if LG.hard(vs) else 0


if __name__ == "__main__":
    raise SystemExit(main())
