"""Prepared, exact-scope, single-use owner-approved actions.

Actions are not issued by AI directly. No arbitrary URLs or browser hosts from model output.
Provider response is checked; a queued post or triggered deployment is never marked live.
"""
import json,os,re,threading,urllib.request,urllib.parse,time,uuid
try:
    from . import products,operations,oauth_local
except ImportError:
    import products,operations,oauth_local

LOCK=threading.RLock(); PATH=products.STATE/'prepared-actions.json'
KINDS={'buffer-post','resend-email','vercel-deploy-hook','browser-interact'}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def _public(item):
    return {k:v for k,v in item.items() if k not in ('approvalId','secret')}

def _validate(project,kind,data):
    if project not in {x['id'] for x in products.custom_projects()}:raise products.ProductError('Unknown project')
    if kind not in KINDS:raise products.ProductError('Unsupported action')
    if not isinstance(data,dict):raise products.ProductError('Action details required')
    if kind=='buffer-post':
        if not isinstance(data.get('channelId'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{3,120}',data['channelId']):raise products.ProductError('Buffer channel ID required')
        if not isinstance(data.get('text'),str) or not 1<=len(data['text'])<=3000:raise products.ProductError('Post text required')
        if data.get('mode','addToQueue') not in ('addToQueue','shareNow'):raise products.ProductError('Invalid posting mode')
        return {'channelId':data['channelId'],'text':data['text'],'mode':data.get('mode','addToQueue')}
    if kind=='resend-email':
        address=data.get('to','');from_addr=data.get('from','');subject=data.get('subject','');text=data.get('text','')
        for a in (address,from_addr):
            if not isinstance(a,str) or not re.fullmatch(r'[^\s@<>]{1,80}@[^\s@<>]{1,160}\.[A-Za-z]{2,}',a):raise products.ProductError('Valid sending and recipient addresses required')
        if not isinstance(subject,str) or not 1<=len(subject)<=180 or not isinstance(text,str) or not 1<=len(text)<=10000:raise products.ProductError('Invalid email contents')
        return {'to':address,'from':from_addr,'subject':subject,'text':text}
    if kind=='vercel-deploy-hook':
        # Hook secret is configured outside the browser; browser cannot select arbitrary URL.
        if not os.environ.get('AIBO_VERCEL_PREVIEW_HOOK','').startswith('https://api.vercel.com/v1/integrations/deploy/'):
            raise products.ProductError('AIBO_VERCEL_PREVIEW_HOOK is not configured for this installation')
        return {'environment':'preview','notice':'Triggers configured Vercel preview branch, not production'}
    if kind=='browser-interact':
        url=data.get('url','');selector=data.get('selector','');action=data.get('action','')
        hosts={x.strip().lower() for x in os.environ.get('AIBO_BROWSER_ALLOWED_HOSTS','').split(',') if x.strip()}
        parsed=urllib.parse.urlsplit(url)
        if parsed.scheme!='https' or not hosts or parsed.hostname not in hosts or parsed.username or parsed.password:
            raise products.ProductError('Site not in local browser allowlist')
        operations.assert_public_host(parsed.hostname)
        if action not in ('click','fill'):raise products.ProductError('Only explicitly approved click/fill operations supported')
        if not isinstance(selector,str) or not 1<=len(selector)<=240:raise products.ProductError('Selector required')
        value=data.get('value')
        if action=='fill' and (not isinstance(value,str) or len(value)>1000):raise products.ProductError('Fill value required')
        return {'url':url,'action':action,'selector':selector,'value':value if action=='fill' else None,'hosts':sorted(hosts)}

def prepare(project,kind,details):
    validated=_validate(project,kind,details)
    ident=str(uuid.uuid4()); item={'id':ident,'project':project,'kind':kind,'details':validated,'status':'waiting-for-approval','createdAt':time.time(),'result':None}
    # Action ID & approved parameters include the exact payload (but not any credentials).
    params={'project':project,'kind':kind,'details':validated,'id':ident}
    approval=operations.approval_request('http-write' if kind!='browser-interact' else 'browser-interact',params)
    item['approvalId']=approval['id']
    with LOCK:
        db=products.read_json(PATH,{})
        db[ident]=item
        products.write_json(PATH,db)
    return {**_public(item),'approvalId':approval['id'],'message':'Review the exact action and approve it before execution.'}

def records(project=None):
    db=products.read_json(PATH,{})
    return [_public(v) for v in db.values() if project is None or v['project']==project]

def approve_action(ident,phrase):
    with LOCK:
        item=products.read_json(PATH,{}).get(ident)
        if not item or item['status']!='waiting-for-approval':raise products.ProductError('Unknown or non-pending action')
        operations.approve(item['approvalId'],phrase)
        return {'id':ident,'status':'approved','message':'Approval recorded for this exact action, once only.'}

def execute(ident,opener=None,browser_runner=None):
    with LOCK:
        db=products.read_json(PATH,{})
        item=db.get(ident)
        if not item or item['status']!='waiting-for-approval':raise products.ProductError('Action already used or unavailable')
        params={'project':item['project'],'kind':item['kind'],'details':item['details'],'id':ident}
        operations.consume(item['approvalId'],'http-write' if item['kind']!='browser-interact' else 'browser-interact',params)
        item['status']='running';db[ident]=item;products.write_json(PATH,db)
    try:
        result=_perform(item,opener,browser_runner)
        item['status']='submitted' if item['kind'] in ('buffer-post','vercel-deploy-hook') else 'completed'
        item['result']=result
    except Exception as exc:
        item['status']='failed';item['result']={'error':str(exc)[:200] if isinstance(exc,products.ProductError) else 'Provider action failed; inspect local provider status and configuration. Credentials and private URLs are not shown.'}
    with LOCK:
        db=products.read_json(PATH,{})
        db[ident]=item;products.write_json(PATH,db)
    return _public(item)

def _http(req,opener=None):
    if opener is None:opener=urllib.request.build_opener(NoRedirect)
    with opener.open(req,timeout=25) as response:
        if response.status not in (200,201,202):raise products.ProductError('Provider did not accept the request')
        return json.loads(response.read(15000))

def _perform(item,opener=None,browser_runner=None):
    kind=item['kind'];p=item['project'];d=item['details']
    if kind=='buffer-post':
        token=oauth_local.token(p) or os.environ.get('BUFFER_ACCESS_TOKEN')
        if not token:raise products.ProductError('Buffer OAuth authorization is missing or expired')
        query='mutation CreatePost($input:CreatePostInput!){ createPost(input:$input){... on PostActionSuccess{post{id text status}} ... on MutationError{message}}}'
        input={'text':d['text'],'channelId':d['channelId'],'schedulingType':'automatic','mode':d['mode']}
        req=urllib.request.Request('https://api.buffer.com',data=json.dumps({'query':query,'variables':{'input':input}}).encode(),
            method='POST',headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        data=_http(req,opener)
        if data.get('errors') or data.get('data',{}).get('createPost',{}).get('message'):
            raise products.ProductError('Buffer rejected the post')
        post=data.get('data',{}).get('createPost',{}).get('post')
        if not isinstance(post,dict) or not post.get('id'):raise products.ProductError('Buffer did not confirm post creation')
        return {'provider':'Buffer','postId':post['id'],'providerStatus':post.get('status','unknown'),'published':False}
    if kind=='resend-email':
        token=os.environ.get('RESEND_API_KEY')
        if not token:raise products.ProductError('Resend key missing')
        req=urllib.request.Request('https://api.resend.com/emails',method='POST',data=json.dumps(d).encode(),
                    headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','Idempotency-Key':item['id']})
        data=_http(req,opener)
        if not data.get('id'):raise products.ProductError('Resend did not confirm acceptance')
        return {'provider':'Resend','emailId':data['id'],'status':'accepted-by-provider-not-delivery-confirmed'}
    if kind=='vercel-deploy-hook':
        url=os.environ['AIBO_VERCEL_PREVIEW_HOOK']
        parsed=urllib.parse.urlsplit(url)
        if parsed.scheme!='https' or parsed.hostname!='api.vercel.com' or not parsed.path.startswith('/v1/integrations/deploy/'):
            raise products.ProductError('Invalid local preview hook')
        data=_http(urllib.request.Request(url,data=b'',method='POST'),opener)
        job=data.get('job',{})
        if not job.get('id'):raise products.ProductError('Vercel did not return a deployment job')
        return {'provider':'Vercel','jobId':job['id'],'providerState':job.get('state','unknown'),'deployed':False}
    if kind=='browser-interact':
        d=dict(d)
        if browser_runner is not None:return browser_runner(d)
        
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise products.ProductError('Optional Playwright is not installed; install it and the Chromium browser first')
        return operations._browser_execute(sync_playwright,d['action'],d['url'],set(d['hosts']),d['selector'],d['value'],None)
    raise products.ProductError('Unsupported action')
