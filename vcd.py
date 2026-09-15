"""VCD 를 읽어 **파형을 그린다.** 그리고 x/z 를 0 으로 그리지 않는다.

사용자(2026-09-15): 남은 구멍 중 첫째가 파형 보기였다.

## 왜 있나 -- 통과했다는 말만으로는 안에서 무슨 일이 났는지 모른다

`rtl.py` 가 PASS/FAIL 을 내 주지만, **왜** 틀렸는지는 파형을 봐야 안다. 그것이
디지털 설계에서 사람이 실제로 하는 일이다.

## x 를 0 으로 그리면 깨진 것이 깨끗해 보인다 -- 실측 2026-09-15

테스트벤치에서 `rst_n` 과 `en` 을 **초기화하지 않고** 돌렸다.

    x$          <- rst_n 이 전 구간 x
    x#          <- en 이 전 구간 x
    bx !        <- q 가 전 구간 x
    PASS
    끝값=0

설계는 한 번도 안 돌았는데 벤치는 PASS 를 찍었다. 이때 파형에서 x 를 0(거짓)으로
칠하면 **가지런한 낮은 선**이 보인다 -- 사용자는 그것을 보고 "리셋이 잘 걸렸다" 고
읽는다. 그래서 여기서는

1. x/z 를 **눈에 띄게 따로 칠하고**(빗금 친 빨간 띠),
2. 그림만 믿게 두지 않고 **글로도 센다** -- "전 구간 x 인 신호: rst_n, en, q".

그림은 오해할 수 있어도 한 줄 글은 못 오해한다.

## `$dumpvars` 가 없으면 파형이 아예 없다

그것도 끝값 0 이고 PASS 다(실측). 없는 것을 "파형 없음" 이라고 조용히 넘기면
사용자는 왜 그림이 안 왔는지 모른다. 그래서 **덤프 블록을 끼워 넣고 끼웠다고 말한다.**
"""
from __future__ import annotations

import os
import re

x자 = "xzXZ"


def 덤프있나(글: str) -> bool:
    return bool(re.search(r"\$dumpfile\s*\(", 글 or ""))


def 덤프끼우기(테스트벤치: str, top: str, 파일: str = "wave.vcd") -> "tuple[str, bool]":
    """`$dumpfile` 이 없으면 마지막 `endmodule` 앞에 덤프 블록을 끼운다.

    (바뀐 글, 끼웠나). **끼웠으면 부르는 쪽이 그렇게 말해야 한다** -- 남의 코드를
    조용히 고쳐 놓고 결과만 보이면 그 결과가 무엇의 결과인지 알 수 없다.
    """
    글 = 테스트벤치 or ""
    if 덤프있나(글):
        return 글, False
    i = 글.rfind("endmodule")
    if i < 0:
        return 글, False
    끼움 = (f'\ninitial begin\n  $dumpfile("{파일}");\n'
          f'  $dumpvars(0, {top});\nend\n')
    return 글[:i] + 끼움 + 글[i:], True


