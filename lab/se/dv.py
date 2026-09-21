# -*- coding: utf-8 -*-
"""09 DV -- UVM 꼴 검증 환경.  T21 의 그림을 실제로 돌린다.

## 왜 파이썬인가

iverilog 는 UVM 을 못 돌린다.  그렇다고 판단(스코어보드)까지 Verilog 로
옮기면 참조모델이 DUT 와 **같은 언어·같은 머릿속**에서 나와 둘이 같이 틀리기
쉽다.  그래서 T21 의 구조를 그대로 두고 언어만 가른다.

    시퀀스 · 시퀀서   여기 (무엇을 할 것인가)
    드라이버          여기 -> 자극 파일 -> tb_dsp.v 가 핀을 흔든다
    가상 인터페이스   tb_dsp.v (유일하게 핀을 아는 자리)
    모니터            여기 <- 응답 파일 (드라이버의 의도가 아니라 **핀**을 읽는다)
    스코어보드        여기 (참조모델은 거래 수준으로 따로 쓴다)
    기능 커버리지     여기

## 스코어보드가 보는 것

한 거래 = start 펄스 하나.  그 뒤 done 이 뜰 때 acc 가 무엇이어야 하나.
**실측으로 확인한 계약**: LOAD 에서 한 번, RUN 여덟 주기에서 여덟 번 더해져서
`9 · a · b` 이고, acc 가 18 비트라 그 위는 **넘친다**.
넘침은 버그가 아니라 설계의 성질이고, 그래서 커버리지 칸으로 둔다.
"""
from __future__ import annotations

import os
import random
import subprocess

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACC폭 = 18
ACC마스크 = (1 << ACC폭) - 1


# ---------------------------------------------------------------------------
class 거래:
    def __init__(self, a, b, 틈, start유지=2):
        """`start유지` 는 start 를 몇 주기 올려 두나.

        기본 2 로는 **레벨과 펄스를 구별하지 못한다** -- FSM 이 IDLE 로
        돌아오기 전에 start 가 이미 내려가 있으므로.  변이검사가 그 구멍을
        실제로 찾아냈다(m3_pulse, 어긋난 거래 0).  그래서 start 를 길게
        붙들어 두는 지시 시험을 따로 둔다.
        """
        self.a, self.b, self.틈, self.start유지 = a, b, 틈, start유지
        self.관측acc = None
        self.관측주기 = None
        self.관측done수 = 0

    def __repr__(self):
        return f"거래(a={self.a}, b={self.b})"


class 시퀀스:
    """무엇을 할 것인가 -- 핀을 모른다."""

    def __init__(self, 씨=5):
        self.r = random.Random(씨)

    def 무작위(self, n=24):
        return [거래(self.r.randrange(256), self.r.randrange(256),
                    self.r.randrange(2, 6)) for _ in range(n)]

    def 지시(self):
        """무작위가 잘 안 닿는 자리를 손으로 -- T21.3 의 그 희귀칸."""
        return [거래(0, 0, 3), 거래(255, 255, 3), 거래(1, 255, 3),
                거래(255, 1, 3), 거래(16, 16, 3), 거래(128, 128, 3)]

    def 긴start(self):
        """**변이검사가 시킨 시험.**  start 를 끝까지 붙들어 둔다.

        m3_pulse(레벨/펄스 바꿔치기)를 잡는 유일한 시험이다.  무작위로는
        영영 안 나온다 -- 드라이버가 start 를 두 주기만 올리기 때문이다.
        희귀칸은 확률이 낮은 것이 아니라 **자극의 모양이 닿지 않는 것**일
        때가 있고, 그때 답은 패턴을 더 도는 것이 아니라 시험을 쓰는 것이다.
        """
        return [거래(7, 9, 4, start유지=20), 거래(3, 5, 4, start유지=26)]


class 드라이버:
    """거래를 핀 흔들기로 바꾼다 -- 이 클래스만 규약의 타이밍을 안다."""

    def 자극(self, 거래들, 리셋주기=3):
        줄 = ["0 0 00 00"] * 리셋주기
        지도 = []
        주기 = 리셋주기
        for t in 거래들:
            유지 = getattr(t, "start유지", 2)
            시작 = 주기
            줄.append(f"1 0 {t.a:02x} {t.b:02x}")      # start 낮게 한 주기
            줄 += [f"1 1 {t.a:02x} {t.b:02x}"] * 유지
            줄.append(f"1 0 {t.a:02x} {t.b:02x}")
            주기 += 2 + 유지
            안 = 12 + t.틈
            줄 += [f"1 0 {t.a:02x} {t.b:02x}"] * 안
            주기 += 안
            지도.append((t, 시작, 주기))
        return "\n".join(줄) + "\n", 지도


