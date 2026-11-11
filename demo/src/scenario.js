(function (root) {
  'use strict';

  const sourceRevision = 'e371c76c4d8e102f152e3a41ccfb76184fa91580';
  const sourceRoot = `https://github.com/kvegh/aap_autodeploy_configascode/blob/${sourceRevision}/`;
  const steps = [
    {
      id: 'overview', phase: 'The idea', title: 'Describe the platform. Keep the knowledge.',
      description: 'AAP configuration lives in reviewed code and encrypted configuration. Follow how an existing AAP turns those inputs into a usable automation catalog.',
      focus: ['code', 'desired', 'source', 'target'], routes: [], configured: [],
      caption: 'An installed AAP is the starting point. This story follows its configuration.',
      heading: 'Two kinds of input. One repeatable approach.',
      body: 'Public automation describes how configuration is applied. Private, Vault-encrypted files hold the desired objects and protected inputs. AAP runs the automation against the selected platform.',
      points: ['Shared base configuration prepares common platform capabilities.', 'Project captures add the definitions for deliberately selected use cases.', 'The page illustrates code behavior; it does not connect to an AAP.'],
      codeTitle: 'The configuration entry points',
      code: '04-aap-config.yml             # shared platform base\ndeploy-selected-use-cases.yml # select and prepare projects\ndeploy-cac-project.yml        # one common project importer',
      sources: ['04-aap-config.yml', 'deploy-cac-project.yml', 'vars/use-case-catalog.yml'],
      next: 'Choose the destination',
    },
    {
      id: 'destination', phase: 'Select', title: 'Make the destination explicit.',
      description: 'The inventory selects the AAP instance. The project importer selects that instance’s saved API access and verifies its HTTPS identity before fetching private configuration.',
      focus: ['source', 'target'], routes: ['apply'], configured: [],
      caption: 'The AAP running the job and the AAP receiving configuration may be the same instance.',
      heading: 'A name in inventory, a verified API connection.',
      body: 'The common importer resolves API access from the existing per-instance token store. The saved record must agree with the selected inventory identity. Only that destination’s access reaches the configuration roles.',
      points: ['Missing, expired or mismatched access stops the import.', 'TLS verification stays enabled.', 'The selector verifies source and destination Controller identities, including self-targeting.'],
      codeTitle: 'Illustrative operator selection',
      code: 'aap_instance_key: demo-instance\n\n# The saved job template fixes the project ID.\n# The importer resolves this inventory entry’s API access.',
      sources: ['tasks/cac-api-auth.yml', 'deploy-selected-use-cases.yml', 'filter_plugins/use_case_setup.py'],
      next: 'Open the reviewed inputs',
    },
    {
      id: 'inputs', phase: 'Read', title: 'Keep automation and protected inputs together in purpose.',
      description: 'The job reads the reviewed automation and the correct encrypted configuration. Git and Vault credentials are supplied by AAP; the checkout is temporary.',
      focus: ['code', 'desired', 'source'], routes: ['code', 'desired'], configured: [],
      caption: 'Public playbooks + private desired configuration → one protected job workspace.',
      heading: 'Shared base and project configuration have different homes.',
      body: 'Base reads the shared platform capture. Each project importer derives its own companion repository and canonical capture from the fixed project ID. Free-form repository and file overrides are refused.',
      points: ['Base: cac/base_CaC_vault.yml.', 'Project: vaults/cac/<project-id>-cac-vault.yml.', 'The project’s saved Git/Vault credentials protect its checkout and decryption.'],
      codeTitle: 'The fixed project capture route',
      code: 'project ID\n  → <project-id>-secrets repository\n  → vaults/cac/<project-id>-cac-vault.yml\n\n# Decrypt only inside the private job workspace.',
      sources: ['tasks/cac-project-checkout.yml', 'filter_plugins/cac_import.py', 'tasks/private-config-cleanup.yml'],
      next: 'Configure the shared base',
    },
    {
      id: 'base', phase: 'Build the base', title: 'Give the platform its common foundation.',
      description: 'Base configuration prepares the shared AAP capabilities: organizations, platform settings, credentials and Automation Hub configuration. It also prepares access for later configuration jobs.',
      focus: ['desired', 'source', 'target'], routes: ['desired', 'apply'], configured: ['base'],
      caption: '04-aap-config.yml applies shared configuration through infra.aap_configuration.',
      heading: 'A configured base makes later imports possible.',
      body: 'The base stage applies the subscription, creates organizations before their Hub credentials, and applies shared definitions through the configuration collection. It provisions the declared Git/Vault bootstrap credentials and prepares persistent API/MCP access.',
      points: ['Automation Hub repository and retention settings belong to the base.', 'Persistent instance access can be published to encrypted CaC and the existing source credential.', 'The base job removes its temporary checkout and revokes its temporary Gateway token.'],
      codeTitle: 'Existing base configuration role',
      code: '- name: Apply shared AAP configuration\n  ansible.builtin.include_role:\n    name: infra.aap_configuration.dispatch\n  vars:\n    dispatch_include_wildcard_vars: false',
      sources: ['04-aap-config.yml', 'tasks/bootstrap-credentials.yml', 'tasks/mcp-access.yml'],
      next: 'Choose the project definitions',
    },
    {
      id: 'selection', phase: 'Choose', title: 'Add the use cases you actually need.',
      description: 'Choose reviewed project configurations, such as disconnected Windows patching or AIOps. The selector prepares their declared prerequisites and calls their existing CaC job templates.',
      focus: ['code', 'desired', 'source', 'target'], routes: ['code', 'desired', 'apply'], configured: ['base'],
      caption: 'Selected projects share one importer; each keeps its own reviewed capture and credentials.',
      heading: 'Select several projects, or import one directly.',
      body: 'deploy-selected-use-cases.yml orchestrates deliberate selections and prerequisite preparation. Each saved “Deploy … CaC” template calls deploy-cac-project.yml directly with its fixed project ID. The standalone importer can also be run on its own.',
      points: ['Unknown, duplicate and unavailable selections are refused.', 'Declared collection dependencies are prepared in Automation Hub when needed.', 'Existing, remote and self-target AAP instances are supported; preparation retains its registered-route checks.'],
      codeTitle: 'One shared importer, project-specific inputs',
      code: '# Saved by the project’s CaC job template:\naap_cac_project_id: disconnected-windows-patching\n\n# The common entry point:\nplaybook: deploy-cac-project.yml',
      sources: ['vars/use-case-catalog.yml', 'deploy-selected-use-cases.yml', 'tasks/selected-use-case-import.yml'],
      next: 'Validate, then import',
    },
    {
      id: 'import', phase: 'Apply', title: 'Check the definitions. Then build their dependencies.',
      description: 'The importer validates capture identity, declared inputs, resource mappings and template labels before applying project objects through the target API.',
      focus: ['source', 'target'], routes: ['apply'], configured: ['base', 'inventory', 'templates', 'eda'],
      caption: 'Dependencies first: ordinary resources → group relationships → templates → workflows → declared EDA definitions.',
      heading: 'An ordered import, with a clear scope.',
      body: 'Only the capture’s explicitly mapped resources are imported. Configuration roles handle the ordinary resources; all group skeletons exist before relationships, job templates precede their workflows, and EDA dependencies precede activation definitions.',
      points: ['Project configuration does not use ambient wildcard variable merging.', 'Required labels and declared readiness checks must pass before resource changes.', 'Existing secret access is preserved where supported; AIOps preparation/readback updates only its selected saved settings.'],
      codeTitle: 'A dependency expressed in the actual importer',
      code: '- name: Import workflow definitions after all referenced job templates\n  ansible.builtin.include_role:\n    name: infra.aap_configuration.controller_workflow_job_templates\n  when: controller_workflows | length > 0',
      sources: ['deploy-cac-project.yml', 'tasks/cac-resource-definitions.yml', 'tasks/cac-template-labels.yml'],
      next: 'See what “configured” means',
    },
    {
      id: 'configured', phase: 'Use', title: 'The catalog is ready. Workloads have their own start.',
      description: 'Projects, inventories, credentials, templates and workflows are now definitions in AAP. Running the application or a deployment workflow remains a separate operator action.',
      focus: ['target'], routes: [], configured: ['base', 'inventory', 'templates', 'eda'],
      caption: 'Configuration import creates the automation catalog; application execution is a separate action.',
      heading: 'A useful boundary between defining and running.',
      body: 'The project importer excludes job launches, workflow launches, schedules and resource deletion. New EDA activation definitions are created disabled, while existing activation states are preserved.',
      points: ['Importing Windows configuration does not start patching.', 'Importing AIOps configuration does not launch the recovery demo.', 'Removing a definition from CaC does not itself delete the corresponding live object.'],
      codeTitle: 'Existing application-launch exclusions',
      code: 'aap_configuration_dispatcher_exclude_roles:\n  - controller_job_launch\n  - controller_workflow_launch\n\n# EDA definitions are handled separately:\nrestart: false',
      sources: ['tasks/cac-resource-definitions.yml', 'filter_plugins/cac_import.py', 'action_plugins/aap_cac_activation.py'],
      next: 'Review later changes',
    },
    {
      id: 'capture', phase: 'Review', title: 'Bring reviewed changes back into configuration.',
      description: 'The existing scoped capture reads Controller configuration and compares it with encrypted CaC. Preview comes first, with an encrypted report for human review.',
      focus: ['desired', 'target', 'review'], routes: ['review', 'save'], configured: ['base', 'inventory', 'templates', 'eda'],
      caption: 'Controller → scoped read-only preview → review → an explicitly accepted encrypted Git update.',
      heading: 'A reviewed return path, with defined limits.',
      body: 'The current capture adapter covers an explicitly owned AutoDeploy Controller scope. It checks visibility and conflicts against accepted baselines. A reviewed digest binds a proposed update to the inputs and source revision.',
      points: ['First baseline initialization and later updates are explicit choices.', 'Commit and push default to false; preview does not change AAP.', 'Gateway, EDA and Automation Hub are outside this capture adapter. Masked secret rotations need a separate protected input update.'],
      codeTitle: 'The default capture mode',
      code: 'aap_cac_capture_scope: autodeploy\naap_cac_capture_mode: preview\naap_cac_capture_commit: false\naap_cac_capture_push: false',
      sources: ['capture-aap-cac.yml', 'docs/cac-reconciliation.md', 'src/cac_compare.py'],
      next: 'See the complete picture',
    },
    {
      id: 'complete', phase: 'The complete picture', title: 'Keep the platform’s knowledge ready for its next home.',
      description: 'Reviewed automation, encrypted desired configuration and explicit destination access make the configuration reusable. Each import has a defined target, a defined scope and a result to verify.',
      focus: ['code', 'desired', 'source', 'target', 'review'], routes: ['code', 'desired', 'apply', 'review', 'save'], configured: ['base', 'inventory', 'templates', 'eda'],
      caption: 'Describe → validate → configure → review. Reuse the same configuration approach on the selected AAP.',
      heading: 'Recreation is an outcome to verify.',
      body: 'These are implemented configuration paths. A successful import proves the selected definitions were installed. Complete environment recovery and production takeover require their own functional verification.',
      points: ['Maintain shared settings separately from instance-specific values.', 'Keep protected inputs encrypted and use the selected instance’s access.', 'Verify configuration results, then deliberately run and test the required workloads.'],
      codeTitle: 'Keep exploring the actual source',
      code: 'Shared foundation  →  04-aap-config.yml\nProject import     →  deploy-cac-project.yml\nSelection          →  deploy-selected-use-cases.yml\nReviewed capture   →  capture-aap-cac.yml',
      sources: ['docs/cac-project-import.md', 'docs/selected-use-cases.md', 'docs/cac-reconciliation.md'],
      next: 'Start again',
    },
  ];

  function stepAt(index) {
    if (!Number.isInteger(index)) throw new TypeError('Step index must be an integer.');
    return steps[Math.max(0, Math.min(steps.length - 1, index))];
  }

  function move(index, direction) {
    if (!Number.isInteger(index) || ![-1, 1].includes(direction)) throw new TypeError('Choose a valid step and direction.');
    return Math.max(0, Math.min(steps.length - 1, index + direction));
  }

  const api = { steps, stepAt, move, sourceRevision, sourceRoot, runtimeVersion: '0.50.13' };
  function freeze(value) {
    if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
    return value;
  }
  freeze(api);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CacWalkthrough = api;
}(typeof globalThis !== 'undefined' ? globalThis : this));
