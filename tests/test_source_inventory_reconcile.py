"""Exercise selected Source metadata repair with native guards and encrypted Git reads."""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import yaml
from ansible.errors import AnsibleActionFail, AnsibleFilterError
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.vault import VaultLib, VaultSecret
from ansible.plugins.action import ActionBase

from test_aap_supplemental_interfaces import planned
from test_instance_keys import load

ROOT = Path(__file__).resolve().parents[1]
keys = load('metadata_reconcile_keys', 'src/aap_instance_keys.py')
publisher = load('metadata_reconcile_publisher', 'action_plugins/aap_publish_instance_keys.py')
reader = load('metadata_reconcile_reader', 'action_plugins/aap_read_instance.py')


def fixture():
    guest, _, _, shared, _, allocation, context, _ = planned()
    shared = keys.supplemental_interface_capture(shared, context, 'shared')
    allocation = keys.supplemental_interface_capture(allocation, context, 'allocation')
    route = guest['route']
    host = next(row for row in shared['host_inventory_configuration']['hosts']
                if keys.aap_inventory_owner(row, route['vm_name']))
    host['name'] = 'aap27-v07'
    canonical = keys.inventory_variables(host)
    canonical['keep'] = {'literal': '{{ never_render_this }}'}
    keys.set_inventory_variables(host, canonical)
    current = deepcopy(canonical)
    del current['vm_resource']['supplemental_interfaces']
    source = Source(host['name'], host['inventory'], current)
    resources = allocation['aap_vm_allocation']['reservations']['selected-request']['instance_resources']
    return source, shared, allocation, route, resources, current


class Source:
    origin = 'https://source.example.invalid'

    def __init__(self, name, inventory, values):
        self.row = {'id': 41, 'name': name, 'inventory': 2, 'variables': json.dumps(values)}
        self.inventory = {'id': 2, 'name': inventory}
        self.job = {'id': 123, 'inventory': 2, 'status': 'running', 'job_template': 152,
                    'scm_revision': 'a' * 40}
        self.calls = []
        self.before_read = None
        self.after_patch = None
        self.fail_patch = False

    def rows(self, path):
        self.calls.append(('GET', path))
        if path.startswith('inventories/?name='):
            return [deepcopy(self.inventory)]
        if path.startswith('hosts/?inventory='):
            return [deepcopy(self.row)]
        raise AssertionError(path)

    def request(self, method, path, body=None):
        self.calls.append((method, path))
        if path == 'jobs/123/' and method == 'GET':
            return deepcopy(self.job)
        if path == 'hosts/41/':
            if method == 'GET':
                if self.before_read:
                    change, self.before_read = self.before_read, None
                    change(self)
                return deepcopy(self.row)
            if method == 'PATCH':
                if self.fail_patch:
                    raise keys.StoreError('Synthetic API failure.')
                self.row.update(deepcopy(body))
                if self.after_patch:
                    self.after_patch(self)
                return deepcopy(self.row)
        raise AssertionError((method, path))

    def writes(self):
        return [call for call in self.calls if call[0] != 'GET']


