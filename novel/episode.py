"""에피소드의 역방향 조립 -- **결과를 먼저 정하고 인과를 거꾸로 세운다.**

보고서: "달성하고자 하는 '결과'를 먼저 정한 후 이를 인과관계에 따라 역방향으로 조립하여
개연성을 확보한다."

순방향으로 쓰면 이야기가 배회한다. 각 씬이 다음 씬을 낳지만 어디로 가는지는 아무도 모르고,
10화쯤 뒤에 "그래서 이게 왜 필요했지" 가 남는다. 역방향은 목표 지향이라 그 씬이 존재하는
이유가 구조에 박힌다.

**여기서 얻는 진짜 값어치는 검증이다.** 비트마다 requires(성립하려면 이미 참이어야 하는 것)
와 establishes(이 비트가 참으로 만드는 것)를 선언하게 하면,

    개연성 구멍 = 어떤 비트의 requires 가 앞의 어떤 establishes 로도, 에피소드 진입 상태
                  로도 충족되지 않는 것

이 된다. 즉 **플롯 구멍이 그래프 도달 가능성 문제로 환원된다.** 사람이 읽어서 "어색하다"고
느끼는 것을 기계가 "48번 비트의 요구 '주인공이 열쇠를 갖고 있다' 가 아무 데서도 성립되지
않는다"로 짚는다.

조건의 두 종류:
    state: 접두사   -- 원장에 대고 실제로 판정한다 (관계·지식·부재)
    맨 문자열       -- 다른 비트의 establishes 와 문자열로 대조한다

맨 문자열은 오타가 곧 구멍으로 나타난다. 그게 맞다 -- 조용히 통과하는 것보다 시끄럽게
틀리는 편이 낫다. 다만 비슷한 문자열이 있으면 오타로 짚어준다.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field


@dataclass
class Beat:
    """한 씬 분량의 사건. requires/establishes 가 인과의 배선이다."""
    beat: str
    participants: list = field(default_factory=list)
    mode: str = "dialogue"
    requires: list = field(default_factory=list)
    establishes: list = field(default_factory=list)
    world_ops: list = field(default_factory=list)
    relation_ops: list = field(default_factory=list)
    scale: int = 0
    cliffhanger: str = ""
    direction: dict = field(default_factory=dict)


@dataclass
class Outcome:
    """에피소드가 도달할 결말. **가장 먼저 정한다.**"""
    summary: str
    requires: list = field(default_factory=list)
    world_ops: list = field(default_factory=list)
    relation_ops: list = field(default_factory=list)


@dataclass
class Episode:
    n: int
    outcome: Outcome
    beats: list = field(default_factory=list)      # 시간 순서 (조립은 역순으로 했다)
    episodes: tuple = (0, 0)                       # 회차 범위


# ---------------------------------------------------------------- 조건 판정

def eval_state(cond: str, novel, upto_scene: str) -> bool:
    """state: 조건을 원장에 대고 판정한다. 형태:
        state:rel:연인:A,B      관계가 살아 있다
        state:knows:A:비밀      A 가 안다
        state:absent:D          D 가 없다
    앞에 not: 를 붙이면 부정. 예: state:not:rel:연인:A,B"""
    body = cond[len("state:"):]
    neg = body.startswith("not:")
    if neg:
        body = body[len("not:"):]
    parts = body.split(":")
    kind = parts[0]

    val = False
    if kind == "rel" and len(parts) >= 3:
        want, members = parts[1], set(parts[2].split(","))
        val = any(r.kind == want and set(r.members) == members
                  for r in novel.active_relations(upto_scene))
    elif kind == "knows" and len(parts) >= 3:
        from .gate import _knowers
        val = parts[1] in _knowers(novel, ":".join(parts[2:]), upto_scene)
    elif kind == "absent" and len(parts) >= 2:
        idx = novel.scene_index(upto_scene)
        gates, _ = novel.derive_gates(idx)
        val = any(g.kind in ("absence", "absence_physical")
                  and g.params.get("who") == parts[1]
                  and novel.scene_index(g.from_scene) <= idx for g in gates)
    else:
        raise ValueError(f"알 수 없는 state 조건: {cond!r}")
    return (not val) if neg else val


def check_causality(episode: Episode, entry: set = None, novel=None,
                    upto_scene: str = None) -> list:
    """개연성 사슬 검사. 충족되지 않은 요구 목록을 돌려준다(빈 목록이면 통과).

    각 항목 (등급, 비트 번호, 조건, 설명). 진입 상태(entry)는 에피소드 시작 시점에 이미
    참인 것들이다."""
    have = set(entry or ())
    holes = []
    seq = list(episode.beats) + [Beat(beat="[결말] " + episode.outcome.summary,
                                      requires=episode.outcome.requires)]

    for i, b in enumerate(seq):
        for cond in b.requires or []:
            if cond.startswith("state:"):
                if novel is None:
                    continue                    # 원장 없이는 판정하지 않는다
                try:
                    if eval_state(cond, novel, upto_scene or novel.scenes[-1].id):
                        continue
                except ValueError as e:
                    holes.append(("hard", i, cond, str(e)))
                    continue
                holes.append(("hard", i, cond,
                              f"원장이 이 조건을 만족하지 않는다"))
                continue
            if cond in have:
                continue
            near = difflib.get_close_matches(cond, have, n=1, cutoff=0.75)
            if near:
                holes.append(("soft", i, cond,
                              f"충족되지 않았지만 비슷한 것이 있다: {near[0]!r} "
                              f"-- 오타이면 맞춰라"))
            else:
                holes.append(("hard", i, cond,
                              f"이 요구를 성립시키는 비트가 앞에 없다. 개연성 구멍이다"))
        have.update(b.establishes or [])
    return holes


# ---------------------------------------------------------------- 역방향 조립

def assemble_backward(outcome: Outcome, entry: set, library, max_beats: int = 12) -> tuple:
    """결말에서 시작해 거꾸로 비트를 쌓는다. 반환 (시간순 비트 목록, 남은 미충족 조건).

    library 는 후보 비트 목록이다. 각 라운드에서 **아직 열려 있는 요구를 성립시키는** 비트만
    고른다 -- 그래서 나온 사슬의 모든 비트에는 존재 이유가 있다. 순방향으로 뽑으면 그
    보장이 없다."""
    open_conds = [c for c in outcome.requires if c not in entry and not c.startswith("state:")]
    chain = []

    for _ in range(max_beats):
        if not open_conds:
            break
        target = open_conds[0]
        cand = next((b for b in library
                     if target in (b.establishes or []) and b not in chain), None)
        if cand is None:
            break                                    # 라이브러리가 못 메운다 -- 구멍으로 남는다
        chain.append(cand)
        open_conds = [c for c in open_conds if c not in (cand.establishes or [])]
        for c in cand.requires or []:
            if c not in entry and not c.startswith("state:") and c not in open_conds:
                if not any(c in (b.establishes or []) for b in chain):
                    open_conds.append(c)

    chain.reverse()                                  # 거꾸로 쌓았으니 뒤집으면 시간순
    return chain, open_conds


def to_scenes(episode: Episode, prefix="e", start_ep: int = 0):
    """비트를 Scene 으로. 마지막 비트가 회차의 끝이 된다."""
    from .state import Scene
    out = []
    for i, b in enumerate(episode.beats):
        last = i == len(episode.beats) - 1
        out.append(Scene(
            id=f"{prefix}{episode.n:02d}s{i + 1:02d}",
            participants=list(b.participants), mode=b.mode,
            directives=[b.beat], world_ops=list(b.world_ops),
            relation_ops=list(b.relation_ops), scale=b.scale,
            requires=list(b.requires or []), establishes=list(b.establishes or []),
            direction=dict(b.direction or {}),
            episode=start_ep + i if start_ep else 0,
            is_episode_end=last, cliffhanger=b.cliffhanger if last else ""))
    return out
