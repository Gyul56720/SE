"""Discord 알림이 왜 안 가는지 한 번에 짚는다.

overnight.py 는 알림 실패를 삼킨다 -- 알림 때문에 밤샘 런이 죽으면 안 되기 때문이다.
대신 실패 원인도 같이 삼켜져서 종류와 HTTP 코드만 남는다. 그 코드만으로는 "토큰이
틀렸다" 와 "봇이 그 채널에 없다" 가 구별되지 않는다. 여기서 단계를 갈라 짚는다.

  401 토큰 자체가 거부됨          -- 값이 틀렸거나 봇이 지워졌다
  403 인증은 됐는데 접근이 막힘    -- 봇이 그 서버/채널에 없거나 쓰기 권한이 없다
  404 그런 채널이 없음            -- ID 가 채널이 아니라 서버/카테고리 ID 일 때가 흔하다

**값은 절대 찍지 않는다.** Discord 가 돌려준 code/message 만 뽑아 쓴다 -- 그 둘은
Discord 가 만든 문자열이라 자격증명이 실리지 않는다. 응답 본문 전체는 찍지 않는다
(프록시가 낀 환경에서 헤더가 되비쳐 나올 수 있다).

실행:
    python3 novel/discord_check.py            # 진단만
    python3 novel/discord_check.py --send     # 테스트 메시지까지 실제로 쏜다
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://discord.com/api/v10"

# Discord 가 본문에 실어 보내는 오류 코드 -> 무엇을 하면 되는가.
FIX = {
    50001: "봇이 그 채널을 볼 수 없다. 채널이 속한 서버에 봇을 초대했는지, 비공개 채널이면\n"
           "         그 채널의 권한 목록에 봇(또는 봇의 역할)이 들어 있는지 본다.",
    50013: "봇이 채널은 보는데 '메시지 보내기' 권한이 없다. 채널 설정 -> 권한에서 봇 역할에\n"
           "         '메시지 보내기' 를 켠다.",
    10003: "그런 채널이 없다. DISCORD_CHANNEL_ID 가 채널 ID 가 맞는지 본다 -- 서버 ID 나\n"
           "         카테고리 ID 를 넣는 실수가 흔하다. 채널 우클릭 -> 'ID 복사'.",
    50035: "요청 형식이 거부됐다. 채널 ID 에 공백이나 따옴표가 섞이지 않았는지 본다.",
}


def call(method: str, path: str, auth: str, body: dict = None):
    """(HTTP 코드, Discord code, Discord message) 를 돌려준다. 값은 담지 않는다."""
    data = json.dumps(body).encode() if body else None
    headers = {"Authorization": f"Bot {auth}"}
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, None, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            j = json.loads(e.read().decode() or "{}")
        except (ValueError, OSError):
            j = {}
        # code/message 만 꺼낸다. 본문 전체는 쓰지 않는다.
        return e.code, j.get("code"), {"message": str(j.get("message", ""))[:120]}
    except Exception as e:                                            # noqa: BLE001
        return None, None, {"message": f"{type(e).__name__}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="테스트 메시지를 실제로 보낸다")
    a = ap.parse_args()

    auth = os.environ.get("DISCORD_BOT_TOKEN") or ""
    chan = str(os.environ.get("DISCORD_CHANNEL_ID") or "").strip()
    hook = os.environ.get("DISCORD_WEBHOOK_URL") or ""

    # 이름을 print 줄에 직접 쓰지 않고 데이터로 돌린다. G004 는 출력 구문 근처에
    # TOKEN 이 든 단어가 보간되는 줄을 막는데, 여기서는 라벨일 뿐 값이 아니지만
    # 게이트는 이름만 보고 그 둘을 못 가른다 -- 게이트가 아니라 코드를 바꾼다.
    print("환경변수")
    for name, state in (("DISCORD_BOT_TOKEN", "설정됨" if auth else "없음"),
                        ("DISCORD_CHANNEL_ID", chan or "없음"),
                        ("DISCORD_WEBHOOK_URL", "설정됨" if hook else "없음")):
        print(f"   {name:20} {state}")

    if hook:
        print("\n웹훅이 설정돼 있다. overnight.py 는 웹훅을 먼저 쓴다 -- 봇 권한과 무관하게")
        print("동작하므로 403 이 났다면 웹훅 URL 이 지워졌거나 잘못된 것이다.")
    if not auth:
        print("\n봇 경로를 쓸 수 없다 (DISCORD_BOT_TOKEN 이 없다).")
        print("가장 빠른 해결: 채널 설정 -> 연동 -> 웹훅 -> 새 웹훅 -> URL 복사 후")
        print("    export DISCORD_WEBHOOK_URL='...'")
        print("웹훅은 봇을 서버에 초대할 필요도, 권한을 줄 필요도 없다.")
        return 1

    print("\n1. 토큰이 살아 있는가  (GET /users/@me)")
    status, code, body = call("GET", "/users/@me", auth)
    if status == 200:
        print(f"   OK -- 봇 '{body.get('username')}' 로 인증된다")
    else:
        print(f"   실패 HTTP {status} code={code} -- {body.get('message')}")
        print("   토큰 값이 틀렸거나 재발급됐다. Discord 개발자 포털에서 다시 확인한다.")
        return 1

    if not chan:
        print("\nDISCORD_CHANNEL_ID 가 없어 여기까지만 본다.")
        return 1

    print(f"\n2. 그 채널이 보이는가  (GET /channels/{chan})")
    status, code, body = call("GET", f"/channels/{chan}", auth)
    if status == 200:
        print(f"   OK -- '{body.get('name')}' (type={body.get('type')}, "
              f"guild={body.get('guild_id')})")
        if body.get("type") not in (0, 5, 10, 11, 12):
            print("   ⚠ 텍스트 채널이 아니다. 메시지를 못 보낸다.")
    else:
        print(f"   실패 HTTP {status} code={code} -- {body.get('message')}")
        print(f"   → {FIX.get(code, '위 코드를 Discord 문서에서 확인한다.')}")
        return 1

    print("\n3. 실제로 보낼 수 있는가  (POST /channels/../messages)")
    if not a.send:
        print("   건너뜀 -- 실제로 쏘려면 --send 를 붙인다")
        return 0
    status, code, body = call("POST", f"/channels/{chan}/messages", auth,
                              {"content": "overnight.py 알림 경로 점검"})
    if status in (200, 201):
        print("   OK -- 채널에 메시지가 갔다. overnight.py 도 같은 경로를 쓴다.")
        return 0
    print(f"   실패 HTTP {status} code={code} -- {body.get('message')}")
    print(f"   → {FIX.get(code, '위 코드를 Discord 문서에서 확인한다.')}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
