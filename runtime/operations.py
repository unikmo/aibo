"""AIBO execution tools. Local operations require explicit invocation and bounded scope.

Approval is issued by a human using a separate CLI invocation and is cryptographically
bound to the intended operation parameters. No LLM response can mint an approval.
"""
import argparse
import datetime as dt
import hashlib
import ipaddress
import hmac
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import uuid

from aibo import ROOT, project_info, AiboError, load_json

STATE = ROOT / '.aibo-state'
CONFIG = ROOT / 'runtime' / 'connectors.json'
RISKY = {'deploy-preview', 'deploy-production', 'http-write', 'browser-interact'}
SAFE_EXTENSIONS = {'.py','.js','.jsx','.ts','.tsx','.json','.md','.css','.html','.txt','.yml','.yaml','.toml','.sql','.sh','.ps1'}
BLOCKED_SEGMENTS = {'.git','.env','.ssh','.aws','.vercel','node_modules','venv','.venv','__pycache__','.aibo-state'}


def timestamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def fingerprint(action, params):
    return hashlib.sha256(canonical({'action':action,'params':params}).encode()).hexdigest()


def safe_workspace(value):
    p = Path(value).expanduser().resolve()
    if not p.is_dir():
        raise AiboError('Workspace directory missing')
    if p == Path.home() or p == Path(p.anchor) or p == ROOT.resolve():
        raise AiboError('Select an isolated project CODE workspace, not home, root or AIBO knowledge root')
    return p


def safe_file(workspace, rel):
    candidate = Path(rel)
    if candidate.is_absolute() or not candidate.parts or any(s in BLOCKED_SEGMENTS or s.startswith('.env') for s in candidate.parts) or '..' in candidate.parts:
        raise AiboError('Unsafe file path')
    full = (workspace / candidate).resolve()
    if not full.is_relative_to(workspace) or full.suffix.lower() not in SAFE_EXTENSIONS:
        raise AiboError('File outside permitted code workspace or unapproved extension')
    return full


def audit(entry):
    STATE.mkdir(exist_ok=True)
    record = {'at':timestamp(), **entry}
    with (STATE / 'audit.jsonl').open('a', encoding='utf-8') as f:
        f.write(canonical(record)+'\n')
    return record


def approval_request(action, params):
    if action not in RISKY:
        raise AiboError('Action not in approval registry')
    request={'id':str(uuid.uuid4()),'action':action,'fingerprint':fingerprint(action,params), 'params':params, 'created':timestamp(), 'status':'PENDING'}
    directory=STATE/'approvals'
    directory.mkdir(parents=True,exist_ok=True)
    (directory/(request['id']+'.json')).write_text(json.dumps(request,indent=2),encoding='utf-8')
    audit({'event':'approval_requested','id':request['id'],'action':action,'fingerprint':request['fingerprint']})
    return request


def approve(id, phrase):
    if phrase!='I APPROVE THIS SPECIFIC ACTION':
        raise AiboError('Explicit human confirmation phrase required')
    path=STATE/'approvals'/(id+'.json')
    if not path.is_file() or not re.fullmatch(r'[0-9a-f-]{36}', id):
        raise AiboError('Unknown approval ID')
    request=load_json(path)
    if request['status']!='PENDING':
        raise AiboError('Approval is not pending')
    start=dt.datetime.fromisoformat(request['created'])
    if (dt.datetime.now(dt.timezone.utc)-start).total_seconds()>3600:
        raise AiboError('Approval expired after one hour')
    request['status']='APPROVED'
    request['approvedAt']=timestamp()
    path.write_text(json.dumps(request,indent=2),encoding='utf-8')
    audit({'event':'approved','id':id,'fingerprint':request['fingerprint']})
    return {'id':id,'status':'APPROVED','action':request['action']}


def consume(id, action, params):
    if not id or not re.fullmatch(r'[0-9a-f-]{36}',id):
        raise AiboError('Action requires a valid human approval ID')
    path=STATE/'approvals'/(id+'.json')
    if not path.is_file():
        raise AiboError('Action requires a valid human approval ID')
    approval=load_json(path)
    if approval.get('action')!=action or approval.get('fingerprint')!=fingerprint(action,params) or approval['status']!='APPROVED':
        raise AiboError('Approval does not match the exact operation or is already used')
    if (dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(approval['created'])).total_seconds()>3600:
        raise AiboError('Approval expired')
    approval['status']='CONSUMED'
    approval['consumedAt']=timestamp()
    path.write_text(json.dumps(approval,indent=2),encoding='utf-8')
    audit({'event':'approval_consumed','id':id,'action':action})


