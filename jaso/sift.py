"""**자소서인가 아닌가.** 긁어 온 것에서 아닌 것을 가려낸다. 호출 0회.

    python3 jaso/sift.py                      # 점수순으로 늘어놓는다
    python3 jaso/sift.py --자세히             # 왜 그 점수인지
    python3 jaso/sift.py --버리기 -0.5        # 그 아래를 지운다 (**명시해야 지운다**)

## 왜 있나

긁으면 **아닌 것이 섞인다.** 실측(사용자 런, 23편): 논문 초록 여섯 편이 2만자대로
들어왔고, 음악·지도·라이선스 쪽도 섞였다. 이대로 `mine` 에 넣으면 **논문의 형식이
'합격 자소서의 형식' 으로 집계된다** -- 그리고 그 분포로 만든 문법 후보가 프롬프트에
들어간다. 잡음이 아니라 **틀린 값**이 되는 것이다.

## 지우지 않는다 -- 늘어놓는다

`dig/README.md` 의 규율이다: 줄이면 줄인 것을 아무도 못 되찾는다. 그래서 여기는
**점수와 까닭을 내고 멈춘다.** `--버리기` 에 임계를 **직접 적어야** 지운다.

자동으로 자르지 않는 까닭이 하나 더 있다: 이 자는 **꼴로만 본다.** 뜻을 안 읽으므로
자소서인데 낮게 나오는 것이 있을 수 있고, 그것을 말없이 지우면 아무도 모른다.

## 축 -- 자소서'다움' 이 아니라 **꼴**을 잰다

    나       1인칭 밀도            자소서는 내 이야기다
    겪음     과거 서술 어미        겪은 일을 적는다
    자소서말 지원·역량·포부 …      그 자리에서만 쓰는 말
    학술     초록·키워드·DOI·pp.   **논문이다** (dbpia 가 여기 걸린다)
    상업     장바구니·정가·배송     책·상품 쪽
    목록     로그인·검색·더보기     게시판 껍데기 (JS 로 그린 쪽)

앞 셋은 올리고 뒤 셋은 내린다. **어느 쪽이 몇 점인지는 아래 `무게` 에 적혀 있고,
그것이 이 자의 전부다** -- 숨은 규칙이 없다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import keep as KP                                          # noqa: E402

# (이름, 자, 무게). **무게가 이 자의 전부다** -- 숨은 규칙이 없다.
축들 = (
    ("나", re.compile(r"저는|제가|저의|저를|제\s|나는|내가"), +1.0),
    ("겪음", re.compile(r"(했|였|었|았)(습니다|다)|하였습니다|그때|당시|처음에는|"
                        r"돌이켜|겪었"), +1.0),
    ("자소서말", re.compile(r"지원\s*동기|지원하게|자기소개서|성장\s*과정|입사\s*후|"
                            r"포부|역량|학업\s*계획|편입|합격|면접|직무|"
                            r"장단점|협업|성취"), +1.2),
    ("학술", re.compile(r"초록|Abstract|키워드|Keywords|참고\s*문헌|References|"
                        r"DOI|doi:|Vol\.|No\.|pp\.|학회|논문|연구는|본\s*연구|"
                        r"게재|등재|피인용|권호|저자명"), -2.0),
    ("상업", re.compile(r"장바구니|바로\s*구매|정가|판매가|배송|적립|리뷰\s*\d|"
                        r"품절|재고|결제|쿠폰|할인율|판매지수|출판사|ISBN"), -2.0),
    ("목록", re.compile(r"로그인|회원가입|더\s*보기|전체\s*보기|이전\s*글|다음\s*글|"
                        r"카테고리|태그\s*목록|검색어|공지사항|이용약관|"
                        r"저작권|Copyright|라이선스|License"), -1.5),
)


def 재기(글: str) -> dict:
    """축마다 1,000자당 몇 번. **길이로 나눈다** -- 긴 글이 그냥 이기면 안 된다."""
    n = max(1, len(글 or ""))
    return {이름: round(len(자.findall(글 or "")) * 1000 / n, 2)
            for 이름, 자, _ in 축들}


def 점수(잰것: dict) -> float:
    """무게를 곱해 더한다. 클수록 자소서 꼴이다."""
    무게 = {이름: w for 이름, _, w in 축들}
    return round(sum(잰것.get(이름, 0.0) * 무게[이름] for 이름 in 무게), 2)


def 까닭(잰것: dict) -> str:
    """무엇이 이 점수를 끌었나. **두드러진 축 둘만** -- 다 적으면 안 읽는다."""
    무게 = {이름: w for 이름, _, w in 축들}
    몫 = sorted(((이름, 잰것.get(이름, 0.0) * 무게[이름]) for 이름 in 무게),
               key=lambda kv: -abs(kv[1]))
    return " · ".join(f"{이름} {몫값:+.1f}" for 이름, 몫값 in 몫[:2] if abs(몫값) >= 0.3)


def 훑기(곳: Path | None = None) -> list:
    """`[(경로, 점수, 잰것, 까닭, 글자수)]` -- 점수 낮은 것부터(버릴 것이 위로)."""
    out = []
    for p, 출처, 몸 in KP.읽기(곳):
        잰 = 재기(몸)
        out.append((p, 점수(잰), 잰, 까닭(잰), len(몸), 출처))
    return sorted(out, key=lambda x: x[1])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="긁어 온 것에서 자소서가 아닌 것을 가른다")
    ap.add_argument("--곳", default=str(KP.보기DIR))
    ap.add_argument("--자세히", action="store_true")
    ap.add_argument("--버리기", dest="버리기", type=float, default=None,
                    help="이 점수 아래를 지운다. **임계를 직접 적어야 지운다**")
    a = ap.parse_args(argv)

    것들 = 훑기(Path(a.곳))
    if not 것들:
        print(f"볼 것이 없다: {a.곳}", file=sys.stderr)
        return 3

    print(f"{len(것들)}편 · 점수 낮은 것부터 (낮을수록 자소서가 아니다)\n")
    print(f"{'점수':>7}  {'글자':>7}  {'까닭':<22} 파일")
    for p, s, _, 왜, n, _출처 in 것들:
        print(f"{s:>7.2f}  {n:>7,}  {왜[:22]:<22} {p.name}")
        if a.자세히:
            print(f"         {_출처[:76]}")
    값 = [s for _, s, _, _, _, _ in 것들]
    가온 = sorted(값)[len(값) // 2]
    print(f"\n가운데 {가온:.2f} · 가장 낮은 {값[0]:.2f} · 가장 높은 {값[-1]:.2f}")

    if a.버리기 is None:
        낮은것 = [x for x in 것들 if x[1] < 0]
        print(f"\n음수인 것 {len(낮은것)}편 -- **아직 아무것도 안 지웠다.**")
        print("  이 자는 꼴로만 본다. 뜻을 안 읽으므로 자소서인데 낮게 나오는 것이")
        print("  있을 수 있고, 말없이 지우면 아무도 모른다. 눈으로 보고 자르라:")
        print(f"    python3 jaso/sift.py --곳 {a.곳} --버리기 -0.5")
        return 0

    버릴것 = [x for x in 것들 if x[1] < a.버리기]
    for p, s, _, 왜, n, _o in 버릴것:
        print(f"  지움 {s:>6.2f}  {p.name}  ({왜})")
        p.unlink()
    print(f"\n{len(버릴것)}편 지웠다 · {len(것들) - len(버릴것)}편 남았다")
    print("\n남은 것으로 다시:  python3 jaso/mine.py --분포  ·  jaso/beats.py --차례")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
