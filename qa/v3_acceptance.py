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
                        page.goto(BASE+"/v3/?edition=custom",wait_until="domcontentloaded",timeout=2500)
                        break
                    except Exception:
                        if attempt==44:raise
                        time.sleep(.3)
                page.wait_for_function("document.querySelector('#countProjects').textContent !== '—'")
                assert page.locator('.nav[data-screen="soni"]').inner_text().strip()=="Talk to CariFive"
                assert "CariFive" in page.locator("#soni-title").inner_text()
                assert page.locator("#soniPrompt").get_attribute("aria-label")=="Message CariFive"
                assert page.locator("#reviewPrompt").get_attribute("aria-label")=="Send to CariFive"
                assert page.get_by_text("Just ask Soni.",exact=True).count()==0
                assert page.locator(".nav").count()==6
                for screen in ("home","soni","projects","activity","connections","growth"):
                    page.locator(f'.nav[data-screen="{screen}"]').click()
                    page.locator("#screen-"+screen+".active").wait_for()
                    assert page.locator(".screen.active").count()==1
                    page.screenshot(path=str(OUT/f"{screen}-{device}.png"),full_page=True)
                    result["screens"].append(f"{screen}-{device}")
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),"Horizontal overflow on "+device
                page.locator('.nav[data-screen="soni"]').click()
                # An unused Soni workspace must not display an empty dark history
                # occupying most of the screen. Only the composer stays dark.
                assert page.locator("#conversation").evaluate("(el)=>el.children.length===0")
                empty_chat=page.locator("#screen-soni .chat").evaluate("""el => {
                    const r=el.getBoundingClientRect();
                    const wrap=el.parentElement.getBoundingClientRect();
                    const composer=document.querySelector('#soniPrompt').getBoundingClientRect();
                    const heading=document.querySelector('#soni-title').getBoundingClientRect();
                    return {height:r.height,top:r.top,wrapHeight:wrap.height,
                            composerBottom:composer.bottom,composerTop:composer.top,
                            headingTop:heading.top,viewport:innerHeight,
                            background:getComputedStyle(el).backgroundColor};
                }""")
                assert empty_chat["height"]<230,empty_chat
                assert page.locator("#screen-soni.is-empty").count()==1
                assert empty_chat["headingTop"]>empty_chat["viewport"]*0.24,empty_chat
                assert empty_chat["composerTop"]<empty_chat["viewport"]*0.74,empty_chat
                assert empty_chat["composerBottom"]<empty_chat["viewport"]*0.83,empty_chat
                assert empty_chat["background"]=="rgba(0, 0, 0, 0)",empty_chat
                result["functional"].append("Fresh chat centers title and compact composer; no empty full-screen panel")
                colors=page.locator("#conversation").evaluate("""el => {
                    const css=getComputedStyle(el);
                    const agent=getComputedStyle(document.querySelector('#screen-soni .chat'));
                    return [css.backgroundColor,css.color,agent.backgroundColor];
                }""")
                # Empty chat intentionally has no dark history container.
                assert colors==['rgb(255, 255, 255)','rgb(38, 51, 78)','rgba(0, 0, 0, 0)'],colors
                assert page.locator("#soniPrompt").is_visible(),"Soni composer must remain visible"
                assert len(page.locator("#soniProvider option[value=auto]").inner_text())<=27,"Auto provider label should be compact on mobile"
                def check_composer():
                    result=page.evaluate("""() => {
                      const composer=document.querySelector('#soniPrompt').getBoundingClientRect();
                      const history=document.querySelector('#conversation').getBoundingClientRect();
                      const outer=document.querySelector('#screen-soni').getBoundingClientRect();
                      return {composerTop:composer.top,composerBottom:composer.bottom,
                        historyTop:history.top,historyBottom:history.bottom,
                        viewHeight:window.innerHeight, outerBottom:outer.bottom,
                        scrollHeight:document.querySelector('#conversation').scrollHeight,
                        clientHeight:document.querySelector('#conversation').clientHeight};
                    }""")
                    assert result["composerTop"]>=result["historyBottom"]-2,result
                    assert result["composerBottom"]<result["viewHeight"]-12,result
                    assert result["outerBottom"]<=result["viewHeight"]+5,result
                    return result
                check_composer()
                # A project with extensive historical chat must scroll messages, not the whole page.
                page.locator("#conversation").evaluate("""el => {
                  for(let i=0;i<45;i++){
                    const msg=document.createElement('div');
                    msg.className='log-item agent';
                    msg.textContent='Previous conversation ' + i + ' — status and verified project records.';
                    el.append(msg);
                  }
                }""")
                page.wait_for_function("!document.querySelector('#screen-soni').classList.contains('is-empty')")
                sizes=check_composer()
                assert sizes["scrollHeight"]>sizes["clientHeight"]+80,"Old messages must scroll independently"
                page.locator("#conversation").evaluate("(el)=>{el.scrollTop=el.scrollHeight}")
                check_composer()
                page.locator("#conversation").evaluate("(el)=>el.replaceChildren()")
                page.locator('.nav[data-screen="projects"]').click()
                # Copy-density and hierarchy contract: no promotional filler or duplicate controls.
                visible_headings=[page.locator("#screen-"+screen+" h1").inner_text() for screen in ("home","soni","projects","activity","connections")]
                assert visible_headings[0]=="Your business, in focus." and visible_headings[2:] == ["Projects","Activity","Connections"],visible_headings
                assert page.locator(".aside-foot .footline").count()==1,"Compact connection-status footer missing"
                assert page.locator("#screen-home .page-heading .heading-copy").count()==1
                assert page.locator("#homeTalkForm").count()==1
                assert page.locator(".nav[data-screen='growth']").count()==1
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
                    page.locator("#modalBody input[name='sourceLink']").wait_for(state="visible",timeout=15000)
                    assert page.locator("#modalBody input[type=file]").is_visible()
                    assert page.locator("#modalBody details.source-extra").evaluate("(x) => !x.open")
                    assert page.locator("#modalBody input[name='repository']").is_hidden()
                    assert page.locator("#modalBody input[name='drive']").is_hidden()
                    assert page.locator("#modalBody input[name='website']").is_hidden()
                    assert page.locator("#modalBody input[name='sourceLink']").count()==1
                    assert page.locator("#modalBody input[name='sourceLink']").get_attribute("type")=="text"
                    # A pasted domain without a scheme must be normalized to HTTPS.
                    # Inaccessible links must produce a visible, actionable failure.
                    page.locator("#modalBody input[name='sourceLink']").fill("unresolvable-onboarding-test.invalid")
                    with page.expect_request(lambda request: "/api/setup/custom/" in request.url and request.url.endswith("/inspect") and request.method=="POST") as attempted:
                        page.locator("#modalBody form button",has_text="Check sources").click()
                    submitted=attempted.value.post_data_json
                    assert submitted["website"]=="https://unresolvable-onboarding-test.invalid/"
                    page.wait_for_function("document.querySelector('#modalTitle')?.textContent?.includes('Review project profile')",timeout=15000)
                    assert "unresolvable-onboarding-test.invalid" in page.locator(".source-warning").inner_text()
                    page.locator("#closeModal").click()
                    page.locator("#projectCards .project-summary button",has_text="Import sources").click()
                    page.locator("#modalBody input[name='sourceLink']").wait_for(state="visible")

                    page.locator("#modalBody input[type=file]").set_input_files({
                        "name":"onboarding-brief.md",
                        "mimeType":"text/markdown",
                        "buffer":b"Goal: Verify a real imported project brief\nAudience: Business decision makers\n"
                    })
                    assert page.locator("#modalBody button",has_text="Cancel").count()==0
                    assert page.locator("#closeModal").count()==1
                    assert "save the project" in page.locator(".source-guidance").inner_text()
                    page.locator("#modalBody form button",has_text="Check sources").click()
                    page.wait_for_function("document.querySelector('#modalTitle')?.textContent?.includes('Review project profile')",timeout=15000)
                    assert "Read 1 source" in page.locator(".source-review").inner_text()
                    assert page.locator(".source-review details.source-extra").evaluate("(element) => element.open") is True
                    assert "onboarding-brief.md" in page.locator(".source-review").inner_text()
                    assert "Verify a real imported project brief" in page.locator(".source-list-item").inner_text()
                    # Previously owner-reviewed values take precedence over imported suggestions.
                    assert page.locator("#modalBody form textarea[name='goal']").input_value().strip()
                    assert "Verify a real imported project brief" in page.locator(".source-list-item").inner_text()
                    assert page.locator("#modalBody form input[name='audience']").input_value().strip()
                    assert "Audience: Business decision makers" in page.locator(".source-list-item").inner_text()
                    page.locator("#modalBody details.source-extra summary",has_text="Optional project details").click()
                    page.locator("#modalBody form input[name='region']").fill("Germany")
                    page.locator("#modalBody form textarea[name='goal']").fill("Validate local workflow")
                    page.locator("#modalBody form input[name='audience']").fill("Business users")
                    page.locator("#modalBody form input[name='successMeasure']").fill("Verified acceptance")
                    page.locator("#modalBody form button[type=submit]").click()
                    page.wait_for_function("document.querySelector('#modalTitle')?.textContent==='Project ready'",timeout=15000)
                    assert "You can now ask CariFive" in page.locator("#modalBody").inner_text()
                    page.locator("#closeModal").click()
                    page.locator("#overlay.open").wait_for(state="hidden")
                    result["functional"].append("single close action, source review, explicit setup success, and persistence")
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
                    if "completed" not in hint.lower():
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
                    # Isolation: naming a different registered project while another is
                    # selected must be rejected before any provider call or run is queued.
                    mismatch=page.request.post(BASE+"/api/work/custom/"+new_id,data={
                        "task":"Review Politangle's development status using its sources",
                        "provider":"auto","consent":False
                    },headers={"Content-Type":"application/json"})
                    assert mismatch.status==400,mismatch.text()
                    assert "Project mismatch" in mismatch.text(),mismatch.text()
                    previous=page.request.get(BASE+"/api/runs/custom/"+new_id).json()
                    assert not previous.get("runs"),"Cross-project request unexpectedly created a run"
                    result["functional"].append("cross-project request denied before AI execution")
                    comparison=page.request.post(BASE+"/api/work/custom/"+new_id,data={
                        "task":"Compare V3 Acceptance Initiative versus Politangle using approved profiles only",
                        "provider":"mock","consent":False
                    },headers={"Content-Type":"application/json"})
                    assert comparison.ok,comparison.text()
                    comp=page.request.get(BASE+"/api/run/"+comparison.json()["id"]).json()
                    assert comp["status"]=="completed",comp
                    assert comp["crossProjectReadOnly"] is True,comp
                    assert comp["result"]["externalActionsExecuted"] is False,comp
                    assert comp["comparisonEvidence"]=="owner-reviewed-profile-fields-only",comp
                    assert "Politangle" in comp["result"]["soni"] or comp["comparedProjects"],comp
                    result["functional"].append("explicit cross-project comparison uses read-only owner-reviewed summaries")

                    run=page.request.post(BASE+"/api/work/custom/"+new_id,data={
                        "task":"Check new project routing","provider":"mock","consent":False
                    },headers={"Content-Type":"application/json"})
                    assert run.ok,run.text()
                    detail=page.request.get(BASE+"/api/run/"+run.json()["id"])
                    assert detail.ok and detail.json()["status"]=="completed"
                    assert "MOCK" in detail.json()["result"]["soni"]
                    result["functional"].append("newly created project routes through Soni")

                    # One-time purchase: five Standard slots initialize and run without
                    # license activation, and retain local state after a page reload.
                    page.goto(BASE+"/v3/?edition=standard",wait_until="domcontentloaded")
                    page.wait_for_function("document.querySelector('#countProjects')?.textContent === '5'",timeout=15000)
                    standard_data=page.request.get(BASE+"/api/products/standard").json()
                    assert standard_data["purchase"]["activationRequired"] is False
                    assert standard_data["purchase"]["upgrades"]["annualUsd"]==48
                    assert standard_data["purchase"]["mandatoryRenewal"] is False
                    assert page.locator("#newProjectBtn").is_hidden()
                    page.locator("#projectSelect").select_option("standard-slot-1")
                    page.locator(".nav[data-screen='projects']").click()
                    page.locator("#projectCards .project-summary button",has_text="Import sources").click()
                    page.locator("#modalBody input[name='sourceLink']").wait_for(state="visible")
                    page.locator("#modalBody button",has_text="Check sources").click()
                    page.wait_for_function("document.querySelector('#modalTitle')?.textContent?.includes('Review project profile')",timeout=15000)
                    page.locator("#modalBody form textarea[name='goal']").fill("Improve qualified local enquiries")
                    page.locator("#modalBody form button[type=submit]").click()
                    page.wait_for_function("document.querySelector('#modalTitle')?.textContent==='Project ready'",timeout=15000)
                    page.locator("#closeModal").click()
                    current=page.request.get(BASE+"/api/setup/custom/standard-slot-1").json()
                    assert current["complete"] is True and current["fields"]["goal"]=="Improve qualified local enquiries"
                    run=page.request.post(BASE+"/api/work/custom/standard-slot-1",
                        data={"task":"Review Standard project positioning","provider":"mock","consent":False},
                        headers={"Content-Type":"application/json"})
                    assert run.ok,run.text()
                    details=page.request.get(BASE+"/api/run/"+run.json()["id"]).json()
                    assert details["status"]=="completed" and "MOCK" in details["result"]["soni"]
                    page.reload(wait_until="domcontentloaded")
                    page.wait_for_function("document.querySelector('#countProjects')?.textContent === '5'",timeout=15000)
                    assert page.request.get(BASE+"/api/products/standard").json()["slots"][0]["setupComplete"] is True
                    result["functional"].append("perpetual Standard five-slot setup, local AI run and reload without key")

                    # Real Growth OS customer journey: entry point, project isolation
                    # and persisted personality settings, without sending any content.
                    page.locator("#projectSelect").select_option("standard-slot-1")
                    page.locator(".nav[data-screen='projects']").click()
                    page.locator("#projectCards .project-summary button",has_text="Growth OS").click()
                    page.locator("#modalTitle").wait_for(state="visible")
                    assert page.locator("#modalTitle").inner_text().startswith("Growth · ")
                    assert page.locator("#modalBody").get_by_text("Brand readiness: FAIL").count()==1
                    page.locator("#modalBody button",has_text="Creative personality").click()
                    page.locator("#modalBody textarea[name='voice']").fill("Clear, clever, evidence-driven")
                    page.locator("#modalBody input[name='humor']").fill("6")
                    page.locator("#modalBody input[name='provocation']").fill("2")
                    page.locator("#modalBody textarea[name='boundaries']").fill("No invented evidence")
                    page.locator("#modalBody button",has_text="Save reviewed record").click()
                    page.locator("#modalTitle").wait_for(state="visible")
                    page.wait_for_function("document.querySelector('#modalTitle')?.textContent?.startsWith('Growth · ')",timeout=15000)
                    assert page.request.get(BASE+"/api/growth/project/standard-slot-1").json()["mischief"]["voice"]=="Clear, clever, evidence-driven"
                    assert page.request.get(BASE+"/api/growth/project/standard-slot-2").json()["mischief"] is None
                    page.locator("#closeModal").click()
                    page.locator(".nav[data-screen='home']").click()
                    assert page.get_by_role("button",name="Growth portfolio").count()==1
                    page.get_by_role("button",name="Today's action").click()
                    page.wait_for_function("document.querySelector('#modalTitle')?.textContent?.startsWith('Today · ')",timeout=15000)
                    page.locator("#closeModal").click()
                    result["functional"].append("Growth OS entry, readiness, saved per-brand persona, isolation and Today UI")



                assert not result["errors"], "Browser JS errors: "+repr(result["errors"])
                page.close()
            browser.close()
        (OUT/"acceptance.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
        print(json.dumps(result))
    finally:
        proc.terminate()
        try:proc.wait(timeout=7)
        except subprocess.TimeoutExpired:proc.kill()
