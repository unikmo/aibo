(()=>{
"use strict";
const $=id=>document.getElementById(id), E=(tag,cls,content)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(content!==undefined)e.textContent=String(content??"");return e;};
const S={projects:[],activity:[],actions:[],connections:null,providers:null,selected:"",filter:"all",edition:new URLSearchParams(location.search).get("edition")==="standard"?"standard":"custom",busy:false,providerChoice:null};
const safe=(x)=>String(x??"");
function notice(title,msg){$("modalTitle").textContent=title;$("modalBody").textContent=msg;$("modalBody").replaceChildren(document.createTextNode(msg));$("overlay").classList.add("open");$("closeModal").focus()}
function formModal(title,fields,submit){$("modalTitle").textContent=title;const root=$("modalBody");root.replaceChildren();const form=E("form","modal-form");for(const f of fields){const label=E("label","",f.label),control=E(f.multiline?"textarea":f.options?"select":"input","field");control.name=f.name;if(f.multiline){control.rows=3;}else if(f.options){for(const [val,txt] of f.options){const option=E("option","",txt);option.value=val;control.append(option);}}else{control.type=f.type||"text";}control.value=f.value??"";if(f.required)control.required=true;if(f.max)control.maxLength=f.max;if(f.disabled)control.disabled=true;label.append(control);form.append(label);}
const msg=E("div","notice");msg.setAttribute("role","status");form.append(msg);const actions=E("div","modal-controls"),go=E("button","cta","Save"),cancel=E("button","secondary","Cancel");go.type="submit";cancel.type="button";cancel.onclick=closeModal;actions.append(go,cancel);form.append(actions);form.onsubmit=async e=>{e.preventDefault();go.disabled=true;msg.textContent="Saving…";try{await submit(Object.fromEntries(new FormData(form).entries()));closeModal();await refresh();}catch(err){msg.className="notice error";msg.textContent=err.message;go.disabled=false;}};root.append(form);$("overlay").classList.add("open");form.querySelector("input,select,textarea")?.focus();}
function closeModal(){$("overlay").classList.remove("open");$("modalBody").replaceChildren();}
$("closeModal").onclick=closeModal;$("overlay").onclick=e=>{if(e.target===$("overlay"))closeModal()};document.addEventListener("keydown",e=>{if(e.key==="Escape")closeModal()});
async function api(url,options={}){const r=await fetch(url,{cache:"no-store",...options});let body;try{body=await r.json()}catch{body={error:"Server returned an invalid response"}}if(!r.ok)throw Error(body.error||"Request failed ("+r.status+")");return body}
const json=(method,body)=>({method,headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
function projectName(id){return S.projects.find(p=>p.id===id)?.name||id||"Project"}
function filteredProjects(){return S.selected?S.projects.filter(p=>p.id===S.selected):S.projects}
function show(name){if(!["home","soni","projects","activity","connections"].includes(name))return;document.querySelectorAll(".screen").forEach(x=>x.classList.toggle("active",x.id==="screen-"+name));document.querySelectorAll(".nav").forEach(x=>{const yes=x.dataset.screen===name;x.classList.toggle("active",yes);if(yes)x.setAttribute("aria-current","page");else x.removeAttribute("aria-current")});if(location.hash.slice(1)!==name)location.hash=name;document.title="AIBO — "+name[0].toUpperCase()+name.slice(1);if(name==="soni")renderConversation();if(name==="activity")refresh().catch(e=>console.warn('Activity refresh:',e.message));window.scrollTo(0,0)}
document.addEventListener("click",e=>{const r=e.target.closest("[data-go],[data-screen]");if(r){e.preventDefault();show(r.dataset.go||r.dataset.screen)}});
function renderRows(id,items,empty){const node=$(id);node.replaceChildren();if(!items.length){node.className="empty";node.textContent=empty;return;}node.className="";for(const item of items){const row=E("div","rowitem"),left=E("div");left.append(E("strong","",item.name),E("small","",item.info));row.append(left,E("span","pill"+(["failed","interrupted","Attention"].includes(item.status)?" gold":""),item.status||"Recorded"));if(item.click){row.style.cursor="pointer";row.tabIndex=0;row.setAttribute("role","button");row.onclick=item.click;row.onkeydown=e=>{if(e.key==="Enter")item.click()}}node.append(row)}}
function renderHome(){const p=filteredProjects(),num=k=>p.reduce((n,x)=>n+Number(x[k]||0),0),activity=S.activity.filter(x=>!S.selected||x.project===S.selected);$("countProjects").textContent=p.length;$("countActive").textContent=num("tasksOpen");$("countNeeds").textContent=num("tasksFailed");$("countDone").textContent=num("tasksCompleted");renderRows("homeNeeds",p.filter(x=>x.tasksFailed||x.tasksOpen||!x.setupComplete).slice(0,5).map(x=>({name:x.name,info:x.tasksFailed?"Latest work needs review":x.tasksOpen?"Work running":"Complete project setup",status:x.tasksFailed?"Attention":"Review",click:()=>openProject(x)})),"No open project attention items recorded.");renderRows("homeRecent",activity.slice(0,5).map(x=>({name:projectName(x.project),info:(x.task||"Task").slice(0,130),status:x.status,click:()=>runDetail(x.id)})),"No work recorded.");renderRows("homeHealth",p.slice(0,6).map(x=>({name:x.name,info:x.readiness||"No readiness assessment",status:x.tasksFailed?"Attention":"Recorded"})),"No portfolio records available.")}
function renderProjects(){const node=$("projectCards");node.replaceChildren();const q=$("projectSearch").value.toLowerCase().trim();const projects=filteredProjects().filter(p=>p.name.toLowerCase().includes(q));if(!projects.length){node.append(E("div","empty","No matching project."));return}for(const p of projects){const button=E("button","project-card");button.type="button";const top=E("div"),bottom=E("div","footer");top.append(E("p","eyebrow",p.industry||"Independent workspace"),E("h3","",p.name));bottom.append(E("span","category",p.readiness||"Setup required"),E("span","arrow","↗"));button.append(top,bottom);button.onclick=()=>openProject(p);node.append(button)}}
function renderActivity(){const list=S.activity.filter(x=>(!S.selected||x.project===S.selected)&&(S.filter==="all"||S.filter==="completed"&&x.status==="completed"||S.filter==="running"&&["queued","running"].includes(x.status)||S.filter==="failed"&&["failed","interrupted"].includes(x.status)));$("activityCount").textContent=list.length+" records";renderRows("activityRows",list.map(x=>({name:projectName(x.project),info:safe(x.task).slice(0,150)+" · "+safe(x.createdAt||""),status:x.status,click:()=>runDetail(x.id)})),"No matching execution records.");renderRows("approvalRows",S.actions.filter(x=>!S.selected||x.project===S.selected).slice(0,15).map(x=>({name:x.kind||"Action",info:projectName(x.project)+" · "+safe(x.createdAt||""),status:x.status||"Unknown",click:()=>actionDetail(x)})),"No approval actions recorded. This is not proof of authorization.")}
function renderConnections(){const node=$("connectionsGrid");node.replaceChildren();const data=S.connections;if(!data){node.append(E("div","empty","Connector catalog is unavailable."));return}$("connectionStatus").textContent=Number(data.connected||0)+" verified · "+Number(data.registered||0)+" registered adapters · "+Number(data.total||0)+" catalog entries. Registration alone does not grant access.";const entries=data.connectors||[];for(const c of entries){const card=E("div","conn"),left=E("div"),right=E("div");left.append(E("h3","",c.name),E("p","",c.category||"Integration"));right.append(E("span","pill",c.connected?"Verified":c.status==="runtime-registered"?"Registered":"Catalog"));const button=E("button","secondary","Request");button.type="button";button.style.marginTop="12px";button.onclick=()=>requestConnection(c);right.append(button);card.append(left,right);node.append(card)}}
async function runDetail(id){if(!id)return;try{const r=await api("/api/run/"+encodeURIComponent(id));const result=r.result||{},parts=[r.task||"Task", "Status: "+r.status,"Provider: "+(r.provider||"Unknown"),"External actions executed: "+(r.externalActionsExecuted===true?"Yes":"No")];if(r.effectiveProvider)parts.push("Executed with: "+r.effectiveProvider);if(Array.isArray(r.providerAttempts))parts.push("Routing: "+r.providerAttempts.map(a=>a.provider+" ("+a.status+")").join(" → "));if(r.error)parts.push("Error: "+r.error);if(result.soni)parts.push("\nSoni:\n"+result.soni);if(result.specialistResults)parts.push("\nSpecialist review:\n"+Object.entries(result.specialistResults).map(([n,t])=>n+": "+safe(t)).join("\n\n"));notice("Execution record",parts.join("\n\n"))}catch(e){notice("Record unavailable",e.message)}}
function actionDetail(a){
const title="Action · "+(a.kind||"record"),description="Project: "+projectName(a.project)+"\nStatus: "+(a.status||"Unknown")+"\nDetails: "+JSON.stringify(a.details||{},null,2)+"\n\nExternal action requires exact approval and a separate execution confirmation.";
notice(title,description);
if(a.status!=="waiting-for-approval")return;
const controls=E("div","modal-controls"),approve=E("button","secondary","Review and approve"),execute=E("button","cta","Execute approved action");
approve.type=execute.type="button";
approve.onclick=()=>formModal("Approve exact action · "+(a.kind||""),[{name:"phrase",label:"Type I APPROVE THIS SPECIFIC ACTION",required:true}],async d=>{if(d.phrase!=="I APPROVE THIS SPECIFIC ACTION")throw Error("Exact approval phrase required");await api("/api/actions/approve/"+encodeURIComponent(a.id),json("POST",{phrase:d.phrase}))});
execute.onclick=()=>formModal("Execute approved action · "+(a.kind||""),[{name:"confirmation",label:"Type EXECUTE to confirm this external action",required:true}],async d=>{if(d.confirmation!=="EXECUTE")throw Error("Execution confirmation required");const result=await api("/api/actions/execute/"+encodeURIComponent(a.id),json("POST",{confirm:true}));if(result.status==="failed")throw Error(result.result?.error||"Provider action failed")});
controls.append(approve,execute);$("modalBody").append(controls);
}
async function openProject(p){if(S.edition==="standard"){notice("Standard edition","Standard activation requires a verified license issuer. The five licensed project slots cannot be activated by local UI settings.");return}try{const data=await api("/api/setup/custom/"+encodeURIComponent(p.id));const f=data.fields||{};formModal("Project setup · "+p.name,[{name:"name",label:"Name",value:f.name||p.name,required:true,max:80},{name:"region",label:"Country / region",value:f.region,required:true,max:100},{name:"goal",label:"Business goal",value:f.goal,multiline:true,required:true,max:500},{name:"audience",label:"Target audience",value:f.audience,required:true,max:250},{name:"website",label:"Website (optional)",value:f.website,max:200},{name:"successMeasure",label:"Measure of success",value:f.successMeasure,required:true,max:250},{name:"notes",label:"Project constraints (optional)",value:f.notes,multiline:true,max:800}],async fields=>{await api("/api/setup/custom/"+encodeURIComponent(p.id),json("POST",{fields,step:2,complete:true}));S.selected=p.id;$("projectSelect").value=p.id;});}catch(e){notice("Project unavailable",e.message)}}
async function requestConnection(c){if(!S.selected){notice("Choose a project first","Select a project from the top bar before requesting "+c.name+".");return}try{const result=await api("/api/connections/request",json("POST",{connector:c.id,project:S.selected}));notice("Request recorded",result.alreadyRequested?"A setup request already exists for this project.":"A project-scoped setup request was recorded. Authentication and connection verification remain separate.");S.connections=await api("/api/connections/catalog");renderConnections()}catch(e){notice("Connection request failed",e.message)}}
function cleanCopy(value){
  return safe(value).replace(/^\s{0,3}#{1,6}\s+/gm,"").replace(/\*\*([^*]+)\*\*/g,"$1")
    .replace(/__([^_]+)__/g,"$1").replace(/(?<!\w)\*([^*\n]+)\*(?!\w)/g,"$1")
    .replace(/^\s*[-*]\s+/gm,"• ").replace(/\n{3,}/g,"\n\n").trim();
}
function shortAnswer(text){
  const clean=cleanCopy(text);
  if(!clean)return "No verified response was recorded.";
  const first=clean.split(/\n\s*\n/)[0].trim();
  if(first.length<=320)return first;
  const slice=first.slice(0,320),boundary=Math.max(slice.lastIndexOf(". "),slice.lastIndexOf("! "),slice.lastIndexOf("? "));
  return boundary>110?slice.slice(0,boundary+1):slice.slice(0,288).trimEnd()+"…";
}
function logMessage(type,title,body,detail){
  const root=$("conversation"),item=E("div","log-item "+(type==="agent"?"agent":"user"));
  item.append(E("small","",title),E("div","message-body",cleanCopy(body)));
  if(type==="agent"&&detail&&cleanCopy(detail)!==cleanCopy(body)){
    const toggle=E("button","detail-toggle","Details");toggle.type="button";
    toggle.setAttribute("aria-expanded","false");
    const more=E("div","detail-body",cleanCopy(detail));more.hidden=true;
    toggle.onclick=()=>{more.hidden=!more.hidden;toggle.textContent=more.hidden?"Details":"Hide details";toggle.setAttribute("aria-expanded",String(!more.hidden));};
    item.append(toggle,more);
  }
  root.append(item);
}
async function renderConversation(){
  const root=$("conversation");root.replaceChildren();root.classList.add("chat-log");
  if(!S.selected)return;
  try{
    const data=await api("/api/runs/custom/"+encodeURIComponent(S.selected));
    const runs=(data.runs||[]).slice().reverse().slice(-12);
    for(const r of runs){
      logMessage("user","You",r.task||"Task");
      let detail=r;
      if(r.status==="completed"){try{detail=await api("/api/run/"+encodeURIComponent(r.id))}catch{}}
      const result=detail.result||{},answer=result.soni||detail.error||"Run "+r.status;
      const extended=[answer,...Object.entries(result.specialistResults||{}).map(([name,body])=>name.toUpperCase()+":\n"+safe(body))].join("\n\n");
      logMessage("agent","Soni · "+r.status,shortAnswer(answer),extended);
    }
  }catch(e){root.append(E("div","empty","Conversation unavailable: "+e.message))}
  root.scrollTop=root.scrollHeight;
}
const soniComposer=$("soniPrompt");
function sizeComposer(){soniComposer.style.height="34px";soniComposer.style.height=Math.min(175,Math.max(34,soniComposer.scrollHeight))+"px";}
soniComposer.addEventListener("input",sizeComposer);
soniComposer.addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey&&!e.isComposing){e.preventDefault();$("reviewPrompt").click()}});
$("soniProjectSelect").onchange=e=>{$("projectSelect").value=e.target.value;$("projectSelect").dispatchEvent(new Event("change"))};
function providerOptions(){const select=$("soniProvider");select.replaceChildren();for(const [val,label] of [["mock","Demo (no paid AI)"],["auto","Automatic · Codex → Claude · no paid API"],["codex-local","Codex · local CLI"],["claude-local","Claude · local CLI"],["openai","OpenAI API"],["anthropic","Anthropic API"],["openrouter","OpenRouter API"],["vercel-gateway","Vercel AI Gateway"],["together","Together API"],["groq","Groq API"]]){const opt=E("option","",label+(S.providers?.ready?.[val]?" · available":""));opt.value=val;select.append(opt)}select.value=S.providerChoice||"auto";providerConsent()}
function providerConsent(){const paid=["openai","anthropic","openrouter","vercel-gateway","together","groq"].includes($("soniProvider").value);document.querySelector(".consent").classList.toggle("visible",paid);$("soniConsent").checked=false;}
$("soniProvider").onchange=()=>{S.providerChoice=$("soniProvider").value;providerConsent()};
$("reviewPrompt").onclick=async()=>{const task=$("soniPrompt").value.trim(),project=S.selected,provider=$("soniProvider").value;const button=$("reviewPrompt");if(S.edition==="standard"){notice("License not activated","Standard edition requires trusted license activation before Soni execution.");return}if(!project){notice("Select a project","Choose an existing project before starting a task.");return}if(task.length<5){notice("Describe the task","Enter at least five characters.");return}if(S.busy)return;S.busy=true;button.disabled=true;$("promptHint").textContent="Submitting task…";try{const r=await api("/api/work/custom/"+encodeURIComponent(project),json("POST",{task,provider,consent:$("soniConsent").checked}));$("soniPrompt").value="";sizeComposer();$("promptHint").textContent="Run started · "+r.id;await renderConversation();for(let i=0;i<100;i++){await new Promise(ok=>setTimeout(ok,1200));const status=await api("/api/run/"+encodeURIComponent(r.id));if(["completed","failed","interrupted"].includes(status.status)){$("promptHint").textContent="Run "+status.status;await refresh();await renderConversation();if(status.status!=="completed")notice("Task "+status.status,status.error||"Review its activity record");break}if(i===99)$("promptHint").textContent="Still processing; check Activity for the latest status."}}catch(e){$("promptHint").textContent="Task not started";notice("Soni could not start",e.message)}finally{button.disabled=false;S.busy=false;}};
$("projectSelect").onchange=e=>{S.selected=e.target.value;render();renderConversation()};$("projectSearch").oninput=renderProjects;
if(S.edition==="custom"){
const addProject=E("button","secondary","New project");addProject.type="button";addProject.style.margin="0 0 20px 12px";
addProject.onclick=()=>formModal("New independent project",[{name:"name",label:"Project name",required:true,max:80},{name:"industry",label:"Industry (optional)",max:100},{name:"region",label:"Country / region",max:100}],async d=>{const result=await api("/api/projects/custom",json("POST",{name:d.name,industry:d.industry,region:d.region,corePack:null,addOns:[]}));S.selected=result.project;});
$("projectSearch").after(addProject);
}
document.querySelectorAll("[data-filter]").forEach(b=>b.onclick=()=>{S.filter=b.dataset.filter;document.querySelectorAll("[data-filter]").forEach(x=>x.classList.toggle("active",x===b));renderActivity()});
async function costSettings(){try{const c=await api("/api/cost-controls");formModal("AI use and cost controls",[{name:"maxOutputTokens",label:"Maximum output tokens per call",type:"number",value:c.maxOutputTokens,required:true},{name:"maxModelCalls",label:"Maximum model calls per task",type:"number",value:c.maxModelCalls,required:true},{name:"monthlyBudgetUsd",label:"Advisory monthly budget (USD — not enforced)",type:"number",value:c.monthlyBudgetUsd,required:true},{name:"perTaskBudgetUsd",label:"Advisory per-task budget (USD — not enforced)",type:"number",value:c.perTaskBudgetUsd,required:true}],async d=>{await api("/api/cost-controls",json("PATCH",Object.fromEntries(Object.entries(d).map(([k,v])=>[k,Number(v)]))));});}catch(e){notice("Settings unavailable",e.message)}}
async function providerSettings(){try{const p=await api("/api/ai-providers");formModal("AI provider routing",[{name:"switchMode",label:"Switching policy",value:p.switchMode,options:[["ask","Automatic CLI failover · no specialist overrides"],["soni","Automatic CLI failover · local specialist preferences"]]}],async d=>{await api("/api/ai-providers",json("PUT",{switchMode:d.switchMode}))});}catch(e){notice("Provider settings unavailable",e.message)}}
async function providerCredentials(){
  formModal("Secure local API key",[
    {name:"provider",label:"AI provider",options:[["openai","OpenAI"],["anthropic","Anthropic"],["openrouter","OpenRouter"],["vercel-gateway","Vercel AI Gateway"],["together","Together"],["groq","Groq"]]},
    {name:"key",label:"Provider API key (stored with Windows user encryption)",type:"password",required:true}
  ],async d=>{await api("/api/ai-providers/key",json("POST",{provider:d.provider,key:d.key}));});
}
async function providerModel(){
  try{
    const config=await api("/api/ai-providers");
    const providers=[["openai","OpenAI API"],["anthropic","Anthropic API"],["openrouter","OpenRouter API"],["vercel-gateway","Vercel AI Gateway"],["together","Together API"],["groq","Groq API"]];
    formModal("Model selection",[
      {name:"provider",label:"API provider",options:providers},
      {name:"model",label:"Available model",options:[] ,required:true}
    ],async d=>{if(!d.model)throw Error("Choose a model");await api("/api/ai-providers",json("PUT",{models:{[d.provider]:d.model}}));});
    const form=$("modalBody").querySelector("form"),provider=form.querySelector('[name="provider"]'),model=form.querySelector('[name="model"]'),message=form.querySelector(".notice"),save=form.querySelector('[type="submit"]');
    async function loadModels(){
      const requested=provider.value;
      model.replaceChildren();model.disabled=true;save.disabled=true;message.textContent="Checking available models…";
      try{
        const result=await api("/api/ai-providers/models?provider="+encodeURIComponent(requested));
        if(provider.value!==requested)return;
        for(const id of result.models||[]){const option=E("option","",id);option.value=id;model.append(option)}
        const selected=config.models?.[requested];
        if(selected&&Array.from(model.options).some(o=>o.value===selected))model.value=selected;
        model.disabled=!model.options.length;save.disabled=!model.options.length;
        message.textContent=model.options.length?(result.verified?"Models retrieved from provider.":"Saved/default models only; live list unavailable."):"Connect this provider to load its models.";
      }catch(e){message.textContent="Model catalog unavailable: "+e.message}
    }
    provider.onchange=loadModels;
    await loadModels();
  }catch(e){notice("Models unavailable",e.message)}
}
async function agentSettings(){if(!S.selected||S.edition!=="custom"){notice("Choose a project","Select a Custom project to edit Soni's project-scoped settings.");return}try{const a=await api("/api/agent-setup/custom/"+encodeURIComponent(S.selected));formModal("Agent setup · "+projectName(S.selected),[{name:"workingStyle",label:"Working style",value:a.workingStyle,options:[["autonomous","Autonomous within permissions"],["supervised","Supervised"]]}],async d=>{await api("/api/agent-setup/custom/"+encodeURIComponent(S.selected),json("PUT",{workingStyle:d.workingStyle}))});}catch(e){notice("Agent settings unavailable",e.message)}}
$("settingsBtn").onclick=()=>{notice("Settings","Choose the control area. Permissions, AI provider routing and usage limits remain locally managed.");const controls=E("div","modal-controls");for(const [label,fn] of [["Cost controls",costSettings],["AI providers",providerSettings],["API credentials",providerCredentials],["Select model",providerModel],["Project agents",agentSettings]]){const button=E("button","secondary",label);button.type="button";button.onclick=fn;controls.append(button)}$("modalBody").append(controls)};

$("accountBtn").onclick=()=>notice("Account and edition","AIBO is running as a local-first workspace. Cross-device identity and signed commercial licensing are not yet verified. Current edition: "+S.edition+".");
async function refresh(){let projectState;const opts=[api("/api/portfolio/custom"),api("/api/products/"+S.edition),api("/api/actions"),api("/api/connections/catalog"),api("/api/ai-providers")];const all=await Promise.allSettled(opts);const get=i=>all[i].status==="fulfilled"?all[i].value:null;const portfolio=get(0)||{projects:[],recentWork:[]};projectState=get(1);S.projects=S.edition==="custom"?portfolio.projects||[]:(projectState?.slots||[]).map(x=>({id:"slot-"+x.slot,name:x.name||"Project slot "+x.slot,industry:"Licensed slot",readiness:"License not activated",setupComplete:false,tasksOpen:0,tasksCompleted:0,tasksFailed:0}));S.activity=S.edition==="custom"?portfolio.recentWork||[]:[];S.actions=S.edition==="custom"?get(2)?.actions||[]:[];S.connections=get(3);S.providers=get(4);const sel=$("projectSelect"),prior=S.selected;sel.replaceChildren();const allOpt=E("option","","All projects");allOpt.value="";sel.append(allOpt);for(const p of S.projects){const o=E("option","",p.name);o.value=p.id;sel.append(o)}S.selected=S.projects.some(p=>p.id===prior)?prior:"";sel.value=S.selected;$("editionLabel").textContent=(S.edition==="custom"?"Portfolio edition":"Standard edition")+" · "+S.projects.length+" projects";render();renderConnections();providerOptions();if(all[0].status==="rejected")$("homeNeeds").textContent="Local backend unavailable — "+all[0].reason.message;}
function render(){
  renderHome();renderProjects();renderActivity();
  const sel=$("soniProjectSelect"),prior=S.selected;
  sel.replaceChildren();const placeholder=E("option","","Select project");placeholder.value="";sel.append(placeholder);
  for(const p of S.projects){const opt=E("option","",p.name);opt.value=p.id;sel.append(opt)}
  sel.value=prior;$("soniProject").textContent=projectName(S.selected)||"All projects";
}

(async()=>{await refresh();show(location.hash.slice(1)||"home");})();
})();