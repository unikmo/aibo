import ipaddress,os,tempfile,unittest
from unittest.mock import patch
from runtime import browser_qa,products

class BrowserQATests(unittest.TestCase):
    def setUp(self):
        self.project=products.custom_projects()[0]['id']
        self.allowed='example.org'
        self.resolver=lambda host,port,**kw:[(None,None,None,None,('93.184.215.14',port))]
    def test_allowlisted_inspection_is_read_only(self):
        with patch.dict(os.environ,{'AIBO_BROWSER_ALLOWED_HOSTS':self.allowed}):
            result=browser_qa.inspect(self.project,'https://example.org/research','inspect',
                runner=lambda **kw:{'title':'Research','text':'Evidence','javascriptErrors':[]},resolver=self.resolver)
        self.assertEqual(result['text'],'Evidence')
        self.assertFalse(result['externalBusinessAction'])
    def test_unlisted_domain_blocked(self):
        with patch.dict(os.environ,{'AIBO_BROWSER_ALLOWED_HOSTS':self.allowed}):
            with self.assertRaises(products.ProductError):browser_qa.validate(self.project,'https://bad.example/','inspect',resolver=self.resolver)
    def test_private_dns_blocked(self):
        with patch.dict(os.environ,{'AIBO_BROWSER_ALLOWED_HOSTS':self.allowed}):
            resolver=lambda *a,**kw:[(None,None,None,None,('127.0.0.1',443))]
            with self.assertRaises(products.ProductError):browser_qa.validate(self.project,'https://example.org/','inspect',resolver=resolver)
    def test_mutating_action_refused(self):
        with patch.dict(os.environ,{'AIBO_BROWSER_ALLOWED_HOSTS':self.allowed}):
            with self.assertRaises(products.ProductError):browser_qa.validate(self.project,'https://example.org/','click',resolver=self.resolver)
    def test_capability_status_has_no_false_cloud_browser_claim(self):
        result=browser_qa.capabilities()
        self.assertTrue(result['localHttpDiagnostics'])
        self.assertIn('not accessible',result['cloudBrowser'].lower())
        self.assertIsInstance(result['playwrightChromiumInstalled'],bool)
    def test_disabled_permission_blocked(self):
        with patch('runtime.browser_qa.agent_setup.assert_permission',side_effect=products.ProductError('disabled')):
            with self.assertRaises(products.ProductError):browser_qa.validate(self.project,'https://example.org/','inspect',resolver=self.resolver)

if __name__=='__main__':unittest.main()
