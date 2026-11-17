import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
import aibo, costs, products

class CostControlsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=products.STATE
        products.STATE=Path(self.tmp.name)
    def tearDown(self):
        products.STATE=self.old
        self.tmp.cleanup()
    def test_default_and_saved_limits(self):
        self.assertEqual(costs.current()['maxOutputTokens'],1800)
        value={'maxOutputTokens':4096,'maxModelCalls':5,'monthlyBudgetUsd':90,'perTaskBudgetUsd':15}
        self.assertEqual(costs.update(value),value)
        self.assertEqual(costs.current(),value)
    def test_incorrect_limits_cannot_change_record(self):
        base=costs.current()
        with self.assertRaises(products.ProductError):
            costs.update({**base,'maxOutputTokens':999999})
        with self.assertRaises(products.ProductError):
            costs.update({**base,'maxModelCalls':True})
        with self.assertRaises(products.ProductError):
            costs.update({**base,'perTaskBudgetUsd':1000})
        self.assertEqual(costs.current(),base)
    def test_preflight_blocks_before_provider_call(self):
        from unittest.mock import patch
        with patch.object(aibo,'provider_call') as call:
            project=aibo.load_json(aibo.REGISTRY)['projects'][0]['id']
            with self.assertRaisesRegex(aibo.AiboError, 'Model-call limit exceeded'):
                aibo.execute(project,'research website',agents=['research','engineering'],max_model_calls=2)
            call.assert_not_called()
    def test_output_limit_argument_is_forwarded(self):
        from unittest.mock import patch
        project=aibo.load_json(aibo.REGISTRY)['projects'][0]['id']
        with patch.object(aibo,'provider_call',return_value='ok') as call:
            aibo.execute(project,'research',agents=['research'],max_model_calls=3,output_token_limit=4096)
            self.assertEqual(call.call_count,3)
            self.assertTrue(all(c.args[-1]==4096 for c in call.call_args_list))
