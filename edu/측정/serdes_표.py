# -*- coding: utf-8 -*-
"""T8 의 표를 **다시 낸다** -- 붙여 넣은 수가 조용히 낡지 않게.

    python3 edu/측정/serdes_표.py            전부 (몇 분)
    python3 edu/측정/serdes_표.py --빠르게    비트 수를 줄여 배선만 본다

이 저장소의 링크 모형(`serdes.링크`)을 그대로 쓴다.  교재가 인용하는 수는
여기서 나온 것이고, `tests/test_serdes_표.py` 가 둘을 맞춰 본다.
"""
import json
import os
import sys

뿌리 = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, 뿌리)

구성 = [("none", {}),
      ("CTLE", dict(CTLE피킹dB=6)),
      ("CTLE+FFE3", dict(CTLE피킹dB=6, FFE탭=3)),
      ("CTLE+FFE3+DFE4", dict(CTLE피킹dB=6, FFE탭=3, DFE탭=4))]
씨앗들 = (1, 2, 3)


def 재기(비트=200000, 손실들=(10, 20, 30), SNR=26):
    import serdes
    난것 = {}
    for l in 손실들:
        for 이름, kw in 구성:
            오류 = 비트수 = 0
            for 씨 in 씨앗들:
                r = serdes.링크(비트수=비트, 손실dB=l, SNRdB=SNR, 씨=씨, **kw)
                오류 += r["오류수"]
                비트수 += r["잰비트"]
            난것[f"{l}|{이름}"] = [오류, 비트수]
    return 난것


def 커서재기(손실들=(10, 20, 30), sps=8):
    import serdes
    난것 = {}
    for l in 손실들:
        h = serdes.채널(손실dB=l, sps=sps)
        c = serdes.커서들(serdes.펄스응답(h, sps), sps)
        난것[l] = [round(c["메인"], 4), round(c["선행"][-1], 4),
                 round(c["후행"][0], 4), round(c["ISI"], 4),
                 round(c["아이높이_ISI"], 4)]
    return 난것


if __name__ == "__main__":
    빠르게 = "--빠르게" in sys.argv
    난것 = {"커서": 커서재기(), "BER": 재기(비트=20000 if 빠르게 else 200000)}
    print(json.dumps(난것, ensure_ascii=False, indent=1))
