"""Prove bounded installer/own-API access before the vendor installation phase."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.vault import VaultLib, VaultSecret
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.plugins.action import ActionBase

from test_aap_hypervisor_access import fixture, access
from test_instance_keys import FakeRetirementSource, keys, load, vault_yaml, retirement_fixture


class InstallationAccessTests(unittest.TestCase):
    def test_installer_and_own_api_https_are_added_before_base_ssh_without_other_grants(self):
        expected, probe, *_ = fixture()
        before = deepcopy(expected['declared_policy'])
        identity = {key: expected['primary'][field] for key, field in (
            ('bridge', 'bridge'), ('ipv4', 'address'), ('mac', 'mac'))}
        before['https_clients'] = [row for row in before['https_clients'] if row != identity]
        expected.update(mode='installation', declared_policy=before)
        probe['policy'] = deepcopy(before)
        result = access.plan(expected, probe)
        self.assertEqual(result['desired_policy']['https_clients'], before['https_clients'] + [identity])
        self.assertEqual(result['client']['ports'], [443])
        self.assertEqual(result['client']['destinations'], [expected['route']['hypervisor']['public_ip']])
        self.assertEqual(result['desired_policy']['protected_ipv4'], before['protected_ipv4'])
        self.assertEqual(result['desired_policy'].get('released_clients'), before.get('released_clients'))
        managed = access.desired_policy(expected['route'], expected['primary'], result['desired_policy'])
        client = next(row for row in managed['guest_host_clients'] if row['ipv4'] == identity['ipv4'])
        self.assertEqual(client['ports'], [443, expected['route']['hypervisor']['port']])
        self.assertEqual(access.desired_policy(expected['route'], expected['primary'], managed, 'installation'), managed)
        mixed = deepcopy(expected['route'])
        mixed['hypervisor']['public_ip'] = '192.0.2.55'
        with self.assertRaises(ValueError):
            access.desired_policy(mixed, expected['primary'], managed, 'installation')

    def test_installation_context_uses_consumed_exact_aap_only_ownership(self):
        expected, _, main, shared, _, allocation = fixture()
        context = keys.installation_access_context(main, shared, allocation, expected['route'], expected['primary'])
        self.assertEqual(context['access_mode'], 'installation')
        self.assertEqual(context['desired_policy']['protected_ipv4'], context['previous_policy']['protected_ipv4'])
        for changes in ({'uuid': 'foreign'}, {'verified': False}, {'address': '192.168.70.99'}):
            with self.subTest(changes=changes), self.assertRaises(keys.StoreError):
                keys.installation_access_context(main, shared, allocation, expected['route'],
                                                dict(expected['primary'], **changes))
        retired = deepcopy(allocation)
        retired['aap_vm_allocation']['reservations']['selected-request']['decommissioned'] = True
        with self.assertRaises(keys.StoreError):
            keys.installation_access_context(main, shared, retired, expected['route'], expected['primary'])

    def test_runtime_installation_rollback_restores_only_new_rules_and_old_policy(self):
        expected, observed, *_ = fixture()
        expected['mode']='installation'
        with tempfile.TemporaryDirectory(prefix='installation-native-rollback-')as temporary:
            directory=Path(temporary);config=directory/'policy.json';helper=directory/'helper'
            original=json.dumps(expected['declared_policy']).encode();config.write_bytes(original)
            helper.write_text("TABLE='hactar_recovery'\ndef validate_configuration(value):return value\ndef policy(value):return []\n")
            states=set();writes=[]
            def command(arguments,data=None,allowed=(0,)):
                if arguments[0]=='firewall-cmd':
                    permanent='--permanent'in arguments
                    action=next(value for value in arguments if value.startswith(('--query-rich-rule=','--add-rich-rule=','--remove-rich-rule=')))
                    if action.startswith('--query'):return SimpleNamespace(returncode=0 if permanent in states else 1,stdout='')
                    writes.append(arguments)
                    if action.startswith('--add'):states.add(permanent)
                    else:states.discard(permanent)
                return SimpleNamespace(returncode=0,stdout='')
            def probe(route):
                result=deepcopy(observed);result['policy']=json.loads(config.read_text());return result
            with mock.patch.multiple(access,DIRECTORY=directory,CONFIG=config,HELPER=helper), \
                 mock.patch.object(access,'probe',side_effect=probe),mock.patch.object(access,'command',side_effect=command):
                applied=access.reconcile(expected)
                self.assertEqual(states,{False,True});self.assertTrue(applied['changed'])
                rollback=dict(expected,operation='rollback',native_rule_previous=applied['native_rule_previous'])
                restored=access.reconcile(rollback)
                self.assertTrue(restored['changed']);self.assertEqual(states,set());self.assertEqual(config.read_bytes(),original)
            self.assertTrue(all('--zone=libvirt'in args for args in writes))

    def test_undeployed_optional_hactar_alias_requires_proved_admin_visibility(self):
        expected, _, main, shared, hactar, allocation=fixture()
        context=keys.installation_access_context(main,shared,allocation,expected['route'],expected['primary'])
        desired_main=keys.installation_inventory_capture(main,context,'autodeploy')
        desired_shared=keys.installation_inventory_capture(shared,context,'shared')
        desired_hactar=keys.installation_inventory_capture(hactar,context,'hactar')
        class Client(FakeRetirementSource):
            admin=True
            def rows(self,path):
                if path=='me/':return [{'is_superuser':self.admin}]
                return super().rows(path)
        client=Client(main,shared,hactar)
        del client.inventories[2]
        operations=keys.source_management_operations(client,desired_shared,desired_main,desired_hactar,context)
        self.assertTrue(operations);self.assertEqual(client.calls,[])
        for admin in (False,None,'true'):
            with self.subTest(admin=admin),self.assertRaises(keys.StoreError):
                client.admin=admin
                keys.source_management_operations(client,desired_shared,desired_main,desired_hactar,context)
        client.admin=True
        del client.inventories[3]
        with self.assertRaises(keys.StoreError):
            keys.source_management_operations(client,desired_shared,desired_main,desired_hactar,context)
        present=Client(main,shared,hactar)
        row=next(row for row in present.hosts.values()if row['inventory']==2)
        values=json.loads(row['variables']);values['machine_id']='9'*32;row['variables']=json.dumps(values)
        with self.assertRaises(keys.StoreError):
            keys.source_management_operations(present,desired_shared,desired_main,desired_hactar,context)
        self.assertEqual(present.calls,[])

    def test_canonical_display_alias_is_preserved_by_registration_and_decommission(self):
        expected, _, main, shared, hactar, allocation = fixture()
        physical = expected['route']['vm_name']
        row = next(row for row in shared['host_inventory_configuration']['hosts'] if row['name'] == physical)
        row['name'] = 'aap27-v07'
        values = keys.inventory_variables(row)
        values['vm_resource'] = dict(expected['primary'], vm_name=physical)
        keys.set_inventory_variables(row, values)
        for group in shared['host_inventory_configuration']['groups']:
            group['hosts'] = ['aap27-v07' if name == physical else name for name in group.get('hosts', [])]
        changed = keys.merge_inventory(shared, physical, expected['route'], expected['declared_policy'], expected['primary'])
        owned = [row for row in changed['host_inventory_configuration']['hosts'] if keys.aap_inventory_owner(row, physical)]
        self.assertEqual([row['name'] for row in owned], ['aap27-v07'])
        self.assertNotIn(physical, [row['name'] for row in changed['host_inventory_configuration']['hosts']])
        empty = deepcopy(shared)
        empty['host_inventory_configuration']['hosts'] = [row for row in empty['host_inventory_configuration']['hosts']
                                                       if not keys.aap_inventory_owner(row, physical)]
        created = keys.merge_inventory(empty, physical, expected['route'], expected['declared_policy'], expected['primary'])
        self.assertEqual([row['name'] for row in created['host_inventory_configuration']['hosts']
                          if keys.aap_inventory_owner(row, physical)], ['aap27-v07'])

    def test_alias_source_ownership_and_retirement_use_physical_provenance_without_recreating_old_row(self):
        context, transition, main, shared, hactar, allocation = retirement_fixture()
        physical=context['route']['vm_name'];alias='aap27-v07'
        row=next(row for row in shared['host_inventory_configuration']['hosts']
                 if row['inventory']=='Shared' and row['name']==physical)
        row['name']=alias
        values=keys.inventory_variables(row)
        values['vm_resource']=dict(allocation['aap_vm_allocation']['reservations']['selected-request']['instance_resources']['aap'],vm_name=physical)
        keys.set_inventory_variables(row,values)
        for group in shared['host_inventory_configuration']['groups']:
            if group['inventory']=='Shared':group['hosts']=[alias if name==physical else name for name in group['hosts']]
        client=FakeRetirementSource(main,shared,hactar)
        proof=keys.source_related_resources(client,shared,allocation['aap_vm_allocation'],physical)
        self.assertEqual(set(proof['related_resources']),{'zabbix','testserver1','tra'})
        retired=keys.retire_inventory_capture(shared,context,'shared')
        self.assertNotIn(alias,[row['name']for row in retired['host_inventory_configuration']['hosts']if row['inventory']=='Shared'])
        self.assertNotIn(alias,retired['host_inventory_configuration']['groups'][0]['hosts'])
        operations=keys.source_retirement_operations(client,retired,
            keys.retire_inventory_capture(main,context,'autodeploy'),keys.retire_inventory_capture(hactar,context,'hactar'),context)
        alias_id=next(row['id']for row in client.hosts.values()if row['inventory']==1 and row['name']==alias)
        self.assertIn(('DELETE','hosts/%s/'%alias_id,None),operations)
        self.assertEqual(client.calls,[],'All ownership and API destinations are preflighted read-only.')

    def test_native_base_repair_runs_only_access_with_pinned_delegation_and_cleans_trust(self):
        expected, _, *_ = fixture()
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='native-installation-repair-') as temporary:
            directory=Path(temporary);plugins=directory/'action_plugins';plugins.mkdir()
            trace=directory/'trace.jsonl'
            plugin='''import json
from pathlib import Path
from ansible.plugins.action import ActionBase
TRACE=Path(TRACEPATH)
class ActionModule(ActionBase):
 def run(self,tmp=None,task_vars=None):
  phase=self._task.args['phase']
  with TRACE.open('a') as output:output.write(json.dumps({'phase':phase})+'\\n')
  return {'changed':False,'published':phase=='publish','transition':task_vars['fixture_transition']}
'''.replace('TRACEPATH',repr(str(trace)))
            (plugins/'aap_publish_instance_keys.py').write_text(plugin)
            (plugins/'aap_read_instance.py').write_text('''from ansible.plugins.action import ActionBase
class ActionModule(ActionBase):
 def run(self,tmp=None,task_vars=None):
  return {'changed':False,'instance_route':task_vars['fixture_route'],'instance_resources':{'aap':task_vars['fixture_primary']}}
''')
            (plugins/'installation_transport_proof.py').write_text('''import json
from pathlib import Path
from ansible.plugins.action import ActionBase
class ActionModule(ActionBase):
 def run(self,tmp=None,task_vars=None):
  original=task_vars['hostvars'][task_vars['inventory_hostname']]
  pin=original['aap_instance_route']['hypervisor'];connection=self._play_context
  assert connection.remote_addr==pin['address'] and connection.remote_user==pin['user'] and connection.port==pin['port']
  assert 'StrictHostKeyChecking=yes' in self._connection.get_option('ssh_common_args')
  assert 'ProxyCommand' not in self._connection.get_option('ssh_common_args')
  request=json.loads(self._task.args['stdin']);assert request['mode']=='installation' and not request['check_mode']
  with Path(TRACEPATH).open('a')as output:output.write(json.dumps({'transport':True,'trust':original['aap_instance_trust']['path']})+'\\n')
  return {'changed':False,'rc':0,'stdout':json.dumps({'changed':False,'applied':True,'native_rule_previous':{'runtime':False,'permanent':False}})}
'''.replace('TRACEPATH',repr(str(trace))))
            child=yaml.safe_load((root/'tasks/aap-installation-access.yml').read_text())
            for block in child:
                for task in block.get('block',[])+block.get('rescue',[]):
                    if 'ansible.builtin.command' in task:
                        task['installation_transport_proof']=task.pop('ansible.builtin.command')
                        task['installation_transport_proof']['argv'][2]='synthetic-code-not-executed'
            child_path=directory/'installation.yml';child_path.write_text(yaml.safe_dump(child,sort_keys=False))
            play=yaml.safe_load((root/'04-aap-config.yml').read_text())[0]
            pre=deepcopy(play['pre_tasks'][:2])
            for task in pre[0]['block']:
                if 'ansible.builtin.include_tasks' in task:
                    target=task['ansible.builtin.include_tasks']['file']
                    task['ansible.builtin.include_tasks']['file']=str(child_path if target.endswith('aap-installation-access.yml')else root/target)
            transition={'previous_policy':expected['declared_policy'],
                        'desired_policy':access.desired_policy(expected['route'],expected['primary'],expected['declared_policy'],'installation')}
            variables={'aap_instance_key':expected['route']['vm_name'],'fixture_route':expected['route'],
                       'fixture_primary':expected['primary'],'fixture_transition':transition}
            fixture_play=directory/'play.yml'
            fixture_play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,
                'vars':variables,'pre_tasks':pre,'tasks':[{'name':'Forbidden ordinary base stage',
                'ansible.builtin.fail':{'msg':'Ordinary base configuration must not execute'}}],
                'post_tasks':[{'name':'Forbidden final AAP release after bounded repair','tags':['always'],
                'ansible.builtin.fail':{'msg':'Repair must end before any final release'}}]}],sort_keys=False))
            env=dict(os.environ,ANSIBLE_ACTION_PLUGINS=str(plugins),ANSIBLE_FILTER_PLUGINS=str(root/'filter_plugins'),
                     ANSIBLE_LOCAL_TEMP=str(directory/'local'),ANSIBLE_REMOTE_TEMP=str(directory/'remote'),ANSIBLE_NOCOLOR='1')
            for native in (False,True):
                env['ANSIBLE_JINJA2_NATIVE']=str(native).lower()
                trace.unlink(missing_ok=True)
                result=subprocess.run([sys.executable,'-m','ansible.cli.playbook','-i','localhost,',str(fixture_play),
                    '--tags','aap_installation_access'],env=env,cwd=root,text=True,capture_output=True,timeout=45)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertNotIn('TASK [Forbidden ordinary base stage]',result.stdout)
                self.assertNotIn('TASK [Forbidden final AAP release',result.stdout)
                rows=[json.loads(line)for line in trace.read_text().splitlines()]
                self.assertEqual([row['phase']for row in rows if 'phase'in row],['plan','publish'])
                remote=next(row for row in rows if row.get('transport'));self.assertFalse(Path(remote['trust']).exists())

    def test_real_encrypted_git_bootstrap_plan_publish_retry_and_idempotence_preserve_tokens_and_allocator(self):
        module = load('installation_publication_action', 'action_plugins/aap_publish_instance_keys.py')
        expected, _, main, shared, hactar, allocation = fixture()
        class Client(FakeRetirementSource):
            def rows(self, path):
                if path.startswith('groups/?'):
                    return [{'id':77,'name':'guests','inventory':1,'variables':json.dumps({'hypervisor_host':'fixture-hypervisor'})}]
                if path == 'groups/77/hosts/':
                    return [{'id':row['id']} for row in self.hosts.values() if row['inventory']==1]
                return super().rows(path)
        client = Client(main, shared, hactar)
        secret, env_secret = VaultSecret(b'synthetic-cac'), VaultSecret(b'synthetic-environment')
        vault = VaultLib([('cac',secret),('default',env_secret)])
        documents = {'vaults/cac/aap_autodeploy_configascode-cac-vault.yml':main,'cac/host_inventory.yml':shared,
                     'cac/hactar_recovery.yml':hactar,'state/aap_vm_allocations_vault.yml':allocation}
        real_run = subprocess.run
        with tempfile.TemporaryDirectory(prefix='installation-encrypted-cas-') as temporary:
            directory=Path(temporary);remote=directory/'remote.git';seed=directory/'seed';project=directory/'project'
            seed.mkdir();project.mkdir()
            def git(path,*args):return real_run(['git','-C',str(path),*args],text=True,capture_output=True,check=True)
            real_run(['git','init','--bare','--initial-branch=main',str(remote)],capture_output=True,check=True)
            git(seed,'init','--initial-branch=main')
            for relative,value in documents.items():
                path=seed/relative;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(vault.encrypt(yaml.dump(value,Dumper=vault_yaml.VaultDumper),vault_id='cac'))
            git(seed,'add','.')
            git(seed,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','Initialize')
            git(seed,'remote','add','origin',str(remote));git(seed,'push','origin','main')
            (project/'myvars').write_bytes(vault.encrypt(yaml.safe_dump({'git_url':'https://git.example.invalid/fixture-owner/autodeploy.git'}),vault_id='default'))
            loader=DataLoader();loader.set_vault_secrets([('cac',secret),('default',env_secret)])
            def redirected(command,*args,**kwargs):
                replaced=[str(remote) if value=='https://git.example.invalid/fixture-owner/aap_autodeploy_configascode-secrets.git' else value for value in command]
                self.assertFalse(any(value.startswith(('https://','http://','git@')) for value in replaced))
                return real_run(replaced,*args,**kwargs)
            def run(phase,transition=None):
                plugin=module.ActionModule.__new__(module.ActionModule)
                args={'operation':'installation_access','phase':phase,'route':expected['route'],'primary':expected['primary']}
                if transition is not None:args['transition']=transition
                plugin._task=SimpleNamespace(args=args,check_mode=False);plugin._loader=loader
                return plugin.run(task_vars={'awx_job_id':123,'awx_job_template_id':456,'awx_project_revision':'a'*40})
            with mock.patch.object(ActionBase,'run',return_value={}),mock.patch.object(module,'ROOT',project), \
                 mock.patch.object(module,'SourceClient',return_value=client),mock.patch.object(module.subprocess,'run',side_effect=redirected), \
                 mock.patch.dict(os.environ,{'CAC_GIT_TOKEN':'synthetic-writer'}):
                planned=run('plan');self.assertNotIn('failed',planned,planned)
                self.assertFalse(planned['published']);self.assertEqual(client.calls,[])
                transition=planned['transition']
                original_request=client.request
                def fail_source(method,path,body=None):
                    if method=='PATCH'and path.startswith('inventories/'):
                        raise keys.StoreError('Synthetic source interruption')
                    return original_request(method,path,body)
                with mock.patch.object(client,'request',side_effect=fail_source):
                    failure=run('publish',transition)
                self.assertTrue(failure['failed']);self.assertTrue(failure['durable_policy_published'])
                success=run('publish',transition);self.assertTrue(success['published'],success)
                self.assertFalse(run('publish',transition)['changed'])
            restored={relative:AnsibleLoader(vault.decrypt(git(remote,'show','main:'+relative).stdout.encode())).get_single_data()
                      for relative in documents}
            self.assertEqual(restored['state/aap_vm_allocations_vault.yml'],allocation)
            self.assertEqual(restored['vaults/cac/aap_autodeploy_configascode-cac-vault.yml']['aap_instance_api_credentials'],main['aap_instance_api_credentials'])
            self.assertFalse(any(method=='DELETE' for method,path in client.calls))


if __name__=='__main__':unittest.main()
