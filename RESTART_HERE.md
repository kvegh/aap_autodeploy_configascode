# Restart here

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
