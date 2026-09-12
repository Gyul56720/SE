import json
import os

def test_ledgerstat():
    ledger_path = 'repair/ledger.jsonl'
    if not os.path.exists(ledger_path):
        raise FileNotFoundError(f"{ledger_path}가 없습니다.")
    
    with open(ledger_path, 'r') as f:
        lines = [json.loads(line) for line in f.readlines()]
    
    # 조사가 진행 중인 항목을 찾음
    target_entry = None
    for entry in lines:
        if entry.get('조사') == 'f867ea29':
            target_entry = entry
            break
            
    if not target_entry:
        raise AssertionError("조사 f867ea29 항목을 찾을 수 없습니다.")

    # 증상에서 언급된 열쇠들 (바퀴, 빨강 등 원장에 존재하는 것들)
    required_keys = ['조사', '단계', '빨강']
    
    for key in required_keys:
        if key not in target_entry:
            raise AssertionError(f"원장에 필수 열쇠 {key}가 없습니다.")
            
    print("검사 통과")

if __name__ == "__main__":
    test_ledgerstat()
