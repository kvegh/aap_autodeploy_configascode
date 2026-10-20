# Release notes

## 0.15.5

Document interpreter-preservation change `f23f1af` and encrypted capture `c141e1a`.
Live Orchestrator configuration import 2273 succeeded, and a separate verified
HTTPS read confirmed that the target inventory stores the job-time expression
literally. Functional Orchestrator deployment and cleanup were not run.

Validation: documentation, version and staged-content checks passed; the three
focused importer tests passed with the implementation commit.

## 0.15.4

Test and document deferred interpreter rendering for Orchestrator imports.
Companion encrypted capture `c141e1a` marks the existing localhost interpreter
expression `!unsafe`, preserving it for each imported job's execution environment
instead of storing the import process's Python path. Other decoded configuration
and secret inputs are unchanged.

Validation: all three focused Orchestrator tests passed, including actual CoP
wildcard/host-parameter rendering with different import and job Python paths.
Vault header, decryption roundtrip, actual Ansible loading and documentation
checks passed. Live import verification remains separate at this commit.

## 0.15.3

Document planning change `d7be1cc`: manual stage retries remain the selected
recovery method, and automatic workflow recovery is removed from the TODO.
Documentation diff, version and staged-content checks passed.

## 0.15.2

Document manual stage retries as the deployment workflow recovery method and
remove the automatic workflow recovery TODO at the operator's request. Retry
failed Job Templates with the same instance inputs, then run the remaining
stages. A full workflow relaunch still creates another instance.

Validation: documentation diff and version checks passed. No deployment code
or live configuration changed.

## 0.15.1

Document implementation `0b3910b` and encrypted capture commits `0146052` and
`62d6647`: current lifecycle definitions, target-local service access, preserved
secrets, empty new lifecycle groups, verified CA selection and safe reruns.
Documentation whitespace, version consistency and staged-sensitive-data checks
passed. Assistant rollout remains separate from the 70 offline checks.


## 0.15.0

Refresh Assistant Team configuration import for seven ordinary templates,
including Shutdown and the current controlled deployment/retirement surveys.
Import the inventory service identity and its dedicated inventory grant through
CoP before issuing target-local access. Reuse the captured credential schema;
generate a new encrypted service password and preserve a protected token copy
on each target. Verify TLS, token ownership/scope, permissions, saved bindings
and credential material on reruns; reject collisions without automatic rotation.
Revoke only this run's new token when failure proves it was not saved.

The companion Windows capture now includes patch-level assessment and WSUS
patch-ceiling templates, with existing definitions preserved and collection
pins aligned with the consolidated PAH catalog. Both refreshed captures use the
documented per-use-case PAH requirement schema. No imported VM, patching,
shutdown, retirement or provider-recovery automation was launched by this work.

Validation: 70 distinct offline tests passed, including 15 service-token behavior
checks and focused existing-user password and installer-CA tests. Existing users
must authenticate before definition updates, and their update payload omits the
password so metadata changes cannot reset it. Assistant playbook syntax, strict
Ansible rendering, whole-file Vault
round trips, preserved ciphertext/injector checks and object references passed.
The target's internal URL and installed CA passed a separate verified HTTPS
inspection. Assistant target rollout remains separate from these source checks.

## 0.14.5

Document planning commit `cce0e28` and the decision to retain current CaC
comparisons while audit-log catch-up remains future work. Record the checkpoint,
dependency, retention and coverage requirements without implementing automation.
Documentation whitespace and version checks passed.

## 0.14.4

Plan incremental CaC catch-up using component audit logs, durable checkpoints,
targeted configuration retrieval and dependency checks, with Git checks and
periodic full comparisons for coverage. Keep the current CaC comparison approach
until the future mechanism is implemented and verified. No log-based automation
or scheduling was added. Documentation whitespace and version checks passed.

## 0.14.3

Document fix `fb87a08`: fresh base setup uses the successful installer login for
PAH token issuance until the declared administrator password is applied, while
configured-password reruns preserve existing access. Documentation whitespace
and version checks passed; live base rerun verification remains separate.

## 0.14.2

Fix fresh base deployment when the desired administrator password is not active
yet. Retain the password that successfully authenticated in a protected local
fact and use it to issue PAH read tokens before password rotation; preserve the
desired `aap_password` for configuration and later verification. Configured-login
reruns retain their existing PAH credentials. No password is cached or passed in
workflow statistics/artifacts.

Three focused regression tests passed, covering fresh/rerun login selection,
pre-rotation PAH issuance, token preservation and failure cleanup. Base, PAH
preparation, AutoDeploy and curator syntax checks and whitespace checks passed.

## 0.14.1

Document implementation `768550d` and encrypted base policy `cd4a4ab`, including
repository-local latest selection, independently configured PAH limits, reviewed
pin/dependency exceptions and the external maintenance-window requirement.
Preserve the distinction between tested source behavior and pending live rollout.
Documentation whitespace and version consistency checks passed.

## 0.14.0

- Declare latest-plus-required collection retention in encrypted base; Stage 04
  configures and verifies each remote's highest-version selection and each
  repository's single-snapshot retention without syncing or deleting content.
- Add a separate preview/apply curator. Preserve each repository's newest installed
  release, actual reviewed project/playbook/EE requirements,
  and dependency closure. Reject incomplete or changed audits, active target
  work, missing dependencies and stale previews before pruning associations.
- Document the external-client/seed requirement, maintenance window, mutable
  image limitations and remaining production audit/recurring execution work.
  No production curation or global content deletion was performed.
