# -*- coding: utf-8 -*-
"""장 HTML 을 **파일로 꺼내 커밋한다** -- 번역과 색인이 VM 에서도 돌게.

## 왜

장은 `edu/*.py` 가 그릴 때마다 만들어 내고, 그 렌더는 저장소 **밖**의 자료
(`/home/user/edu/zoo.json` · `/home/user/ipzoo/...`)를 읽는다.  VM 에는 그것이
없다 -- 그래서 VM 에서는 장을 한 장도 못 짓는다.

번역(`edu/번역/translate.py`)은 Gemini 키가 있는 **VM 에서** 돌아야 하는데,
지금까지는 장을 직접 import 해서 그렸다.  그러면 VM 에서 못 돈다.  그래서
여기서 한 번 꺼내 `edu/원문/` 에 커밋한다 -- 색인(`edu/kb/`)과 같은 처리다.

    python3 edu/원문내기.py          # edu/원문/<모듈>.<함수>.html + 차례.json

## 왜 색인(kb.jsonl)을 안 쓰나

색인은 **글만** 뽑은 것이라 태그가 없다.  번역은 태그를 그대로 지켜야 하고
(`대조()` 가 태그열을 바이트로 맞춘다), 그림·표·코드가 원래 자리에 있어야 한다.
그러니 번역이 먹는 것은 **HTML 원문**이어야 한다.
"""
import json
import os
import sys

여기 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, 여기)
곳 = os.path.join(여기, "원문")
차례경로 = os.path.join(곳, "차례.json")


def 내기(보고=print):
    import kb
    os.makedirs(곳, exist_ok=True)
    차례, 못한것 = [], []
    for 모듈, fn, 오류 in kb.장함수들():
        if fn is None:
            continue
        try:
            h = getattr(sys.modules[모듈], fn)()
        except Exception as e:                       # noqa: BLE001
            못한것.append(f"{모듈}.{fn}: {repr(e)[:100]}")
            continue
        이름 = f"{모듈}.{fn}.html"
        open(os.path.join(곳, 이름), "w", encoding="utf-8").write(h)
        차례.append({"파일": 이름, "모듈": 모듈, "함수": fn, "자": len(h)})
    json.dump({"장": 차례, "못한것": 못한것}, open(차례경로, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    보고(f"원문 {len(차례)}장 · {sum(c['자'] for c in 차례):,}자 -> {곳}"
       + (f" · 못한 것 {len(못한것)}" if 못한것 else ""))
    return 차례


def 읽기():
    """[(키, 파일경로, html)] -- 번역이 먹는다.  없으면 빈 목록."""
    if not os.path.exists(차례경로):
        return []
    j = json.load(open(차례경로, encoding="utf-8"))
    난것 = []
    for c in j["장"]:
        p = os.path.join(곳, c["파일"])
        if os.path.exists(p):
            난것.append((c["모듈"].split("_")[0], p,
                       open(p, encoding="utf-8").read()))
    return 난것


if __name__ == "__main__":
    내기()
