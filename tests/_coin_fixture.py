"""coin 검사들이 같이 쓰는 **가짜 시장.** 망도 LLM 도 안 쓴다.

신호를 **심어 놓고** 파이프라인이 그것을 찾는지(GREEN), 안 심으면 안 찾는지(RED)를
본다. `law/mutate.py` 가 조문 낱말을 일부러 틀리게 심는 것과 같은 자리다 --
**어긋남 0 은 관문이 좋아서일 수도 있고 아무것도 못 잡아서일 수도 있다.**
"""
from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coin import price as PR                                          # noqa: E402

시작 = datetime(2018, 1, 1, tzinfo=timezone.utc)


def 날짜(i: int) -> str:
    return (시작 + timedelta(days=i)).strftime("%Y-%m-%d")


def 사건날(첫: int = 60, 끝: int = 1500, 걸음: int = 35) -> list:
    return [날짜(i) for i in range(첫, 끝, 걸음)]


def 계열(씨: int = 11, 심을날: list = None, 효과: float = 0.0, 날수: int = 1600,
        퍼짐: int = 3):
    """`효과` 를 사건 다음날부터 `퍼짐`일에 걸쳐 나눠 심는다."""
    R = random.Random(씨)
    px, 봉 = 100.0, []
    자리 = {(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc) - 시작).days
            for d in (심을날 or [])}
    for i in range(날수):
        더 = (효과 / 퍼짐) if any((i - k) in range(1, 퍼짐 + 1) for k in 자리) else 0.0
        px *= (1 + R.gauss(0.002, 0.03) + 더)
        봉.append([날짜(i), px, px, px, px, 1000 + R.random() * 500])
    return PR.계열({"자산": "BTC", "봉": 봉})


def 사건(날들: list, 유형: str = "규제금지", 자산: str = "BTC", 나라=("CN", "US"),
        때: str = "T09:00:00+00:00") -> list:
    return [{"유형": 유형, "자산": 자산, "최초": d + 때, "주류": d + 때,
             "주국": 나라[0], "나라들": list(나라), "나라수": len(나라), "글수": 3,
             "출처들": ["pboc", "coindesk"], "지연": 0.0,
             "본보기": f"{유형} 본보기"} for d in 날들]
