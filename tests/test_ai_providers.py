import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from runtime import ai_providers, products

class ProviderConfigTests(unittest.TestCase):
    def setUp(self):
        # Test routing independent of CLI installations on CI runners.
        self.local_cli_probe=patch('runtime.ai_providers.shutil.which', side_effect=lambda name: 'C:/test/'+name if name in ('codex','claude','codex.cmd','claude.cmd') else None)
        self.local_cli_probe.start()
        self.addCleanup(self.local_cli_probe.stop)
        self.tmp=tempfile.TemporaryDirectory()
        self.saved_path=ai_providers.PATH
        self.saved_key=ai_providers.KEY_PATH
        ai_providers.PATH=Path(self.tmp.name)/'settings.json'
        ai_providers.KEY_PATH=Path(self.tmp.name)/'vault.json'
    def tearDown(self):
        ai_providers.PATH=self.saved_path
        ai_providers.KEY_PATH=self.saved_key
        self.tmp.cleanup()
    def test_windows_npm_cmd_shims_selected(self):
        from types import SimpleNamespace
        with patch.object(ai_providers,'os',SimpleNamespace(name='nt')):
            with patch('runtime.ai_providers.shutil.which',side_effect=lambda name: 'C:/npm/'+name if name.endswith('.cmd') else None):
                self.assertEqual(ai_providers.local_cli_path('codex-local'),'C:/npm/codex.cmd')
                self.assertEqual(ai_providers.local_cli_path('claude-local'),'C:/npm/claude.cmd')
        self.assertIsNone(ai_providers.local_cli_path('openrouter'))

    def test_initial_default_priority(self):
        self.assertEqual(ai_providers.public()['priority'][:4],['codex-local','claude-local','openai','anthropic'])
        self.assertEqual(ai_providers.public()['switchMode'],'ask')
        self.assertEqual(ai_providers.route('auto')[0],'codex-local')
    def test_reorder_and_specialist_override(self):
        ai_providers.update({'priority':['claude-local','codex-local','anthropic','openai','openrouter','vercel-gateway','together','groq'], 'switchMode':'soni','agentOverrides':{'research':'openai'},'models':{'openai':'gpt-4.1-mini'}})
        self.assertEqual(ai_providers.route('auto','research')[0],'claude-local')  # paid API override ignored
        self.assertEqual(ai_providers.route('auto','quality')[0],'claude-local')
    def test_auto_never_selects_paid_api_even_with_override(self):
        ai_providers.update({'switchMode':'soni','agentOverrides':{'soni':'openai','research':'openrouter'}})
        self.assertEqual(ai_providers.route('auto','soni')[0],'codex-local')
        self.assertEqual(ai_providers.route('auto','research')[0],'codex-local')

    def test_ask_mode_ignores_specialist_override(self):
        ai_providers.update({'switchMode':'ask','agentOverrides':{'research':'anthropic'}})
        self.assertEqual(ai_providers.route('auto','research')[0],'codex-local')
    def test_reject_duplicate_priority_and_bad_models(self):
        with self.assertRaises(products.ProductError):ai_providers.update({'priority':['codex-local']*4})
        with self.assertRaises(products.ProductError):ai_providers.update({'models':{'openai':'bad model; rm /'}})
    def test_no_credential_leak_in_read_endpoint(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':'do-not-expose-this-test-key'}):
            self.assertNotIn('do-not-expose-this-test-key',str(ai_providers.public()))
            self.assertEqual(ai_providers.key_for('openai'),'do-not-expose-this-test-key')
    def test_nonwindows_persistent_storage_is_not_plaintext(self):
        if os.name=='nt':self.skipTest('Requires Windows user encryption available')
        with self.assertRaises(products.ProductError):ai_providers.save_key('openai','secret-1234567890')
        self.assertFalse(ai_providers.KEY_PATH.exists())

if __name__=='__main__':unittest.main()

class AggregatorProviderTests(unittest.TestCase):
    def test_all_gateway_hosts_are_https_and_fixed(self):
        from runtime import ai_providers
        self.assertEqual(set(ai_providers.COMPAT_URLS), {'openrouter','vercel-gateway','together','groq'})
        self.assertTrue(all(x.startswith('https://') and x.endswith('/chat/completions') for x in ai_providers.COMPAT_URLS.values()))

    def test_existing_four_provider_priority_migrates_without_reset(self):
        from runtime import ai_providers, products
        with tempfile.TemporaryDirectory() as d:
            with patch.object(ai_providers,'PATH',Path(d)/'ai.json'):
                products.write_json(ai_providers.PATH,{'priority':['anthropic','openai','codex-local','claude-local'],'switchMode':'ask','models':{'openai':'custom-model'}})
                settings=ai_providers.public()
                self.assertEqual(settings['priority'][:4], ['anthropic','openai','codex-local','claude-local'])
                self.assertEqual(settings['models']['openai'],'custom-model')
                self.assertIn('openrouter',settings['priority'])

    def test_unconfigured_gateway_never_makes_network_request(self):
        from runtime import aibo, ai_providers
        with patch.object(ai_providers,'key_for',return_value='fake-key'):
            with patch.object(ai_providers,'public',return_value={'models':{'openrouter':''}}):
                with patch('runtime.aibo.urllib.request.urlopen') as network:
                    with self.assertRaisesRegex(aibo.AiboError,'Choose a model ID'):
                        aibo.provider_call('openrouter','system','user',None,3)
                    network.assert_not_called()

    def test_openrouter_chat_completions_adapter(self):
        from runtime import aibo, ai_providers
        from io import BytesIO
        class Response:
            def __enter__(self):return BytesIO(b'{"choices":[{"message":{"content":"Research result"}}]}')
            def __exit__(self,*args):return False
        with patch.object(ai_providers,'key_for',return_value='fake-key'):
            with patch('runtime.aibo.urllib.request.urlopen',return_value=Response()) as network:
                self.assertEqual(aibo.provider_call('openrouter','system','user','vendor/model',3),'Research result')
                req=network.call_args.args[0]
                self.assertIn('openrouter.ai',req.full_url)
                self.assertEqual(json.loads(req.data)['model'],'vendor/model')
