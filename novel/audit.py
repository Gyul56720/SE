"""**파이프라인 점검 -- 적어 둔 것이 실제로 부쳐지는가.**

사용자(2026-09-09): "모든 파이프라인 전부 다 점검해."

## 왜 있나

이 저장소가 같은 병을 네 번 앓았다. 전부 **적어 두고 안 부친 규칙**이다:

    --persona        axes 경로가 style.narrator() 를 안 부른다 -- 문장론이 한 줄도 안 간다
    첫회차 열넷      디렉터의 카드에만 실렸다 -- 첫 쪽을 쓰는 호출은 못 봤다
    echo.check       복사를 잡고도 "원고는 그대로 쓴다" 로 흘려보냈다
    GENRE 빈 값      도착지도 카드도 안 서고 이야기 층이 통째로 꺼진다

넷 다 **원고는 멀쩡히 나온다.** 그래서 아무도 안 알아챈다 -- 사용자는 "성능이
저하되는 것 같다" 로만 알아챌 수 있었다. 한 번은 실수지만 넷은 절차의 결손이다.

## 무엇을 보나

    배선   집필 프롬프트에 어느 블록이 실제로 실리는가 (켜짐/꺼짐)
    축     재는 축 가운데 몇 개가 실제로 프롬프트를 움직이는가
    손     잡은 것이 원고를 고치는가, 로그에만 남는가
    손잡이 환경변수 기본값이 무엇을 끄고 있는가 · 값이 뜻이 있는가
    모듈   flow 에서 도달하지 못하는 모듈 (연장인가, 안 이어진 것인가)

**바늘은 손으로 적지 않는다.** 블록이 실렸는지는 그 블록을 만드는 함수의 출력을
그대로 찾아서 본다 -- 손으로 적은 낱말로 찾다가 거짓 음성을 냈다(실측 2026-09-09:
"닿을 자리" 로 찾았는데 실제 머리표는 "[어디로]" 였다). **잘못 답하는 자는
없느니만 못하다.**

실행:  python3 -m novel.audit            # 흉내 원고로
       python3 -m novel.audit --book <원고.json>
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


# ---------------------------------------------------------------- 배선

def _needle(produced: str, prompt: str, n: int = 40) -> bool:
    """만든 쪽의 출력을 바늘로 쓴다. 빈 것이면 애초에 안 만든 것이라 꺼짐."""
    s = (produced or "").strip()
    if not s:
        return False
    head = s[:n].strip()
    return bool(head) and head in prompt


def wiring(book: dict) -> list:
    """(이름, 상태, 왜). 프롬프트를 실제로 지어 보고 센다.

    상태는 셋이다 -- **꺼짐과 '차례가 아님' 을 가른다.** 개그는 한 덩어리 걸러 실리고
    첫 쪽 규율은 첫 덩어리에만 실린다. 그것을 다 '꺼짐' 이라고 하면 이 자가 늑대소년이
    되고, 그러면 진짜 꺼진 것이 그 속에 묻힌다."""
    from novel import flow, beat as BT, serial as SR, genre as GN, space as SP
    p = flow.write_prompt(book)
    seed = str(book.get("seed_id") or book.get("first") or "")
    nn = len(book.get("chunks") or [])
    g = book.get("genre") or ""
    card = book.get("card") or {}
    inside = BT.brief(book)
    heat = float(book.get("heat") or 0)
    layer = getattr(flow, "LAYER", "text")

    rows = []

    def add(name, on, why, skip=""):
        """`skip` 이 있으면 꺼져 있어도 그것은 차례가 아닌 것이다."""
        rows.append((name, "켜짐" if on else ("차례아님" if skip else "꺼짐"), skip or why))

    add("회차 각본", _needle(BT.brief(book), p), "비트 · 쾌감 · 갈고리 (beat.brief)")
    add("당김", _needle(SR.brief(book), p), "이 대목이 향하는 곳 (serial.brief)")
    add("갈래 꾸러미", _needle(GN.brief(g, seed, nn), p), "엔진 · 화법 · 부름 (genre.brief)")
    add("세계 원장", _needle(flow.brief(book.get("ledger") or {}, now=nn), p),
        "인물 · 장소 · 사물 · 사실")
    add("축 지시문", bool(re.search(r"문장이 (짧|길)다|따옴표를 열|대사 줄|이름이", p)),
        "어긋난 축을 고치라는 말 (dyn.asks)")
    add("쾌감", "**쾌감**" in inside, "회차마다 통쾌한 자리 하나",
        "" if card.get("쾌감") else "카드에 쾌감이 없다")
    add("싸움 · 액션", "**싸움**" in inside, "다섯 박 · 부위 · 기전",
        "" if card.get("전투") else "이 회차에 싸움이 없다")
    add("부상(영구)", "부위를 댄다" in inside, "해부학 이름 · 기전 · 안 낫는다",
        "" if card.get("전투") else "싸움이 있는 덩어리에만")
    add("개그", "낙차" in inside or "무표정" in inside, "분위기 전환",
        "" if nn % 2 == 1 else f"한 덩어리 걸러 (지금 {nn}번째)")
    add("연출", "· 연출:" in inside, "카메라워크 · 등장")
    add("대사 문법", "· 대사:" in inside, "決め台詞 · 名乗り · 츳코미")
    add("판이 바뀜", "달라져 있는 것" in inside, "회차가 닫힐 때 무엇이 달라지나",
        "" if (card.get("바뀜") or {}).get("무엇") else "카드에 바뀜이 없다")
    add("설정집", "설정집" in inside, "각본이 세운 직함 · 등급 · 법칙",
        "" if BT.codex(book) else "아직 세운 설정이 없다")
    add("수위 조건", "어른만" in inside, "조건이라 늘 실린다")
    add("수위 본보기", _needle(SP.render("수위", seed, nn, 1, skip=SP.HEAD["수위"]), p, 20),
        "단계 · 지연 · 여운", "" if heat > 0 else "HEAT 이 꺼져 있다")
    add("첫 쪽 규율", "첫 쪽이다" in inside, "이미 벌어지고 있다 · 설명하지 않는다",
        "" if nn == 0 else f"첫 덩어리에만 (지금 {nn}번째)")
    add("사건(shock)", "급발진" in p or "이번 대목에 일어나는 일" in p,
        "무작위 사건", "카드가 대신한다" if BT.has(book)
        else ("" if layer == "all" else f"DRIFT_LAYER={layer} (all 이라야)"))
    add("확산(diffusion)", "넓혀라" in p or "회수" in p, "넓히고 회수한다",
        "" if layer == "all" else f"DRIFT_LAYER={layer} (all 이라야)")
    return rows


# ---------------------------------------------------------------- 축

def axes() -> dict:
    """재는 축 가운데 몇 개가 프롬프트를 움직이나."""
    from novel import profile as PF, targets as TG, genre as GN
    d = json.loads((ROOT / "directives.json").read_text(encoding="utf-8"))["axes"]
    live, dead, mute = [], [], []
    for k in PF.AXES:
        banded = bool(TG.band(k)) or any(GN.band(n, k) for n in GN.names())
        says = "high" in (d.get(k) or {}) or "low" in (d.get(k) or {})
        (live if banded and says else mute if banded else dead).append(k)
    return {"live": live, "mute": mute, "dead": dead}


# ---------------------------------------------------------------- 손

def hands() -> dict:
    """잡은 것이 원고를 고치는가, 장부에만 남는가. flow 의 소스를 읽어 센다."""
    src = (ROOT / "flow.py").read_text(encoding="utf-8")
    fix = sorted(set(re.findall(r"text,? [\w, ]*= *(\w+)\.(\w+)\(", src))
                 | set(re.findall(r"text = (\w+)\.(\w+)\(", src)))
    logged = re.findall(r"(\w+)\.check\(", src)
    return {"고침": [f"{a}.{b}" for a, b in fix], "장부에만": sorted(set(logged))}


# ---------------------------------------------------------------- 손잡이

_ENV = re.compile(r'os\.environ\.get\(\s*"([A-Z_0-9]+)"\s*,\s*"([^"]*)"\s*\)')


def knobs() -> list:
    """(이름, 기본값, 파일, 꺼짐인가). 기본값이 기능을 끄고 있는 것들."""
    out = []
    for p in sorted(ROOT.glob("*.py")):
        for m in _ENV.finditer(p.read_text(encoding="utf-8")):
            name, val = m.group(1), m.group(2)
            out.append((name, val, p.name, val in ("0", "0.0", "", "false", "text", "none")))
    return out


def switches() -> list:
    """**값이 뜻이 없는 손잡이.** 0~1 로 받아 놓고 `> 0` 로만 쓰면 그것은 스위치다.

    사용자는 HEAT=0.6 을 세기로 알고 준다. 실제로는 0.6 도 1.0 도 같다."""
    out = []
    src = "\n".join(p.read_text(encoding="utf-8") for p in ROOT.glob("*.py"))
    for key in ("heat", "trait", "bond", "matter", "drift", "bridge", "doubt", "pov"):
        uses = re.findall(rf'book(?:\.get\(|\[)["\']{key}["\']\)?[^\n]*', src)
        real = [u for u in uses if re.search(r"[<>]=?\s*[0-9.]+|\*|_level|rand|scale", u)]
        cmp0 = [u for u in real if re.search(r">\s*0\b", u)]
        if real and len(cmp0) == len(real):
            out.append((key, len(real)))
    return out


# ---------------------------------------------------------------- 인자

SH = ROOT.parent / "scripts" / "drift.sh"


def flags(sh_path=None) -> dict:
    """**drift.sh 가 넘기는 인자를 flow 가 받는가.**

    실측 2026-09-09: drift.sh 가 `--body` 를 넘기는데 flow 에는 그런 인자가 없다.
    문서에 적힌 손잡이(BODY)를 쓰면 런이 **아예 안 뜬다** --
    `flow.py: error: unrecognized arguments: --body 0.5`. 두 자리(start · go) 다.

    줄 이음(`\`)을 먼저 펴고 본다. 처음에 안 펴고 찾았다가 이 버그를 **놓쳤다** --
    `--body` 가 `set --` 의 둘째 줄에 있었다. 못 잡는 자는 없느니만 못하다."""
    path = Path(sh_path) if sh_path else SH
    if not path.exists():
        return {"넘긴다": [], "안 받는다": [], "_없다": True}
    sh = re.sub(r"\\\n\s*", " ", path.read_text(encoding="utf-8"))
    fl = (ROOT / "flow.py").read_text(encoding="utf-8")
    ok = set(re.findall(r'add_argument\("--([a-z][a-z-]*)"', fl))
    sent = set()
    for line in sh.splitlines():
        if "$FLOW" in line or "set -- --out" in line or "--resume" in line:
            sent |= set(re.findall(r"--([a-z][a-z-]*)", line))
    return {"넘긴다": sorted(sent), "안 받는다": sorted(sent - ok)}


# ---------------------------------------------------------------- 모듈

def orphans() -> list:
    """flow 에서 도달하지 못하는 모듈. 연장일 수도, 안 이어진 것일 수도 있다."""
    mods = {p.stem for p in ROOT.glob("*.py") if p.stem != "__init__"}
    edges = {}
    for p in ROOT.glob("*.py"):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        used = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("novel"):
                used |= {a.name for a in n.names if a.name in mods}
            elif isinstance(n, ast.Import):
                used |= {a.name.split(".")[-1] for a in n.names
                         if a.name.startswith("novel") and a.name.split(".")[-1] in mods}
        edges[p.stem] = used
    seen, stack = set(), ["flow"]
    while stack:
        m = stack.pop()
        if m in seen:
            continue
        seen.add(m)
        stack.extend(edges.get(m, ()))
    return sorted(mods - seen)


# **혼자 도는 연장들.** 집필 경로에 없는 것이 맞다 -- 명령줄에서 따로 부른다.
# 여기 없는 고아가 나오면 그것은 **안 이어진 것**일 수 있으니 사람이 본다.
TOOLS = {"corpus", "deliver", "discord_check", "gate", "overnight", "read", "seed",
         "tuner", "watch", "world_abc", "world_probe", "world_romance", "world_seeded",
         "verify_pipeline", "first", "audit", "arms", "state", "repair_ops", "plots",
         "arc", "episode", "verbs"}


# ---------------------------------------------------------------- 흉내 원고

def sample(genre: str = "lanobe", heat: float = 0.6, chunks: int = 2) -> dict:
    """점검용 원고. 카드까지 세워 둔다 -- **가짜 LLM 이라 산문은 안 짓는다.**"""
    from novel import flow, beat as BT
    card = {"질문": "무엇을 받아낸다", "방해": "누가 막는다",
            "비트": [{"무엇": "격이 갈린다", "꼴": "장면"},
                    {"무엇": "며칠이 지난다", "꼴": "요약"},
                    {"무엇": "답이 갈린다", "꼴": "장면"}],
            "답": "반만", "갈고리종류": "박탈", "갈고리": "명부가 덮인다",
            "쾌감": "무릎 꿇는 자가 생긴다", "쾌감자리": 3, "전투": "둘이 붙는다",
            "설정": "", "심음": "", "바뀜": {"축": "처지", "무엇": "자리가 생긴다"}}

    def fake(prompt):
        return json.dumps(card, ensure_ascii=False) if "회차**의 각본" in prompt else "{}"

    b = flow.blank("첫 문장이다.")
    b["seed_id"] = "점검"; b["genre"] = genre; b["_target"] = 200_000; b["heat"] = heat
    b["chunks"] = ["가" * 3200] * chunks
    if genre:
        b["arc"] = {"end": "끝", "start": "시작", "made": genre,
                    "debts": [{"무엇": f"빚{i}", "갚음": 0} for i in range(5)]}
        BT.ensure(b, fake)
    return b


# ---------------------------------------------------------------- 보고

def report(book: dict) -> str:
    from novel import flow
    out, w = [], wiring(book)
    on = [r for r in w if r[1] == "켜짐"]
    off = [r for r in w if r[1] == "꺼짐"]
    p = flow.write_prompt(book)
    out.append(f"[배선]  갈래 {book.get('genre') or '(없음)'} · 수위 {book.get('heat') or 0}"
               f" · 층 {flow.LAYER} · 프롬프트 {len(p):,}자")
    out.append(f"        켜짐 {len(on)} · 차례아님 {len(w) - len(on) - len(off)} · **꺼짐 {len(off)}**")
    for name, state, why in w:
        out.append(f"    {state:<5} {name:<12} {why}")
    if off:
        out.append("    ** 위의 '꺼짐' 은 차례 문제가 아니다 -- 실려야 하는데 안 실린 것이다.")

    a = axes()
    out.append(f"\n[축]    재는 축 {sum(len(v) for v in a.values())}개")
    out.append(f"    프롬프트를 움직인다  {len(a['live']):3d}개  {', '.join(a['live'])}")
    if a["mute"]:
        out.append(f"    폭은 있는데 말이 없다 {len(a['mute']):3d}개  {', '.join(a['mute'])}"
                   "   ← 밴드만 두면 손질 루프가 조용하다")
    out.append(f"    재기만 한다          {len(a['dead']):3d}개  (점수와 밤샘 학습으로 간다)")

    h = hands()
    out.append(f"\n[손]    원고를 고친다: {', '.join(h['고침']) or '없음'}")
    out.append(f"        장부에만 남는다: {', '.join(x + '.check' for x in h['장부에만'])}"
               "\n        ← 정도의 문제는 다음 덩어리가 고친다. 통째로 복사한 줄은 echo.dedup 이 지운다.")

    off = [k for k in knobs() if k[3]]
    out.append(f"\n[손잡이] 기본값이 끄고 있는 것 {len(off)}개")
    for name, val, f, _ in off:
        out.append(f"    {name:<18} = {val!r:<8} ({f})")
    sw = switches()
    if sw:
        out.append("    **값이 뜻이 없는 것** (0~1 로 받고 `> 0` 로만 쓴다):")
        for key, n in sw:
            out.append(f"      {key:<8} 켜짐/꺼짐일 뿐이다 -- 0.6 도 1.0 도 같다")

    fg = flags()
    out.append(f"\n[인자]  drift.sh 가 flow 로 넘기는 것 {len(fg['넘긴다'])}개")
    if fg.get("_없다"):
        out.append("    drift.sh 를 못 찾았다 -- 건너뛴다")
    elif fg["안 받는다"]:
        out.append(f"    ** flow 가 안 받는 인자: {', '.join('--' + x for x in fg['안 받는다'])}"
                   "\n       ← 이 손잡이를 쓰면 런이 아예 안 뜬다(unrecognized arguments)")
    else:
        out.append("    전부 받는다")

    orp = [m for m in orphans() if m not in TOOLS]
    out.append(f"\n[모듈]  flow 에서 도달 못 하는 것 {len(orphans())}개"
               f" · 그중 연장이 아닌 것 {len(orp)}개")
    if orp:
        out.append(f"    ** {', '.join(orp)}   ← 연장이면 audit.TOOLS 에 적고, 아니면 안 이어진 것이다")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="파이프라인 점검 -- 적어 둔 것이 부쳐지는가")
    ap.add_argument("--book", default="", help="실제 원고 JSON (없으면 흉내 원고)")
    ap.add_argument("--genre", default="lanobe", help="흉내 원고의 갈래 (빈 값으로 꺼진 꼴을 본다)")
    ap.add_argument("--heat", type=float, default=0.6)
    a = ap.parse_args(argv)
    if a.book:
        b = json.loads(Path(a.book).read_text(encoding="utf-8"))
        print(f"원고: {a.book}  덩어리 {len(b.get('chunks') or [])}개\n")
    else:
        b = sample(a.genre, a.heat)
        print(f"흉내 원고 (갈래 {a.genre or '(없음)'} · 수위 {a.heat})\n")
    print(report(b))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
