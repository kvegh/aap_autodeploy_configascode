"""Run persistent credential lifecycle operations through the target API only."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import ssl

from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase

SPEC = spec_from_file_location('cac_api_lifecycle', Path(__file__).resolve().parents[1]
                              / 'src/cac_api_lifecycle.py')
lifecycle = module_from_spec(SPEC)
SPEC.loader.exec_module(lifecycle)


class ActionModule(ActionBase):
    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        args = self._task.args
        auth = args['authentication']
        client = lifecycle.Client(auth['hostname'], auth['token'], auth['username'], auth['password'])
        try:
            if args['operation'] == 'service_preflight':
                resources, credential_type = lifecycle.service_preflight(
                    client, args['contract'], args['password'], args['resources'])
                result.update(resources=resources, credential_type=credential_type, changed=False)
            elif args['operation'] == 'service_access':
                # This is the source EE's already trusted public CA store, not a fetched target secret.
                ca_file = ssl.get_default_verify_paths().cafile
                lifecycle.require(bool(ca_file), 'Prepare a trusted public CA bundle in the source EE.')
                ca = Path(ca_file).read_text()
                result.update(lifecycle.service_access(client, args['contract'], args['password'],
                                                       args['credential_type'], ca))
            elif args['operation'] == 'eda_access':
                result.update(lifecycle.eda_access(client, args['capability'], args['definitions']))
            else:
                raise lifecycle.LifecycleError('Unsupported credential lifecycle operation.')
        except lifecycle.LifecycleError as error:
            raise AnsibleActionFail(str(error)) from None
        except Exception:
            raise AnsibleActionFail('API-only credential preparation failed; inspect target state before retrying.') from None
        return result
