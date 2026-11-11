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
from test_instance_keys import FakeRetirementSource, keys, load, vault_yaml, retirement_fixture, application_capture


class InstallationAccessTests(unittest.TestCase):
    @staticmethod
    def set_declared_policy(configuration, policy):
        row = configuration['autodeploy_configuration']['inventories'][0]
        values = keys.inventory_variables(row)
        for field, name in (
                ('aap_hypervisor_isolation_https_clients', 'https_clients'),
                ('aap_hypervisor_isolation_protected_ipv4', 'protected_ipv4'),
                ('aap_hypervisor_isolation_host_clients', 'guest_host_clients'),
                ('aap_hypervisor_isolation_released_clients', 'released_clients'),
                ('aap_hypervisor_isolation_http_clients', 'http_clients')):
            values[field] = deepcopy(policy.get(name, []))
        for alias in ('isolation_policy', 'hactar_isolation_policy'):
            if alias in values:
                values[alias] = deepcopy(policy)
        keys.set_inventory_variables(row, values)

    def first_installation_fixture(self):
        expected, probe, main, shared, hactar, allocation = fixture()
        previous = {field: deepcopy(expected['declared_policy'][field])
                    for field in ('bridges', 'dns_bridges')}
        main['aap_autodeploy_source_public_ip'] = '203.0.113.10'
        self.set_declared_policy(main, previous)
        return expected, main, shared, allocation, previous

    def test_first_installation_derives_canonical_protection_without_changing_previous_policy(self):
        expected, main, shared, allocation, previous = self.first_installation_fixture()
        original = deepcopy((main, shared, allocation))
        context = keys.installation_access_context(main, shared, allocation,
                                                  expected['route'], expected['primary'])
        declared = dict(previous, protected_ipv4=[main['aap_autodeploy_source_public_ip']])
        desired = access.desired_policy(expected['route'], expected['primary'], declared, 'installation')
        self.assertEqual(context['previous_policy'], previous)
        self.assertEqual(context['desired_policy'], desired)
        self.assertEqual(context['desired_policy']['https_clients'], [{
            'bridge': expected['primary']['bridge'], 'ipv4': expected['primary']['address'],
            'mac': expected['primary']['mac']}])
        self.assertEqual((main, shared, allocation), original)
        transition = {field: deepcopy(context[field]) for field in ('previous_policy', 'desired_policy')}
        for published in (False, True):
            with self.subTest(published=published):
                current = deepcopy(main)
                if published:
                    self.set_declared_policy(current, desired)
                retry = keys.installation_access_context(current, shared, allocation,
                    expected['route'], expected['primary'], transition)
                self.assertEqual(retry['previous_policy'], previous)
                self.assertEqual(retry['desired_policy'], desired)

    def test_first_installation_refuses_missing_invalid_or_target_source_address(self):
        expected, main, shared, allocation, previous = self.first_installation_fixture()
        plan = keys.installation_access_context(main, shared, allocation,
                                               expected['route'], expected['primary'])
        transition = {field: deepcopy(plan[field]) for field in ('previous_policy', 'desired_policy')}
        pin = expected['route']['hypervisor']
        invalid = (None, '', False, 42, 'not-an-ip', '203.0.113.010', '0.0.0.0',
                   '127.0.0.1', '169.254.1.1', '224.0.0.1', '255.255.255.255',
                   pin['address'], pin['public_ip'], expected['route']['vm_ip'])
        for source in invalid:
            for published in (False, True):
                with self.subTest(source=source, published=published):
                    current = deepcopy(main)
                    if published:
                        self.set_declared_policy(current, plan['desired_policy'])
                    if source is None:
                        current.pop('aap_autodeploy_source_public_ip')
                    else:
                        current['aap_autodeploy_source_public_ip'] = source
                    with self.assertRaisesRegex(keys.StoreError, 'distinct canonical source'):
                        keys.installation_access_context(current, shared, allocation,
                            expected['route'], expected['primary'], transition if published else None)
        changed = deepcopy(main)
        changed['aap_autodeploy_source_public_ip'] = '203.0.113.11'
        with self.assertRaises(keys.StoreError):
            keys.installation_access_context(changed, shared, allocation,
                expected['route'], expected['primary'], transition)

    def test_first_installation_preserves_existing_local_guests_and_management_stays_strict(self):
        expected, main, shared, allocation, previous = self.first_installation_fixture()
        local = deepcopy(expected['declared_policy']['guest_host_clients'])
        self.assertTrue(local)
        previous['guest_host_clients'] = local
        self.set_declared_policy(main, previous)
        context = keys.installation_access_context(main, shared, allocation,
                                                  expected['route'], expected['primary'])
        self.assertEqual(context['previous_policy'], previous)
        self.assertEqual(context['desired_policy']['guest_host_clients'][:len(local)], local)
        self.assertNotIn('released_clients', context['desired_policy'])
        record = allocation['aap_vm_allocation']['reservations']['selected-request']
        with self.assertRaises(keys.StoreError):
            keys.management_access_context(main, record, expected['route']['vm_name'],
                                           expected['route'], None)
        with self.assertRaises(ValueError):
            access.desired_policy(expected['route'], expected['primary'], previous, 'installation')

    def test_existing_protected_installation_policy_is_preserved(self):
        expected, _, main, shared, _, allocation = fixture()
        original = deepcopy((main, shared, allocation))
        main['aap_autodeploy_source_public_ip'] = '203.0.113.10'
        context = keys.installation_access_context(main, shared, allocation,
                                                  expected['route'], expected['primary'])
        self.assertEqual(context['previous_policy'], expected['declared_policy'])
        self.assertEqual(context['desired_policy']['protected_ipv4'],
                         expected['declared_policy']['protected_ipv4'])
        self.assertEqual(shared, original[1])
        self.assertEqual(allocation, original[2])

    def test_first_installation_source_aliases_require_the_exact_validated_transition(self):
        expected, main, shared, allocation, previous = self.first_installation_fixture()
        context = keys.installation_access_context(main, shared, allocation,
                                                  expected['route'], expected['primary'])
        for policy in (previous, context['desired_policy']):
            values = {'isolation_policy': deepcopy(policy), 'keep': '{{ literal_source_setting }}'}
            original = deepcopy(values)
            updated = keys.source_management_variables(values, context)
            self.assertEqual(updated['keep'], values['keep'])
            self.assertEqual(updated['isolation_policy'], context['desired_policy'])
            self.assertEqual(values, original)
        pinned = keys.inventory_variables(main['autodeploy_configuration']['inventories'][0])
        updated = keys.source_management_variables(pinned, context, True)
        self.assertEqual(updated['aap_hypervisor_isolation_protected_ipv4'],
                         [main['aap_autodeploy_source_public_ip']])
        unrelated = deepcopy(previous)
        unrelated['guest_host_clients'] = deepcopy(expected['declared_policy']['guest_host_clients'])
        self.assertTrue(unrelated['guest_host_clients'])
        with self.assertRaisesRegex(keys.StoreError, 'exact validated transition'):
            keys.source_management_variables({'isolation_policy': unrelated}, context)
        management = dict(context, access_mode='management')
        with self.assertRaises(keys.StoreError):
            keys.source_management_variables({'isolation_policy': previous}, management)

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

    def test_runtime_installation_verifier_is_read_only_and_preserves_approved_policy(self):
        expected, observed, *_ = fixture()
        expected['mode'] = 'installation'
        original = deepcopy(observed)
        with mock.patch.object(access, 'probe', return_value=observed), \
             mock.patch.object(access, 'command') as command:
            result = access.reconcile(expected)
            self.assertTrue(result['changed'])
            self.assertFalse(result['applied'])
            self.assertEqual(result['desired_policy'], access.desired_policy(expected['route'], expected['primary'], expected['declared_policy'], 'installation'))
            self.assertEqual(observed, original)
            command.assert_not_called()

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
        proof=keys.source_related_resources(client,shared,allocation['aap_vm_allocation'],physical,application_capture(context))
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
        expected, probe, *_ = fixture()
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
  assert task_vars['fixture_transition']==task_vars['fixture_original_transition']
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
from importlib.util import module_from_spec,spec_from_file_location
from ansible.plugins.action import ActionBase
spec=spec_from_file_location('fixture_native_access',ACCESSPATH)
access=module_from_spec(spec);spec.loader.exec_module(access)
class ActionModule(ActionBase):
 def run(self,tmp=None,task_vars=None):
  original=task_vars['hostvars'][task_vars['inventory_hostname']]
  pin=original['aap_instance_route']['hypervisor'];connection=self._play_context
  assert connection.remote_addr==pin['address'] and connection.remote_user==pin['user'] and connection.port==pin['port']
  assert 'StrictHostKeyChecking=yes' in self._connection.get_option('ssh_common_args')
  assert 'ProxyCommand' not in self._connection.get_option('ssh_common_args')
  request=json.loads(self._task.args['stdin']);assert request['mode']=='installation' and not request['check_mode']
  transition=task_vars['fixture_transition']
  assert transition==task_vars['fixture_original_transition']
  assert request['declared_policy']==dict(transition['previous_policy'],protected_ipv4=transition['desired_policy']['protected_ipv4'])
  if task_vars['fixture_first_empty']:assert 'protected_ipv4'not in transition['previous_policy']
  observed=dict(task_vars['fixture_probe'],policy=request['declared_policy'])
  planned=access.plan(request,observed)
  assert planned['desired_policy']==transition['desired_policy']
  with Path(TRACEPATH).open('a')as output:output.write(json.dumps({'transport':True,'trust':original['aap_instance_trust']['path']})+'\\n')
  return {'changed':False,'rc':0,'stdout':json.dumps({'changed':False,'applied':True,'native_rule_previous':{'runtime':False,'permanent':False}})}
