"""**보고서 파이프라인** -- 원장 · 셈 · 관문. 네트워크도 LLM 도 필요 없다.

    python3 tests/test_brief.py

제일 중요한 검사는 **B004(다시 셈해서 대조)** 다. 나머지 관문은 꼬리표를 보지만
B004 는 값을 본다 -- 값을 손으로 바꿔치기해 놓고 관문이 잡는지 본다.
`law/mutate.py` 가 조문 낱말 하나를 일부러 틀리게 심는 것과 같은 자리다:
**어긋남 0 은 관문이 좋아서일 수도 있고 아무것도 못 잡아서일 수도 있다.**
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brief import derive as DV                                     # noqa: E402
from brief import gate as GT                                       # noqa: E402
from brief import ledger as LG                                     # noqa: E402
from brief import report as RP                                     # noqa: E402
from brief import source as SRC                                    # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


CSV = ("Symbol,Date,Time,Open,High,Low,Close,Volume\n"
       "^kospi,2026-09-09,16:00:00,2500,2530,2480,2510,412000\n"
       "^ndq,2026-09-09,16:00:00,20000,20100,19800,19850,88000\n")

주식 = SRC.get("주식")


def led_of(text=CSV, 받은날="2026-09-09"):
    v = LG.inspect(주식, LG.parse(주식, text))
    return LG.Ledger(출처="주식", 받은날=받은날, 질의="검사", 줄=v["good"],
                     버린것=v["버린것"])


print("── 출처 표는 스스로 앞뒤가 맞는가 ─────────────────────")
for name, s in SRC.SOURCES.items():
    ok(s.key in s.칸, f"{name}: key({s.key})가 칸 안에 있다")
    ok(set(s.수칸) <= set(s.칸), f"{name}: 수칸이 전부 칸 안에 있다")
    ok(all(c in DV.RULES for c in s.셈), f"{name}: 셈이 전부 derive.RULES 에 있다")
    ok("{심볼}" in s.url, f"{name}: url 에 채울 자리가 있다")
    need = {c for c in s.셈 for c in DV.RULES[c][0]}
    ok(need <= set(s.수칸), f"{name}: 셈이 필요한 칸을 출처가 다 받아 온다")
ok(SRC.get("없는출처") is None, "없는 출처는 None -- 비슷한 것을 골라 주지 않는다")
ok(SRC.심볼(주식, ["코스피", "모르는것"]) == ["^kospi", "모르는것"],
   "**모르는 이름은 그대로 넘긴다** -- 임의로 고치면 딴 종목을 그 이름으로 보고한다")

print()
print("── 원장: 받은 것을 그대로 믿지 않는가 ──────────────────")
ok(len(LG.parse(주식, CSV)) == 2, "CSV 를 두 줄로 읽는다")
ok(LG.parse(주식, "깨진 것") != [] or True, "깨진 CSV 로 안 죽는다")
ok(LG.parse(replace(주식, 꼴="json"), "{{{") == [], "깨진 JSON -> 빈 목록")

v = LG.inspect(주식, LG.parse(주식, CSV))
ok(v["통과"] and len(v["good"]) == 2, "멀쩡한 것은 통과")
ok(isinstance(v["good"][0]["Close"], float), "수칸은 수로 바뀐다")
ok(v["good"][0]["id"] == "^kospi", "key 칸이 줄 id 가 된다")

drift = CSV.replace("Close", "Closing")
ok(not LG.inspect(주식, LG.parse(주식, drift))["통과"],
   "**칸 이름이 바뀌면 통째로 안 받는다** -- 스키마가 바뀐 모습이다")
ok("빠졌다" in " ".join(LG.inspect(주식, LG.parse(주식, drift))["왜"]),
   "왜 안 받았는지 적는다")

nan = CSV.replace("2510", "N/A")
r = LG.inspect(주식, LG.parse(주식, nan))
ok(r["버린것"] == 1 and r["통과"] is False,
   f"수가 아닌 줄은 버린다 -- 절반이 깨지면 통과도 안 된다 (버린 것 {r['버린것']})")
ok(LG._num("N/A") is None and LG._num("1,234.5") == 1234.5,
   "**못 읽는 수는 None 이다 -- 0 으로 안 채운다**")
ok(not LG.inspect(주식, [])["통과"], "한 줄도 없으면 안 받는다")

print()
print("── 원장: 머리글이 없으면 안 읽는다 ────────────────────")
with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "a.json"
    LG.save(led_of(), p)
    back = LG.load(p)
    ok(back is not None and len(back) == 2 and back.받은날 == "2026-09-09",
       "저장 -> 읽기 왕복")
    p.write_text(json.dumps({"줄": [{"id": "x"}]}), encoding="utf-8")
    ok(LG.load(p) is None, "**출처·받은날이 없으면 None** -- 언제 것인지 모르면 못 쓴다")
    p.write_text("{{{", encoding="utf-8")
    ok(LG.load(p) is None, "깨진 파일도 None")
ok(led_of(받은날="망가진날짜").나이() is None,
   "받은날을 못 읽으면 나이는 None -- 모르는 것은 모른다고 한다")

print()
print("── 셈: 값이 맞고, **어디서 왔는지 들고 다니는가** ───────")
led = led_of()
facts = DV.row_facts(led, "^kospi", ("일간등락", "폭", "종가위치"), 주식.단위)
by = {f.이름: f for f in facts}
ok(abs(by["일간등락"].값 - 0.4) < 1e-9,
   f"일간등락 (2510-2500)/2500 = 0.40% (실제 {by['일간등락'].값:.4f})")
ok(abs(by["폭"].값 - 2.0) < 1e-9, f"폭 (2530-2480)/2500 = 2.00% ({by['폭'].값:.4f})")
ok(abs(by["종가위치"].값 - 0.6) < 1e-9,
   f"종가위치 (2510-2480)/(2530-2480) = 0.60 ({by['종가위치'].값:.4f})")
ok(by["일간등락"].단위 == "%", "단위가 붙는다")
ok(("^kospi", "Close") in by["일간등락"].근거 and ("^kospi", "Open") in by["일간등락"].근거,
   "**근거에 어느 줄 어느 칸인지 적혀 있다**")
ok(by["일간등락"].규칙 == "일간등락" and by["일간등락"].인자 == ("^kospi",),
   "규칙과 인자가 남아 있다 -- 관문이 이것으로 다시 센다")
ok(by["일간등락"].셈, "사람이 읽을 식도 같이")
ok(DV.row_facts(led, "없는줄", ("일간등락",)) == [], "없는 줄에서는 아무것도 안 나온다")

flat = led_of(CSV.replace("2530,2480", "2500,2500"))
got = {f.이름 for f in DV.row_facts(flat, "^kospi", ("일간등락", "폭", "종가위치"))}
ok("종가위치" not in got,
   "**고가=저가면 종가위치를 안 만든다** -- 0 으로 채우지 않는다(분모 0)")
ok("폭" in got, "그래도 폭은 셀 수 있으므로 센다 -- 하나가 안 된다고 다 버리지 않는다")

print()
print("── 셈: 가로질러 ──────────────────────────────────────")
allf = DV.row_facts(led, "^kospi", ("일간등락",)) + DV.row_facts(led, "^ndq", ("일간등락",))
up, down, flat_n = DV.한방향인가(allf, "일간등락")
ok((up, down, flat_n) == (1, 1, 0), f"코스피는 오르고 나스닥은 내렸다 ({up},{down},{flat_n})")
rank = DV.순위(allf, "일간등락")
ok(rank[0][0] == "^kospi" and rank[-1][0] == "^ndq", "순위가 큰 것부터")
ok(DV.흩어짐(allf, "일간등락") is not None, "둘이면 흩어짐을 센다")
ok(DV.흩어짐(DV.row_facts(led, "^kospi", ("일간등락",)), "일간등락") is None,
   "**하나뿐이면 안 센다** -- 표본 하나의 표준편차는 없는 값이다")

print()
print("── 관문 GREEN ────────────────────────────────────────")
good = RP.build(주식, led)
vs = GT.check(good, led, 주식)
ok(not GT.hard(vs), f"멀쩡한 보고서에는 hard 위반이 없다 ({[str(x) for x in vs]})")

print()
print("── 관문 RED -- 일부러 망가뜨린다 ────────────────────────")
f0 = [f for f in good if f.이름 == "일간등락"][0]

tampered = [replace(f0, 값=99.9)]
hits = GT.check_facts(tampered, led)
ok(any(v.rule == "B004" for v in hits),
   "**B004: 값을 바꿔치기하면 잡는다** -- 관문이 다시 세기 때문이다")
ok(any("다시 세니" in v.msg for v in hits), "얼마가 나와야 하는지도 적는다")

ok(any(v.rule == "B001" for v in GT.check_facts([replace(f0, 근거=())], led)),
   "B001: 근거가 없으면 잡는다")
ok(any(v.rule == "B002" for v in
       GT.check_facts([replace(f0, 근거=(("없는줄", "Close"),), 규칙="", 인자=())], led)),
   "B002: 원장에 없는 줄을 가리키면 잡는다")
ok(any(v.rule == "B002" for v in
       GT.check_facts([replace(f0, 근거=(("^kospi", "없는칸"),), 규칙="", 인자=())], led)),
   "B002: 있는 줄이라도 없는 칸을 가리키면 잡는다")

old = led_of(받은날="2020-01-01")
ok(any(v.rule == "B003" for v in GT.check_ledger(old, 주식)), "B003: 낡은 원장을 잡는다")
ok(any(v.rule == "B003" for v in GT.check_ledger(led_of(받은날="?"), 주식)),
   "B003: 받은날을 못 읽어도 잡는다 -- 모르는 것은 안 된 것으로 다룬다")
ok(any(v.rule == "B003" for v in GT.check_ledger(LG.Ledger(출처="x"), 주식)),
   "B003: 빈 원장을 잡는다")

ok(any(v.rule == "B005" for v in GT.check_prose("금리 때문이다.", good)),
   "B005: 근거 없는 단정을 잡는다 (soft)")
ok(not GT.check_prose("코스피 일간등락 0.4 로 올랐다.", good),
   "**수를 댄 문장은 안 잡는다** -- 근거를 댔기 때문이다")
ok(all(v.severity == "soft" for v in GT.check_prose("전망이다.", good)),
   "B005 는 soft 다 -- 문장은 사람이 고칠 수 있다")

print()
print("── 보고서: 못 받치면 **수를 안 적는다** ─────────────────")


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = RP.main(argv)
    return code, buf.getvalue()

code, out = run(["없는출처", "--것", "코스피"])
ok(code == 3 and "미검증" in out, "없는 출처 -> 끝값 3")
code, out = run(["주식"])
ok(code == 3 and "무엇을 받을지" in out, "--것 이 없으면 끝값 3")
code, out = run(["주식", "--원장", "/없는/경로.json"])
ok(code == 3 and "머리글" in out, "못 읽는 원장 -> 끝값 3, 왜인지 적는다")
code, out = run(["--출처목록"])
ok(code == 0 and "주식" in out and "환율" in out, "--출처목록 은 표를 보여 준다")

print()
print("── 보고서: 관문에 걸린 수는 **화면에서 뺀다** ───────────")
with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "낡음.json"
    LG.save(led_of(받은날="2019-01-01"), p)
    code, out = run(["주식", "--원장", str(p)])
    ok(code == 1, "hard 위반이 있으면 끝값 1")
    ok("뺐다" in out, "뺐다고 적는다")
    ok("2,510" not in out and "--" in out,
       "**낡은 원장의 종가가 화면에 안 나온다** -- 수를 먼저 읽고 단서를 나중에 "
       "읽게 두지 않는다")

    p2 = Path(d) / "좋음.json"
    import datetime
    LG.save(led_of(받은날=datetime.date.today().isoformat()), p2)
    code, out = run(["주식", "--원장", str(p2)])
    ok(code == 0, "신선한 원장이면 끝값 0")
    ok("2,510.00" in out, "그때는 종가가 나온다")
    ok("0.40" in out and "2.00" in out, "셈한 값도 나온다")
    ok("셈:" in out and "(종가-시가)/시가" in out, "**식을 같이 적는다**")
    ok("안 보는 것" in out and "원인" in out, "무엇을 안 보는지 매번 적는다")
    ok("위반 없음" in out, "관문 결과를 보고서 안에 적는다")

print()
if fails:
    print(f"보고: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("출처 선언 · 스키마 강제 · 추적 가능한 셈 · 관문 B001~B005 RED/GREEN · "
      "걸린 수 빼기 -- 통과")
