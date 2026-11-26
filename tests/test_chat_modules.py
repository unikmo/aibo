"""Real CariFive module selection must affect specialist execution, not only UI labels."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime import workspace, products


class ChatModuleRoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state=Path(self.temp.name)
        patches=[
            patch.object(products,'STATE',self.state),
            patch.object(workspace,'DIR',self.state/'workspaces'),
            patch.object(workspace,'RUNS_DIR',self.state/'runs')
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        workspace.CURRENT.clear()
        self.project='standard-slot-1'
        workspace.save_setup(self.project,{'step':2,
            'fields':{'name':'Test Business','goal':'Launch a service','region':'Germany'},
            'complete':True})

    def test_explicit_module_maps_to_actual_specialists(self):
        expected={
            'build':['engineering','automation'],
            'marketing':['growth','content','sales'],
            'analysis':['research','finance'],
            'complete':['research','engineering','growth','content'],
        }
        for module,agents in expected.items():
            with self.subTest(module=module):
                self.assertEqual(workspace.specialists_for_module(module,'Review this project'),agents)

    def test_module_routing_is_persisted_and_used_in_actual_mock_execution(self):
        for module,expected in [
            ('build',['engineering','automation']),
            ('marketing',['growth','content','sales']),
            ('analysis',['research','finance']),
            ('complete',['research','engineering','growth','content']),
        ]:
            with self.subTest(module=module):
                result=workspace.start_run(self.project,{
                    'task':'Review our business priorities','provider':'mock','module':module})
                record=workspace.run_status(result['id'])
                self.assertEqual(record['status'],'completed',record.get('error'))
                self.assertEqual(record['module'],module)
                self.assertEqual(record['result']['agents'],expected+['quality'])
                self.assertFalse(record['externalActionsExecuted'])

    def test_invalid_module_fails_before_queueing_any_work(self):
        with self.assertRaisesRegex(products.ProductError,'Unknown CariFive module'):
            workspace.start_run(self.project,{
                'task':'Review our business priorities','provider':'mock','module':'unauthorized'})
        self.assertEqual(workspace.recent_runs(self.project),[])

    def test_auto_retains_keyword_routing_and_default_backwards_compatibility(self):
        result=workspace.start_run(self.project,{
            'task':'Review marketing campaign opportunities','provider':'mock'})
        item=workspace.run_status(result['id'])
        self.assertEqual(item['module'],'auto')
        self.assertIn('growth',item['result']['agents'])
        self.assertIn('quality',item['result']['agents'])

    def test_paid_provider_still_requires_explicit_consent_even_with_module(self):
        with self.assertRaisesRegex(products.ProductError,'consent'):
            workspace.start_run(self.project,{
                'task':'Review the positioning','provider':'openai','module':'marketing'})


if __name__=='__main__':
    unittest.main()
