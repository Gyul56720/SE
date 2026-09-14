r"""부탁을 못박는다 -- "LaTeX 설치 없이 디스코드에서 방정식을 깔끔하게 본다".

**첫 판의 검사는 아무것도 안 붙들었다.** 이랬다.

    res = latex_formatter.format_latex("E = mc^2")
    self.assertIn("E = mc^2", res)

입력이 출력 어딘가에 들어 있기만 하면 통과다. 실측 2026-09-14, 함수를 셋으로 바꿔 심으니
**셋 다 통과**했다.

    return f                  아무 일도 안 한다
    return "XX" + f + "XX"    쓰레기를 붙인다
    return f + "\n"

그래서 "됐다" 는 초록불이 떴는데 부탁은 하나도 안 풀려 있었다(디스코드는 ```math 를
수식으로 안 그린다). 여기서는 **결과를 본다.**

실행: PYTHONPATH=. python3 tests/test_목표_9ae5aee0.py
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import latex_formatter as L  # noqa: E402


class 유니코드로그린다(unittest.TestCase):
    def test_분수가_분수로_보인다(self):
        r = L.유니코드(r"\frac{x^2+1}{\sqrt{y}}")
        self.assertTrue(r["됐나"], f"못 그렸다: {r['왜']}")
        글 = r["글"]
        # **원문이 아니라 그림이어야 한다** -- 항등 변형을 죽이는 자리다
        self.assertNotIn(r"\frac", 글, "LaTeX 명령이 그대로 남아 있다 -- 안 그린 것이다")
        self.assertIn("─", 글, "분수선이 없다")
        self.assertIn("√", 글, "근호가 없다")
        self.assertGreater(len(글.splitlines()), 1, "여러 줄로 쌓여야 분수다")

    def test_적분도_그린다(self):
        r = L.유니코드(r"\int_0^\infty e^{-t} dt")
        self.assertTrue(r["됐나"], f"못 그렸다: {r['왜']}")
        self.assertNotIn(r"\int", r["글"], "LaTeX 명령이 그대로 남아 있다")

    def test_못_읽으면_못했다고_한다(self):
        r = L.유니코드(r"\frac{{{{")
        self.assertFalse(r["됐나"], "깨진 수식을 됐다고 했다")
        self.assertTrue(r["왜"], "왜 못했는지 안 적었다")
        self.assertIsNone(r["글"])

    def test_빈것은_못잼이다(self):
        self.assertFalse(L.유니코드("")["됐나"])
        self.assertFalse(L.유니코드("   ")["됐나"])


class 디스코드글(unittest.TestCase):
    def test_코드펜스로_감싼다(self):
        글 = L.디스코드글(r"\frac{x^2+1}{\sqrt{y}}")
        # **감싼다는 것을 실제로 확인한다** -- 첫 판이 빠뜨린 자리
        self.assertTrue(글.startswith("```"), f"코드 펜스로 안 시작한다: {글[:20]!r}")
        self.assertTrue(글.rstrip().endswith("```"), "코드 펜스로 안 끝난다")
        self.assertGreaterEqual(글.count("```"), 2, "펜스가 짝이 안 맞는다")

    def test_math_펜스를_안_쓴다(self):
        # 디스코드는 ```math 를 수식으로 안 그린다 -- 쓰면 안 되는 것을 못박는다
        self.assertNotIn("```math", L.디스코드글(r"x^2"))

    def test_원문이_아니라_그림이_들어간다(self):
        원문 = r"\frac{x^2+1}{\sqrt{y}}"
        글 = L.디스코드글(원문)
        self.assertNotIn(원문, 글, "**원문이 그대로 들어 있다** -- 감싸기만 한 것이다")
        self.assertIn("─", 글, "그린 결과가 안 들어 있다")

    def test_못_그리면_그렇다고_적는다(self):
        글 = L.디스코드글(r"\frac{{{{")
        self.assertIn("못 그렸다", 글, "**조용히 원문을 수식인 척 내놓았다**")

    def test_뒤호환_이름도_같은_것을_한다(self):
        수식 = r"\frac{a}{b}"
        self.assertEqual(L.format_latex(수식), L.디스코드글(수식))


class 그림으로그린다(unittest.TestCase):
    def test_PNG_가_실제로_생긴다(self):
        r = L.그림(r"\frac{x^2+1}{\sqrt{y}}")
        self.assertTrue(r["됐나"], f"못 그렸다: {r['왜']}")
        self.assertTrue(os.path.isfile(r["경로"]), "파일이 없다")
        self.assertGreater(os.path.getsize(r["경로"]), 1000, "파일이 너무 작다 -- 빈 그림이다")
        with open(r["경로"], "rb") as f:
            self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n", "PNG 가 아니다")

    def test_LaTeX_설치_없이_그린다(self):
        import matplotlib
        # **이것이 이 부탁의 핵심이다** -- usetex 가 켜지면 LaTeX 설치가 필요해진다
        self.assertFalse(matplotlib.rcParams["text.usetex"],
                         "usetex 가 켜져 있다 -- LaTeX 설치가 필요해진다")

    def test_수식마다_다른_그림이_나온다(self):
        # 같은 그림만 내놓는(아무것도 안 그리는) 구현을 죽인다
        ㄱ = L.그림(r"x^2", 경로=os.path.join(self._판(), "ㄱ.png"))
        ㄴ = L.그림(r"\int_0^\infty \frac{e^{-t}}{\sqrt{t}} dt",
                  경로=os.path.join(self._판(), "ㄴ.png"))
        self.assertTrue(ㄱ["됐나"] and ㄴ["됐나"])
        self.assertNotEqual(open(ㄱ["경로"], "rb").read(), open(ㄴ["경로"], "rb").read(),
                            "**다른 수식인데 같은 그림이다**")

    def test_빈것은_못잼이다(self):
        self.assertFalse(L.그림("")["됐나"])

    def _판(self):
        if not hasattr(self, "_d"):
            import tempfile
            self._d = tempfile.mkdtemp(prefix="검사-수식-")
        return self._d


if __name__ == "__main__":
    unittest.main(verbosity=2)
