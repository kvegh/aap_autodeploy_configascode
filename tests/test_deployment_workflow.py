"""Check deployment ordering, artifact boundaries, and exact-version batching."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    import yaml
    from jinja2 import Environment, StrictUndefined
except ImportError:
    yaml = None


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(yaml, "requires installed PyYAML and Jinja")
class DeploymentWorkflowTests(unittest.TestCase):
    def graph(self):
        environment = Environment(undefined=StrictUndefined)
        environment.filters["to_json"] = json.dumps
        template = environment.from_string((ROOT / "templates/deployment-workflow-nodes.yml.j2").read_text())
        return yaml.safe_load(template.render(cac_workflow={"organization": "Synthetic organization"}))

    def test_base_deployment_stops_after_shared_configuration(self):
        nodes = self.graph()
        by_id = {node["identifier"]: node for node in nodes}
        self.assertEqual(len(nodes), len(by_id))
        self.assertEqual(len(nodes), 4)
        parents = {identifier: [] for identifier in by_id}
        for node in nodes:
            self.assertEqual(node["related"]["always_nodes"], [])
            self.assertEqual(node["related"]["failure_nodes"], [])
            self.assertNotRegex(node["unified_job_template"]["name"].lower(), "destroy|teardown|cleanup")
            for child in node["related"]["success_nodes"]:
                self.assertIn(child["identifier"], by_id)
                parents[child["identifier"]].append(node["identifier"])
        expected_chain = ["create_vm", "configure_infrastructure", "install_aap", "configure_base"]
        self.assertEqual(parents[expected_chain[0]], [])
        for parent, child in zip(expected_chain, expected_chain[1:]):
            self.assertEqual(parents[child], [parent])
        self.assertEqual(by_id["configure_base"]["related"]["success_nodes"], [])
        self.assertEqual([by_id[key]["unified_job_template"]["name"] for key in expected_chain], [
            "Deploy AAP on Rebuild Hypervisor - 01 VM Setup",
            "Deploy AAP on Rebuild Hypervisor - 02 Infrastructure",
            "Deploy AAP on Rebuild Hypervisor - 03 Install AAP",
            "Deploy AAP on Rebuild Hypervisor - 04 Base Configuration"])
        self.assertTrue(all(not node.get("extra_data") for node in nodes))

    def test_nodes_do_not_pin_an_old_target_or_pass_secrets_as_artifacts(self):
        nodes = self.graph()
        for node in nodes:
            self.assertFalse(node.get("extra_data"))
            self.assertNotIn("credentials", node["related"])
        provision = yaml.safe_load((ROOT / "01-linux-vm-setup.yml").read_text())[0]
        artifact = next(task["ansible.builtin.set_stats"] for task in provision["tasks"]
                        if task.get("name") == "Pass only the verified new instance handoff to downstream jobs")
        self.assertEqual(set(artifact["data"]), {"aap_instance_key", "vm_name", "vm_ip", "aap_hostname", "aap_instance_route"})
        self.assertEqual(artifact["data"]["aap_instance_key"], "{{ aap_instance_route.vm_name }}")
        self.assertEqual(artifact["data"]["aap_hostname"], "{{ aap_instance_route.aap_hostname }}")
        self.assertFalse(artifact["per_host"])
        self.assertFalse(artifact["aggregate"])
        installer = yaml.safe_load((ROOT / "03-aap-install.yml").read_text())[-1]
        self.assertNotIn("aap_hostname", installer["vars"])
        self.assertEqual(installer["vars"]["aap_installer_hostname"], "{{ aap_hostname | ansible.builtin.urlsplit('hostname') }}")

    @unittest.skipUnless(importlib.util.find_spec("ansible"), "requires installed Ansible")
    def test_native_factory_replaces_old_ten_node_graph_without_deleting_job_templates(self):
        self.run_factory('captured')
        self.run_factory('direct')
        self.run_factory('conflicting-capture')

    def run_factory(self, mode):
        with tempfile.TemporaryDirectory(prefix='base-workflow-factory-') as directory:
            folder=Path(directory);actions=folder/'action_plugins';actions.mkdir();templates=folder/'templates';templates.mkdir()
            (templates/'deployment-workflow-nodes.yml.j2').write_text((ROOT/'templates/deployment-workflow-nodes.yml.j2').read_text())
            state=folder/'state.json'
            seed={'workflow_id':7,'nodes':[{'identifier':name}for name in [
                'create_vm','configure_infrastructure','install_aap','configure_base','prepare_use_cases',
                'configure_aiops','configure_windows','configure_orchestrator','configure_assistant_team','configure_autodeploy']],
                'job_templates':{'legacy-four':'preserved','modern-four':'preserved','use-case-imports':'preserved'},'calls':[]}
            state.write_text(json.dumps(seed))
            plugin='''import json
from pathlib import Path
from ansible.plugins.action import ActionBase
STATE=Path(STATEPATH)
class ActionModule(ActionBase):
 def run(self,tmp=None,task_vars=None):
  args=self._task.args;state=json.loads(STATE.read_text())
  assert args['name']=='Deploy Complete AAP' and args['organization']=='Synthetic organization'
  state['calls'].append({'operation':'workflow_definition','replace_nodes':args.get('destroy_current_nodes',False)})
  if args.get('destroy_current_nodes',False):state['nodes']=[]
  existing={row['identifier']:row for row in state['nodes']}
  existing.update({row['identifier']:row for row in args['workflow_nodes']})
  state['nodes']=list(existing.values());STATE.write_text(json.dumps(state))
  return {'changed':True,'id':state['workflow_id']}
'''.replace('STATEPATH',repr(str(state)))
            (actions/'workflow_native.py').write_text(plugin)
            tasks=yaml.safe_load((ROOT/'tasks/deployment-workflow.yml').read_text())
            for task in tasks:
                if 'ansible.controller.workflow_job_template'in task:task['workflow_native']=task.pop('ansible.controller.workflow_job_template')
            definition={'name':'Deploy Complete AAP','organization':'Synthetic organization','workflow_nodes':self.graph()}
            variables={'controller_workflows_autodeploy':[definition]}
            if mode=='direct':variables={'cac_workflow':{'organization':'Synthetic organization'}}
            if mode=='conflicting-capture':definition['workflow_nodes'].append({'identifier':'prepare_use_cases'})
            play=folder/'fixture.yml';play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,
                'vars':variables,'tasks':tasks}],sort_keys=False))
            env=dict(os.environ,ANSIBLE_ACTION_PLUGINS=str(actions),ANSIBLE_LOCAL_TEMP=str(folder/'local'),
                     ANSIBLE_REMOTE_TEMP=str(folder/'remote'),ANSIBLE_NOCOLOR='1')
            result=subprocess.run([sys.executable,'-m','ansible.cli.playbook','-i','localhost,',str(play)],cwd=ROOT,
                                  env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode==0,mode!='conflicting-capture',result.stdout+result.stderr)
            after=json.loads(state.read_text());self.assertEqual(after['workflow_id'],seed['workflow_id'])
            self.assertEqual(after['job_templates'],seed['job_templates'])
            if mode=='conflicting-capture':self.assertEqual(after,seed)
            else:
                self.assertEqual(after['nodes'],self.graph());self.assertEqual(after['calls'],[{'operation':'workflow_definition','replace_nodes':True}])

    @unittest.skipUnless(importlib.util.find_spec("ansible"), "requires installed Ansible")
    def test_actual_vm_stats_handoff_replaces_stale_registry_selector_without_using_display_alias(self):
        with tempfile.TemporaryDirectory(prefix='base-workflow-handoff-') as directory:
            folder=Path(directory);actions=folder/'action_plugins';actions.mkdir();trace=folder/'requests.jsonl'
            plugin='''import json
from pathlib import Path
from ansible.plugins.action import ActionBase
TRACE=Path(TRACEPATH)
class ActionModule(ActionBase):
 def run(self,tmp=None,task_vars=None):
  args=self._task.args
  with TRACE.open('a')as stream:stream.write(json.dumps(args)+'\\n')
  assert args['instance_key']=='aap27-test-25'
  assert args['expected_route']==task_vars['fixture_route']
  return {'changed':False,'instance_route':task_vars['fixture_route'],'instance_resources':{}}
'''.replace('TRACEPATH',repr(str(trace)))
            (actions/'aap_read_instance.py').write_text(plugin)
            route={'vm_name':'aap27-test-25','vm_ip':'192.0.2.25','aap_hostname':'https://aap.example.invalid',
                   'hypervisor':{'machine_id':'b'*32}}
            producer=yaml.safe_load((ROOT/'01-linux-vm-setup.yml').read_text())[0]
            stats=next(task for task in producer['tasks']if task.get('name')=='Pass only the verified new instance handoff to downstream jobs')
            stats=dict(stats,register='fixture_stats')
            variables={'fixture_route':route,'aap_instance_route':route,'vm_name':route['vm_name'],'new_vm_ip':route['vm_ip'],
                       'fixture_saved_stage_defaults':{'aap_instance_key':'aap27-test-24'},
                       'fixture_native_inventory_alias':'aap27-v25'}
            play=folder/'fixture.yml';play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,'vars':variables,
                'tasks':[stats,{'ansible.builtin.set_fact':{'fixture_effective_launch':'{{ fixture_saved_stage_defaults | combine(fixture_stats.ansible_stats.data) }}'}},
                    {'ansible.builtin.set_fact':{'aap_instance_key':'{{ fixture_effective_launch.aap_instance_key }}'}},
                    {'ansible.builtin.include_tasks':str(ROOT/'tasks/aap-instance-select.yml')},
                    {'ansible.builtin.assert':{'that':['aap_instance_key == fixture_route.vm_name',
                      'aap_instance_key != fixture_native_inventory_alias','aap_instance_route == fixture_route']}}]}],sort_keys=False))
            env=dict(os.environ,ANSIBLE_ACTION_PLUGINS=str(actions),ANSIBLE_FILTER_PLUGINS=str(ROOT/'filter_plugins'),
                     ANSIBLE_LOCAL_TEMP=str(folder/'local'),ANSIBLE_REMOTE_TEMP=str(folder/'remote'),ANSIBLE_NOCOLOR='1')
            result=subprocess.run([sys.executable,'-m','ansible.cli.playbook','-i','localhost,',str(play)],cwd=ROOT,
                                  env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            requests=[json.loads(line)for line in trace.read_text().splitlines()]
            self.assertEqual(len(requests),1);self.assertEqual(requests[0]['instance_key'],'aap27-test-25')

    @unittest.skipUnless(importlib.util.find_spec("ansible"), "requires installed Ansible")
    def test_duplicate_collection_pins_are_synced_in_nonoverlapping_exact_batches(self):
        tasks = yaml.safe_load((ROOT / "tasks/use-case-pah-repository.yml").read_text())
        select = next(task for task in tasks if task.get("name") == "Separate additional exact versions of the same collection")
        entries = [{"name": "example.roles", "version": "1.2.3"},
                   {"name": "example.roles", "version": "2.4.0"},
                   {"name": "example.windows", "version": "3.1.0"}]
        with tempfile.TemporaryDirectory(prefix="workflow-batches-") as directory:
            root = Path(directory)
            (root / "ansible.cfg").write_text("[defaults]\nretry_files_enabled=False\n")
            tasks = [select, {"ansible.builtin.copy": {
                "dest": str(root / "batches.json"), "content": "{{ cac_required_sync_batches | to_json }}", "mode": "0600"}}]
            fixture = root / "play.yml"
            fixture.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local", "gather_facts": False,
                                               "vars": {"cac_required_repository": {"collections": entries}},
                                               "tasks": tasks}], sort_keys=False))
            environment = dict(os.environ, ANSIBLE_CONFIG=str(root / "ansible.cfg"),
                               ANSIBLE_LOCAL_TEMP=str(root / "local"), ANSIBLE_REMOTE_TEMP=str(root / "remote"))
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(fixture)],
                                    cwd=root, env=environment, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            batches = json.loads((root / "batches.json").read_text())
        self.assertEqual(len(batches), 2)
        self.assertCountEqual([item for batch in batches for item in batch], entries)
        for batch in batches:
            self.assertEqual(len({entry["name"] for entry in batch}), len(batch))


if __name__ == "__main__":
    unittest.main()
