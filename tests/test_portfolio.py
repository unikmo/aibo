import os
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import products, portfolio, workspace

class PortfolioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.original=(products.STATE,workspace.DIR,workspace.RUNS_DIR,portfolio.KPI_FILE)
        products.STATE=Path(self.tmp.name);workspace.DIR=products.STATE/'workspaces';workspace.RUNS_DIR=products.STATE/'runs';portfolio.KPI_FILE=products.STATE/'portfolio-kpis.json'
    def tearDown(self):
        products.STATE,workspace.DIR,workspace.RUNS_DIR,portfolio.KPI_FILE=self.original
        self.tmp.cleanup()
    def test_real_project_counts_and_unknown_health(self):
        view=portfolio.overview()
        self.assertGreaterEqual(view['counts']['projects'],15)
        self.assertEqual(view['counts']['completed'],0)
        self.assertIsNone(view['businessHealth']);self.assertIsNone(view['pendingApprovals'])
        self.assertEqual(len(view['projects']),view['counts']['projects'])
    def test_kpi_source_and_persistence(self):
        p=products.custom_projects()[0]
        item=portfolio.save_kpi(p['id'],{'name':'Leads','value':'12','unit':'leads','source':'CRM export'})
        view=portfolio.overview()
        loaded=next(x for x in view['projects'] if x['id']==p['id'])['kpis']
        self.assertEqual(loaded[0]['id'],item['id']);self.assertEqual(loaded[0]['source'],'CRM export')
    def test_unknown_project_cannot_write(self):
        with self.assertRaises(products.ProductError):
            portfolio.save_kpi('not-a-project',{'name':'Leads','value':'12','source':'manual'})
    def test_run_count_from_saved_ledger_only(self):
        p=products.custom_projects()[0]
        products.write_json(workspace.RUNS_DIR/'job.json',{'id':'job','project':p['id'],'task':'Audit','status':'completed','createdAt':'2026-11-12T01:00:00Z'})
        products.write_json(workspace.RUNS_DIR/'invalid.json',{'id':'x','project':'not-a-project','status':'completed'})
        self.assertEqual(portfolio.overview()['counts']['completed'],1)
