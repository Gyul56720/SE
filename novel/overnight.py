"""야간 러너 -- 몇 시간을 혼자 버틴다.

drive_novel 은 한 에피소드가 막히면 break 한다. 사람이 지켜보고 있을 때는 그게 맞다 --
막힌 것을 보고 고치면 되니까. 하지만 자는 동안에는 그 break 하나가 밤을 통째로 날린다.

여기서 다르게 하는 것:
  · **에피소드 실패가 런을 죽이지 않는다.** 기록하고 다음으로 간다
  · **디렉터 폴백 사슬.** claude -p 가 연속 실패하면 Gemini 로 내려간다. 구독 한도는
    자정 넘어 리셋될 수도 있으므로, 내려간 뒤에도 주기적으로 위를 다시 두드린다
  · **벽시계 예산.** --hours 를 넘기면 진행 중인 에피소드를 끝내고 멈춘다
  · **아침에 읽을 요약.** 무엇이 됐고 무엇이 막혔는지 한 파일에

재개는 공짜다. novel.json 이 있으면 편 에피소드와 verified 씬을 건너뛴다.

    setsid nohup python3 novel/overnight.py --hours 7 \\
        > logs/overnight.log 2>&1 < /dev/null & disown
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import drive as D                                          # noqa: E402
from novel.state import Novel                                         # noqa: E402
from novel.world_romance import build, OUTCOMES                       # noqa: E402


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


class Director:
    """claude -p 를 쓰되, 연속 실패하면 Gemini 로 내려가고 나중에 다시 올라온다.

    한 번 실패했다고 영영 내려가면 자정 리셋을 못 쓰고, 매번 다시 시도하면 실패에 시간을
    다 쓴다. 그래서 연속 실패 수로 내려가고 시간으로 올라온다."""

    def __init__(self, fall_after: int = 3, retry_after: float = 1800.0):
        self.primary = D.claude_code_llm(timeout=300)
        self.fall_after, self.retry_after = fall_after, retry_after
        self.streak, self.demoted_at = 0, None
        self.stats = {"primary": 0, "fallback": 0, "fail": 0}

    def __call__(self, prompt: str) -> str:
        if self.demoted_at and time.time() - self.demoted_at > self.retry_after:
            D._log(f"[{_now()}] 디렉터: claude -p 를 다시 시도한다")
            self.demoted_at, self.streak = None, 0
        if self.demoted_at is None:
            try:
                out = self.primary(prompt)
                self.streak = 0
                self.stats["primary"] += 1
                return out
            except Exception as e:                                    # noqa: BLE001
                self.streak += 1
                self.stats["fail"] += 1
                D._log(f"[{_now()}] claude -p 실패 {self.streak}/{self.fall_after}: "
                       f"{str(e).splitlines()[0][:140]}")
                if self.streak >= self.fall_after:
                    self.demoted_at = time.time()
                    D._log(f"[{_now()}] 디렉터를 Gemini 로 내린다 "
                           f"({self.retry_after / 60:.0f}분 뒤 재시도)")
        self.stats["fallback"] += 1
        return D.default_llm(prompt)


def main() -> int:
    ap = argparse.ArgumentParser(description="야간 소설 러너")
    ap.add_argument("--hours", type=float, default=7.0)
    ap.add_argument("--path", default="novel/romance.json")
    ap.add_argument("--max-repairs", type=int, default=3)
    ap.add_argument("--gemini-director", action="store_true",
                    help="claude -p 를 쓰지 않고 처음부터 Gemini 로")
    a = ap.parse_args()

    deadline = time.time() + a.hours * 3600
    path = Path(a.path)
    log = path.with_suffix(".scenes.jsonl")
    report = path.with_suffix(".overnight.json")

    novel = Novel.load(path) if path.exists() else build()
    director = None if a.gemini_director else Director()
    llm = D.default_llm if a.gemini_director else {"director": director}

    D._log(f"[{_now()}] 시작 -- 예산 {a.hours}시간, 목표 {len(OUTCOMES)}개 에피소드")
    D._log(f"[{_now()}] 기존 씬 {len(novel.scenes)}개 "
           f"(verified {sum(1 for s in novel.scenes if s.status == 'verified')})")

    done, failed = [], []
    for spec in OUTCOMES:
        if time.time() > deadline:
            D._log(f"[{_now()}] 예산 소진 -- 여기서 멈춘다")
            break
        tag = f"ep{spec['eps'][0]:03d}_"
        if any(s.id.startswith(tag) for s in novel.scenes):
            continue

        lo, hi = spec["eps"]
        D._log(f"\n[{_now()}] === {lo}~{hi}화 조립 시작 ===")
        t0 = time.time()
        try:
            novel.scenes.extend(D.build_episode(novel, spec, llm, a.max_repairs, log))
            novel.save(path)
            r = D.drive(novel, str(path), llm=llm, max_repairs=a.max_repairs, log=log)
            # **여기가 요점: 실패해도 다음 에피소드로 간다.** 자는 동안 break 하면
            # 남은 시간이 통째로 낭비된다.
            (done if r["status"] == "done" else failed).append(
                {"eps": [lo, hi], **r, "seconds": round(time.time() - t0)})
            D._log(f"[{_now()}] {lo}~{hi}화 {r['status']} "
                   f"(verified {r['verified']}, {time.time() - t0:.0f}초)")
        except Exception as e:                                        # noqa: BLE001
            failed.append({"eps": [lo, hi], "status": "error",
                           "error": f"{type(e).__name__}: {e}",
                           "seconds": round(time.time() - t0)})
            D._log(f"[{_now()}] {lo}~{hi}화 예외 -- 다음으로 넘어간다\n"
                   f"{traceback.format_exc()[-800:]}")
            try:
                novel.save(path)
            except Exception:                                         # noqa: BLE001
                pass

    ver = sum(1 for s in novel.scenes if s.status == "verified")
    chars = sum(len(s.prose or "") for s in novel.scenes)
    summary = {
        "finished_at": _now(), "hours_budget": a.hours,
        "episodes_done": done, "episodes_failed": failed,
        "scenes_total": len(novel.scenes), "scenes_verified": ver,
        "chars_total": chars,
        "director": director.stats if director else "gemini",
    }
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    D._log(f"\n[{_now()}] === 끝 ===")
    D._log(f"  에피소드 성공 {len(done)} / 실패 {len(failed)}")
    D._log(f"  씬 {len(novel.scenes)}개 중 verified {ver} / 총 {chars:,}자")
    if director:
        D._log(f"  디렉터: claude -p {director.stats['primary']}회 / "
               f"Gemini 폴백 {director.stats['fallback']}회 / 실패 {director.stats['fail']}회")
    D._log(f"  요약: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
