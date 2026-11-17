import unittest, tempfile, json
from pathlib import Path
from runtime.gsi_initialize import initialize
class TestGSIInitialization(unittest.TestCase):
    def test_queue_and_idempotence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'queue.json';first=initialize(p);self.assertEqual(first['months'],83)
            data=json.loads(p.read_text(encoding='utf8'))
            self.assertEqual(data['months'][0]['period'],'2020-01')
            self.assertEqual(data['months'][-1]['period'],'2026-11')
            self.assertTrue(all(m['coverage']=='UNASSESSED' for m in data['months']))
            self.assertEqual(initialize(p)['result'],'existing_preserved')
            self.assertEqual(len(json.loads(p.read_text(encoding='utf8'))['months']),83)
if __name__=='__main__':unittest.main()
