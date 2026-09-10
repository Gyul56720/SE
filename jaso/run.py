"""**한 명령으로 갈 수 있는 데까지 간다.** 그리고 사람 차례에서 멈춘다.

    python3 jaso/run.py --이름 누리하나 --회사 누리하나 --직무 "데이터 분석" \\
        --질의 "2026 상반기 자기소개서 문항"
    python3 jaso/run.py --이름 누리하나 --답글 "1) ... 2) ..."   # 답을 바로 넣는다
    python3 jaso/run.py --이름 누리하나                          # 이어서 간다

끝값이 **다음에 무엇을 할지**다.

    0  자소서까지 냈다
    2  **사람 차례다** -- 물음이 나갔고 답을 기다린다
    1  관문 hard 가 남았다
    3  못 갔다 (키가 없다 · 한 벌도 못 받았다)

## 문항이 없는 것은 끝값 3 이 아니다 -- 사람 차례다

한동안 3 이었다. 그런데 **이것은 배포판에서 열에 아홉이 지나는 자리다.** 공개
채널에서 사람이 처음 하는 말은 "자소서 써 줘" 한 줄이고, 학교도 문항도 안 딸려
온다. 거기서 3 을 내면 사람이 보는 것은 이 문구였다:

    문항을 못 구했다 -- `--문항 "<원문>"` 을 직접 주거나, 망이 열린 데서
    `--질의` 를 다시 돌려라

**옵션 이름을 모르는 사람에게 옵션 이름으로 답한 것이다.** 그리고 3 은 부르는
쪽에 "이 건은 끝났다" 로 읽혀, 봇이 되묻지 않고 대화를 닫는다. 재료가 모자란
것은 실패가 아니라 **아직 사람에게 물을 것이 남은 것**이고, 그것을 가리키는
끝값은 이미 2 다. 물음이 원장 빈칸에서 나오느냐 문항이 없어서 나오느냐만
다르다.

## 왜 끝까지 자동으로 안 도나

**답할 사람이 있어야 하기 때문이다.** 그리고 그 자리를 기계로 메우면 이 파이프라인은
스스로를 무력화한다.

실측으로 한 번 그럴 뻔했다 -- "`내원장.json` 이 없으면 방금 수집한 정보를 토대로
구조를 잡고 진행하겠습니다." **수집한 것은 남의 공고문이다.** 그것으로 원장을 만들면
그 사람의 이력을 지어내는 것이고, J001~J004 와 P001 이 전부 미검증이 되며, 나오는
글은 정확히 이 파이프라인이 막으려던 그 글이다. 관문이 있다는 착각만 얹은 채로.

그래서 여기에 못을 박는다: **`run.py` 는 경험 항목을 만들지 않는다.** 항목이 원장에
들어가는 길은 `intake.py` 가 사람의 답에서 넣는 것 하나뿐이고, 그때도 I001 이 답
원문과 대조한다. `tests/test_jaso_run.py` 가 그 자리를 붙든다.

## 그래서 자동인 것은 무엇인가

**사람이 답을 준 다음의 모든 것.** 넣기 · 다시 묻기 · 다 찼는지 판정 · 여러 벌 생성 ·
관문 · 고르기 · 작성 근거 기록. 한 번 부르면 다음 사람 차례까지 알아서 간다.

## 작업 폴더

    jaso/작업/<이름>/
      원장.json    경험 원장 (사람의 답이 쌓이는 곳)
      문항.json    이 건의 문항
      물음.json    지금 물을 것
      답.txt       **사람이 채우는 칸** -- 여기만 사람 차례다
      답_01.txt    처리된 답 (지우지 않는다 -- 작성 근거 기록의 재료다)
      자소서.md · 근거.md · 기록.md
"""
from __future__ import annotations

