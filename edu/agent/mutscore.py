# -*- coding: utf-8 -*-
"""변이 점수 -- **검사가 무는지**를 수로 말한다.

## 왜 이것이 필요한가

회귀가 초록이라는 말은 "이 자극에서는 안 틀렸다" 는 뜻이지 "틀리면 잡는다" 는
뜻이 아니다.  고객이 실제로 묻는 것은 두 번째다.  변이 점수는 그 질문에 답한다:

    DUT 에 알려진 결함을 하나씩 심고, 회귀가 몇 개를 잡는지 센다.

잡히지 않은 변이(**escape**)는 그 자체로 값진 산출물이다.  자극이 그 자리를
안 건드리고 있거나, 그 자리가 죽은 코드이거나, 둘 중 하나다.  둘 다 알아야 한다.

## 등가 변이 (equivalent mutant)

문법은 바뀌었는데 **동작이 같은** 변이가 있다.  그런 변이는 영원히 안 잡히고,
그것은 검사의 잘못이 아니다.  기계가 등가성을 판정할 수는 없으므로, 이 도구는
안 잡힌 변이를 **목록으로 내놓고 사람이 한 줄씩 보게** 한다 -- 점수를 올리려고
조용히 빼지 않는다.

## 쓰기

    python3 mutscore.py --블록 gf_mul --시행 400
    python3 mutscore.py                      # 전부
"""
import argparse
import importlib.util
import json
import os
import sys
import time

여기 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, 여기)
import harness
import vrepair


def 블록불러오기(이름):
    p = os.path.join(여기, "blocks", 이름, "block.py")
    spec = importlib.util.spec_from_file_location(f"ms_{이름}", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def 점수(블록, 시행=600, 씨앗들=(1, 2), 최대변이=200, 시간제한=15):
    """변이 점수를 잰다.

    돌려주는 dict 의 칸:
        변이수      만들어 본 변이 개수
        잡힘        회귀가 빨개진 변이
        안잡힘      초록으로 통과한 변이 (escape) -- 목록도 같이 준다
        컴파일실패  문법이 깨진 변이 (점수에서 뺀다 -- 검사의 공이 아니다)
        멈추지않음  시뮬레이션이 안 끝난 변이 (잡힌 것으로 센다: 관문이 막는다)
    """
    # 블록이 `변이대상()` 을 주면 그 파일들을 전부 변이시킨다.  모듈이 여럿인
    # 블록에서 [0] 만 변이시키면 **높은 점수가 거짓이 된다** -- 나머지 모듈을
    # 아예 안 본 점수이기 때문이다.
    대상들 = (블록.변이대상() if hasattr(블록, "변이대상")
             else [블록.소스들()[0]])
    cands = []
    for 파일 in 대상들:
        원문 = open(파일, encoding="utf-8").read()
        for c in vrepair.후보들(원문, 최대변이):
            c["파일"] = 파일
            cands.append(c)
        if len(cands) >= 최대변이:
            break
    셈 = {"변이수": 0, "잡힘": 0, "안잡힘": 0, "컴파일실패": 0, "멈추지않음": 0}
    탈출 = []
    t0 = time.time()
    for c in cands:
        tb = vrepair.임시블록(블록, c["파일"], c["원문"])
        try:
            잡았나 = False
            깨짐 = False
            for 씨 in 씨앗들:
                r = harness.잰다(tb, 시행=시행, 씨앗=씨, 시간제한=시간제한)
                if r.오류:
                    if "시간초과" in r.오류:
                        셈["멈추지않음"] += 1
                        잡았나 = True
                    else:
                        깨짐 = True
                    break
                if r.틀림 or not r.쓸모있나:
                    잡았나 = True
                    break
            if 깨짐:
                셈["컴파일실패"] += 1
                continue
            셈["변이수"] += 1
            if 잡았나:
                셈["잡힘"] += 1
            else:
                셈["안잡힘"] += 1
                탈출.append({"규칙": c["규칙"], "줄번호": c["줄번호"],
                            "파일": os.path.basename(c["파일"]),
                            "전": c["전"], "후": c["후"]})
        finally:
            tb.닫기()
    # **판정된 등가 변이**를 뺀다 -- 이유가 적힌 것만.  파일이 없으면 아무것도
    # 빼지 않는다(조용히 점수가 오르는 일이 없게).
    판정 = []
    판정파일 = os.path.join(os.path.dirname(대상들[0]), "판정된탈출.py")
    if os.path.exists(판정파일):
        ns = {}
        exec(open(판정파일, encoding="utf-8").read(), ns)
        판정 = ns.get("판정", [])
    def 판정됐나(t_):
        for j in 판정:
            if (j["규칙"] == t_["규칙"] and j["줄번호"] == t_["줄번호"]
                    and j.get("파일", t_.get("파일")) == t_.get("파일")):
                return True
        return False
    등가 = [t_ for t_ in 탈출 if 판정됐나(t_)]
    남은 = [t_ for t_ in 탈출 if not 판정됐나(t_)]
    셈["등가로판정됨"] = len(등가)
    셈["변이수"] -= len(등가)
    셈["안잡힘"] = len(남은)
    셈["점수"] = (셈["잡힘"] / 셈["변이수"]) if 셈["변이수"] else 0.0
    셈["탈출"] = 남은
    셈["초"] = round(time.time() - t0, 1)
    return 셈


def 본체(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--블록", nargs="*", default=None)
    ap.add_argument("--시행", type=int, default=600)
    ap.add_argument("--최대변이", type=int, default=200)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    이름들 = a.블록 or sorted(
        n for n in os.listdir(os.path.join(여기, "blocks"))
        if os.path.exists(os.path.join(여기, "blocks", n, "block.py")))
    전체 = {}
    for n in 이름들:
        b = 블록불러오기(n)
        ok, 왜 = harness.자해검사(b)
        if not ok:
            print(f"{n}: 자해검사 실패 ({왜}) -- 점수를 내지 않는다")
            전체[n] = {"오류": 왜}
            continue
        s = 점수(b, 시행=a.시행, 최대변이=a.최대변이)
        전체[n] = s
        if not a.json:
            등가 = s.get("등가로판정됨", 0)
            print(f"{n}: 변이 {s['변이수']}개 중 {s['잡힘']}개 잡음 "
                  f"= {s['점수']*100:.1f}%  "
                  f"(컴파일실패 {s['컴파일실패']}, 안멈춤 {s['멈추지않음']}"
                  + (f", 등가판정 {등가}" if 등가 else "")
                  + f", {s['초']}초)")
            for t in s["탈출"]:
                print(f"    탈출 {t.get('파일','?')}:{t['줄번호']} "
                      f"[{t['규칙']}] {t['전'][:46]} -> {t['후'][:46]}")
    if a.json:
        print(json.dumps(전체, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(본체())
