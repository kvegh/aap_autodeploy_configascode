#!/usr/bin/python
"""Ansible entry point for the bounded native AAP cold snapshot operation."""
from ansible.module_utils.basic import AnsibleModule
import os
from ansible.module_utils.aap_snapshot import Manager, native_preflight, native_lock, policy


def main():
    module = AnsibleModule(argument_spec={
        'route': {'type': 'dict', 'required': True}, 'primary': {'type': 'dict', 'required': True},
        'policy': {'type': 'dict', 'required': True}, 'checkpoint': {'type': 'str', 'required': True},
        'external_state': {'type': 'dict', 'required': True},
        'guest_machine_id': {'type': 'str', 'required': True},
        'protected_production_ipv4': {'type': 'str', 'required': True},
        'operation': {'type': 'str', 'choices': ['create', 'restore'], 'default': 'create'},
    }, supports_check_mode=True)
    p = module.params
    lock = None
    try:
        policy(p['policy'], p['checkpoint'], p['route']['vm_name'])
        native_preflight(p['route'], p['primary'], p['protected_production_ipv4'], p['policy']['minimum_free_bytes'])
        lock = native_lock(p['primary'])
        result = Manager().execute(p['route'], p['primary'], p['policy'], p['checkpoint'], p['external_state'],
                                   p['guest_machine_id'], p['operation'], module.check_mode)
        module.exit_json(**result)
    except Exception as error:
        module.fail_json(msg=str(error), changed=getattr(error, 'changed', False),
                         operation_outcome='Inspect native snapshot and VM state before retrying an uncertain mutation.')
    finally:
        if lock is not None:
            os.close(lock)


if __name__ == '__main__':
    main()
