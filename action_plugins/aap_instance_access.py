"""Select one instance token from the approved injected private credential file."""

from importlib.util import module_from_spec, spec_from_file_location
import json
import os
from pathlib import Path

from ansible.plugins.action import ActionBase

spec = spec_from_file_location("instance_keys", Path(__file__).resolve().parents[1] / "src/aap_instance_keys.py")
keys = module_from_spec(spec)
spec.loader.exec_module(keys)


class ActionModule(ActionBase):
    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        try:
            require = keys.require
            require(set(self._task.args) == {"instance_name", "fqdn"},
                    "Select an inventory instance without token-file overrides.")
            require(not any(os.environ.get(key) for key in ("AAP_HOSTNAME", "AAP_TOKEN", "AAP_USERNAME", "AAP_PASSWORD")),
                    "Use the shared instance token store instead of an attached native destination API credential.")
            filename = os.environ.get("AAP_INSTANCE_KEY_STORE_FILE", "")
            require(bool(filename), "Attach AAP API/MCP Auth Token Store to this job template.")
            path = Path(filename)
            require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 8 * 1024 * 1024,
                    "Require a regular injected instance token file.")
            data = json.loads(path.read_text())
            auth = keys.select_access(data, self._task.args["instance_name"], {"ansible_fqdn": self._task.args["fqdn"]})
        except keys.StoreError as error:
            result.update(changed=False, access_error=str(error))
            return result
        except Exception:
            result.update(changed=False, access_error="The protected instance token file could not be read or validated.")
            return result
        result.update(changed=False, authentication=auth)
        return result
