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


print("[원장] 세계가 자라는가")
led = flow.blank()["ledger"]
ok(not flow._merge(led, {"people": {"요우": "양조장 주인"}}), "빈 자리를 채우는 것은 모순이 아니다")
ok(led["people"]["요우"] == "양조장 주인", "원장에 남는다")
ok(not flow._merge(led, {"people": {"요우": "양조장 주인"}}), "같은 값을 다시 써도 통과")
ok(not flow._merge(led, {"places": {"양조장": "레이캬비크 외곽"}}), "다른 칸도 채워진다")

print("[원장] 어긋나는 것만 잡는가  ← 못 가리면 두 번째 덩어리부터 전부 기각된다")
clash = flow._merge(led, {"people": {"요우": "우체국 직원"}})
ok(clash, f"같은 키에 다른 값이면 잡는다 ({clash})")
ok("앞에서는" in clash[0] and "양조장 주인" in clash[0], "무엇과 어긋나는지 말해준다")
ok(led["people"]["요우"] == "양조장 주인", "기각된 값은 원장에 안 들어간다")
ok(not flow._merge(led, {"people": {"시그": "이웃"}}), "새 인물은 그대로 통과")
ok(not flow._merge(led, {"time": ["크리스마스 이브"]}) and led["time"], "시간은 쌓인다")

print("[원장] 쓰레기 값은 무시하는가")
before = dict(led["facts"])
flow._merge(led, {"facts": {"x": "", "y": None, "z": {"안": "됨"}}})
ok(led["facts"] == before, "빈 값·None·객체는 안 넣는다  ← 추출기가 그런 것을 보낸다")

print()
print("[프롬프트] 첫 덩어리에 첫 문장과 흐름이 실리는가")
book = flow.blank()
p0 = flow.write_prompt(book)
ok(flow.FIRST[:20] in p0, "첫 문장이 실린다")
ok("양조장의 내력" in p0 and "오로라" in p0, "지나갈 자리를 준다  ← 줄거리가 아니라 방향이다")
book2 = flow.blank()
book2["chunks"] = ["이어지는 산문. " * 200]
p1 = flow.write_prompt(book2)
ok("오로라" not in p1, "이어쓰기에는 첫 덩어리 지시가 안 실린다")
ok("지금까지의 끝부분" in p1, "꼬리를 넘긴다")
ok(len(p1) < len(p0) + 2000, "프롬프트가 무한정 커지지 않는다  ← 꼬리는 잘라서 넘긴다")

print("[프롬프트] 문체와 규율이 실리는가")
for key, label in (("가볍고 재미있게", "가벼운 온도"),
                   ("거칠고 현실적으로", "거친 대사"),
                   ("점층", "점층"),
                   ("장문과 단문을 섞어라", "장단문 섞기"),
                   ("미리 정하지 마라", "줄거리를 미리 안 짠다"),
                   ("사정을 하나 더", "연쇄 확장"),
                   ("두 번 울리는 종", "편의주의 금지"),
                   ("대가를 치르고 얻는다", "정보에 값을 매긴다"),
                   ("실패한 채로 둬라", "실패를 되돌리지 않는다")):
    ok(key in p0, label)
ok("회차도 씬도 없다" in p0, "조립하지 않는다고 못박는다")

print()
print("[루프] 모순이면 기각하고 다시 쓰는가")


class Fake:
    """첫 시도는 원장과 어긋나게, 두 번째는 맞게 쓴다."""

    def __init__(self):
        self.tries, self.prompts = 0, []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        if "JSON 만 출력" in prompt and "새로 확정된 사실만" in prompt:
            wrong = self.tries == 1
            return json.dumps({"people": {"요우": "우체국 직원" if wrong else "양조장 주인"}},
                              ensure_ascii=False)
        self.tries += 1
        return "산문 덩어리. " * 120


bk = flow.blank()
bk["ledger"]["people"]["요우"] = "양조장 주인"
f = Fake()
r = flow.step(bk, f)
ok(r["status"] == "ok", f"두 번째 시도에서 채택 ({r['status']})")
ok(f.tries == 2, f"한 번 기각하고 다시 썼다 ({f.tries}회)")
retry = [q for q in f.prompts if "직전 시도가 기각된 이유" in q]
ok(retry, "기각 사유가 다음 프롬프트에 실린다")
ok(any("우체국" in q for q in retry), "무엇이 어긋났는지까지")
ok(any("나머지는 자유다" in q for q in retry), "그것만 고치라고 한다  ← 자유를 죽이지 않는다")
ok(len(bk["chunks"]) == 1, "채택된 덩어리만 남는다")

print("[루프] 목표 자수까지 이어 쓰는가 · 파일로 남는가")
d = Path(tempfile.mkdtemp()) / "flow.json"


class Clean:
    def __call__(self, prompt):
        if "새로 확정된 사실만" in prompt:
            return "{}"
        return "이어지는 산문. " * 130


bk2 = flow.blank()
res = flow.run(bk2, Clean(), 3000, str(d))
ok(res["chars"] >= 3000, f"{res['chars']:,}자까지 쓴다 ({res['chunks']}덩어리)")
ok(d.exists(), "덩어리마다 저장한다")
saved = json.loads(d.read_text(encoding="utf-8"))
ok(len(saved["chunks"]) == res["chunks"], "저장된 것과 메모리가 같다")
ok(flow.text_of(saved).count("이어지는") > 10, "이어 붙여 읽힌다")

print("[루프] 못 풀면 멈추는가  ← 같은 모순을 무한히 반복하지 않는다")


class Stubborn:
    def __call__(self, prompt):
        if "새로 확정된 사실만" in prompt:
            return json.dumps({"people": {"요우": "우체국 직원"}}, ensure_ascii=False)
        return "산문. " * 120


bk3 = flow.blank()
bk3["ledger"]["people"]["요우"] = "양조장 주인"
r3 = flow.step(bk3, Stubborn())
ok(r3["status"] == "blocked", f"기각으로 끝난다 ({r3['status']})")
ok(not bk3["chunks"], "원고에 안 들어간다")

print()
if fails:
    print(f"연속 집필: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("연속 집필: 원장 성장 · 모순 검출 · 첫 덩어리 흐름 · 되먹임 · 영속 · 한도 -- 통과")
