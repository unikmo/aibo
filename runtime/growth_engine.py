"""CariFive Growth OS: local-first evidence ledger, not a pretend marketing connector.

All generated recommendations remain drafts. Publishing uses the existing approved
action gateway and only provider receipts may mark real execution as verified.
"""
from __future__ import annotations
import datetime as dt
import re
import threading
import uuid
from pathlib import Path
try:
    from . import products
except ImportError:
    import products

LOCK=threading.RLock()
CHANNELS=('email','linkedin','tiktok','instagram','facebook','youtube','reddit',
          'internations','x','threads','pinterest','quora','discord','slack',
          'forums','creators','partnerships','pr','events','guerrilla')
PLATFORM_STATES=('EXISTS_AND_USABLE','EXISTS_BUT_WEAK','EXISTS_BUT_OFF_BRAND',
                 'MISSING_AND_RECOMMENDED','MISSING_NOT_NEEDED','BLOCKED_UNKNOWN')
OUTCOMES=('SCALE','ITERATE','STOP','NEEDS_MORE_EVIDENCE','WEBSITE_INTERVENTION_REQUIRED')
OPPORTUNITY_DECISIONS=('IGNORE','WATCH','RESPOND','AMPLIFY','HIJACK MOMENT',
                       'CREATE STUNT','CREATE GROWTH TEST','ESCALATE')
LIFECYCLE=('DRAFT','READY_FOR_APPROVAL','APPROVED','RUNNING','MEASURED','CLOSED')
SCORE_FIELDS=('brandFit','originality','timing','expectedAttention','shareability',
              'conversionPotential','earnedMediaPotential','effort',
              'reputationalRisk','legalIpRisk','misinterpretationRisk')
CREATIVE_FIELDS=('originality','hook','conversion','shareability','naturalness',
                 'audienceRelevance','brandFit')
GOAL_FIELDS=('product','audience','buyer','offer','conversion','positioning',
             'successMetric','successThreshold')
MODES=(0,1,2,3,4)

def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')

def _ids():
    return {p['id'] for p in products.project_records()}

def _validate_project(project):
    if not isinstance(project,str) or project not in _ids():
        raise products.ProductError('Unknown project')
    return project

def _text(x,maxlen=500,required=False):
    if not isinstance(x,str) or (required and not x.strip()) or len(x)>maxlen:
        raise products.ProductError('Missing, excessive or invalid text')
    return x.strip()

def _score(x):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not 0<=x<=10:
        raise products.ProductError('Score must be between 0 and 10')
    return round(float(x),1)

def _file(project):
    return products.STATE/'growth'/f'{project}.json'

def _empty(project):
    return {'project':project,'brand':None,'channels':{},'mischief':None,'autonomy':{
        'level':2,'authorizedChannels':[],'authorizedLowRiskTypes':[],
        'scopeApproved':False},'opportunities':[],'experiments':[],
            'creativeReviews':[]}

def _read(project):
    _validate_project(project)
    data=products.read_json(_file(project),_empty(project))
    if not isinstance(data,dict) or data.get('project')!=project:
        raise products.ProductError('Invalid project growth ledger')
    return data

def _write(project,data):
    products.write_json(_file(project),data)

def _required_fields(data,keys):
    if not isinstance(data,dict) or any(k not in data for k in keys):
        raise products.ProductError('Missing required fields')
    return data

def brand_profile(project,body):
    """Owner-reviewed facts and per-platform classification, never fabricated discovery."""
    _required_fields(body,('product','audience','buyer','offer','conversion',
                            'positioning','successMetric','successThreshold','channels'))
    channels=body['channels']
    if not isinstance(channels,dict) or any(
        ch not in CHANNELS or status not in PLATFORM_STATES for ch,status in channels.items()):
        raise products.ProductError('Invalid channel classification')
    clean={k:_text(body[k],600) for k in GOAL_FIELDS}
    clean['assets']=list(dict.fromkeys(
        _text(a,300,True) for a in body.get('assets',[])
    )) if isinstance(body.get('assets',[]),list) and len(body.get('assets',[]))<=30 else None
    if clean['assets'] is None:raise products.ProductError('Invalid assets')
    clean['evidence']=list(dict.fromkeys(
        _text(a,500,True) for a in body.get('evidence',[])
    )) if isinstance(body.get('evidence',[]),list) and len(body.get('evidence',[]))<=20 else None
    if clean['evidence'] is None:raise products.ProductError('Invalid evidence')
    clean['reviewedByOwner']=body.get('reviewedByOwner') is True
    clean['updatedAt']=_now()
    with LOCK:
        data=_read(project)
        data['brand']=clean
        data['channels']=dict(channels)
        _write(project,data)
    return overview(project)

