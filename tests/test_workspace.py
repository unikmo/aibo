import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from runtime import workspace, products, aibo

class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state=Path(self.temp.name)
        self.state.mkdir(exist_ok=True)
        self.patches=[patch.object(products,'STATE',self.state),patch.object(workspace,'DIR',self.state/'workspaces'),patch.object(workspace,'RUNS_DIR',self.state/'runs'),patch.dict(os.environ,{'AIBO_STATE_DIR':self.temp.name})]
        for p in self.patches:p.start();self.addCleanup(p.stop)
        self.id=products.custom_projects()[0]['id']
        workspace.CURRENT.clear()

    def test_guided_resume_and_complete(self):
        setup=workspace.save_setup(self.id,{'step':0,'fields':{'name':'Reviewed name','region':'Boston'}})
        self.assertFalse(setup['complete'])
        self.assertEqual(workspace.setup_state(self.id)['fields']['name'],'Reviewed name')
        setup=workspace.save_setup(self.id,{'step':1,'fields':{'goal':'Improve organic visibility','audience':'Property managers','successMeasure':'10 inbound leads'}})
        self.assertFalse(setup['complete'])
        completed=workspace.save_setup(self.id,{'step':2,'fields':{},'complete':True})
        self.assertTrue(completed['complete'])
        self.assertTrue(products.custom_projects()[0]['setupComplete'])
        self.assertIn('OWNER-REVIEWED CURRENT SETUP', aibo.context(aibo.project_info(self.id)))
        updated=workspace.save_setup(self.id,{'step':1,'fields':{'goal':'A changed goal'}})
        self.assertFalse(updated['complete'])

    def test_uninitialized_run_denied(self):
        with self.assertRaisesRegex(products.ProductError,'Finish the guided'):
            workspace.start_run(self.id,{'task':'Review the existing page','provider':'mock'})

    def test_consent_required_for_nonmock(self):
        self._ready()
        with self.assertRaisesRegex(products.ProductError,'consent'):
            workspace.start_run(self.id,{'task':'Research the market','provider':'openai'})

    def test_soni_mock_run(self):
        self._ready()
        created=workspace.start_run(self.id,{'task':'Review market positioning','provider':'mock'})
        self.assertEqual(created['project'],self.id)
        import time
        for _ in range(70):
            result=workspace.run_status(created['id'])
            if result['status'] not in ('queued','running'):break
            time.sleep(.05)
        self.assertEqual(result['status'],'completed',result.get('error'))
        self.assertFalse(result['externalActionsExecuted'])
        self.assertEqual(result['result']['externalActionsExecuted'],False)
        self.assertIn('quality', result['result']['agents'])
        self.assertTrue(workspace.recent_runs(self.id))

    def test_cannot_modify_pack_during_setup(self):
        with self.assertRaisesRegex(products.ProductError,'Unknown setup field'):
            workspace.save_setup(self.id,{'step':1,'fields':{'corePack':'unauthorized'}})

    def _ready(self):
        return workspace.save_setup(self.id,{'step':2,'fields':{'name':'Test Business','region':'Boston','goal':'Improve sales','audience':'Property managers','successMeasure':'10 leads'},'complete':True})

if __name__=='__main__':unittest.main()
