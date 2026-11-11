# Development speed: evidence and detailed review

## Window and limits

This finite follow-up extends the earlier [decision/action review](project-decision-action-path-flowchart.md), whose window ended on 9 November 2026 at 09:55:47 UTC. It reviews **v16 onward**, beginning with source Controller job 3197's actual VM-setup start, **3 November 2026 at 20:46:28.720763 UTC**, through a fixed **11 November 2026 at 12:41:05 UTC** cutoff. Job 3197 finished at 20:48:05.659747, elapsed **96.939s**. A later observed launch-helper execution is not substituted for this server start.

Inputs were the previously published 64-episode account, the supplied private native execution transcript, preserved Controller job/transition proofs, and maintained public source. No new Controller/host queries, installations, runtime changes or Vault/credential reads were performed for this review. Private transcripts, raw commands, raw outputs, infrastructure identifiers and credential material are deliberately excluded from this public document.

At the freeze, RHEL update 3561, host setup 3564, managed verification 3567 and managed reboot 3569 were successful. AAP v18 had **not been allocated**. Subsequent results are outside the ranking/counting window. The host rebuild's separate continuation does not establish an unattended fresh AAP deployment or completion of use-case acceptance.

### Measurement rules

- Prefer Controller `started`, `finished` and `elapsed` for job execution. Native action bounds use `started_at_ms`/`completed_at_ms` where available; visible messages establish observation/decision bounds only. **Beads modification timestamps are not action timestamps.**
- Rank concrete observed episodes, including bounded waits, rather than umbrella tasks such as “finish v18.” Earlier episode bounds remain traceable to their original numbered explanations. Where a pending episode lacks a demonstrated later action boundary, retain its earlier censored interval rather than stretch stale state to this cutoff.
- Calendar duration is neither active engineering time nor user-review time. No complete critical-path graph, continuous staffing record or coding/wait split is available. **Do not add the top-30 rows**: workstreams overlap. A diagnostic inside a broader acceptance span is shown because its own measured behavior is informative; that does not create extra additive time.
- Deduplicate native executions by their item/call IDs. Repeated status responses do not create new jobs. Controller IDs are interpreted within their source/target lane; the same numeric ID on different Controllers is not one global job identity.
- Command text containing a command is not proof that it executed. The conservative execution categories below require a directly parsed executable/subcommand. Text-only matches are reported separately. Categories overlap and are not a count of independent engineering tasks.
- Skip private reasoning records. Inspect only visible messages, tool actions and returned metadata. Parse failures are handled without rendering contents. A partial/unparseable record encountered while reading the active transcript is excluded; counts are conservative observations, not a complete cross-agent audit.
- Savings are estimates unless explicitly measured. A measured dependency cost is not proof that removing it is safe or that all its time can be recovered.

## Top 30 observed tasks and episodes

All bounds below are UTC in November 2026. `Pxx` links to the matching explanation in the earlier review; `Nxx` identifies additional evidence examined here. Durations are rounded to the nearest minute for scanning; precise job durations appear in the run ledger. “Parallel” means this record does not establish it as a technical prerequisite for the v18 path. A historical request is not a current approval or blocker.

