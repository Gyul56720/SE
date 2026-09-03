"""씬 루프 -- 기획 → 연기 → 관문 → 수리 → 서술 → 관문.

이 저장소가 배운 것 셋을 그대로 옮겼다:

  · **위반 목록이 곧 수리 프롬프트다.** (bool, str) 로는 고칠 것이 없다. 직선거리 심판이
    "22.5% 더 짧은 점이 있다" 고 짚어줘서 쓸모가 있었던 것과 같다.
  · **씬마다 즉시 저장.** 장편은 며칠 돌고 반드시 중간에 죽는다. verified 씬은 건너뛴다.
  · **scenes.jsonl 에 한 줄씩.** 도는 중에 보이고 죽어도 남는다(solve.py 의 rounds.jsonl).

LLM 은 주입한다. llm(prompt) -> str 하나면 되고, 기본값은 llm_pool 이다. 주입 가능해야
가짜 LLM 으로 루프 자체를 시험할 수 있다 -- test_planner_repair.py 가 쓰는 수다.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from . import gate
from .state import AXES, Turn
from .verbs import catalog_for_prompt

MAX_REPAIRS = 3
# 프롬프트를 캐시 가능한 고정부와 매번 바뀌는 부분으로 가르는 표식. 캐싱은 접두사 일치라
# 이 경계가 있어야 고정부를 통째로 캐시할 수 있다.
SPLIT = "\n<<<VOLATILE>>>\n"


def _llm_for(llm, role: str):
    """llm 이 dict 면 역할별로 고른다. 호출자가 director 만 Claude 로 돌릴 수 있게."""
    if isinstance(llm, dict):
        return llm.get(role) or llm.get("default") or default_llm
    return llm


# ---------------------------------------------------------------- LLM 어댑터

def anthropic_llm(model: str = "claude-opus-5", effort: str = "high"):
    """역할 하나를 Claude 로 돌린다. author(director)에 쓰라고 만든 것이다.

    왜 director 만인가. 실측 프롬프트 기준 director 는 호출 6회 중 1회이고 출력이 300 토큰
    남짓이라 **전체 토큰의 일부**인데, 플롯의 재미는 전부 거기서 갈린다. 100만자 한 편에서
    director 를 Haiku 대신 Opus 로 올리는 비용 차이가 몇 달러다 -- 아낄 자리가 아니다.

    캐싱: 카탈로그·페르소나·규칙은 매 씬 동일하므로 system 으로 올려 캐시한다. 캐시는 접두사
    일치라 **바뀌는 것(씬 씨앗·되먹임)은 반드시 뒤에** 와야 한다. 프리픽스가 1바이트라도
    흔들리면 캐시가 통째로 무효화된다."""
    import anthropic
    client = anthropic.Anthropic()

    def call(prompt: str) -> str:
        stable, _, volatile = prompt.partition(SPLIT)
        r = client.messages.create(
            model=model, max_tokens=16000,
            output_config={"effort": effort},
            system=[{"type": "text", "text": stable,
                     "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": volatile or prompt}])
        if r.stop_reason == "refusal":
            raise RuntimeError(f"거절됨: {r.stop_details}")
        return "".join(b.text for b in r.content if b.type == "text")
    return call


def default_llm(prompt: str) -> str:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "orchestrator"))
    import llm_pool
    pool = llm_pool.build_pool()
    if not pool:
        raise RuntimeError("LLM 후보 풀이 비었다 -- GEMINI_API_KEY 를 설정하라")
    return llm_pool.call(pool, _flatten(prompt), pool_id="novel")[0]


def _flatten(prompt: str) -> str:
    """캐시 경계 표식을 지운다. 캐싱을 안 쓰는 경로(Gemini 등)는 통짜 프롬프트를 받는다."""
    return prompt.replace(SPLIT, "\n")


def _json(text: str) -> dict:
    """코드펜스와 앞뒤 잡소리를 벗기고 JSON 하나를 꺼낸다."""
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < 0:
        raise ValueError(f"JSON 을 찾지 못했다: {text[:120]!r}")
    return json.loads(t[i:j + 1])


# ---------------------------------------------------------------- 프롬프트

def _fb(violations) -> str:
    """관문 위반을 되먹임 문단으로. **이것이 수리의 전부다.**"""
    if not violations:
        return ""
    lines = [f"- {v.rule}: {v.where} -- {v.detail}" for v in violations]
    return ("\n\n[직전 시도가 기각된 이유 -- 같은 실수를 반복하지 마라]\n"
            + "\n".join(lines))


def director_prompt(novel, scene, feedback="") -> str:
    prev = [s for s in novel.scenes if s.status == "verified"][-2:]
    return f"""너는 1인칭 회고 소설의 디렉터다. 다음 씬의 무대와 지시를 정한다.