import argparse
import hashlib
import re
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import ask as AS                                           # noqa: E402
from jaso import corpus as CP                                        # noqa: E402
from jaso import gate as GT                                          # noqa: E402
from jaso import heed as HD                                          # noqa: E402
from jaso import intake as IN                                        # noqa: E402
from jaso import item as IT                                          # noqa: E402
from jaso import ledger as LG                                        # noqa: E402
from jaso import refine as RF                                        # noqa: E402
from jaso import trace as TR                                         # noqa: E402
from jaso import write as WR                                         # noqa: E402

작업DIR = Path(__file__).resolve().parent / "작업"

사람차례 = 2


def _적기(터: Path, 말: str) -> None:
    with (터 / "기록.md").open("a", encoding="utf-8") as f:
        f.write(f"- {datetime.now().strftime('%Y-%m-%d %H:%M')}  {말}\n")


def 문항읽기(터: Path) -> list:
    p =터 / "문항.json"
    if not p.is_file():
        return []
    try:
        것 = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return [IT.쪼개기(str(x.get("글") or ""), str(x.get("번호") or ""))
            for x in (것.get("문항") or []) if str(x.get("글") or "").strip()]


def 문항담기(터: Path, qs: list, 출처: str = "") -> None:
    (터 / "문항.json").write_text(json.dumps(
        {"출처": 출처, "문항": [{"글": q.원문, "번호": q.번호} for q in qs]},
        ensure_ascii=False, indent=2), encoding="utf-8")


def 들은담기(터: Path, 말: str, 들은) -> None:
    """들은 것을 폴더에 남긴다. **원장에는 안 넣는다.**

    '경북대 에너지화학공학과 3학년' 은 그 사람이 말한 사실이지만, 항목이 원장에
    들어가는 길은 `intake` 가 사람의 답에서 넣는 것 하나뿐이다 -- 그때 I001 이 답
    원문과 대조한다. 여기서 넣으면 그 못이 뽑힌다. 남기는 것은 **무엇을 듣고 이렇게
    움직였는지**의 근거이고, 틀리게 들었으면 사람이 화면에서 보고 고친다.
    """
    (터 / "들은것.json").write_text(json.dumps(
        {"말": 말, "낼곳": 들은.낼곳, "단위": 들은.단위, "지금": 들은.지금,
         "문항들": list(들은.문항들), "요구들": list(들은.요구들),
         "들은데": dict(들은.들은데), "버린것": list(들은.버린것)},
        ensure_ascii=False, indent=2), encoding="utf-8")


_주소 = re.compile(r"https?://\S+")


def 받은것꼴(것: str) -> dict:
    """사용자가 준 것을 **꼴을 보고** 어디로 보낼지 정한다.

    배포판에서는 사용자가 무엇을 줄지 모른다 -- 학교 이름만 던질 수도, 주소를
    붙일 수도, 요강을 통째로 넣을 수도 있다. **갈래를 물어보지 않는다.** 물어보면
    한 번 더 왕복하고, 그 왕복에서 사람이 떠난다.
    """
    것 = (것 or "").strip()
    if not 것:
        return {}
    주소 = _주소.findall(것)
    if 주소:
        return {"urls": 주소}
    if "\n" in 것 or len(것) > 120:
        return {"글": 것}                      # 요강·공고를 붙인 것
    return {"질의": 것}                        # "○○대 편입" 같은 이름


def 찾아본것(a) -> str:
    """무엇을 짚어 봤는지 한 줄로. **빈 문자열이면 아무것도 안 짚은 것이다.**"""
    본 = []
    if a.질의:
        본.append(f'질의 "{a.질의[:40]}"')
    if a.urls:
        본.append(f"주소 {len(a.urls)}개")
    if a.글:
        본.append(f"붙여넣은 글 {len(a.글)}자")
    if a.문항:
        본.append(f"준 문항 {len(a.문항)}개")
    return " · ".join(본)