class SourceMetadataTests(unittest.TestCase):
    def setUp(self):
        self.source, self.shared, self.allocation, self.route, self.resources, self.caller = fixture()
        self.selected = self.source.row['name']

    def reconcile(self, **kwargs):
        return keys.ensure_source_inventory(self.source, self.shared, self.selected, self.route,
            missing_supplemental_only=True, resources=self.resources, job_inventory_id=2,
            caller_host=self.caller, **kwargs)

    def test_missing_key_repairs_once_preserving_every_other_value_and_capture(self):
        original = deepcopy((self.shared, self.allocation, self.source.row))
        result = self.reconcile()
        self.assertTrue(result['changed'])
        self.assertEqual(result['vm_resource'], self.resources['aap'] | {'vm_name': self.route['vm_name']})
        expected = keys.inventory_variables(original[2])
        expected['vm_resource']['supplemental_interfaces'] = self.resources['aap']['supplemental_interfaces']
        self.assertEqual(keys.inventory_variables(self.source.row), expected)
        self.assertEqual((self.shared, self.allocation), original[:2])
        self.assertEqual(self.source.writes(), [('PATCH', 'hosts/41/')])
        self.caller = deepcopy(expected)
        self.assertFalse(self.reconcile()['changed'])
        self.assertEqual(len(self.source.writes()), 1)

    def test_absent_canonical_supplemental_is_noop(self):
        del self.resources['aap']['supplemental_interfaces']
        row = next(row for row in self.shared['host_inventory_configuration']['hosts'] if row['name'] == self.selected)
        values = keys.inventory_variables(row)
        del values['vm_resource']['supplemental_interfaces']
        keys.set_inventory_variables(row, values)
        self.assertFalse(self.reconcile()['changed'])
        self.assertFalse(self.source.writes())

    def test_present_conflicting_supplemental_values_are_never_overwritten(self):
        for value in ([], None, [{'address': '192.0.2.99'}]):
            with self.subTest(value=value):
                values = deepcopy(self.caller)
                values['vm_resource']['supplemental_interfaces'] = value
                self.source.row['variables'] = json.dumps(values)
                with self.assertRaises((ValueError, AnsibleFilterError)):
                    self.reconcile()
                self.assertFalse(self.source.writes())

    def test_any_primary_or_identity_conflict_refuses_without_write(self):
        mutations = [
            lambda v: v['vm_resource'].update(uuid='99999999-2222-3333-4444-555555555555'),
            lambda v: v['vm_resource'].update(disk='/foreign'),
            lambda v: v['vm_resource'].update(address='192.0.2.99'),
            lambda v: v['vm_resource'].update(mac='52:54:00:00:00:99'),
            lambda v: v['vm_resource'].update(network='foreign'),
            lambda v: v['vm_resource'].update(bridge='foreign'),
            lambda v: v['vm_resource'].update(hypervisor_machine_id='9' * 32),
            lambda v: v['vm_resource'].update(verified=False),
            lambda v: v['vm_resource'].pop('uuid'),
            lambda v: v.pop('vm_resource'),
            lambda v: v.update(vm_uuid='99999999-2222-3333-4444-555555555555'),
            lambda v: v.update(ansible_host='192.0.2.99'),
            lambda v: v.update(ansible_fqdn='foreign.example.invalid'),
            lambda v: v.update(host_keys=['ssh-ed25519 Rk9SRUlHTg==']),
            lambda v: v.update(aap_instance_number=8),
            lambda v: v.update(hypervisor_host='foreign'),
            lambda v: v.update(machine_id='9' * 32),
        ]
        for mutate in mutations:
            for location in ('source', 'caller'):
                with self.subTest(mutate=mutate, location=location):
                    values = deepcopy(self.caller)
                    mutate(values)
                    prior_row = deepcopy(self.source.row)
                    prior_caller = deepcopy(self.caller)
                    if location == 'source':
                        self.source.row['variables'] = json.dumps(values)
                    else:
                        self.caller = values
                    with self.assertRaises((ValueError, AnsibleFilterError)):
                        self.reconcile()
                    self.assertFalse(self.source.writes())
                    self.source.row, self.caller = prior_row, prior_caller

    def test_wrong_inventory_or_duplicate_owner_refuses(self):
        self.source.inventory['id'] = 99
        with self.assertRaises(ValueError):
            self.reconcile()
        self.assertFalse(self.source.writes())
        self.source.inventory['id'] = 2
        self.shared['host_inventory_configuration']['hosts'].append(
            deepcopy(next(row for row in self.shared['host_inventory_configuration']['hosts'] if row['name'] == self.selected)))
        with self.assertRaises(ValueError):
            self.reconcile()
        self.assertFalse(self.source.writes())

    def test_canonical_allocation_and_shared_disagreement_refuses(self):
        self.resources['aap']['supplemental_interfaces'][0]['connection_name'] = 'different'
        with self.assertRaises((ValueError, AnsibleFilterError)):
            self.reconcile()
        self.assertFalse(self.source.writes())

    def test_fresh_preimage_change_refuses_without_write(self):
        def change(source):
            values = keys.inventory_variables(source.row)
            values['keep'] = 'concurrent'
            source.row['variables'] = json.dumps(values)
        self.source.before_read = change
        with self.assertRaisesRegex(ValueError, 'changed during'):
            self.reconcile()
        self.assertFalse(self.source.writes())

    def test_patch_failure_and_readback_mismatch_never_report_verification(self):
        self.source.fail_patch = True
        with self.assertRaisesRegex(ValueError, 'API failure'):
            self.reconcile()
        self.source.fail_patch = False
        self.source.after_patch = lambda source: source.row.update(variables=json.dumps(self.caller))
        with self.assertRaisesRegex(ValueError, 'Verify the exact'):
            self.reconcile()

    def test_check_mode_does_not_write_missing_metadata(self):
        with self.assertRaisesRegex(ValueError, 'check mode'):
            self.reconcile(check_mode=True)
        self.assertFalse(self.source.writes())

    def test_canonical_decimal_counter_is_not_rewritten(self):
        self.caller['aap_instance_number'] = str(self.caller['aap_instance_number'])
        values = keys.inventory_variables(self.source.row)
        values['aap_instance_number'] = str(values['aap_instance_number'])
        self.source.row['variables'] = json.dumps(values)
        self.assertTrue(self.reconcile()['changed'])
        self.assertIsInstance(keys.inventory_variables(self.source.row)['aap_instance_number'], str)


