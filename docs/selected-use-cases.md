# Explicit selected use-case setup

Base deployment ends after stages01–04. The separate
`deploy-selected-use-cases.yml` selector prepares only selected use-case
requirements, then launches their existing configuration Job Templates. All
five project Job Templates use [the common API-only driver](cac-project-import.md).
The selector retains a distinct fresh-target check and infrastructure preparation;
the standalone importer also supports existing and self-target AAP instances.
Application jobs are not launched. New activation definitions are disabled and
existing activation states are preserved.

The reviewed selector catalog follows umbrella submodule paths. It derives each
deployment Job Template display name as **Deploy** followed by the fixed project ID
and the **CaC** suffix using the
[shared naming rule](cac-project-import.md); encrypted credential-map keys and
extraction matches use those same names:

| Submodule | Fixed project ID | Common playbook |
|---|---|---|
| `aap_autodeploy_configascode` | `aap_autodeploy_configascode` | `deploy-cac-project.yml` |
| `AIOps_selfhealing_demo` | `aiops-selfhealing-demo` | `deploy-cac-project.yml` |
| `automation-orchestrator` | `automation-orchestrator` | `deploy-cac-project.yml` |
| `disconnected-windows-patching` | `disconnected-windows-patching` | `deploy-cac-project.yml` |

Other declared modules have explicit unavailable reasons; empty, duplicate and
unknown selections fail before setup. Assistant Team has its standalone importer
but is not silently added as an umbrella submodule. Update the public eligibility
catalog and encrypted protected bindings when umbrella membership changes.
Actual source/private repository URLs, scoped credential pins and prerequisite
versions stay in `vaults/cac/aap_autodeploy_configascode-cac-vault.yml`.

## Launching the selector

Use its AAP Job Template with the shared `main inventory`. Choose the exact
`aap_instance_key` and supported use cases. Keep the saved source/catalog
credentials and **AAP API/MCP Auth Token Store**. Its injected JSON contains
per-instance API/MCP tokens; the selected inventory name determines which bearer
and HTTPS origin are used. That origin must match inventory `ansible_fqdn`. The
selector checks that the saved shared-store credential is forwarded unchanged.
Its Verify SSL flag must be true. It never selects a source bearer as target auth.

AAP inventory hosts store explicit FQDNs without scheme/path; VM placement groups
carry `hypervisor_host`. The separate preparation stage still requires the
completed protected instance route and pinned infrastructure SSH credentials.
Its saved AutoDeploy CaC Vault credential also decrypts the instance registry;
only the reader and Machine credentials are added for preparation routing.
Public origin/DNS and distinct controller checks remain. There is no guessed
hostname suffix, free-form destination URL or SSH API-login fallback.

Source orchestration uses only the encrypted catalog's explicit seed login and,
if supplied, its dedicated CA file. Source token creation, reads, job waits and
cleanup use this source trust context. Destination token selection cannot
replace the source login through extra-variable precedence. TLS verification
remains enabled. The source session is revoked; the operator's destination API
credential is preserved.

Before any child launch, the selector verifies unique importer identity,
organization, labels, reviewed SCM Project, common playbook, fixed project ID,
bounded survey and exact saved case credential associations. Source-global
credentials require their existing reviewed name/ID/type pins; no grants are
widened. Each generic child receives its saved Git/Vault/environment credentials
including the same saved shared API/MCP token-store credential. It receives
only the destination instance and diagnostic choice as launch variables: its
project ID, repository and capture file remain fixed on its saved template.

The separate prerequisite child additionally receives only the pinned Machine
credential. Its saved AutoDeploy repository read token and CaC Vault also read
and decrypt the registry. Stage05 uses
the selected instance bearer for PAH preparation and never scrapes installer
passwords. Existing infrastructure SSH preparation remains separate from API
requests. The approved temporary credential type is described in [instance token storage](instance-token-store.md). The redundant registry-reader type is no longer provisioned or used;
the separate allocation writer uses the same Git-token type with its own write token.

Every child is watched to actual completion, and the completed job's credential
associations must match the bounded launch set. Success publishes only bounded
selection/job/status results. A successful SCM update or metadata migration alone
does not establish a completed selector run. This migration does not run any
configuration import, application job, VM operation or activation.
