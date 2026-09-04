"""씨앗 하나를 세계로 편다. **LLM 을 쓰지 않는다** -- 전부 코드다.

씨앗(novel/seed.py)이 정하는 것은 "무엇에 대한 이야기인가" 이고, 여기서 하는 일은 그것을
파이프라인이 먹을 수 있는 모양으로 옮기는 것뿐이다:

    인물 셋      -> Character (이름은 씨앗 id 로 결정론적으로. 모델에게 짓게 하지 않는다)
    불가능한 규칙 -> 세계의 법. 페르소나와 화자 선지식에 실린다
    최초의 사건   -> 첫 블록의 마감과 사건
    상처         -> 비밀(facts.secrets). 정보 격차의 씨앗이 된다
    목소리       -> Novel.voice -> 화자 프롬프트

**한 블록 3화만 만든다.** 씨앗이 쓸 만한지는 3화면 안다. 200화 설계는 그다음 일이다.

씨앗은 novel/seed_current.json 에 저장해두고 여기서 읽는다 -- 실행할 때마다 새로 뽑으면
이어 돌릴 수가 없다.

실행:
    python3 novel/world_seeded.py --new          # 새로 뽑아 저장하고 보여준다
    python3 novel/world_seeded.py                # 지금 저장된 씨앗을 보여준다
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import seed as S                                           # noqa: E402
from novel.state import Novel, Character                              # noqa: E402

HERE = Path(__file__).resolve().parent
CURRENT = HERE / "seed_current.json"


def load_seed() -> dict:
    if not CURRENT.exists():
        raise SystemExit(f"{CURRENT} 가 없다. 먼저: python3 novel/world_seeded.py --new")
    return json.loads(CURRENT.read_text(encoding="utf-8"))


def new_seed(rng_seed=None) -> dict:
    rng = random.Random(rng_seed)
    used = S.used_ids()
    while True:
        s = S.draw(rng)
        if not S.validate(s, used):
            break
    CURRENT.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    return s


def build(seed: dict = None) -> Novel:
    seed = seed or load_seed()
    names = S.cast_names(seed)
    p = seed["people"]
    rule, cost, limit = (seed["impossible"]["rule"], seed["impossible"]["cost"],
                         seed["impossible"]["limit"])
    law = f"{rule} (효과: {cost} · 조건: {limit})"

    chars = []
    for i, (nm, person) in enumerate(zip(names, p)):
        chars.append(Character(
            name=nm,
            # 직업이 아니라 **상처와 태도**로 쓴다. 직업은 인물이 아니다.
            persona=f"{person['who']}. {person['wound']} "
                    f"이 세계의 법을 알고 산다: {law}",
            hidden_agenda=person["wound"],
            knows=[f"{nm}의 상처"],
            # 화자는 꺾여도 다시 서야 한다. 다른 인물은 하한을 낮게 둬 색이 갈리게 한다.
            emotion_envelope={"joy": 30} if i == 0 else {"joy": 20}))

    return Novel(
        title=f"{seed['motif']}",          # 제목은 디렉터가 다듬는다. 여기선 재료만
        pov_character=names[0],
        revision_budget=2,
        seed_id=seed["id"],                # 원고와 세계가 어긋나면 여기서 드러난다
        depth=dict(seed.get("depth") or {}),   # 겉은 가볍고 속은 무겁게
        world=dict(seed.get("world") or {}),   # 게임 설정집 -- 디렉터가 지어내지 않게
        voice=f"{seed['voice']['how']} -- {seed['voice']['note']}",
        narrator_foreknowledge=[
            f"이 이야기는 {seed['theme']}에 대한 것이다",
            f"{seed['motif']}이 마지막에 다시 나온다",
            f"{S.josa(names[1], '이')} 먼저 알고 있었다는 것을 나는 한참 뒤에 알았다",
        ],
        characters=chars,
        facts={
            "secrets": {
                f"{nm}의 상처": {"knows": [nm], "aliases": []}
                for nm in names
            },
            "truths": {
                "세계의 법": law,
                "시간": seed["time"]["note"],
            },
        })


def outcomes(seed: dict = None) -> list:
    """블록 둘로 5화 (회차 5,000자 = 총 2만 5천 자).

    사이다의 결말은 **성취**다. 주인공이 대가를 치르는 구조는 이 장르에서 곧 고구마다.
    되찾고, 편을 늘리고, 누군가 그것을 인정하는 것으로 닫는다.

    그런데 이 소설에는 밑에 깔린 물음이 하나 있다(씨앗의 depth). 그것은 **결말 문장에
    쓰지 않는다** -- 결말은 겉으로 시원해야 하고, 물음은 그 아래에서 시험된다. 여기서
    하는 일은 마지막 블록의 stake 에 그 시험이 걸리게 두는 것뿐이다.

        1~3화  곤경 -> 관계 프레임 -> 첫 역전   (규모 1 · 시계 48)
        4~5화  판을 뒤집고 값을 치른다          (규모 2 · 시계 24)

    3화 법칙은 style.episode_brief 가 1·2·3화에 따로 싣는다."""
    seed = seed or load_seed()
    n = S.cast_names(seed)
    J = S.josa
    rule = seed["impossible"]["rule"]
    # n[0] 화자 · n[1] 처음엔 막아서다 편이 되는 인물 · n[2] 끝까지 반동
    return [
        dict(
            seq=1, eps=(1, 3), scale=1,
            # 마감은 **사건**에 건다. 반칙은 세계의 성질이라 마감 문장으로 쓰면 어색해진다.
            deadline=f"{seed['event']} — 이 판이 넘어가기 전에 뒤집어야 한다",
            deadline_hours=48,
            # **걸린 것은 손해가 아니라 기회다.** 못 이기면 잃는 것으로 쓴다.
            stake=f"놓치면 {J(n[1], '이')} 그 자리를 가져간다",
            steps=[f"{J(n[0], '이')} {seed['event']} — 그 자리에서 목적을 못박는다",
                   f"{J(n[0], '이')} 반칙으로 {n[1]}의 각오를 먼저 읽고 "
                   f"{J(n[1], '을')} 자기 편으로 세운다"],
            summary=f"{J(n[0], '이')} 반칙으로 판을 뒤집고 빼앗겼던 것을 되찾는다 — {rule}. "
                    f"{J(n[2], '이')} 그것을 지켜보고 인정한다",
            requires=[],
            establishes=["빼앗겼던 것을 되찾았다",
                         f"{S.josa(n[0], '과')} {n[1]} 이 같은 편이 됐다"],
            world_ops=[{"event": "meet", "pair": [n[0], n[1]]},
                       {"event": "conceal", "term": f"{n[1]}의 상처",
                        "from_whom": [n[0]]}]),
        dict(
            seq=2, eps=(4, 5), scale=2,
            deadline=f"{n[2]}가 판을 닫기 전에 끝내야 한다",
            deadline_hours=24,
            # 마지막 블록의 stake 에 심층의 시험을 건다. **문장에 사상을 쓰지 않는다** --
            # 무엇을 걸었는지만 적는다. 선택은 디렉터가 장면으로 만든다.
            stake=f"밀리면 지금까지 세운 자리가 한 번에 없어진다",
            steps=[f"{J(n[2], '이')} 남은 힘을 모아 {J(n[0], '을')} 밀어내려 한다",
                   f"{J(n[1], '이')} 자기 몫을 걸고 {n[0]}의 편에 선다"],
            summary=f"{J(n[0], '이')} {n[2]}를 밀어내고 판을 가져간다 — {rule}. "
                    f"그리고 아무에게도 말하지 않은 것이 하나 남는다",
            requires=["빼앗겼던 것을 되찾았다"],
            establishes=["판을 가져갔다"],
            world_ops=[{"event": "expose", "term": f"{n[2]}의 방식",
                        "to_whom": [n[0], n[1]]}]),
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", action="store_true", help="새 씨앗을 뽑아 저장한다")
    ap.add_argument("--rng", type=int, default=None)
    a = ap.parse_args()

    s = new_seed(a.rng) if a.new else load_seed()
    print(S.render(s, long=True))
    nv = build(s)
    print(f"\n인물   {[c.name for c in nv.characters]}  (화자: {nv.pov_character})")
    print(f"목소리 {nv.voice}")
    o = outcomes(s)[0]
    print(f"\n1~3화 마감  {o['deadline']} ({o['deadline_hours']}시간)")
    print(f"       걸린 것 {o['stake']}")
    for i, st in enumerate(o["steps"], 1):
        print(f"       단계{i} {st}")
    print(f"       결말   {o['summary']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
