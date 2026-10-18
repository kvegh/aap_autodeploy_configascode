# AAP AutoDeploy and Configuration as Code

Deploy fresh Ansible Automation Platform instances and configure them for demos.
The intended flow is to select a demo, deploy AAP, apply shared configuration
plus that demo's configuration, and verify the result.

The project provides reusable automation and CaC templates for other operators.
Populated shared and demo configuration is maintained in a separate private
repository as Vault-encrypted files.

## Current implementation

The repository contains four separate Ansible stages:

| Stage | Playbook | Purpose |
|---|---|---|
| 01 | `01-linux-vm-setup.yml` | Clone a prepared golden image and discover the VM address. |
| 02 | `02-infra-config.yml` | Configure DNS, certificates, and the reverse proxy. |
| 03 | `03-aap-install.yml` | Prepare the VM and run the pre-staged AAP installer. |
| 04 | `04-aap-config.yml` | Apply the subscription manifest, then shared CaC through `infra.aap_configuration.dispatch`. |

Post-install configuration uses the `dispatch` role from the
[Red Hat Communities of Practice AAP Configuration Collection](https://github.com/redhat-cop/infra.aap_configuration#readme).
It reads our CaC definitions and calls AAP APIs to create or update those objects.

Stage 04 downloads the private configuration repository's `main` branch into a
temporary directory, decrypts `cac/base_CaC_vault.yml`, and loads it before dispatch.
It also decrypts `cac/manifest.zip.vault` into a temporary ZIP and applies the AAP
subscription through `ansible.controller.license` before dispatch. The module's
`force: false` preserves an existing non-trial license on reruns. A failed import
stops configuration. A per-run Gateway token authenticates the subscription
import and dispatch. It is revoked afterward, and the temporary checkout, ZIP,
and authentication helper are removed after successful runs and ordinary task
failures. Ansible role-loading errors or interruptions can prevent cleanup.
Selectable demo profiles and automatic
handoff remain planned. Full deployment with the current dispatch configuration
has not been verified since the repository split.
Live Step 04 testing has verified private Git access, decryption, installer
password retrieval, Gateway token creation, and subscription import. Configuration
then stopped because dispatch selected a legacy Controller application role whose
module is absent from the installed Controller collection. Step 04 now excludes
`controller_applications`; application configuration remains handled by
`gateway_applications`. Full configuration verification remains pending.

The separate `restore-windows-config.yml` applies a supplied Windows CaC file
to an existing AAP. `destroy-test-aap.yml` handles guarded test-instance teardown.

## Setup and secrets

Use an execution environment with Ansible and the required collections, including
`infra.aap_configuration`, `ansible.controller`, `redhat.rhel_system_roles`, and
`community.general`. Verify the dispatch role's dependencies in that environment.
`collections/requirements.yml` pins `infra.aap_configuration` to `4.10.0`.
With collection downloads enabled, AAP installs it and its declared dependencies
during project synchronization. The requirements file defines which collections
are needed; Galaxy credentials attached to the project's organization define
where AAP downloads them. To use private Automation Hub's `validated` repository,
attach a Galaxy credential for that repository to the organization. Configured
sources must also provide the certified
`ansible.platform`, `ansible.hub`, `ansible.controller`, and `ansible.eda`
dependencies. This does not install Python or system packages into the execution
environment.

The target infrastructure needs the prepared golden image, installer bundle,
virtualization tools, and the DNS/certificate/proxy prerequisites described in
[documentation.md](documentation.md) and [PLAN.md](PLAN.md).

Environment access values remain encrypted in `myvars`. Shared AAP objects and
their credential inputs are encrypted in the private configuration repository's
`cac/base_CaC_vault.yml`. Supply the appropriate Ansible Vault password through a
local password file or an AAP Vault credential.
Each operator must prepare configuration for their own environment.

### Collection source policy

Project collection downloads must use private Automation Hub (PAH). Direct
public Ansible Galaxy access is not recommended; do not attach it to the
project's organization as a download source or fallback. Sync every required
certified, validated, and community collection, including its dependencies,
into PAH before synchronizing the project. Community content follows the same
policy: public Galaxy may be an upstream source for a PAH sync, while projects
download the curated content from PAH.

Attach credentials for the required PAH repositories to the project's
organization, preserving the intended source order. Keep tokens encrypted in
CaC and provide them before project synchronization; job 04 cannot configure
the sources it needs to download its own dependencies. A platform-managed
public Galaxy credential may remain as an unattached object if AAP prevents
its deletion. Verify that it is absent from the organization's active sources.

### Stage 04 inputs

Supply `aap_hostname` as the full HTTPS URL of the target AAP. Use an internal
hostname that resolves to the internal IP, or the internal IP itself, to keep
configuration traffic on the internal network. The execution environment must
be able to reach that address. Stage 04 requires this explicit URL and has no
fallback based on `vm_name` or `vault_domain`; it does not require `vm_name`
or `vm_ip`.

Supply `aap_config_repo_url` as the HTTPS Git URL of the private configuration
repository. Stage 04 always uses `main`; it requires these Vault-encrypted files:

- `cac/base_CaC_vault.yml`: the shared YAML configuration.
- `cac/manifest.zip.vault`: the complete subscription manifest ZIP, encrypted as
  a whole file. Keep the original archive intact before encrypting it.

Use a read-only token with access to that repository.
Do not put the token in the URL or extra variables.

Attach these credentials to the Stage 04 job template:

- A custom Git credential that injects the token as `CAC_GIT_TOKEN` in the job
  environment. Git reads it through a temporary askpass helper; it is not embedded
  in command arguments or written into the checkout's Git configuration.
- A Vault credential with identifier `cac` and the private configuration's password.
- The existing Vault credential that decrypts `myvars`, using its original/default
  identifier. `myvars` still supplies environment settings and installer SSH access.

AAP supplies the attached Vault passwords to Ansible at launch. `include_vars`
decrypts the shared YAML and `copy` with `decrypt: true` restores the manifest ZIP
with mode `0600` inside the job's private temporary directory. Both use the same
`cac` Vault credential; the playbook does not retrieve its password through AAP's
API or require it in extra variables. The license module uploads the restored ZIP
to the target AAP before the dispatch role applies object configuration.

For a freshly installed target, Step 04 connects over SSH to the hostname or IP
in `aap_hostname`, using `vault_ansible_user` and `vault_ansible_password` from
`myvars`, with sudo access. It reads only `gateway_admin_password` from the
installer inventory at the bundle path defined by `installer_extract_dir` and
`aap_version`. It no longer assumes that `aap_gateway_admin_passwd` matches this
target. For an existing target, supply its current `aap_password` through
encrypted configuration to skip SSH/installer access. `aap_username` defaults
to the administrator account and may be overridden.

Step 04 creates a write-scope token through `/api/gateway/v1/tokens/` using the
current Gateway login. The Controller license module and dispatch then use
Bearer-token authentication. Dispatch runs inside the cleanup block so the
token remains valid until configuration ends. Cleanup revokes the token after
success or an ordinary task failure and removes the workspace even if revocation
fails. Fatal role-loading errors or interruptions can skip Ansible's cleanup;
such runs require checking for a leftover token.

For AAP 2.7, dispatch excludes the legacy `controller_applications` role because
`ansible.controller` 4.8.11 does not contain its application module. Dispatch's
`gateway_applications` role applies `aap_applications` through `ansible.platform`.
Other Controller configuration roles remain enabled.

The execution environment must provide `ansible.controller.license` and Git,
and trust the repository server's TLS certificate. HTTPS redirects and stored
Git credential helpers are disabled for this download. Submodules are not
fetched. Git servers must accept token authentication using the `x-access-token`
username, as GitHub does.

### Step 04 debug logging

`debug_logging` defaults to `false` in both the playbook and its Job Template.
An optional true/false survey can override that default for a launch. Boolean
values and the survey strings `true` and `false` are accepted; other inputs fail
playbook validation. With the multiple-choice survey enabled, API launches must
send `debug_logging` as the quoted string `"true"` or `"false"`, matching the
survey choices; the playbook converts it to a Boolean. The meaning is consistent:
`false` enables `no_log`, while `true`
disables it for troubleshooting. The same inverse value controls the dispatch
collection's `aap_configuration_secure_logging` setting.

Enabling debug logging can expose decrypted configuration and other sensitive
data in AAP job output. Use it deliberately for troubleshooting; leave the
saved default at `false`. This control currently applies only to Step 04.

Stage 03 still uses `vm_name` and `vault_domain` to form the installer's fully
qualified hostname. That hostname can resolve internally; Stage 04's explicit
API URL determines how the configuration job connects.

Rotating the target administrator password, removing the remaining `myvars`
dependency, and selecting demos are separate pending work.
Attaching the credentials and adding this loader do not establish that the full
Stage 04 job can successfully configure a target AAP.

Never commit plaintext secrets or sensitive environment-specific data, including
account names, hostnames, addresses, tokens, or keys. Vault-encrypted files/values
are allowed. Keep `vpf` and other Vault password files outside Git. Ignore rules
are a convenience; inspect staged files before committing.

## Start a CaC configuration

The checkout includes two plaintext examples with empty resource lists:

- [cac/base_CaC_vault.yml.example](cac/base_CaC_vault.yml.example): shared objects.
- [cac/project.yml.example](cac/project.yml.example): per-demo objects.

Copy them into an operator-owned working directory outside Git before filling in
actual values. The commented entries use generic placeholders; replace the empty
lists with your resource definitions. Give every per-demo variable the same
unique suffix, such as `controller_projects_DEMO_PLACEHOLDER`, and reference
dependencies by object name. Keep configuration authentication separate from the
credentials that demo jobs will use inside AAP.

Keep editable files such as `base.yml` and `DEMO_PLACEHOLDER.yml` in that
working directory. When a configuration is ready:

1. Create a separate Vault-encrypted copy using the local Vault password file.
2. Place that encrypted copy in the private configuration repository's `cac/`.
   Use `base_CaC_vault.yml` or `DEMO_PLACEHOLDER_CaC_vault.yml` as its name.
3. Verify the Vault header, successful decryption with the intended password,
   and equality with the working copy without displaying decrypted content.
4. Review staged files, then commit and push only the encrypted configuration.

Keep the editable working files and Vault password file outside Git. This public
repository's `cac/` retains the empty examples. Stage 04 loads the private shared
base automatically; selection and loading of additional demo files remain planned.

See [Configuration_as_Code.md](Configuration_as_Code.md) for variable naming,
resource types, and restore dependencies. Empty templates do not provision
resources and have not been tested as populated demo configurations against AAP.

## Version maintenance

`VERSION` tracks this project's source version independently of `aap_version`
in `vars/main.yml`, which selects the AAP installer.

The initial source baseline is `0.0.1`. After that baseline, increment the version
once for every commit, including documentation and decision-history commits:

```bash
# Fixes, documentation, history, and other non-feature changes:
python3 src/bump-version.py

# Features: increment minor and reset patch:
python3 src/bump-version.py --feature
```

The helper locates `VERSION` relative to its own project directory. It preserves
the major version and refuses invalid version text. It and its tests need only
Python 3's standard library; no dependency installation or build step is required.
Follow standard Python formatting with four-space indentation.

Update [RELEASE_NOTES.md](RELEASE_NOTES.md) for each version. Commit implementation
and relevant README changes together. Add the implementation commit ID to
[design_decisions_history.md](design_decisions_history.md) in a following
documentation commit when necessary; that commit also increments patch.
Use "Document" in documentation-only commit subjects and summaries.

For a requested release, push an annotated `v<VERSION>` tag on the commit whose
`VERSION` matches, then publish the matching GitHub release. A branch version
increment alone is not a published release. Release notes must state what was
verified and whether deployment was performed. Later documentation commits can
advance the branch beyond the released version.

## Validation

Run the local version-tool tests and whitespace check:

```bash
python3 -m unittest discover -s tests -v
git diff --check
```

These checks do not run Ansible jobs. Ansible syntax checks alone do not verify
Vault-file loading, authentication, dependency readiness, or successful deployment.
No standalone formatter or linter dependency is required for the version helper.

## Repository layout

- Root playbooks: deployment, configuration, and guarded teardown.
- `cac/`: empty plaintext examples; populated CaC lives in the private repository.
- `vars/`: generic defaults; `templates/`: reverse-proxy templates.
- `utils/`: existing controller-label utility.
- `src/`: version-maintenance helper; `tests/`: its command-line tests.
- `VERSION`, `RELEASE_NOTES.md`, and `AGENTS.md`: version and working rules.
- `documentation.md`, `Configuration_as_Code.md`, and `PLAN.md`: detailed notes,
  CaC reference, and original design; historical TODOs need reconciliation.
- `design_decisions_history.md`: documented decisions and implementation references.