def run_program(command,cwd,timeout=240,input=None):
    try:
        p=subprocess.run(command,cwd=cwd,input=input,capture_output=True,text=True,timeout=timeout,check=False)
    except FileNotFoundError as e:
        raise AiboError(f'Executable missing: {command[0]} (install and authenticate separately)') from e
    except subprocess.TimeoutExpired as e:
        raise AiboError('Execution timed out') from e
    return {'returncode':p.returncode,'stdout':p.stdout[-8000:],'stderr':p.stderr[-3000:],'verifiedExit':p.returncode==0}


def code_agent(project,workspace,provider,goal,timeout=900):
    project_info(project)
    cwd=safe_workspace(workspace)
    if not (cwd/'.git').exists():
        raise AiboError('Code workspace must have its own .git directory; initialise git and review the target first')
    if provider=='codex-local':
        command=['codex','exec','--sandbox','workspace-write','--skip-git-repo-check','-']
    elif provider=='claude-local':
        # acceptEdits grants in-workspace edit access but still gates unsafe shell/network activities.
        command=['claude','-p','--permission-mode','acceptEdits','--output-format','text','--max-turns','15']
    else:
        raise AiboError('Native code editing supports codex-local or claude-local')
    instructions=('You are AIBO Product & Engineering. Only edit files within your supplied workspace. '
       'Do not deploy, send external communications, access other workspaces, use credentials, change billing, '
       'or claim tests you have not run. Apply minimal fixes, run applicable local tests, and report evidence. '
       'Do not change production services. Goal: '+goal)
    result=run_program(command,cwd,timeout,instructions)
    receipt=audit({'event':'code_agent','project':project,'provider':provider,'workspace':str(cwd),'goal':goal[:300], 'exitCode':result['returncode']})
    return {'operation':'code-agent','receipt':receipt,'process':result,'note':'Process exit is verified; functional correctness requires independent tests.'}


def apply_edits(project,workspace,patchfile,check_only=False):
    project_info(project)
    cwd=safe_workspace(workspace)
    spec=load_json(patchfile)
    if not isinstance(spec,dict) or not isinstance(spec.get('edits'),list) or not 1 <=len(spec['edits'])<=30:
        raise AiboError('Patch requires 1-30 explicit edits')
    changes=[]
    for item in spec['edits']:
        target=safe_file(cwd,item['path'])
        if not isinstance(item.get('content'),str) or len(item['content'].encode())>500_000:
            raise AiboError('Invalid edit content')
        expected=item.get('sha256')
        original=target.read_bytes() if target.exists() else None
        current=hashlib.sha256(original).hexdigest() if original is not None else None
        if expected!=current:
            raise AiboError('Optimistic concurrency hash mismatch: '+item['path'])
        changes.append((target,item['content'],current))
    if not check_only:
        for target,contents,_ in changes:
            target.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=target.parent,delete=False) as tmp:
                tmp.write(contents)
                name=tmp.name
            os.replace(name,target)
    audit({'event':'patch_validated' if check_only else 'patch_applied','project':project,'files':[str(t.relative_to(cwd)) for t,_,_ in changes]})
    return {'files':[str(t.relative_to(cwd)) for t,_,_ in changes], 'applied':not check_only}


def assert_public_host(host):
    if not host or host.lower() == "localhost" or host.endswith(".local") or host.endswith(".internal"):
        raise AiboError("Private or local hosts are prohibited")
    try:
        ip = ipaddress.ip_address(host)
        if not ip.is_global: raise AiboError("Non-public IP address prohibited")
    except ValueError:
        pass

