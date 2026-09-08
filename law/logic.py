"""수리논리 -- **본문에서 따라 나오는 것만 참이라고 말한다.**

LEET 추리논증의 규칙이 이 저장소의 규율과 같다: **사전 지식을 쓰지 않는다.**
지문에 없는 것은 아무리 그럴듯해도 답이 아니고, 지문에서 따라 나오는 것은 아무리
뜻밖이어도 답이다. 그래서 여기서 하는 일은 하나다 -- 지문을 명제로 세우고,
선택지가 **거기서 따라 나오는가 · 거스르는가 · 아무 관계도 없는가**를 가른다.

    참    지문의 모든 해석에서 선택지가 참이다        (KB |= C)
    거짓  지문의 모든 해석에서 선택지가 거짓이다      (KB |= ~C)
    모름  둘 다 아니다 -- **지문이 말하지 않았다**

**'모름' 을 답으로 세지 않는다.** 이것이 이 파일의 전부다. 그럴듯한데 지문에 없는
것을 참이라 하면 그것이 곧 사전 지식을 쓴 것이다. 미검증은 통과가 아니다.

## 왜 진리표인가

해석을 전부 세어 본다. 느려 보이지만 원자가 20개면 100만 해석이고, LEET 한 문항의
원자는 대개 열 개 안쪽이다. 그리고 이 방법은 **건전하고 완전하다** -- 놓치는 추론도
없고 지어내는 추론도 없다. 규칙을 손으로 늘리다 보면 어느 규칙이 빠졌는지 아무도
모르게 되는데, 심판이 그렇게 되면 안 된다.

원자가 너무 많으면 **못 쟀다고 말한다.** 짐작해서 답하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product

원자꼴, 부정꼴, 그리고꼴, 또는꼴, 함의꼴, 동치꼴 = "원자", "부정", "그리고", "또는", "함의", "동치"

# 원자가 이보다 많으면 진리표를 못 센다. 2^22 = 400만 -- 여기서 끊는다.
한계 = 22


@dataclass(frozen=True)
class 식:
    """논리식. 얼거나 바뀌지 않는다 -- 같은 식은 같은 열쇠를 갖는다."""

    꼴: str
    항: tuple = ()
    이름: str = ""

    def __str__(self) -> str:
        if self.꼴 == 원자꼴:
            return self.이름
        if self.꼴 == 부정꼴:
            return f"~{self.항[0]}"
        기호 = {그리고꼴: " & ", 또는꼴: " | ", 함의꼴: " -> ", 동치꼴: " <-> "}[self.꼴]
        return "(" + 기호.join(str(x) for x in self.항) + ")"


def 원자(이름: str) -> 식:
    return 식(원자꼴, (), 이름)


def 부정(f: 식) -> 식:
    return f.항[0] if f.꼴 == 부정꼴 else 식(부정꼴, (f,))


def 그리고(*fs) -> 식:
    fs = tuple(fs)
    return fs[0] if len(fs) == 1 else 식(그리고꼴, fs)


def 또는(*fs) -> 식:
    fs = tuple(fs)
    return fs[0] if len(fs) == 1 else 식(또는꼴, fs)


def 함의(a: 식, b: 식) -> 식:
    return 식(함의꼴, (a, b))


def 동치(a: 식, b: 식) -> 식:
    return 식(동치꼴, (a, b))


def 대우(f: 식) -> 식:
    """A -> B 를 ~B -> ~A 로. **같은 말이다** -- 새 정보가 아니라 다른 꼴이다."""
    if f.꼴 != 함의꼴:
        return f
    return 함의(부정(f.항[1]), 부정(f.항[0]))


def 원자들(f: 식) -> set:
    if f.꼴 == 원자꼴:
        return {f.이름}
    out = set()
    for x in f.항:
        out |= 원자들(x)
    return out


def 값(f: 식, 해석: dict) -> bool:
    """이 해석에서 이 식이 참인가."""
    if f.꼴 == 원자꼴:
        return 해석[f.이름]
    if f.꼴 == 부정꼴:
        return not 값(f.항[0], 해석)
    if f.꼴 == 그리고꼴:
        return all(값(x, 해석) for x in f.항)
    if f.꼴 == 또는꼴:
        return any(값(x, 해석) for x in f.항)
    if f.꼴 == 함의꼴:
        return (not 값(f.항[0], 해석)) or 값(f.항[1], 해석)
    return 값(f.항[0], 해석) == 값(f.항[1], 해석)


@dataclass
class 판정:
    """묻기의 답. **근거를 못 대면 참이라 하지 않는다.**"""

    값: str = "모름"           # 참 · 거짓 · 모름 · 못잼 · 지문모순
    근거: tuple = ()           # 답을 떠받치는 지문 줄들 (출처)
    반례: dict = field(default_factory=dict)   # 모름일 때, 갈리는 해석 하나
    왜: str = ""


@dataclass
class 망:
    """지문에서 세운 명제들. **여기 없는 것은 답의 근거가 못 된다.**"""

    줄: list = field(default_factory=list)     # [(식, 출처)]

    def 넣기(self, f: 식, 출처: str = "") -> None:
        self.줄.append((f, 출처))

    def 원자(self) -> list:
        out = set()
        for f, _ in self.줄:
            out |= 원자들(f)
        return sorted(out)

    def _해석들(self, 이름들):
        for 값들 in product((False, True), repeat=len(이름들)):
            yield dict(zip(이름들, 값들))

    def 묻기(self, c: 식) -> 판정:
        """선택지 `c` 가 지문에서 따라 나오는가."""
        이름들 = sorted(set(self.원자()) | 원자들(c))
        if len(이름들) > 한계:
            return 판정("못잼", 왜=f"원자가 {len(이름들)}개 -- 진리표를 못 센다. "
                                 f"**짐작해서 답하지 않는다**")
        참모형, 거짓모형 = None, None
        본것 = False
        for 해 in self._해석들(이름들):
            if not all(값(f, 해) for f, _ in self.줄):
                continue
            본것 = True
            if 값(c, 해):
                참모형 = 해
            else:
                거짓모형 = 해
            if 참모형 and 거짓모형:
                break
        if not 본것:
            # **지문 자체가 모순이면 무엇이든 따라 나온다.** 그 답은 답이 아니다.
            return 판정("지문모순", 왜="지문의 명제들을 다 참으로 만드는 해석이 없다 -- "
                                      "여기서 나오는 답은 무엇이든 참이 되므로 안 낸다")
        if 거짓모형 is None:
            return 판정("참", 근거=self._근거(c, True), 왜="지문의 모든 해석에서 참이다")
        if 참모형 is None:
            return 판정("거짓", 근거=self._근거(c, False), 왜="지문의 모든 해석에서 거짓이다")
        return 판정("모름", 반례=거짓모형,
                   왜="지문이 이것을 말하지 않았다 -- **그럴듯한 것은 답이 아니다**")

    def _근거(self, c: 식, 참인가: bool) -> tuple:
        """답을 떠받치는 **가장 작은** 줄 묶음. 하나씩 빼 보고 그래도 되면 뺀다.

        근거를 대는 것이 답을 내는 것만큼 중요하다. 지문 전체를 근거라 하면
        '본문에서 나왔다' 는 말이 아무것도 안 가리킨다.
        """
        쓸것 = list(self.줄)
        for i in range(len(쓸것) - 1, -1, -1):
            남 = 쓸것[:i] + 쓸것[i + 1:]
            if 망(남)._따라나오나(c, 참인가):
                쓸것 = 남
        return tuple(출처 or str(f) for f, 출처 in 쓸것)

    def _따라나오나(self, c: 식, 참인가: bool) -> bool:
        이름들 = sorted(set(self.원자()) | 원자들(c))
        if len(이름들) > 한계:
            return False
        본것 = False
        for 해 in self._해석들(이름들):
            if not all(값(f, 해) for f, _ in self.줄):
                continue
            본것 = True
            if 값(c, 해) != 참인가:
                return False
        return 본것


# ---------------------------------------------------------------- 흔한 오류
# LEET 가 매년 내는 자리다. **꼴이 비슷하고 결론이 반대**라서 사람이 잘 속는다.
# 여기서는 진리표가 알아서 가르지만, **왜 아닌지를 말할 수 있어야** 쓸모가 있다.

def 오류이름(전제들, 결론) -> str:
    """이 걸음이 알려진 오류의 꼴인가. 아니면 빈 문자열."""
    가언 = [f for f in 전제들 if f.꼴 == 함의꼴]
    for h in 가언:
        앞, 뒤 = h.항
        others = [f for f in 전제들 if f is not h]
        if any(f == 뒤 for f in others) and 결론 == 앞:
            return "후건긍정 -- B 가 참이라고 A 가 참인 것은 아니다"
        if any(f == 부정(앞) for f in others) and 결론 == 부정(뒤):
            return "전건부정 -- A 가 거짓이라고 B 가 거짓인 것은 아니다"
    return ""


# ---------------------------------------------------------------- 양화
# '모든 A 는 B 이다' 를 **지문에 이름이 나온 것들 위에서만** 편다. 도메인을 지문
# 밖으로 넓히면 그 순간 사전 지식이 들어온다.

def 모든(A, B, 것들) -> 식:
    """모든 A 는 B 다 -- 지문에 나온 것들 위에서. A(x) -> B(x) 의 그리고."""
    return 그리고(*[함의(원자(f"{A}({x})"), 원자(f"{B}({x})")) for x in 것들]) \
        if 것들 else 그리고(원자("참"), 부정(원자("참")))


def 어떤(A, B, 것들) -> 식:
    """어떤 A 는 B 다. A(x) & B(x) 의 또는."""
    return 또는(*[그리고(원자(f"{A}({x})"), 원자(f"{B}({x})")) for x in 것들]) \
        if 것들 else 그리고(원자("참"), 부정(원자("참")))


def 이다(A, x) -> 식:
    return 원자(f"{A}({x})")
