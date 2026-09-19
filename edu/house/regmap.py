# -*- coding: utf-8 -*-
"""레지스터 맵 **한 곳**에서 RTL · C 헤더 · 문서 · IP-XACT 를 낸다.

## 왜 생성기인가

레지스터 맵은 최소 여섯 곳에 나타난다: RTL, 드라이버 헤더, 데이터시트 표,
검증 모델, 디버거 기술, 통합 도구용 IP-XACT.  손으로 여섯 벌을 유지하면
반드시 갈라지고, 갈라진 것은 **통합할 때** 발견된다 -- 가장 비싼 자리다.

교안 Y10 장이 이 계산을 한다: 60개 레지스터, 9개월, 편집당 2 % 놓침이면
기대 놓침이 아홉 개다.  그래서 여기서는 **말하지 않고 만든다.**

## 쓰기

    python3 regmap.py 예제 --rtl  > regs.v
    python3 regmap.py 예제 --c    > regs.h
    python3 regmap.py 예제 --md   > regs.md
    python3 regmap.py 예제 --ipxact > regs.xml
    python3 regmap.py 예제 --전부 낼자리/

맵은 파이썬 리터럴이다(YAML 의존성을 안 쓴다 -- VM 에 없을 수 있다).
"""
import argparse
import html
import os
import sys

# 접근 종류.  각각이 어떤 경주를 막는지 Y10 장에 있다.
접근종류 = {
    "RO":  "읽기 전용, 쓰기는 무시",
    "RW":  "읽고 쓰기",
    "W1C": "1 을 쓰면 지워진다 (두 드라이버가 서로의 비트를 안 지우게)",
    "W1S": "1 을 쓰면 세워진다",
    "RC":  "읽으면 지워진다 (디버거가 건드리면 상태가 바뀐다 -- 표시해 둘 것)",
    "WO":  "쓰기 전용",
    "RW1": "리셋까지 한 번만 쓸 수 있다 (잠기는 설정)",
}


class 필드:
    """레지스터 안의 한 필드.

    `하드웨어` 가 True 면 그 값을 **하드웨어가 준다**(포트가 생긴다).
    False 인 RO 필드는 **상수**다 -- 리셋값이 곧 읽히는 값이다.

    실측 2026-09-19: 처음에는 RO 를 전부 하드웨어 입력으로 만들었다.  그러면
    **ID 레지스터를 표현할 수 없다** -- 상수 벤더 코드를 넣을 자리가 없어서
    0 이 읽혔다.  검증 에이전트가 첫 실행에서 이것을 잡았다(기대 0x1A2B0110,
    실제 0x00000000).  생성기를 쓰되 생성물을 검사한다는 것이 이런 뜻이다.
    """

    def __init__(self, 이름, 상위, 하위, 접근, 리셋, 설명, 하드웨어=None):
        if 접근 not in 접근종류:
            raise ValueError(f"모르는 접근 종류: {접근}")
        if not (0 <= 하위 <= 상위 <= 31):
            raise ValueError(f"{이름}: 비트 범위가 이상하다 {상위}:{하위}")
        폭 = 상위 - 하위 + 1
        if 리셋 >= (1 << 폭):
            raise ValueError(f"{이름}: 리셋값 {리셋} 이 {폭} 비트에 안 들어간다")
        self.이름, self.상위, self.하위 = 이름, 상위, 하위
        self.접근, self.리셋, self.설명 = 접근, 리셋, 설명
        # 기본값: RO 는 상수, W1C/W1S/RC 는 하드웨어가 세운다, 나머지는 소프트웨어
        if 하드웨어 is None:
            하드웨어 = 접근 in ("W1C", "W1S", "RC")
        self.하드웨어 = 하드웨어
        if 하드웨어 and 접근 in ("RW", "WO", "RW1"):
            raise ValueError(f"{이름}: {접근} 필드를 하드웨어가 쓰면 "
                             "read-modify-write 경주가 난다 (Y10 장). "
                             "별도 레지스터로 갈라라")

    @property
    def 폭(self):
        return self.상위 - self.하위 + 1

    @property
    def 마스크(self):
        return ((1 << self.폭) - 1) << self.하위


