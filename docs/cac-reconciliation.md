# Reviewed Controller extraction and CaC updates

`capture-aap-cac.yml` reads an explicitly owned Controller scope and compares its
current configuration with encrypted CaC. It never applies configuration to AAP,
launches application jobs, accepts activity-stream entries as authoritative
state, or changes allocator-owned state. Preview is the default.

The initial reviewed adapter covers AutoDeploy. Its encrypted companion
`cac/capture_scopes_vault.yml` declares the source origin, organization,
project/label ownership families, bounded dependency/member ownership, stable
name aliases, writable CaC sections and code-owned workflow adapter. Other
captures remain intact and give explicit missing-adapter reasons. This is a
reusable scoped mechanism, not a claim that every AAP component is exportable.

## Visibility and normalization

The source credential must match the encrypted source origin. Every request is
GET-only, validates TLS, refuses redirects and constrains all pagination and
relationship URLs to that exact origin and Controller API prefix. A live
Controller-superuser read, consistent page counts, unique IDs, completed
pagination and readable managed relationships are required. An operator Boolean
does not establish visibility. Access failures and incomplete reads never imply
deletion. New templates are discovered through the declared project and label
families rather than an old ID list.

Objects and references use names/organizations/inventory parents. Runtime IDs,
timestamps, job statuses and source revisions do not enter semantic object
diffs. Association order is normalized; survey-field and node identities remain
meaningful. Removals include deleted resources, labels/credentials, survey
questions and workflow edges. Leaving the declared ownership scope removes an
object from that capture; no source-AAP deletion is performed.
Accepted dependency names are retained independently of template associations:
removing a credential/EE/inventory association does not declare the still-existing
definition deleted. Declared shared inventory members remain bounded; unrelated
shared hosts are excluded. YAML and JSON variable fields compare as mappings,
including literal unsafe Jinja values, so formatting does not create false drift.

Existing API-masked credential inputs and password survey defaults retain their
vaulted values, following survey variable identities across reordering. New
unrecoverable secret inputs block acceptance. **API-masked secret rotations
cannot be detected:** an operator must separately refresh the existing vaulted
input. Masked equality does not prove secret equality.

## First baseline and later reviews

Without `baselines/<scope>_vault.yml`, preview reports initial live-versus-desired
differences and requires explicit reviewed `initialize`. It does not guess which
side is newer. Initialization records separate accepted source and accepted
desired models, including deliberate namespace mappings and excluded resources.
It does not replace current desired CaC.

Later previews compare accepted source, accepted desired, current desired and
fresh source. Source-only changes are proposed; repo-only edits/deletions are
preserved. Disjoint edits merge. Same-field edits, source deletion versus repo
modification and changed source versus pending repo deletion conflict. Accepted
desired exclusions remain excluded. A fresh review digest binds all models,
scope and actual code revision/content; any intervening meaningful change
requires another preview.
Unordered relationship lists apply source membership deltas to desired state,
preserving accepted desired-only bootstrap credentials and excluded workflow
nodes. Arbitrary lists inside variables/credential inputs remain ordered and are
never treated as Controller associations merely because their keys have similar
names.

The protected review artifact includes source/current/proposed models, explicit
addition/change/removal paths, conflicts, visibility evidence and code ownership.
Its `encrypted_review` is whole-file Vault ciphertext in AAP artifacts. Retrieve
and decrypt only in a protected local workspace using the capture Vault secret.
Initial-difference counts must not be confused with changes since a baseline.

After a TLS trust failure, `cac_capture_failure_vault` retains encrypted source
resolution, matching host-file entries, trust-store paths and verified-SNI peer
probe results. Those probes send no HTTP request or API credentials and never
disable certificate/hostname checks. Compare the evidence with independently
trusted source identity before changing a credential trust bundle or route.

## Invocation and publication

Attach the source-reader credential (`AAP_CAC_SOURCE_URL/TOKEN`), scoped Git
credential (`AAP_CAC_CAPTURE_REPOSITORY/GIT_TOKEN`) and capture Vault credential.
The existing authorized allocation writer can supply its equivalent repository/
token variables; no new repository grant is implied.

```sh
ansible-playbook -i localhost, capture-aap-cac.yml \
  -e aap_cac_capture_scope=autodeploy
```

After inspecting the encrypted report, choose `initialize` or `update`, provide
`aap_cac_capture_review_digest`, and explicitly choose Boolean commit/push flags.
The AAP template defaults both to false. AAP update publication requires both
true; an unpublished local update instead requires an existing persistent
`aap_cac_capture_working_copy` with the exact credential-bound origin. That path
is deliberately not a free-form AAP survey input.

Updates write only the declared encrypted capture and separate encrypted baseline.
Vault roundtrips and label definitions are checked before normal non-force Git
publication. Unrelated staged work is refused. Contention fails safely and
requires a fresh review; it never overwrites a competing update or consumed VM
reservation. Unchanged accepted state produces no commit. Removing a definition
from captured CaC does not itself delete an existing AAP object; application and
teardown policy remain separate.

## Code and adapter limits

The report binds the actual code revision and a content fingerprint, and checks
own-project playbook paths against that checkout. The base workflow graph is
rendered from its current source template and compared separately. Source changes
that would require rewriting this code-owned graph block acceptance until its
code/ownership is resolved. Arbitrary Ansible AST reconciliation is not attempted.

The Controller adapter covers projects, templates, labels, credential/type inputs,
execution environments, declared inventories/hosts/groups and bounded workflow
graphs. Approval nodes, node overrides, notifications, schedules, dynamic
credential input sources and instance-group associations require explicit
adapter extensions; present unsupported associations block incomplete acceptance.
Gateway/EDA/PAH settings and application RBAC are outside this adapter. The
maintained `ansible.controller.export` module is available separately, but needs
`awxkit` and does not provide this capture schema's visibility/deletion/three-way
contract; this mechanism adds no dependency installation.

Local tests exercise semantic/removal/conflict fixtures, URL/visibility failures,
and real encrypted Git preview, initialization, update and removal. Runtime AAP
template installation and a successful real preview must be reported separately
from a YAML declaration or local fixture.
