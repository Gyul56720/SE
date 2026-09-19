# -*- coding: utf-8 -*-
"""검증 하니스 -- 파이썬 골든모델과 Verilog DUT 를 **같은 자극으로** 돌려 비교한다.

## 이 하니스가 막으려는 거짓초록

RTL 회귀의 흔한 거짓초록 두 가지를 구조로 막는다.

1. **자극이 DUT 를 안 건드리는 것.**  `잰다()` 는 골든 출력의 **서로 다른 값 수**를
   같이 돌려준다.  전부 같은 값이면 비교가 아무것도 안 본 것이다 -- `agent.py` 가
   그것을 실패로 낸다.
2. **비교가 DUT 를 안 보는 것.**  `자해검사()` 가 DUT 출력을 일부러 망가뜨려
   (비트 하나 뒤집어) 하니스가 **반드시 걸리는지** 먼저 확인한다.  안 걸리면
   그 블록의 회귀 결과는 버린다.

둘 다 이 저장소의 규율 -- *검사하지 않은 초록불이 검사한 빨간불보다 나쁘다* -- 를
기계로 옮긴 것이다.
"""
import os, subprocess, tempfile, shutil, json, time, random

여기 = os.path.dirname(os.path.abspath(__file__))


class 결과:
    성능실패 = None

    def __init__(self, 이름, 시행, 틀림, 서로다른출력, 첫실패, 초, 오류=None):
        self.이름, self.시행, self.틀림 = 이름, 시행, 틀림
        self.서로다른출력, self.첫실패, self.초 = 서로다른출력, 첫실패, 초
        self.오류 = 오류

    @property
    def 쓸모있나(self):
        """출력이 두 가지 이상이라야 비교가 무언가를 본 것이다."""
        return self.오류 is None and self.서로다른출력 >= 2

    def dict(self):
        return {"이름": self.이름, "시행": self.시행, "틀림": self.틀림,
                "서로다른출력": self.서로다른출력, "첫실패": self.첫실패,
                "초": round(self.초, 2), "오류": self.오류,
                "성능실패": self.성능실패, "쓸모있나": self.쓸모있나}


def 컴파일(소스들, 톱, 일터):
    """iverilog 로 컴파일.  실패하면 (None, 메시지)."""
    벌 = os.path.join(일터, "a.out")
    r = subprocess.run(["iverilog", "-g2012", "-o", 벌, "-s", 톱] + 소스들,
                       capture_output=True, text=True)
    if r.returncode:
        return None, (r.stderr or r.stdout)[:2000]
    return 벌, None


def 돌리기(벌, 일터, 입력줄들, 시간제한=120):
    """자극 파일을 넣고 시뮬레이션.  출력은 한 줄에 하나씩 16진수."""
    with open(os.path.join(일터, "stim.txt"), "w") as f:
        f.write("\n".join(입력줄들) + "\n")
    try:
        r = subprocess.run(["vvp", 벌], cwd=일터, capture_output=True,
                           text=True, timeout=시간제한)
    except subprocess.TimeoutExpired:
        return None, "시간초과"
    if r.returncode:
        return None, (r.stderr or r.stdout)[:2000]
    p = os.path.join(일터, "out.txt")
    if not os.path.exists(p):
        return None, "DUT 가 out.txt 를 안 냈다"
    return [l.strip() for l in open(p) if l.strip()], None


def 사이클읽기(일터):
    """테스트벤치가 cycles.txt 를 냈으면 그 수를 돌려준다.  없으면 None."""
    p = os.path.join(일터, "cycles.txt")
    if not os.path.exists(p):
        return None
    try:
        return int(open(p).read().strip().split()[0])
    except Exception:
        return None


