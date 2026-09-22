# 선행조사 — mera1_event_recorder

요청: MERA-1 v1.0 Event Recorder Core 를 ASIC 으로 설계한다. wave-042ef1d4.png wave-1158c11e.png

## 무엇을 짓기 전인가

MERA-1 v1.0 Event Recorder Core ASIC digital frontend

## 찾아본 질의

- `digital IP architecture low power CMOS`

## 가장 가까운 선행연구

| 무엇 | arXiv/DOI | 연도 | 우리가 다른 점 |
|---|---|---|---|
| **(아직 안 채움)** | | | |

> **이 표가 비어 있으면 코드를 쓰면 안 된다.** CLAUDE.md:
> "'없는 것 같다' 를 조사 결과라고 하지 않는다. 어디를 **아직 못 봤는지** 적는다."

## 아직 못 본 곳

- 상용 IP 카탈로그 (Synopsys DesignWare · Cadence · Arm)
- 해당 분야 표준 (자동차면 ISO 26262 · AEC-Q100, 통신이면 해당 규격)
- 특허 (이 구조가 이미 특허일 수 있다)
- 최근 3년 학회 (ISSCC · VLSI · DAC · DATE)

## 아직 못 지운 가능성

- 이미지(wave-042ef1d4.png, wave-1158c11e.png) 및 텍스트 설명의 부재로 인한 프로토콜 및 타이밍 스펙 오작동
- 외부 아날로그 블록과의 인터페이스 타이밍 불일치로 인한 메타스테이빌리티 및 데이터 유실
- 이벤트 폭주 시 내부 버퍼 용량 부족으로 인한 정보 손실
- 필요한 타이밍 및 제어 레지스터 맵 미확정으로 인한 RTL 구조 재설계 위험

---
_이 파일은 `house/arch.py` 가 틀만 만든 것이다. 표를 채우는 것은 사람이나
`!연구` 기관의 몫이고, **채우기 전에는 RTL 을 짓지 않는다.**_
