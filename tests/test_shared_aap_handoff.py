"""Exercise actual AAP post-VM guards with synthetic ownership and no API/VM access."""

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml
from test_aap_name_allocation import primary_fixture

ROOT = Path(__file__).resolve().parents[1]
CANARY = "fixture-shared-aap-private-credential-canary"


class SharedAapHandoffTests(unittest.TestCase):
    def values(self):
        route, domain, network, resource = primary_fixture()
        guest = dict(resource, vm_name=route["vm_name"], host_keys=route["guest_host_keys"],
                     machine_id="b" * 32, source_image_sha256="a" * 64,
                     vcpus=4, memory_mb=20480, disk_gb=60)
        return {
            "generic_linux_vm_create": True, "generic_linux_vm": guest,
            "vm_name": route["vm_name"], "aap_allocation_request_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "aap_hypervisor_pin": route["hypervisor"], "vm_dir": "/opt/vms", "vm_network": resource["network"],
            "aap_vcpus": 4, "aap_memory_mb": 20480, "aap_disk_size": "60G",
            "linux_vm_upstream": {"vm_name": route["vm_name"], "generic_image": False,
                                  "update_packages": False, "hypervisor_pin": route["hypervisor"],
                                  "source_image_sha256": "a" * 64},
            "aap_instance_route": route, "new_vm_ip": route["vm_ip"],
            "aap_primary_guest_machine_id": {"stdout": "b" * 32},
            "aap_primary_domain_ownership": {"stdout": domain},
            "aap_primary_network_ownership": {"stdout": network},
            "aap_primary_live_vcpus": 4, "aap_primary_live_memory_mb": 20480, "aap_primary_live_disk_gb": 60,
            "fixture_unused_secret": CANARY,
        }

    def run_case(self, values):
        production = yaml.safe_load((ROOT / "tasks/aap-register-shared-vm.yml").read_text())[0]["block"]
        guard = deepcopy(production[0])
        proof = deepcopy(next(task for task in production if task["name"] ==
                              "Match the shared result to the actual primary domain and authenticated guest"))
        with tempfile.TemporaryDirectory(prefix="shared-aap-handoff-") as directory:
            private = Path(directory)
            result_file = private / "passed"
            play = private / "play.yml"
            play.write_text(yaml.safe_dump([{
                "hosts": "localhost", "connection": "local", "gather_facts": False,
                "vars": values, "tasks": [
                    {"name": "Actual protected source guards", "block": [guard, proof], "no_log": True},
                    {"ansible.builtin.copy": {"dest": str(result_file), "content": "passed", "mode": "0600"}, "no_log": True},
                ],
            }], sort_keys=False))
            config = private / "ansible.cfg"
            config.write_text("[defaults]\nretry_files_enabled=False\n")
            env = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_LOCAL_TEMP=str(private / "local"),
                       ANSIBLE_REMOTE_TEMP=str(private / "remote"), ANSIBLE_FILTER_PLUGINS=str(ROOT / "filter_plugins"),
                       ANSIBLE_NOCOLOR="1", ANSIBLE_DISPLAY_ARGS_TO_STDOUT="True")
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(play)],
                                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=35)
            output = result.stdout + result.stderr
            self.assertNotIn(CANARY, output)
            return result.returncode, result_file.exists(), output

    def test_valid_fresh_artifact_is_accepted(self):
        code, passed, output = self.run_case(self.values())
        self.assertEqual(code, 0, output)
        self.assertTrue(passed)

    def test_foreign_or_unproved_fresh_inputs_are_rejected(self):
        for key, value in (("uuid", "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"),
                           ("disk", "/opt/vms/foreign.disk.qcow2"),
                           ("address", "192.0.2.99"), ("machine_id", "c" * 32),
                           ("source_image_sha256", "c" * 64), ("hypervisor_machine_id", "c" * 32)):
            with self.subTest(key=key):
                values = self.values()
                values["generic_linux_vm"][key] = value
                code, passed, _ = self.run_case(values)
                self.assertNotEqual(code, 0)
                self.assertFalse(passed)
        values = self.values()
        values["generic_linux_vm_create"] = "false"
        self.assertNotEqual(self.run_case(values)[0], 0)

    def test_existing_owner_keeps_unknown_legacy_hash_without_fresh_route(self):
        values = self.values()
        values.pop("linux_vm_upstream")
        values["generic_linux_vm_create"] = False
        values["generic_linux_vm"].update(source_image_sha256=None, source_image_status="unknown_legacy",
                                          verification_source="aap_resource_owner")
        code, passed, output = self.run_case(values)
        self.assertEqual(code, 0, output)
        self.assertTrue(passed)
        for key, value in (("source_image_sha256", "a" * 64), ("verification_source", "unproved-caller")):
            with self.subTest(key=key):
                changed = deepcopy(values)
                changed["generic_linux_vm"][key] = value
                code, passed, _ = self.run_case(changed)
                self.assertNotEqual(code, 0)
                self.assertFalse(passed)


if __name__ == "__main__":
    unittest.main()