| Rank / evidence | Concrete episode | Start → end UTC | Observed elapsed | Lane; actual explanation |
| --- | --- | --- | --- | --- |
| 01 / [P39](project-decision-action-path-flowchart.md) | Publish the pilot report and wait for actual HTML feedback | 06 Nov 09:26:10 → 09 Nov 09:54:08 | 72h28 | Parallel documentation; Mostly browser-feedback wait; not 72h coding or a proven successor blocker. |
| 02 / [P59](project-decision-action-path-flowchart.md) | Website recovery acceptance through final runner 330 | 08 Nov 19:33:36 → 10 Nov 17:40:14 | 46h07 | Recovery / acceptance; Extended to successful runner 330; ownership redesign, runtime fixes and replay, with overlapping waits. |
| 03 / [P42](project-decision-action-path-flowchart.md) | Prepare fresh CCNG prerequisites and its private reader | 06 Nov 11:36:44 → 07 Nov 16:06:40 | 28h30 | Parallel CCNG; Setup/token approval boundary and prerequisites; later 42m setup, not 28h execution. |
| 04 / [P43](project-decision-action-path-flowchart.md) | Unblock the Nexus package pipeline with a narrow allowlist change | 06 Nov 12:02:07 → 07 Nov 16:12:02 | 28h10 | Parallel package lane; Narrow access decision; approximately 31m from approval to final result, other work overlapped. |
| 05 / [P53](project-decision-action-path-flowchart.md) | Resolve CCNG first-password assumptions without copying an existing login | 08 Nov 12:23:51 → 09 Nov 09:55:47 | ≥21h32 | Parallel CCNG; later withdrawn; Historical lower bound at old cutoff; fresh-auth mismatch and stale status; subsequently withdrawn. |
| 06 / N01 | Reconcile conversion outcome and reach next host action | 10 Nov 21:34:39 → 11 Nov 12:04:34 | 14h30 | Recovery continuation; Overnight gap, actual remote-state reconciliation and a real continuation decision; avoidable share not fully measurable. |
| 07 / N02 | Stalled diagnostic 3470 through cancellation | 09 Nov 21:10:47 → 10 Nov 11:31:19 | 14h21 | Diagnostic; dependency unknown; One operation,168 status/event reads; purpose/root cause and critical-path role not established. |
| 08 / [P25](project-decision-action-path-flowchart.md) | Remove the unnecessary Windows image-inspection prerequisite | 04 Nov 21:30:16 → 05 Nov 10:46:01 | 13h16 | Recovery / acceptance; Avoidable image-inspection prerequisite plus overnight approval/coordination, not just slow copying. |
| 09 / [P57](project-decision-action-path-flowchart.md) | Resolve the held MCP artifact-key delivery proposal | 08 Nov 18:40:55 → 09 Nov 04:40:28 | 10h00 | Recovery / acceptance; Additional key-delivery dependency; superseded by target-side builds. |
| 10 / [P26](project-decision-action-path-flowchart.md) | Repair Assistant API trust before its first VM test | 04 Nov 21:39:59 → 05 Nov 06:08:52 | 8h29 | Recovery / acceptance; Overnight trust repair; active/wait split not known. |
| 11 / [P46](project-decision-action-path-flowchart.md) | Make the existing production CCNG proxy work with trusted backend TLS | 07 Nov 15:36:36 → 08 Nov 00:00:51 | 8h24 | Parallel production proxy; Proxy/auth/version/access-boundary work; parallel to successor testing. |
| 12 / [P52](project-decision-action-path-flowchart.md) | Free RAM through an approved source-AAP shutdown | 08 Nov 04:36:17 → 08 Nov 12:48:10 | 8h12 | Recovery / acceptance; Capacity/outage decision; actual shutdown 39s, not 8h. |
| 13 / [P45](project-decision-action-path-flowchart.md) | Finish Windows v16 cleanup through normal retirement jobs | 07 Nov 16:18:35 → 07 Nov 23:34:09 | 7h16 | Recovery / acceptance; Partial cleanup repairs, long gap and exact disk scope; not 7h deleting. |
| 14 / [P35](project-decision-action-path-flowchart.md) | Restart authorized work after an overnight continuation failure | 06 Nov 00:19:00 → 06 Nov 07:34:17 | 7h15 | Recovery / acceptance; Explicitly acknowledged failure to continue authorized work; agent/process responsibility. |
| 15 / [P28](project-decision-action-path-flowchart.md) | Fix the Assistant container bootstrap and complete software installation | 05 Nov 08:46:27 → 05 Nov 15:30:19 | 6h44 | Recovery / acceptance; Container trust/bootstrap repair plus about 39m successful software job. |
| 16 / [P49](project-decision-action-path-flowchart.md) | Install the testable v17 CaC catalog through the normal importer | 08 Nov 01:42:40 → 08 Nov 07:55:09 | 6h12 | Recovery / acceptance; Sequential CaC fixes/imports and dependencies; not 6h of import runtime. |
| 17 / [P54](project-decision-action-path-flowchart.md) | Exercise the v17 Windows lab and its owned cleanup | 08 Nov 12:48:10 → 08 Nov 18:32:04 | 5h44 | Recovery / acceptance; Real Windows installs/updates, narrow fixes and owned cleanup; not an uninterrupted clean replay. |
| 18 / [P32](project-decision-action-path-flowchart.md) | Resume Windows after a pending Codex approval request | 05 Nov 16:36:59 → 05 Nov 20:21:05 | 3h44 | Recovery / acceptance; Pending Codex approval operation; exact action and human/processing split unknown. |
| 19 / [P60](project-decision-action-path-flowchart.md) | Implement target-side MCP builds and attempt the first real run | 09 Nov 04:40:28 → 09 Nov 08:22:25 | 3h42 | Recovery / acceptance; Target-build implementation; first live attempt stopped before building on missing repositories. |
| 20 / [P29](project-decision-action-path-flowchart.md) | Add the Windows-only second AAP network interface | 05 Nov 11:08:23 → 05 Nov 14:43:00 | 3h35 | Recovery / acceptance; Required Windows interface ownership decision and implementation. |
| 21 / [P15](project-decision-action-path-flowchart.md) | Unblock website deployment on missing Git and DNS convergence | 04 Nov 02:09:39 → 04 Nov 05:33:32 | 3h24 | Recovery / acceptance; Initial tool-installation permission plus DNS; same pending dependency restated repeatedly. |
| 22 / [P22](project-decision-action-path-flowchart.md) | Make v16 import its own AutoDeploy configuration | 04 Nov 15:34:17 → 04 Nov 18:36:24 | 3h02 | Recovery / acceptance; Literal/template and runtime compatibility repairs in self-import. |
| 23 / [P61](project-decision-action-path-flowchart.md) | Fix the fresh CCNG workspace/tool assumption exposed by its actual job | 09 Nov 06:14:24 → 09 Nov 08:48:22 | 2h34 | Parallel CCNG; Absent fresh workspace/tool/tracker prerequisites; source fixes did not prove deployment. |
| 24 / [P33](project-decision-action-path-flowchart.md) | Fix fresh Windows creation without discarding completed disk copies | 05 Nov 20:26:57 → 05 Nov 22:37:04 | 2h10 | Recovery / acceptance; Untested producer/consumer boundaries and protected diagnostics; preserved completed copies. |
| 25 / [P30](project-decision-action-path-flowchart.md) | Import Windows definitions and repair obsolete workflow links | 05 Nov 14:48:50 → 05 Nov 16:58:00 | 2h09 | Recovery / acceptance; Obsolete workflow links/payload corrections; successful import approximately 3m14s. |
| 26 / [P62](project-decision-action-path-flowchart.md) | Capture the external-account token while preserving production CloudCLI | 09 Nov 07:45:13 → 09 Nov 09:52:38 | 2h07 | Parallel account integration; Protected handoff/access boundary; capture success did not prove two-account integration. |
| 27 / N03 | Conversion 3517 reaches whole-job timeout | 10 Nov 19:33:40 → 10 Nov 21:34:39 | 2h01 | Recovery continuation; Preparation consumed most Controller budget; remote command succeeded 31s later; no repeat conversion. |
| 28 / [P44](project-decision-action-path-flowchart.md) | Complete the Windows OS patch tests and consent safeguards | 06 Nov 12:17:50 → 06 Nov 14:16:53 | 1h59 | Recovery / acceptance; Real update processing plus consent/order safeguards; exact per-job split unknown. |
| 29 / [P19](project-decision-action-path-flowchart.md) | Verify automatic release after guest configuration | 04 Nov 09:52:37 → 04 Nov 11:40:36 | 1h48 | Recovery / acceptance; Publication, dependency retry, actual validator fix and independent policy proof. |
| 30 / [P38](project-decision-action-path-flowchart.md) | Activate Server 2025 with temporary connectivity and remove it afterward | 06 Nov 09:05:00 → 06 Nov 10:45:45 | 1h41 | Recovery / acceptance; Temporary activation connectivity and cleanup; one read-only MCP call stalled about 29m. |

