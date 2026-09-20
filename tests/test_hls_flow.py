# -*- coding: utf-8 -*-
"""C++ 모델 · HLS · 무료 합성 흐름을 **실제로 돌려** 본다.

## 이 검사가 붙드는 것

`edu/model/` 은 한 벌의 C++ 이 **골든모델이자 HLS 입력**이라는 구조에 기대고
있다.  그 구조가 조용히 깨지는 길이 셋 있고, 셋 다 그럴듯한 초록을 낸다.

    1. 세 변형이 갈라진다      -- naive/narrow/folded 가 다른 함수가 된다
    2. RTL 이 모델과 갈라진다   -- 손RTL 이 C++ 골든을 안 따른다
    3. 비교가 아무것도 안 본다  -- 자극이 얕아 늘 같은 값만 나온다

셋 다 **재서** 막는다.  3번이 특히 중요하다 -- 1·2번만 보는 검사는
자극이 전부 0 이어도 초록이다.

## 셸 스크립트는 돌려서 검사한다

`edu/house/synth.sh` 는 `bash -n` 으로는 아무것도 안 잡힌다.  이 저장소가
이미 물린 자리다: 한글 변수명은 문법상 멀쩡한 '명령어'라서 `bash -n` 을
통과하고 **실행할 때** 죽는다.  그래서 여기서는 진짜로 돌린다.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
모델 = os.path.join(뿌리, "edu", "model")
합성 = os.path.join(뿌리, "edu", "house", "synth.sh")

_틀림 = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        _틀림.append(말)


def 돌려(cmd, cwd=None, 시간=600):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          timeout=시간, shell=isinstance(cmd, str))


def test_셸에_한글_식별자가_없다():
    """bash 는 한글 식별자를 못 받는다.  **규칙이 아니라 검사로 붙든다.**

    실측 2026-09-19: 이 저장소의 CLAUDE.md 에 그 규칙이 적혀 있는데도
    `synth.sh` 첫 판이 `파일=...` 로 쓰여 한 줄도 안 돌았다.
    적어 두는 것과 지키는 것은 다르다.
    """
    print("\n== synth.sh 에 한글 변수명이 없다 ==")
    t = open(합성, encoding="utf-8").read()
    # 주석을 뺀 실행 줄만 본다
    줄들 = [l.split("#")[0] for l in t.splitlines()]
    나쁜 = [l.strip() for l in 줄들
           if re.search(r"(^|[;&|]\s*)[가-힣_][가-힣A-Za-z0-9_]*\s*=", l)
           or re.search(r"\$\{?[가-힣]", l)]
    ok(not 나쁜, f"한글 변수명/참조가 없다 (찾은 것 {나쁜[:3]})")


def test_세_변형이_같은_함수다():
    """naive · narrow · folded 가 비트까지 같은지 **재서** 본다."""
    print("\n== C++ 세 변형이 같은 함수다 ==")
    if not shutil.which("g++"):
        ok(False, "g++ 가 없다 -- 이 검사는 g++ 를 요구한다")
        return
    with tempfile.TemporaryDirectory() as d:
        exe = os.path.join(d, "equiv")
        r = 돌려(["g++", "-O2", "-I" + 모델, "-o", exe,
                 os.path.join(모델, "equiv.cpp")])
        ok(r.returncode == 0, f"equiv.cpp 가 컴파일된다 ({r.stderr[:120]})")
        if r.returncode:
            return
        # 전수는 30초다.  검사 스위트에서는 걸음 32 로 훑는다 (1.5억 점)
        r = 돌려([exe, "32"], 시간=300)
        ok(r.returncode == 0, f"등가성 확인이 통과한다 (rc={r.returncode})")
        수 = dict(re.findall(r"(\S+) (\d+)", r.stdout))
        ok(수.get("다름01") == "0", f"naive 와 narrow 가 같다 (다름 {수.get('다름01')})")
        ok(수.get("다름02") == "0", f"naive 와 folded 가 같다 (다름 {수.get('다름02')})")
        ok(int(수.get("출력값가지수", 0)) >= 2,
           f"**출력이 여러 가지다** -- 한 가지뿐이면 이 확인은 아무것도 안 본 것이다 "
           f"({수.get('출력값가지수')} 가지)")
        ok(int(수.get("본것", 0)) > 10_000_000,
           f"실제로 많이 봤다 ({int(수.get('본것', 0)):,} 점)")


def test_손RTL이_Cpp골든을_따른다():
    """C++ 이 낸 벡터로 손으로 쓴 Verilog 를 잰다.  그리고 **자해검사**까지."""
    print("\n== 손RTL 이 C++ 골든과 같다 ==")
    if not all(shutil.which(x) for x in ("g++", "iverilog", "vvp")):
        ok(False, "g++/iverilog/vvp 가 없다")
        return
    with tempfile.TemporaryDirectory() as d:
        vec = os.path.join(d, "vectors")
        r = 돌려(["g++", "-O2", "-I" + 모델, "-DFIR_VARIANT=2", "-o", vec,
                 os.path.join(모델, "vectors.cpp")])
        ok(r.returncode == 0, f"vectors.cpp 가 컴파일된다 ({r.stderr[:120]})")
        if r.returncode:
            return
        r = 돌려([vec, "400", "1"])
        open(os.path.join(d, "vec.txt"), "w").write(r.stdout)
        줄수 = len(r.stdout.strip().splitlines())
        ok(줄수 == 400, f"벡터가 400 줄 나온다 ({줄수})")

        벌 = os.path.join(d, "a.out")
        r = 돌려(["iverilog", "-g2012", "-DDUT=fir4_hand", "-o", 벌,
                 os.path.join(모델, "fir_tb.v"), os.path.join(모델, "fir4_hand.v")])
        ok(r.returncode == 0, f"손RTL 이 컴파일된다 ({r.stderr[:160]})")
        if r.returncode:
            return
        r = 돌려([벌], cwd=d)
        m = re.search(r"잰것 (\d+)\s+틀림 (\d+)", r.stdout)
        ok(m is not None, f"결과 줄이 나온다 ({r.stdout[-160:]})")
        if m:
            ok(m.group(1) == "400", f"400 개를 다 쟀다 ({m.group(1)})")
            ok(m.group(2) == "0", f"틀린 것이 없다 ({m.group(2)})")

        # **자해검사** -- 골든을 망가뜨리면 반드시 걸려야 한다.
        # 이것이 없으면 위의 '틀림 0' 은 비교가 도는지 안 도는지 모르는 수다.
        좋은 = open(os.path.join(d, "vec.txt")).read().splitlines()
        나쁜 = list(좋은)
        조각 = 나쁜[7].split()
        조각[4] = str(int(조각[4]) + 1)
        나쁜[7] = " ".join(조각)
        open(os.path.join(d, "vec.txt"), "w").write("\n".join(나쁜) + "\n")
        r = 돌려([벌], cwd=d)
        m2 = re.search(r"잰것 (\d+)\s+틀림 (\d+)", r.stdout)
        ok(m2 is not None and m2.group(2) != "0",
           f"**골든을 한 줄 망가뜨리면 걸린다** -- 안 걸리면 비교가 DUT 를 안 보는 것이다 "
           f"(틀림 {m2.group(2) if m2 else '?'})")


def test_synth_sh_가_실제로_센다():
    """합성 스크립트를 돌려 셀 수가 진짜로 나오는지 본다."""
    print("\n== synth.sh 가 셀 수를 낸다 ==")
    if not all(shutil.which(x) for x in ("yosys", "verilator")):
        ok(False, "yosys/verilator 가 없다")
        return
    with tempfile.TemporaryDirectory() as d:
        env = dict(os.environ, SYNTH_OUT=d)
        r = subprocess.run(["bash", 합성, os.path.join(모델, "fir4_hand.v"),
                            "fir4_hand"], capture_output=True, text=True,
                           timeout=600, env=env)
        ok("No such file or directory" not in r.stdout + r.stderr,
           "스크립트가 실제로 돈다 (한글 변수명 사고가 아니다)")
        ok("bad substitution" not in r.stdout + r.stderr,
           "치환 오류가 없다")
        m = re.search(r"SB_LUT4\s+(\d+)", r.stdout)
        ok(m is not None, f"iCE40 LUT 수를 읽는다 ({r.stdout[-200:] if not m else m.group(1)})")
        if m:
            ok(int(m.group(1)) > 10,
               f"**셀이 실제로 있다** -- 0 이면 합성이 빈 모듈을 낸 것이다 ({m.group(1)})")
        m2 = re.search(r"SB_DFF\w*\s+(\d+)", r.stdout)
        ok(m2 is not None and int(m2.group(1)) == 9,
           f"플립플롭이 9 개다 -- done_port 1 + return_port 8 "
           f"({m2.group(1) if m2 else '?'})")


def test_그림_라이브러리가_SVG를_깨지_않는다():
    """`sch.py` 가 SVG 를 닫는지, 그리고 HTML 탈출 태그를 막는지."""
    print("\n== sch.py 가 성한 SVG 를 낸다 ==")
    sys.path.insert(0, os.path.join(뿌리, "edu"))
    import sch
    for 이름, 만들기 in (("씨모스인버터", sch.씨모스인버터),
                      ("씨모스낸드", sch.씨모스낸드),
                      ("전가산기", sch.전가산기),
                      ("개방드레인과정적씨모스", sch.개방드레인과정적씨모스)):
        x = 만들기()
        ok(x.startswith("<svg") and x.rstrip().endswith("</svg>"),
           f"{이름}: SVG 가 열리고 닫힌다")
        ok(x.count("<svg") == x.count("</svg>"), f"{이름}: svg 짝이 맞는다")

    # HTML 탈출 태그 관문.  실측으로 그림 반쪽이 사라진 자리다.
    깼나 = False
    try:
        sch.글(0, 0, "R<sub>pu</sub>")
    except ValueError:
        깼나 = True
    ok(깼나, "**<sub> 를 넣으면 물린다** -- HTML 파서가 거기서 SVG 를 끝낸다")
    ok("<sub" not in sch.씨모스인버터() and "<sub" not in sch.개방드레인과정적씨모스(),
       "그림 안에 탈출 태그가 없다")


if __name__ == "__main__":
    for f in (test_셸에_한글_식별자가_없다,
              test_세_변형이_같은_함수다,
              test_손RTL이_Cpp골든을_따른다,
              test_synth_sh_가_실제로_센다,
              test_그림_라이브러리가_SVG를_깨지_않는다):
        f()
    print()
    if _틀림:
        print(f"실패 {len(_틀림)}개 -- {_틀림}")
        sys.exit(1)
    print("C++ 모델 · HLS 배선 · 무료 합성 · 그림 -- 통과")
