"""**Gemini 를 부른다.** `orchestrator/llm_pool.py` 를 그대로 쓴다 -- 키 회전 · 쿼터 ·
429 복구 · 모델 명부가 이미 거기 있다.

    python3 coin/ask.py --프롬프트 파일.txt
    python3 coin/ask.py --탐침                  키가 사나

**Claude 로 대신하지 않는다.** 키가 없으면 사실대로 "못 돌린다" 고 답한다
(`CLAUDE.md` 의 소설 규칙과 같은 자리).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def 풀():
    from orchestrator import llm_pool as LP
    keys = LP.api_keys()
    if not keys:
        raise RuntimeError(
            "GEMINI_API_KEY 가 없다. 이 파이프라인은 Gemini 로 돈다 -- "
            "키 없이 Claude 로 대신하지 않는다")
    return LP.build_pool(keys)


def 부르기(프롬프트: str, pool=None, pool_id: str = "coin") -> str:
    from orchestrator import llm_pool as LP
    p = pool if pool is not None else 풀()
    got = LP.call(p, 프롬프트, pool_id=pool_id)
    if isinstance(got, tuple):
        got = got[0]
    return got if isinstance(got, str) else getattr(got, "content", str(got))


def 부르는것(pool=None):
    """`loop.py` 에 넘길 호출자 하나. 검사에서는 가짜를 넣는다."""
    p = pool if pool is not None else 풀()
    return lambda 프롬프트: 부르기(프롬프트, p)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--프롬프트", default="")
    ap.add_argument("--탐침", action="store_true")
    a = ap.parse_args(argv)
    if a.탐침:
        try:
            p = 풀()
        except Exception as e:                                        # noqa: BLE001
            print(f"못 돌린다: {e}", file=sys.stderr)
            return 3
        print(f"후보 {len(p)}개")
        return 0
    if not a.프롬프트:
        ap.print_help()
        return 0
    글 = Path(a.프롬프트).read_text(encoding="utf-8") if Path(a.프롬프트).exists() else a.프롬프트
    try:
        print(부르기(글))
    except Exception as e:                                            # noqa: BLE001
        print(f"못 돌린다: {type(e).__name__}: {e}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
