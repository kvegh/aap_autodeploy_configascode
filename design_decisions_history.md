# Design decisions history

## Align both AAP content pushes at the content section — 2026-11-14

Implementation `f95ff2168e1d0000b23687772393969c1d37047e` (0.63.32) applies the
existing responsive content-arrow placement to both the blue base-content stage
and the purple content-change stage. Both arrows enter the receiving content
area at the original AAP’s top edge, accounting for caption height and resize.
The preceding AAP-settings arrow keeps its existing placement.

All 23 existing walkthrough checks, JavaScript syntax and whitespace checks
passed. Existing coverage now exercises both content stages and their resize
calculation. Concurrent runtime updates were preserved before publication.
Pages run `43571282117` succeeded; six published assets matched the checkout and
all 23 deployed-asset checks passed. Geometry inputs are simulated, so browser
placement was not visually measured. No browser or dependency was installed.

## Read disabled appliance metadata through the existing API — 2026-11-14

Implementation `fe49d8d` (0.63.30) reads the selected disabled appliance row
from the native inventory response already used by pre-import preparation.
Metadata-only appliances need not be exposed as Ansible targets or appear in
hostvars. The row must be unique, disabled and belong to the selected importer's
existing inventory; the same complete native/API provenance validation follows.
Linux guest handling and all credentials remain unchanged.

A real encrypted-Git regression reproduced missing appliance publication before
the correction, then passed with no appliance hostvars. It also proves an enabled
appliance row cannot publish. That regression and eight related native ownership,
retirement and preparation tests passed on Core 2.20. No live deployment result
is inferred from those fixtures.

## Retain native ownership for an API-only monitoring appliance — 2026-11-14

Implementation `9c75987` (0.63.28) accepts the Zabbix appliance's schema 2
native VM and authenticated API provenance instead of requiring guest SSH keys,
account or machine ID. The owner explicitly requires no SSH into the appliance.
Generated monitoring deployment settings discard the obsolete management-account
inputs. Existing Linux guest transport and identity requirements are unchanged.

The source appliance row is disabled and contains metadata only. Retirement
retains exact domain UUID, disk, network, MAC, address and physical hypervisor
checks, rejects SSH-bearing or enabled appliance rows and preserves other owners.
Older or conflicting records require verified correction rather than fabricated
API evidence or a compatibility fallback. The owner's startup choice is to boot
under verified network isolation, configure through the internal API, and keep
Internet forwarding blocked; no separately prepared image is required.

Eight focused native Core 2.20 tests passed for ownership refusal, metadata-only
inventory, saved-CaC continuity, preservation of successor guests, encrypted
retirement and AIOps preparation. Seven broader local literal-wrapper assertions
also fail unchanged on the public baseline, so no full-suite pass is claimed.
Actual appliance correction and end-to-end AIOps acceptance remain unverified.

## Distinguish AAP configuration from AAP content pushes — 2026-11-14

Implementation `3ce55f2734cfd94921adb7e1cb80a122a56ab982` (0.63.22) labels the
blue AAP-settings action “Push AAP config” and the following base-content action
“Push AAP content”. Distinct captions identify what each stage sends. The purple
change captions and responsive content-arrow placement remain unchanged.

All 23 existing walkthrough checks, JavaScript syntax and whitespace checks
passed. Pages run `43562549560` published the implementation successfully; all six
published assets matched the checkout and all 23 deployed-asset checks passed.
The interaction checks use a simulated DOM; browser layout was not measured.

## Combine scanner and CoP capabilities — 2026-11-14

The owner explicitly corrected the extension approach: take the union of the
existing scanner and CoP exporter capabilities rather than assuming CoP covers
everything already handled locally. The research in
`e032374681d6145efae5b828e0891458eaf80345` establishes useful CoP coverage but does
not establish semantic equivalence or a complete superset.

Keep locally implemented capabilities, verify CoP-only additions, and compare
overlapping fields and relationships before selecting their implementation.
Preserve review, conflict, deletion, visibility, reference and protected-value
guarantees across the combined coverage. Conflicting values require review;
removing duplicate capability descriptions must not choose a configuration value.
The README-linked model guide now states this requirement explicitly. Runtime
integration remains unfinished; this documents the agreed direction without
claiming an implemented union or changing deployed configuration.

## Assess configuration coverage against component models — 2026-11-14

Documentation `e032374681d6145efae5b828e0891458eaf80345` (0.63.16) identifies the
deployed component APIs, OpenAPI documents, collection arguments and installation
definitions as the available sources for AAP configuration models. Read-only
discovery showed that the gateway's schema describes gateway resources rather
than every backend routed through it. A single complete portable model was not
verified, so an accessible API or exported file is insufficient evidence of
complete configuration coverage.

The CoP exporter already supports several Controller features refused by this
project's current extractor. Its supported-object scope, export selections,
settings overrides and protected secret placeholders must be checked before
adding replacement serializers. Record unsupported or unreadable fields and
relationships explicitly; a masked secret cannot prove equality or a rotation.
The README-linked research guide separates these findings from the unfinished
all-component scanner and owning-project Git capture. No dependency, API
permission, deployed setting or scanner behavior changed with this research.

## Render and publish generated monitoring projections on Core 2.20 — 2026-11-14

Implementation `e74b38ac09c78a04581c68cbf0f78a7bfd6c33b1` (0.63.10) gives the existing AIOps preparer's
code-generated importer and firewall-owner expressions, and its reviewed policy
rewrite, explicit template trust. Core 2.20 otherwise retains newly constructed
strings as data, leaving an unevaluated expression in published inventory where
Zabbix deployment requires a native mapping. Runtime credentials and unrelated
literal input remain data; target, ownership and source guards are retained.

The existing writer now compares literal-template paths as well as values. This
ensures a correction to template meaning is published even when its text has not
changed. A real local encrypted-Git regression failed on the old equality-only
writer and passed with the correction, preserving runtime ciphertext and
unrelated literal values. Three additional focused Core 2.20 tests passed for
rendering through YAML serialization/reload and existing importer/guest identity
refusals. The broader baseline suite already had obsolete proxy-type assertions
and synthetic publication fixture failures; a full-suite pass is not claimed.
Normal selected-instance CaC refresh and live monitoring acceptance remain
separate operations; no new wrapper, job, credential type or secret store was
added by this fix.

## Remove the duplicate RHEL action and stabilize navigation — 2026-11-13

Implementation `38a61b5dded16553d21588cb35c04b27130057a8` (source 0.62.4)
removes the later Apply RHEL stop at the owner's request. Certificate and Firewall
already apply during OS preparation; repeating the same action in the base push
adds no useful distinction. The thirteen-stop story retains separate AAP
configuration and AAP content stops, and RHEL state follows the earlier setup.
The canonical Certificate-above-Firewall stack and larger arrow text remain.
This supersedes the RHEL portion of the earlier three-category base sequence.

The owner also removed the bottom object/profile count summary. Its markup,
render assignment and styles are deleted rather than hidden. Navigation lives
in a separate nonshrinking footer with an automatic top margin. Stable grid
tracks and relative button dimensions keep the Next/Complete frame consistent;
narrow layouts give the controls a full footer row. Changing step content and
summary wrapping no longer determine the navigation row's height.

All twenty-three existing walkthrough tests, script syntax and whitespace checks
passed. They cover the removed step, early RHEL state, settings/content sequence,
summary absence and footer/control structure while retaining prior replay and
ordering checks. No browser binary was available, so pixel-position measurements
were not performed; no browser or dependency was installed. No runtime automation
or recovery-export changes are part of this work.

## Allow a bounded wait for longer shared native transactions — 2026-11-13

Implementation `2c3f56800aeceab9ea9a4bf05aa44b934b90dc0c` (source 0.62.2)
allows `aap_isolation_lock_retries` from zero to 1800 with the existing one-second
delay. The default remains five retries. Parallel Windows creation jobs had
exhausted that short wait while another job legitimately held the same native
lock through network preparation and clone creation.

This uses the existing atomic directory lock and keeps its ownership, rollback
and cleanup rules. An invalid retry budget fails before source preparation or
resource changes. No additional registry, wrapper, service, credential or job
template is introduced, and no lock is removed on another invocation's behalf.

An actual Core 2.20 regression first reproduced the default-budget failure while
a synthetic competing transaction held the lock. Four focused native-runtime
tests then passed in 47.761 seconds, covering the longer wait, four invalid
budgets, bounded default contention and successful transient contention with
invocation-owned cleanup. Offline production lint passed for the changed task.
The fixtures use local temporary resources and forced publication failure to
check preservation and cleanup; they do not establish a new parallel deployment
on the real host. Windows consumer selection and its immutable dependency pin
remain a separately coordinated step after active sequential recovery jobs.

## Present the first base push as three distinct categories — 2026-11-13

Implementation `c4822ee6335512a6f2eaf1d4e712c74359f965d4` (source 0.62.0)
splits the initial base push into RHEL configuration, AAP configuration and AAP
content at the owner's request. Each stop highlights its own definitions and
names the matching arrow action; AAP settings appear before shared automation
objects. The existing `#base` link opens completed base content, while the new
`#base-rhel` and `#base-aap` links expose the earlier categories. Seven chapter
positions are derived from fourteen stops so later navigation remains aligned.
These are presentation stops for existing configuration paths, not new runtime
Job Templates or changes to actual AAP deployment automation.

The owner also reported Certificate/Firewall movement around the base transition.
Early preparation and full configuration used different renderer nodes and
styles. All phases now use one canonical configuration stack, Certificate first
and Firewall second, anchored at the top. Obsolete early renderer markup/code
and styles are deleted. Later certificate v2 updates retain firewall v1 and the
same order; reversal and the third-AAP replay use the same rendering path.

All twenty-three existing walkthrough checks passed, including separate category
reveals, exclusive definition highlights, direct links, reverse navigation and
consistent RHEL IDs/order across all stops. Model sanity, script syntax and
whitespace checks passed. Browser-rendered coordinates remain unmeasured.
The original styling, larger arrow descriptions, legend and rejected-preview
removal remain intact; no dependency, runtime job or recovery export was added.

## Withdraw the light comparison and enlarge arrow descriptions — 2026-11-13

Implementation `9428f68c3a1d2d978f86833f6ae672dad2b7bdee` (source 0.61.24)
follows the owner's rejection of the light preview. The publisher is restored
exactly to the original single-site workflow; active preview links and branch
dependencies are removed. The original palette, card borders and story remain.
This supersedes the earlier light-preview design and hosting choice.

The owner also requested larger text for every arrow description, with wrapping
between words. Captions now use 15px-equivalent relative sizing, details 12px,
manual labels 14px and activity text 10px. Normal word wrapping and disabled
hyphenation keep words intact. These are the only changes to the six public
assets; the other five assets are unchanged.

All twenty-three local walkthrough tests, four script syntax checks and whitespace
checks passed. Independent read-only review confirmed the original publisher,
retained protections and absence of current preview dependencies. Pages run
43411778902 succeeded. Six live assets matched the source and twenty-three
deployed interaction checks passed (617.6 ms). The former preview directory,
index and stylesheet each returned HTTP 404. The remote preview branch and its
clean local checkout/branch were then deleted at the owner's explicit request.
Browser-rendered text placement remains unmeasured.

## Document the original shared-width and project-import decision — 2026-11-13

Implementation `31dab22dc9fa821f6b858c321214ec2c45f99da0` (source 0.61.10)
introduced common component columns and gutters for automation objects, AAP
settings and RHEL profiles. It retained the bottom-anchored settings divider,
generated administrator image, complete replay and existing navigation.
The owner also moved Regional servers and Regional automation into Apply
objects with the other project content. The later Git update changes Logging
without importing more automation objects.

The recorded source checks, six-asset publication comparison and twenty-three
deployed interaction checks passed for that revision. They did not establish
rendered browser geometry. The later stretch correction `512a2e5` and the
subsequent proportional-width and alignment decisions remain authoritative for
their later revisions; this entry does not restore the earlier CSS or repeat
its source-only width assertions as browser acceptance.

This fills the missing implementation history returned to the original
AutoDeploy conversation. Fresh public task overviews and the encrypted recovery
snapshot still require their separately reviewed export helper; this
documentation update does not refresh those records or run any deployment.

## Publish both presentation variants through the existing Pages site — 2026-11-13

Implementation `26a34d2395eb8d83b2f5e7ee6363d328dc7d903f` (source 0.61.21)
adds the owner-selected `/light/` preview from `visualization-light` while keeping
the original demo at the site root. Each source checkout is checked separately;
the publisher pins the exact preview revision that passed. Only the six existing
public assets from each version are copied into the artifact.

The existing main-only Pages job, environment, permissions and missing-source
guard remain. Preview refreshes use the existing manual workflow dispatch on
main, so no new repository, hosting service, credential or branch-environment
permission is required. The original demo's six assets are unchanged.

Local workflow validation covered YAML structure, shell syntax, checkout/ref
pinning and the exact asset allowlists. Script syntax and the existing main
walkthrough test command passed. Actual Pages execution and live asset checks
remain the publication acceptance steps, not outcomes implied by local checks.

## Explain origins once below the original AAP — 2026-11-13

Implementation `fc27f4bfc952255f1bae14dddd5ffccaee0c00ae` (source 0.61.19)
replaces repeated Base, From Git, Manual, Captured and In Git badges with one
blue/purple/yellow legend beneath the original middle AAP. This gives the object
names more room while retaining one explicit explanation of base deployment,
Git-defined configuration and manual changes captured back into Git. Badge
markup and styles are deleted; named accessible groups retain origin and whether
manual changes have been saved. The underlying capture and replay states remain.

The owner's subsequent alignment choice supersedes the previous equal-gutter
layout: each stack now starts just inside its own half, with a small relative
left inset and tiny vertical gaps. Automation, AAP settings and RHEL profiles
keep one responsive width. The legend participates in the middle column's layout
rather than covering another panel; narrow layouts include its natural height.

All twenty-three existing walkthrough tests passed, including each story stop's
badge-free names, origin/capture state, accessible descriptions, central legend
placement and the relative left-alignment declarations. Syntax and whitespace
checks passed. Browser-rendered measurements remain unverified. No dependency,
AAP runtime or recovery-export changes are involved.

## Remove redundant deployment navigation — 2026-11-13

Implementation `e65e534eee3e103c45f46c2d7e926ca6ea6d8a6f` (source 0.61.17)
removes the AAP Deployment heading and four stage buttons from the sidebar at
the owner's request. The markup, event handlers, stage-button state rendering
and desktop/mobile styles are deleted. The story keeps all twelve stops and
seven chapters, with Next/Previous, keyboard and direct hash navigation.

The existing deployment test now advances through all four setup stops using
Next and confirms that the separate sidebar controls are absent. All twenty-three
local checks passed (577.7 ms); script syntax and whitespace checks passed.
No dependency, AAP runtime or recovery-export changes are involved.

## Scale component bars with the receiving AAP — 2026-11-13

Implementation `e2fb2425530f64476975d2df5758cbb7885dc568` (source 0.61.15)
uses the supplied Deploy application screenshot as a proportion reference.
The owner rejected both expanding bars into the available half-width and a
fixed-pixel interpretation. The fixed-width draft was replaced before publication.
Each receiving slot now supplies a width reference for three equal proportional
gutters and two equal flexible columns. Object, AAP-setting and RHEL bars share
those columns; RHEL padding compensates its border and margin to retain alignment.
The settings divider stays anchored and the story's object timing is unchanged.

Only coloured-bar text grows by two sizes, expressed in relative font units.
Headings, sidebar and code text keep their existing sizes. Existing native CSS
and the current test runner suffice; no dependency or framework was added.

All twenty-three local checks, script syntax and whitespace checks passed.
No red run was observed for this iteration: the CSS update completed before the
revised tests ran. Pages run 43398234088 succeeded; six deployed assets matched
and twenty-three live interaction checks passed (615.0 ms). Browser-rendered
measurements remain unverified. Recovery/export bookkeeping remains owned by
the original AutoDeploy conversation and was not executed here.

## Stretch receiving panels instead of sizing them around their text — 2026-11-13

Implementation `512a2e51f56c04f5f44c68e9f81c9091427a44ef` (source 0.61.13)
corrects the unequal bar widths demonstrated in the owner's base/project/settings
screenshots. The shared two-column tracks from `31dab22` were insufficient:
the receiving body switched from grid to flex but retained start alignment,
so its catalogue and settings panels shrank around their text. Explicit stretch
alignment fills the available width, keeping the common outer/middle gutter
and object/AAP/RHEL column geometry independent of text and object count.

The focused assertion failed on the old CSS and passed after the correction;
all twenty-three local checks, script syntax and whitespace checks passed.
Pages run 43388731327 succeeded. All six live assets matched the corrected
checkout and twenty-three deployed interaction checks passed (632.4 ms).
Rendered browser measurements remain unverified; the prior source-only checks
must not be described as proof of equal rendered widths.

At the owner's instruction, recovery/export bookkeeping is handed back to the
original AutoDeploy conversation in task `bead-wd-kb27`. This visualization fix
uses a clean isolated checkout and does not touch those unfinished files or run
the snapshot/export helpers.

## Preserve Orchestrator's reviewed build access in the normal selector — 2026-11-12

Implementation `719812a8058a5d05a20877e5f42f33da78efdd45` aligns the existing
selector with the approved receiver-owned Orchestrator EE build. That importer
already saved the required Machine credential, but the selector's older generic
API-only check rejected it before launching the normal job. The Orchestrator
contract may now retain exactly one saved Machine whose ID, name, type and
organization match the independently resolved registered hypervisor credential.
Repository ownership, exact shared token-store identity and duplicate credential
checks remain in force. Other generic imports still reject SSH credentials.

Seventeen actual Core 2.20 tests cover native argument rendering and refusal of
wrong or extra Machines, another project's SSH binding and changed repository
or store associations. The live importer's non-Machine names match the reviewed
selector list. Production lint passes. No alternate launcher, credential type,
job template or API authentication path was added; normal selected-use-case
acceptance remains required after publication.

## Keep configuration results in one private job directory — 2026-11-12

Implementation `6db4be5ce0ec01085aef343b2b79526a8a8a8797` fixes the
organization failure revealed by the encrypted diagnostic. Native async launch
and later polling expanded the default home directory differently, so the poll
could not find a job that had actually started. Base configuration and the
existing project importer now set the CoP async directory to an absolute path
inside their existing private workspace and create it with mode 0700. The
existing cleanup removes it. Standard CoP roles, image user, home settings,
credentials and remote installer result directories remain unchanged.

Three tests in the actual Core 2.20 image reproduce the old missing-result
failure, follow its original completed job, and verify launch, real CoP polling
and cleanup for both corrected production entrypoints. The importer test also
checks that a later capture's null default cannot override this runtime fact.
Focused production lint passes. These checks do not establish a successful
live base deployment; that requires the normal configuration job to pass.

The same implementation completes human-facing Rebuild labels in current
task output, inventory diagnostics and documentation. The owner chose Rebuild
because this procedure supports preparation for a new version, a test
environment and recovery after loss. Technical identifiers, file paths,
stored schema values, unrelated recovery safeguards and historical evidence
are preserved. Live object and encrypted CaC naming were published separately.

## Anchor settings and use a generated sysadmin image — 2026-11-12

Implementation `14cbf02f84635da6623b07c215097322e5df56bd` (source 0.61.8)
anchors the settings category at the bottom of each receiving AAP body. Automatic
space above it keeps the divider from following the growing object count. The
two compact object columns, inset line, RHEL layer and natural whole-card growth
remain; no position-measurement helper or inner scroll pane is added.

The owner explicitly replaced the SVG approach with image generation: simple,
expressive Linux-admin cues and restrained humour. The built-in imagegen output
is saved unchanged as `demo/sysadmin.png`; the old character SVG is deleted.
The 1536 × 1024 RGBA image has actual transparent pixels and retains its original
alpha. Its full prompt and generation method are in the demo guide. The image
appears only during manual changes with the existing accessible caption and
amber flow; publication and live verification now include all six assets.

Twenty-three local interaction checks passed (368.5 ms), along with script syntax
and whitespace checks. Pages run 43309866775 completed successfully. All six
published assets, including the PNG, exactly matched the checkout; twenty-three
deployed interaction checks passed (641.3 ms). The generated image was inspected,
while browser layout and the divider's rendered coordinates remain independently
unverified. No renderer, dependency, runtime AAP job or service was installed.

## Separate platform settings and give the manual operator a clear role — 2026-11-12

Implementation `89496f61d3bb994a85d1319128033e24b31550ea` (source 0.61.7)
puts AAP configuration in its own full-width bottom category in both receiving
AAPs. One thin horizontal rule is inset from the card edges; RHEL remains below.
Inventories/Credentials and Projects/Job Templates form two independent compact
columns above it. This separates platform settings from automation content while
retaining all thirteen objects and the existing no-inner-scroll presentation.

The owner selected an experienced Linux administrator's appearance with the
incident responder's working posture and outage alert. The seated native SVG
uses a plain dropped hood, glasses, clear clothing/chair, hands on the laptop,
one mug and a small amber alert. It appears only for manual changes above the
original AAP; the existing amber path still enters the first receiving AAP.
No external illustration, dependency or new runtime operation was introduced.

Twenty-three local interaction checks passed. One old test assumed identical
source/receiver traversal order; comparing membership while separately asserting
the approved column order corrected that test without changing application
behavior. App/scenario syntax, SVG XML/security and whitespace checks passed.
Pages run 43308022666 completed successfully. All five published assets matched
the checkout and twenty-three deployed interaction checks passed (652.2 ms).
Browser geometry and the rendered illustration remain independently unverified;
no browser/renderer was installed. Concurrent encrypted diagnostics were preserved.

## Use recognisable illustrative object names — 2026-11-12

Implementation `49115f50d90e86d34bab9138b06c5aeb1ee54ad0` (source 0.61.5)
applies the owner-selected VMWare/Satellite inventories, Server access key and
Application auth token credentials, AAP Config-as-Code Git project/jobs,
Application automation playbooks and AAP-prefixed Logging/EDA configuration.
The decrypted YAML preview and inventory-source binding use the same names,
while stable IDs, origin colours and replay behavior remain unchanged. These
are synthetic fixtures; no live AAP objects were renamed.

Pages run 43305022025 completed successfully. All five published assets matched
the checkout and twenty-three deployed interaction checks passed, including
exact names, inventory-source binding and manual-scene sysadmin visibility.
Rendered browser geometry was not independently verified.

## Retain protected organization failure evidence — 2026-11-12

Implementation `f19b9dc2a63860d1e6c425cf94fa6901ed2d2a86` captures a failed initial organization role into
Vault ciphertext using its existing explicit CaC key and native job artifacts.
The role and its secure logging stay unchanged; the rescue stops immediately
and preserves both original async and subsequent cleanup errors. No new job,
credential, token, persistent store or image change is introduced. Actual Core
2.20 tests verify missing-key refusal, absence of plaintext canaries, recovery
of encrypted errors and unchanged successful execution. The underlying failed
organization operation still requires its diagnostic run before selecting a fix.

## Pack complete AAP catalogues and simplify the RHEL layer — 2026-11-12

Implementation `60490df8a3d1a93c17198cbeaf6c542e4ffc810b` (source 0.61.3)
replaces row-synchronised receiving groups with two independent compact columns:
Inventories/Projects on the left, AAP settings/Credentials/Job Templates on the
right. This removes wasted row space and internal receiving-card scrolling while
retaining every automation object and readable 13px names. Shorter layouts let
the whole card grow rather than clipping objects or restoring a nested scroll pane.

The owner's latest directions supersede the earlier monitoring example: remove
Monitoring Agent entirely, rename the TLS profile Certificate config, and keep
exactly Certificate above Firewall on the right of RHEL. Certificate changes
from blue v1 to purple v2; Firewall stays blue v1. RHEL and the three preparation
indicators remain left. The outage sysadmin is seated at a laptop above the
original AAP; the third rectangle still appears only in its preparation/final stops.

The redundant top-right status text, group headings and host-networking captions
are deleted from HTML/presenter code, including the earlier screen-reader-only
copies. Ordinary page accessibility names and intentional scene visibility remain.
Caption cleanup began in `cc324a6fd0762687fa8652bd05ac7c4884533a67`; final 0.61.3
includes that cleanup plus the packing, profile and seated-figure refinements.

Pages run 43302802336 completed successfully. Five published assets matched the
checkout, and all twenty-three deployed interaction checks passed. Static HTML,
model, source links and whitespace were checked; browser geometry remains
unverified under the existing-tools-only choice. Concurrent receiver-EE and SSH
changes were preserved through normal metadata conflict resolution. No runtime
AAP/host operation, dependency installation or visibility workaround was added.


## Resolve receiver SSH options in their original scope — 2026-11-12

Implementation `a28948a38d73f7d0e064e4d039400fb71dcb1d31` fixes the receiver-build connection failure observed
in the base job. Ansible resolves delegated connection options in the managed
host context, while the pinned SSH arguments belong to the original localhost
facts. The task now explicitly reads that original host value. Five actual
Core 2.20 tests preserve the real UID, installation-user and runtime-directory
delegation; restoring the old expression fails the strengthened regression.
The focused production lint also passes. Existing failed job history is retained;
normal base rerun remains the live acceptance check.

## Put infrastructure in RHEL and give manual changes an origin — 2026-11-12

Implementation `beec5ea7e9f002df24afa0c9536a2296aabbee8d` (source 0.61.0)
places the complete Infrastructure configuration group in each RHEL foundation.
The owner delegated the revision choice: nginx/TLS and the previously agreed
monitoring example become purple v2; Firewall remains blue v1. The original
retains its v1 baseline, and the final AAP receives the complete saved snapshot.
The nginx example uses the supported upstream-hostname input with generic
placeholders; revision labels remain illustrative, with no runtime action here.

At the owner's request, an outage-response sysadmin with hands on a laptop
appears above the original AAP only during manual additions. An amber arrow
shows direct input to the receiving AAP. The entire third-AAP rectangle stays
hidden until a brief preparation stop, followed by the final deployment.
Twelve stops, reverse/restart, keyboard/chapter navigation and origin colours
remain consistent. No external asset, dependency or new runtime job was added.

The preceding correction `2dd1495a3b09bc300659c7380404e4643e4af007` made the
major borders dark 3px and delivered firewall/nginx bars into RHEL. Its Pages
publication and twenty deployed checks passed. The integrated 0.61.0 publication
completed in Pages run 43297643513; all five assets matched and all twenty-three
deployed interaction checks passed. Concurrent receiver-EE changes were preserved
through a normal rebase. Rendered browser layout remains unverified under the
owner's existing-tools-only choice.


## Build the receiver-owned shared execution environment — 2026-11-12

Implementation `c711505dabd5937dc0d051eb183a8c0901023c42` adds the
approved native Ansible build playbook. Each receiver builds the pinned
Red Hat Core 2.20 base with Kubernetes and JSON patch from Red Hat Trusted
Libraries and publishes into its own Hub. Private registry authentication,
versioned-tag reuse, offline dependency checks and uncached blob verification
address the earlier damaged-publication failure and remove Source-Hub dependence.
Base setup builds before default configuration; Orchestrator CaC imports run
the same builder before importing their reviewed EE definitions. Native project
requirements continue to provide certified collections.

Implementation `5d3ac74606f0b9777340d6353a236ddca67e1413` changes the current
name to `ee-proj-aap-cac` at the owner's request. The repository and native AAP
EE name stay stable; `2.0.0` remains the image tag. The earlier `-v2` publication
is historical. Source native startup passed before the name change; the stable
publication independently passed all byte and runtime checks afterward. Receiving
AAP base configuration and application acceptance remain separate outcomes.

The owner approved RHEL Skopeo as an explicit OS prerequisite. Current-receiver
Hub timeout reconciliation succeeded; an order-sensitive environment-list
postcheck was corrected by independent mapping and multiset comparison, without
retrying the successful service action. CoP review terminology was clarified:
custom code alone is not a demonstrated departure from a CoP recommendation.

## Show the RHEL foundation and strengthen the diagram — 2026-11-12

Implementation `a6fa859f5526d30ee9c1f1a122451176260e4da4` (source 0.60.0)
adds a slim RHEL foundation below each receiving AAP. The owner requested visible
VM/OS preparation without expanding the story. Source inspection distinguishes
the golden-image VM clone, host firewall/nginx/TLS setup, and guest prerequisites
before AAP installation; a full OS upgrade is not implemented or claimed.
The foundation persists under later configuration changes and appears completed
on the final rebuilt AAP, while reverse/restart navigation removes future state.

The owner also requested stronger boundaries and more breathing room: major
borders are 2px, Git code is 14px with 17px repository headings, and the matching
code/receiving rows are centred at 95 percent of the available canvas height.
The continuous two-column AAP body remains; no separate lower scroll pane returns.
Nineteen local and deployed interaction checks passed, and all five Pages assets
matched the checkout. Pages workflow 43292899539 completed successfully. These
existing-tool checks do not verify rendered browser layout; no browser or runtime
AAP/host action was added. Concurrent EE/runtime updates were preserved.


## Activate the verified EE-v1 default and preserve runtime boundaries — 2026-11-12

Implementation `7e5d2e6e55f926d58701754b930b7bd6d4fa2854` records the
successful native Source AAP job using the repaired publication: Core 2.20.10,
99.483 seconds and no failed or unreachable hosts. The candidate retained its
native registry credential and immutable manifest pin; temporary observer
verbosity and target selection were restored after completion.

The owner requested this derived image as the shared default. Source AAP's
global default, all 62 managed templates and the Hactar project default now use
EE-v1. The original official EE, upstream registry credential and historical
jobs remain available. Maintained encrypted CaC mirrors the new portable names,
immutable image and native base-owned private Hub pull credential, with
unrelated values, YAML tags, allocation history and application-owned names
preserved. The current Command Center capture has one template; the update
preserves that current shape and its deferred installation.

The failed initial Hub manifest was retired through the supported scoped
remove-image action only after replacement acceptance. Native task completion
and exact repository-content preservation were verified; no physical artifact
or global orphan cleanup was performed. DNS checks continue to use native tools
without dnspython or the retired delegation workaround. Fresh receiver registry
access is still a separate network-policy decision, so Source acceptance does
not claim complete receiver configuration or application acceptance.

## Require uncached remote EE verification — 2026-11-12

Implementation `5c8f46a` corrects an overstatement in the initial EE-v1
publication checkpoint. A local pull could reuse cached layers; native AAP then
rejected the published image because Hub's stored compressed base layer was
truncated. The retained failure establishes why push success and matching local
image IDs do not prove registry integrity.

The replacement publication uses native gzip level 1 compression and normal
Skopeo upload under a new tag, preserving the exact image configuration and all
uncompressed layers. This avoids the damaged encoded blob without changing Hub
policy, disabling checks or directly editing registry storage. An uncached
download verified the replacement manifest, configuration, all layer lengths
and compressed/decompressed hashes. Native AAP execution and receiver access
remain distinct acceptance gates. The building and publishing instructions now
include the fresh transport and protected authentication workflow.

## Use the available height and one continuous AAP body — 2026-11-12

