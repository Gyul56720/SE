"""세계관을 바꾸는 동사의 **닫힌 집합**.

언어 정책 (토큰 때문에 정한 것):
    키와 `en` 한 줄   -- 영어. **이것만 Director 프롬프트에 실린다.** 매 씬마다 나가므로
                        한국어로 두면 카탈로그 하나로 컨텍스트를 수백 토큰씩 먹는다.
    `note`            -- 한국어. 사람이 이 파일을 읽을 때만 쓴다. 프롬프트에 안 나간다.
    산문(최종 텍스트) -- 한국어. 그것만 독자가 본다.

왜 닫혀 있어야 하나. Director 가 임의의 사건 이름을 만들 수 있으면 모르는 사건은 아무
게이트도 낳지 않고 조용히 통과한다 -- 검증이 있는 척만 하게 된다. 여기 없는 동사는 hard
위반이다. 새 동사는 사람이 이 표에 추가한다.

**모델은 동사를 선언할 뿐 규칙을 쓰지 않는다.** 어떤 검사가 붙는지는 이 표에 고정돼 있다.
Director 에게 게이트를 쓰게 하면 자기에게 관대한 것을 쓴다 -- orchestrator 의 repair_node 가
verifier 를 절대 건드리지 않는 것과 같은 이유다.

어휘 범위는 무라카미(상실·실종·편지·다른 세계·기억)와 피츠제럴드(신분 위장·파티·몰락·
누명·재회)에서 반복되는 사건들을 덮도록 잡았다. 두 작가가 겹치는 자리가 많다 -- 둘 다
회고 1인칭이고, 둘 다 화자가 관찰자에 가깝고, 둘 다 상실이 이미 끝난 뒤에 서술된다.

일곱 층. 아래로 갈수록 비싸다. 1~6 층은 세계 **안**의 사건이라 예산이 없고, 7층은 세계
**자체**의 개정이라 예산이 붙는다.
"""
from __future__ import annotations


def V(layer, params, gate, en, budget=False, reversible=None, note=""):
    return dict(layer=layer, params=params, gate=gate, en=en,
                budget=budget, reversible=reversible, note=note)


