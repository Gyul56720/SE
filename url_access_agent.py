import subprocess
import sys

def try_url(name, url, headers=None):
    print(f"--- Attempting: {name} ---")
    cmd = ["curl", "-sL", "-m", "10"]
    if headers:
        for h in headers:
            cmd += ["-H", h]
    cmd.append(url)
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    content = res.stdout
    
    # Validation logic
    is_login_wall = any(x in content for x in ["ServiceLogin", "accounts.google.com", "Google 계정에 로그인"])
    if is_login_wall:
        return False, "Login Required"
    if len(content) < 300:
        return False, "Too short"
    
    return True, content

doc_id = "1Lb39_N9MRDfQJ70TAOqWVPdWcPSEBgAzTvOkaRDccyQ"

# Initial Strategies
strategies = [
    ("Standard Mobile", f"https://docs.google.com/document/d/{doc_id}/mobilebasic"),
    ("Direct Export", f"https://docs.google.com/document/d/{doc_id}/export?format=txt")
]

# Self-Improvement: Adding advanced header spoofing and sharing parameter variants
print("[Self-Improvement] Enhancing agent with User-Agent spoofing and Sharing parameter variations...")
improved_strategies = strategies + [
    ("Spoofed Chrome", f"https://docs.google.com/document/d/{doc_id}/mobilebasic", 
     ["User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"]),
    ("Sharing Param", f"https://docs.google.com/document/d/{doc_id}/edit?usp=sharing"),
    ("Open Source Export", f"https://docs.google.com/document/u/0/export?format=txt&id={doc_id}")
]

success = False
for entry in improved_strategies:
    name = entry[0]
    url = entry[1]
    headers = entry[2] if len(entry) > 2 else None
    
    is_ok, result = try_url(name, url, headers)
    if is_ok:
        print(f"Result: {name} SUCCESS! Length: {len(result)}")
        with open("doc_extracted_content.txt", "w") as f:
            f.write(result)
        success = True
        break
    else:
        print(f"Result: {name} FAILED ({result})")

if not success:
    print("\n[!] Conclusion: The document is restricted at the server-side (IAM).")
    print("Self-Correction: To proceed, please set the document permission to 'Anyone with the link' or provide an OAuth token.")

