"""Exercise Windows' existing-credential guard through native Ansible tasks."""

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
NAMES = ["AAP CaC source reader", "AAP CaC source CA"]


class WindowsSourcePrerequisiteTests(unittest.TestCase):
    def test_guard_runs_after_validation_before_resource_dispatch(self):
        block = yaml.safe_load((ROOT / "deploy-cac-project.yml").read_text())[0]["pre_tasks"][-1]["block"]
        guard = next(i for i, task in enumerate(block) if task.get("ansible.builtin.include_tasks") ==
                     "tasks/cac-windows-source-prerequisites.yml")
        validate = next(i for i, task in enumerate(block) if task.get("name") ==
                        "Validate activation relationships and protected embedded configuration inputs")
        dispatch = next(i for i, task in enumerate(block) if task.get("ansible.builtin.include_tasks") ==
                        "tasks/cac-resource-definitions.yml")
        self.assertLess(validate, guard)
        self.assertLess(guard, dispatch)
        self.assertFalse(block[guard]["no_log"])

    def test_existing_matching_credentials_allow_dispatch_with_selected_ca(self):
        self.run_guard("valid", supplemental_ca=True)

    def test_existing_matching_credentials_allow_dispatch_with_default_trust(self):
        self.run_guard("valid")

    def test_missing_either_credential_refuses_before_dispatch(self):
        for behavior in ("missing-reader", "missing-ca"):
            with self.subTest(behavior=behavior):
                self.run_guard(behavior)

    def test_duplicate_wrong_owner_or_wrong_type_refuses_before_dispatch(self):
        for behavior in ("duplicate", "organization", "type", "name"):
            with self.subTest(behavior=behavior):
                self.run_guard(behavior)

    def test_incomplete_or_invalid_native_metadata_refuses_before_dispatch(self):
        for behavior in ("next-page", "boolean-count", "missing-owner"):
            with self.subTest(behavior=behavior):
                self.run_guard(behavior)

    def test_non_windows_import_skips_all_windows_credential_reads(self):
        self.run_guard("missing-reader", project="aap_autodeploy_configascode")

    def run_guard(self, behavior, project="disconnected-windows-patching", supplemental_ca=False):
        with tempfile.TemporaryDirectory(prefix="windows-source-prerequisites-") as directory:
            root = Path(directory)
            actions = root / "action_plugins"
            actions.mkdir()
            trace = root / "trace.jsonl"
            code = '''import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from ansible.plugins.action import ActionBase
class ActionModule(ActionBase):
 def run(self,tmp=None,task_vars=None):
  args=self._task.args
  if args.get('dispatch'):
   row={'stage':'dispatch'}
   with Path(TRACE).open('a') as stream:stream.write(json.dumps(row)+'\\n')
   return {'changed':False}
  assert args['method']=='GET' and 'body' not in args
  assert args['headers']=={'Authorization':'Bearer synthetic-bearer'}
  assert args['validate_certs'] is True and args['follow_redirects']=='none'
  assert args['status_code']==200 and args['timeout']==10
  if task_vars['supplemental_ca']:assert args['ca_path']=='/synthetic/selected-api-ca.pem'
  else:assert 'ca_path' not in args
  parsed=urlsplit(args['url']);assert parsed.scheme=='https' and parsed.netloc=='receiver.example.invalid'
  assert parsed.path=='/api/controller/v2/credentials/'
  query=parse_qs(parsed.query);assert set(query)=={'name','page_size'} and query['page_size']==['2']
  name=query['name'][0];assert name in NAMES
  with Path(TRACE).open('a') as stream:stream.write(json.dumps({'stage':'read','name':name})+'\\n')
  behavior=task_vars['behavior'];missing=(behavior=='missing-reader' and name==NAMES[0]) or (behavior=='missing-ca' and name==NAMES[1])
  row={'id':91 if name==NAMES[0] else 92,'name':name,'summary_fields':{
   'organization':{'id':1,'name':'Example organization'},'credential_type':{'id':31,'name':name}}}
  if name==NAMES[0]:
   if behavior=='organization':row['summary_fields']['organization']['name']='Another organization'
   if behavior=='type':row['summary_fields']['credential_type']['name']='Another type'
   if behavior=='name':row['name']='Another credential'
   if behavior=='missing-owner':del row['summary_fields']['organization']
  results=[] if missing else [row]
  if behavior=='duplicate' and name==NAMES[0]:results.append(dict(row,id=93))
  value={'count':len(results),'next':None,'results':results}
  if behavior=='next-page' and name==NAMES[0]:value['next']='https://receiver.example.invalid/api/controller/v2/credentials/?page=2'
  if behavior=='boolean-count' and name==NAMES[0]:value['count']=True
  return {'changed':False,'status':200,'json':value}
'''.replace("TRACE", repr(str(trace))).replace("NAMES", repr(NAMES))
            (actions / "fixture_source_credential_read.py").write_text(code)
            helper = deepcopy(yaml.safe_load((ROOT / "tasks/cac-windows-source-prerequisites.yml").read_text()))
            for task in helper:
                self.assertFalse(task["no_log"])
                if "ansible.builtin.uri" in task:
                    task["fixture_source_credential_read"] = task.pop("ansible.builtin.uri")
            helper_file = root / "guard.yml"
            helper_file.write_text(yaml.safe_dump(helper, sort_keys=False))
            block = yaml.safe_load((ROOT / "deploy-cac-project.yml").read_text())[0]["pre_tasks"][-1]["block"]
            include = deepcopy(next(task for task in block if task.get("ansible.builtin.include_tasks") ==
                                    "tasks/cac-windows-source-prerequisites.yml"))
            include["ansible.builtin.include_tasks"] = str(helper_file)
            variables = {"behavior": behavior, "supplemental_ca": supplemental_ca,
                         "cac_project_contract": {"project_id": project},
                         "cac_api_auth": {"hostname": "https://receiver.example.invalid", "token": "synthetic-bearer"},
                         "aap_request_timeout": 10.0, "windows_disconnected_organization_name": "Example organization"}
            if supplemental_ca:
                variables["cac_api_ca_path"] = "/synthetic/selected-api-ca.pem"
            play = root / "play.yml"
            play.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local", "gather_facts": False,
                "vars": variables, "tasks": [include, {"name": "Synthetic resource dispatch marker",
                                                       "fixture_source_credential_read": {"dispatch": True}}]}], sort_keys=False))
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith(("AAP_", "TOWER_", "CONTROLLER_"))}
            environment.update(ANSIBLE_HOME=str(root / "home"), ANSIBLE_LOCAL_TEMP=str(root / "local"),
                               ANSIBLE_REMOTE_TEMP=str(root / "remote"), ANSIBLE_ACTION_PLUGINS=str(actions),
                               ANSIBLE_NOCOLOR="1")
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(play)],
                                    cwd=ROOT, env=environment, capture_output=True, text=True, timeout=45)
            allowed = behavior == "valid" or project != "disconnected-windows-patching"
            self.assertEqual(result.returncode == 0, allowed, result.stdout + result.stderr)
            rows = [json.loads(line) for line in trace.read_text().splitlines()]
            reads = [row["name"] for row in rows if row["stage"] == "read"]
            self.assertEqual(reads, NAMES if project == "disconnected-windows-patching" else [])
            self.assertEqual(sum(row["stage"] == "dispatch" for row in rows), int(allowed))
            if not allowed:
                self.assertIn("Run normal AutoDeploy CaC", result.stdout)


if __name__ == "__main__":
    unittest.main()
