"""Bounded, per-project conversational memory and explicit read-only comparisons.

Memory is extractive, local and provider-free. It never writes to other projects,
never copies whole conversations and never treats model answers as verified evidence.
"""
from __future__ import annotations
import datetime as dt
import re
from pathlib import Path

try:
    from . import products
except ImportError:
    import products

MEMORY_DIR=products.STATE/'soni-memory'
MAX_MEMORY_ITEMS=12
MAX_ENTRY_CHARS=360
MAX_CONTEXT_CHARS=3200
MAX_RECENT_TURNS=3
MAX_PINNED=6
PIN_WORDS=re.compile(r'\b(?:remember|decided|agreed|must|never|always|priority|constraint|require|prefer)\b',re.I)
COMPARISON_WORDS=re.compile(
    r'\b(compare|comparison|versus|vs\.?|contrast|similarities|differences|across projects|between projects)\b',
    re.IGNORECASE,
)
SENSITIVE=re.compile(r'(?i)(?:api[_ -]?key|password|client_secret|access_token|private[_ -]?key|authorization\s*:|bearer\s)')
LOCAL_ONLY_FIELDS=('name','goal','audience','website','region','successMeasure')

def _clean(text,limit):
    lines=[line.strip() for line in str(text or '').splitlines() if line.strip() and not SENSITIVE.search(line)]
    return re.sub(r'\s+',' ',' '.join(lines)).strip()[:limit]

def referenced(project_id,request):
    """Find managed project mentions exactly; never interpret arbitrary text as an ID."""
    results=[]
    for item in products.project_records():
        if item['id']==project_id:continue
        name=item.get('name','').strip()
        if len(name)>=4 and re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',request,re.I):
            results.append(item)
    return sorted(results,key=lambda x:x['name'].casefold())

def comparison_scope(project_id,request):
    others=referenced(project_id,request)
    if not others:return []
    if not COMPARISON_WORDS.search(request):return None
    if len(others)>3:
        raise products.ProductError('Compare at most three other projects per request')
    return [item['id'] for item in others]

def _read_profile(project_id):
    path=products.STATE/'workspaces'/(project_id+'.json')
    raw=products.read_json(path,{})
    if raw.get('complete') is not True or raw.get('reviewed') is not True:
        return None
    fields=raw.get('fields') or {}
    return {field:_clean(fields.get(field,''),220) for field in LOCAL_ONLY_FIELDS
            if isinstance(fields.get(field),str) and fields.get(field,'').strip()}

def comparison_context(project_ids):
    """No project files, chat histories, source excerpts, agent teams or credentials."""
    output=[]
    for pid in project_ids:
        project=next((p for p in products.project_records() if p['id']==pid),None)
        if project is None:raise products.ProductError('Unknown comparison project')
        fields=_read_profile(pid)
        if fields is None:
            output.append({'project':project['name'],'status':'NO_OWNER_REVIEWED_SUMMARY'})
        else:
            output.append({'project':project['name'],'status':'OWNER_REVIEWED_PROFILE',
                           'fields':fields})
    import json
    return ('READ-ONLY COMPARISON DATA (separate projects; never share tasks or permissions). '
            'Only owner-reviewed project profile fields are included. Missing profiles are unknown; '
            'do not infer progress or access private conversations. '
            +json.dumps(output,ensure_ascii=False))[:4200]

def _path(project_id):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',project_id):
        raise products.ProductError('Invalid project ID')
    return products.STATE/'soni-memory'/(project_id+'.json')

def memory_state(project_id):
    raw=products.read_json(_path(project_id),{})
    entries=raw.get('entries',[])
    if not isinstance(entries,list):entries=[]
    pinned=raw.get('pinned',[])
    if not isinstance(pinned,list):pinned=[]
    return {'project':project_id,'entries':entries[-MAX_MEMORY_ITEMS:],
            'pinned':pinned[-MAX_PINNED:],
            'completedTurns':max(0,int(raw.get('completedTurns',0))),
            'compactedTurns':max(0,int(raw.get('compactedTurns',0)))}

def previous_context(project_id,runs_dir):
    """Use retained extracted memories and three recent completed local turns.

    Never reread or compact other-project conversations. Extraction uses no AI calls.
    """
    memory=memory_state(project_id)
    pieces=[]
    for e in memory['entries']:
        if isinstance(e,dict) and 'text' in e:
            pieces.append(_clean(e['text'],MAX_ENTRY_CHARS))
    recent=[]
    if Path(runs_dir).exists():
        for file in Path(runs_dir).glob('*.json'):
            item=products.read_json(file,{})
            if item.get('project')!=project_id or item.get('status')!='completed':
                continue
            # Cross-project comparisons remain in THIS project's recent chat only.
            # They are never promoted into lasting project-specific memory.
            answer=(item.get('result') or {}).get('soni','')
            if not isinstance(answer,str) or not answer:continue
            kind='Read-only cross-project comparison: ' if item.get('crossProjectReadOnly') else ''
            recent.append((item.get('createdAt',''),kind+_clean(item.get('task',''),220),_clean(answer,420)))
    recent=sorted(recent,reverse=True)[:MAX_RECENT_TURNS]
    recent.reverse()
    text='RETAINED LOCAL CONTEXT (unverified conversational notes, not factual evidence):\n'
    if recent:text+='Recent turns:\n'+'\n'.join('User: '+q+'\nSoni: '+a for _,q,a in recent)
    if memory['pinned']:
        text+='\nOwner instructions from earlier turns (not independently verified):\n'
        text+='\n'.join('- '+_clean(p,240) for p in memory['pinned'])
    if pieces:text+='\nOlder compressed notes:\n'+'\n'.join('- '+p for p in pieces[-4:] if p)
    if not pieces and not recent and not memory['pinned']:return '',{'recentTurns':0,'memoryItems':0,'contextCharacters':0}
    text=text[:MAX_CONTEXT_CHARS]
    return text,{'recentTurns':len(recent),'memoryItems':len(pieces),'contextCharacters':len(text),
                 'compactedTurns':memory['compactedTurns']}

def remember(project_id,task,answer,cross_project=False):
    if cross_project:return memory_state(project_id)
    clean_task=_clean(task,180)
    clean_answer=_clean(answer,300)
    if not clean_task or not clean_answer:return memory_state(project_id)
    path=_path(project_id)
    state=memory_state(project_id)
    entries=state['entries']
    # Deterministic extractive compaction: older turns reduce to one bounded line
    # and are clearly labeled unverified. No summarization model calls or costs.
    sentence='Question: '+clean_task+' | Response (unverified): '+clean_answer
    entries.append({'text':sentence[:MAX_ENTRY_CHARS],
                    'at':dt.datetime.now(dt.timezone.utc).isoformat()})
    dropped=max(0,len(entries)-MAX_MEMORY_ITEMS)
    entries=entries[-MAX_MEMORY_ITEMS:]
    pinned=state['pinned']
    if PIN_WORDS.search(clean_task) and clean_task not in pinned:
        pinned=(pinned+[clean_task])[-MAX_PINNED:]
    output={'project':project_id,'entries':entries,'pinned':pinned,
            'completedTurns':state['completedTurns']+1,
            'compactedTurns':state['compactedTurns']+dropped,
            'method':'deterministic-extractive-no-model',
            'updatedAt':dt.datetime.now(dt.timezone.utc).isoformat()}
    products.write_json(path,output)
    return output
