# AAP AutoDeploy and Configuration as Code: work plan

## Goal and current position

Build a replacement AAP from versioned configuration and encrypted secrets. It
must run the intended production tasks and be able to deploy another complete
AAP itself. We provide reusable automation/templates; our populated base and
use-case configurations live separately, encrypted in private repositories.

An existing trusted AAP supplies the initial Git-read token and CaC Vault
password. Base provisions that access on the replacement. Base owns platform
setup; each use case owns its projects, inventories, credentials, execution
environments, templates and workflows.

As of 20 October 2026, a fresh replacement has received base and all five
captured use cases: AIOps Self-Healing, Disconnected Windows, Automation
Orchestrator, Assistant Team and AutoDeploy. Independent configuration comparison
is complete. Imports prove that definitions were restored; functional tests,
complete production coverage and recursive deployment remain open.

This is the single project TODO list. See [README.md](README.md) for setup and
[design_decisions_history.md](design_decisions_history.md) for past decisions.
Protected comparison reports, exports and plaintext working files stay outside Git.

## TODO

### 1. Resolve the remaining configuration differences

Why: the comparison found settings whose intended behavior is not explicit in
CaC. Decide the desired behavior before changing captures; a difference alone
is not proof of a defect.

- [ ] **1.1 AutoDeploy interpreter:** decide how its localhost jobs select Python.
  Orchestrator's expression is fixed; AutoDeploy still omits the setting.
- [ ] **1.2 AutoDeploy project policy:** choose and declare source-cleaning,
  project timeout and default execution-environment settings.
- [ ] **1.3 AIOps OAuth policy:** review whether the application and its PKCE
  setting are needed, then capture the intended policy. No authentication
  failure was demonstrated by the comparison.
- [ ] **1.4 Image reproducibility:** decide where images need version/digest pins
  and build provenance. Matching mutable tags resolve to different contents.
- [ ] **1.5 Object ownership:** decide which additional users, teams, grants,
  SSO applications and installer-created access policies belong in CaC.

Goal: document each decision, update encrypted captures where needed and verify
those updates. Record intentional exclusions too.

### 2. Capture the remaining production use cases

Why: the five captured use cases do not represent every production task.

- [ ] **2.1 Intelligent Assistant/Lightspeed:** capture installer/service settings,
  provider credentials, database/service passwords and Gateway OAuth setup;
  independently verify a fresh rebuild.
- [ ] **2.2 ServiceNow ITSM and Configuration Exceptions:** complete the skeleton
  configurations and add dedicated importers.
- [ ] **2.3 Other production scope:** review ROI/simulation, portal and legacy/test
  objects. Capture required automation and document deliberate exclusions.

Goal: each included use case has owned objects, labels, permissions, secrets,
PAH requirements, dependencies and a verified importer. External services remain
explicit prerequisites; recreating those environments is later work.

### 3. Test that imported automation actually works

Why: successful configuration import does not prove the imported jobs work.

- [ ] **3.1 Windows compatibility:** resolve or verify the last audited mismatch
  between Chocolatey requirements (Core 2.18+) and the image (Core 2.16.19).
- [ ] **3.2 Test automation:** create post-deployment test playbooks/Job Templates
  for each use case, with clear prerequisites and expected results.
- [ ] **3.3 Run functional tests:** verify platform access/content supply and each
  demo's actual function. Separate AAP failures from external prerequisites and
  plan disruptive tests explicitly.

Goal: every included use case has a repeatable test and a verified result.

### 4. Prove full workflow and recursive deployment

Why: stages and imports succeeded individually; one complete workflow run and
use of the replacement as the next seed are not yet proven.

- [ ] **4.1 Full workflow:** deploy a fresh target through the complete workflow;
  verify artifact handoff, PAH preparation and all five parallel import branches.
- [ ] **4.2 Next generation:** use that replacement's imported workflow and
  credentials to deploy and configure another complete AAP.

Goal: a new AAP can reproduce itself. Recovery remains manual: rerun failed
stages with the same inputs, then run remaining stages. Relaunching the whole
workflow creates another instance. Automatic workflow recovery was dropped.

### 5. Verify safe reruns and credential preservation

Why: fresh bootstrap works; repeated imports must preserve working access.

- [ ] **5.1 Base rerun:** verify preservation of the four Git-read credentials,
  CaC Vault credential, PAH download tokens and recoverable MCP token.
