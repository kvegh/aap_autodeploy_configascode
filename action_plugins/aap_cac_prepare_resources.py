"""Render only declared configuration resources without passing all vars through Jinja."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase

SPEC = spec_from_file_location(
    'cac_resource_schema',
    Path(__file__).resolve().parents[1] / 'filter_plugins/cac_import.py',
)
schema = module_from_spec(SPEC)
SPEC.loader.exec_module(schema)


class ActionModule(ActionBase):
    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        try:
            self._templar.available_variables = task_vars
            metadata = self._templar.template(task_vars['cac_import_metadata'])
            resources = schema.resources_for_import(metadata, task_vars)
            # Render each value directly. A Jinja expression receiving the entire
            # vars mapping sees unrelated unsafe launch input and can mark the
            # whole returned graph unsafe before its nested templates resolve.
            # Templar preserves explicitly unsafe credential-injector strings.
            resources = self._templar.template(resources)
        except Exception:
            # Templating exceptions can include protected YAML or token values.
            raise AnsibleActionFail(
                'The declared configuration resources could not be prepared; inspect their protected inputs.'
            ) from None
        result.update(changed=False, ansible_facts={'cac_import_resources': resources})
        return result
