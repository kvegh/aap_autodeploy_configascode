# Decommission a test deployment

The existing teardown entry is maintained as **Decommission AAP Test Instance**
and runs `destroy-test-aap.yml`. Select the registered `aap_instance_key` and type
that same value as `aap_decommission_confirmation`. The job uses the one-host
recovery inventory and its Machine credential, environment Vault and private
AutoDeploy CaC reader/Vault. It is separate from the deployment workflow.
The existing source API credential and its configured CA trust are also required
for the decommission-only related-ownership read and final source cleanup.

Before deletion it verifies SSH keys, the actual hypervisor machine ID and
persistent isolation. It checks the selected domain's exact disk and refuses
snapshots or unexpected storage. DNS ownership is checked before any destructive
step. An unexpected destination stops the job for review.

The complete deployment scope includes AAP, matching versioned Zabbix,
testserver and TRA guests, and the demo website. Related guests require recorded
UUID/disk ownership in the existing source AAP inventory before deletion.
AutoDeploy's encrypted reservation retains only primary AAP ownership.
Its optional Windows-owned supplemental interface remains part of that same
AAP resource, not a separate application VM record. Current and persistent NIC
sets must match all declared identities. Saved metadata also identifies every
NIC after the VM is absent. Related generic Linux guests cannot use this optional
AAP field.
Known website content/cache/checkout, nginx vhosts/rate-limit/Basic-auth files,
certificate lineages and upstream CA files are removed only for that version.

The job paginates the entire DNS zone, selects exact `vNN` labels including
unknown orphaned role names, validates ownership, rechecks each record set
immediately before deletion and verifies provider absence. Conflicting addresses,
unexpected IPv6 or unreviewed record types stop before VM deletion. Other
versions and production records are preserved.

The same preflight plans exact matching libvirt DHCP/DNS host records from active
and persistent network XML. After verified shutdown it rereads the definitions,
deletes only those exact records and verifies that all unrelated XML remains.
Retries plan only still-present records. Missing or conflicting ownership stops
cleanup; no MAC or reservation is inferred from a name alone. The Windows AAP
NIC uses a static address outside DHCP pools and adds no DHCP/DNS host record.
For an older live one-NIC AAP that predates saved resource metadata, cleanup
reuses the native UUID/disk/network/MAC identity already validated by the guest
ownership preflight and its route address. It creates no synthetic verified
record. An absent VM without complete saved ownership cannot authorize cleanup
of ambiguous named reservations.

## Read related ownership from the existing source inventory

Only this playbook enables `aap_read_instance.read_related_resources`. Ordinary
stage selection remains registry-only and never constructs the source API client.
The optional reader verifies trusted source HTTPS and that its credential can
identify the current running job/template/revision. Its inventory name comes
from the fixed encrypted shared capture, selecting the independently pinned
hypervisor; callers cannot provide another inventory, endpoint or resource map.

Present related guests require a full verified `vm_resource` on their source
inventory row. Required fields are `vm_name`, `address`, `uuid`, `disk`, `mac`,
`network`, `bridge`, `machine_id`, `host_keys`, `hypervisor_machine_id` and
`verified: true`. The row's address, UUID, machine ID, keys, hypervisor placement
and integer `aap_instance_number` must agree with that artifact and the selected
counter. Exact same-counter role names and bounded disk paths are required.
Other artifact fields are retained in protected memory, never copied into the
AutoDeploy secrets repository. Application CaC stays with its own use case.

A role can legitimately be undeployed. A missing source row is accepted only
after the existing target preflight proves no corresponding VM and neither
bounded disk variant exists. Every permission left after the selected cleanup
must resolve to a surviving verified source VM or proper AAP resource on this
same hypervisor. Unknown or orphaned permissions fail closed. An extant row
without valid `vm_resource` fails even if its VM is absent. This also permits a
new cleanup job after some source host rows were already deleted, without
persisting application ownership in central allocation.

## Retire only the selected guests' permissions

Before stopping any VM, the job reads the existing root-owned protected
isolation JSON, verifies its live policy, and captures the selected domain and
libvirt network XML. Guest bridge/MAC values come from those checked definitions;
the AAP address comes from its registered route, and related addresses come from
their verified source inventory artifacts. Recorded UUID, disk, MAC, bridge,
network, address and hypervisor identity must agree when supplied. A legacy
primary VM without recorded UUID retains the existing exact-name/single-disk
guard. A missing VM with remaining grants needs its full recorded identity;
the job does not invent a MAC from DHCP or assume an address still belongs to it.
New Stage 01 publications automatically retain complete primary ownership in
that same encrypted reservation after pinned guest verification. They therefore
keep the required retry proof even after the primary VM definition is removed.

