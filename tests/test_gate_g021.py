"""G021(코드가 사람에게 시키는 설치를 배포가 하는가)를 임시 저장소에서 **실제로 돌려** 붙든다.

왜 이 게이트가 있나: 실측 2026-09-12, `discord_pdf.py` 가 한글 글꼴이 없으면 사람에게
`sudo apt-get install -y fonts-nanum` 을 하라고 말하는데 배포는 그 꾸러미를 안 깔았다.
그래서 "VM 에 글꼴이 있나요?" 가 사람에게 갔다 -- 읽기만 하는 `ls` 한 줄인데도.

붙드는 것 여섯: (1) 배포가 안 까는 꾸러미를 잡는다, (2) 배포가 까는 꾸러미는 안 잡는다,
(3) `-y` 같은 깃발을 꾸러미로 착각하지 않는다, (4) tests/ 와 gates/ 는 안 본다,
(5) 옵트아웃 주석이 달린 줄은 넘어간다, (6) 배포 워크플로가 없으면 할 일이 없다.

실행: python3 tests/test_gate_g021.py
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))
import gatekeeper  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


게이트파일 = sorted((뿌리 / "gates").glob("G021_*.py"))
ok(len(게이트파일) == 1, f"G021 이 gates/ 에 있다 ({[p.name for p in 게이트파일]})")
spec = importlib.util.spec_from_file_location("_g021", 게이트파일[0])
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)

워크플로상대 = ".github/workflows/deploy-oracle.yml"
임시 = Path(tempfile.mkdtemp(prefix="test-g021-"))


def 저장소(코드: str, 배포: "str | None", 어디: str = "mod.py") -> Path:
    d = Path(tempfile.mkdtemp(prefix="g021-repo-", dir=임시))
    p = d / 어디
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(코드, encoding="utf-8")
    if 배포 is not None:
        wf = d / 워크플로상대
        wf.parent.mkdir(parents=True, exist_ok=True)
        wf.write_text(배포, encoding="utf-8")
    return d


배포_없이 = "jobs:\n  deploy:\n    steps:\n      - run: pip3 install -r requirements.txt\n"
배포_글꼴 = "jobs:\n  deploy:\n    steps:\n      - run: sudo apt-get install -y fonts-nanum\n      - run: pip3 install -r requirements.txt\n"
글꼴시키는코드 = '말 = "이 기계에 한글 글꼴이 없다 -- `sudo apt-get install -y fonts-nanum`"\n'

try:
    print("\n== 배포가 안 까는 꾸러미를 잡는다 ==")
    v = G.check(gatekeeper.GateContext(저장소(글꼴시키는코드, 배포_없이)))
    ok(len(v) == 1 and "fonts-nanum" in v[0], f"사람에게 시키는 apt 를 잡는다 ({v})")
    ok("mod.py:1" in v[0] and 워크플로상대 in v[0], f"어느 줄이고 어디에 넣으라고 말한다 ({v[0][:120]!r})")

    print("\n== 배포가 까는 꾸러미는 안 잡는다 ==")
    v = G.check(gatekeeper.GateContext(저장소(글꼴시키는코드, 배포_글꼴)))
    ok(v == [], f"배포가 이미 깐다 ({v})")

    print("\n== 깃발을 꾸러미로 착각하지 않는다 ==")
    d = 저장소('말 = "apt-get install -y --no-install-recommends poppler-utils"\n', 배포_없이)
    v = G.check(gatekeeper.GateContext(d))
    ok(len(v) == 1 and "poppler-utils" in v[0] and "-y" not in v[0].split("`apt install ")[1][:12],
       f"`-y` 와 `--no-install-recommends` 를 건너뛰고 꾸러미를 고른다 ({v})")

    print("\n== tests/ 와 gates/ 는 안 본다 ==")
    ok(G.check(gatekeeper.GateContext(저장소(글꼴시키는코드, 배포_없이, "tests/test_x.py"))) == [], "tests/ 는 서버 코드가 아니다")
    ok(G.check(gatekeeper.GateContext(저장소(글꼴시키는코드, 배포_없이, "gates/G099_x.py"))) == [], "gates/ 는 서버 코드가 아니다(이 게이트 자신을 포함)")

    print("\n== 옵트아웃은 눈에 보이게 넘어간다 ==")
    v = G.check(gatekeeper.GateContext(저장소(글꼴시키는코드.rstrip("\n") + f"  # {G.OPT_OUT}\n", 배포_없이)))
    ok(v == [], f"`# {G.OPT_OUT}` 가 달린 줄은 넘어간다 ({v})")

    print("\n== 배포 워크플로가 없으면 할 일이 없다 ==")
    ok(G.check(gatekeeper.GateContext(저장소(글꼴시키는코드, None))) == [], "배포가 없는 저장소는 넘어간다")

    print("\n== 이 저장소 자신 ==")
    본 = G.check(gatekeeper.GateContext(뿌리))
    ok(isinstance(본, list), f"이 저장소에서도 돈다 (위반 {len(본)}개: {[x[:80] for x in 본]})")
finally:
    shutil.rmtree(임시, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("G021: 사람에게 시키는 설치를 배포가 하는가 -- 통과")