The ranking is of **observed spans**, not a claim that these are the 30 longest actual CPU runs. In particular, P53 remains a lower-bound historical observation. Its deployment was subsequently withdrawn; the infrastructure/tracker lane is held. It is not legitimate to promote that stale/open interval into an ongoing v18 gate. P39's browser-feedback span is likewise a parallel documentation lane, not three days of coding.

### What changed after the old cutoff

**Website acceptance continued to an actual end-to-end result.** P59's earlier cutoff showed source/kernel checks without a proven recovery loop. The extended observation ends at target v17 runner 330's successful finish on 10 November at 17:40:14.119314. This broader **46h07** acceptance episode includes ownership/design work, fixes, coordination and real replay attempts; the evidence does not assign every intervening hour to one firewall defect. Runner 326 failed at the configured 48-turn limit; runner 330 then succeeded with child repair 333. A child repair alone would not have proved the runner completed.

**A stalled diagnostic remained running overnight.** Ad hoc 3470 started on 9 November at 21:10:47.759452 and was canceled on 10 November at 11:31:19.811532: **51,632.052s, or 14h20m32s**. Its native module was `command`. The transcript contains **91 retrieve calls and 77 event-list calls for this one ID**, plus its cancellation action. Purpose and underlying transport/execution cause were not established by the bounded evidence inspected here. Calling it a necessary v18 critical-path step, or blaming the user for the entire interval, would be speculation. The demonstrated process problem is prolonged monitoring without an effective bounded resolution.

