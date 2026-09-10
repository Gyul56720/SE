def solve(inputs):
    workflow = [
        "Step 1 (Ingestion): orchestrator를 통한 신규 논문 파싱 및 메타데이터 추출",
        "Step 2 (Formalization): law 도구를 활용한 논문 내 정의 및 공리적 규칙의 형식화",
        "Step 3 (Self-Correction): mathdrift 루프를 통한 논문 내 수식 및 추론 체인의 자가 검증",
        "Step 4 (Integration): 최종 지식 베이스(KB) 임베딩 및 인덱싱"
    ]
    prev_limitations = inputs.get("analysis_1", {}).get("limitations", [])
    integration_note = f"상기 워크플로우는 분석 1의 한계 영역({len(prev_limitations)}개)을 우회하기 위해 외부 심볼릭 솔버 연동 단계를 포함합니다."
    return {"workflow": workflow, "integration_note": integration_note}

def check(output, inputs):
    if not isinstance(output, dict) or "workflow" not in output or "integration_note" not in output:
        return False, "필수 키가 누락되었습니다."
    if len(output["workflow"]) < 4:
        return False, "워크플로우 단계가 부족합니다."
    return True, "워크플로우가 성공적으로 제안되었습니다."
