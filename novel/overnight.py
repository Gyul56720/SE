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
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import drive as D                                          # noqa: E402
from novel.state import Novel                                         # noqa: E402
from novel.world_romance import build, OUTCOMES                       # noqa: E402


# 로그 시각은 **한국 시간(KST)** 으로 찍는다. 인스턴스가 UTC 라 time.strftime 이
# 그대로 UTC 를 냈는데, 밤새 돌려놓고 아침에 읽는 로그가 9시간 어긋나 있으면 "언제
# 멈췄나" 를 매번 암산해야 한다.
#
# ZoneInfo("Asia/Seoul") 대신 고정 +09:00 을 쓴다. 한국은 1988년 이후 서머타임이 없어
# 고정 오프셋이 정확하고, tzdata 패키지가 없는 최소 이미지에서도 실패하지 않는다.
#
# 접미사 KST 를 붙인다. 이 로그 파일에는 이미 UTC 로 찍힌 줄이 남아 있어서, 표시가
# 없으면 중간에 시각이 9시간 뛴 것처럼 보인다.
KST = timezone(timedelta(hours=9))


def _now() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")


class Discord:
    """진행 상황을 Discord 로 보낸다. **봇 게이트웨이를 띄우지 않고 REST 로만** 쏜다.

    discord.py 로 로그인하면 이 스크립트가 봇이 되어 버리고, 이미 도는 봇과 세션이 겹친다.
    알림 하나 보내자고 그럴 이유가 없다 -- 채널 메시지 전송은 POST 한 방이면 된다.

    씬마다 보내면 밤새 수백 개가 쌓인다. **에피소드 단위로만** 보내고, 오래 조용하면
    하트비트를 한 번 낸다(살아 있는지 아침에 알 수 있게).

    실패해도 런을 죽이지 않는다. 알림은 관측이지 목적이 아니다.
    웹훅/토큰은 절대 로그에 찍지 않는다."""

    API = "https://discord.com/api/v10/channels/{cid}/messages"

    def __init__(self, token: str = None, channel_id: str = None,
                 webhook: str = None, heartbeat: float = 2400.0):
        import os
        self.token = token or os.environ.get("DISCORD_BOT_TOKEN") or ""
        self.channel = str(channel_id or os.environ.get("DISCORD_CHANNEL_ID") or "")
        self.webhook = webhook or os.environ.get("DISCORD_WEBHOOK_URL") or ""
        self.heartbeat = heartbeat
        self.last = time.time()
        self.on = bool(self.webhook or (self.token and self.channel))
        self.sent, self.failed = 0, 0

    def send(self, text: str) -> bool:
        if not self.on or not text:
            return False
        import json as _json
        import urllib.error
        import urllib.request
        body = _json.dumps({"content": text[:1900]}).encode()
        if self.webhook:
            url, headers = self.webhook, {"Content-Type": "application/json"}
        else:
            url = self.API.format(cid=self.channel)
            headers = {"Content-Type": "application/json",
                       "Authorization": f"Bot {self.token}"}
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=20):
                pass
            self.sent += 1
            self.last = time.time()
            return True
        except Exception as e:                                        # noqa: BLE001
            # **에러 본문에 토큰이 실릴 수 있다.** 종류와 코드만 남긴다.
            self.failed += 1
            code = getattr(e, "code", "")
            D._log(f"[{_now()}] Discord 전송 실패 ({type(e).__name__} {code})")
            return False

    def beat(self, text: str) -> None:
        """오래 조용했으면 한 번 보낸다. 살아 있다는 신호."""
        if self.on and time.time() - self.last > self.heartbeat:
            self.send(text)


