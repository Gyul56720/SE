import json
import unittest
from pathlib import Path
from scripts.ledgerstat import analyze_repair, analyze_improve

class TestLedgerStat(unittest.TestCase):
    def setUp(self):
        self.r_file = Path("repair_test.jsonl")
        self.i_file = Path("improve_test.jsonl")
        
        with open(self.r_file, 'w') as f:
            f.write(json.dumps({"꼴": "조사", "바퀴": 1, "맞춘수": 2, "틀린수": 0, "막음": 0, "명령수": 5, "귀속": 0}) + "\n")
            
        with open(self.i_file, 'w') as f:
            f.write(json.dumps({"꼴": "부탁"}) + "\n")
            f.write(json.dumps({"꼴": "부탁"}) + "\n")

    def test_stats(self):
        r_stats = analyze_repair(self.r_file)
        self.assertEqual(r_stats["조사"]["바퀴"], 1)
        self.assertEqual(r_stats["조사"]["내탓"], 1)
        
        i_stats = analyze_improve(self.i_file)
        self.assertEqual(i_stats["부탁"], 2)

    def tearDown(self):
        self.r_file.unlink()
        self.i_file.unlink()

if __name__ == "__main__":
    unittest.main()
