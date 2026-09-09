"""**첫 쪽을 재는 자가 제대로 재는가.**

사용자(2026-09-09): "게시글을 읽지말고, 실제 1화를 가져와 일본 라노벨이나 한국 웹소설."

에이전트 쪽에서는 그 1화를 못 가져온다 -- 소설이 올라와 있는 자리가 전부 나가는 길에서
막혀 있다(novel/first.py 머리말). 그래서 지어내는 대신 자를 만들었고, 여기서 보는 것은
**그 자가 남의 글도 잰다**는 것이다: 일본 원문의 「 도 대사로 세고, 대사가 아예 없는
글에서도 안 터지고, 앞머리만 재되 분량은 통째로 센다.

실행: python3 tests/test_first.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel import first                                              # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


KO = ('어깨가 먼저 젖었다. 우산은 어제 잃어버렸고 오늘은 그것을 아쉬워할 겨를이 없었다.\n'
      '"비 온다."\n'
      '뒤에서 누가 말했다. 나는 돌아보지 않았다.\n'
      '"그래서?"\n'
      '"그래서 뛰자고. 저기 처마 밑."\n')

JA = ('　男は転んだまま空を見ていた。雨がまだ降っていた。\n'
      '「立てるか」\n'
      '　声がした。\n')

NOTALK = "그는 걸었다. 비가 왔다. 아무도 말하지 않았다. 그것이 이 마을의 규칙이었다.\n" * 6

print("[첫 대사까지]")
ok(first.to_talk(KO) == KO.index('"'), f"큰따옴표를 찾는다 ({first.to_talk(KO)}자)")
ok(first.to_talk(JA) == JA.index("「"), "일본 원문의 「 도 대사로 센다  ← 남의 1화를 잰다")
ok(first.to_talk(NOTALK) == len(NOTALK.strip()) or first.to_talk(NOTALK) == len(NOTALK),
   "대사가 없으면 글 길이  ← 0 이 아니다, 끝까지 안 나온 것이다")
ok(first.to_talk("") == 0, "빈 글에서 안 터진다")

print("\n[첫 문장]")
ok(first.first_len(KO) == len("어깨가 먼저 젖었다."), f"첫 문장만 센다 ({first.first_len(KO)}자)")
ok(first.first_len('"비 온다."\n뒤에서 누가 말했다.\n') == len('"비 온다."'),
   "첫 줄이 대사면 그 대사 줄을 센다")
ok(first.first_len("") == 0, "빈 글에서 안 터진다")

print("\n[프로필]")
_m = first.measure(KO)
ok(set(k for k, _, _ in first._AXES) <= set(_m), f"축이 다 나온다 ({len(_m)}개)")
ok(_m["chars"] == len(KO.strip()), "분량은 글 전체를 센다")
ok(0 < _m["dialog"] <= 1, f"대사 몫이 나온다 ({_m['dialog']:.2f})")
ok(first.measure("") == {}, "빈 글은 빈 것을 준다")

# **앞머리만 잰다.** 이탈은 첫 화면에서 나므로 뒤에 붙은 것은 비율에 안 섞여야 한다.
_head = '"가."\n"나."\n' * 200
_tail = "그는 걸었다. " * 400
_m2 = first.measure(_head + _tail, head=len(_head))
ok(_m2["dialog"] > 0.9, f"뒤에 붙은 서술이 앞머리 비율을 안 흐린다 ({_m2['dialog']:.2f})")
ok(_m2["chars"] > len(_head), "그래도 분량은 통째로 센다")

print("\n[표]")
_t = first.table([("실제1화", first.measure(KO)), ("우리1화", first.measure(NOTALK))])
ok("실제1화" in _t and "우리1화" in _t, "글 이름이 칸으로 선다")
ok(all(lbl in _t for _, lbl, _ in first._AXES), "축이 줄로 선다")
ok(len(_t.splitlines()) == len(first._AXES) + 2, "머리 · 금 · 축만큼의 줄")

print("\n[명령줄]")
tmp = tmp2 = Path(REPO / "tests" / "_first_tmp.txt")
tmp.write_text(KO, encoding="utf-8")
try:
    ok(first.main([str(tmp)]) == 0, "파일을 주면 0")
    ok(first.main([str(tmp / "없다")]) == 2, "없는 파일이면 2  ← 조용히 통과하지 않는다")
finally:
    pass

print("\n[표본이 저장소에 남는가]")
# **이 저장소가 두 번 앓은 병이다.** `novel/*.json` 이 통째로 무시 대상이라
# targets.json 도 directives.json 도 저장소에서 사라진 적이 있고, 그때 CI 는 표본에서
# 온 수가 아니라 옛 짐작으로 돌았다(.gitignore 의 그 자리 주석). first_ref.json 도
# 여기 걸릴 뻔했다 -- 만들고 나서 `git status` 에 안 떴다(2026-09-09).
import subprocess                                                    # noqa: E402
_ig = subprocess.run(["git", "check-ignore", "-q", "novel/first_ref.json"],
                     cwd=REPO, capture_output=True)
ok(_ig.returncode != 0, "표본 파일이 .gitignore 에 안 먹힌다  ← 먹히면 조용히 사라진다")
_tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "novel/first_ref.json"],
                          cwd=REPO, capture_output=True)
ok(_tracked.returncode == 0 or first.REF.exists(),
   "표본 파일이 나무에 있거나 적어도 여기 있다")

print("\n[표본 -- 잰 것이 밴드가 된다]")
# **표본은 저장소 파일에 쌓인다.** 검사가 그 파일을 건드리면 안 된다 -- 검사를 돌릴
# 때마다 진짜 표본이 늘어나면 그 수는 잰 것이 아니라 검사의 부산물이다.
_real = first.REF
_got = first.ref()
ok(isinstance(_got, list), f"표본을 읽는다 ({len(_got)}편)")
ok(all("sent_len" in g or "dialog" in g for g in _got), "표본마다 잰 축이 들어 있다")
_mid = first.ref_mid()
ok(bool(_got) == bool(_mid), "표본이 있으면 중앙값이 나온다")

first.REF = Path(REPO / "tests" / "_first_ref_tmp.json")
try:
    ok(first.ref() == [] and first.ref_mid() == {},
       "없는 파일이면 빈 것  ← 여기서 터지면 자가 죽는다")
    n1 = first.record("가", first.measure(KO))
    n2 = first.record("나", first.measure(NOTALK))
    ok((n1, n2) == (1, 2), f"표본이 쌓인다 ({n1} → {n2})")
    ok(first.record("가", first.measure(NOTALK)) == 2, "같은 이름은 갈아 끼운다")
    _m = first.ref_mid()
    ok("sent_len" in _m or "dialog" in _m, f"중앙값이 나온다 ({sorted(_m)[:3]})")
    ok(first.main([str(tmp2)]) == 0, "표본이 있어도 명령줄이 돈다")
finally:
    first.REF.unlink(missing_ok=True)
    first.REF = _real
ok(first.REF == _real and len(first.ref()) == len(_got),
   "진짜 표본은 안 건드렸다  ← 검사가 표본을 늘리면 그것은 잰 것이 아니다")


print()
if fails:
    print(f"첫 쪽: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
tmp.unlink(missing_ok=True)
print("첫 쪽: 첫 대사까지 · 첫 문장 · 앞머리 프로필 · 표 · 명령줄 · 표본 -- 통과")
