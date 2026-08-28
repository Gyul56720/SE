"""
Diff 기반 자가 수정(self-correction) 루프.

이전 버전은 뼈대만 있고 `_generate_diff`/`_apply_diff`가 각각 빈 문자열/무조건 True를
반환하는 스텁이었다 -- 즉 실제로는 코드가 한 글자도 안 바뀐 채 "성공"을 리턴하는
가짜 루프였다. 이번 버전은 실제로 동작하게 고쳤다.

- diff 적용을 진짜로 한다: unified diff(git diff -u 포맷)를 difflib 기반으로
  파싱해서 순수 파이썬으로 적용한다. 외부 `patch` 바이너리나 셸에 의존하지 않는다.
- diff를 만드는 부분(LLM 호출이든 규칙 기반이든)은 `diff_generator` 콜백으로
  주입받는다 -- 이 파일 자체는 어떤 외부 API도 호출하지 않는 순수 라이브러리다.
- 후보 코드를 이 프로세스 안에서 `exec()`하지 않는다. 먼저 `py_compile`로 문법만
  검사하고, 그다음에는 별도 `python3` 서브프로세스로 실행해서 평가한다 -- 후보
  코드가 루프 자체의 상태나 이 파일을 손상시킬 수 없다.
- 매 반복 실패해도 마지막으로 문법이 맞았던 코드를 다음 반복의 기반으로 쓰고,
  같은 에러가 연속으로 반복되면("stuck") 더 돌려봐야 소용없다고 보고 조기 종료한다.
- `max_iters`는 크게 잡을 수는 있어도 무제한은 아니다(기본 100). 실제로 서브프로세스를
  실행하는 루프에 상한이 없으면 러너웨이 프로세스가 된다 -- 이건 성능이 아니라 안전 문제라
  "조건이 만족될 때까지 무한 반복"으로는 바꾸지 않았다.
- `checkpoint_path`를 주면 매 iteration마다 진행 상태(best_code/iteration/history)를
  JSON으로 저장하고, 다음 실행이 같은 경로를 보면 중단된 지점부터 이어간다. 이게 필요한
  이유: discord_bot_server.py를 self-modify해서 push하면 deploy-oracle.yml의 자동
  재배포가 걸려 서비스가 재시작되는데(실측 확인됨, 2026-08-27), 이 루프는 순수 인메모리
  while문이라 재시작되면 상태가 통째로 날아간다.
- 이 루프를 `run_shell`로 띄울 때는 CLAUDE.md의 백그라운드 실행 규칙(setsid nohup +
  disown)을 그대로 따르고, 가능하면 discord_bot_server.py의 run_claude()가 쓰는
  `systemd-run --scope`로 se-discord-bot.service의 cgroup 밖에 분리해서 실행하라 --
  그래야 재배포로 봇 프로세스가 재시작돼도 진행 중인 루프까지 같이 죽지 않는다.
- `verifier`(옵션): diff_generator가 스스로 "성공"이라고 판단한 걸 그대로 믿지 않고,
  분리된 판단 주체로 한 번 더 검토하는 게이트. evaluator가 성공을 리턴해도 verifier가
  거부하면 채택하지 않고 그 이유를 다음 iteration의 feedback으로 넘긴다.
  `Public_agent/verify.py`의 `verify_candidate`(claude -p 호출, fail-closed)를 기본으로
  쓸 수 있다.
"""

from __future__ import annotations

import difflib
import json
import py_compile
import subprocess
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

# (현재 코드, 직전 피드백) -> unified diff 텍스트
DiffGenerator = Callable[[str, str], str]
# 후보 코드 -> (성공 여부, 피드백)
Evaluator = Callable[[str], "tuple[bool, str]"]
# (objective, diff, eval_feedback) -> (승인 여부, 판단 근거)
Verifier = Callable[[str, str, str], "tuple[bool, str]"]


class RuleConfig:
    RULES = [
        "원칙 0 (최소 변경 및 토큰 최적화): 전체 코드를 다시 작성하지 않고, 변경이 필요한 특정 함수나 코드 블록만 Diff 형식으로 수정한다.",
        "원칙 1 (엄격한 범위 준수): 추상화된 목적 달성에 필요한 최소한의 로직만 구현한다.",
        "원칙 2 (아키텍처 보존): 스켈레톤 코드의 원형을 유지한다.",
        "원칙 3 (단일 책임 수정): 하나의 Diff 블록은 하나의 논리적 단위만 처리한다.",
    ]

    @classmethod
    def get_system_prompt(cls) -> str:
        return "\n".join(cls.RULES)


@dataclass
class IterationRecord:
    iteration: int
    success: bool
    feedback: str
    diff: str


@dataclass
class _Hunk:
    orig_start: int
    orig_len: int
    new_lines: list


