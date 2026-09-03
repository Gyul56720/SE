"""거시 서사 -- 3막 8시퀀스를 **검증 가능한 상태**로.

씬 단위 관문(gate.py)은 한 씬 안의 모순을 잡는다. 200화짜리에서 실제로 무너지는 것은
그게 아니라 **진도**다. 용두사미는 씬 하나가 틀려서 생기지 않는다. 100화가 됐는데 아직
감정선이 혐오 단계에 있거나, 사건 규모가 커지지 않거나, 독자와 인물의 정보 격차가 사라져
서스펜스가 없어져서 생긴다. 전부 씬 하나만 보면 안 보이고 **누적을 봐야 보인다.**

관계 원장이 "A 와 B 가 사귀는데 C 와 사귄다"를 잡은 것과 같은 수를 쓴다: 무너지는 것을
상태로 만들고 불변식으로 검사한다.

웹소설 규격(보고서 기준):
    1회차 = 공백 포함 5,000자 / 100만 자 = 200화 / 단행본 10~14권
    중대형 사건 15~20개, 하나당 10~15화
"""
from __future__ import annotations

CHARS_PER_EPISODE = 5000
TOTAL_EPISODES = 200

# 감정선 4단계. 보고서: 혐오 -> 작은 호의와 흔들림 -> 위기 속 공모와 후회 -> 결정적 선택.
STAGES = ("혐오·대립", "호의·흔들림", "공모·후회", "결정적 선택", "해소")

# narrative_pull = 관계로부터의 거리. -100 밀어냄 .. +100 끌림.
# **단조 증가가 아니다.** 시퀀스 4(입덕 부정)와 6(관계 단절 위기)에서 반드시 꺾인다.
# 그 꺾임이 없으면 "너무 순탄하다" -- 이 장르에서 가장 흔한 실패다. 그래서 밴드로 검사한다.
SEQUENCES = [
    dict(n=1, name="일상 균열과 첫 만남", eps=(1, 20), stage="혐오·대립",
         pull=(-60, -10), events=(1, 2), scale=(1, 2), cliff=True,
         goal="평온한 일상에 균열. 강렬한 첫 만남과 오해로 관계 프레임 고정. "
              "강제적 결속(계약·위장·조별 공모)"),
    dict(n=2, name="갈등의 태동", eps=(21, 40), stage="혐오·대립",
         pull=(-50, 5), events=(1, 2), scale=(1, 2), cliff=True,
         goal="새 환경에 적응하며 얽힘. 미세한 호의와 흔들림의 시작"),
    dict(n=3, name="관계 진전과 공조", eps=(41, 70), stage="호의·흔들림",
         pull=(-10, 45), events=(2, 3), scale=(2, 3), cliff=True,
         goal="밀폐 공간 또는 공동 목표. 마찰과 텐션. 서로의 약점을 보완"),
    dict(n=4, name="중간점 — 자각과 입덕 부정", eps=(71, 100), stage="호의·흔들림",
         pull=(-30, 60), events=(2, 3), scale=(2, 4), cliff=True, dip=True,
         goal="감정적 자각. 그러나 트라우마로 회피. 첫 결정적 스킨십과 도피"),
    dict(n=5, name="질투와 견제", eps=(101, 130), stage="공모·후회",
         pull=(0, 70), events=(2, 3), scale=(3, 4), cliff=True,
         goal="서브 캐릭터 개입. 극단적 질투와 오해. '잃을지도 모른다'는 두려움"),
    dict(n=6, name="모든 것을 잃을 위기", eps=(131, 160), stage="공모·후회",
         pull=(-40, 60), events=(2, 3), scale=(4, 5), cliff=True, dip=True,
         goal="숨긴 진실의 폭로. 관계 단절 위기. 주인공이 내면적 한계에 부딪힘"),
    dict(n=7, name="클라이맥스", eps=(161, 185), stage="결정적 선택",
         pull=(40, 100), events=(2, 3), scale=(5, 5), cliff=True,
         goal="모든 리스크를 감수하고 진심을 증명. 감정 폭발과 오해 해소. 쌍방 구원"),
    dict(n=8, name="에필로그", eps=(186, 200), stage="해소",
         pull=(60, 100), events=(1, 2), scale=(1, 3), cliff=False,
         goal="달달한 일상 회복. 서브플롯 회수. 미래의 약속과 해피엔딩"),
]

# 클리프행어 5대 공식. Director 가 구조로 선언한다 -- 텍스트에서 추론하면 그 추론이 또
# 하나의 환각이 된다.
CLIFFHANGERS = {
    "before_crisis": "위기 직전에 끊기 — 충돌 1초 전, 눈이 마주치는 찰나",
    "shock_line": "충격 발언 후 끊기 — 반전 대사 직후 상대의 반응을 숨긴다",
    "unexpected_entry": "예상치 못한 등장 — 들켜서는 안 되는 자리에 문이 열린다",
    "warning_sign": "위험 신호 직전 — 덫·경고장·협박의 징후가 방금 발견됐다",
    "caught": "들키면 안 되는 순간에 들키기 — 목격당하는 아슬아슬한 시점",
}

# 사건 규모. 작은 일상에서 시작해 점진적으로 커져야 한다. 처음부터 크면 50화 전에 동력을
# 잃는다(보고서). 단조 증가를 강제하지는 않되 **뒷걸음질**을 잡는다.
SCALES = {1: "일상(성적·동아리·조별과제)", 2: "관계(오해·질투·소문)",
          3: "진로(입시·취업·이사)", 4: "가족·과거(비밀·악연)",
          5: "사회·운명(가치관 충돌·결별의 압력)"}


def sequence_of(episode: int) -> dict:
    for s in SEQUENCES:
        if s["eps"][0] <= episode <= s["eps"][1]:
            return s
    raise ValueError(f"회차 범위 밖: {episode} (1..{TOTAL_EPISODES})")


def episodes_in(seq_n: int) -> int:
    lo, hi = SEQUENCES[seq_n - 1]["eps"]
    return hi - lo + 1


def plan_summary() -> str:
    """Director 프롬프트에 실을 압축 요약. 영어가 아니라 한국어인 이유: 이 표는 장르
    규약이라 그대로 산문 지시로 쓰인다. 동사 카탈로그와 달리 매 씬 전체가 실리지 않고
    현재 시퀀스 한 줄만 실린다."""
    out = []
    for s in SEQUENCES:
        out.append(f"시퀀스 {s['n']} ({s['eps'][0]}~{s['eps'][1]}화) {s['name']} "
                   f"| 감정 {s['stage']} | pull {s['pull']} | 사건 {s['events'][0]}~"
                   f"{s['events'][1]}개 규모 {s['scale']}")
    return "\n".join(out)


def brief(episode: int) -> str:
    """현재 회차 한 줄. 이것만 프롬프트에 실린다."""
    s = sequence_of(episode)
    tail = " · 이 시퀀스에는 감정선의 꺾임(회피/단절)이 반드시 있어야 한다" if s.get("dip") else ""
    return (f"[{episode}/{TOTAL_EPISODES}화 · 시퀀스 {s['n']} {s['name']}]\n"
            f"  목표: {s['goal']}\n"
            f"  감정 단계: {s['stage']} / narrative_pull 범위 {s['pull']}\n"
            f"  사건 규모: {SCALES[s['scale'][0]]} ~ {SCALES[s['scale'][1]]}{tail}")
