/* Story and illustrative objects. Source mapping and scope: ../README.md#code-and-data. */
(function (root) {
  'use strict';
  const sourceRevision = '20f70af1c9006a06d422ffa368d38a9f25ae2e13';
  const sourceRoot = `https://github.com/kvegh/aap_autodeploy_configascode/blob/${sourceRevision}/`;
  const chapters = [
    ['separation', 'Data & code', 0], ['deployment', 'A new AAP', 1],
    ['project', 'Apply objects', 5], ['git-change', 'Change in Git', 6],
    ['manual', 'Change in AAP', 7], ['capture', 'Back to Git', 8],
  ].map(([id, title, index]) => ({ id, title, index }));
  const baseObjects = [
    { id: 'platform', type: 'Inventories', name: 'Platform', origin: 'base' },
    { id: 'platform-code', type: 'Projects', name: 'Platform automation', origin: 'base' },
    { id: 'managed-access', type: 'Credentials', name: 'Managed host access', origin: 'base' },
    { id: 'platform-jobs', type: 'Job Templates', name: 'Platform jobs', origin: 'base' },
  ];
  const baseConfiguration = [
    { id: 'logging', name: 'Logging Config v1', origin: 'base', version: 1 },
    { id: 'eda', name: 'EDA Config v1', origin: 'base', version: 1 },
  ];
  const projectObjects = [
    { id: 'operations', type: 'Inventories', name: 'Operations', origin: 'git' },
    { id: 'app-code', type: 'Projects', name: 'Application automation', origin: 'git' },
    { id: 'app-access', type: 'Credentials', name: 'Application access', origin: 'git' },
    { id: 'app-jobs', type: 'Job Templates', name: 'Deploy application', origin: 'git' },
  ];
  const editedObjects = [
    { id: 'regional', type: 'Inventories', name: 'Regional servers', origin: 'git' },
    { id: 'regional-code', type: 'Projects', name: 'Regional automation', origin: 'git' },
  ];
  const manualObjects = [
    { id: 'emergency', type: 'Inventories', name: 'Emergency servers', origin: 'manual' },
    { id: 'quick-fix', type: 'Projects', name: 'Quick-fix automation', origin: 'manual' },
    { id: 'temporary-access', type: 'Credentials', name: 'Temporary access', origin: 'manual' },
  ];
  const steps = [
    { id: 'separation', chapter: 'separation', title: 'Data & code', description: 'Private configuration and public playbooks feed the original AAP.', stage: 0, job: 'Ready to deploy', status: 'Source AAP', routes: [], sources: ['tasks/cac-project-checkout.yml', 'tasks/cac-resource-definitions.yml'] },
    { id: 'vm', chapter: 'deployment', title: '01 / Create a new home.', description: 'The original AAP creates a RHEL VM on the prepared host. It is a new guest, with no AAP content yet.', stage: 1, job: '01 · Create VM', status: 'VM created', routes: ['flow-config', 'flow-code', 'flow-apply'], sources: ['01-linux-vm-setup.yml'] },
    { id: 'infrastructure', chapter: 'deployment', title: 'Prepare OS for AAP installation', description: 'DNS, TLS certificates and nginx connect that same guest to its reserved address. The VM is ready for AAP installation.', stage: 2, job: '02 · Prepare OS for AAP installation', status: 'OS prepared for AAP installation', routes: ['flow-code', 'flow-apply'], sources: ['02-infra-config.yml'] },
    { id: 'installation', chapter: 'deployment', title: '03 / Install AAP inside the VM.', description: 'The platform is installed in the new guest. A second AAP now exists; its automation catalogue comes next.', stage: 3, job: '03 · Install AAP', status: 'AAP installed', routes: ['flow-code', 'flow-apply'], sources: ['03-aap-install.yml'] },
    { id: 'base', chapter: 'deployment', title: '04 / Apply the shared foundation.', description: 'Base CaC creates the shared objects plus Logging Config v1 and EDA Config v1 on the new AAP.', stage: 4, job: '04 · Configure Base AAP', status: 'Base configuration applied', routes: ['flow-config', 'flow-code', 'flow-apply'], sources: ['04-aap-config.yml'] },
    { id: 'project', chapter: 'project', title: 'Turn definitions into more automation.', description: 'A configuration Job Template on the original AAP combines the private YAML with the public playbooks. Additional objects appear on the receiving AAP.', stage: 4, job: 'Deploy objects', status: 'Project objects applied', routes: ['flow-config', 'flow-code', 'flow-apply'], sources: ['deploy-cac-project.yml', 'tasks/cac-resource-definitions.yml'] },
    { id: 'git-change', chapter: 'git-change', title: 'New requirements? Change the YAML.', description: 'Your team updates Logging Config v1 to v2 and adds another inventory and project in CaC. The original AAP applies the changes; EDA Config v1 stays unchanged.', stage: 4, job: 'Apply configuration', status: 'Logging v2 applied; EDA v1 unchanged', routes: ['flow-config', 'flow-code', 'flow-apply'], actor: ['Configuration author', 'Updates Logging Config to v2 and adds Regional servers and Regional automation. EDA Config v1 is retained.'], sources: ['04-aap-config.yml', 'tasks/cac-resource-definitions.yml'] },
    { id: 'manual', chapter: 'manual', title: 'Sometimes, changes happen in the UI.', description: 'An operator adds an inventory, project and credential directly on the receiving AAP. They exist there now, but their definitions are not in Git yet.', stage: 4, job: 'Ready to scan configuration', status: 'Manual objects added', routes: [], actor: ['AAP operator', 'Adds objects directly in the receiving AAP.'], sources: ['capture-aap-cac.yml'] },
    { id: 'capture', chapter: 'capture', title: 'Bring those changes back into Git.', description: 'A configuration scan Job Template on the original AAP reads the added objects and brings their definitions into the encrypted CaC. The next setup can use them too.', stage: 4, job: 'Scan AAP configuration', status: 'Added definitions recorded in Git', routes: ['flow-scan', 'flow-return'], sources: ['capture-aap-cac.yml', 'docs/cac-reconciliation.md'] },
  ];
  function stateAt(index) {
    if (!Number.isInteger(index)) throw new TypeError('Step index must be an integer.');
    const position = Math.max(0, Math.min(steps.length - 1, index));
    const step = steps[position];
    const targetObjects = [
      ...(step.stage >= 4 ? baseObjects : []), ...(position >= 5 ? projectObjects : []),
      ...(position >= 6 ? editedObjects : []), ...(position >= 7 ? manualObjects : []),
    ].map(object => ({ ...object, inGit: object.origin !== 'manual' || position >= 8 }));
    const configObjects = [...baseObjects, ...projectObjects, ...(position >= 6 ? editedObjects : []), ...(position >= 8 ? manualObjects : [])];
    // Replace one stable configuration entry; preserve EDA and the source's state.
    const desiredConfiguration = baseConfiguration.map(config => config.id === 'logging' && position >= 6
      ? { ...config, name: 'Logging Config v2', origin: 'git', version: 2 }
      : { ...config });
    const sourceConfiguration = baseConfiguration.map(config => ({ ...config }));
    const targetConfiguration = step.stage >= 4 ? desiredConfiguration.map(config => ({ ...config })) : [];
    const flowOrigin = position >= 7 ? 'manual' : position >= 5 ? 'git' : 'base';
    return { index: position, step, flowOrigin, desiredConfiguration, sourceConfiguration, targetConfiguration, targetObjects, configObjects, sourceObjects: baseObjects.map(object => ({ ...object, inGit: true })), targetVisible: step.stage > 0, captured: position >= 8 };
  }
  function configurationLines(state) {
    const fields = [['Inventories', 'controller_inventories'], ['Projects', 'controller_projects'], ['Credentials', 'controller_credentials'], ['Job Templates', 'controller_templates']];
    const lines = [{ text: '# Illustrative decrypted view · stored encrypted', origin: 'base' }];
    const logging = state.desiredConfiguration.find(config => config.id === 'logging');
    const readingConfiguration = state.step.routes.includes('flow-config');
    const loggingActive = readingConfiguration && logging.origin === state.flowOrigin;
    const edaActive = readingConfiguration && state.flowOrigin === 'base';
    for (const text of [
      `# ${logging.name}`,
      'controller_settings_base:',
      '  settings:',
      `    LOG_AGGREGATOR_ACTION_QUEUE_SIZE: ${logging.version === 1 ? 10000 : 20000}`,
    ]) lines.push({ text, origin: logging.origin, active: loggingActive });
    for (const text of [
      '# EDA Config v1 · illustrative configuration excerpt',
      'eda_decision_environments_base:',
      '  - name: Event runtime',
      '    image_url: <decision-environment-image>',
      'eda_rulebook_activations_base:',
      '  - name: Event policy',
      '    decision_environment: Event runtime',
      '    log_level: info',
    ]) lines.push({ text, origin: 'base', active: edaActive });

    for (const [type, key] of fields) {
      lines.push({ text: `${key}:`, origin: 'base' });
      for (const object of state.configObjects.filter(item => item.type === type)) {
        const added = object.origin === 'manual' || (state.index === 6 && editedObjects.some(item => item.id === object.id));
        const readingConfiguration = state.step.routes.includes('flow-config') || state.step.routes.includes('flow-return');
        const focusedObject = state.index === 6 ? editedObjects.some(item => item.id === object.id) : object.origin === state.flowOrigin;
        const active = readingConfiguration && focusedObject;
        lines.push({ text: `  - name: ${object.name}`, origin: object.origin, added, active });
        if (type === 'Projects') lines.push({ text: '    scm_url: <automation-repository>', origin: object.origin, added, active });
      }
      if (type === 'Inventories') lines.push(
        { text: 'controller_inventory_sources:', origin: 'base' },
        { text: '  - name: Platform source', origin: 'base' },
        { text: '    inventory: Platform', origin: 'base' },
        { text: '    source: scm', origin: 'base' },
      );
    }
    lines.push({ text: '# API access uses verified HTTPS', origin: 'base' });
    return lines;
  }
  function executionLines(state) {
    const stage = state.step.stage;
    if (state.index >= 8) return ['# Accepted update · illustrative job inputs', 'aap_cac_capture_mode: update', 'aap_cac_capture_commit: true', 'aap_cac_capture_push: true', '', '# Implementation: capture-aap-cac.yml'];
    if (state.index === 7) return ['# capture-aap-cac.yml · excerpt', '- name: Extract and compare through protected Vault API and Git inputs', '  aap_cac_capture:', '    scope: "{{ aap_cac_capture_scope }}"'];
    if (state.index === 6) return ['# Platform settings · 04-aap-config.yml', '- name: Apply shared AAP configuration', '  ansible.builtin.include_role:', '    name: infra.aap_configuration.dispatch', '  vars:', '    dispatch_include_wildcard_vars: false', '', '# Project objects · tasks/cac-resource-definitions.yml', '- name: Import ordinary configuration resources without wildcard merging or workload execution', '  ansible.builtin.include_role:', '    name: infra.aap_configuration.dispatch'];
    if (state.index >= 5 || state.index === 0) return ['# Inventories, projects and credentials · excerpt', '- name: Import ordinary configuration resources without wildcard merging or workload execution', '  ansible.builtin.include_role:', '    name: infra.aap_configuration.dispatch', '', '# Job Templates, after their dependencies', '- name: Import job templates after their persistent credential dependencies', '  ansible.builtin.include_role:', '    name: infra.aap_configuration.controller_job_templates'];
    if (stage === 1) return ['# 01-linux-vm-setup.yml · excerpt', '- name: Create a test VM only after shared name reservation and pinned recovery preflight', '  hosts: hypervisor', '  become: true', '  gather_facts: false'];
    if (stage === 2) return ['# 02-infra-config.yml · excerpt', '- name: "Configure DNS, certificate, and nginx reverse proxy"', '  hosts: hypervisor', '  become: true', '  gather_facts: false'];
    if (stage === 3) return ['# 03-aap-install.yml · excerpt', '- name: Run AAP installer', '  ansible.builtin.command:', '    cmd: ansible-playbook -i inventory ansible.containerized_installer.install', '    chdir: "{{ installer_extract_dir }}/{{ installer_dir_name }}"', '  async: 7200', '  poll: 30'];
    return ['# 04-aap-config.yml · excerpt', '- name: Configure new AAP instance (config-as-code)', '  hosts: localhost', '  connection: local', '  gather_facts: false', '', '  # Verified target API', '  # aap_validate_certs: true'];
  }
  const api = { sourceRevision, sourceRoot, chapters, steps, stateAt, configurationLines, executionLines };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.AapCacStory = api;
})(typeof window !== 'undefined' ? window : globalThis);
