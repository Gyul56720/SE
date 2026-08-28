import urllib.request
import urllib.parse
import json
import http.cookiejar

def robust_search(query):
    # 쿠키 저장소 생성 (세션 유지)
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    
    # 실제 브라우저와 유사한 헤더 세팅
    headers = [
        ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
        ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"),
        ("Accept-Language", "en-US,en;q=0.5"),
        ("Referer", "https://duckduckgo.com/")
    ]
    opener.addheaders = headers
    
    encoded_query = urllib.parse.quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    
    try:
        response = opener.open(url, timeout=5)
        html = response.read().decode("utf-8")
        
        if "anomaly" in html.lower() or "challenge" in html.lower():
            return {"status": "blocked", "reason": "Bot detection / Captcha challenge triggered by simple script request."}
        
        return {"status": "success", "length": len(html)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    print(json.dumps(robust_search("Loopdesk Agentic Video Editor"), indent=2))
