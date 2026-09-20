# -*- coding: utf-8 -*-
"""프로토콜 블록(8b/10b · 24+6 ECC)을 **실제로 돌려** 본다.

## 이 검사가 붙드는 것

프로토콜 블록은 정답이 남의 문서에 있다.  그 문서를 못 받는 자리에서는
**부호의 성질**이 유일한 관문이다.  그 관문이 진짜로 무는지를 여기서 본다.

    1. 8b/10b 의 네 성질(전단사·RD유계·연속5·콤마유일)이 전수로 통과하는가
    2. 24+6 ECC 가 단일 전부 정정, 이중 전부 검출인가
    3. 손으로 쓴 RTL 이 C++ 골든과 같은가 -- **그리고 자해검사가 무는가**
    4. 표를 망가뜨리면 성질 검사가 **반드시 빨개지는가**

4번이 핵심이다.  1~3만 보는 검사는 성질 검사가 통과만 찍게 되어도 초록이다.
이 저장소가 다섯 번 앓은 병이 그것이다 -- 검사하지 않은 초록불.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
프로토 = os.path.join(뿌리, "edu", "proto")

_틀림 = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        _틀림.append(말)


def 돌려(cmd, cwd=None, 시간=600):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=시간)


def _짓기(d, 소스, 이름, 추가=()):
    exe = os.path.join(d, 이름)
    r = 돌려(["g++", "-O2", "-I" + 프로토, "-o", exe,
             os.path.join(프로토, 소스)] + list(추가))
    return (exe if r.returncode == 0 else None), r.stderr[:200]


def test_8b10b_네_성질():
    print("\n== 8b/10b 네 성질이 전수로 통과한다 ==")
    if not shutil.which("g++"):
        ok(False, "g++ 가 없다")
        return
    with tempfile.TemporaryDirectory() as d:
        exe, err = _짓기(d, "proto_check.cpp", "pc")
        ok(exe is not None, f"proto_check.cpp 가 컴파일된다 ({err})")
        if not exe:
            return
        r = 돌려([exe])
        ok(r.returncode == 0, f"네 성질 전부 통과 (rc={r.returncode})")
        수 = dict(re.findall(r"(\S+) (\d+)", r.stdout))
        m = re.search(r"코드워드 (\d+) 개", r.stdout)
        ok(m and m.group(1) == "528", f"코드워드가 528 개다 ({m.group(1) if m else '?'})")
        m = re.search(r"최장 (\d+)", r.stdout)
        ok(m and int(m.group(1)) <= 5,
           f"**같은 비트가 5 를 안 넘는다** -- CDR 이 클럭을 잃는 자리다 "
           f"({m.group(1) if m else '?'})")
        m = re.search(r"콤마가 보인 횟수 (\d+)", r.stdout)
        ok(m and m.group(1) == "0",
           f"**데이터에 콤마가 안 나온다** -- 나오면 정렬이 가짜 경계를 잡는다 "
           f"({m.group(1) if m else '?'})")
        m = re.search(r"서로 다른 코드워드 (\d+)", r.stdout)
        ok(m and int(m.group(1)) > 300,
           f"코드워드가 여러 가지다 -- 몇 개뿐이면 표가 안 채워진 것이다 "
           f"({m.group(1) if m else '?'})")


def test_표를_망가뜨리면_빨개진다():
    """**성질 검사 자체를 검사한다.**  통과만 찍는 관문은 없느니만 못하다."""
    print("\n== 표를 망가뜨리면 성질 검사가 문다 ==")
    if not shutil.which("g++"):
        ok(False, "g++ 가 없다")
        return
    원본 = open(os.path.join(프로토, "enc8b10b.h"), encoding="utf-8").read()
    # D.07 의 RD+ 항목을 RD- 와 같게 만든다 -- 실제로 물렸던 바로 그 결함
    깨진 = 원본.replace("/* D.07 */ 0x07,", "/* D.07 */ 0x38,")
    ok(깨진 != 원본, "망가뜨릴 자리를 찾았다 (D.07 의 RD+ 항목)")
    if 깨진 == 원본:
        return
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "enc8b10b.h"), "w", encoding="utf-8").write(깨진)
        # **검사기도 같이 옮긴다.**  `#include "enc8b10b.h"` 는 따옴표
        # 인클루드라 **그 파일이 있는 디렉터리를 먼저** 뒤진다.  원본 자리에
        # 둔 채 `-I<임시>` 만 앞에 붙이면 원본 헤더가 잡혀서, 망가뜨린 판을
        # 컴파일한 줄 알았는데 성한 판이 돈다 -- 실측으로 그랬다(rc=0).
        # 그러면 이 검사는 **관문이 무는지를 못 보면서 통과를 찍는다.**
        shutil.copy(os.path.join(프로토, "proto_check.cpp"), d)
        exe = os.path.join(d, "pc")
        r = 돌려(["g++", "-O2", "-I" + d, "-o", exe,
                 os.path.join(d, "proto_check.cpp")])
        ok(r.returncode == 0, f"망가뜨린 판이 컴파일된다 ({r.stderr[:160]})")
        if r.returncode:
            return
        r = 돌려([exe])
        ok(r.returncode != 0,
           f"**망가뜨리면 빨간불이 난다** -- 안 나면 이 관문은 아무것도 안 보는 것이다 "
           f"(rc={r.returncode})")
        ok("최장 6" in r.stdout or "5 를 넘는 이음" in r.stdout,
           "연속비트 성질이 그것을 짚는다")


def test_ecc_단일정정_이중검출():
    print("\n== 24+6 ECC 가 SEC-DED 다 ==")
    if not shutil.which("g++"):
        ok(False, "g++ 가 없다")
        return
    with tempfile.TemporaryDirectory() as d:
        exe, err = _짓기(d, "ecc_check.cpp", "ec")
        ok(exe is not None, f"ecc_check.cpp 가 컴파일된다 ({err})")
        if not exe:
            return
        r = 돌려([exe])
        ok(r.returncode == 0, f"SEC-DED 전수 확인 통과 (rc={r.returncode})")
        m = re.search(r"단일 오류: (\d+) 가지 중 틀림 (\d+)", r.stdout)
        ok(m and m.group(2) == "0",
           f"**단일 오류를 전부 고친다** ({m.group(1) if m else '?'} 가지 중 "
           f"틀림 {m.group(2) if m else '?'})")
        ok(m and int(m.group(1)) >= 180, "충분히 많이 봤다 (30 자리 x 대표 6)")
        m = re.search(r"이중 오류: (\d+) 가지 중 검출 (\d+), \*\*오정정 (\d+)\*\*", r.stdout)
        ok(m and m.group(3) == "0",
           f"**이중 오류를 잘못 고치지 않는다** -- 고치려 들면 성한 것을 더 망가뜨린다 "
           f"(오정정 {m.group(3) if m else '?'})")
        ok(m and m.group(1) == m.group(2),
           f"이중 오류를 전부 검출한다 ({m.group(2) if m else '?'}/"
           f"{m.group(1) if m else '?'})")


def test_RTL이_Cpp골든을_따른다():
    print("\n== 손으로 쓴 RTL 이 C++ 골든과 같다 ==")
    if not all(shutil.which(x) for x in ("g++", "iverilog", "vvp")):
        ok(False, "g++/iverilog/vvp 가 없다")
        return
    사례 = [("vec8b10b.cpp", "tb_enc8b10b.v", "enc8b10b.v", "8b/10b", 2000, 3),
           ("vec_ecc.cpp", "tb_ecc24.v", "ecc24.v", "ECC", 1000, 4)]
    for 생성, tb, dut, 이름, n, 칸 in 사례:
        with tempfile.TemporaryDirectory() as d:
            exe, err = _짓기(d, 생성, "v")
            ok(exe is not None, f"{이름}: 골든 생성기가 컴파일된다 ({err})")
            if not exe:
                continue
            r = 돌려([exe, str(n), "5"])
            open(os.path.join(d, "vec.txt"), "w").write(r.stdout)
            줄수 = len(r.stdout.strip().splitlines())
            ok(줄수 == n, f"{이름}: 벡터가 {n} 줄 나온다 ({줄수})")
            벌 = os.path.join(d, "a.out")
            r = 돌려(["iverilog", "-g2012", "-o", 벌,
                     os.path.join(프로토, tb), os.path.join(프로토, dut)])
            ok(r.returncode == 0, f"{이름}: RTL 이 컴파일된다 ({r.stderr[:160]})")
            if r.returncode:
                continue
            r = 돌려([벌], cwd=d)
            m = re.search(r"잰것 (\d+)\s+틀림 (\d+)", r.stdout)
            ok(m is not None, f"{이름}: 결과 줄이 나온다")
            if m:
                ok(m.group(2) == "0", f"{이름}: 틀린 것이 없다 ({m.group(2)})")

            # 자해검사 -- 골든 한 줄을 망가뜨리면 반드시 걸려야 한다
            줄들 = open(os.path.join(d, "vec.txt")).read().splitlines()
            조각 = 줄들[40].split()
            조각[칸 - 2] = str((int(조각[칸 - 2]) + 1))
            줄들[40] = " ".join(조각)
            open(os.path.join(d, "vec.txt"), "w").write("\n".join(줄들) + "\n")
            r = 돌려([벌], cwd=d)
            m2 = re.search(r"잰것 (\d+)\s+틀림 (\d+)", r.stdout)
            ok(m2 is not None and m2.group(2) != "0",
               f"{이름}: **골든을 망가뜨리면 걸린다** "
               f"(틀림 {m2.group(2) if m2 else '?'})")


def test_lint가_깨끗하다():
    print("\n== verilator -Wall 이 조용하다 ==")
    if not shutil.which("verilator"):
        ok(False, "verilator 가 없다")
        return
    for 파일, 톱 in (("enc8b10b.v", "enc8b10b"), ("ecc24.v", "ecc24")):
        r = 돌려(["verilator", "--lint-only", "-Wall", "--top-module", 톱,
                 os.path.join(프로토, 파일)])
        경고 = len(re.findall(r"^%(?:Error|Warning)", r.stdout + r.stderr, re.M))
        ok(경고 == 0 and r.returncode == 0,
           f"{파일}: 경고 {경고} 개, rc={r.returncode}")


def test_출처가_흐려지지_않았다():
    """**확인한 것과 못 한 것의 경계**가 소스에 적혀 있는가.

    이 경계가 지워지면 "MIPI 호환" 이라고 팔았다가 상대 장비와 안 붙는다.
    기계가 상호운용을 확인할 수는 없으므로, 기계가 할 수 있는 일은
    **그 말이 지워지지 않았는지 지키는 것**뿐이다.
    """
    print("\n== 확인 수준이 소스에 적혀 있다 ==")
    ecc = open(os.path.join(프로토, "ecc24.h"), encoding="utf-8").read()
    ok("MIPI 의 것이 아니다" in ecc or "MIPI 와 비트까지 같지는 않다" in ecc,
       "**ecc24.h 가 MIPI 표가 아니라고 못박는다**")
    enc = open(os.path.join(프로토, "enc8b10b.h"), encoding="utf-8").read()
    ok("증명하지 못한 것" in enc, "enc8b10b.h 가 못 확인한 것을 적는다")
    ok("Clause 36" in enc, "정규 표가 어디 있는지 가리킨다")
    잰 = open(os.path.join(프로토, "잰것.json"), encoding="utf-8").read()
    ok("무효화" in 잰, "잰것.json 에 무효화 조건이 있다")


if __name__ == "__main__":
    for f in (test_8b10b_네_성질, test_표를_망가뜨리면_빨개진다,
              test_ecc_단일정정_이중검출, test_RTL이_Cpp골든을_따른다,
              test_lint가_깨끗하다, test_출처가_흐려지지_않았다):
        f()
    print()
    if _틀림:
        print(f"실패 {len(_틀림)}개 -- {_틀림}")
        sys.exit(1)
    print("8b/10b · ECC · RTL 대조 · lint · 출처 -- 통과")
