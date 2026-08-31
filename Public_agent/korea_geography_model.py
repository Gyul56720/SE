# 한국 지리적 특징의 알고리즘적 모델링 및 코드 치환

한국의 핵심 지리적 특징인 **'동고서저(East-High, West-Low)', '태백/소백산맥의 북북서-남남동(또는 남북) 축', 그리고 '3면이 바다인 반도성(배수 시스템)'**을 파이썬 행렬 연산과 최단 경사 하강(Steepest Descent) 알고리즘으로 치환하여 모델링하였습니다.

## 1. 알고리즘 설계 원리
1. **지형 행렬 생성 (`elevation` Matrix):** 
   - 서해안(낮음)에서 동해안(높음)으로 향하는 기본 경사 기울기 적용.
   - 동쪽 능선에 태백산맥 봉우리 함수(`np.exp` 기반 가우스 곡선) 및 지형 잡음 합성.
2. **수계 및 하천 유출 시뮬레이션 (`simulate_river_flow`):**
   - 물은 중력에 의해 가장 높은 곳에서 가장 낮은 곳으로 흐름.
   - 동쪽 산맥에서 시작해 주변 8방향 중 경사가 가장 급한 곳을 찾아 서해(한강·금강·영산강 등) 및 남해로 빠져나가는 경로 추적.

## 2. 파이썬 코드 구현

```python
import numpy as np

class KoreaGeographySimulation:
    def __init__(self, grid_size=100):
        self.grid_size = grid_size
        self.elevation = np.zeros((grid_size, grid_size))
        
        # 지리적 특성 치환: 동고서저 + 태백산맥 능선
        for x in range(grid_size):
            for y in range(grid_size):
                # 서쪽(y=0) -> 동쪽(y=99)으로 갈수록 고도 증가 (동고서저)
                base_slope = (y / grid_size) * 1000  
                # 동쪽에 집중된 태백산맥 봉우리 (가우스 분포 활용)
                taebaek_ridge = 1500 * np.exp(-((y - 85) ** 2) / 20)  
                # 한반도 지형의 굴곡을 모사하는 삼각함수 노이즈
                noise = 200 * np.sin(x / 10) * np.cos(y / 10)
                
                self.elevation[x, y] = max(0, base_slope + taebaek_ridge + noise)

    def simulate_river_flow(self):
        # 물길 흐름 알고리즘: 동쪽 산맥에서 발원해 경사를 따라 서해/남해로 유출
        flows = []
        for x in range(10, self.grid_size - 10, 20):
            curr = (x, 85) # 발원지 (동쪽 산맥 부근)
            path = [curr]
            for _ in range(50):
                cx, cy = curr
                if cy <= 0 or cy >= self.grid_size - 1 or cx <= 0 or cx >= self.grid_size - 1:
                    break
                # 주변 8방향 중 가장 고도가 낮은 곳으로 물이 흐름 (Steepest Descent)
                neighbors = [(cx+dx, cy+dy) for dx in [-1,0,1] for dy in [-1,0,1] if not (dx==0 and dy==0)]
                next_pos = min(neighbors, key=lambda p: self.elevation[p[0], p[1]])
                path.append(next_pos)
                curr = next_pos
            flows.append(path)
        return flows

# 시뮬레이션 실행 및 검증
sim = KoreaGeographySimulation(grid_size=100)
river_paths = sim.simulate_river_flow()

print(f"지형 행렬 크기: {sim.elevation.shape}")
print(f"최고 고도 지점: {np.max(sim.elevation):.2f}m")
print(f"최저 고도 지점: {np.min(sim.elevation):.2f}m")
print(f"생성된 주요 하천 유출 경로 수: {len(river_paths)}개")
```
