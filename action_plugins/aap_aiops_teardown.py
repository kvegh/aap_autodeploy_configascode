"""Use existing owner credentials for bounded selected AIOps API/namespace cleanup."""
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile

import yaml
from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase
from ansible.parsing.vault import VaultLib, VaultSecret

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helpers = load('aiops_teardown_action_helpers', ROOT / 'src/aap_aiops_teardown.py')
keys, codec = helpers.keys, helpers.codec
contract = load('aiops_teardown_action_contract', ROOT / 'filter_plugins/cac_import.py')
lifecycle = load('aiops_teardown_action_lifecycle', ROOT / 'src/cac_api_lifecycle.py')
CAPTURE = 'vaults/cac/aiops-selfhealing-demo-cac-vault.yml'
RUNTIME = 'vaults/runtime/aiops-selfhealing-demo-runtime-vault.yml'


class ActionModule(ActionBase):
    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        try:
            args, variables = self._task.args, task_vars or {}
            self._templar.available_variables = variables
            operation = args.get('operation')
            require = keys.require
            require(set(args) >= {'operation', 'instance_name', 'route'} and set(args) <= {
                'operation', 'instance_name', 'route', 'resources', 'plan', 'job_id'}
                and operation in ('runtime_dns', 'authentication', 'plan', 'plan_absent', 'quiesce', 'record_subscription_absence', 'subscription_result', 'remove_target', 'retire_profile'),
                'Select only the explicit AIOps workload lifecycle operation.')
            selected, route = args['instance_name'], keys._routing.instance_route(args['route'])
            require(selected == route['vm_name'], 'The workload selection and registered AAP route differ.')
            source = keys.SourceClient()
            keys.verify_source_job(source, route['aap_hostname'], variables)
            require(source.origin != keys.origin(route['aap_hostname']),
                    'Run workload teardown on Source AAP, preserving the selected AAP base.')
            token = os.environ.get('CAC_GIT_TOKEN', '')
            require(bool(token), 'Attach the existing central writer and Source API credentials.')
            central = contract.autodeploy_repository(self._loader, ROOT)
            with tempfile.TemporaryDirectory(prefix='aap-aiops-teardown-') as temporary:
                workspace = Path(temporary)

                def checkout(name, repository, credential):
                    path = workspace / name
                    path.mkdir(mode=0o700)
                    environment = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_ASKPASS='/bin/false', LC_ALL='C',
                        GIT_CONFIG_COUNT='4', GIT_CONFIG_KEY_0='credential.helper', GIT_CONFIG_VALUE_0='',
                        GIT_CONFIG_KEY_1='http.followRedirects', GIT_CONFIG_VALUE_1='false',
                        GIT_CONFIG_KEY_2='http.sslVerify', GIT_CONFIG_VALUE_2='true',
                        GIT_CONFIG_KEY_3='http.' + repository + '.extraheader',
                        GIT_CONFIG_VALUE_3='Authorization: Basic ' + base64.b64encode(('x-access-token:' + credential).encode()).decode())

                    def git(*arguments, optional=False):
                        process = subprocess.run(['git', '-C', str(path), *arguments], env=environment,
                            capture_output=True, text=True, timeout=60)
                        require(optional or process.returncode == 0,
                                'Protected workload Git operation failed; no alternate access or force push was attempted.')
                        return process
                    git('init', '--quiet')
                    git('remote', 'add', 'origin', repository)
                    git('fetch', '--quiet', '--depth=1', 'origin', 'main')
                    git('checkout', '--quiet', '--detach', 'FETCH_HEAD')
                    return path, git

                central_path, _ = checkout('central', central, token)
                configuration = codec.load_repository_yaml(self._loader._vault.decrypt(
                    (central_path / 'vaults/cac/aap_autodeploy_configascode-cac-vault.yml').read_bytes()))
                allocation = codec.load_repository_yaml(self._loader._vault.decrypt(
                    (central_path / 'state/aap_vm_allocations_vault.yml').read_bytes()))
                records = [row for row in allocation['aap_vm_allocation']['reservations'].values() if row.get('vm_name') == selected]
                require(len(records) == 1 and records[0].get('decommissioned', False) is False
                        and records[0].get('instance_route') == route,
                        'Keep the active consumed AAP reservation unchanged during workload cleanup.')
                authentication = keys.select_access(keys.document(configuration['aap_instance_api_credentials']), selected,
                    {'ansible_fqdn': route['aap_hostname'].removeprefix('https://')})
                require(keys.origin(authentication['hostname']) == keys.origin(route['aap_hostname']),
                        'Use only the registered target AAP origin.')
                client = lifecycle.Client(authentication['hostname'], authentication['token'])
                if operation == 'runtime_dns':
                    capture = variables['aap_isolation_app_capture']['ansible_facts']
                    runtime_vault = VaultLib([('default', VaultSecret(capture['aiops_playbook_vault_password'].encode()))])
                    runtime = codec.load_repository_yaml(runtime_vault.decrypt(capture['aiops_runtime_settings_vault'].encode()))
                    result.update(changed=False, tokens=helpers.selected_dns_tokens(capture, runtime, selected))
                    return result
                if operation == 'authentication':
                    client.request('GET', '/api/gateway/v1/me/')
                    result.update(changed=False, authentication=authentication)
                    return result
                if operation == 'plan_absent':
                    raw = variables['aap_isolation_app_capture']['ansible_facts']
                    require(selected not in raw['aiops_instances'], 'Selected ownership still exists; use the normal full plan.')
                    names = contract.resources_for_import(raw['cac_import_metadata'], raw)
                    empty_plan = {'operations': [], 'selected_ids': {kind: [] for kind, _ in helpers.TARGET_KINDS},
                                  'required_label': 'aiops_selfhealing', 'profile_absent': True,
                                  'instance_name': selected, 'origin': keys.origin(route['aap_hostname'])}
                    for kind, endpoint in helpers.TARGET_KINDS:
                        for definition in names.get(kind, []):
                            name = self._templar.template(definition['name'])
                            require(not client.rows(endpoint + '?name=' + keys.quote(name) + '&page_size=200'),
                                    'AIOps definitions survive without their owner profile; preserve them for review.')
                    result.update(changed=False, plan=empty_plan)
                    return result
                if operation == 'plan':
                    resources = args.get('resources')
                    plan = helpers.selected_target_plan(client, resources, 'aiops_selfhealing')
                    native_access = client.request('GET', '/api/gateway/v1/tokens/%d/' %
                        configuration['aap_instance_api_credentials'][selected]['token_id'])
                    protected_application = native_access.get('application')
                    protected_application = protected_application.get('id') if isinstance(protected_application, dict) else protected_application
                    require(protected_application not in plan['selected_ids']['aap_applications'],
                            'The AIOps application is shared by base AAP API access; preserve it for review.')
                    plan.update(instance_name=selected, origin=keys.origin(route['aap_hostname']))
                    profile = variables['aap_isolation_app_capture']['ansible_facts']['aiops_instances'].get(selected)
                    plan['subscription_absence_verified'] = bool(helpers.subscription_absence_valid(profile, selected))
                    result.update(changed=False, plan=plan, authentication=authentication)
                    return result
                plan = args.get('plan')
                require(isinstance(plan, dict) and plan.get('instance_name') == selected
                        and plan.get('origin') == keys.origin(route['aap_hostname']),
                        'Use this job\'s exact native AIOps ownership plan.')
                if operation == 'quiesce':
                    permitted = (not self._task.check_mode and variables.get('aap_aiops_teardown_apply') is True
                                 and variables.get('aap_aiops_teardown_confirmation') == selected)
                    result.update(helpers.quiesce_target(client, plan, apply=permitted))
                    return result
                require(not self._task.check_mode, 'Apply teardown only through a normal confirmed job.')
                require(variables.get('aap_aiops_teardown_apply') is True
                        and variables.get('aap_aiops_teardown_confirmation') == selected,
                        'Explicitly confirm only the selected workload before removal.')
                if operation == 'subscription_result':
                    identity = args.get('job_id')
                    require(isinstance(identity, int) and not isinstance(identity, bool) and identity > 0, 'Verify the actual launched native target job ID.')
                    candidates = [item for item in plan['operations'] if item['kind'] == 'controller_templates'
                                  and item['identity']['name'] == 'Retire AIOps TRA Subscription']
                    require(len(candidates) == 1, 'The target-local subscription retirement template must be normally imported first.')
                    expected_template = candidates[0]['identity']
                    job = client.request('GET', '/api/controller/v2/jobs/%d/' % identity)
                    project = client.request('GET', '/api/controller/v2/projects/%d/' % expected_template['project'])
                    selected_profile = variables['aap_isolation_app_capture']['ansible_facts']['aiops_instances'][selected]
                    normalized = helpers.verified_subscription_artifact(job, expected_template, project,
                        selected_profile, selected, identity, variables['awx_job_id'], variables['awx_project_revision'])
                    result.update(changed=False, verified=True, proof=normalized)
                    return result
                if operation == 'remove_target':
                    result.update(changed=helpers.remove_target(client, plan), target_removed=True)
                    return result
                # Profile/runtime namespaces are the final state change. Keep all
                # ownership while native resources or target definitions remain.
                recording_subscription = operation == 'record_subscription_absence'
                require(recording_subscription or (variables.get('aap_aiops_teardown_native_absence_verified') is True
                        and variables.get('aap_aiops_teardown_source_published', {}).get('published') is True),
                        'Retain owner namespaces until native absence and Source publication are verified.')
                for item in ([] if recording_subscription else plan['operations']):
                    require(not client.rows(item['endpoint'] + '?name=' + keys.quote(item['identity']['name']) + '&page_size=200'),
                            'Selected target AIOps definitions remain; retain their runtime ownership.')
                bootstrap = codec.load_repository_yaml(self._loader._vault.decrypt((central_path / 'cac/base_CaC_vault.yml').read_bytes()))
                repository = bootstrap['cac_bootstrap_git_credentials']['aiops']['repository_url']
                credential = bootstrap['cac_bootstrap_git_credentials']['aiops']['token']
                require(repository == central.rsplit('/', 1)[0] + '/aiops-selfhealing-demo-secrets.git'
                        and isinstance(credential, str) and credential and '\n' not in credential and '\r' not in credential,
                        'Reuse only the fixed AIOps owner repository and its approved existing writer.')
                native_vault = VaultLib([('default', VaultSecret(bootstrap['cac_bootstrap_vault_credentials']['aiops']['vault_password'].encode()))])
                path, git = checkout('aiops', repository, credential)
                expected = variables['aap_isolation_app_capture']['ansible_facts']['aiops_instances'].get(selected)
                for attempt in range(8):
                    git('fetch', '--quiet', '--depth=1', 'origin', 'main')
                    git('checkout', '--quiet', '--detach', 'FETCH_HEAD')
                    raw_capture, raw_runtime = (path / CAPTURE).read_bytes(), (path / RUNTIME).read_bytes()
                    capture = codec.load_repository_yaml(native_vault.decrypt(raw_capture))
                    runtime_vault = VaultLib([('default', VaultSecret(capture['aiops_playbook_vault_password'].encode()))])
                    require(capture['aiops_runtime_settings_vault'].encode() == raw_runtime,
                            'Standalone and embedded AIOps runtime ciphertext must agree.')
                    runtime = codec.load_repository_yaml(runtime_vault.decrypt(raw_runtime))
                    if recording_subscription:
                        require(helpers.quiesce_target(client, plan)['quiescent'],
                                'Stop selected delivery and wait for jobs before subscription teardown.')
                        desired = helpers.record_subscription_absence(capture, selected,
                            variables['aap_aiops_teardown_subscription_proof'], variables.get('awx_job_id'),
                            variables.get('awx_project_revision'))
                        next_runtime = runtime
                    else:
                        if selected not in capture['aiops_instances']:
                            require(selected not in runtime['instances'],
                                    'A selected runtime remains after owner retirement; preserve it for review.')
                            for item in plan['operations']:
                                require(not client.rows(item['endpoint'] + '?name=' + keys.quote(item['identity']['name']) + '&page_size=200'),
                                        'Selected target definitions reappeared; retain remaining ownership for review.')
                            result.update(changed=False, retired=True)
                            return result
                        require(capture['aiops_instances'].get(selected) is None or
                                helpers.subscription_absence_valid(capture['aiops_instances'][selected], selected),
                                'Retain the TRA owner until its external subscription absence is verified.')
                        # This job may have added only its exact subscription proof
                        # since the initial protected read. No other owner drift is accepted.
                        candidate = deepcopy(capture['aiops_instances'].get(selected))
                        prior = deepcopy(expected)
                        if isinstance(candidate, dict) and isinstance(prior, dict):
                            candidate.pop('teardown', None)
                            prior.pop('teardown', None)
                        require(candidate == prior, 'Selected AIOps ownership changed during teardown.')
                        desired, next_runtime = helpers.documents_without_instance(capture, runtime, selected,
                            capture['aiops_instances'].get(selected))
                    if desired == capture and next_runtime == runtime:
                        result.update(changed=False, retired=not recording_subscription, subscription_absence_verified=recording_subscription)
                        return result

                    def seal(value, original, vault):
                        header = original.splitlines()[0].decode().split(';')
                        encoded = vault.encrypt(yaml.dump(value, Dumper=codec.VaultDumper, sort_keys=False, width=110),
                            vault_id=header[3] if len(header) == 4 else None)
                        restored = codec.load_repository_yaml(vault.decrypt(encoded))
                        require(encoded.splitlines()[0] == original.splitlines()[0] and restored == value
                                and codec.literal_paths(restored) == codec.literal_paths(value),
                                'AIOps retirement must retain original Vault headers, literal values and unrelated state.')
                        return encoded
                    encoded_runtime = raw_runtime if next_runtime == runtime else seal(next_runtime, raw_runtime, runtime_vault)
                    desired['aiops_runtime_settings_vault'] = encoded_runtime.decode()
                    (path / RUNTIME).write_bytes(encoded_runtime)
                    (path / CAPTURE).write_bytes(seal(desired, raw_capture, native_vault))
                    git('add', '--', CAPTURE, RUNTIME)
                    git('-c', 'user.name=AAP AutoDeploy', '-c', 'user.email=automation@example.invalid',
                        'commit', '--quiet', '-m', 'Retire verified selected AIOps workload namespaces')
                    # Always reread remote state after the acknowledgement,
                    # including uncertainty. Never force or recreate namespaces.
                    if not recording_subscription:
                        for item in plan['operations']:
                            require(not client.rows(item['endpoint'] + '?name=' + keys.quote(item['identity']['name']) + '&page_size=200'),
                                    'Selected target definitions reappeared before owner publication; preserve ownership.')
                    git('push', 'origin', 'HEAD:refs/heads/main', optional=True)
                raise keys.StoreError('Concurrent AIOps owner updates prevented verified retirement; retry from preserved ownership.')
        except (keys.StoreError, lifecycle.LifecycleError, AnsibleActionFail) as error:
            raise AnsibleActionFail(str(error)) from None
        except Exception:
            raise AnsibleActionFail('Protected AIOps workload cleanup did not complete; retain owner records and inspect its native checks.') from None
