import os
import requests

# Qwen2.5-Coder-7B-Instruct의 GGUF 모델 URL (HuggingFace)
# QuantFactory가 올린 GGUF 버전
url = "https://huggingface.co/QuantFactory/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-7B-Instruct.Q4_K_M.gguf"

# 파일의 처음 1MB만 다운로드하여 헤더 및 가중치 구조 확인
def download_partial_file(url, filename, size=1024*1024):
    headers = {'Range': f'bytes=0-{size-1}'}
    response = requests.get(url, headers=headers, stream=True)
    with open(filename, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Downloaded {size} bytes to {filename}")

if __name__ == "__main__":
    file_path = "Qwen2.5-Coder-7B-partial.gguf"
    download_partial_file(url, file_path)
    
    # GGUF 파일 헤더 분석 (GGUF는 앞부분에 매직 넘버와 모델 정보가 있음)
    with open(file_path, "rb") as f:
        magic = f.read(4)
        print(f"GGUF Magic Number: {magic}")
        # GGUF 파일의 구조적 특징 확인
        # GGUF는 0x46554747 (GGUF)로 시작함
