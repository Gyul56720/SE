"""세계관을 바꾸는 동사의 **닫힌 집합**.

왜 닫혀 있어야 하나. Director 가 임의의 사건 이름을 만들 수 있으면, 모르는 사건은 아무
게이트도 낳지 않고 조용히 통과한다 -- 검증이 있는 척만 하게 된다. 그래서 여기 없는 동사는
hard 위반이다. 새 동사가 필요하면 사람이 이 표에 추가한다. self_challenge.py 가 증명 없이는
게이트를 승격시키지 않는 것과 같은 규율이다.

**모델은 동사를 선언할 뿐 규칙을 쓰지 않는다.** 어떤 검사가 붙는지는 이 표에 고정돼 있다.
Director 에게 게이트를 쓰게 하면 자기에게 관대한 것을 쓴다 -- orchestrator 의 repair_node 가
verifier 를 절대 건드리지 않는 것과 같은 이유다.

여섯 층이고 아래로 갈수록 비싸다. 1~5 층은 세계 **안**의 변화라 예산이 없다. 6층은 세계
**자체**의 변경이라 예산이 붙는다.

    1 존재  2 관계  3 지식  4 속성  5 시공간  ── 세계 안의 사건, 무제한
    6 공리                                    ── 세계 자체의 개정, 예산 제한
"""
from __future__ import annotations

