"""Local project onboarding and read-only Soni job ledger.

Never changes existing project folders, the project registry, or its knowledge mapping.
AI provider calls are opt-in per request. All agent requests are analysis-only.
"""
from __future__ import annotations
import datetime as dt
import json
from pathlib import Path
import re
import threading
import uuid

try:
    from . import products, aibo, costs, attachments, ai_providers, source_onboarding
except ImportError:
    import products, aibo, costs, attachments, ai_providers, source_onboarding

LOCK = threading.RLock()
DIR = products.STATE / 'workspaces'
STAGES = ('business', 'focus', 'controls')
PROVIDERS = {'mock', 'auto', 'codex-local', 'claude-local', 'openai', 'anthropic', 'openrouter', 'vercel-gateway', 'together', 'groq'}
API_PROVIDERS = frozenset({'openai', 'anthropic', 'openrouter', 'vercel-gateway', 'together', 'groq'})

def requires_api_consent(provider):
    return provider in API_PROVIDERS
ALLOWED = {'name': 80, 'region': 100, 'goal': 500, 'website': 200,
           'audience': 250, 'successMeasure': 250, 'notes': 800}
RUNS_DIR = products.STATE / 'runs'
CURRENT = {}
SESSION_ID = str(uuid.uuid4())

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def _project(project_id):
    if not isinstance(project_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', project_id):
        raise products.ProductError('Invalid project ID')
    try:
        return aibo.project_info(project_id)
    except aibo.AiboError as exc:
        raise products.ProductError(str(exc)) from exc

DRAFTS = products.STATE/'source-previews'
def source_inventory(project_id):
    """Read a bounded set of non-secret files from this project's own folder."""
    project=_project(project_id)
    folder=aibo._project_folder(project).resolve()
    preferred=('01-Business-Foundation/01-Business-Profile.md',
               '01-Business-Foundation/README.md','AIBO-PROJECT-OVERVIEW.md','README.md')
    candidates=[folder/name for name in preferred]
    if folder.is_dir():
        matches=[]
        for item in folder.rglob('*'):
            if not item.is_file():continue
            relative=item.relative_to(folder)
            if len(relative.parts)>4 or any(part.startswith('.') or part.lower() in (
                    'node_modules','build','dist','vendor','archive','backup','secrets') for part in relative.parts):
                continue
            if item.suffix.lower() not in ('.md','.txt','.json','.csv','.docx','.pptx','.xlsx','.pdf'):
                continue
            if not any(term in item.stem.casefold() for term in (
                    'readme','profile','brief','about','overview','business','strategy','pitch','project')):
                continue
            matches.append(item)
            if len(matches)>=36:break
        candidates.extend(sorted(matches))
    sources=[]
    seen=set()
    for file in candidates:
        file=file.resolve()
        if file in seen or not file.is_relative_to(folder) or not file.is_file():continue
        seen.add(file)
        if not 0<file.stat().st_size<=300000:continue
        rel=file.relative_to(folder).as_posix()
        try:
            raw=file.read_bytes()
            if b'New independent project workspace.' in raw and 'AIBO-PROJECT-OVERVIEW' in rel:
                continue # Empty generated scaffold is not genuine business evidence.
            item=source_onboarding.inspect_document(rel,raw)
            item['reference']='Project file · '+rel
            for evidence in item['evidence']:evidence['source']=item['reference']
            sources.append(item)
        except (source_onboarding.SourceError,OSError,UnicodeError):
            continue
        if len(sources)>=12:break
    summary=source_onboarding.consolidate(sources)
    return {'project':project_id,'sources':sources,
            'suggestions':summary['suggestions'],'conflicts':summary['conflicts'],
            'localOnly':True,
            'note':'Only bounded project-owned local files were inspected. No external connections used.'}

def inspect_sources(project_id,payload):
    """Explicit owner-triggered discovery, with per-source errors and no model calls."""
    _project(project_id)
    if not isinstance(payload,dict) or set(payload)-{'website','repository','drive','attachments'}:
        raise products.ProductError('Invalid source inspection payload')
    sources=source_inventory(project_id)['sources']
    failures=[]
    references=[]
    for kind in ('website','repository','drive'):
        url=payload.get(kind,'')
        if not isinstance(url,str) or len(url)>1400:
            raise products.ProductError('Invalid '+kind+' URL')
        if not url.strip():continue
        references.append({'kind':kind,'url':url.strip()})
        try:
            source=source_onboarding.inspect_remote(kind,url.strip())
            if isinstance(source,list):
                sources.extend(source)
            else:
                sources.append(source)
        except source_onboarding.SourceError as exc:
            failures.append({'kind':kind,'source':url.strip(),'reason':str(exc)[:260]})
    ids=payload.get('attachments',[])
    for meta,file in attachments.load(project_id,ids):
        try:
            sources.append(source_onboarding.inspect_document(meta['name'],file.read_bytes()))
            references.append({'kind':'uploaded-document','name':meta['name'],'sha256':meta['sha256']})
        except source_onboarding.SourceError as exc:
            failures.append({'kind':'uploaded-document','source':meta['name'],'reason':str(exc)[:260]})
    summary=source_onboarding.consolidate(sources)
    result={'project':project_id,'sources':[{'reference':x['reference'],'excerpt':x['excerpt'],'read':True}
                                            for x in sources],
            'suggestions':summary['suggestions'],'conflicts':summary['conflicts'],
            'failures':failures,'references':references,
            'reviewRequired':True,'saved':False}
    products.write_json(DRAFTS/(project_id+'.json'),result)
    return result

def _path(project_id):
    _project(project_id)
    return DIR / (project_id + '.json')

def setup_state(project_id):
    project = _project(project_id)
    data = products.read_json(_path(project_id), {})
    legacy = products.read_json(products.STATE/'custom.json', {}).get(project_id, {})
    initial = {'name': legacy.get('name', project['name']), 'region': legacy.get('region', project.get('region', '')),
               'goal': legacy.get('goal', ''), 'website': '', 'audience': '', 'successMeasure': '', 'notes': ''}
    fields = {**initial, **data.get('fields', {})}
    completed = bool(data.get('complete', False))
    return {'project': project_id, 'fields': fields, 'step': data.get('step', 0),
            'complete': completed, 'savedAt': data.get('savedAt'), 'reviewed': bool(data.get('reviewed', False)),
            'sourceEvidence': data.get('sourceEvidence', [])}

def save_setup(project_id, payload):
    _project(project_id)
    if not isinstance(payload, dict):
        raise products.ProductError('Invalid setup payload')
    fields = payload.get('fields')
    if not isinstance(fields, dict) or any(k not in ALLOWED for k in fields):
        raise products.ProductError('Unknown setup field')
    step = payload.get('step', 0)
    if type(step) is not int or not 0 <= step <= 2:
        raise products.ProductError('Invalid setup step')
    if 'reviewSources' in payload and type(payload['reviewSources']) is not bool:
        raise products.ProductError('Invalid source review flag')
    finish = payload.get('complete') is True
    if 'complete' in payload and type(payload['complete']) is not bool:
        raise products.ProductError('Invalid completion flag')
    with LOCK:
        state = setup_state(project_id)
        for key, value in fields.items():
            if not isinstance(value, str) or len(value) > ALLOWED[key] or any(ord(c)<32 and c not in '\n\t' for c in value):
                raise products.ProductError('Invalid ' + key)
            state['fields'][key] = value.strip()
        if finish:
            draft = products.read_json(DRAFTS/(project_id+'.json'),{})
            has_sources = bool(draft.get('sources')) and payload.get('reviewSources') is True
            if not state['fields'].get('name'):
                raise products.ProductError('Project name required')
            if not has_sources and not state['fields'].get('goal'):
                raise products.ProductError('Provide a business goal or review existing project sources first')
            if has_sources:
                state['sourceEvidence'] = [
                    {'reference':src['reference'],'excerpt':src['excerpt'][:650]}
                    for src in draft['sources'][:12]
                ]
            state['complete'] = True
            state['reviewed'] = True
        else:
            # If a completed project is edited, don't silently keep it approved.
            if state['complete'] and fields:
                state['complete'] = False
                state['reviewed'] = False
        state['step'] = step
        state['savedAt'] = now()
        products.write_json(_path(project_id), {k: state.get(k) for k in ('fields','step','complete','reviewed','savedAt','sourceEvidence')})
        return setup_state(project_id)

def _run_file(run_id):
    if not re.fullmatch(r'[0-9a-f-]{36}', run_id):
        raise products.ProductError('Invalid run ID')
    return RUNS_DIR/(run_id+'.json')

def run_status(run_id):
    item = products.read_json(_run_file(run_id), None)
    if not item:
        raise products.ProductError('Unknown run ID')
    if item.get('status') in ('queued','running') and item.get('sessionId') != SESSION_ID:
        # A local server restart interrupted in-memory work; never claim it completed.
        item['status']='interrupted'
        item['error']='The local server restarted before this run finished. You can start a new run.'
        item['updatedAt']=now()
        products.write_json(_run_file(item['id']),item)
    return item

def _save_run(item):
    products.write_json(_run_file(item['id']), item)

def start_run(project_id, payload):
    _project(project_id)
    if not isinstance(payload, dict):
        raise products.ProductError('Invalid request')
    setup=setup_state(project_id)
    if not setup['complete']:
        raise products.ProductError('Finish the guided project setup before asking Soni to work')
    instruction=payload.get('task','')
    provider=payload.get('provider','mock')
    if not isinstance(instruction,str) or not 5 <= len(instruction.strip()) <= 1500:
        raise products.ProductError('Describe the task in 5–1500 characters')
    if provider not in PROVIDERS:
        raise products.ProductError('Unsupported AI provider')
    if requires_api_consent(provider) and payload.get('consent') is not True:
        raise products.ProductError('API processing requires explicit consent')
    attachment_ids=payload.get('attachments',[])
    attachments.load(project_id,attachment_ids)
    with LOCK:
        if project_id in CURRENT:
            running=products.read_json(_run_file(CURRENT[project_id]),{})
            if running.get('status') in ('queued','running'):
                raise products.ProductError('Soni is already working on this project')
        item={'id':str(uuid.uuid4()), 'project':project_id, 'task':instruction.strip(),
              'provider':provider, 'apiConsentGranted':requires_api_consent(provider) and payload.get('consent') is True, 'attachments':attachment_ids, 'status':'queued','sessionId':SESSION_ID,'createdAt':now(), 'updatedAt':now(),
              'result':None, 'error':None, 'externalActionsExecuted':False}
        _save_run(item)
        CURRENT[project_id]=item['id']
    # AIBO_NFAT_RACE_V1: mock provider has no network or external actions.
    # Complete mock jobs inline; real AI jobs remain asynchronous.
    if provider == 'mock':
        _worker(item['id'])
    else:
        threading.Thread(target=_worker,args=(item['id'],),daemon=True,name='aibo-soni').start()
    return {'id':item['id'],'project':project_id,'status':'queued'}

def _worker(run_id):
    with LOCK:
        item=run_status(run_id)
        item['status']='running';item['updatedAt']=now();_save_run(item)
    try:
        # No publishing, sending, buying, deploying, or other external business operations.
        limits=costs.current()
        attachment_context=attachments.context(item['project'],item.get('attachments',[]))
        enriched=item['task'] + ('\n\n' + attachment_context if attachment_context else '')
        selected,model=(item['provider'],None) if item['provider']=='mock' else ai_providers.route(item['provider'])
        config=ai_providers.public()
        routes=None
        if item['provider']=='auto' and config['switchMode']=='soni':
            roster=aibo.select_agents(enriched)+['quality','soni']
            routes={agent:ai_providers.route('auto',agent) for agent in roster}
        attempt={'provider':selected,'status':'started'}
        item['providerAttempts']=[attempt]
        _save_run(item)
        try:
            result=aibo.execute(item['project'],enriched,provider=selected,model=model,agent_routes=routes,
                                output_token_limit=limits['maxOutputTokens'],max_model_calls=limits['maxModelCalls'])
        except aibo.AiboError as original:
            # Only an automatically routed CLI task may switch providers.
            # Never retry explicit/manual selections or use paid API endpoints.
            message=str(original)
            cli_error=(message.startswith('Local CLI failed') or
                       message.startswith('Local CLI timeout') or
                       message.startswith('Local CLI not installed'))
            fallback='claude-local' if selected=='codex-local' else 'codex-local'
            ready=ai_providers.public()['ready']
            if item['provider']!='auto' or not cli_error or not ready.get(fallback):
                raise
            attempt['status']='failed'
            attempt['error']=message[:300]
            item['providerAttempts'].append({'provider':fallback,'status':'started'})
            _save_run(item)
            # Use one CLI for the entire retry; overrides cannot route to APIs.
            result=aibo.execute(item['project'],enriched,provider=fallback,
                                model=config['models'].get(fallback) or None,agent_routes=None,
                                output_token_limit=limits['maxOutputTokens'],max_model_calls=limits['maxModelCalls'])
            item['providerAttempts'][-1]['status']='completed'
            item['effectiveProvider']=fallback
        else:
            attempt['status']='completed'
            item['effectiveProvider']=selected
        item['result']=result
        item['status']='completed'
    except Exception as exc:
        item['error']=str(exc)[:600]
        item['status']='failed'
    finally:
        item['updatedAt']=now()
        with LOCK:
            _save_run(item)
            if CURRENT.get(item['project'])==run_id:CURRENT.pop(item['project'],None)

def recent_runs(project_id):
    _project(project_id)
    if not RUNS_DIR.exists():return []
    items=[]
    for file in RUNS_DIR.glob('*.json'):
        value=products.read_json(file,{})
        if value.get('project')==project_id:
            items.append({k:value.get(k) for k in ('id','project','task','provider','status','createdAt','updatedAt','error')})
    return sorted(items,key=lambda x:x.get('createdAt') or '',reverse=True)[:12]
