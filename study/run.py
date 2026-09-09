"""**문제 -> 풀이 -> 오답노트 -> 취약점 -> 교안.** 한 원장 위에서.

    python3 study/run.py --넣기 문제.json          # 문제를 공책에 넣는다
    python3 study/run.py --낼것                    # 아직 안 푼 문제 하나 (정답 감춤)
    python3 study/run.py --낼것 --태그 확률 --몇 3
    python3 study/run.py --답 q12 '3' --메모 '조건부를 곱셈으로 봤다'
    python3 study/run.py --맞음 q12 / --틀림 q12   # 서술형처럼 못 채점한 것을 사람이 정함
    python3 study/run.py --오답노트
    python3 study/run.py --취약점
    python3 study/run.py --교안
    python3 study/run.py --짚기 q12 '조건부확률에서 분모를 전체로 잡았다'

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
        print(f"  왜 틀렸는지 짚어 두라: python3 study/run.py --짚기 {qid} '<무엇을 잘못 봤나>'")
    else:
        # **억지로 참·거짓을 내지 않는다.** 우기면 그 우김 위에서 취약점이 돈다
        print(f"[{qid}] **채점을 못 했다.** 글자로 맞춰 볼 수 있는 답이 아니다.")
        print(f"  낸 답: {답}")
        print(f"  정답:  {q.정답}")
        print(f"  네가 정해라: python3 study/run.py --맞음 {qid}   또는   --틀림 {qid}")
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

    n = NT.읽기(자리)
    if a.wrongbook:
        print(PL.오답노트(n, a.tag))
        return 0
    if a.weak:
        print(PL.취약점보고(n))
        return 0
    if a.lesson:
        print(PL.교안(n, a.title))
        return 0

    전, 틀, p0 = WK.전체기저(n)
    print(f"공책: 문제 {len(n.문제)}개 · 시도 {len(n.시도)}개 · "
          f"채점됨 {전}개 · 오답률 {p0:.0%}")
    print("  --넣기 문제.json / --낼것 / --답 <id> '<답>' / "
          "--오답노트 / --취약점 / --교안")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