- Nineteen focused retention tests passed. The 52-test broad run passed every
  other test; its legacy PAH guard fixture was updated for the required policy
  and that focused guard test then passed, including unsafe-policy cases.
  Stage 04/curation syntax, whitespace, and private Vault round-trip checks passed.

## 0.13.1

Document source implementation `6c83591`, encrypted companion capture `9020feb`,
and the ownership, dedicated-key, job handoff and PAH preparation decisions.
Record the offline verification boundaries and remaining recursive/runtime tests.

## 0.13.0

- Add the complete deployment workflow: VM creation, infrastructure, installation,
  base, explicit PAH/image preparation, then five parallel imports for AIOps,
  Disconnected Windows, Orchestrator, Assistant Team and AutoDeploy itself.
- Hand over only the generated VM identity, address and internal API URL. Keep
  installer FQDN handling separate, retain credentials on each Job Template, and
  exclude teardown and imported demo jobs from the workflow.
- Add the AutoDeploy use-case importer and empty public schema. Its populated
  capture, provisioning inputs, references, workflow repository mapping and exact
  PAH requirement catalog are whole-file Vault encrypted in the existing private
  companion. The approved dedicated hypervisor key has independent SSH/sudo
  verification and is separate from the agent's GitHub identity.
- Prepare exact collection versions in batches, preserve older explicit pins,
  restore complete requirements after failures, observe asynchronous policy
  changes, and clean temporary API authentication and private files.
- Thirty existing/graph tests and three additional real-task mock-PAH tests passed.
  Playbook syntax and private Vault round-trip/reference checks passed. Fresh
  recursive execution, complete production coverage and Windows runtime
  compatibility remain unverified. No workflow was launched for validation.

## 0.12.7

Document planning commit `9dad713` and the reason for reviewing this AAP 2.7
implementation against Red Hat's CaC guidance. The review remains a TODO.
Documentation whitespace and version consistency checks passed.

## 0.12.6

Document a planned review against Red Hat's Configuration as Code guidance.
The review covers access and tokens, content sources, export completeness,
secrets, validation, drift, deletions, and Git workflow, with applicability
checked against AAP 2.7 and the project's existing CoP collections.
Clarify that target-side MCP token creation is implemented while encrypted
repository storage and client setup remain planned.

Validation: documentation whitespace, source link and version consistency checks.
This planning change does not modify platform configuration.

## 0.12.5

Document implementation `5f8c3e0` and the distinction between installer async
runtime and the surrounding Job Template timeout.

## 0.12.4

Allow the AAP installer and its existing-job observer up to two hours instead of
one, avoiding premature async termination during fresh installation. The
installation template needs a three-hour timeout for preparation and checks.
Stage 03 passed syntax validation; no installer was launched for this check.

## 0.12.3

Document implementation `6ad202d` and the DNS authorization logging boundary.

## 0.12.2

Protect DNS creation and removal requests with `no_log` so API authorization
headers remain hidden in AAP job results. Both playbooks passed syntax checks;
no teardown was repeated for validation.

## 0.12.1

Document implementation `18f50b2` and the shared bootstrap boundary, collision
guards, preserved credentials on reruns, and offline-only verification.

## 0.12.0

- Create the four private-configuration Git credentials and the CaC Vault
  credential from encrypted base during Stage 04. Reuse the compatible Git
  injector, reject conflicting object ownership/type/Vault identifiers, and
  preserve existing hidden secret values on reruns.
- Verified with four isolated tests running the real Ansible tasks against a
  synthetic Controller API. No configuration deployment was launched for this
  feature's validation.

## 0.11.1

Document implementation `5542cbd` and its rationale: provision persistent
administrator MCP access after final base login verification, preserve existing
access on reruns, and keep a recoverable copy in private target-side storage.
Distinguish that interim storage from planned encrypted repository write-back,
client trust setup and controlled rotation.

Validation: the implementation passed all 23 offline tests and its Ansible
syntax check. This documentation update passed whitespace and version-header
consistency checks. No live deployment or token change was performed.

## 0.11.0

Create persistent administrator MCP access during base configuration after the
final administrator login is verified. Generate a target-specific write-scope
token and atomically save its recoverable JSON copy in root-owned private storage
on that target. Validate and preserve saved access on reruns; preserve existing
manual access without issuing a duplicate or replacing its secret. Reject
ambiguous metadata, mismatched or expired saved access and unsafe storage. Revoke
a newly generated token after a failed save only when its copy is proven absent.

Validation: seven offline tests exercised the real tasks against a
local Gateway API fixture, including first creation, recovery-file permissions,
reruns, manual-token preservation, rejected saved access and interrupted saves.
Secrets stayed out of output with diagnostic logging enabled; an integration
check verified provisioning follows final login verification and leaves ordinary
temporary-token cleanup intact. Stage 04 passed its Ansible syntax check.
The complete offline suite passed all 23 tests using the installed runtime collections.
No live base job, VM operation, encrypted Git write-back or external client setup
was performed.

## 0.10.8

Document maintenance commit `67de471` and its rationale in the decision history:
keep newest present releases plus explicit older project pins, apply the remote
version cap independently from snapshot retention, and retain the encrypted CaC
and recurring-enforcement TODOs. The live cleanup completed before this
documentation commit; no additional PAH changes are introduced here.

Validation: all 15 published collections were independently checked through MCP;
the API audit verified 16 retained releases, unchanged project requirements and
completed cleanup tasks. Documentation whitespace, version-header consistency
and staged-file review passed.

## 0.10.7

