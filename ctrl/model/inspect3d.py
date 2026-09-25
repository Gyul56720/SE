#!/usr/bin/env python3
# 항공기 외부 결함 검사 드론 -- **물리·수학 근거 있는 검증 시나리오.**
#
# 드론을 나는 것은 우리 제어 정책(3축 PI-SSM)이다. 여기서는 그 정책이 **광학 규격을
# 만족하는 검사 임무를 수행하는가**를 물리로 따진다. 임의값이 아니라 아래 근거로 짓는다.
#
# ── 물리·수학 근거 ────────────────────────────────────────────────────────────
# 1) 항공기: Boeing 737-800 실측 -- 길이 39.5 m, 동체 지름 3.76 m(반경 1.88 m).
#    상부 동체(±70°)를 검사 대상으로 둔다(드론이 위에서 접근하는 영역).
# 2) 카메라 광학 -- 지상표본거리(GSD):
#        GSD = (화소피치 · 거리) / 초점거리 ,   화소피치 = 센서폭 / 화소수
#    검출은 광학 분해능: 결함이 K화소 이상 걸쳐야 보인다 -> 최소검출 = K · GSD (K=3).
#    스와스(훑는 폭) = 2·거리·tan(FOV/2) = 거리 · 센서폭/초점.
#    **핵심: GSD 는 카메라~결함 실제 거리로 정한다** -- 멀수록 GSD 커져 작은 결함을 놓친다.
# 3) 드론 동역학 -- 캐스케이드 제어. 내부 자세·속도 루프가 빠르므로(수백 Hz) 외부 유도
#    루프가 보는 플랜트는 '속도지령->위치'(단일적분기)다. 위치를 PI-SSM 이 추종하고,
#    속도는 v_max 로 포화(모터·안전 한계). 이것이 단일적분기 PI-SSM 의 물리적 정당화.
# 4) 규격 -- 카메라~표면 거리(표준거리)는 [d_min 안전여유, d_max GSD상한] 안이어야 하고,
#    각 결함은 그 지점 거리의 GSD 로 검출 가능(크기 ≥ 3·GSD)해야 한다. 커버리지는 훑은
#    표면 띠(passes × 스와스)를 대상 영역 둘레로 나눈 값.
# ──────────────────────────────────────────────────────────────────────────────
import sys, json, pathlib
import numpy as np

AC = {"이름": "B737-800", "동체길이": 39.5, "동체반경": 1.88,
      "코x": -19.75, "꼬리x": 19.75, "검사각도deg": 70.0}
CAM = {"초점mm": 8.0, "센서폭mm": 6.4, "화소수": 4000, "K화소": 3}
SPEC = {"표준거리_m": 1.5, "d_min_m": 0.8, "d_max_m": 2.5, "v_max_ms": 2.0,
        "커버리지목표pct": 90.0, "패스수": 5}

def GSD_mm(거리_m):          # 지상표본거리[mm]
    return (CAM["센서폭mm"]/CAM["화소수"]) * (거리_m*1000.0) / CAM["초점mm"]
def 스와스_m(거리_m):
    return 거리_m * (CAM["센서폭mm"]/CAM["초점mm"])
def 최소검출_mm(거리_m):
    return CAM["K화소"] * GSD_mm(거리_m)

R = AC["동체반경"]


def _표면(x, deg):
    """동체 표면(반경 R) 위, 검사각도(±70°) 안의 한 점."""
    th = np.deg2rad(deg)
    return [float(x), float(R*np.cos(th)), float(R*np.sin(th))]


