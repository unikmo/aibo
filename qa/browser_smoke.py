"""Real frontend + isolated real AIBO backend smoke test.

Chromium is driven locally with Playwright. Because some CI environments block
Chromium from navigating to localhost, UI HTML/JS/CSS are loaded as local assets
and the browser fetch API is bridged to the actual local backend (not mocked).
No external model calls, publish, email, deploy, or financial actions are made.
"""
import argparse, base64, json, os, re, socket, subprocess, sys, tempfile, time
import urllib.error, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'Control-Centre'

def run(output, chromium=None):
    from playwright.sync_api import sync_playwright
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=True)
    checks=[]
    def check(name,func):
        try:
            evidence=func();checks.append({'name':name,'status':'PASS','evidence':str(evidence)[:260]});print('PASS',name,flush=True)
        except Exception as exc:
            checks.append({'name':name,'status':'FAIL','evidence':f'{type(exc).__name__}: {str(exc)[:250]}'})
            print('FAIL',name,checks[-1]['evidence'],flush=True)
    with tempfile.TemporaryDirectory(prefix='aibo-real-qa-') as storage:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        proc=subprocess.Popen([sys.executable,str(ROOT/'runtime'/'control_server.py'),'--port',str(port)],cwd=ROOT,
            env={**os.environ,'AIBO_STATE_DIR':storage},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        def backend(url,opts=None):
            opts=opts or {}
            if not isinstance(url,str) or not url.startswith('/'):return {'status':400,'body':{'error':'Invalid path'}}
            method=opts.get('method','GET').upper()
            data=base64.b64decode(opts['bodyBase64']) if 'bodyBase64' in opts else opts.get('bodyText','').encode() if opts.get('bodyText') is not None else None
            headers=opts.get('headers',{})
            request=urllib.request.Request(f'http://127.0.0.1:{port}'+url,method=method,data=data,headers=headers)
            try:r=urllib.request.urlopen(request,timeout=7)
            except urllib.error.HTTPError as e:r=e
            with r:
                blob=r.read(2000000)
                try:body=json.loads(blob)
                except Exception:body=blob.decode('utf-8',errors='replace')
                return {'status':r.status,'body':body,'headers':dict(r.headers)}
        try:
            for _ in range(50):
                if proc.poll() is not None:raise RuntimeError('AIBO server exited during startup')
                try:
                    if backend('/api/products/custom')['status']==200:break
                except Exception:time.sleep(.15)
            else:raise RuntimeError('AIBO backend startup timeout')
            check('HTTP backend and both editions',lambda:[(x,backend(x)['status']) for x in ('/standard/','/custom/','/api/readiness','/api/qa/capabilities')]
                if all(backend(x)['status']==200 for x in ('/standard/','/custom/','/api/readiness','/api/qa/capabilities')) else (_ for _ in ()).throw(AssertionError('HTTP failure')))
            # Setup only the first registered project in temporary isolated state.
            project=backend('/api/products/custom')['body']['projects'][0]['id']
            fields={'name':'QA Isolated Workspace','region':'Test','goal':'Browser QA without external actions or customer data',
                    'audience':'QA','successMeasure':'Task completes with attached evidence'}
            result=backend('/api/setup/custom/'+project,{'method':'POST','headers':{'Content-Type':'application/json'},
                'bodyText':json.dumps({'fields':fields,'step':2,'complete':True})})
            check('Isolated project setup',lambda:result['status']==200 or (_ for _ in ()).throw(AssertionError(result['body'])))
            with sync_playwright() as pw:
                exe=chromium or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None)
                browser=pw.chromium.launch(headless=True,executable_path=exe,args=['--no-sandbox','--disable-dev-shm-usage'])
                try:
                    for edition in ('standard','custom'):
                        page=browser.new_page(viewport={'width':1360,'height':850});page.set_default_timeout(4500)
                        js_errors=[];page.on('pageerror',lambda e:js_errors.append(str(e)[:180]))
                        html=(WEB/edition/'index.html').read_text(encoding='utf8')
                        html=re.sub(r'<script[^>]*></script>','',html)
                        html=re.sub(r'<link[^>]+stylesheet[^>]*>','',html)
                        page.set_content(html)
                        for sheet in ('styles.css','setup.css','usage.css','product.css'):
                            page.add_style_tag(path=str(WEB/'shared'/sheet))
                        page.expose_function('__aiboBackend',backend)
                        page.evaluate('''window.fetch = async (url, options={}) => {
                           const payload={method:options.method||'GET',headers:options.headers||{}};
                           if (options.body instanceof Blob) {
                               const bytes=new Uint8Array(await options.body.arrayBuffer());
                               let binary='';for(let i=0;i<bytes.length;i++)binary+=String.fromCharCode(bytes[i]);
                               payload.bodyBase64=btoa(binary);
                           } else if (options.body!==undefined) payload.bodyText=String(options.body);
                           const response=await window.__aiboBackend(String(url),payload);
                           return {ok:response.status>=200&&response.status<300,status:response.status,
                               json:async()=>response.body,text:async()=>typeof response.body==='string'?response.body:JSON.stringify(response.body)};
                        };''')
                        scripts=['app.js','product.js']
                        if edition=='custom':scripts+=['operations.js','infra_ui.js','secure-workflows.js']
                        for script in scripts:page.add_script_tag(path=str(WEB/'shared'/script))
                        page.evaluate("document.dispatchEvent(new Event('DOMContentLoaded'))")
                        page.wait_for_timeout(250)
                        check(edition+' loaded navigation',lambda p=page:p.locator('.nav-list [data-view]').count()>0 or (_ for _ in ()).throw(AssertionError('no main nav')))
                        def product_check(p=page,mode=edition):
                            p.wait_for_function("document.querySelector('#project-list')?.children.length > 0",timeout=5000)
                            assert p.locator('#project-list').is_visible()
                            status=backend('/api/products/'+mode)
                            assert status['status']==200,status
                            if mode=='standard':
                                assert len(status['body']['slots'])==5
                                assert status['body']['purchase']['activationRequired'] is False
                            else:
                                assert status['body']['projects']
                            return 'Project list rendered from actual '+mode+' backend without activation'
                        check(edition+' real project edition',product_check)
                        if edition=='custom':
                            page.locator('[data-view="soni"]').first.click();page.wait_for_timeout(200)
                            page.locator('#op-chat-project').select_option(project)
                            check('Soni single composer',lambda:('composer ready' if page.locator('.aibo-chat-composer input[type=file]').count()==1 and page.locator('.aibo-chat-composer button[type=submit]').count()==1 else (_ for _ in ()).throw(AssertionError('composer incomplete'))))
                            page.locator('.aibo-chat-options summary').click()
                            page.locator('#op-chat-provider').select_option('mock')
                            page.locator('#op-chat-files').set_input_files({'name':'qa-evidence.csv','mimeType':'text/csv','buffer':b'id,status\nA,HOLD\n'})
                            def chat_flow():
                                field=page.locator('#op-chat-task');field.fill('Inspect this attached research record, report its evidence status')
                                field.press('Shift+Enter');assert '\n' in field.input_value()
                                field.press('Enter');page.wait_for_timeout(2600)
                                text=page.locator('#op-chat-status').inner_text()
                                assert 'completed' in text.lower(),text
                                return 'Shift+Enter newline, Enter submit, file upload, real task completion: '+text
                            check('Soni chat with real attachment',chat_flow)
                            def persisted():
                                info=backend('/api/runs/custom/'+project)
                                assert info['status']==200
                                assert info['body']['runs'],info['body']
                                return str(info['body']['runs'][0]['status'])
                            check('Soni task history persisted',persisted)
                        page.screenshot(path=str(out/(edition+'-desktop.png')),full_page=True)
                        page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(200)
                        check(edition+' mobile width',lambda p=page: 'no overflow' if p.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 3') else (_ for _ in ()).throw(AssertionError('horizontal overflow')))
                        page.screenshot(path=str(out/(edition+'-mobile.png')),full_page=True)
                        check(edition+' JavaScript exceptions',lambda errs=js_errors: 'none' if not errs else (_ for _ in ()).throw(AssertionError(errs)))
                        page.close()
                finally:browser.close()
        finally:
            proc.terminate()
            try:proc.wait(timeout=4)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
    report={'type':'isolated-backend-real-browser-frontend','passed':sum(x['status']=='PASS' for x in checks),
        'failed':sum(x['status']=='FAIL' for x in checks),'checks':checks,
        'limitations':['Browser documents loaded from local source to bypass Chromium localhost policy, but all data/API calls used the actual isolated AIBO server.',
          'No live vendor accounts, external actions, commercial license activation, Windows installation, or real GSI production records were exercised.']}
    (out/'smoke.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    (out/'smoke.md').write_text('# AIBO real frontend + isolated backend smoke\n\n'+f"Passed: {report['passed']}; Failed: {report['failed']}\n\n"+
        '\n'.join('- '+x['status']+' — '+x['name']+': '+x['evidence'] for x in checks)+'\n',encoding='utf8')
    print(json.dumps({'passed':report['passed'],'failed':report['failed'],'checks':checks},indent=2))
    return 1 if report['failed'] else 0

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(ROOT/'qa'/'smoke-evidence'));parser.add_argument('--chromium');args=parser.parse_args()
    sys.exit(run(args.output,args.chromium))
