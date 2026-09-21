# -*- coding: utf-8 -*-
"""클론한 저장소들을 **재서** `agentbook/zoo.json` 에 적는다.

책이 빌드될 때 망을 안 탄다. 그래서 잰 것을 여기에 담아 두고, 장들은 이 파일에서
꺼내 쓴다. 담기는 것은 **커밋 해시와 잰 날짜**까지다 -- "langgraph 는 이렇다" 는
언제의 langgraph 냐에 따라 틀린 말이 되기 때문이다.

    python3 agentbook/재다.py <클론들이 있는 디렉터리>
"""
import json
import os
import subprocess
import sys
import time

확장 = {".py": "Python", ".rs": "Rust", ".ts": "TypeScript", ".tsx": "TypeScript",
      ".js": "JavaScript", ".jsx": "JavaScript", ".go": "Go", ".java": "Java",
      ".kt": "Kotlin", ".c": "C", ".h": "C", ".cc": "C++", ".cpp": "C++",
      ".cu": "CUDA", ".sh": "Shell", ".proto": "Protobuf", ".toml": "TOML",
      ".json": "JSON", ".md": "Markdown", ".yaml": "YAML", ".yml": "YAML"}
건너뛸 = {".git", "node_modules", "__pycache__", "dist", "build", ".venv",
       "site-packages", "target", ".next", "vendor"}


def 줄수(p):
    try:
        with open(p, "rb") as f:
            return f.read().count(b"\n") + 1
    except OSError:
        return 0


def 한저장소(경로):
    def git(*a):
        return subprocess.run(["git", "-C", 경로, *a], capture_output=True,
                              text=True).stdout.strip()
    말 = {}
    파일 = {}
    for 뿌리, 디렉, 것들 in os.walk(경로):
        디렉[:] = [d for d in 디렉 if d not in 건너뛸 and not d.startswith(".")]
        for f in 것들:
            확 = os.path.splitext(f)[1].lower()
            if 확 not in 확장:
                continue
            p = os.path.join(뿌리, f)
            n = 줄수(p)
            말[확장[확]] = 말.get(확장[확], [0, 0])
            말[확장[확]][0] += 1
            말[확장[확]][1] += n
            파일[os.path.relpath(p, 경로)] = n
    return {
        "이름": os.path.basename(경로),
        "주소": git("config", "--get", "remote.origin.url").replace(".git", ""),
        "커밋": git("rev-parse", "--short", "HEAD"),
        "커밋날": git("log", "-1", "--format=%cI"),
        "잰날": time.strftime("%Y-%m-%d"),
        "말": {k: {"파일": v[0], "줄": v[1]} for k, v in
              sorted(말.items(), key=lambda kv: -kv[1][1])},
        # 파일 목록 전부를 담으면 zoo.json 이 1.3 MB 가 된다(실측). 이 책이
        # 인용하는 것은 큰 파일들이라, **줄 수 상위 150개**만 담는다. 합계는
        # 위 "말" 에 이미 전부가 반영돼 있다.
        "파일": dict(sorted(파일.items(), key=lambda kv: -kv[1])[:150]),
        "파일수": len(파일),
    }


if __name__ == "__main__":
    뿌리 = sys.argv[1]
    out = {}
    for d in sorted(os.listdir(뿌리)):
        p = os.path.join(뿌리, d)
        if os.path.isdir(os.path.join(p, ".git")):
            out[d] = 한저장소(p)
            m = out[d]["말"]
            print(f"{d:26s} {out[d]['커밋']}  "
                  + " · ".join(f"{k} {v['줄']:,}" for k, v in list(m.items())[:3]))
    여기 = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(여기, "zoo.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"-> zoo.json  저장소 {len(out)}개")
