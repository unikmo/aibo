/* The two editions reuse the original UI. Product-specific state is loaded from localhost.
   This interface does not issue paid entitlements or perform external actions. */
(()=>{
'use strict';
const mode=document.body.dataset.product;
const standard=mode==='standard';
const nav=document.querySelector('.nav-list');
const content=document.querySelector('.main-content');
const supportLink=document.querySelector('.support-link');
const trustTitle=document.querySelector('.trust-card b');
const trustCopy=document.querySelector('.trust-card p');
if(supportLink){supportLink.innerHTML='<span>FAQ & help</span><span>→</span>';supportLink.href='../shared/guide.html';}
if(trustTitle)trustTitle.textContent='You stay in control';
if(trustCopy)trustCopy.textContent=standard?'Nothing goes live, spends money, or sends messages without your approval.':'Existing project files stay intact. New projects are added only; they never replace an existing workspace.';
// Product workspace is the landing view; the old Northline dashboard is sample-only.
document.querySelectorAll('.dashboard-view').forEach(v=>v.classList.remove('active'));
document.querySelectorAll('.nav-item').forEach(a=>a.classList.remove('active'));
document.querySelector('.workspace-switcher b').textContent=standard?'AIBO Standard':'AIBO Custom';
document.querySelector('.workspace-switcher small').textContent=standard?'5-project license':'Portfolio workspaces';
document.querySelector('.breadcrumb span').textContent=standard?'Standard':'Portfolio';
document.querySelector('.breadcrumb b').textContent='Projects';
const sync=document.querySelector('.sync-status');if(sync)sync.innerHTML='<i></i>'+(standard?'Preview mode':'Portfolio preview');
const brand=document.querySelector('.brand');if(brand)brand.href='#projects';
const topAction=document.querySelector('.topbar .help-button'); if(topAction) topAction.title='FAQ & help';
const item=document.createElement('a');item.className='nav-item';item.href='#projects';item.dataset.view='projects';item.innerHTML='<span>▤</span>Projects';nav.insertBefore(item,nav.firstChild);item.classList.add('active');
// Prevent a sample dashboard from being mistaken for real project performance.
nav.querySelectorAll('.nav-item:not([data-view=projects])').forEach(a=>a.remove());
const section=document.createElement('section');section.className='dashboard-view';section.id='projects';
section.innerHTML=`<div class="page-intro compact"><div><h1>Projects</h1></div></div><div class="product-summary panel" id="product-summary" aria-live="polite">Loading local configuration…</div><div id="project-list" class="product-list"></div><div class="panel product-footer">${standard?'Need more than five active projects or another pack? That is an upgrade, not a local setting.':'Additions are additive only. Creating or initializing a project does not replace any existing project folder or file.'}</div></section>`;
content.append(section);section.classList.add('active');
let state;
let catalog={corePacks:[],addOns:[]};
const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function setMessage(el,msg,type='note'){if(!el)return;el.textContent=msg;el.className=type==='error'?'form-status error':'form-status success';}
async function load(){
 try{
 const response=await fetch('/api/products/'+mode,{cache:'no-store'});
 if(!response.ok)throw new Error('Local backend not available');
 state=await response.json();
 if(!standard){const r=await fetch('/api/catalog/custom',{cache:'no-store'});if(r.ok)catalog=await r.json();}
 render();
 }catch(e){const x=document.querySelector('#product-summary');x.innerHTML='<strong>Backend not available</strong><p>Start <code>python runtime/control_server.py --port 8765</code> in your AIBO folder. Until then, this page is a visual preview only.</p>';}
}
function render(){
 const summary=document.querySelector('#product-summary'),list=document.querySelector('#project-list');
 if(standard){
 const license=state.license;
 summary.innerHTML=`<div class="product-summary-top"><strong>Standard license</strong><span class="summary-pill">${license.projectLimit} project slots</span></div><p>Industry: <b>${escape(license.industry||'Not activated')}</b> · Core pack: <b>${escape(license.corePack||'Not activated')}</b> · Add-on: <b>${escape((license.addOns&&license.addOns[0])||'Not activated')}</b></p><small>The license holds the knowledge. Each project only adds its own business details and connections.</small>`;
 list.innerHTML=state.slots.map(x=>`<article class="panel product-project"><div class="product-project-info"><div class="product-project-heading"><span class="project-index">0${x.slot}</span><b>${x.name||'Project slot '+x.slot}</b><span class="project-state ${x.initialized?'configured':'pending'}">${x.initialized?'Initialized':'Available'}</span></div><div class="project-facts"><span><strong>Status</strong>${x.initialized?'Setup started':'Ready to initialize'}</span><span><strong>Region</strong>${escape(x.region||'—')}</span><span><strong>Main goal</strong>${escape(x.goal||'—')}</span></div></div><button class="secondary-button" disabled title="Verified license required">Initialize</button></article>`).join('');
 }else{
 summary.innerHTML=`<div class="product-summary-top"><strong>15 existing projects${state.projects.length!==15?' + new additions':''}</strong><button class="primary-button" type="button" id="create-custom-project"><span>+</span> New project</button></div><p>Create more workspaces whenever you need them. <b>Existing projects are preserved.</b> New projects are added to the portfolio; they do not replace existing folders or files.</p><small>Choose the project, initialize it, and let CariFive use that project’s own knowledge setup.</small>`;
 list.innerHTML=state.projects.map((x,i)=>`<article class="panel product-project"><div class="product-project-info"><div class="product-project-heading"><span class="project-index">${String(i+1).padStart(2,'0')}</span><b>${escape(x.name)}</b><span class="project-state ${x.setupComplete?'configured':'pending'}">${x.setupComplete?'Ready':x.setupStep?'Setup in progress':'Needs setup'}</span></div><div class="project-facts"><span><strong>Industry</strong>${escape(x.industry||'Pending')}</span><span><strong>Core pack</strong>${escape(x.corePack||'Pending assignment')}</span><span><strong>Add-ons</strong>${x.addOns.length?escape(x.addOns.join(', ')):'Pending / none assigned'}</span></div><small>${x.setupComplete?'Ready for CariFive.':'Complete guided setup to unlock CariFive.'}${x.region?' · '+escape(x.region):''}</small></div><div class="project-actions"><button class="secondary-button" data-custom-id="${escape(x.id)}">${x.setupComplete?'Edit setup':x.setupStep?'Resume setup':'Initialize'}</button>${x.setupComplete?`<button class="primary-button" data-work-id="${escape(x.id)}">Ask CariFive</button>`:''}</div></article>`).join('');
 }
}
const backdrop=document.createElement('div');
backdrop.className='modal-backdrop';backdrop.id='product-backdrop';backdrop.setAttribute('aria-hidden','true');
backdrop.innerHTML=`<section class="setup-modal wizard-modal" role="dialog" aria-modal="true" aria-labelledby="project-setup-title">
<button class="modal-close" id="project-setup-close" type="button" aria-label="Close">×</button>
<h2 id="project-setup-title">Project setup</h2>
<div class="wizard-progress" aria-label="Setup progress"><span id="wizard-count">Step 1 of 3</span><div class="wizard-track"><div id="wizard-fill"></div></div></div>
<form id="project-setup-form" novalidate>
<div class="wizard-step" data-step="0"><p class="wizard-hint">First, tell CariFive about this project.</p>
<label>Project name<input name="name" required maxlength="80"></label>
<label>Region or location<input name="region" required maxlength="100" placeholder="e.g. Berlin, Germany"></label>
<label>Website (optional)<input name="website" type="url" maxlength="200" placeholder="https://example.com"></label></div>
<div class="wizard-step" data-step="1" hidden><p class="wizard-hint">What should CariFive focus on?</p>
<label>Main goal<textarea name="goal" required maxlength="500" placeholder="e.g. Find 15 qualified leads per month"></textarea></label>
<label>Who are you serving?<input name="audience" required maxlength="250" placeholder="e.g. Property managers in Boston"></label>
<label>How will you measure success?<input name="successMeasure" required maxlength="250" placeholder="e.g. 15 qualified inquiries monthly"></label></div>
<div class="wizard-step" data-step="2" hidden><p class="wizard-hint">Review before activating this workspace.</p>
<label>Anything CariFive should know? (optional)<textarea name="notes" maxlength="800" placeholder="Constraints, brand tone, operating preferences"></textarea></label>
<div class="wizard-review" id="wizard-review"></div>
<div class="setup-note"><p>Setup details remain local. Saving does not send messages, publish, deploy or spend money. Live AI requests are optional and require separate consent.</p></div></div>
<div class="wizard-actions"><button class="secondary-button" type="button" id="wizard-back">Back</button><button class="secondary-button" type="button" id="wizard-save">Save & exit</button><button class="primary-button" type="button" id="wizard-next">Continue</button></div>
</form><p class="form-status" id="project-save-status" role="status"></p></section>`;
document.body.append(backdrop);
let selected=null, wizardStep=0, wizardBusy=false;
const setupForm=backdrop.querySelector('#project-setup-form');
const wizardFields=['name','region','website','goal','audience','successMeasure','notes'];
function getWizardFields(){return Object.fromEntries(wizardFields.map(k=>[k,setupForm.elements[k].value]));}
function showStep(){
 backdrop.querySelectorAll('.wizard-step').forEach((node,i)=>node.hidden=i!==wizardStep);
 backdrop.querySelector('#wizard-count').textContent=`Step ${wizardStep+1} of 3`;
 backdrop.querySelector('#wizard-fill').style.width=`${(wizardStep+1)*100/3}%`;
 backdrop.querySelector('#wizard-back').disabled=wizardStep===0;
 backdrop.querySelector('#wizard-next').textContent=wizardStep===2?'Finish setup':'Continue';
 if(wizardStep===2){const f=getWizardFields();backdrop.querySelector('#wizard-review').innerHTML='<b>Your setup</b><p>'+['name','region','goal','audience','successMeasure'].map(k=>`<span><strong>${escape(k==='successMeasure'?'Success measure':k.charAt(0).toUpperCase()+k.slice(1))}:</strong> ${escape(f[k]||'Not provided')}</span>`).join('')+'</p>';}
}
function close(){backdrop.classList.remove('open');backdrop.setAttribute('aria-hidden','true');}
backdrop.querySelector('#project-setup-close').addEventListener('click',close);
backdrop.addEventListener('click',e=>{if(e.target===backdrop)close();});
async function openSetup(project){
 selected=project;setMessage(backdrop.querySelector('#project-save-status'),'');
 try{
  const response=await fetch('/api/setup/custom/'+encodeURIComponent(project.id),{cache:'no-store'});
  const data=await response.json();if(!response.ok)throw Error(data.error||'Cannot load setup');
  wizardFields.forEach(k=>setupForm.elements[k].value=data.fields[k]||'');
  wizardStep=data.complete?0:Math.min(2,data.step||0);
  backdrop.querySelector('#project-setup-title').textContent=(data.complete?'Edit':'Initialize')+' · '+project.name;
  showStep();backdrop.classList.add('open');backdrop.setAttribute('aria-hidden','false');
 }catch(err){alert('Could not open setup: '+err.message);}
}
function validateWizard(){
 const keys=wizardStep===0?['name','region']:wizardStep===1?['goal','audience','successMeasure']:[];
 for(const k of keys){const input=setupForm.elements[k];if(!input.value.trim()){input.reportValidity();input.focus();setMessage(backdrop.querySelector('#project-save-status'),'Complete the required fields to continue.','error');return false;}}
 const site=setupForm.elements.website;if(wizardStep===0&&site.value.trim()&&!site.checkValidity()){site.reportValidity();return false;}
 return true;
}
async function saveWizard(complete=false){
 if(wizardBusy)return false;
 wizardBusy=true;
 const status=backdrop.querySelector('#project-save-status');setMessage(status,'Saving…');
 try{
  const response=await fetch('/api/setup/custom/'+encodeURIComponent(selected.id),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({fields:getWizardFields(),step:wizardStep,complete})});
  const result=await response.json();if(!response.ok)throw Error(result.error||'Save failed');
  setMessage(status,complete?'Project ready. You can now ask CariFive to work.':'Progress saved. Continue any time.');
  if(complete){await load();setTimeout(close,850);}return true;
 }catch(err){setMessage(status,'Could not save: '+err.message,'error');return false;}
 finally{wizardBusy=false;}
}
backdrop.querySelector('#wizard-back').addEventListener('click',()=>{if(wizardStep>0){wizardStep--;showStep();}});
backdrop.querySelector('#wizard-save').addEventListener('click',async()=>{if(await saveWizard())close();});
backdrop.querySelector('#wizard-next').addEventListener('click',async()=>{
 if(!validateWizard())return;
 if(wizardStep===2){await saveWizard(true);return;}
 const ok=await saveWizard();if(ok){wizardStep++;showStep();setMessage(backdrop.querySelector('#project-save-status'),'');}
});
const createBackdrop=document.createElement('div');
createBackdrop.className='modal-backdrop';createBackdrop.id='new-project-backdrop';createBackdrop.setAttribute('aria-hidden','true');
createBackdrop.innerHTML=`<section class="setup-modal" role="dialog" aria-modal="true" aria-labelledby="new-project-title"><button class="modal-close" id="new-project-close" type="button" aria-label="Close">×</button><p class="eyebrow">ADD A PROJECT</p><h2 id="new-project-title">Create a new project</h2><p>Add a new independent workspace to your portfolio. <b>No existing project will be replaced.</b></p><form id="new-project-form"><label>Project name<input name="name" required maxlength="80" placeholder="e.g. Munich Hotel"></label><label>Industry<input name="industry" maxlength="100" placeholder="e.g. Hospitality & Experiences"></label><label>Core knowledge pack<select name="corePack"><option value="">Not assigned yet</option></select></label><label>Add-ons<select name="addOns" multiple size="5" aria-label="Add-ons; use Ctrl to select more than one"></select></label><small class="form-hint">Use Ctrl-click for multiple add-ons. You can leave packs unassigned and review them later.</small><label>Primary region (optional)<input name="region" maxlength="100"></label><div class="setup-note"><p>This creates a new folder and a new project entry only. It does not modify, replace, merge, or delete any existing project.</p></div><button class="primary-button setup-submit" type="submit">Create project</button></form><p id="new-project-status" class="form-status" role="status"></p></section>`;
document.body.append(createBackdrop);
const closeNew=()=>{createBackdrop.classList.remove('open');createBackdrop.setAttribute('aria-hidden','true');};
createBackdrop.querySelector('#new-project-close').addEventListener('click',closeNew);
createBackdrop.addEventListener('click',e=>{if(e.target===createBackdrop)closeNew();});
document.addEventListener('click',e=>{
 if(e.target.closest('#create-custom-project')&&!standard){
  const f=createBackdrop.querySelector('form');f.reset();
  const core=f.elements.corePack, addons=f.elements.addOns;
  core.replaceChildren(new Option('Not assigned yet',''),...catalog.corePacks.map(x=>new Option(x.path.replace('Industry-Packs/','').replace('/PACK-OVERVIEW.md',''),x.path)));
  addons.replaceChildren(...catalog.addOns.map(x=>new Option(x.path.replace('Industry-Packs/','').replace('/PACK-ADDON.md',''),x.path)));
  createBackdrop.querySelector('#new-project-status').textContent='';
  createBackdrop.classList.add('open');createBackdrop.setAttribute('aria-hidden','false');
 }
});
createBackdrop.querySelector('form').addEventListener('submit',async e=>{
 e.preventDefault();const f=e.currentTarget,status=createBackdrop.querySelector('#new-project-status');
 const payload={name:f.elements.name.value,industry:f.elements.industry.value,corePack:f.elements.corePack.value||null,
  addOns:Array.from(f.elements.addOns.selectedOptions,x=>x.value),region:f.elements.region.value};
 const submit=f.querySelector('[type=submit]');submit.disabled=true;setMessage(status,'Creating project…');
 try{
  const r=await fetch('/api/projects/custom',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const result=await r.json();if(!r.ok)throw Error(result.error||'Creation failed');
  await load();closeNew();
  const created=document.querySelector('[data-custom-id="'+CSS.escape(result.project)+'"]');
  created?.closest('.product-project')?.scrollIntoView({behavior:'smooth',block:'center'});
 }catch(err){setMessage(status,'Could not create project: '+err.message,'error');}
 finally{submit.disabled=false;}
});
// Work panel: analysis-only CariFive orchestration with explicit provider selection.
const workBackdrop=document.createElement('div');workBackdrop.className='modal-backdrop';workBackdrop.id='soni-work-backdrop';workBackdrop.setAttribute('aria-hidden','true');
workBackdrop.innerHTML=`<section class="setup-modal wizard-modal" role="dialog" aria-modal="true" aria-labelledby="soni-work-title">
<button class="modal-close" id="soni-work-close" type="button" aria-label="Close">×</button><h2 id="soni-work-title">CariFive</h2>
<form id="soni-work-form"><label>What would you like done?<textarea name="task" required minlength="5" maxlength="1500" rows="4" placeholder="e.g. Review our positioning and identify the three best improvements"></textarea></label>
<label>Reference files (CSV, XLSX, PDF, JSON; up to 5, 12 MB each)<input type="file" name="attachments" multiple accept=".csv,.xlsx,.xls,.pdf,.json,.txt,.md"></label><small>Files are saved locally to this project. Only bounded CSV/text excerpts are included for API analysis; full workbooks require file-capable local tools.</small>
<label>AI provider<select name="provider"><option value="mock">Demo (no AI request)</option><option value="codex-local">Codex CLI (read-only)</option><option value="claude-local">Claude Code (plan-only)</option><option value="openai">OpenAI API (customer key)</option><option value="anthropic">Anthropic API (customer key)</option></select></label>
<label class="provider-consent" id="provider-consent" hidden><input type="checkbox" name="consent"> I understand this sends project context and the task to my selected AI provider, using my own account and any applicable charges.</label>
<button class="primary-button setup-submit" type="submit">Start analysis</button></form>
<div id="soni-work-status" role="status" class="form-status"></div><div id="soni-work-result" class="soni-results" aria-live="polite"></div><div class="work-history" id="work-history"></div></section>`;
document.body.append(workBackdrop);
let workProject=null,runPolling=null;
function closeWork(){workBackdrop.classList.remove('open');workBackdrop.setAttribute('aria-hidden','true');if(runPolling){clearInterval(runPolling);runPolling=null;}}
workBackdrop.querySelector('#soni-work-close').addEventListener('click',closeWork);
workBackdrop.addEventListener('click',e=>{if(e.target===workBackdrop)closeWork();});
const workForm=workBackdrop.querySelector('form');
workForm.elements.provider.addEventListener('change',()=>{workBackdrop.querySelector('#provider-consent').hidden=workForm.elements.provider.value==='mock';workForm.elements.consent.checked=false;});
function renderSoniResult(job){
 const target=workBackdrop.querySelector('#soni-work-result');
 if(job.status==='failed'||job.status==='interrupted'){target.innerHTML='<div class="soni-run-error"><strong>Task did not finish</strong><p>'+escape(job.error||'No error details were recorded.')+'</p><small>Your task and reference files remain saved. Check provider access, then retry.</small></div>';return;}
 if(job.status!=='completed'){target.innerHTML='<p>Running specialists and QA. No business actions are being executed.</p>';return;}
 const result=job.result||{};
 const specialists=result.specialistResults||{};
 target.innerHTML=`<div class="soni-result-card"><h3>CariFive’s response</h3><pre>${escape(result.soni||'No response')}</pre></div><details><summary>Specialist review (${Object.keys(specialists).length})</summary>${Object.entries(specialists).map(([name,output])=>`<h4>${escape(name)}</h4><pre>${escape(output)}</pre>`).join('')}</details>${result.decisionPackage?'<p class="result-warning">Approval required before the requested external action. No external action was executed.</p>':'<p class="result-ok">Analysis only. No external business action executed.</p>'}`;
}
async function pollRun(id){
 try{const r=await fetch('/api/run/'+encodeURIComponent(id),{cache:'no-store'});const d=await r.json();if(!r.ok)throw Error(d.error||'Status unavailable');
 setMessage(workBackdrop.querySelector('#soni-work-status'),d.status==='failed'||d.status==='interrupted'?'Task '+d.status+': '+(d.error||'Open the result below for details'):`Task ${d.status} · ${d.provider}`,d.status==='failed'||d.status==='interrupted'?'error':'note');
 renderSoniResult(d);
 if(d.status==='completed'||d.status==='failed'||d.status==='interrupted'){if(runPolling){clearInterval(runPolling);runPolling=null;}workForm.querySelector('[type=submit]').disabled=false;await loadHistory();}
 }catch(err){setMessage(workBackdrop.querySelector('#soni-work-status'),'Could not check run: '+err.message,'error');if(runPolling){clearInterval(runPolling);runPolling=null;}workForm.querySelector('[type=submit]').disabled=false;}
}
async function loadHistory(){
 if(!workProject)return;
 const history=workBackdrop.querySelector('#work-history');
 try{
  const r=await fetch('/api/runs/custom/'+encodeURIComponent(workProject.id),{cache:'no-store'});
  const d=await r.json();if(!r.ok)throw Error(d.error||'History unavailable');
  history.innerHTML='<h3>Recent work</h3>'+(d.runs.length?d.runs.map(run=>`<button type="button" class="work-history-entry" data-run-id="${escape(run.id)}"><span>${escape(run.task.length>90?run.task.slice(0,90)+'…':run.task)}</span><small>${escape(run.status)} · ${escape(run.provider)}</small>${run.error?'<em class="soni-history-error">'+escape(run.error)+'</em>':''}</button>`).join(''):'<p>No work runs yet.</p>');
 }catch(err){history.textContent='History not available: '+err.message;}
}
workBackdrop.querySelector('#work-history').addEventListener('click',e=>{
 const button=e.target.closest('[data-run-id]');if(button)pollRun(button.dataset.runId);
});
async function openWork(project){
 workProject=project;workBackdrop.querySelector('#soni-work-title').textContent='Ask CariFive · '+project.name;
 workBackdrop.querySelector('#soni-work-status').textContent='';workBackdrop.querySelector('#soni-work-result').textContent='';
 workForm.reset();workBackdrop.querySelector('#provider-consent').hidden=true;
 workForm.querySelector('[type=submit]').disabled=false;
 workBackdrop.classList.add('open');workBackdrop.setAttribute('aria-hidden','false');
 await loadHistory();
 try{const r=await fetch('/api/runs/custom/'+encodeURIComponent(project.id),{cache:'no-store'});const d=await r.json();if(r.ok&&d.runs&&d.runs.length){const last=d.runs[0];if(last.status==='failed'||last.status==='interrupted'){renderSoniResult(last);setMessage(workBackdrop.querySelector('#soni-work-status'),'Last task '+last.status+': '+(last.error||'Error not recorded'),'error');}}}catch(e){}
}
// Enter sends; Shift+Enter starts a new line. Keep native IME composition intact.
workForm.elements.task.addEventListener('keydown',event=>{
 if(event.key!=='Enter'||event.shiftKey||event.isComposing||event.keyCode===229||event.ctrlKey||event.altKey||event.metaKey)return;
 event.preventDefault();
 const submit=workForm.querySelector('button[type="submit"]');
 if(submit?.disabled||!workForm.reportValidity())return;
 workForm.requestSubmit(submit);
});
workForm.addEventListener('submit',async e=>{
 e.preventDefault();if(!workProject)return;
 const btn=workForm.querySelector('[type=submit]');btn.disabled=true;
 setMessage(workBackdrop.querySelector('#soni-work-status'),'Starting CariFive…');
 try{
 const selected=[...workForm.elements.attachments.files];
 if(selected.length>5)throw Error('Select no more than five attachments');
 const uploaded=[];
 for(const file of selected){
  if(file.size>12*1024*1024)throw Error(file.name+' exceeds 12 MB');
  setMessage(workBackdrop.querySelector('#soni-work-status'),'Saving reference: '+file.name);
  const res=await fetch('/api/attachments/custom/'+encodeURIComponent(workProject.id),{method:'POST',headers:{'Content-Type':'application/octet-stream','X-AIBO-Filename':encodeURIComponent(file.name)},body:file});
  const saved=await res.json();if(!res.ok)throw Error(saved.error||'Upload failed');uploaded.push(saved.id);
 }
 const r=await fetch('/api/work/custom/'+encodeURIComponent(workProject.id),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:workForm.elements.task.value,provider:workForm.elements.provider.value,consent:workForm.elements.consent.checked,attachments:uploaded})});
 const d=await r.json();if(!r.ok)throw Error(d.error||'Could not start');
 await pollRun(d.id);
 if(runPolling)clearInterval(runPolling);runPolling=setInterval(()=>pollRun(d.id),2000);
 }catch(err){setMessage(workBackdrop.querySelector('#soni-work-status'),'Could not start: '+err.message,'error');btn.disabled=false;}
});
document.addEventListener('click',e=>{
 const setupButton=e.target.closest('[data-custom-id]');
 const workButton=e.target.closest('[data-work-id]');
 if(setupButton&&state){const project=state.projects.find(p=>p.id===setupButton.dataset.customId);if(project)openSetup(project);}
 if(workButton&&state){const project=state.projects.find(p=>p.id===workButton.dataset.workId);if(project)openWork(project);}
});

load();
})();
