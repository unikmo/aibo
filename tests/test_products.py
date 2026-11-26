import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('products',ROOT/'runtime/products.py')
products=importlib.util.module_from_spec(spec);spec.loader.exec_module(products)
class ProductTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=products.STATE;products.STATE=Path(self.tmp.name)
 def tearDown(self):products.STATE=self.old;self.tmp.cleanup()
 def test_standard_five_empty_slots(self):
  p=products.standard_state();self.assertEqual(len(p['slots']),5)
  self.assertEqual(p['license']['projectLimit'],5)
  self.assertTrue(all(not s['initialized'] for s in p['slots']))
 def test_perpetual_version_never_expires_or_requires_activation(self):
  policy=products.purchase_model()
  self.assertEqual(policy['type'],'perpetual-version')
  self.assertFalse(policy['activationRequired'])
  self.assertFalse(policy['licenseKeyRequired'])
  self.assertFalse(policy['mandatoryRenewal'])
  self.assertEqual(policy['upgrades']['annualUsd'],48)
  self.assertTrue(policy['upgrades']['noRenewalDisablesExistingVersion'])
  self.assertTrue(policy['support']['statutoryDefectRemediesPreserved'])
 def test_standard_initialize_without_activation_key(self):
  result=products.update_project('standard','1',{'name':'My Shop','region':'Germany','goal':'Find customers'})
  self.assertEqual(result['project'],'standard-slot-1')
  state=products.standard_state()
  self.assertEqual(state['slots'][0]['name'],'My Shop')
  self.assertTrue(state['slots'][0]['setupComplete'])
  self.assertEqual(state['license']['status'],'no-activation-required')
 def test_standard_restarts_and_keeps_workspaces_without_upgrade(self):
  products.update_project('standard','standard-slot-2',{'name':'Another Shop','goal':'Improve sales'})
  self.assertEqual(products.standard_state()['slots'][1]['goal'],'Improve sales')
  self.assertEqual(products.standard_state()['slots'][1]['goal'],'Improve sales')
  self.assertFalse(products.standard_state()['purchase']['mandatoryRenewal'])
 def test_standard_rejects_out_of_scope_slot_and_keeps_portfolio_separate(self):
  initial=len(products.custom_projects())
  with self.assertRaises(products.ProductError):products.update_project('standard','6',{'name':'Bad','goal':'Fail'})
  self.assertEqual(len(products.custom_projects()),initial)
  records=products.project_records()
  self.assertEqual(len([p for p in records if p.get('edition')=='standard']),5)
  self.assertTrue(all(x['id'].startswith('standard-slot-') for x in records if x.get('edition')=='standard'))

 def test_custom_15_independent_projects(self):
  p=products.custom_projects();self.assertGreaterEqual(len(p),15)
  self.assertEqual(len({x['id'] for x in p}),len(p))
 def test_custom_initialization_no_classification_mutation(self):
  before=products.custom_projects();x=before[0]
  products.update_project('custom',x['id'],{'name':x['name'],'region':'Berlin','goal':'Trial'})
  after=next(a for a in products.custom_projects() if a['id']==x['id'])
  self.assertEqual(x['corePack'],after['corePack']);self.assertEqual(x['addOns'],after['addOns'])
  self.assertTrue(after['initialized']);self.assertEqual(after['region'],'Berlin')
 def test_bad_project_rejected(self):
  with self.assertRaises(products.ProductError):products.update_project('custom','does-not-exist',{'name':'x','goal':'y'})
 def test_html_modes_and_shared_scripts(self):
  for mode in ('standard','custom'):
   s=(ROOT/'Control-Centre'/mode/'index.html').read_text(encoding='utf-8')
   self.assertIn('data-product="'+mode+'"',s)
   self.assertIn('../shared/product.js',s)
if __name__=='__main__':unittest.main()
