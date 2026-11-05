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

The `VM allocation git Pseudo CMDB writer` is a separate credential using the existing
`Cac_git_token_type`. Its dedicated write token is injected as `CAC_GIT_TOKEN`;
the repository URL comes directly from encrypted project `myvars`, using the
AutoDeploy secrets-repository naming rule. Launch variables cannot redirect it.
The encrypted shared base defines the reusable Git type before creating the
writer, independently of optional recovery use cases. In `cac/base_CaC_vault.yml`,
its `controller_credentials_base` entry stores the secret in `inputs.token`.
The read-only repository credentials retain their own separate tokens.
The obsolete allocation-writer type is no longer provisioned. Controller refuses
a type change when a credential has job history. Migrate such a writer to a
replacement credential of the existing Git type and update its active assignments.
The owner approved naming it `VM allocation git Pseudo CMDB writer` and deleting
the retired credential after the replacement is verified. Existing type objects
are retained; no job record is deleted. No new token permissions are granted by this
change. Attach that credential, the named `cac` Vault credential, the
environment Vault and the selected hypervisor Machine credential to Stage 01.
Read-only repository access is insufficient; the action never falls back to a
host-local allocator or a force push.

## Recovery target contract

Use an isolated inventory with exactly one `hypervisor` member and a protected
`aap_hypervisor_pin` containing its address, managed user/port, machine ID, public
IP, verified public SSH keys and complete isolation bridge/DNS-bridge lists.
The Machine credential name may be included for later selected setup. No
password or private key belongs in this handoff.

The optional `aap_hypervisor_isolation_host_clients` list describes previously
approved local guest-to-hypervisor TCP permissions. Each entry has exactly
`bridge`, `ipv4`, `mac`, `destinations` and `ports`; addresses, ports and identities
must be normalized, unique and bounded. This list is independent of public HTTPS
egress. The persistent Hactar checker also verifies that its local destinations
belong to the connected hypervisor. AutoDeploy compares the complete policy and
does not configure firewall permissions implicitly.

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

Before publishing the route, new Stage 01 runs wait for authenticated guest
readiness through the already pinned hypervisor jump. They use the generated
guest public keys, the existing environment Vault login and a read-only machine-ID
check; another account, direct private-network route or host-key exception is
not tried. Connection settings explicitly read the original inventory host's
route so delegation cannot accidentally lose its placement data. Conflicting
caller routes or effective connection overrides fail before guest authentication.

The initial route transaction saves `instance_resources.aap` with exactly
`uuid`, `disk`, `address`, `mac`, `network`, `bridge`, `verified` and
`hypervisor_machine_id`. Actual domain/network XML must identify the selected
VM, one expected file-backed disk, one interface and the enforced network
bridge. The allocator revalidates every field against the consumed route,
preserves unrelated AAP allocation history, accepts an unchanged retry and refuses replacement
of known primary ownership. Decommissioned reservations cannot publish a fresh
active route. Legacy callers without ownership metadata remain compatible;
new Stage 01 always supplies it. This retains proof after a failed partial
decommission has already removed the VM definition, without a new state store.

