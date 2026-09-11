"""mailer(메일 도구)와 keys(!열쇠)를 **가짜 SMTP** 로 끝까지 돌려 붙든다.

실측 2026-09-11: 메일 부탁에 에이전트가 (1) 발급 절차·코드를 설명하고 멈췄고, (2) '인프라
없음' 으로 멈췄고, (3) 선택지를 나열했다. 사람이 원한 것은 "필요한 것만 묻고 나머지는
알아서" 다. 그래서 붙드는 것:
(1) 수단이 없으면 보내기가 **무엇이 없고 어떻게 주는지**(`!열쇠 이름=값`)를 돌려준다 --
    선택지가 아니라 한 길, (2) !열쇠 가 .env 에 적고 os.environ 에 올리며 값은 어디에도
    되비치지 않는다(답 · 예외 글), (3) 받으면 같은 호출이 바로 나간다 -- 로그인·헤더·본문,
    (4) 인증 거절·연결 실패는 까닭과 다음 할 일을 말한다, (5) 465 는 SSL · 587 은 STARTTLS,
(6) 배선 -- 도구 · ADMIN_TOOLS · 프롬프트 규칙 · 메시지 지우기 · 배포 경로.

LLM·망 없이 돈다. 실행: python3 tests/test_mail.py
"""
from __future__ import annotations

import os
import shutil
import smtplib
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import keys  # noqa: E402
import mailer  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


임시 = Path(tempfile.mkdtemp(prefix="test-mail-"))
repo = 임시 / "repo"
repo.mkdir()
for n in ("SMTP_USER", "SMTP_APP_PASSWORD", "SMTP_HOST", "SMTP_PORT"):
    os.environ.pop(n, None)

열린 = []


class 가짜SMTP:
    def __init__(self, host, port, 초):
        self.host, self.port, self.로그인, self.보낸, self.닫힘 = host, port, None, [], False
        열린.append(self)

    def login(self, u, p):
        if p == "wrongpassword12":
            raise smtplib.SMTPAuthenticationError(535, b"bad credentials")
        self.로그인 = (u, p)

    def send_message(self, msg):
        self.보낸.append(msg)

    def quit(self):
        self.닫힘 = True


