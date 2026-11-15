"""Seal bounded configuration failures with their existing labelled CaC key."""

import json
import re
from collections.abc import Mapping
from pathlib import Path

from ansible.errors import AnsibleActionFail
from ansible.parsing.vault import VaultLib
from ansible.plugins.action import ActionBase


RESULT_FIELDS = frozenset((
    'msg', 'detail', 'error', 'exception', 'stderr', 'module_stderr',
    'module_stdout', 'stdout', 'rc', 'results_file', 'ansible_job_id',
    'started', 'finished', 'failed', 'unreachable', 'censored', 'results',
    'id', 'job', 'status', 'failed_when_suppressed_exception',
))
LAUNCH_FIELDS = frozenset(('ansible_job_id', 'results_file', 'started', 'finished', 'failed'))
EXCLUDED_FIELDS = frozenset(('invocation', 'module_args', 'module_arguments'))


def scrub(value, depth=0):
    """Bound diagnostic size and omit invocation arguments at every depth."""
    if depth > 12:
        return '[depth limit]'
    if isinstance(value, Mapping):
        if len(value) > 128:
            raise ValueError()
        return {str(key): scrub(item, depth + 1) for key, item in value.items()
                if key not in EXCLUDED_FIELDS}
    if isinstance(value, (list, tuple)):
        if len(value) > 64:
            raise ValueError()
        return [scrub(item, depth + 1) for item in value]
    if isinstance(value, str):
        # A module error may include a complete JSON result as stdout. Preserve
        # its error but still remove nested invocation/module_args objects.
        if value.lstrip().startswith(('{', '[')):
            try:
                parsed = json.loads(value)
            except (ValueError, TypeError):
                pass
            else:
                return json.dumps(scrub(parsed, depth + 1), sort_keys=True)
        return value[:16384]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:16384]


def failure_result(value):
    if not isinstance(value, Mapping):
        return {}
    selected = {key: item for key, item in value.items() if key in RESULT_FIELDS}
    if 'results' in selected:
        if not isinstance(selected['results'], list) or len(selected['results']) > 16:
            raise ValueError()
        selected['results'] = [failure_result(item) for item in selected['results']]
    return scrub(selected)


def launches(value):
    rows = value.get('results', []) if isinstance(value, Mapping) else []
    if not isinstance(rows, list) or len(rows) > 16:
        raise ValueError()
    return [scrub({key: item[key] for key in LAUNCH_FIELDS if key in item})
            for item in rows if isinstance(item, Mapping)]


class ActionModule(ActionBase):
    TRANSFERS_FILES = False
    _requires_connection = False

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        try:
            if set(self._task.args) - {'stage'}:
                raise ValueError()
            stage = self._task.args.get('stage', 'initial_base_organizations')
            if stage not in ('initial_base_organizations', 'selected_configuration_job',
                             'project_configuration_import'):
                raise ValueError()
            context = task_vars or {}
            # Select only the existing explicitly labelled CaC credential. Never
            # try an environment Vault key, even if that key could decrypt data.
            secrets = [secret for label, secret in self._loader._vault.secrets if label == 'cac']
            if len(secrets) != 1:
                raise ValueError()
            vault = VaultLib([('cac', secrets[0])])
            repository = Path(context['cac_workspace']['path']) / 'repository'
            relative = 'cac/base_CaC_vault.yml'
            if stage == 'project_configuration_import':
                contract = context.get('cac_project_contract', {})
                project = contract.get('project_id') if isinstance(contract, Mapping) else None
                if not isinstance(project, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', project):
                    raise ValueError()
                relative = 'vaults/cac/' + project + '-cac-vault.yml'
                if contract.get('configuration_file') != relative:
                    raise ValueError()
            capture = repository / relative
            if capture.is_symlink() or not capture.resolve().is_relative_to(repository.resolve()):
                raise ValueError()
            _, label, secret = vault.decrypt_and_get_vault_id(capture.read_bytes())
            if label != 'cac':
                raise ValueError()
            observed = failure_result(context.get('__cas_job_async_result', {}))
            original = failure_result(context.get('ansible_failed_result', {}))
            if not observed and not original:
                raise ValueError()
            failed_task = context.get('ansible_failed_task')
            task_name = getattr(failed_task, 'name', None)
            payload = {
                'stage': stage,
                'failed_task': scrub(task_name),
                'async_status': observed,
                # The role's always cleanup can fail after the original poll.
                # Keep both results so that cleanup cannot hide the first error.
                'original_failure': original,
                'controller_launches': launches(context.get('__organizations_job_async', {})),
                'gateway_launches': launches(context.get('__gateway_organizations_job_async', {})),
                'async_context': {key: scrub(context.get(key)) for key in (
                    'ansible_async_dir', 'aap_configuration_async_dir',
                    'ansible_playbook_python', 'ansible_python_interpreter')},
                'discovered_interpreter_python': scrub(context.get('ansible_facts', {}).get('discovered_interpreter_python')),
            }
            if stage == 'selected_configuration_job':
                launch = context.get('aap_selected_import_job', {})
                job_id = launch.get('id') if isinstance(launch, Mapping) else None
                payload['configuration_job'] = {
                    'id': job_id if isinstance(job_id, int) and not isinstance(job_id, bool) and job_id > 0 else None,
                    'selection': scrub(context.get('aap_selected_importer_key')),
                }
                payload['launch'] = failure_result(launch)
                payload['observation'] = failure_result(context.get('aap_selected_import_wait', {}))
            plaintext = json.dumps(payload, sort_keys=True).encode()
            if len(plaintext) > 131072:
                raise ValueError()
            sealed = vault.encrypt(plaintext, secret=secret, vault_id='cac')
            if vault.decrypt(sealed) != plaintext:
                raise ValueError()
            result.update(changed=False, encrypted_diagnostic=sealed.decode())
            return result
        except Exception:
            # Exception messages and module results can contain credentials.
            raise AnsibleActionFail('The protected configuration diagnostic could not be encrypted with the existing CaC Vault credential.') from None
