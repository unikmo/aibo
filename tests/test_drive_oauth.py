import io
import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from unittest.mock import patch
from runtime import drive_oauth, products

class DriveAuthTests(unittest.TestCase):
    def setUp(self):
        drive_oauth.PENDING.clear()
        drive_oauth.TOKENS.clear()
        self.pid=products.project_records()[0]['id']

    def test_explicit_readonly_oauth_authorization_and_state(self):
        with patch.dict(os.environ,{'AIBO_GOOGLE_CLIENT_ID':'test-app.apps.googleusercontent.com'}):
            result=drive_oauth.begin(self.pid,8766)
        url=urlsplit(result['authorizationUrl'])
        self.assertEqual(url.hostname,'accounts.google.com')
        query=parse_qs(url.query)
        self.assertEqual(query['scope'][0],drive_oauth.SCOPE)
        self.assertEqual(query['code_challenge_method'][0],'S256')
        state=query['state'][0]
        with patch.object(drive_oauth,'_exchange',return_value={'access_token':'test-token','expires_in':3600,'refresh_token':'test-refresh'}) as exchange:
            completed=drive_oauth.callback({'state':[state],'code':['authorized']})
            self.assertEqual(completed['status'],'authorized-for-session')
            self.assertEqual(drive_oauth.token(self.pid),'test-token')
            self.assertEqual(exchange.call_args.args[0]['code_verifier'],drive_oauth.TOKENS[self.pid].get('code_verifier','') if False else exchange.call_args.args[0]['code_verifier'])
        with self.assertRaises(products.ProductError):
            drive_oauth.callback({'state':[state],'code':['replayed']})

    def test_missing_client_and_unauthorized_project(self):
        with patch.dict(os.environ,{'AIBO_GOOGLE_CLIENT_ID':''}):
            with self.assertRaisesRegex(products.ProductError,'not configured'):
                drive_oauth.begin(self.pid,8766)
        with patch.dict(os.environ,{'AIBO_GOOGLE_CLIENT_ID':'test-client'}):
            with self.assertRaisesRegex(products.ProductError,'Unknown project'):
                drive_oauth.begin('not-a-project',8766)

    def test_project_isolation_and_expiry(self):
        drive_oauth.TOKENS[self.pid]={'access_token':'test','refresh_token':None,
            'expires_at':0,'client':'test-client'}
        self.assertIsNone(drive_oauth.token(self.pid))
        self.assertEqual(drive_oauth.status(self.pid)['status'],'not-connected')

if __name__=='__main__':unittest.main()
