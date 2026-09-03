"""Gemini API 를 생 HTTP 로 때려 층을 갈라내는 진단기. langchain 을 쓰지 않는다.

왜 필요한가. 오케스트레이터가 503/504 로 죽을 때 보이는 것은 langchain +
tenacity + google.genai 를 지나온 예외뿐이라, 아래 중 무엇인지 구별할 수 없다.

    (a) 키가 죽었다                      -> 401/403
    (b) 그 모델 이름이 없다              -> 404. 풀이 유령 모델을 때리고 있는 것이다
    (c) 구글이 정말 과부하다             -> 짧은 프롬프트도 503
    (d) 우리 요청이 문제다               -> 짧은 것은 되는데 우리 것만 503/504
    (e) 우리 재시도 설정이 문제다        -> 생 HTTP 는 되는데 langchain 만 실패
    (f) 쿼터를 진짜로 썼다               -> 429 + 우리 장부에도 기록

표준 라이브러리만 쓴다(urllib). 그래야 실패가 우리 의존성 탓이 아님을 말할 수 있다.

    python3 orchestrator/probe_gemini.py              # 기본 진단
    python3 orchestrator/probe_gemini.py --full       # 실제 문제 기술서까지 태운다
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

ROOT = "https://generativelanguage.googleapis.com"
BASE = f"{ROOT}/v1beta"
# **404 를 "유령 모델"이라고 단정하면 안 된다.** 이 진단기는 v1beta 의 :generateContent 를
# 때리는데, langchain-google-genai 는 다른 버전/엔드포인트를 쓸 수 있다. 그러면 여기서 404 인
# 모델이 오케스트레이터에서는 멀쩡히 돌 수도 있고, 그 반대도 된다. 그래서 두 버전을 다
# 시도하고 **어느 쪽에서 됐는지를 같이 찍는다.**
VERSIONS = ("v1beta", "v1")
TINY = "Reply with exactly: OK"


def _keys() -> list:
    import llm_pool
    if not os.environ.get("GEMINI_API_KEY"):
        llm_pool._load_dotenv()
    out = []
    for name in ("GEMINI_API_KEY", "GEMINI_API_KEY_FALLBACK"):
        v = os.environ.get(name)
        if v:
            out.append((name, v))
    return out


def _mask(k: str) -> str:
    return f"{k[:6]}...{k[-4:]} (len {len(k)})"


def _req(url: str, payload=None, timeout=60.0):
    """(status, body, 초). 예외를 삼키지 않고 상태코드로 돌려준다."""
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method="POST" if data else "GET")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), time.perf_counter() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), time.perf_counter() - t0
    except Exception as e:                       # 타임아웃 / DNS / TLS
        return 0, f"{type(e).__name__}: {e}", time.perf_counter() - t0


def list_models(key: str):
    st, body, dt = _req(f"{BASE}/models?key={key}&pageSize=200", timeout=30.0)
    if st != 200:
        return st, body, dt, []
    names = []
    for m in json.loads(body).get("models", []):
        if "generateContent" in (m.get("supportedGenerationMethods") or []):
            names.append(m["name"].split("/", 1)[-1])
    return st, body, dt, names


def generate(key: str, model: str, prompt: str, timeout=90.0):
    """두 API 버전을 차례로 때린다. 마지막 시도의 결과를 돌려주되, 하나라도 되면 그것을 쓴다."""
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    st = body = None
    dt = 0.0
    ver = ""
    for v in VERSIONS:
        ver = v
        st, body, d = _req(f"{ROOT}/{v}/models/{model}:generateContent?key={key}",
                           payload, timeout)
        dt += d
        if st != 404:                      # 404 만 다음 버전으로 넘어간다
            break
    if st == 200:
        try:
            j = json.loads(body)
            txt = j["candidates"][0]["content"]["parts"][0]["text"]
            return st, f"[{ver}] {txt.strip()[:52]}", dt
        except Exception:
            return st, f"[{ver}] (응답 파싱 실패) {body[:110]}", dt
    try:
        err = json.loads(body).get("error", {})
        return st, f"[{ver}] {err.get('status', '?')}: {str(err.get('message'))[:100]}", dt
    except Exception:
        return st, f"[{ver}] {body[:120]}", dt


def _problem_prompt() -> str:
    import importlib.util
    run = HERE / "problems" / "tensor_rank" / "run.py"
    sp = importlib.util.spec_from_file_location("_tr", run)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    spec = json.loads((run.parent / "target.json").read_text(encoding="utf-8"))
    return m.PROBLEM.format(target_path="/tmp/target.json",
                            target_json=json.dumps(spec, ensure_ascii=False, indent=1))


def main() -> int:
    ap = argparse.ArgumentParser(description="Gemini API 층별 진단 (langchain 우회)")
    ap.add_argument("--full", action="store_true",
                    help="실제 문제 기술서(약 4.7KB)까지 태워 프롬프트 크기 영향을 본다")
    ap.add_argument("--models", type=int, default=8, help="키당 시험할 모델 수")
    ap.add_argument("--reset-quota", action="store_true",
                    help="오늘자 '소진 확정' 표시를 지운다. 429 를 분당/일일로 가르지 "
                         "않던 시절에 잘못 박힌 봉인을 푼다 (_dead 는 안 건드린다)")
    a = ap.parse_args()

    keys = _keys()
    print("=" * 78)
    print(f"[1] 키   {len(keys)}개 발견")
    for name, k in keys:
        print(f"    {name} = {_mask(k)}")
    if not keys:
        print("    키가 없다. set -a; source ~/SE/.env; set +a 부터 해라")
        return 1

    tried = []                                   # 풀이 실제로 때리는 이름
    try:
        import llm_pool
        for name, k in keys:
            tried += llm_pool._default_models(k)
    except Exception as e:
        print(f"    (풀 모델 목록 조회 실패: {e})")

    verdict = []
    for name, k in keys:
        print("=" * 78)
        print(f"[2] {name} -- 모델 목록 (ListModels)")
        st, body, dt, names = list_models(k)
        print(f"    HTTP {st}  {dt:.2f}s  생성가능 모델 {len(names)}개")
        if st != 200:
            print(f"    {body[:300]}")
            # 처음 판은 200 이 아닌 것을 전부 "키가 거부됐다"로 뭉쳤다. 503 은 키 문제가
            # 아니다 -- [3] 에서 같은 실수를 고쳐놓고 [2] 는 그대로 뒀던 것이다.
            if st in (400, 401, 403):
                verdict.append(f"{name}: 모델 목록 조회가 인증에서 거부됐다 "
                               f"(HTTP {st}) -- 키가 죽었다")
            elif st == 429:
                verdict.append(f"{name}: 모델 목록 조회조차 429 -- 한도를 썼다")
            elif st in (503, 504, 500):
                verdict.append(f"{name}: 모델 목록 조회가 HTTP {st} -- **키 문제가 아니다.** "
                               f"구글이 목록조차 못 주고 있다. 순수 용량 문제다")
            else:
                verdict.append(f"{name}: 모델 목록 조회 실패 (HTTP {st}) -- 위 본문을 봐라")
            continue
        print(f"    {', '.join(names[:12])}{' ...' if len(names) > 12 else ''}")
        ghosts = sorted({m for m in tried if m not in names})
        if ghosts:
            print(f"    !! 풀이 때리는데 목록에 없는 이름: {ghosts}")
            verdict.append(f"{name}: 유령 모델 {len(ghosts)}개를 때리고 있다")

        print(f"[3] {name} -- 짧은 프롬프트 ({len(TINY)}자)")
        ok_short, seen = [], []
        for m in names[:a.models]:
            st, msg, dt = generate(k, m, TINY, timeout=60.0)
            mark = "OK" if st == 200 else "X "
            print(f"    [{mark}] {m:38} HTTP {st:3}  {dt:6.2f}s  {msg}")
            seen.append((st, msg))
            if st == 200:
                ok_short.append(m)

        if a.full and ok_short:
            big = _problem_prompt()
            print(f"[4] {name} -- 실제 문제 기술서 ({len(big)}자)")
            for m in ok_short[:2]:
                st, msg, dt = generate(k, m, big, timeout=180.0)
                mark = "OK" if st == 200 else "X "
                print(f"    [{mark}] {m:38} HTTP {st:3}  {dt:6.2f}s  {msg}")
                if st != 200:
                    verdict.append(f"{name}/{m}: 짧은 것은 되는데 4.7KB 는 안 된다 "
                                   f"-- 구글 과부하가 아니라 우리 요청 문제다")
        gap = [m for (m, (st, _)) in zip(names[:a.models], seen) if st in (400, 404)]
        if gap:
            print(f"    !! 목록에는 있는데 호출은 400/404 인 모델 {len(gap)}개: {gap}")
            print(f"       (이 진단기는 {'/'.join(VERSIONS)} 의 :generateContent 를 쓴다. "
                  f"langchain 은 다른 경로를 쓸 수 있으니 이것만으로 유령이라 단정 못 한다)")
        if ok_short:
            verdict.append(f"{name}: 짧은 프롬프트 {len(ok_short)}개 성공 -- API 는 살아 있다"
                           + (f", 다만 {len(gap)}개는 목록에만 있고 호출은 안 된다" if gap else ""))
        else:
            # **"전부 실패"를 한 덩어리로 부르면 안 된다.** 429 와 503 은 할 일이 정반대다:
            # 429 는 우리가 너무 빨리 때린 것이거나 한도를 쓴 것이고, 503 은 구글 용량이다.
            # 처음 판 진단기가 둘을 뭉쳐 "구글 쪽 문제"라고 찍었는데, 그건 진단이 아니다.
            hist = {}
            for st, _ in seen:
                hist[st] = hist.get(st, 0) + 1
            joined = " ".join(m for _, m in seen)
            shape = ", ".join(f"HTTP {st}x{n}" for st, n in sorted(hist.items()))
            if set(hist) <= {429}:
                if "PerMinute" in joined or "per minute" in joined.lower():
                    verdict.append(f"{name}: 전부 429 **분당 한도**({shape}) -- 1분 뒤면 "
                                   f"풀린다. 하루치를 쓴 것이 아니다")
                else:
                    verdict.append(f"{name}: 전부 429 **일일 한도**({shape}) -- 자정까지 "
                                   f"안 풀린다. 다른 키가 필요하다")
            elif set(hist) <= {503, 504, 500, 0}:
                verdict.append(f"{name}: 전부 503/504({shape}) -- 짧은 프롬프트조차 안 된다. "
                               f"구글 무료 티어 용량 문제이고 코드로 못 푼다")
            elif set(hist) <= {400, 401, 403}:
                verdict.append(f"{name}: 전부 인증 거부({shape}) -- 키가 죽었다")
            elif 404 in hist:
                verdict.append(f"{name}: 404 가 섞였다({shape}) -- 없는 모델을 때린다")
            else:
                verdict.append(f"{name}: 섞였다({shape}) -- 위 표를 직접 봐라")

    print("=" * 78)
    print("[5] 우리 장부(quota_tracker) 상태")
    try:
        import quota_tracker
        lim = quota_tracker.DEFAULT_DAILY_LIMIT
        data = quota_tracker._load()
        rows = [(lb, e) for lb, e in data.items()
                if isinstance(e, dict) and "count" in e and not lb.startswith("_")]
        today = [(lb, e) for lb, e in rows if e.get("date") == quota_tracker._today()]
        sealed = [lb for lb, e in today if e.get("count", 0) >= lim]
        counted = [(lb, e["count"]) for lb, e in today if 0 < e["count"] < lim]
        dead = list((data.get("_dead") or {}))
        print(f"    일일 한도 설정값 = {lim}")
        print(f"    영구 제외(_dead) {len(dead)}개: {dead[:6]}")
        print(f"    **오늘 소진 확정** {len(sealed)}개: {sealed[:8]}")
        print(f"    오늘 실사용 카운트 {len(counted)}개: {counted[:8]}")
        if sealed:
            print(f"    -- count 가 정확히 {lim} 인 것은 세어서 도달한 게 아니라 "
                  f"record_exhausted 가 박은 값이다.")
            print(f"       429 를 분당/일일로 가르지 않던 시절의 기록이면 잘못된 봉인이다. "
                  f"--reset-quota 로 지운다.")
        if a.reset_quota:
            for lb, e in today:
                if e.get("count", 0) >= lim:
                    e["count"] = 0
                e.pop("cooling_until", None)
            quota_tracker._save(data)
            print(f"    >> 오늘자 소진 표시 {len(sealed)}개를 지웠다 "
                  f"(_dead 는 건드리지 않았다)")
    except Exception as e:
        print(f"    장부를 못 읽었다: {type(e).__name__}: {e}")

    print("=" * 78)
    print("[판정]")
    for v in verdict:
        print(f"  · {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