Document the reviewed one-time PAH cleanup: 263 collection releases reduced to
16 across 15 collections, preserving newest present releases and the older RHEL
system roles release explicitly pinned by projects. Distinguish the applied
remote `sync_highest_versions: 1` limit from repository snapshot retention and
describe exact dependency pins. Track the remaining encrypted CaC integration,
module support and recurring enforcement separately from the completed
maintenance. No cleanup automation is introduced by this documentation change.

Validation: both repository cleanup tasks completed; retained content and project
requirements were audited. All three remotes use exact pins and a version limit
of one; all repository snapshot limits remain one. Documentation whitespace,
version-header consistency and staged-file review passed. No global orphan
cleanup or runtime automation jobs were run.

## 0.10.6

Document planning commit `c547f68` and the rationale for keeping only justified
PAH collection versions in the decision history. Version selection, retention
enforcement and cleanup remain planned.

Validation: documentation whitespace, version-header consistency and staged-file
review passed. No deployment or content deletion is part of this documentation.

## 0.10.5

Document the planned PAH collection version policy: synchronize and declare only
project-required versions and dependencies in CaC, retain multiple versions only
when those requirements need them, and avoid unbounded release-history downloads.
Audit project and execution-environment requirements before pruning older content.
Retention enforcement and cleanup remain unimplemented.

Validation: documentation whitespace checks and staged-file review passed.
This planning change does not deploy configuration or remove collection content.

## 0.10.4

Document planned per-instance MCP API-token provisioning and recoverable,
Vault-encrypted connection values in the private base configuration repository.
Track a separately scoped Git write credential, opaque instance filenames,
protected client configuration, CA trust, reruns and rotation. The operator will
create the current target's API token manually; no token provisioning or write-back
automation is implemented or launched by this planning update.

Validation: documentation whitespace checks and staged-file review passed.
No AAP jobs, API tokens or credentials were created or changed.

## 0.10.3

Document the verified Assistant Team configuration import and its two encrypted
configuration fixes: omit empty credential names for public code projects and
mount the installer's generated CA trust read-only through base Controller
settings. Add generic host-path guidance to the empty base template and keep
certificate verification enabled. Track complete Intelligent Assistant/Lightspeed
CaC capture and independent rebuild as a new TODO; that service is unchanged.

Validation: base job 2137 applied the trust setting, both source-project sync
retries succeeded through local PAH, and import job 2139 restored all 21 ordinary
objects and six templates. Independent trusted-TLS comparison passed 396 checks.
Private Vault round-trip and actual importer guards passed; six inner ciphertexts
were preserved. Token and workspace cleanup succeeded. Runtime deployment,
recovery, provider calls and optional authentication maintenance remain untested.
Documentation whitespace and empty-template YAML checks passed.

## 0.10.2

Document the completed administrator-password rollout from implementation
`1216f38` and mark its verification TODO complete. Job 2125 applied the encrypted
base password and updated the deployed installer inventory with mode `0600`.
Job 2128 reran successfully with the configured password and skipped installer
bootstrap. Both used source `c51aede` and removed their run token and workspace.

Validation: independent trusted-TLS checks confirmed the desired login, matching
installer password and permissions, no remaining configuration-run tokens, and
preserved use-case object counts and EDA activation states. The first run had
88 successful tasks and the rerun 85, with no failures or unreachable hosts.
Documentation whitespace checks passed. The sixteen local implementation tests
and Ansible syntax checks had already passed before rollout.

## 0.10.1

Document the primary goal: recreate production AAP configuration and capabilities,
including the ability to deploy further AAP instances. Explain the initial seed's
independent Git and Vault access, encrypted credential inputs for trusted
replacements, and the resulting trust boundary. Track complete production
coverage, bootstrap provisioning, deployment templates, job handoff, functional
tests and controlled takeover as remaining work. Document administrator-password
implementation `1216f38` while keeping live rollout verification pending.

Validation: documentation whitespace checks passed. No deployment, configuration
import or production takeover was launched for this documentation.

## 0.10.0

Manage the desired administrator password from the encrypted base configuration.
Try that login first, bootstrap from the deployed installer only when it is not
active, and let the CoP Gateway user role apply the account password. Verify a
fresh login, keep the deployed installer password current for use-case imports,
and protect password operations even during diagnostics. A configured-password
rerun does not need installer access.

Validation: all sixteen local tests passed. Seven authentication scenarios
exercise bootstrap, reruns, legacy configuration, rejected passwords and
access/server failures without logging secrets. Ansible syntax, Vault round-trip
and whitespace checks passed. Live rollout and final verification are documented
separately after they complete.

## 0.9.2

Use the existing CaC Git-token credential type for Assistant Team's private
configuration import. Require an HTTPS repository URL and the injected
`CAC_GIT_TOKEN`, and use the same temporary askpass authentication as the other
importers. Keep TLS verification enabled and tokens out of URLs, command
arguments and the helper's stored contents. Remove the unused SSH credential
type; no SSH key or credential was created.

Validation: all fifteen local tests passed, including eight repository URL
cases, missing/present token checks, encrypted capture guards and failure cleanup.
Full Ansible syntax and whitespace checks passed. No Assistant Team import or
runtime automation was launched.

## 0.9.1

Document the dedicated Assistant Team importer in `614763a`, its read-only SSH
bootstrap access, encrypted snapshot guards, definition-only scope, optional
maintenance separation and focused validation. No additional target import or
runtime automation was launched. Documentation whitespace checks passed.

## 0.9.0

