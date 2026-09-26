"""**편대(스웜) 위협회피 동적 시뮬 HTML 도구를 붙든다.** 실측 2026-09-26.

## 왜

사용자가 "디스코드에서 편대 시뮬을 보내달라" 고 했다. `simulate_inspection` 이 단일
드론 검사 3D 를 디스코드로 올리듯, `simulate_formation` 이 N대 편대의 전술 스택
(계획→MPC→편대수행)을 **움직이는 HTML** 로 내고 파일로 올린다. 정지 이미지가 아니다.

## 무엇을 붙드나 -- 글자가 아니라 진짜 HTML 을 잰다

  1. 파이프라인이 실제로 돈다: ctrl.model.tactical(계획→MPC→편대) -> ctrl.swarm_viz(HTML).
  2. 나온 HTML 이 **동적**이다: Canvas + requestAnimationFrame + 데이터 임베드(자리표가
     치워졌다). 재생/일시정지·스크럽 컨트롤이 있다. 정지 이미지가 아니다.
  3. 수치는 지어내지 않는다 -- tactical 이 낸 세 계획의 여유가 그대로 실린다. 중심만
     계획은 관통(음수), 폭+실행마진은 전원회피(양수) -- 이 정성 사실을 HTML·재현으로 확인.
  4. 도구가 두 채널(ADMIN/PUBLIC)에 등록됐고, 파일을 `_그림남기기` 로 올린다(임포트가
     아니라 소스로 확인 -- 이 컨테이너엔 langchain 이 없어 bot_tools 를 임포트 못 한다).
  5. G013 배선: ctrl 을 임포트하니 ctrl/**.py 가 배포 paths 에 있어야 한다.
  6. 산출 HTML 은 inbox/시뮬(.gitignore)라 커밋을 안 더럽힌다(§303 결).
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile

루트 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(루트))
FAIL = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        FAIL.append(말)


print("== 1. 파이프라인이 실제로 돈다: 계획->MPC->편대 -> 동적 HTML ==")
import ctrl.swarm_viz as SV          # noqa: E402
from ctrl.model import tactical as T  # noqa: E402

임시 = pathlib.Path(tempfile.mkdtemp(prefix="편대시뮬-"))
h = str(임시 / "f.html")
_, 요약 = SV.만들기(h)
html = pathlib.Path(h).read_text(encoding="utf-8")
ok(len(html) > 8000, f"HTML 이 실하게 나온다 ({len(html)} bytes)")

print("\n== 2. 나온 HTML 이 동적이다(정지 이미지가 아니다) ==")
ok("requestAnimationFrame" in html, "**애니메이션 루프가 있다** -- 편대가 시간에 따라 난다")
ok("/*__DATA__*/null" not in html, "데이터 자리표가 실제 데이터로 치워졌다 -- 자체완결")
ok(all(k in html for k in ('"traj"', '"threat"', '"center"', '"cases"')),
   "궤적·위협·중심경로·계획 데이터가 HTML 에 박혔다")
ok('id="play"' in html and 'id="scrub"' in html,
   "재생/일시정지·타임 슬라이더가 있다 -- 사용자가 조작하는 동적 시뮬")

print("\n== 3. 수치는 지어내지 않는다: 세 계획의 여유가 tactical 그대로 ==")
p = SV.페이로드()
중심만 = next(c for c in p["cases"] if c["name"] == "중심만")
폭마진 = next(c for c in p["cases"] if c["name"] == "폭+실행마진")
ok(중심만["clr"] < 0, f"중심만 계획은 바깥 드론이 관통한다 (여유 {중심만['clr']}m)")
ok(폭마진["clr"] > 0, f"폭+실행마진 계획은 전원 회피한다 (여유 +{폭마진['clr']}m)")
ok(str(폭마진["clr"]) in html, "그 여유 수치가 HTML 에 그대로 실렸다(지어내지 않음)")
ok(all(c["fe"] < 0.5 for c in p["cases"]), "편대는 대형을 유지한다(유지오차 유계)")

import shutil  # noqa: E402
shutil.rmtree(임시, ignore_errors=True)

print("\n== 4. 도구가 두 채널에 등록되고 파일로 올린다(소스로 확인) ==")
도구원 = (루트 / "bot_tools.py").read_text(encoding="utf-8")
서버 = (루트 / "discord_bot_server.py").read_text(encoding="utf-8")
공개 = (루트 / "main_public.py").read_text(encoding="utf-8")
_함수 = 도구원.split("def simulate_formation")[1].split("\n@tool")[0]
ok("_그림남기기(h)" in _함수, "**HTML 을 _그림남기기 로 올린다** -- 서버가 discord.File 로 붙인다")
ok("ctrl.swarm_viz" in _함수, "편대 시뮬·뷰를 실제로 부른다(빈 껍데기 아님)")
ok("simulate_formation" in 서버.split("ADMIN_TOOLS = [")[1].split("]")[0],
   "ADMIN_TOOLS 에 있다")
ok("simulate_formation" in 공개.split("PUBLIC_TOOLS = [")[1].split("]")[0],
   "PUBLIC_TOOLS 에 있다")

print("\n== 5. G013 배선: ctrl 을 임포트하니 배포 paths 에 있어야 한다 ==")
_wf = (루트 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('"ctrl/**.py"' in _wf, "**ctrl/**.py 가 배포 트리거에 있다** -- 없으면 봇이 임포트에서 죽는다")

print("\n== 6. 산출 HTML 은 .gitignore 라 커밋을 안 더럽힌다 ==")
_ci = subprocess.run(["git", "check-ignore", "inbox/시뮬/x.html"],
                     cwd=str(루트), capture_output=True, text=True)
ok(_ci.returncode == 0, "inbox/시뮬/ 이 gitignore 된다 -- HTML 이 커밋에 안 쌓인다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    sys.exit(1)
print("편대 시뮬 HTML: 파이프라인 실제로 돎 · HTML 동적 · 두 채널 등록 · G013 배선 · gitignore -- 통과")
