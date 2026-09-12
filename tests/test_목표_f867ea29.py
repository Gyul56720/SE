import json
import os
import sys

def test_ledgerstat():
    ledger_path = 'repair/ledger.jsonl'
    if not os.path.exists(ledger_path):
        raise FileNotFoundError(f"{ledger_path}가 없습니다.")
    
    with open(ledger_path, 'r') as f:
        lines = [json.loads(line) for line in f.readlines()]
    
    # 0이 아닐 수도 있는 열쇠들을 확인
    # "귀속" 같은 키가 없다는 것이 문제임
    for entry in lines:
        if '귀속' in entry:
            print("귀속 발견됨")
            return
            
    # 귀속 키가 없는 경우가 문제라면, 
    # 일단 테스트가 귀속 키를 가진 항목을 하나라도 찾을 수 있는지 확인해야 함
    raise AssertionError("어떤 항목에도 '귀속' 열쇠가 없습니다.")

if __name__ == "__main__":
    test_ledgerstat()
