import difflib
import subprocess

class RuleConfig:
    RULES = [
        "원칙 0 (최소 변경 및 토큰 최적화): 전체 코드를 다시 작성하지 않고, 변경이 필요한 특정 함수나 코드 블록만 Diff 형식으로 수정한다.",
        "원칙 1 (엄격한 범위 준수): 추상화된 목적 달성에 필요한 최소한의 로직만 구현한다.",
        "원칙 2 (아키텍처 보존): 스켈레톤 코드의 원형을 유지한다.",
        "원칙 3 (단일 책임 수정): 하나의 Diff 블록은 하나의 논리적 단위만 처리한다."
    ]
    
    @classmethod
    def get_system_prompt(cls) -> str:
        return "\n".join(cls.RULES)

class AutoRegressivePatcher:
    def __init__(self, initial_code: str, objective: str, max_iters: int = 5):
        self.current_code = initial_code
        self.objective = objective
        self.max_iters = max_iters

    def _generate_diff(self, feedback: str) -> str:
        prompt = f"""
        {RuleConfig.get_system_prompt()}
        목표: {self.objective}
        현재 코드 상태 반영 및 피드백: {feedback}
        위 조건에 맞춰 원칙 0에 따라 Diff를 생성하라.
        """
        return "@@ -... +... @@\n- old\n+ new"

    def _apply_diff(self, diff_text: str) -> bool:
        return True

    def _evaluate_code(self) -> tuple[bool, str]:
        try:
            local_vars = {}
            exec(self.current_code, {}, local_vars)
            return True, ""
        except Exception as e:
            return False, str(e)

    def run_self_correction_loop(self) -> str:
        feedback = "최초 실행"
        
        for iteration in range(1, self.max_iters + 1):
            diff = self._generate_diff(feedback)
            
            if not self._apply_diff(diff):
                feedback = "Diff 적용 실패: 포맷 오류"
                continue
            
            is_success, error_log = self._evaluate_code()
            
            if is_success:
                return self.current_code
                
            feedback = f"실행 오류 발생:\n{error_log}"
            
        return self.current_code
