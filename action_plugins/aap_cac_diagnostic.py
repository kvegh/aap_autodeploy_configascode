"""Seal only the initial organization failure with its existing CaC Vault key."""

import json
from collections.abc import Mapping
from pathlib import Path

from ansible.errors import AnsibleActionFail
from ansible.parsing.vault import VaultLib
from ansible.plugins.action import ActionBase


RESULT_FIELDS = frozenset((
    'msg', 'detail', 'error', 'exception', 'stderr', 'module_stderr',
    'module_stdout', 'stdout', 'rc', 'results_file', 'ansible_job_id',
    'started', 'finished', 'failed', 'unreachable', 'censored', 'results',
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
            if self._task.args:
                raise ValueError()
            context = task_vars or {}
            # Select only the existing explicitly labelled CaC credential. Never
            # try an environment Vault key, even if that key could decrypt data.
            secrets = [secret for label, secret in self._loader._vault.secrets if label == 'cac']
            if len(secrets) != 1:
                raise ValueError()
            vault = VaultLib([('cac', secrets[0])])
            capture = Path(context['cac_workspace']['path']) / 'repository/cac/base_CaC_vault.yml'
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
                'stage': 'initial_base_organizations',
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
            raise AnsibleActionFail('The protected organization diagnostic could not be encrypted with the existing CaC Vault credential.') from None
