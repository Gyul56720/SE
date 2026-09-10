import urllib.parse
import subprocess

query = "중화역 맛집"
encoded_query = urllib.parse.quote(query)
url = f"https://search.naver.com/search.naver?query={encoded_query}"
print(f"URL: {url}")
result = subprocess.run(["python3", "dig/run.py", "--url", url], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
