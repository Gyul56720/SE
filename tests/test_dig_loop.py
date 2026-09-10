"""**루프가 진짜로 도는가.**

    python3 tests/test_dig_loop.py

`scripts/seek.sh` 때 배운 자리다. 그때 검사는 `bash -n` 과 텍스트 grep 뿐이었고 --
네 걸음이 다 있나, rebase 를 안 쓰나, 순서가 맞나 -- **그 검사는 파일이 한 줄도 안
도는 동안 전부 통과했다.** 한글 변수명(`초=25`)이 대입이 아니라 명령어로 파싱되는데
문법으로는 멀쩡했기 때문이다.

    검사하지 않은 초록불이 검사한 빨간불보다 나쁘다

그래서 여기서는 **스크립트를 끝까지 돌린다.** 망은 안 탄다 -- `DIG_CMD` 에 가짜
dig 를 물려서, 루프가 무엇을 몇 번 어떤 값으로 부르는지 그 가짜가 받아 적는다.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


가짜dig = r'''#!/usr/bin/env python3
"""부른 것을 받아 적고, 진짜 dig 처럼 생긴 것을 낸다."""
import json, os, sys
기록 = os.environ["DIG_CALLS"]
with open(기록, "a", encoding="utf-8") as f:
    f.write(" ".join(sys.argv[1:]) + "\n")

if "--찾기" in sys.argv:
    if "--json" in sys.argv:
        print(json.dumps({"물음": "x", "찾은주소": [
            {"주소": f"https://ex{i}.kr/p/{i}", "글": "", "값": 50 - i}
            for i in range(1, 7)]}, ensure_ascii=False))
    sys.exit(0)

urls = []
보는중 = False
for a in sys.argv[1:]:
    if a == "--url":
        보는중 = True
    elif a.startswith("--"):
        보는중 = False
    elif 보는중:
        urls.append(a)
for u in urls:
    print("## 캔 값")
    print("  가격    (2) 9,000원 · 15,000원")
    print("  전화    (1) 02-434-1234")
    print(f"## 글 [{u}] (12자)")
    print("  9,000원 육개장")
sys.exit(0)
'''

실패dig = ('#!/usr/bin/env python3\n'
          'import os, sys\n'
          'open(os.environ["DIG_CALLS"], "a").write(" ".join(sys.argv[1:]) + "\\n")\n'
          'print("[못받음] -- HTTP 403"); sys.exit(3)\n')


def 돌리기(dig본문, argv, env더=None, 초=6):
    """스크립트를 **진짜로** 돌린다. (끝값, 화면, 부른것들, 낸파일)"""
    tmp = Path(tempfile.mkdtemp())
    가짜 = tmp / "fakedig.py"
    가짜.write_text(dig본문, encoding="utf-8")
    가짜.chmod(0o755)
    부른것 = tmp / "calls.txt"
    부른것.touch()
    낼것 = tmp / "out.txt"
    env = dict(os.environ)
    env.update({"DIG_CMD": f"{sys.executable} {가짜}", "DIG_CALLS": str(부른것),
                "DIG_LOOP_SECONDS": str(초), "DIG_LOOP_BATCH": "2",
                "DIG_LOOP_FOLLOW": "8", "DIG_LOOP_FOLLOW_STEP": "6"})
    env.update(env더 or {})
    p = subprocess.run(["bash", str(ROOT / "scripts" / "dig_loop.sh")] + argv
                       + [str(낼것)] if argv else ["bash", str(ROOT / "scripts" / "dig_loop.sh")],
                       capture_output=True, text=True, env=env, timeout=초 + 40)
    return (p.returncode, p.stdout + p.stderr,
            부른것.read_text(encoding="utf-8").splitlines(),
            낼것.read_text(encoding="utf-8") if 낼것.exists() else "")


print("── 파일이 실제로 도는가 ────────────────────────────────────")
끝, 화면, 부른것, 난것 = 돌리기(가짜dig, ["중화역 맛집", "1"])
ok("No such file or directory" not in 화면 and "bad substitution" not in 화면,
   "**한글 변수명으로 안 죽는다** -- seek.sh 는 여기서 첫 줄부터 죽었다")
ok("unbound variable" not in 화면, "set -u 아래에서 안 죽는다")
ok(끝 == 0, f"끝값 0 (받았으므로) -- 실제 {끝}")
ok(len(부른것) >= 2, f"dig 를 여러 번 부른다 ({len(부른것)}회) -- 한 번이면 루프가 아니다")

print()
print("── 두 걸음으로 가는가 ──────────────────────────────────────")
ok(any("--찾기" in c and "--json" in c for c in 부른것),
   "**먼저 주소를 캔다** (--찾기 --json)")
ok(any("--url" in c for c in 부른것), "**그 다음 그 주소를 판다** (--url)")
첫캐기 = next(i for i, c in enumerate(부른것) if "--찾기" in c)
첫파기 = next(i for i, c in enumerate(부른것) if "--url" in c)
ok(첫캐기 < 첫파기, "캐고 나서 판다 -- 순서가 뒤집히면 팔 주소가 없다")
ok(any("ex1.kr" in c for c in 부른것),
   "**캔 주소를 실제로 판다** -- 캐 놓고 안 파면 라운드가 헛돈다")

print()
print("── 같은 주소를 두 번 파지 않는가 ───────────────────────────")
판것 = [u for c in 부른것 if "--url" in c
       for u in c.split() if u.startswith("http")]
ok(판것 and len(판것) == len(set(판것)),
   f"**안 판 것부터 판다** ({len(판것)}개, 겹침 {len(판것) - len(set(판것))}) -- "
   "겹치면 남은 시간을 같은 쪽에 쓴다")

print()
print("── 라운드마다 더 깊이 파는가 ───────────────────────────────")
따라 = [c.split("--따라")[1].split()[0] for c in 부른것 if "--따라" in c]
ok(len(따라) >= 2 and 따라[0] == "8" and int(따라[1]) > int(따라[0]),
   f"**--따라 가 커진다** ({' -> '.join(따라[:4])}) -- 얕은 데만 되풀이하면 새것이 없다")
ok(any("--찾" in c and "중화역,맛집" in c for c in 부른것),
   "**--찾 말을 물음에서 뽑는다** -- 여기서 지어내면 그것이 하드코딩이다")

print()
print("── 캔 것이 파일에 쌓이는가 ─────────────────────────────────")
ok("9,000원" in 난것, "**받은 것이 파일에 들어간다**")
ok("라운드 1" in 난것, "어느 라운드 것인지 갈라 적는다")
ok("육개장" in 난것 and 난것.count("## 글") >= 2, "여러 쪽이 한 파일에 쌓인다")
ok("판 주소" in 화면 and "받은 쪽" in 화면 and "글자" in 화면,
   "**얼마나 캤는지 세어서 낸다** -- 안 세면 돌았는지도 모른다")
요약 = 화면.split("── 끝 ")[-1].splitlines()
떠도는 = [L for L in 요약 if L.strip() and not L.startswith(("  ", "─"))]
ok(not 떠도는,
   f"**요약에 떠도는 줄이 없다** (찾은 것: {떠도는}) -- `grep -c` 는 안 맞으면 0 을 "
   "찍고 **끝값 1 도** 낸다. `|| echo 0` 을 붙이면 0 이 두 번 찍힌다")
캔값줄 = [L for L in 요약 if "캔값" in L]
ok(캔값줄 and 캔값줄[0].split()[-1].isdigit() and int(캔값줄[0].split()[-1]) >= 2,
   f"**캔값 줄을 실제로 센다** ({캔값줄}) -- 꼴이 안 맞으면 늘 0 이라 눈치를 못 챈다")

print()
print("── 한 라운드가 실패해도 루프가 사는가 ──────────────────────")
끝2, 화면2, 부른것2, _난것2 = 돌리기(실패dig, ["안 열리는 것", "1"])
ok(len(부른것2) >= 2,
   f"**403 이 나도 계속 판다** ({len(부른것2)}회) -- dig 의 끝값 3 은 정상이고, "
   "거기서 죽으면 남은 시간을 통째로 버린다")
ok("라운드" in 화면2 or "주소" in 화면2, "그래도 끝에 세어서 낸다")

print()
print("── 시간을 지키는가 ─────────────────────────────────────────")
# 위의 가짜는 주소가 여섯뿐이라 **씨앗이 떨어져서** 멈춘다 -- 그것은 마감을 지킨
# 것이 아니다. 진짜 위험은 팔 것이 끝없을 때이므로, 부를 때마다 **새 주소를 주는**
# 가짜로 잰다. 여기서 안 멈추면 "10분" 이라 해 놓고 밤새 돈다.
끝없는dig = r'''#!/usr/bin/env python3
import json, os, sys
기록 = os.environ["DIG_CALLS"]
with open(기록, "a", encoding="utf-8") as f:
    f.write(" ".join(sys.argv[1:]) + "\n")
번 = sum(1 for _ in open(기록, encoding="utf-8"))
if "--찾기" in sys.argv:
    if "--json" in sys.argv:
        print(json.dumps({"찾은주소": [
            {"주소": f"https://ex.kr/{번}/{i}", "글": "", "값": 9}
            for i in range(1, 9)]}, ensure_ascii=False))
    sys.exit(0)
print("## 글 [x] (3자)\n  9,000원")
'''
import time                                                    # noqa: E402
잰것 = time.time()
_끝3, 화면3, 부른것3, _ = 돌리기(끝없는dig, ["끝없이", "1"], 초=10)
걸린 = time.time() - 잰것
ok("더 팔 주소가 없다" not in 화면3,
   f"(이 가짜는 팔 것이 안 떨어진다 -- {len(부른것3)}회 불렀다)")
ok(걸린 < 24, f"**팔 것이 끝없어도 마감에서 멈춘다** ({걸린:.1f}초 / 준 것 10초) -- "
   "안 멈추면 10분이라 해 놓고 밤새 돈다")
# 마지막 3초는 안 쓴다 -- 그 짧은 시간에 새 라운드를 열어 봐야 timeout 에 걸려
# 받다 만 것만 남는다. 진짜 라운드는 수십 초짜리라 실제로는 셈에 안 든다.
ok(걸린 >= 6, f"**남은 시간을 다 쓴다** ({걸린:.1f}초 / 마감 10초, 끝 3초는 안 씀) -- "
   "일찍 나오면 캘 것을 두고 나온 것")

print()
print("── 줄 것이 없으면 무엇을 하라고 하는가 ─────────────────────")
p = subprocess.run(["bash", str(ROOT / "scripts" / "dig_loop.sh")],
                   capture_output=True, text=True, timeout=30)
ok(p.returncode == 3, f"물음이 없으면 끝값 3 (실제 {p.returncode})")
ok("bash scripts/dig_loop.sh" in p.stdout, "어떻게 부르는지 적어 준다")

print()
print("── 셸에 한글 변수명이 없는가 ───────────────────────────────")
import re                                                      # noqa: E402
글 = (ROOT / "scripts" / "dig_loop.sh").read_text(encoding="utf-8")
코드 = "\n".join(L for L in 글.splitlines() if not L.lstrip().startswith("#"))
한글대입 = re.findall(r"^\s*([가-힣][가-힣A-Za-z0-9_]*)=", 코드, re.M)
ok(not 한글대입,
   f"**한글 변수명이 없다** (찾은 것: {한글대입}) -- bash 는 대입이 아니라 명령어로 읽는다")

print()
if fails:
    print(f"dig 루프: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("실제로 돎 · 캐고 나서 팜 · 안 판 것부터 · 라운드마다 깊게 · "
      "실패해도 살아남음 · 시간을 지킴 -- 통과")
