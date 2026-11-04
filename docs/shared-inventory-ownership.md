# Shared inventory ownership and AAP display names

The shared inventory retains connection addresses, SSH or WinRM settings,
hypervisor placement, verified VM ownership, instance numbers, host keys and
recovery firewall policy. These describe where a host is and how automation
identifies it. Hactar's AAP-object CaC capture also remains with Hactar.

## Project runtime settings

| Fields | Owning project and actual consumer | Future shared-capture treatment |
| --- | --- | --- |
| `zabbix_server` | AIOps `playbooks/deploy_zabbix_agent.yml` | Remove the obsolete original-environment inventory default. Selected runtime settings remain in the existing private AIOps capture. |
| `claude_agent_user` | AIOps `playbooks/run_claude_analyse_fix.yml` | Remove the obsolete original-environment host value. Selected runtime settings remain in the existing private AIOps capture. |
| `windows_hostname`, `windows_connection_address`, `windows_network_interfaces` | Disconnected Windows Patching `configure_windows_server_basics.yml` | Remove the twelve exact duplicate values already present on the four owning-project host definitions. |
| `assistant_vm_name` | Assistant Team `inventory_vm_guard`, `linux_vm_shutdown`, `linux_vm_retire` and inventory registration | Retain: this is an explicit VM ownership binding used by lifecycle safety checks. |

The original AIOps values differ from the selected environment's settings; they
are not described as identical duplicates. Their encrypted history remains in
AutoDeploy secrets commit `fb476d1cce91d8b8b090fe7424f2543d724a67ab` and earlier
commits. No additional archive or configuration store is introduced. The
existing AIOps and Windows private repositories remain authoritative for their
own runtime configuration.

Cleanup of the future shared capture does not change existing production
inventory variables. Older AIOps jobs and Windows jobs still consume that live
shared inventory. Moving those live consumers to their project inventories is a
separate remaining step; deleting their required live variables first would
break them. Connection and verified ownership metadata are preserved throughout.

## Rename an inventory entry without renaming the VM

An AAP entry's display name may use the versioned inventory convention while
its existing libvirt name, disk, public FQDN, reservation and token-store key
remain unchanged. The selected entry's existing verified `vm_resource.vm_name`
is the physical identity; no additional alias table or token rekey is needed.

The common CaC importer keeps the inventory display name for `hostvars` lookup
and obtains token access using that recorded physical identity. It still checks
the token's HTTPS origin against the selected entry's `ansible_fqdn`. Registered
selection checks the inventory address, UUID, keys, counter and physical
ownership against the saved route before preserving a display alias.

The dedicated recovery-stage inventory contains only its hypervisor. Those
stages continue to take the immutable registered VM name; they do not guess a
physical name from a display alias. Lifecycle publication and retirement must
match any renamed AAP inventory entry through its existing `vm_resource`, so a
later base run cannot recreate the old display entry or overlook it during
cleanup. These coordinated code and capture changes precede a live rename.
