"""Prove global reservation semantics and target-bound routing without touching VMs."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import unittest
from unittest import mock
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.errors import AnsibleActionFail
from ansible.parsing.vault import VaultLib, VaultSecret
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.plugins.action import ActionBase

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


allocation = load("allocation", ROOT / "src/aap_name_allocation.py")
routing = load("routing", ROOT / "filter_plugins/aap_instance_route.py")


def writer_project(directory, vault):
    """Use actual action files and encrypted fixture settings for token-bound Git."""
    project = directory / "project"
    for relative in ("action_plugins/aap_reserve_vm_name.py",
                     "src/aap_name_allocation.py", "filter_plugins/cac_import.py"):
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    (project / "myvars").write_bytes(vault.encrypt(yaml.safe_dump({
        "git_url": "https://git.example.invalid/fixture-owner/aap_autodeploy_configascode.git",
    }), vault_id="cac"))
    return project


class AllocationTests(unittest.TestCase):
    def test_writer_refuses_repository_overrides_and_obsolete_token_injection(self):
        action = load("reserve_binding", ROOT / "action_plugins/aap_reserve_vm_name.py")
        plugin = action.ActionModule.__new__(action.ActionModule)
        plugin._task = SimpleNamespace(args={"repository": "https://untrusted.example.invalid/repo.git"})
        with mock.patch.object(ActionBase, "run", return_value={}), mock.patch.object(
            action.subprocess, "run", side_effect=AssertionError("No Git operation allowed")
        ), mock.patch.dict(os.environ, {"CAC_GIT_TOKEN": "fixture-writer"}):
            with self.assertRaisesRegex(AnsibleActionFail, "fixed by encrypted"):
                plugin.run(task_vars={})
            plugin._task.args = {}
            with mock.patch.dict(os.environ, {"CAC_GIT_TOKEN": "", "AAP_ALLOCATION_GIT_TOKEN": "obsolete"}):
                with self.assertRaisesRegex(AnsibleActionFail, "writer credential"):
                    plugin.run(task_vars={})

    def state(self):
        return {"schema_version": 1, "next_number": 15, "reservations": {}}

    def test_names_are_consumed_before_work_and_next_host_cannot_reuse_them(self):
        first, one = allocation.reserve(
            self.state(),
            "aap27-test",
            "a" * 8 + "-aaaa-aaaa-aaaa-" + "a" * 12,
            "1" * 32,
        )
        second, two = allocation.reserve(
            first, "aap27-test", "b" * 8 + "-bbbb-bbbb-bbbb-" + "b" * 12, "2" * 32
        )
        self.assertEqual(
            (one["number"], two["number"], second["next_number"]), (15, 16, 17)
        )
        self.assertEqual(len(second["reservations"]), 2)

    def test_retry_of_the_same_published_request_is_idempotent(self):
        request = "a" * 8 + "-aaaa-aaaa-aaaa-" + "a" * 12
        first, one = allocation.reserve(self.state(), "aap27-test", request, "1" * 32)
        second, two = allocation.reserve(first, "aap27-test", request, "1" * 32)
        self.assertEqual(first, second)
        self.assertEqual(one, two)
        with self.assertRaises(ValueError):
            allocation.reserve(first, "aap27-test", request, "2" * 32)

    def test_migration_evidence_can_only_raise_the_shared_floor(self):
        state, result = allocation.reserve(
            self.state(),
            "aap27-test",
            "a" * 8 + "-aaaa-aaaa-aaaa-" + "a" * 12,
            "1" * 32,
            20,
        )
        self.assertEqual(result["number"], 20)
        self.assertEqual(state["next_number"], 21)

    def test_invalid_or_regressed_state_is_refused(self):
        for value in (
            None,
            {},
            dict(self.state(), next_number=True),
            dict(self.state(), next_number=0),
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                allocation.reserve(
                    value,
                    "aap27-test",
                    "a" * 8 + "-aaaa-aaaa-aaaa-" + "a" * 12,
                    "1" * 32,
                )

    def test_route_cannot_move_to_a_different_reserved_name_or_host(self):
        request = "a" * 8 + "-aaaa-aaaa-aaaa-" + "a" * 12
        first, one = allocation.reserve(self.state(), "aap27-test", request, "1" * 32)
        route = {"vm_name": one["vm_name"], "hypervisor": {"machine_id": "1" * 32}}
        result, record = allocation.publish_route(first, request, route)
        self.assertEqual(result["next_number"], 16)
        self.assertEqual(record["instance_route"], route)
        route["hypervisor"]["machine_id"] = "2" * 32
        with self.assertRaises(ValueError):
            allocation.publish_route(result, request, route)

    def test_real_git_competing_writers_publish_unique_vaulted_reservations(self):
        secret = VaultSecret(b"fixture-vault-password")
        vault = VaultLib([("cac", secret)])
        real_run = subprocess.run
        with tempfile.TemporaryDirectory(prefix="aap-counter-cas-test-") as temporary:
            directory = Path(temporary)
            remote = directory / "remote.git"
            seed = directory / "seed"
            seed.mkdir()

            def git(path, *args):
                return real_run(
                    ["git", "-C", str(path), *args],
                    text=True,
                    capture_output=True,
                    check=True,
                )

            real_run(
                ["git", "init", "--bare", "--initial-branch=main", str(remote)],
                check=True,
                capture_output=True,
            )
            git(seed, "init", "--initial-branch=main")
            (seed / "state").mkdir()
            (seed / "state/aap_vm_allocations_vault.yml").write_bytes(
                vault.encrypt(
                    yaml.safe_dump(
                        {"aap_vm_allocation": self.state(), "unchanged": "fixture"}
                    ).encode(),
                    secret=secret,
                    vault_id="cac",
                )
            )
            git(seed, "add", ".")
            git(
                seed,
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-m",
                "Initialize",
            )
            git(seed, "remote", "add", "origin", str(remote))
            git(seed, "push", "origin", "main")
            project = writer_project(directory, vault)
            action = load("reserve_action", project / "action_plugins/aap_reserve_vm_name.py")
            barrier = threading.Barrier(2)
            seen = threading.local()

            def redirected(command, *args, **kwargs):
                command = [
                    str(remote) if x == "https://git.example.invalid/fixture-owner/aap_autodeploy_configascode-secrets.git" else x
                    for x in command
                ]
                result = real_run(command, *args, **kwargs)
                if "fetch" in command and not getattr(seen, "fetched", False):
                    seen.fetched = True
                    barrier.wait(timeout=20)
                return result

            def reserve_one(hypervisor):
                plugin = action.ActionModule.__new__(action.ActionModule)
                plugin._task = SimpleNamespace(
                    args={
                        "prefix": "aap27-test",
                        "hypervisor_id": hypervisor,
                    },
                    check_mode=False,
                )
                plugin._loader = DataLoader()
                plugin._loader.set_vault_secrets([("cac", secret)])
                return plugin.run(task_vars={})

            with mock.patch.object(
                ActionBase, "run", side_effect=lambda *args, **kwargs: {}
            ), mock.patch.object(
                action.subprocess, "run", side_effect=redirected
            ), mock.patch.dict(
                os.environ, {"CAC_GIT_TOKEN": "fixture-writer"}
            ):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(reserve_one, ["1" * 32, "2" * 32]))
            self.assertEqual({x["number"] for x in results}, {15, 16})
            accepted = git(
                remote, "show", "main:state/aap_vm_allocations_vault.yml"
            ).stdout.encode()
            data = AnsibleLoader(vault.decrypt(accepted)).get_single_data()
            self.assertEqual(data["aap_vm_allocation"]["next_number"], 17)
            self.assertEqual(len(data["aap_vm_allocation"]["reservations"]), 2)
            self.assertEqual(data["unchanged"], "fixture")

    def test_native_ansible_action_uses_attached_vault_and_preserves_check_mode(self):
        import sys

        with tempfile.TemporaryDirectory(prefix="aap-native-reservation-") as temporary:
            directory = Path(temporary)
            remote = directory / "remote.git"
            seed = directory / "seed"
            seed.mkdir()

            def git(path, *args):
                return subprocess.run(
                    ["git", "-C", str(path), *args],
                    text=True,
                    capture_output=True,
                    check=True,
                )

            subprocess.run(
                ["git", "init", "--bare", "--initial-branch=main", str(remote)],
                capture_output=True,
                check=True,
            )
            git(seed, "init", "--initial-branch=main")
            (seed / "state").mkdir()
            vault = VaultLib([("cac", VaultSecret(b"fixture-password"))])
            (seed / "state/aap_vm_allocations_vault.yml").write_bytes(
                vault.encrypt(
                    yaml.safe_dump({"aap_vm_allocation": self.state()}).encode(),
                    vault_id="cac",
                )
            )
            git(seed, "add", ".")
            git(
                seed,
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-m",
                "Initialize",
            )
            git(seed, "remote", "add", "origin", str(remote))
            git(seed, "push", "origin", "main")
            binaries = directory / "bin"
            binaries.mkdir()
            wrapper = binaries / "git"
            wrapper.write_text(
                "#!"
                + sys.executable
                + '\nimport os,sys\na=[os.environ["FIXTURE_GIT_REMOTE"] if x=="https://git.example.invalid/fixture-owner/aap_autodeploy_configascode-secrets.git" else x for x in sys.argv[1:]]\nos.execv("/usr/bin/git",["git"]+a)\n'
            )
            wrapper.chmod(0o700)
            password = directory / "password"
            password.write_text("fixture-password")
            password.chmod(0o600)
            other_password = directory / "other-password"
            other_password.write_text("different-fixture-password")
            other_password.chmod(0o600)
            fixture = directory / "play.yml"
            fixture.write_text(
                yaml.safe_dump(
                    [
                        {
                            "hosts": "localhost",
                            "connection": "local",
                            "gather_facts": False,
                            "tasks": [
                                {
                                    "name": "Run the real controller action",
                                    "aap_reserve_vm_name": {
                                        "prefix": "aap27-test",
                                        "hypervisor_id": "1" * 32,
                                        "observed_floor": "15",
                                    },
                                    "register": "reservation",
                                    "no_log": True,
                                },
                                {
                                    "ansible.builtin.assert": {
                                        "that": [
                                            "reservation.reserved == (not ansible_check_mode)",
                                            "ansible_check_mode or reservation.number == 15",
                                        ]
                                    }
                                },
                            ],
                        }
                    ]
                )
            )
            project = writer_project(directory, vault)
            env = dict(
                os.environ,
                PATH=str(binaries) + os.pathsep + os.environ["PATH"],
                CAC_GIT_TOKEN="fixture-writer-canary",
                FIXTURE_GIT_REMOTE=str(remote),
                ANSIBLE_ACTION_PLUGINS=str(project / "action_plugins"),
                ANSIBLE_LIBRARY=str(ROOT / "library"),
                ANSIBLE_LOCAL_TEMP=str(directory / "local"),
                ANSIBLE_REMOTE_TEMP=str(directory / "remote"),
            )
            for check in (True, False):
                command = [
                    sys.executable,
                    "-m",
                    "ansible.cli.playbook",
                    "-i",
                    "localhost,",
                    "--vault-id",
                    "default@" + str(other_password),
                    "--vault-id",
                    "cac@" + str(password),
                ]
                if check:
                    command.append("--check")
                result = subprocess.run(
                    command + [str(fixture), "-e", json.dumps({
                        "git_url": "https://untrusted.example.invalid/attacker/project.git",
                        "vault_cac_repository_namespace": "https://untrusted.example.invalid/attacker",
                    })],
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=45,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn("fixture-writer-canary", result.stdout + result.stderr)
            accepted = git(
                remote, "show", "main:state/aap_vm_allocations_vault.yml"
            ).stdout.encode()
            self.assertEqual(
                AnsibleLoader(vault.decrypt(accepted)).get_single_data()[
                    "aap_vm_allocation"
                ]["next_number"],
                16,
            )


class RoutingTests(unittest.TestCase):
    def test_optional_https_policy_is_independently_declared_and_preserves_pins(self):
        pin = self.route()["hypervisor"]
        before = copy.deepcopy(pin)
        baseline = routing.isolation_policy(pin)
        self.assertEqual(set(baseline), {"bridges", "dns_bridges"})
        client = {"bridge": "virbr0", "ipv4": "192.0.2.15", "mac": "52:54:00:00:00:15"}
        extended = routing.isolation_policy(pin, [client], ["198.51.100.5"])
        self.assertEqual(extended["https_clients"], [client])
        self.assertEqual(extended["protected_ipv4"], ["198.51.100.5"])
        self.assertEqual(pin, before)
        with self.assertRaises(routing.AnsibleFilterError):
            routing.isolation_policy(pin, [client], [])
        invalid = dict(client, bridge="unapproved")
        with self.assertRaises(routing.AnsibleFilterError):
            routing.isolation_policy(pin, [invalid], ["198.51.100.5"])
        self.assertEqual(routing.isolation_policy(pin, [], ["198.51.100.5"]), baseline)

    def route(self):
        return {
            "vm_name": "aap27-test-15",
            "vm_ip": "192.0.2.15",
            "aap_hostname": "https://aap27-test-15.example.invalid",
            "guest_host_keys": ["ssh-ed25519 AAAA"],
            "hypervisor": {
                "address": "192.0.2.200",
                "public_ip": "192.0.2.200",
                "user": "fixture",
                "port": 22,
                "machine_id": "1" * 32,
                "host_keys": ["ssh-ed25519 AAAA"],
                "isolation_bridges": ["virbr0"],
                "isolation_dns_bridges": ["virbr0"],
            },
        }

    def test_ssh_always_routes_through_the_pinned_hypervisor_with_both_key_checks(self):
        result = routing.ssh_args(self.route(), "/tmp/fixture-known-hosts")
        self.assertIn("ProxyCommand=", result)
        self.assertIn("fixture@192.0.2.200", result)
        self.assertEqual(result.count("StrictHostKeyChecking=yes"), 2)
        self.assertIn("HostKeyAlias=aap27-test-15.example.invalid", result)
        self.assertNotIn("StrictHostKeyChecking=no", result)

    def test_private_api_and_missing_pin_are_refused(self):
        route = self.route()
        route["aap_hostname"] = "https://192.0.2.15"
        with self.assertRaises(routing.AnsibleFilterError):
            routing.instance_route(route)
        route = self.route()
        route["hypervisor"].pop("host_keys")
        with self.assertRaises(routing.AnsibleFilterError):
            routing.instance_route(route)

    def test_public_api_refuses_stale_dns_ipv6_alternatives_and_disabled_tls(self):
        self.assertTrue(routing.instance_api_dns(self.route(), ["192.0.2.200"], []))
        for addresses, ipv6, tls in (
            (["192.0.2.201"], [], True),
            (["192.0.2.200", "192.0.2.201"], [], True),
            (["192.0.2.200"], ["2001:db8::1"], True),
            (["192.0.2.200"], [], False),
        ):
            with self.subTest(
                addresses=addresses, ipv6=ipv6, tls=tls
            ), self.assertRaises(routing.AnsibleFilterError):
                routing.instance_api_dns(self.route(), addresses, ipv6, tls)

    def test_instance_selection_uses_only_published_routes(self):
        state = {
            "schema_version": 1,
            "reservations": {
                "fixture": {"vm_name": "aap27-test-15", "instance_route": self.route()}
            },
        }
        self.assertEqual(
            routing.registered_instance(state, "aap27-test-15"), self.route()
        )
        for key in ("unknown", "https://old.example.invalid"):
            with self.assertRaises(routing.AnsibleFilterError):
                routing.registered_instance(state, key)

    def test_existing_domains_and_old_counter_raise_only_the_floor(self):
        self.assertEqual(
            routing.observed_floor(["aap27-test-14", "other-domain"], "15"), 15
        )
        self.assertEqual(routing.observed_floor(["aap27-test-20"], "15"), 21)
        self.assertEqual(routing.observed_floor([], ""), 1)

    def test_public_key_comments_are_not_part_of_the_trust_identity(self):
        self.assertEqual(
            routing.public_host_key("ssh-ed25519 AAAA fixture@host\n"),
            "ssh-ed25519 AAAA",
        )

    def test_network_must_have_a_declared_live_bridge(self):
        self.assertEqual(
            routing.network_bridge('<network><bridge name="virbr0"/></network>'),
            "virbr0",
        )
        with self.assertRaises(routing.AnsibleFilterError):
            routing.network_bridge("<network/>")

    def test_dns_preflight_accepts_only_absent_or_exact_existing_bindings(self):
        self.assertTrue(routing.safe_instance_dns([], "aap27-test-15", "192.0.2.200"))
        existing = [{"name": "aap27-test-15", "type": "A", "data": "192.0.2.200"}]
        self.assertTrue(
            routing.safe_instance_dns(existing, "aap27-test-15", "192.0.2.200")
        )
        for invalid in (
            [{"data": "192.0.2.201"}],
            [{"name": "other", "data": "192.0.2.200"}],
            [{"data": None}],
            {"error": "not a complete record list"},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(
                routing.AnsibleFilterError
            ):
                routing.safe_instance_dns(invalid, "aap27-test-15", "192.0.2.200")

    def test_real_reader_and_delegated_inventory_use_registered_jump_route(self):
        import sys

        with tempfile.TemporaryDirectory(prefix="aap-native-instance-") as temporary:
            directory = Path(temporary)
            remote = directory / "remote.git"
            seed = directory / "seed"
            seed.mkdir()

            def git(path, *args):
                return subprocess.run(
                    ["git", "-C", str(path), *args],
                    text=True,
                    capture_output=True,
                    check=True,
                )

            subprocess.run(
                ["git", "init", "--bare", "--initial-branch=main", str(remote)],
                capture_output=True,
                check=True,
            )
            git(seed, "init", "--initial-branch=main")
            (seed / "state").mkdir()
            vault = VaultLib([("cac", VaultSecret(b"fixture-password"))])
            state = {
                "schema_version": 1,
                "next_number": 16,
                "reservations": {
                    "fixture": {
                        "vm_name": "aap27-test-15",
                        "instance_route": self.route(),
                    }
                },
            }
            (seed / "state/aap_vm_allocations_vault.yml").write_bytes(
                vault.encrypt(
                    yaml.safe_dump({"aap_vm_allocation": state}).encode(),
                    vault_id="cac",
                )
            )
            git(seed, "add", ".")
            git(
                seed,
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-m",
                "Initialize",
            )
            git(seed, "remote", "add", "origin", str(remote))
            git(seed, "push", "origin", "main")
            binaries = directory / "bin"
            binaries.mkdir()
            wrapper = binaries / "git"
            wrapper.write_text(
                "#!"
                + sys.executable
                + '\nimport os,sys\na=[os.environ["FIXTURE_GIT_REMOTE"] if x=="https://git.example.invalid/fixture-owner/aap_autodeploy_configascode-secrets.git" else x for x in sys.argv[1:]]\nif any(x.startswith(("https://","http://","ssh://","git@")) for x in a):sys.exit("Unexpected network target")\nos.execv("/usr/bin/git",["git"]+a)\n'
            )
            wrapper.chmod(0o700)
            # Run the actual action source with encrypted fixture configuration.
            # Its project-relative lookup must never read the operator's myvars.
            for relative in ('action_plugins/aap_read_instance.py',
                             'filter_plugins/aap_instance_route.py', 'filter_plugins/cac_import.py'):
                target = directory / relative
                target.parent.mkdir(exist_ok=True)
                target.write_bytes((ROOT / relative).read_bytes())
            (directory / 'myvars').write_bytes(vault.encrypt(yaml.safe_dump({
                'git_url': 'https://git.example.invalid/fixture-owner/aap_autodeploy_configascode.git',
            }), vault_id='cac'))
            password = directory / "password"
            password.write_text("fixture-password")
            password.chmod(0o600)
            other_password = directory / "other-password"
            other_password.write_text("unrelated-case-password")
            other_password.chmod(0o600)
            fixture = directory / "play.yml"
            fixture.write_text(
                yaml.safe_dump(
                    [
                        {
                            "hosts": "localhost",
                            "connection": "local",
                            "gather_facts": False,
                            "tasks": [
                                {
                                    "ansible.builtin.include_tasks": str(
                                        ROOT / "tasks/aap-instance-select.yml"
                                    )
                                },
                                {
                                    "ansible.builtin.include_tasks": str(
                                        ROOT / "tasks/aap-instance-ssh.yml"
                                    )
                                },
                                {
                                    "ansible.builtin.assert": {
                                        "that": [
                                            "aap_hostname == 'https://aap27-test-15.example.invalid'",
                                            "hostvars['aap27-test-15.example.invalid'].ansible_host == '192.0.2.15'",
                                            "'fixture@192.0.2.200' in hostvars['aap27-test-15.example.invalid'].ansible_ssh_common_args",
                                            "hostvars['aap27-test-15.example.invalid'].ansible_ssh_host_key_checking | bool",
                                        ]
                                    }
                                },
                            ],
                        }
                    ]
                )
            )
            env = dict(
                os.environ,
                PATH=str(binaries) + os.pathsep + os.environ["PATH"],
                CAC_GIT_TOKEN="fixture-reader-canary",
                FIXTURE_GIT_REMOTE=str(remote),
                ANSIBLE_ACTION_PLUGINS=str(directory / "action_plugins"),
                ANSIBLE_LIBRARY=str(ROOT / "library"),
                ANSIBLE_FILTER_PLUGINS=str(ROOT / "filter_plugins"),
                ANSIBLE_LOCAL_TEMP=str(directory / "local"),
                ANSIBLE_REMOTE_TEMP=str(directory / "remote"),
            )
            base = [
                sys.executable,
                "-m",
                "ansible.cli.playbook",
                "-i",
                "localhost,",
                "--vault-id",
                "cac@" + str(password),
                str(fixture),
            ]
            for extra, success in (
                ({"aap_instance_key": "aap27-test-15"}, True),
                ({"aap_instance_key": "aap27-test-15",
                  "git_url": "https://untrusted.example.invalid/attacker/project.git",
                  "vault_cac_repository_namespace": "https://untrusted.example.invalid/attacker"}, True),
                ({"aap_instance_key": "unknown"}, False),
                ({"aap_instance_key": "aap27-test-15", "vm_ip": "192.0.2.99"}, False),
                (
                    {
                        "aap_instance_key": "aap27-test-15",
                        "aap_hostname": "https://old.example.invalid",
                    },
                    False,
                ),
            ):
                with self.subTest(extra=extra):
                    result = subprocess.run(
                        base + ["-e", json.dumps(extra)],
                        env=env,
                        text=True,
                        capture_output=True,
                        timeout=45,
                    )
                    self.assertEqual(
                        result.returncode == 0, success, result.stdout + result.stderr
                    )
                    self.assertNotIn(
                        "fixture-reader-canary", result.stdout + result.stderr
                    )
            self.assertEqual(
                git(remote, "rev-list", "--count", "main").stdout.strip(), "1"
            )
            wrong_key = ["cac@" + str(other_password) if value == "cac@" + str(password) else value
                         for value in base]
            refused = subprocess.run(wrong_key + ["-e", json.dumps({"aap_instance_key": "aap27-test-15"})],
                                     env=env, text=True, capture_output=True, timeout=45)
            self.assertNotEqual(refused.returncode, 0)
            self.assertNotIn("fixture-reader-canary", refused.stdout + refused.stderr)


if __name__ == "__main__":
    unittest.main()
