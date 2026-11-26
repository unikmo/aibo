(()=>{
"use strict";
const $=id=>document.getElementById(id), E=(tag,cls,content)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(content!==undefined)e.textContent=String(content??"");return e;};
const S={projects:[],activity:[],actions:[],connections:null,providers:null,selected:"",filter:"all",edition:new URLSearchParams(location.search).get("edition")==="custom"?"custom":"standard",busy:false,providerChoice:null};
const safe=(x)=>String(x??"");
function notice(title,msg){$("modalTitle").textContent=title;$("modalBody").textContent=msg;$("modalBody").replaceChildren(document.createTextNode(msg));$("overlay").classList.add("open");$("closeModal").focus()}
function formModal(title,fields,submit){$("modalTitle").textContent=title;const root=$("modalBody");root.replaceChildren();const form=E("form","modal-form");for(const f of fields){const label=E("label","",f.label),control=E(f.multiline?"textarea":f.options?"select":"input","field");control.name=f.name;if(f.multiline){control.rows=3;}else if(f.options){for(const [val,txt] of f.options){const option=E("option","",txt);option.value=val;control.append(option);}}else{control.type=f.type||"text";}control.value=f.value??"";if(f.required)control.required=true;if(f.max)control.maxLength=f.max;if(f.disabled)control.disabled=true;label.append(control);form.append(label);}
const msg=E("div","notice");msg.setAttribute("role","status");form.append(msg);const actions=E("div","modal-controls"),go=E("button","cta","Save");go.type="submit";actions.append(go);form.append(actions);form.onsubmit=async e=>{e.preventDefault();go.disabled=true;msg.textContent="Saving…";try{const outcome=await submit(Object.fromEntries(new FormData(form).entries()));if(outcome!=="keep-open")closeModal();await refresh();if(outcome==="project-saved"){show("soni");notice("Project ready","Project setup saved. You can now ask CariFive to work on this project.");}}catch(err){msg.className="notice error";msg.textContent=err.message;go.disabled=false;}};root.append(form);$("overlay").classList.add("open");form.querySelector("input,select,textarea")?.focus();}
function closeModal(){$("overlay").classList.remove("open");$("modalBody").replaceChildren();}
$("closeModal").onclick=closeModal;$("overlay").onclick=e=>{if(e.target===$("overlay"))closeModal()};document.addEventListener("keydown",e=>{if(e.key==="Escape")closeModal()});
async function api(url,options={}){const r=await fetch(url,{cache:"no-store",...options});let body;try{body=await r.json()}catch{body={error:"Server returned an invalid response"}}if(!r.ok)throw Error(body.error||"Request failed ("+r.status+")");return body}
const json=(method,body)=>({method,headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
function projectName(id){return S.projects.find(p=>p.id===id)?.name||id||"Project"}
function filteredProjects(){return S.selected?S.projects.filter(p=>p.id===S.selected):S.projects}
function show(name){if(!["home","soni","projects","activity","connections"].includes(name))return;document.querySelectorAll(".screen").forEach(x=>x.classList.toggle("active",x.id==="screen-"+name));document.querySelectorAll(".nav").forEach(x=>{const yes=x.dataset.screen===name;x.classList.toggle("active",yes);if(yes)x.setAttribute("aria-current","page");else x.removeAttribute("aria-current")});if(location.hash.slice(1)!==name)location.hash=name;document.title="AIBO — "+name[0].toUpperCase()+name.slice(1);if(name==="soni")renderConversation();if(name==="activity")refresh().catch(e=>console.warn('Activity refresh:',e.message));window.scrollTo(0,0)}
document.addEventListener("click",e=>{const r=e.target.closest("[data-go],[data-screen]");if(r){e.preventDefault();show(r.dataset.go||r.dataset.screen)}});
function renderRows(id,items,empty){const node=$(id);node.replaceChildren();if(!items.length){node.className="empty";node.textContent=empty;return;}node.className="";for(const item of items){const row=E("div","rowitem"),left=E("div");left.append(E("strong","",item.name),E("small","",item.info));row.append(left,E("span","pill"+(["failed","interrupted","Attention"].includes(item.status)?" gold":""),item.status||"Recorded"));if(item.click){row.style.cursor="pointer";row.tabIndex=0;row.setAttribute("role","button");row.onclick=item.click;row.onkeydown=e=>{if(e.key==="Enter")item.click()}}node.append(row)}}
function renderHome(){const p=filteredProjects(),num=k=>p.reduce((n,x)=>n+Number(x[k]||0),0),activity=S.activity.filter(x=>!S.selected||x.project===S.selected);$("countProjects").textContent=p.length;$("countActive").textContent=num("tasksOpen");$("countNeeds").textContent=num("tasksFailed");$("countDone").textContent=num("tasksCompleted");renderRows("homeNeeds",p.filter(x=>x.tasksFailed||x.tasksOpen||!x.setupComplete).slice(0,5).map(x=>({name:x.name,info:x.tasksFailed?"Latest work needs review":x.tasksOpen?"Work running":"Review setup",status:x.tasksFailed?"Attention":"Review",click:()=>openProject(x)})),"Nothing needs attention.");renderRows("homeRecent",activity.slice(0,5).map(x=>({name:projectName(x.project),info:(x.task||"Task").slice(0,130),status:x.status,click:()=>runDetail(x.id)})),"No activity yet.");renderRows("homeHealth",p.slice(0,6).map(x=>({name:x.name,info:x.readiness||"No readiness assessment",status:x.tasksFailed?"Attention":"Recorded"})),"No portfolio records available.")}
function renderProjects(){
 const node=$("projectCards");node.replaceChildren();
 const chosen=S.projects.find(p=>p.id===S.selected);
 if(chosen){
   $("projectSubheading").textContent=chosen.name;
   const card=E("div","project-summary");
   const state=E("div","meta",chosen.setupComplete?"Profile reviewed":"Setup needed");
   const actions=E("div","project-actions");
   const setup=E("button","cta",chosen.setupComplete?"Review sources":"Import sources");
   setup.onclick=()=>openProject(chosen);
   const open=E("button","secondary","Ask CariFive");open.onclick=()=>show("soni");
   actions.append(setup,open);card.append(state,actions);node.append(card);return;
 }
 $("projectSubheading").textContent=S.projects.length+" projects";
 for(const p of S.projects){
   const button=E("button","project-card");button.type="button";
   const left=E("div");left.append(E("h3","",p.name));
   if(p.industry)left.append(E("p","eyebrow",p.industry));
   const right=E("div","footer");right.append(E("span","category",p.setupComplete?"Ready":"Setup needed"),E("span","arrow","›"));
   button.append(left,right);
   button.onclick=()=>{S.selected=p.id;$("projectSelect").value=p.id;render();renderConversation();};
   node.append(button);
 }
}
function renderActivity(){const list=S.activity.filter(x=>(!S.selected||x.project===S.selected)&&(S.filter==="all"||S.filter==="completed"&&x.status==="completed"||S.filter==="running"&&["queued","running"].includes(x.status)||S.filter==="failed"&&["failed","interrupted"].includes(x.status)));$("activityCount").textContent=String(list.length);renderRows("activityRows",list.map(x=>({name:projectName(x.project),info:safe(x.task).slice(0,150)+" · "+safe(x.createdAt||""),status:x.status,click:()=>runDetail(x.id)})),"No activity.");renderRows("approvalRows",S.actions.filter(x=>!S.selected||x.project===S.selected).slice(0,15).map(x=>({name:x.kind||"Action",info:projectName(x.project)+" · "+safe(x.createdAt||""),status:x.status||"Unknown",click:()=>actionDetail(x)})),"No approvals.")}
function renderConnections(){
 const node=$("connectionsGrid"),focus=$("connectionFocus");node.replaceChildren();focus.replaceChildren();
 const data=S.connections;if(!data){focus.append(E("div","empty","Connection status unavailable."));return;}
 const entries=data.connectors||[],verified=entries.filter(x=>x.connected),registered=entries.filter(x=>x.status==="runtime-registered"&&!x.connected);
 $("connectionStatus").textContent=verified.length+" connected · "+registered.length+" available";
 const visible=[...verified];
 if(!visible.length)focus.append(E("div","empty","No tools connected."));
 const create=(c)=>{
   const card=E("div","conn"),left=E("div"),right=E("div");
   left.append(E("h3","",c.name),E("p","",c.category||"Integration"));
   right.append(E("span","pill",c.connected?"Verified":c.status==="runtime-registered"?"Available":"Available"));
   const button=E("button","secondary",c.connected?"Details":"Connect");button.type="button";
   button.style.marginTop="8px";button.onclick=()=>requestConnection(c);right.append(button);
   card.append(left,right);return card;
 };
 for(const c of visible.slice(0,12))focus.append(create(c));
 // A long catalog should not produce hundreds of cards until explicitly opened.
 const details=$("connectionsCatalog");
 const populate=()=>{
   if(details.dataset.loaded==="yes")return;
   details.dataset.loaded="yes";
   for(const c of entries.filter(x=>!visible.includes(x)))node.append(create(c));
 };
 if(details.open)populate();
 details.addEventListener("toggle",()=>{if(details.open)populate()},{once:true});
}
async function runDetail(id){if(!id)return;try{const r=await api("/api/run/"+encodeURIComponent(id));const result=r.result||{},parts=[r.task||"Task", "Status: "+r.status,"Provider: "+(r.provider||"Unknown"),"External actions executed: "+(r.externalActionsExecuted===true?"Yes":"No")];if(r.effectiveProvider)parts.push("Executed with: "+r.effectiveProvider);if(Array.isArray(r.providerAttempts))parts.push("Routing: "+r.providerAttempts.map(a=>a.provider+" ("+a.status+")").join(" → "));if(r.error)parts.push("Error: "+r.error);if(result.soni)parts.push("\nCariFive:\n"+result.soni);if(result.specialistResults)parts.push("\nSpecialist review:\n"+Object.entries(result.specialistResults).map(([n,t])=>n+": "+safe(t)).join("\n\n"));notice("Execution record",cleanCopy(parts.join("\n\n")))}catch(e){notice("Record unavailable",e.message)}}
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
async function openProject(p){
  try{
    const [state,local]=await Promise.all([api("/api/setup/custom/"+encodeURIComponent(p.id)),api("/api/setup/custom/"+encodeURIComponent(p.id)+"/sources").catch(()=>({suggestions:{}}))]);
    const root=$("modalBody");root.replaceChildren();$("modalTitle").textContent="Set up "+p.name;
    const form=E("form","modal-form compact-ingest");
    const linkLabel=E("label","","Website, GitHub or Google Drive link");
    const link=E("input","field");link.name="sourceLink";link.type="text";link.inputMode="url";link.autocomplete="url";
    link.placeholder="Paste a link";
    link.value=state.fields?.website||local.suggestions?.website?.value||"";
    linkLabel.append(link);form.append(linkLabel);
    form.append(E("p","source-guidance","Add a website, GitHub link or document. Check what can be read, then review and save the project."));
    const fileLabel=E("label","upload-source-label","Or add documents");
    const files=E("input");files.type="file";files.multiple=true;
    files.accept=".pdf,.docx,.pptx,.xlsx,.txt,.md,.csv,.json";fileLabel.append(files);form.append(fileLabel);
    const more=E("details","source-extra"),moreTitle=E("summary","","More sources");
    more.append(moreTitle);
    for(const [key,title] of [["website","Additional website"],["repository","Additional GitHub repository"],["drive","Additional Google Drive link"]]){
      const label=E("label","",title),input=E("input","field");input.name=key;input.type="text";input.inputMode="url";
      input.placeholder="Optional additional link";label.append(input);more.append(label);
    }
    form.append(more);
    const status=E("p","notice","");
    status.setAttribute("role","status");form.append(status);
    const actions=E("div","modal-controls");
    const scan=E("button","cta","Check sources");scan.type="submit";
    actions.append(scan);
    const driveStatus=await api("/api/oauth/google-drive/status/"+encodeURIComponent(p.id)).catch(()=>({available:false,status:"not-connected"}));
    if(driveStatus.available){
      const connect=E("button","secondary",driveStatus.status==="authorized-for-session"?"Drive connected":"Connect Google Drive");
      connect.type="button";connect.disabled=driveStatus.status==="authorized-for-session";
      connect.onclick=async()=>{
        try{
          const consent=await api("/api/oauth/google-drive/start",json("POST",{project:p.id}));
          if(!consent.authorizationUrl.startsWith("https://accounts.google.com/"))throw Error("Unexpected authorization host");
          window.open(consent.authorizationUrl,"_blank","noopener,noreferrer");
          status.textContent="Authorize read-only Drive access in the new browser tab, then select Inspect sources.";
        }catch(error){status.className="notice error";status.textContent=error.message;}
      };
      more.append(connect);
    }
    form.append(actions);root.append(form);
    $("overlay").classList.add("open");
    form.onsubmit=async e=>{
      e.preventDefault();scan.disabled=true;status.textContent="Checking the selected sources. This may take a few seconds…";
      try{
        const ids=[];
        if(files.files.length>5)throw Error("Select up to five documents");
        for(const file of files.files){
          if(file.size>12*1024*1024)throw Error(file.name+" exceeds 12 MB");
          const response=await fetch("/api/attachments/custom/"+encodeURIComponent(p.id),{
            method:"POST",headers:{"Content-Type":"application/octet-stream","X-AIBO-Filename":encodeURIComponent(file.name)},
            body:file});
          const result=await response.json();if(!response.ok)throw Error(result.error||"Upload failed");
          ids.push(result.id);
        }
        const data=Object.fromEntries(new FormData(form).entries());
        const normalizeLink=value=>{let raw=String(value||"").trim();if(!raw)return "";if(!/^https?:\/\//i.test(raw))raw="https://"+raw;if(/^http:\/\//i.test(raw))raw="https://"+raw.slice(7);const parsed=new URL(raw);if(parsed.protocol!=="https:"||!parsed.hostname||parsed.username||parsed.password)throw Error("Enter a valid public website, GitHub or Google Drive link");parsed.hash="";return parsed.href;};
        const main=normalizeLink(data.sourceLink);
        const hostname=main?new URL(main).hostname.toLowerCase():"";
        const kind=hostname==="github.com"?"repository":
          ["docs.google.com","drive.google.com"].includes(hostname)?"drive":"website";
        if(main&&normalizeLink(data[kind])&&normalizeLink(data[kind])!==main)throw Error("Use the More sources section to avoid two links of the same type");
        const sources={website:normalizeLink(data.website),repository:normalizeLink(data.repository),drive:normalizeLink(data.drive)};
        if(main)sources[kind]=main;
        const report=await api("/api/setup/custom/"+encodeURIComponent(p.id)+"/inspect",
          json("POST",{...sources,attachments:ids}));
        renderSourceReview(p,state,report);
      }catch(error){status.className="notice error";status.textContent=error.message;scan.disabled=false;}
    };
  }catch(e){notice("Project unavailable",e.message);}
}
function renderSourceReview(project,state,report){
  const extracted=report.suggestions||{};
  const fields=state.fields||{};
  const derived={};
  for(const [key,entry] of Object.entries(extracted))if(entry&&entry.value)derived[key]=entry.value;
  // An explicit prior owner-reviewed value always wins over an extracted suggestion.
  const values={...derived,...Object.fromEntries(Object.entries(fields).filter(([,value])=>value))};
  const sources=report.sources||[],failures=report.failures||[],conflicts=report.conflicts||{};
  const sourceReviewed=sources.some(x=>x.excerpt?.trim());
  const usableSuggestions=Object.keys(extracted).filter(k=>["name","goal","audience","website","region","successMeasure"].includes(k));
  // Never suggest that an inaccessible URL was read or a profile was inferred from it.
  if(!sourceReviewed&&sources.length)failures.push({kind:"source",source:"supplied material",reason:"No readable text was returned. Upload a document or enter a goal manually."});
  const missingSource=sourceReviewed?"":"No source could be read. Check the errors below or upload a document. You can still finish setup by entering a project goal.";
  const definitions=[
    ["name","Project name",true,80,false],
    ["region","Country / region",false,100,false],
    ["goal","Business goal"+(extracted.goal?" · suggested":""),!Boolean(extracted.goal||fields.goal),500,true],
    ["audience","Target buyer or audience",false,250,false],
    ["website","Website",false,200,false],
    ["successMeasure","Success measure",false,250,false],
    ["notes","Additional constraints",false,800,true]
  ];
  formModal("Review project profile · "+project.name,
    definitions.map(([name,label,required,max,multiline])=>({name,label,value:values[name]||"",required,max,multiline})),
    async values=>{
      await api("/api/setup/custom/"+encodeURIComponent(project.id),
        json("POST",{fields:values,step:2,complete:true,reviewSources:sourceReviewed}));
      S.selected=project.id;$("projectSelect").value=project.id;
      return "project-saved";
    });
  const form=$("modalBody").querySelector("form");
  const intro=E("div","source-review");
  intro.append(E("strong","",sources.length?("Read "+sources.length+" source"+(sources.length===1?"":"s")):"No sources read"));
  intro.append(E("p","",missingSource||"Check the source content and suggested details below, then save the project."));
  if(sourceReviewed&&!usableSuggestions.length)intro.append(E("p","source-warning","The source was read, but it did not state a clear business goal. Enter the goal yourself before saving."));
  if(sources.length){
    const list=E("details","source-extra"),heading=E("summary","","Sources inspected ("+sources.length+")");list.open=true;
    list.append(heading);
    for(const entry of sources.slice(0,8)){const item=E("div","source-list-item");item.append(E("strong","",entry.reference),E("p","",entry.excerpt?.trim()?entry.excerpt.slice(0,550):"The source returned no readable text."));list.append(item)}
    intro.append(list);
  }
  for(const [key,alternatives] of Object.entries(conflicts)){
    if(alternatives?.length)intro.append(E("p","source-warning","Conflicting "+key+": "+alternatives.map(x=>x.source).join(", ")+". Please verify."));
  }
  for(const failure of failures)intro.append(E("p","source-warning","Could not read "+failure.kind+" ("+(failure.source||"link") +"): "+failure.reason));
  form.prepend(intro);
  const optional=E("details","source-extra"),heading=E("summary","","Optional project details");
  optional.append(heading);
  for(const key of ["region","audience","website","successMeasure","notes"]){
    const input=form.querySelector('[name="'+key+'"]');
    if(input)optional.append(input.closest("label"));
  }
  const controls=form.querySelector(".modal-controls");
  if(controls)form.insertBefore(optional,controls);
  for(const [key,entry] of Object.entries(extracted)){
    const field=form.querySelector('[name="'+key+'"]');
    if(!field)continue;
    const label=field.closest("label");
    label.append(E("small","source-credit","Suggested from "+entry.source+" · "+entry.confidence));
  }
}
async function requestConnection(c){if(!S.selected){notice("Choose a project first","Select a project from the top bar before requesting "+c.name+".");return}try{const result=await api("/api/connections/request",json("POST",{connector:c.id,project:S.selected}));notice("Request recorded",result.alreadyRequested?"A setup request already exists for this project.":"A project-scoped setup request was recorded. Authentication and connection verification remain separate.");S.connections=await api("/api/connections/catalog");renderConnections()}catch(e){notice("Connection request failed",e.message)}}
function cleanCopy(value){
  let text=safe(value);
  // Legacy run records may contain API provider error payloads.
  if(/invalid_api_key|Incorrect API key provided|sk-(?:proj-)?[A-Za-z0-9]/i.test(text))
    return "OpenAI API authentication failed. Check your API key in Connections. No result was generated.";
  text=text.replace(/\r\n?/g,"\n")
    .replace(/â€”|â€“/g,"—").replace(/â€™/g,"’").replace(/â€œ/g,"“").replace(/â€�/g,"”")
    .replace(/Â /g," ").replace(/Â(?=\s)/g,"")
    .replace(/&nbsp;|&#160;/gi," ").replace(/&lt;/gi,"<").replace(/&gt;/gi,">")
    .replace(/<br\b[^>]*\/?>/gi,"\n").replace(/<\/(?:div|p|li|section)>/gi,"\n")
    .replace(/<[^>]{1,1000}>/g,"")
    .replace(/\\([*\x60_])/g,"$1")
    .replace(/\[([^\]]{1,200})\]\((?:file:\/\/|\/[A-Za-z]:\/|[A-Za-z]:\\)[^)]+\)/g,"$1")
    .replace(/\[([^\]]{1,200})\]\(([^)]+)\)/g,"$1 ($2)")
    .replace(/^\s{0,3}#{1,6}\s+/gm,"")
    .replace(/\*\*([^*]+)\*\*/g,"$1").replace(/__([^_]+)__/g,"$1")
    .replace(/(?<!\w)\*([^*\n]+)\*(?!\w)/g,"$1")
    .replace(/\x60([^\x60]+)\x60/g,"$1")
    .replace(/^\s*[-*]\s+/gm,"• ")
    .replace(/\n{3,}/g,"\n\n")
    .replace(/\b(?:OPENAI|ANTHROPIC|GITHUB|GOOGLE)_API_KEY\s*[:=]\s*\S+/gi,"[credential hidden]")
    .trim();
  return text;
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
  const screen=$("screen-soni");
  screen.classList.toggle("is-empty",true);
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
      logMessage("agent","CariFive · "+r.status,shortAnswer(answer),extended);
    }
  }catch(e){root.append(E("div","empty","Conversation unavailable: "+e.message))}
  screen.classList.toggle("is-empty",root.children.length===0);
  root.scrollTop=root.scrollHeight;
}
// Derive the visual state from actual message nodes, including asynchronous
// updates and restored history; never use the absence of a selected project alone.
const conversationRoot=$("conversation");
const syncSoniLayout=()=>{$("screen-soni").classList.toggle("is-empty",conversationRoot.children.length===0)};
new MutationObserver(syncSoniLayout).observe(conversationRoot,{childList:true});
syncSoniLayout();
const soniComposer=$("soniPrompt");
function sizeComposer(){soniComposer.style.height="34px";soniComposer.style.height=Math.min(175,Math.max(34,soniComposer.scrollHeight))+"px";}
soniComposer.addEventListener("input",sizeComposer);
soniComposer.addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey&&!e.isComposing){e.preventDefault();$("reviewPrompt").click()}});

