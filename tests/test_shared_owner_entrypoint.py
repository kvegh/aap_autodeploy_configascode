"""Qualify actual AAP producer output against the shared VM entrypoint offline."""
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
from test_aap_name_allocation import primary_fixture

ROOT = Path(__file__).resolve().parents[1]
SHARED = Path(os.environ["SHARED_GENERIC_VM_SOURCE"]) if os.environ.get("SHARED_GENERIC_VM_SOURCE") else None
CANARY = "synthetic-owner-bootstrap-only-canary"


@unittest.skipUnless(SHARED and (SHARED / "playbooks/deploy_generic_linux_vm.yml").is_file(),
                     "set SHARED_GENERIC_VM_SOURCE to qualify the cross-project source contract")
class SharedOwnerEntrypointTests(unittest.TestCase):
    def env(self, root):
        return dict(os.environ, ANSIBLE_NOCOLOR="1", ANSIBLE_HOME=str(root / "home"),
                    ANSIBLE_LOCAL_TEMP=str(root / "local"), ANSIBLE_REMOTE_TEMP=str(root / "remote"),
                    ANSIBLE_FILTER_PLUGINS=str(ROOT / "filter_plugins"),
                    ANSIBLE_SSH_CONTROL_PATH_DIR=str(root / "cp"))

    def producer(self, root, *, existing=True):
        route, domain, network, resource = primary_fixture()
        values = {
            "vm_name": route["vm_name"], "vm_dir": "/opt/vms", "vm_network": resource["network"],
            "vault_domain": "example.invalid", "aap_hypervisor_pin": route["hypervisor"],
            "aap_vm_reservation": {"request_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"},
            "aap_vcpus": 4, "aap_memory_mb": 20480, "aap_disk_size": "60G",
            "aap_golden_image_path": str(root / "never-inspected-source.qcow2"),
            "aap_golden_source": {"stat": {"checksum": "a" * 64}},
            "aap_guest_network": {"stdout": network},
            "aap_existing_owner": {},
        }
        pre = yaml.safe_load((ROOT / "01-aap-resource-preconfigure.yml").read_text())[0]["tasks"]
        tasks = []
        if existing:
            values.update(aap_existing_owner={"instance_route": route, "instance_resources": {"aap": resource}},
                          aap_instance_route=route, aap_primary_domain_ownership={"stdout": domain},
                          aap_primary_network_ownership={"stdout": network},
                          aap_primary_guest_machine_id={"stdout": "b" * 32},
                          aap_primary_guest_hostname={"stdout": "aap27.v15.example.invalid"},
                          aap_primary_live_vcpus=4, aap_primary_live_memory_mb=20480, aap_primary_live_disk_gb=60)
            owner = yaml.safe_load((ROOT / "tasks/aap-verify-owned-vm.yml").read_text())
            tasks += [deepcopy(owner[0]), deepcopy(owner[2]), deepcopy(owner[3])]
        else:
            tasks.append(deepcopy(next(task for task in pre if task["name"] ==
                                      "Publish the actual prepared-image route only for fresh creation")))
        tasks.append(deepcopy(next(task for task in pre if task["name"] ==
                                  "Hand off only the reserved AAP image route and resource sizes")))
        registered = []
        for index, task in enumerate(tasks):
            if "ansible.builtin.set_stats" in task:
                name = "fixture_stats_" + str(index)
                task["register"] = name
                registered.append(name + ".ansible_stats.data")
        expression = registered[0]
        for item in registered[1:]:
            expression += " | combine(" + item + ")"
        output = root / "producer-output.json"
        tasks.append({"name": "Retain actual producer artifacts only in the private fixture",
                      "ansible.builtin.copy": {"dest": str(output), "mode": "0600",
                        "content": "{{ (" + expression + ") | to_json }}"}, "no_log": True})
        play = root / "producer.yml"
        play.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local", "gather_facts": False,
                                         "vars": values, "tasks": tasks}], sort_keys=False))
        result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(play)],
                                cwd=ROOT, env=self.env(root), capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        artifacts = json.loads(output.read_text())
        self.assertNotIn(CANARY, json.dumps(artifacts))
        return artifacts

    def consumer(self, root, artifacts, *, target="single"):
        poison = root / "forbidden-action"
        trap = root / "ssh-trap"
        trap.write_text("#!" + sys.executable + "\nimport pathlib,sys\npathlib.Path(" + repr(str(poison)) +
                        ").write_text('forbidden')\nsys.exit(91)\n")
        trap.chmod(0o700)
        pin = artifacts.get("linux_vm_existing_route", artifacts.get("linux_vm_upstream", {}))["hypervisor_pin"]
        host = {"ansible_host": pin["address"], "ansible_connection": "ssh", "ansible_user": "fixture",
                "ansible_ssh_executable": str(trap)}
        targets = {"fixture-hypervisor": host} if target != "missing" else {}
        if target == "multiple":
            targets["fixture-other"] = dict(host, ansible_host="192.0.2.99")
        inventory = root / "inventory.yml"
        inventory.write_text(yaml.safe_dump({"all": {"children": {
            "hypervisor": {"hosts": targets},
            "provisioned_linux_guest": {"hosts": {"fixture-guest": dict(host, ansible_host="192.0.2.15")}},
        }}}))
        secret = VaultSecret(b"fixture-key")
        vault_file = root / "bootstrap-only.vault"
        vault_file.write_bytes(VaultLib([("default", secret)]).encrypt(yaml.safe_dump({"provisioning": {
            "guest_ssh_user": "fixture_guest", "guest_ssh_password": CANARY,
        }})))
        key = root / "key"
        key.write_text("fixture-key")
        key.chmod(0o600)
        inputs = dict(artifacts, generic_linux_vm_config_file=str(vault_file))
        inputs_path = root / "inputs.json"
        inputs_path.write_text(json.dumps(inputs))
        complete = root / "handoff.json"
        wrapper = root / "consumer.yml"
        verify = [{"ansible.builtin.assert": {"that": [
            "generic_linux_vm.source_image_sha256 is none",
            "generic_linux_vm.source_image_status == 'unknown_legacy'",
            "'golden_image_path' not in hostvars.localhost.provisioning",
            "'source_image_sha256' not in hostvars.localhost.provisioning",
        ]}, "no_log": True}, {"ansible.builtin.copy": {"dest": str(complete), "mode": "0600",
            "content": "{{ generic_linux_vm | to_json }}"}, "no_log": True}]
        wrapper.write_text(yaml.safe_dump([
            {"name": "Run the actual shared entrypoint", "ansible.builtin.import_playbook": str(SHARED / "playbooks/deploy_generic_linux_vm.yml")},
            {"name": "Check the owner handoff after the actual shared no-op", "hosts": "localhost", "connection": "local",
             "gather_facts": False, "tasks": verify},
        ], sort_keys=False))
        env = self.env(root)
        env["ANSIBLE_FILTER_PLUGINS"] = str(SHARED / "playbooks/filter_plugins")
        env.pop("AC_AGENTS_ENVIRONMENT_VAULT_FILE", None)
        result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", str(inventory), str(wrapper),
                                 "-e", "@" + str(inputs_path), "--vault-password-file", str(key), "-v"],
                                cwd=SHARED, env=env, capture_output=True, text=True, timeout=50)
        self.assertNotIn(CANARY, result.stdout + result.stderr)
        self.assertNotIn("forbidden-credential-override", result.stdout + result.stderr)
        return result, poison, complete

    def test_actual_owner_output_and_bootstrap_only_config_preserve_unknown_provenance(self):
        with tempfile.TemporaryDirectory(prefix="shared-owner-positive-") as temporary:
            root = Path(temporary)
            artifacts = self.producer(root)
            result, poison, complete = self.consumer(root, artifacts)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertFalse(poison.exists())
            self.assertEqual(json.loads(complete.read_text()), artifacts["generic_linux_vm"])
            self.assertIn('"generic_linux_vm_creation":', output)
            self.assertNotIn('"generic_linux_vm":', output)
            self.assertNotIn('"verified": true', output)
            self.assertNotIn("TASK [linux_vm :", output)
            self.assertNotIn("TASK [linux_guest :", output)

    def test_existing_route_rejects_ambiguous_target_bad_pin_and_unknown_or_secret_fields(self):
        with tempfile.TemporaryDirectory(prefix="shared-owner-negative-") as temporary:
            parent = Path(temporary)
            artifacts = self.producer(parent)
            for mode in ("missing", "multiple", "bad_pin", "unknown", "credential", "both", "creation"):
                with self.subTest(mode=mode):
                    root = parent / mode
                    root.mkdir()
                    changed = deepcopy(artifacts)
                    target = mode if mode in ("missing", "multiple") else "single"
                    if mode == "bad_pin":
                        changed["linux_vm_existing_route"]["hypervisor_pin"]["port"] = True
                    if mode == "unknown":
                        changed["linux_vm_existing_route"]["source_image_sha256"] = None
                    if mode == "credential":
                        changed["linux_vm_existing_route"]["guest_ssh_password"] = "forbidden-credential-override"
                    if mode == "both":
                        changed["linux_vm_upstream"] = {}
                    if mode == "creation":
                        changed["generic_linux_vm_create"] = True
                    result, poison, complete = self.consumer(root, changed, target=target)
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertFalse(poison.exists())
                    self.assertFalse(complete.exists())
                    self.assertNotIn('"generic_linux_vm_creation":', result.stdout)

    def test_actual_fresh_route_remains_strict_and_reaches_creator_only_when_complete(self):
        with tempfile.TemporaryDirectory(prefix="shared-owner-fresh-") as temporary:
            parent = Path(temporary)
            artifacts = self.producer(parent, existing=False)
            for field in (None, "golden_image_path", "source_image_sha256"):
                with self.subTest(missing=field):
                    root = parent / (field or "complete")
                    root.mkdir()
                    changed = deepcopy(artifacts)
                    if field:
                        changed["linux_vm_upstream"].pop(field)
                    result, poison, _ = self.consumer(root, changed)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(poison.exists(), field is None, result.stdout + result.stderr)
                    self.assertNotIn('"generic_linux_vm_creation":', result.stdout)
                    self.assertNotIn('"verified": true', result.stdout)


if __name__ == "__main__":
    unittest.main()