Implementation `6c33f0f4f16529920327077ba23b3353408f0af6` follows the owner's
browser feedback that a fixed configuration strip left only the lower object
list scrolling. The owner chose to try height first, retain two internal columns
and defer the proposed three-column interior.

The desktop code/receiving rows now use the full available viewport height,
removing the 860px maximum. Each AAP has one focusable content area containing
plain configuration and object groups; toolbar bands, boxed configuration
strips and independent lower-list scrolling are removed. Compact bars preserve
13px names. Short viewports may still scroll the complete content area without
truncating definitions. Source-centred connector offsets preserve routing as
height changes; early VM/install stages hide the empty content wrapper.

The existing seventeen story/navigation checks passed locally and against the
live assets. Pages run `43259012043` completed successfully at 16:28:51 UTC; all
five HTTPS assets matched source. Static structure, 62 retained IDs, sole content
scroll ownership, two-column receiving flow, staged hiding, declared height/route
fit and whitespace checks passed. No state-model, runtime or host change was
made. Actual rendered-browser acceptance remains unverified here; the height-first
choice does not authorize adopting the deferred three-column interior.

## Align receiving AAPs with code and replay the saved configuration — 2026-11-12

Implementation `a56c0c57dd93a9c4e603268e7dbe0f1844e38c85` follows the owner's
requested composition: equal-width Git and receiving columns with matching rows,
first destination aligned with the upper code window, original AAP centred and
a later destination below. Code windows get more space. All installed cards
share a readable AAP identity; their dimensions are illustrative. The sidebar
uses stronger current/completed states, a persistent current-step heading and
active chapter following.

Seven chapters now contain eleven stops. The last stop creates another AAP from
the complete saved Git definitions, retaining the first destination and the
blue/violet/amber origins. Captured manual-origin definitions are labelled
Captured and In Git on the replayed platform. Future content is hidden until the
last stop, and reverse navigation/reset removes it.

The owner also requested a separate infrastructure-configuration job category,
then confirmed that Monitoring Agent Config changes from v1 to v2 while Firewall
Config stays v1. These are illustrative saved Job Template inputs, imported by
the existing native configuration role; no host monitoring/firewall operation is
executed. Logging v2 and EDA v1 are retained across the complete replay. Existing
source citations and protected-secret limitations remain explicit.

Seventeen named interaction checks passed locally and against the downloaded
live assets. Pages run `43255522355` completed successfully at 16:09:41 UTC; all
five HTTPS assets matched source. Syntax, static HTML/CSS structure, equal-track
fit, hiding, palette and whitespace checks passed. A local patch guard and one
test ordering assumption were corrected in their own scope, without an app
workaround or uncertain-operation retry. Actual browser rendering remains
unverified under the existing-tools-only choice.

Concurrent EE-v1 source and documentation updates were preserved; the visual
feature advanced to 0.59.0 after main had reached 0.58.1. No runtime AAP automation
or environment settings were changed by this work.

## Show platform configuration changing alongside automation content — 2026-11-12

Implementation `c6ed2b04610a67e143025adb2f805bebc1e6f74d` adds separate AAP
configuration panels at the owner's request. Stage 04 creates blue Logging
Config v1 and EDA Config v1. A later Git change replaces the stable logging
entry with violet v2 while EDA v1 and the original AAP's own configuration stay
unchanged. Navigation restores the corresponding revision without duplicates.

The YAML uses a real Controller logging queue setting with synthetic 10000 and
20000 values. Settings follow the existing Stage 04 shared-configuration path;
project imports remain separate in the code preview. EDA Config is an illustrative
bundle of supported decision-environment/rulebook-activation definitions, not a
new global-settings API. No runtime AAP change is made by this visualization.

Fourteen named local and downloaded-live-asset interaction checks passed. Pages
run `43239629244` completed successfully at 14:40:54 UTC and all five HTTPS assets
matched source. Source tracing, independent bounded review, syntax, static HTML
and whitespace checks passed. Browser-rendered layout remains unverified under
the existing-tools-only decision.

## Give Git code more room and match active flow colours — 2026-11-12

Implementation `875473e8867a9b568830a399d865107fdf53e871` makes the repository
column about 50 percent wider on a wide desktop and the source AAP narrower
and shorter. It links arrow strokes, markers and action labels to the focused
YAML/playbook origin: blue for deployment/base, violet for Git additions and
amber for captured manual definitions. An interaction regression checks matching
origins and navigation reset. Implementation
`7d66e99d9fcf235aa02cd391d6a383d2a3708901` then changes the small repository-type
labels to larger, dark Private Git Repository and Public Git Repository headings.
Both publications passed exact live asset parity and thirteen interaction checks.

## Put the operational story beside a three-column diagram — 2026-11-12

Implementation `e0a6d034b1104cd34373028db0ac82208f9f7234` follows the owner's
explicit layout choice after the previous width-only correction was rejected.
Navigation, deployment stages, progress and status live in a left sidebar, as in
the Windows/AIOps references. Compact private/public repositories sit beside the
original AAP and new AAP, with matching instance cards and no large hero or
explanatory scene header. A visual mockup was shown before implementation.
Stage 02 now reads Prepare OS for AAP installation. Active routes have strong
blue direction, brief travelling markers, ordinary HTML labels and a persistent
static cue; reduced-motion preferences remove animation without hiding activity.

The two-instance story, true VM/AAP/base visibility, labelled object origins and
manual definitions returning to encrypted CaC remain intact. A dependency-free
Node command checks the actual five HTTPS assets, requires checkout byte parity
before executing downloaded JavaScript, runs the same interactions and cleans
only its own temporary directory. It performs no live AAP operation.

All twelve integrated checks passed. Pages run `43234094803` completed successfully
at 14:08:50 UTC; the live runner then verified five exact assets and all twelve
interactions. Syntax, static structure and whitespace checks passed. Rendered
browser/phone layout remains unverified under the owner's existing-tools-only
choice; the generated design mockup is not rendered application evidence.

## Use desktop space and distinguish object origins — 2026-11-12

Implementation `18b5b2c044228aebf3d7e963c19adb74f1de2b3e` follows the owner's
browser screenshot and feedback: the capped central canvas left excessive empty
space, stacked panels were too tall and origin colours were too pale. The
visualization now uses fluid desktop width, bounded panels with two-column
scrollable object groups, larger code/object text and stronger labelled blue,
violet and amber fills and borders. Scrollable regions are keyboard focusable.
The story and smaller-screen layout remained intact. The owner subsequently
rejected the rendered composition: width and colour corrections did not solve
the stacked diagram. The next approved revision uses three columns and a left
sidebar, following a visual mockup shown before implementation.

All ten interaction checks, syntax, focused CSS assertions and whitespace passed.
Independent source review found no blocking cascade, overflow or story regression.
The Pages run completed successfully, and all five public HTTPS assets matched
source. This establishes publication and tested interactions; rendered-browser
layout remains separately unverified under the existing-tools-only decision.

## Separate private configuration from public execution in the two-AAP story — 2026-11-12

Implementation `9bb4b12cac43acb0b7d785f4f1e9096eb9e71fe1` rebuilt the withdrawn
visualization around the owner's selected narrative: original AAP, two separate
repositories, four deployment stages, base objects, project additions, Git
changes and manual objects returning to encrypted CaC. Only two AAP instances
are shown. Trigger choices and detailed scan/review mechanics are deliberately
abstracted from the main flow, as requested. The YAML preview is marked encrypted
and illustrative; execution excerpts link to the real implementation. Captured
manual objects keep their origin and gain an In Git badge.

Ten interaction/source checks passed and initial Pages publication plus live
asset parity were verified. No live AAP operations or browser installation were
performed. At initial publication the deployed-source interaction runner remained pending;
its original native write later completed, and normal plus copied-asset fixture
runs passed. The next layout revision integrates that runner with byte parity
before downloaded code is executed. Browser rendering remains outside that check.

## Publish verified identity before normal recovery — 2026-11-12

Hactar implementation `e629966` and private configuration implementation
`c2f5348` publish the new provider-backed SSH trust and machine identity after
strict authenticated Rocky 9 and unchanged physical-hardware checks. Existing
deployment source pins select that Hactar implementation; unrelated configuration
and advancing allocation history are preserved. Normal recovery preflight passed
using the official Core 2.20 EE. This checkpoint records actual identity readiness
and source consumption, not conversion or complete fresh AAP acceptance.

## Verify native EE authentication before physical recovery — 2026-11-12

Implementation `e58acc6` passed the existing managed preflight with native
registry authentication and a temporary forced pull; the intended `missing`
policy was restored and independently read back. The final normal CaC preview
completed with zero validation errors, conflicts or desired changes. Its
initialization flag remains true: this proves the preview checks, not an
initialized capture baseline or completed fresh deployment.

The public base example now shows commented organization, built-in registry
credential and EE-reference placeholders. Real values remain in encrypted base
CaC. The existing guarded provider installation acknowledged exactly one reset;
fresh provider identity and authenticated OS/hardware checks remain separate
from that acknowledgement.

## Let Controller authenticate image pulls before job startup — 2026-11-12

Implementation `e58acc6` removes the manual Stage 05 image-copy operations.
An EE must already exist before its playbook can execute, so an in-play download
cannot bootstrap that job's runtime. Base CaC now declares a built-in Container
Registry credential, created before the EE by the existing dispatcher, and links
that credential by name. Controller/Runner performs the authenticated pull.

The image remains the unmodified official Core 2.20 stream. Authenticated
manifest access and native credential/EE readback passed. The five existing PAH
admission cases still pass; collection preparation remains unchanged. Actual
fresh-target pulling and runtime remain part of normal deployment acceptance.

## Omit completed handoffs from the overview — 2026-11-12

Implementation `e9d19a4` excludes the transferred visualization and performance
workstreams from the public overview at the owner request. Their completed Beads
records and full encrypted recovery history remain available; subsequent work
belongs to the receiving chats. Nine existing task-mirror checks passed, and the
generated overview omits both transferred task families without narrowing the
protected export. Concurrent visualization removal commits remain preserved.

## Withdraw the visualization and retain its publishing workflow — 2026-11-12

Implementation `30e35f8554581b4e9ba367432046aec421d60910` removes the previous
visualization application, its tests and its current README links at the owner's
request. The owner wants a new design from scratch and explicitly retained the
GitHub Pages workflow. A checkout-time source-presence check skips JavaScript
checks and publication while the visualization source is absent. Existing
publishing triggers, permissions and asset allowlist are preserved.

The old Pages site was separately unpublished because deleting repository files
does not withdraw the previously deployed artifact. The authenticated Pages API
and the public URL both returned 404. The removal commit's GitHub Actions run
completed successfully: the source-presence check passed and publication was
skipped. Local checks exercised both guard branches, existing version-policy
tests and whitespace; an independent scoped review found no blocking issue.
AAP runtime source and deployment were outside this change. Earlier release and
decision records remain historical evidence. AIOps source informs a proposed
replacement outline; no replacement design or application has been implemented.

## Accept the normal firewall access repair before continuing installation — 2026-11-12

Implementations `ae03bb3` and `8e400c0`, documented at `35021e9`, passed the normal
tagged repair through the complete certified role and existing publisher. An
independent machine-pinned read confirmed the exact runtime and permanent rule,
the complete desired native policy and removal of the temporary lock. All three
encrypted capture transformations matched the expected addition; the allocation
ciphertext and saved primary VM remained unchanged. Source policy and placement
needed no remaining synchronization operations. Failed earlier runs remain
historical failures. Continue the existing guest through normal infrastructure,
installation and full base configuration; do not repeat VM creation.

## Preserve the target interpreter after clearing role delegation — 2026-11-12

Implementation `8e400c0` completes the connection context for the firewall role.
The first live nondelegated retry failed during the vendor role's fact task,
before package selection. Source inventory has no explicit localhost entry;
Ansible's implicit localhost supplies the execution container's Python path.
That path must not be inherited by an SSH task on the hypervisor.

Both role calls now use the selected hypervisor's existing interpreter override
or normal remote discovery. No new interpreter path, package backend, credential,
vendor patch or execution environment is introduced. The regression reproduces
the omitted controller-only Python input and passes with the corrected setting.
The actual vendor fact task also passed a machine-pinned read-only SSH check;
the old context failed. Source retry `3610` remains failed and its exact raw
message remains censored. Syntax, focused production lint and whitespace pass;
the next normal tagged retry must separately prove live acceptance.

## Keep direct SSH while avoiding the unsafe delegated package lookup — 2026-11-12

Implementation `ae03bb3` clears inherited delegation only inside the certified
firewall role's apply and rollback calls. The surrounding transaction still
supplies the verified hypervisor's SSH address, user, port and strict server-key
settings. No protected value is unwrapped, package backend forced, vendor role
patched or execution environment changed.

The previous inventory loop passed a simplified fixture but failed live. The
expanded regression covers both plain JSON and unsafe YAML inventory names,
the protected route/rule inputs and the actual transaction connection variables.
It exercises Ansible's real package action, verifies the same SSH destination
and DNF selection for both calls, and reproduces the original failure as a
negative control. All three focused Ansible regressions passed on resumption;
scoped syntax and production lint had also passed for the same runtime change.