function providerOptions(){const select=$("soniProvider");select.replaceChildren();for(const [val,label] of [["mock","Demo (no paid AI)"],["auto","Auto · Codex → Claude"],["codex-local","Codex · local CLI"],["claude-local","Claude · local CLI"],["openai","OpenAI API"],["anthropic","Anthropic API"],["openrouter","OpenRouter API"],["vercel-gateway","Vercel AI Gateway"],["together","Together API"],["groq","Groq API"]]){const opt=E("option","",label+(S.providers?.ready?.[val]?" · available":""));opt.value=val;select.append(opt)}select.value=S.providerChoice||"auto";select.title="Automatic: Codex CLI first, Claude CLI on failure. Paid API requires separate approval.";providerConsent()}
function providerConsent(){const paid=["openai","anthropic","openrouter","vercel-gateway","together","groq"].includes($("soniProvider").value);document.querySelector(".consent").classList.toggle("visible",paid);$("soniConsent").checked=false;}
$("soniProvider").onchange=()=>{S.providerChoice=$("soniProvider").value;providerConsent()};
$("reviewPrompt").onclick=async()=>{const task=$("soniPrompt").value.trim(),project=S.selected,provider=$("soniProvider").value;const button=$("reviewPrompt");if(!project){notice("Select a project","Choose an existing project before starting a task.");return}if(task.length<5){notice("Describe the task","Enter at least five characters.");return}if(S.busy)return;S.busy=true;button.disabled=true;$("promptHint").textContent="Submitting task…";try{const r=await api("/api/work/custom/"+encodeURIComponent(project),json("POST",{task,provider,consent:$("soniConsent").checked}));$("soniPrompt").value="";sizeComposer();$("promptHint").textContent="Run started · "+r.id;await renderConversation();for(let i=0;i<255;i++){
  await new Promise(ok=>setTimeout(ok,2000));
  const status=await api("/api/run/"+encodeURIComponent(r.id));
  if(["completed","failed","interrupted"].includes(status.status)){
    $("promptHint").textContent=status.status==="completed"?"Completed":status.error||"Run "+status.status;
    await refresh();await renderConversation();
    break;
  }
  // Maintain truthful status during lengthy multi-specialist execution.
  if(i%5===0){
    $("promptHint").textContent=status.status==="queued"?"Queued — checking execution": "CariFive working · "+Math.round((i+1)*2/60)+" min";
    await renderConversation();
  }
  if(i===254){$("promptHint").textContent="Execution deadline reached. Check Activity.";await renderConversation();}
}}catch(e){$("promptHint").textContent="Task not started";notice("CariFive could not start",e.message)}finally{button.disabled=false;S.busy=false;}};
$("projectSelect").onchange=e=>{S.selected=e.target.value;render();renderConversation()};
$("newProjectBtn").onclick=()=>{
 if(S.edition!=="custom"){notice("Five project slots","Standard includes five permanent workspaces. Choose a slot from the Projects page.");return;}
 formModal("New project",[{name:"name",label:"Project name",required:true,max:80}],async d=>{
   const result=await api("/api/projects/custom",json("POST",{name:d.name,industry:"",region:"",corePack:null,addOns:[]}));
   S.selected=result.project;
   await refresh();
   show("projects");
   const created=S.projects.find(p=>p.id===result.project);
   if(created){await openProject(created);return "keep-open";}
 });
};
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
async function agentSettings(){if(!S.selected){notice("Choose a project","Select a project to edit CariFive's project-scoped settings.");return}try{const a=await api("/api/agent-setup/custom/"+encodeURIComponent(S.selected));formModal("Agent setup · "+projectName(S.selected),[{name:"workingStyle",label:"Working style",value:a.workingStyle,options:[["autonomous","Autonomous within permissions"],["supervised","Supervised"]]}],async d=>{await api("/api/agent-setup/custom/"+encodeURIComponent(S.selected),json("PUT",{workingStyle:d.workingStyle}))});}catch(e){notice("Agent settings unavailable",e.message)}}
$("settingsBtn").onclick=()=>{notice("Settings","Choose the control area. Permissions, AI provider routing and usage limits remain locally managed.");const controls=E("div","modal-controls");for(const [label,fn] of [["Cost controls",costSettings],["AI providers",providerSettings],["API credentials",providerCredentials],["Select model",providerModel],["Project agents",agentSettings]]){const button=E("button","secondary",label);button.type="button";button.onclick=fn;controls.append(button)}$("modalBody").append(controls)};

