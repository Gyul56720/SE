r"""씨앗 소스에서 `seek/seed.json` 을 만든다. 호출 0회.

**왜 두 벌인가.** 원장이 읽는 것은 JSON 이고(코드를 문자열로 들고 있다), 사람이
읽고 고치는 것은 파이썬이다. JSON 안의 `\n` 투성이 문자열을 손으로 고치면 반드시
틀린다 -- G017 이 그런 자리를 이미 한 번 잡았다.

그래서 **파이썬이 원본이고 JSON 은 만들어진 것**이다. 둘이 어긋나면
`tests/test_seek_seeds.py` 가 잡는다.

    python3 seek/seeds/build.py            # seek/seed.json 을 새로 쓴다
    python3 seek/seeds/build.py --확인      # 어긋났는지만 본다 (안 쓴다)
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

여기 = Path(__file__).resolve().parent
나갈곳 = 여기.parent / "seed.json"


def 토막(글: str, 이름: str) -> str:
    """`def <이름>` 의 소스를 그대로 떠낸다. **직접 임포트하지 않는다** --
    씨앗은 결국 자식 프로세스에서 도는 코드고, 여기서 부를 이유가 없다."""
    나무 = ast.parse(글)
    for 마디 in 나무.body:
        if isinstance(마디, ast.FunctionDef) and 마디.name == 이름:
            return ast.get_source_segment(글, 마디)
    raise ValueError(f"`def {이름}` 이 없다")


def 물음(글: str) -> str:
    나무 = ast.parse(글)
    for 마디 in 나무.body:
        if (isinstance(마디, ast.Assign) and len(마디.targets) == 1
                and getattr(마디.targets[0], "id", "") == "물음"):
            return ast.literal_eval(마디.value)
    raise ValueError("`물음 = ...` 이 없다")


def 짓기() -> dict:
    씨앗들 = sorted(p for p in 여기.glob("*.py") if p.name != "build.py")
    if not 씨앗들:
        raise ValueError(f"{여기} 에 씨앗이 없다")
    문제 = []
    for i, p in enumerate(씨앗들, 1):
        글 = p.read_text(encoding="utf-8")
        문제.append({"id": f"P{i}", "물음": 물음(글),
                     "표본": 토막(글, "sample"), "판정": 토막(글, "judge"),
                     "옮김": "",
                     "계보": {"부모": "-", "연산자": "씨앗"}, "깊이": 0})
    return {"seq": len(문제), "problems": 문제}


def 글자(원장: dict) -> str:
    return json.dumps(원장, ensure_ascii=False, indent=1) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--확인", dest="check", action="store_true")
    a = ap.parse_args(argv)
    새것 = 글자(짓기())
    if a.check:
        옛것 = 나갈곳.read_text(encoding="utf-8") if 나갈곳.exists() else ""
        if 새것 == 옛것:
            print(f"{나갈곳.name} 이 씨앗 소스와 같다")
            return 0
        print(f"**{나갈곳.name} 이 씨앗 소스와 다르다** -- `python3 seek/seeds/build.py`")
        return 1
    나갈곳.write_text(새것, encoding="utf-8")
    n = len(json.loads(새것)["problems"])
    print(f"{나갈곳} 에 씨앗 {n}개를 적었다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
