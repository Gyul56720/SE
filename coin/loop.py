"""**정제 루프 -- 멈추는 자리를 기계가 정한다.**

    바퀴마다:  프롬프트 <- 원장 + 앞 바퀴에서 어긋난 자리
               답      <- Gemini
               위반    <- gate.검사   (LLM 아님)
               점수    <- (hard, soft, -짚은수, 길이)   튜플 비교

    멈춘다:    hard 0 이고 soft 0        -- 더 좋아질 데가 없다
               hard 0 인데 점수가 안 나아짐 -- 두 바퀴 헛돌았다
               바퀴를 다 씀

    돌려준다:  점수가 가장 낮은 답. **hard 가 남아 있으면 안 내보낸다**

## 심판자가 LLM 이 아니라는 것의 뜻

"가장 좋은 답으로 정제되면" 을 모델에게 물으면 모델은 늘 자기 답이 좋다고 한다.
여기서 '가장 좋은' 은 위 튜플이 정한다 -- 원장에 없는 수가 몇 개인가, 기저율을
빠뜨렸는가, 방향이 잰 것과 맞는가. 사람 취향이 아니라 **원장과의 어긋남**이다.

## 되먹임에 규칙 이름을 안 싣는다

돌려주는 것은 "무엇이 사실과 어긋났나" 뿐이고 "어느 관문에 걸렸나" 는 아니다.
알려 주면 관문을 통과하는 문장이 나오지 맞는 문장이 나오지 않는다
(`law/write.py` 와 같은 규율). `tests/test_coin_loop.py` 가 그 자리를 붙든다.

## 끝내 hard 가 안 없어지면

**미검증으로 끝낸다.** 제일 나은 답을 그래도 내보내지 않는다 -- 그것이 이 저장소가
다섯 번 앓은 병이다(검사 안 한 초록불). 대신 무엇이 어긋났는지를 사람에게 준다.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coin import gate as GT                                           # noqa: E402
from coin import ledger as LG                                         # noqa: E402
from coin import prompt as PM                                         # noqa: E402


@dataclass
class 바퀴:
    번호: int
    답: str
    점수: tuple
    hard: int
    soft: int
    인용: list = field(default_factory=list)
    되먹임: str = ""


@dataclass
class 결말:
    답: str
    통과: bool
    바퀴들: list = field(default_factory=list)
    위반들: list = field(default_factory=list)
    왜: str = ""

    @property
    def 돈바퀴(self):
        return len(self.바퀴들)


def 돌리기(물음: str, 원장: dict, 부르기, 사건들: list = None, 계열들: dict = None,
          시나리오: list = None, 바퀴수: int = 4, 유형들=None,
          장세: dict = None, 흐름: dict = None, 훑음: dict = None) -> 결말:
    되먹임, 후보, 앞점수 = "", [], None
    for i in range(1, 바퀴수 + 1):
        p = PM.짓기(물음, 원장, 사건들, 되먹임, 유형들, 시나리오, 장세, 흐름, 훑음)
        try:
            답 = 부르기(p)
        except Exception as e:                                        # noqa: BLE001
            return 결말("", False, 후보, [], f"모델을 못 불렀다: {type(e).__name__}: {e}")
        res = GT.검사(답, 원장, 계열들, 장세=장세, 흐름=흐름)
        점 = GT.점수(res, 답)
        되먹임 = GT.되먹임(res)
        후보.append((점, 바퀴(i, 답, 점, len(res.hard), len(res.soft), res.인용, 되먹임), res))
        if not res.hard and not res.soft:
            break
        if not res.hard and 앞점수 is not None and 점 >= 앞점수:
            break                                     # 두 바퀴째 안 나아진다
        앞점수 = 점
    if not 후보:
        return 결말("", False, [], [], "한 바퀴도 못 돌았다")
    후보.sort(key=lambda t: t[0])
    점, b, res = 후보[0]
    바퀴들 = [x[1] for x in sorted(후보, key=lambda t: t[1].번호)]
    if res.hard:
        return 결말("", False, 바퀴들, res.위반들,
                    f"{len(바퀴들)}바퀴를 돌았는데 어긋난 자리가 {len(res.hard)}개 남았다 "
                    "-- 내보내지 않는다")
    return 결말(b.답, True, 바퀴들, res.위반들)


def 적기(끝: 결말) -> str:
    줄 = []
    for b in 끝.바퀴들:
        줄.append(f"  {b.번호}바퀴  hard {b.hard} · soft {b.soft} · "
                  f"짚은 잰것 {len(b.인용)} · {len(b.답)}자")
    if 끝.통과:
        줄.append(f"  -> {끝.돈바퀴}바퀴에서 hard 0. 내보낸다")
    else:
        줄.append(f"  -> {끝.왜}")
        for v in 끝.위반들:
            if v.급 == "hard":
                줄.append(f"     {v}")
    return "\n".join(줄)
