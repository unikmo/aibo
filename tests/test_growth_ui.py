"""Growth UI integration contract and JS parse checks (no browser or network required)."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
JS=ROOT/'Control-Centre'/'v3'/'growth.js'


class GrowthUiTests(unittest.TestCase):
    def test_growth_module_loaded_by_real_control_centre(self):
        html=(ROOT/'Control-Centre'/'v3'/'index.html').read_text(encoding='utf-8')
        app=(ROOT/'Control-Centre'/'v3'/'app.js').read_text(encoding='utf-8')
        self.assertIn('<script src="growth.js" defer></script>',html)
        self.assertIn('window.CariFiveGrowth?.open(chosen.id)',app)
        self.assertIn('Growth OS',app)

    def test_growth_panel_has_real_backed_actions(self):
        js=JS.read_text(encoding='utf-8')
        for part in ('/api/growth/project/','/api/growth/brand/',
                     '/api/growth/mischief/','/api/growth/autonomy/',
                     '/api/growth/opportunity/','/api/growth/creative-review/',
                     '/api/growth/experiment/','/api/growth/transition/',
                     '/api/growth/measure/','/api/growth/dashboard',
                     '/api/growth/today'):
            with self.subTest(path=part):
                self.assertIn(part,js)
        self.assertIn('estimatedQualityOnly',(
            ROOT/'runtime'/'growth_engine.py').read_text(encoding='utf-8'))
        self.assertNotIn('window.open("https://linkedin',js)

    @unittest.skipUnless(shutil.which('node'),'Node.js not available for JavaScript syntax check')
    def test_growth_ui_js_parses(self):
        for name in ('growth.js','app.js'):
            proc=subprocess.run(['node','--check',str(ROOT/'Control-Centre'/'v3'/name)],
                capture_output=True,text=True,timeout=15)
            self.assertEqual(proc.returncode,0,proc.stderr)


if __name__=='__main__':
    unittest.main()
