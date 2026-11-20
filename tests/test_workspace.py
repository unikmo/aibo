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

    def test_other_project_reference_is_blocked_without_queuing_or_ai(self):
        self._ready()
        with patch('runtime.workspace.aibo.execute') as ai:
            with self.assertRaisesRegex(products.ProductError,'Project mismatch: Politangle'):
                workspace.start_run(self.id,{'task':"Review Politangle's current development status using its actual project sources.",'provider':'auto'})
        self.assertFalse(workspace.recent_runs(self.id))
        ai.assert_not_called()

    def test_selected_project_name_is_allowed(self):
        self._ready()
        self.assertEqual(workspace._cross_project_names(self.id,"Review Auditdefend's source records"),[])

    def test_old_queued_job_expires_instead_of_waiting_forever(self):
        self._ready()
        import datetime as dt
        from datetime import timezone, timedelta
        run_id='22222222-2222-4222-8222-222222222222'
        queued={'id':run_id,'project':self.id,'task':'Review records','provider':'codex-local',
            'status':'queued','sessionId':workspace.SESSION_ID,
            'createdAt':(dt.datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),
            'updatedAt':workspace.now(),'result':None,'error':None}
        workspace._save_run(queued)
        workspace.CURRENT[self.id]=run_id
        result=workspace.run_status(run_id)
        self.assertEqual(result['status'],'failed')
        self.assertIn('task limit',result['error'])
        self.assertNotIn(self.id,workspace.CURRENT)

    def test_timed_out_run_cannot_be_resurrected_by_late_worker(self):
        self._ready()
        run_id='44444444-4444-4444-8444-444444444444'
        stale={'id':run_id,'project':self.id,'status':'running',
               'sessionId':workspace.SESSION_ID,'updatedAt':'old-timestamp'}
        workspace._save_run(stale)
        self.assertTrue(workspace._expire_run(run_id))
        workspace._save_run(stale)
        final=workspace.run_status(run_id)
        self.assertEqual(final['status'],'failed')
        self.assertIn('task limit',final['error'])

    def test_watchdog_does_not_overwrite_completed_or_interrupted_jobs(self):
        self._ready()
        run_id='33333333-3333-4333-8333-333333333333'
        for status in ('completed','interrupted'):
            record={'id':run_id,'project':self.id,'status':status,
                'sessionId':workspace.SESSION_ID,'updatedAt':workspace.now()}
            workspace._save_run(record)
            self.assertFalse(workspace._expire_run(run_id))
            self.assertEqual(workspace.run_status(run_id)['status'],status)

    def test_factual_status_does_not_invent_project_progress(self):
        self._ready()
        with patch('runtime.workspace.aibo.execute') as external_ai:
            result=workspace.start_run(self.id,{'task':'What is the status of this project?','provider':'mock'})
            completed=workspace.run_status(result['id'])
        self.assertEqual(completed['status'],'completed')
        self.assertEqual(completed['effectiveProvider'],'local-records')
        self.assertIn('cannot be confirmed',completed['result']['soni'])
        self.assertNotIn('blocked',completed['result']['soni'])
        external_ai.assert_not_called()

    def test_ambiguous_outreach_does_not_invent_abas_or_claim_no_outreach(self):
        self._ready()
        with patch('runtime.workspace.aibo.execute') as external_ai:
            result=workspace.start_run(self.id,{'task':'Have we reached out to some ABAs?','provider':'mock'})
            completed=workspace.run_status(result['id'])
        self.assertEqual(completed['status'],'completed')
        self.assertIn('What does “ABAs” refer to',completed['result']['soni'])
        self.assertNotIn('Applied Behavior Analysts',completed['result']['soni'])
        self.assertNotIn('no outreach has',completed['result']['soni'].lower())
        external_ai.assert_not_called()

    def test_unexpected_exception_never_exposes_secret_in_run_record(self):
        self._ready()
        with patch('runtime.workspace.aibo.execute',side_effect=Exception(
                'Invalid api key sk-proj-SECRET-EXAMPLE in a provider error')):
            result=workspace.start_run(self.id,{'task':'Review market positioning','provider':'mock'})
            completed=workspace.run_status(result['id'])
        self.assertEqual(completed['status'],'failed')
        self.assertNotIn('SECRET',completed['error'])
        self.assertIn('Execution failed',completed['error'])

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
