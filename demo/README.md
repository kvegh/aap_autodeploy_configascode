# AAP Configuration as Code walkthrough

A buildless, browser-local explanation of the implemented deployment and
configuration flow, using an azure, blue and slate palette.
It follows the visual approach used by the Windows and AIOps GitHub Pages demos:
a guided story, a highlighted architecture and an explanation for each step.
It sends no API requests, reads no live configuration and contains only generic
illustrative selections.

The story is grounded in runtime 0.50.13, source
`e371c76c4d8e102f152e3a41ccfb76184fa91580`. The twelve-step story gives all four
normal stages their own visual step: `01-linux-vm-setup.yml`,
`02-infra-config.yml`, `03-aap-install.yml` and `04-aap-config.yml`. It then covers
selected project CaC and the reviewed capture path. Both the selector and the
importer support verified self/remote targets in this source. Physical-host
deployment remains outside the page.

The provisioning diagram shows the existing source AAP running jobs against one
pinned test hypervisor and its new guest. It includes encrypted allocation, the
preserved golden image, fresh guest identity, DNS/TLS/nginx and AAP installed
inside that guest. The API diagram shows Base AAP and project configuration on
the selected receiving AAP. The four prominent stage buttons select the actual
phase and diagram. Application deployment jobs remain separate actions; no
future AIOps-triggered workload installation is depicted as current behavior.

## Files and preview

`index.html` owns both diagrams and accessible page structure. `src/scenario.js`
owns the reviewed narrative and pinned public source links. `src/app.js` owns
navigation, highlighting and the illustrative destination switch;
`src/styles.css` owns presentation and responsive/reduced-motion behavior.
No package manager, downloaded fonts, runtime service or frontend build is used.

Use the existing Python and Node tools:

```sh
python3 -m http.server 8765 --directory demo --bind 127.0.0.1
node --check demo/src/scenario.js
node --check demo/src/app.js
node --test demo/tests/*.test.cjs
git diff --check
```

Open `http://127.0.0.1:8765/` locally. Previous/Next, the step list, arrow keys and
R navigate the story. The destination switch distinguishes two roles within
one AAP from two separate AAP instances. Motion starts disabled when the browser
requests reduced motion. A step can be linked directly, for example `#import`.

The Node fixtures execute the real scripts against a small disposable DOM.
They check reversible navigation, configured-resource state, deep links,
self-target explanation, deployment/configuration views, stage-specific routes
and results, the blue palette, reduced motion and pinned source links. They do not
establish browser layout or actual AAP behavior. Browser checks and screenshots
are separate validation when an existing browser is available.

## GitHub Pages

The narrowly scoped `.github/workflows/deploy-demo.yml` checks the scripts and
interaction fixtures, then publishes only an explicit allowlist of public HTML,
CSS, JS and SVG assets. Tests, repository configuration and protected content are
excluded from that artifact. The workflow deploys on main; pull requests run its
checks without deployment. Repository Pages must use GitHub Actions as its source.

Keep the source revision and narrative current when runtime behavior changes.
Changes to base or project preparation can have infrastructure side effects;
the visualization presents the configuration flow and does not run those stages.
