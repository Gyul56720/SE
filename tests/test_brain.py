"""**어떤 물음이 와도 다섯 꼴로 가거나 관할 밖인가.**

    python3 tests/test_brain.py

이 검사의 요점은 **내가 예상하지 못한 물음**으로 돌려 보는 것이다. 스포츠·영어·논문·
법·의학은 사용자가 든 **예시**였지 목록이 아니었다 -- 그래서 여기서는 그 다섯을 쓰지
않고, 촉매·산불·환율·번역·배송처럼 이 저장소에 모듈이 하나도 없는 것들로 돌린다.

한 번 잘못 짰던 자리를 회귀 못으로 붙든다: 판정기를 `법.조문대조` 처럼 **도메인별로**
등록했었다. 그러면 예상한 물음만 된다 -- `brief/source.py` 에 출처를 미리 등록한 것과
같은 하드코딩을 한 층 위에서 되풀이한 것이다.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brain import form as FM                                       # noqa: E402
from brain import order as OD                                      # noqa: E402
from brain import route as RT                                      # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


def 표(조각, 밖=(({"무엇": "인과", "왜": "원장으로 안 정해진다"}),)):
    return OD.읽기({"물음": "검사", "조각": list(조각), "관할밖": list(밖)})


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = RT.main(argv)
    return code, buf.getvalue()


print("── 꼴은 다섯이고 **도메인을 모른다** ────────────────────")
ok(len(FM.FORMS) == 5, f"꼴이 다섯이다 ({len(FM.FORMS)}개: {', '.join(FM.FORMS)})")
ok(set(FM.FORMS) == {"대조", "재계산", "기준선", "연역", "뒤집기"}, "이름이 그 다섯")
도메인말 = ("법", "의학", "스포츠", "주식", "논문", "영어", "승률", "조문", "LoL")
샌것 = [w for w in 도메인말 for n in FM.FORMS if w in n]
ok(not 샌것, f"**꼴 이름에 도메인이 한 글자도 안 들어간다** (샌 것: {샌것})")
ok(all(len(f.판정) >= 3 for f in FM.FORMS.values()),
   "**모든 꼴에 '모름' 갈래가 있다** -- 참/거짓 둘뿐인 꼴은 없다")
ok(all(f.못하는것 for f in FM.FORMS.values()), "꼴마다 못 하는 것이 적혀 있다")
ok(all(f.있어야 for f in FM.FORMS.values()), "꼴마다 무엇이 있어야 하는지 적혀 있다")
ok(FM.get("법.조문대조") is None,
   "(회귀 못) **도메인 이름으로는 꼴이 안 잡힌다** -- 그렇게 짰던 판을 되돌렸다")
ok(FM.get("없는꼴") is None, "없는 꼴은 None -- 비슷한 것을 골라 주지 않는다")

print()
print("── 모듈이 하나도 없는 물음들이 꼴로 가는가 ──────────────")
안예상 = [
    ("촉매 X 의 표면적이 보고된 값과 맞나", "대조",
     {"원장": "논문 표 S3", "주장": "BET 표면적 412 m2/g", "근거": "표S3:행2"}),
    ("올해 산불 건수가 평년보다 많은가", "기준선",
     {"관측": "올해 412건", "과거표본": "1991~2025 연간 건수", "기준선": "35년 분포"}),
    ("이 배송 지연율 8.3% 가 내가 센 것과 같나", "재계산",
     {"원장": "주문 원장 4,120줄", "수": "8.3%", "규칙": "지연건/전체"}),
    ("지문에서 '모든 A 는 B' 와 'C 는 A' 면 'C 는 B' 인가", "연역",
     {"전제": "모든 A 는 B · C 는 A", "결론": "C 는 B"}),
    ("그 결론이 응답자 한 명에 기대고 있나", "뒤집기",
     {"결론": "만족도가 올랐다", "근거묶음": "응답 37건"}),
]
for 말, 꼴, 재료 in 안예상:
    t = 표([{"주장": 말, "꼴": 꼴, "재료": 재료}])
    vs = OD.검사(t)
    ok(not OD.hard(vs), f"[{꼴}] {말[:30]} -- 통과 ({[str(v) for v in OD.hard(vs)]})")

print()
print("── 관할 밖도 **도메인이 아니라 물음의 종류**로 적힌다 ────")
ok(set(FM.관할밖) == {"인과", "전망", "가치", "처방", "원장없음"},
   f"관할 밖 갈래: {', '.join(FM.관할밖)}")
ok(not any(w in k for w in 도메인말 for k in FM.관할밖),
   "**관할 밖에도 도메인 이름이 없다** -- 있으면 그것도 예시 목록이 된다")
ok("의학" in FM.관할밖["처방"] and "법" in FM.관할밖["처방"],
   "처방 갈래가 위험한 자리를 짚어 준다(설명 안에서)")

print()
print("── 통째로 관할 밖인 물음 ───────────────────────────────")
t = OD.읽기({"물음": "영어 공부 어떻게 하지", "조각": [],
             "관할밖": [{"무엇": "원장없음", "왜": "밖에 대조할 정답표가 없다"}]})
ok(t.갈데없음, "조각이 없으면 갈 데 없음")
ok(not OD.hard(OD.검사(t)), "**관할 밖만 적어도 위반이 아니다** -- 그것도 옳은 답이다")
보 = OD.보고(t, OD.검사(t))
ok("수치를 붙이지 마라" in 보, "판정 없이 답하되 수치를 붙이지 말라고 적는다")

print()
print("── R001~R005 (RED) ─────────────────────────────────────")
vs = OD.검사(표([{"주장": "x", "꼴": "직관", "재료": {}}]))
ok(any(v.규칙 == "R001" for v in vs),
   "**R001: 없는 꼴을 지어내면 잡는다** -- 꼴은 요청 시점에 못 늘린다")
ok(any("있는 것은" in v.말 for v in vs if v.규칙 == "R001"), "있는 꼴을 알려 준다")

vs = OD.검사(표([{"주장": "x", "꼴": "기준선", "재료": {"관측": "1"}}]))
ok(any(v.규칙 == "R002" for v in vs), "R002: 재료가 빠지면 잡는다")
ok(any("과거표본" in v.말 for v in vs if v.규칙 == "R002"), "무엇이 빠졌는지 적는다")

vs = OD.검사(표([{"주장": "x", "꼴": "연역", "재료": {"전제": "  ", "결론": "C"}}]))
ok(any(v.규칙 == "R003" for v in vs),
   "**R003: 칸만 채우고 내용이 비면 잡는다** -- 도는 척만 하게 된다")

vs = OD.검사(OD.읽기({"물음": "x", "조각": [{"주장": "y", "꼴": "연역",
                                          "재료": {"전제": "A", "결론": "B"}}],
                     "관할밖": []}))
ok(any(v.규칙 == "R004" and v.등급 == "hard" for v in vs),
   "**R004: 관할 밖을 안 적으면 hard 위반** -- 통째로 판정되는 물음은 없다")

vs = OD.검사(OD.읽기({"물음": "x", "조각": [], "관할밖": []}))
ok(any(v.규칙 == "R005" for v in vs), "R005: 조각도 관할밖도 없으면 잡는다")

vs = OD.검사(OD.읽기({"물음": "x", "조각": [],
                     "관할밖": [{"무엇": "", "왜": "그냥"}]}))
ok(any(v.규칙 == "R004" and v.등급 == "soft" for v in vs),
   "무엇이 관할 밖인지 안 적히면 soft 로 짚는다")

print()
print("── 작업표 읽기 -- 아무거나 와도 안 죽는다 ────────────────")
ok(OD.읽기("이건 JSON 이 아니다").조각 == [], "깨진 JSON -> 빈 작업표")
ok(OD.읽기("[1,2,3]").조각 == [], "dict 가 아니면 빈 작업표")
ok(OD.읽기({"조각": "목록이 아님"}).조각 == [], "조각이 목록이 아니면 빈 목록")
ok(OD.읽기({"조각": [{"주장": "a", "꼴": "연역", "재료": "dict 아님"}]}).조각[0].재료 == {},
   "재료가 dict 가 아니면 빈 dict -- 그러면 R002 가 잡는다")
ok(OD.읽기(json.dumps({"물음": "q", "조각": [], "관할밖": [{"무엇": "가치"}]})).관할밖,
   "JSON 문자열도 읽는다")

print()
print("── 프롬프트: **판정 이야기가 한 줄도 없다** ──────────────")
p = RT.프롬프트("촉매 선택을 어떻게 해야 하나")
for w in ("R001", "R002", "R003", "R004", "hard", "위반", "관문"):
    ok(w not in p, f"프롬프트에 '{w}' 가 안 실린다 -- 실으면 쪼갬이 사양서가 된다")
ok(all(n in p for n in FM.FORMS), "다섯 꼴을 보여 준다 -- 여기서 골라야 하므로")
ok("관할밖" in p and "반드시" in p, "관할 밖을 반드시 적으라고 시킨다")
ok("없는 출처나 없는 수를 적지 마라" in p, "지어내지 말라고 시킨다")

print()
print("── CLI ───────────────────────────────────────────────")
code, out = run(["--꼴"])
ok(code == 0 and "다섯이고 늘지 않는다" in out, "--꼴 은 목록 (호출 0회)")
code, out = run(["--프롬프트", "산불이 늘었나"])
ok(code == 0 and "산불이 늘었나" in out, "--프롬프트 는 물음을 실어 준다")
code, out = run([])
ok(code == 3, "아무것도 안 주면 끝값 3")

with tempfile.TemporaryDirectory() as d:
    good = Path(d) / "g.json"
    good.write_text(json.dumps({"물음": "산불", "조각": [
        {"주장": "올해 건수가 평년보다 많은가", "꼴": "기준선",
         "재료": {"관측": "412건", "과거표본": "1991~2025", "기준선": "35년 분포"}}],
        "관할밖": [{"무엇": "인과", "왜": "왜 늘었는지는 이 원장으로 안 정해진다"}]},
        ensure_ascii=False), encoding="utf-8")
    code, out = run(["--표", str(good)])
    ok(code == 0, "성한 작업표는 끝값 0")
    ok("위반 없음" in out and "돌려도 된다" in out, "돌려도 된다고 적는다")
    ok("brief/infer.py" in out, "**어느 자리로 가야 하는지 낸다**")
    ok("못 하는 것" in out, "그 꼴이 못 하는 것을 같이 적는다")
    ok("관할 밖" in out and "인과" in out, "관할 밖을 적는다")

    bad = Path(d) / "b.json"
    bad.write_text(json.dumps({"물음": "x", "조각": [
        {"주장": "y", "꼴": "직관", "재료": {}}], "관할밖": []}, ensure_ascii=False),
        encoding="utf-8")
    code, out = run(["--표", str(bad)])
    ok(code == 1, "hard 위반이면 끝값 1")
    ok("돌리지 않는다" in out, "**돌리지 말라고 적는다**")

    밖만 = Path(d) / "o.json"
    밖만.write_text(json.dumps({"물음": "어떻게 살아야 하나", "조각": [],
        "관할밖": [{"무엇": "가치", "왜": "외적 정당화"}]}, ensure_ascii=False),
        encoding="utf-8")
    code, out = run(["--표", str(밖만)])
    ok(code == 3 and "통째로 관할 밖" in out, "통째로 관할 밖이면 끝값 3")

    code, out = run(["--표", str(Path(d) / "없다.json")])
    ok(code == 3 and "못 열었다" in out,
       "**없는 파일로 안 죽는다** -- 무엇을 하라고 알려 준다")

print()
if fails:
    print(f"라우터: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("꼴 다섯(도메인 없음) · 예상 못 한 물음 다섯 · 관할 밖 · R001~R005 RED · "
      "프롬프트에 판정 안 샘 -- 통과")