Add a dedicated Assistant Team configuration importer for the six ordinary
deployment, lifecycle and recovery templates and their supporting AAP objects.
Read the encrypted capture from the private companion's `main` branch through
an injected repository-scoped SSH key and independently trusted host keys.
Require strict SSH host verification, complete ordinary secrets and all six
embedded Vault ciphertexts. Keep optional authentication maintenance untouched;
its unresolved target inputs do not block an ordinary definition import.
Reject job launches and schedules, protect credential diagnostics, revoke the
temporary Gateway token, and clean the checkout even if token revocation fails.

Validation: all fourteen local tests passed. New coverage exercises sixteen
actual encrypted-capture/core guard cases, six SSH repository URL cases and
three token/workspace cleanup scenarios. Full syntax and the current encrypted
capture preflight passed. No Assistant Team import or runtime automation was
launched during implementation; PAH and image preparation precede a live import.

## 0.8.3

Document consistent Orchestrator EE references and the refreshed Assistant Team
capture. Public code access replaces the obsolete code SCM secret; encrypted
configuration snapshots supply ordinary deployment and recovery inputs. Keep
authentication maintenance separate with explicit authorization for the target.
Declare PAH collection and execution environment prerequisites before project sync.

Validation covers object references, strict Ansible rendering, native export of
all seven Assistant Team templates, Vault round trips, and equality of the six
embedded ciphertexts. No configuration import, automation, or provider
authentication refresh was launched.

## 0.8.2

Document the successful protected PAH base rollout and independent verification:
three remotes, repositories, distributions, and ordered local download sources;
public Galaxy unattached; collection versions unchanged and no content sync;
existing read tokens preserved; temporary tokens and workspace removed. Mark
the live PAH verification TODO complete. Use-case content preparation and
functional tests remain separate. Documentation whitespace checks passed.

## 0.8.1

Document the dedicated Orchestrator configuration importer in `de5b54c`, its
separate bootstrap access and runtime launch inputs, definition-only scope,
protected diagnostics, cleanup guarantees, and focused offline validation.
No configuration import or Orchestrator runtime operation has been launched.

## 0.8.0

Add a dedicated Automation Orchestrator configuration importer. Load only its
reviewed, whole-file Vault-encrypted private capture; validate registry inputs,
reject job launches and schedules, and import definitions through CoP dispatch.
Keep Git access, credentials, wildcard values, and temporary Gateway tokens
protected during diagnostics. Revoke the run token and clean the checkout on
ordinary failures, including failed token revocation. Imported deployment and
cleanup Job Templates are never launched by the importer.

Validation: all eleven local tests passed. New coverage runs eleven real Vault
loading/preflight cases and three token/workspace cleanup scenarios. Full
playbook syntax and the existing encrypted capture preflight passed. Live
configuration import has not been launched.

## 0.7.5

Document the Hub API's paired upstream authentication requirement and the
URL-only base correction in `bf12d01`. Preserve local credentials and the
separation between setup and synchronization; live rollout awaits a rerun.

## 0.7.4

Keep upstream authentication URLs out of the URL-only base until their upstream
tokens are supplied. Hub rejects an authentication URL without a token even when
no synchronization is requested. Validate this pair before modifying the target,
extend the protected regression cases, and document the future sync prerequisite.
Local PAH download credentials and tokens are preserved.
Both focused PAH tests passed, including seven configuration cases and the
credential lifecycle; syntax, populated-base guards, and Vault equality passed.

## 0.7.3

Document the API-summary correction in `40906b1` and its focused PAH regression
validation. Existing credentials remain preserved; the earlier Hub remote
failure still requires a diagnostic rerun.

## 0.7.2

Validate existing PAH credentials using the type name returned by AAP's summary
API. That summary omits `kind`; the original guard therefore stopped a rerun
after credentials had been created. Correct the real-module regression fixture
to use the actual API shape. Credential tokens remain preserved.

## 0.7.1

Document the base PAH implementation in `5fc2c98`: local repository sources,
separate management and persistent read tokens, rerun preservation, failure
cleanup, and synchronization exclusions. Nine tests, syntax checks, populated
base validation, and Vault round-trip checks passed; live rollout remains pending.

## 0.7.0

Extend Stage 04 base configuration with certified, validated, and community PAH
remotes, repositories, download distributions, and ordered organization sources.
Replace direct Galaxy downloads with local PAH credentials. Create a read-scope
Gateway token only when a repository's credential is missing; preserve matching
credentials on reruns and clean up demonstrably unsaved tokens after failure.
Keep target tokens separate from the reusable encrypted base and from each
run's temporary management token. No collection content is synchronized.

Nine tests passed, including actual Ansible execution of five PAH configuration
guards and the real Controller credential module against a local API fixture.
The token regression covers creation, rerun preservation, failed saves before and
after persistence, credential drift, and protected output with diagnostics enabled.
Stage 04 syntax and the populated working base guards passed. Target rollout
remains pending.

## 0.6.5

Document the PAH ownership, bootstrap credential separation, clean-target group
ordering, and step-by-step CaC guide TODO implemented in `d2e6988`. Preserve the
distinction between successful live import using the preceding source and the
offline-validated ordering fix. Documentation whitespace checks passed.

## 0.6.4

Keep PAH collection synchronization out of base dispatch. Base owns the certified,
validated, and community repository setup; use cases declare their collection
requirements separately. Extend the empty templates and document bootstrap Git
credentials versus target project SCM credentials. Add a TODO for a complete
step-by-step CaC guide and the remaining PAH implementation.

