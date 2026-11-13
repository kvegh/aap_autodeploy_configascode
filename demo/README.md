# AAP CaC: build, capture and deploy again

A new buildless, browser-local visualization of the implemented AAP configuration
paths. The owner-selected presentation keeps configuration data separate from
execution code and follows an original AAP, its first destination and a later
fresh AAP through deployment, project imports, Git-authored additions, manual UI
additions, capture and replay of the complete saved configuration.

Seven chapters contain twelve presenter-controlled stops because the deployment
chapter gives all four stages their own view. The receiving platform is genuinely
hidden initially; Stage 01 reveals a RHEL VM, Stage 03 reveals AAP, and Stage 04
reveals the shared base objects and configuration profiles. Additional project
definitions and configuration revisions follow.
Regional servers and Regional automation are part of the same project import as
Satellite Inventory and Application automation playbooks. The Change in Git stop
updates AAP Logging Config only; it retains the already imported objects.
Backwards navigation, restart and direct links restore the corresponding state.

The interface uses a light canvas and labelled origin colours: blue for base
objects, violet for Git-defined additions and amber for manually created objects.
A left sidebar holds chapter navigation, the four deployment stages, job status,
progress and presenter controls. The main diagram has three columns: compact
repositories, the original AAP and two receiving slots. The repository and
receiving columns share equal widths and matching rows: the first new AAP aligns
with the upper code window, with room for another below. Code previews have more
space; the original AAP is centred between rows. Every installed AAP has the same
prominent platform identity; card dimensions are illustrative. Receiving object
definitions share one continuous content area inside each AAP. Receiving cards
use two independently packed, unboxed object columns. Inventories and Credentials
fill the left; Projects and Job Templates fill the right. AAP configuration follows
as a full-width bottom category, separated by one light horizontal line inset from
the card borders. Its two settings share a compact row, with RHEL beneath. The category is anchored
at the bottom of the receiving AAP body from initial setup, reserving empty
space for objects above so the divider does not follow their growing count.
All component bars follow the Deploy application reference proportions from the
supplied screenshot, including AAP Logging/EDA and RHEL Certificate/Firewall.
Each receiving slot provides its own width reference: the left, middle and right
gutters each use 4.7 percent of that slot's width, with two equal flexible tracks
between them. Bars and gutters scale together without a fixed bar width. The
RHEL boxes retain their compact right-hand stack, aligned with the object and
AAP-setting columns. Text and object counts do not change bar length between
stages. Coloured bar names are two sizes larger (15px-equivalent automation/AAP
names and 14px-equivalent RHEL names, expressed in relative rem units); their
origin badges also increase by two sizes. Category headings, sidebar and code
text are unchanged. Text wraps without an internal receiving scroll pane. On desktop, the receiving/code rows use 95 percent of the
available canvas height, centred with balanced top/bottom spacing rather than a
fixed 860px maximum. Major card borders are dark 3px and Git previews use 14px text;
the repository-type headings use 17px text. If a short viewport still requires scrolling,
the receiving card grows with its contents; no objects are clipped or put in a
separately scrolling inner pane.
The narrow source uses one column to keep names readable. Three internal columns
remain deferred while the owner tries this height-first revision. The sidebar uses larger readable
labels, a persistent current-step heading and distinct completed/current chapters;
chapter changes keep the active navigation item in view. There is no marketing hero
or explanatory scene header above the diagram. Stage 02 is labelled **Prepare OS
for AAP installation**. Strong fills, borders and labelled badges distinguish the
origins. Active connectors use a bold directional line, brief travelling markers
and normal HTML action labels, avoiding stretched SVG text. Arrow strokes,
markers and labels share the highlighted code/object-origin colour: deployment
and base configuration remain blue, Git-defined additions use violet, and
captured manual definitions use amber. The highlighted YAML identifies the
definitions in focus; execution-code highlighting means code being read, not a
change to the public playbook. Reduced motion keeps the strong static activity cue.
Captured manual objects keep their origin and gain an **In Git** badge. The
private repository carries a lock; its YAML is an illustrative decrypted view,
not ciphertext rendered as readable text. The repository-type headings read
**Private Git Repository** and **Public Git Repository**, using larger dark text
at every breakpoint. All examples are synthetic.

A RHEL foundation at the bottom of each AAP card contains the whole
Infrastructure configuration group. Receiving foundations appear when their
VM is created. Milestones show VM creation, OS prerequisites and AAP installation;
backwards navigation and restart reverse them. Stage 01 clones the existing golden
image. Stage 02 prepares host networking, including firewall, nginx and TLS on the
hypervisor. Stage 03 prepares the guest filesystem, subscription/repositories and
Ansible prerequisite before installation. The strip qualifies those host services
and does not claim that the playbooks perform a full guest OS update/upgrade.
The third AAP receives the completed foundation at the existing final replay stop;
no new runtime deployment operation is added. Blue **Firewall config** and
**Certificate config** bars land inside that rectangle from Stage 02 onward.
The Stage 02 connector points into the RHEL foundation, which briefly highlights
on receipt; reduced motion keeps the static configurations and strong boundary.
From base configuration onward, the RHEL group contains Certificate and Firewall
profiles. The infrastructure CaC stop replaces Certificate config with violet v2,
retaining blue Firewall v1. Both replay
to the third instance, while the original retains its blue v1 baseline. The
host-networking scope is explained in this guide; the strip represents the
infrastructure associated with AAP, not a claim that host nginx runs inside its VM.

