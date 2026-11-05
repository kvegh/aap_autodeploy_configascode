# Import a project into AAP

All six project Job Templates run `deploy-cac-project.yml`. Each template fixes
its `aap_cac_project_id` and retains its own private repository read token and
Vault credential. Operators choose the destination, not the repository or file.
The older five wrapper playbooks have been removed; all six templates select
the common playbook directly.

| Fixed project ID | Deployment Job Template | Derived private repository | Derived encrypted capture |
|---|---|---|---|
| `aiops-selfhealing-demo` | Deploy AIOps Selfhealing Demo CaC | `aiops-selfhealing-demo-secrets` | `vaults/cac/aiops-selfhealing-demo-cac-vault.yml` |
| `disconnected-windows-patching` | Deploy Disconnected Windows Patching CaC | `disconnected-windows-patching-secrets` | `vaults/cac/disconnected-windows-patching-cac-vault.yml` |
| `automation-orchestrator` | Deploy Automation Orchestrator CaC | `automation-orchestrator-secrets` | `vaults/cac/automation-orchestrator-cac-vault.yml` |
| `assistant-team` | Deploy Assistant Team CaC | `assistant-team-secrets` | `vaults/cac/assistant-team-cac-vault.yml` |
| `aap_autodeploy_configascode` | Deploy AAP Autodeploy Configascode CaC | `aap_autodeploy_configascode-secrets` | `vaults/cac/aap_autodeploy_configascode-cac-vault.yml` |
| `RHEL-sniperpatching` | Deploy RHEL Sniperpatching CaC | `RHEL-sniperpatching-secrets` | `vaults/cac/RHEL-sniperpatching-cac-vault.yml` |

Deployment names begin with **Deploy** and end with **CaC** to distinguish them
from application deployment jobs. Split the fixed project ID at hyphens and underscores, capitalize
each word and retain the original order. `aiops` becomes **AIOps** and `aap`
becomes **AAP**. The catalog uses this same rule rather than maintaining separate
name overrides. Existing template IDs, credentials and workflow links are retained;
application templates and SCM Projects keep their existing names.

The repository owner namespace comes from encrypted environment configuration:
`vault_cac_repository_namespace`, or the owner of the existing protected
`git_url`. Unknown IDs and repository/file overrides fail before authenticated
network operations. No repository owner or authentication value is hardcoded.
The separate platform bootstrap file remains `cac/base_CaC_vault.yml`.

The reviewed `RHEL-sniperpatching` ID preserves its exact repository and capture
casing; its display name retains **RHEL**. Other mixed-case IDs remain invalid.
RHEL uses the same importer and resource schema. Its capture declares the project,
seven Job Templates and reviewed inventory, host, execution-environment and
Satellite credential definitions. The Machine credential is an explicit existing
target binding. Readiness and dependency checks must pass before import; importing
definitions alone does not establish SSH access, package changes or a completed
patch cycle.

## Operator procedure

1. Choose the project's configuration Job Template after the destination's base
   installation is ready.
2. Set `aap_instance_key` to its exact host name in the shared inventory. That
   entry must have `ansible_fqdn`, for example `test-aap.example.invalid`. VM
   placement still uses the inventory's `hypervisor_host` group variable.
3. Keep the saved project Git/Vault/environment credentials and the shared
   **AAP API/MCP Auth Token Store** credential. The job selects that instance's
   bearer automatically; there is no destination credential prompt. The stored
   HTTPS origin must match `ansible_fqdn`, and certificates are verified.
   Missing, expired or mismatched access stops the job before the import.
4. Launch the configuration job. It checks the destination API from the source
   execution environment, retrieves the derived private repository, decrypts the
   one canonical capture, checks readiness/labels and imports the declared data.
5. Check the completed job result. Imports create definitions; application
   deployment, functional tests and explicit activation remain separate actions.

