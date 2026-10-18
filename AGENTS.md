# Project working rules

This repository owns AAP deployment and configuration as code. Keep changes
scoped to this project and follow the workspace security and approval rules.

## Secrets

Never commit secrets or sensitive environment-specific values in plaintext,
including account names, hostnames, addresses, passwords, tokens, and keys.
Ansible Vault-encrypted files or values are allowed. Plaintext templates and
documentation must use generic placeholders. Keep Vault password files,
including `vpf`, outside Git; an ignore rule does not protect an already tracked
file. Review staged files before every commit and push.

## Versions and releases

- `VERSION` is the project version; it is separate from the AAP installer version.
- The initial source baseline is `0.0.1`. Every subsequent commit increments
  `VERSION`, including documentation and decision-history commits.
- Features increment the minor version and reset patch. All other changes
  increment patch. Preserve the major version unless a different policy is agreed.
- Use `python3 src/bump-version.py` for a patch increment, or add `--feature`
  for a feature increment. Run it once for each commit after the baseline.
- Maintain incremental `RELEASE_NOTES.md` describing the final behavior and
  meaningful validation. Use "Document" rather than "Record" in documentation-only
  commit subjects and release-note summaries. Preserve historical commit subjects.
- Keep README.md current and commit it with the implementation. Document lasting
  decisions and rationale in `design_decisions_history.md`. When the implementation
  commit ID is not yet known, add it in a following documentation commit, which
  also requires a patch increment and release-note entry.
- A version increment is not a published release. When a release is requested,
  push an annotated `v<VERSION>` Git tag and publish the matching GitHub release.
  Tag the commit containing that exact version, even if later documentation
  commits have already incremented the branch version.
- Report the validation performed and the deployment state accurately. Keep any
  deployed project version/build metadata aligned with the source actually used.
  A tooling-only release does not establish successful end-to-end AAP deployment.

## Validation

Version-tool tests use Python's standard library:

```bash
python3 -m unittest discover -s tests -v
git diff --check
```

Use focused Ansible validation for playbook changes. Do not launch deployment,
configuration, or teardown jobs merely to validate documentation or version tools.
