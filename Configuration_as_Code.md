# Configuration as Code

AAP post-install configuration uses the `dispatch` role from `infra.aap_configuration`,
the [Red Hat Communities of Practice AAP Configuration Collection](https://github.com/redhat-cop/infra.aap_configuration#readme).
CoP means Community of Practice. Both `04-aap-config.yml` and
`restore-windows-config.yml` use this role to apply our AAP object definitions.

## How dispatch works

The `dispatch` role auto-merges suffixed variables into base variables. With `dispatch_include_wildcard_vars: true`, it discovers all variables matching a pattern (e.g., `controller_templates_*`), merges them into `controller_templates`, and applies them through the appropriate service collection, including `ansible.controller` and `ansible.platform`.

This lets us split configuration into logical files — one per project group — without writing any glue code. The dispatch role handles the merge and the module calls.

## Target playbook (04-aap-config.yml)

The current `04-aap-config.yml` first clones the private repository supplied as
`aap_config_repo_url`, always using `main`. It requires HTTPS without credentials
embedded in the URL. A custom AAP credential injects `CAC_GIT_TOKEN`; a temporary
Git askpass helper provides it during authentication. Token-bearing tasks hide
their output by default; `debug_logging: true` disables that protection. Normal
Git TLS verification remains enabled, redirects and stored Git
credential helpers are disabled, and submodules are not fetched.

Before running dispatch, the playbook requires a Vault-encrypted
`cac/base_CaC_vault.yml` in that checkout and loads it with `include_vars`.
The attached Vault credential with identifier `cac` decrypts this file. The
playbook also requires the whole-file encrypted ZIP at `cac/manifest.zip.vault`.
Ansible's `copy` action decrypts it using that same attached Vault credential,
creating a mode-`0600` temporary ZIP. `ansible.controller.license` imports it into
the explicit target AAP before dispatch; `force: false` preserves an existing
non-trial license on reruns. The temporary checkout, ZIP, and helper are removed
after success or ordinary task failures. Fatal role-loading errors or interruptions
can prevent cleanup. A failed subscription import prevents dispatch. A per-run
Gateway token authenticates both the license module and dispatch, then is revoked
in cleanup. Workspace removal still runs if revocation fails.
The role sees the loaded suffixed variables and applies them as before. Step 04
excludes the legacy `controller_applications` role on AAP 2.7; Gateway's role
handles `aap_applications` through `ansible.platform` instead.

`myvars` and `vars/main.yml` remain in `vars_files`. Keep the original/default
Vault credential attached alongside the `cac` credential because installer SSH
access still comes from `myvars`. Unless current `aap_password` is supplied in
encrypted configuration, Step 04 uses those SSH credentials and sudo to read
`gateway_admin_password` from the target's installer inventory. It creates a
Gateway token for the API calls instead of sending the saved password to the
Controller API. Supply the target HTTPS URL
explicitly as `aap_hostname`. Stage 04 does not use `vm_name`, `vm_ip`, or
`vault_domain` to choose its target. Use an internally resolving hostname or an
internal IP in that HTTPS URL to avoid the public reverse-proxy route. Password
rotation, removing `myvars`, and demo loading remain future work.
See [README.md](README.md#stage-04-inputs) for inputs
and execution-environment requirements. Live job 1985 successfully applied the
shared base configuration, revoked its token, and removed its workspace. Earlier
testing verified subscription import; the successful rerun preserved that license.
Per-demo configuration loading and full deployment-pipeline verification remain
separate pending work.

## Collection sources

The AAP running Stage 04 must download project collections from PAH only.
Before project synchronization, sync the required certified, validated, and
community collections and their dependencies into PAH, then attach credentials
for those PAH repositories to the project's organization. The requirements file
selects collections; these organization attachments select their download
sources. Direct public Galaxy access is not recommended and must not be
configured as a project fallback under this policy. PAH may sync community
content from public Galaxy upstream.

Include the PAH source credentials and organization associations when preparing
CaC for another instance, keeping token values encrypted. The AAP running this
job needs its own source configuration beforehand; applying configuration to a
target does not bootstrap the running job's dependency downloads.

## CaC file layout

```
working-directory/cac/        # editable configuration outside Git
    base.yml                   # shared resources (org, users, credentials, EEs, inventories, hosts, projects, labels)
    selfhealing.yml            # AIOps self-healing demo JTs + EDA          (complete)
    simroi.yml                 # simulated ROI dashboard JTs + schedules    (complete)
    orchestrator_deploy.yml    # Automation Orchestrator JTs                (complete)
    autodeploy.yml             # autodeploy pipeline JTs (01-04 + destroy)  (complete)
    servicenow.yml             # ServiceNow ITSM integration               (skeleton)
    config_exceptions.yml      # configuration drift detection              (skeleton)
    intelligent_assistant.yml  # Intelligent Assistant                      (skeleton)
```

The private configuration repository stores encrypted copies under `cac/`, named
`base_CaC_vault.yml` and `DEMO_PLACEHOLDER_CaC_vault.yml`. The shared encrypted
base has moved there. Editable working files remain outside Git.

The private repository also holds `cac/manifest.zip.vault`, which encrypts the
complete subscription ZIP without converting or unpacking its contents.

This public repository retains two empty plaintext examples: use
`cac/base_CaC_vault.yml.example` for shared resources and
`cac/project.yml.example` for a demo. Both examples contain empty resource lists
and commented entries with generic placeholders. See [README.md](README.md)
for the preparation, encryption, verification, and commit workflow. Stage 04
loads only the shared `cac/base_CaC_vault.yml` from `main`; adding another encrypted
file to the private repository does not automatically apply that demo.

## Variable naming

Each file uses a dispatch suffix on every variable. The suffix matches the project group name.

Prefixes follow the CoP convention: `aap_*` for platform-level objects (gateway-managed), `controller_*` for controller objects, `eda_*` for EDA, `hub_*` for Hub.

| Variable pattern | Resource type |
|---|---|
| **Platform (aap_\*)** | |
| `aap_organizations_{suffix}` | Organizations |
| `aap_teams_{suffix}` | Teams |
| `aap_user_accounts_{suffix}` | Users |
| `aap_applications_{suffix}` | OAuth2 applications |
| **Controller (controller_\*)** | |
| `controller_credentials_{suffix}` | Credentials |
| `controller_credential_types_{suffix}` | Custom credential types |
| `controller_projects_{suffix}` | Projects |
| `controller_inventories_{suffix}` | Inventories |
| `controller_hosts_{suffix}` | Hosts |
| `controller_groups_{suffix}` | Host groups |
| `controller_templates_{suffix}` | Job templates |
| `controller_workflows_{suffix}` | Workflow job templates |
| `controller_schedules_{suffix}` | Schedules |
| `controller_notifications_{suffix}` | Notification templates |
| `controller_labels_{suffix}` | Labels |
| `controller_execution_environments_{suffix}` | Execution environments |
| `controller_settings_{suffix}` | Controller settings |
| `controller_roles_{suffix}` | RBAC role assignments |
| **EDA (eda_\*)** | |
| `eda_projects_{suffix}` | EDA projects |
| `eda_credentials_{suffix}` | EDA credentials |
| `eda_decision_environments_{suffix}` | Decision environments |
| `eda_rulebook_activations_{suffix}` | Rulebook activations |
| `eda_event_streams_{suffix}` | Event streams |

Gotchas: `controller_templates` (not `controller_job_templates`), `aap_user_accounts` (not `aap_users`), `controller_notifications` (not `controller_notification_templates`), `aap_organizations` (not `controller_organizations`).

## Resource inventory

What the CaC files capture from the current AAP instance:

### base_CaC_vault.yml (shared)
- 1 organization (Default)
- 4 users (admin, kkrzywic, mnolo, orchestrator_svc)
- 4 credentials (hypervisor, default machine, vault, PAH token)
- 1 custom EE (Orchestrator EE — ee-supported-rhel9)
- 3 inventories (main inventory, Localhost, ROInventory)
- 9 hosts across the 3 inventories
- 4 projects (automation-ng-repo, SelfHealing Repo, Advanced AAP Features, AAP Advanced Features)
- 6 labels
- 1 generic JT (VMs deploy locally)

### selfhealing.yml (2 JTs + 1 EDA activation)
- Deploy Zabbix Agent — deploys agent to testserver1
- Run Claude to analyse and fix — Claude CLI self-healing on tra
- Zabbix Rulebook v3 — EDA activation, triggers "Run Claude" on Zabbix agent-down alerts
- EDA credentials and Event Stream are documented but commented (API doesn't expose them for listing)

### simroi.yml (5 JTs + 5 schedules)
- Patch RHEL, Deploy App Updates, Security Scan, Database Backup, Firewall Rule Update
- All use `roi_demo.yml` playbook against ROInventory
- Each has a 2-hour schedule

### orchestrator_deploy.yml (2 JTs)
- Deploy Automation Orchestrator — OCP deployment with survey
- Cleanup AAP after Orchestrator — removes OAuth2 apps for fresh redeploy

### autodeploy.yml (5 JTs)
- 01 VM Setup, 02 Infra Config, 03 AAP Install, 04 AAP Config, Destroy VM v2
- Various inventories and credentials per step
- Most use Orchestrator EE

### Skeletons (TODOs)
- servicenow.yml — ServiceNow ITSM bootstrap playbooks
- config_exceptions.yml — configuration drift detection
- intelligent_assistant.yml — AI assistant features

## Secret handling

Incomplete CaC files use `CHANGEME` placeholders. The working-copy workflow is:

1. Edit and complete plaintext configuration in the working directory outside Git.
2. Create a separate whole-file Vault-encrypted copy with the local password file.
3. Put that copy in the private configuration repository's `cac/` directory.
4. Verify the Vault header, successful decryption, and equality with the working
   copy without displaying secrets.
5. Review staged files, then commit and push only the encrypted configuration.

The Vault password file remains outside both repositories. Secret backup to
Bitwarden remains a separate TODO.

## Windows patching workflow restore

The external `disconnected_windows_patching.yml` CaC file captures the Windows
project, deployment Job Template, survey and `Deploy Windows + WSUS environment`
workflow. It is staged alongside the other external CaC files for encryption
and review before inclusion in the private configuration repository. Step 04 does
not load it yet. The four nodes have no
edges and can run concurrently because their Job Template has
`allow_simultaneous: true`. Concurrent workflow runs remain disabled to avoid
competing deployments of the same four VM names.

Objects are referenced by name and organization rather than source-instance
IDs. The Git project uses HTTPS and branch `main`; project creation waits for
sync before the Job Template is applied. The current deployment playbook selects
boot mode from the verified images, so the old template-side boot expression
is omitted from the restore configuration.

On a new AAP, provision these shared dependencies through the private
`cac/base_CaC_vault.yml` first, after verifying Stage 04's target authentication
and execution-environment dependencies:

- Organization `Default`.
- `main inventory`, including the `hypervisor` group and target host/connection
  variables appropriate for that environment.
- `hypervisor cred`, including its SSH key and any required privilege-escalation
  secrets. Secret values cannot be recovered from the controller API.
- `Orchestrator EE` and its registry pull credentials if required.

The target hypervisor must already have both images and the `internal` and
`windows-isolated` networks. Change the node variables if target network names
or VM names differ. The capture has environment-specific references and must be encrypted or
parameterized before inclusion in Git. Shared secret configuration remains
vault-encrypted.

To apply only the Windows objects after the shared dependencies are provisioned,
use `restore-windows-config.yml` with `windows_cac_file` pointing to the external
reviewed/encrypted file. It avoids Step 04's existing `myvars` path
and takes authentication from a separately supplied protected file:

```bash
ansible-playbook restore-windows-config.yml \
  -e windows_cac_file=/secure/disconnected_windows_patching.yml \
  -e @/secure/target-aap-auth.yml --ask-vault-pass
```

The encrypted authentication file supplies `aap_hostname` and `aap_token`, or
`aap_username` / `aap_password`. TLS verification defaults to enabled. Ensure
`ansible.controller` and the dispatch role's dependencies are available in the
execution environment, installing required collections from approved PAH
repositories beforehand. A local CLI run must also use PAH sources rather than
the default public Galaxy source. Keep registry and SSH secrets outside
plaintext config.

Neither restore entry point launches VM jobs. This restores configuration, not
running guests or Windows account/WinRM setup. No restore against a second AAP
has been performed yet. Reapplying the simplified workflow config creates or
updates these four nodes; it does not remove unrelated nodes added manually.
