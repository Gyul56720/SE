import json
import sys
from collections import defaultdict
from pathlib import Path

def analyze_repair(path):
    stats = defaultdict(lambda: {"바퀴": 0, "맞음": 0, "틀림": 0, "막음": 0, "명령": 0, "내탓": 0, "기타": 0})
    if not path.exists(): return stats
    with open(path, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line)
                cat = entry.get("꼴", "알수없음")
                stats[cat]["바퀴"] += entry.get("바퀴", 0)
                stats[cat]["맞음"] += entry.get("맞춘수", 0)
                stats[cat]["틀림"] += entry.get("틀린수", 0)
                stats[cat]["막음"] += entry.get("막음", 0)
                stats[cat]["명령"] += entry.get("명령수", 0)
                if entry.get("귀속") == 0:
                    stats[cat]["내탓"] += 1
                else:
                    stats[cat]["기타"] += 1
            except: continue
    return stats

def analyze_improve(path):
    stats = defaultdict(int)
    if not path.exists(): return stats
    with open(path, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line)
                stats[entry.get("꼴", "알수없음")] += 1
            except: continue
    return stats

def main():
    repair_path = Path("repair/ledger.jsonl")
    improve_path = Path("improve/ledger.jsonl")
    
    r_stats = analyze_repair(repair_path)
    i_stats = analyze_improve(improve_path)
    
    print(f"{'꼴':<10} | {'바퀴':<5} | {'맞음':<5} | {'틀림':<5} | {'막음':<5} | {'명령':<5} | {'내탓':<5} | {'기타':<5}")
    for cat, s in r_stats.items():
        print(f"{cat:<10} | {s['바퀴']:<5} | {s['맞음']:<5} | {s['틀림']:<5} | {s['막음']:<5} | {s['명령']:<5} | {s['내탓']:<5} | {s['기타']:<5}")
    
    print("\n[Improve Ledger Stats]")
    for cat, count in i_stats.items():
        print(f"{cat}: {count}")

if __name__ == "__main__":
    main()