# 시나리오: B737-800 상부 동체 결함 검사. 위치·종류·크기·심각도는 실제 검사 유형에서.
# 크기는 표준거리 1.5m 의 최소검출(≈0.9mm)보다 커서 광학적으로 잡히는 것들만 둔다
# (더 작으면 안전거리에서 물리적으로 못 본다 -- 그건 별도 근접검사 문제).
결함들 = [
    {"pos": _표면(-12.0,   0), "종류": "균열",     "크기mm":  2.0, "심각": "높음"},
    {"pos": _표면(  4.0,  45), "종류": "우박눌림",  "크기mm": 20.0, "심각": "중간"},
    {"pos": _표면( -5.0, -50), "종류": "부식",     "크기mm": 40.0, "심각": "낮음"},
    {"pos": _표면( 16.0,  20), "종류": "리벳풀림",  "크기mm":  5.0, "심각": "중간"},
    {"pos": _표면( 10.0,  30), "종류": "도장손상",  "크기mm": 15.0, "심각": "낮음"},
    {"pos": _표면( -8.0, -38), "종류": "파스너풀림", "크기mm":  3.5, "심각": "중간"},
    {"pos": _표면(  7.0,  62), "종류": "번개흔적",  "크기mm": 25.0, "심각": "높음"},
    {"pos": _표면(-15.0,  10), "종류": "패널틈",    "크기mm":  4.0, "심각": "중간"},
    {"pos": _표면(  1.0, -58), "종류": "긁힘",     "크기mm":  8.0, "심각": "낮음"},
    {"pos": _표면( 13.0, -25), "종류": "표면부식",  "크기mm": 30.0, "심각": "중간"},
]


def 검사경로(조밀=1):
    """상부 동체(±검사각도)를 세로 패스로 훑는 serpentine. 표준거리 유지.

    조밀>1 이면 이웃 웨이포인트 사이를 그 배수로 보간해 촘촘하게 만든다. 손 PI 는 큰
    간격도 잘 따라가지만, **학습 Mamba 는 목표가 ±3 안(학습 분포)일 때 정밀**하다 --
    간격이 6m 넘으면 분포 밖이라 표준거리가 흔들린다(실측: 밴드 0.69~4.44m 로 벗어남).
    촘촘히 하면 스텝 오차가 작아 분포 안이라 밴드를 지킨다(실측: 1.06~2.48m 로 통과)."""
    rho = R + SPEC["표준거리_m"]
    각도 = np.deg2rad(np.linspace(-AC["검사각도deg"], AC["검사각도deg"], SPEC["패스수"]))
    x0, x1 = AC["코x"]+3, AC["꼬리x"]-3
    wp = []
    for k, th in enumerate(각도):
        xs = np.linspace(x0, x1, 6)
        if k % 2 == 1: xs = xs[::-1]                 # 지그재그
        for x in xs:
            wp.append([x, rho*np.cos(th), rho*np.sin(th)])
    wp = np.array(wp)
    if 조밀 > 1:
        out = [wp[0]]
        for a, b in zip(wp[:-1], wp[1:]):
            for k in range(1, 조밀+1):
                out.append(a + (b-a)*k/조밀)
        wp = np.array(out)
    return wp


def 표면거리_m(p):
    """동체 표면까지 = 동체축(x)에서 반경거리 − 반경. python float."""
    return float(max(0.05, np.hypot(p[1], p[2]) - R))


