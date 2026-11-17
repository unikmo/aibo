import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from runtime import agent_setup, products

class AgentSetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.patch1=patch.object(agent_setup,'PATH',Path(self.tmp.name)/'agent-setup.json')
        self.patch2=patch.object(products,'custom_projects',lambda:[{'id':'gsi'},{'id':'other'}])
        self.patch1.start();self.patch2.start()
    def tearDown(self):
        self.patch2.stop();self.patch1.stop();self.tmp.cleanup()
    def test_defaults_and_project_isolation(self):
        a=agent_setup.get('gsi');self.assertTrue(a['permissions']['research'])
        self.assertTrue(a['permissions']['write_browser'])
        self.assertFalse(a['permissions']['send_mail'])
        agent_setup.update('gsi',{'mailboxes':[{'address':'team@example.com','enabled':True}], 'permissions':{'send_mail':True}})
        self.assertTrue(agent_setup.get('gsi')['permissions']['send_mail'])
        self.assertFalse(agent_setup.get('other')['permissions']['send_mail'])
        self.assertEqual(agent_setup.get('gsi')['mailboxes'][0]['address'],'team@example.com')
    def test_invalid_and_disabled(self):
        for payload in ({'permissions':{'send_mail':'yes'}},{'mailboxes':[{'address':'not-email','enabled':True}]},{'agent':'anyone'}):
            with self.assertRaises(products.ProductError):agent_setup.update('gsi',payload)
        with self.assertRaises(products.ProductError):agent_setup.assert_permission('gsi','send_mail')
        with self.assertRaises(products.ProductError):agent_setup.get('unknown')
    def test_atomic_roundtrip(self):
        agent_setup.update('gsi',{'workingStyle':'supervised','permissions':{'read_browser':False}})
        self.assertEqual(agent_setup.get('gsi')['workingStyle'],'supervised')
        self.assertFalse(agent_setup.get('gsi')['permissions']['read_browser'])
        agent_setup.assert_permission('gsi','research')
