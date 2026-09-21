# -*- coding: utf-8 -*-
"""W1 -- 회사의 뼈대. 빈 디렉터리에서 다섯 엔지니어까지, 코드로."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "edu"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 정의, 유도, 예제, 짚기, 사고, 수  # noqa: E402
from bookA import 정리, 따름정리, 논문출처, 언어, 직무, 말풀이  # noqa: E402
import dia  # noqa: E402


def 재기(상대경로):
    """이 저장소의 실제 파일을 잰다. **인용이 아니라 측정이다.**"""
    뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = os.path.join(뿌리, 상대경로)
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            글 = f.read()
        return {"줄": 글.count("\n") + 1, "글자": len(글), "있다": True}
    except OSError:
        return {"줄": 0, "글자": 0, "있다": False}


def ch_skeleton():
    잰것 = {p: 재기(p) for p in (
        "house/people.py", "house/report.py", "house/run.py", "house/viz.py",
        "house/designs.py", "house/spec.py", "house/arch.py", "house/gen.py",
        "house/signoff.py", "house/syn/agent.py", "tests/test_house.py")}
    코어 = sum(잰것[p]["줄"] for p in ("house/people.py", "house/report.py",
                                    "house/run.py", "house/designs.py"))
    한명 = 잰것["house/syn/agent.py"]["줄"]

    c = 장(
        "W1", "회사의 뼈대 — 빈 디렉터리에서 다섯 엔지니어까지",
        "이 부는 이론이 아니다. <b>당신이 이것을 혼자 지을 수 있게</b> 하는 것이 "
        "목적이고, 그러려면 &lsquo;무엇을 먼저 만들고 무엇을 나중에 만드는가&rsquo; 가 "
        "글로 적혀 있어야 한다.",
        쓰는것=["에이전트", "런타임", "도구", "제어루프", "종료조건", "원장",
             "출처표시", "멱등성", "능력천장", "도달가능문맥", "판정자",
             "선언형", "세값종료코드", "스트림분리", "점진공개"],
        내놓는것=["보고서객체", "측정원장", "산출물계약", "실패보고", "회로등록부",
              "한명계약", "조립순서"],
        특허="""여기서 발명이 일어나는 자리는 <b>산출물 계약</b>이다 &mdash; &lsquo;무엇을
        내야 보고서로 인정하는가&rsquo; 를 기계가 판정하게 만드는 방법. 그것이 없으면
        에이전트는 글만 쓰고 일했다고 한다.""")

    c.날것(직무(["AIE.코어", "AIE.시제품", "NAV.분해", "NAV.감사"]))

    # ------------------------------------------------------------------
    c.절("W1.1 무엇을 짓는가 — 한 문장으로")

    c.글("""<b>&ldquo;일을 하고 그것을 증명하는 보고서를 내는 프로그램 다섯 개.&rdquo;</b>
    이 한 문장에 설계가 다 들어 있다. &lsquo;일을 한다&rsquo; 는 진짜 도구를 돌린다는
    뜻이고, &lsquo;증명하는&rsquo; 은 보고서의 모든 수가 그 실행에서 나왔다는 뜻이며,
    &lsquo;다섯 개&rsquo; 는 책임이 갈려 있다는 뜻이다.""")

    c.날것(dia.파이프(
        [("요청", "자연어 한 줄", "회색"),
         ("판독", "spec.py — 넘겨짚지 않는다", "파랑"),
         ("제안", "arch.py — 짓기 전에 보인다", "보라"),
         ("생성", "gen.py — 일곱 관문", "노랑"),
         ("다섯 명", "각자 도구를 돌린다", "초록"),
         ("보고", "PDF + 메일 + 첨부", "진파랑")],
        제목="W1.1 — 요청 한 줄이 사인오프 꾸러미가 되기까지",
        아래글="각 상자가 파일 하나다. 순서대로 만들면 된다.",
        폭=660))

    c.날것(정의("한 명 계약 (agent contract)",
              "엔지니어 하나가 지켜야 하는 약속. 이 회사에서는 세 줄이다 &mdash; "
              "<b>(1) 인자 없이 부를 수 있다</b>, <b>(2) 사전 하나를 돌려준다</b>, "
              "<b>(3) 그 사전에 <code>pdf</code> 가 있고 그 파일이 실제로 있다</b>. "
              "이 셋만 지키면 나머지는 자유다."))

    c.날것(표(f"<b>조립 순서.</b> 이 순서대로 만들면 각 단계에서 돌려볼 수 있다. "
            f"(줄 수는 이 저장소의 실제 파일을 지금 잰 것이다)",
            ["순서", "파일", "무엇을 정하나", "줄", "이것 없이 다음을 못 하는 이유"],
            [["1", "<code>people.py</code>", "누가 있나 · 무엇을 책임지나",
              f"{수(잰것['house/people.py']['줄'])}",
              "보고서에 서명할 주체가 없으면 보고서가 아니다"],
             ["2", "<code>report.py</code>", "<b>보고서 객체</b> · 산출물 계약",
              f"{수(잰것['house/report.py']['줄'])}",
              "이게 없으면 각자 제멋대로 출력한다"],
             ["3", "<code>viz.py</code>", "그림 &mdash; 표·막대·선·히트맵",
              f"{수(잰것['house/viz.py']['줄'])}",
              "그림 0장을 거절하려면 그림을 만들 수 있어야 한다(W2)"],
             ["4", "<code>designs.py</code>", "어떤 회로를 맡고 있나",
              f"{수(잰것['house/designs.py']['줄'])}",
              "에이전트가 <b>회로에 딸리지 않게</b> 하는 유일한 방법"],
             ["5", "<code>&lt;분야&gt;/agent.py</code> &times;5", "각자의 일",
              f"{수(한명)} (합성 기준)",
              "여기서 비로소 도구가 돈다"],
             ["6", "<code>run.py</code>", "한 명 / 전체 / 메일",
              f"{수(잰것['house/run.py']['줄'])}",
              "다섯을 한 명령으로 묶는다(W5)"],
             ["7", "<code>spec.py · arch.py · gen.py</code>",
              "자연어 요청 &rarr; 새 회로",
              f"{수(잰것['house/spec.py']['줄'] + 잰것['house/arch.py']['줄'] + 잰것['house/gen.py']['줄'])}",
              "맡은 회로가 고정이면 여기까지 필요 없다"]]))

    c.날것(짚기(f"""<b>1&ndash;4 번을 합쳐 {수(코어)}줄이다.</b> 이것이 &lsquo;회사&rsquo; 의
    전부이고, 나머지는 각 분야의 전문성이다. <b>먼저 이 {수(코어)}줄을 짓고 가짜
    엔지니어 한 명(&ldquo;난수를 세 개 내고 막대그래프를 그린다&rdquo;)으로 끝까지
    돌려 보라.</b> 그것이 돌면 나머지는 채우기만 하면 된다."""))

    # ------------------------------------------------------------------
    c.절("W1.2 보고서 객체 — 이 설계의 중심")

    c.글("""가장 중요한 결정은 <b>보고서를 문자열이 아니라 객체로</b> 만드는 것이다.
    문자열이면 &ldquo;그림이 몇 장인가&rdquo; 를 물을 수 없고, 물을 수 없으면 강제할 수
    없다.""")

    c.날것(언어(
        "보고서 객체의 최소 골격 &mdash; <b>이대로 복사해서 시작해도 된다</b>",
        [("뼈대 — 쌓고, 세고, 낸다",
          """import time
