"""**sky130 PDK 를 스스로 받아 온다** -- 사람에게 설치를 시키지 않는다.

`afe.py` 는 손계산이다. 그 계산이 맞는지 보려면 **진짜 소자 모델**로 돌려 봐야 하고,
열려 있는 것이 SkyWater sky130 이다. 그런데 이 환경은 GitHub 도 apt 도 막혀 있다.

## 그런데 **PyPI 는 열려 있고, 거기에 모델이 통째로 있다**

`sky130` 휠(38 MB) 안에 `sky130_fd_pr` 의 BSIM4 모델 카드와 코너 파일(tt·ff·ss·fs·sf)이
그대로 들어 있다. 파일 머리말이 대놓고 이렇게 적어 놓았다:

    This file is for use by ngspice using the ".lib" statement

**파이썬 패키지를 설치하지는 않는다.** 그쪽 의존성(gdsfactory -> rectpack)이 이 기계에서
빌드에 실패한다. 필요한 것은 `.spice` 파일뿐이므로 **휠을 풀어 쓴다.**

## 왜 최소 집합만 푸나

전체 129 MB 를 푼다. 골라 풀어 34.5 MB 로 줄여 봤더니 코너 파일이 참조하는
셀이 빠져 ngspice 가 include 오류를 뱉었다 -- **오류를 뱉으며 도는 것은 도는 것이
아니다**. 커밋하지 않으므로(캐시) 저장소 크기와는 무관하다.

## 없을 때

`받기()` 가 pip 로 휠을 받아 푼다. 그것도 막힌 기계라면 `왜` 에 **사람이 직접 하는
방법**을 적어 돌려준다. 이 저장소의 규칙("사람에게 설치를 시키지 마라")은 **자동으로
될 수 있는 것을 시키지 마라**는 뜻이지, 정말 막혔을 때 침묵하라는 뜻이 아니다.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import zipfile

이름 = "sky130"
집 = os.environ.get("SE_PDK_ROOT") or os.path.join(
    os.path.expanduser("~"), ".cache", "se-pdk")
_안쪽 = os.path.join("sky130", "src", "sky130_fd_pr")
_lib상대 = os.path.join(_안쪽, "combined_models", "sky130.lib.spice")

손으로 = (
    "직접 하려면 (셋 중 아무거나):\n"
    "  1) pip download sky130 하고 휠을 풀어 "
    "sky130/src/sky130_fd_pr/combined_models/sky130.lib.spice 를 쓴다\n"
    "  2) apt/brew 로 ngspice 를 깔고 open_pdks 로 sky130 을 빌드한다 "
    "(github.com/RTimothyEdwards/open_pdks)\n"
    "  3) pip install volare && volare enable --pdk sky130 <버전>\n"
    "받은 뒤 `SE_PDK_ROOT=<푼 자리>` 를 환경 변수로 두면 이 모듈이 그것을 쓴다.")


def _필요한가(n: str) -> bool:
    """`sky130_fd_pr` 을 통째로 푼다(129 MB).

    처음에는 쓰는 셀만 골라 34.5 MB 로 줄였다. **그랬더니 ngspice 가 include 를
    못 찾는다고 다섯 줄을 뱉었다** -- 코너 파일이 우리가 안 쓰는 셀(special_nfet ·
    cap_vpp 여러 개)을 참조한다. 시뮬레이션은 그래도 돌았지만, **오류를 뱉으면서
    도는 것은 도는 것이 아니다** -- 다음에 진짜 오류가 나도 묻힌다.

    129 MB 는 캐시에 두는 값으로 충분히 싸다. 커밋하지 않으므로 저장소는 안 는다.
    """
    if n.startswith(_안쪽.replace(os.sep, "/") + "/"):
        return True
    return _표준셀필요한가(n)


# **표준셀도 같은 휠 안에 있다** -- `sky130_fd_sc_hd` 7,582 파일.
# 그중 두 가지만 푼다(합쳐 2.8 MB):
#   .lef    셀마다 `SIZE w BY h` -- **실제 면적**이 여기 있다
#   .spice  셀마다 트랜지스터 넷리스트 -- **소자 수**를 셀 수 있다
# 위의 `sky130_fd_pr` 은 통째로 풀어야 했다(코너 파일이 안 쓰는 셀을 include 한다).
# 여기는 다르다 -- 이 파일들은 서로를 참조하지 않고 **내 파서가 직접 읽는 자료**라
# 골라 풀어도 아무것도 안 깨진다. 그래서 이유가 다르면 판단도 다르다.
_표준셀 = "sky130/src/sky130_fd_sc_hd"


def _표준셀필요한가(n: str) -> bool:
    if not n.startswith(_표준셀 + "/"):
        return False
    if n.endswith(".spice"):
        return True
    return n.endswith(".lef") and ".magic." not in n


def 표준셀자리() -> "str | None":
    """`sky130_fd_sc_hd` 셀 디렉터리. 없으면 None."""
    직접 = os.environ.get("SKY130_SC")
    if 직접 and os.path.isdir(직접):
        return 직접
    p = os.path.join(집, _표준셀.replace("/", os.sep), "cells")
    return p if os.path.isdir(p) else None


def 표준셀있나() -> bool:
    return 표준셀자리() is not None


def 자리() -> "str | None":
    """모델 라이브러리 경로. 없으면 None."""
    직접 = os.environ.get("SKY130_LIB")
    if 직접 and os.path.exists(직접):
        return 직접
    p = os.path.join(집, _lib상대)
    return p if os.path.exists(p) else None


def 있나() -> bool:
    return 자리() is not None


def 받기(초: int = 900) -> dict:
    """없으면 PyPI 에서 받아 푼다. {됐나, 경로, 왜}."""
    이미 = 자리()
    if 이미:
        return {"됐나": True, "경로": 이미, "왜": "이미 있다"}
    os.makedirs(집, exist_ok=True)
    받은곳 = os.path.join(집, "_wheel")
    os.makedirs(받은곳, exist_ok=True)
    try:
        r = subprocess.run(
            ["pip", "download", "--no-deps", "--dest", 받은곳, 이름],
            capture_output=True, text=True, timeout=초)
    except Exception as e:                       # pragma: no cover
        return {"됐나": False, "경로": None,
                "왜": f"pip 을 못 돌렸다({e}).\n{손으로}"}
    휠 = [f for f in os.listdir(받은곳) if f.endswith(".whl")]
    if r.returncode != 0 or not 휠:
        return {"됐나": False, "경로": None,
                "왜": ("PyPI 에서 sky130 을 못 받았다 -- "
                      + (r.stderr or r.stdout)[-300:] + "\n" + 손으로)}
    w = os.path.join(받은곳, sorted(휠)[-1])
    with zipfile.ZipFile(w) as z:
        골라 = [n for n in z.namelist() if _필요한가(n)]
        z.extractall(집, members=골라)
    shutil.rmtree(받은곳, ignore_errors=True)    # 휠 38 MB 는 안 남긴다
    p = 자리()
    return {"됐나": bool(p), "경로": p, "표준셀": 표준셀자리(),
            "왜": "" if p else f"풀었는데 라이브러리가 없다.\n{손으로}"}


def lib줄(코너: str = "tt") -> str:
    """넷리스트 맨 위에 넣을 `.lib` 한 줄. 없으면 RuntimeError."""
    p = 자리()
    if not p:
        raise RuntimeError(f"sky130 모델이 없다 -- `pdk.받기()` 를 부르거나\n{손으로}")
    return f'.lib "{p}" {코너}'


def 말로() -> str:
    p = 자리()
    if p:
        크기 = sum(
            os.path.getsize(os.path.join(뿌, f))
            for 뿌, _, fs in os.walk(os.path.join(집, _안쪽)) for f in fs)
        return f"sky130 있음: {p} ({크기 / 1e6:.1f} MB)"
    return "sky130 없음 -- `pdk.받기()`. " + 손으로
