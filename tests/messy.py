"""**진짜 모델처럼 지저분하게 답하는 껍데기.** 검사의 가짜 LLM 을 여기로 감싼다.

## 왜 있나

2026-09-07 하루에 같은 모양의 사고가 셋 났다. 셋 다 코드가 아니라 **검사가 서 있는
자리** 때문이었다.

    gemini_http 임포트   검사가 sys.path 에 두 경로를 다 넣어 뒀다 -- 진짜 호출자는
                         하나만 연다
    JSON 쪼개짐          검사의 가짜 추출기가 **한 덩이로만** 답했다 -- 진짜 gemma 는
                         `{"people":...} {"places":...}` 로 쪼개서 낸다. 그래서 추출이
                         **한 번도 성공 못 하는** 채로 원고가 0자였다
    500/503              애초에 검사가 없었다

가짜 LLM 이 얌전하면 검사는 얌전한 세상만 확인한다. 진짜 모델은 얌전하지 않다.

## 규칙 -- 지어내지 않는다

**여기 있는 꼴은 전부 실제로 본 것이다.** 각 항목에 어디서 봤는지 적는다. "이럴 수도
있겠다" 는 넣지 않는다 -- 안 나는 실패를 막느라 코드를 비틀면 그 비틈이 다음 사고다.

새 꼴을 넣으려면 **로그 한 줄을 같이 붙여라.**

## 쓰는 법

    from messy import dirty, SHAPES

    class Fake:
        def __call__(self, prompt):
            return dirty(json.dumps({"people": {}}), self.n)   # n 마다 다른 꼴

`dirty` 는 **정해진 순서로** 돌아간다 -- 무작위가 아니다. 검사가 실패하면 같은 자리에서
같은 꼴로 다시 실패해야 고칠 수 있다.
"""
from __future__ import annotations

# ---------------------------------------------------------------- JSON 을 더럽히는 꼴
#
# (이름, 함수, 어디서 봤나)

def _plain(s: str) -> str:
    return s


def _fenced(s: str) -> str:
    return f"```json\n{s}\n```"


def _preamble(s: str) -> str:
    return f"네, 요청하신 JSON 입니다:\n\n{s}"


def _postamble(s: str) -> str:
    return f"{s}\n\n도움이 되셨길 바랍니다."


def _split_one_line(s: str) -> str:
    """**객체를 쪼개서 한 줄에.** 오늘 원고를 0자로 만든 그 꼴이다.

    실측 2026-09-07 VM (gemma-4-31b-it):
        JSONDecodeError: Extra data: line 1 column 30 (char 29)
    """
    if not s.startswith("{") or len(s) < 4:
        return s
    return _split(s, sep=" ")


def _split_lines(s: str) -> str:
    """같은 것을 줄바꿈으로. NDJSON 처럼 온다."""
    if not s.startswith("{") or len(s) < 4:
        return s
    return _split(s, sep="\n")


def _split(s: str, sep: str) -> str:
    """최상위 키를 둘로 갈라 객체 두 개로 만든다. 키가 하나뿐이면 그대로 둔다."""
    import json
    try:
        d = json.loads(s)
    except Exception:
        return s
    if not isinstance(d, dict) or len(d) < 2:
        return s
    ks = list(d)
    half = len(ks) // 2
    a = {k: d[k] for k in ks[:half]}
    b = {k: d[k] for k in ks[half:]}
    return json.dumps(a, ensure_ascii=False) + sep + json.dumps(b, ensure_ascii=False)


def _trailing_comma(s: str) -> str:
    """마지막 쉼표를 남긴다. **이건 못 고친다** -- 파서가 죽는 것이 맞다.

    call_json 이 오류 문구를 되먹여 다시 묻는 길이 이것 때문에 있다."""
    return s.replace("}", ",}", 1) if "}" in s else s


def _smart_quotes(s: str) -> str:
    """따옴표를 둥근 것으로 바꾼다. 한국어 모델이 종종 그런다."""
    return s.replace('"', "”", 1)


SHAPES = (
    ("그대로", _plain, "얌전할 때도 있다 -- 이것이 기준선이다"),
    ("코드펜스", _fenced, "흔하다. drive._json 이 예전부터 벗긴다"),
    ("앞에 잡소리", _preamble, "흔하다. drive._json 이 예전부터 벗긴다"),
    ("뒤에 잡소리", _postamble, "흔하다"),
    ("객체를 쪼갬(한 줄)", _split_one_line,
     "실측 2026-09-07 VM gemma-4-31b-it: Extra data: line 1 column 30"),
    ("객체를 쪼갬(여러 줄)", _split_lines,
     "위와 같은 뿌리. 줄바꿈으로 오는 경우"),
)

# **파서가 죽는 것이 맞는 꼴.** 살려내려 하면 안 된다 -- 무엇이 왔는지 모르는 채로
# 원장에 넣는 것보다 사실대로 죽고 다시 묻는 편이 낫다(call_json 이 그 길이다).
BROKEN = (
    ("끝 쉼표", _trailing_comma,
     "실측 2026-09-03: 값 안의 따옴표를 안 escape 한 것과 같은 부류. 그날 밤샘 런이"
     " 여기서 통째로 날아갔다 -- 재시도가 없어서 15화가 버려졌다"),
    ("둥근 따옴표", _smart_quotes, "한국어 모델이 종종 그런다"),
)


def dirty(clean: str, n: int = 0) -> str:
    """`clean` 을 n 번째 꼴로 더럽힌다. **무작위가 아니다** -- 검사가 실패하면 같은
    자리에서 같은 꼴로 다시 실패해야 고칠 수 있다."""
    return SHAPES[n % len(SHAPES)][1](clean)


def every(clean: str):
    """살아남아야 하는 꼴 전부. `for name, txt, why in every(...)`."""
    for name, fn, why in SHAPES:
        yield name, fn(clean), why


def every_broken(clean: str):
    """**죽는 것이 맞는** 꼴 전부."""
    for name, fn, why in BROKEN:
        yield name, fn(clean), why
