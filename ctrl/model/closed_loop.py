#!/usr/bin/env python3
# 가장 쉬운 무인체계 제어 정책 -- PI 위치 제어기를 SSM(상태공간) 꼴로.
#
# 왜 이게 "가장 쉬운데 진짜 SSM 인가":
#   SSM 재귀        h_t = Abar·h_{t-1} + Bbar·o_t ,  y_t = C·h_t + D·o_t
#   PI 제어기       적분 = 적분 + 오차·dt ,          u = Kp·오차 + Ki·적분
#   -> Abar=1, Bbar=dt, o=오차, C=Ki, D=Kp. **완전히 같은 식이다.**
# 상태 h = 오차의 적분. 이 재귀가 우리 하드웨어 scan_mac 의 h 갱신에 그대로 매핑된다.
# (Mamba 의 selective 는 Abar/Bbar 를 입력의존으로 만든 것 -- 여기선 상수라 '가장 쉬움'.)
#
# 플랜트: 속도지령 로버(단일 적분기) p' = u. 외란 d 를 더해 적분항이 미는 것을 보인다.
# 이 파일은 **골든(float)** 이다. 고정소수·회로판은 ssm/scan_mac 이 같은 재귀를 한다.
import numpy as np, json, sys, pathlib


def 돌리기(목표=1.0, Kp=4.5, Ki=2.0, dt=0.02, T=10.0,
          외란=0.4, 외란시작=5.0, p0=0.0):
    # 게인은 쓸어서 골랐다(ζ≈1.6, 잘 감쇠). PI 는 영점(s=-Ki/Kp) 때문에 약간 오버슈트한다 --
    # 그것을 숨기지 않는다(과장방지). Ki 를 낮춰 영점을 멀리 두어 7%까지 줄였다.
    """폐루프 시뮬. 목표 위치로 로버를 보낸다. 외란시작(초)부터 상수 외란을 더한다.
    돌려주는 것: 시간·위치·행동·상태(적분) 배열과 지표."""
    N = int(T / dt)
    t = np.arange(N) * dt
    p = np.zeros(N)          # 위치(측정)
    u = np.zeros(N)          # 행동(속도 지령) = 정책 출력
    h = np.zeros(N)          # SSM 상태 = 오차 적분
    p[0] = p0
    적분 = 0.0
    for k in range(N):
        오차 = 목표 - p[k]                     # 관측 o = 오차
        적분 = 적분 + 오차 * dt                 # h 갱신: Abar=1, Bbar=dt
        h[k] = 적분
        u[k] = Kp * 오차 + Ki * 적분            # 출력: D=Kp, C=Ki
        d = 외란 if t[k] >= 외란시작 else 0.0   # 상수 외란(바람 등)
        if k + 1 < N:
            p[k+1] = p[k] + (u[k] - d) * dt     # 플랜트: p' = u - d
    지표 = _지표내기(t, p, 목표, dt, 외란시작)
    return {"t": t, "p": p, "u": u, "h": h, "목표": 목표, "외란시작": 외란시작, "지표": 지표}


def _지표내기(t, p, 목표, dt, 외란시작):
    err = np.abs(p - 목표)
    band = 0.02 * abs(목표)                     # 2% 정착 밴드
    # 정착시간: 이후로 계속 밴드 안인 첫 시각(외란 전 구간에서)
    전 = t < 외란시작
    정착 = None
    idx = np.where(전)[0]
    for i in idx:
        if np.all(err[i:idx[-1]+1] <= band):
            정착 = float(t[i]); break
    오버슈트 = float(max(0.0, (np.max(p[전]) - 목표) / abs(목표) * 100)) if 목표 else 0.0
    정상오차 = float(err[idx[-1]])              # 외란 직전 정상상태 오차
    외란후 = t >= 외란시작
    외란편차 = float(np.max(err[외란후]))       # 외란이 밀어낸 최대 편차
    외란복구 = float(err[-1])                   # 끝에서 남은 오차(적분이 밀어냈나)
    return {"정착시간s": 정착, "오버슈트pct": round(오버슈트, 1),
            "정상오차": round(정상오차, 4), "외란최대편차": round(외란편차, 4),
            "외란복구잔차": round(외란복구, 4)}


def 요약(r):
    m = r["지표"]
    print("== 가장 쉬운 제어 정책 (PI as SSM) ==")
    print(f"  목표 위치      : {r['목표']}")
    print(f"  정착시간(2%)   : {m['정착시간s']} s")
    print(f"  오버슈트       : {m['오버슈트pct']} %")
    print(f"  정상상태 오차  : {m['정상오차']}")
    print(f"  외란({r['외란시작']}s~) 최대편차: {m['외란최대편차']}  -> 끝 잔차 {m['외란복구잔차']}")
    # 정직 점검: 실제로 목표에 갔나, 적분이 외란을 밀어냈나
    성공 = (m['정상오차'] < 0.02 and m['외란복구잔차'] < 0.05)
    print(f"  판정: {'수렴·외란복구 확인' if 성공 else '**아직 안정 안 됨 -- 게인 조정 필요**'}")
    return 성공


def 궤적저장(r, 경로="ctrl/model/궤적.json"):
    간추림 = {"t": [round(x,3) for x in r["t"].tolist()],
             "p": [round(x,4) for x in r["p"].tolist()],
             "u": [round(x,4) for x in r["u"].tolist()],
             "h": [round(x,4) for x in r["h"].tolist()],
             "목표": r["목표"], "외란시작": r["외란시작"], "지표": r["지표"]}
    pathlib.Path(경로).write_text(json.dumps(간추림, ensure_ascii=False))
    print(f"  궤적 저장: {경로} ({len(간추림['t'])} 스텝)")


if __name__ == "__main__":
    r = 돌리기()
    성공 = 요약(r)
    if "--저장" in sys.argv:
        궤적저장(r)
    sys.exit(0 if 성공 else 1)
