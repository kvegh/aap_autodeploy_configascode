# Review of the older destroy template

The current **Decommission AAP Test Instance** and older **Destroy Test AAP VM v2**
Job Templates reference the same SCM Project, execution environment and
`destroy-test-aap.yml`. The older template does not retain a separate teardown
implementation. This review inspected configuration and history without launching
or changing a job.

## Current differences

| Setting | Current decommission template | Older destroy template |
| --- | --- | --- |
| Inventory and limit | Dedicated single-hypervisor recovery inventory and fixed limit | Shared inventory and empty limit |
| Saved credentials | Environment Vault, CaC Vault, selected hypervisor Machine, Git writer, source API and CA | None; credentials requested at launch |
| Target selection | Required registered-instance selection and matching confirmation survey | No survey; free-form variables requested at launch |
| Saved variables and tags | Empty | Empty |
| Timeout | Thirty minutes | No template timeout |
| Saved privilege escalation | Enabled | Disabled |
| Playbook privilege escalation | Enabled by the shared playbook | Enabled by the same shared playbook |
| Schedules and workflow-node references | None found | None found |
| Webhooks and direct user/team role grants | None found | None found |

The saved privilege-escalation flag on the older template does not override the
playbook's explicit `become: true`. Both templates still require the correct
managed account and sudo authorization. Organization-level inherited access is
separate from direct template grants.

No unique saved variables, tag selection or cleanup logic needs migration from
the older template. Its distinguishing behavior is asking the operator to supply
credentials and arbitrary variables. That flexibility is not required by the
current dedicated recovery inventory and confirmation survey.

## Cleanup coverage

Both templates now execute the current registered-instance teardown. It checks
pinned hypervisor identity, verified VM and disk ownership, snapshots, related
same-version guest resources, complete DNS pagination and nginx validity before
changing resources. The implementation retires selected VM permissions, domain
definitions and disks, versioned website/proxy/auth/cache files, certificates,
matching DNS including orphaned version labels, source inventory entries and
stored instance access. Consumed allocation history remains reserved.

Historical successful runs of the older template used older SCM revisions.
They do not establish that its former VM-name-only launch procedure works with
the current playbook. Without the registered instance, confirmation, pinned
inventory and required credentials, the current older template is incomplete
for ordinary launch and should fail its preflight.

The current production CaC capture still contains both template definitions.
Its current-template timeout also differs from the live thirty-minute value;
future capture reconciliation should retain the reviewed live timeout and
portable environment-Vault reference.

## Original-host implications

The current registered routes inspected for this review belong to the recovery
hypervisor. The current decommission playbook requires that registered ownership
and the recovery isolation machinery. The older template's broad inventory does
not supply a maintained teardown path for historical VMs on the original
hypervisor. Retaining older deployment templates there does not establish a
matching supported decommission procedure.

Removing the older template from future CaC installations therefore loses no
currently maintained cleanup behavior. It should not be presented as removal of
a working original-host teardown capability. If historical original-host VMs need
retirement, review their ownership and cleanup requirements explicitly rather
than weakening the recovery guards.

## Recommendation

Use **Decommission AAP Test Instance** for registered recovery deployments.
Exclude **Destroy Test AAP VM v2** from future CaC installations; leave existing
production objects and historical jobs unchanged until their retirement is
explicitly authorized. Preserve the original host's older deployment templates
according to the separate owner decision. No deletion or deployment was performed
as part of this comparison.