VERBS = {
    # ---- 시간선 (마술적 리얼리즘) -------------------------------------------
    # 되감기는 **좌표를 만드는 사건**이다. 이 뒤의 씬은 새 시간선에 놓이고, 원장은
    # 시간선의 조상만 본다 -- 그래서 지워진 일과 남은 기억이 모순이 아니게 된다.
    #
    # carry 가 이 장치의 심장이다. 되감은 사람만 기억을 갖고 넘어오고, 그 비대칭이
    # 정보 격차(V016)를 통째로 만든다. cost/limit 는 씨앗이 요구하는 규율이다 --
    # 대가와 한계가 없는 되감기는 긴장을 죽인다.
    "rewind": V("시간", ("who", "carry", "cost", "back_to"), "timeline_branch",
                "rewind time back to scene `back_to`; scenes in between are "
                "erased; only people in `carry` keep their memories; "
                "the rewinder pays `cost`",
                budget=True,
                note="되감기. carry 에 적힌 인물만 기억을 갖고 넘어온다. "
                     "budget=True -- 횟수가 한정돼야 긴장이 산다"),

    # ============================================================ 1 · 존재
    "introduce": V("existence", ("who",), "not_before_existence",
                   "character enters the story; may not be known in earlier scenes"),
    "die": V("existence", ("who",), "absence",
             "character dies; cannot appear after, except in flashback/letter/reported",
             reversible="revive"),
    "suicide": V("existence", ("who",), "absence",
                 "character takes own life; recolors earlier scenes",
                 note="die 와 갈라둔 이유: 소급 재해석 효과가 있다. 앞 씬의 침묵과 사소한 "
                      "행동의 의미가 통째로 바뀐다 -- 원작에서 기즈키와 나오코가 그렇다. "
                      "reinterpret 를 동반하는 것이 보통이다."),
    "accident": V("existence", ("who", "witnesses"), "absence",
                  "sudden death or injury; witness set matters",
                  note="목격자 집합이 핵심이다. 누가 봤는지가 이후 지식·누명 구조를 만든다 "
                       "-- 개츠비의 자동차 사고가 그 구조 전체를 돌린다."),
    "depart": V("existence", ("who", "to"), "absence_physical",
                "character leaves; physically absent but letters/calls still possible",
                reversible="return_",
                note="물리적 동석만 금지된다. 원작의 요양원, 개츠비의 옥스퍼드가 이 구조다."),
    "return_": V("existence", ("who",), "lift_absence",
                 "character comes back; lifts departure", reversible="depart"),
    "vanish": V("existence", ("who",), "absence",
                "character disappears; absent but not confirmed dead",
                reversible="return_",
                note="die 와 구분해야 '살아 있을지도 모른다' 는 서사가 성립한다. "
                     "무라카미의 중심 동사다."),
    "revive": V("existence", ("who",), "lift_absence",
                "the dead returns; requires an axiom revision", budget=True,
                note="죽은 자가 돌아오는 세계인지가 먼저 정해져야 한다. 예산을 쓴다."),
    "birth": V("existence", ("who", "parents"), "not_before_existence",
               "a new character is born into the story"),

    # ============================================================ 2 · 관계
    "meet": V("relation", ("pair",), "not_before",
              "first encounter; they may not act acquainted before this"),
    "reunite": V("relation", ("pair", "after"), "reunion",
                 "meet again after a long gap; they already knew each other",
                 note="meet 과 다르다. 이전에 알던 사이이므로 '처음 본다' 는 서술이 오히려 "
                      "위반이다. 개츠비와 데이지, 그리고 재회 서사 전반."),
    "start_romance": V("relation", ("pair",), "relation_start",
                       "exclusive romance begins; partner must be free",
                       reversible="end_romance",
                       note="'A 와 B 가 사귀는데 어느 순간 C 가 A 와 사귄다' 를 막는 자리."),
    "end_romance": V("relation", ("pair",), "relation_end",
                     "romance ends; the breaking scene must exist",
                     reversible="start_romance"),
    "unrequited": V("relation", ("who", "toward"), "relation_start",
                    "one-sided love; directed, not exclusive"),
    "triangle": V("relation", ("center", "pair"), "triangle",
                  "two characters both oriented toward one; not an exclusivity breach"),
    "marry": V("relation", ("pair",), "relation_start",
               "marriage; stronger exclusivity than romance", reversible="divorce"),
    "divorce": V("relation", ("pair",), "relation_end",
                 "marriage ends", reversible="marry"),
    "betray": V("relation", ("who", "against"), "trust_break",
                "betrayal; relation may persist but trust inverts",
                note="관계를 끊지 않는다는 것이 요점이다. 겉으로 유지되면서 안이 무너진 "
                     "상태가 이 두 작가의 주요 지형이다."),
    "sever": V("relation", ("pair",), "no_contact",
               "estrangement; they may not share a scene", reversible="reconcile"),
    "reconcile": V("relation", ("pair",), "lift_no_contact",
                   "estrangement lifted", reversible="sever"),
    "mentor": V("relation", ("who", "to"), "relation_start",
                "one takes the other under their wing"),

    # ============================================================ 3 · 지식
    "reveal": V("knowledge", ("term", "to"), "knowledge_grant",
                "a secret becomes known to the listed characters", reversible="forget"),
    "overhear": V("knowledge", ("who", "term", "unknown_to"), "knowledge_grant_covert",
                  "character learns a secret without the owner knowing",
                  note="reveal 과 다르다. 정보를 얻은 사실 자체가 비밀이라, 그가 아는 것을 "
                       "'왜 아느냐' 로 추궁당하면 안 된다. 두 작가 모두 이걸로 플롯을 돌린다."),
    "conceal": V("knowledge", ("term", "from_whom"), "knowledge_deny",
                 "actively kept from someone; if they speak it, violation",
                 reversible="reveal"),
    "forget": V("knowledge", ("who", "term"), "knowledge_revoke",
                "amnesia; the knows-set narrows", reversible="reveal",
                note="이 동사가 없으면 기억을 잃은 인물의 침묵이 설정 오류로 잡힌다."),
    "misbelieve": V("knowledge", ("who", "term", "believes"), "belief",
                    "character holds a false belief as true", reversible="reveal",
                    note="**이 표에서 가장 중요한 동사다.** 없으면 인물의 오해가 전부 환각으로 "
                         "오판된다. 세계가 모순된 것과 인물이 틀린 것은 완전히 다른데, "
                         "텍스트만 보면 똑같이 생겼다."),
    "fabricate": V("knowledge", ("who", "story", "believed_by"), "public_fiction",
                   "character invents a past; the world knows otherwise", budget=False,
                   note="misbelieve 의 집단 버전. 개츠비의 옥스퍼드가 이것이다. 세계의 진실과 "
                        "공개된 이야기가 갈라진 채 유지되고, 그 간극이 서사의 엔진이 된다."),
    "expose": V("knowledge", ("target", "story"), "public_fiction_break",
                "a fabrication collapses in public"),
    "secret_pact": V("knowledge", ("members", "term"), "knowledge_grant",
                     "two or more agree to keep something between them"),
    "blame_transfer": V("knowledge", ("truth_who", "blamed_who", "term"), "belief",
                        "the world believes the wrong person is responsible",
                        note="누명. 세계의 사실과 세계의 믿음이 갈라진다 -- 개츠비가 데이지의 "
                             "운전을 뒤집어쓰는 구조."),

    # ============================================================ 4 · 속성/신분
    "fact_change": V("attribute", ("key", "old", "new"), "stale_fact",
                     "a fact about the world changes; old value is stale after"),
    "rename": V("attribute", ("who", "old", "new"), "alias",
                "same character, new name or form of address",
                note="두 이름을 다른 인물로 세지 않도록 별칭을 등록한다."),
    "status_change": V("attribute", ("who", "axis", "old", "new"), "stale_fact",
                       "wealth, class, or position shifts"),
    "ruin": V("attribute", ("who",), "stale_fact",
              "financial or social collapse", reversible="status_change"),
    "assume_identity": V("attribute", ("who", "as_whom"), "public_fiction",
                         "character passes as someone else"),

    # ============================================================ 5 · 시공간
    "timeskip": V("spacetime", ("amount",), "age_advance",
                  "time passes; ages, years, seasons must update"),
    "flashback": V("spacetime", ("to_when",), "suspend_absence",
                   "scene moves backward; absence rules suspended for this scene only"),
    "season_turn": V("spacetime", ("to_season",), "punctum_refresh",
                     "season changes; sensory register should follow"),
    "place_shift": V("spacetime", ("to_place",), "stage_move",
                     "the story's stage moves"),
    "gathering": V("spacetime", ("who", "occasion"), "convergence",
                   "many characters converge in one scene",
                   note="파티. 피츠제럴드의 기본 무대이고, 다수 인물이 한 씬에 모이므로 "
                        "지식·관계 검사가 한꺼번에 걸린다 -- 모순이 가장 잘 드러나는 자리다."),
    "destroy_place": V("spacetime", ("place",), "place_gone",
                       "a location ceases to exist; cannot be a stage after"),

    # ============================================================ 6 · 사물·감각
    "acquire_object": V("object", ("who", "thing"), "object_track",
                        "an object enters the story and can be referenced after"),
    "lose_object": V("object", ("who", "thing"), "object_gone",
                     "the object is lost; cannot be used after",
                     note="무라카미의 사물은 감정의 객관적 상관물이라 유실이 서사적 사건이다."),
    "give_object": V("object", ("from_whom", "to", "thing"), "object_track",
                     "possession moves between characters"),
    "motif": V("object", ("name", "sense"), "motif_track",
               "a recurring sensory motif is established (a song, a smell, a sound)",
               note="푼크툼의 재료. 한 번 심으면 이후 씬에서 되돌아올 때 의미가 생긴다."),

    # ============================================================ 7 · 공리
    "assert_axiom": V("axiom", ("axiom", "value"), "axiom",
                      "establish a rule of the world (magic, era, narrator reliability)"),
    "revise_axiom": V("axiom", ("axiom", "from_", "to", "justification"), "axiom_revision",
                      "overturn a rule of the world; costs budget", budget=True,
                      note="무제한이면 제약이 없는 것과 같고, 그러면 환각과 반전을 구분할 "
                           "방법이 사라진다."),
    "retcon": V("axiom", ("invalidates", "justification"), "retro_invalidate",
                "earlier content was false (a dream, a lie); must name the scenes",
                budget=True),
    "reinterpret": V("axiom", ("rereads", "justification"), "retro_reinterpret",
                     "earlier content stands but its meaning changes", budget=True,
                     note="retcon 과 반드시 구분해야 한다. 전자는 앞을 거짓으로 만들고 후자는 "
                          "참으로 둔 채 뜻만 바꾼다. 기계는 뜻을 판정할 수 없으므로 재독 대상 "
                          "씬이 실재하는지만 보고 나머지는 보고로 낸다."),
    "dream_frame": V("axiom", ("scenes", "justification"), "retro_invalidate",
                     "a span of scenes turns out to have been a dream", budget=True),
    "world_cross": V("axiom", ("who", "to_world", "justification"), "axiom_revision",
                     "character moves into another layer of reality", budget=True,
                     note="무라카미의 우물·1Q84. 공리 개정이므로 예산을 쓴다."),
    "unreliable_narrator": V("axiom", ("scope", "justification"), "axiom_revision",
                             "narration itself becomes untrustworthy within scope",
                             budget=True,
                             note="이후 V004 같은 검사의 전제가 흔들리므로 scope 로 좁혀야 한다."),
}

