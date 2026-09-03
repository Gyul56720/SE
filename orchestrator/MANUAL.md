# orchestrator 운용 매뉴얼 — 검증이란 무엇이고, 어디에 쓰고, 어떻게 생산적으로 만드나

이 문서는 세 질문에 답한다.

1. 여기서 말하는 **검증(verification)** 이 정확히 무엇인가 (정답도 목적도 아니다)
2. 이 파이프라인이 **어떤 문제에 특화**되어 있고 어디에 쓰면 안 되는가
3. **생산성을 높이는 방법** — 프롬프트, 코드, 운용, 그리고 코드 개선 제안

---

## 1. 검증이란 무엇인가

세 가지를 구분해야 한다. 자주 섞인다.

| | 무엇 | 우리가 가지고 있나 |
|---|---|---|
| **정답 (ground truth)** | 답 그 자체 | **없다.** 있으면 풀 필요가 없다 |
| **목적 (goal)** | 자연어로 쓴 "무엇을 원하는가" | 있다. 하지만 채점할 수 없다 |
| **검증 (verification)** | 답이 **만족해야 하는 성질**을 코드로 쓴 것 | 이것이 유일하게 실행 가능한 판정 |

계약은 딱 이것이다:

```python
def check(output: dict, inputs: dict) -> tuple[bool, str]:
    """output 이 정말 맞는지 재계산으로 확인한다. (통과여부, 사유)"""
```

`orchestrator.run_plan` 은 이 함수가 `True` 를 준 노드만 `verified` 로 확정하고 결과를
파일로 남긴다. 거부되면 사유가 `attempts` 에 쌓이고, `solve.drive()` 가 그 사유를 플래너에
되먹여 `solve` 를 다시 쓰게 한다.

### 검증이 성립하는 조건: 비대칭성

**확인이 해결보다 싸야 한다.** 이 비대칭이 없으면 verifier 는 아무것도 아니다.

| 문제 | 푸는 비용 | 확인 비용 | 비대칭 |
|---|---|---|---|
| N 의 소인수분해 | 어렵다 | 곱하기 한 번 | 크다 |
| x² ≡ 16 (mod 91) 의 해 | 인수분해 + CRT | 후보를 제곱해서 mod | 크다 |
| 배열 정렬 | O(n log n) | 한 번 훑기 | 있다 |
| 스케줄링 해 | 어렵다 | 제약 위반 검사 | 있다 (최적성은 별개) |
| "이 문단을 요약하라" | — | **확인 방법이 없다** | 없다 |
| "이름/소속을 추출하라" (라벨 없이) | — | **정답을 모르면 못 채점** | 없다 |

### 검증의 4단계 — 강도

| 단계 | 무엇을 보나 | 예 | 신뢰 |
|---|---|---|---|
| **0. 형태** | 키가 있나, 타입이 맞나 | `"name" in res` | 거의 없음 |
| **1. 자기 재계산** | solve 와 **같은 식**을 다시 계산해 비교 | 아래 실패 사례 | **없음 (순환)** |
| **2. 역연산 / 성질** | 답을 원 문제에 **대입** | `x*x % 91 == 16` | 높다 |
| **3. 독립 기준** | 밖에서 온 채점표 | `verify_scheme()`, 테스트 스위트, 라벨 데이터 | 가장 높다 |

**생산성은 2단계 이상 verifier 를 쓸 수 있느냐로 결정된다.**

### 실패 사례 — 1단계가 어떻게 생겼나 (실측)

`runs/20260902-051943` 은 `verified` 로 끝났다. 그 verifier 는 이렇다:

```python
gamma = output["gamma"]
quantized_sample = np.array(output["quantized_sample"])
np.random.seed(42)
weights = np.random.randn(100, 100)
expected_quantized = np.clip(np.round(weights / gamma), -1, 1)[:5, :5]
if not np.array_equal(quantized_sample, expected_quantized):
    return False, "Quantized sample does not match expected configuration"
```

심판이 `solve` 와 **똑같은 식을 같은 시드로 다시 계산해서 자기 자신과 비교한다.** 통과 안
할 수가 없다. JSON 검사도 키 3개가 비어 있지 않은지만 본다 — 추출이 **맞는지**는 안 본다.

