const approvals = {
  landing: { title: "Approve launch page direction", intro: "A short, focused page designed to turn high-intent visitors into consultation requests.", why: "The market plan needs one clear conversion path before content and outreach can point people anywhere.", evidence: "Local demand, competitor review, and customer-language research support this direction.", cost: "Included in the $680 approved monthly budget. No additional spend is requested.", next: "Build work begins, then quality and accessibility review happens before anything goes live." },
  ad: { title: "Confirm paid search test budget", intro: "A small, controlled search test to learn whether high-intent local demand can convert efficiently.", why: "Organic activity is being prepared, but a defined test can validate demand faster without committing to a campaign.", evidence: "The selected search themes appeared consistently in the regional opportunity review.", cost: "$240 maximum. It remains at $0 until you approve. The test automatically pauses at the agreed limit.", next: "A draft campaign and audience summary are prepared for your review. Nothing will publish until the final check." },
  claim: { title: "Review the customer promise", intro: "Choose the clearest promise for the launch page and social assets.", why: "A single, specific customer promise keeps the website, video, outreach, and paid test aligned.", evidence: "The wording is based on repeated customer concerns and gaps in competitor messaging.", cost: "No cost. This is a positioning decision.", next: "The selected wording will be used in draft assets, then checked for clarity and customer-facing risk." }
};

const approvalStack = document.querySelector('#approval-stack');
const evidenceList = document.querySelector('.evidence-list');
const evidence = [
  ['Regional demand review', 'Search demand, service language, and location signals · checked today', 'High'],
  ['Competitive messaging scan', 'Three active competitors reviewed for positioning gaps and proof points', 'High'],
  ['Customer-problem synthesis', 'Recurring needs and objections distilled from supplied customer material', 'Medium'],
  ['Target and budget assumptions', 'Range-based model with stated assumptions and a low-risk test path', 'Medium']
];
const storageKey = 'aibo-control-centre-'+(location.pathname.includes('/custom/')?'custom':'standard')+'-v1';
let workspace = { business: 'Northline Services', industry: 'Home & local services', region: 'Greater London', goal: 'Turn validated demand into booked consultations', initialized: false };
let usage = {
  monthlyLimit: 60,
  taskLimit: 12,
  hardStop: true,
  used: 12.46,
  activity: [
    ['Market opportunity brief', 'Scoped regional research; reused approved context', 4.18, 'Complete'],
    ['Launch-page direction', 'Focused draft and quality review', 3.54, 'Complete'],
    ['Video concept options', 'Three story routes from the approved positioning', 2.86, 'Complete'],
    ['Plan coordination', 'Specialist routing and clear owner actions', 1.88, 'Complete']
  ]
};
try {
  const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
  if (saved.workspace) workspace = { ...workspace, ...saved.workspace };
  if (saved.approvals) { Object.keys(approvals).forEach(key => delete approvals[key]); Object.assign(approvals, saved.approvals); }
  if (saved.evidence) { evidence.splice(0, evidence.length, ...saved.evidence); }
  if (saved.usage) usage = { ...usage, ...saved.usage };
} catch { /* Start safely with the visible sample workspace. */ }
const persist = () => localStorage.setItem(storageKey, JSON.stringify({ workspace, approvals, evidence, usage }));
const refreshWorkspace = () => { document.querySelectorAll('.workspace-switcher b').forEach(el => el.textContent = workspace.business); document.querySelector('.breadcrumb span').textContent = workspace.business; document.querySelector('.focus-label b').textContent = workspace.goal; };
const escapeHtml = value => String(value).replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[character]));

