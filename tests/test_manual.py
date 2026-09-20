# -*- coding: utf-8 -*-
"""매뉴얼(`manual/`)이 **실제로 도는지** 본다.

## 왜 매뉴얼을 검사하나

매뉴얼의 실패 방식은 코드와 다르다.  코드는 안 돌면 바로 티가 나는데,
**매뉴얼은 틀려도 조용하다** -- 그것을 따라 하는 사람이 막힐 때까지.
그리고 그 사람은 대개 "내가 뭘 잘못했나" 로 시간을 쓴다.

그래서 매뉴얼이 시키는 것을 기계가 그대로 해 본다:

    1. `지금어디.sh` 가 도는가 (한글 변수명 사고가 아닌가)
    2. **뼈대 셋이 이어 붙어 실제로 통과하는가**
       golden.cpp -> vec.txt -> block.v + block_tb.v -> 틀림 0
    3. 그 검증이 **물기는 하는가** (정답을 망가뜨리면 빨개지는가)
    4. 뼈대 RTL 이 lint 경고 0 인가
    5. 문서 사이 링크가 성한가
    6. 채워 넣을 템플릿에 TODO 가 남아 있는가

2·3 이 핵심이다.  "복사하면 돈다" 고 적어 놓고 안 돌면 매뉴얼 전체를
못 믿게 된다.  그리고 3 이 없으면 2 의 '틀림 0' 은 아무 뜻이 없다 --
매뉴얼이 가르치는 바로 그 규율이다.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
매뉴얼 = os.path.join(뿌리, "manual")
템플릿 = os.path.join(매뉴얼, "템플릿")

_틀림 = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        _틀림.append(말)


def 돌려(cmd, cwd=None, 시간=600):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          timeout=시간, shell=isinstance(cmd, str))


def test_상태스크립트가_돈다():
    print("\n== 지금어디.sh 가 돈다 ==")
    p = os.path.join(매뉴얼, "지금어디.sh")
    ok(os.path.exists(p), "지금어디.sh 가 있다")
    r = 돌려(["bash", "-n", p])
    ok(r.returncode == 0, f"문법이 성하다 ({r.stderr[:120]})")
    r = 돌려(["bash", p])
    합 = r.stdout + r.stderr
    ok("No such file or directory" not in 합,
       "**한글 변수명 사고가 없다** -- bash 는 한글 식별자를 못 받는다")
    ok("bad substitution" not in 합, "치환 오류가 없다")
    ok("단계" in 합, "단계별 상태를 낸다")
    # 실행 줄에 한글 변수 대입/참조가 없는지 글자로도 확인
    t = open(p, encoding="utf-8").read()
    줄들 = [l.split("#")[0] for l in t.splitlines()]
    나쁜 = [l.strip() for l in 줄들
           if re.search(r"(^|[;&|]\s*)[가-힣_][가-힣A-Za-z0-9_]*\s*=", l)
           or re.search(r"\$\{?[가-힣]", l)]
    ok(not 나쁜, f"한글 변수명/참조가 없다 (찾은 것 {나쁜[:2]})")


def test_뼈대가_이어붙어_통과한다():
    """**매뉴얼의 핵심 약속**: 뼈대를 복사하면 그대로 돈다."""
    print("\n== 뼈대 셋이 이어 붙어 검증을 통과한다 ==")
    필요 = ("g++", "iverilog", "vvp", "verilator")
    if not all(shutil.which(x) for x in 필요):
        ok(False, f"도구가 없다 ({필요})")
        return
    with tempfile.TemporaryDirectory() as d:
        for src in (os.path.join(템플릿, "model", "golden.cpp"),
                    os.path.join(템플릿, "rtl", "block.v"),
                    os.path.join(템플릿, "rtl", "block_tb.v")):
            ok(os.path.exists(src), f"{os.path.basename(src)} 가 있다")
            shutil.copy(src, d)

        r = 돌려(["g++", "-O2", "-I.", "-o", "golden", "golden.cpp"], cwd=d)
        ok(r.returncode == 0, f"golden.cpp 가 컴파일된다 ({r.stderr[:160]})")
        if r.returncode:
            return

        # 모델 자기확인 -- 출력이 여러 가지인가
        r = 돌려([os.path.join(d, "golden"), "self"], cwd=d)
        ok(r.returncode == 0 and "여러 가지인가: 예" in r.stdout,
           f"**모델 자기확인이 통과한다** -- 출력이 한 가지면 검증이 무의미하다 "
           f"({r.stdout.strip()[:60]})")

        r = 돌려([os.path.join(d, "golden"), "vec", "400", "1"], cwd=d)
        open(os.path.join(d, "vec.txt"), "w").write(r.stdout)
        줄수 = len(r.stdout.strip().splitlines())
        ok(줄수 == 400, f"벡터가 400 줄 나온다 ({줄수})")

        # lint -- 매뉴얼이 '경고 0' 을 요구하므로 뼈대도 그래야 한다
        r = 돌려(["verilator", "--lint-only", "-Wall",
                 "--top-module", "block", "block.v"], cwd=d)
        경고 = len(re.findall(r"^%(?:Error|Warning)", r.stdout + r.stderr, re.M))
        ok(경고 == 0 and r.returncode == 0,
           f"**뼈대 RTL 이 lint 경고 0** -- 템플릿이 경고를 내면 규칙을 못 가르친다 "
           f"(경고 {경고})")

        r = 돌려(["iverilog", "-g2012", "-o", "sim.out",
                 "block_tb.v", "block.v"], cwd=d)
        ok(r.returncode == 0, f"RTL 이 컴파일된다 ({r.stderr[:160]})")
        if r.returncode:
            return

        r = 돌려([shutil.which("vvp"), "sim.out"], cwd=d)
        m = re.search(r"잰것 (\d+)\s+틀림 (\d+)", r.stdout)
        ok(m is not None, f"결과 줄이 나온다 ({r.stdout[-160:]})")
        if m:
            ok(m.group(1) == "400" and m.group(2) == "0",
               f"**복사하자마자 통과한다** (잰것 {m.group(1)}, 틀림 {m.group(2)})")

        # 노는 사이클 관찰이 실제로 배선돼 있는가
        ok("노는사이클오류" in r.stdout,
           "**노는 사이클을 관찰한다** -- valid=0 구간을 안 보면 변이가 새어 나간다")

        # ---- 자해검사: 이 검증이 물기는 하는가 ----
        좋은 = open(os.path.join(d, "vec.txt")).read().splitlines()
        조각 = 좋은[7].split()
        조각[1] = str(int(조각[1]) + 1)
        좋은[7] = " ".join(조각)
        open(os.path.join(d, "vec.txt"), "w").write("\n".join(좋은) + "\n")
        r = 돌려([shutil.which("vvp"), "sim.out"], cwd=d)
        m2 = re.search(r"틀림 (\d+)", r.stdout)
        ok(m2 is not None and m2.group(1) != "0",
           f"**정답을 망가뜨리면 빨개진다** -- 안 빨개지면 위의 '틀림 0' 은 "
           f"아무 뜻이 없다 (틀림 {m2.group(1) if m2 else '?'})")


def test_매뉴얼대로_따라가면_초록이_된다():
    """**끝까지 따라가 본다.**  매뉴얼이 시키는 대로 하면 `지금어디.sh` 가
    전부 통과가 되는가.  각 문서가 따로 맞는 것과, 이어서 따라갈 수 있는
    것은 다른 문제다.

    실측: 이 검사를 처음 돌렸을 때 `지금어디.sh` 가
    `[: 0\n0: integer expression expected` 로 깨졌다.  `grep -c` 가
    못 찾으면 **0 을 찍고 종료코드 1** 을 내는데 `|| echo 0` 을 붙여
    "0\n0" 이 됐기 때문이다.  문서를 아무리 읽어도 안 보이는 결함이고,
    **따라가 봐야만** 나온다.
    """
    print("\n== 매뉴얼대로 따라가면 전부 통과가 된다 ==")
    필요 = ("g++", "iverilog", "vvp", "bash")
    if not all(shutil.which(x) for x in 필요):
        ok(False, f"도구가 없다 ({필요})")
        return
    with tempfile.TemporaryDirectory() as d:
        # 매뉴얼과 상태 스크립트만 옮긴 가짜 저장소를 만든다
        shutil.copytree(매뉴얼, os.path.join(d, "manual"))
        w = os.path.join(d, "work")
        os.makedirs(os.path.join(w, "model"))
        os.makedirs(os.path.join(w, "rtl"))

        # 02~03: 제품·스펙
        shutil.copy(os.path.join(템플릿, "제품.md"), os.path.join(w, "제품.md"))
        스펙 = open(os.path.join(템플릿, "스펙.md"), encoding="utf-8").read()
        open(os.path.join(w, "스펙.md"), "w", encoding="utf-8").write(
            스펙.replace("TODO", "정함"))

        # 04: 모델
        shutil.copy(os.path.join(템플릿, "model", "golden.cpp"),
                    os.path.join(w, "model", "golden.cpp"))
        r = 돌려(["g++", "-O2", "-I.", "-o", "golden", "golden.cpp"],
                cwd=os.path.join(w, "model"))
        ok(r.returncode == 0, f"04 모델이 선다 ({r.stderr[:120]})")

        # 05: RTL
        for f in ("block.v", "block_tb.v"):
            shutil.copy(os.path.join(템플릿, "rtl", f), os.path.join(w, "rtl", f))

        # 06: 검증
        rtl = os.path.join(w, "rtl")
        r = 돌려([os.path.join(w, "model", "golden"), "vec", "400", "1"], cwd=rtl)
        open(os.path.join(rtl, "vec.txt"), "w").write(r.stdout)
        r = 돌려(["iverilog", "-g2012", "-o", "sim.out", "block_tb.v", "block.v"],
                cwd=rtl)
        ok(r.returncode == 0, f"06 RTL 이 선다 ({r.stderr[:120]})")
        r = 돌려([shutil.which("vvp"), "sim.out"], cwd=rtl)
        m = re.search(r"틀림 (\d+)", r.stdout)
        open(os.path.join(w, "검증결과.txt"), "w", encoding="utf-8").write(
            f"회귀 틀림 {m.group(1) if m else '?'}\n")
        ok(m is not None and m.group(1) == "0", "06 검증이 통과한다")

        # 07~08: 합성 기록과 문서
        open(os.path.join(w, "합성결과.txt"), "w", encoding="utf-8").write("기록\n")
        for f in ("DATASHEET.md", "INTEGRATION.md", "KNOWN_ISSUES.md"):
            s = open(os.path.join(템플릿, f), encoding="utf-8").read()
            open(os.path.join(w, f), "w", encoding="utf-8").write(
                s.replace("TODO", "채움"))

        # 이제 상태 스크립트가 전부 통과라고 말해야 한다
        r = 돌려(["bash", os.path.join(d, "manual", "지금어디.sh")])
        합 = r.stdout + r.stderr
        ok("integer expression expected" not in 합,
           "**상태 스크립트가 깨지지 않는다** (grep -c 종료코드 함정)")
        ok("No such file or directory" not in 합, "한글 변수명 사고가 없다")
        m = re.search(r"남은 것 (\d+) 개", 합)
        ok(m is not None, f"요약 줄이 나온다 ({합[-200:]})")
        if m:
            ok(m.group(1) == "0",
               f"**매뉴얼대로 따라가면 남은 것이 0 이 된다** (남은 것 {m.group(1)})")
        ok("팔 수 있는 모양이다" in 합, "끝나면 다음 단계를 가리킨다")


def test_경로를_박아넣지_않았다():
    """매뉴얼에 **절대경로가 없어야** 한다.

    실측 2026-09-20: 매뉴얼 전체에 `/home/user/SE` 를 박아 넣었다.
    그런데 그것은 **내 컨테이너 경로**이고 사용자의 기계는
    `/home/ubuntu/SE` 였다.  첫 명령부터

        bash: cd: /home/user/SE: No such file or directory

    로 죽었다.  매뉴얼의 첫 줄이 안 돌면 나머지는 읽히지도 않는다.

    고친 방식: `cd "$(git rev-parse --show-toplevel)"`.  저장소 안
    어디서 실행해도 루트를 찾아 주므로 받은 자리가 어디든 상관없다.
    """
    print("\n== 매뉴얼에 절대경로가 없다 ==")
    나쁜 = []
    for f in sorted(os.listdir(매뉴얼)):
        if not (f.endswith(".md") or f.endswith(".sh") or f.endswith(".py")):
            continue
        for i, l in enumerate(open(os.path.join(매뉴얼, f),
                                   encoding="utf-8").read().splitlines(), 1):
            # /tmp 는 일부러 쓴다 (임시 작업터).  홈 디렉터리 경로만 잡는다.
            #
            # 아래 정규식은 홈 경로를 **찾는** 무늬이지 **쓰는** 경로가
            # 아니다.  관문 G019 는 검사 파일 안의 `/home/.../` 를 "그
            # 기계에만 있는 자리" 로 보는데, 여기서는 그것이 바로 잡으려는
            # 대상이다.  그래서 표식을 달아 눈에 보이게 넘어간다.
            if re.search(r"/home/[A-Za-z0-9_.-]+/", l):   # G019: 기계 경로
                나쁜.append(f"{f}:{i}")
    ok(not 나쁜, f"**홈 디렉터리 경로를 박아 넣지 않았다** ({나쁜[:4]})")

    # 시작 명령이 저장소 루트를 스스로 찾는가
    r = open(os.path.join(매뉴얼, "README.md"), encoding="utf-8").read()
    ok("git rev-parse --show-toplevel" in r,
       "README 의 첫 명령이 저장소 루트를 스스로 찾는다")

    # 상태 스크립트도 자기 자리를 스스로 찾는가
    s = open(os.path.join(매뉴얼, "지금어디.sh"), encoding="utf-8").read()
    ok('dirname "$0"' in s or "rev-parse" in s,
       "지금어디.sh 가 자기 자리를 스스로 찾는다 (어디서 불러도 된다)")


def test_명령블록이_문법상_성하다():
    """매뉴얼의 bash 블록이 **문법상 돌 수 있는가**.

    매뉴얼의 명령은 복사해서 붙이라고 있는 것이다.  붙였는데 문법 오류가
    나면 따라 하는 사람은 자기가 잘못 붙인 줄 안다.
    """
    print("\n== 매뉴얼의 bash 블록이 문법상 성하다 ==")
    나쁜, 셈 = [], 0
    for f in sorted(os.listdir(매뉴얼)):
        if not f.endswith(".md"):
            continue
        t = open(os.path.join(매뉴얼, f), encoding="utf-8").read()
        for i, blk in enumerate(re.findall(r"```bash\n(.*?)```", t, re.S)):
            셈 += 1
            # <자리표시자> 와 $EDITOR 는 셸 문법이 아니므로 치환해서 본다
            s = re.sub(r"<[^>\n]+>", "X", blk).replace("$EDITOR", "true")
            r = 돌려(["bash", "-n"], 시간=30) if False else subprocess.run(
                ["bash", "-n"], input=s, capture_output=True, text=True, timeout=30)
            if r.returncode:
                나쁜.append(f"{f}#{i}: {r.stderr.strip().splitlines()[0][:70]}")
    ok(셈 >= 20, f"검사한 블록이 충분하다 ({셈} 개)")
    ok(not 나쁜, f"**문법 오류가 없다** ({나쁜[:3]})")


def test_링크가_성하다():
    print("\n== 문서 사이 링크가 성하다 ==")
    깨진 = []
    for f in sorted(os.listdir(매뉴얼)):
        if not f.endswith(".md"):
            continue
        t = open(os.path.join(매뉴얼, f), encoding="utf-8").read()
        for 링크 in re.findall(r"\]\(([^)#]+\.md)\)", t):
            if not os.path.exists(os.path.join(매뉴얼, 링크)):
                깨진.append(f"{f} -> {링크}")
    ok(not 깨진, f"깨진 링크가 없다 ({깨진[:3]})")


def test_그림이_있고_성하다():
    """매뉴얼이 거는 그림이 실제로 있고, SVG 가 성한가.

    그림의 실패도 조용하다 -- 깨진 `<img>` 는 빈 자리로 보일 뿐이다.
    그리고 SVG 안의 마크다운 별표는 **화면에 별표로 그대로 보인다**
    (실측으로 그랬다).  둘 다 기계가 본다.
    """
    print("\n== 매뉴얼의 그림이 성하다 ==")
    그림 = os.path.join(매뉴얼, "그림")
    ok(os.path.isdir(그림), "manual/그림/ 이 있다")

    # 문서가 거는 그림이 전부 있나
    깨진 = []
    for f in sorted(os.listdir(매뉴얼)):
        if not f.endswith(".md"):
            continue
        t = open(os.path.join(매뉴얼, f), encoding="utf-8").read()
        for s in re.findall(r'src="([^"]+)"', t):
            if not os.path.exists(os.path.join(매뉴얼, s)):
                깨진.append(f"{f} -> {s}")
    ok(not 깨진, f"깨진 그림 참조가 없다 ({깨진[:3]})")

    # SVG 가 열리고 닫히나, 별표가 안 남았나
    import sys as _s
    _s.path.insert(0, os.path.join(뿌리, "edu"))
    import sch
    나쁜 = []
    n = 0
    for g in sorted(os.listdir(그림)):
        if not g.endswith(".svg"):
            continue
        n += 1
        s = open(os.path.join(그림, g), encoding="utf-8").read()
        if not (s.startswith("<svg") and s.rstrip().endswith("</svg>")):
            나쁜.append(g + " (svg 가 안 닫힌다)")
        if sch.글자에별이없나(s):
            나쁜.append(g + " (마크다운 별표가 남았다)")
    ok(n >= 8, f"그림이 충분히 있다 ({n} 개)")
    ok(not 나쁜, f"**모든 SVG 가 성하다** ({나쁜[:2]})")

    # 생성기가 다시 돌아도 같은 것이 나오나
    r = 돌려([_s.executable, os.path.join(매뉴얼, "그림만들기.py")])
    ok(r.returncode == 0, f"그림만들기.py 가 돈다 ({r.stderr[:160]})")


def test_템플릿에_채울자리가_있다():
    print("\n== 템플릿이 '채워 넣는' 물건이다 ==")
    for 이름 in ("제품.md", "스펙.md", "DATASHEET.md",
               "INTEGRATION.md", "KNOWN_ISSUES.md"):
        p = os.path.join(템플릿, 이름)
        ok(os.path.exists(p), f"{이름} 가 있다")
        if os.path.exists(p):
            n = open(p, encoding="utf-8").read().count("TODO")
            ok(n >= 3, f"{이름}: 채울 자리 TODO {n} 개")


def test_매뉴얼이_규율을_적어두었다():
    """매뉴얼에서 이 셋이 지워지면 그냥 명령어 모음이 된다."""
    print("\n== 세 규율이 매뉴얼에 적혀 있다 ==")
    t = open(os.path.join(매뉴얼, "README.md"), encoding="utf-8").read()
    ok("검사하지 않은 초록불" in t, "① 검사하지 않은 초록불이 더 나쁘다")
    ok("재지 않은 수" in t, "② 재지 않은 수는 말하지 않는다")
    ok("못 한 것은 못 했다" in t, "③ 못 한 것은 못 했다고 적는다")
    v = open(os.path.join(매뉴얼, "06_검증.md"), encoding="utf-8").read()
    ok("자해검사" in v, "검증 문서가 자해검사를 시킨다")
    ok("변이" in v, "검증 문서가 변이 점수를 시킨다")
    s = open(os.path.join(매뉴얼, "07_합성과타이밍.md"), encoding="utf-8").read()
    ok("껍데기" in s, "**타이밍 껍데기**를 시킨다 -- 없으면 주파수가 10배 틀린다")


if __name__ == "__main__":
    for f in (test_상태스크립트가_돈다, test_뼈대가_이어붙어_통과한다,
              test_매뉴얼대로_따라가면_초록이_된다,
              test_경로를_박아넣지_않았다, test_명령블록이_문법상_성하다,
              test_링크가_성하다, test_그림이_있고_성하다,
              test_템플릿에_채울자리가_있다,
              test_매뉴얼이_규율을_적어두었다):
        f()
    print()
    if _틀림:
        print(f"실패 {len(_틀림)}개 -- {_틀림}")
        sys.exit(1)
    print("매뉴얼: 상태스크립트 · 뼈대 · 자해검사 · 링크 · 템플릿 · 규율 -- 통과")
