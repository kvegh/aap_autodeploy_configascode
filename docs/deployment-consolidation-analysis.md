# Proposed consolidation of AAP CaC importers

**Analysis only; not implemented.** Reviewed source: `8865506` (0.26.1),
2026-11-03. No AAP, VM, import, deployment or project-sync job was run.

## Decision

Yes: use **one generic CaC importer playbook for every project**, with a common
resource schema and explicit import/security policy. The five project importers
are not five fundamentally different deployment mechanisms. Much of their size
comes from copied checkout, validation, login and cleanup code, different variable
names, and workarounds for the currently pinned roles.

This does **not** mean concatenate them, introduce `when: project == ...`
branches, or dispatch arbitrary `include_tasks` paths from each secrets repo.
Normalize ordinary CaC into supported resource data. Use reusable resource-level
compatibility handling where demonstrated necessary. Keep secret materialization
and infrastructure preparation explicit when they are actually needed.

One playbook does not automatically mean one Job Template. AAP must inject the
selected repository's read credential and CaC Vault **before the job starts**.
The job cannot recover another credential's masked secret from the AAP API.
Several thin repository-bound templates can initially share the same playbook;
a single dynamically bound template needs the still-pending credential-selection
and RBAC design. Never attach all repository Vaults with identifier `cac` to one
job. Existing repository pairs remain valid; this proposal does not replace them.

The deployment runner/EE checks out public automation, fetches private CaC with
its own repository access, decrypts it, and sends configuration to the receiver's
verified APIs. The receiver does not need that Git/Vault pair merely to receive
configuration. Current base bootstrap deliberately provisions those pairs so the
replacement can later become a deployer. That is a separate capability, not an
intrinsic requirement of API import. Imported private SCM projects may separately
need their own Source Control credentials for their subsequent checkouts.

## Scope and classification

There are no literal `deploy_*project*yml` files. The relevant entry points are:

