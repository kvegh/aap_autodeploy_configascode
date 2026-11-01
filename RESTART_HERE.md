# Restart here

Continue the AAP AutoDeploy and Configuration as Code project in this repository.
Read the applicable `AGENTS.md`, then [PLAN.md](PLAN.md),
[README.md](README.md) and
[design_decisions_history.md](design_decisions_history.md).

The goal is to deploy a replacement AAP that can run the intended production
work and deploy another complete AAP itself. Base and use-case configurations
are kept separately and encrypted; secrets and plaintext working files must
remain outside this public repository.

The existing goals, open tasks and completed work are in `PLAN.md`, with
completed items under `Done:`. Migration of that existing backlog to Beads is
still pending. Follow the current Beads skill and run `bd prime` to recover
tracker context; inspect existing issues before migrating to avoid duplicates.
Use Beads for subsequent task tracking rather than creating another Markdown
TODO list. Recheck current source and evidence before treating historical
completion notes as current deployment state.
