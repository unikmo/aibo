"""Public deployment checks. Static shell != full production runtime."""
import sys
import urllib.error
import urllib.request

BASE = "https://antibalcony.com"
PAGES = {
    "/": ("text/html", b"CariFive"),
    "/v3/": ("text/html", b"CariFive"),
    "/v3/app.js": ("javascript", b"CariFive"),
    "/v3/manifest.webmanifest": ("json", b"/v3/"),
    "/v3/sw.js": ("javascript", b"cache"),
}
PRIVATE_APIS = ["/api/readiness", "/api/portfolio/custom", "/api/ai-providers", "/api/actions", "/api/cost-controls"]


def get(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "AIBO-Release-Gate/1"})
    try:
        with urllib.request.urlopen(req, timeout=18) as response:
            return response.status, response.headers, response.read(400000)
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read(10000)


def main():
    errors = []
    for path, (content_type, marker) in PAGES.items():
        try:
            status, headers, body = get(path)
            ok = status == 200 and content_type in headers.get("Content-Type", "").lower() and marker in body
            print(f"{'PASS' if ok else 'FAIL'} route {path}: HTTP {status}")
            if not ok:
                errors.append(f"{path}: expected HTTP 200, {content_type}, and marker")
        except Exception as exc:
            errors.append(f"{path}: {exc}")
    for path in PRIVATE_APIS:
        try:
            status, headers, body = get(path)
            content_type = headers.get("Content-Type", "").lower()
            # The static preview must never make local APIs remotely reachable.
            safe = status in (401, 403, 404, 405, 410) and "application/json" not in content_type
            print(f"{'PASS' if safe else 'FAIL'} private API {path}: HTTP {status}")
            if not safe:
                errors.append(f"{path}: public API exposure or unexpectedly successful response")
        except Exception as exc:
            errors.append(f"{path}: {exc}")
    if errors:
        for err in errors:
            print("ERROR:", err, file=sys.stderr)
        return 1
    print("PUBLIC STATIC PREVIEW verified. Full production backend is NOT verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
