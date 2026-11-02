# TODO

Beads is the source of truth. This file mirrors selected AutoDeploy backlog
entries for Git readers; it is not the complete workspace backlog. Update the
Beads issue first and refresh its mirrored entry when its scope or status changes.

## bead-wd-72v — Design complete CaC object ownership beyond labels

- [ ] Status: **open**; priority: **P2**; type: **feature**.

Inspect the authoritative issue with `bd show bead-wd-72v`.

### Requirement and unresolved decision

Every managed AAP CaC object must have a clear owning AAP Project/use case,
including a defined owner for shared platform resources and references from
their consumers. Ownership must remain recoverable across CaC deployment and
later API extraction so additions, changes and removals reach the correct
configuration file and private companion repository.

The proposed universal ownership label cannot cover every object type. Keep
existing useful labels, but choose another ownership mechanism before claiming
complete coverage. No replacement mechanism has been selected or implemented.

Project-specific CaC files already establish ownership for their definitions,
even where several files share a private repository. They do not by themselves
classify a newly created, previously uncaptured production object. A custom key
ignored or removed before the CoP role is not persisted in AAP and cannot be
recovered from its API.

### Verified label coverage

Checked on 2026-11-02 using read-only Controller API GET/OPTIONS responses and
the JavaScript served by the current production UI. Recheck on another version;
this table covers Controller resources, not all Automation Hub or EDA objects.

| Object | API labels | UI label controls | UI label filter |
|---|---|---|---|
| Job Templates / Workflow Templates | Yes | Create/Edit | Yes |
| Inventories | Yes | Standard inventories only | No |
| Schedules | Yes | Conditional launch prompts* | No |
| Workflow nodes | Yes | Conditional node prompts* | No |
| Jobs / workflow runs | Read-only | Supplied at launch* | Yes |
| SCM Projects | No | No | No |
| Credentials / credential types | No | No | No |
| Execution environments | No | No | No |
| Hosts / groups / inventory sources | No | No | No |
| Organizations / teams / users | No | No | No |
| Notification templates / instance groups | No | No | No |

*Label prompts appear only when the referenced template enables Labels > Prompt
on launch. Schedule/node labels configure the future job's labels; they are not
a universal object ownership field. Runtime job label associations are read-only.

All API-supported types accepted labels__name filtering, including inventories
and schedules whose overview filters omit labels. Standard inventory Create/Edit
exposes Labels; smart/constructed inventory editors do not. Inventory and template
Details pages hide labels when none are assigned. The installed CoP inventory
role does not manage inventory label associations, despite API support.
For inventory sources and notification templates there were no existing objects
to probe: the negative checks used create schemas and UI code, not an instance
label endpoint. No labels or other AAP resources were changed during the audit.

### Ownership ideas to evaluate

1. An encrypted ownership registry keyed by resource kind and stable logical
   identity, mapping to the owning project, CaC file and companion repository.
   Shared resources have one owner and explicitly declared consumers.
2. Reserved description markers where the object supports descriptions, with
   an external mapping for resource types without suitable metadata. Preserve
   human descriptions and check field support for each resource type.
3. Ownership derived from existing relationships, such as a Job Template's
   project or a host's inventory. Treat dependencies as evidence, not proof of
   unique ownership: a credential or execution environment can be shared.
4. A hybrid: the registry is authoritative, existing relationships suggest
   assignments, and labels/markers provide visibility only where supported.

Compare these ideas for deployment/API roundtrips, complete resource coverage,
new manually created objects, shared dependencies, renames, confirmed removals,
and differing runtime IDs across AAP instances. Define a review path for missing
or ambiguous ownership rather than silently assigning it to a project.

### Completion criteria

Review the alternatives and select the ownership design with the owner before
implementation. Define a read-only coverage audit against production that reports
uncaptured resources, unassigned objects, conflicting ownership and missing
dependencies. Preserve encrypted secrets, CoP deployment compatibility and
existing labels. This backlog entry does not authorize live metadata changes,
use-case imports or implementation of a new ownership architecture.

**Acceptance criteria:** Document the verified API/UI capability matrix, compare alternative ownership mechanisms, select a design with the owner, and define a complete read-only ownership/coverage audit before implementation.