from pathlib import Path

class Report:
    def __init__(self, owner, title, project):
        self.owner, self.title, self.project = owner, title, project
        self.parts   = []      # HTML 조각들
        self.summary = []      # 요약 줄 -- 메일 본문이 이걸 그대로 쓴다
        self.n_fig   = 0       # **세고 있다** -- 이게 있어야 강제할 수 있다
        self.n_tab   = 0
        self.measured = []     # (양, 값, 단위, 무엇으로 쟀나)
        self.t0 = time.time()
        self.work_sec = None   # 도구를 실제로 돌린 시간(보고서 조립 시간이 아니다)

    def figure(self, svg, caption, tool=""):
        self.n_fig += 1
        self.parts.append(
            f'<figure>{svg}<figcaption><b>Figure {self.n_fig}.</b> '
            f'{caption} <span class="tool">{tool}</span></figcaption></figure>')
        return self

    def table(self, head, rows, caption, tool=""):
        self.n_tab += 1
        ...
        return self""",
          "<code>self.n_fig</code> 를 <b>세는 것</b>이 요점이다. 이 한 줄이 "
          "다음 칸의 거절을 가능하게 한다"),
         ("산출물 계약 — 그림 0장은 보고서가 아니다",
          """    def html(self) -> str:
        if self.n_fig == 0:
            raise RuntimeError(
                "그림이 0 장인 보고서는 내지 않는다. "
                "이 회사는 글만 보내지 않는다 -- 무엇을 쟀는지 보여라.")
        ...

    def emit(self, name=None) -> Path:
        \"\"\"**HTML 을 먼저 쓰고** PDF 를 만든다. 순서가 중요하다.\"\"\"
        out.mkdir(parents=True, exist_ok=True)
        path = out / (name or self._default_name())
        h = self.html()
        (out / (path.stem + ".html")).write_text(h, encoding="utf-8")
        #      ^^^ 무슨 일이 있어도 이건 남는다
        try:
            from weasyprint import HTML
        except ImportError as e:
            raise RuntimeError(
                f"weasyprint 가 없어 PDF 를 못 만들었다 ({e}). HTML 은 남겼다.\\n"
                "**사람에게 설치를 시키지 마라** -- requirements 에 넣고 배포가 깔게 하라"
            ) from e
        HTML(string=h).write_pdf(str(path))
        return path""",
          "<b>순서가 설계다.</b> 실측 2026-09-21: VM 에서 세 명이 보고서를 다 만들고 "
          "마지막 한 줄에서 똑같이 <code>ModuleNotFoundError: weasyprint</code> 로 "
          "죽었다. HTML 을 먼저 쓰게 고친 뒤로는 <b>PDF 가 실패해도 내용이 남는다</b>"),
         ("측정 원장 — 모든 수에 출처를 붙인다",
          """    def measure(self, name, value, unit, tool):
        \"\"\"보고서에 들어가는 **모든 수**는 여기를 거친다.

        `tool` 칸에 '가정' 이라고 적힌 것과 도구 이름이 적힌 것이
        부록 A 에서 나란히 보인다 -- 읽는 사람이 어느 것이 잰 것이고
        어느 것이 정한 것인지 구별할 수 있어야 한다.
        \"\"\"
        self.measured.append((name, value, unit, tool))
        return self

