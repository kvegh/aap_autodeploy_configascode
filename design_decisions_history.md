# Design decisions history

This retrospective uses this repository's Git history and the project handoff.
Where historical intent is not documented, it is identified as an inference.
Source-baseline versioning begins after the historical commits below.

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
