# Design decisions history

This retrospective uses this repository's Git history and the project handoff.
Where historical intent is not documented, it is identified as an inference.
Source-baseline versioning begins after the historical commits below.

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