def 잰다(블록, 시행=2000, 씨앗=0, 일터=None, 시간제한=120):
    """블록 하나를 회귀한다.

    블록은 다음을 제공하는 모듈이다:
        이름, 소스들(), 톱, 자극(시행, 씨앗) -> (입력줄들, 골든출력들)
    """
    t0 = time.time()
    지움 = False
    if 일터 is None:
        일터 = tempfile.mkdtemp(prefix="vrf_")
        지움 = True
    try:
        벌, 오류 = 컴파일(블록.소스들(), 블록.톱, 일터)
        if 벌 is None:
            return 결과(블록.이름, 0, 0, 0, None, time.time() - t0, "컴파일: " + 오류)
        입력, 골든 = 블록.자극(시행, 씨앗)
        얻은, 오류 = 돌리기(벌, 일터, 입력, 시간제한)
        if 얻은 is None:
            return 결과(블록.이름, 0, 0, 0, None, time.time() - t0, "실행: " + 오류)
        if len(얻은) != len(골든):
            return 결과(블록.이름, len(골든), 0, 0, None, time.time() - t0,
                       f"출력 개수 {len(얻은)} != 자극 {len(골든)}")
        # --- 성능 검사.  값만 보는 회귀는 **느려지는 결함을 못 잡는다**.
        # 실측 2026-09-19: 변이 점수가 `s_ready = ~(m_valid & ~m_ready)` 를
        # `|` 로 바꾼 변이를 **못 잡았다** -- 값은 전부 맞고 처리량만 떨어진다.
        # 블록이 `성능한계(입력수)` 를 주면 여기서 잰다.
        성능말 = None
        if hasattr(블록, "성능한계"):
            사이클 = 사이클읽기(일터)
            if 사이클 is None:
                성능말 = "성능한계를 선언했는데 테스트벤치가 cycles.txt 를 안 냈다"
            else:
                한계 = 블록.성능한계(len(입력))
                if 사이클 > 한계:
                    성능말 = f"사이클 {사이클} > 한계 {한계}"
        틀림, 첫 = 0, None
        for i, (a, b) in enumerate(zip(얻은, 골든)):
            if int(a, 16) != b:
                틀림 += 1
                if 첫 is None:
                    첫 = {"i": i, "입력": 입력[i], "골든": f"{b:x}", "DUT": a}
        r = 결과(블록.이름, len(골든), 틀림, len(set(골든)), 첫,
                 time.time() - t0)
        if 성능말:
            r.성능실패 = 성능말
            if 틀림 == 0:
                r.틀림 = 1      # 성능 위반도 빨간불이다
                r.첫실패 = {"i": -1, "입력": "(성능)", "골든": "-", "DUT": 성능말}
        return r
    finally:
        if 지움:
            shutil.rmtree(일터, ignore_errors=True)


def 자해검사(블록, 시행=200, 씨앗=999, 시간제한=120):
    """골든 출력을 **일부러 한 비트 뒤집어** 하니스가 걸리는지 본다.

    여기서 안 걸리면 그 블록의 초록불은 아무 뜻이 없다.
    """
    t0 = time.time()
    일터 = tempfile.mkdtemp(prefix="vrf_self_")
    try:
        벌, 오류 = 컴파일(블록.소스들(), 블록.톱, 일터)
        if 벌 is None:
            return False, "컴파일: " + 오류
        입력, 골든 = 블록.자극(시행, 씨앗)
        얻은, 오류 = 돌리기(벌, 일터, 입력, 시간제한)
        if 얻은 is None:
            return False, "실행: " + 오류
        if len(얻은) != len(골든):
            return False, "출력 개수 불일치"
        # 성한 상태에서 먼저 0 틀림이라야 한다
        기본틀림 = sum(1 for a, b in zip(얻은, 골든) if int(a, 16) != b)
        if 기본틀림:
            return False, f"성한 상태에서 이미 {기본틀림} 개 틀림"
        # 이제 골든을 망가뜨린다
        망친 = list(골든)
        망친[len(망친) // 2] ^= 1
        걸린 = sum(1 for a, b in zip(얻은, 망친) if int(a, 16) != b)
        if 걸린 != 1:
            return False, f"골든을 한 개 망쳤는데 {걸린} 개가 걸렸다 -- 비교가 이상하다"
        return True, None
    finally:
        shutil.rmtree(일터, ignore_errors=True)


def 좁히기(블록, 첫실패, 씨앗, 최대=40):
    """실패한 자극 하나를 **그 하나만으로** 재현해 최소 사례를 만든다.

    조합회로 블록에서는 입력 한 줄이 곧 최소 사례이므로 재현 확인이 곧 좁히기다.
    순차 블록에서는 이 함수를 블록이 덮어쓴다.
    """
    if 첫실패 is None:
        return None
    일터 = tempfile.mkdtemp(prefix="vrf_min_")
    try:
        벌, 오류 = 컴파일(블록.소스들(), 블록.톱, 일터)
        if 벌 is None:
            return None
        얻은, 오류 = 돌리기(벌, 일터, [첫실패["입력"]])
        if 얻은 is None or not 얻은:
            return None
        return {"입력": 첫실패["입력"], "골든": 첫실패["골든"],
                "DUT": 얻은[0], "재현됨": int(얻은[0], 16) != int(첫실패["골든"], 16)}
    finally:
        shutil.rmtree(일터, ignore_errors=True)