def 추종(dt=0.02, Kp=3.2, Ki=1.0, 도달=0.6, 최대T=120.0, 정책=None, 조밀=1):
    """검사 경로를 제어 정책이 따라 난다.

    정책=None 이면 손 PI(베이스라인). 정책이 주어지면 그 스텝 함수가 속도 지령을 낸다
    -- 맘바정책() 을 넣으면 **학습된 신경망 Mamba** 가 실제로 검사 경로를 난다.
    스텝 함수 규약: (오차, 내부상태, dt) -> (속도지령u, 새내부상태, 기록용h[3])."""
    wp = 검사경로(조밀)
    p = np.array(wp[0], dtype=float) + np.array([0.8, 0.0, 0.0])
    h = np.zeros(3); vmax = SPEC["v_max_ms"]; 상태 = None
    이름 = "PI-SSM (베이스라인)" if 정책 is None else getattr(정책, "이름", "학습 정책")
    ts, ps, hs, standoffs, speeds = [], [], [], [], []
    wi, t = 0, 0.0
    for _ in range(int(최대T/dt)):
        목표 = wp[wi]; 오차 = 목표 - p
        if 정책 is None:
            h = h + 오차*dt
            u = Kp*오차 + Ki*h
            hrec = h
        else:
            u, 상태, hrec = 정책(오차, 상태, dt)
        s = np.linalg.norm(u)
        if s > vmax: u = u*(vmax/s)                  # 속도 포화
        p = p + u*dt
        ts.append(round(t,3)); ps.append([round(v,4) for v in p])
        hs.append([round(float(v),4) for v in hrec])
        standoffs.append(round(표면거리_m(p),4)); speeds.append(round(float(np.linalg.norm(u)),4))
        if np.linalg.norm(p-목표) < 도달:
            wi += 1
            if wi >= len(wp): break
        t += dt
    ps_arr = np.array(ps); so_arr = np.array(standoffs)

    # 검출: GSD 는 카메라~결함 실제 거리로
    결함출력 = []
    for d in 결함들:
        dist = np.linalg.norm(ps_arr - np.array(d["pos"]), axis=1)
        j = int(np.argmin(dist)); 봄거리 = float(dist[j])
        gsd = GSD_mm(봄거리); 최소 = 최소검출_mm(봄거리)
        밴드ok = SPEC["d_min_m"] <= 봄거리 <= SPEC["d_max_m"]
        분해능ok = d["크기mm"] >= 최소
        검출 = bool(밴드ok and 분해능ok)
        결함출력.append({**d, "검출idx": j if 검출 else -1, "봄거리_m": round(봄거리,3),
                       "GSD_mm": round(gsd,3), "최소검출_mm": round(최소,3), "검출": 검출})

    검출수 = sum(1 for d in 결함출력 if d["검출"])
    경로길이 = float(np.sum(np.linalg.norm(np.diff(ps_arr,axis=0),axis=1)))
    평균스와 = 스와스_m(float(np.mean(so_arr)))
    대상둘레 = 2*(np.deg2rad(AC["검사각도deg"]))*R          # ±검사각도 호 길이
    커버 = float(min(100.0, SPEC["패스수"]*평균스와/대상둘레*100))
    v_max_meas = float(np.max(speeds)); so_min=float(np.min(so_arr)); so_max=float(np.max(so_arr))
    검증 = {
        "표준거리_밴드": bool(so_min >= SPEC["d_min_m"] and so_max <= SPEC["d_max_m"]),
        "속도_한계": bool(v_max_meas <= SPEC["v_max_ms"]*1.001),
        "결함_전부검출": bool(검출수 == len(결함들)),
        "커버리지_목표": bool(커버 >= SPEC["커버리지목표pct"]),
    }
    지표 = {"스텝": len(ts), "비행시간s": round(ts[-1],1), "웨이포인트수": len(wp),
           "결함수": len(결함들), "검출수": 검출수,
           "표준거리min_m": round(so_min,3), "표준거리max_m": round(so_max,3),
           "GSD표준_mm": round(GSD_mm(SPEC["표준거리_m"]),3), "최소검출표준_mm": round(최소검출_mm(SPEC["표준거리_m"]),3),
           "스와스표준_m": round(스와스_m(SPEC["표준거리_m"]),3),
           "속도max_ms": round(v_max_meas,3), "커버리지pct": round(커버,1), "검증": 검증}
    return {"AC": AC, "CAM": CAM, "SPEC": SPEC, "t": ts, "p": ps, "h": hs,
            "standoff": standoffs, "웨이포인트": wp.tolist(), "결함": 결함출력, "지표": 지표,
            "정책이름": 이름}


