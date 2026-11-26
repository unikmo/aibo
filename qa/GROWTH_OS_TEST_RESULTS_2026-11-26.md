# CariFive Growth OS — independently executed QA, 2026-11-26

## Test environment and scope
- Source: `feature/carifive-perpetual-purchase-20261126` in `unikmo/aibo` (PR #25), fetched through authenticated repository access and executed as an isolated non-production copy.
- Runtime: Linux, Python 3.11.17, Node 22, headless Playwright Chromium; temporary `AIBO_STATE_DIR`; no customer secrets or live provider account.
- Verification commands are reproducible against a checkout with the declared dependencies installed.

## Verified execution results

| Gate | Command | Result |
|---|---|---|
| Python syntax | `python3 -m compileall -q runtime tests qa` | PASS |
| Full unit and HTTP integration regression | `python3 -m unittest discover -s tests -q` | **219 run, 218 pass, 1 skipped, 0 failures** |
| Growth OS-specific tests | `python3 -m unittest discover -s tests -p 'test_growth*.py' -v` | **32/32 passed** (included in 219 above) |
| Full Control Centre v3 desktop/mobile browser journey | `python3 qa/v3_acceptance.py` | PASS, **10 screens, 18 functional checkpoints, 0 JavaScript page errors** |
| Legacy Standard and Portfolio frontend/back-end smoke | `python3 qa/browser_smoke.py` | PASS, **13 checks passed, 0 failed** |
| PWA installability and cache isolation | `python3 qa/pwa_acceptance.py` | PASS: manifest, service-worker scope, non-cached private API, navigation |
| CariFive chat responsive layout | `python3 qa/soni_sanity.py` | PASS at **1440×930, 390×844, 768×750** |
| Local startup, security and concurrent request smoke | `python3 qa/release_nonfunctional.py` | PASS: 48 requests, 8-way concurrency, p95 **34.6 ms**, 0 HTTP failures |
| Independent semantic-output gate with no actual provider reports | `python3 qa/output_quality_gate.py unreviewed-runs.json` | **BLOCKED / expected FAIL**: missing 12 reviewed real-provider cases |

## Defects found and repaired during actual execution

1. **Critical:** `runtime/products.py` had a source string containing literal backslash-n characters in the module docstring, causing a Python `SyntaxError`. Corrected; import and compile now pass.
2. **Project scope regression:** `runtime/agent_setup.py` and `runtime/connector_catalog.py` stopped accepting existing mocked Portfolio project identities after Standard integration. Fixed validation to accept Portfolio and Standard while preserving isolation. The complete 219-test suite now passes.
3. **V3 browser acceptance defects:** Standard setup / Growth OS steps clicked controls while Projects was hidden. Fixed navigation; also waited for async Today modal before asserting. Re-run passes.
4. **Legacy frontend smoke was stale:** It loaded non-existent `navigation.js` and `ai-providers-ui.js`. Updated the script to use actual live frontend assets and real project-edition checks. Re-run passes 13/13.
5. The standalone PWA acceptance initially failed in the **test copy** because `sw.js` was not yet transferred to the isolated environment; with the source file present, the original acceptance passed unchanged. This was an environment completeness issue, not a repository repair.

## Important limits and blocked release gates

- **90% substantive real AI output quality is NOT certified.** Zero of 12 required real-provider scenarios were executed and independently scored; the fail-closed gate correctly refuses to issue a grade.
- **No clean install on a customer's Windows PC** was performed. Windows and macOS installer generation/signing and platform-native binary launches were not verified in this Linux sandbox.
- **No real third-party social publishing, email sending, paid ad activity, purchase checkout, or authenticated analytics** were exercised. Mock task completions are not delivery receipts.
- GitHub Actions workflow jobs were repeatedly reported failed with **zero executed steps** and inaccessible logs; the reason for runner startup failure has not been determined. These **independent sandbox tests** establish a different evidence path; they do not imply GitHub CI checks passed.
- The legacy shared application requests `/api/control`, which currently returns 404 and leaves its legacy usage-control display in explicit demo mode. Modern Control Centre v3 uses `/api/cost-controls`. Do not misrepresent legacy demo controls as authenticated cost accounting.
- The existing one skipped test requires unavailable native `.claude`/`.codex` agent configuration files. No fake PASS was assigned.

## Verdict

**PASS:** Core Growth OS logic and isolated local integration, Control Centre v3 interactions, mobile/desktop browser, PWA, local security/performance smoke.

**NOT READY FOR CUSTOMER RELEASE:** Real 12-scenario output-quality assessment, clean native Windows installer validation, seller-side checkout/upgrade delivery, and verified GitHub CI status remain unresolved.

Do not merge into `main` or claim full 90% semantic certification without those gates.
