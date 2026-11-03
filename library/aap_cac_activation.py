#!/usr/bin/python
"""Import EDA definitions while preserving running state and never starting new ones.

The upstream 2.13 module ignores enabled:false for state:present, while its
state:disabled path skips updates to existing definitions. Use its normal
resolution/update implementation and change only the generated is_enabled
field: false for new definitions, observed state for existing definitions.
"""

DOCUMENTATION = r'''
---
module: aap_cac_activation
short_description: Import an activation definition without changing its active state
description:
  - Accepts the ansible.eda.rulebook_activation arguments.
  - Requires state present and restart false.
  - Creates new activations disabled and preserves existing enabled state.
author: AAP AutoDeploy maintainers
'''


def install_safety_guard(native):
    original_controller = native.Controller
    original_parameters = native.create_params
    original_module = native.AnsibleModule

    class DefinitionController(original_controller):
        observed_enabled = False

        def get_exactly_one(self, endpoint, *args, **kwargs):
            found = super().get_exactly_one(endpoint, *args, **kwargs)
            if endpoint == 'activations':
                if found and type(found.get('is_enabled')) is not bool:
                    self.module.fail_json(msg='The existing activation has no unambiguous enabled state.')
                self.observed_enabled = found['is_enabled'] if found else False
            return found

    def definition_parameters(module, controller, is_aap_24):
        parameters = original_parameters(module, controller, is_aap_24)
        parameters['is_enabled'] = controller.observed_enabled
        return parameters

    def definition_module(*args, **kwargs):
        module = original_module(*args, **kwargs)
        if module.params.get('state') != 'present' or module.params.get('restart'):
            module.fail_json(msg='Configuration imports only update definitions; explicit activation operations are separate.')
        return module

    native.Controller = DefinitionController
    native.create_params = definition_parameters
    native.AnsibleModule = definition_module


def main():
    from ansible_collections.ansible.eda.plugins.modules import rulebook_activation
    install_safety_guard(rulebook_activation)
    rulebook_activation.main()


if __name__ == '__main__':
    main()
