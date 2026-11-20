"""Local-only Control Centre development server; no external exposure or bundled credentials."""
import json
import html
import ipaddress
import re
import errno
import sys
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit
try:
    from . import products, workspace, portfolio, costs, connector_catalog, connection_runtime, dependencies, editorial, oauth_local, action_gateway, attachments, agent_setup, ai_providers, relationship_work, browser_qa
except ImportError:
    import products
    import workspace
    import portfolio
    import costs
    import connector_catalog
    import connection_runtime
    import dependencies
    import editorial
    import oauth_local
    import action_gateway
    import attachments
    import agent_setup
    import ai_providers
    import relationship_work
    import browser_qa
try:
    from . import infra_actions
except ImportError:
    import infra_actions
ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))
WEB=ROOT/'Control-Centre'
DEFAULT_PORT=8765
DEFAULT_PORT_RETRIES=20
UNAVAILABLE_PORT_ERRORS=(errno.EADDRINUSE,errno.EACCES,10048,10013)

class Handler(SimpleHTTPRequestHandler):
    def _trusted_local_client(self):
        # Loopback binding alone is insufficient if a local browser is redirected
        # by a hostile DNS-rebinding page. All routes require a loopback Host.
        host=self.headers.get('Host','')
        if not re.fullmatch(r'(?:localhost|127\.0\.0\.1):[0-9]{1,5}',host):
            return False
        try:
            if not ipaddress.ip_address(self.client_address[0]).is_loopback:
                return False
            if int(host.rsplit(':',1)[1])!=self.server.server_port:
                return False
        except (ValueError,IndexError,TypeError):
            return False
        return True
    def _reject_untrusted_client(self):
        if self._trusted_local_client():return False
        self._json(403,{'error':'Local AIBO access only; use 127.0.0.1 or localhost on the configured port'})
        return True
    def end_headers(self):
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        # Updated local application assets must never be hidden behind stale browser cache.
        if self.path.split('?',1)[0].endswith(('.html','.js','.css','/standard/','/custom/')):
            self.send_header('Cache-Control','no-store, max-age=0')
        super().end_headers()
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(WEB),**kwargs)
    def _json(self,status,obj):
        blob=json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Length',str(len(blob)));self.end_headers();self.wfile.write(blob)
    def _read_body(self):
        origin=self.headers.get('Origin')
        if origin:
            from urllib.parse import urlsplit as split
            parsed=split(origin)
            host=self.headers.get('Host','')
            if parsed.scheme!='http' or parsed.netloc!=host or host.split(':')[0] not in ('127.0.0.1','localhost'):
                raise products.ProductError('Cross-origin request denied')
        if self.headers.get('Content-Type','').split(';')[0].strip().lower()!='application/json':
            raise products.ProductError('JSON content type required')
        try:length=int(self.headers.get('Content-Length','0'))
        except (TypeError,ValueError):raise products.ProductError('Invalid request size')
        if not 0<length<=8192:
            raise products.ProductError('Invalid request size')
        return json.loads(self.rfile.read(length))
    def _infra(self):
        return infra_actions.Engine(products.STATE/'infrastructure-actions.json')
    def _infra_write_guard(self):
        # Browser-origin protection + DNS rebinding guard for the sensitive write API.
        host=self.headers.get('Host','').lower()
        if not (host.startswith('127.0.0.1:') or host.startswith('localhost:')):
            raise infra_actions.InfraError('Infrastructure API requires a loopback Host')
        if not host.rsplit(':',1)[1].isdigit():
            raise infra_actions.InfraError('Invalid Host port')
        if self.headers.get('Origin','').lower()!='http://'+host:
            raise infra_actions.InfraError('Explicit same-origin browser request required')
        if self.headers.get('X-AIBO-Intent')!='infrastructure':
            raise infra_actions.InfraError('Missing infrastructure intent header')
        if self.headers.get('Sec-Fetch-Site','same-origin') not in ('same-origin','none'):
            raise infra_actions.InfraError('Cross-site infrastructure request denied')
    def _infra_get_guard(self):
        host=self.headers.get('Host','').lower()
        if not (host.startswith('127.0.0.1:') or host.startswith('localhost:')) or not host.rsplit(':',1)[-1].isdigit():
            raise infra_actions.InfraError('Invalid infrastructure API Host')
    def do_GET(self):
        if self._reject_untrusted_client():return
        path=urlsplit(self.path).path
        if path=='/api/infrastructure/capabilities' or path.startswith('/api/infrastructure/status/'):
            try:self._infra_get_guard()
            except infra_actions.InfraError as e:
                self._json(403,{'error':str(e)});return
        if path=='/api/infrastructure/capabilities':
            self._json(200,{'operations':{key:sorted(value) for key,value in infra_actions.ALLOWED.items()},'approvalRequired':True,'liveCredentialsVerified':False})
            return
        if path.startswith('/api/infrastructure/status/'):
            item=self._infra().status(path.rsplit('/',1)[-1])
            self._json(200 if item else 404,item if item else {'error':'Not found'})
            return
        if path=='/':self.send_response(302);self.send_header('Location','/v3/');self.end_headers();return
        if path=='/api/oauth/buffer/callback':
            from urllib.parse import parse_qs
            qs=parse_qs(urlsplit(self.path).query)
            try:
                if self.headers.get('Host','').split(':')[0] not in ('127.0.0.1','localhost'):
                    raise products.ProductError('Invalid callback host')
                result=oauth_local.callback(qs)
                # OAuth continuation is read-only; do not automatically initiate business writes.
                resumed=dependencies.resume_verified(result['project'],'buffer')
                self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Cache-Control','no-store');self.end_headers()
                self.wfile.write(b'<h2>Buffer connected to this local session.</h2><p>Return to AIBO Control Centre.</p>')
            except products.ProductError as e:self._json(400,{'error':str(e)})
            return
        if path.startswith('/api/relationship/custom/'):
            try:self._json(200,relationship_work.overview(path.split('/')[-1]))
            except products.ProductError as e:self._json(404,{'error':str(e)})
            return
        if path=='/api/ai-providers/models':
            from urllib.parse import parse_qs
            provider=parse_qs(urlsplit(self.path).query).get('provider',[''])[0]
            try:self._json(200,ai_providers.available_models(provider))
            except products.ProductError as e:self._json(400,{'error':str(e)})
            return
        if path=='/api/ai-providers':self._json(200,ai_providers.public());return
        if path=='/api/qa/capabilities':self._json(200,browser_qa.capabilities());return
        if path=='/api/readiness':
            from shutil import which
            ai=ai_providers.public()
            providers={name:{'configured':bool(ready),'authenticated':False,'liveTested':False} for name,ready in ai['ready'].items()}
            self._json(200,{'status':'local-runtime-only',
                'providers':providers,'standardLicense':products.standard_state()['license']['status'],
                'costs':{'enforced':['maxOutputTokens','maxModelCalls'], 'usdHardCap':False},
                'externalConnectors':'not-verified',
                'notice':'A configured API key or local CLI is not proof of live authentication or authorized execution.'})
            return
        if path.startswith('/api/attachments/custom/') and path.endswith('/inspection'):
            parts=path.strip('/').split('/')
            if len(parts)!=6:
                self._json(404,{'error':'Invalid attachment inspection path'});return
            try:
                info=attachments.inspect(parts[3],parts[4]);self._json(200,info)
            except (ValueError,TypeError) as exc:self._json(400,{'error':str(exc)})
            return
        if path.startswith('/api/agent-setup/custom/'):
            try:self._json(200,agent_setup.get(path.split('/')[-1]))
            except products.ProductError as e:self._json(404,{'error':str(e)})
            return
        if path=='/api/actions':self._json(200,{'actions':action_gateway.records()});return
        if path.startswith('/api/oauth/buffer/status/'):
            self._json(200,oauth_local.status(path.split('/')[-1]));return
        if path=='/api/connections/capabilities':self._json(200,{'verificationAdapters':connection_runtime.public_capabilities()});return
        if path=='/api/dependencies':self._json(200,{'tasks':dependencies.records()});return
        if path=='/api/connections/catalog':self._json(200,connector_catalog.catalog());return
        if path=='/api/cost-controls':self._json(200,{**costs.current(),'budgetEnforcement':'not-available','usageMetering':'not-connected'});return
        if path=='/api/portfolio/custom':self._json(200,portfolio.overview());return
        if path.startswith('/api/setup/custom/'):
            try:self._json(200,workspace.setup_state(path.split('/')[-1]))
            except products.ProductError as ex:self._json(404,{'error':str(ex)})
            return
        if path.startswith('/api/runs/custom/'):
            try:self._json(200,{'runs':workspace.recent_runs(path.split('/')[-1])})
            except products.ProductError as ex:self._json(404,{'error':str(ex)})
            return
        if path.startswith('/api/run/'):
            try:self._json(200,workspace.run_status(path.split('/')[-1]))
            except products.ProductError as ex:self._json(404,{'error':str(ex)})
            return
        if path=='/api/catalog/custom':self._json(200,products.pack_catalog());return
        if path.startswith('/api/products/'):
            mode=path.split('/')[-1]
            try:self._json(200,products.state_for(mode))
            except products.ProductError as ex:self._json(404,{'error':str(ex)})
            return
        if path.startswith('/api/'):self._json(404,{'error':'API not implemented in local server'});return
        return super().do_GET()
    def do_PATCH(self):
        if self._reject_untrusted_client():return
        path=urlsplit(self.path).path
        if path=='/api/cost-controls':
            try:self._json(200,costs.update(self._read_body()))
            except (ValueError,TypeError) as ex:self._json(400,{'error':str(ex)})
            return
        self._json(404,{'error':'Not found'})
    def do_PUT(self):
        if self._reject_untrusted_client():return
        path=urlsplit(self.path).path
        if path=='/api/ai-providers':
            try:self._json(200,ai_providers.update(self._read_body()))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path.startswith('/api/agent-setup/custom/'):
            try:self._json(200,agent_setup.update(path.split('/')[-1],self._read_body()))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        self._json(404,{'error':'Not found'})
    def do_POST(self):
        if self._reject_untrusted_client():return
        path=urlsplit(self.path).path
        if path in ('/api/infrastructure/prepare','/api/infrastructure/approve','/api/infrastructure/execute'):
            try:
                self._infra_write_guard()
                data=self._read_body()
                engine=self._infra()
                if path.endswith('/prepare'):
                    project=data.get('project')
                    if project not in {x['id'] for x in products.custom_projects()}:
                        raise infra_actions.InfraError('Unknown project')
                    result=engine.prepare(project,data.get('provider'),data.get('operation'),data.get('args'))
                    status=201
                elif path.endswith('/approve'):
                    result=engine.approve(data.get('id'),data.get('approvalPhrase'));status=200
                else:
                    if data.get('confirm') is not True:raise infra_actions.InfraError('Explicit confirmation required')
                    result=engine.execute(data.get('id'));status=200
                self._json(status,result)
            except (ValueError,TypeError) as exc:self._json(400,{'error':str(exc)[:160]})
            return
        if path=='/api/browser/inspect':
            try:
                body=self._read_body()
                self._json(200,browser_qa.inspect(body.get('project'),body.get('url'),body.get('action','inspect')))
            except (ValueError,TypeError) as exc:self._json(400,{'error':str(exc)})
            return
        if path.startswith('/api/relationship/custom/'):
            parts=path.strip('/').split('/')
            if len(parts)!=5:self._json(404,{'error':'Unknown relationship operation'});return
            project,operation=parts[3],parts[4]
            try:
                body=self._read_body()
                fn={'contact':relationship_work.save_contact,'message':relationship_work.prepare_message,
                    'manual-update':relationship_work.log_manual_contact,'tpt-listing':relationship_work.save_tpt_listing}.get(operation)
                if fn is None:self._json(404,{'error':'Unknown relationship operation'});return
                self._json(201,fn(project,body))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path=='/api/ai-providers/test':
            try:
                data=self._read_body()
                self._json(200,ai_providers.test_connection(data.get('provider'),data.get('consent')))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path=='/api/ai-providers/key':
            try:
                data=self._read_body()
                self._json(200,ai_providers.save_key(data.get('provider'),data.get('key')))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path=='/api/ai-providers/key/remove':
            try:
                data=self._read_body()
                self._json(200,ai_providers.delete_key(data.get('provider')))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path.startswith('/api/attachments/custom/'):
            try:
                # Raw local upload, not multipart; no third-party transfer.
                host=self.headers.get('Host','').split(':')[0]
                if host not in ('127.0.0.1','localhost'):raise products.ProductError('Local access only')
                origin=self.headers.get('Origin')
                if origin and origin not in ('http://'+self.headers.get('Host',''),):
                    raise products.ProductError('Cross-origin request denied')
                if self.headers.get('Content-Type','').split(';')[0].strip().lower()!='application/octet-stream':
                    raise products.ProductError('Binary upload required')
                try:length=int(self.headers.get('Content-Length','0'))
                except (TypeError,ValueError):raise products.ProductError('Invalid attachment size')
                if not 0<length<=attachments.MAX_BYTES:raise products.ProductError('Invalid attachment size')
                filename=self.headers.get('X-AIBO-Filename','')
                from urllib.parse import unquote
                self._json(201,attachments.save(path.split('/')[-1],unquote(filename),self.rfile.read(length)))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path=='/api/editorial/start':
            try:self._json(202,editorial.start_editorial(self._read_body()))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path=='/api/editorial/review':
            try:self._json(200,editorial.review(self._read_body()))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path=='/api/oauth/buffer/start':
            try:
                data=self._read_body()
                result=oauth_local.begin(data.get('project'), self.server.server_port)
                self._json(200,result)
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path=='/api/actions/prepare':
            try:
                data=self._read_body()
                required={'buffer-post':'publish','resend-email':'send_mail','vercel-deploy-hook':'deploy','browser-interact':'write_browser'}.get(data.get('kind'))
                if required:agent_setup.assert_permission(data.get('project'),required)
                self._json(201,action_gateway.prepare(data.get('project'),data.get('kind'),data.get('details')))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path.startswith('/api/actions/approve/'):
            try:self._json(200,action_gateway.approve_action(path.split('/')[-1],self._read_body().get('phrase')))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path.startswith('/api/actions/execute/'):
            try:
                data=self._read_body()
                if data.get('confirm') is not True:raise products.ProductError('Owner confirmation required')
                record=next((x for x in action_gateway.records() if x['id']==path.split('/')[-1]),None)
                if record:
                    required={'buffer-post':'publish','resend-email':'send_mail','vercel-deploy-hook':'deploy','browser-interact':'write_browser'}.get(record['kind'])
                    if required:agent_setup.assert_permission(record['project'],required)
                self._json(200,action_gateway.execute(path.split('/')[-1]))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path=='/api/dependencies':
            try:self._json(201,dependencies.queue(self._read_body()))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path.startswith('/api/dependencies/resume/'):
            try:self._json(202,dependencies.resume(path.split('/')[-1]))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path=='/api/localization/translate':
            try:
                body=self._read_body()
                self._json(200,connection_runtime.translate(body.get('project'),body.get('text'),body.get('source'),body.get('target'),body.get('consent') is True))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path=='/api/connections/verify':
            try:
                body=self._read_body()
                result=connection_runtime.verify(body.get('project'),body.get('connector'))
                if result.get('verified'):result['resumedAnalysisTasks']=dependencies.resume_verified(body.get('project'),body.get('connector'))
                self._json(200,result)
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path=='/api/connections/request':
            try:self._json(201,connector_catalog.request_connection(self._read_body()))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path.startswith('/api/kpis/custom/'):
            try:self._json(201,portfolio.save_kpi(path.split('/')[-1],self._read_body()))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path=='/api/portfolio/custom':self._json(200,portfolio.overview());return
        if path.startswith('/api/setup/custom/'):
            try:self._json(200,workspace.save_setup(path.split('/')[-1],self._read_body()))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path.startswith('/api/work/custom/'):
            try:self._json(202,workspace.start_run(path.split('/')[-1],self._read_body()))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if path=='/api/projects/custom':
            try:
                data=self._read_body()
                self._json(201,products.create_custom_project(data))
            except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
            return
        if not path.startswith('/api/projects/'):self._json(404,{'error':'Not found'});return
        parts=path.strip('/').split('/')
        if len(parts)!=4:self._json(404,{'error':'Invalid path'});return
        _,_,mode,identifier=parts
        try:
            data=self._read_body()
            result=products.update_project(mode,identifier,data)
            self._json(200,result)
        except (ValueError,TypeError) as e:self._json(400,{'error':str(e)})
    def log_message(self,fmt,*args):pass

