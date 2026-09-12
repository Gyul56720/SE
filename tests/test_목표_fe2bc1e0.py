import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_goal_fe2bc1e0():
    assert os.path.exists("tests/test_목표_fe2bc1e0.py"), "검사 파일 존재해야 함"
    import plan
    assert os.path.exists("plan/할일.py"), "plan/할일.py 존재해야 함"
    assert os.path.exists("plan/할일.jsonl"), "plan/할일.jsonl 존재해야 함"
    assert os.path.exists("improve/ledger.jsonl") or os.path.exists("repair/ledger.jsonl"), "개선/수리 원장 존재"

if __name__ == '__main__':
    test_goal_fe2bc1e0()
    print("SUCCESS: test_목표_fe2bc1e0 passed")
