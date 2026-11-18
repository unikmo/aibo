"""AIBO Control Centre v3 visual preview: independent browser acceptance checks."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qa" / "control-centre-preview"
OUT.mkdir(parents=True, exist_ok=True)
PORT = 8769
URL = f"http://127.0.0.1:{PORT}/preview/"
errors = []
results = []
with tempfile.TemporaryDirectory() as temp:
    env = dict(os.environ, AIBO_STATE_DIR=temp)
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "runtime" / "control_server.py"),
         "--port", str(PORT), "--strict-port"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=env,
    )
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for viewport, width, height in [("desktop", 1440, 940), ("mobile", 390, 844)]:
                page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
                page.on("pageerror", lambda error: errors.append(str(error)))
                ready = False
                for _ in range(35):
                    try:
                        page.goto(URL, wait_until="domcontentloaded", timeout=1500)
                        ready = True
                        break
                    except Exception:
                        time.sleep(.25)
                if not ready:
                    raise RuntimeError("Preview local server did not start")
                page.wait_for_timeout(300)
                assert page.locator(".nav").count() == 5
                for screen in ["home", "soni", "projects", "activity", "connections"]:
                    page.locator(f'button.nav[data-screen="{screen}"]').click()
                    page.locator("#screen-" + screen + ".active").wait_for()
                    assert page.locator(".screen.active").count() == 1
                    page.screenshot(path=str(OUT / f"{screen}-{viewport}.png"), full_page=True)
                    results.append(f"{screen}-{viewport}")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), f"Horizontal overflow at {viewport}"
                assert not errors, "Browser JavaScript errors: " + "; ".join(errors)
                page.close()
            browser.close()
        (OUT / "acceptance.json").write_text(
            json.dumps({"passed": len(results), "failed": 0, "screenshots": results}, indent=2),
            encoding="utf-8",
        )
        print(json.dumps({"passed": len(results), "screenshots": results}))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