class 모니터:
    """**핀만 읽는다.**  드라이버가 무엇을 하려 했는지는 안 본다."""

    def 훑기(self, 응답글):
        줄 = []
        for ln in 응답글.strip().splitlines():
            c, st, acc, done = (int(x) for x in ln.split())
            줄.append({"주기": c, "상태": st, "acc": acc, "done": done})
        return 줄

    def 거래복원(self, 흐름, 지도):
        """done 이 뜬 주기를 찾아 그 거래에 붙인다."""
        done주기 = [r for r in 흐름 if r["done"]]
        for t, s, e in 지도:
            맞 = [r for r in done주기 if s <= r["주기"] < e]
            t.관측done수 = len(맞)          # **몇 번 떴나도 관측값이다**
            if 맞:
                t.관측acc = 맞[0]["acc"]
                t.관측주기 = 맞[0]["주기"] - s
        return 지도


class 참조모델:
    """거래 수준.  RTL 을 줄줄이 베끼지 않는다 -- 그러면 같이 틀린다."""

    def 기대(self, t):
        return (9 * t.a * t.b) & ACC마스크

    def 넘쳤나(self, t):
        return (9 * t.a * t.b) > ACC마스크


class 스코어보드:
    def __init__(self):
        self.본것 = 0
        self.어긋남 = []

    def 견주기(self, 거래들, 모델):
        for t in 거래들:
            if t.관측acc is None:
                self.어긋남.append((t, "done 이 안 떴다", None, None))
                continue
            self.본것 += 1
            기 = 모델.기대(t)
            if t.관측acc != 기:
                self.어긋남.append((t, "acc 가 다르다", 기, t.관측acc))
            # **규약 점검: 거래 하나에 done 은 정확히 한 번.**
            #
            # 이 줄은 변이검사가 시켜서 생겼다.  m3_pulse(레벨/펄스 바꿔치기)를
            # 잡으려고 start 를 길게 붙드는 지시 시험을 더했는데 **그래도 안
            # 잡혔다** -- 값 비교만으로는 못 잡는다.  레벨이면 IDLE 로 돌아오자
            # 마자 다시 걸려서 done 이 여러 번 뜨는데, 첫 done 의 acc 는 맞기
            # 때문이다.  구멍은 자극이 아니라 **검사** 쪽에 있었다.
            if t.관측done수 != 1:
                self.어긋남.append((t, f"done 이 {t.관측done수} 번 떴다 "
                                  "(거래당 한 번이어야 한다)", 1,
                                  t.관측done수))
        return not self.어긋남


class 커버리지:
    """커버그룹 -- **무엇을 해 봤나**.  맞았는지는 스코어보드가 본다."""

    칸 = {
        "a": ["0", "1..15", "16..127", "128..254", "255"],
        "b": ["0", "1..15", "16..127", "128..254", "255"],
        "결과": ["0", "안넘침", "넘침"],
    }

    def __init__(self):
        self.맞은칸 = {k: set() for k in self.칸}
        self.크로스 = set()

    @staticmethod
    def _칸(v):
        if v == 0:
            return "0"
        if v <= 15:
            return "1..15"
        if v <= 127:
            return "16..127"
        if v <= 254:
            return "128..254"
        return "255"

    def 표본(self, t, 모델):
        ka, kb = self._칸(t.a), self._칸(t.b)
        k결 = ("0" if 모델.기대(t) == 0 and not 모델.넘쳤나(t)
               else ("넘침" if 모델.넘쳤나(t) else "안넘침"))
        self.맞은칸["a"].add(ka)
        self.맞은칸["b"].add(kb)
        self.맞은칸["결과"].add(k결)
        self.크로스.add((ka, kb))

    def 요약(self):
        전체크로스 = len(self.칸["a"]) * len(self.칸["b"])
        칸별 = {k: f"{len(self.맞은칸[k])}/{len(v)}"
               for k, v in self.칸.items()}
        덮 = sum(len(self.맞은칸[k]) for k in self.칸)
        총 = sum(len(v) for v in self.칸.values())
        return {
            "커버포인트": 칸별,
            "커버포인트_비": round(덮 / 총, 4),
            "크로스_a_x_b": f"{len(self.크로스)}/{전체크로스}",
            "크로스_비": round(len(self.크로스) / 전체크로스, 4),
            "못채운_크로스": sorted(
                {(x, y) for x in self.칸["a"] for y in self.칸["b"]}
                - self.크로스)[:8],
        }


