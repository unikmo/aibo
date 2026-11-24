"""Unit coverage of the platform-neutral native desktop lifecycle, without a GUI."""
import importlib
import pathlib
import sys
import threading
import types
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))
desktop_shell = importlib.import_module("desktop_shell")


class FakeServer:
    server_port = 49115

    def __init__(self):
        self.started = threading.Event()
        self.stopped = threading.Event()
        self.closed = False

    def serve_forever(self):
        self.started.set()
        self.stopped.wait(5)

    def shutdown(self):
        self.stopped.set()

    def server_close(self):
        self.closed = True


class DesktopShellTests(unittest.TestCase):
    def test_native_window_uses_loopback_and_closes_server(self):
        server = FakeServer()
        calls = []

        class FakeWebView:
            def create_window(self, title, url, **kwargs):
                self.assert_called = True
                calls.append((title, url, kwargs))

            def start(self, **kwargs):
                self.started = True
                self_start = server.started.wait(3)
                if not self_start:
                    raise AssertionError("Local server did not start before native UI")

        fake = FakeWebView()
        desktop_shell.launch_window(server_factory=lambda port, retries: server,
                                    webview_module=fake)
        self.assertEqual(calls[0][1], "http://127.0.0.1:49115/v3/")
        self.assertEqual(calls[0][0], "AIBO Control Centre")
        self.assertTrue(server.closed)
        self.assertTrue(server.stopped.is_set())

    def test_gui_close_on_error_still_closes_server(self):
        server = FakeServer()

        class BrokenWebView:
            def create_window(self, *args, **kwargs):
                raise RuntimeError("Native renderer missing")

        with self.assertRaisesRegex(RuntimeError, "renderer"):
            desktop_shell.launch_window(server_factory=lambda port, retries: server,
                                        webview_module=BrokenWebView())
        self.assertTrue(server.closed)
        self.assertTrue(server.stopped.is_set())

    def test_gui_backend_is_not_imported_in_headless_path(self):
        # The GUI subprocesses are tested in packaged Windows/macOS CI; this
        # unit test verifies module import does not require a display server.
        self.assertFalse("webview" in desktop_shell.__dict__)


if __name__ == "__main__":
    unittest.main()