def _parse_hunks(diff_text: str) -> list:
    """unified diff의 @@ 헤더들을 파싱한다. `+`/` `로 시작하는 줄만 결과에 남기고
    `-`로 시작하는 줄은 버린다(=삭제)."""
    hunks: list = []
    lines = diff_text.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("@@"):
            parts = line.split("@@")
            if len(parts) < 2:
                raise ValueError(f"깨진 hunk 헤더: {line!r}")
            orig_range = parts[1].strip().split(" ")[0]  # "-start,len" 또는 "-start"
            orig_start_str, _, orig_len_str = orig_range.lstrip("-").partition(",")
            orig_start = int(orig_start_str)
            orig_len = int(orig_len_str) if orig_len_str else 1

            i += 1
            new_lines: list = []
            while i < len(lines) and not lines[i].startswith("@@"):
                body = lines[i]
                if body.startswith("+"):
                    new_lines.append(body[1:])
                elif body.startswith(" "):
                    new_lines.append(body[1:])
                elif body.startswith("-"):
                    pass
                else:
                    new_lines.append(body)
                i += 1
            hunks.append(_Hunk(orig_start=orig_start, orig_len=orig_len, new_lines=new_lines))
        else:
            i += 1
    if not hunks:
        raise ValueError("diff에서 @@ hunk를 하나도 못 찾았다.")
    return hunks


def apply_unified_diff(original: str, diff_text: str) -> str:
    """git diff -u / difflib.unified_diff 형식의 patch를 순수 파이썬으로 적용한다."""
    if not diff_text.strip():
        raise ValueError("빈 diff")

    result_lines = original.splitlines(keepends=True)
    hunks = _parse_hunks(diff_text)

    # 뒤 hunk부터 적용해야 앞 hunk의 라인 번호가 밀리지 않는다.
    for hunk in sorted(hunks, key=lambda h: h.orig_start, reverse=True):
        start = hunk.orig_start - 1
        end = start + hunk.orig_len
        if start < 0 or end > len(result_lines):
            raise ValueError(f"hunk 라인 범위가 원본과 안 맞는다: {hunk.orig_start},{hunk.orig_len}")
        result_lines[start:end] = hunk.new_lines

    return "".join(result_lines)


def make_unified_diff(before: str, after: str, filename: str = "code") -> str:
    """설명/기록용 -- before/after 전체 텍스트가 있을 때 diff 표시를 만든다."""
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
        )
    )


def _check_syntax(code: str) -> "tuple[bool, str]":
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        tmp_path = f.name
    try:
        py_compile.compile(tmp_path, doraise=True)
        return True, ""
    except py_compile.PyCompileError as e:
        return False, str(e)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def default_subprocess_evaluator(timeout: int = 10) -> Evaluator:
    """후보 코드를 별도 `python3` 프로세스로 실행해서 평가한다 -- 이 프로세스 안에서
    `exec()`하지 않으므로 후보 코드가 루프 자체의 상태를 망가뜨릴 수 없다."""

    def _evaluate(candidate_code: str) -> "tuple[bool, str]":
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(candidate_code)
            tmp_path = f.name
        try:
            result = subprocess.run(
                ["python3", tmp_path], capture_output=True, text=True, timeout=timeout,
            )
            if result.returncode == 0:
                return True, ""
            return False, (result.stderr or result.stdout)[-2000:]
        except subprocess.TimeoutExpired:
            return False, f"실행 시간 초과({timeout}초)"
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    return _evaluate


