# -*- coding: utf-8 -*-
"""교재를 **질문에 답할 수 있는 형태**로 꺼내 둔다 -- 디스코드 답변의 근거.

## 이것이 있는 이유

사용자 지시: *"너가 영어로 작성해서 VM에 넣으면 그걸 질문하면 디스코드가
대답할 수 있게. 대신 아주 자세하고 논리적이고 체계적으로. 진짜 교수처럼."*

교재는 `edu/*.py` 의 장 함수들이 **그릴 때마다 만들어 내는** HTML 이다.
그런데 그 렌더는 이 저장소 밖의 자료(`/home/user/edu/zoo.json`,
`/home/user/ipzoo/...`)를 읽고 **2분 30초** 걸린다.  VM 에는 그 자료가
아예 없다 -- 그래서 **VM 에서는 교재를 못 짓는다.**

그러니 여기서 한 번 꺼내 **텍스트로 커밋해 둔다.**  VM 의 봇은 그 파일만
읽는다.  이 저장소의 규율대로, 봇이 답할 때 쓰는 것은 *기억*이 아니라
*파일*이다.

## 무엇을 꺼내나

장 하나를 통째로 주면 답이 흐려진다.  그래서 **절(h2) 단위**로 자른다.
절 하나가 답 하나의 근거가 된다.

    edu/kb/kb.jsonl     절마다 한 줄. 제목·경로·본문·코드
    edu/kb/meta.json    몇 장 몇 절, 언제 지었나, 어느 모듈에서 왔나

## 찾기는 왜 BM25 인가 (그리고 왜 색인 파일이 없나)

전체가 1.2 MB 남짓이다.  질문 하나에 **한 번 훑으면** 된다 -- 0.5초 안쪽.
역색인 파일을 따로 커밋하면 본문과 **어긋날 수 있는 두 번째 진실**이
생긴다.  어긋난 색인은 조용히 엉뚱한 절을 준다.  파일 하나만 둔다.

## 한국어로 묻고 영어로 찾는다

본문은 영어다.  사용자는 한국어로 묻는다.  그대로 훑으면 **한 글자도
안 맞는다.**  그래서 `용어.py` 가 한국어 말을 영어 말로 바꿔 준다.
못 바꾼 한국어 말은 그대로 두되(고유명사·코드 이름이 섞이므로),
**바꾼 것과 못 바꾼 것을 답에 같이 적는다** -- 못 찾았을 때 왜 못 찾았는지
사용자가 알 수 있어야 한다.
"""
import html as _html
import json
import math
import os
import re
import sys
import time

여기 = os.path.dirname(os.path.abspath(__file__))
창고 = os.path.join(여기, "kb")
원장 = os.path.join(창고, "kb.jsonl")
메타 = os.path.join(창고, "meta.json")

# 장 함수를 안 가진 것들 -- 틀·도구 모듈이다.
틀 = {"buildE", "buildT", "buildK", "bookE", "bookK", "sch", "wex",
      "srcsel", "srcdocE", "apidoc", "kb", "용어"}


# ---------------------------------------------------------------------------
# HTML -> 사람이 읽는 글
# ---------------------------------------------------------------------------
def _표풀기(m):
    """표를 파이프 줄로.  표의 수가 답의 근거가 되는 일이 많다."""
    속 = m.group(0)
    설명 = re.search(r"<caption>(.*?)</caption>", 속, re.S)
    줄들 = []
    if 설명:
        줄들.append("[" + _태그빼기(설명.group(1)) + "]")
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", 속, re.S):
        칸 = [_태그빼기(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S)]
        if 칸:
            줄들.append(" | ".join(칸))
    return "\n" + "\n".join(줄들) + "\n"


