import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from runtime import attachments, products

class TestAttachments(unittest.TestCase):
    def test_project_isolation_and_integrity(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(attachments,'ROOT',Path(tmp)), patch.object(attachments,'_project',lambda pid:None):
            meta=attachments.save('gsi','baseline.csv',b'claim,status\nA,HOLD\n')
            files=attachments.load('gsi',[meta['id']])
            self.assertEqual(len(files),1)
            self.assertIn('HOLD',attachments.context('gsi',[meta['id']]))
            with self.assertRaises(products.ProductError):attachments.load('other',[meta['id']])
            files[0][1].write_bytes(b'altered')
            with self.assertRaises(products.ProductError):attachments.load('gsi',[meta['id']])
    def test_reject_invalid(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(attachments,'ROOT',Path(tmp)), patch.object(attachments,'_project',lambda pid:None):
            for filename in ('bad.exe','bad.zip'):
                with self.assertRaises(products.ProductError):attachments.save('gsi',filename,b'x')
            with self.assertRaises(products.ProductError):attachments.save('gsi','a.csv',b'')
            with self.assertRaises(products.ProductError):attachments.load('gsi',['../other'])
