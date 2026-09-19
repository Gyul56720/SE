# -*- coding: utf-8 -*-
"""생성된 레지스터 파일을 검사한다.

DUT 는 `edu/house/regmap.py` 가 낸 RTL 이다.  골든모델은 **같은 맵을 보고
접근 규칙을 따로 구현한** 파이썬이다 -- 생성기 코드를 읽어서 베낀 것이 아니라
접근 종류의 정의(RO 는 쓰기를 무시한다, W1C 는 1 을 쓰면 지워진다 ...)에서
왔다.  그래서 생성기가 규칙을 잘못 구현하면 갈라진다.

이것이 교안이 말하는 '생성기를 쓰되 생성물을 검사한다' 를 실제로 한 것이다.
"""
import os, sys, random, tempfile

여기 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/SE/edu/house")
sys.path.insert(0, 여기)
import regmap
import gen

이름 = "regfile"
톱 = "tb"
_만든것 = {}


합성톱 = "crcip_regs"


def 소스들():
    """[0] 이 **생성된** DUT 다.  생성기가 바뀌면 여기가 바뀐다."""
    if "p" not in _만든것:
        d = tempfile.mkdtemp(prefix="regf_")
        _만든것["d"] = d
        _만든것["p"] = gen.만들기(d)
    return list(_만든것["p"])


def _골든(접근들):
    """맵의 접근 규칙만으로 각 접근 뒤의 읽기 값을 계산한다.

    접근은 (쓰기, 주소, 값, 하드웨어사건) 이다.  하드웨어 사건은 APB 접근보다
    **먼저** 한 사이클 들어간다 -- 테스트벤치와 같은 순서라야 한다.
    """
    m = regmap.예제
    상태 = {}
    for r in m.레지스터들:
        for f in r.필드들:
            상태[(r.오프셋, f.이름)] = f.리셋
    오프셋맵 = {r.오프셋: r for r in m.레지스터들}
    낸값 = []
    for 쓰기, 주소, 값, 하드 in 접근들:
        # 하드웨어 사건: IRQ_STATUS 의 W1C 비트를 세우고, ERR_COUNT 를 늘린다
        if 하드:
            for f in 오프셋맵[0x10].필드들:
                비트 = {"ERR_CRC": 0, "ERR_LEN": 1, "OVERFLOW": 2}[f.이름]
                if (하드 >> 비트) & 1:
                    상태[(0x10, f.이름)] |= 1
            더할 = (하드 >> 3) & 0x7
            if 더할:
                k = (0x18, "COUNT")
                상태[k] |= 더할
        r = 오프셋맵.get(주소)
        if r is None:
            낸값.append(0)
            continue
        if 쓰기:
            for f in r.필드들:
                k = (r.오프셋, f.이름)
                조각 = (값 >> f.하위) & ((1 << f.폭) - 1)
                if f.접근 in ("RW", "WO"):
                    상태[k] = 조각
                elif f.접근 == "RW1":
                    if 상태[k] == f.리셋:
                        상태[k] = 조각
                elif f.접근 == "W1C":
                    상태[k] &= ~조각 & ((1 << f.폭) - 1)
                elif f.접근 == "W1S":
                    상태[k] |= 조각
                # RO, RC 는 쓰기를 무시한다
        # 읽기
        v = 0
        for f in r.필드들:
            if f.접근 == "WO":
                continue
            v |= (상태[(r.오프셋, f.이름)] & ((1 << f.폭) - 1)) << f.하위
        낸값.append(v)
        for f in r.필드들:
            if f.접근 == "RC":
                상태[(r.오프셋, f.이름)] = 0
    return 낸값


def 자극(시행, 씨앗):
    m = regmap.예제
    rnd = random.Random(씨앗)
    오프셋들 = [r.오프셋 for r in m.레지스터들]
    접근들 = []
    # 경계: 리셋 직후 모든 레지스터를 한 번 읽는다 (리셋값 확인)
    for off in 오프셋들:
        접근들.append((0, off, 0, 0))
    # 모든 비트를 1 로 써 본다 (RO 가 정말 무시하는지, W1C 가 지우는지)
    for off in 오프셋들:
        접근들.append((1, off, 0xFFFFFFFF, 0))
    # **하드웨어 사건을 반드시 넣는다.**  안 넣으면 W1C 와 RC 경로가 안 돈다 --
    # 변이 점수가 그것을 짚어서 알게 됐다(58 % 에서 탈출 다섯 개가 전부 그 자리).
    접근들.append((0, 0x10, 0, 0b111))          # 세 IRQ 비트를 모두 세운다
    접근들.append((0, 0x10, 0, 0))              # 세워졌는지 읽는다
    접근들.append((1, 0x10, 0b001, 0))          # 하나만 W1C 로 지운다
    접근들.append((0, 0x10, 0, 0))              # 나머지 둘은 남아 있어야 한다
    접근들.append((0, 0x18, 0, 0b111 << 3))     # ERR_COUNT 를 올린다
    접근들.append((0, 0x18, 0, 0))              # RC -- 읽으면 지워진다
    for _ in range(max(0, 시행 - len(접근들))):
        하드 = rnd.choice([0, 0, 0, rnd.getrandbits(6)])
        접근들.append((rnd.randrange(2), rnd.choice(오프셋들),
                      rnd.getrandbits(32), 하드))
    줄들 = [f"{w} {a:08x} {d:08x} {h:08x}" for w, a, d, h in 접근들]
    return 줄들, _골든(접근들)


# 처리량 한계를 선언하지 않는 이유를 **적는다**.  관문이 "못 쟀다" 로 내는 것과
# "해당 없다" 는 다르다 -- 모르는 것은 안 된 것으로 다루되, 아는 것은 적는다.
성능해당없음 = ("APB 접근은 규격이 사이클을 정한다(setup 1 + enable 1). 이 블록이"
              )
