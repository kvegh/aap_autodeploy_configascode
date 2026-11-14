/* Presenter-only DOM rendering; no network or AAP calls. See ../README.md#code-and-data. */
(function () {
  'use strict';
  const story = window.AapCacStory;
  const byId = id => document.getElementById(id);
  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const objectTypes = ['Inventories', 'Projects', 'Credentials', 'Job Templates'];
  const originDescriptions = {
    base: 'Base CaC configuration at AAP deployment',
    git: 'New configuration and changes defined in CaC Git',
    manual: 'Manual change made directly in AAP',
  };
  let index = Math.max(0, story.steps.findIndex(step => `#${step.id}` === window.location.hash));
  function drawObjects(container, objects, independentColumns = false) {
    const groups = objectTypes.map(type => {
      const items = objects.filter(object => object.type === type);
      const group = element('section', 'object-group');
      group.append(element('h4', 'object-type', `${type} · ${items.length}`));
      for (const object of items) {
        const item = element('div', 'object-item');
        item.dataset.origin = object.origin;
        item.append(element('span', 'object-name', object.name));
        item.dataset.inGit = String(object.inGit);
        const captureState = object.origin === 'manual' ? (object.inGit ? '; saved in Git' : '; not yet saved in Git') : '';
        item.setAttribute('role', 'group');
        item.setAttribute('aria-label', `${object.name}. ${originDescriptions[object.origin]}${captureState}`);
        group.append(item);
      }
      return group;
    });
    if (independentColumns) {
      // Independent columns pack the groups without reserving empty neighbouring rows.
      const primary = element('div', 'aap-object-column');
      const secondary = element('div', 'aap-object-column');
      primary.append(groups[0], groups[2]);
      secondary.append(groups[1], groups[3]);
      container.replaceChildren(primary, secondary);
    } else container.replaceChildren(...groups);
  }
  function drawConfiguration(container, configurations) {
    container.replaceChildren(...configurations.map(config => {
      const item = element('div', 'object-item configuration-item');
      item.dataset.origin = config.origin;
      item.dataset.configId = config.id;
      item.append(element('span', 'object-name', config.name));
      item.setAttribute('role', 'group');
      item.setAttribute('aria-label', `${config.name}. ${originDescriptions[config.origin]}`);
      return item;
    }));
  }
  function drawRhel(prefix, stage, visible, receivingConfiguration = false, origin = 'base') {
    const foundation = byId(`${prefix}-rhel`);
    foundation.hidden = !visible;
    foundation.dataset.stage = String(stage);
    foundation.classList.toggle('landing', visible && receivingConfiguration);
    foundation.dataset.origin = receivingConfiguration ? origin : 'base';
    // OS prerequisites run in stage 03; stage 02 configures networking on the host.
    const milestones = [
      { title: 'VM created', complete: stage >= 1 },
      { title: 'OS prepared', complete: stage >= 3 },
      { title: 'AAP installed', complete: stage >= 3 },
    ];
    byId(`${prefix}-rhel-progress`).replaceChildren(...(visible ? milestones.map((milestone, position) => {
      const item = element('span', 'rhel-milestone', milestone.title);
      const current = position === 1 && stage < 3;
      item.dataset.state = milestone.complete ? 'complete' : current ? 'current' : 'pending';
      item.setAttribute('aria-label', `${milestone.title}: ${milestone.complete ? 'complete' : current ? 'next preparation' : 'pending'}`);
      return item;
    }) : []));

  }
  function drawCode(container, lines) {
    container.replaceChildren(...lines.map((value, position) => {
      const entry = typeof value === 'string' ? { text: value } : value;
      const active = Boolean(entry.active);
      const line = element('span', `yaml-line${entry.added ? ' line-added' : ''}${active ? ' line-active' : ''}`);
      if (entry.origin) line.dataset.origin = entry.origin;
      if (entry.section) line.dataset.section = entry.section;
      if (entry.focus) line.dataset.focus = 'true';
      const number = element('span', 'line-number', String(position + 1).padStart(2, '0'));
      number.setAttribute('aria-hidden', 'true');
      line.append(number);
      const colon = entry.text.indexOf(':');
      if (entry.text.trimStart().startsWith('#')) line.append(element('span', 'yaml-comment', entry.text));
      else if (colon >= 0) line.append(element('span', 'yaml-key', entry.text.slice(0, colon + 1)), element('span', 'yaml-value', entry.text.slice(colon + 1)));
      else line.append(element('span', 'yaml-value', entry.text));
      return line;
    }));
    // Jump within this complete file; navigation must not scroll the whole page.
    const focusLine = [...container.children].find(line => line.dataset.focus === 'true')
      || [...container.children].find(line => line.classList.contains('line-active'));
    if (container.parentElement) {
      container.parentElement.scrollTop = focusLine
        ? Math.max(0, focusLine.offsetTop - container.offsetTop - 6) : 0;
      container.parentElement.scrollLeft = 0;
    }
  }
  const chapterButtons = story.chapters.map(chapter => {
    const button = element('button', 'chapter-button', chapter.title);
    button.type = 'button';
    button.dataset.chapter = chapter.id;
    button.addEventListener('click', () => navigate(chapter.index));
    byId('chapter-list').append(button);
    return button;
  });
  function render() {
    const state = story.stateAt(index);
    const { step } = state;
    byId('scene-title').textContent = step.title;
    byId('scene-description').textContent = step.description;
    byId('step-count').textContent = `${index + 1} / ${story.steps.length}`;
    byId('progress-fill').style.width = `${((index + 1) / story.steps.length) * 100}%`;
    byId('previous').disabled = index === 0;
    byId('next').disabled = index === story.steps.length - 1;
    byId('next-label').textContent = index === story.steps.length - 1 ? 'Complete' : 'Next';
    byId('next').setAttribute('aria-label', index === story.steps.length - 1 ? 'Story complete' : 'Next step');
    const currentChapter = story.chapters.findIndex(chapter => chapter.id === step.chapter);
    chapterButtons.forEach((button, position) => {
      const active = position === currentChapter;
      const wasActive = button.classList.contains('active');
      button.classList.toggle('active', active);
      button.classList.toggle('complete', position < currentChapter);
      if (active) button.setAttribute('aria-current', 'step'); else button.removeAttribute('aria-current');
      if (active && !wasActive) button.scrollIntoView?.({ block: 'nearest', inline: 'nearest' });
    });
    byId('target-placeholder').hidden = state.targetVisible;
    byId('target-card').hidden = !state.targetVisible;
    byId('target-card').setAttribute('aria-hidden', String(!state.targetVisible));
    const manualChange = step.id === 'manual';
    byId('manual-operator').hidden = !manualChange;
    byId('manual-operator').setAttribute('aria-hidden', String(!manualChange));
    byId('manual-operator-title').textContent = manualChange ? 'Sysadmin · incident response' : '';
    byId('manual-operator-description').textContent = manualChange
      ? 'Creates an inventory, project and credential directly in AAP while resolving an outage.' : '';
    byId('successor-placeholder').hidden = !state.successorPlaceholderVisible;
    byId('successor-placeholder').setAttribute('aria-hidden', String(!state.successorPlaceholderVisible));
    byId('successor-card').hidden = !state.successorVisible;
    byId('successor-card').setAttribute('aria-hidden', String(!state.successorVisible));
    byId('successor-card').dataset.stage = '4';
    drawRhel('target', step.stage, state.targetVisible, ['infrastructure', 'infra-change'].includes(step.id), state.flowOrigin);
    drawRhel('successor', 4, state.successorVisible);
    byId('successor-card').classList.toggle('captured', state.successorVisible);
    byId('target-title').textContent = step.stage < 3 ? 'New RHEL VM' : 'New AAP';
    byId('target-state').textContent = step.status;
    const deploymentActions = ['Deploy', 'Create VM', 'Prepare OS', 'Install AAP'];
    const baseCaptions = { 'base-aap': 'Push AAP config', base: 'Push AAP content' };
    byId('apply-caption').textContent = step.stage < 4 ? deploymentActions[step.stage] : baseCaptions[step.id] || (step.id === 'git-change' ? 'Push AAP config changes' : step.id === 'infra-change' ? 'Push OS changes' : 'Push AAP content changes');
    // The base categories arrive independently; later steps keep prior categories.
    byId('flow-apply').dataset.destination = step.id === 'project' ? 'content'
      : ['infrastructure', 'infra-change'].includes(step.id) ? 'rhel' : 'aap';
    byId('target-objects').hidden = !state.baseContentApplied;
    byId('target-configuration-panel').hidden = !state.aapConfigurationApplied;
    byId('target-infrastructure-panel').hidden = step.stage < 2;
    byId('target-card').dataset.stage = String(step.stage);
    byId('target-card').classList.toggle('captured', state.captured);
    byId('source-card').classList.toggle('phase-job', step.routes.length > 0);
    byId('config-card').classList.toggle('active', step.routes.includes('flow-config') || step.routes.includes('flow-return'));
    byId('code-card').classList.toggle('active', step.routes.includes('flow-code'));
    for (const id of ['flow-config', 'flow-code', 'flow-apply', 'flow-scan', 'flow-return', 'flow-rebuild']) {
      const active = step.routes.includes(id);
      const route = byId(id);
      const sourceFeed = id === 'flow-config' || id === 'flow-code';
      route.hidden = !active && !sourceFeed;
      route.setAttribute('aria-hidden', String(route.hidden));
      route.dataset.origin = state.rebuilding && id === 'flow-code' ? 'git' : state.flowOrigin;
      route.classList.toggle('active', active);
      // Restart brief directional motion when entering another active story step.
      // Reduced-motion styles remove the animation while keeping the active line.
      if (active) {
        for (const animation of route.getAnimations?.({ subtree: true }) || []) {
          animation.cancel();
          animation.play();
        }
      }
    }
    drawConfiguration(byId('source-configuration'), state.sourceConfiguration);
    drawConfiguration(byId('target-configuration'), state.targetConfiguration);
    drawConfiguration(byId('successor-configuration'), state.successorConfiguration);
    drawConfiguration(byId('source-infrastructure'), state.sourceInfrastructure);
    drawConfiguration(byId('target-infrastructure'), state.targetInfrastructure);
    drawConfiguration(byId('successor-infrastructure'), state.successorInfrastructure);
    drawObjects(byId('successor-objects'), state.successorObjects, true);
    drawObjects(byId('source-objects'), state.sourceObjects);
    drawObjects(byId('target-objects'), state.targetObjects, true);
    drawCode(byId('config-lines'), story.configurationLines(state));
    drawCode(byId('code-lines'), story.executionLines(state));
    byId('execution-file-name').textContent = 'playbooks.yml · combined excerpts';
    byId('job-label').textContent = step.job;
    byId('job-status').textContent = step.job;
    byId('actor').hidden = !step.actor;
    if (step.actor) {
      byId('actor-title').textContent = step.actor[0];
      byId('actor-description').textContent = step.actor[1];
    }
    byId('source-links').replaceChildren(...step.sources.map(path => {
      const link = element('a', 'source-link', path.split('/').at(-1));
      link.href = story.sourceRoot + path;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      return link;
    }));
    positionContentPush();
  }
  function positionContentPush() {
    const route = byId('flow-apply');
    // Desktop columns share a top edge; align the line centre with the source card.
    // Narrow layouts retain their existing CSS top:auto override.
    route.style.top = route.dataset.destination === 'content'
      ? `${byId('source-card').offsetTop - byId('apply-caption').offsetHeight - byId('apply-track').offsetHeight / 2}px`
      : '';
  }
  function navigate(nextIndex, updateHash = true) {
    index = story.stateAt(nextIndex).index;
    if (updateHash) window.history.replaceState(null, '', `#${story.steps[index].id}`);
    render();
  }
  byId('previous').addEventListener('click', () => navigate(index - 1));
  byId('next').addEventListener('click', () => navigate(index + 1));
  byId('restart').addEventListener('click', () => navigate(0));
  document.addEventListener('keydown', event => {
    if (event.altKey || event.ctrlKey || event.metaKey || event.target?.closest('input, textarea, select, [contenteditable="true"]')) return;
    if (event.key === 'ArrowRight') { event.preventDefault(); navigate(index + 1); }
    if (event.key === 'ArrowLeft') { event.preventDefault(); navigate(index - 1); }
    if (event.key.toLowerCase() === 'r') { event.preventDefault(); navigate(0); }
  });
  window.addEventListener('resize', positionContentPush);
  window.addEventListener('hashchange', () => {
    const nextIndex = story.steps.findIndex(step => `#${step.id}` === window.location.hash);
    navigate(nextIndex < 0 ? 0 : nextIndex, false);
  });
  render();
})();
