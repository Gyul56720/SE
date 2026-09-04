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

# 판(국면). 탑이 선 뒤의 세계다. **디스토피아지만 사람들은 거기 적응해 산다** --
# 아무도 절망하지 않는 디스토피아가 더 무섭고, 겉으로도 가볍다.
TIME = [
    ("탑이 선 지 십 년째", "층수가 곧 계급이 됐고, 아무도 그걸 이상하게 여기지 않는다"),
    ("협회가 '희생 지수'를 공표하기 시작한 달", "누구를 버려도 되는지 숫자로 정해준다"),
    ("영웅 은퇴식이 매달 열리는 해", "은퇴한 영웅이 어디로 가는지는 아무도 묻지 않는다"),
    ("탑 12층이 삼 년째 안 열리는 겨울", "위층 사람들은 아래로 내려오지 않는다"),
    ("구조 우선순위가 공개된 주", "명단에 없는 구역은 조용히 지워진다"),
    ("영웅 면허 갱신 시즌", "면허 없이 사람을 구하면 처벌된다"),
    ("각성 실패자 재배치가 시작된 달", "실패자는 탑 아래 공사장으로 간다"),
    ("전 영웅의 재판이 생중계되는 보름", "무엇을 지키려 했는지는 심리하지 않는다"),
    ("배급이 층별로 갈린 첫 겨울", "1층은 줄을 서고 20층은 배달을 받는다"),
    ("탑이 하루 동안 완전히 조용했던 다음 날", "그 하루에 무슨 일이 있었는지 기록이 없다"),
]

# 반칙 하나. **대가가 아니라 조건이다.** 그리고 **수치가 아니라 앎이다** --
# "능력치가 숫자로 보인다" 류는 문장을 상태창 UI 로 바꾼다(등급 D→C, 호감도 41).
# 필력을 살리자고 한 판에서 그 자리가 제일 먼저 죽는다.
#
# 그리고 반칙은 **철학적 시험대**이기도 하다. 남을 살릴 수 있는 힘, 남의 고통을 아는 힘,
# 규칙의 예외가 되는 힘 -- 이 힘들은 전부 "그래서 너는 무엇을 해야 하는가" 를 묻는다.
# 그 물음이 이 소설의 심층이고, 겉으로는 그냥 편리한 능력으로 보인다.
IMPOSSIBLE = [
    ("죽을 사람이 누구인지 하루 전에 안다", "먼저 가서 막을 수 있다", "하루에 한 사람만"),
    ("남의 고통을 대신 짊어질 수 있다", "그 사람은 그만큼 멀쩡해진다", "만지고 있는 동안만"),
    ("규칙이 자기에게만 적용되지 않는다", "면허도 층수도 통제도 비껴간다", "혼자 있을 때만"),
    ("한 번 죽은 자리로 시간이 되감긴다", "같은 죽음을 두 번 겪지 않는다", "그 자리에서만"),
    ("남이 무엇을 걸고 싸우는지 보인다", "속셈이 아니라 각오가 읽힌다", "마주 본 동안만"),
    ("자기가 한 약속은 반드시 지켜진다", "말한 대로 세계가 맞춰진다", "한 번에 하나만"),
    ("탑의 다음 층이 무엇을 요구할지 미리 안다", "준비하고 들어갈 수 있다", "한 층 앞까지"),
    ("죽은 자의 마지막 순간을 본다", "아무도 모르는 것을 안다", "시신을 만졌을 때"),
    ("누가 끝까지 갈 사람인지 첫 만남에 안다", "사람을 고르는 데 실패하지 않는다", "직접 만난 사람만"),
]

