"""Project-scoped agent operating preferences; no credentials or entitlements stored."""
from pathlib import Path
import re
try:
    from . import products
except ImportError:
    import products

PATH=products.STATE/'agent-setup.json'
PERMISSIONS=('research','read_browser','write_local','write_browser','read_mail','draft_mail','send_mail','publish','deploy','spend')
DEFAULTS={'research':True,'read_browser':True,'write_local':True,'write_browser':True,'read_mail':True,'draft_mail':True,'send_mail':False,'publish':False,'deploy':False,'spend':False}


def _project(pid):
    if not isinstance(pid,str) or pid not in ({p['id'] for p in products.custom_projects()} | {s['id'] for s in products.standard_state()['slots']}):
        raise products.ProductError('Unknown project')


def _defaults():
    return {'agent':'soni','workingStyle':'autonomous','mailboxes':[],'permissions':dict(DEFAULTS)}


def _clean_mailboxes(boxes):
    if not isinstance(boxes,list) or len(boxes)>30:raise products.ProductError('Invalid mailboxes')
    result=[]
    for b in boxes:
        if not isinstance(b,dict):raise products.ProductError('Invalid mailbox entry')
        address=b.get('address','').strip().lower()
        if not re.fullmatch(r'[^\s@<>]{1,80}@[^\s@<>]{1,160}\.[A-Za-z]{2,}',address):raise products.ProductError('Invalid mailbox address')
        entry={'address':address,'enabled':b.get('enabled') is True}
        if entry['address'] not in {x['address'] for x in result}:result.append(entry)
    return result


def get(pid):
    _project(pid)
    saved=products.read_json(PATH,{})
    config=saved.get(pid,{})
    d=_defaults()
    if isinstance(config,dict):
        d['agent']=config.get('agent',d['agent'])
        d['workingStyle']=config.get('workingStyle',d['workingStyle'])
        d['mailboxes']=config.get('mailboxes',[])
        d['permissions'].update({k:v for k,v in config.get('permissions',{}).items() if k in PERMISSIONS and isinstance(v,bool)})
    return {'project':pid,**d,'note':'Preferences are saved locally. Actual external execution still requires a verified adapter and existing authorization gates.'}


def update(pid,body):
    _project(pid)
    if not isinstance(body,dict):raise products.ProductError('Invalid agent setup')
    allowed={'agent','workingStyle','mailboxes','permissions'}
    if set(body)-allowed:raise products.ProductError('Unknown settings')
    existing=get(pid)
    if 'agent' in body:
        if body['agent'] not in ('soni','specialists'):raise products.ProductError('Unknown agent mode')
        existing['agent']=body['agent']
    if 'workingStyle' in body:
        if body['workingStyle'] not in ('autonomous','supervised'):raise products.ProductError('Unknown working style')
        existing['workingStyle']=body['workingStyle']
    if 'mailboxes' in body:existing['mailboxes']=_clean_mailboxes(body['mailboxes'])
    if 'permissions' in body:
        perms=body['permissions']
        if not isinstance(perms,dict) or set(perms)-set(PERMISSIONS) or any(type(x) is not bool for x in perms.values()):
            raise products.ProductError('Invalid permissions')
        existing['permissions'].update(perms)
    saved=products.read_json(PATH,{})
    saved[pid]={k:existing[k] for k in allowed}
    products.write_json(PATH,saved)
    return get(pid)


def assert_permission(pid,permission):
    if permission not in PERMISSIONS:raise products.ProductError('Unknown permission')
    if not get(pid)['permissions'][permission]:
        raise products.ProductError('Action disabled in Agent Setup for this project')
