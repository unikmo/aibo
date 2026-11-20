"""Focused sanity gate for the recently fixed Soni composer and dark-theme defects."""
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

def run():
    with tempfile.TemporaryDirectory(prefix="aibo-soni-sanity-") as state:
        env=dict(os.environ,AIBO_STATE_DIR=state)
        proc=subprocess.Popen([sys.executable,str(ROOT/"runtime"/"control_server.py"),
            "--port","0","--strict-port"],cwd=ROOT,env=env,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,text=True)
        try:
            lines=queue.Queue()
            threading.Thread(target=lambda:lines.put(proc.stdout.readline()),daemon=True).start()
            line=lines.get(timeout=12)
            m=re.search(r"http://127\.0\.0\.1:(\d+)/v3/",line)
            assert m,line
            url="http://127.0.0.1:"+m.group(1)+"/v3/#soni"
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(headless=True)
                for width,height in ((1440,930),(390,844),(768,750)):
                    page=browser.new_page(viewport={"width":width,"height":height})
                    page.goto(url,wait_until="domcontentloaded")
                    page.locator("#screen-soni.active").wait_for()
                    # Insert a realistic long history into the actual DOM.
                    page.locator("#conversation").evaluate("""el => {
                       for(let i=0;i<70;i++){
                         const bubble=document.createElement('div');
                         bubble.className=i%2?'log-item user':'log-item agent';
                         bubble.textContent='History item '+i+': previously recorded project status and notes.';
                         el.append(bubble);
                       }
                    }""")
                    geometry=page.evaluate("""() => {
                      const r=id=>document.querySelector(id).getBoundingClientRect();
                      const conversation=document.querySelector('#conversation');
                      const color=getComputedStyle(conversation);
                      return {historyBottom:r('#conversation').bottom,
                        composerTop:r('#soniPrompt').top,composerBottom:r('#soniPrompt').bottom,
                        viewport:innerHeight,
                        scrollHeight:conversation.scrollHeight,
                        clientHeight:conversation.clientHeight,
                        background:color.backgroundColor,color:color.color};
                    }""")
                    assert geometry["scrollHeight"]>geometry["clientHeight"]+100,geometry
                    assert geometry["historyBottom"]<=geometry["composerTop"]+2,geometry
                    assert geometry["composerBottom"]<geometry["viewport"]-10,geometry
                    assert geometry["background"]=="rgb(36, 41, 39)",geometry
                    assert geometry["color"]=="rgb(244, 243, 238)",geometry
                    assert page.locator("#soniPrompt").is_visible()
                    print("SONI_SANITY_PASS",width,height)
                    page.close()
                browser.close()
        finally:
            proc.terminate()
            try:proc.wait(timeout=4)
            except subprocess.TimeoutExpired:proc.kill()

if __name__=="__main__":run()
