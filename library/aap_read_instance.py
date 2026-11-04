#!/usr/bin/python
"""Documentation stub for the read-only controller action."""
DOCUMENTATION = r"""
---
module: aap_read_instance
short_description: Resolve one instance from the shared encrypted registry
description: Uses the scoped registry credential and attached CaC Vault secret without mutating Git or AAP.
options:
  instance_key:
    type: str
    required: true
  expected_route:
    type: dict
  allow_retired:
    type: bool
    default: false
    description: Read consumed retired history only for an explicit cleanup retry.
  read_related_resources:
    type: bool
    default: false
    description: For decommission only, verify related ownership in the fixed source AAP inventory.
author:
  - AAP AutoDeploy maintainers
"""
