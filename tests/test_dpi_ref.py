"""DPI-C 레퍼런스 모델이 **실제로 돌고, 틀린 것을 무는지**.

파이썬 골든 == C++ 레퍼런스 == Verilog RTL 셋이 같아야 한다.
"""
import os
import re
import shutil
import subprocess
import tempfile

import numpy as np

import ldpcrtl as R

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DPI = os.path.join(뿌리, "dpi")


def _도구():
    assert shutil.which("verilator"), "verilator 가 없다 -- '통과' 가 아니라 '못 잼' 이다"
    assert shutil.which("g++"), "g++ 가 없다 -- 못 잼"


def _돌리기(verilog: str, ref_cpp: str, 판: str) -> str:
    v = os.path.join(판, "cnu.v")
    open(v, "w").write(verilog)
    c = os.path.join(판, "ref.cpp")
    open(c, "w").write(ref_cpp)
    tb = os.path.join(판, "tb.sv")
    shutil.copy(os.path.join(DPI, "cnu_tb.sv"), tb)
    r = subprocess.run(["verilator", "--binary", "-Wno-fatal", "--timing",
                        "--top-module", "cnu_tb", tb, v, c,
                        "-o", "sim", "--Mdir", os.path.join(판, "obj")],
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        return "BUILDFAIL " + r.stderr[-400:]
    s = subprocess.run([os.path.join(판, "obj", "sim")],
                       capture_output=True, text=True, timeout=300)
    return s.stdout


def test_파이썬골든과_Cpp레퍼런스가_같다():
    """벤치를 안 돌려도 되는 빠른 대조. C++ 를 단독 실행해 맞댄다."""
    _도구()
    with tempfile.TemporaryDirectory() as 판:
        본 = open(os.path.join(DPI, "cnu_ref.cpp")).read()
        본 = 본.replace("#include <svdpi.h>", "")          # 단독 실행용
        본 = 본.replace('extern "C" void cnu_ref', "void cnu_ref")
        본 += """
#include <cstdio>
int main(){int a,b,c,d,r0,r1,r2,r3;
 while(scanf("%d %d %d %d",&a,&b,&c,&d)==4){cnu_ref(a,b,c,d,&r0,&r1,&r2,&r3);
 printf("%d %d %d %d\\n",r0,r1,r2,r3);} return 0;}
"""
        src = os.path.join(판, "x.cpp")
        open(src, "w").write(본)
        exe = os.path.join(판, "x")
        assert subprocess.run(["g++", "-O2", "-o", exe, src],
                              capture_output=True).returncode == 0
        rng = np.random.default_rng(5)
        v = rng.integers(-31, 32, size=(800, 4))
        inp = "\n".join(" ".join(map(str, r)) for r in v)
        out = subprocess.run([exe], input=inp, capture_output=True,
                             text=True, timeout=120).stdout.strip().splitlines()
        assert len(out) == len(v)
        for i, line in enumerate(out):
            assert [int(x) for x in line.split()] == \
                   [int(x) for x in R.골든CNU(v[i])], (i, list(v[i]))


def test_RTL이_DPI레퍼런스와_같다():
    _도구()
    with tempfile.TemporaryDirectory() as 판:
        로그 = _돌리기(R.cnu(4, 6), open(os.path.join(DPI, "cnu_ref.cpp")).read(), 판)
        assert "PASS" in 로그 and "FAIL" not in 로그, 로그[-400:]


def test_틀린_RTL을_잡는다():
    """안 잡으면 위 검사는 아무 뜻이 없다."""
    _도구()
    with tempfile.TemporaryDirectory() as 판:
        나쁜 = R.cnu(4, 6).replace("? min2 : min1", "? min1 : min2")
        로그 = _돌리기(나쁜, open(os.path.join(DPI, "cnu_ref.cpp")).read(), 판)
        assert "FAIL" in 로그, 로그[-400:]


def test_틀린_Cpp레퍼런스도_잡는다():
    """레퍼런스가 틀려도 잡혀야 한다 -- 한쪽만 믿지 않는다."""
    _도구()
    with tempfile.TemporaryDirectory() as 판:
        나쁜 = open(os.path.join(DPI, "cnu_ref.cpp")).read().replace(
            "normalize(sp * sign[i] * mag, 3, 2)", "normalize(sp * sign[i] * mag, 4, 2)")
        로그 = _돌리기(R.cnu(4, 6), 나쁜, 판)
        assert "FAIL" in 로그, 로그[-400:]


def test_벤치가_부호확장을_한다():
    """`int'()` 캐스팅이 없으면 음수가 큰 양수로 넘어가 조용히 틀린다."""
    tb = open(os.path.join(DPI, "cnu_tb.sv")).read()
    assert re.search(r"cnu_ref\(\s*int'\(q0\)", tb), "DPI 호출에 int'() 캐스팅이 없다"