Create Windows inventory groups before applying their memberships so a parent
cannot race child-group creation on a clean target. Seven tests passed, including
the real group module's missing-child regression and existing dispatcher and
preflight checks; both changed playbooks passed syntax checks. Live Windows
import succeeded after a retry with the preceding source; this group-order fix
has not yet been deployed. PAH repository configuration remains pending; no
collection synchronization was performed.

## 0.6.3

Document the protected Git failure classification implemented in `5ccb0ca` and
its validation of fixed messages, secret protection, and workspace cleanup.
Documentation whitespace checks passed. Live error classification awaits rerun.

## 0.6.2

Report a safe failure category when the Windows private configuration checkout
fails. Keep raw Git errors protected and distinguish repository access/not found,
DNS, TLS/certificate, redirects, connection/timeout, and other errors. Document
that the Git token must grant read access to the selected configuration repository.

Validation: seven synthetic Git failures produced only fixed categories, exposed
neither synthetic secrets nor raw errors, and ran the actual workspace cleanup.
Syntax, existing regression tests, and whitespace checks passed. The first live
Windows attempt stopped at checkout before target changes; a diagnostic rerun is
needed to identify its category.

## 0.6.1

Document the separate Windows configuration importer implemented in `a84bf09`,
including its definition-only scope, independent private repository input, and
protected wildcard/credential logging during diagnostics. Documentation and
whitespace checks passed. Live Windows import remains pending.

## 0.6.0

Add a dedicated disconnected Windows CaC import. It retrieves only the encrypted
Windows definitions from the private repository's `main`, requires reviewed
configuration and complete secret inputs, and dispatches AAP objects without
running the imported jobs or workflows. Reject launches and schedules, preserve
protected credential logging during diagnostics, and clean temporary Gateway
authentication and the checkout. Subscription and shared base remain separate.

Validation: full Ansible syntax check, the real CoP dispatcher regression, seven
Windows preflight cases, version-tool tests, and whitespace checks passed. Live
Windows configuration import has not yet run.

## 0.5.12

Document the Event Stream dispatch correction in `a64e16c` and successful live
AIOps configuration deployment. Job 2018 completed in 94 seconds with 131
successful tasks and no failures. Independent TLS-verified API checks found all
29 expected objects, both Controller project syncs successful, and both EDA
activations running. Temporary configuration and verification tokens were revoked;
the configuration checkout was removed. Functional remediation tests remain pending.

Validation: real dispatcher regression, six focused stream/activation checks,
syntax, live deployment, object comparison, and documentation whitespace passed.

## 0.5.11

Keep Event Stream creation out of initial AIOps dispatch. CoP 4.10.0 does include
an Event Stream role, contrary to the earlier documentation, and it expects
`organization` in each data item. Our explicit module task uses
`organization_name`; dispatching the same definitions first caused a live
missing-organization error. Exclude that role alongside activations so the
dedicated stream task runs after prerequisites and before activation creation.

Validation: the live diagnostic confirmed the exact missing-organization error.
Ansible syntax and six isolated Event Stream/activation checks passed. A real
CoP dispatch regression passed; removing either stream or activation exclusion
fails safely in check mode before module execution. Live rerun follows this fix.

## 0.5.10

Document installer monitoring recovery implemented in `64aec45` and the fresh
four-stage deployment completed as individually launched jobs. Live resume
verified the original installer's successful exit and Controller health without
restarting installation. Step 04 applied the subscription and platform-only base
in 22 seconds; temporary token and workspace cleanup succeeded with protected
logging enabled. AIOps deployment remains unlaunched.

Validation: live recovery and base deployment passed; documentation whitespace
checks passed. Automatic inter-job handoff remains planned.

## 0.5.9

Recover monitoring of an existing Stage 03 installer through the optional
`aap_installer_resume_job_id`. Resume mode skips host preparation, inventory
changes, and installer launch; it checks the existing async result before the
Controller health check. Protect captured installer output and reject invalid
job identifiers. Document separate Controller and remote installer time limits.

Validation: Ansible syntax and whitespace checks passed. The live installation
was interrupted by the Controller's overall timeout; successful installation
and the new resume path have not yet been verified live.

## 0.5.8

Document the unified CoP credential item schema implemented in `91b5fc6` and the
successful syntax and credential lifecycle checks. Whitespace checks passed.
This follow-up changes documentation only; live AIOps deployment remains pending.

## 0.5.7

Use the CoP credential item schema consistently for AIOps EDA credentials:
`organization` and `credential_type`. The target-specific Controller credential
handler translates those fields into the EDA module's argument names. This makes
the exported configuration compatible with both ordinary dispatch and the special
target-token handling, without duplicate field aliases.

Validation: full Ansible syntax check and eleven isolated credential checks with
the installed EDA module passed, including secret protection, target-token
creation/preservation, and cleanup. No live AIOps deployment was launched.

## 0.5.6

Document Event Stream and activation ordering implemented in `33f2575`, the
CoP field omissions supplemented through EDA modules, and the target-specific
reference policy. Whitespace checks passed. This follow-up changes documentation
only; the AIOps Job Template remains unlaunched.

## 0.5.5

Create AIOps Event Streams before their rulebook activations. CoP dispatch
4.10.0 does not create streams, so the playbook first applies prerequisites,
then uses `ansible.eda.event_stream`, and finally applies the activation role.
Require named stream mappings and resolve new target IDs and source metadata
without copying source-instance IDs or UUIDs. Preserve EDA project revision-on-
launch and cache settings with the supported project module after dispatch.

