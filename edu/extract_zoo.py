# -*- coding: utf-8 -*-
"""IP 동물원과 모델 동물원을 **기계로** 훑는다.

교안의 모든 수가 이 파일에서 나온다.  손으로 적은 수는 없다.
말뭉치 서베이(survey/extract.py)와 같은 규율이다.
"""
import json, os, re, sys

ZOO = {"ip": "/home/user/ipzoo", "model": "/home/user/modelzoo",
       "hls": "/home/user/hls_study"}

RTL = {".sv", ".v", ".svh", ".vh"}
SW  = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh"}
ETC = {".py", ".scala", ".sail", ".S", ".s"}
ALL = RTL | SW | ETC

건너뛸디렉 = {".git", "node_modules", "__pycache__", ".github", "build", "dist"}

# 모듈/클래스/함수를 아주 가볍게 센다 -- 파서가 아니라 자
_모듈 = re.compile(r"^\s*(?:module|interface|package|program)\s+(\w+)", re.M)
_클래스 = re.compile(r"^\s*(?:class|struct)\s+(\w+)", re.M)
_함수C = re.compile(r"^[A-Za-z_][\w\s\*:<>,&~]*?\b(\w+)\s*\([^;{]*\)\s*(?:const\s*)?\{", re.M)
_항상 = re.compile(r"^\s*always(?:_ff|_comb|_latch)?\b", re.M)
_단언 = re.compile(r"^\s*\w*\s*:?\s*assert\b|`ASSERT|\bassert\s+property", re.M)


def 훑기(밑):
    난것 = []
    for 뿌리, 디렉, 파일들 in os.walk(밑):
        디렉[:] = [d for d in 디렉 if d not in 건너뛸디렉]
        for f in 파일들:
            확장 = os.path.splitext(f)[1]
            if 확장 not in ALL:
                continue
            p = os.path.join(뿌리, f)
            try:
                if os.path.getsize(p) > 4_000_000:
                    continue
                t = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            줄 = t.count("\n") + 1
            난것.append({
                "경로": os.path.relpath(p, 밑),
                "확장": 확장,
                "종류": "RTL" if 확장 in RTL else ("SW" if 확장 in SW else "기타"),
                "줄": 줄,
                "바이트": len(t),
                "모듈": _모듈.findall(t)[:40],
                "클래스": _클래스.findall(t)[:40],
                "always": len(_항상.findall(t)),
                "단언": len(_단언.findall(t)),
            })
    return 난것


def 저장소별(파일들):
    """저장소별 집계.

    **첫 판은 틀렸다.** 한 줄에 조건을 겹쳐 쓰는 바람에 '기타' 파일에서
    왼쪽은 `줄`, 오른쪽은 `SW줄` 을 읽어 **합계를 부분으로 덮어썼다**
    (opentitan 이 줄=446,830 인데 RTL줄=1,167,060 으로 나왔다 -- 합계가
    부분보다 작을 수 없다).  영리하게 쓰려다 틀렸다.  풀어 쓴다.
    """
    d = {}
    for f in 파일들:
        r = f["경로"].split(os.sep)[0]
        s = d.setdefault(r, {"파일": 0, "줄": 0, "RTL줄": 0, "SW줄": 0, "기타줄": 0,
                             "모듈": 0, "클래스": 0, "always": 0, "단언": 0})
        s["파일"] += 1
        s["줄"] += f["줄"]
        if f["종류"] == "RTL":
            s["RTL줄"] += f["줄"]
        elif f["종류"] == "SW":
            s["SW줄"] += f["줄"]
        else:
            s["기타줄"] += f["줄"]
        s["모듈"] += len(f["모듈"])
        s["클래스"] += len(f["클래스"])
        s["always"] += f["always"]
        s["단언"] += f["단언"]
    # 합계가 부분의 합과 같은지 **재서** 확인한다.  덮어쓰기 사고를 막는 장치.
    for r, s in d.items():
        부분 = s["RTL줄"] + s["SW줄"] + s["기타줄"]
        assert s["줄"] == 부분, f"{r}: 줄 {s['줄']} != 부분합 {부분}"
    return d


if __name__ == "__main__":
    밖 = {}
    for 이름, 밑 in ZOO.items():
        if not os.path.isdir(밑):
            print(f"건너뜀(없음): {밑}")
            continue
        fs = 훑기(밑)
        밖[이름] = fs
        print(f"{이름:6s} {len(fs):6,d}파일 {sum(f['줄'] for f in fs):10,d}줄")
    os.makedirs("/home/user/edu", exist_ok=True)
    json.dump(밖, open("/home/user/edu/zoo.json", "w"), ensure_ascii=False)
    합 = {k: 저장소별(v) for k, v in 밖.items()}
    json.dump(합, open("/home/user/edu/zoo_by_repo.json", "w"),
              ensure_ascii=False, indent=1)
    print(f"\n총 {sum(len(v) for v in 밖.values()):,}파일 "
          f"{sum(f['줄'] for v in 밖.values() for f in v):,}줄")
