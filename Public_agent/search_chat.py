import os

def find_chat_logs(search_term, log_directory="."):
    """
    지정된 디렉토리 내의 파일들에서 특정 검색어가 포함된 라인을 출력합니다.
    """
    found_occurrences = []
    
    # 예시: 현재 디렉토리 및 하위 디렉토리의 모든 파일 탐색
    for root, dirs, files in os.walk(log_directory):
        for file in files:
            # 로그 파일 확장자나 특정 규칙이 있다면 여기에 추가
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if search_term in line:
                            found_occurrences.append((file_path, line_num, line.strip()))
            except (UnicodeDecodeError, PermissionError):
                continue
                
    return found_occurrences

if __name__ == "__main__":
    term = "김희섭"
    results = find_chat_logs(term)
    
    if results:
        print(f"'{term}' 검색 결과:")
        for path, line_num, content in results:
            print(f"파일: {path}, 줄: {line_num}, 내용: {content}")
    else:
        print(f"'{term}'을(를) 포함하는 로그를 찾을 수 없습니다.")