- [ ] **5.2 Use-case reruns:** verify refreshed Windows and Assistant lifecycle
  definitions, inventory-scoped identity/grant and target-local token/CA bindings;
  verify AIOps token reuse and repeated application of the other importers.
- [ ] **5.3 Failure handling:** verify agreed cleanup/recovery cases without
  rotating working secrets or revoking tokens already saved for ongoing use.

Goal: repeatable configuration without lost access. Fresh presence/binding checks
are done; exports cannot establish equality of API-masked secret values.

### 6. Finish PAH requirements auditing and recurring curation

Why: use cases need compatible content; pruning needs evidence of what must stay.

- [ ] **6.1 Use-case requirements:** finish auditing each encrypted use-case
  component for collections, required versions, dependencies and EE compatibility.
  The combined AutoDeploy prerequisites already work; Windows and Assistant
  Team also expose the common per-use-case requirements schema.
- [ ] **6.2 Production audit:** verify project/playbook/EE sources, revisions,
  actual pins, dependency constraints and image provenance. A captured version
  alone is not evidence that a project requires it.
- [ ] **6.3 Recurring curation:** establish reviewed preview/apply operation and
  scheduling after the audit. Preserve each repository's newest installed release
  plus required pins/dependencies; determine upstream refresh needs separately.
  Use an external runner against an idle target, or implement safe own-job
  handling before adding a target-side curator template.

Goal: reliable content supply and controlled retention. Base policy and one-time
cleanup are done; recurring pruning is not enabled or authorized by that policy.
A collection appearing in multiple repositories is not itself a cleanup problem.

### 7. Make CaC change detection repeatable

Why: UI/API edits, such as a changed timeout, can disappear on rebuild.

- [ ] **7.1 Comparison process:** maintain the accepted ownership/dependency
  inventory, check Git revisions and compare normalized CoP/API exports with CaC.
  Detect additions, modifications, deletions and reassociations; review changes
  before updating encrypted files. Update secrets explicitly; exports mask them.
- [ ] **7.2 Audit-log catch-up, later:** use component audit checkpoints to find
  changed objects, then retrieve their current definitions and dependencies.
  Handle missing/expired records and keep periodic full comparisons for coverage.

Goal: reviewed changes reliably reach CaC. The initial full extraction/comparison
is done; the recurring process is not automated. Continue comparisons for now.

### 8. Save generated MCP connection details securely for clients

Why: each installation issues its own token. Clients need its recoverable value,
endpoint and trusted CA; API-masked credentials cannot return the value later.

- [ ] **8.1 Encrypted storage:** write whole-file Vault-encrypted per-instance
  connection files to the private base repository. Use opaque filenames and
  verify encryption before uploading.
- [ ] **8.2 Access/client setup:** provide separate repository-scoped Git write
  access, preserve read credentials, and decrypt only into protected local client
  configuration with certificate verification enabled.
- [ ] **8.3 Lifecycle:** define controlled rotation, revocation and recovery.

Goal: clients can securely recover access to any new AAP. Target-side MCP token
creation and root-owned recovery storage are already working.

### 9. Plan controlled production takeover

Why: a replacement must not run duplicate schedules or process events twice.

- [ ] Define and test transfer of schedules, EDA activations and other automatic
  triggers, including verification and rollback. Make external consumer/service
  changes explicit prerequisites.

Goal: automatic work can move safely to the replacement and back.

### 10. Make inputs and authentication reusable

Why: other operators need to run stages independently in their own environments.

- [ ] **10.1 Inputs:** standardize variable names, independent-stage parameters,
  template defaults, surveys, override precedence and Boolean handling. Prefer
  established collection input names where applicable.
- [ ] **10.2 Authentication:** remove Stage 04's remaining `myvars` dependency by
  making target login and required guest SSH/recovery access independently
  configurable; preserve installer bootstrap and protected MCP storage.
- [ ] **10.3 Naming/logging:** reconcile Vault/password names and logging controls.
  Use `debug_logging`: false protects ordinary output; true enables diagnostics.
  Credential and secret tasks remain protected in both modes.

Goal: usable standalone jobs without our naming scheme or environment file.
Explicit `aap_hostname`, Stage 04's debug survey and workflow handoff are done.

### 11. Write the complete operator guide and review the design

