"""Regression checks for Windows PyInstaller's extracted resource directory."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WindowsBundleResourcesTests(unittest.TestCase):
    def test_frozen_runtime_uses_extraction_root(self):
        # Isolate imports so normal test discovery does not retain already-loaded modules.
        with tempfile.TemporaryDirectory() as temporary:
            script = """
import sys
from pathlib import Path
sys._MEIPASS = sys.argv[1]
sys.path.insert(0, sys.argv[2])
import products, aibo
expected = Path(sys.argv[1])
assert products.ROOT == expected, (products.ROOT, expected)
assert aibo.ROOT == expected, (aibo.ROOT, expected)
assert products.REGISTRY == expected / 'System' / 'project-registry.json'
assert aibo.ROSTER == expected / 'runtime' / 'agents.json'
"""
            run = subprocess.run(
                [sys.executable, "-c", script, temporary, str(ROOT / "runtime")],
                capture_output=True, text=True, timeout=20, check=False,
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_windows_bundle_contains_required_resource_directories(self):
        script = (ROOT / "build-windows.ps1").read_text(encoding="utf-8")
        for item in (
            'Control-Centre;Control-Centre',
            'System;System',
            'Industry-Packs;Industry-Packs',
            'runtime\\agents.json;runtime',
        ):
            with self.subTest(item=item):
                self.assertIn(item, script)


if __name__ == "__main__":
    unittest.main()
