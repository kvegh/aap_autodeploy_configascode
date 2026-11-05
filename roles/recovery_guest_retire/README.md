# Exact generic guest retirement

Call this role from the existing guest retirement job in two phases. First use
`recovery_retire_phase: plan` with `recovery_retire_guest_name` and the reviewed
`recovery_retire_hypervisor`. It resolves the exact saved `vm_resource` in the
existing encrypted shared capture and source inventory, then verifies native
hypervisor, UUID, disk, MAC, network and bootstrap provenance. It exposes
`recovery_guest_retire_plan` for that job's physical deletion checks. Planning
does not alter the VM, network, firewall, Git or AAP inventory.

After the caller has gracefully stopped and removed only that verified domain
and clone disk, call the same role with `recovery_retire_phase: publish`. The
native helper requires the selected domain and both canonical disk paths to be
absent. It removes only matching static DHCP reservations and this guest's
HTTPS/full-release isolation entries. Unsupported guest-to-host grants stop
planning before physical deletion. Normal firewall rules and other guests remain
unchanged. Dynamic DHCP lease cache is reported separately and is not edited.

The existing publication action saves the exact reduction in all three encrypted
captures and source inventory. It uses the same source API, Git writer and CaC
Vault credentials as guest release; target API authentication and a connection to
the deleted guest are unnecessary. Keep the caller's own deployment inventory
row until this shared publication succeeds.

An interrupted publication can retry from the surviving canonical or source API
resource record. Once both are gone, a repeated run allows only verified physical
absence without changing policy or unknown DHCP records. Conflicting ownership,
remaining storage, changed policy and selected host-service grants require
review. Git uses ordinary compare-and-retry publication. A policy reduction is
rolled back only before durable Git publication and only while its exact desired
state is still current. Temporary code and SSH trust files are cleaned after
either phase. Check mode validates without deletion, publication or policy change.

For a verified Windows resource, additionally set
`recovery_retire_guest_kind: windows` in both phases. This explicit choice is
required even when a previous successful run has already removed its saved
resource. It never infers an operating system from a name or substitutes Linux
identity fields. The same publisher resolves the saved Windows computer/native
UUID and all permanent NICs; native checks require its marked Windows clone and
owning-instance title. After physical deletion it removes only that resource's
exact per-NIC DHCP and DNS records and policy entries. The Windows clone and both
incompatible Linux canonical disk paths must be absent before publication.
Omitting this option preserves the existing Linux request and disk checks.

The existing Windows reset job can first include this same role with
`tasks_from: plan` and the ordinary `plan` inputs above. This reads canonical and
source ownership only, without contacting the hypervisor. A genuinely absent
record remains `null` in both supported Ansible templating modes. The caller may
then select its existing unconfigured-clone checks only when records and matching
permissions are absent. This entry point does not authorize physical deletion.
Registered guests still require the complete normal role plan before removal and
the normal publication phase afterward. Missing provenance is an error.