# kind: 이 동사가 낳는 게이트 종류. None 이면 원장만 갱신하고 게이트는 안 낳는다.
# budget: 개정 예산을 소모하는가.
# reversible: 되돌리는 짝 동사.
VERBS = {
    # ---------------------------------------------------------- 1층 · 존재
    "introduce": dict(
        layer="존재", params=("who",), gate="not_before_existence", budget=False,
        reversible=None,
        desc="인물이 세계에 들어온다. 이전 씬에서 그를 아는 척하면 위반이다."),
    "die": dict(
        layer="존재", params=("who",), gate="absence", budget=False,
        reversible="revive",
        desc="이후 등장 금지. 회상·편지·전언 씬은 예외다."),
    "depart": dict(
        layer="존재", params=("who", "to"), gate="absence_physical", budget=False,
        reversible="return_",
        desc="물리적 동석만 금지된다. 편지·전화는 가능하다 -- 원작의 요양원이 그 구조다."),
    "return_": dict(
        layer="존재", params=("who",), gate="lift_absence", budget=False,
        reversible="depart", desc="depart 를 해제한다."),
    "vanish": dict(
        layer="존재", params=("who",), gate="absence", budget=False, reversible="return_",
        desc="실종. 등장은 금지되지만 사망은 확정되지 않는다 -- die 와 구분해야 "
             "'살아 있을지도 모른다'는 서사가 성립한다."),
    "revive": dict(
        layer="존재", params=("who",), gate="lift_absence", budget=True,
        reversible=None,
        desc="죽은 인물이 돌아온다. **공리 개정을 동반해야 한다** -- 죽은 자가 돌아오는 "
             "세계인지가 먼저 정해져야 하기 때문이다. 예산을 쓴다."),

    # ---------------------------------------------------------- 2층 · 관계
    "meet": dict(
        layer="관계", params=("pair",), gate="not_before", budget=False, reversible=None,
        desc="첫 대면. 이전 씬에서 서로를 아는 것처럼 굴면 위반이다."),
    "start_romance": dict(
        layer="관계", params=("pair",), gate="relation_start", budget=False,
        reversible="end_romance",
        desc="배타 관계를 시작한다. 상대가 이미 있으면 end 없이 시작할 수 없다 -- "
             "'A 와 B 가 사귀는데 어느 순간 C 가 A 와 사귄다' 를 막는 자리다."),
    "end_romance": dict(
        layer="관계", params=("pair",), gate="relation_end", budget=False,
        reversible="start_romance", desc="배타 관계를 끝낸다. 그 장면이 씬에 남아야 한다."),
    "bind": dict(
        layer="관계", params=("pair", "kind"), gate="relation_start", budget=False,
        reversible="sever", desc="약혼·결혼. 연인보다 강한 배타."),
    "sever": dict(
        layer="관계", params=("pair",), gate="no_contact", budget=False,
        reversible="reconcile", desc="절연. 이후 같은 씬에 두면 위반이다."),
    "reconcile": dict(
        layer="관계", params=("pair",), gate="lift_no_contact", budget=False,
        reversible="sever", desc="sever 를 해제한다."),

    # ---------------------------------------------------------- 3층 · 지식
    "reveal": dict(
        layer="지식", params=("term", "to"), gate="knowledge_grant", budget=False,
        reversible="forget", desc="비밀이 알려진다. 그 인물의 knows 가 넓어진다."),
    "conceal": dict(
        layer="지식", params=("term", "from_whom"), gate="knowledge_deny", budget=False,
        reversible="reveal", desc="특정 인물에게 계속 숨긴다. 그가 말하면 위반이다."),
    "forget": dict(
        layer="지식", params=("who", "term"), gate="knowledge_revoke", budget=False,
        reversible="reveal",
        desc="기억상실. knows 를 **좁힌다.** 이 동사가 없으면 기억을 잃은 인물의 침묵이 "
             "설정 오류로 잡힌다."),
    "misbelieve": dict(
        layer="지식", params=("who", "term", "believes"), gate="belief", budget=False,
        reversible="reveal",
        desc="인물이 틀린 것을 참으로 믿는다. **이 동사가 이 표에서 가장 중요하다.** "
             "없으면 인물의 오해가 전부 환각으로 오판된다 -- 세계가 모순된 것과 인물이 "
             "틀린 것은 완전히 다른데, 텍스트만 보면 똑같이 생겼다."),

    # ---------------------------------------------------------- 4층 · 속성
    "fact_change": dict(
        layer="속성", params=("key", "old", "new"), gate="stale_fact", budget=False,
        reversible=None, desc="전공·직장·거주지가 바뀐다. 이후 옛 값을 현재형으로 쓰면 보고한다."),
    "rename": dict(
        layer="속성", params=("who", "old", "new"), gate="alias", budget=False,
        reversible=None,
        desc="같은 인물의 호칭이 바뀐다. 두 이름을 다른 인물로 세지 않게 별칭을 등록한다."),

    # ---------------------------------------------------------- 5층 · 시공간
    "timeskip": dict(
        layer="시공간", params=("amount",), gate="age_advance", budget=False,
        reversible=None, desc="나이·학년·계절을 일괄 갱신한다. 갱신 없이 넘기면 나이가 어긋난다."),
    "flashback": dict(
        layer="시공간", params=("to_when",), gate="suspend_absence", budget=False,
        reversible=None,
        desc="시간 역행. 죽거나 떠난 인물의 등장 금지를 **그 씬에 한해** 푼다."),
    "destroy_place": dict(
        layer="시공간", params=("place",), gate="place_gone", budget=False,
        reversible=None, desc="장소가 사라진다. 이후 그곳을 무대로 쓰면 위반이다."),

    # ---------------------------------------------------------- 6층 · 공리
    "assert_axiom": dict(
        layer="공리", params=("axiom", "value"), gate="axiom", budget=False,
        reversible=None,
        desc="세계의 규칙을 세운다(마법 유무, 시대, 화자 신뢰성, 시간의 선형성). "
             "초기 설정이라 예산을 쓰지 않는다."),
    "revise_axiom": dict(
        layer="공리", params=("axiom", "from_", "to", "justification"), gate="axiom_revision",
        budget=True, reversible=None,
        desc="규칙을 뒤집는다. 장르 전환이 여기다. **예산을 쓴다** -- 무제한이면 제약이 "
             "없는 것과 같고, 그러면 환각과 반전을 구분할 방법이 사라진다."),
    "retcon": dict(
        layer="공리", params=("invalidates", "justification"), gate="retro_invalidate",
        budget=True, reversible=None,
        desc="앞의 내용이 거짓이었다(꿈·거짓말·오인). 무효화할 씬을 **명시해야** 한다. "
             "무효화된 사실은 불변에서 빠지지만 '주장되었다는 기록' 은 남는다."),
    "reinterpret": dict(
        layer="공리", params=("rereads", "justification"), gate="retro_reinterpret",
        budget=True, reversible=None,
        desc="앞의 내용은 그대로고 **의미만** 바뀐다(반전). retcon 과 반드시 구분해야 한다 -- "
             "전자는 앞을 거짓으로 만들고 후자는 참으로 둔 채 뜻을 바꾼다. 기계는 뜻을 "
             "판정할 수 없으므로, 재독할 씬 목록이 실재하는지만 보고 나머지는 보고로 낸다."),
    "unreliable_narrator": dict(
        layer="공리", params=("scope", "justification"), gate="axiom_revision", budget=True,
        reversible=None,
        desc="서술 자체의 신뢰성을 내린다. 이후 V004(시점 위반) 같은 검사의 전제가 흔들리므로 "
             "관문이 어디까지 적용되는지 scope 로 좁혀야 한다."),
}

# 개정 예산. 6층 동사와 revive 가 이것을 소모한다.
DEFAULT_REVISION_BUDGET = 2

# 개정할 수 없는 핵. 여기 손대면 다른 소설이 된다.
FROZEN_AXIOMS = ("pov_character", "narrative_person", "retrospective")

BUDGETED = tuple(k for k, v in VERBS.items() if v["budget"])
BY_LAYER = {}
for _k, _v in VERBS.items():
    BY_LAYER.setdefault(_v["layer"], []).append(_k)


def spec(verb: str) -> dict:
    """모르는 동사는 예외다. 조용히 통과시키지 않는다."""
    if verb not in VERBS:
        raise KeyError(f"알 수 없는 세계 변경 동사: {verb!r}. "
                       f"허용된 동사: {sorted(VERBS)}")
    return VERBS[verb]


def validate_op(op: dict) -> list:
    """world_op 하나의 형식을 본다. 위반 사유 목록을 돌려준다(빈 목록이면 통과)."""
    verb = op.get("event")
    if verb not in VERBS:
        return [f"알 수 없는 세계 변경 동사: {verb!r}"]
    missing = [p for p in VERBS[verb]["params"] if p not in op]
    return [f"'{verb}' 에 필요한 인자 누락: {missing}"] if missing else []
