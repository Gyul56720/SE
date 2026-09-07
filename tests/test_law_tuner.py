"""법 지시문 튜너가 **실제로 한 바퀴를 도는가**, 그리고 그 계약을 지키는가.

계약 셋을 검사로 고정한다. 셋 다 novel/tuner.py 가 사고로 배운 것이다:

    1. 산출물 본문은 프롬프트에 안 들어간다   (새면 다음 산출물이 그것으로 도배된다)
    2. 시도마다 결론은 한 번                  (아니면 채택한 것을 다음 바퀴가 되돌린다)
    3. 한 축을 내리 되돌리면 쉬게 한다        (아니면 같은 축만 계속 뽑힌다)

여기에 법에서 새로 넣은 것 하나를 더 본다: **재생성 없이는 심판하지 않는다.**

    python3 tests/test_law_tuner.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# **모듈 상수를 읽기 전에** 갈아끼운다 -- 진짜 장부와 진짜 지시문을 건드리면 안 된다.
TMP = Path(tempfile.mkdtemp())
os.environ["LAW_TUNE_LOG"] = str(TMP / "tune.jsonl")
os.environ["LAW_TUNE_BEST"] = str(TMP / "tune.best.json")
os.environ["LAW_DIRECTIVES"] = str(TMP / "directives.json")
shutil.copy(ROOT / "law" / "directives.json", TMP / "directives.json")

FAKE = TMP / "fake_claude.sh"
FAKE.write_text("#!/bin/sh\necho '지어낸 사실관계는 그 블록의 첫 문장에서 가상임을 밝혀라.'\n")
FAKE.chmod(0o755)
os.environ["LAW_CLAUDE"] = str(FAKE)

from law import corpus as CP                                          # noqa: E402
from law import tuner as TU                                           # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "law_corpus"

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


DOCS = TMP / "문서"
DOCS.mkdir()
SECTIONS = ("1. 왜 알아야 하는가", "2. 조문과 이론", "3. 핵심 법리", "4. 해석기법",
            "5. 실무상 흔한 오해", "6. 사례 적용 (학습용 창작 사례, 실제 판례 아님)",
            "7. 연습 사실관계", "8. 다음 주제와의 연결")

# 이 문장이 프롬프트에 새어 들어가는지 보려고 심어 둔 표지다.
MARKER = "낙타표성냥공장에서벌어진일"


def write_doc(labelled: bool):
    body = ['---', 'title: "검사용"', 'domain: "00_검사"', 'tags: "[검사]"',
            'key_principle: "검사"', 'source_statute: "가상시험법"', '---', '']
    for name in SECTIONS:
        body.append(f"## {name}")
        if name.startswith("6."):
            head = "가상의 " if labelled else ""
            body.append(f"### 사례 1\n**사실관계:** {head}{MARKER} 에서 다툼이 생겼다.\n")
        elif name.startswith("7."):
            body.append(f"가상의 연습 사실관계. {MARKER}.\n")
        else:
            body.append("제7조에 따른다.\n")
    (DOCS / "검사문서.md").write_text("\n".join(body), encoding="utf-8")


CORPUS = CP.load(FIXTURE)
TARGETS = [str(DOCS)]

print("[재기] 관문 위반을 규칙별 거리로 낸다 -- LLM 호출 0회")
write_doc(labelled=False)
s = TU.measure(TARGETS, CORPUS)
ok("L008" in s["axes"] and s["axes"]["L008"]["hard"] == 1,
   f"라벨 없는 사례 블록 -> L008 hard 1 (얻은 값 {s['axes'].get('L008')})")
ok(abs(s["axes"]["L008"]["gap"] - 1.0) < 1e-9,
   f"대상 1개이므로 거리 = 위반 수 (얻은 값 {s['axes']['L008']['gap']})")
ok(s["docs"] == 1 and s["checked"] > 0, "문서 수와 검증 인용 수를 같이 보고한다")

print()
print("[계약 1] 산출물 본문은 프롬프트에 한 글자도 안 들어간다")
p = TU.ask_prompt("L008", s, "지금 지시문", "지어낸 사실관계에 그렇다고 적는다")
ok(MARKER not in p, "문서에 심은 표지가 프롬프트에 없다")
ok("L008" in p and "1건" in p, "규칙 이름과 위반 수는 들어간다")
ok("지금 지시문" in p, "지금 쓰고 있는 지시문은 들어간다")

print()
print("[정리] 되받은 것을 그대로 싣지 않는다")
ok(TU._clean('```\n고친 지시문\n```') == "고친 지시문", "코드펜스를 걷어낸다")
ok(TU._clean('"따옴표에 싸여 왔다"') == "따옴표에 싸여 왔다", "따옴표를 벗긴다")
ok(TU._clean("첫 줄\n둘째 줄") == "첫 줄 둘째 줄", "여러 줄을 한 줄로 잇는다")

print()
print("[한 바퀴] 고침 -> 재생성 -> 채택")
rc = TU.attempt(TARGETS)
ok(rc == 0, "claude 한 번 불러 지시문을 고쳐 넣었다")
d = json.loads((TMP / "directives.json").read_text(encoding="utf-8"))
ok("첫 문장에서 가상임" in d["rules"]["L008"]["지시"], "지시문이 바뀌어 저장됐다")
ok([r["무엇"] for r in TU.rows()] == ["고침"], "장부에 '고침' 한 줄")

rc = TU.keep(TARGETS)
ok(rc == 1, "재생성이 없으면 심판을 거부한다 (지문이 그대로다)")
ok([r["무엇"] for r in TU.rows()] == ["고침"], "거부했으므로 장부에 결론이 안 붙는다")

write_doc(labelled=True)                       # 생성기가 다시 돌았다고 치자
rc = TU.keep(TARGETS)
ok(rc == 0, "재생성 뒤에는 심판한다")
last = TU.rows()[-1]
ok(last["무엇"] == "채택" and last["거리(후)"] < last["거리(전)"],
   f"거리가 내려갔으니 채택 (얻은 값 {last['거리(전)']} -> {last['거리(후)']})")
d = json.loads((TMP / "directives.json").read_text(encoding="utf-8"))
ok("첫 문장에서 가상임" in d["rules"]["L008"]["지시"], "채택된 지시문이 남아 있다")
ok(Path(os.environ["LAW_TUNE_BEST"]).exists(), "챔피언 파일을 남긴다")

print()
print("[계약 2] 시도마다 결론은 한 번")
ok(TU._pending() is None, "결론이 붙은 고침은 다시 집지 않는다")
ok(TU.keep(TARGETS) == 0 and [r["무엇"] for r in TU.rows()].count("채택") == 1,
   "keep 을 다시 불러도 결론이 두 번 붙지 않는다")

print()
print("[되돌림] 나빠지면 지시문을 원래대로 되돌린다")
write_doc(labelled=False)                      # 다시 나빠진 상태
before = json.loads((TMP / "directives.json").read_text(encoding="utf-8"))
TU.attempt(TARGETS)
write_doc(labelled=False)                      # 그 규칙은 그대로인데
# 규약을 안 지킨 문서가 하나 늘었다 -- 총점이 나빠진다. **지킴목이 여기서 일한다:**
# 규칙 하나의 거리가 조금 내려가도 전체가 나빠지면 채택하지 않는다.
(DOCS / "여분.md").write_text("# 8절도 front-matter 도 없는 문서", encoding="utf-8")
TU.keep(TARGETS)
last = TU.rows()[-1]
ok(last["무엇"] == "되돌림", f"나아지지 않았으면 되돌림 (얻은 값 {last['무엇']})")
after = json.loads((TMP / "directives.json").read_text(encoding="utf-8"))
ok(after["rules"]["L008"]["지시"] == before["rules"]["L008"]["지시"],
   "되돌림이면 지시문이 원래대로 돌아온다")
ok(last["점수(후)"] > last["점수(전)"],
   f"거리는 내려갔지만 총점이 올라가 지킴목에 걸렸다 "
   f"({last['거리(전)']:.1f}->{last['거리(후)']:.1f}, 총점 {last['점수(전)']:.1f}->{last['점수(후)']:.1f})")

print()
print("[계약 3] 내리 되돌린 규칙은 쉬게 한다")
for _ in range(2):
    TU.note({"때": "x", "무엇": "되돌림", "축": "L005", "대상": None,
             "점수(전)": 1.0, "점수(후)": 1.0})
ok("L005" in TU.cooling(), f"두 번 되돌린 L005 는 쉰다 (얻은 값 {TU.cooling()})")
TU.note({"때": "x", "무엇": "채택", "축": "L005", "대상": None,
         "점수(전)": 1.0, "점수(후)": 0.5})
ok("L005" not in TU.cooling(), "채택이 나오면 그 규칙은 다시 뽑힌다")

s2 = TU.measure(TARGETS, CORPUS)
rule, _ = TU.worst(s2, skip={"L008"})
ok(rule != "L008", f"쉬는 규칙은 건너뛰고 다음을 뽑는다 (얻은 값 {rule})")

print()
print("[적재] 걸린 규칙의 지시문만 프롬프트에 싣는다")
blk = TU.block(s2, limit=2)
ok(blk.count("\n") <= 1, f"두 줄까지만 (얻은 값 {blk.count(chr(10)) + 1}줄)")
# **수를 박지 않는다.** 18 로 박아 뒀더니 문언 관문 W 다섯 개가 늘면서 깨졌다 --
# 규칙이 느는 것은 정상이고, 검사가 그걸 막으면 안 된다.
n = len(json.loads((TMP / "directives.json").read_text(encoding="utf-8"))["rules"])
ok(len(TU.block(None).splitlines()) == n,
   f"측정값이 없으면 전부 싣는다 (지금 규칙 {n}개)")

print()
if fails:
    print(f"튜너: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("법 튜너: 재기 · 본문 격리 · 한 바퀴 · 결론 한 번 · 쉬는 규칙 -- 통과")
