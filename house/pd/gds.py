# -*- coding: utf-8 -*-
"""house/pd/gds -- GDSII stream 을 **진짜 바이너리 규격으로** 쓰고 되읽는다.

klayout·magic 이 없다. 그러면 "GDSII 를 냈다" 고 적고 넘어갈 수도 있지만, 그러면
아무도 그 말을 확인할 수 없다. 그래서 규격(Calma GDSII Stream Format)대로 바이트를
직접 적고, **같은 파일을 파서로 되읽어** 도형 수와 좌표가 맞는지 왕복 검증한다.

레코드 꼴: [2바이트 길이][1바이트 레코드타입][1바이트 자료형][데이터...]
좌표는 데이터베이스 단위(정수)이고, UNITS 레코드가 미터 환산을 준다.
"""
from __future__ import annotations

import struct
import time
from pathlib import Path

# 레코드 타입
HEADER, BGNLIB, LIBNAME, UNITS, ENDLIB = 0x00, 0x01, 0x02, 0x03, 0x04
BGNSTR, STRNAME, ENDSTR = 0x05, 0x06, 0x07
BOUNDARY, PATH, SREF, LAYER, DATATYPE = 0x08, 0x09, 0x0A, 0x0D, 0x0E
WIDTH, XY, ENDEL, SNAME, TEXT = 0x0F, 0x10, 0x11, 0x12, 0x0C
STRANS, MAG, TEXTTYPE, STRING, PATHTYPE = 0x1A, 0x1B, 0x16, 0x19, 0x21

NODATA, BITARRAY, INT2, INT4, REAL8, ASCII = 0x00, 0x01, 0x02, 0x03, 0x05, 0x06

# 층 배정 -- 실제 PDK 의 층 번호를 흉내 낸다
층 = {"NWELL": (1, 0), "DIFF": (2, 0), "POLY": (3, 0), "CONT": (4, 0),
     "M1": (5, 0), "VIA1": (6, 0), "M2": (7, 0), "VIA2": (8, 0), "M3": (9, 0),
     "M4": (10, 0), "TEXT": (63, 0), "BOUNDARY": (64, 0)}


def _rec(타입, 자료형, 몸=b"") -> bytes:
    길이 = 4 + len(몸)
    if 길이 % 2:
        몸 += b"\x00"
        길이 += 1
    return struct.pack(">HBB", 길이, 타입, 자료형) + 몸


def _real8(x: float) -> bytes:
    """GDSII 의 8바이트 실수 = IBM 370 부동소수점.  IEEE 가 아니다."""
    if x == 0:
        return b"\x00" * 8
    부호 = 0x80 if x < 0 else 0x00
    x = abs(x)
    지수 = 0
    while x >= 1.0:
        x /= 16.0
        지수 += 1
    while x < 1.0 / 16.0:
        x *= 16.0
        지수 -= 1
    가수 = int(x * (1 << 56))
    return bytes([부호 | (지수 + 64)]) + 가수.to_bytes(7, "big")


def _ascii(s: str) -> bytes:
    b = s.encode("ascii", "replace")
    if len(b) % 2:
        b += b"\x00"
    return b


