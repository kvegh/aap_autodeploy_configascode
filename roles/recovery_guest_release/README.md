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
