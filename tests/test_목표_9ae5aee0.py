import sys
import unittest
import latex_formatter

class TestLatexRendering(unittest.TestCase):
    def test_latex_formatter_works(self):
        res = latex_formatter.format_latex("E = mc^2")
        self.assertIn("E = mc^2", res)

if __name__ == '__main__':
    unittest.main()