Validation: full Ansible syntax check and ten isolated checks using the actual
EDA modules and CoP activation role passed. They cover dependency order, target
ID resolution, incomplete mappings, API failures, and project revision settings.
These checks used a synthetic API. The live AIOps Job Template remains unlaunched.

## 0.5.4

Document the Stage 02 dependency fix in `97e3236`, why its earlier successful
implementation differed, and the collection-based DNS decision. The existing
execution environment has compatible Ansible Core and `dnspython`; PAH curation
and the requirements file provide the missing collection. Whitespace checks
passed. This follow-up changes documentation only.

## 0.5.3

Use `community.general.dig` for Stage 02 DNS checks and declare the missing
`community.general` 11.4.0 collection for PAH-backed project synchronization.
This retains the collection-based playbook style and checks the expected public
A record, rather than accepting any nonempty DNS result. The execution
environment also needs `dnspython`; collection downloads do not install it.
This supersedes the HTTPS DNS implementation in 0.5.2.

Validation: Ansible syntax and whitespace checks passed. Collection compatibility,
PAH availability, runtime dependencies, and the live retry are checked separately.

## 0.5.2

Restore Stage 02's successful HTTPS DNS check using `ansible.builtin.uri`.
The standalone checkout had an unprovided `community.general.dig` lookup instead
of the implementation used by successful deployment job 993. Wait for the
expected public A record before certificate issuance without adding runtime
dependencies. Earlier VM creation and teardown stages do not need repeating.

Validation: compared successful job 993 with failed job 1996, checked the
playbook syntax, and checked whitespace. Live retry follows this source fix.

## 0.5.1

Document the base/use-case ownership split and AIOps deployment implementation
in `e864dc9`, including the user's current-demo selection, independent copies,
secret/readiness checks, target-only EDA token handling, and unlaunched state.
README and templates describe the same boundaries. Whitespace checks passed;
this follow-up changes documentation only.

## 0.5.0

Add a separate AIOps configuration deployment playbook for an AAP that already
has platform base configuration. It loads only the encrypted `cac/aiops_demo.yml`
from private Git, rejects incomplete captures and missing secrets, and creates
target-specific EDA Controller access without copying a source-instance token.
Reruns preserve that credential and reject conflicting settings. Temporary
configuration tokens and checkouts are cleaned; persistent EDA access remains
available to the imported activations. The new entry point must not run yet.

Clarify base ownership and update the empty templates: platform setup belongs
to base, while use-case projects, credentials, inventories, templates, and EDA
integrations belong to their own configurations. The current private base was
reduced to its organization and existing platform setting, with its previous
definitions preserved outside Git. AIOps owns copies of formerly shared source
inventory, credentials, and runtime environments. External setup is deferred.

Validation: full Ansible syntax check passed. Eleven isolated real-Ansible
checks using the installed EDA credential module passed, covering readiness,
missing secrets, first deployment, preserved credentials, drift rejection,
and token/workspace cleanup after failures. These checks used a synthetic API;
the AIOps deployment playbook was not launched against a live AAP.

## 0.4.4

Document the first successful complete Step 04 shared-base configuration run.
The job retrieves encrypted configuration and the manifest from private Git,
authenticates using the installer password and a temporary Gateway token, and
applies the shared AAP objects. Live job 1985 used source `7d65678`, completed in
162 seconds with 147 successful tasks, 36 changes, and no failures, preserved
the previously imported subscription, revoked its token with HTTP 204, and
removed its temporary workspace. Saved debug logging remains false.

The project polling wait completed successfully after 46 seconds; its retry
messages did not indicate repeated failed project creation. Reviewed the full
job events and the saved Job Template default. Documentation and whitespace
checks passed. Per-demo loading and the full deployment pipeline remain pending.
This update changes documentation only and publishes no release tag.

## 0.4.3

Document the AAP 2.7 dispatch compatibility decision implemented in `44e1045`,
the successful subscription import, collection-artifact validation, and cleanup
limitation. README describes the same behavior. Whitespace checks passed;
this follow-up changes documentation only.

## 0.4.2

Exclude the legacy Controller application role from Step 04 dispatch on AAP 2.7.
The installed `ansible.controller` 4.8.11 collection lacks its application module;
Gateway application management remains enabled through `ansible.platform`.
Other roles remain selected. Clarify that fatal role-loading errors can prevent
Ansible cleanup. Live testing of the preceding authentication fix successfully
read the installer password, created a Gateway token, and imported the subscription
before encountering this role-loading error; its leftover token was revoked.

Validation: inspected the actual five PAH collection artifacts and verified all
59 module references across the 58 selected dispatch roles, retaining Gateway
applications and Controller role assignments. No collections were installed for
this check. Focused token lifecycle checks and whitespace validation passed.
Full configuration verification remains pending.

## 0.4.1

Document authentication bootstrap implemented in `62ab119`, the verified
installer-password mismatch, Gateway token use, cleanup ordering, and remaining
scope. README already describes the implementation. Documentation and
whitespace checks passed. No runtime behavior changes in this follow-up.

## 0.4.0

Bootstrap Step 04 authentication from the target installer Gateway password,
read over SSH with the existing environment credentials and sudo. Accept an
explicit current `aap_password` from encrypted configuration to skip installer
access. Replace the stale saved-password assumption with a per-run Gateway
token for subscription import and dispatch. Revoke the token afterward and
remove the private workspace even when configuration or revocation fails.
Keep password rotation as separate work and preserve the debug logging control.

