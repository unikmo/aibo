import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import operations as o
from aibo import AiboError

class TestOperations(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name)/'project'
        self.work.mkdir()
        self.state=Path(self.temp.name)/'private-state'
        self.state.mkdir()
        self.patcher=patch.object(o,'STATE',self.state)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_roster_and_projects(self):
        from aibo import load_json, ROSTER, REGISTRY, context
        self.assertEqual(len(load_json(ROSTER)['specialists']),11)
        projects=load_json(REGISTRY)['projects']
        self.assertGreaterEqual(len(projects),15)
        for proj in projects:
            self.assertTrue(proj['classification']['industry'])
            self.assertIn(proj['classification']['status'],('confirmed','provisional','pending-pack'))
            self.assertIn('PROJECT:',context(proj))

    def test_p2_integrity(self):
        self.assertEqual(o.doctor()['nullByteMarkdown'],[])

    def test_path_traversal_symlinks_and_secrets(self):
        for path in ('../outside.py','/tmp/a.py','.env','credentials/.env.production','.git/config','file.exe'):
            with self.assertRaises(AiboError):o.safe_file(self.work,path)
        try:
            (self.work/'link.py').symlink_to(Path(self.temp.name)/'outside.py')
        except OSError as exc:
            if getattr(exc, 'winerror', None) == 1314:
                self.skipTest('Windows symlink privilege not granted; path traversal checks already passed')
            raise
        with self.assertRaises(AiboError):o.safe_file(self.work,'link.py')

    def test_patch_atomic_validation(self):
        p=self.work/'hello.py';p.write_text('old',encoding='utf-8')
        spec={'edits':[{'path':'hello.py','sha256':hashlib.sha256(b'old').hexdigest(),'content':'new'}]}
        patchfile=Path(self.temp.name)/'patch.json';patchfile.write_text(json.dumps(spec))
        result=o.apply_edits('politangle',str(self.work),patchfile,True)
        self.assertFalse(result['applied']);self.assertEqual(p.read_text(),'old')
        result=o.apply_edits('politangle',str(self.work),patchfile)
        self.assertTrue(result['applied']);self.assertEqual(p.read_text(),'new')
        with self.assertRaises(AiboError):o.apply_edits('politangle',str(self.work),patchfile)

    def test_invalid_patch_prevents_partial_changes(self):
        p=self.work/'hello.py';p.write_text('old',encoding='utf-8')
        patchfile=Path(self.temp.name)/'bad.json'
        patchfile.write_text(json.dumps({'edits':[{'path':'hello.py','sha256':hashlib.sha256(b'old').hexdigest(),'content':'new'}, {'path':'bad.py','sha256':'wrong','content':'bad'}]}))
        with self.assertRaises(AiboError):o.apply_edits('politangle',str(self.work),patchfile)
        self.assertEqual(p.read_text(),'old')

    def test_approval_exact_scope_single_use(self):
        params={'project':'politangle','workspace':str(self.work),'environment':'preview'}
        req=o.approval_request('deploy-preview',params)
        with self.assertRaises(AiboError):o.consume(req['id'],'deploy-preview',params)
        with self.assertRaises(AiboError):o.approve(req['id'],'yes')
        o.approve(req['id'],'I APPROVE THIS SPECIFIC ACTION')
        with self.assertRaises(AiboError):o.consume(req['id'],'deploy-production',params)
        o.consume(req['id'],'deploy-preview',params)
        with self.assertRaises(AiboError):o.consume(req['id'],'deploy-preview',params)

    def test_deploy_rejects_unlinked(self):
        with self.assertRaisesRegex(AiboError,'not linked'):
            o.deploy('politangle',str(self.work),'preview',approval=None)

    def test_browser_denies_non_https_and_unlisted(self):
        for url in ('http://example.org','https://other.org','file:///etc/passwd'):
            with self.assertRaises(AiboError):o.browser('inspect',url,'example.org')
        with self.assertRaises(AiboError):o.browser('click','https://example.org','example.org',selector='button')

    def test_http_requires_approval(self):
        with self.assertRaises(AiboError):o.integration('politangle','POST','https://api.example.org/submit','api.example.org',payload={'a':1})
        with self.assertRaises(AiboError):o.integration('politangle','GET','https://evil.example.org','api.example.org')

    def test_code_agent_requires_git_workspace(self):
        with self.assertRaisesRegex(AiboError,'git'):
            o.code_agent('politangle',str(self.work),'codex-local','test')

    def test_provider_dispatch_mocked(self):
        (self.work/'.git').mkdir()
        with patch.object(o,'run_program',return_value={'returncode':0,'stdout':'done','stderr':'','verifiedExit':True}) as fake:
            result=o.code_agent('politangle',str(self.work),'codex-local','fix UI')
            self.assertTrue(result['process']['verifiedExit'])
            self.assertIn('workspace-write',fake.call_args.args[0])
        with patch.object(o,'run_program',return_value={'returncode':0,'stdout':'done','stderr':'','verifiedExit':True}) as fake:
            result=o.code_agent('politangle',str(self.work),'claude-local','fix UI')
            self.assertTrue(result['process']['verifiedExit'])
            self.assertIn('acceptEdits',fake.call_args.args[0])

if __name__=='__main__':unittest.main()

class TestConnectorGuards(unittest.TestCase):
    def test_reject_private_hosts(self):
        for hostname in ('localhost','127.0.0.1','169.254.169.254','10.0.0.5','example.local'):
            with self.assertRaises(AiboError):o.assert_public_host(hostname)
    def test_stripe_write_blocked(self):
        with self.assertRaisesRegex(AiboError,'Financial write'):
            o.integration('politangle','POST','https://api.stripe.com/v1/charges','api.stripe.com',payload={'amount':99})
