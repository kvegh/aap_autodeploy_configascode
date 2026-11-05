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
                     "src/aap_name_allocation.py", "src/aap_hypervisor_access.py", "filter_plugins/cac_import.py"):
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    (project / "myvars").write_bytes(vault.encrypt(yaml.safe_dump({
        "git_url": "https://git.example.invalid/fixture-owner/aap_autodeploy_configascode.git",
    }), vault_id="cac"))
    return project


def primary_fixture():
    route = RoutingTests().route()
    domain = ('<domain><name>aap27-test-15</name><uuid>aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee</uuid>'
        '<devices><disk device="disk"><source file="/opt/vms/aap27-test-15.disk.qcow2" index="1"/></disk>'
        '<interface type="network"><mac address="52:54:00:00:00:15"/>'
        '<source network="isolated" bridge="virbr0"/></interface></devices></domain>')
    network = '<network><name>isolated</name><bridge name="virbr0"/></network>'
    resource = routing.primary_resources(route, domain, network, 'isolated')
    return route, domain, network, resource


class AllocationTests(unittest.TestCase):
    def test_primary_ownership_is_published_atomically_and_preserves_other_aap_state(self):
        request = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        state, _ = allocation.reserve(self.state(), "aap27-test", request, "1" * 32)
        state["unrelated"] = {"keep": True}
        original = copy.deepcopy(state)
        route, domain, network, resource = primary_fixture()
        published, record = allocation.publish_route(state, request, route, {"aap": resource})
        self.assertEqual(state, original)
        self.assertEqual(published["next_number"], state["next_number"])
        self.assertEqual(record["instance_route"], route)
        self.assertEqual(record["instance_resources"], {"aap": resource})
        self.assertEqual(published["unrelated"], state["unrelated"])
        self.assertEqual(allocation.publish_route(published, request, route, {"aap": resource})[0], published)
        self.assertEqual(allocation.publish_route(published, request, route)[0], published)
        changed = dict(resource, uuid="bbbbbbbb-cccc-dddd-eeee-ffffffffffff")
        with self.assertRaises(ValueError):
            allocation.publish_route(published, request, route, {"aap": changed})
        published["reservations"][request]["decommissioned"] = True
        with self.assertRaises(ValueError):
            allocation.publish_route(published, request, route, {"aap": resource})
        app_data = copy.deepcopy(state)
        app_data["reservations"][request]["instance_resources"] = {"tra": {"keep": True}}
        with self.assertRaises(ValueError):
            allocation.publish_route(app_data, request, route, {"aap": resource})

    def test_incomplete_foreign_or_extra_primary_ownership_fields_are_refused(self):
        request = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        state, _ = allocation.reserve(self.state(), "aap27-test", request, "1" * 32)
        route, domain, network, resource = primary_fixture()
        for field, value in (("uuid", "invalid"), ("disk", "/opt/vms/other.disk.qcow2"),
                             ("address", "192.0.2.99"), ("mac", "ff:ff:ff:ff:ff:ff"),
                             ("bridge", "foreign0"), ("network", "--all"),
                             ("verified", "true"), ("hypervisor_machine_id", "2" * 32),
                             ("private_key", "forbidden")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                allocation.publish_route(state, request, route, {"aap": dict(resource, **{field: value})})
        for invalid in ({}, {"tra": resource}, {"aap": {}}, {"aap": resource, "tra": {}}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                allocation.publish_route(state, request, route, invalid)

    def test_primary_metadata_argument_needs_route_before_any_git_access(self):
        action = load("primary_resource_argument", ROOT / "action_plugins/aap_reserve_vm_name.py")
        plugin = action.ActionModule.__new__(action.ActionModule)
        plugin._task = SimpleNamespace(args={"instance_resources": {"aap": {}}})
        with mock.patch.object(ActionBase, "run", return_value={}), mock.patch.object(
                action.subprocess, "run", side_effect=AssertionError("No Git operation allowed")):
            with self.assertRaisesRegex(AnsibleActionFail, "only with"):
                plugin.run(task_vars={})

    def test_live_primary_xml_requires_exact_name_disk_uuid_mac_and_pinned_network(self):
        route, domain, network, resource = primary_fixture()
        self.assertTrue(resource["verified"])
        for changed_domain, changed_network in (
                (domain.replace('<name>aap27-test-15', '<name>other'), network),
                (domain.replace('aap27-test-15.disk', 'other.disk'), network),
                (domain.replace('aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', 'invalid'), network),
                (domain.replace('52:54:00:00:00:15', 'ff:ff:ff:ff:ff:ff'), network),
                (domain.replace('</devices>', '<disk device="disk"/></devices>'), network),
                (domain.replace('</devices>', '<interface type="network"/></devices>'), network),
                (domain.replace('network="isolated"', 'network="foreign"'), network),
                (domain, network.replace('name="virbr0"', 'name="foreign0"')),
                (domain, network.replace('<name>isolated', '<name>other'))):
            with self.subTest(domain=changed_domain, network=changed_network), self.assertRaises(routing.AnsibleFilterError):
                routing.primary_resources(route, changed_domain, changed_network, 'isolated')

    def test_stage_one_publishes_only_actual_xml_resource_after_pinned_guest_probe(self):
        from ansible.parsing.dataloader import DataLoader
        from ansible.template import Templar
        source = yaml.safe_load((ROOT / "01-linux-vm-setup.yml").read_text())[0]["tasks"]
        publication = next(task for task in source if "aap_reserve_vm_name" in task)
        probe = next(index for index, task in enumerate(source) if task["name"] ==
                     "Verify the fresh guest through its exact pinned hypervisor route")
        self.assertLess(probe, source.index(publication))
        self.assertTrue(source[probe]["no_log"])
        route, domain, network, resource = primary_fixture()
        variables = {"aap_instance_route": route, "aap_primary_domain_ownership": {"stdout": domain},
            "aap_primary_network_ownership": {"stdout": network}, "vm_network": "isolated",
            "instance_resources": {"aap": {"uuid": "caller-supplied"}}, "aap_primary_resource": {"uuid": "caller-supplied"}}
        templar = Templar(loader=DataLoader(), variables=variables)
        templar.environment.filters["aap_primary_instance_resources"] = routing.primary_resources
        self.assertEqual(templar.template(publication["aap_reserve_vm_name"]["instance_resources"]), {"aap": resource})

    def test_native_primary_probe_uses_original_host_route_and_pinned_jump_without_direct_ssh(self):
        import sys
        source = yaml.safe_load((ROOT / "01-linux-vm-setup.yml").read_text())[0]["tasks"]
        block = copy.deepcopy(next(task for task in source if task["name"] ==
                                   "Verify the fresh guest through its exact pinned hypervisor route"))
        block["block"] = [task for task in block["block"]
                          if task["name"] != "Wait for authenticated guest readiness without another connection path"]
        task = next(task for task in block["block"] if "ansible.builtin.command" in task)
        task.pop("ansible.builtin.command")
        task["ansible.builtin.raw"] = "cat /etc/machine-id"
        block["no_log"] = False  # Synthetic inputs only; production inherits protected logging.
        with tempfile.TemporaryDirectory(prefix="primary-probe-route-") as temporary:
            directory = Path(temporary)
            calls, executable = directory / "ssh.json", directory / "ssh"
            identity = "b" * 32
            executable.write_text("#!" + sys.executable + "\nimport json,sys\nfrom pathlib import Path\n"
                + "Path(%r).write_text(json.dumps(sys.argv[1:]))\nprint(%r)\n" % (str(calls), identity))
            executable.chmod(0o700)
            route = primary_fixture()[0]
            route["hypervisor"]["port"] = 2222
            trust = directory / "known-hosts"
            trust.write_text("synthetic fixture only\n")
            inventory = {"all": {"hosts": {"original_hypervisor": {"aap_instance_route": route,
                "aap_hypervisor_pin": route["hypervisor"], "aap_hypervisor_trust": {"path": str(trust)},
                "aap_primary_guest_login": {"user": "synthetic_guest", "password": "synthetic-guest-password"}}}}}
            (directory / "inventory.yml").write_text(yaml.safe_dump(inventory))
            play = [{"hosts": "original_hypervisor", "gather_facts": False,
                "vars": {"ansible_ssh_executable": str(executable), "ansible_user": "wrong_outer_user"}, "tasks": [block]}]
            (directory / "play.yml").write_text(yaml.safe_dump(play, sort_keys=False))
            env = dict(os.environ, ANSIBLE_NOCOLOR="1", ANSIBLE_FILTER_PLUGINS=str(ROOT / "filter_plugins"),
                ANSIBLE_SSH_CONTROL_PATH_DIR=str(directory / "cp"), ANSIBLE_LOCAL_TEMP=str(directory / "local"))
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", str(directory / "inventory.yml"),
                str(directory / "play.yml")], env=env, text=True, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            arguments = calls.read_text()
            self.assertIn('ProxyCommand=', arguments)
            self.assertIn(' -W %h:%p ', arguments)
            self.assertIn(route["hypervisor"]["address"], arguments)
            self.assertIn('2222', arguments)
            self.assertIn('StrictHostKeyChecking=yes', arguments)
            self.assertIn('HostKeyAlias=aap27-test-15.example.invalid', arguments)
            self.assertIn('synthetic_guest', arguments)
            self.assertNotIn('wrong_outer_user', arguments)
            self.assertNotIn('synthetic-guest-password', arguments)
            calls.unlink()
            refused = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", str(directory / "inventory.yml"),
                str(directory / "play.yml"), "-e", json.dumps({"ansible_host": "198.51.100.99"})],
                env=env, text=True, capture_output=True, timeout=60)
            self.assertNotEqual(refused.returncode, 0)
            self.assertFalse(calls.exists(), refused.stdout + refused.stderr)

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
                                {
                                    "name": "Publish the verified fixture primary ownership in the same route transaction",
                                    "aap_reserve_vm_name": {
                                        "prefix": "aap27-test", "hypervisor_id": "1" * 32,
                                        "request_id": "{{ reservation.request_id }}",
                                        "instance_route": primary_fixture()[0],
                                        "instance_resources": {"aap": primary_fixture()[3]},
                                    },
                                    "when": "not ansible_check_mode", "no_log": True,
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
            published = AnsibleLoader(vault.decrypt(accepted)).get_single_data()["aap_vm_allocation"]
            self.assertEqual(next(iter(published["reservations"].values()))["instance_resources"]["aap"], primary_fixture()[3])


class RoutingTests(unittest.TestCase):
    def test_native_verify_ssl_strings_preserve_the_exact_dns_and_tls_guard(self):
        from ansible.errors import AnsibleError
        from ansible.parsing.dataloader import DataLoader
        from ansible.playbook.conditional import Conditional
        from ansible.template import Templar

        task = yaml.safe_load((ROOT / 'tasks/aap-instance-api.yml').read_text())[1]
        route = self.route()
        for flag, address, accepted in (
            (True, route['hypervisor']['public_ip'], True),
            ('True', route['hypervisor']['public_ip'], True),
            ('true', route['hypervisor']['public_ip'], True),
            (False, route['hypervisor']['public_ip'], False),
            ('False', route['hypervisor']['public_ip'], False),
            ('True', '198.51.100.254', False),
        ):
            with self.subTest(flag=flag, address=address):
                variables = {'aap_instance_route': route, 'aap_hostname': route['aap_hostname'],
                             'aap_validate_certs': flag}
                loader = DataLoader()
                templar = Templar(loader=loader, variables=variables)
                templar.environment.globals['query'] = lambda *args, **kwargs: (
                    [address] if kwargs.get('qtype') == 'A' else [])
                templar.environment.filters['aap_instance_api_dns'] = routing.instance_api_dns
                condition = Conditional(loader=loader)
                condition.when = [task['ansible.builtin.assert']['that']]
                if accepted:
                    self.assertTrue(condition.evaluate_conditional(templar, variables))
                else:
                    with self.assertRaises(AnsibleError):
                        condition.evaluate_conditional(templar, variables)

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

    def test_local_host_policy_is_exact_bounded_and_does_not_change_default_isolation(self):
        pin = self.route()["hypervisor"]
        baseline = routing.isolation_policy(pin)
        client = {"bridge": "virbr0", "ipv4": "192.0.2.15", "mac": "52:54:00:00:00:15",
                  "destinations": ["192.0.2.200"], "ports": [2222]}
        self.assertEqual(routing.isolation_policy(pin, guest_host_clients=[client]),
                         dict(baseline, guest_host_clients=[client]))
        self.assertEqual(routing.isolation_policy(pin, guest_host_clients=[]), baseline)
        invalid = [dict(client, bridge="other"), dict(client, destinations=["0.0.0.0"]),
                   dict(client, destinations=["192.0.2.200", "192.0.2.200"]),
                   dict(client, ports=[True]), dict(client, ports=[0]),
                   dict(client, ports=[2222, 2222]), dict(client, mac="00:00:00:00:00:00"),
                   dict(client, protocol="all")]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(routing.AnsibleFilterError):
                routing.isolation_policy(pin, guest_host_clients=[value])
        with self.assertRaises(routing.AnsibleFilterError):
            routing.isolation_policy(pin, guest_host_clients=[client, client])

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
