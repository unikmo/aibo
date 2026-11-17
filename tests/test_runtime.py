import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('aibo',ROOT/'runtime/aibo.py')
aibo=importlib.util.module_from_spec(spec)
spec.loader.exec_module(aibo)

class RuntimeTests(unittest.TestCase):
    def test_roster(self):
        roster=aibo.load_json(aibo.ROSTER)
        self.assertEqual(len(roster['specialists']),11)
        self.assertEqual(len({x['id'] for x in roster['specialists']}),11)
        self.assertEqual(roster['coordinator']['id'],'soni')
    def test_projects_and_packs(self):
        registry=aibo.load_json(aibo.REGISTRY)
        self.assertGreaterEqual(len(registry['projects']),15)
        for item in registry['projects']:
            mapping=item['classification']
            self.assertTrue(mapping['industry'])
            self.assertIn(mapping['status'],('confirmed','provisional','pending-pack'))
            self.assertTrue(aibo.context(item))
            if mapping['status']=='pending-pack':
                self.assertIsNone(mapping['corePack'])
    def test_mock_orchestration_and_qa(self):
        result=aibo.execute('locksmith-boston','Review SEO opportunities',provider='mock',agents=['growth','research'])
        self.assertEqual(result['agents'],['growth','research','quality'])
        self.assertIn('MOCK',result['soni'])
        self.assertFalse(result['externalActionsExecuted'])
        self.assertEqual(result['actionGate'],'internal-only')
    def test_gated_action_is_never_executed(self):
        result=aibo.execute('unikmo','Send outreach email and publish offers',provider='mock',agents=['sales'])
        self.assertEqual(result['actionGate'],'approval-required')
        self.assertEqual(result['decisionPackage']['status'],'APPROVAL_REQUIRED')
        self.assertFalse(result['externalActionsExecuted'])
    def test_unknown_project_agent_and_path(self):
        with self.assertRaises(aibo.AiboError):aibo.project_info('other-company')
        with self.assertRaises(aibo.AiboError):aibo.execute('unikmo','Plan',agents=['invalid'])
        with self.assertRaises(aibo.AiboError):aibo.safe_path('../../etc/passwd')
    def test_no_null_bytes_in_active_markdown(self):
        for f in [ROOT/'AGENTS.md',* (ROOT/'Projects').glob('*/AIBO-PROJECT-OVERVIEW.md')]:
            self.assertNotIn(b'\x00',f.read_bytes(),str(f))
    def test_agent_descriptions_for_both_hosts(self):
        for x in aibo.load_json(aibo.ROSTER)['specialists']:
            self.assertTrue((ROOT/'.claude/agents'/(x['id']+'.md')).exists())
            self.assertTrue((ROOT/'.codex/agents'/(x['id']+'.md')).exists())
    def test_no_api_keys_bundled(self):
        for f in ROOT.rglob('*.json'):
            if 'Legacy' not in f.parts:
                self.assertNotIn('sk-proj-',f.read_text(errors='replace'))

if __name__=='__main__':unittest.main()

class RoutingTests(unittest.TestCase):
    def test_auto_route(self):
        result=aibo.execute('hccontroller','Research SEO and pricing for product',provider='mock')
        self.assertIn('growth',result['agents'])
        self.assertIn('finance',result['agents'])
        self.assertEqual(result['agents'][-1],'quality')
    def test_booking_action_gated(self):
        self.assertEqual(aibo.classify_action('Review bookings and approve pricing'),'approval-required')
