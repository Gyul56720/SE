"""**널 모형 -- 기저율.** 이 파일이 없으면 이 파이프라인이 내는 수는 전부 거짓말이다.

## 왜

"규제 금지 뉴스가 뜨면 7일 뒤 +4.2%" 는 그 자체로 아무 뜻이 없다. 비트코인은
2017~2021 구간에서 **아무 날이나 골라도** 7일 뒤가 +1~2% 다. 그러면 +4.2% 의 절반은
그냥 시장이 오른 것이고, 남는 것이 무엇인지는 **아무 날이나 골라 같은 자로 재 보기
전에는 모른다.**

그래서 여기서 하는 일은 하나다: **같은 자로, 상관없는 날들을 재서, 관측이 그 분포의
어디쯤인가를 본다.**

    초과 = 관측중앙 - 널중앙        <- 보고할 수
    p    = 널이 관측만큼 나온 비율   <- 그 수를 믿을 만한가

## 널을 어떻게 뽑나 -- 두 가지, 그리고 왜 기본이 '이동' 인가

    무작위   아무 날이나 n개. 쉽지만 **사건의 뭉침을 안 흉내 낸다**
    이동     사건 날짜 집합 전체를 k일 통째로 민다 (원형으로 감음). **기본**

사건은 뭉쳐서 난다 -- 규제 뉴스는 한 주에 몰리고 그 주는 시장이 이미 흔들리는 주다.
무작위로 흩뿌린 날들은 그 뭉침이 없어서 **널의 분산이 실제보다 작게 나오고**, 그러면
p 가 실제보다 작게(= 있어 보이게) 나온다. 통째로 밀면 뭉침·간격·계절성이 그대로
남은 채 뉴스-가격 짝만 끊긴다. 그것이 우리가 지우고 싶은 딱 하나다.

## 겹침

지평 7일짜리를 이틀 간격 사건 두 개에 재면 그 둘은 거의 같은 구간을 본다. n 을
그대로 세면 표본이 실제보다 많아 보인다. `유효표본()` 이 **안 겹치게 골라 센 수**를
따로 준다 -- 보고에 둘 다 적는다.

## 여러 번 시험하면 뭔가는 걸린다

유형 13 × 자산 5 × 지평 5 = 325 번 재면 p<0.05 짜리가 **아무 신호가 없어도 16개쯤**
나온다. `보정()` 이 Benjamini-Hochberg 로 그 자리를 잡고, 몇 번 쟀는지를 잰 값마다
적어 둔다. `gate.py` 가 그 수를 답이 밝혔는지 본다.
"""
from __future__ import annotations

import random
from statistics import median


def 중앙(값들) -> float:
    값들 = [v for v in 값들 if v is not None]
    return median(값들) if 값들 else float("nan")


def 승률(값들) -> float:
    값들 = [v for v in 값들 if v is not None]
    return (sum(1 for v in 값들 if v > 0) / len(값들)) if 값들 else float("nan")


def 유효표본(날들, 지평: int, 차례: dict) -> int:
    """**안 겹치게 골라 센 수.** 앞에서부터 잡고 지평 안에 드는 것은 건너뛴다."""
    쓴것, 끝 = 0, -1
    for d in sorted(날들):
        i = 차례.get(d)
        if i is None:
            continue
        if i > 끝:
            쓴것 += 1
            끝 = i + 지평 - 1
    return 쓴것


def _잰다(계열, 날들, 지평: int):
    return [계열.수익(d, 지평) for d in 날들]


def 널(계열, 사건날들, 지평: int, 판수: int = 2000, 씨: int = 20260909,
       꼴: str = "이동") -> dict:
    """널 분포를 만든다. 돌려주는 것은 **판마다의 중앙값 목록**.

    `씨` 가 원장에 적힌다 -- 안 적으면 다시 세도 같은 값이 안 나오고, 그러면
    `gate.py` 의 다시셈(C002)이 못 돈다.
    """
    쓸날 = 계열.살수있는날들(지평)
    if not 쓸날 or not 사건날들:
        return {"판": [], "꼴": 꼴, "씨": 씨, "판수": 0}
    차례 = {d: i for i, d in enumerate(쓸날)}
    자리 = sorted({차례[d] for d in 사건날들 if d in 차례})
    if not 자리:
        return {"판": [], "꼴": 꼴, "씨": 씨, "판수": 0}
    R = random.Random(씨)
    N = len(쓸날)
    판 = []
    for _ in range(판수):
        if 꼴 == "이동":
            k = R.randrange(N)
            뽑 = [쓸날[(i + k) % N] for i in 자리]        # **간격을 그대로 둔 채 민다**
        else:
            뽑 = [쓸날[R.randrange(N)] for _ in 자리]
        m = 중앙(_잰다(계열, 뽑, 지평))
        if m == m:                                        # nan 이 아니면
            판.append(m)
    판.sort()
    return {"판": 판, "꼴": 꼴, "씨": 씨, "판수": len(판)}


def p값(관측: float, 판: list) -> dict:
    """(1 + 넘은 수) / (판수 + 1). **0 이 안 나오게** 한 칸 더한다 -- 판수가 유한한데
    p=0 이라고 적으면 '절대 우연이 아니다' 가 되어 버린다."""
    n = len(판)
    if not n or 관측 != 관측:
        return {"상향": float("nan"), "하향": float("nan"), "양측": float("nan")}
    위 = (1 + sum(1 for v in 판 if v >= 관측)) / (n + 1)
    아래 = (1 + sum(1 for v in 판 if v <= 관측)) / (n + 1)
    return {"상향": 위, "하향": 아래, "양측": min(1.0, 2 * min(위, 아래))}


def 구간(판: list, 아래: float = 0.05, 위: float = 0.95) -> tuple:
    if not 판:
        return (float("nan"), float("nan"))
    n = len(판)
    return (판[max(0, int(아래 * n))], 판[min(n - 1, int(위 * n))])


def 보정(잰것들: list, q: float = 0.10, 칸: str = "p양측") -> list:
    """Benjamini-Hochberg. 각 잰것에 `살아남음` 과 `문턱` 을 박아 돌려준다.

    **몇 번 쟀는지를 안 적으면 이 보정은 못 한다.** 그래서 `시험수` 도 같이 적는다.
    """
    쓸것 = [r for r in 잰것들 if isinstance(r.get(칸), float) and r[칸] == r[칸]]
    m = len(쓸것)
    순 = sorted(쓸것, key=lambda r: r[칸])
    큰k = 0
    for i, r in enumerate(순, 1):
        if r[칸] <= i / m * q:
            큰k = i
    문턱 = (큰k / m * q) if (m and 큰k) else 0.0
    for r in 잰것들:
        r["시험수"] = m
        r["FDR"] = q
        r["문턱"] = 문턱
        v = r.get(칸)
        r["살아남음"] = bool(m and 큰k and isinstance(v, float) and v == v and v <= 문턱)
    return 잰것들
