"""eval/tasks -- 절대 기준 과제 원장. "참고를 주면 같은 모델이 더 맞히는가" 를 재는 자.

`eval/answers.py` 는 결정적 표면(고정 명령이 같은 일을 하는가)을 재고, 여기는 **모델이
푸는 것**을 잰다. 다만 판정은 여전히 모델이 아니라 코드가 한다: 코드 과제는 답 코드를
격리해서 돌려 검사 스크립트의 끝값으로, 정답 과제는 정규화한 글자 대조로, 담겨야 과제는
낱말 포함으로. 모델이 "맞았다" 고 말하는 것은 아무 근거가 아니다.

왜 있나: 제2의 뇌(참고 수집·압축)가 값을 하는지는 **같은 과제를 참고 있음/없음으로 풀어
맞힘 수의 차이**로만 알 수 있다. 이 자가 없으면 모은 것이 쓰레기인지 뇌인지 영영 모른다.
그래서 수집기보다 이것을 먼저 짓는다.

과제 한 개 = `eval/tasks/<id>.json`:

    {"id": "코드-역순단어", "과제갈래": "코드"|"추론"|"지식",
     "물음": "...",
     "판정": {"꼴": "실행", "검사": "<답.py 를 import 해 확인하는 파이썬>"}
          | {"꼴": "정답", "정답들": ["42", "마흔둘"]}          # 정규화 뒤 하나라도 같으면
          | {"꼴": "담겨야", "담겨야": ["G020", "지울 수 없"]}   # 전부 들어 있어야
     "깃발": ["..."]}                                          # 참고를 찾을 때 물음에 얹는 말

참고(있음): `graph/ask.찾기` 로 깃발 색인에서 찾은 노드의 요약·깃발·출처를 프롬프트 앞에
붙인다. 어떤 노드를 줬는지(출처·해시)를 원장에 같이 적는다 -- 나중에 "이 참고가 들어간
풀이가 맞았는가" 로 참고를 가지치기하는 재료다.

원장: eval/ledger.jsonl 에 `꼴: 과제`(한 과제 한 줄)와 `꼴: 과제묶음`(한 바퀴 요약) 으로
덧쓴다. 판정 원장이라 G020 이 지키고 .gitattributes 가 union 으로 합친다.

쓰기:
    python3 eval/tasks.py --목록                    # 과제만 보인다 (호출 0회)
    python3 eval/tasks.py                           # 참고 없음으로 한 바퀴
    python3 eval/tasks.py --참고 있음               # 색인에서 참고를 붙여
    python3 eval/tasks.py --참고 둘다               # 둘 다 풀어 이득을 잰다
    python3 eval/tasks.py --갈래 코드 --과제 코드-역순단어
끝값: 0 돌았고 후퇴 없음 · 1 후퇴(같은 참고 조건의 직전 바퀴보다 맞힘이 줄었다)
      · 3 못돌림(과제 없음 · 모델 못 부름)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from sandbox import run as SB  # noqa: E402  격리 실행의 고삐·환경을 그대로 쓴다(두 벌 금지)

과제상대 = "eval/tasks"
원장상대 = "eval/ledger.jsonl"
갈래이름들 = ("코드", "추론", "지식")
꼴들 = ("실행", "정답", "담겨야")
참고조건들 = ("없음", "있음")

# 검사 주입 자리. None 이면 router 의 풀이기(에이전트와 같은 Gemini)를 부른다.
# 검사는 (prompt) -> {"답": str, "id": str|None, "라벨": str} 을 넣는다.
풀이 = None
참고찾기 = None          # (물음, repo) -> list[dict]  (None 이면 graph/ask.찾기)


# ---------------------------------------------------------------- 과제 읽기
def 과제검사(t: dict) -> "list[str]":
    """과제 한 개가 성한가. 틀린 과제는 잴 수 없으니 읽을 때 거른다."""
    잘못 = []
    if not re.fullmatch(r"[0-9A-Za-z가-힣_-]{2,60}", str(t.get("id", ""))):
        잘못.append("id 가 없거나 글자가 이상하다")
    if t.get("과제갈래") not in 갈래이름들:
        잘못.append(f"과제갈래는 {갈래이름들} 중 하나여야 한다")
    if not str(t.get("물음", "")).strip():
        잘못.append("물음이 비었다")
    판 = t.get("판정") or {}
    꼴 = 판.get("꼴")
    if 꼴 not in 꼴들:
        잘못.append(f"판정.꼴은 {꼴들} 중 하나여야 한다")
    elif 꼴 == "실행" and not str(판.get("검사", "")).strip():
        잘못.append("실행 과제는 판정.검사(파이썬) 가 있어야 한다")
    elif 꼴 == "정답" and not [x for x in 판.get("정답들", []) if str(x).strip()]:
        잘못.append("정답 과제는 판정.정답들 이 비면 안 된다")
    elif 꼴 == "담겨야" and not [x for x in 판.get("담겨야", []) if str(x).strip()]:
        잘못.append("담겨야 과제는 판정.담겨야 가 비면 안 된다")
    return 잘못


def 과제읽기(repo=None) -> "tuple[list[dict], list[str]]":
    """(성한 과제들, 거른 까닭들). id 순."""
    d = Path(repo or REPO) / 과제상대
    과제들, 거른 = [], []
    for p in sorted(d.glob("*.json")) if d.is_dir() else []:
        try:
            t = json.loads(p.read_text(encoding="utf-8"))
        except ValueError as e:
            거른.append(f"{p.name}: JSON 이 깨졌다 ({e})")
            continue
        잘못 = 과제검사(t)
        if 잘못:
            거른.append(f"{p.name}: " + " · ".join(잘못))
        elif t["id"] != p.stem:
            거른.append(f"{p.name}: 파일 이름과 id({t['id']}) 가 다르다")
        else:
            과제들.append(t)
    return 과제들, 거른


# ---------------------------------------------------------------- 참고
def _참고기본(물음: str, repo=None) -> "list[dict]":
    from graph import ask
    return [n for _, n in ask.찾기(물음, repo=repo, 최대=3)]


def 참고묶기(과제: dict, repo=None) -> "tuple[str, list[dict]]":
    """(프롬프트에 붙일 글, 준 노드들의 [출처·해시]). 색인이 비면 ('', [])."""
    물음 = 과제["물음"] + " " + " ".join(과제.get("깃발", []))
    노드들 = (참고찾기 or _참고기본)(물음, repo)
    if not 노드들:
        return "", []
    줄 = ["[참고 -- 이 저장소의 깃발 색인에서 찾은 것. 맞는 것만 써라]"]
    준것 = []
    for n in 노드들:
        줄.append(f"- [{'·'.join(n.get('깃발', [])[:6])}] {n.get('요약', '')[:400]} <{n.get('출처', '')}>")
        준것.append({"출처": n.get("출처", ""), "해시": n.get("해시", "")})
    return "\n".join(줄) + "\n\n", 준것


# ---------------------------------------------------------------- 풀기
def 프롬프트(과제: dict, 참고글: str = "") -> str:
    꼴 = 과제["판정"]["꼴"]
    if 꼴 == "실행":
        규약 = ("답은 ```python 블록 **하나**로만 내라. 그 블록이 그대로 `답.py` 로 저장되어 "
              "검사 스크립트가 import 한다. 설명·주석은 블록 밖에 두어라.")
    elif 꼴 == "정답":
        규약 = "풀이는 짧게 하고, **마지막 줄**에 `답: <값>` 꼴로 답만 적어라."
    else:
        규약 = "한두 문단으로 답하라. 모르면 모른다고 적어라 -- 지어내지 마라."
    return f"{참고글}[과제]\n{과제['물음']}\n\n[답 규약]\n{규약}\n"


def _풀이기본(prompt: str) -> dict:
    from router import call as R
    r = R.부르기("풀이기", prompt)
    return {"답": r["답"], "id": r["id"], "라벨": r.get("라벨", "")}


# ---------------------------------------------------------------- 판정 (코드가 한다)
_코드블록 = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)
_답줄 = re.compile(r"^\s*답\s*[:：]\s*(.+?)\s*$", re.M)


def 코드뽑기(답: str) -> str:
    """마지막 파이썬 블록. 없으면 ''."""
    m = _코드블록.findall(답 or "")
    return m[-1] if m else ""


def _정규화(s: str) -> str:
    s = (s or "").strip().strip("`*\"'.。")
    s = re.sub(r"\s+", "", s).lower()
    return s.replace(",", "")


def 답뽑기(답: str) -> str:
    """`답: <값>` 의 마지막 것. 없으면 마지막 빈 줄 아닌 줄."""
    m = _답줄.findall(답 or "")
    if m:
        return m[-1]
    줄들 = [x for x in (답 or "").splitlines() if x.strip()]
    return 줄들[-1] if 줄들 else ""


def 실행판정(코드: str, 검사: str, 초: int = 20, 메모리MB: int = 512) -> "tuple[bool, str]":
    """답 코드와 검사 스크립트를 빈 임시 디렉터리에서 격리해 돌린다. (맞음, 꼬리)."""
    if not 코드.strip():
        return False, "```python 블록이 없다"
    tmp = Path(tempfile.mkdtemp(prefix="task-"))
    try:
        (tmp / "답.py").write_text(코드, encoding="utf-8")
        (tmp / "검사.py").write_text(검사, encoding="utf-8")
        # -I(격리) 는 스크립트 디렉터리를 sys.path 에서 빼서 `import 답` 이 안 된다(실측).
        # -E -s 로 환경·사용자 site 만 끊는다.
        argv = ["python3", "-E", "-s", "-B", "검사.py"]
        if SB.망차단_가능():
            argv = ["unshare", "-r", "-n", "--"] + argv
        try:
            p = subprocess.run(argv, cwd=str(tmp), capture_output=True, text=True,
                               errors="replace", timeout=초 + 10, env=SB._환경(False),
                               preexec_fn=SB._고삐(초, 메모리MB))
        except subprocess.TimeoutExpired:
            return False, f"{초}초 안에 안 끝났다"
        꼬리 = ((p.stdout or "") + (p.stderr or "")).strip()
        if p.returncode < 0:      # RLIMIT_CPU(SIGXCPU) 등 고삐가 먼저 끊으면 신호로 끝난다
            꼬리 = f"신호 {-p.returncode} 로 끊겼다 (시간·메모리 고삐)\n" + 꼬리
        return p.returncode == 0, "\n".join(꼬리.splitlines()[-6:])[-600:]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def 판정하기(과제: dict, 답: str) -> "tuple[str, str]":
    """('맞음'|'틀림', 꼬리). 모델의 말은 근거가 아니다 -- 여기만이 판정이다."""
    판 = 과제["판정"]
    if 판["꼴"] == "실행":
        ok, 꼬리 = 실행판정(코드뽑기(답), 판["검사"], 초=int(판.get("초", 20)))
        return ("맞음" if ok else "틀림"), 꼬리
    if 판["꼴"] == "정답":
        낸것 = 답뽑기(답)
        맞 = _정규화(낸것) in {_정규화(x) for x in 판["정답들"]}
        return ("맞음" if 맞 else "틀림"), f"낸 답: {낸것[:80]!r}"
    빠진 = [x for x in 판["담겨야"] if x.lower() not in (답 or "").lower()]
    return ("맞음" if not 빠진 else "틀림"), (f"빠진 말: {빠진}" if 빠진 else "")


# ---------------------------------------------------------------- 한 바퀴
def _head(repo) -> str:
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(repo),
                          capture_output=True, text=True).stdout.strip()


def 한과제(과제: dict, 참고: str, repo=None) -> dict:
    repo = Path(repo or REPO)
    참고글, 준것 = 참고묶기(과제, repo) if 참고 == "있음" else ("", [])
    시작 = time.monotonic()
    줄 = {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "꼴": "과제",
         "과제": 과제["id"], "과제갈래": 과제["과제갈래"], "참고": 참고,
         "참고들": 준것, "HEAD": _head(repo)}
    try:
        r = (풀이 or _풀이기본)(프롬프트(과제, 참고글))
    except Exception as e:
        줄.update({"판정": "못돌림", "걸린초": round(time.monotonic() - 시작, 1),
                   "꼬리": f"모델을 못 불렀다: {type(e).__name__}: {str(e)[:200]}"})
        return 줄
    판정, 꼬리 = 판정하기(과제, r.get("답", ""))
    줄.update({"판정": 판정, "걸린초": round(time.monotonic() - 시작, 1),
               "라벨": r.get("라벨", ""), "호출id": r.get("id"), "꼬리": 꼬리[-600:]})
    if r.get("id"):
        try:
            from router import call as R
            R.채택표시(r["id"], 판정 == "맞음", repo=repo)
        except Exception:
            pass
    return 줄


def 원장읽기(repo=None) -> "list[dict]":
    p = Path(repo or REPO) / 원장상대
    if not p.is_file():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def 마지막묶음(참고: str, repo=None) -> "dict | None":
    후보 = [r for r in 원장읽기(repo) if r.get("꼴") == "과제묶음" and r.get("참고") == 참고]
    return 후보[-1] if 후보 else None


def 묶음요약(줄들: "list[dict]", 참고: str, repo=None) -> dict:
    갈래별: dict = {}
    for r in 줄들:
        g = 갈래별.setdefault(r["과제갈래"], {"맞음": 0, "전체": 0, "못돌림": 0})
        g["전체"] += 1
        if r["판정"] == "맞음":
            g["맞음"] += 1
        elif r["판정"] == "못돌림":
            g["못돌림"] += 1
    맞음 = sum(1 for r in 줄들 if r["판정"] == "맞음")
    못 = sum(1 for r in 줄들 if r["판정"] == "못돌림")
    # **천장**: 참고 없이 만점인 갈래는 이득도 후퇴도 못 잰다 -- 눈금이 없다. 실측
    # 2026-09-11 첫 바퀴: 추론 4/4 · 코드 4/4 라 지식만 움직였다. 더 어려운 과제를 넣어라.
    천장 = ([g for g, v in 갈래별.items() if 참고 == "없음" and v["전체"] and v["맞음"] == v["전체"]]
          if 참고 == "없음" else [])
    앞 = 마지막묶음(참고, repo)
    흐름 = ""
    if 앞 and 앞.get("전체") and 못 == 0 and 앞.get("못돌림", 0) == 0:
        if 맞음 < 앞["맞음"]:
            흐름 = "후퇴"
        elif 맞음 > 앞["맞음"]:
            흐름 = "향상"
    return {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "꼴": "과제묶음",
            "참고": 참고, "맞음": 맞음, "전체": len(줄들), "못돌림": 못,
            "갈래별": 갈래별, "HEAD": _head(Path(repo or REPO)),
            "틀린과제": [r["과제"] for r in 줄들 if r["판정"] == "틀림"], "흐름": 흐름,
            "천장": 천장}


def 돌리기(참고조건: "list[str]", repo=None, 갈래: str = "", 과제id: str = "",
        적기: bool = True) -> dict:
    """참고 조건마다 과제 전부를 풀고 원장에 적는다.
    돌려주는 것: {"돌았나", "묶음들": {참고: 묶음}, "줄들", "거른", "이득"}."""
    repo = Path(repo or REPO)
    과제들, 거른 = 과제읽기(repo)
    if 갈래:
        과제들 = [t for t in 과제들 if t["과제갈래"] == 갈래]
    if 과제id:
        과제들 = [t for t in 과제들 if t["id"] == 과제id]
    if not 과제들:
        return {"돌았나": False, "묶음들": {}, "줄들": [], "거른": 거른, "이득": None,
                "메모": "풀 과제가 없다"}
    줄들, 묶음들 = [], {}
    for 참고 in 참고조건:
        이번 = [한과제(t, 참고, repo) for t in 과제들]
        묶음들[참고] = 묶음요약(이번, 참고, repo)
        줄들 += 이번
        if 적기:
            p = repo / 원장상대
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                for r in 이번 + [묶음들[참고]]:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
    전부못 = all(r["판정"] == "못돌림" for r in 줄들)
    이득 = None
    if "있음" in 묶음들 and "없음" in 묶음들:
        이득 = {"전체": 묶음들["있음"]["맞음"] - 묶음들["없음"]["맞음"]}
        for g in 갈래이름들:
            a = 묶음들["있음"]["갈래별"].get(g, {}).get("맞음", 0)
            b = 묶음들["없음"]["갈래별"].get(g, {}).get("맞음", 0)
            if g in 묶음들["있음"]["갈래별"]:
                이득[g] = a - b
    return {"돌았나": not 전부못, "묶음들": 묶음들, "줄들": 줄들, "거른": 거른, "이득": 이득}


def 보고(결과: dict) -> str:
    줄 = []
    for 거 in 결과.get("거른", []):
        줄.append(f"  (거름) {거}")
    if not 결과.get("돌았나"):
        줄.append("  못돌림 -- " + (결과.get("메모") or "모델을 한 번도 못 불렀다 (키·쿼터를 보라)"))
        꼬리들 = [r.get("꼬리", "") for r in 결과.get("줄들", [])][:1]
        줄 += [f"       {x}" for x in 꼬리들 if x]
        return "\n".join(줄)
    for 참고, m in 결과["묶음들"].items():
        갈래 = " · ".join(f"{g} {v['맞음']}/{v['전체']}" for g, v in m["갈래별"].items())
        흐름 = f"  ** {m['흐름']} **" if m["흐름"] else ""
        줄.append(f"  참고 {참고}: 맞음 {m['맞음']}/{m['전체']}"
                 + (f" (못돌림 {m['못돌림']})" if m["못돌림"] else "") + f"  [{갈래}]{흐름}")
        if m["틀린과제"]:
            줄.append(f"       틀림: {', '.join(m['틀린과제'][:8])}")
        if m.get("천장"):
            줄.append(f"       천장(눈금 없음): {', '.join(m['천장'])} -- 참고 없이 만점이라 "
                     "이득·후퇴를 못 잰다. 더 어려운 과제를 넣어라")
    if 결과.get("이득") is not None:
        d = 결과["이득"]
        갈래 = " · ".join(f"{g} {d[g]:+d}" for g in 갈래이름들 if g in d)
        줄.append(f"  참고의 이득: 전체 {d['전체']:+d}  [{갈래}]"
                 + ("  <- 참고가 값을 못 한다. 모은 것을 의심하라" if d["전체"] <= 0 else ""))
    return "\n".join(줄)


def main() -> int:
    ap = argparse.ArgumentParser(description="절대 기준 과제를 풀고 참고의 이득을 잰다")
    ap.add_argument("--참고", default="없음", choices=("없음", "있음", "둘다"))
    ap.add_argument("--갈래", default="", help=f"{'|'.join(갈래이름들)} 중 하나만")
    ap.add_argument("--과제", default="", help="id 하나만")
    ap.add_argument("--목록", action="store_true", help="과제만 보이고 안 푼다")
    args = ap.parse_args()

    if args.목록:
        과제들, 거른 = 과제읽기()
        for t in 과제들:
            print(f"  {t['과제갈래']:<3} {t['id']:<24} [{t['판정']['꼴']}] {t['물음'][:60]}")
        for 거 in 거른:
            print(f"  (거름) {거}")
        print(f"  과제 {len(과제들)}개" + (f" · 거름 {len(거른)}" if 거른 else ""))
        return 0 if 과제들 else 3

    조건 = list(참고조건들) if args.참고 == "둘다" else [args.참고]
    결과 = 돌리기(조건, 갈래=args.갈래, 과제id=args.과제)
    print(보고(결과))
    if not 결과["돌았나"]:
        return 3
    return 1 if any(m["흐름"] == "후퇴" for m in 결과["묶음들"].values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