Diagnosis: the target installer Gateway password differs from the value the
previous job used; its Controller password differs too. Values were not printed.
Five isolated Ansible checks passed: installer bootstrap (including quoted
password punctuation), explicit-password override, configuration rejection,
authentication rejection, and revocation failure. Checks verified token use,
revocation attempts, workspace cleanup, and protected output. YAML/whitespace
checks passed; live subscription/configuration verification remains pending.

## 0.3.2

Document that the multiple-choice debug survey requires quoted `"true"` or
`"false"` values in API launches. The playbook still accepts native Booleans
when run directly and normalizes survey strings. Verified that the API accepts
the survey-compatible debug launch and that the saved default remains false.
Whitespace checks passed. This documentation change does not alter logging or
claim a successful subscription import.

## 0.3.1

Document Step 04's debug logging decision implemented in `ff84279`, including
the user's chosen name and meaning, protected defaults, survey override, and
unchanged scope for other templates. Reviewed README and grouped the execution
environment prerequisites with the other Step 04 inputs. Whitespace checks
passed. No runtime behavior changes in this documentation follow-up.

## 0.3.0

Add `debug_logging` to Step 04 only. Default to `false`, enabling `no_log` and
the dispatch collection's secure logging. Setting `true` disables those logging
protections for troubleshooting. Accept native Booleans and the survey strings
`true` and `false`; reject other values. Document that debug job output can
include sensitive decrypted configuration. The existing Job Template now has
a saved `false` default and an optional true/false survey with the same default.
Other projects retain their current controls; broader consistency stays a TODO.

Validation: six isolated Ansible checks passed for the protected default, native
and survey Boolean values, dispatch setting, output visibility, and invalid
input rejection. All nine existing Step 04 `no_log` settings use the tested
inverse expression. The live template's default, survey, and retained settings
were verified; whitespace checks passed. These checks did not apply target
configuration or import a subscription.

## 0.2.6

Document the TODO for consistent extra-variable names, Job Template defaults,
survey and launch overrides, Boolean handling, and logging controls. The audit
found four logging variable names in existing templates; the TODO covers
aligning them with their playbooks while keeping sensitive output protected by
default. Reviewed README; it remains accurate. Whitespace checks passed. This
adds planning documentation only; no templates or playbooks changed.

## 0.2.5

Document the PAH-only collection sourcing decision implemented in `2725894`,
the user's curation requirement, verified organization source removal, and the
managed credential deletion restriction. README already describes this policy.
Documentation and whitespace checks passed. This follow-up changes no AAP
settings or playbook behavior and launches no jobs.

## 0.2.4

Document PAH as the exclusive collection source for project downloads. Sync
certified, validated, and community content and all required dependencies into
PAH before project synchronization; direct public Galaxy access is not
recommended and must not be an organization fallback. Public Galaxy may remain
an upstream for PAH community synchronization. Explain source bootstrap and
encrypted CaC credentials, and remove the restore guide's implicit public
Galaxy install command.

Operational verification: removed the public Galaxy source from the existing
organization and verified that its three PAH sources remain in order. AAP
rejects deletion of the platform-managed public Galaxy credential; the
protected object remains unattached. Documentation and whitespace checks passed.
No playbook behavior changed and no jobs were launched for this policy change.

## 0.2.3

Document the project collection requirement implemented in `9243762`, why a
collection stored in private Hub also needs to be downloaded for the job, and
the separate responsibilities of requirements and organization source credentials.
The README already describes the implementation. Whitespace and staged-file
checks passed. This documentation commit does not install dependencies or verify
a live project synchronization or job run.

## 0.2.2

Declare `infra.aap_configuration` version `4.10.0` in
`collections/requirements.yml` so AAP can download the missing dispatch role and
its declared collection dependencies during project synchronization. Explain
that the requirements file selects collections while the organization's Galaxy
credentials select download sources, including a private Hub `validated`
repository. The execution environment still supplies Python and system packages.

Validation: the requirements YAML contains exactly the requested collection and
matches the published Galaxy version; staged-file and whitespace checks passed.
No dependencies were installed locally, no AAP settings were changed, and no
project synchronization or job was launched. Runtime availability still requires
a successful project synchronization.

## 0.2.1

Document subscription application implemented in `7503d96`, including automatic
use of the attached Vault credential, private ZIP handling, failure ordering,
cleanup, and preservation of an existing non-trial license. The README already
describes the implementation. Whitespace checks passed; this documentation
commit does not change runtime behavior or claim a successful live run.

## 0.2.0

Apply the AAP subscription before configuration in Step 04. Require the complete
manifest ZIP as `cac/manifest.zip.vault` in the private repository. Use the
attached `cac` Vault credential through Ansible's copy action to restore it into
a mode-`0600` temporary file, then upload it with `ansible.controller.license`.
Keep `force: false` so reruns preserve an existing non-trial license. Failed
decryption or import prevents dispatch; cleanup removes the ZIP and checkout on
success or failure. The launch inputs and existing credentials are unchanged.

Pre-launch validation: six isolated manifest-flow checks passed, including exact
binary ZIP restoration, restrictive permissions, rejection of plaintext, missing
and corrupt payloads, wrong-password failure, configuration blocked after a
simulated subscription rejection, and cleanup in every case. The license API was
simulated because its collection and the dispatch role are not installed locally.
Whitespace checks passed. No live subscription or configuration was applied as
part of these checks.

## 0.1.4

Document the TODO for automatic variable handoff between deployment jobs,
including discovered VM name/address values and Step 04's explicit API URL.
Identify AAP workflow artifacts as the native mechanism and retain independent
stage inputs. Reviewed the README's existing statement that automatic handoff
is pending; it remains accurate. Whitespace and staged-file checks passed.
This adds planning documentation only; no playbooks changed or AAP jobs ran.

