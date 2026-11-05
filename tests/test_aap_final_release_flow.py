"""Exercise normal04 completion, cleanup and typed final-hook boundaries natively."""
from copy import deepcopy
import json,os
from pathlib import Path
import subprocess,sys,tempfile,unittest
import yaml
from test_aap_final_release import fixture

ROOT=Path(__file__).resolve().parents[1]


class FinalReleaseFlowTests(unittest.TestCase):
    def test_actual_final_hook_runs_only_after_complete_base_publication_and_cleanup(self):
        for native in (False,True):
            for behavior in ('success','base','mcp','source-publication','revoke','workspace','release','unpublished','skip'):
                with self.subTest(native=native,behavior=behavior):self.run_flow(native,behavior)

    def run_flow(self,native,behavior):
        guest,pin,*_=fixture()
        with tempfile.TemporaryDirectory(prefix='aap-final-flow-')as directory:
            root=Path(directory);plugins=root/'action_plugins';plugins.mkdir()
            trace=root/'trace.jsonl';workspace=root/'workspace';workspace.mkdir()
            descriptor,old_path=tempfile.mkstemp(prefix='aap-instance-known-hosts-');os.close(descriptor)
            old=Path(old_path);old.write_text('synthetic public keys only')
            source='''import json
from pathlib import Path
from ansible.plugins.action import ActionBase
from ansible.template import Templar
TRACE=Path(TRACEPATH)
class ActionModule(ActionBase):
 def run(self,tmp=None,task_vars=None):
  stage=self._task.args['stage'];row={'stage':stage}
  if stage=='identity':
   original=task_vars['hostvars'][task_vars['inventory_hostname']];route=original['aap_instance_route']
   assert self._play_context.remote_addr==route['vm_ip']
   assert self._play_context.remote_user=='fixture'
   assert self._play_context.port==22
   args=self._connection.get_option('ssh_common_args')
   assert 'StrictHostKeyChecking=yes' in args and 'ProxyCommand=' in args
   assert self._task.args['argv']==['cat','/etc/machine-id']
   row['trust']=original['aap_instance_trust']['path'];assert Path(row['trust']).is_file()
  if stage=='release':
   templar=Templar(loader=self._loader,variables=task_vars)
   actual=templar.template(task_vars['recovery_release_guest']);assert set(actual)=={'kind','route','primary','guest_machine_id'}
   assert actual['kind']=='aap' and actual['guest_machine_id']=='a'*32
   assert task_vars['recovery_release_operation']=='release_guest'
   row['trust']=templar.template(task_vars['recovery_release_trust_file']);assert Path(row['trust']).is_file()
   assert not Path(task_vars['fixture_workspace']).exists()
  with TRACE.open('a')as stream:stream.write(json.dumps(row)+'\\n')
  failed=task_vars['fixture_behavior']==stage
  if failed:return {'failed':True,'msg':'Synthetic stage failure'}
  return {'changed':False,'rc':0,'stdout':'a'*32,'published':stage=='source-publication' and task_vars['fixture_behavior']!='unpublished'}
'''.replace('TRACEPATH',repr(str(trace)))
            (plugins/'final_flow_proof.py').write_text(source)
            helper=deepcopy(yaml.safe_load((ROOT/'tasks/aap-final-release.yml').read_text()))
            for task in helper:
                task['no_log']=False  # Synthetic fixture only; real tasks remain protected.
                if task.get('ansible.builtin.include_tasks')=='aap-instance-ssh.yml':task['ansible.builtin.include_tasks']=str(ROOT/'tasks/aap-instance-ssh.yml')
                if 'ansible.builtin.command'in task:
                    task['final_flow_proof']=dict(task.pop('ansible.builtin.command'),stage='identity')
                if 'ansible.builtin.include_role'in task:
                    task.pop('ansible.builtin.include_role');task['final_flow_proof']={'stage':'release'}
            helper_path=root/'final.yml';helper_path.write_text(yaml.safe_dump(helper,sort_keys=False))
            actual=yaml.safe_load((ROOT/'04-aap-config.yml').read_text())[0]
            post=deepcopy(actual['post_tasks'])
            post[0]['block'][0]['ansible.builtin.include_tasks']=str(helper_path)
            cleanup=deepcopy(actual['pre_tasks'][-1]['always'])
            def replace(items):
                for task in items:
                    task['no_log']=False
                    if 'ansible.builtin.uri'in task:
                        task.pop('ansible.builtin.uri');task['final_flow_proof']={'stage':'revoke'}
                    if task.get('name')=='Remove the temporary checkout, decrypted manifest, and authentication helper':
                        if behavior=='workspace':
                            task.pop('ansible.builtin.file');task['final_flow_proof']={'stage':'workspace'}
                    for key in ('block','always','rescue'):
                        if key in task:replace(task[key])
            replace(cleanup)
            variables={'fixture_behavior':behavior,'fixture_workspace':str(workspace),'cac_workspace':{'path':str(workspace)},
                'cac_gateway_token':{'json':{'id':1}},'aap_instance_trust':{'path':str(old)},'aap_instance_route':guest['route'],
                'aap_instance_resources':{'aap':guest['primary']},'aap_instance_key_store':{'publish':True,'register_inventory':True},
                'vault_ansible_user':'fixture','vault_ansible_password':'synthetic-only'}
            play=root/'play.yml';play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,
                'vars':variables,'pre_tasks':[{'name':'Retain selector facts on the original host like normal04',
                    'ansible.builtin.set_fact':{'aap_instance_route':guest['route'],'aap_instance_resources':{'aap':guest['primary']}}},
                    {'name':'Simulate normal stages while retaining actual always cleanup',
                    'block':[{'name':'Configured base','final_flow_proof':{'stage':'base'}},
                             {'name':'Verified MCP','final_flow_proof':{'stage':'mcp'}},
                             {'name':'Published source','final_flow_proof':{'stage':'source-publication'},'register':'cac_instance_key_publication'}],
                    'always':cleanup}],'post_tasks':post}],sort_keys=False))
            env=dict(os.environ,ANSIBLE_HOME=str(root/'home'),ANSIBLE_LOCAL_TEMP=str(root/'local'),ANSIBLE_REMOTE_TEMP=str(root/'remote'),
                ANSIBLE_ACTION_PLUGINS=str(plugins),ANSIBLE_FILTER_PLUGINS=str(ROOT/'filter_plugins'),ANSIBLE_JINJA2_NATIVE=str(native).lower(),ANSIBLE_NOCOLOR='1')
            args=[sys.executable,'-m','ansible.cli.playbook','-i','localhost,',str(play)]
            if behavior=='skip':args+=['--skip-tags','synthetic-partial-choice']
            try:
                result=subprocess.run(args,cwd=ROOT,env=env,text=True,capture_output=True,timeout=45)
                self.assertEqual(result.returncode==0,behavior=='success',result.stdout+result.stderr)
                rows=[json.loads(line)for line in trace.read_text().splitlines()]
                stages=[row['stage']for row in rows]
                self.assertFalse(old.exists(),result.stdout+result.stderr)
                release=behavior in ('success','release')
                self.assertEqual('release'in stages,release,result.stdout+result.stderr)
                self.assertEqual('identity'in stages,release,result.stdout+result.stderr)
                if release:
                    self.assertLess(stages.index('source-publication'),stages.index('revoke'))
                    self.assertLess(stages.index('revoke'),stages.index('identity'))
                    self.assertLess(stages.index('identity'),stages.index('release'))
                for row in rows:
                    if 'trust'in row:self.assertFalse(Path(row['trust']).exists(),result.stdout+result.stderr)
            finally:old.unlink(missing_ok=True)


if __name__=='__main__':unittest.main()
