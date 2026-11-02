# Shared test-VM names and recovery provisioning

Stage 01 reserves each name in the AutoDeploy secrets repository's encrypted
`state/aap_vm_allocations_vault.yml` before copying or changing a VM image.
`aap_vm_allocation.next_number` and its reservation history are shared across
hypervisors. Old `/opt/vms/vmcounter` files are read only as migration evidence
and remain untouched. The initial shared floor exceeds all observed existing
test names and respects the highest observed old next-counter value.

The controller-side action uses the active attached `cac` Vault secret and an
authorized Git writer. Each attempt reads current `main`, encrypts one updated
state file, commits it and performs a normal non-force push. A competing update
causes a fresh read/retry. The accepted reservation is reread before a name is
returned. Failed provisioning never releases or reuses its number. A lost job
can therefore leave a consumed name without a VM; that gap is intentional.

The `AAP AutoDeploy allocation writer` credential injects
`AAP_ALLOCATION_GIT_TOKEN` and `AAP_ALLOCATION_REPOSITORY`. Its encrypted type/
credential definitions belong to shared base, independently of optional recovery
use cases. Attach that credential, the named `cac` Vault credential, the
environment Vault and the selected hypervisor Machine credential to Stage 01.
Read-only repository access is insufficient; the action never falls back to a
host-local allocator or a force push.

## Recovery target contract

Use an isolated inventory with exactly one `hypervisor` member and a protected
`aap_hypervisor_pin` containing its address, managed user/port, machine ID, public
IP, verified public SSH keys and complete isolation bridge/DNS-bridge lists.
The Machine credential name may be included for later selected setup. No
password or private key belongs in this handoff.

Before reservation, Stage 01 enforces SSH host-key checking, reads the actual
machine ID, verifies the existing persistent recovery isolation helper/service,
checks the selected network bridge and requires the already-published golden
image through explicit `aap_golden_image_path`; the source host's legacy image
default is not used. Existing disks/domains are never overwritten. Fresh guest host keys are
generated in a private temporary workspace and installed only into the new image;
cloud-init keeps those keys and the new machine ID is generated on first boot.
Only the copied disk's local RHSM identity is cleaned, with the customization
appliance network disabled. No server-side unregister is performed against a
copied consumer, and the shared golden image/source registration is untouched.
Only that temporary private workspace is removed afterward.

The exact new domain's DHCP address is read from libvirt. Public trust evidence
is retained before startup; the complete `aap_instance_route` is subsequently
stored in the encrypted registry and passed as an AAP artifact. It binds VM name,
private IP, fresh public host keys, the verified hypervisor and the VM's unique
public HTTPS hostname. Passwords, private keys and tokens are excluded.

Provisioning is enabled one phase at a time. A successful isolated Stage 01
proves neither AAP installation nor later API routing. Installation observers
must use the pinned hypervisor jump route for overlapping private subnets, and
configuration must use the matching public proxy/DNS/TLS path. Those later phase
checks and actual deployment proof remain separate gates.

Local tests exercise real competing Git writers, active named-Vault decryption,
check mode, lost-number retention and routing validation. They do not establish
real VM boot, guest SSH, certificate issuance or AAP installation. Check mode
checks access without consuming a number or provisioning a VM.
