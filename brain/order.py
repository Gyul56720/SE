"""**작업표** -- 물음을 검사 꼴로 쪼갠 것. 그리고 그 쪼갬을 코드가 검사한다.

물음이 무엇일지는 아무도 모른다. 그래서 **쪼개는 일은 모델이 하고, 쪼갠 것이 성한지는
코드가 본다.** `law/METHOD.md` 의 분업 그대로다 -- LLM 은 조문에서 요건을 뽑고(대조
가능한 일), 쟁점은 코드가 도출한다.

    물음 --(모델)--> 작업표 --(코드 R001~R005)--> 성하면 돌린다
                       |
                  못 세우면 --> 관할 밖이라 말한다

## 모델이 지어낼 수 있는 것과 없는 것

    지어낼 수 있다   어느 꼴로 갈지 · 무엇을 대조할지 · 무엇을 기준선으로 둘지
    지어낼 수 없다   **꼴 자체**(닫힌 다섯) · 재료가 있는 척(R002/R003 이 잡는다)
                     · 판정(꼴을 돌리는 코드가 낸다)

지어낸 꼴 이름은 R001 이 잡고, 없는 재료는 R002 가 잡는다. 그래서 모델이 아무리
그럴듯하게 써도 **판정까지는 못 간다.**

## R004 가 이 파일에서 제일 중요하다

**관할 밖 칸이 비어 있으면 위반이다.** 어떤 물음도 통째로 기계 판정되지 않는다 --
원인·전망·가치·처방은 늘 남는다. 그것을 안 적었다는 것은 다 판정했다고 믿는 것이고,
그 믿음이 판정 안 받은 답에 판정받은 옷을 입히는 자리다.

모든 보고서가 끝에 '안 보는 것' 을 적는 것과 같은 규율이다. 여기서는 **시작할 때**
적게 한다.

## 실측 2026-09-09 -- 작업표에 "받아 와야 한다" 를 적을 칸이 없었다

`Cogito ergo sum kr1도` 를 넣었더니 조각이 **하나도 안 나오고** 통째로 관할 밖이
되었다. 사용자가 물었다: **"api 접근 안하고 뭐해?"**

`kr1` 은 앞선 물음(`사는게외롭다#kr1`)에 붙어 있던 라이엇 태그라인이다. 즉 그 물음은
조회할 열쇠를 들고 있었는데, 모델은 라틴어 문장으로 읽고 `가치` 로 보냈다. 그런데
**모델만 탓할 자리가 아니다** -- 그렇게 몰고 간 것이 이 파일과 프롬프트였다.

    받아 올 곳을 적을 칸이 없다  ->  재료를 못 채운다
    재료를 못 채우면 R002/R003 이 잡는다
    잡히지 않으려면 두 길뿐이다
        (가) "아직 안 받았다" 라고 글자를 채운다  -> R003 통과, **관문이 초록불**,
             그런데 아무도 안 받아 온다. 판정은 빈 것 위에서 돈다
        (나) 조각을 안 만들고 관할 밖에 적는다    -> 통째로 관할 밖

**둘 다 받아 오지 않는다.** (가)는 검사 안 한 초록불이고 (나)는 안 알아보고 접은
것이다. 이 저장소가 제일 싫어하는 두 가지를 한 자리에서 고르게 해 놓았다.

그래서 셋째 칸을 판다.

    재료 값 = 손에 있는 값  |  **받을것**(`{"받기": "<주소>", "무엇": "..."}`)

받을것이 하나라도 있으면 이 작업표는 **아직 못 돌린다**(끝값 2). 관할 밖도 아니고
돌려도 되는 것도 아니다 -- **받아 와야 하는 것**이다. 그리고 R006 이 그 주소가
진짜 갈 수 있는 곳인지 본다. "받아 온다" 고만 적고 어디인지 안 적으면 소원이지
계획이 아니다.

## 그리고 `원장없음` 은 찾아본 뒤에만 할 수 있는 말이다 (R007)

관할 밖 다섯 갈래 중 넷(인과·전망·가치·처방)은 **물음의 성질**이라 안 찾아보고도
안다. `원장없음` 만 다르다 -- 그것은 **밖의 사정**이고, 찾아봐야 아는 것이다.
안 찾아보고 그 말을 하면 추측인데, 추측으로 관할 밖에 놓으면 관문이 아예 안 돈다.
위 (나)가 정확히 그 구멍으로 나갔다. 그래서 `찾아본곳` 을 적게 한다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from brain import form as FM


@dataclass
class 조각:
    주장: str = ""                 # 무엇을 검사할 것인가
    꼴: str = ""                   # FORMS 의 이름
    재료: dict = field(default_factory=dict)
    왜: str = ""


@dataclass
class 작업표:
    물음: str = ""
    조각: list = field(default_factory=list)
    관할밖: list = field(default_factory=list)   # [{"무엇":..., "왜":..., "찾아본곳":...}]

    @property
    def 갈데없음(self) -> bool:
        return not self.조각

    @property
    def 미수령(self) -> list:
        """아직 안 받은 재료들. `[(조각번호, 조각, 재료이름, 받을것), ...]`"""
        out = []
        for i, p in enumerate(self.조각, 1):
            for k, v in p.재료.items():
                g = 받을것(v)
                if g:
                    out.append((i, p, k, g))
        return out

    @property
    def 받아야함(self) -> bool:
        """**관할 밖도 아니고 돌려도 되는 것도 아닌 셋째 자리.**"""
        return bool(self.미수령)


@dataclass
class 위반:
    규칙: str
    등급: str
    어디: str
    말: str

    def __str__(self) -> str:
        return f"[{self.규칙}/{self.등급}] {self.어디}: {self.말}"


AIM = {
    "R001": "검사 꼴이 닫힌 다섯 중 하나여야 한다",
    "R002": "그 꼴이 요구하는 재료가 다 채워져야 한다",
    "R003": "재료가 빈 값이 아니어야 한다",
    "R004": "관할 밖을 적어야 한다 -- 통째로 판정되는 물음은 없다",
    "R005": "갈 데가 하나도 없으면 그렇다고 적어야 한다",
    "R006": "받아 올 것이면 **어디서** 받는지가 주소여야 한다",
    "R007": "`원장없음` 은 찾아본 뒤에만 할 수 있는 말이다",
}

# 재료 값이 "아직 없다" 는 뜻으로 흔히 적히는 말들. 이렇게 적으면 R003 은 글자가
# 있으니 통과시키고, 아무도 안 받아 온다 -- **초록불인 채로 빈 것 위에서 판정이 돈다.**
# 그래서 여기 걸리면 받을것으로 적으라고 되돌려 보낸다(R003).
안받은말 = ("아직", "안 받", "안받", "미수", "없음", "미상", "unknown", "tbd",
            "todo", "n/a", "받아야", "필요함", "조회 필요", "확인 필요", "?")


def 받을것(v):
    """재료 값이 **아직 손에 없고 받아 오면 되는 것**인가. 맞으면 그 선언, 아니면 None.

    꼴: `{"받기": "<주소 또는 등록된 출처 이름>", "무엇": "무엇을 뽑을지"}`

    이 칸이 없어서 모델이 받아 오기를 포기했다(위 실측). 값이냐 없음이냐 둘뿐이면
    **아직 안 받은 것**을 적을 데가 없고, 없는 칸에 넣으려면 지어내거나 접어야 한다.
    """
    if isinstance(v, dict) and str(v.get("받기") or "").strip():
        return {"받기": str(v["받기"]).strip(),
                "무엇": str(v.get("무엇") or "").strip()}
    return None


def _갈수있는곳(어디: str) -> bool:
    """주소이거나, `brief/source.py` 에 등록된 출처 이름인가.

    **brief 가 없어도 안 죽는다** -- 그러면 주소만 받는다. brain 은 brief 를 부르지만
    brief 는 brain 을 안 부르므로 되돌이가 없다.
    """
    if 어디.startswith(("http://", "https://")):
        return True
    try:
        from brief import source as SRC
    except Exception:                                         # noqa: BLE001
        return False
    return SRC.get(어디) is not None


def 읽기(d) -> 작업표:
    """dict 나 JSON 문자열 -> 작업표. **꼴이 아니면 빈 작업표다.**"""
    if isinstance(d, str):
        try:
            d = json.loads(d)
        except json.JSONDecodeError:
            return 작업표()
    if not isinstance(d, dict):
        return 작업표()
    조각들 = []
    for p in (d.get("조각") or []):
        if isinstance(p, dict):
            조각들.append(조각(주장=str(p.get("주장") or ""), 꼴=str(p.get("꼴") or ""),
                             재료=p.get("재료") if isinstance(p.get("재료"), dict) else {},
                             왜=str(p.get("왜") or "")))
    밖 = [x for x in (d.get("관할밖") or []) if isinstance(x, dict)]
    return 작업표(물음=str(d.get("물음") or ""), 조각=조각들, 관할밖=밖)


def 검사(표: 작업표) -> list:
    """R001~R005. **판정을 안 한다** -- 작업표가 성한지만 본다."""
    vs = []
    for i, p in enumerate(표.조각, 1):
        어디 = f"조각{i}({p.주장[:24] or '이름없음'})"
        f = FM.get(p.꼴)
        if f is None:
            vs.append(위반("R001", "hard", 어디,
                          f"그런 검사 꼴이 없다: {p.꼴!r} -- 있는 것은 "
                          f"{', '.join(FM.FORMS)}. 꼴은 요청 시점에 못 늘린다"))
            continue
        빠짐 = [k for k in f.있어야 if k not in p.재료]
        if 빠짐:
            vs.append(위반("R002", "hard", 어디,
                          f"'{p.꼴}' 꼴에 필요한 재료가 없다: {', '.join(빠짐)}"))
        빔, 흉내 = [], []
        for k in f.있어야:
            if k not in p.재료:
                continue
            v = p.재료[k]
            g = 받을것(v)
            if g:
                # **받을것은 빈 값이 아니다.** 다만 어디서 받는지는 주소여야 한다.
                if not _갈수있는곳(g["받기"]):
                    vs.append(위반("R006", "hard", 어디,
                                  f"'{k}' 를 받아 온다는데 갈 수 있는 곳이 아니다: "
                                  f"{g['받기'][:60]!r} -- 주소(http…)이거나 등록된 "
                                  "출처 이름이어야 한다. 어디인지 없으면 소원이지 계획이 아니다"))
                continue
            글자 = str(v or "").strip()
            if not 글자:
                빔.append(k)
            elif any(w in 글자.lower() for w in 안받은말) and len(글자) <= 40:
                흉내.append(k)
        if 빔:
            vs.append(위반("R003", "hard", 어디,
                          f"재료가 빈 값이다: {', '.join(빔)} -- "
                          "칸만 채우고 내용이 없으면 검사가 도는 척만 한다"))
        if 흉내:
            vs.append(위반("R003", "hard", 어디,
                          f"'아직 없다' 를 값인 척 적었다: {', '.join(흉내)} -- "
                          "이러면 글자가 있으니 통과하고 **아무도 안 받아 온다.** "
                          '받아 올 것이면 {"받기": "<주소>", "무엇": "..."} 로 적어라'))
    # R004 -- **비어 있으면 위반이다**
    if not 표.관할밖:
        vs.append(위반("R004", "hard", "작업표",
                      "관할 밖을 하나도 안 적었다. 어떤 물음도 통째로 기계 판정되지 "
                      f"않는다 -- 늘 남는 것: {', '.join(FM.관할밖)}"))
    else:
        for x in 표.관할밖:
            if not str(x.get("무엇") or "").strip():
                vs.append(위반("R004", "soft", "관할밖",
                              "무엇이 관할 밖인지 안 적혔다"))
            # R007 -- **`원장없음` 만 밖의 사정이다.** 나머지 넷은 물음의 성질이라
            # 안 찾아보고도 알지만, 이것은 찾아봐야 아는 것이다.
            종 = " ".join(str(x.get(k) or "") for k in ("종류", "무엇", "왜"))
            if "원장없음" in 종.replace(" ", "") and not str(
                    x.get("찾아본곳") or "").strip():
                vs.append(위반("R007", "hard", "관할밖",
                              "'원장없음' 은 **찾아본 뒤에만 할 수 있는 말**이다 -- "
                              "어디를 찾아봤는지 `찾아본곳` 에 적어라. 안 찾아보고 "
                              "'밖에 아무것도 없다' 고 하면 추측이고, 추측으로 관할 밖에 "
                              "놓으면 아무것도 안 돈다"))
    # R005 -- 갈 데가 없으면 그렇다고 말해야 한다
    if 표.갈데없음 and not 표.관할밖:
        vs.append(위반("R005", "hard", "작업표",
                      "검사할 조각도 없고 관할 밖도 안 적었다 -- 아무 말도 안 한 것이다"))
    return vs


def hard(vs) -> list:
    return [v for v in vs if v.등급 == "hard"]


def 보고(표: 작업표, vs) -> str:
    out = [f"# 작업표 -- {표.물음[:70]}", ""]
    if 표.갈데없음:
        out.append("**검사 꼴로 갈 조각이 없다.** 이 물음은 통째로 관할 밖이다.")
        # **여기서 멈추면 안 된다.** 실측 2026-09-09: 사용자가 양자 다체 문제를
        # 물었는데 이 보고만 나오고 **답이 안 나갔다**("그냥 답변을 안하는데").
        # 관할 밖은 애초에 답하지 말라는 뜻이 아니었다 -- `brain/form.py` 가
        # 적어 둔 대로 "판정 없이 답한다고 말하고 답하면 된다" 는 뜻이다.
        # 그 문장이 이 자리에 없어서 부르는 쪽이 끝값 3 을 실패로 읽었다.
        out.append("")
        out.append("**여기서 멈추지 마라 -- 지금부터가 답할 차례다.**")
        out.append("관할 밖은 '답하지 마라' 가 아니라 '판정 없이 답하라' 다. "
                   "아는 대로 답하되 두 가지를 지켜라:")
        out.append("  1. **수치를 붙이지 마라.** 없는 출처와 근거 없는 수가 "
                   "정확히 그 자리에서 나온다.")
        out.append("  2. 판정을 안 받았다고 **말하고** 답하라. 하면 안 되는 것은 "
                   "판정 안 받은 답에 판정받은 옷을 입히는 것이다.")
        out.append("")
    else:
        out.append(f"검사할 조각 {len(표.조각)}개")
        out.append("")
        for i, p in enumerate(표.조각, 1):
            f = FM.get(p.꼴)
            out.append(f"  {i}. [{p.꼴}] {p.주장}")
            if f:
                out.append(f"       묻는 것: {f.묻는것}")
                out.append(f"       판정:    {' / '.join(f.판정)}")
                out.append(f"       돌린다:  {f.돌리는것}")
                out.append(f"       **못 하는 것**: {f.못하는것}")
            for k, v in p.재료.items():
                g = 받을것(v)
                if g:
                    out.append(f"       {k}: **아직 안 받음** <- {g['받기'][:60]}"
                               + (f" ({g['무엇'][:40]})" if g["무엇"] else ""))
                else:
                    out.append(f"       {k}: {str(v)[:70]}")
            out.append("")

    if 표.받아야함:
        out.append("## 받아 와야 하는 것 -- **아직 못 돌린다**")
        out.append("")
        out.append("관할 밖이 아니다. 돌려도 되는 것도 아니다. **받아 오면 되는 것**이다.")
        out.append("")
        for i, p, k, g in 표.미수령:
            out.append(f"  조각{i} · {k} <- {g['받기'][:80]}")
            if g["무엇"]:
                out.append(f"       뽑을 것: {g['무엇'][:70]}")
            if g["받기"].startswith(("http://", "https://")):
                out.append(f"       python3 brief/report.py --탐색 --url '{g['받기']}'")
        out.append("")
        out.append("  `--탐색` 은 **무엇이 오는지만** 본다 -- 저장도 판정도 안 한다.")
        out.append("  받아 온 값을 재료에 채워 넣고 이 작업표를 다시 넣어라.")
        out.append("  못 받으면 그때 **왜 못 받았는지 적고** 관할 밖으로 옮겨라 -- "
                   "안 받아 보고 옮기지 마라.")
        out.append("")

    out.append("## 관할 밖 -- 판정 없이 답할 자리")
    out.append("")
    if 표.관할밖:
        for x in 표.관할밖:
            out.append(f"  · {x.get('무엇', '?')} -- {x.get('왜', '')}")
            찾 = str(x.get("찾아본곳") or "").strip()
            if 찾:
                out.append(f"       찾아본 곳: {찾[:70]}")
    else:
        out.append("  (안 적혔다 -- R004 위반)")
    out.append("")
    out.append("## 작업표 관문")
    out.append("")
    if not vs and 표.갈데없음:
        # **여기서 "돌려도 된다" 고 하면 안 된다** -- 돌릴 것이 없다. 그 말이
        # 부르는 쪽에 '할 일 없음' 으로 읽혀서 답이 안 나갔다.
        out.append("  R001~R007: 위반 없음 -- 돌릴 조각은 없다. "
                   "**답은 네가 한다**(위 '여기서 멈추지 마라')")
    elif not vs and 표.받아야함:
        out.append("  R001~R007: 위반 없음 -- 다만 **재료를 받아 와야 돈다** (끝값 2)")
    elif not vs:
        out.append("  R001~R007: 위반 없음 -- 이 작업표는 돌려도 된다")
    else:
        out.append(f"  위반 {len(hard(vs))}건(hard) · {len(vs) - len(hard(vs))}건(soft)")
        for v in vs:
            out.append(f"    {v}")
        if hard(vs):
            out.append("")
            out.append("  **hard 가 있으면 돌리지 않는다.** 재료를 채우거나, "
                       "그 조각을 관할 밖으로 옮겨라.")
    return "\n".join(out)
