"""Read settings from the current native plugin checkout after an earlier checkout is removed."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml
from ansible.parsing.vault import VaultLib, VaultSecret

ROOT = Path(__file__).resolve().parents[1]
MARKER = 'Fixture stopped at protected Git fetch; no network request.'


class ActionPluginCheckoutLifetimeTests(unittest.TestCase):
    def test_native_repeated_inclusion_reads_current_encrypted_settings_after_original_root_is_deleted(self):
        for native in ('true', 'false'):
            for operation in ('guest_bootstrap_https', 'publish'):
                with self.subTest(native=native, operation=operation):
                    self.run_native(native, operation)

    def run_native(self, native, operation):
        with tempfile.TemporaryDirectory(prefix='publisher-native-lifetime-') as temporary:
            root = Path(temporary)
            sources = [root/'first'/'source', root/'second'/'source']
            trace = root/'git-boundary.jsonl'
            password = root/'fixture-password'
            password.write_text('synthetic-fixture-key\n')
            password.chmod(0o600)
            vault = VaultLib([('default', VaultSecret(b'synthetic-fixture-key'))])
            for index, source in enumerate(sources):
                for directory in ('action_plugins', 'src', 'filter_plugins'):
                    shutil.copytree(ROOT/directory, source/directory, ignore=shutil.ignore_patterns('__pycache__'))
                (source/'myvars').write_bytes(vault.encrypt(yaml.safe_dump({
                    'vault_cac_repository_namespace':'https://github.com/fixture'+str(index)})))
                plugin = source/'action_plugins/aap_publish_instance_keys.py'
                with plugin.open('a') as stream:
                    stream.write('\n# Local fixture transports only; production guards and settings loader remain real.\n'
                        'from types import SimpleNamespace\n'
                        'class FixtureSourceClient:\n'
                        '    origin = "https://source.example.invalid"\n'
                        '    def request(self, method, path, body=None):\n'
                        '        assert method == "GET" and path == "jobs/41/" and body is None\n'
                        '        return {"status":"running", "job_template":23, "scm_revision":"'+'a'*40+'"}\n'
                        'SourceClient = FixtureSourceClient\n'
                        '_fixture_original_run = ActionModule.run\n'
                        'def fixture_action_run(self, tmp=None, task_vars=None):\n'
                        '    global _fixture_current_action\n'
                        '    _fixture_current_action = self\n'
                        '    try:\n'
                        '        return _fixture_original_run(self, tmp, task_vars)\n'
                        '    except AnsibleActionFail as error:\n'
                        '        return {"failed":True,"changed":False,"msg":str(error)}\n'
                        'ActionModule.run = fixture_action_run\n'
                        'def fixture_git_run(command, **kwargs):\n'
                        '    assert command[0] == "git"\n'
                        '    if command[3:6] == ["remote", "add", "origin"]:\n'
                        '        record = {"repository":command[6], "cached_root":str(ROOT),\n'
                        '                  "cached_root_exists":ROOT.exists(),\n'
                        '                  "native_plugin_path":_fixture_current_action._original_path}\n'
                        '        with Path('+repr(str(trace))+').open("a") as output:\n'
                        '            output.write(json.dumps(record)+"\\n")\n'
                        '    if command[3] == "fetch":\n'
                        '        raise keys.StoreError('+repr(MARKER)+')\n'
                        '    return SimpleNamespace(returncode=0, stdout="", stderr="")\n'
                        'subprocess = SimpleNamespace(run=fixture_git_run)\n')
                role = source/'roles'/'fixture_publisher'
                (role/'tasks').mkdir(parents=True)
                (role/'action_plugins').mkdir()
                (role/'action_plugins/aap_publish_instance_keys.py').symlink_to('../../../action_plugins/aap_publish_instance_keys.py')
                args = ({'operation':operation,'phase':'plan','guest':{},'hypervisor':{}}
                        if operation!='publish' else {'operation':'publish','instance_name':'example-v01',
                                                     'record':{'target':'https://target.example.invalid'},'organization':1})
                (role/'tasks/main.yml').write_text(yaml.safe_dump([
                    {'name':'Reach the current encrypted settings through the real publisher',
                     'aap_publish_instance_keys':args,'register':'observed',
                     'failed_when':'observed.msg != '+repr(MARKER)}],sort_keys=False))
            play = root/'fixture.yml'
            play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,
                'vars':{'awx_job_id':41,'awx_job_template_id':23,'awx_project_revision':'a'*40},'tasks':[
                    {'name':'First native publisher inclusion','ansible.builtin.include_role':{'name':str(sources[0]/'roles/fixture_publisher')}},
                    {'name':'Remove the first invocation checkout',
                     'ansible.builtin.file':{'path':str(sources[0].parent),'state':'absent'}},
                    {'name':'Second native publisher inclusion','ansible.builtin.include_role':{'name':str(sources[1]/'roles/fixture_publisher')}}]}],sort_keys=False))
            env=dict(os.environ,ANSIBLE_HOME=str(root/'home'),ANSIBLE_LOCAL_TEMP=str(root/'local'),
                     ANSIBLE_REMOTE_TEMP=str(root/'remote'),ANSIBLE_JINJA2_NATIVE=native,
                     ANSIBLE_NOCOLOR='1',CAC_GIT_TOKEN='synthetic-no-network-fixture')
            result=subprocess.run([sys.executable,'-m','ansible.cli.playbook','-i','localhost,',
                                   '--vault-password-file',str(password),str(play)],cwd=ROOT,env=env,
                                  text=True,capture_output=True,timeout=45)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            rows=[json.loads(line)for line in trace.read_text().splitlines()]
            self.assertEqual([row['repository']for row in rows],[
                'https://github.com/fixture0/aap_autodeploy_configascode-secrets.git',
                'https://github.com/fixture1/aap_autodeploy_configascode-secrets.git'])
            self.assertTrue(rows[0]['cached_root_exists'])
            self.assertFalse(rows[1]['cached_root_exists'])
            self.assertEqual(rows[0]['cached_root'],rows[1]['cached_root'])
            self.assertEqual(Path(rows[1]['native_plugin_path']).resolve(),
                             sources[1]/'action_plugins/aap_publish_instance_keys.py')
            self.assertFalse(sources[0].exists())

    def test_missing_or_invalid_native_plugin_path_refuses_without_a_cached_root_fallback(self):
        spec=importlib.util.spec_from_file_location('publisher_lifetime_unit',ROOT/'action_plugins/aap_publish_instance_keys.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        action=module.ActionModule.__new__(module.ActionModule)
        for invalid in (None,'','relative/action_plugins/aap_publish_instance_keys.py',
                        '/tmp/nonexistent-publisher-source/action_plugins/aap_publish_instance_keys.py',str(ROOT/'myvars')):
            with self.subTest(path=invalid),self.assertRaises((module.keys.StoreError,OSError)):
                if invalid is None:action.__dict__.pop('_original_path',None)
                else:action._original_path=invalid
                action._project_root()
        action._original_path=str(ROOT/'roles/recovery_guest_release/action_plugins/aap_publish_instance_keys.py')
        self.assertEqual(action._project_root(),ROOT)


if __name__=='__main__':unittest.main()