[화자] {novel.pov_character} (37세 시점의 회고. 결말을 이미 알고 있다)
[인물] {chr(10).join(f'  {c.name}: {c.persona}' for c in novel.characters)}
[화자가 이미 아는 미래] {novel.narrator_foreknowledge}

규칙:
- 감정을 직접 말하게 하지 마라. 사물·소리·날씨로 옮겨라.
- punctum 은 한 씬을 여는 감각 하나다. 나중에 되돌아올 수 있는 것으로.
- 인물이 "슬프다/외롭다" 라고 서술되면 기각된다.

세계 변경이 필요하면 아래 동사만 쓴다(없는 동사는 기각):
{catalog_for_prompt()}
{SPLIT}
[직전까지] {chr(10).join(f'  {s.id}: {s.directives[0] if s.directives else ""}' for s in prev) or '  (시작)'}
[이 씬의 씨앗] {scene.directives[0] if scene.directives else ''}
[참여자] {scene.participants} / [모드] {scene.mode}
{feedback}

JSON 만 출력:
{{"location": "...", "punctum": "...", "directives": ["...", "...", "..."],
  "world_ops": [], "relation_ops": []}}"""


def actor_prompt(novel, scene, name, feedback="") -> str:
    c = novel.character(name)
    log = "\n".join(f"  {t.actor}: {t.speech}" for t in scene.turns[-6:]) or "  (첫 발화)"
    return f"""너는 '{name}' 역할이다.

[페르소나] {c.persona}
[숨긴 것] {c.hidden_agenda}
[네가 아는 것] {c.knows}
[무대] {scene.location} / [감각] {scene.punctum}
[지시] {scene.directives}
[직전 대화]
{log}

규칙:
- 속마음(inner_thought)과 실제 말(speech) 사이에 괴리를 둬라. 담담하게 말하고 속으로 복잡하라.
- 네가 모르는 것은 말할 수 없다. 오해하고 있다면 오해한 채로 말하라.
- 감정은 0~100, narrative_pull 만 -100~100. 한 턴에 35 이상 변하면 기각된다.
{'- 편지 모드다. 대화가 아니라 긴 편지를 써라.' if scene.mode == 'letter' else ''}
{feedback}

JSON 만 출력:
{{"inner_thought": "...", "action": "...", "speech": "...",
  "emotions": {{"joy": 0, "melancholy": 0, "isolation": 0, "narrative_pull": 0}}}}"""


def narrator_prompt(novel, scene, feedback="") -> str:
    logs = "\n".join(
        f"  [{t.actor}] 속:{t.inner_thought} / 행동:{t.action} / 말:{t.speech}"
        for t in scene.turns)
    return f"""수집된 로그를 1인칭 회고 산문으로 직조한다.

[화자] {novel.pov_character} — 반드시 "나는 ~했다" 시점
[무대] {scene.location} / [감각] {scene.punctum}
[로그]
{logs}

규칙:
- 다른 인물의 속마음을 사실로 쓰지 마라. 화자의 관찰과 추측으로 옮겨라
  (예: "그녀의 눈동자 깊은 곳에서 무언가 무너져 내리는 기척이 느껴졌다").
- "슬펐다/외로웠다" 같은 직접 서술 금지. 대사 안에서는 허용된다.
- punctum 을 대화의 공백에 끼워 넣어라.
- 담담하고 건조하게. 신파로 흐르지 마라.
{'- 편지를 읽는 장면으로 감싸고, 편지 내용을 서술에 녹여라.' if scene.mode == 'letter' else ''}
{feedback}

