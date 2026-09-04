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


HERE = Path(__file__).resolve().parent


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
        if self.webhook and not self.webhook.startswith(("http://", "https://")):
            D._log(f"[{_now()}] DISCORD_WEBHOOK_URL 이 URL 이 아니다 -- 무시한다")
            self.webhook = ""
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
        try:
            # **Request 생성도 try 안에 둔다.** 잘못된 URL 은 urlopen 이 아니라 여기서
            # ValueError 를 낸다("unknown url type"). 밖에 두면 환경변수 오타 하나가
            # 런을 죽인다 -- 알림 때문에 소설이 멈추는 것은 앞뒤가 바뀐 것이다.
            req = urllib.request.Request(url, data=body, headers=headers,
                                         method="POST")
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


def _refuse_if_running(path: Path) -> None:
    """이미 도는 런이 있으면 시작하지 않는다.

    두 벌이 같은 romance.json 을 쓰면 **서로를 덮어쓴다.** 각자 메모리에 든 Novel 을
    통째로 저장하므로, 나중에 저장한 쪽이 상대가 채운 산문을 통째로 지운다. 밖에서는
    "산문이 0자인데 end:done 이 찍혔다" 처럼 앞뒤가 안 맞는 상태로만 보인다(실측
    2026-09-04: 씬 수가 줄었다 늘었다 하고 조립이 --blocks 1 을 넘어 다음 블록까지 갔다).

    CLAUDE.md 에 사람이 조심하라고 적어뒀지만, 조심으로 막을 일이 아니다 -- 재시작할
    때마다 매번 확인해야 하고 한 번 놓치면 그동안 쓴 것이 사라진다. 여기서 막는다.

    PID 파일이 아니라 pgrep 을 쓴다. PID 파일은 kill -9 나 재부팅 뒤에 남아서 멀쩡한
    시작을 막는데, pgrep 은 실제로 도는 것만 본다."""
    import os
    import subprocess
    me = os.getpid()
    try:
        r = subprocess.run(["pgrep", "-af", "overnight.py"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return                      # pgrep 이 없으면 막지 않는다. 검사가 실행을 막으면 안 된다
    others = []
    for line in r.stdout.splitlines():
        pid, _, cmd = line.partition(" ")
        if not pid.isdigit() or int(pid) in (me, os.getppid()):
            continue
        # 자기 이름을 품은 것들을 걸러낸다. pgrep -af 는 명령줄 전체를 훑으므로
        # tests/test_overnight.py 도 "overnight.py" 로 잡힌다 -- 검사 스위트를 돌리는
        # 것만으로 진짜 실행이 막힌다(실측). 감시기와 편집기도 마찬가지다.
        if any(x in cmd for x in ("pgrep", "test_overnight", "watch.py",
                                  "vim ", "nano ", "less ", "tail ")):
            continue
        others.append(line)
    if not others:
        return
    D._log("이미 도는 런이 있다 -- 시작하지 않는다. 두 벌이 같은 원고를 쓰면 "
           "나중에 저장한 쪽이 상대가 쓴 산문을 통째로 지운다.")
    for line in others:
        D._log(f"  {line}")
    D._log("  정리:  kill <위 PID>   (pkill -f 는 자기 셸까지 죽인다)")
    D._log("  그래도 띄우려면:  --allow-concurrent")
    raise SystemExit(2)


def refuse_seed_mismatch(novel, seed_id: str, path) -> str:
    """이어받은 원고가 지금 씨앗의 것인가. 아니면 멈출 이유를 돌려준다(빈 문자열이면 정상).

    실측 2026-09-04: `--restart` 는 돌던 런을 죽이고 **새 씨앗을 뽑는데**, overnight 은
    seeded.json 이 있으면 그것을 이어받는다. 그래서 옛 인물이 든 원고 위에 새 세계의
    결말이 얹혔다 -- 등장인물 목록에 없는 이름이 척추에 들어가고, V001 이 매 씬을
    기각하며, 밤이 통째로 날아간다.

    조용히 굴러가면 아침에야 안다. 여기서 멈추고 무엇을 하면 되는지 말해준다."""
    if not seed_id or not getattr(novel, "seed_id", ""):
        return ""                       # 옛 원고(표식 없음)는 막지 않는다
    if novel.seed_id == seed_id:
        return ""
    return (f"원고와 씨앗이 다르다.\n"
            f"  원고({path}) 의 씨앗: {novel.seed_id}\n"
            f"  지금 씨앗           : {seed_id}\n"
            f"  새 씨앗으로 새로 쓰려면 옛 원고를 치워라:\n"
            f"    mv {path} {path}.$(date +%Y%m%d-%H%M%S).bak\n"
            f"  옛 원고를 이어 쓰려면 그 씨앗을 되살려라(--keep 로 시작했어야 한다).")


def main() -> int:
    ap = argparse.ArgumentParser(description="야간 소설 러너")
    ap.add_argument("--hours", type=float, default=7.0)
    ap.add_argument("--world", default="romance",
                    choices=("romance", "probe", "seeded"),
                    help="probe 는 3화짜리 최소 세계. seeded 는 novel/seed.py 가 "
                         "뽑은 씨앗을 편 세계다(먼저 world_seeded.py --new)")
    ap.add_argument("--path", default="",
                    help="원고 경로. 비우면 세계마다 다른 기본값을 쓴다 -- "
                         "탐침과 본편이 같은 파일을 쓰면 서로를 덮어쓴다")
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
    ap.add_argument("--persona", default="cider",
                    help="문체 페르소나(novel/style.py). cider = 웹소설 사이다(기본), "
                         "hardboiled = 하드보일드 마술적 리얼리즘")
    ap.add_argument("--freewrite", action="store_true",
                    help="자유 집필 -- 배우 턴을 거치지 않고 화자가 **회차를 통째로** 쓴다. "
                         "분량 할당량(씬당 1,666자)이 곧 희석 지시라, 회차를 주면 화자가 "
                         "어디를 늘리고 자를지 스스로 정한다. 호출도 회차당 18 -> 2~3 으로 "
                         "준다. 대신 턴 기반 관문(V001·V011)은 검사할 대상이 없어진다")
    ap.add_argument("--rounds", type=int, default=3,
                    help="막힌 씬을 몇 바퀴까지 다시 도는가. 1 이면 예전 그대로 한 바퀴. "
                         "실패는 결정론적이지 않다 -- 디렉터·배우·화자를 새로 뽑으면 "
                         "다음 바퀴에 통과하는 일이 흔하다(실측: 12씬 중 3씬이 막힌 채 "
                         "예산 다섯 시간을 남기고 런이 끝났다)")
    ap.add_argument("--skip-blocked", type=int, default=999,
                    help="관문에 막힌 씬을 몇 개까지 넘어갈 것인가. 야간 런은 넘어가는 "
                         "쪽이 맞다 -- 씬 하나 때문에 회차 전체가 서면 밤이 날아간다")
    ap.add_argument("--episode-minutes", type=float, default=75.0,
                    help="에피소드 하나에 허용할 벽시계(분). 넘기면 그 편을 접고 다음으로 "
                         "간다 -- 한 편이 밤을 다 먹지 않게")
    ap.add_argument("--allow-concurrent", action="store_true",
                    help="이미 도는 런이 있어도 시작한다. **원고가 서로 덮어써진다** -- "
                         "다른 원고 파일(--path)을 쓸 때만 안전하다")
    a = ap.parse_args()

    from novel import style
    style.use(a.persona)          # 모르는 이름이면 여기서 죽는다 -- 조용히 기본값으로
                                  # 물러서면 엉뚱한 문체로 몇 시간을 쓰고도 아무도 모른다
    D._log(f"[{_now()}] 페르소나: {a.persona} -- {style.P()['label']}")

    sd = None
    global OUTCOMES, build
    if a.world == "probe":
        from novel import world_probe
        OUTCOMES, build = world_probe.OUTCOMES, world_probe.build
    elif a.world == "seeded":
        from novel import world_seeded
        sd = world_seeded.load_seed()
        OUTCOMES, build = world_seeded.outcomes(sd), (lambda: world_seeded.build(sd))
        D._log(f"[{_now()}] 씨앗 {sd['id']} -- {world_seeded.S.title_hint(sd)}")

    deadline = time.time() + a.hours * 3600
    # 세계마다 다른 파일. 같은 파일을 쓰면 탐침 한 번이 본편 원고를 지운다.
    path = Path(a.path or (HERE / {"probe": "probe.json",
                                   "seeded": "seeded.json"}.get(a.world,
                                                               "romance.json")))
    log = path.with_suffix(".scenes.jsonl")
    report = path.with_suffix(".overnight.json")

    if not a.allow_concurrent:
        _refuse_if_running(path)
    novel = Novel.load(path) if path.exists() else build()
    # **이어받은 원고가 지금 씨앗의 것인지 먼저 본다.** 아니면 여기서 멈춘다 --
    # 섞인 채로 굴리면 밤이 통째로 날아가고 아침에야 안다.
    if a.world == "seeded":
        why = refuse_seed_mismatch(novel, (sd or {}).get("id", ""), path)
        if why:
            D._log(f"[{_now()}] 시작하지 않는다 -- {why}")
            return 1
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
                        skip_blocked=a.skip_blocked, upto_episode=a.upto_episode,
                        rounds=a.rounds, freewrite=a.freewrite)
            # **여기가 요점: 실패해도 다음 에피소드로 간다.** 자는 동안 break 하면
            # 남은 시간이 통째로 낭비된다.
            (done if r["status"] == "done" else failed).append(
                {"eps": [lo, hi], **r, "seconds": round(time.time() - t0)})
            D._log(f"[{_now()}] {lo}~{hi}화 {r['status']} "
                   f"(verified {r['verified']}, {time.time() - t0:.0f}초)")
            for b in (r.get("blocked") or [])[:6]:
                D._log(f"    막힘 {b['id']} ({b['episode']}화): {b['why']}")
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

    # ------------------------------------------------------------ 마무리 루프
    # **예산이 남아 있는데 미완인 씬이 있으면 계속 돈다.**
    #
    # 블록 루프는 블록을 한 번씩만 지나간다. 그래서 앞 블록에서 막힌 씬은 뒤 블록이 도는
    # 동안 그대로 남고, 블록이 다 끝나면 예산이 몇 시간 남아도 런이 끝났다(실측: 12씬 중
    # 3씬이 막힌 채 220초 만에 종료). drive(rounds=) 가 한 호출 안에서 세 바퀴를 돌지만
    # 그것도 그 호출 안에서만이다.
    #
    # 여기서는 **남은 예산을 다 쓸 때까지** 다시 돈다. 한 바퀴에 아무것도 못 고치면
    # 멈춘다 -- 진전 없이 같은 실패를 무한 반복하는 것은 예산을 태우는 것일 뿐이다.
    sweep = 0
    while time.time() < deadline:
        # **조립조차 안 된 블록이 있으면 먼저 조립한다.** 블록 루프가 예산이나 예외로
        # 건너뛴 블록은 씬이 하나도 없어서 아래 drive 가 채울 대상 자체를 못 갖는다 --
        # 그러면 "미완 0씬" 으로 보이고 10화 중 6화만 쓴 채 끝난다.
        for spec in (OUTCOMES[:a.blocks] if a.blocks else OUTCOMES):
            tag = f"ep{spec['eps'][0]:03d}_"
            if any(sc.id.startswith(tag) for sc in novel.scenes):
                continue
            if time.time() >= deadline:
                break
            D._log(f"[{_now()}] 마무리: {spec['eps'][0]}~{spec['eps'][1]}화 가 "
                   f"조립조차 안 됐다 -- 지금 조립한다")
            D.EPISODE_DEADLINE = deadline
            try:
                novel.scenes.extend(D.build_episode(novel, spec, llm, a.max_repairs, log))
                novel.save(path)
            except Exception:                                         # noqa: BLE001
                D._log(f"[{_now()}] 마무리 조립 실패 -- 넘어간다\n"
                       f"{traceback.format_exc()[-400:]}")

        left = [sc for sc in novel.scenes
                if sc.status != "verified"
                and not (a.upto_episode and sc.episode > a.upto_episode)]
        if not left:
            break
        sweep += 1
        D.EPISODE_DEADLINE = deadline          # 마무리에서는 회차 상한을 걸지 않는다
        D._log(f"\n[{_now()}] === 마무리 {sweep}회차 -- 미완 {len(left)}씬 "
               f"(남은 예산 {(deadline - time.time()) / 3600:.1f}시간) ===")
        before = sum(1 for sc in novel.scenes if sc.status == "verified")
        try:
            r = D.drive(novel, str(path), llm=llm, max_repairs=a.max_repairs, log=log,
                        skip_blocked=a.skip_blocked, upto_episode=a.upto_episode,
                        rounds=a.rounds, freewrite=a.freewrite)
        except Exception as e:                                        # noqa: BLE001
            D._log(f"[{_now()}] 마무리 {sweep}회차 예외 -- 멈춘다\n"
                   f"{traceback.format_exc()[-500:]}")
            break
        gained = sum(1 for sc in novel.scenes if sc.status == "verified") - before
        D._log(f"[{_now()}] 마무리 {sweep}회차: {r['status']} · 이번에 {gained}씬 채움")
        try:
            novel.save(path)
        except Exception:                                             # noqa: BLE001
            pass
        if gained <= 0:
            D._log(f"[{_now()}] 진전이 없다 -- 마무리를 멈춘다 "
                   f"(같은 실패를 반복하는 것은 예산을 태우는 것일 뿐이다)")
            break

    ver = sum(1 for s in novel.scenes if s.status == "verified")
    chars = sum(len(s.prose or "") for s in novel.scenes)
    stuck = [{"id": s.id, "episode": s.episode, "why": (s.violations or [""])[0][:160]}
             for s in novel.scenes if s.status == "failed"]
    summary = {
        "blocked_scenes": stuck,
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
    if stuck:
        D._log(f"  막힌 씬 {len(stuck)}개 -- 같은 명령을 다시 돌리면 이어서 채운다:")
        for b in stuck[:8]:
            D._log(f"    {b['id']} ({b['episode']}화): {b['why']}")
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
