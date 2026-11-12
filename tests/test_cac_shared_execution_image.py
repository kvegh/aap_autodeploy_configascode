"""Resolve receiver-owned native EE data before real capture normalization."""

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
IMAGE = "receiver.example.invalid/ee-proj-aap-cac@sha256:" + "2" * 64


class SharedExecutionImageTests(unittest.TestCase):
    def test_both_importers_resolve_before_rendering_owned_ee_definitions(self):
        generic = yaml.safe_load((ROOT / "deploy-cac-project.yml").read_text())[0]["pre_tasks"][-1]["block"]
        resolve = next(i for i, task in enumerate(generic)
                       if task.get("ansible.builtin.include_tasks") == "tasks/cac-shared-execution-image.yml")
        normalize = next(i for i, task in enumerate(generic) if "aap_cac_prepare_resources" in task)
        build = next(i for i, task in enumerate(generic)
                     if task.get("ansible.builtin.include_tasks") == "tasks/cac-orchestrator-ee.yml")
        self.assertLess(build, resolve)
        self.assertLess(resolve, normalize)
        separate = yaml.safe_load((ROOT / "tasks/autodeploy-config.yml").read_text())
        resolve = next(i for i, task in enumerate(separate)
                       if task.get("ansible.builtin.include_tasks") == "cac-shared-execution-image.yml")
        role = next(i for i, task in enumerate(separate)
                    if task.get("ansible.builtin.include_role", {}).get("name") ==
                    "infra.aap_configuration.controller_execution_environments")
        self.assertLess(resolve, role)

    def test_native_readback_binds_only_explicit_owned_image_references(self):
        self.run_binding("success")
        self.run_binding("orchestrator")

    def test_missing_foreign_mutable_or_unverified_bindings_fail_before_import(self):
        for behavior in ("missing", "foreign-image", "mutable", "credential-name", "credential-host", "tls", "build-mismatch"):
            with self.subTest(behavior=behavior):
                self.run_binding(behavior)

    def run_binding(self, behavior):
        with tempfile.TemporaryDirectory(prefix="cac-shared-ee-test-") as directory:
            root = Path(directory)
            actions = root / "action_plugins"
            actions.mkdir()
            trace = root / "trace.jsonl"
            code = '''import json
from pathlib import Path
from ansible.plugins.action import ActionBase
class ActionModule(ActionBase):
 def run(self,tmp=None,task_vars=None):
  stage=self._task.args['stage'];behavior=task_vars['behavior']
  with Path(TRACE).open('a') as stream:stream.write(json.dumps({'stage':stage})+'\\n')
  if stage=='resolve':
   assert self._task.args['name']=='ee-proj-aap-cac'
   assert self._task.args['state']=='exists'
   assert self._task.args['controller_host']=='https://receiver.example.invalid'
   assert self._task.args['controller_oauthtoken']=='synthetic-bearer'
   assert self._task.args['validate_certs'] is True
   if behavior=='missing':return {'failed':True,'msg':'Synthetic missing EE'}
   return {'changed':False,'id':70}
  assert self._task.args['validate_certs'] is True
  assert self._task.args['follow_redirects']=='none'
  assert self._task.args['headers']['Authorization']=='Bearer synthetic-bearer'
  if '/execution_environments/' in self._task.args['url']:
   image=IMAGE
   if behavior=='foreign-image':image=image.replace('receiver.example.invalid','source.example.invalid')
   if behavior=='mutable':image='receiver.example.invalid/ee-proj-aap-cac:2.0.0'
   return {'changed':False,'json':{'id':70,'name':'ee-proj-aap-cac','image':image,'credential':71}}
  assert self._task.args['url']=='https://receiver.example.invalid/api/controller/v2/credentials/71/'
  return {'changed':False,'json':{'id':71,'name':'Wrong credential' if behavior=='credential-name' else 'Project AAP CaC EE registry',
   'inputs':{'host':'source.example.invalid' if behavior=='credential-host' else 'receiver.example.invalid','verify_ssl':behavior!='tls'}}}
'''.replace("TRACE", repr(str(trace))).replace("IMAGE", repr(IMAGE))
            (actions / "native_ee_probe.py").write_text(code)
            helper = deepcopy(yaml.safe_load((ROOT / "tasks/cac-shared-execution-image.yml").read_text()))
            for task in helper:
                task["no_log"] = False  # Synthetic fixture only.
                if "ansible.controller.execution_environment" in task:
                    task["native_ee_probe"] = dict(task.pop("ansible.controller.execution_environment"), stage="resolve")
                if "ansible.builtin.uri" in task:
                    task["native_ee_probe"] = dict(task.pop("ansible.builtin.uri"), stage="readback")
            helper_file = root / "bind.yml"
            helper_file.write_text(yaml.safe_dump(helper, sort_keys=False))
            project = "automation-orchestrator" if behavior in ("orchestrator", "build-mismatch") else "assistant-team"
            variables = {"behavior": behavior, "aap_hostname": "https://receiver.example.invalid", "aap_token": "synthetic-bearer",
                         "aap_username": "", "aap_password": "", "aap_validate_certs": True,
                         "cac_project_contract": {"project_id": project},
                         "cac_import_metadata": {"schema_version": 1, "project_id": project,
                             "required_template_label": "Synthetic", "resource_variables": {"controller_execution_environments": "captured.execution_environments"},
                             "checks": {}, "capabilities": {}},
                         "captured": {"execution_environments": [
                             {"name": "Owned EE", "image": "{{ aap_shared_execution_image }}", "credential": "Project AAP CaC EE registry"},
                             {"name": "Foreign EE", "image": "other.example.invalid/foreign:stable", "credential": "Foreign registry"}]},
                         "aap_ee_build_result": {"verified": True, "image": IMAGE if behavior != "build-mismatch" else IMAGE[:-1] + "3"}}
            play = root / "play.yml"
            play.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local", "gather_facts": False,
                "vars": variables, "tasks": [{"ansible.builtin.include_tasks": str(helper_file)},
                    {"aap_cac_prepare_resources": {}},
                    {"ansible.builtin.assert": {"that": [
                        "aap_shared_execution_image == '" + IMAGE + "'",
                        "cac_import_resources.controller_execution_environments[0].image == aap_shared_execution_image",
                        "cac_import_resources.controller_execution_environments[0].name == 'Owned EE'",
                        "cac_import_resources.controller_execution_environments[1].image == 'other.example.invalid/foreign:stable'",
                        "cac_import_resources.controller_execution_environments[1].credential == 'Foreign registry'",
                        "aap_username == ''", "aap_password == ''"]}}]}], sort_keys=False))
            env = dict(os.environ, ANSIBLE_HOME=str(root / "home"), ANSIBLE_LOCAL_TEMP=str(root / "local"),
                       ANSIBLE_REMOTE_TEMP=str(root / "remote"), ANSIBLE_ACTION_PLUGINS=os.pathsep.join((str(actions), str(ROOT / "action_plugins"))),
                       ANSIBLE_FILTER_PLUGINS=str(ROOT / "filter_plugins"), ANSIBLE_NOCOLOR="1")
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(play)],
                                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode == 0, behavior in ("success", "orchestrator"), result.stdout + result.stderr)
            rows = [json.loads(line) for line in trace.read_text().splitlines()]
            self.assertEqual(rows[0]["stage"], "resolve")


if __name__ == "__main__":
    unittest.main()