## 0.1.3

Document the explicit Step 04 target URL decision and its implementation commit.
Keep the installer hostname, API connection address, remaining authentication,
and future automatic address handoff distinct. No runtime behavior changed.
Validation: documentation review and whitespace checks passed; no AAP jobs ran.

## 0.1.2

Require an explicit `aap_hostname` HTTPS URL for Step 04. Remove the derived
`vm_name`/domain default and reject missing or invalid targets before downloading
configuration. Operators can choose an internal hostname or IP without depending
on provisioning names or the public reverse proxy. Document the required launch
inputs and keep Step 03's installer FQDN separate.

Validation: nine isolated input checks passed, including internal DNS and IP URLs
without provisioning variables and rejection of missing, malformed, HTTP, and
credential-bearing URLs. All eleven HTTPS Git/Vault loader checks passed with
the explicit target input. Whitespace checks passed. The real dispatch collection
and live target were not exercised; no AAP jobs or remote configuration changes
were performed. Steps 01-03 remain unchanged.

## 0.1.1

Document private configuration loading implemented in `fd35d02`, including the
separate Git-token bootstrap, fixed `main` policy, secret-safe temporary download,
retained `myvars`, and validation limits. Reviewed the README and confirmed it
matches the implementation. Whitespace and staged-file checks passed. No AAP jobs
were run and no release was published.

## 0.1.0

Load Step 04's encrypted shared configuration from a private HTTPS Git repository
supplied as `aap_config_repo_url`, always using `main`. Authenticate through the
injected `CAC_GIT_TOKEN` and a temporary askpass helper. Require a whole-file
Ansible Vault payload at `cac/base_CaC_vault.yml`, load it before dispatch, and
remove the temporary checkout/helper on success or failure. Keep the token out
of Git URLs, command arguments, saved credential helpers, and task output;
preserve TLS verification, reject URL credentials and redirects, and skip submodules.

Validation: an isolated local HTTPS Git fixture passed 11 cases, including loading
the existing unlabeled private base with both the default and `cac` Vault passwords,
failed Git authentication, invalid/missing/plaintext CaC, wrong Vault password,
untrusted TLS, and invalid repository URLs. Temporary checkouts were removed on
all tested failures, and token/plaintext fixture values were absent from output.
The four version-helper tests and whitespace checks passed. Full playbook syntax
validation is blocked locally by the missing `infra.aap_configuration.dispatch`
role; the loader itself ran successfully in isolation without that role.

No AAP jobs were launched. The existing `myvars` environment/authentication remains;
installer-password bootstrap, admin-password rotation, and demo selection are
separate pending work. This change does not verify a full live Stage 04 run or
publish a release.

## 0.0.7

Document planned work to make deployment jobs reusable and independently runnable.
Step 04 should accept the target AAP URL and credentials directly, allowing it to
configure an existing installation without our VM naming or domain scheme.
Provisioning-specific inputs should stay in stages that need them, using established
collection input names where available. Whitespace and staged-file checks passed.
This adds TODOs only; playbooks are unchanged and no AAP jobs were run.

## 0.0.6

Document why the project credits the Red Hat Communities of Practice collection
for its AAP configuration role, referencing the documentation update in `e97480d`.
Whitespace and staged-file checks passed.

## 0.0.5

Document that AAP post-install configuration uses the Red Hat Communities of
Practice collection `infra.aap_configuration`. Identify its `dispatch` role in
Step 04 and the Windows restore playbook, explain its purpose, and link upstream.
Verified both playbooks and the collection's official README; whitespace checks
passed. Deployment behavior is unchanged; no AAP jobs were run.

## 0.0.4

Document the private-configuration separation implemented in `6583b61`, including
the external plaintext working files, verified encrypted-copy workflow, preserved
history, and outstanding Step 04 loading integration. Whitespace and staged-file
checks passed. This documentation update does not publish a release or deploy AAP.

## 0.0.3

Move the populated encrypted shared CaC base to a separate private configuration
repository and retain generic examples here. Keep editable plaintext configuration
outside Git; encrypt a copy, verify its Vault header and decrypted equality, then
commit and push the encrypted copy to the private repository.

The private copy was verified and pushed before removing this repository's copy.
Step 04 is unchanged and still expects the former local file, so it cannot run
from this checkout alone. Private-configuration loading remains to be implemented.
No AAP deployment or configuration jobs were run.

## 0.0.2

Document the version-policy and reusable CaC template decisions implemented in
`f3efca9`. Explain independent project versions, generic templates versus populated
encrypted configuration, and the scope of validation. This is the required
decision-history follow-up to the `0.0.1` source baseline.

## 0.0.1

Establish the initial tracked source baseline and adopt a per-commit version
policy: minor increments for features, patch increments for all other commits,
including documentation and decision history. Add the version-bump helper,
project working rules, a current README, and retrospective decision history.

Include empty shared and per-demo CaC templates with generic commented examples.
A fresh checkout can use these as a starting point without obtaining a private
configuration export. Document encryption before committing populated sensitive
configuration and keep Vault password files outside Git.

Validation: all four command-line version tests passed; both templates parsed as
valid YAML with empty resource lists; existing secret files remain Vault-encrypted;
Vault password paths are ignored; and Git whitespace checks passed. The current AAP
deployment and configuration pipeline has not been verified end to end since
the repository split. Demo selection, authentication alignment, and dispatch
dependency readiness remain outstanding. This release adds source tooling and
templates; it does not deploy or configure an AAP instance.