def browser(action,url,host_allow,selector=None,value=None,outfile=None,approval=None):
    # An allowlist prevents arbitrary navigation to internal networks, cloud metadata, or credentials endpoints.
    parsed=urllib.parse.urlsplit(url)
    host=parsed.hostname or ''
    hosts={x.lower().strip() for x in host_allow.split(',') if x.strip()}
    if parsed.scheme!='https' or host.lower() not in hosts or not hosts or parsed.username or parsed.password:
        raise AiboError('Only allowlisted HTTPS hosts are permitted')
    assert_public_host(host)
    if action not in ('inspect','screenshot','click','fill'):
        raise AiboError('Unknown browser action')
    params={'action':action,'url':url,'hosts':sorted(hosts),'selector':selector,'value':value}
    if action in ('click','fill'):
        consume(approval,'browser-interact',params)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise AiboError('Install optional dependency: pip install playwright && playwright install chromium') from e
    from playwright.sync_api import Error as PlaywrightError
    try:
      return _browser_execute(sync_playwright,action,url,hosts,selector,value,outfile)
    except PlaywrightError as exc:
      raise AiboError('Playwright browser operation failed. Install browser binary with: python -m playwright install chromium; detail: '+str(exc)[:230]) from exc

def _browser_execute(sync_playwright,action,url,hosts,selector,value,outfile):
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True)
        page=b.new_page(accept_downloads=False)
        page.route('**/*',lambda route: route.continue_() if (urllib.parse.urlsplit(route.request.url).scheme=='https' and urllib.parse.urlsplit(route.request.url).hostname in hosts) else route.abort())
        try:
            page.goto(url,wait_until='domcontentloaded',timeout=25000)
            if page.url.split('/')[2].lower() not in hosts:
                raise AiboError('Browser redirected outside allowed hosts')
            if action=='click':
                if not selector: raise AiboError('Click requires selector')
                page.locator(selector).first.click(timeout=8000)
            if action=='fill':
                if not selector or value is None: raise AiboError('Fill requires selector and value')
                page.locator(selector).first.fill(value,timeout=8000)
            output={'url':page.url,'title':page.title(),'text':page.locator('body').inner_text()[:6000]}
            if action=='screenshot':
                if not outfile: raise AiboError('Screenshot requires output')
                screenshot=Path(outfile).expanduser().resolve()
                screenshot.parent.mkdir(parents=True,exist_ok=True)
                page.screenshot(path=str(screenshot),full_page=True)
                output['screenshot']=str(screenshot)
            audit({'event':'browser_'+action,'host':urllib.parse.urlsplit(url).hostname,'success':True})
            return output
        finally:
            b.close()


def deploy(project,workspace,environment,approval=None,timeout=600):
    project_info(project)
    cwd=safe_workspace(workspace)
    if not (cwd/'.vercel'/'project.json').is_file():
        raise AiboError('Vercel project not linked; refusing to select a target automatically')
    if environment not in ('preview','production'):
        raise AiboError('Only preview or production are supported')
    action='deploy-'+environment
    params={'project':project,'workspace':str(cwd),'environment':environment}
    consume(approval,action,params)
    command=['vercel','deploy','--yes'] + (['--prod'] if environment=='production' else [])
    result=run_program(command,cwd,timeout)
    urls=re.findall(r'https://[^\s]+',result['stdout'])
    audit({'event':'deployment','project':project,'environment':environment,'exitCode':result['returncode'],'url':urls[-1] if urls else None})
    return {'deployment':environment,'process':result,'deploymentUrl':urls[-1] if urls else None,'status':'submitted' if result['verifiedExit'] else 'failed','note':'HTTP smoke tests and production routing checks still required'}


def integration(project,operation,endpoint,allowed_hosts,approval=None,payload=None,token_env=None):
    project_info(project)
    parsed=urllib.parse.urlsplit(endpoint)
    hosts={x.strip().lower() for x in allowed_hosts.split(',') if x.strip()}
    if parsed.scheme!='https' or not hosts or parsed.hostname not in hosts or parsed.username or parsed.password:
        raise AiboError('Integration endpoint must be HTTPS with explicit host allowlist')
    assert_public_host(parsed.hostname)
    if operation not in ('GET','POST','PATCH'):
        raise AiboError('Unsupported integration HTTP verb')
    if parsed.hostname in ('api.stripe.com', 'api.paypal.com') and operation != 'GET':
        raise AiboError('Financial write actions require a dedicated provider-specific integration')
    params={'project':project,'operation':operation,'endpoint':endpoint,'payload':payload,'token_env':token_env}
    if operation!='GET':
        consume(approval,'http-write',params)
    headers={'Accept':'application/json','User-Agent':'AIBO/1.0'}
    if token_env:
        if not re.fullmatch(r'[A-Z][A-Z0-9_]*',token_env): raise AiboError('Invalid secret environment variable name')
        token=os.environ.get(token_env)
        if not token: raise AiboError('Secret environment variable missing: '+token_env)
        headers['Authorization']='Bearer '+token
    data=None if payload is None else json.dumps(payload).encode('utf-8')
    if data is not None: headers['Content-Type']='application/json'
    request=urllib.request.Request(endpoint,data=data,method=operation,headers=headers)
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs): return None
    opener=urllib.request.build_opener(NoRedirect)
    with opener.open(request,timeout=30) as response:
        text=response.read(20000).decode('utf-8','replace')
        result={'status':response.status,'body':text[:4000]}
    audit({'event':'integration_request','project':project,'method':operation,'host':parsed.hostname,'status':result['status']})
    return result


