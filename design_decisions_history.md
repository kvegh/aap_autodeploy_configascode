# Design decisions history

## Preserve blocked inputs in the recovery checkpoint — 2026-11-09

Implementation `96e5e29f19511441eb977eb9ef8757c8fd68924b` (0.49.8) refreshes
the existing public task mirror. Matching Hactar checkpoint
`a8681163134ef3432bafe7ac42ceaf3e3231903c` preserves 181 complete selected
records, all 180 previously exported IDs and all 258 comments under the existing
Vault scope and header. AutoDeploy lists 122 tasks; Hactar lists 80. The existing
exporters remain authoritative projections of Beads, not another task store.

The native firewall source consumers are published, but ordinary setup still
failed fetching its private configuration source. Authentication delivery is
therefore back in progress rather than complete. The new fresh-instance Zabbix
ownership-publication decision remains blocked. Private input preparation and
publication do not establish successful source retrieval, host application,
MCP builds, fresh Command Center acceptance or readiness for the physical rebuild.

Both exporters' current-state checks, native Vault roundtrip/preservation,
nine AutoDeploy mirror tests, six Hactar mirror tests, four version-tool tests
and whitespace checks passed. The process diagrams, functional source and user
handover were unchanged. No live controller, guest, firewall, DNS or credential
operation was performed by this documentation checkpoint.

## Explain elapsed actions across the requested seven-day window — 2026-11-09

Implementation `ce594b99c587b99c9e2191fbf2ec50b001ee1608` (0.49.6) replaces
the accepted one-day pilot with the requested seven-day retrospective. Markdown
remains primary; its HTML companion presents the same 64 meaningful blocks in
nine compact diagrams. The 20 longest evidenced episodes have vivid rank bands,
numeric ranks and observed durations directly in their boxes.

The analysis distinguishes job runtime, elapsed calendar spans, documented
waits, rework and unknown attribution. Parallel spans are not summed, and the
longest browser-feedback wait is not described as continuous implementation or
a proven successor-deployment blocker. Visible narrative and existing project
history support the report; raw commands, transcripts and private reasoning do
not appear in the interface or repository.

The previous HTML used doubled digit escapes and a fixed expected node count.
Controls now derive their IDs from the actual diagrams/details. Root replay
passed all 64 click/keyboard/native-collapse paths and missing-runtime/control
cases; matching structure, privacy, GFM tables and pinned Mermaid grammar checks
passed. These are source/control-logic checks; actual browser layout and clicks
remain unverified. Native collapsible explanations remain usable without the
internet module.

## Wait for normal Controller project synchronization — 2026-11-09

Implementation `29f2a29470fceb088e42cce892bef2307245f68e` (0.49.4) fixes the
observed successor CaC import failure while creating its Controller project.
The exact pinned CoP 4.10 role allowed 50 one-second status polls. Protected
event metadata showed all 50 attempts were exhausted after 60.280 seconds;
the underlying project update continued and then succeeded in 67.684 seconds.
The importer's outer wait ended before the ordinary synchronization completed.

The existing dispatcher call now supplies the documented project-specific
180 retries and one-second delay. This retains bounded completion below the
role's existing 1000-second async module allowance without changing other
resource waits, secure logging or failure reporting. No second retry job,
reconciliation path, helper or polling service is added.

The focused test resolves the actual pinned collection's project defaults and
collector arguments, checks the selected wait and secure logging, and confirms
the wait remains below the existing async allowance. Strict scoped lint, Python
compilation and diff checks pass. The normal successor self-CaC retry subsequently
passed in 174.539 seconds on the published fix; this verifies the import repair,
not the remaining application or full successor acceptance tests.

## Propagate existing RHSM inputs into selected AIOps runtime settings — 2026-11-09

Implementation `8efa9df482fc7497c0ffb9e6e3fe8fab5f9e2735` (0.49.2) prepares the
RHEL prerequisite inputs needed by the existing MCP jobs. The source's existing
vaulted organization and activation key already support AAP's RHEL setup; the
existing AIOps pre-import phase now reuses that approved material for the
selected allocation's encrypted runtime namespace. No new credential, store,
helper or job is introduced, and configuration import registers no host.

The instance name is derived from the verified selected allocation. The runtime
entry includes only that name, the protected RHSM inputs and the required RHEL 9
BaseOS/AppStream repositories. Existing matching material is retained; a
different organization or key stops for review rather than being replaced.
Other instances and unrelated runtime settings stay unchanged. Protected inputs
are accepted only in the action's no-log pre-import phase and omitted afterward.

The actual native-mode fixture exposed a missing exact-type serializer handler:
Ansible's string conversion produced a native unsafe string whose literal tag
was lost during YAML writing. Existing roundtrip validation correctly refused
publication. Adding that type to the existing literal-string serializer fixes
the failure without weakening validation or adding another serialization path.

All 34 preparation tests and both serializer/CoP merge tests pass, including the
actual pre/post tasks in both native modes, encrypted local Git publication,
selected-instance preservation, repeats and mismatch refusal without credential
output. Scoped strict lint, Python compilation and diff checks pass. These
results do not establish future-instance live import, registration or MCP use.

## Apply source-owned firewall CaC through native Ansible — 2026-11-09

Implementation `90edda0546fe149d317846d8d257fefe7abf6319` (0.49.0) replaces Python firewall mutation
and the deployed JSON policy with readable Ansible, certified firewall role
1.120.5 and reviewed Hactar native nft tasks. The owner selected CaC as desired
state, including removals, and approved temporary atomic-directory locking across
independent jobs. Existing resource/production guards and source-publication
boundaries remain; read-only provisioning pin checks require an explicit apply
when native policy differs. The same-host switch must quiesce old flock writers.

Application permissions remain in their own encrypted AIOps instance records.
Existing central bootstrap authentication loads that source without a second
colliding Git credential. Native tagged loading preserves unsafe literals and
unused encrypted leaves; no deployed state file becomes policy authority. Only
native old/new/rollback policy combines base with current application grants.
Canonical base publication remains base-only. The independent protected source
address and reviewed public Hactar revision are required caller inputs.

Exact selected decommission disables and verifies ordinary rich rules before
removing domains or source records, while retaining other instances. Arbitrary
source omission cannot identify an already orphaned ordinary rule: stop for
manual reconciliation rather than infer ownership or purge unrelated rules.
New clone-record publication and final AIOps-record retirement remain explicit
private-CaC operator steps; no new publisher, registry, credential type or service
was introduced.

The merged functional source passed 103 focused tests, strict scoped lint for
16 Ansible files and syntax checks of the five normal stage/decommission
playbooks. These are source/fixture results. Protected migration, coordinated
consumer pins, host application and live AAP demonstration acceptance remain
separate rollout work. No formal review or live acceptance is claimed.

## Use fresh default Command Center setup and target-side MCP builds — 2026-11-09

The owner selected the latest Command Center source at deployment, its maintained
default installation directory, a separate home-relative agent workspace and a
fresh Beads tracker on first setup. Repeated deployments preserve existing
tracker data and authentication. No demonstration-repository checkout is needed
as a prerequisite. The missing-tools/workspace Ansible patch is prepared and
locally checked, with publication and live application acceptance still pending.

Public AIOps implementation `7a973353e2c7e0215473b1d9393b5b984d54be57`,
release 1.2.0, implements the previously selected target-side MCP image builds.
The obsolete rendered artifact prerequisite is removed while preserving existing
encrypted instance records and runtime secrets. Four build fixtures, ten MCP
regressions, syntax and focused strict lint passed; real builds and authenticated
queries remain to be verified through the existing application jobs.

The owner also requested reproducible CloudCLI setup for two new-TRA accounts
using the newer release currently installed in the selected existing account,
while preserving the production account's older installation. Its existing AAP
MCP settings belong in encrypted AIOps CaC. Reading that private account requires
a protected operator export; no credential has been copied or guessed.

## Use CaC and Ansible instead of custom deployed state — 2026-11-09

The owner superseded the host-state proposals documented after `2b25410`
(0.48.26). Encrypted project CaC is the single desired-state authority, including
ownership, validation and the target hypervisor. Each instance has its own
section; adding another instance must preserve existing sections. Applying
changed CaC must remove deleted permissions rather than preserve observed rules.

The immediate firewall work replaces the custom isolation-helper/JSON path
with readable Ansible and native firewall configuration. The broader existing
cleanup task now includes custom helpers and deployed sidecar state; a parallel
source inventory identifies writers and consumers before migration. Native
application authentication/data and essential resource/production checks remain
protected. These are selected requirements and work in progress, not a claim of
implementation or live acceptance. This conversation owns the firewall work;
the application-builder conversation retains application development.

The owner also selected target-side MCP image builds, with public build recipes
and encrypted per-instance AIOps configuration. The offline key-delivery choice
is superseded. A registry or separate development/build host remains deferred.

## Correct the CCNG blocker and preserve separate firewall ownership — 2026-11-09

The owner confirmed existing CCNG setup creates a password when absent and
reuses an existing one. Source `f6c28a1` (0.37.0) documents that interactive
behavior; its AAP task requires protected input only without authentication.
The earlier claim that a new application setup feature was required is withdrawn.
The rollout is ordinary unfinished work: update the selected successor data,
verify its existing setup path, deploy through AAP and check actual login.
No user password, default, auth transfer or changed authentication design is
supplied by this clarification. Production proxy task completion remains separate.

The owner also chose AIOps ownership for Zabbix-specific firewall permissions,
added on deployment and removed on decommission. The earlier exception question
is superseded. Building Command Center owns the integration; its draft calls
interfaces that do not yet exist and has no live validation. This documentation
does not publish that draft or implement the proposed base/use-case policy check.

## Stop monitoring setup on an invalid sample and preserve the ownership choice — 2026-11-08

AIOps implementation `f1b5d64` (1.1.8) requires a fresh successful website
sample before forwarding. The negative test exposed an explicit failure
override that masked exhausted readiness retries; removing it from both
health polls restores standard Ansible failure handling. Fifteen focused
tests and strict lint passed; a real retry remains held.

Exact guest diagnostics established the current website-probe failure:
the verified monitoring VM has no permission to reach its hypervisor bridge
on HTTPS. The validated candidate adds only that existing-schema client.
Native and central-record changes remain unapplied while the owner decides
whether the existing shared firewall records may remain in AutoDeploy secrets,
given the earlier AAP-only rule. No application settings are proposed there.
The saved-image job also lacks automatic publication of those shared records;
operator preparation remains an explicit limitation, not a completed feature.
The website is restored and disarmed, both activations are disabled, and the
separate MCP artifact-key delivery choice remains unanswered.

## Verify monitoring separately from the full repair demonstration — 2026-11-08

AIOps fix `93a30e3`, published at `3420f92` (1.1.7), extends the existing
frontend readiness window to cover the observed DNS negative cache. Address,
IPv6 and trusted-certificate checks remain intact; fourteen focused regressions
and strict task lint passed. The normal owned retry then passed without another
clone. Its identity, HTTPS Basic gate, monitoring and forwarding configuration
were verified. The real outage test then found that the website probe has no
valid sample and times out before generating an event. That connection remains
under repair; configuration success did not prove website recovery.
The exact new testserver's normal agent installation also passed.

Private AIOps implementation `1a64a17`, documented at `0db59ca`, preserves the
verified selected-instance resource and final monitoring settings. The normal
configuration refresh passed with other instances unchanged. The existing
website recovery route is tested separately from private MCP and AI-driven
repair. The latter still needs the owner's pending artifact-key delivery choice;
no credential mechanism or new helper was selected to bypass that decision.
These are partial service results, not complete recovery or permission to start
the conditional bare-metal reinstall.

## Preserve staged acceptance and the exact predecessor VM retirement — 2026-11-08

Windows `c54d4d4` (1.1.14) passed the selected successor's AD login/RBAC checks,
both April OS baselines and complete application baseline-to-upgrade verification.
Implementation `a11695c` (1.1.15), documented at `de0687c` (1.1.16), then passed
all five normal guest retirements and final network/source cleanup using backend
`e0a96b1`. Original core guests and golden images were preserved. The original
workflow failed and required staged continuation; fresh unattended acceptance
is still unproved, and the original masked failure's precise cause is unknown.

The owner reiterated removing only the old AAP VM. The earlier implementation
choice question was withdrawn in favour of that one-off exact VM operation;
no partial-decommission mode was added. After Windows baseline verification,
the registered VM and its single unshared runtime clone were removed. Remaining
core definitions/states, source images and policy passed verification. DNS,
proxy, credential and canonical residuals remain separate later cleanup work.

The existing Linux template on Assistant `9d76402` (1.11.11) deployed the new
testserver and TRA with actual native and source/canonical matching, exercising
publisher fix `785e613`. Their remaining AIOps services are not inferred from
VM deployment. The existing approved backup route also preserved all 22 MCP
artifact files immutably and passed byte-level verification; exact restore
metadata remains in Hactar's existing encrypted download evidence. No new
artifact store, credential type or runtime helper was introduced.
Hactar implementation `7def85f` preserves that verified restore record and all
168 selected encrypted task records, retaining previous IDs and export scope.

Private Windows implementation `18f2ae7`, documented at `512e247` (0.0.2), makes
the existing API credential's CA bundle include the already registered selected
issuer when absent. Eight native rendering checks passed; the full current
35-template resource render and all unrelated private data remained unchanged.
This prevents repeating the known missing-issuer preparation defect without a
new trust source or factory. Fresh next-instance runtime verification remains
part of the later recovery acceptance.

## Retire only the predecessor AAP and continue on the successor — 2026-11-08

The owner withdrew the earlier source-AAP restart and directed retiring that
AAP while continuing tests on the successor. Other predecessor guests and
source images remain protected. Retirement must wait until normal Windows
cleanup verifies its immutable original core baseline, which still includes
the shut-down AAP's domain and disk. Earlier restoration plans are historical
and superseded, not permission to restart it.

Source review found that the existing decommission entry removes the entire
same-version environment. It must not be used for this narrower instruction.
The existing exact-retirement capability is being assessed before any resource
removal; this documentation introduces no new selector, framework or helper.
The pending CCNG rollout also needs successor AAP bindings rather than relying
on the retired AAP; its first-opening feature remains separate application work.

## Bound native release lock contention and keep diagnostics safe — 2026-11-08

Fix `e0a96b1c13c756faf7cef3ca7ca3fe2dcc3b1e2e` gives the existing release
transaction the same bounded five-second lock wait as the management helper.
Separate AAP processes can reach this shared native critical section; Ansible
task throttling does not serialize those processes. The exclusive lock still
precedes every probe and mutation. Identity, current-policy, production denial
and rollback checks remain unchanged; the separate retirement path is untouched.

Only a controlled lock-exhaustion marker produces code 75 and fixed public
failure text. Command input/results stay protected, while other exceptions keep
generic diagnostics and are not retried. No helper, framework, type or result
schema was introduced.

The earlier pinned helper failed immediately under a real sandbox directory
lock and discarded the error through its CLI. This reproduces a defect, not
the original historical exception: retained failure diagnostics were censored,
and the exact lock owner is unknown. An identical later retry passed, which
does not establish the missing cause.

Fifteen runtime tests, eighteen supplemental-interface tests and four version
tests passed, including real transient locking followed by complete fake-native
apply, bounded exhaustion without probes or changes, unchanged rollback and
identity checks, exact CLI classification and native Ansible secret-canary
protection. Strict production role lint, Python/YAML syntax and whitespace
checks passed. Caller pins and a complete authorized live workflow remain
separate work; publication is not full-project or live end-to-end acceptance.

## Correct first-opening setup and approve the Windows test window — 2026-11-08

The owner clarified that a fresh CCNG installation creates its password at first
browser opening. It must use neither a default nor a password provided before
deployment. Earlier entries describing a required Vault password reflect the
worker's mistaken interpretation and are superseded by this correction.
Existing user authentication remains preserved. The application owner reports
CCNG 0.35.1 still requires authentication before startup; therefore the fresh
rollout waits for implementation and verification, with no user-password input
pending. No authentication control or private runtime setting was changed.

The owner separately approved the existing bounded Windows capacity proposal:
gracefully stop only the selected source AAP on the pinned test hypervisor,
run the successor's normal Windows test and owned cleanup, then restart and
verify the source's services and prior EDA state. Production, other core guests
and golden images remain protected; force shutdown and AAP decommissioning are
excluded. The decision is resolved, while actual execution is tracked separately.
This documentation does not claim successful shutdown, testing or restoration.

## Verify and retire the disposable Assistant environment — 2026-11-08

The normal successor software test passed on pinned Assistant source `73a74ac`
(1.11.8) using private preparation `0157adc` and pair `1997664`. The complete run
took about 46 minutes and exercised actual deployed CLI, environment and
project-isolation checks, without authentication restoration or model inference.
Guest identity and canonical publication matched the resulting resource.

The existing retirement preview and apply both passed. Independent checks found
the case domain, disk, static DHCP/DNS records, owned policy and inventory rows
removed, with all five original guests and golden images preserved. One dynamic
DHCP lease remains cached until normal expiry; no shared-network restart was
used to clear it. This completes the disposable software test and cleanup,
while full successor services and independent host recovery remain open.

Assistant implementation `1ee9e4b`, documented at `9d76402` (1.11.11), then
updates only the existing public helper revision from its earlier value to
AutoDeploy fix `785e613`. All 23 focused caller/recovery/retirement/version
checks, three syntax checks and scoped lint passed. Private configuration and
the pinned software-test baseline stay unchanged. Actual new-guest publication
and AIOps consumption still need their own runtime verification.

Normal Automation Orchestrator and RHEL configuration setup then passed on
tested source `ead5a05` (0.48.17), preserving prior objects, token-store state
and EDA activation state. The RHEL-only prerequisite run confirmed fix `7d8a59b`
without selecting another case. Their reviewed projects, templates, inventories,
execution environments and credential definitions are installed. These API
imports do not establish OpenShift deployment or external RHEL patching.

## Require a chosen CCNG password only for fresh setup — 2026-11-08

The owner withdrew the shared default-password and first-login access-choice
proposal. A fresh install must require an operator-chosen password, and an
existing user-set password must be preserved. The obsolete rollout dependency
is removed; no answer to the withdrawn access question is still required.

Published CCNG source `e5e1232` (0.35.0) already enforces this in its AAP password
task. The standalone installer's noninteractive behavior is a separate
application-owner concern. The rollout resumes private-candidate and secure
input verification, retaining the approved Machine/Vault choices and existing
target. No password is copied, generated, reset or supplied by this decision;
configuration import and actual application verification remain separate work.

## Prepare reviewed EE-only use cases independently — 2026-11-08

Fix `7d8a59ba8f310246493aa48db41da366d1111ab0` removes the common requirement
for at least one PAH repository. The reviewed RHEL capture deliberately declares
none because its existing runtime image supplies its Satellite collection.
Requiring an unrelated selected use case would hide that standalone setup defect.
Review, mapping, sequence, repository uniqueness, exact collection versions and
execution-image readiness remain required; empty collection loops simply skip.

Eight native admission/PAH tests, sixteen selector tests and four version tests
passed. The admission regression executes the real task definitions, admitting
reviewed empty requirements and refusing unreviewed, missing-image, duplicate and
unpinned inputs. Strict production lint and prerequisite syntax checks passed.
These are source checks; standalone live metadata setup and external application
runtime acceptance remain separate. No helper, flag, credential or schema is added.

## Preserve verified Linux SSH fields for the next AIOps import — 2026-11-08

Fix `785e613f53036fae61bf3a63b994a83fbe68fcaf` carries a Linux guest's supplied
verified user and port into its source inventory alongside the existing native
resource. The previous publisher omitted those fields on a new host, so the
unchanged AIOps provenance check could not accept that host without manual
inventory edits. No account or port is inferred, conflicting existing values
still stop publication, and Windows keeps its separate WinRM behavior.

Thirty AIOps preparation/publication tests, nine encrypted guest-release tests,
twelve Windows lifecycle tests and four version tests passed, with Python syntax
and whitespace checks. The new producer-to-consumer fixture proves the mapping,
idempotence, conflict refusal and behavior when optional fields are absent.

The existing publisher was corrected rather than adding a helper, schema,
credential or alternate registration path. Its source-fix task is closed in the
existing task overview and encrypted recovery export. Selecting this revision
in callers and proving a full live guest-to-AIOps run remain separate work;
publication is not full-project review or end-to-end acceptance.

## Verify the website and prepare the existing disposable test — 2026-11-08

AIOps source `c69097e` completed the successor website deployment without changing
code or DNS timeouts. Normal DNS and trusted HTTPS then passed, with monitoring
and auto-arm off; the expected selected AAP fault destination was verified.

Private Assistant implementation `0157adc`, with encrypted pair `1997664` and
published history `df7bbda`, prepares only the selected successor's disposable
test and retirement settings while retaining the predecessor's six snapshots.
Prepared identities are selected explicitly, including their supported aliases;
unprepared instances fail rather than inheriting another instance's settings.
The already defined Linux utility joins the ordinary concrete resource list by
YAML reference, preserving the original seven definitions and existing validation.
No dispatch framework, helper, credential type or new store is added.

