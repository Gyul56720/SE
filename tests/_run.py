# -*- coding: utf-8 -*-
"""pytest 꼴로 쓴 검사 파일을 **스크립트로도 돌게** 한다.

## 왜 있나 -- 실측 2026-09-19

이 저장소의 관문은 `scripts/tests.sh` 와 `scripts/precheck.sh` 둘 다
**`python3 tests/test_*.py`** 로 검사를 돌린다.  대부분의 검사 파일은 모듈 수준에서
재고 `sys.exit(1)` 로 끝나므로 그렇게 돌아간다.

그런데 **`def test_...()` 만 있고 `__main__` 이 없는 파일 열 개**는 그렇게 돌리면
임포트만 하고 끝난다 -- 0.14 초에 종료 코드 0.  관문은 그것을 `OK` 로 찍는다.
실측: `tests/test_rs.py` · `tests/test_gf.py` · `tests/test_verif_agent.py` 가
전부 그랬다.  합쳐서 검사 함수 여든 개 남짓이 **관문에서 한 번도 돈 적이 없다.**

    검사하지 않은 초록불이 검사한 빨간불보다 나쁘다

그래서 한 줄로 고칠 수 있게 여기 runner 를 둔다.  검사 파일 맨 끝에:

    if __name__ == "__main__":
        import _run; _run.돌리기(globals())

`tests/test_검사가_도는가.py` 가 이 줄이 빠진 파일을 찾아 **실패로 낸다** --
사람이 기억할 것이 아니라 기계가 붙들 것이다.

## 무엇을 흉내 내나

pytest 전체가 아니다.  이 저장소가 실제로 쓰는 것만 한다:

    @pytest.mark.parametrize(...)   여러 개면 곱집합
    @pytest.mark.skipif(...)        함수별 · 모듈 수준(pytestmark)
    pytest.skip() / pytest.fail()   함수 안에서 부른 것
    fixture                         **안 한다** -- 인자가 parametrize 로 안 채워지면
                                    그 파일은 pytest 로 돌려야 한다고 말하고 실패한다

흉내가 모자란 것을 **조용히 건너뛰지 않는다**.  못 돌리면 못 돌린다고 말하고 1 을 낸다.
"""
import inspect
import itertools
import sys
import traceback


def _marks(fn):
    return list(getattr(fn, "pytestmark", []) or [])


def _skip이유(marks):
    """skipif / skip 마크를 보고 (건너뛸까, 이유) 를 돌려준다."""
    for m in marks:
        name = getattr(m, "name", "")
        if name == "skip":
            return True, (m.kwargs.get("reason") or "skip")
        if name == "skipif":
            조건 = m.args[0] if m.args else False
            if 조건:
                return True, (m.kwargs.get("reason") or "skipif")
    return False, ""


def _경우들(fn):
    """parametrize 마크를 펼쳐 [(이름, kwargs), ...] 를 낸다."""
    ps = [m for m in _marks(fn) if getattr(m, "name", "") == "parametrize"]
    if not ps:
        return [("", {})]
    축 = []
    for m in ps:
        이름들 = m.args[0]
        if isinstance(이름들, str):
            이름들 = [s.strip() for s in 이름들.split(",") if s.strip()]
        값들 = list(m.args[1])
        축.append((이름들, 값들))
    out = []
    for 조합 in itertools.product(*[값들 for _, 값들 in 축]):
        kw = {}
        표시 = []
        for (이름들, _), 값 in zip(축, 조합):
            if len(이름들) == 1:
                kw[이름들[0]] = 값
                표시.append(repr(값))
            else:
                for n, v in zip(이름들, 값):
                    kw[n] = v
                표시.append(",".join(repr(v) for v in 값))
        out.append(("[" + "-".join(표시)[:60] + "]", kw))
    return out


class _건너뜀(Exception):
    pass


def 돌리기(ns, 조용히=False):
    """ns(보통 globals()) 안의 test_* 를 전부 돌린다.  실패가 있으면 sys.exit(1)."""
    이름 = ns.get("__file__", "?").split("/")[-1]
    모듈마크 = ns.get("pytestmark") or []
    if not isinstance(모듈마크, (list, tuple)):
        모듈마크 = [모듈마크]
    건너뛸까, 이유 = _skip이유(list(모듈마크))
    if 건너뛸까:
        print(f"{이름}: 전부 건너뜀 -- {이유}")
        return 0

    함수들 = [(k, v) for k, v in sorted(ns.items())
              if k.startswith("test_") and inspect.isfunction(v)]
    if not 함수들:
        print(f"{이름}: test_ 함수가 없다 -- runner 를 왜 불렀나", file=sys.stderr)
        sys.exit(1)

    통과 = 실패 = 건너뜀 = 0
    빨강 = []
    for 이름2, fn in 함수들:
        f건너뛸까, f이유 = _skip이유(_marks(fn))
        if f건너뛸까:
            건너뜀 += 1
            continue
        받는인자 = set(inspect.signature(fn).parameters)
        for 표시, kw in _경우들(fn):
            남은 = 받는인자 - set(kw)
            if 남은:
                print(f"{이름}: {이름2}{표시} 가 fixture {sorted(남은)} 를 받는다 -- "
                      f"이 runner 는 fixture 를 흉내 내지 않는다. "
                      f"pytest 로 돌려야 한다.", file=sys.stderr)
                sys.exit(1)
            try:
                fn(**kw)
                통과 += 1
            except BaseException as e:      # noqa: BLE001 -- 전부 잡아 보고한다
                if type(e).__name__ in ("Skipped", "_건너뜀"):
                    건너뜀 += 1
                    continue
                실패 += 1
                빨강.append(f"{이름2}{표시}: {type(e).__name__}: {e}")
                if not 조용히:
                    print(f"  실패 {이름2}{표시}", file=sys.stderr)
                    traceback.print_exc(limit=6)

    꼬리 = f" · 건너뜀 {건너뜀}" if 건너뜀 else ""
    if 실패:
        print(f"{이름}: {통과} 통과 · **{실패} 실패**{꼬리}", file=sys.stderr)
        for l in 빨강[:10]:
            print("    " + l, file=sys.stderr)
        sys.exit(1)
    print(f"{이름}: {통과} 통과{꼬리}")
    return 0
