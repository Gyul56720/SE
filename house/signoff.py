# -*- coding: utf-8 -*-
"""사인오프 꾸러미를 낸다 -- **말이 아니라 파일로**.

사용자 지시(2026-09-21): "우리가 만든 회로의 최종 sign-off 회로를 받았으면 해.
지금 그걸 말 안 해줘. 베릴로그, 시스템 베릴로그, HLS 등으로 작성된 최종 코드를
보내줘."

그래서 이 스크립트는 **설명을 안 쓴다.** 대신

  1. RTL(SystemVerilog) 원본을 담고
  2. **yosys 를 다시 돌려** 게이트 레벨 넷리스트(.v)를 새로 뽑고
  3. **HLS 를 다시 돌려** C 식에서 SystemVerilog 를 새로 낳고(기능확인까지)
  4. SDC/UPF, 검증 하니스, GDSII 를 담고
  5. 담은 것마다 **sha256 과 줄 수**를 적은 MANIFEST 를 쓴다

그러면 받은 사람이 "이게 정말 그때 그것이냐" 를 스스로 확인할 수 있다.
**꾸러미 안의 수는 이 스크립트가 잰 것이고, 보고서의 수와 같아야 한다.**
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

여기 = Path(__file__).resolve().parent
저장소 = 여기.parent
sys.path.insert(0, str(저장소))

from house import designs, synth, hls   # noqa: E402

낼곳 = 여기 / "signoff"


def _해시(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def _줄(p: Path) -> int:
    try:
        return p.read_text(encoding="utf-8", errors="replace").count("\n") + 1
    except OSError:
        return 0


def 꾸리기(키="fir", 파라=None) -> dict:
    d = designs.찾기(키)
    낼곳.mkdir(parents=True, exist_ok=True)
    담은것 = []

    def 담기(원본: Path, 이름: str, 무엇: str):
        대상 = 낼곳 / 이름
        shutil.copyfile(원본, 대상)
        담은것.append({"파일": 이름, "무엇": 무엇, "바이트": 대상.stat().st_size,
                    "줄": _줄(대상), "sha256": _해시(대상)})
        return 대상

    # 1. RTL -- 사람이 쓴 것
    for p in d.RTL:
        담기(p, p.name, "RTL (SystemVerilog) -- 사람이 쓴 원본")

    # 2. 게이트 레벨 넷리스트 -- yosys 를 지금 다시 돌려서
    합 = synth.합성(파라 or dict(d.파라), top=d.top, 빠르게=True, 설계=d)
    if not 합.get("됐나"):
        return {"됐나": False, "까닭": f"합성 실패: {합.get('까닭','')[:300]}"}
    넷 = 담기(Path(합["v"]), f"{d.top}_netlist.v",
            f"게이트 레벨 넷리스트 (Verilog) -- yosys, {합['라이브러리']}, abc {합['abc']}")
    담기(Path(합["json"]), f"{d.top}_netlist.json",
       "같은 넷리스트의 JSON -- STA/배치가 읽는 것")

    # 3. HLS -- C 식에서 SV 를 낳고 기능까지 확인한다
    식 = "(a0*x0 + a1*x1) + (a2*x2 + a3*x3)"
    자원 = {"mul": 2, "add": 1, "sub": 1}
    # **PPA 는 여기서 안 돌린다.** `hls.한바퀴` 는 끝에 yosys+abc 를 한 번 더 도는데,
    # 이 기계에서 16x16 곱셈기 매핑에 십 분 넘게 걸려 꾸러미 만들기가 멎었다
    # (실측 2026-09-21: 25분 뒤에도 안 끝나 죽였다). 면적/Fmax 는 Marcus 의
    # 보고서가 이미 재서 냈고, 여기서 필요한 것은 **낳은 RTL 과 그것이 C 와 같다는
    # 확인**이다. 그래서 스케줄·바인딩·생성·기능확인까지만 한다.
    g = hls.읽기(식)
    sch = hls.스케줄(g, 자원)
    bnd = hls.바인딩(g, 자원)
    sv = hls.생성(g, sch, bnd, "nsw_mac4_hls")
    fn = hls.기능확인(식, sv, "nsw_mac4_hls", 횟수=200)
    h = {"SV": sv, "스케줄": sch, "바인딩": bnd, "기능": fn,
         "PPA": {"면적_um2": None, "Fmax_MHz": None,
                 "메모": "PPA 는 Marcus 의 합성 보고서에 있다 -- 여기서 두 번 안 돈다"}}
    hp = 낼곳 / "nsw_mac4_hls.sv"
    hp.write_text(h["SV"], encoding="utf-8")
    담은것.append({"파일": hp.name,
                "무엇": f"HLS 가 낳은 RTL -- 식 {식!r}, 자원 {자원}, "
                      f"기능확인 {'통과' if h['기능']['됐나'] else '실패'} "
                      f"({h['기능'].get('견준수')} 벡터)",
                "바이트": hp.stat().st_size, "줄": _줄(hp), "sha256": _해시(hp)})
    hc = 낼곳 / "nsw_mac4_hls.c"
    hc.write_text(
        "/* HLS 입력 -- 이 한 줄이 위 nsw_mac4_hls.sv 가 되었다.\n"
        f" * 자원: {자원}\n"
        f" * 스케줄: 지연 {h['스케줄']['지연_단계']} 단계 · II {h['스케줄']['II']}\n"
        f" * 바인딩: {h['바인딩']['연산기수']} · 레지스터 {h['바인딩']['레지스터수']}\n"
        " */\n"
        "int nsw_mac4(int a0,int x0,int a1,int x1,int a2,int x2,int a3,int x3){\n"
        f"    return {식};\n}}\n", encoding="utf-8")
    담은것.append({"파일": hc.name, "무엇": "HLS 입력 (C)", "바이트": hc.stat().st_size,
                "줄": _줄(hc), "sha256": _해시(hc)})

    # 4. 제약 · 전력의도 · 검증 하니스 · GDSII
    if d.SDC and Path(d.SDC).exists():
        담기(Path(d.SDC), Path(d.SDC).name, "타이밍 제약 (SDC)")
    if d.UPF and Path(d.UPF).exists():
        담기(Path(d.UPF), Path(d.UPF).name, "전력 의도 (UPF)")
    if d.TB and Path(d.TB).exists():
        담기(Path(d.TB), Path(d.TB).name,
           "검증 하니스 (C++/verilator) -- UVM 꼴: 시퀀스·드라이버·모니터·참조모델·스코어보드·커버리지")
    gds = 여기 / "out" / f"{d.top}.gds"
    if gds.exists():
        담기(gds, gds.name, "GDSII (이진) -- 배치·배선 결과의 층 도형")
    for vcd in (여기 / "out").glob("*.vcd"):
        담기(vcd, vcd.name, "파형 (VCD) -- 보고서의 파형 그림이 여기서 나왔다")

    # 5. MANIFEST
    총줄 = sum(x["줄"] for x in 담은것)
    manifest = {
        "설계": {"키": d.키, "이름": d.이름, "top": d.top, "한줄": d.한줄,
               "파라": dict(파라 or d.파라), "클럭": dict(d.클럭), "출처": d.출처},
        "잰때": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "커밋": subprocess.run(["git", "-C", str(저장소), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True).stdout.strip(),
        "합성": {"면적_um2": 합["면적_um2"], "셀수": 합["셀수"], "배선수": 합["배선수"],
               "라이브러리": 합["라이브러리"], "abc": 합["abc"],
               "셀종류상위": dict(sorted(합["셀종류"].items(),
                                   key=lambda kv: -kv[1])[:12])},
        "HLS": {"식": 식, "자원": 자원,
                "지연_단계": h["스케줄"]["지연_단계"], "II": h["스케줄"]["II"],
                "연산기": h["바인딩"]["연산기수"], "레지스터": h["바인딩"]["레지스터수"],
                "기능확인": h["기능"]["됐나"], "견준벡터": h["기능"].get("견준수"),
                "면적_um2": h["PPA"].get("면적_um2"), "Fmax_MHz": h["PPA"].get("Fmax_MHz")},
        "파일": 담은것, "파일수": len(담은것), "총줄": 총줄,
    }
    (낼곳 / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"됐나": True, "manifest": manifest, "곳": str(낼곳)}


def main() -> int:
    r = 꾸리기()
    if not r["됐나"]:
        print(r["까닭"])
        return 1
    m = r["manifest"]
    print(f"사인오프 꾸러미 -> {r['곳']}  (파일 {m['파일수']}개 · 총 {m['총줄']:,}줄)")
    print(f"  설계 {m['설계']['이름']} · top {m['설계']['top']} · 커밋 {m['커밋']}")
    print(f"  합성 면적 {m['합성']['면적_um2']:,} um^2 · 셀 {m['합성']['셀수']:,} · "
          f"{m['합성']['라이브러리']} · abc {m['합성']['abc']}")
    print(f"  HLS  지연 {m['HLS']['지연_단계']}단계 · II {m['HLS']['II']} · "
          f"기능확인 {'통과' if m['HLS']['기능확인'] else '실패'}"
          f"({m['HLS']['견준벡터']} 벡터) · Fmax {m['HLS']['Fmax_MHz']} MHz")
    for x in m["파일"]:
        print(f"   {x['파일']:28s} {x['줄']:>7,}줄  {x['sha256'][:12]}  {x['무엇'][:56]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
