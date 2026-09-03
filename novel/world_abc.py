"""스핀오프 세계 -- 대학 로맨스 / 청춘 / 직장인-대학생.

인물을 A·B·C·D 로 두고 내용을 원작과 다르게 잡았다. 아키텍처는 인물에 의존하지 않는다는
것을 이 파일이 증명한다 -- 구조 매핑(회고 1인칭, 이항 대립 축, 편지 모드, 푼크툼, 절제된
묘사)만 남기고 세계를 갈아끼웠다.

이항 대립 축의 이식:
    원작   나오코(죽음의 인력) ────── 미도리(삶의 추동)
    여기   B(같은 궤도 · 캠퍼스 · 스무 살의 시간) ────── C(다른 세계 · 직장 · 어른의 시간)

narrative_pull 은 -100(B 쪽, 익숙한 궤도) .. +100(C 쪽, 궤도 이탈)이다. A 의 방황은
이 축 위의 좌표 하나로 표현되고, Director 가 그 좌표를 계획하고 관문이 궤적의 연속성을 본다.
"""
from .state import Novel, Character, Scene

TITLE = "가을 학기의 환승"
POV = "A"


def build() -> Novel:
    return Novel(
        title=TITLE,
        pov_character=POV,
        narrator_foreknowledge=[
            "그해 겨울 B 는 교환학생으로 떠나고 나는 배웅하지 못한다",
            "C 의 회사는 이듬해 봄에 사무실을 옮긴다",
            "이 계절의 카페는 지금 없다",
        ],
        characters=[
            Character(
                name="A", persona="스물둘, 건축학과 3학년. 관찰이 많고 말이 적다. "
                                  "학교 앞 카페에서 저녁 알바를 한다.",
                hidden_agenda="설계 스튜디오를 그만두고 싶다는 생각을 아무에게도 말하지 않았다.",
                knows=["휴학 신청서", "C의 이직"],
                emotion_envelope={}),
            Character(
                name="B", persona="같은 과 동기. 명랑하고 계획이 뚜렷하다. 웃음이 많고 "
                                  "그 웃음으로 자기 불안을 덮는다.",
                hidden_agenda="교환학생 지원서를 이미 냈고 A 에게 아직 말하지 않았다.",
                knows=["교환학생 지원서"],
                # B 는 밝은 인물이다. 관문이 밝음만 벌해서 인물이 균일한 우울로 수렴하는
                # 것을 막는다 -- 이 하한이 없으면 B 는 몇 씬 만에 다른 사람이 된다.
                emotion_envelope={"joy": 40}),
            Character(
                name="C", persona="스물아홉, 카페 옆 건물 설계사무소의 직원. 말이 느리고 "
                                  "정확하다. 늘 같은 자리에 앉는다.",
                hidden_agenda="회사를 그만둘 생각이지만 그럴 이유를 스스로도 모른다.",
                knows=["C의 이직"],
                emotion_envelope={}),
            Character(
                name="D", persona="A 의 오랜 친구. 눈치가 빠르고 입이 가볍지 않다. "
                                  "촉매 역할을 한다.",
                hidden_agenda="A 와 B 사이가 이미 끝났다는 것을 둘보다 먼저 알았다.",
                knows=["교환학생 지원서"],
                emotion_envelope={"joy": 30}),
        ],
        # 별칭은 첫 실측 런에서 필요해졌다. 텍스트에는 "교환학생 지원서" 가 아니라 "지원서"
        # 로만 나와서 정확 일치로는 안 걸렸고, A 가 모르는 것을 속으로 생각하는 산문이 통과했다.
        facts={"secrets": {
            "교환학생 지원서": {"knows": ["B", "D"], "aliases": ["지원서", "교환학생"]},
            "휴학 신청서": {"knows": ["A"], "aliases": ["휴학"]},
            "C의 이직": {"knows": ["A", "C"], "aliases": ["이직"]},
        }},
        scenes=[
            Scene(id="s01", location="9월, 학교 앞 카페의 저녁",
                  punctum="원두 그라인더가 멎은 뒤의 정적",
                  participants=["A", "B"], mode="dialogue",
                  directives=["A 는 스튜디오 얘기를 피한다",
                              "B 는 지원서를 말하려다 만다",
                              "둘 다 아무 말도 하지 않는 구간이 한 번 있을 것"],
                  relation_ops=[{"op": "start", "kind": "연인", "members": ["A", "B"]}],
                  fact_ops=[{"key": "A.전공", "value": "건축학"},
                            {"key": "B.학년", "value": "3학년"}]),
            Scene(id="s02", location="10월, 설계사무소 앞 비 오는 계단",
                  punctum="젖은 트레이싱지에서 나는 냄새",
                  participants=["A", "C"], mode="dialogue",
                  directives=["C 는 도면 얘기만 한다",
                              "A 는 처음으로 학교 밖의 시간을 본다",
                              "A 의 narrative_pull 이 양의 방향으로 움직인다"]),
            Scene(id="s03", location="11월, B 의 자취방",
                  punctum="창틀에 쌓인 마른 화분의 흙",
                  participants=["A", "B"], mode="dialogue",
                  directives=["지원서가 드러난다", "관계가 끝난다"],
                  relation_ops=[{"op": "end", "kind": "연인", "members": ["A", "B"]}]),
            Scene(id="s04", location="12월, 교환학생 기숙사에서 온 편지",
                  punctum="봉투 안쪽에 눌린 낯선 우표 자국",
                  participants=["B"], mode="letter",
                  directives=["B 가 A 에게 긴 편지를 쓴다",
                              "과거의 파편과 현재의 일상 묘사가 섞일 것"]),
            Scene(id="s05", location="이듬해 3월, 이사 전날의 빈 사무실",
                  punctum="벽에서 뜯어낸 도면 자국의 사각형",
                  participants=["A", "C"], mode="dialogue",
                  directives=["A 와 C 의 관계가 시작된다"],
                  relation_ops=[{"op": "start", "kind": "연인", "members": ["A", "C"]}],
                  fact_ops=[{"key": "C.직장", "value": "다른 사무소"}]),
        ])
