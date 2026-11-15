# Restart here

## Verified replacement; retirement proof next — 2026-11-15

The resumed provider check and authenticated fresh-OS read passed, including
all three provider-matched SSH keys, unchanged hardware, empty guest storage
and required proof tools. Current Hactar trust is published and its Source host
alias now matches; old shared/platform captures and the rebuild inventory pin
remain intentionally unchanged. Bind the final Hactar revision and require
the actual native absence proof before metadata retirement or conversion.
The new generation remains unallocated and full-run acceptance is outstanding.

## Maintenance completed; execution resumed — 2026-11-15

The owner explicitly resumed the existing deployment goal after maintenance.
Continue from the already completed provider reinstall/reset. Revalidate current
provider and new-host identity, then follow the guarded trust/proof/retirement
sequence. Do not repeat the reset to observe progress. Beads contains the latest
native outcomes and active task state; the maintenance checkpoint below is
historical context.

## Saved maintenance checkpoint — 2026-11-15

The owner halted operations for a maintenance break at this saved checkpoint;
execution and Beads work were paused then. The later explicit resume above
revokes that hold within the existing scope. Task pings alone never resume a
user pause.

The authorized provider reinstall/reset job completed successfully. Its template
was restored to safe discovery defaults immediately after launch. The last
read-only provider check also completed, but readiness was false: the provider
had three host-key fingerprints while the network scan returned no SSH keys.
No authenticated fresh-OS check, trust publication, native absence proof,
metadata/DNS retirement, conversion or next-generation allocation has occurred.
All Controller jobs and delegated work were inactive at the saved checkpoint.

Old ownership, selected allocation, DNS and the old rebuild-inventory pin remain
intact intentionally. They describe the previous candidate, not a verified
current installation. The next shared number remains unconsumed; the new
platform and workload deployments have not run. The qualified runtime changes
and exact execution records are preserved in Beads and the existing encrypted
`docs/project-task-records.vault.yml` recovery export.

On an explicit resume, inspect the saved native job outcomes and current provider
state first. Do not repeat the completed reset. Require provider-verified fresh
SSH keys before authenticated inspection. Follow the documented Hactar-only
trust transition, actual post-reset proof and metadata-only retirement before
conversion or new guests. Preserve old immutable ownership until that succeeds;
never replay historical whole-trust mutators or the saved destructive profile.

Continue the AAP AutoDeploy and Configuration as Code project in this repository.
Read the applicable `AGENTS.md`, [README.md](README.md), the
[agreed targets](docs/recovery-and-use-case-targets.md), [TODO.md](TODO.md) and
[design_decisions_history.md](design_decisions_history.md).

The goal is to deploy a replacement AAP that can run the intended production
work and deploy another complete AAP itself. Base and use-case configurations
are kept separately and encrypted; secrets and plaintext working files must
remain outside this public repository.

Beads is the authoritative task tracker. Run `bd prime` when that tracker is
available. [TODO.md](TODO.md) is its generated Git overview, while
[PLAN.md](PLAN.md) retains historical planning. Do not create a second independent
task list or infer current deployment state from an old completion note.

Task records must survive loss of the current Beads database. The existing
Hactar repository keeps the complete scoped record snapshot in
`docs/project-task-records.vault.yml`, encrypted with the existing CaC Vault key.
It preserves descriptions, decisions, acceptance criteria, notes, outcomes,
relationships and comments. Public TODO output contains reviewed metadata only;
private task details are never copied there. The snapshot is a recovery copy,
not a second task authority or an automatic replacement for the Dolt database.
Keep access to the repositories and Vault key available outside the hypervisor
being reinstalled.

After changing a project task in Beads, refresh and commit both Git mirrors:
Use an existing Python environment that provides Ansible Vault support; select
its interpreter, such as `python3.12`, instead of installing another dependency.

```sh
python3 scripts/sync_todo.py \
  --snapshot-file /path/to/hactarconfig/docs/project-task-records.vault.yml \
  --vault-password-file /secure/path/cac-password
```

Run the same command with `--check` to detect stale output. In the Hactar
repository, also run its existing `python3 scripts/sync_todo.py --check`.
Read the decision history and linked requirement documents for the current
agreed design. If Beads is unavailable after reinstalling, read the Git TODOs and
decrypt the snapshot with `ansible-vault view` to recover the full task context
before restoring or recreating the tracker through an approved Beads procedure.
Do not initialize another tracker automatically or treat exported JSON as a
native database backup. Verify that commits reached their remote before relying
on them for recovery.