| Entry point | What it currently does | Consolidation disposition |
| --- | --- | --- |
| [deploy-aiops-demo.yml](../deploy-aiops-demo.yml#L76) | Imports Controller/EDA data, provisions a missing persistent target EDA credential, handles Event Streams/revision fields and activation state. | Replace the import shell with the generic importer. Keep necessary token lifecycle separate/reusable; normalize resource data and handle verified compatibility gaps. |
| [deploy-windows-demo.yml](../deploy-windows-demo.yml#L80) | Imports Windows definitions, optionally materializes target trust for an AD-related credential, stages inventory groups. | Same importer; optional trust preparation and general group-graph handling. No Windows application/patching job is run by this importer. |
| [deploy-orchestrator-demo.yml](../deploy-orchestrator-demo.yml#L78) | Validates a capture/registry inputs, then ordinary dispatch. | Direct generic-import candidate; registry credentials and literal interpreter expressions are data. |
| [deploy-assistant-team.yml](../deploy-assistant-team.yml#L159) | Imports ordinary definitions/ciphertext snapshots and provisions target-owned inventory service access. | Same importer; retain the real service-secret lifecycle as an explicit reusable capability/precondition. Authentication maintenance remains outside default import. |
| [deploy-autodeploy.yml](../deploy-autodeploy.yml#L26) | Maps a differently shaped capture into standard resource roles and builds a four-stage deployment workflow. | Normalize the capture and render the workflow as ordinary workflow CaC; no separate import engine is required. Creating its templates does not run provisioning/extraction. |
| [deploy-selected-use-cases.yml](../deploy-selected-use-cases.yml#L32) | Authenticates the seed and launches prerequisite/importer child jobs. | Orchestration, not a pure importer. Decide its replacement separately; do not hide these launches inside the generic import. |

The related [workflow entry point](../configure-deployment-workflow.yml#L7) and
[workflow builder](../tasks/deployment-workflow.yml#L30) configure definitions;
they do not run the workflow. Base Stage 04 and preparation Stage 05 establish
boundaries below; VM creation/install redesign is outside this analysis.

Categories used in the comparison:

- **A — CaC data:** resource definitions, names, schemas, references and desired settings.
- **B — generic import/security policy:** checkout, binding, validation, logging and outcome rules.
- **C — real secret/trust lifecycle:** target-owned material must be supplied or safely materialized.
- **D — verified compatibility/ordering issue:** a resource-level workaround, not a project identity.
- **E — beyond pure import:** server/content preparation, orchestration or workload execution.

## Detailed behavior comparison

| Current behavior and source evidence | Class | Necessity, risk and proposed treatment |
| --- | --- | --- |
| Four wrappers duplicate HTTPS Git checkout, askpass, Vault-header checking and `include_vars`: e.g. [AIOps 78–127](../deploy-aiops-demo.yml#L78), [Windows 82–157](../deploy-windows-demo.yml#L82). AutoDeploy already shares [checkout 2–92](../tasks/private-config-checkout.yml#L2). | B | Common code. Parameterize reviewed file/ref/root, not credentials in URLs. Keep private temporary storage, no Git redirects, protected failures and unconditional cleanup. |
| File locations, variable suffixes, readiness fields and hard-coded counts differ: [AIOps 129](../deploy-aiops-demo.yml#L129), [Windows 159](../deploy-windows-demo.yml#L159), [Assistant 159](../deploy-assistant-team.yml#L159), [AutoDeploy 31](../deploy-autodeploy.yml#L31). | A/B | They identify a capture, not a different importer. Convert to one versioned resource schema plus completeness/required-input validation. Do not make seven templates an invariant of every Assistant configuration. |
| Shared [instance selection](../tasks/aap-instance-select.yml#L2), [DNS/TLS API verification](../tasks/aap-instance-api.yml#L2) and [SSH jump trust](../tasks/aap-instance-ssh.yml#L2). | B/E | Keep identity and TLS checks. Registry-only/fresh-VM assumptions are current constraints, not requirements of CaC API calls. Do not simply remove them: implement the owner's agreed inventory/credential contract later, while leaving VM/recovery safeguards intact. |
| Installer password reads occur **only when `aap_password` is undefined** in [AIOps 211–247](../deploy-aiops-demo.yml#L211), [Windows 198](../deploy-windows-demo.yml#L198), [Orchestrator 202](../deploy-orchestrator-demo.yml#L202), [Assistant 244](../deploy-assistant-team.yml#L244). AutoDeploy's [shared login](../tasks/gateway-base-login.yml#L11) also falls back after configured login returns 401. | B/C | This is legacy authentication bootstrap, not project CaC preparation. A selected, valid destination API credential removes this reason for SSH. That credential decision remains open; do not silently retain installer password scraping in the proposed pure API path. |
| AIOps password read/fact tasks make `no_log` conditional on diagnostics: [211–247](../deploy-aiops-demo.yml#L211); the [Orchestrator equivalent](../deploy-orchestrator-demo.yml#L202) is always protected. | B | Logging policy is inconsistent. If that AIOps fallback runs with diagnostics enabled, the password can reach task output. No such job was executed in this analysis. The common path must protect secret-bearing operations unconditionally and provide separate sanitized diagnostics; parent `bead-wd-72f` tracks this policy. |
| Temporary Gateway token creation/use/deletion: [AIOps 249–269, 475](../deploy-aiops-demo.yml#L249), other wrappers, [shared cleanup](../tasks/private-config-cleanup.yml#L2). | B | One authentication/cleanup implementation. Native token creation exists, but creates a new token per call. Revoke only tokens created by this run, never a borrowed destination credential or a persisted service token. Keep seed and receiver contexts separate. |
| Label coverage and survey validation use [cac-template-labels.yml 2–69](../tasks/cac-template-labels.yml#L2). | A/B | Reusable validation with bundle ownership/label data. Preserve string multiselect defaults and bounded prompts. Do not infer ownership of all AAP object types from labels: many kinds do not expose labels. |
| Wildcard merge and dispatch: [Windows 263](../deploy-windows-demo.yml#L263), [Orchestrator 262](../deploy-orchestrator-demo.yml#L262); AutoDeploy's [manual mapping](../tasks/autodeploy-config.yml#L2). | A/B | Normalize into canonical CoP variables and apply only that bundle. Loading shared authentication/base variables must not accidentally make them importable resources. Prefer namespaced loading and explicit resource assignment; do not wildcard-merge unrelated bundles or retain facts between imports. |
| Literal injector/interpreter Jinja versus intended input interpolation; [protected YAML writer](../src/cac_yaml.py#L1), [Orchestrator regression](../tests/test_orchestrator_config.py#L26). | B | Preserve `!unsafe` and ordinary bindings distinctly, including through encryption/roundtrip. Equal strings do not prove equal templating behavior. Never globally mark every input literal or eagerly evaluate controller/runtime templates. |
| AIOps validates and creates a persistent Controller bearer only for a missing target EDA credential, saves it, excludes it from ordinary dispatch: [271–388](../deploy-aiops-demo.yml#L271). | C/B | Genuine lifecycle under the current runtime contract; a captured seed token is not portable to another receiver. Native roles can store supplied credentials/tokens but do not perform discovery, mint-once, binding verification and recovery. A reusable token/credential capability or pre-materialized target credential can replace project-specific control flow. |
| AIOps orphan-token cleanup checks whether the persistent credential was saved; on an inconclusive check it preserves the token: [439–472](../deploy-aiops-demo.yml#L439). | B/C | Keep this distinction. A generic `always: delete all tokens` would break runtime access. Verify identity, host, owner/purpose and durable persistence; never rotate merely because API output masks the secret. |
| Manual Event Stream pass: [408–421](../deploy-aiops-demo.yml#L408). | A/D | **Not inherently a custom AIOps operation.** Installed dispatch already orders Event Streams before activations. Normalize captured `organization_name` to the role's `organization`; the native module accepts that alias. `event_stream_type` is unused/deprecated in the inspected module. Use the existing role after normalization rather than retain a duplicate pass. |
| EDA project revision post-pass: [394–406](../deploy-aiops-demo.yml#L394). | D | Real pinned-role field gap: the native module supports both fields, but the CoP role omits them. Its native defaults are false/zero, so role-then-restore can reset settings on each rerun. A generic EDA-project handler must forward correct settings in the **first** application, or use a verified fixed role; do not keep the reset/post-patch pattern. |
| AIOps forces `state: present, enabled: false` every import: [423–430](../deploy-aiops-demo.yml#L423). | B/D/E | Fresh-import intent is no execution, but this is not a safe universal update policy and the inspected module has a concrete compatibility issue (below). Preserve existing enabled/disabled state by explicit policy and do not restart active workloads without approval. New activations must be demonstrably disabled. |
| Windows secret requirements are a list; optional AD credential receives target CA/SSH public-key material: [178–238](../deploy-windows-demo.yml#L178), [windows-ad-target.yml](../tasks/windows-ad-target.yml#L2). | A/C | Static secret inputs and resulting credential schema are ordinary CaC. Authentic trust material must come from somewhere; current helper gathers it over trusted installer SSH. A protected infrastructure output/trust credential can supply it instead. No inherent requirement for Windows-specific import code or for generic API imports to gather SSH facts. |
| Windows excludes group role from initial dispatch and creates all groups before linking memberships: [exclusion](../deploy-windows-demo.yml#L12), [277–293](../deploy-windows-demo.yml#L277). | D | General dependency graph issue. The pinned role starts all items asynchronously and resolves children inside each call. Implement a reusable skeleton/relationship barrier or a verified ordered handler; list sorting alone does not eliminate the async race. Respect existing membership preservation and explicit deletion policy. |
| Assistant's six embedded environment/authentication snapshots remain whole-file encrypted: [207–234](../deploy-assistant-team.yml#L207). | A/B | Custom credential type/inputs are supported data. Envelope validation is generic. Importing these snapshots does not log into model providers, refresh authentication, restore guest files, prove entitlement, or run the application; keep those operations separate. |
| Assistant service user, dedicated inventory, role and compatible credential type are applied and validated before granting access: [lifecycle 11–258](../tasks/assistant-team-lifecycle.yml#L11). | A/B/C | Resource definitions are ordinary CoP data. Collision/RBAC/password-preservation checks are reusable security policy. Their ordering matters. The implementation deliberately omits an existing authenticated user's password on metadata updates, not merely `update_secrets: false`. |
| Assistant mints/reuses a target service bearer with private atomic recovery storage and credential fingerprint: [lifecycle 260–311](../tasks/assistant-team-lifecycle.yml#L260), [module 179–269](../library/assistant_lifecycle_token.py#L179). | C/E | The recoverable target-owned secret is a real requirement of the current lifecycle contract. Root-owned target storage/SSH is this implementation's storage choice, not intrinsic to importing AAP objects. Retain the lifecycle separately or supply an equivalently verified secret-store output; native token creation alone is insufficient. Do not copy a seed bearer or silently rotate lost/expired access. |
| Assistant excludes optional authentication maintenance and requires the ordinary capture; [159–180](../deploy-assistant-team.yml#L159), [236–242](../deploy-assistant-team.yml#L236). | A/B | Bundle scope and deny-execution policy. The generic importer should not add maintenance/app jobs just because they exist in the repo. Their definitions may be separately selected data; their execution is separate. |
| Orchestrator validates registry inputs then dispatches: [181–274](../deploy-orchestrator-demo.yml#L181). | A/B | No imperative project-specific target URL substitution is present. Read-only capture inspection found only registry input references and literal `ansible_playbook_python` expressions. Preserve intentional data bindings; no Orchestrator-only handler is justified by this code. |
| AutoDeploy restores types, credentials, EEs, inventories, hosts/groups, labels, project and JTs: [autodeploy-config.yml 2–66](../tasks/autodeploy-config.yml#L2). | A | These are the same resource roles used by dispatch. Adapt its nested capture schema rather than preserve another engine. Included extraction JT/type schemas are definitions; importing them neither extracts nor updates a repository. |
| AutoDeploy builds a four-stage workflow from a template: [builder 30–65](../tasks/deployment-workflow.yml#L30), [node data](../templates/deployment-workflow-nodes.yml.j2#L2). | A | Native workflow role/module already support graph data, surveys and edges. Move the graph into normal workflow CaC with controlled bindings. Workflow configuration can share the importer; running VM creation/install remains outside it. Define node/edge replacement policy instead of assuming omitted nodes are deleted. |
| Stage 04 imports subscription/base settings, persistent PAH access, bootstrap pairs and MCP access: [04 166–243](../04-aap-config.yml#L166). | A/C/E | Ordinary base resources can use the common engine, but fresh-platform bootstrap and persistent-secret provisioning remain explicit stages. Five repository pairs provide future-deployer capability; do not make them prerequisites for every receiver. Do not fold licensing, administrator/installer file changes or MCP provisioning invisibly into every project import. |
| Stage 05 synchronizes exact PAH content and copies an image into Controller's runtime store: [05 24–45](../05-prepare-use-cases.yml#L24), [prerequisites 17–95](../tasks/use-case-prerequisites.yml#L17). | A/D/E | Requirements are data; actual content synchronization/container loading is environment preparation. Hub modules already perform sync; existing batch/policy/restoration handling is a reusable compatibility concern. Keep preparation explicit and complete before dependent project synchronization. |
| Selector checks fixed importer identities/surveys/credentials and launches preparation plus children: [selector 100–259](../deploy-selected-use-cases.yml#L100), [launch/wait 13–57](../tasks/selected-use-case-import.yml#L13). | B/E | Keep bounded credential/target binding and real completion checks. Whether to retain this legacy child-job orchestration or replace it with an explicit native workflow is a pending owner decision. A pure importer must not secretly invoke the old project importers. |
| Windows/Orchestrator/Assistant explicitly reject all launch/schedule variables; AIOps relies on capture content and selected role exclusions: [Windows 190](../deploy-windows-demo.yml#L190), [AIOps 12](../deploy-aiops-demo.yml#L12). | A/B/E | Disabled schedule definitions are CaC data and can fit a generic importer; the present blanket rejection is a current constraint. Launching jobs, restarting/enabling activations and creating/enabling active schedules need explicit execution policy. Agree that policy before broadening support. `dispatch` includes launch roles when their variables exist; a descriptive `definitions_only` flag is not an existing CoP safeguard. |

## What the installed content actually supports

Primary evidence is the installed source, not a prediction about a newer release.
The reviewed artifact root is `tools/aap-cac-export/collections/ansible_collections`
in the workspace. Vendor paths below are relative to that root and include the
entry line; `.../roles/` abbreviates `infra/aap_configuration/roles/`.
Local manifests report:

| Collection | Observed local version | Pin qualification |
| --- | --- | --- |
| `infra.aap_configuration` | 4.10.0 | Explicit project requirement; exact reviewed role code. |
| `community.general` | 11.4.0 required by project | Explicit requirement; not relevant to the role gaps below. |
| `ansible.platform` | 2.7.20260930 | Observed installed dependency, not separately locked by this project's requirements. |
| `ansible.controller` | 4.8.11 | Same qualification. |
| `ansible.hub` | 1.1.2 | Same qualification. |
| `ansible.eda` | 2.13.0 | Same qualification; do not assume this proves every live EE resolves the same version. |

See [collections/requirements.yml](../collections/requirements.yml#L1).
The implementation phase must attest the actual project/EE dependency set or
lock it appropriately; this analysis installs or upgrades nothing.

| Verified source | Consequence |
| --- | --- |
| `infra/aap_configuration/roles/dispatch/defaults/main.yml:315` and `tasks/main.yml:7` | EDA order is projects → Event Streams → decision environments → activations; roles execute only for defined resource variables. Dispatch aggregates asynchronous errors and fails at `tasks/main.yml:23`. |
| `.../roles/eda_event_streams/tasks/main.yml:9`; `ansible/eda/plugins/modules/event_stream.py:177` | Role supports name/credential/organization/headers/forwarding/state. Native `organization` alias resolves `organization_name`; `event_stream_type` is unused/deprecated. This is a schema adapter opportunity, not absence of Event Stream support. |
| `.../roles/eda_projects/tasks/main.yml:9`; `ansible/eda/plugins/modules/project.py:235,363` | Role omits revision-on-launch/cache timeout. Native module accepts them with defaults false/zero and includes those values in requested project state. Use a complete generic resource call, not a resetting role plus repair call. |
| `.../roles/eda_rulebook_activations/tasks/main.yml:27`; `ansible/eda/plugins/modules/rulebook_activation.py:502,547,659` | Role forwards activation mappings/state/enabled, but native behavior is version-sensitive. The inspected module derives `is_enabled` from `state`; see blocker below. Merely omitting `enabled` does not establish preservation. |
| `.../roles/controller_host_groups/tasks/main.yml:7,32,44` | Native group module supports links and preservation flags; the role launches items before its collection barrier. Graph staging is generic. |
| `.../roles/controller_workflow_job_templates/tasks/main.yml:27,52` | Workflow graphs/surveys/edges are already accepted data; no separate AutoDeploy graph-creation engine is necessary. |
| `ansible/platform/plugins/modules/token.py:18–26` | Native Gateway token module exists, returns a new bearer once, and explicitly documents non-idempotent creation. It can replace raw HTTP transport, not persistent-token discovery/recovery policy. |
| `.../roles/eda_controller_tokens/tasks/main.yml:9` | Stores a caller-supplied Controller token through `ansible.eda.controller_token`; it does not mint the Gateway bearer required by the current EDA credential lifecycle. |
| `.../roles/gateway_users/tasks/main.yml:17`; `ansible/platform/plugins/module_utils/aap_module.py:540,726` | `update_secrets: false` affects change detection; another metadata change can still send the full supplied update. Preserve existing write-only fields by intentional omission/provenance checks, not an unverified blanket promise. |
| `.../roles/controller_projects/tasks/main.yml:19–32`; [Hub sync call](../tasks/use-case-pah-sync.yml#L20) | SCM auth, cache/update flags and explicit Hub synchronization are supported. Import policy must declare permitted sync effects and wait for required completion; project/content preparation is not a reason for project-specific API importers. |

### Concrete activation compatibility blocker

An offline call to the inspected `ansible.eda` 2.13.0 `create_params` function,
using synthetic inputs and stub lookups (zero API calls), produced:

| Input | Generated API field |
| --- | --- |
| `state: present`, `enabled: false` | `is_enabled: true` |
| `state: disabled`, `enabled: false` | `is_enabled: false` |

The current AIOps source uses the first combination. This does **not** prove any
live activation changed: no import was run and the live resolved dependency set
was not attested here. It does mean a later importer must not rely on the current
Boolean override as a verified no-execution guarantee. Confirm the actual module
version and test the policy before any migration/import. In this module explicit
`state: disabled` on an existing activation takes a state-change/early-return
path, so it is also not a substitute for applying all definition fields in one
call. CoP's `global_vars/defaults/main.yml:13–18` recognizes both enabled and
disabled operations, so there is no missing operation label that prevents using
the native state vocabulary. State-preserving update sequencing still needs a
full role/module test. This separate compatibility work is tracked as
`bead-wd-72f.4`; no fix is implemented here.

## Proposed minimal interface and sequencing

The proposal separates a trusted catalog, a generic resource bundle, and injected
credentials. This is an illustrative schema, **not an accepted current format**:

```yaml
# Reviewed launcher/catalog data, not arbitrary survey paths or secret values.
cac_import_catalog:
  project_key:
    repository: https://git.example.invalid/team/project-secrets.git
    revision: REVIEWED_REF
    files: [cac/project_vault.yml]
    resource_root: cac_resources
    git_credential: project-secrets CaC repo read token
    vault_credential: project-secrets CaC vault cred

# One job request; destination API credential is bound before launch.
cac_import_request:
  project: project_key
  destination: INVENTORY_INSTANCE_NAME

# Inside the selected encrypted bundle: existing CoP resource schemas.
cac_resources:
  controller_projects: []
  controller_inventories: []
  controller_groups: []
  controller_templates: []
  controller_workflows: []
  eda_projects: []
  eda_event_streams: []
  eda_rulebook_activations: []
```

The resource vocabulary extends to **all supported AAP resource kinds**, not an
allowlist of five project names. New projects conforming to that schema need
only catalog/data and credential bindings. Unknown resource kinds/fields must
fail clearly until supported; supporting all projects does not mean pretending
all possible AAP fields or server tasks are already covered.

1. Resolve a reviewed project entry and the destination name. The owner's intended
   inventory `ansible_fqdn` lookup and self/remote API credential policy are still
   pending under `bead-wd-72f`; current registry guards remain implemented.
2. Before launching the importer, bind exactly one repository read/Vault pair and
   the selected destination API credential. Validate credential purpose/RBAC and
   source-versus-receiver identity. Do not fetch masked credentials by name after
   startup, or send the source bearer to another receiver.
3. In the source EE, fetch the fixed file set/ref, verify encryption, load under a
   private namespace, validate schema/completeness/ownership/literal templates,
   then resolve only declared destination bindings. Do not load authentication
   base variables into an ambient wildcard resource merge.
4. Validate requested resources and side effects before applying them. The
   recommended no-workload-execution policy rejects job launch roles and activation
   restarts; new activations must be disabled and existing activity state preserved
   unless explicitly authorized. Disabled schedule definitions remain eligible CaC
   data. Active/enabling schedule policy needs explicit agreement before replacing
   the current blanket schedule rejection. Unknown/deleting objects and graph-edge
   removal need ownership/impact review. Report controller-managed SCM
   synchronization and waits honestly.
5. Apply ordinary resource data through CoP/native modules in dependency order.
   Add only demonstrated **resource-level** compatibility handling: complete EDA
   project fields and a group graph barrier, for example. Preserve omitted fields
   rather than silently enforcing defaults; collect and fail real async errors.
6. Where genuinely needed, use explicit, trusted capability steps or preconditions
   for target trust or durable service credentials. Prefer separate preparation
   stages around foundation/dependent resource imports. Do not embed arbitrary
   repository task paths or project-key branches. If a runtime contract needs a
   token factory, removing its code requires an equivalent verified provider;
   moving it behind `include_tasks: project_name` is not consolidation.
7. Verify resulting identities/bindings and actual resource outcomes. Revoke only
   run-owned temporary/orphan tokens proven safe to revoke; retain borrowed and
   persisted credentials. Clean the private workspace on every exit. Secret reads,
   merges, token results and failures stay under `no_log` even with diagnostics.

These policies would be enforced by the proposed importer; they are not magic
CoP fields that can be added to today's data and assumed effective. A separate
plan/dry-run mode is an optional future enhancement, not a consolidation
prerequisite: CoP does not automatically provide a complete planner, and each
module's check-mode/diff coverage would need verification.
A thin repository-specific JT sharing this playbook is a safe interim binding
mechanism. The owner still needs to choose the final single-JT/native-workflow
credential-selection model and whether to remove the legacy selector's hidden
child-job pattern.

An alternative source layout could use each private CaC repository as an AAP SCM
project with a built-in Source Control credential and a tiny entry point importing
a common public collection. The Vault credential then decrypts already checked-out
files, without a runtime Git-token injector for that checkout. This is a different
packaging/layout, potentially more projects/templates, **not a drop-in change**.
The current `Cac_git_token_type`/`CAC_GIT_TOKEN` pattern remains valid and is not
being removed or renamed by this proposal.

## Migration, self-targeting and required regressions

The five import wrappers can disappear after schema normalization, capability
separation and equivalence tests. Keep thin aliases temporarily if needed for
existing JT/workflow references; migrate their playbook/survey/credential pins
explicitly. The workflow configurator can become a data profile. Stage 05,
selected-use-case orchestration, VM deployment, application jobs, authentication
refresh and extraction/repository updates stay outside the pure importer.
Base may later reuse its API resource engine without losing its separate platform
bootstrap/secret-lifecycle stages. No refactor is authorized by this analysis.

Self-targeting is legitimate API use, not permission to remove every fresh-target
guard. For the proposed importer, verify the selected identity and deliberate
self/remote intent, existing ownership/RBAC, active jobs and activity state. Do not
use the current selector's blanket distinct-UUID rule as the generic policy, and
do not weaken new-VM/hypervisor recovery guards. Updating the importer's own
project/template/credentials requires safe ordering so the current job remains
authenticated and later launches remain usable.

Required later regressions, reusing existing tests where useful:

- Every current project plus a sixth data-only project follows the same driver;
  equivalent normalized resources result without per-project branches.
- Repository pair isolation, exact source pins, separate destination API auth,
  one `cac` Vault per child, denied cross-repo/host credentials and no source-token
  forwarding. Cover both native templating modes and `!unsafe` roundtrips.
- Fresh, existing and deliberate self-target imports; preserve existing secrets,
  account passwords and activity state during unrelated metadata changes. Reject
  ambiguous identity, wrong organization/type and masked new secrets.
- Persistent service token first creation/rerun, expired/lost copies, duplicate
  concurrent creation, interrupted save and inconclusive readback. Preserve
  recoverable access and revoke only proven unsaved run-owned tokens.
- Nested groups on empty and populated targets; preserve configured membership
  semantics and explicitly test cycle/deletion policy. EDA schema aliasing and
  project revision/cache settings must apply correctly without reset-then-restore.
- Resolve actual EDA module versions (`bead-wd-72f.4`); prove new activations stay disabled and
  existing enabled/disabled activations remain unchanged. Test definition updates
  separately from state transitions; assert no launch, restart or active schedule.
- Workflow nodes/edges/surveys and precise replacement semantics; verify project
  sync/preparation failures and async role errors fail the overall import.
- Safe checkout/error cleanup and secret canaries under diagnostic/failure paths.
  No model auth refresh, VM provisioning, application work or repository extraction
  is accidentally executed by importing their definitions.

## Validation and open decisions

This analysis used local source/role/module reads, manifest checks, a read-only
Orchestrator capture inspection limited to template identifiers, and an offline
synthetic activation-parameter probe. It did not attest live EE dependency
resolution, execute importers, or prove a new generic implementation end to end.
All 61 document links resolve to existing source files/line numbers. The single
illustrative YAML block parses, and its eight resource variables match installed
dispatch vocabulary. Four existing version-policy tests pass, as does
`git diff --check`. These checks validate the documentation and offline evidence,
not a deployed importer.

Implementation blockers remain the owner's destination API credential/RBAC and
self-target contract, the orchestration choice, verified activation semantics,
and an agreed storage/provider for any still-required durable target secrets.
These are reasons to sequence the refactor carefully, not reasons to retain five
copies of the common CaC importer. Parent `bead-wd-72f` and future extraction/rekey
routing `bead-wd-72f.2` remain separate open work.