def _태그빼기(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = _html.unescape(s)
    return re.sub(r"[ \t]+", " ", s).strip()


def 글로(h):
    """장 HTML 을 글로.  그림(SVG)은 버리고 그림설명은 남긴다."""
    h = re.sub(r"<svg.*?</svg>", " ", h, flags=re.S)
    h = re.sub(r"<script.*?</script>", " ", h, flags=re.S)
    h = re.sub(r"<figcaption[^>]*>(.*?)</figcaption>",
               lambda m: "\n[그림] " + _태그빼기(m.group(1)) + "\n", h, flags=re.S)
    h = re.sub(r"<table.*?</table>", _표풀기, h, flags=re.S)
    h = re.sub(r"<pre[^>]*>(.*?)</pre>",
               lambda m: "\n```\n" + _html.unescape(
                   re.sub(r"<[^>]+>", "", m.group(1))).strip() + "\n```\n",
               h, flags=re.S)
    h = re.sub(r"<(li|tr|p|div|br|h[1-6])[^>]*>", "\n", h)
    h = re.sub(r"</(li|tr|p|div|h[1-6])>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = _html.unescape(h)
    h = re.sub(r"[ \t]+", " ", h)
    h = re.sub(r"\n\s*\n\s*\n+", "\n\n", h)
    return h.strip()


# ---------------------------------------------------------------------------
# 자르기 -- 절(h2) 하나가 근거 하나
# ---------------------------------------------------------------------------
칸상한 = 7000          # 이보다 긴 절은 h3 에서 더 자른다


def 절나누기(장h):
    """(장제목, [(절제목, 절HTML), ...])"""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", 장h, re.S)
    장제목 = _태그빼기(m.group(1)) if m else "(제목 없음)"
    토막 = re.split(r"(<h2[^>]*>.*?</h2>)", 장h, flags=re.S)
    머리 = 토막[0]
    절들 = []
    if len(글로(머리)) > 200:
        절들.append((장제목 + " — 들어가며", 머리))
    for i in range(1, len(토막) - 1, 2):
        제목 = _태그빼기(토막[i])
        속 = 토막[i] + 토막[i + 1]
        if len(속) <= 칸상한:
            절들.append((제목, 속))
            continue
        # 너무 길면 h3 에서 한 번 더
        작은 = re.split(r"(<h3[^>]*>.*?</h3>)", 속, flags=re.S)
        절들.append((제목, 작은[0]))
        for j in range(1, len(작은) - 1, 2):
            절들.append((제목 + " / " + _태그빼기(작은[j]), 작은[j] + 작은[j + 1]))
    return 장제목, 절들


# ---------------------------------------------------------------------------
# 짓기
# ---------------------------------------------------------------------------
def 장함수들():
    """`edu/*.py` 에서 `ch_*` 를 전부 찾는다.

    빌드 목록(`buildE.py`)을 베끼지 않는다 -- 베끼면 **새 장을 더했을 때
    여기에 안 실려도 아무도 모른다.**  파일에서 직접 찾으면 빠질 수 없다.
    """
    import importlib
    if 여기 not in sys.path:
        sys.path.insert(0, 여기)
    난것 = []
    for p in sorted(os.listdir(여기)):
        if not p.endswith(".py"):
            continue
        이름 = p[:-3]
        if 이름 in 틀 or 이름.startswith("_"):
            continue
        try:
            mod = importlib.import_module(이름)
        except Exception as e:          # 장이 아닌 모듈일 수 있다
            난것.append((이름, None, repr(e)[:120]))
            continue
        for fn in sorted(dir(mod)):
            if fn.startswith("ch_") and callable(getattr(mod, fn)):
                난것.append((이름, fn, None))
    return 난것


def 짓기(보고=print):
    t0 = time.time()
    os.makedirs(창고, exist_ok=True)
    줄들, 못한것, 장수 = [], [], 0
    for 모듈, fn, 오류 in 장함수들():
        if fn is None:
            못한것.append(f"{모듈}: {오류}")
            continue
        try:
            h = getattr(sys.modules[모듈], fn)()
        except Exception as e:
            못한것.append(f"{모듈}.{fn}: {repr(e)[:120]}")
            continue
        장제목, 절들 = 절나누기(h)
        장수 += 1
        for k, (제목, 속) in enumerate(절들):
            글 = 글로(속)
            if len(글) < 120:
                continue
            줄들.append({
                "id": f"{모듈}.{fn}#{k}",
                "모듈": 모듈, "함수": fn,
                "장": 장제목, "절": 제목,
                "글": 글,
            })
        보고(f"  {모듈}.{fn}: {len(절들)}절")
    with open(원장, "w", encoding="utf-8") as f:
        for r in 줄들:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    m = {"장": 장수, "절": len(줄들),
         "글자": sum(len(r["글"]) for r in 줄들),
         "지은때": time.strftime("%Y-%m-%d %H:%M:%S"),
         "못한것": 못한것,
         "걸린초": round(time.time() - t0, 1)}
    json.dump(m, open(메타, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # 장 함수 중에는 **부르는 것만으로 파일을 남기는** 것이 있다(실측 2026-09-20:
    # 색인을 짓고 나니 `edu/모델링팀_실무교안.pdf` 가 바뀌어 있었다).  그대로
    # `git add -A` 하면 산출물이 커밋에 끌려 들어간다 -- 이 저장소가 원장으로
    # 한 번 겪은 그 병이다.  그러니 **짓고 나서 무엇이 늘었는지 말해 준다.**
    import subprocess
    흔적 = subprocess.run(["git", "status", "--porcelain", "-uno"],
                         cwd=os.path.dirname(여기), capture_output=True,
                         text=True).stdout.strip().splitlines()
    흔적 = [l for l in 흔적 if "edu/kb/" not in l]
    if 흔적:
        m["흔적"] = 흔적
        보고("!! 짓는 동안 바뀐 파일(색인 밖) -- 커밋에 끌고 들어가지 마라:")
        for l in 흔적:
            보고("   " + l)
    보고(f"장 {장수} · 절 {len(줄들)} · {m['글자']:,}자 · {m['걸린초']}초"
         + (f" · 못한 것 {len(못한것)}" if 못한것 else ""))
    return m


# ---------------------------------------------------------------------------
# 찾기 -- BM25
# ---------------------------------------------------------------------------
_실림 = None


def 싣기():
    global _실림
    if _실림 is None:
        if not os.path.exists(원장):
            raise FileNotFoundError(
                f"{원장} 이 없다. `python3 edu/kb.py --짓기` 로 먼저 짓는다 "
                "(이 저장소 밖 자료가 필요하므로 VM 이 아니라 개발 자리에서 짓는다)")
        _실림 = [json.loads(l) for l in open(원장, encoding="utf-8") if l.strip()]
    return _실림


_토큰 = re.compile(r"[a-z0-9]+|[가-힣]+")
_영국 = [(re.compile(r"isation$"), "ization"), (re.compile(r"isations$"), "izations"),
        (re.compile(r"ising$"), "izing"), (re.compile(r"ised$"), "ized"),
        (re.compile(r"isers$"), "izers"), (re.compile(r"iser$"), "izer"),
        (re.compile(r"ises$"), "izes"), (re.compile(r"ise$"), "ize")]


def 고르기(w):
    """철자와 복수형을 **한 꼴로** 모은다.

    실측 2026-09-20: "고정소수점 비트폭" 이 전용 장(X1)을 상위 14 안에도 못
    올렸다.  까 보니 교재는 영국 철자(`quantisation` · `equalisation` ·
    `synchroniser`)로 쓰여 있는데 말표는 미국 철자(`quantization`)였다 --
    **한 글자 차이로 영영 안 맞는다.**  여기서 하는 변환은 사전에 있는 낱말을
    만드는 것이 아니다(`exercise` 는 `exercize` 가 된다).  **질문과 본문에 똑같이**
    걸므로 맞추는 데는 아무 문제가 없고, 철자 차이만 사라진다.
    """
    if len(w) > 5:
        for r, t in _영국:
            w2 = r.sub(t, w)
            if w2 != w:
                w = w2
                break
    if len(w) >= 5 and w.endswith("ies"):
        return w[:-3] + "y"
    if (len(w) >= 4 and w.endswith("s")
            and not w.endswith(("ss", "us", "is", "as"))):
        return w[:-1]
    return w


def 토막(s):
    """영어는 낱말(철자·복수형을 고르고), 한국어는 두 글자 창으로."""
    out = []
    for w in _토큰.findall(s.lower()):
        if "가" <= w[0] <= "힣":
            if len(w) <= 2:
                out.append(w)
            else:
                out += [w[i:i + 2] for i in range(len(w) - 1)]
        elif len(w) >= 2:
            out.append(고르기(w))
    return out


def 찾기(질문, 개수=5, 최소점=0.0):
    """질문에 가장 가까운 절들.  돌려주는 것: (절목록, 쓴말)"""
    import 용어
    확장, 바뀐것, 못바꾼것 = 용어.넓히기(질문)
    q = 토막(확장)
    if not q:
        return [], {"영어로": 바뀐것, "못바꾼말": 못바꾼것, "찾은말": []}
    문서 = 싣기()
    N = len(문서)
    df = {}
    tf = []
    길이 = []
    for r in 문서:
        t = 토막(r["장"] + " " + r["절"] + " " + r["절"] + " " + r["글"])
        길이.append(len(t))
        c = {}
        for w in t:
            if w in q:
                c[w] = c.get(w, 0) + 1
        for w in c:
            df[w] = df.get(w, 0) + 1
        tf.append(c)
    평균 = sum(길이) / max(1, N)
    k1, b = 1.5, 0.75
    점수 = []
    for i, c in enumerate(tf):
        s = 0.0
        for w, f in c.items():
            idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
            항 = idf * f * (k1 + 1) / (f + k1 * (1 - b + b * 길이[i] / 평균))
            # 한국어 말 하나가 두 글자 창 여러 개로 쪼개진다(`고정소수점` -> 다섯 개).
            # 그대로 더하면 **한국어 낱말 하나가 영어 낱말 다섯 개 무게**를 갖는다.
            # 실측: 그 때문에 한국어로 쓰인 장이 전용 영어 장을 눌렀다.
            s += 항 * (0.4 if "가" <= w[0] <= "힣" else 1.0)
        if s > 최소점:
            점수.append((s, i))
    점수.sort(reverse=True)
    고른것 = []
    본장 = {}
    본책 = {}
    책상한 = max(2, (개수 * 2 + 2) // 3)     # 한 책이 다 가져가지 않게
    for s, i in 점수:
        r = dict(문서[i])
        # 한 장이 답을 독점하지 않게 -- 장당 둘까지
        본장[r["모듈"]] = 본장.get(r["모듈"], 0) + 1
        if 본장[r["모듈"]] > 2:
            continue
        # 이 저장소의 교재는 두 권이다 -- 영어 본서(대문자 모듈)와 한국어
        # 실무교안(소문자 모듈).  한쪽이 다 채우면 다른 쪽의 더 정확한 절이
        # 밀려난다(실측: 한국어 장 넷이 상위를 채워 전용 영어 장이 안 왔다).
        책 = "한" if r["모듈"][:1].islower() else "영"
        본책[책] = 본책.get(책, 0) + 1
        if 본책[책] > 책상한:
            continue
        r["점수"] = round(s, 2)
        고른것.append(r)
        if len(고른것) >= 개수:
            break
    쓴말 = {"영어로": 바뀐것, "못바꾼말": 못바꾼것,
           "찾은말": sorted(set(w for w in q if df.get(w, 0)))[:30]}
    return 고른것, 쓴말


def 하나(절id):
    for r in 싣기():
        if r["id"] == 절id:
            return r
    return None


def 요약():
    if os.path.exists(메타):
        return json.load(open(메타, encoding="utf-8"))
    return {}


# ---------------------------------------------------------------------------
# 봇이 부르는 자리 -- **도구 껍데기 안에 논리를 두지 않는다**
# ---------------------------------------------------------------------------
# `bot_tools.textbook` 은 langchain 의 `@tool` 로 감싸여 있어서, langchain 이 없는
# 자리(이 개발 컨테이너·CI)에서는 **임포트조차 안 된다.**  그 안에 로직을 두면
# 검사가 건너뛰어지고(실측: `1 skipped`), 건너뛴 자리에서 난 버그는 사용자가
# 디스코드에서 처음 본다.  그래서 로직은 여기 평범한 함수로 두고 도구는 부르기만
# 한다 -- 이 함수는 어디서나 검사된다.
답의꼴 = (
    "Answer at graduate-seminar level, in this order: (1) restate the question and "
    "name the quantity; (2) the governing relation with every symbol and unit defined, "
    "and where it comes from; (3) where it is used in a real flow; (4) the regime where "
    "it binds and where it is negligible; (5) how to apply it, with a worked number; "
    "(6) what the industry code or constraint looks like, quoted from the sections; "
    "(7) the specific way engineers get it wrong; (8) what the book does not establish. "
    "Cite `chapter / section` per claim and never present recall as the book's text.")


def 답근거(question: str, sections: int = 5, section_id: str = "") -> str:
    """질문에 대한 **근거 절들 + 답의 꼴**을 하나의 글로."""
    if (section_id or "").strip():
        r = 하나(section_id.strip())
        if not r:
            return (f"no section with id {section_id!r}. "
                    "Search first with `textbook(question=...)`.")
        return f"### {r['장']} / {r['절']}  ({r['id']})\n{r['글']}"
    try:
        n = max(1, min(int(sections or 5), 8))
    except (TypeError, ValueError):
        n = 5
    try:
        절들, 말 = 찾기(question, 개수=n)
    except FileNotFoundError as e:
        return f"textbook index missing: {e}"
    if not 절들:
        return ("no section matched. Mapped terms: "
                + (", ".join(말["영어로"].values()) or "(none)")
                + ". Unmapped Korean words: "
                + (", ".join(말["못바꾼말"]) or "(none)")
                + "\nSay the book does not cover this and answer from first "
                  "principles, marked as such.")
    m = 요약()
    머리 = [f"Retrieved from the textbook ({m.get('장', '?')} chapters, "
           f"{m.get('절', '?')} sections, built {m.get('지은때', '?')}).",
           "Korean→English terms used: "
           + (", ".join(f"{k}→{v.split()[0]}" for k, v in 말["영어로"].items())
              or "(none)")]
    if 말["못바꾼말"]:
        머리.append("**Not mapped** (may explain a weak hit): "
                   + ", ".join(말["못바꾼말"]))
    빈자리 = os.path.join(창고, "빈자리.md")
    if os.path.exists(빈자리):
        낮 = question.lower()
        걸린것 = [l for l in open(빈자리, encoding="utf-8").read().splitlines()
                if l.startswith("- `") and l.split("`")[1].lower() in 낮]
        if 걸린것:
            머리.append("**The book does not cover this** (measured): "
                       + " ".join(걸린것))
    머리.append("")
    덩이 = []
    for r in 절들:
        글 = r["글"]
        if len(글) > 4500:
            글 = 글[:4500] + ("\n… (truncated — full text: "
                            f"textbook(section_id='{r['id']}'))")
        덩이.append(f"### [{r['점수']}] {r['장']} / {r['절']}  ({r['id']})\n{글}")
    return "\n\n".join(머리 + 덩이) + "\n\n---\n" + 답의꼴


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--짓기":
        짓기()
    elif a and a[0] == "--묻기":
        절들, 말 = 찾기(" ".join(a[1:]), 개수=5)
        print("영어로 바꾼 말:", 말["영어로"])
        for r in 절들:
            print(f"\n=== [{r['점수']}] {r['장']} / {r['절']}  ({r['id']})")
            print(r["글"][:600])
    else:
        print(json.dumps(요약(), ensure_ascii=False, indent=1))