AAP configuration is a distinct full-width category below inventories, projects,
credentials and Job Templates, separated by a light inset rule. Stage 04 creates blue **AAP Logging Config v1** and **AAP EDA Config
v1**. Change in Git replaces the same logging entry with violet **AAP Logging Config
v2**; EDA v1 and the original AAP's own configuration remain unchanged. Backwards
navigation restores v1. These are illustrative configuration revisions, not AAP
product versions.

The **Infrastructure configuration** group is inside RHEL, outside the AAP
object catalogue. The strip keeps the RHEL label, three preparation indicators
on the left, and two configuration boxes stacked on the right. Redundant group,
host-networking and top-right status captions are deleted, including presenter
rendering code; sections keep concise direct accessibility labels. The redundant status text is removed from the presenter code, not retained
as hidden content. The firewall example preserves its existing saved Job Template inputs;
Certificate config represents the TLS configuration in
`02-infra-config.yml`. The private YAML keeps stable template names with synthetic
`extra_vars.config_revision` inputs and shows the supported
`aap_upstream_hostname` input with generic before/after placeholders for nginx.
These are illustrative revisions; full runtime definitions and dependent TLS
settings are omitted. No new infrastructure playbook or runtime operation is
introduced by the visualization.

The lower AAP rectangle stays hidden during the main story. **Room for another AAP**
appears only in the brief **Ready for another AAP** preparation stop immediately
before the final replay. The **Deploy again** chapter opens this interim stop;
Next deploys the third AAP. A direct `#rebuild` link still opens the completed
replay. Backwards navigation and restart restore the corresponding visibility.
This presentation-only preparation does not add a runtime job or host operation.

During **Change in AAP**, an unframed Linux sysadmin appears above the small
original AAP. The owner-selected figure wears a plain hoodie with its hood down
and glasses, seated in an office chair with a slight forward lean and hands on
the laptop keyboard. One coffee mug and a small amber outage alert provide
restrained role and incident cues. An amber directional
flow carries manual configuration into the first receiving AAP. This actor
appears only at the manual stop; the third-AAP placeholder remains hidden there.
The existing amber inventory/project/credential additions are still absent from
CaC until the subsequent scan. The figure is a generated transparent PNG, stored locally with the page; the old
SVG character is deleted. It adds no runtime service or dependency and preserves
the existing reduced-motion behavior.

The final **Deploy again** stop restores the whole Git-recorded snapshot into
the lower destination: base definitions, Git changes and captured manual-origin
objects, plus AAP Logging Config v2, AAP EDA Config v1, Certificate config v2 and
Firewall Config v1. The first destination remains
intact. The lower card is genuinely hidden before this final stop; going back or
restarting removes its future content. Amber objects on the replayed AAP are
labelled **Captured**, preserving their historical origin while showing that
these definitions came from Git. Three coloured lanes show the complete replay.
This one visual stop groups the existing VM/install/base/object-import paths;
it adds no runtime job, deployment wrapper or live AAP operation.

The object names used throughout the cards and private YAML are:

| Object | Name |
|---|---|
| Base inventory | VMWare Inventory |
| Added inventory | Satellite Inventory |
| AAP settings | AAP Logging Config v1 → v2; AAP EDA Config v1 |
| Base credential | Server access key |
| Application credential | Application auth token |
| Base project | AAP Config-as-Code Git |
| Application project | Application automation playbooks |
| Base Job Template | AAP Config-as-Code jobs |

Names are illustrative; changing these fixtures does not rename live AAP objects.

## Sysadmin illustration

The owner requested a simple, expressive image with familiar Linux-admin cues
and restrained humour. `sysadmin.png` was generated with the built-in imagegen
tool, inspected and copied unchanged into this project. It is a 1536 × 1024 RGBA
PNG with genuine transparent pixels; the original alpha is preserved.
The page displays it as a compact decorative illustration alongside an existing
accessible caption, only during manual changes. It does not replace the flow,
model or controls.

<details>
<summary>Generation prompt</summary>

Use case: illustration-story. Asset type: one small transparent-background character illustration for a professional IT configuration-as-code demo. Primary request: a simple but expressive experienced Linux sysadmin working through an outage, seated at a laptop. Familiar restrained clichés: a plain charcoal hoodie with the hood down, rectangular glasses, short stubble, and exactly one coffee mug. Calm incident-responder posture: seated naturally in an office chair, leaning slightly forward with both hands plausibly on the laptop keyboard, focused eyebrows and an alert, thoughtful expression. A tiny clear amber warning triangle on the laptop screen conveys the outage. Style: polished contemporary editorial illustration with simple bold shapes, clear silhouette, natural adult proportions and minimal shading; friendly and authentic, expressive without caricature or slapstick. Composition: compact landscape 3:2, character facing right in a three-quarter view so the face and laptop are legible, seated figure/chair and small desk complete, tightly composed with a little transparent breathing room. Intended to read at approximately 160 by 110 pixels on a light web canvas: prioritize face, seated posture, hoodie, laptop and amber alert rather than fine detail. Colour: dark navy/charcoal clothing, warm natural skin, light neutral laptop, one amber accent, clear contrast. Background must be genuinely transparent with alpha, no room, no background panel, no scenery, no extra people, no floating UI, no server racks. No lettering, slogans, brand logos, watermark, superhero props, exaggerated funny features, or photorealism.