Normal configuration import passed. Source/render ciphertext preservation and
public provenance were checked; AAP masks stored secret fields, so their native
bytes were not read independently. The existing disposable runtime test will
verify normal consumption instead of adding a redundant secret-storage check.
Software acceptance and owned cleanup remain unfinished.

## Retain the approved image-based Zabbix authentication baseline — 2026-11-08

Private configuration implementation `bf75752` supplies the selected demo's
existing MCP-token leaf from its approved image-bootstrap value. The earlier
working setup already used that image credential, and the owner authorized
taking over its MCP configuration. Requiring a newly minted Zabbix token would
have added an unnecessary producer and encryption/publishing mechanism.

Keep the existing runtime schema, selected-resource/endpoint checks and explicit
normal CaC refresh for saved job payloads. Target-local AAP/MCP and EDA credentials
remain separately generated by the existing factories. No new credential type,
store, helper or hidden child job is introduced. The private configuration and
docs are published at `63c91c2`; application and private MCP tests remain pending.

AutoDeploy source `22ac431`, including port-boundary fix `2cd85c8`, passed the
normal AIOps import after the successful prerequisites. Native readback verified
the new objects and disabled activations while preserving prior instance data.
Remote and self-targeted AutoDeploy imports also passed; these are configuration
acceptance results, not complete successor service recovery.

The successor's normal Windows and Assistant prerequisite/import sequences and
AIOps self-refresh also passed on that source. Existing objects and native
credentials were preserved; new EDA activations remain disabled. Fresh Windows
runtime is capacity-dependent, and Assistant's disposable test still needs
instance-specific payload preparation. Keep those gaps explicit rather than
counting successful configuration imports as application acceptance.

## Accept native inventory port text at the AIOps boundary — 2026-11-08

Fix `2cd85c8` normalizes a canonical decimal-text inventory SSH port before the
existing strict hypervisor pin validation. A normal configuration import exposed
this representation difference during successor AIOps preparation; the selected
port itself matched the independently verified route. Identity, account, host-key
and port-range checks remain unchanged, and no saved inventory is rewritten.

The focused 29-test AIOps module, four version tests, Python syntax and native
selected-context reproduction passed. This repairs preparation input handling;
successful CaC import and application deployment require their own live results.
The existing task overview was refreshed without introducing new automation.

## Document the AAP-only successor acceptance — 2026-11-08

The tested runtime remains `30629f7` (source 0.48.7), including guest SSH fix
`34b40d1`. The source controller completed the four existing stages, and bounded
independent checks verified trusted public API/token access, a valid license,
ready Controller and distinct native instance identity. Original guests, disks,
source images and prior API records were preserved. The temporary native
start-at-task setting was restored after the continuation job captured it.

Stage 01 required a repair and continuation, so this closes AAP-only acceptance
without claiming a fresh unattended run or complete successor service recovery.
The quick guide now describes the four installed stage templates directly;
fresh successors must not depend on an assumed umbrella workflow. Additional
use-case imports and memory-aware runtime testing remain separately tracked.

The existing task overview and encrypted recovery export retain the actual job
outcomes and limitations. This documentation update introduces no new workflow,
recovery mechanism, credential, allocation, shutdown or host reinstall.

## Preserve guest SSH routing above hypervisor facts — 2026-11-08

Fix `34b40d1` keeps the existing Stage 01 SSH safety checks while giving the
new guest's connection settings the same precedence as the earlier hypervisor
facts. A delegated block's variables alone did not override those facts, so the
readiness guard correctly stopped before guest authentication. The probe now
saves the original connection, binds the exact pinned guest route and restores
the original hypervisor facts in `always` on success or failure.

The existing native Ansible regression now reproduces the observed precedence,
checks guest SSH through the pinned hypervisor, rejects unsafe higher-precedence
caller inputs and verifies restoration. It also checks native partial-stage
continuation when earlier connection facts are absent. All 26 allocation/routing
tests, focused playbook syntax and production lint passed. The failed live run
created one guest before the guard stopped; completing a partial stage remains
separate from proving a fresh unattended deployment.

The public task overview includes the existing successor functional-test child.
Paired Hactar checkpoint `573acb4` preserves all 150 prior task records and that
child in the existing encrypted recovery snapshot. No new recovery framework,
workflow, credential or counter reset was introduced.

## Preserve completed teardown and production HTTPS acceptance — 2026-11-07

Checkpoint `0ddcd06` documents the passed staged Windows patching demonstration
and Windows-only reset separately from fresh unattended provisioning. Final
verification passed on Windows source 1.1.11; its published documentation retains
the earlier repairs and unresolved historical failure rather than hiding them.

Hactar checkpoint `c68f6e6` preserves all 150 prior full task records and current
outcomes in the existing encrypted recovery export. Production backend HTTPS
verification and the user's confirmation of external and localhost access are
recorded as completed; the rejected host-setting removal remains withdrawn.
The separate test application waits on the existing first-login implementation
task, not another password request. Read-only successor readiness does not mean
a VM has been allocated or installed.

Mirror/export checks, Vault preservation, the original handover checksum and
diff checks passed. This checkpoint changes no runtime code or configuration.

## Document the approved application deployment choices — 2026-11-07

Documentation checkpoint `090d761` records the owner's explicit approval of
encrypted runtime settings, expected SSH server-key preparation, credential-free
HTTPS public-source download and matched tested application revisions. The
README distinguishes configuration import from installation and running-service
acceptance so restoring the project does not repeat the resolved decisions or
mistake an imported template for a working application.

The public overview reflects completed preparation and ongoing runtime work.
Hactar checkpoint `1f76421` retains all 150 existing full task records and their
current user answers in the established encrypted recovery export. Export/mirror
checks, preservation of every prior record and the original user handover,
four existing version-tool tests and diff checks passed. No runtime playbook,
credential, inventory, application restart or new recovery mechanism was added.

## Clarify the canonical Command Center task title — 2026-11-06

Existing task `bead-wd-1rl.40` now reads "Deploy Command Center from AAP to the
selected workstation". This makes the deployment direction clear and keeps the
public title generic. Actual target choices, original notes, state, owner and
labels remain unchanged; Hactar checkpoint `62c2a27` retains the full encrypted
147-record context and appended clarification.

The ordinary exporter/mirror refresh and preservation checks passed. No exporter
code, title-override mechanism, new research, runtime or umbrella change was
introduced. Existing README instructions remain accurate. Published history is
preserved; this is one necessary metadata-only follow-up.

## Reflect waiting tasks and an open stability issue accurately — 2026-11-06

The existing diagram task `bead-wd-72f.35` is blocked on its already-pending
client error/viewer question, with no browser-diagnosis worker running. The
known stability issue `bead-wd-72f.31.4.3` is open: bounded research/observer work
finished, but its cause and correction criterion remain unmet. Neither a new
active investigation nor a completed fix is claimed. Windows and the deployment
integration keep their actual input blockers.

Hactar checkpoint `89c2cf1` retains all 147 complete encrypted task records and
these exact two status corrections. Exporter/mirror checks and preservation
checks passed. Existing README instructions remain accurate. This single
metadata/version checkpoint changes no runtime source, evidence collection,
base configuration, credentials, DNS or umbrella reference.

## Reflect completed Windows OS work and the remaining package-access blocker — 2026-11-06

The existing Windows acceptance record now has a real public status change from
in progress to blocked. Windows 1.1.5 documentation `0626bd5` and tested executable
`2dfb9c0` establish both selected OS patch jobs at their exact April builds,
with zero remaining approved updates/reboots, alongside successful AD and WSUS.
Only the existing Nexus package-access approval blocks the remaining package
chain; its prepared rule is unapplied. Full use-case acceptance stays open.

Hactar checkpoint `ed5a152` retains all 147 complete encrypted task records and
the actual proof. Exporter/mirror checks passed with every prior ID preserved.
README instructions remain accurate and unchanged. This single necessary
overview/version checkpoint changes no runtime source, base, credentials or DNS.

## Retain existing deferred external CaC work — 2026-11-06

Documentation `e8d43a1` adds the existing `bead-wd-9ezo` to the generated public
overview as a deferred future independent External CloudCLI CaC project. The
original task, ownership and labels are retained; no duplicate or implementation
task is created. Its full handoff and the current blocked integration inputs
remain in Hactar's encrypted 147-record export, checkpoint `6514ae2`.

The existing exporter/check retains all previous task IDs, and Hactar's overview
check passes. Public text contains only generic task metadata. The user's
handover and separate deployment evidence are preserved. This publication
changes no runtime source, credentials, base configuration, DNS or umbrella refs.

## Document verified agent recovery without changing deployment behavior — 2026-11-06

Documentation `8b44905` refreshes the public overview to 87 tasks, including the
closed agent-remediation acceptance and rebuild-tooling task, and the current
transferred rollout state. The selected isolated service-outage chain passed on
AIOps runtime `3da21af`, including bounded-turn implementation `67a6e69`; its
acceptance documentation is `c69097e`. One real event launched one bounded agent
and one saved repair, with native target, service and fresh recovery verification.
This does not establish package-removal recovery or successor installation.

Hactar checkpoint `3904f20` preserves the actual aggregate and all 146 complete
selected task records, including closed acceptance. Existing exporter/mirror
checks passed without changing that encrypted checkpoint during this overview
refresh. Public output contains metadata only; private records and the user's
handover remain protected. No runtime playbook, base configuration, DNS,
credential or production-project pin was changed by this publication.

## Keep transferred AAP work in the recoverable task overview — 2026-11-06

Documentation `da64bd1a2f17579176694017e188e812f5a134c1` refreshes the generated
public overview to 86 tasks, including the existing transferred rollout question
and the Windows API-responsiveness follow-up. AAP-owned integration work retains
its project label, conversation association and original parent; classification
does not answer its pending Vault-source question or authorize deployment.

The public overview matches a fresh Beads read. Hactar checkpoint `dabae0b`
already holds the 145 selected full records and remains byte-for-byte unchanged.
No automation, credential binding, VM or live-job behavior changes. Published
documentation remains separate from unfinished runtime and successor acceptance.

## Diagnose missing diagrams without hiding a valid rendering — 2026-11-06

Implementation `51b8df4` replaces a misleading blanket network error with separate
Mermaid import, rendering and node-control errors. A node-control exception now
keeps any rendered SVG visible. Static instructions distinguish a script-blocking
preview from a started runtime without assuming the user's viewing context. The
pinned module was reachable, and its actual grammar accepted all 28 vertices in
a syntax-only Node harness; that does not exercise browser DOM sanitation or SVG
layout. Focused checks cover the separate failures and preservation of rendered
SVG. Strict security remains unchanged. The reported client-side failure still
requires its actual stage/error; browser end-to-end verification is unavailable
without an installed executable. This checkpoint is diagnostic progress, not
closure of the user's missing-diagram report.

## Name the actual work and add a local interactive companion — 2026-11-06

Implementation `c3f4b74` replaces vague pilot phase labels with Windows
connectivity, Assistant Team installation/cleanup and Windows/private MCP test
preparation. The frozen window, 28 steps and historical timing qualifications
remain unchanged. At the user's additional request, a plain HTML companion embeds
the same diagram and details; known-node clicks or Enter/Space toggle native
details without changing Mermaid's strict security mode. A pinned Mermaid12.3.0
CDN runtime is the sole online rendering requirement; no server, package install
or new audit is required. The CDN response, content parity, all node toggle paths
and runtime-failure fallback were checked. Browser rendering remains unverified
because no browser executable was available. Markdown remains the GitHub-readable
source; users download/open the HTML locally rather than expect GitHub to host it.

## Explain delivery delay through a bounded visible-history pilot — 2026-11-06

Implementation `15bd6ce` adds the user-approved Markdown flowchart for one frozen
24-hour window. Its 28 short Mermaid blocks map to native collapsible details,
keeping the overview readable while explaining decisions, actual failures,
fixes, outcomes and timing. Main visible chat and existing decision histories
drive the narrative; underlying execution evidence only corroborates facts. Raw
action lists, private reasoning and environment identifiers stay out of Git.
The record separates real installation time, observed rework, pending execution
and the acknowledged overnight continuation failure; unknown effort and parallel
overlap remain explicit. No live AAP query or behavior change was needed.
Structural/privacy checks passed; a Mermaid renderer was unavailable, so rendered
layout was not claimed verified.

## Carry only the private AAP issuer in runtime settings — 2026-11-06

Implementation `bde1120` reads the installer's `tls/ca.cert` by default. A real
CaC request failed with HTTP 413 because copying the extracted system-root
bundle expanded encrypted runtime data past the proxy request limit. The actual
installed issuer is already present in that bundle and independently verifies
both private MCP and Controller HTTPS identities. No proxy limit, token or
global trust change is needed. Public provider calls retain their existing
system/vendor roots and additive application trust. The native publication/reuse
test passed; selected metadata correction and live import retry are separate.

## Preserve secondary isolation during final AAP release — 2026-11-06

Implementation `437fe9f` keeps source policy comparison aligned with the existing
primary-only AAP release. A live base refresh exposed that the shared interface
enumerator also selected a Windows-owned second interface, contradicting the
intended transition. The fix selects only the primary identity for this AAP
operation; secondary ownership and native hardware checks remain unchanged.
The focused regression proves publication and an idempotent repeat without
granting the secondary interface egress. Live base retry remains separate proof.

## Reuse selected instance access for private AIOps MCP — 2026-11-05

Implementation `8237ce6` adds optional private MCP endpoint/public-CA metadata to
the existing encrypted instance record and credential payload. Ordinary API
authentication and legacy records remain unchanged. Existing base publication
reads the installed authority; existing AIOps preparation copies only the chosen
connection into its runtime Vault. This keeps the API importer free of SSH and
adds no token, credential type, store or job. Compatible readers must be synced
before normal selected-instance backfill; unrelated pinned guest lifecycle paths
preserve the mapping. Forty-five focused checks and both affected syntax entry
points passed. No backfill, deployment, model or policy action ran for validation.

## Reuse the existing Windows retirement source plan — 2026-11-05

Implementation `41c77d231c54baf9ea3fd70d7b2b35f00183de33` exposes the same
retirement source plan as an internal task entry point, so the existing Windows
reset job can distinguish registered guests from unconfigured clones before
native checks. A focused native test found that absent records became empty
strings under non-native Jinja; retaining the complete mapping preserves actual
null absence. Registered guests still require full native planning and normal
publication. Three focused tests and two-file production lint passed. Complete
Windows reset remains subject to the separate authorized live test.

## Keep Windows AAP networking in its infrastructure deployment — 2026-11-05

Implementation `eb806b7b79d51f08d7cf54fb2edb3d449ed375aa` follows the owner's decision that the
Windows infrastructure job should prepare its selected AAP's second isolated NIC
and persistent RHEL connection, following the AIOps infrastructure pattern.
The existing private Windows profile declares this requirement. The API-only CaC
import installs definitions; the infrastructure job performs the host work.
Existing AAP guest preparation remains a partial image, storage, subscription and
installer setup, rather than a complete declared RHEL operating-system baseline.

The same existing AAP allocation and main-inventory ownership record retain one
optional Windows interface. Its primary identity and route remain immutable.
Native checks account for the exact current and persistent interface set,
Windows ownership alias and virtio model. Authenticated RHEL readback proves the
static address, manual IPv4, disabled IPv6, persistent connection and absence of
a gateway or DNS configuration. Firewall permissions remain unchanged.

The same role exposes its source preflight before host work. Its existing
publisher saves the bounded ownership change with encrypted Git compare-and-swap
and reconciles the same source inventory row. Concurrent writers retain a
published exact owner. Failed jobs may remove only newly created components,
after a fresh authenticated read proves canonical ownership absent; uncertainty
preserves the components for review. Complete AAP cleanup consumes every saved
NIC and removes exact owned DHCP/DNS host records while retaining other network
content. Older live single-NIC AAPs reuse their already validated native identity
without inventing saved verification metadata. Missing ownership still refuses
ambiguous reservation cleanup.

Repeated dynamic role calls exposed Ansible's cached action module retaining an
earlier deleted checkout. The publisher now reads settings through each native
action instance's current source path, retaining strict path validation and the
existing authentication and cleanup behavior.

The merged tree preserves the separately published sixth RHEL CaC project and
passes 54 supplemental-interface, native plugin-lifetime, project-contract,
bootstrap and selector checks. The coordinator independently repeated all 17
supplemental tests. Existing decommission, allocation, source TLS and native role
checks also passed, as did production lint, AST, local links and whitespace
validation. Real capture rendering passed with the normal existing environment
and CaC Vault identities. This publication establishes code and local validation;
live interface setup, Windows functionality and complete cleanup remain separate
acceptance steps. This worker launched no live job or host operation.

## Add explicit HTTP bootstrap for an already owned guest — 2026-11-05

Implementation `85ee77d` follows the owner's decision to retain the current
container platform and its HTTP downloads.
The approved permission is public IPv4 TCP 80 for only the existing verified
guest, retaining its HTTPS access and all private/reserved/production blocks.
The shared implementation therefore extends the existing guest bootstrap and
publication transaction with `guest_bootstrap_http`, rather than changing HTTPS
approvals or releasing the guest before configuration succeeds.

HTTP is an independent optional list of exact bridge, IPv4 and MAC identities.
The new operation requires the complete existing published guest identity and
placement, then repeats native domain, disk, network, lease and bootstrap
provenance checks before applying the exact derived change. Existing source-job
verification, encrypted compare-and-swap publication, source alias reconciliation,
idempotent retries, durable-publication handling and bounded rollback remain.
All existing policy operations preserve HTTP permissions; exact retirement
removes only the selected identity and retains production denial while another
HTTP, HTTPS or released guest survives. No service, store, registry, credential,
job template or wrapper is introduced.

All 113 scoped checks passed, including the real encrypted publication and
interrupted source synchronization retry, native HTTP operation and rollback,
complete guest identity checks, preservation through AAP/Linux/Windows policy
operations, and exact retirement. The coordinator independently repeated the
six HTTP tests. Production lint passed five files, and compile, policy-call
propagation, whitespace and added-text privacy checks passed.

These results establish implemented code and test behavior. Live helper
installation, source synchronization, encrypted environment changes, firewall
application and successful guest downloads remain separate acceptance steps.
This publication did not run those operations or launch a job.

## Verify the existing native Claude installer separately from model access — 2026-11-05

The AIOps implementation `80b7dff`, published in `86d3cb5`, passed its normal
native Claude installation with both private MCP diagnostics. Independent checks
verified the pinned binary, actual job user's command path, protected guardrails,
approved provider configuration and preservation of the original client data.
This verifies software readiness; no model call or isolation release occurred.
Those checks and the complete successor environment remain separate work.

## Retain the approved Windows demo certificate policy — 2026-11-05

Implementation `276ad84e257453d14a729d9cc806c0b65771e2e8` follows the operator's
choice to keep the existing Windows lab connection: HTTPS on port 5986 with
NTLM and certificate validation disabled. The additional predeployment image and
WinRM inspection is skipped. This corrects an extra prerequisite introduced for
the versioned test environment; it does not require new authentication or
certificate infrastructure.

Both existing Windows resource validators retain the same fields and require a
real Boolean certificate-validation result. The approved exception records
`false`; actually validated connections record `true`. Neither may replace
`verified: true`, authenticated computer facts or the independent native
UUID, exclusive clone, owning instance, NIC, source and policy checks. Strings
and numeric substitutes are refused. Other platform and SSH trust settings are
unchanged, and no new policy flag, job, credential type, store or service is added.

Eleven Windows lifecycle checks passed, including capture preservation of false,
native UUID mismatch refusal and real encrypted publication/retry for both
Boolean cases. Forty existing Linux/AAP lifecycle and version checks also passed.
These are source tests; actual Windows management connectivity, configuration,
isolation release and functional acceptance remain separate work.

## Match canonical live Controller SSH port representations — 2026-11-05

Implementation `6de45e0` normalizes only the live inventory SSH port before
comparing it with the exact registered pin. Controller had returned a canonical
decimal string where encrypted ownership used an integer; the same numeric port
was incorrectly refused during the shared bootstrap preflight. Actual receiving
logs showed successful source API reads, and read-only replay of the saved guest
artifact/captures reproduced this identity refusal. With the correction that
read-only plan passes without changing live variables or policy.

Only an integer or canonical ASCII decimal string in range 1–65535 is accepted.
Booleans, floats, signs, whitespace, leading zeros and other ports remain refused.
Other identity, source-job, TLS and policy checks are unchanged. Three new tests
include real Ansible/URI YAML-string and JSON-integer Controller representations
in both native modes; fifty-eight related instance, guest, Windows, AAP and
version checks also pass. Live bootstrap/software acceptance remains separate.

## Release the AAP guest only after normal base completes and cleans up — 2026-11-05

Implementation `75639c54ffff61eac7ea9e1b8707ce9f80240bb3` adds the final release
hook to normal Stage 04. The owner requires successful VM configuration before
full recovery isolation is lifted. An AAP primary is not a generic Linux clone,
so the existing shared role/action accepts an explicit AAP route, exact primary
resource and freshly authenticated guest machine ID. It reuses the consumed
reservation and existing native AAP ownership checks instead of fabricating
generic-image descriptions or duplicating the VM record in another store.

