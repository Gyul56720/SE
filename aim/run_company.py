# -*- coding: utf-8 -*-
"""AIM 설계를 **Nowon Silicon Works 의 다섯 직무에 넘긴다.**

내가 손으로 변이를 걸거나 면적을 재지 않는다 -- 그것은 Priya(DV) 와 Marcus(SYN) 의
일이다. 이 스크립트는 넘기고 받아 적기만 한다.

실행: setsid nohup python3 aim/run_company.py > logs/aim_company.log 2>&1 < /dev/null &
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("SE_ROOT", str(Path(__file__).resolve().parent.parent))

import house.run as R                                            # noqa: E402

설계들 = ["aim_chain", "aim_bin"]
직무들 = ["rtl", "dv", "syn", "dft", "pd"]
낸것길 = Path(__file__).resolve().parent / "company_out.json"


def 적기(표):
    낸것길.write_text(json.dumps(표, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def main():
    표 = {"시작": time.time(), "결과": []}
    적기(표)
    for 회로 in 설계들:
        for 키 in 직무들:
            줄 = {"회로": 회로, "직무": 키, "시작": time.strftime("%H:%M:%S")}
            print(f"=== {회로} / {키} ===", flush=True)
            t0 = time.time()
            try:
                r = R.한명(키, 빠르게=True, 회로=회로)
                줄["초"] = round(time.time() - t0, 1)
                줄["pdf"] = str(r.get("pdf", ""))
                줄["쪽"] = r.get("쪽")
                줄["요약"] = r.get("요약", [])[:6]
                줄["상태"] = "됨"
                print(f"    됨 {줄['초']}초 -> {줄['pdf']}", flush=True)
                for s in 줄["요약"][:3]:
                    print("      ", str(s)[:150], flush=True)
            except Exception as e:                               # noqa: BLE001
                줄["초"] = round(time.time() - t0, 1)
                줄["상태"] = "막힘"
                줄["오류"] = f"{type(e).__name__}: {e}"
                줄["자취"] = traceback.format_exc()[-1200:]
                # **우회하지 않는다.** 막힌 것은 막혔다고 적고 다음으로 간다.
                print(f"    막힘 {줄['초']}초 -- {줄['오류']}", flush=True)
            표["결과"].append(줄)
            적기(표)
    표["끝"] = time.time()
    적기(표)
    print("=== 다 돌았다 ===", flush=True)


if __name__ == "__main__":
    main()
