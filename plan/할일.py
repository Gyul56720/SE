import json
import os

def 할일(args=None):
    ledger_path = "plan/할일.jsonl"
    if not os.path.exists(ledger_path):
        with open(ledger_path, "w") as f:
            pass
    print("할일 관리 모듈 정상 동작")
    return 0

if __name__ == "__main__":
    할일()