Base configuration, MCP/API token validation, source publication, temporary-token
revocation and private-workspace cleanup must all succeed first. The original
trust file is removed in that cleanup path, including failures. Only afterward
does the hook create new short-lived pinned SSH trust and read the guest's
machine ID with the existing login. It neither recovers passwords/tokens nor
changes authentication. The new trust file is always removed, including release
failure. Existing token-store publication and inventory registration must be
enabled; partial/skipped execution and check mode cannot grant full release.
The HTTPS-only installation repair retains its early end-play boundary.

The policy transaction adds only the exact primary bridge/IP/MAC identity in the
same three encrypted captures and source aliases. The selected reservation is
compared before and after durable publication and remains read-only. Existing
source-host aliases, physical identities, tokens, counters, native rules and
other guest permissions remain unchanged. Native checks cover both domain
definitions, actual UUID/disk/MAC/network/DHCP and conflicting guest ownership.
Existing exact rollback and durable-publication retry behavior is reused;
Linux and Windows paths keep their existing behavior.

Seventy-one lifecycle checks and four version checks pass on published 0.41.1,
including eighteen native ordering/failure scenarios across both template modes,
both repair modes and actual independent Git-writer reservation races before
and after publication. Production lint passes fifteen files. These are code and
native-fixture results; no live full-base job or AAP release was run by this work.

Separately, normal AIOps preparation job 3320 succeeded on `5728dfe` (0.41.1),
following implementation `cecff63`. Independent parent-agent readback verified
the new Claude installer, preservation of all sixty-nine previous template IDs
and the selected application's VM identity. That existing-target preparation
result does not prove this new final AAP release or a fresh successor cycle.

## Prepare AIOps data inside its existing CaC import — 2026-11-05

Implementation `cecff63751a800bdd38df3e0a18ab0f6b5c05f59` adds the reviewed
pre/post data stages to the existing `deploy-cac-project.yml` path for AIOps.
A fresh instance previously required already prepared auxiliary guest metadata
and a credential reference before its first import could render. The new stage
creates only the namespace and validated existing base Machine reference,
leaves absent guests disabled, and persists one per-instance Event Stream Basic
password before ordinary configuration roles use it. Existing known password
material is preserved; interrupted or competing Git writes do not rotate it.

The owner approved this repository's existing token having scoped write access.
Preparation therefore reuses the same private checkout, askpass, separate Vault
secrets and selected target HTTPS authentication. Both maintained files remain
whole-file encrypted, preserve original headers/literal tags and are committed
together. Accepted remote state is reread after publication. Capture and
effective launch-time review holds are enforced before commits or target access.
No additional job, wrapper, service, repository, credential type or store is added.

Guest facts are accepted only from matching verified native inventory ownership;
they are not generated or copied from a previous allocation. Zabbix retains its
own clone source hash, schema, frontend/private API references and native IDs,
while Linux retains its existing provenance schema. The shared inventory helper
normalizes only canonical positive decimal counter text, retaining malformed
value refusal and physical alias/ownership checks.

After the existing roles create resources, GET-only readback binds the target's
actual website fault-template ID/webhook key and Event Stream UUID/endpoint.
Existing values must agree; equivalent default HTTPS-port text is preserved
verbatim. The same Controller configuration role saves refreshed ciphertext;
preparation performs no direct AAP resource writes or activation/application run.

Thirty-three affected tests pass against the published Windows lifecycle base,
including actual Ansible modes, real encrypted local Git concurrency, lost
acknowledgements, wrong keys, holds and native provenance. Two private
ciphertext checks pass. Protected current-source/target-GET fixtures preserve
the existing password, runtime ciphertext and Zabbix metadata; fresh-instance
rendering passes both modes without fabricated guests. Syntax, four version
checks and scoped production lint pass. Full recursive lint still reports three
pre-existing unrelated issues, left unchanged.

This is configuration preparation, not complete successor deployment proof.
VM producer orchestration, per-clone Zabbix API/MCP token lifecycle, signed
offline MCP artifacts and approved shared application defaults remain separate
factory work. New namespaces receive no provider credentials. The current
Vertex reuse approval covers only the previously selected TRA and one short
read-only test, and does not extend to later allocations. No new allocation,
VM action, live import or model request was performed for this publication.

## Verify Windows through its own identity in the shared lifecycle — 2026-11-05

Implementation `ae9cfdbdbf29fe0471b71a0163cd557f607d7d8c` adds the explicitly
approved `guest.kind: windows` variant to the existing release and retirement
transaction. Windows clone naming, trusted WinRM/CIM identity and permanent NICs
differ from Linux. Fabricating Linux machine IDs, SSH keys or generic-image
descriptions would weaken ownership proof, so the Linux schema and default
request shapes remain while Windows has a strict bounded field set. No new
publisher, store, service, credential type or job is added.

The caller must complete the VM's configuration and validate its computer name,
normalized CIM product UUID and all observed NIC MAC/private IPv4 pairs over
authenticated, certificate-validated WinRM. Native readback independently matches
the clone marker, owning-instance title, UUID, exclusive Windows disk, both domain
definitions and every network/bridge/subnet/DHCP/DNS tuple. The selected WinRM
address must be one of those verified NICs. One or two NICs receive their exact
policy identities atomically; production protection and unrelated permissions
remain. Later patch/content functional tests are separate from this complete-VM
configuration milestone. No Windows bootstrap exception is authorized or enabled.

Windows retirement explicitly passes its kind even after successful record
removal. Saved canonical/API ownership supports interrupted publication retries;
native checks require the Windows clone and both incompatible Linux canonical
paths absent. Exact per-NIC static DHCP/DNS and policy records are removed through
the same encrypted captures and source inventory. Unknown host-service grants
still refuse preflight, dynamic lease cache is not edited, and allocation/token
state remains untouched. The AAP-only consumed-reservation guards are unchanged.

Sixty-three relevant checks pass, including real encrypted Git/API interruption
recovery, actual native template modes, distinct Windows bridges, native cleanup
and rollback, absent-path checks and existing Linux/AAP regressions. Both shared
lifecycle roles pass production lint; four version-tool checks also pass.
These are implementation checks. Trusted booted-Windows producer and live
deployment/release/decommission acceptance remain separate pending steps.

## Retire one verified generic guest through the existing transaction — 2026-11-05

Implementation `1976a5aae2f70a5455dda9032820889369849183` adds `retire_guest`
and the reusable two-phase `recovery_guest_retire` role. The owner requires
disposable use-case VMs to be removed after successful testing, including their
saved inventory and isolation permissions. Domain-and-disk deletion alone would
leave those permissions behind. The existing source API, Git writer, CaC Vault
and three encrypted captures provide the required ownership and publication;
no separate state store, credential type, service or job is introduced.

Planning resolves exact persisted clone provenance before deletion and refuses
unsupported selected host-service grants. Publication requires the domain and
both canonical disk paths absent, removes only its static DHCP reservations and
HTTPS/full-release entries, then reconciles source inventory. The caller retains
its own application inventory row until shared publication completes. A surviving
canonical/API resource record supports retries without guest SSH. With both
records absent, only physical absence with no additional policy or unknown DHCP
removal is accepted. Dynamic lease cache is reported separately and is not
edited. Existing AAP management and installation paths keep their default strict
guest-presence behavior.

Fifty-eight focused tests pass, including real encrypted publication and API
interruption recovery, exact native ownership/DHCP cleanup, both native template
modes and existing management/installation regressions. Scoped production lint
passes. These checks prove code behavior; the serialized live disposable-guest
deployment and decommission acceptance remain separate.

## Bootstrap approved generic guests without granting full release — 2026-11-04

Implementation `2795c133507ee5affdaf8e420807496cd2299899` extends the existing
verified-guest policy transaction with `guest_bootstrap_https`. The disposable
Assistant installation needs package downloads before it can complete software
configuration. The owner approved public IPv4 TCP 443 for that exact guest while
retaining private/reserved and production blocks; complete deployment and
validation must precede full release. The same source-job, native libvirt,
encrypted-capture and source inventory checks apply. The separate consumed-AAP
installation guard is unchanged, and no new service or credential type is added.

Nineteen guest/publication/native-role checks and eight existing AAP installation
regressions pass; focused offline production lint passes. These checks changed
no live permissions. Final lifecycle hooks and exact disposable-guest retirement
remain unfinished, and a static encrypted test profile must be refreshed from
canonical policy before a retry after a successful policy transition.

That implementation also documents the owner's two repository write exceptions.
The existing AutoDeploy/base CaC writer persists encrypted state. The owner
changed the existing AIOps token to Contents read/write for its own companion
repository so new instance settings can be persisted there. Other companions
retain read-only tokens. This reuses the existing credential/type and preserves
the token value and name; the external permission change was owner-confirmed,
not yet established by a new runtime publication test. Automated AIOps instance
preparation remains a separate task.

The owner approved reusing the reference Vertex authentication on the new TRA,
with any persisted copy encrypted in the private AIOps Vault and one short
read-only Claude/private-MCP test. Its implementation and live result are still
pending. Automation Orchestrator's functional test is explicitly waiting because
the owner currently has no OpenShift access. Another worker owns Command Center
on the shared TRA and another owns the additional RHEL configuration import;
their objects and running guests must be preserved.

## Verify source use cases before the successor deployment test — 2026-11-04

The owner clarified the order after the verified configuration acceptance
documented in `ce2ab03`. First exercise the source environment's remaining
functionality. Then pause its monitoring, TRA and testserver guests while keeping
the source AAP running to install and verify the successor. Building that next
environment is itself part of proving the source AAP's functionality, rather
than a capability that can be fully verified beforehand.

The protected capacity check accounts for all guest allocations and host
overhead. Additional Windows or Assistant test guests need their own allowance;
reclaimable cache and deduplication do not guarantee peak capacity. Paused
source guests retain their definitions and disks for restart. These are planning
and documentation changes, with no VM shutdown or allocation executed.

The first missing source functionality is tracked in `bead-wd-72f.33.1`: add
Claude installation and reuse both existing private MCP deployments through one
AIOps application entry point. Read-only runtime test preparation is tracked in
`bead-wd-72f.31.1`; it identifies actual targets and prerequisites separately from
the already successful configuration imports. Existing authentication, private
MCP and architecture approval boundaries remain in effect.

That read-only assessment also identified inherited Windows/Assistant runtime
targets, missing Orchestrator inputs and unverified login TLS, plus a missing
automatic AIOps per-instance preparation path (`bead-wd-72f.31.2`). Existing
website, monitoring and private MCP results remain valid. The assessment did
not launch those other runtime jobs or select a new writer/storage design.

## Verify remote and self-target AutoDeploy configuration — 2026-11-04

Portable implementation `a522e7b`, group/native-rule fix `1e89880` and trust/counter
fix `2ef4d42` now have normal configuration acceptance. Remote import 3296 added
fourteen AutoDeploy templates while retaining all fifty-five existing templates.
Refresh 3300 verified the five credential-forwarding flags from private
configuration `df6882a`, preserving every template ID and other setting. Existing
production-only objects remain on production and outside the receiving bundle.

Private correction `3104552` retains the existing environment Vault name in its
definition, fourteen template references and extraction dependency. The receiver
had no conflicting credential; its ID, secret inputs and assignments were
preserved. The exact name and ownership guards remain unchanged. All nine
remaining selector guards and six launch-credential plans passed in both native
modes using actual API metadata. Returned injector strings retain their native
unsafe treatment in those fixtures.

Normal receiving-instance selector 84 then succeeded on `8c5a05c`, with existing
prerequisite job 86 and importer 88 both successful. Independent readback verified
trusted source API access, actual running-job and self-target identity, exact
child credentials, shared token store and cleanup. All sixty-nine template IDs
and project, inventory, execution-environment, credential and label bindings
were preserved. No application or VM deployment was launched. The full successor
installation and independent recovery remain separate requirements.

Private capture `9647f70` also applies the inventory display rename and removes
twelve duplicate Windows fields plus two obsolete AIOps fields. Physical VM,
DNS, allocator and token identities remain unchanged; live legacy consumers
still retain their required variables. Normal AIOps refresh 3298 verified the
renamed lookup, existing runtime ciphertext, monitoring policy and website
activation. Monitoring jobs 69/72 verified fresh Linux/ICMP data and disabled
inherited Apache checks in place. AIOps problem guard `ba7785d` rejects recovery
and unknown events; general AI repair remains disabled pending the concrete
private-runtime prerequisites in `bead-wd-72f.33`.

The current Beads overview and full encrypted recovery records are refreshed
together. These documentation changes do not alter the tested runtime revision.

## Preserve receiving-instance trust during selected configuration setup — 2026-11-04

Implementation `2ef4d42` fixes the first authenticated request in the normal
self-target selector. The installed AAP resolves its public hostname to its
internal listener, as required by the existing installer configuration. Its
execution environment already receives the matching authority through the base
installation's trust mounts. Supplying a public-only file as the native HTTP
module's complete CA bundle replaced that valid runtime trust and rejected the
internal certificate before any child configuration job could launch.

Read-only inspection reproduced the actual cached execution image, network mode
and trust mounts. Its default trust and the installed instance authority both
verified the internal peer; the public-only supplemental bundle did not. Their
union verified the same peer. No HTTP credentials were sent during that probe,
and neither name resolution nor certificate validation was bypassed.

The selector now validates the declared supplemental CA, preserves the active
default PEM trust bundle and appends the existing source credential's CA material
in a private temporary file. Certificate and trust metadata are retained. Native
HTTPS requests and source SDK operations use that same scoped bundle, matching
the existing Python source client's additive trust behavior. Global trust,
installer host entries, source credentials and target authentication are unchanged.
Authentication now runs inside the existing cleanup block, and the later private
checkout reuses that workspace. Separate allocation results prevent a skipped
Ansible register from discarding the existing workspace and leaking its file.

The native configuration role also serialized a verified inventory counter as
canonical decimal text. The identity filter now normalizes that representation
locally, retaining physical VM, route, UUID, address, key and hypervisor checks.
It rejects booleans, floats, zero, leading zeros, signs, whitespace, Unicode
digits and oversized values without modifying inventory or token records.

Twenty-six focused tests passed: eight real TLS/native cases, thirteen selector
checks and five inventory identity checks. Fixtures cover both native modes,
default trust with an unrelated supplemental CA, declared private trust,
malformed/untrusted certificates, hostname and running-job rejection, actual
SDK launch/wait, private file permissions, workspace reuse and early-failure
cleanup. Syntax, strict production lint across six files, whitespace and
added-text privacy checks passed. A normal target selector retry remains the
separate end-to-end acceptance step; this implementation launched no job.

## Make AutoDeploy configuration portable between AAP instances — 2026-11-04

Implementation `a522e7b` follows the owner's decision to retain the four older
production stage templates and their history while excluding that family from
future configuration bundles. The same four playbooks remain behind the newer
stages. Read-only extraction now supports explicit reviewed source exclusions;
an excluded resource still referenced by a retained object stops extraction.
It does not delete the original source objects. The coordinated encrypted
capture changes also remove the original Machine key and clear saved targets;
their publication and normal import are separate deployment steps.

The existing selected-use-case launcher authenticates to its source using the
already injected API credential and verifies the actual running job before
launching its existing prerequisite/import templates. The destination uses the
existing instance-indexed token store. Self and remote targets share this path;
no installer-password lookup, temporary token, wrapper or additional store is
introduced. A receiving AAP's source credential must point to its own API.

Stage 01 now verifies the consumed primary reservation and exact guest identity
before the existing isolation helper grants public installation HTTPS and
guest-to-own-hypervisor API TCP 443. The existing Git/API publication transaction
persists that permission and placement across maintained encrypted captures.
Other guests, released clients and production protection remain intact. Failed
early publication restores exact prior runtime/permanent native rules; durable
publication remains available for an idempotent source-synchronization retry.
The existing base stage has a bounded installation-access repair tag that ends
before ordinary base configuration. Its launch must accept the requested tag.
Mixed destination/port cross products stop rather than add implicit grants.

Inventory display labels use the agreed format while the existing physical
VM name remains the allocation and token key. Verified `vm_resource` provenance
connects those identities for authentication, callbacks and retirement. An empty
saved stage key accepts the existing registered-route handoff. The main and
recovery inventories remain mandatory. An undeployed optional Hactar inventory
alias may be absent only with a genuinely empty query and verified administrator
visibility; present aliases retain identity checks and their canonical encrypted
policy still updates.

All 275 regression tests passed before the final two empty-key fallback changes;
the four focused alias tests then passed with native handoff coverage in both
Jinja modes. Both native importer-render modes, Stage 01/04 syntax, strict
production lint across 31 files, whitespace and added-text privacy checks passed.
Tests cover actual native task execution, exact permissions and rollback, real
encrypted Git publication/retry, physical/display ownership and read-only
exclusions. These results validate code and candidate rendering. A normal CaC
import, permission repair and complete independent recovery cycle require their
own live acceptance; this change did not allocate or remove a VM.

## Preserve activation variable text during repeat imports — 2026-11-04

Implementation `8c0af1c` fixes a formatting change at the existing activation
task boundary. A declared serialized empty mapping with its trailing newline
became a dictionary during Ansible templating. The native string argument then
contained different text, so an unchanged activation appeared to need an API
update. The disabled definition accepted that update; the running website
definition failed during the normal configuration refresh.

The task now explicitly preserves non-null values as strings. Null and omitted
values retain the native module defaults. The existing module, API transport,
enabled-state guard, Event Stream bindings and protected logging are unchanged.
Genuine definition differences still follow the native update path; no automatic
stop or restart is added to make an update succeed.

Read-only reproduction used the source execution image, Core 2.16.19 and
ansible.eda 2.13.0 with recorded GET responses. Preserved arguments produced no
writes for both real definitions, while deliberately changed variables still
requested an update. Eight focused regressions pass, including actual task
rendering in both Jinja modes, null/omitted values and native Event Stream/state
handling. Syntax, production lint and whitespace checks also pass. Live
acceptance is checked through the existing normal configuration import job.

## Configure each AAP instance's own hypervisor connection during base — 2026-11-03

Implementation `931edb8` follows the owner's explicit request to fix the
automation rather than rely on a manual firewall exception. Existing Hactar
base jobs correctly enforce empty-host or complete saved-VM recovery guards;
neither describes an already running hypervisor containing newly created CaC
guests. Those global guards remain unchanged. The normal AAP base stage already
has the selected primary ownership, pinned Machine connection and existing
encrypted/source publication credentials, so the necessary connection belongs
in that stage's existing inventory publication block.

The selected AAP identity must match its existing HTTPS approval, actual guest
UUID/disk/interface/network/lease and the pinned hypervisor. Every saved and
running guest definition is checked against enforced bridges and device
restrictions before changing only the guest-to-own-host management TCP grant.
The existing native firewall and atomic nftables isolation helper apply and
verify it. Local failure restores prior state; interrupted later publication
can retry only the exact independently derived permission. No new job, scope,
credential type, key, persistent store or installed service is introduced.

The same existing compare-and-swap callback independently reads primary AAP
ownership and updates encrypted recovery/shared/Hactar policy declarations and
their source API equivalents. Existing token records and unrelated use cases
are retained. Native Ansible testing also established why original play-level
credentials and policy must be captured before delegation: `vars_files` values
are not automatically available through `hostvars`. Protected, noncached job
facts carry those existing values through the pinned connection.

The already implemented Assistant importer was also registered in the existing
selection catalog using its existing project ID and configuration key.

Sixty-eight focused checks passed, including native effective SSH/delegation,
identity/device and policy guards, check mode, local rollback, real encrypted
Git with interrupted source synchronization, token reuse, decommission and
selection. Stage 04 syntax and strict production lint passed. These are code
validation results; live application and connection proof are separate normal
job outcomes controlled by the coordinator.

## Read application VM ownership from the existing source inventory — 2026-11-03

Implementation `f0a70c2` follows the owner's decision that AutoDeploy secrets
contain only AAP configuration and primary AAP ownership. Application CaC
belongs to its use case. Generic decommission therefore reads related ownership
from verified `vm_resource` data in the existing source AAP inventory, using the
already attached API credential rather than another repository/token/store.
Only decommission enables this read; ordinary registry lookup does not load the
API client or gain an API dependency.

The fixed encrypted shared capture identifies the inventory and pinned
hypervisor. Related names, counters, address, UUID, disk, MAC, bridge, machine ID
and keys must agree across the source row and its complete verified artifact.
Final publication independently rereads those records and compares them with
the same running job's protected preflight. Application ownership is retained
only in job memory and never written back to central allocation. Existing
credential types, job templates and ordinary import logic remain in place.

Optional guests can be undeployed, and later cleanup may find source rows
already deleted. Such absence requires no actual VM or either bounded disk
variant, plus verified surviving ownership of every remaining permission.
Unknown grants and tampered extant rows stop cleanup. Source policy aliases
are patched and read back before any guest ownership deletion; this preserves
the evidence needed if an API update fails. A fresh retry can reconcile a
lagging API policy only when removal of its verified selected identities yields
the exact encrypted desired policy, preserving all unrelated permissions.