try:
    print("== 수단이 없으면 딱 그것만 묻는다 ==")
    ok(mailer.필요한것(repo) == ["SMTP_USER", "SMTP_APP_PASSWORD"], "없는 것 둘")
    r = mailer.보내기("dbsurd123@gmail.com", "제목", "본문", repo=repo)
    ok(not r["보냈나"] and r["필요한것"] == ["SMTP_USER", "SMTP_APP_PASSWORD"], "안 보내고 필요한 것을 돌려준다")
    ok("`!열쇠 SMTP_USER=" in r["말"] and "`!열쇠 SMTP_APP_PASSWORD=" in r["말"], "**어떻게 주는지가 한 줄로 적혀 있다**")
    ok("smtplib" not in r["말"] and "가입" not in r["말"] and "또는" not in r["말"], "**코드·가입·선택지가 없다** -- 한 길")
    ok("데몬은 필요 없다" in r["말"], "인프라를 세우라고 하지 않는다")
    ok(mailer.보내기("주소아님", "x", "y", repo=repo)["말"].startswith("받는 주소 꼴"), "주소 꼴 검사")
    r = mailer.보내기("dbsurd123@gamil.com", "x", "y", repo=repo)
    ok(not r["보냈나"] and "gmail.com" in r["말"] and "오타" in r["말"], "**gamil.com 같은 흔한 오타는 보내지 않고 되묻는다** (실측)")

    print("\n== .env 의 별칭·꼴로 스스로 찾는다 (실측: GMAIL_APP_PASSWORD 로 적어 두고 '없다' 며 또 물었다) ==")
    (repo / ".env").write_text("GMAIL_APP_PASSWORD=abcd efgh ijkl mnop\nMY_GMAIL=you@gmail.com\nOTHER=x\n", encoding="utf-8")
    ok(mailer.필요한것(repo) == [], "**별칭(GMAIL_APP_PASSWORD)과 꼴(이메일 값)로 찾아 '없다' 고 하지 않는다**")
    v, 어디 = mailer.값찾기("SMTP_APP_PASSWORD", repo)
    ok(v == "abcd efgh ijkl mnop" and 어디 == "GMAIL_APP_PASSWORD", f"비밀번호는 별칭에서 ({어디})")
    v, 어디 = mailer.값찾기("SMTP_USER", repo)
    ok(v == "you@gmail.com" and "꼴로 찾음" in 어디, f"보내는 주소는 값의 꼴로 ({어디})")
    ok("옮겨 적었다" in mailer.표준화("SMTP_APP_PASSWORD", repo) and "SMTP_APP_PASSWORD=abcd" in (repo / ".env").read_text(encoding="utf-8"),
       "찾은 값을 표준 이름으로 옮겨 적는다 -- 다음엔 바로")
    (repo / ".env").write_text("SECRET_PASSWORD=khkh gexu wpep wscp\nA=1\n", encoding="utf-8")
    for n in ("SMTP_USER", "SMTP_APP_PASSWORD"):
        os.environ.pop(n, None)
    ok(mailer.값찾기("SMTP_APP_PASSWORD", repo)[0] == "khkh gexu wpep wscp", "이름이 엉뚱해도 16자 영문 꼴이면 앱 비밀번호로 본다")
    ok(mailer.필요한것(repo) == ["SMTP_USER"], "주소는 없으니 그것만 묻는다")
    (repo / ".env").unlink()

    print("\n== 자리표가 남은 본문은 보내지 않는다 · '내 메일' ==")
    os.environ["SMTP_USER"], os.environ["SMTP_APP_PASSWORD"] = "you@gmail.com", "abcdefghijklmnop"
    r = mailer.보내기("a@b.co", "Invitation – [Lab Name]", "Dear [지원자 이름], ... Prof. [교수님 성함]", repo=repo)
    ok(not r["보냈나"] and "자리표 3개" in r["말"] and "[교수님 성함]" in r["말"] and "실존 인물" in r["말"],
       f"**[자리표]가 남으면 안 보내고 채우라고 한다** ({r['말'][:70]})")
    r = mailer.보내기("me", "x", "y", repo=repo)
    ok(not r["보냈나"] and r["필요한것"] == ["USER_EMAIL"] and "set_key(USER_EMAIL" in r["말"], "'내 메일' 을 모르면 그것만 한 번 묻는다")
    os.environ["USER_EMAIL"] = "me@gmail.com"
    ok(mailer.내정보(repo)["주소"] == "me@gmail.com", "USER_EMAIL 로 '내 메일' 을 안다")
    for n in ("SMTP_USER", "SMTP_APP_PASSWORD", "USER_EMAIL"):
        os.environ.pop(n, None)

    print("\n== !열쇠: 적고, 값은 되비치지 않는다 ==")
    답 = keys.run("!열쇠 SMTP_USER=me@gmail.com", runner=lambda n, v: keys.적기(n, v, repo=repo), allow_write=True)
    ok("SMTP_USER" in 답 and "me@gmail.com" not in 답 and "지워라" in 답, f"답에 이름만, 값 없음, 지우라는 말 ({답[:60]})")
    답 = keys.run("!열쇠 SMTP_APP_PASSWORD=abcd efgh ijkl mnop", runner=lambda n, v: keys.적기(n, v, repo=repo), allow_write=True)
    ok("abcd" not in 답 and "적었다" in 답, "**비밀번호 값이 답에 없다**")
    env = (repo / ".env").read_text(encoding="utf-8")
    ok("SMTP_USER=me@gmail.com\n" in env and "SMTP_APP_PASSWORD=abcd efgh ijkl mnop\n" in env, ".env 에 두 줄")
    ok(oct(os.stat(repo / ".env").st_mode)[-3:] == "600", ".env 는 600")
    ok(os.environ.get("SMTP_APP_PASSWORD") == "abcd efgh ijkl mnop", "os.environ 에도 올라 재시작 없이 쓴다")
    keys.적기("SMTP_USER", "you@gmail.com", repo=repo)
    env = (repo / ".env").read_text(encoding="utf-8")
    ok(env.count("SMTP_USER=") == 1 and "SMTP_USER=you@gmail.com" in env, "같은 이름은 줄을 바꾼다 (두 줄 안 됨)")
    ok("거절" in keys.run("!열쇠 smtp-user=x", allow_write=True) and "관리 채널" in keys.run("!열쇠 A_B=x", allow_write=False),
       "이름 꼴 검사 · 공개 채널 거절")
    try:
        keys.적기("SMTP_APP_PASSWORD", "", repo=repo)
        ok(False, "빈 값은 거절")
    except ValueError as e:
        ok("abcd" not in str(e), "빈 값은 거절, 예외 글에도 값 없음")
    ok(keys.run("!열쇠장 x") is None and keys.run("!열쇠") and "메일" in keys.run("!열쇠"), "경계 · 도움말에 메일 상태")
    ok(mailer.필요한것(repo) == [], "이제 없는 것이 없다")

    print("\n== 받으면 바로 나간다 ==")
    mailer.smtp열기 = 가짜SMTP
    r = mailer.보내기("dbsurd123@gmail.com", "SE 배선 확인", "본문입니다", repo=repo)
    ok(r["보냈나"] and "보냈다" in r["말"], f"보냈다 ({r['말'][:50]})")
    s = 열린[-1]
    ok(s.host == "smtp.gmail.com" and s.port == 465, "기본 gmail:465")
    ok(s.로그인 == ("you@gmail.com", "abcdefghijklmnop"), "**앱 비밀번호의 띄어쓰기를 지우고 로그인**")
    m = s.보낸[0]
    ok(m["To"] == "dbsurd123@gmail.com" and m["From"] == "you@gmail.com" and m["Subject"] == "SE 배선 확인"
       and "본문입니다" in m.get_content(), "헤더·본문이 맞다")
    ok(s.닫힘, "닫는다")
    원장 = (repo / "logs" / "mail_ledger.jsonl").read_text(encoding="utf-8")
    ok('"보냈나": true' in 원장 and "본문입니다" not in 원장, "원장에 보냈나만, 본문은 없다")

    print("\n== 인증 거절: 스스로 좁힌다 (실측 5.7.8) ==")
    mailer.뇌찾기 = lambda: ["앱 비밀번호는 2단계 인증이 켜져야 만들 수 있다 <dig/corpus/github-readme-x.md>"]
    os.environ["SMTP_APP_PASSWORD"] = "wrongpassword12"          # 16자 아님 -> 계정 비밀번호를 준 꼴
    r = mailer.보내기("a@b.co", "x", "y", repo=repo)
    ok(not r["보냈나"] and "앱 비밀번호 꼴이 아니다" in r["말"] and "!열쇠 SMTP_APP_PASSWORD" in r["말"],
       "**계정 비밀번호를 준 것을 코드가 알아챈다** -- 구글 탓으로 돌리지 않는다")
    거절포트 = {"465"}

    class 포트가림(가짜SMTP):
        def login(self, u, p):
            if str(self.port) in 거절포트:
                raise smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")
            self.로그인 = (u, p)
    mailer.smtp열기 = 포트가림
    os.environ["SMTP_APP_PASSWORD"] = "qwertyuiopasdfgh"           # 꼴은 맞는데 465 만 거절
    r = mailer.보내기("a@b.co", "x", "y", repo=repo)
    ok(r["보냈나"] and 열린[-1].port == 587, f"**465 거절 -> 587 로 스스로 고쳐 바로 보낸다** ({r['말'][:60]})")
    ok("SMTP_PORT=587" in (repo / ".env").read_text(encoding="utf-8"), "고친 설정을 .env 에 적었다")
    os.environ.pop("SMTP_PORT", None)
    거절포트.update({"587"})
    r = mailer.보내기("a@b.co", "x", "y", repo=repo)
    ok(not r["보냈나"] and "다 해봤다" in r["말"] and "2단계 인증" in r["말"] and "새로" in r["말"],
       "**다 거절이면 해 본 것을 적고 계정 쪽 한 가지만 청한다**")
    ok("해봄: smtp.gmail.com:587" in r["말"] and "참고(제2의 뇌): 앱 비밀번호는 2단계" in r["말"],
       "해 본 변형과 제2의 뇌의 참고가 답에 붙는다")
    ok(r["필요한것"] == ["SMTP_APP_PASSWORD"], "필요한 것은 앱 비밀번호 하나")
    mailer.뇌찾기 = None
    mailer.smtp열기 = 가짜SMTP
    os.environ["SMTP_APP_PASSWORD"] = "abcdefghijklmnop"

    def 못닿음(h, p, 초):
        raise OSError("Connection refused")
    mailer.smtp열기 = 못닿음
    r = mailer.보내기("a@b.co", "x", "y", repo=repo)
    ok(not r["보냈나"] and "못 닿았다" in r["말"] and "smtp.gmail.com:587" in r["말"],
       "연결 실패는 어디에 못 닿았는지 (앞의 자가 수리가 .env 를 587 로 고쳤으므로 587)")

    print("\n== 587 은 STARTTLS ==")
    os.environ["SMTP_HOST"], os.environ["SMTP_PORT"] = "smtp-relay.brevo.com", "587"
    mailer.smtp열기 = 가짜SMTP
    r = mailer.보내기("a@b.co", "x", "y", repo=repo)
    ok(r["보냈나"] and 열린[-1].host == "smtp-relay.brevo.com" and 열린[-1].port == 587, "다른 중계도 host/port 만 바꾸면 된다")
    import inspect
    src = inspect.getsource(mailer._기본열기)
    ok("starttls" in src and "SMTP_SSL" in src, "기본 열기가 465 SSL / 그 밖 STARTTLS 둘 다")
    ok("--진단" in (뿌리 / "mailer.py").read_text(encoding="utf-8"), "--진단 CLI 가 있다")
