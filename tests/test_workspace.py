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

    def test_consent_required_for_api_provider(self):
        self._ready()
        with self.assertRaisesRegex(products.ProductError,'consent'):
            workspace.start_run(self.id,{'task':'Research the market','provider':'openai'})

    def test_local_code_agents_do_not_require_api_consent(self):
        self.assertFalse(workspace.requires_api_consent('codex-local'))
        self.assertFalse(workspace.requires_api_consent('claude-local'))
        self.assertTrue(workspace.requires_api_consent('openrouter'))

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

    def test_auto_fails_over_codex_to_claude_without_api(self):
        self._ready()
        import time
        calls=[]
        def execute(project,task,**kwargs):
            calls.append(kwargs['provider'])
            if len(calls)==1:
                raise aibo.AiboError('Local CLI failed (exit 1): unavailable')
            return {'soni':'CLAUDE_OK','externalActionsExecuted':False}
        ready={'ready':{'codex-local':True,'claude-local':True},
               'switchMode':'ask','models':{}}
        with patch('runtime.workspace.ai_providers.route',return_value=('codex-local',None)), \
             patch('runtime.workspace.ai_providers.public',return_value=ready), \
             patch('runtime.workspace.aibo.execute',side_effect=execute):
            created=workspace.start_run(self.id,{'task':'Review positioning','provider':'auto'})
            for _ in range(100):
                final=workspace.run_status(created['id'])
                if final['status'] not in ('queued','running'):break
                time.sleep(.02)
        self.assertEqual(final['status'],'completed',final.get('error'))
        self.assertEqual(calls,['codex-local','claude-local'])
        self.assertEqual(final['effectiveProvider'],'claude-local')
        self.assertEqual([a['status'] for a in final['providerAttempts']],['failed','completed'])

    def test_manual_codex_failure_does_not_fail_over(self):
        self._ready()
        import time
        with patch('runtime.workspace.aibo.execute',side_effect=aibo.AiboError('Local CLI failed (exit 1): unavailable')) as execution:
            created=workspace.start_run(self.id,{'task':'Review positioning','provider':'codex-local'})
            for _ in range(100):
                final=workspace.run_status(created['id'])
                if final['status'] not in ('queued','running'):break
                time.sleep(.02)
        self.assertEqual(final['status'],'failed')
        self.assertEqual(execution.call_count,1)

    def test_auto_does_not_use_api_as_fallback(self):
        self._ready()
        import time
        with patch('runtime.workspace.ai_providers.route',return_value=('codex-local',None)), \
             patch('runtime.workspace.ai_providers.public',return_value={'ready':{'codex-local':True,'claude-local':False},'switchMode':'ask','models':{}}), \
             patch('runtime.workspace.aibo.execute',side_effect=aibo.AiboError('Local CLI timeout')) as execution:
            created=workspace.start_run(self.id,{'task':'Review positioning','provider':'auto'})
            for _ in range(100):
                final=workspace.run_status(created['id'])
                if final['status'] not in ('queued','running'):break
                time.sleep(.02)
        self.assertEqual(final['status'],'failed')
        self.assertEqual(execution.call_count,1)

    def test_explicit_api_uses_selected_model_only_with_consent(self):
        self._ready()
        import time
        with patch('runtime.workspace.ai_providers.route',return_value=('openai','gpt-4.1-mini')), \
             patch('runtime.workspace.aibo.execute',return_value={'soni':'API_OK','externalActionsExecuted':False}) as execution:
            created=workspace.start_run(self.id,{'task':'Analyze positioning','provider':'openai','consent':True})
            for _ in range(100):
                final=workspace.run_status(created['id'])
                if final['status'] not in ('queued','running'):break
                time.sleep(.02)
        self.assertEqual(final['status'],'completed',final.get('error'))
        self.assertTrue(final['apiConsentGranted'])
        self.assertEqual(execution.call_args.kwargs['provider'],'openai')
        self.assertEqual(execution.call_args.kwargs['model'],'gpt-4.1-mini')
        self.assertEqual(final['providerAttempts'][0]['provider'],'openai')

    def test_cannot_modify_pack_during_setup(self):
        with self.assertRaisesRegex(products.ProductError,'Unknown setup field'):
            workspace.save_setup(self.id,{'step':1,'fields':{'corePack':'unauthorized'}})

    def _ready(self):
        return workspace.save_setup(self.id,{'step':2,'fields':{'name':'Test Business','region':'Boston','goal':'Improve sales','audience':'Property managers','successMeasure':'10 leads'},'complete':True})

if __name__=='__main__':unittest.main()
