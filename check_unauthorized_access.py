import os
import subprocess
from datetime import datetime

# 1. 최근 Git 커밋 중 내가 아닌 작성자 확인
def check_git_history():
    print("--- 최근 Git 커밋 기록 (작성자 확인) ---")
    # 마지막 5개 커밋의 작성자 이름과 이메일 출력
    result = subprocess.run(
        ["git", "log", "-n", "5", "--pretty=format:%an <%ae>"],
        capture_output=True, text=True
    )
    print(result.stdout)
    return result.stdout

# 2. 최근 파일 수정 시간 확인 (시스템 파일들이 언제 변경되었는지)
def check_recent_files():
    print("\n--- 최근 수정된 시스템 파일 (최근 1시간) ---")
    result = subprocess.run(
        ["find", ".", "-mmin", "-60", "-not", "-path", "*/.*", "-not", "-name", "*.log", "-not", "-name", "*.txt"],
        capture_output=True, text=True
    )
    print(result.stdout)

# 3. 현재 실행 중인 프로세스 중 의심스러운 파이썬 프로세스 확인
def check_processes():
    print("\n--- 실행 중인 파이썬 프로세스 ---")
    result = subprocess.run(["ps", "aux", "|", "grep", "python"], shell=True, capture_output=True, text=True)
    print(result.stdout)

if __name__ == "__main__":
    print(f"[{datetime.now()}] 무단 접근 확인 검사 시작")
    check_git_history()
    check_recent_files()
    check_processes()
