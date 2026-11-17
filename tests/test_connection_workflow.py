import os
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from runtime import connection_runtime, connector_catalog, dependencies, products, workspace

class Reply:
    status=200
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n):return b'{}'
class Opener:
    def __init__(self):self.requests=[]
    def open(self,request,timeout):
        self.requests.append((request.full_url, request.get_method(), timeout))
        return Reply()
class ConnectionWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old=(products.STATE,connection_runtime.STATE,dependencies.PATH,workspace.DIR,workspace.RUNS_DIR)
        root=Path(self.tmp.name)
        products.STATE=root
        connection_runtime.STATE=root/'verified.json'
        dependencies.PATH=root/'dependencies.json'
        workspace.DIR=root/'workspaces'
        workspace.RUNS_DIR=root/'runs'
        self.addCleanup(self.restore)
        self.pid=products.custom_projects()[0]['id']
        products.write_json(workspace.DIR/(self.pid+'.json'), {'complete':True,'reviewed':True,'step':2,'fields':{'name':'Test','region':'DE','goal':'Test goal','audience':'Readers','successMeasure':'Leads'},'savedAt':workspace.now()})
    def restore(self):
        products.STATE,connection_runtime.STATE,dependencies.PATH,workspace.DIR,workspace.RUNS_DIR=self.old
    def test_language_services_present(self):
        names={x['name'] for x in connector_catalog.entries()}
        for name in ('DeepL API','Lokalise','Crowdin','Weglot','Google Cloud Translation','Microsoft Azure AI Translator'):
            self.assertIn(name,names)
    def test_missing_service_blocks_and_records_request(self):
        with patch.object(connector_catalog,'request_connection',return_value={'ok':True}):
            item=dependencies.queue({'project':self.pid,'task':'Check our GitHub repository','provider':'mock','connector':'github'})
        self.assertEqual(item['status'],'waiting-for-connection')
        with self.assertRaises(products.ProductError):dependencies.resume(item['id'])
    def test_verify_fixed_read_only_endpoint_and_resume(self):
        fake=Opener()
        with patch.dict(os.environ,{'GITHUB_TOKEN':'test-secret'}):
            result=connection_runtime.verify(self.pid,'github',opener=fake)
            self.assertTrue(result['verified'])
            self.assertEqual(fake.requests[0],('https://api.github.com/user','GET',10))
            self.assertNotIn('test-secret',str(result))
            item=dependencies.queue({'project':self.pid,'task':'Analyze GitHub code issues','provider':'mock','connector':'github'})
            self.assertEqual(item['status'],'ready-to-run')
            response=dependencies.resume(item['id'])
            self.assertEqual(response['status'],'submitted')
            self.assertEqual(dependencies.resume(item['id'])['runId'],response['runId'])
            for _ in range(200):
                if workspace.run_status(response['runId'])['status'] not in ('queued','running'):break
                time.sleep(0.01)
            self.assertNotIn(workspace.run_status(response['runId'])['status'],('queued','running'))
        self.assertFalse(connection_runtime.status(self.pid,'github')['verified'])
    def test_unimplemented_adapter_never_verified(self):
        result=connection_runtime.verify(self.pid,'weglot')
        self.assertFalse(result['verified'])
        self.assertEqual(result['status'],'setup-required')
    def test_deepl_translation_explicit_consent_and_fixed_endpoint(self):
        class TranslateReply:
            status=200
            def __enter__(self):return self
            def __exit__(self,*a):return False
            def read(self,n):return json.dumps({'translations':[{'text':'Bonjour'}]}).encode()
        class TranslateOpener:
            request=None
            def open(self,request,timeout):
                self.request=request
                self.timeout=timeout
                return TranslateReply()
        opener=TranslateOpener()
        with patch.dict(os.environ,{'DEEPL_API_KEY':'fake-key','DEEPL_API_TIER':'free'}):
            with self.assertRaises(products.ProductError):
                connection_runtime.translate(self.pid,'Hello','EN','FR',False,opener)
            result=connection_runtime.translate(self.pid,'Hello','EN','FR',True,opener)
        self.assertEqual(result['text'],'Bonjour')
        self.assertTrue(result['needsHumanReview'])
        self.assertEqual(opener.request.full_url,'https://api-free.deepl.com/v2/translate')
        self.assertEqual(opener.request.get_method(),'POST')
        self.assertNotIn('fake-key',str(result))
    def test_unknown_project_rejected(self):
        with self.assertRaises(products.ProductError):
            connection_runtime.verify('not-existing','github')
    def test_inference(self):
        self.assertEqual(dependencies.infer_connector('Deploy on Vercel'),'vercel')
        self.assertIsNone(dependencies.infer_connector('Summarize our market'))
if __name__=='__main__':unittest.main()
