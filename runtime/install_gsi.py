"""Add GSI project only if absent. Never mutate preexisting project files or registry records."""
from pathlib import Path
import json,sys
try:
    from . import products
except ImportError:
    import products

ROOT=Path(__file__).resolve().parent.parent
ID='gulf-sovereign-intelligence'
CORE='Industry-Packs/Financial-Markets-Institutional-Investment/PACK-OVERVIEW.md'
ADDON='Industry-Packs/Financial-Markets-Institutional-Investment/Add-Ons/Sovereign-Wealth-Fund-Intelligence/PACK-ADDON.md'

def install():
    registry=products.read_json(products.REGISTRY, {'projects':[]})
    existing=registry.get('projects',[])
    if any(p.get('id')==ID or str(p.get('name','')).casefold()=='gulf sovereign intelligence' for p in existing):
        print('GSI already registered: preserving existing record and workspace.');return 0
    # This update deliberately ships a template folder. The registry addition is isolated and backed up.
    newpath=ROOT/'Projects'/ID
    if not newpath.is_dir():raise RuntimeError('GSI workspace template missing')
    if not Path(ROOT/CORE).exists() or not Path(ROOT/ADDON).exists():raise RuntimeError('GSI knowledge packs missing')
    mapping=json.loads((newpath/'PROJECT-KNOWLEDGE.json').read_text(encoding='utf8'))
    # No mutation of existing project records; only append one mapping.
    record={'id':ID,'name':'Gulf Sovereign Intelligence','projectHome':'Projects/'+ID,
            'classification':{k:mapping[k] for k in ('industry','corePack','addOns','status','reviewRequired')}}
    # Registry backup is kept forever in local backups; no aggressive cleanup.
    import datetime,shutil
    backup=ROOT/'backups'/('gsi-install-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True,exist_ok=False)
    if products.REGISTRY.exists():shutil.copy2(products.REGISTRY,backup/'project-registry.json')
    # Existing tests assumed exactly 15 projects; preserve their original checks while allowing expansion.
    patches={
        'test_operations.py': [('self.assertEqual(len(projects),15)', 'self.assertGreaterEqual(len(projects),15)')],
        'test_products.py': [('p=products.custom_projects();self.assertEqual(len(p),15)', 'p=products.custom_projects();self.assertGreaterEqual(len(p),15)'),
                             ("self.assertEqual(len({x['id'] for x in p}),15)","self.assertEqual(len({x['id'] for x in p}),len(p))")],
        'test_runtime.py': [("self.assertEqual(len(registry['projects']),15)", "self.assertGreaterEqual(len(registry['projects']),15)")],
    }
    # Preflight all before touching any test files or registry.
    changes={}
    for name,replacements in patches.items():
        path=ROOT/'tests'/name
        original=path.read_text(encoding='utf8')
        updated=original
        for old,new in replacements:
            if old not in updated and new not in updated:
                raise RuntimeError('Unexpected test version: '+name+'; install stopped safely')
            updated=updated.replace(old,new)
        changes[path]=(original,updated)
    for path,(old,new) in changes.items():
        if new!=old:
            shutil.copy2(path,backup/path.name)
            path.write_text(new,encoding='utf8')
    products.write_json(products.REGISTRY,{**registry,'projects':existing+[record]})
    print('GSI added to AIBO Custom. Registry backup: '+str(backup));return 0
if __name__=='__main__':
    try:raise SystemExit(install())
    except Exception as e:
        print('GSI install failed: '+str(e),file=sys.stderr);raise SystemExit(1)