**The conversion timeout did not mean conversion had failed on the host.** Source job 3517 and workflow 3511 truthfully remained failed. Protected remote outcome evidence showed native async completion with return code 0 at 21:35:10.606499 on 10 November, approximately **31 seconds after job failure**. There was no second conversion. Preparation had used roughly 1h55 of a 7,200-second whole-job budget, despite a 14,400-second allowance for the conversion command itself. Controller also needed time for cleanup, reboot and final proof. This mismatch created a continuation problem at exactly the point where blind replay would be unsafe.

**The next host action was much later than remote completion.** N01 measures job 3517 failure through protected credential cleanup on 11 November at 12:04:34: **14h29m55s**. The record includes an overnight observation gap, reconciliation of actual remote state, a genuine protected-input/continuation decision and repeated status replies. The entire span is not proven avoidable agent idle time or human decision time. Visible host-continuation final replies recur between 11:23 and 11:56; they are communication events, not completed host stages. The next explicit user continuation was recorded at 11:57:52.798. State recovery and the actual approval boundary should have been made concrete once, with already-authorized independent work continuing.

**Normal continuation preserved completed work.** Cleanup and bootstrap reboot were followed by the existing RHEL update, host setup, managed verification and managed reboot stages. Preflight, physical deployment assignment, DNS and conversion were not all blindly replayed. In particular, the deployment counter requires Rocky 9: restarting the whole old workflow after successful conversion would re-enter an incompatible completed stage. There is no supported failed-node resume exposed by the inspected Controller workflow relaunch contract; relaunch creates an identical workflow and accepts no input body. A failed historical workflow cannot simply be declared successful.

## Repeated short operations

The following table is a census of the **root transcript's observed native actions in the stated window**, not a full inventory of subprocesses executed by every delegated agent. A parsed shell execution containing several actual subcommands counts once in each matching category. Counts do not measure wasted time.