class Director:
    """claude -p 를 쓰되, 실패하면 Gemini 로 내려가고 나중에 **싸게** 다시 올라온다.

    처음 설계는 30분마다 강등을 풀고 streak 를 0 으로 되돌렸다. 계산해보니 그게 밤을 먹는다:
    풀린 뒤 다시 강등되려면 3번 실패해야 하고, 실패가 타임아웃이면 한 번에 300초다.
    30분 주기 x 3회 x 300초 = **7시간 중 3.5시간이 타임아웃 대기로만 소모된다.**

    그래서 재시도를 **탐침 한 번**으로 바꿨다:
      · 강등 중에는 짧은 타임아웃(probe_timeout)으로 딱 한 번만 두드린다
      · 성공하면 복귀. 실패하면 그대로 강등 유지하고 **간격을 두 배로** 늘린다
      · 낭비의 상한이 사이클당 probe_timeout 하나로 묶인다 (7시간에 수 분)

    한 번 실패로 영영 내려가지도 않는다 -- 구독 한도는 자정을 넘겨 리셋될 수 있다."""

    def __init__(self, fall_after: int = 3, retry_after: float = 1800.0,
                 timeout: float = 300.0, probe_timeout: float = 45.0,
                 max_retry_after: float = 7200.0):
        self.primary = D.claude_code_llm(timeout=timeout)
        self.probe = D.claude_code_llm(timeout=probe_timeout)
        self.fall_after = fall_after
        self.retry_after, self.max_retry_after = retry_after, max_retry_after
        self.streak, self.demoted_at = 0, None
        self.stats = {"primary": 0, "fallback": 0, "fail": 0, "probe": 0}

    def _try_recover(self) -> bool:
        """탐침 한 번. 성공하면 복귀, 실패하면 간격을 늘리고 강등 유지."""
        self.stats["probe"] += 1
        try:
            self.probe('JSON 하나만 출력하라. 설명 금지. {"ok": true}')
            D._log(f"[{_now()}] 디렉터 복귀 -- claude -p 가 다시 응답한다")
            self.demoted_at, self.streak = None, 0
            self.retry_after = min(self.retry_after, self.max_retry_after)
            return True
        except Exception as e:                                        # noqa: BLE001
            self.retry_after = min(self.retry_after * 2, self.max_retry_after)
            self.demoted_at = time.time()
            D._log(f"[{_now()}] 탐침 실패 -- 강등 유지, 다음 시도 "
                   f"{self.retry_after / 60:.0f}분 뒤 ({str(e).splitlines()[0][:90]})")
            return False

    def __call__(self, prompt: str) -> str:
        if self.demoted_at and time.time() - self.demoted_at > self.retry_after:
            if not self._try_recover():
                self.stats["fallback"] += 1
                return D.default_llm(prompt)
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
                           f"({self.retry_after / 60:.0f}분 뒤 탐침)")
        self.stats["fallback"] += 1
        return D.default_llm(prompt)


