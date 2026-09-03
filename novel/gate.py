"""기계적 관문 -- LLM 을 쓰지 않는다. 위반 목록을 돌려준다.

원 설계의 Critic 은 LLM 이 LLM 출력을 주관적으로 평가하고 롤백을 결정했다. mathgen/README
가 그것을 하지 말라고 적어둔 바로 그 구조다(DeepMind, LLMs Cannot Self-Correct Reasoning
Yet -- 내재적 자기교정은 개선이 없거나 성능을 떨어뜨린다).

여기서 하는 일은 **판정을 둘로 가르는 것**이다:

    기계 관문 (이 파일)  -- 결정적으로 판정되는 것만. 하드 위반은 기각 권한을 갖는다.
    LLM 비평가          -- "하루키다운가" 같은 취향. **자문만 한다. 기각 권한이 없다.**

반환은 (bool, str) 이 아니라 **위반 목록**이다. gates/__init__.py 의 규약을 그대로 떼왔다.
이유: 소설에서 "실패했다" 는 수리 신호가 못 된다. 어느 규칙이 어디서 왜 깨졌는지가 있어야
Director 와 Actor 에게 되먹일 것이 생긴다. 직선거리 심판이 "22.5% 더 짧은 점이 있다" 고
짚어줘서 쓸모가 있었던 것과 같다.

severity:
    hard -- 확실한 위반. 씬을 기각한다.
    soft -- 의심스럽다. 기록하고 수리 프롬프트에 실지만 기각하지는 않는다.

soft 를 따로 둔 이유가 있다. **과잉 기각하는 심판은 맞는 답도 버린다** -- 직선거리에서
상대 임계만 쓰다가 진짜 최소가 0 일 때 정답을 기각한 것이 그 사례다. 한국어 패턴 검사는
정밀도가 100% 가 아니므로, 애매한 것은 기각이 아니라 보고로 내린다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

MAX_EMOTION_DELTA = 35          # 턴당 축 변화량 상한. 이보다 크면 인물이 갑자기 변한 것이다
RANGE_COLLAPSE = 8              # 씬 전체 감정 폭이 이보다 좁으면 "회색 죽" 으로 수렴한 것
DIRECT_EMOTION_SOFT = 1         # 이 횟수까지는 soft, 넘으면 hard

# 타인의 내면을 사실로 단정하는 술어. 1인칭 회고 화자는 이것을 쓸 수 없다.
INTERIORITY = ("생각했다", "생각한다", "느꼈다", "느낀다", "깨달았다", "믿었다",
               "기억했다", "바랐다", "후회했다", "결심했다", "확신했다", "알고 있었다",
               "그리워했다", "두려워했다", "사랑했다")

# 감정을 직접 서술하는 말. 대사 안에서는 허용된다 -- 인물은 "외로워" 라고 말할 수 있다.
# 금지되는 것은 **서술**이다.
DIRECT_EMOTION = ("슬펐다", "슬프다", "외로웠다", "외롭다", "행복했다", "행복하다",
                  "기뻤다", "우울했다", "절망했다", "괴로웠다", "비참했다", "쓸쓸했다")

_SENT = re.compile(r"[^.!?…\n]+[.!?…]?")
_QUOTED = re.compile(r"[\"“”][^\"“”]*[\"“”]|'[^']*'|「[^」]*」")
_NARRATOR = re.compile(r"\b나(는|도|만|의|에게|를|와|랑)?\b|내(가|\s)")


@dataclass
class Violation:
    rule: str
    severity: str        # "hard" | "soft"
    where: str
    detail: str

    def __str__(self):
        return f"[{self.rule}/{self.severity}] {self.where}: {self.detail}"


def _strip_quotes(text: str) -> str:
    """대사를 지운다. 서술만 남겨서 검사한다."""
    return _QUOTED.sub(" ", text)


def _sentences(text: str) -> list:
    return [s.strip() for s in _SENT.findall(text) if s.strip()]


# ---------------------------------------------------------------- 개별 검사

def check_turn_format(scene, novel) -> list:
    """V001 -- Actor 턴의 형식. 파싱이 깨진 것을 문학적 판단에 넘기지 않는다."""
    out = []
    from .state import AXES, BIPOLAR
    for i, t in enumerate(scene.turns):
        w = f"턴 {i}({t.actor})"
        if t.actor not in [c.name for c in novel.characters]:
            out.append(Violation("V001", "hard", w, f"등장인물 목록에 없는 화자: {t.actor!r}"))
        if not (t.speech or t.action or t.inner_thought):
            out.append(Violation("V001", "hard", w, "speech/action/inner_thought 가 모두 비었다"))
        for a in AXES:
            if a not in t.emotions:
                out.append(Violation("V001", "hard", w, f"감정 축 '{a}' 누락"))
                continue
            v = t.emotions[a]
            lo = -100 if a in BIPOLAR else 0
            if not isinstance(v, int) or not (lo <= v <= 100):
                out.append(Violation("V001", "hard", w,
                                     f"'{a}'={v!r} 가 범위 [{lo},100] 밖이거나 정수가 아니다"))
    return out


def check_emotion_continuity(scene, novel) -> list:
    """V002 -- 턴당 감정 급변. 인물이 한 턴 만에 다른 사람이 되는 것을 막는다."""
    out = []
    from .state import AXES
    last = {}
    for i, t in enumerate(scene.turns):
        prev = last.get(t.actor)
        if prev:
            for a in AXES:
                if a in prev and a in t.emotions:
                    d = abs(t.emotions[a] - prev[a])
                    if d > MAX_EMOTION_DELTA:
                        out.append(Violation(
                            "V002", "hard", f"턴 {i}({t.actor})",
                            f"'{a}' 가 한 턴에 {prev[a]} -> {t.emotions[a]} ({d} 변화, "
                            f"상한 {MAX_EMOTION_DELTA}). 중간 단계를 거치게 하라"))
        last[t.actor] = dict(t.emotions)
    return out


def check_emotion_range(scene, novel) -> list:
    """V003 -- 감정 폭 붕괴. **이 관문이 미도리를 지키는 것이다.**

    원 설계는 '지나치게 쾌활하면 롤백' 이라는 단측 압력만 걸었다. 밝은 쪽 이탈만 벌하고
    어두운 쪽은 안 벌하면 수십 턴 뒤 전체가 균일한 우울로 수렴한다 -- 압축에서 3진 양자화로
    굴러떨어진 것과 같은 퇴화다. 그리고 미도리는 진짜로 웃긴 인물이라, 밝음을 벌하는 관문은
    소설의 절반을 삭제한다. 그래서 수준이 아니라 **폭**을 본다."""
    out = []
    from .state import AXES
    if len(scene.turns) < 2:
        return out

    for name in {t.actor for t in scene.turns}:
        mine = [t.emotions for t in scene.turns if t.actor == name]
        # 턴이 하나뿐인 인물은 변동 폭이 0 일 수밖에 없다. 여기서 걸면 정상 씬을 흔든다 --
        # 과잉 기각이 되는 자리라 최소 두 턴을 요구한다.
        span = max((max(e.get(a, 0) for e in mine) - min(e.get(a, 0) for e in mine))
                   for a in AXES) if len(mine) >= 2 else None
        if span is not None and span < RANGE_COLLAPSE:
            out.append(Violation("V003", "soft", f"인물 {name}",
                                 f"씬 내내 감정이 거의 고정이다 (최대 변동 폭 {span}). "
                                 f"인물이 반응하지 않고 있다"))
        try:
            env = novel.character(name).emotion_envelope
        except KeyError:
            continue
        for a, floor in (env or {}).items():
            peak = max(e.get(a, 0) for e in mine)
            if peak < floor:
                out.append(Violation(
                    "V003", "hard", f"인물 {name}",
                    f"'{a}' 가 씬 안에서 한 번도 {floor} 에 닿지 않았다 (최고 {peak}). "
                    f"이 인물은 그 폭을 잃으면 다른 사람이 된다"))
    return out


def check_pov(scene, novel) -> list:
    """V004 -- 시점 위반. 1인칭 회고 화자는 타인의 내면을 사실로 서술할 수 없다.

    '나는 그녀가 ~라고 생각했다' 는 화자의 추측이므로 허용된다. 문장에 화자 표지가 있으면
    통과시키는 이유다 -- 이 구별을 못 하면 정당한 문장을 기각한다."""
    out = []
    if not scene.prose:
        return out
    others = [c.name for c in novel.characters if c.name != novel.pov_character]
    for s in _sentences(_strip_quotes(scene.prose)):
        if not any(v in s for v in INTERIORITY):
            continue
        if _NARRATOR.search(s):
            continue                                  # 화자의 추측 -- 정당하다
        hit = next((n for n in others if re.search(rf"{re.escape(n)}(은|는|이|가)", s)), None)
        if hit:
            out.append(Violation("V004", "hard", f"'{s[:40]}...'",
                                 f"{hit} 의 내면을 사실로 단정했다. 화자의 관찰·추측으로 "
                                 f"바꿔라 (예: '~한 기척이 느껴졌다')"))
        elif re.search(r"(그녀|그)(은|는|이|가)", s):
            out.append(Violation("V004", "soft", f"'{s[:40]}...'",
                                 "대명사 주어의 내면 서술로 보인다. 화자 시점인지 확인하라"))
    return out


def check_direct_emotion(scene, novel) -> list:
    """V005 -- 감정 직접 서술. 푼크툼을 강제하는 관문이다.

    대사는 검사하지 않는다. 인물은 '외로워' 라고 말할 수 있다 -- 금지되는 것은 서술이다.
    한 번은 soft, 그 이상은 hard 로 둔다. 절대 0 을 요구하면 과잉 기각이 된다."""
    if not scene.prose:
        return []
    narration = _strip_quotes(scene.prose)
    hits = [w for w in DIRECT_EMOTION if w in narration]
    if not hits:
        return []
    sev = "soft" if len(hits) <= DIRECT_EMOTION_SOFT else "hard"
    return [Violation("V005", sev, "서술부",
                      f"감정을 직접 서술했다: {hits}. 사물·소리·날씨로 치환하라 "
                      f"(푼크툼: {scene.punctum!r})")]


def check_punctum(scene, novel) -> list:
    """V006 -- Director 가 심은 푼크툼이 산문에 실제로 나타났는가. 지시가 유실되는 것을 막는다."""
    if not scene.prose or not scene.punctum:
        return []
    key = [w for w in re.split(r"[\s,·]+", scene.punctum) if len(w) >= 2]
    if key and not any(k[:2] in scene.prose for k in key):
        return [Violation("V006", "soft", "서술부",
                          f"푼크툼 {scene.punctum!r} 의 흔적이 산문에 없다")]
    return []


def check_pov_presence(scene, novel) -> list:
    """V007 -- 화자가 없는 씬. 1인칭 회고는 이것을 직접 서술할 수 없다.

    원 설계에 이 구멍이 있었다. Actor 들이 자율 상호작용하면 화자가 없는 씬이 필연적으로
    생기는데, 그것을 1인칭으로 쓸 방법이 없다. 해답은 문서가 이미 갖고 있었다 -- 편지 모드다.
    원작이 나오코의 요양원을 편지와 레이코의 입을 통해 전달하는 것과 같다."""
    if novel.pov_character in scene.participants:
        return []
    if scene.mode in ("letter", "reported"):
        return []
    return [Violation("V007", "hard", f"씬 {scene.id}",
                      f"화자 '{novel.pov_character}' 가 참여하지 않는데 mode 가 "
                      f"'{scene.mode}' 다. letter 또는 reported 로 세탁하라")]


def check_knowledge(scene, novel) -> list:
    """V008 -- 지식 누출. 인물이 자기가 모르는 것을 말한다."""
    out = []
    secrets = novel.facts.get("secrets", {})       # {용어: [아는 인물...]}
    for i, t in enumerate(scene.turns):
        text = f"{t.speech} {t.action}"
        for term, holders in secrets.items():
            if term in text and t.actor not in holders:
                out.append(Violation("V008", "hard", f"턴 {i}({t.actor})",
                                     f"'{term}' 을 말했지만 이 인물은 그것을 모른다 "
                                     f"(아는 인물: {holders})"))
    return out


CHECKS = (check_turn_format, check_emotion_continuity, check_emotion_range,
          check_pov, check_direct_emotion, check_punctum,
          check_pov_presence, check_knowledge)


def check(scene, novel) -> list:
    """전체 관문. 위반 목록을 돌려준다. 빈 목록이면 통과."""
    out = []
    for fn in CHECKS:
        out.extend(fn(scene, novel))
    return out


def verdict(violations) -> tuple:
    """(통과 여부, 요약). hard 가 하나라도 있으면 기각한다."""
    hard = [v for v in violations if v.severity == "hard"]
    soft = [v for v in violations if v.severity == "soft"]
    if hard:
        return False, f"하드 위반 {len(hard)}건 (참고 soft {len(soft)}건):\n" + \
                      "\n".join(f"  {v}" for v in hard + soft)
    if soft:
        return True, f"통과 -- 다만 soft {len(soft)}건:\n" + \
                     "\n".join(f"  {v}" for v in soft)
    return True, "통과 -- 위반 없음"
