"""graph/night -- 밤일. 쌓인 기록을 간추려 깃발 색인으로 만든다.

사람이 잘 때 기억이 굳는 것에서 이름을 땄지만, **버리는 압축이 아니다** -- 원본은
git 에 그대로 있고 여기서는 깃발+요약+해시(찾는 길)만 만든다. 지우는 쪽 밤일은
따로 있다(`memory_hygiene.py` -- 코드와 모순된 노트를 지운다). 둘은 다른 일이라
두 벌이 아니다: 거기는 잊기, 여기는 간추리기.

무엇을 간추리나: public_agent_memory/*.md (에이전트가 쌓는 노트) · reports/*.md.
이미 같은 해시로 간추린 것은 건너뛴다 -- 밤마다 돌려도 원장이 안 부푼다. 원본이
바뀌었으면 새 줄로 다시 간추린다(조회는 최신만 본다).

깃발과 요약은 기본으로 **코드가 뽑는다**(파일 이름 · topic 머리말 · 본문 잦은 낱말 ·
연월). `--모델` 이면 Gemini 가 요약·깃발을 **제안**하는데, 채택은 verify.대조(수치·
깃발·근거율이 원문에 서 있는가)를 **통과한 것만** 이다 -- 퇴짜면 코드 요약으로
물러서고 퇴짜 사유를 그대로 보고한다. 모델은 제안하고 코드가 판정한다.

쓰기:
    python3 graph/night.py            # 간추린다 (몇 개 적었는지 말한다)
    python3 graph/night.py --모델     # Gemini 제안 + 대조 검증 (키 없으면 안 돌린다)
    python3 graph/night.py --보고만    # 무엇을 간추릴지 보기만
밤 루프로 돌리려면 scripts/night.sh (setsid 패턴은 CLAUDE.md).
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from graph import store, verify
else:
    from graph import store, verify

REPO = store.REPO
간추릴곳 = ("public_agent_memory", "reports")

_불용 = verify.불용            # 한 벌만 -- 두 목록은 언젠가 갈라진다
_말꼴 = re.compile(r"[0-9A-Za-z가-힣_.-]{2,}")


def _머리말(text: str) -> "tuple[str, str]":
    """(topic, 본문). frontmatter(--- ... ---)가 있으면 topic 을 뽑고 본문에서 뗀다."""
    topic = ""
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            head, body = text[:end], text[end + 4:]
            m = re.search(r"^topic:\s*['\"]?(.+?)['\"]?\s*$", head, re.M)
            if m:
                topic = m.group(1)
    return topic, body


_이름조각 = re.compile(r"[0-9A-Za-z가-힣]{2,}")


def 깃발뽑기(이름: str, topic: str, 본문: str) -> "list[str]":
    """파일 이름 조각 + topic 조각 + 본문에서 잦은 낱말 + 연월. 전부 코드가 뽑는다.

    이름은 `_이름조각` 으로 -- `_말꼴` 로 뽑으면 `-_.` 가 이어져 **파일 이름 전체가
    깃발 하나**가 되고, 그것은 노드마다 유일해서 기준선 판정을 전부 이례로 쏠리게
    한다(검사가 실측으로 잡았다). 아무도 파일 이름 전체로 검색하지 않는다 -- 조각으로
    검색한다."""
    깃발: list[str] = []
    m = re.match(r"(\d{6})", 이름)
    if m:
        깃발.append(m.group(1))          # 연월 -- "그때쯤 그거" 로 찾는 길
    for 조각 in _이름조각.findall(이름) + _말꼴.findall(topic):
        if not 조각.isdigit() and 조각.lower() not in _불용 and 조각.lower() != "md":
            깃발.append(조각)
    잦은 = Counter(w.lower() for w in _말꼴.findall(본문)
                  if not w.isdigit() and w.lower() not in _불용)
    깃발.extend(w for w, c in 잦은.most_common(5) if c >= 2)
    return store.깃발정리(깃발)


def 요약뽑기(본문: str, 길이: int = 500) -> str:
    return " ".join(본문.split())[:길이]


def 대상들(repo: Path) -> "list[Path]":
    out: list[Path] = []
    for d in 간추릴곳:
        base = repo / d
        if base.is_dir():
            out.extend(sorted(base.glob("*.md")))
    return out


def 간추리기(repo=None, 적기=True, 요약기=None) -> dict:
    """돌고 나서 {적음: [...], 그대로: n, 거절: [...], 퇴짜: [...]} 를 돌려준다.

    요약기: 선택. (파일이름, topic, 본문) -> {"요약": str, "깃발": [...]} 를 내는
    호출 가능(대개 모델). **제안일 뿐이다** -- verify.대조 를 통과해야 채택되고,
    퇴짜면 코드 요약으로 물러서며 사유가 퇴짜 목록에 남는다. 요약기가 죽어도
    밤일은 계속된다(그 파일만 코드 요약)."""
    repo = Path(repo or REPO)
    nodes, _ = store.읽기(repo)
    이미 = {(n.get("출처"), n.get("해시")) for n in nodes}
    적음, 거절, 퇴짜 = [], [], []
    그대로 = 0
    for p in 대상들(repo):
        rel = str(p.relative_to(repo))
        if (rel, store.해시(p)) in 이미:
            그대로 += 1
            continue
        topic, body = _머리말(p.read_text(encoding="utf-8", errors="replace"))
        if not 적기:
            적음.append(rel)
            continue
        요약 = 요약뽑기(body)
        깃발 = 깃발뽑기(p.name, topic, body)
        지은이 = "코드"
        if 요약기 is not None:
            try:
                제안 = 요약기(p.name, topic, body) or {}
            except Exception as e:
                제안 = {}
                퇴짜.append(f"{rel}: 요약기가 죽었다 ({type(e).__name__}: {e})")
            제안요약 = " ".join(str(제안.get("요약", "")).split())
            제안깃발 = store.깃발정리(깃발 + list(제안.get("깃발", [])))
            if 제안요약:
                판 = verify.대조(제안요약, 제안깃발, body, 이름=f"{p.name} {topic}")
                if 판["판정"] == "맞음":
                    요약, 깃발, 지은이 = 제안요약, 제안깃발, "모델(대조통과)"
                else:
                    퇴짜.append(f"{rel}: {판['판정']} -- {'; '.join(판['위반']) or '잰 것 없음'}")
        try:
            r = store.적기(요약, 깃발, rel, repo=repo, 지은이=지은이)
        except ValueError as e:
            거절.append(f"{rel}: {e}")
            continue
        if r == "적었다":
            적음.append(rel)
        else:
            그대로 += 1
    return {"적음": 적음, "그대로": 그대로, "거절": 거절, "퇴짜": 퇴짜}


def 모델요약기():
    """Gemini 로 요약·깃발을 제안하는 요약기를 만든다. 키가 없거나 bot_tools 를 못
    들이면 RuntimeError -- **못 돌리면 못 돌린다고 말한다**, 다른 모델로 대신하지
    않는다(novel 의 규율). 프롬프트에는 검사 내용을 한 글자도 안 적는다 -- 알려 주면
    통과하는 요약이 나오고 검사가 사양서가 된다."""
    import os
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY_FALLBACK")
    if not key:
        raise RuntimeError("GEMINI_API_KEY 가 없다")
    try:
        import bot_tools
    except Exception as e:
        raise RuntimeError(f"bot_tools 를 못 들인다: {type(e).__name__}: {e}")
    import json as _json

    def 요약기(이름: str, topic: str, body: str) -> dict:
        물음 = ("다음 글을 300자 안에서 간추리고, 나중에 찾을 때 쓸 꼬리표를 3~6개 "
               '제안하라. JSON 하나만 내라: {"요약": "...", "깃발": ["...", "..."]}\n\n'
               + body[:6000])
        답 = bot_tools.invoke_text(물음, key, pool_id="graph-night", log_prefix="[night]")
        m = re.search(r"\{.*\}", 답, re.S)
        got = _json.loads(m.group(0)) if m else {}
        return {"요약": got.get("요약", ""), "깃발": got.get("깃발", [])}

    return 요약기


def main() -> int:
    ap = argparse.ArgumentParser(description="쌓인 기록을 깃발 색인으로 간추린다")
    ap.add_argument("--보고만", action="store_true", help="적지 않고 무엇을 간추릴지만")
    ap.add_argument("--모델", action="store_true",
                    help="Gemini 제안 + 대조 검증. 키가 없으면 안 돌린다")
    args = ap.parse_args()
    요약기 = None
    if args.모델:
        try:
            요약기 = 모델요약기()
        except RuntimeError as e:
            print(f"모델을 못 부른다: {e} -- 안 돌린다 (코드 요약으로 돌리려면 --모델 없이)")
            return 3
    r = 간추리기(적기=not args.보고만, 요약기=요약기)
    동사 = "간추릴 것" if args.보고만 else "간추림"
    print(f"{동사} {len(r['적음'])}개 · 이미 있음 {r['그대로']}개 · 거절 {len(r['거절'])}개"
          + (f" · 모델 퇴짜 {len(r['퇴짜'])}개" if r["퇴짜"] else ""))
    for rel in r["적음"][:20]:
        print(f"  + {rel}")
    for why in r["거절"]:
        print(f"  ! {why}")
    for why in r["퇴짜"]:
        print(f"  퇴짜 {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
