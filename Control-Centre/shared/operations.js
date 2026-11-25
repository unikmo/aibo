/* Custom operational home. Reads only local portfolio data; no demo KPI figures. */
(()=>{
'use strict';
if(document.body.dataset.product!=='custom')return;
const nav=document.querySelector('.nav-list'),main=document.querySelector('.main-content');
const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const current=document.querySelector('[data-view="projects"]');
for(const [key,text] of [['portfolio','Dashboard'],['soni','CariFive']]){
 const a=document.createElement('a');a.className='nav-item';a.href='#'+key;a.dataset.view=key;a.textContent=text;
 nav.insertBefore(a,current);
}
const connectionsNav=document.createElement('a');connectionsNav.className='nav-item';connectionsNav.href='#connections';connectionsNav.dataset.view='connections';connectionsNav.textContent='Connections';nav.insertBefore(connectionsNav,current);
const costsNav=document.createElement('a');costsNav.className='nav-item';costsNav.href='#cost-management';costsNav.dataset.view='cost-management';costsNav.textContent='Cost Management';nav.insertBefore(costsNav,current);
const dashboard=document.createElement('section');dashboard.id='portfolio';dashboard.className='dashboard-view aibo-operational-view';
dashboard.innerHTML=`<header class="soni-home-hero"><p class="eyebrow">AIBO CONTROL CENTRE</p><h1>What would you like to <em>move forward?</em></h1><p>CariFive turns a plain request into the right plan, evidence, specialist work and a clear decision—without asking you to manage agents.</p><button class="soni-prompt-button" data-view="soni" type="button"><span>Ask CariFive anything about your work</span><kbd>Enter</kbd></button><small>Nothing is sent, spent, published or connected without your approval.</small></header>
<div class="op-metrics" id="op-metrics" aria-live="polite"></div>
<div class="soni-home-grid"><article class="panel"><div class="op-panel-title"><div><p class="eyebrow">YOUR ATTENTION</p><h2>What needs you next</h2></div><button class="text-button" data-view="soni">Ask CariFive →</button></div><div id="op-home-next"></div></article><article class="panel"><div class="op-panel-title"><div><p class="eyebrow">PROJECT STATUS</p><h2>Only what needs a look</h2></div><span>Local workspace data</span></div><div id="op-health"></div></article><article class="panel"><div class="op-panel-title"><div><p class="eyebrow">RECENT WORK</p><h2>CariFive’s clear record</h2></div></div><div id="op-jobs"></div></article></div>
<div class="panel op-kpis"><div class="op-panel-title"><h2>Project KPIs</h2><span>Manual entries are labelled. Live business data is not connected.</span></div><div id="op-kpi-list"></div>
<form id="op-kpi-form" class="op-kpi-form"><label>Project<select name="project" required></select></label><label>KPI name<input name="name" placeholder="e.g. Monthly leads" maxlength="75" required></label><label>Value<input name="value" placeholder="e.g. 12" maxlength="60" required></label><label>Unit<input name="unit" placeholder="e.g. leads" maxlength="30"></label><label>Source<input name="source" placeholder="e.g. CRM export, 12 Nov" maxlength="100" required></label><button class="secondary-button" type="submit">Add KPI</button></form><p id="op-kpi-status" role="status"></p></div>`;
main.insertBefore(dashboard,document.querySelector('#projects'));
const soni=document.createElement('section');soni.id='soni';soni.className='dashboard-view aibo-operational-view';
soni.innerHTML=`<header class="soni-chat-heading"><p class="eyebrow">YOUR BUSINESS PARTNER</p><h1>Ask CariFive.</h1><p>Use your own words. CariFive brings in the right expertise, keeps work scoped, and returns only what you need to decide.</p></header>
<div class="op-chat-shell"><div class="panel op-chat-panel"><label class="op-project-picker">Working on <select id="op-chat-project"></select></label>
<div id="op-conversation" class="op-conversation" role="log" aria-live="polite"><p>Select a project to load its history.</p></div>
<form id="op-chat-form"><label for="op-chat-task" class="aibo-visually-hidden">Your request</label><div class="aibo-chat-composer"><textarea id="op-chat-task" rows="3" minlength="5" maxlength="1500" required placeholder="Ask CariFive what you want to achieve, solve, decide or create…"></textarea><div class="aibo-chat-composer-bar"><label for="op-chat-files" class="aibo-chat-attach-button" title="Attach files" aria-label="Attach files">＋</label><input id="op-chat-files" type="file" multiple accept=".csv,.xlsx,.xls,.pdf,.json,.txt,.md" aria-label="Attach reference files"><span id="op-chat-attachment-list" aria-live="polite"></span><button class="primary-button aibo-chat-send" type="submit" title="Send" aria-label="Send message">Send <span>↑</span></button></div></div><div class="op-chat-actions"><details class="aibo-chat-options"><summary>AI connection</summary><p>By default, CariFive uses an available local Codex or Claude connection. APIs are always your choice.</p><label>Use <select id="op-chat-provider"><option value="auto" selected>Let CariFive choose a local connection</option><option value="mock">Demo only (no AI request)</option><option value="codex-local">Codex on this computer</option><option value="claude-local">Claude on this computer</option><option value="openai">OpenAI API</option><option value="anthropic">Anthropic API</option><option value="openrouter">OpenRouter API</option><option value="vercel-gateway">Vercel AI Gateway</option><option value="together">Together AI API</option><option value="groq">Groq API</option></select></label><label id="op-chat-consent-wrap" hidden><input id="op-chat-consent" type="checkbox"> I approve this API request and any provider charges</label></details></div></form><p id="op-chat-status" role="status"></p></div>
</div>`;
main.insertBefore(soni,document.querySelector('#projects'));

// Optional tools remain inside CariFive, not in the main navigation.
const relationshipTools=document.createElement('details');relationshipTools.className='aibo-relationship-tools';
relationshipTools.innerHTML=`<summary>Contacts & publishing</summary>
<div class="aibo-relationship-panel">
<div class="aibo-tool-tabs"><button type="button" data-rel-tab="contacts" aria-pressed="true">Contacts</button><button type="button" data-rel-tab="tpt" aria-pressed="false">Teaching resources</button></div>
<section data-rel-panel="contacts"><form id="aibo-contact-form" class="aibo-rel-form">
<input name="name" placeholder="Contact name" required maxlength="120" aria-label="Contact name">
<select name="channel" aria-label="Channel"><option value="internations">InterNations</option><option value="email">Email</option><option value="linkedin">LinkedIn</option><option value="other">Other</option></select>
<input name="handle" placeholder="Profile URL or email" maxlength="180" aria-label="Profile URL or email">
<input name="organization" placeholder="Organization" maxlength="150" aria-label="Organization">
<textarea name="context" placeholder="Why this person is relevant" rows="2" maxlength="2000" aria-label="Relationship context"></textarea>
<button type="submit" class="secondary-button">Save contact</button></form>
<div id="aibo-contact-list"></div>
<form id="aibo-outreach-form" class="aibo-rel-form"><label>Draft for<select name="contactId" id="aibo-outreach-contact" required></select></label>
<input name="reason" placeholder="Individual reason for reaching out" maxlength="1000" required aria-label="Individual relevance">
<textarea name="message" placeholder="Individual message for review" maxlength="4000" rows="3" required></textarea>
<button type="submit" class="secondary-button">Save personalized draft</button></form>
<p class="aibo-rel-caption">InterNations: prepare individual drafts only; send manually. No automated messaging or timing evasion.</p>
</section>
<section data-rel-panel="tpt" hidden><form id="aibo-tpt-form" class="aibo-rel-form">
<input name="title" placeholder="Resource title" maxlength="160" required>
<input name="subject" placeholder="Subject" maxlength="120" required>
<input name="grade" placeholder="Grade / learner level" maxlength="100" required>
<input name="keywords" placeholder="Search keywords" maxlength="500">
<textarea name="description" placeholder="Original resource description" maxlength="4000" rows="3" required></textarea>
<textarea name="rightsNotes" placeholder="Copyright and asset rights notes" maxlength="1200" rows="2"></textarea>
<button type="submit" class="secondary-button">Save listing draft</button></form><div id="aibo-tpt-list"></div>
<p class="aibo-rel-caption">Listing drafts stay local; no Teachers Pay Teachers account connection or automatic publishing.</p></section>
<p id="aibo-rel-status" role="status" aria-live="polite"></p>
</div>`;
soni.querySelector('.op-chat-panel').append(relationshipTools);

const costPage=document.createElement('section');costPage.id='cost-management';costPage.className='dashboard-view aibo-operational-view';
costPage.innerHTML=`<header class="op-heading"><div><h1>Cost controls</h1></div></header>
<div class="op-grid"><article class="panel"><div class="op-panel-title"><h2>Model request limits</h2><span>Enforced for requests started through CariFive</span></div>
<form id="aibo-cost-form" class="aibo-cost-form"><label>Maximum output tokens per API call<input name="maxOutputTokens" type="number" min="256" max="8192" step="1" required></label><small>Increase for longer responses. Larger responses may cost more. Local Codex/Claude CLI tokens are not controlled by this setting.</small>
<label>Maximum model calls per task<input name="maxModelCalls" type="number" min="2" max="8" step="1" required></label><small>Includes specialists, quality review, and CariFive's final synthesis. A task exceeding this cap stops before execution.</small>
<label>Monthly AI budget target (USD)<input name="monthlyBudgetUsd" type="number" min="1" max="10000" step="1" required></label>
<label>Per-task AI budget target (USD)<input name="perTaskBudgetUsd" type="number" min="1" max="5000" step="1" required></label>
<button type="submit" class="primary-button">Save limits</button><p id="aibo-cost-status" role="status"></p></form></article>
<article class="panel"><div class="op-panel-title"><h2>What is protected</h2><span>Current implementation status</span></div>
<div class="aibo-cost-explainer"><p><b>Enforced:</b> API output-token cap and model-call count on CariFive requests.</p><p><b>Not yet enforced:</b> monthly and per-task USD budgets. Accurate provider usage metering and pricing reconciliation are not connected.</p><p><b>Provider billing:</b> AI providers charge the customer's own account. Set spending caps at the provider too where supported.</p><p><b>No hidden usage data:</b> the dashboard does not invent token totals or cost balances.</p></div></article></div>`;
main.insertBefore(costPage,document.querySelector('#projects'));
const connectionsPage=document.createElement('section');connectionsPage.id='connections';connectionsPage.className='dashboard-view aibo-operational-view';
connectionsPage.innerHTML=`<header class="op-heading"><div><h1>Connections</h1></div></header>
<div class="panel aibo-connect-summary"><div><h2>Connector catalog</h2><p>Available to discover does not mean connected. Registered adapters are not necessarily ready to use.</p></div><div id="aibo-connect-stats" aria-live="polite">Loading catalog…</div></div>
<div class="panel aibo-connect-controls"><label>Find a connector<input type="search" id="aibo-connect-search" placeholder="Search social media, Resend, Firebase, browser…" autocomplete="off"></label><label>Category<select id="aibo-connect-category"><option value="">All categories</option></select></label><label>Setup status<select id="aibo-connect-filter"><option value="">All</option><option value="runtime-registered">Registry entry</option><option value="catalog-only">Catalog only</option></select></label></div>
<div id="aibo-connection-list" class="aibo-connection-list" aria-live="polite"></div>
<div class="panel aibo-connect-notice"><h3>Connection requests</h3><p>A setup request records what your project needs. It does not grant authorization or connect the service. CariFive-assisted authentication, permission verification and task resumption are not implemented yet.</p><div id="aibo-connection-requests"></div><p id="aibo-connection-status" role="status"></p></div>`;
main.insertBefore(connectionsPage,document.querySelector('#projects'));


let connectionCatalog=null;
async function loadConnections(){
 try{
  const r=await fetch('/api/connections/catalog',{cache:'no-store'});
  if(!r.ok)throw Error('Connection catalog unavailable');
  connectionCatalog=await r.json();
  const categories=[...new Set(connectionCatalog.connectors.map(x=>x.category))];
  const category=document.getElementById('aibo-connect-category'),old=category.value;
  category.innerHTML='<option value="">All categories</option>'+categories.map(x=>`<option value="${escape(x)}">${escape(x)}</option>`).join('');
  if(categories.includes(old))category.value=old;
  renderConnections();
 }catch(e){document.getElementById('aibo-connection-status').textContent=e.message;}
}
function renderConnections(){
 if(!connectionCatalog)return;
 const all=connectionCatalog.connectors;
 document.getElementById('aibo-connect-stats').textContent=`${all.length} listed · ${connectionCatalog.registered} registered adapters · ${connectionCatalog.connected} verified connections`;
 const q=document.getElementById('aibo-connect-search').value.trim().toLowerCase();
 const category=document.getElementById('aibo-connect-category').value,filter=document.getElementById('aibo-connect-filter').value;
 const items=all.filter(x=>(!q||(x.name+' '+x.category).toLowerCase().includes(q))&&(!category||x.category===category)&&(!filter||x.status===filter));
 document.getElementById('aibo-connection-list').innerHTML=items.map(x=>`<article class="panel aibo-connector"><div><small>${escape(x.category)}</small><h3>${escape(x.name)}</h3><span class="aibo-connector-state">${x.status==='runtime-registered'?'Runtime registry entry':'Catalog only'}</span></div><button class="secondary-button" type="button" data-connection-request="${escape(x.id)}">Request setup</button></article>`).join('')||'<p class="panel">No matching connectors.</p>';
 const named=new Map(all.map(x=>[x.id,x.name]));
 const projects=new Map((portfolio?.projects||[]).map(x=>[x.id,x.name]));
 document.getElementById('aibo-connection-requests').innerHTML=connectionCatalog.requests.length?connectionCatalog.requests.slice().reverse().map(x=>`<div class="op-row"><div><strong>${escape(named.get(x.connector)||x.connector)}</strong><small>${escape(projects.get(x.project)||x.project)}</small></div><span class="op-chip pending">Setup requested</span></div>`).join(''):'<p class="op-empty">No setup requests yet.</p>';
}
for(const id of ['aibo-connect-search','aibo-connect-category','aibo-connect-filter'])document.getElementById(id).addEventListener(id==='aibo-connect-search'?'input':'change',renderConnections);
document.addEventListener('click',async e=>{
 const btn=e.target.closest('[data-connection-request]');if(!btn)return;
 const selected=btn.dataset.connectionRequest;
 if(!portfolio)await refresh();
 const ps=portfolio?.projects||[];
 if(!ps.length){document.getElementById('aibo-connection-status').textContent='No projects found. Create a project first.';return;}
 const dialog=document.getElementById('aibo-connection-dialog');
 const picker=document.getElementById('aibo-connection-project');
 picker.innerHTML=ps.map(x=>`<option value="${escape(x.id)}">${escape(x.name)}</option>`).join('');
 dialog.dataset.connector=selected;
 document.getElementById('aibo-connection-choice-status').textContent='';
 dialog.showModal();
});
const connectionDialog=document.createElement('dialog');
connectionDialog.id='aibo-connection-dialog';
connectionDialog.className='aibo-connection-dialog';
connectionDialog.innerHTML=`<form method="dialog" id="aibo-connection-dialog-form"><h2>Request a connection</h2><p>Choose which project needs this service. This records a setup request only; no account is connected yet.</p><label>Project<select id="aibo-connection-project" required></select></label><p id="aibo-connection-choice-status" role="status"></p><div class="aibo-connection-dialog-actions"><button type="button" class="secondary-button" id="aibo-connection-cancel">Cancel</button><button class="primary-button" type="submit" id="aibo-connection-confirm">Save request</button></div></form>`;
document.body.append(connectionDialog);
document.getElementById('aibo-connection-cancel').addEventListener('click',()=>connectionDialog.close());
document.getElementById('aibo-connection-dialog-form').addEventListener('submit',async e=>{
 e.preventDefault();const button=document.getElementById('aibo-connection-confirm');button.disabled=true;
 try{
  const r=await fetch('/api/connections/request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({connector:connectionDialog.dataset.connector,project:document.getElementById('aibo-connection-project').value})});
  const d=await r.json();if(!r.ok)throw Error(d.error||'Request failed');
  connectionDialog.close();
  document.getElementById('aibo-connection-status').textContent=d.alreadyRequested?'Setup is already requested for that project.':'Setup request saved. No account access was granted.';
  await loadConnections();
 }catch(err){document.getElementById('aibo-connection-choice-status').textContent=err.message;}
 finally{button.disabled=false;}
});
let portfolio=null,selectedRun=null,pollTimer=null;
async function api(url,opts){const r=await fetch(url,{cache:'no-store',...opts});let d=await r.json();if(!r.ok)throw Error(d.error||`Request failed (${r.status})`);return d;}
const el=id=>document.getElementById(id);
const status=(id,message)=>{el(id).textContent=message;};
async function refresh(){
 try{portfolio=await api('/api/portfolio/custom');renderDashboard();updateProjectChoices();}
 catch(e){status('op-kpi-status','Cannot load portfolio: '+e.message);}
}
function renderDashboard(){
 const c=portfolio.counts;
 el('op-metrics').innerHTML=[['Projects',c.projects,'your workspaces'],['Active work',c.queued+c.running,'CariFive is progressing'],['Needs attention',c.failed+c.interrupted,'review or retry'],['Completed',c.completed,'recorded outcomes']].map(([name,val,detail])=>`<div class="panel op-metric"><small>${name}</small><b>${val}</b><span>${detail}</span></div>`).join('');
 const next=el('op-home-next');
 const attention=portfolio.projects.filter(p=>p.tasksFailed||p.tasksOpen||!p.setupComplete).slice(0,3);
 next.innerHTML=attention.length?attention.map(p=>`<button class="soni-next-row" type="button" data-view="soni"><span><b>${escape(p.name)}</b><small>${p.tasksFailed?'A result needs review':p.tasksOpen?'CariFive has work in progress':'Finish the short setup, then ask CariFive anything'}</small></span><i>→</i></button>`).join(''):'<p class="op-empty">Everything is quiet. Ask CariFive to start the next useful piece of work.</p>';
 el('op-health').innerHTML=portfolio.projects.map(p=>`<div class="op-row"><div><strong>${escape(p.name)}</strong><small>${p.tasksCompleted} completed · ${p.tasksOpen} active · ${p.tasksFailed} failed</small></div><span class="op-chip ${p.setupComplete?'ready':'pending'}">${escape(p.readiness)}</span></div>`).join('');
 el('op-jobs').innerHTML=portfolio.recentWork.length?portfolio.recentWork.slice(0,10).map(r=>`<div class="op-row"><div><strong>${escape(portfolio.projects.find(p=>p.id===r.project)?.name||r.project)}</strong><small>${escape((r.task||'').slice(0,88))}${(r.task||'').length>88?'…':''}${r.createdAt?' · '+escape(r.createdAt.substring(0,10)):''}${r.error?'<br><strong class="soni-job-error">'+escape(r.error)+'</strong>':''}</small></div><span class="op-chip ${r.status==='completed'?'ready':'pending'}">${escape(r.status)}</span></div>`).join(''):'<p class="op-empty">No CariFive tasks recorded yet.</p>';
 el('op-kpi-list').innerHTML=portfolio.projects.map(p=>p.kpis.length?`<div class="op-kpi-project"><h3>${escape(p.name)}</h3><div class="op-kpi-values">${p.kpis.map(k=>`<div><b>${escape(k.value)} ${escape(k.unit)}</b><span>${escape(k.name)}</span><small>Source: ${escape(k.source)} · ${escape((k.recordedAt||'').substring(0,10))}</small></div>`).join('')}</div></div>`:'').filter(Boolean).join('')||'<p class="op-empty">No KPIs recorded yet. Add sourced business metrics below.</p>';
}
function updateProjectChoices(){
 const options=portfolio.projects.map(p=>`<option value="${escape(p.id)}">${escape(p.name)}</option>`).join('');
 for(const id of ['op-chat-project']){const sel=el(id),prev=sel.value;sel.innerHTML=options;if(portfolio.projects.some(p=>p.id===prev))sel.value=prev;}
 const kpi=el('op-kpi-form').elements.project,prev=kpi.value;kpi.innerHTML=options;if(portfolio.projects.some(p=>p.id===prev))kpi.value=prev;
}
el('op-kpi-form').addEventListener('submit',async e=>{
 e.preventDefault();const f=e.currentTarget,button=f.querySelector('button');button.disabled=true;
 try{await api('/api/kpis/custom/'+encodeURIComponent(f.elements.project.value),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:f.elements.name.value,value:f.elements.value.value,unit:f.elements.unit.value,source:f.elements.source.value})});f.elements.name.value='';f.elements.value.value='';f.elements.unit.value='';f.elements.source.value='';await refresh();status('op-kpi-status','KPI saved locally with its source.');}
 catch(err){status('op-kpi-status',err.message);}finally{button.disabled=false;}
});
async function renderConversation(){
 const id=el('op-chat-project').value,box=el('op-conversation');
 if(!id){box.textContent='No projects registered.';return;}
 try{const r=await api('/api/runs/custom/'+encodeURIComponent(id));
  if(!r.runs.length){box.innerHTML='<p class="op-empty">No history for this project yet. Ask CariFive your first question.</p>';return;}
  // The ledger is authoritative; render latest requests and verified saved results.
  const runs=r.runs.slice(0,12).reverse();const nodes=[];
  for(const run of runs){nodes.push(`<div class="op-message user"><small>You · ${escape((run.createdAt||'').slice(0,16).replace('T',' '))}</small><p>${escape(run.task.length>280?run.task.slice(0,280)+'…':run.task)}</p></div>`);
    if(run.status==='completed'){let detail;try{detail=await api('/api/run/'+encodeURIComponent(run.id));}catch{}
      nodes.push(`<div class="op-message assistant"><small>CariFive · ${escape(run.provider)} · completed</small><p>${escape(detail?.result?.soni||'Completed. See original task details for the full result.')}</p></div>`);
    }else nodes.push(`<div class="op-message assistant"><small>${escape(run.status)}</small><p>${escape(run.error||'No completed response yet.')}</p></div>`);
  }
  box.innerHTML=nodes.join('');box.scrollTop=box.scrollHeight;
 }catch(err){box.textContent='Unable to load conversation: '+err.message;}
}
el('op-chat-project').addEventListener('change',renderConversation);
el('op-chat-provider').addEventListener('change',()=>{const api=['openai','anthropic','openrouter','vercel-gateway','together','groq'].includes(el('op-chat-provider').value);el('op-chat-consent-wrap').hidden=!api;el('op-chat-consent').checked=false;});
el('op-chat-form').addEventListener('submit',async e=>{
 e.preventDefault();const f=e.currentTarget,button=f.querySelector('button[type="submit"]'),project=el('op-chat-project').value;
 const p=portfolio?.projects.find(p=>p.id===project);
 if(!p?.setupComplete){status('op-chat-status','Finish guided setup for this project in Projects before using CariFive.');return;}
 button.disabled=true;status('op-chat-status','Requesting CariFive…');
 try{
  const result=await api('/api/work/custom/'+encodeURIComponent(project),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:el('op-chat-task').value,provider:el('op-chat-provider').value,consent:el('op-chat-consent').checked})});
  el('op-chat-task').value='';await renderConversation();
  if(pollTimer)clearInterval(pollTimer);
  let attempts=0;
  pollTimer=setInterval(async()=>{try{const run=await api('/api/run/'+encodeURIComponent(result.id));if(['completed','failed','interrupted'].includes(run.status)){clearInterval(pollTimer);pollTimer=null;button.disabled=false;status('op-chat-status',`Run ${run.status}.`);await refresh();await renderConversation();}else if(++attempts>150){clearInterval(pollTimer);pollTimer=null;button.disabled=false;status('op-chat-status','Still processing. Refresh to check history.');}}catch(err){clearInterval(pollTimer);pollTimer=null;button.disabled=false;status('op-chat-status',err.message);}},1200);
 }catch(err){button.disabled=false;status('op-chat-status',err.message);}
});
// The inherited app.js owns all nav clicks. Open Dashboard by default; never surface sample metrics.
const moneyForm=document.getElementById('aibo-cost-form');
async function loadCosts(){try{const c=await api('/api/cost-controls');for(const k of ['maxOutputTokens','maxModelCalls','monthlyBudgetUsd','perTaskBudgetUsd'])moneyForm.elements[k].value=c[k];}
catch(e){document.getElementById('aibo-cost-status').textContent='Could not load controls: '+e.message;}}
moneyForm.addEventListener('submit',async e=>{e.preventDefault();const button=moneyForm.querySelector('button[type=submit]');button.disabled=true;
try{const fields=['maxOutputTokens','maxModelCalls','monthlyBudgetUsd','perTaskBudgetUsd'];const data=Object.fromEntries(fields.map(k=>[k,Number(moneyForm.elements[k].value)]));await api('/api/cost-controls',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});document.getElementById('aibo-cost-status').textContent='Saved. Token and model-call caps now apply to new CariFive runs. USD targets are informational until metering is connected.';}
catch(err){document.getElementById('aibo-cost-status').textContent='Could not save: '+err.message;}finally{button.disabled=false;}});
// Connector-gated CariFive workflow. Explicit project-scoped checks; no unattended writes.
el('op-chat-files').addEventListener('change',()=>{const files=[...el('op-chat-files').files];el('op-chat-attachment-list').textContent=files.length?files.map(x=>x.name).join(' · '):'';});
const aiServicePicker=document.createElement('label');
aiServicePicker.textContent='Service needed ';
aiServicePicker.innerHTML+=' <select id="op-chat-required-service"><option value="">Auto-detect from task</option><option value="github">GitHub</option><option value="vercel">Vercel</option><option value="netlify">Netlify</option><option value="resend">Resend</option><option value="deepl-api">DeepL</option><option value="buffer">Buffer</option></select>';
const taskActions=document.querySelector('#op-chat-form .op-chat-actions');taskActions.querySelector('.aibo-chat-options').append(aiServicePicker);
const dependencyArea=document.createElement('section');dependencyArea.className='aibo-dependent-work';
dependencyArea.innerHTML='<details><summary>Connection requests</summary><div id="aibo-dependency-items"></div><p id="aibo-dependency-status" role="status"></p></details>';
const chatPanel=document.querySelector('#soni .op-chat-panel');chatPanel.append(dependencyArea);
async function loadDependencies(){
 try{
  const data=await api('/api/dependencies');
  const selected=el('op-chat-project').value;
  const rows=data.tasks.filter(t=>t.project===selected).slice(-12).reverse();
  el('aibo-dependency-items').innerHTML=rows.length?rows.map(t=>`<div class="op-row"><div><strong>${escape(t.task.slice(0,100))}</strong><small>${escape(t.connector||'No connector')} · ${escape(t.status)}</small></div><div class="aibo-connector-buttons">${t.status==='waiting-for-connection'&&t.connector==='buffer'?`<button class="secondary-button" type="button" data-aibo-buffer-auth="1">Authorize Buffer</button>`:''}${t.status==='waiting-for-connection'&&['github','vercel','netlify','resend','deepl-api'].includes(t.connector)?`<button class="secondary-button" type="button" data-aibo-verify="${escape(t.connector)}">Check access</button>`:''}${t.status!=='submitted'?`<button class="secondary-button" type="button" data-aibo-resume="${escape(t.id)}">Continue task</button>`:''}</div></div>`).join(''):'<p class="op-empty">No tasks waiting for a connection.</p>';
 }catch(err){el('aibo-dependency-status').textContent='Could not load connection-dependent tasks: '+err.message;}
}
async function queueSoniRequest(event){
 event.preventDefault();event.stopImmediatePropagation();
 const project=el('op-chat-project').value,provider=el('op-chat-provider').value;
 const p=portfolio?.projects.find(p=>p.id===project);
 if(!p?.setupComplete){status('op-chat-status','Finish project setup first.');return;}
 const submit=event.target.querySelector('button[type="submit"]');submit.disabled=true;
 try{
  const picked=[...el('op-chat-files').files];if(picked.length>5)throw Error('Maximum 5 files per request');
  const uploaded=[];for(const file of picked){
   if(file.size>12*1024*1024)throw Error(file.name+' exceeds 12 MB');
   if(!/\.(csv|xlsx|xls|pdf|json|txt|md)$/i.test(file.name))throw Error('Unsupported file: '+file.name);
   status('op-chat-status','Saving '+file.name+'…');
   const r=await fetch('/api/attachments/custom/'+encodeURIComponent(project),{method:'POST',headers:{'Content-Type':'application/octet-stream','X-AIBO-Filename':encodeURIComponent(file.name)},body:file});
   const d=await r.json();if(!r.ok)throw Error(d.error||'Upload failed');uploaded.push(d.id);
  }
  const task=await api('/api/dependencies',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project,task:el('op-chat-task').value,connector:el('op-chat-required-service').value||null,provider,consent:el('op-chat-consent').checked,attachments:uploaded})});
  el('op-chat-task').value='';el('op-chat-files').value='';el('op-chat-attachment-list').textContent='';
  if(task.status==='ready-to-run'){
   const response=await api('/api/dependencies/resume/'+encodeURIComponent(task.id),{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
   status('op-chat-status','CariFive started. Job '+response.runId.slice(0,8)+'…');
   await renderConversation();
   // Connection-queued runs previously stopped here, leaving a stale 'running'
   // bubble even after the backend had completed or failed.
   if(pollTimer)clearInterval(pollTimer);
   let polls=0;
   pollTimer=setInterval(async()=>{
     try{
       const run=await api('/api/run/'+encodeURIComponent(response.runId));
       if(['completed','failed','interrupted'].includes(run.status)){
         clearInterval(pollTimer);pollTimer=null;
         status('op-chat-status','Run '+run.status+'.');
         await renderConversation();await refresh();
       }else if(++polls>=150){
         clearInterval(pollTimer);pollTimer=null;
         status('op-chat-status','Still processing. History remains available.');
       }
     }catch(err){clearInterval(pollTimer);pollTimer=null;status('op-chat-status','Unable to refresh run: '+err.message);}
   },1200);
  }else{
   status('op-chat-status','Waiting for '+task.connector+' connection. Open Options → Connection requests.');
  }
  await loadDependencies();await refresh();
 }catch(err){status('op-chat-status',err.message);}finally{submit.disabled=false;}
}
el('op-chat-form').addEventListener('submit',queueSoniRequest,true);
// Conversation-standard keyboard interaction. Prevent double sends and IME interruption.
el('op-chat-task').addEventListener('keydown',event=>{
 if(event.key!=='Enter'||event.shiftKey||event.isComposing||event.keyCode===229||event.ctrlKey||event.altKey||event.metaKey)return;
 event.preventDefault();
 const form=el('op-chat-form'),submit=form.querySelector('button[type="submit"]');
 if(submit?.disabled||!form.reportValidity())return;
 form.requestSubmit(submit);
});
el('op-chat-project').addEventListener('change',loadDependencies);
document.addEventListener('click',async event=>{
 const bufferButton=event.target.closest('[data-aibo-buffer-auth]');
 if(bufferButton){bufferButton.disabled=true;try{const r=await api('/api/oauth/buffer/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project:el('op-chat-project').value})});window.open(r.authorizationUrl,'_blank','noopener,noreferrer');el('aibo-dependency-status').textContent='Finish Buffer consent in the opened page. Your task will resume after successful authorization.';}catch(err){el('aibo-dependency-status').textContent=err.message;}finally{bufferButton.disabled=false;}return;}
 const verifyButton=event.target.closest('[data-aibo-verify]');
 const resumeButton=event.target.closest('[data-aibo-resume]');
 if(!verifyButton&&!resumeButton)return;
 const target=verifyButton||resumeButton;target.disabled=true;
 try{
  if(verifyButton){
   const result=await api('/api/connections/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project:el('op-chat-project').value,connector:verifyButton.dataset.aiboVerify})});
   el('aibo-dependency-status').textContent=result.message;
  }else{
   const result=await api('/api/dependencies/resume/'+encodeURIComponent(resumeButton.dataset.aiboResume),{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
   el('aibo-dependency-status').textContent='CariFive resumed the analysis request. Run '+result.runId.slice(0,8)+'…';
   await renderConversation();
  }
  await loadDependencies();await refresh();
 }catch(err){el('aibo-dependency-status').textContent=err.message;}
 finally{target.disabled=false;}
});
loadDependencies();
loadCosts();
const show=id=>{document.querySelectorAll('.dashboard-view').forEach(v=>v.classList.toggle('active',v.id===id));document.querySelectorAll('.nav-item').forEach(n=>n.classList.toggle('active',n.dataset.view===id));document.querySelector('.breadcrumb b').textContent=id==='portfolio'?'Dashboard':id==='soni'?'CariFive':id==='cost-management'?'Cost Management':id==='connections'?'Connections':id==='agent-setup'?'Agent Setup':id==='ai-providers'?'AI Providers':'Projects';};
show('portfolio');
document.addEventListener('click',e=>{const a=e.target.closest('[data-view]');if(a&&['portfolio','soni','projects','cost-management','connections','agent-setup','ai-providers'].includes(a.dataset.view)){setTimeout(()=>{if(a.dataset.view==='portfolio')refresh();if(a.dataset.view==='connections')loadConnections();if(a.dataset.view==='agent-setup')loadAgentSetup();if(a.dataset.view==='soni'){refresh().then(renderConversation);}},0);}});
refresh();
loadConnections();
// Agent Setup: project-scoped operating preferences, not a credential store.
const agentSetupNav=document.createElement('a');agentSetupNav.className='nav-item';agentSetupNav.href='#agent-setup';agentSetupNav.dataset.view='agent-setup';agentSetupNav.textContent='Agent Setup';nav.insertBefore(agentSetupNav,document.querySelector('[data-view="cost-management"]'));
const agentSetupPage=document.createElement('section');agentSetupPage.id='agent-setup';agentSetupPage.className='dashboard-view aibo-operational-view';
agentSetupPage.innerHTML=`<header class="op-heading"><div><p class="eyebrow">WORKING PREFERENCES</p><h1>Agent Setup.</h1><p>Decide what CariFive may do for each project.</p></div></header>
<article class="panel aibo-agent-panel"><div class="aibo-agent-top"><label>Project<select id="aibo-agent-project"></select></label><label>Coordinator<select id="aibo-agent-coordinator"><option value="soni">CariFive + specialists</option><option value="specialists">Specialists, coordinated by CariFive</option></select></label><label>Working style<select id="aibo-agent-style"><option value="autonomous">Autonomous</option><option value="supervised">Supervised</option></select></label></div>
<h2>Work permissions</h2><p class="aibo-agent-muted">Routine research and local edits start enabled. Public and financial actions require approval.</p><div id="aibo-agent-permissions" class="aibo-agent-permissions"></div>
<h2>Mailboxes</h2><p class="aibo-agent-muted">Select addresses CariFive may use once the mail provider is connected. This does not connect an account.</p><div id="aibo-agent-mailboxes"></div><div class="aibo-agent-mailbox-add"><input id="aibo-agent-mailbox-input" type="email" placeholder="name@company.com" aria-label="Mailbox address"><button type="button" id="aibo-agent-mailbox-add" class="secondary-button">Add mailbox</button></div>
<div class="aibo-agent-footer"><button class="primary-button" type="button" id="aibo-agent-save">Save settings</button><span role="status" id="aibo-agent-status"></span></div><p class="aibo-agent-muted">Preferences govern supported prepared actions. Other external work requires an available, authenticated connector; sending, publishing and deployment retain existing approval gates.</p></article>`;
main.insertBefore(agentSetupPage,document.querySelector('#projects'));
// User-initiated translation uses their own DeepL API key; nothing is published.
const localization=document.createElement('section');localization.className='panel aibo-translation';
localization.innerHTML=`<details id="aibo-optional-translation"><summary>Translation tools (optional)</summary><div class="op-panel-title"><h2>Translate text</h2><span>DeepL · Review before use</span></div><form id="aibo-translation-form"><div class="aibo-translation-langs"><label>From<select name="source"><option value="EN">English</option><option value="DE">German</option><option value="FR">French</option><option value="ES">Spanish</option><option value="PT">Portuguese</option></select></label><label>To<select name="target"><option value="DE">German</option><option value="FR" selected>French</option><option value="ES">Spanish</option><option value="PT-BR">Brazilian Portuguese</option><option value="EN">English</option></select></label></div><label>Text<textarea name="text" maxlength="5000" rows="4" required placeholder="Paste text to localize…"></textarea></label><label class="aibo-translation-consent"><input type="checkbox" name="consent" required> I approve sending this text to DeepL using my own API credentials. Provider charges may apply.</label><button class="primary-button" type="submit">Translate</button><p id="aibo-translation-status" role="status"></p><label>Translation for review<textarea id="aibo-translation-result" rows="4" readonly placeholder="Translation appears here after successful verification."></textarea></label></form></details>`;
agentSetupPage.append(localization);
el('aibo-translation-form').addEventListener('submit',async event=>{
 event.preventDefault();const f=event.currentTarget,button=f.querySelector('button[type="submit"]');button.disabled=true;
 try{
  const result=await api('/api/localization/translate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project:el('aibo-agent-project').value,text:f.elements.text.value,source:f.elements.source.value,target:f.elements.target.value,consent:f.elements.consent.checked})});
  el('aibo-translation-result').value=result.text;
  el('aibo-translation-status').textContent='Translated using your DeepL account. Review language, cultural context, links and SEO before publishing.';
 }catch(err){el('aibo-translation-status').textContent=err.message;}
 finally{button.disabled=false;}
});

const agentLabels={research:'Research & analysis',read_browser:'Browse and read websites',write_local:'Edit local project files',write_browser:'Interact with websites',read_mail:'Read connected mail',draft_mail:'Prepare email drafts',send_mail:'Send email',publish:'Publish content',deploy:'Deploy changes',spend:'Spend money'};
const agentHint={research:'Enabled',read_browser:'Enabled',write_local:'Enabled',write_browser:'Enabled',read_mail:'Enabled',draft_mail:'Enabled',send_mail:'Approval required',publish:'Approval required',deploy:'Approval required',spend:'Approval required'};
let agentData=null;
const agentStatus=message=>document.getElementById('aibo-agent-status').textContent=message;
const agentAddMailbox=(address,enabled=true)=>{
 const parent=document.getElementById('aibo-agent-mailboxes');
 const row=document.createElement('div');row.className='aibo-agent-mailbox';
 const check=document.createElement('input');check.type='checkbox';check.className='aibo-agent-mailbox-enable';check.checked=enabled;
 const span=document.createElement('span');span.textContent=address;span.className='aibo-agent-mailbox-address';
 const del=document.createElement('button');del.type='button';del.className='secondary-button';del.textContent='Remove';del.addEventListener('click',()=>row.remove());
 row.append(check,span,del);parent.append(row);
};
async function loadAgentSetup(){
 try{
  const r=await fetch('/api/products/custom',{cache:'no-store'});if(!r.ok)throw Error('Project list unavailable');
  const data=await r.json();const select=document.getElementById('aibo-agent-project'),previous=select.value;
  select.innerHTML=data.projects.map(p=>`<option value="${escape(p.id)}">${escape(p.name)}</option>`).join('');
  if([...select.options].some(o=>o.value===previous))select.value=previous;
  if(!select.value){agentStatus('No projects available');return;}
  await loadAgentProject();
 }catch(e){agentStatus(e.message)}
}
async function loadAgentProject(){
 const id=document.getElementById('aibo-agent-project').value;if(!id)return;
 try{
  const r=await fetch('/api/agent-setup/custom/'+encodeURIComponent(id),{cache:'no-store'});const d=await r.json();if(!r.ok)throw Error(d.error||'Could not load');agentData=d;
  document.getElementById('aibo-agent-coordinator').value=d.agent;
  document.getElementById('aibo-agent-style').value=d.workingStyle;
  document.getElementById('aibo-agent-permissions').innerHTML=Object.entries(agentLabels).map(([key,name])=>`<label class="aibo-agent-choice"><span><b>${escape(name)}</b><small>${escape(agentHint[key])}</small></span><input type="checkbox" data-agent-permission="${key}" ${d.permissions[key]?'checked':''}></label>`).join('');
  document.getElementById('aibo-agent-mailboxes').replaceChildren();d.mailboxes.forEach(b=>agentAddMailbox(b.address,b.enabled));agentStatus('');
 }catch(e){agentStatus('Could not load: '+e.message)}
}
document.getElementById('aibo-agent-project').addEventListener('change',loadAgentProject);
document.getElementById('aibo-agent-mailbox-add').addEventListener('click',()=>{
 const input=document.getElementById('aibo-agent-mailbox-input');if(!input.value.trim()||!input.checkValidity()){input.reportValidity();return;}
 const address=input.value.trim().toLowerCase();
 if([...document.querySelectorAll('.aibo-agent-mailbox-address')].some(x=>x.textContent===address)){agentStatus('Mailbox already listed');return;}
 agentAddMailbox(address);input.value='';agentStatus('');
});
document.getElementById('aibo-agent-save').addEventListener('click',async()=>{
 const project=document.getElementById('aibo-agent-project').value;
 const permissions=Object.fromEntries([...document.querySelectorAll('[data-agent-permission]')].map(el=>[el.dataset.agentPermission,el.checked]));
 const mailboxes=[...document.querySelectorAll('.aibo-agent-mailbox')].map(row=>({address:row.querySelector('.aibo-agent-mailbox-address').textContent,enabled:row.querySelector('input').checked}));
 const payload={agent:document.getElementById('aibo-agent-coordinator').value,workingStyle:document.getElementById('aibo-agent-style').value,permissions,mailboxes};
 const save=document.getElementById('aibo-agent-save');save.disabled=true;agentStatus('Saving…');
 try{const r=await fetch('/api/agent-setup/custom/'+encodeURIComponent(project),{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const d=await r.json();if(!r.ok)throw Error(d.error||'Save failed');agentData=d;agentStatus('Saved for this project.');}
 catch(e){agentStatus('Could not save: '+e.message)}finally{save.disabled=false}
});


// Relationship & education preparation: project-scoped local records, no external sends.
let relationshipData=null;
async function loadRelationship(){
 const project=document.getElementById('op-chat-project')?.value;
 if(!project)return;
 try{
  relationshipData=await api('/api/relationship/custom/'+encodeURIComponent(project));
  const list=document.getElementById('aibo-contact-list');
  list.innerHTML=relationshipData.contacts.length?relationshipData.contacts.slice(-12).reverse().map(c=>`<div class="aibo-rel-item"><b>${escape(c.name)}</b><small>${escape(c.channel)} · ${escape(c.organization||c.handle)} · ${escape(c.status)}</small></div>`).join(''):'<p class="aibo-rel-caption">No contacts yet.</p>';
  document.getElementById('aibo-outreach-contact').innerHTML='<option value="">Select a contact</option>'+relationshipData.contacts.map(c=>`<option value="${escape(c.id)}">${escape(c.name)} (${escape(c.channel)})</option>`).join('');
  document.getElementById('aibo-tpt-list').innerHTML=relationshipData.listings.slice(-8).reverse().map(x=>`<div class="aibo-rel-item"><b>${escape(x.title)}</b><small>${escape(x.subject)} · Draft only</small></div>`).join('');
  document.getElementById('aibo-rel-status').textContent='';
 }catch(error){document.getElementById('aibo-rel-status').textContent=error.message;}
}
relationshipTools.addEventListener('toggle',()=>{if(relationshipTools.open)loadRelationship();});
document.getElementById('op-chat-project').addEventListener('change',()=>{if(relationshipTools.open)loadRelationship();});
relationshipTools.querySelectorAll('[data-rel-tab]').forEach(button=>button.addEventListener('click',()=>{
 for(const tab of relationshipTools.querySelectorAll('[data-rel-tab]'))tab.setAttribute('aria-pressed',String(tab===button));
 for(const panel of relationshipTools.querySelectorAll('[data-rel-panel]'))panel.hidden=panel.dataset.relPanel!==button.dataset.relTab;
}));
for(const [formId,endpoint] of [['aibo-contact-form','contact'],['aibo-outreach-form','message'],['aibo-tpt-form','tpt-listing']]){
 const form=document.getElementById(formId);
 form.addEventListener('submit',async event=>{
  event.preventDefault();
  const project=document.getElementById('op-chat-project').value;
  const button=form.querySelector('button[type="submit"]');button.disabled=true;
  try{
   const payload=Object.fromEntries(new FormData(form).entries());
   await api('/api/relationship/custom/'+encodeURIComponent(project)+'/'+endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
   form.reset();await loadRelationship();document.getElementById('aibo-rel-status').textContent='Saved locally. No external action taken.';
  }catch(error){document.getElementById('aibo-rel-status').textContent=error.message;}
  finally{button.disabled=false;}
 });
}
})();
