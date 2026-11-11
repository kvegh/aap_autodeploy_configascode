(function () {
  'use strict';

  const scenario = window.CacWalkthrough;
  const byId = id => document.getElementById(id);
  const app = document.querySelector('.app');
  const media = window.matchMedia('(prefers-reduced-motion: reduce)');
  let motion = !media.matches;
  let destination = 'remote';
  let index = 0;
  const stepNames = ['The idea', 'Choose a destination', 'Read protected inputs', 'Configure the base', 'Select use cases', 'Import definitions', 'Define, then run', 'Review changes', 'The complete picture'];

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

  function setDestination(value) {
    destination = value;
    const self = destination === 'self';
    byId('target-self').setAttribute('aria-pressed', String(self));
    byId('target-remote').setAttribute('aria-pressed', String(!self));
    byId('target-self').classList.toggle('selected', self);
    byId('target-remote').classList.toggle('selected', !self);
    byId('target-role').textContent = self ? 'The same verified AAP instance' : 'Another verified AAP instance';
    byId('target-explanation').textContent = self
      ? 'These are two roles in the flow: the job configures the AAP on which it runs.'
      : 'The job runs on an existing source AAP and configures another selected AAP.';
  }

  function render(position, updateUrl = true) {
    index = Math.max(0, Math.min(scenario.steps.length - 1, position));
    const step = scenario.stepAt(index);
    byId('phase').textContent = step.phase;
    byId('step-count').textContent = `${String(index + 1).padStart(2, '0')} / ${String(scenario.steps.length).padStart(2, '0')}`;
    byId('current-title').textContent = step.title;
    byId('current-description').textContent = step.description;
    byId('next-label').textContent = step.next;
    byId('next').querySelector('small').textContent = index === scenario.steps.length - 1 ? 'Walk through again' : 'Next step';
    byId('previous').disabled = index === 0;
    byId('progress').setAttribute('aria-valuenow', String(index + 1));
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
