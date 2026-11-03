"""Inspect decrypted metadata without evaluating templates or exposing secrets."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from ansible.errors import AnsibleActionFail
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.plugins.action import ActionBase

SPEC = spec_from_file_location('cac_import_schema', Path(__file__).resolve().parents[1]
                              / 'filter_plugins/cac_import.py')
schema = module_from_spec(SPEC)
SPEC.loader.exec_module(schema)


class ActionModule(ActionBase):
    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        filename = Path(self._task.args['file'])
        root = Path(self._task.args['repository']).resolve()
        if filename.is_symlink() or not filename.resolve().is_relative_to(root):
            raise AnsibleActionFail('The capture must be a regular file within its private checkout.')
        encrypted = filename.read_bytes()
        if not encrypted.startswith((b'$ANSIBLE_VAULT;1.1;AES256', b'$ANSIBLE_VAULT;1.2;AES256')):
            raise AnsibleActionFail('The project capture must be fully Vault encrypted.')
        try:
            data = AnsibleLoader(self._loader._vault.decrypt(encrypted)).get_single_data()
            schema.require(isinstance(data, dict), 'The project capture must contain a mapping.')
            schema.import_metadata(data.get('cac_import_metadata'), self._task.args['project_id'])
            schema.validate_capture_roots(data)
        except Exception:
            # Exceptions can carry YAML source lines, including secrets. Never echo them.
            raise AnsibleActionFail('The encrypted capture failed its project/schema safety checks.') from None
        result.update(changed=False)
        return result