def readiness(data):
    brand=data.get('brand') or {}
    missing=[k for k in GOAL_FIELDS if not brand.get(k)]
    if not brand.get('assets'):missing.append('assets')
    if not brand.get('evidence'):missing.append('evidence')
    if not any(v=='EXISTS_AND_USABLE' for v in data.get('channels',{}).values()):
        missing.append('usable channel')
    if not brand.get('reviewedByOwner'):missing.append('owner review')
    blocked=any(v=='BLOCKED_UNKNOWN' for v in data.get('channels',{}).values())
    status='BLOCKED' if blocked else ('PASS' if not missing else 'FAIL')
    return {'status':status,'missing':missing,
            'note':'Readiness is based on owner-reviewed records, not verified live social access.'}

def set_mischief(project,body):
    _required_fields(body,('voice','humor','provocation','prohibitedThemes','boundaries'))
    if not isinstance(body['prohibitedThemes'],list) or len(body['prohibitedThemes'])>30:
        raise products.ProductError('Invalid prohibited themes')
    result={'voice':_text(body['voice'],350,True),
            'humor':_score(body['humor']),'provocation':_score(body['provocation']),
            'prohibitedThemes':[_text(x,120,True) for x in body['prohibitedThemes']],
            'boundaries':_text(body['boundaries'],1000,True),'updatedAt':_now()}
    with LOCK:
        data=_read(project);data['mischief']=result;_write(project,data)
    return result

def set_autonomy(project,body):
    """L3/L4 require scoped explicit owner consent; never authorize high-risk categories."""
    level=body.get('level') if isinstance(body,dict) else None
    channels=body.get('authorizedChannels',[]) if isinstance(body,dict) else []
    types=body.get('authorizedLowRiskTypes',[]) if isinstance(body,dict) else []
    if type(level)!=int or level not in MODES:
        raise products.ProductError('Invalid autonomy level')
    if not isinstance(channels,list) or len(channels)>20 or any(c not in CHANNELS for c in channels):
        raise products.ProductError('Invalid channel authorization scope')
    permitted=('routine-post','routine-followup')
    if not isinstance(types,list) or len(types)>2 or any(t not in permitted for t in types):
        raise products.ProductError('Only preapproved low-risk activity types can be delegated')
    approved=body.get('scopeApproved') is True
    if level>=3 and (not approved or not channels or not types):
        raise products.ProductError('L3/L4 requires explicit scope, channels and authorization')
    policy={'level':level,'authorizedChannels':list(dict.fromkeys(channels)) if level>=3 else [],
            'authorizedLowRiskTypes':list(dict.fromkeys(types)) if level>=3 else [],
            'scopeApproved':approved if level>=3 else False,'updatedAt':_now()}
    with LOCK:
        data=_read(project);data['autonomy']=policy;_write(project,data)
    return policy

def requires_specific_approval(kind,body=None):
    """Not even L4 can bypass costly, politically sensitive or legally risky actions."""
    high={'paid-spend','crisis-response','political-content','sensitive-content',
          'legal-claim','account-deletion','competitor-attack','physical-activation',
          'premium-generation','bulk-outreach'}
    return kind in high or (isinstance(body,dict) and body.get('highRisk') is True)

def _assess_opportunity(scores):
    if not isinstance(scores,dict) or set(scores)!=set(SCORE_FIELDS):
        raise products.ProductError('All opportunity criteria must be assessed')
    s={k:_score(v) for k,v in scores.items()}
    upside=sum(s[k] for k in SCORE_FIELDS[:7])/7
    risk=(sum(s[k] for k in SCORE_FIELDS[8:])/3+s['effort'])/2
    priority=round(max(0,min(100,(upside*.75+(10-risk)*.25)*10)),1)
    if max(s[k] for k in SCORE_FIELDS[8:])>=8:
        decision='ESCALATE'
    elif priority>=75 and s['timing']>=7 and s['conversionPotential']>=6:
        decision='CREATE GROWTH TEST'
    elif priority>=58:
        decision='WATCH'
    else:decision='IGNORE'
    return {'scores':s,'priority':priority,'decision':decision,
            'hypothesis':True,'note':'Scores are editorial estimates, not measured reach or sales.'}

def add_opportunity(project,body):
    _required_fields(body,('title','source','reason','scores'))
    assessment=_assess_opportunity(body['scores'])
    item={'id':'OPP-'+uuid.uuid4().hex[:12].upper(),
          'title':_text(body['title'],180,True),
          'source':_text(body['source'],500,True),
          'reason':_text(body['reason'],700,True),
          'createdAt':_now(),**assessment}
    with LOCK:
        data=_read(project);data['opportunities'].append(item);_write(project,data)
    return item