DEFAULT_REVISION_BUDGET = 2
FROZEN_AXIOMS = ("pov_character", "narrative_person", "retrospective")

BUDGETED = tuple(k for k, v in VERBS.items() if v["budget"])
BY_LAYER = {}
for _k, _v in VERBS.items():
    BY_LAYER.setdefault(_v["layer"], []).append(_k)


def spec(verb: str) -> dict:
    if verb not in VERBS:
        raise KeyError(f"unknown world verb: {verb!r}")
    return VERBS[verb]


def validate_op(op: dict) -> list:
    """world_op 하나의 형식 검사. 위반 사유 목록(빈 목록이면 통과).

    **객체가 아닌 것이 들어와도 죽지 않는다.** LLM 이 world_ops 를 문자열 목록으로 낼
    때가 있는데(["설윤이 자리를 잃었다"]), 예전에는 여기서 op.get 이
    'str' object has no attribute 'get' 로 터졌다. 검증기가 잘못된 입력에 죽으면 그건
    검증이 아니라 사고다 -- 2026-09-03 밤샘 런이 novel.save() 안에서 이렇게 죽어
    결말 블록을 잃었다. 위반으로 **보고**하고 넘어간다."""
    if not isinstance(op, dict):
        return [f"world_op 이 객체가 아니다: {type(op).__name__} {str(op)[:60]!r}"]
    verb = op.get("event")
    if verb not in VERBS:
        return [f"unknown world verb: {verb!r}"]
    missing = [p for p in VERBS[verb]["params"] if p not in op]
    return [f"'{verb}' missing params: {missing}"] if missing else []


def catalog_for_prompt(layers=None) -> str:
    """Director 프롬프트에 실을 압축 카탈로그. **영어 한 줄씩.**

    한국어 note 는 나가지 않는다 -- 매 씬 호출마다 실리므로 여기서 아낀 토큰이 그대로
    컨텍스트 여유가 된다."""
    out = []
    for layer, keys in BY_LAYER.items():
        if layers and layer not in layers:
            continue
        out.append(f"# {layer}")
        for k in keys:
            v = VERBS[k]
            args = ",".join(v["params"])
            tag = " [BUDGET]" if v["budget"] else ""
            out.append(f"  {k}({args}) - {v['en']}{tag}")
    return "\n".join(out)
