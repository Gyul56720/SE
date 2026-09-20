# -*- coding: utf-8 -*-
"""8b/10b 부호기 블록.  **골든모델은 C++ 이다** -- `edu/proto/enc8b10b.h`.

이 블록이 앞의 것들과 다른 점
------------------------------
  * 골든이 파이썬이 아니라 **컴파일된 C++** 이다.  같은 헤더가 HLS 로도
    갈 수 있고, 무엇보다 **RTL 과 독립**이다 (RTL 은 손으로 따로 썼다).
  * 출력에 **running disparity 를 같이 싣는다.**  안 그러면 RD 상태기계가
    틀려도 코드워드 값이 우연히 맞는 경우를 못 잡는다.  상태가 있는
    블록은 **상태를 관찰 가능하게 만들어야** 회귀가 문다.
  * 자극이 흐름이다.  한 줄의 정답이 앞줄 전체에 달려 있어서, 한 군데만
    어긋나면 그 뒤가 전부 틀린다.
"""
import os
import subprocess
import tempfile

여기 = os.path.dirname(os.path.abspath(__file__))
프로토 = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(여기))), "proto")
이름 = "enc8b10b"
톱 = "tb"
합성톱 = "enc8b10b"

_벌 = [None]          # 컴파일한 골든 생성기를 한 번만 짓는다


def 소스들():
    """[0] 이 DUT 다 -- 수리와 변이는 이 파일만 건드린다."""
    return [os.path.join(프로토, "enc8b10b.v"), os.path.join(여기, "tb.v")]


def _골든벌():
    if _벌[0] and os.path.exists(_벌[0]):
        return _벌[0]
    d = tempfile.mkdtemp(prefix="g8b10b_")
    exe = os.path.join(d, "vec")
    r = subprocess.run(["g++", "-O2", "-I" + 프로토, "-o", exe,
                        os.path.join(프로토, "vec8b10b.cpp")],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("골든모델 컴파일 실패: " + r.stderr[:400])
    _벌[0] = exe
    return exe


def 자극(시행, 씨앗):
    """C++ 골든 생성기를 **실제로 돌려** 자극과 정답을 받는다."""
    n = max(64, 시행)
    r = subprocess.run([_골든벌(), str(n), str(씨앗 or 1)],
                       capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise RuntimeError("골든모델 실행 실패: " + r.stderr[:400])
    줄들, 골든 = [], []
    for l in r.stdout.strip().splitlines():
        d, k, code, rd = l.split()
        줄들.append(f"{d} {k}")
        # tb 가 자극 한 줄마다 **두 줄**을 낸다:
        #   {err, rd, code}  그리고  놀고 있는 사이클의 code_valid (0 이어야 함)
        골든.append((int(rd) << 10) | int(code))
        골든.append(0)
    return 줄들, 골든


def 성능한계(입력줄수):
    """부호기는 한 줄에 한 코드워드다.  테스트벤치가 한 줄에 세 사이클을
    쓴다(자극 두 사이클 + 놀림 한 사이클).  4 배에 리셋 몫을 더해 잡는다.
    넉넉하되 **무한대는 아니다** -- 한계가 없으면 느려지는 결함을 못 잡는다."""
    return 입력줄수 * 4 + 100


관문시행 = 3000