The observed engine is `ansible-core 2.16.19`. Maintainer-verified
[upstream issue #82598](https://github.com/ansible/ansible/issues/82598)
documents the protected delegation/template failure. Upstream 2.17.0 uses direct
fact lookup; 2.16.20 still contains the old expression. An engine upgrade remains
a separate change. Live access repair and the remaining installation stages
must be verified independently; passing local tests is not deployment acceptance.

## Preserve protected values while selecting a trusted delegation name — 2026-11-11

Implementation `d98c8f2` addresses the actual package failure. The privately
retrieved message showed Ansible trying to load a literal internal hostvars
lookup as a module name. On the same Ansible 2.16.19, interpolating an unsafe
delegation value marks that internal expression unsafe, so it remains unrendered.
Adding facts or changing package backends would not address that mechanism.

Both certified firewall role calls now select the trusted name from the existing
inventory loop and apply the pinned-host match as a separate condition. A custom
loop variable avoids conflicts with the role's own item loops. Vault/unsafe
values, native target checks, package selection and access permissions are
preserved. A real Ansible/PackageAction regression covers apply and rollback,
asserts unsafe candidates stay protected and selects only the verified host.
Its negative control reproduces the exact old literal-expression failure.
The two existing connection/tagged-repair fixtures also pass, plus scoped syntax,
production lint and whitespace checks.

The one-time protected capture code is removed. Its root-private temporary host
file was retrieved through pinned SSH and deleted after an exact hash check.
The private local proof remains outside Git. Live access acceptance remains a
separate outcome; earlier failed jobs retain their failed status.

## Retrieve the original package error privately — 2026-11-11

Implementation `73e9327` permits the existing tagged access repair to save only
its original package error message in a root-owned temporary 0600 log. The job
prints only the generated path, and the operator retrieves it through the same
pinned SSH route before removing that exact file. It is a temporary diagnostic,
not desired configuration, ownership metadata or a new state store. No new
plugin, credential, service or Job Template is introduced.

The previous live flags showed DNF and Ansible 2.16.19 but matched none of the
three expected error branches, so another backend change would be a guess.
The original failure is retained privately before diagnostic/rollback tasks can
replace it. Actual Ansible fixture runs verify ordinary runs create no log,
tagged repair preserves the message with private mode, and the raw canary stays
out of job output; the test file is removed. Scoped syntax, production lint and
whitespace checks pass. Actual error retrieval and repair remain live work.

## Distinguish exact package auto-detection branches — 2026-11-11

Implementation `5677bec` narrows the fixed Boolean diagnostic to three distinct
Ansible error branches: general package-manager detection, DNF major-version
detection, and missing DNF module. It also reports safe DNF/DNF5 fact matches and
the running Ansible version. The prior broad backend flag was insufficient to
choose a fix; explicit delegated fact ownership alone did not resolve the live
failure. Source execution-environment metadata identifies a cached supported
image by a mutable tag, so local Ansible source cannot prove its runtime version.

Three actual-template cases cover string and sequence error messages, Boolean
output and secret-canary suppression. Sequence-safe matching avoids confusing
list membership with substring matching. Scoped syntax, production lint and
whitespace checks pass. This adds diagnosis only, without changing packages,
backend selection, the execution environment, credentials or access controls.

## Reveal AAP only when its deployment creates it — 2026-11-11

Implementation `321d9e4` follows the owner's correction: the selected receiving
AAP must not appear before deployment. Overview, destination and input steps
now show the existing source AAP and prepared host. The RHEL VM appears during
Stage 01, DNS/TLS during Stage 02, installed AAP inside that VM during Stage 03,
and the configured API diagram in Stage 04. Existing future objects and routes
use real hidden/accessibility states, including initial HTML; changing only
their tint would still suggest they already existed.

Backwards navigation, restart and direct links reverse those states consistently.
Nine Node checks, both script syntax checks, SVG structure and whitespace checks
pass. The existing blue palette, twelve-step code-grounded story and pinned
citations remain. The owner selected existing checks only, so no browser was
installed and no browser layout or screenshot acceptance is claimed. Pages
publication and live asset verification are separate from source validation.

## Keep delegated package facts on the existing hypervisor identity — 2026-11-11

Implementation `4348af4` resolves the pinned address to exactly one existing
inventory host, then delegates the existing transaction and package-manager
fact gathering to that identity. The certified firewall role keeps normal
backend selection. There is no new inventory record, forced interpreter or
package backend, credential change, or weakened target/security check.

The live diagnostic identified the package auto-detection boundary; it did not
prove a repository or credential problem. A read-only target reproduction
confirmed DNF and an already installed package. Delegating facts to a raw address
outside inventory failed the fact-ownership assertion; using the existing source
inventory name passed it and the package check without installing anything.
Both native Ansible connection fixtures pass with actual delegated fact caching,
covering management and first-empty tagged repair under both Jinja modes.
Scoped syntax, production lint and whitespace checks pass. Live repair acceptance
remains a separately observed result.

## Classify hidden access failures before rollback — 2026-11-11

Implementation `9d18ed6c59c1778597fab52a822d27feeaf3d5ee` adds fixed Boolean failure categories at the start of
the existing rescue. A live repair passed the first-empty policy planning and
resource checks, then failed inside the certified firewall role's package task.
Its rollback package task also failed. Protected logging intentionally withheld
the raw module error. Independent host checks verified installed firewalld and
Python support, unchanged native policy, absent selected rich rule and released
lock; they did not establish the package failure's cause.

The diagnostic reads the original failure privately before rollback can replace
it. It reports only fixed backend, Python, repository, privilege and transport
flags, keeping unknown results unknown. Four actual-template canary checks
confirmed Boolean-only output without raw error content; scoped syntax and
production lint passed. No backend override, new package or security workaround
is introduced. Actual repair success requires its separately observed outcome.

## Finish first-guest installation access without reallocating — 2026-11-11

Implementation `75b191d` fixes a fresh-host policy mismatch after VM creation
had already succeeded and published verified primary ownership. The empty
base policy omitted explicit production exclusions, while the native Hactar
template already enforced the independently configured source address. The
installation planner now materializes that existing protection for its desired
grant. It keeps the exact original publication baseline and permits lagging
source aliases only through the same independently validated transition.
Native resource verification receives the equivalent explicit baseline; its
production, guest ownership and management guards remain strict.

The existing tagged Stage 04 repair finishes only installation access and exits
before base configuration. The operator then continues ordinary infrastructure,
installer and full base stages on the consumed VM. No new template, wrapper,
store or allocation is needed. Fourteen installation and ten management tests
pass, including real encrypted Git/API publication with interrupted source
registration, retry and idempotence, plus tagged execution under both Jinja
modes. Scoped syntax, production lint and whitespace checks pass. Protected
offline checks of the actual reservation and three captures pass; the empty
and materialized baselines render identical native firewall bytes. These checks
do not establish successful live access repair or completed AAP installation.

## Show deployment stages in blue and make recommendations actionable — 2026-11-11

Implementation `847f498382743e7d26d10ab485760f877a0ea2f1` follows the owner's
visual revision: blue/slate colors replace green/teal, and the twelve-step story
includes first-class VM creation, infrastructure, AAP installation and Base AAP
configuration. A separate deployment diagram shows the receiving AAP inside its
fresh guest on the already prepared pinned test host. Stage 04 returns to the
API-configuration view. Existing project import/capture behavior remains grounded
in the pinned code; the later AIOps trigger is still a separate unimplemented
follow-up. Eight focused interaction/source/palette checks, syntax, SVG/assets
and privacy checks passed. Pages run 43027938116 succeeded and the live page plus
four assets match source bytes. The owner’s existing-tools choice still excludes
a browser installation and layout/screenshot acceptance.

The short speed report now names fourteen actions, each with a concrete step
and completion criterion. The appendix maps all thirty ranked episodes and
eighteen repeated/additional findings to those actions, and accounts for all
sixty-four earlier blocks. Forty-nine eligible observed intervals were sorted;
the pre-v16 extractor is outside the window, while the concrete firewall span
is ranked instead of its broader overlapping acceptance envelope. Root checks
verified complete mappings, row counts, links and public-safe content. This
report revision implements no runtime optimization and claims no measured
savings, new authority or universal adoption of the proposed practices.

## Schedule AIOps-owned runtime setup after v18 acceptance — 2026-11-11

The owner explicitly assigned monitoring-server and demonstration-guest
installation/setup to the AIOps project, with setup triggered when that project’s
CaC is deployed to the selected AAP. The main TRA toolkit remains in the base.
Implementation is conditional on successful v18 acceptance and tracked by
`bead-wd-72f.31.2.6`; no runtime changes follow from recording this decision.
The existing visualization remains pinned to the currently implemented code.

## Explain the implemented CaC flow and development delays — 2026-11-11

Implementation `baa562d69f1c69d7f91af2c6df42b9df8b41ce4a` adds a guided,
buildless visualization and the two requested development-speed reports.
The visualization follows the code at e371c76 / runtime 0.50.13 rather than a
proposed architecture: explicit destinations, shared base, common project
imports and scoped reviewed Controller capture. Physical installation is outside
the story; VM creation is brief context. Examples are generic and no AAP
connection is made. GitHub Pages publishes only allowlisted presentation assets.
Six interaction/source checks, syntax, links and privacy checks passed. Actions
run 43025270437 succeeded; the live HTTPS page and four assets match committed
bytes, with tests and README excluded. The owner chose existing checks, so no
browser was installed and layout/screenshots were not verified.

The short recommendations link to a separate detailed top-30 review, frozen at
11 November 2026 12:41:05 UTC from the actual v16 VM start. Measurements separate
calendar spans, job runtime and repeated reads; overlapping episodes are not
summed. Continuation failures, unnecessary prerequisites, timeout budgeting and
producer/consumer gaps are concrete findings. Required guards and recovery
records remain necessary; counts alone do not prove waste or savings. No runtime
performance settings or test policy were changed by this documentation work.

Host recovery separately passed RHEL update, setup, managed access, reboot and
all 17 post-reboot checks plus the firmware assertion. Original timed-out jobs
remain failed; the actual successful continuation is retained in encrypted task
records. Image staging and fresh AAP allocation remain separate operations.

## Keep Command Center outside the base installation — 2026-11-11

Documentation checkpoint `8e742ddf39201365d53d07173fb0d86ea3ecf7e1` records the owner's explicit boundary:
CCNG remains a separate AAP project with its own installer Job Template, and its
installation and tests are deferred. Base stages01–04 and physical-host recovery
do not depend on CCNG acceptance. The optional CaC import declares its separate
objects without launching application installation. Prepared infrastructure and
application drafts, existing settings and unresolved inputs remain preserved.

Beads deployment, infrastructure and fresh-tracker acceptance records are now
deferred. The combined DNS/nginx task retains its separate unfinished MCP scope.
No application, DNS, proxy, credential or production change follows from this
decision. The existing task overview and encrypted recovery export were refreshed
and verified against Beads; whitespace checks pass.

## Refresh the physical recovery checkpoint — 2026-11-11

Documentation checkpoint `4838766446b12621792b4639fa0231a5dda68111` refreshes the generated task overview and
README after verified retirement, reinstall and firmware preflight. Detailed
records and comments remain in the separate encrypted Hactar recovery export.
The original timed-out conversion job and workflow retain their failed states,
while the later remote conversion success is recorded separately. Remaining
host setup requires the explicit host-settings decision that the workflow never
reached; fresh AAP allocation remains 18 and has not started. The owner deferred
Vault-key rotation. No guest, provider, credential or runtime change is made by
this documentation checkpoint. Both task-mirror checks and whitespace checks pass.

## Clarify the final access-retirement task name — 2026-11-10

Implementation `63b39be7d2ab85a049ee5e1a7e85fd83a407f6e6` (0.50.12) corrects an obsolete display name
that said allocation history was retained in current state. The task now states
that completed selected reservations are removed after source and encrypted
access retirement. The playbook differs only in that name: arguments,
conditions, ordering and behavior are unchanged. README and the decommission
guide already describe final reservation removal and were retained.

The existing normal selected-instance teardown and final publisher succeeded on
`73418cae722657805565fc465c7c9730bd60f0e6` (0.50.11). That runtime result
belongs to that revision; this wording update was not rerun live. The existing
teardown syntax check, exact label-only byte comparison and whitespace check
passed. No new tests, source-policy changes, live operations or repeated
retirement were needed for the display correction.

## Remove completed instance reservations from current CaC — 2026-11-10

Implementation `7d2114279cc4dcb8f4b638a05b8c36e815454a59` (0.50.10) follows the owner's requirement to
remove retired namespaces from current allocation/CaC records while preserving
the monotonic next-number counter, shared configuration and surviving instances.
The previous final publisher deliberately retained a decommissioned reservation
because intermediate source ownership checks still needed it. Deleting that row
earlier would break safe cleanup and retry, so the existing transaction ordering
is retained through successful source/API synchronization.

At the existing stable-success endpoint, the same action now reads fresh remote
allocation state, requires the exact selected decommissioned row and a valid
non-regressed counter, and removes only that row. It preserves all other data,
Vault identity and literal tags, commits from the current remote head, pushes
without force and independently rereads the published result. Early Git retries
also preserve the highest observed counter floor. Contention uses the existing
bounded synchronization retry; changed ownership or a regressed counter stops.
An advance immediately after final removal stops success reporting for review.
The completed namespace is then absent and no longer selectable; Git history
retains past records without a current tombstone or new recovery mechanism.

All 68 affected instance-access, allocation, supplemental-interface and guest
retirement checks passed. Real encrypted local-Git fixtures verify interrupted
source cleanup retains ownership, selected URL/record mismatch refuses pruning,
early and final counter regressions stop, exhausted nonforce push contention
retains the row, and a concurrent surviving row/counter advance is preserved.
The existing teardown syntax check, Python compilation, whitespace and offline
strict production lint across thirteen encountered files passed. Independent
focused review found the early-retry counter-floor gap; it was fixed and the
new conflict regression and follow-up review passed. No other substantive finding
was reported. This is scoped source verification, not a formal full review or
live retirement acceptance. No live job, private CaC or source API was changed
by this publication.

## Validate the monitoring clone's existing native DHCP allocation — 2026-11-10

Implementation `c084ce90dd4959e2e4d5f655404f8ccd935ff899` (0.50.8) fixes an
address-proof mismatch. The maintained clone producer obtains its address from
native libvirt DHCP leases for the verified VM MAC; it does not create a static
reservation. The previous validator required a static reservation regardless of
that allocation method. This is a correction to verification of existing
ownership, not an address adoption or network configuration change.

Keep exact unique static DHCP ownership as sufficient proof, including for a
stopped guest. Only when neither the saved MAC nor address has a static owner,
read the full native network lease table and require one unique same-row MAC/IP
pair with future expiry. Duplicate or crossed ownership and failed/malformed,
missing or expired lease data fail closed. DNS host entries are excluded from
DHCP counts. Native reads use the existing protected Ansible command path with
`LC_ALL=C` and `TZ=UTC`; no helper, mode, store, credential or recovery path was
added. All existing UUID, disk, interface, MAC, network, bridge, hypervisor and
production guards remain required. Safe failure context uses `address_matches`
because address proof can be static or DHCP.

Nine affected native-policy tests pass, including sixteen concrete address-proof
cases, verbose privacy and full composition for two dynamic monitoring owners.
Scoped strict production lint across fourteen encountered files, syntax and
whitespace checks pass; independent source review found no significant defect.
Finite native expiry timestamps and correct clocks are the supported demo
assumptions. A stopped dynamic guest still requires its current lease; expiration
stops cleanup without rewriting saved ownership. Live preview and final cleanup
acceptance remain the parent task's responsibility and are not claimed here.

## Report only safe native identity check outcomes — 2026-11-09

Implementation `03e09d72505468181e2bf0fb228774cdcfd545a1` (0.50.6) makes
the existing application identity assertion explain which comparison failed.
It still requires the same UUID, bridge and static-reservation checks together.
Only the generic `uuid_matches`, `bridge_matches` and
`static_reservation_matches` boolean outcomes are visible. The native command
reads and every other protected task remain hidden; the change adds no flag,
loader, diagnostic job, ownership exception or repair behavior.

Seven directly affected native-policy tests pass. The actual native Ansible
verbose-output regression exercises each mismatch and all-match success with
unsafe stdout and confirms UUID, IP, MAC, key and token canaries never appear.
Scoped strict production lint and whitespace checks pass. Independent security
review repeated the native fixture and checked bounded malformed/missing input
cases without sensitive output. These source checks do not establish the cause
of the live VM mismatch or authorize acceptance of changed ownership; live
diagnosis and final cleanup acceptance remain pending.

## Select private configuration branches without eager whole-file evaluation — 2026-11-09

Implementation `859b6ccd7835a0ef3e69da0fab668d139c9ff689` (0.50.4) corrects
the existing native permission preparation loader. The central bootstrap's reader
and Vault values were valid, but selecting them through a whole-file namespace
first evaluated unrelated `pah_base` references. The same behavior affected the
AIOps capture through unrelated `aiops_eda_organization_name` references. These
were variable-loading failures, not missing credentials or invalid ownership.

Both files now follow the existing global native `include_vars` pattern. YAML
selects the needed credential, metadata and instance branches directly; the
existing ownership actions consume the AIOps loader's raw registered facts
without templating unrelated application configuration. No loader, helper,
repository read, credential, fallback or persisted store was added. Existing
Vault/literal tags, protected stdin, cleanup, TLS and all guards remain intact.
Accepted private-source checks found no overlapping existing/protected variable
names, preserved the route/pin/source prerequisites, and passed all fourteen
credential and project-metadata guards plus instance iteration in memory.

All seventy-five directly affected tests pass, including native reproductions of
both former failures, literal credentials, an unused nested Vault value without
its key, complete policy loading and real encrypted partial-cleanup retry.
Scoped strict production lint passed across fourteen encountered files, syntax
and whitespace checks passed, and an independent agent reviewed the combined
change without significant findings. These are local checks; the parent retains
the normal live check-mode retry and final end-to-end acceptance.

## Retire related test VMs from their durable application CaC — 2026-11-09

Implementation `c56ac82a848f11e67be57026325f3ba3c1533cfc` (0.50.2) fixes
external-controller cleanup when a successor's VM inventory exists only on the
successor controller. The owner's existing architecture makes per-instance
AIOps CaC authoritative for its auxiliary VM identities, while the allocation
registry owns the primary AAP VM, hypervisor and counter. The normal teardown
already loaded that private CaC for application permissions; it now reuses that
same capture before related-resource validation and final source comparisons.
No alternate loader, credential, target API read, inventory copy or handoff
store was introduced. Present source rows must agree with the durable identities.

Surviving registered primary VMs and same-hypervisor application VM records also
supply permission-owner identities when their external inventory rows are
absent. Only the selected instance enters the deletion plan. Runtime settings
are excluded from projected ownership. Existing source-versus-target, namespace,
hypervisor, SSH trust, native domain/storage/network checks and production
exclusions remain in force. Private VM records stay available until successful
cleanup, allowing a new job to reconstruct ownership after partial completion.
Missing canonical primary identity with an absent VM remains a refusal; the
existing registered-primary/missing-VM cleanup remains supported.

Sixty-nine focused local tests pass, including selected-instance cleanup with a
surviving successor's four records absent externally, encrypted Git recovery
after partial source deletion, identity conflicts, supplemental interfaces and
installation access. Scoped strict production lint passed across thirteen
encountered files; the teardown syntax check passed on local ansible-core
2.16.19 using the established environment Vault identity. An independent agent
review found no significant defect and passed seven focused cases. These are
local implementation checks; normal live teardown and final end-to-end
acceptance remain the parent task's responsibility and were not run here.

## Keep Zabbix configuration with its existing VM definition — 2026-11-09

Implementation `bdda318620ae30ebea455376442dc509ec7fb583` (0.50.0) follows
the owner's selected instance → VM → configuration placement. Existing firewall
settings move into the Zabbix VM definition with one copy; verified native VM
facts and unrelated protected values remain intact. The existing importer
resolves native source inventory, placement group and target alias instead of
introducing another publisher or Job Template.

The matching Zabbix deployment saves its authenticated VM facts and observed
gateway into that source inventory, invokes the same importer and reloads its
rendered host, runtime ciphertext and cached policy. Fresh permission is derived
once from verified ownership; a later explicit removal stays removed. Planned
VMs carry configuration without fabricated resource identity. Controller
collection operations supply the API behavior; the existing settings checks
retain project-specific ownership and layout validation.

Thirty-nine settings/publication and five native policy fixtures pass, as do
three matching producer sequences, nine runtime/Vault and four configuration
checks. Scoped strict lint, syntax and whitespace checks pass. Controller
operations are substituted in producer fixtures; no live fresh-clone acceptance
is claimed. The existing local Ansible/Python crypt deprecation remains visible.
Protected layout and every pinned common reader must be upgraded together before
affected runtime jobs resume; that coordinated migration is separate from these
local source checks.

## Save new VM details inside the existing application VM definition — 2026-11-09

The owner approved saving newly verified monitoring VM details in encrypted
AIOps CaC before configuration continues, using the existing importer. The
placement is the selected instance's existing Zabbix VM definition, with its
configuration nested there. A separate metadata section/store or saved Job
Template was not selected. Implementation remains active and is not claimed by
this documentation checkpoint.

Implementation `5cddc87948bce4d5c7808784e343ecc2f9475282`, release 0.49.13,
refreshes the public task overview and the existing encrypted recovery export.
It preserves all 181 prior IDs and 258 prior comments across 182 current records
and 260 total comments. Both Beads mirror checks and native Vault preservation
checks pass. Source-reader fixes, successful normal imports/retrieval and the
later firewall readback failure are retained separately from unfinished MCP,
fresh application, Windows and host-rebuild acceptance. No executable source,
host firewall, VM or hardware state changes are part of this checkpoint.

## Preserve blocked inputs in the recovery checkpoint — 2026-11-09

Implementation `96e5e29f19511441eb977eb9ef8757c8fd68924b` (0.49.8) refreshes
the existing public task mirror. Matching Hactar checkpoint
`a8681163134ef3432bafe7ac42ceaf3e3231903c` preserves 181 complete selected
records, all 180 previously exported IDs and all 258 comments under the existing
Vault scope and header. AutoDeploy lists 122 tasks; Hactar lists 80. The existing
exporters remain authoritative projections of Beads, not another task store.

The native firewall source consumers are published, but ordinary setup still
failed fetching its private configuration source. Authentication delivery is
therefore back in progress rather than complete. The new fresh-instance Zabbix
ownership-publication decision remains blocked. Private input preparation and
publication do not establish successful source retrieval, host application,
MCP builds, fresh Command Center acceptance or readiness for the physical rebuild.

Both exporters' current-state checks, native Vault roundtrip/preservation,
nine AutoDeploy mirror tests, six Hactar mirror tests, four version-tool tests
and whitespace checks passed. The process diagrams, functional source and user
handover were unchanged. No live controller, guest, firewall, DNS or credential
operation was performed by this documentation checkpoint.

## Explain elapsed actions across the requested seven-day window — 2026-11-09

Implementation `ce594b99c587b99c9e2191fbf2ec50b001ee1608` (0.49.6) replaces
the accepted one-day pilot with the requested seven-day retrospective. Markdown
remains primary; its HTML companion presents the same 64 meaningful blocks in
nine compact diagrams. The 20 longest evidenced episodes have vivid rank bands,
numeric ranks and observed durations directly in their boxes.

The analysis distinguishes job runtime, elapsed calendar spans, documented
waits, rework and unknown attribution. Parallel spans are not summed, and the
longest browser-feedback wait is not described as continuous implementation or
a proven successor-deployment blocker. Visible narrative and existing project
history support the report; raw commands, transcripts and private reasoning do
not appear in the interface or repository.

The previous HTML used doubled digit escapes and a fixed expected node count.
Controls now derive their IDs from the actual diagrams/details. Root replay
passed all 64 click/keyboard/native-collapse paths and missing-runtime/control
cases; matching structure, privacy, GFM tables and pinned Mermaid grammar checks
passed. These are source/control-logic checks; actual browser layout and clicks
remain unverified. Native collapsible explanations remain usable without the
internet module.

## Wait for normal Controller project synchronization — 2026-11-09

Implementation `29f2a29470fceb088e42cce892bef2307245f68e` (0.49.4) fixes the
observed successor CaC import failure while creating its Controller project.
The exact pinned CoP 4.10 role allowed 50 one-second status polls. Protected
event metadata showed all 50 attempts were exhausted after 60.280 seconds;
the underlying project update continued and then succeeded in 67.684 seconds.
The importer's outer wait ended before the ordinary synchronization completed.

The existing dispatcher call now supplies the documented project-specific
180 retries and one-second delay. This retains bounded completion below the
role's existing 1000-second async module allowance without changing other
resource waits, secure logging or failure reporting. No second retry job,
reconciliation path, helper or polling service is added.

The focused test resolves the actual pinned collection's project defaults and
collector arguments, checks the selected wait and secure logging, and confirms
the wait remains below the existing async allowance. Strict scoped lint, Python
compilation and diff checks pass. The normal successor self-CaC retry subsequently
passed in 174.539 seconds on the published fix; this verifies the import repair,
not the remaining application or full successor acceptance tests.

## Propagate existing RHSM inputs into selected AIOps runtime settings — 2026-11-09

Implementation `8efa9df482fc7497c0ffb9e6e3fe8fab5f9e2735` (0.49.2) prepares the
RHEL prerequisite inputs needed by the existing MCP jobs. The source's existing
vaulted organization and activation key already support AAP's RHEL setup; the
existing AIOps pre-import phase now reuses that approved material for the
selected allocation's encrypted runtime namespace. No new credential, store,
helper or job is introduced, and configuration import registers no host.

The instance name is derived from the verified selected allocation. The runtime
entry includes only that name, the protected RHSM inputs and the required RHEL 9
BaseOS/AppStream repositories. Existing matching material is retained; a
different organization or key stops for review rather than being replaced.
Other instances and unrelated runtime settings stay unchanged. Protected inputs
are accepted only in the action's no-log pre-import phase and omitted afterward.

The actual native-mode fixture exposed a missing exact-type serializer handler:
Ansible's string conversion produced a native unsafe string whose literal tag
was lost during YAML writing. Existing roundtrip validation correctly refused
publication. Adding that type to the existing literal-string serializer fixes
the failure without weakening validation or adding another serialization path.

All 34 preparation tests and both serializer/CoP merge tests pass, including the
actual pre/post tasks in both native modes, encrypted local Git publication,
selected-instance preservation, repeats and mismatch refusal without credential
output. Scoped strict lint, Python compilation and diff checks pass. These
results do not establish future-instance live import, registration or MCP use.

## Apply source-owned firewall CaC through native Ansible — 2026-11-09

Implementation `90edda0546fe149d317846d8d257fefe7abf6319` (0.49.0) replaces Python firewall mutation
and the deployed JSON policy with readable Ansible, certified firewall role
1.120.5 and reviewed Hactar native nft tasks. The owner selected CaC as desired
state, including removals, and approved temporary atomic-directory locking across
independent jobs. Existing resource/production guards and source-publication
boundaries remain; read-only provisioning pin checks require an explicit apply
when native policy differs. The same-host switch must quiesce old flock writers.

Application permissions remain in their own encrypted AIOps instance records.
Existing central bootstrap authentication loads that source without a second
colliding Git credential. Native tagged loading preserves unsafe literals and
unused encrypted leaves; no deployed state file becomes policy authority. Only
native old/new/rollback policy combines base with current application grants.
Canonical base publication remains base-only. The independent protected source
address and reviewed public Hactar revision are required caller inputs.

Exact selected decommission disables and verifies ordinary rich rules before
removing domains or source records, while retaining other instances. Arbitrary
source omission cannot identify an already orphaned ordinary rule: stop for
manual reconciliation rather than infer ownership or purge unrelated rules.
New clone-record publication and final AIOps-record retirement remain explicit
private-CaC operator steps; no new publisher, registry, credential type or service
was introduced.

The merged functional source passed 103 focused tests, strict scoped lint for
16 Ansible files and syntax checks of the five normal stage/decommission
playbooks. These are source/fixture results. Protected migration, coordinated
consumer pins, host application and live AAP demonstration acceptance remain
separate rollout work. No formal review or live acceptance is claimed.

## Use fresh default Command Center setup and target-side MCP builds — 2026-11-09

The owner selected the latest Command Center source at deployment, its maintained
default installation directory, a separate home-relative agent workspace and a
fresh Beads tracker on first setup. Repeated deployments preserve existing
tracker data and authentication. No demonstration-repository checkout is needed
as a prerequisite. The missing-tools/workspace Ansible patch is prepared and
locally checked, with publication and live application acceptance still pending.

Public AIOps implementation `7a973353e2c7e0215473b1d9393b5b984d54be57`,
release 1.2.0, implements the previously selected target-side MCP image builds.
The obsolete rendered artifact prerequisite is removed while preserving existing
encrypted instance records and runtime secrets. Four build fixtures, ten MCP
regressions, syntax and focused strict lint passed; real builds and authenticated
queries remain to be verified through the existing application jobs.

The owner also requested reproducible CloudCLI setup for two new-TRA accounts
using the newer release currently installed in the selected existing account,
while preserving the production account's older installation. Its existing AAP
MCP settings belong in encrypted AIOps CaC. Reading that private account requires
a protected operator export; no credential has been copied or guessed.

## Use CaC and Ansible instead of custom deployed state — 2026-11-09

The owner superseded the host-state proposals documented after `2b25410`
(0.48.26). Encrypted project CaC is the single desired-state authority, including
ownership, validation and the target hypervisor. Each instance has its own
section; adding another instance must preserve existing sections. Applying
changed CaC must remove deleted permissions rather than preserve observed rules.

The immediate firewall work replaces the custom isolation-helper/JSON path
with readable Ansible and native firewall configuration. The broader existing
cleanup task now includes custom helpers and deployed sidecar state; a parallel
source inventory identifies writers and consumers before migration. Native
application authentication/data and essential resource/production checks remain
protected. These are selected requirements and work in progress, not a claim of
implementation or live acceptance. This conversation owns the firewall work;
the application-builder conversation retains application development.

The owner also selected target-side MCP image builds, with public build recipes
and encrypted per-instance AIOps configuration. The offline key-delivery choice
is superseded. A registry or separate development/build host remains deferred.

## Correct the CCNG blocker and preserve separate firewall ownership — 2026-11-09

The owner confirmed existing CCNG setup creates a password when absent and
reuses an existing one. Source `f6c28a1` (0.37.0) documents that interactive
behavior; its AAP task requires protected input only without authentication.
The earlier claim that a new application setup feature was required is withdrawn.
The rollout is ordinary unfinished work: update the selected successor data,
verify its existing setup path, deploy through AAP and check actual login.
No user password, default, auth transfer or changed authentication design is
supplied by this clarification. Production proxy task completion remains separate.

The owner also chose AIOps ownership for Zabbix-specific firewall permissions,
added on deployment and removed on decommission. The earlier exception question
is superseded. Building Command Center owns the integration; its draft calls
interfaces that do not yet exist and has no live validation. This documentation
does not publish that draft or implement the proposed base/use-case policy check.

## Stop monitoring setup on an invalid sample and preserve the ownership choice — 2026-11-08

AIOps implementation `f1b5d64` (1.1.8) requires a fresh successful website
sample before forwarding. The negative test exposed an explicit failure
override that masked exhausted readiness retries; removing it from both
health polls restores standard Ansible failure handling. Fifteen focused
tests and strict lint passed; a real retry remains held.

Exact guest diagnostics established the current website-probe failure:
the verified monitoring VM has no permission to reach its hypervisor bridge
on HTTPS. The validated candidate adds only that existing-schema client.
Native and central-record changes remain unapplied while the owner decides
whether the existing shared firewall records may remain in AutoDeploy secrets,
given the earlier AAP-only rule. No application settings are proposed there.
The saved-image job also lacks automatic publication of those shared records;
operator preparation remains an explicit limitation, not a completed feature.
The website is restored and disarmed, both activations are disabled, and the
separate MCP artifact-key delivery choice remains unanswered.

## Verify monitoring separately from the full repair demonstration — 2026-11-08

AIOps fix `93a30e3`, published at `3420f92` (1.1.7), extends the existing
frontend readiness window to cover the observed DNS negative cache. Address,
IPv6 and trusted-certificate checks remain intact; fourteen focused regressions
and strict task lint passed. The normal owned retry then passed without another
clone. Its identity, HTTPS Basic gate, monitoring and forwarding configuration
were verified. The real outage test then found that the website probe has no
valid sample and times out before generating an event. That connection remains
under repair; configuration success did not prove website recovery.
The exact new testserver's normal agent installation also passed.

Private AIOps implementation `1a64a17`, documented at `0db59ca`, preserves the
verified selected-instance resource and final monitoring settings. The normal
configuration refresh passed with other instances unchanged. The existing
website recovery route is tested separately from private MCP and AI-driven
repair. The latter still needs the owner's pending artifact-key delivery choice;
no credential mechanism or new helper was selected to bypass that decision.
These are partial service results, not complete recovery or permission to start
the conditional bare-metal reinstall.

## Preserve staged acceptance and the exact predecessor VM retirement — 2026-11-08

Windows `c54d4d4` (1.1.14) passed the selected successor's AD login/RBAC checks,
both April OS baselines and complete application baseline-to-upgrade verification.
Implementation `a11695c` (1.1.15), documented at `de0687c` (1.1.16), then passed
all five normal guest retirements and final network/source cleanup using backend
`e0a96b1`. Original core guests and golden images were preserved. The original
workflow failed and required staged continuation; fresh unattended acceptance
is still unproved, and the original masked failure's precise cause is unknown.

The owner reiterated removing only the old AAP VM. The earlier implementation
choice question was withdrawn in favour of that one-off exact VM operation;
no partial-decommission mode was added. After Windows baseline verification,
the registered VM and its single unshared runtime clone were removed. Remaining
core definitions/states, source images and policy passed verification. DNS,
proxy, credential and canonical residuals remain separate later cleanup work.

The existing Linux template on Assistant `9d76402` (1.11.11) deployed the new
testserver and TRA with actual native and source/canonical matching, exercising
publisher fix `785e613`. Their remaining AIOps services are not inferred from
VM deployment. The existing approved backup route also preserved all 22 MCP
artifact files immutably and passed byte-level verification; exact restore
metadata remains in Hactar's existing encrypted download evidence. No new
artifact store, credential type or runtime helper was introduced.
Hactar implementation `7def85f` preserves that verified restore record and all
168 selected encrypted task records, retaining previous IDs and export scope.

Private Windows implementation `18f2ae7`, documented at `512e247` (0.0.2), makes
the existing API credential's CA bundle include the already registered selected
issuer when absent. Eight native rendering checks passed; the full current
35-template resource render and all unrelated private data remained unchanged.
This prevents repeating the known missing-issuer preparation defect without a
new trust source or factory. Fresh next-instance runtime verification remains
part of the later recovery acceptance.

## Retire only the predecessor AAP and continue on the successor — 2026-11-08

The owner withdrew the earlier source-AAP restart and directed retiring that
AAP while continuing tests on the successor. Other predecessor guests and
source images remain protected. Retirement must wait until normal Windows
cleanup verifies its immutable original core baseline, which still includes
the shut-down AAP's domain and disk. Earlier restoration plans are historical
and superseded, not permission to restart it.

Source review found that the existing decommission entry removes the entire
same-version environment. It must not be used for this narrower instruction.
The existing exact-retirement capability is being assessed before any resource
removal; this documentation introduces no new selector, framework or helper.
The pending CCNG rollout also needs successor AAP bindings rather than relying
on the retired AAP; its first-opening feature remains separate application work.

## Bound native release lock contention and keep diagnostics safe — 2026-11-08

Fix `e0a96b1c13c756faf7cef3ca7ca3fe2dcc3b1e2e` gives the existing release
transaction the same bounded five-second lock wait as the management helper.
Separate AAP processes can reach this shared native critical section; Ansible
task throttling does not serialize those processes. The exclusive lock still
precedes every probe and mutation. Identity, current-policy, production denial
and rollback checks remain unchanged; the separate retirement path is untouched.

Only a controlled lock-exhaustion marker produces code 75 and fixed public
failure text. Command input/results stay protected, while other exceptions keep
generic diagnostics and are not retried. No helper, framework, type or result
schema was introduced.

The earlier pinned helper failed immediately under a real sandbox directory
lock and discarded the error through its CLI. This reproduces a defect, not
the original historical exception: retained failure diagnostics were censored,
and the exact lock owner is unknown. An identical later retry passed, which
does not establish the missing cause.

Fifteen runtime tests, eighteen supplemental-interface tests and four version
tests passed, including real transient locking followed by complete fake-native
apply, bounded exhaustion without probes or changes, unchanged rollback and
identity checks, exact CLI classification and native Ansible secret-canary
protection. Strict production role lint, Python/YAML syntax and whitespace
checks passed. Caller pins and a complete authorized live workflow remain
separate work; publication is not full-project or live end-to-end acceptance.

## Correct first-opening setup and approve the Windows test window — 2026-11-08

The owner clarified that a fresh CCNG installation creates its password at first
browser opening. It must use neither a default nor a password provided before
deployment. Earlier entries describing a required Vault password reflect the
worker's mistaken interpretation and are superseded by this correction.
Existing user authentication remains preserved. The application owner reports
CCNG 0.35.1 still requires authentication before startup; therefore the fresh
rollout waits for implementation and verification, with no user-password input
pending. No authentication control or private runtime setting was changed.

The owner separately approved the existing bounded Windows capacity proposal:
gracefully stop only the selected source AAP on the pinned test hypervisor,
run the successor's normal Windows test and owned cleanup, then restart and
verify the source's services and prior EDA state. Production, other core guests
and golden images remain protected; force shutdown and AAP decommissioning are
excluded. The decision is resolved, while actual execution is tracked separately.
This documentation does not claim successful shutdown, testing or restoration.

## Verify and retire the disposable Assistant environment — 2026-11-08

The normal successor software test passed on pinned Assistant source `73a74ac`
(1.11.8) using private preparation `0157adc` and pair `1997664`. The complete run
took about 46 minutes and exercised actual deployed CLI, environment and
project-isolation checks, without authentication restoration or model inference.
Guest identity and canonical publication matched the resulting resource.

The existing retirement preview and apply both passed. Independent checks found
the case domain, disk, static DHCP/DNS records, owned policy and inventory rows
removed, with all five original guests and golden images preserved. One dynamic
DHCP lease remains cached until normal expiry; no shared-network restart was
used to clear it. This completes the disposable software test and cleanup,
while full successor services and independent host recovery remain open.

Assistant implementation `1ee9e4b`, documented at `9d76402` (1.11.11), then
updates only the existing public helper revision from its earlier value to
AutoDeploy fix `785e613`. All 23 focused caller/recovery/retirement/version
checks, three syntax checks and scoped lint passed. Private configuration and
the pinned software-test baseline stay unchanged. Actual new-guest publication
and AIOps consumption still need their own runtime verification.

Normal Automation Orchestrator and RHEL configuration setup then passed on
tested source `ead5a05` (0.48.17), preserving prior objects, token-store state
and EDA activation state. The RHEL-only prerequisite run confirmed fix `7d8a59b`
without selecting another case. Their reviewed projects, templates, inventories,
execution environments and credential definitions are installed. These API
imports do not establish OpenShift deployment or external RHEL patching.

## Require a chosen CCNG password only for fresh setup — 2026-11-08

The owner withdrew the shared default-password and first-login access-choice
proposal. A fresh install must require an operator-chosen password, and an
existing user-set password must be preserved. The obsolete rollout dependency
is removed; no answer to the withdrawn access question is still required.

Published CCNG source `e5e1232` (0.35.0) already enforces this in its AAP password
task. The standalone installer's noninteractive behavior is a separate
application-owner concern. The rollout resumes private-candidate and secure
input verification, retaining the approved Machine/Vault choices and existing
target. No password is copied, generated, reset or supplied by this decision;
configuration import and actual application verification remain separate work.

## Prepare reviewed EE-only use cases independently — 2026-11-08

Fix `7d8a59ba8f310246493aa48db41da366d1111ab0` removes the common requirement
for at least one PAH repository. The reviewed RHEL capture deliberately declares
none because its existing runtime image supplies its Satellite collection.
Requiring an unrelated selected use case would hide that standalone setup defect.
Review, mapping, sequence, repository uniqueness, exact collection versions and
execution-image readiness remain required; empty collection loops simply skip.

Eight native admission/PAH tests, sixteen selector tests and four version tests
passed. The admission regression executes the real task definitions, admitting
reviewed empty requirements and refusing unreviewed, missing-image, duplicate and
unpinned inputs. Strict production lint and prerequisite syntax checks passed.
These are source checks; standalone live metadata setup and external application
runtime acceptance remain separate. No helper, flag, credential or schema is added.

## Preserve verified Linux SSH fields for the next AIOps import — 2026-11-08

Fix `785e613f53036fae61bf3a63b994a83fbe68fcaf` carries a Linux guest's supplied
verified user and port into its source inventory alongside the existing native
resource. The previous publisher omitted those fields on a new host, so the
unchanged AIOps provenance check could not accept that host without manual
inventory edits. No account or port is inferred, conflicting existing values
still stop publication, and Windows keeps its separate WinRM behavior.

Thirty AIOps preparation/publication tests, nine encrypted guest-release tests,
twelve Windows lifecycle tests and four version tests passed, with Python syntax
and whitespace checks. The new producer-to-consumer fixture proves the mapping,
idempotence, conflict refusal and behavior when optional fields are absent.

The existing publisher was corrected rather than adding a helper, schema,
credential or alternate registration path. Its source-fix task is closed in the
existing task overview and encrypted recovery export. Selecting this revision
in callers and proving a full live guest-to-AIOps run remain separate work;
publication is not full-project review or end-to-end acceptance.

## Verify the website and prepare the existing disposable test — 2026-11-08

AIOps source `c69097e` completed the successor website deployment without changing
code or DNS timeouts. Normal DNS and trusted HTTPS then passed, with monitoring
and auto-arm off; the expected selected AAP fault destination was verified.

Private Assistant implementation `0157adc`, with encrypted pair `1997664` and
published history `df7bbda`, prepares only the selected successor's disposable
test and retirement settings while retaining the predecessor's six snapshots.
Prepared identities are selected explicitly, including their supported aliases;
unprepared instances fail rather than inheriting another instance's settings.
The already defined Linux utility joins the ordinary concrete resource list by
YAML reference, preserving the original seven definitions and existing validation.
No dispatch framework, helper, credential type or new store is added.

Normal configuration import passed. Source/render ciphertext preservation and
public provenance were checked; AAP masks stored secret fields, so their native
bytes were not read independently. The existing disposable runtime test will
verify normal consumption instead of adding a redundant secret-storage check.
Software acceptance and owned cleanup remain unfinished.

## Retain the approved image-based Zabbix authentication baseline — 2026-11-08

Private configuration implementation `bf75752` supplies the selected demo's
existing MCP-token leaf from its approved image-bootstrap value. The earlier
working setup already used that image credential, and the owner authorized
taking over its MCP configuration. Requiring a newly minted Zabbix token would
have added an unnecessary producer and encryption/publishing mechanism.

Keep the existing runtime schema, selected-resource/endpoint checks and explicit
normal CaC refresh for saved job payloads. Target-local AAP/MCP and EDA credentials
remain separately generated by the existing factories. No new credential type,
store, helper or hidden child job is introduced. The private configuration and
docs are published at `63c91c2`; application and private MCP tests remain pending.

AutoDeploy source `22ac431`, including port-boundary fix `2cd85c8`, passed the
normal AIOps import after the successful prerequisites. Native readback verified
the new objects and disabled activations while preserving prior instance data.
Remote and self-targeted AutoDeploy imports also passed; these are configuration
acceptance results, not complete successor service recovery.

The successor's normal Windows and Assistant prerequisite/import sequences and
AIOps self-refresh also passed on that source. Existing objects and native
credentials were preserved; new EDA activations remain disabled. Fresh Windows
runtime is capacity-dependent, and Assistant's disposable test still needs
instance-specific payload preparation. Keep those gaps explicit rather than
counting successful configuration imports as application acceptance.

## Accept native inventory port text at the AIOps boundary — 2026-11-08

Fix `2cd85c8` normalizes a canonical decimal-text inventory SSH port before the
existing strict hypervisor pin validation. A normal configuration import exposed
this representation difference during successor AIOps preparation; the selected
port itself matched the independently verified route. Identity, account, host-key
and port-range checks remain unchanged, and no saved inventory is rewritten.

The focused 29-test AIOps module, four version tests, Python syntax and native
selected-context reproduction passed. This repairs preparation input handling;
successful CaC import and application deployment require their own live results.
The existing task overview was refreshed without introducing new automation.

## Document the AAP-only successor acceptance — 2026-11-08

The tested runtime remains `30629f7` (source 0.48.7), including guest SSH fix
`34b40d1`. The source controller completed the four existing stages, and bounded
independent checks verified trusted public API/token access, a valid license,
ready Controller and distinct native instance identity. Original guests, disks,
source images and prior API records were preserved. The temporary native
start-at-task setting was restored after the continuation job captured it.

Stage 01 required a repair and continuation, so this closes AAP-only acceptance
without claiming a fresh unattended run or complete successor service recovery.
The quick guide now describes the four installed stage templates directly;
fresh successors must not depend on an assumed umbrella workflow. Additional
use-case imports and memory-aware runtime testing remain separately tracked.

The existing task overview and encrypted recovery export retain the actual job
outcomes and limitations. This documentation update introduces no new workflow,
recovery mechanism, credential, allocation, shutdown or host reinstall.

## Preserve guest SSH routing above hypervisor facts — 2026-11-08

Fix `34b40d1` keeps the existing Stage 01 SSH safety checks while giving the
new guest's connection settings the same precedence as the earlier hypervisor
facts. A delegated block's variables alone did not override those facts, so the
readiness guard correctly stopped before guest authentication. The probe now
saves the original connection, binds the exact pinned guest route and restores
the original hypervisor facts in `always` on success or failure.

The existing native Ansible regression now reproduces the observed precedence,
checks guest SSH through the pinned hypervisor, rejects unsafe higher-precedence
caller inputs and verifies restoration. It also checks native partial-stage
continuation when earlier connection facts are absent. All 26 allocation/routing
tests, focused playbook syntax and production lint passed. The failed live run
created one guest before the guard stopped; completing a partial stage remains
separate from proving a fresh unattended deployment.

The public task overview includes the existing successor functional-test child.
Paired Hactar checkpoint `573acb4` preserves all 150 prior task records and that
child in the existing encrypted recovery snapshot. No new recovery framework,
workflow, credential or counter reset was introduced.

## Preserve completed teardown and production HTTPS acceptance — 2026-11-07

Checkpoint `0ddcd06` documents the passed staged Windows patching demonstration
and Windows-only reset separately from fresh unattended provisioning. Final
verification passed on Windows source 1.1.11; its published documentation retains
the earlier repairs and unresolved historical failure rather than hiding them.

Hactar checkpoint `c68f6e6` preserves all 150 prior full task records and current
outcomes in the existing encrypted recovery export. Production backend HTTPS
verification and the user's confirmation of external and localhost access are
recorded as completed; the rejected host-setting removal remains withdrawn.
The separate test application waits on the existing first-login implementation
task, not another password request. Read-only successor readiness does not mean
a VM has been allocated or installed.

Mirror/export checks, Vault preservation, the original handover checksum and
diff checks passed. This checkpoint changes no runtime code or configuration.

## Document the approved application deployment choices — 2026-11-07

Documentation checkpoint `090d761` records the owner's explicit approval of
encrypted runtime settings, expected SSH server-key preparation, credential-free
HTTPS public-source download and matched tested application revisions. The
README distinguishes configuration import from installation and running-service
acceptance so restoring the project does not repeat the resolved decisions or
mistake an imported template for a working application.

The public overview reflects completed preparation and ongoing runtime work.
Hactar checkpoint `1f76421` retains all 150 existing full task records and their
current user answers in the established encrypted recovery export. Export/mirror
checks, preservation of every prior record and the original user handover,
four existing version-tool tests and diff checks passed. No runtime playbook,
credential, inventory, application restart or new recovery mechanism was added.

## Clarify the canonical Command Center task title — 2026-11-06

Existing task `bead-wd-1rl.40` now reads "Deploy Command Center from AAP to the
selected workstation". This makes the deployment direction clear and keeps the
public title generic. Actual target choices, original notes, state, owner and
labels remain unchanged; Hactar checkpoint `62c2a27` retains the full encrypted
147-record context and appended clarification.

The ordinary exporter/mirror refresh and preservation checks passed. No exporter
code, title-override mechanism, new research, runtime or umbrella change was
introduced. Existing README instructions remain accurate. Published history is
preserved; this is one necessary metadata-only follow-up.

## Reflect waiting tasks and an open stability issue accurately — 2026-11-06

The existing diagram task `bead-wd-72f.35` is blocked on its already-pending
client error/viewer question, with no browser-diagnosis worker running. The
known stability issue `bead-wd-72f.31.4.3` is open: bounded research/observer work
finished, but its cause and correction criterion remain unmet. Neither a new
active investigation nor a completed fix is claimed. Windows and the deployment
integration keep their actual input blockers.

Hactar checkpoint `89c2cf1` retains all 147 complete encrypted task records and
these exact two status corrections. Exporter/mirror checks and preservation
checks passed. Existing README instructions remain accurate. This single
metadata/version checkpoint changes no runtime source, evidence collection,
base configuration, credentials, DNS or umbrella reference.

## Reflect completed Windows OS work and the remaining package-access blocker — 2026-11-06

The existing Windows acceptance record now has a real public status change from
in progress to blocked. Windows 1.1.5 documentation `0626bd5` and tested executable
`2dfb9c0` establish both selected OS patch jobs at their exact April builds,
with zero remaining approved updates/reboots, alongside successful AD and WSUS.
Only the existing Nexus package-access approval blocks the remaining package
chain; its prepared rule is unapplied. Full use-case acceptance stays open.

Hactar checkpoint `ed5a152` retains all 147 complete encrypted task records and
the actual proof. Exporter/mirror checks passed with every prior ID preserved.
README instructions remain accurate and unchanged. This single necessary
overview/version checkpoint changes no runtime source, base, credentials or DNS.

## Retain existing deferred external CaC work — 2026-11-06

Documentation `e8d43a1` adds the existing `bead-wd-9ezo` to the generated public
overview as a deferred future independent External CloudCLI CaC project. The
original task, ownership and labels are retained; no duplicate or implementation
task is created. Its full handoff and the current blocked integration inputs
remain in Hactar's encrypted 147-record export, checkpoint `6514ae2`.

The existing exporter/check retains all previous task IDs, and Hactar's overview
check passes. Public text contains only generic task metadata. The user's
handover and separate deployment evidence are preserved. This publication
changes no runtime source, credentials, base configuration, DNS or umbrella refs.

## Document verified agent recovery without changing deployment behavior — 2026-11-06

Documentation `8b44905` refreshes the public overview to 87 tasks, including the
closed agent-remediation acceptance and rebuild-tooling task, and the current
transferred rollout state. The selected isolated service-outage chain passed on
AIOps runtime `3da21af`, including bounded-turn implementation `67a6e69`; its
acceptance documentation is `c69097e`. One real event launched one bounded agent
and one saved repair, with native target, service and fresh recovery verification.
This does not establish package-removal recovery or successor installation.

Hactar checkpoint `3904f20` preserves the actual aggregate and all 146 complete
selected task records, including closed acceptance. Existing exporter/mirror
checks passed without changing that encrypted checkpoint during this overview
refresh. Public output contains metadata only; private records and the user's
handover remain protected. No runtime playbook, base configuration, DNS,
credential or production-project pin was changed by this publication.

## Keep transferred AAP work in the recoverable task overview — 2026-11-06

Documentation `da64bd1a2f17579176694017e188e812f5a134c1` refreshes the generated
public overview to 86 tasks, including the existing transferred rollout question
and the Windows API-responsiveness follow-up. AAP-owned integration work retains
its project label, conversation association and original parent; classification
does not answer its pending Vault-source question or authorize deployment.

The public overview matches a fresh Beads read. Hactar checkpoint `dabae0b`
already holds the 145 selected full records and remains byte-for-byte unchanged.
No automation, credential binding, VM or live-job behavior changes. Published
documentation remains separate from unfinished runtime and successor acceptance.

## Diagnose missing diagrams without hiding a valid rendering — 2026-11-06

Implementation `51b8df4` replaces a misleading blanket network error with separate
Mermaid import, rendering and node-control errors. A node-control exception now
keeps any rendered SVG visible. Static instructions distinguish a script-blocking
preview from a started runtime without assuming the user's viewing context. The
pinned module was reachable, and its actual grammar accepted all 28 vertices in
a syntax-only Node harness; that does not exercise browser DOM sanitation or SVG
layout. Focused checks cover the separate failures and preservation of rendered
SVG. Strict security remains unchanged. The reported client-side failure still
requires its actual stage/error; browser end-to-end verification is unavailable
without an installed executable. This checkpoint is diagnostic progress, not
closure of the user's missing-diagram report.

## Name the actual work and add a local interactive companion — 2026-11-06

Implementation `c3f4b74` replaces vague pilot phase labels with Windows
connectivity, Assistant Team installation/cleanup and Windows/private MCP test
preparation. The frozen window, 28 steps and historical timing qualifications
remain unchanged. At the user's additional request, a plain HTML companion embeds
the same diagram and details; known-node clicks or Enter/Space toggle native
details without changing Mermaid's strict security mode. A pinned Mermaid12.3.0
CDN runtime is the sole online rendering requirement; no server, package install
or new audit is required. The CDN response, content parity, all node toggle paths
and runtime-failure fallback were checked. Browser rendering remains unverified
because no browser executable was available. Markdown remains the GitHub-readable
source; users download/open the HTML locally rather than expect GitHub to host it.

## Explain delivery delay through a bounded visible-history pilot — 2026-11-06

Implementation `15bd6ce` adds the user-approved Markdown flowchart for one frozen
24-hour window. Its 28 short Mermaid blocks map to native collapsible details,
keeping the overview readable while explaining decisions, actual failures,
fixes, outcomes and timing. Main visible chat and existing decision histories
drive the narrative; underlying execution evidence only corroborates facts. Raw
action lists, private reasoning and environment identifiers stay out of Git.
The record separates real installation time, observed rework, pending execution
and the acknowledged overnight continuation failure; unknown effort and parallel
overlap remain explicit. No live AAP query or behavior change was needed.
Structural/privacy checks passed; a Mermaid renderer was unavailable, so rendered
layout was not claimed verified.

## Carry only the private AAP issuer in runtime settings — 2026-11-06

Implementation `bde1120` reads the installer's `tls/ca.cert` by default. A real
CaC request failed with HTTP 413 because copying the extracted system-root
bundle expanded encrypted runtime data past the proxy request limit. The actual
installed issuer is already present in that bundle and independently verifies
both private MCP and Controller HTTPS identities. No proxy limit, token or
global trust change is needed. Public provider calls retain their existing
system/vendor roots and additive application trust. The native publication/reuse
test passed; selected metadata correction and live import retry are separate.

## Preserve secondary isolation during final AAP release — 2026-11-06

Implementation `437fe9f` keeps source policy comparison aligned with the existing
primary-only AAP release. A live base refresh exposed that the shared interface
enumerator also selected a Windows-owned second interface, contradicting the
intended transition. The fix selects only the primary identity for this AAP
operation; secondary ownership and native hardware checks remain unchanged.
The focused regression proves publication and an idempotent repeat without
granting the secondary interface egress. Live base retry remains separate proof.

## Reuse selected instance access for private AIOps MCP — 2026-11-05

Implementation `8237ce6` adds optional private MCP endpoint/public-CA metadata to
the existing encrypted instance record and credential payload. Ordinary API
authentication and legacy records remain unchanged. Existing base publication
reads the installed authority; existing AIOps preparation copies only the chosen
connection into its runtime Vault. This keeps the API importer free of SSH and
adds no token, credential type, store or job. Compatible readers must be synced
before normal selected-instance backfill; unrelated pinned guest lifecycle paths
preserve the mapping. Forty-five focused checks and both affected syntax entry
points passed. No backfill, deployment, model or policy action ran for validation.

## Reuse the existing Windows retirement source plan — 2026-11-05

Implementation `41c77d231c54baf9ea3fd70d7b2b35f00183de33` exposes the same
retirement source plan as an internal task entry point, so the existing Windows
reset job can distinguish registered guests from unconfigured clones before
native checks. A focused native test found that absent records became empty
strings under non-native Jinja; retaining the complete mapping preserves actual
null absence. Registered guests still require full native planning and normal
publication. Three focused tests and two-file production lint passed. Complete
Windows reset remains subject to the separate authorized live test.

## Keep Windows AAP networking in its infrastructure deployment — 2026-11-05

Implementation `eb806b7b79d51f08d7cf54fb2edb3d449ed375aa` follows the owner's decision that the
Windows infrastructure job should prepare its selected AAP's second isolated NIC
and persistent RHEL connection, following the AIOps infrastructure pattern.
The existing private Windows profile declares this requirement. The API-only CaC
import installs definitions; the infrastructure job performs the host work.
Existing AAP guest preparation remains a partial image, storage, subscription and
installer setup, rather than a complete declared RHEL operating-system baseline.

The same existing AAP allocation and main-inventory ownership record retain one
optional Windows interface. Its primary identity and route remain immutable.
Native checks account for the exact current and persistent interface set,
Windows ownership alias and virtio model. Authenticated RHEL readback proves the
static address, manual IPv4, disabled IPv6, persistent connection and absence of
a gateway or DNS configuration. Firewall permissions remain unchanged.

The same role exposes its source preflight before host work. Its existing
publisher saves the bounded ownership change with encrypted Git compare-and-swap
and reconciles the same source inventory row. Concurrent writers retain a
published exact owner. Failed jobs may remove only newly created components,
after a fresh authenticated read proves canonical ownership absent; uncertainty
preserves the components for review. Complete AAP cleanup consumes every saved
NIC and removes exact owned DHCP/DNS host records while retaining other network
content. Older live single-NIC AAPs reuse their already validated native identity
without inventing saved verification metadata. Missing ownership still refuses
ambiguous reservation cleanup.

Repeated dynamic role calls exposed Ansible's cached action module retaining an
earlier deleted checkout. The publisher now reads settings through each native
action instance's current source path, retaining strict path validation and the
existing authentication and cleanup behavior.

The merged tree preserves the separately published sixth RHEL CaC project and
passes 54 supplemental-interface, native plugin-lifetime, project-contract,
bootstrap and selector checks. The coordinator independently repeated all 17
supplemental tests. Existing decommission, allocation, source TLS and native role
checks also passed, as did production lint, AST, local links and whitespace
validation. Real capture rendering passed with the normal existing environment
and CaC Vault identities. This publication establishes code and local validation;
live interface setup, Windows functionality and complete cleanup remain separate
acceptance steps. This worker launched no live job or host operation.

## Add explicit HTTP bootstrap for an already owned guest — 2026-11-05

Implementation `85ee77d` follows the owner's decision to retain the current
container platform and its HTTP downloads.
The approved permission is public IPv4 TCP 80 for only the existing verified
guest, retaining its HTTPS access and all private/reserved/production blocks.
The shared implementation therefore extends the existing guest bootstrap and
publication transaction with `guest_bootstrap_http`, rather than changing HTTPS
approvals or releasing the guest before configuration succeeds.

HTTP is an independent optional list of exact bridge, IPv4 and MAC identities.
The new operation requires the complete existing published guest identity and
placement, then repeats native domain, disk, network, lease and bootstrap
provenance checks before applying the exact derived change. Existing source-job
verification, encrypted compare-and-swap publication, source alias reconciliation,
idempotent retries, durable-publication handling and bounded rollback remain.
All existing policy operations preserve HTTP permissions; exact retirement
removes only the selected identity and retains production denial while another
HTTP, HTTPS or released guest survives. No service, store, registry, credential,
job template or wrapper is introduced.

All 113 scoped checks passed, including the real encrypted publication and
interrupted source synchronization retry, native HTTP operation and rollback,
complete guest identity checks, preservation through AAP/Linux/Windows policy
operations, and exact retirement. The coordinator independently repeated the
six HTTP tests. Production lint passed five files, and compile, policy-call
propagation, whitespace and added-text privacy checks passed.

These results establish implemented code and test behavior. Live helper
installation, source synchronization, encrypted environment changes, firewall
application and successful guest downloads remain separate acceptance steps.
This publication did not run those operations or launch a job.

## Verify the existing native Claude installer separately from model access — 2026-11-05

The AIOps implementation `80b7dff`, published in `86d3cb5`, passed its normal
native Claude installation with both private MCP diagnostics. Independent checks
verified the pinned binary, actual job user's command path, protected guardrails,
approved provider configuration and preservation of the original client data.
This verifies software readiness; no model call or isolation release occurred.
Those checks and the complete successor environment remain separate work.

## Retain the approved Windows demo certificate policy — 2026-11-05

Implementation `276ad84e257453d14a729d9cc806c0b65771e2e8` follows the operator's
choice to keep the existing Windows lab connection: HTTPS on port 5986 with
NTLM and certificate validation disabled. The additional predeployment image and
WinRM inspection is skipped. This corrects an extra prerequisite introduced for
the versioned test environment; it does not require new authentication or
certificate infrastructure.

Both existing Windows resource validators retain the same fields and require a
real Boolean certificate-validation result. The approved exception records
`false`; actually validated connections record `true`. Neither may replace
`verified: true`, authenticated computer facts or the independent native
UUID, exclusive clone, owning instance, NIC, source and policy checks. Strings
and numeric substitutes are refused. Other platform and SSH trust settings are
unchanged, and no new policy flag, job, credential type, store or service is added.

Eleven Windows lifecycle checks passed, including capture preservation of false,
native UUID mismatch refusal and real encrypted publication/retry for both
Boolean cases. Forty existing Linux/AAP lifecycle and version checks also passed.
These are source tests; actual Windows management connectivity, configuration,
isolation release and functional acceptance remain separate work.

## Match canonical live Controller SSH port representations — 2026-11-05

Implementation `6de45e0` normalizes only the live inventory SSH port before
comparing it with the exact registered pin. Controller had returned a canonical
decimal string where encrypted ownership used an integer; the same numeric port
was incorrectly refused during the shared bootstrap preflight. Actual receiving
logs showed successful source API reads, and read-only replay of the saved guest
artifact/captures reproduced this identity refusal. With the correction that
read-only plan passes without changing live variables or policy.

Only an integer or canonical ASCII decimal string in range 1–65535 is accepted.
Booleans, floats, signs, whitespace, leading zeros and other ports remain refused.
Other identity, source-job, TLS and policy checks are unchanged. Three new tests
include real Ansible/URI YAML-string and JSON-integer Controller representations
in both native modes; fifty-eight related instance, guest, Windows, AAP and
version checks also pass. Live bootstrap/software acceptance remains separate.

## Release the AAP guest only after normal base completes and cleans up — 2026-11-05

Implementation `75639c54ffff61eac7ea9e1b8707ce9f80240bb3` adds the final release
hook to normal Stage 04. The owner requires successful VM configuration before
full recovery isolation is lifted. An AAP primary is not a generic Linux clone,
so the existing shared role/action accepts an explicit AAP route, exact primary
resource and freshly authenticated guest machine ID. It reuses the consumed
reservation and existing native AAP ownership checks instead of fabricating
generic-image descriptions or duplicating the VM record in another store.

Base configuration, MCP/API token validation, source publication, temporary-token
revocation and private-workspace cleanup must all succeed first. The original
trust file is removed in that cleanup path, including failures. Only afterward
does the hook create new short-lived pinned SSH trust and read the guest's
machine ID with the existing login. It neither recovers passwords/tokens nor
changes authentication. The new trust file is always removed, including release
failure. Existing token-store publication and inventory registration must be
enabled; partial/skipped execution and check mode cannot grant full release.
The HTTPS-only installation repair retains its early end-play boundary.

The policy transaction adds only the exact primary bridge/IP/MAC identity in the
same three encrypted captures and source aliases. The selected reservation is
compared before and after durable publication and remains read-only. Existing
source-host aliases, physical identities, tokens, counters, native rules and
other guest permissions remain unchanged. Native checks cover both domain
definitions, actual UUID/disk/MAC/network/DHCP and conflicting guest ownership.
Existing exact rollback and durable-publication retry behavior is reused;
Linux and Windows paths keep their existing behavior.

Seventy-one lifecycle checks and four version checks pass on published 0.41.1,
including eighteen native ordering/failure scenarios across both template modes,
both repair modes and actual independent Git-writer reservation races before
and after publication. Production lint passes fifteen files. These are code and
native-fixture results; no live full-base job or AAP release was run by this work.

Separately, normal AIOps preparation job 3320 succeeded on `5728dfe` (0.41.1),
following implementation `cecff63`. Independent parent-agent readback verified
the new Claude installer, preservation of all sixty-nine previous template IDs
and the selected application's VM identity. That existing-target preparation
result does not prove this new final AAP release or a fresh successor cycle.

## Prepare AIOps data inside its existing CaC import — 2026-11-05

Implementation `cecff63751a800bdd38df3e0a18ab0f6b5c05f59` adds the reviewed
pre/post data stages to the existing `deploy-cac-project.yml` path for AIOps.
A fresh instance previously required already prepared auxiliary guest metadata
and a credential reference before its first import could render. The new stage
creates only the namespace and validated existing base Machine reference,
leaves absent guests disabled, and persists one per-instance Event Stream Basic
password before ordinary configuration roles use it. Existing known password
material is preserved; interrupted or competing Git writes do not rotate it.

The owner approved this repository's existing token having scoped write access.
Preparation therefore reuses the same private checkout, askpass, separate Vault
secrets and selected target HTTPS authentication. Both maintained files remain
whole-file encrypted, preserve original headers/literal tags and are committed
together. Accepted remote state is reread after publication. Capture and
effective launch-time review holds are enforced before commits or target access.
No additional job, wrapper, service, repository, credential type or store is added.

Guest facts are accepted only from matching verified native inventory ownership;
they are not generated or copied from a previous allocation. Zabbix retains its
own clone source hash, schema, frontend/private API references and native IDs,
while Linux retains its existing provenance schema. The shared inventory helper
normalizes only canonical positive decimal counter text, retaining malformed
value refusal and physical alias/ownership checks.

After the existing roles create resources, GET-only readback binds the target's
actual website fault-template ID/webhook key and Event Stream UUID/endpoint.
Existing values must agree; equivalent default HTTPS-port text is preserved
verbatim. The same Controller configuration role saves refreshed ciphertext;
preparation performs no direct AAP resource writes or activation/application run.

Thirty-three affected tests pass against the published Windows lifecycle base,
including actual Ansible modes, real encrypted local Git concurrency, lost
acknowledgements, wrong keys, holds and native provenance. Two private
ciphertext checks pass. Protected current-source/target-GET fixtures preserve
the existing password, runtime ciphertext and Zabbix metadata; fresh-instance
rendering passes both modes without fabricated guests. Syntax, four version
checks and scoped production lint pass. Full recursive lint still reports three
pre-existing unrelated issues, left unchanged.

This is configuration preparation, not complete successor deployment proof.
VM producer orchestration, per-clone Zabbix API/MCP token lifecycle, signed
offline MCP artifacts and approved shared application defaults remain separate
factory work. New namespaces receive no provider credentials. The current
Vertex reuse approval covers only the previously selected TRA and one short
read-only test, and does not extend to later allocations. No new allocation,
VM action, live import or model request was performed for this publication.

## Verify Windows through its own identity in the shared lifecycle — 2026-11-05

Implementation `ae9cfdbdbf29fe0471b71a0163cd557f607d7d8c` adds the explicitly
approved `guest.kind: windows` variant to the existing release and retirement
transaction. Windows clone naming, trusted WinRM/CIM identity and permanent NICs
differ from Linux. Fabricating Linux machine IDs, SSH keys or generic-image
descriptions would weaken ownership proof, so the Linux schema and default
request shapes remain while Windows has a strict bounded field set. No new
publisher, store, service, credential type or job is added.

The caller must complete the VM's configuration and validate its computer name,
normalized CIM product UUID and all observed NIC MAC/private IPv4 pairs over
authenticated, certificate-validated WinRM. Native readback independently matches
the clone marker, owning-instance title, UUID, exclusive Windows disk, both domain
definitions and every network/bridge/subnet/DHCP/DNS tuple. The selected WinRM
address must be one of those verified NICs. One or two NICs receive their exact
policy identities atomically; production protection and unrelated permissions
remain. Later patch/content functional tests are separate from this complete-VM
configuration milestone. No Windows bootstrap exception is authorized or enabled.

Windows retirement explicitly passes its kind even after successful record
removal. Saved canonical/API ownership supports interrupted publication retries;
native checks require the Windows clone and both incompatible Linux canonical
paths absent. Exact per-NIC static DHCP/DNS and policy records are removed through
the same encrypted captures and source inventory. Unknown host-service grants
still refuse preflight, dynamic lease cache is not edited, and allocation/token
state remains untouched. The AAP-only consumed-reservation guards are unchanged.

Sixty-three relevant checks pass, including real encrypted Git/API interruption
recovery, actual native template modes, distinct Windows bridges, native cleanup
and rollback, absent-path checks and existing Linux/AAP regressions. Both shared
lifecycle roles pass production lint; four version-tool checks also pass.
These are implementation checks. Trusted booted-Windows producer and live
deployment/release/decommission acceptance remain separate pending steps.

## Retire one verified generic guest through the existing transaction — 2026-11-05

Implementation `1976a5aae2f70a5455dda9032820889369849183` adds `retire_guest`
and the reusable two-phase `recovery_guest_retire` role. The owner requires
disposable use-case VMs to be removed after successful testing, including their
saved inventory and isolation permissions. Domain-and-disk deletion alone would
leave those permissions behind. The existing source API, Git writer, CaC Vault
and three encrypted captures provide the required ownership and publication;
no separate state store, credential type, service or job is introduced.

Planning resolves exact persisted clone provenance before deletion and refuses
unsupported selected host-service grants. Publication requires the domain and
both canonical disk paths absent, removes only its static DHCP reservations and
HTTPS/full-release entries, then reconciles source inventory. The caller retains
its own application inventory row until shared publication completes. A surviving
canonical/API resource record supports retries without guest SSH. With both
records absent, only physical absence with no additional policy or unknown DHCP
removal is accepted. Dynamic lease cache is reported separately and is not
edited. Existing AAP management and installation paths keep their default strict
guest-presence behavior.

Fifty-eight focused tests pass, including real encrypted publication and API
interruption recovery, exact native ownership/DHCP cleanup, both native template
modes and existing management/installation regressions. Scoped production lint
passes. These checks prove code behavior; the serialized live disposable-guest
deployment and decommission acceptance remain separate.

## Bootstrap approved generic guests without granting full release — 2026-11-04

Implementation `2795c133507ee5affdaf8e420807496cd2299899` extends the existing
verified-guest policy transaction with `guest_bootstrap_https`. The disposable
Assistant installation needs package downloads before it can complete software
configuration. The owner approved public IPv4 TCP 443 for that exact guest while
retaining private/reserved and production blocks; complete deployment and
validation must precede full release. The same source-job, native libvirt,
encrypted-capture and source inventory checks apply. The separate consumed-AAP
installation guard is unchanged, and no new service or credential type is added.

Nineteen guest/publication/native-role checks and eight existing AAP installation
regressions pass; focused offline production lint passes. These checks changed
no live permissions. Final lifecycle hooks and exact disposable-guest retirement
remain unfinished, and a static encrypted test profile must be refreshed from
canonical policy before a retry after a successful policy transition.

That implementation also documents the owner's two repository write exceptions.
The existing AutoDeploy/base CaC writer persists encrypted state. The owner
changed the existing AIOps token to Contents read/write for its own companion
repository so new instance settings can be persisted there. Other companions
retain read-only tokens. This reuses the existing credential/type and preserves
the token value and name; the external permission change was owner-confirmed,
not yet established by a new runtime publication test. Automated AIOps instance
preparation remains a separate task.

The owner approved reusing the reference Vertex authentication on the new TRA,
with any persisted copy encrypted in the private AIOps Vault and one short
read-only Claude/private-MCP test. Its implementation and live result are still
pending. Automation Orchestrator's functional test is explicitly waiting because
the owner currently has no OpenShift access. Another worker owns Command Center
on the shared TRA and another owns the additional RHEL configuration import;
their objects and running guests must be preserved.

## Verify source use cases before the successor deployment test — 2026-11-04

The owner clarified the order after the verified configuration acceptance
documented in `ce2ab03`. First exercise the source environment's remaining
functionality. Then pause its monitoring, TRA and testserver guests while keeping
the source AAP running to install and verify the successor. Building that next
environment is itself part of proving the source AAP's functionality, rather
than a capability that can be fully verified beforehand.

The protected capacity check accounts for all guest allocations and host
overhead. Additional Windows or Assistant test guests need their own allowance;
reclaimable cache and deduplication do not guarantee peak capacity. Paused
source guests retain their definitions and disks for restart. These are planning
and documentation changes, with no VM shutdown or allocation executed.

The first missing source functionality is tracked in `bead-wd-72f.33.1`: add
Claude installation and reuse both existing private MCP deployments through one
AIOps application entry point. Read-only runtime test preparation is tracked in
`bead-wd-72f.31.1`; it identifies actual targets and prerequisites separately from
the already successful configuration imports. Existing authentication, private
MCP and architecture approval boundaries remain in effect.

That read-only assessment also identified inherited Windows/Assistant runtime
targets, missing Orchestrator inputs and unverified login TLS, plus a missing
automatic AIOps per-instance preparation path (`bead-wd-72f.31.2`). Existing
website, monitoring and private MCP results remain valid. The assessment did
not launch those other runtime jobs or select a new writer/storage design.

## Verify remote and self-target AutoDeploy configuration — 2026-11-04

Portable implementation `a522e7b`, group/native-rule fix `1e89880` and trust/counter
fix `2ef4d42` now have normal configuration acceptance. Remote import 3296 added
fourteen AutoDeploy templates while retaining all fifty-five existing templates.
Refresh 3300 verified the five credential-forwarding flags from private
configuration `df6882a`, preserving every template ID and other setting. Existing
production-only objects remain on production and outside the receiving bundle.

Private correction `3104552` retains the existing environment Vault name in its
definition, fourteen template references and extraction dependency. The receiver
had no conflicting credential; its ID, secret inputs and assignments were
preserved. The exact name and ownership guards remain unchanged. All nine
remaining selector guards and six launch-credential plans passed in both native
modes using actual API metadata. Returned injector strings retain their native
unsafe treatment in those fixtures.

Normal receiving-instance selector 84 then succeeded on `8c5a05c`, with existing
prerequisite job 86 and importer 88 both successful. Independent readback verified
trusted source API access, actual running-job and self-target identity, exact
child credentials, shared token store and cleanup. All sixty-nine template IDs
and project, inventory, execution-environment, credential and label bindings
were preserved. No application or VM deployment was launched. The full successor
installation and independent recovery remain separate requirements.

Private capture `9647f70` also applies the inventory display rename and removes
twelve duplicate Windows fields plus two obsolete AIOps fields. Physical VM,
DNS, allocator and token identities remain unchanged; live legacy consumers
still retain their required variables. Normal AIOps refresh 3298 verified the
renamed lookup, existing runtime ciphertext, monitoring policy and website
activation. Monitoring jobs 69/72 verified fresh Linux/ICMP data and disabled
inherited Apache checks in place. AIOps problem guard `ba7785d` rejects recovery
and unknown events; general AI repair remains disabled pending the concrete
private-runtime prerequisites in `bead-wd-72f.33`.

The current Beads overview and full encrypted recovery records are refreshed
together. These documentation changes do not alter the tested runtime revision.

## Preserve receiving-instance trust during selected configuration setup — 2026-11-04

Implementation `2ef4d42` fixes the first authenticated request in the normal
self-target selector. The installed AAP resolves its public hostname to its
internal listener, as required by the existing installer configuration. Its
execution environment already receives the matching authority through the base
installation's trust mounts. Supplying a public-only file as the native HTTP
module's complete CA bundle replaced that valid runtime trust and rejected the
internal certificate before any child configuration job could launch.

Read-only inspection reproduced the actual cached execution image, network mode
and trust mounts. Its default trust and the installed instance authority both
verified the internal peer; the public-only supplemental bundle did not. Their
union verified the same peer. No HTTP credentials were sent during that probe,
and neither name resolution nor certificate validation was bypassed.

The selector now validates the declared supplemental CA, preserves the active
default PEM trust bundle and appends the existing source credential's CA material
in a private temporary file. Certificate and trust metadata are retained. Native
HTTPS requests and source SDK operations use that same scoped bundle, matching
the existing Python source client's additive trust behavior. Global trust,
installer host entries, source credentials and target authentication are unchanged.
Authentication now runs inside the existing cleanup block, and the later private
checkout reuses that workspace. Separate allocation results prevent a skipped
Ansible register from discarding the existing workspace and leaking its file.

The native configuration role also serialized a verified inventory counter as
canonical decimal text. The identity filter now normalizes that representation
locally, retaining physical VM, route, UUID, address, key and hypervisor checks.
It rejects booleans, floats, zero, leading zeros, signs, whitespace, Unicode
digits and oversized values without modifying inventory or token records.

Twenty-six focused tests passed: eight real TLS/native cases, thirteen selector
checks and five inventory identity checks. Fixtures cover both native modes,
default trust with an unrelated supplemental CA, declared private trust,
malformed/untrusted certificates, hostname and running-job rejection, actual
SDK launch/wait, private file permissions, workspace reuse and early-failure
cleanup. Syntax, strict production lint across six files, whitespace and
added-text privacy checks passed. A normal target selector retry remains the
separate end-to-end acceptance step; this implementation launched no job.

## Make AutoDeploy configuration portable between AAP instances — 2026-11-04

Implementation `a522e7b` follows the owner's decision to retain the four older
production stage templates and their history while excluding that family from
future configuration bundles. The same four playbooks remain behind the newer
stages. Read-only extraction now supports explicit reviewed source exclusions;
an excluded resource still referenced by a retained object stops extraction.
It does not delete the original source objects. The coordinated encrypted
capture changes also remove the original Machine key and clear saved targets;
their publication and normal import are separate deployment steps.

The existing selected-use-case launcher authenticates to its source using the
already injected API credential and verifies the actual running job before
launching its existing prerequisite/import templates. The destination uses the
existing instance-indexed token store. Self and remote targets share this path;
no installer-password lookup, temporary token, wrapper or additional store is
introduced. A receiving AAP's source credential must point to its own API.

Stage 01 now verifies the consumed primary reservation and exact guest identity
before the existing isolation helper grants public installation HTTPS and
guest-to-own-hypervisor API TCP 443. The existing Git/API publication transaction
persists that permission and placement across maintained encrypted captures.
Other guests, released clients and production protection remain intact. Failed
early publication restores exact prior runtime/permanent native rules; durable
publication remains available for an idempotent source-synchronization retry.
The existing base stage has a bounded installation-access repair tag that ends
before ordinary base configuration. Its launch must accept the requested tag.
Mixed destination/port cross products stop rather than add implicit grants.

Inventory display labels use the agreed format while the existing physical
VM name remains the allocation and token key. Verified `vm_resource` provenance
connects those identities for authentication, callbacks and retirement. An empty
saved stage key accepts the existing registered-route handoff. The main and
recovery inventories remain mandatory. An undeployed optional Hactar inventory
alias may be absent only with a genuinely empty query and verified administrator
visibility; present aliases retain identity checks and their canonical encrypted
policy still updates.

All 275 regression tests passed before the final two empty-key fallback changes;
the four focused alias tests then passed with native handoff coverage in both
Jinja modes. Both native importer-render modes, Stage 01/04 syntax, strict
production lint across 31 files, whitespace and added-text privacy checks passed.
Tests cover actual native task execution, exact permissions and rollback, real
encrypted Git publication/retry, physical/display ownership and read-only
exclusions. These results validate code and candidate rendering. A normal CaC
import, permission repair and complete independent recovery cycle require their
own live acceptance; this change did not allocate or remove a VM.

## Preserve activation variable text during repeat imports — 2026-11-04

Implementation `8c0af1c` fixes a formatting change at the existing activation
task boundary. A declared serialized empty mapping with its trailing newline
became a dictionary during Ansible templating. The native string argument then
contained different text, so an unchanged activation appeared to need an API
update. The disabled definition accepted that update; the running website
definition failed during the normal configuration refresh.

The task now explicitly preserves non-null values as strings. Null and omitted
values retain the native module defaults. The existing module, API transport,
enabled-state guard, Event Stream bindings and protected logging are unchanged.
Genuine definition differences still follow the native update path; no automatic
stop or restart is added to make an update succeed.

Read-only reproduction used the source execution image, Core 2.16.19 and
ansible.eda 2.13.0 with recorded GET responses. Preserved arguments produced no
writes for both real definitions, while deliberately changed variables still
requested an update. Eight focused regressions pass, including actual task
rendering in both Jinja modes, null/omitted values and native Event Stream/state
handling. Syntax, production lint and whitespace checks also pass. Live
acceptance is checked through the existing normal configuration import job.

## Configure each AAP instance's own hypervisor connection during base — 2026-11-03

Implementation `931edb8` follows the owner's explicit request to fix the
automation rather than rely on a manual firewall exception. Existing Hactar
base jobs correctly enforce empty-host or complete saved-VM recovery guards;
neither describes an already running hypervisor containing newly created CaC
guests. Those global guards remain unchanged. The normal AAP base stage already
has the selected primary ownership, pinned Machine connection and existing
encrypted/source publication credentials, so the necessary connection belongs
in that stage's existing inventory publication block.

The selected AAP identity must match its existing HTTPS approval, actual guest
UUID/disk/interface/network/lease and the pinned hypervisor. Every saved and
running guest definition is checked against enforced bridges and device
restrictions before changing only the guest-to-own-host management TCP grant.
The existing native firewall and atomic nftables isolation helper apply and
verify it. Local failure restores prior state; interrupted later publication
can retry only the exact independently derived permission. No new job, scope,
credential type, key, persistent store or installed service is introduced.

The same existing compare-and-swap callback independently reads primary AAP
ownership and updates encrypted recovery/shared/Hactar policy declarations and
their source API equivalents. Existing token records and unrelated use cases
are retained. Native Ansible testing also established why original play-level
credentials and policy must be captured before delegation: `vars_files` values
are not automatically available through `hostvars`. Protected, noncached job
facts carry those existing values through the pinned connection.

The already implemented Assistant importer was also registered in the existing
selection catalog using its existing project ID and configuration key.

Sixty-eight focused checks passed, including native effective SSH/delegation,
identity/device and policy guards, check mode, local rollback, real encrypted
Git with interrupted source synchronization, token reuse, decommission and
selection. Stage 04 syntax and strict production lint passed. These are code
validation results; live application and connection proof are separate normal
job outcomes controlled by the coordinator.

## Read application VM ownership from the existing source inventory — 2026-11-03

Implementation `f0a70c2` follows the owner's decision that AutoDeploy secrets
contain only AAP configuration and primary AAP ownership. Application CaC
belongs to its use case. Generic decommission therefore reads related ownership
from verified `vm_resource` data in the existing source AAP inventory, using the
already attached API credential rather than another repository/token/store.
Only decommission enables this read; ordinary registry lookup does not load the
API client or gain an API dependency.

The fixed encrypted shared capture identifies the inventory and pinned
hypervisor. Related names, counters, address, UUID, disk, MAC, bridge, machine ID
and keys must agree across the source row and its complete verified artifact.
Final publication independently rereads those records and compares them with
the same running job's protected preflight. Application ownership is retained
only in job memory and never written back to central allocation. Existing
credential types, job templates and ordinary import logic remain in place.

Optional guests can be undeployed, and later cleanup may find source rows
already deleted. Such absence requires no actual VM or either bounded disk
variant, plus verified surviving ownership of every remaining permission.
Unknown grants and tampered extant rows stop cleanup. Source policy aliases
are patched and read back before any guest ownership deletion; this preserves
the evidence needed if an API update fails. A fresh retry can reconcile a
lagging API policy only when removal of its verified selected identities yields
the exact encrypted desired policy, preserving all unrelated permissions.

All 63 focused cases pass: 16 key/source, 21 decommission and 26 allocation/routing.
They include real encrypted Git with AAP-only central data, API independence of
normal reads, foreign metadata refusal, absent optional roles, hidden disk
variants and fresh-job recovery after partial source deletion. Syntax, strict
production lint and added-text privacy checks pass. The coordinator also
verified actual source metadata with a GET-only lookup against an in-memory
AAP-only allocation. No destructive job or inventory naming change was run;
the separately coordinated private-data migration remains a distinct step.

## Keep complete ownership and retire only verified deployment permissions — 2026-11-03

Implementation `fc85d29` completes the selected deployment's permission cleanup
within the existing decommission job. The recovery layer protects restored
production state, so retirement must remove only the proven selected guests'
local and installation HTTPS permissions while preserving other clients and
normal isolation checks. Ownership preflight precedes shutdown; exact native
runtime/permanent rules and the existing atomic isolation policy are cleaned
before VM definitions and external resources are removed. Failed local application
restores the captured policy and stops before deletion.

The owner required retryable cleanup without a new service, state store or
publication phase. Decommission therefore accepts only the declared canonical
policy or its exact removal result derived from recorded guest identities. The
existing final Git/API action updates the maintained encrypted policy aliases,
shared and recovery captures, related guest rows and source inventory. It checks
all source targets before publication, preserves literal JSON variable wrappers,
shared credentials and consumed allocation history, and rereads concurrent state.
It refuses foreign identities, omitted selected grants and new permissions.

Future primary VMs now retain complete ownership automatically in the same
encrypted route transaction. Stage 01 first authenticates read-only through its
generated guest keys and pinned hypervisor jump, using the existing environment
login. Original-host variable references prevent delegation from losing the
route; effective connection overrides fail before authentication. Actual domain
and network XML supply exact UUID, disk, address, MAC and bridge evidence.
The allocator preserves other resource roles and refuses conflicting known
identity. This retains proof after a later partial cleanup has removed the VM
definition, without another registry or credential design.

The complete vendor-path suite passed 218 cases without skips. Subsequent guard
changes passed all 26 allocation/routing and 12 instance-key cases; the coordinator
independently passed 20 decommission and 12 instance-key cases before approval.
Both playbooks pass syntax and scoped strict production lint passes 12 files.
Tests include real encrypted Git, fake source APIs, native delegated SSH option
resolution, check mode and local rollback. No new VM or live decommission was
launched for validation; successful code publication does not claim those proofs.

## Register instance inventory alongside existing token publication — 2026-11-03

Implementation `3dd7f5a` uses the same approved base callback to register the new
instance in the existing encrypted shared inventory and source Controller.
Selection by instance name requires an explicit FQDN and hypervisor placement;
requiring a separate manual inventory update would leave a successful new token
unusable by project imports. The callback preserves other hosts, variables and
group memberships, including literal JSON tags, and places no token in inventory.
Existing Git writer, source API and Vault credentials perform this update.

The same implementation accepts independently declared exact local guest TCP
permissions in policy checks and published placement. Hactar applies those
permissions separately; AutoDeploy verifies the complete existing policy. Empty
lists preserve previous behavior and no automatic network grant is introduced.

Validation comprises 192 full-suite cases, eight publication/literal-tag
regressions and twenty allocation/routing cases, with production task lint.
Actual new-instance base publication remains a separate runtime acceptance check.

## Resolve delegated SSH settings from the original guest entry — 2026-11-03

Implementation `faf64bc` fixes proxy publication after successful AAP installation.
Ansible evaluates SSH connection variables in the delegated hypervisor's context,
but the selected instance route belongs to the original guest inventory entry.
Explicit `hostvars[inventory_hostname]` references retain that route and its exact
management address, account and port. The machine-ID guard and strict host-key
validation remain enforced.

The regression executes actual Ansible delegated connection resolution with the
route present only on the original entry and an isolated SSH fixture. Thirteen
TLS/proxy cases and production lint pass. A live publication-only retry then
succeeded, and independent checks confirmed trusted public HTTPS, upstream
authority/SNI verification and a valid nginx configuration. Temporary diagnostic
Job Template settings were restored afterward; installation was not repeated.

## Retry verified upstream publication without repeating installation — 2026-11-03

Implementation `ec1aed8` adds the `aap_upstream_tls` tag after the vendor installer
had independently returned zero and its installed Gateway passed a trusted local
HTTPS check, but proxy publication failed. The initial route selection and pinned
SSH setup always run. The tag excludes preparation, installation and the async
observer; untagged installation retains all phases. A real Ansible task-listing
fixture verifies this separation alongside existing TLS and rollback tests.

Only the non-secret machine-ID command has an opt-in diagnostic result. All
credential-handling tasks remain protected and diagnostics default to disabled.

## Verify configuration import separately from application execution — 2026-11-03

Rendering implementation `617fd15` and native TLS-input fix `f4c5b5b`, together
with an explicit native API request timeout and the existing reviewed PAH
prerequisite preparation, allow the AIOps configuration import to finish on a
fresh recovery controller. The prerequisite stage supplies only the approved
collection pins and retains existing content. Independent target API readback
checks the declared Controller and EDA resources, successful project syncs and
both activation definitions disabled.

This result establishes configuration deployment. It does not establish functional
remediation: the importer launches no application Job Template or activation.
Existing supplied API credentials and persistent EDA Controller access tokens
remain in place. No new deployment architecture or security exception is needed
for these focused corrections.

## Preserve native credential TLS flags in registered-instance checks — 2026-11-03

Implementation `f4c5b5b` converts the native credential's Verify SSL
value to an Ansible Boolean before applying the existing pinned DNS/TLS guard.
The managed credential injector emits `True` as a string; the guard previously
accepted Boolean true or lowercase `true`, causing prerequisite preparation to
stop despite enabled verification. The real guard is tested against native
Boolean/string inputs, disabled TLS and conflicting DNS answers. All eleven
routing tests and changed-task production lint pass. DNS pinning, IPv6 refusal
and trusted HTTPS remain enforced.

The same deployment iteration identified an omitted native credential Request
Timeout: its empty injected value fails the configuration role's numeric argument
schema. Explicitly setting the existing credential to ten seconds preserves its
token and grants. Current operator guidance also requires the existing reviewed
PAH prerequisite selection before first project import on a fresh controller.
This supplies declared collection pins without launching application workloads.

## Resolve resource templates when survey inputs are protected — 2026-11-03

Implementation `617fd15` fixes the first AIOps CaC import validation failure.
Controller marks survey values as protected text. Passing the entire variable
mapping into one Jinja normalization expression propagated that protection to
unrelated nested resource values, leaving an Event Stream organization expression
unresolved. A controller-side action now reads and renders only the declared
resource lists before existing validation. Explicit literal injector templates
remain protected; no validation rule or authentication behavior is weakened.

The failure was reproduced with the actual encrypted AIOps capture and protected
survey input in both templating modes. The fix passes all eleven importer tests,
including all five real captures, and the existing production execution image
with networking disabled. The failed live jobs stopped before CoP resource roles
and did not change target configuration. Live deployment remains a separate check.

## Name the temporary VM-registry writer explicitly — 2026-11-03

Implementation `0399e2a` uses the exact owner-selected credential name
`VM allocation git Pseudo CMDB writer` throughout current operator guidance.
The matching encrypted configuration uses this name for the credential and all
saved template/dependency references. The owner approved replacing the used
production credential with one of the existing `Cac_git_token_type`, then
explicitly chose deletion of the retired credential after the replacement is
verified. This supersedes the earlier proposal to retain that credential.
Job records, template IDs and workflow links remain; the unused test writer can
change type and name in place. Separate read tokens and grants are preserved.

## Use the existing Git type with a distinct writer token — 2026-11-03

Implementation `64a197e` follows the owner's decision to use `Cac_git_token_type`
for the separate allocation writer, with the replacement write token supplied
in encrypted shared base. Repository readers keep their own read-only tokens.
The writer uses `CAC_GIT_TOKEN`; allocation and extraction read the fixed
repository URL from encrypted project runtime configuration using the same
protected naming rule as registry reads. Launch variables cannot redirect it.
The extraction template therefore also needs its existing environment Vault.
Obsolete writer environment names and the old host-registry token fallback are
removed. No wrapper, extra credential type or repository permission is added.

All 173 regression tests and changed-playbook production lint pass. Actual
GitHub write-service authorization accepts the writer and refuses the reader
without changing repository state. Native fixtures cover concurrent encrypted
reservations, check mode, launch overrides, wrong Vault keys and secret logging.
The existing test-controller writer changed type in place, preserving its ID,
other objects and grants. Production rejects changing a credential's type when
it has job history; such a migration requires an approved replacement with
active assignments updated and the original credential retained for history.
The owner must approve creating that replacement. No VM or use-case job is run.

## Reuse the AutoDeploy CaC read token for registry reads — 2026-11-03

Implementation `328c982` follows the owner's approval to replace the separate
instance-registry reader with the existing AutoDeploy secrets repository read
credential. The registry action uses `CAC_GIT_TOKEN` and derives its fixed
repository from encrypted project runtime configuration, so launch variables
cannot redirect the token. Preparation retains its saved repository pair and
adds only the registered Machine credential. Existing ownership pins remain.

The existing read token successfully read the current registry ciphertext.
Real Ansible/Git fixtures verify encrypted configuration, rejected wrong keys,
ignored launch namespace overrides and preserved host routing. The full suite
passes 171 tests; production lint and source checks pass. Five live consumer
definitions and companion dependencies follow the same credential selection.
The allocation writer and token permissions are outside this change.

The owner separately requires a real CMDB instead of the temporary Git/YAML
registry. That requirement is tracked in `bead-wd-sc8` and the work plan; no CMDB
product is selected or implemented by this change.

## Use the repository CaC Vault for registry encryption and decryption — 2026-11-03

Implementation `eb6b214` follows the owner's explicit instruction to reuse
`aap_autodeploy_configascode-secrets CaC vault cred` for the instance registry.
Preparation retains that saved credential and adds only the registry reader
and pinned Machine credential. The selector no longer selects a separate
registry Vault. Existing repository-pair ownership checks remain in place.

The maintained shared password decrypts the current registry without changing
its ciphertext or reservation history. Real Ansible/Git fixtures read a registry
with only its `cac` key and refuse an unrelated key. Forty-nine focused checks,
selector syntax and production lint pass. Companion configuration stops creating
or attaching the redundant Vault entry. No credential object is deleted and no
key is rotated; custom Git credential types remain unchanged.

## Use direct project selection and explicit CaC deployment names — 2026-11-03

Implementation `b5fb34b` removes the five unused wrapper playbooks. The owner
requires every project Job Template to call `deploy-cac-project.yml` directly
with its fixed `aap_cac_project_id` in saved Extra Variables. Controller readback
confirmed that no production template referenced the wrappers.

The owner also requires a Deploy prefix. Because an existing application job
already uses an otherwise matching deployment name, the owner chose
`Deploy <Project Name> CaC` for all five configuration templates. The naming
helper, existing selector tests, documentation and encrypted references follow
that rule. Existing IDs, credential pairs and workflow relationships are retained.
Twenty-four focused checks and syntax checks for the importer and selector pass.
Compatibility layers are not implied by this design and require consultation
before being added. No use-case import or application deployment is run here.

## Propose one shared CaC importer without hiding preparation — 2026-11-03

Analysis `96ce498` compares all five importers, the selector and shared helpers
with installed CoP/native implementation. Ordinary resource data, different
capture layouts and duplicated authentication/cleanup do not justify separate
import engines. The proposed replacement is one resource-driven playbook, with
normal schema adapters and only demonstrated resource-level compatibility
handlers. Event Streams and workflow graphs are already supported; EDA project
field forwarding and asynchronous group ordering need specific attention.

Durable target service tokens require discovery, safe persistence and recovery;
native token creation alone is not idempotent and does not replace that policy.
Preparation, model authentication maintenance and child-job orchestration remain
explicit boundaries. One playbook also does not resolve credential injection:
repository pairs and destination API access must be bound before launch. Thin
repository templates can share the playbook until the owner agrees the pending
credential, self-target and orchestration design under `bead-wd-72f`.

Local role/module inspection and a synthetic zero-API activation probe identified
a disabled-state compatibility risk, tracked separately as `bead-wd-72f.4`.
This is not evidence that a live activation changed. The analysis also identifies
conditional secret logging to eliminate in any common path. Sixty-one source
links, an illustrative YAML schema and four version-policy checks pass. No
consolidation, runtime change, AAP job or live credential operation was performed.

## Bind configuration access to each repository — 2026-11-03

Implementation `7e5f672` and encrypted capture `4ab587f` replace the shared-entry
bootstrap with five independently named read-token/Vault pairs. Production
readers were renamed in place; the existing base Vault entry was retained and
four repository Vault entries were added with the same ownership/grant boundary.
The four use-case importers now bind their own Vault, while base stages, catalog
and extractor retain base access. The existing fresh instance has all five pairs
without changing runtime Vaults, registry access, token inputs or credential types.
All fourteen affected production template assignments, role grants, workflow
nodes, schedules and surveys were verified. Actual selector checks pass for every
importer and preparation using the encrypted pins. Eight bootstrap checks and ten
selector checks cover both native modes; generic regression checks and impacted
production lint pass. No import, deployment, rekey or target API redesign ran.
The corrected commented example provisions all five pairs in the local fixture.
The encrypted migration record preserves genuine before/after evidence; historical
names there do not define current bindings. Future multi-repository extraction
key routing is tracked separately as `bead-wd-72f.2`.

## Store the API DNS name explicitly in inventory — 2026-11-03

Source documentation `9003fb4` and companion capture `720710d` define an explicit
`ansible_fqdn` host variable for AAP instances. The owner confirmed that the
numbered instance in the request was an example, so only the existing verified
inventory entry was updated. Its DNS name comes from its already-recorded HTTPS
origin; no new VM, guessed suffix or remote fact gathering is involved.

Live readback and a decrypted comparison against the previous capture verify
that only this host variable was added. Other variables, group memberships,
capture records and literal tags are preserved. The public example parses as
YAML. The intended future lookup is launch-time instance name to stored FQDN to
verified HTTPS origin. This data update does not replace the existing registry
launcher or implement credential selection; that remains the next discussion.

## Limit this phase to inventory placement and future upstream TLS — 2026-11-03

Implementation `aaafed2` follows the owner's explicit stop boundary. Keep the
instance name as a launch-time input and add per-hypervisor VM placement groups
whose `hypervisor_host` variable resolves to an existing host in the shared
inventory. Companion capture `e3a171b` preserves original variables and functional
memberships. Existing aliases are retained to avoid colliding with service group
names. Actual Ansible inventory parsing verified all nine mapped VM entries.
Credential bindings, use-case execution, API delegation and replacement workflow
implementation are deferred until credential management is agreed.

The owner retained public UI/API access and prohibited production SSL changes.
Future Stage 02 therefore publishes a temporary 503 frontend until installation
provides the guest's public CA bundle through pinned SSH. Stage 03 verifies guest
health against that installed authority, binds nginx to the selected hostname and
CA, validates before reload and restores the prior instance configuration after
a publication failure. The small standard-library probe verifies a private
upstream address with its DNS certificate identity without changing DNS, global
trust or sending API credentials.

Eleven focused cases pass in both templating modes, including real TLS refusal
paths, real Ansible publication/rollback and validation-before-reload ordering.
Both nginx states pass in-memory syntax validation with the installed binary;
the infrastructure/install entry points and full trust task syntax pass, as does
scoped production lint. No existing proxy configuration or service was changed,
and no deployment job or fresh VM installation was run.

## Keep selected setup's seed identity and trust separate from its target — 2026-11-02

Implementation `0684007` fixes readiness failures found before the first selected
AIOps import. The execution environment lacked the seed's existing private
issuer, and source authentication inherited the fresh target's base password.
The selector now requires an explicit encrypted seed login. It reuses the
existing source CA file for source authentication, reads, job launch/wait and
temporary-token cleanup. Certificate/hostname validation stays enabled; the
target retains its normal trust and login. No global trust or DNS change is made.

Two existing source credential associations have no organization. Exact
encrypted source-local name/ID/type pins permit those already-reviewed inputs
without changing ACLs or moving credentials. Registered route credentials still
require the expected organization, and case Git/Vault boundaries are preserved.
These narrow source pins do not resolve the separate universal ownership design.

Four real-module TLS fixtures pass in both templating modes, covering verified
launch/wait/cleanup and secure refusal paths. Selector and login regressions,
syntax and production lint pass. Actual source/target API prechecks and scoped
credential calculation pass, with temporary-token revocation verified. The local
preflight used protected captures/route state and independently verified DNS
answers; it did not run registry Git fetch, private clone or child jobs. No
prerequisite, AIOps configuration import or application execution is claimed.

## Verify the AIOps companion cutover after scoped token input — 2026-11-02

Companion implementation `30aecfd` moves AIOps platform CaC to its own private
repository. The capture published in `2a22fbc` is byte-identical to its former
shared copy, including the Vault identity and all configuration values. The
operator supplied a dedicated read-only token; its verified repository read and
inability to read shared base precede legacy-copy removal. Encrypted base stores
that token, repository URL and independently named Git credential.

The seed importer changed only its repository default and Git association.
Its other survey/launch settings and Vault inputs, plus the separate preparation
and selector templates, were verified unchanged. Five encrypted capture bindings
and one external credential dependency changed; shared catalog/registry and
allocator bytes were preserved. Bootstrap implementation `3b6d48f` supplies the
optional credential on later base runs without replacing existing hidden secrets.

No AIOps import, activation or application job ran. The separate runtime
`myvars` remains in the public AIOps playbook repository; this verified split
concerns platform CaC. The broader ownership architecture remains undecided.

## Provision independent AIOps configuration access — 2026-11-02

Implementation `3b6d48f` adds optional `cac_bootstrap_git_credentials.aiops`
support to base bootstrap. It creates the independently named AIOps Git-read
credential while preserving the four existing Git inputs, the shared Vault
identity and existing hidden secrets on reruns. The CoP roles themselves are
unchanged. Six real local Controller/API fixtures pass in each native mode,
including the legacy path, the new credential and refusal of a masked input.
Stage 04 syntax and scoped production lint pass.

The owner requested a separate private companion repository for AIOps. Its initial
capture publication `2a22fbc` preserves the exact ciphertext and configuration
values from the existing shared file. The public playbook repository needs no
private Git token. The existing fine-grained base token can read its original
repository but cannot read the new companion, so a new repository-scoped read-only
token must be supplied through encrypted base. No broader credential is used as
a substitute and no existing token is replaced.

At this checkpoint the live importer and legacy capture are retained until the
new token is verified. Prepared repository/name bindings preserve the shared
catalog and allocator registry and pass encrypted roundtrip/literal-tag checks.
No AIOps import or application execution is claimed by these source changes.

## Keep complete object ownership open after the label audit — 2026-11-02

Documentation commit `1846f71` adds the requested TODO entry and API/UI label
capability table. The original idea was to use labels to map all CaC objects to
their owning project. Read-only API responses and the served UI code establish
that several resource types have no labels at all, while some API-supported
labels have no overview filter or only conditional launch controls. Labels
therefore cannot be the universal ownership mechanism; existing useful labels
are retained.

The owner requested new ownership ideas. Beads `bead-wd-72v` remains open and is
mirrored in TODO.md. It asks for comparison of an encrypted registry, supported
description markers, existing project/parent relationships and a hybrid approach.
The eventual design must handle shared resources, uncaptured manual additions,
renames, removals and changed runtime IDs across deployments, while preserving
CoP compatibility and secrets. No alternative has been selected or implemented.

The README links the backlog. Four existing version-tool tests, whitespace checks,
mirror equality and a changed-plaintext identity scan passed. These are
documentation and version changes; no deployment, extraction update or live
metadata modification was performed.

## Verify actual base configuration after protected tag repair — 2026-11-02

Actual base retry 3144 on source `59aa985` and encrypted base `f38a8cf` succeeded
in 125.097 seconds. Independent strict public-TLS administrator login, reserved
node identity, expected organization/types/base credentials/PAH repositories and
absence of advanced use-case objects were verified. Temporary run tokens were
removed. The fix in `4af4121`/`bef8921` required only the base retry; VM creation
and installation were not repeated. Follow-up optional captures restore 44
injector tags (AutoDeploy 4, Hactar 3, Windows 8, Assistant 29); actual vendor-role
local checks preserve every schema value and hide canaries without API calls.
Companion implementations are `0f42c79`, `ef849c5` and `0954190`. No live optional
import, credential refresh or AIOps change was performed.

## Preserve literal tags as part of encrypted YAML correctness — 2026-11-02

Actual fresh base configuration failed in the exact CoP wildcard merge. The four
new credential injectors were evaluated as playbook variables because ordinary
AnsibleDumper discards `!unsafe` markers, even though string equality survives.
Implementation `4af4121` adds a protected dumper and validates literal-tag paths
after Vault roundtrip; companion `bef8921` protects only the four base injector
scalars. Ordinary environment references and all logical values remain unchanged.
The actual encrypted base/myvars merge fails before and passes after locally
without APIs. Canary fixtures cover both native modes, and all 31 generic capture
fixtures pass. Protected logging remains enabled. Broader lint retains four
existing line-length findings in unchanged tasks; actual Stage 04 retry is pending.

## Verify the installed extractor with a real protected preview — 2026-11-02

Actual template 158 default preview job 3139 on `f38517a` succeeded in 44.042 seconds.
It reported zero conflicts/validation errors, retained a decryptable Vault review,
and performed no Git publication. The missing accepted baseline is explicit:
373 initial source/desired differences and seven code-graph differences need
review before initialization; they are not changes since a previous extraction.
The used reader remains intact beside the separately installed CA attachment.
The implementation and meaningful merge/deletion/secret fixtures are verified;
no actual baseline acceptance or update was authorized or run. Independently
read vendor common-role tasks/defaults also confirm Podman belongs to bundled
installer package setup, so its earlier absence does not require manual packages.

## Verify refined preparation readiness on the actual guest — 2026-11-02

Actual observer job 3135 on source `6932ebf` succeeded in 16.308 seconds:
preparation readiness passed, the supported expansion dry run proved available
capacity, and bundle/account/resource/tool checks passed. Strict HTTPS handshakes
verified all three declared endpoints; the two Red Hat services used already
installed RHSM authorities and no client credentials. Current installer readiness
remained false for unexpanded temporary space and the absent container runtime.
Infrastructure job 3133 independently succeeded. Implementations `3706770` and
`ba20ce5` preserve the preparation boundary; no complete AAP installation is
claimed. The broader local 122-test suite and additional already-installed
collection fixtures passed as documented in release notes.

## Capture custom credential schemas with their retained dependencies — 2026-11-02

The separate-CA fixture exposed a missing stable-field allowlist for custom
credential types. Implementation `04316b8` serializes name, description, kind,
inputs and injectors while omitting runtime IDs/management flags. The fixture
proves alias resolution, retained CA/type after removed associations and preserved
vaulted PEM input. Thirty-one generic fixtures pass. The actual separate CA-only
type/credential was created successfully and attached beside the untouched used
reader; no grant or global trust changed. Actual extraction preview is the next
required proof, and no initialization/update is claimed.

## Preserve used credential schemas and attach source trust separately — 2026-11-02

Actual Controller validation also refused input changes to the already-used
reader type. No live type or credential changed. Implementation `988d172`
retains that URL/token schema and provides a separate CA-only credential whose
required PEM uses the supported single-file injector. The capture restores the
original reader exactly, adds the separate credential/type and fourth extractor
association, and retains its dependency/alias. No access grant, deletion, global
trust or Controller constraint bypass is involved. Thirty generic fixtures pass;
actual creation and preview remain parent coordinated.

## Verify preparation results before starting installation — 2026-11-02

Implementation `ba20ce5` follows the observed copied-disk readiness gap: the
existing growth steps now validate the exact supported layout, refuse actual
errors, accept only explicit growpart NOCHANGE for idempotence, and require real
temporary capacity before subscription or installer tasks. The installer observer
path still skips preparation and starts no second installer. Starting a new async
installer is explicitly marked changed. Strict Stage03 production lint passes;
live preparation remains parent coordinated.

## Assess work at the phase that owns it — 2026-11-02

Actual guest verification found a correct bundle, supported root layout and
sufficient virtual disk, while the copied root partition remained small and a
container runtime was absent. Implementation `3706770` separates preparation
readiness from current installer readiness. A read-only growth dry run proves
whether existing preparation can supply temporary capacity; missing runtime tools
and vendor package-task references remain explicit. Red Hat probe retries use
only already installed configured RHSM authorities, with certificate/hostname
checks, bounded errors and no client credentials. Five audit fixtures and strict
production lint pass. This change neither installs packages nor grows filesystems,
and the subsequent actual audit must still verify preparation readiness.

## Follow the actual Controller single-file injector contract — 2026-11-02

The actual credential-type PATCH rejected a named-file mapping before any
credential changed. Implementation `652ca05` supplies the supported single
string `file.template` and `tower.filename`. A canonical portable schema and
strict Jinja rendering fixture cover missing, empty and populated optional PEM
inputs. The encrypted capture/private migration payload use the same definition.
This corrects API compatibility without changing trust or source identity.

## Reuse the existing source authority within the collector context — 2026-11-02

Encrypted execution-environment evidence proved the same source peer as the
trusted local route and missing issuer trust. An independently located issuer
already trusted by the workspace verified the same leaf with hostname checking
and no HTTP credentials. Implementation `1cfb86b` accepts that existing
authority through an optional credential file, added only to the collector SSL
context alongside default roots. Global EE trust, DNS and host files remain
unchanged; origin, redirects, certificate/hostname checks and invalid-input
refusal remain enforced. Twenty-nine generic fixtures and strict entrypoint lint
pass. A subsequent actual preview must prove extraction; no baseline acceptance
or repository update was performed by this change.

## Audit bundled installation readiness before guest changes — 2026-11-02

Implementation `e53878f` extends the existing registered-instance observer,
using its authenticated pinned jump route. It reads the configured installer
bundle, nonroot installer permissions, root layout and capacities, tools, OS and
resources, and tests credential-free verified Red Hat HTTPS handshakes. Protected
subscription/login inputs must be present without disclosure. Sizing follows the
local AAP 2.7 installation reference. Unsupported filesystem layout blocks the
existing fixed growth commands; it is not guessed or changed. The observer does
not benchmark IOPS, authenticate to Red Hat, register subscriptions, install
packages, grow disks or start the installer. Three fixtures and strict production
lint pass. Actual guest audit remains a separate parent-coordinated job.

## Declare narrowly approved installer HTTPS separately from target identity — 2026-11-02

Implementation `c365298` validates explicitly approved bridge/IPv4/MAC clients and
protected source addresses independently of the immutable registered hypervisor
pin. The default bridge/DNS policy remains unchanged; persisted host exceptions
are never treated as approval. The encrypted inventory capture retains the same
explicit declaration, verified against the approved host configuration. Seventeen
routing/allocation fixtures and scoped production lint pass. The same checkpoint
refreshes only the authorized DNS credential from its maintained encrypted record;
Vault roundtrip comparison proves every other environment input unchanged. This
is deployment readiness, not proof that infrastructure or installation ran.

## Collect encrypted TLS route evidence before changing trust — 2026-11-02

Actual execution-environment preview confirmed certificate trust failure while
the same source-reader inputs verified locally. Implementation `3eb4edf` retains
only encrypted DNS/host-file/trust-path and verified-SNI peer evidence after that
failure. Diagnostic probes send no HTTP/API credentials, accept no untrusted
certificate and change no DNS or trust policy. Evidence must be compared with
independently trusted source identity before choosing a repair. Tests prove zero
diagnostic HTTP requests, unchanged certificate/hostname verification and Vault
encryption of failure artifacts; all twenty-eight focused fixtures pass.

## Keep certificate package ownership in shared baremetal base — 2026-11-02

The user clarified that certbot and its nginx plugin serve several hypervisor
applications and belong in Hactar's shared base OS. Implementation `a184012`
therefore adds only a read-only installed-RPM readiness check to infrastructure,
after exact hypervisor validation and before certificate/account checks. Missing
packages produce a clear base prerequisite failure. AutoDeploy installs no
packages, registers no new account and preserves the legal approval guard.
Infrastructure syntax/scoped strict production lint pass; live installation and
certificate proof remain parent-coordinated.

## Classify actual Controller GET failures without exposing requests — 2026-11-02

The next real preview reached a controlled Controller-read refusal. Exact source
reader inputs verified successfully through local trusted TLS, so implementation
`b2c5366` distinguishes endpoint family and HTTP status from TLS trust, DNS and
connection failures in the execution environment. URLs, query values, server
error bodies and authentication headers remain protected. Twenty-seven focused
tests pass, including HTTP/TLS secret-canary failures. Runtime extraction remains
unproved until a later actual preview succeeds; no baseline/update was run.

## Preserve protected diagnostics through actual Ansible task execution — 2026-11-02

The first real extractor preview failed before its protected action could report
an actionable reason. Raised `AnsibleActionFail` bypassed the task's
`failed_when` handling, leaving only censored output. Implementation `09fe5a9`
strictly normalizes Boolean survey strings inside the action and returns bounded
refusals for the separate public failure task. Protected source/Vault/Git inputs
remain under `no_log`; unexpected failures expose only a controlled stage and
exception class. No access, checksum, TLS or Vault control is relaxed.

A real entrypoint fixture runs through Ansible task templating in both native
modes, covers false/false, false/true and true/true publication choices and proves
the safe reason reaches the failure task without the secret canary. All twenty-six
focused tests pass. A subsequent actual preview is required before declaring
the installed extractor operational; no baseline initialization/update was run.

## Resolve portable credential namespaces before fresh import — 2026-11-02

Implementation `e8ab5ac` and companion `0c1cc64` align shared external aliases and
the five new isolated recovery/observer definitions with the environment Vault
name actually created by the captured use case. The earlier manual capture kept
the source-only name for those references, which would be unavailable on a fresh
controller. Actual seed credential IDs/scopes are preserved; only encrypted
blueprint references change. Every one of nineteen templates now resolves its
credentials against actual captured or base-bootstrap definitions. Twenty-five
focused fixtures pass, including portable external-alias recognition.

## Preserve accepted association intent when source membership changes — 2026-11-02

Implementation `5583f42` applies unordered association and workflow-node deltas
to accepted desired state. A source credential removal must not discard portable
writer/Vault associations that intentionally exist only in CaC. Desired-only
members and excluded source nodes retain their baseline intent. Arbitrary lists
inside variable/input mappings keep meaningful order even when their keys are
named like Controller associations. Retained dependency metadata is name-sorted.
All twenty-five focused fixtures pass, including both regressions and real
encrypted Git update/removal behavior. No production baseline/update was run.

## Review complete owned state before updating encrypted CaC — 2026-11-02

Implementation `055b9dc` adds `capture-aap-cac.yml` and bounded Controller API
adapters. The existing exporter requires an additional dependency and does not
provide the accepted-source/accepted-desired merge or complete-visibility deletion
contract, so this path uses the existing Python/Ansible runtime and GET-only
transport. Every source/related URL is pinned to the exact TLS origin and
Controller prefix; redirects, incomplete pages and nonadministrator visibility
are refused. Owned project/label families discover additions without an old ID
list. Stable names and parsed YAML/JSON variables exclude runtime noise.

Separate encrypted source and desired baselines preserve intentional namespace
differences, exclusions and pending desired edits/deletions. Removals include
resources and associations. Conflicting changes require review, and masked new
secrets need recoverable inputs. Existing masked secrets and reordered password
survey defaults keep their vaulted values; masked rotations remain unknowable.
Accepted dependency names remain owned independently of job associations, so an
unlinked but existing definition is not mistaken for a deleted resource.

Reviews bind actual code revision/content and validate own playbook paths. The
base graph is compared through its narrow code-owned adapter; changes requiring
source adaptation block acceptance. No arbitrary playbook AST rewrite, source
configuration apply or application job launch occurs. First initialization and
updates require an exact fresh review digest. Encrypted Git publication is
explicit, refuses unrelated staged work, never force-pushes and excludes the
allocator-owned state file.

Companion `77e7cf3` stores the initial encrypted AutoDeploy ownership adapter,
source-reader/type and preview-default extractor definition, bringing its capture
to nineteen templates. Other scopes state their missing adapter boundaries;
saving those definitions does not prove live AAP installation. The 116-test
regression passed and all 23 focused tests pass in both native modes. Scoped
strict lint and syntax pass. Local production GET-only preview succeeded without
publication or AAP mutation; accepted baseline initialization and actual AAP job
availability remain separate runtime steps.

## Pin selector authentication origins — 2026-11-02

Implementation `85e7307` and companion `4593bd6` require the orchestration seed
to match the encrypted reviewed origin and require catalog access to match the
registry-reader credential's repository before authentication. This keeps
operator survey values from redirecting protected seed/Git inputs. Nine selector
tests pass; target instance and scoped credential selection remain unchanged.

## Match captured prompt policy to the guarded selector — 2026-11-02

Implementation `70b1661` and companion capture `3daa17e` disable arbitrary
variable prompts on all six existing configuration importers. The bounded
surveys stay enabled and credential prompting is retained for the selector's
validated scoped associations. Parent API readback found the earlier live/capture
setting was permissive and would fail the selector's existing guard. A real
preflight fixture now rejects that mismatch as well as missing target questions.

## Complete surveys that previously exposed diagnostics only — 2026-11-02

Parent API preflight found three importer surveys that had only the logging
question, so renaming an existing URL question did not add the required instance
key. Implementation `17c5efb` adds a capture preflight for every fixed importer;
companion `729b3f2` gives all six required key/repository/debug prompts and removes
stale saved target URLs/addresses while preserving other scoped inputs.
Nine selector/label tests pass, including real missing-prompt rejection and a
complete-survey acceptance fixture. No use-case import was launched by the fix.

## Select registered targets without replacing case credentials — 2026-11-02

Implementation `c1d60b7` replaces free-form target URL surveys with an exact
completed registry key in the selector and standalone configuration importers.
Every importer derives its public API and private SSH route before connecting.
The selector verifies the saved non-Machine credential names/organization,
preserves their Git/Vault boundaries, adds only the fixed registry dependencies
and registered Machine, and verifies actual completed job associations/results.
A distinct `instance_registry` Vault identity avoids collisions with a case's
`cac` secret. Credential prompting is limited to these validated setup launches;
free variable prompts and application job execution remain disabled.

Companion capture `cbe5b7a` retains eighteen templates, including separately
bound recovery phases and a read-only observer, with their exact protected
inventory/host/group and recoverable Machine dependency. Optional captured
groups are restored without broad inventory rewriting. All template labels are
defined. Allocator-owned runtime state is unchanged.

API checks additionally reject alternate IPv6 records and disabled TLS overrides
because either could send credentials outside the pinned IPv4 route. The full
95-test regression passes; sixteen routing/allocation and nine selector tests
pass in both native modes, including distinct Vault identity and credential
removal/substitution refusal. Ten entrypoints pass syntax checks and scoped
strict lint passes; broader prerequisite lint retains four older line-length
findings. Actual isolated creation and read-only guest login/sudo succeeded,
while certificate issuance, installation and selected setup remain unproved.

## Verify authenticated guest access separately from installation — 2026-11-02

Implementation `0079680` adds a read-only registered-instance observer. A strict
host-key handshake establishes the peer key, while guest login and sudo require
their own proof. The observer uses the same protected route and attached
environment/Machine credentials, reads minimal facts and both machine-ID paths,
and retains bounded identity evidence for comparison with protected golden/source
records. It changes no machine identity, package, filesystem size or subscription.
Syntax and scoped strict production lint pass; actual login results must be
reported separately from this source validation.

## Bind later setup to registered routes — 2026-11-02

Implementation `b780524` makes Stages 02–04 resolve one completed instance from
the latest encrypted allocation registry before target connections. A separate
read-only credential avoids replacing a use-case's scoped configuration token.
The instance key determines the VM name, private address, public API URL, SSH
public keys and hypervisor; conflicting workflow/caller values stop execution.

Private subnets may overlap across hypervisors, so guest installation and
installer-password/MCP observers always jump through the pinned hypervisor with
strict host-key checks on both hops. API authentication uses this VM's public
hostname only after exclusive DNS and trusted TLS checks. Infrastructure reads
the exact reserved DNS record and refuses an existing conflicting address. It
uses the pinned hypervisor public address and limits proxy/certificate paths to
the reserved hostname. Existing certificates or separately approved ACME
registration are prerequisites; this stage never accepts new terms.

Fifteen allocation/routing tests pass in both Jinja native modes, including real
Git-backed read-only lookup, stale/unknown-target refusal and delegated inventory
routing. Stages 02–04 pass syntax checks; Stage 02 and route tasks pass scoped
strict production lint. These local checks do not prove certificate issuance,
installation or base configuration on a real target.

## Reserve shared names before isolated recovery provisioning — 2026-11-02

Implementation `98f491a` replaces independent local allocation with normal
conditional Git publication into a separate encrypted allocation-state file.
The owner requires globally unique test names across hypervisors and no reuse
after failed provisioning. Old counters remain migration evidence. The state
file is separate from ordinary CaC so later capture updates cannot reset it.
Encrypted companion change `8bebb0a` seeds the reviewed floor and defines the
portable writer in shared base without an optional recovery-case dependency.

The isolated Stage 01 verifies SSH keys, physical identity and live persistent
isolation before reservation and again before startup. It changes only a newly
copied disk, generates fresh guest SSH/machine identities, cleans only its local
copied RHSM identity with appliance networking disabled, and observes its exact
local libvirt domain. Public trust/routing artifacts survive later job failure;
the complete route is retained in the encrypted registry.

Thirteen tests pass in both native modes, including competing real Git writers
and the native action with distinct default/cac Vault passwords and check mode.
Workflow artifacts, Stage 01 syntax and scoped strict production lint pass.
This checkpoint permits only independently bound isolated Stage 01 execution.
Later installation/API routing and live provisioning proof remain separate;
older unbound downstream stages must not be chained automatically.

## Match Controller survey default types — 2026-11-02

Implementation `725e33d` fixes empty multiselect defaults to strings after the
actual Controller API rejected an empty list. The shared importer preflight now
refuses that invalid shape, with real Ansible regression fixtures. Encrypted
capture correction `e5d61b3` matches the accepted/read-back selector and
prerequisite surveys. This metadata correction launched no configuration jobs.

## Keep base deployment separate from selected use cases — 2026-11-02

Implementation `2338422` stops the deployment workflow after stages 01–04.
The owner explicitly chose platform base first, followed by an operator-selected
mechanism that installs selected umbrella Projects and their Job Templates/
related CaC. The selector uses only fixed owned configuration importers, preserving
each importer's scoped Git/Vault credentials. It verifies separate seed/target
instance identities and actual child-job completion. Four umbrella modules have
reviewed captures/importers; six report their missing capture/importer explicitly.
The two standalone projects outside umbrella membership are not silently added.

Every importer now checks project label assignments and organization-scoped
label definitions. Selected prerequisite preparation remains outside base;
AIOps imports leave activations disabled. Encrypted central capture `205e2da`
adds the selector definition and standalone recovery objects; Windows `57ca87e`
adds its regression verifier and labels. Assistant changes `ae00634` and
`4962934` complete ordinary and separately gated maintenance labels.

All 79 repository tests pass. Eight new safety/label tests pass in both native
modes, the modified entrypoints pass syntax and new YAML passes strict offline
production lint with zero findings. Private roundtrips/comparisons preserve
unrelated secret inputs. These are local code/capture changes; no live selector,
configuration import, application job or fresh deployment ran.

## Keep a Git-tracked session restart entry point

Documentation implementation: `fa10dfd`.

The operator requested RESTART_HERE.md in Git so a new chat can recover this
project's goal and find its plan, setup and decision history. The README links
to that entry point. It documents that the existing backlog has not yet been
migrated to Beads and directs subsequent tracking there; it does not create a
second task list. It contains no secrets or environment-specific access values.

Restart-document links, version consistency, whitespace and staged-content
checks passed. No automation or deployed configuration changed.

## Document the AD runtime proof separately from configuration import

Windows presenter guide: `0b46f96`; service identity checks: `60a8531`.

The receiving-platform import restored the definitions and target credential;
separate runtime stages then verified applicable Server patching, directory
promotion, identity nesting, synchronized time and LDAPS/gateway trust. The full
live verifier passed all twelve logins, 48 scoped grants, 192 regional access
checks and twelve completed mock jobs. Documentation now links the beginner
VNC/browser presenter guide and explains that AD selects membership while
Ansible maintains AAP resource grants. No importer behavior or encrypted capture
changed for this documentation update. Complete fresh infrastructure deployment
and live membership revocation remain separate proof.

## Verify trust from certificate files with Unicode comments

Implementation: `e9e892a`; encrypted project refresh: `e4f2d29`.

The installed public bundle contains Unicode comments, which Python's inline
PEM interface rejects. Loading the installed certificate files preserves the
full bundle and required HTTPS chain/hostname verification. That check passed
in the focused import, which subsequently succeeded after the Windows project
was refreshed before template validation. Independent API reads confirmed all
32 templates, 29 nodes, target binding and file injectors; the imported static
verifier also passed all 48 regional grants. Infrastructure provisioning and
LDAP login verification remain separate from configuration import.

## Diagnose the public trust read while protecting authentication

Implementation: `4772b6b`.

The initial refreshed Windows import stopped during public trust collection.
The existing diagnostic choice now exposes errors from that public-data command
while passwords, decryption and credential writes remain protected. The retry
identified Python's inline PEM interface rejecting non-ASCII comments in the
installed CA bundle. A transient PAH service error also interrupted a source
sync; the existing PAH endpoints recovered and remained the collection source.

## Reuse installed platform trust for the AD target credential

Implementation: `1f75e14`; encrypted Windows capture: `6d2c9c4`.

The platform's own issuing CA can live in its installer-generated trust bundle
rather than host trust alone. Read both public bundles over the existing SSH
connection and require normal HTTPS chain and hostname verification before
storing the target credential. Reuse the established containerized-installer
trust path, allow an explicit protected override for another verified layout,
and supply existing sudo authentication. No certificate checks are disabled.
Python/YAML parsing and importer syntax passed. The capture's actual CoP
combination verified fresh target bindings and deferred credential injectors;
live import and infrastructure deployment remain separate validation.

## Bind Windows AD configuration to the receiving platform

Implementation: `e6bf9bd`.

Fresh Windows imports must configure their own platform rather than reusing a
dedicated validation instance's API and SSH settings. An optional encrypted
capture flag prepares a target-specific credential using the existing installer
SSH connection, public trust and the current administrator identity. HTTPS
hostname and chain validation precede credential creation. The importer still
restores definitions only and rejects launches and schedules. Syntax, Windows
configuration guards, group-ordering and version-policy tests passed; live
AD deployment and a fresh-target import remain separate proof.

## Consolidate the current work plan and separate completion from proof

Documentation implementation: `591fc43`.

The operator requested an understandable TODO list with context, reasons and
completion goals, and completed work at the document bottom under `Done:`.
Older lists mixed historical design, completed implementation and unverified
behavior. PLAN.md is now the single task list, with numbered areas/subtasks;
the overview and README link to it instead of maintaining competing checklists.
Earlier plans remain recoverable in Git and this decision history.

Completion was reconciled with the protected deployment handover and full
production/replacement comparison, not inferred from source code alone. Fresh
base, bootstrap/MCP provisioning, all five imports and initial comparison are
marked done with their limits. Full-workflow execution, recursive deployment,
functional tests, live rerun preservation and takeover remain open. Remaining
comparison findings are explicit decisions/tasks. Historical cleanup candidates
require current ownership review instead of action based on old IDs.

Reference status was corrected where it still described working imports or
password/PAH/MCP setup as pending. Four version-tool tests, TODO structure,
relative links/anchors, whitespace and added-content sensitive-marker checks
passed. This change modifies documentation/version metadata only.

## Preserve Orchestrator interpreter selection for job runtime

Importer regression and documentation: `f23f1af`; encrypted capture: `c141e1a`.

The production comparison found that the import process evaluated the localhost
interpreter expression, storing its own Python path. The operator requested a
portable result for imported Orchestrator jobs. The encrypted host definition
now marks the expression `!unsafe`, so CoP preserves it literally while importing.
The stored expression resolves normally when a later job runs. All other decoded
capture values and secret inputs are unchanged; the fix belongs to the CaC
inventory definition before the application playbooks execute.

Three focused tests passed, including the installed CoP wildcard combination and
host-parameter rendering with distinct import/job Python paths. Encryption header,
roundtrip and actual Ansible loader checks passed. Live import job 2273 succeeded
using `f23f1af`; a separate verified HTTPS read confirmed the target inventory
stores the literal expression. Application deployment and cleanup were not run.

## Recover failed deployments through manual stage retries

Planning and documentation change: `d7be1cc`.

The operator chose to remove automatic workflow recovery from the TODO because
individual Job Templates can already be retried manually. Operators retain the
existing instance inputs, rerun failed stages and launch the remaining stages.
A full workflow relaunch creates another instance and consumes another counter.
Stage 03's existing installer observer remains available. This decision changes
the plan and instructions only; deployment behavior is unchanged.

## Capture current lifecycle definitions and issue access on each target

Implementation: `0b3910b`; encrypted Assistant capture: `0146052`; encrypted
Windows capture: `62d6647`.

The configuration comparison found two uncaptured Windows templates and current
Assistant lifecycle changes. Windows now includes patch assessment and WSUS
patch-ceiling definitions without changing its prior objects or secret inputs.
Assistant retains its current project branches, reviewed release pin and selected
execution environment, controlled deployment/retirement surveys and Shutdown
template. Dedicated lifecycle groups start empty instead of copying old source
guest registrations. Both captures expose their existing exact PAH requirements
in the common schema; optional authentication maintenance remains excluded.

An inventory lifecycle bearer belongs to its target. The encrypted capture now
contains a new service-account password and a dedicated inventory grant, while
CoP creates the nonadministrator account and its objects. The importer issues a
target-local token and binds the lifecycle credential to that target's URL,
inventory and installed CA. It preserves a root-owned protected token record for
reruns, verifies ownership, scope, privileges, schema and material checksums, and
stops on ambiguous or missing recovery state. An existing account must authenticate
before any updates, and its password is omitted from update payloads to prevent
metadata changes from resetting it. Only this run's new token proved unsaved can
be revoked after failure. No source password/token is copied or rotated.

The CA default follows the installer account rather than the SSH login account.
Verified HTTPS requires the supplied URL to match a certificate DNS or IP SAN;
the encrypted contract may select another installed CA file. The target's internal
URL and installed CA passed a separate read-only TLS inspection.

The 67-test offline suite and three additional focused checks passed, including
15 token behavior checks, account control before grants/updates, password omission
and installer CA selection. Syntax, strict Ansible rendering, encryption round
trips, preserved ciphertexts/literal injectors, object references and staged
sensitive-data checks passed. Refreshed Assistant rollout and functional demo
execution remain separate from these source checks. Production configuration and
external demo environments were not changed by the capture refresh.


## Keep CaC comparisons while planning incremental audit-log catch-up

Planning commit: `cce0e28`.

The user chose to continue the current configuration comparisons and defer
audit-log analysis for catching CaC up with platform changes. The TODO now makes
that future work explicit: preserve audit checkpoints, identify changed owned
objects and relationships, retrieve current definitions and dependencies, then
review differences before updating encrypted captures. Audit events identify
what to examine; they do not replace the current object configuration.

Git changes, deletions, audit retention and component coverage must also be
handled. Periodic full comparisons remain part of the planned coverage checks.
No log-based automation, daily schedule or automatic CaC update was implemented.
Documentation whitespace, version consistency and staged-content checks passed.

## Use the successful login password until administrator rotation

Implementation: `fb87a08`.

A fresh installation exposed an ordering error: bootstrap authenticated with
the installer password, but PAH token creation then used the desired password
before the Gateway user role applied it. That request failed authentication.
The shared login task now retains its successful password in a protected,
noncached fact, and pre-rotation PAH issuance uses that fact. The encrypted desired
password remains unchanged and is still applied and verified later. A rerun
selects the already-active configured password and preserves existing tokens.
No password is added to workflow statistics, artifacts, or logs.

Three focused regression tests passed, including actual login selection for
fresh and configured-password cases and a PAH mock that rejects the inactive
desired password. Token preservation and failure cleanup remain covered.
Base, PAH preparation, AutoDeploy and curator syntax and whitespace checks passed.
The installer had completed successfully; only the failed base stage needed a
rerun. Live verification of that rerun is tracked separately from these checks.

## Manage PAH selection in base and require reviewed release curation

Implementation: `768550d`; encrypted base policy: `cd4a4ab`.

The user requested one current collection version unless project requirements
justify older versions, and clarified that the same collection may appear in
multiple repositories. Retention is therefore local to each repository: preserve
its newest installed release and actual project/playbook/EE requirements plus
dependency closure. A repository's older latest does not preserve obsolete
copies in another repository, and a newer release elsewhere does not remove a
repository's own latest. The curator does not claim to discover newest upstream
content or deduplicate collection names across repositories.

Stage 04 applies and verifies the remote selection limit and repository snapshot
limit independently. The installed remote collection module lacks the selection
field, so a local API extension supplies it after CoP dispatch. Base still does
not synchronize or prune collection content. The populated policy is encrypted
with the existing CaC Vault identity; all other encrypted base values were
verified unchanged.

Actual pruning is separate and defaults to preview. It needs a reviewed source
audit matching live projects and EE references, complete dependencies, an idle
target and an unchanged approved preview. Apply removes only the reviewed
repository associations and verifies retained content. Run externally or from
another seed during a maintenance window that prevents concurrent target work;
preflight checks do not provide a continuous lock. Mutable image references do
not establish image content or build provenance. Production audit completion,
recurring curation and target-side own-job exclusion remain future work.

Nineteen focused retention tests passed, including repository-local latest
selection, exact pins, dependency closure, unchanged settings and stale-preview
rejection. The 52-test broad run passed all other tests; its PAH guard fixture
needed the new required policy, and the corrected focused guard test passed.
Stage 04 and curator syntax, whitespace, staged-sensitive-data review, and
encrypted base round-trip checks passed. No live pruning was performed.

## Restore AutoDeploy as a use case and orchestrate complete deployments

Implementation: `6c83591`; encrypted companion capture: `9020feb`.

The user requested one workflow that creates an AAP, applies shared base, then
imports captured use cases in parallel, including the ability for the replacement
to deploy another instance. AutoDeploy therefore has its own encrypted capture
and importer rather than placing its deployment objects in platform base. The
workflow passes only the created VM identity, address and internal API URL;
installer hostname handling remains separate. After explicit PAH/image
preparation it branches to four captured demos and AutoDeploy itself, excluding
teardown and functional demo jobs.

The capture keeps environment credentials and populated object references in the
existing encrypted companion repository. A dedicated provisioning key was
explicitly approved and independently verified; the workspace's GitHub SSH
identity was excluded. Existing environment Vault access is captured separately
from base's Git and CaC Vault bootstrap credentials. Exact PAH collection batches
preserve multiple required versions, restore complete remote requirements even
after failure, and observe asynchronous policy completion before syncing.
Thirty existing/graph tests and three real-task mock-PAH tests passed, as did
syntax and private encryption/reference checks. Fresh recursive deployment and
full production coverage remain unverified; a captured Windows collection's
runtime version mismatch remains an explicit follow-up.
## Review the current CaC implementation against Red Hat guidance

Planning commit: `9dad713`.

The user requested a TODO to compare this project with Red Hat's Configuration
as Code guidance. Review automation access, content sources, capture coverage,
secrets, validation, drift, deletions and Git workflow for applicable gaps.
Account for the article's different AAP versions and example collection when
assessing the current AAP 2.7 CoP implementation. This schedules a review;
it does not establish compliance or change platform configuration. The README
overview also now reflects implemented target-side MCP token creation and the
remaining encrypted repository storage and client setup work. Documentation
whitespace, source-link and version consistency checks passed.

## Allow fresh installation to exceed the old one-hour async ceiling

Implementation: `5f8c3e0`.

An earlier fresh installation reached the one-hour command ceiling and required
observation of its existing async job. A longer Job Template timeout alone did
not extend that command ceiling. The installer command and existing-job observer
now allow two hours; the documented template timeout is three hours to cover
host preparation and health checks. Resume behavior still observes the original
job instead of launching another installer. Stage 03 passed syntax validation.

## Protect DNS authorization during provisioning and cleanup

Implementation: `6ad202d`.

The rebuild preflight found that the DNS API tasks could include authorization
headers in ordinary task results. Both creation and removal now suppress their
requests and responses independently of diagnostic logging elsewhere. Syntax
checks passed for infrastructure configuration and teardown; teardown was not
repeated to validate this logging change.

## Provision configuration access on trusted replacement instances

Implementation: `18f50b2`.

The user requested that shared base create the four configuration-repository Git
credentials and the CaC Vault credential from inputs already held in encrypted
base. This allows a trusted replacement to read and decrypt the same private
configuration repositories. The first seed still needs its initial access
independently. Provisioning rejects incompatible existing ownership, types,
injection schemas and Vault identifiers, and preserves already stored secret
values on reruns. Rotation remains a separate operation. Deployment-project
objects and provisioning-environment credentials belong to the AutoDeploy use
case rather than shared platform base. Four isolated real-task tests and a
Stage 04 syntax check passed; no live rollout was used for that validation.

This retrospective uses this repository's Git history and the project handoff.
Where historical intent is not documented, it is identified as an inference.
Source-baseline versioning begins after the historical commits below.

## Create recoverable target-local MCP access during base configuration

Implementation: `5542cbd`.

The user requested that base configuration issue an administrator MCP token with
read and write access on every new installation. Gateway scope `write` provides
both operations within that account's permissions. Provision it after the final
administrator login is verified, separately from the temporary management token
that ordinary run cleanup revokes.

The API returns a new bearer value only once. Save that value atomically in a
root-owned private file on its target so an authorized operator can recover it
for an external client. The directory uses mode `0700` and the file uses `0600`.
This interim storage uses existing guest SSH/sudo access and requires no new Git
write credential. Encrypted per-instance repository storage, client certificate
trust and controlled rotation remain separate planned work.

Reruns validate metadata, expiry, target identity and saved bearer authentication
before preserving existing access. Preserve manually created matching tokens
without issuing duplicates; their hidden value cannot be recovered from the API.
Unsafe storage or ambiguous/mismatched access stops for operator review. After
a failed save, revoke a new token only when inspection proves that its recovery
copy was not saved. Preserve inconclusive outcomes for inspection rather than
silently breaking access. Sensitive operations remain hidden during diagnostics.

Seven MCP tests exercised the actual tasks against an offline HTTP fixture and a
local substitute for the target filesystem. The complete 23-test suite and Stage
04 syntax check passed. Read-only inspection confirmed the live Gateway response
shapes; no live token, base deployment, VM or external client was changed.

## Limit PAH selection and remove obsolete collection releases

Documentation and verified-maintenance commit: `67de471`, following the policy
planned in `c547f68`. The live maintenance used supported Pulp API operations;
this repository does not yet contain recurring cleanup automation.

The operator requested the newest retained release for each collection while
preserving older versions explicitly required by projects. The audit covered
11 Controller projects, their available collection and execution-environment
requirements, and the retained collections' dependency constraints. Keep the
newest stable release already present for each collection, plus RHEL system
roles 1.120.5 because two projects pin it; retain 2.4.2 alongside that exception.
This avoids breaking exact project pins while removing unused release histories.

The maintenance reduced 263 releases to 16 across 15 collections: certified
244 to 10, community 18 to five, and validated one unchanged. Both removal tasks
completed and the final content matched the reviewed set. Project requirements
were unchanged, and independent MCP reads confirmed the published collections.
Removing repository associations did not include global orphan cleanup or
establish how much disk space was reclaimed.

Set each collection remote's `sync_highest_versions` to one and use exact
requirements with a complete dependency closure. Disable automatic dependency
selection for those explicit lists to avoid downloading extra matching releases.
Duplicate exact entries preserve the required older pin despite the per-entry
version limit. Keep repository `retain_repo_versions` at one as a separate
snapshot policy; it does not limit collection releases in the current snapshot.
Upstream source, authentication and TLS settings were preserved.

Updating the encrypted CaC source and implementing recurring enforcement remain
TODOs. The installed collection-remote module lacks the sync-limit argument, so
declarative management needs supported module or API integration. Use the current
encrypted source with its matching Vault key rather than replacing it from an
older plaintext export. No runtime automation jobs were launched for this work.

## Plan PAH version retention from project requirements

Planning commit: `c547f68`. Automated selection, retention and cleanup remain
unimplemented.

The operator requested fewer collection versions for simpler PAH management.
Synchronize only the exact versions required by projects and execution
environments, including their dependency constraints, and declare the required
set in PAH configuration as code. Keep multiple versions of a collection only
when project requirements justify each retained version. Otherwise select one
current compatible version. Audit requirements before pruning older content and
avoid unbounded remote selections that download complete release histories.

The TODO and README describe this future policy. The planning change does not
deploy a retention mechanism or remove collection content.

## Plan recoverable per-instance MCP credentials

This is planning only; persistent MCP provisioning has no implementation commit.
The existing temporary base-authentication implementation is `1216f38`.

The operator will create the current target's MCP API token manually and requested
future automation in the TODO. Each fresh platform issues its own token, so base
must provision instance-specific access rather than copy an old platform token.
An AAP credential masks its secret on API reads and therefore cannot be the only
copy needed to configure an external MCP client.

The planned recoverable copy contains the token, endpoint and CA trust material
in fully Vault-encrypted per-instance files in the private base repository. Opaque
filenames avoid exposing environment names. A separate repository-scoped Git
write credential enables saving these files while existing import access stays
read-only. Client setup decrypts values into protected local configuration with
certificate verification enabled. Provisioning, storage, rerun and rotation
behavior remain unimplemented; no platform or client configuration changes are
part of this documentation update.

## Verify Assistant Team import with trusted local PAH downloads

Encrypted Assistant Team fix: `094ee7f` in its private companion repository.
Encrypted base trust fix: `63f08ff` in the private base configuration repository.
The successful jobs used the existing importer from source `b80a1f0`.

The operator authorized importing the six ordinary Assistant Team templates and
their supporting objects. The first project creation failed because an empty
source-control credential name matched every credential. Omitting that field
correctly expresses anonymous access to the public code repository. Both encrypted
project entries were corrected while preserving every other value and all six
inner encrypted file snapshots; Vault round-trip and importer guards passed.

Project synchronization then exposed a separate platform trust issue. The
Controller service trusted the installer-generated CA, but its remote Podman
engine resolved execution-environment volume sources on the host. The default
host trust mount lacked that CA. A read-only mount from the installer's host-side
extracted trust directory produced the same bundle hash as Controller and a
verified HTTPS response. The encrypted base now declares this mount through the
existing Controller settings role, preserving its prior mounts and certificate
verification. Base job 2137 applied it; both project sync retries succeeded.

The pinned certified collection was curated through local PAH before import.
Import job 2139 succeeded with protected logging, and an independent TLS-verified
API comparison passed 396 checks over all 21 objects and six templates. Run tokens
and temporary workspaces were removed. API-masked secret fields were verified for
presence and protection; nonsecret snapshot provenance and credential type
injection matched the capture. Runtime deployment, recovery, provider calls and
optional authentication maintenance were not executed.

The operator also requested a planning item to capture Intelligent
Assistant/Lightspeed completely, including installer/service configuration,
vaulted credentials and passwords, Gateway OAuth, and an independent rebuild.
This adds a TODO only and does not change that service.

## Verify the encrypted base administrator password on a deployed target

Implementation: `1216f38`; verified runtime source: `c51aede`.

After restoring the existing private-base Git credential, job 2125 successfully
applied the desired password through the CoP Gateway user role and synchronized
the deployed installer inventory with mode `0600`. Job 2128 successfully used
the configured password and skipped installer access, bootstrap-token creation
and inventory changes. This verifies that future base reruns can authenticate
with the declared password while existing use-case importers can read the
current installer login.

Independent checks used trusted TLS and confirmed successful desired and
installer logins, matching password and permissions, no leftover run tokens,
and unchanged use-case object counts and EDA activation states. Both job event
streams confirmed token revocation and temporary workspace removal. No imported
use-case Job Template was launched for this verification.

## Define a complete production replacement and trusted seed bootstrap

Encrypted base credential inputs: `490a27b` and `9563936` in the private base
configuration repository. Administrator-password implementation: `1216f38`.

The operator clarified that the primary goal is a fresh AAP capable of taking
over production tasks, including deploying further AAP instances. Individual
demo imports remain supported, while complete replacement requires restoring
the deployment automation itself, all relevant production objects and secret
inputs, runtime dependencies, and functional verification.

An existing trusted AAP starts with independently provisioned base Git and Vault
credentials. The operator explicitly requested storing those inputs together in
the encrypted base so a seed can configure another trusted instance. Including
the decryption password in that ciphertext enables propagation after decryption;
it does not provide the initial seed's access or recover a lost key. Recipients
share the credentials' configuration access. Actual target credential and
deployment-template provisioning remains unimplemented and is tracked in the
plan, together with complete capture, job handoff, tests and controlled takeover.

This documentation does not resume stopped deployments or establish successful
password rollout or production takeover. Markdown whitespace checks were used;
no AAP job was launched for this documentation.

## Manage the administrator password in encrypted base configuration

Implementation: `1216f38`.

The operator requested that the desired administrator password live in the private
base Vault and be applied by Step 04. The base now declares the password and a
Gateway user entry that references it. Authentication first tries the desired
password; HTTP 401 or an omitted password enables installer bootstrap. Other
HTTP or connection errors stop rather than falling back. The CoP Gateway user
role applies the account, followed by a fresh Basic-authenticated login check.

When bootstrap was necessary, the deployed installer inventory is updated to the
verified password and restricted to mode `0600`. This keeps the existing use-case
importers' installer-based login current. A rerun using the configured password
skips installer access. Password handling stays protected during diagnostics.

All sixteen local tests passed, including seven authentication scenarios. Syntax,
Vault round-trip and whitespace checks passed. The first rollout stopped at
private-repository checkout before target changes because its token had been
regenerated. The existing base Git credential was subsequently updated and
repository access verified. The password rollout remains pending.

## Reuse the established Git-token credential type for Assistant Team

Implementation: `1926669`.

The operator requested the existing Git-token mechanism instead of a separate
SSH deploy-key mechanism. The importer now requires an HTTPS Git URL and
`CAC_GIT_TOKEN`, with the same temporary askpass helper and verified HTTPS used
by the other CaC importers. The unused SSH credential type was removed before
any key or credential was created. The token still needs read access to the
selected private repository; sharing a type does not share its permissions.

All fifteen local tests passed, including repository URL rejection, missing
token handling, encrypted configuration guards and cleanup after failure. Full
syntax and whitespace checks passed. No Assistant Team import was launched.

## Import the ordinary Assistant Team configuration independently

Implementation: `614763a`.

The operator authorized deploying Assistant Team definitions after shared base,
separately from running its deployment and recovery automation. The dedicated
importer loads only the companion repository's encrypted CaC capture and restores
six ordinary Job Templates with their supporting objects. Public code access
does not provide access to the private configuration; repository-scoped read-only
SSH access is injected as files, with independently trusted host keys and strict
verification. No write credential or source Controller identity is propagated.

The ordinary import validates complete deployment secrets and all six unchanged
encrypted file snapshots. Optional authentication maintenance remains nested,
outside dispatch, because it needs target-specific authorization and trust.
Reading that optional mapping can recursively render deliberately unresolved
inputs, so the ordinary importer leaves it untouched. A regression includes such
an unresolved input and rejects adding a seventh template to ordinary dispatch.
Functional readiness and optional maintenance remain separate from importing
complete ordinary AAP definitions. PAH collection and service-image availability
must be verified before a live import.

Authentication follows the established temporary Gateway-token approach.
Sensitive tasks remain protected during diagnostics, and cleanup removes the
checkout after ordinary failures, including failed token revocation. Launch and
schedule definitions are rejected; imported automation is never executed by this
entry point. Interrupted jobs and fatal role-loading errors retain the existing
cleanup limitation.

All fourteen local tests passed, with sixteen Assistant Team Vault/core guard
cases, six SSH URL cases and three failed-import cleanup scenarios. Full syntax
and the current encrypted capture's actual preflight passed. Implementation did
not launch Assistant Team configuration import or runtime automation.

## Align encrypted use-case captures with their current source

Private capture implementations: Orchestrator `0fd3b53`; Assistant Team
`2c3a825`, documented in `fbd7afd`.

The operator chose `Orchestrator EE` as the common name for the execution
environment definition, the project's default, and both Job Templates. The
previous project reference named an object the capture did not create, so the
three other references were aligned before attempting a clean-target import.
The configuration's remaining values were preserved.

Assistant Team was refreshed from the current Controller configuration and native
CoP export. Its public code no longer requires an SCM credential for private code.
The capture includes current project revisions and the encrypted external file
credential for six deployment/recovery templates. Existing deployment and model
authentication ciphertexts remain unchanged. Authentication maintenance is
captured separately from ordinary dispatch because its repository write access,
controller identity and trusted CA must be prepared for the target AAP.

The capture declares required PAH content and the execution environment's pull
prerequisite. Empty PAH repositories can prevent project synchronization before
runtime automation is launched. A dedicated Assistant Team importer is still
outstanding; validated capture data is separate from completed target deployment.

Validation checked owned references, native export of all seven templates,
strict ordinary rendering, missing maintenance input rejection and a synthetic
maintenance render. Vault headers and private round trips passed, and all six
embedded ciphertexts matched their source files exactly. No AAP configuration
import, runtime job, or provider authentication refresh was launched.

## Verify the protected PAH base rollout

Implementations: `5fc2c98`, `40906b1`, and `bf12d01`; encrypted base: private
configuration commit `82643da`.

The protected rollout succeeded after the API summary and upstream field-pair
fixes. Independent TLS-verified API checks found the three intended remotes,
repositories, distributions, and ordered local Controller download credentials.
The organization no longer includes public Galaxy as a source. Collection
repository versions remained unchanged, and no collection synchronization task
was created. Periodic Hub resource synchronization is distinct from collection
content synchronization and was already present before rollout.

The same three read-scope download tokens survived the reruns without replacement
or duplication. Temporary management and verification tokens were removed, and
the configuration workspace was cleaned. The successful job had no failures
with protected logging enabled. These checks establish repository and source
setup, not populated content or functional use-case tests. Upstream Red Hat
authentication and use-case collection preparation remain separate work.

## Import Orchestrator definitions separately from platform and runtime deployment

Implementation: `de5b54c`.

Orchestrator needs a dedicated CaC entry point after base, with its own private
configuration repository and Git read credential. `deploy-orchestrator-demo.yml`
loads only `cac/orchestrator.yml` from `main`. It uses the existing capture's
readiness mapping and protected registry inputs instead of changing the capture
schema or storing bootstrap access inside the repository being downloaded.
The reviewed capture defines eight owned AAP objects, including deployment and
cleanup Job Templates and their launch surveys. Those runtime operations remain
separate from importing their definitions; launch and schedule definitions are
rejected, and the dispatch launch roles are excluded.

Authentication follows the established importers: explicit target URL, encrypted
administrator input or installer SSH fallback, and a temporary Gateway token for
CoP dispatch. Sensitive tasks remain protected during diagnostic logging. Token
revocation and workspace removal run after ordinary failures; a token-revocation
error still permits workspace cleanup. Fatal role-loading errors and interrupted
jobs retain the existing cleanup limitation.

All eleven local tests passed. New tests ran eleven actual Vault loading and
preflight cases plus three failed-import cleanup scenarios. Full syntax and the
existing encrypted capture's new guards passed. No configuration import or
Orchestrator/OpenShift runtime operation was launched during this implementation.

## Defer upstream authentication during URL-only PAH setup

Implementation: `bf12d01`.

The diagnostic rollout reached the Hub remote module and returned HTTP 400:
an upstream authentication URL requires its upstream token even when no sync is
requested. The reusable base therefore omits that URL until future content
preparation supplies both fields. Local repository setup and local download
tokens do not require an upstream token. A protected preflight check now rejects
an unpaired authentication URL before any target change. No access controls are
weakened and no synchronization is added.

The encrypted base was regenerated from its protected working copy, with matching
Vault decryption and the private repository's minimal README preserved. Both PAH
tests passed, including seven configuration cases and credential lifecycle
coverage; full syntax and populated-base guards passed. A protected target rerun
is required to establish live success.

## Validate credential types using the actual summary schema

Implementation: `40906b1`.

The first PAH rollout created its local download credentials before failing at
the Hub remote role. A diagnostic rerun then stopped at credential preservation:
the Controller summary returns a credential type's name but omits its kind.
The guard now compares the exact built-in Galaxy credential type name. This
preserves the intended type check without replacing credentials or their tokens.
The local API fixture now reflects the actual summary schema; both focused PAH
tests passed, covering guards and the full credential lifecycle. The original
Hub failure still requires its separate diagnostic rerun.

## Configure PAH in base without synchronizing content

Implementation: `5fc2c98`.

Base now owns three PAH remotes, repositories, download distributions, and
Controller source associations in certified, validated, community order. The
organization's source list replaces the public Galaxy fallback with those local
sources. Upstream URLs are configured without fetching content or requiring
Red Hat synchronization credentials at this stage. Repository definitions must
explicitly disable synchronization, and the separate CoP synchronization role
remains excluded. Use-case content preparation is still a separate task.

The Hub roles require their own authentication variable, so the temporary
Gateway management token now supplies both Controller and Hub authentication.
Controller also needs credentials that survive the configuration job. Each
missing PAH credential receives a target-generated read token, stored immediately
in Controller. Matching existing credentials retain their hidden tokens; drift
stops for review. This avoids copying a source instance's token into another
instance or continuously creating replacement tokens on reruns. The reusable
encrypted base stores definitions rather than tokens belonging to an older target.

A failed save revokes the newly generated token only when a subsequent lookup
proves no credential was saved. An ambiguous result retains the token for review,
avoiding deletion of a token that Controller may already use. Management token
revocation and workspace cleanup remain independent. Authentication, decrypted
configuration, and credential-bearing tasks stay protected even when ordinary
diagnostics are enabled.

Nine tests passed. Local Ansible runs exercise source-order and no-sync guards,
and the actual Controller credential module covers creation, reruns, interrupted
saves, drift, and protected output against a local API fixture. Stage 04 syntax,
populated base validation, and full Vault encryption/decryption equality checks
passed. Live target rollout remains pending at this documentation commit.

## Keep PAH setup in base and create groups before linking children

Implementation: `d2e6988`.

The user clarified that base owns PAH's certified, validated, and community
repository configuration and Controller content sources. Base must not
synchronize content. Each use case separately declares its collection
requirements, including versions and dependencies. The dispatcher defaults to
synchronizing defined repositories, so Stage 04 now explicitly excludes that
role. Empty templates document both responsibilities. Actual target PAH setup
and population of existing use-case requirements remain TODOs.

Private Git access is needed before the encrypted configuration can be loaded.
Its runtime token therefore belongs in the deploying AAP's custom credential,
with a separately encrypted bootstrap recovery copy. A target project's Source
Control credential serves a different purpose: synchronizing that project's
private playbook repository after import. Repository-specific credentials keep
one access update from replacing another deployment's token.

The first Windows import to reach inventory creation failed at the parent
group; its child groups were submitted afterward by the asynchronous CoP role.
A retry succeeded once those children existed. The importer now creates group
skeletons first, then calls the standard role for full definitions and
memberships. A regression exercises the real Controller group module and
reproduces the missing-child failure before verifying the new sequence.
Existing empty-membership drift behavior is unchanged.

Seven tests and syntax checks passed. Live import succeeded with the preceding
source after a retry, without launching imported automation; the new ordering
has offline validation only. The project TODO also calls for a complete,
step-by-step CaC guide covering setup, deployment, verification, and recovery.

## Diagnose private configuration fetches without printing Git errors

Implementation: `5ccb0ca`.

The first Windows import stopped during the protected private checkout before
target authentication or object changes. Because the Git error can contain
credential-bearing data, enabling raw output is inappropriate. The fetch now
rescues failures, privately classifies their message, and reports only a fixed
category. This distinguishes repository access/not-found errors from DNS, TLS,
redirect, connection/timeout, and unclassified failures without changing access
controls or trying alternate credentials.

Seven synthetic failures exercised the actual rescue and cleanup tasks with
diagnostics enabled. They produced the expected fixed categories, hid both the
synthetic secret and raw errors, and removed each temporary checkout. Full
syntax and existing regression tests passed. The live error category still
requires a rerun; token repository permissions must not be assumed from a
successful checkout of a different private repository.

## Import disconnected Windows definitions independently from base

Implementation: `a84bf09`.

The Windows capture belongs to its own private configuration repository, so its
import accepts an explicit target URL and repository URL rather than assuming
the base or AIOps configuration store. It retrieves only the Vault-encrypted
Windows definitions from `main`, checks readiness and required secrets, then
uses the existing Gateway-token and CoP dispatch approach. Subscription and base
configuration are prerequisites rather than repeated operations.

Importing AAP definitions must not start Windows provisioning or patching. The
entry point therefore rejects job-launch and schedule definitions and excludes
the launch roles. It imports the captured Job Templates and workflow for later
use. Existing target machines are not contacted by this configuration job.

The CoP wildcard combiner can print its input values, so that step remains
protected separately before ordinary dispatch. Credential updates and all Git,
decryption, password, and token operations stay protected when diagnostics are
enabled. Default logging remains protected throughout. Syntax, the real CoP
dispatcher regression, seven Windows preflight cases, and version-tool tests
passed. Live Windows import remains a separate pending validation.

## Keep module-native Event Stream definitions out of initial dispatch

Implementation: `a64e16c`; encrypted deployment enablement: private configuration
commit `8a121e8`.

The first live AIOps import exposed an incorrect earlier assumption that CoP
4.10.0 lacked an Event Stream role. It includes that role, which reads each
item's `organization` field. Our dedicated module definitions use
`organization_name`, so initial dispatch attempted stream creation with a missing
required organization. Diagnostic job 2016 confirmed that exact error while
leaving other configuration logging protected.

Initial dispatch now excludes streams as well as activations. The existing
explicit stream task runs after prerequisites, followed by the activation role.
A regression test exercises the real dispatcher, including negative controls
that remove each exclusion. The earlier fixture replaced prerequisite dispatch
with a stub and could not detect this integration error.

The user authorized the first deployment, so the complete encrypted capture's
readiness flag was enabled. Job 2018 then succeeded with 131 successful tasks and
no failures. Independent API checks verified all 29 expected objects, successful
Controller project syncs, and both EDA activations running. Configuration tokens
and temporary files were cleaned; the persistent EDA credential was preserved.
Functional remediation remains a separate test; no external setup was changed.

## Resume installer monitoring without starting another installation

Implementation: `64aec45`.

The Controller stopped installation job 2002 at its overall 3,600-second timeout.
Host preparation had consumed part of that budget, so the remote installer's
separate 3,600-second async task had not reached its deadline. The last event
reported that task as unfinished; there was no installer error to justify a
second installation. The template timeout now allows 7,200 seconds.

Stage 03 accepts an optional existing async job identifier. This mode skips host
preparation, inventory edits, and installer launch, checks the existing result
under the original installer account, and requires exit code zero before the
Controller health check. Captured installer output remains protected. It does
not extend an existing task's async limit or treat an open HTTPS port as success.

Syntax and whitespace checks passed. Live resume job 2008 completed successfully
in 32 seconds: the original installer reported success, the installer-launch task
was skipped, and the Controller ping returned HTTP 200. No installation rerun or
security-control workaround was needed.

## Declare the collection used for public DNS validation

Implementation: `97e3236`; preceding HTTPS implementation: `de07aad`.

Successful deployment job 993 used a built-in HTTPS DNS request, while the
standalone checkout used an undeclared `community.general.dig` lookup and failed
in job 1996 before certificate issuance. The brief HTTPS restoration was
superseded by the user's preference for readable playbooks using reliable
collections. Stage 02 therefore keeps the collection lookup, explicitly requires
`community.general` 11.4.0 through PAH, and waits for the expected public A record.
This version supports the actual execution environment's Ansible Core 2.16.19;
its required `dnspython` package is already installed in that image. No Python
package installation or execution environment change is needed for this fix.

Ansible syntax and whitespace validation passed. The original failure happened
after DNS and temporary HTTP proxy configuration; the successful teardown and
VM creation stages must not be repeated to retry this infrastructure stage.

## Use the same EDA credential schema throughout deployment

Implementation: `91b5fc6`.

Integration review found that native exports normalized for CoP use
`organization` and `credential_type`, while the special target-token handler
expected the EDA module's argument names. The handler now reads the CoP item
fields and translates them only at the module call. This keeps one schema for
ordinary credentials and the target-specific Controller credential and avoids
storing duplicate aliases in the encrypted configuration.

Full syntax validation and eleven isolated checks using the installed EDA
credential module passed. Secret protection, first creation, preservation on
reruns, drift rejection, and cleanup remain covered. No live AIOps deployment
was launched.

## Create Event Streams before activating AIOps rulebooks

Implementation: `33f2575`.

This change introduced explicit Event Stream creation before activation import.
Its initial assumption that CoP 4.10.0 lacked the stream role was incorrect;
the later correction is documented above under `a64e16c`. The AIOps playbook
dispatches prerequisites first, creates streams through the supported EDA module,
and only then applies the CoP activation role. The encrypted capture
uses names and rulebook source names or indexes, so modules resolve the new
instance's IDs, hashes, and stream UUIDs. Required mappings are validated before
target configuration starts.

CoP also omits EDA project revision-on-launch and cache settings even though the
installed EDA project module supports them. A focused update after dispatch
preserves declared values, waits for the existing project, and avoids a second
source-control sync. These tasks supplement the collection's known omissions;
they do not change source AAP objects or external event publishers.

Full syntax validation and ten isolated checks using the actual EDA modules and
CoP activation role passed, including ordering, target mapping, failure handling,
and project setting preservation. The live AIOps Job Template remains unlaunched.

## Separate platform base from AIOps use-case deployment

Implementation: `e864dc9`.

The user clarified that base must exclude objects belonging to actual use cases,
including their Git projects. Each use case gets an independent encrypted file
and deployment Job Template. The broad private base was reduced to its platform
organization and existing setting, with previous definitions preserved outside
Git. The old credential intended for local PAH actually held an upstream token;
it was omitted instead of copying an unrelated management token. Destination
PAH bootstrap remains a separate requirement.

The AIOps entry point loads only its encrypted configuration after base and
requires reviewed readiness and explicit secret inputs before target changes.
It uses temporary configuration access and creates persistent target-specific
EDA access only when the corresponding credential is absent. Reruns preserve
that credential and reject conflicting settings. Cleanup revokes an unsaved EDA
token only when absence is verified, while retaining saved or uncertain access.
This avoids reusing source-instance tokens or disrupting existing activations.

The user selected the current working demo, with older/test objects inventoried
separately outside Git, and approved use-case-specific copies of shared inventory,
credentials, and runtime environments. Source AAP objects remain unchanged.
External environment setup is deferred. Export tooling was approved separately
and installed outside these repositories; it was not added to project requirements.

Full syntax validation and eleven isolated real-Ansible checks with the actual
EDA credential module passed. Empty template and whitespace checks passed.
The AIOps deployment entry point must remain unlaunched; live validation is future
work after its encrypted capture is reviewed. This does not claim a working
restored external monitoring or assistant environment.

## Manage AAP 2.7 applications through Gateway

Implementation: `44e1045`.

The first live run with the corrected installer authentication successfully
imported the subscription, then stopped while loading the collection's legacy
Controller application role. The installed Controller collection does not
provide that module. Step 04 excludes only `controller_applications`; the
Gateway application role still handles `aap_applications`, and Controller role
assignments remain enabled. The collection's supported role-exclusion setting
avoids changing its downloaded contents or suppressing the failure.

All 59 module references across the 58 selected roles were verified against
the five actual PAH collection artifacts. Five token-lifecycle checks passed.
The role-loading failure bypassed Ansible's normal cleanup, so its run token
was revoked separately using CA-verified HTTPS over the trusted SSH connection.
README now states this cleanup limitation. Subsequent live job 1985, using source
revision `7d65678`, completed shared base configuration in 162 seconds with 147
successful tasks, 36 changes, and no failures. It preserved the previously
imported license, revoked its run token with HTTP 204, and removed its workspace.
The project wait that displayed retry messages finished successfully after
46 seconds. Saved debug logging remains false. This verifies Step 04's shared
base flow, not per-demo loading or the complete deployment pipeline.

## Download project collections exclusively from PAH

Implementation and policy documentation: `2725894`.

The user required collection curation in private Automation Hub, including
community collections, rather than direct public Galaxy downloads by projects.
Sync all required collections and dependencies into the corresponding PAH
repositories before project synchronization. Organization source credentials
must point to those PAH repositories; public Galaxy must not be an active
source or fallback. PAH may continue using public Galaxy as an upstream when
syncing community content. The requirements file still selects the collections.

The public Galaxy source was detached from the existing organization. The
three PAH sources were verified to remain attached in their existing order.
AAP rejected deletion of the managed public Galaxy credential with a permission
error, so it remains an unattached protected object. No access controls were
changed. Source credentials on an AAP running Stage 04 are bootstrap inputs;
target CaC cannot supply the running job's own dependency-download access.

README, CaC guide, and operational documentation describe this policy and the
encrypted-token requirement. Documentation and whitespace checks passed. No
playbook behavior changed and no jobs were launched for this policy change;
runtime dependency verification belongs to the separate Stage 04 run.

## Declare the configuration collection for project synchronization

Implementation: `9243762`.

Step 04 could not start because its dispatch role was absent from the job's
collection search path. Storing the collection in private Automation Hub did not
make it available to the job. The user requested a project requirement for
`infra.aap_configuration`; it is pinned to the published version `4.10.0`.

With collection downloads enabled, project synchronization resolves that
requirement and its declared collection dependencies using the Galaxy credentials
attached to the project's organization. The requirements file selects the
collection, while organization credentials select accessible download sources.
Using a private Hub `validated` repository therefore also requires its source
credential on the organization. Python and system packages remain the execution
environment's responsibility.

The YAML structure and pin were checked against published Galaxy metadata, and
staged-file and whitespace checks passed. No local dependency installation, AAP
settings change, project synchronization, or job launch was performed for this
change. A successful project synchronization is still needed before runtime
collection availability can be verified.

## Bootstrap API access from the installed Gateway credentials

Implementation: `62ab119`.

Live subscription import returned HTTP 401. A read-only comparison over the
target VM's supplied SSH login confirmed that its installer Gateway password
differs from the saved password previously used by Step 04. The installer
Controller password is separate as well. No password values were printed.

The user had requested reading the current password from the installer. Step
04 now reads only that Gateway password over SSH with sudo, unless an explicit
current `aap_password` is supplied through encrypted configuration. It creates
a per-run write-scope token at the Gateway token endpoint, then passes that
token to the Controller license module and the configuration roles. This
follows AAP 2.7's Gateway token authentication path without changing access or
certificate-validation settings.

Dispatch runs inside the protected workspace block so cleanup can revoke the
token after configuration ends or fails. A nested cleanup block removes the
checkout, manifest, and helper even if token revocation fails. Password rotation
and removal of the remaining environment Vault dependency stay separate work.
Normal output remains protected; the existing debug switch still applies.

Five isolated Ansible checks verified installer parsing, an explicit password,
token use, authentication/configuration failure, revocation attempts, protected
output, and workspace cleanup. These fixture checks do not claim a successful
live subscription import or full configuration push.

## Use an explicit debug switch for Step 04

Implementation: `ff84279`.

The user chose `debug_logging` with positive debugging semantics: `true` shows
task output, while `false` enables `no_log`. The change is limited to Step 04;
aligning other projects remains planned. Both the playbook and Job Template
default to `false`, and an optional true/false survey supports a per-run override.
Native Booleans and survey strings are normalized, and invalid choices fail.

All nine existing protected tasks use the inverse of this switch. The dispatch
collection receives the same inverse through `aap_configuration_secure_logging`.
Debugging can therefore expose decrypted configuration in AAP job output, which
is documented in the README and survey; the saved default stays protected.

Six isolated Ansible checks verified default protection, native and survey
values, dispatch mapping, output visibility, and invalid input rejection. The
live template default and survey were verified without changing other template
settings. Those checks did not import a subscription or apply target objects.

## Apply the subscription before object configuration

Implementation: `7503d96`.

The user required subscription activation before pushing configuration. Step 04
now downloads the whole ZIP as `cac/manifest.zip.vault` alongside the encrypted
shared base. The same attached `cac` Vault credential decrypts both through
Ansible's runtime Vault support; no password lookup or new launch secret is needed.
The ZIP is restored with restrictive permissions in the private temporary
workspace and imported with `ansible.controller.license` before dispatch.

Failed decryption or subscription import stops configuration. Cleanup removes
the checkout, decrypted ZIP, and authentication helper on success or failure.
The license module uses `force: false` to preserve an existing non-trial license
when rerunning configuration. Installation registry/content access remains
separate from this AAP activation step.

Six isolated checks verified exact ZIP restoration, permissions, invalid inputs,
wrong-password failure, failure ordering, and cleanup. The API was simulated
because the required collections are absent locally; these checks do not claim
a successful live subscription import or configuration push.

## Choose the configuration API target explicitly

Implementation: `0d4bb8d`.

The user requested one explicit connection URL for Step 04, so operators can
choose an internal hostname or IP instead of implicitly using public DNS and
the reverse proxy. Step 04 now requires `aap_hostname` and validates that it is
an HTTPS URL before fetching configuration. It no longer constructs a target
from `vm_name` and the domain, and has no fallback to that naming scheme.

Step 03 remains unchanged: its installer inventory uses the VM's fully qualified
hostname, which can resolve internally. Step 04's API connection address is
supplied separately. Administrator authentication still comes from `myvars`;
automatic address handoff between deployment stages remains future work.

Nine isolated target-input checks and eleven HTTPS Git/Vault loader checks
passed. The real dispatch role and live AAP target were not exercised, and no
deployment or configuration job was launched.

## Load private configuration before applying shared AAP objects

Implementation: `fd35d02`.

Public playbooks remain separate from private deployment configuration. Step 04
downloads the private repository using a token injected by an AAP custom
credential, then decrypts and loads its shared base before the dispatch role runs.
The repository URL is an input; the branch is always `main`, as requested, rather
than a release tag. The token is supplied independently from the encrypted
configuration so access does not depend on first downloading the file that would
contain that token.

The token stays out of Git URLs, command arguments, stored credential helpers,
and task output. A private temporary checkout and authentication helper are
removed after loading, including on tested failures. HTTPS certificate validation
remains enabled, redirects are refused, and submodules are not downloaded.

The existing `myvars` still supplies environment settings and target login while
the new `cac` Vault credential decrypts private configuration. Removing `myvars`,
reading the installer password, rotating the administrator password, and selecting
demo files remain separate work.

Eleven isolated HTTPS Git/Vault checks verified the current encrypted base with
both Vault credentials, invalid inputs, authentication/decryption failures, TLS
rejection, protected output, and temporary-file cleanup. The four version-helper
tests and whitespace checks passed. Full syntax validation was blocked locally
by the missing dispatch collection; no live AAP job or full deployment was run.

## Identify the source of the AAP configuration role

Implementation: `e97480d`.

The user requested attribution to the Ansible Community of Practice. The upstream
project identifies `infra.aap_configuration` as the Red Hat Communities of
Practice AAP Configuration Collection. Step 04 and Windows restore both use its
`dispatch` role to apply AAP object definitions. The README and CaC guide now
name that role and link upstream so operators can find its documentation.
This describes the existing configuration implementation; no playbooks changed.

## Separate editable, private, and generic configuration

Implementation: `6583b61`.

The user requested moving the encrypted shared base into the private configuration
repository and removing it from this repository's current tree. Generic empty
examples remain here. This keeps reusable automation separate from the intended
deployment configuration; existing Git history and release tags were preserved.

Editable `base.yml` and demo files stay in the working directory outside Git.
Completed configuration is copied, Vault-encrypted with the local password file,
placed in the private repository, verified by its header and decrypted equality,
then committed and pushed. The moved ciphertext was unchanged, and its private
commit was pushed before the public copy was removed. The local plaintext base
was created with restricted permissions. The password file stays outside Git.

Step 04 was deliberately left unchanged within this migration's scope. It still
references the former project-local base path, so loading from the private
repository must be implemented before it can run from this checkout alone.
No deployment or configuration jobs were launched.

## Adopt per-project versioning and reusable CaC templates

Implementation: `f3efca9`.

The user requested the same version policy used by the assistant-team project,
applied independently to this repository. The source baseline is `0.0.1`;
later feature commits increment minor and reset patch, while all other commits,
including documentation and history, increment patch. A version-bump helper and
incremental release notes make that convention reproducible. Published releases
use an annotated tag and a matching GitHub release on the exact version commit.

The user also distinguished two deliverables: a reusable CaC structure for other
operators and applicable configuration for our demos. Empty shared and per-demo
examples provide the former without exposing the latter. Operators fill copies
outside Git and encrypt sensitive completed configuration before committing it.
Existing encrypted configuration is retained; selecting demo profiles and fixing
target authentication remain future deployment work.

Vault password files stay outside Git, and ignore rules plus staged-file review
protect against accidental inclusion. Four CLI tests verify patch/feature changes,
project-relative file selection, and safe failure for invalid or missing versions.
The empty templates passed YAML structure checks. This validation does not claim
successful deployment of the current AAP pipeline.

## Keep the deployment project in its own repository

Implementation: `5f7597d`.

The initial commit explicitly describes the split from the umbrella repository
into an independent AAP deployment and CaC project. It contains the four-stage
pipeline, guarded teardown, and shared configuration. Earlier private history
is outside the scope of this retrospective. Historical plans describe separate
stages as a way to support independent execution and recovery.

## Read guest access settings from Vault variables

Implementation: `caec4cc`.

The commit message states that guest connection and installer-account values
were replaced with Vault variables and the missing variable-file load was added
to the first installation play. This made the split playbook runnable without
restoring environment-specific values to plaintext source.

## Update the image source and identify the Linux provisioning stage

Implementations: `81c9fd9`, `bbb82d8`.

These commits updated the image source setting and renamed the first playbook
to identify Linux VM setup. No extended rationale was recorded in their commit
messages. Matching the available image and making the stage's purpose clearer
are inferences from the changes, not documented decisions.

## Restore Windows configuration independently

Implementation: `5850626`.

The dedicated restore playbook accepts a supplied CaC file and separately
provided target authentication, with certificate validation enabled by default.
Its accompanying documentation describes applying configuration to an existing
AAP after shared prerequisites are present. It restores definitions without
launching the VM deployment jobs. A second-target restore was not verified.

## Make encrypted CaC files recognizable

Implementations: `63c89ed`, `c163e8a`, `4cdf25d`.

The commit messages explain that the shared CaC file contains credential inputs,
so its encrypted nature should be visible in its filename. The naming convention
settled on `PROJECT_PLACEHOLDER_CaC_vault.yml` for encrypted CaC and plain names
before encryption. Related references were updated without changing ciphertext.

## Keep the Vault variables inside the AAP project root

Implementation: `0b45904`.

The commit message documents that splitting the repository made the former
parent-relative Vault path point outside the synced AAP project. Moving `myvars`
into this repository and updating load paths makes the encrypted file available
inside the project root. The handoff reports a local variable-loading check;
that check does not establish full post-split deployment success.

## Canonical capture compatibility — 99cc306

Project captures move to one predictable `vaults/cac/<project-id>-cac-vault.yml`
path in each project's private companion. Commit99cc306 publishes compatibility
before private file removal: old consumers prefer canonical paths and shared
checkout temporarily retains the former AutoDeploy path. Extraction accepts the
canonical path and a narrow declared per-template shared-inventory reference,
while retaining older portable inventory aliases. This ordering avoids breaking
saved jobs during private publication. The implementation was validated offline;
SCM synchronization3165 completed at the same commit without running an import.

## One project importer and explicit API credentials — 305b0cd

Commit305b0cd replaces five import engines with one resource-driven playbook.
Separate Job Templates keep their fixed human-readable project IDs and saved
repository-specific read token/Vault pair. The ID derives the private repository
and canonical capture; protected environment data supplies its owner namespace.
Old playbook names are only fixed-ID aliases. Capture metadata maps existing
resource lists rather than introducing project-specific task branches or arbitrary
includes, preserving nested data and literal runtime templates.

The operator selects the inventory instance and an explicit native destination
API credential at launch. Its endpoint must match stored ansible_fqdn, and TLS
verification is mandatory. All AAP API requests run in the source execution
environment; installer-password scraping, SSH API delegation and source bearer
fallback are excluded from project import, selector authentication and prerequisite
API login. Existing infrastructure custom types are unchanged; their review was
explicitly deferred. Standalone import may target its source AAP, while the
optional preparation selector retains its separate fresh-target checks.

Shared resource handlers establish group skeletons before relationships, apply
EDA project settings completely, normalize Event Stream organization aliases,
and preserve existing activation states while creating new definitions disabled.
Persistent EDA and dedicated inventory-service access have explicit API-only
creation/reuse and proved-unsaved-token cleanup. Existing masked or ambiguous
access is preserved for explicit recovery. Windows public trust must be prepared
as encrypted input; missing trust never triggers an SSH workaround.

The actual source requirements cache matches the native-module fixtures. Full
offline regression passes170tests; focused real-capture rendering runs both
Ansible native modes, and impacted production lint passes. These checks establish
source behavior without importing a use case or running application/activation
operations. SCM publication and preserved-ID template metadata migration are
verified separately; functional use-case tests remain outside this change.


## Project-derived deployment names — 3028df4

Commit `3028df4` gives the five project deployment templates the display names
requested by the operator. Hyphens and underscores separate ID words; word order
is retained, first letters are capitalized, and AIOps/AAP use explicit acronym
overrides. A single tested helper derives selector lookups from project IDs, so
the public catalog no longer maintains independent display-name strings.
Repository names and project IDs remain unchanged.

The five existing production templates were renamed in place, including the
matching AutoDeploy survey title. Encrypted template definitions, selector
credential keys and extraction inventory-reference keys were aligned. Existing
IDs, repository credentials, launch settings, grants, schedules and numeric
workflow links were preserved; no application template or SCM Project was renamed.
Current protected diagnostic wording was copied from the five source surveys
into the desired capture without weakening secret logging.

Focused naming/selector, extraction and version regressions passed 28 tests;
production lint passed for the changed catalog. Protected readback compared all
124 template identities and all 76 workflow nodes. Eighteen current encrypted
YAML files across the five private repositories had no remaining old deployment
name references; historical migration evidence remains unchanged. Publication
and SCM synchronization do not establish a successful project import, and no
import, application job or activation was run for this naming change.


## Shared instance tokens, future public names and complete retirement

Implementation `fda45e8` keeps one generic CaC importer and each project's own
Git/Vault pair, selecting the destination bearer by inventory instance name from
the owner-approved temporary shared credential. Base reuses its existing MCP
token for remote API access, encrypts its per-instance record and updates the
source credential. This avoids fixed destination bindings; an external secret
manager remains the deliberate future replacement.

The same change derives future public names from the already consumed global
number while retaining existing VM keys and completed routes. The owner chose
future deployments only, then separately authorized retiring the old recovery
instance and building a fresh one. Decommissioning verifies the recovery host,
exact guest storage/UUID ownership and versioned DNS before removing related
guests, website/proxy/auth/cache/certificates and orphaned same-version records.
It removes obsolete active source inventory/API data but retains allocation
history. These are explicit owner requirements; production remains excluded.

Validation: 188 full-suite tests passed, plus focused real encrypted Git
publication/retirement and DNS/storage refusal checks; production lint passed
23 files. Live decommission/rebuild is a separate tracked verification step.

## Release verified generic guests through the existing deployment

The operator approved automatic removal of a successfully configured guest's
extra IPv4 recovery quarantine while retaining production destination denial.
The existing generic Linux job calls a shared role from an exact public source
revision. The existing publication action preflights source-job identity and
current policy, records verified ownership in the existing shared inventory, and
saves the release in the existing encrypted recovery captures and API metadata.
No new job, service, credential type, secret store or allocation record is added.
An unpublished failed release rolls back; a durably published release remains
for an idempotent source-inventory retry. Decommissioning retires only exact
selected identities and preserves production protection for other releases.

Implementation `183d3ce` passed all 249 repository tests, including native role
loading, encrypted-Git publication, interrupted source update/retry, exact guest
ownership, runtime rollback and unchanged token/allocation tests. Focused Ansible
syntax and production lint passed. Actual guest acceptance is checked separately
through the existing normal deployment template.

## Preserve project tasks and decisions independently of the running hypervisor

The operator requires Git copies of task progress and decisions because the
original host may be reinstalled. Beads remains authoritative. Implementation
`d74a61b` adds a generated public metadata overview and a complete scoped native
Ansible Vault recovery export in the existing Hactar repository. Private task
bodies and comments are encrypted; source data is read-only and both outputs
have stale checks. Unchanged decrypted data retains its ciphertext. No new
tracker, secret store, credential type or automatic database restoration is added.
The Hactar companion implementation is `40198b0`.

The agreed guide records external AAP recovery, independent version-to-version
acceptance, retention of the four older production stages while excluding them
from future CaC, newer-stage own/remote hypervisor requirements, self/remote CaC
installation and use-case-specific runtime targets. AO's deployment origin,
OpenShift destination and selected AAP integration are independent. AIOps must
use the intended versioned environment consistently. Requirements are separated
from successful live proof, and the older destroy-template review preserves the
original-host teardown limitation without deleting objects.

Validation passed nine exporter/native-Vault checks, six Hactar metadata checks
and four version checks. Actual scoped export, comments, exact decryption,
unchanged-record checks, prior task-ID retention and ownership-table preservation
were verified. README, restart instructions and project working rules describe
mandatory Git refresh and recovery without the current Beads database.

## Verify persistent bootstrap metadata and running guest ownership

Generic guest bootstrap saves its public provenance using `virsh desc --config`
after startup. Libvirt may therefore omit that description from running XML.
Implementation `d2d7254` requires the saved provenance in persistent XML and
checks any live copy if present. Both definitions must still match the exact
UUID, disk, network and MAC, and all hypervisor and guest identity checks remain.
This corrects verification of the existing native bootstrap behavior without
restarting guests or broadening the release policy.

The same fix checks command success and nonempty output before parsing runtime
JSON or deciding on rollback. Sixteen focused runtime, native-role and encrypted
publication tests pass, including failure-output handling and refusal of missing
persistent metadata or altered live ownership. A read-only execution against the
actual target passed with application disabled. Production lint passed.

## Verify automatic release through the normal deployment job

Source job 3282 completed configuration-only acceptance using Assistant revision
`6098490`, which pins AutoDeploy implementation `d2d7254`. The existing guest was
verified and released in that same job; no provisioning or package-update stage
ran. Independent inspection confirmed the selected release only, production
denies before release and established-connection allowances, unchanged VM
definitions and normal services, public connectivity and blocked production
access. Encrypted publication `fb476d1` and source inventory match the intended
transition, preserving instance tokens, allocation history and existing literal
template tags. The protected evidence is retained in the existing Hactar Vault.

This completes acceptance of the generic Linux deployment hook. Other guest
restrictions and the broader recovery acceptance work remain; a successful
selected-guest test is not a reason to lift quarantine for every VM.

## Preserve native firewall rebuild rules and omit empty group inputs

Implementation `1e89880` fixes two boundaries found during the current portable
deployment. A captured empty group-variable string is omitted before calling the
dictionary-typed native group module, matching the existing CoP role. Native
fixtures reproduce the former rejection and verify empty, omitted and nonempty
inputs in both Ansible modes.

The live guest permission also needs its exact native firewalld declaration in
the settings consumed by Hactar's base firewall playbook. Publication now saves
only the current operation's verified source/destination/port rule across the
three encrypted captures and source aliases. Prior rules, credentials and guest
identities are retained; conflicting states, priorities and duplicates for that
endpoint are refused. Three focused persistence tests and 34 related regressions
passed. Full regression validation of the preceding portable implementation
passed 275 tests; subsequent focused checks cover these corrections.

## 2026-11-05 — Register RHEL through the shared CaC importer

The exact reviewed RHEL-sniperpatching project ID now uses the common importer
and selected-use-case catalog. Deploy RHEL Sniperpatching CaC runs the shared
playbook directly with its fixed ID, dedicated repository reader/Vault pair and
existing inventory/token-store destination selection. The repository and capture
retain uppercase RHEL. The original five bootstrap pairs remain required; the
RHEL Git and Vault entries are optional together. No wrapper, authentication
mechanism or resource schema was added.

All 38 focused tests passed, including six protected captures under both native
modes, half-pair/case/reused-Vault refusals and rerun preservation. Three syntax
checks and production lint passed. Live import and host/application acceptance
remain separate.

Implementation commit: `d12d5a4ab72082d7de63637fe7ae400c703c8924`.

## 2026-11-05 — Verify the RHEL configuration deployment

The shared importer completed on the explicitly selected receiving AAP using
implementation `d12d5a4` and published source `0d52fc1`. Readback verified all
seven RHEL templates, six surveys and inventory/runtime/credential bindings,
while preserving existing template definitions. The imported read-only runtime
diagnostic then confirmed execution-environment, collection and Satellite API
readiness. Existing Machine selection remains separate from SSH-key equivalence
and receiving-host login. No wrapper or authentication mechanism changed.

## 2026-11-05 — Focus on the repeatable demonstration

Documentation commit `b62e89d` replaces the long opening run history with the
existing deploy, demonstrate and reset sequence. It corrects prerequisite order,
source bearer guidance, target selection and private capture filenames. The owner
requires observed failures to be fixed in normal automation; manual cleanup is
not a substitute for a working reset. Keep resource/production safeguards and
bounded waits, while avoiding additional recovery frameworks and repeated proof
collection. OpenShift runtime verification is deferred. Beads remains authoritative
with a public overview and encrypted Git recovery checkpoint.

## 2026-11-05 — Complete the lean RHEL demo

RHEL implementation `2be30c742f946b6f9c1ad93a9b7efbe14e230953` (source 0.5.7)
passed one complete RHSA/cutoff/full-update cycle on the workshop controller.
Both full updates ran and verified already-current outcomes. Receiving-AAP CaC
and runtime verification remain distinct from unproved client SSH access.
The current generated task overview and encrypted recovery checkpoint are preserved.

## Honor the isolated network's disabled DNS — 2026-11-05

Implementation `3f5c7e2` follows the native network declaration during Windows
release and retirement. Explicitly disabled DNS requires no matching DNS entry;
exact DHCP ownership remains mandatory. Enabled DNS retains both checks. This
fixes a real deployment mismatch without enabling DNS or weakening VM identity
checks. All twelve focused lifecycle tests passed, including DHCP-only networks
and refusal of missing DHCP, unexpected DNS or missing enabled-DNS records.

## Queue certified-content and readability cleanup — 2026-11-05

Documentation `632d2cb` adds task `bead-wd-72f.34` to the Git-visible overview.
The owner requires reviewing standalone helpers, custom Ansible plugins/modules,
embedded Python and other scripts against certified collections/vendor roles
first. Remaining custom code needs a concrete gap; cleanup must reduce opaque
helper chains and preserve readable workflows, clear errors and essential safety.
The task is queued rather than an unreviewed rewrite during functional testing.

## 2026-11-07 — Add Command Center to the reviewed CaC projects

Implementation: `d107d3fbd1be2ecd29c14bdb4b442f1ecba84757` (0.48.0).

The owner requested the same deployment arrangement as the existing projects.
Command Center now has a reviewed project ID, catalog entry and derived
deployment name in the common importer. Its dedicated repository reader and
Vault inputs are an optional complete pair, preserving the five required pairs
and optional RHEL pair. Bootstrap reruns preserve existing credentials.

CaC import installs reviewed platform definitions. The separate application job
still requires the selected workstation's account, native authentication,
tracker and protected application settings. Importing definitions does not
establish successful application deployment or public browser access.

All 41 focused importer, selector and bootstrap tests passed, including seven
protected captures in both native rendering modes. Three playbook syntax checks
and production lint passed. The public overview and existing encrypted recovery
export retain current task outcomes and all 150 baseline records. Live Command
Center import and application acceptance remain separate work.
## Authenticate the private native firewall source — 2026-11-09

Implementation: `b1587dc7e76df7320815fc8199be1a98144e2fe5` (0.49.10).

The native firewall task source is private. Credential-free checkout failed;
the ordinary base reader could not read the exact commit, while the existing
source-only SCM reader could. Reuse that reader through existing encrypted
project settings instead of adding a credential type or replacing the allocation
writer's token. Git receives a process-local header scoped to the fixed
repository, with verified HTTPS, no redirects, no credential helper and the
unchanged exact-revision check. Temporary checkout cleanup remains unchanged.

The existing protected AIOps pre-import preparation also seeds this setting in
new selected runtime namespaces. It preserves other instances and identical
retries and refuses an unexpected existing credential change. No provenance
schema, secret store, wrapper or additional job was introduced.

Forty focused native-source, application-policy and encrypted factory tests,
two-file strict production lint and five normal playbook syntax checks passed.
The local Git fixture checks the actual checkout for absent persisted auth,
keeps the separate writer token intact and rejects missing/multiline auth before
Git runs. The encrypted input's other values, literal tags, Vault key and header
were preserved. These checks do not establish live AAP source authentication or
full downstream demo acceptance.

## 2026-11-12 — Use official Core 2.20 without image customization

Implementation `feab264` moves the deployment runtime to the official AAP 2.7
minimal RHEL 9 Core 2.20 stream. The owner chose to keep the image unchanged,
load collections through project requirements, and replace the optional Python
DNS lookup dependency with managed RHEL dig and built-in EE DNS resolution.
Exact endpoint-address checks and trusted TLS remain before authentication.

Core 2.20 fixes upstream delegated package lookup issue 82598, so both firewall
role calls use normal delegation again. The earlier null-delegation, interpreter
and manual package-fact workaround is removed; inventory identity, protected
values, SSH pins, rollback and native isolation checks remain.

The existing Vault serializer/readers use the public template-trust API, preserve
literal template-bearing values, and accept native tagged integer IDs without
accepting booleans. Obsolete Vault filename arguments are removed. Eighteen
focused fixtures passed on the actual Core 2.20.10 image across scoped runs,
covering DNS refusal cases, allocation, protected YAML, normal package dispatch
and encrypted Git publication. Failed intermediate test attempts remain evidence
of the migration work rather than deployment acceptance.

Base CaC resolves the default EE by name on the rebuilt controller. Hactar
reinstall and configuration jobs use that same runtime; platform control-plane
and preserved legacy job images remain independent. Fresh bare-metal recovery
and complete versioned deployment still require their own observed outcomes.

## 2026-11-12 — Record verified Core 2.20 host progress

Implementation `f406fcf` updates current recovery documentation after
conversion, host setup and all seventeen post-reboot host checks passed on the
unmodified official Core 2.20 EE. It preserves the failed parent workflow result:
removing an approval definition during the active run left a runtime node without
its template, which Controller treats as a failure despite successful children.
Current maintained workflow definitions contain no manual approval nodes, as
requested by the owner.

Current Orchestrator documentation names the base-owned Core 2.20 EE. Its
OpenShift runtime remains deferred because the stock image lacks its Python
client; documentation is not runtime acceptance or image-build authorization.
Fresh receiving AAP and full use-case acceptance remain separate. Version
0.57.2 corrects an accidentally committed documentation/version merge conflict,
preserves concurrent visualization history and records this checkpoint without
changing runtime automation.

## 2026-11-12 — Describe native policy verification before allocation

Implementation `9763121ebd248754f1995064f24d2b440a09e8c4` (0.57.3) corrects the allocation guide's stale reference
to a retired isolation helper. Stage 01 compares the complete native firewall
policy with protected CaC and checks the persistent service before reserving a
new name. The README and guide now describe the existing implementation. No
firewall permission, identity check, runtime path or allocation behavior changed.
Version 0.57.4 records the documentation correction.

## 2026-11-12 — Build a layered shared default EE-v1

Implementation `cd10989` (0.58.0) follows the owner's explicit replacement of
the earlier unmodified-default decision: derive a new shared EE from the exact
Red Hat Core 2.20 base, add the Kubernetes Python client, publish to the existing
Private Automation Hub and then change AAP/CaC defaults. The recipe adds client
35.0.0 plus jsonpatch 1.33 required by the intended collection, with all nine new
distributions and wheel hashes locked. Collections remain native project content.

Actual local build and offline checks preserve all 57 original Python package
versions, the full base layer chain and native user/entrypoint/command/working
directory. Core remains 2.20.10 and Python 3.12.15. The original vendor image is
unchanged. The complete vendor package inventory and native build/publish steps
are documented. The first Hub push failed with HTTP 502 and Hub worker timeout
evidence; publication, AAP default activation and fresh runtime acceptance are
not claimed. Version 0.58.1 records this implementation and its current limits.

## 2026-11-12 — Persist the approved Hub upload limits

Implementation `8b91b22` (0.59.3) persists the supported Hub worker timeout of
200 seconds before installation and the native registry request/idle limits of
600 seconds during base configuration. An actual image push failed because Hub
workers were killed after ten seconds while hashing its large layer; the
registry route also had an effective fifteen-second ceiling. No OOM evidence
was found. The owner approved the narrow live fix and durable configuration.

Only the existing Hub API container was reconciled with its exact native module,
image, mounts and secrets; other running containers retained their start times.
The Source inventory and registry route readback verified the approved settings.
The same image then published and independently pulled with verified TLS.

Three focused tests passed on actual Core 2.20.10 with the native Platform
collection, including installer and route rerun idempotency, preserved security
fields and seven refusal cases. Both complete playbooks passed syntax checks.
Source route IDs are not copied into new receivers. The firewall decision for
new receivers reaching the protected Source Hub remains separate. Version
0.59.4 records this implementation and its verification limits.


## 2026-11-13 — Keep complete repository previews and reserve sysadmin space

Implementation `202741292f577ebfa152aa74f9f288d1cb8545d7` (0.63.0)
keeps one continuous scrollable presentation file in each repository pane.
The private pane already retained the complete configuration; its existing
behavior is preserved and extended with explicitly synthetic Vault-style inputs.
The public pane now combines the pinned playbook excerpts rather than replacing
them at every step. Each step focuses and scrolls within its relevant sections;
all other sections remain available. Focus and execution highlighting are
separate so merely showing capture code does not imply running it.

These are presentation examples. Runtime playbooks and the whole-file Vault
storage architecture are unchanged. Certificate settings are illustrative;
Certbot-managed private keys are not moved into Git. The existing sysadmin figure
also has permanent reserved space above the original AAP, keeping that AAP in
its lower position throughout the story instead of moving it at the outage step.

The 23-case local regression suite passed. Pages run `43444124218` succeeded for
the implementation commit, and all six deployed assets matched the checkout.
The same 23 interaction checks passed against the downloaded deployed assets.
Scroll-selection tests use simulated offsets; actual browser geometry was not
measured. Version 0.63.1 documents the implementation and these verification
limits without changing the deployed assets.


## 2026-11-13 — Apply purple changes in the same layer order as blue

Implementation `adb598bf6f0219f7f32e99bdf142e9b99b49b05a` (0.63.2)
reorders the three purple stages to OS/RHEL configuration, AAP configuration,
then additional AAP objects, following the owner's requested layer order.
The certificate changes to v2 while Logging remains v1 and only the four blue
base objects are present. Logging then changes to v2; the six purple objects
arrive last. Earlier changes remain applied at each later stage. Change in Git
now precedes Apply objects in chapter navigation, while existing direct links
and the thirteen-stop story are preserved. The purple route colour begins at
the OS update independently of the later object import.

All 23 regression checks passed, including incremental state and backwards
navigation. Pages run `43445905286` succeeded for this implementation; all six
published assets matched and the same 23 interaction checks passed against the
downloaded deployed assets. Browser geometry remains unmeasured. Runtime AAP
automation is unchanged. Version 0.63.3 documents this result without changing
the deployed assets.


## 2026-11-13 — Show quoted Jinja variables in mockup VM inputs

Implementation `7f4979f3f995f2ef82be5db1707850a115b4f0f7` (0.63.4)
replaces the three VM input angle-bracket placeholders with quoted Jinja
variable references, following the owner's request for realistic mockup syntax.
The names are illustrative; runtime automation and protected values are unchanged.
The existing 23 checks passed locally and against the downloaded live assets.
Pages run `43515673878` succeeded, and all six published assets matched the
implementation checkout. Browser geometry was not measured. Version 0.63.5
adds this history only and does not alter deployed assets.


## 2026-11-13 — Show the RHEL implementation and match travelling block fills

Implementation `77b2d16566bbe0d2436b2c36c7e6d88335c85a5b` (0.63.6)
replaces the header-only infrastructure preview with the actual certificate task
and firewall role. Independent inspection confirmed both source files match the
existing pinned revision. Each excerpt has its own source label; initial OS
setup focuses both, while the later certificate update focuses only its section.
Private mockup inputs now show the corresponding protected domain and rich-rule
bindings instead of disconnected saved Job Template inputs. The bindings remain
illustrative, and the actual firewall plan is computed by existing automation.
Both source excerpts operate on the hypervisor; diagram placement is not a claim
that the infrastructure play configures firewalld inside the guest. A comment
also distinguishes local job execution from the remote AAP HTTPS API target.

The owner additionally requested that travelling blocks match the configuration
objects' light fills. Ordinary, manual and replay packets now use the same soft
origin colours. Strong arrow colours remain, with dark packet chevrons for
readability; dimensions, motion, reduced-motion behavior and object layout are
unchanged. Runtime automation and protected configuration are unchanged.

The 23-case regression suite passed locally and against the downloaded deployed
assets. Pages run `43517173937` succeeded, and all six public assets matched the
implementation checkout. Browser geometry and pixel colours were not measured.
Version 0.63.7 documents these outcomes without changing the deployed assets.


## 2026-11-14 — Name the AAP configuration push explicitly

Implementation `a7694b4f609f70299aead6d9fb36b990e2c21237` (0.63.8)
changes the base AAP-settings arrow caption from “Apply AAP” to the
owner-requested “Push AAP config”. The existing interaction expectation and
README are aligned; other labels and behavior are unchanged.
All 23 local and downloaded deployed-asset checks passed. Pages run
`43557407229` succeeded and all six public assets matched the implementation.
Browser geometry was not measured. Version 0.63.9 documents this result only.


## 2026-11-14 — Delete all underneath-arrow text

Implementation `00f843a920da67807d9d6ad49840773b96c6fa4a` (0.63.12)
deletes ACTIVE cues from all six arrows and the New VM/New AAP, Scan job and
Another AAP subtitles. Their HTML, presenter write and unused CSS are removed
rather than hidden. Action captions above the arrows, card titles, travelling
blocks and route activity remain. The change follows the owner's explicit
request to remove the secondary text everywhere.

A normal push encountered concurrent source changes. The visual commit was
rebased onto them, preserving both updates and reconciling only version/release
metadata. All 23 walkthrough checks passed after integration. Pages run
`43558753956` succeeded; all six deployed assets matched and the same 23 checks
passed against them, including absence of secondary-label markup and rendering
references. Browser geometry was not measured. Version 0.63.13 documents this
result without changing deployed assets.


## 2026-11-14 — Name purple pushes by their configuration layer

Implementation `4d3974df5808262dbc20d9ea6d06d8620557485c` (0.63.14)
uses the owner-requested purple-stage arrow captions: “Push OS changes”,
“Push AAP config changes” and “Push AAP content changes”. Existing expectations
and README use the same labels. Blue-stage captions, chapter names, routing and
the deletion of underneath-arrow text are preserved.
All 23 local and downloaded deployed-asset checks passed. Pages run
`43560037080` succeeded, with all six public assets matching the implementation.
Browser geometry was not measured. Version 0.63.15 documents this result only.


## 2026-11-14 — Align the content push with the original AAP top

Implementation `6376a603e78697cbd676fd9c07f04db8f20ad8e4` (0.63.18)
changes the blue base-content caption to the owner-requested “Push AAP config”.
The purple “Push AAP content changes” arrow uses a separate content destination
and aligns its line centre with the original AAP's top edge. Its position uses
the rendered source-card offset and caption/track heights, recalculated after
scene rendering and on window resize, instead of a fixed coordinate for this
stage. Other stages clear that inline position, and the existing narrow-layout
CSS override preserves the stacked vertical connectors. No dependency or layout
framework is introduced.

Existing checks cover alignment arithmetic with simulated dimensions, resize
recalculation, stage reset and the requested caption. All 23 checks passed.
The change was integrated with concurrent documentation commits, preserving
their content and reconciling only version/release metadata. Visualization assets
were unchanged by that rebase. Pages run `43561593593` succeeded; all six public
assets matched and all 23 checks passed against the downloaded deployed files.
Actual browser geometry was not measured. Version 0.63.19 documents this result
without changing deployed assets.


## 2026-11-14 — Integrate secret-safe importer authentication diagnostics

Implementation `f3deca3d33fdb89f44107a9c6092dd813b3c786e` adds a protected URI
result and a separate fail-closed assertion exposing only a numeric HTTP
status and fixed error category. Bearer, URL, raw response and exception
details stay hidden. Existing TLS, redirect and credential-source rules
are preserved; no importer or authentication fallback is introduced.

Nine synthetic success/HTTP/TLS/DNS/network/timeout cases passed in the
unchanged cached official Core 2.20.10 image with networking disabled.
Verbose-output canaries remained hidden with protected fixture values
separate from executable YAML. Offline production lint passed.

Version 0.63.21 integrates the diagnostic and its existing implementation
commit with concurrent published documentation and AIOps-rendering work.
Only the tested diagnostic, its test and explanatory documentation differ
from the upstream branch; other published work remains intact. A live
diagnostic rerun is still needed to identify the actual connection cause.


## 2026-11-14 — Use the existing CA for private receiver imports

Implementation `d983450900dabce47b27b9f6f7ecc20af43a1484` (0.63.24)
corrects an observed project-import TLS validation failure by consuming the
existing injected CA credential. It appends that CA to an unchanged default
PEM trust bundle in the importer's private workspace and supplies it to the
verified authentication URI and configuration modules within that job.
Certificate and hostname validation remain enabled; no receiver certificate,
system trust, credential type, login source or importer architecture changes.

Six synthetic local-TLS scenarios passed on actual cached Core 2.20.10:
trusted private CA, missing CA, unrelated CA, malformed CA even with trusted
defaults, preserved default trust and wrong-host rejection. They exercise
real HTTPS requests, inherited module trust, private file mode and cleanup.
Nine protected-result classification cases also passed, including verbose
output canaries. Initial fixture-only literal-template markers were corrected
before the passing run. Tests used disabled external networking and unchanged
images. Focused offline production lint passed with the existing action/filter
mocked. This records code and tests; live binding and import remain separate.