이것이 `G008` 이 자가개선 루프에서 막는 vacuous verify 와 같은 부류다. 차이는 하나:
**orchestrator 의 노드 verifier 는 아무도 감시하지 않는다.**

### 구조적 약점: 플래너가 답과 채점표를 둘 다 쓴다

`planner.PLANNER_SYSTEM` 은 노드마다 `component_code`(solve) 와 `verifier_code`(check) 를
**같은 LLM 이 같은 응답에서** 만들게 한다. 프롬프트가 "독립적으로 검증하라, 그냥 True 반환
금지"라고 못박고 있지만, 그건 요청이지 강제가 아니다. 같은 모델이 같은 가정으로 둘 다 쓰면
가정이 틀렸을 때 둘 다 같이 틀린다.

수리 단계는 안전하다 — `repair_node` 는 `component` 만 덮어쓰고 verifier 는 읽기 전용으로
프롬프트에 넣는다. 문제는 **최초 생성**이다.

---

## 2. 어디에 쓰는가

### 특화 조건 (셋 다 만족할수록 잘 맞는다)

1. **검증 비대칭** — 확인이 해결보다 싸다
2. **분해 가능** — 하위 작업 결과가 JSON 으로 다음 단계에 넘어간다
3. **결정론적** — 같은 입력에 같은 출력 (아니면 수리 루프가 무의미해진다)

### 잘 맞는 분야

| 분야 | 예 | 쓸 수 있는 verifier |
|---|---|---|
| **정수론 / 암호** | 인수분해, 모듈러 방정식, 이산로그, CRT | 대입·곱셈 (2단계) |
| **조합 최적화** | 스케줄링, 배낭, 그래프 컬러링, 라우팅 | 제약 위반 검사 + 목적함수 값 (2단계) |
| **수치 알고리즘** | 행렬/텐서 분해, 선형계, 최소제곱 | 잔차 노름 < ε (2단계) |
| **알고리즘 설계** | "O(n log n) 으로 X 하라" | 브루트포스와 대조 + 시간 예산 (2단계) |
| **코드 변환** | 리팩터링, 스키마 마이그레이션, 파서 생성 | 기존 테스트 스위트 (3단계) |
| **데이터 파이프라인** | 파싱 → 정규화 → 집계 | 스키마 + 합계 불변식 (2~3단계) |
| **시뮬레이션 튜닝** | 파라미터 탐색 | 실측 벤치마크 (3단계) |

### 안 맞는 분야

| 분야 | 왜 |
|---|---|
| 요약 / 번역 / 글쓰기 | 정답이 없다. verifier 가 길이·키워드 검사로 퇴화 |
| 추출 / 분류 (라벨 없이) | 정답을 모르면 채점 불가 — `20260902-051943` 이 이 함정 |
| 취향·디자인 판단 | 판정 기준이 사람 안에 있다 |
| 외부 세계 상태 | 실시간 API, 사람 승인 — 재현되지 않아 수리 루프가 의미 없다 |

**예외:** 라벨 데이터가 있으면 추출/분류도 3단계가 된다. `check` 가 라벨 파일을 읽어
정확도 임계값으로 판정하면 된다. 라벨이 곧 독립 기준이다.

---

## 3. 생산성을 높이는 세 축

### 축 A — verifier 를 밖에서 주입한다 (레버가 가장 크다)

`plan_schema.Node.verifier` 는 그냥 문자열이다: `"파일.py#함수"` (런 디렉토리 기준, `#` 이
없으면 함수 이름은 `check`). `orchestrator._load_callable` 이 그 경로를 그대로 로드한다.
**즉 플래너가 만든 파일이 아니어도 된다.**

#### 방법 1 — 지금 코드 변경 없이 (plan.json 을 고친다)

```bash
RUN=orchestrator/runs/$(date +%Y%m%d-%H%M%S)
mkdir -p $RUN/verifiers
```

독립 심판을 먼저 깐다. 예: 이 저장소의 행렬곱 검증기를 그대로 쓴다
(`verify_scheme(scheme, trials, seed) -> (bool, str)` — 계약이 이미 같은 모양이다).

```python
# $RUN/verifiers/scheme_check.py
import sys
sys.path.insert(0, "/home/ubuntu/SE/mathmetics/matrix_exponent")
import verifier as mv          # LLM 이 쓰지 않은 심판


def check(output, inputs):
    scheme = output.get("scheme")
    if not isinstance(scheme, dict):
        return False, "출력에 scheme(dict) 이 없다"
    ok, msg = mv.verify_scheme(scheme, trials=20, seed=0)
    return ok, msg
```

