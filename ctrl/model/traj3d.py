#!/usr/bin/env python3
# 3D 궤적 -- 같은 PI-SSM 정책을 **3축 독립**으로 돌려 드론을 3D 웨이포인트로 보낸다.
#
# 축마다 closed_loop.돌리기() 를 그대로 쓴다(검증된 코드 재사용). 바람(외란)은 축별
# 벡터. 각 축의 적분 상태가 자기 축의 바람을 밀어낸다. 3D 는 1D 세 개일 뿐 -- 정책은 같다.
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
import numpy as np
import ctrl.model.closed_loop as C


def 돌리기3d(웨이포인트=(3.0, 2.0, 4.0), 바람=(0.4, 0.0, -0.3), 바람시작=5.0,
            dt=0.02, T=10.0):
    """드론이 원점에서 웨이포인트로. 바람시작(초)부터 상수 바람 벡터. 축별 PI-SSM.
    돌려주는 것: 시간 t, 위치 p[N,3], 축별 지표."""
    축들 = []
    for i in range(3):
        r = C.돌리기(목표=웨이포인트[i], dt=dt, T=T,
                    외란=바람[i], 외란시작=바람시작, p0=0.0)
        축들.append(r)
    t = 축들[0]["t"]
    p = np.stack([축들[i]["p"] for i in range(3)], axis=1)   # [N,3]
    목표 = np.array(웨이포인트)
    # 3D 지표: 목표까지 유클리드 거리
    거리 = np.linalg.norm(p - 목표, axis=1)
    band = 0.02 * np.linalg.norm(목표)
    정착 = None
    이전 = t < 바람시작
    idx = np.where(이전)[0]
    for j in idx:
        if np.all(거리[j:idx[-1]+1] <= band):
            정착 = float(t[j]); break
    바람후 = t >= 바람시작
    지표 = {"정착시간s": 정착,
           "도착거리": round(float(거리[idx[-1]]), 4),
           "바람최대편차": round(float(np.max(거리[바람후])), 4),
           "바람복구잔차": round(float(거리[-1]), 4),
           "웨이포인트": list(웨이포인트), "바람시작": 바람시작}
    return {"t": t, "p": p, "목표": 목표, "지표": 지표}


def 요약(r):
    m = r["지표"]
    print("== 3D 궤적 (축별 PI-SSM) ==")
    print(f"  웨이포인트     : {m['웨이포인트']}")
    print(f"  정착시간(2%)   : {m['정착시간s']} s")
    print(f"  도착 거리      : {m['도착거리']}")
    print(f"  바람({m['바람시작']}s~) 최대편차: {m['바람최대편차']} -> 끝 잔차 {m['바람복구잔차']}")
    band = 0.02 * float(np.linalg.norm(m["웨이포인트"]))   # 2% 상대 밴드(웨이포인트 크기 대비)
    성공 = m["도착거리"] < band and m["바람복구잔차"] < 0.1
    print(f"  판정: {'웨이포인트 도착·바람복구 확인' if 성공 else '**아직 안정 안 됨**'} "
          f"(도착 {m['도착거리']} < 밴드 {band:.3f})")
    return 성공


def 저장(r, 경로="ctrl/model/궤적3d.json"):
    ds = 4  # 다운샘플
    간 = {"t": [round(x, 3) for x in r["t"][::ds].tolist()],
         "p": [[round(v, 4) for v in row] for row in r["p"][::ds].tolist()],
         "목표": [round(v, 3) for v in r["목표"].tolist()],
         "지표": r["지표"]}
    pathlib.Path(경로).write_text(json.dumps(간, ensure_ascii=False))
    print(f"  저장: {경로} ({len(간['t'])} 스텝)")
    return 간


if __name__ == "__main__":
    r = 돌리기3d()
    성공 = 요약(r)
    if "--저장" in sys.argv:
        저장(r)
    sys.exit(0 if 성공 else 1)