class 레지스터:
    def __init__(self, 이름, 오프셋, 필드들, 설명=""):
        self.이름, self.오프셋, self.설명 = 이름, 오프셋, 설명
        self.필드들 = 필드들
        if 오프셋 % 4:
            raise ValueError(f"{이름}: 오프셋 0x{오프셋:x} 이 4 의 배수가 아니다")
        # 겹침 검사 -- 손으로 쓴 맵에서 가장 흔한 오류다
        쓴비트 = 0
        for f in 필드들:
            if 쓴비트 & f.마스크:
                raise ValueError(f"{이름}.{f.이름}: 비트가 겹친다")
            쓴비트 |= f.마스크

    @property
    def 리셋값(self):
        v = 0
        for f in self.필드들:
            v |= f.리셋 << f.하위
        return v


class 맵:
    def __init__(self, 이름, 레지스터들, 설명=""):
        self.이름, self.레지스터들, self.설명 = 이름, 레지스터들, 설명
        본 = set()
        for r in 레지스터들:
            if r.오프셋 in 본:
                raise ValueError(f"오프셋 0x{r.오프셋:x} 이 두 번 나온다")
            본.add(r.오프셋)

    @property
    def 크기(self):
        return max(r.오프셋 for r in self.레지스터들) + 4


# ------------------------------------------------------------------ 내는 것
def rtl(m):
    """APB 꼴 레지스터 파일.  접근 종류마다 다른 쓰기 동작을 낸다."""
    o = [f"// 자동 생성 -- 고치지 마라.  원본은 regmap.py 의 맵 정의다.",
         f"// 맵: {m.이름}   크기: {m.크기} 바이트",
         f"module {m.이름}_regs (",
         "   input  wire        clk,",
         "   input  wire        rst_n,",
         "   input  wire [31:0] paddr,",
         "   input  wire        psel,",
         "   input  wire        penable,",
         "   input  wire        pwrite,",
         "   input  wire [31:0] pwdata,",
         "   output reg  [31:0] prdata,",
         "   output wire        pready,"]
    for r in m.레지스터들:
        for f in r.필드들:
            n = f"{r.이름.lower()}_{f.이름.lower()}"
            if f.접근 == "RO":
                if f.하드웨어:
                    o.append(f"   input  wire [{f.폭-1}:0] hw_{n},")
                # 상수 RO 는 포트를 만들지 않는다
            elif f.접근 in ("W1C", "W1S", "RC"):
                o.append(f"   input  wire [{f.폭-1}:0] hw_set_{n},")
                o.append(f"   output wire [{f.폭-1}:0] {n},")
            else:
                o.append(f"   output wire [{f.폭-1}:0] {n},")
    o[-1] = o[-1].rstrip(",")
    o.append(");")
    o.append("   assign pready = 1'b1;")
    o.append("   // 접근은 **enable 단계에서만** 일어난다.  처음에는 rd 에서")
    o.append("   // penable 을 빠뜨렸는데, 그러면 RC 레지스터가 setup 단계에서")
    o.append("   // 미리 지워져 읽기가 0 을 돌려준다.  검증 에이전트가 잡았다")
    o.append("   // (ERR_COUNT: 기대 7, 실제 0).")
    o.append("   wire wr = psel & penable & pwrite;")
    o.append("   wire rd = psel & penable & ~pwrite;")
    for r in m.레지스터들:
        for f in r.필드들:
            n = f"{r.이름.lower()}_{f.이름.lower()}"
            if f.접근 == "RO":
                continue
            o.append(f"   reg [{f.폭-1}:0] r_{n};")
            o.append(f"   assign {n} = r_{n};")
    o.append("   always @(posedge clk) begin")
    o.append("      if (!rst_n) begin")
    for r in m.레지스터들:
        for f in r.필드들:
            if f.접근 == "RO":
                continue
            n = f"{r.이름.lower()}_{f.이름.lower()}"
            o.append(f"         r_{n} <= {f.폭}'d{f.리셋};")
    o.append("      end else begin")
    for r in m.레지스터들:
        for f in r.필드들:
            if f.접근 == "RO":
                continue
            n = f"{r.이름.lower()}_{f.이름.lower()}"
            sel = f"(paddr[31:2] == 30'd{r.오프셋 >> 2})"
            sl = f"pwdata[{f.상위}:{f.하위}]"
            if f.접근 in ("RW", "WO"):
                o.append(f"         if (wr && {sel}) r_{n} <= {sl};")
            elif f.접근 == "RW1":
                o.append(f"         if (wr && {sel} && (r_{n} == {f.폭}'d{f.리셋}))"
                         f" r_{n} <= {sl};")
            elif f.접근 == "W1C":
                o.append(f"         r_{n} <= (r_{n} | hw_set_{n})"
                         f" & ~((wr && {sel}) ? {sl} : {f.폭}'d0);")
            elif f.접근 == "W1S":
                o.append(f"         r_{n} <= r_{n} | ((wr && {sel}) ? {sl}"
                         f" : {f.폭}'d0);")
            elif f.접근 == "RC":
                o.append(f"         r_{n} <= (rd && {sel}) ? hw_set_{n}"
                         f" : (r_{n} | hw_set_{n});")
    o.append("      end")
    o.append("   end")
    o.append("   always @* begin")
    o.append("      prdata = 32'd0;")
    o.append("      case (paddr[31:2])")
    for r in m.레지스터들:
        parts = []
        for f in r.필드들:
            n = f"{r.이름.lower()}_{f.이름.lower()}"
            if f.접근 == "RO":
                src = f"hw_{n}" if f.하드웨어 else f"{f.폭}'d{f.리셋}"
            else:
                src = f"r_{n}"
            if f.접근 == "WO":
                continue
            parts.append(f"prdata[{f.상위}:{f.하위}] = {src};")
        o.append(f"         30'd{r.오프셋 >> 2}: begin " + " ".join(parts) + " end")
    o.append("         default: prdata = 32'd0;")
    o.append("      endcase")
    o.append("   end")
    o.append("endmodule")
    return "\n".join(l for l in o if l != "")


