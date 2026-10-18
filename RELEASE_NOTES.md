# Release notes

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
