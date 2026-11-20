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
                page.locator('.nav[data-screen="soni"]').click()
                colors=page.locator("#conversation").evaluate("""el => {
                    const css=getComputedStyle(el);
                    const agent=getComputedStyle(document.querySelector('#screen-soni .chat'));
                    return [css.backgroundColor,css.color,agent.backgroundColor];
                }""")
                assert colors==['rgb(250, 250, 250)','rgb(32, 33, 36)','rgb(255, 255, 255)'],colors
                assert page.locator("#soniPrompt").is_visible(),"Soni composer must remain visible without scrolling"
                page.locator('.nav[data-screen="projects"]').click()
                # Copy-density and hierarchy contract: no promotional filler or duplicate controls.
                visible_headings=[page.locator("#screen-"+screen+" h1").inner_text() for screen in ("home","soni","projects","activity","connections")]
                assert visible_headings[0]=="Overview" and visible_headings[2:] == ["Projects","Activity","Connections"],visible_headings
                assert page.locator(".aside-foot").count()==0,"Decorative sidebar footer returned"
                assert page.locator("#screen-home .page-heading p").count()==0
                assert page.locator("#screen-activity .page-heading p").count()==0
                assert page.locator("#screen-projects #projectSubheading").evaluate("(el)=>getComputedStyle(el).position==='absolute'"),"Project instructions should not occupy visual space"
                assert page.locator("#projectSelect").count()==1
                assert page.locator("#newProjectBtn").count()==1
                assert page.locator("#projectSearch").count()==0,"Duplicate project search returned"
                assert page.locator("#soniProjectSelect").count()==0,"Duplicate Soni project selector returned"
                page.locator('.nav[data-screen="projects"]').click()
                assert page.locator("#projects-title").inner_text()=="Projects"
                assert page.locator("#projectCards .project-card").count()>=15
                assert page.locator("#projectCards").evaluate("(x) => x.getBoundingClientRect().top < innerHeight-50"),"Project list pushed below fold"
                page.locator("#projectSelect").select_option(index=1)
                assert page.locator("#projectCards .project-summary").count()==1
                assert page.locator("#projectSearch").count()==0
                page.locator('.nav[data-screen="connections"]').click()
                assert page.locator("#connectionsCatalog").evaluate("(x)=>!x.open"),"Integration catalog should be collapsed"
                page.locator("#projectSelect").select_option("")

                assert page.locator("#projectCards .project-card").count()>=15
                if device=="desktop":
                    # Work with existing project, recording setup and Soni mock result in isolated state.
                    page.locator(".nav[data-screen='projects']").click()
                    page.locator("#projectSelect").select_option(index=1)
                    page.locator("#projectCards .project-summary button",has_text="Import sources").click()
                    assert page.locator("#modalBody input[name='sourceLink']").is_visible()
                    assert page.locator("#modalBody input[type=file]").is_visible()
                    assert page.locator("#modalBody details.source-extra").evaluate("(x) => !x.open")
                    assert page.locator("#modalBody input[name='repository']").is_hidden()
                    assert page.locator("#modalBody input[name='drive']").is_hidden()
                    assert page.locator("#modalBody input[name='website']").is_hidden()
                    assert page.locator("#modalBody input[name='sourceLink']").count()==1
                    page.locator("#modalBody form button",has_text="Continue").click()
                    page.wait_for_function("document.querySelector('#modalTitle')?.textContent?.includes('Review project profile')",timeout=15000)
                    page.locator("#modalBody details.source-extra summary").click()
                    page.locator("#modalBody form input[name='region']").fill("Germany")
                    page.locator("#modalBody form textarea[name='goal']").fill("Validate local workflow")
                    page.locator("#modalBody form input[name='audience']").fill("Business users")
                    page.locator("#modalBody form input[name='successMeasure']").fill("Verified acceptance")
                    page.locator("#modalBody form button[type=submit]").click()
                    page.locator("#overlay.open").wait_for(state="hidden")
                    result["functional"].append("project source scan reviewed and setup persists")
                    page.locator(".nav[data-screen='soni']").click()
                    page.locator("#soniProvider").select_option("mock")
                    page.locator("#soniPrompt").fill("Review selected project positioning")
                    # Enter sends; Shift+Enter must add a line without submitting.
                    page.locator("#soniPrompt").press("Shift+Enter")
                    assert chr(10) in page.locator("#soniPrompt").input_value()
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
                    # Regression: legacy Markdown, encoding errors and HTML must not appear as raw chat text.
                    run_id=sent.value.json()["id"]
                    run_file=Path(state_dir)/"runs"/(run_id+".json")
                    original=json.loads(run_file.read_text(encoding="utf-8"))
                    fixture="**Executive status**â€”<div>Registered project</div>\\n- Pending review"
                    original["result"]["soni"]=fixture
                    run_file.write_text(json.dumps(original,ensure_ascii=False),encoding="utf-8")
                    page.locator(".nav[data-screen='projects']").click()
                    page.locator(".nav[data-screen='soni']").click()
                    page.locator("#projectSelect").select_option(original["project"])
                    page.locator(".log-item.agent").last.wait_for(state="visible")
                    displayed=page.locator(".log-item.agent").last.locator(".message-body").inner_text()
                    assert "**" not in displayed and "â€”" not in displayed and "<div>" not in displayed,displayed
                    assert "Executive status—" in displayed,displayed
                    assert page.locator(".log-item.agent").last.locator(".detail-body").is_hidden()
                    assert page.locator("#conversation").evaluate("(x) => x.getBoundingClientRect().bottom <= document.querySelector('#soniPrompt').getBoundingClientRect().top + 1"),"Conversation should sit above composer"
                    result["functional"].append("Markdown, HTML and mojibake normalized in bottom-anchored Soni chat")

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
                    page.locator("#connectionsCatalog summary").click()
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
                    page.locator("#newProjectBtn").click()
                    page.locator("#modalBody input[name='name']").fill("V3 Acceptance Initiative")
                    page.locator("#modalBody form button[type=submit]").click()
                    page.wait_for_function("document.querySelector('#modalTitle')?.textContent?.startsWith('Set up ')",timeout=15000)
                    page.locator("#closeModal").click()
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
                    upload=page.request.post(BASE+"/api/attachments/custom/"+new_id,
                        data=b"Goal: Verify new project execution\nAudience: Test owner\n",
                        headers={"Content-Type":"application/octet-stream","X-AIBO-Filename":"project-brief.md"})
                    assert upload.ok,upload.text()
                    inspected=page.request.post(BASE+"/api/setup/custom/"+new_id+"/inspect",
                        data={"attachments":[upload.json()["id"]]},
                        headers={"Content-Type":"application/json"})
                    assert inspected.ok,inspected.text()
                    candidates=inspected.json()["suggestions"]
                    assert candidates["goal"]["value"]=="Verify new project execution",candidates
                    assert candidates["audience"]["value"]=="Test owner",candidates
                    setup=page.request.post(BASE+"/api/setup/custom/"+new_id,data={
                        "fields":{"name":"V3 Acceptance Initiative","goal":candidates["goal"]["value"],
                                  "audience":candidates["audience"]["value"]},
                        "step":2,"complete":True,"reviewSources":True
                    },headers={"Content-Type":"application/json"})
                    assert setup.ok,setup.text()
                    assert setup.json()["sourceEvidence"],"Owner-reviewed uploaded evidence not retained"
                    result["functional"].append("uploaded document ingested into project context before owner review")
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
