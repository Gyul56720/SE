"""shellmemo -- **같은 나무에 같은 명령은 두 번 돌리지 않는다.** 표준 라이브러리만 쓴다.

사용자(2026-09-12): "구조가 좋으면 모델의 성능을 이길 수 있다." 실측: 조사 c5cc1ef8 이 열한 바퀴 중
열 바퀴를 같은 명령(검사 실행 · gatekeeper)으로 돌았다. 코드가 `되풀이` 를 열 번 세었지만 막지는 않았다.
나무가 안 바뀌면 답도 안 바뀐다 -- 그것을 모델이 기억할 필요가 없다. 부르는 쪽이 (명령, 나무 지문) 을
적어 두고 같은 것이 오면 **돌리지 않고** 그때 답을 돌려준다.

왜 별도 모듈인가: bot_tools 는 langchain 이 있어야 임포트된다. 이 규칙은 그것과 무관하고 검사에서
임포트돼야 한다(agent_context 를 뗀 것과 같은 까닭).

쓰는 쪽: bot_tools.run_shell(돌리기 전에 묻고, 돌린 뒤 적는다) · investigate.run(조사 동안 켜고 끈다).
"""
from __future__ import annotations

import hashlib
import subprocess
import threading
from pathlib import Path

_판들: dict[str, dict] = {}       # 작성자(thread_id) -> {"본것": {(명령, 지문): (끝값, 출력머리)}, "막음": [...], "돌린것": [(명령, 끝값)]}
_lock = threading.Lock()
출력머리길이 = 600


def 켜기(작성자: str) -> None:
    with _lock:
        _판들[작성자] = {"본것": {}, "막음": [], "돌린것": []}


def 끄기(작성자: str) -> "dict | None":
    with _lock:
        return _판들.pop(작성자, None)


def 켜졌나(작성자: str) -> bool:
    with _lock:
        return 작성자 in _판들


def 보기(작성자: str) -> "dict | None":
    """{막음: [명령...], 돌린것: [(명령, 끝값)...]} 의 사본. 안 켜졌으면 None."""
    with _lock:
        d = _판들.get(작성자)
        return None if d is None else {"막음": list(d["막음"]), "돌린것": list(d["돌린것"])}


def 나무지문(판) -> str:
    """작업 트리의 지문 -- HEAD · 추적 파일의 diff 통계 · 미추적 목록. 같으면 같은 나무다."""
    조각 = []
    for argv in (["rev-parse", "HEAD"], ["diff", "HEAD", "--stat"], ["status", "--porcelain", "--untracked-files=all"]):
        try:
            r = subprocess.run(["git", "-C", str(판), *argv], capture_output=True, text=True, timeout=30)
            조각.append(r.stdout)
        except (OSError, subprocess.SubprocessError):
            조각.append("?")
    return hashlib.sha1("\n".join(조각).encode("utf-8", "replace")).hexdigest()[:12]


def 이미돌렸나(작성자: str, 명령: str, 지문: str) -> "tuple[int, str] | None":
    """같은 나무에서 같은 명령을 돌린 적 있으면 (끝값, 출력머리). 없으면 None. 있으면 막은 것으로 센다."""
    with _lock:
        d = _판들.get(작성자)
        if d is None:
            return None
        전 = d["본것"].get((명령.strip(), 지문))
        if 전 is not None:
            d["막음"].append(명령[:160])
        return 전


def 적기(작성자: str, 명령: str, 지문: str, 끝값: int, 출력: str) -> None:
    with _lock:
        d = _판들.get(작성자)
        if d is None:
            return
        d["본것"][(명령.strip(), 지문)] = (끝값, (출력 or "")[:출력머리길이])
        d["돌린것"].append((명령[:160], 끝값))


def 막힘말(명령: str, 지문: str, 전: "tuple[int, str]") -> str:
    return (f"[중복 -- 돌리지 않았다] 이 명령은 **같은 나무**(지문 {지문})에서 이미 돌렸고 끝값 {전[0]} 이었다. "
            f"나무가 안 바뀌면 답도 안 바뀐다. 먼저 파일을 고치거나, 다른 것을 재는 명령을 해라.\n"
            f"그때 출력 머리:\n{전[1]}")