All 63 focused cases pass: 16 key/source, 21 decommission and 26 allocation/routing.
They include real encrypted Git with AAP-only central data, API independence of
normal reads, foreign metadata refusal, absent optional roles, hidden disk
variants and fresh-job recovery after partial source deletion. Syntax, strict
production lint and added-text privacy checks pass. The coordinator also
verified actual source metadata with a GET-only lookup against an in-memory
AAP-only allocation. No destructive job or inventory naming change was run;
the separately coordinated private-data migration remains a distinct step.

## Keep complete ownership and retire only verified deployment permissions — 2026-11-03

Implementation `fc85d29` completes the selected deployment's permission cleanup
within the existing decommission job. The recovery layer protects restored
production state, so retirement must remove only the proven selected guests'
local and installation HTTPS permissions while preserving other clients and
normal isolation checks. Ownership preflight precedes shutdown; exact native
runtime/permanent rules and the existing atomic isolation policy are cleaned
before VM definitions and external resources are removed. Failed local application
restores the captured policy and stops before deletion.

The owner required retryable cleanup without a new service, state store or
publication phase. Decommission therefore accepts only the declared canonical
policy or its exact removal result derived from recorded guest identities. The
existing final Git/API action updates the maintained encrypted policy aliases,
shared and recovery captures, related guest rows and source inventory. It checks
all source targets before publication, preserves literal JSON variable wrappers,
shared credentials and consumed allocation history, and rereads concurrent state.
It refuses foreign identities, omitted selected grants and new permissions.

Future primary VMs now retain complete ownership automatically in the same
encrypted route transaction. Stage 01 first authenticates read-only through its
generated guest keys and pinned hypervisor jump, using the existing environment
login. Original-host variable references prevent delegation from losing the
route; effective connection overrides fail before authentication. Actual domain
and network XML supply exact UUID, disk, address, MAC and bridge evidence.
The allocator preserves other resource roles and refuses conflicting known
identity. This retains proof after a later partial cleanup has removed the VM
definition, without another registry or credential design.

The complete vendor-path suite passed 218 cases without skips. Subsequent guard
changes passed all 26 allocation/routing and 12 instance-key cases; the coordinator
independently passed 20 decommission and 12 instance-key cases before approval.
Both playbooks pass syntax and scoped strict production lint passes 12 files.
Tests include real encrypted Git, fake source APIs, native delegated SSH option
resolution, check mode and local rollback. No new VM or live decommission was
launched for validation; successful code publication does not claim those proofs.

## Register instance inventory alongside existing token publication — 2026-11-03

Implementation `3dd7f5a` uses the same approved base callback to register the new
instance in the existing encrypted shared inventory and source Controller.
Selection by instance name requires an explicit FQDN and hypervisor placement;
requiring a separate manual inventory update would leave a successful new token
unusable by project imports. The callback preserves other hosts, variables and
group memberships, including literal JSON tags, and places no token in inventory.
Existing Git writer, source API and Vault credentials perform this update.

The same implementation accepts independently declared exact local guest TCP
permissions in policy checks and published placement. Hactar applies those
permissions separately; AutoDeploy verifies the complete existing policy. Empty
lists preserve previous behavior and no automatic network grant is introduced.

Validation comprises 192 full-suite cases, eight publication/literal-tag
regressions and twenty allocation/routing cases, with production task lint.
Actual new-instance base publication remains a separate runtime acceptance check.

## Resolve delegated SSH settings from the original guest entry — 2026-11-03

Implementation `faf64bc` fixes proxy publication after successful AAP installation.
Ansible evaluates SSH connection variables in the delegated hypervisor's context,
but the selected instance route belongs to the original guest inventory entry.
Explicit `hostvars[inventory_hostname]` references retain that route and its exact
management address, account and port. The machine-ID guard and strict host-key
validation remain enforced.

The regression executes actual Ansible delegated connection resolution with the
route present only on the original entry and an isolated SSH fixture. Thirteen
TLS/proxy cases and production lint pass. A live publication-only retry then
succeeded, and independent checks confirmed trusted public HTTPS, upstream
authority/SNI verification and a valid nginx configuration. Temporary diagnostic
Job Template settings were restored afterward; installation was not repeated.

## Retry verified upstream publication without repeating installation — 2026-11-03

Implementation `ec1aed8` adds the `aap_upstream_tls` tag after the vendor installer
had independently returned zero and its installed Gateway passed a trusted local
HTTPS check, but proxy publication failed. The initial route selection and pinned
SSH setup always run. The tag excludes preparation, installation and the async
observer; untagged installation retains all phases. A real Ansible task-listing
fixture verifies this separation alongside existing TLS and rollback tests.

Only the non-secret machine-ID command has an opt-in diagnostic result. All
credential-handling tasks remain protected and diagnostics default to disabled.

## Verify configuration import separately from application execution — 2026-11-03

Rendering implementation `617fd15` and native TLS-input fix `f4c5b5b`, together
with an explicit native API request timeout and the existing reviewed PAH
prerequisite preparation, allow the AIOps configuration import to finish on a
fresh recovery controller. The prerequisite stage supplies only the approved
collection pins and retains existing content. Independent target API readback
checks the declared Controller and EDA resources, successful project syncs and
both activation definitions disabled.

This result establishes configuration deployment. It does not establish functional
remediation: the importer launches no application Job Template or activation.
Existing supplied API credentials and persistent EDA Controller access tokens
remain in place. No new deployment architecture or security exception is needed
for these focused corrections.

## Preserve native credential TLS flags in registered-instance checks — 2026-11-03

Implementation `f4c5b5b` converts the native credential's Verify SSL
value to an Ansible Boolean before applying the existing pinned DNS/TLS guard.
The managed credential injector emits `True` as a string; the guard previously
accepted Boolean true or lowercase `true`, causing prerequisite preparation to
stop despite enabled verification. The real guard is tested against native
Boolean/string inputs, disabled TLS and conflicting DNS answers. All eleven
routing tests and changed-task production lint pass. DNS pinning, IPv6 refusal
and trusted HTTPS remain enforced.

The same deployment iteration identified an omitted native credential Request
Timeout: its empty injected value fails the configuration role's numeric argument
schema. Explicitly setting the existing credential to ten seconds preserves its
token and grants. Current operator guidance also requires the existing reviewed
PAH prerequisite selection before first project import on a fresh controller.
This supplies declared collection pins without launching application workloads.

## Resolve resource templates when survey inputs are protected — 2026-11-03

Implementation `617fd15` fixes the first AIOps CaC import validation failure.
Controller marks survey values as protected text. Passing the entire variable
mapping into one Jinja normalization expression propagated that protection to
unrelated nested resource values, leaving an Event Stream organization expression
unresolved. A controller-side action now reads and renders only the declared
resource lists before existing validation. Explicit literal injector templates
remain protected; no validation rule or authentication behavior is weakened.

The failure was reproduced with the actual encrypted AIOps capture and protected
survey input in both templating modes. The fix passes all eleven importer tests,
including all five real captures, and the existing production execution image
with networking disabled. The failed live jobs stopped before CoP resource roles
and did not change target configuration. Live deployment remains a separate check.

## Name the temporary VM-registry writer explicitly — 2026-11-03

Implementation `0399e2a` uses the exact owner-selected credential name
`VM allocation git Pseudo CMDB writer` throughout current operator guidance.
The matching encrypted configuration uses this name for the credential and all
saved template/dependency references. The owner approved replacing the used
production credential with one of the existing `Cac_git_token_type`, then
explicitly chose deletion of the retired credential after the replacement is
verified. This supersedes the earlier proposal to retain that credential.
Job records, template IDs and workflow links remain; the unused test writer can
change type and name in place. Separate read tokens and grants are preserved.

## Use the existing Git type with a distinct writer token — 2026-11-03

Implementation `64a197e` follows the owner's decision to use `Cac_git_token_type`
for the separate allocation writer, with the replacement write token supplied
in encrypted shared base. Repository readers keep their own read-only tokens.
The writer uses `CAC_GIT_TOKEN`; allocation and extraction read the fixed
repository URL from encrypted project runtime configuration using the same
protected naming rule as registry reads. Launch variables cannot redirect it.
The extraction template therefore also needs its existing environment Vault.
Obsolete writer environment names and the old host-registry token fallback are
removed. No wrapper, extra credential type or repository permission is added.

All 173 regression tests and changed-playbook production lint pass. Actual
GitHub write-service authorization accepts the writer and refuses the reader
without changing repository state. Native fixtures cover concurrent encrypted
reservations, check mode, launch overrides, wrong Vault keys and secret logging.
The existing test-controller writer changed type in place, preserving its ID,
other objects and grants. Production rejects changing a credential's type when
it has job history; such a migration requires an approved replacement with
active assignments updated and the original credential retained for history.
The owner must approve creating that replacement. No VM or use-case job is run.

## Reuse the AutoDeploy CaC read token for registry reads — 2026-11-03

Implementation `328c982` follows the owner's approval to replace the separate
instance-registry reader with the existing AutoDeploy secrets repository read
credential. The registry action uses `CAC_GIT_TOKEN` and derives its fixed
repository from encrypted project runtime configuration, so launch variables
cannot redirect the token. Preparation retains its saved repository pair and
adds only the registered Machine credential. Existing ownership pins remain.

The existing read token successfully read the current registry ciphertext.
Real Ansible/Git fixtures verify encrypted configuration, rejected wrong keys,
ignored launch namespace overrides and preserved host routing. The full suite
passes 171 tests; production lint and source checks pass. Five live consumer
definitions and companion dependencies follow the same credential selection.
The allocation writer and token permissions are outside this change.

The owner separately requires a real CMDB instead of the temporary Git/YAML
registry. That requirement is tracked in `bead-wd-sc8` and the work plan; no CMDB
product is selected or implemented by this change.

## Use the repository CaC Vault for registry encryption and decryption — 2026-11-03

Implementation `eb6b214` follows the owner's explicit instruction to reuse
`aap_autodeploy_configascode-secrets CaC vault cred` for the instance registry.
Preparation retains that saved credential and adds only the registry reader
and pinned Machine credential. The selector no longer selects a separate
registry Vault. Existing repository-pair ownership checks remain in place.

The maintained shared password decrypts the current registry without changing
its ciphertext or reservation history. Real Ansible/Git fixtures read a registry
with only its `cac` key and refuse an unrelated key. Forty-nine focused checks,
selector syntax and production lint pass. Companion configuration stops creating
or attaching the redundant Vault entry. No credential object is deleted and no
key is rotated; custom Git credential types remain unchanged.

## Use direct project selection and explicit CaC deployment names — 2026-11-03

Implementation `b5fb34b` removes the five unused wrapper playbooks. The owner
requires every project Job Template to call `deploy-cac-project.yml` directly
with its fixed `aap_cac_project_id` in saved Extra Variables. Controller readback
confirmed that no production template referenced the wrappers.

The owner also requires a Deploy prefix. Because an existing application job
already uses an otherwise matching deployment name, the owner chose
`Deploy <Project Name> CaC` for all five configuration templates. The naming
helper, existing selector tests, documentation and encrypted references follow
that rule. Existing IDs, credential pairs and workflow relationships are retained.
Twenty-four focused checks and syntax checks for the importer and selector pass.
Compatibility layers are not implied by this design and require consultation
before being added. No use-case import or application deployment is run here.

## Propose one shared CaC importer without hiding preparation — 2026-11-03

Analysis `96ce498` compares all five importers, the selector and shared helpers
with installed CoP/native implementation. Ordinary resource data, different
capture layouts and duplicated authentication/cleanup do not justify separate
import engines. The proposed replacement is one resource-driven playbook, with
normal schema adapters and only demonstrated resource-level compatibility
handlers. Event Streams and workflow graphs are already supported; EDA project
field forwarding and asynchronous group ordering need specific attention.

Durable target service tokens require discovery, safe persistence and recovery;
native token creation alone is not idempotent and does not replace that policy.
Preparation, model authentication maintenance and child-job orchestration remain
explicit boundaries. One playbook also does not resolve credential injection:
repository pairs and destination API access must be bound before launch. Thin
repository templates can share the playbook until the owner agrees the pending
credential, self-target and orchestration design under `bead-wd-72f`.

Local role/module inspection and a synthetic zero-API activation probe identified
a disabled-state compatibility risk, tracked separately as `bead-wd-72f.4`.
This is not evidence that a live activation changed. The analysis also identifies
conditional secret logging to eliminate in any common path. Sixty-one source
links, an illustrative YAML schema and four version-policy checks pass. No
consolidation, runtime change, AAP job or live credential operation was performed.

## Bind configuration access to each repository — 2026-11-03

Implementation `7e5f672` and encrypted capture `4ab587f` replace the shared-entry
bootstrap with five independently named read-token/Vault pairs. Production
readers were renamed in place; the existing base Vault entry was retained and
four repository Vault entries were added with the same ownership/grant boundary.
The four use-case importers now bind their own Vault, while base stages, catalog
and extractor retain base access. The existing fresh instance has all five pairs
without changing runtime Vaults, registry access, token inputs or credential types.
All fourteen affected production template assignments, role grants, workflow
nodes, schedules and surveys were verified. Actual selector checks pass for every
importer and preparation using the encrypted pins. Eight bootstrap checks and ten
selector checks cover both native modes; generic regression checks and impacted
production lint pass. No import, deployment, rekey or target API redesign ran.
The corrected commented example provisions all five pairs in the local fixture.
The encrypted migration record preserves genuine before/after evidence; historical
names there do not define current bindings. Future multi-repository extraction
key routing is tracked separately as `bead-wd-72f.2`.

## Store the API DNS name explicitly in inventory — 2026-11-03

Source documentation `9003fb4` and companion capture `720710d` define an explicit
`ansible_fqdn` host variable for AAP instances. The owner confirmed that the
numbered instance in the request was an example, so only the existing verified
inventory entry was updated. Its DNS name comes from its already-recorded HTTPS
origin; no new VM, guessed suffix or remote fact gathering is involved.

Live readback and a decrypted comparison against the previous capture verify
that only this host variable was added. Other variables, group memberships,
capture records and literal tags are preserved. The public example parses as
YAML. The intended future lookup is launch-time instance name to stored FQDN to
verified HTTPS origin. This data update does not replace the existing registry
launcher or implement credential selection; that remains the next discussion.

## Limit this phase to inventory placement and future upstream TLS — 2026-11-03

Implementation `aaafed2` follows the owner's explicit stop boundary. Keep the
instance name as a launch-time input and add per-hypervisor VM placement groups
whose `hypervisor_host` variable resolves to an existing host in the shared
inventory. Companion capture `e3a171b` preserves original variables and functional
memberships. Existing aliases are retained to avoid colliding with service group
names. Actual Ansible inventory parsing verified all nine mapped VM entries.
Credential bindings, use-case execution, API delegation and replacement workflow
implementation are deferred until credential management is agreed.

The owner retained public UI/API access and prohibited production SSL changes.
Future Stage 02 therefore publishes a temporary 503 frontend until installation
provides the guest's public CA bundle through pinned SSH. Stage 03 verifies guest
health against that installed authority, binds nginx to the selected hostname and
CA, validates before reload and restores the prior instance configuration after
a publication failure. The small standard-library probe verifies a private
upstream address with its DNS certificate identity without changing DNS, global
trust or sending API credentials.

Eleven focused cases pass in both templating modes, including real TLS refusal
paths, real Ansible publication/rollback and validation-before-reload ordering.
Both nginx states pass in-memory syntax validation with the installed binary;
the infrastructure/install entry points and full trust task syntax pass, as does
scoped production lint. No existing proxy configuration or service was changed,
and no deployment job or fresh VM installation was run.

## Keep selected setup's seed identity and trust separate from its target — 2026-11-02

Implementation `0684007` fixes readiness failures found before the first selected
AIOps import. The execution environment lacked the seed's existing private
issuer, and source authentication inherited the fresh target's base password.
The selector now requires an explicit encrypted seed login. It reuses the
existing source CA file for source authentication, reads, job launch/wait and
temporary-token cleanup. Certificate/hostname validation stays enabled; the
target retains its normal trust and login. No global trust or DNS change is made.

Two existing source credential associations have no organization. Exact
encrypted source-local name/ID/type pins permit those already-reviewed inputs
without changing ACLs or moving credentials. Registered route credentials still
require the expected organization, and case Git/Vault boundaries are preserved.
These narrow source pins do not resolve the separate universal ownership design.

Four real-module TLS fixtures pass in both templating modes, covering verified
launch/wait/cleanup and secure refusal paths. Selector and login regressions,
syntax and production lint pass. Actual source/target API prechecks and scoped
credential calculation pass, with temporary-token revocation verified. The local
preflight used protected captures/route state and independently verified DNS
answers; it did not run registry Git fetch, private clone or child jobs. No
prerequisite, AIOps configuration import or application execution is claimed.

## Verify the AIOps companion cutover after scoped token input — 2026-11-02

Companion implementation `30aecfd` moves AIOps platform CaC to its own private
repository. The capture published in `2a22fbc` is byte-identical to its former
shared copy, including the Vault identity and all configuration values. The
operator supplied a dedicated read-only token; its verified repository read and
inability to read shared base precede legacy-copy removal. Encrypted base stores
that token, repository URL and independently named Git credential.

The seed importer changed only its repository default and Git association.
Its other survey/launch settings and Vault inputs, plus the separate preparation
and selector templates, were verified unchanged. Five encrypted capture bindings
and one external credential dependency changed; shared catalog/registry and
allocator bytes were preserved. Bootstrap implementation `3b6d48f` supplies the
optional credential on later base runs without replacing existing hidden secrets.

No AIOps import, activation or application job ran. The separate runtime
`myvars` remains in the public AIOps playbook repository; this verified split
concerns platform CaC. The broader ownership architecture remains undecided.

## Provision independent AIOps configuration access — 2026-11-02

Implementation `3b6d48f` adds optional `cac_bootstrap_git_credentials.aiops`
support to base bootstrap. It creates the independently named AIOps Git-read
credential while preserving the four existing Git inputs, the shared Vault
identity and existing hidden secrets on reruns. The CoP roles themselves are
unchanged. Six real local Controller/API fixtures pass in each native mode,
including the legacy path, the new credential and refusal of a masked input.
Stage 04 syntax and scoped production lint pass.

The owner requested a separate private companion repository for AIOps. Its initial
capture publication `2a22fbc` preserves the exact ciphertext and configuration
values from the existing shared file. The public playbook repository needs no
private Git token. The existing fine-grained base token can read its original
repository but cannot read the new companion, so a new repository-scoped read-only
token must be supplied through encrypted base. No broader credential is used as
a substitute and no existing token is replaced.

At this checkpoint the live importer and legacy capture are retained until the
new token is verified. Prepared repository/name bindings preserve the shared
catalog and allocator registry and pass encrypted roundtrip/literal-tag checks.
No AIOps import or application execution is claimed by these source changes.

## Keep complete object ownership open after the label audit — 2026-11-02

Documentation commit `1846f71` adds the requested TODO entry and API/UI label
capability table. The original idea was to use labels to map all CaC objects to
their owning project. Read-only API responses and the served UI code establish
that several resource types have no labels at all, while some API-supported
labels have no overview filter or only conditional launch controls. Labels
therefore cannot be the universal ownership mechanism; existing useful labels
are retained.

The owner requested new ownership ideas. Beads `bead-wd-72v` remains open and is
mirrored in TODO.md. It asks for comparison of an encrypted registry, supported
description markers, existing project/parent relationships and a hybrid approach.
The eventual design must handle shared resources, uncaptured manual additions,
renames, removals and changed runtime IDs across deployments, while preserving
CoP compatibility and secrets. No alternative has been selected or implemented.

The README links the backlog. Four existing version-tool tests, whitespace checks,
mirror equality and a changed-plaintext identity scan passed. These are
documentation and version changes; no deployment, extraction update or live
metadata modification was performed.

## Verify actual base configuration after protected tag repair — 2026-11-02

Actual base retry 3144 on source `59aa985` and encrypted base `f38a8cf` succeeded
in 125.097 seconds. Independent strict public-TLS administrator login, reserved
node identity, expected organization/types/base credentials/PAH repositories and
absence of advanced use-case objects were verified. Temporary run tokens were
removed. The fix in `4af4121`/`bef8921` required only the base retry; VM creation
and installation were not repeated. Follow-up optional captures restore 44
injector tags (AutoDeploy 4, Hactar 3, Windows 8, Assistant 29); actual vendor-role
local checks preserve every schema value and hide canaries without API calls.
Companion implementations are `0f42c79`, `ef849c5` and `0954190`. No live optional
import, credential refresh or AIOps change was performed.

## Preserve literal tags as part of encrypted YAML correctness — 2026-11-02

Actual fresh base configuration failed in the exact CoP wildcard merge. The four
new credential injectors were evaluated as playbook variables because ordinary
AnsibleDumper discards `!unsafe` markers, even though string equality survives.
Implementation `4af4121` adds a protected dumper and validates literal-tag paths
after Vault roundtrip; companion `bef8921` protects only the four base injector
scalars. Ordinary environment references and all logical values remain unchanged.
The actual encrypted base/myvars merge fails before and passes after locally
without APIs. Canary fixtures cover both native modes, and all 31 generic capture
fixtures pass. Protected logging remains enabled. Broader lint retains four
existing line-length findings in unchanged tasks; actual Stage 04 retry is pending.

