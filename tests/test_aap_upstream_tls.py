"""Exercise upstream trust with real TLS, including refusal of wrong identities."""

import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import socket
import socketserver
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest

import jinja2
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("upstream", ROOT / "files/verify_aap_upstream.py")
upstream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upstream)


@unittest.skipUnless(shutil.which("openssl"), "requires installed OpenSSL")
class UpstreamTrustTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(prefix="upstream-trust-")
        cls.root = Path(cls.workspace.name)
        for name in ("expected", "unrelated"):
            subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                            "-keyout", str(cls.root / (name + ".key")),
                            "-out", str(cls.root / (name + ".pem")), "-days", "1",
                            "-subj", "/CN=Synthetic upstream fixture",
                            "-addext", "subjectAltName=DNS:gateway.example.invalid"],
                           check=True, capture_output=True)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cls.root / "expected.pem", cls.root / "expected.key")
        cls.application_data = []

        class Endpoint(socketserver.BaseRequestHandler):
            def handle(self):
                try:
                    with context.wrap_socket(self.request, server_side=True) as peer:
                        cls.application_data.append(peer.recv(1024))
                except (ssl.SSLError, OSError):
                    pass

        cls.server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Endpoint)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.workspace.cleanup()

    def probe(self, hostname="gateway.example.invalid", authority="expected.pem"):
        return upstream.verify("127.0.0.1", hostname, str(self.root / authority), self.server.server_address[1])

    def test_installed_authority_and_correct_hostname_are_required(self):
        result = self.probe()
        expected = ssl.PEM_cert_to_DER_cert((self.root / "expected.pem").read_text())
        self.assertEqual(result, {"verified": True, "certificate_sha256": hashlib.sha256(expected).hexdigest()})

    def test_unrelated_authority_is_refused(self):
        with self.assertRaises(ssl.SSLCertVerificationError):
            self.probe(authority="unrelated.pem")

    def test_wrong_hostname_is_refused_even_with_the_installed_authority(self):
        with self.assertRaises(ssl.SSLCertVerificationError):
            self.probe(hostname="other.example.invalid")

    def test_missing_authority_is_refused(self):
        with self.assertRaises(ValueError):
            self.probe(authority="missing.pem")

    def test_probe_never_adds_the_authority_to_default_trust(self):
        self.probe()
        with self.assertRaises(ssl.SSLCertVerificationError):
            with socket.create_connection(self.server.server_address, timeout=5) as stream:
                ssl.create_default_context().wrap_socket(stream, server_hostname="gateway.example.invalid")

    def test_probe_sends_no_application_data_or_credentials(self):
        self.probe()
        self.assertTrue(all(data == b"" for data in self.application_data))


class ProxyTemplateTests(unittest.TestCase):
    def render(self, ready):
        environment = jinja2.Environment(undefined=jinja2.StrictUndefined)
        template = environment.from_string((ROOT / "templates/nginx-aap-test.conf.j2").read_text())
        return template.render(vm_name="instance-placeholder", vault_domain="example.invalid",
                               aap_test_subdomain="instance-placeholder", vm_ip="192.0.2.10",
                               aap_upstream_ready=ready)

    def test_new_frontend_has_no_unverified_upstream_before_installation(self):
        output = self.render(False)
        self.assertIn("return 503;", output)
        self.assertNotIn("proxy_pass", output)
        self.assertNotIn("proxy_ssl_verify off", output)

    def test_published_proxy_verifies_chain_hostname_and_sni(self):
        output = self.render(True)
        self.assertIn("proxy_ssl_verify on;", output)
        self.assertIn("proxy_ssl_server_name on;", output)
        self.assertIn("proxy_ssl_name instance-placeholder.example.invalid;", output)
        self.assertIn("proxy_ssl_trusted_certificate /etc/nginx/aap-upstreams/instance-placeholder.pem;", output)
        self.assertNotIn("proxy_ssl_verify off", output)
        self.assertNotIn("return 503;", output)


