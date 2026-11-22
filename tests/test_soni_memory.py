"""Soni memory and cross-project safeguards: no providers or paid calls."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from runtime import products, soni_memory, workspace, aibo

class SoniMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state=Path(self.temp.name)
        self.patch=patch.object(products,'STATE',self.state)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        records=products.project_records()
        self.primary=next(x for x in records if x['name']=='Auditdefend')
        self.other=next(x for x in records if x['name']=='Politangle')

    def test_comparison_requires_explicit_intent(self):
        self.assertIsNone(soni_memory.comparison_scope(self.primary['id'],
            'Review Politangle development status'))
        self.assertEqual(soni_memory.comparison_scope(self.primary['id'],
            'Compare Auditdefend and Politangle using owner-reviewed facts'),[self.other['id']])
        self.assertEqual(soni_memory.comparison_scope(self.primary['id'],
            'Review the current project'),[])

    def test_comparison_uses_only_reviewed_fields_not_private_history(self):
        pid=self.other['id']
        private='VERY-PRIVATE-PROJECT-NOTE'
        folder=self.state/'workspaces'
        folder.mkdir(parents=True)
        (folder/(pid+'.json')).write_text(json.dumps({
            'complete':True,'reviewed':True,
            'fields':{'name':'Politangle','goal':'Improve political literacy','audience':'Schools',
                      'notes':private},
            'sourceEvidence':[{'excerpt':'PRIVATE-EVIDENCE-SOURCE'}]}),encoding='utf-8')
        (self.state/'soni-memory').mkdir()
        (self.state/'soni-memory'/(pid+'.json')).write_text(
            json.dumps({'entries':[{'text':'PRIVATE-CHAT-HISTORY'}]}),encoding='utf-8')
        ctx=soni_memory.comparison_context([pid])
        self.assertIn('Improve political literacy',ctx)
        for leak in (private,'PRIVATE-EVIDENCE-SOURCE','PRIVATE-CHAT-HISTORY'):
            self.assertNotIn(leak,ctx)

    def test_unreviewed_project_gives_unknown_not_unverified_business_claims(self):
        context=soni_memory.comparison_context([self.other['id']])
        self.assertIn('NO_OWNER_REVIEWED_SUMMARY',context)

    def test_memory_is_isolated_persistent_and_bounded(self):
        pid=self.primary['id']
        other=self.other['id']
        for i in range(35):
            soni_memory.remember(pid,'Question '+str(i),'Answer '+str(i))
        memory=soni_memory.memory_state(pid)
        self.assertLessEqual(len(memory['entries']),12)
        self.assertEqual(memory['completedTurns'],35)
        self.assertEqual(memory['compactedTurns'],23)
        self.assertEqual(soni_memory.memory_state(other)['entries'],[])
        context,meta=soni_memory.previous_context(pid,self.state/'runs')
        self.assertLessEqual(len(context),soni_memory.MAX_CONTEXT_CHARS)
        self.assertGreater(meta['compactedTurns'],0)

    def test_explicit_owner_instruction_survives_older_turn_compaction(self):
        pid=self.primary['id']
        soni_memory.remember(pid,'Always require approval before spending','Acknowledged')
        for i in range(30):
            soni_memory.remember(pid,'Routine question '+str(i),'Routine answer '+str(i))
        ctx,meta=soni_memory.previous_context(pid,self.state/'runs')
        self.assertIn('Always require approval before spending',ctx)
        self.assertLessEqual(len(ctx),soni_memory.MAX_CONTEXT_CHARS)

    def test_comparison_never_writes_to_either_memory(self):
        before=soni_memory.memory_state(self.primary['id'])
        soni_memory.remember(self.primary['id'],'Compare','Other project response',cross_project=True)
        after=soni_memory.memory_state(self.primary['id'])
        self.assertEqual(before,after)
        self.assertEqual(soni_memory.memory_state(self.other['id'])['entries'],[])

    def test_comparison_is_available_for_same_chat_followup_not_permanent_memory(self):
        pid=self.primary['id']
        run_dir=self.state/'runs'
        run_dir.mkdir()
        (run_dir/'11111111-1111-4111-8111-111111111111.json').write_text(
            json.dumps({'project':pid,'status':'completed',
                        'createdAt':'2026-11-22T18:00:00+00:00',
                        'crossProjectReadOnly':True,
                        'task':'Compare Auditdefend with Politangle',
                        'result':{'soni':'Both have separate business goals.'}}),encoding='utf-8')
        context,usage=soni_memory.previous_context(pid,run_dir)
        self.assertIn('Read-only cross-project comparison',context)
        self.assertIn('Both have separate business goals',context)
        self.assertEqual(soni_memory.memory_state(pid)['entries'],[])
        self.assertEqual(soni_memory.memory_state(self.other['id'])['entries'],[])

    def test_local_memory_cannot_elevate_or_read_another_project(self):
        pid=self.primary['id']
        other=self.other['id']
        soni_memory.remember(other,'An unrelated project question',
                             'Confidential unrelated response')
        context,meta=soni_memory.previous_context(pid,self.state/'runs')
        self.assertNotIn('Confidential',context)

if __name__=='__main__':
    unittest.main()