계획을 세우고, **verifier 필드만 갈아끼운다**:

```bash
python3 -c "
import sys; sys.path.insert(0, 'orchestrator')
import planner, json
run='$RUN'
planner.make_plan('<문제 설명>', run)

p = json.load(open(run + '/plan.json'))
for n in p['nodes']:
    if n['id'] == '<채점할 노드 id>':
        n['verifier'] = 'verifiers/scheme_check.py#check'   # 독립 심판으로 교체
json.dump(p, open(run + '/plan.json','w'), ensure_ascii=False, indent=2)
"
python3 orchestrator/solve.py --resume $RUN
```

이제 플래너가 무엇을 쓰든 채점은 밖에서 한다. `repair_node` 는 verifier 를 절대 안 고치므로
수리 루프도 이 심판을 통과하는 방향으로만 돈다.

#### 방법 2 — API 로 못박기 (코드 변경 제안)

```python
# planner.make_plan(problem, run_dir, verifier_map={"node_id": "verifiers/x.py#check"})
#   - 지정된 노드는 LLM 이 낸 verifier_code 를 무시하고 이 경로를 쓴다
#   - 지정된 노드 id 가 계획에 없으면 계획을 거부하고 재시도(피드백)
```

이게 있으면 "이 문제는 이 심판으로 채점한다"를 호출 시점에 고정할 수 있다.

---

### 축 B — 프롬프트: 문제 기술서를 채점 기준 중심으로 쓴다

플래너에게 목표만 주면 **자기 편한 채점표**를 쓴다. 채점 기준을 문제 안에 넣어야 한다.

#### 나쁜 문제 기술 (실제로 1단계 verifier 를 낳았다)

```
NPU 하드웨어의 가중치를 BitNet b1.58(3진) 방식으로 양자화하고, '이름/소속/주제 추출'
프롬프트에 대해 JSON 결과를 생성하라. 결과가 지정된 JSON 포맷과 일치하지 않거나
유사도가 낮으면, 양자화 임계값(gamma)을 조정하여 다시 수행하고 성공할 때까지 반복하라.
```

채점 기준이 "포맷 일치"와 "유사도"뿐이다. 둘 다 코드로 재계산할 대상이 없다.

#### 좋은 문제 기술 템플릿

```
[목표]     무엇을 구하는가. 출력 dict 의 키와 타입까지 명시.
[입력]     주어진 값 / 읽을 파일 경로.
[정답 조건] 답이 만족해야 하는 성질을, solve 를 다시 돌리지 않고 확인 가능한 형태로.
[검증 금지] verifier 가 써서는 안 되는 것 (solve 와 같은 공식·같은 시드 재사용 금지).
[규모]     시간 예산(기본 60초) 안에 끝나야 하는 입력 크기.
```

#### 같은 문제, 고쳐 쓴 것

```
[목표] N=91 에서 x^2 ≡ 16 (mod 91) 의 모든 해를 구하라.
       출력: {"solutions": [int, ...]} — 오름차순, 0 <= x < 91.
[정답 조건]
  1. 모든 x 에 대해 (x*x) % 91 == 16 이어야 한다.
  2. 빠진 해가 없어야 한다: range(91) 전수로 세어 개수가 일치해야 한다.
[검증 금지] verifier 는 인수분해나 CRT 를 쓰지 마라. 대입과 전수 확인만 써라.
[규모] N < 10^4 이므로 전수 확인은 예산 안에 끝난다.
```

이렇게 쓰면 verifier 가 자동으로 2단계가 된다 — 푸는 방법(인수분해+CRT)과 채점 방법
(대입+전수)이 **다른 알고리즘**이 되기 때문이다. 이것이 핵심 요령이다:

> **verifier 가 solve 와 다른 경로로 답에 도달하게 만들어라.**

#### 프롬프트에 넣으면 좋은 문장들 (그대로 복사해서 써라)

