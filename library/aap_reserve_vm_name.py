#!/usr/bin/python
"""Documentation stub; the controller-side action plugin performs this action."""
DOCUMENTATION = r"""
---
module: aap_reserve_vm_name
short_description: Reserve an AAP test-VM name in shared encrypted Git state
description: Uses conditional non-force Git publication and the attached CaC Vault secret before provisioning.
options:
  prefix:
    type: str
    required: true
  hypervisor_id:
    type: str
    required: true
  observed_floor:
    type: int
    default: 1
  request_id:
    type: str
  instance_route:
    type: dict
  instance_resources:
    type: dict
    description: Complete verified primary AAP ownership, published with its consumed route only.
author:
  - AAP AutoDeploy maintainers
"""
