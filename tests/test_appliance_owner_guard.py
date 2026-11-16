"""Accept actual schema-2 producer provenance without adding appliance SSH."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml
from test_aiops_settings import fixture, zabbix_guest

ROOT = Path(__file__).resolve().parents[1]


class ApplianceOwnerGuardTests(unittest.TestCase):
    def test_actual_producer_shape_and_wrong_kind_refusals_through_native_assert(self):
        context, *_ = fixture()
        guest = zabbix_guest(context)['vm_resource']
        task = yaml.safe_load((ROOT / 'tasks/aap-isolation-app-instance.yml').read_text())[0]
        cases = [('actual-producer', guest)]
        for key, value in [('schema_version', 1), ('schema_version', True), ('machine_id', 'b' * 32),
                           ('host_keys', ['ssh-ed25519 AAAA']), ('user', 'automation'),
                           ('api_url', 'http://192.168.70.99/api_jsonrpc.php'), ('api_version', '7.0.0'),
                           ('source_sha256', ''), ('source_sha256', 'd' * 64)]:
            bad = copy.deepcopy(guest)
            bad[key] = value
            cases.append((key + '-' + str(value), bad))
        with tempfile.TemporaryDirectory(prefix='appliance-owner-guard-') as temporary:
            root = Path(temporary)
            transactions = []
            for index, (name, record) in enumerate(cases):
                transactions.append({'block': [task, {'ansible.builtin.set_fact': {'accepted': '{{ accepted + [' + str(index) + '] }}'}}],
                                     'rescue': [{'ansible.builtin.set_fact': {'refused': '{{ refused + [' + str(index) + '] }}'}}],
                                     'vars': {'aap_isolation_app_owner': {'guest': record}}})
            play = [{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                     'vars': {'accepted': [], 'refused': [], 'aap_isolation_machine_id': {'stdout': context['hypervisor']['machine_id']},
                              'aap_isolation_hypervisor': {'isolation_bridges': ['vmbr0']},
                              'aiops_zabbix_source_image': {'sha256': 'c' * 64}},
                     'tasks': transactions + [{'ansible.builtin.assert': {'that': ['accepted == [0]',
                                'refused == ' + str(list(range(1, len(cases))))]}}]}]
            path = root / 'play.yml'
            path.write_text(yaml.safe_dump(json.loads(json.dumps(play)), sort_keys=False))
            result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(path)],
                env=dict(os.environ, ANSIBLE_LOCAL_TEMP=str(root / 'local'), ANSIBLE_REMOTE_TEMP=str(root / 'remote'),
                         ANSIBLE_NOCOLOR='1'), capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
