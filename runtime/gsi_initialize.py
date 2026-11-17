"""Initialize separate research work queue; never alters GSI master/ledger/coverage schema."""
from pathlib import Path
import json, argparse, datetime
ROOT=Path(__file__).resolve().parent.parent
WORK=ROOT/'Projects'/'gulf-sovereign-intelligence'/'01-Intake'/'research-queue-2020-2026.json'

def initialize(out=WORK):
    out=Path(out)
    if out.exists():
        data=json.loads(out.read_text(encoding='utf8'))
        if len(data.get('months',[]))!=83:raise ValueError('Existing research queue has an unexpected shape; refusing to replace it')
        return {'result':'existing_preserved','path':str(out),'months':len(data['months'])}
    months=[]
    for year in range(2020,2027):
        for month in range(1,13 if year<2026 else 12):
            key=f'{year}-{month:02d}'
            months.append({'period':key,'coverage':'UNASSESSED','sourceRegisterReviewed':False,'researchLane':'recent-monitoring' if year>=2025 else 'historical-backfill','notes':'Needs reconciliation against authoritative GSI coverage register'})
    assert len(months)==83
    obj={'kind':'AIBO_WORKFLOW_QUEUE_NOT_GSI_DATABASE','version':1,'researchWindow':{'from':'2020-01','through':'2026-11'},'months':months,'policy':'Workflow coverage is unassessed until actual GSI source-family evidence reviewed; do not infer no deals.'}
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf8') as f:json.dump(obj,f,ensure_ascii=False,indent=2)
    return {'result':'created','path':str(out),'months':83}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();print(json.dumps(initialize(a.output or WORK),indent=2))