# 인물의 축. **직업이 아니라 상처와 태도**로 잡는다. 조연은 주인공을 빛내되,
# 각자 자기 신념을 하나씩 들고 있어야 한다 -- 그래야 주인공의 선택이 시험받는다.
PEOPLE = [
    ("규정대로만 사람을 구하는 영웅", "명단에 없는 사람을 지나친 밤을 세지 않는다"),
    ("면허 없이 사람을 구하고 다니는 자", "잡히면 끝인 걸 알면서 멈추지 않는다"),
    ("한 사람을 살리려 열을 버린 적 있는 자", "그 계산이 맞았는지 아직 모른다"),
    ("영웅을 그만두고 장부만 적는 사람", "누가 죽었는지 전부 적어 두었다"),
    ("희생자 명단을 관리하는 실무자", "이름을 지우는 것이 자기 일이라고 믿는다"),
    ("탑 아래에서 태어나 위를 본 적 없는 사람", "올라가는 것이 옳은지 의심한다"),
    ("자기가 구한 사람에게 원망을 들은 자", "그 뒤로 아무도 구하지 않는다"),
    ("영웅의 유족", "고맙다는 말과 원망을 같은 입으로 한다"),
    ("모두를 위해 한 명을 버리자고 말하는 사람", "그 말을 하고 잠을 못 잔다"),
    ("사람들을 위해 악당을 자처한 자", "설명하지 않는 쪽을 택했다"),
    ("신을 믿다가 그만둔 성직자", "아직 매일 같은 시간에 눈을 감는다"),
    ("영웅 지망생", "아무것도 모르고 전부 묻는다"),
]

# 1화의 곤경과 손실. **작지만 즉시 아픈 것**으로 연다. 그리고 그 화 안에 목적이 선다.
EVENT = [
    "구조 명단에서 자기 구역이 지워진 것을 알게 된다",
    "면허를 정지당한 날, 눈앞에서 사람이 무너진다",
    "형이 영웅으로 죽었는데 공식 기록에는 이름이 없다",
    "자기가 구한 사람이 다음 날 명단에서 지워진다",
    "탑에서 나온 자가 아무 말도 못 하고 웃기만 한다",
    "협회가 자기 구역을 '포기 구역' 으로 분류한다",
    "은퇴한 영웅이 돌아와 자기를 안다고 말한다",
    "공사장에서 각성 실패자 열 명이 한꺼번에 사라진다",
    "동료가 규정을 어겨 사람을 구했고, 그 대가로 잡혀간다",
    "죽은 줄 알았던 사람이 12층 명부에 살아 있다",
]

# 되돌아올 사물. 체호프의 총.
MOTIF = ["금이 간 영웅 면허", "이름이 지워진 구조 명단", "형이 쓰던 장갑",
         "누구도 열지 않은 유서", "멈춘 손목시계", "12층 출입증",
         "손으로 적은 사망자 장부", "부서진 무전기", "낡은 성경",
         "아이가 그린 영웅 그림", "회수되지 않은 훈장"]

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
THEME = ["한 사람과 여럿 사이", "규칙과 옳음이 갈릴 때", "왜 착한 사람이 당하는가",
         "이름을 되찾기", "대신 짊어지기", "옳은 일을 나쁜 방법으로",
         "아무도 모르게 한 일", "구원은 누구의 몫인가"]

