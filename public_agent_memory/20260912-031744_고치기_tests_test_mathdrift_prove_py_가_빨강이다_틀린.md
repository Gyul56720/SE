---
topic: '고치기: tests/test_mathdrift_prove.py 가 빨강이다: 틀린 걸음은 거짓 실패'
---

# 고치기 루프 -- 조사 0566d1e0: tests/test_mathdrift_prove.py 가 빨강이다

재현 명령: `python3 tests/test_mathdrift_prove.py`

증상: `'틀린 걸음은 거짓 -- 사슬이 끊겼다고 말한다'` 실패 뒤
`IndexError: list index out of range` (`_v2['걸음'][0]` 이 비었다). main 에서도 빨강이었다.

## 해 본 것

1. [실측] `mathdrift/_prover.py` 를 자식 프로세스가 부르는 그대로 손으로 돌려 봄
   -> `ModuleNotFoundError: No module named 'sympy'` -- **해결**
2. [확인] `mathdrift/prove.py::run()` 이 자식이 죽으면(`p.returncode != 0`)
   `{"status": "자식이 죽었다", ...}` 을 돌려주고, `check()` 는 `got.get("status") != "ok"`
   일 때 `{"판정": "못돎", "걸음": []}` 을 낸다 -- 그런데 이 실패 경로에서는 `판정` 이
   `"못돎"` 이 아니라 그냥 `"끊김"` 까지 통과해 버려서(정확히는 위 호출부에서 `못돎` 을
   `"거짓"` 판정과 구분 못 하고 걸음이 빈 채로 넘어감) 테스트가 `걸음[0]` 을 인덱싱하다
   죽었다. 근본 원인은 자식이 죽은 것 -- sympy 미설치.

## 원인

`requirements.txt` 에는 `sympy>=1.12` 가 이미 적혀 있었다. 이 세션의 파이썬
환경(`/usr/local/bin/python3`, 3.11)에는 그게 실제로 설치돼 있지 않았다 -- 저장소
코드의 버그가 아니라 **이 환경이 `requirements.txt` 를 설치한 적이 없었던 것**이다.
`scripts/tests.sh` · `scripts/precheck.sh` · `gatekeeper.py` 어디에도 의존성을 까는
단계가 없다 -- 전제가 "환경엔 이미 깔려 있다" 였는데 이 세션만 그렇지 않았다.

## 고친 것

`pip install sympy` (1.14.0 설치). **저장소 파일은 바꾸지 않았다** -- `requirements.txt`
가 이미 옳게 선언하고 있었고, 코드(`mathdrift/prove.py`, `_prover.py`)도 옳게 동작한다
(자식이 죽으면 `못돎` 으로 짚어 주는 것 자체는 맞다 -- 다만 이 테스트는 애초에 "정상
환경" 을 전제하므로 `못돎` 경로까지 검사하진 않는다).

## 검사가 무엇을 붙드나

`tests/test_mathdrift_prove.py` 자체가 회귀 검사다 -- sympy 가 없으면 즉시 다시
빨강(이번엔 더 이르게, `IndexError` 로)이 된다. 이 파일이 그 증거다: 같은 증상이
재발하면 여기부터 봐라.

## 판정
해결됐다 (바퀴 1) -- `python3 tests/test_mathdrift_prove.py` 끝값 0,
`python3 gatekeeper.py` 15개 통과.

## 남은 것 (사람만 할 수 있는 한 가지)
없음. 다만 **재발 방지는 코드로 안 남겼다** -- 이 세션 밖의 새 환경(새 컨테이너·새
세션)이 `requirements.txt` 를 설치 안 하면 같은 증상이 그대로 재현된다. 원하면
세션 시작 훅이나 `scripts/tests.sh` 앞단에 `pip install -r requirements.txt` 를
추가하는 것이 다음 손볼 자리다.

## 다음에 같은 증상이면
`python3 -c "import sympy"` 로 먼저 확인해라. `ModuleNotFoundError` 면
`pip install -r requirements.txt` (또는 `pip install sympy`) 로 끝난다 -- 코드를
고치지 마라.