class LocalServer(ThreadingHTTPServer):
    # Larger backlog avoids delaying concurrent browser startup requests.
    request_queue_size = 64
    daemon_threads = True
    block_on_close = False
    def get_request(self):
        sock, address = super().get_request()
        sock.settimeout(12)
        return sock, address

def create_local_server(port=DEFAULT_PORT,port_retries=DEFAULT_PORT_RETRIES):
    """Bind a loopback-only server, choosing the next local port if needed."""
    if not isinstance(port,int) or not 0<=port<=65535:
        raise ValueError('Port must be between 0 and 65535')
    if not isinstance(port_retries,int) or port_retries<0:
        raise ValueError('Port retries must be zero or greater')
    candidates=(0,) if port==0 else range(port,min(65536,port+port_retries+1))
    last_error=None
    for candidate in candidates:
        try:
            return LocalServer(('127.0.0.1',candidate),Handler)
        except OSError as error:
            # Windows may report an occupied or excluded port as either
            # WSAEADDRINUSE (10048) or WSAEACCES (10013).
            if error.errno not in UNAVAILABLE_PORT_ERRORS:
                raise
            last_error=error
    upper=min(65535,port+port_retries)
    raise OSError(f'No local AIBO port is available between {port} and {upper}') from last_error

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=DEFAULT_PORT)
    parser.add_argument('--port-retries',type=int,default=DEFAULT_PORT_RETRIES,help='Number of consecutive local ports to try when the requested port is busy')
    parser.add_argument('--strict-port',action='store_true',help='Fail instead of choosing a fallback local port')
    parser.add_argument('--open-browser',action='store_true',help='Open the AIBO Control Centre 3 after the local server starts')
    args=parser.parse_args()
    try:
        srv=create_local_server(args.port,0 if args.strict_port else args.port_retries)
    except (OSError,ValueError) as error:
        parser.error(str(error))
    url=f'http://127.0.0.1:{srv.server_port}/v3/'
    print(f'AIBO local Control Centre: {url} or /custom/',flush=True)
    if args.open_browser:
        import webbrowser
        webbrowser.open_new_tab(url)
    srv.serve_forever()
if __name__=='__main__':main()
