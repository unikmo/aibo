"""Local operational reporting for Custom; never invents business performance."""
from __future__ import annotations
import datetime as dt
import threading
import uuid
try:
    from . import products, workspace
except ImportError:
    import products, workspace

LOCK=threading.RLock()
KPI_FILE=products.STATE/'portfolio-kpis.json'

def _projects():
    return products.custom_projects()

def _kpis():
    return products.read_json(KPI_FILE,{})

def all_runs():
    allowed={p['id'] for p in _projects()}
    items=[]
    if workspace.RUNS_DIR.exists():
        for f in workspace.RUNS_DIR.glob('*.json'):
            x=products.read_json(f,{})
            if isinstance(x,dict) and x.get('project') in allowed and x.get('status'):
                # Do not put full project context or responses into summary endpoints.
                items.append({k:x.get(k) for k in ('id','project','task','status','provider','createdAt','updatedAt','error')})
    return sorted(items,key=lambda x:x.get('createdAt') or '',reverse=True)

def overview():
    projects=_projects(); runs=all_runs(); metrics=_kpis()
    counts={s:sum(1 for r in runs if r['status']==s) for s in ('queued','running','completed','failed','interrupted')}
    projects_out=[]
    for p in projects:
        mine=[r for r in runs if r['project']==p['id']]
        kp=metrics.get(p['id'],[])
        has_pack=bool(p.get('corePack')) and p.get('classificationStatus') not in ('pending-pack',)
        setup=bool(p.get('setupComplete'))
        # Operational readiness is explicitly separate from business outcomes.
        readiness='Setup needed' if not setup else ('Pack review' if not has_pack else 'Ready for analysis')
        if any(r['status'] in ('failed','interrupted') for r in mine[:1]): readiness='Work needs review'
        projects_out.append({'id':p['id'],'name':p['name'],'industry':p.get('industry'),
            'setupComplete':setup,'readiness':readiness,'corePackReady':has_pack,
            'tasksCompleted':sum(r['status']=='completed' for r in mine),
            'tasksOpen':sum(r['status'] in ('queued','running') for r in mine),
            'tasksFailed':sum(r['status'] in ('failed','interrupted') for r in mine),
            'kpis':kp[:12]})
    return {'projects':projects_out,'counts':{'projects':len(projects),'setupComplete':sum(p['setupComplete'] for p in projects_out),
        'needsSetup':sum(not p['setupComplete'] for p in projects_out),**counts},
        'recentWork':runs[:25], 'pendingApprovals':None,'pendingApprovalsNote':'Approval workflow is not connected yet.',
        'businessHealth':None,'businessHealthNote':'No validated performance connectors are configured.',
        'updatedAt':dt.datetime.now(dt.timezone.utc).isoformat()}

def save_kpi(project_id,data):
    if project_id not in {p['id'] for p in _projects()}:raise products.ProductError('Unknown project')
    if not isinstance(data,dict):raise products.ProductError('Invalid KPI')
    name=data.get('name'); value=data.get('value'); unit=data.get('unit',''); source=data.get('source','manual')
    if not isinstance(name,str) or not 1<=len(name.strip())<=75:raise products.ProductError('KPI name required (1–75 chars)')
    if not isinstance(value,str) or not 1<=len(value.strip())<=60:raise products.ProductError('KPI value required (1–60 chars)')
    if not isinstance(unit,str) or len(unit)>30:raise products.ProductError('Invalid unit')
    if not isinstance(source,str) or not 1<=len(source.strip())<=100:raise products.ProductError('Source required')
    for text in (name,value,unit,source):
        if any(ord(ch)<32 for ch in text):raise products.ProductError('Invalid control characters')
    with LOCK:
        all_metrics=_kpis(); entries=all_metrics.get(project_id,[])
        if len(entries)>=12:raise products.ProductError('Maximum 12 KPIs per project')
        item={'id':str(uuid.uuid4()),'name':name.strip(),'value':value.strip(),'unit':unit.strip(),
              'source':source.strip(),'recordedAt':dt.datetime.now(dt.timezone.utc).isoformat()}
        all_metrics[project_id]=entries+[item]
        products.write_json(KPI_FILE,all_metrics)
        return item