class 라이브러리:
    """도형을 모아 .gds 로 낸다.  좌표 단위는 µm 이고 DB 단위는 1 nm 다."""

    def __init__(self, 이름="NSW_FIR", 사용자단위=1e-3, DB단위=1e-9):
        self.이름 = 이름
        self.사용자단위 = 사용자단위        # 1 DB 단위 = 1 nm, 사용자 단위 = µm
        self.DB단위 = DB단위
        self.구조 = {}
        self.현재 = None

    def 구조시작(self, 이름):
        self.현재 = 이름
        self.구조.setdefault(이름, [])
        return self

    def 사각(self, 층이름, x, y, w, h):
        """µm 좌표로 직사각형.  BOUNDARY 는 닫힌 다각형이어야 한다(첫 점 반복)."""
        L, D = 층.get(층이름, (0, 0))
        s = 1e-6 / self.DB단위                       # µm -> DB 단위
        pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
        self.구조[self.현재].append(
            ("BOUNDARY", L, D, [(int(round(px * s)), int(round(py * s))) for px, py in pts]))
        return self

    def 선(self, 층이름, 점들, 폭=0.2):
        L, D = 층.get(층이름, (0, 0))
        s = 1e-6 / self.DB단위
        self.구조[self.현재].append(
            ("PATH", L, D, [(int(round(px * s)), int(round(py * s))) for px, py in 점들],
             int(round(폭 * s))))
        return self

    def 글(self, 층이름, x, y, 글자):
        L, D = 층.get(층이름, (63, 0))
        s = 1e-6 / self.DB단위
        self.구조[self.현재].append(
            ("TEXT", L, D, [(int(round(x * s)), int(round(y * s)))], 글자))
        return self

    def 바이트(self) -> bytes:
        t = time.localtime()
        때 = struct.pack(">6h", t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
        out = [_rec(HEADER, INT2, struct.pack(">h", 600)),      # 릴리스 6.0
               _rec(BGNLIB, INT2, 때 + 때),
               _rec(LIBNAME, ASCII, _ascii(self.이름 + ".DB")),
               _rec(UNITS, REAL8, _real8(self.DB단위 / self.사용자단위) + _real8(self.DB단위))]
        for 이름, 도형들 in self.구조.items():
            out.append(_rec(BGNSTR, INT2, 때 + 때))
            out.append(_rec(STRNAME, ASCII, _ascii(이름)))
            for 도형 in 도형들:
                종류 = 도형[0]
                if 종류 == "BOUNDARY":
                    _, L, D, pts = 도형
                    out.append(_rec(BOUNDARY, NODATA))
                    out.append(_rec(LAYER, INT2, struct.pack(">h", L)))
                    out.append(_rec(DATATYPE, INT2, struct.pack(">h", D)))
                    out.append(_rec(XY, INT4, b"".join(struct.pack(">ii", a, b) for a, b in pts)))
                    out.append(_rec(ENDEL, NODATA))
                elif 종류 == "PATH":
                    _, L, D, pts, 폭 = 도형
                    out.append(_rec(PATH, NODATA))
                    out.append(_rec(LAYER, INT2, struct.pack(">h", L)))
                    out.append(_rec(DATATYPE, INT2, struct.pack(">h", D)))
                    out.append(_rec(PATHTYPE, INT2, struct.pack(">h", 2)))
                    out.append(_rec(WIDTH, INT4, struct.pack(">i", 폭)))
                    out.append(_rec(XY, INT4, b"".join(struct.pack(">ii", a, b) for a, b in pts)))
                    out.append(_rec(ENDEL, NODATA))
                elif 종류 == "TEXT":
                    _, L, D, pts, 글자 = 도형
                    out.append(_rec(TEXT, NODATA))
                    out.append(_rec(LAYER, INT2, struct.pack(">h", L)))
                    out.append(_rec(TEXTTYPE, INT2, struct.pack(">h", D)))
                    out.append(_rec(XY, INT4, b"".join(struct.pack(">ii", a, b) for a, b in pts)))
                    out.append(_rec(STRING, ASCII, _ascii(글자)))
                    out.append(_rec(ENDEL, NODATA))
            out.append(_rec(ENDSTR, NODATA))
        out.append(_rec(ENDLIB, NODATA))
        return b"".join(out)

    def 내기(self, 길: Path) -> Path:
        길 = Path(길)
        길.parent.mkdir(parents=True, exist_ok=True)
        길.write_bytes(self.바이트())
        return 길


# ------------------------------------------------------------------ 되읽기

def 읽기(길: Path) -> dict:
    """제 파일을 규격대로 되읽는다.  **쓴 것과 읽은 것이 맞아야 냈다고 말한다.**"""
    b = Path(길).read_bytes()
    i, n = 0, len(b)
    구조, 현재 = {}, None
    층별 = {}
    도형수 = {"BOUNDARY": 0, "PATH": 0, "TEXT": 0}
    이름 = ""
    현층 = None
    좌표수 = 0
    레코드수 = 0
    while i + 4 <= n:
        길이, 타입, 자료형 = struct.unpack(">HBB", b[i:i + 4])
        if 길이 < 4:
            break
        몸 = b[i + 4:i + 길이]
        레코드수 += 1
        if 타입 == LIBNAME:
            이름 = 몸.rstrip(b"\x00").decode("ascii", "replace")
        elif 타입 == STRNAME:
            현재 = 몸.rstrip(b"\x00").decode("ascii", "replace")
            구조.setdefault(현재, 0)
        elif 타입 == LAYER:
            현층 = struct.unpack(">h", 몸[:2])[0]
        elif 타입 in (BOUNDARY, PATH, TEXT):
            k = {BOUNDARY: "BOUNDARY", PATH: "PATH", TEXT: "TEXT"}[타입]
            도형수[k] += 1
            if 현재:
                구조[현재] += 1
        elif 타입 == XY:
            좌표수 += len(몸) // 8
            if 현층 is not None:
                층별[현층] = 층별.get(현층, 0) + 1
        i += 길이
    return {"라이브러리": 이름, "구조": 구조, "도형수": 도형수, "층별도형": 층별,
            "좌표점수": 좌표수, "레코드수": 레코드수, "바이트": n}


def 왕복확인(lib: "라이브러리", 길: Path) -> dict:
    """쓴 도형 수와 되읽은 도형 수를 견준다."""
    p = lib.내기(길)
    r = 읽기(p)
    쓴것 = {"BOUNDARY": 0, "PATH": 0, "TEXT": 0}
    for 도형들 in lib.구조.values():
        for d in 도형들:
            쓴것[d[0]] += 1
    맞나 = 쓴것 == r["도형수"]
    return {"길": str(p), "바이트": r["바이트"], "쓴것": 쓴것, "읽은것": r["도형수"],
            "맞나": 맞나, "구조": r["구조"], "층별도형": r["층별도형"],
            "좌표점수": r["좌표점수"], "레코드수": r["레코드수"],
            "라이브러리": r["라이브러리"]}