class AutoRegressivePatcher:
    """diff_generator로 패치를 만들고, 문법 검사 -> 서브프로세스 평가 -> 성공 시 채택,
    실패 시 다음 반복의 기반으로 이어가며 반복하는 self-correction 루프."""

    def __init__(
        self,
        initial_code: str,
        objective: str,
        diff_generator: DiffGenerator,
        evaluator: Optional[Evaluator] = None,
        max_iters: int = 100,
        stuck_after: int = 3,
        checkpoint_path: "str | Path | None" = None,
        history_log_path: "str | Path | None" = None,
        verifier: Optional[Verifier] = None,
    ):
        self.objective = objective
        self.diff_generator = diff_generator
        self.evaluator = evaluator or default_subprocess_evaluator()
        # diff_generator를 만든 것과 같은 모델이 "내가 objective를 달성했다"고 스스로
        # 채점하면 자기 확신 편향으로 실패해도 성공이라 우길 수 있다. verifier는 diff_generator와
        # 분리된 판단 주체(예: Public_agent/verify.py의 claude -p 호출)로, evaluator가
        # 성공을 리턴해도 verifier가 거부하면 최종 채택하지 않고 그 사유를 다음 iteration의
        # feedback으로 넘긴다. None이면(기본값) 이 게이트 없이 evaluator 결과만으로 채택한다.
        self.verifier = verifier
        self.max_iters = max_iters
        self.stuck_after = stuck_after
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else None
        # checkpoint_path는 "이어서 돌기 위한" 상태라 성공하면 지운다. 반면 이건 다르다 --
        # 성공/실패와 무관하게 diff와 그게 왜 나왔는지(feedback)를 영구적으로 계속 쌓아서,
        # 나중에 다른 LLM 호출이 "이 코드베이스에서 뭘 시도했다가 왜 실패/성공했는지"를
        # 참고할 수 있게 한다. 체크포인트가 삭제돼도(=한 실행이 끝나도) 이 로그는 안 지운다.
        self.history_log_path = Path(history_log_path) if history_log_path else None

        # discord_bot_server.py를 self-modify한 push는 deploy-oracle.yml의 자동 재배포를
        # 트리거해서 서비스가 재시작된다(실측 확인됨, 2026-08-27) -- 이 루프는 순수 인메모리
        # while문이라 재시작되면 상태가 통째로 날아간다. checkpoint_path가 주어지면 매
        # iteration마다 진행 상태를 JSON으로 남겨서, 다음 실행이 처음부터 다시 돌지 않고
        # 중단된 지점부터 이어가게 한다.
        self.current_code = initial_code
        self.history: list = []
        self._start_iteration = 0
        self._resume_feedback = "최초 실행"
        if self.checkpoint_path and self.checkpoint_path.exists():
            self._load_checkpoint()

    def _load_checkpoint(self) -> None:
        data = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
        if data.get("objective") != self.objective:
            return  # 다른 목표의 체크포인트는 무시하고 처음부터 시작한다.
        self.current_code = data["best_code"]
        self._start_iteration = data["iteration"]
        self._resume_feedback = data["feedback"]
        self.history = [IterationRecord(**rec) for rec in data["history"]]

    def _save_checkpoint(self, best_code: str, iteration: int, feedback: str) -> None:
        if not self.checkpoint_path:
            return
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "objective": self.objective,
            "best_code": best_code,
            "iteration": iteration,
            "feedback": feedback,
            "history": [asdict(rec) for rec in self.history],
        }
        tmp = self.checkpoint_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.checkpoint_path)  # 원자적 교체 -- 쓰는 도중 재시작돼도 파일이 깨지지 않는다.

    def _append_history_log(self, record: IterationRecord) -> None:
        if not self.history_log_path:
            return
        self.history_log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"objective": self.objective, "timestamp": datetime.now(timezone.utc).isoformat(), **asdict(record)}
        with self.history_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _is_stuck(self, recent_feedbacks: list) -> bool:
        tail = recent_feedbacks[-self.stuck_after:]
        return len(tail) == self.stuck_after and len(set(tail)) == 1

    def run_self_correction_loop(self) -> "tuple[str, int]":
        best_code = self.current_code
        feedback = self._resume_feedback
        recent_feedbacks: list = [rec.feedback for rec in self.history[-self.stuck_after:]]

        iteration = self._start_iteration
        while iteration < self.max_iters:
            iteration += 1
            diff = self.diff_generator(best_code, feedback)

            try:
                candidate = apply_unified_diff(best_code, diff)
            except ValueError as e:
                feedback = f"diff 적용 실패: {e}"
                self.history.append(IterationRecord(iteration, False, feedback, diff))
                self._append_history_log(self.history[-1])
                recent_feedbacks.append(feedback)
                self._save_checkpoint(best_code, iteration, feedback)
                if self._is_stuck(recent_feedbacks):
                    break
                continue

            ok, syntax_err = _check_syntax(candidate)
            if not ok:
                feedback = f"문법 오류:\n{syntax_err}"
                self.history.append(IterationRecord(iteration, False, feedback, diff))
                self._append_history_log(self.history[-1])
                recent_feedbacks.append(feedback)
                self._save_checkpoint(best_code, iteration, feedback)
                if self._is_stuck(recent_feedbacks):
                    break
                continue

            is_success, error_log = self.evaluator(candidate)

            if is_success and self.verifier:
                approved, verify_note = self.verifier(self.objective, diff, error_log)
                record = IterationRecord(iteration, approved, f"[verifier] {verify_note}", diff)
                self.history.append(record)
                self._append_history_log(record)
                if approved:
                    if self.checkpoint_path:
                        self.checkpoint_path.unlink(missing_ok=True)
                    return candidate, iteration
                # evaluator는 통과했지만 별도 검증자가 거부함 -- 채택하지 않고 그 이유를
                # 다음 iteration의 feedback으로 넘긴다.
                best_code = candidate
                feedback = f"자동 평가는 통과했지만 검증자가 거부:\n{verify_note}"
                recent_feedbacks.append(feedback)
                self._save_checkpoint(best_code, iteration, feedback)
                if self._is_stuck(recent_feedbacks):
                    break
                continue

            self.history.append(IterationRecord(iteration, is_success, error_log, diff))
            self._append_history_log(self.history[-1])

            if is_success:
                if self.checkpoint_path:
                    self.checkpoint_path.unlink(missing_ok=True)  # 완료됐으니 다음 실행이 이어받지 않게 지운다.
                return candidate, iteration

            best_code = candidate  # 문법은 맞으니 다음 diff의 기반으로 이어간다.
            feedback = f"실행 오류 발생:\n{error_log}"
            recent_feedbacks.append(feedback)
            self._save_checkpoint(best_code, iteration, feedback)
            if self._is_stuck(recent_feedbacks):
                break

        return best_code, iteration
