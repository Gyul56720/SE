"""mailer -- 메일은 도구가 보낸다. 수단이 없으면 **딱 그것만** 묻는다.

실측 2026-09-11: "메일을 보내라" 는 부탁에 에이전트가 Gmail 앱 비밀번호 발급 절차와
smtplib 코드를 **설명하고 멈췄다.** 그다음엔 "localhost:25 가 거절한다, 인프라가 없다"
고 멈췄다. 둘 다 사람이 원한 것이 아니다 -- 사람은 "필요한 것만 묻고 나머지는 알아서
접속하는 하네스" 를 원했다.

그래서 규칙을 코드로 둔다:
  · 필요한 것은 둘뿐이다: SMTP_USER(보내는 gmail 주소) · SMTP_APP_PASSWORD(16자리 앱
    비밀번호). 서버·포트는 기본값(smtp.gmail.com:465, SSL)이 있다. 데몬을 세울 일이 없다.
    다른 중계(Brevo·Mailgun …)를 쓰려면 SMTP_HOST/SMTP_PORT(587 = STARTTLS)만 더 준다.
  · **가입은 사람만 할 수 있다**(메일 인증 · 캡차 · 약관). 그래서 선택지를 나열하지 않고
    제일 짧은 길 하나(Gmail 앱 비밀번호, 1분)를 딱 집어 청한다.
  · 없으면 `보내기` 가 **무엇이 없는지와 어떻게 주는지**(`!열쇠 이름=값`)를 돌려준다.
    에이전트는 그 말을 그대로 전한다. 받으면 같은 도구를 다시 부르면 된다.
  · SMTP_APP_PASSWORD 는 이름에 PASSWORD 가 있어 secret_filter 가 출력에서 지우고
    sandbox 가 자식 환경에서 뺀다 -- 새로 할 것이 없다.
  · 원장: logs/mail_ledger.jsonl (누구에게 · 제목 · 보냈나 · 까닭). 본문은 안 적는다.

쓰기:
    python3 mailer.py --필요                              # 없는 것 (0 다 있음 · 3 없음)
    python3 mailer.py --진단                              # 인증 실패를 스스로 좁힌다 (0 됐다 · 1 계정 쪽)
    python3 mailer.py --to a@b.c --subject 제목 --body 본문
"""
from __future__ import annotations

import argparse
import json
import re
import smtplib
import ssl
import sys
import time
from email.message import EmailMessage
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from dig.harvest import env값  # noqa: E402

필요이름들 = ("SMTP_USER", "SMTP_APP_PASSWORD")
기본 = {"SMTP_HOST": "smtp.gmail.com", "SMTP_PORT": "465"}
_주소꼴 = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
원장상대 = "logs/mail_ledger.jsonl"

smtp열기 = None       # 검사 주입: (host, port, 초) -> login(u, p) · send_message(msg) · quit()


def 필요한것(repo=None) -> "list[str]":
    return [n for n in 필요이름들 if not env값(n, repo)]


def 묻는말(빠진: "list[str]") -> str:
    설명 = {"SMTP_USER": "보내는 gmail 주소", "SMTP_APP_PASSWORD": "16자리 앱 비밀번호"}
    줄 = ["보내려면 이것이 필요하다 -- **딱 이것만** 달라 (관리 채널에서, 값은 안 보여준다):"]
    for n in 빠진:
        줄.append(f"  `!열쇠 {n}=<{설명.get(n, n)}>`")
    if "SMTP_APP_PASSWORD" in 빠진:
        줄.append("  앱 비밀번호: myaccount.google.com → 보안 → 2단계 인증 켬 → '앱 비밀번호' → 생성")
    줄.append("받으면 다시 부르면 바로 보낸다. 서버·포트·데몬은 필요 없다(smtp.gmail.com:465 기본).")
    return "\n".join(줄)


def _기본열기(host: str, port: int, 초: int):
    """465 는 SSL, 그 밖(587)은 STARTTLS -- Gmail 도 Brevo·Mailgun 같은 중계도 이 둘 중 하나다."""
    ctx = ssl.create_default_context()
    if port == 465:
        return smtplib.SMTP_SSL(host, port, timeout=초, context=ctx)
    s = smtplib.SMTP(host, port, timeout=초)
    s.starttls(context=ctx)
    return s


def _적기(repo, 줄: dict) -> None:
    p = Path(repo or REPO) / 원장상대
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(줄, ensure_ascii=False) + "\n")
    except OSError:
        pass


