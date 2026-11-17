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
 def test_standard_cannot_unlock_via_client(self):
  with self.assertRaises(products.ProductError):products.update_project('standard','1',{'name':'Demo','goal':'Profit','licensed':True})
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
