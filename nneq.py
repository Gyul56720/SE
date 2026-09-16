"""신경망 등화기. **선형 등화기가 못 푸는 것만 이겨야 한다.**

사용자가 고른 주제의 3단계: "신경망 등화기 설계 -> floating point 로 먼저 학습해
상한 성능 확인". 4단계(양자화·프루닝)가 이 위에 선다.

## 먼저 못 박을 것 -- 선형 채널에서 이기면 그건 구멍이다

선형 채널 + AWGN 에서는 **최적 등화기가 선형이다**(MMSE-DFE). 거기에 신경망을
얹으면 잘해야 비긴다. 이기면 물리가 아니라 새는 데가 있는 것이다 --
학습 비트로 재고 있거나, 판정 되먹임에 정답이 섞였거나.

그래서 이 모듈의 첫 검사는 **"압축 없는 채널에서 선형을 못 이긴다"** 이다.
이기면 빨간불이다. 거짓 초록을 막는 자리가 여기다.

## 신경망이 할 일이 있는 자리

`serdes.압축하기` 가 수신 앞단 압축을 넣는다. 선형 역연산이 없으므로 FFE·DFE·CTLE
로는 못 되돌린다. 실측 2026-09-16 (25dB, SNR 30dB, FFE11+DFE8):

    압축 0.0  BER 7.67e-04      압축 1.5  BER 5.70e-02
    압축 0.5  BER 1.85e-03      압축 2.0  BER 8.29e-02
    압축 1.0  BER 2.38e-02      압축 3.0  BER 1.14e-01

## 규율은 그대로다

  · 학습은 앞 `학습비율` 만, BER 은 나머지에서만 센다
  · DFE 되먹임은 **제 판정**이다(정답을 먹이면 오류 번짐이 사라진다)
  · 씨 하나로 결론을 말하지 않는다
  · 안 수렴하면 안 수렴했다고 말한다 -- 나쁜 BER 로 조용히 넘어가지 않는다
"""
from __future__ import annotations

import numpy as np

import serdes

PASS, FAIL, 못잼 = serdes.PASS, serdes.FAIL, serdes.못잼


def 창만들기(표본: np.ndarray, 앞뒤: int) -> np.ndarray:
    """각 심볼마다 앞뒤 `앞뒤` 개를 붙인 (N, 2*앞뒤+1) 행렬. 가장자리는 0 으로 채운다."""
    n, 폭 = len(표본), 2 * int(앞뒤) + 1
    채운 = np.concatenate([np.zeros(앞뒤), 표본, np.zeros(앞뒤)])
    X = np.empty((n, 폭))
    for j in range(폭):
        X[:, j] = 채운[j:j + n]
    return X


def 짓기(입력수: int, 은닉수: int, 씨: int = 0) -> dict:
    """He 초기화. 층 하나(tanh) + 선형 출력."""
    rng = np.random.default_rng(씨)
    return {"W1": rng.normal(0, np.sqrt(2.0 / 입력수), (입력수, 은닉수)),
            "b1": np.zeros(은닉수),
            "W2": rng.normal(0, np.sqrt(2.0 / 은닉수), (은닉수, 1)),
            "b2": np.zeros(1)}


def 파라미터수(모: dict) -> int:
    return int(sum(v.size for v in 모.values()))


def 앞먹임(모: dict, X: np.ndarray):
    h = np.tanh(X @ 모["W1"] + 모["b1"])
    return h, (h @ 모["W2"] + 모["b2"]).ravel()


def 예측(모: dict, X: np.ndarray) -> np.ndarray:
    return 앞먹임(모, X)[1]


