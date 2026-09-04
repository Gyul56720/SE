"""원고를 **VM 밖으로** 내보낸다 -- Discord 에 파일로 올린다.

원고는 VM 안의 JSON 에만 있다. SSH 로 들어가 `--read` 로 보는 것은 되는데, 그건 화면에
쏟아지는 것이지 손에 들어오는 파일이 아니다. 사용자 평: "파일 다운로드를 받고 싶은데
로컬 환경 밖으로 못 빼겠어."

이 저장소는 이미 Discord 로 지시를 주고받는다. 그러니 **원고를 Discord 에 올리면** 폰이든
노트북이든 어디서나 받을 수 있다. 자격증명도 이미 있다(DISCORD_BOT_TOKEN + CHANNEL_ID,
또는 DISCORD_WEBHOOK_URL) -- overnight.py 의 알림이 쓰는 것과 같은 것이다.

봇 게이트웨이는 띄우지 않는다. discord.py 로 로그인하면 이 스크립트가 봇이 되어 이미 도는
봇과 세션이 겹친다. 파일 업로드는 multipart POST 한 방이면 된다.

    python3 novel/deliver.py --book novel/drift.json
    python3 novel/deliver.py --book novel/drift.json --name 1화.txt

Discord 의 첨부 상한(무료 서버 기준 25MB)을 넘으면 나눠 올린다. 5만 자짜리 한글 원고가
15만 바이트 남짓이라 실제로는 걸릴 일이 거의 없지만, 상한에 걸려 통째로 실패하는 것보다
나눠서라도 도착하는 편이 낫다.

**토큰은 절대 찍지 않는다.** Discord 가 돌려준 code/message 만 뽑아 쓴다.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

API = "https://discord.com/api/v10/channels/{cid}/messages"
LIMIT = 24 * 1024 * 1024          # Discord 첨부 상한보다 한 뼘 아래


def _multipart(fields: dict, filename: str, blob: bytes) -> tuple[bytes, str]:
    """multipart/form-data 를 손으로 짠다 -- 이것 하나 때문에 의존성을 늘리지 않는다."""
    bound = f"----drift{uuid.uuid4().hex}"
    out = []
    for k, v in fields.items():
        out.append(f"--{bound}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n"
                   f"{v}\r\n".encode())
    ctype = mimetypes.guess_type(filename)[0] or "text/plain; charset=utf-8"
    out.append(f"--{bound}\r\nContent-Disposition: form-data; name=\"files[0]\"; "
               f"filename=\"{filename}\"\r\nContent-Type: {ctype}\r\n\r\n".encode())
    out.append(blob)
    out.append(f"\r\n--{bound}--\r\n".encode())
    return b"".join(out), f"multipart/form-data; boundary={bound}"


def send_file(text: str, filename: str, note: str = "") -> tuple[bool, str]:
    token = os.environ.get("DISCORD_BOT_TOKEN") or ""
    channel = str(os.environ.get("DISCORD_CHANNEL_ID") or "")
    webhook = os.environ.get("DISCORD_WEBHOOK_URL") or ""
    if not webhook and not (token and channel):
        return False, ("Discord 자격증명이 없다. .env 에 DISCORD_BOT_TOKEN + "
                       "DISCORD_CHANNEL_ID 또는 DISCORD_WEBHOOK_URL 이 있어야 한다")

    blob = text.encode("utf-8")
    parts = [blob[i:i + LIMIT] for i in range(0, len(blob), LIMIT)] or [b""]
    stem, _, ext = filename.rpartition(".")
    ok = 0
    for i, part in enumerate(parts, 1):
        name = filename if len(parts) == 1 else f"{stem or filename}.{i}of{len(parts)}.{ext or 'txt'}"
        head = note if i == 1 else ""
        if len(parts) > 1:
            head = f"{head} ({i}/{len(parts)})".strip()
        body, ctype = _multipart({"payload_json": json.dumps({"content": head[:1900]})},
                                 name, part)
        url = webhook if webhook else API.format(cid=channel)
        headers = {"Content-Type": ctype}
        if not webhook:
            headers["Authorization"] = f"Bot {token}"
        try:
            urllib.request.urlopen(
                urllib.request.Request(url, data=body, headers=headers, method="POST"),
                timeout=60).read()
            ok += 1
        except urllib.error.HTTPError as e:
            # 값은 찍지 않는다. Discord 가 만든 code/message 만 뽑는다.
            try:
                j = json.loads(e.read().decode("utf-8", "replace"))
                why = f"{j.get('code', '')} {j.get('message', '')}".strip()
            except Exception:
                why = ""
            return False, f"HTTP {e.code} {why}".strip()
        except Exception as e:
            return False, f"{type(e).__name__}"
    return True, f"{ok}개 파일, {len(blob):,}바이트"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default="novel/drift.json")
    ap.add_argument("--name", default="")
    ap.add_argument("--note", default="")
    a = ap.parse_args()

    p = Path(a.book)
    if not p.exists():
        print(f"원고가 없다: {p}", file=sys.stderr)
        return 1

    from novel import flow
    book = json.loads(p.read_text(encoding="utf-8"))
    text = flow.text_of(book)
    if not text.strip():
        print(f"원고가 비어 있다: {p}  (아직 덩어리가 안 나왔다)", file=sys.stderr)
        return 1

    name = a.name or f"{p.stem}.txt"
    note = a.note or (f"**{name}** — {len(book['chunks'])}덩어리 · {len(text):,}자 · "
                      f"사건 {book.get('shocks', 0)}회")
    ok, why = send_file(text, name, note)
    print(("보냈다: " if ok else "못 보냈다: ") + why, file=sys.stderr if not ok else sys.stdout)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