def review_creative(project,body):
    """Creative is checked against the saved brand personality and editorial thresholds."""
    _required_fields(body,('content','channel','scores','factChecked','rulesChecked'))
    data=_read(project)
    if not data.get('mischief'):
        raise products.ProductError('Brand Mischief Profile required before creative review')
    channel=body['channel']
    if channel not in CHANNELS:raise products.ProductError('Unknown channel')
    scores=body['scores']
    if not isinstance(scores,dict) or set(scores)!=set(CREATIVE_FIELDS):
        raise products.ProductError('Seven creative rubric scores required')
    s={k:_score(v) for k,v in scores.items()}
    issues=[k for k in CREATIVE_FIELDS[:4] if s[k]<9]
    issues.extend(k for k in CREATIVE_FIELDS[4:] if s[k]<9.5)
    if body['factChecked'] is not True:issues.append('factual review')
    if body['rulesChecked'] is not True:issues.append('platform-rule review')
    if any(word.casefold() in str(body['content']).casefold()
           for word in data['mischief']['prohibitedThemes']):
        issues.append('prohibited brand theme')
    result={'id':'CRE-'+uuid.uuid4().hex[:12].upper(),'project':project,
            'channel':channel,'passed':not issues,
            'score':round(sum(s.values())/len(s),2),'issues':issues,
            'status':'PASS' if not issues else 'REWRITE_OR_REJECT',
            'content':_text(body['content'],5000,True),
            'estimatedQualityOnly':True,'published':False,'reviewedAt':_now()}
    with LOCK:
        data=_read(project)
        data.setdefault('creativeReviews',[]).append(result)
        _write(project,data)
    return result

def create_experiment(project,body):
    _required_fields(body,('opportunityId','channel','hypothesis','primaryMetric',
                            'threshold','assetRoute','cta'))
    data=_read(project)
    opp=next((x for x in data['opportunities'] if x['id']==body['opportunityId']),None)
    if opp is None:raise products.ProductError('Opportunity not in this brand')
    if body['channel'] not in CHANNELS:raise products.ProductError('Unsupported channel')
    try:threshold=float(body['threshold'])
    except (ValueError,TypeError):raise products.ProductError('Invalid threshold')
    if not 0<threshold<1e12:raise products.ProductError('Threshold must be positive')
    item={'id':'EXP-'+uuid.uuid4().hex[:12].upper(),'project':project,
          'opportunityId':opp['id'],'channel':body['channel'],
          'hypothesis':_text(body['hypothesis'],600,True),
          'primaryMetric':_text(body['primaryMetric'],90,True),
          'threshold':threshold,'assetRoute':_text(body['assetRoute'],350,True),
          'cta':_text(body['cta'],350,True),
          'status':'DRAFT','createdAt':_now(),'creativeApproved':False,
          'externalActionExecuted':False,'measurements':[],'outcome':'NEEDS_MORE_EVIDENCE'}
    with LOCK:
        data=_read(project);data['experiments'].append(item);_write(project,data)
    return item

def transition(project,experiment_id,body):
    _required_fields(body,('status',))
    target=body['status']
    if target not in LIFECYCLE:raise products.ProductError('Invalid experiment state')
    next_states={'DRAFT':('READY_FOR_APPROVAL',),'READY_FOR_APPROVAL':('APPROVED','DRAFT'),
                 'APPROVED':('RUNNING',),'RUNNING':(),
                 'MEASURED':('CLOSED','RUNNING'),'CLOSED':()}
    with LOCK:
        data=_read(project)
        item=next((x for x in data['experiments'] if x['id']==experiment_id),None)
        if not item:raise products.ProductError('Unknown experiment')
        if target not in next_states[item['status']]:
            raise products.ProductError('Invalid lifecycle transition')
        if target=='READY_FOR_APPROVAL':
            if readiness(data)['status']!='PASS':
                raise products.ProductError('Brand readiness must PASS before campaign approval')
            if data.get('channels',{}).get(item['channel'])!='EXISTS_AND_USABLE':
                raise products.ProductError('Campaign channel is not classified usable for this brand')
            opportunity=next((o for o in data['opportunities']
                              if o['id']==item['opportunityId']),None)
            if not opportunity or opportunity['decision'] in ('ESCALATE','IGNORE'):
                raise products.ProductError('Risk or weak-fit opportunity cannot enter routine approval')
            review=next((r for r in data.get('creativeReviews',[])
                         if r['id']==body.get('creativeReviewId') and r['passed']
                         and r['channel']==item['channel']),None)
            if review is None:
                raise products.ProductError('Passing saved creative review required for this channel')
        if target=='APPROVED' and body.get('ownerApproved') is not True:
            raise products.ProductError('Explicit owner approval required')
        if target=='RUNNING':
            evidence=body.get('manualLaunchEvidence')
            if not isinstance(evidence,str) or not evidence.strip() or len(evidence)>500:
                raise products.ProductError('Document manual launch evidence before marking a campaign running')
            if body.get('executionEvidence') is not None:
                raise products.ProductError('Unverified manual notes are not provider receipts')
        item['status']=target
        if target=='READY_FOR_APPROVAL':
            item['creativeApproved']=True
            item['creativeReviewId']=review['id']
        if target=='APPROVED':item['ownerApprovedAt']=_now()
        if target=='RUNNING':
            item['manualLaunchEvidence']=evidence.strip()
            item['launchVerification']='manual-unverified'
            item['externalActionExecuted']=False
        item['updatedAt']=_now()
        _write(project,data)
        return item

