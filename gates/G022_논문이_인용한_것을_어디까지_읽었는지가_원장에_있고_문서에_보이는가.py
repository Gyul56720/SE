"""
G022 -- 논문이 인용한 것을 **실제로 어디까지 읽었는지**가 원장에 있고 문서에 보이는가.

사용자(2026-09-18): "반복되는 잘못되는 측정, 논리적 결함, 이미 있는 연구의 반복, 그리고
너무나도 큰 과장. 이건 사용자에 관한 기만이라고 느껴졌다."

실측 2026-09-17 (`ff31763`): `paper/recurrence_hls_IEEE.html` 의 참고문헌 28개 중 **18개**가
`[verify ...]` 표시를 단 채로 1차본에 들어갔다. `paper/multiplier_free_lookup_eq_IEEE.html`
은 25개 중 **21개**였다. `[verify]` 는 "전문을 안 봤다" 는 뜻이다. 그러니까 그 원고는
**읽지 않은 문헌 위에 서 있었다.** 그런데 문서 어디에도 "이 인용은 검색 조각만 보고 적었다"
고 적혀 있지 않았다 -- `[verify pages]` 는 쪽수만 못 맞춘 것처럼 읽힌다.

인용을 안 읽고 다는 것이 이 저장소가 다섯 번 같은 주제에서 진 경로다. 남이 이미 한 것을
모르는 채로 짓고, 다 짓고 나서 알게 된다.

## 무엇을 위반으로 보는가

`paper/*.html` 의 참고문헌 목록(`<div class="ref">` 안의 `<li>`) 각각에 대해:

  1. `paper/출처.jsonl` 에 그 논문·번호의 행이 있어야 한다
  2. 행에 `확인수준` (전문|초록|목록|조각), `날짜`, `질의`, `어디서` 가 **비어 있지 않아야** 한다
  3. 그 `<li>` 안에 `[출처:<확인수준>]` 이 **글자로 보여야** 한다

3번이 이 게이트의 핵심이다. 원장만 요구하면 원장은 서랍에 들어가고 독자는 못 본다. 읽은
수준을 문서 표면에 강제로 올려서, **안 읽고 인용한 것이 읽는 사람 눈에 띄게** 한다.

## 무엇을 안 잡는가 -- 그리고 왜

  · `attic/` 은 안 본다 -- 폐기한 원고의 무덤이다. 거기 남은 것이 RED 증명의 근거다
  · 원장에 `전문` 이라고 **거짓으로** 적는 것은 못 잡는다. 기계가 독서를 확인할 길은 없다.
    이 게이트가 하는 일은 그 거짓을 **한 줄로 명시하게** 만드는 것뿐이다 -- 얼버무림과
    명시적 거짓은 다르다
  · 인용이 적절한지, 그 논문이 정말 그 말을 하는지는 안 본다
"""
from __future__ import annotations

import json
import re

RULE_ID = "G022"
TITLE = "논문이 인용한 것을 어디까지 읽었는지가 원장에 있고 문서에 보이는가"
ORIGIN = "ff31763 (참고문헌 28개 중 18개가 [verify] 인 채로 1차본에 들어갔다)"
EVIDENCE = "attic/폐기논문/README.md"

_원장이름 = "paper/출처.jsonl"
_수준들 = ("전문", "초록", "목록", "조각")
_필수 = ("확인수준", "날짜", "질의", "어디서")

_참고구획 = re.compile(r'<div[^>]*class="[^"]*\bref\b[^"]*"[^>]*>(.*?)</div>', re.S)
_항목 = re.compile(r"<li\b[^>]*>(.*?)</li>", re.S)


def _논문들(ctx):
    자리 = ctx.repo / "paper"
    if not 자리.is_dir():
        return []
    return sorted(p for p in 자리.glob("*.html") if p.is_file())


def _인용수(글: str) -> int:
    구획 = _참고구획.search(글)
    return len(_항목.findall(구획.group(1))) if 구획 else 0


def _인용글(글: str) -> "list[str]":
    구획 = _참고구획.search(글)
    return _항목.findall(구획.group(1)) if 구획 else []


def _원장(ctx) -> "tuple[dict, str | None]":
    """{(논문, 번호): 행}. 두 번째 값은 원장 자체가 잘못됐을 때의 위반 문구."""
    p = ctx.repo / _원장이름
    if not p.is_file():
        return {}, None
    표 = {}
    for n, 줄 in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        줄 = 줄.strip()
        if not 줄 or 줄.startswith("#"):
            continue
        try:
            행 = json.loads(줄)
        except ValueError as e:
            return {}, f"{_원장이름}:{n}: JSON 이 깨졌다 ({e}) -- 원장이 읽히지 않으면 게이트가 무력하다."
        try:
            표[(str(행.get("논문", "")), int(행.get("번호", -1)))] = 행
        except (TypeError, ValueError):
            return {}, f"{_원장이름}:{n}: '논문'/'번호' 가 없거나 번호가 정수가 아니다."
    return 표, None


def check(ctx) -> "list[str]":
    논문들 = _논문들(ctx)
    if not 논문들:
        return []                                   # 살아 있는 원고가 없다 -- 막을 것이 없다
    표, 깨짐 = _원장(ctx)
    if 깨짐:
        return [깨짐]

    위반 = []
    for path in 논문들:
        이름 = path.name
        try:
            글 = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        항목들 = _인용글(글)
        if not 항목들:
            continue                                # 참고문헌이 없는 문서 -- 이 게이트 밖이다
        for i, 항목 in enumerate(항목들, 1):
            행 = 표.get((이름, i))
            if 행 is None:
                위반.append(
                    f"{이름} 참고문헌 [{i}]: {_원장이름} 에 행이 없다 -- 어디서 어떻게 찾았고 "
                    f"어디까지 읽었는지가 없는 인용이다. "
                    f'{{"논문":"{이름}","번호":{i},"확인수준":"조각","날짜":"YYYY-MM-DD",'
                    f'"질의":"…","어디서":"…"}} 를 넣어라.')
                continue
            빈칸 = [k for k in _필수 if not str(행.get(k, "")).strip()]
            if 빈칸:
                위반.append(f"{이름} 참고문헌 [{i}]: {_원장이름} 의 행에 {', '.join(빈칸)} 이(가) 비어 있다.")
                continue
            수준 = str(행["확인수준"]).strip()
            if 수준 not in _수준들:
                위반.append(f"{이름} 참고문헌 [{i}]: 확인수준 '{수준}' 은(는) {_수준들} 중 하나여야 한다.")
                continue
            표식 = f"[출처:{수준}]"
            if 표식 not in 항목:
                위반.append(
                    f"{이름} 참고문헌 [{i}]: 문서에 {표식} 이(가) 안 보인다 -- 원장에만 적고 "
                    f"독자에게 감추면 이 게이트는 아무것도 막지 못한다. 그 <li> 안에 그대로 적어라.")
    return 위반
