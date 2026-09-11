"""router/call -- 역할이 모델을 고른다. novel 의 분업을 표로 빼서 어디서든 쓰게 한다.

CLAUDE.md 의 분업(디렉터만 Claude, 산문은 Gemini)은 novel/ 안에 박혀 있었다. 같은
판단이 필요한 다른 자리(jaso · coin · orchestrator ...)마다 다시 짜면 두 벌이 갈라
진다. 그래서 **역할표 하나로 뺀다** -- 무엇을 쓸 것인가를 정하는 드문 호출만 비싼
모델로, 토큰의 대부분은 Gemini 풀로, 판정은 모델이 아니라 코드로.

| 역할 | 바탕 | 왜 |
|---|---|---|
| 디렉터 | claude -> gemini 강등 | 호출 적고 출력 짧다. 무엇을 할 것인가가 여기서 갈린다 |
| 배우·화자 | gemini 풀 | 토큰의 대부분. 도는 것이 곧 품질이다 |
| 추출기 | gemini 풀 (gemma 먼저) | 계열이 달라 산문의 분당 한도를 안 깎는다 |
| 판정기 | **모델 없음 -- 거절** | 판정은 코드가 한다(exit code · verify · gates) |

호출층은 새로 만들지 않는다:
  · Gemini 는 **orchestrator/llm_pool.call** 그대로 -- 쿼터·RPM·명부·전적 전부 그 층이 진다.
  · Claude 는 **novel/drive.claude_code_llm** 그대로 -- 구독 청구, 키 안 물려주기 포함.
  · 강등·탐침 수학은 novel/overnight.Director 에서 일반화했다: 3연속 실패면 Gemini 로
    내리고, 짧은 탐침 한 번으로 복귀하며, 실패하면 간격을 두 배로(밤을 타임아웃으로
    안 먹는다).

**호출마다 비용 원장(router/ledger.jsonl)에 남긴다**: 역할 · 바탕 · 라벨(실제 모델) ·
걸린초 · 프롬프트/답 글자수 · 성공 여부. 채택표시() 로 "그 답이 실제로 채택됐는가" 를
이어 적으면, eval 이 "비싼 모델이 실제로 더 채택되는가" 를 잰다(router/check.py).

쓰기:
    from router import call as R
    r = R.부르기("디렉터", "다음 회차의 주제를 한 줄로")   # {"답", "바탕", "라벨", "id", ...}
    R.채택표시(r["id"], True)                              # 채택했으면 이어 적는다
    python3 router/call.py --표                            # 역할표 (호출 0회)
    python3 router/call.py --요약                          # 원장 요약 (호출 0회)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
원장상대 = "router/ledger.jsonl"

# 닫힌 역할표. 여기 없는 역할은 거절한다 -- 표가 열리면 표를 검사할 것이 없어진다.
역할들 = {
    "디렉터": {"바탕": "claude", "물러설곳": "gemini", "prefer": "",
             "왜": "호출 6회 중 1회, 출력 300토큰 남짓 -- 무엇을 쓸 것인가가 전부 여기서 갈린다"},
    "배우":   {"바탕": "gemini", "prefer": "",
             "왜": "토큰의 대부분. 도는 것이 곧 품질이다"},
    "화자":   {"바탕": "gemini", "prefer": "",
             "왜": "배우와 같다 -- 양이 많은 산문"},
    "추출기": {"바탕": "gemini", "prefer": "gemma",
             "왜": "gemma 는 계열이 달라 산문(flash)의 분당 한도를 안 깎는다"},
    "판정기": {"바탕": "코드",
             "왜": "판정은 모델이 아니라 코드가 한다 -- verify.대조 · gates · exit code"},
}

# 강등 매개변수 (novel/overnight.Director 의 실측값 그대로).
강등_연속실패 = int(os.environ.get("ROUTER_FALL_AFTER", "3"))
강등_재시도초 = float(os.environ.get("ROUTER_RETRY_AFTER", "1800"))
강등_재시도상한 = float(os.environ.get("ROUTER_MAX_RETRY", "7200"))
탐침_시간 = float(os.environ.get("ROUTER_PROBE_TIMEOUT", "45"))

# 갈아 끼울 수 있는 호출기. 검사가 여기에 가짜를 꽂는다 -- 기본은 지연 생성.
클로드호출 = None   # (prompt) -> str
지미니호출 = None   # (prompt, prefer, pool_id) -> (str, label)


def _원장(repo=None) -> Path:
    return Path(repo or REPO) / 원장상대


def _클로드기본():
    """novel/drive.claude_code_llm 그대로 -- 구독 청구·키 안 물려주기가 이미 거기 있다."""
    from novel import drive
    return drive.claude_code_llm()


_풀 = None


def _지미니기본(prompt: str, prefer: str, pool_id: str):
    """orchestrator/llm_pool 그대로. 풀은 한 번만 세운다(모델 목록 조회가 API 호출이다)."""
    global _풀
    if _풀 is None:
        from orchestrator import llm_pool
        _풀 = (llm_pool, llm_pool.build_pool())
    mod, pool = _풀
    return mod.call(pool, prompt, pool_id=f"router-{pool_id}", prefer=prefer)


class 강등기:
    """claude 를 쓰되 3연속 실패면 Gemini 로 내리고, 탐침 한 번으로 싸게 복귀한다.
    novel/overnight.Director 의 수학을 역할 무관하게 일반화한 것이다."""

    def __init__(self):
        self.연속실패 = 0
        self.내려간때 = None
        self.재시도초 = 강등_재시도초
        self._주 = None
        self._탐침 = None

    def _준비(self):
        if 클로드호출 is not None:
            return 클로드호출, 클로드호출
        if self._주 is None:
            from novel import drive
            self._주 = drive.claude_code_llm()
            self._탐침 = drive.claude_code_llm(timeout=탐침_시간)
        return self._주, self._탐침

    def 부르기(self, prompt: str, prefer: str, pool_id: str) -> "tuple[str, str, str]":
        """(답, 바탕, 라벨). 바탕: claude · gemini(물러섬) -- 어느 길로 나갔는지 원장에 남는다."""
        주, 탐침 = self._준비()
        if self.내려간때 and time.time() - self.내려간때 > self.재시도초:
            try:
                탐침('JSON 하나만 출력하라. 설명 금지. {"ok": true}')
                self.내려간때, self.연속실패 = None, 0
            except Exception:
                self.재시도초 = min(self.재시도초 * 2, 강등_재시도상한)
                self.내려간때 = time.time()
        if self.내려간때 is None:
            try:
                답 = 주(prompt)
                self.연속실패 = 0
                return 답, "claude", "claude-cli"
            except Exception as e:
                self.연속실패 += 1
                print(f"[router] claude 실패 {self.연속실패}/{강등_연속실패}: "
                      f"{str(e).splitlines()[0][:120]}", file=sys.stderr)
                if self.연속실패 >= 강등_연속실패:
                    self.내려간때 = time.time()
                    print(f"[router] 디렉터를 Gemini 로 내린다 "
                          f"({self.재시도초 / 60:.0f}분 뒤 탐침)", file=sys.stderr)
                else:
                    raise
        답, 라벨 = (지미니호출 or _지미니기본)(prompt, prefer, pool_id)
        return 답, "gemini(물러섬)", 라벨


_강등기 = 강등기()


def _적기(repo, 기록: dict) -> None:
    path = _원장(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(기록, ensure_ascii=False) + "\n")


def 부르기(역할: str, prompt: str, repo=None) -> dict:
    """역할표대로 부르고 비용 원장에 남긴다. {"답", "바탕", "라벨", "걸린초", "id"}."""
    표 = 역할들.get(역할)
    if 표 is None:
        raise ValueError(f"모르는 역할이다: {역할!r} -- 아는 역할: {sorted(역할들)}")
    if 표["바탕"] == "코드":
        raise ValueError("판정기는 모델을 안 부른다 -- 판정은 코드가 한다 "
                         "(graph/verify.대조 · gatekeeper · 도메인 심판의 exit code)")
    기록id = time.strftime("%Y%m%d%H%M%S") + "-" + os.urandom(3).hex()
    시작 = time.monotonic()
    성공, 답, 바탕, 라벨, 오류 = False, "", 표["바탕"], "", ""
    try:
        if 표["바탕"] == "claude":
            답, 바탕, 라벨 = _강등기.부르기(prompt, 표["prefer"], 역할)
        else:
            답, 라벨 = (지미니호출 or _지미니기본)(prompt, 표["prefer"], 역할)
        성공 = True
    except Exception as e:
        오류 = f"{type(e).__name__}: {str(e)[:200]}"
        raise
    finally:
        _적기(repo, {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "id": 기록id, "역할": 역할, "바탕": 바탕, "라벨": 라벨,
                    "걸린초": round(time.monotonic() - 시작, 2), "성공": 성공,
                    "프롬프트글자": len(prompt or ""), "답글자": len(답 or ""),
                    **({"오류": 오류} if 오류 else {})})
    return {"답": 답, "바탕": 바탕, "라벨": 라벨, "id": 기록id,
            "걸린초": round(time.monotonic() - 시작, 2)}


def 채택표시(기록id: str, 채택: bool, repo=None) -> None:
    """부른 답이 실제로 채택됐는가를 이어 적는다 -- eval 이 '비싼 모델이 더 채택되는가' 를
    잴 재료다. 부르는 쪽(verifier 통과 여부 등)이 판정 결과를 그대로 넘긴다."""
    _적기(repo, {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "꼴": "채택", "id": 기록id, "채택": bool(채택)})


def 원장읽기(repo=None) -> "list[dict]":
    path = _원장(repo)
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def 요약(repo=None) -> dict:
    """역할별: 호출 · 성공률 · 평균초 · 바탕 분포 · 채택률(채택표시가 있는 것만)."""
    기록들 = 원장읽기(repo)
    채택 = {r["id"]: r["채택"] for r in 기록들 if r.get("꼴") == "채택"}
    out: dict = {}
    for r in 기록들:
        if r.get("꼴") == "채택" or not r.get("역할"):
            continue
        s = out.setdefault(r["역할"], {"호출": 0, "성공": 0, "초합": 0.0,
                                      "바탕": {}, "채택분모": 0, "채택분자": 0})
        s["호출"] += 1
        s["성공"] += 1 if r.get("성공") else 0
        s["초합"] += float(r.get("걸린초", 0))
        s["바탕"][r.get("바탕", "?")] = s["바탕"].get(r.get("바탕", "?"), 0) + 1
        if r["id"] in 채택:
            s["채택분모"] += 1
            s["채택분자"] += 1 if 채택[r["id"]] else 0
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="역할이 모델을 고른다")
    ap.add_argument("--표", action="store_true", help="역할표를 본다 (호출 0회)")
    ap.add_argument("--요약", action="store_true", help="비용 원장 요약 (호출 0회)")
    args = ap.parse_args()
    if args.표 or not args.요약:
        for 이름, 표 in 역할들.items():
            print(f"  {이름:<4} {표['바탕']:<7} {표.get('prefer') or '-':<6} {표['왜']}")
        if not args.요약:
            return 0
    s = 요약()
    if not s:
        print("원장이 비어 있다 -- 아직 아무도 router 로 안 불렀다")
        return 3
    for 역할, v in s.items():
        채택 = (f" · 채택 {v['채택분자']}/{v['채택분모']}" if v["채택분모"] else "")
        print(f"  {역할:<4} 호출 {v['호출']} · 성공 {v['성공']} · "
              f"평균 {v['초합'] / max(1, v['호출']):.1f}초 · 바탕 {v['바탕']}{채택}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
