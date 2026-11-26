"""Real browser acceptance for premium, chat-first CariFive Control Centre.

Uses isolated temporary backend, real API routes and mock AI only. No payments,
publishing, live model calls or production data. Works with Playwright.
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
PORT=8797
BASE=f"http://127.0.0.1:{PORT}"

def run():
    results=[]
    with tempfile.TemporaryDirectory(prefix="carifive-premium-qa-") as state:
        env=dict(os.environ,AIBO_STATE_DIR=state)
        server=subprocess.Popen([sys.executable,str(ROOT/'runtime'/'control_server.py'),
            '--port',str(PORT),'--strict-port'],cwd=ROOT,env=env,
            stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True)
                for width,height in ((1440,900),(390,844)):
                    page=browser.new_page(viewport={'width':width,'height':height})
                    errors=[];network=[]
                    page.on('pageerror',lambda e: errors.append(str(e)))
                    page.on('response',lambda r:network.append([r.status,r.url]) if r.status>=400 else None)
                    for attempt in range(40):
                        try:
                            response=page.goto(BASE+'/v3/?edition=standard',wait_until='load',timeout=2000)
                            if response.status==200:break
                        except Exception:
                            if attempt==39:raise
                            time.sleep(.2)
                    page.wait_for_function("document.querySelector('#countProjects')?.textContent==='5'",timeout=15000)
                    assert page.locator('.nav[data-screen="soni"]').count()==1
                    assert page.locator('.nav[data-screen="growth"]').count()==1
                    assert page.locator('#homeTalkForm').is_visible()
                    assert page.locator('#homePortfolio .portfolio-tile').count()==3
                    assert page.locator('#homePortfolio .portfolio-state').count()==3
                    assert page.locator('#homeTalkPrompt').get_attribute('placeholder')=="Ask CariFive anything…"
                    assert page.locator('#screen-home .home-talk-head').count()==0
                    assert page.locator('#settingsBtn').count()==1
                    assert page.locator('#accountBtn').count()==1
                    assert page.locator('#homeModule').count()==1
                    assert page.locator('#soniModule').count()==1
                    assert page.locator('#homeTalkPrompt').evaluate("(el)=>getComputedStyle(el).resize")=="none"
                    assert 'No brand' in page.locator('#growthReadyValue').inner_text()
                    page.wait_for_function("document.querySelector('#todayTitle')?.textContent!=='Looking for a high-value next step…'",timeout=15000)
                    assert page.evaluate('document.documentElement.scrollWidth-window.innerWidth')<=3
                    assert page.evaluate("getComputedStyle(document.body).backgroundColor")=="rgb(247, 248, 252)"
                    assert not errors,errors
                    assert not network,network
                    # Home composer retains the task and requests a project rather than using global context.
                    task="Review marketing positioning and growth opportunities."
                    page.locator('#homeModule').select_option('marketing')
                    page.locator('#homeTalkPrompt').fill(task)
                    page.locator('#homeTalkPrompt').press('Shift+Enter')
                    page.locator('#homeTalkPrompt').type('Prioritize quick wins.')
                    submitted=task+'\nPrioritize quick wins.'
                    assert page.locator('#homeTalkPrompt').input_value()==submitted
                    page.locator('#homeTalkPrompt').press('Enter')
                    assert page.locator('#screen-soni').is_visible()
                    assert page.locator('#soniPrompt').input_value()==submitted
                    assert page.locator('#soniModule').input_value()=='marketing'
                    assert 'Choose a project' in page.locator('#promptHint').inner_text()
                    # Finish reviewed setup in the isolated local backend, then use real mock execution.
                    init=page.request.post(BASE+'/api/setup/custom/standard-slot-1',data={
                        'fields':{'name':'Demo Project','goal':'Grow local enquiries','region':'Germany'},
                        'step':2,'complete':True},headers={'Content-Type':'application/json'})
                    assert init.ok,init.text()
                    page.locator('#projectSelect').select_option('standard-slot-1')
                    page.locator('#soniProvider').select_option('mock')
                    page.locator('#soniPrompt').press('Enter')
                    page.wait_for_function("document.querySelector('#promptHint')?.textContent==='Completed'",timeout=20000)
                    # Growth OS is real navigation, never a fictional connected channel.
                    # A new home message must never reuse earlier paid-provider consent.
                    page.locator('#soniProvider').select_option('openai')
                    page.locator('#soniConsent').check()
                    page.locator('.nav[data-screen="home"]').click()
                    page.locator('#homeTalkPrompt').fill('Review the financial risk of this launch.')
                    page.locator('#homeTalkPrompt').press('Enter')
                    assert page.locator('#screen-soni').is_visible()
                    assert not page.locator('#soniConsent').is_checked()
                    assert 'paid API request' in page.locator('#promptHint').inner_text()
                    assert page.locator('#soniPrompt').input_value().startswith('Review the financial')
                    page.locator('.nav[data-screen="growth"]').click()
                    assert page.locator('#screen-growth').is_visible()
                    assert 'not independently verified' in page.locator('#growthScreenSummary').inner_text().lower() or 'No brand growth profile' in page.locator('#growthScreenSummary').inner_text()
                    assert not errors,errors
                    assert not network,network
                    results.append({'width':width,'height':height,'status':'PASS',
                                    'jsErrors':len(errors),'httpErrors':len(network)})
                    page.close()
                browser.close()
        finally:
            server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.kill()
    print(json.dumps({'status':'PASS','checks':results,'note':
        'Local-only mock execution; no real AI, publication, payments or production deployment.'}))
    return 0

if __name__=='__main__':
    raise SystemExit(run())
