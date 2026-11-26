import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

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
    def test_real_provider_rejects_empty_specialist_output(self):
        with patch.object(aibo,'provider_call',return_value='   '):
            with self.assertRaisesRegex(aibo.AiboError,'empty or simulated specialist output'):
                aibo.execute('locksmith-boston','Evaluate SEO opportunities',provider='codex-local',agents=['research'])
    def test_real_provider_rejects_empty_synthesis(self):
        values=iter(['Useful research finding based on stated evidence.',
                     'Independent QA flags missing benchmarks and citations.',
                     ''])
        with patch.object(aibo,'provider_call',side_effect=lambda *args,**kwargs:next(values)):
            with self.assertRaisesRegex(aibo.AiboError,'empty or simulated final answer'):
                aibo.execute('locksmith-boston','Evaluate SEO opportunities',provider='codex-local',agents=['research'])
    def test_real_provider_does_not_pass_simulated_text_as_analysis(self):
        with patch.object(aibo,'provider_call',return_value='[MOCK RESPONSE: no model or external actions executed]'):
            with self.assertRaisesRegex(aibo.AiboError,'empty or simulated specialist output'):
                aibo.execute('locksmith-boston','Evaluate SEO opportunities',provider='codex-local',agents=['research'])
    def test_synthesis_depth_follows_real_task_instead_of_universal_short_limit(self):
        prompts=[]
        def provider(provider,system,user,model,timeout,limit):
            prompts.append(system)
            return 'This is a nonempty task-specific result with traceable actions.'
        with patch.object(aibo,'provider_call',side_effect=provider):
            aibo.execute('locksmith-boston','Prepare a detailed technical and SEO audit',provider='codex-local',agents=['engineering'])
        specialist,quality,coordinator=prompts
        self.assertIn('task-appropriate structure',specialist)
        self.assertIn('arbitrarily truncate substantive work',coordinator)
        self.assertIn('Markdown headings',coordinator)
        self.assertNotIn('45–90 words maximum',coordinator)
    def test_good_real_provider_result_remains_accepted(self):
        values=iter(['Evidence: existing homepage needs clear positioning; this is a recommendation, not a verified deployment.',
                     'QA: site changes have not been implemented; validate actual search visibility independently.',
                     'The current homepage positioning should be reviewed against user intent. A proposed improvement is a clearer headline; no changes have been deployed.'])
        with patch.object(aibo,'provider_call',side_effect=lambda *args,**kwargs:next(values)):
            result=aibo.execute('locksmith-boston','Evaluate SEO opportunities',provider='codex-local',agents=['research'])
        self.assertIn('no changes have been deployed',result['soni'])
        self.assertFalse(result['externalActionsExecuted'])
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
        # Native agent files are currently excluded from the source migration.
        # This check stays visible as a skip until the actual local files are
        # safely migrated; do not fabricate replacements or claim completeness.
        roster=aibo.load_json(aibo.ROSTER)['specialists']
        expected=[ROOT/folder/'agents'/(x['id']+'.md')
                  for folder in ('.claude','.codex') for x in roster]
        missing=[p for p in expected if not p.is_file()]
        if missing:
            self.skipTest(f'Native agent configs not migrated: {len(missing)}/{len(expected)} missing')
        for path in expected:
            self.assertGreater(path.stat().st_size,0,str(path))
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
