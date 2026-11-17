import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
try:
 from runtime import infra_actions as m
except ImportError:
 import infra_actions as m

class Response:
 def __init__(self,data,status=200):self.data=data;self.status=status
 def __enter__(self):return self
 def __exit__(self,*_):pass
 def read(self,n):return json.dumps(self.data).encode()

class Transport:
 def __init__(self,results):self.results=list(results);self.requests=[]
 def open(self,req,timeout=15):
  self.requests.append((req.get_method(),req.full_url,req.data))
  value=self.results.pop(0)
  if isinstance(value,Exception):raise value
  return Response(value)

class InfraTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
 def engine(self,transport=None):return m.Engine(Path(self.tmp.name)/'infra.json',transport)
 def args(self):return {'zone':'zoneABC123','record':{'name':'www','type':'A','content':'192.0.2.10','ttl':3600}}
 def approve(self,engine,rec):engine.approve(rec['id'],rec['approvalPhrase'])
 def test_unsupported_provider(self):
  with self.assertRaises(m.InfraError):self.engine().prepare('test','hosteurope','dns.create',self.args())
 def test_no_urls_or_host_injection(self):
  with self.assertRaises(m.InfraError):self.engine().prepare('test','godaddy','dns.create',{'zone':'https://evil.com','record':self.args()['record']})
 def test_no_invalid_ip(self):
  r=self.args();r['record']['content']='not-ip'
  with self.assertRaises(m.InfraError):self.engine().prepare('test','cloudflare','dns.create',r)
 def test_reject_bool_ttl(self):
  r=self.args();r['record']['ttl']=True
  with self.assertRaises(m.InfraError):self.engine().prepare('test','cloudflare','dns.create',r)
 def test_missing_expected_rejected(self):
  with self.assertRaises(m.InfraError):self.engine().prepare('test','cloudflare','dns.delete',{'zone':'abc123','recordId':'rec123'})
 def test_requires_approval(self):
  e=self.engine();r=e.prepare('test','cloudflare','dns.create',self.args())
  with self.assertRaises(m.InfraError):e.execute(r['id'])
  with self.assertRaises(m.InfraError):e.approve(r['id'],'wrong')
 def test_single_use(self):
  t=Transport([{'success':True,'result':{'id':'rec123'}},{'result':{'type':'A','name':'www.test.com','content':'192.0.2.10'}}]);e=self.engine(t)
  with patch.dict(os.environ,{'CLOUDFLARE_API_TOKEN':'fake'}):
   args=self.args();args['zone']='abc123';r=e.prepare('test','cloudflare','dns.create',args);self.approve(e,r)
   result=e.execute(r['id'])
  self.assertEqual(result['status'],'verification-pending') # name mismatched without a known apex
  with self.assertRaises(m.InfraError):e.execute(r['id'])
  self.assertEqual(t.requests[0][0],'POST')
 def test_cloudflare_verified(self):
  t=Transport([{'success':True,'result':{'id':'r1'}},{'result':{'type':'A','name':'www','content':'192.0.2.10'}}]);e=self.engine(t)
  with patch.dict(os.environ,{'CLOUDFLARE_API_TOKEN':'fake'}):
   r=e.prepare('test','cloudflare','dns.create',self.args());self.approve(e,r);res=e.execute(r['id'])
  self.assertEqual(res['status'],'verified')
  self.assertNotIn('fake',json.dumps(res))
 def test_godaddy_create(self):
  t=Transport([[],{},[{'type':'A','name':'www','data':'192.0.2.10'}]]);e=self.engine(t)
  with patch.dict(os.environ,{'GODADDY_PAT':'fake'}):
   a=self.args();a['zone']='example.com';a['record']['ttl']=600;r=e.prepare('test','godaddy','dns.create',a);self.approve(e,r);res=e.execute(r['id'])
  self.assertEqual(res['status'],'verified')
  self.assertIn('api.godaddy.com/v1',t.requests[0][1])
  self.assertEqual([x[0] for x in t.requests],['GET','PATCH','GET'])
  self.assertIsInstance(json.loads(t.requests[1][2]),list)
 def test_godaddy_bulk_mutations_disabled(self):
  for action in ('dns.update','dns.delete'):
   with self.assertRaises(m.InfraError):self.engine().prepare('test','godaddy',action,{'zone':'example.com','recordId':'rec123','expected':self.args()['record']})
 def test_unapproved_has_no_http(self):
  t=Transport([]);e=self.engine(t);e.prepare('test','cloudflare','dns.create',self.args());self.assertEqual(t.requests,[])
 def test_fail_is_redacted(self):
  t=Transport([OSError('SecretToHide')]);e=self.engine(t)
  with patch.dict(os.environ,{'CLOUDFLARE_API_TOKEN':'fake'}):
   r=e.prepare('test','cloudflare','dns.create',self.args());self.approve(e,r);res=e.execute(r['id'])
  self.assertEqual(res['status'],'failed');self.assertNotIn('SecretToHide',json.dumps(res))
 def test_update_mismatch_never_writes(self):
  t=Transport([{'result':{'type':'TXT','name':'www','content':'old'}}]);e=self.engine(t)
  a=self.args();a['recordId']='r1';a['expected']=a['record']
  with patch.dict(os.environ,{'CLOUDFLARE_API_TOKEN':'fake'}):
   r=e.prepare('test','cloudflare','dns.update',a);self.approve(e,r);res=e.execute(r['id'])
  self.assertEqual(res['status'],'failed');self.assertEqual(len(t.requests),1)
 def test_state_persists(self):
  e=self.engine();r=e.prepare('proj','cloudflare','dns.create',self.args());e2=self.engine();self.assertEqual(e2.status(r['id'])['status'],'awaiting-approval')
 def test_no_credential_exposure(self):
  e=self.engine();r=e.prepare('proj','cloudflare','dns.create',self.args());self.assertNotIn('approval_hash',r)
 def test_mongo_validation(self):
  r=self.engine().prepare('p','mongodb','index.create',{'database':'db','collection':'items','field':'slug','unique':True});self.assertEqual(r['operation'],'index.create')
 def test_aws_region_validation(self):
  with self.assertRaises(m.InfraError):self.engine().prepare('p','aws','ec2.start',{'region':'https://bad','instanceId':'i-0123456789abcdef0'})

