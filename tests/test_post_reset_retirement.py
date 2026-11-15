"""Prove native reset provenance and exact metadata-only retirement boundaries."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import uuid

import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.vault import VaultLib, VaultSecret
from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail

from test_instance_keys import retirement_fixture, application_capture, FakeRetirementSource

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('post_reset_guard_test', ROOT / 'filter_plugins/aap_post_reset_retirement.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def public_keys(label):
    return [kind + ' ' + base64.b64encode((label + kind).encode()).decode()
            for kind in ('ssh-rsa', 'ecdsa-sha2-nistp256', 'ssh-ed25519')]


def fixtures():
    context, _, main, shared, hactar, allocation = retirement_fixture()
    shared['host_inventory_configuration']['hosts'] = [row for row in shared['host_inventory_configuration']['hosts']
        if row['name'] != 'other-v08']
    for group in shared['host_inventory_configuration']['groups']:
        group['hosts'] = [name for name in group['hosts'] if name != 'other-v08']
    pin = context['route']['hypervisor']
    guests = [dict(role=guest['role'], name=guest['name'], uuid=guest['metadata']['uuid'], disk=guest['metadata']['disk'])
              for guest in context['guests']]
    for index, role in enumerate(sorted(guard.WINDOWS_ROLES), 1):
        name = 'win%d-v07' % index
        address = '192.168.70.%d' % (100 + index)
        identity = '%08d-2222-3333-4444-555555555555' % (100 + index)
        guest = dict(kind='windows', vm_name=name, instance_name=context['route']['vm_name'], uuid=identity,
            disk='/opt/vms/win-' + name + '-clone.disk.qcow2', hypervisor_machine_id=pin['machine_id'], verified=True,
            computer_name=name.upper(), computer_uuid=identity, address=address, winrm_certificate_validated=True,
            interfaces=[dict(network='isolated', bridge='vmbr0', mac='52:54:00:12:35:%02d' % index,
                             address=address, dns_name=name + '.example.invalid')])
        shared['host_inventory_configuration']['hosts'].append(dict(name=name, inventory='Shared', variables={
            'ansible_host': address, 'hypervisor_host': 'fixture-hypervisor', 'vm_uuid': identity,
            'computer_name': name.upper(), 'computer_uuid': identity, 'vm_resource': guest}))
        shared['host_inventory_configuration']['groups'][0]['hosts'].append(name)
        guests.append(dict(role=role, name=name, uuid=identity, disk=guest['disk']))
    application = application_capture(context)
    application['aiops_instances'][context['route']['vm_name']]['zabbix']['configuration'] = {
        'firewall': {'guest_host_clients': []}}
    resources = guard.decommission.resources(context['route'], 'example.invalid', '/opt/vms',
        {row['role']: row['metadata'] for row in context['guests']})
    paths = resources['nginx'] + resources['website_paths'] + [resources['authority']]
    for name in resources['certificates']:
        paths.extend(['/etc/letsencrypt/live/' + name, '/etc/letsencrypt/archive/' + name,
                      '/etc/letsencrypt/renewal/' + name + '.conf'])
    expected = dict(schema_version=1, instance_name=context['route']['vm_name'], previous_pin=pin,
        aap_hostname=context['route']['aap_hostname'], public_zone='example.invalid', provider_server_number=12345,
        hardware=dict(product_uuid='11112222-3333-4444-5555-666677778888', board_serial='fixture-board'),
        previous_storage_uuids=['aaaa-bbbb'], guests=sorted(guests, key=lambda row: row['role']), paths=sorted(paths),
        rich_rules=[dict(zone='libvirt', rule=rule) for rule in sorted(context['removed_rules'])])
    client = FakeRetirementSource(main, shared, hactar)
    return context, main, shared, hactar, allocation, application, expected, client


def job_fixture():
    context, main, _, _, _, _, expectation, _ = fixtures()
    expectation['previous_pin']['host_keys'] = public_keys('old')
    settings = dict(expectation=expectation, verification=dict(template_id=70, project_id=90,
                    inventory_id=12, project_revision='a' * 40))
    now = datetime.now(timezone.utc)
    checked = now - timedelta(seconds=10)
    host_keys = public_keys('new')
    fingerprints = sorted('SHA256:' + base64.b64encode(hashlib.sha256(base64.b64decode(x.split()[1])).digest()).decode().rstrip('=')
                          for x in host_keys)
    actual = dict(machine_id='2' * 32, host_keys=host_keys, hardware=expectation['hardware'],
        target_ipv4='192.0.2.10', source_ipv4='192.0.2.20', all_ipv4_addresses=['192.0.2.10'],
        provider_identity=dict(server_number=12345, host_fingerprints=fingerprints, image='Rocky Linux 9 base'))
    paths = sorted(set(expectation['paths'] + [row['disk'] for row in expectation['guests']] + ['/opt/vms']))
    evidence = dict(schema_version=1, complete=True, checked_at=checked.isoformat(), machine_id=actual['machine_id'],
        host_keys=host_keys, hardware=expectation['hardware'],
        paths=[dict(path=path, exists=False, symlink_ancestor=False) for path in paths],
        guest_inventory=dict(saved=0, runtime=0, running=0), blockdevices=dict(blockdevices=[dict(name='/dev/vda')]),
        mounts=dict(filesystems=[dict(target='/')]), nftables=dict(nftables=[]),
        firewalld_xml=[dict(path=x, exists=False, files=[]) for x in
            ['/etc/firewalld', '/usr/lib/firewalld/zones', '/usr/lib/firewalld/policies']],
        legacy_ipv4_tables='', iptables_save='')
    proof = dict(schema_version=1, verified=True, expectation=expectation,
        expectation_sha256=guard.digest(expectation), evidence=evidence, actual=actual,
        source_job=dict(id=100, template_id=70, project_revision='a' * 40), checked_at=checked.isoformat(),
        remote_checked_at=checked.isoformat())
    job = dict(id=100, status='successful', failed=False, job_template=70, project=90, inventory=12,
        scm_revision='a' * 40, processed_events=True, started=(now - timedelta(seconds=20)).isoformat(),
        finished=(now - timedelta(seconds=5)).isoformat(),
        artifacts=dict(hactar_recovery_target_details=dict(retirement_absence=proof)))
    class Source:
        def __init__(self): self.calls = []
        def request(self, method, path):
            self.calls.append((method, path))
            assert (method, path) == ('GET', 'jobs/100/')
            return deepcopy(job)
    return settings, job, proof, now, Source()


class PostResetRetirementTests(unittest.TestCase):
    def test_existing_publisher_retires_all_nine_through_real_encrypted_git_and_source_readback(self):
        self.publisher_retirement()

    def test_consumed_host_generation_is_retained_as_retired_history_after_native_cleanup(self):
        self.publisher_retirement(marked_generation=True)

    def publisher_retirement(self, marked_generation=False):
        context, main, shared, hactar, allocation, application, expected, source = fixtures()
        reservation_key = 'selected-request'
        if marked_generation:
            installation = 'f' * 64
            record = allocation['aap_vm_allocation']['reservations'].pop(reservation_key)
            record['host_installation_id'] = installation
            reservation_key = str(uuid.uuid5(uuid.NAMESPACE_URL, 'aap-host-install:' + installation))
            allocation['aap_vm_allocation']['reservations'][reservation_key] = record
        settings, native_job, proof, _, _ = job_fixture()
        settings['expectation'] = deepcopy(expected)
        settings['verification']['inventory_id'] = 2
        native_job['inventory'] = 2
        proof['expectation'] = deepcopy(expected)
        proof['expectation_sha256'] = guard.digest(expected)
        expected_paths = sorted(set(expected['paths'] + [row['disk'] for row in expected['guests']] + ['/opt/vms']))
        proof['evidence']['paths'] = [dict(path=path, exists=False, symlink_ancestor=False) for path in expected_paths]
        hactar_row = next(row for row in source.hosts.values() if row['inventory'] == 2)
        fresh_hactar = guard.keys.inventory_variables(hactar_row)
        fresh_hactar.update(machine_id=proof['actual']['machine_id'], host_keys=proof['actual']['host_keys'],
            ansible_user='root', ansible_port='22', replacement_only={'keep': True},
            isolation_policy=deepcopy(context['previous_policy']), hactar_isolation_policy=deepcopy(context['previous_policy']))
        hactar_row['variables'] = json.dumps(fresh_hactar)
        main['aap_post_reset_retirement'] = settings
        original_request = source.request
        original_rows = source.rows
        def rows(path):
            return [] if path.startswith('jobs/') else original_rows(path)
        source.rows = rows
        failure = {'enabled': False, 'deletes': 0}
        def request(method, path, body=None):
            if (method, path) == ('GET', 'jobs/100/'):
                return deepcopy(native_job)
            result = original_request(method, path, body)
            if method == 'DELETE' and failure['enabled']:
                failure['deletes'] += 1
                if failure['deletes'] == 2:
                    raise RuntimeError('fixture lost response after actual deletion')
            return result
        source.request = request
        secret = VaultSecret(b'fixture-retirement-password')
        vault = VaultLib([('cac', secret)])
        spec = importlib.util.spec_from_file_location('post_reset_publisher_integration', ROOT / 'action_plugins/aap_publish_instance_keys.py')
        publisher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(publisher)
        real_run = subprocess.run
        documents = {'vaults/cac/aap_autodeploy_configascode-cac-vault.yml': main,
            'cac/host_inventory.yml': shared, 'cac/hactar_recovery.yml': hactar,
            'state/aap_vm_allocations_vault.yml': allocation}
        with tempfile.TemporaryDirectory(prefix='post-reset-publisher-test-') as temporary:
            directory = Path(temporary)
            seed, remote, project = [directory / name for name in ('seed', 'remote.git', 'project')]
            seed.mkdir(); project.mkdir()
            def git(path, *args):
                return real_run(['git', '-C', str(path), *args], capture_output=True, text=True, check=True)
            real_run(['git', 'init', '--bare', '--initial-branch=main', str(remote)], capture_output=True, check=True)
            git(seed, 'init', '--initial-branch=main')
            for name, value in documents.items():
                path = seed / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(vault.encrypt(yaml.dump(value, Dumper=publisher.vault_yaml.VaultDumper), vault_id='cac'))
            git(seed, 'add', '.')
            git(seed, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'Seed encrypted fixture')
            git(seed, 'remote', 'add', 'origin', str(remote)); git(seed, 'push', 'origin', 'main')
            (project / 'myvars').write_bytes(vault.encrypt(yaml.safe_dump({'git_url':
                'https://git.example.invalid/fixture-owner/autodeploy.git'}), vault_id='cac'))
            loader = DataLoader(); loader.set_vault_secrets([('cac', secret)])
            def redirected(command, *args, **kwargs):
                command = [str(remote) if item == 'https://git.example.invalid/fixture-owner/aap_autodeploy_configascode-secrets.git'
                           else item for item in command]
                self.assertFalse(any(item.startswith(('https://', 'http://', 'git@')) for item in command))
                return real_run(command, *args, **kwargs)
            ownership = guard.keys.source_related_resources(source, shared, allocation['aap_vm_allocation'],
                context['route']['vm_name'], application)
            ownership.update(source_job_id='123', source_project_revision='a' * 40)
            variables = dict(awx_job_id=123, awx_job_template_id=456, awx_project_revision='a' * 40,
                aap_registered_target=dict(related_resource_proof=ownership),
                aap_isolation_app_capture=dict(ansible_facts=application))
            plugin = publisher.ActionModule.__new__(publisher.ActionModule)
            args = dict(instance_name=context['route']['vm_name'], record=dict(target=context['route']['aap_hostname']),
                        organization='Example', operation='post_reset_inspect', post_reset_verification_job=100)
            plugin._task = SimpleNamespace(args=args, check_mode=False); plugin._loader = loader
            with mock.patch.object(ActionBase, 'run', return_value={}), \
                    mock.patch.object(publisher.ActionModule, '_project_root', return_value=project), \
                    mock.patch.object(publisher, 'SourceClient', return_value=source), \
                    mock.patch.object(publisher.subprocess, 'run', side_effect=redirected), \
                    mock.patch.dict(os.environ, {'CAC_GIT_TOKEN': 'fixture-writer-never-print'}):
                original_head = git(remote, 'rev-parse', 'main').stdout
                wrong_hactar = dict(fresh_hactar, machine_id='4' * 32)
                hactar_row['variables'] = json.dumps(wrong_hactar)
                with self.assertRaises(AnsibleActionFail):
                    plugin.run(task_vars=variables)
                self.assertEqual(git(remote, 'rev-parse', 'main').stdout, original_head)
                self.assertFalse(source.calls)
                hactar_row['variables'] = json.dumps(fresh_hactar)
                inspected = plugin.run(task_vars=variables)
                self.assertTrue(inspected['reset_verified'])
                self.assertEqual(git(remote, 'rev-parse', 'main').stdout, original_head)
                self.assertFalse(source.calls)
                args['operation'] = 'retire'
                failure['enabled'] = True
                with self.assertRaises(AnsibleActionFail):
                    plugin.run(task_vars=variables)
                # Even a lost DELETE acknowledgement cannot discard the nine
                # durable canonical owners or original policy before reconciliation.
                held = publisher.vault_yaml.load_repository_yaml(vault.decrypt(
                    git(remote, 'show', 'main:cac/host_inventory.yml').stdout.encode()))
                self.assertEqual(held, shared)
                held_hactar = publisher.vault_yaml.load_repository_yaml(vault.decrypt(
                    git(remote, 'show', 'main:cac/hactar_recovery.yml').stdout.encode()))
                self.assertEqual(held_hactar, hactar)
                held_main = publisher.vault_yaml.load_repository_yaml(vault.decrypt(git(remote, 'show',
                    'main:vaults/cac/aap_autodeploy_configascode-cac-vault.yml').stdout.encode()))
                self.assertEqual(held_main['autodeploy_configuration']['inventories'], main['autodeploy_configuration']['inventories'])
                held_allocation = publisher.vault_yaml.load_repository_yaml(vault.decrypt(git(remote, 'show',
                    'main:state/aap_vm_allocations_vault.yml').stdout.encode()))
                self.assertTrue(held_allocation['aap_vm_allocation']['reservations'][reservation_key]['decommissioned'])
                self.assertEqual(held_allocation['aap_vm_allocation']['next_number'], allocation['aap_vm_allocation']['next_number'])
                # A fresh actual job first rereads ownership and reconciles the
                # already-completed deletes; it never resubmits uncertain writes.
                failure['enabled'] = False
                ownership = guard.keys.source_related_resources(source, held,
                    held_allocation['aap_vm_allocation'], context['route']['vm_name'], application)
                ownership.update(source_job_id='124', source_project_revision='a' * 40)
                variables.update(awx_job_id=124, aap_registered_target=dict(related_resource_proof=ownership))
                fresh = publisher.ActionModule.__new__(publisher.ActionModule)
                fresh._task = SimpleNamespace(args=deepcopy(args), check_mode=False); fresh._loader = loader
                completed = fresh.run(task_vars=variables)
            self.assertTrue(completed['published'])
            saved = {}
            for name in documents:
                saved[name] = publisher.vault_yaml.load_repository_yaml(vault.decrypt(git(remote, 'show', 'main:' + name).stdout.encode()))
            final_allocation = saved['state/aap_vm_allocations_vault.yml']['aap_vm_allocation']
            self.assertEqual(final_allocation['next_number'], allocation['aap_vm_allocation']['next_number'])
            if marked_generation:
                self.assertEqual(final_allocation['reservations'][reservation_key],
                    dict(allocation['aap_vm_allocation']['reservations'][reservation_key], decommissioned=True))
            else:
                self.assertNotIn(reservation_key, final_allocation['reservations'])
            self.assertEqual(final_allocation['reservations']['other-request'], allocation['aap_vm_allocation']['reservations']['other-request'])
            selected_names = {row['name'] for row in expected['guests']}
            final_hosts = saved['cac/host_inventory.yml']['host_inventory_configuration']['hosts']
            self.assertFalse(any(row['name'] in selected_names and row['inventory'] == 'Shared' for row in final_hosts))
            self.assertTrue(any(row['inventory'] == 'Other' for row in final_hosts))
            self.assertFalse(any(row['name'] in selected_names and row['inventory'] == 1 for row in source.hosts.values()))
            final_hactar = guard.keys.inventory_variables(source.hosts[hactar_row['id']])
            for field in fresh_hactar:
                if field not in ('isolation_policy', 'hactar_isolation_policy', 'firewall_additional_zone_rules'):
                    self.assertEqual(final_hactar[field], fresh_hactar[field])
            old_shared = next(row for row in source.hosts.values() if row['inventory'] == 1
                and row['name'] == 'fixture-hypervisor')
            old_variables = guard.keys.inventory_variables(old_shared)
            self.assertEqual(old_variables['machine_id'], context['route']['hypervisor']['machine_id'])
            self.assertEqual(old_variables['host_keys'], context['route']['hypervisor']['host_keys'])

    def test_replacement_alias_rejects_wrong_keys_machine_inventory_or_old_shared_identity_drift(self):
        for variant in ('keys', 'machine', 'inventory', 'missing_inventory', 'owner', 'old_shared'):
            with self.subTest(variant=variant):
                context, main, shared, hactar, allocation, application, expected, source = fixtures()
                settings, _, proof, _, _ = job_fixture()
                settings['expectation'] = deepcopy(expected)
                settings['verification']['inventory_id'] = 2
                proof['expectation'] = deepcopy(expected)
                row = next(row for row in source.hosts.values() if row['inventory'] == 2)
                values = guard.keys.inventory_variables(row)
                values.update(machine_id=proof['actual']['machine_id'], host_keys=proof['actual']['host_keys'],
                    ansible_user='root', ansible_port=22, replacement_only='preserve')
                if variant == 'keys': values['host_keys'] = public_keys('wrong')
                if variant == 'machine': values['machine_id'] = '3' * 32
                row['variables'] = json.dumps(values)
                if variant == 'inventory': settings['verification']['inventory_id'] = 12
                if variant == 'missing_inventory': del source.inventories[2]
                if variant == 'owner':
                    selected = next(row for row in source.hosts.values() if row['name'] == expected['guests'][1]['name'])
                    changed = guard.keys.inventory_variables(selected)
                    changed['vm_resource']['uuid'] = '99999999-2222-3333-4444-555555555555'
                    selected['variables'] = json.dumps(changed)
                if variant == 'old_shared':
                    selected = next(row for row in source.hosts.values() if row['name'] == 'fixture-hypervisor')
                    changed = guard.keys.inventory_variables(selected)
                    changed['machine_id'] = proof['actual']['machine_id']
                    selected['variables'] = json.dumps(changed)
                with self.assertRaises(Exception):
                    combined, _, _ = guard.combined_context(main, shared, hactar, allocation, source,
                        context['route']['vm_name'], application, expected)
                    desired = [guard.keys.retire_inventory_capture(capture, combined, kind)
                        for kind, capture in [('shared', shared), ('autodeploy', main), ('hactar', hactar)]]
                    guard.source_operations(source, *desired, combined, settings, proof)
                self.assertFalse(any(method != 'GET' for method, _ in source.calls))

    def test_current_nine_guest_owners_compose_existing_helpers_without_mutating_inputs(self):
        context, main, shared, hactar, allocation, app, expected, client = fixtures()
        before = deepcopy((main, shared, hactar, allocation, app))
        combined, proof, resources = guard.combined_context(main, shared, hactar, allocation, client,
            context['route']['vm_name'], app, expected)
        self.assertEqual(len(combined['guests']), 9)
        self.assertEqual({row['name'] for row in combined['guests']}, {row['name'] for row in expected['guests']})
        self.assertEqual(resources['version'], 'v07')
        self.assertEqual((main, shared, hactar, allocation, app), before)
        self.assertFalse(any(method != 'GET' for method, _ in client.calls))

    def test_changed_owner_missing_application_or_guessed_path_is_refused(self):
        for variant in ('owner', 'missing_app', 'path', 'rich_rule', 'omitted_windows'):
            with self.subTest(variant=variant):
                context, main, shared, hactar, allocation, app, expected, client = fixtures()
                if variant == 'owner': expected['guests'][0]['uuid'] = '99999999-2222-3333-4444-555555555555'
                if variant == 'missing_app': app['aiops_instances'].clear()
                if variant == 'path': expected['paths'].append('/etc/nginx/foreign')
                if variant == 'rich_rule': expected['rich_rules'] = []
                if variant == 'omitted_windows': expected['guests'].pop()
                with self.assertRaises(Exception):
                    guard.combined_context(main, shared, hactar, allocation, client,
                        context['route']['vm_name'], app, expected)
                self.assertFalse(any(method != 'GET' for method, _ in client.calls))

    def test_real_native_job_binding_is_read_instead_of_accepting_a_caller_proof(self):
        settings, _, proof, now, source = job_fixture()
        self.assertEqual(guard.verified_job(source, 100, settings, now=now), proof)
        self.assertEqual(source.calls, [('GET', 'jobs/100/')])

    def test_remote_clock_offset_preserves_raw_time_without_loosening_controller_attestation(self):
        for seconds in (-3600, 3600):
            with self.subTest(remote_offset=seconds):
                settings, _, proof, now, source = job_fixture()
                remote = (datetime.fromisoformat(proof['checked_at']) + timedelta(seconds=seconds)).isoformat()
                proof['remote_checked_at'] = proof['evidence']['checked_at'] = remote
                returned = guard.verified_job(source, 100, settings, now=now)
                self.assertEqual(returned['remote_checked_at'], remote)
                self.assertEqual(returned['evidence']['checked_at'], remote)
                self.assertEqual(returned['checked_at'], proof['checked_at'])
        for failure in ('mismatched_remote', 'naive_remote', 'stale_controller', 'future_controller'):
            with self.subTest(failure=failure):
                settings, job, proof, now, source = job_fixture()
                if failure == 'mismatched_remote':
                    proof['remote_checked_at'] = (now + timedelta(hours=1)).isoformat()
                if failure == 'naive_remote':
                    proof['remote_checked_at'] = proof['evidence']['checked_at'] = now.replace(tzinfo=None).isoformat()
                if failure == 'stale_controller':
                    proof['checked_at'] = (now - timedelta(hours=2)).isoformat()
                    job['started'] = (now - timedelta(hours=2, seconds=10)).isoformat()
                    job['finished'] = (now - timedelta(hours=2) + timedelta(seconds=5)).isoformat()
                if failure == 'future_controller':
                    proof['checked_at'] = (now + timedelta(hours=1)).isoformat()
                with self.assertRaises(Exception):
                    guard.verified_job(source, 100, settings, now=now)

    def test_incomplete_stale_wrong_or_nonreplacement_proof_is_rejected(self):
        for variant in ('running', 'template', 'project', 'revision', 'inventory', 'events', 'stale',
                        'same_machine', 'old_key', 'provider', 'incomplete', 'surviving_path', 'surviving_guest',
                        'missing_evidence', 'wrong_digest', 'future'):
            with self.subTest(variant=variant):
                settings, job, proof, now, source = job_fixture()
                if variant == 'running': job['status'] = 'running'
                if variant == 'template': job['job_template'] += 1
                if variant == 'project': job['project'] += 1
                if variant == 'revision': job['scm_revision'] = 'b' * 40
                if variant == 'inventory': job['inventory'] += 1
                if variant == 'events': job['processed_events'] = False
                if variant == 'stale': now += timedelta(hours=1)
                if variant == 'same_machine': proof['actual']['machine_id'] = settings['expectation']['previous_pin']['machine_id']
                if variant == 'old_key': proof['actual']['host_keys'][0] = settings['expectation']['previous_pin']['host_keys'][0]
                if variant == 'provider': proof['actual']['provider_identity']['server_number'] += 1
                if variant == 'incomplete': proof['evidence']['complete'] = False
                if variant == 'surviving_path': proof['evidence']['paths'][0]['exists'] = True
                if variant == 'surviving_guest': proof['evidence']['guest_inventory']['running'] = 1
                if variant == 'missing_evidence': proof.pop('evidence')
                if variant == 'wrong_digest': proof['expectation_sha256'] = '0' * 64
                if variant == 'future': job['finished'] = (now + timedelta(seconds=1)).isoformat()
                with self.assertRaises(Exception): guard.verified_job(source, 100, settings, now=now)

    def test_later_target_work_invalidates_proof_but_same_branch_retry_can_reconcile(self):
        settings, _, _, now, source = job_fixture()
        current = dict(id=124, template_id=456, project_revision='b' * 40)
        later = dict(id=123, inventory=12, job_template=456, scm_revision='b' * 40, status='failed',
            extra_vars=json.dumps(dict(aap_post_reset_verification_job=100,
                                       aap_decommission_confirmation=settings['expectation']['instance_name'])))
        source.rows = lambda path: [deepcopy(later)]
        guard.verified_job(source, 100, settings, now=now, retirement_job=current)
        for field, value in [('job_template', 99), ('scm_revision', 'c' * 40), ('status', 'running'),
                             ('extra_vars', '{}')]:
            changed = dict(later, **{field: value})
            source.rows = lambda path: [changed]
            with self.subTest(field=field), self.assertRaises(Exception):
                guard.verified_job(source, 100, settings, now=now, retirement_job=current)
        # An operation launched before the absence proof can still change the
        # host afterward; elapsed ID/time order does not establish its outcome.
        active = dict(id=50, inventory=12, status='running')
        source.rows = lambda path: [active] if 'status__in' in path else []
        with self.assertRaises(Exception):
            guard.verified_job(source, 100, settings, now=now, retirement_job=current)

    def test_post_reset_branch_ends_before_any_old_pin_connection_and_never_claims_guest_stop(self):
        play = yaml.safe_load((ROOT / 'destroy-test-aap.yml').read_text())[0]
        tasks = play['pre_tasks']
        branch = next(index for index, task in enumerate(tasks) if task.get('ansible.builtin.include_tasks') == 'tasks/decommission-post-reset.yml')
        old_pin = next(index for index, task in enumerate(tasks) if task.get('ansible.builtin.include_tasks') == 'tasks/aap-hypervisor-identity.yml')
        self.assertLess(branch, old_pin)
        self.assertEqual(tasks[branch + 1]['ansible.builtin.meta'], 'end_play')
        source = (ROOT / 'tasks/decommission-post-reset.yml').read_text()
        self.assertNotIn('aap_decommission_selected_guests_stopped', source)
        self.assertNotIn('virsh', source)
        self.assertNotIn('aap-hypervisor-identity', source)
        self.assertNotIn('aap-isolation-prepare', source)


if __name__ == '__main__': unittest.main()
