import json
import os
from collections import Counter

def solve(inputs):
    ledger_path = '/mathdrift/ledger.json'
    if not os.path.exists(ledger_path):
        # Fallback for testing environment if file doesn't exist
        return {
            "total_records": 0,
            "success_count": 0,
            "failure_count": 0,
            "top_success_ops": [],
            "evolution_summary": "No data found",
            "failure_bottlenecks": []
        }
    
    with open(ledger_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    records = data if isinstance(data, list) else data.get('records', [])
    
    success_records = [r for r in records if r.get('status') == 'success' or r.get('success') == True]
    failure_records = [r for r in records if r.get('status') == 'failure' or r.get('success') == False]
    
    # 1. Success pattern & ops combinations
    op_counter = Counter()
    for r in success_records:
        ops = r.get('ops', [])
        if isinstance(ops, list):
            op_tuple = tuple(sorted(ops))
            op_counter[op_tuple] += 1
        elif isinstance(ops, str):
            op_counter[ops] += 1
            
    top_success_ops = [[str(k), v] for k, v in op_counter.most_common(5)]
    
    # 2. Evolution stage / complexity over time
    # Assuming records are ordered chronologically or have a timestamp/index
    evolution_steps = []
    for idx, r in enumerate(records):
        complexity = r.get('complexity', len(r.get('ops', [])))
        evolution_steps.append({'index': idx, 'complexity': complexity, 'success': r.get('success', False)})
        
    # 3. Failure bottlenecks
    fail_reason_counter = Counter()
    for r in failure_records:
        reason = r.get('reason', r.get('error', 'unknown'))
        fail_reason_counter[reason] += 1
        
    failure_bottlenecks = [[str(k), v] for k, v in fail_reason_counter.most_common(5)]
    
    report = {
        "total_records": len(records),
        "success_count": len(success_records),
        "failure_count": len(failure_records),
        "top_success_ops": top_success_ops,
        "evolution_summary": f"Analyzed {len(records)} chronological entries.",
        "failure_bottlenecks": failure_bottlenecks
    }
    return report