def 읽기(경로: str) -> dict:
    """VCD 를 읽는다. {신호: [(이름, 폭, 열쇠)], 바뀜: {열쇠: [(시각, 값)]}, 끝시각, 눈금}."""
    신호, 바뀜, 이름들 = [], {}, {}
    눈금, 시각, 머리 = "1ns", 0, True
    범위, 눈금기다림 = [], False
    with open(경로, encoding="utf-8", errors="replace") as f:
        for 줄 in f:
            줄 = 줄.strip()
            if not 줄:
                continue
            if 머리:
                if 줄.startswith("$timescale"):
                    # **값이 다음 줄에 올 수 있다.** Icarus 가 그렇게 쓴다(실측 2026-09-15):
                    #     $timescale \n \t 1ps \n $end
                    # 한 줄로만 찾으면 기본값 1ns 가 남아 **시간축이 1000배 어긋난다.**
                    m = re.search(r"\$timescale\s+(\S+)", 줄)
                    if m:
                        눈금 = m.group(1)
                    else:
                        눈금기다림 = True
                    continue
                if 눈금기다림:
                    if 줄 != "$end":
                        눈금 = 줄.split()[0]
                    눈금기다림 = False
                    continue
                if 줄.startswith("$scope"):
                    조각 = 줄.split()
                    if len(조각) >= 3:
                        범위.append(조각[2])
                    continue
                if 줄.startswith("$upscope"):
                    if 범위:
                        범위.pop()
                    continue
                if 줄.startswith("$var"):
                    # $var wire 4 ! q [3:0] $end
                    조각 = 줄.split()
                    if len(조각) >= 5:
                        갈래, 폭, 열쇠, 이름 = 조각[1], int(조각[2]), 조각[3], 조각[4]
                        # **파라미터는 파형이 아니다.** 늘 한 값이라 "안 변한다" 칸만 채운다.
                        if 갈래 == "parameter":
                            continue
                        온이름 = ".".join(범위 + [이름]) if 범위 else 이름
                        if 열쇠 not in 이름들:      # 같은 열쇠를 여러 이름이 나눠 쓴다
                            이름들[열쇠] = 온이름
                            신호.append((온이름, 폭, 열쇠))
                    continue
                if 줄.startswith("$enddefinitions"):
                    머리 = False
                    continue
                if 줄 == "$timescale":
                    continue
                continue
            if 줄.startswith("#"):
                try:
                    시각 = int(줄[1:])
                except ValueError:
                    pass
                continue
            if 줄.startswith(("$dumpvars", "$dumpall", "$dumpon", "$dumpoff", "$end",
                              "$comment")):
                continue
            if 줄[0] in "bB":                      # 여러 비트: `b1010 !`
                조각 = 줄.split()
                if len(조각) == 2:
                    바뀜.setdefault(조각[1], []).append((시각, 조각[0][1:]))
            elif 줄[0] in "rR":                     # 실수
                조각 = 줄.split()
                if len(조각) == 2:
                    바뀜.setdefault(조각[1], []).append((시각, 조각[0][1:]))
            else:                                   # 한 비트: `0!` `x$`
                값, 열쇠 = 줄[0], 줄[1:].strip()
                if 열쇠:
                    바뀜.setdefault(열쇠, []).append((시각, 값))
    끝 = max((v[-1][0] for v in 바뀜.values() if v), default=시각)
    return {"신호": 신호, "바뀜": 바뀜, "끝시각": max(끝, 시각), "눈금": 눈금}


def 헤아리기(잰것: dict) -> dict:
    """**글로 센다.** 그림은 오해할 수 있어도 이 줄은 못 오해한다."""
    바뀜 = 잰것["바뀜"]
    죽은것, 안변한것, 살아있는것 = [], [], 0
    for 이름, 폭, 열쇠 in 잰것["신호"]:
        값들 = 바뀜.get(열쇠) or []
        if not 값들:
            안변한것.append(이름)
            continue
        보인값 = [v for _, v in 값들]
        if all(any(c in x자 for c in v) for v in 보인값):
            죽은것.append(이름)               # 전 구간 x/z -- **이게 거짓 초록의 자리다**
        elif len(set(보인값)) <= 1:
            안변한것.append(이름)
        else:
            살아있는것 += 1
    return {"신호수": len(잰것["신호"]), "움직인것": 살아있는것,
            "전구간xz": 죽은것, "안변한것": 안변한것,
            "끝시각": 잰것["끝시각"], "눈금": 잰것["눈금"]}


def 말로(셈: dict) -> str:
    줄 = [f"signals {셈['신호수']} · toggling {셈['움직인것']} · "
         f"span {셈['끝시각']} {셈['눈금']}"]
    if 셈["전구간xz"]:
        줄.append("**x/z for the WHOLE run** (the design never really ran): "
                  + ", ".join(셈["전구간xz"][:12]))
    if 셈["안변한것"]:
        줄.append("never toggles: " + ", ".join(셈["안변한것"][:12]))
    return "\n".join(줄)


