"""AIBO pre-release nonfunctional check: local security controls and performance.

This is a bounded localhost probe, NOT a penetration test or proof of zero vulnerabilities.
Never uses external credentials, paid APIs or production data.
"""
import concurrent.futures
import json
import os
from pathlib import Path
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
RESULT=ROOT/"qa"/"release-evidence"
RESULT.mkdir(parents=True,exist_ok=True)
FAIL=[]

def get(url, headers=None, method="GET", body=None):
    req=Request(url,headers=headers or {},method=method,data=body)
    start=time.monotonic()
    try:
        with urlopen(req,timeout=8) as r:
            return r.status,r.read(300000),dict(r.headers),(time.monotonic()-start)*1000
    except HTTPError as err:
        return err.code,err.read(300000),dict(err.headers),(time.monotonic()-start)*1000

def check(condition, description):
    if not condition:FAIL.append(description)

def main():
    with tempfile.TemporaryDirectory(prefix="aibo-release-gate-") as state:
        env=dict(os.environ,AIBO_STATE_DIR=state)
        proc=subprocess.Popen([sys.executable,str(ROOT/"runtime"/"control_server.py"),
            "--port","0","--strict-port"],cwd=ROOT,env=env,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,text=True)
        try:
            import select
            # Server prints its bound port immediately on start.
            # Poll using a bounded startup window, without a fixed-port collision.
            import threading,queue
            lines=queue.Queue()
            threading.Thread(target=lambda:lines.put(proc.stdout.readline()),daemon=True).start()
            try:line=lines.get(timeout=12)
            except queue.Empty:raise AssertionError("Server did not start")
            import re
            found=re.search(r"http://127\.0\.0\.1:(\d+)/v3/",line)
            check(bool(found),"Server did not publish loopback URL")
            if not found:return
            port=int(found.group(1))
            base="http://127.0.0.1:"+str(port)
            # Stage 2 smoke: main app, health and isolated local startup.
            for path in ("/v3/","/api/products/custom","/api/ai-providers"):
                status,body,hdr,ms=get(base+path)
                check(status==200,f"Smoke: {path} status {status}")
                check(hdr.get("X-Frame-Options")=="DENY",f"Security header missing: {path}")
                check(hdr.get("X-Content-Type-Options")=="nosniff",f"Content sniff guard missing: {path}")
            # Stage 6: hostile Host and cross-origin write must be refused.
            st,body,_,_=get(base+"/api/ai-providers",{"Host":"example.com"})
            check(st==403,"Untrusted Host not denied")
            st,body,_,_=get(base+"/api/projects/custom",
                {"Content-Type":"application/json","Origin":"https://attacker.example"},
                "POST",json.dumps({"name":"Must Not Create"}).encode())
            check(st==400 or st==403,"Cross-origin project write not denied")
            st,body,_,_=get(base+"/api/projects/custom",
                {"Content-Type":"text/plain"},"POST",b"test")
            check(st==400 or st==403,"Non-JSON project write not denied")
            st,body,_,_=get(base+"/api/ai-providers",
                {"Content-Type":"application/json"},"POST",b"{}")
            check(st==404 or st==405,"Unexpected API method accepted")
            st,body,_,_=get(base+"/api/../../../.env")
            check(st in (400,403,404),"Directory traversal probe unexpectedly succeeded")
            # Project isolation and API-consent are covered by unit/integration tests.
            # Performance is a small local concurrency smoke, not load capacity validation.
            def probe(_):
                status,body,_,ms=get(base+"/api/products/custom")
                return status,ms
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                samples=list(pool.map(probe,range(48)))
            times=sorted(ms for code,ms in samples)
            p95=times[min(len(times)-1,int(len(times)*0.95))]
            failures=sum(code!=200 for code,ms in samples)
            check(failures==0,"Concurrent reads had HTTP failures")
            check(p95<2500,f"Local HTTP p95 {p95:.0f}ms exceeds 2500ms")
            report={"stage2_smoke":"PASS" if not any("Smoke:" in x for x in FAIL) else "FAIL",
                "stage6_security_probes":"PASS" if not any("denied" in x or "guard" in x or "traversal" in x for x in FAIL) else "FAIL",
                "stage6_local_performance":{"requests":len(samples),"concurrency":8,
                    "p95_ms":round(p95,1),"http_failures":failures,
                    "status":"PASS" if failures==0 and p95<2500 else "FAIL"},
                "limitations":["No paid/provider API tested","No external penetration test",
                    "Local request smoke is not a capacity benchmark"],
                "failures":FAIL}
            (RESULT/"local-security-performance.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
            print(json.dumps(report,indent=2))
            if FAIL:raise AssertionError("; ".join(FAIL))
        finally:
            proc.terminate()
            try:proc.wait(timeout=4)
            except subprocess.TimeoutExpired:proc.kill()
if __name__=="__main__":main()