'''.replace('TRACEPATH',repr(str(trace))).replace('ACCESSPATH',repr(str(root/'src/aap_hypervisor_access.py'))))
            child=yaml.safe_load((root/'tasks/aap-installation-access.yml').read_text())
            management = yaml.safe_load((root/'tasks/aap-hypervisor-access.yml').read_text())
            transaction = next(task for task in management if 'block' in task)
            verifier = next(task for task in transaction['block'] if task['name'].startswith('Verify native guest identity'))
            verifier['installation_transport_proof'] = verifier.pop('ansible.builtin.command')
            verifier['installation_transport_proof']['argv'] = ['synthetic-resource-code-not-executed']
            publisher = next(task for task in transaction['block'] if 'aap_publish_instance_keys' in task)
            transaction['block'] = [verifier, publisher]
            transaction.pop('rescue', None)
            transaction.pop('always', None)
            native_child = directory/'aap-hypervisor-access.yml'
            native_child.write_text(yaml.safe_dump(management[:2]+[transaction], sort_keys=False))
            child[1]['ansible.builtin.include_tasks'] = str(native_child)
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
                       'fixture_primary':expected['primary'],'fixture_transition':transition,
                       'fixture_original_transition':deepcopy(transition),'fixture_probe':probe,
                       'fixture_first_empty':False,
                       'vault_ansible_user':'fixture_operator','vault_ansible_password':'fixture_password'}
            fixture_play=directory/'play.yml'
            fixture_play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,
                'vars':variables,'pre_tasks':pre,'tasks':[{'name':'Forbidden ordinary base stage',
                'ansible.builtin.fail':{'msg':'Ordinary base configuration must not execute'}}],
                'post_tasks':[{'name':'Forbidden final AAP release after bounded repair','tags':['always'],
                'ansible.builtin.fail':{'msg':'Repair must end before any final release'}}]}],sort_keys=False))
            env=dict(os.environ,ANSIBLE_ACTION_PLUGINS=str(plugins),ANSIBLE_FILTER_PLUGINS=str(root/'filter_plugins'),
                     ANSIBLE_LOCAL_TEMP=str(directory/'local'),ANSIBLE_REMOTE_TEMP=str(directory/'remote'),ANSIBLE_NOCOLOR='1')
            for native, first_empty in ((False,False),(True,False),(False,True),(True,True)):
                if first_empty:
                    previous={key:deepcopy(expected['declared_policy'][key])for key in ('bridges','dns_bridges')}
                    declared=dict(previous,protected_ipv4=expected['declared_policy']['protected_ipv4'])
                    selected={'previous_policy':previous,'desired_policy':access.desired_policy(
                        expected['route'],expected['primary'],declared,'installation')}
                else:
                    selected=transition
                # The same tagged entry point must materialize protection without changing its old transition.
                fixture_data=yaml.safe_load(fixture_play.read_text())
                fixture_data[0]['vars'].update(fixture_transition=deepcopy(selected),
                    fixture_original_transition=deepcopy(selected),fixture_first_empty=first_empty)
                fixture_play.write_text(yaml.safe_dump(fixture_data,sort_keys=False))
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
        self.assert_encrypted_publication_roundtrip()

    def test_real_first_empty_encrypted_publication_preserves_exact_transition_and_allocator(self):
        self.assert_encrypted_publication_roundtrip(first_empty=True)

    def assert_encrypted_publication_roundtrip(self, first_empty=False):
        module = load('installation_publication_action', 'action_plugins/aap_publish_instance_keys.py')
        expected, _, main, shared, hactar, allocation = fixture()
        previous = None
        if first_empty:
            previous={key:deepcopy(expected['declared_policy'][key])for key in ('bridges','dns_bridges')}
            main['aap_autodeploy_source_public_ip']='203.0.113.10'
            self.set_declared_policy(main,previous)
            for configuration, field in ((shared,'host_inventory_configuration'),(hactar,None)):
                rows=configuration[field]['hosts']if field else configuration['controller_hosts_hactar_recovery']
                for row in rows:
                    values=keys.inventory_variables(row)
                    if values.get('ansible_host')==expected['route']['hypervisor']['address']:
                        values.update(isolation_policy=deepcopy(previous),hactar_isolation_policy=deepcopy(previous),
                                      firewall_additional_zone_rules=[])
                        keys.set_inventory_variables(row,values)
            name=expected['route']['vm_name']
            shared['host_inventory_configuration']['hosts']=[row for row in shared['host_inventory_configuration']['hosts']
                if not keys.aap_inventory_owner(row,name)]
            for group in shared['host_inventory_configuration']['groups']:
                group['hosts']=[member for member in group.get('hosts',[])if member!=name]
        class Client(FakeRetirementSource):
            def __init__(self, *args):
                super().__init__(*args)
                self.members = {row['id'] for row in self.hosts.values() if row['inventory'] == 1}

            def rows(self, path):
                if path.startswith('groups/?'):
                    return [{'id':77,'name':'guests','inventory':1,'variables':json.dumps({'hypervisor_host':'fixture-hypervisor'})}]
                if path == 'groups/77/hosts/':
                    return [{'id':identity} for identity in self.members]
                return super().rows(path)

            def request(self, method, path, body=None):
                if method == 'POST' and path == 'hosts/':
                    identity = max(self.hosts) + 1
                    self.calls.append((method, path))
                    self.hosts[identity] = dict(deepcopy(body), id=identity)
                    return deepcopy(self.hosts[identity])
                if method == 'POST' and path == 'groups/77/hosts/':
                    self.assert_member(body['id'])
                    self.calls.append((method, path))
                    self.members.add(body['id'])
                    return {}
                return super().request(method, path, body)

            def assert_member(self, identity):
                if identity not in self.hosts or self.hosts[identity]['inventory'] != 1:
                    raise AssertionError('Associate only the selected fixture inventory host.')
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
            with mock.patch.object(ActionBase,'run',return_value={}),mock.patch.object(module.ActionModule,'_project_root',return_value=project), \
                 mock.patch.object(module,'SourceClient',return_value=client),mock.patch.object(module.subprocess,'run',side_effect=redirected), \
                 mock.patch.dict(os.environ,{'CAC_GIT_TOKEN':'synthetic-writer'}):
                planned=run('plan');self.assertNotIn('failed',planned,planned)
                self.assertFalse(planned['published']);self.assertEqual(client.calls,[])
                transition=planned['transition']
                if first_empty:
                    self.assertEqual(transition['previous_policy'],previous)
                    self.assertEqual(transition['desired_policy']['protected_ipv4'],
                                     [main['aap_autodeploy_source_public_ip']])
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
            if first_empty:
                desired=transition['desired_policy']
                for configuration,kind in ((restored['vaults/cac/aap_autodeploy_configascode-cac-vault.yml'],'autodeploy'),
                        (restored['cac/host_inventory.yml'],'shared'),(restored['cac/hactar_recovery.yml'],'hactar')):
                    if kind=='autodeploy':row=configuration['autodeploy_configuration']['inventories'][0]
                    else:
                        rows=configuration['host_inventory_configuration']['hosts']if kind=='shared'else configuration['controller_hosts_hactar_recovery']
                        row=next(row for row in rows if keys.inventory_variables(row).get('ansible_host')==expected['route']['hypervisor']['address'])
                    self.assertEqual(keys.inventory_variables(row)['hactar_isolation_policy'],desired)
                self.assertEqual(transition['previous_policy'],previous)
                selected=[row for row in client.hosts.values()
                          if row['inventory']==1 and keys.aap_inventory_owner(row,expected['route']['vm_name'])]
                self.assertEqual(len(selected),1)
                self.assertIn(selected[0]['id'],client.members)
                self.assertEqual(keys.inventory_variables(selected[0])['vm_resource'],
                                 dict(expected['primary'],vm_name=expected['route']['vm_name']))
                self.assertEqual(client.calls.count(('POST','hosts/')),1)
                self.assertEqual(client.calls.count(('POST','groups/77/hosts/')),1)
                current_hosts=restored['cac/host_inventory.yml']['host_inventory_configuration']['hosts']
                for original in shared['host_inventory_configuration']['hosts']:
                    if keys.inventory_variables(original).get('ansible_host')!=expected['route']['hypervisor']['address']:
                        self.assertIn(original,current_hosts)


if __name__=='__main__':unittest.main()