The destination may be the same AAP that launches the job. The standalone
importer has no fresh-instance or different-controller requirement. The optional
selector retains its distinct fresh-target and PAH preparation checks.
No SSH login, installer inventory password, source AAP bearer, or certificate
verification exception substitutes for destination API authentication.
The generic import passes only the selected bearer to the CoP roles and never
revokes that persistent API/MCP token. A native API credential attached in addition
to the shared store is refused because its injected variables could override selection. Credentials remain protected
when diagnostic logging is enabled. Temporary private checkouts are removed on
normal completion and ordinary failure; process interruption can prevent cleanup.

## Data and resource handling

`cac_import_metadata` schema version 1 declares the project ID, required template
label, canonical CoP resource variable to existing variable-path mappings,
readiness checks and a small allowlist of lifecycle capabilities. It cannot name
arbitrary task files or roles. Root variables cannot override importer facts,
API authentication, logging controls or the role dispatcher.

Existing nested capture lists and ordinary inputs are preserved, including
explicit `!unsafe` runtime templates. The importer maps only declared lists and
turns wildcard merging off, so another project's ambient variables are excluded.
Job launches, workflow launches, schedules and resource deletions are refused.
AutoDeploy's workflow graph is ordinary configuration data. Its extraction scope
still treats the deployment workflow as code-owned/report-only; the filename
migration does not add workflow writeback support.

CoP applies the common resource types. All inventory group skeletons finish
before the group role links children and hosts. EDA projects receive revision and
cache settings in their first application; Event Stream organization aliases are
normalized before the CoP role. Event Streams and decision environments precede
activation definitions. The activation adapter uses the installed native EDA
module but creates new definitions disabled and preserves existing enabled state
while updating definitions; it never invokes enable, disable or restart actions.

Persistent EDA Controller access is created only when its target credential is
absent, stored through the target API, and preserved on reruns. A newly issued
token is revoked after failure only when its credential is proved absent.
Unknown persistence outcomes preserve the token for review.

Assistant's dedicated service identity uses API-only preflight checks: one
nonprivileged user, one inventory grant, no team membership and the exact
credential schema. An existing authenticated user's password is omitted from
updates. New service access is stored directly in its target Controller
credential, with a public binding to the user, inventory, CA and token metadata.
Reruns preserve masked inputs. Legacy or ambiguous access requires explicit
recovery; the importer neither rotates it nor reads target token files.
All six embedded deployment/authentication snapshots must remain fully encrypted.

Windows target CA and SSH-known-host data must already be prepared in encrypted
configuration. The importer does not discover them using SSH or invent them.
This public trust data is used by the imported application credential, not to
replace the selected destination API token.

## Preparation, validation and deployment evidence

`05-prepare-use-cases.yml` stays separate from pure configuration import. It
uses the same shared token-store credential and selected instance. PAH calls use
that bearer; infrastructure SSH remains separate. The selector forwards the
same saved store credential to preparation and each importer, while keeping each
importer's own repository Git/Vault pair. Preparation still permits its reviewed
Machine credential to be supplied for the selected hypervisor.

See [instance token storage](instance-token-store.md) for the encrypted source,
population during base deployment and the external secret-manager backlog.

The source EE's cached base image was inspected read-only, without pulling an
image or installing content. Its core is 2.16.19. The actual source Project's
requirements cache supplies `infra.aap_configuration` 4.10.0, `ansible.eda` 2.13.0,
`ansible.controller` 4.8.11, `ansible.platform` 2.7.20260930 and `ansible.hub` 1.1.2.
Version-matched activation fixtures mock only the API boundary, including the
actual source action process; they never contact a live activation endpoint.

Offline validation covers all six maintained captures under both Ansible
native modes, ownership/label/readiness checks, literal templates, group
relationships, masked-secret preservation, token failure cleanup, explicit
instance-token selection and selector forwarding. SCM synchronization and Job Template
metadata verification establish publication only. AIOps CaC was subsequently verified live on a disposable target; that proof is
separate from application deployment and EDA activation.

The RHEL configuration import and receiving-runtime diagnostic have now passed.
Independent readback verified the seven project templates, six surveys, owned
host pair and API/runtime resources while preserving existing template
definitions. These checks establish configuration and Satellite connectivity;
targeted host patching on the original demonstration Controller was verified
separately. The chosen receiving Machine credential's SSH key was not exported
or equated with the original key.
