"""Local, project-scoped relationship tracking and TPT listing preparation.

No scraping, messaging, posting, account access or automated engagement.
"""
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
try:
    from . import products
except ImportError:
    import products

ROOT = products.STATE / 'relationship-work'
CHANNELS = ('internations','email','linkedin','other')
STATES = ('research','draft','contacted','replied','closed')


def _project(project):
    if not isinstance(project,str) or project not in {p['id'] for p in products.custom_projects()}:
        raise products.ProductError('Unknown project')
    return project


def _store(project):
    _project(project)
    return ROOT / (project + '.json')


def _read(project):
    data=products.read_json(_store(project),{'contacts':[], 'listings':[], 'activities':[]})
    return data if isinstance(data,dict) else {'contacts':[], 'listings':[], 'activities':[]}


def _text(value,limit=500):
    if not isinstance(value,str):raise products.ProductError('Text field required')
    value=value.strip()
    if len(value)>limit:raise products.ProductError('Text field too long')
    return value


def _now():return datetime.now(timezone.utc).isoformat(timespec='seconds')


def overview(project):
    data=_read(project)
    return {'project':project,'contacts':data.get('contacts',[]), 'listings':data.get('listings',[]), 'activities':data.get('activities',[])[-40:],
            'capabilities':{'crm':'local','outreach':'draft-and-review-only','internations':'manual-send-only','tpt':'draft-and-export-only'}}


def save_contact(project,body):
    if not isinstance(body,dict):raise products.ProductError('Invalid contact')
    channel=body.get('channel','other')
    if channel not in CHANNELS:raise products.ProductError('Unknown channel')
    name=_text(body.get('name',''),120)
    if not name:raise products.ProductError('Contact name required')
    handle=_text(body.get('handle',''),180)
    organization=_text(body.get('organization',''),150)
    details=_text(body.get('context',''),2000)
    if not handle and not organization:raise products.ProductError('A profile/handle or organization is required')
    state=body.get('status','research')
    if state not in STATES:raise products.ProductError('Invalid status')
    data=_read(project)
    identity=(channel,(handle or name+'|'+organization).casefold())
    for contact in data['contacts']:
        check=(contact['channel'],(contact['handle'] or contact['name']+'|'+contact['organization']).casefold())
        if check==identity:raise products.ProductError('Possible duplicate contact; update existing record instead')
    record={'id':uuid.uuid4().hex,'channel':channel,'name':name,'handle':handle,'organization':organization,
            'context':details,'status':state,'createdAt':_now(),'updatedAt':_now(),'lastContactAt':None}
    data['contacts'].append(record)
    products.write_json(_store(project),data)
    return record


def prepare_message(project,body):
    if not isinstance(body,dict):raise products.ProductError('Invalid message')
    data=_read(project)
    cid=body.get('contactId')
    target=next((x for x in data['contacts'] if x['id']==cid),None)
    if target is None:raise products.ProductError('Contact not found')
    message=_text(body.get('message',''),4000)
    if not message:raise products.ProductError('Draft is required')
    reason=_text(body.get('reason',''),1000)
    if not reason:raise products.ProductError('Individual relevance/context required')
    # Exact copies cannot be queued for InterNations recipients; a timestamp is not a compliance bypass.
    if target['channel']=='internations':
        normalized=' '.join(message.casefold().split())
        for activity in data['activities']:
            if activity['kind']=='outreach_draft' and activity.get('channel')=='internations' and activity.get('contactId')!=cid and ' '.join(activity.get('message','').casefold().split())==normalized:
                raise products.ProductError('Repeated InterNations message. Draft an individually relevant message, not a duplicate.')
    item={'id':uuid.uuid4().hex,'kind':'outreach_draft','contactId':cid,'contactName':target['name'],
          'channel':target['channel'],'reason':reason,'message':message,'createdAt':_now(),'status':'review-required'}
    data['activities'].append(item)
    products.write_json(_store(project),data)
    return item


def log_manual_contact(project,body):
    if not isinstance(body,dict):raise products.ProductError('Invalid contact update')
    data=_read(project)
    target=next((x for x in data['contacts'] if x['id']==body.get('contactId')),None)
    if target is None:raise products.ProductError('Contact not found')
    state=body.get('status')
    if state not in ('contacted','replied','closed'):raise products.ProductError('Invalid contact status')
    note=_text(body.get('note',''),1500)
    if not note:raise products.ProductError('Evidence or contact note required')
    target['status']=state;target['updatedAt']=_now()
    if state=='contacted':target['lastContactAt']=_now()
    data['activities'].append({'id':uuid.uuid4().hex,'kind':'manual_contact_update','contactId':target['id'],
        'contactName':target['name'],'channel':target['channel'],'status':state,'note':note,'createdAt':_now()})
    products.write_json(_store(project),data)
    return target


def save_tpt_listing(project,body):
    if not isinstance(body,dict):raise products.ProductError('Invalid listing')
    title=_text(body.get('title',''),160)
    subject=_text(body.get('subject',''),120)
    grade=_text(body.get('grade',''),100)
    description=_text(body.get('description',''),4000)
    keywords=_text(body.get('keywords',''),500)
    rights=_text(body.get('rightsNotes',''),1200)
    if not title or not description or not subject or not grade:
        raise products.ProductError('Title, subject, grade and description required')
    item={'id':uuid.uuid4().hex,'title':title,'subject':subject,'grade':grade,'description':description,
          'keywords':keywords,'rightsNotes':rights,'status':'draft','publication':'not-connected',
          'createdAt':_now()}
    data=_read(project)
    data['listings'].append(item)
    products.write_json(_store(project),data)
    return item
