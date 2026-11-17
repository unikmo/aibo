"""Small, allowlisted connector verification service.

This module does not hold secrets, initiate OAuth, or authorize writes.
Verification is explicit and read-only. Only fixed provider endpoints are allowed.
"""
from __future__ import annotations
import json
import os
import threading
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
try:
    from . import products, connector_catalog
except ImportError:
    import products, connector_catalog

_LOCK=threading.RLock()
STATE=products.STATE/'verified-connections.json'
# Fixed verification endpoints, never supplied by user, no redirects.
PROBES={
 'github':('GITHUB_TOKEN','https://api.github.com/user','Bearer'),
 'vercel':('VERCEL_TOKEN','https://api.vercel.com/v2/user','Bearer'),
 'netlify':('NETLIFY_AUTH_TOKEN','https://api.netlify.com/api/v1/user','Bearer'),
 'resend':('RESEND_API_KEY','https://api.resend.com/domains','Bearer'),
 'deepl-api':('DEEPL_API_KEY','https://api.deepl.com/v2/usage','DeepL-Auth-Key'),
}
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def verify(project,connector,opener=None):
    if project not in {x['id'] for x in products.custom_projects()}:
        raise products.ProductError('Unknown project')
    names={x['id'] for x in connector_catalog.entries()}
    if connector not in names:raise products.ProductError('Unknown connector')
    if connector not in PROBES:
        return {'verified':False,'status':'setup-required','message':'This service has no verified local adapter yet. Soni can record the setup request, but cannot connect it automatically.'}
    env,url,method=PROBES[connector]
    if connector=='deepl-api' and os.environ.get('DEEPL_API_TIER','pro').lower()=='free':
        url='https://api-free.deepl.com/v2/usage'
    token=os.environ.get(env,'').strip()
    if not token:
        return {'verified':False,'status':'needs-authentication','message':f'No {env} credential was found in the local AIBO server environment. Authorize this provider using its own account controls, then retry verification.'}
    # Credential never returned to the browser or written to disk.
    headers={'Accept':'application/json','User-Agent':'AIBO-Connector-Verification/1.0'}
    headers['Authorization']=(f'Bearer {token}' if method=='Bearer' else f'DeepL-Auth-Key {token}')
    req=urllib.request.Request(url,headers=headers,method='GET')
    try:
        if opener is None:
            opener=urllib.request.build_opener(NoRedirect)
        response=opener.open(req,timeout=10)
        with response:
            code=response.status
            response.read(1024)
        ok=code==200
    except (urllib.error.URLError,TimeoutError,OSError) as exc:
        # Hide server/provider details to avoid returning credentials in URLs or exceptions.
        return {'verified':False,'status':'verification-failed','message':'Verification failed or provider was unavailable. Check account permissions and retry.'}
    if not ok:
        return {'verified':False,'status':'verification-failed','message':'Provider did not confirm access.'}
    with _LOCK:
        db=products.read_json(STATE,{})
        db[project+':'+connector]={'project':project,'connector':connector,'verifiedAt':datetime.now(timezone.utc).isoformat(),'method':'read-only-get','credentialSource':env}
        products.write_json(STATE,db)
    return {'verified':True,'status':'verified','message':'Read-only credential verification succeeded. No external changes were made.'}

def status(project,connector):
    if connector not in PROBES:return {'verified':False,'status':'setup-required'}
    entry=products.read_json(STATE,{}).get(project+':'+connector)
    if not os.environ.get(PROBES[connector][0], '').strip():entry=None
    # A previous success is informational, not a guarantee credentials remain valid.
    return {'verified':bool(entry),'status':'previously-verified' if entry else 'not-verified', 'verifiedAt':entry.get('verifiedAt') if entry else None}

def public_capabilities():
    return [{'connector':k,'verification':'read-only','credentialEnvironment':v[0]} for k,v in PROBES.items()]

# Language tasks: direct translation is only invoked by an explicit user action.
# This is not automatic publication, page localization QA, or a replacement for review.
LANGS={'EN','DE','FR','ES','PT','PT-BR','IT','NL','PL','SV','DA','NO','FI','JA','KO','ZH','UK','AR','TR'}
def translate(project,text,source,target,consent=False,opener=None):
    import urllib.parse
    if not consent:raise products.ProductError('Explicit approval for DeepL API processing and possible charges is required')
    if project not in {x['id'] for x in products.custom_projects()}:raise products.ProductError('Unknown project')
    if not isinstance(text,str) or not 1<=len(text)<=5000 or any(ord(c)<32 and c not in '\n\t' for c in text):
        raise products.ProductError('Text must be 1–5,000 characters')
    if source not in LANGS or target not in LANGS or source==target:
        raise products.ProductError('Select different supported source and target languages')
    token=os.environ.get('DEEPL_API_KEY','').strip()
    if not token:raise products.ProductError('DeepL API credential not configured in the local server environment')
    # Customer chooses the account tier on their computer, not an arbitrary endpoint.
    url='https://api-free.deepl.com/v2/translate' if os.environ.get('DEEPL_API_TIER','pro').lower()=='free' else 'https://api.deepl.com/v2/translate'
    payload=urllib.parse.urlencode({'text':text,'source_lang':source.split('-')[0], 'target_lang':target}).encode()
    req=urllib.request.Request(url,data=payload,method='POST',headers={
        'Authorization':'DeepL-Auth-Key '+token,'Content-Type':'application/x-www-form-urlencoded','User-Agent':'AIBO-Local-Translation/1.0'})
    if opener is None:opener=urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req,timeout=25) as response:
            if response.status !=200:raise products.ProductError('Translation provider did not confirm success')
            decoded=json.loads(response.read(100000).decode('utf-8'))
        candidates=decoded.get('translations',[])
        if not candidates or not isinstance(candidates[0].get('text'),str):
            raise products.ProductError('Unexpected translation provider response')
        return {'source':source,'target':target,'text':candidates[0]['text'],
                'provider':'DeepL API','published':False,'needsHumanReview':True}
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,OSError,ValueError) as exc:
        # Never reflect provider error payload or credentials in the UI.
        raise products.ProductError('DeepL translation failed. Check your API tier, credentials and provider quota.') from None