```
- verifier 는 solve 의 계산을 재사용하지 말고, 답을 원 문제에 대입해서 확인하라.
- verifier 안에서 난수 시드를 solve 와 동일하게 고정해 결과를 재생성하는 방식은 금지한다.
- verifier 는 출력이 틀렸을 때 반드시 False 를 내야 한다. 형태 검사만 하지 마라.
- 작은 입력에 대해서는 전수(브루트포스) 결과와 대조하라.
- 각 노드의 solve 결과는 JSON 으로 왕복하므로 dict 의 정수 키는 문자열로 돌아온다.
```

마지막 줄은 `planner.JSON_CONTRACT` 가 이미 넣고 있다 — `runs/20260829-224043` 이 그것
때문에 죽었기 때문이다(dict 키 `7` → `"7"`, `KeyError`).

---

### 축 C — 운용

#### 디스코드 (admin 채널)

| 도구 | 쓰는 때 |
|---|---|
| `orchestrator_solve(problem)` | 새 런. 위 템플릿으로 쓴 문제를 통째로 넣는다 |
| `orchestrator_status(run)` | 노드별 상태·마지막 실패 사유·최종 결과 |
| `orchestrator_resume(run)` | 미완인데 프로세스가 없을 때 (배포 재시작 등) |
| `orchestrator_stop(run)` | 엉뚱한 방향으로 도는 런 중지 |

#### VM / 셸

```bash
# 새 런
python3 orchestrator/solve.py "<문제>"

# 노드 예산을 늘린다 (무거운 수치 계산)
python3 orchestrator/solve.py "<문제>" --node-timeout 300

# 수리를 더 끈질기게
python3 orchestrator/solve.py --resume <런> --max-repair-rounds 5 --max-node-repairs 3

# 예산 자체를 환경변수로
ORCH_NODE_TIMEOUT=300 python3 orchestrator/solve.py "<문제>"
```

#### 언제 무엇을 만지나

| 증상 | 원인 | 손댈 곳 |
|---|---|---|
| `planning_failed` | 키 없음 / 쿼터 소진 / JSON 파싱 실패 | 로그 확인. 문제 기술이 너무 길면 줄여라(코드가 JSON 안에 이스케이프돼 들어가서 길수록 깨진다) |
| `invalid_plan` | 사이클·미정의 의존·final 부재 | 문제를 더 작게 쪼개서 다시 |
| 같은 노드가 계속 `failed` | 수리가 안 먹힌다 | `attempts` 를 읽어라. 사유가 매번 다르면 문제 기술이 모호한 것 |
| 예산 초과 반복 | 알고리즘이 지수 시간 | `--node-timeout` 을 늘리기 전에 `[규모]` 를 문제에 명시 |
| `verified` 인데 답이 이상하다 | **1단계 verifier** | 축 A 로 심판을 교체하라. 이게 가장 위험한 실패다 |

마지막 줄이 중요하다. **틀린 답보다 나쁜 것은 통과한 틀린 답이다.**

#### 성공한 런은 자산이다

런 디렉토리는 git 에 남는다. `components/*.py` 는 검증을 통과한 코드다. 같은 부류의 문제를
다시 풀 때 그 파일을 verifier 로 재사용하면 3단계 심판이 하나 늘어난다.

---

## 4. 코드 개선 제안 (구현 대기)

### 제안 1 — 심판 건전성 카나리 (실측으로 범위를 확인했다)

`G008` 이 자가개선 루프에서 하는 일을 orchestrator 노드에 적용한다. **verified 로 확정하기
전에 출력을 일부러 망가뜨려서 verifier 가 거부하는지 본다.** 거부 못 하면 그 심판은 채점을
하지 않는 것이다.

```python
# orchestrator.py 에 추가할 것 (제안)
def _judge_is_alive(check, output, inputs) -> tuple[bool, str]:
    """verifier 가 망가진 출력을 실제로 거부하는가. 형태만 보는 심판(0단계)을 잡는다."""
    import copy
    for key, val in output.items():
        broken = copy.deepcopy(output)
        if isinstance(val, bool):
            broken[key] = not val
        elif isinstance(val, (int, float)):
            broken[key] = val + 1
        elif isinstance(val, str):
            broken[key] = val + "_MUTATED"
        elif isinstance(val, list) and val:
            broken[key] = val[:-1]
        elif isinstance(val, dict) and val:
            broken[key] = {}
        else:
            continue
        try:
            ok, _ = check(broken, inputs)
        except Exception:
            continue                       # 예외로 죽는 것도 거부로 친다
        if ok:
            return False, (f"verifier 가 '{key}' 를 망가뜨려도 통과시킨다 "
                           f"-- 이 심판은 채점하지 않는다")
    return True, ""
```