def 맘바정책(iters=400):
    """**학습된 신경망 Mamba 정책**의 스텝 함수를 만든다 -- 추종(정책=맘바정책()) 으로 태운다.

    mamba_policy 가 PI 를 모방학습한 그 정책(손 Kp/Ki 아님, 대각 SSM 재귀 + SiLU 게이트)이
    검사 경로를 실제로 난다. 재귀 h=a⊙h+b⊙x 는 ssm/scan_mac 하드웨어에 그대로 매핑되는
    바로 그 재귀다. 관측은 오차(목표-위치), 행동은 속도지령."""
    import ctrl.model.mamba_policy as MP
    P, loss = MP.train(iters=iters)
    a = MP.sig(P["a_raw"])

    def step(오차, 상태, dt):
        h = np.zeros(MP.M) if 상태 is None else 상태
        o = np.asarray(오차, float)
        x = P["W_in"] @ o
        h = a*h + P["b"]*x
        y = P["C"] * h
        gt = MP.silu(P["W_g"] @ o + P["bg"])
        act = P["W_out"] @ (y*gt) + P["D"] @ o          # 신경망 정책의 속도지령
        return act, h, np.array([float(np.linalg.norm(h)), 0.0, 0.0])

    step.이름 = f"학습 신경망 Mamba (모방손실 {loss:.4f})"
    step.모방손실 = float(loss)
    return step


def 추종_맘바(iters=400):
    """학습된 Mamba 정책이 검사 경로를 나는 실측을 낸다(viz 형식 그대로).

    Mamba 는 DT=0.05 로 학습됐으니 그 dt 로 돌리고, 경로를 촘촘히(조밀=5) 해 스텝 오차를
    학습 분포(±3) 안에 둔다 -- 그래야 표준거리 밴드를 지킨다(위 검사경로 주석의 실측)."""
    return 추종(dt=0.05, 정책=맘바정책(iters), 도달=0.35, 최대T=240.0, 조밀=5)


def 요약(r):
    m = r["지표"]; v = m["검증"]
    print(f"== 항공기 결함검사 드론 -- 검증 시나리오 ({r['AC']['이름']}) ==")
    print(f"  카메라 초점 {r['CAM']['초점mm']}mm · 표준거리 {r['SPEC']['표준거리_m']}m"
          f" -> GSD {m['GSD표준_mm']}mm · 최소검출 {m['최소검출표준_mm']}mm · 스와스 {m['스와스표준_m']}m")
    print(f"  비행 {m['비행시간s']}s · 웨이포인트 {m['웨이포인트수']} · 표준거리 {m['표준거리min_m']}~{m['표준거리max_m']}m")
    print(f"  속도 최대 {m['속도max_ms']}m/s(한계 {r['SPEC']['v_max_ms']}) · 커버리지 {m['커버리지pct']}%(목표 {r['SPEC']['커버리지목표pct']})")
    print(f"  결함 {m['검출수']}/{m['결함수']}:")
    for d in r["결함"]:
        print(f"    - {d['종류']:6s} {d['크기mm']:5.1f}mm @거리{d['봄거리_m']}m GSD{d['GSD_mm']}mm 최소검출{d['최소검출_mm']}mm -> {'검출' if d['검출'] else '놓침'}")
    print("  === 검증 규격 ===")
    for k, ok in v.items():
        print(f"    [{'PASS' if ok else 'FAIL'}] {k}")
    성공 = all(v.values())
    print(f"  판정: {'검증 통과 -- 임무 규격 만족' if 성공 else '**규격 불만족**'}")
    return 성공


def 저장(r, 경로="ctrl/model/검사3d.json"):
    ds = 15   # 뷰용 다운샘플(~400스텝)
    r2 = dict(r)
    for k in ("t","p","h","standoff"): r2[k] = r[k][::ds]
    for d in r2["결함"]:
        if d["검출idx"] >= 0: d["검출idx"] = d["검출idx"]//ds
    pathlib.Path(경로).write_text(json.dumps(r2, ensure_ascii=False, separators=(",",":")))
    print(f"  저장: {경로} ({len(r2['t'])}스텝)")
    return r2


if __name__ == "__main__":
    r = 추종()
    성공 = 요약(r)
    if "--저장" in sys.argv: 저장(r)
    sys.exit(0 if 성공 else 1)