The Windows infrastructure job may later add one optional
`supplemental_interfaces` declaration to that same AAP ownership record and its
main-inventory `vm_resource`. This bounded transaction preserves the eight
primary fields and route, checks exact native and authenticated RHEL identity,
and grants no firewall permission. Unused metadata is omitted. Ordinary route
publication cannot replace or discard the declaration. See the
[existing role contract](../roles/recovery_guest_release/README.md#windows-owned-aap-interface)
for its plan, publication, concurrent rollback and exact removal requirements.

AutoDeploy allocation retains only `instance_resources.aap`. Application VM
configuration belongs to its use case; generic teardown reads related ownership
from the existing source Controller inventory's verified `vm_resource` records.
It does not copy that data into AutoDeploy secrets. Only decommission enables
the optional source read, using the existing source API credential; normal
stage selection remains a registry-only read. See [decommissioning](decommission.md)
for the fixed-inventory, pin, resource and missing-role checks.

Provisioning is enabled one phase at a time. A successful isolated Stage 01
proves neither AAP installation nor later API routing. Installation observers
must use the pinned hypervisor jump route for overlapping private subnets, and
configuration must use the matching public proxy/DNS/TLS path. Actual deployment
proof remains a separate gate.

An isolated Stage 01 and the separate authenticated read-only observer have now
completed successfully on the recovery host. Independent protected checks proved
the guest identity differs from both the golden image and hypervisor; the source
host's domains and local counter were preserved. This proves VM creation and
guest login/sudo through the pinned route. It does not prove certificate issuance,
permitted installer egress, AAP installation or base configuration.

## Selecting an existing reserved instance

Stages 02–04 accept `aap_instance_key`, the exact reserved VM name. A workflow may
instead supply its Stage 01 route; it must equal the registry's completed entry.
The read-only `aap_read_instance` controller action retrieves current `main` and
decrypts only the shared state file with the attached CaC Vault secret. Unknown
keys, incomplete reservations and conflicting caller URLs/private addresses fail
before target connections. There is no free-form URL or old-host fallback.

Attach `aap_autodeploy_configascode-secrets CaC repo read token`, which supplies
the existing `CAC_GIT_TOKEN`, plus
`aap_autodeploy_configascode-secrets CaC vault cred` (Vault ID `cac`) and the
environment Vault. The same AutoDeploy CaC credential encrypts and decrypts the
registry; no separate instance-registry Vault credential is required.
The registry URL is derived from the namespace in encrypted runtime `myvars`,
using the same AutoDeploy repository naming rule as the project importer.
Launch variables cannot redirect this token to another repository. Generic
use-case imports do not read the instance registry and retain their own tokens.
Guest stages also require the selected hypervisor's Machine
credential. Their private job-local known-hosts file trusts the registered
hypervisor and newly generated guest public keys. Both SSH hops require strict
host-key checking, and the guest connection always traverses that hypervisor;
overlapping private guest networks cannot select a production guest directly.

Stage 02 derives the DNS address from the verified hypervisor pin, reads the
exact reserved A record and refuses any conflicting address before its PUT.
It first checks that Hactar's shared baremetal base OS already provides certbot
and its nginx plugin. Package ownership stays in that base rather than the AAP
VM or this certificate consumer.
Certificate/proxy paths are limited to the reserved VM hostname. An existing
certificate or separately approved ACME account is required; this playbook does
not accept certificate terms. Stage 04 checks that public DNS points exclusively
to this hypervisor and validates the instance's public TLS endpoint before
sending AAP credentials. Installer-password/MCP observers use the same pinned
SSH jump route. Legal approval, permitted installer egress and live proof remain
operator-controlled prerequisites.

Local tests exercise real competing Git writers, active named-Vault decryption,
check mode, lost-number retention, a real read-only registry lookup, refusal of
unknown/stale targets, delegated SSH routing and conflicting DNS refusal. They do not establish
real VM boot, guest SSH, certificate issuance or AAP installation. Check mode
checks access without consuming a number or provisioning a VM.

## Public names for future deployments

A reservation such as `aap27-test-7` keeps that VM and inventory key. Its new
guest and public FQDN is `aap27.v07.example.invalid`; the matching demo website
is `redhat.v07.example.invalid`. Numbers have at least two digits. The shared
allocator consumes one number; services do not allocate independent counters.
Existing completed instance routes retain their current public names. Rerunning
stages against such an instance does not migrate its DNS or certificates.

Stage 04 now needs the existing Git writer instead of the repository reader,
alongside the existing source API and source CA credentials, to publish the new
instance token back to the source. Stages 02/03 retain repository read access.
See [instance token storage](instance-token-store.md) and [decommissioning](decommission.md).

With `aap_instance_key_store.register_inventory: true`, the same base publication
also updates the existing encrypted shared inventory and source AAP inventory.
It registers the selected instance's explicit FQDN, fresh guest host keys and
hypervisor placement, adds the existing placement-group membership and retains
other hosts, variables and members. The hypervisor's verified management identity
and declared isolation policy are preserved alongside placement. This callback
uses the existing writer, source API and Vault credentials; it creates no extra
job and places no API tokens in inventory variables.
