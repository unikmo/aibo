# AIBO release gates — required evidence before founder UAT

Scope: Control Centre, project setup, Soni providers, local state, Windows executable.
Never use real credentials, external actions or paid calls without explicit approval.

| Stage | Automated coverage | Pass criteria |
|---|---|---|
| 1 Unit & integration | Compile all Python; run full unittest discovery, covering providers, setup, consent, local records and source isolation | Zero failures |
| 2 Smoke | Start isolated local server, check UI/API; separately compile and smoke Windows executable | Core paths HTTP 200; packaged mock execution works |
| 3 Functional | Desktop/mobile Playwright on five Control Centre pages; setup, local runs and UI errors | Zero functional failures |
| 4 Sanity | Targeted Soni viewport + dark-theme test with 70 message history at three screen sizes | Composer visible; history alone scrolls; correct colors |
| 5 Regression | Repeat complete test suite after fixes; preserve browser evidence | No regressions |
| 6 Security & performance | Negative loopback/cross-origin/method/traversal tests, secret-literal check, 48 concurrent local reads | No bypass, HTTP errors or p95 over 2500ms |
| 6b Owner acceptance | Founder reviews actual business usability and accurate information | Explicit owner approval, never CI self-certified |
| 7 Production smoke | Run qa/production_smoke.ps1 on the user's actual local installation | Correct UI/API responds without paid calls |

## Release rule

- If any automated stage fails, reject the build and rerun all dependent stages after the fix.
- Windows bundle verification is a second mandatory build check.
- A green CI result means **AUTOMATED PRE-RELEASE PASS**, not **PRODUCTION READY**.
- Synthetic tests cannot verify user CLI credentials, paid API costs, authenticated external provider access, external outreach, or a real installed environment.
- The security/concurrency checks are bounded probes, **not** a penetration test, dependency audit, sustained load test, or accessibility certification.
- GitHub branch protection must require these workflows before merge. Merely adding a workflow does not prevent manual bypass by a repository administrator.
- Keep real tokens, personal data and private documents out of CI artifacts.
- Owner acceptance is a required external decision after developer tests; post-install smoke is run after the local software has been updated.

## Post-install read-only smoke

In Windows PowerShell, run:

    cd C:\Users\mbanw\AIBO-v3-test
    pwsh -File qa\production_smoke.ps1 -BaseUrl http://127.0.0.1:8766

Do not mark stage 7 PASS unless it has been executed against the actual installed build.
