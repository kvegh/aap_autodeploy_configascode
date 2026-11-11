(function () {
  'use strict';

  const scenario = window.CacWalkthrough;
  const byId = id => document.getElementById(id);
  const app = document.querySelector('.app');
  const media = window.matchMedia('(prefers-reduced-motion: reduce)');
  let motion = !media.matches;
  let destination = 'remote';
  let index = 0;
  const stepNames = ['The idea', 'Choose destinations', 'Read protected inputs', '01 · Create the VM', '02 · DNS, TLS + nginx', '03 · Install AAP', '04 · Base AAP configuration', 'Select use cases', 'Import definitions', 'Define, then run', 'Review changes', 'The complete picture'];
  const stages = ['vm', 'infrastructure', 'installation', 'base'];

  const buttons = scenario.steps.map((step, position) => {
    const item = document.createElement('li');
    const button = document.createElement('button');
    button.className = 'step-button';
    button.type = 'button';
    const number = document.createElement('span');
    number.className = 'step-number';
    number.textContent = String(position + 1).padStart(2, '0');
    const label = document.createElement('span');
    label.textContent = stepNames[position];
    button.append(number, label);
    button.addEventListener('click', () => render(position));
    item.append(button);
    byId('step-list').append(item);
    return button;
  });

  function setMotion(value) {
    motion = value;
    app.dataset.motion = motion ? 'on' : 'off';
    byId('motion').setAttribute('aria-pressed', String(motion));
    byId('motion').textContent = motion ? 'Motion on' : 'Motion off';
  }

  function setVisible(id, visible) {
    const element = byId(id);
    if (visible) element.removeAttribute('hidden');
    else element.setAttribute('hidden', '');
    element.setAttribute('aria-hidden', String(!visible));
  }

  function setDestination(value) {
    destination = value;
    const self = destination === 'self';
    byId('target-self').setAttribute('aria-pressed', String(self));
    byId('target-remote').setAttribute('aria-pressed', String(!self));
    byId('target-self').classList.toggle('selected', self);
    byId('target-remote').classList.toggle('selected', !self);
    byId('target-role').textContent = self ? 'The same verified AAP instance' : 'Another verified AAP instance';
    byId('target-explanation').textContent = app.dataset.view === 'deployment'
      ? Number(app.dataset.deploymentStage) === 0
        ? 'The source AAP and prepared test host exist already. The new VM and its AAP appear during deployment.'
        : Number(app.dataset.deploymentStage) < 3
          ? 'The new RHEL VM exists. AAP is not installed until Stage 03.'
          : 'AAP is now installed inside that same VM. Stage 04 applies its base configuration next.'
      : self
      ? 'These are two roles in the flow: the job configures the AAP on which it runs.'
      : 'The job runs on an existing source AAP and configures another selected AAP.';
  }

  function render(position, updateUrl = true) {
    index = Math.max(0, Math.min(scenario.steps.length - 1, position));
    const step = scenario.stepAt(index);
    const deployment = step.view === 'deployment';
    const deploymentStage = step.stage || 0;
    app.dataset.view = deployment ? 'deployment' : 'configuration';
    app.dataset.deploymentStage = String(deploymentStage);
    setVisible('configuration-view', !deployment);
    setVisible('deployment-view', deployment);
    setVisible('node-target', !deployment);
    setVisible('target-controls', !deployment);
    setVisible('deployment-context', deployment);
    byId('architecture-title').textContent = deployment
      ? deploymentStage === 0 ? 'Start with the source AAP and prepared host.' : 'Create the guest. Install the platform.'
      : step.id === 'base' ? 'Stage 04: configure the installed AAP.' : 'Saved intent. Explicit destination.';
    byId('ready-legend').textContent = deployment ? 'Stage result present' : 'Configuration present';
    setDestination(destination);
    byId('phase').textContent = step.phase;
    byId('step-count').textContent = `${String(index + 1).padStart(2, '0')} / ${String(scenario.steps.length).padStart(2, '0')}`;
    byId('current-title').textContent = step.title;
    byId('current-description').textContent = step.description;
    byId('next-label').textContent = step.next;
    byId('next').querySelector('small').textContent = index === scenario.steps.length - 1 ? 'Walk through again' : 'Next step';
    byId('previous').disabled = index === 0;
    byId('progress').setAttribute('aria-valuenow', String(index + 1));
    byId('progress').setAttribute('aria-valuemax', String(scenario.steps.length));
    byId('progress-fill').style.width = `${(index + 1) / scenario.steps.length * 100}%`;
    byId('flow-caption').textContent = step.caption;
    byId('detail-title').textContent = step.heading;
    byId('detail-body').textContent = step.body;
    byId('detail-points').replaceChildren(...step.points.map(text => {
      const item = document.createElement('li');
      item.textContent = text;
      return item;
    }));
    byId('code-title').textContent = step.codeTitle;
    byId('code-example').textContent = step.code;
    byId('source-links').replaceChildren(...step.sources.map(path => {
      const item = document.createElement('li');
      const link = document.createElement('a');
      link.href = scenario.sourceRoot + path;
      link.textContent = path;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      item.append(link);
      return item;
    }));
    ['code', 'desired', 'source', 'target', 'review'].forEach(id => {
      byId(`node-${id}`).classList.toggle('active', step.focus.includes(id));
    });
    ['code', 'desired', 'apply', 'review', 'save'].forEach(id => {
      byId(`route-${id}`).classList.toggle('active', step.routes.includes(id));
    });
    ['base', 'inventory', 'templates', 'eda'].forEach(id => {
      byId(`resource-${id}`).classList.toggle('configured', step.configured.includes(id));
    });
    ['runner', 'state', 'host', 'guest', 'edge', 'platform'].forEach(id => {
      byId(`deploy-${id}`).classList.toggle('active', (step.deploymentFocus || []).includes(id));
      byId(`deploy-${id}`).classList.toggle('ready', (step.deploymentReady || []).includes(id));
    });
    const appearsAtStage = {
      'deploy-state': 1, 'deploy-guest': 1, 'deploy-edge': 2, 'deploy-platform': 3,
      'deploy-golden-copy-label': 1, 'deploy-public-label': 2, 'deploy-dns-label': 2,
      'deploy-frontend-label': 3, 'deploy-note': 3,
      'deploy-route-reserve': 1, 'deploy-route-ssh': 1, 'deploy-route-copy': 1,
      'deploy-route-dns': 2, 'deploy-route-install': 3, 'deploy-route-frontend': 3,
    };
    Object.entries(appearsAtStage).forEach(([id, stage]) => setVisible(id, deploymentStage >= stage));
    setVisible('guest-empty-status', deploymentStage >= 1 && deploymentStage < 3);
    setVisible('deploy-ssh-label', deploymentStage >= 1);
    byId('deployment-description').textContent = deploymentStage === 0
      ? 'An existing source AAP and prepared pinned test hypervisor are ready. No new VM or receiving AAP exists yet.'
      : deploymentStage < 3
        ? `Stage ${String(deploymentStage).padStart(2, '0')} has created a verified RHEL guest${deploymentStage === 2 ? ' and its DNS, TLS and nginx frontend' : ''}. AAP is not installed yet.`
        : 'Stage 03 has installed and verified AAP inside the same RHEL guest. Stage 04 will apply the shared base configuration.';
    ['reserve', 'ssh', 'copy', 'dns', 'install', 'frontend'].forEach(id => {
      byId(`deploy-route-${id}`).classList.toggle('active', (step.deploymentRoutes || []).includes(id));
    });
    byId('platform-status').textContent = (step.deploymentReady || []).includes('platform')
      ? 'Gateway + public endpoint verified' : 'Installed here in Stage 03';
    byId('edge-status').textContent = step.id === 'installation' ? 'TLS + verified AAP upstream'
      : step.id === 'infrastructure' ? 'TLS ready · upstream pending' : 'Frontend prepared in Stage 02';
    const baseIndex = scenario.steps.findIndex(item => item.id === 'base');
    stages.forEach((id, position) => {
      const button = byId(`stage-${id}`);
      const current = step.stage === position + 1;
      button.dataset.state = current ? 'active'
        : index > baseIndex || (step.stage || 0) > position + 1 ? 'complete' : 'pending';
      if (current) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
    });
    buttons.forEach((button, position) => {
      if (position === index) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
      button.classList.toggle('completed', position < index);
    });
    if (updateUrl) window.history.replaceState(null, '', `#${step.id}`);
  }

  byId('next').addEventListener('click', () => render(index === scenario.steps.length - 1 ? 0 : scenario.move(index, 1)));
  byId('previous').addEventListener('click', () => render(scenario.move(index, -1)));
  byId('restart').addEventListener('click', () => { setDestination('remote'); render(0); });
  byId('motion').addEventListener('click', () => setMotion(!motion));
  byId('target-self').addEventListener('click', () => setDestination('self'));
  byId('target-remote').addEventListener('click', () => setDestination('remote'));
  stages.forEach(id => byId(`stage-${id}`).addEventListener('click', () => {
    render(scenario.steps.findIndex(step => step.id === id));
  }));
  document.addEventListener('keydown', event => {
    if (event.altKey || event.ctrlKey || event.metaKey || event.target.closest('input, textarea, select, [contenteditable="true"]')) return;
    if (event.key === 'ArrowRight') { event.preventDefault(); render(scenario.move(index, 1)); }
    if (event.key === 'ArrowLeft') { event.preventDefault(); render(scenario.move(index, -1)); }
    if (event.key.toLowerCase() === 'r') { setDestination('remote'); render(0); }
  });
  media.addEventListener('change', event => setMotion(!event.matches));
  window.addEventListener('hashchange', () => {
    const next = scenario.steps.findIndex(step => `#${step.id}` === window.location.hash);
    if (next >= 0) render(next, false);
  });
  const initial = scenario.steps.findIndex(step => `#${step.id}` === window.location.hash);
  setMotion(motion);
  setDestination(destination);
  render(initial < 0 ? 0 : initial, false);
}());
