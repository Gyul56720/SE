import urllib.parse
import subprocess

query = "중화역 맛집"
encoded_query = urllib.parse.quote(query)
url = f"https://search.naver.com/search.naver?query={encoded_query}"
# --따라 2를 사용해 더 자세한 정보를 추출합니다.
result = subprocess.run(["python3", "dig/run.py", "--url", url, "--따라", "2"], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
