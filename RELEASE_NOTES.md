# Release notes

## 0.0.7

Document planned work to make deployment jobs reusable and independently runnable.
Step 04 should accept the target AAP URL and credentials directly, allowing it to
configure an existing installation without our VM naming or domain scheme.
Provisioning-specific inputs should stay in stages that need them, using established
collection input names where available. Whitespace and staged-file checks passed.
This adds TODOs only; playbooks are unchanged and no AAP jobs were run.

## 0.0.6

Document why the project credits the Red Hat Communities of Practice collection
for its AAP configuration role, referencing the documentation update in `e97480d`.
Whitespace and staged-file checks passed.

## 0.0.5

Document that AAP post-install configuration uses the Red Hat Communities of
Practice collection `infra.aap_configuration`. Identify its `dispatch` role in
Step 04 and the Windows restore playbook, explain its purpose, and link upstream.
Verified both playbooks and the collection's official README; whitespace checks
passed. Deployment behavior is unchanged; no AAP jobs were run.

## 0.0.4

Document the private-configuration separation implemented in `6583b61`, including
the external plaintext working files, verified encrypted-copy workflow, preserved
history, and outstanding Step 04 loading integration. Whitespace and staged-file
checks passed. This documentation update does not publish a release or deploy AAP.

## 0.0.3

Move the populated encrypted shared CaC base to a separate private configuration
repository and retain generic examples here. Keep editable plaintext configuration
outside Git; encrypt a copy, verify its Vault header and decrypted equality, then
commit and push the encrypted copy to the private repository.

The private copy was verified and pushed before removing this repository's copy.
Step 04 is unchanged and still expects the former local file, so it cannot run
from this checkout alone. Private-configuration loading remains to be implemented.
No AAP deployment or configuration jobs were run.

## 0.0.2

Document the version-policy and reusable CaC template decisions implemented in
`f3efca9`. Explain independent project versions, generic templates versus populated
encrypted configuration, and the scope of validation. This is the required
decision-history follow-up to the `0.0.1` source baseline.

## 0.0.1

Establish the initial tracked source baseline and adopt a per-commit version
policy: minor increments for features, patch increments for all other commits,
including documentation and decision history. Add the version-bump helper,
project working rules, a current README, and retrospective decision history.

Include empty shared and per-demo CaC templates with generic commented examples.
A fresh checkout can use these as a starting point without obtaining a private
configuration export. Document encryption before committing populated sensitive
configuration and keep Vault password files outside Git.

Validation: all four command-line version tests passed; both templates parsed as
valid YAML with empty resource lists; existing secret files remain Vault-encrypted;
Vault password paths are ignored; and Git whitespace checks passed. The current AAP
deployment and configuration pipeline has not been verified end to end since
the repository split. Demo selection, authentication alignment, and dispatch
dependency readiness remain outstanding. This release adds source tooling and
templates; it does not deploy or configure an AAP instance.
