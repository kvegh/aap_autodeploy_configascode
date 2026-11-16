"""Exercise actual action plan/CAS wiring across a native app-capture reread."""
from copy import deepcopy
import importlib.util
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest import mock
import yaml
from ansible.errors import AnsibleActionFail
from ansible.parsing.vault import VaultLib, VaultSecret
from ansible.plugins.action import ActionBase
from test_decommission_guest_access import fixture

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('tested_teardown_action',ROOT/'action_plugins/aap_aiops_teardown.py')
action=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(action)


class FrozenOwnerActionTests(unittest.TestCase):
    def test_real_plan_freezes_owner_and_recording_refuses_later_capture_and_remote_owner_drift(self):
        route=fixture()[2];selected=route['vm_name'];revision='a'*40
        owner={'tra':{'vm_name':'tra-v07','uuid':'11111111-2222-4333-8444-555555555555','machine_id':'b'*32},'event_stream_password':'synthetic'}
        variables={'awx_job_id':31,'awx_job_template_id':32,'awx_project_revision':revision,
                   'aap_aiops_teardown_apply':True,'aap_aiops_teardown_confirmation':selected,
                   'aap_isolation_app_capture':{'ansible_facts':{'aiops_instances':{selected:deepcopy(owner)}}}}
        secret=b'synthetic-native-owner-vault';vault=VaultLib([('default',VaultSecret(secret))]);pushes=[]
        remote_owner=deepcopy(owner)
        def encoded(value):return vault.encrypt(yaml.safe_dump(value,sort_keys=False))
        runtime=encoded({'schema_version':1,'instances':{selected:{}}})
        configuration={'aap_instance_api_credentials':{selected:{'token_id':99}}}
        allocation={'aap_vm_allocation':{'reservations':{'owned':{'vm_name':selected,'decommissioned':False,'instance_route':route}}}}
        bootstrap={'cac_bootstrap_git_credentials':{'aiops':{'repository_url':'https://git.example.invalid/team/aiops-selfhealing-demo-secrets.git','token':'synthetic-writer'}},
                   'cac_bootstrap_vault_credentials':{'aiops':{'vault_password':secret.decode()}}}
        def fake_git(args,**kwargs):
            folder=Path(args[2]);arguments=args[3:]
            if arguments[0]=='init':
                if folder.name=='central':
                    values={'vaults/cac/aap_autodeploy_configascode-cac-vault.yml':encoded(configuration),
                            'state/aap_vm_allocations_vault.yml':encoded(allocation),'cac/base_CaC_vault.yml':encoded(bootstrap)}
                else:
                    capture={'aiops_instances':{selected:deepcopy(remote_owner)},'aiops_playbook_vault_password':secret.decode(),
                             'aiops_runtime_settings_vault':runtime.decode()}
                    values={action.CAPTURE:encoded(capture),action.RUNTIME:runtime}
                for name,value in values.items():
                    path=folder/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
            if arguments[0]=='push':pushes.append(arguments)
            return subprocess.CompletedProcess(args,0,stdout='',stderr='')
        target=SimpleNamespace(hostname=route['aap_hostname'],request=lambda *args,**kwargs:{'id':99,'application':None})
        def invoke(operation,plan=None):
            plugin=action.ActionModule.__new__(action.ActionModule)
            args={'operation':operation,'instance_name':selected,'route':route}
            if plan is None:args['resources']={}
            else:args['plan']=plan
            plugin._task=SimpleNamespace(args=args,check_mode=False)
            plugin._loader=SimpleNamespace(_vault=vault)
            plugin._templar=SimpleNamespace(available_variables={})
            return plugin.run(task_vars=variables)
        empty={'operations':[],'selected_ids':{'aap_applications':[]},'access_tokens':[]}
        with mock.patch.object(ActionBase,'run',return_value={}),mock.patch.object(action.keys,'SourceClient',return_value=SimpleNamespace(origin='https://source.example.invalid')), \
             mock.patch.object(action.keys,'verify_source_job'),mock.patch.object(action.keys,'document',side_effect=lambda value:value),mock.patch.object(action.keys,'select_access',return_value={'hostname':route['aap_hostname'],'token':'synthetic-api'}), \
             mock.patch.object(action.contract,'autodeploy_repository',return_value='https://git.example.invalid/team/aap_autodeploy_configascode-secrets.git'),mock.patch.object(action.lifecycle,'Client',return_value=target), \
             mock.patch.object(action.helpers,'selected_target_plan',return_value=deepcopy(empty)),mock.patch.object(action.helpers,'quiesce_target',return_value={'quiescent':True}),mock.patch.object(action.subprocess,'run',side_effect=fake_git),mock.patch.dict(os.environ,{'CAC_GIT_TOKEN':'synthetic-central'}):
            planned=invoke('plan')['plan']
            self.assertEqual(planned['owner_preimage'],owner)
            remote_owner['tra']['uuid']='99999999-2222-4333-8444-555555555555'
            variables['aap_isolation_app_capture']['ansible_facts']['aiops_instances'][selected]=deepcopy(remote_owner)
            self.assertEqual(planned['owner_preimage'],owner)
            with self.assertRaisesRegex(AnsibleActionFail,'ownership changed'):
                invoke('record_target_access',planned)
            self.assertEqual(pushes,[])