$("accountBtn").onclick=()=>notice("Your CariFive version","One-time purchase: keep this installed version without renewal or activation keys. Optional feature upgrades: $48/year or individually priced. AI provider costs are separate. Unsupported customer modifications and custom support may be billable; statutory defect remedies and required security updates remain protected.");
async function refresh(){let projectState;const opts=[api("/api/portfolio/"+S.edition),api("/api/products/"+S.edition),api("/api/actions"),api("/api/connections/catalog"),api("/api/ai-providers")];const all=await Promise.allSettled(opts);const get=i=>all[i].status==="fulfilled"?all[i].value:null;const portfolio=get(0)||{projects:[],recentWork:[]};projectState=get(1);S.projects=portfolio.projects?.length?portfolio.projects:(S.edition==="custom"?projectState?.projects||[]:(projectState?.slots||[]).map(x=>({...x,id:x.id||"standard-slot-"+x.slot,industry:"Standard",readiness:x.setupComplete?"Ready":"Setup needed",tasksOpen:0,tasksCompleted:0,tasksFailed:0})));S.activity=(portfolio.recentWork||[]).filter(x=>S.edition==="custom"?!String(x.project||"").startsWith("standard-slot-"):String(x.project||"").startsWith("standard-slot-"));S.actions=(get(2)?.actions||[]).filter(x=>S.edition==="custom"?!String(x.project||"").startsWith("standard-slot-"):String(x.project||"").startsWith("standard-slot-"));S.connections=get(3);S.providers=get(4);const sel=$("projectSelect"),prior=S.selected;sel.replaceChildren();const allOpt=E("option","","All projects");allOpt.value="";sel.append(allOpt);for(const p of S.projects){const o=E("option","",p.name);o.value=p.id;sel.append(o)}S.selected=S.projects.some(p=>p.id===prior)?prior:"";sel.value=S.selected;$("editionLabel").textContent=(S.edition==="custom"?"Portfolio":"Standard")+" · Owned version · "+S.projects.length+" projects";render();renderConnections();providerOptions();if(all[0].status==="rejected")$("homeNeeds").textContent="Local backend unavailable — "+all[0].reason.message;}
function render(){
 renderHome();renderProjects();renderActivity();
 $("soniProject").textContent=projectName(S.selected)||"Select a project above to begin";
 $("newProjectBtn").hidden=S.edition!=="custom";
}

// The hosted shell is a safe visual preview until an authenticated backend is deployed.
if(location.protocol==="https:"&&!["localhost","127.0.0.1"].includes(location.hostname)){
  const banner=document.createElement("div");
  banner.setAttribute("role","status");
  banner.style.cssText="position:relative;z-index:100;background:#fff5db;color:#39312a;border-bottom:1px solid #d3b873;padding:10px 18px;font:13px/1.5 Inter,Arial,sans-serif;text-align:center";
  banner.textContent="CariFive web preview — the local execution engine is not connected. Tasks and integrations are unavailable online.";
  document.body.prepend(banner);
}
(async()=>{await refresh();show(location.hash.slice(1)||"home");})();
})();