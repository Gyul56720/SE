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
if fails:
    print(f"표본 자르기: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("표본 자르기: 표식 · 속임수 · 표식 없음 · 짧은 토막 · 인코딩 · 저장 -- 통과")