`run_plan` 에서 `verify(...)` 가 True 를 준 직후에 걸고, 실패하면 `attempts` 에 사유를 남기고
`failed` 로 둔다. 그러면 피드백 루프가 **심판이 헛돈다는 사실 자체**를 플래너에 되먹인다.

#### 무엇을 잡고 무엇을 못 잡는가 (실제로 돌려봤다)

| 심판 | 카나리 판정 |
|---|---|
| 0단계 — `"solutions" in output` 만 확인 | **잡는다** (`'solutions' 를 망가뜨려도 통과한다`) |
| 2단계 — `runs/20260829-224043` 의 CRT 심판 (대입 확인) | 통과 (정상) |
| 1단계 — `runs/20260902-051943` 의 BitNet 심판 (자기 재계산) | **통과해버린다 — 못 잡는다** |

세 번째 줄이 중요하다. 자기 재계산 심판은 `gamma` 를 망가뜨리면 기대값도 같이 바뀌어
불일치가 나고, `quantized_sample` 을 망가뜨려도 불일치가 나고, `result_json` 을 망가뜨리면
JSON 파싱이 터진다. **모든 변형을 정확히 거부한다.** 그런데도 채점은 하지 않는다 — 심판이
`solve` 와 같은 공식을 쓰기 때문에 `solve` 가 그 공식을 구현하기만 하면 그 공식이 옳은지와
무관하게 항상 통과한다.

**결론:** 카나리는 값싼 0단계 필터다. 순환 심판(1단계)은 출력 변형으로 검출되지 않는다 --
심판과 해답이 **같은 가정을 공유**하는 것이 문제이고, 그건 출력만 봐서는 보이지 않는다.
자동 검출을 더 밀어붙이는 것보다 **축 A(밖에서 심판을 주입)** 가 확실하다. 카나리는 그
위에 얹는 싼 안전망으로 쓴다.

승격하려면 `self_challenge.py prove` 로 red-green 을 받아야 한다. RED 는 위 표의 0단계
심판으로, GREEN 은 `runs/20260829-224043` 으로 만들면 된다.

### 제안 2 — `verifier_map` 주입 API

축 A 방법 2. `make_plan` / `replan` 에 지정 노드의 verifier 경로를 고정한다.

### 제안 3 — 자가개선 루프와 연결

`runs/strategy_switch`, `runs/test_math_strategy`, `runs/approx_strategy_switch` 는
계획만 있고 **한 번도 실행되지 않았다.** 탐색이 정체됐을 때 orchestrator 에 전략 전환을
시키려던 흔적이다. `mathmetics/matrix_exponent/verifier.py` 를 노드 심판으로 물리면
(축 A) 그 루프가 닫힌다:

```
탐색 정체 -> orchestrator 가 새 전략 DAG 를 세운다 -> 벤치마크가 판정한다
          -> 실패하면 사유를 되먹여 수리 -> 통과한 스킴만 채택
```

심판이 LLM 밖에 있으므로 이건 1단계 함정에 빠지지 않는다.

---

## 5. 한 장 요약

- **검증은 정답이 아니다.** 답이 만족해야 하는 성질을 코드로 쓴 것이고, 확인이 해결보다
  쌀 때만 성립한다.
- **verifier 가 solve 와 다른 경로로 답에 도달하게 만들어라.** 이것이 유일한 요령이다.
- 지금 가장 큰 약점은 **플래너가 답과 채점표를 둘 다 쓴다**는 것. 밖에서 심판을 주입하면
  사라진다 (`Node.verifier` 는 그냥 경로 문자열이라 지금도 가능하다). 자동 검출로는 못
  메운다 -- 순환 심판은 출력을 아무리 망가뜨려도 정확히 거부하기 때문이다(실측).
- **잘 맞는 것**: 정수론, 조합 최적화, 수치 알고리즘, 코드 변환, 데이터 파이프라인.
- **안 맞는 것**: 요약·번역·취향 판단, 라벨 없는 추출/분류.
- **통과한 틀린 답이 틀린 답보다 나쁘다.** `verified` 를 봤을 때 verifier 부터 읽어라.