function renderApprovals() {
  approvalStack.innerHTML = Object.entries(approvals).map(([key, item]) => `<article class="approval-card"><div><small>Decision required</small><b>${item.title}</b><p>${item.intro}</p></div><button class="primary-button" data-open-approval="${key}">Review decision →</button></article>`).join('');
}
function renderEvidence() {
  evidenceList.innerHTML = evidence.map(([title, detail, confidence]) => `<article class="source-card"><span class="source-mark">⌕</span><div><b>${escapeHtml(title)}</b><small>${escapeHtml(detail)}</small></div><span class="confidence">${escapeHtml(confidence)} confidence</span></article>`).join('');
}
function renderUsage() {
  const limit = Math.max(usage.monthlyLimit, 1);
  const percent = Math.min(100, Math.round((usage.used / limit) * 100));
  const remaining = Math.max(0, limit - usage.used);
  const money = value => `$${Number(value).toFixed(2)}`;
  document.querySelector('#usage-total').innerHTML = `${money(usage.used)} <small>of ${money(limit)} limit</small>`;
  document.querySelector('#usage-percent').textContent = `${percent}%`;
  document.querySelector('#usage-remaining').textContent = money(remaining);
  document.querySelector('#usage-cap').textContent = money(usage.taskLimit);
  document.querySelector('#usage-bar').style.width = `${percent}%`;
  document.querySelector('#usage-status').textContent = usage.used >= limit ? 'Limit reached' : usage.hardStop ? 'Pause protected' : 'Within limit';
  document.querySelector('#usage-status').classList.toggle('at-limit', usage.used >= limit);
  document.querySelector('#overview-usage').innerHTML = `${money(usage.used)} <small>of ${money(limit)} AI & tool limit</small>`;
  document.querySelector('#overview-usage-percent').textContent = `${percent}%`;
  document.querySelector('#usage-table').innerHTML = usage.activity.map(([name, purpose, cost, state, billingSource]) => {
    const label = billingSource === 'claude_code_subscription' ? 'Claude plan' : billingSource === 'codex_chatgpt' ? 'ChatGPT/Codex plan' : money(cost);
    return `<div class="usage-row"><div><b>${escapeHtml(name)}</b><small>${escapeHtml(purpose)}</small></div><span>${escapeHtml(state)}</span><b>${label}</b></div>`;
  }).join('');
}

const modal = document.querySelector('#modal-backdrop');
const toast = document.querySelector('#toast');
let activeApproval = null;
function openApproval(key) {
  activeApproval = key;
  const item = approvals[key];
  if (!item) return;
  document.querySelector('#modal-title').textContent = item.title;
  document.querySelector('#modal-intro').textContent = item.intro;
  document.querySelector('#modal-why').textContent = item.why;
  document.querySelector('#modal-evidence').textContent = item.evidence;
  document.querySelector('#modal-cost').textContent = item.cost;
  document.querySelector('#modal-next').textContent = item.next;
  modal.classList.add('open'); modal.setAttribute('aria-hidden', 'false');
}
function closeModal(){ modal.classList.remove('open'); modal.setAttribute('aria-hidden', 'true'); }
function showToast(message){ toast.textContent = message; toast.classList.add('show'); setTimeout(()=>toast.classList.remove('show'), 3200); }
function showView(id) {
  document.querySelectorAll('.dashboard-view').forEach(view => view.classList.toggle('active', view.id === id));
  document.querySelectorAll('.nav-item').forEach(link => link.classList.toggle('active', link.dataset.view === id));
  document.querySelector('.breadcrumb b').textContent = id.charAt(0).toUpperCase() + id.slice(1);
  window.scrollTo({top:0, behavior:'smooth'});
}

