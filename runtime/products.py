"""AIBO dual product state: local development backend, not a commercial license authority.

Standard entitlements are supplied by an external trusted activation service for production.
Local owner settings cannot grant paid entitlements.
"""
import json
import os
import sys
from pathlib import Path
import tempfile
import re
import threading

_registry_lock=threading.RLock()

ROOT=Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
REGISTRY=ROOT/'System'/'project-registry.json'
STATE=Path(os.environ.get('AIBO_STATE_DIR', str(Path.home()/'.aibo-state')))
MAX_SLOTS=5

class ProductError(ValueError): pass

def read_json(p,default):
    # AIBO_NFAT_RACE_V1: bounded retry for transient Windows read locks.
    for attempt in range(8):
        try:
            return json.loads(Path(p).read_text(encoding='utf8'))
        except FileNotFoundError:
            return default
        except PermissionError:
            if attempt == 7: raise
            __import__('time').sleep(min(0.005 * 2**attempt, 0.08))

def write_json(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.aibo-',dir=p.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf8') as f:
            json.dump(obj,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
        # AIBO_NFAT_RACE_V1: bounded retry for transient Windows replace locks.
        for attempt in range(8):
            try:
                os.replace(tmp,p)
                break
            except PermissionError:
                if attempt == 7: raise
                __import__('time').sleep(min(0.005 * 2**attempt, 0.08))
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def project_records():
    """Bundled registry plus user-owned additions, without modifying packaged sources."""
    bundled=read_json(REGISTRY, {'projects':[]})
    extra=read_json(STATE/'custom-projects.json', {'projects':[]})
    if not isinstance(bundled,dict) or not isinstance(bundled.get('projects'),list):
        raise ProductError('Invalid bundled project registry')
    if not isinstance(extra,dict) or not isinstance(extra.get('projects'),list):
        raise ProductError('Invalid local project registry')
    return bundled['projects'] + extra['projects']


def _project_folder(record):
    """User-created project files live in writable local state, not PyInstaller."""
    base=STATE if record.get('stateProject') is True else ROOT
    candidate=(base/record['projectHome']).resolve()
    if not candidate.is_relative_to(base.resolve()):
        raise ProductError('Invalid project workspace path')
    return candidate


def custom_projects():
    registry={'projects':project_records()}
    state=read_json(STATE/'custom.json',{})
    projects=[]
    for p in registry['projects']:
        x=state.get(p['id'],{})
        mapping=read_json(_project_folder(p)/'PROJECT-KNOWLEDGE.json',p.get('classification') or {'status':'pending-pack','industry':None,'corePack':None,'addOns':[]})
        setup=read_json(STATE/'workspaces'/(p['id']+'.json'),{})
        projects.append({'id':p['id'],'name':setup.get('fields',{}).get('name',x.get('name',p['name'])),'industry':mapping.get('industry'),
            'corePack':mapping.get('corePack'),'addOns':mapping.get('addOns',[]),
            'classificationStatus':mapping.get('status','pending-pack'),'initialized':bool(x.get('initialized',False) or setup.get('complete',False)),
            'setupComplete':bool(setup.get('complete',False)), 'setupStep':setup.get('step',0),
            'region':setup.get('fields',{}).get('region',x.get('region',p.get('region',''))),
            'goal':setup.get('fields',{}).get('goal',x.get('goal',''))})
    return projects

def standard_state():
    x=read_json(STATE/'standard.json',{})
    slots=x.get('slots',[])
    # Always provision five stable slots; inactive slots hold no business content.
    slots=(slots+[{'slot':i,'initialized':False,'name':'','region':'','goal':''} for i in range(1,6)])[0:5]
    for i,s in enumerate(slots):s['slot']=i+1
    return {'license':{'status':'not-activated','industry':None,'corePack':None,'addOns':[],
                       'projectLimit':MAX_SLOTS,'note':'Production licenses must be verified by a trusted issuer.'},
            'slots':slots}

def state_for(mode):
    if mode=='standard':return standard_state()
    if mode=='custom':return {'projects':custom_projects(),'model':'project-scoped-knowledge'}
    raise ProductError('Invalid product mode')

def update_project(mode,identifier,data):
    if mode not in ('standard','custom'):raise ProductError('Invalid mode')
    if not isinstance(data,dict):raise ProductError('Invalid request')
    name=str(data.get('name','')).strip()[:80]
    region=str(data.get('region','')).strip()[:100]
    goal=str(data.get('goal','')).strip()[:500]
    if not name or not goal:raise ProductError('Name and goal required')
    if mode=='standard':
        # Commercial SKU control must not trust browser input or local JSON.
        raise ProductError('Standard activation requires a verified license. Local demo cannot unlock paid project slots.')
    projects={p['id']:p for p in custom_projects()}
    if identifier not in projects:raise ProductError('Project not in configured workspace')
    state=read_json(STATE/'custom.json',{})
    state[identifier]={'initialized':True,'name':name,'region':region,'goal':goal}
    write_json(STATE/'custom.json',state)
    return {'ok':True,'project':identifier}


def pack_catalog():
    """Only actual bundled pack files can be assigned to Custom workspaces."""
    root=ROOT/'Industry-Packs'
    def scan(name):
        return [{'path':p.relative_to(ROOT).as_posix(),
                 'label':p.parent.name.replace('-', ' ')}
                for p in sorted(root.rglob(name))] if root.exists() else []
    return {'corePacks':scan('PACK-OVERVIEW.md'),'addOns':scan('PACK-ADDON.md')}


def _validate_pack(path, type_name):
    if not path:return None
    if not isinstance(path,str):raise ProductError('Invalid pack selection')
    allowable={x['path'] for x in pack_catalog()[type_name]}
    if path not in allowable:raise ProductError('Pack does not exist in bundled catalog')
    return path


def create_custom_project(data):
    """Additive only: new path, new registry record, never overwrite existing project data."""
    if not isinstance(data,dict):raise ProductError('Invalid request')
    name=data.get('name')
    if not isinstance(name,str) or not 1<=len(name.strip())<=80:raise ProductError('Project name required (up to 80 characters)')
    name=name.strip()
    if any(ord(c)<32 for c in name):raise ProductError('Invalid project name')
    slug=re.sub(r'[^a-z0-9]+','-',name.lower()).strip('-')
    if not 2<=len(slug)<=70:raise ProductError('Use a project name containing at least two letters or numbers')
    if slug in {'.','..'}:raise ProductError('Invalid project name')
    industry=data.get('industry','')
    if not isinstance(industry,str) or len(industry)>100:raise ProductError('Invalid industry')
    industry=industry.strip() or None
    core=_validate_pack(data.get('corePack'), 'corePacks')
    addons=data.get('addOns',[])
    if not isinstance(addons,list) or len(addons)>20:raise ProductError('Invalid add-ons')
    addons=list(dict.fromkeys(_validate_pack(x,'addOns') for x in addons))
    addons=[x for x in addons if x]
    if (core or addons) and not industry:raise ProductError('Enter the project industry before choosing packs')
    # Existing core pack and add-ons must be from a coherent industry folder.
    if core:
        prefix=core.split('/')[1]
        if any(a.split('/')[1]!=prefix for a in addons):raise ProductError('Selected add-ons belong to a different core pack')
    region=data.get('region','')
    if not isinstance(region,str) or len(region)>100:raise ProductError('Invalid region')
    region=region.strip()
    # Portable Windows builds must never try to write inside their bundled _MEIPASS directory.
    folder=STATE/'Projects'/slug
    with _registry_lock:
        bundled=read_json(REGISTRY, {'projects':[]})
        extra=read_json(STATE/'custom-projects.json', {'projects':[]})
        if not isinstance(bundled,dict) or not isinstance(bundled.get('projects'),list):
            raise ProductError('Invalid built-in project registry')
        if not isinstance(extra,dict) or not isinstance(extra.get('projects'),list):
            raise ProductError('Invalid local project registry')
        existing=bundled['projects']+extra['projects']
        if any(x.get('id','').lower()==slug or x.get('name','').casefold()==name.casefold() or
                x.get('projectHome','').casefold()==('Projects/'+slug).casefold()
                for x in existing):
            raise ProductError('Project already exists')
        if folder.exists() or (ROOT/'Projects'/slug).exists():
            raise ProductError('Project folder already exists; existing files will never be overwritten')
        classification={'industry':industry,'corePack':core,'addOns':addons,
                        'status':'provisional' if industry and core else 'pending-pack',
                        'reviewRequired':True}
        record={'id':slug,'name':name,'projectHome':'Projects/'+slug,
                'classification':classification,'region':region,'stateProject':True}
        folder.parent.mkdir(parents=True,exist_ok=True)
        created=False
        try:
            folder.mkdir(parents=False,exist_ok=False)
            created=True
            with (folder/'PROJECT-KNOWLEDGE.json').open('x',encoding='utf8') as h:
                json.dump(classification,h,ensure_ascii=False,indent=2)
            with (folder/'AIBO-PROJECT-OVERVIEW.md').open('x',encoding='utf8') as h:
                h.write('# '+name+' — AIBO Custom project\n\nNew independent project workspace.\n'
                        'Pack classification requires explicit review. No external actions are enabled.\n')
            for d in ('01-Business-Foundation','02-Market-and-Industry',
                      '03-Strategy-and-Targets','04-Delivery',
                      '05-Approvals-and-Governance','06-Results-and-Learning'):
                (folder/d).mkdir(exist_ok=False)
            write_json(STATE/'custom-projects.json',{'projects':extra['projects']+[record]})
        except Exception:
            if created:
                import shutil
                shutil.rmtree(folder)
            raise
        return {'ok':True,'project':slug,'totalProjects':len(existing)+1}
