import subprocess
import os

def run_audit():
    # 1. Git 로그 조사
    log = subprocess.run(["git", "log", "-n", "10", "--pretty=format:%an <%ae> %s"], capture_output=True, text=True).stdout
    
    # 2. 최근 수정된 파일 조사
    files = subprocess.run(["find", ".", "-mmin", "-120", "-type", "f", "-not", "-path", "*/.*"], capture_output=True, text=True).stdout
    
    # 3. 프로세스 조사
    procs = subprocess.run(["ps", "aux"], capture_output=True, text=True).stdout
    
    report = f"--- [Public Agent Security Audit Report] ---\n"
    report += f"1. Recent Git Commits:\n{log}\n\n"
    report += f"2. Files modified in last 2 hours:\n{files}\n\n"
    report += f"3. Running Processes (Python related):\n"
    for line in procs.splitlines():
        if "python" in line:
            report += f"{line}\n"
            
    return report

if __name__ == "__main__":
    print(run_audit())
