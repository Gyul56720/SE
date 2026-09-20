"""
G024 -- 논문마다 **선행조사 기록**이 있고, 거기에 가장 가까운 선행연구가 **찾을 수 있는
꼴로** 적혀 있으며, 우리가 그것과 무엇이 다른지가 적혀 있는가.

사용자(2026-09-18): "이미 있는 연구의 반복 ... 이건 사용자에 관한 기만이라고 느껴졌다."

이 저장소는 같은 방식으로 **다섯 번** 졌다. 주제를 고르고, 짓고, 재고, 원고까지 쓰고,
**그러고 나서** 이미 있는 것을 알았다.

  · 비선형 재귀의 look-ahead        -> Parhi 가 선형 재귀에 대해 이미(1989/1999)
  · LLM-RTL 벤치마크 변이 검사      -> GateTruth (arXiv:2608.12635, 2026) 가 그대로
  · 학습 LUT 비용법칙(점유≠주소폭)  -> ReducedLUT (FPGA'25, arXiv:2412.18579) 가 그대로
  · LUT-NN 을 ASIC 으로 값매김      -> BitLogic (arXiv:2602.07400, 2026) 이 이미
  · FPGA 내부 RO/TDC 지연 센서      -> PUF · 원격전력공격 · PVT 적응클럭으로 빽빽

다섯 번 다 조사가 **투자 뒤에** 왔다. 시간과 돈이 거기서 다 샜다.

## 무엇을 위반으로 보는가

`paper/<이름>.html` 마다 `paper/선행조사/<이름>.md` 가 있어야 하고, 아래 네 마디가 모두
있고 그 아래에 내용이 있어야 한다.

  · `## 가장 가까운 선행연구` -- **찾을 수 있는 꼴**이 최소 하나 (arXiv:… · doi:… ·
    `학회/저널 + 연도`). "비슷한 연구가 있다" 같은 말은 조사한 것이 아니다
  · `## 우리가 그것과 다른 점`
  · `## 찾아본 질의` -- 최소 3줄. 무엇으로 찾았는지가 남아야 다음 사람이 이어서 판다
  · `## 아직 못 지운 가능성` -- **이미 있는 것일 수 있는 자리**를 스스로 적는다.
    다섯 번의 패배는 전부 "없다고 생각했다" 에서 났다. 없다고 말하는 대신 **어디를
    아직 못 봤는지** 적게 한다

## 무엇을 안 잡는가 -- 그리고 왜

  · `attic/` 은 안 본다 -- 폐기한 원고의 무덤이고, 거기 남은 것이 RED 증명의 근거다
  · **조사가 짓기보다 먼저였는지는 못 본다.** git 이력을 봐야 하는데, 증명 하니스가 사고
    트리를 단일 커밋 저장소로 다시 만들기 때문에 거기엔 이력이 없다. 순서 규칙은
    `CLAUDE.md` 에 적혀 있고, 이 게이트는 **기록의 존재**만 강제한다
  · 적힌 선행연구가 진짜 가장 가까운 것인지는 못 본다. 기계가 분야를 읽을 수는 없다
"""
from __future__ import annotations

import re

RULE_ID = "G024"
TITLE = "논문마다 선행조사 기록이 있고 가장 가까운 선행연구가 찾을 수 있는 꼴로 적혀 있는가"
ORIGIN = "ff31763 (선행조사 없이 원고까지 갔다 -- 같은 방식으로 다섯 번 졌다)"
EVIDENCE = "attic/폐기논문/README.md"

_조사자리 = "paper/선행조사"
_마디들 = ("가장 가까운 선행연구", "우리가 그것과 다른 점", "찾아본 질의", "아직 못 지운 가능성")
_질의최소 = 3
# arXiv:2412.18579 · doi:10.1145/… · "FPGA'25" · "IEEE ... , 2020" 처럼 **찾아갈 수 있는** 꼴.
_찾을수있는꼴 = re.compile(r"arxiv[:\s]*\d{4}\.\d{4,5}|doi[:\s]*10\.\d{4,9}/|https?://|\b(?:19|20)\d{2}\b", re.I)


def _논문들(ctx):
    자리 = ctx.repo / "paper"
    return sorted(p for p in 자리.glob("*.html") if p.is_file()) if 자리.is_dir() else []


def _마디속(글: str, 마디: str) -> "list[str] | None":
    """그 마디 아래의 빈 줄 아닌 줄들. 마디 자체가 없으면 None."""
    줄들 = 글.splitlines()
    for i, 줄 in enumerate(줄들):
        if re.match(r"^\s*#{1,6}\s*" + re.escape(마디) + r"\s*$", 줄):
            속 = []
            for 뒤 in 줄들[i + 1:]:
                if re.match(r"^\s*#{1,6}\s+", 뒤):
                    break
                if 뒤.strip():
                    속.append(뒤.strip())
            return 속
    return None


def check(ctx) -> "list[str]":
    위반 = []
    for path in _논문들(ctx):
        이름 = path.name
        조사 = ctx.repo / _조사자리 / (path.stem + ".md")
        if not 조사.is_file():
            위반.append(
                f"{이름}: 선행조사 기록 {_조사자리}/{path.stem}.md 가 없다 -- 이 저장소는 조사를 "
                f"투자 뒤에 해서 같은 방식으로 다섯 번 졌다. 네 마디({' · '.join(_마디들)})를 "
                f"채운 파일을 **짓기 전에** 만들어라.")
            continue
        try:
            글 = 조사.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            위반.append(f"{_조사자리}/{path.stem}.md: 읽을 수 없다 ({e}).")
            continue
        for 마디 in _마디들:
            속 = _마디속(글, 마디)
            if 속 is None:
                위반.append(f"{_조사자리}/{path.stem}.md: '## {마디}' 마디가 없다.")
            elif not 속:
                위반.append(f"{_조사자리}/{path.stem}.md: '## {마디}' 아래가 비어 있다.")
        가까운 = _마디속(글, _마디들[0]) or []
        if 가까운 and not any(_찾을수있는꼴.search(줄) for 줄 in 가까운):
            위반.append(
                f"{_조사자리}/{path.stem}.md: '## {_마디들[0]}' 에 찾아갈 수 있는 꼴이 하나도 없다 "
                f"-- arXiv 번호 · DOI · URL · 연도 중 하나는 있어야 조사한 것이다.")
        질의 = _마디속(글, "찾아본 질의") or []
        진짜질의 = [줄 for 줄 in 질의 if len(줄.lstrip("-*0123456789. ").strip()) >= 4]
        if 질의 and len(진짜질의) < _질의최소:
            위반.append(
                f"{_조사자리}/{path.stem}.md: '## 찾아본 질의' 가 {len(진짜질의)}줄이다 "
                f"-- 최소 {_질의최소}줄. 무엇으로 찾았는지가 남아야 다음에 이어서 판다.")
    return 위반