Why: a new operator needs a verified route from checkout to configured AAP.

- [ ] **11.1 Step-by-step guide:** cover prerequisites, templates, ownership,
  private repositories, seed credentials, Vault setup, subscription, base,
  later PAH preparation, job inputs, verification, updates/deletions and manual
  recovery. Test the instructions from a fresh checkout.
- [ ] **11.2 Guidance review:** assess this project against
  [Red Hat's Configuration as Code guidance](https://developers.redhat.com/articles/2025/05/27/how-start-configuration-code-ansible-instance).
  Review accounts/token lifecycle, content supply, export completeness, secrets,
  validation, drift/deletions and Git workflow. Account for the guide's different
  example versions/collection before applying advice to AAP 2.7.

Goal: understandable, tested instructions and documented design improvements.

### 12. Review historical cleanup candidates

Why: older notes mention empty duplicate credentials, temporary hosts/templates
and leftover test VMs. Old IDs/names do not establish current state or ownership.

- [ ] Recheck references/activity, identify genuinely obsolete objects and prepare
  a scoped cleanup. Keep sensitive candidate details outside Git. This task does
  not authorize destruction.

Goal: remove confirmed leftovers without disturbing active environments.

### 13. Back up secrets independently

Why: the first seed must be recoverable if AAP or private Git access is lost.

- [ ] Implement and verify the planned Bitwarden backup/recovery mechanism for
  bootstrap secrets and required credential inputs, without exposing values.

Goal: tested secret recovery independent of the running AAP. General Git backups
and external workspace recreation remain umbrella-project work.

## Done:

Implemented and verified to the extent stated below. Functional, rerun, workflow
and takeover checks remain in the open list above.

- [x] **Reusable source/configuration separation:** public automation and empty
  templates; private whole-file encrypted captures; plaintext working files and
  Vault passwords outside Git; separate base and use-case ownership.
- [x] **Fresh deployment stages:** VM, infrastructure, bundled install and base
  succeeded (jobs 2201, 2208, 2211, 2233), including subscription, private Git,
  decryption, temporary-token revocation and workspace cleanup.
- [x] **Administrator password management:** encrypted base sets the desired
  password and updates the installer record. Jobs 2125/2128 verified change and
  rerun; 2233 verified fresh setup after the PAH authentication-order fix.
- [x] **Replacement bootstrap credentials:** base creates four private Git-read
  credentials and the CaC Vault credential; fresh-target presence/bindings were
  checked. Recursive use and live rerun preservation remain open.
- [x] **Persistent MCP access:** base creates/verifies a target-local administrator
  token with write scope and a protected root-owned recovery copy. Fresh-target
  MCP access is verified; client export, reruns and rotation remain open.
- [x] **PAH base:** certified, validated and community sources, local download
  credentials and ordered organization attachments are verified. Base performs
  no synchronization; project downloads use PAH.
- [x] **PAH retention implementation:** encrypted base declares remote selection
  and repository snapshot limits; a separate preview/apply curator protects pins
  and dependencies. One-time cleanup reduced 263 releases to 16 across 15
  collections. Recurring operation still needs the audit above.
- [x] **Workflow/handoff implementation:** stages 01-05 feed five parallel imports
  using nonsecret VM/address/API URL artifacts. AutoDeploy restores that workflow
  too. Full-workflow and recursive live proofs remain open.
- [x] **Five use cases imported:** AIOps (2260), Windows (2248), Orchestrator (2246),
  Assistant Team (2262), AutoDeploy (2247). Windows follow-up 2270 added the managed
  update template, bringing Windows to 21 templates. Refreshed Assistant lifecycle
  definitions and target-local access are imported; runtime tests remain open.
- [x] **Orchestrator interpreter:** encrypted host definition preserves job-time
  selection. Import 2273 and an independent verified-HTTPS read confirmed that
  the literal expression is stored.
- [x] **Initial full comparison:** CoP exports and raw supported APIs from both
  instances were compared on 20 October 2026. Protected local evidence/report
  identifies gaps, intended differences and masked-secret limits. The Windows
  missing template and Gateway health-interval drift were resolved afterward.
- [x] **Independent targeting/diagnostics:** explicit `aap_hostname`, Stage 04 debug
  default/survey, manual stage retry and existing-installer observation are in
  place. Automatic workflow recovery was dropped.
