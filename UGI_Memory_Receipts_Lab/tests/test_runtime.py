import json,tempfile,unittest
from pathlib import Path
from p5memory import Memory, PolicyError
from p5memory.run_lab import execute
class RuntimeTests(unittest.TestCase):
 def test_sqlite_in_memory_rejected(self):
  with self.assertRaisesRegex(PolicyError,'IN_MEMORY_CONNECTIONS'):Memory(':memory:')
 def test_report_scenarios_genuine_and_pass(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'r.json';self.assertEqual(execute(path),0)
   report=json.loads(path.read_text());self.assertEqual(report['pass'],17)
   self.assertEqual(report['fail'],0)
   self.assertFalse(report['has_real_falkordb_integration'])
 def test_report_exposes_external_action_gap(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'r.json';execute(p);r=json.loads(p.read_text())
   self.assertFalse(r['external_action_atomicity_proven'])
   self.assertTrue(r['no_external_actions_available'])
if __name__=='__main__':unittest.main()
