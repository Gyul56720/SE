"""Gemini 를 직접 부른다 -- langchain 을 걷어낸 자리.

`llm_pool.py` 613줄 중 langchain 을 쓰던 것은 세 줄이었고, 그마저 재시도 기본값을
꺼야 했다("후보 풀 자체가 재시도 전략이므로 한 후보 안에서 오래 버틸 이유가 없다").
모델 목록 조회는 이미 requests 로 직접 부르고 있었으니, 같은 API 를 한쪽은 직접
한쪽은 래퍼를 거쳐 부르던 셈이다.

여기서 고정하는 계약:

  · **에러의 str() 이 계약이다** -- 풀의 분류가 그것을 읽는다. 상태 코드 · 상태 이름 ·
    응답 본문이 그대로 실려야 retryDelay 같은 것이 분류에 닿는다
  · **한 후보 안에서 안 버틴다** -- 응답이 왔으면 풀이 판단한다. 연결이 안 된 것만 다시
  · **빈 응답은 성공이 아니다** -- 안전 필터에 걸리면 200 인데 글이 없다. 빈 글을
    돌려주면 풀이 성공으로 세고 원고에 빈 덩어리가 들어간다
  · **키가 로그에 안 샌다**
  · **되돌릴 수 있다** -- GEMINI_CLIENT=langchain

**진짜 API 는 여기서 못 시험한다**(키도 없고 망도 막혀 있다). 전송을 가짜로 끼워
호출 경로만 본다 -- VM 에서 한 번 진짜로 불러 봐야 한다.

실행: python3 tests/test_gemini_http.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "orchestrator"))

import gemini_http as G                                               # noqa: E402
import llm_pool as P                                                  # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


class _Resp:
    def __init__(self, code, payload):
        self.status_code, self._p = code, payload
        self.text = json.dumps(payload)

    def json(self):
        return self._p


class _Fake:
    """requests 자리에 끼우는 가짜. 무엇이 나갔는지도 적어 둔다."""

    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def post(self, url, params=None, json=None, timeout=None):
        self.calls.append({"url": url, "params": params, "body": json, "timeout": timeout})
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def run(client, *replies):
    fake = _Fake(*replies)
    real = sys.modules.get("requests")
    sys.modules["requests"] = fake
    try:
        return client.invoke("프롬프트"), fake
    finally:
        if real is not None:
            sys.modules["requests"] = real
        else:
            sys.modules.pop("requests", None)


OKAY = _Resp(200, {"candidates": [{"content": {"parts": [{"text": "산문이다."}]}}]})

print("[성공] **응답에서 글자만 뽑는다**")
c = G.Client("gemini-3.5-flash", "KEY", timeout=12, max_output_tokens=99)
rep, fake = run(c, OKAY)
ok(rep.content == "산문이다.", f"글자를 뽑는다 ({rep.content!r})")
ok(hasattr(rep, "content"), "`.content` 로 읽는다  ← llm_pool._extract_text 가 그렇게 본다")
ok(P._extract_text(rep) == "산문이다.", "풀의 껍질 벗기기가 그대로 먹는다")
call = fake.calls[0]
ok(call["params"] == {"key": "KEY"}, "키는 쿼리로 간다")
ok(call["timeout"] == 12, "시간 제한이 실린다  ← langchain 기본값에는 없어서 매달렸다")
ok(call["body"]["generationConfig"]["maxOutputTokens"] == 99, "출력 상한이 실린다")
ok(call["body"]["contents"][0]["parts"][0]["text"] == "프롬프트", "프롬프트가 실린다")
ok("gemini-3.5-flash" in call["url"], "모델이 URL 에 실린다")

print()
print("[에러 문자열이 계약이다] **풀의 분류가 이것을 읽는다**")
print("      ← 상태 코드·이름·본문이 그대로 실려야 retryDelay 가 분류에 닿는다.")
cases = [
    (429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
                     "details": [{"retryDelay": "27s"}]}},
     "쿼터", lambda e: P._is_quota(e) and P._is_rpm(e) and P._retry_delay(e) == 27.0),
    (429, {"error": {"status": "RESOURCE_EXHAUSTED",
                     "message": "GenerateRequestsPerMinutePerProjectPerModel"}},
     "분당 한도", lambda e: P._is_rpm(e)),
    (503, {"error": {"code": 503, "status": "UNAVAILABLE"}},
     "일시장애", lambda e: not P._is_quota(e) and not P._is_permanent(e)),
    (404, {"error": {"status": "NOT_FOUND"}}, "영구", P._is_permanent),
    (403, {"error": {"status": "PERMISSION_DENIED"}}, "영구", P._is_permanent),
]
for code, payload, label, check in cases:
    died = None
    try:
        run(G.Client("m", "K"), _Resp(code, payload))
    except G.GeminiError as e:
        died = e
    ok(died is not None and check(died), f"{code} → {label} 로 분류된다")
    if died:
        ok(str(died).startswith(f"{code} "), f"  str() 이 코드로 시작한다 ({str(died)[:34]}…)")

print()
print("[빈 응답] **200 인데 글이 없으면 성공이 아니다**")
print("      ← 안전 필터에 걸리거나 토큰을 다 쓰면 이렇게 온다. 빈 글을 돌려주면")
print("        풀이 성공으로 세고 원고에 빈 덩어리가 들어간다.")
for payload, why in (({"candidates": []}, "candidates 가 비었다"),
                     ({"candidates": [{"content": {"parts": []}}]}, "parts 가 비었다"),
                     ({"candidates": [{"content": {"parts": [{"text": "  "}]}},
                       ], "promptFeedback": {"blockReason": "SAFETY"}}, "공백뿐이다")):
    died = None
    try:
        run(G.Client("m", "K"), _Resp(200, payload))
    except G.GeminiError as e:
        died = e
    ok(died is not None, f"{why} → 던진다")
    ok(died is None or "EMPTY" in str(died), "  EMPTY 라고 밝힌다")

print()
print("[한 후보 안에서 안 버틴다] **응답이 왔으면 풀이 판단한다**")
died = None
try:
    run(G.Client("m", "K", attempts=3), _Resp(429, {"error": {"status": "RESOURCE_EXHAUSTED"}}), OKAY)
except G.GeminiError as e:
    died = e
ok(died is not None, "429 를 받으면 다시 안 던지고 그대로 올린다  ← 풀이 다음 후보로 간다")

fake = _Fake(OSError("연결 끊김"), OKAY)
real = sys.modules.get("requests")
sys.modules["requests"] = fake
try:
    rep = G.Client("m", "K", attempts=2).invoke("p")
finally:
    sys.modules["requests"] = real if real is not None else sys.modules.pop("requests", None)
ok(rep.content == "산문이다." and len(fake.calls) == 2,
   "연결이 안 된 것만 다시 해 본다  ← 다음 후보로 넘어가는 것보다 싸다")

died = None
try:
    run(G.Client("m", "K", attempts=1), OSError("끊김"))
except G.GeminiError as e:
    died = e
ok(died is not None and "DEADLINE" in str(died),
   "끝내 연결이 안 되면 504 로 올린다  ← 풀이 아는 말이다")

print()
print("[비밀] **키가 로그에 안 샌다**")
c = G.Client("gemini-3.5-flash", "AIza-진짜키처럼-생긴-것")
ok("AIza" not in repr(c), f"repr 에 안 나온다 ({c!r})")
ok("AIza" not in str(c), "str 에도 안 나온다")

print()
print("[되돌리기] **GEMINI_CLIENT=langchain 이면 예전 경로**")
ok(P.CLIENT in ("direct", "langchain"), f"스위치가 있다 (지금 {P.CLIENT})")
ok(hasattr(P, "_langchain_factory"), "예전 팩토리가 남아 있다")
ok(type(P._default_factory("m", "K")).__name__ == "Client",
   "기본은 직접 부르기다")

print()
if fails:
    print(f"직접 호출: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("직접 호출: 성공 · 에러 계약 · 빈 응답 · 재시도 · 비밀 · 되돌리기 -- 통과")