## Verify the installed extractor with a real protected preview — 2026-11-02

Actual template 158 default preview job 3139 on `f38517a` succeeded in 44.042 seconds.
It reported zero conflicts/validation errors, retained a decryptable Vault review,
and performed no Git publication. The missing accepted baseline is explicit:
373 initial source/desired differences and seven code-graph differences need
review before initialization; they are not changes since a previous extraction.
The used reader remains intact beside the separately installed CA attachment.
The implementation and meaningful merge/deletion/secret fixtures are verified;
no actual baseline acceptance or update was authorized or run. Independently
read vendor common-role tasks/defaults also confirm Podman belongs to bundled
installer package setup, so its earlier absence does not require manual packages.

## Verify refined preparation readiness on the actual guest — 2026-11-02

Actual observer job 3135 on source `6932ebf` succeeded in 16.308 seconds:
preparation readiness passed, the supported expansion dry run proved available
capacity, and bundle/account/resource/tool checks passed. Strict HTTPS handshakes
verified all three declared endpoints; the two Red Hat services used already
installed RHSM authorities and no client credentials. Current installer readiness
remained false for unexpanded temporary space and the absent container runtime.
Infrastructure job 3133 independently succeeded. Implementations `3706770` and
`ba20ce5` preserve the preparation boundary; no complete AAP installation is
claimed. The broader local 122-test suite and additional already-installed
collection fixtures passed as documented in release notes.

## Capture custom credential schemas with their retained dependencies — 2026-11-02

The separate-CA fixture exposed a missing stable-field allowlist for custom
credential types. Implementation `04316b8` serializes name, description, kind,
inputs and injectors while omitting runtime IDs/management flags. The fixture
proves alias resolution, retained CA/type after removed associations and preserved
vaulted PEM input. Thirty-one generic fixtures pass. The actual separate CA-only
type/credential was created successfully and attached beside the untouched used
reader; no grant or global trust changed. Actual extraction preview is the next
required proof, and no initialization/update is claimed.

## Preserve used credential schemas and attach source trust separately — 2026-11-02

Actual Controller validation also refused input changes to the already-used
reader type. No live type or credential changed. Implementation `988d172`
retains that URL/token schema and provides a separate CA-only credential whose
required PEM uses the supported single-file injector. The capture restores the
original reader exactly, adds the separate credential/type and fourth extractor
association, and retains its dependency/alias. No access grant, deletion, global
trust or Controller constraint bypass is involved. Thirty generic fixtures pass;
actual creation and preview remain parent coordinated.

## Verify preparation results before starting installation — 2026-11-02

Implementation `ba20ce5` follows the observed copied-disk readiness gap: the
existing growth steps now validate the exact supported layout, refuse actual
errors, accept only explicit growpart NOCHANGE for idempotence, and require real
temporary capacity before subscription or installer tasks. The installer observer
path still skips preparation and starts no second installer. Starting a new async
installer is explicitly marked changed. Strict Stage03 production lint passes;
live preparation remains parent coordinated.

## Assess work at the phase that owns it — 2026-11-02

Actual guest verification found a correct bundle, supported root layout and
sufficient virtual disk, while the copied root partition remained small and a
container runtime was absent. Implementation `3706770` separates preparation
readiness from current installer readiness. A read-only growth dry run proves
whether existing preparation can supply temporary capacity; missing runtime tools
and vendor package-task references remain explicit. Red Hat probe retries use
only already installed configured RHSM authorities, with certificate/hostname
checks, bounded errors and no client credentials. Five audit fixtures and strict
production lint pass. This change neither installs packages nor grows filesystems,
and the subsequent actual audit must still verify preparation readiness.

## Follow the actual Controller single-file injector contract — 2026-11-02

The actual credential-type PATCH rejected a named-file mapping before any
credential changed. Implementation `652ca05` supplies the supported single
string `file.template` and `tower.filename`. A canonical portable schema and
strict Jinja rendering fixture cover missing, empty and populated optional PEM
inputs. The encrypted capture/private migration payload use the same definition.
This corrects API compatibility without changing trust or source identity.

## Reuse the existing source authority within the collector context — 2026-11-02

Encrypted execution-environment evidence proved the same source peer as the
trusted local route and missing issuer trust. An independently located issuer
already trusted by the workspace verified the same leaf with hostname checking
and no HTTP credentials. Implementation `1cfb86b` accepts that existing
authority through an optional credential file, added only to the collector SSL
context alongside default roots. Global EE trust, DNS and host files remain
unchanged; origin, redirects, certificate/hostname checks and invalid-input
refusal remain enforced. Twenty-nine generic fixtures and strict entrypoint lint
pass. A subsequent actual preview must prove extraction; no baseline acceptance
or repository update was performed by this change.

## Audit bundled installation readiness before guest changes — 2026-11-02

Implementation `e53878f` extends the existing registered-instance observer,
using its authenticated pinned jump route. It reads the configured installer
bundle, nonroot installer permissions, root layout and capacities, tools, OS and
resources, and tests credential-free verified Red Hat HTTPS handshakes. Protected
subscription/login inputs must be present without disclosure. Sizing follows the
local AAP 2.7 installation reference. Unsupported filesystem layout blocks the
existing fixed growth commands; it is not guessed or changed. The observer does
not benchmark IOPS, authenticate to Red Hat, register subscriptions, install
packages, grow disks or start the installer. Three fixtures and strict production
lint pass. Actual guest audit remains a separate parent-coordinated job.

## Declare narrowly approved installer HTTPS separately from target identity — 2026-11-02

Implementation `c365298` validates explicitly approved bridge/IPv4/MAC clients and
protected source addresses independently of the immutable registered hypervisor
pin. The default bridge/DNS policy remains unchanged; persisted host exceptions
are never treated as approval. The encrypted inventory capture retains the same
explicit declaration, verified against the approved host configuration. Seventeen
routing/allocation fixtures and scoped production lint pass. The same checkpoint
refreshes only the authorized DNS credential from its maintained encrypted record;
Vault roundtrip comparison proves every other environment input unchanged. This
is deployment readiness, not proof that infrastructure or installation ran.

## Collect encrypted TLS route evidence before changing trust — 2026-11-02

Actual execution-environment preview confirmed certificate trust failure while
the same source-reader inputs verified locally. Implementation `3eb4edf` retains
only encrypted DNS/host-file/trust-path and verified-SNI peer evidence after that
failure. Diagnostic probes send no HTTP/API credentials, accept no untrusted
certificate and change no DNS or trust policy. Evidence must be compared with
independently trusted source identity before choosing a repair. Tests prove zero
diagnostic HTTP requests, unchanged certificate/hostname verification and Vault
encryption of failure artifacts; all twenty-eight focused fixtures pass.

## Keep certificate package ownership in shared baremetal base — 2026-11-02

The user clarified that certbot and its nginx plugin serve several hypervisor
applications and belong in Hactar's shared base OS. Implementation `a184012`
therefore adds only a read-only installed-RPM readiness check to infrastructure,
after exact hypervisor validation and before certificate/account checks. Missing
packages produce a clear base prerequisite failure. AutoDeploy installs no
packages, registers no new account and preserves the legal approval guard.
Infrastructure syntax/scoped strict production lint pass; live installation and
certificate proof remain parent-coordinated.

## Classify actual Controller GET failures without exposing requests — 2026-11-02

The next real preview reached a controlled Controller-read refusal. Exact source
reader inputs verified successfully through local trusted TLS, so implementation
`b2c5366` distinguishes endpoint family and HTTP status from TLS trust, DNS and
connection failures in the execution environment. URLs, query values, server
error bodies and authentication headers remain protected. Twenty-seven focused
tests pass, including HTTP/TLS secret-canary failures. Runtime extraction remains
unproved until a later actual preview succeeds; no baseline/update was run.

## Preserve protected diagnostics through actual Ansible task execution — 2026-11-02

The first real extractor preview failed before its protected action could report
an actionable reason. Raised `AnsibleActionFail` bypassed the task's
`failed_when` handling, leaving only censored output. Implementation `09fe5a9`
strictly normalizes Boolean survey strings inside the action and returns bounded
refusals for the separate public failure task. Protected source/Vault/Git inputs
remain under `no_log`; unexpected failures expose only a controlled stage and
exception class. No access, checksum, TLS or Vault control is relaxed.

A real entrypoint fixture runs through Ansible task templating in both native
modes, covers false/false, false/true and true/true publication choices and proves
the safe reason reaches the failure task without the secret canary. All twenty-six
focused tests pass. A subsequent actual preview is required before declaring
the installed extractor operational; no baseline initialization/update was run.

## Resolve portable credential namespaces before fresh import — 2026-11-02

Implementation `e8ab5ac` and companion `0c1cc64` align shared external aliases and
the five new isolated recovery/observer definitions with the environment Vault
name actually created by the captured use case. The earlier manual capture kept
the source-only name for those references, which would be unavailable on a fresh
controller. Actual seed credential IDs/scopes are preserved; only encrypted
blueprint references change. Every one of nineteen templates now resolves its
credentials against actual captured or base-bootstrap definitions. Twenty-five
focused fixtures pass, including portable external-alias recognition.

## Preserve accepted association intent when source membership changes — 2026-11-02

Implementation `5583f42` applies unordered association and workflow-node deltas
to accepted desired state. A source credential removal must not discard portable
writer/Vault associations that intentionally exist only in CaC. Desired-only
members and excluded source nodes retain their baseline intent. Arbitrary lists
inside variable/input mappings keep meaningful order even when their keys are
named like Controller associations. Retained dependency metadata is name-sorted.
All twenty-five focused fixtures pass, including both regressions and real
encrypted Git update/removal behavior. No production baseline/update was run.

## Review complete owned state before updating encrypted CaC — 2026-11-02

Implementation `055b9dc` adds `capture-aap-cac.yml` and bounded Controller API
adapters. The existing exporter requires an additional dependency and does not
provide the accepted-source/accepted-desired merge or complete-visibility deletion
contract, so this path uses the existing Python/Ansible runtime and GET-only
transport. Every source/related URL is pinned to the exact TLS origin and
Controller prefix; redirects, incomplete pages and nonadministrator visibility
are refused. Owned project/label families discover additions without an old ID
list. Stable names and parsed YAML/JSON variables exclude runtime noise.

Separate encrypted source and desired baselines preserve intentional namespace
differences, exclusions and pending desired edits/deletions. Removals include
resources and associations. Conflicting changes require review, and masked new
secrets need recoverable inputs. Existing masked secrets and reordered password
survey defaults keep their vaulted values; masked rotations remain unknowable.
Accepted dependency names remain owned independently of job associations, so an
unlinked but existing definition is not mistaken for a deleted resource.

Reviews bind actual code revision/content and validate own playbook paths. The
base graph is compared through its narrow code-owned adapter; changes requiring
source adaptation block acceptance. No arbitrary playbook AST rewrite, source
configuration apply or application job launch occurs. First initialization and
updates require an exact fresh review digest. Encrypted Git publication is
explicit, refuses unrelated staged work, never force-pushes and excludes the
allocator-owned state file.

Companion `77e7cf3` stores the initial encrypted AutoDeploy ownership adapter,
source-reader/type and preview-default extractor definition, bringing its capture
to nineteen templates. Other scopes state their missing adapter boundaries;
saving those definitions does not prove live AAP installation. The 116-test
regression passed and all 23 focused tests pass in both native modes. Scoped
strict lint and syntax pass. Local production GET-only preview succeeded without
publication or AAP mutation; accepted baseline initialization and actual AAP job
availability remain separate runtime steps.

## Pin selector authentication origins — 2026-11-02

Implementation `85e7307` and companion `4593bd6` require the orchestration seed
to match the encrypted reviewed origin and require catalog access to match the
registry-reader credential's repository before authentication. This keeps
operator survey values from redirecting protected seed/Git inputs. Nine selector
tests pass; target instance and scoped credential selection remain unchanged.

## Match captured prompt policy to the guarded selector — 2026-11-02

Implementation `70b1661` and companion capture `3daa17e` disable arbitrary
variable prompts on all six existing configuration importers. The bounded
surveys stay enabled and credential prompting is retained for the selector's
validated scoped associations. Parent API readback found the earlier live/capture
setting was permissive and would fail the selector's existing guard. A real
preflight fixture now rejects that mismatch as well as missing target questions.

## Complete surveys that previously exposed diagnostics only — 2026-11-02

Parent API preflight found three importer surveys that had only the logging
question, so renaming an existing URL question did not add the required instance
key. Implementation `17c5efb` adds a capture preflight for every fixed importer;
companion `729b3f2` gives all six required key/repository/debug prompts and removes
stale saved target URLs/addresses while preserving other scoped inputs.
Nine selector/label tests pass, including real missing-prompt rejection and a
complete-survey acceptance fixture. No use-case import was launched by the fix.

## Select registered targets without replacing case credentials — 2026-11-02

Implementation `c1d60b7` replaces free-form target URL surveys with an exact
completed registry key in the selector and standalone configuration importers.
Every importer derives its public API and private SSH route before connecting.
The selector verifies the saved non-Machine credential names/organization,
preserves their Git/Vault boundaries, adds only the fixed registry dependencies
and registered Machine, and verifies actual completed job associations/results.
A distinct `instance_registry` Vault identity avoids collisions with a case's
`cac` secret. Credential prompting is limited to these validated setup launches;
free variable prompts and application job execution remain disabled.

Companion capture `cbe5b7a` retains eighteen templates, including separately
bound recovery phases and a read-only observer, with their exact protected
inventory/host/group and recoverable Machine dependency. Optional captured
groups are restored without broad inventory rewriting. All template labels are
defined. Allocator-owned runtime state is unchanged.

API checks additionally reject alternate IPv6 records and disabled TLS overrides
because either could send credentials outside the pinned IPv4 route. The full
95-test regression passes; sixteen routing/allocation and nine selector tests
pass in both native modes, including distinct Vault identity and credential
removal/substitution refusal. Ten entrypoints pass syntax checks and scoped
strict lint passes; broader prerequisite lint retains four older line-length
findings. Actual isolated creation and read-only guest login/sudo succeeded,
while certificate issuance, installation and selected setup remain unproved.

## Verify authenticated guest access separately from installation — 2026-11-02

Implementation `0079680` adds a read-only registered-instance observer. A strict
host-key handshake establishes the peer key, while guest login and sudo require
their own proof. The observer uses the same protected route and attached
environment/Machine credentials, reads minimal facts and both machine-ID paths,
and retains bounded identity evidence for comparison with protected golden/source
records. It changes no machine identity, package, filesystem size or subscription.
Syntax and scoped strict production lint pass; actual login results must be
reported separately from this source validation.

## Bind later setup to registered routes — 2026-11-02

Implementation `b780524` makes Stages 02–04 resolve one completed instance from
the latest encrypted allocation registry before target connections. A separate
read-only credential avoids replacing a use-case's scoped configuration token.
The instance key determines the VM name, private address, public API URL, SSH
public keys and hypervisor; conflicting workflow/caller values stop execution.

Private subnets may overlap across hypervisors, so guest installation and
installer-password/MCP observers always jump through the pinned hypervisor with
strict host-key checks on both hops. API authentication uses this VM's public
hostname only after exclusive DNS and trusted TLS checks. Infrastructure reads
the exact reserved DNS record and refuses an existing conflicting address. It
uses the pinned hypervisor public address and limits proxy/certificate paths to
the reserved hostname. Existing certificates or separately approved ACME
registration are prerequisites; this stage never accepts new terms.

Fifteen allocation/routing tests pass in both Jinja native modes, including real
Git-backed read-only lookup, stale/unknown-target refusal and delegated inventory
routing. Stages 02–04 pass syntax checks; Stage 02 and route tasks pass scoped
strict production lint. These local checks do not prove certificate issuance,
installation or base configuration on a real target.

## Reserve shared names before isolated recovery provisioning — 2026-11-02

Implementation `98f491a` replaces independent local allocation with normal
conditional Git publication into a separate encrypted allocation-state file.
The owner requires globally unique test names across hypervisors and no reuse
after failed provisioning. Old counters remain migration evidence. The state
file is separate from ordinary CaC so later capture updates cannot reset it.
Encrypted companion change `8bebb0a` seeds the reviewed floor and defines the
portable writer in shared base without an optional recovery-case dependency.

The isolated Stage 01 verifies SSH keys, physical identity and live persistent
isolation before reservation and again before startup. It changes only a newly
copied disk, generates fresh guest SSH/machine identities, cleans only its local
copied RHSM identity with appliance networking disabled, and observes its exact
local libvirt domain. Public trust/routing artifacts survive later job failure;
the complete route is retained in the encrypted registry.

Thirteen tests pass in both native modes, including competing real Git writers
and the native action with distinct default/cac Vault passwords and check mode.
Workflow artifacts, Stage 01 syntax and scoped strict production lint pass.
This checkpoint permits only independently bound isolated Stage 01 execution.
Later installation/API routing and live provisioning proof remain separate;
older unbound downstream stages must not be chained automatically.

## Match Controller survey default types — 2026-11-02

Implementation `725e33d` fixes empty multiselect defaults to strings after the
actual Controller API rejected an empty list. The shared importer preflight now
refuses that invalid shape, with real Ansible regression fixtures. Encrypted
capture correction `e5d61b3` matches the accepted/read-back selector and
prerequisite surveys. This metadata correction launched no configuration jobs.

## Keep base deployment separate from selected use cases — 2026-11-02

Implementation `2338422` stops the deployment workflow after stages 01–04.
The owner explicitly chose platform base first, followed by an operator-selected
mechanism that installs selected umbrella Projects and their Job Templates/
related CaC. The selector uses only fixed owned configuration importers, preserving
each importer's scoped Git/Vault credentials. It verifies separate seed/target
instance identities and actual child-job completion. Four umbrella modules have
reviewed captures/importers; six report their missing capture/importer explicitly.
The two standalone projects outside umbrella membership are not silently added.

Every importer now checks project label assignments and organization-scoped
label definitions. Selected prerequisite preparation remains outside base;
AIOps imports leave activations disabled. Encrypted central capture `205e2da`
adds the selector definition and standalone recovery objects; Windows `57ca87e`
adds its regression verifier and labels. Assistant changes `ae00634` and
`4962934` complete ordinary and separately gated maintenance labels.

All 79 repository tests pass. Eight new safety/label tests pass in both native
modes, the modified entrypoints pass syntax and new YAML passes strict offline
production lint with zero findings. Private roundtrips/comparisons preserve
unrelated secret inputs. These are local code/capture changes; no live selector,
configuration import, application job or fresh deployment ran.

## Keep a Git-tracked session restart entry point

Documentation implementation: `fa10dfd`.

The operator requested RESTART_HERE.md in Git so a new chat can recover this
project's goal and find its plan, setup and decision history. The README links
to that entry point. It documents that the existing backlog has not yet been
migrated to Beads and directs subsequent tracking there; it does not create a
second task list. It contains no secrets or environment-specific access values.

Restart-document links, version consistency, whitespace and staged-content
checks passed. No automation or deployed configuration changed.

## Document the AD runtime proof separately from configuration import

Windows presenter guide: `0b46f96`; service identity checks: `60a8531`.

The receiving-platform import restored the definitions and target credential;
separate runtime stages then verified applicable Server patching, directory
promotion, identity nesting, synchronized time and LDAPS/gateway trust. The full
live verifier passed all twelve logins, 48 scoped grants, 192 regional access
checks and twelve completed mock jobs. Documentation now links the beginner
VNC/browser presenter guide and explains that AD selects membership while
Ansible maintains AAP resource grants. No importer behavior or encrypted capture
changed for this documentation update. Complete fresh infrastructure deployment
and live membership revocation remain separate proof.

## Verify trust from certificate files with Unicode comments

Implementation: `e9e892a`; encrypted project refresh: `e4f2d29`.

The installed public bundle contains Unicode comments, which Python's inline
PEM interface rejects. Loading the installed certificate files preserves the
full bundle and required HTTPS chain/hostname verification. That check passed
in the focused import, which subsequently succeeded after the Windows project
was refreshed before template validation. Independent API reads confirmed all
32 templates, 29 nodes, target binding and file injectors; the imported static
verifier also passed all 48 regional grants. Infrastructure provisioning and
LDAP login verification remain separate from configuration import.

## Diagnose the public trust read while protecting authentication

Implementation: `4772b6b`.

The initial refreshed Windows import stopped during public trust collection.
The existing diagnostic choice now exposes errors from that public-data command
while passwords, decryption and credential writes remain protected. The retry
identified Python's inline PEM interface rejecting non-ASCII comments in the
installed CA bundle. A transient PAH service error also interrupted a source
sync; the existing PAH endpoints recovered and remained the collection source.

## Reuse installed platform trust for the AD target credential

Implementation: `1f75e14`; encrypted Windows capture: `6d2c9c4`.