if __name__=='__main__':unittest.main()

class MoreInfraTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
 def test_ionos_create(self):
  t=Transport([[{'id':'ionosrecord1'}],{'id':'ionosrecord1','type':'A','name':'www','content':'192.0.2.44'}])
  e=m.Engine(Path(self.tmp.name)/'db.json',t)
  with patch.dict(os.environ,{'IONOS_API_KEY':'dummy'}):
   rec=e.prepare('p','ionos','dns.create',{'zone':'ionoszone','record':{'name':'www','type':'A','content':'192.0.2.44','ttl':3600}})
   e.approve(rec['id'],rec['approvalPhrase']);done=e.execute(rec['id'])
  self.assertEqual(done['status'],'verified')
  self.assertEqual(t.requests[0][0],'POST')
  self.assertIsInstance(json.loads(t.requests[0][2]),list)
 def test_hetzner_is_pending(self):
  t=Transport([{'action':{'id':123}}, {'server':{'id':88,'status':'running'}}])
  e=m.Engine(Path(self.tmp.name)/'db.json',t)
  with patch.dict(os.environ,{'HETZNER_CLOUD_TOKEN':'dummy'}):
   r=e.prepare('p','hetzner','server.reboot',{'serverId':88});e.approve(r['id'],r['approvalPhrase']);out=e.execute(r['id'])
  self.assertEqual(out['status'],'verification-pending')
  self.assertTrue(out['result']['accepted'])
 def test_update_expected_match(self):
  t=Transport([{'result':{'type':'A','name':'www','content':'192.0.2.1'}},
               {'success':True,'result':{'id':'r2'}},
               {'result':{'name':'www','type':'A','content':'192.0.2.2'}}])
  e=m.Engine(Path(self.tmp.name)/'db.json',t)
  with patch.dict(os.environ,{'CLOUDFLARE_API_TOKEN':'dummy'}):
   r=e.prepare('p','cloudflare','dns.update',{'zone':'abc','recordId':'r2',
     'expected':{'name':'www','type':'A','content':'192.0.2.1','ttl':3600},
     'record':{'name':'www','type':'A','content':'192.0.2.2','ttl':3600}})
   e.approve(r['id'],r['approvalPhrase']);out=e.execute(r['id'])
  self.assertEqual(out['status'],'verified')
  self.assertEqual([x[0] for x in t.requests],['GET','PUT','GET'])
