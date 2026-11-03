# AAP AutoDeploy: deployment overview

[README.md](README.md) contains setup instructions, inputs and current behavior.
[PLAN.md](PLAN.md#todo) retains the older backlog; Beads tracks current work. Each open area explains
why it matters and the intended result; completed work is at [Done:](PLAN.md#done).
[design_decisions_history.md](design_decisions_history.md) preserves past decisions.

## Deployment sequence

Each stage is a separate AAP Job Template. Base deployment runs stages 01–04
on success and stops. The [separate selector](docs/selected-use-cases.md) prepares
only explicitly selected prerequisites and imports the selected Projects and CaC.

| Stage | Playbook | Purpose |
|---|---|---|
| 01 | `01-linux-vm-setup.yml` | Clone the prepared golden image and discover its address. |
| 02 | `02-infra-config.yml` | Configure DNS, certificates and reverse-proxy routing. |
| 03 | `03-aap-install.yml` | Prepare the guest and run the bundled AAP installer. |
| 04 | `04-aap-config.yml` | Apply subscription and platform-only base configuration. |
| Separate | `05-prepare-use-cases.yml` | Prepare the selected PAH collections and existing execution image. |

The five project Job Templates all run `deploy-cac-project.yml` with a fixed
project ID. Their names begin with **Deploy**; the unused per-project wrappers
have been removed. AutoDeploy's capture restores deployment templates and its
workflow on the replacement. Importing definitions does not establish functional
demo readiness. New activations are disabled; existing active states are preserved.

Stage 01 records a verified instance handoff for later installation stages.
Stage 03 uses a separate installer hostname. Project imports select an inventory
host and use its explicit `ansible_fqdn` over verified HTTPS from the source EE.
Credentials are not passed through workflow artifacts.

Recover a failed sequence by rerunning the failed stage with the same inputs and
then launching remaining stages. A full workflow relaunch creates another VM.
Stage 03 can observe an existing installer using its async-job identifier;
it does not need to start the installer again.

`destroy-test-aap.yml` is separate guarded teardown, never a deployment-workflow
step. Review its exact target before launching it.

## Configuration and secrets

Base owns platform settings, subscription, desired administrator password,
bootstrap Git/Vault access, persistent MCP access and PAH source configuration.
Use-case files own their projects, inventories, credentials, execution
environments, labels, templates, workflows and integrations. Each has a separate
Job Template using the shared importer; Stage 04 does not load all use cases implicitly.

Public empty templates are in `cac/`. Populated working files and Vault password
files stay outside Git. Completed configuration is whole-file encrypted, checked
for successful decryption/equality, then committed to its private repository.
The manifest is the complete ZIP encrypted as `cac/manifest.zip.vault`.

Imports fetch the chosen private repository's `main` branch using a credential
injecting `CAC_GIT_TOKEN`. A separate Vault credential with identifier `cac`
decrypts its contents. The original Vault credential is still needed for
`myvars`, which supplies environment/guest-access settings. Target authentication
requires an explicitly selected native AAP API credential for project imports
and prerequisite preparation; it never reads installer passwords for those jobs.
Stage 04's separate bootstrap behavior manages the desired administrator password;
see [Stage 04 inputs](README.md#stage-04-inputs).

Base creates five repository-specific Git-read credentials and five matching
CaC Vault credentials on the replacement from encrypted inputs. The first trusted seed still needs those
initial access secrets supplied independently. Target-issued MCP/PAH/EDA tokens
belong to their installation; API exports cannot recover masked secret values.
Persistent MCP recovery storage is on the target; encrypted client write-back
remains in the project TODO.

## Collection supply

Base configures certified, validated and community PAH sources and organization
attachments without content synchronization. Stage 05 prepares declared use-case
requirements later. Project requirements select collections; organization
credentials select the PAH download sources. Direct public Galaxy project access
is not this project's policy; PAH may use Galaxy as its community upstream.

Remote highest-version selection and repository snapshot retention are separate
settings. Base configures both; collection pruning is a separate reviewed
preview/apply operation, not an automatic effect of base deployment.

## Verification status

On 20 October 2026 a fresh replacement completed stages 01-04, prerequisite
preparation and all five captured use-case imports through individually launched
jobs. Bootstrap credential bindings and persistent MCP access were independently
checked. Full CoP/API production-versus-replacement comparison was completed;
Windows and Orchestrator follow-up configuration fixes were also imported.

Full workflow execution, recursive deployment, safe reruns, functional demo tests
and production takeover remain open in [PLAN.md](PLAN.md#todo). Sensitive evidence
and detailed environment comparisons stay outside Git. Historical completion
notes are available in Git history and the decision history, rather than a second
TODO list here.
