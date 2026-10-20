# Design decisions history

This retrospective uses this repository's Git history and the project handoff.
Where historical intent is not documented, it is identified as an inference.
Source-baseline versioning begins after the historical commits below.

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