산문만 출력한다. JSON 도 머리말도 쓰지 마라."""


# ---------------------------------------------------------------- 루프

def _record(path, rec):
    if not path:
        return
    try:
        with Path(path).open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def run_scene(novel, scene, llm, max_repairs=MAX_REPAIRS, log=None) -> dict:
    """한 씬을 관문 통과까지 몰아붙인다. 반환 {status, attempts, violations}."""
    t0 = time.time()
    feedback = ""

    for attempt in range(1, max_repairs + 2):
        # --- 기획 (이미 채워져 있으면 건너뛴다: 템플릿이 준 씬)
        if not scene.location:
            d = _json(_llm_for(llm, "director")(director_prompt(novel, scene, feedback)))
            scene.location = d.get("location", "")
            scene.punctum = d.get("punctum", "")
            scene.directives = d.get("directives") or scene.directives
            scene.world_ops = (scene.world_ops or []) + (d.get("world_ops") or [])
            scene.relation_ops = (scene.relation_ops or []) + (d.get("relation_ops") or [])

        # --- 연기
        # **직전 시도의 산문을 반드시 지운다.** 안 지우면 아래 턴 단계 관문이 낡은 산문을
        # 그대로 검사해서, 턴이 멀쩡한데도 이전 산문의 위반으로 계속 기각된다 -- 서술
        # 단계까지 가지 못하니 수리가 영원히 안 된다(회귀 검사 test_novel_drive 가 잡았다).
        scene.prose = ""
        scene.turns = []
        speakers = scene.participants or [novel.pov_character]
        rounds = 1 if scene.mode == "letter" else 2
        for _ in range(rounds):
            for name in speakers:
                a = _json(_llm_for(llm, "actor")(actor_prompt(novel, scene, name, feedback)))
                scene.turns.append(Turn(
                    actor=name, inner_thought=a.get("inner_thought", ""),
                    action=a.get("action", ""), speech=a.get("speech", ""),
                    emotions={k: int(a.get("emotions", {}).get(k, 0)) for k in AXES}))

        # --- 관문 1차 (로그 규칙)
        vs = gate.check(scene, novel)
        hard = [v for v in vs if v.severity == "hard"]
        if hard:
            feedback = _fb(hard)
            scene.attempts.append({"attempt": attempt, "stage": "turns",
                                   "violations": [str(v) for v in hard]})
            continue

        # --- 서술
        scene.prose = _llm_for(llm, "narrator")(
            narrator_prompt(novel, scene, feedback)).strip()

        # --- 관문 2차 (산문 규칙)
        vs = gate.check(scene, novel)
        hard = [v for v in vs if v.severity == "hard"]
        if hard:
            feedback = _fb(hard)
            scene.attempts.append({"attempt": attempt, "stage": "prose",
                                   "violations": [str(v) for v in hard]})
            continue

        scene.status = "verified"
        scene.violations = [str(v) for v in vs]          # soft 는 기록만
        return {"status": "verified", "attempts": attempt, "soft": len(vs),
                "seconds": round(time.time() - t0, 2)}

    scene.status = "failed"
    scene.violations = [str(v) for v in hard]
    return {"status": "failed", "attempts": max_repairs + 1,
            "reason": "관문 위반이 수리 한도 안에 해소되지 않았다",
            "violations": [str(v) for v in hard], "seconds": round(time.time() - t0, 2)}


def drive(novel, path, llm=None, max_repairs=MAX_REPAIRS, log=None, limit=None) -> dict:
    """미완 씬들을 차례로 몰아붙인다. 씬마다 즉시 저장한다."""
    llm = llm or default_llm      # 콜러블 하나 또는 {역할: 콜러블} dict
    log = log or (Path(path).with_suffix(".scenes.jsonl") if path else None)
    _record(log, {"event": "start", "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                  "title": novel.title, "scenes": len(novel.scenes)})

    done, failed = 0, 0
    while True:
        scene = novel.next_pending()
        if scene is None or (limit and done + failed >= limit):
            break
        r = run_scene(novel, scene, llm, max_repairs, log)
        _record(log, {"event": "scene", "id": scene.id, "at": time.strftime("%H:%M:%S"), **r})
        if path:
            novel.save(path)                              # 씬마다 즉시 저장
        if r["status"] == "verified":
            done += 1
        else:
            failed += 1
            break                                         # 막힌 씬을 넘어가지 않는다

    out = {"status": "done" if failed == 0 else "blocked",
           "verified": done, "failed": failed,
           "remaining": sum(1 for s in novel.scenes if s.status != "verified")}
    _record(log, {"event": "end", "at": time.strftime("%Y-%m-%d %H:%M:%S"), **out})
    return out
