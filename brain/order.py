"""**작업표** -- 물음을 검사 꼴로 쪼갠 것. 그리고 그 쪼갬을 코드가 검사한다.

물음이 무엇일지는 아무도 모른다. 그래서 **쪼개는 일은 모델이 하고, 쪼갠 것이 성한지는
코드가 본다.** `law/METHOD.md` 의 분업 그대로다 -- LLM 은 조문에서 요건을 뽑고(대조
가능한 일), 쟁점은 코드가 도출한다.

    물음 --(모델)--> 작업표 --(코드 R001~R005)--> 성하면 돌린다
                       |
                  못 세우면 --> 관할 밖이라 말한다

## 모델이 지어낼 수 있는 것과 없는 것

    지어낼 수 있다   어느 꼴로 갈지 · 무엇을 대조할지 · 무엇을 기준선으로 둘지
    지어낼 수 없다   **꼴 자체**(닫힌 다섯) · 재료가 있는 척(R002/R003 이 잡는다)
                     · 판정(꼴을 돌리는 코드가 낸다)

지어낸 꼴 이름은 R001 이 잡고, 없는 재료는 R002 가 잡는다. 그래서 모델이 아무리
그럴듯하게 써도 **판정까지는 못 간다.**

## R004 가 이 파일에서 제일 중요하다

**관할 밖 칸이 비어 있으면 위반이다.** 어떤 물음도 통째로 기계 판정되지 않는다 --
원인·전망·가치·처방은 늘 남는다. 그것을 안 적었다는 것은 다 판정했다고 믿는 것이고,
그 믿음이 판정 안 받은 답에 판정받은 옷을 입히는 자리다.

모든 보고서가 끝에 '안 보는 것' 을 적는 것과 같은 규율이다. 여기서는 **시작할 때**
적게 한다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from brain import form as FM


@dataclass
class 조각:
    주장: str = ""                 # 무엇을 검사할 것인가
    꼴: str = ""                   # FORMS 의 이름
    재료: dict = field(default_factory=dict)
    왜: str = ""


@dataclass
class 작업표:
    물음: str = ""
    조각: list = field(default_factory=list)
    관할밖: list = field(default_factory=list)   # [{"무엇":..., "왜":...}]

    @property
    def 갈데없음(self) -> bool:
        return not self.조각


@dataclass
class 위반:
    규칙: str
    등급: str
    어디: str
    말: str

    def __str__(self) -> str:
        return f"[{self.규칙}/{self.등급}] {self.어디}: {self.말}"


AIM = {
    "R001": "검사 꼴이 닫힌 다섯 중 하나여야 한다",
    "R002": "그 꼴이 요구하는 재료가 다 채워져야 한다",
    "R003": "재료가 빈 값이 아니어야 한다",
    "R004": "관할 밖을 적어야 한다 -- 통째로 판정되는 물음은 없다",
    "R005": "갈 데가 하나도 없으면 그렇다고 적어야 한다",
}


def 읽기(d) -> 작업표:
    """dict 나 JSON 문자열 -> 작업표. **꼴이 아니면 빈 작업표다.**"""
    if isinstance(d, str):
        try:
            d = json.loads(d)
        except json.JSONDecodeError:
            return 작업표()
    if not isinstance(d, dict):
        return 작업표()
    조각들 = []
    for p in (d.get("조각") or []):
        if isinstance(p, dict):
            조각들.append(조각(주장=str(p.get("주장") or ""), 꼴=str(p.get("꼴") or ""),
                             재료=p.get("재료") if isinstance(p.get("재료"), dict) else {},
                             왜=str(p.get("왜") or "")))
    밖 = [x for x in (d.get("관할밖") or []) if isinstance(x, dict)]
    return 작업표(물음=str(d.get("물음") or ""), 조각=조각들, 관할밖=밖)


def 검사(표: 작업표) -> list:
    """R001~R005. **판정을 안 한다** -- 작업표가 성한지만 본다."""
    vs = []
    for i, p in enumerate(표.조각, 1):
        어디 = f"조각{i}({p.주장[:24] or '이름없음'})"
        f = FM.get(p.꼴)
        if f is None:
            vs.append(위반("R001", "hard", 어디,
                          f"그런 검사 꼴이 없다: {p.꼴!r} -- 있는 것은 "
                          f"{', '.join(FM.FORMS)}. 꼴은 요청 시점에 못 늘린다"))
            continue
        빠짐 = [k for k in f.있어야 if k not in p.재료]
        if 빠짐:
            vs.append(위반("R002", "hard", 어디,
                          f"'{p.꼴}' 꼴에 필요한 재료가 없다: {', '.join(빠짐)}"))
        빔 = [k for k in f.있어야
              if k in p.재료 and not str(p.재료.get(k) or "").strip()]
        if 빔:
            vs.append(위반("R003", "hard", 어디,
                          f"재료가 빈 값이다: {', '.join(빔)} -- "
                          "칸만 채우고 내용이 없으면 검사가 도는 척만 한다"))
    # R004 -- **비어 있으면 위반이다**
    if not 표.관할밖:
        vs.append(위반("R004", "hard", "작업표",
                      "관할 밖을 하나도 안 적었다. 어떤 물음도 통째로 기계 판정되지 "
                      f"않는다 -- 늘 남는 것: {', '.join(FM.관할밖)}"))
    else:
        for x in 표.관할밖:
            if not str(x.get("무엇") or "").strip():
                vs.append(위반("R004", "soft", "관할밖",
                              "무엇이 관할 밖인지 안 적혔다"))
    # R005 -- 갈 데가 없으면 그렇다고 말해야 한다
    if 표.갈데없음 and not 표.관할밖:
        vs.append(위반("R005", "hard", "작업표",
                      "검사할 조각도 없고 관할 밖도 안 적었다 -- 아무 말도 안 한 것이다"))
    return vs


def hard(vs) -> list:
    return [v for v in vs if v.등급 == "hard"]


def 보고(표: 작업표, vs) -> str:
    out = [f"# 작업표 -- {표.물음[:70]}", ""]
    if 표.갈데없음:
        out.append("**검사 꼴로 갈 조각이 없다.** 이 물음은 통째로 관할 밖이다.")
        out.append("판정 없이 답해도 된다 -- 다만 **수치를 붙이지 마라.** "
                   "없는 출처와 근거 없는 수가 정확히 그 자리에서 나온다.")
        out.append("")
    else:
        out.append(f"검사할 조각 {len(표.조각)}개")
        out.append("")
        for i, p in enumerate(표.조각, 1):
            f = FM.get(p.꼴)
            out.append(f"  {i}. [{p.꼴}] {p.주장}")
            if f:
                out.append(f"       묻는 것: {f.묻는것}")
                out.append(f"       판정:    {' / '.join(f.판정)}")
                out.append(f"       돌린다:  {f.돌리는것}")
                out.append(f"       **못 하는 것**: {f.못하는것}")
            for k, v in p.재료.items():
                out.append(f"       {k}: {str(v)[:70]}")
            out.append("")
    out.append("## 관할 밖 -- 판정 없이 답할 자리")
    out.append("")
    if 표.관할밖:
        for x in 표.관할밖:
            out.append(f"  · {x.get('무엇', '?')} -- {x.get('왜', '')}")
    else:
        out.append("  (안 적혔다 -- R004 위반)")
    out.append("")
    out.append("## 작업표 관문")
    out.append("")
    if not vs:
        out.append("  R001~R005: 위반 없음 -- 이 작업표는 돌려도 된다")
    else:
        out.append(f"  위반 {len(hard(vs))}건(hard) · {len(vs) - len(hard(vs))}건(soft)")
        for v in vs:
            out.append(f"    {v}")
        if hard(vs):
            out.append("")
            out.append("  **hard 가 있으면 돌리지 않는다.** 재료를 채우거나, "
                       "그 조각을 관할 밖으로 옮겨라.")
    return "\n".join(out)
