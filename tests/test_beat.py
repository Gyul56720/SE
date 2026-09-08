"""회차 각본 -- **덩어리 위의 층이 실제로 서고 · 실리고 · 사건을 대신하는가.**

LLM 은 가짜다. 여기서 보는 것은 재미가 아니라 배선이다: 회차당 호출 한 번인가, 카드가
비트로 실리는가, 회차 안의 자리로 비트가 넘어가는가, 갈고리와 전환점이 실리는가,
카드가 있으면 무작위 사건을 안 뽑는가, 도착지가 없으면 카드도 없는가, 각본이 깨져
와도 원고는 사는가.

실행: python3 tests/test_beat.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel import beat as BT                                          # noqa: E402
from novel import serial as SR                                        # noqa: E402
from novel import flow                                                # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


ARC = {"end": "그 계약이 더는 두 사람을 묶지 못한다", "start": "공녀는 제 이름으로 초대장 한 장 못 보낸다",
       "debts": [{"무엇": f"빚{i}", "갚음": 0} for i in range(5)], "made": "ropan"}

CARD = {"질문": "공녀가 무도회 초대장을 제 손으로 받아낸다",
        "방해": "백작 부인이 명부에서 이름을 지운다",
        "비트": [{"무엇": "공녀가 집사에게 명부를 보여 달라고 한다", "꼴": "장면"},
                {"무엇": "사흘 동안 답장이 없다", "꼴": "요약"},
                {"무엇": "무도회 전날 밤 초대장이 남의 이름으로 온다", "꼴": "장면"}],
        "답": "반만",
        # 쾌감은 회차마다 하나다 -- 없으면 되묻는다(호출 +1). 배선 검사가 호출 수를 세므로 넣어 둔다.
        "쾌감": "집사가 명부를 공녀 앞에 펼쳐 놓고 한 걸음 물러선다", "쾌감자리": 2,
        "갈고리종류": "피",
        "갈고리": "로일의 왼팔이 서재 문틀에 끼여 팔꿈치 아래가 잘려 나간다"}


def book(chars=0, arc=True, target=50_000):
    b = flow.blank("첫 문장이다.")
    b["seed_id"] = "씨"
    if chars:
        b["chunks"] = ["가" * chars]
    if arc:
        b["arc"] = json.loads(json.dumps(ARC))
        b["_target"] = target
    b["ledger"]["people"]["공녀"] = {"나이": "19", "직업": "공작가의 딸", "말투": "짧다", "_seen": 3}
    return b


class Director:
    """각본 자리에서 카드를 돌려준다. 부른 횟수를 센다. 나머지는 긴 산문."""

    def __init__(self, payload=None, broken=False, queue=None):
        self.calls, self.prompts, self.n = 0, [], 0
        self.payload, self.broken = payload if payload is not None else CARD, broken
        self.queue = list(queue or [])          # 차례로 낼 각본 -- 되묻기를 검사할 때

    def __call__(self, prompt):
        self.prompts.append(prompt)
        if "회차**의 각본" in prompt:
            self.calls += 1
            if self.queue:
                return json.dumps(self.queue.pop(0), ensure_ascii=False)
            return "그냥 산문이다." if self.broken else json.dumps(self.payload, ensure_ascii=False)
        if "JSON 만 출력" in prompt:
            return "{}"
        self.n += 1                        # 매번 다른 산문 -- 같은 글이면 echo.trim 이 도려낸다
        return _long(45, start=self.n * 50)


def _long(n, start=1):
    return "".join(f"{i}월의 회랑은 오후 네 시부터 어두워졌고, 촛대가 {i}개씩 꺼졌다. "
                   if i % 3 else f"아니, 꺼진다기보다 {i}월이 통째로 실려 와 창을 훑는 것에 가까웠다. "
                   for i in range(start, start + n))


print("[세우기] **회차당 호출 한 번 -- 같은 회차면 안 다시 세운다**")
_b, _d = book(100), Director()
BT.ensure(_b, _d)
ok(_d.calls == 1 and BT.has(_b), f"첫 부름에 카드가 선다 ({_d.calls}회)")
ok(_b["card"]["질문"] == CARD["질문"] and len(_b["card"]["비트"]) == 3, "질문과 비트 셋이 실린다")
BT.ensure(_b, _d)
ok(_d.calls == 1, f"같은 회차에서 다시 부르지 않는다 ({_d.calls}회)")
_b["chunks"].append("나" * BT.EP)
BT.ensure(_b, _d)
ok(_d.calls == 2, f"회차가 바뀌면 한 번 더 ({_d.calls}회)")
ok("로일의 왼팔이" in _d.prompts[-1], "앞 회차의 갈고리가 다음 각본의 입력이다  ← 인과가 구조로 들어간다")
ok("공녀" in _d.prompts[-1] and "닿을 자리" in _d.prompts[-1], "세계와 도착지가 각본의 입력이다")

print()
print("[깨짐] **각본이 깨져 와도 원고는 산다**")
_b2, _d2 = book(100), Director(broken=True)
ok(BT.ensure(_b2, _d2) is None and not BT.has(_b2), "산문이 오면 카드 없이 간다")
ok(BT.brief(_b2) == "", "카드가 없으면 프롬프트도 조용하다")
_b3 = book(100)
ok(BT.ensure(_b3, Director({"질문": "", "비트": []})) is None, "빈 각본은 카드가 아니다")
_b4 = book(100)
BT.ensure(_b4, Director({"질문": "q", "비트": ["문자열 비트", {"무엇": "x", "꼴": "엉뚱"}],
                         "갈고리종류": "절단", "갈고리": "로일의 팔이 잘린다"}))
ok([b["꼴"] for b in _b4["card"]["비트"]] == ["장면", "장면"], "문자열 비트와 모르는 꼴은 장면으로 받는다")

print()
print("[비트] **덩어리가 비트 범위를 덮고, 회차의 마지막 덩어리는 답까지 간다**")
print("      ← 실측 2026-09-08: 덩어리 3,200자 · 회차 5,000자라 회차당 덩어리가 1.56개인데")
print("        비트는 셋이었다. 비트 3(답이 갈리고 갈고리가 터지는 자리)이 **한 번도**")
print("        안 쓰였다. 사용자 평: \"전개가 없다. 한 씬의 반복이다.\"")
_b5 = book(100); BT.ensure(_b5, Director())
ok(BT.beat_span(_b5)[0] == 1, f"회차 첫머리는 비트 1부터 ({BT.beat_span(_b5)})")
_ch = flow.CHUNK
_b5["chunks"].append("다" * _ch)
_lo, _hi = BT.beat_span(_b5)
ok(_lo > 1, f"덩어리를 하나 쓰면 다음 비트로 넘어간다 ({_lo}~{_hi})")
ok(_hi == 3 and BT.last_chunk(_b5), f"회차가 닫히는 덩어리는 마지막 비트까지 간다 ({_lo}~{_hi})")
_p = BT.brief(_b5)
ok(f"{_lo}번 비트부터" in _p and f"→ {_hi}." in _p, "몇 번 비트부터 몇 번까지인지 표시한다")
ok("이번 대목이 이 회차의 끝이다" in _p and "다음 대목으로 미루지 마라" in _p,
   "회차를 닫는 덩어리라고 말해 준다")

# **모든 회차가 답까지 간다.** 이것이 이 고침의 계약이다.
_sim = book(0); BT.ensure(_sim, Director())
_seen, _total = {}, 0
for _i in range(14):
    _ep = _total // BT.EP
    _l, _h = BT.beat_span(_sim)
    _seen.setdefault(_ep, set()).update(range(_l, _h + 1))
    _sim["chunks"].append("가" * _ch); _total += _ch
    if _total // BT.EP != _ep:
        _sim["card"] = dict(_sim["card"], ep=_total // BT.EP, at=_total)
_unfinished = max(_seen)                       # 마지막 회차는 아직 안 끝났다
_missed = [e + 1 for e, s in _seen.items() if e != _unfinished and 3 not in s]
ok(not _missed, f"끝난 회차는 전부 비트 3 까지 간다 (못 간 회차: {_missed or '없다'})")
ok(all(1 in s for e, s in _seen.items() if e != _unfinished), "첫 비트도 빠지지 않는다")
ok("(요약)" in _p and "(장면)" in _p, "장면 · 요약 꼴이 실린다")
ok("시간을 접는다" in _p, "요약 비트는 시간을 접으라고 한다  ← TTCW 의 시간 조작")
ok(CARD["갈고리"] in _p and "벌어진 문장" in _p and "**피**" in _p,
   "갈고리가 벌어진 문장에서 끊으라고 한다 -- 종류까지")
ok("묻고 끝내지 마라" in _p, "묻고 끝내지 말라고 한다")

print()
print("[갈고리] **사건이다 -- 질문 · 대사 · 목록 밖은 되묻고, 그래도 아니면 카드를 버린다**")
print("      ← 사용자(2026-09-08): \"질문 이딴 게 재미없다고. 누가 죽든가 팔이 잘리든가")
print("        키스를 하든가 관계를 맺든가. 자극적이게 끝내라고.\"")
ok(BT.hook_ok("피", "로일의 팔이 잘려 나간다") == "", "몸에 벌어진 일은 통과")
ok("질문" in BT.hook_ok("피", "이 모든 일이 숙부님이 계획한 대로 끝날 것이라고 믿는 겁니까?"),
   "첫 런의 그 갈고리는 질문이라 안 된다")
ok("질문" in BT.hook_ok("폭로", "그가 정말 돌아올까"), "물음표 없는 물음도 잡는다")
ok("대사" in BT.hook_ok("배신", "\"나는 네 편이 아니다.\""), "대사는 안 된다")
ok(BT.hook_ok("더 큰 것", "끝난 줄 알았던 골짜기에서 더 큰 것이 내려와 마르코를 통째로 삼킨다") == "",
   "목록 밖 종류라도 꼴이 사건이면 통과  ← 닫힌 목록이 아니다")
ok("조용히" in BT.hook_ok("미소", "소르미는 그 뒷모습을 보며 희미하게 미소 지었다"), "미소로 끝나면 안 된다")
ok("예고" in BT.hook_ok("불", "곧 서재에 불이 붙을 것이었다"), "벌어지려는 문장은 안 된다")
ok("비었다" in BT.hook_ok("", "팔이 잘린다"), "종류가 비면 안 된다")
from novel import hooks as HK                                         # noqa: E402
ok(len(HK.KINDS) >= 25, f"본보기가 많다 ({len(HK.KINDS)}개)  ← 표본 18 + 사용자 요구")
ok(sum(1 for _, _, src in HK.KINDS if src.startswith("표본")) >= 15, "표본에서 온 것이 15개 넘는다")
ok(sum(1 for _, _, src in HK.KINDS if src.startswith("일본")) >= 10, "일본 연재물 문법에서 온 것이 10개 넘는다 (HIKI.md)")
ok(sum(1 for _, _, src in HK.KINDS if src.startswith("류")) >= 6, "코인로커 베이비스에서 온 것이 6개 넘는다 (RYU.md)")
ok("판을 넓혀라" in BT.card_prompt(book(100)), "무대와 판돈이 앞 회차보다 커야 한다고 말한다  ← 류의 계단")
ok("첫 회차다" in BT.card_prompt(book(100)) and "첫 회차다" not in BT.card_prompt(book(BT.EP + 100)),
   "첫 회차에만 주인공의 목적을 요구한다  ← 점프의 1화 규칙")
_s0, _s1 = HK.sample("씨", 0), HK.sample("씨", 1)
ok(len(_s0) == 5 and _s0 != _s1 and HK.sample("씨", 0) == _s0, "회차마다 다섯 개씩 돌아가고, 같은 원고는 같다")
ok(any(k in BT.card_prompt(book(100)) for k, _, _ in _s0), "각본 프롬프트에 본보기가 실린다")
ok("지어내도 된다" in BT.card_prompt(book(100)), "목록 밖을 지어내도 된다고 말한다")
_q = dict(CARD, 갈고리종류="피", 갈고리="정말 그가 숙부의 사람이었을까?")
_bq, _dq = book(100), Director(queue=[_q, CARD])
BT.ensure(_bq, _dq)
ok(_dq.calls == 2 and BT.has(_bq) and _bq["card"]["갈고리"] == CARD["갈고리"],
   f"질문이면 한 번 되묻고, 고쳐 오면 받는다 ({_dq.calls}회)")
ok("갈고리가 틀렸다" in _dq.prompts[-1], "되물을 때 무엇이 틀렸는지 말한다")
_bq2, _dq2 = book(100), Director(queue=[_q, _q])
ok(BT.ensure(_bq2, _dq2) is None and _dq2.calls == 2, "두 번 다 질문이면 카드를 버린다")
ok("질문 · 예감 · 대사 · 미소가 아니다" in BT.card_prompt(book(100)), "각본 프롬프트가 금지를 준다")
ok("반만" in _p and "답이 갈린다" in _p, "답이 갈리는 자리를 표시한다")
# **자를 시키지 않는다**(serial.py 의 계약). 다만 낱말로 맞추면 평범한 산문을 잡는다 --
# "한 마디로 김을 뺀다" 의 마디, "두 번째 것이 온다" 의 번째가 그것이다. 그래서 낱말이
# 아니라 **자의 꼴**을 본다: 수가 붙은 마디 · 회차 · 진도 · 분량.
import re as _re_ruler                                                # noqa: E402
for _pat in (r"\d+\s*번째\s*(마디|회차)", r"(마디|회차)\s*\d+", r"\d+\s*%",
             r"\d{1,3},\d{3}\s*자"):
    _hit = _re_ruler.search(_pat, _p)
    ok(not _hit, f"자가 안 실린다: /{_pat}/ ({_hit.group(0) if _hit else '없다'})")

print()
print("[전환점] **마디의 마지막 회차에만 온다 -- 다섯 중 하나**")
_span = SR.span(book(0))                      # 50,000 / 6
ok(BT.turning_point(book(100)) == "", "마디 첫머리에는 없다")
ok(BT.turning_point(book(_span - 100)) == "기회", "첫 마디 끝은 기회")
ok(BT.turning_point(book(_span * 2 - 100)) == "계획 변경", "둘째 마디 끝은 계획 변경")
ok(BT.turning_point(book(_span * 4 - 100)) == "돌아올 수 없는 지점", "넷째 마디 끝은 돌아올 수 없는 지점")
ok(BT.turning_point(book(_span * 5 - 100)) == "대좌절", "마지막 빚의 끝은 대좌절")
ok(BT.turning_point(book(49_000)) == "절정", "닫는 덩어리는 절정")
ok(BT.turning_point(book(100, arc=False)) == "", "도착지가 없으면 전환점도 없다")
_b6 = book(_span - 100); BT.ensure(_b6, Director())
ok(_b6["card"]["전환점"] == "기회" and "**기회**" in BT.brief(_b6), "카드에 실리고 프롬프트에 실린다")

print()
print("[배선] **flow.step 이 세우고 · 싣고 · 무작위 사건을 안 뽑는다**")
_src = (REPO / "novel" / "flow.py").read_text(encoding="utf-8")
ok("BT.ensure(book, llm)" in _src and "SR.planned(book)" in _src.split("BT.ensure")[0][-400:],
   "도착지가 있을 때만 세운다")
ok(_src.count("BT.brief(book)") == 2, "axes 와 legacy 두 자리 모두")
ok("not BT.has(book) and SH.due" in _src, "카드가 있으면 shock 을 안 뽑는다")
ok("줄거리를 미리 정하지 마라" not in _src.split("def _legacy_prompt")[1],
   "줄거리 금지가 집필 프롬프트에서 빠졌다")
_csrc = (REPO / "novel" / "compose.py").read_text(encoding="utf-8")
ok("plan or deep.brief" in _csrc and "회차도 씬도 없다" not in _csrc, "compose 는 각본이 오면 사건축을 안 뽑는다")

_b7, _d7 = book(100), Director()
_r = flow.step(_b7, _d7)
ok(_r["status"] == "ok" and _d7.calls == 1, f"step 이 각본을 세운다 ({_r['status']}, 디렉터 {_d7.calls}회)")
_wp = [p for p in _d7.prompts if "[이번 회차]" in p]
ok(bool(_wp) and CARD["질문"] in _wp[0], "집필 프롬프트에 카드가 실린다")
ok("[이 대목에서 일어날 일]" not in _wp[0], "무작위 사건 블록은 안 실린다")
_r2 = flow.step(_b7, _d7)
ok(_r2["status"] == "ok" and _d7.calls == 1, f"같은 회차의 다음 덩어리는 디렉터를 안 부른다 ({_d7.calls}회)")

_b8, _d8 = book(100, arc=False), Director()
flow.step(_b8, _d8)
ok(_d8.calls == 0 and not BT.has(_b8), "도착지가 없으면 각본도 없다  ← 검사와 옛 원고는 예전대로")

_b9 = book(100); _b9["_path"] = None
BT.ensure(_b9, Director())
ok("회차 1" in BT.show(_b9) and CARD["질문"] in BT.show(_b9), "show 가 카드를 보여 준다")

print()
if fails:
    print(f"회차 각본: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("회차 각본: 세우기 · 깨짐 · 비트 · 전환점 · 배선 -- 통과")
