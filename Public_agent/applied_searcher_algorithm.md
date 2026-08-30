# 최근 applied된 알고리즘 코드 변경 내역

가장 최근 반영된 커밋(`8a79ece`)과 직전 커밋(`1574ce5`)에서 수정된 `mathmetics/matrix_exponent/searcher.py`의 핵심 알고리즘 변경 부위입니다.

## 1. 외삽 가속 및 교란(Perturbation) 파라미터 튜닝 (`8a79ece`)
- **외삽 점증 비율(`alpha`)**: `alpha = min(alpha * 1.05, 1.5)` -> `alpha = min(alpha * 1.08, 1.8)` 로 상향하여 수렴 가속도 강화
- **고착 방지 주기 및 잡음 스케일**:
  ```python
  if it > 0 and it % 300 == 0 and res > 1e-2 and use_perturbation and rng is not None:
      scale = noise_scale * (res + 1e-8)
      U += rng.normal(0, scale, U.shape)
      V += rng.normal(0, scale, V.shape)
      W += rng.normal(0, scale, W.shape)
  ```
  기존 U만 흔들던 것에서 V, W까지 동시 교란하도록 변경하여 국소 최적점 탈출 성능 개선.

## 2. 리프팅(Lifting) 및 감쇠(Damping) 조정
- **라운드별 격자 고정 임계값 (`_lift`)**:
  `thresh = 0.02 * (r + 1) / LIFT_ROUNDS` 방식으로 정밀화
- **ALS 감쇠 (`damp0`)**: 리프팅 후 자유도 수렴 단계에서 감쇠를 `1e-7` -> `1e-8`로 낮춰 수렴 정확도 향상.

---

### 전체 `searcher.py` 원본 보기
현재 저장소의 `mathmetics/matrix_exponent/searcher.py` 파일 전체를 확인하시려면 아래 명령을 실행할 수 있습니다:
```bash
cat mathmetics/matrix_exponent/searcher.py
```
