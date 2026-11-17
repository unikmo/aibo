"""Owner-configured local AI providers. Credentials use Windows DPAPI user encryption."""
from __future__ import annotations
import base64
import os
from pathlib import Path
import re
import shutil
import sys
import threading
try:
    from . import products
except ImportError:
    import products

PATH = products.STATE/'ai-providers.json'
KEY_PATH = products.STATE/'ai-provider-secrets.json'
LOCK=threading.RLock()
ORDER=('codex-local','claude-local','openai','anthropic','openrouter','vercel-gateway','together','groq')
API=('openai','anthropic','openrouter','vercel-gateway','together','groq')
ENV_KEYS={'openai':'OPENAI_API_KEY','anthropic':'ANTHROPIC_API_KEY','openrouter':'OPENROUTER_API_KEY','vercel-gateway':'AI_GATEWAY_API_KEY','together':'TOGETHER_API_KEY','groq':'GROQ_API_KEY'}
# Fixed HTTPS hosts; never accept arbitrary credential destinations from the browser.
COMPAT_URLS={'openrouter':'https://openrouter.ai/api/v1/chat/completions', 'vercel-gateway':'https://ai-gateway.vercel.sh/v1/chat/completions', 'together':'https://api.together.xyz/v1/chat/completions', 'groq':'https://api.groq.com/openai/v1/chat/completions'}
DEFAULT_MODELS={'codex-local':'','claude-local':'','openai':'gpt-4.1-mini','anthropic':'claude-sonnet-4-5','openrouter':'','vercel-gateway':'','together':'','groq':''}
DEFAULT={'priority':list(ORDER),'switchMode':'ask','models':dict(DEFAULT_MODELS),'agentOverrides':{}}
AGENTS=('research','finance','growth','content','community','sales','video','engineering','automation','quality','legal','soni')

