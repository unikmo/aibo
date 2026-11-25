"""Playwright PWA acceptance against the REAL loopback AIBO backend.

Tests installability, standalone launch metadata, service-worker isolation and
API network-only behavior. No account/DNS/production changes are performed.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
PORT=8786
BASE=f"http://127.0.0.1:{PORT}"
with tempfile.TemporaryDirectory(prefix="aibo-pwa-state-") as state:
    env=dict(os.environ,AIBO_STATE_DIR=state)
    proc=subprocess.Popen([sys.executable,str(ROOT/"runtime"/"control_server.py"),
        "--port",str(PORT),"--strict-port"],cwd=ROOT,env=env,
        stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            context=browser.new_context(service_workers="allow")
            page=context.new_page()
            for i in range(60):
                try:
                    response=page.goto(BASE+"/v3/",wait_until="domcontentloaded",timeout=2000)
                    if response.status==200: break
                except Exception:
                    if i==59: raise
                    time.sleep(.25)
            page.wait_for_function("navigator.serviceWorker.controller !== null",timeout=15000)
            manifest_url=page.locator('link[rel="manifest"]').get_attribute('href')
            assert manifest_url=="/v3/manifest.webmanifest",manifest_url
            response=context.request.get(BASE+manifest_url)
            assert response.status==200
            manifest=response.json()
            assert manifest["display"]=="standalone"
            assert manifest["scope"]=="/v3/"
            assert manifest["start_url"]=="/v3/"
            assert manifest["name"]=="AIBO Control Centre"
            assert manifest["icons"] and all(x["src"].startswith("/v3/") for x in manifest["icons"])
            icon=context.request.get(BASE+"/v3/icon.svg")
            assert icon.status==200 and "<svg" in icon.text()
            scopes=page.evaluate("""async () => (await navigator.serviceWorker.getRegistrations())
                .map(x=>new URL(x.scope).pathname)""")
            assert scopes==["/v3/"],scopes
            # API remains unmodified and never enters Cache Storage
            api=context.request.get(BASE+"/api/portfolio/custom")
            assert api.status==200
            cached=page.evaluate("""async () => {
              const keys=await caches.keys();
              const urls=[];
              for (const key of keys) {
                const cache=await caches.open(key);
                urls.push(...(await cache.keys()).map(req=>req.url));
              }
              return {keys,urls};
            }""")
            assert not cached["keys"] and not cached["urls"],cached
            page.reload(wait_until="domcontentloaded")
            page.wait_for_function("document.querySelector('#countProjects').textContent !== '—'")
            assert page.locator(".nav").count()==5
            context.close()
            browser.close()
        print("PWA Playwright acceptance passed: manifest, standalone, SVG, service worker, API, no private caching, 5 navigation areas")
    finally:
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill()