def c헤더(m):
    g = f"{m.이름.upper()}_REGS_H"
    o = [f"/* 자동 생성 -- 고치지 마라.  원본은 regmap.py 의 맵 정의다. */",
         f"#ifndef {g}", f"#define {g}", "", "#include <stdint.h>", ""]
    for r in m.레지스터들:
        o.append(f"/* {r.이름}: {r.설명} */")
        o.append(f"#define {m.이름.upper()}_{r.이름}_OFFSET  0x{r.오프셋:03X}u")
        o.append(f"#define {m.이름.upper()}_{r.이름}_RESET   0x{r.리셋값:08X}u")
        for f in r.필드들:
            p = f"{m.이름.upper()}_{r.이름}_{f.이름}"
            o.append(f"#define {p}_SHIFT  {f.하위}u")
            o.append(f"#define {p}_MASK   0x{f.마스크:08X}u")
            o.append(f"#define {p}_GET(v) (((v) & {p}_MASK) >> {p}_SHIFT)")
            o.append(f"#define {p}_SET(v) (((v) << {p}_SHIFT) & {p}_MASK)")
        o.append("")
    o.append(f"#endif /* {g} */")
    return "\n".join(o)


def 마크다운(m):
    o = [f"# {m.이름} 레지스터 맵", "", m.설명, "",
         "*자동 생성 -- 고치지 마라. 원본은 `regmap.py` 의 맵 정의다.*", ""]
    o.append("| 오프셋 | 이름 | 리셋 | 설명 |")
    o.append("|---|---|---|---|")
    for r in m.레지스터들:
        o.append(f"| `0x{r.오프셋:03X}` | **{r.이름}** | `0x{r.리셋값:08X}` "
                 f"| {r.설명} |")
    o.append("")
    for r in m.레지스터들:
        o.append(f"## {r.이름}  (`0x{r.오프셋:03X}`)")
        o.append("")
        o.append("| 비트 | 필드 | 접근 | 값의 출처 | 리셋 | 설명 |")
        o.append("|---|---|---|---|---|---|")
        for f in sorted(r.필드들, key=lambda x: -x.상위):
            비트 = f"{f.상위}:{f.하위}" if f.폭 > 1 else str(f.상위)
            출처 = ("하드웨어" if f.하드웨어
                   else ("상수" if f.접근 == "RO" else "소프트웨어"))
            o.append(f"| {비트} | `{f.이름}` | {f.접근} | {출처} "
                     f"| `0x{f.리셋:X}` | {f.설명} |")
        o.append("")
    o.append("## 접근 종류")
    o.append("")
    o.append("| 종류 | 뜻 |")
    o.append("|---|---|")
    for k, v in 접근종류.items():
        o.append(f"| {k} | {v} |")
    return "\n".join(o)


