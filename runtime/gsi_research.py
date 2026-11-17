"""GSI CSV evidence gate and additive research snapshot staging; stdlib only.

No external network. No AI claim invention. Data preserved verbatim.
"""
import argparse,csv,hashlib,json,shutil,sys,datetime,uuid
from collections import Counter
from pathlib import Path
SCHEMA=Path(__file__).resolve().parent.parent/'Industry-Packs'/'Financial-Markets-Institutional-Investment'/'Add-Ons'/'Sovereign-Wealth-Fund-Intelligence'/'REFERENCE-SCHEMA.json'
PROJECT=Path(__file__).resolve().parent.parent/'Projects'/'gulf-sovereign-intelligence'
class SchemaError(ValueError):pass

def inspect_csv(path,kind):
    specs=json.loads(SCHEMA.read_text(encoding='utf8'))['datasets'][kind]['columns']
    p=Path(path)
    with p.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=specs:
            missing=[c for c in specs if c not in (reader.fieldnames or [])]
            extra=[c for c in (reader.fieldnames or []) if c not in specs]
            raise SchemaError(f'{kind}: expected exact v4.9 columns/order; missing={missing[:8]} extra={extra[:8]}')
        rows=list(reader)
    if any(None in r for r in rows):raise SchemaError(f'{kind}: malformed CSV extra columns')
    out={'kind':kind,'rows':len(rows),'columns':len(specs),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    if kind in ('master','ledger'):
        ids=[r['master_record_id'] for r in rows]
        duplicated=len(ids)-len(set(ids))
        out['duplicateIds']=duplicated
        out['originalInclusionDecisions']=dict(Counter(r['inclusion_decision'] for r in rows))
        out['explicitNullTicketCount']=sum(not r['investor_specific_amount'].strip() for r in rows)
        out['unresolvedClaimsCount']=sum(bool(r['outstanding_material_claims'].strip()) for r in rows)
        out['missingIndependentSourceCount']=sum(not r['independent_source'].strip() for r in rows)
        out['verificationCautions']=['A source grade applies to its specific claim, not necessarily settlement','An independent_source URL does not by itself prove source-family independence','Investor-specific ticket blanks must never be inferred from headline amounts']
    if kind=='coverage':
        out['coverageStatuses']=dict(Counter(r['coverage_status'] for r in rows))
        out['openWorkGroups']=sum(bool(r['open_work'].strip()) for r in rows)
    return out

def stage(inputs, output_dir=None):
    # Validate every input before creating any destination.
    reports={kind:inspect_csv(path,kind) for kind,path in inputs.items()}
    base=Path(output_dir) if output_dir else PROJECT/'08-Research-Snapshots'
    base.mkdir(parents=True,exist_ok=True)
    folder=base/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
    folder.mkdir(exist_ok=False)
    try:
        for kind,path in inputs.items():
            # Never store untrusted original names or escape the destination directory.
            with (folder/(kind+'.csv')).open('xb') as dst:
                with Path(path).open('rb') as src:shutil.copyfileobj(src,dst)
        manifest={'createdAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':'raw-snapshot-no-claim-upgrade','datasets':reports}
        (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
        return str(folder),reports
    except Exception:
        shutil.rmtree(folder)
        raise

def main():
    a=argparse.ArgumentParser(description='Validate or append-only stage GSI v4.9 research CSVs')
    a.add_argument('mode',choices=('audit','stage'))
    for k in ('master','ledger','coverage'):a.add_argument('--'+k,type=Path)
    a.add_argument('--output-dir',type=Path)
    x=a.parse_args();sources={k:getattr(x,k) for k in ('master','ledger','coverage') if getattr(x,k) is not None}
    if not sources:a.error('Specify at least one input: --master, --ledger or --coverage')
    try:
        if x.mode=='audit':result={'datasets':{k:inspect_csv(v,k) for k,v in sources.items()}}
        else:
            path,reports=stage(sources,x.output_dir);result={'snapshotFolder':path,'datasets':reports}
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (OSError,SchemaError,ValueError) as e:
        print('GSI validation failed: '+str(e),file=sys.stderr);return 2
    return 0
if __name__=='__main__':raise SystemExit(main())
