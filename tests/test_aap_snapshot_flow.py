"""Run the real snapshot task ordering/delegation and API guards without a VM."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml
from test_aap_snapshots import fixture

ROOT = Path(__file__).resolve().parents[1]


class SnapshotFlowTests(unittest.TestCase):
    def test_actual_tasks_guard_power_and_verify_original_guest(self):
        for behavior in ('success', 'controller_busy', 'eda_busy', 'foreign_page', 'native_failure', 'guest_changed'):
            with self.subTest(behavior=behavior): self.run_flow(behavior)

    def run_flow(self, behavior):
        route, primary, _, policy, external = fixture()
        route.update(aap_hostname='https://aap.example.invalid', guest_host_keys=['ssh-ed25519 AAAA'])
        route['hypervisor'].update(address='192.0.2.20', public_ip='192.0.2.20', user='fixture', port=2222)
        with tempfile.TemporaryDirectory(prefix='aap-snapshot-flow-') as directory:
            folder = Path(directory); actions = folder/'action_plugins'; actions.mkdir()
            trace = folder/'trace.jsonl'; trust = folder/'trust'
            plugin = '''import json
from pathlib import Path
from ansible.plugins.action import ActionBase
TRACE=Path(TRACEPATH); TRUST=Path(TRUSTPATH)
class ActionModule(ActionBase):
 def run(self,tmp=None,task_vars=None):
  stage=self._task.args['stage']; behavior=task_vars['fixture_behavior']
  with TRACE.open('a')as f:f.write(json.dumps({'stage':stage})+'\\n')
  if stage=='registry':return dict(changed=False,instance_resources={'aap':task_vars['fixture_primary']},snapshot_external_state=task_vars['fixture_external'],snapshot_api_access={'token':'synthetic-token'})
  if stage=='trust':
   TRUST.write_text('synthetic trust')
   return dict(changed=False,ansible_facts={'aap_instance_trust':{'path':str(TRUST)},'aap_instance_ssh_args':'-o StrictHostKeyChecking=yes'})
  if stage in ['before','after','wait']:
   assert self._play_context.remote_addr==task_vars['aap_instance_route']['vm_ip']
   assert self._play_context.remote_user=='fixture'
   if stage=='after'and behavior=='guest_changed':return dict(changed=False,rc=0,stdout='c'*32)
   return dict(changed=False,rc=0,stdout='b'*32)
  if stage=='controller_idle':return dict(changed=False,status=200,json={'count':1 if behavior=='controller_busy'else 0})
  if stage=='eda_page':return dict(changed=False,status=200,json={'count':1,'results':[{'is_enabled':behavior=='eda_busy','current_job_id':None}], 'next':'https://foreign.example.invalid/api/eda/v1/activations/?page=2'if behavior=='foreign_page'else None})
  if stage=='native':
   assert self._play_context.remote_addr==task_vars['aap_instance_route']['hypervisor']['address']
   assert self._play_context.remote_user=='fixture'
   if behavior=='native_failure':return dict(changed=True,failed=True,msg='Synthetic native failure')
   return dict(changed=True,snapshot_name='aap-base-deployed-snapshot')
  if stage=='ping':return dict(changed=False,status=200,json={'version':'synthetic'})
  raise AssertionError(stage)
'''.replace('TRACEPATH',repr(str(trace))).replace('TRUSTPATH',repr(str(trust)))
            (actions/'snapshot_io.py').write_text(plugin)
            page = deepcopy(yaml.safe_load((ROOT/'tasks/aap-snapshot-eda-page.yml').read_text()))
            page[0].pop('ansible.builtin.uri'); page[0]['snapshot_io']={'stage':'eda_page'}
            (folder/'page.yml').write_text(yaml.safe_dump(page,sort_keys=False))
            tasks = deepcopy(yaml.safe_load((ROOT/'tasks/aap-cold-snapshot.yml').read_text()))
            tasks[0].pop('aap_read_instance'); tasks[0]['snapshot_io']={'stage':'registry'}
            tasks[2].pop('ansible.builtin.include_tasks'); tasks[2]['snapshot_io']={'stage':'trust'}
            tasks[-1]['always'][0]['when'] = True  # Only fixture-owned file; no real trust path is touched.
            for task in tasks[-1]['block']:
                name=task['name']
                if 'ansible.builtin.command' in task:
                    task.pop('ansible.builtin.command');task['snapshot_io']={'stage':'before'if 'before' in name else 'after'}
                elif 'ansible.builtin.uri' in task:
                    task.pop('ansible.builtin.uri');task['snapshot_io']={'stage':'controller_idle'if 'still has executing' in name else 'ping'}
                elif 'aap_vm_snapshot' in task:
                    task.pop('aap_vm_snapshot');task['snapshot_io']={'stage':'native'}
                elif 'ansible.builtin.wait_for_connection' in task:
                    task.pop('ansible.builtin.wait_for_connection');task['snapshot_io']={'stage':'wait'}
                elif task.get('ansible.builtin.include_tasks')=='aap-snapshot-eda-page.yml':
                    task['ansible.builtin.include_tasks']=str(folder/'page.yml')
                task['retries']=0 if 'until' in task else task.get('retries',None)
                if task.get('retries') is None:task.pop('retries',None)
            variables={'aap_instance_route':route,'fixture_primary':primary,'fixture_external':external,
                       'aap_snapshot_policy':policy,'aap_snapshot_checkpoint':'base','fixture_behavior':behavior,
                       'vault_ansible_user':'fixture','vault_ansible_password':'synthetic-fixture',
                       'aap_instance_ssh_args':'-o StrictHostKeyChecking=yes',
                       'hactar_source_public_ip':'192.0.2.99'}
            play=folder/'fixture.yml';play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,'vars':variables,
                'tasks':[{'name':'Publish fixture host-scoped routing as the actual registry action does','ansible.builtin.set_fact':{
                    'aap_instance_route':route,'aap_instance_ssh_args':'-o StrictHostKeyChecking=yes'}}, *tasks]}],sort_keys=False))
            environment=dict(os.environ,ANSIBLE_LOCAL_TEMP=str(folder/'local'),ANSIBLE_REMOTE_TEMP=str(folder/'remote'),
                             ANSIBLE_ACTION_PLUGINS=str(actions),ANSIBLE_FILTER_PLUGINS=str(ROOT/'filter_plugins'),ANSIBLE_NOCOLOR='1')
            result=subprocess.run([sys.executable,'-m','ansible.cli.playbook','-i','localhost,',str(play)],cwd=ROOT,
                                  env=environment,capture_output=True,text=True,timeout=40)
            stages=[json.loads(line)['stage']for line in trace.read_text().splitlines()]
            self.assertEqual(result.returncode==0,behavior=='success',result.stdout+result.stderr)
            self.assertFalse(trust.exists(),'The job-local trust file must always be removed.')
            if behavior in ('controller_busy','eda_busy','foreign_page'):self.assertNotIn('native',stages)
            if behavior=='success':
                self.assertEqual(stages,['registry','trust','before','controller_idle','eda_page','native','wait','after','ping'])
            if behavior=='guest_changed':self.assertNotIn('ping',stages)


if __name__=='__main__':unittest.main()
