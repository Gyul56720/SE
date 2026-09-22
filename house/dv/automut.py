# -*- coding: utf-8 -*-
"""house/dv/automut -- **테스트벤치가 정말로 무는지 기계로 증명한다.**

## 왜 필요한가

회귀가 초록이라는 것은 두 가지 중 하나다: **설계가 옳거나, 검사기가 아무것도
안 보거나.** 보통의 회귀는 그 둘을 못 가른다 -- 실패 경로를 한 번도 안 타기
때문이다. 이 저장소의 규율이 그것이다: *검사하지 않은 초록불이 검사한 빨간불보다
나쁘다.*

실측 2026-09-22 기준, `gen.관문()` 은 일곱 칸을 봤지만 **테스트벤치가 무는지는
한 번도 안 봤다.** 모델이 `printf("{\\"pass\\":400,\\"fail\\":0}")` 한 줄만 찍는
테스트벤치를 내도 관문 4(골든 대조)가 초록이었다. 그러면 그 위에 쌓은 합성·STA
수가 전부 무의미해진다.

## 업계에서 이것을 무엇이라 부르나

팹리스 VLSI 의 검증 사인오프에서 **fault grading** 또는 **mutation / fault
injection** 이라고 부른다(Synopsys Certitude 가 이 일만 하는 상용 도구다).
AMD · Xilinx · Broadcom 급의 IP 사인오프에서 "커버리지 100%" 만으로는 서명하지
않는다 -- 커버리지는 *자극이 거기를 지나갔다* 는 말이지 *검사기가 틀린 값을
알아본다* 는 말이 아니기 때문이다. 재는 수가 **변이 점수(mutation score)** 다.

    변이 점수 = 잡힌 변이 / 심은 변이

## `house/dv/mutate.py` 와 무엇이 다른가

`mutate.py` 는 `nsw_fir` 하나에 대해 **손으로 고른** 변이 목록을 갖는다. 그 편이
날카롭다 -- 어느 검사가 잡아야 하는지까지 적혀 있다. 그러나 **스펙에서 방금 지은
회로**에는 쓸 수 없다. 손으로 쓸 사람이 없기 때문이다.

여기서는 **어느 SystemVerilog 에나 걸리는 기계적 변이**만 쓴다. 덜 날카롭지만
회로를 안 가린다. 둘은 서로를 대신하지 않는다.

## 안 잡히는 변이가 다 구멍인 것은 아니다

`mutate.py` 가 이미 배운 것을 그대로 가져온다. 안 잡힌 변이는 셋 중 하나다.

  · **구멍**   -- 진짜 버그인데 테스트벤치가 못 본다
  · **무해**   -- 변이가 사실 버그가 아니다 (닿지 않는 코드, 여유가 있는 상수)
  · **못 짓는다** -- 변이 뒤 RTL 이 lint/빌드에서 죽는다. 점수에서 **뺀다**
                   (안 돌아간 것을 '안 잡혔다' 로 세면 점수가 거짓이 된다)

세 번째를 점수에서 빼는 것이 중요하다. 빌드가 깨진 변이를 '검사가 놓쳤다' 로
세면, **테스트벤치를 고치지 않고도 점수가 오르내린다.**

실행: python3 house/dv/automut.py [회로키]
"""
from __future__ import annotations

import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

뿌리 = Path(__file__).resolve().parent
집 = 뿌리.parent
저장소 = 집.parent
if str(저장소) not in sys.path:
    sys.path.insert(0, str(저장소))


# ------------------------------------------------------------------ 변이 규칙
#
# **주석과 문자열은 안 건드린다.** 주석 안의 `+` 를 `-` 로 바꾸면 RTL 은 그대로인데
# 변이를 심었다고 세게 되고, 그 변이는 영영 안 잡힌다 -- 점수가 거짓으로 내려간다.
#
# 규칙 하나 = (id, 설명, 정규식, 바꿀 것, 갈래)
#   갈래 "값"   -- 계산 결과가 달라진다. **기능 검사가 잡아야 한다**
#   갈래 "제어" -- 흐름이 달라진다. 자극이 그 가지를 타야 잡힌다
#   갈래 "경계" -- 한 칸 어긋난다(off-by-one). 경계 시험이 없으면 못 잡는다
규칙들 = [
    ("연산_더하기빼기", "`+` 를 `-` 로 -- 데이터패스의 값이 달라진다",
     r"(?<![-+=<>!])\+(?![-+=])", "-", "값"),
    # **`always @(*)` 의 별표를 건드리면 안 된다.** 첫 판이 그것을 바꿔
    # `always @(+)` 를 냈다 -- 빌드가 깨지는 변이라 점수에서 빠지고, 그 자리를
    # 검사하지도 못한다. 앞에 `(` 나 `@` 가 오면 곱셈이 아니다.
    ("연산_곱하기", "`*` 를 `+` 로 -- 곱셈이 덧셈이 된다",
     r"(?<![*/(@\s])\s*\*(?![*/)])", " +", "값"),
    # **`<=` 는 비대입일 수도 있다.** 첫 판이 `v_s1 <= push;` 를 `v_s1 < push;`
    # 로 바꿨다 -- 비교가 아니라 **비블로킹 대입**이다. 둘을 정규식으로 가르는 것은
    # 믿을 수 없으므로 반대로 간다: `<` 만 무는 것은 절대 대입이 아니다.
    ("비교_작다", "`<` 를 `<=` 로 -- 경계가 한 칸 어긋난다",
     r"(?<![<=])<(?![<=])", "<=", "경계"),
    ("비교_크다", "`>` 를 `>=` 로 -- 경계가 한 칸 어긋난다",
     r"(?<![->=])>(?![>=])", ">=", "경계"),
    ("논리_and를or", "`&&` 를 `||` 로 -- 조건이 느슨해진다",
     r"&&", "||", "제어"),
    ("논리_or를and", "`||` 를 `&&` 로 -- 조건이 빡빡해진다",
     r"\|\|", "&&", "제어"),
    ("같다_다르다", "`==` 를 `!=` 로 -- 조건이 뒤집힌다",
     r"(?<![!=<>])==(?![=])", "!=", "제어"),
    ("상수_한칸", "상수를 한 칸 올린다 -- off-by-one",
     r"\b(\d+)'([dD])(\d+)\b", None, "경계"),
    ("십진상수_한칸", "맨 십진수를 한 칸 올린다 -- off-by-one",
     r"(?<![\w'])(\d{1,4})(?![\w'.])", None, "경계"),
]

