# AAP AutoDeploy and Configuration as Code

Deploy fresh Ansible Automation Platform instances and configure them for demos.
The intended flow is to select a demo, deploy AAP, apply shared configuration
plus that demo's configuration, and verify the result.

The project has two deliverables: reusable CaC templates for other operators,
and applicable, Vault-protected configuration for our shared resources and demos.
The generic templates and populated environment configuration remain distinct.

## Current implementation

The repository contains four separate Ansible stages:

| Stage | Playbook | Purpose |
|---|---|---|
| 01 | `01-linux-vm-setup.yml` | Clone a prepared golden image and discover the VM address. |
| 02 | `02-infra-config.yml` | Configure DNS, certificates, and the reverse proxy. |
| 03 | `03-aap-install.yml` | Prepare the VM and run the pre-staged AAP installer. |
| 04 | `04-aap-config.yml` | Apply shared CaC through `infra.aap_configuration.dispatch`. |

Stage 04 currently loads only `cac/base_CaC_vault.yml`; selectable demo profiles
and automatic handoff between stages remain planned. Full deployment with the
current dispatch configuration has not been verified since the repository split.
The latest handoff reports missing dispatch collection availability and a mismatch
between the installer password and the credentials Stage 04 uses. These require
verification and resolution before an unattended deployment.

The separate `restore-windows-config.yml` applies a supplied Windows CaC file
to an existing AAP. `destroy-test-aap.yml` handles guarded test-instance teardown.

## Setup and secrets

Use an execution environment with Ansible and the required collections, including
`infra.aap_configuration`, `ansible.controller`, `redhat.rhel_system_roles`, and
`community.general`. Verify the dispatch role's dependencies in that environment.
The target infrastructure needs the prepared golden image, installer bundle,
virtualization tools, and the DNS/certificate/proxy prerequisites described in
[documentation.md](documentation.md) and [PLAN.md](PLAN.md).

Environment access values are encrypted in `myvars`; shared AAP objects and their
credential inputs are encrypted in `cac/base_CaC_vault.yml`. Supply the appropriate
Ansible Vault password through a local password file or an AAP Vault credential.
Each operator must prepare configuration for their own environment.

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

Encrypt sensitive completed files using Ansible Vault before copying them into
`cac/` and staging them. Encrypted names follow `base_CaC_vault.yml` or
`DEMO_PLACEHOLDER_CaC_vault.yml`; plaintext examples retain `.example`.
The repository's existing encrypted base file is a captured configuration;
using the example lets an operator build their own shared configuration instead.
Adding a file under `cac/` does not automatically load it. Stage 04 must explicitly
load the chosen files; selectable demo loading remains outstanding.

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
- `cac/`: encrypted configuration and empty plaintext examples.
- `vars/`: generic defaults; `templates/`: reverse-proxy templates.
- `utils/`: existing controller-label utility.
- `src/`: version-maintenance helper; `tests/`: its command-line tests.
- `VERSION`, `RELEASE_NOTES.md`, and `AGENTS.md`: version and working rules.
- `documentation.md`, `Configuration_as_Code.md`, and `PLAN.md`: detailed notes,
  CaC reference, and original design; historical TODOs need reconciliation.
- `design_decisions_history.md`: documented decisions and implementation references.
