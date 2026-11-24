"""AIBO standalone desktop window: shared localhost runtime, native Windows/macOS WebView.

No Python terminal or external browser is required for normal launch. The existing
HTTP server and its loopback/Host/Origin guards remain authoritative.
"""
import argparse
import os
import sys
import threading

from control_server import create_local_server


def launch_window(server_factory=create_local_server, webview_module=None):
    """Own the server lifetime and close it when the user closes the window."""
    if webview_module is None:
        import webview as webview_module

    server = server_factory(0, 0)  # OS-selected free port; do not collide with old AIBO.
    url = f"http://127.0.0.1:{server.server_port}/v3/"
    thread = threading.Thread(target=server.serve_forever, name="aibo-local-server", daemon=True)
    thread.start()
    try:
        webview_module.create_window(
            "AIBO Control Centre", url,
            width=1330, height=860, min_size=(880, 600),
            confirm_close=False,
        )
        # Cocoa requires GUI on the main thread; Windows uses embedded WebView2.
        webview_module.start(debug=False)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=8)


def main():
    parser = argparse.ArgumentParser(description="AIBO desktop application")
    parser.add_argument(
        "--headless", action="store_true",
        help="Run only the local server for automated packaged smoke tests.",
    )
    parser.add_argument(
        "--verify-desktop", action="store_true",
        help="Verify embedded WebView support in the packaged application.",
    )
    args, remaining = parser.parse_known_args()
    if args.verify_desktop:
        import webview
        assert hasattr(webview, "create_window") and hasattr(webview, "start")
        if sys.stdout is not None:
            print("AIBO embedded WebView module available", flush=True)
        return
    if args.headless:
        # PyInstaller --windowed provides no sys.stdout on Windows.
        # Preserve the runtime server path for automated bundled API checks.
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w", encoding="utf8")
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w", encoding="utf8")
        from control_server import main as server_main
        sys.argv = [sys.argv[0], *remaining]
        server_main()
        return
    if remaining:
        parser.error("Unknown desktop option(s): " + " ".join(remaining))
    launch_window()


if __name__ == "__main__":
    main()
