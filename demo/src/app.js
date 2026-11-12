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
  let index = Math.max(0, story.steps.findIndex(step => `#${step.id}` === window.location.hash));
  function drawObjects(container, objects) {
    const groups = objectTypes.map(type => {
      const items = objects.filter(object => object.type === type);
      const group = element('section', 'object-group');
      group.append(element('h4', 'object-type', `${type} · ${items.length}`));
      for (const object of items) {
        const item = element('div', 'object-item');
        item.dataset.origin = object.origin;
        item.append(element('span', 'object-name', object.name));
        const label = object.origin === 'base' ? 'Base' : object.origin === 'git' ? 'From Git' : 'Manual';
        item.append(element('span', 'origin-label', label));
        if (object.origin === 'manual' && object.inGit) item.append(element('span', 'git-badge', 'In Git'));
        group.append(item);
      }
      return group;
    });
    container.replaceChildren(...groups);
  }
  function drawConfiguration(container, configurations) {
    container.replaceChildren(...configurations.map(config => {
      const item = element('div', 'object-item configuration-item');
      item.dataset.origin = config.origin;
      item.dataset.configId = config.id;
      item.append(element('span', 'object-name', config.name));
      item.append(element('span', 'origin-label', config.origin === 'base' ? 'Base' : 'From Git'));
      return item;
    }));
  }
  function drawCode(container, lines, activeOrigin) {
    container.replaceChildren(...lines.map((value, position) => {
      const entry = typeof value === 'string' ? { text: value } : value;
      const active = entry.active || (activeOrigin && entry.text.trim() && !entry.text.trimStart().startsWith('#'));
      const line = element('span', `yaml-line${entry.added ? ' line-added' : ''}${active ? ' line-active' : ''}`);
      if (entry.origin || activeOrigin) line.dataset.origin = entry.origin || activeOrigin;
      const number = element('span', 'line-number', String(position + 1).padStart(2, '0'));
      number.setAttribute('aria-hidden', 'true');
      line.append(number);
      const colon = entry.text.indexOf(':');
      if (entry.text.trimStart().startsWith('#')) line.append(element('span', 'yaml-comment', entry.text));
      else if (colon >= 0) line.append(element('span', 'yaml-key', entry.text.slice(0, colon + 1)), element('span', 'yaml-value', entry.text.slice(colon + 1)));
      else line.append(element('span', 'yaml-value', entry.text));
      return line;
    }));
    // Keep the matching YAML section visible without scrolling the whole page.
    const activeLine = [...container.children].find(line => line.classList.contains('line-active'));
    if (container.parentElement) container.parentElement.scrollTop = activeLine
      ? Math.max(0, activeLine.offsetTop - container.offsetTop - 6) : 0;
  }
  const chapterButtons = story.chapters.map(chapter => {
    const button = element('button', 'chapter-button', chapter.title);
    button.type = 'button';
    button.dataset.chapter = chapter.id;
    button.addEventListener('click', () => navigate(chapter.index));
    byId('chapter-list').append(button);
    return button;
  });
  const stages = [...byId('stage-list').querySelectorAll('[data-stage]')];
  stages.forEach(button => button.addEventListener('click', () => navigate(Number(button.dataset.stage))));
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
    chapterButtons.forEach((button, position) => {
      const active = story.chapters[position].id === step.chapter;
      button.classList.toggle('active', active);
      if (active) button.setAttribute('aria-current', 'step'); else button.removeAttribute('aria-current');
    });
    stages.forEach(button => {
      const stage = Number(button.dataset.stage);
      button.classList.toggle('active', step.chapter === 'deployment' && step.stage === stage);
      button.classList.toggle('complete', step.stage >= stage);
      if (step.chapter === 'deployment' && step.stage === stage) button.setAttribute('aria-current', 'step'); else button.removeAttribute('aria-current');
    });
    byId('target-placeholder').hidden = state.targetVisible;
    byId('target-card').hidden = !state.targetVisible;
    byId('target-card').setAttribute('aria-hidden', String(!state.targetVisible));
    byId('target-title').textContent = step.stage < 3 ? 'New RHEL VM' : 'New AAP';
    byId('target-state').textContent = step.status;
    const deploymentActions = ['Deploy', 'Create VM', 'Prepare OS', 'Install AAP'];
    byId('apply-caption').textContent = step.stage < 4 ? deploymentActions[step.stage] : index === 4 ? 'Apply base' : index === 6 ? 'Apply changes' : 'Apply objects';
    byId('apply-detail').textContent = step.stage < 3 ? 'New VM' : 'New AAP';
    byId('target-objects').hidden = step.stage < 4;
    byId('target-configuration-panel').hidden = step.stage < 4;
    byId('target-card').dataset.stage = String(step.stage);
    byId('target-card').classList.toggle('captured', state.captured);
    byId('source-card').classList.toggle('phase-job', step.routes.length > 0);
    byId('config-card').classList.toggle('active', step.routes.includes('flow-config') || step.routes.includes('flow-return'));
    byId('code-card').classList.toggle('active', step.routes.includes('flow-code'));
    for (const id of ['flow-config', 'flow-code', 'flow-apply', 'flow-scan', 'flow-return']) {
      const active = step.routes.includes(id);
      const route = byId(id);
      const sourceFeed = id === 'flow-config' || id === 'flow-code';
      route.hidden = !active && !sourceFeed;
      route.setAttribute('aria-hidden', String(route.hidden));
      route.dataset.origin = state.flowOrigin;
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
    drawObjects(byId('source-objects'), state.sourceObjects);
    drawObjects(byId('target-objects'), state.targetObjects);
    drawCode(byId('config-lines'), story.configurationLines(state));
    drawCode(byId('code-lines'), story.executionLines(state), step.routes.includes('flow-code') ? state.flowOrigin : undefined);
    const executionFile = index === 6 ? '04-aap-config.yml + imports' : index >= 7 ? 'capture-aap-cac.yml' : index === 0 || index >= 5 ? 'cac-resource-definitions.yml' : step.sources[0];
    byId('execution-file-name').textContent = executionFile;
    byId('job-label').textContent = step.job;
    byId('job-status').textContent = step.routes.length ? 'Job in focus' : 'Job Template';
    byId('actor').hidden = !step.actor;
    if (step.actor) {
      byId('actor-title').textContent = step.actor[0];
      byId('actor-description').textContent = step.actor[1];
    }
    byId('feedback').textContent = index === 0 ? 'Two repositories. One repeatable configuration.' : index === 7 ? '3 manual additions · not recorded in Git yet' : index === 8 ? '3 manual additions now recorded in encrypted CaC' : step.stage < 4 ? step.status : `${state.targetObjects.length} automation objects · ${state.targetConfiguration.length} AAP configurations`;
    byId('source-links').replaceChildren(...step.sources.map(path => {
      const link = element('a', 'source-link', path.split('/').at(-1));
      link.href = story.sourceRoot + path;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      return link;
    }));
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
  window.addEventListener('hashchange', () => {
    const nextIndex = story.steps.findIndex(step => `#${step.id}` === window.location.hash);
    navigate(nextIndex < 0 ? 0 : nextIndex, false);
  });
  render();
})();
