"""LEET 지문을 **화자별 원장**으로 가른다.

24문항을 옮겨 놓고 세어 보니 설계가 갈렸다(2023 추리논증):

    분석 -- 누가 무엇에 동의하는가   9
    추론 -- 따라 나오는가            4
    규정 적용 (표·날짜·산술)         4
    평가 -- 강화·약화                3
    ---
    견해 대립 꼴                    14 / 24

**순수 함의는 4개뿐이다.** 그런데 나머지가 논리 밖에 있는 것이 아니다.
"갑과 을은 의견을 달리할 것이다" 는 이렇게 풀린다:

    갑의 원장 |= X   그리고   을의 원장 |= ~X

즉 **화자마다 원장을 따로 세우면** `law/logic.py` 의 진리표가 그대로 먹는다.
지문 전체를 원장 하나로 뭉치면 갑과 을의 말이 서로 모순이라 `지문모순` 이 나고
아무것도 못 푼다 -- 실제로 문항 열넷이 그 꼴이다.

**그래서 이 파일이 하는 일은 논리가 아니라 가르기다.** 논리는 이미 있다.

## 가르는 자리 셋

    화자      갑: / 을: / 병: / 견해1: / 견해A: / A: -- 줄 첫머리의 이름표
    보기      <보기> 아래 ㄱ. ㄴ. ㄷ. -- 각각이 하나의 주장이다
    선택지    (1)~(5) -- ㄱㄴㄷ 의 부분집합을 고르는 꼴이 대부분이다

## 못 가르면 못 갈랐다고 한다

이름표가 없는 지문(설명문 한 덩이)도 많다. 그때는 화자를 하나('글')로 두고
**그렇게 적는다.** 없는 화자를 지어내지 않는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# 화자 이름표. **줄 첫머리에 오고 뒤에 콜론이 붙은 것만.** 본문 가운데의
# "갑은 ~라고 말했다" 를 화자 전환으로 읽으면 지문이 산산조각 난다.
_화자 = re.compile(r"^\s{0,2}(갑|을|병|정|무|견해\s*[0-9A-Z]+|[A-Z])\s*[:：]\s*", re.M)

_보기시작 = re.compile(r"^\s*<\s*보\s*기\s*>\s*$", re.M)
_보기항 = re.compile(r"^\s*([ㄱ-ㅎ])\.\s*", re.M)
_선택지 = re.compile(r"^\s*([①-⑤])\s*", re.M)
_문번 = re.compile(r"^문\s*(\d+)\.\s*$", re.M)

# 물음 꼴. **닫힌 목록이다** -- 새 꼴이 나오면 '?' 로 남기고 세어 둔다.
꼴표 = (
    ("추론", r"추론한\s*것"),
    ("적용", r"적용(?:한|으로)|판단(?:으로|한)|부과되는|충족하는"),
    ("반대논거", r"반대\s*논거|논거가\s*될"),
    ("평가", r"평가로"),
    ("분석", r"분석(?:으로|한)"),
    ("구조", r"논증의\s*구조"),
)


@dataclass
class 문항:
    번호: int = 0
    물음: str = ""
    지문: str = ""                      # 화자 이름표가 안 붙은 앞머리
    화자: dict = field(default_factory=dict)      # {'갑': '...', '견해1': '...'}
    보기: dict = field(default_factory=dict)      # {'ㄱ': '...', 'ㄴ': '...'}
    선택지: list = field(default_factory=list)
    원문: str = ""

    def 꼴(self) -> str:
        for 이름, 무늬 in 꼴표:
            if re.search(무늬, self.물음):
                return 이름
        return "?"

    def 표있나(self) -> bool:
        return "|" in self.원문

    def 수량있나(self) -> bool:
        return bool(re.search(r"\d+\s*(?:개월|년|일|원|%|주|배|명|시간)", self.원문))

    def 원장수(self) -> int:
        """세워야 할 원장이 몇 개인가. 화자가 없으면 글 하나."""
        return len(self.화자) or 1


def _자르기(글: str, 무늬) -> list:
    """무늬가 걸리는 자리에서 (표시, 몸통) 목록으로 자른다."""
    자리 = [(m.start(), m.end(), m.group(1)) for m in 무늬.finditer(글)]
    out = []
    for i, (s, e, 표) in enumerate(자리):
        끝 = 자리[i + 1][0] if i + 1 < len(자리) else len(글)
        out.append((표, 글[e:끝].strip()))
    return out


def 한문항(글: str, 번호: int = 0) -> 문항:
    """문항 한 덩이 -> `문항`. **못 가른 것은 비워 둔다.**"""
    q = 문항(번호=번호, 원문=글)
    줄 = 글.strip().split("\n")
    q.물음 = 줄[0].strip() if 줄 else ""
    몸 = "\n".join(줄[1:])

    # 선택지를 떼어 낸다. **본문 속 동그라미를 선택지로 읽으면 안 된다.**
    # 실측: 문 6 의 [학칙] 이 "제1조 (1) 학생이 ... (2) 학교장은" 이고, 문 10 의
    # [규정] 이 "체결가능수량은 (1)과 (2) 중 적은 것" 이다. 첫 동그라미부터 잘랐더니
    # **그 두 문항의 <보기>가 통째로 잘려 나갔다** -- 오류 없이 조용히.
    # 선택지는 (1)(2)(3)(4)(5)가 **차례로 이어지는** 마지막 자리다.
    선 = list(_선택지.finditer(몸))
    차례 = "①②③④⑤"
    시작 = -1
    for i in range(len(선) - 5, -1, -1):
        if all(선[i + k].group(1) == 차례[k] for k in range(5)):
            시작 = 선[i].start()
            break
    if 시작 >= 0:
        q.선택지 = [t.strip() for _, t in _자르기(몸[시작:], _선택지)][:5]
        몸 = 몸[:시작]

    # 보기
    m = _보기시작.search(몸)
    if m:
        q.보기 = dict(_자르기(몸[m.end():], _보기항))
        몸 = 몸[: m.start()]

    # 화자
    q.화자 = dict(_자르기(몸, _화자))
    첫 = _화자.search(몸)
    q.지문 = (몸[: 첫.start()] if 첫 else 몸).strip()
    return q


def 읽기(글: str) -> list:
    """손옮김 파일 한 벌 -> 문항 목록. `#` 로 시작하는 줄은 메타라 버린다."""
    글 = "\n".join(l for l in 글.split("\n") if not l.lstrip().startswith("#"))
    자리 = [(m.start(), m.end(), int(m.group(1))) for m in _문번.finditer(글)]
    out = []
    for i, (s, e, n) in enumerate(자리):
        끝 = 자리[i + 1][0] if i + 1 < len(자리) else len(글)
        out.append(한문항(글[e:끝].strip(), n))
    return out


def 통계(문항들) -> dict:
    """**무엇을 만들어야 하는지는 세어 보고 정한다.**"""
    from collections import Counter
    꼴 = Counter(q.꼴() for q in 문항들)
    return {
        "문항": len(문항들),
        "꼴": dict(꼴),
        "보기꼴": sum(1 for q in 문항들 if q.보기),
        "화자있음": sum(1 for q in 문항들 if q.화자),
        "원장둘이상": sum(1 for q in 문항들 if q.원장수() >= 2),
        "표": sum(1 for q in 문항들 if q.표있나()),
        "수량": sum(1 for q in 문항들 if q.수량있나()),
        "논리만으로": sum(1 for q in 문항들 if not q.표있나() and not q.수량있나()),
    }


def 보고(문항들) -> str:
    s = 통계(문항들)
    줄 = [f"문항 {s['문항']}개",
          "  꼴: " + " · ".join(f"{k} {v}" for k, v in
                                sorted(s["꼴"].items(), key=lambda x: -x[1])),
          f"  <보기> 꼴 {s['보기꼴']} · 화자 있음 {s['화자있음']} · "
          f"원장 둘 이상 {s['원장둘이상']}",
          f"  표 {s['표']} · 수량 {s['수량']} · **표도 수량도 없음 {s['논리만으로']}**"]
    return "\n".join(줄)


def main(argv=None) -> int:
    import argparse
    import sys
    from pathlib import Path
    ap = argparse.ArgumentParser(description="LEET 손옮김을 화자별로 가른다")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--문", type=int, default=0, help="이 번호 문항만 자세히")
    a = ap.parse_args(argv)
    모두 = []
    for f in a.files:
        qs = 읽기(Path(f).read_text(encoding="utf-8"))
        모두 += qs
        print(f"[{Path(f).name}]")
        print(보고(qs))
        if a.문:
            for q in qs:
                if q.번호 != a.문:
                    continue
                print(f"\n문 {q.번호} · 꼴={q.꼴()} · 원장 {q.원장수()}개")
                print(f"  물음: {q.물음[:70]}")
                print(f"  지문: {len(q.지문)}자")
                for 이름, 말 in q.화자.items():
                    print(f"  [{이름}] {len(말)}자 · {말[:48]}…")
                for ㄱ, t in q.보기.items():
                    print(f"  <{ㄱ}> {t[:56]}…")
                print(f"  선택지 {len(q.선택지)}개: {[t[:12] for t in q.선택지]}")
    if len(a.files) > 1:
        print("\n[모두]")
        print(보고(모두))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
