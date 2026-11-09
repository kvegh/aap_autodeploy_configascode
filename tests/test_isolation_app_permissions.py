"""Exercise native encrypted source loading and CaC-only effective composition."""
from copy import deepcopy
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
    return {'zabbix': guest, 'firewall': {'guest_host_clients': [row]}}


class ApplicationPolicyTests(unittest.TestCase):
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
                next(iter(entries.values())).pop('firewall')
            inner = vault.encrypt(b'synthetic-unused-secret', VaultSecret(unrelated_key)).decode()
            plaintext = yaml.safe_dump({'cac_import_metadata': {'project_id': 'aiops-selfhealing-demo'},
                'aiops_instances': entries}, sort_keys=False)
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
            records = {row['zabbix']['vm_name']: row['zabbix'] for row in entries.values() if row.get('zabbix')}
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
                    expected.extend(value.get('firewall', {}).get('guest_host_clients', []))
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
                if all(not row.get('firewall', {}).get('guest_host_clients') or
                       row.get('zabbix', {}).get('hypervisor_machine_id') != '1' * 32 for row in entries.values()):
                    self.assertFalse(trace.exists())
                return policy

    def test_tagged_source_selects_actual_hypervisor_and_removes_only_deleted_app_permission(self):
        entries = {'fixture-17': owner(17), 'fixture-18': owner(18), 'remote-19': owner(19, '9' * 32), 'not-created': {}}
        entries['remote-19']['zabbix']['instance_name'] = 'remote-19'
        entries['fixture-18']['zabbix']['instance_number'] = '18'
        first = self.run_native(entries)
        entries['fixture-17']['firewall']['guest_host_clients'] = []
        second = self.run_native(entries)
        self.assertEqual(len(first['guest_host_clients']), 2)
        self.assertEqual(second['guest_host_clients'], entries['fixture-18']['firewall']['guest_host_clients'])

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
