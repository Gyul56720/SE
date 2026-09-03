"""소설 오케스트레이션의 공유 상태 -- 파일 영속, 재개 가능.

**Pydantic 대신 dataclass 를 쓴다.** plan_schema.py 와 같은 이유다: 이 저장소가 반복
실증한 것은 "인메모리 상태는 프로세스 재시작에 소실된다" 이고, 장편 소설은 수십~수백 씬이라
며칠 도는 작업이며 반드시 중간에 죽는다. 그래서 씬 하나가 끝날 때마다 JSON 으로 떨군다.
새 의존성도 늘리지 않는다(requirements.txt 에 pydantic 이 없다).

원본 설계와 바꾼 것:
  · 감정 축에 **narrative_pull 을 추가**했다. 원 문서 §2 가 이 소설의 진짜 상태 공간을
    "나오코(죽음의 인력) ↔ 미도리(삶의 추동)" 로 정확히 짚어놓고 §4 스키마에는 안 넣었다.
    joy/melancholy/isolation 세 축은 그 축을 표현하지 못한다.
  · Character 에 emotion_envelope 를 넣었다. **미도리가 지워지는 것을 막기 위한 것**이다
    (gate.V003 참고).
  · Scene 에 pov_present / mode 를 넣었다. 1인칭 회고는 화자가 없는 씬을 서술할 수 없다.
  · narrator_foreknowledge -- 회고 프레임을 분위기가 아니라 상태로 만든다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

# 감정 축. narrative_pull 은 -100(죽음의 인력/나오코) .. +100(삶의 추동/미도리).
# 나머지 셋은 0..100.
AXES = ("joy", "melancholy", "isolation", "narrative_pull")
BIPOLAR = ("narrative_pull",)


@dataclass
class Character:
    name: str
    persona: str
    hidden_agenda: str = ""
    emotions: dict = field(default_factory=lambda: {a: 0 for a in AXES})
    # 이 인물이 아는 비밀 용어들. 발화에 모르는 것이 나오면 지식 누출이다.
    knows: list = field(default_factory=list)
    # 씬 안에서 이 축이 적어도 한 번은 이 값에 도달해야 한다.
    # 미도리: {"joy": 40} -- 관문이 밝음만 벌해서 인물이 균일한 우울로 수렴하는 것을 막는다.
    emotion_envelope: dict = field(default_factory=dict)


@dataclass
class Turn:
    actor: str
    inner_thought: str = ""
    action: str = ""
    speech: str = ""
    emotions: dict = field(default_factory=dict)


@dataclass
class Scene:
    id: str
    location: str = ""
    punctum: str = ""
    directives: list = field(default_factory=list)
    participants: list = field(default_factory=list)
    # "dialogue" | "letter" | "reported"
    mode: str = "dialogue"
    turns: list = field(default_factory=list)
    prose: str = ""
    status: str = "pending"          # pending | gated | verified | failed
    violations: list = field(default_factory=list)
    attempts: list = field(default_factory=list)


@dataclass
class Novel:
    title: str
    pov_character: str
    characters: list
    scenes: list = field(default_factory=list)
    # 화자가 이미 알고 있는 미래. Narrator 가 가끔 흘려 회고의 아이러니를 만든다.
    narrator_foreknowledge: list = field(default_factory=list)
    # 확립된 사실 원장. 모순 검사의 기준이 된다.
    facts: dict = field(default_factory=dict)

    # ---- 영속 ----
    @staticmethod
    def load(path) -> "Novel":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return Novel(
            title=raw["title"], pov_character=raw["pov_character"],
            characters=[Character(**c) for c in raw["characters"]],
            scenes=[Scene(**{**s, "turns": [Turn(**t) for t in s.get("turns", [])]})
                    for s in raw.get("scenes", [])],
            narrator_foreknowledge=raw.get("narrator_foreknowledge", []),
            facts=raw.get("facts", {}))

    def save(self, path):
        Path(path).write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2),
                              encoding="utf-8")

    def character(self, name: str) -> Character:
        for c in self.characters:
            if c.name == name:
                return c
        raise KeyError(name)

    def scene(self, sid: str) -> Scene:
        for s in self.scenes:
            if s.id == sid:
                return s
        raise KeyError(sid)

    def next_pending(self):
        """아직 verified 가 아닌 첫 씬. 소설은 선형이라 DAG 가 아니라 시퀀스다."""
        for s in self.scenes:
            if s.status != "verified":
                return s
        return None

    def others(self, name: str) -> list:
        return [c.name for c in self.characters if c.name != name]
