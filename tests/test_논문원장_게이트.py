"""
G022 · G023 · G024 의 거짓 초록 사냥.

`self_challenge.py prove` 는 이 셋의 RED 를 `ff31763` 에서 증명했다. 그런데 그때의 GREEN 은
**`paper/` 에 살아 있는 원고가 하나도 없어서** 난 것이다. 그러면 증명된 것은 "없으면 통과"
뿐이고, **채워진 트리에서 제대로 무는지는 아무도 안 봤다.** 이 저장소의 규율은

    검사하지 않은 초록불이 검사한 빨간불보다 나쁘다

이므로, 여기서 **옳게 채운 트리 하나**를 짓고 초록을 확인한 뒤, 그것을 **한 군데씩 망가뜨려**
매번 빨개지는지 본다. 망가뜨렸는데 초록이면 그 자리는 게이트가 안 보고 있는 것이다.

실행: python3 tests/test_논문원장_게이트.py
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import gatekeeper  # noqa: E402


def _게이트(rule_id: str):
    (파일,) = [p for p in (REPO / "gates").glob(f"{rule_id}_*.py")]
    spec = importlib.util.spec_from_file_location(f"_g_{rule_id}", 파일)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


G022, G023, G024 = _게이트("G022"), _게이트("G023"), _게이트("G024")

_논문 = "x.html"

_HTML = """<html><head><title>T</title></head><body>
<h1 class="title">A Substitute at 1/59 the Area</h1>
<div class="abs"><b>Abstract&mdash;</b>OIF frames 448 Gb/s lanes.</div>
<div class="ref"><ol>
<li>A. Author, "Thing," <i>IEEE Trans.</i>, 1989. [출처:전문]</li>
<li>B. Author, "Other," arXiv:2412.18579. [출처:조각]</li>
</ol></div>
</body></html>
"""

_출처 = [
    {"논문": _논문, "번호": 1, "확인수준": "전문", "날짜": "2026-09-18",
     "질의": "pipeline interleaving recursive filters", "어디서": "IEEE Xplore 전문 PDF"},
    {"논문": _논문, "번호": 2, "확인수준": "조각", "날짜": "2026-09-18",
     "질의": "ReducedLUT lookup table occupancy", "어디서": "검색 결과 조각만 봤다"},
]

_측정 = [
    {"논문": _논문, "값": "1/59", "종류": "측정",
     "재현": "python3 asic.py --쓸기", "독립대조": "LEF 면적합 대 셀수x평균면적, 차이 1.3%",
     "사소한설명": "탭이 0이라 고리가 노는 경우 -- 탭 에너지 0.64 로 배제",
     "무효화": "W(1e-3)>16 인 동작점에서는 뒤집힌다"},
    {"논문": _논문, "값": "448", "종류": "규격", "출처": "OIF-FD-CEI-448G-01.0"},
]

_조사 = """# x 선행조사

## 가장 가까운 선행연구
- ReducedLUT, FPGA'25, arXiv:2412.18579 -- 점유가 비용을 정한다는 것을 이미 보였다

## 우리가 그것과 다른 점
- 저쪽은 학습 LUT, 우리는 되먹임 고리

## 찾아본 질의
- lookup table occupancy cost FPGA
- speculative DFE unrolling area
- recurrence II high-level synthesis

