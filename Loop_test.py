import urllib.request
import urllib.parse
import http.cookiejar
import re

def verify_search(query):
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    
    headers = [
        ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
        ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        ("Accept-Language", "en-US,en;q=0.5"),
        ("Referer", "https://duckduckgo.com/")
    ]
    opener.addheaders = headers
    
    encoded_query = urllib.parse.quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    
    try:
        response = opener.open(url, timeout=5)
        html = response.read().decode("utf-8")
        
        # 1번 한계 검증: 봇 차단 여부
        is_blocked = "anomaly" in html.lower() or "challenge" in html.lower()
        
        # 2번 한계 검증: 유효한 검색 결과(Snippet 또는 결과 타이틀) 존재 여부
        has_results = "result" in html.lower() and not is_blocked
        
        return not is_blocked and has_results
    except Exception:
        return False

# 자가 검증 루프 (True가 될 때까지 반복하며 시행 횟수 카운트)
max_attempts = 5
success = False
attempts = 0

query = '"Loopdesk" "Agentic" "Video Editor"'

for i in range(1, max_attempts + 1):
    attempts = i
    if verify_search(query):
        success = True
        break

print(f"Result: {success}")
print(f"Attempts: {attempts}")