def 어디에낼지(a, 다시: str) -> tuple:
    """문항이 없을 때 **사람에게 보일 말**. `(할말, 답.txt 머리말)`.

    두 경우를 가른다 -- 아무것도 안 주신 것과, 주신 것으로 찾아봤는데 없는 것.
    **같은 물음을 두 번 하지 않는다.** 배포판에서 그것은 "이 봇은 내 말을 안
    듣는다" 로 읽히고, 두 번째 왕복에서 사람이 떠난다. 첫 번째는 열어 놓고 묻고
    (이름이든 주소든 붙여넣기든), 두 번째는 **되는 것 하나만** 짚어 준다.
    """
    본것 = 찾아본것(a)
    if not 본것:
        return (
            "**어디에 내는 것입니까?** 셋 중 아무거나 주시면 됩니다.\n\n"
            "  · 학교나 회사 이름          예: ○○대 편입 · △△기업 신입\n"
            "  · 모집요강·공고 **주소**     예: https://…\n"
            "  · 문항이나 요강을 **그대로 붙여넣기**\n"
            f'\n  python3 jaso/run.py {다시} --답글 "<위 중 하나>"',
            "# 어디에 내는 것인지 한 줄로 적어 주십시오.\n\n1) ")
    return (
        f"**찾아봤지만 문항을 못 구했습니다.** (짚어 본 것: {본것})\n\n"
        "같은 것을 다시 주셔도 결과는 같습니다. **문항 원문을 그대로 붙여넣어\n"
        "주십시오** -- 요강 화면을 통째로 복사하셔도 됩니다. 문항으로 보이는\n"
        "대목만 캐냅니다.\n"
        f'\n  python3 jaso/run.py {다시} --답글 "1. 지원 동기를 기술하시오 (700자)  2. …"',
        "# 문항 원문을 그대로 붙여넣어 주십시오 (요강을 통째로 붙이셔도 됩니다).\n\n")


def _글로(것: str) -> str:
    """경로면 읽고 아니면 그대로. **길거나 줄이 여럿이면 경로가 아니다.**

    실측: 붙여넣은 요강을 그대로 `Path(...).is_file()` 에 넣었더니
    `OSError: File name too long` 으로 죽었다. 공개 채널에서 사람이 요강을 통째로
    붙이는 것이 **정상 사용**인데, 그 정상 사용이 봇을 죽인다.
    """
    if "\n" not in 것 and len(것) < 200:
        try:
            p = Path(것)
            if p.is_file():
                return p.read_text(encoding="utf-8")
        except OSError:
            pass
    return 것


def 문항모으기(터: Path, a) -> tuple:
    """이 건의 문항을 정한다. `(문항들, 못한까닭)`.

    **글의 갈래를 안 정한다.** 편입 요강이든 채용 공고든 문항만 적힌 쪽지든, 오는 것을
    `corpus.문항뽑기` 에 그대로 넣는다 -- 거기는 '기술하시오' · `(700자)` 같은 **끝나는
    자리**로 캐므로 어느 서식에서든 돈다. 갈래 목록을 두면 목록에 없는 서식이 오는
    날 통째로 못 읽고, 그 목록은 늘 모자란다.
    """
    qs = 문항읽기(터)
    if qs and not (a.문항 or a.질의 or a.urls or a.글):
        return qs, ""
    새것 = [IT.쪼개기(x, str(i + 1)) for i, x in enumerate(a.문항)]
    출처 = getattr(a, "출처힌트", "") or "손으로"
    if a.글:
        붙인글 = _글로(a.글)
        캔것 = CP.문항뽑기(붙인글, "붙여넣은 글")
        새것 += [q.쪼갠것() for q in 캔것]
        print(f"  붙여넣은 글 {len(붙인글)}자에서 문항 {len(캔것)}개를 캤다")
        출처 = "붙여넣은 글"
    if a.질의 or a.urls:
        from jaso import fetch as JF
        보고 = JF.받기(a.질의, a.urls, a.회사, a.몇)
        for 이름, 말 in (보고["창구별"] or {}).items():
            print(f"  [창구 {이름}] {말}")
        for u, 말 in 보고["쪽별"].items():
            print(f"  {말:<24} {u[:64]}")
        새것 += [q.쪼갠것() for q in 보고["문항"]]
        for 출, 것들 in _출처별(보고["문항"]).items():
            CP.담기(것들)                       # 문항 원장에도 남긴다
        출처 = a.질의 or ",".join(a.urls)
    if a.문항원장:
        새것 += [q.쪼갠것() for q in CP.읽기(a.곳).문항들]
    본것, 모은것 = set(), list(qs)
    for q in 새것:
        if q.원문 not in 본것 and q.원문 not in {x.원문 for x in qs}:
            본것.add(q.원문)
            모은것.append(q)
    for i, q in enumerate(모은것, 1):
        q.번호 = q.번호 or str(i)
    if not 모은것:
        return [], ("문항을 못 구했다 -- `--문항 \"<원문>\"` 을 직접 주거나, "
                    "망이 열린 데서 `--질의` 를 다시 돌려라")
    문항담기(터, 모은것, 출처)
    return 모은것, ""