# 부록 A 가 자동으로 나온다:
#   Quantity              Value      Unit   Measured with
#   Cells                 4,308             yosys stat
#   Node toggle rate      0.18              **assumed**    <- 눈에 띈다""",
          "<b>이 칸 하나가 보고서의 신뢰도를 만든다.</b> 잰 것과 가정한 것이 "
          "섞여 있으면 읽는 사람은 전부를 의심하거나 전부를 믿는데, 둘 다 틀렸다")],
        짚기="""<b>세 칸이 전부 &lsquo;거절&rsquo; 과 &lsquo;출처&rsquo; 에 관한 것</b>임을
        보라. 보고서 객체가 하는 일은 HTML 을 만드는 것이 아니라 <b>못난 보고서가
        나가지 못하게 막는 것</b>이다."""))

    c.날것(정리(
        "산출물 계약은 생성 시점이 아니라 배출 시점에 걸어야 한다",
        """보고서가 조건 <i>P</i>(예: 그림이 1장 이상)를 만족해야 한다고 하자.
        검사를 <b>조각을 쌓을 때마다</b> 거는 것과 <b>낼 때 한 번</b> 거는 것을
        비교하면, 후자만이 <b>모든 실행 경로</b>에서 <i>P</i> 를 보장한다.""",
        [("조각을 쌓는 메서드는 여러 개이고, 앞으로 더 늘어난다.",
          "<code>figure</code>, <code>table</code>, <code>text</code>, <code>note</code>&hellip;"),
         ("쌓을 때 거는 검사는 <b>그 메서드를 지나는 경로</b>에서만 돈다.",
          "호출되지 않은 메서드의 검사는 안 돈다."),
         ("그림을 한 장도 안 넣는 실행은 <code>figure</code> 를 안 부르므로, 거기 건 검사는 <b>영원히 안 돈다</b>.",
          "2 의 따름 &mdash; 막으려던 바로 그 경우가 검사를 피해 간다."),
         ("배출(<code>emit</code>)은 <b>모든 경로가 반드시 지나는</b> 한 점이다.",
          "보고서를 내려면 그것을 불러야 한다 &mdash; 정의상 병목이다."),
         ("그러므로 <i>P</i> 를 배출에 걸면 모든 경로가 검사된다.",
          "4 &mdash; 지나지 않는 경로가 없다."),
         ("<b>일반화</b>: 불변식은 <b>상태를 바꾸는 곳</b>이 아니라 <b>상태를 쓰는 곳</b>에 건다.",
          "쓰는 곳은 대개 하나이고 바꾸는 곳은 여럿이다."),
         ],
        가정="배출 경로가 하나여야 한다. 우회로(직접 HTML 을 쓰는 등)가 있으면 그것도 막아야 한다."))

    # ------------------------------------------------------------------
    c.절("W1.3 회로 등록부 — 에이전트를 회로에서 떼어낸다")

    c.글("""처음 지으면 에이전트가 회로 이름을 안에 박아 둔다
    (<code>read_verilog nsw_fir.sv</code>). 그러면 <b>회로가 하나뿐인 회사</b>가
    된다. 두 번째 회로를 받는 순간 다섯 파일을 다 고쳐야 한다.""")

    c.날것(dia.견줌(
        "회로가 박혀 있을 때",
        ["에이전트 5개가 각자 파일 이름을 안다",
         "새 회로 = 5개 파일 수정",
         "두 회로를 비교하려면 코드를 갈아 끼운다",
         "'이 회사가 맡은 회로' 라는 개념이 없다"],
        "등록부가 있을 때",
        ["<code>designs.find(\"fir\")</code> 하나만 안다",
         "새 회로 = 등록부에 한 줄",
         "<code>!회사 rtl tdc</code> 처럼 인자로 고른다",
         "<code>!회사 회로</code> 가 목록을 보여 준다"],
        제목="W1.3 — 회로를 자료로 만들면 회사가 확장된다", 폭=640))

    c.날것(언어(
        "등록부 &mdash; 자료 클래스 하나면 된다",
        [("등록부",
          """from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Design:
    key:   str                      # "fir"
    name:  str                      # "NSW-FIR v1.0"
    top:   str                      # 합성 top 모듈 이름
    RTL:   list                     # [Path, ...]
    TB:    Path | None = None       # 검증 하니스
    params: dict = field(default_factory=dict)
    SDC:   Path | None = None
    UPF:   Path | None = None
    clocks: dict = field(default_factory=dict)   # {"clk": 13.0}
    source: str = ""                # 손으로 쓴 것인가 생성된 것인가
    oneline: str = ""

_TABLE: dict[str, Design] = {}

def register(d: Design) -> Design:
    _TABLE[d.key] = d
    return d

def find(key: str) -> Design:
    if key not in _TABLE:
        raise KeyError(f"모르는 회로: {key!r} -- 있는 것: {', '.join(sorted(_TABLE))}")
    return _TABLE[key]        # **조용히 기본값으로 안 넘어간다**""",
          "<code>find</code> 가 <b>KeyError 를 던지는 것</b>이 중요하다. "
          "기본 회로로 조용히 넘어가면 <b>엉뚱한 회로의 보고서</b>가 나오고, "
          "그 보고서는 완벽해 보인다"),
         ("에이전트가 이렇게 받는다",
          """def work(design=None) -> dict:
    d = design or designs.find("fir")          # 기본은 있되 명시적
    net = synth.run(d.params, top=d.top, design=d)
    ...

# run.py 가 인자를 흘려 준다
def one(key, design=None):
    fn = _AGENTS[key]
    try:
        return fn(design=design)
    except TypeError:
        # 아직 design= 를 안 받는 에이전트 -- **조용히 넘어가지 않는다**
        if design:
            print(f"!! {key}: does not take design= yet -- running default")
        return fn()""",
          "<code>except TypeError</code> 로 넘어가되 <b>말을 한다</b>. "
          "말 없이 넘어가면 사용자는 TDC 를 시켰는데 FIR 보고서를 받고도 모른다"),
         ("무엇을 못 하는지도 등록부가 안다",
          """def missing(d: Design) -> list[str]:
    \"\"\"이 회로에 대해 **아직 못 하는 것**을 적는다.

    '못 한다' 를 적어 두지 않으면 보고서가 그 자리를 조용히 비우고,
    읽는 사람은 그 항목이 통과한 줄 안다.
    \"\"\"
    gaps = []
    if not d.TB:  gaps.append("검증 하니스가 없다 -- DV 는 스모크만 돈다")
    if not d.SDC: gaps.append("SDC 가 없다 -- STA 는 기본 주기로만")
    if not d.UPF: gaps.append("UPF 가 없다 -- 전원 의도 점검 없음")
    return gaps""",
          "<b>결손을 자료로 만든다.</b> 그러면 보고서가 &lsquo;이 회로는 여기까지만 "
          "봤다&rsquo; 를 자동으로 적을 수 있다")],
        짚기="""<b>등록부는 열 줄짜리 자료 클래스지만, 이것이 있고 없고가 &lsquo;회사&rsquo;
        와 &lsquo;스크립트 다섯 개&rsquo; 를 가른다.</b> 이 저장소에서 새 회로를 받는 일
        (8탭 FIR 을 AXI 붙은 IP 와 NPU PE 어레이로 키우는 것 같은)이 가능한 이유가
        전적으로 이 파일이다."""))

    # ------------------------------------------------------------------
    c.절("W1.4 실패도 보고서로 낸다")

    c.날것(정리(
        "실패했을 때 보고서를 안 내면 실패의 원인을 아무도 못 본다",
        """에이전트가 도구 실행에 실패했을 때 (a) 예외를 던지고 끝내는 것과
        (b) <b>실패를 담은 보고서</b>를 내는 것을 비교하자. 관측자가 보는 정보량은
        (b) 가 엄격히 많다 &mdash; (a) 는 스택 트레이스 한 줄이고, (b) 는 그 시점의
        <b>환경 · 입력 · 중간 산출물</b>을 전부 담을 수 있다.""",
        [("(a) 에서 관측자가 얻는 것은 예외 메시지와 호출 스택뿐이다.",
          "프로세스가 거기서 끝나므로 그 뒤 코드가 못 돈다."),
         ("실패의 원인은 대개 <b>환경</b>에 있다 &mdash; 라이브러리가 없다, 파일이 없다, 판이 다르다.",
          "실측 2026-09-21: 다섯 중 셋이 <code>weasyprint</code> 없음, 하나가 빈 목록에 <code>min()</code>, 하나가 <code>KeyError</code>."),
         ("그 환경 정보는 예외 메시지에 안 들어 있다.",
          "<code>ModuleNotFoundError: weasyprint</code> 는 <b>어느 파일을 어디까지 만들었는지</b>를 말하지 않는다."),
         ("(b) 는 그 정보를 담는 자리를 가진다 &mdash; 표 한 장에 라이브러리 경로 · 존재 여부 · 입력 파일 · 걸린 시간.",
          "보고서 객체가 이미 표를 만들 수 있으므로 추가 비용이 거의 없다."),
         ("<b>따라서 실패 경로에도 보고서 객체를 태워야 한다.</b>",
          "4 &mdash; 같은 장치를 실패에도 쓴다."),
         ("<b>그리고 그 보고서에도 그림이 한 장 필요하다</b> &mdash; 산출물 계약이 실패 보고서에만 예외를 두면 그 예외가 곧 빠져나갈 구멍이 된다.",
          "정리 43 의 배출 시점 논증 &mdash; 우회로를 만들면 보장이 깨진다. 그래서 &lsquo;그릴 것이 없다&rsquo; 는 빈 그림을 그린다."),
         ],
        가정="실패가 프로세스를 즉사시키지 않는 종류여야 한다(OOM·SIGKILL 은 이 정리 밖이다)."))

    c.날것(사고("""<b>이 정리가 나온 실측.</b> VM 에서 다섯 엔지니어가 동시에 죽었다.
    Ethan 은 <code>ValueError: min() iterable argument is empty</code>,
    Priya·Sofia·Kenji 는 <code>ModuleNotFoundError: weasyprint</code>,
    Marcus 는 <code>KeyError: '코너'</code>. 다섯 개의 스택 트레이스만 남았고,
    <b>무엇을 어디까지 했는지는 하나도 안 남았다.</b> 지금은 셋 다 보고서로 나온다
    &mdash; 합성이 실패하면 &lsquo;합성 실패 &mdash; 무엇이 막혔나&rsquo; 절이 나오고,
    거기에 라이브러리 경로와 존재 여부가 표로 찍힌다."""))

    c.날것(언어(
        "실패 보고서의 꼴",
        [("에이전트 안에서",
          """def report(m: dict) -> Report:
    R = Report(P, "NSW-FIR v1.0 — Synthesis Sign-off", "nsw_fir")
    net = m.get("synth") or {}

    # **일찍 돌아온 경우를 여기서 받는다.**
    if not net.get("ok") or "corners" not in m:
        R.summary("<b>Synthesis failed; this report carries no timing or power.</b>")
        R.summary(f"Reason: {str(net.get('why', 'no result'))[:200]}")
        R.section("Synthesis failure — what blocked")
        R.figure(viz.empty("Synthesis failed; there is nothing to plot"))
        R.table(["Item", "Value"],
                [["Succeeded",  str(net.get("ok"))],
                 ["Reason",     str(net.get("why", ""))[:400]],
                 ["Library",    str(LIB)],
                 ["Library exists", str(LIB.exists())],   # <- 진짜 원인이 여기 있다
                 ["RTL",        ", ".join(map(str, m.get("rtl", [])))],
                 ["Elapsed",    f"{m.get('sec')} s"]],
                "<b>This table is the whole report.</b>")
        R.limits("Nothing was measured. This is a failure report.")
        return R
    ...""",
          "<code>Library exists</code> 한 줄이 <b>진짜 원인</b>이었다 &mdash; "
          "생성물이라 커밋 안 하는 <code>.lib</code> 파일이 VM 에 없었다. "
          "예외만 봤으면 영영 몰랐을 것"),
         ("시작할 때 한 번 묻는 편이 낫다",
          """def pdf_available() -> dict:
    \"\"\"**다섯이 줄줄이 같은 까닭으로 죽기 전에 한 번 묻는다.**

    세 번 같은 말을 듣는 것보다 시작할 때 한 번 아는 것이 낫다.
    \"\"\"
    try:
        import weasyprint
        return {"ok": True, "version": getattr(weasyprint, "__version__", "?")}
    except ImportError as e:
        return {"ok": False, "why": str(e)[:120],
                "fix": "requirements 에 weasyprint>=60 -> 머지 -> 배포가 깐다"}""",
          "<b>사전 점검(preflight)</b>이다. 다섯 번 실패하고 다섯 번 같은 보고를 "
          "받는 대신, 시작할 때 한 줄로 안다")],
        짚기="""<b>실패를 자료로 다루면 실패가 싸진다.</b> 예외는 프로그램을 멈추지만,
        실패 보고서는 <b>다음 사람이 고칠 수 있게</b> 한다 &mdash; 그리고 그 다음
        사람이 대개 나 자신이다."""))

    # ------------------------------------------------------------------
    c.절("W1.5 첫날에 무엇을 하나 — 구체적으로")

    c.날것(표("<b>하루치 작업으로 끝까지 도는 것을 만든다.</b> 전문성은 그 다음이다.",
            ["시간", "무엇", "끝났는지 어떻게 아나"],
            [["1시간", "<code>people.py</code> &mdash; 사람 하나만. 이름 · 팀 · 메일",
              "<code>print(P.EVERYONE)</code> 가 돈다"],
             ["2시간", "<code>report.py</code> &mdash; figure/table/emit, 그림 0장 거절",
              "<b>그림 없이 emit 하면 RuntimeError 가 난다</b>"],
             ["1시간", "<code>viz.py</code> &mdash; 막대그래프 하나만 (SVG 문자열)",
              "브라우저로 열어 보인다"],
             ["1시간", "가짜 엔지니어 &mdash; 난수 3개를 막대로 그리고 보고서를 낸다",
              "<b>PDF 가 나온다</b>"],
             ["1시간", "<code>run.py</code> &mdash; <code>one(key)</code> 하나",
              "명령줄에서 한 줄로 돈다"],
             ["1시간", "검사 &mdash; 그림 0장 거절이 <b>실제로</b> 나는지",
              "일부러 망가뜨려 빨간불을 본다(W4)"],
             ["나머지", "진짜 도구를 붙인다 &mdash; 가짜 엔지니어를 하나씩 바꾼다",
              "보고서의 수가 <b>실행마다 달라진다</b>"]]))

    c.날것(짚기("""<b>&lsquo;가짜 엔지니어로 먼저 끝까지 돌린다&rsquo; 가 이 표의 핵심이다.</b>
    진짜 도구(yosys · verilator)를 붙이는 것은 각각 몇 시간씩 걸리는데, 그것을
    먼저 하면 <b>보고서가 안 나오는 이유가 도구 때문인지 뼈대 때문인지</b> 구별이
    안 된다. 난수 세 개짜리 가짜로 PDF 가 나오는 것을 먼저 보고, 그 다음에 난수를
    진짜 측정으로 바꾼다."""))

    c.날것(예제(
        "가짜 엔지니어 &mdash; 스무 줄",
        """뼈대가 도는지 확인하는 것이 목적이다. 진짜 일은 안 한다.""",
        """보고서 객체를 만들고, 난수 세 개로 막대를 그리고, 측정 원장에 적고, 낸다.
        <b>측정 원장의 도구 칸에 &lsquo;가짜&rsquo; 라고 적는다</b> &mdash; 그래야 이 PDF 를
        나중에 보고 진짜인 줄 착각하지 않는다.""",
        """<pre style="font-size:8pt">import random
def work():
    r = random.Random(0)
    return {"a": r.random(), "b": r.random(), "c": r.random()}

def report(m):
    R = Report(P.ETHAN, "SKELETON CHECK — not a real report", "smoke")
    R.summary("이것은 뼈대 점검용이다. 어떤 도구도 돌지 않았다.")
    R.figure(viz.bar(list(m), list(m.values()), "random"), "난수 세 개", "가짜")
    for k, v in m.items():
        R.measure(k, round(v, 4), "", "<b>가짜</b> — 아무것도 재지 않았다")
    return R

def run():
    R = report(work()); return {"pdf": R.emit()}</pre>""",
        """<b>&lsquo;나중에 지우겠다&rsquo; 고 도구 칸을 비워 두면 안 된다.</b> 이 PDF 가
        어딘가에 남아 있다가 진짜 보고서와 섞인다. 도구 칸에 <b>가짜</b> 라고 적어
        두면 그 순간 구별된다 &mdash; 그리고 진짜로 바꿀 때 그 칸이 할 일 목록이 된다.""",
        덧=f"""이 스무 줄이 돌면 뼈대가 끝난 것이다. 이 저장소에서 가장 작은
        진짜 에이전트가 {수(한명)}줄인데, 그 차이는 전부 <b>합성 도메인 지식</b>이지
        뼈대가 아니다."""))

    c.날것(유도("이 장을 한 문단으로", [
        ("만드는 것은 &lsquo;일을 하고 그것을 증명하는 보고서를 내는 프로그램 다섯 개&rsquo; 다",
         "이 문장에 설계가 다 들어 있다"),
        ("보고서를 문자열이 아니라 <b>객체</b>로 만든다",
         "세지 못하면 강제하지 못한다 &mdash; <code>n_fig</code> 한 줄이 계약을 가능하게 한다"),
        ("계약은 <b>배출 시점</b>에 건다",
         "정리 43 &mdash; 쌓을 때 걸면 그 메서드를 안 부르는 경로가 빠져나간다"),
        ("HTML 을 PDF 보다 먼저 쓴다",
         "PDF 단계가 죽어도 내용이 남는다 &mdash; 실측으로 배운 순서"),
        ("모든 수에 <b>출처 칸</b>을 붙인다",
         "잰 것과 가정한 것이 부록에서 나란히 보여야 한다"),
        ("회로를 <b>등록부</b>로 떼어낸다",
         "그래야 두 번째 회로를 받을 때 다섯 파일을 안 고친다"),
        ("<b>실패도 보고서로 낸다</b>",
         "정리 44 &mdash; 예외는 원인을 안 담는다. 실패 보고서는 담는다"),
        ("가짜 엔지니어로 먼저 끝까지 돌린다",
         "뼈대와 도구를 분리해서 디버깅한다"),
    ]))

    return c.완성()
