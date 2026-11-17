"""Explicitly approved, single-use infrastructure writes for AIBO.

No arbitrary endpoints, no credentials in browser payloads, no write on plan/prepare.
Provider HTTP API is fixed; verification reads the exact resource back.
"""
from __future__ import annotations
import hashlib, ipaddress, json, os, re, threading, time, uuid, urllib.request, urllib.error
from pathlib import Path
from urllib.parse import quote

LOCK=threading.RLock()
BASE={
 'cloudflare':'https://api.cloudflare.com/client/v4',
 'godaddy':'https://api.godaddy.com',
 'ionos':'https://api.hosting.ionos.com/dns/v1',
 'hetzner':'https://api.hetzner.cloud/v1',
}
# Provider API paths only; never accept URLs from model/user inputs.
ALLOWED={
 'cloudflare':{'dns.create','dns.update','dns.delete'},
 'godaddy':{'dns.create'}, # v1 has name/type-wide replace/delete, not record-ID mutation
 'ionos':{'dns.create','dns.update','dns.delete'},
 'hetzner':{'server.poweron','server.poweroff','server.reboot'},
 'aws':{'ec2.start','ec2.stop'},
 'mongodb':{'collection.create','index.create'},
}
NAME=re.compile(r'^(?:@|\*|[a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9_-]+)*)$')
ZONE=re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9.-]{0,250}$')
ID=re.compile(r'^[a-zA-Z0-9_-]{1,100}$')
TYPES={'A','AAAA','CNAME','TXT','MX'}

class InfraError(ValueError):pass
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def _str(v, pattern=ID, label='Identifier'):
 if not isinstance(v,str) or not pattern.fullmatch(v):raise InfraError(label+' invalid')
 return v

def _record(raw,provider):
 if not isinstance(raw,dict):raise InfraError('DNS record required')
 typ=raw.get('type');name=_str(raw.get('name'),NAME,'DNS name')
 if typ not in TYPES:raise InfraError('Unsupported DNS record type')
 value=raw.get('content',raw.get('data'))
 if not isinstance(value,str) or not value or len(value)>1024 or any(ord(c)<32 for c in value):raise InfraError('Invalid DNS value')
 if typ in ('A','AAAA'):
  try: ip=ipaddress.ip_address(value)
  except ValueError:raise InfraError('Invalid IP address')
  if ip.version!=(4 if typ=='A' else 6):raise InfraError('Incorrect IP version')
 elif typ in ('CNAME','MX'):
  if not ZONE.fullmatch(value.rstrip('.')):raise InfraError('Invalid DNS target')
 ttl=raw.get('ttl',3600)
 if type(ttl) is not int or ttl<60 or ttl>86400:raise InfraError('Invalid DNS TTL')
 if provider=='godaddy' and ttl<600:raise InfraError('GoDaddy TTL must be at least 600')
 entry={'type':typ,'name':name,'content':value,'ttl':ttl}
 if typ=='MX':
  priority=raw.get('priority')
  if type(priority) is not int or not 0<=priority<=65535:raise InfraError('MX priority required')
  entry['priority']=priority
 return entry

def _canonical(provider,operation,args):
 if provider not in ALLOWED or operation not in ALLOWED[provider]:raise InfraError('Unsupported provider operation')
 if not isinstance(args,dict):raise InfraError('Arguments must be an object')
 if operation.startswith('dns.'):
  if provider=='cloudflare':zone=_str(args.get('zone'),ID,'Zone ID')
  elif provider=='ionos':zone=_str(args.get('zone'),ID,'Zone ID')
  else:zone=_str(args.get('zone'),ZONE,'Domain')
  out={'zone':zone}
  if operation!='dns.create':out['recordId']=_str(args.get('recordId'),ID,'Record ID')
  if operation!='dns.delete':out['record']=_record(args.get('record'),provider)
  if operation in ('dns.delete','dns.update'):
   if args.get('expected') is None:raise InfraError('Expected current record required for safe update/delete')
   out['expected']=_record(args['expected'],provider)
  return out
 if provider=='hetzner':
  ident=args.get('serverId')
  if type(ident) is not int or not 1<=ident<=2**63-1:raise InfraError('Invalid server ID')
  return {'serverId':ident}
 if provider=='aws':
  region=args.get('region','eu-central-1')
  if not isinstance(region,str) or not re.fullmatch(r'[a-z]{2}(?:-gov)?-[a-z]+-\d',region):raise InfraError('Invalid region')
  return {'region':region,'instanceId':_str(args.get('instanceId'),re.compile(r'i-[0-9a-f]{8}(?:[0-9a-f]{9})?'),'Instance')}
 if provider=='mongodb':
  db=_str(args.get('database'),re.compile(r'[A-Za-z0-9_-]{1,60}'),'Database')
  collection=_str(args.get('collection'),re.compile(r'[A-Za-z0-9_-]{1,80}'),'Collection')
  if operation=='collection.create':return {'database':db,'collection':collection}
  field=_str(args.get('field'),re.compile(r'[A-Za-z][A-Za-z0-9_.]{0,80}'),'Index field')
  return {'database':db,'collection':collection,'field':field,'unique':args.get('unique') is True}
 raise InfraError('Unsupported operation')

