def solve(inputs):
    data = inputs["analyze_systems"]
    law = data["law"]
    math = data["mathdrift"]
    report = f"# 시스템 아키텍처 분석 리포트\n\n## 1. /law 시스템\n- 역할: {law['role']}\n- 경로: {law['path']}\n- 동작: {law['architecture']}\n\n## 2. /mathdrift 시스템\n- 역할: {math['role']}\n- 경로: {math['path']}\n- 동작: {math['architecture']}\n\n## 3. 상호작용\n/law는 데이터 필터링을 통해 /mathdrift의 학습 효율을 높이며, /mathdrift는 이를 바탕으로 Terrain 스키마를 업데이트함."
    return {"report": report}