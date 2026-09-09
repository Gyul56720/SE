"""**심판자다. 그리고 LLM 이 아니다.**

    python3 coin/gate.py 답.txt
    python3 coin/gate.py 답.txt -v            soft 도 전부
    python3 coin/gate.py --규칙                무엇을 보는가 (호출 0회)

`law/gate.py` · `jaso/gate.py` · `brief/gate.py` 와 같은 규약 위에 있다.

    hard   확실한 위반. **이 답을 기각한다**
    soft   의심스럽다. 보고하되 기각하지 않는다
    미검증 대조할 것이 없어 **아직 아무도 안 봤다.** 통과가 아니다

## 관문

    C001 근거 실재   답의 수가 잰것 원장에 있는가                     hard
    C002 다시 셈     **원장의 날짜로 다시 세도 같은 값인가**           hard
    C003 표본        표본 수를 밝혔는가 · 미검증을 근거로 단정했는가   hard
    C004 기저율      **아무 날이나 골랐을 때의 값을 같이 적었는가**    hard
    C005 지평        며칠 뒤인지 밝혔는가                             hard
    C006 단정        "반드시" · "확실히" 로 미래를 말했는가            hard
    C007 없는 유형   사전에 없는 사건 유형을 지어냈는가               hard
    C008 미리보기    잰 값이 사건보다 앞선 가격을 쓰지 않았는가       hard
    C009 여러번재기  몇 번 쟀는지 밝혔는가                            hard(유의 주장 시)/soft
    C010 방향        말한 방향이 잰 부호와 같은가                     hard
    C011 알맹이      원장에서 온 것이 하나라도 있는가                 soft
    C012 투자권유    사라 · 팔아라 · 목표가 · 전액                    hard
    C013 나라 쏠림   그 잰 값이 한 나라 기사에서만 왔는가             soft

## C002 가 요점이다

나머지는 꼬리표를 보지만 C002 는 **값을 본다.** 원장에 적힌 날짜 목록으로 가격
원장에서 수익률을 다시 세고, 원장에 적힌 씨로 널을 다시 돌려서, 답이 인용한 수와
견준다. 재는 자리가 조용히 틀리면 여기서 걸린다.

`brief/gate.py` 의 B004 와 같은 자리이고, 그쪽에서 배운 것도 같이 가져왔다 --
**막힌 잰것의 수는 화면에서 뺀다**(`막힌것()`). "관문에 걸렸습니다" 라고 적으면서
수는 그대로 보여 주면 읽는 사람은 수를 먼저 읽는다.

## C004 가 이 도메인의 J002 다

암호화폐에서 사람을 제일 많이 속이는 문장은 거짓말이 아니라 **반쪽 사실**이다.

    "규제 금지 뉴스 뒤 7일 수익률 중앙값 +2.9%"          <- 참이다
    "아무 날이나 골라도 +1.6% 다"                        <- 이걸 빼면 반쪽이다

실측(`tests/test_coin_event.py`): 신호를 하나도 안 심은 무작위 걸음에서 저 첫 줄이
그대로 나온다. 그러므로 기저율 없는 수익률 수는 **틀린 수가 아니라 뜻이 없는 수**이고,
뜻 없는 수를 통과시키는 관문은 관문이 아니다.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coin import flow as FL                                           # noqa: E402
from coin import ledger as LG                                         # noqa: E402
from coin import tag as TG                                            # noqa: E402

# **사건 유형의 어휘는 두 군데서 온다** -- 뉴스 사전과 흐름 원장. 답이 이 밖의
# 유형을 지어내면 C007 이 잡는다.
어휘 = tuple(TG.유형들) + tuple(FL.흐름유형)

규칙표 = {
    "C001": ("근거 실재", "답의 수가 잰것 원장에 있는가"),
    "C002": ("다시 셈", "원장의 날짜로 다시 세도 같은 값인가"),
    "C003": ("표본", "표본 수를 밝혔는가 · 미검증을 근거로 단정했는가"),
    "C004": ("기저율", "아무 날이나 골랐을 때의 값을 같이 적었는가"),
    "C005": ("지평", "며칠 뒤인지 밝혔는가"),
    "C006": ("단정", "반드시 · 확실히 로 미래를 말했는가"),
    "C007": ("없는 유형", "사전에 없는 사건 유형을 지어냈는가"),
    "C008": ("미리보기", "잰 값이 사건보다 앞선 가격을 쓰지 않았는가"),
    "C009": ("여러번재기", "몇 번 쟀는지 밝혔는가"),
    "C010": ("방향", "말한 방향이 잰 부호와 같은가"),
    "C011": ("알맹이", "원장에서 온 것이 하나라도 있는가"),
    "C012": ("투자권유", "사라 · 팔아라 · 목표가 · 전액"),
    "C013": ("나라 쏠림", "그 잰 값이 한 나라 기사에서만 왔는가"),
    "C014": ("장세 고지", "장세가 아래 칸인데 오름을 말하면서 그것을 밝혔는가"),
    "C015": ("고래 과장", "거래량·포지션을 지갑을 본 것처럼 말했는가"),
}

_수 = re.compile(r"[-+]?\d+(?:\.\d+)?\s*(?:%p|%|퍼센트)")
_지평말 = re.compile(r"(?:D\s*\+\s*|디\s*플러스\s*)(\d+)|(\d+)\s*일\s*(?:뒤|후|이내|만에)")
_단정 = ("반드시", "확실히", "무조건", "틀림없이", "100% 오른", "100% 내린",
         "guaranteed", "will surely", "certainly rise", "certainly fall")
_권유 = ("사라", "사세요", "매수하세요", "매수 추천", "팔아라", "파세요", "매도 추천",
         "전액", "몰빵", "풀매수", "목표가", "손절가", "지금 들어가", "지금 사",
         "buy now", "sell now", "price target", "all in")
_유의말 = ("유의", "통계적으로", "significant", "p=", "p 값", "p값")


@dataclass
class 위반:
    규칙: str
    급: str                 # hard · soft · 미검증
    무엇: str
    어디: str = ""

    def __str__(self):
        머 = {"hard": "hard  ", "soft": "soft  ", "미검증": "미검증"}[self.급]
        이름 = 규칙표.get(self.규칙, ("", ""))[0]
        return f"  {머} {self.규칙} {이름:<10} {self.무엇}" + (f"  [{self.어디}]" if self.어디 else "")


@dataclass
class 결과:
    위반들: list = field(default_factory=list)
    인용: list = field(default_factory=list)      # 답이 실제로 인용한 잰것 열쇠
    쓸수있던것: int = 0

    @property
    def hard(self):
        return [v for v in self.위반들 if v.급 == "hard"]

    @property
    def soft(self):
        return [v for v in self.위반들 if v.급 == "soft"]

    @property
    def 미검증(self):
        return [v for v in self.위반들 if v.급 == "미검증"]

    def 통과(self) -> bool:
        return not self.hard

    def 막힌것(self) -> set:
        """**hard 에 걸린 잰것의 열쇠.** 이것들의 수는 화면에서 뺀다."""
        return {v.어디 for v in self.hard if v.어디}


# ------------------------------------------------------------------ 도움
def _수뽑기(글: str) -> list:
    out = []
    for m in _수.finditer(글):
        s = m.group(0)
        try:
            out.append((float(re.sub(r"[^0-9.+-]", "", s)), s, m.start()))
        except ValueError:
            pass
    return out


def _허용수(잰것들: list) -> set:
    """**원장에서 나올 수 있는 수 전부.** 소수 둘째 자리로 맞춘다(적히는 꼴이 그렇다)."""
    ok = set()
    for r in 잰것들:
        for k in ("관측중앙", "관측평균", "널중앙", "초과", "주류초과"):
            v = r.get(k)
            if isinstance(v, float) and v == v:
                ok.add(round(v * 100, 2))
                ok.add(round(v * 100, 1))
                ok.add(round(v * 100))
        v = r.get("승률")
        if isinstance(v, float) and v == v:
            for x in (round(v * 100, 2), round(v * 100, 1), round(v * 100)):
                ok.add(x)
        for k in ("p양측", "p상향", "문턱", "FDR"):
            v = r.get(k)
            if isinstance(v, float) and v == v:
                ok.add(round(v * 100, 2))
                ok.add(round(v, 3))
        for k in ("n", "유효n", "지평", "시험수", "나라수", "최소표본"):
            if isinstance(r.get(k), int):
                ok.add(float(r[k]))
    return ok


def 인용찾기(글: str, 원장: dict) -> list:
    """답이 어느 잰것을 말하고 있나. (유형 이름 + 지평) 이 같이 나오면 그것이다."""
    표 = LG.표(원장)
    out = []
    for 열쇠, r in 표.items():
        if r["유형"] not in 글:
            continue
        h = str(r["지평"])
        if re.search(rf"(?:D\s*\+\s*{h}\b|\b{h}\s*일)", 글):
            out.append(열쇠)
    return sorted(set(out))


# ------------------------------------------------------------------ 관문
def 검사(답: str, 원장: dict, 계열들: dict = None, 엄격: bool = True,
        장세: dict = None, 흐름: dict = None) -> 결과:
    글 = 답 or ""
    표 = LG.표(원장)
    산것 = LG.쓸만한것(원장)
    미검증것 = [r for r in (원장.get("잰것") or []) if r.get("미검증")]
    res = 결과(쓸수있던것=len(산것))
    res.인용 = 인용찾기(글, 원장)
    인용된 = [표[k] for k in res.인용 if k in 표]

    # --- C012 투자 권유 (먼저 본다. 이 답은 다른 무엇이 맞아도 나가면 안 된다)
    for w in _권유:
        if w in 글.lower() if w.isascii() else w in 글:
            res.위반들.append(위반("C012", "hard", f"투자를 권하는 말이 있다: '{w}'"))
            break

    # --- C006 단정
    for w in _단정:
        if (w in 글.lower()) if w.isascii() else (w in 글):
            res.위반들.append(위반("C006", "hard", f"미래를 단정한다: '{w}'"))
            break

    # --- C007 없는 유형
    for m in re.findall(r"[가-힣A-Za-z]{2,12}(?=\s*(?:뉴스|사건|유형))", 글):
        if m in TG.유형들 or m in ("암호화폐", "해당", "이런", "그런", "같은", "관련",
                                   "여러", "다른", "모든", "각", "위", "아래"):
            continue
    지어낸 = [m for m in re.findall(r"'([^']{2,14})'\s*(?:유형|사건)", 글)
              if m not in 어휘]
    for m in 지어낸:
        res.위반들.append(위반("C007", "hard", f"사전에 없는 사건 유형이다: '{m}'"))

    # --- C011 알맹이
    if 산것 and not res.인용:
        res.위반들.append(위반("C011", "soft",
                              f"쓸만한 잰것이 {len(산것)}개 있는데 답이 하나도 안 짚었다"))

    # --- C001 근거 실재
    허용 = _허용수(원장.get("잰것") or [])
    for v, s, i in _수뽑기(글):
        if round(v, 2) in 허용 or round(v, 1) in 허용 or round(v) in 허용:
            continue
        res.위반들.append(위반("C001", "hard", f"원장에 없는 수다: '{s.strip()}'",
                              어디=글[max(0, i - 28):i].strip()[-28:]))

    # --- 인용한 잰것마다
    for r in 인용된:
        열쇠 = LG.열쇠(r)
        # C005 지평
        if not re.search(rf"(?:D\s*\+\s*{r['지평']}\b|\b{r['지평']}\s*일)", 글):
            res.위반들.append(위반("C005", "hard", f"며칠 뒤인지 안 적었다", 어디=열쇠))
        # C003 표본
        if not re.search(rf"(?:n\s*=?\s*{r['n']}\b|표본\s*{r['n']}\b|{r['n']}\s*건)", 글):
            res.위반들.append(위반("C003", "hard",
                                  f"표본 수를 안 적었다 (원장은 n={r['n']})", 어디=열쇠))
        # C004 기저율 -- **이 도메인의 심장**
        널 = round(r["널중앙"] * 100, 2)
        초 = round(r["초과"] * 100, 2)
        있나 = any(abs(v - x) < 0.06 for v, _, _ in _수뽑기(글) for x in (널, 초))
        말 = any(w in 글 for w in ("기저율", "널", "아무 날", "초과", "대비"))
        if not (있나 and 말):
            res.위반들.append(위반("C004", "hard",
                                  "아무 날이나 골랐을 때의 값(기저율)을 안 적었다 -- "
                                  "그것 없이는 이 수가 시장 추세인지 사건 효과인지 안 갈린다",
                                  어디=열쇠))
        # C008 미리보기
        if float(r.get("유예", 0)) <= 0 or r.get("기준") not in ("최초", "주류"):
            res.위반들.append(위반("C008", "hard",
                                  f"진입가가 사건 뒤라는 보장이 없다 "
                                  f"(유예={r.get('유예')} 기준={r.get('기준')})", 어디=열쇠))
        # C010 방향
        오름 = re.search(r"(오르|상승|올랐|상방|반등)", 글)
        내림 = re.search(r"(내리|하락|떨어|하방|급락)", 글)
        if r["초과"] == r["초과"]:
            if r["초과"] > 0 and 내림 and not 오름:
                res.위반들.append(위반("C010", "hard",
                                      f"잰 것은 +{초:.2f}%p 인데 내린다고 적었다", 어디=열쇠))
            if r["초과"] < 0 and 오름 and not 내림:
                res.위반들.append(위반("C010", "hard",
                                      f"잰 것은 {초:.2f}%p 인데 오른다고 적었다", 어디=열쇠))
        # C013 나라 쏠림
        if r.get("나라수", 0) <= 1:
            res.위반들.append(위반("C013", "soft",
                                  f"이 잰 값의 기사가 한 나라({list(r.get('나라') or ['?'])[0]})"
                                  "에서만 왔다 -- 다른 나라가 먼저 보도했으면 D0 가 늦다",
                                  어디=열쇠))
        # C002 다시 셈
        res.위반들.append(_다시셈(r, 계열들, 열쇠))

    # --- C003 미검증을 근거로 단정
    for r in 미검증것:
        if r["유형"] in 글 and re.search(rf"(?:D\s*\+\s*{r['지평']}\b|\b{r['지평']}\s*일)", 글):
            if not re.search(r"(미검증|모른다|못 잰|알 수 없|표본이 모자)", 글):
                res.위반들.append(위반("C003", "hard",
                                      f"미검증인 것을 근거로 말한다 ({r['왜']})",
                                      어디=LG.열쇠(r)))

    # --- C009 여러 번 재기
    시험수 = (산것[0].get("시험수") if 산것 else 0)
    밝혔나 = bool(시험수) and (str(시험수) in 글) and any(
        w in 글 for w in ("번 쟀", "시험", "다중", "보정", "BH"))
    if res.인용 and not 밝혔나:
        급 = "hard" if (엄격 and any(w in 글 for w in _유의말)) else "soft"
        res.위반들.append(위반("C009", 급,
                              f"몇 번 쟀는지를 안 적었다 (원장은 {시험수}번) -- "
                              "많이 재면 우연히 걸리는 것이 반드시 나온다"))

    # --- C014 장세 고지. 장이 아래 칸인데 오름을 말하면서 그 사실을 안 적었으면
    나쁜장 = [a for a, g in (장세 or {}).items() if g and g.get("나쁨")]
    if 나쁜장 and re.search(r"(오르|상승|상방|반등|올랐)", 글):
        밝혔나 = any(w in 글 for w in ("장세", "약세", "추세", "아래 칸", "자리"))
        if not 밝혔나:
            res.위반들.append(위반("C014", "hard",
                                  f"장세가 아래 칸인데({', '.join(나쁜장)}) 그것을 안 적고 "
                                  "오름을 말한다 -- 읽는 사람은 이것을 권유로 읽는다"))

    # --- C015 고래 과장. 지갑을 안 봤는데 봤다고 말하면
    지갑봤나 = bool((흐름 or {}).get("대형이체"))
    if not 지갑봤나 and re.search(r"(고래|세력|큰손|whale)", 글):
        if not re.search(r"(거래량|포지션|자금조달|미결제|대용|보지 못|못 본)", 글):
            res.위반들.append(위반("C015", "hard",
                                  "지갑 자료가 없는데 '고래·세력' 이라고 적었다 -- "
                                  "잰 것은 거래량이나 포지션이다"))

    res.위반들 = [v for v in res.위반들 if v is not None]
    return res


def _다시셈(r: dict, 계열들: dict, 열쇠: str):
    """**원장에 적힌 날짜와 씨로 다시 센다.** 계열이 없으면 미검증 -- 통과가 아니다."""
    from coin import null as NU
    if not 계열들 or r["자산"] not in 계열들:
        return 위반("C002", "미검증", "가격 원장이 없어 다시 셈을 못 했다", 어디=열쇠)
    c = 계열들[r["자산"]]
    값 = [c.수익(d, r["지평"]) for d in (r.get("날들") or [])]
    관측 = NU.중앙(값)
    if 관측 != 관측:
        return 위반("C002", "hard", "원장의 날짜로는 하나도 못 셌다", 어디=열쇠)
    if abs(관측 - r["관측중앙"]) > 1e-9:
        return 위반("C002", "hard",
                    f"다시 세니 다르다: 원장 {r['관측중앙']*100:+.4f}% "
                    f"vs 다시 셈 {관측*100:+.4f}%", 어디=열쇠)
    널 = NU.널(c, r.get("날들") or [], r["지평"], r.get("널판수") or 2000,
              r.get("씨") or 0, r.get("널꼴") or "이동")
    널중 = NU.중앙(널["판"])
    if 널중 == 널중 and abs((관측 - 널중) - r["초과"]) > 5e-4:
        return 위반("C002", "hard",
                    f"초과를 다시 세니 다르다: 원장 {r['초과']*100:+.3f}%p "
                    f"vs 다시 셈 {(관측-널중)*100:+.3f}%p", 어디=열쇠)
    return None


# ------------------------------------------------------------------ 점수 · 되먹임
def 점수(res: 결과, 답: str) -> tuple:
    """**순위 자. 낮을수록 좋다.** LLM 이 아니라 이 튜플이 '가장 좋은 답' 을 고른다.

    (hard 수, soft 수, -인용 수, 글자 수)
    """
    return (len(res.hard), len(res.soft), -len(res.인용), len(답 or ""))


def 되먹임(res: 결과) -> str:
    """다음 바퀴에 돌려줄 말. **규칙 이름도 문턱도 안 나간다 -- 사실만 나간다.**

    무엇이 통과하는지 알려 주면 통과하는 답이 나오고, 그러면 관문이 사양서가 된다
    (`law/write.py` 가 생성자에게 관문을 안 알려 주는 것과 같은 자리).
    여기서 나가는 것은 **이 답의 어디가 사실과 어긋나는가**뿐이다.
    """
    줄들 = []
    for v in res.hard + res.soft:
        t = v.무엇
        t = re.sub(r"\bC0\d\d\b", "", t)
        줄들.append(f"- {t}" + (f" (그 자리: {v.어디})" if v.어디 else ""))
    return "\n".join(줄들)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("답", nargs="?", default="")
    ap.add_argument("-v", "--전부", action="store_true")
    ap.add_argument("--규칙", action="store_true")
    ap.add_argument("--원장", default="")
    a = ap.parse_args(argv)

    if a.규칙 or not a.답:
        for k, (이름, 설명) in 규칙표.items():
            print(f"  {k}  {이름:<10} {설명}")
        print("\n**LLM 을 안 쓴다.** C002 만 값을 보고 나머지는 꼬리표를 본다")
        return 0

    글 = Path(a.답).read_text(encoding="utf-8") if Path(a.답).exists() else a.답
    원장 = LG.불러오기(a.원장 or None)
    from coin import price as PR
    계열들 = {}
    for x in {r["자산"] for r in (원장.get("잰것") or [])}:
        원 = PR.불러오기(x)
        if 원:
            계열들[x] = PR.계열(원)
    res = 검사(글, 원장, 계열들)
    for v in res.위반들:
        if v.급 == "hard" or a.전부:
            print(v)
    print(f"\nhard {len(res.hard)} · soft {len(res.soft)} · 미검증 {len(res.미검증)} "
          f"· 짚은 잰것 {len(res.인용)}/{res.쓸수있던것}")
    return 0 if res.통과() else 1


if __name__ == "__main__":
    raise SystemExit(main())
