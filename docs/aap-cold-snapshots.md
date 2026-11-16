# Cold AAP installation checkpoints

The next enabled AAP installation keeps three managed libvirt checkpoints:

| Successful stage | Native snapshot name |
| --- | --- |
| VM deployment and infrastructure configuration | `aap-infra-configured-before-install-snapshot` |
| AAP installer, before base configuration | `aap-up-before-base-snapshot` |
| Base configuration and final guest publication | `aap-base-deployed-snapshot` |

The longest name is 44 ASCII characters. Each stage first completes its normal
checks, then cleanly shuts down the exact registered VM, takes an internal
snapshot, starts it and verifies its original SSH identity. Installed and base
checkpoints also verify the public Controller API. Infrastructure has no AAP API
yet, so its readiness check is SSH and machine identity. Pending infrastructure
handlers finish before the first checkpoint.

The public default disables this feature. Encrypted AutoDeploy CaC owns the
enabled flag, first eligible allocation number, all three names, shutdown and
startup bounds and free-space reserve. The already running installation is
outside the enabled generation range. Updating code or desired CaC does not
retroactively shut it down or create a snapshot.

## Implementation and storage boundaries

The reusable playbooks are `snapshot-aap-vm.yml` and
`restore-aap-vm-snapshot.yml`. Existing infrastructure, installer and base stages
include the same creation tasks only after success; no new deployment workflow
or continuation service is introduced. A bounded native Ansible module uses the
already installed `virsh` and `qemu-img` commands; no libvirt Python dependency is
installed.

The supported shape is the registered BIOS KVM VM, one local standalone qcow2
system disk and its exact recorded NICs on the pinned isolated bridges. A
read-only seed CDROM may accompany that disk. Firmware/NVRAM-backed guests,
backing chains, external data files, encrypted storage, TPM state, extra writable
disks, host devices and shared host filesystems require separate qualification
and are refused. Existing snapshots are never overwritten or silently deleted.
An existing checkpoint for that same native guest is preserved without another
power cycle, including after later project changes. It is never relabelled as a
new capture. Matching external state is required for restore, not for preserving
an existing immutable checkpoint during a repeat base run.

Libvirt can serialize controller declarations in a different order in the
snapshot's saved domain XML. The configuration comparison sorts only complete
`domain/devices/controller` elements within their existing controller slots.
Every attribute, address, child element, duplicate and count remains significant;
all other device declaration order remains significant. Metadata with nested
elements of the same names is not normalized. This accepts equivalent saved
controllers without accepting changed hardware or modifying a checkpoint.

Inactive disk snapshots are clean when the preceding guest shutdown was clean.
Internal snapshots preserve the existing disk path, avoiding an external overlay
chain and a changed registered primary path. See the official
[libvirt snapshot format](https://libvirt.org/formatsnapshot.html) and
[native snapshot commands](https://libvirt.org/manpages/virsh.html#snapshot-commands).

Before shutdown the module verifies the managed host identity and independent
production exclusion, active isolation service, actual network/bridge identity,
unique selected disk and MAC ownership, regular non-symlink disk storage,
available capacity and atomic snapshot support. Normal image inspection runs
only after a clean shutdown; no forced shared image read is used. A native
per-VM lock rejects competing snapshot operations.

The shared transaction explicitly selects root for its existing privileged
guest and hypervisor operations, including when called from the installer's
unprivileged installation play. Delegation retains its original SSH identity,
pinning and native ownership checks. Controller-side API reads and temporary
trust cleanup keep privilege escalation disabled. A temporary-file permission
failure caused by an inherited installer account must be fixed at this caller
context; it does not justify installing ACL tools or weakening file permissions.

The configured reserve is 64 GiB, and the check also requires at least one
virtual disk's capacity to remain free. This is a lower bound at each operation,
not a guarantee against later growth. Three retained snapshots plus test
workloads can consume substantially more space. Monitor the normal VM storage
pool; this feature does not resize storage or prune checkpoints automatically.
These local snapshots do not survive a physical-host reinstall and do not
replace off-host backups.

## Explicit restore and external state

The ordinary CaC restore template requires the registered instance, one exact
snapshot name and confirmation that later guest disk changes may be discarded.
It never allocates, rewinds or modifies a generation counter. The receiving
Controller must become idle within a bounded wait. Every paginated EDA
activation must explicitly be disabled with no current job; this operation
never cancels work or disables listeners. API, authentication and incomplete
pagination failures stop before a VM power operation.

Native snapshot descriptions store checkpoint proofs and digests, not plaintext
credentials. Restore checks the real stored native domain XML, UUID, internal
disk and memory metadata, plus current checkpoint-relevant state:

- Selected registered route and resources, canonical inventory identities and
  scoped permission grants, including inherited group/inventory declarations.
- The selected AAP access record, validated through the existing native token,
  origin and expiry checks.
- The selected Windows private profile and its opaque per-instance runtime
  ciphertext, read through its existing bootstrap reader and Vault key.
- The selected AIOps private profile and decrypted runtime namespace, including
  importer-generated template IDs, webhook keys and Event Stream endpoints.

Unrelated installations, global next-generation counters, Git revisions and
volatile observation timestamps are excluded. AIOps runtime re-encryption alone
does not change its selected semantic digest. Windows runtime remains opaque to
this reader: re-encrypting that selected ciphertext can conservatively block a
restore even if its plaintext is unchanged. Standalone and embedded runtime
ciphertext must agree.

**A VM snapshot is not yet a complete automatic project-test reset.** Normal
AIOps CaC import itself can publish generated keys and IDs into its private
repository. Windows preparation also writes its selected private profile.
Restore refuses those changes until the appropriate owner-specific
reconciliation has restored checkpoint-relevant state. Project runs can also
create guests, DNS entries and host rules. Existing guarded guest retirement,
selected profile retirement and native policy/DNS verification remain separate
operations; this playbook never launches them automatically or rewinds a whole
repository. Canonical fingerprints do not independently prove every actual DNS
record or native firewall rule. Run tests in a quiescent, explicitly selected
scope and retain the normal owner-specific native guards.

The post-base snapshot is therefore a reusable native AAP baseline, with guarded
restore available when external state matches. Automatic reconciliation after
arbitrary project imports and runs remains a separate acceptance requirement.

## Failure handling and verification

Shutdown is graceful and bounded; there is no forced destroy or power-off.
Creation uses native atomic snapshotting. If creation fails after shutdown, the
unchanged original VM is restarted where that is demonstrably safe, and the
original failure remains reported. A restart failure is reported alongside it.
An uncertain failed restore deliberately leaves the VM off for native-state
review rather than starting a potentially partial rollback. SSH, machine-ID and
installed API verification must pass before the stage reports completion.

If installation itself succeeded but its checkpoint hook failed, preserve that
component result and the failed parent job. Inspect the actual VM, existing
snapshots and installed API before using the normal CaC template for
`snapshot-aap-vm.yml` to capture only the missing declared checkpoint. Do not
rerun a completed installer merely to reach its checkpoint hook, and do not
substitute a restore. Base configuration still waits for verified completion
of the installed checkpoint.

Offline regression tests exercise native identity and metadata rejection,
idempotence, bounded power transitions, failure/restart handling, scoped state
and secret preservation, private import-generated values, actual Ansible
delegation/ordering and paginated API guards. Native Core 2.20 qualification and
a read-only check of the current supported host/VM shape do not establish a
successful real snapshot or rollback. Each enabled installation must verify all
three checkpoints. Restore acceptance remains separate and requires explicit
authorization; workload redeployment tests preserve the running AAP VM.