def main() -> int:
    ap = argparse.ArgumentParser(description="야간 소설 러너")
    ap.add_argument("--hours", type=float, default=7.0)
    ap.add_argument("--path", default="novel/romance.json")
    ap.add_argument("--max-repairs", type=int, default=3)
    ap.add_argument("--gemini-director", action="store_true",
                    help="claude -p 를 쓰지 않고 처음부터 Gemini 로")
    ap.add_argument("--all-claude", action="store_true",
                    help="배우·화자·추출기까지 전부 claude -p 로. Gemini 쿼터가 말랐을 때 "
                         "쓴다 -- Max 구독으로 청구되므로 API 크레딧이 필요 없다. "
                         "호출마다 프로세스를 띄우므로 느리다(한 회차 정도에 알맞다)")
    ap.add_argument("--discord", action="store_true",
                    help="진행 상황을 Discord 로 보낸다 (DISCORD_BOT_TOKEN + "
                         "DISCORD_CHANNEL_ID 또는 DISCORD_WEBHOOK_URL)")
    ap.add_argument("--no-discord", action="store_true")
    ap.add_argument("--upto-episode", type=int, default=0,
                    help="여기까지의 회차만 산문을 채운다 (0 = 전부). 1 이면 1화만 -- "
                         "산문이 실제로 나오는지 가장 빨리 확인하는 방법이다")
    ap.add_argument("--blocks", type=int, default=0,
                    help="결말 블록을 몇 개까지 처리하고 멈출 것인가 (0 = 전부). "
                         "1 이면 1~10화만 끝내고 종료한다 -- 밤을 걸기 전에 한 블록으로 "
                         "실제로 산문이 나오는지 보는 데 쓴다")
    ap.add_argument("--skip-blocked", type=int, default=999,
                    help="관문에 막힌 씬을 몇 개까지 넘어갈 것인가. 야간 런은 넘어가는 "
                         "쪽이 맞다 -- 씬 하나 때문에 회차 전체가 서면 밤이 날아간다")
    ap.add_argument("--episode-minutes", type=float, default=75.0,
                    help="에피소드 하나에 허용할 벽시계(분). 넘기면 그 편을 접고 다음으로 "
                         "간다 -- 한 편이 밤을 다 먹지 않게")
    a = ap.parse_args()

    deadline = time.time() + a.hours * 3600
    path = Path(a.path)
    log = path.with_suffix(".scenes.jsonl")
    report = path.with_suffix(".overnight.json")

    novel = Novel.load(path) if path.exists() else build()
    director = None if a.gemini_director else Director()
    if a.all_claude:
        # **한 콜러블로 모든 역할을 덮는다.** _llm_for 는 역할이 없으면 "default" 로
        # 물러서므로 director/actor/narrator/extractor 가 전부 이것을 쓴다.
        # Director 래퍼(강등·탐침)는 쓰지 않는다 -- 내려갈 Gemini 가 없는 상황이라
        # 강등이 곧 실패다. 실패하면 사실대로 실패하는 편이 낫다.
        director = None
        llm = {"default": D.claude_code_llm(timeout=300)}
    elif a.gemini_director:
        llm = D.default_llm
    else:
        llm = {"director": director}

    dc = Discord() if (a.discord and not a.no_discord) else Discord(token="", channel_id="",
                                                                    webhook="")
    if a.discord and not dc.on:
        D._log(f"[{_now()}] Discord 알림을 켰지만 토큰/채널이 없다 -- 로그로만 남긴다")

    D._log(f"[{_now()}] 시작 -- 예산 {a.hours}시간, 목표 {len(OUTCOMES)}개 에피소드")
    dc.send(f"🌙 **야간 소설 런 시작** ({_now()})\n"
            f"예산 {a.hours}시간 · 목표 {len(OUTCOMES)}편 · "
            f"디렉터 {'claude -p (전 역할)' if a.all_claude else ('Gemini' if a.gemini_director else 'claude -p')}\n"
            f"기존 씬 {len(novel.scenes)}개")
    D._log(f"[{_now()}] 기존 씬 {len(novel.scenes)}개 "
           f"(verified {sum(1 for s in novel.scenes if s.status == 'verified')})")

    done, failed = [], []
    worked = 0                      # 실제로 손댄 블록 수 (건너뛴 것은 세지 않는다)
    for spec in OUTCOMES:
        if a.blocks and worked >= a.blocks:
            D._log(f"[{_now()}] 블록 {a.blocks}개를 처리했다 -- 여기서 멈춘다")
            break
        if time.time() > deadline:
            D._log(f"[{_now()}] 예산 소진 -- 여기서 멈춘다")
            break
        tag = f"ep{spec['eps'][0]:03d}_"
        have = [s for s in novel.scenes if s.id.startswith(tag)]
        # **조립된 것과 완성된 것은 다르다.** 예전에는 씬이 하나라도 있으면 블록 전체를
        # 건너뛰었는데, 조립만 되고 산문 단계에서 죽은 블록이 바로 그 상태다 -- 다시
        # 띄워도 영원히 건너뛰어져 한 글자도 안 채워진다(2026-09-03 밤샘 런의 1~10화가
        # 정확히 그랬다: 30씬 전부 pending 인 채로 다음 실행에서도 건너뛰어질 참이었다).
        # 다 끝난 블록만 건너뛰고, 조립만 된 블록은 **조립을 건너뛰고 산문부터** 채운다.
        if have and all(s.status == "verified" for s in have):
            continue
        dc.beat(f"⏳ 아직 도는 중 ({_now()}) · 씬 {len(novel.scenes)}개 · "
                f"남은 예산 {(deadline - time.time()) / 3600:.1f}시간")

        lo, hi = spec["eps"]
        worked += 1
        D._log(f"\n[{_now()}] === {lo}~{hi}화 조립 시작 ===")
        t0 = time.time()
        # **한 편이 밤을 다 먹지 못하게 한다.** 디렉터 호출이 느리면(타임아웃 직전에서
        # 겨우 성공하는 경우) 에피소드 하나가 다섯 시간을 먹을 수 있다 -- 척추 최악 40회 +
        # 서브플롯 20회이므로. 남은 예산과 이 상한 중 작은 쪽으로 자른다.
        ep_deadline = min(time.time() + a.episode_minutes * 60, deadline)
        D.EPISODE_DEADLINE = ep_deadline
        try:
            if have:
                D._log(f"[{_now()}] {lo}~{hi}화 는 이미 조립돼 있다 "
                       f"({len(have)}씬) -- 산문부터 채운다")
            else:
                novel.scenes.extend(D.build_episode(novel, spec, llm, a.max_repairs, log))
                novel.save(path)
            # **막힌 씬 하나가 열다섯 화를 세우지 않게 한다.** 자는 동안에는 사람이
            # 풀어줄 수 없으므로 넘어가고 아침에 본다.
            r = D.drive(novel, str(path), llm=llm, max_repairs=a.max_repairs, log=log,
                        skip_blocked=a.skip_blocked, upto_episode=a.upto_episode)
            # **여기가 요점: 실패해도 다음 에피소드로 간다.** 자는 동안 break 하면
            # 남은 시간이 통째로 낭비된다.
            (done if r["status"] == "done" else failed).append(
                {"eps": [lo, hi], **r, "seconds": round(time.time() - t0)})
            D._log(f"[{_now()}] {lo}~{hi}화 {r['status']} "
                   f"(verified {r['verified']}, {time.time() - t0:.0f}초)")
            chars = sum(len(s.prose or "") for s in novel.scenes
                        if lo <= s.episode <= hi)
            mark = "✅" if r["status"] == "done" else "⚠️"
            dc.send(f"{mark} **{lo}~{hi}화** {r['status']} · "
                    f"verified {r['verified']} · {chars:,}자 · "
                    f"{(time.time() - t0) / 60:.0f}분\n"
                    f"남은 예산 {(deadline - time.time()) / 3600:.1f}시간")
        except Exception as e:                                        # noqa: BLE001
            failed.append({"eps": [lo, hi], "status": "error",
                           "error": f"{type(e).__name__}: {e}",
                           "seconds": round(time.time() - t0)})
            D._log(f"[{_now()}] {lo}~{hi}화 예외 -- 다음으로 넘어간다\n"
                   f"{traceback.format_exc()[-800:]}")
            dc.send(f"❌ **{lo}~{hi}화 예외** -- 다음 편으로 넘어간다\n"
                    f"```{type(e).__name__}: {str(e)[:300]}```")
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
        "director": (director.stats if director
                     else ("claude -p (전 역할)" if a.all_claude else "gemini")),
    }
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    D._log(f"\n[{_now()}] === 끝 ===")
    D._log(f"  에피소드 성공 {len(done)} / 실패 {len(failed)}")
    D._log(f"  씬 {len(novel.scenes)}개 중 verified {ver} / 총 {chars:,}자")
    if director:
        D._log(f"  디렉터: claude -p {director.stats['primary']}회 / "
               f"Gemini 폴백 {director.stats['fallback']}회 / 실패 {director.stats['fail']}회")
    D._log(f"  요약: {report}")
    dstat = (f"claude -p {director.stats['primary']} / Gemini {director.stats['fallback']} / "
             f"실패 {director.stats['fail']}") if director else (
                 "claude -p 전용 (전 역할)" if a.all_claude else "Gemini 전용")
    dc.send(f"🌅 **야간 런 종료** ({_now()})\n"
            f"성공 {len(done)}편 · 실패 {len(failed)}편\n"
            f"씬 {len(novel.scenes)}개 (verified {ver}) · **{chars:,}자**\n"
            f"디렉터: {dstat}\n"
            f"요약 파일: `{report}`")
    if dc.on:
        D._log(f"  Discord: 보냄 {dc.sent} / 실패 {dc.failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
