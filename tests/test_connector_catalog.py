import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'runtime'))
import connector_catalog as c

class ConnectorCatalogTests(unittest.TestCase):
    def test_scope_and_requested_providers(self):
        names={x['name'] for x in c.entries()}
        self.assertGreaterEqual(len(names), 240)
        for name in ('Instagram','TikTok','YouTube','Buffer','Canva','HeyGen','VEED',
                     'Vercel','Supabase','Firebase','Netlify','Resend',
                     'Playwright','Google Chrome','Microsoft Outlook Email',
                     'Printful','Printify','Gelato Print','Gooten','Prodigi',
                     'DSers','CJdropshipping','Spocket','Zendrop','AutoDS',
                     'ShipStation','WooCommerce','Etsy','Pinterest','Pinterest Ads',
                     'Puppeteer','Playwright MCP',
                     'Amazon Kindle Direct Publishing (KDP)','Kobo Writing Life',
                     'Apple Books for Authors','Draft2Digital','BookBub Ads',
                     'Amazon Ads for Books','Gumroad','Payhip','Creative Fabrica',
                     'Goodnotes Marketplace','Zedge','Walli','Pinterest Business'):
            self.assertIn(name,names)
        self.assertEqual(len(names),len(c.entries()))
        self.assertFalse(any(x['connected'] for x in c.entries()))

    def test_runtime_registration_does_not_imply_auth(self):
        entry=next(x for x in c.entries() if x['name']=='GitHub')
        self.assertIn(entry['status'],('catalog-only','runtime-registered'))
        self.assertFalse(entry['connected'])

    def test_request_additive_and_scoped(self):
        with tempfile.TemporaryDirectory() as t:
            with patch.object(c,'STATE',Path(t)):
                with patch('products.custom_projects', return_value=[{'id':'example'}]):
                    x=c.request_connection({'connector':'resend','project':'example'})
                    self.assertEqual(x['request']['status'],'setup-requested')
                    y=c.request_connection({'connector':'resend','project':'example'})
                    self.assertTrue(y['alreadyRequested'])
                    self.assertEqual(len(c.requests()),1)
                    self.assertNotIn('secret',json.dumps(c.requests()).lower())
                    with self.assertRaises(ValueError):
                        c.request_connection({'connector':'resend','project':'wrong'})
                    with self.assertRaises(ValueError):
                        c.request_connection({'connector':'unlisted','project':'example'})

if __name__=='__main__':unittest.main()
