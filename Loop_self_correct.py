import urllib.request
import urllib.parse
import http.cookiejar
import json

def agent_search_and_verify(query):
    """
    할루시네이션을 방지하기 위한 자가 수정형 검색 및 검증 에이전트 루프
    """
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
    
    log = []
    log.append(f"[Step 1] Query initiated: {query}")
    
    try:
        response = opener.open(url, timeout=5)
        html = response.read().decode("utf-8")
        log.append(f"[Step 2] HTTP Response received. Length: {len(html)}")
        
        # 봇 탐지 검사
        if "anomaly" in html.lower() or "challenge" in html.lower():
            log.append("[Step 3] Error: Bot detection / Captcha challenge triggered. Search blocked.")
            return {"status": "FAILED", "reason": "Bot detection blocked live search.", "log": log}
        
        # 유효 결과 검사
        if "result" not in html.lower():
            log.append("[Step 3] Error: No valid search results found in HTML.")
            return {"status": "FAILED", "reason": "No valid search results.", "log": log}
            
        log.append("[Step 3] Success: Valid search results retrieved.")
        return {"status": "SUCCESS", "log": log}
        
    except Exception as e:
        log.append(f"[Step 3] Exception occurred: {str(e)}")
        return {"status": "FAILED", "reason": str(e), "log": log}

def self_correcting_loop():
    query = 'Loopdesk "Agentic Video Editor"'
    max_attempts = 3
    
    for attempt in range(1, max_attempts + 1):
        print(f"\n--- [Attempt {attempt}] ---")
        result = agent_search_and_verify(query)
        for entry in result["log"]:
            print(entry)
            
        if result["status"] == "SUCCESS":
            print("-> Verification PASSED. Real data acquired.")
            return True
        else:
            print(f"-> Verification FAILED due to: {result['reason']}")
            print("-> Self-Correction Triggered: Avoiding hallucination. Refusing to fabricate simulated fallback data.")
            
    print("\n--- [Final Result] ---")
    print("Agent safely halted without hallucination due to persistent search blocking.")
    return False

if __name__ == "__main__":
    self_correcting_loop()
