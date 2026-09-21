# -*- coding: utf-8 -*-
"""01 합성 -- yosys 를 실제로 돌린다.  여기만 바깥 도구를 쓴다."""
from __future__ import annotations

import os
import subprocess
import sys

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

대본 = """\
read_verilog {rtl}
hierarchy -check -top {top}
proc; opt; fsm; opt; memory; opt
techmap; opt
dfflibmap -liberty {lib}
abc -liberty {lib}
opt_clean
write_json {json}
write_verilog -noattr {v}
stat -liberty {lib}
"""


def 있나():
    from shutil import which
    return which("yosys") is not None


def 돌리기(rtl=None, top="dsp_top", 밖=None, 조용히=True):
    """돌아간 뒤 낸 파일들의 길을 돌려준다.  yosys 가 없으면 **터진다** --
    조용히 건너뛰면 '돌렸다' 는 거짓 초록이 된다."""
    rtl = rtl or os.path.join(뿌리, "rtl", "dsp_top.v")
    밖 = 밖 or os.path.join(뿌리, "out")
    os.makedirs(밖, exist_ok=True)
    lib = os.path.join(뿌리, "lib", "se10.lib")
    if not os.path.exists(lib):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import mklib
        open(lib, "w", encoding="utf-8").write(mklib.글())
    j = os.path.join(밖, f"{top}.json")
    v = os.path.join(밖, f"{top}_mapped.v")
    ys = os.path.join(밖, f"{top}.ys")
    open(ys, "w", encoding="utf-8").write(
        대본.format(rtl=rtl, top=top, lib=lib, json=j, v=v))
    if not 있나():
        raise RuntimeError("yosys 가 없다.  이 단계는 진짜 도구를 쓴다 -- "
                           "없으면 건너뛰지 않고 여기서 멈춘다.")
    r = subprocess.run(["yosys", "-q", "-s", ys], capture_output=True,
                       text=True, cwd=뿌리, timeout=600)
    if r.returncode != 0:
        raise RuntimeError("yosys 실패:\n" + (r.stderr or r.stdout)[-3000:])
    if not 조용히:
        print(r.stdout)
    return {"json": j, "verilog": v, "lib": lib, "대본": ys}


if __name__ == "__main__":
    import pprint
    pprint.pprint(돌리기(조용히=False))
