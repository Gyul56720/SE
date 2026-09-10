"""**자유로운 한 마디를 듣는다** -- 무엇을 부탁했는지만 캔다.

공개 채널로 오는 첫 말은 서식이 아니다. 실측(디스코드):

    내가 현재 경북대학교 에너지화학공학과 3학년으로 재학중인데 경희대전기정보공학부로
    편입을 지원을 원하는데 자소서를 필요로해서 재학중인 과와 연관해서 지원동기 파트를
    어떻게 작성해야할까?

한 줄 102자. 여기에 **낼 곳 · 지금 있는 데 · 무엇을 써 달라는지**가 다 들어 있는데,
`corpus.문항뽑기` 는 0개를 캔다 -- 그것은 '기술하시오' · `(700자)` 같은 **끝나는
자리**로 캐기 때문이고, 부탁하는 말에는 그런 자리가 없다. 그래서 이 말은 통째로
검색어가 되어 나갔다(실측). 헛걸음이다 -- 찾을 것이 이미 그 말 안에 있었다.

## 두 정거장이고, 둘 다 **캐는 것**이지 짓는 것이 아니다

    ① 코드   `item.쪼개기` 로 **요구를 도출한다.** 키가 없어도 돈다
    ② 모델   원문에서 **오려 온다** -- 낼 곳 · 단위 · 지금 · 문항 (Gemini)

②를 모델에게 맡기는 까닭은 고유명사이기 때문이다. '경희대전기정보공학부' 를 코드로
가르려면 학교 이름 목록이 있어야 하고, **그 목록은 늘 모자란다.** 갈래를 박아 두면
목록에 없는 학교가 오는 날 통째로 못 읽는다.

## H001 -- 원문에 없는 글자는 버린다

모델이 낸 값이 **원문의 부분 문자열이 아니면 그 칸을 버린다.** 여기는 캐는 자리지
채우는 자리가 아니고, 모델이 '경희대학교 전기전자공학부' 라고 반듯하게 고쳐 놓으면
그 사람이 안 쓴 학부에 지원하는 자소서가 나간다.

띄어쓰기만 **양쪽에서 다 지우고** 견준다. 한국어 띄어쓰기는 사람마다 다르고, 모델이
'경희대 전기정보공학부' 로 띄운 것을 지어냈다고 볼 수는 없다. 글자가 그대로면 통과다.

## 원장은 안 건드린다

'경북대 에너지화학공학과 3학년' 은 그 사람이 말한 사실이지만 **여기서 원장에 넣지
않는다.** 항목이 원장에 들어가는 길은 `intake` 가 사람의 답에서 넣는 것 하나뿐이고,
그때 I001 이 답 원문과 대조한다. 여기서 넣으면 그 못이 뽑힌다. 들은 것은 화면에
되비쳐 주기만 한다 -- 틀리게 들었으면 사람이 거기서 고친다.

    python3 jaso/heed.py "<한 마디>"
    python3 jaso/heed.py "<한 마디>" --코드만       # 모델을 안 부른다
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import item as IT                                          # noqa: E402

# **한 마디인가.** 여러 줄이면 그것은 붙여넣은 글이지 부탁하는 말이 아니다 --
# 요강을 통째로 붙인 것을 여기로 들이면 요강 전문이 문항 하나가 된다.
한마디상한 = 400

칸들 = ("낼곳", "단위", "지금")


@dataclass
class 들은것:
    낼곳: str = ""                       # 어디에 내려는가 (학교·회사)
    단위: str = ""                       # 그 안의 학과·학부·직무
    지금: str = ""                       # 지금 어디에 있다고 했는가
    문항들: list = field(default_factory=list)
    요구들: list = field(default_factory=list)
    들은데: dict = field(default_factory=dict)   # 칸마다 누가 채웠나
    버린것: list = field(default_factory=list)   # H001 에 걸린 것

    def 있나(self) -> bool:
        return bool(self.문항들 or self.낼곳 or self.단위 or self.지금)

    def 한줄(self) -> str:
        칸 = [f"{이름} {getattr(self, 이름)}" for 이름 in 칸들 if getattr(self, 이름)]
        if self.문항들:
            칸.append("문항 " + " · ".join(self.문항들))
        return " · ".join(칸) or "(못 들었다)"


def 한마디인가(말: str) -> bool:
    말 = (말 or "").strip()
    return bool(말) and "\n" not in 말 and len(말) <= 한마디상한


def _붙여(s: str) -> str:
    """띄어쓰기를 다 지운다. H001 은 이 꼴로 견준다."""
    return re.sub(r"\s+", "", s or "")


def _못쪼갬(요구들: list) -> bool:
    """`기술` 하나뿐이면 **못 쪼갠 것**이다 -- `item.쪼개기` 의 되돌림 자리.

    실측: 이것을 안 가렸더니 `"한양대 편입"` 이 요구 `['기술']` 로 잡혀 **부탁으로
    읽혔다.** 그러면 학교 이름을 그대로 문항으로 삼아 "이 문항에 답을 쓰라" 는 꼴이
    되고, 찾아볼 기회는 사라진다. 이름뿐인 말은 부탁이 아니라 **찾을 말**이다.
    """
    return list(요구들) == ["기술"]


# ------------------------------------------------------------ ① 코드 정거장

def 코드로(말: str) -> 들은것:
    """`item.쪼개기` 로 **요구를 도출한다.** 키가 없어도 도는 정거장이다.

    요구가 하나도 안 잡히면 그 말은 부탁이 아니라 이름뿐인 것이다 -- 빈 것을
    돌려주고, 부르는 쪽이 그것을 찾을 말로 보낸다.
    """
    말 = (말 or "").strip()
    것 = 들은것()
    if not 한마디인가(말):
        return 것
    q = IT.쪼개기(말, "1")
    것.요구들 = [r.종류 for r in q.요구]
    if 것.요구들 and not _못쪼갬(것.요구들):
        # **문항 원문은 그 사람이 한 말 그대로다.** 요구 이름으로 갈아 끼우면
        # 학교가 안 낸 문항을 지어내는 것이 된다.
        것.문항들 = [말]
        것.들은데["문항들"] = "코드"
    return 것


# ------------------------------------------------------------ ② 모델 정거장

def 프롬프트(말: str) -> str:
    """**캐라고만 한다.** 관문 이름도, 좋은 자소서가 무엇인지도 여기 없다."""
    return (
        "아래는 어떤 사람이 자기소개서를 부탁하며 한 말입니다.\n"
        "그 사람이 **이미 말한 것만** 골라 옮겨 적으십시오.\n\n"
        "  낼곳    어디에 내려는가 (학교 · 회사 이름)\n"
        "  단위    그 안의 학과 · 학부 · 직무\n"
        "  지금    지금 어디에 있다고 했는가 (학교 · 학과 · 학년 · 회사)\n"
        "  문항들  무엇을 써 달라고 했는가. **그 사람이 쓴 말 그대로** "
        "(여러 개면 여러 개)\n\n"
        "규칙\n"
        "- 값은 **원문에 있는 글자를 그대로** 옮깁니다. 고쳐 쓰거나 풀어 쓰지 않습니다.\n"
        "- 원문에 없는 것은 **빈 칸(\"\")으로 둡니다.** 짐작해서 채우지 않습니다.\n"
        "- JSON 하나만 냅니다. 다른 말을 붙이지 않습니다.\n\n"
        '{"낼곳": "", "단위": "", "지금": "", "문항들": []}\n\n'
        "--- 그 사람이 한 말 ---\n" + 말)


def _JSON(글: str):
    글 = (글 or "").strip()
    m = re.search(r"\{.*\}", 글, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def 새기기(말: str, 답, 것: 들은것) -> 들은것:
    """모델이 낸 것을 **H001 로 거르고** 얹는다. 원문에 없으면 버린다."""
    준것 = _JSON(답) if isinstance(답, str) else 답
    if not isinstance(준것, dict):
        return 것
    바탕 = _붙여(말)
    for 이름 in 칸들:
        값 = str(준것.get(이름) or "").strip()
        if not 값:
            continue
        if _붙여(값) in 바탕:
            setattr(것, 이름, 값)
            것.들은데[이름] = "모델"
        else:
            것.버린것.append(f"{이름}={값!r}")            # H001
    캔문항 = [str(x).strip() for x in (준것.get("문항들") or []) if str(x).strip()]
    성한것 = [x for x in 캔문항 if _붙여(x) in 바탕]
    것.버린것 += [f"문항={x!r}" for x in 캔문항 if _붙여(x) not in 바탕]
    if 성한것:
        # **모델이 오려 온 것이 그 말 전체보다 낫다.** 코드는 통째로 들 수밖에 없다.
        것.문항들 = 성한것
        것.들은데["문항들"] = "모델"
        if not 것.요구들:
            것.요구들 = [r.종류 for x in 성한것 for r in IT.쪼개기(x, "1").요구]
    return 것


_POOL = None


def _풀에게(글: str) -> str:
    global _POOL
    if _POOL is None:
        sys.path.insert(0, str(ROOT / "orchestrator"))
        import llm_pool
        pool = llm_pool.build_pool()
        if not pool:
            raise RuntimeError("LLM 후보 풀이 비었다 -- GEMINI_API_KEY 를 설정하라")
        _POOL = (llm_pool, pool)
    mod, pool = _POOL
    return mod.call(pool, 글, pool_id="jaso")[0]


def 듣기(말: str, 묻기=None, 코드만: bool = False) -> 들은것:
    """`코드로` 로 먼저 듣고, 모델이 있으면 오려 온 것으로 다듬는다.

    **모델이 죽어도 코드가 들은 것은 남는다.** 키가 없는 데서 통째로 못 듣게 되면
    이 자리는 배포판에서 없는 것과 같다.
    """
    것 = 코드로(말)
    if 코드만 or not 한마디인가(말):
        return 것
    try:
        답 = (묻기 or _풀에게)(프롬프트(말))
    except Exception as e:
        것.버린것.append(f"모델을 못 불렀다: {type(e).__name__}")
        return 것
    return 새기기(말, 답, 것)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="자유로운 한 마디에서 부탁만 캔다")
    ap.add_argument("말", help="사용자가 한 말 그대로")
    ap.add_argument("--코드만", action="store_true", help="모델을 안 부른다")
    a = ap.parse_args(argv)
    것 = 듣기(a.말, 코드만=a.코드만)
    print(f"한 마디인가: {한마디인가(a.말)} ({len(a.말)}자)")
    for 이름 in 칸들:
        값 = getattr(것, 이름)
        print(f"  {이름:<6} {값 or '(못 들었다)':<40} {것.들은데.get(이름, '')}")
    print(f"  문항   {' · '.join(것.문항들) or '(못 들었다)'}"
          f"   {것.들은데.get('문항들', '')}")
    print(f"  요구   {' · '.join(것.요구들) or '(없다)'}")
    if 것.버린것:
        print("\n**H001 -- 원문에 없어 버린 것:**")
        for x in 것.버린것:
            print(f"  {x}")
    return 0 if 것.있나() else 1


if __name__ == "__main__":
    raise SystemExit(main())