def 보내기(to: str, subject: str, body: str, repo=None, 초: int = 30) -> dict:
    """{"보냈나", "필요한것", "말"}. 말은 사람에게 그대로 보여도 되는 글이다(값 없음)."""
    to = (to or "").strip()
    if not _주소꼴.match(to):
        return {"보냈나": False, "필요한것": [], "말": f"받는 주소 꼴이 아니다: {to[:40]!r}"}
    if not (subject or "").strip():
        return {"보냈나": False, "필요한것": [], "말": "제목이 비었다"}
    빠진 = 필요한것(repo)
    if 빠진:
        return {"보냈나": False, "필요한것": 빠진, "말": 묻는말(빠진)}
    user, pw = env값("SMTP_USER", repo), env값("SMTP_APP_PASSWORD", repo)
    host = env값("SMTP_HOST", repo) or 기본["SMTP_HOST"]
    try:
        port = int(env값("SMTP_PORT", repo) or 기본["SMTP_PORT"])
    except ValueError:
        port = int(기본["SMTP_PORT"])
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = user, to, subject.strip()
    msg.set_content(body or "")
    줄 = {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "to": to, "subject": subject[:120]}
    try:
        s = (smtp열기 or _기본열기)(host, port, 초)
        try:
            s.login(user, pw.replace(" ", ""))      # 구글이 앱 비밀번호를 4자리씩 띄워 보여준다
            s.send_message(msg)
        finally:
            try:
                s.quit()
            except Exception:                        # noqa: BLE001
                pass
    except smtplib.SMTPAuthenticationError as e:
        # **스스로 좁힌다.** 실측 2026-09-11: 5.7.8 을 받고 "구글 보안 정책 때문" 이라 보고하고
        # 멈췄다. 코드가 해 볼 수 있는 것(꼴 검사 · 포트 · 대소문자)을 다 해 보고, 제2의 뇌에서
        # 참고를 끌어오고, 그래도 안 되면 계정 쪽 한 가지만 청한다.
        진 = 진단(repo, 초=초)
        if 진.get("됐다"):
            return 보내기(to, subject, body, repo=repo, 초=초)   # 고쳐진 설정으로 바로 다시
        말 = (f"로그인 거절 ({str(e)[:60]}). 스스로 좁혔다:\n"
             + "".join(f"  해봄: {x}\n" for x in 진["해본것"])
             + f"  판정: {진['판정']}\n  다음: {진['다음']}"
             + ("".join(f"\n  참고(제2의 뇌): {x}" for x in 진["참고"][:3]) if 진["참고"] else ""))
        _적기(repo, dict(줄, 보냈나=False, 까닭="인증 거절: " + 진["판정"][:80]))
        return {"보냈나": False, "필요한것": 진["필요한것"], "말": 말}
    except (OSError, smtplib.SMTPException) as e:
        말 = f"SMTP 서버에 못 닿았다 ({host}:{port}) -- {type(e).__name__}: {str(e)[:80]}"
        _적기(repo, dict(줄, 보냈나=False, 까닭=말[:120]))
        return {"보냈나": False, "필요한것": [], "말": 말}
    _적기(repo, dict(줄, 보냈나=True))
    return {"보냈나": True, "필요한것": [], "말": f"보냈다 -> {to} ({host}:{port}, 제목 {subject.strip()[:40]!r})"}


# ---------------------------------------------------------------- 진단: 인증 실패를 스스로 좁힌다
뇌찾기 = None      # 검사 주입: () -> ["요약 <출처>", ...]. None 이면 dig/harvest 한 바퀴 + graph 조회
뇌검색어 = "gmail smtp 535 5.7.8 username and password not accepted app password"


def _뇌기본() -> "list[str]":
    """제2의 뇌: 이 오류를 밖에서 찾아 색인하고, 색인에서 꺼낸다. 망이 막히면 빈손."""
    try:
        from dig import harvest
        from graph import ask
        harvest.한바퀴([뇌검색어], 몇=3, 상한=4)
        return [f"{n.get('요약', '')[:160]} <{n.get('출처', '')}>" for _, n in ask.찾기(뇌검색어, 최대=3)]
    except Exception as e:                                        # noqa: BLE001
        return [f"(제2의 뇌를 못 물었다: {type(e).__name__})"]


