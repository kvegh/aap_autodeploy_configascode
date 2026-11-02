#!/usr/bin/python
"""Documentation stub for the protected controller-side capture action."""
DOCUMENTATION = r"""
---
module: aap_cac_capture
short_description: Preview or accept reviewed encrypted Controller CaC changes
description: GET-only extraction, complete visibility proof, three-way comparison and guarded encrypted Git publication.
options:
  scope:
    type: str
    required: true
  mode:
    type: str
    choices: [preview, initialize, update]
    default: preview
  review_digest:
    type: str
    default: ''
  commit:
    type: bool
    default: false
  push:
    type: bool
    default: false
  working_copy:
    type: path
author:
  - AAP AutoDeploy maintainers
"""
