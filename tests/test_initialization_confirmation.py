"""Regression contract: a successful onboarding save must not be reported as failed
only because a separate dashboard refresh fails.
"""
from pathlib import Path
import unittest

APP = Path(__file__).resolve().parents[1] / "Control-Centre" / "v3" / "app.js"


class InitializationConfirmationTests(unittest.TestCase):
    def test_completed_setup_is_confirmed_before_dashboard_refresh(self):
        source = APP.read_text(encoding="utf-8")
        start = source.index("function formModal(")
        end = source.index("function closeModal()", start)
        modal = source[start:end]
        save = modal.index("const outcome=await submit(")
        confirmation = modal.index('notice("Project ready"', save)
        dashboard_refresh = modal.index("await refresh()", save)
        self.assertLess(save, confirmation)
        self.assertLess(confirmation, dashboard_refresh)

    def test_dashboard_refresh_failure_is_handled_separately(self):
        source = APP.read_text(encoding="utf-8")
        modal = source.split("function formModal(", 1)[1].split("function closeModal()", 1)[0]
        self.assertIn("catch(refreshError)", modal)
        self.assertIn('if(outcome!=="project-saved")notice("Saved"', modal)


if __name__ == "__main__":
    unittest.main()