# 이 낱말이 든 줄은 안 건드린다 -- 바꿔 봐야 뜻이 없거나 빌드가 깨질 뿐이다
_건너뛸줄 = ("`include", "`define", "`timescale", "module ", "endmodule",
          "import ", "package ", "parameter ", "localparam ")


def _토막내기(sv: str) -> list:
    """(글, 바꿔도 되나) 조각들. 주석과 문자열은 `False` 로 잠근다."""
    조각, 버퍼, i, n = [], [], 0, len(sv)
    def 밀기(쓸수있나):
        if 버퍼:
            조각.append(("".join(버퍼), 쓸수있나))
            버퍼.clear()
    while i < n:
        c = sv[i]
        if c == "/" and i + 1 < n and sv[i + 1] == "/":
            밀기(True)
            j = sv.find("\n", i)
            j = n if j < 0 else j
            조각.append((sv[i:j], False))
            i = j
        elif c == "/" and i + 1 < n and sv[i + 1] == "*":
            밀기(True)
            j = sv.find("*/", i + 2)
            j = n if j < 0 else j + 2
            조각.append((sv[i:j], False))
            i = j
        elif c == '"':
            밀기(True)
            j = i + 1
            while j < n and sv[j] != '"':
                j += 2 if sv[j] == "\\" else 1
            j = min(j + 1, n)
            조각.append((sv[i:j], False))
            i = j
        else:
            버퍼.append(c)
            i += 1
    밀기(True)
    return 조각


def 후보찾기(sv: str, 최대=40) -> list:
    """심을 수 있는 변이들. [{"id","설명","갈래","자리","전","후"}].

    **자리는 바이트 위치**다. 같은 글자가 여러 번 나오므로 몇 번째인지로는 못 짚는다.
    """
    조각 = _토막내기(sv)
    난것, 위치 = [], 0
    줄시작 = {0: 0}
    for m in re.finditer(r"\n", sv):
        줄시작[m.end()] = 0
    for 글, 쓸수있나 in 조각:
        if not 쓸수있나:
            위치 += len(글)
            continue
        for 규칙id, 설명, 패턴, 바꿀것, 갈래 in 규칙들:
            for m in re.finditer(패턴, 글):
                절대 = 위치 + m.start()
                줄머리 = sv.rfind("\n", 0, 절대) + 1
                줄끝 = sv.find("\n", 절대)
                줄 = sv[줄머리: 줄끝 if 줄끝 > 0 else len(sv)]
                if any(k in 줄 for k in _건너뛸줄):
                    continue
                전 = m.group(0)
                if 바꿀것 is None:            # 상수 한 칸 올리기
                    if 규칙id == "상수_한칸":
                        후 = f"{m.group(1)}'{m.group(2)}{int(m.group(3)) + 1}"
                    else:
                        후 = str(int(m.group(1)) + 1)
                else:
                    후 = 바꿀것
                if 후 == 전:
                    continue
                난것.append({"id": f"{규칙id}@{절대}", "규칙": 규칙id, "설명": 설명,
                           "갈래": 갈래, "자리": 절대, "전": 전, "후": 후,
                           "줄": 줄.strip()[:90]})
        위치 += len(글)
    # **골고루 고른다.** 앞에서부터 40개를 자르면 한 always 블록만 두들기게 된다.
    난것.sort(key=lambda x: x["자리"])
    if len(난것) <= 최대:
        return 난것
    걸음 = len(난것) / 최대
    return [난것[int(i * 걸음)] for i in range(최대)]


