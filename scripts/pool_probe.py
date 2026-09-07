"""풀 탐침 -- **아주 짧은 프롬프트**를 후보마다 한 번씩 던져 지금 무엇이 살아 있는지 본다.

원고를 돌리다 429 를 만나면 무엇이 문제인지 알 수가 없다. 키가 죽었는지, 오늘 치를 다
썼는지, 분당 한도에 걸린 것뿐인지, 모델 이름이 바뀐 것인지 -- 로그에는 전부 429 로만
보인다. 그래서 **소설 프롬프트가 아니라 열 글자짜리 프롬프트**로 한 바퀴 돌려 본다.
토큰이 거의 안 들고, 걸리는 갈래는 똑같이 걸린다.

    python3 scripts/pool_probe.py            # 한 바퀴 돌며 후보별 상태와 지연
    python3 scripts/pool_probe.py --parallel # 동시에 던져 총 걸린 시간을 본다

구글 문서 기준(2026-09):
  · 한도는 **프로젝트** 단위다. 한 프로젝트에서 키를 여러 개 만들어도 한도는 안 늘어난다.
  · RPM 은 **모델별**로 따로 걸린다(무료: 2.5 Pro 5 · Flash 10 · Flash-Lite 15).
  · TPM(분당 토큰)은 프로젝트에서 공유한다.
그래서 이 탐침은 **키가 몇 개의 프로젝트에 흩어져 있는지**를 보는 데 제일 쓸모가 있다 --
같은 프로젝트의 키들이면 아무리 늘려도 빨라지지 않는다.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import llm_pool                                     # noqa: E402

TINY = "1+1은?"          # 열 글자도 안 된다. 토큰을 아끼려는 것이 이 도구의 요점이다.


def probe_one(label, llm, prompt: str) -> dict:
    t0 = time.time()
    try:
        text = llm_pool._extract_text(llm.invoke(prompt))
        return {"label": label, "ok": True, "sec": time.time() - t0,
                "note": (text or "").strip().replace("\n", " ")[:24]}
    except Exception as e:                                   # noqa: BLE001
        kind = ("RPM" if llm_pool._is_rpm(e) else
                "일일소진" if llm_pool._is_quota(e) else
                "영구" if llm_pool._is_permanent(e) else "일시")
        wait = llm_pool._retry_delay(e)
        return {"label": label, "ok": False, "sec": time.time() - t0,
                "note": kind + (f" (retryDelay {wait:.0f}s)" if wait else "")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parallel", action="store_true", help="동시에 던진다")
    ap.add_argument("--prompt", default=TINY)
    ap.add_argument("--roster", default="",
                    help="답한 후보만 이 파일에 적는다. 런은 GEMINI_ROSTER 로 이것만 쓴다")
    a = ap.parse_args()

    # 명부를 만드는 중에는 명부를 읽지 않는다 -- 어제 것으로 오늘을 재게 된다.
    if a.roster:
        llm_pool.ROSTER = ""
    pool = llm_pool.build_pool()
    if not pool:
        print("후보가 없다 -- GEMINI_API_KEY 를 확인해라", file=sys.stderr)
        return 1

    keys = {llm_pool._key_of(lb) for lb, _ in pool}
    print(f"후보 {len(pool)}개 · 키 {len(keys)}개 · 프롬프트 {len(a.prompt)}자")
    print("-" * 68)

    t0 = time.time()
    if a.parallel:
        with cf.ThreadPoolExecutor(max_workers=len(pool)) as ex:
            rows = list(ex.map(lambda c: probe_one(c[0], c[1], a.prompt), pool))
    else:
        rows = [probe_one(lb, llm, a.prompt) for lb, llm in pool]

    for r in sorted(rows, key=lambda r: (not r["ok"], r["sec"])):
        print(f"  {'O' if r['ok'] else 'X'} {r['label']:44} "
              f"{r['sec']:5.1f}s  {r['note']}")

    live = [r for r in rows if r["ok"]]
    print("-" * 68)
    print(f"살아 있는 후보 {len(live)}/{len(rows)} · 총 {time.time() - t0:.1f}초"
          f"{' (동시)' if a.parallel else ' (차례로)'}")
    if live:
        best = min(live, key=lambda r: r["sec"])
        print(f"제일 빠른 것: {best['label']} ({best['sec']:.1f}s)")
    else:
        print("전부 실패했다. 갈래를 보고 무엇을 고칠지 정해라 -- "
              "RPM 이면 기다리면 되고, 일일소진이면 내일이고, 영구면 모델 이름이다.")
    if a.roster:
        # **답한 것만 적는다.** 전부 실패했으면 안 쓴다 -- 빈 명부는 런을 죽이고,
        # 그때는 명부가 없는 편이(전 후보로 도는 편이) 낫다.
        if live:
            import json
            Path(a.roster).parent.mkdir(parents=True, exist_ok=True)
            Path(a.roster).write_text(json.dumps(
                {"at": time.time(),
                 "live": [{"label": r["label"], "sec": round(r["sec"], 2)}
                          for r in sorted(live, key=lambda r: r["sec"])]},
                ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"명부에 {len(live)}개를 적었다 -> {a.roster}")
        else:
            print("답한 후보가 없어 명부를 쓰지 않는다 -- 런은 전 후보로 돈다")
    return 0 if live else 1


if __name__ == "__main__":
    raise SystemExit(main())
