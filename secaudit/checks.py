"""secaudit/checks -- 로컬 호스트의 **읽기 전용** 보안 진단 낱낱. 판정은 코드가 한다.

이 저장소의 규율 그대로: 모델이 "안전해 보인다" 고 말하는 것은 근거가 아니다. 각 점검은
실제 상태(포트·권한·계정)를 **실측**해 규칙으로 심각도를 매긴다. 도구가 없어 못 본 것은
"안전" 이 아니라 **"못 잼"** 이다(검사하지 않은 초록불이 검사한 빨간불보다 나쁘다).

무엇을 하고 무엇을 안 하나:
  · 한다: 돌고 있는 호스트 자신의 열린 포트·파일 권한·SUID·계정·방화벽·키 노출을 **열거하고 평가**.
  · 안 한다: 남의 기계에 접속하거나, 익스플로잇을 실제로 실행하거나, 상태를 바꾸는 일. 전부
    읽기뿐이다 -- `find`·`stat`·`/proc` 읽기·`iptables -L`. 쓰기·kill·연결은 없다.

낱낱 하나 = {"id", "제목", "심각도"("높음"|"중간"|"낮음"|"정보"|"못잼"), "증거"(list[str]),
            "고침"(str)}. 심각도는 여기 규칙이 정한다 -- 부르는 쪽(run)이 모으고 보고한다.

network·LLM 없이 돈다.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

심각도차례 = {"높음": 0, "중간": 1, "낮음": 2, "정보": 3, "못잼": 4}

# 들을 만한 포트(서버가 열어도 되는 흔한 것). 이 밖에 0.0.0.0 로 열려 있으면 들여다본다.
흔한포트 = {22, 80, 443, 3000, 5000, 8000, 8080, 8443}
# /usr/bin 에 흔히 SUID 인 것(정상). 이 밖의 SUID 는 들여다본다.
흔한SUID = {"sudo", "su", "passwd", "chsh", "chfn", "gpasswd", "newgrp", "mount", "umount",
          "ping", "ping6", "fusermount", "fusermount3", "pkexec", "sudoedit", "ntfs-3g",
          "dmcrypt-get-device", "mount.nfs", "unix_chkpwd"}


def _달리기(argv, 초=15) -> "tuple[int, str]":
    try:
        p = subprocess.run(argv, capture_output=True, text=True, errors="replace", timeout=초)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, f"{type(e).__name__}: {e}"


def _있나(이름: str) -> bool:
    return any((Path(d) / 이름).exists() for d in os.environ.get("PATH", "").split(":") if d)


# ---------------------------------------------------------------- 포트
def _proc포트(경로: str) -> "list[tuple[str, int]]":
    """/proc/net/tcp(6) 에서 LISTEN(st=0A) 인 (로컬IP, 포트). ss 가 없어도 본다."""
    out = []
    try:
        줄들 = Path(경로).read_text().splitlines()[1:]
    except OSError:
        return out
    for 줄 in 줄들:
        f = 줄.split()
        if len(f) < 4 or f[3] != "0A":       # 0A = LISTEN
            continue
        addr, port = f[1].rsplit(":", 1)
        try:
            포트 = int(port, 16)
        except ValueError:
            continue
        # 주소가 전부 0 이면 모든 인터페이스(0.0.0.0 / ::)로 열린 것 -- 밖에서 닿는다
        전부0 = set(addr) <= {"0"}
        out.append(("*" if 전부0 else "local", 포트))
    return out


def 열린포트() -> dict:
    if not Path("/proc/net/tcp").exists():
        return {"id": "포트", "제목": "열린 TCP 포트", "심각도": "못잼", "증거": ["/proc/net/tcp 가 없다"],
                "고침": "이 환경에서는 포트를 못 본다 -- ss -tlnp 가 되는 호스트에서 다시 잰다"}
    포트들 = _proc포트("/proc/net/tcp") + _proc포트("/proc/net/tcp6")
    노출 = sorted({p for 범위, p in 포트들 if 범위 == "*"})
    뜻밖 = [p for p in 노출 if p not in 흔한포트]
    증거 = [f"모든 인터페이스(0.0.0.0)로 열림: {노출}" if 노출 else "0.0.0.0 로 열린 포트 없음",
          f"그중 흔치 않은 포트: {뜻밖}" if 뜻밖 else ""]
    증거 = [x for x in 증거 if x]
    if 뜻밖:
        심 = "중간"
        고침 = (f"포트 {뜻밖} 가 밖으로 열려 있다 -- 쓰지 않으면 서비스를 끄거나 방화벽으로 막고, "
              "써야 하면 127.0.0.1 에만 바인드하라")
    elif 노출:
        심, 고침 = "정보", "열린 포트가 전부 흔한 것이다 -- 그래도 방화벽으로 허용 범위를 좁혀 두라"
    else:
        심, 고침 = "정보", "밖으로 열린 포트가 없다"
    return {"id": "포트", "제목": "열린 TCP 포트", "심각도": 심, "증거": 증거, "고침": 고침}


# ---------------------------------------------------------------- 방화벽
def 방화벽() -> dict:
    if _있나("ufw"):
        rc, out = _달리기(["ufw", "status"])
        if rc == 0:
            켜짐 = "Status: active" in out
            return {"id": "방화벽", "제목": "방화벽(ufw)", "심각도": "정보" if 켜짐 else "중간",
                    "증거": [out.strip().splitlines()[0] if out.strip() else "ufw status 빈 응답"],
                    "고침": "ufw 가 켜져 있다" if 켜짐 else "sudo ufw enable 로 방화벽을 켜고 필요한 포트만 허용하라"}
    rc, out = _달리기(["iptables", "-S"])
    if rc == 0:
        규칙 = [x for x in out.splitlines() if x.startswith("-A")]
        막는기본 = "-P INPUT DROP" in out or "-P INPUT REJECT" in out
        if 규칙 or 막는기본:
            return {"id": "방화벽", "제목": "방화벽(iptables)", "심각도": "정보",
                    "증거": [f"규칙 {len(규칙)}개, INPUT 기본 {'DROP' if 막는기본 else 'ACCEPT'}"],
                    "고침": "방화벽 규칙이 있다 -- 허용 포트가 의도한 것인지 확인하라"}
        return {"id": "방화벽", "제목": "방화벽(iptables)", "심각도": "중간",
                "증거": ["INPUT 기본 ACCEPT, 규칙 없음 -- 전부 열려 있다"],
                "고침": "기본 정책을 DROP 으로 두고 필요한 포트만 허용하라 (ufw 가 더 쉽다)"}
    return {"id": "방화벽", "제목": "방화벽", "심각도": "못잼", "증거": ["ufw·iptables 를 못 읽었다(권한/부재)"],
            "고침": "root 로 iptables -S 나 ufw status 가 되는 호스트에서 다시 잰다"}


# ---------------------------------------------------------------- SSH 키 권한
def ssh키권한() -> dict:
    d = Path(os.path.expanduser("~/.ssh"))
    if not d.is_dir():
        return {"id": "ssh키", "제목": "~/.ssh 권한", "심각도": "정보", "증거": ["~/.ssh 가 없다"],
                "고침": "SSH 키를 안 쓰면 해당 없음"}
    나쁜 = []
    dm = d.stat().st_mode & 0o077
    if dm:
        나쁜.append(f"~/.ssh 디렉터리가 남에게 열림({oct(d.stat().st_mode)[-3:]}) -- 700 이어야 한다")
    for p in sorted(d.iterdir()):
        if not p.is_file():
            continue
        mode = p.stat().st_mode & 0o077
        개인키 = p.name in ("id_rsa", "id_ed25519", "id_ecdsa", "id_dsa") or (
            p.suffix == "" and "PRIVATE KEY" in _앞줄(p))
        if 개인키 and mode:
            나쁜.append(f"개인키 {p.name} 가 남에게 읽힘({oct(p.stat().st_mode)[-3:]}) -- 600 이어야 한다")
    if 나쁜:
        return {"id": "ssh키", "제목": "~/.ssh 권한", "심각도": "높음", "증거": 나쁜,
                "고침": "chmod 700 ~/.ssh; chmod 600 ~/.ssh/<개인키> -- 남이 읽으면 키가 새 것과 같다"}
    return {"id": "ssh키", "제목": "~/.ssh 권한", "심각도": "정보", "증거": ["키·디렉터리 권한이 600/700 이다"],
            "고침": "권한이 바르다"}


def _앞줄(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:200]
    except OSError:
        return ""


# ---------------------------------------------------------------- 비밀 파일 노출
def 비밀파일노출(뿌리들=("~", ".")) -> dict:
    """.env · *.pem · *.key · id_* 가 남에게 읽히는가. 저장소 .env 가 제일 흔한 구멍이다."""
    나쁜 = []
    본 = set()
    # 진짜 비밀이 담기는 파일 이름만 -- `secret_filter.py` 같은 소스·`.env.example` 같은
    # 템플릿은 비밀이 아니다(거짓 양성은 점검의 신뢰를 깎는다).
    비밀이름 = re.compile(r"(\.pem$|\.key$|\.pfx$|\.p12$|^id_(rsa|ed25519|ecdsa|dsa)$"
                       r"|credentials\.json$|\.netrc$)", re.I)
    제외 = (".example", ".sample", ".template", ".dist", ".py", ".md", ".txt", ".rst")
    def 비밀인가(이름: str) -> bool:
        low = 이름.lower()
        if low.endswith(제외):
            return False
        if low == ".env" or (low.startswith(".env.") and not low.endswith(제외)):
            return True
        return bool(비밀이름.search(이름))
    for 뿌리 in 뿌리들:
        base = Path(os.path.expanduser(뿌리)).resolve()
        if not base.is_dir():
            continue
        for p in list(base.glob("*")) + list(base.glob(".env*")):
            if not p.is_file() or p in 본:
                continue
            본.add(p)
            if 비밀인가(p.name) and (p.stat().st_mode & 0o044):
                나쁜.append(f"{p} 가 남에게 읽힘({oct(p.stat().st_mode)[-3:]})")
    if 나쁜:
        return {"id": "비밀파일", "제목": "비밀 파일 노출", "심각도": "높음", "증거": 나쁜[:10],
                "고침": "chmod 600 <파일> -- 비밀·키 파일은 주인만 읽어야 한다"}
    return {"id": "비밀파일", "제목": "비밀 파일 노출", "심각도": "정보", "증거": ["훑은 자리에서 남에게 읽히는 비밀 파일 없음"],
            "고침": "해당 자리는 깨끗하다 -- 다른 디렉터리도 의심되면 뿌리를 늘려 다시 잰다"}


# ---------------------------------------------------------------- 세계 쓰기 가능
def 세계쓰기가능(뿌리들=("/etc", "~")) -> dict:
    나쁜 = []
    for 뿌리 in 뿌리들:
        base = os.path.expanduser(뿌리)
        if not Path(base).is_dir():
            continue
        rc, out = _달리기(["find", base, "-xdev", "-type", "f", "-perm", "-0002",
                         "-not", "-path", "*/.git/*"], 초=30)
        if rc == 0:
            나쁜 += [x for x in out.splitlines() if x.strip()]
    if 나쁜:
        return {"id": "세계쓰기", "제목": "세계 쓰기 가능 파일", "심각도": "높음", "증거": 나쁜[:10]
                + ([f"... 외 {len(나쁜) - 10}개"] if len(나쁜) > 10 else []),
                "고침": "chmod o-w <파일> -- 아무나 고칠 수 있는 설정·스크립트는 통째로 장악 경로다"}
    return {"id": "세계쓰기", "제목": "세계 쓰기 가능 파일", "심각도": "정보",
            "증거": ["훑은 자리에 세계 쓰기 가능 파일 없음"], "고침": "깨끗하다"}


# ---------------------------------------------------------------- SUID
def suid파일(뿌리들=("/usr/bin", "/usr/local/bin", "/bin")) -> dict:
    뜻밖 = []
    for 뿌리 in 뿌리들:
        if not Path(뿌리).is_dir():
            continue
        rc, out = _달리기(["find", 뿌리, "-xdev", "-type", "f", "-perm", "-4000"], 초=30)
        if rc == 0:
            for 줄 in out.splitlines():
                줄 = 줄.strip()
                if 줄 and Path(줄).name not in 흔한SUID:
                    뜻밖.append(줄)
    if 뜻밖:
        return {"id": "suid", "제목": "흔치 않은 SUID 실행파일", "심각도": "중간", "증거": 뜻밖[:12],
                "고침": "각 파일이 왜 SUID 인지 확인하라 -- 모르는 것은 chmod u-s 로 내리거나 조사하라 "
                      "(SUID 는 권한 상승의 흔한 경로다)"}
    return {"id": "suid", "제목": "흔치 않은 SUID 실행파일", "심각도": "정보",
            "증거": ["SUID 가 전부 흔한 것이다"], "고침": "깨끗하다"}


# ---------------------------------------------------------------- 계정
def 위험계정() -> dict:
    나쁜 = []
    rc, out = _달리기(["getent", "passwd"])
    if rc != 0:
        try:
            out = Path("/etc/passwd").read_text()
            rc = 0
        except OSError:
            return {"id": "계정", "제목": "UID 0 계정", "심각도": "못잼", "증거": ["passwd 를 못 읽었다"],
                    "고침": "getent passwd 가 되는 호스트에서 다시 잰다"}
    uid0 = []
    for 줄 in out.splitlines():
        f = 줄.split(":")
        if len(f) >= 3 and f[2] == "0" and f[0] != "root":
            uid0.append(f[0])
    if uid0:
        나쁜.append(f"root 말고 UID 0 인 계정: {uid0} -- root 와 같은 권한이다")
    # 빈 비밀번호(shadow 를 읽을 수 있을 때만)
    try:
        for 줄 in Path("/etc/shadow").read_text().splitlines():
            f = 줄.split(":")
            if len(f) >= 2 and f[1] == "" and f[0] not in ("sync",):
                나쁜.append(f"빈 비밀번호 계정: {f[0]}")
    except OSError:
        pass
    if 나쁜:
        return {"id": "계정", "제목": "위험한 계정", "심각도": "높음", "증거": 나쁜,
                "고침": "UID 0 중복 계정은 지우거나 UID 를 바꾸고, 빈 비밀번호는 passwd 로 설정하거나 잠근다"}
    return {"id": "계정", "제목": "위험한 계정", "심각도": "정보", "증거": ["root 외 UID 0 없음, 빈 비밀번호 못 봄"],
            "고침": "깨끗하다(shadow 를 못 읽었으면 빈 비밀번호는 '못 잼' 이다)"}


낱낱들 = [열린포트, 방화벽, ssh키권한, 비밀파일노출, 세계쓰기가능, suid파일, 위험계정]


def 전부(repo=None) -> "list[dict]":
    out = []
    for fn in 낱낱들:
        try:
            out.append(fn())
        except Exception as e:                                    # noqa: BLE001
            out.append({"id": fn.__name__, "제목": fn.__name__, "심각도": "못잼",
                        "증거": [f"점검이 터졌다: {type(e).__name__}: {str(e)[:120]}"],
                        "고침": "이 점검 코드를 고쳐야 한다(repair 로)"})
    out.sort(key=lambda f: 심각도차례.get(f["심각도"], 9))
    return out
