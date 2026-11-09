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

Before stopping any VM, the job validates the selected domain and libvirt
network definitions against its registered UUID, disk, MAC, bridge, network,
address and hypervisor. The complete effective firewall policy comes from base
CaC plus application grants read from AIOps' own encrypted CaC. No deployed JSON
is loaded as desired policy. Missing source access or decryption stops cleanup.

The base plan removes only verified selected identities. Base publication remains
base-only. For AIOps, retain the selected instance's Zabbix ownership record and
`firewall.guest_host_clients` until native cleanup has completed. Those tuples
identify the exact ordinary rich rules to remove; no host-wide rule scan or
ownership inference is used. The record must match the selected version/domain,
disk and preflight UUID, and changed tuples after shutdown stop the operation.

All selected existing VMs are stopped and checked before permissions change.
The certified firewall role disables only those exact base/application rich
rules in both runtime and permanent libvirt-zone configuration. Native Hactar
Ansible tasks then apply and verify the complete reduced nft file/table. The
explicit decommission operation excludes only this instance's application tuples;
other declared instances remain. Domain definitions, disks and external resources
are removed only after this permission cleanup succeeds.

Native checks, changes and rollback share the approved temporary transaction
lock. On failure, the existing rescue restores exactly the recorded rich-rule
states and base-previous plus current application CaC. Guests remain stopped and
not deleted. Failure of restoration also stops the job for protected operator
inspection; it does not count as successful rollback. No host policy snapshot,
JSON owner file or firewall writer is installed.

The protected `aap_decommission_isolation_retirement` handoff still contains only
base `previous_policy`, `desired_policy` and selected `identities`. The existing
canonical/source action receives that unchanged base-only handoff. Application
grants are never copied into AutoDeploy's secrets. Check mode ends after ownership
planning, before shutdown or policy/resource changes. The separate provisioning
pin check remains read-only and requires explicit CaC reconciliation on drift.

After successful native cleanup, remove the selected application ownership and
permission entries through the existing AIOps private-CaC update procedure before
another policy apply. The existing AutoDeploy retire publisher updates its base
and shared records; it does not publish deletions into the AIOps private repo.
This final application-record step remains explicit operator work in the demo.

Do not delete the application permission/owner record before native decommission.
Plain CaC omission revokes the effective nft access on reconciliation, but cannot
safely identify an already orphaned ordinary rich rule. If the source record was
removed too early, stop for manual reconciliation; never purge unrelated rules
or claim that omission alone physically removed that rule.

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
