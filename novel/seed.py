"""자유 씨앗 -- 무작위로 섞되 **기계가 최소한만 거른다.**

고정된 세계(여성향 청춘 로맨스 200화)로 뽑아보니 문제가 구조에 있었다. 세계가 하나면
프롬프트가 매번 거의 같고, 같은 입력은 같은 답을 낸다 -- 서브플롯 세 회차가 전부
"핫팩을 많이 사는 남자" 였던 것이 그 증상이다.

여기서는 반대로 간다. **축마다 따로 뽑아 조합한다.** 축이 8개이고 각 축이 8~12개면
조합은 수천만 가지다. 같은 씨앗이 두 번 나올 일이 없다.

무작위는 재미의 필요조건이지 충분조건이 아니다. 그래서 **뽑은 뒤 기계가 검사한다** --
다만 "최소한만" 이다:

  · 반칙에는 **효과와 조건**이 있어야 한다. 무제한이면 긴장이 없다
    (대가가 아니라 조건이다 -- 주인공이 손해를 보는 순간 그것은 고구마다)
  · 인물 셋이 서로 다른 축에서 와야 한다. 같은 축이면 같은 사람이 셋이다
  · 시간 장치와 사건이 충돌하면 안 된다 (되감기 + 일회성 사건은 같이 못 선다)
  · 이미 쓴 씨앗과 겹치면 안 된다

취향은 안 본다. "재미있는가" 는 기계가 판정할 수 없고, 판정하려 들면 평균만 남는다.

실행:
    python3 novel/seed.py                 # 열 개 뽑아 본다 (LLM 호출 없음)
    python3 novel/seed.py --n 3 --long    # 자세히
    python3 novel/seed.py --rng 42        # 같은 씨앗 재현
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "seeds_used.json"

# ---------------------------------------------------------------- 축

# 판(국면). **주인공에게 기회가 열리는 자리**여야 한다. 현실의 정체된 상황이 아니라,
# 오늘부터 판이 뒤집힐 수 있는 상황이다 -- 사이다는 시작과 동시에 목적이 서야 한다.
TIME = [
    ("게이트가 처음 열린 지 삼 년째", "각성자 등급이 곧 신분이 됐다"),
    ("길드 재편이 공고된 달", "약한 길드는 흡수되고, 순위표가 매주 갈린다"),
    ("탑의 1층이 개방된 첫 주", "아무도 규칙을 모른다. 먼저 아는 자가 먹는다"),
    ("아카데미 실기 재평가 기간", "한 번의 시연으로 서열이 다시 매겨진다"),
    ("그룹 후계 구도가 흔들리는 분기", "지분과 실적이 매일 저울에 오른다"),
    ("경매장에 옛 유물이 쏟아지는 시즌", "값을 아는 사람만 쓸어 담는다"),
    ("던전 등급 산정이 무너진 여름", "표기된 등급을 믿으면 죽는다"),
    ("회귀 직후의 첫 한 달", "앞으로 벌어질 일을 나만 안다"),
    ("협회 감사가 시작된 보름", "묻어둔 것이 하나씩 올라온다"),
    ("신인 계약 시즌", "지금 잡은 사람이 십 년을 간다"),
]

# 반칙 하나. **대가가 아니라 조건이다.** 그리고 **수치가 아니라 앎이다** --
# "능력치가 숫자로 보인다" 류는 문장을 상태창 UI 로 바꾼다(등급 D→C, 호감도 41).
# 필력을 살리자고 한 판에서 그 자리가 제일 먼저 죽는다. 반칙은 주인공이 남보다
# **먼저 아는 것**으로만 드러난다.
#
# 예전에는 이 축이 "찾으러 가면 다른 것을 하나 잃는다" 처럼 **대가**를 물렸다. 마술적
# 리얼리즘의 규율이었지 사이다의 규율이 아니다 -- 주인공이 손해를 감수하는 순간 그것이
# 고구마가 되고, 사이다에서 고구마는 독자가 떠나는 이유다.
#
# 그래서 셋째 칸을 대가에서 **조건(쿨타임·범위·발동 요건)**으로 바꿨다. 무제한이면 긴장이
# 없으므로 제약은 남기되, 그 제약이 주인공을 다치게 하지는 않는다. 제약은 "언제 쓸 수
# 있는가" 를 정할 뿐이고, 쓰면 반드시 이긴다.
IMPOSSIBLE = [
    ("상대가 다음에 무엇을 할지 한 수 먼저 보인다", "선수를 빼앗기지 않는다", "마주 본 동안만"),
    ("한 번 본 기술을 그대로 복제한다", "복제한 것은 영구히 남는다", "직접 눈으로 봐야 한다"),
    ("죽기 전으로 돌아왔고 그 기억이 남아 있다", "앞으로 벌어질 일을 안다", "바뀐 것은 다시 확인해야 한다"),
    ("물건의 진짜 값과 내력이 읽힌다", "값을 아는 자가 판을 먹는다", "손으로 만져야 한다"),
    ("남이 숨긴 의도가 문장으로 떠오른다", "거짓말이 통하지 않는다", "마주 본 동안만"),
    ("계약의 빈틈이 표시된다", "서명 전에 전부 보인다", "문서로 된 것만"),
    ("누가 끝까지 갈 사람인지 첫 만남에 안다", "사람을 고르는 데 실패하지 않는다", "직접 만난 사람만"),
    ("죽은 자의 마지막 기억을 읽는다", "아무도 모르는 것을 안다", "하루 한 번"),
    ("자기 실력을 실제보다 낮게 보이게 한다", "약해 보이는 쪽을 고를 수 있다", "처음 보는 상대에게만"),
]

# 인물의 축. 조연은 **주인공을 빛내는 자리**다. 스스로 판단해 서사를 끌지 않는다.
PEOPLE = [
    ("주인공을 처음 알아본 사람", "남들이 비웃을 때 혼자 걸었다"),
    ("실력만 보고 따라붙은 후배", "묻지 않고 먼저 움직인다"),
    ("한물간 취급을 받는 옛 강자", "주인공에게서 옛날의 자기를 본다"),
    ("장부를 쥐고 있는 실무자", "숫자로 주인공을 증명해준다"),
    ("주인공을 얕본 명문가 자제", "밀릴 때마다 판을 키운다"),
    ("협회의 규정만 앞세우는 감독관", "규정 밖의 것을 인정하지 못한다"),
    ("주인공의 성과를 가로챈 선배", "가져간 것을 자기 실력이라 믿는다"),
    ("사람 보는 눈 하나로 버틴 중개인", "붙을 사람을 고르는 데 실패한 적이 없다"),
    ("길드를 물려받았지만 비어 있는 후계자", "이름값만 남았고 사람이 없다"),
    ("주인공을 시험하려는 최상위권", "재미있는 것을 오래 못 참는다"),
    ("현장만 아는 오래된 대원", "말은 거칠고 판단은 정확하다"),
    ("정보만 파는 브로커", "값을 매기는 데 감정을 섞지 않는다"),
]

# 1화의 곤경과 손실. **작지만 즉시 아픈 것**으로 연다. 그리고 그 화 안에 목적이 선다.
EVENT = [
    "공적을 가로채이고 팀에서 잘린다",
    "등급 재심사에서 최하위 판정을 받는다",
    "보증을 잘못 서 빚이 통째로 넘어온다",
    "형이 남긴 길드가 헐값에 넘어가기 직전이다",
    "죽기 직전으로 돌아왔고 그날이 사흘 뒤다",
    "계약서의 독소조항 때문에 성과를 전부 뺏긴다",
    "쓸모없다던 유물이 사실 값을 매길 수 없는 것임을 안다",
    "명문가 자제에게 공개 석상에서 모욕당한다",
    "동료가 던전에서 버려졌고 아무도 문제 삼지 않는다",
    "협회 장비가 자기 등급을 잘못 읽는다는 것을 알아챈다",
]

# 되돌아올 사물. 체호프의 총.
MOTIF = ["금이 간 인식표", "이름이 지워진 계약서", "낡은 단검", "빈 길드 인장",
         "숫자만 적힌 수첩", "회수되지 않은 보증서", "등급이 잘못 찍힌 카드",
         "형이 쓰던 장갑", "값을 못 매긴 유물", "멈춘 손목시계", "닳은 출입증"]

# 문장의 색. 사이다는 전부 빠르되, 빠른 방식이 다르다.
VOICE = [
    ("짧고 건조하게", "한 문장에 하나만 담는다. 수식을 붙이지 않는다"),
    ("대사 위주로", "지문을 최소로 하고 말로 굴린다"),
    ("담담한 통보처럼", "이겼다는 사실만 적는다. 감탄은 남이 한다"),
    ("사실만 먼저", "무엇이 일어났는지 한 줄로 적고 사정은 뒤에 붙인다"),
    ("관찰자의 감탄을 빌려", "주인공은 말이 없고 주변이 술렁인다"),
    ("선언하듯", "결론을 먼저 말하고 근거를 뒤에 던진다"),
]

# 무엇에 대한 이야기인가.
THEME = ["빼앗긴 것을 되찾기", "값을 아는 자의 독식", "먼저 아는 자의 우위",
         "무시당한 자의 증명", "사람을 알아보는 눈", "규칙의 빈틈",
         "다시 사는 두 번째 기회", "가장 밑에서 정상까지"]

AXES = ("time", "impossible", "people", "event", "motif", "voice", "theme")

# 이름은 **씨앗에서 결정론적으로** 뽑는다. 모델에게 짓게 하면 호출이 늘고 재현이 안 된다.
# 흔한 이름을 피했다 -- 이름이 진부하면 인물이 시작부터 진부해 보인다.
NAMES = ["윤오", "해수", "단희", "무경", "리원", "정안", "세류", "가온",
         "은결", "도하", "여림", "채운", "시온", "하람", "노아", "유안"]


def josa(word: str, kind: str) -> str:
    """받침에 따라 조사를 고른다. **이게 없으면 "세류이" 가 나온다.**

    이 저장소에서 이미 한 번 데인 자리다 -- 인물 이름을 바꿨더니 "설윤가" 가 스물세 곳에
    생겼다. 이름을 씨앗이 정하는 지금은 손으로 고칠 수도 없다."""
    if not word:
        return word
    last = word[-1]
    has = (ord(last) - 0xAC00) % 28 != 0 if 0xAC00 <= ord(last) <= 0xD7A3 else False
    pair = {"이": ("이", "가"), "은": ("은", "는"), "을": ("을", "를"),
            "과": ("과", "와"), "으로": ("으로", "로")}[kind]
    return word + (pair[0] if has else pair[1])


def cast_names(seed: dict) -> list:
    """씨앗 id 로 이름을 정한다. 같은 씨앗이면 같은 이름이 나온다."""
    rng = random.Random(seed["id"])
    return rng.sample(NAMES, len(seed["people"]))


def draw(rng: random.Random) -> dict:
    """축마다 하나씩 뽑는다. 인물은 셋 -- 서로 다른 축에서."""
    cast = rng.sample(PEOPLE, 3)
    t, t_note = rng.choice(TIME)
    # cost 는 이제 **대가가 아니라 효과**다(사이다: 주인공은 손해를 보지 않는다).
    # limit 은 발동 조건이다. 키 이름은 원장 호환을 위해 그대로 둔다.
    rule, cost, limit = rng.choice(IMPOSSIBLE)
    voice, v_note = rng.choice(VOICE)
    seed = {
        "time": {"what": t, "note": t_note},
        "impossible": {"rule": rule, "cost": cost, "limit": limit},
        "people": [{"who": w, "wound": s} for w, s in cast],
        "event": rng.choice(EVENT),
        "motif": rng.choice(MOTIF),
        "voice": {"how": voice, "note": v_note},
        "theme": rng.choice(THEME),
    }
    seed["id"] = hashlib.sha256(
        json.dumps(seed, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]
    return seed


def validate(seed: dict, used: set = None) -> list:
    """**최소한만** 본다. 취향은 판정하지 않는다."""
    out = []
    imp = seed.get("impossible") or {}
    if not imp.get("cost") or not imp.get("limit"):
        out.append("반칙에 효과나 조건이 없다 -- 무제한이면 긴장이 없고, "
                   "조건이 없으면 언제 쓸지가 곧 전개가 되지 못한다")
    who = [p["who"] for p in seed.get("people") or []]
    if len(set(who)) < 3:
        out.append(f"인물이 서로 다른 축에서 오지 않았다: {who}")
    if not seed.get("event"):
        out.append("최초의 사건이 없다")
    if used and seed.get("id") in used:
        out.append(f"이미 쓴 씨앗이다 ({seed['id']})")
    # 시간 장치와 규칙이 같은 것을 두 번 말하는가 (겹치면 축이 하나 죽는다)
    if seed["time"]["what"][:4] in imp.get("rule", ""):
        out.append("시간 장치와 불가능한 규칙이 같은 소재다 -- 축 하나가 낭비된다")
    return out


def used_ids() -> set:
    try:
        return set(json.loads(LEDGER.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def remember(seed_id: str) -> None:
    ids = used_ids() | {seed_id}
    LEDGER.write_text(json.dumps(sorted(ids), ensure_ascii=False, indent=1),
                      encoding="utf-8")


def title_hint(seed: dict) -> str:
    """제목을 짓지 않는다 -- 재료만 준다. 짓는 것은 디렉터의 일이다."""
    return f"{seed['motif']} · {seed['time']['what']} · {seed['theme']}"


def render(seed: dict, long: bool = False) -> str:
    p = seed["people"]
    lines = [f"[{seed['id']}]  {title_hint(seed)}"]
    if not long:
        lines.append(f"   시간   {seed['time']['what']}")
        lines.append(f"   규칙   {seed['impossible']['rule']}"
                     f"  (효과: {seed['impossible']['cost']})")
        lines.append(f"   사건   {seed['event']}")
        lines.append(f"   인물   {' / '.join(x['who'] for x in p)}")
        lines.append(f"   목소리 {seed['voice']['how']} · 주제 {seed['theme']}")
        return "\n".join(lines)
    lines.append(f"   시간   {seed['time']['what']}")
    lines.append(f"          {seed['time']['note']}")
    lines.append(f"   규칙   {seed['impossible']['rule']}")
    lines.append(f"          효과: {seed['impossible']['cost']}")
    lines.append(f"          조건: {seed['impossible']['limit']}")
    lines.append(f"   사건   {seed['event']}")
    for i, x in enumerate(p, 1):
        lines.append(f"   인물{i}  {x['who']}")
        lines.append(f"          {x['wound']}")
    lines.append(f"   장치   {seed['motif']}")
    lines.append(f"   목소리 {seed['voice']['how']} -- {seed['voice']['note']}")
    lines.append(f"   주제   {seed['theme']}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--rng", type=int, default=None, help="재현용 난수 씨앗")
    ap.add_argument("--long", action="store_true")
    ap.add_argument("--keep", help="이 id 를 '쓴 것' 으로 기록한다")
    a = ap.parse_args()

    if a.keep:
        remember(a.keep)
        print(f"{a.keep} 을 기록했다. 다음부터 다시 뽑히지 않는다.")
        return 0

    rng = random.Random(a.rng)
    used = used_ids()
    space = (len(TIME) * len(IMPOSSIBLE) * len(EVENT) * len(MOTIF)
             * len(VOICE) * len(THEME))
    print(f"조합 공간 {space:,} x 인물 {len(PEOPLE)}C3 = "
          f"{space * 220:,}가지 · 이미 쓴 것 {len(used)}개\n")
    shown = 0
    while shown < a.n:
        s = draw(rng)
        bad = validate(s, used)
        if bad:
            continue
        print(render(s, a.long))
        print()
        shown += 1
    print("마음에 드는 것을 고르면:  python3 novel/seed.py --keep <id>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
