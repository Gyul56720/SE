"""검증된 플롯 템플릿과 무작위 조합기.

목적: **무작위로 섞어도 세계가 자기모순이 되지 않게.**

그냥 사건을 무작위로 뽑으면 "A 가 B 와 사귀는 중인데 C 와 사귄다" 같은 것이 바로 나온다.
그렇다고 검사를 빡빡하게 걸면 재미있는 전개가 다 막힌다. 답은 검사를 조이는 것이 아니라
**조합 단계에서 이미 성립하는 것만 뽑는 것**이다.

그래서 템플릿마다 requires / provides 를 둔다. 조합기는 현재 세계 상태를 들고 다니며
전제가 맞는 템플릿만 고른다 -- 작은 계획 문제가 되고, 나온 사슬은 정의상 관문을 통과한다.
관문은 그 뒤에 **최소한**만 본다.

템플릿은 사건의 뼈대만 준다. 장소·푼크툼·대사는 Director 가 채운다.
어휘는 무라카미(상실·실종·편지·모티프)와 피츠제럴드(날조·파티·누명·몰락)에서 가져왔다.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class Beat:
    """한 씬 분량의 사건 뼈대."""
    beat: str                                   # 이 씬이 무엇인가 (Director 에게 주는 씨앗)
    participants: list = field(default_factory=list)
    mode: str = "dialogue"                      # dialogue | letter | reported
    world_ops: list = field(default_factory=list)
    relation_ops: list = field(default_factory=list)
    flashback: bool = False


@dataclass
class Plot:
    name: str
    ko: str                                     # 사람이 읽는 이름
    roles: tuple                                # 필요한 배역
    tags: tuple                                 # 분위기 태그
    budget: int = 0                             # 공리 예산 소모
    requires: dict = field(default_factory=dict)
    provides: dict = field(default_factory=dict)
    build: object = None                        # (역할맵) -> [Beat]


def _P(name, ko, roles, tags, build, budget=0, requires=None, provides=None):
    return Plot(name=name, ko=ko, roles=roles, tags=tags, budget=budget,
                requires=requires or {}, provides=provides or {}, build=build)


# ---------------------------------------------------------------- 템플릿들

def _transfer(r):
    a, b, c = r["a"], r["b"], r["c"]
    return [
        Beat(f"{a}·{b} 의 익숙한 저녁. 둘 다 말하지 않는 것이 하나씩 있다",
             [a, b], relation_ops=[{"op": "start", "kind": "연인", "members": [a, b]}],
             world_ops=[{"event": "motif", "name": "그라인더가 멎은 뒤의 정적",
                         "sense": "청각"}]),
        Beat(f"{a} 가 {c} 를 처음 본다. 다른 시간대의 사람이라는 것만 안다",
             [a, c], world_ops=[{"event": "meet", "pair": [a, c]}]),
        Beat(f"{a} 의 마음이 옮겨가는 것을 {a} 자신만 모른다",
             [a, c], world_ops=[{"event": "unrequited", "who": a, "toward": c}]),
        Beat(f"{b} 와 끝난다. 끝내는 쪽이 누구인지 애매하게",
             [a, b], relation_ops=[{"op": "end", "kind": "연인", "members": [a, b]}]),
        Beat(f"{a}·{c} 가 시작된다. 시작인데도 무언가 끝난 것처럼",
             [a, c], relation_ops=[{"op": "start", "kind": "연인", "members": [a, c]}]),
    ]


def _gatsby(r):
    a, c, d = r["a"], r["c"], r["d"]
    return [
        Beat(f"{c} 가 자기 과거를 말한다. 너무 매끄러워서 오히려 이상하다",
             [a, c], world_ops=[{"event": "fabricate", "who": c,
                                 "story": "지어낸 내력", "believed_by": [a, d]}]),
        Beat("사람이 너무 많은 파티. 아무도 주인을 모른다",
             [a, c, d], world_ops=[{"event": "gathering", "who": [a, c, d],
                                    "occasion": "여름의 파티"}]),
        Beat(f"{a} 가 우연히 듣는다. {c} 는 들킨 줄 모른다",
             [a], mode="reported",
             world_ops=[{"event": "overhear", "who": a, "term": "지어낸 내력",
                         "unknown_to": [c]}]),
        Beat(f"{c} 의 이야기가 사람들 앞에서 무너진다",
             [a, c, d], world_ops=[{"event": "expose", "target": c,
                                    "story": "지어낸 내력"}]),
        Beat(f"{c} 가 가진 것을 잃는다. 잃는 장면은 조용하다",
             [a, c], world_ops=[{"event": "ruin", "who": c}]),
    ]


def _false_blame(r):
    a, b, c = r["a"], r["b"], r["c"]
    return [
        Beat("사고. 아무도 예상하지 않았고 아무도 준비되지 않았다",
             [a, b], world_ops=[{"event": "accident", "who": b, "witnesses": [a, c]}]),
        Beat(f"{a} 가 뒤집어쓴다. 스스로 그렇게 되도록 둔다",
             [a, c], world_ops=[{"event": "blame_transfer", "truth_who": c,
                                 "blamed_who": a, "term": "그날 밤의 일"}]),
        Beat("진실을 아는 사람이 아무 말도 하지 않는 계절이 지나간다",
             [a], mode="reported",
             world_ops=[{"event": "season_turn", "to_season": "겨울"}]),
    ]


def _vanishing(r):
    a, d = r["a"], r["d"]
    return [
        Beat(f"{d} 가 사라진다. 마지막으로 본 것이 무엇이었는지 아무도 확실하지 않다",
             [a], world_ops=[{"event": "vanish", "who": d}]),
        Beat(f"{d} 에게서 온 편지. 어디서 부친 것인지 소인이 뭉개져 있다",
             [d], mode="letter"),
        Beat("그 계절 전체의 의미가 뒤늦게 바뀐다",
             [a], mode="reported",
             world_ops=[{"event": "reinterpret", "rereads": ["prev"],
                         "justification": "실종 이후의 재독"}]),
    ]


def _reunion(r):
    a, b = r["a"], r["b"]
    return [
        Beat(f"{b} 가 떠난다. 배웅은 없다",
             [a, b], world_ops=[{"event": "depart", "who": b, "to": "먼 도시"}]),
        Beat("시간이 지나간다. 사람보다 도시가 더 많이 변했다",
             [a], mode="reported", world_ops=[{"event": "timeskip", "amount": "3년"}]),
        Beat(f"{a} 와 {b} 가 다시 만난다. 처음 보는 사람처럼 굴지 않는 것이 더 어렵다",
             [a, b], world_ops=[{"event": "return_", "who": b},
                                {"event": "reunite", "pair": [a, b], "after": "3년"}]),
    ]


def _betrayal(r):
    a, b, c = r["a"], r["b"], r["c"]
    return [
        Beat(f"{a}·{b}·{c} 사이에 삼각이 생긴다. 아무도 그 이름을 부르지 않는다",
             [a, b, c], world_ops=[{"event": "triangle", "center": a, "pair": [b, c]}]),
        Beat(f"{b} 가 {a} 를 배신한다. 관계는 겉으로 유지된다",
             [a, b], world_ops=[{"event": "betray", "who": b, "against": a}]),
        Beat("둘은 서로를 보지 않기로 한다. 말로 정하지는 않는다",
             [a, b], world_ops=[{"event": "sever", "pair": [a, b]}]),
    ]


def _keepsake(r):
    a, c = r["a"], r["c"]
    return [
        Beat(f"{c} 가 {a} 에게 무언가를 준다. 대단하지 않은 물건이다",
             [a, c], world_ops=[{"event": "give_object", "from_whom": c, "to": a,
                                 "thing": "낡은 라이터"}]),
        Beat("그것을 잃어버린다. 잃어버린 줄도 한참 뒤에 안다",
             [a], world_ops=[{"event": "lose_object", "who": a, "thing": "낡은 라이터"}]),
    ]


def _misread(r):
    a, b = r["a"], r["b"]
    return [
        Beat(f"{b} 가 무언가를 잘못 알게 된다. 바로잡을 기회가 몇 번 지나간다",
             [a, b], world_ops=[{"event": "misbelieve", "who": b, "term": "그 밤의 전화",
                                 "believes": "다른 사람이 걸었다"}]),
        Beat("오해 위에서 대화가 계속된다. 둘 다 다른 이야기를 하고 있다",
             [a, b]),
    ]


PLOTS = [
    _P("transfer", "환승", ("a", "b", "c"), ("상실", "청춘", "연애"), _transfer,
       requires={"free": ["a", "b", "c"]},
       provides={"pairs": [("a", "c")], "unpairs": [("a", "b")]}),
    _P("gatsby", "날조와 몰락", ("a", "c", "d"), ("계급", "환멸", "파티"), _gatsby),
    _P("false_blame", "누명", ("a", "b", "c"), ("희생", "침묵"), _false_blame,
       requires={"alive": ["b"]}, provides={"hurt": ["b"]}),
    _P("vanishing", "실종과 편지", ("a", "d"), ("상실", "부재", "편지"), _vanishing,
       budget=1, requires={"alive": ["d"]}, provides={"absent": ["d"]}),
    _P("reunion", "재회", ("a", "b"), ("시간", "거리"), _reunion,
       requires={"present": ["b"]}),
    _P("betrayal", "삼각과 배신", ("a", "b", "c"), ("배신", "청춘"), _betrayal,
       provides={"severed": [("a", "b")]}),
    _P("keepsake", "선물과 상실", ("a", "c"), ("사물", "여운"), _keepsake),
    _P("misread", "오해", ("a", "b"), ("소통불능",), _misread),
]

BY_NAME = {p.name: p for p in PLOTS}


# ---------------------------------------------------------------- 조합기

class WorldState:
    """조합 중에 들고 다니는 최소 상태. 관문의 축약판이다 -- 여기서 미리 걸러야
    관문이 '최소한' 만 보게 된다."""

    def __init__(self, roles):
        self.pairs = set()
        self.absent = set()
        self.severed = set()
        self.roles = set(roles)

    def ok(self, plot, bind) -> bool:
        req = plot.requires
        for r in req.get("free", []):
            who = bind[r]
            if any(who in p for p in self.pairs):
                return False
        for r in req.get("alive", []) + req.get("present", []):
            if bind[r] in self.absent:
                return False
        return True

    def apply(self, plot, bind):
        pr = plot.provides
        for x, y in pr.get("unpairs", []):
            self.pairs.discard(tuple(sorted((bind[x], bind[y]))))
        for x, y in pr.get("pairs", []):
            self.pairs.add(tuple(sorted((bind[x], bind[y]))))
        for r in pr.get("absent", []):
            self.absent.add(bind[r])
        for x, y in pr.get("severed", []):
            self.severed.add(tuple(sorted((bind[x], bind[y]))))


def compose(cast, n=3, seed=None, budget=2):
    """무작위로 n 개 템플릿을 골라 사건 사슬을 만든다. **성립하는 것만 고른다.**

    cast 는 배역 -> 인물 이름. 예: {"a":"A","b":"B","c":"C","d":"D"}
    반환 (Beat 목록, 고른 플롯 이름 목록)."""
    rng = random.Random(seed)
    state = WorldState(cast.values())
    beats, chosen, spent = [], [], 0

    pool = PLOTS[:]
    rng.shuffle(pool)
    for plot in pool:
        if len(chosen) >= n:
            break
        if any(r not in cast for r in plot.roles):
            continue
        if spent + plot.budget > budget:
            continue
        if not state.ok(plot, cast):
            continue
        beats.extend(plot.build(cast))
        state.apply(plot, cast)
        spent += plot.budget
        chosen.append(plot.name)
    return beats, chosen


def to_scenes(beats, prefix="s"):
    """Beat 목록을 Scene 으로. 장소·푼크툼·지시는 비워 둔다 -- Director 가 채운다."""
    from .state import Scene
    return [Scene(id=f"{prefix}{i + 1:02d}", participants=list(b.participants),
                  mode=b.mode, flashback=b.flashback,
                  directives=[b.beat],
                  world_ops=list(b.world_ops), relation_ops=list(b.relation_ops))
            for i, b in enumerate(beats)]
