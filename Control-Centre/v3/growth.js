/* CariFive Growth OS: local, owner-reviewed campaign evidence. No publishing side effects. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
const E=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=String(text);return n};
const f=(id)=>encodeURIComponent(id);
const post=async(path,value)=>{
 const r=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json"},
   body:JSON.stringify(value),cache:"no-store"});
 const data=await r.json();if(!r.ok)throw Error(data.error||"Growth operation failed");return data;
};
const get=async(path)=>{const r=await fetch(path,{cache:"no-store"});const d=await r.json();
 if(!r.ok)throw Error(d.error||"Growth data unavailable");return d};
const labels={brandFit:"Brand fit",originality:"Originality",timing:"Timing",
 expectedAttention:"Expected attention",shareability:"Shareability",
 conversionPotential:"Conversion potential",earnedMediaPotential:"Earned media",
 effort:"Effort",reputationalRisk:"Reputation risk",legalIpRisk:"Legal / IP risk",
 misinterpretationRisk:"Misinterpretation risk",hook:"First-line hook",
 conversion:"Conversion",naturalness:"Natural language",
 audienceRelevance:"Audience relevance"};
const oppScores=["brandFit","originality","timing","expectedAttention","shareability",
 "conversionPotential","earnedMediaPotential","effort","reputationalRisk",
 "legalIpRisk","misinterpretationRisk"];
const qualityScores=["originality","hook","conversion","shareability",
 "naturalness","audienceRelevance","brandFit"];
const channels=["email","linkedin","tiktok","instagram","facebook","youtube","reddit",
 "internations","x","threads","pinterest","quora","discord","slack",
 "forums","creators","partnerships","pr","events","guerrilla"];
const states=["EXISTS_AND_USABLE","EXISTS_BUT_WEAK","EXISTS_BUT_OFF_BRAND",
 "MISSING_AND_RECOMMENDED","MISSING_NOT_NEEDED","BLOCKED_UNKNOWN"];
let current="";
function modal(title){
 $("modalTitle").textContent=title;const body=$("modalBody");body.replaceChildren();
 $("overlay").classList.add("open");return body;
}
function detail(title,lines,actions=[]){
 const root=modal(title);
 for(const line of lines){root.append(E("p","growth-line",line))}
 if(actions.length){const bar=E("div","growth-buttons");
  for(const [name,click] of actions){const b=E("button","secondary",name);b.type="button";
   b.onclick=()=>Promise.resolve(click()).catch(e=>detail("Growth action unavailable",[e.message],[["Back",()=>open(current)]]));
   bar.append(b)}root.append(bar)}
}
function form(title,fields,save){
 const root=modal(title),node=E("form","growth-form");
 for(const field of fields){
  const label=E("label","",field.label||field.name);
  const el=E(field.options?"select":field.multi?"textarea":"input","field");
  el.name=field.name;if(field.options){for(const option of field.options){
    const o=E("option","",Array.isArray(option)?option[1]:option);
    o.value=Array.isArray(option)?option[0]:option;el.append(o)
  }}else if(!field.multi)el.type=field.type||"text";
  if(field.multi)el.rows=3;
  if(field.value!==undefined)el.value=field.value;
  if(field.required)el.required=true;
  if(field.type==="number"){el.min="0";el.max="10";el.step=".1"}
  label.append(el);node.append(label);
 }
 const message=E("p","notice");
 const submit=E("button","cta","Save reviewed record");submit.type="submit";
 node.append(message,submit);
 node.onsubmit=async e=>{
  e.preventDefault();submit.disabled=true;
  const values=Object.fromEntries(new FormData(node).entries());
  try{const result=await save(values);if(result!=="keep-open")await open(current)}
  catch(err){message.textContent=err.message;message.setAttribute("role","alert")}
  finally{submit.disabled=false}
 };
 root.append(node);node.querySelector("input,select,textarea")?.focus();
}
async function open(project){
 current=project;
 let data;try{data=await get("/api/growth/project/"+f(project))}
 catch(e){detail("Growth data unavailable",[e.message]);return}
 const ready=data.readiness;
 const lines=[
  "Brand readiness: "+ready.status+(ready.missing.length?" · Missing: "+ready.missing.join(", "):""),
  "Autonomy: L"+data.autonomy.level+" · L2 prepares content for approval; no publishing is implied.",
  "Radar: "+data.opportunities.length+" opportunities · "+
  data.experiments.length+" experiments · "+data.creativeReviews.length+" creative reviews.",
  "Current results are locally recorded. No social account, campaign or metric has been externally verified."
 ];
 const actions=[
  ["Review brand",()=>brand(project,data)],
  ["Creative personality",()=>mischief(project,data)],
  ["Radar opportunity",()=>opportunity(project)],
  ["Review content",()=>creative(project,data)],
  ["Plan growth test",()=>experiment(project,data)],
  ["Campaign outcomes",()=>campaigns(project,data)],
  ["Autonomy policy",()=>autonomy(project,data)],
  ["Today's action",()=>today()]
 ];
 detail("Growth · "+project,lines,actions);
}
async function brand(project,data){
 const b=data.brand||{},saved=Object.entries(data.channels);
 const fields=[
  ...["product","audience","buyer","offer","conversion","positioning","successMetric",
      "successThreshold"].map(n=>({name:n,label:n.replace(/[A-Z]/g,c=>" "+c).trim(),
                         value:b[n]||"",required:true,multi:n==="positioning"})),
  {name:"channel",label:"Platform assessed",options:channels,value:saved[0]?.[0]||"linkedin"},
  {name:"platformState",label:"Platform status",options:states,value:saved[0]?.[1]||"BLOCKED_UNKNOWN"},
  {name:"assets",label:"Existing assets (one per line)",value:(b.assets||[]).join("\n"),multi:true,required:true},
  {name:"evidence",label:"Evidence / reviewed sources (one per line)",
    value:(b.evidence||[]).join("\n"),multi:true,required:true}
 ];
 form("Owner-review brand facts",fields,async v=>{
  const channels={...data.channels,[v.channel]:v.platformState};
  const body=Object.fromEntries(["product","audience","buyer","offer","conversion",
       "positioning","successMetric","successThreshold"].map(k=>[k,v[k]]));
  await post("/api/growth/brand/"+f(project),{...body,channels,
    assets:v.assets.split("\n").map(x=>x.trim()).filter(Boolean),
    evidence:v.evidence.split("\n").map(x=>x.trim()).filter(Boolean),
    reviewedByOwner:true});
 });
}
function mischief(project,data){
 const m=data.mischief||{};
 form("Brand Mischief Profile",[
  {name:"voice",label:"Brand voice",value:m.voice||"",required:true,multi:true},
  {name:"humor",label:"Humor /10",type:"number",value:m.humor??5,required:true},
  {name:"provocation",label:"Provocation /10",type:"number",value:m.provocation??2,required:true},
  {name:"prohibitedThemes",label:"Prohibited themes (one per line)",
    multi:true,value:(m.prohibitedThemes||[]).join("\n")},
  {name:"boundaries",label:"Creative, legal and reputational boundaries",
    multi:true,value:m.boundaries||"",required:true}
 ],async v=>post("/api/growth/mischief/"+f(project),{
   voice:v.voice,humor:Number(v.humor),provocation:Number(v.provocation),
   prohibitedThemes:v.prohibitedThemes.split("\n").map(x=>x.trim()).filter(Boolean),
   boundaries:v.boundaries
 }));
}
function opportunity(project){
 form("Radar · Review an opportunity",[
  {name:"title",label:"Opportunity / event",required:true},
  {name:"source",label:"Source and date / evidence",required:true},
  {name:"reason",label:"Why it fits this brand",multi:true,required:true},
  ...oppScores.map(k=>({name:k,label:(labels[k]||k)+" /10 · estimate",
    type:"number",value:5,required:true}))
 ],async v=>post("/api/growth/opportunity/"+f(project),{
  title:v.title,source:v.source,reason:v.reason,
  scores:Object.fromEntries(oppScores.map(k=>[k,Number(v[k])]))
 }));
}
function creative(project,data){
 const fields=[
  {name:"content",label:"Draft copy (not published)",multi:true,required:true},
  {name:"channel",label:"Channel",options:channels},
  ...qualityScores.map(k=>({name:k,label:(labels[k]||k)+" /10 · editor rating",
    type:"number",value:8,required:true})),
  {name:"factChecked",label:"Facts independently checked?",options:[["false","No"],["true","Yes"]]},
  {name:"rulesChecked",label:"Platform rules checked?",options:[["false","No"],["true","Yes"]]}
 ];
 if(!data.mischief){detail("Creative review requires brand personality",
 ["Set a Brand Mischief Profile first; this avoids generic, off-brand copy."],
 [["Profile",()=>mischief(project,data)],["Back",()=>open(project)]]);return}
 form("Creative quality · Manual editorial rubric",fields,async v=>{
  const review=await post("/api/growth/creative-review/"+f(project),{
   content:v.content,channel:v.channel,
   scores:Object.fromEntries(qualityScores.map(k=>[k,Number(v[k])])),
   factChecked:v.factChecked==="true",rulesChecked:v.rulesChecked==="true"});
  detail("Creative decision: "+review.status,
   ["Quality estimate: "+review.score+"/10",
    review.passed?"Saved as passing editorial review; not published.":
      "Rewrite needed: "+review.issues.join(", "),
    "This rubric records editor judgments; it is not an independently executed AI evaluation."],
   [["Back to Growth",()=>open(project)]]);
  return "keep-open";
 });
}
function experiment(project,data){
 if(!data.opportunities.length){detail("No radar opportunities",
  ["Record and score a source-backed opportunity first."],
  [["Add opportunity",()=>opportunity(project)],["Back",()=>open(project)]]);return}
 form("New growth experiment",[
  {name:"opportunityId",label:"Opportunity",options:data.opportunities.map(o=>[o.id,o.title+" · "+o.decision])},
  {name:"channel",label:"Channel",options:channels},
  {name:"hypothesis",label:"Test hypothesis",multi:true,required:true},
  {name:"primaryMetric",label:"Commercial metric",required:true},
  {name:"threshold",label:"Success threshold (positive number)",required:true},
  {name:"assetRoute",label:"Existing asset or production route",required:true},
  {name:"cta",label:"Call to action",required:true}
 ],async v=>post("/api/growth/experiment/"+f(project),v));
}
function campaigns(project,data){
 const lines=data.experiments.length?data.experiments.map(e=>
  e.id+" · "+e.status+" · "+e.primaryMetric+" ≥ "+e.threshold+
  " · Outcome: "+e.outcome+(e.outcomeIsProvisional?" (provisional)":"")):
  ["No growth experiments recorded."];
 const actions=data.experiments.length?data.experiments.slice(-4).map(e=>
  ["Review "+e.id.slice(-5),()=>campaign(project,e,data)]):[];
 actions.push(["New growth test",()=>experiment(project,data)],["Back",()=>open(project)]);
 detail("Experiments · "+project,lines,actions);
}
function campaign(project,e,data){
 const actions=[["Back",()=>open(project)]];
 const advance=(status,fields,transform)=>()=>form("Campaign · "+status,fields,
   async v=>post("/api/growth/transition/"+f(project)+"/"+f(e.id),
     {status,...transform(v)}));
 if(e.status==="DRAFT"){
  const reviews=(data.creativeReviews||[]).filter(r=>r.passed&&r.channel===e.channel);
  if(reviews.length)actions.unshift(["Submit for approval",advance("READY_FOR_APPROVAL",
    [{name:"creativeReviewId",label:"Passing saved creative review",
      options:reviews.map(r=>[r.id,r.id+" · "+r.score+"/10"])}],v=>v)]);
  else actions.unshift(["Review creative first",()=>creative(project,data)]);
 }else if(e.status==="READY_FOR_APPROVAL")
  actions.unshift(["Record owner approval",advance("APPROVED",
   [{name:"approval",label:"Type APPROVE to confirm review",required:true}],
   v=>({ownerApproved:v.approval==="APPROVE"}))]);
 else if(e.status==="APPROVED"){
  actions.unshift(["Record manual launch",advance("RUNNING",
   [{name:"manualLaunchEvidence",label:"Evidence of manually executed launch (unverified)",
     required:true,multi:true}],v=>v)]);
 }else if(e.status==="RUNNING"||e.status==="MEASURED"){
  actions.unshift(["Record measurement",()=>form("Record measured result",[
   {name:"value",label:"Observed "+e.primaryMetric,required:true},
   {name:"source",label:"Source (manual; not independently verified)",required:true},
   {name:"observedAt",label:"Observation ISO date/time",value:new Date().toISOString(),required:true},
   {name:"websiteEvidence",label:"Evidence-backed website intervention?",
    options:[["false","No"],["true","Yes"]]},
   {name:"websiteIssue",label:"Website defect and commercial impact (required for intervention)",
    multi:true},
   {name:"websiteEvidenceRef",label:"Website evidence reference (required for intervention)"}
  ],async v=>post("/api/growth/measure/"+f(project)+"/"+f(e.id),
     {...v,websiteEvidence:v.websiteEvidence==="true"}))]);
  if(e.status==="MEASURED")
   actions.unshift(["Close experiment",advance("CLOSED",[],()=>({}))]);
 }
 detail(e.id+" · "+e.status,[
  e.hypothesis,"Channel: "+e.channel+" · CTA: "+e.cta,
  "Outcome: "+e.outcome+" · External actions executed by this module: No",
  "Provider execution and performance are not verified by this local evidence ledger."
 ],actions);
}
function autonomy(project,data){
 const a=data.autonomy;
 form("Autonomy · Scoped owner authority",[
  {name:"level",label:"Autonomy level",options:[
    ["0","L0 · Recommend only"],["1","L1 · Draft"],["2","L2 · Approval (default)"],
    ["3","L3 · Scoped low risk"],["4","L4 · Scoped reactive low risk"]],value:String(a.level)},
  {name:"authorizedChannel",label:"Permitted channel",options:channels,
    value:a.authorizedChannels[0]||"linkedin"},
  {name:"authorizedType",label:"Low-risk task type",
    options:[["routine-post","Routine post"],["routine-followup","Routine follow-up"]]},
  {name:"approval",label:"Type AUTHORIZE to grant scoped L3/L4 capability"}
 ],async v=>{
  const level=Number(v.level);
  return post("/api/growth/autonomy/"+f(project),{
   level,authorizedChannels:level>=3?[v.authorizedChannel]:[],
   authorizedLowRiskTypes:level>=3?[v.authorizedType]:[],
   scopeApproved:level>=3&&v.approval==="AUTHORIZE"});
 });
}
async function today(){
 const result=await get("/api/growth/today");
 const a=result.action;
 detail("Today · One actionable opportunity",
  a?[
   "Brand: "+a.project,"Opportunity: "+a.objective,
   "Priority score: "+a.priority+"/100",
   a.recommendedAction,"Evidence: "+a.source,
   "Status: "+a.execution+" · Approval and channel checks still required"
  ]:[result.reason],
  a?[["Open brand Growth",()=>open(a.project)]]:[]);
}
async function dashboard(){
 const result=await get("/api/growth/dashboard");
 detail("Growth portfolio",[
  result.count+" brands configured · independently verified commercial outcomes: unavailable",
  ...result.brands.slice(0,12).map(b=>
   b.project+" · "+b.readiness+" · "+b.experiments+" tests · "+b.measured+" measured"),
  "Results entered by users are provisional until source verification."
 ],[["Today's best action",today]]);
}
function quickActions(){
 const composer=document.querySelector("#screen-home .home-talk");
 if(!composer||document.querySelector("#screen-home .growth-quicklinks"))return;
 const root=E("div","growth-quicklinks");
 for(const [label,action] of [["Growth portfolio",dashboard],
                              ["Today's action",today]]){
  const button=E("button","secondary",label);button.type="button";
  button.onclick=()=>Promise.resolve(action()).catch(err=>
   detail("Growth data unavailable",[err.message]));
  root.append(button);
 }
 composer.after(root);
}
quickActions();
window.CariFiveGrowth={open,today,dashboard};
})();
