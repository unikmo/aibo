import unittest,tempfile,csv,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'runtime'))
import gsi_research
class GsiTests(unittest.TestCase):
    def test_schema_exists(self):
        import json
        x=json.loads(gsi_research.SCHEMA.read_text(encoding='utf8'))
        self.assertEqual(len(x['datasets']['master']['columns']),67)
        self.assertEqual(len(x['datasets']['coverage']['columns']),6)
    def test_explicit_nulls_and_append_only(self):
        import json
        fields=json.loads(gsi_research.SCHEMA.read_text(encoding='utf8'))['datasets']['ledger']['columns']
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.csv'
            with p.open('w',newline='',encoding='utf8') as f:
                w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerow({'master_record_id':'ABC','outstanding_material_claims':'Closing unknown','amount_scope':'TOTAL_ROUND_NOT_SWF'})
            report=gsi_research.inspect_csv(p,'ledger')
            self.assertEqual(report['explicitNullTicketCount'],1)
            self.assertEqual(report['unresolvedClaimsCount'],1)
            first,_=gsi_research.stage({'ledger':p},Path(d)/'snapshots')
            second,_=gsi_research.stage({'ledger':p},Path(d)/'snapshots')
            self.assertNotEqual(first,second)
            self.assertTrue(Path(first,'ledger.csv').exists())
    def test_schema_rejects_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.csv';p.write_text('a,b\n1,2\n')
            with self.assertRaises(gsi_research.SchemaError):gsi_research.inspect_csv(p,'master')
if __name__=='__main__':unittest.main()