@unittest.skipUnless(importlib.util.find_spec("ansible"), "requires installed Ansible")
class ProxyPublicationTests(unittest.TestCase):
    def test_upstream_retry_keeps_routing_and_omits_installation(self):
        plays = yaml.safe_load((ROOT / "03-aap-install.yml").read_text())
        with tempfile.TemporaryDirectory(prefix="upstream-retry-tags-") as directory:
            workspace = Path(directory)
            for play in plays:
                play.pop("vars_files", None)
                play.setdefault("vars", {}).update(vault_aap_install_user="synthetic_installer")
            path = workspace / "play.yml"
            path.write_text(yaml.safe_dump(plays, sort_keys=False))
            environment = dict(os.environ, ANSIBLE_NOCOLOR="1",
                ANSIBLE_LOCAL_TEMP=str(workspace / "local"),
                ANSIBLE_ACTION_PLUGINS=str(ROOT / "action_plugins"),
                ANSIBLE_LIBRARY=str(ROOT / "library"))
            command = [sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,target_vm,",
                       str(path), "--list-tasks"]
            full = subprocess.run(command, env=environment, cwd=ROOT,
                                  capture_output=True, text=True, timeout=60)
            retry = subprocess.run(command + ["--tags", "aap_upstream_tls"], env=environment,
                                   cwd=ROOT, capture_output=True, text=True, timeout=60)
            self.assertEqual(full.returncode, 0, full.stdout + full.stderr)
            self.assertEqual(retry.returncode, 0, retry.stdout + retry.stderr)
            self.assertIn("Run AAP installer", full.stdout)
            self.assertIn("Wait for the existing installer result", full.stdout)
            self.assertNotIn("Run AAP installer", retry.stdout)
            self.assertNotIn("Wait for the existing installer result", retry.stdout)
            self.assertNotIn("Grow root filesystem", retry.stdout)
            for name in ("Select the registered instance before any guest connection",
                         "Prepare strict guest trust through the pinned hypervisor",
                         "Verify the installed Gateway against its authenticated local CA",
                         "Publish only a verified upstream after successful installation",
                         "Verify the public Gateway through the trusted proxy"):
                self.assertIn(name, retry.stdout)

    def test_frontend_reload_is_stopped_by_failed_nginx_validation(self):
        handlers = copy.deepcopy(yaml.safe_load((ROOT / "02-infra-config.yml").read_text())[0]["handlers"])
        with tempfile.TemporaryDirectory(prefix="proxy-handler-order-") as directory:
            workspace = Path(directory)
            marker = workspace / "reloaded"
            handlers[0]["ansible.builtin.command"]["argv"] = [sys.executable, "-c", "raise SystemExit(1)"]
            del handlers[1]["ansible.builtin.systemd"]
            handlers[1]["ansible.builtin.command"] = {"argv": [sys.executable, "-c",
                "from pathlib import Path; import sys; Path(sys.argv[1]).touch()", str(marker)]}
            handlers[1]["changed_when"] = True
            play = workspace / "play.yml"
            play.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local", "gather_facts": False,
                "tasks": [{"ansible.builtin.debug": {"msg": "synthetic template change"},
                           "changed_when": True, "notify": "Reload nginx"}], "handlers": handlers}], sort_keys=False))
            environment = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(workspace / "local"),
                               ANSIBLE_REMOTE_TEMP=str(workspace / "remote"), ANSIBLE_NOCOLOR="1")
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(play)],
                                    cwd=workspace, env=environment, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Validate nginx before the TLS frontend reload", result.stdout)
            self.assertFalse(marker.exists(), result.stdout + result.stderr)

    def publish(self, reject=False):
        source = yaml.safe_load((ROOT / "tasks/aap-upstream-trust.yml").read_text())
        block = copy.deepcopy(source[1]["block"][-1])
        with tempfile.TemporaryDirectory(prefix="proxy-publication-") as directory:
            workspace = Path(directory)
            destination = workspace / "instance.conf"
            destination.write_text("previous configuration\n")
            reloads = workspace / "reloads"
            attempts = workspace / "validation-attempts"
            for sequence in (block["block"], block["rescue"]):
                for task in sequence:
                    for module in ("ansible.builtin.template", "ansible.builtin.copy"):
                        if module in task:
                            task[module]["dest"] = str(destination)
                            if module == "ansible.builtin.template":
                                task[module]["src"] = str(ROOT / "templates/nginx-aap-test.conf.j2")
                            task[module].pop("owner", None)
                            task[module].pop("group", None)
                    if "ansible.builtin.command" in task:
                        task["ansible.builtin.command"]["argv"] = [sys.executable, "-c",
                            "import pathlib,sys; p=pathlib.Path(sys.argv[1]); n=int(p.read_text()) if p.exists() else 0; "
                            "p.write_text(str(n+1)); sys.exit(1 if sys.argv[2]=='reject' and n==0 else 0)",
                            str(attempts), "reject" if reject else "accept"]
                    if "ansible.builtin.systemd" in task:
                        del task["ansible.builtin.systemd"]
                        task["ansible.builtin.command"] = {"argv": [sys.executable, "-c",
                            "from pathlib import Path; import sys; Path(sys.argv[1]).write_text(Path(sys.argv[2]).read_text())",
                            str(reloads), str(destination)]}
                        task["changed_when"] = True
            path = workspace / "play.yml"
            path.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local", "gather_facts": False,
                "vars": {"vm_name": "instance-placeholder", "vault_domain": "example.invalid",
                         "aap_test_subdomain": "instance-placeholder", "vm_ip": "192.0.2.10"},
                "tasks": [block]}], sort_keys=False))
            configuration = workspace / "ansible.cfg"
            configuration.write_text("[defaults]\nretry_files_enabled=False\nstdout_callback=default\n")
            environment = dict(os.environ, ANSIBLE_CONFIG=str(configuration), ANSIBLE_NOCOLOR="1",
                               ANSIBLE_LOCAL_TEMP=str(workspace / "local"), ANSIBLE_REMOTE_TEMP=str(workspace / "remote"))
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(path)],
                                    cwd=workspace, env=environment, capture_output=True, text=True, timeout=60)
            return result, destination.read_text(), reloads.read_text() if reloads.exists() else None

    def test_verified_configuration_is_rendered_validated_and_reloaded(self):
        result, content, reloaded = self.publish()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("proxy_ssl_verify on;", content)
        self.assertEqual(content, reloaded)

    def test_invalid_nginx_configuration_restores_the_previous_file_before_reload(self):
        result, content, reloaded = self.publish(reject=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(content, "previous configuration\n")
        self.assertEqual(reloaded, content)
        self.assertIn("Report the failed verified proxy publication", result.stdout)


if __name__ == "__main__":
    unittest.main()