def 그리기(경로: str, 낼곳: str, 고를것="", 최대: int = 14) -> dict:
    """파형을 PNG 로. {그렸나, 경로, 셈, 왜}."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
    except Exception as e:                                          # noqa: BLE001
        return {"그렸나": False, "왜": f"matplotlib 이 없다: {e}", "셈": {}}
    if not os.path.exists(경로):
        return {"그렸나": False, "왜": "VCD 파일이 없다 -- 테스트벤치에 `$dumpfile` 이 있나",
                "셈": {}}
    잰것 = 읽기(경로)
    셈 = 헤아리기(잰것)
    if not 잰것["신호"]:
        return {"그렸나": False, "왜": "VCD 에 신호가 하나도 없다", "셈": 셈}

    고름 = [s.strip() for s in (고를것 or "").replace(",", " ").split() if s.strip()]
    신호 = 잰것["신호"]
    if 고름:
        신호 = [s for s in 신호 if any(g == s[0] or s[0].endswith("." + g) or g in s[0]
                                    for g in 고름)] or 신호
    # **같은 net 이 계층마다 또 나온다** -- `tb.q` 와 `tb.dut.q` 는 한 선인데 VCD 열쇠가
    # 다르다(실측: 카운터 파형에 `q[3:0]` 이 두 줄로 찍혔다). 짧은 이름만 보고 지우면
    # 서로 다른 모듈의 동명이인(`u1.q` · `u2.q`)까지 지워 **신호가 사라진다.** 그래서
    # **값의 흐름까지 같을 때만** 한 줄로 합치고, 이름만 겹치면 긴 이름을 그대로 쓴다.
    본것, 신호2 = {}, []
    for 이름, 폭, 열쇠 in 신호:
        짧 = 이름.split(".")[-1]
        자취 = tuple(sorted(잰것["바뀜"].get(열쇠) or []))
        도장 = (짧, 폭, 자취)
        if 도장 in 본것:
            continue
        본것[도장] = 이름
        신호2.append((이름, 짧, 폭, 열쇠))
    겹침 = {}
    for _, 짧, _, _ in 신호2:
        겹침[짧] = 겹침.get(짧, 0) + 1
    신호 = [((짧 if 겹침[짧] == 1 else 온), 폭, 열쇠) for 온, 짧, 폭, 열쇠 in 신호2][:최대]

    끝 = max(잰것["끝시각"], 1)
    fig, ax = plt.subplots(figsize=(11, 0.55 * len(신호) + 1.1))
    for 층, (이름, 폭, 열쇠) in enumerate(신호):
        y = len(신호) - 1 - 층
        값들 = sorted(잰것["바뀜"].get(열쇠) or [])
        if not 값들:
            값들 = [(0, "x")]
        토막 = [(값들[i][0], (값들[i + 1][0] if i + 1 < len(값들) else 끝), 값들[i][1])
              for i in range(len(값들))]
        for 처음, 끝점, 값 in 토막:
            if 끝점 <= 처음:
                continue
            깨짐 = any(c in x자 for c in 값)
            if 깨짐:
                # **x/z 는 0 으로 안 그린다.** 빗금 친 빨간 띠로 따로 보인다.
                ax.add_patch(Rectangle((처음, y + 0.12), 끝점 - 처음, 0.66,
                                       facecolor="#d62728", alpha=0.35,
                                       hatch="///", edgecolor="#d62728", lw=0.8))
                ax.text((처음 + 끝점) / 2, y + 0.45, "x", ha="center", va="center",
                        fontsize=8, color="#7a0000", weight="bold")
            elif 폭 == 1:
                높이 = y + 0.78 if 값 == "1" else y + 0.12
                ax.plot([처음, 끝점], [높이, 높이], color="#1f77b4", lw=1.7)
                ax.plot([처음, 처음], [y + 0.12, y + 0.78], color="#1f77b4", lw=1.0)
            else:
                ax.add_patch(Rectangle((처음, y + 0.12), 끝점 - 처음, 0.66,
                                       facecolor="#dbe9f6", edgecolor="#1f77b4", lw=1.0))
                try:
                    글 = f"{int(값, 2):X}"
                except ValueError:
                    글 = 값
                if (끝점 - 처음) / 끝 > 0.035:
                    ax.text((처음 + 끝점) / 2, y + 0.45, 글, ha="center", va="center",
                            fontsize=8, color="#123")
        ax.axhline(y, color="#e8e8e8", lw=0.6, zorder=0)
    ax.set_yticks([len(신호) - 1 - i + 0.45 for i in range(len(신호))])
    ax.set_yticklabels([f"{n}[{w-1}:0]" if w > 1 else n for n, w, _ in 신호], fontsize=9)
    ax.set_xlim(0, 끝)
    ax.set_ylim(0, len(신호))
    ax.set_xlabel(f"time ({잰것['눈금']})", fontsize=9)
    머리 = f"{len(신호)} signals"
    if 셈["전구간xz"]:
        머리 += f"  —  {len(셈['전구간xz'])} x/z for the whole run"
    ax.set_title(머리, fontsize=10)
    for 쪽 in ("top", "right", "left"):
        ax.spines[쪽].set_visible(False)
    fig.tight_layout()
    os.makedirs(os.path.dirname(낼곳) or ".", exist_ok=True)
    fig.savefig(낼곳, dpi=130)
    plt.close(fig)
    if not os.path.exists(낼곳) or os.path.getsize(낼곳) < 1000:
        return {"그렸나": False, "왜": "PNG 가 안 만들어졌거나 너무 작다", "셈": 셈}
    return {"그렸나": True, "경로": 낼곳, "셈": 셈, "왜": 말로(셈)}