document.addEventListener('click', event => {
  const nav = event.target.closest('[data-view]');
  const target = event.target.closest('[data-view-target]');
  const approval = event.target.closest('[data-open-approval]');
  if (nav) { event.preventDefault(); showView(nav.dataset.view); document.querySelector('.sidebar').classList.remove('open'); }
  if (target) { event.preventDefault(); showView(target.dataset.viewTarget); }
  if (approval) { event.preventDefault(); openApproval(approval.dataset.openApproval); }
});
document.querySelector('.modal-close').addEventListener('click', closeModal);
modal.addEventListener('click', event => { if(event.target === modal) closeModal(); });
document.querySelector('#approve-action').addEventListener('click', () => { if (!activeApproval) return; delete approvals[activeApproval]; persist(); renderApprovals(); const remaining = Object.keys(approvals).length; document.querySelector('#approval-count').textContent = remaining; document.querySelector('.nav-badge').textContent = remaining; closeModal(); showToast('Approved. The next safe step is now ready to begin.'); });
document.querySelector('#request-change').addEventListener('click', () => { closeModal(); showToast('Change request noted. Your Chief of Staff will bring back a revised option.'); });
const setupBackdrop = document.querySelector('#setup-backdrop');
const openSetup = () => { document.querySelector('#business-name').value = workspace.business; document.querySelector('#business-industry').value = workspace.industry; document.querySelector('#business-region').value = workspace.region; document.querySelector('#business-goal').value = workspace.goal; setupBackdrop.classList.add('open'); setupBackdrop.setAttribute('aria-hidden', 'false'); };
const closeSetup = () => { setupBackdrop.classList.remove('open'); setupBackdrop.setAttribute('aria-hidden', 'true'); };
document.querySelector('#new-request').addEventListener('click', openSetup);
document.querySelector('#adjust-plan').addEventListener('click', openSetup);
document.querySelector('#setup-close').addEventListener('click', closeSetup);
setupBackdrop.addEventListener('click', event => { if (event.target === setupBackdrop) closeSetup(); });
document.querySelector('#setup-form').addEventListener('submit', event => { event.preventDefault(); workspace = { business: document.querySelector('#business-name').value.trim(), industry: document.querySelector('#business-industry').value, region: document.querySelector('#business-region').value.trim(), goal: document.querySelector('#business-goal').value.trim(), initialized: true }; evidence.unshift(['Customer setup brief', `${workspace.industry} · ${workspace.region} · outcome: ${workspace.goal}`, 'Customer supplied']); persist(); refreshWorkspace(); renderEvidence(); closeSetup(); showToast('Workspace saved. The first opportunity brief is ready to be created for your approval.'); });
const usageBackdrop = document.querySelector('#usage-backdrop');
const openUsage = () => { document.querySelector('#usage-monthly-limit').value = usage.monthlyLimit; document.querySelector('#usage-task-limit').value = usage.taskLimit; document.querySelector('#usage-hard-stop').checked = usage.hardStop; usageBackdrop.classList.add('open'); usageBackdrop.setAttribute('aria-hidden', 'false'); };
const closeUsage = () => { usageBackdrop.classList.remove('open'); usageBackdrop.setAttribute('aria-hidden', 'true'); };
document.querySelector('#edit-usage').addEventListener('click', openUsage);
document.querySelector('#usage-close').addEventListener('click', closeUsage);
usageBackdrop.addEventListener('click', event => { if (event.target === usageBackdrop) closeUsage(); });
async function syncUsageControls() {
  try {
    const response = await fetch('/api/control', { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error('The shared control record is not ready.');
    const data = await response.json();
    usage = {
      ...usage,
      monthlyLimit: data.controls.monthlyLimitCents / 100,
      taskLimit: data.controls.perTaskLimitCents / 100,
      hardStop: data.controls.hardStop,
      used: data.actualCostCents / 100,
      activity: data.records.map(record => [record.taskName, `${record.functionName.replaceAll('_', ' ')} · ${record.inputTokens.toLocaleString()} input / ${record.outputTokens.toLocaleString()} output tokens`, record.costCents / 100, record.status === 'complete' ? 'Complete' : 'Running', record.billingSource])
    };
    renderUsage();
    document.querySelector('.sync-status').innerHTML = '<i></i> Shared controls active';
    document.querySelector('.usage-note').textContent = data.records.length ? 'Live runtime records' : 'Ready for the first protected runtime task';
  } catch {
    document.querySelector('.sync-status').innerHTML = '<i></i> Demo controls only';
  }
}
document.querySelector('#usage-form').addEventListener('submit', async event => { event.preventDefault(); const monthlyLimit = Number(document.querySelector('#usage-monthly-limit').value); const taskLimit = Number(document.querySelector('#usage-task-limit').value); if (!Number.isFinite(monthlyLimit) || !Number.isFinite(taskLimit) || taskLimit > monthlyLimit) return; try { const response = await fetch('/api/control', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ monthlyLimitCents: Math.round(monthlyLimit * 100), perTaskLimitCents: Math.round(taskLimit * 100), hardStop: document.querySelector('#usage-hard-stop').checked }) }); if (!response.ok) throw new Error(); usage = { ...usage, monthlyLimit, taskLimit, hardStop: document.querySelector('#usage-hard-stop').checked }; persist(); renderUsage(); closeUsage(); showToast('Shared usage controls saved.'); } catch { showToast('Shared controls are not ready. Your local setting was not changed.'); } });
document.querySelector('.mobile-menu').addEventListener('click', () => document.querySelector('.sidebar').classList.toggle('open'));
refreshWorkspace(); renderApprovals(); renderEvidence(); renderUsage();
syncUsageControls();
const initialApprovalCount = Object.keys(approvals).length;
document.querySelector('#approval-count').textContent = initialApprovalCount;
document.querySelector('.nav-badge').textContent = initialApprovalCount;