## 아직 못 지운 가능성
- ASPLOS/MICRO 쪽 근사계산 문헌을 아직 못 봤다
"""


def _트리(자리: Path) -> None:
    (자리 / "paper" / "선행조사").mkdir(parents=True)
    (자리 / "paper" / _논문).write_text(_HTML, encoding="utf-8")
    _쓰기(자리, "출처", _출처)
    _쓰기(자리, "측정", _측정)
    (자리 / "paper" / "선행조사" / "x.md").write_text(_조사, encoding="utf-8")


def _쓰기(자리: Path, 이름: str, 행들) -> None:
    (자리 / "paper" / f"{이름}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in 행들), encoding="utf-8")


def _재다(자리: Path):
    ctx = gatekeeper.GateContext(자리)
    return G022.check(ctx), G023.check(ctx), G024.check(ctx)


# (설명, 트리를 망가뜨리는 함수, 빨개져야 하는 게이트의 자리 0=G022 1=G023 2=G024)
_망가뜨리기 = [
    ("출처 원장에서 인용 [2] 의 행을 지운다",
     lambda 자리: _쓰기(자리, "출처", _출처[:1]), 0),
    ("문서의 [출처:조각] 을 [출처:전문] 로 올려 적는다 (원장과 어긋난다)",
     lambda 자리: (자리 / "paper" / _논문).write_text(
         _HTML.replace("[출처:조각]", "[출처:전문]"), encoding="utf-8"), 0),
    ("출처 원장의 '질의' 를 비운다",
     lambda 자리: _쓰기(자리, "출처", [_출처[0], {**_출처[1], "질의": "  "}]), 0),
    ("출처 원장 자체를 지운다",
     lambda 자리: (자리 / "paper" / "출처.jsonl").unlink(), 0),
    ("측정 원장에서 1/59 행을 지운다",
     lambda 자리: _쓰기(자리, "측정", _측정[1:]), 1),
    ("측정 원장의 '무효화' 를 비운다 (깨지는 조건이 없는 수)",
     lambda 자리: _쓰기(자리, "측정", [{**_측정[0], "무효화": ""}, _측정[1]]), 1),
    ("측정 원장의 '사소한설명' 을 비운다 (시시한 원인을 안 죽였다)",
     lambda 자리: _쓰기(자리, "측정", [{**_측정[0], "사소한설명": ""}, _측정[1]]), 1),
    ("측정 원장의 '독립대조' 를 비운다 (한 길로만 쟀다)",
     lambda 자리: _쓰기(자리, "측정", [{**_측정[0], "독립대조": ""}, _측정[1]]), 1),
    ("규격 숫자 448 의 '출처' 를 비운다",
     lambda 자리: _쓰기(자리, "측정", [_측정[0], {**_측정[1], "출처": ""}]), 1),
    ("선행조사 파일을 지운다",
     lambda 자리: (자리 / "paper" / "선행조사" / "x.md").unlink(), 2),
    ("선행조사에서 '아직 못 지운 가능성' 마디를 통째로 뺀다",
     lambda 자리: (자리 / "paper" / "선행조사" / "x.md").write_text(
         _조사.split("## 아직 못 지운 가능성")[0], encoding="utf-8"), 2),
    ("가장 가까운 선행연구에서 찾아갈 꼴(arXiv·연도)을 지운다",
     lambda 자리: (자리 / "paper" / "선행조사" / "x.md").write_text(
         _조사.replace("FPGA'25, arXiv:2412.18579", "어디선가 본 논문"), encoding="utf-8"), 2),
    ("찾아본 질의를 2줄로 줄인다",
     lambda 자리: (자리 / "paper" / "선행조사" / "x.md").write_text(
         _조사.replace("- recurrence II high-level synthesis\n", ""), encoding="utf-8"), 2),
]


def main() -> int:
    이름들 = ("G022", "G023", "G024")
    실패 = []

    with tempfile.TemporaryDirectory() as tmp:
        바른트리 = Path(tmp) / "바른것"
        바른트리.mkdir()
        _트리(바른트리)
        결과 = _재다(바른트리)
        print("[초록] 옳게 채운 트리")
        for 이름, 위반 in zip(이름들, 결과):
            if 위반:
                실패.append(f"{이름} 가 옳은 트리를 빨갛다고 했다: {위반[0]}")
                print(f"  {이름}: 위반 {len(위반)}건 <- 틀렸다")
            else:
                print(f"  {이름}: 통과")

        print(f"\n[빨강] 한 군데씩 망가뜨린다 ({len(_망가뜨리기)}가지)")
        for 설명, 깨기, 자리 in _망가뜨리기:
            사본 = Path(tmp) / "깨진것"
            shutil.rmtree(사본, ignore_errors=True)
            shutil.copytree(바른트리, 사본)
            깨기(사본)
            위반 = _재다(사본)[자리]
            표 = "빨강" if 위반 else "초록 <- 안 물었다"
            print(f"  {이름들[자리]} {표}: {설명}")
            if not 위반:
                실패.append(f"{이름들[자리]} 가 '{설명}' 를 못 잡는다 -- 거짓 초록이다")

    print()
    if 실패:
        for s in 실패:
            print(f"실패: {s}")
        return 1
    print(f"모두 통과 -- 옳은 트리 1개 초록, 망가뜨린 {len(_망가뜨리기)}가지 전부 빨강.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
