"""Exercise native encrypted source loading and CaC-only effective composition."""
from copy import deepcopy
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml
from ansible.parsing.vault import VaultLib, VaultSecret

ROOT = Path(__file__).resolve().parents[1]


def owner(number, machine='1' * 32):
    guest = {'schema_version': 1, 'instance_name': 'fixture-%s' % number,
             'instance_number': number, 'vm_name': 'zabbix-v%s' % number,
             'uuid': '01234567-89ab-cdef-0123-%012d' % number,
             'disk': '/opt/vms/zabbix-v%s.disk.qcow2' % number,
             'network': 'isolated', 'bridge': 'virbr0', 'address': '192.168.70.%s' % number,
             'mac': '52:54:00:00:00:%02x' % number,
             'hypervisor_machine_id': machine, 'verified': True}
    row = {'bridge': guest['bridge'], 'ipv4': guest['address'], 'mac': guest['mac'],
           'destinations': ['192.168.70.1'], 'ports': [443]}
    guest['configuration'] = {'firewall': {'guest_host_clients': [row]}}
    return {'zabbix': guest}


class ApplicationPolicyTests(unittest.TestCase):
    def test_fixed_private_source_checkout_uses_only_scoped_runtime_auth_and_cleans_up(self):
        """Exercise the actual Git task with real Git against an isolated repository."""
        for token in ('synthetic-hactar-reader-canary', '', 'invalid\nheader'):
            with self.subTest(token_present=bool(token)), tempfile.TemporaryDirectory(prefix='private-source-fixture-') as temporary:
                root = Path(temporary)
                origin = root / 'origin'
                origin.mkdir()
                (origin / 'source').write_text('reviewed task source\n')
                for arguments in (['init', '-q', '-b', 'main'], ['add', '.'],
                                  ['-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                                   'commit', '-q', '-m', 'Prepare source fixture']):
                    subprocess.run(['git', '-C', str(origin), *arguments], check=True,
                                   text=True, capture_output=True, timeout=15)
                revision = subprocess.check_output(['git', '-C', str(origin), 'rev-parse', 'HEAD'], text=True).strip()
                trace = root / 'git-environment'
                executable = root / 'git'
                # The fixed production URL remains in the actual module task;
                # this test-only executable substitutes a local bare source.
                executable.write_text('#!' + sys.executable + '\nimport json,os,pathlib,subprocess,sys\n'
                    'args=sys.argv[1:]\n'
                    'fixed="https://github.com/kvegh/hactarconfig.git"\n'
                    'assert all(not x.startswith(("http://","https://")) or x==fixed for x in args)\n'
                    'record={k:v for k,v in os.environ.items() if k.startswith("GIT_CONFIG_") or k=="CAC_GIT_TOKEN"}\n'
                    'pathlib.Path(' + repr(str(trace)) + ').write_text(json.dumps(record))\n'
                    'args=[' + repr(str(origin)) + ' if x==fixed else x for x in args]\n'
                    'raise SystemExit(subprocess.run(["/usr/bin/git",*args]).returncode)\n')
                executable.chmod(0o700)
                tasks = yaml.safe_load((ROOT / 'tasks/aap-isolation-prepare.yml').read_text())
                git_task = next(task for task in tasks if 'ansible.builtin.git' in task)
                self.assertEqual(git_task['ansible.builtin.git']['repo'], 'https://github.com/kvegh/hactarconfig.git')
                git_task['ansible.builtin.git']['executable'] = str(executable)
                tasks = tasks[:next(i for i, task in enumerate(tasks) if task['name'].startswith('Acquire the approved'))]
                variables = {'aap_isolation_hypervisor': {'machine_id': '1' * 32, 'port': 22},
                             'aap_isolation_trust_file': str(root / 'known-hosts'),
                             'aap_hactar_source_revision': revision, 'hactar_source_public_ip': '198.51.100.5',
                             'hactar_source_git_token': token}
                inspect = [
                    {'name': 'Read the actual checkout configuration before cleanup', 'ansible.builtin.slurp': {
                        'src': '{{ aap_isolation_source_workspace.path }}/repository/.git/config'},
                     'register': 'fixture_checkout_config', 'no_log': True},
                    {'name': 'Prove authentication was not persisted in the actual checkout', 'ansible.builtin.assert': {
                        'that': ["'extraheader' not in (fixture_checkout_config.content | b64decode)",
                                 'hactar_source_git_token not in (fixture_checkout_config.content | b64decode)']}, 'no_log': True}]
                play = [{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False, 'vars': variables,
                         'tasks': [{'name': 'Read only the protected fixed source', 'block': tasks + inspect,
                                    'always': [{'name': 'Remove this invocation source checkout',
                                                'ansible.builtin.file': {'path': '{{ aap_isolation_source_workspace.path }}',
                                                                        'state': 'absent'},
                                                'when': 'aap_isolation_source_workspace.path is defined', 'no_log': True}]}]}]
                path = root / 'play.yml'
                path.write_text(yaml.safe_dump(play, sort_keys=False))
                config = root / 'ansible.cfg'; config.write_text('[defaults]\n')
                env = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_LOCAL_TEMP=str(root / 'local'),
                           ANSIBLE_REMOTE_TEMP=str(root / 'remote'), CAC_GIT_TOKEN='synthetic-writer-canary')
                run = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(path)],
                                     env=env, text=True, capture_output=True, timeout=60)
                self.assertNotIn('synthetic-hactar-reader-canary', run.stdout + run.stderr)
                self.assertNotIn('synthetic-writer-canary', run.stdout + run.stderr)
                if not token or '\n' in token:
                    self.assertNotEqual(run.returncode, 0)
                    self.assertFalse(trace.exists(), 'Invalid auth must stop before any Git command')
                    continue
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                observed = json.loads(trace.read_text())
                self.assertEqual(observed['CAC_GIT_TOKEN'], 'synthetic-writer-canary')
                self.assertEqual(observed['GIT_CONFIG_KEY_3'], 'http.https://github.com/kvegh/hactarconfig.git.extraheader')
                self.assertEqual(observed['GIT_CONFIG_VALUE_3'],
                                 'Authorization: Basic ' + base64.b64encode(('x-access-token:' + token).encode()).decode())
                self.assertEqual(observed['GIT_CONFIG_VALUE_0'], '')
                self.assertEqual(observed['GIT_CONFIG_VALUE_1'], 'false')
                self.assertEqual(observed['GIT_CONFIG_VALUE_2'], 'true')

    def test_bootstrap_native_loading_does_not_template_unrelated_base_configuration(self):
        tasks = yaml.safe_load((ROOT / 'tasks/aap-isolation-app-permissions.yml').read_text())
        load = next(task for task in tasks if task['name'].startswith('Load the existing central bootstrap'))
        guard = next(task for task in tasks if task['name'].startswith('Require the already chosen AIOps'))
        app_load = next(task for task in tasks if task['name'].startswith('Load AIOps variables'))
        app_guard = next(task for task in tasks if task['name'] == "Require the selected project's explicit instance namespace")
        self.assertNotIn('name', load['ansible.builtin.include_vars'])
        self.assertNotIn('name', app_load['ansible.builtin.include_vars'])
        self.assertEqual(app_load['register'], 'aap_isolation_app_capture')
        with tempfile.TemporaryDirectory(prefix='bootstrap-native-scope-') as temporary:
            root = Path(temporary)
            bootstrap = {
                'pah_base': 'https://hub.example.invalid',
                'unrelated_pah_remote': '{{ pah_base }}/api/',
                'unrelated_runtime': '{{ unavailable_runtime_setting }}',
                'cac_bootstrap_git_credentials': {'aiops': {
                    'repository_url': 'https://git.example.invalid/fixture/aiops-secrets.git',
                    'token': 'synthetic-bootstrap-reader-canary'}},
                'cac_bootstrap_vault_credentials': {'aiops': {
                    'vault_id': 'cac', 'vault_password': 'synthetic-bootstrap-password-canary'}}}
            plain = yaml.safe_dump(bootstrap).replace(
                'token: synthetic-bootstrap-reader-canary',
                'token: !unsafe "synthetic-bootstrap-reader-canary {{ must_remain_literal }}"')
            plain += 'literal_marker: !unsafe "{{ must_remain_literal }}"\n'
            unused = VaultLib().encrypt(b'synthetic-unused-bootstrap-secret',
                                        VaultSecret(b'synthetic-unattached-key')).decode()
            plain += 'unused_secret: !vault |\n' + ''.join('  ' + line + '\n' for line in unused.splitlines())
            key = root / 'vault-password'
            key.write_bytes(b'synthetic-bootstrap-key')
            key.chmod(0o600)
            encrypted = root / 'central/cac/base_CaC_vault.yml'
            encrypted.parent.mkdir(parents=True)
            encrypted.write_bytes(VaultLib().encrypt(plain, VaultSecret(key.read_bytes()), vault_id='cac'))
            app_plain = yaml.safe_dump({
                'cac_import_metadata': {'project_id': 'aiops-selfhealing-demo'},
                'aiops_instances': {'fixture-17': owner(17)},
                'aiops_eda_organization_name': 'fixture-organization',
                'unused_organization': '{{ aiops_eda_organization_name }}',
                'unused_app_runtime': '{{ unavailable_app_runtime }}'})
            app_plain += 'app_literal: !unsafe "{{ preserve_app_literal }}"\n'
            app_plain += 'unused_secret: !vault |\n' + ''.join('  ' + line + '\n' for line in unused.splitlines())
            app_file = root / 'aiops-variables.yml'
            app_file.write_text(app_plain)
            app_file.chmod(0o600)
            for case in ('old_base_namespace', 'old_app_namespace', 'global_branches'):
                selected_load, selected_guard = deepcopy(load), deepcopy(guard)
                selected_app_load, selected_app_guard = deepcopy(app_load), deepcopy(app_guard)
                if case == 'old_base_namespace':
                    selected_load['ansible.builtin.include_vars']['name'] = 'aap_isolation_bootstrap'
                    selected_guard['ansible.builtin.assert']['that'] = [
                        expression.replace('cac_bootstrap_', 'aap_isolation_bootstrap.cac_bootstrap_')
                        for expression in selected_guard['ansible.builtin.assert']['that']]
                if case == 'old_app_namespace':
                    selected_app_load['ansible.builtin.include_vars']['name'] = 'aap_isolation_app_capture'
                    selected_app_load.pop('register')
                    selected_app_guard['ansible.builtin.assert']['that'] = [
                        expression.replace('cac_import_metadata', 'aap_isolation_app_capture.cac_import_metadata')
                                  .replace('aiops_instances', 'aap_isolation_app_capture.aiops_instances')
                        for expression in selected_app_guard['ansible.builtin.assert']['that']]
                checks = [{'name': 'Preserve literal tagged values without unrelated runtime evaluation',
                           'ansible.builtin.assert': {'that': [
                               'literal_marker == fixture_expected_literal',
                               "literal_marker | type_debug == 'AnsibleUnsafeText'",
                               "cac_bootstrap_git_credentials.aiops.token == ('synthetic-bootstrap-reader-canary ' ~ literal_marker)",
                               "cac_bootstrap_git_credentials.aiops.token | type_debug == 'AnsibleUnsafeText'",
                               "app_literal | type_debug == 'AnsibleUnsafeText'",
                               'aap_hypervisor_pin == fixture_pin', 'aap_instance_key == fixture_instance']},
                           'no_log': True}]
                play = [{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                    'vars': {'aap_isolation_source_workspace': {'path': str(root)},
                             'fixture_expected_literal': yaml.safe_load('"{{ must_remain_literal }}"'),
                             'fixture_pin': {'machine_id': '1' * 32},
                             'aap_hypervisor_pin': {'machine_id': '1' * 32},
                             'aap_instance_key': 'fixture-instance', 'fixture_instance': 'fixture-instance'},
                    'tasks': [selected_load, selected_guard, selected_app_load, selected_app_guard]
                             + (checks if case == 'global_branches' else [])}]
                # The comparison value itself must remain literal as well.
                path = root / 'play.yml'
                text = yaml.safe_dump(play, sort_keys=False)
                text = text.replace("fixture_expected_literal: '{{ must_remain_literal }}'",
                                    'fixture_expected_literal: !unsafe "{{ must_remain_literal }}"')
                path.write_text(text)
                config = root / 'ansible.cfg'
                config.write_text('[defaults]\n')
                env = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_LOCAL_TEMP=str(root / 'local'),
                           ANSIBLE_REMOTE_TEMP=str(root / 'remote'))
                result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,',
                    str(path), '--vault-id', 'cac@' + str(key)], env=env, text=True, capture_output=True, timeout=45)
                self.assertNotIn('synthetic-bootstrap-reader-canary', result.stdout + result.stderr)
                self.assertNotIn('synthetic-bootstrap-password-canary', result.stdout + result.stderr)
                self.assertNotIn('synthetic-unused-bootstrap-secret', result.stdout + result.stderr)
                if case != 'global_branches':
                    self.assertNotEqual(result.returncode, 0)
                    failure = selected_guard if case == 'old_base_namespace' else selected_app_guard
                    self.assertIn(failure['name'], result.stdout)
                else:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_identity_failure_reports_only_booleans_even_with_verbose_native_output(self):
        tasks = yaml.safe_load((ROOT / 'tasks/aap-isolation-app-instance.yml').read_text())
        task = next(task for task in tasks if task['name'] == 'Require the actual UUID, bridge and static guest address')
        for failure in (None, 'uuid_matches', 'bridge_matches', 'static_reservation_matches'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory(prefix='app-identity-output-') as temporary:
                root = Path(temporary)
                guest = {'uuid': 'recorded-uuid-canary', 'bridge': 'recorded-bridge-canary',
                         'mac': '52:54:00:98:76:54', 'address': '192.0.2.199'}
                uuid = guest['uuid'] if failure != 'uuid_matches' else 'different-uuid-canary'
                bridge = guest['bridge'] if failure != 'bridge_matches' else 'different-bridge-canary'
                address = guest['address'] if failure != 'static_reservation_matches' else '192.0.2.200'
                xml = '<network><!--xml-readback-canary--><ip><dhcp><host mac="%s" ip="%s"/></dhcp></ip></network>' % (guest['mac'], address)
                variables = {'aap_isolation_app_owner': {'guest': guest},
                    'aap_isolation_app_uuid': {'stdout': uuid},
                    'aap_isolation_app_network': {'stdout': 'Bridge: ' + bridge + '\nnetwork-readback-canary'},
                    'aap_isolation_app_addresses': {'stdout': xml},
                    'unused_private_key': 'private-key-canary', 'unused_auth_token': 'credential-token-canary'}
                play = root / 'play.yml'
                text = yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local',
                    'gather_facts': False, 'vars': variables, 'tasks': [task]}], sort_keys=False)
                # Registered command stdout is unsafe; preserve that native shape.
                for name in ('aap_isolation_app_uuid', 'aap_isolation_app_network', 'aap_isolation_app_addresses'):
                    text = text.replace(name + ':\n      stdout:', name + ':\n      stdout: !unsafe')
                play.write_text(text)
                config = root / 'ansible.cfg'
                config.write_text('[defaults]\n')
                env = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_LOCAL_TEMP=str(root / 'local'),
                           ANSIBLE_REMOTE_TEMP=str(root / 'remote'))
                result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,',
                    '-vvvv', str(play)], env=env, text=True, capture_output=True, timeout=45)
                output = result.stdout + result.stderr
                for value in (*guest.values(), uuid, bridge, address, 'xml-readback-canary',
                              'network-readback-canary', 'private-key-canary', 'credential-token-canary'):
                    self.assertNotIn(value, output)
                if failure is None:
                    self.assertEqual(result.returncode, 0, output)
                else:
                    self.assertNotEqual(result.returncode, 0)
                    for name in ('uuid_matches', 'bridge_matches', 'static_reservation_matches'):
                        self.assertIn(name + '=' + str(name != failure), output)

    def run_native(self, entries, missing_migration=False, wrong_key=False, wrong_uuid=False, strict=False):
        with tempfile.TemporaryDirectory(prefix='app-policy-fixture-') as temporary, \
             tempfile.TemporaryDirectory(prefix='aap-hactar-source-') as workspace:
            root = Path(temporary)
            work = Path(workspace)
            project = root / 'source'
            (project / 'tasks').mkdir(parents=True)
            central_key = b'synthetic-central-vault'
            app_key = b'synthetic-app-vault'
            unrelated_key = b'synthetic-unattached-vault'
            vault = VaultLib()
            key_file = root / 'vault-password'
            key_file.write_bytes(central_key)
            key_file.chmod(0o600)
            (project / 'myvars').write_bytes(vault.encrypt(yaml.safe_dump({
                'vault_cac_repository_namespace': 'https://git.example.invalid/fixture-owner'}),
                VaultSecret(central_key), vault_id='cac'))
            central = root / 'central-origin'
            app = root / 'app-origin'
            (central / 'cac').mkdir(parents=True)
            (app / 'vaults/cac').mkdir(parents=True)
            bootstrap = {'cac_bootstrap_git_credentials': {'aiops': {
                'repository_url': 'https://git.example.invalid/fixture-owner/aiops-selfhealing-demo-secrets.git',
                'token': 'synthetic-reader-canary'}}, 'cac_bootstrap_vault_credentials': {'aiops': {
                'vault_id': 'cac', 'vault_password': 'wrong-key' if wrong_key else app_key.decode()}}}
            (central / 'cac/base_CaC_vault.yml').write_bytes(vault.encrypt(yaml.safe_dump(bootstrap),
                VaultSecret(central_key), vault_id='cac'))
            entries = deepcopy(entries)
            if missing_migration:
                next(iter(entries.values()))['zabbix']['configuration'].pop('firewall')
            inner = vault.encrypt(b'synthetic-unused-secret', VaultSecret(unrelated_key)).decode()
            plaintext = yaml.safe_dump({'cac_import_metadata': {'project_id': 'aiops-selfhealing-demo'},
                'aiops_instances': entries}, sort_keys=False)
            plaintext += 'aiops_eda_organization_name: fixture-organization\nunused_organization: "{{ aiops_eda_organization_name }}"\nunused_app_runtime: "{{ unavailable_app_runtime }}"\n'
            plaintext += 'unused_literal: !unsafe "{{ must_remain_literal }}"\nunused_secret: !vault |\n'
            plaintext += ''.join('  ' + line + '\n' for line in inner.splitlines())
            (app / 'vaults/cac/aiops-selfhealing-demo-cac-vault.yml').write_bytes(
                vault.encrypt(plaintext, VaultSecret(app_key), vault_id='cac'))
            for repository in (central, app):
                for arguments in (['init', '-q', '-b', 'main'], ['add', '.'],
                                  ['-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                                   'commit', '-q', '-m', 'Prepare encrypted fixture']):
                    subprocess.run(['git', '-C', str(repository), *arguments], check=True,
                                   capture_output=True, text=True, timeout=15)
            trace = root / 'native-probes'
            virsh = root / 'virsh'
            records = {row['zabbix']['vm_name']: row['zabbix'] for row in entries.values()
                       if row.get('zabbix', {}).get('verified') is True}
            virsh.write_text('#!/usr/bin/python3.12\nimport json,pathlib,sys\n'
                'records=' + repr(records) + '\n'
                'with pathlib.Path(' + repr(str(trace)) + ').open("a") as f:f.write(sys.argv[3]+"\\n")\n'
                'operation=sys.argv[3];name=sys.argv[4]\n'
                'guest=records.get(name)\n'
                'if operation=="domuuid":print(' + ('"foreign-uuid"' if wrong_uuid else 'guest["uuid"]') + ')\n'
                'elif operation=="domblklist":print("Type Device Target Source\\n-------------------------\\nfile disk vda "+guest["disk"])\n'
                'elif operation=="domiflist":print("Interface Type Source Model MAC\\n--------------------------------\\n- network "+guest["network"]+" virtio "+guest["mac"])\n'
                'elif operation=="net-info":print("Bridge: virbr0")\n'
                'elif operation=="net-dumpxml":print("<network><ip><dhcp>"+"".join("<host mac=\\\""+row["mac"]+"\\\" ip=\\\""+row["address"]+"\\\"/>" for row in records.values())+"</dhcp></ip></network>")\n'
                'else:raise SystemExit(1)\n')
            virsh.chmod(0o700)
            instance_tasks = yaml.safe_load((ROOT / 'tasks/aap-isolation-app-instance.yml').read_text())
            for task in instance_tasks:
                if 'ansible.builtin.command' in task:
                    argv = task['ansible.builtin.command']['argv']
                    if isinstance(argv, list):
                        argv[0] = str(virsh)
                    else:
                        task['ansible.builtin.command']['argv'] = argv.replace("['virsh',", '[' + repr(str(virsh)) + ',')
            (project / 'tasks/aap-isolation-app-instance.yml').write_text(yaml.safe_dump(instance_tasks, sort_keys=False))
            tasks = yaml.safe_load((ROOT / 'tasks/aap-isolation-app-permissions.yml').read_text())
            git_tasks = [task for task in tasks if 'ansible.builtin.git' in task]
            git_tasks[0]['ansible.builtin.git']['repo'] = str(central)
            git_tasks[1]['ansible.builtin.git']['repo'] = str(app)
            base = {'bridges': ['virbr0'], 'dns_bridges': ['virbr0'],
                    'protected_ipv4': ['198.51.100.5'], 'guest_host_clients': []}
            base_desired = deepcopy(base)
            base_desired['released_clients'] = [{'bridge': 'virbr0', 'ipv4': '192.168.70.2', 'mac': '52:54:00:00:00:02'}]
            desired_file = root / 'effective-policy'
            hactar = root / 'hactar/playbooks/tasks'
            hactar.mkdir(parents=True)
            (hactar / 'replacement-isolation-validate.yml').write_text(yaml.safe_dump([
                {'name': 'Validate complete synthetic policy', 'ansible.builtin.assert': {
                    'that': ['hactar_isolation_policy is mapping', 'hactar_isolation_policy.protected_ipv4 | length > 0']}}]))
            (hactar / 'replacement-isolation-readback.yml').write_text(yaml.safe_dump([
                {'name': 'Simulate native drift including a deleted grant', 'ansible.builtin.set_fact': {
                    '__hactar_isolation_matches': False}}]))
            expected = []
            for value in entries.values():
                if value.get('zabbix', {}).get('hypervisor_machine_id') == '1' * 32:
                    expected.extend(value.get('zabbix', {}).get('configuration', {}).get('firewall', {}).get('guest_host_clients', []))
            assertions = [
                'aap_isolation_app_clients == fixture_expected',
                'aap_isolation_effective_desired_policy.guest_host_clients == fixture_expected',
                'aap_isolation_effective_previous_policy.guest_host_clients == fixture_expected',
                'aap_isolation_previous_policy == fixture_base',
                'aap_isolation_desired_policy == fixture_desired',
                'aap_isolation_rollback_policy == aap_isolation_effective_previous_policy']
            play = [{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'vars': {'aap_isolation_source_workspace': {'path': str(work)},
                         'aap_isolation_autodeploy_root': str(project),
                         'aap_isolation_machine_id': {'stdout': '1' * 32},
                         'aap_isolation_hypervisor': {'isolation_bridges': ['virbr0']},
                         'hactar_firewall_source_root': str(root / 'hactar'),
                         'aap_isolation_previous_policy': base, 'aap_isolation_desired_policy': base_desired,
                         'fixture_base': deepcopy(base), 'fixture_desired': deepcopy(base_desired),
                         'fixture_expected': expected, 'aap_isolation_require_match': strict},
                'tasks': [{'name': 'Load and compose protected project source', 'block': tasks + [
                    {'ansible.builtin.include_tasks': str(ROOT / 'tasks/aap-isolation-observe.yml')},
                    {'name': 'Prove complete composition and unchanged base transition',
                     'ansible.builtin.assert': {'that': assertions}, 'no_log': True},
                    {'ansible.builtin.copy': {'dest': str(desired_file),
                     'content': '{{ aap_isolation_effective_desired_policy | to_json }}', 'mode': '0600'}, 'no_log': True}],
                    'always': [{'ansible.builtin.file': {'path': str(work), 'state': 'absent'}, 'no_log': True}]}]}]
            path = root / 'play.yml'
            path.write_text(yaml.safe_dump(play, sort_keys=False))
            config = root / 'ansible.cfg'; config.write_text('[defaults]\n')
            env = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_LOCAL_TEMP=str(root / 'local'),
                       ANSIBLE_REMOTE_TEMP=str(root / 'remote'), CAC_GIT_TOKEN='synthetic-central-canary')
            result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,',
                str(path), '--vault-id', 'cac@' + str(key_file)], env=env, text=True, capture_output=True, timeout=90)
            self.assertFalse(work.exists(), 'Always cleanup must remove decrypted variables and checkouts')
            self.assertNotIn('synthetic-reader-canary', result.stdout + result.stderr)
            self.assertNotIn('synthetic-unused-secret', result.stdout + result.stderr)
            self.assertNotIn('synthetic-central-canary', result.stdout + result.stderr)
            if missing_migration or wrong_key or wrong_uuid or strict:
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(desired_file.exists())
            else:
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                policy = json.loads(desired_file.read_text())
                self.assertEqual(policy['guest_host_clients'], expected)
                if all(not row.get('zabbix', {}).get('configuration', {}).get('firewall', {}).get('guest_host_clients') or
                       row.get('zabbix', {}).get('hypervisor_machine_id') != '1' * 32 for row in entries.values()):
                    self.assertFalse(trace.exists())
                return policy

    def test_tagged_source_selects_actual_hypervisor_and_removes_only_deleted_app_permission(self):
        entries = {'fixture-17': owner(17), 'fixture-18': owner(18), 'remote-19': owner(19, '9' * 32), 'not-created': {},
                   'planned': {'zabbix': {'configuration': {'firewall': {'guest_host_clients': []}}}}}
        entries['remote-19']['zabbix']['instance_name'] = 'remote-19'
        entries['fixture-18']['zabbix']['instance_number'] = '18'
        first = self.run_native(entries)
        entries['fixture-17']['zabbix']['configuration']['firewall']['guest_host_clients'] = []
        second = self.run_native(entries)
        self.assertEqual(len(first['guest_host_clients']), 2)
        self.assertEqual(second['guest_host_clients'], entries['fixture-18']['zabbix']['configuration']['firewall']['guest_host_clients'])

    def test_missing_migration_and_failed_decryption_never_become_empty_permissions(self):
        entries = {'fixture-17': owner(17)}
        self.run_native(entries, missing_migration=True)
        self.run_native(entries, wrong_key=True)

    def test_readonly_pin_refuses_drift_without_implicit_firewall_application(self):
        self.run_native({'fixture-17': owner(17)}, strict=True)

    def test_native_guest_identity_mismatch_stops_before_effective_policy_is_used(self):
        self.run_native({'fixture-17': owner(17)}, wrong_uuid=True)


if __name__ == '__main__':
    unittest.main()