def ipxact(m):
    e = html.escape
    o = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<ipxact:component xmlns:ipxact="http://www.accellera.org/XMLSchema/IPXACT/'
         '1685-2014">',
         '  <ipxact:vendor>example</ipxact:vendor>',
         '  <ipxact:library>ip</ipxact:library>',
         f'  <ipxact:name>{e(m.이름)}</ipxact:name>',
         '  <ipxact:version>1.0</ipxact:version>',
         '  <ipxact:memoryMaps><ipxact:memoryMap>',
         f'    <ipxact:name>{e(m.이름)}_map</ipxact:name>',
         '    <ipxact:addressBlock>',
         '      <ipxact:name>regs</ipxact:name>',
         '      <ipxact:baseAddress>0</ipxact:baseAddress>',
         f'      <ipxact:range>{m.크기}</ipxact:range>',
         '      <ipxact:width>32</ipxact:width>']
    for r in m.레지스터들:
        o.append('      <ipxact:register>')
        o.append(f'        <ipxact:name>{e(r.이름)}</ipxact:name>')
        o.append(f'        <ipxact:description>{e(r.설명)}</ipxact:description>')
        o.append(f'        <ipxact:addressOffset>{r.오프셋}</ipxact:addressOffset>')
        o.append('        <ipxact:size>32</ipxact:size>')
        for f in r.필드들:
            o.append('        <ipxact:field>')
            o.append(f'          <ipxact:name>{e(f.이름)}</ipxact:name>')
            o.append(f'          <ipxact:bitOffset>{f.하위}</ipxact:bitOffset>')
            o.append(f'          <ipxact:bitWidth>{f.폭}</ipxact:bitWidth>')
            접근맵 = {"RO": "read-only", "RW": "read-write", "WO": "write-only",
                     "W1C": "read-write", "W1S": "read-write",
                     "RC": "read-only", "RW1": "read-write"}
            o.append(f'          <ipxact:access>{접근맵[f.접근]}</ipxact:access>')
            o.append(f'          <ipxact:resets><ipxact:reset>'
                     f'<ipxact:value>{f.리셋}</ipxact:value>'
                     f'</ipxact:reset></ipxact:resets>')
            o.append(f'          <ipxact:description>{e(f.설명)}</ipxact:description>')
            o.append('        </ipxact:field>')
        o.append('      </ipxact:register>')
    o += ['    </ipxact:addressBlock>',
          '  </ipxact:memoryMap></ipxact:memoryMaps>',
          '</ipxact:component>']
    return "\n".join(o)


