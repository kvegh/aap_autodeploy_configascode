# AAP guest access to its own hypervisor

The normal base configuration stage also prepares the connection that an AAP
instance needs when its installed use cases manage that instance's hypervisor.
This is part of Step 04's existing saved-token and inventory publication block;
it does not require a separate job. It runs only when the existing
`aap_instance_key_store.register_inventory` setting is enabled for a registered
replacement deployment.

The destination is the address and management TCP port in the verified
hypervisor pin. The source is the primary AAP resource already recorded by
Step 01. Its bridge, IPv4 and MAC must match an existing approved HTTPS client.
Only that identity gains TCP access to that one host address and port. No
forwarding, general private-network access or production access is added.

## Verification and application

The task uses the existing Machine credential and strict SSH host keys to reach
the registered hypervisor directly. A short Python transaction is streamed from
the project; it is not installed as a new host program or service. It verifies:

- the hypervisor machine ID, assigned destination address and existing protected
  configuration, active/enabled isolation service and libvirt bridge zone;
- the selected primary UUID, exact single disk and interface, MAC, network,
  bridge and DHCP IPv4 lease against recorded ownership;
- the saved and current device definitions of every actual guest, refusing
  passthrough devices, remote storage and interfaces outside enforced bridges;
- that guest autostart remains disabled and current policy is the declared
  policy or precisely the independently derived management permission.

The existing isolation helper checks the current kernel policy and validates
the candidate. A native nftables check precedes changes. The transaction adds
and verifies only the exact libvirt-zone priority-zero rich rule in runtime
and permanent firewalld configuration, atomically updates the existing policy
file, then uses the existing helper's atomic apply/check operations. An advisory
lock on the existing protected directory serializes these base transactions;
no lock file or additional state store is created. Local application failure
restores the prior policy and removes only native entries added by that attempt.

Finally a task inside the selected AAP guest checks TCP reachability to the
registered host management port. The observer uses the existing verified SSH
jump through that hypervisor, so overlapping private guest networks cannot
redirect the check. All connection fields explicitly reference the original
play host's route. Configuration and token tasks remain protected by `no_log`.

## Saved configuration and retry

The existing token publication rereads the consumed AAP-only allocation inside
its Git compare-and-swap loop. It independently derives the exact permission
from primary ownership and the canonical recovery policy. Caller-supplied
additional ports, destinations, foreign ownership or unrelated client changes
are refused.

The same encrypted commit updates the recovery inventory's policy variables,
both policy aliases on the shared hypervisor, and equivalent metadata in the
existing Hactar recovery capture. The shared AAP row receives its recorded
primary `vm_resource`; application ownership remains outside AutoDeploy secrets.
The existing source API credential updates and verifies the corresponding
source policy aliases and placement. Literal Vault/template wrappers, other
instances, existing Machine credentials and the saved API/MCP token are retained.
The canonical `guest_host_clients` data describes native rule ownership; the
task does not create a host-level rule list that could shadow group settings.

If physical application succeeds and later publication fails, the approved
permission may already be active. Rerunning Step 04 accepts only the declared
policy or that exact derived permission. A lagging source API alias is accepted
only when adding the same independently verified management permission yields
the encrypted desired policy. Other drift stops for review. The existing saved
token is reused rather than rotated, and unrelated installed use cases remain
outside the base dispatch. The existing decommission path removes these same
owned policy clients and exact native rules.

Check mode reads identities, validates the candidate and reports changes without
applying firewall or configuration writes. It does not run the guest TCP probe
or publish secrets. Tests use synthetic identities and local encrypted Git with
a fake API; a passing test does not establish live connectivity.
