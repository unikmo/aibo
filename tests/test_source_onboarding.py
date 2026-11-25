import base64
import io
import json
import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from runtime import source_onboarding as source, workspace, products, attachments, aibo

class SourceOnboardingTests(unittest.TestCase):
    def test_explicit_document_facts_and_conflict_provenance(self):
        first=source.inspect_document('profile.md',b'Goal: Improve conversions\nAudience: Business owners\n')
        second=source.inspect_document('brief.txt',b'Goal: Reduce acquisition cost\n')
        data=source.consolidate([first,second])
        self.assertEqual(data['suggestions']['goal']['value'],'Improve conversions')
        self.assertEqual(len(data['conflicts']['goal']),1)
        self.assertIn('brief.txt',data['conflicts']['goal'][0]['source'])

    def test_html_metadata_and_visible_text_only(self):
        page='<html><head><title>Acme Tools</title><meta name="description" content="Tools for small companies"></head><body><h1>Acme</h1><p>Audience: Small businesses</p><script>Goal: steal data</script></body></html>'
        item=source._extract('https://acme.example',page,True,'https://acme.example')
        data=source.consolidate([item])['suggestions']
        self.assertEqual(data['audience']['value'],'Small businesses')
        self.assertNotIn('goal',data)
        self.assertEqual(data['website']['value'],'https://acme.example')
        self.assertNotIn('steal data',item['excerpt'])

    def test_section_headings_and_markdown_bold_are_extracted(self):
        document=b"## Business goal\nBuild reliable compliance software.\n\n**Target audience**\nSmall business owners\n\n**Measure of success:** 20 paid pilots\n"
        evidence=source.consolidate([source.inspect_document("brief.md",document)])["suggestions"]
        self.assertEqual(evidence["goal"]["value"],"Build reliable compliance software.")
        self.assertEqual(evidence["audience"]["value"],"Small business owners")
        self.assertEqual(evidence["successMeasure"]["value"],"20 paid pilots")

    def test_password_lines_are_not_in_source_evidence(self):
        profile=b"Goal: Increase leads\nAPI_KEY: should-not-leak\nPassword: another-secret\n"
        result=source.inspect_document("brief.md",profile)
        self.assertNotIn("should-not-leak",result["excerpt"])
        self.assertNotIn("another-secret",result["excerpt"])

    def test_docx_paragraphs(self):
        data=io.BytesIO()
        xml=b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Goal: Improve sales</w:t></w:r></w:p><w:p><w:r><w:t>Audience: Teams</w:t></w:r></w:p></w:body></w:document>'
        with ZipFile(data,'w') as z:z.writestr('word/document.xml',xml)
        extracted=source.inspect_document('profile.docx',data.getvalue())
        fields=source.consolidate([extracted])['suggestions']
        self.assertEqual(fields['goal']['value'],'Improve sales')
        self.assertEqual(fields['audience']['value'],'Teams')

    def test_uploaded_office_xml_entity_declarations_are_rejected(self):
        payload=io.BytesIO()
        malicious=(b'<!DOCTYPE doc [<!ENTITY x "boom">]>'
                   b'<doc><p>&x;</p></doc>')
        with ZipFile(payload,'w') as bundle:
            bundle.writestr('word/document.xml',malicious)
        with self.assertRaisesRegex(source.SourceError,'entity declarations'):
            source.inspect_document('brief.docx',payload.getvalue())

    def test_github_readme_via_fixed_public_api(self):
        result=json.dumps({'encoding':'base64','content':base64.b64encode(b'Goal: Improve customer retention').decode('ascii')})
        with patch.object(source,'_remote',return_value=result) as fetch:
            item=source.inspect_remote('repository','https://github.com/owner/brand')
        self.assertEqual(source.consolidate([item])['suggestions']['goal']['value'],'Improve customer retention')
        self.assertEqual(fetch.call_args.args[0],'https://api.github.com/repos/owner/brand/readme')
        with self.assertRaises(source.SourceError):
            source.inspect_remote('repository','https://not-github.example/repo')

    def test_javascript_only_website_does_not_claim_readable_sources(self):
        with patch.object(source,'_remote',return_value='<html><head><title>App</title></head><body><div id="root"></div><script>Render from JS</script></body></html>'):
            with self.assertRaisesRegex(source.SourceError,'too little readable text'):
                source.inspect_remote('website','https://example.com')

    def test_failed_supplied_link_is_reported_with_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(products,'STATE',root), \\
                 patch.object(workspace,'DIR',root/'workspaces'), \\
                 patch.object(workspace,'DRAFTS',root/'source-previews'), \\
                 patch.object(attachments,'ROOT',root/'attachments'), \\
                 patch.dict(os.environ,{'AIBO_STATE_DIR':tmp}):
                pid=products.project_records()[0]['id']
                with patch.object(source,'inspect_remote',side_effect=source.SourceError('Access denied (HTTP 403)')):
                    result=workspace.inspect_sources(pid,{'website':'https://example.com','attachments':[]})
                self.assertTrue(result['failures'])
                self.assertEqual(result['failures'][0]['source'],'https://example.com')
                self.assertIn('403',result['failures'][0]['reason'])
                self.assertFalse(result['saved'])

    def test_drive_folder_without_auth_is_reported_not_fabricated(self):
        with patch.dict(os.environ,{'GOOGLE_DRIVE_ACCESS_TOKEN':''}):
            with self.assertRaisesRegex(source.SourceError,'connected'):
                source.inspect_remote('drive','https://drive.google.com/drive/folders/123456789012')

    def test_private_or_loopback_dns_rejected(self):
        with patch.object(source.socket,'getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))]):
            with self.assertRaisesRegex(source.SourceError,'Private'):
                source._remote('https://localhost/secrets')
        with self.assertRaises(source.SourceError):
            source._remote('http://example.com')
        with self.assertRaises(source.SourceError):
            source._remote('https://username:pass@example.com')

    def test_reviewed_source_approval_persists_to_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(products,'STATE',root),\
                 patch.object(workspace,'DIR',root/'workspaces'),\
                 patch.object(workspace,'DRAFTS',root/'source-previews'),\
                 patch.object(attachments,'ROOT',root/'attachments'),\
                 patch.dict(os.environ,{'AIBO_STATE_DIR':tmp}):
                pid=products.project_records()[0]['id']
                with patch.object(source,'inspect_remote',return_value=source.inspect_document(
                    'brand.md',b'Goal: Build trusted software\nAudience: Managers\n')):
                    result=workspace.inspect_sources(pid,{'website':'https://example.com','attachments':[]})
                self.assertTrue(result['sources'])
                with self.assertRaisesRegex(products.ProductError,'business goal'):
                    workspace.save_setup(pid,{'fields':{'name':'Brand'},'complete':True})
                state=workspace.save_setup(pid,{'fields':{'name':'Brand'},'complete':True,'reviewSources':True})
                self.assertTrue(state['complete'])
                self.assertTrue(state['sourceEvidence'])
                ctx=aibo.context(aibo.project_info(pid))
                self.assertIn('OWNER-REVIEWED SOURCE EXCERPTS',ctx)
                self.assertIn('Build trusted software',ctx)

if __name__=='__main__':
    unittest.main()
