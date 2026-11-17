import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('products', ROOT/'runtime/products.py')
products=importlib.util.module_from_spec(spec);spec.loader.exec_module(products)

class CreationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=Path(self.tmp.name)
        (self.p/'Projects').mkdir()
        (self.p/'Industry-Packs'/'Local').mkdir(parents=True)
        (self.p/'Industry-Packs'/'Local'/'PACK-OVERVIEW.md').write_text('core')
        (self.p/'Industry-Packs'/'Local'/'PACK-ADDON.md').write_text('addon')
        (self.p/'System').mkdir()
        self.original_registry={'projects':[{'id':'old','name':'Original',
            'projectHome':'Projects/Original','classification':{'status':'pending-pack'}}],
            'workspace':'keep-metadata'}
        products.write_json(self.p/'System'/'project-registry.json',self.original_registry)
        (self.p/'Projects'/'Original').mkdir()
        (self.p/'Projects'/'Original'/'do-not-touch.txt').write_text('keep')
        self.old=(products.ROOT,products.REGISTRY,products.STATE)
        products.ROOT=self.p;products.REGISTRY=self.p/'System'/'project-registry.json';products.STATE=self.p/'state'
    def tearDown(self):
        products.ROOT,products.REGISTRY,products.STATE=self.old
        self.tmp.cleanup()
    def test_additive_creation_preserves_existing_data(self):
        r=products.create_custom_project({'name':'New Branch','industry':'Local Services',
            'corePack':'Industry-Packs/Local/PACK-OVERVIEW.md',
            'addOns':['Industry-Packs/Local/PACK-ADDON.md'],'region':'Munich'})
        self.assertEqual(r['totalProjects'],2)
        self.assertEqual((self.p/'Projects'/'Original'/'do-not-touch.txt').read_text(),'keep')
        state=json.loads(products.REGISTRY.read_text())
        self.assertEqual(state['projects'][0],self.original_registry['projects'][0])
        self.assertEqual(state['workspace'],'keep-metadata')
        self.assertEqual(state['projects'][1]['region'],'Munich')
        self.assertTrue((self.p/'Projects'/'new-branch'/'PROJECT-KNOWLEDGE.json').exists())
        self.assertEqual(len(products.custom_projects()),2)
    def test_no_existing_folder_replacement(self):
        (self.p/'Projects'/'in-use').mkdir()
        (self.p/'Projects'/'in-use'/'keep').write_text('safe')
        with self.assertRaises(products.ProductError):
            products.create_custom_project({'name':'In Use'})
        self.assertEqual((self.p/'Projects'/'in-use'/'keep').read_text(),'safe')
        self.assertEqual(len(json.loads(products.REGISTRY.read_text())['projects']),1)
    def test_duplicate_rejected(self):
        products.create_custom_project({'name':'New Branch'})
        with self.assertRaises(products.ProductError):products.create_custom_project({'name':'New Branch'})
        self.assertEqual(len(json.loads(products.REGISTRY.read_text())['projects']),2)
    def test_unlisted_pack_rejected(self):
        with self.assertRaises(products.ProductError):
            products.create_custom_project({'name':'Trial','industry':'X','corePack':'../../private'})
        self.assertFalse((self.p/'Projects'/'trial').exists())
    def test_cross_industry_addons_rejected(self):
        (self.p/'Industry-Packs'/'Other').mkdir()
        (self.p/'Industry-Packs'/'Other'/'PACK-ADDON.md').write_text('addon')
        with self.assertRaises(products.ProductError):
            products.create_custom_project({'name':'Trial','industry':'Local','corePack':'Industry-Packs/Local/PACK-OVERVIEW.md',
                'addOns':['Industry-Packs/Other/PACK-ADDON.md']})
    def test_names_and_path_validation(self):
        for bad in ('..','!!!','A','Original'):
            with self.assertRaises(products.ProductError):products.create_custom_project({'name':bad})

if __name__=='__main__':unittest.main()
