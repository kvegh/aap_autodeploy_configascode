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

## Target inventory mapping and current implementation boundary

Keep the exact instance name as the launch-time `aap_instance_key` input.
The shared all-hosts inventory has separate VM placement groups, each carrying
`hypervisor_host` as a group variable. Its value names an existing hypervisor
host in that same inventory. VM hosts join one placement group while retaining
their functional groups and existing host variables. Hypervisor hosts themselves
are not members of these VM groups. Existing aliases are retained rather than
renamed into names already used by service groups.

The protected definitions live in encrypted `cac/host_inventory.yml` in the
shared private configuration repository. Literal inventory variables survive
Vault serialization. A public structural example is
[`cac/host_inventory.yml.example`](../cac/host_inventory.yml.example).

This addition establishes inventory data and preserves the current target
prompt. It does not switch existing launchers away from their registry route,
change credential bindings, introduce API delegation or implement a replacement
workflow. Credential selection must be agreed before connecting that next stage.

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

The encrypted catalog must supply `cac_use_case_selector.seed_username` and
`seed_password` for orchestration on the seed. The target's administrator password
from base is a separate identity and is never used as a seed-login fallback.
Keep literal passwords tagged `!unsafe` when serializing the catalog.

When the seed uses a private issuer, attach the existing source CA credential to
the selector. Its private file injector supplies `AAP_CAC_SOURCE_CA_FILE`.
Source authentication, API reads and token cleanup use that file explicitly;
only the source job-launch/wait task receives `SSL_CERT_FILE`. Missing input
retains default trust. Certificate and hostname checks remain enabled, and target
API requests retain their normal trust context. No global trust-store change is
needed. A locally declared credential alone does not attach it to the live selector.

Before launching, the selector verifies unique fixed importer names, expected
playbooks, organization, project source URL, labels and bounded target/repository
surveys. It uses each just-validated template ID, verifies its exact captured
non-Machine credential associations and retains their scoped Git/Vault inputs.
Existing source credentials without an organization require exact reviewed
name, numeric ID, credential-type ID and type-name pins in the encrypted
`cac_use_case_selector.shared_seed_credentials` mapping. Pins cover only the
already-associated source credentials; all route credentials still require the
reviewed organization. This preserves existing ACLs and is not a general resource
ownership scheme. Re-review source-local pins when moving to another seed.
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