finally:
    mailer.smtp열기 = None
    mailer.뇌찾기 = None
    for n in ("SMTP_USER", "SMTP_APP_PASSWORD", "SMTP_HOST", "SMTP_PORT", "USER_EMAIL", "USER_NAME"):
        os.environ.pop(n, None)
    shutil.rmtree(임시, ignore_errors=True)

print("\n== 배선 ==")
import dispatch  # noqa: E402
ok(dispatch.run("!열쇠 A_B=c", allow_write=False) is not None, "!열쇠 가 dispatch 에 걸려 있다")
_도구 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("def send_email" in _도구 and "mailer.보내기" in _도구 and "relay.적기(f\"✉" in _도구, "send_email 도구가 mailer 를 부르고 중계한다")
ok(_서버.count(" send_email,") >= 2, "ADMIN_TOOLS 와 임포트 둘 다에 send_email")
ok("[수단이 없을 때" in _서버 and "딱 그 값만" in _서버 and "선택지를 나열하지 말고" in _서버,
   "**프롬프트 규칙: 설명하고 멈추지 마라 · 선택지 말고 한 길 · 딱 그 값만**")
ok("message.delete()" in _서버 and "keys.PREFIX" in _서버, "!열쇠 메시지는 지운다")
ok("def set_key(name: str, value: str)" in _도구 and "keys.적기(name, value)" in _도구 and _서버.count(" set_key,") >= 2,
   "**set_key 도구**: 채팅으로 준 값을 되묻지 않고 .env 에 (재시작하면 대화 기억은 사라진다)")
