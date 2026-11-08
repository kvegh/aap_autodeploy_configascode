# Verified recovery guest release

This role runs inside the existing generic Linux deployment job after authenticated
guest facts, hostname, resources and setup have passed. It reuses the existing
source API credential, allocation Git writer and AutoDeploy CaC Vault credential.
The existing publication action preflights the running source job, encrypted
captures and source inventory before any live change.

The helper checks actual hypervisor identity, guest UUID, disk, bridge, MAC, DHCP
lease and public bootstrap provenance, then atomically updates only the existing
recovery isolation table. The released guest returns to normal IPv4 firewall
handling while declared production destinations remain blocked. IPv6 quarantine,
normal firewalld rules and every other guest remain unchanged.

Publication uses the existing encrypted captures and source inventory. A failure
before durable publication rolls back exactly the change applied by this job;
after durable publication, a retry completes source-inventory reconciliation.
Check mode performs source and live read-only validation without applying policy
or publishing configuration. Temporary code is removed on success and failure.

Inputs are `recovery_release_guest`, `recovery_release_hypervisor` and the existing
controller-side `recovery_release_trust_file`. This role adds no job template,
service, credential type or secret store.

## Native lock contention

Separate AAP jobs can reach the same hypervisor policy transaction concurrently.
Ansible task throttling applies within one job and cannot protect this shared
native critical section. The existing Python helper therefore keeps the native
exclusive directory lock and uses the management helper's bounded five-second
wait, polling only lock acquisition every tenth of a second. It performs no
native probe or policy change before acquiring the lock. Identity, current
policy, production exclusion and rollback checks then run unchanged.

Lock exhaustion returns code 75 and one fixed public busy message. The role
shows that controlled reason without exposing command input or raw exceptions;
other failures are not retried and retain sanitized diagnostics. This corrects
a locally reproduced contention defect. The original historical release failure
had censored diagnostics, so contention is not established as its cause.

## Exact guest bootstrap

`recovery_release_operation` defaults to `release_guest`. The existing
`guest_bootstrap_https` value permits only the selected verified generic Linux
guest's public IPv4 TCP 443 traffic. It does not give that guest full release.

The explicit `guest_bootstrap_http` value permits only public IPv4 TCP 80 for
the same exact guest identity. HTTP additionally requires its complete verified
`vm_resource` to have already been published in the canonical shared inventory,
with the same hypervisor placement, address, UUID, disk, network, MAC, machine
identity and SSH keys. The caller still supplies the same existing guest,
hypervisor and pinned trust inputs. No caller-selected port list is accepted.

HTTP uses its own optional `http_clients` list. It never turns existing HTTPS
clients into HTTP clients. The matching recovery variable is
`aap_hypervisor_isolation_http_clients`; the structured `isolation_policy` and
`hactar_isolation_policy` aliases retain the same field. Missing or empty input
is omitted from the normalized policy. A persisted HTTP list is bounded,
nonempty and requires the declared protected IPv4 destinations.

Both bootstrap operations retain private/reserved/production restrictions,
existing HTTPS access, host-service grants and other released guests. They use
the same native guest checks, source-job verification, encrypted compare-and-swap
publication and rollback as full release. Other policy operations preserve HTTP
entries. Selected guest retirement removes only that guest's exact HTTP entry
and retains production protection while any HTTP, HTTPS or released guest remains.
Full release still requires the caller's completed configuration checks.

The HTTP extension is implemented and tested. This does not establish successful
live bootstrap or downloads; the caller still requires operator approval.

## Verified Windows deployments

The same role accepts an explicit Windows resource only after the caller has
completed the VM's configuration checks over authenticated WinRM. The operator
has retained the demo's existing HTTPS/NTLM certificate-validation exception;
the resource must truthfully record whether certificate validation occurred.
This is a per-VM deployment milestone; later patch/content functional
tests are separate. VM creation alone is insufficient. Windows bootstrap HTTP
and HTTPS are not supported by this branch.

The resource has exactly these fields: `kind: windows`, `vm_name`, `instance_name`,
`uuid`, `disk`, `hypervisor_machine_id`, `verified: true`, `computer_name`,
`computer_uuid`, `address`, `interfaces` and Boolean `winrm_certificate_validated`.
The value is `false` for the approved demo exception and `true` only for an
actually certificate-validated connection. Strings and numeric substitutes are
refused. This field does not replace `verified: true` or any native identity check.
The observed computer name must match the versioned VM name; the normalized CIM
product UUID must equal the native libvirt UUID. No Linux machine ID, SSH host
key or generic-image description is substituted. `instance_name` is the existing
owning AAP instance identity, retained in the native domain title.

`interfaces` contains every one or two permanent NICs, each with exactly
`network`, `bridge`, `mac`, `address` and `dns_name`. The caller must validate
observed Windows MAC/IP pairs, not merely copy expected settings. The selected
WinRM `address` must belong to one of these verified NICs. Native checks bind all
NICs to both domain XML definitions, actual network bridges/subnets and exact
static DHCP/DNS records; conflicting leases refuse release. The exact disk is
`/opt/vms/win-<vm-name>-clone.disk.qcow2`, with the existing Windows clone marker
and `<instance>:<vm-name>` title. It must be exclusively owned and non-symlinked.

