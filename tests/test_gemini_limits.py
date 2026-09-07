"""한도 탐침 -- **응답을 읽는 부분만** 잰다. 네트워크는 안 탄다.

이 도구가 하는 일은 하나다: Gemini 가 한 번에 낼 수 있는 양을 **물어봐서** 우리가
쓰는 값과 견주는 것. 지금까지 그 답을 받아 놓고 버리고 있었다
(`bot_tools.list_available_models()` 가 이름만 꺼낸다).

실행: python3 tests/test_gemini_limits.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "gemini_limits", ROOT / "scripts" / "gemini_limits.py")
GL = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(GL)

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


RESP = {"models": [
    {"name": "models/gemini-3.5-flash", "inputTokenLimit": 1048576,
     "outputTokenLimit": 65536, "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-3.5-flash-lite", "inputTokenLimit": 1048576,
     "outputTokenLimit": 8192, "supportedGenerationMethods": ["generateContent"]},
    # 생성용이 아니다 -- 걸러야 한다
    {"name": "models/text-embedding-004", "inputTokenLimit": 2048,
     "outputTokenLimit": 1, "supportedGenerationMethods": ["embedContent"]},
    # 이름으로 걸러지는 것 (채팅용이 아니다)
    {"name": "models/imagen-4.0", "inputTokenLimit": 480, "outputTokenLimit": 0,
     "supportedGenerationMethods": ["generateContent"]},
    # 한도가 안 실려 온 것 -- 0 으로 두고 지어내지 않는다
    {"name": "models/gemini-3.1-flash", "supportedGenerationMethods":
        ["generateContent"]},
]}

print("[읽기] **한도를 버리지 않는다** -- 이게 이 도구의 전부다")
rows = GL.parse(RESP)
names = [r["name"] for r in rows]
ok("gemini-3.5-flash" in names, f"생성용 모델이 남는다 ({names})")
ok("text-embedding-004" not in names,
   "generateContent 를 안 하는 것은 뺀다")
ok("imagen-4.0" not in names, "채팅용이 아닌 것은 이름으로도 뺀다")
big = [r for r in rows if r["name"] == "gemini-3.5-flash"][0]
ok(big["out"] == 65536, f"출력 한도를 들고 온다 ({big['out']:,})")
ok(big["in"] == 1048576, f"입력 한도도 들고 온다 ({big['in']:,})")

print()
print("[모름] **안 실려 온 것을 지어내지 않는다**")
none = [r for r in rows if r["name"] == "gemini-3.1-flash"][0]
ok(none["out"] == 0 and none["in"] == 0,
   f"한도가 없으면 0 이다 ({none})  ← 8192 같은 기본값을 끼워 넣으면 그게 또 짐작이다")

print()
print("[견주기] **모델 한도와 우리가 보내는 상한은 다른 숫자다**")
print("      ← GEMINI_MAX_OUTPUT 은 요청에 우리가 적어 보내는 값이지 모델의 한도가")
print("        아니다. 한도가 더 크면 그 차이만큼을 매 호출에서 스스로 버린다.")
best = max(rows, key=lambda r: r["out"])
ok(best["name"] == "gemini-3.5-flash", f"제일 큰 것을 고른다 ({best['name']})")
ok(best["out"] > 8192,
   f"이 표본에서는 우리 상한보다 크다 ({best['out']:,} > 8,192)")

print()
print("[표본] **원고가 없으면 없다고 한다** -- 지어낸 글로 자/토큰을 재지 않는다")
ok(GL.sample(str(ROOT / "novel" / "없는파일.json")) == "",
   "없는 원고는 빈 문자열")
ok(GL.sample(str(ROOT / "requirements.txt")) == "",
   "원고 꼴이 아니면 빈 문자열  ← JSON 이 아니어도 죽지 않는다")

print()
if fails:
    print(f"한도 탐침: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("한도 탐침: 읽기 · 거르기 · 모름 · 견주기 · 표본 -- 통과")