# ------------------------------------------------------------------ 예제 맵
예제 = 맵("crcip", [
    레지스터("ID", 0x00, [
        필드("VENDOR", 31, 16, "RO", 0x1A2B, "벤더 식별자, 상수"),
        필드("BLOCK", 15, 8, "RO", 0x01, "블록 식별자"),
        필드("VERSION", 7, 0, "RO", 0x10, "주.부 버전, BCD"),
    ], "한 번 읽으면 전원·클럭·리셋·버스·주소해독이 한꺼번에 증명된다"),
    레지스터("SCRATCH", 0x04, [
        필드("DATA", 31, 0, "RW", 0, "아무 값. 하드웨어 효과 없음"),
    ], "쓰기 경로를 기능과 무관하게 증명한다"),
    레지스터("CTRL", 0x08, [
        필드("ENABLE", 0, 0, "RW", 0, "1 이면 데이터패스가 돈다"),
        필드("LOOPBACK", 1, 1, "RW", 0, "브링업용 내부 루프백"),
        필드("SOFT_RESET", 2, 2, "W1S", 0, "데이터패스만 리셋. 자동 해제"),
        필드("MODE", 7, 4, "RW", 0, "동작 모드"),
    ], "동작을 바꾸는 것만 모아 둔다 -- 하드웨어가 쓰는 비트를 섞지 않는다"),
    레지스터("STATUS", 0x0C, [
        필드("READY", 0, 0, "RO", 0, "초기화 완료", 하드웨어=True),
        필드("BUSY", 1, 1, "RO", 0, "처리 중", 하드웨어=True),
        필드("STATE", 7, 4, "RO", 0, "현재 상태 (디버그용)", 하드웨어=True),
    ], "살아 있는 상태. 래치하지 않는다 -- 래치는 지우기가 필요하고 지우기는 경주다"),
    레지스터("IRQ_STATUS", 0x10, [
        필드("ERR_CRC", 0, 0, "W1C", 0, "CRC 오류가 났다"),
        필드("ERR_LEN", 1, 1, "W1C", 0, "길이 오류가 났다"),
        필드("OVERFLOW", 2, 2, "W1C", 0, "수신 버퍼가 넘쳤다"),
    ], "W1C -- 두 드라이버가 서로의 비트를 지우지 못하게"),
    레지스터("IRQ_ENABLE", 0x14, [
        필드("MASK", 2, 0, "RW", 0, "IRQ_STATUS 비트마다 하나"),
    ], "상태와 따로 둔다 -- 가리는 것이 사건을 잃지 않게"),
    레지스터("ERR_COUNT", 0x18, [
        필드("COUNT", 31, 0, "RC", 0, "마지막 읽기 이후 오류 수. 포화한다"),
    ], "읽으면 지워진다. 조용히 넘어가는 카운터보다 포화가 낫다"),
])


def 본체(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("맵", nargs="?", default="예제")
    ap.add_argument("--rtl", action="store_true")
    ap.add_argument("--c", action="store_true")
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--ipxact", action="store_true")
    ap.add_argument("--전부", metavar="디렉터리")
    a = ap.parse_args(argv)
    m = globals()[a.맵]
    if a.전부:
        os.makedirs(a.전부, exist_ok=True)
        for 이름, 내용 in ((f"{m.이름}_regs.v", rtl(m)), (f"{m.이름}_regs.h", c헤더(m)),
                          (f"{m.이름}_regs.md", 마크다운(m)),
                          (f"{m.이름}.xml", ipxact(m))):
            with open(os.path.join(a.전부, 이름), "w", encoding="utf-8") as f:
                f.write(내용 + "\n")
            print(f"  냈다: {os.path.join(a.전부, 이름)}")
        return 0
    if a.rtl:   print(rtl(m))
    elif a.c:   print(c헤더(m))
    elif a.md:  print(마크다운(m))
    elif a.ipxact: print(ipxact(m))
    else:
        print(f"{m.이름}: 레지스터 {len(m.레지스터들)}개, "
              f"필드 {sum(len(r.필드들) for r in m.레지스터들)}개, "
              f"{m.크기} 바이트")
        print("  --rtl | --c | --md | --ipxact | --전부 <디렉터리>")
    return 0


if __name__ == "__main__":
    sys.exit(본체())
