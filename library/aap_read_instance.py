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
author:
  - AAP AutoDeploy maintainers
"""