def 심기(sv: str, 후보: dict) -> str:
    """그 자리 하나만 바꾼 소스."""
    i, 전 = 후보["자리"], 후보["전"]
    if sv[i:i + len(전)] != 전:
        raise ValueError(f"자리가 안 맞는다: {i} 에 {전!r} 가 없다")
    return sv[:i] + 후보["후"] + sv[i + len(전):]


# ------------------------------------------------------------------ 돌리기
def 한바퀴(설계, 최대=12, txn=300, 씨앗들=(1, 7), 초=240, 찍기=False) -> dict:
    """변이를 하나씩 심고 **테스트벤치가 빨개지는지** 본다.

    돌려주는 것:
        점수      잡힌 / (심은 - 못지은)   -- 못 지은 변이는 분모에서 뺀다
        심은/잡힌/놓친/못지은
        목록      변이마다 무슨 일이 났나
    """
    from house import designs as DES
    from house import sim as SIM

    t0 = time.time()
    if not 설계.RTL:
        return {"됐나": False, "까닭": "RTL 이 없다", "점수": None}
    원본길 = Path(설계.RTL[0])
    if not 원본길.exists():
        return {"됐나": False, "까닭": f"RTL 을 못 읽는다: {원본길}", "점수": None}
    원본 = 원본길.read_text(encoding="utf-8")

    후보들 = 후보찾기(원본, 최대=최대)
    if not 후보들:
        return {"됐나": False, "까닭": "심을 변이를 못 찾았다", "점수": None,
                "심은": 0}

    잡힌, 놓친, 못지은 = [], [], []
    with tempfile.TemporaryDirectory() as 방:
        방 = Path(방)
        for c in 후보들:
            새길 = 방 / 원본길.name
            새길.write_text(심기(원본, c), encoding="utf-8")
            나머지 = []
            for p in 설계.RTL[1:]:
                q = 방 / Path(p).name
                shutil.copy(Path(p), q)
                나머지.append(q)
            변이설계 = DES.설계(키=f"{설계.키}__mut", 이름=설계.이름, top=설계.top,
                            RTL=[새길] + 나머지, TB=설계.TB, 파라=dict(설계.파라))
            결과 = {"id": c["id"], "규칙": c["규칙"], "갈래": c["갈래"],
                  "전": c["전"], "후": c["후"], "줄": c["줄"]}
            try:
                빨개졌나 = False
                for s in 씨앗들:
                    r = SIM.돌리기(None, seed=s, txn=txn, 설계=변이설계, 초=초)
                    if int(r.get("fail", 0)) + int(r.get("timeout", 0)) > 0:
                        빨개졌나 = True
                        결과["잡은씨앗"] = s
                        결과["fail"] = r.get("fail")
                        break
                (잡힌 if 빨개졌나 else 놓친).append(결과)
            except Exception as e:                           # noqa: BLE001
                # 빌드/lint 가 깨졌다 -- **점수에서 뺀다.** 안 돌아간 것을
                # '검사가 놓쳤다' 로 세면 점수가 거짓이 된다.
                결과["까닭"] = f"{type(e).__name__}: {str(e)[:120]}"
                못지은.append(결과)
            if 찍기:
                print(f"  {c['id']:42} {c['전']!r}->{c['후']!r}  "
                      f"{'잡힘' if 결과 in 잡힌 else ('못지음' if 결과 in 못지은 else '놓침')}",
                      flush=True)

    센것 = len(잡힌) + len(놓친)
    return {"됐나": True, "초": round(time.time() - t0, 1),
            "점수": (round(len(잡힌) / 센것, 3) if 센것 else None),
            "심은": len(후보들), "잡힌": len(잡힌), "놓친": len(놓친),
            "못지은": len(못지은), "센것": 센것,
            "잡힌목록": 잡힌, "놓친목록": 놓친, "못지은목록": 못지은}


def 요약글(r: dict) -> str:
    if not r.get("됐나"):
        return f"자해 검사를 못 돌렸다 -- {r.get('까닭')}"
    점 = r.get("점수")
    줄 = [f"변이 점수 {점:.0%} ({r['잡힌']}/{r['센것']}) · "
         f"심은 {r['심은']} · 못 지은 {r['못지은']} · {r['초']}s" if 점 is not None
         else f"변이를 하나도 못 셌다 (심은 {r['심은']} · 못 지은 {r['못지은']})"]
    for x in (r.get("놓친목록") or [])[:6]:
        줄.append(f"  놓침 [{x['갈래']}] {x['전']}->{x['후']}  {x['줄']}")
    return "\n".join(줄)


if __name__ == "__main__":
    from house import designs as DES
    키 = next((a for a in sys.argv[1:] if not a.startswith("-")), None)
    d = DES.찾기(키)
    print(f"[automut] {d.키} ({d.이름}) -- {d.RTL[0]}")
    r = 한바퀴(d, 최대=int(next((a.split("=")[1] for a in sys.argv if a.startswith("--최대=")), 12)),
            찍기=True)
    print()
    print(요약글(r))
