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

    def test_installer_privilege_context_cannot_change_snapshot_ownership(self):
        self.run_flow('success', installer_context=True)

    def test_filtered_count_mismatch_does_not_hide_complete_idle_history(self):
        self.run_flow('filtered_count_mismatch')

    def test_incomplete_active_late_page_and_changing_history_never_reach_power(self):
        for behavior in ('controller_incomplete', 'controller_late_active', 'controller_changed_confirmation'):
            with self.subTest(behavior=behavior): self.run_flow(behavior)

    def run_flow(self, behavior, installer_context=False):
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
  with TRACE.open('a')as f:f.write(json.dumps({'stage':stage,'become':self._play_context.become,'become_user':self._play_context.become_user})+'\\n')
  if task_vars['fixture_installer_context'] and stage in ['before','after','wait','native']:
   assert self._play_context.become is True
   assert self._play_context.become_user=='root', 'Snapshot operations must not inherit the installer account.'
  if stage in ['registry','trust','controller_page','eda_page','ping']:
   assert self._play_context.become is False, 'Controller-side work must keep privilege escalation disabled.'
  if stage=='registry':return dict(changed=False,instance_resources={'aap':task_vars['fixture_primary']},snapshot_external_state=task_vars['fixture_external'],snapshot_api_access={'token':'synthetic-token'})
  if stage=='trust':
   TRUST.write_text('synthetic trust')
   return dict(changed=False,ansible_facts={'aap_instance_trust':{'path':str(TRUST)},'aap_instance_ssh_args':'-o StrictHostKeyChecking=yes'})
  if stage in ['before','after','wait']:
   assert self._play_context.remote_addr==task_vars['aap_instance_route']['vm_ip']
   assert self._play_context.remote_user=='fixture'
   if stage=='after'and behavior=='guest_changed':return dict(changed=False,rc=0,stdout='c'*32)
   return dict(changed=False,rc=0,stdout='b'*32)
  if stage=='controller_pause':return dict(changed=False)
  if stage=='controller_page':
   from urllib.parse import urlsplit,parse_qs
   parsed=urlsplit(self._task.args['url']); query=parse_qs(parsed.query)
   assert parsed.scheme=='https' and parsed.netloc=='aap.example.invalid'
   assert parsed.path=='/api/controller/v2/unified_jobs/' and 'status__in' not in query
   assert query['order_by']==['id'] and query['page_size']==['100']
   if behavior=='controller_incomplete':return dict(changed=False,status=200,json={'count':1,'next':None,'results':[]})
   if behavior=='controller_late_active':
    if query.get('page')==['2']:return dict(changed=False,status=200,json={'count':101,'next':None,'results':[{'id':101,'status':'running'}]})
    return dict(changed=False,status=200,json={'count':101,'next':'/api/controller/v2/unified_jobs/?order_by=id&page_size=100&page=2','results':[{'id':i,'status':'successful'}for i in range(1,101)]})
   reads=sum(json.loads(line)['stage']=='controller_page'for line in TRACE.read_text().splitlines())
   number=2 if behavior=='controller_changed_confirmation'and reads>1 else 1
   return dict(changed=False,status=200,json={'count':1,'next':None,'results':[{'id':number,'status':'running'if behavior=='controller_busy'else 'successful'}]})
  if stage=='eda_page':return dict(changed=False,status=200,json={'count':1,'results':[{'is_enabled':behavior=='eda_busy','current_job_id':None}], 'next':'https://foreign.example.invalid/api/eda/v1/activations/?page=2'if behavior=='foreign_page'else None})
  if stage=='native':
   assert self._play_context.remote_addr==task_vars['aap_instance_route']['hypervisor']['address']
   assert self._play_context.remote_user=='fixture'
   if behavior=='native_failure':return dict(changed=True,failed=True,msg='Synthetic native failure')
   return dict(changed=True,snapshot_name=task_vars['aap_snapshot_policy']['names'][task_vars['aap_snapshot_checkpoint']])
  if stage=='ping':return dict(changed=False,status=200,json={'version':'synthetic'})
  raise AssertionError(stage)
