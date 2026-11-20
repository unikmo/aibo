"""Read-only Google Drive OAuth PKCE for AIBO project onboarding.

Consent is initiated per project. Tokens are session-only; never returned to the
browser or persisted into project files. Requires AIBO_GOOGLE_CLIENT_ID.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.parse
import urllib.request

try:
    from . import products
except ImportError:
    import products

AUTH_URL="https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL="https://oauth2.googleapis.com/token"
SCOPE="https://www.googleapis.com/auth/drive.readonly"
PENDING={}
TOKENS={}
LOCK=threading.RLock()

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def begin(project,port):
    if project not in {x["id"] for x in products.custom_projects()}:
        raise products.ProductError("Unknown project")
    client=os.environ.get("AIBO_GOOGLE_CLIENT_ID","").strip()
    if not client:
        raise products.ProductError("Google Drive authorization is not configured. Upload a document or configure an AIBO Google OAuth desktop client.")
    if not 0<int(port)<65536:
        raise products.ProductError("Invalid local callback port")
    verifier=secrets.token_urlsafe(48)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state=secrets.token_urlsafe(32)
    redirect="http://127.0.0.1:"+str(int(port))+"/api/oauth/google-drive/callback"
    with LOCK:
        PENDING[state]={"project":project,"client":client,"verifier":verifier,
                        "redirect":redirect,"created":time.monotonic()}
    params={"response_type":"code","client_id":client,"redirect_uri":redirect,
            "scope":SCOPE,"access_type":"offline","prompt":"consent",
            "state":state,"code_challenge":challenge,"code_challenge_method":"S256"}
    return {"provider":"google-drive","authorizationUrl":AUTH_URL+"?"+urllib.parse.urlencode(params),
            "status":"consent-required","project":project}

def _exchange(body,opener=None):
    request=urllib.request.Request(TOKEN_URL,
        data=urllib.parse.urlencode(body).encode("utf-8"),
        headers={"Content-Type":"application/x-www-form-urlencoded"},
        method="POST")
    if opener is None:opener=urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request,timeout=15) as response:
            if response.status!=200:raise ValueError()
            data=json.loads(response.read(15000))
        token=data.get("access_token")
        if not isinstance(token,str) or not token:raise ValueError()
        return data
    except Exception:
        raise products.ProductError("Google Drive authorization could not be verified") from None

def callback(query,opener=None):
    state=query.get("state",[""])[0]
    with LOCK:pending=PENDING.pop(state,None)
    if not pending or time.monotonic()-pending["created"]>600:
        raise products.ProductError("Google Drive authorization expired or was not requested")
    if "error" in query:
        raise products.ProductError("Google Drive authorization was declined")
    code=query.get("code",[""])[0]
    if not isinstance(code,str) or not 1<=len(code)<=1500:
        raise products.ProductError("Google Drive authorization code missing")
    fields={"grant_type":"authorization_code","code":code,
            "client_id":pending["client"],"redirect_uri":pending["redirect"],
            "code_verifier":pending["verifier"]}
    secret=os.environ.get("AIBO_GOOGLE_CLIENT_SECRET","").strip()
    if secret:fields["client_secret"]=secret
    data=_exchange(fields,opener)
    with LOCK:
        TOKENS[pending["project"]]={"access_token":data["access_token"],
            "refresh_token":data.get("refresh_token"),
            "expires_at":time.time()+max(60,int(data.get("expires_in",3600))),
            "client":pending["client"]}
    return {"provider":"google-drive","project":pending["project"],
            "status":"authorized-for-session","persistent":False}

def token(project,opener=None):
    with LOCK:
        current=TOKENS.get(project)
        if not current:return None
        if current["expires_at"]>time.time()+45:return current["access_token"]
        if not current.get("refresh_token"):
            TOKENS.pop(project,None)
            return None
        fields={"grant_type":"refresh_token","client_id":current["client"],
                "refresh_token":current["refresh_token"]}
        secret=os.environ.get("AIBO_GOOGLE_CLIENT_SECRET","").strip()
        if secret:fields["client_secret"]=secret
        try:
            new=_exchange(fields,opener)
        except products.ProductError:
            TOKENS.pop(project,None)
            return None
        TOKENS[project]={"access_token":new["access_token"],
            "refresh_token":new.get("refresh_token",current["refresh_token"]),
            "expires_at":time.time()+max(60,int(new.get("expires_in",3600))),
            "client":current["client"]}
        return new["access_token"]

def status(project):
    if project not in {x["id"] for x in products.custom_projects()}:
        raise products.ProductError("Unknown project")
    active=bool(token(project))
    return {"provider":"google-drive","project":project,
            "available":bool(os.environ.get("AIBO_GOOGLE_CLIENT_ID","").strip()),
            "status":"authorized-for-session" if active else "not-connected",
            "persistent":False}
