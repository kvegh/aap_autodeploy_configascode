# Decommission a test deployment

The existing teardown entry is maintained as **Decommission AAP Test Instance**
and runs `destroy-test-aap.yml`. Select the registered `aap_instance_key` and type
that same value as `aap_decommission_confirmation`. The job uses the one-host
recovery inventory and its Machine credential, environment Vault and private
AutoDeploy CaC reader/Vault. It is separate from the deployment workflow.

Before deletion it verifies SSH keys, the actual hypervisor machine ID and
persistent isolation. It checks the selected domain's exact disk and refuses
snapshots or unexpected storage. DNS ownership is checked before any destructive
step. An unexpected destination stops the job for review.

The complete deployment scope includes AAP, matching versioned Zabbix,
testserver and TRA guests, and the demo website. Related guests require recorded
UUID/disk ownership in the existing encrypted reservation before deletion.
Known website content/cache/checkout, nginx vhosts/rate-limit/Basic-auth files,
certificate lineages and upstream CA files are removed only for that version.

The job paginates the entire DNS zone, selects exact `vNN` labels including
unknown orphaned role names, validates ownership, rechecks each record set
immediately before deletion and verifies provider absence. Conflicting addresses,
unexpected IPv6 or unreviewed record types stop before VM deletion. Other
versions and production records are preserved.

After infrastructure retirement, the existing Git writer marks the consumed
reservation decommissioned, removes the active token and inventory entry from
encrypted CaC, updates the source token-store credential and removes the matching
source inventory/manual API credential. A source credential still referenced by
a template is refused rather than silently detached. Check mode performs the
ownership review without destruction. Failed partial cleanup can be rerun with
the same exact confirmation; normal deployment stages refuse retired entries.

The shared counter and consumed reservation history are never rolled back.
The next fresh deployment consumes a new number.
