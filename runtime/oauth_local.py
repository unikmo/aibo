"""Buffer OAuth 2.0 PKCE for a user-controlled localhost Control Centre.

Tokens are intentionally session-only; no token is written in plaintext to disk.
Restart requires reauthorization. No implicit permissions or automatic publishing.
"""
import base64,hashlib,json,os,secrets,threading,time,urllib.parse,urllib.request
try:
    from . import products
except ImportError:
    import products

PENDING={}; TOKENS={}; LOCK=threading.RLock()
AUTH='https://auth.buffer.com/auth'; TOKEN='https://auth.buffer.com/token'
SCOPE='posts:write posts:read offline_access'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*a,**kw):return None

def begin(project,port=8765):
    if project not in {x['id'] for x in products.custom_projects()}:raise products.ProductError('Unknown project')
    client=os.environ.get('AIBO_BUFFER_CLIENT_ID','').strip()
    if not client:raise products.ProductError('Buffer OAuth client ID not configured. Register a public OAuth client and set AIBO_BUFFER_CLIENT_ID locally.')
    verifier=secrets.token_urlsafe(48)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    state=secrets.token_urlsafe(32)
    redirect=f'http://127.0.0.1:{int(port)}/api/oauth/buffer/callback'
    with LOCK:
        PENDING[state]={'project':project,'verifier':verifier,'client':client,'redirect':redirect,'created':time.monotonic()}
    params={'response_type':'code','client_id':client,'redirect_uri':redirect,'scope':SCOPE,
            'state':state,'code_challenge':challenge,'code_challenge_method':'S256','prompt':'consent'}
    return {'provider':'buffer','authorizationUrl':AUTH+'?'+urllib.parse.urlencode(params),
            'message':'Open the provider consent page. AIBO stores the resulting token in server memory only.'}

def callback(query,opener=None):
    state=query.get('state',[''])[0]
    with LOCK:pending=PENDING.pop(state,None)
    if not pending or time.monotonic()-pending['created']>600:raise products.ProductError('OAuth state invalid or expired')
    if 'error' in query:raise products.ProductError('Buffer authorization was declined or failed')
    code=query.get('code',[''])[0]
    if not code or len(code)>1500:raise products.ProductError('OAuth code missing')
    body=urllib.parse.urlencode({'grant_type':'authorization_code','client_id':pending['client'],
           'code':code,'redirect_uri':pending['redirect'],'code_verifier':pending['verifier']}).encode()
    req=urllib.request.Request(TOKEN, data=body,method='POST',headers={'Content-Type':'application/x-www-form-urlencoded'})
    if opener is None:opener=urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req,timeout=20) as response:
            if response.status!=200:raise ValueError()
            data=json.loads(response.read(12000))
    except Exception:
        raise products.ProductError('Buffer token exchange failed. Confirm registered localhost callback and OAuth client settings.') from None
    token=data.get('access_token')
    if not isinstance(token,str) or not token:raise products.ProductError('Provider returned no access token')
    with LOCK:TOKENS[pending['project']]={'access_token':token,'refresh_token':data.get('refresh_token'),
             'expires_at':time.time()+int(data.get('expires_in',3600)), 'client':pending['client']}
    return {'provider':'buffer','project':pending['project'],'status':'authorized-for-session'}

def token(project,opener=None):
    with LOCK:
        data=TOKENS.get(project)
        if not data:return None
        if data['expires_at']>time.time()+30:return data['access_token']
        refresh=data.get('refresh_token')
        if not refresh:return None
        payload=urllib.parse.urlencode({'grant_type':'refresh_token','client_id':data['client'],
                'refresh_token':refresh}).encode()
        req=urllib.request.Request(TOKEN,data=payload,method='POST',headers={'Content-Type':'application/x-www-form-urlencoded'})
        if opener is None:opener=urllib.request.build_opener(NoRedirect)
        try:
            with opener.open(req,timeout=20) as response:
                if response.status!=200:raise ValueError()
                new=json.loads(response.read(12000))
            if not new.get('access_token') or not new.get('refresh_token'):raise ValueError()
            # Buffer refresh tokens are single-use: replace both atomically in this session.
            TOKENS[project]={'access_token':new['access_token'],'refresh_token':new['refresh_token'],
               'expires_at':time.time()+int(new.get('expires_in',3600)),'client':data['client']}
            return new['access_token']
        except Exception:
            TOKENS.pop(project,None)
            return None

def status(project):
    return {'provider':'buffer','project':project,'status':'authorized-for-session' if token(project) else 'not-connected',
            'persistent':False}