def _dpapi(data,encrypt):
    if os.name!='nt':
        raise products.ProductError('Persistent API key storage requires Windows DPAPI. Use provider environment variables on this platform.')
    import ctypes
    from ctypes import wintypes
    class DATA_BLOB(ctypes.Structure):
        _fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_ubyte))]
    src=ctypes.create_string_buffer(data)
    src_blob=DATA_BLOB(len(data),ctypes.cast(src,ctypes.POINTER(ctypes.c_ubyte)))
    dst_blob=DATA_BLOB()
    crypt=ctypes.windll.crypt32
    crypt.CryptProtectData.argtypes=[ctypes.POINTER(DATA_BLOB),wintypes.LPCWSTR,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(DATA_BLOB)]
    crypt.CryptProtectData.restype=wintypes.BOOL
    crypt.CryptUnprotectData.argtypes=[ctypes.POINTER(DATA_BLOB),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(DATA_BLOB)]
    crypt.CryptUnprotectData.restype=wintypes.BOOL
    if encrypt:
        ok=crypt.CryptProtectData(ctypes.byref(src_blob),'AIBO AI provider key',None,None,None,0,ctypes.byref(dst_blob))
    else:
        ok=crypt.CryptUnprotectData(ctypes.byref(src_blob),None,None,None,None,0,ctypes.byref(dst_blob))
    if not ok:raise products.ProductError('Windows credential protection failed for the current user')
    try:return ctypes.string_at(dst_blob.pbData,dst_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree.argtypes=[ctypes.c_void_p]
        ctypes.windll.kernel32.LocalFree.restype=ctypes.c_void_p
        ctypes.windll.kernel32.LocalFree(ctypes.cast(dst_blob.pbData,ctypes.c_void_p))

def _saved():
    data=products.read_json(PATH,{})
    if not isinstance(data,dict):data={}
    d={**DEFAULT,**data}
    # Upgrade older four-provider configurations without resetting user preferences.
    old_priority=data.get('priority') if isinstance(data.get('priority'),list) else []
    d['priority']=[v for v in old_priority if v in ORDER]+[v for v in ORDER if v not in old_priority]
    d['models']={**DEFAULT_MODELS,**(data.get('models',{}) if isinstance(data.get('models'),dict) else {})}
    d['agentOverrides']=data.get('agentOverrides',{}) if isinstance(data.get('agentOverrides'),dict) else {}
    return d

def key_for(provider):
    if provider not in API:return None
    env=os.environ.get(ENV_KEYS[provider])
    if env:return env
    values=products.read_json(KEY_PATH,{})
    encoded=values.get(provider)
    if not encoded:return None
    try:return _dpapi(base64.b64decode(encoded,validate=True),False).decode('utf-8')
    except Exception:raise products.ProductError('Stored provider key cannot be decrypted for this Windows user')

def public():
    settings=_saved()
    saved_keys=products.read_json(KEY_PATH,{})
    available={v:bool(shutil.which('codex' if v=='codex-local' else 'claude')) if v in ('codex-local','claude-local') else bool(os.environ.get(ENV_KEYS[v]) or saved_keys.get(v)) for v in ORDER}
    return {**settings,'ready':available,'credentialStorage':'Windows DPAPI per-user encryption for API keys',
            'note':'Provider availability is a local prerequisite check, not proof of authentication. No automatic paid fallback in ask mode.'}

def update(data):
    if not isinstance(data,dict) or set(data)-{'priority','switchMode','models','agentOverrides'}:
        raise products.ProductError('Invalid AI provider settings')
    with LOCK:
        settings=_saved()
        if 'priority' in data:
            v=data['priority']
            if not isinstance(v,list) or len(v)!=len(ORDER) or set(v)!=set(ORDER):
                raise products.ProductError('Priority must contain each configured provider exactly once')
            settings['priority']=v
        if 'switchMode' in data:
            if data['switchMode'] not in ('ask','soni'):
                raise products.ProductError('Invalid switching policy')
            settings['switchMode']=data['switchMode']
        if 'models' in data:
            v=data['models']
            if not isinstance(v,dict) or set(v)-set(ORDER) or any(not isinstance(s,str) or len(s)>100 or not re.fullmatch(r'[a-zA-Z0-9._:/-]*',s) for s in v.values()):
                raise products.ProductError('Invalid model identifiers')
            settings['models'].update(v)
        if 'agentOverrides' in data:
            v=data['agentOverrides']
            if not isinstance(v,dict) or set(v)-set(AGENTS) or any(x not in ORDER and x!='default' for x in v.values()):
                raise products.ProductError('Invalid specialist routing')
            settings['agentOverrides']=v
        products.write_json(PATH,settings)
    return public()

def save_key(provider, value):
    if provider not in API:raise products.ProductError('Only API providers accept API keys')
    if not isinstance(value,str) or not 12<=len(value)<=2048 or any(ord(c)<33 or ord(c)>126 for c in value):
        raise products.ProductError('Invalid API key')
    encoded=base64.b64encode(_dpapi(value.encode('utf-8'),True)).decode('ascii')
    with LOCK:
        saved=products.read_json(KEY_PATH,{})
        saved[provider]=encoded
        products.write_json(KEY_PATH,saved)
    return {'provider':provider,'saved':True}

def delete_key(provider):
    if provider not in API:raise products.ProductError('Unknown API provider')
    with LOCK:
        saved=products.read_json(KEY_PATH,{})
        saved.pop(provider,None)
        products.write_json(KEY_PATH,saved)
    return {'provider':provider,'removed':True}

def route(explicit='auto',agent=None):
    settings=_saved()
    if explicit in ORDER:return (explicit,settings['models'].get(explicit) or None)
    if explicit!='auto':raise products.ProductError('Unsupported provider')
    preferred=settings['priority'][0]
    if settings['switchMode']=='soni' and agent:
        choice=settings['agentOverrides'].get(agent)
        if choice in ORDER:preferred=choice
    # No silent selection of a different paid provider when a CLI is unavailable.
    return preferred, settings['models'].get(preferred) or None
