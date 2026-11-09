"""Final AAP release reuses consumed ownership without changing its allocation."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ansible.errors import AnsibleFilterError
import test_guest_release as transaction
from test_aap_hypervisor_access import fixture as access_fixture
from test_guest_release_runtime import runtime

ORIGINAL_FIXTURE = access_fixture


def fixture(new=True):
    expected, _, main, shared, hactar, allocation = ORIGINAL_FIXTURE()
    route, primary = expected['route'], expected['primary']
    shared = transaction.keys.merge_inventory(shared, route['vm_name'], route, expected['declared_policy'], primary)
    guest = {'kind': 'aap', 'route': deepcopy(route), 'primary': deepcopy(primary), 'guest_machine_id': 'a' * 32}
    return guest, route['hypervisor'], main, shared, hactar, allocation


def native_fixture():
    guest, pin, main, shared, _, allocation = fixture()
    _, state, *_ = ORIGINAL_FIXTURE()
    context = transaction.keys.aap_release_context(main, shared, allocation, guest, pin)
    request = {'operation': 'apply', 'guest': guest, 'hypervisor': pin, 'check_mode': False,
               'transition': {key: context[key] for key in ('previous_policy', 'desired_policy')}}
    return request, state


class AapFinalReleaseTests(unittest.TestCase):
    def test_existing_inventory_alias_keeps_physical_reservation_identity(self):
        guest,pin,main,shared,hactar,allocation=fixture()
        physical=guest['route']['vm_name'];alias='aap27-v07';keys=transaction.keys
        row=next(row for row in shared['host_inventory_configuration']['hosts']if keys.aap_inventory_owner(row,physical))
        row['name']=alias
        for group in shared['host_inventory_configuration']['groups']:
            group['hosts']=[alias if name==physical else name for name in group.get('hosts',[])]
        source=transaction.Source(main,shared,hactar)
        before=deepcopy(allocation)
        context=keys.aap_release_context(main,shared,allocation,guest,pin)
        self.assertEqual(context['inventory_host_name'],alias)
        desired={kind:keys.retire_inventory_capture(value,context,kind)for kind,value in
                 {'autodeploy':main,'shared':shared,'hactar':hactar}.items()}
        self.assertTrue(keys.source_aap_release_operations(source,desired['shared'],desired['autodeploy'],desired['hactar'],context))
        self.assertEqual(context['route']['vm_name'],physical)
        self.assertEqual(allocation,before)

    def test_source_adds_only_consumed_primary_release_preserving_all_other_state(self):
        guest, pin, main, shared, hactar, allocation = fixture()
        original = deepcopy((main, shared, hactar, allocation))
        keys = transaction.keys
        context = keys.aap_release_context(main, shared, allocation, guest, pin)
        expected = deepcopy(context['previous_policy'])
        primary = guest['primary']
        expected.setdefault('released_clients', []).append({'bridge': primary['bridge'], 'ipv4': primary['address'], 'mac': primary['mac']})
        self.assertEqual(context['desired_policy'], expected)
        desired = {kind: keys.retire_inventory_capture(value, context, kind) for kind, value in
                   {'autodeploy': main, 'shared': shared, 'hactar': hactar}.items()}
        source = transaction.Source(main, shared, hactar)
        operations = keys.source_aap_release_operations(source, desired['shared'], desired['autodeploy'], desired['hactar'], context)
        self.assertTrue(operations)
        self.assertTrue(all(method == 'PATCH' for method, *_ in operations))
        before = next(row for row in shared['host_inventory_configuration']['hosts'] if keys.aap_inventory_owner(row, guest['route']['vm_name']))
        after = next(row for row in desired['shared']['host_inventory_configuration']['hosts'] if row['name'] == before['name'])
        self.assertEqual(before, after)
        self.assertEqual((main, shared, hactar, allocation), original)
        self.assertEqual(desired['autodeploy']['aap_instance_api_credentials'], main['aap_instance_api_credentials'])

    def test_source_refuses_foreign_retired_incomplete_or_changed_identity(self):
        for variant in ('retired', 'primary', 'route', 'machine', 'hypervisor-machine', 'extra', 'missing-host', 'recorded-machine', 'foreign-live'):
            guest, pin, main, shared, hactar, allocation = fixture()
            if variant == 'retired': allocation['aap_vm_allocation']['reservations']['selected-request']['decommissioned'] = True
            elif variant == 'primary': guest['primary']['uuid'] = '88888888-2222-3333-4444-555555555555'
            elif variant == 'route': guest['route']['vm_ip'] = '192.168.70.99'
            elif variant == 'machine': guest['guest_machine_id'] = 'invalid'
            elif variant == 'hypervisor-machine': guest['guest_machine_id'] = pin['machine_id']
            elif variant == 'extra': guest['host_keys'] = ['ssh-ed25519 AAAA']
            elif variant == 'missing-host': shared['host_inventory_configuration']['hosts'] = [row for row in shared['host_inventory_configuration']['hosts'] if not transaction.keys.aap_inventory_owner(row, guest['route']['vm_name'])]
            elif variant == 'recorded-machine':
                row = next(row for row in shared['host_inventory_configuration']['hosts'] if transaction.keys.aap_inventory_owner(row, guest['route']['vm_name']))
                values = transaction.keys.inventory_variables(row);values['machine_id'] = 'b' * 32
                transaction.keys.set_inventory_variables(row, values)
            source = transaction.Source(main, shared, hactar)
            if variant == 'foreign-live':
                row = next(row for row in source.hosts.values() if row['name'] == guest['route']['vm_name'])
                values = transaction.keys.inventory_variables(row);values['vm_uuid'] = '88888888-2222-3333-4444-555555555555'
                row['variables'] = json.dumps(values)
            with self.subTest(variant=variant), self.assertRaises((transaction.keys.StoreError, AnsibleFilterError)):
                context = transaction.keys.aap_release_context(main, shared, allocation, guest, pin)
                transaction.keys.source_aap_release_operations(source, shared, main, hactar, context)
            self.assertFalse(source.calls)

    def test_native_reuses_aap_ownership_without_generic_description_and_rejects_changed_devices(self):
        request, state = native_fixture()
        self.assertTrue(runtime.plan(request, state)['changed'])
        for variant in ('machine', 'uuid', 'mac', 'disk', 'network', 'policy', 'kind', 'bootstrap', 'shared-disk'):
            request, state = native_fixture()
            route, primary = request['guest']['route'], request['guest']['primary']
            if variant == 'machine': request['guest']['guest_machine_id'] = request['hypervisor']['machine_id']
            elif variant in ('uuid', 'mac', 'disk', 'network'):
                xml = state['domains'][route['vm_name']]['persistent']
                state['domains'][route['vm_name']]['persistent'] = xml.replace(primary[variant], 'foreign')
            elif variant == 'policy': request['transition']['desired_policy']['protected_ipv4'] = []
            elif variant == 'kind': request['guest']['kind'] = 'generic'
            elif variant == 'bootstrap': request['mode'] = 'bootstrap_https'
            else: state['domains']['foreign-v08'] = {'persistent': '<domain><name>foreign-v08</name><uuid>88888888-2222-3333-4444-555555555555</uuid><devices><disk device="disk"><source file="' + primary['disk'] + '"/></disk></devices></domain>'}
            with self.subTest(variant=variant), self.assertRaises((ValueError, KeyError)): runtime.plan(request, state)

    def test_native_resource_proof_does_not_apply_or_rollback_firewall(self):
        request, state = native_fixture()
        original = deepcopy(state)
        with patch.object(runtime.base, 'probe', return_value=state), \
             patch.object(runtime.base, 'command') as command:
            request['check_mode'] = True
            self.assertFalse(runtime.reconcile(request)['applied'])
            request['check_mode'] = False
            self.assertTrue(runtime.reconcile(request)['changed'])
            self.assertEqual(state, original)
            state['policy'] = deepcopy(request['transition']['desired_policy'])
            self.assertFalse(runtime.reconcile(request)['changed'])
            request['operation'] = 'rollback'
            self.assertTrue(runtime.reconcile(request)['changed'])
            command.assert_not_called()

    def test_native_encrypted_publication_preserves_reservation_tokens_and_source_host(self):
        with patch.object(transaction, 'fixture', side_effect=fixture):
            transaction.GuestReleaseTests().exercise_action('release_guest')


class AapReservationRaceTests(unittest.TestCase):
    def test_consumed_reservation_is_rechecked_before_and_after_durable_publication(self):
        import os,subprocess
        from types import SimpleNamespace
        from unittest import mock
        import yaml
        from ansible.parsing.dataloader import DataLoader
        from ansible.parsing.vault import VaultLib,VaultSecret
        from ansible.parsing.yaml.loader import AnsibleLoader
        from ansible.plugins.action import ActionBase
        for stage in ('before','after'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory(prefix='aap-final-reservation-race-')as directory:
                root=Path(directory);remote=root/'remote.git';seed=root/'seed';project=root/'project';seed.mkdir();project.mkdir()
                module=transaction.load('aap_final_race_action_'+stage,'action_plugins/aap_publish_instance_keys.py')
                guest,pin,main,shared,hactar,allocation=fixture();source=transaction.Source(main,shared,hactar)
                vault=VaultLib([('cac',VaultSecret(b'fixture-cac')),('default',VaultSecret(b'fixture-environment'))])
                real_run=subprocess.run
                def git(path,*args):return real_run(['git','-C',str(path),*args],text=True,capture_output=True,check=True)
                real_run(['git','init','--bare','--initial-branch=main',str(remote)],capture_output=True,check=True)
                git(seed,'init','--initial-branch=main')
                documents={'vaults/cac/aap_autodeploy_configascode-cac-vault.yml':main,'cac/host_inventory.yml':shared,
                           'cac/hactar_recovery.yml':hactar,'state/aap_vm_allocations_vault.yml':allocation}
                for name,value in documents.items():
                    path=seed/name;path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_bytes(vault.encrypt(yaml.dump(value,Dumper=transaction.vault_yaml.VaultDumper),vault_id='cac'))
                allocation_path='state/aap_vm_allocations_vault.yml';original_cipher=(seed/allocation_path).read_bytes()
                git(seed,'add','.');git(seed,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','Seed')
                git(seed,'remote','add','origin',str(remote));git(seed,'push','origin','main')
                (project/'myvars').write_bytes(vault.encrypt(yaml.safe_dump({'git_url':'https://git.example.invalid/fixture-owner/autodeploy.git'}),vault_id='default'))
                loader=DataLoader();loader.set_vault_secrets(vault.secrets)
                fired=False;checks=0
                def external_writer():
                    nonlocal fired
                    self.assertFalse(fired);fired=True
                    other=root/'independent-writer'
                    real_run(['git','clone','--quiet',str(remote),str(other)],capture_output=True,check=True)
                    changed=deepcopy(allocation);changed['aap_vm_allocation']['reservations']['selected-request']['decommissioned']=True
                    (other/allocation_path).write_bytes(vault.encrypt(yaml.dump(changed),vault_id='cac'))
                    git(other,'add',allocation_path);git(other,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','External ownership change')
                    git(other,'push','origin','main')
                verify=module.keys.verify_source_job
                def checked(*args,**kwargs):
                    nonlocal checks
                    result=verify(*args,**kwargs);checks+=1
                    if stage=='before'and checks==3:external_writer()
                    return result
                def redirected(command,*args,**kwargs):
                    command=[str(remote)if value=='https://git.example.invalid/fixture-owner/aap_autodeploy_configascode-secrets.git'else value for value in command]
                    self.assertFalse(any(value.startswith(('https://','http://','git@'))for value in command))
                    result=real_run(command,*args,**kwargs)
                    if stage=='after'and 'push'in command and result.returncode==0 and not fired:external_writer()
                    return result
                def run(phase,transition=None):
                    action=module.ActionModule.__new__(module.ActionModule)
                    args={'operation':'release_guest','phase':phase,'guest':guest,'hypervisor':pin}
                    if transition is not None:args['transition']=transition
                    action._task=SimpleNamespace(args=args,check_mode=False);action._loader=loader
                    return action.run(task_vars={'awx_job_id':123,'awx_job_template_id':456,'awx_project_revision':'a'*40})
                with mock.patch.object(ActionBase,'run',side_effect=lambda *a,**k:{}),mock.patch.object(module.ActionModule,'_project_root',return_value=project), \
                     mock.patch.object(module,'SourceClient',return_value=source),mock.patch.object(module.subprocess,'run',side_effect=redirected), \
                     mock.patch.object(module.keys,'verify_source_job',side_effect=checked),mock.patch.dict(os.environ,{'CAC_GIT_TOKEN':'synthetic-writer'}):
                    planned=run('plan');self.assertFalse(planned.get('failed'),planned)
                    result=run('publish',planned['transition'])
                self.assertTrue(fired);self.assertTrue(result['failed'],result)
                self.assertEqual(result['durable_policy_published'],stage=='after',result)
                self.assertEqual(source.calls,[],'Changed ownership must stop before source API mutations.')
                self.assertEqual(git(remote,'show','main~1:'+allocation_path).stdout.encode(),original_cipher)
                observed=AnsibleLoader(vault.decrypt(git(remote,'show','main:'+allocation_path).stdout.encode())).get_single_data()
                expected=deepcopy(allocation);expected['aap_vm_allocation']['reservations']['selected-request']['decommissioned']=True
                self.assertEqual(observed,expected)
                current=AnsibleLoader(vault.decrypt(git(remote,'show','main:vaults/cac/aap_autodeploy_configascode-cac-vault.yml').stdout.encode())).get_single_data()
                self.assertEqual(current['aap_instance_api_credentials'],main['aap_instance_api_credentials'])


if __name__ == '__main__': unittest.main()