def _출처별(것들) -> dict:
    out = {}
    for q in 것들:
        out.setdefault(q.출처, []).append(q)
    return out


def 답받기(터: Path, 답글: str = "") -> tuple:
    """아직 안 넣은 답을 읽는다. `(답 원문, 어디서)`."""
    if 답글.strip():
        return 답글, "바로 준 것"
    p = 터 / "답.txt"
    if not p.is_file():
        return "", ""
    # **주석 줄을 먼저 뗀다.** 실측: 안 떼었더니 템플릿의 안내 주석(`# 아래 번호마다…`)
    # 이 통째로 '1번 답' 으로 읽혔다 -- `답나누기` 는 번호가 없으면 전부를 1번으로
    # 주기 때문이다(그것은 답을 안 버리려고 그렇게 둔 것이라 옳다). 그래서 여기서
    # 껍데기를 걷어내야 한다. 안 걷으면 매번 "답을 넣었다 -- 0칸" 이 찍힌다.
    글 = "\n".join(x for x in p.read_text(encoding="utf-8").splitlines()
                  if not x.lstrip().startswith("#"))
    if not any(v.strip() for v in IN.답나누기(글).values()):
        return "", ""
    return 글, str(p)


def 물음내기(터: Path, qs: list, L: LG.원장, 몇: int, 다시: str = "",
           모델: bool = False) -> list:
    물을것 = AS.물을것(qs, L, 몇)
    if 모델 and 물을것:
        from jaso import write as WR
        try:
            물을것, n = AS.문구입히기(물을것,
                                  WR._풀에게(AS.프롬프트(qs, 물을것)))
            print(f"  (모델이 물음 {n}개의 문구를 이 문항의 말로 썼다)", flush=True)
        except Exception as e:
            print(f"  (모델을 못 불렀다 -- 씨앗 문구로 간다: {type(e).__name__})",
                  flush=True)
    if not 물을것:                       # 물을 것이 없으면 빈 칸을 만들지 않는다
        (터 / "물음.json").write_text(
            json.dumps({"물음": [], "남은것": AS.남은것(qs, L)},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        return []
    (터 / "물음.json").write_text(json.dumps(
        {"물음": [x.__dict__ for x in 물을것],
         "남은것": AS.남은것(qs, L)}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (터 / "답.txt").write_text(
        "# 아래 번호마다 답을 적어 주십시오. 적은 뒤 다시 부르면 이어서 갑니다.\n"
        f"#   python3 jaso/run.py {다시}\n\n"
        + "\n\n".join(f"{i}) " for i in range(1, len(물을것) + 1)) + "\n",
        encoding="utf-8")
    return 물을것


def _사람터(사람: str, 이름: str) -> Path:
    """**호출자마다 다른 폴더.** 공개 채널에서 원장이 섞이면 남의 이력을 보게 된다.

    id 를 그대로 폴더 이름에 쓰지 않는다 -- 그러면 채널에서 누가 이 봇을 썼는지가
    폴더 목록으로 남는다. 해시로 가른다.
    """
    h = hashlib.sha1(str(사람).encode("utf-8")).hexdigest()[:12]
    return 작업DIR / f"ㅅ{h}" / (이름 or "기본")


def 한걸음(a) -> int:
    터 = (Path(a.터) if a.터
          else (_사람터(a.사람, a.이름) if a.사람 else 작업DIR / a.이름))
    # **원장과 답은 공개 폴더로 못 나간다.** `Public_agent/` 는 커밋되는 곳이고,
    # 거기에 경험 원장이 들어가면 그 사람의 이력이 저장소에 영영 남는다.
    안되는곳 = (ROOT / "Public_agent").resolve()
    if 안되는곳 == 터.resolve() or 안되는곳 in 터.resolve().parents:
        print(f"**{안되는곳} 안에는 못 쓴다** -- 거기는 커밋되는 곳이고, 경험 원장과 "
              "인터뷰 답이 담기면 그 사람의 이력이 저장소에 남는다", file=sys.stderr)
        return 3
    # **다시 부르는 법을 그대로 찍어야 한다.** `--터` 로 부른 사람에게 `--이름 <폴더>`
    # 를 알려 주면 다른 폴더가 새로 파이고, 그 사람은 답을 적어 둔 데를 잃는다.
    터.mkdir(parents=True, exist_ok=True)
    원장길 = 터 / "원장.json"

    다시 = (f"--터 {터}" if a.터 else
          (f"--사람 {a.사람} --이름 {a.이름}" if a.사람
           else f"--이름 {a.이름}"))
    qs, 왜 = 문항모으기(터, a)
    if 왜 and a.답글.strip():
        # **사용자가 준 것을 문항 재료로 본다.** 문항이 없는 판에서 온 답은
        # 물음에 대한 답이 아니라 "어디에 내는지" 에 대한 답이다.
        말 = a.답글.strip()
        a.답글 = ""
        보낼데 = 받은것꼴(말)
        if "urls" in 보낼데:
            a.urls = 보낼데["urls"]
            qs, 왜 = 문항모으기(터, a)
        else:
            # ① **끝나는 자리부터.** '기술하시오' · `(700자)` 가 있으면 그것이 진짜
            #    문항 원문이다. 망을 안 탄다.
            a.글 = 말
            qs, 왜 = 문항모으기(터, a)
            if 왜 and HD.한마디인가(말):
                # ② **부탁하는 말인가.** 찾으러 나가기 전에 먼저 듣는다 -- 실측:
                #    "…지원동기 파트를 어떻게 작성해야할까?" 102자가 통째로
                #    검색어가 되어 나갔다. 찾을 것이 이미 그 말 안에 있었다.
                들은 = HD.듣기(말)
                if 들은.문항들:
                    a.문항, a.글 = list(들은.문항들), ""
                    a.출처힌트 = "사용자가 한 말"
                    a.회사 = a.회사 or 들은.낼곳
                    a.직무 = a.직무 or 들은.단위
                    들은담기(터, 말, 들은)
                    print(f"  들은 것: {들은.한줄()}")
                    qs, 왜 = 문항모으기(터, a)
                elif "질의" in 보낼데:
                    # ③ 이름뿐이다 -- 찾아본다
                    a.질의, a.글 = 보낼데["질의"], ""
                    qs, 왜 = 문항모으기(터, a)
    if 왜:
        # **끝값 3 이 아니다 -- 사람 차례다.** 배포판에서 여기 오는 것은 사용자가
        # "자소서 써 줘" 만 한 경우이고, 그때 개발자용 오류 문구를 내밀면 안 된다.
        할말, 머리말 = 어디에낼지(a, 다시)
        (터 / "답.txt").write_text(머리말, encoding="utf-8")
        print("\n" + "─" * 62)
        print(할말)
        본것 = 찾아본것(a)
        _적기(터, ("문항을 못 구했다 -- " +
                 (f"짚어 본 것: {본것}" if 본것 else "어디에 내는지 물었다")))
        return 사람차례
    print(f"문항 {len(qs)}개 · 작업 폴더 {터}")

    L = LG.읽기(str(원장길)) if 원장길.is_file() else LG.원장()
    for i in a.빼기:
        h = L.찾기(i)
        L.항목들 = [x for x in L.항목들 if x.id != i]
        print(f"  뺌    [{i}] {h.이름 if h else '(그런 항목이 없다)'}")
        _적기(터, f"항목 [{i}] 를 뺐다")
    if a.빼기:
        IN.쓰기(L, 원장길)

    # 1) 답이 와 있으면 넣는다. **항목이 원장에 들어가는 유일한 길이다.**
    글, 어디서 = 답받기(터, a.답글)
    if 글:
        물음들 = json.loads((터 / "물음.json").read_text(encoding="utf-8")).get(
            "물음", []) if (터 / "물음.json").is_file() else []
        L, vs, 채운것 = IN.넣기(물음들, IN.답나누기(글), L)
        IN.쓰기(L, 원장길)
        n = len(list(터.glob("답_*.txt"))) + 1
        (터 / f"답_{n:02d}.txt").write_text(글, encoding="utf-8")
        if (터 / "답.txt").is_file():
            (터 / "답.txt").unlink()
        print(f"\n답을 넣었다 ({어디서}) -- {len(채운것)}칸")
        for 말 in 채운것:
            print(f"  채움  {말}")
        for v in vs:
            print(f"  {v}")
        _적기(터, f"답 {n}번째를 넣었다 ({len(채운것)}칸 · 위반 {len(vs)}건)")

    막힌것 = LG.hard(LG.검사(L))
    if 막힌것:
        print("\n원장에 hard 위반이 있다 -- 고치기 전에는 그 위에서 못 쓴다:")
        for v in 막힌것:
            print(f"  {v}")

    # 2) 아직 물을 것이 있으면 **여기서 멈춘다.** 기계가 메울 자리가 아니다.
    물을것 = 물음내기(터, qs, L, a.몇물음, 다시, a.모델물음)
    if 물을것 or 막힌것:
        남 = AS.남은것(qs, L)
        print(f"\n원장: 항목 {남['항목']}개 · 물을 것 {len(물을것)}개\n")
        for x in 물을것:
            print(x)
            print()
        print("─" * 62)
        print(f"**사람 차례입니다.** {터 / '답.txt'} 에 번호대로 적고 다시 부르십시오:")
        print(f"  python3 jaso/run.py {다시}")
        print(f"또는 답을 바로:  python3 jaso/run.py {다시} --답글 \"1) … 2) …\"")
        _적기(터, f"물음 {len(물을것)}개를 냈다 -- 사람 차례")
        return 사람차례

    # 3) 재료가 찼다. 여기서부터 끝까지 자동이다.
    print("\n재료가 찼다 -- 쓴다")
    벌들, 쓴것, 조각 = [], set(), []
    for q in qs:
        try:
            r = RF.돌리기(q, L, a.바퀴, a.벌, a.회사, a.직무, 쓴것,
                        문법=a.문법)
        except Exception as e:
            print(f"\n**못 썼다: {type(e).__name__}: {e}**", file=sys.stderr)
            print("  (GEMINI_API_KEY 가 있는 데서 돌려라 -- 이 컨테이너는 키가 없다)",
                  file=sys.stderr)
            _적기(터, f"쓰기 실패: {type(e).__name__}")
            return 3
        if not r["글있나"]:
            print(f"\n**문항 {q.번호 or '?'} 에서 한 벌도 글을 못 받았다: {r['왜']}**",
                  file=sys.stderr)
            print("  (GEMINI_API_KEY 가 있는 데서 돌려라 -- **빈 자소서는 안 쓴다.** "
                  "0자짜리 파일이 생기면 사람은 파일이 생긴 것을 먼저 본다)",
                  file=sys.stderr)
            _적기(터, f"문항 {q.번호} 에서 한 벌도 못 받았다: {r['왜'][:60]}")
            return 3
        벌들.append(r)
        쓴것 |= set(r["최선"]["항목"])
        조각.append(f"## {q.번호 + '. ' if q.번호 else ''}{q.원문}\n\n"
                   f"{r['최선']['글']}\n")
        print(f"  [문항 {q.번호}] {len(r['바퀴들'])}바퀴 -> {r['최선']['잰']}")
        for b in r["바퀴들"]:
            표 = "나아짐" if b.나아졌나 else ("버림 " if b.번호 else "첫벌 ")
            print(f"      {b.번호}바퀴 {표}  {b.잰}")
        if r["물을것"]:
            print("      **루프가 못 고친 것이 있다 -- 재료 문제다.** 물을 것:")
            for x in r["물을것"][:2]:
                print(f"        · {x.말[:72]}")

    자소서 = 터 / "자소서.md"
    자소서.write_text(f"---\n회사: \"{a.회사}\"\n직무: \"{a.직무}\"\n---\n\n"
                    + "\n".join(조각), encoding="utf-8")
    print(f"\n[씀] {자소서}")

    자 = GT.읽기(자소서.read_text(encoding="utf-8"), 자소서)
    vs, 대조, 미검증 = GT.검사(자, L)
    hard = [v for v in vs if v.등급 == "hard"]
    soft = [v for v in vs if v.등급 == "soft"]
    print(f"\n관문: hard {len(hard)} · soft {len(soft)} · "
          f"값 대조 {대조}건 · 미검증 {미검증}건")
    for v in hard + soft:
        print(f"  {v}")

    답벌 = "\n\n".join(p.read_text(encoding="utf-8")
                     for p in sorted(터.glob("답_*.txt")))
    근거 = 터 / "근거.md"
    근거.write_text(TR.글로(자, L, TR.훑기(자, L), IN.답나누기(답벌) if 답벌 else None),
                  encoding="utf-8")
    print(f"[씀] {근거}")
    _적기(터, f"자소서를 냈다 (hard {len(hard)} · soft {len(soft)})")
    if hard:
        print("\n**hard 가 남았다.** 고른 것은 덜 나쁜 것이지 통과한 것이 아니다")
    return 1 if hard else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="갈 수 있는 데까지 간다 -- 사람 차례에서 멈춘다")
    ap.add_argument("--이름", default="기본", help="작업 이름 (폴더 이름이 된다)")
    ap.add_argument("--사람", default="",
                    help="**공개 채널에서는 반드시 준다.** 호출자마다 폴더를 "
                         "가른다 -- 안 가르면 남의 원장을 보게 된다")
    ap.add_argument("--터", default="", help="작업 폴더를 직접 정한다")
    ap.add_argument("--회사", default="")
    ap.add_argument("--직무", default="")
    ap.add_argument("--질의", dest="질의", default="")
    ap.add_argument("--url", dest="urls", nargs="+", default=[])
    ap.add_argument("--문항", dest="문항", action="append", default=[])
    ap.add_argument("--문항원장", action="store_true")
    ap.add_argument("--글", dest="글", default="",
                    help="요강·공고·문항 목록 아무 글이나 (파일 경로도 된다).\n갈래를 안 가린다 -- 문항으로 보이는 대목을 캔다")
    ap.add_argument("--곳", default=str(CP.문항DIR))
    ap.add_argument("--답글", dest="답글", default="", help="답을 바로 준다")
    ap.add_argument("--모델물음", action="store_true",
                    help="물음 문구를 모델이 이 문항의 말로 쓴다")
    ap.add_argument("--빼기", dest="빼기", action="append", default=[],
                    help="잘못 들어간 항목 id 를 원장에서 뺀다")
    ap.add_argument("--몇", dest="몇", type=int, default=8, help="찾을 주소 수")
    ap.add_argument("--몇물음", dest="몇물음", type=int, default=8)
    ap.add_argument("--벌", dest="벌", type=int, default=3)
    ap.add_argument("--바퀴", dest="바퀴", type=int, default=3,
                    help="정제 바퀴 (0 이면 첫 벌만 내고 안 돈다)")
    ap.add_argument("--문법", dest="문법", default="기본",
                    help="jaso/bench.py 가 고른 것을 쓴다")
    a = ap.parse_args(argv)
    return 한걸음(a)


if __name__ == "__main__":
    raise SystemExit(main())