| Operation/category | Unique observed executions/calls | What the count establishes |
| --- | --- | --- |
| All shell executions | 7164 | Native CommandExecution IDs; includes other projects, failures and parallel work. |
| Direct Git status | 426 | Actual parsed Git status subcommand; status-text matches are reported separately. |
| Direct Git whitespace checks | 211 | Actual parsed diff-check subcommand; necessary checks can recur after changes. |
| Direct Beads reads | 327 | Read commands; not proof that each was needed or redundant. |
| Direct Beads mutations | 538 | Task/relationship changes; owner-required durable tracking is retained. |
| Direct task-export/mirror/version scripts | 289 | Recognized existing maintenance entry points, including required publication work. |
| Direct unittest executions | 49 | Known Python-module runner; alternate/script/delegated launches are not comprehensively counted. |
| Unfiltered unittest discovery | 7 | Subset of the preceding row; no pattern/filter recognized, not proof of redundancy. |
| Agent status listings | 235 | Tool calls, not actual implementation runs. |
| Agent follow-up calls | 444 | Communication/orchestration, not proof of useful progress. |
| Agent messages | 1016 | Communication, not tests or jobs. |
| Input-form calls | 47 | Includes preferences and real decisions; not a count of unnecessary approvals. |
| Native job retrieves | 102 | 51 distinct numeric IDs in this native source connection; not 102 launches. |
| Diagnostic 3470 status/event reads | 168 | 91 retrieves+77 event-list calls for one operation; one separate cancellation action. |
| Shell text merely containing Git status | 500 | Text-match category; includes quoted/generated commands, not all executable proof. |
| Shell text containing a test-runner name | 58 | Text-only category; not a test-run count. |
| Shell text containing maintenance script names | 353 | Text-only category; not all direct invocations. |

These distinctions materially change the conclusion:

- The 168 reads of ad hoc 3470 represent **one operation**, not 168 diagnostic launches. There were 102 native job-retrieve calls across 51 IDs in the broader window; polling is not job creation. There may also be API reads performed by existing local helpers, which this native-MCP count does not capture.
- Listing agent state, sending a follow-up and receiving progress are communication, not proof that the delegated implementation advanced. A busy transcript can coexist with a stalled task. Repeatedly reviving a completed, held or withdrawn lane is especially unproductive; do not use this review to restart one.
- Beads writes and documentation/version maintenance have explicit owner requirements. README, decision history, encrypted recovery/task mirrors and version increments cannot simply be deleted from the workflow. Batch the necessary updates and checks at meaningful implementation/publication boundaries. The count alone does not identify which particular update was unnecessary.
- Seven directly recognized unfiltered unittest-discovery executions are a **lower bound**, not seven proven redundant runs. Forty-nine recognized unittest executions include focused checks. Commands hidden inside scripts, alternate test launchers and delegated transcripts are not comprehensively counted. The full-suite command must be matched to its code change before declaring it waste.
- Hundreds of fast status/diff/task commands can consume orchestration and attention despite short subprocess runtimes. Their calendar contribution is not established by multiplying the count by an assumed delay.

### Repeat justification: examples

| Repeat | Classification | Reason |
| --- | --- | --- |
| Verification 3567 before reboot and the required later post-reboot verification | Intentional; preserve | Pre-reboot correctness does not prove boot persistence or restored managed access. The later verification is outside this freeze. |
| Source package reboot and later managed-host reboot | Intentional; preserve | They prove different transitions and use different connection stages. |
| Runner 330 after runner 326 hit its turn limit | Narrow fix verification | Diagnostic reporting was improved after the failure; the later end-to-end replay passed with the same limits. The earlier exhaustion cause remains unproved; repair 333 alone was insufficient. |
| Physical cleanup 3502 after 3499 failed final metadata | Inspect actual outcome, then narrow continuation | A failed final record is not evidence that already-deleted resources still exist. Repeating destructive removal blindly would be wrong. |
| Project update 3552 after 3550 artifact-hash failure | Justified retry after diagnosis | First update failed; the successful corrected retry is a distinct execution. |
| Project update 3565 after a new source publication | Justified refresh | It fetched a different revision from 3562. |
| Same-revision dependencies before verification and reboot | Optimization candidate | Their observed cost is real, but dependency/environment checks may still be required. Reuse needs a deliberate verified policy. |
| Additional unchanged status/event reads of3470 | Process waste candidate with strong evidence | 168 reads did not supply a resolution; set a bounded response to absent progress. Not every individual poll is unnecessary. |
| A whole successful pipeline repeated solely to obtain another green status | Redundant if evidenced | No such repeat is inferred merely from multiple job IDs. The demonstrated host continuation avoided repeating conversion. |
| Full suite after an unrelated documentation-only edit | Avoidable if present | No runtime behavior changed; use document/privacy checks. This is a recommendation, not attribution of every observed suite run. |

