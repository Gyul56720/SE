"""dig/harvest(수집기)를 임시 저장소에서 **가짜 망**으로 끝까지 돌려 붙든다.

붙드는 것: (1) 검색 -> README/파일 raw -> 검증 -> dig/corpus 저장 -> graph 색인 -> 원장,
(2) 판정은 코드가 한다 -- 허용 밖 라이선스·빈 내용·문법 깨진 코드는 거절로 남고 저장 안
된다, (3) 같은 url+해시는 두 번 안 받는다, (4) 403/Remaining 0 이면 그 출처는 멈추고
그렇다고 말한다 -- 첫 요청부터 다 막히면 못돌림, (5) 상한·하루 상한, (6) 틈: 자(eval)가
참고를 줘도 틀린 과제의 깃발이 검색어가 된다, (7) 토큰 없으면 코드 검색은 안 두드린다,
(8) `!수집` 배선 · 색인이 eval/tasks 의 참고로 실제로 찾힌다.

LLM·망 없이 돈다. 실행: python3 tests/test_harvest.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from dig import fetch as FT  # noqa: E402
from dig import harvest as H  # noqa: E402
from graph import ask, store  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


임시 = Path(tempfile.mkdtemp(prefix="test-harvest-"))
repo = 임시 / "repo"
(repo / "eval" / "tasks").mkdir(parents=True)
subprocess.run(["git", "init", "-q", str(repo)], check=True)

# ---- 가짜 망: url 꼴마다 정해진 답
호출 = []
막힘 = {"github": False, "hf": False}
남은 = {"github": "40"}


def 가짜(url, 헤더, 틈=20.0):
    호출.append((url, dict(헤더)))
    # 검색어마다 다른 것이 나오게 -- 그래야 중복 거르기와 상한을 갈라 잰다
    tag = (url.split("q=", 1)[1] if "q=" in url else url.split("search=", 1)[1] if "search=" in url else "")[:6]
    def 답(몸, 코드=200, 꼴="application/json", h=None):
        return FT.응답(url=url, 최종url=url, 코드=코드, 몸통=몸, 꼴=꼴, 헤더=h or {})
    if "api.github.com" in url:
        if 막힘["github"]:
            return FT.응답(url=url, 코드=403, 몸통='{"message":"rate limit"}', 왜="HTTP 403 -- 막았다")
        gh = {"X-RateLimit-Remaining": 남은["github"]}
        if "/search/repositories" in url:
            return 답(json.dumps({"items": [
                {"full_name": "a/cusum", "html_url": f"https://github.com/a/cusum?q={tag}", "stargazers_count": 90,
                 "license": {"spdx_id": "MIT"}},
                {"full_name": "b/closed", "html_url": f"https://github.com/b/closed?q={tag}", "stargazers_count": 5,
                 "license": {"spdx_id": "NOASSERTION"}},
                {"full_name": "c/empty", "html_url": "https://github.com/c/empty", "stargazers_count": 1,
                 "license": {"spdx_id": "Apache-2.0"}},
            ]}), h=gh)
        if "/search/code" in url:
            return 답(json.dumps({"items": [
                {"path": "cp/cusum.py", "html_url": "https://github.com/a/cusum/blob/main/cp/cusum.py",
                 "repository": {"full_name": "a/cusum"}},
                {"path": "bad.py", "html_url": "https://github.com/a/cusum/blob/main/bad.py",
                 "repository": {"full_name": "a/cusum"}},
            ]}), h=gh)
        if url.endswith("/repos/a/cusum"):
            return 답(json.dumps({"license": {"spdx_id": "MIT"}}), h=gh)
        if "/repos/a/cusum/readme" in url:
            return 답("# cusum\n\nCUSUM change point detection. detection detection change change point.\n", 꼴="text/plain", h=gh)
        if "/repos/b/closed/readme" in url:
            return 답("# closed\nall rights reserved\n", 꼴="text/plain", h=gh)
        if "/repos/c/empty/readme" in url:
            return FT.응답(url=url, 코드=404, 왜="HTTP 404 -- 없다")
        if "/contents/cp/cusum.py" in url:
            return 답("def cusum(xs):\n    return max(range(1, len(xs)), key=lambda k: abs(sum(xs[:k])/k - sum(xs[k:])/(len(xs)-k)))\n", 꼴="text/plain", h=gh)
        if "/contents/bad.py" in url:
            return 답("def (broken:\n", 꼴="text/plain", h=gh)
    if "huggingface.co" in url:
        if 막힘["hf"]:
            return FT.응답(url=url, 코드=429, 왜="HTTP 429 -- 한도")
        if "/api/datasets" in url:
            return 답(json.dumps([{"id": f"org/changepoints-{tag}", "cardData": {"license": "cc-by-4.0"}},
                                  {"id": "org/nolicense", "tags": []}]))
        if "/api/models" in url:
            return 답(json.dumps([{"id": f"org/cpmodel-{tag}", "tags": ["license:apache-2.0"]}]))
        if "datasets/org/changepoints" in url and "/raw/" in url:
            return 답("---\nlicense: cc-by-4.0\n---\n# changepoints dataset\nlabeled change point series for CUSUM benchmarks.\n", 꼴="text/plain")
        if "datasets/org/nolicense/raw" in url:
            return 답("# nolicense\n", 꼴="text/plain")
        if "org/cpmodel" in url and "/raw/" in url:
            return 답("# cpmodel\nchange point model card.\n", 꼴="text/plain")
    return FT.응답(url=url, 코드=404, 왜="HTTP 404 -- 가짜 망에 없다")


진짜 = FT.한번
FT.한번 = 가짜
os.environ.pop("GITHUB_TOKEN", None)
os.environ.pop("HF_TOKEN", None)

try:
    print("== 토큰 없이 한 바퀴 ==")
    r = H.한바퀴(["cusum change point"], repo=repo, 몇=5, 상한=20)
    ok(r["돌았나"], "돌았다")
    ok(not any("/search/code" in u for u, _ in 호출), "**토큰 없으면 코드 검색은 안 두드린다**")
    ok(r["저장"] == 3 and r["색인"] == 3, f"MIT README · cc-by 데이터셋 · apache 모델 = 저장 3 · 색인 3 ({r['저장']}, {r['색인']})")
    거절 = " | ".join(r["거절"])
    ok("noassertion" in 거절 and "허용 목록 밖" in 거절, f"**허용 밖 라이선스는 거절** ({거절[:80]})")
    ok("내용 없음" in 거절 and "404" in 거절, "빈 내용(404)은 까닭과 함께 거절")
    ok("라이선스 미상" in 거절, "라이선스 미상은 거절")
    파일들 = sorted((repo / "dig" / "corpus").glob("*.md"))
    ok(len(파일들) == 3 and all(p.read_text(encoding="utf-8").startswith("---\n출처: https://") for p in 파일들),
       "corpus 파일에 출처·라이선스 머리가 있다")
    nodes, _ = store.읽기(repo)
    ok(len(nodes) == 3 and all(n["지은이"] == "코드" for n in nodes), "graph 색인 3 노드, 지은이=코드(모델 요약 없음)")
    찾은 = ask.찾기("cusum change point", repo=repo)
    ok(찾은 and "dig/corpus/" in 찾은[0][1]["출처"], f"**eval/tasks 가 쓰는 색인 조회로 실제로 찾힌다** ({찾은[0][1]['출처'] if 찾은 else None})")
    원장 = H.원장읽기(repo)
    ok(len(원장) == 6 and {x["판정"] for x in 원장} == {"색인", "거절"}, f"원장 6줄 (색인 3 · 거절 3) ({len(원장)})")
    ok(H.오늘받은수(repo) == 3, "오늘 받은 수는 색인만 센다")

    print("\n== 두 번째 바퀴: 같은 것은 다시 안 받는다 ==")
    n0 = len(호출)
    r2 = H.한바퀴(["cusum change point"], repo=repo)
    ok(r2["저장"] == 0 and r2["색인"] == 0 and len(H.원장읽기(repo)) == 6, "저장 0 · 원장 그대로")
    ok(len(호출) > n0, "검색은 다시 한다 (새 것이 생겼을 수 있다)")

    print("\n== 토큰 있으면 코드 검색 -> compile 검증 ==")
    (repo / ".env").write_text("GITHUB_TOKEN=ghp_test\nHF_TOKEN=hf_test\n", encoding="utf-8")
    ok(H._env("GITHUB_TOKEN", repo) == "ghp_test", ".env 에서 토큰을 읽는다 (dotenv 없이)")
    r3 = H.한바퀴(["cusum change point"], repo=repo, 출처=("github",))
    ok(any("/search/code" in u and h.get("Authorization") == "Bearer ghp_test" for u, h in 호출),
       "코드 검색을 Bearer 토큰으로 두드린다")
    ok(r3["저장"] == 1 and any("문법이 안 맞는다" in x for x in r3["거절"]),
       f"**돌아가는 코드만 저장, 문법 깨진 것은 거절** ({r3['거절']})")
    코드파일 = [p for p in (repo / "dig" / "corpus").glob("github-code-*.md")]
    ok(len(코드파일) == 1 and "라이선스: mit" in 코드파일[0].read_text(encoding="utf-8"),
       "코드 조각의 라이선스는 저장소 것으로 채운다")

    print("\n== 막히면 멈추고 말한다 ==")
    막힘["github"] = True
    r4 = H.한바퀴(["kalman filter"], repo=repo, 출처=("github",))
    ok(not r4["돌았나"] and "github" in r4["막힘"] and "403" in r4["막힘"]["github"],
       f"**첫 요청부터 403 이면 못돌림** ({r4['막힘']})")
    막힘["github"] = False
    남은["github"] = "0"
    r5 = H.한바퀴(["kalman filter"], repo=repo)
    ok("github" in r5["막힘"] and "Remaining 0" in r5["막힘"]["github"] and r5["돌았나"],
       f"Remaining 0 이면 github 은 멈추되 hf 는 돌아 '돌았다' ({r5['막힘']})")
    남은["github"] = "40"
    보 = H.보고(r5)
    ok("막힘 github" in 보 and "이 바퀴는 여기까지" in 보, "보고가 막힘을 말한다")

    print("\n== 상한 ==")
    r6 = H.한바퀴(["kalman filter", "ornstein uhlenbeck"], repo=repo, 상한=1)
    ok(r6["색인"] <= 1 and "상한" in r6.get("메모", ""), f"바퀴 상한 ({r6['색인']}, {r6.get('메모')})")
    os.environ["HARVEST_DAILY_CAP"] = "3"
    r7 = H.한바퀴(["walk forward"], repo=repo)
    ok(not r7["돌았나"] and "하루 상한" in r7["메모"], f"**하루 상한에 닿으면 안 돈다** ({r7['메모']})")
    os.environ.pop("HARVEST_DAILY_CAP", None)

    print("\n== 틈: 자가 틀린 자리가 검색어가 된다 ==")
    (repo / "eval" / "tasks" / "코드-변화점.json").write_text(json.dumps(
        {"id": "코드-변화점", "과제갈래": "코드", "물음": "x", "깃발": ["변화점", "CUSUM"],
         "판정": {"꼴": "실행", "검사": "import 답\n"}}, ensure_ascii=False), encoding="utf-8")
    (repo / "eval" / "tasks" / "추론-둘.json").write_text(json.dumps(
        {"id": "추론-둘", "과제갈래": "추론", "물음": "1+1", "판정": {"꼴": "정답", "정답들": ["2"]}},
        ensure_ascii=False), encoding="utf-8")
    with open(repo / "eval" / "ledger.jsonl", "a", encoding="utf-8") as f:
        for 줄 in [{"꼴": "과제", "과제": "코드-변화점", "참고": "있음", "판정": "맞음"},
                  {"꼴": "과제", "과제": "코드-변화점", "참고": "있음", "판정": "틀림"},   # 마지막이 틀림
                  {"꼴": "과제", "과제": "추론-둘", "참고": "있음", "판정": "맞음"},
                  {"꼴": "과제", "과제": "추론-둘", "참고": "없음", "판정": "틀림"}]:    # 없음은 안 본다
            f.write(json.dumps(줄, ensure_ascii=False) + "\n")
    틈 = H.틈찾기(repo)
    ok([g["과제"] for g in 틈] == ["코드-변화점"] and 틈[0]["말"] == "변화점 CUSUM",
       f"**참고를 줘도 마지막에 틀린 과제만, 깃발이 검색어** ({틈})")
finally:
    FT.한번 = 진짜
    shutil.rmtree(임시, ignore_errors=True)

print("\n== 배선 ==")
import dispatch  # noqa: E402
ok("검색어" in (dispatch.run("!수집") or ""), "!수집 도움말")
ok("관리 채널" in (dispatch.run("!수집 cusum", allow_write=False) or ""), "공개 채널은 거절")
불림 = []
답 = dispatch.run("!수집 kalman filter", runner=lambda argv, 로그, 무엇: (불림.append(argv) or "시작"), allow_write=True)
ok(불림 and 불림[0] == ["python3", "dig/harvest.py", "--말", "kalman filter"], f"검색어가 argv 로 넘어간다 ({불림})")
dispatch.run("!수집 틈으로", runner=lambda argv, 로그, 무엇: (불림.append(argv) or "시작"), allow_write=True)
ok(불림[-1] == ["python3", "dig/harvest.py", "--틈"], "틈으로 -> --틈")
ok(dispatch.run("!수집기 x") is None, "붙여 쓴 `!수집기` 는 명령이 아니다")
p = subprocess.run(["python3", "dig/harvest.py", "--틈만"], cwd=str(뿌리), capture_output=True, text=True)
ok(p.returncode in (0, 3) and "틈" in p.stdout, "--틈만 은 망 없이 돈다")
ok("dig/corpus/" in (뿌리 / ".gitignore").read_text(encoding="utf-8"), "corpus 는 gitignore (다시 받으면 되는 것)")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("dig/harvest.py" in _서버, "프롬프트가 dig/harvest.py 를 이름을 대고 시킨다")
_wf = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok("deploy/se-harvest.timer" in _wf and (뿌리 / "deploy" / "se-harvest.timer").is_file(),
   "24시간 루프: systemd timer 가 배포 스크립트에 걸려 있다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("harvest: 끝까지 한 바퀴 · 라이선스/문법 거절 · 중복 · 막힘 · 상한 · 틈 · 배선 -- 통과")
