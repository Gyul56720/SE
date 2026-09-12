"""probes -- **탐침 묶음을 한꺼번에 돌린다.** 표준 라이브러리만 쓴다.

사용자(2026-09-12): "구조가 좋으면 모델의 성능을 이길 수 있다." 여덟 알고리즘 중 5번.
약한 모델의 천장은 **한 호출당 추론 깊이**다. 깊이는 못 올리지만 **한 호출당 폭**은 올릴 수 있다 --
모델의 일을 "무엇 다섯 개를 볼까" 로 줄이고, 보는 것은 코드가 나란히 한다. 한 바퀴에 명령 하나씩
돌리던 것(실측: 열 바퀴 = 열 명령)이 한 바퀴에 표 하나가 된다.

  결과는 명령마다 (끝값, 걸린초, 출력 꼬리) 인 표다. 판단은 여기 없다 -- 부르는 쪽(두뇌)이 표를 읽는다.
  같은 나무에 같은 명령을 두 번 돌리지 않는 규칙(shellmemo)은 run_shell 이 적용한다; 여기는 묶음마다
  중복만 걸러 한 번씩 돌린다.

쓰는 쪽: bot_tools.run_probes(조사 두뇌의 도구) · 검사.
"""
from __future__ import annotations

import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

기본초 = 120
기본동시 = 6
최대명령 = 12
꼬리줄 = 12


def _하나(명령: str, cwd: Path, 초: int, env: "dict | None") -> dict:
    시작 = time.monotonic()
    try:
        p = subprocess.run(["bash", "-lc", 명령], cwd=str(cwd), capture_output=True, text=True,
                           errors="replace", timeout=초, env=env)
        본 = (p.stdout or "") + (("\n" + p.stderr) if (p.stderr or "").strip() else "")
        return {"명령": 명령, "끝값": p.returncode, "걸린초": round(time.monotonic() - 시작, 1),
                "꼬리": "\n".join(본.strip().splitlines()[-꼬리줄:])}
    except subprocess.TimeoutExpired:
        return {"명령": 명령, "끝값": 124, "걸린초": round(time.monotonic() - 시작, 1), "꼬리": f"{초}초 안에 안 끝났다"}
    except OSError as e:
        return {"명령": 명령, "끝값": 127, "걸린초": round(time.monotonic() - 시작, 1), "꼬리": f"{type(e).__name__}: {e}"}


def 묶음(명령들: "list[str]", cwd=None, 초: int = 기본초, 동시: int = 기본동시, env: "dict | None" = None) -> "list[dict]":
    """명령들을 나란히 돌려 표로. 차례는 준 차례 그대로. 빈 줄·중복은 뺀다. 최대명령을 넘으면 앞 것만."""
    본: list[str] = []
    for c in 명령들 or []:
        c = (c or "").strip()
        if c and c not in 본:
            본.append(c)
    본 = 본[:최대명령]
    if not 본:
        return []
    cwd = Path(cwd or ".")
    with ThreadPoolExecutor(max_workers=max(1, min(동시, len(본)))) as ex:
        return list(ex.map(lambda c: _하나(c, cwd, 초, env), 본))


def 표(결과: "list[dict]") -> str:
    """사람과 두뇌가 읽는 꼴. 빨강이 위로."""
    if not 결과:
        return "(돌린 명령이 없다)"
    줄 = [f"탐침 {len(결과)}개 · 빨강 {sum(1 for r in 결과 if r['끝값'])}개"]
    for r in sorted(결과, key=lambda r: (r["끝값"] == 0, r["명령"])):
        줄.append(f"[exit={r['끝값']} · {r['걸린초']}s] {r['명령'][:120]}")
        줄 += [f"    {x[:200]}" for x in r["꼬리"].splitlines()[-6:]]
    return "\n".join(줄)