The platform's own issuing CA can live in its installer-generated trust bundle
rather than host trust alone. Read both public bundles over the existing SSH
connection and require normal HTTPS chain and hostname verification before
storing the target credential. Reuse the established containerized-installer
trust path, allow an explicit protected override for another verified layout,
and supply existing sudo authentication. No certificate checks are disabled.
Python/YAML parsing and importer syntax passed. The capture's actual CoP
combination verified fresh target bindings and deferred credential injectors;
live import and infrastructure deployment remain separate validation.

## Bind Windows AD configuration to the receiving platform

Implementation: `e6bf9bd`.

Fresh Windows imports must configure their own platform rather than reusing a
dedicated validation instance's API and SSH settings. An optional encrypted
capture flag prepares a target-specific credential using the existing installer
SSH connection, public trust and the current administrator identity. HTTPS
hostname and chain validation precede credential creation. The importer still
restores definitions only and rejects launches and schedules. Syntax, Windows
configuration guards, group-ordering and version-policy tests passed; live
AD deployment and a fresh-target import remain separate proof.

## Consolidate the current work plan and separate completion from proof

Documentation implementation: `591fc43`.

The operator requested an understandable TODO list with context, reasons and
completion goals, and completed work at the document bottom under `Done:`.
Older lists mixed historical design, completed implementation and unverified
behavior. PLAN.md is now the single task list, with numbered areas/subtasks;
the overview and README link to it instead of maintaining competing checklists.
Earlier plans remain recoverable in Git and this decision history.

Completion was reconciled with the protected deployment handover and full
production/replacement comparison, not inferred from source code alone. Fresh
base, bootstrap/MCP provisioning, all five imports and initial comparison are
marked done with their limits. Full-workflow execution, recursive deployment,
functional tests, live rerun preservation and takeover remain open. Remaining
comparison findings are explicit decisions/tasks. Historical cleanup candidates
require current ownership review instead of action based on old IDs.

Reference status was corrected where it still described working imports or
password/PAH/MCP setup as pending. Four version-tool tests, TODO structure,
relative links/anchors, whitespace and added-content sensitive-marker checks
passed. This change modifies documentation/version metadata only.

## Preserve Orchestrator interpreter selection for job runtime

Importer regression and documentation: `f23f1af`; encrypted capture: `c141e1a`.

The production comparison found that the import process evaluated the localhost
interpreter expression, storing its own Python path. The operator requested a
portable result for imported Orchestrator jobs. The encrypted host definition
now marks the expression `!unsafe`, so CoP preserves it literally while importing.
The stored expression resolves normally when a later job runs. All other decoded
capture values and secret inputs are unchanged; the fix belongs to the CaC
inventory definition before the application playbooks execute.

Three focused tests passed, including the installed CoP wildcard combination and
host-parameter rendering with distinct import/job Python paths. Encryption header,
roundtrip and actual Ansible loader checks passed. Live import job 2273 succeeded
using `f23f1af`; a separate verified HTTPS read confirmed the target inventory
stores the literal expression. Application deployment and cleanup were not run.

## Recover failed deployments through manual stage retries

Planning and documentation change: `d7be1cc`.

The operator chose to remove automatic workflow recovery from the TODO because
individual Job Templates can already be retried manually. Operators retain the
existing instance inputs, rerun failed stages and launch the remaining stages.
A full workflow relaunch creates another instance and consumes another counter.
Stage 03's existing installer observer remains available. This decision changes
the plan and instructions only; deployment behavior is unchanged.

## Capture current lifecycle definitions and issue access on each target

Implementation: `0b3910b`; encrypted Assistant capture: `0146052`; encrypted
Windows capture: `62d6647`.

The configuration comparison found two uncaptured Windows templates and current
Assistant lifecycle changes. Windows now includes patch assessment and WSUS
patch-ceiling definitions without changing its prior objects or secret inputs.
Assistant retains its current project branches, reviewed release pin and selected
execution environment, controlled deployment/retirement surveys and Shutdown
template. Dedicated lifecycle groups start empty instead of copying old source
guest registrations. Both captures expose their existing exact PAH requirements
in the common schema; optional authentication maintenance remains excluded.

An inventory lifecycle bearer belongs to its target. The encrypted capture now
contains a new service-account password and a dedicated inventory grant, while
CoP creates the nonadministrator account and its objects. The importer issues a
target-local token and binds the lifecycle credential to that target's URL,
inventory and installed CA. It preserves a root-owned protected token record for
reruns, verifies ownership, scope, privileges, schema and material checksums, and
stops on ambiguous or missing recovery state. An existing account must authenticate
before any updates, and its password is omitted from update payloads to prevent
metadata changes from resetting it. Only this run's new token proved unsaved can
be revoked after failure. No source password/token is copied or rotated.

The CA default follows the installer account rather than the SSH login account.
Verified HTTPS requires the supplied URL to match a certificate DNS or IP SAN;
the encrypted contract may select another installed CA file. The target's internal
URL and installed CA passed a separate read-only TLS inspection.

The 67-test offline suite and three additional focused checks passed, including
15 token behavior checks, account control before grants/updates, password omission
and installer CA selection. Syntax, strict Ansible rendering, encryption round
trips, preserved ciphertexts/literal injectors, object references and staged
sensitive-data checks passed. Refreshed Assistant rollout and functional demo
execution remain separate from these source checks. Production configuration and
external demo environments were not changed by the capture refresh.


## Keep CaC comparisons while planning incremental audit-log catch-up

Planning commit: `cce0e28`.

The user chose to continue the current configuration comparisons and defer
audit-log analysis for catching CaC up with platform changes. The TODO now makes
that future work explicit: preserve audit checkpoints, identify changed owned
objects and relationships, retrieve current definitions and dependencies, then
review differences before updating encrypted captures. Audit events identify
what to examine; they do not replace the current object configuration.

Git changes, deletions, audit retention and component coverage must also be
handled. Periodic full comparisons remain part of the planned coverage checks.
No log-based automation, daily schedule or automatic CaC update was implemented.
Documentation whitespace, version consistency and staged-content checks passed.

## Use the successful login password until administrator rotation

Implementation: `fb87a08`.

A fresh installation exposed an ordering error: bootstrap authenticated with
the installer password, but PAH token creation then used the desired password
before the Gateway user role applied it. That request failed authentication.
The shared login task now retains its successful password in a protected,
noncached fact, and pre-rotation PAH issuance uses that fact. The encrypted desired
password remains unchanged and is still applied and verified later. A rerun
selects the already-active configured password and preserves existing tokens.
No password is added to workflow statistics, artifacts, or logs.

Three focused regression tests passed, including actual login selection for
fresh and configured-password cases and a PAH mock that rejects the inactive
desired password. Token preservation and failure cleanup remain covered.
Base, PAH preparation, AutoDeploy and curator syntax and whitespace checks passed.
The installer had completed successfully; only the failed base stage needed a
rerun. Live verification of that rerun is tracked separately from these checks.

## Manage PAH selection in base and require reviewed release curation

Implementation: `768550d`; encrypted base policy: `cd4a4ab`.

The user requested one current collection version unless project requirements
justify older versions, and clarified that the same collection may appear in
multiple repositories. Retention is therefore local to each repository: preserve
its newest installed release and actual project/playbook/EE requirements plus
dependency closure. A repository's older latest does not preserve obsolete
copies in another repository, and a newer release elsewhere does not remove a
repository's own latest. The curator does not claim to discover newest upstream
content or deduplicate collection names across repositories.

Stage 04 applies and verifies the remote selection limit and repository snapshot
limit independently. The installed remote collection module lacks the selection
field, so a local API extension supplies it after CoP dispatch. Base still does
not synchronize or prune collection content. The populated policy is encrypted
with the existing CaC Vault identity; all other encrypted base values were
verified unchanged.

Actual pruning is separate and defaults to preview. It needs a reviewed source
audit matching live projects and EE references, complete dependencies, an idle
target and an unchanged approved preview. Apply removes only the reviewed
repository associations and verifies retained content. Run externally or from
another seed during a maintenance window that prevents concurrent target work;
preflight checks do not provide a continuous lock. Mutable image references do
not establish image content or build provenance. Production audit completion,
recurring curation and target-side own-job exclusion remain future work.

Nineteen focused retention tests passed, including repository-local latest
selection, exact pins, dependency closure, unchanged settings and stale-preview
rejection. The 52-test broad run passed all other tests; its PAH guard fixture
needed the new required policy, and the corrected focused guard test passed.
Stage 04 and curator syntax, whitespace, staged-sensitive-data review, and
encrypted base round-trip checks passed. No live pruning was performed.

## Restore AutoDeploy as a use case and orchestrate complete deployments

Implementation: `6c83591`; encrypted companion capture: `9020feb`.

The user requested one workflow that creates an AAP, applies shared base, then
imports captured use cases in parallel, including the ability for the replacement
to deploy another instance. AutoDeploy therefore has its own encrypted capture
and importer rather than placing its deployment objects in platform base. The
workflow passes only the created VM identity, address and internal API URL;
installer hostname handling remains separate. After explicit PAH/image
preparation it branches to four captured demos and AutoDeploy itself, excluding
teardown and functional demo jobs.

The capture keeps environment credentials and populated object references in the
existing encrypted companion repository. A dedicated provisioning key was
explicitly approved and independently verified; the workspace's GitHub SSH
identity was excluded. Existing environment Vault access is captured separately
from base's Git and CaC Vault bootstrap credentials. Exact PAH collection batches
preserve multiple required versions, restore complete remote requirements even
after failure, and observe asynchronous policy completion before syncing.
Thirty existing/graph tests and three real-task mock-PAH tests passed, as did
syntax and private encryption/reference checks. Fresh recursive deployment and
full production coverage remain unverified; a captured Windows collection's
runtime version mismatch remains an explicit follow-up.
## Review the current CaC implementation against Red Hat guidance

Planning commit: `9dad713`.

The user requested a TODO to compare this project with Red Hat's Configuration
as Code guidance. Review automation access, content sources, capture coverage,
secrets, validation, drift, deletions and Git workflow for applicable gaps.
Account for the article's different AAP versions and example collection when
assessing the current AAP 2.7 CoP implementation. This schedules a review;
it does not establish compliance or change platform configuration. The README
overview also now reflects implemented target-side MCP token creation and the
remaining encrypted repository storage and client setup work. Documentation
whitespace, source-link and version consistency checks passed.

## Allow fresh installation to exceed the old one-hour async ceiling

Implementation: `5f8c3e0`.

An earlier fresh installation reached the one-hour command ceiling and required
observation of its existing async job. A longer Job Template timeout alone did
not extend that command ceiling. The installer command and existing-job observer
now allow two hours; the documented template timeout is three hours to cover
host preparation and health checks. Resume behavior still observes the original
job instead of launching another installer. Stage 03 passed syntax validation.

## Protect DNS authorization during provisioning and cleanup

Implementation: `6ad202d`.

The rebuild preflight found that the DNS API tasks could include authorization
headers in ordinary task results. Both creation and removal now suppress their
requests and responses independently of diagnostic logging elsewhere. Syntax
checks passed for infrastructure configuration and teardown; teardown was not
repeated to validate this logging change.

## Provision configuration access on trusted replacement instances

Implementation: `18f50b2`.

The user requested that shared base create the four configuration-repository Git
credentials and the CaC Vault credential from inputs already held in encrypted
base. This allows a trusted replacement to read and decrypt the same private
configuration repositories. The first seed still needs its initial access
independently. Provisioning rejects incompatible existing ownership, types,
injection schemas and Vault identifiers, and preserves already stored secret
values on reruns. Rotation remains a separate operation. Deployment-project
objects and provisioning-environment credentials belong to the AutoDeploy use
case rather than shared platform base. Four isolated real-task tests and a
Stage 04 syntax check passed; no live rollout was used for that validation.

This retrospective uses this repository's Git history and the project handoff.
Where historical intent is not documented, it is identified as an inference.
Source-baseline versioning begins after the historical commits below.

## Create recoverable target-local MCP access during base configuration

Implementation: `5542cbd`.

The user requested that base configuration issue an administrator MCP token with
read and write access on every new installation. Gateway scope `write` provides
both operations within that account's permissions. Provision it after the final
administrator login is verified, separately from the temporary management token
that ordinary run cleanup revokes.

The API returns a new bearer value only once. Save that value atomically in a
root-owned private file on its target so an authorized operator can recover it
for an external client. The directory uses mode `0700` and the file uses `0600`.
This interim storage uses existing guest SSH/sudo access and requires no new Git
write credential. Encrypted per-instance repository storage, client certificate
trust and controlled rotation remain separate planned work.

Reruns validate metadata, expiry, target identity and saved bearer authentication
before preserving existing access. Preserve manually created matching tokens
without issuing duplicates; their hidden value cannot be recovered from the API.
Unsafe storage or ambiguous/mismatched access stops for operator review. After
a failed save, revoke a new token only when inspection proves that its recovery
copy was not saved. Preserve inconclusive outcomes for inspection rather than
silently breaking access. Sensitive operations remain hidden during diagnostics.

Seven MCP tests exercised the actual tasks against an offline HTTP fixture and a
local substitute for the target filesystem. The complete 23-test suite and Stage
04 syntax check passed. Read-only inspection confirmed the live Gateway response
shapes; no live token, base deployment, VM or external client was changed.

## Limit PAH selection and remove obsolete collection releases

Documentation and verified-maintenance commit: `67de471`, following the policy
planned in `c547f68`. The live maintenance used supported Pulp API operations;
this repository does not yet contain recurring cleanup automation.

The operator requested the newest retained release for each collection while
preserving older versions explicitly required by projects. The audit covered
11 Controller projects, their available collection and execution-environment
requirements, and the retained collections' dependency constraints. Keep the
newest stable release already present for each collection, plus RHEL system
roles 1.120.5 because two projects pin it; retain 2.4.2 alongside that exception.
This avoids breaking exact project pins while removing unused release histories.

The maintenance reduced 263 releases to 16 across 15 collections: certified
244 to 10, community 18 to five, and validated one unchanged. Both removal tasks
completed and the final content matched the reviewed set. Project requirements
were unchanged, and independent MCP reads confirmed the published collections.
Removing repository associations did not include global orphan cleanup or
establish how much disk space was reclaimed.

Set each collection remote's `sync_highest_versions` to one and use exact
requirements with a complete dependency closure. Disable automatic dependency
selection for those explicit lists to avoid downloading extra matching releases.
Duplicate exact entries preserve the required older pin despite the per-entry
version limit. Keep repository `retain_repo_versions` at one as a separate
snapshot policy; it does not limit collection releases in the current snapshot.
Upstream source, authentication and TLS settings were preserved.

Updating the encrypted CaC source and implementing recurring enforcement remain
TODOs. The installed collection-remote module lacks the sync-limit argument, so
declarative management needs supported module or API integration. Use the current
encrypted source with its matching Vault key rather than replacing it from an
older plaintext export. No runtime automation jobs were launched for this work.

## Plan PAH version retention from project requirements

Planning commit: `c547f68`. Automated selection, retention and cleanup remain
unimplemented.

The operator requested fewer collection versions for simpler PAH management.
Synchronize only the exact versions required by projects and execution
environments, including their dependency constraints, and declare the required
set in PAH configuration as code. Keep multiple versions of a collection only
when project requirements justify each retained version. Otherwise select one
current compatible version. Audit requirements before pruning older content and
avoid unbounded remote selections that download complete release histories.

The TODO and README describe this future policy. The planning change does not
deploy a retention mechanism or remove collection content.

## Plan recoverable per-instance MCP credentials

This is planning only; persistent MCP provisioning has no implementation commit.
The existing temporary base-authentication implementation is `1216f38`.

The operator will create the current target's MCP API token manually and requested
future automation in the TODO. Each fresh platform issues its own token, so base
must provision instance-specific access rather than copy an old platform token.
An AAP credential masks its secret on API reads and therefore cannot be the only
copy needed to configure an external MCP client.

The planned recoverable copy contains the token, endpoint and CA trust material
in fully Vault-encrypted per-instance files in the private base repository. Opaque
filenames avoid exposing environment names. A separate repository-scoped Git
write credential enables saving these files while existing import access stays
read-only. Client setup decrypts values into protected local configuration with
certificate verification enabled. Provisioning, storage, rerun and rotation
behavior remain unimplemented; no platform or client configuration changes are
part of this documentation update.

## Verify Assistant Team import with trusted local PAH downloads

Encrypted Assistant Team fix: `094ee7f` in its private companion repository.
Encrypted base trust fix: `63f08ff` in the private base configuration repository.
The successful jobs used the existing importer from source `b80a1f0`.

The operator authorized importing the six ordinary Assistant Team templates and
their supporting objects. The first project creation failed because an empty
source-control credential name matched every credential. Omitting that field
correctly expresses anonymous access to the public code repository. Both encrypted
project entries were corrected while preserving every other value and all six
inner encrypted file snapshots; Vault round-trip and importer guards passed.

Project synchronization then exposed a separate platform trust issue. The
Controller service trusted the installer-generated CA, but its remote Podman
engine resolved execution-environment volume sources on the host. The default
host trust mount lacked that CA. A read-only mount from the installer's host-side
extracted trust directory produced the same bundle hash as Controller and a
verified HTTPS response. The encrypted base now declares this mount through the
existing Controller settings role, preserving its prior mounts and certificate
verification. Base job 2137 applied it; both project sync retries succeeded.

The pinned certified collection was curated through local PAH before import.
Import job 2139 succeeded with protected logging, and an independent TLS-verified
API comparison passed 396 checks over all 21 objects and six templates. Run tokens
and temporary workspaces were removed. API-masked secret fields were verified for
presence and protection; nonsecret snapshot provenance and credential type
injection matched the capture. Runtime deployment, recovery, provider calls and
optional authentication maintenance were not executed.

The operator also requested a planning item to capture Intelligent
Assistant/Lightspeed completely, including installer/service configuration,
vaulted credentials and passwords, Gateway OAuth, and an independent rebuild.
This adds a TODO only and does not change that service.

## Verify the encrypted base administrator password on a deployed target

Implementation: `1216f38`; verified runtime source: `c51aede`.

After restoring the existing private-base Git credential, job 2125 successfully
applied the desired password through the CoP Gateway user role and synchronized
the deployed installer inventory with mode `0600`. Job 2128 successfully used
the configured password and skipped installer access, bootstrap-token creation
and inventory changes. This verifies that future base reruns can authenticate
with the declared password while existing use-case importers can read the
current installer login.

Independent checks used trusted TLS and confirmed successful desired and
installer logins, matching password and permissions, no leftover run tokens,
and unchanged use-case object counts and EDA activation states. Both job event
streams confirmed token revocation and temporary workspace removal. No imported
use-case Job Template was launched for this verification.

## Define a complete production replacement and trusted seed bootstrap

Encrypted base credential inputs: `490a27b` and `9563936` in the private base
configuration repository. Administrator-password implementation: `1216f38`.

The operator clarified that the primary goal is a fresh AAP capable of taking
over production tasks, including deploying further AAP instances. Individual
demo imports remain supported, while complete replacement requires restoring
the deployment automation itself, all relevant production objects and secret
inputs, runtime dependencies, and functional verification.

An existing trusted AAP starts with independently provisioned base Git and Vault
credentials. The operator explicitly requested storing those inputs together in
the encrypted base so a seed can configure another trusted instance. Including
the decryption password in that ciphertext enables propagation after decryption;
it does not provide the initial seed's access or recover a lost key. Recipients
share the credentials' configuration access. Actual target credential and
deployment-template provisioning remains unimplemented and is tracked in the
plan, together with complete capture, job handoff, tests and controlled takeover.

This documentation does not resume stopped deployments or establish successful
password rollout or production takeover. Markdown whitespace checks were used;
no AAP job was launched for this documentation.

## Manage the administrator password in encrypted base configuration

Implementation: `1216f38`.

The operator requested that the desired administrator password live in the private
base Vault and be applied by Step 04. The base now declares the password and a
Gateway user entry that references it. Authentication first tries the desired
password; HTTP 401 or an omitted password enables installer bootstrap. Other
HTTP or connection errors stop rather than falling back. The CoP Gateway user
role applies the account, followed by a fresh Basic-authenticated login check.

When bootstrap was necessary, the deployed installer inventory is updated to the
verified password and restricted to mode `0600`. This keeps the existing use-case
importers' installer-based login current. A rerun using the configured password
skips installer access. Password handling stays protected during diagnostics.

All sixteen local tests passed, including seven authentication scenarios. Syntax,
Vault round-trip and whitespace checks passed. The first rollout stopped at
private-repository checkout before target changes because its token had been
regenerated. The existing base Git credential was subsequently updated and
repository access verified. The password rollout remains pending.

## Reuse the established Git-token credential type for Assistant Team

Implementation: `1926669`.

The operator requested the existing Git-token mechanism instead of a separate
SSH deploy-key mechanism. The importer now requires an HTTPS Git URL and
`CAC_GIT_TOKEN`, with the same temporary askpass helper and verified HTTPS used
by the other CaC importers. The unused SSH credential type was removed before
any key or credential was created. The token still needs read access to the
selected private repository; sharing a type does not share its permissions.

