"""**스키마 -- 배경지식을 적은 표.** 데이터가 아니다.

여태 지은 것(`brief/`)은 원장에서 수를 받아 통계로 판정했다. 그것은 **데이터 분석**이지
추론이 아니다. 추론은 **아는 것(스키마)에서 결론을 끌어내는 일**이고, 그 자리는 이미
`law/issue.py` 에 있었다 -- 요건표와 양측 입장만으로 "어느 요건이 결론을 지고 있나" 를
계산한다. 데이터가 한 줄도 안 든다.

여기서는 그것을 도메인 밖으로 뺀다. 법에 묶여 있던 것은 단계 이름뿐이었다:

    법                              여기
    권리근거 · 구성요건 · 적법요건    **세움**      -- 다 서야 주장이 선다
    권리장애 · 위법성조각 · ...       **무너뜨림**  -- 하나만 서도 주장이 무너진다
    재항변(defeats)                  **무너뜨림 대상**  -- 이미 도메인을 몰랐다

## 스키마가 참인지는 **못 본다** -- 그래서 보여 준다

`law/` 는 요건이 실재하는 조문에 걸렸는지 원장으로 대조했다(L001). 모든 분야에 원장을
만들 수는 없다 -- 사용자가 그 길을 골랐다. 그러면 남는 것이 무엇인가.

    스키마가 참인가        **관할 밖.** 외적 정당화다(law/METHOD.md 1-7)
    스키마에서 결론이 따라 나오는가   **기계가 본다.** 내적 정당화다

그러니 **결론은 스키마에 조건부**다. 그리고 조건부인 결론을 낼 때 지켜야 할 것이 하나
있다 -- **스키마를 통째로 같이 보여 준다.** 결론만 보이고 전제를 숨기면, 검사받지 않은
전제 위에 검사받은 결론이 얹히고 읽는 사람은 그 둘을 구별할 수 없다.

## 그래서 검사하는 것은 '내용' 이 아니라 '성함' 이다

    S001  요건 id 가 겹치지 않는가        겹치면 어느 것을 가리키는지 모른다
    S002  무너뜨림이 실재하는 요건을 가리키는가   없는 것은 못 무너뜨린다
    S003  무너뜨림에 되돌이가 없는가       서로 무너뜨리면 결론이 안 정해진다
    S004  양측 입장이 다 적혔는가          한쪽만 있는 것은 다툼이 아니라 설명이다
    S005  **요건마다 출처가 적혔는가**      안 적혔으면 '모델이 지어낸 것' 이라고 적는다

S005 가 원장 대조를 대신하는 자리다. 대조는 못 해도 **어디서 왔다고 말했는지**는 남길 수
있고, 안 남겼으면 그것을 화면에 크게 적을 수는 있다. 검사가 아니라 **표시**다 -- 이
저장소가 미검증을 다뤄 온 방식과 같다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

세움 = "세움"
무너뜨림 = "무너뜨림"
역할들 = (세움, 무너뜨림)


@dataclass
class 요건:
    id: str
    말: str
    역할: str = 세움
    무너뜨림: str = ""       # 이 요건이 서면 저 요건(id)이 무너진다 -- 재반박 사슬
    출처: str = ""           # **어디서 온 배경지식인가.** 비면 지어낸 것으로 다룬다
    원용필요: bool = False   # 상대가 꺼내야만 보는 것(법의 항변사항 같은 자리)
    원용됨: bool = False


@dataclass
class 스키마:
    물음: str = ""
    세우는쪽: str = "세우는 쪽"
    다투는쪽: str = "다투는 쪽"
    요건: list = field(default_factory=list)
    입장: dict = field(default_factory=dict)     # id -> {쪽: bool}

    def 찾기(self, eid: str):
        return next((e for e in self.요건 if e.id == eid), None)

    def 쪽들(self) -> tuple:
        return (self.세우는쪽, self.다투는쪽)

    @property
    def 출처없음(self) -> list:
        """출처가 안 적힌 요건. **이것이 비어 있지 않으면 화면이 그렇게 말한다.**"""
        return [e for e in self.요건 if not e.출처.strip()]


@dataclass
class 위반:
    규칙: str
    등급: str
    어디: str
    말: str

    def __str__(self) -> str:
        return f"[{self.규칙}/{self.등급}] {self.어디}: {self.말}"


AIM = {
    "S001": "요건 id 가 겹치지 않아야 한다",
    "S002": "무너뜨림이 실재하는 요건을 가리켜야 한다",
    "S003": "무너뜨림에 되돌이가 없어야 한다",
    "S004": "양측 입장이 다 적혀야 한다",
    "S005": "요건마다 출처가 적혀야 한다 (안 적혔으면 지어낸 것으로 다룬다)",
}


def 읽기(d) -> 스키마:
    """dict 나 JSON 문자열 -> 스키마. **꼴이 아니면 빈 스키마다.**"""
    if isinstance(d, str):
        try:
            d = json.loads(d)
        except json.JSONDecodeError:
            return 스키마()
    if not isinstance(d, dict):
        return 스키마()
    es = []
    for x in (d.get("요건") or []):
        if not isinstance(x, dict) or not str(x.get("id") or "").strip():
            continue
        역 = str(x.get("역할") or 세움)
        es.append(요건(id=str(x["id"]).strip(), 말=str(x.get("말") or ""),
                      역할=역 if 역 in 역할들 else 세움,
                      무너뜨림=str(x.get("무너뜨림") or ""),
                      출처=str(x.get("출처") or ""),
                      원용필요=bool(x.get("원용필요")),
                      원용됨=bool(x.get("원용됨"))))
    입장 = d.get("입장") if isinstance(d.get("입장"), dict) else {}
    입장 = {k: {kk: bool(vv) for kk, vv in v.items()}
            for k, v in 입장.items() if isinstance(v, dict)}
    return 스키마(물음=str(d.get("물음") or ""),
                 세우는쪽=str(d.get("세우는쪽") or "세우는 쪽"),
                 다투는쪽=str(d.get("다투는쪽") or "다투는 쪽"),
                 요건=es, 입장=입장)


def _되돌이(s: 스키마) -> list:
    """무너뜨림을 따라가다 자기로 돌아오는 사슬. **결론이 안 정해지는 자리다.**"""
    대상 = {e.id: e.무너뜨림 for e in s.요건 if e.무너뜨림}
    돈것 = []
    for start in 대상:
        본, cur = [], start
        while cur and cur not in 본:
            본.append(cur)
            cur = 대상.get(cur, "")
        if cur and cur in 본:
            고리 = 본[본.index(cur):]
            if sorted(고리) not in [sorted(x) for x in 돈것]:
                돈것.append(고리)
    return 돈것


def 검사(s: 스키마) -> list:
    """S001~S005. **스키마가 참인지는 안 본다** -- 성한지만 본다."""
    vs = []
    ids = [e.id for e in s.요건]
    for eid in {i for i in ids if ids.count(i) > 1}:
        vs.append(위반("S001", "hard", eid,
                      f"같은 id 가 {ids.count(eid)}번 있다 -- 어느 것을 가리키는지 모른다"))
    있는 = set(ids)
    for e in s.요건:
        if e.무너뜨림 and e.무너뜨림 not in 있는:
            vs.append(위반("S002", "hard", e.id,
                          f"없는 요건을 무너뜨린다고 한다: {e.무너뜨림!r}"))
    for 고리 in _되돌이(s):
        vs.append(위반("S003", "hard", " -> ".join(고리),
                      "무너뜨림이 되돌이다 -- 서로 무너뜨리면 결론이 안 정해진다"))
    for e in s.요건:
        pos = s.입장.get(e.id, {})
        if len(pos) < 2:
            vs.append(위반("S004", "soft", e.id,
                          f"입장이 {len(pos)}쪽만 적혔다 -- 한쪽 말만 있는 것은 "
                          "다툼이 아니라 설명이다"))
    빈출처 = s.출처없음
    if 빈출처:
        vs.append(위반("S005", "soft", f"{len(빈출처)}개",
                      "출처가 안 적힌 요건이 있다 -- 어디서 온 배경지식인지 모르면 "
                      "**모델이 지어낸 것으로 다뤄야 한다**: "
                      + ", ".join(e.id for e in 빈출처[:6])))
    return vs


def hard(vs) -> list:
    return [v for v in vs if v.등급 == "hard"]
