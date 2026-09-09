"""**어떤 물음이 와도 여기로 들어온다.** 꼴로 쪼개고, 쪼갠 것을 검사한다.

    python3 brain/route.py --꼴                      # 검사 꼴 다섯 (호출 0회)
    python3 brain/route.py --프롬프트 "<물음>"        # 모델에게 줄 것 (호출 0회)
    python3 brain/route.py --표 작업표.json           # 검사하고 무엇을 돌릴지 낸다
    python3 brain/route.py --표 - < 작업표.json       # 파이프로도

    끝값 0  돌려도 된다   1  작업표에 hard 위반   3  통째로 관할 밖

## 이 파일이 하는 일은 **분류가 아니라 검사**다

물음을 어느 꼴로 보낼지는 모델이 정한다 -- 물음이 무엇일지 아무도 모르므로 그 자리는
열려 있어야 한다. 대신 **쪼갠 결과가 성한지는 코드가 본다**(R001~R005). 그래서 모델이
아무리 그럴듯하게 써도 재료 없이 판정까지 갈 수는 없다.

`--url` 과 같은 배치다. 거기서도 어디를 볼지는 열려 있고 `inspect` 는 닫혀 있었다.

## 왜 여기서 판정까지 안 하나

판정은 이미 다섯 자리에 있다(`brief/` · `law/` · `lol/` · `mathdrift/`). 여기서 또
판정하면 **두 벌이 생기고 두 벌은 언젠가 갈라진다** -- `score.py` 가 예측을 다시 만들지
않는 것과 같은 이유다. 여기서는 어느 자리로 가야 하는지까지만 낸다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brain import form as FM                                       # noqa: E402
from brain import order as OD                                      # noqa: E402


def 프롬프트(물음: str) -> str:
    """**모델에게 줄 것.** 판정 이야기가 한 줄도 없다 -- 쪼개기만 시킨다.

    `law/write.py` 가 생성자에게 관문을 안 알려 주는 것과 같은 규율이다. 어떤 판정이
    나오면 좋은지 알려 주면 그쪽으로 쪼개게 되고, 그러면 쪼갬이 사양서가 된다.
    """
    꼴표 = "\n".join(
        f"  {f.이름:<6} {f.묻는것}\n         있어야: {' · '.join(f.있어야)}"
        for f in FM.FORMS.values())
    밖 = "\n".join(f"  {k:<8} {v}" for k, v in FM.관할밖.items())
    return f"""다음 물음을 **검사할 수 있는 조각**으로 쪼개라.

## 물음
{물음.strip()}

## 쓸 수 있는 검사 꼴 -- **이 다섯뿐이고 늘릴 수 없다**
{꼴표}

## 어떤 꼴로도 안 가는 것 -- 여기 해당하면 조각으로 만들지 말고 `관할밖` 에 적어라
{밖}

## 어떻게 쪼개나

  · 조각 하나는 **검사할 수 있는 주장 하나**다. "시장을 분석해줘" 는 조각이 아니고
    "오늘 코스피 움직임이 과거 분포에서 이례인가" 는 조각이다.
  · 꼴마다 `있어야` 가 다르다. **재료를 실제로 채울 수 있을 때만** 그 조각을 만들어라.
    받아 올 곳이 없으면 조각이 아니라 관할 밖이다.
  · 재료에 없는 출처나 없는 수를 적지 마라. 채워 넣어도 검사에서 걸리고, 걸리면
    그 조각은 안 돈다.
  · **`관할밖` 을 반드시 하나 이상 적어라.** 통째로 기계 판정되는 물음은 없다 --
    원인·전망·가치·처방은 늘 남는다.
  · 쪼갤 것이 하나도 없으면 조각을 비우고 관할밖만 적어라. 그것도 옳은 답이다.

## 출력 (JSON 하나만. 다른 말은 붙이지 마라)

{{
 "물음": "{물음.strip()[:40]}",
 "조각": [
  {{"주장": "검사할 주장 하나", "꼴": "기준선",
    "재료": {{"관측": "...", "과거표본": "...", "기준선": "..."}},
    "왜": "이 꼴을 고른 까닭"}}
 ],
 "관할밖": [{{"무엇": "...", "왜": "..."}}]
}}"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="물음을 검사 꼴로 쪼개고 그 쪼갬을 검사한다")
    ap.add_argument("--꼴", dest="forms", action="store_true", help="검사 꼴 다섯")
    ap.add_argument("--프롬프트", dest="ask", default="", help="모델에게 줄 것을 찍는다")
    ap.add_argument("--표", dest="order", default="", help="작업표 JSON (`-` 면 표준입력)")
    a = ap.parse_args(argv)

    if a.forms:
        print(FM.목록())
        return 0
    if a.ask:
        print(프롬프트(a.ask))
        return 0
    if not a.order:
        print("무엇을 할지 안 정해졌다.")
        print("  python3 brain/route.py --꼴                 # 검사 꼴 다섯")
        print("  python3 brain/route.py --프롬프트 '<물음>'  # 모델에게 줄 것")
        print("  python3 brain/route.py --표 작업표.json     # 쪼갠 것을 검사한다")
        return 3

    try:
        raw = (sys.stdin.read() if a.order == "-"
               else Path(a.order).read_text(encoding="utf-8"))
    except OSError as e:                                      # noqa: BLE001
        # 없는 파일로 죽지 않는다. 부르는 쪽이 봇이면 예외 문자열만 보고 무슨 일인지
        # 모른다 -- 무엇을 하라고 알려 주는 편이 낫다.
        print(f"**작업표를 못 열었다**: {e}")
        print("  python3 brain/route.py --프롬프트 '<물음>' 로 무엇을 받아야 하는지 본다.")
        return 3
    표 = OD.읽기(raw)
    if not 표.조각 and not 표.관할밖:
        print("**작업표를 못 읽었다.** JSON 이 아니거나 `조각`·`관할밖` 이 둘 다 없다.")
        print("  python3 brain/route.py --프롬프트 '<물음>' 로 무엇을 받아야 하는지 본다.")
        return 3
    vs = OD.검사(표)
    print(OD.보고(표, vs))
    if 표.갈데없음:
        return 3
    return 1 if OD.hard(vs) else 0


if __name__ == "__main__":
    raise SystemExit(main())
