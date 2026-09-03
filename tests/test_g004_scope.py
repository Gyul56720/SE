"""G004 의 적용 범위를 고정한다 -- 좁힌 결정이 조용히 되돌려지지 않게.

2026-09-03 에 _ECHO_SECRET(비밀값을 출력하는 코드)의 적용 범위를 셸/설정 파일로 좁혔다.
파이썬에서 token 은 LLM 단위를 뜻하는 표준 단어라 오탐만 셋 났고 참 양성은 없었던 반면,
이 게이트를 낳은 사고는 셸 스크립트였기 때문이다.

여기서 네 가지를 못 박는다. 특히 셋째가 이 좁힘의 전제다 -- 셸에서 여전히 잡히지 않으면
좁힌 게 아니라 껐다는 뜻이다.

실행: python3 tests/test_g004_scope.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import gatekeeper                                                     # noqa: E402
from gates import G004_secret_exposure as G004                        # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


def run(files: dict) -> list:
    """임시 저장소에 파일을 펼치고 G004 를 돌린다.

    **git init 을 해야 한다.** GateContext.tracked_files() 는 git ls-files 가 실패하면
    python_files() 로 물러서는데, 그러면 .sh 와 .yml 이 아예 읽히지 않는다. 그걸 모르고
    "셸에서 안 잡힌다" 는 결론을 낼 뻔했다(실측 2026-09-03) -- 게이트가 아니라 이 하네스가
    셸 파일을 안 보고 있었다."""
    import subprocess
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        for name, body in files.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(body, encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True,
                       capture_output=True)
        return G004.check(gatekeeper.GateContext(root))


print("[범위] 파이썬의 token 은 LLM 단위다 -- 잡지 않는다")
v = run({"a.py": 'print(f"입력 {approx_tokens(text)} 토큰")\n'})
ok(not v, f"approx_tokens 를 print 해도 통과 ({v})")
v = run({"b.py": 'print(f"캐시 {resp.usage.cache_creation_input_tokens}")\n'})
ok(not v, f"cache_creation_input_tokens 도 통과 ({v})")
v = run({"c.py": 'for name in ("DISCORD_BOT_TOKEN",):\n    print(f"{name} 설정됨")\n'})
ok(not v, f"이름을 라벨로 찍는 것도 통과 ({v})")

print("[범위] 셸에서는 그대로 잡는다  ← 이게 성립해야 '좁힘'이지 '끔'이 아니다")
v = run({"run.sh": 'echo "토큰을 발견했습니다: $TOKEN"\n'})
ok(any("비밀값을 출력한다" in x for x in v), f"echo $TOKEN 은 위반 ({v})")
v = run({"deploy.yml": 'run: echo "key=${API_KEY}"\n'})
ok(any("비밀값을 출력한다" in x for x in v), f"워크플로의 echo 도 위반 ({v})")

print("[불변] 자격증명이 커밋되는 것은 범위를 줄이지 않았다")
v = run({"conf.py": 'DISCORD_BOT_TOKEN = "MTA5ODc2NTQzMjEwOTg3NjU0Mzg7Yz9x"\n'})
ok(any("실제 자격증명으로 보이는 값" in x for x in v),
   f"파이썬 파일이어도 자격증명 문자열은 잡는다 ({v})")
v = run({".env.example": "DISCORD_BOT_TOKEN=your_token_here\n"})
ok(not v, f"자리표시자는 통과 ({v})")

print("[불변] 저장소를 훑어 자격증명을 캐는 패턴도 그대로")
# 어간을 쪼개 둔다. 그대로 적으면 G004 의 _HARVEST 가 **이 파일 자신을** 수집 패턴으로
# 잡는다(실측). 게이트를 시험하는 파일이 게이트에 걸리는 건 흔한 자충수다.
STEM = "TOK" + "EN"
v = run({"harvest.sh": f"grep -r . | grep {STEM}\n"})
ok(any("자격증명을 수집하는 패턴" in x for x in v), f"grep -r + TOKEN 은 위반 ({v})")

print()
if fails:
    print(f"G004 범위: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("G004 범위: 파이썬 오탐 없음 · 셸에서는 그대로 · 커밋 차단은 불변 -- 통과")