class NativeActionTests(unittest.TestCase):
    def native_repair(self, base, remote, project, source, caller, route, resources, secret):
        native = base/'native'; (native/'action_plugins').mkdir(parents=True)
        shutil.copy(project/'myvars', native/'myvars')
        (native/'vault-password').write_bytes(secret.bytes)
        (native/'vault-password').chmod(0o600)
        shutil.copy(ROOT/'action_plugins/aap_read_instance.py', native/'action_plugins/aap_read_instance.py')
        for folder in ('src', 'filter_plugins'):
            (native/folder).symlink_to(ROOT/folder, target_is_directory=True)
        (native/'fixture.json').write_text(json.dumps({'selected':source.row['name'],
            'inventory':source.inventory['name'], 'values':caller}))
        # Native Ansible loads the real action; only its synthetic API and Git remote are substituted.
        wrapper = f'''import sys
from pathlib import Path
import json
sys.path.insert(0, {str(ROOT/'tests')!r})
from test_source_inventory_reconcile import Source, load
module = load('native_metadata_publisher', 'action_plugins/aap_publish_instance_keys.py')
fixture = json.loads(Path({str(native/'fixture.json')!r}).read_text())
source = Source(fixture['selected'], fixture['inventory'], fixture['values'])
module.SourceClient = lambda: source
original_run = module.subprocess.run
def fixture_run(argv, *args, **kwargs):
    if argv[0] == 'git':
        assert not any(value in argv for value in ('push', 'commit'))
        if 'remote' in argv and 'add' in argv:
            argv = list(argv); argv[-1] = {str(remote)!r}
    return original_run(argv, *args, **kwargs)
module.subprocess.run = fixture_run
ActionModule = module.ActionModule
'''
        (native/'action_plugins/aap_publish_instance_keys.py').write_text(wrapper)
        values = deepcopy(caller); values['keep'] = 'unchanged'
        (native/'inventory.yml').write_text(yaml.safe_dump({'all': {'hosts': {source.row['name']: values}}}))
        source_tasks = yaml.safe_load((ROOT/'deploy-selected-use-cases.yml').read_text())[0]['tasks'][0]['block']
        repair = next(task for task in source_tasks if task.get('aap_publish_instance_keys', {}).get('operation') == 'reconcile_inventory_metadata')
        refresh = next(task for task in source_tasks if 'ansible.builtin.add_host' in task)
        guard = yaml.safe_load((ROOT/'tasks/aap-instance-select.yml').read_text())[2]
        for logging in (True, False):
            play = [{'hosts':'localhost', 'connection':'local', 'gather_facts':False,
                'vars': {'aap_instance_key':source.row['name'], 'debug_logging':logging,
                         'awx_job_id':123, 'awx_job_template_id':152, 'awx_project_revision':'a'*40,
                         'aap_selected_source_auth': {'hostname':source.origin},
                         'aap_selected_target_auth': {'hostname':route['aap_hostname']},
                         'aap_registered_target': {'instance_route':route, 'instance_resources':resources}},
                'tasks': [repair, refresh, guard, {'ansible.builtin.assert': {'that': [
                    'aap_selected_inventory_metadata.changed', 'aap_selected_inventory_metadata.metadata_verified',
                    'hostvars[aap_instance_key].keep == "unchanged"']}}]}]
            (native/'play.yml').write_text(yaml.safe_dump(play, sort_keys=False))
            environment = dict(os.environ, CAC_GIT_TOKEN='synthetic-read-only-token',
                ANSIBLE_LOCAL_TEMP=str(native/'local'), ANSIBLE_REMOTE_TEMP=str(native/'remote'),
                ANSIBLE_NOCOLOR='1', ANSIBLE_ACTION_PLUGINS=str(native/'action_plugins'))
            process = subprocess.run([sys.executable, '-B', '-c',
                'from ansible.cli.playbook import main; main()', '-i', str(native/'inventory.yml'),
                '--vault-password-file', str(native/'vault-password'), str(native/'play.yml')],
                cwd=native, env=environment, text=True, capture_output=True, timeout=60)
            self.assertEqual(process.returncode, 0, process.stdout+'\n'+process.stderr)

    def test_encrypted_read_only_publication_and_generic_reader_use_same_canonical_state(self):
        source, shared, allocation, route, resources, caller = fixture()
        real_run = subprocess.run
        secret = VaultSecret(b'synthetic-cac-password')
        vault = VaultLib([('default', secret)])
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            remote, seed, project = base/'remote.git', base/'seed', base/'project'
            seed.mkdir(); project.mkdir()
            (project/'action_plugins').symlink_to(ROOT/'action_plugins', target_is_directory=True)
            (project/'myvars').write_bytes(vault.encrypt(yaml.safe_dump({
                'vault_cac_repository_namespace': 'https://git.example.invalid/fixture'})))
            def git(path, *args):
                return real_run(['git', '-C', str(path), *args], check=True, text=True, capture_output=True)
            real_run(['git','init','--bare','--initial-branch=main',str(remote)], check=True, capture_output=True)
            git(seed, 'init', '--initial-branch=main')
            for relative, document in {'state/aap_vm_allocations_vault.yml': allocation,
                                       'cac/host_inventory.yml': shared}.items():
                path = seed/relative; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(vault.encrypt(yaml.dump(document, Dumper=publisher.vault_yaml.VaultDumper)))
            git(seed,'add','.')
            git(seed,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','Fixture')
            git(seed,'remote','add','origin',str(remote)); git(seed,'push','origin','main')
            before = git(remote,'rev-parse','main').stdout
            self.native_repair(base, remote, project, source, caller, route, resources, secret)
            self.assertEqual(git(remote,'rev-parse','main').stdout, before)
            calls = []
            def local_git(argv, **kwargs):
                calls.append(list(argv))
                self.assertEqual(argv[0], 'git')
                self.assertFalse(any(value in argv for value in ('push', 'commit')))
                if 'remote' in argv and 'add' in argv:
                    argv = list(argv); argv[-1] = str(remote)
                return real_run(argv, **kwargs)
            loader = DataLoader(); loader.set_vault_secrets([('default',secret)])
            action = object.__new__(publisher.ActionModule)
            action._loader = loader
            action._original_path = str(project/'action_plugins/aap_publish_instance_keys.py')
            # Use a real project directory with fixture encrypted settings, never native credentials.
            action._project_root = lambda: project
            action._task = SimpleNamespace(args={'operation':'reconcile_inventory_metadata',
                                                 'inventory_host':source.row['name']},check_mode=False)
            variables = {'hostvars': {source.row['name']: caller}, 'awx_job_id':123,
                         'awx_job_template_id':152, 'awx_project_revision':'a'*40}
            with mock.patch.dict(os.environ, {'CAC_GIT_TOKEN':'synthetic-read-only-token'}), \
                 mock.patch.object(subprocess,'run',side_effect=local_git), \
                 mock.patch.object(ActionBase,'run',return_value={}), \
                 mock.patch.object(publisher,'SourceClient',return_value=source):
                for enabled in (True, False):
                    variables['debug_logging'] = enabled
                    result = action.run(task_vars=variables)
                    self.assertTrue(result['metadata_verified'])
                    self.assertNotIn('synthetic-read-only-token', json.dumps(result))
                    # Simulate only the actual caller's selected resource refresh.
                    variables['hostvars'][source.row['name']]['vm_resource'] = result['vm_resource']
                self.assertEqual(source.writes(), [('PATCH','hosts/41/')])
                with mock.patch.object(reader,'source_keys',side_effect=AssertionError('Generic reader touched Source API')):
                    generic = reader.ActionModule.read_instance(loader, project,
                        {'instance_key':route['vm_name']}, variables)
                    self.assertEqual(generic['instance_resources'], resources)
                    self.assertNotIn('inventory_configuration', generic)
                for field,value in (('status','successful'),('job_template',999),('scm_revision','b'*40),
                                    ('id',999),('inventory',999)):
                    prior = deepcopy(source.job); source.job[field] = value
                    count = len(source.writes())
                    with self.subTest(field=field), self.assertRaises(AnsibleActionFail):
                        action.run(task_vars=variables)
                    self.assertEqual(len(source.writes()), count)
                    source.job = prior
                prior_origin = source.origin
                source.origin = route['aap_hostname']
                with self.assertRaises(AnsibleActionFail): action.run(task_vars=variables)
                source.origin = prior_origin
                with mock.patch.object(source, 'request', side_effect=keys.StoreError('Synthetic denied API')):
                    with self.assertRaises(AnsibleActionFail): action.run(task_vars=variables)
                retired = deepcopy(allocation)
                retired['aap_vm_allocation']['reservations']['selected-request']['decommissioned'] = True
                (seed/'state/aap_vm_allocations_vault.yml').write_bytes(vault.encrypt(yaml.dump(retired)))
                git(seed,'add','.'); git(seed,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                                         'commit','-m','Retire fixture')
                # Seed the bare fixture through the saved, unmocked subprocess function.
                git(seed,'push','origin','main')
                count = len(source.writes())
                with self.assertRaises(AnsibleActionFail): action.run(task_vars=variables)
                self.assertEqual(len(source.writes()), count)
                # The only changed remote commit was made by this test's explicit fixture setup.
                before = git(remote,'rev-parse','main').stdout
            self.assertEqual(git(remote,'rev-parse','main').stdout, before)
            self.assertTrue(calls)

    def test_native_refresh_replaces_stale_hostvars_then_original_strict_guard_passes(self):
        source, _, _, route, resources, caller = fixture()
        selected = source.row['name']
        document = yaml.safe_load((ROOT/'deploy-selected-use-cases.yml').read_text())[0]
        refresh = next(task for task in document['tasks'][0]['block'] if 'ansible.builtin.add_host' in task)
        guard = yaml.safe_load((ROOT/'tasks/aap-instance-select.yml').read_text())[2]
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            values = deepcopy(caller); values['keep'] = 'unchanged'
            inventory = {'all': {'hosts': {selected: values, 'unrelated': {'keep': 'foreign'}}}}
            (work/'inventory.yml').write_text(yaml.safe_dump(inventory))
            play = [{'hosts':'localhost', 'connection':'local', 'gather_facts':False,
                'vars': {'aap_instance_key':selected,
                         'aap_registered_target': {'instance_route':route, 'instance_resources':resources},
                         'aap_selected_inventory_metadata': {'inventory_host':selected,
                             'metadata_verified':True, 'vm_resource':dict(caller['vm_resource'],
                                 supplemental_interfaces=resources['aap']['supplemental_interfaces'])}},
                'tasks': [
                    {'block':[deepcopy(guard)], 'rescue':[{'ansible.builtin.set_fact':{'original_refused':True}}]},
                    {'ansible.builtin.assert':{'that':'original_refused | default(false)'}},
                    refresh, guard,
                    {'ansible.builtin.assert':{'that':[
                        'hostvars[aap_instance_key].keep == "unchanged"',
                        'hostvars.unrelated.keep == "foreign"',
                        'hostvars[aap_instance_key].vm_resource.supplemental_interfaces == aap_registered_target.instance_resources.aap.supplemental_interfaces']}}
                ]}]
            (work/'play.yml').write_text(yaml.safe_dump(play, sort_keys=False))
            environment = dict(os.environ, ANSIBLE_FILTER_PLUGINS=str(ROOT/'filter_plugins'),
                ANSIBLE_LOCAL_TEMP=str(work/'local'), ANSIBLE_REMOTE_TEMP=str(work/'remote'),
                ANSIBLE_NOCOLOR='1')
            process = subprocess.run([sys.executable, '-B', '-c',
                'from ansible.cli.playbook import main; main()', '-i', str(work/'inventory.yml'),
                str(work/'play.yml')], cwd=work, env=environment, text=True, capture_output=True, timeout=60)
            self.assertEqual(process.returncode, 0, process.stdout+'\n'+process.stderr)
            self.assertIn('rescued=1', process.stdout)

    def test_launcher_refresh_precedes_existing_strict_guard_and_has_no_new_privileges(self):
        data = yaml.safe_load((ROOT/'deploy-selected-use-cases.yml').read_text())[0]
        tasks = data['tasks'][0]['block']
        repair = next(i for i,t in enumerate(tasks) if t.get('aap_publish_instance_keys',{}).get('operation') == 'reconcile_inventory_metadata')
        refresh = next(i for i,t in enumerate(tasks) if 'ansible.builtin.add_host' in t)
        authentication = next(i for i,t in enumerate(tasks) if t.get('ansible.builtin.include_tasks') == 'tasks/cac-api-auth.yml')
        retention = next(i for i,t in enumerate(tasks) if 'aap_selected_target_auth' in t.get('ansible.builtin.set_fact',{}))
        guard = next(i for i,t in enumerate(tasks) if t.get('ansible.builtin.include_tasks') == 'tasks/aap-instance-select.yml')
        self.assertLess(authentication, retention); self.assertLess(retention, repair)
        self.assertLess(repair, refresh); self.assertLess(refresh, guard)
        self.assertEqual(set(tasks[refresh]['ansible.builtin.add_host']), {'name','vm_resource'})
        selection = yaml.safe_load((ROOT/'tasks/aap-instance-select.yml').read_text())
        self.assertIn('aap_inventory_route_matches', selection[2]['ansible.builtin.assert']['that'])
        self.assertNotIn('reconcile_inventory_metadata', (ROOT/'deploy-cac-project.yml').read_text())
        self.assertNotIn('reconcile_inventory_metadata', (ROOT/'action_plugins/aap_read_instance.py').read_text())

    def test_native_source_launcher_preserves_self_target_and_legacy_readonly_paths(self):
        source, _, _, route, resources, caller = fixture()
        source_tasks = yaml.safe_load((ROOT/'deploy-selected-use-cases.yml').read_text())[0]['tasks'][0]['block']
        verification = next(task for task in source_tasks if task['name'] == 'Require the credential to identify the actual running source job')
        retention = next(task for task in source_tasks if 'aap_selected_target_auth' in task.get('ansible.builtin.set_fact',{}))
        repair = next(task for task in source_tasks if task.get('aap_publish_instance_keys',{}).get('operation') == 'reconcile_inventory_metadata')
        refresh = next(task for task in source_tasks if 'ansible.builtin.add_host' in task)
        guard = yaml.safe_load((ROOT/'tasks/aap-instance-select.yml').read_text())[2]
        for behavior in ('self', 'legacy_absent', 'legacy_null', 'malformed_legacy', 'self_conflict'):
            with self.subTest(behavior=behavior), tempfile.TemporaryDirectory() as directory:
                work = Path(directory); (work/'action_plugins').mkdir()
                (work/'action_plugins/aap_publish_instance_keys.py').write_text('''from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail
class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        raise AnsibleActionFail('Unexpected metadata mutation on a read-only compatibility path')
''')
                values = deepcopy(caller); values['keep'] = 'unchanged'
                selected = source.row['name'] if behavior.startswith('self') else route['vm_name']
                if behavior.startswith('self'):
                    values['vm_resource']['supplemental_interfaces'] = resources['aap']['supplemental_interfaces']
                elif behavior == 'legacy_absent':
                    del values['vm_resource']
                else:
                    values['vm_resource'] = None if behavior == 'legacy_null' else []
                if behavior == 'self_conflict':
                    values['vm_resource']['uuid'] = '99999999-2222-3333-4444-555555555555'
                (work/'inventory.yml').write_text(yaml.safe_dump({'all': {'hosts': {selected:values}}}))
                # Exercise normalization too: same receiver with default-port spelling remains self-target.
                same = route['aap_hostname'].upper() + ':443/'
                source_origin = same if behavior.startswith('self') else source.origin
                variables = {'aap_instance_key':selected,
                    'awx_job_id':123, 'awx_job_template_id':152, 'awx_project_revision':'a'*40,
                    'aap_selected_source_job': {'json':source.job},
                    'aap_selected_source_auth': {'hostname':source_origin},
                    'cac_api_auth': {'hostname':route['aap_hostname']},
                    'aap_registered_target': {'instance_route':route, 'instance_resources':resources}}
                tasks = [verification, retention, repair, refresh,
                    {'ansible.builtin.assert':{'that':[
                        'aap_selected_inventory_metadata is skipped',
                        'hostvars[aap_instance_key].keep == "unchanged"']}}, guard]
                (work/'play.yml').write_text(yaml.safe_dump([{'hosts':'localhost', 'connection':'local',
                    'gather_facts':False, 'vars':variables, 'tasks':tasks}], sort_keys=False))
                environment = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(work/'local'),
                    ANSIBLE_REMOTE_TEMP=str(work/'remote'), ANSIBLE_NOCOLOR='1',
                    ANSIBLE_FILTER_PLUGINS=str(ROOT/'filter_plugins'),
                    ANSIBLE_ACTION_PLUGINS=str(work/'action_plugins'))
                process = subprocess.run([sys.executable, '-B', '-c',
                    'from ansible.cli.playbook import main; main()', '-i', str(work/'inventory.yml'),
                    str(work/'play.yml')], cwd=work, env=environment, text=True, capture_output=True, timeout=60)
                output = process.stdout+'\n'+process.stderr
                self.assertNotIn('Unexpected metadata mutation', output)
                if behavior in ('malformed_legacy', 'self_conflict'):
                    self.assertNotEqual(process.returncode, 0, output)
                    self.assertIn('Require existing AAP inventory identity', output)
                else:
                    self.assertEqual(process.returncode, 0, output)
                    self.assertIn('skipped=2', output)


if __name__ == '__main__':
    unittest.main()
