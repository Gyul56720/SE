"""**문제 -> 풀이 -> 오답노트 -> 취약점 -> 교안.** 한 원장 위에서.

    python3 study/run.py --넣기 문제.json          # 문제를 공책에 넣는다
    python3 study/run.py --낼것                    # 아직 안 푼 문제 하나 (정답 감춤)
    python3 study/run.py --낼것 --태그 확률 --몇 3
    python3 study/run.py --답 q12 '3' --메모 '조건부를 곱셈으로 봤다'
    python3 study/run.py --맞음 q12 / --틀림 q12   # 서술형처럼 못 채점한 것을 사람이 정함
    python3 study/run.py --오답노트
    python3 study/run.py --취약점
    python3 study/run.py --교안
    python3 study/run.py --사유 q12 '조건부확률에서 분모를 전체로 잡는다'
    python3 study/run.py --사유프롬프트 / --사유붙이기 답.json
    python3 study/run.py --태그프롬프트 / --태그붙이기 답.json / --흩어짐

## 취약점은 태그가 아니라 **사유**로 센다

과목(`확률`)이 아니라 **어긋난 자리**(`조건부확률에서 분모를 전체로 잡는다`)여야
고칠 데가 정해진다. 그래서 틀린 것마다 사유를 적는다 -- 손으로 `--사유`, 또는
`--사유프롬프트`/`--사유붙이기` 로 모델이.

한때 그 앞에 "오답인가 모름인가" 를 1·2 로 묻는 걸음이 있었는데 뺐다(사용자 지시
2026-09-09). **묻는 걸음이 하나 늘면 그만큼 안 적히고, 안 적히면 셈에 안 들어간다** --
갈래를 알아도 사유가 없으면 아무것도 못 하는데 갈래부터 물으면 사유까지 못 간다.

    끝값 0 냈다 · 1 못 했다(무엇이 없는지 적는다) · 3 무엇을 할지 안 정해졌다

## 문제는 어디서 오나

**여기서 지어내지 않는다.** 셋 중 하나다.

    사용자가 붙여넣는다        --넣기 문제.json  (또는 `-` 로 표준입력)
    dig 로 긁어 온다           python3 dig/run.py --url '<기출 주소>' --json
    이미 공책에 있다           --낼것 이 아직 안 푼 것에서 고른다

문제를 지어내면 정답도 지어내게 되고, 그러면 오답노트가 통째로 창작이 된다.
그 위에서 도는 취약점 판정은 더 나쁘다 -- 지어낸 약점을 근거 있는 얼굴로 낸다.

## `--낼것` 은 정답을 안 보여 준다

당연해 보이지만 안 그러면 검사가 아니다. 정답은 공책에 있고 화면에만 안 나온다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from study import note as NT                                   # noqa: E402
from study import plan as PL                                   # noqa: E402
from study import tag as TG                                    # noqa: E402
from study import weak as WK                                   # noqa: E402


def _문제들(d) -> list:
    """dict/list/JSONL 어느 꼴로 와도 문제를 뽑는다. **꼴 때문에 못 넣는 일이 없게.**"""
    if isinstance(d, dict):
        d = d.get("문제") if isinstance(d.get("문제"), list) else [d]
    if not isinstance(d, list):
        return []
    out = []
    for i, x in enumerate(d, 1):
        if not isinstance(x, dict):
            continue
        qid = str(x.get("id") or x.get("번호") or f"q{i}").strip()
        말 = str(x.get("말") or x.get("문제") or x.get("question") or "")
        if not 말.strip():
            continue
        태 = x.get("태그") or x.get("tags") or []
        out.append(NT.문제(
            id=qid, 말=말, 정답=str(x.get("정답") or x.get("answer") or ""),
            태그=[str(t) for t in (태 if isinstance(태, list) else [태])],
            보기=[str(t) for t in (x.get("보기") or x.get("choices") or [])],
            해설=str(x.get("해설") or x.get("explanation") or ""),
            출처=str(x.get("출처") or x.get("source") or "")))
    return out


def 넣기(자리, raw: str) -> int:
    n = NT.읽기(자리)
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        d = [json.loads(줄) for 줄 in raw.splitlines()
             if 줄.strip().startswith("{")]
    qs = _문제들(d)
    if not qs:
        print("**문제를 못 읽었다.** JSON 이 아니거나 `말`(문제 본문)이 비었다.")
        print('  꼴: [{"id":"q1","말":"...","정답":"...","태그":["확률"],'
              '"해설":"...","출처":"..."}]')
        return 1
    빈정답 = [q.id for q in qs if not q.정답.strip()]
    빈출처 = [q.id for q in qs if not q.출처.strip()]
    for q in qs:
        n.넣기(q)
    NT.저장(n, 자리)
    print(f"문제 {len(qs)}개 넣었다 (공책에 모두 {len(n.문제)}개)")
    if 빈정답:
        print(f"  **정답이 없는 것 {len(빈정답)}개**: {', '.join(빈정답[:8])} -- "
              "채점을 못 하고, 채점 못 한 것은 취약점 셈에 안 들어간다")
    if 빈출처:
        print(f"  출처 없는 것 {len(빈출처)}개: {', '.join(빈출처[:8])} -- "
              "어디서 왔는지 모르면 정답도 못 되짚는다")
    return 0


def 낼것(자리, 태그: str, 몇: int) -> int:
    n = NT.읽기(자리)
    것들 = n.안푼것(태그)
    if not 것들:
        print(f"낼 문제가 없다{f' (태그 {태그})' if 태그 else ''}. "
              f"공책 {len(n.문제)}개 중 {len(n.푼것())}개를 이미 풀었다.")
        print("  `--넣기` 로 더 넣거나, `dig/run.py` 로 긁어 오라.")
        return 1
    for q in 것들[:max(1, 몇)]:
        print(f"[{q.id}] {' · '.join(q.태그) or '(태그없음)'}")
        print(f"  {q.말}")
        for i, b in enumerate(q.보기, 1):
            print(f"    {i}) {b}")
        print()
    print(f"답: python3 study/run.py --답 {것들[0].id} '<답>' --메모 '<어떻게 풀었나>'")
    print("**정답은 안 보여 준다** -- 공책에는 있다.")
    return 0


def 답하기(자리, qid: str, 답: str, 메모: str, 초: float) -> int:
    n = NT.읽기(자리)
    q = n.문제.get(qid)
    if not q:
        print(f"**그런 문제가 없다: {qid}** -- `--낼것` 으로 id 를 보라.")
        return 1
    맞 = NT.채점(q.정답, 답)
    n.시도.append(NT.시도(문제id=qid, 낸답=답, 맞았나=맞, 언제=NT.지금(),
                        걸린초=초, 메모=메모))
    NT.저장(n, 자리)
    if 맞 is True:
        print(f"[{qid}] 맞았다.")
    elif 맞 is False:
        print(f"[{qid}] **틀렸다.**  낸 답: {답}   정답: {q.정답}")
        if q.해설:
            print(f"  해설: {q.해설}")
        print(_사유물음(qid))
    else:
        # **억지로 참·거짓을 내지 않는다.** 우기면 그 우김 위에서 취약점이 돈다
        print(f"[{qid}] **채점을 못 했다.** 글자로 맞춰 볼 수 있는 답이 아니다.")
        print(f"  낸 답: {답}")
        print(f"  정답:  {q.정답}")
        print(f"  네가 정해라: python3 study/run.py --맞음 {qid}   또는   --틀림 {qid}")
    return 0


def _사유물음(qid: str) -> str:
    """**무엇이 어긋났는지 적으라고 한다.** 한 걸음이다.

    한때 여기서 "오답인가 모름인가" 를 먼저 물었다(1·2). 사용자가 뺐다 -- 걸음이
    하나 늘면 그만큼 안 적히고, **안 적힌 것은 셈에 안 들어간다.** 갈래를 알아도
    사유가 없으면 아무것도 못 한다.
    """
    return (f"\n  **무엇이 어긋났나?** (과목 말고 그 자리)\n"
            f"    python3 study/run.py --사유 {qid} '조건부확률에서 분모를 전체로 잡는다'\n"
            "  지금 안 적어도 된다 -- `--사유프롬프트` 로 모델이 붙인다. "
            "다만 **비어 있으면 취약점 셈에 안 들어간다.**")


def 사유적기(자리, qid: str, 사유: str) -> int:
    n = NT.읽기(자리)
    a = n.마지막(qid)
    if not a:
        print(f"**그 문제에 시도가 없다: {qid}** -- `--답` 부터.")
        return 1
    사유 = 사유.strip()
    if not 사유:
        print("**무엇이 어긋났는지 적어라.** 비면 셈에 안 들어간다.")
        return 1
    # **여기서도 묶는다.** 손으로 적으면 매번 조금씩 달라 같은 오개념이 넷으로
    # 갈라진다(실측). 그러면 되풀이가 안 보이고, 되풀이를 보는 것이 이 자리의 전부다.
    이미 = sorted({x.사유 for x in n.시도 if x.사유})
    표 = TG.묶기(이미 + [사유])
    a.사유 = 표.get(사유, 사유)
    NT.저장(n, 자리)
    print(f"[{qid}] 사유: {a.사유}")
    if a.사유 != 사유:
        print(f"  닮아서 이미 쓰던 이름으로 묶었다 (적은 것: {사유})")
    return 0


def 정하기(자리, qid: str, 맞았나: bool) -> int:
    n = NT.읽기(자리)
    a = n.마지막(qid)
    if not a:
        print(f"**그 문제에 시도가 없다: {qid}** -- `--답` 부터.")
        return 1
    a.맞았나 = 맞았나
    NT.저장(n, 자리)
    print(f"[{qid}] {'맞음' if 맞았나 else '틀림'} 으로 정했다.")
    return 0


def 짚기(자리, qid: str, 말: str) -> int:
    n = NT.읽기(자리)
    a = n.마지막(qid)
    if not a:
        print(f"**그 문제에 시도가 없다: {qid}**")
        return 1
    a.짚은것 = 말
    NT.저장(n, 자리)
    print(f"[{qid}] 짚어 뒀다. 교안에 근거로 실린다.")
    return 0


def 태그프롬프트(자리, 태그없는것만: bool, 몇: int) -> int:
    n = NT.읽기(자리)
    것들 = [q for q in n.문제.values() if not (태그없는것만 and q.태그)]
    if not 것들:
        print("태그를 붙일 문제가 없다. (`--전부` 를 주면 이미 붙은 것도 다시 낸다)")
        return 1
    이미 = sorted({t for q in n.문제.values() for t in (q.태그 or [])})
    print(TG.프롬프트(것들[:max(1, 몇)], 이미))
    return 0


def 태그붙이기(자리, raw: str, 덮어쓰기: bool) -> int:
    n = NT.읽기(자리)
    표 = TG.읽기(raw)
    if not 표:
        print("**태그를 못 읽었다.** JSON 이 아니거나 비었다.")
        print('  꼴: {"태그": {"q1": ["확률", "조건부"]}}')
        return 1
    r = TG.붙이기(n, 표, 덮어쓰기)
    NT.저장(n, 자리)
    print(f"태그를 {r['붙임']}문제에 붙였다"
          + (f" · 이미 있어 건너뜀 {r['건너뜀']}" if r["건너뜀"] else "")
          + (f" · 없는 id {len(r['없는id'])}" if r["없는id"] else ""))
    if r["모은것"]:
        # **합친 것을 말한다.** 조용히 합치면 화면의 태그가 모델이 쓴 것과 달라져
        # 읽는 쪽이 어긋난 것을 못 알아챈다.
        print("  같은 것으로 모았다 (안 모으면 표본이 갈라져 아무것도 못 가른다):")
        for a, b in r["모은것"].items():
            print(f"    {a} -> {b}")
    if r["없는id"]:
        print(f"  공책에 없는 id: {', '.join(r['없는id'][:8])}")
    흩 = TG.흩어짐(n)
    if 흩["흩어짐"]:
        print(f"  **태그가 잘게 쪼개졌다**: 태그 {흩['태그수']}개에 채점된 문제 "
              f"{흩['채점된문제']}개 (태그당 평균 {흩['태그당평균']:.1f}). "
              f"이 태그 수로는 태그마다 {흩['태그당필요']}문제쯤은 있어야 가른다.")
        if 흩["작은태그"]:
            print(f"    문제가 모자란 태그: {', '.join(흩['작은태그'][:10])}")
    if 흩["닮은쌍"]:
        # **합치지는 않는다.** 뜻으로 합치면 짐작이고, 말 안 하면 사용자는 표본이
        # 왜 안 모이는지 모른 채 늘 `못잼` 만 본다.
        print("  합칠 만해 보이는 짝 (합치지는 않았다 -- 뜻으로 합치는 것은 짐작이다):")
        for a, b, v in 흩["닮은쌍"][:8]:
            print(f"    {v:.2f}  {a}  ~  {b}")
        print("    합치려면 `--태그붙이기` 에 같은 이름으로 다시 주고 `--덮어쓰기`")
    return 0


def 사유프롬프트(자리, 몇: int) -> int:
    n = NT.읽기(자리)
    것들 = [(n.문제[a.문제id], a) for a in n.사유없는것() if a.문제id in n.문제]
    if not 것들:
        print("사유를 붙일 것이 없다 (틀린 것이 없거나 이미 다 적혔다).")
        return 1
    이미 = sorted({a.사유 for a in n.시도 if a.사유})
    print(TG.사유프롬프트(것들[:max(1, 몇)], 이미))
    return 0


def 사유붙이기(자리, raw: str, 덮어쓰기: bool) -> int:
    n = NT.읽기(자리)
    표 = TG.사유읽기(raw)
    if not 표:
        print("**사유를 못 읽었다.** JSON 이 아니거나 비었다.")
        print('  꼴: {"사유": {"q1": "조건부확률에서 분모를 전체로 잡는다"}}')
        return 1
    r = TG.사유붙이기(n, 표, 덮어쓰기)
    NT.저장(n, 자리)
    print(f"사유를 {r['붙임']}개에 붙였다"
          + (f" · 이미 있어 건너뜀 {r['건너뜀']}" if r["건너뜀"] else "")
          + (f" · 없는 id {len(r['없는id'])}" if r["없는id"] else ""))
    if r["모은것"]:
        print("  닮아서 한 이름으로 묶었다 (안 묶으면 되풀이가 안 보인다):")
        for a, b in r["모은것"].items():
            print(f"    {a}\n      -> {b}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="문제 -> 오답노트 -> 취약점 -> 교안")
    ap.add_argument("--공책", dest="자리", default="", help="공책 자리 (기본 study/공책)")
    ap.add_argument("--넣기", dest="put", default="", help="문제 JSON 파일 (`-` 표준입력)")
    ap.add_argument("--낼것", dest="ask", action="store_true", help="안 푼 문제를 낸다")
    ap.add_argument("--태그", dest="tag", default="")
    ap.add_argument("--몇", dest="howmany", type=int, default=1)
    ap.add_argument("--답", dest="answer", nargs=2, metavar=("문제id", "답"))
    ap.add_argument("--메모", dest="memo", default="")
    ap.add_argument("--초", dest="secs", type=float, default=0.0)
    ap.add_argument("--맞음", dest="right", default="")
    ap.add_argument("--틀림", dest="wrong", default="")
    ap.add_argument("--짚기", dest="point", nargs=2, metavar=("문제id", "무엇"))
    ap.add_argument("--사유", dest="why", nargs="+", metavar="문제id 무엇이",
                    help="틀린 자리를 적는다 (과목 말고 어긋난 자리)")
    ap.add_argument("--사유프롬프트", dest="whyask", action="store_true",
                    help="틀린 것마다 무엇이 어긋났는지 모델에게 물을 것 (호출 0회)")
    ap.add_argument("--사유붙이기", dest="whyput", default="",
                    help="모델이 답한 사유 JSON (`-` 표준입력)")
    ap.add_argument("--태그프롬프트", dest="tagask", action="store_true",
                    help="태그를 붙일 때 모델에게 줄 것 (호출 0회)")
    ap.add_argument("--태그붙이기", dest="tagput", default="",
                    help="모델이 답한 태그 JSON (`-` 표준입력)")
    ap.add_argument("--전부", dest="alltags", action="store_true",
                    help="--태그프롬프트 에서 이미 태그가 붙은 것도 낸다")
    ap.add_argument("--덮어쓰기", dest="overwrite", action="store_true",
                    help="--태그붙이기 에서 이미 있는 태그를 덮는다")
    ap.add_argument("--흩어짐", dest="spread", action="store_true",
                    help="태그가 잘게 쪼개져 못 가르는 상태인지 본다")
    ap.add_argument("--오답노트", dest="wrongbook", action="store_true")
    ap.add_argument("--취약점", dest="weak", action="store_true")
    ap.add_argument("--교안", dest="lesson", action="store_true")
    ap.add_argument("--제목", dest="title", default="")
    a = ap.parse_args(argv)
    자리 = Path(a.자리) if a.자리 else None

    if a.put:
        raw = sys.stdin.read() if a.put == "-" else Path(a.put).read_text(encoding="utf-8")
        return 넣기(자리, raw)
    if a.ask:
        return 낼것(자리, a.tag, a.howmany)
    if a.answer:
        return 답하기(자리, a.answer[0], a.answer[1], a.memo, a.secs)
    if a.right:
        return 정하기(자리, a.right, True)
    if a.wrong:
        return 정하기(자리, a.wrong, False)
    if a.point:
        return 짚기(자리, a.point[0], a.point[1])
    if a.why:
        return 사유적기(자리, a.why[0], " ".join(a.why[1:]))
    if a.whyask:
        return 사유프롬프트(자리, a.howmany if a.howmany > 1 else 40)
    if a.whyput:
        raw = (sys.stdin.read() if a.whyput == "-"
               else Path(a.whyput).read_text(encoding="utf-8"))
        return 사유붙이기(자리, raw, a.overwrite)
    if a.tagask:
        return 태그프롬프트(자리, not a.alltags, a.howmany if a.howmany > 1 else 60)
    if a.tagput:
        raw = (sys.stdin.read() if a.tagput == "-"
               else Path(a.tagput).read_text(encoding="utf-8"))
        return 태그붙이기(자리, raw, a.overwrite)

    n = NT.읽기(자리)
    if a.wrongbook:
        print(PL.오답노트(n, a.tag))
        return 0
    if a.weak:
        # **구체적인 것을 먼저 낸다.** 과목 수준은 그 아래에 붙인다 --
        # 사용자가 요구한 것은 "(특정 과목)에 취약" 이 아니라 어긋난 자리다.
        print(PL.사유보고(n))
        print()
        print(PL.취약점보고(n))
        return 0
    if a.lesson:
        print(PL.교안(n, a.title))
        return 0
    if a.spread:
        흩 = TG.흩어짐(n)
        print(f"태그 {흩['태그수']}개 (그중 잴 수 있는 것 {흩['잴수있는태그']}개) · "
              f"채점된 문제 {흩['채점된문제']}개 · 태그당 평균 {흩['태그당평균']:.1f}")
        print(f"  이 태그 수로 가르려면 태그마다 {흩['태그당필요']}문제쯤 필요하다")
        if 흩["작은태그"]:
            print(f"  문제가 모자란 태그: {', '.join(흩['작은태그'])}")
        for a, b, v in 흩["닮은쌍"][:8]:
            print(f"  합칠 만해 보임({v:.2f}): {a}  ~  {b}")
        print("  **흩어졌다** -- 태그를 합치거나 문제를 더 풀어라"
              if 흩["흩어짐"] else "  괜찮다")
        return 0

    전, 틀, p0 = WK.전체기저(n)
    print(f"공책: 문제 {len(n.문제)}개 · 시도 {len(n.시도)}개 · "
          f"채점됨 {전}개 · 오답률 {p0:.0%}")
    print("  --넣기 문제.json / --낼것 / --답 <id> '<답>' / "
          "--오답노트 / --취약점 / --교안")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
