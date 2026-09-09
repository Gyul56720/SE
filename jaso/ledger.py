"""**경험 원장** -- 자소서가 대조받을 유일한 바깥.

    python3 jaso/ledger.py --표 내원장.json          # 성한지 보고 앵커를 센다
    python3 jaso/ledger.py --표 jaso/보기.json --앵커  # 무엇이 앵커인지 눈으로

## 왜 이것이 첫 파일인가

`law/write.py` 가 적어 둔 것: 재료를 안 주면 모델이 기억에서 꺼내 오고, 그것이 법률
LLM 의 1위 실패 모드다. 자소서에서 "기억" 은 **사용자의 인생을 지어내는 것**이다.
원장이 비면 J001~J004 가 전부 미검증이 되고, 미검증 위에 쓴 자소서는 그냥 일반 LLM
출력이다 -- 관문이 있다는 착각만 얹힌 채로.

## 거절하지 않는다. 표를 단다

`brief/ledger` 는 검사에 통과하는 것만 받았다. **여기서는 반대다.** 사용자가 잰 방법을
안 적었다고 그 경험을 원장에서 빼면, 뺀 것을 아무도 못 되찾는다(`dig/README.md` 의 선).

그래서 두 층으로 나눈다.

    E001~E003  **성함**을 본다. 어기면 판정 자체가 불가능하다 -> hard
    E004~E006  **표시**를 단다. 사실은 남고, 그 사실로 무엇을 못 하는지가 붙는다 -> soft

잰 방법 없는 수는 원장에 남는다. 다만 `쓸수있나 = False` 가 붙고, `jaso/gate.py` 의
J002 가 그 수를 자소서에서 막는다. **원장에서 거절하는 것과 자소서에서 막는 것은
다른 일이다.**

## 역할만 닫힌 목록인 이유

`갈래`(프로젝트·인턴·동아리…)는 열려 있다. 닫으면 사용자의 이력이 목록에 안 맞는
순간 잘려 나가고, 그것은 `brain/README.md` 가 한 번 잘못 짰다고 적어 둔 하드코딩과
같은 짓이다.

**`역할`만 닫는다.** 관문 J004(역할 승격)가 이 낱말로 판정하기 때문이다. 자유 서술이면
'참여' 와 '함께 했음' 과 '팀원으로서' 가 다 다른 문자열이 되고, 그러면 관문이 눈이 없다.
`law/wording.py` 가 '준용' 과 '적용' 을 가르는 자리와 같다 -- **낱말 하나가 사실을 바꾼다.**
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# **닫힌 목록.** 위에서 아래로 갈수록 기여가 작다 -- J004 가 이 순서로 승격을 잰다.
역할들 = ("주도", "참여", "보조", "관찰")

AIM = {
    "E001": "항목 id 가 겹치지 않아야 한다",
    "E002": "역할이 닫힌 목록 안이어야 한다",
    "E003": "기간이 구간이고 시작이 끝보다 앞서야 한다",
    "E004": "수마다 잰 방법이 적혀야 한다 (없으면 그 수는 자소서에 못 쓴다)",
    "E005": "항목마다 증빙이 적혀야 한다 (없으면 그렇게 표시한다)",
    "E006": "전념 구간이 겹치지 않아야 한다 (겹치면 자소서에서 설명이 필요하다)",
}

_YM = re.compile(r"^(\d{4})(?:[-./](\d{1,2}))?$")


@dataclass
class 잰것:
    무엇: str = ""
    전: str = ""
    후: str = ""
    단위: str = ""
    어떻게: str = ""          # **재는 법.** 비면 이 수는 자소서에 못 쓴다

    @property
    def 쓸수있나(self) -> bool:
        return bool(self.어떻게.strip())

    @property
    def 수들(self) -> list:
        return [_수(x) for x in (self.전, self.후) if _수(x)]


@dataclass
class 항목:
    id: str
    갈래: str = ""            # 열려 있다 -- 닫으면 남의 이력이 잘려 나간다
    이름: str = ""
    곳: str = ""
    언제: tuple = ()          # ("2025-03", "2025-08")
    역할: str = ""            # 닫힌 목록
    한일: list = field(default_factory=list)
    잰것: list = field(default_factory=list)
    쓴것: list = field(default_factory=list)
    같이: int = 0
    증빙: str = ""
    전념: bool = True         # 풀타임인가. E006 겹침이 이것만 본다

    @property
    def 무게(self) -> int:
        """역할의 크기. 클수록 기여가 크다. J004 가 이 수를 견준다."""
        return len(역할들) - 역할들.index(self.역할) if self.역할 in 역할들 else 0

    @property
    def 개월(self) -> int:
        a, b = _달(self.언제[0] if self.언제 else ""), _달(self.언제[-1] if self.언제 else "")
        return (b - a + 1) if (a and b and b >= a) else 0

    @property
    def 연도들(self) -> set:
        out = set()
        for x in self.언제:
            m = _YM.match(str(x).strip())
            if m:
                out.add(m.group(1))
        if len(out) == 2:                       # 구간 사이 해도 그 항목의 해다
            a, b = sorted(int(x) for x in out)
            out |= {str(y) for y in range(a, b + 1)}
        return out


@dataclass
class 위반:
    규칙: str
    등급: str
    어디: str
    말: str

    def __str__(self) -> str:
        return f"[{self.규칙}/{self.등급}] {self.어디}: {self.말}"


@dataclass
class 원장:
    항목들: list = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.항목들)

    def __len__(self) -> int:
        return len(self.항목들)

    def 찾기(self, id: str):
        return next((h for h in self.항목들 if h.id == id), None)


# ---------------------------------------------------------------- 읽기

def _수(x) -> str:
    """수를 한 꼴로 편다. 자소서는 `48,000` 이라 쓰고 원장은 `48000` 이라 적는다."""
    s = str(x).strip().replace(",", "")
    m = re.match(r"^-?\d+(?:\.\d+)?", s)
    if not m:
        return ""
    v = m.group(0)
    return v[:-2] if v.endswith(".0") else v


def _달(x) -> int:
    """'2025-03' -> 24303. 달 수로 편다 -- 구간 셈이 여기서만 일어나게."""
    m = _YM.match(str(x).strip())
    return int(m.group(1)) * 12 + int(m.group(2) or 1) if m else 0


def 읽기(것) -> 원장:
    """경로 · JSON 문자열 · dict · list -> 원장. **꼴이 아니면 빈 원장이다.**

    거절이 아니라 빈 원장이다 -- 그러면 관문이 전부 '미검증' 을 내고, 보고서가
    "원장이 비어 있다" 를 크게 적는다. 예외로 죽으면 그 말을 할 자리가 없어진다.
    """
    if isinstance(것, (str, Path)):
        # **`exists()` 로 보면 안 된다.** 빈 문자열은 `Path("")` -> `.` 이고, 그것은
        # 있는 데다 디렉터리라 `read_text` 가 IsADirectoryError 로 죽는다(실측).
        # 빈 원장을 돌려줘야 할 자리에서 예외로 죽으면 "원장이 비었다" 를 말할 자리가
        # 없어진다.
        p = Path(것) if str(것).strip() else None
        try:
            if p is not None and p.is_file():
                것 = p.read_text(encoding="utf-8")
        except OSError:
            return 원장()
        try:
            것 = json.loads(것)
        except (json.JSONDecodeError, TypeError):
            return 원장()
    if isinstance(것, dict):
        것 = 것.get("항목") or 것.get("항목들") or [것]
    if not isinstance(것, list):
        return 원장()

    out = []
    for x in 것:
        if not isinstance(x, dict) or not str(x.get("id") or "").strip():
            continue
        언제 = x.get("언제") or []
        언제 = tuple(str(v).strip() for v in (언제 if isinstance(언제, (list, tuple))
                                             else [언제]) if str(v).strip())
        잰 = []
        for m in (x.get("잰것") or []):
            if isinstance(m, dict):
                잰.append(잰것(무엇=str(m.get("무엇") or ""), 전=str(m.get("전") or ""),
                              후=str(m.get("후") or ""), 단위=str(m.get("단위") or ""),
                              어떻게=str(m.get("어떻게") or "")))
        out.append(항목(
            id=str(x["id"]).strip(), 갈래=str(x.get("갈래") or ""),
            이름=str(x.get("이름") or ""), 곳=str(x.get("곳") or ""), 언제=언제,
            역할=str(x.get("역할") or "").strip(),
            한일=[str(v) for v in (x.get("한일") or [])], 잰것=잰,
            쓴것=[str(v) for v in (x.get("쓴것") or [])],
            같이=int(x.get("같이") or 0), 증빙=str(x.get("증빙") or ""),
            전념=bool(x.get("전념", True))))
    return 원장(out)


# ---------------------------------------------------------------- 검사

def 검사(L: 원장) -> list:
    """E001~E006. **성함만 본다** -- 이 경험이 실제로 있었는지는 관할 밖이다.

    `reason/schema.py` 가 "스키마가 참인지는 못 본다" 고 적은 자리와 같다. 여기가
    붙드는 것은 '판정할 수 있는 꼴인가' 뿐이다.
    """
    vs = []
    ids = [h.id for h in L.항목들]
    for i in sorted({i for i in ids if ids.count(i) > 1}):
        vs.append(위반("E001", "hard", i,
                      f"같은 id 가 {ids.count(i)}번 있다 -- 자소서가 어느 것을 "
                      "가리키는지 판정할 수 없다"))
    for h in L.항목들:
        if h.역할 not in 역할들:
            vs.append(위반("E002", "hard", h.id,
                          f"역할이 {h.역할!r} 이다. {' · '.join(역할들)} 중 하나여야 "
                          "한다 -- 자유 서술이면 J004(역할 승격)가 눈이 없다"))
        if not h.언제 or not all(_YM.match(x) for x in h.언제):
            vs.append(위반("E003", "hard", h.id,
                          f"기간이 {list(h.언제)!r} 이다. 'YYYY-MM' 두 개(또는 하나)로 "
                          "적어야 한다 -- J003 이 이것으로 겹침과 길이를 잰다"))
        elif len(h.언제) == 2 and _달(h.언제[0]) > _달(h.언제[1]):
            vs.append(위반("E003", "hard", h.id,
                          f"시작({h.언제[0]})이 끝({h.언제[1]})보다 뒤다"))
        for m in h.잰것:
            if not m.쓸수있나:
                vs.append(위반("E004", "soft", f"{h.id} · {m.무엇 or '?'}",
                              "잰 방법이 없다 -- **원장에는 남지만 자소서에는 못 쓴다**"
                              "(J002 가 막는다). 어떻게 쟀는지 한 줄 적으면 쓸 수 있다"))
        if not h.증빙.strip():
            vs.append(위반("E005", "soft", h.id,
                          "증빙이 안 적혔다 -- 원장에는 남는다. 면접에서 물으면 "
                          "무엇을 보여 줄지만 적어 두면 된다"))
    vs.extend(_겹침(L))
    return vs


def _겹침(L: 원장) -> list:
    """E006 -- 전념 구간이 겹치는가. **위반이 아니라 표시다.**

    겸업·병행은 실제로 있다. 원장이 거짓이라는 뜻이 아니라, 자소서에 둘 다 풀타임인
    것처럼 쓰면 읽는 사람이 걸린다는 뜻이다. 그래서 soft 이고, 관문 J003 이 자소서
    본문에서 그 주장을 실제로 했을 때 비로소 hard 가 된다.
    """
    쓸것 = [h for h in L.항목들 if h.전념 and len(h.언제) == 2
            and all(_YM.match(x) for x in h.언제) and _달(h.언제[0]) <= _달(h.언제[1])]
    out = []
    for i, a in enumerate(쓸것):
        for b in 쓸것[i + 1:]:
            겹 = min(_달(a.언제[1]), _달(b.언제[1])) - max(_달(a.언제[0]), _달(b.언제[0])) + 1
            if 겹 > 0:
                out.append(위반("E006", "soft", f"{a.id} × {b.id}",
                               f"전념 구간이 {겹}개월 겹친다 -- 둘 다 풀타임으로 "
                               "적으면 읽는 사람이 걸린다. 한쪽의 `전념` 을 false 로 "
                               "두거나 자소서에서 병행이라고 밝혀라"))
    return out


def hard(vs) -> list:
    return [v for v in vs if v.등급 == "hard"]


# ---------------------------------------------------------------- 앵커

# 글자가 하나도 없는 것은 앵커가 아니다. 실측: 이름의 `--` 가 앵커로 잡혔다.
_글자 = re.compile(r"[0-9A-Za-z가-힣]")

# 앵커로 안 세는 흔한 말. **이것이 없으면 '분석' · '개발' 같은 말이 앵커가 되고,
# 그러면 어느 자소서에나 앵커가 있어서 P001 이 눈이 없어진다.**
흔한말 = {"분석", "개발", "설계", "운영", "관리", "기획", "개선", "구축", "협업",
          "데이터", "프로젝트", "시스템", "서비스", "팀", "회사", "업무", "경험",
          "연구", "학습", "교육", "활동", "인턴", "동아리", "학회", "대회"}


def 말앵커(h: 항목) -> set:
    """이 항목에서 온 **고유한 말**. 곳 · 이름 · 쓴것.

    흔한말은 뺀다. 두 글자 미만도 뺀다 -- 'AI' 같은 것은 남기되 한 글자는 아무 데나
    걸린다.
    """
    out = set()
    for x in [h.곳, h.이름] + list(h.쓴것):
        t = re.sub(r"\s+", " ", str(x)).strip()
        # 붙은 이름에서 낱말도 따로 -- '사내 추천 시스템 개편' 에서 '추천' 을 건진다
        for w in [t] + re.split(r"[\s/·,()]+", t):
            if len(w) >= 2 and w not in 흔한말 and _글자.search(w):
                out.add(w)
    return out


def 수앵커(h: 항목, 쓸수있는것만: bool = False) -> set:
    """이 항목에서 온 **수**. 잰 값과 인원.

    `쓸수있는것만` 이면 잰 방법이 적힌 수만 돌려준다 -- J002 가 그 꼴로 쓴다.
    """
    out = set()
    for m in h.잰것:
        if 쓸수있는것만 and not m.쓸수있나:
            continue
        out |= set(m.수들)
        # **재는 법에 적힌 수도 원장의 수다.** 실측: "2주간 A/B 로 클릭률을 개선했다"
        # 에서 `2주` 가 원장에 없는 수로 잡혀 J002 위반이 됐다 -- 그런데 그 `2주` 는
        # 사용자가 `어떻게` 에 적어 둔 바로 그 값이었다. 성한 문장을 기각하는 관문은
        # 없느니만 못하다.
        out |= 숫자들(m.어떻게)
    if h.같이:
        out.add(str(h.같이))
    if h.개월:                          # "6개월간 ~ 개선했습니다" 도 원장에서 온 수다
        out.add(str(h.개월))
    return out


# 같은 뜻인데 다르게 적는 단위. **정규화 안 하면 `퍼센트` 와 `%` 가 딴 값이 된다.**
단위정규 = {"퍼센트": "%", "프로": "%", "인": "명", "사람": "명", "달": "개월",
            "개월": "개월", "년": "년", "시간": "시간", "초": "초", "분": "분"}


def _단위(u: str) -> str:
    return 단위정규.get((u or "").strip(), (u or "").strip())


def 값앵커(h: 항목, 쓸수있는것만: bool = False) -> set:
    """**(수, 단위) 쌍**으로 된 앵커. `"2.1|%"` 꼴. J002 가 이것으로 판정한다.

    수만 보면 안 되는 이유가 실측으로 나왔다. 어떤 항목의 `어떻게` 에 `30일치` 가
    적혀 있으면 수 `30` 이 원장에 있는 것이 되고, 그러면 **지어낸 `매출 30% 향상`
    이 통과한다.** 단위까지 묶어야 `30|일` 과 `30|%` 가 갈린다.

    `어떻게`(재는 법)에 적힌 수도 원장의 수다 -- "2주간 A/B" 를 자소서가 그대로
    말하는 것은 지어낸 것이 아니다.
    """
    from jaso import wording as WD                      # 자는 한 벌만 -- wording 것
    out = set()
    for m in h.잰것:
        if 쓸수있는것만 and not m.쓸수있나:
            continue
        u = _단위(m.단위)
        for v in m.수들:
            out.add(f"{v}|{u}")
        for 수, 단위, _ in WD.수단위쌍(m.어떻게):
            out.add(f"{수}|{_단위(단위)}")
    if h.같이:
        out.add(f"{h.같이}|명")
    if h.개월:
        out.add(f"{h.개월}|개월")
    return out


def 값수(h: 항목, 쓸수있는것만: bool = False) -> set:
    """**잰 값 그 자체**의 수만. 재는 법에 적힌 수는 안 넣는다.

    J002 가 '수는 맞는데 단위가 다르다'(soft)와 '원장에 없는 수다'(hard)를 가르는
    자리다. 여기에 재는 법의 수까지 넣으면 그 둘이 안 갈린다.
    """
    return {v for m in h.잰것 if not (쓸수있는것만 and not m.쓸수있나)
            for v in m.수들}


def 숫자들(글: str) -> set:
    """글에서 수를 뽑아 원장과 같은 꼴로 편다. `48,000건` · `2.1%` · `4명`."""
    return {v for v in (_수(m) for m in re.findall(r"\d[\d,]*(?:\.\d+)?", 글 or "")) if v}


def 앵커(글: str, h: 항목) -> list:
    """이 글에 이 항목의 앵커가 몇 개나 박혀 있나. **P001 이 세는 것이 이것이다.**"""
    글 = 글 or ""
    수 = 숫자들(글)
    return sorted({a for a in 말앵커(h) if a in 글} | (수앵커(h) & 수))


# ---------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="경험 원장을 읽고 성한지 본다")
    ap.add_argument("--표", dest="표", default="jaso/보기.json",
                    help="원장 JSON (`-` 면 표준입력)")
    ap.add_argument("--앵커", action="store_true", help="항목마다 앵커를 늘어놓는다")
    a = ap.parse_args(argv)

    raw = sys.stdin.read() if a.표 == "-" else a.표
    L = 읽기(raw)
    if not L:
        print("원장이 비었다 -- 읽을 항목이 없다. 꼴을 보려면 jaso/보기.json",
              file=sys.stderr)
        return 3

    vs = 검사(L)
    print(f"항목 {len(L)}개")
    for v in vs:
        print(f"  {v}")
    if not vs:
        print("  E001~E006: 위반 없음")

    못쓰는수 = sum(1 for h in L.항목들 for m in h.잰것 if not m.쓸수있나)
    쓰는수 = sum(1 for h in L.항목들 for m in h.잰것 if m.쓸수있나)
    print(f"\n수: 쓸 수 있는 것 {쓰는수}개 · 잰 방법이 없어 못 쓰는 것 {못쓰는수}개")
    if a.앵커:
        for h in L.항목들:
            print(f"\n[{h.id}] {h.이름}  ({h.역할} · {h.개월}개월)")
            print(f"    말: {', '.join(sorted(말앵커(h))) or '(없다)'}")
            print(f"    수: {', '.join(sorted(수앵커(h))) or '(없다)'}")
    빈앵커 = [h.id for h in L.항목들 if not 말앵커(h) and not 수앵커(h)]
    if 빈앵커:
        print(f"\n**앵커가 하나도 없는 항목: {', '.join(빈앵커)}** -- 이 항목으로 쓴 "
              "문단은 P001(치환 가능)에 걸린다. 곳·기술·수 중 하나는 적어야 한다")
    return 1 if hard(vs) else 0


if __name__ == "__main__":
    raise SystemExit(main())