def _public(rec):
 return {k:v for k,v in rec.items() if k not in ('approval_hash',)}

class Engine:
 def __init__(self,state_path,transport=None,aws_factory=None,mongo_factory=None):
  self.path=Path(state_path);self.transport=transport;self.aws_factory=aws_factory;self.mongo_factory=mongo_factory
 def _load(self):
  if not self.path.exists():return {}
  return json.loads(self.path.read_text('utf-8'))
 def _save(self,data):
  self.path.parent.mkdir(parents=True,exist_ok=True)
  temp=self.path.with_name(self.path.name+'.'+uuid.uuid4().hex+'.tmp')
  try:
   with temp.open('w',encoding='utf-8') as f:
    json.dump(data,f,sort_keys=True);f.flush();os.fsync(f.fileno())
   os.replace(temp,self.path)
  finally:
   if temp.exists():temp.unlink()
 def prepare(self,project,provider,operation,args):
  project=_str(project,re.compile(r'[A-Za-z0-9_-]{1,100}'),'Project')
  details=_canonical(provider,operation,args)
  ident=uuid.uuid4().hex; challenge='APPROVE '+ident[:10].upper()
  rec={'id':ident,'project':project,'provider':provider,'operation':operation,'args':details,
       'createdAt':int(time.time()),'status':'awaiting-approval','result':None,
       'approval_hash':hashlib.sha256(challenge.encode()).hexdigest()}
  with LOCK:
   entries=self._load();entries[ident]=rec;self._save(entries)
  return {**_public(rec),'approvalPhrase':challenge,'note':'Review exact operation, target and impact. Approval is single-use.'}
 def approve(self,ident,phrase):
  with LOCK:
   entries=self._load();rec=entries.get(ident)
   if not rec or rec['status']!='awaiting-approval':raise InfraError('Action is not pending')
   if int(time.time())-rec['createdAt']>900:raise InfraError('Approval expired')
   import hmac
   if not isinstance(phrase,str) or not hmac.compare_digest(hashlib.sha256(phrase.encode()).hexdigest(),rec['approval_hash']):raise InfraError('Approval phrase incorrect')
   rec['status']='approved';entries[ident]=rec;self._save(entries)
  return {'id':ident,'status':'approved'}
 def execute(self,ident):
  with LOCK:
   entries=self._load();rec=entries.get(ident)
   if not rec or rec['status']!='approved':raise InfraError('Action is not approved or already used')
   if int(time.time())-rec['createdAt']>900:raise InfraError('Approval expired')
   rec['status']='executing';entries[ident]=rec;self._save(entries)
  try:
   outcome=self._perform(rec)
   rec['status']='verified' if outcome.get('verified') else 'verification-pending';rec['result']=outcome
  except Exception:
   rec['status']='failed';rec['result']={'message':'Provider execution failed. Check authorized account and provider logs; outcome may be uncertain.'}
  with LOCK:
   entries=self._load();entries[ident]=rec;self._save(entries)
  return _public(rec)
 def status(self,ident):
  return _public(self._load().get(ident,{}))
 def _request(self,provider,method,path,data=None):
  if provider not in BASE or not path.startswith('/') or '://' in path:raise InfraError('Provider path invalid')
  env={'cloudflare':'CLOUDFLARE_API_TOKEN','godaddy':'GODADDY_PAT','ionos':'IONOS_API_KEY','hetzner':'HETZNER_CLOUD_TOKEN'}
  token=os.environ.get(env[provider],'')
  if not token:raise InfraError('Provider credentials not configured')
  auth={'cloudflare':{'Authorization':'Bearer '+token},'godaddy':{'Authorization':'Bearer '+token},'ionos':{'X-API-Key':token},'hetzner':{'Authorization':'Bearer '+token}}[provider]
  headers={**auth,'Accept':'application/json','Content-Type':'application/json','User-Agent':'AIBO-Infrastructure/1.0'}
  req=urllib.request.Request(BASE[provider]+path,data=json.dumps(data).encode() if data is not None else None,headers=headers,method=method)
  opener=self.transport or urllib.request.build_opener(NoRedirect)
  with opener.open(req,timeout=15) as res:
   if res.status>=300:raise InfraError('Provider did not accept operation')
   raw=res.read(250000)
   return json.loads(raw) if raw else {}
 def _dns(self,provider,operation,args):
  zone=quote(args['zone'],safe='')
  if provider=='cloudflare':root=f'/zones/{zone}/dns_records'
  elif provider=='godaddy':root=f'/domains/zones/{zone}/dns-records'
  else:root=f'/zones/{zone}/records'
  ident=args.get('recordId')
  detail=root+'/'+quote(ident,safe='') if ident else root
  method={'dns.create':'POST','dns.update':'PUT','dns.delete':'DELETE'}[operation]
  if operation in ('dns.update','dns.delete'):
   prior=self._request(provider,'GET',detail)
   if provider=='cloudflare':prior=prior.get('result',{})
   if not isinstance(prior,dict) or not prior:raise InfraError('Existing DNS record could not be read')
   if args.get('expected'):
    expected=args['expected'];previous=_normalize(prior)
    for k in ('name','type','content'):
     if str(previous.get(k,'')).rstrip('.') != str(expected.get(k,'')).rstrip('.'):
      raise InfraError('DNS record changed since review')
  record=args.get('record')
  if provider=='godaddy' and record:
   body={**record,'data':record['content']};body.pop('content')
  elif provider=='ionos' and record:
   body={'name':record['name'],'type':record['type'],'content':record['content'],'ttl':record['ttl']}
   if 'priority' in record:body['prio']=record['priority']
  else:body=record
  if operation=='dns.create' and provider=='ionos':body=[body]
  response=self._request(provider,method,detail,None if operation=='dns.delete' else body)
  if provider=='cloudflare' and response.get('success') is not True:raise InfraError('Cloudflare did not confirm change')
  rid=ident
  if operation=='dns.create':
   if provider=='cloudflare':rid=response.get('result',{}).get('id')
   elif provider=='godaddy':rid=response.get('recordId')
   else:
    records=response if isinstance(response,list) else [response]
    rid=records[0].get('id') if records and isinstance(records[0],dict) else None
  if operation=='dns.delete':
   try:self._request(provider,'GET',detail)
   except urllib.error.HTTPError as ex:
    if ex.code==404:return {'verified':True,'method':'read-back-404','recordId':ident}
    raise
   return {'verified':False,'message':'DNS record still available after deletion'}
  if not rid:return {'verified':False,'message':'Provider accepted write but did not return a record ID'}
  checked=self._request(provider,'GET',root+'/'+quote(str(rid),safe=''))
  if provider=='cloudflare':checked=checked.get('result',{})
  observed=_normalize(checked)
  ok=bool(observed and observed.get('type')==record['type'] and _matches_name(observed.get('name'),record['name'],args['zone']) and str(observed.get('content','')).rstrip('.')==record['content'].rstrip('.'))
  return {'verified':ok,'method':'provider-read-back','recordId':rid}
 def _godaddy(self,operation,args):
  """GoDaddy v1: append only; update/delete are intentionally fail-closed.

  GoDaddy v1 GET returns an array by name/type and PATCH appends records.
  Deleting or replacing by name/type may affect sibling records; do not do that.
  """
  if operation!='dns.create':raise InfraError('GoDaddy name/type bulk changes are not supported')
  record=args['record'];zone=quote(args['zone'],safe='')
  typ=quote(record['type'],safe='');name=quote(record['name'],safe='')
  endpoint=f'/v1/domains/{zone}/records/{typ}/{name}'
  def list_matching():
   rows=self._request('godaddy','GET',endpoint)
   if not isinstance(rows,list):raise InfraError('Unexpected GoDaddy DNS response')
   return [r for r in rows if isinstance(r,dict) and
           r.get('type')==record['type'] and
           _matches_name(r.get('name'),record['name'],args['zone']) and
           str(r.get('data','')).rstrip('.')==record['content'].rstrip('.')]
  before=list_matching()
  if before:raise InfraError('Matching GoDaddy record already exists; refusing duplicate')
  payload={'name':record['name'],'type':record['type'],'data':record['content'],'ttl':record['ttl']}
  if 'priority' in record:payload['priority']=record['priority']
  # PATCH appends; it does not replace the entire zone.
  self._request('godaddy','PATCH',f'/v1/domains/{zone}/records',[payload])
  after=list_matching()
  return {'verified':bool(after),'method':'provider-read-back','recordType':record['type'],
          'recordName':record['name'],
          'message':'GoDaddy append verified; no automatic deletion was attempted'}
 def _perform(self,rec):
  p=rec['provider'];op=rec['operation'];a=rec['args']
  if op.startswith('dns.'):
   if p=='godaddy':return self._godaddy(op,a)
   return self._dns(p,op,a)
  if p=='hetzner':
   ident=a['serverId'];action=op.split('.')[1]
   api={'poweron':'poweron','poweroff':'poweroff','reboot':'reboot'}[action]
   result=self._request('hetzner','POST',f'/servers/{ident}/actions/{api}')
   action_id=(result.get('action') or {}).get('id')
   if not action_id:return {'verified':False,'message':'Hetzner did not return action ID'}
   state=self._request('hetzner','GET',f'/servers/{ident}')
   return {'verified':False,'accepted':bool(state.get('server',{}).get('id')==ident),'providerActionId':action_id,'message':'Hetzner action accepted; asynchronous completion not yet verified'}
  if p=='aws':
   try:
    if self.aws_factory:ec2=self.aws_factory(a['region'])
    else:
     import boto3
     ec2=boto3.client('ec2',region_name=a['region'])
    ident=a['instanceId']
    if op=='ec2.start':ec2.start_instances(InstanceIds=[ident],DryRun=False)
    else:ec2.stop_instances(InstanceIds=[ident],DryRun=False)
    res=ec2.describe_instances(InstanceIds=[ident])
    states=[i['State']['Name'] for r in res.get('Reservations',[]) for i in r.get('Instances',[]) if i['InstanceId']==ident]
    return {'verified':len(states)==1 and states[0] == ('running' if op=='ec2.start' else 'stopped'),'observedState':states[0] if states else None,'message':'AWS EC2 state checked immediately; pending transitions require follow-up'}
   except ImportError:raise InfraError('boto3 missing')
  if p=='mongodb':
   uri=os.environ.get('MONGODB_URI','')
   if not uri:raise InfraError('MongoDB credentials not configured')
   client=self.mongo_factory(uri) if self.mongo_factory else __import__('pymongo').MongoClient(uri,serverSelectionTimeoutMS=5000)
   try:
    db=client[a['database']];names=db.list_collection_names()
    if op=='collection.create':
     if a['collection'] in names:raise InfraError('Collection already exists')
     db.create_collection(a['collection']);return {'verified':a['collection'] in db.list_collection_names()}
    if a['collection'] not in names:raise InfraError('Collection missing')
    key=a['field'];db[a['collection']].create_index([(key,1)],unique=a['unique'])
    idx=db[a['collection']].index_information()
    return {'verified':any(z.get('key')==[(key,1)] and z.get('unique',False)==a['unique'] for z in idx.values())}
   finally:client.close()
  raise InfraError('Unsupported operation')

def _normalize(r):
 if not isinstance(r,dict):return {}
 return {'name':r.get('name'),'type':r.get('type'),'content':r.get('content',r.get('data'))}

def _matches_name(actual,expected,zone):
 if actual is None:return False
 return str(actual).rstrip('.').lower() in {expected.rstrip('.').lower(),(expected+'.'+zone).rstrip('.').lower(),zone.lower() if expected=='@' else ''}
