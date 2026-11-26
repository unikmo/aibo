"""Local project-scoped missing-connection task queue.

Does not execute business writes. Verification and resumption are explicit owner actions.
"""
from __future__ import annotations
import re
import uuid
import threading
from datetime import datetime,timezone
try:
    from . import products, connector_catalog, connection_runtime, workspace, oauth_local
except ImportError:
    import products, connector_catalog, connection_runtime, workspace, oauth_local

_LOCK=threading.RLock()
PATH=products.STATE/'connection-dependent-work.json'
# Conservative matching; human can override via UI service selection.
TRIGGERS={
 'github':('github','repository','pull request'),
 'vercel':('vercel','deployment preview'),
 'netlify':('netlify',),
 'resend':('resend',),
 'deepl-api':('deepl',),
 'buffer':('buffer','social publishing'),
}

def infer_connector(task):
    value=task.lower()
    for cid,terms in TRIGGERS.items():
        if any(re.search(r'\b'+re.escape(term)+r'\b',value) for term in terms):return cid
    return None

def records(project=None):
    data=products.read_json(PATH,[])
    if not isinstance(data,list):return []
    return [x for x in data if project is None or x['project']==project]

def queue(payload):
    if not isinstance(payload,dict):raise products.ProductError('Invalid task')
    project=payload.get('project')
    if project not in {x['id'] for x in products.project_records()}:raise products.ProductError('Unknown project')
    if not workspace.setup_state(project)['complete']:
        raise products.ProductError('Initialize the project before starting work')
    task=payload.get('task','')
    if not isinstance(task,str) or not 5<=len(task.strip())<=1500:raise products.ProductError('Invalid task')
    provider=payload.get('provider','mock')
    if provider not in workspace.PROVIDERS:raise products.ProductError('Unknown AI provider')
    if workspace.requires_api_consent(provider) and payload.get('consent') is not True:raise products.ProductError('API-provider data sharing requires explicit consent')
    requested=payload.get('connector') or infer_connector(task)
    if requested and requested not in {x['id'] for x in connector_catalog.entries()}:
        raise products.ProductError('Unknown connector')
    connected=(bool(oauth_local.token(project)) if requested=='buffer' else connection_runtime.status(project,requested)['verified']) if requested else True
    status='waiting-for-connection' if not connected else 'ready-to-run'
    item={'id':str(uuid.uuid4()),'project':project,'task':task.strip(),'connector':requested,
          'provider':provider,'consent':payload.get('consent') is True,'status':status,'runId':None,
          'createdAt':datetime.now(timezone.utc).isoformat()}
    with _LOCK:
        data=records();data.append(item);products.write_json(PATH,data)
    if status=='waiting-for-connection':
        connector_catalog.request_connection({'project':project,'connector':requested})
    return {k:v for k,v in item.items() if k!='consent'}

def resume(task_id):
    if not isinstance(task_id,str) or not re.fullmatch(r'[0-9a-f-]{36}',task_id):raise products.ProductError('Invalid task ID')
    with _LOCK:
        data=records();item=next((x for x in data if x['id']==task_id),None)
        if not item:raise products.ProductError('Unknown task')
        if item['status']=='submitted':return {'id':task_id,'status':'submitted','runId':item['runId']}
        if item['status'] not in ('waiting-for-connection','ready-to-run'):raise products.ProductError('Task not ready')
        connected=(bool(oauth_local.token(item['project'])) if item['connector']=='buffer' else connection_runtime.status(item['project'],item['connector'])['verified']) if item['connector'] else True
        if not connected:
            raise products.ProductError('Connection not verified yet')
        # For safety, all requests still go through analysis-only workspace.start_run.
        run=workspace.start_run(item['project'],{'task':item['task'],'provider':item['provider'],'consent':item['consent']})
        item['status']='submitted';item['runId']=run['id']
        products.write_json(PATH,data)
        return {'id':task_id,'status':'submitted','runId':run['id']}


def resume_verified(project,connector):
    """Resume analysis-only tasks after an explicitly verified project connection.

    Never resumes publication, sending, deployment or browser writes.
    """
    resumed=[]
    for item in records(project):
        if item.get('connector')==connector and item.get('status')=='waiting-for-connection':
            try:resumed.append(resume(item['id']))
            except products.ProductError:pass
    return resumed