</details>

## Code and data

`src/scenario.js` contains the story, object fixtures and source links. `src/app.js`
renders the state and navigation. Native browser DOM APIs are sufficient for this
static educational interaction; Ansible modules are not a browser renderer.
There are no external scripts, packages, fonts, analytics, API calls or runtime
services. No live AAP or Git operation is performed by the page.

The public execution preview uses condensed excerpts from the actual playbooks
and configuration roles. Source citations pin the inspected runtime logic at
`f52546d3456614869aa254d220de4a786b96c31f`; that source pin is separate from the
new visualization's own publication revision. Human-facing job labels describe
the operation, rather than inventing new deployed Job Templates.

| Scene | Maintained source |
|---|---|
| Private definitions and public execution code | `tasks/cac-project-checkout.yml`, `tasks/cac-resource-definitions.yml` |
| VM, infrastructure, installer and shared base | `01-linux-vm-setup.yml` through `04-aap-config.yml` |
| Project objects | `deploy-cac-project.yml`, `tasks/cac-resource-definitions.yml` |
| Later Git-defined settings and object updates | `04-aap-config.yml`, `tasks/cac-resource-definitions.yml` |
| Infrastructure configuration Job Template inputs | `deploy-cac-project.yml`, `tasks/cac-resource-definitions.yml` |
| Manual changes returning to configuration | `capture-aap-cac.yml`, `docs/cac-reconciliation.md` |
| Complete saved configuration on another AAP | `01-linux-vm-setup.yml` through `04-aap-config.yml`, `deploy-cac-project.yml`, `tasks/cac-resource-definitions.yml` |

The logging example uses the supported Controller setting
`LOG_AGGREGATOR_ACTION_QUEUE_SIZE`, with synthetic 10000-to-20000 values.
`controller_settings_base.settings` follows the shared/base configuration path;
the generic project importer excludes Controller settings. The Git-change code
preview cites both the existing base reapply and object-import paths. AAP EDA Config
v1 represents a retained decision-environment/rulebook-activation bundle using
supported EDA CaC variables, not a generic EDA global-settings API. Its YAML is
an excerpt, with other required activation fields omitted. Highlighted code is
kept in view within its own preview pane.

As requested, the story abstracts the application trigger and detailed scan/review
mechanics. It does not change those mechanisms: imports and captures remain
explicit operations in the actual implementation. The existing capture adapter
has its documented Controller scope: the scene assumes supported, owned objects.
Credential secrets are maintained separately through protected inputs; scanning
cannot recover newly masked passwords or tokens. The page does not establish
universal AAP export, live deployment or workload acceptance.

## Verification

Use existing Node 18 or newer (verified with Node 22.23.1) and Python; no browser
or dependency installation is needed.

```sh
node --check demo/src/scenario.js
node --check demo/src/app.js
node --test demo/tests/walkthrough.test.cjs
node demo/tests/live.cjs https://kvegh.github.io/aap_autodeploy_configascode/
python3 -m http.server 8765 --directory demo --bind 127.0.0.1
```

Open the local URL only on the host running the server, or through an existing
supported forwarding mechanism. Next/Previous, the seven chapter buttons, the
four stage buttons, arrow keys, R and restart navigate the same state. Source
links open the real implementation. Motion honours reduced-motion preferences.

The Node tests exercise the real scripts against a disposable DOM and check
visible object outcomes, source mapping, true hidden state and reversible
navigation. The live runner downloads only the six allowlisted assets over HTTPS, refuses
redirects, checks size/time limits and requires exact checkout byte parity before
executing the same interaction suite against the downloaded files. It removes
only its own temporary directory and exits nonzero for a failure. Run it from the
checkout matching the intended deployment; an older or not-yet-published checkout
will fail parity. No credentials or live AAP inputs are needed, and no remote data
is changed. These checks exercise deployed HTML/JavaScript interactions in a
disposable DOM; they do not establish rendered browser, desktop or phone layout.
The owner chose existing checks only; no browser installation is authorized.

## Publication

The retained `.github/workflows/deploy-demo.yml` checks the source and publishes
only `index.html`, `icon.svg`, `sysadmin.png`, `src/app.js`, `src/scenario.js`, `src/styles.css`
and a generated `.nojekyll`. Repository Pages must use GitHub Actions. A matching
main push deploys after checks; pull requests only check. There is no build step.
Source publication, GitHub Pages deployment and actual AAP execution are separate
outcomes and must be reported separately.