def measure(project,experiment_id,body):
    _required_fields(body,('value','source','observedAt'))
    try:value=float(body['value'])
    except (TypeError,ValueError):raise products.ProductError('Invalid measurement value')
    if not 0<=value<1e12:raise products.ProductError('Invalid measurement value')
    entry={'value':value,'source':_text(body['source'],500,True),
           'observedAt':_text(body['observedAt'],50,True),
           'recordedAt':_now(),'verified':False}
    try:dt.datetime.fromisoformat(entry['observedAt'].replace('Z','+00:00'))
    except ValueError:raise products.ProductError('Invalid observation timestamp')
    issue=None
    if body.get('websiteEvidence') is True:
        issue=_text(body.get('websiteIssue'),700,True)
        reference=_text(body.get('websiteEvidenceRef'),500,True)
    with LOCK:
        data=_read(project)
        item=next((x for x in data['experiments'] if x['id']==experiment_id),None)
        if not item:raise products.ProductError('Unknown experiment')
        if item['status'] not in ('RUNNING','MEASURED'):
            raise products.ProductError('Experiment must be running before measurements')
        item['measurements'].append(entry)
        item['status']='MEASURED'
        item['outcome']=('WEBSITE_INTERVENTION_REQUIRED' if body.get('websiteEvidence') is True
                         else ('SCALE' if value>=item['threshold'] else
                               'ITERATE' if value>=item['threshold']*.5 else 'STOP'))
        item['outcomeIsProvisional']=True
        if issue is not None:
            item['websiteIntervention']={
                'id':'WEB-'+uuid.uuid4().hex[:12].upper(),
                'status':'PENDING_BUILD_REVIEW',
                'issue':issue,'evidenceRef':reference,
                'observedMetric':item['primaryMetric'],'observedValue':value,
                'source':entry['source'],'createdAt':_now(),
                'note':'Request for the Build module; no website modification authorized or executed.'}
        _write(project,data)
    return {'experiment':item,'note':'Manually entered metrics and outcomes are provisional until independently verified.'}

def today(project=None):
    """Select one highest-value actionable task, not a fabricated live trend."""
    projects=[project] if project else sorted(_ids())
    options=[]
    for pid in projects:
        d=_read(pid);ready=readiness(d)
        if ready['status']!='PASS':continue
        for opp in d['opportunities']:
            if opp['decision'] in ('CREATE GROWTH TEST','WATCH'):
                if not any(e['opportunityId']==opp['id'] for e in d['experiments']):
                    options.append({'project':pid,'opportunityId':opp['id'],
                                    'objective':opp['title'],'priority':opp['priority'],
                                    'recommendedAction':'Prepare a scoped growth experiment for review',
                                    'execution':'not-started','source':opp['source']})
    options.sort(key=lambda x:(-x['priority'],x['project'],x['opportunityId']))
    if options:return {'status':'SUPPORTED','action':options[0],'candidates':len(options)}
    return {'status':'NEEDS_MORE_EVIDENCE','action':None,
            'reason':'No owner-reviewed ready brand has an eligible untested opportunity.'}

def overview(project):
    data=_read(project)
    return {'project':project,'brand':data['brand'],'channels':data['channels'],
            'readiness':readiness(data),'mischief':data['mischief'],
            'autonomy':data['autonomy'],'opportunities':data['opportunities'],
            'experiments':data['experiments'],'creativeReviews':data.get('creativeReviews',[]),
            'note':'Local marketing planning and evidence ledger only. No posts, messages, purchases or monitoring were performed.'}

def dashboard():
    ids=sorted(_ids())
    rows=[]
    for pid in ids:
        data=_read(pid)
        if data['brand'] is None and not data['experiments']:continue
        rows.append({'project':pid,'readiness':readiness(data)['status'],
                     'experiments':len(data['experiments']),
                     'measured':sum(bool(e['measurements']) for e in data['experiments']),
                     'outcomes':{k:sum(e['outcome']==k for e in data['experiments']) for k in OUTCOMES}})
    return {'brands':rows,'count':len(rows),'verifiedCommercialOutcomes':None,
            'note':'No provider analytics have been independently reconciled.'}