# ---------------------------------------------------------------------------
class 환경:
    """T21 의 그림 하나가 이 클래스다."""

    def __init__(self, 밖=None, rtl=None, tb=None):
        self.밖 = 밖 or os.path.join(뿌리, "out")
        self.rtl = rtl or os.path.join(뿌리, "rtl", "dsp_top.v")
        self.tb = tb or os.path.join(뿌리, "rtl", "tb_dsp.v")
        os.makedirs(self.밖, exist_ok=True)
        self.드라이버 = 드라이버()
        self.모니터 = 모니터()
        self.모델 = 참조모델()

    def 돌리기(self, 거래들, 꼬리="main"):
        """`꼬리` 는 파일 이름에 들어간다 -- **아스키만 쓴다.**

        실측 2026-09-20: 기본값이 한글("주")이었더니 `vvp` 가
        `*** buffer overflow detected *** : terminated` 로 죽었다.  같은 자극을
        아스키 이름으로 미리 컴파일해 둔 것으로는 591 주기가 멀쩡히 돌았다.
        셸 변수 이름 · Verilog 식별자 · pgrep 패턴에 이어 **네 번째**로 같은
        자리에서 한글이 물었다.
        """
        자극, 지도 = self.드라이버.자극(거래들)
        자극길 = os.path.join(self.밖, f"stim_{꼬리}.txt")
        응답길 = os.path.join(self.밖, f"resp_{꼬리}.txt")
        vvp = os.path.join(self.밖, f"tb_{꼬리}.vvp")
        open(자극길, "w").write(자극)
        r = subprocess.run(["iverilog", "-g2001", "-o", vvp,
                            self.rtl, self.tb, "-s", "tb_dsp"],
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            raise RuntimeError("iverilog 실패:\n" + r.stderr[-2000:])
        r = subprocess.run(["vvp", vvp, f"+stim={자극길}",
                            f"+resp={응답길}"],
                           capture_output=True, text=True, timeout=300,
                           cwd=뿌리)
        if r.returncode != 0:
            raise RuntimeError("vvp 실패:\n" + (r.stderr or r.stdout)[-2000:])
        흐름 = self.모니터.훑기(open(응답길).read())
        self.모니터.거래복원(흐름, 지도)
        return 흐름

    def 회귀(self, 씨=5, 무작위수=24):
        시 = 시퀀스(씨)
        거래들 = 시.무작위(무작위수) + 시.지시() + 시.긴start()
        self.돌리기(거래들)
        sb = 스코어보드()
        cov = 커버리지()
        for t in 거래들:
            cov.표본(t, self.모델)
        통과 = sb.견주기(거래들, self.모델)
        return {
            "거래": len(거래들),
            "스코어보드_본것": sb.본것,
            "어긋남": len(sb.어긋남),
            "통과": 통과,
            "첫어긋남": (f"{sb.어긋남[0][0]} {sb.어긋남[0][1]} "
                     f"기대 {sb.어긋남[0][2]} 관측 {sb.어긋남[0][3]}")
            if sb.어긋남 else None,
            "커버리지": cov.요약(),
        }

    # ------------------------------------------------------------------
    # 뜻은 **영어로** 적는다 -- 이 글자가 영어판 교안(T23)의 표에 그대로
    # 찍히기 때문이다.  한글은 주석과 독스트링에만 둔다.
    변이들 = [
        ("m1_cnt", "if (cnt == 3'd7)", "if (cnt == 3'd6)",
         "RUN one cycle shorter — one accumulate is lost"),
        ("m2_load", "if (st == S_LOAD) acc <= {{2{1'b0}}, prod};",
         "if (st == S_LOAD) acc <= {(2*W+2){1'b0}};",
         "LOAD does not load the product"),
        ("m3_pulse", "wire start_pulse = s2 & ~s3;",
         "wire start_pulse = s2;",
         "level instead of a pulse — start re-triggers"),
        ("m4_done", "S_DONE: begin done <= 1'b1;    st <= S_IDLE; end",
         "S_DONE: begin done <= 1'b0;    st <= S_IDLE; end",
         "done is never asserted"),
        ("m5_prod", "wire [2*W-1:0] prod = a * b;",
         "wire [2*W-1:0] prod = a + b;",
         "sum instead of product"),
    ]

    def 변이검사(self, 무작위수=24):
        """**테스트벤치가 빨개질 수 있는가.**

        회귀는 늘 고쳐진 설계에 대고 도므로 실패 경로를 한 번도 안 탄다.
        일부러 망가뜨려 보고, 무엇이 잡았는지까지 적는다.  아무것도 못 잡은
        변이는 **검사의 구멍**이고 그 자리를 정확히 가리킨다.
        """
        원본 = open(self.rtl, encoding="utf-8").read()
        결과 = []
        for 이름, 옛, 새, 뜻 in self.변이들:
            if 옛 not in 원본:
                결과.append({"변이": 이름, "잡힘": None,
                           "비고": "pattern not found — did the RTL change?"})
                continue
            길 = os.path.join(self.밖, f"dsp_top_{이름}.v")
            open(길, "w", encoding="utf-8").write(원본.replace(옛, 새, 1))
            e = 환경(밖=self.밖, rtl=길, tb=self.tb)
            시 = 시퀀스(5)
            거래들 = 시.무작위(무작위수) + 시.지시() + 시.긴start()
            e.돌리기(거래들, 꼬리=이름)
            sb = 스코어보드()
            통과 = sb.견주기(거래들, e.모델)
            까닭 = [m for _, m, *_ in sb.어긋남]
            잡은것 = ("none" if 통과 else
                    ("done count" if any("번 떴다" in m for m in 까닭) else
                     ("no done" if any("안 떴다" in m for m in 까닭)
                      else "acc compare")))
            결과.append({"변이": 이름, "뜻": 뜻, "잡힘": not 통과,
                       "잡은_검사": 잡은것, "어긋난_거래": len(sb.어긋남)})
        구멍 = [r for r in 결과 if r.get("잡힘") is not True]
        return {"변이": 결과, "구멍": len(구멍),
                "구멍목록": [r["변이"] for r in 구멍]}
