r"""**성능개선** -- 실제로 빨라진 것만 받아들이는가.

    python3 tests/test_perf.py

붙드는 것: 빨라지면 ACCEPT · 느려지면 REJECT · **V 가 빨갛면 시간을 아예 안 잰다** ·
잡음과 구별 안 되면 REJECT · 번갈아 돌리나 · 잡음바닥을 모르면 모른다고 하나.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import perf as PF                                                  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=False)


os.environ.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})


def 판짓기(자는초: float, 터질까=False):
    """벽시계를 정해진 만큼 쓰는 '프로그램' 하나. 성능 차이를 만들어 낸다."""
    판 = Path(tempfile.mkdtemp(prefix="test-perf-"))
    git(판, "init", "-q")
    (판 / "tests").mkdir()
    몸 = (f"import time\ntime.sleep({자는초})\n"
         + ("raise SystemExit(3)\n" if 터질까 else "print('했다')\n"))
    (판 / "일.py").write_text(몸, encoding="utf-8")
    (판 / "tests" / "test_일.py").write_text(
        'import sys; sys.path.insert(0, ".")\nprint("초록")\n', encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "i")
    return 판


PF.워크로드들["시늉"] = {"argv": ["python3", "-B", "일.py"], "왜": "검사용 -- 정해진 만큼 잔다"}
초록V = lambda a, b: (True, "검사를 주입했다")                        # noqa: E731

print("== 잡음바닥과 분포 갈림 ==")
ok(PF.흔들림([1.0, 1.0]) is None,
   "**표본이 적으면 None 이다** -- 모르는 것을 0 으로 채우면 모든 Δ 가 개선이 된다")
ok(PF.흔들림([1.0, 1.0, 1.0]) == 0.0, "흔들리지 않으면 0 이다")
ok(PF.흔들림([1.0, 2.0, 3.0]) == 1.0, "MAD -- 중앙값에서의 중앙 거리")
ok(PF.잡음바닥([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0,
   "**짝이 맞으면 짝차의 흔들림을 쓴다** -- 같이 흔들리는 것은 짝 안에서 상쇄된다")
ok(PF.잡음바닥([1.0, 2.0, 3.0], [1.0, 2.0]) == 1.0,
   "짝이 안 맞으면(한쪽이 터지면) 계열의 흔들림으로 돌아간다 -- 짝이 없으니 그럴 수밖에 없다")
ok(PF.잡음바닥([1.0], [1.0]) is None, "못 재면 None")
ok(PF.짝차([1.0, 2.0], [0.5, 2.5]) == [-0.5, 0.5] and PF.짝Δ([1.0, 2.0], [0.5, 2.5]) == 0.0,
   "짝차와 그 중앙값")

# **실측 2026-09-13, 세 번째 교정.** 관문 후보가 **14짝 전부**에서 빨랐는데(p 0.006%)
# `MAD(바탕)+MAD(후보)` = 0.509 가 Δ -0.364 를 덮어 REJECT 가 났다. 긴 판에서 기계 부하가
# 흘러(바탕 13.78~14.80초) 두 MAD 가 같이 부풀었는데 **그 흐름은 짝 안에서 상쇄된다.**
# 방향은 짝으로 보면서 크기는 안 짝으로 본 것 -- 같은 실수를 다른 항에서 되풀이했다.
_바14 = [14.2894, 13.8804, 13.809, 14.3928, 14.796, 14.3648, 14.4247,
        14.6814, 14.1367, 14.6021, 14.1938, 13.8433, 13.7818, 13.9581]
_후14 = [13.8897, 13.4659, 13.5037, 13.8059, 13.9916, 14.1296, 14.0017,
        13.8985, 14.1251, 14.0159, 13.8657, 13.4942, 13.4452, 13.6411]
ok(PF.짝이김(_바14, _후14) == (14, 14), f"그 실측은 14짝 전부 후보가 빨랐다 ({PF.짝이김(_바14, _후14)})")
ok(PF.부호검정p(14, 14) < 0.0001, f"p = {PF.부호검정p(14, 14):.5f}")
ok(PF.잡음바닥(_바14, _후14) == 0.0633,
   f"**짝차의 MAD 는 0.063 이다** (안 짝으로 재면 0.509) ({PF.잡음바닥(_바14, _후14)})")
ok(abs(PF.짝Δ(_바14, _후14)) > PF.잡음바닥(_바14, _후14) * 5,
   f"짝 이득 {abs(PF.짝Δ(_바14, _후14))} 이 짝 흔들림의 다섯 배를 넘는다 -- 구별된다")
# **문턱을 낮춘 것이 아니다.** 짝 기준이 느슨해지는 것은 **둘이 같이 흔들릴 때뿐**이고,
# 그때는 그것이 옳다(흐름은 짝 안에서 상쇄된다). 짝마다 방향이 엇갈리면 느슨해지지 않는다.
_같이 = ([1.0, 2.0, 3.0, 4.0], [1.1, 2.1, 3.1, 4.1])          # 같이 흐른다 + 일정하게 0.1 느림
ok(PF.잡음바닥(*_같이) == 0.0 and (PF.흔들림(_같이[0]) + PF.흔들림(_같이[1])) == 2.0,
   f"같이 흔들리면 짝 바닥이 작다 ({PF.잡음바닥(*_같이)} vs 안 짝 "
   f"{PF.흔들림(_같이[0]) + PF.흔들림(_같이[1])}) -- 그 흐름은 이득도 손해도 아니다")
_엇갈 = ([1.0, 2.0, 1.0, 2.0, 1.0, 2.0], [2.0, 1.0, 2.0, 1.0, 2.0, 1.0])
ok(PF.잡음바닥(*_엇갈) >= (PF.흔들림(_엇갈[0]) + PF.흔들림(_엇갈[1])),
   f"엇갈리면 **느슨해지지 않는다** ({PF.잡음바닥(*_엇갈)} >= "
   f"{PF.흔들림(_엇갈[0]) + PF.흔들림(_엇갈[1])}) -- 문턱을 낮춘 것이 아니다")
ok(PF.갈렸나([1.0, 1.1, 1.2], [0.8, 0.85, 0.9]),
   "보조 길: 가장 느린 후보가 가장 빠른 바탕보다 빠르면 갈렸다")
ok(not PF.갈렸나([1.0, 1.1, 1.2], [0.9, 1.05, 1.3]), "겹치면 안 갈렸다")
ok(not PF.갈렸나([1.0, 1.1], [0.1, 0.2]), "표본이 적으면 갈렸다고 하지 않는다")

# **실측 2026-09-13:** 관문 13.94 -> 13.64초(2.1%)를 REJECT 했다. 일곱 짝 **전부** 후보가
# 빨랐는데, 4·5회차에 부하가 올라 양쪽이 같이 느려져 *짝이 아닌* 최대·최소가 겹쳤다.
# 번갈아 돌려 짝을 만들어 놓고 짝 정보를 버린 것이 잘못이었다.
바 = [13.8414, 13.9387, 13.9628, 14.1562, 14.1286, 13.8949, 13.6885]
후 = [13.5843, 13.6869, 13.3646, 13.9440, 13.9401, 13.6395, 13.4839]
ok(not PF.갈렸나(바, 후), "그 실측은 분포로는 겹친다(부하가 중간에 올라갔다)")
ok(PF.짝이김(바, 후) == (7, 7), f"**짝으로 보면 일곱 전부 후보가 빨랐다** ({PF.짝이김(바, 후)})")
ok(PF.짝으로갈렸나(바, 후), "**그러면 갈렸다고 한다** -- 부호검정 p = 0.78%")

# **실측 2026-09-13, 고친 기준으로 다시 재니 6/7 이 나왔다(Δ -0.42초 · 3.0%).** "전부 이겨야
# 한다" 는 규칙은 그것을 거절했는데 그 거절은 **우연히 옳았다** -- 6/7 은 p=6.25% 로 실제로
# 못 미친다. 하지만 그 규칙은 n 을 안 보므로 6/6(1.56%)은 받고 11/12(0.32%)는 버린다.
# p 를 직접 세면 문턱이 하나가 되고, 못 넘었을 때 몇 짝이 더 필요한지도 말할 수 있다.
ok(abs(PF.부호검정p(7, 7) - 1 / 128) < 1e-9, f"7/7 은 p = 1/128 = 0.78% ({PF.부호검정p(7,7):.4f})")
ok(abs(PF.부호검정p(6, 7) - 8 / 128) < 1e-9, f"6/7 은 p = 8/128 = 6.25% ({PF.부호검정p(6,7):.4f})")
ok(not PF.짝으로갈렸나(바, 후[:-1] + [99.0]),
   "**6/7 은 안 받는다** -- 규칙이 아니라 p 가 문턱을 못 넘어서다")
ok(PF.부호검정p(11, 12) < PF.부호문턱 < PF.부호검정p(6, 6),
   f"**11/12(p {PF.부호검정p(11,12):.2%})는 받고 6/6(p {PF.부호검정p(6,6):.2%})은 안 받는다** "
   "-- '전부 이겨야 한다' 는 이 둘을 거꾸로 판정했다")
ok(PF.부호검정p(1, 2) is None, f"짝이 {PF.짝최소}개 미만이면 None -- 모르는 것은 모른다고 한다")
ok(PF.몇짝이면(6, 7) == 14,
   f"**못 넘었으면 몇 짝이 필요한지 말한다** ({PF.몇짝이면(6, 7)}짝) -- 기준을 낮추지 말고 표본을 늘린다")
ok(PF.몇짝이면(1, 7) is None, "승률이 낮으면 표본을 늘려도 안 된다고 말한다")

print("\n== 빨라지면 ACCEPT · 느려지면 REJECT ==")
느림, 빠름 = 판짓기(0.30), 판짓기(0.05)
try:
    r = PF.성능개선(느림, 빠름, "시늉", 반복=5, V=초록V, 말하기=lambda s: None)
    ok(r["결정"] == "ACCEPT", f"**0.30초 -> 0.05초 는 ACCEPT** (Δ {r['Δ']})")
    ok(r["Δ"] is not None and r["Δ"] < 0, f"Δ 가 음수다 ({r['Δ']})")
    ok(r["J후보"] > r["J바탕"], f"**J = 1/t 가 올랐다** ({r['J바탕']} -> {r['J후보']})")
    ok(any("빠름" in x for x in r["까닭"]), f"몇 % 빨라졌는지 적는다 ({r['까닭'][1][:60]})")
    # **무엇이 다른지 늘 적는다.** 실측 2026-09-13: 후보 판을 떠 놓고 그 뒤 커밋을 더 해서
    # 비교가 오염된 일이 두 번 났고, 출력에서 알 길이 없었다(V 가 고른 검사 수로만 눈치챘다).
    ok("바뀐파일" in r["잰것"],
       "결과가 **두 판의 차이**를 담는다 -- 오염된 벤치마크는 수가 나오기 때문에 더 위험하다")
    ok(isinstance(r["잰것"]["바뀐파일"], list),
       f"파일 목록이다 ({r['잰것']['바뀐파일'][:3]})")
    거꾸로 = PF.성능개선(빠름, 느림, "시늉", 반복=5, V=초록V, 말하기=lambda s: None)
    ok(거꾸로["결정"] == "REJECT" and any("느려졌" in x for x in 거꾸로["까닭"]),
       f"거꾸로는 REJECT ({거꾸로['까닭'][:1]})")

    print("\n== 잡음과 구별되지 않으면 REJECT ==")
    같음1, 같음2 = 판짓기(0.10), 판짓기(0.10)
    try:
        같 = PF.성능개선(같음1, 같음2, "시늉", 반복=6, V=초록V, 말하기=lambda s: None)
        ok(같["결정"] == "REJECT",
           f"**같은 프로그램 둘은 ACCEPT 가 아니다** (Δ {같['Δ']} · 잡음바닥 {같['잰것']['잡음바닥']})")
        ok(any("잡음" in x or "느려졌" in x or "우연일 수 있다" in x for x in 같["까닭"]),
           f"까닭이 잡음·안 빨라짐·짝 쏠림 없음 중 하나다 ({같['까닭'][:1]})")
    finally:
        shutil.rmtree(같음1, ignore_errors=True); shutil.rmtree(같음2, ignore_errors=True)

    print("\n== 번갈아 돌린다 -- 기계 부하의 흐름을 Δ 로 읽지 않게 ==")
    견 = PF.견주기(느림, 빠름, PF.워크로드들["시늉"]["argv"], 반복=4, 말하기=lambda s: None)
    ok(len(견["바탕표본"]) == 4 and len(견["후보표본"]) == 4,
       f"양쪽을 같은 횟수로 잰다 ({len(견['바탕표본'])} · {len(견['후보표본'])})")
    ok(견["잡음바닥"] is not None and 견["짝이김"][1] == 4,
       f"잡음바닥과 짝을 같은 표본에서 얻는다 (바닥 {견['잡음바닥']} · 짝 {견['짝이김']})")

    print("\n== V 가 빨갛면 **시간을 아예 안 잰다** ==")
    빨강V = lambda a, b: (False, "검사가 빨갛다")                     # noqa: E731
    rv = PF.성능개선(느림, 빠름, "시늉", 반복=5, V=빨강V, 말하기=lambda s: None)
    ok(rv["결정"] == "REJECT" and rv["V"] is False, "V 가 빨갛면 REJECT")
    ok(rv["Δ"] is None and "바탕중앙값" not in (rv["잰것"] or {}),
       f"**시간이 없다** -- 재면 그 수가 근거처럼 보인다 (잰것 {list((rv['잰것'] or {}))})")
    ok(any("깨진 것이 빠른 것은 개선이 아니다" in x for x in rv["까닭"]),
       "까닭에 그렇게 적는다")

    print("\n== 워크로드가 터지면 REJECT ==")
    터짐 = 판짓기(0.05, 터질까=True)
    try:
        rt = PF.성능개선(느림, 터짐, "시늉", 반복=4, V=초록V, 말하기=lambda s: None)
        ok(rt["결정"] == "REJECT" and any("터졌" in x for x in rt["까닭"]),
           f"**터진 것의 시간은 성능이 아니다** ({rt['까닭'][:1]})")
    finally:
        shutil.rmtree(터짐, ignore_errors=True)
    ok(PF.성능개선(느림, 빠름, "없는워크로드", V=초록V)["결정"] == "REJECT",
       "모르는 워크로드면 REJECT")

    print("\n== 기본 V: 바뀐 파일을 재는 검사를 돌린다 ==")
    깨짐 = Path(tempfile.mkdtemp(prefix="test-perfV-"))
    try:
        git(깨짐, "init", "-q")
        (깨짐 / "tests").mkdir()
        (깨짐 / "계산.py").write_text("def 더하기(a, b):\n    return a + b\n", encoding="utf-8")
        (깨짐 / "tests" / "test_계산.py").write_text(
            'import sys; sys.path.insert(0, ".")\nimport 계산\nassert 계산.더하기(1, 2) == 3\n'
            'print("본다")\n', encoding="utf-8")
        git(깨짐, "add", "-A"); git(깨짐, "commit", "-qm", "i")
        좋 = Path(tempfile.mkdtemp(prefix="test-perfV2-"))
        shutil.rmtree(좋); shutil.copytree(깨짐, 좋)
        (좋 / "계산.py").write_text("def 더하기(a, b):\n    return a - b\n", encoding="utf-8")
        통과, 말 = PF.기본V(깨짐, 좋)
        ok(not 통과 and "test_계산" in 말, f"**바뀐 파일을 재는 검사가 빨갛면 V 가 안 선다** ({말[:60]})")
        ok(PF._바뀐파일들(깨짐, 좋) == ["계산.py"], f"바뀐 파일을 정확히 찾는다 ({PF._바뀐파일들(깨짐, 좋)})")
        같 = Path(tempfile.mkdtemp(prefix="test-perfV3-"))
        shutil.rmtree(같); shutil.copytree(깨짐, 같)
        통과2, 말2 = PF.기본V(깨짐, 같)
        ok(not 통과2 and "못 찾았다" in 말2,
           f"**바뀐 것이 없으면 V 를 못 쟀다고 한다** -- 안 쟀으면 받아들이지 않는다 ({말2[:50]})")
        shutil.rmtree(좋, ignore_errors=True); shutil.rmtree(같, ignore_errors=True)
    finally:
        shutil.rmtree(깨짐, ignore_errors=True)

    print("\n== 원장 · 보고 ==")
    집 = Path(tempfile.mkdtemp(prefix="test-perf원장-"))
    ok("비어 있다" in PF.보고(집), "기록이 없으면 없다고 말한다")
    PF.적기(집, r, "바탕갈래", "후보갈래")
    PF.적기(집, 거꾸로, "후보갈래", "바탕갈래")
    ok(len(PF.기록들(집)) == 2, "덧붙이기만 한다")
    줄 = PF.기록들(집)[0]
    빠진 = [k for k in ("워크로드", "바탕중앙값", "후보중앙값", "Δ", "잡음바닥", "J바탕", "J후보",
                      "결정", "바탕표본") if k not in 줄]
    ok(not 빠진, f"원장 줄에 표본까지 다 있다 (빠진 것 {빠진})")
    ok("ACCEPT 1 / 2" in PF.보고(집), f"보고가 받아들인 수를 센다 ({PF.보고(집).splitlines()[-2][:40]})")
    shutil.rmtree(집, ignore_errors=True)
finally:
    shutil.rmtree(느림, ignore_errors=True); shutil.rmtree(빠름, ignore_errors=True)

print("\n== 배선 ==")
ok("perf.py" in (ROOT / ".github/workflows/deploy-oracle.yml").read_text(encoding="utf-8"),
   "배포가 perf.py 를 서버에 올린다")
ok(set(PF.워크로드들) >= {"관문", "변형생성", "검사고르기", "요약"}, "실제로 도는 워크로드가 등록돼 있다")
for 이름, 일 in PF.워크로드들.items():
    ok(bool(일.get("왜")), f"워크로드 `{이름}` 이 왜 있는지 적혀 있다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("perf: 잡음바닥 · 빠름 ACCEPT · 느림 REJECT · 잡음 REJECT · V 빨강이면 안 잼 · "
      "터짐 REJECT · 기본V · 원장 -- 통과")