def doctor():
    commands={c:shutil.which(c) for c in ('python','codex','claude','vercel','git')}
    try: import playwright; browser_package=True
    except ImportError: browser_package=False
    keys={k:bool(os.environ.get(k)) for k in ('OPENAI_API_KEY','ANTHROPIC_API_KEY','VERCEL_TOKEN')}
    null=[]
    for p in ROOT.rglob('*.md'):
        if '.aibo-state' not in p.parts and b'\x00' in p.read_bytes():null.append(str(p.relative_to(ROOT)))
    return {'commands':commands,'credentialPresence':keys,'playwrightPython':browser_package,'nullByteMarkdown':null,'note':'Presence is not authentication or browser-install verification; secrets are never printed'}


def main(argv=None):
    p=argparse.ArgumentParser(description='AIBO operations: bounded autonomous editing, browser, deployment and integrations')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    ar=sub.add_parser('request-approval'); ar.add_argument('--action',choices=sorted(RISKY),required=True);ar.add_argument('--params',required=True,help='JSON object of exact operation arguments')
    ap=sub.add_parser('approve');ap.add_argument('--id',required=True);ap.add_argument('--confirm',required=True)
    cd=sub.add_parser('code');cd.add_argument('--project',required=True);cd.add_argument('--workspace',required=True);cd.add_argument('--provider',choices=['codex-local','claude-local'],required=True);cd.add_argument('--goal',required=True)
    ed=sub.add_parser('apply-patch');ed.add_argument('--project',required=True);ed.add_argument('--workspace',required=True);ed.add_argument('--patch',required=True);ed.add_argument('--check-only',action='store_true')
    br=sub.add_parser('browser');br.add_argument('--action',choices=['inspect','screenshot','click','fill'],required=True);br.add_argument('--url',required=True);br.add_argument('--hosts',required=True);br.add_argument('--selector');br.add_argument('--value');br.add_argument('--output');br.add_argument('--approval')
    dep=sub.add_parser('deploy');dep.add_argument('--project',required=True);dep.add_argument('--workspace',required=True);dep.add_argument('--environment',choices=['preview','production'],required=True);dep.add_argument('--approval',required=True)
    ht=sub.add_parser('http');ht.add_argument('--project',required=True);ht.add_argument('--method',choices=['GET','POST','PATCH'],required=True);ht.add_argument('--url',required=True);ht.add_argument('--hosts',required=True);ht.add_argument('--payload');ht.add_argument('--token-env');ht.add_argument('--approval')
    args=p.parse_args(argv)
    try:
        if args.command=='doctor':result=doctor()
        elif args.command=='request-approval':result=approval_request(args.action,json.loads(args.params))
        elif args.command=='approve':result=approve(args.id,args.confirm)
        elif args.command=='code':result=code_agent(args.project,args.workspace,args.provider,args.goal)
        elif args.command=='apply-patch':result=apply_edits(args.project,args.workspace,args.patch,args.check_only)
        elif args.command=='browser':result=browser(args.action,args.url,args.hosts,args.selector,args.value,args.output,args.approval)
        elif args.command=='deploy':result=deploy(args.project,args.workspace,args.environment,args.approval)
        else: result=integration(args.project,args.method,args.url,args.hosts,args.approval,json.loads(args.payload) if args.payload else None,args.token_env)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (AiboError,ValueError,OSError,ImportError) as e:
        print('AIBO ERROR: '+str(e),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
