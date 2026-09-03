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

BASE = "https://generativelanguage.googleapis.com/v1beta"
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
    st, body, dt = _req(f"{BASE}/models/{model}:generateContent?key={key}",
                        {"contents": [{"parts": [{"text": prompt}]}]}, timeout)
    if st == 200:
        try:
            j = json.loads(body)
            txt = j["candidates"][0]["content"]["parts"][0]["text"]
            return st, txt.strip()[:60], dt
        except Exception:
            return st, f"(응답 파싱 실패) {body[:120]}", dt
    try:
        err = json.loads(body).get("error", {})
        return st, f"{err.get('status', '?')}: {str(err.get('message'))[:110]}", dt
    except Exception:
        return st, body[:130], dt


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
    ap.add_argument("--models", type=int, default=4, help="키당 시험할 모델 수")
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
            verdict.append(f"{name}: 키 자체가 거부됐다 (HTTP {st}) -- 키를 의심하라")
            continue
        print(f"    {', '.join(names[:12])}{' ...' if len(names) > 12 else ''}")
        ghosts = sorted({m for m in tried if m not in names})
        if ghosts:
            print(f"    !! 풀이 때리는데 목록에 없는 이름: {ghosts}")
            verdict.append(f"{name}: 유령 모델 {len(ghosts)}개를 때리고 있다")

        print(f"[3] {name} -- 짧은 프롬프트 ({len(TINY)}자)")
        ok_short = []
        for m in names[:a.models]:
            st, msg, dt = generate(k, m, TINY, timeout=60.0)
            mark = "OK" if st == 200 else "X "
            print(f"    [{mark}] {m:38} HTTP {st:3}  {dt:6.2f}s  {msg}")
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
        if not ok_short:
            verdict.append(f"{name}: 짧은 프롬프트도 전부 실패 -- 구글 쪽 문제다")
        else:
            verdict.append(f"{name}: 짧은 프롬프트 {len(ok_short)}개 성공 "
                           f"-- API 는 살아 있다")

    print("=" * 78)
    print("[5] 우리 장부(quota_tracker) 상태")
    try:
        import quota_tracker
        data = quota_tracker._load()
        rows = [(lb, e) for lb, e in (data.get("models") or data).items()
                if isinstance(e, dict)]
        dead = [lb for lb, e in rows if e.get("dead")]
        used = [(lb, e.get("count")) for lb, e in rows if e.get("count")]
        print(f"    영구 제외(dead) {len(dead)}개: {dead[:6]}")
        print(f"    오늘 사용 기록 {len(used)}개: {used[:8]}")
    except Exception as e:
        print(f"    장부를 못 읽었다: {type(e).__name__}: {e}")

    print("=" * 78)
    print("[판정]")
    for v in verdict:
        print(f"  · {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