## Recent run ledger and actual runtime

This is a bounded ledger of the executions needed to explain the new findings, not every job in the project. Source and target lanes remain distinct. Blank bounds mean the duration/result was confirmed in the supplied operational evidence but a complete start/finish pair was not independently re-extracted for this document.

| Lane / execution | Started UTC | Finished UTC | Elapsed | Result and interpretation |
| --- | --- | --- | --- | --- |
| Source VM setup 3197 | 03 Nov 20:46:28.720763 | 03 Nov 20:48:05.659747 | 96.939s | Successful; actual v16 starting boundary. |
| Target v17 runner 326 | Not re-extracted | Not re-extracted | 228.972s | Failed: `error_max_turns`, limit 48. |
| Target v17 runner 330 | 10 Nov 17:34:31.359009 | 10 Nov 17:40:14.119314 | 342.760s | Successful end-to-end runner. |
| Target v17 repair 333 | Not re-extracted | Not re-extracted | 12.318s | Successful child repair; contained in runner 330, do not add as serial time. |
| Source cleanup 3499 | Not re-extracted | Not re-extracted | Not established here | Failed at final metadata; do not infer that prior physical cleanup was undone. |
| Source cleanup 3502 | 10 Nov 18:45:50.281348 | 10 Nov 18:50:09.030267 | 258.749s | Successful continuation. |
| Source provider-status 3505 | 10 Nov 18:59:54.451888 | 10 Nov 19:01:52.856329 | 118.404s | Successful readback around the provider transition. |
| Source provider-status 3508 | 10 Nov 19:07:24.930179 | 10 Nov 19:08:27.068823 | 62.139s | Successful later readback; not a second reinstall. |
| Source workflow 3511 | 10 Nov 19:28:41.067621 | 10 Nov 21:34:39.591765 | 7558.524s | Failed workflow; contains child jobs and parallel DNS. |
| Source preflight 3512 | 10 Nov 19:29:40.687164 | 10 Nov 19:31:01.837329 | 81.150s | Successful. |
| Source physical assignment 3515 | 10 Nov 19:32:12.962578 | 10 Nov 19:32:31.498729 | 18.536s | Successful; physical-host counter is separate from the AAP VM allocator. |
| Source dependency 3519 | 10 Nov 19:32:32.709686 | 10 Nov 19:33:40.359513 | 67.650s | Successful project update before conversion. |
| Source conversion 3517 | 10 Nov 19:33:40.749809 | 10 Nov 21:34:39.377015 | 7258.627s | Controller timeout; configured budget 7200s plus termination overhead. |
| Remote async conversion | Not established here | 10 Nov 21:35:10.606499 | Not established here | Return code 0; finishes after Controller timeout. One conversion, not two. |
| Source dependency 3550 | 11 Nov 10:54:26.432194 | 11 Nov 10:55:15.512103 | 49.080s | Failed artifact-hash validation. |
| Source dependency 3552 | 11 Nov 11:04:17.961647 | 11 Nov 11:06:02.915452 | 104.954s | Successful retry. |
| Source dependency 3554 | 11 Nov 11:08:25.872728 | 11 Nov 11:10:07.919695 | 102.047s | Successful final source update. |
| Source hardware preflight 3553 | 11 Nov 11:10:08.581331 | 11 Nov 11:10:20.865265 | 12.284s | Successful; actual identity protection remains necessary. |
| Protected cleanup | 11 Nov 12:04:34 observation | — | Not established here | Conversion credential cleanup reconciled without rerunning conversion. |
| Bootstrap reboot | Not re-extracted | 11 Nov 12:06:10 observation | About 89s | Successful; actual boot transition, not package ownership alone. |
| Source dependency 3562 | 11 Nov 12:06:51.436295 | 11 Nov 12:09:13.021051 | 141.585s | Successful; revision 31c0a72. |
| Source RHEL update 3561 | 11 Nov 12:09:13.988513 | 11 Nov 12:15:54.131331 | 400.143s | Successful;326 Ansible events. |
| Source dependency 3565 | 11 Nov 12:18:09.003119 | 11 Nov 12:19:41.579036 | 92.576s | Successful; new revision 8fd228a. |
| Source host setup 3564 | 11 Nov 12:19:41.883557 | 11 Nov 12:29:27.136362 | 585.253s | Successful;2358 Ansible events. |
| Source dependency 3568 | 11 Nov 12:32:11.614076 | 11 Nov 12:33:32.838317 | 81.224s | Successful; same revision 8fd228a. |
| Source managed verification 3567 | 11 Nov 12:33:33.480320 | 11 Nov 12:33:52.618136 | 19.138s | Successful;194 events,17 substantive checks. |
| Source dependency 3570 | 11 Nov 12:36:15.005472 | 11 Nov 12:37:51.145047 | 96.140s | Successful; consuming reboot 3569 used 8fd228a. |
| Source managed reboot 3569 | 11 Nov 12:37:51.447547 | 11 Nov 12:39:11.099381 | 79.652s | Successful managed reconnection;165 events. |

