# -*- coding: utf-8 -*-
"""후보 순회가 **멈추는가** -- 503 이 아무 데도 안 남던 자리.

사용자 로그(2026-09-21)가 끝없이 같은 줄을 찍었다:

    [admin-agent] candidate=key-…:gemini-3-flash-preview 일시 장애(503 UNAVAILABLE…),
                  다음 후보로 전환

그리고 물었다: **"변환을 한거를 계속 안쓰고 왜 처음부터 다시 찾지?"**
답은 기록이 없어서다 -- 429 는 소진/쿨다운으로, 404·403 은 영구 사망으로 남는데
503 만 안 남아서, 잔량 가득 + 등급 높은 그 조합이 매 요청마다 또 1순위가 됐다.

여기서 재는 것은 **순서와 멈춤**뿐이다(poolpick). bot_tools 는 langchain 을 임포트해서
이 컨테이너에서 못 부르는데, 그래서 여태 이 규칙을 검사한 적이 없었다.

LLM·네트워크 없이 돈다. 실행: python3 tests/test_poolpick.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.environ["QUOTA_STATE_PATH"] = tempfile.mktemp()      # 진짜 장부를 안 건드린다
sys.path.insert(0, str(REPO))

import poolpick                                                      # noqa: E402
import quota_tracker as q                                            # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


# ---------------------------------------------------------------- 가짜 장부
class 장부:
    def __init__(self, 쉼=None, 잔량=None, 죽음=(), 핀=None):
        self.쉼 = dict(쉼 or {})
        self.잔량 = dict(잔량 or {})
        self.죽음 = set(죽음)
        self.핀 = 핀

    def is_dead(self, l):        return l in self.죽음
    def cooling_seconds(self, l): return float(self.쉼.get(l, 0.0))
    def remaining(self, l):      return int(self.잔량.get(l, 1000))
    def get_pinned(self, _):     return self.핀


최고 = {"A": 0, "B": 1, "C": 2}          # A 가 가장 좋은 모델


def 등급(l):
    return 최고.get(l, 9)


ALL = ["A", "B", "C"]

print("[기록없음] 일시 장애가 안 남으면 같은 후보가 매번 1순위가 된다")
없 = poolpick.고르기(ALL, "p", 장부(), 등급)
ok(없["순서"][0] == "A", f"쉼이 없으면 등급 순 ({없['순서']})")
있 = poolpick.고르기(ALL, "p", 장부(쉼={"A": 30.0}), 등급)
ok("A" not in 있["순서"], f"쉬는 중인 A 는 **아예 안 건다** ({있['순서']})")
ok(있["순서"][0] == "B", "다음 등급이 앞으로 온다")
ok(있["쉼"] == [("A", 30.0)], f"쉬는 것과 남은 초를 알려준다 ({있['쉼']})")

print()
print("[핀] 직전에 답을 준 조합을 처음부터 다시 찾지 않는다")
핀 = poolpick.고르기(ALL, "p", 장부(핀="C"), 등급)
ok(핀["순서"][0] == "C", f"등급이 낮아도 핀이 먼저 ({핀['순서']})")
ok(set(핀["순서"]) == set(ALL), "나머지는 그대로 뒤에 남는다")
핀쉼 = poolpick.고르기(ALL, "p", 장부(쉼={"C": 40.0}, 핀="C"), 등급)
ok("C" not in 핀쉼["순서"], "핀이 쉬는 중이면 핀도 건너뛴다(핀이 쿨다운을 무력화하지 않는다)")

print()
print("[두번] 이번 요청에서 이미 시도한 것을 또 두드리지 않는다")
또 = poolpick.고르기(ALL, "p", 장부(), 등급, 뺄것={"A", "B"})
ok(또["순서"] == ["C"], f"뺄것은 빠진다 ({또['순서']})")
빔 = poolpick.고르기(ALL, "p", 장부(), 등급, 뺄것=set(ALL))
ok(빔["순서"] == [], "다 시도했으면 빈 목록 -- 여기서 순회가 끝난다")

print()
print("[사망] 영구 사망은 빠지되, 전부 사망이면 최후로는 시도한다")
죽 = poolpick.고르기(ALL, "p", 장부(죽음={"A"}), 등급)
ok("A" not in 죽["순서"], "죽은 것은 안 건다")
전 = poolpick.고르기(ALL, "p", 장부(죽음=set(ALL)), 등급)
ok(len(전["순서"]) == 3, "다 죽었다는 기록이 틀렸을 수 있으니 최후로는 시도한다")

print()
print("[기다림] 다 쉬는 중이면 -- 한 바퀴 더 도는 대신 짧으면 기다린다")
ok(poolpick.기다릴까([("A", 12.0)], 0.0) == ("A", 12.0), "12초면 기다린다")
# 실측 2026-09-21 두 번째: 사용자가 "약 1초 남았습니다 -- 그 뒤에 다시 물어봐 주세요" 를
# 받았다. 1초를 안 기다리고 사람에게 기다리라 한 것이다. 세던 단위가 **횟수**였던 탓이다.
ok(poolpick.기다릴까([("A", 1.0)], 30.0) is not None,
   "**1초는 당연히 기다린다** ← 이미 한 번 기다렸다는 이유로 포기하지 않는다")
ok(poolpick.기다릴까([("A", 0.2)], 0.0)[1] >= 1.0,
   "너무 짧은 잠은 바닥을 준다 -- 깨어나도 아직 안 풀려 있으면 헛돈다")
ok(poolpick.기다릴까([("A", 5.0)], poolpick.마감초 - 3) is None,
   "기다림은 **벽시계**로 끝난다 -- 마감이 가까우면 안 기다린다")
ok(poolpick.기다릴까([("A", 600.0)], 0.0) is None,
   "너무 길면 기다리지 않는다 -- 기다리는 척하며 두드리는 것이 제일 나쁘다")
ok(poolpick.기다릴까([], 0.0) is None, "쉬는 것도 없으면 기다릴 것이 없다")
ok(poolpick.기다릴까([("A", 60.0)], poolpick.마감초 - 10) is None,
   "마감을 넘길 기다림은 하지 않는다 -- **끝이 있어야 한다**")

print()
print("[말] 막혔을 때 숫자를 지어내지 않는다")
말 = poolpick.막힌말([("k:gemini-3.5-flash", 47.0)], 3)
ok("47" in 말 and "gemini-3.5-flash" in 말, f"남은 초와 모델을 그대로 적는다 ({말})")
ok("3" in poolpick.막힌말([], 3), "쉼이 없어도 후보 수는 적는다")

print()
print("[장부] 일시 장애가 실제로 기록되는가 (진짜 quota_tracker)")
q.record_transient("x:m", base=10, cap=100)
ok(q.cooling_seconds("x:m") > 0, "503 을 맞으면 쉬는 표시가 남는다")
ok(q.remaining("x:m") == 0, "쉬는 동안 잔량 추정이 0 -- 후보 정렬에서도 뒤로")
첫 = q.streak("x:m")
쉼2 = q.record_transient("x:m", base=10, cap=100)
ok(q.streak("x:m") == 첫 + 1 == 2, "연달아 실패하면 횟수가 쌓인다")
ok(쉼2 == 20.0, f"쉬는 시간이 두 배로 늘어난다 ({쉼2}초)")
for _ in range(10):
    마지막 = q.record_transient("x:m", base=10, cap=100)
ok(마지막 == 100.0, f"상한에서 멈춘다 ({마지막}초) -- 영영 봉인되지 않는다")
ok(not q.is_dead("x:m"), "일시 장애를 영구 사망으로 기록하지 않는다")

print()
print("[복귀] 성공하면 벌점이 곧바로 지워지는가")
q.record_success("x:m")
ok(q.streak("x:m") == 0, "연속 실패 횟수가 0 으로")
ok(q.cooling_seconds("x:m") == 0.0, "쉬는 표시도 지워진다 -- 답을 준 조합을 뒤로 밀지 않는다")
ok(q.remaining("x:m") > 0, "잔량이 원래대로")

print()
print("[막힌답] 풀 고갈 안내를 알아보는가 -- 그래야 도구 0회로 벌주지 않는다")
import poolpick as P
쉼안내 = P.막힌말([("key-x:gemini-3.8-flash", 49.0)], 32)
실패안내 = P.막힌말([], 12)
ok(P.막힌답인가(쉼안내), "'쉬는 중' 안내를 알아본다(실측 로그의 그 답)")
ok(P.막힌답인가(실패안내), "'모두 실패했습니다' 안내도 알아본다")
ok(not P.막힌답인가("논현에 있는 관세 법인은 ... 입니다."), "**평범한 답은 막힌답이 아니다** -- 진짜 답까지 삼키면 안 된다")
ok(not P.막힌답인가(""), "빈 글도 막힌답 아님")
ok(not P.막힌답인가(None), "None 도 막힌답 아님(안 터진다)")

print()
if fails:
    print(f"실패 {len(fails)}개: {fails}")
    raise SystemExit(1)
print("전부 통과")