All verified NIC identities are added atomically to the same policy transition
and existing encrypted captures/source inventory. Production denial and every
unrelated permission remain. Omitted `kind` keeps the existing Linux schema and
checks; the Windows fields are refused by that default schema.

## Completed AAP base configuration

The same role accepts exactly `kind: aap`, `route`, `primary` and
`guest_machine_id` as its guest object. The route and exact primary come from the
existing consumed VM reservation; the machine ID must be freshly read through
the existing authenticated, pinned SSH connection and must agree with any
recorded guest ID. It is not a password/token recovery mechanism and introduces
no generic-image description or synthetic guest fields.

Normal Stage 04 calls this branch only after base configuration, MCP/API access,
source publication and their cleanup succeed. Existing publication and inventory
registration must be enabled. A new short-lived trust file is removed even when
release fails. Partial runs, skipped tasks, check mode and the HTTPS-only repair
path do not reach full release.

The source action compares the read-only reservation before and after durable
publication. It requires the already-published AAP inventory host and leaves its
physical/alias identity and token data unchanged. Native checks reuse the AAP
management/installation ownership guard, including both domain definitions,
UUID, exclusive ownership among guests, canonical disk, MAC, network and DHCP.
Only the primary's exact policy identity is added; existing native firewall rules,
production exclusions and other guest permissions remain. Linux and Windows
branches retain their existing behavior.
The primary-only selection also applies during source alias comparison when the
recorded AAP has a Windows-owned second interface; that interface stays isolated.

## Windows-owned AAP interface

The existing `recovery_release_operation: aap_supplemental_interface` verifies
and saves one Windows-owned supplemental interface on an existing AAP. It
changes ownership metadata only, with no firewall grant, early release or token
change. The Windows infrastructure job configures the NIC and RHEL connection;
this role independently checks the resulting native hardware and its protected
authenticated connection readback before publication.

Use the same role with `tasks_from: plan` before any mutation. Supply the usual
`recovery_release_guest`, `recovery_release_hypervisor` and
`recovery_release_trust_file`, plus that operation value. The plan is read-only
and returns `__recovery_release_plan`; it does not claim that intended hardware
already exists. Retain the same pinned checkout throughout plan, setup, publish
and any rollback check. Call the role's normal entry point after configuration
and fresh authenticated RHEL readback.

The typed guest has exactly `kind: aap`, `route`, `primary`, `guest_machine_id`,
`supplemental_interface`, `supplemental_state` (`present` or `absent`) and
`connection_readback`. Route and primary come from the existing reservation.
The primary remains immutable. The optional `supplemental_interfaces` list in
that same primary resource contains at most one exact declaration; omission
means unused. Main-inventory `vm_resource` mirrors the same declaration.

Each declaration has exactly `owner_project_id: disconnected-windows-patching`,
`network`, `bridge`, `address`, `mac`, `connection_uuid`, `connection_name`,
`attachment_created: true` and `connection_created: true`. Existing unowned
matching hardware or connections must be refused rather than adopted. Source
and native checks bind the exact primary UUID/disk and all declared MAC/network
pairs to both current and persistent XML. The supplemental interface remains
bound to the exact `ua-windows-<connection_uuid>` interface alias and virtio
model; primary and legacy interfaces retain their original model behavior.
The supplemental network remains
isolated; the static private address must be outside DHCP pools and absent from
existing reservations. The primary DHCP lease remains required; a static
secondary interface requires no fabricated DHCP lease.

`connection_readback` contains the actual authenticated `machine_id` and a
bounded `connections` list. Every row has `uuid`, `name`, `mac`, `addresses`
(IPv4 CIDR strings), `gateway`, `dns` (list), `never_default`, `autoconnect`,
`ipv4_method`, `ipv4_ignore_auto_dns`, `ipv6_method`, `ipv6_never_default` and
`ipv6_ignore_auto_dns`. The exact owned row must have its one static address,
empty gateway/DNS, `manual` IPv4, `disabled` IPv6, and all five applicable
Boolean settings true. The producer also verifies that the interface has no
IPv4/IPv6 default route or IPv6 address, preserving the original routes and
resolver. For removal, no profile may retain its UUID, name, MAC or address,
and the exact NIC must be absent from both XML definitions.

The same publisher verifies the running source job and uses encrypted Git
compare-and-swap to update the existing allocation and main inventory, then
reconciles that same source AAP row without renaming it. Other captures, routes,
primary identity, credentials, tokens and permissions remain unchanged.
`__recovery_release_plan.canonical_resource_present` and
`canonical_resource_absent` describe the freshly read canonical record;
`durable_ownership_published` describes the exact intended saved state.

If publication fails, the Windows producer may undo only components it created
and only after a fresh authenticated plan proves canonical ownership absent.
Preserve components when this or any concurrent job published their exact
declaration. If absence cannot be proved, preserve them and report cleanup
pending. Reset per-invocation results prevents reusing a previous role call's
durability flag. Ordinary role cleanup still removes its temporary runtime code.
The publisher resolves settings from each invocation's native action path even
when Ansible cached its module from a deleted earlier checkout.

Windows-only teardown removes this declaration after the exact owned extra NIC
and connection are gone. Complete AAP teardown consumes every saved interface,
including cleanup after VM absence, and removes only exact owned DHCP/DNS host
records while preserving unrelated network XML. Related generic Linux guests
cannot borrow this supplemental AAP schema. These are local implementation
checks; live Windows deployment and teardown remain separate acceptance.