'''.replace('TRACEPATH',repr(str(trace))).replace('TRUSTPATH',repr(str(trust)))
            (actions/'snapshot_io.py').write_text(plugin)
            page = deepcopy(yaml.safe_load((ROOT/'tasks/aap-snapshot-eda-page.yml').read_text()))
            page[0].pop('ansible.builtin.uri'); page[0]['snapshot_io']={'stage':'eda_page'}
            (folder/'page.yml').write_text(yaml.safe_dump(page,sort_keys=False))
            controller_files=('aap-snapshot-controller-idle.yml','aap-snapshot-controller-round.yml','aap-snapshot-controller-page.yml')
            def fixture_controller_tasks(tasks):
                for task in tasks:
                    if task.get('ansible.builtin.include_tasks') in controller_files:
                        task['ansible.builtin.include_tasks']=str(folder/task['ansible.builtin.include_tasks'])
                    if 'ansible.builtin.uri'in task:
                        uri=task.pop('ansible.builtin.uri');task['snapshot_io']={'stage':'controller_page','url':uri['url']}
                    if 'ansible.builtin.pause'in task:
                        task.pop('ansible.builtin.pause');task['snapshot_io']={'stage':'controller_pause'}
                    for field in ('block','rescue','always'):
                        if field in task:fixture_controller_tasks(task[field])
            for filename in controller_files:
                controller=deepcopy(yaml.safe_load((ROOT/'tasks'/filename).read_text()))
                fixture_controller_tasks(controller)
                if filename=='aap-snapshot-controller-idle.yml':
                    # Shorten only the fixture's retry budget; production guards,
                    # full-page validation and confirmation logic run unchanged.
                    controller[1]['loop']='{{ range(0, 2) | list }}'
                (folder/filename).write_text(yaml.safe_dump(controller,sort_keys=False))
            tasks = deepcopy(yaml.safe_load((ROOT/'tasks/aap-cold-snapshot.yml').read_text()))
            tasks[0].pop('aap_read_instance'); tasks[0]['snapshot_io']={'stage':'registry'}
            tasks[2].update(tasks[2]['ansible.builtin.include_tasks']['apply'])
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
                elif task.get('ansible.builtin.include_tasks')=='aap-snapshot-controller-idle.yml':
                    task['ansible.builtin.include_tasks']=str(folder/'aap-snapshot-controller-idle.yml')
                task['retries']=0 if 'until' in task else task.get('retries',None)
                if task.get('retries') is None:task.pop('retries',None)
            variables={'aap_instance_route':route,'fixture_primary':primary,'fixture_external':external,
                       'aap_snapshot_policy':policy,'aap_snapshot_checkpoint':'installed' if installer_context else 'base','fixture_behavior':behavior,
                       'fixture_installer_context':installer_context,'vault_aap_install_user':'fixture-installer',
                       'vault_ansible_user':'fixture','vault_ansible_password':'synthetic-fixture',
                       'aap_instance_ssh_args':'-o StrictHostKeyChecking=yes',
                       'hactar_source_public_ip':'192.0.2.99'}
            definition={'hosts':'localhost','connection':'local','gather_facts':False,'vars':variables,
                'tasks':[{'name':'Publish fixture host-scoped routing as the actual registry action does','ansible.builtin.set_fact':{
                    'aap_instance_route':route,'aap_instance_ssh_args':'-o StrictHostKeyChecking=yes'}}, *tasks]}
            if installer_context:
                caller=yaml.safe_load((ROOT/'03-aap-install.yml').read_text())[-1]
                self.assertEqual(caller['name'], 'Configure and install AAP')
                definition.update({key:caller[key] for key in ('become','become_user')})
            play=folder/'fixture.yml';play.write_text(yaml.safe_dump([definition],sort_keys=False))
            environment=dict(os.environ,ANSIBLE_LOCAL_TEMP=str(folder/'local'),ANSIBLE_REMOTE_TEMP=str(folder/'remote'),
                             ANSIBLE_ACTION_PLUGINS=str(actions),ANSIBLE_FILTER_PLUGINS=str(ROOT/'filter_plugins'),ANSIBLE_NOCOLOR='1')
            result=subprocess.run([sys.executable,'-m','ansible.cli.playbook','-i','localhost,',str(play)],cwd=ROOT,
                                  env=environment,capture_output=True,text=True,timeout=40)
            stages=[json.loads(line)['stage']for line in trace.read_text().splitlines()]
            self.assertEqual(result.returncode==0,behavior in ('success','filtered_count_mismatch'),result.stdout+result.stderr)
            self.assertFalse(trust.exists(),'The job-local trust file must always be removed.')
            if behavior in ('controller_busy','eda_busy','foreign_page','controller_incomplete','controller_late_active','controller_changed_confirmation'):
                self.assertNotIn('native',stages)
            if behavior in ('success','filtered_count_mismatch'):
                self.assertEqual(stages,['registry','trust','before','controller_page','controller_page','eda_page','native','wait','after','ping'])
            if behavior=='guest_changed':self.assertNotIn('ping',stages)


if __name__=='__main__':unittest.main()
