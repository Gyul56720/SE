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
ok(len(p1) < len(p0) + 2000, "프롬프트가 무한정 커지지 않는다  ← 꼬리는 잘라서 넘긴다")

print("[프롬프트] 문체와 규율이 실리는가")
for key, label in (("가볍고 재미있게", "가벼운 온도"),
                   ("**인물에 맞게.**", "대사는 인물에 맞게"),
                   ("그 자리에서 사람을 만들어라", "새 인물이 나오면 사람을 만든다"),
                   ("점층", "점층"),
                   ("길이를 섞어라", "장단문 섞기"),
                   ("미리 정하지 마라", "줄거리를 미리 안 짠다"),
                   ("사정을 하나 더", "연쇄 확장"),
                   ("두 번 울리는 종", "편의주의 금지"),
                   ("대가를 치르고 얻는다", "정보에 값을 매긴다"),
                   ("실패한 채로 둬라", "실패를 되돌리지 않는다")):
    ok(key in p0, label)
ok("회차도 씬도 없다" in p0, "조립하지 않는다고 못박는다")

print()
print("[루프] 모순이면 기각하고 다시 쓰는가")


# 리듬 자에도 메아리 자에도 걸리지 않는 본문. **시도마다 달라야 한다** -- 매번 같은 글을
# 돌려주면 꼬리 절단(echo.trim)이 통째로 잘라내고, 그러면 여기서 세는 횟수가 어긋난다.
# 그것도 자가 제대로 도는 것이지 픽스처가 옳은 것이 아니다. 이 시험이 보는 것은 모순이라,
# 다른 자에 걸리지 않는 글을 넣어야 한다.
def clean(tag: int) -> str:
    return "\n".join(
        [f"{tag}년 {i}월의 항구는 오후 세 시부터 어두워졌고, 바람에는 생선과 디젤과 "
         f"눈 냄새가 한꺼번에 섞여 있었다." for i in range(1, 13)]
        + [f'"{w} 드실래요?"' for w in ("커피", "차", "물", "맥주")]
        + [f'"아뇨, 괜찮습니다. 방금 마셨거든요. 아니, 마신 것 같기도 하고 아닌 것 '
           f'같기도 하고, {tag}년쯤부터는 그게 잘 구분이 안 갑니다."']
        # 이름을 여덟 번 부르면 diffusion.overused 가 잡는다 -- 회수는 다시 부르는 것이
        # 아니라 다시 쓰는 것이라서다. 두 번째부터는 대명사로 받는다.
        + [f"{'요우는' if i == 1 else '그는'} 창가 {tag}-{i}번 자리에 앉아, 유리에 서린 "
           f"김 너머로 밖이라기보다는 밖의 소문 같은 것을 오래 바라보았다."
           for i in range(1, 9)])


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
            return json.dumps({"people": {"요우": {"나이": "30" if wrong else "42"},
                                          "한나": {"직업": "등대지기"}},
                               "places": {"등대": "북쪽 곶"},
                               "objects": {"무전기": "1978년 것"}},
                              ensure_ascii=False)
        self.tries += 1
        return clean(self.tries)


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
print("[영속] **시작하자마자 한 번 저장한다**")
print("      ← 첫 덩어리를 다 받고서야 파일이 생기면, 아직 쓰는 중인지 시작도 못 한 건지")
print("        밖에서 구분할 수가 없다(실측: --read 가 FileNotFoundError 로 죽었다).")


class Dead:
    def __call__(self, prompt):
        raise RuntimeError("모델 호출 실패")


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

retry = [q for q in f.prompts if "직전 시도가 기각된 이유" in q]
ok(retry, "기각 사유가 다음 프롬프트에 실린다")
ok(any("나이" in q for q in retry), "무엇이 어긋났는지까지")
ok(any("나머지는 자유다" in q for q in retry), "그것만 고치라고 한다  ← 자유를 죽이지 않는다")
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
ok(r3["status"] == "blocked", f"기각으로 끝난다 ({r3['status']})")
ok(not bk3["chunks"], "원고에 안 들어간다")

print("[추출] 카드 칸을 뽑으라고 지시하는가")
e = flow.extract_prompt("아무 산문")
for f in ("나이", "키", "성격", "가족", "과거", "트라우마", "취미", "전공", "직업",
          "말투", "버릇"):
    ok(f in e, f"{f} 칸")
ok("안 나온 칸은 빼라" in e and "지어내지 마라" in e,
   "안 나온 칸은 비운다  ← 추출기가 지어내면 그것이 원장의 거짓이 된다")
ok("끝을 흐린다" in e, "말투를 어떻게 적는지 예시로 준다")

print()
if fails:
    print(f"연속 집필: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("연속 집필: 원장 성장 · 모순 검출 · 첫 덩어리 흐름 · 되먹임 · 영속 · 한도 -- 통과")
