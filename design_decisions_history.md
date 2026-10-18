# Design decisions history

This retrospective uses this repository's Git history and the project handoff.
Where historical intent is not documented, it is identified as an inference.
Source-baseline versioning begins after the historical commits below.

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
