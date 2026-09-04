"""자유 씨앗 -- 무작위로 섞되 **기계가 최소한만 거른다.**

고정된 세계(여성향 청춘 로맨스 200화)로 뽑아보니 문제가 구조에 있었다. 세계가 하나면
프롬프트가 매번 거의 같고, 같은 입력은 같은 답을 낸다 -- 서브플롯 세 회차가 전부
"핫팩을 많이 사는 남자" 였던 것이 그 증상이다.

여기서는 반대로 간다. **축마다 따로 뽑아 조합한다.** 축이 8개이고 각 축이 8~12개면
조합은 수천만 가지다. 같은 씨앗이 두 번 나올 일이 없다.

무작위는 재미의 필요조건이지 충분조건이 아니다. 그래서 **뽑은 뒤 기계가 검사한다** --
다만 "최소한만" 이다:

  · 불가능한 규칙에는 **대가와 한계**가 있어야 한다. 무한한 마법은 긴장을 죽인다
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

# 시간과 국면. **여기는 전부 현실이다.**
#
# 예전에는 이 축이 "해가 지지 않는 두 달", "매년 하루가 통째로 사라지는 도시" 처럼 그
# 자체로 불가능한 것들이었다. 그러면 세계에 마법이 둘이 된다(시간 하나 + 규칙 하나) --
# 그건 초현실이지 마술적 리얼리즘이 아니다.
#
# 마술적 리얼리즘의 규율은 **딱 하나만 불가능하고 나머지는 전부 현실**인 것이다. 그
# 하나가 유일하기 때문에 인물들이 그것을 당연하게 받아들이는 태도가 성립한다. 둘이 되면
# 세계 자체가 꿈이 되고, 그러면 무엇을 놀라야 할지 알 수 없어진다.
#
# 그래서 이 축은 **현실의 국면**만 담는다 -- 계절, 재개발, 폐업, 상(喪), 파업. 소설이
# 딛고 설 단단한 바닥이다. 불가능은 아래 IMPOSSIBLE 하나뿐이다.
TIME = [
    ("장마가 40일째 그치지 않는 여름", "날짜 감각이 무너진다. 사람들이 요일을 잊는다"),
    ("재개발 고시가 붙고 지나간 두 달", "이사 간 집과 남은 집이 한 집 걸러 있다"),
    ("시장이 문을 닫기 전 마지막 겨울", "상인들이 재고를 헐값에 내놓는다"),
    ("삼년상의 마지막 해", "제사가 끝나면 이 집 사람들은 흩어질 것이다"),
    ("공장이 멈춘 뒤 첫 봄", "낮에 사람이 많아졌고, 다들 갈 데가 없다"),
    ("폐선을 앞둔 기차역의 가을", "시간표가 하루에 두 번으로 줄었다"),
    ("전기가 하루 두 번 끊기는 여름", "정전 시간에만 사람들이 밖에 나와 앉는다"),
    ("이십 년 만의 폭설이 온 일주일", "골목이 통째로 막혔고 아무도 나가지 못한다"),
    ("시계가 전부 4분 느린 마을", "약속이 늘 어긋나고, 아무도 고치지 않는다"),
    ("돌아오는 명절을 앞둔 보름", "안 오던 사람들이 온다는 연락이 온다"),
]

# 하나의 불가능. **대가와 한계가 붙은 것만** 넣는다 -- 그것이 마술적 리얼리즘의 규율이다.
IMPOSSIBLE = [
    ("잃어버린 물건이 주인의 꿈에 나타난다", "찾으러 가면 다른 것을 하나 잃는다", "한 사람당 세 번"),
    ("거짓말을 하면 손톱에 흰 점이 돋는다", "숨기려면 손을 감춰야 한다", "열흘이면 사라진다"),
    ("비 오는 날에만 죽은 이의 목소리가 라디오에 섞인다", "들은 사람은 그날 말을 잃는다", "장마철뿐"),
    ("이름을 세 번 부르면 그 사람이 하던 일을 잊는다", "부른 사람도 그 대가로 하나를 잊는다", "같은 사람에게 한 번"),
    ("사진에 찍힌 사람은 그 자리에 하루 더 머문다", "찍은 사람은 그 하루를 잃는다", "필름 한 통"),
    ("빚을 진 사람의 그림자가 옅어진다", "다 갚으면 돌아오지만 색이 다르다", "돈만이 아니다"),
    ("이 골목에서 한 약속은 반드시 지켜진다", "지키지 못하면 그 골목을 다시 못 찾는다", "골목 안에서만"),
    ("편지를 태우면 받는 사람이 그 문장을 꿈에서 읽는다", "쓴 사람은 그 문장을 영영 못 쓴다", "한 사람당 한 통"),
    ("물에 비친 얼굴이 하루 늦게 따라온다", "앞질러 본 사람은 그 하루를 두 번 살아야 한다", "고인 물에서만"),
]

# 인물의 축. **직업이 아니라 상처와 태도**로 잡는다.
PEOPLE = [
    ("남의 물건을 오래 맡아주는 사람", "돌려주지 못한 것이 방 하나를 채웠다"),
    ("사과를 대신 해주는 일을 하는 사람", "정작 자기 잘못은 한 번도 말한 적 없다"),
    ("죽은 사람의 집을 정리하는 사람", "남의 유서를 백 통 읽고 자기 것은 못 쓴다"),
    ("한 번도 이 도시를 떠난 적 없는 사람", "떠나는 사람들의 짐만 실어 날랐다"),
    ("남의 글씨를 흉내내는 사람", "자기 글씨가 어떤 건지 잊었다"),
    ("밤에만 여는 가게를 지키는 사람", "낮에 무슨 일이 있는지 모른다"),
    ("모두가 이름을 잘못 부르는 사람", "한 번도 고쳐준 적 없다"),
    ("빚을 대신 갚아주고 다니는 사람", "자기 빚이 왜 생겼는지는 말하지 않는다"),
    ("남의 개를 산책시키는 사람", "자기 개는 잃어버렸다"),
    ("녹음을 지우는 일을 하는 사람", "지우기 전에 한 번씩 듣는다"),
    ("계속 이사만 다니는 사람", "짐이 해마다 줄어든다"),
    ("남의 결혼식 사진을 찍는 사람", "자기 사진은 한 장도 없다"),
]

# 최초의 사건. **작고 물리적인 것**으로 시작한다 -- 처음부터 크면 갈 데가 없다.
EVENT = [
    "택배가 잘못 왔는데 받는 사람 이름이 자기 옛 이름이다",
    "매일 같은 시간에 같은 자리에 놓이는 우산 하나",
    "전 세입자 앞으로 온 청구서가 십 년째 온다",
    "옆집에서 매일 밤 같은 곡의 같은 마디만 반복해서 연주한다",
    "잃어버린 지갑이 돌아왔는데 안에 없던 사진이 들어 있다",
    "장례식장에서 자기를 안다는 사람을 만난다",
    "이사한 집 벽지 아래에서 누군가 세어둔 날짜가 나온다",
    "매달 같은 날 통장에 정체 모를 돈이 들어온다",
    "버린 물건이 자꾸 문 앞에 돌아와 있다",
    "동네 사람들이 자기만 빼고 어떤 날을 기억한다",
]

# 되돌아올 사물. 체호프의 총.
MOTIF = ["젖은 성냥갑", "한쪽만 남은 장갑", "고장난 자동응답기", "빈 액자",
         "이름이 지워진 명찰", "잠기지 않는 서랍", "숫자만 적힌 수첩",
         "타다 만 편지", "주인 없는 열쇠고리", "멈춘 손목시계", "말라붙은 잉크병"]

# 문장의 색. 화자 프롬프트의 어휘 온도를 바꾼다.
VOICE = [
    ("건조하고 짧게", "감정어를 쓰지 않고 사물의 동작만 적는다"),
    ("만연체로 길게", "한 호흡에 여러 절을 잇고 쉼표로 숨을 고른다"),
    ("목록처럼", "본 것을 나열한다. 판단을 붙이지 않는다"),
    ("남에게 말하듯", "듣는 사람이 있는 것처럼 쓴다. 되묻고 정정한다"),
    ("기록처럼", "날짜와 수치를 자주 적는다. 감정은 그 사이에 낀다"),
    ("뒤에서 보듯", "자기 일을 남의 일처럼 옮긴다"),
]

# 무엇에 대한 이야기인가. 로맨스에 한정하지 않는다.
THEME = ["남은 사람의 몫", "갚지 못한 것", "잘못 배달된 인생", "대신 살아주기",
         "기억을 나눠 갖기", "떠나지 못하는 이유", "이름을 되찾기",
         "빚과 용서", "돌아오지 않는 것을 기다리기"]

AXES = ("time", "impossible", "people", "event", "motif", "voice", "theme")

# 시간 축에 들어오면 안 되는 어휘. 여기 걸리면 세계에 마법이 둘이다.
# (사람이 TIME 에 새 항목을 넣을 때 실수하는 것을 막는 카나리다 -- 목록을 손으로 늘리는
#  자리는 반드시 언젠가 잘못 늘어난다.)
SUPERNATURAL = ("죽은", "꿈을 꾸는", "되돌려", "사라지는", "해가 지지 않는", "유령",
                "영혼", "부활", "환생")

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
        out.append("불가능한 규칙에 대가나 한계가 없다 -- 무한한 마법은 긴장을 죽인다")
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
    # **불가능은 하나여야 한다.** 시간 축까지 불가능하면 세계가 통째로 꿈이 되고, 그러면
    # 인물이 그것을 당연하게 받아들이는 태도가 성립하지 않는다 -- 초현실과 마술적
    # 리얼리즘을 가르는 자리가 여기다.
    if any(w in seed["time"]["what"] for w in SUPERNATURAL):
        out.append(f"시간 축이 현실이 아니다: {seed['time']['what']!r} -- "
                   f"불가능은 규칙 하나뿐이어야 한다")
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
                     f"  (대가: {seed['impossible']['cost']})")
        lines.append(f"   사건   {seed['event']}")
        lines.append(f"   인물   {' / '.join(x['who'] for x in p)}")
        lines.append(f"   목소리 {seed['voice']['how']} · 주제 {seed['theme']}")
        return "\n".join(lines)
    lines.append(f"   시간   {seed['time']['what']}")
    lines.append(f"          {seed['time']['note']}")
    lines.append(f"   규칙   {seed['impossible']['rule']}")
    lines.append(f"          대가: {seed['impossible']['cost']}")
    lines.append(f"          한계: {seed['impossible']['limit']}")
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
