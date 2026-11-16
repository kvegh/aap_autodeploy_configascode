# AIOps workload teardown on the same AAP instance

`teardown-aiops-workload.yml` is a Source-owned lifecycle that preserves the
receiving AAP VM and hypervisor. It defaults to `preview`. The maintained CaC
append helper creates **Teardown AIOps Workload**, using the existing guarded
retirement template's six credentials, inventory, Source project and saved
hypervisor limit. No new credential type or connection path is introduced.

Select the exact active reservation VM name, choose `preview` or `apply`, and
repeat that name in `aap_aiops_teardown_confirmation`. Inventory aliases and
arbitrary host, credential or source overrides are refused. Check mode remains
read-only. A preview validates ownership and reports the selected scope; it
never disables event delivery or changes VM power, DNS or owner records.

## Owned resources and preserved platform

Cleanup covers the selected monitoring appliance, test server and TRA clones;
their recorded disks, exact DHCP/DNS reservations and guest isolation grants;
website checkout/cache/armed marker, managed nginx vhosts, rate-limit and Basic
Auth files, single-name certificate lineages and the two workload public A
records; and the normally imported Controller, Gateway and EDA definitions.
It stops selected event delivery and waits for existing selected jobs to finish.
It does not cancel jobs. The target-local normal subscription retirement job
must finish, and its exact native job/artifact identity must be verified, before
its own definitions or TRA disk can be removed. The monitoring appliance is
stopped by its selected hypervisor UUID, without an appliance guest connection.

The receiving AAP VM, AAP publication and snapshots, active allocation and
monotonic counter, hypervisor, networks, golden images, platform container
images, base credentials, unrelated hosts/tools, other owners and job/history
records remain. Native shared disk, image backing-chain or snapshot references,
foreign workflow/template consumers, extra inventory hosts and unproved OAuth
application tokens stop cleanup before their dependencies are removed.

The persistent EDA Controller token is a separate native Gateway resource with
`application=None`. Its first-creation token-ID/user/target/credential binding
receipt is saved in the existing EDA credential description. Cleanup retains
that exact receipt in the selected existing owner namespace before deleting
its credential, revokes only the rechecked ID and verifies native absence.
Base API access and every other token remain. A legacy credential or possible
orphan token without this proof is preserved for original native evidence;
a human-readable description grants no deletion ownership.

## Proof and ordering

Native checks first validate the full existing owner graph, then narrow it to
only three workload guests. The original selected owner is deep-copied into the
plan and bound to the running Source job/revision. Every fresh private-repository
CAS compares against this frozen preimage; a later native application-capture
reload cannot replace it. Only validated teardown additions are allowed, and
normal pre-import and post-import publication refuse retained teardown owners. Exact UUID, disk, address, NIC and native provenance
checks precede power actions. A bounded read-only native disk scan covers current
and persistent domain XML, snapshot XML, unattached image files in the existing
clone directory and complete backing chains. It repeats before unlink while
holding the existing native policy transaction lock. It refuses unsupported or
unreadable storage rather than inferring exclusive ownership.

Application DNS uses the active selected encrypted runtime credentials. It
reads complete exact-name A/AAAA/CNAME provider pages, refuses aliases, alternate
families, duplicate or changed ownership, and deletes only the freshly rechecked
individual v3 provider ID. It then proves all three types absent at the provider
and requires every independently validated authoritative endpoint to return a
strict nonrecursive authoritative negative answer in the same bounded round.
This does not claim recursive caches have expired. Missing authoritative
convergence leaves owner namespaces intact for a retry.

Publication checks inspect the managed nginx configuration, exact file paths
and single-name certificate SANs. They repeat immediately before unlink under
the native transaction lock. Preserved domain definitions, power states and AAP
snapshot names are compared after removal. Selected Source guest rows and policy
aliases are published only after required native absence checks. Paired selected
AIOps owner/runtime namespaces are removed last through the existing approved
scoped private-repository writer, preserving all other values, Vault identity,
literal fields and history. Normal AIOps preparation refuses a retained teardown owner until cleanup finishes.
Concurrent native publisher changes are reread;
there is no force push or alternate credential fallback.

RHSM unregistration requires a receipt created at the actual native registration,
with exact guest UUID, authenticated machine ID, consumer name and consumer UUID.
Copied or otherwise unproved consumers are neither adopted nor unregistered.
A normal repository-enable failure must retain registration ownership for retry.
An ambiguous interruption after external unregistration but before its success
receipt is retained fails closed and requires the original native job evidence.
A receiving AAP without the reviewed normal subscription helper cannot complete
this lifecycle. This feature does not fabricate legacy receipts.

The owner's temporary deployment logging direction applies to all owned tasks,
includes and blocks: `no_log: false` remains until clean acceptance. Vendor
role masking stays intact. Keep raw native results in private AAP/protected
local evidence and redact reports. This does not change credential, ownership
or native connection guards.

## CaC adoption

Use `src/aap_aiops_teardown_cac.py` against a **fresh** encrypted Source capture:

```bash
python3 src/aap_aiops_teardown_cac.py \
  --scope source \
  --capture /protected/latest-source-capture.vault.yml \
  --vault-password-file /protected/existing-vault-selector \
  --output /protected/reviewed-candidate.vault.yml
```

The helper performs no controller or Git operation. It appends exactly one job
template and verifies the typed inverse, literal paths and original Vault header.
It refuses conflicting saved definitions or weakened existing launch guards.
Integrate that same transform against current private HEAD after an active
native publisher finishes; an old encrypted candidate must never replace a
newer route, reservation, key or owner capture. Normal CaC import and project
sync are separate publication gates. The matching AIOps capture adds the
receiving AAP's **Retire AIOps TRA Subscription** template with its existing TRA
Machine/Vault credentials, fixed `tra` limit and sole exact-instance survey.
Use the same helper with `--scope target` against a fresh encrypted AIOps capture.
An unchanged candidate retains exact ciphertext; another profile, runtime,
credential or template is never rewritten by the typed append.

## Qualification and remaining acceptance

The final focused suite passes 101 tests in cached Core2.20 and local Core2.21.
These tests cover owner projection, AAP/shared preservation, native
API preimages, deletion ordering, job quiescence, foreign references and races,
strict authoritative negative proof, selected DNS credentials, concurrent-safe
CaC append and native disk/backing/snapshot refusal. Native selected capture
rendering and subscription receipt retry tests are separate checks. An existing
broader isolation suite has reproducible baseline failures; those are not
reported as a passing suite.

No offline result establishes live deletion, external subscription cleanup or a
successful redeploy. Live acceptance must use an exactly selected current owned
runtime after all matching code, registration provenance and normal templates
are adopted. Verify teardown absence and shared preservation, then run the
normal AIOps import/deployment and the original website and monitoring recovery
functionality tests on the same AAP VM. AAP rollback and whole-instance destroy
are outside this workload reset.