def 학습(모: dict, X: np.ndarray, d: np.ndarray, 걸음: float = 3e-3,
       에폭: int = 12, 배치: int = 256, 씨: int = 0) -> dict:
    """Adam 으로 MSE 를 줄인다. **수렴했는지 같이 낸다.**

    끝 MSE 가 시작보다 안 줄었으면 안 수렴한 것이다. 그때 BER 이 나쁜 것은
    등화기 성능이 아니라 학습 실패이고, 둘을 섞으면 "신경망이 안 된다" 는
    틀린 결론이 나온다.
    """
    rng = np.random.default_rng(씨)
    m = {k: np.zeros_like(v) for k, v in 모.items()}
    v = {k: np.zeros_like(x) for k, x in 모.items()}
    b1, b2, eps, t = 0.9, 0.999, 1e-8, 0
    n = len(X)
    처음MSE, 끝MSE = None, None
    for _ in range(int(에폭)):
        차례 = rng.permutation(n)
        모은것 = []
        for i in range(0, n, int(배치)):
            골 = 차례[i:i + int(배치)]
            xb, db = X[골], d[골]
            h, y = 앞먹임(모, xb)
            e = y - db
            모은것.append(float(np.mean(e ** 2)))
            g = {}
            g["W2"] = h.T @ e[:, None] / len(골)
            g["b2"] = np.array([float(np.mean(e))])
            뒤 = (e[:, None] @ 모["W2"].T) * (1.0 - h ** 2)
            g["W1"] = xb.T @ 뒤 / len(골)
            g["b1"] = 뒤.mean(axis=0)
            t += 1
            for k in 모:
                m[k] = b1 * m[k] + (1 - b1) * g[k]
                v[k] = b2 * v[k] + (1 - b2) * g[k] ** 2
                모[k] -= 걸음 * (m[k] / (1 - b1 ** t)) / (np.sqrt(v[k] / (1 - b2 ** t)) + eps)
        if 처음MSE is None:
            처음MSE = 모은것[0]
        끝MSE = float(np.mean(모은것[-max(1, len(모은것) // 5):]))
    수렴 = (끝MSE is not None and np.isfinite(끝MSE) and 끝MSE < 처음MSE)
    return {"모": 모, "처음MSE": 처음MSE, "끝MSE": 끝MSE, "수렴": bool(수렴),
            "왜": (f"MSE {처음MSE:.4f} -> {끝MSE:.4f}" if 수렴 else
                  f"**안 수렴했다** MSE {처음MSE:.4f} -> {끝MSE:.4f} -- "
                  "걸음이나 에폭을 고쳐라. 이 BER 은 등화기 성능이 아니다")}


def 가중치양자화(모: dict, 비트: int) -> dict:
    """층마다 따로 최댓값 스케일로 자른다. `serdes.양자화` 와 같은 규칙이다."""
    if not 비트 or 비트 <= 0:
        return 모
    return {k: serdes.양자화(v, int(비트)) for k, v in 모.items()}


def 가중치프루닝(모: dict, 남길비율: float) -> dict:
    """작은 가중치부터 0 으로. 편향은 건드리지 않는다(개수가 적고 값이 크다)."""
    if 남길비율 >= 1.0:
        return 모
    난것 = dict(모)
    for k in ("W1", "W2"):
        난것[k] = serdes.프루닝(모[k].ravel(), 남길비율).reshape(모[k].shape)
    return 난것


def 링크(비트수: int = 300000, 손실dB: float = 25.0, SNRdB: float = 30.0,
       압축: float = 0.0, sps: int = 8, 앞뒤: int = 10, 은닉수: int = 16,
       DFE탭: int = 0, DFE자리=None, 이상적판정: bool = False,
       가중치비트: int = 0, 남길비율: float = 1.0,
       에폭: int = 12, 걸음: float = 3e-3, 학습비율: float = 0.3,
       ADC비트: int = 0, ADC풀스케일시그마: float = 2.5, 반사=(), 씨: int = 0) -> dict:
    """신경망 등화기로 링크를 돌린다. {BER, 오류수, 잰비트, 파라미터수, 학습, 왜}.

    `serdes.링크` 로 **정렬·AGC·ADC 까지 끝난 표본**을 받아 그 위에 신경망을 얹는다.
    선형 등화(FFE)는 끄고 신경망이 그 자리를 맡는다. `DFE탭`/`DFE자리` 를 주면
    신경망 출력 뒤에 판정 되먹임을 붙인다(되먹이는 것은 **제 판정**이다).
    """
    밑 = serdes.링크(비트수=int(비트수), 손실dB=손실dB, SNRdB=SNRdB, sps=int(sps),
                   FFE탭=0, DFE탭=0, 반사=반사, 압축=압축, ADC비트=int(ADC비트),
                   ADC풀스케일시그마=ADC풀스케일시그마, 학습비율=학습비율, 씨=int(씨))
    표본, 비트 = 밑["표본"], 밑["비트"].astype(float)
    학습끝 = int(np.clip(len(표본) * 학습비율, 1, len(표본) - 1))
    X = 창만들기(표본, int(앞뒤))
    모 = 짓기(X.shape[1], int(은닉수), 씨=int(씨))
    r = 학습(모, X[:학습끝], 비트[:학습끝], 걸음=걸음, 에폭=int(에폭), 씨=int(씨))
    모 = r["모"]
    if 가중치비트:
        모 = 가중치양자화(모, int(가중치비트))
    if 남길비율 < 1.0:
        모 = 가중치프루닝(모, 남길비율)

    y = 예측(모, X)
    # 신경망 출력을 메인 커서 이득으로 정규화한다 -- DFE 탭이 읽을 수 있는 값이 되게
    g = float(np.mean(y[:학습끝] * 비트[:학습끝])) or 1.0
    y = y / g
    자리들 = ([int(x) for x in DFE자리 if int(x) > 0] if DFE자리
            else list(range(1, int(DFE탭) + 1)))
    자리들 = sorted(set(자리들))
    탭 = None
    if 자리들:
        탭 = np.array([float(np.mean(y[:학습끝][m:] * 비트[:학습끝][:-m] if m else 0.0))
                     if m < 학습끝 else 0.0 for m in 자리들])
        if 가중치비트:
            탭 = serdes.양자화(탭, int(가중치비트))
    # **되먹이는 것은 제 판정이다.** `이상적판정` 은 그것을 일부러 깨는 손잡이이고,
    # 그 차이가 오류 번짐의 크기다 -- 하드웨어는 정답을 모른다.
    판정 = serdes._슬라이스(y, 탭, 비트 if 이상적판정 else None, 자리들)

    잰것 = slice(학습끝, len(판정))
    오류 = int(np.sum(판정[잰것] != 비트[잰것]))
    잰비트 = int(잰것.stop - 잰것.start)
    return {"BER": (오류 / 잰비트) if 잰비트 else float("nan"),
            "오류수": 오류, "잰비트": 잰비트, "파라미터수": 파라미터수(모),
            "학습": {k: v for k, v in r.items() if k != "모"}, "모": 모,
            "DFE자리": 자리들, "압축": 압축, "이상적판정": bool(이상적판정),
            "판정": PASS if r["수렴"] else 못잼,
            "왜": (serdes.BER말(오류, 잰비트) if r["수렴"] else r["왜"])}


def 말로(r: dict) -> str:
    줄 = [f"NN equaliser: {r['왜']}",
         f"params {r['파라미터수']:,} · training {r['학습']['왜']}"]
    if r.get("DFE자리"):
        줄.append("DFE after the net @" + ",".join(str(m) for m in r["DFE자리"]))
    if r.get("이상적판정"):
        줄.append("**ideal-decision DFE — hides error propagation; hardware does not "
                  "know the answer**")
    if r.get("압축"):
        줄.append(f"RX compression {r['압축']:.1f} (linear equalisers cannot invert this)")
    return "\n".join(줄)