The four latest dependencies total **411.525s (6m51.525s)**. The actual host-stage runtimes 3561/3564/3567/3569 total **1084.186s (18m04.186s)**. These arithmetic totals describe these particular sequential stages, not the whole project or all intervening delay. The bootstrap reboot, publication, operator decisions and gaps are separate. Counting events as tests or counting dependency polls as new runs would greatly exaggerate activity.

Revision 31c0a72 was used before publication of8fd228a. Updates 3565 and 3568, and consuming jobs 3564/3567/3569, establish the later revision. The two dependencies after the first 8fd228a update cost **177.364s (2m57.364s)**. This is an optimization candidate's observed cost, not guaranteed savings: collection artifacts, execution environments and freshness requirements must also match. No caching change is included in this review.

## Causes and attribution

### Continuation and orchestration

P35 explicitly acknowledged a 7h15 failure to continue already-authorized work. This is agent/process responsibility, not evidence of a missing user approval. Later recurrence of status-only replies and the long 3470 monitoring episode show that communication volume did not ensure progress. Native job state, last successful stage, remaining authorized action and an actual required decision should agree before a response ends. A completed or held agent should not be revived merely because an umbrella objective remains open.

The conversion workflow exposed a related operational gap: its normal relaunch starts the graph again, while several earlier stages had already succeeded and conversion had changed the required OS. A safe narrow continuation took more analysis than a successful run. Make remaining normal stages and their actual decisions reviewable in the existing task record; do not invent another scheduler or falsify the old run.

### Excessive caution and permission loops

The evidence supports specific criticism, not the assertion that approvals are generally unnecessary. Legal acceptance, access-control changes, source-AAP shutdown and destructive cleanup scope were real decisions. Initial installation permission was also an explicit workspace requirement. In contrast, P25 added image inspection as a prerequisite that was later removed; the overnight approval/coordination episode therefore included avoidable work. P15 restated the same missing-Git dependency several times while other work continued. Repeating the request or treating a delivered approval as still absent can extend confusion without improving safety.

The 47 observed input-form calls do not prove 47 permission loops. Forms include preferences and real scope questions, and the actual execution-approval channel is separate. The record does not support assigning all unanswered time to the user. Preserve prior authorization, identify exactly what decision remains, prepare concrete reviewable work first, and ask once when genuinely necessary.

### Overengineering and ownership

The firewall/website episode involved custom deployed JSON and ownership helpers that were subsequently replaced with CaC-driven native Ansible behavior. Multiple stores/writers and repository handoffs expanded the surface to debug. That rework is evidence against building extra control machinery before the normal lifecycle and ownership contracts are settled. It is not proof that every firewall identity check was excessive, nor that all 46 hours were design churn.

