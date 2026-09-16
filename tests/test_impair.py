"""**새로 넣은 손상들** -- 슬루·드룹·누화·전원잡음·지터·물리채널.

이 손상들은 논문의 마지막 주장을 떠받친다: "긴 메모리를 가진 비선형에서 표가 무너지고
신경망이 필요해진다". 그 주장이 서려면 **손상이 내가 말한 그것이어야** 한다 -- 슬루가
정말 상태를 갖는 비선형인지, 드룹이 정말 긴 메모리인지, 노치가 정말 1/(4tau) 에
나는지는 재 봐야 안다. 재지 않고 "넣었다" 고만 하면 그것이 이 저장소가 내내 쫓은
거짓 초록이다.

## 여기서 특히 조심한 두 가지

*하나 -- 빠르기를 고치면서 답이 바뀌는 것.* `누설` 은 처음에 파이썬 되돌이로 썼다가
`lfilter` 로 갈아 끼웠다. **같은 값을 내는지 확인 안 하면** 그 순간 실험 전체가
다른 물건을 재게 된다. 그래서 스칼라 되돌이를 검사 안에 다시 적어 맞대 본다
(참조를 두 번 적는 것이 싫지만, 여기서는 그것이 요점이다 -- 두 구현이 맞는가).

*둘 -- 손상이 실은 아무것도 안 하는 것.* 손잡이를 돌려도 BER 이 안 움직이면 실험은
손상을 안 재고 잡음만 재는 것이다. 각 손상이 **정말로 파형을 바꾸는지** 붙든다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

뿌리 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(뿌리))

import serdes

FAIL_목록 = []


def ok(참, 말):
    print(("  통과 " if 참 else "  실패 ") + 말)
    if not 참:
        FAIL_목록.append(말)


rng = np.random.default_rng(7)

print("[슬루 -- 상태를 갖는 비선형인가]")
u = rng.normal(0.0, 1.0, 4000)
S = 0.05
v = serdes.슬루(u, S)
걸음 = np.max(np.abs(np.diff(v)))
ok(걸음 <= S + 1e-12, f"한 표본에 S 보다 더 못 움직인다: 최대 걸음 {걸음:.6f} <= {S}")
# **비선형이다**: 중첩이 깨진다. 이것이 정의이므로 문턱을 눈대중으로 안 고른다.
u1, u2 = u, rng.normal(0.0, 1.0, len(u))
따로 = serdes.슬루(u1, S) + serdes.슬루(u2, S)
같이 = serdes.슬루(u1 + u2, S)
깨짐 = float(np.max(np.abs(같이 - 따로))) / float(np.std(같이))
ok(깨짐 > 0.5, f"중첩이 깨진다: |f(a+b)-f(a)-f(b)| 최대가 출력 rms 의 {깨짐:.2f}배")
# **메모리가 S 에 반비례해 길어진다**: 진폭 1 계단이 올라가는 데 1/S 표본이 든다.
def 상승(S):
    시작 = 50
    y = serdes.슬루(np.concatenate([np.zeros(시작), np.ones(4000)]), S)
    return int(np.argmax(y > 0.9)) - 시작
빠른, 느린 = 상승(0.05), 상승(0.01)
ok(3.5 < 느린 / max(빠른, 1) < 7.0,
   f"S 를 5배 줄이면 상승이 {느린 / max(빠른, 1):.1f}배 길어진다 "
   f"({빠른} -> {느린} 표본, 1/S 꼴이면 5배)")
ok(np.allclose(serdes.슬루(u, 0.0), u), "S=0 이면 아무것도 안 한다")

print("[드룹 -- 빠른 판이 느린 판과 같은 값인가]")
tau = 97.0
a = float(np.exp(-1.0 / tau))
b, 참조 = 0.0, np.empty_like(u)
for i, x in enumerate(u.tolist()):
    b = a * b + (1.0 - a) * x
    참조[i] = x - b
차 = float(np.max(np.abs(참조 - serdes.누설(u, tau))))
ok(차 < 1e-9, f"lfilter 판이 스칼라 되돌이와 같다: 최대 차 {차:.2e}")
계단 = serdes.누설(np.ones(3000), tau)
ok(계단[-1] < 0.05, f"DC 를 지운다(고역통과): 계단 끝 {계단[-1]:.4f}")
# **메모리가 tau 만큼 길다** -- 계단 응답이 1/e 로 떨어지는 자리.
떨어짐 = int(np.argmax(계단 < np.exp(-1.0)))
ok(abs(떨어짐 - tau) < 0.2 * tau,
   f"1/e 자리가 tau 근처다: {떨어짐} 표본 vs tau={tau}")

print("[누화 -- 데이터와 무관한 방해인가]")
h = serdes.채널(20.0, 8, 64)
y = np.convolve(np.repeat(rng.integers(0, 2, 2000) * 2.0 - 1.0, 8), h,
                mode="full")[:16000]
y2 = serdes.크로스토크(y, h, 8, 0.2, 2000, np.random.default_rng(3))
ok(not np.allclose(y, y2), "파형을 실제로 바꾼다")
상관 = abs(float(np.corrcoef(y, y2 - y)[0, 1]))
ok(상관 < 0.2, f"더해진 것이 내 신호와 거의 무관하다: |상관| {상관:.3f}")
ok(np.allclose(serdes.크로스토크(y, h, 8, 0.0, 2000, rng), y), "세기 0 이면 그대로다")

print("[전원잡음 -- 더하기가 아니라 곱하기인가]")
z = serdes.전원잡음(np.ones(800), 8, 0.1, 10.0)
ok(abs(np.max(z) - 1.1) < 0.02 and abs(np.min(z) - 0.9) < 0.02,
   f"1 에 ±세기만큼 실린다: [{np.min(z):.3f}, {np.max(z):.3f}]")
z2 = serdes.전원잡음(2 * np.ones(800), 8, 0.1, 10.0)
ok(np.allclose(z2, 2 * z), "입력에 비례한다 -- 더해지는 잡음이 아니다")

print("[지터 -- 뽑는 때를 흔드는가]")
파형 = np.arange(4000, dtype=float)          # 기울기 1인 톱니: 오프셋이 값으로 보인다
곧은것 = serdes.지터표본(파형, 3, 8, 400, 0.0, 0.0)
ok(np.array_equal(곧은것, 파형[3::8][:400]), "지터 0 이면 그냥 뽑은 것과 같다")
흔든것 = serdes.지터표본(파형, 3, 8, 400, 0.05, 0.0, rng=np.random.default_rng(1))
오프 = (흔든것 - 곧은것) / 8.0                # 기울기 1 이므로 값 차이 = 표본 차이
ok(abs(float(np.std(오프)) - 0.05) < 0.01,
   f"랜덤 지터 rms 가 시킨 값이다: {np.std(오프):.4f} UI vs 0.05")
사인 = serdes.지터표본(파형, 3, 8, 400, 0.0, 0.1, 40.0)
ok(abs(float(np.max((사인 - 곧은것) / 8.0)) - 0.1) < 0.01,
   f"정현 지터 진폭이 시킨 값이다: {np.max((사인 - 곧은것) / 8.0):.4f} UI vs 0.1")

print("[물리채널 -- 두 손실 기구와 비아 스터브]")
ok(np.allclose(serdes.채널(20.0, 8, 64),
               serdes.채널물리(sps=8, 길이심볼=64, 도체dB=20.0, 유전dB=0.0)),
   "유전 손실 0 이면 기존 sqrt(f) 채널과 정확히 같다")
# **노치는 1/(4tau) 에 난다** -- 1/4 파장 개방 스터브.
for UI, 기대 in ((0.5, 1.0), (1.0, 0.5)):
    hh = serdes.채널물리(sps=8, 길이심볼=64, 도체dB=12.0, 유전dB=8.0,
                     스터브UI=UI, 스터브세기=1.0)
    H = np.abs(np.fft.rfft(hh))
    f = np.fft.rfftfreq(len(hh), 1.0)
    fn = 0.5 / 8
    안 = (f > 1e-6) & (f <= fn * 1.05)
    자리 = f[안][int(np.argmin(H[안]))] / fn
    ok(abs(자리 - 기대) < 0.06,
       f"스터브 {UI} UI 의 노치가 f_nyq 의 {자리:.2f}배 (1/(4tau) = {기대})")
# 유전 손실은 **같은 Nyquist 손실이라도 꼬리를 바꾼다**
c1 = serdes.커서들(serdes.채널물리(sps=8, 길이심볼=64, 도체dB=20.0, 유전dB=0.0), 8)
c2 = serdes.커서들(serdes.채널물리(sps=8, 길이심볼=64, 도체dB=0.0, 유전dB=20.0), 8)
ok(abs(c1["메인"] - c2["메인"]) > 0.02,
   f"같은 20dB 라도 메인 커서가 다르다: 도체 {c1['메인']:.3f} vs 유전 {c2['메인']:.3f}")

print("[링크에 물렸는가 -- 손잡이가 BER 을 움직이나]")
밑 = dict(비트수=40000, 손실dB=20.0, SNRdB=26.0, FFE탭=11, ADC비트=7, 씨=0)
기준 = serdes.링크(**밑)
for 이름, kw in (("슬루", dict(슬루율=0.015)),
              ("드룹+압축", dict(누설시상수=150.0, 압축=1.6)),
              ("누화", dict(누화세기=0.25)),
              ("지터", dict(지터rjUI=0.12)),
              ("물리채널(스터브)", dict(물리채널=dict(도체dB=12.0, 유전dB=8.0,
                                             스터브UI=0.6, 스터브세기=1.0)))):
    r = serdes.링크(**밑, **kw)
    갈림, 말 = serdes.구별되나(기준["오류수"], 기준["잰비트"], r["오류수"], r["잰비트"])
    ok(갈림 and r["BER"] > 기준["BER"],
       f"{이름}: BER {기준['BER']:.2e} -> {r['BER']:.2e} ({말})")

print("[전원잡음 -- 두 구조를 똑같이 깎는다(내 예상이 틀렸던 자리)]")
# 처음에는 "정적인 표에 특히 나쁘다" 고 적었다. **재 보니 아니었다** -- 둘 다
# 같은 비율로 나빠진다. 이 검사는 그 정정을 붙들어 둔다: 비대칭이 없다는 것이
# 결론이므로, 누가 다시 "표가 약하다" 고 적으면 여기서 걸려야 한다.
def 합(kw, 씨수=3):
    e = b = 0
    for 씨 in range(씨수):
        r = serdes.링크(씨=씨, **kw)
        e += r["오류수"]; b += r["잰비트"]
    return e, b, e / b

선 = dict(비트수=400000, 손실dB=20.0, SNRdB=26.0, FFE탭=11, ADC비트=7)
긴 = dict(선, 누설시상수=150.0, 압축=1.6, 표본표창=2, 표본표비트=4)
잰 = {}
for 이름, 밑2 in (("선형슬라이서", 선), ("긴메모리+표", 긴)):
    e0, b0, p0 = 합(밑2)
    e1, b1, p1 = 합(dict(밑2, 전원세기=0.5))
    갈림, 말 = serdes.구별되나(e0, b0, e1, b1)
    ok(갈림 and p1 > p0, f"{이름}: {p0:.2e} -> {p1:.2e} ({말})")
    잰[이름] = p1 / p0
ok(0.6 < 잰["긴메모리+표"] / 잰["선형슬라이서"] < 1.6,
   f"두 구조가 **같은 비율로** 깎인다: 표 {잰['긴메모리+표']:.2f}배 vs "
   f"선형 {잰['선형슬라이서']:.2f}배 -- 비대칭이 없다")

print()
if FAIL_목록:
    print(f"실패 {len(FAIL_목록)}개")
    for m in FAIL_목록:
        print("  - " + m)
    sys.exit(1)
print("전부 통과")