# ---------------------------------------------------------------- 심층
#
# **겉은 가볍고 속은 무겁게.** 표층은 탑·영웅·역전이고, 심층은 한 사상가의 명제다.
#
# 규율 하나가 이 축의 전부다: **인용하지 않는다.** 칸트라는 이름도, "정언명령" 이라는
# 말도 텍스트에 나오면 안 된다. 사상은 개념으로 실리는 것이 아니라 **주인공이 내리는
# 선택으로** 실린다. 그래서 각 항목은 세 칸이다:
#
#   claim  한 줄 명제 (사람 말로 쓴다. 학술 용어를 쓰지 않는다)
#   test   플롯이 그 명제를 시험하는 방식 -- 주인공이 실제로 하게 될 선택
#   cover  겉으로 보이는 것 -- 독자가 처음 읽을 때 느끼는 가벼운 재미
#
# 심층은 디렉터와 화자 프롬프트에 test 로만 실린다. claim 은 사람이 이 파일을 읽을 때
# 쓰고, cover 는 그 장면이 겉으로 어떻게 보여야 하는지를 정한다.
DEPTH = [
    dict(who="칸트",
         claim="사람을 목적으로 대하라. 수단으로만 쓰지 마라",
         test="한 사람을 버리면 열을 살릴 수 있다. 주인공은 그 계산을 거부하고, "
              "거부한 대가를 자기가 치른다",
         cover="계산 안 하고 그냥 밀고 들어가는 시원한 장면"),
    dict(who="칸트",
         claim="옳음은 결과가 아니라 준칙에서 나온다. 누구나 그렇게 해도 되는가",
         test="주인공이 남에게 요구한 규칙을 자기에게도 그대로 적용한다. "
              "예외를 쓸 수 있는데 안 쓴다",
         cover="말한 대로 하는 사람이라 통쾌한 장면"),
    dict(who="헤겔",
         claim="대립하는 둘은 어느 한쪽이 이기는 게 아니라 더 높은 데서 합쳐진다",
         test="영웅과 악당이 같은 것을 지키려 했음이 드러나고, 주인공은 둘 다 아닌 "
              "제3의 길을 만든다",
         cover="적이 알고 보니 같은 편이었던 반전"),
    dict(who="헤겔",
         claim="주인은 인정받으려 노예를 두지만, 노예가 없으면 주인도 없다",
         test="위층이 아래층 없이는 하루도 못 산다는 것을 주인공이 증명해 보인다",
         cover="갑질하던 쪽이 한 방에 무너지는 장면"),
    dict(who="니체",
         claim="같은 삶을 영원히 반복해도 좋다고 할 수 있는가",
         test="주인공이 같은 자리로 되감기는 능력을 쓰면서, 어느 순간 되감지 않기로 한다",
         cover="회귀물의 시원한 반복, 그리고 마지막에 안 돌아가는 선택"),
    dict(who="니체",
         claim="괴물과 싸우는 자는 스스로 괴물이 되지 않게 조심해야 한다",
         test="주인공이 악당의 방법을 쓰기 시작하고, 조연이 그것을 알아본다. "
              "주인공은 멈추거나, 멈추지 않는다",
         cover="다크히어로가 선을 넘는 짜릿함"),
    dict(who="키르케고르",
         claim="가장 중요한 선택은 근거를 다 갖추고 하는 것이 아니다. 뛰어드는 것이다",
         test="아무 보장도 없는 상태에서 주인공이 혼자 12층으로 올라간다. "
              "설명하지 않고 간다",
         cover="설명 없이 혼자 들어가는 멋있는 장면"),
    dict(who="레비나스",
         claim="타인의 얼굴이 나에게 명령한다. 그 명령은 내가 고른 것이 아니다",
         test="주인공이 구할 이유가 하나도 없는 사람과 눈이 마주치고, 그것만으로 간다",
         cover="이유 없이 사람을 구하는 장면"),
    dict(who="도스토옙스키",
         claim="사람들은 자유보다 빵과 안전을 원한다. 그래서 기꺼이 복종한다",
         test="주인공이 진실을 공개할 수 있는데, 사람들이 그것을 원하지 않는다는 것을 안다",
         cover="다 밝혀놓고도 아무도 안 믿는 씁쓸한 장면"),
    dict(who="욥기",
         claim="왜 옳은 사람이 당하는가. 그 물음에 답이 주어지지 않는다",
         test="가장 착한 인물이 아무 이유 없이 죽고, 아무도 설명해주지 않는다. "
              "주인공은 그래도 계속한다",
         cover="갑작스러운 죽음과, 그 뒤의 조용한 복수"),
    dict(who="아우구스티누스",
         claim="악은 따로 있는 것이 아니라 선이 비어 있는 자리다",
         test="악당이 따로 없다. 아무도 악하지 않은데 사람이 죽는 구조가 드러난다",
         cover="배후를 쫓아갔더니 아무도 없는 반전"),
    dict(who="대속(代贖)",
         claim="누군가 대신 짊어져야 끝나는 빚이 있다",
         test="주인공이 남의 몫을 자기 것으로 떠안고, 그 사실을 아무에게도 말하지 않는다",
         cover="혼자 다 뒤집어쓰고 아무 말 안 하는 장면"),
]

AXES = ("time", "impossible", "people", "event", "motif",
        "voice", "theme", "depth")

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
        # **겉은 가볍고 속은 무겁다.** 이 한 줄이 소설의 심층이고, 표층은 cover 다.
        "depth": dict(rng.choice(DEPTH)),
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
    dep = seed.get("depth") or {}
    if not dep.get("test") or not dep.get("cover"):
        out.append("심층에 시험(test)이나 겉모습(cover)이 없다 -- 명제만 있으면 "
                   "인물이 그것을 말로 떠들게 된다")
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
    d = seed.get("depth") or {}
    if d:
        lines.append(f"   심층   {d.get('who', '')} -- {d.get('claim', '')}")
        lines.append(f"          시험: {d.get('test', '')}")
        lines.append(f"          겉모습: {d.get('cover', '')}")
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