All fifteen local tests passed, including repository URL rejection, missing
token handling, encrypted configuration guards and cleanup after failure. Full
syntax and whitespace checks passed. No Assistant Team import was launched.

## Import the ordinary Assistant Team configuration independently

Implementation: `614763a`.

The operator authorized deploying Assistant Team definitions after shared base,
separately from running its deployment and recovery automation. The dedicated
importer loads only the companion repository's encrypted CaC capture and restores
six ordinary Job Templates with their supporting objects. Public code access
does not provide access to the private configuration; repository-scoped read-only
SSH access is injected as files, with independently trusted host keys and strict
verification. No write credential or source Controller identity is propagated.

The ordinary import validates complete deployment secrets and all six unchanged
encrypted file snapshots. Optional authentication maintenance remains nested,
outside dispatch, because it needs target-specific authorization and trust.
Reading that optional mapping can recursively render deliberately unresolved
inputs, so the ordinary importer leaves it untouched. A regression includes such
an unresolved input and rejects adding a seventh template to ordinary dispatch.
Functional readiness and optional maintenance remain separate from importing
complete ordinary AAP definitions. PAH collection and service-image availability
must be verified before a live import.

Authentication follows the established temporary Gateway-token approach.
Sensitive tasks remain protected during diagnostics, and cleanup removes the
checkout after ordinary failures, including failed token revocation. Launch and
schedule definitions are rejected; imported automation is never executed by this
entry point. Interrupted jobs and fatal role-loading errors retain the existing
cleanup limitation.

All fourteen local tests passed, with sixteen Assistant Team Vault/core guard
cases, six SSH URL cases and three failed-import cleanup scenarios. Full syntax
and the current encrypted capture's actual preflight passed. Implementation did
not launch Assistant Team configuration import or runtime automation.

## Align encrypted use-case captures with their current source

Private capture implementations: Orchestrator `0fd3b53`; Assistant Team
`2c3a825`, documented in `fbd7afd`.

The operator chose `Orchestrator EE` as the common name for the execution
environment definition, the project's default, and both Job Templates. The
previous project reference named an object the capture did not create, so the
three other references were aligned before attempting a clean-target import.
The configuration's remaining values were preserved.

Assistant Team was refreshed from the current Controller configuration and native
CoP export. Its public code no longer requires an SCM credential for private code.
The capture includes current project revisions and the encrypted external file
credential for six deployment/recovery templates. Existing deployment and model
authentication ciphertexts remain unchanged. Authentication maintenance is
captured separately from ordinary dispatch because its repository write access,
controller identity and trusted CA must be prepared for the target AAP.

The capture declares required PAH content and the execution environment's pull
prerequisite. Empty PAH repositories can prevent project synchronization before
runtime automation is launched. A dedicated Assistant Team importer is still
outstanding; validated capture data is separate from completed target deployment.

Validation checked owned references, native export of all seven templates,
strict ordinary rendering, missing maintenance input rejection and a synthetic
maintenance render. Vault headers and private round trips passed, and all six
embedded ciphertexts matched their source files exactly. No AAP configuration
import, runtime job, or provider authentication refresh was launched.

## Verify the protected PAH base rollout

Implementations: `5fc2c98`, `40906b1`, and `bf12d01`; encrypted base: private
configuration commit `82643da`.

The protected rollout succeeded after the API summary and upstream field-pair
fixes. Independent TLS-verified API checks found the three intended remotes,
repositories, distributions, and ordered local Controller download credentials.
The organization no longer includes public Galaxy as a source. Collection
repository versions remained unchanged, and no collection synchronization task
was created. Periodic Hub resource synchronization is distinct from collection
content synchronization and was already present before rollout.

The same three read-scope download tokens survived the reruns without replacement
or duplication. Temporary management and verification tokens were removed, and
the configuration workspace was cleaned. The successful job had no failures
with protected logging enabled. These checks establish repository and source
setup, not populated content or functional use-case tests. Upstream Red Hat
authentication and use-case collection preparation remain separate work.

## Import Orchestrator definitions separately from platform and runtime deployment

Implementation: `de5b54c`.

Orchestrator needs a dedicated CaC entry point after base, with its own private
configuration repository and Git read credential. `deploy-orchestrator-demo.yml`
loads only `cac/orchestrator.yml` from `main`. It uses the existing capture's
readiness mapping and protected registry inputs instead of changing the capture
schema or storing bootstrap access inside the repository being downloaded.
The reviewed capture defines eight owned AAP objects, including deployment and
cleanup Job Templates and their launch surveys. Those runtime operations remain
separate from importing their definitions; launch and schedule definitions are
rejected, and the dispatch launch roles are excluded.

Authentication follows the established importers: explicit target URL, encrypted
administrator input or installer SSH fallback, and a temporary Gateway token for
CoP dispatch. Sensitive tasks remain protected during diagnostic logging. Token
revocation and workspace removal run after ordinary failures; a token-revocation
error still permits workspace cleanup. Fatal role-loading errors and interrupted
jobs retain the existing cleanup limitation.

All eleven local tests passed. New tests ran eleven actual Vault loading and
preflight cases plus three failed-import cleanup scenarios. Full syntax and the
existing encrypted capture's new guards passed. No configuration import or
Orchestrator/OpenShift runtime operation was launched during this implementation.

## Defer upstream authentication during URL-only PAH setup

Implementation: `bf12d01`.

The diagnostic rollout reached the Hub remote module and returned HTTP 400:
an upstream authentication URL requires its upstream token even when no sync is
requested. The reusable base therefore omits that URL until future content
preparation supplies both fields. Local repository setup and local download
tokens do not require an upstream token. A protected preflight check now rejects
an unpaired authentication URL before any target change. No access controls are
weakened and no synchronization is added.

The encrypted base was regenerated from its protected working copy, with matching
Vault decryption and the private repository's minimal README preserved. Both PAH
tests passed, including seven configuration cases and credential lifecycle
coverage; full syntax and populated-base guards passed. A protected target rerun
is required to establish live success.

## Validate credential types using the actual summary schema

Implementation: `40906b1`.

The first PAH rollout created its local download credentials before failing at
the Hub remote role. A diagnostic rerun then stopped at credential preservation:
the Controller summary returns a credential type's name but omits its kind.
The guard now compares the exact built-in Galaxy credential type name. This
preserves the intended type check without replacing credentials or their tokens.
The local API fixture now reflects the actual summary schema; both focused PAH
tests passed, covering guards and the full credential lifecycle. The original
Hub failure still requires its separate diagnostic rerun.

## Configure PAH in base without synchronizing content

Implementation: `5fc2c98`.

Base now owns three PAH remotes, repositories, download distributions, and
Controller source associations in certified, validated, community order. The
organization's source list replaces the public Galaxy fallback with those local
sources. Upstream URLs are configured without fetching content or requiring
Red Hat synchronization credentials at this stage. Repository definitions must
explicitly disable synchronization, and the separate CoP synchronization role
remains excluded. Use-case content preparation is still a separate task.

The Hub roles require their own authentication variable, so the temporary
Gateway management token now supplies both Controller and Hub authentication.
Controller also needs credentials that survive the configuration job. Each
missing PAH credential receives a target-generated read token, stored immediately
in Controller. Matching existing credentials retain their hidden tokens; drift
stops for review. This avoids copying a source instance's token into another
instance or continuously creating replacement tokens on reruns. The reusable
encrypted base stores definitions rather than tokens belonging to an older target.

A failed save revokes the newly generated token only when a subsequent lookup
proves no credential was saved. An ambiguous result retains the token for review,
avoiding deletion of a token that Controller may already use. Management token
revocation and workspace cleanup remain independent. Authentication, decrypted
configuration, and credential-bearing tasks stay protected even when ordinary
diagnostics are enabled.

Nine tests passed. Local Ansible runs exercise source-order and no-sync guards,
and the actual Controller credential module covers creation, reruns, interrupted
saves, drift, and protected output against a local API fixture. Stage 04 syntax,
populated base validation, and full Vault encryption/decryption equality checks
passed. Live target rollout remains pending at this documentation commit.

## Keep PAH setup in base and create groups before linking children

Implementation: `d2e6988`.

The user clarified that base owns PAH's certified, validated, and community
repository configuration and Controller content sources. Base must not
synchronize content. Each use case separately declares its collection
requirements, including versions and dependencies. The dispatcher defaults to
synchronizing defined repositories, so Stage 04 now explicitly excludes that
role. Empty templates document both responsibilities. Actual target PAH setup
and population of existing use-case requirements remain TODOs.

Private Git access is needed before the encrypted configuration can be loaded.
Its runtime token therefore belongs in the deploying AAP's custom credential,
with a separately encrypted bootstrap recovery copy. A target project's Source
Control credential serves a different purpose: synchronizing that project's
private playbook repository after import. Repository-specific credentials keep
one access update from replacing another deployment's token.

The first Windows import to reach inventory creation failed at the parent
group; its child groups were submitted afterward by the asynchronous CoP role.
A retry succeeded once those children existed. The importer now creates group
skeletons first, then calls the standard role for full definitions and
memberships. A regression exercises the real Controller group module and
reproduces the missing-child failure before verifying the new sequence.
Existing empty-membership drift behavior is unchanged.

Seven tests and syntax checks passed. Live import succeeded with the preceding
source after a retry, without launching imported automation; the new ordering
has offline validation only. The project TODO also calls for a complete,
step-by-step CaC guide covering setup, deployment, verification, and recovery.

## Diagnose private configuration fetches without printing Git errors

Implementation: `5ccb0ca`.

The first Windows import stopped during the protected private checkout before
target authentication or object changes. Because the Git error can contain
credential-bearing data, enabling raw output is inappropriate. The fetch now
rescues failures, privately classifies their message, and reports only a fixed
category. This distinguishes repository access/not-found errors from DNS, TLS,
redirect, connection/timeout, and unclassified failures without changing access
controls or trying alternate credentials.

Seven synthetic failures exercised the actual rescue and cleanup tasks with
diagnostics enabled. They produced the expected fixed categories, hid both the
synthetic secret and raw errors, and removed each temporary checkout. Full
syntax and existing regression tests passed. The live error category still
requires a rerun; token repository permissions must not be assumed from a
successful checkout of a different private repository.

## Import disconnected Windows definitions independently from base

Implementation: `a84bf09`.

The Windows capture belongs to its own private configuration repository, so its
import accepts an explicit target URL and repository URL rather than assuming
the base or AIOps configuration store. It retrieves only the Vault-encrypted
Windows definitions from `main`, checks readiness and required secrets, then
uses the existing Gateway-token and CoP dispatch approach. Subscription and base
configuration are prerequisites rather than repeated operations.

Importing AAP definitions must not start Windows provisioning or patching. The
entry point therefore rejects job-launch and schedule definitions and excludes
the launch roles. It imports the captured Job Templates and workflow for later
use. Existing target machines are not contacted by this configuration job.

The CoP wildcard combiner can print its input values, so that step remains
protected separately before ordinary dispatch. Credential updates and all Git,
decryption, password, and token operations stay protected when diagnostics are
enabled. Default logging remains protected throughout. Syntax, the real CoP
dispatcher regression, seven Windows preflight cases, and version-tool tests
passed. Live Windows import remains a separate pending validation.

## Keep module-native Event Stream definitions out of initial dispatch

Implementation: `a64e16c`; encrypted deployment enablement: private configuration
commit `8a121e8`.

The first live AIOps import exposed an incorrect earlier assumption that CoP
4.10.0 lacked an Event Stream role. It includes that role, which reads each
item's `organization` field. Our dedicated module definitions use
`organization_name`, so initial dispatch attempted stream creation with a missing
required organization. Diagnostic job 2016 confirmed that exact error while
leaving other configuration logging protected.

Initial dispatch now excludes streams as well as activations. The existing
explicit stream task runs after prerequisites, followed by the activation role.
A regression test exercises the real dispatcher, including negative controls
that remove each exclusion. The earlier fixture replaced prerequisite dispatch
with a stub and could not detect this integration error.

The user authorized the first deployment, so the complete encrypted capture's
readiness flag was enabled. Job 2018 then succeeded with 131 successful tasks and
no failures. Independent API checks verified all 29 expected objects, successful
Controller project syncs, and both EDA activations running. Configuration tokens
and temporary files were cleaned; the persistent EDA credential was preserved.
Functional remediation remains a separate test; no external setup was changed.

## Resume installer monitoring without starting another installation

Implementation: `64aec45`.

The Controller stopped installation job 2002 at its overall 3,600-second timeout.
Host preparation had consumed part of that budget, so the remote installer's
separate 3,600-second async task had not reached its deadline. The last event
reported that task as unfinished; there was no installer error to justify a
second installation. The template timeout now allows 7,200 seconds.

Stage 03 accepts an optional existing async job identifier. This mode skips host
preparation, inventory edits, and installer launch, checks the existing result
under the original installer account, and requires exit code zero before the
Controller health check. Captured installer output remains protected. It does
not extend an existing task's async limit or treat an open HTTPS port as success.

Syntax and whitespace checks passed. Live resume job 2008 completed successfully
in 32 seconds: the original installer reported success, the installer-launch task
was skipped, and the Controller ping returned HTTP 200. No installation rerun or
security-control workaround was needed.

## Declare the collection used for public DNS validation

Implementation: `97e3236`; preceding HTTPS implementation: `de07aad`.

Successful deployment job 993 used a built-in HTTPS DNS request, while the
standalone checkout used an undeclared `community.general.dig` lookup and failed
in job 1996 before certificate issuance. The brief HTTPS restoration was
superseded by the user's preference for readable playbooks using reliable
collections. Stage 02 therefore keeps the collection lookup, explicitly requires
`community.general` 11.4.0 through PAH, and waits for the expected public A record.
This version supports the actual execution environment's Ansible Core 2.16.19;
its required `dnspython` package is already installed in that image. No Python
package installation or execution environment change is needed for this fix.

Ansible syntax and whitespace validation passed. The original failure happened
after DNS and temporary HTTP proxy configuration; the successful teardown and
VM creation stages must not be repeated to retry this infrastructure stage.

## Use the same EDA credential schema throughout deployment

Implementation: `91b5fc6`.

Integration review found that native exports normalized for CoP use
`organization` and `credential_type`, while the special target-token handler
expected the EDA module's argument names. The handler now reads the CoP item
fields and translates them only at the module call. This keeps one schema for
ordinary credentials and the target-specific Controller credential and avoids
storing duplicate aliases in the encrypted configuration.

Full syntax validation and eleven isolated checks using the installed EDA
credential module passed. Secret protection, first creation, preservation on
reruns, drift rejection, and cleanup remain covered. No live AIOps deployment
was launched.

## Create Event Streams before activating AIOps rulebooks

Implementation: `33f2575`.

This change introduced explicit Event Stream creation before activation import.
Its initial assumption that CoP 4.10.0 lacked the stream role was incorrect;
the later correction is documented above under `a64e16c`. The AIOps playbook
dispatches prerequisites first, creates streams through the supported EDA module,
and only then applies the CoP activation role. The encrypted capture
uses names and rulebook source names or indexes, so modules resolve the new
instance's IDs, hashes, and stream UUIDs. Required mappings are validated before
target configuration starts.

CoP also omits EDA project revision-on-launch and cache settings even though the
installed EDA project module supports them. A focused update after dispatch
preserves declared values, waits for the existing project, and avoids a second
source-control sync. These tasks supplement the collection's known omissions;
they do not change source AAP objects or external event publishers.

Full syntax validation and ten isolated checks using the actual EDA modules and
CoP activation role passed, including ordering, target mapping, failure handling,
and project setting preservation. The live AIOps Job Template remains unlaunched.

## Separate platform base from AIOps use-case deployment

Implementation: `e864dc9`.

The user clarified that base must exclude objects belonging to actual use cases,
including their Git projects. Each use case gets an independent encrypted file
and deployment Job Template. The broad private base was reduced to its platform
organization and existing setting, with previous definitions preserved outside
Git. The old credential intended for local PAH actually held an upstream token;
it was omitted instead of copying an unrelated management token. Destination
PAH bootstrap remains a separate requirement.

The AIOps entry point loads only its encrypted configuration after base and
requires reviewed readiness and explicit secret inputs before target changes.
It uses temporary configuration access and creates persistent target-specific
EDA access only when the corresponding credential is absent. Reruns preserve
that credential and reject conflicting settings. Cleanup revokes an unsaved EDA
token only when absence is verified, while retaining saved or uncertain access.
This avoids reusing source-instance tokens or disrupting existing activations.

The user selected the current working demo, with older/test objects inventoried
separately outside Git, and approved use-case-specific copies of shared inventory,
credentials, and runtime environments. Source AAP objects remain unchanged.
External environment setup is deferred. Export tooling was approved separately
and installed outside these repositories; it was not added to project requirements.

Full syntax validation and eleven isolated real-Ansible checks with the actual
EDA credential module passed. Empty template and whitespace checks passed.
The AIOps deployment entry point must remain unlaunched; live validation is future
work after its encrypted capture is reviewed. This does not claim a working
restored external monitoring or assistant environment.

## Manage AAP 2.7 applications through Gateway

Implementation: `44e1045`.

The first live run with the corrected installer authentication successfully
imported the subscription, then stopped while loading the collection's legacy
Controller application role. The installed Controller collection does not
provide that module. Step 04 excludes only `controller_applications`; the
Gateway application role still handles `aap_applications`, and Controller role
assignments remain enabled. The collection's supported role-exclusion setting
avoids changing its downloaded contents or suppressing the failure.

All 59 module references across the 58 selected roles were verified against
the five actual PAH collection artifacts. Five token-lifecycle checks passed.
The role-loading failure bypassed Ansible's normal cleanup, so its run token
was revoked separately using CA-verified HTTPS over the trusted SSH connection.
README now states this cleanup limitation. Subsequent live job 1985, using source
revision `7d65678`, completed shared base configuration in 162 seconds with 147
successful tasks, 36 changes, and no failures. It preserved the previously
imported license, revoked its run token with HTTP 204, and removed its workspace.
The project wait that displayed retry messages finished successfully after
46 seconds. Saved debug logging remains false. This verifies Step 04's shared
base flow, not per-demo loading or the complete deployment pipeline.

## Download project collections exclusively from PAH

Implementation and policy documentation: `2725894`.

The user required collection curation in private Automation Hub, including
community collections, rather than direct public Galaxy downloads by projects.
Sync all required collections and dependencies into the corresponding PAH
repositories before project synchronization. Organization source credentials
must point to those PAH repositories; public Galaxy must not be an active
source or fallback. PAH may continue using public Galaxy as an upstream when
syncing community content. The requirements file still selects the collections.

The public Galaxy source was detached from the existing organization. The
three PAH sources were verified to remain attached in their existing order.
AAP rejected deletion of the managed public Galaxy credential with a permission
error, so it remains an unattached protected object. No access controls were
changed. Source credentials on an AAP running Stage 04 are bootstrap inputs;
target CaC cannot supply the running job's own dependency-download access.

README, CaC guide, and operational documentation describe this policy and the
encrypted-token requirement. Documentation and whitespace checks passed. No
playbook behavior changed and no jobs were launched for this policy change;
runtime dependency verification belongs to the separate Stage 04 run.

## Declare the configuration collection for project synchronization

Implementation: `9243762`.

Step 04 could not start because its dispatch role was absent from the job's
collection search path. Storing the collection in private Automation Hub did not
make it available to the job. The user requested a project requirement for
`infra.aap_configuration`; it is pinned to the published version `4.10.0`.

With collection downloads enabled, project synchronization resolves that
requirement and its declared collection dependencies using the Galaxy credentials
attached to the project's organization. The requirements file selects the
collection, while organization credentials select accessible download sources.
Using a private Hub `validated` repository therefore also requires its source
credential on the organization. Python and system packages remain the execution
environment's responsibility.

The YAML structure and pin were checked against published Galaxy metadata, and
staged-file and whitespace checks passed. No local dependency installation, AAP
settings change, project synchronization, or job launch was performed for this
change. A successful project synchronization is still needed before runtime
collection availability can be verified.

## Bootstrap API access from the installed Gateway credentials

Implementation: `62ab119`.

Live subscription import returned HTTP 401. A read-only comparison over the
target VM's supplied SSH login confirmed that its installer Gateway password
differs from the saved password previously used by Step 04. The installer
Controller password is separate as well. No password values were printed.

The user had requested reading the current password from the installer. Step
04 now reads only that Gateway password over SSH with sudo, unless an explicit
current `aap_password` is supplied through encrypted configuration. It creates
a per-run write-scope token at the Gateway token endpoint, then passes that
token to the Controller license module and the configuration roles. This
follows AAP 2.7's Gateway token authentication path without changing access or
certificate-validation settings.

Dispatch runs inside the protected workspace block so cleanup can revoke the
token after configuration ends or fails. A nested cleanup block removes the
checkout, manifest, and helper even if token revocation fails. Password rotation
and removal of the remaining environment Vault dependency stay separate work.
Normal output remains protected; the existing debug switch still applies.

Five isolated Ansible checks verified installer parsing, an explicit password,
token use, authentication/configuration failure, revocation attempts, protected
output, and workspace cleanup. These fixture checks do not claim a successful
live subscription import or full configuration push.

