"""Verify optional selected MCP metadata without changing ordinary API authentication."""
from copy import deepcopy
import importlib.util
import subprocess
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result
keys = load('selected_mcp_keys', 'src/aap_instance_keys.py')
settings = load('selected_mcp_settings', 'src/aap_aiops_settings.py')

class SelectedMcpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='selected-mcp-ca-')
        p = Path(cls.temporary.name)
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(p/'key'),
            '-out', str(p/'ca'), '-days', '1', '-subj', '/CN=synthetic-test-ca'], check=True, capture_output=True)
        cls.ca = (p/'ca').read_text()
    @classmethod
    def tearDownClass(cls): cls.temporary.cleanup()
    def saved(self):
        return {'target':'https://aap27.v07.example.invalid','username':'admin','scope':'write',
                'id':7,'token':'synthetic-selected-token','expires':None}
    def mcp(self): return {'url':'https://192.168.70.10:8448/mcp','ca_pem':self.ca}
    def test_legacy_authentication_shape_and_token_remain_unchanged(self):
        old = keys.merge_record({}, 'aap27-test-7', self.saved())
        host = {'ansible_fqdn':'aap27.v07.example.invalid'}
        baseline = keys.select_access(keys.document(old['aap_instance_api_credentials']), 'aap27-test-7', host)
        newer = keys.merge_record(old, 'aap27-test-7', dict(self.saved(), mcp=self.mcp()))
        document = keys.document(newer['aap_instance_api_credentials'])
        self.assertEqual(keys.select_access(document,'aap27-test-7',host),baseline)
        self.assertEqual(keys.select_mcp(document,'aap27-test-7',host),self.mcp())
        self.assertIsNone(keys.select_mcp(keys.document(old['aap_instance_api_credentials']),'aap27-test-7',host))
        self.assertEqual(keys.merge_record(newer,'aap27-test-7',self.saved()),newer)
    def test_conflicting_metadata_and_invalid_authorities_are_refused(self):
        for bad in [dict(self.mcp(),url='https://203.0.113.7:8448/mcp'),dict(self.mcp(),url='https://192.168.70.10:8448/mcp#'),
                    dict(self.mcp(),ca_pem='not a certificate'),dict(self.mcp(),ca_pem=self.ca+'PRIVATE KEY')]:
            with self.subTest(bad=bad['url']), self.assertRaises(keys.StoreError): keys.mcp_connection(bad)
        old=keys.merge_record({},'aap27-test-7',dict(self.saved(),mcp=self.mcp()))
        with self.assertRaises(keys.StoreError):
            keys.merge_record(old,'aap27-test-7',dict(self.saved(),mcp=dict(self.mcp(),url='https://192.168.70.11:8448/mcp')))
    def test_only_selected_namespace_receives_selected_token_and_ca(self):
        from test_aiops_settings import fixture
        context,capture,runtime,_,_=fixture()
        runtime['instances']['aap27-test-6']={'demo_claude_vertex_auth':{'preserve':'old-account'}}
        before=deepcopy(runtime)
        auth={'hostname':context['aap_origin'],'token':self.saved()['token']}
        after,protected=settings.prepare_documents(capture,runtime,context,'Base guest Machine',
            password_factory=lambda:'x'*64,mcp_access=self.mcp(),authentication=auth)
        expected=dict(self.mcp(),instance_name=context['instance_name'],token=auth['token'])
        self.assertEqual(protected['instances'][context['instance_name']]['demo_aap_mcp'],expected)
        self.assertEqual(protected['instances']['aap27-test-6'],before['instances']['aap27-test-6'])
        self.assertEqual(runtime,before)
        self.assertNotIn('demo_claude_vertex_auth',protected['instances'][context['instance_name']])
        for changed in [dict(self.mcp(),url='https://192.168.70.11:8448/mcp')]:
            with self.assertRaises(Exception):
                settings.prepare_documents(capture,runtime,context,'Base guest Machine',password_factory=lambda:'x'*64,
                    mcp_access=changed,authentication=auth)
    def test_old_shared_pin_retirement_preserves_other_optional_records(self):
        # Execute the actual already-published consumer module, not a rewritten
        # imitation. Shared guest-release paths do not select token records.
        import types
        source=subprocess.run(['git','show','41c77d2:src/aap_instance_keys.py'],cwd=ROOT,capture_output=True,text=True,check=True).stdout
        old=types.ModuleType('old_shared_instance_keys');old.__file__=str(ROOT/'src/aap_instance_keys.py')
        exec(compile(source,old.__file__,'exec'),old.__dict__)
        document=keys.merge_record({},'aap27-test-7',dict(self.saved(),mcp=self.mcp()))
        document=keys.merge_record(document,'other',dict(self.saved(),target='https://other.example.invalid',id=8,token='other-token'))
        retired=old.retire_record(document,'other','https://other.example.invalid')
        self.assertEqual(retired['aap_instance_api_credentials']['aap27-test-7'],document['aap_instance_api_credentials']['aap27-test-7'])
        self.assertEqual(old.document(document['aap_instance_api_credentials']),keys.document(document['aap_instance_api_credentials']))
