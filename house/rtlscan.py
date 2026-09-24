# -*- coding: utf-8 -*-
"""house/rtlscan -- **어느 SystemVerilog 에서나 같은 것을 읽어 낸다.**

## 왜 있나

사용자(2026-09-22): **"fir 만든걸 mera에 못쓰는건 제대로된 에이전트가 아니야."**

맞는 말이다. 앞서 다섯 에이전트에 `회로=` 를 뚫었지만, 그것은 **배관**이었다.
안에 든 분석은 여전히 `nsw_fir` 을 손으로 적어 둔 것이었다.

    식 = "(a0*x0 + a1*x1) + (a2*x2 + a3*x3)"      # FIR 의 식
    조합 = [{"TAPS": 4}, {"TAPS": 8}, {"TAPS": 16}]  # FIR 의 파라미터
    건넘 = [{"신호": "cfg_coef[15:0] + cfg_we", ...}]  # FIR 의 CDC

MERA 를 넘겨도 이 글자들은 그대로다. **회로 이름만 바뀐 FIR 보고서**가 된다.

## 무엇이 범용일 수 있나

회로를 안 가리고 읽을 수 있는 것은 **RTL 글 자체에 적혀 있는 것**뿐이다.

    포트          module 머리에서
    파라미터       `#(parameter ...)` 에서
    클럭 도메인     `posedge <신호>` 를 전부 모아서
    리셋          이름 꼴(`*rst*`/`*reset*`)과 민감도 목록에 있나(비동기)로
    순차/조합 블록  `always_ff`/`always @(posedge` 대 `always_comb`/`always @(*`
    FSM 후보      `case (<신호>)` + 그 신호에 쓰이는 상태 상수
    CDC 건넘       **어느 클럭 아래에서 쓰이고 어느 클럭 아래에서 읽히나**
    산술          `*` · `+` · `-` 를 세어 데이터패스의 크기를 가늠
    래치 위험      `always @(*)` 안에서 모든 갈래에 대입이 없나

## 무엇이 범용일 수 없나 -- 그대로 적는다

**골든 모델은 범용일 수 없다.** 무엇이 옳은 값인지는 회로마다 다르고, 그것은
스펙에서 나온다(그래서 `gen.py` 가 테스트벤치를 회로마다 짓는다).

여기서 하는 일은 **글을 읽는 것**이지 뜻을 아는 것이 아니다. 정규식으로 읽으므로
`generate` 안의 조건이나 매크로로 감싼 코드는 놓친다. **놓칠 수 있다는 것을
결과에 적는다** -- 다 읽은 척하면 그 표를 믿고 판단하게 된다.

실행: python3 house/rtlscan.py [회로키]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent
저장소 = 뿌리.parent
if str(저장소) not in sys.path:
    sys.path.insert(0, str(저장소))


def 군더더기빼기(sv: str) -> str:
    """주석과 문자열을 공백으로 바꾼다. **길이는 그대로 둔다**(자리를 보존한다)."""
    out = list(sv)
    i, n = 0, len(sv)
    while i < n:
        c = sv[i]
        if c == "/" and i + 1 < n and sv[i + 1] == "/":
            j = sv.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif c == "/" and i + 1 < n and sv[i + 1] == "*":
            j = sv.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if sv[k] != "\n":
                    out[k] = " "
            i = j
        elif c == '"':
            j = i + 1
            while j < n and sv[j] != '"':
                j += 2 if sv[j] == "\\" else 1
            j = min(j + 1, n)
            for k in range(i, j):
                out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


_모듈 = re.compile(r"\bmodule\s+(\w+)")
_에지 = re.compile(r"\b(pos|neg)edge\s+(\w+)")
_파라 = re.compile(r"\bparameter\s+(?:\w+\s+)?(?:signed\s+)?(?:\[[^\]]*\]\s*)?(\w+)\s*=\s*([^,)\n;]+)")
_로컬 = re.compile(r"\blocalparam\s+(?:\w+\s+)?(?:\[[^\]]*\]\s*)?(\w+)\s*=\s*([^,;\n]+)")
_케이스 = re.compile(r"\bcase[xz]?\s*\(\s*([\w\[\]:$\s]+?)\s*\)")
_인스턴스 = re.compile(r"^\s*(\w+)\s*(?:#\s*\([^;]*?\))?\s*(\w+)\s*\(", re.M)
_예약어 = {"module", "endmodule", "if", "else", "case", "casex", "casez", "endcase",
        "begin", "end", "always", "always_ff", "always_comb", "always_latch",
        "assign", "initial", "generate", "endgenerate", "function", "task",
        "for", "while", "wire", "reg", "logic", "input", "output", "inout",
        "parameter", "localparam", "typedef", "enum", "struct", "return", "posedge",
        "negedge", "or", "and", "not", "xor", "default", "unique", "priority"}


def _문장끝(sv: str, i: int) -> int:
    """`i` 에서 시작하는 **한 문장**의 끝. `begin..end` 와 `if/else` 사슬을 따라간다.

    **실측 2026-09-22.** 첫 판은 `begin` 이 없으면 **첫 `;` 에서 끊었다.**
    그런데 이 저장소의 RTL 은 이렇게 쓴다:

        always @(posedge wclk or negedge wrst_n)
          if (!wrst_n) {wbin, wgray} <= 0;
          else if (wen) {wbin, wgray} <= {wbin_nxt, wgray_nxt};

    첫 `;` 에서 끊으면 **`else` 가지가 통째로 안 보인다.** 그 가지에 든 CDC 신호가
    사라지고, 그래서 nsw_fir 의 CDC 건넘이 **0개**로 나왔다 -- 비동기 FIFO 가
    빤히 있는 회로에서.
    """
    n = len(sv)
    while i < n and sv[i].isspace():
        i += 1
    if sv.startswith("begin", i):
        깊이 = 0
        for t in re.finditer(r"\b(begin|end)\b", sv[i:]):
            깊이 += 1 if t.group(1) == "begin" else -1
            if 깊이 == 0:
                i = i + t.end()
                break
        else:
            return n
    elif sv.startswith("case", i) or sv.startswith("casex", i) or sv.startswith("casez", i):
        m = re.search(r"\bendcase\b", sv[i:])
        i = i + m.end() if m else n
    elif sv.startswith("if", i):
        골 = sv.find("(", i)
        if 골 < 0:
            return n
        깊이, k = 0, 골
        while k < n:
            if sv[k] == "(":
                깊이 += 1
            elif sv[k] == ")":
                깊이 -= 1
                if 깊이 == 0:
                    break
            k += 1
        i = _문장끝(sv, k + 1)
    else:
        세미 = sv.find(";", i)
        i = 세미 + 1 if 세미 >= 0 else n
    # `else` 가 이어지면 그것도 이 문장이다
    j = i
    while j < n and sv[j].isspace():
        j += 1
    if sv.startswith("else", j) and not (sv[j + 4:j + 5].isalnum() or sv[j + 4:j + 5] == "_"):
        return _문장끝(sv, j + 4)
    return i


def _블록들(sv: str) -> list:
    """always 블록들. [{"갈래","클럭","에지","리셋","비동기리셋","시작","끝","글"}].

    `begin`/`end` 를 세어 블록 끝을 찾는다. `begin` 이 없는 한 줄짜리도 받는다.
    """
    난것 = []
    for m in re.finditer(r"\balways(_ff|_comb|_latch)?\b", sv):
        머리끝 = m.end()
        민감도 = ""
        if sv[머리끝:머리끝 + 40].lstrip().startswith("@"):
            골 = sv.find("@", 머리끝)
            깊이, j = 0, sv.find("(", 골)
            if j < 0:
                continue
            k = j
            while k < len(sv):
                if sv[k] == "(":
                    깊이 += 1
                elif sv[k] == ")":
                    깊이 -= 1
                    if 깊이 == 0:
                        break
                k += 1
            민감도 = sv[j:k + 1]
            몸시작 = k + 1
        else:
            몸시작 = 머리끝
        끝 = _문장끝(sv, 몸시작)
        글 = sv[m.start():끝]
        에지들 = _에지.findall(민감도)
        갈래 = ("순차" if 에지들 else
              ("조합" if (m.group(1) in (None, "_comb") or "*" in 민감도) else "래치"))
        클럭 = 에지들[0][1] if 에지들 else ""
        리셋 = [s for e, s in 에지들[1:]]
        난것.append({"갈래": 갈래, "클럭": 클럭, "에지": 에지들,
                   "비동기리셋": 리셋, "민감도": 민감도.strip(),
                   "시작": m.start(), "끝": 끝, "글": 글})
    return 난것


# 몸 맨 앞의 `if (!rst_n)` 꼴 -- **동기 리셋은 민감도 목록에 안 나온다**
_동기리셋가지 = re.compile(r"if\s*\(\s*(!|~)?\s*(\w+)\s*\)")


def _리셋이름(묶: frozenset) -> str:
    """리셋 묶음을 사람이 읽을 이름으로.  **빈 묶음은 '(리셋없음)' 이다** --
    이름 없는 도메인을 빈 칸으로 두면 표에서 사라진다."""
    return " + ".join(sorted(묶)) if 묶 else "(리셋없음)"


_리셋꼴 = re.compile(r"(^|_)(a?rst|a?reset)(_?n)?$|(^|_)(rst|reset)_?n?$", re.I)


def 리셋같나(이름: str) -> bool:
    n = (이름 or "").lower()
    return bool(re.search(r"(rst|reset)", n))


def 훑기(RTL, top: str = "") -> dict:
    """RTL 파일들을 읽어 회로를 안 가리는 표를 낸다."""
    글들, 파일들 = [], []
    for p in (RTL or []):
        q = Path(p)
        if not q.exists():
            continue
        파일들.append(str(q))
        글들.append(군더더기빼기(q.read_text(encoding="utf-8", errors="replace")))
    if not 글들:
        return {"됐나": False, "까닭": "읽을 RTL 이 없다"}
    sv = "\n".join(글들)

    모듈 = _모듈.findall(sv)
    블록 = _블록들(sv)
    클럭수 = {}
    for b in 블록:
        if b["클럭"]:
            클럭수[b["클럭"]] = 클럭수.get(b["클럭"], 0) + 1
    # 리셋으로 쓰이는 이름은 클럭에서 뺀다 -- `posedge rst` 는 비동기 리셋이다
    클럭들 = sorted((c for c in 클럭수 if not 리셋같나(c)), key=lambda c: -클럭수[c])
    리셋들 = sorted({s for b in 블록 for s in b["비동기리셋"]}
                 | {c for c in 클럭수 if 리셋같나(c)})

    # 동기 리셋: 순차 블록 첫머리의 `if (!rst_n)` 꼴
    동기리셋 = sorted({m.group(1) for b in 블록 if b["갈래"] == "순차"
                   for m in re.finditer(r"if\s*\(\s*!?\s*(\w*(?:rst|reset)\w*)\s*\)",
                                        b["글"], re.I)}
                  - set(리셋들))

    파라 = {k: v.strip() for k, v in _파라.findall(sv)}
    # **한 `localparam` 이 이름을 여럿 선언한다.** 실측 2026-09-22: nsw_fir 의
    # FSM 상태가 이렇게 적혀 있다.
    #
    #     localparam [4:0] S_IDLE = 5'b00001,
    #                      S_LOAD = 5'b00010, ... S_DONE = 5'b10000;
    #
    # 첫 이름만 잡으면 **상태 다섯 중 하나만** 나오고, FSM 커버 빈이 한 개가 된다.
    # 그러면 "모든 상태 방문" 이라고 적고 한 상태만 세는 꼴이 된다.
    로컬 = {}
    for m in re.finditer(r"\blocalparam\b([^;]*);", sv):
        몸 = m.group(1)
        몸 = re.sub(r"^\s*(?:integer|signed|unsigned|logic|bit|int)\b", " ", 몸)
        몸 = re.sub(r"^\s*\[[^\]]*\]", " ", 몸)
        깊이, 조각, 버퍼 = 0, [], []
        for ch in 몸:                       # 중괄호 안의 쉼표는 구분자가 아니다
            if ch in "{([":
                깊이 += 1
            elif ch in "})]":
                깊이 -= 1
            if ch == "," and 깊이 == 0:
                조각.append("".join(버퍼)); 버퍼 = []
            else:
                버퍼.append(ch)
        조각.append("".join(버퍼))
        for 한 in 조각:
            mm = re.match(r"\s*(?:\[[^\]]*\]\s*)?(\w+)\s*=\s*(.+)", 한, re.S)
            if mm and not mm.group(1).isdigit():
                로컬[mm.group(1)] = mm.group(2).strip()

    # **톱 모듈의 파라미터만 따로 센다.** 실측 2026-09-22: 스윕이 저장소 전체에서
    # 파라미터를 긁어 `-GADDRW=...` 를 넘겼는데, `ADDRW` 는 하위 모듈(`nsw_afifo`)의
    # 것이라 verilator 가 이렇게 죽었다:
    #
    #     %Error: Parameters from the command line were not found in the design: ADDRW
    #
    # `-G` 는 **톱 모듈의 파라미터만** 받는다. 하위 모듈 것을 섞으면 빌드가 깨진다.
    톱파라 = {}
    if top:
        mt = re.search(rf"\bmodule\s+{re.escape(top)}\b(.*?);", sv, re.S)
        if mt:
            머리 = mt.group(1)
            짝 = re.search(r"#\s*\((.*?)\)\s*\(", 머리, re.S) or \
                re.search(r"#\s*\((.*)\)", 머리, re.S)
            if 짝:
                톱파라 = {k: v.strip() for k, v in _파라.findall(짝.group(1))}

    # CDC: 어느 클럭 아래에서 쓰이고 어느 클럭 아래에서 읽히나
    쓰인곳, 읽힌곳 = {}, {}
    for b in 블록:
        if b["갈래"] != "순차" or not b["클럭"]:
            continue
        몸 = b["글"]
        for m in re.finditer(r"(\w+)\s*(?:\[[^\]]*\])?\s*<=", 몸):
            쓰인곳.setdefault(m.group(1), set()).add(b["클럭"])
        for w in set(re.findall(r"\b([a-zA-Z_]\w*)\b", 몸)):
            if w not in _예약어:
                읽힌곳.setdefault(w, set()).add(b["클럭"])
    건넘 = []
    for 신호, 쓴 in sorted(쓰인곳.items()):
        읽 = 읽힌곳.get(신호, set()) - 쓴
        if 읽:
            건넘.append({"신호": 신호, "보내는곳": sorted(쓴), "받는곳": sorted(읽)})

    # RDC: **어느 리셋 아래에서 쓰이고 어느 리셋 아래에서 읽히나.**
    #
    # CDC 와 같은 꼴이되 도메인을 **클럭이 아니라 리셋**으로 가른다. 리셋 묶음은
    # 두 곳에서 온다 -- 민감도 목록의 비동기 리셋과, 몸 맨 앞의 `if (!rst_n)`
    # 꼴로 걸린 동기 리셋.
    #
    # **리셋이 아예 없는 블록도 한 도메인으로 센다.** 실측 2026-09-23 (nsw_fir):
    # 순차 블록 10개 중 둘이 리셋이 없었고, 거기로 건너는 것이 넷 중 둘이었다.
    # `rst_n` 이 걸린 플롭이 리셋 없는 플롭을 먹이면, 리셋이 서는 순간 소스만
    # 바뀌어 목적지가 그 변화를 잡는다 -- 고전적인 RDC 자리다. 그것을 '리셋이
    # 없으니 도메인이 아니다' 로 빼면 **가장 위험한 것을 빼는 것**이 된다.
    쓴리셋, 읽힌리셋 = {}, {}
    for b in 블록:
        if b["갈래"] != "순차":
            continue
        묶 = set(b["비동기리셋"])
        mm = _동기리셋가지.search(b["글"], b["글"].find(")"))
        if mm and 리셋같나(mm.group(2)):
            묶.add(mm.group(2))
        R = frozenset(묶)
        몸 = b["글"]
        for m in re.finditer(r"(\w+)\s*(?:\[[^\]]*\])?\s*<=", 몸):
            쓴리셋.setdefault(m.group(1), set()).add(R)
        for w in set(re.findall(r"\b([a-zA-Z_]\w*)\b", 몸)):
            if w not in _예약어:
                읽힌리셋.setdefault(w, set()).add(R)
    # **짝마다 한 줄로 낸다 -- 신호마다 한 줄이 아니다.**
    #
    # 실측 2026-09-23. 첫 판은 신호마다 한 줄이었고 `받는곳` 이 목록이었다.
    # 그러면 이미 선언된 목적지가 **새 목적지를 가린다** -- `cnt` 가
    # `rst_n -> (리셋없음)` 로 선언돼 있는데 RTL 에 `aux_rst_n` 도메인을 더해도
    # 같은 한 줄에 목적지만 붙어서 관문이 안 물었다(검사가 잡았다).
    #
    # 짝(보내는 리셋, 받는 리셋)마다 한 줄이면 세는 수도 정직해지고
    # 선언 파일의 한 줄과 **하나씩** 맞는다.
    RDC건넘 = []
    for 신호, 쓴 in sorted(쓴리셋.items()):
        읽 = 읽힌리셋.get(신호, set()) - 쓴
        for A in sorted(쓴, key=_리셋이름):
            for B in sorted(읽, key=_리셋이름):
                RDC건넘.append({"신호": 신호, "보내는곳": _리셋이름(A),
                              "받는곳": _리셋이름(B)})

    # FSM 후보
    # **`NAME:` 을 저장소 전체에서 찾으면 안 된다.** 실측 2026-09-22: 포화 상수
    # `SAT_LO` 가 삼항연산자 `? SAT_LO : SAT_HI` 의 콜론에 걸려 **FSM 상태**로
    # 잡혔다. 그럴듯하지만 틀린 줄이고, 그 줄로 커버 빈까지 만들어진다.
    # **그 case 문 안에서만** 찾는다.
    fsm = []
    for m in _케이스.finditer(sv):
        신호 = m.group(1).strip()
        끝 = re.search(r"\bendcase\b", sv[m.end():])
        몸 = sv[m.end(): m.end() + 끝.start()] if 끝 else ""
        상태 = [k for k in 로컬 if re.search(rf"\b{re.escape(k)}\b\s*:", 몸)]
        # **천이도 RTL 에서 읽는다.** 손으로 그린 상태도는 회로가 바뀌어도 안 바뀐다
        # -- 그러면 그림이 코드와 달라지고, 사람은 그림을 믿는다.
        #
        # `S_X: ... st_n = S_Y;` 꼴에서 (X -> Y, 조건) 을 뽑는다. 조건은 그 대입을
        # 감싼 `if (...)` 에서 가져온다. 없으면 빈 글 -- **지어내지 않는다.**
        # **라벨 뒤의 공백을 잊으면 가지가 안 끊긴다.** 실측 2026-09-22: 이 저장소의
        # RTL 은 `S_IDLE : if (start) ...` 처럼 **콜론 앞에 공백**을 둔다.
        # `뒤.find(st + ":")` 로 경계를 찾았더니 한 번도 안 맞았고, 그래서 각 가지가
        # **case 문 끝까지 흘러** 뒤에 나오는 대입을 전부 제 것으로 삼켰다. 결과가
        # 이랬다: `S_IDLE -> S_FLUSH` · `S_LOAD -> S_FLUSH` -- **없는 천이**다.
        #
        # 없는 천이가 그려진 상태도는 없느니보다 나쁘다. 사람은 그림을 믿는다.
        라벨 = []
        for st in 상태 + ["default"]:
            for m2 in re.finditer(rf"(?<![\w.]){re.escape(st)}\s*:(?!:)", 몸):
                라벨.append((m2.start(), m2.end(), st))
        라벨.sort()
        전이 = []
        for 자리, (시작, 끝, st) in enumerate(라벨):
            if st == "default":
                continue
            다음시작 = 라벨[자리 + 1][0] if 자리 + 1 < len(라벨) else len(몸)
            가지 = 몸[끝:다음시작]
            for m3 in re.finditer(r"(\w+)\s*<?=\s*(\w+)\s*;", 가지):
                목적 = m3.group(2)
                if 목적 not in 상태:
                    continue
                앞글 = 가지[:m3.start()]
                조건 = ""
                m4 = None
                for m4 in re.finditer(r"\bif\s*\(([^;{]*?)\)", 앞글):
                    pass
                if m4:
                    조건 = " ".join(m4.group(1).split())[:40]
                전이.append((st, 목적, 조건))
        # 겹치는 것은 뺀다
        본것, 깔끔 = set(), []
        for a, b, c in 전이:
            if (a, b) not in 본것:
                본것.add((a, b))
                깔끔.append((a, b, c))
        fsm.append({"신호": 신호, "상태후보": 상태[:16], "상태수": len(상태),
                   "전이": 깔끔[:24]})

    # 산술: 데이터패스의 크기를 가늠한다
    산술 = {"곱셈": len(re.findall(r"(?<![*/(@\s])\s*\*(?![*/)])", sv)),
          "덧셈": len(re.findall(r"(?<![-+=<>!])\+(?![-+=])", sv)),
          # **`[W-1:0]` 의 빼기를 데이터패스 뺄셈으로 세면 안 된다.** 첫 판이
          # nsw_fir 에서 뺄셈 **51개**를 냈다 -- 거의 다 비트폭 계산이었다.
          # 양쪽에 공백이 있는 것만 센다(이 저장소의 RTL 은 그렇게 쓴다).
          "뺄셈": len(re.findall(r"(?<=[\w\)\]])\s-\s(?=[\w\($])", sv)),
          "시프트": len(re.findall(r"<<|>>", sv))}

    # 래치 위험: 조합 블록에 `if` 가 있는데 `else` 가 없다
    래치위험 = [b["민감도"] for b in 블록 if b["갈래"] == "조합"
             and re.search(r"\bif\s*\(", b["글"]) and "else" not in b["글"]]

    인스턴스 = [(t, n) for t, n in _인스턴스.findall(sv)
             if t not in _예약어 and n not in _예약어 and t in 모듈]

    포트 = []
    if top:
        from house import gen as G
        원본 = "\n".join(Path(p).read_text(encoding="utf-8", errors="replace")
                       for p in 파일들)
        포트 = G.포트뽑기(원본, top)

    return {
        "됐나": True, "파일": 파일들, "모듈": 모듈, "top": top,
        "포트": 포트, "파라미터": 파라, "톱파라미터": 톱파라, "로컬파라": 로컬,
        "클럭": 클럭들, "클럭블록수": 클럭수,
        "비동기리셋": 리셋들, "동기리셋": 동기리셋,
        "순차블록": sum(1 for b in 블록 if b["갈래"] == "순차"),
        "조합블록": sum(1 for b in 블록 if b["갈래"] == "조합"),
        "래치블록": sum(1 for b in 블록 if b["갈래"] == "래치"),
        "래치위험": 래치위험,
        "CDC건넘": 건넘, "RDC건넘": RDC건넘, "FSM": fsm, "산술": 산술,
        "인스턴스": 인스턴스, "줄수": sv.count("\n") + 1,
        # **다 읽은 척하지 않는다.** 정규식으로 읽으므로 놓치는 자리가 있다.
        "못보는것": ["`generate` 안의 조건부 코드", "매크로(`define)로 감싼 코드",
                 "인터페이스·모듈포트(modport)", "계층 참조(`a.b.c`)",
                 "함수/태스크 안의 대입"],
    }


def 요약글(r: dict) -> str:
    if not r.get("됐나"):
        return f"RTL 을 못 읽었다 -- {r.get('까닭')}"
    클 = " · ".join(f"{c}({r['클럭블록수'][c]})" for c in r["클럭"]) or "(없음)"
    return "\n".join([
        f"모듈 {len(r['모듈'])}개 · 줄 {r['줄수']} · 포트 {len(r['포트'])}개",
        f"클럭 {클}   비동기리셋 {r['비동기리셋'] or '(없음)'}   "
        f"동기리셋 {r['동기리셋'] or '(없음)'}",
        f"순차 {r['순차블록']} · 조합 {r['조합블록']} · 래치 {r['래치블록']}"
        + (f"  ⚠ 래치 위험 {len(r['래치위험'])}" if r["래치위험"] else ""),
        f"CDC 건넘 {len(r['CDC건넘'])}개   FSM 후보 {len(r['FSM'])}개   "
        f"파라미터 {len(r['파라미터'])}개",
        f"산술 곱{r['산술']['곱셈']} 덧{r['산술']['덧셈']} "
        f"뺄{r['산술']['뺄셈']} 시프트{r['산술']['시프트']}",
    ])


def 데이터패스식(r: dict, 최대곱=4) -> str:
    """HLS 설계공간 탐색에 넣을 **이 회로 크기의** 식.

    **이것은 회로의 식이 아니다.** RTL 의 곱셈·덧셈 개수로 *같은 크기의* 식을
    지어낸 것이고, 스케줄러가 그 크기에서 무엇을 하는지 보이는 데 쓴다.
    보고서에 그렇게 적어야 한다 -- 이 회로의 데이터패스라고 하면 거짓말이 된다.
    """
    # **한 항짜리 식은 설계공간이 없다.** 곱셈기 4개든 1개든 스케줄이 같아서
    # 표 세 줄이 글자까지 똑같아진다 -- 아무 말도 안 하는 표다(실측: nsw_fir 의
    # 소스에는 곱셈 인스턴스가 하나뿐이라 `a0*x0` 이 나왔다). 최소 둘로 둔다.
    곱 = max(2, min(int(r.get("산술", {}).get("곱셈", 1) or 1), 최대곱))
    항 = [f"a{i}*x{i}" for i in range(곱)]
    if len(항) == 1:
        return 항[0]
    반 = len(항) // 2
    왼 = " + ".join(항[:반]) if 반 else 항[0]
    오 = " + ".join(항[반:])
    return f"({왼}) + ({오})"


if __name__ == "__main__":
    from house import designs as DES
    키 = next((a for a in sys.argv[1:] if not a.startswith("-")), None)
    d = DES.찾기(키)
    r = 훑기(d.RTL, d.top)
    print(f"[rtlscan] {d.키} ({d.이름})")
    print(요약글(r))
    if r.get("됐나"):
        print("\nCDC 건넘:")
        for x in r["CDC건넘"][:10]:
            print(f"  {x['신호']:24} {x['보내는곳']} -> {x['받는곳']}")
        print(f"\n데이터패스 식(크기만 흉내): {데이터패스식(r)}")
        print("\n못 보는 것: " + " · ".join(r["못보는것"]))
