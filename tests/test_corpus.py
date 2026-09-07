"""표본 자르기 -- **손으로 나누지 않는다.**

사람이 미리 분류하면 그 나눔이 곧 편향이고, 무엇보다 작품마다 나누는 방식이 다르다.
원문을 통째로 받아 기계가 자른다. 여기서 고정하는 것은 세 가지다.

  · 본문을 손대지 않는다 (우리가 재려는 것이 그 꼴이다)
  · 표식이 없어도 자른다 (연재분을 이어 붙인 파일)
  · 본문 한가운데의 표식 같은 말에 속지 않는다

실행: python3 tests/test_corpus.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import corpus as C                                        # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


BODY = "본문이 이어진다. " * 120


def work(marks):
    return "\n".join(f"{m}\n{BODY}" for m in marks)


print("[표식] **원문에 있는 표식으로 자른다**")
u = C.split(work(["1화", "2화", "3화"]))
ok(len(u) == 3, f"화 표식으로 셋으로 갈린다 ({len(u)}개)")
ok([x.episode for x in u] == [1, 2, 3], "번호가 이어진다")
ok(all(BODY.strip() in x.body for x in u), "본문이 그대로 들어 있다  ← 손대지 않는다")

u = C.split(work(["제 1 부", "제1장", "1화", "2화", "제2장", "3화"]))
ok(max(x.chapter for x in u) >= 2, f"장이 바뀌는 것을 센다 (장 {max(x.chapter for x in u)}개)")
ok(len({x.stem for x in u}) == len(u), "이름이 겹치지 않는다  ← 겹치면 파일이 덮인다")

u = C.split(work(["프롤로그", "1화", "에필로그"]))
ok(len(u) == 3, "프롤로그와 에필로그도 한 토막이다")

print()
print("[속임수] **본문 한가운데의 말에 속지 않는다**")
mid = "그는 3화 때의 일을 떠올렸다. " + BODY
u = C.split("1화\n" + mid + "\n2화\n" + BODY)
ok(len(u) == 2, f"문장 안의 '3화' 로는 안 자른다 ({len(u)}개)  ← 자르면 원고가 조각난다")
u = C.split(work(["1화", "2화"]) + "\n" + "긴 제목처럼 보이지만 사실은 본문인 줄 " * 3)
ok(len(u) == 2, "긴 줄은 표식으로 안 본다")

print()
print("[표식 없음] **연재분을 이어 붙인 파일도 잘라야 한다**")
flat = "\n\n".join([BODY] * 12)
u = C.split(flat, target=3000)
ok(len(u) >= 3, f"길이로 자른다 ({len(u)}개)")
ok(all("\n" in x.body for x in u), "빈 줄에서만 끊는다  ← 문장 한가운데를 자르면 자가 거짓말한다")
ok(sum(len(x.body) for x in u) >= len(flat) - len(u) * 2,
   "글자를 잃지 않는다  ← 자르다 흘리면 그만큼 표본이 줄어든다")

print()
print("[짧은 토막] **표식만 있고 알맹이가 없으면 앞에 붙인다**")
u = C.split("1화\n" + BODY + "\n2화\n짧다.\n3화\n" + BODY)
ok(len(u) == 2, f"짧은 토막은 앞엣것에 붙는다 ({len(u)}개)")
ok("짧다." in "".join(x.body for x in u), "붙이면서도 글자는 안 버린다")

print()
print("[인코딩] **cp949 로 저장된 파일도 읽는다**")
d = Path(tempfile.mkdtemp())
(d / "a.txt").write_bytes(("1화\n" + BODY).encode("cp949"))
ok(C.load(d / "a.txt").startswith("1화"), "cp949 를 읽는다  ← 옛 파일이 대개 이쪽이다")
(d / "b.txt").write_bytes(("﻿1화\n" + BODY).encode("utf-8"))
ok(C.load(d / "b.txt").startswith("1화"), "BOM 을 걷어낸다")

print()
print("[저장] **이름에 부 · 장 · 화가 들어간다**")
print("      ← 화마다 부마다 방식이 다르다는 것을 재려면 그 축이 이름에 있어야 한다.")
man = C.write(C.split(work(["1화", "2화"])), d / "out")
ok((d / "out" / "01-01-001.txt").exists(), "부-장-화 꼴로 떨군다")
ok((d / "out" / "manifest.json").exists(), "목록도 같이 남긴다")
ok(man["n"] == 2 and man["units"][0]["chars"] > 0, "목록에 길이가 적힌다")
ok((d / "out" / "01-01-001.txt").read_text(encoding="utf-8").count("본문이 이어진다") > 100,
   "떨군 파일에 본문이 그대로 있다")

print()
print("[2차 분할] **표식으로 잘랐어도 크면 다시 자른다**")
print("      ← 실측: 장 하나가 310,835자인 단행본. 한 덩이로 두면 그 작품의 프로필이")
print("        열두 점밖에 안 되고, 화마다 다른 것을 재겠다는 말이 무의미해진다.")
huge = "제 1장 어떤 제목\n" + ("문장이 이어진다. " * 60 + "\n\n") * 300
u = C.split(huge)
ok(len(u) > 8, f"거대한 장이 여러 토막으로 갈린다 ({len(u)}개)")
ok(max(len(x.body) for x in u) < C.MAX_CHARS, "어느 토막도 상한을 안 넘는다")
ok(all(x.chapter == u[0].chapter for x in u), "나뉜 조각은 같은 장에 남는다")
flat = "제 1장 제목\n" + "문장이 붙어 있다. " * 8000          # 빈 줄이 하나도 없다
u = C.split(flat)
ok(len(u) > 5, f"빈 줄이 없어도 자른다 ({len(u)}개)  ← 그런 원고가 실제로 있었다")

print()
print("[앞머리] **제목만 있는 첫 줄은 뒤엣것에 붙인다**")
print("      ← 실측: 59자 · 61자짜리 토막. 앞에 붙일 것이 없으니 뒤로 붙여야 한다.")
u = C.split("어떤 소설의 제목\n\n" + "\n".join(["1화", BODY, "2화", BODY]))
ok(len(u) == 2, f"부스러기가 사라진다 ({len(u)}개)")
ok("어떤 소설의 제목" in u[0].body, "붙이면서도 글자는 안 버린다")
ok(u[0].stem.endswith("001"), f"번호가 1부터 다시 매겨진다 ({u[0].stem})")

print()
print("[상한] **붙이기와 자르기가 서로를 되돌리면 안 된다**")
print("      ← 실측: 27자짜리 조각이 앞엣것에 계속 붙어 한 토막이 64,851자가 됐다.")
print("        2차 분할로 잘라 놓은 것을 붙이기가 도로 이어 붙인 것이다.")
u = C.split("제 1장 제목\n" + "\n".join(["짧다."] * 4000))
ok(max(len(x.body) for x in u) <= C.MAX_CHARS,
   f"짧은 줄이 몇천 개여도 상한을 안 넘는다 (최대 {max(len(x.body) for x in u):,}자)")
u = C.split("\n".join(["제 1장"] + ["문장. " * 40] * 3000))
ok(max(len(x.body) for x in u) <= C.MAX_CHARS,
   f"거대한 장도 상한 아래로 내려온다 (최대 {max(len(x.body) for x in u):,}자)")
ok(all("\n" not in x.title for x in u), "제목에 줄바꿈이 안 남는다  ← 보고서가 깨진다")

print()
if fails:
    print(f"표본 자르기: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("표본 자르기: 표식 · 속임수 · 표식 없음 · 짧은 토막 · 인코딩 · 저장 -- 통과")
