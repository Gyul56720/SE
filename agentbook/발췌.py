# -*- coding: utf-8 -*-
"""클론한 저장소에서 **실제 줄**을 떠서 `agentbook/snips/` 에 박아 둔다.

왜 박아 두나. 클론은 스크래치패드에 있어 사라진다. 그런데 이 책은 남의 코드를
**줄 번호와 함께** 인용한다 -- "읽은 커밋만 인용한다" 를 지키려면 인용한 글자가
저장소 안에 남아 있어야 나중에 대조가 된다.

발췌 하나는 머리에 (저장소 · 커밋 · 경로 · 줄범위) 를 달고 있다. 책이 빌드될 때
망도 클론도 안 탄다.

    python3 agentbook/발췌.py <클론뿌리> langchain libs/core/.../base.py 133 180 [열쇠]
"""
import json
import os
import subprocess
import sys

여기 = os.path.dirname(os.path.abspath(__file__))
곳간 = os.path.join(여기, "snips")


def 뜨기(뿌리: str, 저장소: str, 경로: str, 시작: int, 끝: int, 열쇠=None) -> dict:
    d = os.path.join(뿌리, 저장소)
    커밋 = subprocess.run(["git", "-C", d, "rev-parse", "--short", "HEAD"],
                        capture_output=True, text=True).stdout.strip()
    p = os.path.join(d, 경로)
    줄들 = open(p, encoding="utf-8", errors="replace").read().splitlines()
    if not (1 <= 시작 <= 끝 <= len(줄들)):
        raise ValueError(f"{경로}: 줄 범위 {시작}-{끝} 이 파일({len(줄들)}줄) 밖이다")
    토막 = 줄들[시작 - 1:끝]
    열쇠 = 열쇠 or f"{저장소}_{os.path.basename(경로).split('.')[0]}_{시작}"
    os.makedirs(곳간, exist_ok=True)
    메타 = {"열쇠": 열쇠, "저장소": 저장소, "커밋": 커밋, "경로": 경로,
          "시작": 시작, "끝": 끝, "줄수": len(토막)}
    with open(os.path.join(곳간, 열쇠 + ".json"), "w", encoding="utf-8") as f:
        json.dump(메타, f, ensure_ascii=False)
    with open(os.path.join(곳간, 열쇠 + ".txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(토막) + "\n")
    return 메타


def 읽기(열쇠: str) -> tuple:
    """(메타, [(줄번호, 글자), ...]) 를 돌려준다. **책이 부르는 것은 이것뿐이다.**"""
    with open(os.path.join(곳간, 열쇠 + ".json"), encoding="utf-8") as f:
        메타 = json.load(f)
    글 = open(os.path.join(곳간, 열쇠 + ".txt"), encoding="utf-8").read().splitlines()
    return 메타, list(zip(range(메타["시작"], 메타["시작"] + len(글)), 글))


def 목록():
    if not os.path.isdir(곳간):
        return []
    return sorted(f[:-5] for f in os.listdir(곳간) if f.endswith(".json"))


if __name__ == "__main__":
    뿌리 = sys.argv[1]
    m = 뜨기(뿌리, sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]),
          sys.argv[6] if len(sys.argv) > 6 else None)
    print(f"{m['열쇠']}: {m['저장소']}@{m['커밋']} {m['경로']}:{m['시작']}-{m['끝']} "
          f"({m['줄수']}줄)")
