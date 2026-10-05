# Configuration as Code

AAP post-install configuration using the `infra.aap_configuration` collection's `dispatch` role.

## How dispatch works

The `dispatch` role auto-merges suffixed variables into base variables. With `dispatch_include_wildcard_vars: true`, it discovers all variables matching a pattern (e.g., `controller_templates_*`), merges them into `controller_templates`, and applies them via `ansible.controller` modules.

This lets us split configuration into logical files — one per project group — without writing any glue code. The dispatch role handles the merge and the module calls.

## Target playbook (04-aap-config.yml)

The current `04-aap-config.yml` uses one task block per resource type (users, credentials, inventories, projects, JTs, schedules, EDA). The target state replaces all of that with:

```yaml
- name: Configure new AAP instance (config-as-code)
  hosts: localhost
  connection: local
  gather_facts: false
  vars_files:
    - ../myvars
    - vars/main.yml
  vars:
    dispatch_include_wildcard_vars: true
    aap_hostname: "https://{{ vm_name }}.{{ vault_domain }}"
    aap_username: admin
    aap_password: "{{ aap_gateway_admin_passwd }}"
    aap_validate_certs: false
  roles:
    - infra.aap_configuration.dispatch
```

The CaC variable files are loaded via `vars_files` or `include_vars` — the dispatch role picks up all suffixed variables automatically.

## CaC file layout

```
cac/
    base.yml                  # shared resources (org, users, credentials, EEs, inventories, hosts, projects, labels)
    selfhealing.yml           # AIOps self-healing demo JTs + EDA          (complete)
    simroi.yml                # simulated ROI dashboard JTs + schedules    (complete)
    orchestrator_deploy.yml   # Automation Orchestrator JTs                (complete)
    autodeploy.yml            # autodeploy pipeline JTs (01-04 + destroy)  (complete)
    servicenow.yml            # ServiceNow ITSM integration               (skeleton)
    config_exceptions.yml     # configuration drift detection              (skeleton)
    intelligent_assistant.yml # Intelligent Assistant                      (skeleton)
    base.yml.example          # template for shared resources
    project.yml.example       # template for per-project files
```

Files are currently in `~/claude-wd/cac/` (outside the repo). They'll be vault-encrypted and committed once secrets are filled in.

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

### base.yml (shared)
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

CaC files use `CHANGEME` as placeholder for all secrets. The migration workflow:

1. Fill in cleartext values in the CaC files
2. Back up secrets to Bitwarden
3. Vault-encrypt the files (or use inline `!vault` per-value)
4. Commit encrypted files to the repo
