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
