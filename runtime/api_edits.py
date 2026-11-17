"""Generate a restricted multi-file proposal using OpenAI/Anthropic model adapters.
Does not silently write files. Apply with operations.py apply-patch after review.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from aibo import AiboError, project_info, context, provider_call
from operations import safe_workspace,safe_file


def propose(project,workspace,goal,provider,files,output,model=None):
    project_info(project)
    cwd=safe_workspace(workspace)
    if provider not in ('openai','anthropic'):
        raise AiboError('Only authenticated API providers supported')
    if not 1<=len(files)<=8:
        raise AiboError('Select 1-8 concrete files; do not upload whole repositories to providers')
    chosen=[]
    for rel in files:
        target=safe_file(cwd,rel)
        if target.is_file() and target.stat().st_size>25000:
            raise AiboError('Source file too large for bounded API editing: '+rel)
        raw=target.read_bytes() if target.exists() else None
        chosen.append({'path':rel,'sha256':hashlib.sha256(raw).hexdigest() if raw is not None else None,'content':raw.decode('utf-8') if raw else ''})
    system=('You are a software editor. Reply ONLY with a JSON object with exactly one key "edits", an array of objects '
        '{"path": string, "sha256": string or null, "content": full replacement content}. '
        'Use only the exact paths and sha256 supplied. Do not modify environment, credentials, billing, production, integrations, '
        'or unrelated files. Preserve behavior, provide minimal necessary changes. Do not include markdown fences. '
        'This output is a proposal and must not claim execution or deployment.')
    user='PROJECT CONTEXT:\n'+context(project)[:7500]+'\nGOAL:\n'+goal+'\nFILE SNAPSHOTS:\n'+json.dumps(chosen,ensure_ascii=False)
    response=provider_call(provider,system,user,model,120)
    try: parsed=json.loads(response)
    except json.JSONDecodeError as e:raise AiboError('API did not return valid JSON edit proposal') from e
    if not isinstance(parsed,dict) or not isinstance(parsed.get('edits'),list) or not parsed['edits']:
        raise AiboError('API did not return edits')
    keys={c['path']:c['sha256'] for c in chosen}
    for item in parsed['edits']:
        if item.get('path') not in keys or item.get('sha256')!=keys[item['path']] or not isinstance(item.get('content'),str):
            raise AiboError('Unapproved path, invalid content, or concurrency mismatch in proposal')
    dest=Path(output).expanduser().resolve()
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(parsed,indent=2,ensure_ascii=False),encoding='utf-8')
    return {'proposal':str(dest),'changedFiles':[x['path'] for x in parsed['edits']],'applied':False,'note':'Review proposal and run apply-patch; functional tests are still required'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--workspace',required=True);p.add_argument('--goal',required=True);p.add_argument('--provider',required=True,choices=['openai','anthropic']);p.add_argument('--files',required=True,help='Comma-separated explicit file paths');p.add_argument('--output',required=True);p.add_argument('--model');a=p.parse_args()
    try:
        print(json.dumps(propose(a.project,a.workspace,a.goal,a.provider,a.files.split(','),a.output,a.model),indent=2));return 0
    except (AiboError,OSError,ValueError) as e:
        print('AIBO ERROR: '+str(e),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
