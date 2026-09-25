"""**워크스페이스 동적 시뮬 HTML 기능을 붙든다.** 실측 2026-09-25.

## 왜

사용자(2026-09-25): "Html이 이미지인데? 움직이지 않아." 봇이 낸 것은 정지 이미지였다 --
SendUserFile 이 렌더한 스냅숏이었고, 봇에는 **움직이는 HTML 을 만들어 파일로 올리는 도구가
없었다.** `bot_tools.simulate_inspection` 이 그 구멍을 메운다: 제어 정책을 실제로 돌린 궤적을
Three.js 인터랙티브 HTML 로 내고, 파일로 디스코드에 올린다(받아서 열면 애니메이션이 돈다).

## 무엇을 붙드나 -- 글자가 아니라 진짜 HTML 을 잰다

  1. 파이프라인이 실제로 돈다: inspect3d(제어 정책) -> 저장(json) -> viz(HTML).
  2. 나온 HTML 이 **동적**이다: three.js + requestAnimationFrame 애니메이션 루프 + 데이터
     임베드(자리표가 치워졌다). 정지 이미지가 아니다.
  3. 도구가 두 채널에 등록됐고, 파일을 `_그림남기기` 로 올린다(임포트가 아니라 소스로 확인 --
     이 컨테이너엔 langchain 이 없어 bot_tools 를 임포트 못 한다. test_회로그리기 와 같은 결).
  4. **G013 배선**: ctrl 을 임포트하니 ctrl/**.py 가 배포 paths 에 있어야 한다.
  5. 산출 HTML 은 .gitignore 라 커밋을 안 더럽힌다(§303 결).
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile

뿌리 = Path = pathlib.Path
루트 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(루트))
FAIL = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        FAIL.append(말)


print("== 1. 파이프라인이 실제로 돈다: 제어 정책 -> json -> 동적 HTML ==")
import ctrl.model.inspect3d as I   # noqa: E402
import ctrl.viz as V               # noqa: E402

임시 = pathlib.Path(tempfile.mkdtemp(prefix="시뮬검사-"))
j = str(임시 / "s.json")
h = str(임시 / "s.html")
r = I.추종(dt=0.05)                  # 가볍게(precheck 안)
I.저장(r, j)
V.만들기("검사3d", j, h)
html = pathlib.Path(h).read_text(encoding="utf-8")
ok(len(html) > 8000, f"HTML 이 실하게 나온다 ({len(html)} bytes)")

print("\n== 2. 나온 HTML 이 동적이다(정지 이미지가 아니다) ==")
ok("three.min.js" in html, "three.js 를 싣는다 -- 3D 렌더")
ok("requestAnimationFrame" in html, "**애니메이션 루프가 있다** -- 드론이 시간에 따라 난다")
ok("/*__DATA__*/null" not in html, "데이터 자리표가 실제 데이터로 치워졌다 -- 자체완결")
ok(all(k in html for k in ('"AC"', '"결함"', '"웨이포인트"', '"standoff"')),
   "궤적· 결함· 웨이포인트· 표면거리 데이터가 HTML 에 박혔다")
ok('id="play"' in html and 'id="scrub"' in html,
   "재생/일시정지· 타임 슬라이더가 있다 -- 사용자가 조작하는 동적 시뮬")
# 물리 규격이 지어낸 것이 아니라 시뮬이 낸 것인지: 지표가 HTML 데이터에 실려 있다
m = r["지표"]
ok(str(m["웨이포인트수"]) in html, "검증 지표가 시뮬 결과 그대로 실렸다(지어내지 않음)")

import shutil  # noqa: E402
shutil.rmtree(임시, ignore_errors=True)

print("\n== 2-b. 학습된 Mamba 정책이 검사 경로를 난다(손 PI 아님) ==")
# 도구가 실제로 쓰는 설정 그대로(추종_맘바 기본 iters=400, seed 7 로 결정적).
# **덜 학습하면(예: 200 iters) 표준거리 밴드를 못 지킨다** -- 이건 정직한 한계다:
# 모방정책의 정밀도는 학습량에 달렸다. 그래서 도구는 400 을 쓴다.
rm = I.추종_맘바()
mm = rm["지표"]
ok("Mamba" in rm["정책이름"] and "PI" not in rm["정책이름"],
   f"정책이름이 학습 Mamba 다 -- 손 PI 아님 ({rm['정책이름']})")
ok(mm["검출수"] == mm["결함수"], f"학습 정책도 결함 전부 검출 ({mm['검출수']}/{mm['결함수']})")
ok(mm["커버리지pct"] >= I.SPEC["커버리지목표pct"], f"커버리지 목표 달성 ({mm['커버리지pct']}%)")
ok(mm["검증"]["표준거리_밴드"],
   f"**학습 정책이 표준거리 밴드를 지킨다** ({mm['표준거리min_m']}~{mm['표준거리max_m']}m) "
   f"-- 촘촘한 경로로 스텝오차를 학습분포(±3) 안에 둔 덕. 성긴 경로면 벗어난다(실측 0.69~4.44)")
ok(mm["검증"]["속도_한계"], f"속도 한계도 지킨다 (max {mm['속도max_ms']}m/s)")

print("\n== 3. 도구가 두 채널에 등록되고 파일로 올린다(소스로 확인) ==")
도구원 = (루트 / "bot_tools.py").read_text(encoding="utf-8")
서버 = (루트 / "discord_bot_server.py").read_text(encoding="utf-8")
공개 = (루트 / "main_public.py").read_text(encoding="utf-8")
_함수 = 도구원.split("def simulate_inspection")[1].split("\n@tool")[0]
ok("_그림남기기(h)" in _함수, "**HTML 을 _그림남기기 로 올린다** -- 서버가 discord.File 로 붙인다")
ok("ctrl.model.inspect3d" in _함수 and "ctrl.viz" in _함수,
   "제어 정책 시뮬과 뷰를 실제로 부른다(빈 껍데기 아님)")
ok("추종_맘바" in _함수, "**정책=mamba 면 학습된 Mamba 를 태운다** -- 손 PI 만이 아니다")
ok("simulate_inspection" in 서버.split("ADMIN_TOOLS = [")[1].split("]")[0],
   "ADMIN_TOOLS 에 있다")
ok("simulate_inspection" in 공개.split("PUBLIC_TOOLS = [")[1].split("]")[0],
   "PUBLIC_TOOLS 에 있다")

print("\n== 4. G013 배선: ctrl 을 임포트하니 배포 paths 에 있어야 한다 ==")
_wf = (루트 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('"ctrl/**.py"' in _wf,
   "**ctrl/**.py 가 배포 트리거에 있다** -- 없으면 봇이 임포트에서 죽거나 옛 코드로 돈다")

print("\n== 5. 산출 HTML 은 .gitignore 라 커밋을 안 더럽힌다 ==")
_ci = subprocess.run(["git", "check-ignore", "inbox/시뮬/x.html"],
                     cwd=str(루트), capture_output=True, text=True)
ok(_ci.returncode == 0, "inbox/시뮬/ 이 gitignore 된다 -- 회당 45KB HTML 이 커밋에 안 쌓인다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    sys.exit(1)
print("시뮬 HTML: 파이프라인 실제로 돎 · HTML 동적 · 두 채널 등록 · G013 배선 · gitignore -- 통과")
