/* DevNexus front end: vanilla JS, no build step. Every figure shown is fetched from the REST API (/api/...).
   DOM is built with text nodes (no HTML string injection) so user-entered text cannot inject markup. */
(() => {
  'use strict';

  const USER_KEY = 'devnexus.user';
  const PROJECT_KEY = 'devnexus.project';
  const STATES = ['Created', 'Assigned', 'Generating', 'In Review', 'Testing', 'Ready for Deployment', 'Deployed'];
  const BUSY_STATES = ['Assigned', 'Generating', 'Testing'];
  const state = { users: [], me: null };

  // ---------- tiny helpers ----------
  const $ = (sel, root = document) => root.querySelector(sel);
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === false || v == null) continue;
      if (k === 'class') el.className = v;
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? '' : v);
    }
    for (const kid of kids.flat()) {
      if (kid == null || kid === false) continue;
      el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
    }
    return el;
  }
  const put = (el, ...kids) => el.replaceChildren(...kids.flat().filter((k) => k != null));
  const slug = (s) => s.replace(/\s+/g, '-');
  const when = (iso) => (iso ? new Date(iso).toLocaleString() : '—');
  const badge = (status) => h('span', { class: `badge s-${slug(status)}` }, status);
  const levelBadge = (lvl) => h('span', { class: `badge lvl-${lvl}` }, lvl);
  const empty = (msg) => h('div', { class: 'empty' }, msg);

  let toastTimer;
  function toast(msg, isError = false) {
    const el = $('#toast');
    el.textContent = msg;
    el.className = `toast${isError ? ' error' : ''}`;
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (el.hidden = true), isError ? 7000 : 3500);
  }

  async function api(path, { method = 'GET', body, query } = {}) {
    const url = new URL(path, location.origin);
    for (const [k, v] of Object.entries(query || {})) if (v !== '' && v != null) url.searchParams.set(k, v);
    const headers = { Accept: 'application/json' };
    if (state.me) headers['X-User-Id'] = String(state.me.user_id);
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const res = await fetch(url, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    const data = res.status === 204 ? null : await res.json().catch(() => null);
    if (!res.ok) {
      const err = (data && data.error) || { code: 'http_error', message: res.statusText };
      const detail = Array.isArray(err.details) && err.details.length ? ' (' + err.details.map((d) => `${d.field}: ${d.message}`).join('; ') + ')' : '';
      const e = new Error(`${err.message}${detail}`);
      e.code = err.code;
      e.status = res.status;
      throw e;
    }
    return data;
  }

  // Run an async action, surface errors as a toast, and never leave a button stuck disabled.
  async function act(button, fn) {
    if (button) button.disabled = true;
    try {
      return await fn();
    } catch (e) {
      toast(e.message, true);
    } finally {
      if (button) button.disabled = false;
    }
  }

  function formJson(form) {
    const out = {};
    for (const [k, v] of new FormData(form).entries()) if (v !== '') out[k] = v;
    return out;
  }

  const isPM = () => state.me && state.me.role === 'project_manager';
  const isDev = () => state.me && state.me.role === 'developer';

  // ---------- shell: user switcher, bell, nav ----------
  async function initShell() {
    $('#nav-toggle').addEventListener('click', (ev) => {
      const open = $('#nav').classList.toggle('open');
      ev.currentTarget.setAttribute('aria-expanded', String(open));
    });
    state.users = await fetch('/api/users').then((r) => r.json());
    const stored = Number(localStorage.getItem(USER_KEY));
    state.me = state.users.find((u) => u.user_id === stored) || state.users[0] || null;
    const select = $('#user-select');
    put(select, state.users.map((u) => h('option', { value: u.user_id, selected: state.me && u.user_id === state.me.user_id }, userLabel(u))));
    select.addEventListener('change', () => {
      localStorage.setItem(USER_KEY, select.value);
      location.reload();
    });
    refreshBell();
    setInterval(refreshBell, 10000);
  }

  // Demo user names already carry the role, e.g. "Aryan (Project Manager)"; only append it when they don't.
  function userLabel(u) {
    const role = u.role.replace('_', ' ');
    return u.name.toLowerCase().replace(/[()]/g, '').includes(role) ? u.name : `${u.name} · ${role}`;
  }

  async function refreshBell() {
    if (!state.me) return;
    try {
      const unread = await api('/api/notifications', { query: { unread_only: true } });
      const bell = $('#bell');
      bell.textContent = unread.length;
      bell.hidden = unread.length === 0;
    } catch (_) { /* the bell is best-effort */ }
  }

  async function projectFilter(select, { allowAll }) {
    const projects = await api('/api/projects');
    const saved = localStorage.getItem(PROJECT_KEY) || '';
    put(select, allowAll ? h('option', { value: '' }, 'All projects') : null,
      projects.map((p) => h('option', { value: p.project_id, selected: String(p.project_id) === saved }, p.name)));
    if (!allowAll && !select.value && projects.length) select.value = String(projects[0].project_id);
    select.addEventListener('change', () => localStorage.setItem(PROJECT_KEY, select.value));
    return projects;
  }

  // ---------- dashboard (FR-6, FR-11, FR-12) ----------
  async function pageDashboard() {
    const select = $('#project-filter');
    const projects = await projectFilter(select, { allowAll: true });
    $('#dash-empty').hidden = projects.length > 0;
    async function load() {
      const d = await api('/api/dashboard', { query: { project_id: select.value } });
      const cov = d.coverage.average_pct;
      put($('#kpis'),
        kpi('Progress', `${d.progress_pct}%`, 'deployed tasks ÷ all tasks'),
        kpi('Tasks', d.totals.tasks, `${d.totals.by_group.queued} queued · ${d.totals.by_group.in_progress} in progress · ${d.totals.by_group.completed} completed · ${d.totals.by_group.failed} failed`),
        kpi('Test coverage', cov == null ? '—' : `${cov}%`, cov == null ? 'no test results yet' : `simulated · ${d.coverage.tasks_with_results} task(s)`),
        kpi('Risk', levelBadge(d.risk.level), `score ${d.risk.score} (probability × impact)`));
      const max = Math.max(1, d.totals.tasks);
      put($('#status-bars'), Object.entries(d.totals.by_status).map(([s, n]) =>
        h('div', { class: 'bar-row' }, badge(s), h('div', { class: `bar${s === 'Failed' ? ' red' : ''}` }, h('span', { style: `width:${(100 * n) / max}%` })), h('strong', {}, n))));
      const vmax = Math.max(1, ...d.velocity.map((v) => v.deployed));
      put($('#velocity'), d.velocity.map((v) =>
        h('div', { title: `${v.sprint_start} → ${v.sprint_end}` }, h('strong', {}, v.deployed), h('span', { style: `height:${(100 * v.deployed) / vmax}%` }), v.sprint_start.slice(5))));
      put($('#risk'), riskView(d.risk));
    }
    // PLAN-10 / NFR-7: getting-started checklist. Every tick comes from API data (never from local state); the
    // card disappears once all steps are done, or when the user hides it (a per-browser convenience only).
    const GS_KEY = 'devnexus.getting-started.hidden';
    const gsHidden = () => { try { return localStorage.getItem(GS_KEY) === '1'; } catch (_) { return false; } };
    $('#gs-hide').addEventListener('click', () => {
      try { localStorage.setItem(GS_KEY, '1'); } catch (_) { /* storage blocked: hide for this view only */ }
      $('#getting-started').hidden = true;
    });
    // Every step is monotonic (audit rows are append-only, deployments and tasks are never removed), so once all
    // steps are done the checklist stops polling.
    let gsComplete = false;
    async function loadChecklist() {
      if (gsComplete || gsHidden()) return;
      const [projects, all, approvals, riskReports] = await Promise.all([
        api('/api/projects'), api('/api/dashboard'), api('/api/audit', { query: { action: 'task.approve', limit: 1 } }),
        api('/api/audit', { query: { action: 'risk_report.generate', limit: 1 } })]);
      const s = all.totals.by_status;
      const first = projects[0];
      const projectLink = first ? `/projects/${first.project_id}` : '/projects';
      const steps = [
        ['Create a project', 'Project Manager', projects.length > 0, '/projects'],
        ['Add a requirement', 'Project Manager', projects.some((p) => p.requirement_count > 0), projectLink],
        ['Create a task from a requirement', 'Developer', all.totals.tasks > 0, projectLink],
        ['Assign a task to the Code Generation Agent', 'Developer', all.totals.tasks - s.Created > 0, projectLink],
        ['Review and approve the generated code', 'Developer', approvals.length > 0, projectLink],
        ['Authorise a deployment', 'Developer or Project Manager', s.Deployed > 0, projectLink],
        ['Generate a risk report', 'Project Manager', riskReports.length > 0, '/reports'],
      ];
      const done = steps.filter((st) => st[2]).length;
      gsComplete = done === steps.length;
      $('#getting-started').hidden = gsComplete;
      $('#gs-count').textContent = `${done} of ${steps.length} steps done. Switch the acting user at the top to play each role.`;
      $('#gs-bar').style.width = `${(100 * done) / steps.length}%`;
      put($('#gs-steps'), steps.map(([label, who, ok, href]) => h('li', { class: ok ? 'done' : '' },
        h('span', { class: 'tick', 'aria-hidden': 'true' }, ok ? '✓' : ''),
        h('div', {}, h('span', { class: 'step' }, ok ? label : h('a', { href }, label)), ' ',
          h('span', { class: 'who' }, `(${who})`), h('span', { class: 'sr-only' }, ok ? ' — done' : ' — to do')))));
    }
    const kpi = (label, value, sub) => h('div', { class: 'card kpi' }, h('div', { class: 'label' }, label), h('div', { class: 'value' }, value), h('small', {}, sub));
    await Promise.all([load(), loadChecklist()]);
    setInterval(() => { load().catch(() => {}); loadChecklist().catch(() => {}); }, 5000);
  }

  function riskView(risk) {
    if (!risk.items.length) return h('p', { class: 'muted' }, 'No delayed tasks, repeated agent failures or schedule slippage detected.');
    return h('div', { class: 'table-wrap' }, h('table', {},
      h('thead', {}, h('tr', {}, ['Category', 'Finding', 'Prob.', 'Impact', 'Score', 'Level', 'Tasks'].map((c) => h('th', {}, c)))),
      h('tbody', {}, risk.items.map((i) => h('tr', {},
        h('td', {}, i.category.replace('_', ' ')), h('td', {}, i.description), h('td', {}, i.probability), h('td', {}, i.impact),
        h('td', {}, i.score), h('td', {}, levelBadge(i.level)),
        h('td', {}, i.task_ids.map((id) => h('a', { href: `/tasks/${id}`, style: 'margin-right:.4rem' }, `#${id}`))))))));
  }

  // ---------- projects list ----------
  async function pageProjects() {
    put($('#project-list'), empty('Loading…'));
    const projects = await api('/api/projects');
    $('#create-project-card').hidden = !isPM();
    $('#dev-note').hidden = isPM();
    put($('#project-list'), projects.length ? h('table', {},
      h('thead', {}, h('tr', {}, ['Project', 'Status', 'Requirements', 'Tasks', 'Dates'].map((c) => h('th', {}, c)))),
      h('tbody', {}, projects.map((p) => h('tr', {},
        h('td', {}, h('a', { href: `/projects/${p.project_id}` }, p.name)), h('td', {}, p.status), h('td', {}, p.requirement_count), h('td', {}, p.task_count),
        h('td', {}, [p.start_date, p.end_date].filter(Boolean).join(' → ') || '—'))))) : empty('No projects yet.'));
    $('#project-form').addEventListener('submit', (ev) => {
      ev.preventDefault();
      const form = ev.currentTarget;
      act(ev.submitter, async () => {
        const p = await api('/api/projects', { method: 'POST', body: formJson(form) });
        location.href = `/projects/${p.project_id}`;
      });
    });
  }

  // ---------- one project: requirements, pipeline, tasks (FR-2, FR-3, FR-4) ----------
  async function pageProject() {
    const pid = Number(document.body.dataset.projectId);
    let current = null;
    let editingReq = null;
    async function load() {
      const [p, reqs, tasks] = await Promise.all([
        api(`/api/projects/${pid}`), api(`/api/projects/${pid}/requirements`), api('/api/tasks', { query: { project_id: pid } })]);
      $('#project-title').textContent = p.name;
      $('#project-sub').textContent = `${p.status} · ${p.requirement_count} requirement(s) · ${p.task_count} task(s)`;
      put($('#project-info'), h('dl', {}, [['Problem statement', p.problem_statement], ['Scope', p.scope], ['Objectives', p.objectives]]
        .flatMap(([k, v]) => [h('dt', {}, h('strong', {}, k)), h('dd', { style: 'margin:0 0 .6rem' }, v)])));
      current = p;
      $('#project-edit-open').hidden = !isPM() || !$('#project-edit-form').hidden;
      put($('#req-table'), reqs.length ? h('table', {},
        h('thead', {}, h('tr', {}, ['#', 'Description', 'Type', 'Priority', 'Status', isPM() ? '' : null].filter((c) => c != null).map((c) => h('th', {}, c)))),
        h('tbody', {}, reqs.map((r) => h('tr', {}, h('td', {}, r.req_id), h('td', {}, r.description), h('td', {}, r.type), h('td', {}, r.priority),
          h('td', {}, h('span', { class: `badge req-${r.status}` }, r.status === 'Approved' ? 'Approved · locked' : r.status)),
          isPM() ? h('td', { class: 'row-actions' }, reqActions(r)) : null)))) : empty('No requirements yet.'));
      $('#req-form').hidden = !isPM();
      fillPipeline(p.pipeline_config);
      put($('#task-req'), reqs.map((r) => h('option', { value: r.req_id }, `#${r.req_id} ${r.description.slice(0, 60)}`)));
      $('#task-form').hidden = !isDev() || reqs.length === 0;
      $('#task-note').hidden = isDev() && reqs.length > 0;
      $('#task-note').textContent = !isDev() ? 'Only a Developer can create and assign tasks.' : 'Add a requirement first: every task is created from a requirement.';
      put($('#task-table'), tasks.length ? h('table', {},
        h('thead', {}, h('tr', {}, ['#', 'Title', 'Status', 'Group', 'Runs', 'Last change'].map((c) => h('th', {}, c)))),
        h('tbody', {}, tasks.map((t) => h('tr', {}, h('td', {}, t.task_id), h('td', {}, h('a', { href: `/tasks/${t.task_id}` }, t.title)), h('td', {}, badge(t.status)),
          h('td', {}, t.status_group.replace('_', ' ')), h('td', {}, t.run_count), h('td', {}, when(t.status_changed_at)))))) : empty('No tasks yet.'));
    }
    // PLAN-09: edit / approve requirements and edit project details (PATCH endpoints, contract C-3). PM only.
    function reqActions(r) {
      if (r.status !== 'Draft') return h('span', { class: 'muted' }, '—');
      return [
        h('button', { type: 'button', class: 'secondary small', onclick: () => openReqEdit(r) }, 'Edit'),
        h('button', { type: 'button', class: 'small', onclick: (ev) => {
          if (!confirm(`Approve requirement #${r.req_id}? Approved requirements are locked and cannot be edited.`)) return;
          act(ev.currentTarget, async () => {
            await api(`/api/requirements/${r.req_id}`, { method: 'PATCH', body: { status: 'Approved' } });
            toast(`Requirement #${r.req_id} approved`);
            await load();
          });
        } }, 'Approve'),
      ];
    }
    function openReqEdit(r) {
      const f = $('#req-edit-form');
      editingReq = r.req_id;
      $('#req-edit-title').textContent = `Edit requirement #${r.req_id}`;
      f.description.value = r.description;
      f.type.value = r.type;
      f.priority.value = r.priority;
      f.hidden = false;
      f.description.focus();
    }
    function openProjectEdit() {
      const f = $('#project-edit-form');
      for (const k of ['name', 'problem_statement', 'scope', 'objectives', 'status']) f[k].value = current[k];
      f.start_date.value = current.start_date || '';
      f.end_date.value = current.end_date || '';
      f.hidden = false;
      $('#project-edit-open').hidden = true;
      f.name.focus();
    }
    function closeProjectEdit() {
      $('#project-edit-form').hidden = true;
      $('#project-edit-open').hidden = !isPM();
    }
    $('#project-edit-open').addEventListener('click', openProjectEdit);
    $('#project-edit-cancel').addEventListener('click', closeProjectEdit);
    $('#project-edit-form').addEventListener('submit', (ev) => {
      ev.preventDefault();
      const f = ev.currentTarget;
      act(ev.submitter, async () => {
        const body = {};
        for (const k of ['name', 'problem_statement', 'scope', 'objectives', 'status']) body[k] = f[k].value;
        body.start_date = f.start_date.value || null; // an emptied date field clears the date
        body.end_date = f.end_date.value || null;
        await api(`/api/projects/${pid}`, { method: 'PATCH', body });
        closeProjectEdit();
        toast('Project details saved');
        await load();
      });
    });
    $('#req-edit-cancel').addEventListener('click', () => ($('#req-edit-form').hidden = true));
    $('#req-edit-form').addEventListener('submit', (ev) => {
      ev.preventDefault();
      const f = ev.currentTarget;
      act(ev.submitter, async () => {
        await api(`/api/requirements/${editingReq}`, { method: 'PATCH', body: { description: f.description.value, type: f.type.value, priority: f.priority.value } });
        f.hidden = true;
        toast(`Requirement #${editingReq} saved`);
        await load();
      });
    });
    function fillPipeline(cfg) {
      const f = $('#pipeline-form');
      f.querySelectorAll('input[name=agent]').forEach((c) => (c.checked = cfg.active_agents.includes(c.value)));
      f.retry_limit.value = cfg.retry_limit;
      f.max_loc.value = cfg.constraints.max_loc;
      f.target_environment.value = cfg.constraints.target_environment;
      f.delay_threshold_hours.value = cfg.constraints.delay_threshold_hours;
      f.querySelectorAll('input, select').forEach((el) => (el.disabled = !isPM()));
      $('#pipeline-save').hidden = !isPM();
      $('#pipeline-note').hidden = isPM();
    }
    $('#req-form').addEventListener('submit', (ev) => {
      ev.preventDefault();
      const form = ev.currentTarget;
      act(ev.submitter, async () => {
        await api(`/api/projects/${pid}/requirements`, { method: 'POST', body: formJson(form) });
        form.reset();
        toast('Requirement added');
        await load();
      });
    });
    $('#pipeline-form').addEventListener('submit', (ev) => {
      ev.preventDefault();
      const f = ev.currentTarget;
      act(ev.submitter, async () => {
        await api(`/api/projects/${pid}/pipeline`, { method: 'PUT', body: {
          active_agents: [...f.querySelectorAll('input[name=agent]:checked')].map((c) => c.value),
          retry_limit: Number(f.retry_limit.value),
          constraints: { max_loc: Number(f.max_loc.value), target_environment: f.target_environment.value, delay_threshold_hours: Number(f.delay_threshold_hours.value) },
        } });
        toast('Pipeline saved');
        await load();
      });
    });
    $('#task-form').addEventListener('submit', (ev) => {
      ev.preventDefault();
      const form = ev.currentTarget;
      act(ev.submitter, async () => {
        const body = formJson(form);
        body.project_id = pid;
        body.req_id = Number(body.req_id);
        const t = await api('/api/tasks', { method: 'POST', body });
        location.href = `/tasks/${t.task_id}`;
      });
    });
    await load();
  }

  // ---------- one task: lifecycle, review, tests, deployment, history (FR-4..FR-9, FR-14) ----------
  async function pageTask() {
    const tid = Number(document.body.dataset.taskId);
    let diffKey = null;
    let timer;

    async function load() {
      const t = await api(`/api/tasks/${tid}`);
      $('#task-title').textContent = t.title;
      $('#task-sub').textContent = `Task #${t.task_id} · created ${when(t.created_at)}`;
      $('#back-link').href = `/projects/${t.project_id}`;
      const group = t.status_group.replace('_', ' ');
      put($('#task-badges'), badge(t.status), group !== t.status.toLowerCase() ? h('span', { class: 'badge group', title: 'Status group (FR-6)' }, group) : null);
      renderStepper(t.status);
      put($('#task-meta'), h('p', {}, t.description || h('span', { class: 'muted' }, 'No description.')),
        h('p', { class: 'muted' }, `Rework budget: ${Math.max(0, t.run_count - 1)} of ${t.retry_limit} rework/retry attempt(s) used` + (t.rework_allowed ? '.' : ' - the retry limit is reached, so this task is reported as a risk.')));
      renderActions(t);
      await renderDiff(t);
      put($('#runs'), t.runs.length ? table(['Run', 'Branch', 'Started', 'Status', 'Error'],
        t.runs.map((r) => [r.run_id, h('code', {}, r.branch_name), when(r.started_at), r.status, r.error_message || '—'])) : empty('No agent runs yet.'));
      put($('#tests'), t.test_results.length ? table(['Test', 'Run', 'Passed', 'Failed', 'Coverage', 'When'],
        t.test_results.map((r) => [r.test_id, r.run_id, r.passed_count, r.failed_count, `${r.coverage_pct}%`, when(r.created_at)])) : empty('No test results yet.'));
      put($('#deployments'), t.deployments.length ? table(['Deployment', 'Environment', 'Status', 'When'],
        t.deployments.map((d) => [d.deploy_id, d.environment, d.status, when(d.deployed_at)])) : empty('Not deployed yet.'));
      put($('#history'), t.history.length ? table(['When', 'Actor', 'Action', 'Detail'],
        t.history.map((e) => [when(e.timestamp), e.actor_name, h('code', {}, e.action), h('span', { style: 'white-space:pre-wrap' }, e.detail || '—')])) : empty('No history.'));
      clearTimeout(timer);
      timer = setTimeout(() => load().catch(() => {}), BUSY_STATES.includes(t.status) ? 1500 : 6000);
    }

    function table(head, rows) {
      return h('table', {}, h('thead', {}, h('tr', {}, head.map((c) => h('th', {}, c)))),
        h('tbody', {}, rows.map((r) => h('tr', {}, r.map((c) => h('td', {}, c))))));
    }

    function renderStepper(status) {
      const failed = status === 'Failed';
      const idx = failed ? STATES.indexOf('Generating') : STATES.indexOf(status);
      const items = STATES.map((s, i) => h('li', { class: i < idx || (status === 'Deployed' && i <= idx) ? 'done' : i === idx && !failed ? 'current' : '' }, s));
      if (failed) items.push(h('li', { class: 'failed' }, 'Failed'));
      put($('#stepper'), items);
    }

    function renderActions(t) {
      const box = $('#actions');
      const a = t.allowed_actions;
      const post = (path, body, okMsg) => act(null, async () => {
        const r = await api(`/api/tasks/${tid}/${path}`, { method: 'POST', body });
        if (r && r.outcome) toast(r.message, r.outcome === 'failed');
        else toast(okMsg);
        await load();
      });
      const buttons = [];
      if (a.includes('assign')) buttons.push(h('button', { onclick: () => post('assign', { agent_type: 'code_generation' }, 'Assigned to the Code Generation Agent') }, 'Assign to Code Generation Agent'));
      if (a.includes('approve')) buttons.push(h('button', { onclick: () => post('approve', {}, 'Approved: tests are running') }, 'Approve code'));
      if (a.includes('reject')) buttons.push(h('button', { class: 'danger', onclick: () => { $('#reject-form').hidden = false; $('#reject-form').comments.focus(); } }, 'Reject…'));
      if (a.includes('retry')) buttons.push(h('button', { onclick: () => post('retry', undefined, 'Retrying') }, 'Retry after failure'));
      if (a.includes('tests')) buttons.push(h('button', { class: 'secondary', onclick: () => post('tests', undefined, 'Tests re-run started') }, 'Re-run tests'));
      if (a.includes('deploy')) {
        const env = h('select', { id: 'deploy-env', 'aria-label': 'Environment' }, h('option', { value: 'staging' }, 'staging'), h('option', { value: 'production' }, 'production'));
        buttons.push(h('span', { class: 'row inline' }, env, h('button', { onclick: () => post('deploy', { environment: env.value }) }, 'Authorise deployment')));
      }
      put(box, buttons);
      if (!a.includes('reject')) $('#reject-form').hidden = true;
      $('#actions-note').textContent = buttons.length ? '' : idleReason(t);
    }

    function idleReason(t) {
      const role = state.me ? state.me.role.replace('_', ' ') : 'user';
      const map = {
        Created: 'Waiting for a Developer to assign this task to the Code Generation Agent.',
        Assigned: 'Queued: the Code Generation Agent is about to start.',
        Generating: 'The Code Generation Agent is working. This page refreshes automatically.',
        'In Review': 'Waiting for a Developer to review the generated code.',
        Testing: 'The Testing Agent is running the automated tests.',
        'Ready for Deployment': 'All tests passed. A Developer or Project Manager can authorise deployment.',
        Deployed: 'This task is complete: the build was deployed.',
      };
      if (t.status === 'Failed') {
        map.Failed = !t.rework_allowed
          ? 'An agent error occurred and the retry limit is reached, so this task cannot be retried; it is reported as a risk.'
          : isDev()
            ? 'An agent error occurred. Retrying needs the Code Generation agent to be active in the project pipeline.'
            : 'An agent error occurred. Only a Developer can retry this task.';
      }
      return `${map[t.status] || ''} (You are acting as: ${role}.)`;
    }

    async function renderDiff(t) {
      const key = `${t.runs.length}:${t.status}`;
      if (key === diffKey) return;
      diffKey = key;
      if (!t.runs.length) return put($('#diff'), empty('No code has been generated yet.'));
      try {
        const d = await api(`/api/tasks/${tid}/diff`);
        put($('#diff'), h('p', { class: 'muted' }, 'Branch ', h('code', {}, d.branch), ` → ${d.base}. Agents commit only to this feature branch; nothing is merged until deployment is authorised.`),
          d.files.length ? d.files.map((f) => h('details', { open: true }, h('summary', {}, f.path),
            h('pre', { class: 'diff' }, f.diff.split('\n').map((line) => h('div', { class: line.startsWith('+') && !line.startsWith('+++') ? 'add' : line.startsWith('-') && !line.startsWith('---') ? 'del' : line.startsWith('@@') || line.startsWith('---') || line.startsWith('+++') ? 'meta' : '' }, line || ' '))))) : empty('No differences against main (already merged).'));
      } catch (e) {
        put($('#diff'), empty(e.message));
      }
    }

    $('#reject-cancel').addEventListener('click', () => ($('#reject-form').hidden = true));
    $('#reject-form').addEventListener('submit', (ev) => {
      ev.preventDefault();
      const form = ev.currentTarget;
      act(ev.submitter, async () => {
        await api(`/api/tasks/${tid}/reject`, { method: 'POST', body: { comments: form.comments.value } });
        form.reset();
        toast('Rejected: the agent is reworking the code');
        await load();
      });
    });
    await load();
  }

  // ---------- reports (FR-10, FR-11) ----------
  async function pageReports() {
    const select = $('#project-filter');
    const projects = await projectFilter(select, { allowAll: true });
    if (!select.value && projects.length) select.value = String(projects[0].project_id); // risk needs a project
    const gen = $('#gen-risk');
    gen.hidden = !isPM();
    async function load() {
      const pid = select.value;
      const e = await api('/api/reports/estimation', { query: { project_id: pid } });
      const inr = (n) => '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 });
      put($('#estimation'),
        table2([['Tasks counted', e.task_count], ['Size', `${e.loc_total} LOC (${e.loc_actual} generated + ${e.loc_planned} planned) = ${e.kloc} KLOC`],
          ['Effort', `${e.effort_person_months} person-months`], ['Schedule', `${e.duration_months} months`], ['Average team', e.team_size], ['Indicative cost', inr(e.cost_inr)]]),
        h('p', { class: 'muted' }, e.model),
        h('p', { class: 'muted' }, `Phase 2 baseline for the full 8,000 LOC system: ${e.phase2_baseline.effort_person_months} person-months, ${e.phase2_baseline.duration_months} months, ${inr(e.phase2_baseline.cost_inr)}.`));
      if (!pid) {
        put($('#risk-live'), h('p', { class: 'muted' }, 'Choose a project to see its risk assessment and reports.'));
        put($('#risk-stored'), empty('—'));
        gen.disabled = true;
        return;
      }
      gen.disabled = false;
      const d = await api('/api/dashboard', { query: { project_id: pid } });
      put($('#risk-live'), h('p', {}, 'Current level: ', levelBadge(d.risk.level), ` (score ${d.risk.score})`), riskView(d.risk));
      try {
        const r = await api('/api/reports/risk', { query: { project_id: pid } });
        put($('#risk-stored'), h('p', {}, `Report #${r.report_id}, generated ${when(r.generated_at)}: `, levelBadge(r.risk_level)), riskView(r.details));
      } catch (err) {
        put($('#risk-stored'), empty(err.status === 404 ? 'No risk report has been generated for this project yet.' : err.message));
      }
    }
    const table2 = (rows) => h('table', {}, h('tbody', {}, rows.map(([k, v]) => h('tr', {}, h('th', {}, k), h('td', {}, v)))));
    select.addEventListener('change', () => load().catch((e) => toast(e.message, true)));
    gen.addEventListener('click', () => act(gen, async () => {
      await api('/api/reports/risk', { method: 'POST', query: { project_id: select.value } });
      toast('Risk report generated');
      await load();
    }));
    await load();
  }

  // ---------- audit trail (FR-14) ----------
  async function pageAudit() {
    const form = $('#audit-form');
    async function load() {
      const rows = await api('/api/audit', { query: { ...formJson(form), limit: 200 } });
      put($('#audit-table'), rows.length ? h('table', {},
        h('thead', {}, h('tr', {}, ['#', 'When', 'Actor', 'Action', 'Target', 'Detail'].map((c) => h('th', {}, c)))),
        h('tbody', {}, rows.map((r) => h('tr', {}, h('td', {}, r.log_id), h('td', {}, when(r.timestamp)), h('td', {}, r.actor_name), h('td', {}, h('code', {}, r.action)),
          h('td', {}, r.target_ref.startsWith('task:') ? h('a', { href: `/tasks/${r.target_ref.split(':')[1]}` }, r.target_ref) : r.target_ref),
          h('td', { style: 'white-space:pre-wrap' }, r.detail || '—'))))) : empty('No audit entries match.'));
    }
    form.addEventListener('submit', (ev) => { ev.preventDefault(); act(ev.submitter, load); });
    $('#audit-reset').addEventListener('click', () => setTimeout(() => act(null, load), 0));
    await load();
  }

  // ---------- notifications (FR-13) ----------
  async function pageNotifications() {
    async function load() {
      const notes = await api('/api/notifications');
      put($('#notes'), notes.length ? h('table', {},
        h('thead', {}, h('tr', {}, ['When', 'Type', 'Message', ''].map((c) => h('th', {}, c)))),
        h('tbody', {}, notes.map((n) => h('tr', { class: n.is_read ? '' : 'unread' },
          h('td', {}, when(n.created_at)), h('td', {}, n.kind.replace('_', ' ')),
          h('td', {}, n.task_id ? h('a', { href: `/tasks/${n.task_id}` }, n.message) : n.message),
          h('td', {}, n.is_read ? '' : h('button', { class: 'secondary', onclick: (ev) => act(ev.currentTarget, async () => { await api(`/api/notifications/${n.notification_id}/read`, { method: 'POST' }); await load(); refreshBell(); }) }, 'Mark read')))))) : empty('No notifications for this user yet.'));
    }
    await load();
  }

  // ---------- boot ----------
  const PAGES = { dashboard: pageDashboard, projects: pageProjects, project: pageProject, task: pageTask, reports: pageReports, audit: pageAudit, notifications: pageNotifications };

  document.addEventListener('DOMContentLoaded', async () => {
    try {
      await initShell();
      const d = document.body.dataset;
      const page = d.taskId ? 'task' : d.projectId ? 'project' : d.page;
      if (!state.me) return toast('No users found: start the server with demo users enabled.', true);
      await PAGES[page]();
    } catch (e) {
      toast(e.message, true);
    }
  });
})();
