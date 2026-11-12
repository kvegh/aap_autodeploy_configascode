"""Run the actual Orchestrator build hook with synthetic native action boundaries."""

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class OrchestratorBuildHookTests(unittest.TestCase):
    def test_only_orchestrator_builds_before_resource_rendering(self):
        tasks = yaml.safe_load((ROOT / "deploy-cac-project.yml").read_text())[0]["pre_tasks"][-1]["block"]
        hook = next(i for i, task in enumerate(tasks)
                    if task.get("ansible.builtin.include_tasks") == "tasks/cac-orchestrator-ee.yml")
        normalize = next(i for i, task in enumerate(tasks) if "aap_cac_prepare_resources" in task)
        self.assertLess(hook, normalize)
        self.assertEqual(tasks[hook]["when"], "cac_project_contract.project_id == 'automation-orchestrator'")

    def test_verified_local_image_preserves_foreign_resources_and_bearer_isolation(self):
        self.run_hook("success")

    def test_wrong_target_machine_or_unverified_image_never_changes_desired_resources(self):
        for behavior in ("origin", "registry", "machine", "root-uid", "unverified", "foreign-image", "build-failed"):
            with self.subTest(behavior=behavior):
                self.run_hook(behavior)

    def run_hook(self, behavior):
        origin = "https://aap27.v07.example.invalid"
        physical = "aap27-test-7"
        route = {"vm_name": physical, "vm_ip": "192.0.2.27", "aap_hostname": origin,
                 "guest_host_keys": ["ssh-ed25519 AAAA"],
                 "hypervisor": {"address": "192.0.2.10", "public_ip": "198.51.100.10",
                    "user": "fixture", "port": 22, "machine_id": "b" * 32,
                    "host_keys": ["ssh-ed25519 BBBB"], "isolation_bridges": ["virbr7"],
                    "isolation_dns_bridges": ["virbr7"]}}
        original = [{"name": "Orchestrator EE", "image": "{{ aap_shared_execution_image }}",
                     "organization": "Synthetic", "credential": "Project AAP CaC EE registry", "pull": "missing"},
                    {"name": "Foreign EE", "image": "registry.example.invalid/foreign:stable",
                     "credential": "Other registry", "pull": "always"}]
        target = {"hostname": origin, "route": route, "machine_id": "a" * 32,
                  "ssh_username": "fixture", "ssh_password": "synthetic-ssh-only",
                  "build_user": "fixture-install",
                  "hub_username": "fixture", "hub_password": "synthetic-hub-only"}
        if behavior == "origin":
            target["hostname"] = "https://other.example.invalid"
        with tempfile.TemporaryDirectory(prefix="cac-orchestrator-ee-test-") as directory:
            root = Path(directory)
            actions = root / "action_plugins"
            actions.mkdir()
            trace = root / "trace.jsonl"
            plugin = '''import json
from pathlib import Path
from ansible.plugins.action import ActionBase
class ActionModule(ActionBase):
 def run(self,tmp=None,task_vars=None):
  stage=self._task.args['stage'];row={'stage':stage}
  if stage in ('identity','uid','build'):
   assert self._play_context.remote_addr=='192.0.2.27'
   assert self._play_context.remote_user=='fixture'
   assert self._play_context.become is (stage!='identity')
   if stage!='identity':assert self._play_context.become_user=='fixture-install'
   options=self._connection.get_option('ssh_common_args')
   assert 'StrictHostKeyChecking=yes' in options and 'PasswordAuthentication=no' in options
   assert 'ProxyCommand=' in options
   row['trust']=task_vars['aap_instance_trust']['path']
   assert Path(row['trust']).exists()
  with Path(TRACE).open('a') as stream:stream.write(json.dumps(row)+'\\n')
  if stage=='credential':return {'changed':False,'id':123}
  if stage=='registry':return {'changed':False,'json':{'inputs':{'host':'other.example.invalid' if task_vars['behavior']=='registry' else 'aap27.v07.example.invalid','verify_ssl':True,'username':'fixture'}}}
  if stage=='identity':return {'changed':False,'stdout':('c' if task_vars['behavior']=='machine' else 'a')*32}
  if stage=='uid':return {'changed':False,'stdout':'0' if task_vars['behavior']=='root-uid' else '1007'}
  if stage=='build':
   environment={};self._compute_environment_string(raw_environment_out=environment)
   assert environment['XDG_RUNTIME_DIR']=='/run/user/1007'
   if task_vars['behavior']=='build-failed':return {'failed':True,'msg':'Synthetic build failure'}
   assert self._task.args['registry']=='aap27.v07.example.invalid'
   assert self._task.args['username']=='fixture'
   assert self._task.args['password']=='synthetic-hub-only'
   assert self._task.args['redhat_username']=='synthetic-upstream'
   image=('foreign.example.invalid' if task_vars['behavior']=='foreign-image' else 'aap27.v07.example.invalid')+'/ee-proj-aap-cac@sha256:'+'2'*64
   return {'changed':False,'ansible_facts':{'aap_ee_build_result':{'verified':task_vars['behavior']!='unverified','image':image}}}
  return {'changed':False}
'''.replace("TRACE", repr(str(trace)))
            (actions / "build_hook_probe.py").write_text(plugin)
            stub = [{"name": "Prove the included build receives receiver-local protected parameters",
                     "build_hook_probe": {"stage": "build", "registry": "{{ aap_ee_registry }}",
                         "username": "{{ aap_ee_registry_username }}", "password": "{{ aap_ee_registry_password }}",
                         "redhat_username": "{{ aap_ee_redhat_username }}"}}]
            stub_file = root / "build.yml"
            stub_file.write_text(yaml.safe_dump(stub))
            helper = deepcopy(yaml.safe_load((ROOT / "tasks/cac-orchestrator-ee.yml").read_text()))

            def prepare(tasks):
                for task in tasks:
                    task["no_log"] = False  # These are synthetic fixtures only.
                    if "ansible.controller.credential" in task:
                        task.pop("ansible.controller.credential")
                        task["build_hook_probe"] = {"stage": "credential"}
                    if "ansible.builtin.command" in task:
                        command = task.pop("ansible.builtin.command")
                        task["build_hook_probe"] = {"stage": "uid" if command['argv'] == ['id', '-u'] else "identity"}
                    if "ansible.builtin.uri" in task:
                        task.pop("ansible.builtin.uri")
                        task["build_hook_probe"] = {"stage": "registry"}
                    include = task.get("ansible.builtin.include_tasks")
                    if include == "aap-instance-ssh.yml":
                        task["ansible.builtin.include_tasks"] = str(ROOT / "tasks/aap-instance-ssh.yml")
                    if isinstance(include, dict):
                        include["file"] = str(stub_file)
                    for key in ("block", "always", "rescue"):
                        prepare(task.get(key, []))

            prepare(helper)
            helper_file = root / "hook.yml"
            helper_file.write_text(yaml.safe_dump(helper, sort_keys=False))
            variables = {"behavior": behavior, "aap_instance_key": physical,
                         "cac_project_contract": {"project_id": "automation-orchestrator"},
                         "cac_import_metadata": {"resource_variables": {"controller_execution_environments": "controller_execution_environments_orchestrator"}},
                         "cac_api_auth": {"hostname": origin, "token": "synthetic-bearer"},
                         "orchestrator_ee_build_targets": {physical: target},
                         "orchestrator_registry_username": "synthetic-upstream",
                         "orchestrator_registry_password": "synthetic-upstream-only",
                         "controller_execution_environments_orchestrator": original,
                         "aap_username": "", "aap_password": ""}
            play = root / "play.yml"
            play.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local", "gather_facts": False,
                "vars": variables, "tasks": [
                    {"ansible.builtin.add_host": {"name": physical, "ansible_host": route["vm_ip"],
                        "ansible_fqdn": "aap27.v07.example.invalid", "host_keys": route["guest_host_keys"]}},
                    {"ansible.builtin.include_tasks": str(helper_file)},
                    {"ansible.builtin.assert": {"that": [
                        "controller_execution_environments_orchestrator[0].image == aap_ee_build_result.image",
                        "controller_execution_environments_orchestrator[0].name == 'Orchestrator EE'",
                        "controller_execution_environments_orchestrator[0].pull == 'missing'",
                        "controller_execution_environments_orchestrator[1] == " + repr(original[1]),
                        "aap_username == ''", "aap_password == ''"]}}]}], sort_keys=False))
            env = dict(os.environ, ANSIBLE_HOME=str(root / "home"), ANSIBLE_LOCAL_TEMP=str(root / "local"),
                       ANSIBLE_REMOTE_TEMP=str(root / "remote"), ANSIBLE_ACTION_PLUGINS=str(actions),
                       ANSIBLE_FILTER_PLUGINS=str(ROOT / "filter_plugins"), ANSIBLE_NOCOLOR="1")
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(play)],
                                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode == 0, behavior == "success", result.stdout + result.stderr)
            rows = [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []
            stages = [row["stage"] for row in rows]
            self.assertEqual("build" in stages, behavior not in ("origin", "registry", "machine", "root-uid"), result.stdout + result.stderr)
            for row in rows:
                if "trust" in row:
                    self.assertFalse(Path(row["trust"]).exists(), result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