ok("set_key 로 즉시" in _서버 and "재시작(배포)마다 사라지고" in _서버, "프롬프트가 그 규칙을 말한다")
ok("[자리표]는 네가 다" in _서버 and "실존 인물 이름을 지어 서명하지 마라" in _서버 and "별칭·꼴로 알아서" in _서버,
   "프롬프트: 자리표는 채워서 · 실존 인물 서명 금지 · .env 는 도구가 찾는다")
ok('"set_key" in (relay.마지막도구.get(thread_id)' in _서버, "set_key 로 적은 턴이면 사용자 메시지를 지운다 (값이 채널에 남았다)")
_wf = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('"mailer.py"' in _wf and '"keys.py"' in _wf, "배포 경로에 mailer.py · keys.py")
p = subprocess.run(["python3", "mailer.py", "--필요"], cwd=str(뿌리), capture_output=True, text=True,
                   env={k: v for k, v in os.environ.items() if not k.startswith("SMTP_")})
ok(p.returncode in (0, 3) and ("!열쇠" in p.stdout or "다 있다" in p.stdout), "--필요 는 망 없이 돈다")
import relay  # noqa: E402
ok("✉" in relay.도구표지, "✉ 는 도구 줄로 센다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("mail: 딱 그것만 묻기 · !열쇠 · 바로 보내기 · 거절/실패 · STARTTLS · 배선 -- 통과")
