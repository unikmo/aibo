"""Smoke-test actual PyInstaller macOS .app, not only source Python."""
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/"dist"/"AIBO.app"
EXE=APP/"Contents"/"MacOS"/"AIBO"
RESOURCES=APP/"Contents"/"Frameworks"
assert EXE.is_file(), f"Missing executable: {EXE}"
for item in ("Control-Centre/v3/index.html","Control-Centre/v3/app.js",
             "System/project-registry.json","runtime/agents.json",
             "runtime/connectors.json","Industry-Packs/README.md"):
    assert any((base/item).is_file() for base in
               (APP/"Contents"/"Resources",RESOURCES,APP/"Contents"/"_internal")), f"Not bundled: {item}"
with tempfile.TemporaryDirectory(prefix="aibo-macos-smoke-") as state:
    env=dict(os.environ, AIBO_STATE_DIR=state)
    with tempfile.NamedTemporaryFile(mode="w+",encoding="utf8") as log:
        proc=subprocess.Popen([str(EXE),"--port","0"],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            root=None
            for _ in range(90):
                time.sleep(.4)
                log.seek(0)
                match=re.search(r"http://127\.0\.0\.1:(\d+)/v3/",log.read())
                if match:
                    root=f"http://127.0.0.1:{match.group(1)}"
                    break
                if proc.poll() is not None:raise RuntimeError("AIBO.app exited during startup")
            assert root, "AIBO.app did not announce a local port"
            for path in ("/v3/","/api/products/custom","/api/portfolio/custom"):
                with urllib.request.urlopen(root+path,timeout=12) as response:
                    assert response.status==200,path
            request=urllib.request.Request(root+"/api/projects/custom",
                data=json.dumps({"name":"macOS Smoke Project","industry":"Internal","region":"Test",
                                 "corePack":None,"addOns":[]}).encode(),
                headers={"Content-Type":"application/json"},method="POST")
            with urllib.request.urlopen(request,timeout=15) as response:
                assert json.load(response)["project"]=="macos-smoke-project"
            print("MacOS .app smoke passed: HTTP, APIs, persistent project creation")
        finally:
            proc.terminate()
            try:proc.wait(timeout=8)
            except subprocess.TimeoutExpired:proc.kill()
