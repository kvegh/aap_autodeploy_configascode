"""Run the installed EDA definition guard locally in the source EE.

Ansible's module payload does not package imports of other collection modules.
Use an isolated local interpreter with the resolved collection on its import
path. Protected module arguments travel through stdin, never command arguments
or a generated file. The target is contacted only by the native HTTPS client.
"""

import json
import os
from pathlib import Path
import subprocess
import sys

from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase
from ansible.plugins.loader import module_loader


class ActionModule(ActionBase):
    TRANSFERS_FILES = False
    _requires_connection = False

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        resolved = module_loader.find_plugin_with_context('ansible.eda.rulebook_activation')
        if not resolved.resolved:
            raise AnsibleActionFail('Install the declared ansible.eda collection in the source execution environment.')
        native_path = Path(resolved.plugin_resolved_path).resolve()
        collection_root = native_path.parents[5]
        expected = collection_root / 'ansible_collections/ansible/eda/plugins/modules/rulebook_activation.py'
        if native_path != expected:
            raise AnsibleActionFail('The installed EDA activation module has an unexpected location.')
        arguments = dict(self._task.args, _ansible_check_mode=self._task.check_mode,
                         _ansible_no_log=True)
        environment = dict(os.environ, PYTHONPATH=str(collection_root))
        helper = Path(__file__).resolve().parents[1] / 'library/aap_cac_activation.py'
        try:
            process = subprocess.run(
                [sys.executable, str(helper)],
                input=json.dumps({'ANSIBLE_MODULE_ARGS': arguments}),
                text=True, capture_output=True, env=environment, timeout=600,
            )
            response = json.loads(process.stdout)
            if not isinstance(response, dict) or (process.returncode and not response.get('failed')):
                raise ValueError('Invalid module result')
        except (OSError, ValueError, subprocess.TimeoutExpired):
            raise AnsibleActionFail('The local EDA definition guard failed; no alternate transport was attempted.') from None
        # Native invocation metadata may repeat connection inputs; keep only the result.
        response.pop('invocation', None)
        response.pop('exception', None)
        result.update(response)
        return result
