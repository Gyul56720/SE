import json

def solve(inputs):
    analysis = inputs.get('issue_analysis', {})
    if isinstance(analysis, str):
        analysis = json.loads(analysis)
    
    strategy = inputs.get('dig_strategy', {})
    if isinstance(strategy, str):
        strategy = json.loads(strategy)
        
    impact = analysis.get('issues', {}).get('impact', 'legal rigidity')
    method = strategy.get('strategy', {}).get('method', 'dynamic retrieval')
    
    report = f"SCAL Integration Report: Addressing {impact} via {method}."
    return {"final_report": report}