## Use an explicit debug switch for Step 04

Implementation: `ff84279`.

The user chose `debug_logging` with positive debugging semantics: `true` shows
task output, while `false` enables `no_log`. The change is limited to Step 04;
aligning other projects remains planned. Both the playbook and Job Template
default to `false`, and an optional true/false survey supports a per-run override.
Native Booleans and survey strings are normalized, and invalid choices fail.

All nine existing protected tasks use the inverse of this switch. The dispatch
collection receives the same inverse through `aap_configuration_secure_logging`.
Debugging can therefore expose decrypted configuration in AAP job output, which
is documented in the README and survey; the saved default stays protected.

Six isolated Ansible checks verified default protection, native and survey
values, dispatch mapping, output visibility, and invalid input rejection. The
live template default and survey were verified without changing other template
settings. Those checks did not import a subscription or apply target objects.

## Apply the subscription before object configuration

Implementation: `7503d96`.

The user required subscription activation before pushing configuration. Step 04
now downloads the whole ZIP as `cac/manifest.zip.vault` alongside the encrypted
shared base. The same attached `cac` Vault credential decrypts both through
Ansible's runtime Vault support; no password lookup or new launch secret is needed.
The ZIP is restored with restrictive permissions in the private temporary
workspace and imported with `ansible.controller.license` before dispatch.

Failed decryption or subscription import stops configuration. Cleanup removes
the checkout, decrypted ZIP, and authentication helper on success or failure.
The license module uses `force: false` to preserve an existing non-trial license
when rerunning configuration. Installation registry/content access remains
separate from this AAP activation step.

Six isolated checks verified exact ZIP restoration, permissions, invalid inputs,
wrong-password failure, failure ordering, and cleanup. The API was simulated
because the required collections are absent locally; these checks do not claim
a successful live subscription import or configuration push.

## Choose the configuration API target explicitly

Implementation: `0d4bb8d`.

The user requested one explicit connection URL for Step 04, so operators can
choose an internal hostname or IP instead of implicitly using public DNS and
the reverse proxy. Step 04 now requires `aap_hostname` and validates that it is
an HTTPS URL before fetching configuration. It no longer constructs a target
from `vm_name` and the domain, and has no fallback to that naming scheme.

Step 03 remains unchanged: its installer inventory uses the VM's fully qualified
hostname, which can resolve internally. Step 04's API connection address is
supplied separately. Administrator authentication still comes from `myvars`;
automatic address handoff between deployment stages remains future work.

Nine isolated target-input checks and eleven HTTPS Git/Vault loader checks
passed. The real dispatch role and live AAP target were not exercised, and no
deployment or configuration job was launched.

## Load private configuration before applying shared AAP objects

Implementation: `fd35d02`.

Public playbooks remain separate from private deployment configuration. Step 04
downloads the private repository using a token injected by an AAP custom
credential, then decrypts and loads its shared base before the dispatch role runs.
The repository URL is an input; the branch is always `main`, as requested, rather
than a release tag. The token is supplied independently from the encrypted
configuration so access does not depend on first downloading the file that would
contain that token.

The token stays out of Git URLs, command arguments, stored credential helpers,
and task output. A private temporary checkout and authentication helper are
removed after loading, including on tested failures. HTTPS certificate validation
remains enabled, redirects are refused, and submodules are not downloaded.

The existing `myvars` still supplies environment settings and target login while
the new `cac` Vault credential decrypts private configuration. Removing `myvars`,
reading the installer password, rotating the administrator password, and selecting
demo files remain separate work.

Eleven isolated HTTPS Git/Vault checks verified the current encrypted base with
both Vault credentials, invalid inputs, authentication/decryption failures, TLS
rejection, protected output, and temporary-file cleanup. The four version-helper
tests and whitespace checks passed. Full syntax validation was blocked locally
by the missing dispatch collection; no live AAP job or full deployment was run.

## Identify the source of the AAP configuration role

Implementation: `e97480d`.

The user requested attribution to the Ansible Community of Practice. The upstream
project identifies `infra.aap_configuration` as the Red Hat Communities of
Practice AAP Configuration Collection. Step 04 and Windows restore both use its
`dispatch` role to apply AAP object definitions. The README and CaC guide now
name that role and link upstream so operators can find its documentation.
This describes the existing configuration implementation; no playbooks changed.

## Separate editable, private, and generic configuration

Implementation: `6583b61`.

The user requested moving the encrypted shared base into the private configuration
repository and removing it from this repository's current tree. Generic empty
examples remain here. This keeps reusable automation separate from the intended
deployment configuration; existing Git history and release tags were preserved.

Editable `base.yml` and demo files stay in the working directory outside Git.
Completed configuration is copied, Vault-encrypted with the local password file,
placed in the private repository, verified by its header and decrypted equality,
then committed and pushed. The moved ciphertext was unchanged, and its private
commit was pushed before the public copy was removed. The local plaintext base
was created with restricted permissions. The password file stays outside Git.

Step 04 was deliberately left unchanged within this migration's scope. It still
references the former project-local base path, so loading from the private
repository must be implemented before it can run from this checkout alone.
No deployment or configuration jobs were launched.

## Adopt per-project versioning and reusable CaC templates

Implementation: `f3efca9`.

The user requested the same version policy used by the assistant-team project,
applied independently to this repository. The source baseline is `0.0.1`;
later feature commits increment minor and reset patch, while all other commits,
including documentation and history, increment patch. A version-bump helper and
incremental release notes make that convention reproducible. Published releases
use an annotated tag and a matching GitHub release on the exact version commit.

The user also distinguished two deliverables: a reusable CaC structure for other
operators and applicable configuration for our demos. Empty shared and per-demo
examples provide the former without exposing the latter. Operators fill copies
outside Git and encrypt sensitive completed configuration before committing it.
Existing encrypted configuration is retained; selecting demo profiles and fixing
target authentication remain future deployment work.

Vault password files stay outside Git, and ignore rules plus staged-file review
protect against accidental inclusion. Four CLI tests verify patch/feature changes,
project-relative file selection, and safe failure for invalid or missing versions.
The empty templates passed YAML structure checks. This validation does not claim
successful deployment of the current AAP pipeline.

## Keep the deployment project in its own repository

Implementation: `5f7597d`.

The initial commit explicitly describes the split from the umbrella repository
into an independent AAP deployment and CaC project. It contains the four-stage
pipeline, guarded teardown, and shared configuration. Earlier private history
is outside the scope of this retrospective. Historical plans describe separate
stages as a way to support independent execution and recovery.

## Read guest access settings from Vault variables

Implementation: `caec4cc`.

The commit message states that guest connection and installer-account values
were replaced with Vault variables and the missing variable-file load was added
to the first installation play. This made the split playbook runnable without
restoring environment-specific values to plaintext source.

## Update the image source and identify the Linux provisioning stage

Implementations: `81c9fd9`, `bbb82d8`.

These commits updated the image source setting and renamed the first playbook
to identify Linux VM setup. No extended rationale was recorded in their commit
messages. Matching the available image and making the stage's purpose clearer
are inferences from the changes, not documented decisions.

## Restore Windows configuration independently

Implementation: `5850626`.

The dedicated restore playbook accepts a supplied CaC file and separately
provided target authentication, with certificate validation enabled by default.
Its accompanying documentation describes applying configuration to an existing
AAP after shared prerequisites are present. It restores definitions without
launching the VM deployment jobs. A second-target restore was not verified.

## Make encrypted CaC files recognizable

Implementations: `63c89ed`, `c163e8a`, `4cdf25d`.

The commit messages explain that the shared CaC file contains credential inputs,
so its encrypted nature should be visible in its filename. The naming convention
settled on `PROJECT_PLACEHOLDER_CaC_vault.yml` for encrypted CaC and plain names
before encryption. Related references were updated without changing ciphertext.

## Keep the Vault variables inside the AAP project root

Implementation: `0b45904`.

The commit message documents that splitting the repository made the former
parent-relative Vault path point outside the synced AAP project. Moving `myvars`
into this repository and updating load paths makes the encrypted file available
inside the project root. The handoff reports a local variable-loading check;
that check does not establish full post-split deployment success.

## Canonical capture compatibility — 99cc306

Project captures move to one predictable `vaults/cac/<project-id>-cac-vault.yml`
path in each project's private companion. Commit99cc306 publishes compatibility
before private file removal: old consumers prefer canonical paths and shared
checkout temporarily retains the former AutoDeploy path. Extraction accepts the
canonical path and a narrow declared per-template shared-inventory reference,
while retaining older portable inventory aliases. This ordering avoids breaking
saved jobs during private publication. The implementation was validated offline;
SCM synchronization3165 completed at the same commit without running an import.

## One project importer and explicit API credentials — 305b0cd

Commit305b0cd replaces five import engines with one resource-driven playbook.
Separate Job Templates keep their fixed human-readable project IDs and saved
repository-specific read token/Vault pair. The ID derives the private repository
and canonical capture; protected environment data supplies its owner namespace.
Old playbook names are only fixed-ID aliases. Capture metadata maps existing
resource lists rather than introducing project-specific task branches or arbitrary
includes, preserving nested data and literal runtime templates.

The operator selects the inventory instance and an explicit native destination
API credential at launch. Its endpoint must match stored ansible_fqdn, and TLS
verification is mandatory. All AAP API requests run in the source execution
environment; installer-password scraping, SSH API delegation and source bearer
fallback are excluded from project import, selector authentication and prerequisite
API login. Existing infrastructure custom types are unchanged; their review was
explicitly deferred. Standalone import may target its source AAP, while the
optional preparation selector retains its separate fresh-target checks.

Shared resource handlers establish group skeletons before relationships, apply
EDA project settings completely, normalize Event Stream organization aliases,
and preserve existing activation states while creating new definitions disabled.
Persistent EDA and dedicated inventory-service access have explicit API-only
creation/reuse and proved-unsaved-token cleanup. Existing masked or ambiguous
access is preserved for explicit recovery. Windows public trust must be prepared
as encrypted input; missing trust never triggers an SSH workaround.

The actual source requirements cache matches the native-module fixtures. Full
offline regression passes170tests; focused real-capture rendering runs both
Ansible native modes, and impacted production lint passes. These checks establish
source behavior without importing a use case or running application/activation
operations. SCM publication and preserved-ID template metadata migration are
verified separately; functional use-case tests remain outside this change.


## Project-derived deployment names — 3028df4

Commit `3028df4` gives the five project deployment templates the display names
requested by the operator. Hyphens and underscores separate ID words; word order
is retained, first letters are capitalized, and AIOps/AAP use explicit acronym
overrides. A single tested helper derives selector lookups from project IDs, so
the public catalog no longer maintains independent display-name strings.
Repository names and project IDs remain unchanged.

The five existing production templates were renamed in place, including the
matching AutoDeploy survey title. Encrypted template definitions, selector
credential keys and extraction inventory-reference keys were aligned. Existing
IDs, repository credentials, launch settings, grants, schedules and numeric
workflow links were preserved; no application template or SCM Project was renamed.
Current protected diagnostic wording was copied from the five source surveys
into the desired capture without weakening secret logging.

Focused naming/selector, extraction and version regressions passed 28 tests;
production lint passed for the changed catalog. Protected readback compared all
124 template identities and all 76 workflow nodes. Eighteen current encrypted
YAML files across the five private repositories had no remaining old deployment
name references; historical migration evidence remains unchanged. Publication
and SCM synchronization do not establish a successful project import, and no
import, application job or activation was run for this naming change.


## Shared instance tokens, future public names and complete retirement

Implementation `fda45e8` keeps one generic CaC importer and each project's own
Git/Vault pair, selecting the destination bearer by inventory instance name from
the owner-approved temporary shared credential. Base reuses its existing MCP
token for remote API access, encrypts its per-instance record and updates the
source credential. This avoids fixed destination bindings; an external secret
manager remains the deliberate future replacement.

The same change derives future public names from the already consumed global
number while retaining existing VM keys and completed routes. The owner chose
future deployments only, then separately authorized retiring the old recovery
instance and building a fresh one. Decommissioning verifies the recovery host,
exact guest storage/UUID ownership and versioned DNS before removing related
guests, website/proxy/auth/cache/certificates and orphaned same-version records.
It removes obsolete active source inventory/API data but retains allocation
history. These are explicit owner requirements; production remains excluded.

Validation: 188 full-suite tests passed, plus focused real encrypted Git
publication/retirement and DNS/storage refusal checks; production lint passed
23 files. Live decommission/rebuild is a separate tracked verification step.

## Release verified generic guests through the existing deployment

The operator approved automatic removal of a successfully configured guest's
extra IPv4 recovery quarantine while retaining production destination denial.
The existing generic Linux job calls a shared role from an exact public source
revision. The existing publication action preflights source-job identity and
current policy, records verified ownership in the existing shared inventory, and
saves the release in the existing encrypted recovery captures and API metadata.
No new job, service, credential type, secret store or allocation record is added.
An unpublished failed release rolls back; a durably published release remains
for an idempotent source-inventory retry. Decommissioning retires only exact
selected identities and preserves production protection for other releases.

Implementation `183d3ce` passed all 249 repository tests, including native role
loading, encrypted-Git publication, interrupted source update/retry, exact guest
ownership, runtime rollback and unchanged token/allocation tests. Focused Ansible
syntax and production lint passed. Actual guest acceptance is checked separately
through the existing normal deployment template.

## Preserve project tasks and decisions independently of the running hypervisor

The operator requires Git copies of task progress and decisions because the
original host may be reinstalled. Beads remains authoritative. Implementation
`d74a61b` adds a generated public metadata overview and a complete scoped native
Ansible Vault recovery export in the existing Hactar repository. Private task
bodies and comments are encrypted; source data is read-only and both outputs
have stale checks. Unchanged decrypted data retains its ciphertext. No new
tracker, secret store, credential type or automatic database restoration is added.
The Hactar companion implementation is `40198b0`.

The agreed guide records external AAP recovery, independent version-to-version
acceptance, retention of the four older production stages while excluding them
from future CaC, newer-stage own/remote hypervisor requirements, self/remote CaC
installation and use-case-specific runtime targets. AO's deployment origin,
OpenShift destination and selected AAP integration are independent. AIOps must
use the intended versioned environment consistently. Requirements are separated
from successful live proof, and the older destroy-template review preserves the
original-host teardown limitation without deleting objects.

Validation passed nine exporter/native-Vault checks, six Hactar metadata checks
and four version checks. Actual scoped export, comments, exact decryption,
unchanged-record checks, prior task-ID retention and ownership-table preservation
were verified. README, restart instructions and project working rules describe
mandatory Git refresh and recovery without the current Beads database.

## Verify persistent bootstrap metadata and running guest ownership

Generic guest bootstrap saves its public provenance using `virsh desc --config`
after startup. Libvirt may therefore omit that description from running XML.
Implementation `d2d7254` requires the saved provenance in persistent XML and
checks any live copy if present. Both definitions must still match the exact
UUID, disk, network and MAC, and all hypervisor and guest identity checks remain.
This corrects verification of the existing native bootstrap behavior without
restarting guests or broadening the release policy.

The same fix checks command success and nonempty output before parsing runtime
JSON or deciding on rollback. Sixteen focused runtime, native-role and encrypted
publication tests pass, including failure-output handling and refusal of missing
persistent metadata or altered live ownership. A read-only execution against the
actual target passed with application disabled. Production lint passed.

## Verify automatic release through the normal deployment job

Source job 3282 completed configuration-only acceptance using Assistant revision
`6098490`, which pins AutoDeploy implementation `d2d7254`. The existing guest was
verified and released in that same job; no provisioning or package-update stage
ran. Independent inspection confirmed the selected release only, production
denies before release and established-connection allowances, unchanged VM
definitions and normal services, public connectivity and blocked production
access. Encrypted publication `fb476d1` and source inventory match the intended
transition, preserving instance tokens, allocation history and existing literal
template tags. The protected evidence is retained in the existing Hactar Vault.

This completes acceptance of the generic Linux deployment hook. Other guest
restrictions and the broader recovery acceptance work remain; a successful
selected-guest test is not a reason to lift quarantine for every VM.

## Preserve native firewall rebuild rules and omit empty group inputs

Implementation `1e89880` fixes two boundaries found during the current portable
deployment. A captured empty group-variable string is omitted before calling the
dictionary-typed native group module, matching the existing CoP role. Native
fixtures reproduce the former rejection and verify empty, omitted and nonempty
inputs in both Ansible modes.

The live guest permission also needs its exact native firewalld declaration in
the settings consumed by Hactar's base firewall playbook. Publication now saves
only the current operation's verified source/destination/port rule across the
three encrypted captures and source aliases. Prior rules, credentials and guest
identities are retained; conflicting states, priorities and duplicates for that
endpoint are refused. Three focused persistence tests and 34 related regressions
passed. Full regression validation of the preceding portable implementation
passed 275 tests; subsequent focused checks cover these corrections.

## 2026-11-05 — Register RHEL through the shared CaC importer

The exact reviewed RHEL-sniperpatching project ID now uses the common importer
and selected-use-case catalog. Deploy RHEL Sniperpatching CaC runs the shared
playbook directly with its fixed ID, dedicated repository reader/Vault pair and
existing inventory/token-store destination selection. The repository and capture
retain uppercase RHEL. The original five bootstrap pairs remain required; the
RHEL Git and Vault entries are optional together. No wrapper, authentication
mechanism or resource schema was added.

All 38 focused tests passed, including six protected captures under both native
modes, half-pair/case/reused-Vault refusals and rerun preservation. Three syntax
checks and production lint passed. Live import and host/application acceptance
remain separate.

Implementation commit: `d12d5a4ab72082d7de63637fe7ae400c703c8924`.

## 2026-11-05 — Verify the RHEL configuration deployment

The shared importer completed on the explicitly selected receiving AAP using
implementation `d12d5a4` and published source `0d52fc1`. Readback verified all
seven RHEL templates, six surveys and inventory/runtime/credential bindings,
while preserving existing template definitions. The imported read-only runtime
diagnostic then confirmed execution-environment, collection and Satellite API
readiness. Existing Machine selection remains separate from SSH-key equivalence
and receiving-host login. No wrapper or authentication mechanism changed.

## 2026-11-05 — Focus on the repeatable demonstration

Documentation commit `b62e89d` replaces the long opening run history with the
existing deploy, demonstrate and reset sequence. It corrects prerequisite order,
source bearer guidance, target selection and private capture filenames. The owner
requires observed failures to be fixed in normal automation; manual cleanup is
not a substitute for a working reset. Keep resource/production safeguards and
bounded waits, while avoiding additional recovery frameworks and repeated proof
collection. OpenShift runtime verification is deferred. Beads remains authoritative
with a public overview and encrypted Git recovery checkpoint.

## 2026-11-05 — Complete the lean RHEL demo

RHEL implementation `2be30c742f946b6f9c1ad93a9b7efbe14e230953` (source 0.5.7)
passed one complete RHSA/cutoff/full-update cycle on the workshop controller.
Both full updates ran and verified already-current outcomes. Receiving-AAP CaC
and runtime verification remain distinct from unproved client SSH access.
The current generated task overview and encrypted recovery checkpoint are preserved.

## Honor the isolated network's disabled DNS — 2026-11-05

Implementation `3f5c7e2` follows the native network declaration during Windows
release and retirement. Explicitly disabled DNS requires no matching DNS entry;
exact DHCP ownership remains mandatory. Enabled DNS retains both checks. This
fixes a real deployment mismatch without enabling DNS or weakening VM identity
checks. All twelve focused lifecycle tests passed, including DHCP-only networks
and refusal of missing DHCP, unexpected DNS or missing enabled-DNS records.

## Queue certified-content and readability cleanup — 2026-11-05

Documentation `632d2cb` adds task `bead-wd-72f.34` to the Git-visible overview.
The owner requires reviewing standalone helpers, custom Ansible plugins/modules,
embedded Python and other scripts against certified collections/vendor roles
first. Remaining custom code needs a concrete gap; cleanup must reduce opaque
helper chains and preserve readable workflows, clear errors and essential safety.
The task is queued rather than an unreviewed rewrite during functional testing.

## 2026-11-07 — Add Command Center to the reviewed CaC projects

Implementation: `d107d3fbd1be2ecd29c14bdb4b442f1ecba84757` (0.48.0).

The owner requested the same deployment arrangement as the existing projects.
Command Center now has a reviewed project ID, catalog entry and derived
deployment name in the common importer. Its dedicated repository reader and
Vault inputs are an optional complete pair, preserving the five required pairs
and optional RHEL pair. Bootstrap reruns preserve existing credentials.

CaC import installs reviewed platform definitions. The separate application job
still requires the selected workstation's account, native authentication,
tracker and protected application settings. Importing definitions does not
establish successful application deployment or public browser access.

All 41 focused importer, selector and bootstrap tests passed, including seven
protected captures in both native rendering modes. Three playbook syntax checks
and production lint passed. The public overview and existing encrypted recovery
export retain current task outcomes and all 150 baseline records. Live Command
Center import and application acceptance remain separate work.