The pure plan removes only those exact bridge/IPv4/MAC identities from
`guest_host_clients` and `https_clients`. Other guests, bridge coverage and
forwarding restrictions remain. Removing the last HTTPS client also removes
its now-unused protected-address field; the default forwarding drop remains.
Only exact old-owned native source/destination/TCP rich rules absent from the
desired policy are selected. No broad rich-rule scan, service opening or
unrelated rule deletion occurs.

All selected existing VMs are stopped and checked before permissions change.
The job then queries, removes and verifies absence of those exact native rules
in runtime and permanent libvirt-zone configuration. It atomically saves the
reduced existing JSON and calls the installed isolation helper's `apply` and
`check` commands. No helper, service, dependency or separate state store is
installed. Only after successful permission cleanup may domain definitions,
disks and external resources be removed.

If applying or verifying the reduced local policy fails, the captured previous
JSON is restored and the same helper reapplies/checks it. The job then fails
before domain/disk removal, with guests stopped. Removed native grants stay
disabled; this tighter condition is safe and can be retried using exact queries.
If that restoration itself fails, the job fails and requires protected operator
inspection; it does not claim successful rollback.

The protected fact `aap_decommission_isolation_retirement` contains
`previous_policy`, `desired_policy` and `identities` for the existing source
publication action. The local plan also exposes `changed` and
`rich_rules_to_remove`. These facts are not public job artifacts. Canonical
encrypted/controller policy updates belong to that existing action integration;
the local task alone does not prove successful source synchronization. A retry
after later partial teardown accepts only the declared canonical policy or its
exact desired policy derived from the verified selected identities. Any third
state fails. The matched actual JSON must still pass the installed helper's
strict kernel check and active/enabled service proof. Rich-rule cleanup always
derives ownership from the canonical prior policy, so leftovers are removed
even when the local JSON was already reduced. The source handoff retains both
canonical policies, while local rollback restores the captured actual policy.
Ordinary deployment retains its unchanged complete policy verification; there
is no generic skip flag. Check mode performs reads and planning, ending before
shutdown and any permission or resource writes.

After infrastructure retirement, the existing Git writer marks the consumed
reservation decommissioned, removes the active token and inventory entry from
encrypted CaC, updates the source token-store credential and removes the matching
source inventory/manual API credential. A source credential still referenced by
a template is refused rather than silently detached. Check mode performs the
ownership review without destruction. Failed partial cleanup can be rerun with
the same exact confirmation; normal deployment stages refuse retired entries.

The shared counter and consumed reservation history are never rolled back.
The next fresh deployment consumes a new number.

The final action accepts the protected `isolation_retirement` mapping only for
its existing `retire` operation. Inside each compare-and-swap Git attempt it
reads the selected reservation first, checks both normalized policies against
that pin and proves the desired policy is exactly removal of the selected
recorded identities. It rejects omitted selected permissions, foreign identities,
new grants and conflicting current policy. Current encrypted policy may equal
only the captured previous or desired value for an idempotent retry.
It independently rereads source ownership, compares extant records with this
same running job's protected reader result and retains those verified facts only
in memory while its own API deletions progress. No caller resource argument or
encrypted application-metadata fallback is accepted.

The same encrypted commit updates the canonical recovery inventory, both
hypervisor policy aliases in the shared capture, and equivalent metadata in the
existing fixed Hactar recovery capture. Exact retired rich-rule entries are
removed from saved additional-rule data so a later firewall deployment cannot
add them back. Captured literal JSON variable wrappers remain literal. Only
matching AAP rows and memberships in the captured shared inventory are removed;
related application rows are retired from the source API using verified source
address/UUID/machine-identity checks. Application metadata is never added to the
encrypted central captures. Existing unrelated rows and memberships remain;
other inventories, versions, credentials and resource history are preserved.

All source API targets are read and validated before encrypted publication or
source writes. Synchronization updates only those policy fields and removes
the verified guest hosts in that exact shared inventory. All policy aliases are
patched and reread before any guest host deletion. A lagging API policy is
accepted only when its normalized state, minus exactly this job's verified
selected identities, equals the encrypted desired policy. Unrelated changes or
new permissions are refused. A failed source update
after successful encrypted publication can be rerun without a second Git change.
Concurrent changes are reread and checked rather than overwritten.
