"""Prove native DNS parsing and the selected instance's existing address guard."""

import importlib.util
import os
from pathlib import Path
import unittest
from unittest import mock

os.environ.setdefault("ANSIBLE_LOCAL_TEMP", "/tmp/aap-dns-test-local")

from ansible.modules import getent
from ansible.errors import AnsibleError
from ansible.parsing.dataloader import DataLoader
from ansible.plugins.loader import filter_loader
from ansible.template import Templar, trust_as_template


ROOT = Path(__file__).resolve().parents[1]
filter_loader.add_directory(str(ROOT / "filter_plugins"))
SPEC = importlib.util.spec_from_file_location("dns_instance_route", ROOT / "filter_plugins/aap_instance_route.py")
routing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(routing)


class ModuleResult(Exception):
    def __init__(self, result, failed=False):
        self.result = result
        self.failed = failed


def fixture_route():
    return {
        "vm_name": "aap27-test-15", "vm_ip": "192.0.2.15",
        "aap_hostname": "https://aap27-test-15.example.invalid",
        "guest_host_keys": ["ssh-ed25519 AAAA"],
        "hypervisor": {
            "address": "192.0.2.200", "public_ip": "192.0.2.200",
            "user": "fixture", "port": 22, "machine_id": "1" * 32,
            "host_keys": ["ssh-ed25519 AAAA"],
            "isolation_bridges": ["virbr0"], "isolation_dns_bridges": ["virbr0"],
        },
    }


class NativeDnsTests(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader()
        self.api_tasks = self.loader.load_from_file(str(ROOT / "tasks/aap-instance-api.yml"))
        self.api_guard = next(t for t in self.api_tasks if t["name"] == "Require public DNS to identify only the pinned hypervisor")
        self.infra_tasks = self.loader.load_from_file(str(ROOT / "02-infra-config.yml"))[0]

    def evaluate(self, condition, values):
        # DataLoader loaded this expression from the repository task file,
        # preserving its native template-trust tag on core 2.20.
        # Only the expression read from this repository's playbook is trusted;
        # synthetic module results remain ordinary, untrusted input data.
        return Templar(loader=self.loader, variables=values).evaluate_conditional(trust_as_template(condition))

    def parsed_getent(self, output, rc=0):
        """Run the real built-in module parser; only its external process is stubbed."""
        params = {"database": "hosts", "key": "aap27-test-15.example.invalid.",
                  "service": "dns", "split": None, "fail_key": True}
        module = mock.Mock(params=params)
        module.get_bin_path.return_value = "/usr/bin/getent"
        module.run_command.return_value = (rc, output, "")
        module.exit_json.side_effect = lambda **kw: (_ for _ in ()).throw(ModuleResult(kw))
        module.fail_json.side_effect = lambda **kw: (_ for _ in ()).throw(ModuleResult(kw, True))
        with mock.patch.object(getent, "AnsibleModule", return_value=module):
            with self.assertRaises(ModuleResult) as finished:
                getent.main()
        module.run_command.assert_called_once_with(
            ["/usr/bin/getent", "hosts", "aap27-test-15.example.invalid.", "-s", "dns"])
        if finished.exception.failed:
            raise finished.exception
        return finished.exception.result

    def test_dns_only_lookup_accepts_exact_ipv4_and_rejects_other_results(self):
        lookup = next(t for t in self.api_tasks if "ansible.builtin.getent" in t)
        self.assertEqual(lookup["ansible.builtin.getent"]["service"], "dns")
        cases = [
            ("192.0.2.200 name.example.invalid\n", True),
            ("192.0.2.201 name.example.invalid\n", False),
            ("192.0.2.200 name.example.invalid\n192.0.2.201 name.example.invalid\n", False),
            ("2001:db8::1 name.example.invalid\n", False),
            ("192.0.2.200 name.example.invalid\n2001:db8::1 name.example.invalid\n", False),
            ("", False),
        ]
        for output, expected in cases:
            with self.subTest(output=output):
                result = self.parsed_getent(output)
                variables = {"aap_instance_dns": result, "aap_instance_route": fixture_route(),
                             "aap_validate_certs": True}
                if expected:
                    self.assertTrue(self.evaluate(self.api_guard["ansible.builtin.assert"]["that"], variables))
                else:
                    with self.assertRaises(AnsibleError):
                        self.evaluate(self.api_guard["ansible.builtin.assert"]["that"], variables)

    def test_getent_failure_is_not_an_empty_successful_answer(self):
        with self.assertRaises(ModuleResult) as failure:
            self.parsed_getent("", rc=2)
        self.assertTrue(failure.exception.failed)

    def test_propagation_rejects_wrong_or_incomplete_external_answers(self):
        task = next(t for t in self.infra_tasks["tasks"] if t["name"] == "Wait for DNS propagation")
        self.assertEqual(task["ansible.builtin.command"]["argv"][:2], ["dig", "@8.8.8.8"])
        self.assertEqual((task["retries"], task["delay"]), (30, 10))
        for rc, lines, fails in [(0, ["192.0.2.200"], False), (0, [], True),
                                  (0, ["192.0.2.201"], True),
                                  (0, ["192.0.2.200", "192.0.2.201"], True),
                                  (9, ["192.0.2.200"], True)]:
            with self.subTest(rc=rc, lines=lines):
                values = {"dns_check": {"rc": rc, "stdout_lines": lines}, "aap_instance_route": fixture_route()}
                self.assertEqual(self.evaluate(task["failed_when"], values), fails)

    def test_dns_guard_precedes_tls_and_keeps_certificate_verification(self):
        guard_index = self.api_tasks.index(self.api_guard)
        tls_index = next(i for i, t in enumerate(self.api_tasks) if "ansible.builtin.uri" in t)
        self.assertLess(guard_index, tls_index)
        self.assertTrue(self.api_tasks[tls_index]["ansible.builtin.uri"]["validate_certs"])
        self.assertEqual(self.api_tasks[tls_index]["ansible.builtin.uri"]["follow_redirects"], "none")


if __name__ == "__main__":
    unittest.main()