P57's ten-hour artifact-key transport hold was removed when target-side builds were chosen. Transport choices should be tested against already-authorized native paths before introducing another key-delivery dependency. Conversely, protected shared name allocation, exact VM ownership, strict SSH/TLS, safe concurrent publication and cleanup proof solve demonstrated risks; removing them would trade speed for ambiguity and unsafe targeting.

### Testing and redundant reruns

Fresh replay exposed gaps missed by local checks: unsafe/template tags, string/number coercion, collection payload behavior, obsolete workflow links, guest routing and partial-deletion state. This is primarily **test placement and contract coverage**, rather than proof that the total test count was too small. Use installed-version rendering/refusal tests at the boundary, then retry only the failed normal stage. Preserve copied disks, completed installations and successful branches where the actual outcome proves they remain usable.

A full suite can be justified after shared logic changes; repeating it after no relevant changes needs a reason. The census cannot independently classify every suite invocation as redundant. The earlier report also documented a local test hanging for roughly 14 minutes before proper writable temporary paths let it finish in 0.4s, and a read-only MCP request stalled about 29 minutes. Those are environment/deadline defects, not evidence that the tested feature intrinsically takes that long.

### Stale state mistaken for required work

Before the next AAP allocation, saved source templates 154/155/156 still selected generation 16. Their normal launch variables and surveys were disabled. Maintained CaC had already cleared those selectors after retirement. Sending a generation 18 launch variable would therefore not fix the stale saved value. Registration publishes tokens/inventory/placement; it does not rewrite these saved stage selectors. The narrow remedy is reconciliation of those existing fields after normal 153 actually returns a completed allocation, preserving all unrelated settings. Never pre-reserve 18 by editing a counter or recreate an older instance to satisfy a stale selector.

Historical CCNG status is another stale-state risk. Its deployment request is withdrawn; infrastructure/tracker work is held and rekeying deferred. Those statuses must be respected. Historical waits are included to explain the record, not to propose reminders, resume held work or make them current v18 dependencies.

## Prioritized changes and how to judge them

| Priority | Concrete change to working practice or existing implementation | Evidence | Acceptance / limitation |
| --- | --- | --- | --- |
| 1 | Inspect terminal outcome and continue the next authorized normal stage; preserve one genuine pending decision. | P35; N01; repeated status replies. | Fewer status-only turns before action; no bypassed approvals or replay of successful destructive stages. |
| 2 | Budget whole jobs by preparation + native async + reboot + cleanup/proof; investigate stalled diagnostics against meaningful progress. | N02/N03;3470 and 3517. | A representative run finishes with cleanup/proof or fails with a bounded actionable cause. Source-only timeout repair is separate from runtime deployment. |
| 3 | Move installed-version producer/consumer contract checks ahead of long replay; run focused regressions after fixes. | P22/P30/P33/P49; literal tags and rendered timeout tests. | Fewer first-live-run serialization/link failures; retain real end-to-end acceptance. |
| 4 | Reconcile exact existing selector fields from actual allocation and canonical CaC. | Stale 154–156 selectors. | Correct target, unchanged credentials/prompts/limits, no new wrapper or store. |
| 5 | Batch required documentation/task/version publication around meaningful changes. | Repeated maintenance census; owner requirements. | Required recovery records remain current; fewer unchanged reads and intermediate publications. No claim of measured savings yet. |
| 6 | Evaluate same-revision dependency reuse only with explicit revision/artifact guarantees. |411.525s total;177.364s later same-revision overhead. | Potential savings measured in a controlled comparison; no implicit caching or security change. |
| 7 | Keep parallel/withdrawn/held work out of the active successor gate. | Historical CCNG/documentation lanes. | No proactive reminders or resumed held work; completed base stages remain distinct from optional application acceptance. |

This review changes documentation only. It neither implements those runtime proposals nor establishes future savings. The short [main review](development-speed-improvement-review.md) is the intended reading path; this appendix preserves the measurements, qualifications and concrete counterexamples.
