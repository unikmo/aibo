"""Project-scoped, permission-gated browser inspection (read-only).

Cloud Browser/ChatGPT Work is not callable from the local runtime. This adapter
uses optional Playwright when permitted, otherwise reports an actionable error.
No form submission, clicking, filling, payment, posting or publishing here.
"""
import hashlib
import importlib.util
import ipaddress
import os
import re
import socket
import time
import urllib.parse
from pathlib import Path
try:
    from . import products, agent_setup
except ImportError:
    import products, agent_setup

ALLOWED_TASKS = {'inspect','screenshot'}

def capabilities():
    available=importlib.util.find_spec('playwright') is not None
    installed=False
    if available:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                installed=Path(p.chromium.executable_path).is_file()
        except Exception:
            installed=False
    return {'localHttpDiagnostics':True,
            'playwrightAvailable':available,
            'playwrightChromiumInstalled':installed,
            'browserDevtools': 'Available through Playwright console, page errors and request monitoring when Chromium is installed',
            'cloudBrowser': 'Not accessible directly from local AIBO; use ChatGPT Work separately',
            'hosting': 'Vercel integration is optional; other hosts remain supported',
            'browserReads':'explicit allowlisted HTTPS public hosts only',
            'browserWrites':'separate exact-action approval required'}

def validate(project, url, action, resolver=None):
    agent_setup.assert_permission(project,'read_browser')
    if action not in ALLOWED_TASKS:raise products.ProductError('Only inspect and screenshot are supported in read-only browser QA')
    if not isinstance(url,str) or len(url)>2048:raise products.ProductError('Invalid URL')
    try:parsed=urllib.parse.urlsplit(url);port=parsed.port
    except ValueError:raise products.ProductError('Invalid browser URL') from None
    hosts={h.strip().lower() for h in os.environ.get('AIBO_BROWSER_ALLOWED_HOSTS','').split(',') if h.strip()}
    host=(parsed.hostname or '').lower()
    if not hosts or parsed.scheme!='https' or host not in hosts or parsed.username or parsed.password or port not in (None,443):
        raise products.ProductError('Browser QA requires an explicitly allowlisted HTTPS host')
    if not re.fullmatch(r'[a-z0-9.-]{1,253}',host) or host.startswith('-'):
        raise products.ProductError('Invalid browser hostname')
    resolver=resolver or socket.getaddrinfo
    try:
        addresses={a[4][0] for a in resolver(host,443,type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(addr).is_global for addr in addresses):
            raise products.ProductError('Browser QA cannot access local or private addresses')
    except (OSError,ValueError) as exc:
        if isinstance(exc,products.ProductError):raise
        raise products.ProductError('Browser QA could not verify public host addresses') from None
    return {'host':host,'allowed':hosts}

def inspect(project,url,action='inspect',runner=None,resolver=None):
    trusted=validate(project,url,action,resolver=resolver)
    if runner is None:
        try:from playwright.sync_api import sync_playwright
        except ImportError:raise products.ProductError('Playwright is not installed on this computer') from None
        runner=lambda **kwargs: _playwright(sync_playwright,**kwargs)
    start=time.monotonic()
    try:
        result=runner(url=url,hosts=trusted['allowed'],screenshot=(action=='screenshot'),project=project)
    except products.ProductError:raise
    except Exception:raise products.ProductError('Browser inspection failed. Check the site, browser installation and local QA log.') from None
    if not isinstance(result,dict):raise products.ProductError('Invalid browser QA result')
    # Never return cookies, credentials, arbitrary machine paths or response bodies.
    return {'project':project,'url':url,'title':str(result.get('title',''))[:180],
            'text':str(result.get('text',''))[:6000],
            'javascriptErrors':[str(e)[:250] for e in result.get('javascriptErrors',[])[:15]],
            'networkErrors':[str(e)[:250] for e in result.get('networkErrors',[])[:15]],
            'screenshotSaved':bool(result.get('screenshotSaved',False)),
            'durationMs':round((time.monotonic()-start)*1000),
            'externalBusinessAction':False}

def _playwright(sync_playwright,url,hosts,screenshot,project):
    errors=[];network=[]
    def allowed_request(route):
        p=urllib.parse.urlsplit(route.request.url)
        if p.scheme=='https' and p.hostname in hosts and p.username is None and p.password is None:
            route.continue_()
        else:route.abort()
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            context=browser.new_context(accept_downloads=False,service_workers='block')
            page=context.new_page();page.route('**/*',allowed_request)
            page.on('pageerror',lambda e:errors.append(type(e).__name__+': '+str(e)[:180]))
            page.on('requestfailed',lambda r:network.append(r.url.split('?')[0][:180]))
            page.goto(url,wait_until='domcontentloaded',timeout=20000)
            if urllib.parse.urlsplit(page.url).hostname not in hosts:
                raise products.ProductError('Browser redirected outside its allowlist')
            data={'title':page.title(),'text':page.locator('body').inner_text(timeout=5000)[:6000],
                  'javascriptErrors':errors,'networkErrors':network}
            if screenshot:
                directory=products.STATE/'browser-qa'/project
                directory.mkdir(parents=True,exist_ok=True)
                stamp=hashlib.sha256((url+str(time.time_ns())).encode()).hexdigest()[:20]
                page.screenshot(path=str(directory/(stamp+'.png')),full_page=True,timeout=15000)
                data['screenshotSaved']=True
            return data
        finally:browser.close()
