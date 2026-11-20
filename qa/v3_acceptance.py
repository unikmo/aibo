"""End-to-end acceptance of functional AIBO Control Centre 3 against the real local runtime."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"qa"/"v3-acceptance"
OUT.mkdir(parents=True,exist_ok=True)
PORT=8778
BASE=f"http://127.0.0.1:{PORT}"
result={"screens":[],"functional":[],"errors":[]}
with tempfile.TemporaryDirectory() as state_dir:
    env=dict(os.environ,AIBO_STATE_DIR=state_dir)
    proc=subprocess.Popen([sys.executable,str(ROOT/"runtime"/"control_server.py"),"--port",str(PORT),"--strict-port"],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            for device,width,height in (("desktop",1440,930),("mobile",390,844)):
                page=browser.new_page(viewport={"width":width,"height":height},device_scale_factor=1)
                page.on("pageerror",lambda err:result["errors"].append(str(err)))
                for attempt in range(45):
                    try:
                        page.goto(BASE+"/v3/",wait_until="domcontentloaded",timeout=2500)
                        break
                    except Exception:
                        if attempt==44:raise
                        time.sleep(.3)
                page.wait_for_function("document.querySelector('#countProjects').textContent !== '—'")
                assert page.locator(".nav").count()==5
                for screen in ("home","soni","projects","activity","connections"):
                    page.locator(f'.nav[data-screen="{screen}"]').click()
                    page.locator("#screen-"+screen+".active").wait_for()
                    assert page.locator(".screen.active").count()==1
                    page.screenshot(path=str(OUT/f"{screen}-{device}.png"),full_page=True)
                    result["screens"].append(f"{screen}-{device}")
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),"Horizontal overflow on "+device
                assert page.locator("#projectCards .project-card").count()>=15
                if device=="desktop":
                    # Work with existing project, recording setup and Soni mock result in isolated state.
                    page.locator(".nav[data-screen='projects']").click()
                    page.locator(".project-card").first.click()
                    page.locator("#modalBody form input[name='region']").fill("Germany")
                    page.locator("#modalBody form textarea[name='goal']").fill("Validate local workflow")
                    page.locator("#modalBody form input[name='audience']").fill("Business users")
                    page.locator("#modalBody form input[name='successMeasure']").fill("Verified acceptance")
                    page.locator("#modalBody form button[type=submit]").click()
                    page.locator("#overlay.open").wait_for(state="hidden")
                    result["functional"].append("project setup persists")
                    page.locator(".nav[data-screen='soni']").click()
                    page.locator("#soniProvider").select_option("mock")
                    page.locator("#soniPrompt").fill("Review selected project positioning")
                    # Enter sends; Shift+Enter must add a line without submitting.
                    page.locator("#soniPrompt").press("Shift+Enter")
                    assert "\\n" in page.locator("#soniPrompt").input_value()
                    page.locator("#soniPrompt").fill("Review selected project positioning")
                    assert page.locator("#soniPrompt").evaluate("(e) => e.scrollHeight <= 190"), "Composer is not compact"
                    assert page.locator("#soniProvider").input_value()=="mock", "Provider selection reset before submit"
                    with page.expect_response(lambda resp: "/api/work/custom/" in resp.url and resp.request.method=="POST") as sent:
                        page.locator("#soniPrompt").press("Enter")
                    request_data=sent.value.request.post_data_json
                    assert request_data["provider"]=="mock", f"Provider changed during refresh: {request_data['provider']}"
                    result["functional"].append("explicit provider selection respected during concurrent refresh")
                    # Wait for a terminal status, including failures. Windows may expose
                    # an explicit modal error that an 'includes completed' wait hides.
                    try:
                        page.wait_for_function("""() => {
                            const hint=document.querySelector('#promptHint')?.textContent||'';
                            return /completed|failed|interrupted|not started/i.test(hint);
                        }""",timeout=20000)
                    except Exception as exc:
                        hint=page.locator("#promptHint").inner_text()
                        modal=page.locator("#modalBody").inner_text() if page.locator("#overlay.open").count() else ""
                        portfolio=page.request.get(BASE+"/api/portfolio/custom").json()
                        recent=portfolio.get("recentWork",[])[:3]
                        raise AssertionError(f"Soni UI did not reach a terminal state. Hint={hint!r}; modal={modal!r}; recentRuns={recent!r}; browserErrors={result['errors']!r}") from exc
                    hint=page.locator("#promptHint").inner_text()
                    if "completed" not in hint:
                        modal=page.locator("#modalBody").inner_text() if page.locator("#overlay.open").count() else ""
                        recent=page.request.get(BASE+"/api/portfolio/custom").json().get("recentWork",[])[:3]
                        raise AssertionError(f"Soni failed. Hint={hint!r}; modal={modal!r}; recentRuns={recent!r}")
                    page.locator(".log-item.agent").first.wait_for(state="visible",timeout=15000)
                    assert "MOCK" in page.locator(".log-item.agent").last.inner_text()
                    result["functional"].append("Soni mock execution persisted and rendered")
                    page.locator(".nav[data-screen='activity']").click()
                    page.wait_for_function("document.querySelectorAll('#activityRows .rowitem').length > 0",timeout=15000)
                    assert any(x["status"]=="completed" for x in page.request.get(BASE+"/api/portfolio/custom").json()["recentWork"])
                    result["functional"].append("activity records reflect real run")
                    page.locator("#settingsBtn").click()
                    page.locator("#modalBody button",has_text="Cost controls").click()
                    page.locator("#modalBody input[name='maxModelCalls']").fill("7")
                    page.locator("#modalBody form button[type=submit]").click()
                    page.locator("#overlay.open").wait_for(state="hidden")
                    assert page.request.get(BASE+"/api/cost-controls").json()["maxModelCalls"]==7
                    result["functional"].append("settings are saved")
                    page.locator(".nav[data-screen='connections']").click()
                    page.locator("#projectSelect").select_option(index=1)
                    page.locator("#connectionsGrid button").first.click()
                    page.locator("#overlay.open").wait_for()
                    assert "request" in page.locator("#modalTitle").inner_text().lower()
                    page.locator("#closeModal").click()
                    assert len(page.request.get(BASE+"/api/connections/catalog").json()["requests"])>=1
                    result["functional"].append("connection setup request recorded")
                    # Provider settings change using the real authenticated-local API surface.
                    page.locator("#settingsBtn").click()
                    page.locator("#modalBody button",has_text="AI providers").click()
                    page.locator("#modalBody select[name='switchMode']").select_option("soni")
                    page.locator("#modalBody form button[type=submit]").click()
                    page.locator("#overlay.open").wait_for(state="hidden")
                    assert page.request.get(BASE+"/api/ai-providers").json()["switchMode"]=="soni"
                    result["functional"].append("model routing settings persisted")
                    page.locator("#settingsBtn").click()
                    page.locator("#modalBody button",has_text="Select model").click()
                    page.locator("#modalBody select[name='provider']").select_option("openrouter")
                    page.wait_for_function("Array.from(document.querySelectorAll('#modalBody select[name=model] option')).some(o => o.value === 'openrouter/auto')",timeout=15000)
                    page.locator("#modalBody select[name='model']").select_option("openrouter/auto")
                    page.locator("#modalBody form button[type=submit]").click()
                    page.locator("#overlay.open").wait_for(state="hidden")
                    assert page.request.get(BASE+"/api/ai-providers").json()["models"]["openrouter"]=="openrouter/auto"
                    result["functional"].append("provider model selection persisted")

                    # Additive project creation must not overwrite existing workspaces.
                    page.locator(".nav[data-screen='projects']").click()
                    page.locator("#projectSearch + button").click()
                    page.locator("#modalBody input[name='name']").fill("V3 Acceptance Initiative")
                    page.locator("#modalBody input[name='industry']").fill("Internal test")
                    page.locator("#modalBody form button[type=submit]").click()
                    page.locator("#overlay.open").wait_for(state="hidden")
                    projects_response=page.request.get(BASE+"/api/products/custom").json()
                    assert len(projects_response["projects"])>=16
                    assert any(p["id"]=="v3-acceptance-initiative" for p in projects_response["projects"]), "New project missing from backend"
                    try:
                        page.wait_for_function("document.querySelector('#projectSelect').value === 'v3-acceptance-initiative'",timeout=15000)
                    except Exception as exc:
                        actual=page.locator("#projectSelect").input_value()
                        options=page.locator("#projectSelect option").evaluate_all("(options) => options.map(o => o.value)")
                        raise AssertionError(f"Created project exists in backend but selector did not synchronize: selected={actual!r}, options={options!r}; browserErrors={result['errors']!r}") from exc
                    result["functional"].append("new project safely created")
                    # New state-owned projects must work through Soni, not merely appear in a card.
                    new_id="v3-acceptance-initiative"
                    setup=page.request.post(BASE+"/api/setup/custom/"+new_id,data={
                        "fields":{"name":"V3 Acceptance Initiative","region":"Germany",
                                  "goal":"Verify new project execution","audience":"Test owner",
                                  "successMeasure":"Verified local run"},
                        "step":2,"complete":True
                    },headers={"Content-Type":"application/json"})
                    assert setup.ok,setup.text()
                    run=page.request.post(BASE+"/api/work/custom/"+new_id,data={
                        "task":"Check new project routing","provider":"mock","consent":False
                    },headers={"Content-Type":"application/json"})
                    assert run.ok,run.text()
                    detail=page.request.get(BASE+"/api/run/"+run.json()["id"])
                    assert detail.ok and detail.json()["status"]=="completed"
                    assert "MOCK" in detail.json()["result"]["soni"]
                    result["functional"].append("newly created project routes through Soni")


                assert not result["errors"], "Browser JS errors: "+repr(result["errors"])
                page.close()
            browser.close()
        (OUT/"acceptance.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
        print(json.dumps(result))
    finally:
        proc.terminate()
        try:proc.wait(timeout=7)
        except subprocess.TimeoutExpired:proc.kill()
