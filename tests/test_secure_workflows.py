import os, tempfile, unittest, json, urllib.parse
from pathlib import Path
from unittest import mock
from runtime import products, editorial, oauth_local, action_gateway, dependencies

class MockResponse:
    def __init__(self,obj,status=200):self.obj=obj;self.status=status
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def read(self,n=-1):return json.dumps(self.obj).encode()
class MockOpener:
    def __init__(self,obj):self.obj=obj;self.calls=[]
    def open(self,req,timeout=0):self.calls.append(req);return MockResponse(self.obj)

class Workflows(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.oldroot=products.STATE;products.STATE=Path(self.temp.name)
        self.oldpath=action_gateway.PATH;action_gateway.PATH=products.STATE/'prepared.json'
        self.addCleanup(lambda: setattr(products,'STATE',self.oldroot))
        self.addCleanup(lambda: setattr(action_gateway,'PATH',self.oldpath))
        self.project=products.custom_projects()[0]['id']
    def test_editorial_flags_and_localization(self):
        result=editorial.review({'project':self.project,'locale':'pt-BR','text':'In today’s fast-paced world, this is a game-changer!','audience':'Brazilian adults'})
        self.assertEqual(result['locale'],'pt-BR');self.assertFalse(result['readyToPublish'])
        self.assertTrue(result['flags'])
    def test_oauth_pkce_state_and_token_refresh(self):
        with mock.patch.dict(os.environ,{'AIBO_BUFFER_CLIENT_ID':'local-test-client'}):
            r=oauth_local.begin(self.project)
        q=urllib.parse.parse_qs(urllib.parse.urlsplit(r['authorizationUrl']).query)
        self.assertEqual(q['code_challenge_method'],['S256'])
        state=q['state'][0]
        opener=MockOpener({'access_token':'test-token','refresh_token':'refresh-test','expires_in':3600})
        c=oauth_local.callback({'state':[state],'code':['test-code']},opener)
        self.assertEqual(c['project'],self.project)
        self.assertEqual(oauth_local.token(self.project),'test-token')
        with self.assertRaises(products.ProductError):oauth_local.callback({'state':[state],'code':['reuse']},opener)
        oauth_local.TOKENS.pop(self.project,None)
    def test_approval_one_use_and_browser_mock(self):
        params={'url':'https://example.com/page','action':'click','selector':'#menu'}
        with mock.patch.dict(os.environ,{'AIBO_BROWSER_ALLOWED_HOSTS':'example.com'}):
            item=action_gateway.prepare(self.project,'browser-interact',params)
        with self.assertRaises(Exception):action_gateway.execute(item['id'],browser_runner=lambda x:{'ok':True})
        action_gateway.approve_action(item['id'],'I APPROVE THIS SPECIFIC ACTION')
        out=action_gateway.execute(item['id'],browser_runner=lambda x:{'ok':True})
        self.assertEqual(out['status'],'completed')
        with self.assertRaises(products.ProductError):action_gateway.execute(item['id'],browser_runner=lambda x:{'ok':True})
    def test_buffer_action_approved_but_not_published_claim(self):
        info=action_gateway.prepare(self.project,'buffer-post',{'channelId':'channel42','text':'New post','mode':'addToQueue'})
        action_gateway.approve_action(info['id'],'I APPROVE THIS SPECIFIC ACTION')
        op=MockOpener({'data':{'createPost':{'post':{'id':'post_001','status':'buffer'}}}})
        with mock.patch.dict(os.environ,{'BUFFER_ACCESS_TOKEN':'test-token'}):
            result=action_gateway.execute(info['id'],opener=op)
        self.assertEqual(result['status'],'submitted')
        self.assertFalse(result['result']['published'])
    def test_vercel_no_production_and_no_hook(self):
        with mock.patch.dict(os.environ,{},clear=True):
            with self.assertRaises(products.ProductError):action_gateway.prepare(self.project,'vercel-deploy-hook',{})
        with mock.patch.dict(os.environ,{'AIBO_VERCEL_PREVIEW_HOOK':'https://api.vercel.com/v1/integrations/deploy/prj_x/secret'}):
            item=action_gateway.prepare(self.project,'vercel-deploy-hook',{})
            action_gateway.approve_action(item['id'],'I APPROVE THIS SPECIFIC ACTION')
            out=action_gateway.execute(item['id'],opener=MockOpener({'job':{'id':'job_1','state':'PENDING'}}))
            self.assertEqual(out['status'],'submitted')
            self.assertFalse(out['result']['deployed'])
    def test_resend_requires_explicit_approval(self):
        details={'to':'a@example.com','from':'b@example.com','subject':'Test','text':'Hello'}
        item=action_gateway.prepare(self.project,'resend-email',details)
        with self.assertRaises(Exception):action_gateway.execute(item['id'],opener=MockOpener({'id':'email_1'}))

if __name__=='__main__':unittest.main()
