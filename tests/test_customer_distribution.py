"""Static packaging regression: commercial installers must not expose founder portfolio."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class CustomerDistributionTests(unittest.TestCase):
    def test_windows_customer_build_removes_founder_registry_by_default(self):
        script=(ROOT/'build-windows.ps1').read_text(encoding='utf-8')
        self.assertIn('[switch]$OwnerPortfolio',script)
        self.assertIn("if(-not $OwnerPortfolio)",script)
        self.assertIn("'project-registry.json'",script)
        self.assertIn('{"projects":[]}',script)
        self.assertIn('--add-data "$bundleSystem;System"',script)

    def test_macos_customer_build_removes_founder_registry_by_default(self):
        script=(ROOT/'build-macos.sh').read_text(encoding='utf-8')
        self.assertIn('AIBO_OWNER_PORTFOLIO',script)
        self.assertIn('customer-System',script)
        self.assertIn('{"projects":[]}',script)
        self.assertIn('--add-data "$BUNDLE_SYSTEM:System"',script)

    def test_customer_default_uses_standard_without_owner_portfolio(self):
        js=(ROOT/'Control-Centre/v3/app.js').read_text(encoding='utf-8')
        self.assertIn('EXPLICIT_EDITION',js)
        self.assertIn('?"custom":"standard"',js)
        self.assertIn('if(owner.projects?.length)S.edition="custom"',js)
        self.assertNotIn('License not activated',js)


if __name__=='__main__':
    unittest.main()
