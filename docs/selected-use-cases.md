# Explicit selected use-case setup

Base deployment ends after stages 01–04. `deploy-selected-use-cases.yml` runs
separately on a trusted seed AAP or control node. It prepares only selected
requirements, then invokes the existing configuration importers with their own
Git/Vault credentials. Those create the selected SCM Projects, Job Templates,
labels and related saved CaC on a distinct fresh AAP. Application jobs are not
run. Imported AIOps activations stay disabled.

The reviewed catalog follows the umbrella `.gitmodules` paths. Current support:

| Submodule | Configuration importer |
|---|---|
| `aap_autodeploy_configascode` | `deploy-autodeploy.yml` |
| `AIOps_selfhealing_demo` | `deploy-aiops-demo.yml` |
| `automation-orchestrator` | `deploy-orchestrator-demo.yml` |
| `disconnected-windows-patching` | `deploy-windows-demo.yml` |

The other six declared submodules are listed with a missing reviewed capture/
importer reason. Selecting one fails before setup. Empty, duplicate and unknown
selections also fail. Assistant Team and the recovery project are not umbrella
submodules; their standalone configuration/captures are not silently selected.

The public eligibility table is `vars/use-case-catalog.yml`. Actual repository
URLs and prerequisite pins remain in encrypted `cac/autodeploy.yml`, under
`cac_use_case_selector` and `cac_use_case_prerequisites`. Refresh that reviewed
catalog when umbrella membership changes.

AIOps has a dedicated private configuration companion containing
`cac/aiops_demo.yml` and uses its own Git-read credential provisioned from
`cac_bootstrap_git_credentials.aiops` in encrypted base. Its public automation
source remains separate. The shared catalog and completed-instance registry
continue to use the base configuration repository; changing the AIOps capture
repository must not retarget either shared input.

## Invocation

```sh
ansible-playbook -i localhost, deploy-selected-use-cases.yml \
  -e aap_seed_hostname=https://seed.example.invalid \
  -e aap_instance_key="$INSTANCE_KEY" \
  -e aap_use_case_catalog_repo_url=https://git.example.invalid/team/configuration.git \
  -e '{"aap_selected_use_cases":["AIOps_selfhealing_demo","disconnected-windows-patching"]}'
```

Supply the existing CaC Git-token credential, `cac` Vault credential, environment
Vault and separate registry-reader credential. The exact instance key must have
a completed route in the latest encrypted registry; it determines the target's
public URL and both SSH peer keys. There is no free-form target URL fallback.
Both HTTPS origins must be trusted, public A records must identify only the
pinned hypervisor, and unpinned AAAA records are refused. The seed must have the
updated labelled configuration importers and the bounded Stage 05 selection
survey. The fresh target must already have received base configuration and its
configured administrator login. Distinct instance UUIDs are read from both APIs,
preventing a different URL for the seed from passing as a fresh target.

Before launching, the selector verifies unique fixed importer names, expected
playbooks, organization, project source URL, labels and bounded target/repository
surveys. It uses each just-validated template ID, verifies its exact captured
non-Machine credential associations and retains their scoped Git/Vault inputs.
Credential prompting adds only the fixed registry-reader, the distinct
`instance_registry` Vault identity and the route's named Machine credential.
Case Vault identities must remain unique. Standalone importer runs require the
same explicit key and scoped route credentials; wrong Machine access fails the
pinned jump authentication. Completed jobs' actual credential associations are
also verified. Each setup job must finish successfully before proceeding. Bounded
job IDs/statuses are published after successful completion; launch acceptance
alone does not establish setup success.

The encrypted AutoDeploy capture defines `Configure Selected AAP Use Cases`
with the same scoped credentials as its existing importer, a bounded multiselect,
explicit seed/registered-instance/repository prompts and a twelve-hour overall timeout.
Importing that capture creates the template; a local declaration alone does not
make it available in AAP. The base workflow and selector are not launched by
configuration import. No live selector run or new fresh deployment is claimed.
