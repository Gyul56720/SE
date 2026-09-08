"""연속 집필 -- **조립하지 않고 한 문장에서 이어 쓴다.**

결말을 먼저 정하고 거꾸로 쌓는 방식(episode.py)은 인과가 튼튼한 대신 문장이 칸에 갇힌다.
씬마다 분량이 할당되고 회차마다 구조가 요구되고 관문 아홉이 매번 판정한다. 그렇게 나온
원고가 무겁고 단조로웠다.

여기서는 관문을 다 끄고 **모순 하나만** 남긴다. 자유롭게 쓰라고 하면 모델은 세 덩어리
뒤에 인물 이름을 바꾸고 죽은 사람을 걷게 한다 -- 취향은 사람이 보면 되지만 모순은
길어질수록 사람도 못 본다.

실행: python3 tests/test_flow.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import flow                                                # noqa: E402

# **이 파일은 예전 프롬프트를 켜고 본다.** 기본은 axes 다(flow.PROMPT="axes") --
# 프롬프트를 재는 축에서 짓고, 손으로 쓴 문장론은 한 줄도 안 넣는다.
# 여기서 검사하는 것은 그 옛 작법서 블록의 내용이라 켜 놓고 본다.
flow.PROMPT = "legacy"


# **이 파일은 서사층까지 켜고 본다.** 기본값은 문면층만이다(flow.LAYER = "text") --
# 재는 것 열넷이 전부 문면층인데 서사까지 시키면 지켜졌는지 알 수가 없어서다.
# 여기서 검사하는 것은 그 서사층 블록의 **내용**이라 켜 놓고 본다.
flow.LAYER = "all"


fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


print("[게이트] **최소로만 개입한다** -- 자유도가 이 모드의 전부다")
print("      ← 실측: '은색 물건' 이 '1950년대 독일제 은색 지포' 로 자세해진 것을 기각했다.")
print("        그건 같은 라이터고, 그런 기각이 원고를 못 나오게 한다.")
led = flow.blank()["ledger"]
ok(not flow._merge(led, {"objects": {"라이터": "은색 물건"}}), "사물은 기록만")
ok(not flow._merge(led, {"objects": {"라이터": "1950년대 독일제 은색 지포"}}),
   "자세해져도 통과")
ok(led["objects"]["라이터"].startswith("1950"), "자세한 쪽을 남긴다")
ok(not flow._merge(led, {"objects": {"라이터": "붉은 플라스틱"}}),
   "**아예 달라져도 기각하지 않는다** ← 주변 사물은 게이트가 보지 않는다")
ok(not flow._merge(led, {"places": {"양조장": "레이캬비크 외곽"}})
   and not flow._merge(led, {"places": {"양조장": "아쿠레이리 근처"}}),
   "장소도 기각하지 않는다")
ok(not flow._merge(led, {"facts": {"날씨": "눈"}})
   and not flow._merge(led, {"facts": {"날씨": "비"}}), "잡다한 사실도 기각하지 않는다")

print("[게이트] 스쳐 간 인물은 그냥 넘기는가")
for i in range(4):
    c = flow._merge(led, {"people": {"행인": {"나이": str(40 + i * 10)}}})
    ok(not c, f"행인 {i + 1}회차 나이가 바뀌어도 통과")
ok(led["people"]["행인"]["_seen"] == 4, "등장 횟수는 세어 둔다")

print("[게이트] 주요 인물의 핵심 칸만 잡는가")
print("      ← 자주 나오고(3회) 카드도 두툼해야(3칸) 주요 인물이다. 둘 중 하나만 보면")
print("        행인이 두 번 언급된 것으로 주요 인물이 되고 원고가 기각된다.")
for f in ({"나이": "42", "취미": "낚시"}, {"말투": "짧게 끊는다"}, {"가족": "형이 있었다"}):
    ok(not flow._merge(led, {"people": {"요우": f}}), f"요우 카드가 자란다 {list(f)}")
ok(not flow._merge(led, {"people": {"요우": {"취미": "등산"}}}),
   "취미가 바뀌어도 통과  ← 핵심 칸이 아니다")
c = flow._merge(led, {"people": {"요우": {"나이": "30"}}})
ok(c and "나이" in c[0], f"나이가 뒤집히면 잡는다 ({c})")
ok(led["people"]["요우"]["나이"] == "42", "기각된 값은 안 들어간다")
ok(not flow._merge(led, {"people": {"요우": {"나이": "42세"}}}),
   "'42' 와 '42세' 는 같은 나이다  ← 표기 차이로 기각하지 않는다")
flow._merge(led, {"people": {"요우": {"생사": "죽었다"}}})
c2 = flow._merge(led, {"people": {"요우": {"생사": "살아 있다"}}})
ok(c2, f"죽은 사람이 걸어 들어오면 잡는다 ({c2})")
ok(not flow._merge(led, {"people": {"요우": {"성격": "말수 적고 손이 빠르다"}}}),
   "성격이 자세해지는 것은 통과")

print("[원장] 카드가 브리핑에 펼쳐지는가")
b2 = flow.brief(led)
ok("[인물]" in b2 and "말투 짧게 끊는다" in b2, "카드가 펼쳐진다")
ok("_seen" not in b2, "내부 표식은 감춘다")
ok("가족 형이 있었다" in b2, "가족까지 실린다  ← 나중에 녹여낼 재료다")

print("[원장] 쓰레기 값은 무시하는가")
before = dict(led["facts"])
flow._merge(led, {"facts": {"x": "", "y": None, "z": {"안": "됨"}}})
ok(led["facts"] == before, "빈 값·None·객체는 안 넣는다  ← 추출기가 그런 것을 보낸다")

print()
print("[프롬프트] 첫 덩어리에 첫 문장과 흐름이 실리는가")
book = flow.blank()
p0 = flow.write_prompt(book)
ok(flow.FIRST[:20] in p0, "첫 문장이 실린다")
# 첫 덩어리 지시는 **무엇을 쓸지가 아니라 어떻게 열지만** 말해야 한다. 예전엔 여기에
# "양조장의 내력 / 크리스마스 이브 / 오로라" 가 박혀 있었는데, 첫 문장을 갈아 끼우자
# 그것이 남의 이야기를 시키는 각본이 됐다.
ok("첫 문장이 놓은 좌표에서 출발해라" in p0, "첫 문장의 좌표에서 출발시킨다")
ok("사람을 하나 만나게 해라" in p0, "손잡이를 만들게 한다  ← 세계는 사람에서 자란다")
ok("양조장" not in p0 and "오로라" not in p0,
   "특정 씨앗의 소재가 박혀 있지 않다  ← 첫 문장을 갈아 끼워도 지시가 남지 않는다")
book2 = flow.blank()
book2["chunks"] = ["이어지는 산문. " * 200]
p1 = flow.write_prompt(book2)
ok("첫 덩어리가 할 일" not in p1, "이어쓰기에는 첫 덩어리 지시가 안 실린다")
ok("지금까지의 끝부분" in p1, "꼬리를 넘긴다")
# **원고가 길어져도 프롬프트가 그만큼 커지면 안 된다.** 첫 덩어리와 이어쓰기를 견주면
# 급발진·잡소리처럼 이어쓰기에만 실리는 항목까지 세어져서, 재려는 것과 다른 것을 잰다.
# 재야 할 것은 **꼬리가 늘 때 프롬프트가 늘어나는 몫**이다.
big_book = flow.blank()
big_book["chunks"] = ["가" * 50000]
grew = len(flow.write_prompt(big_book)) - len(p1)
ok(grew <= flow.TAIL, f"원고가 250배 늘어도 프롬프트는 꼬리만큼만 는다 ({grew:,}자)")

print("[프롬프트] 문체와 규율이 실리는가")
for key, label in (("가볍고 재미있게", "가벼운 온도"),
                   ("**인물에 맞게.**", "대사는 인물에 맞게"),
                   ("그 자리에서 사람을 만들어라", "새 인물이 나오면 사람을 만든다"),
                   ("점층", "점층"),
                   ("길이를 섞어라", "장단문 섞기"),
                   ("사정을 하나 더", "연쇄 확장"),
                   ("두 번 울리는 종", "편의주의 금지"),
                   ("대가를 치르고 얻는다", "정보에 값을 매긴다"),
                   ("실패한 채로 둬라", "실패를 되돌리지 않는다")):
    ok(key in p0, label)
# **2026-09-08 에 뒤집었다.** "줄거리를 미리 정하지 마라 · 회차도 씬도 없다" 는 DRIFT 의
# 원칙이었고 문체를 얻었다. 값은 플롯이었다(STORY.md 2절: 회차 층이 없어서 플롯도
# 연출도 재미없었다). 이제 회차 각본(beat.py)이 덩어리 위에 선다.
ok("줄거리를 미리 정하지 마라" not in p0 and "회차도 씬도 없다" not in p0,
   "줄거리 금지 · 회차 금지를 뺐다  ← 회차 각본이 그 자리다")

print()
print("[루프] 모순이면 기각하고 다시 쓰는가")


# 리듬 자에도 메아리 자에도 걸리지 않는 본문. **시도마다 달라야 한다** -- 매번 같은 글을
# 돌려주면 꼬리 절단(echo.trim)이 통째로 잘라내고, 그러면 여기서 세는 횟수가 어긋난다.
# 그것도 자가 제대로 도는 것이지 픽스처가 옳은 것이 아니다. 이 시험이 보는 것은 모순이라,
# 다른 자에 걸리지 않는 글을 넣어야 한다.
def clean(tag: int) -> str:
    """자에 걸리지 않는 본문. **여기서 보는 것은 모순이지 문체가 아니라서**, 리듬·확산·
    메아리 자가 물면 재시도가 늘고 아래에서 세는 횟수가 어긋난다.

    그래서 셋을 지킨다: 길이를 섞고(리듬), 점층을 넣고(리듬), **줄마다 다르게 쓴다**(메아리).
    """
    풍경 = [
        f"{tag}년 {i}월의 항구는 오후 세 시부터 어두워졌고, 바람에는 생선과 디젤과 "
        f"눈 냄새가 {i}할쯤 섞여 있었다."
        if i % 3 else
        f"아니, 냄새라기보다는 {tag}년 {i}월이 통째로 실려 온 것에 가까웠다."
        for i in range(1, 13)
    ]
    대사 = [f'"{w} 드실래요?"' for w in ("커피", "차", "물", "맥주")]
    대사 += [
        # 아주 긴 대사 하나 -- 한 사람이 자기 얘기에 빠져 있는 대목이 없으면 자에 걸린다.
        f'"그게 말입니다, {tag}년 겨울에 등이 꺼지고 나서 한 삼십 분쯤 아무것도 안 '
        f'보였는데, 그때 물소리가 평소랑 달랐어요. 아니 물소리가 아니라 물이 없는 '
        f'소리였나. 아무튼 나는 그 소리를 지금도 가끔 듣습니다. 우리 형이 그해 겨울에 '
        f'배를 띄웠다가 안 돌아왔는데, 그때도 꼭 그 소리가 났었고요. 아무도 안 믿지만."',
        f'"아뇨, 괜찮습니다. 방금 마셨거든요. 아니, 마신 것 같기도 하고 아닌 것 '
        f'같기도 하고, {tag}년쯤부터는 그게 잘 구분이 안 갑니다."',
        f'"구분이 안 가면 그냥 드시면 되잖아요. 나는 그런 걸로 고민해 본 적이 없는데, '
        f'하긴 고민이라는 걸 잘 안 하는 편이라 그게 자랑은 아니겠습니다만."',
    ]
    # 이름을 여덟 번 부르면 diffusion.overused 가 잡는다 -- 회수는 다시 부르는 것이
    # 아니라 다시 쓰는 것이라서다. 두 번째부터는 대명사로 받는다.
    자리 = [
        f"{'요우는' if i == 1 else '그는'} 창가 {tag}-{i}번 자리에 앉아, 유리에 서린 "
        f"김 너머로 밖이라기보다는 밖의 소문 같은 것을 {i}분쯤 바라보았다."
        for i in range(1, 9)
    ]
    return "\n".join(풍경 + 대사 + 자리)


class Fake:
    """첫 시도는 원장과 어긋나게, 두 번째는 맞게 쓴다."""

    def __init__(self):
        self.tries, self.prompts = 0, []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        if "JSON 만 출력" in prompt and "새로 확정된 사실만" in prompt:
            wrong = self.tries == 1
            # 세계를 넓히는 것도 같이 돌려준다 -- 확산 자(diffusion.py)에 걸리면
            # 리듬 때문에 다시 쓰게 되어 여기서 세는 횟수가 어긋난다.
            # **회차마다 다른 것을 내놓는다.** 같은 것을 돌려주면 두 번째부터 "새것 0개"
            # 가 되어 확산 자에 걸리고, 그러면 여기서 세는 재시도 횟수가 어긋난다.
            n = self.tries
            return json.dumps({"people": {"요우": {"나이": "30" if wrong else "42"},
                                          f"한나{n}": {"직업": "등대지기"}},
                               "places": {f"등대{n}": "북쪽 곶"},
                               "objects": {f"무전기{n}": "오래된 것"}},
                              ensure_ascii=False)
        self.tries += 1
        return clean(self.tries)


# **길이 되먹임은 여기서 끈다.** 아래 검사들이 재는 것은 모순·원장·되먹임 배선이지
# 분량이 아니다. clean() 이 1,499자라 기본값(CHUNK*0.6 = 1,920자)에 걸려 이어받기가
# 한 번 더 돌고, 그러면 호출 수를 세는 검사들이 어긋난다. 분량 되먹임 자체는 파일
# 맨 아래 [분량] 절에서 기본값 그대로 잰다.
flow.CHUNK_MIN = 0.0


def main_char():
    """주요 인물 하나가 이미 선 원장 -- 자주 나왔고(3회) 카드도 두툼하다(3칸)."""
    bk = flow.blank()
    bk["ledger"]["people"]["요우"] = {"나이": "42", "직업": "정비공",
                                     "말투": "짧게 끊는다", "_seen": 3}
    return bk


bk = main_char()
f = Fake()
r = flow.step(bk, f)
ok(r["status"] == "ok", f"두 번째 시도에서 채택 ({r['status']})")
ok(f.tries == 2, f"한 번 기각하고 다시 썼다 ({f.tries}회)")
print()
print("[규모] **5만 자를 써도 프롬프트가 원장으로 차지 않게**")
print("      ← 스쳐 간 사람이 쉰 명 쌓이면 그들의 카드가 꼬리와 확산 지시를 밀어낸다.")
big = flow.blank()["ledger"]
big["people"]["요우"] = {"나이": "42", "직업": "정비공", "말투": "짧게 끊는다", "_seen": 5}
for i in range(40):
    big["people"][f"행인{i}"] = {"직업": "행인", "_seen": 1}
b = flow.brief(big)
ok("나이 42 · 직업 정비공" in b, "주요 인물은 카드를 통째로 펼친다")
ok("[스쳐 간 사람]" in b, "조연은 한 줄로 접는다")
ok(b.count("\n") < 8, f"조연 마흔이 있어도 줄 수가 늘지 않는다 ({b.count(chr(10)) + 1}줄)")
ok("행인39" in b, "접혀도 이름은 남는다  ← 확산의 연료로는 그대로 쓰인다")
ok(flow.is_main(big["people"]["요우"]) and not flow.is_main(big["people"]["행인0"]),
   "펼치는 잣대가 _merge 의 '주요 인물' 과 같다")

print()
print("[농도] **원장은 자라도 브리핑은 자라면 안 된다**")
print("      ← 실측: '뒤로 갈수록 밀도가 높아져서 처음 1/2 지점 정도로 유지해주면 좋겠다'.")
print("        인물·장소·사물·사실이 쌓이고 그게 매번 통째로 실리니 농도가 올라갔다.")
grow = flow.blank()["ledger"]
grow["people"]["요우"] = {"나이": "42", "직업": "정비공", "말투": "짧게 끊는다", "_seen": 9}
sizes = {}
for i in range(61):
    flow._merge(grow, {"objects": {f"물건{i}": "어떤 것인가 한 줄"},
                       "facts": {f"사실{i}": "확정된 값 한 줄"},
                       "people": {f"행인{i}": {"직업": "행인"}}}, at=i)
    sizes[i] = len(flow.brief(grow, now=i))
ok(sizes[60] <= sizes[20] * 1.1,
   f"스무 덩어리 뒤로는 안 자란다 ({sizes[20]}자 → {sizes[60]}자)")
ok(sizes[60] < flow.BRIEF_MAX, f"상한 아래에 머문다 ({sizes[60]} < {flow.BRIEF_MAX})")
ok("요우" in flow.brief(grow, now=60),
   "주요 인물은 나이를 안 본다  ← 그 카드가 대사를 갈라 놓는 근거다")
ok("행인3" not in flow.brief(grow, now=60),
   "오래 전 스쳐 간 사람은 접힌다  ← 그 이름이 쉰 개면 그것이 곧 밀도다")
ok("행인58" in flow.brief(grow, now=60), "최근에 스쳐 간 사람은 남는다")
ok("물건59" in flow.brief(grow, now=60) and "물건2" not in flow.brief(grow, now=60),
   "사물도 창으로 자른다")
ok(len(grow["objects"]) == 61,
   "접힌 것이 원장에서 사라지지는 않는다  ← 눈앞에서 치우는 것이지 잊는 것이 아니다")

print()
print("[영속] **시작하자마자 한 번 저장한다**")
print("      ← 첫 덩어리를 다 받고서야 파일이 생기면, 아직 쓰는 중인지 시작도 못 한 건지")
print("        밖에서 구분할 수가 없다(실측: --read 가 FileNotFoundError 로 죽었다).")


class Dead:
    def __call__(self, prompt):
        raise RuntimeError("모델 호출 실패")


flow.BACKOFF = (0,)      # 런은 실패하면 쉬었다 다시 한다. 시험에서는 안 쉰다.


import tempfile as _tf                                                # noqa: E402
_p = Path(_tf.mkdtemp()) / "start.json"
try:
    flow.run(flow.blank(flow.FIRST), Dead(), 3000, str(_p))
except Exception:
    pass
ok(_p.exists(), "첫 호출이 죽어도 파일은 남는다")
if _p.exists():
    ok(json.loads(_p.read_text(encoding="utf-8"))["chunks"] == [],
       "빈 원고로라도 저장된다  ← 그래야 '없다' 가 '시작 못 했다' 를 뜻한다")

# 되먹임은 이제 원고 프롬프트가 아니라 **손질 프롬프트**로 간다 -- 원고를 다시 받지
# 않고 걸린 문장만 주고받는다.
retry = [q for q in f.prompts if "각 문장 앞 대괄호가 그 문장의" in q]
ok(retry, "고칠 것이 손질 프롬프트로 간다  ← 원고를 다시 받지 않는다")
ok(any("나이" in q or "어긋난다" in q for q in retry), "무엇이 어긋났는지까지")
ok(all("전부 고쳐라" in q for q in retry),
   "한 번에 전부 고치라고 한다  ← 하나씩 시키면 호출이 그만큼 는다")
ok(len(bk["chunks"]) == 1, "채택된 덩어리만 남는다")

print("[루프] 목표 자수까지 이어 쓰는가 · 파일로 남는가")
d = Path(tempfile.mkdtemp()) / "flow.json"


class Clean:
    """목표 분량까지 도는지만 본다. **덩어리마다 다른 글**을 돌려줘야 한다 -- 같은 글을
    되풀이하면 메아리 자가 옳게 기각해서, 여기서 재려는 것과 다른 것을 재게 된다."""

    def __init__(self):
        self.n = 0

    def __call__(self, prompt):
        if "새로 확정된 사실만" in prompt:
            return "{}"
        self.n += 1
        return clean(1900 + self.n)


bk2 = flow.blank()
res = flow.run(bk2, Clean(), 3000, str(d))
ok(res["chars"] >= 3000, f"{res['chars']:,}자까지 쓴다 ({res['chunks']}덩어리)")
ok(d.exists(), "덩어리마다 저장한다")
saved = json.loads(d.read_text(encoding="utf-8"))
ok(len(saved["chunks"]) == res["chunks"], "저장된 것과 메모리가 같다")
ok(flow.text_of(saved).count("항구는 오후 세 시부터") > 2, "이어 붙여 읽힌다")

print("[루프] 못 풀면 멈추는가  ← 같은 모순을 무한히 반복하지 않는다")


class Stubborn:
    def __call__(self, prompt):
        if "새로 확정된 사실만" in prompt:
            return json.dumps({"people": {"요우": {"나이": "30"}}}, ensure_ascii=False)
        return "산문. " * 120


bk3 = main_char()
r3 = flow.step(bk3, Stubborn())
# **폐기는 없다.** 모순을 못 풀어도 원고는 쓰고, 못 고친 것은 장부에 적는다.
ok(r3["status"] == "ok", f"버리지 않는다 ({r3['status']})")
ok(bk3["chunks"], "원고에 들어간다  ← 예전에는 여기서 3,200자를 통째로 버렸다")

print("[추출] 카드 칸을 뽑으라고 지시하는가")
e = flow.extract_prompt("아무 산문")
for f in ("나이", "키", "성격", "가족", "과거", "트라우마", "취미", "전공", "직업",
          "말투", "버릇"):
    ok(f in e, f"{f} 칸")
ok("안 나온 칸은 빼라" in e and "지어내지 마라" in e,
   "안 나온 칸은 비운다  ← 추출기가 지어내면 그것이 원장의 거짓이 된다")
# **예시가 아니라 물어볼 것으로 준다.** 말투 예문을 박아 두면 원장이 그 말투로만
# 채워지고, 원장이 다시 다음 덩어리의 프롬프트가 된다 -- 예문이 두 바퀴 도는 자리다.
ok("말끝을 어떻게 맺는지" in e, "말투에서 무엇을 보라고 하는지 짚어 준다")
ok("존댓말인데" not in e, "말투를 예문으로 박아 두지는 않는다")


print("[되먹임] **한 번에 안 고쳐지면 프롬프트가 틀린 것이다**")
print("      ← 손질은 덩어리마다 한 번뿐이다. 같은 지시를 한 번 더 보내면 같은 것이 온다.")
print("        그러니 고칠 것은 원고가 아니라 지시다 -- 그것도 손질이 아니라 초고에서.")
_g = "그는 문을 열고 밖을 보면서 담배를 물었는데 불이 붙지 않아서 다시 뒤졌다."
_it, _kd = flow.mend_items("\n".join([_g] * 10), [], "", with_kinds=True)
ok("glue" in list(_kd.values())[0], f"걸린 갈래를 같이 돌려준다 ({list(_kd.values())[0]})")
_v = flow.verify_patch([(_it[0][0], "짧게 끊었다.")], _kd)
ok(_v.get("glue", (0, 0))[1] == 1, "고친 문장을 자에 다시 대 본다  ← 호출은 안 쓴다")
ok(_v.get("long", (0, 0))[1] == 0, "안 고쳐진 갈래는 실패로 센다  ← '끼워 넣었다' 는 '고쳤다' 가 아니다")

_bk = flow.blank()
flow._mend_learn(_bk, {"glue": (flow.MEND_TRIES, 1)})
ok(_bk["mend"]["glue"] == [flow.MEND_TRIES, 1], "성공/시도가 원고에 쌓인다  ← 이어 쓸 때도 이어 배운다")
ok(flow.mend_broken(_bk), "반절을 못 넘기면 '안 고쳐지는 갈래' 로 잡는다")
_bk2 = flow.blank()
flow._mend_learn(_bk2, {"glue": (2, 0)})
ok(not flow.mend_broken(_bk2),
   f"몇 번 안 해 보고 단정하지 않는다 ({flow.MEND_TRIES}번은 해 본다)")
_bk["chunks"] = ["앞."]
_ap = flow.write_prompt(_bk)
ok("[초고에서 막을 것]" in _ap, "안 고쳐지는 갈래를 초고 단계로 옮긴다  ← 호출은 안 는다")
ok("처음 쓸 때 아예 그렇게 쓰지 마라" in _ap, "되받아 고치지 말고 미리 막으라고 한다")
ok("[초고에서 막을 것]" not in flow.write_prompt(dict(flow.blank(), chunks=["앞."])),
   "안 걸린 갈래로는 아무 말도 안 한다  ← 늘 켜진 경고는 꺼진 것과 같다")


print("[층] **문면층만 싣는다** -- 기본값")
print("      ← 재는 것 열넷이 전부 문면층인데 프롬프트는 서사까지 요구하고 있었다.")
print("        재지 않는 것을 시키면 지켜졌는지 알 수가 없고, 한꺼번에 시키면 안 지켜진다.")
_was = flow.LAYER
try:
    flow.LAYER = "text"
    _bk = flow.blank(); _bk["chunks"] = ["앞."] * 4; _bk["genre"] = "youth"
    _tp = flow.write_prompt(_bk)
    for _gone in ("[확산]", "[전개]", "[어디로 가든]", "[리얼리즘]", "[표류가 먼저다]",
                  "[청춘물]", "[세기]"):
        ok(_gone not in _tp, f"{_gone} 을 안 싣는다")
    # 필수 목록은 남되 **문면 항목만** 남는다 -- 점층과 회수는 문장 층위의 일이다.
    ok("[이 덩어리에 반드시]" in _tp and "심어 놓고 회수한다" in _tp,
       "필수 목록의 문면 항목은 남는다  ← 점층과 회수는 문장의 일이다")
    ok("욕망 하나가 결판난다" not in _tp and "인물이 이 덩어리를 지나며" not in _tp,
       "필수 목록의 서사 항목은 빠진다")
    for _keep in ("[문장]", "[리듬]", "[말맛]", "[대사]", "[점층]",
                  "[세계 — 지금까지 놓인 것들]", "[고정]"):
        ok(_keep in _tp, f"{_keep} 은 남는다")
    ok("(아직 비어 있다)" in _tp or "인물" in _tp,
       "원장 자체는 싣는다  ← 없으면 모순 검사가 죽는다")
    flow.LAYER = "all"
    _ap = flow.write_prompt(_bk)
    ok(len(_tp) < len(_ap) - 2000,
       f"프롬프트가 줄어든다 ({len(_ap):,} -> {len(_tp):,}자)")
    ok("[확산]" in _ap, "층을 켜면 예전 그대로다  ← 지우는 것이 아니라 안 싣는 것이다")
finally:
    flow.LAYER = _was

print("[되먹임] 고칠 것을 한 번에 다 보내는가  ← 하나씩 시키면 호출이 그만큼 는다")


class Limp:
    """게이트에 계속 걸리는 산문. 손질 프롬프트를 받아 적어 둔다."""

    def __init__(self):
        self.sent = []

    def __call__(self, prompt):
        if "새로 확정된 사실만" in prompt:
            return json.dumps({}, ensure_ascii=False)
        if "각 문장 앞 대괄호가" in prompt:
            self.sent.append(prompt)
            return json.dumps({}, ensure_ascii=False)
        # 서로 다른 문장이어야 한다 -- 같은 문장은 원문에서 어느 것인지 못 짚어
        # 손질 목록에서 하나로 접힌다(그것도 옳은 동작이다).
        return " ".join(f"{i}번 배가 들어왔다." for i in range(40))


_lm = Limp()
flow.step(main_char(), _lm)
ok(len(_lm.sent) == 1, f"손질은 한 번만 부른다 ({len(_lm.sent)}회)")
ok(_lm.sent and _lm.sent[0].count("\n1. ") == 1, "번호를 붙여 한 장에 담는다")
ok(_lm.sent and _lm.sent[0].count(". [") > 1,
   "여러 문장을 한 번에 보낸다  ← 갈래마다 부르면 호출이 갈래 수만큼 는다")


print("[호출] 버릴 원고에 추출을 쓰지 않는가  ← 규칙은 그대로, 두드리는 횟수만 줄인다")


class Count:
    def __init__(self):
        self.w = self.x = self.m = 0

    def __call__(self, prompt):
        if "새로 확정된 사실만" in prompt:
            self.x += 1
            return json.dumps({}, ensure_ascii=False)
        if "각 문장 앞 대괄호가" in prompt:
            self.m += 1
            return json.dumps({}, ensure_ascii=False)
        self.w += 1
        return "짧다. " * 80


_c = Count()
flow.step(main_char(), _c)

ok(_c.w + _c.x + _c.m <= 4,
   f"한 덩어리에 {_c.w + _c.x + _c.m}회  ← 예전에는 12회였다 (화자 6 · 추출 6)")
ok(_c.w == 1, f"화자는 한 번만 부른다 ({_c.w}회)  ← 원고를 다시 받지 않는다")
ok(_c.m <= 1, f"손질도 한 번만 부른다 ({_c.m}회)  ← 갈래를 나눠 부르지 않는다")
ok(_c.x <= 1,
   f"추출도 한 번뿐이다 ({_c.x}회)  ← 모순이 없는데 고친 뒤 원장을 다시 사지 않는다")


class Few:
    """리듬만 한둘 걸리게 하는 가짜 화자 -- 결함(모순·메아리)은 없다."""

    def __init__(self):
        self.w = self.x = self.m = 0

    def __call__(self, prompt):
        if "새로 확정된 사실만" in prompt:
            self.x += 1
            return json.dumps({}, ensure_ascii=False)
        if "각 문장 앞 대괄호가" in prompt:
            self.m += 1
            return json.dumps({}, ensure_ascii=False)
        self.w += 1
        return "짧다. " * 80


print("[호출] 한 문장 고치자고 호출 한 번을 쓰는가")
_f = Few()
flow.step(main_char(), _f)
ok(flow.MEND_MIN >= 2, f"손질 문턱이 있다 (MEND_MIN={flow.MEND_MIN})")
_items = flow.mend_items("짧다. " * 80, [], "")
ok(_f.m == (1 if len(_items) >= flow.MEND_MIN else 0),
   f"걸린 것 {len(_items)}개 · 손질 {_f.m}회  ← 문턱 아래면 다음 덩어리로 넘긴다")
_two = "요우는 서른이 되었다. 요우는 서른이 되었다. 그리고 문을 닫았다."
_it = flow.mend_items(_two, ["요우의 나이: 앞에서는 '42' 였는데 지금 '30' 다"],
                      "요우는 서른이 되었다.")
ok(len({s for s, _ in _it}) == len(_it),
   "같은 문장을 두 번 보내지 않는다  ← 번호가 겹치면 되받은 것을 못 끼운다")
ok(any(" / " in why for _, why in _it),
   f"두 갈래에 걸린 문장은 딱지를 겹쳐 붙인다  ← 뒤엣것을 버리면 이번 회에 안 고쳐진다")
ok("한꺼번에" in flow.mend_prompt(_it),
   "겹친 딱지를 한 문장으로 풀라고 말한다  ← 수정은 한 번이다")

ok(flow.mend_items("요우는 서른이 되었다. 그리고 문을 닫았다.",
                   ["요우의 나이: 앞에서는 '42' 였는데 지금 '30' 다"], ""),
   "모순은 하나여도 고친다  ← 결함은 문턱을 안 본다")

_debt_before = Path("drift.debt.jsonl").exists()
flow.step(main_char(), Few())
ok(Path("drift.debt.jsonl").exists() == _debt_before,
   "원고 경로가 없으면 장부를 안 쌓는다  ← 테스트가 실측 장부를 오염시키던 자리다")


print("[손질] 걸린 문장만 보내는가  ← input 토큰을 아끼는 자리다")
_lines_in = ["짧다.", "또 짧다.", "역시 짧다."]
_items = [(l, "짧다") for l in _lines_in]
_pp = flow.mend_prompt(_items)
ok(len(_pp) < 800, f"손질 프롬프트가 {len(_pp)}자  ← 원고 프롬프트는 18,000자다")
for i, l in enumerate(_lines_in):
    ok(f"{i + 1}. [짧다] {l}" in _pp, f"{i + 1}번 문장이 문제와 함께 실린다")
ok("뜻과 사건은 그대로" in _pp, "뜻을 바꾸지 말라고 못박는다")
ok("전부 고쳐라" in _pp, "한 번에 전부 고치라고 한다")

_t = "가. 짧다. 나."
ok(flow.apply_patch(_t, ["짧다."], {"1": "길게 늘여 쓴 문장이다, 정말로."})[1] == 1,
   "고쳐 온 문장이 끼워진다")
ok(flow.apply_patch(_t, ["짧다."], {"1": "짧"})[1] == 0,
   "짧아져서 오면 안 넣는다  ← 분량으로 지표를 맞추는 길")
ok(flow.apply_patch(_t, ["짧다."], {"9": "아무거나"})[1] == 0,
   "없는 번호는 무시한다")
ok(flow.apply_patch("같다. 같다.", ["같다."], {"1": "아주 길게 고쳐 온 문장이다."})[1] == 0,
   "여러 군데 있는 문장은 손대지 않는다  ← 어느 것인지 알 수 없다")

print("[분량] 한 번에 받을 만큼 받는가")
ok(flow.CHUNK >= 3000, f"한 덩어리 {flow.CHUNK}자  ← 1,400자는 한 번 출력 한도의 1/8이었다")

print("[구조] 모순도 버리기 전에 그 문장만 고쳐 보는가  ← 폐기는 마지막이다")
_cl = ["요우의 나이: 앞에서는 '42' 였는데 지금 '30' 다"]
_hit = flow.clash_lines("요우는 서른이다. 항구는 조용했다. 요우가 웃었다.", _cl)
ok(_hit and all("요우" in h for h in _hit),
   f"어긋난 이름이 든 문장만 고른다 ({_hit})")
ok("항구는 조용했다." not in _hit, "상관없는 문장은 안 보낸다")
_cp = flow.clash_prompt(_cl, _hit)
ok(_cl[0] in _cp and "앞에서 확정된 쪽이 맞다" in _cp, "무엇이 어긋났는지 알려준다")
ok(len(_cp) < 900, f"모순 손질 프롬프트가 {len(_cp)}자  ← 원고를 다시 쓰면 18,000자다")


class Refuse:
    """모순을 계속 뱉지만, 문장만 고쳐 달라면 고쳐 주는 배우."""

    def __init__(self):
        self.mended = False

    def __call__(self, prompt):
        if "앞에서 확정된 쪽이 맞다" in prompt:
            self.mended = True
            return json.dumps({"1": "요우는 마흔둘이고 오늘도 늦게 왔다, 늘 그렇듯."},
                              ensure_ascii=False)
        if "새로 확정된 사실만" in prompt:
            if self.mended:
                return json.dumps({"people": {"요우": {"나이": "42"}}}, ensure_ascii=False)
            return json.dumps({"people": {"요우": {"나이": "30"}}}, ensure_ascii=False)
        return "요우는 서른이다.\n" + "항구는 조용하고 사람들은 천천히 걸었다, 늘 그렇듯. " * 12


_bk4 = main_char()
_r4 = flow.step(_bk4, Refuse())
ok(_r4["status"] == "ok", f"버리지 않고 살린다 ({_r4['status']})")
ok(_bk4["chunks"], "원고에 들어간다  ← 3,200자를 통째로 버리던 자리다")


print()
print("[분량] **짧게 온 덩어리는 한 번 이어 받는다**")
print("      ← 실측 2026-09-07, 10만 자 원고 58덩어리: 3,200자를 시켰는데 평균 1,734자가")
print("        왔다. 목표를 넘긴 것은 4개뿐, 하위 10%는 309자. 그런데 짧게 온 덩어리도")
print("        집필·추출·손질 3호출을 똑같이 문다 -- 300자 받자고 3호출이다.")
flow.CHUNK_MIN = 0.6          # 진짜 기본값으로 잰다


class _Short:
    """첫 집필은 짧게, 이어받기는 길게. 추출·손질은 빈 것을 준다."""

    def __init__(self, first, second):
        self.first, self.second, self.writes = first, second, 0

    def __call__(self, prompt):
        if "JSON 만 출력" in prompt and "새로 확정된 사실만" in prompt:
            return json.dumps({}, ensure_ascii=False)
        # **손질 프롬프트의 표지는 이 문장이다.** "고쳐" 같은 흔한 말로 가르면
        # 집필 프롬프트까지 걸려서 원고 자리에 "{}" 가 돌아온다(그렇게 짰다가
        # "덩어리가 2자로 왔다" 를 봤다). 위의 되먹임 검사가 쓰는 표지와 같은 것을 쓴다.
        if "각 문장 앞 대괄호가 그 문장의" in prompt:
            return json.dumps({}, ensure_ascii=False)
        self.writes += 1
        return self.first if self.writes == 1 else self.second


# **되풀이하면 안 된다.** 같은 문장을 곱해 쓰면 echo.trim 이 도려내서, 길게 만든 것이
# 짧게 도착한다(그렇게 짰다가 "1,679자로 왔다" 를 봤다). clean() 처럼 줄마다 다르게 쓴다.
def _long(n: int) -> str:
    return "".join(
        f"{i}월의 등대는 오후 네 시부터 어두워졌고, 불빛이 {i}초마다 한 바퀴를 돌았다. "
        if i % 3 else
        f"아니, 돈다기보다는 {i}월이 통째로 실려 와 창을 훑고 지나가는 것에 가까웠다. "
        for i in range(1, n))


_A = _long(9)            # 짧다 -- 기본값(CHUNK*0.6 = 1,920자)에 못 미친다
_B = _long(45)           # 넉넉하다

_bk = main_char()
_s = _Short(_A, _B)
_r = flow.step(_bk, _s)
ok(_s.writes == 2, f"짧으면 한 번 더 부른다 ({_s.writes}회)")
ok(_r.get("chars", 0) > len(_A), f"이어받은 만큼 늘었다 ({_r.get('chars', 0):,}자)")

# **한 번만이다.** 되풀이하면 계속 짧게 주는 모델에게 쿼터를 통째로 태운다.
_bk2 = main_char()
_s2 = _Short(_A, _A)                      # 이어받기도 짧게 온다
flow.step(_bk2, _s2)
ok(_s2.writes == 2, f"이어받기는 한 번뿐이다 ({_s2.writes}회)  ← 되풀이하면 쿼터를 태운다")

# 길게 온 덩어리에는 값이 안 붙는다.
_bk3 = main_char()
_s3 = _Short(_B, _B)
flow.step(_bk3, _s3)
ok(_s3.writes == 1, f"넉넉히 오면 안 부른다 ({_s3.writes}회)")


# **요약은 맨 끝에 있어야 한다.** 2026-09-07 까지 이 블록이 402줄에 있었다 -- 파일은
# 605줄인데. 검사가 자라면서 자기 요약문을 넘어갔고, 그 뒤 200줄은 종료 코드에
# 아무 영향을 못 줬다. test_llm_pool_rpm.py 에서 같은 것을 찾아 고쳤는데 여기도
# 그랬다. **검사하지 않은 초록불은 검사한 빨간불보다 나쁘다.**

print()
print("[문체] **고른 페르소나가 실제로 닿는가**")
print("      ← 2026-09-07 까지 flow 는 style.use() 를 한 번도 안 불렀다. 표본에서 잰")
print("        로판 페르소나를 만들어 두고도 DRIFT 에서 닿지 않았다 -- searcher.py ·")
print("        bot_tools.py · gatekeeper.py · 배포 경로 · gemini_http 임포트에 이어")
print("        여섯 번째 '코드가 실행에 도달하지 못하는' 자리다.")

import subprocess as _sp                                              # noqa: E402
import tempfile as _tmp                                               # noqa: E402

_REPO = Path(__file__).resolve().parent.parent

_d = Path(_tmp.mkdtemp()) / "b.json"
_bk = flow.blank("첫 문장이다.")
_bk["chunks"] = ["가" * 500]                       # 목표를 이미 넘겨 호출 없이 끝난다
_d.write_text(json.dumps(_bk, ensure_ascii=False), encoding="utf-8")


def _run_persona(name):
    r = _sp.run([sys.executable, str(_REPO / "novel" / "flow.py"), "--resume", str(_d),
                 "--chars", "10", "--first", "첫 문장이다.", "--persona", name],
                capture_output=True, text=True, cwd=str(_REPO))
    return r.returncode, r.stdout + r.stderr


_rc, _out = _run_persona("ropan")
ok(_rc == 0, f"로판으로 돌아간다 (exit={_rc})")
ok("문체 ropan" in _out, "고른 문체가 로그에 찍힌다  ← 안 찍히면 뭘로 썼는지 모른다")

# **모르는 이름은 사실대로 죽어야 한다.** 조용히 기본값으로 물러서면, 로판을 시켰는데
# cider 로 8만 자를 쓰고도 아무도 모른다.
_rc2, _out2 = _run_persona("없는이름")
ok(_rc2 != 0, f"모르는 이름은 죽는다 (exit={_rc2})")
ok("모르는 페르소나" in _out2, "왜 죽었는지 말한다")

# 안 주면 건드리지 않는다 -- 기존 런의 기본값이 조용히 바뀌면 안 된다.
_was = flow.style.ACTIVE
ok(_was == "cider", f"기본값은 그대로다 ({_was})")

# drift.sh 가 **두 자리 모두** 넘겨야 한다. start 에만 넣으면 이어 쓸 때 문체가 사라진다.
_sh = (_REPO / "scripts" / "drift.sh").read_text(encoding="utf-8")
ok(_sh.count('${STYLE:+--persona "$STYLE"}') == 2,
   f"drift.sh 의 start 와 go 둘 다 넘긴다 ({_sh.count('--persona')}자리)")

print()
print("[지저분] **진짜 모델처럼 답해도 원장이 차는가**")
print("      ← 2026-09-07: 이 파일의 가짜 추출기가 **한 덩이로만** 답했다. 진짜 gemma 는")
print("        객체를 쪼개서 낸다. 그래서 추출이 한 번도 성공 못 하는 채로 원고가")
print("        0자였는데, 검사는 내내 초록이었다. **가짜가 얌전하면 검사는 얌전한")
print("        세상만 확인한다.**")

sys.path.insert(0, str(_REPO / "tests"))
import messy                                                          # noqa: E402

_DELTA = {"people": {"한나": {"직업": "등대지기"}},
          "places": {"북쪽 곶": "등대가 선 자리"},
          "objects": {"무전기": "오래된 것"}}


class _Messy:
    """추출기만 지저분하게 답한다. 집필과 손질은 평소대로."""

    def __init__(self, shape):
        self.shape = shape

    def __call__(self, prompt):
        if "JSON 만 출력" in prompt and "새로 확정된 사실만" in prompt:
            return self.shape(json.dumps(_DELTA, ensure_ascii=False))
        if "각 문장 앞 대괄호가 그 문장의" in prompt:
            return json.dumps({}, ensure_ascii=False)
        return _long(45)


for _name, _fn, _why in messy.SHAPES:
    _bk = main_char()
    flow.step(_bk, _Messy(_fn))
    _people = (_bk.get("ledger") or {}).get("people") or {}
    ok("한나" in _people, f"{_name:14} 로 와도 원장이 찬다  ({_why[:40]})")

# **죽는 것이 맞는 꼴은 원고를 안 죽인다.** 추출이 실패해도 flow 는 "원장 갱신 없이
# 간다" 로 계속 가야 한다 -- 그것까지 막히면 모델의 오타 하나가 런을 끝낸다.
for _name, _fn, _why in messy.BROKEN:
    _bk2 = main_char()
    _r2 = flow.step(_bk2, _Messy(_fn))
    ok(_r2["status"] == "ok" and _r2["chars"] > 200,
       f"{_name:14} 는 파서가 죽되 원고는 산다 ({_r2['status']}, {_r2['chars']:,}자)")


print()
print("[규격 밖] **쪼개진 속 사전이 최상위로 올라와도 원장을 더럽히지 않는다**")
print("      ← 실측 2026-09-07 VM: 합친 키가 ['Name-Name', '백작-엘리나', 'bonds', ...]")

_raw = {"people": {"한나": {"직업": "등대지기"}, "사람 이름": {"나이": "숫자"}},
        "Name-Name": "자리 이름을 베낀 것",
        "백작-엘리나": "서로 경계한다",
        "bonds": "문자열이 온 칸",
        "closed": ["앞에서 열려 있다가 이번에 답이 나온 것", "등대의 불"],
        "엉뚱한칸": {"a": 1}}
_cd = flow.clean_delta(_raw)
ok("Name-Name" not in _cd and "엉뚱한칸" not in _cd, "모르는 키는 안 들어간다")
ok((_cd.get("bonds") or {}).get("백작-엘리나") == "서로 경계한다",
   "흘러나온 관계는 bonds 로 돌아간다")
ok("사람 이름" not in _cd["people"] and "한나" in _cd["people"], "자리 이름을 베낀 항목은 버린다")
ok(_cd.get("closed") == ["등대의 불"], f"목록에서도 자리 이름을 버린다 ({_cd.get('closed')})")
ok(flow.clean_delta("문자열") == {} and flow.clean_delta(None) == {}, "사전이 아니면 빈 것")

# 그 규격 밖이 _merge 까지 갔으면 `.items()` 에서 죽었다 -- 죽지 않는다.
_bk3 = main_char()
_r3 = flow.step(_bk3, _Messy(lambda s: json.dumps(_raw, ensure_ascii=False)))
ok(_r3["status"] == "ok" and _r3["chars"] > 200 and "한나" in _bk3["ledger"]["people"],
   f"규격 밖이 섞여 와도 덩어리를 채택하고 원장도 찬다 ({_r3['status']})")
ok("Name-Name" not in _bk3["ledger"] and "백작-엘리나" not in _bk3["ledger"],
   "원장 최상위에 잡키가 없다")


print()
print("[장부 사고] **원고를 받은 뒤의 일이 터져도 원고는 쓴다**")
print("      ← 장부는 다음 덩어리에서 다시 채워지지만 원고는 다시 안 온다.")


class _Boom:
    def __call__(self, prompt):
        if "JSON 만 출력" in prompt and "새로 확정된 사실만" in prompt:
            raise RuntimeError("추출기가 통째로 터졌다")
        return _long(45)


_bk4 = main_char()
_n4 = len(_bk4["chunks"])
_r4 = flow.step(_bk4, _Boom())
ok(_r4["status"] == "ok" and len(_bk4["chunks"]) == _n4 + 1,
   f"추출기가 예외를 던져도 덩어리는 붙는다 ({_r4['status']}, {_r4.get('why', '')})")


# **요약은 맨 끝에 있어야 한다.** 종료 블록 뒤에 붙인 검사는 실패해도 종료 코드를
# 0 으로 남긴다 -- 스위트는 초록으로 보고, 화면의 '실패' 줄은 스크롤 위로 흘러간다.
# 2026-09-07 에 이 저장소에서 일곱 번 나왔다. 그래서 G015 가 이제 커밋에서 막는다.

print()
if fails:
    print(f"연속 집필: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("연속 집필: 원장 성장 · 모순 검출 · 첫 덩어리 흐름 · 되먹임 · 영속 · 한도 -- 통과")
