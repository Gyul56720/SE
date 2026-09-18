"""**투기적 언롤 DFE 의 고정소수점 골든.** RTL 이 이것과 비트까지 같아야 한다.

`spec/IP_투기적언롤DFE.md` 의 1단계. 여기가 없으면 합성해서 면적을 보고하고도
**그것이 맞는 답을 내는지 아무도 안 본다** -- 이 저장소가 내내 쫓은 거짓 초록이다.

## 왜 정수로만 두는가 -- 되먹임 경로에는 반올림이 없다

되먹임에 들어가는 것은 **판정된 심볼**이고, 심볼은 작은 정수다(NRZ ±1, PAM4 ±1·±3).
그러니 탭 가중치 `c[k]` 를 **심볼 한 단위당 값**으로 두면

    acc = x[t] - sum_k c[k] * m[t-k]        <- 정수 곱과 정수 덧셈뿐. 반올림 0

이 된다. 실리콘도 이렇게 한다(탭 DAC 을 심볼이 직접 몬다).

## 그래서 S2 가 바뀐다 -- 순서가 아니라 **넘침**이다

부동소수점에서는 합산 순서가 마지막 비트를 바꿔 문턱 근처 판정이 갈렸다
(`spec/증거/언롤_항등성_유리수증명.py`: 무한정밀 0/60, 배정밀도 10/200).
**정수 덧셈은 결합법칙을 지키므로 순서가 자유롭다.** 대신 넘치면 순서에 따라
**다르게** 넘친다. 그러므로 스펙 항목은

    S2'  누산기가 안 넘칠 폭을 잡는다.  넘치면 직접형과 투기형이 갈린다.

로 고쳐 적는다. `누산최소폭()` 이 그 폭을 닫힌 꼴로 내고, `tests/test_spec_dfe.py`
가 **좁은 폭에서 실제로 갈리는지**까지 본다(안 갈리면 그 검사는 아무것도 안 잡는 것이다).

## S1 은 그대로다

투기형은 `m[-1]` 을 **반드시** 쓴다(그것으로 먹스를 고르므로). 직접형이 그 자리를
"없음"으로 다루면 둘은 다른 회로다. 초기값을 같게 못 박는다.
"""
from __future__ import annotations

NRZ, PAM4 = "NRZ", "PAM4"


def 레벨들(변조: str) -> "tuple[int, ...]":
    """심볼 색인. **진폭이 아니라 색인이다** -- 진폭은 `g` 가 갖는다."""
    if 변조 == NRZ:
        return (-1, 1)
    if 변조 == PAM4:
        return (-3, -1, 1, 3)
    raise ValueError(f"모르는 변조: {변조}")


def 슬라이서(acc: int, g: int, 변조: str) -> int:
    """이상적 입력은 `m*g` 다. 문턱은 그 사이 한가운데."""
    if 변조 == NRZ:
        return 1 if acc >= 0 else -1
    if acc >= 2 * g:
        return 3
    if acc >= 0:
        return 1
    if acc >= -2 * g:
        return -1
    return -3


def 누산최소폭(x최대: int, c: "list[int]", 변조: str) -> int:
    """누산기가 **안 넘칠** 부호 폭. 넘치면 직접형과 투기형이 갈린다."""
    최대레벨 = max(abs(m) for m in 레벨들(변조))
    한계 = int(x최대) + sum(abs(int(v)) for v in c) * 최대레벨
    폭 = 2
    while (1 << (폭 - 1)) - 1 < 한계:
        폭 += 1
    return 폭


def _감싸기(v: int, 폭: "int | None") -> int:
    """2의 보수 감싸기. `폭=None` 이면 안 감싼다(무한 폭)."""
    if 폭 is None:
        return int(v)
    m = 1 << int(폭)
    v = int(v) % m
    return v - m if v >= (m >> 1) else v


def _과거(m: "list[int]", t: int, k: int, 초기: "list[int]") -> int:
    """`m[t-k]`. 음수 자리는 초기 레지스터에서 꺼낸다 (**S1**)."""
    return m[t - k] if t - k >= 0 else int(초기[k - 1 - t])


def 직접형(x, c, g: int, 변조: str = NRZ, 초기=None, 누산폭=None) -> "list[int]":
    """교과서 DFE. 되먹임 고리에 **합산기와 래치가 함께** 들어 있다."""
    c = [int(v) for v in c]
    초기 = [int(v) for v in (초기 if 초기 is not None else [0] * len(c))]
    out: "list[int]" = []
    for t in range(len(x)):
        acc = int(x[t])
        for k in range(1, len(c) + 1):
            acc = _감싸기(acc - c[k - 1] * _과거(out, t, k, 초기), 누산폭)
        out.append(슬라이서(acc, g, 변조))
    return out


def 투기형(x, c, g: int, 변조: str = NRZ, N: int = 1, 초기=None,
        누산폭=None) -> "list[int]":
    """**언롤 깊이 N.** 앞 N 탭의 모든 가설을 미리 다 계산해 두고, 지난 판정으로
    **먹스만** 고른다. 고리에서 합산기가 빠지고 먹스가 들어간다.

    갈래 수 = len(레벨들)^N  (NRZ 2^N · PAM4 4^N). 슬라이서도 그만큼 든다.
    """
    c = [int(v) for v in c]
    L = 레벨들(변조)
    N = max(1, min(int(N), len(c)))
    초기 = [int(v) for v in (초기 if 초기 is not None else [0] * len(c))]
    out: "list[int]" = []
    갈래들 = [()]
    for _ in range(N):
        갈래들 = [g0 + (s,) for g0 in 갈래들 for s in L]
    for t in range(len(x)):
        rest = int(x[t])                                   # 잔여 직접형 탭 (N+1 .. )
        for k in range(N + 1, len(c) + 1):
            rest = _감싸기(rest - c[k - 1] * _과거(out, t, k, 초기), 누산폭)
        표 = {}                                            # <- 이것이 '표' 다
        for 갈래 in 갈래들:
            a = rest
            for i, s in enumerate(갈래):
                a = _감싸기(a - c[i] * s, 누산폭)
            표[갈래] = 슬라이서(a, g, 변조)
        고른것 = tuple(_과거(out, t, k, 초기) for k in range(1, N + 1))
        out.append(표[고른것])                              # <- 먹스
    return out


def 갈래수(변조: str, N: int) -> int:
    return len(레벨들(변조)) ** int(N)


def 슬라이서수(변조: str, N: int) -> int:
    """PAM4 는 갈래마다 문턱 3개가 필요하다."""
    문턱 = 1 if 변조 == NRZ else 3
    return 갈래수(변조, N) * 문턱
