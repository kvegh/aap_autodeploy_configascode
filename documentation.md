# AAP AutoDeploy: deployment overview

[README.md](README.md) contains setup instructions, inputs and current behavior.
[PLAN.md](PLAN.md#todo) is the single project TODO list: each open area explains
why it matters and the intended result; completed work is at [Done:](PLAN.md#done).
[design_decisions_history.md](design_decisions_history.md) preserves past decisions.

## Deployment sequence

Each stage is a separate AAP Job Template. The complete workflow runs stages
01-05 on success, then applies the five captured use cases in parallel.

| Stage | Playbook | Purpose |
|---|---|---|
| 01 | `01-linux-vm-setup.yml` | Clone the prepared golden image and discover its address. |
| 02 | `02-infra-config.yml` | Configure DNS, certificates and reverse-proxy routing. |
| 03 | `03-aap-install.yml` | Prepare the guest and run the bundled AAP installer. |
| 04 | `04-aap-config.yml` | Apply subscription and platform-only base configuration. |
| 05 | `05-prepare-use-cases.yml` | Prepare the declared PAH collections and existing execution image. |

The five importers are `deploy-aiops-demo.yml`, `deploy-windows-demo.yml`,
`deploy-orchestrator-demo.yml`, `deploy-assistant-team.yml` and
`deploy-autodeploy.yml`. AutoDeploy restores the deployment templates and workflow
on the replacement. Importing definitions does not establish functional demo
readiness; applying enabled EDA activations can start them.

Stage 01 publishes only `vm_name`, `vm_ip` and `aap_hostname` as workflow artifacts.
Stage 03 uses a separate installer hostname. Stage 04 and the use-case importers
connect through the explicit `aap_hostname` HTTPS URL, allowing an internal route
independent of VM naming and public reverse-proxy access. Credentials are not
passed through workflow artifacts.

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
configuration importer; Stage 04 does not load all use cases implicitly.

Public empty templates are in `cac/`. Populated working files and Vault password
files stay outside Git. Completed configuration is whole-file encrypted, checked
for successful decryption/equality, then committed to its private repository.
The manifest is the complete ZIP encrypted as `cac/manifest.zip.vault`.

Imports fetch the chosen private repository's `main` branch using a credential
injecting `CAC_GIT_TOKEN`. A separate Vault credential with identifier `cac`
decrypts its contents. The original Vault credential is still needed for
`myvars`, which supplies environment/guest-access settings. Target authentication
supports the configured password and installer bootstrap; base manages the
desired password. See [Stage 04 inputs](README.md#stage-04-inputs).

Base creates four private Git-read credentials and the CaC Vault credential on
the replacement from encrypted inputs. The first trusted seed still needs those
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