def 진단(repo=None, 초: int = 20) -> dict:
    """{"됐다", "판정", "해본것", "다음", "필요한것", "참고"}. 판정은 코드가 한다."""
    해본, 참고 = [], []
    user, pw = env값("SMTP_USER", repo), env값("SMTP_APP_PASSWORD", repo)
    if "@" not in user:
        return {"됐다": False, "판정": "SMTP_USER 가 전체 주소가 아니다", "해본것": 해본,
                "다음": "`!열쇠 SMTP_USER=<전체 gmail 주소>`", "필요한것": ["SMTP_USER"], "참고": 참고}
    pw2 = pw.replace(" ", "").replace("-", "")
    if not (len(pw2) == 16 and pw2.isalpha()):
        해본.append(f"비밀번호 꼴 검사: 공백 뺀 길이 {len(pw2)} (앱 비밀번호는 영문 16자)")
        return {"됐다": False, "판정": "앱 비밀번호 꼴이 아니다 -- 계정 비밀번호를 준 듯하다. 구글 SMTP 는 그것을 안 받는다",
                "해본것": 해본, "다음": "`!열쇠 SMTP_APP_PASSWORD=<앱 비밀번호 16자>` (myaccount.google.com → 보안 → 앱 비밀번호)",
                "필요한것": ["SMTP_APP_PASSWORD"], "참고": 참고}
    host = env값("SMTP_HOST", repo) or 기본["SMTP_HOST"]
    try:
        port0 = int(env값("SMTP_PORT", repo) or 기본["SMTP_PORT"])
    except ValueError:
        port0 = 465
    변형들 = [(port, u) for port in (port0, 587 if port0 == 465 else 465) for u in (user, user.lower())]
    본 = set()
    for port, u in 변형들:
        if (port, u) in 본:
            continue
        본.add((port, u))
        try:
            s = (smtp열기 or _기본열기)(host, port, 초)
            try:
                s.login(u, pw2)
            finally:
                try:
                    s.quit()
                except Exception:                                 # noqa: BLE001
                    pass
        except smtplib.SMTPAuthenticationError:
            해본.append(f"{host}:{port} {u} -> 거절")
            continue
        except (OSError, smtplib.SMTPException) as e:
            해본.append(f"{host}:{port} -> 못 닿음 ({type(e).__name__})")
            continue
        해본.append(f"{host}:{port} {u} -> **됐다**")
        import keys
        if port != port0:
            keys.적기("SMTP_PORT", str(port), repo=repo)
        if u != user:
            keys.적기("SMTP_USER", u, repo=repo)
        return {"됐다": True, "판정": f"{host}:{port} · {u} 로 로그인이 된다 -- 설정을 그렇게 고쳤다",
                "해본것": 해본, "다음": "바로 다시 보낸다", "필요한것": [], "참고": 참고}
    참고 = (뇌찾기 or _뇌기본)()
    return {"됐다": False,
            "판정": "코드 쪽에서 할 수 있는 것은 다 해봤다 -- 구글이 자격 자체를 거절한다(5.7.8). "
                  "앱 비밀번호가 폐기됐거나, 2단계 인증이 꺼져 있거나(그러면 앱 비밀번호가 무효), "
                  "Workspace 관리자가 SMTP 를 막은 것 중 하나다",
            "해본것": 해본,
            "다음": "계정 쪽 한 가지: myaccount.google.com → 보안 → 2단계 인증 '켜짐' 확인 → 앱 비밀번호를 "
                  "**새로** 만들어 `!열쇠 SMTP_APP_PASSWORD=<새 16자>`. 받으면 다시 부르면 된다",
            "필요한것": ["SMTP_APP_PASSWORD"], "참고": 참고}


def main() -> int:
    ap = argparse.ArgumentParser(description="메일을 보낸다 -- 수단이 없으면 딱 그것만 묻는다")
    ap.add_argument("--필요", action="store_true", help="없는 것만 본다 (안 보낸다)")
    ap.add_argument("--진단", action="store_true", help="인증 실패를 스스로 좁힌다 (로그인만 해 본다)")
    ap.add_argument("--to", default="")
    ap.add_argument("--subject", default="")
    ap.add_argument("--body", default="")
    args = ap.parse_args()
    if args.진단:
        진 = 진단()
        for x in 진["해본것"]:
            print("  해봄:", x)
        print("  판정:", 진["판정"])
        print("  다음:", 진["다음"])
        for x in 진["참고"]:
            print("  참고:", x)
        return 0 if 진["됐다"] else 1
    if args.필요 or not args.to:
        빠진 = 필요한것()
        print("  다 있다 -- 보낼 수 있다" if not 빠진 else 묻는말(빠진))
        return 0 if not 빠진 else 3
    r = 보내기(args.to, args.subject, args.body)
    print(r["말"])
    return 0 if r["보냈나"] else (3 if r["필요한것"] else 1)


if __name__ == "__main__":
    raise SystemExit(main())
