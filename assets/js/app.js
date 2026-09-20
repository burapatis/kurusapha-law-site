/* คลังกฎหมายและข้อเสนอปฏิรูปคุรุสภา — แอปฝั่งผู้ใช้ (vanilla JS) */
"use strict";
const NAV = [
  ["index.html","หน้าแรก"],["library.html","คลังกฎหมาย"],["tracker.html","ทะเบียนปฏิรูป"],
  ["compare.html","เทียบตัวบท"],["hierarchy.html","ผังลำดับศักดิ์"],
  ["opinions.html","ความเห็นกฎหมาย"],["proposals.html","ข้อเสนอดำเนินงาน"]
];
const RSMAP={keep:["คงไว้","b-keep"],amend:["แก้ไข","b-amend"],repeal:["ยกเลิก/ยกฐาน","b-repeal"],
  verify:["ตรวจสอบ","b-verify"],done:["ดำเนินการแล้ว","b-done"]};
const STMAP={in_force:["ใช้บังคับ","b-inforce"],amended:["มีแก้ไข","b-amended"],repealed:["ยกเลิกแล้ว","b-repealed"],
  reference:["เอกสารอ้างอิง","b-reference"],draft:["ร่าง","b-draft"]};
const GAZETTE="https://ratchakitcha.soc.go.th/";
const $=(s,r=document)=>r.querySelector(s);
const $$=(s,r=document)=>[...r.querySelectorAll(s)];
function el(tag,attrs={},...kids){const e=document.createElement(tag);
  for(const k in attrs){if(k==="class")e.className=attrs[k];else if(k==="html")e.innerHTML=attrs[k];else e.setAttribute(k,attrs[k]);}
  kids.flat().forEach(k=>e.append(k&&k.nodeType?k:document.createTextNode(k==null?"":k)));return e;}
async function getJSON(p){const r=await fetch(p);if(!r.ok)throw new Error(p+" "+r.status);return r.json();}
function badge(map,key){if(!key||!map[key])return null;const[t,c]=map[key];return el("span",{class:"badge "+c},t);}
function esc(s){return(s==null?"":String(s)).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));}

/* header + footer */
function chrome(){
  const page=document.body.dataset.page||"index.html";
  const hdr=el("header",{class:"site"},
    el("div",{class:"wrap"},
      el("a",{class:"brand",href:"index.html"}, el("span",{class:"dot"}), "คลังกฎหมายคุรุสภา"),
      el("nav",{}, NAV.map(([h,t])=>el("a",{href:h,class:page===h?"active":""},t)))
    ));
  document.body.prepend(hdr);
  document.body.append(el("footer",{class:"site"},
    el("div",{class:"wrap"},"ระบบภายในทีมยกร่าง • ฐานข้อมูลคอร์ปัสคุรุสภา • จัดทำโดยโครงการปรับปรุงอนุบัญญัติคุรุสภา • v1 (เฟส 1)")));
}
function head(title,sub){const h=$("#pagehead");if(h){h.append(el("h1",{},title));if(sub)h.append(el("p",{},sub));}}

/* ---------- DASHBOARD ---------- */
async function initDashboard(){
  head("ภาพรวมระบบ","คลังกฎหมายและเครื่องมือบริหารการปฏิรูปอนุบัญญัติคุรุสภา");
  const cat=await getJSON("data/catalog.json");
  let reg={items:[]},prop={groups:[]};
  try{reg=await getJSON("data/register.json")}catch(e){}
  try{prop=await getJSON("data/proposals.json")}catch(e){}
  const items=cat.items, ksp=items.filter(i=>i.isKurusapha&&!i.isDeliverable);
  const inforce=items.filter(i=>i.status==="in_force").length;
  const repealed=items.filter(i=>i.status==="repealed").length;
  const deliver=items.filter(i=>i.isDeliverable).length;
  const stats=el("div",{class:"grid g4"},
    stat(items.length,"เอกสารในคลัง","ทั้งหมด (คอร์ปัสคุรุสภา)"),
    stat(inforce,"ฉบับใช้บังคับ","สถานะ in force"),
    stat(reg.items.length||"—","รายการในทะเบียนปฏิรูป","คงไว้/แก้ไข/ยกเลิก"),
    stat(deliver,"เอกสารส่งมอบโครงการ","ฉบับรวม/ร่าง/ความเห็น"));
  $("#app").append(stats);
  // reform status summary
  const rs={};(reg.items||[]).forEach(r=>{rs[r.status]=(rs[r.status]||0)+1});
  const sumCard=el("div",{class:"card"}, el("h3",{},"สรุปสถานะการปฏิรูป (ทะเบียน)"),
    el("div",{class:"pill-row"}, Object.keys(RSMAP).map(k=>rs[k]?el("span",{class:"chip"},[badge(RSMAP,k)," ",String(rs[k])+" รายการ"]):null).filter(Boolean)),
    el("a",{href:"tracker.html"},"ดูทะเบียนปฏิรูปทั้งหมด →"));
  // urgent proposals
  const urg=(prop.groups||[]).find(g=>/เร่งด่วน/.test(g.title));
  const urgCard=el("div",{class:"card"}, el("h3",{},"งานเร่งด่วน"),
    urg?el("ul",{style:"margin:6px 0 0;padding-left:18px"},(urg.items||[]).slice(0,5).map(it=>el("li",{style:"margin-bottom:4px"},it.title)))
        :el("p",{class:"count"},"—"),
    el("a",{href:"proposals.html"},"ดูข้อเสนอทั้งหมด →"));
  $("#app").append(el("div",{class:"grid g2",style:"margin-top:14px"},sumCard,urgCard));
  // categories
  const byCat={};items.forEach(i=>{byCat[i.category]=(byCat[i.category]||0)+1});
  const catCard=el("div",{class:"card",style:"margin-top:14px"},el("h3",{},"จำนวนเอกสารแยกหมวด"),
    el("div",{}, Object.entries(byCat).sort((a,b)=>b[1]-a[1]).map(([c,n])=>
      el("a",{class:"chip",href:"library.html?cat="+encodeURIComponent(c)},c+" ("+n+")"))));
  $("#app").append(catCard);
  $("#app").append(el("p",{class:"disclaimer",style:"margin-top:16px"},
    "หมายเหตุ: เมทาดาทาสังเคราะห์จากชื่อไฟล์/หมวด + เสริมข้อมูลตรวจทานสำหรับฉบับสำคัญ; การค้นหาเต็มข้อความ (บทเต็ม) จะเพิ่มในเฟสถัดไป"));
}
function stat(n,l,s){return el("div",{class:"card stat"},el("span",{class:"n"},String(n)),el("span",{class:"l"},l),s?el("span",{class:"s"},s):null);}

/* ---------- LIBRARY ---------- */
let LIB=[];
async function initLibrary(){
  head("คลังกฎหมาย","ค้นหาและกรองเอกสารกฎหมายในคอร์ปัสคุรุสภา");
  const cat=await getJSON("data/catalog.json");LIB=cat.items;
  const q=new URLSearchParams(location.search);
  const cats=cat.meta.categories, types=[...new Set(LIB.map(i=>i.type))].sort();
  const bar=el("div",{class:"controls"},
    el("input",{type:"search",id:"q",placeholder:"ค้นหาชื่อกฎหมาย / คำสำคัญ / ปี …"}),
    selOf("cat","— ทุกหมวด —",cats),
    selOf("type","— ทุกประเภท —",types),
    selOf("status","— ทุกสถานะ —",Object.keys(STMAP).map(k=>[k,STMAP[k][0]])),
    el("span",{class:"count",id:"cnt"}));
  $("#app").append(bar,el("div",{id:"list"}));
  if(q.get("cat"))$("#cat").value=q.get("cat");
  if(q.get("status"))$("#status").value=q.get("status");
  ["q","cat","type","status"].forEach(id=>$("#"+id).addEventListener("input",renderLib));
  renderLib();
}
function selOf(id,ph,opts){const s=el("select",{id});s.append(el("option",{value:""},ph));
  opts.forEach(o=>{const[v,t]=Array.isArray(o)?o:[o,o];s.append(el("option",{value:v},t))});return s;}
function renderLib(){
  const q=$("#q").value.trim().toLowerCase(),c=$("#cat").value,t=$("#type").value,st=$("#status").value;
  const toks=q.split(/\s+/).filter(Boolean);
  let r=LIB.filter(i=>{
    if(c&&i.category!==c)return false; if(t&&i.type!==t)return false; if(st&&i.status!==st)return false;
    if(toks.length){const hay=(i.title+" "+(i.issuer||"")+" "+(i.note||"")+" "+(i.year||"")+" "+(i.reformCode||"")).toLowerCase();
      return toks.every(k=>hay.includes(k));}
    return true;});
  $("#cnt").textContent="พบ "+r.length+" ฉบับ";
  const list=$("#list");list.innerHTML="";
  if(!r.length){list.append(el("p",{class:"count"},"ไม่พบเอกสารที่ตรงเงื่อนไข"));return;}
  r.slice(0,400).forEach(i=>list.append(libItem(i)));
}
function libItem(i){
  const meta=el("div",{class:"meta"},
    el("span",{},i.type), i.year?el("span",{},"พ.ศ. "+i.year):null, el("span",{},i.category),
    i.issuer&&i.issuer!=="-"?el("span",{},i.issuer):null,
    badge(STMAP,i.status), i.reformStatus?badge(RSMAP,i.reformStatus):null,
    i.reformCode?el("span",{class:"chip"},i.reformCode):null);
  return el("div",{class:"item"},
    el("h4",{}, el("a",{href:"instrument.html?id="+i.id},i.title)),
    meta, i.note?el("div",{class:"note"},i.note):null);
}

/* ---------- INSTRUMENT DETAIL ---------- */
async function initInstrument(){
  const id=new URLSearchParams(location.search).get("id");
  const cat=await getJSON("data/catalog.json");
  const i=cat.items.find(x=>x.id===id);
  $("#app").append(el("a",{class:"backlink",href:"library.html"},"← กลับคลังกฎหมาย"));
  if(!i){head("ไม่พบเอกสาร");return;}
  head(i.title, i.type+(i.year?" • พ.ศ. "+i.year:""));
  const rows=[["ประเภท",i.type],["หมวด",i.category],["ผู้ออก/ผู้ตรา",i.issuer],["ปี (พ.ศ.)",i.year||"—"],
    ["ราชกิจจานุเบกษา",i.gazette||"—"],["สถานะ",(STMAP[i.status]||["—"])[0]],
    ["สถานะปฏิรูป",i.reformStatus?(RSMAP[i.reformStatus][0]+(i.reformCode?" ("+i.reformCode+")"):""):"—"]];
  const tbl=el("table",{class:"tbl"});rows.forEach(([k,v])=>tbl.append(el("tr",{},el("th",{style:"width:190px"},k),el("td",{},String(v)))));
  $("#app").append(el("div",{class:"card"},tbl));
  if(i.note)$("#app").append(el("div",{class:"callout teal"},el("h3",{},"หมายเหตุ/ข้อสังเกต"),el("div",{},i.note)));
  const links=el("div",{class:"card",style:"margin-top:14px"},el("h3",{},"ต้นฉบับและไฟล์"),
    el("p",{},[el("span",{},"ไฟล์ในคลัง: "),el("code",{},i.file)]),
    el("p",{},[el("a",{href:GAZETTE,target:"_blank",rel:"noopener"},"เปิดค้นราชกิจจานุเบกษา (ต้นทาง) ↗")," ",
      el("span",{class:"disclaimer"},"— นโยบายเก็บเฉพาะข้อความ+ลิงก์ต้นทาง ไม่ฝังไฟล์ PDF")]));
  $("#app").append(links);
  // related by reformCode
  if(i.reformCode){const rel=cat.items.filter(x=>x.reformCode===i.reformCode&&x.id!==i.id);
    if(rel.length)$("#app").append(el("div",{class:"card",style:"margin-top:14px"},
      el("h3",{},"ฉบับที่เกี่ยวข้อง (รหัส "+i.reformCode+")"),
      el("div",{},rel.map(x=>el("div",{class:"item"},el("a",{href:"instrument.html?id="+x.id},x.title),
        " ",badge(STMAP,x.status))))));}
  $("#app").append(el("p",{class:"disclaimer",style:"margin-top:14px"},
    "ธงความถูกต้อง: ฉบับที่ทีมตรวจทานกับราชกิจจาฯ แล้วจะมีหมายเหตุกำกับ; ฉบับอื่นเป็นเมทาดาทาสังเคราะห์จากชื่อไฟล์ ควรตรวจกับต้นฉบับก่อนอ้างอิงทางการ"));
}

/* ---------- TRACKER ---------- */
async function initTracker(){
  head("ทะเบียนปฏิรูปอนุบัญญัติ","แผนแม่บทการทบทวน: คงไว้ / แก้ไข / ยกเลิก / ดำเนินการแล้ว");
  let reg;try{reg=await getJSON("data/register.json")}catch(e){$("#app").append(el("p",{class:"count"},"ยังไม่มีข้อมูลทะเบียน"));return;}
  const pills=el("div",{class:"pill-row"},
    el("span",{class:"pill on","data-f":""},"ทั้งหมด"),
    ...Object.keys(RSMAP).map(k=>el("span",{class:"pill","data-f":k},RSMAP[k][0])));
  $("#app").append(pills);
  const wrap=el("div",{id:"twrap"});$("#app").append(wrap);
  function draw(f){wrap.innerHTML="";
    const groups={};reg.items.forEach(r=>{(groups[r.group]=groups[r.group]||[]).push(r)});
    Object.entries(groups).forEach(([g,rows])=>{
      const rr=rows.filter(r=>!f||r.status===f);if(!rr.length)return;
      const t=el("table",{class:"tbl"});
      t.append(el("tr",{},el("th",{style:"width:70px"},"รหัส"),el("th",{},"ชื่อ/สาระ"),el("th",{style:"width:150px"},"ฐานอำนาจ"),el("th",{style:"width:120px"},"สถานะ"),el("th",{},"หมายเหตุ")));
      rr.forEach(r=>t.append(el("tr",{},el("td",{},r.code),el("td",{html:mark(r.title)}),el("td",{},r.authority||"—"),
        el("td",{},badge(RSMAP,r.status)||r.status),el("td",{html:mark(r.note||"")}))));
      wrap.append(el("div",{class:"card",style:"padding:0;overflow:hidden;margin-bottom:14px"},
        el("div",{style:"font-weight:700;color:#fff;background:var(--navy);padding:8px 12px"},g),t));
    });
  }
  pills.addEventListener("click",e=>{const p=e.target.closest(".pill");if(!p)return;
    $$(".pill",pills).forEach(x=>x.classList.remove("on"));p.classList.add("on");draw(p.dataset.f);});
  draw("");
}
function mark(s){return esc(s).replace(/\*\*(.+?)\*\*/g,"<b>$1</b>");}

/* ---------- PROPOSALS ---------- */
async function initProposals(){
  head("ข้อเสนอการดำเนินงาน","สิ่งที่ควรดำเนินการในปัจจุบันและอนาคต (จัดกลุ่มตามความเร่งด่วน)");
  let d;try{d=await getJSON("data/proposals.json")}catch(e){$("#app").append(el("p",{class:"count"},"ยังไม่มีข้อมูล"));return;}
  (d.groups||[]).forEach(g=>{
    const card=el("div",{class:"card",style:"margin-bottom:14px"},el("h3",{},g.title));
    (g.items||[]).forEach(it=>card.append(el("div",{class:"item"},
      el("h4",{html:mark(it.title)}),
      el("div",{class:"meta"}, it.ref?el("span",{class:"chip"},it.ref):null, it.status?badge(RSMAP,it.status):null),
      it.detail?el("div",{class:"note",html:mark(it.detail)}):null)));
    $("#app").append(card);
  });
}

/* ---------- HIERARCHY ---------- */
async function initHierarchy(){
  head("ผังลำดับศักดิ์ของกฎหมาย","รัฐธรรมนูญ → พระราชบัญญัติ → ข้อบังคับ → ระเบียบ/ประกาศ พร้อมข้อสังเกตความสอดคล้อง");
  let d;try{d=await getJSON("data/hierarchy.json")}catch(e){$("#app").append(el("p",{class:"count"},"ยังไม่มีข้อมูล"));return;}
  const tree=el("div",{class:"tree"});
  (d.levels||[]).forEach((lv,idx)=>{
    tree.append(el("div",{class:"level"},el("div",{class:"lh"},lv.name),
      el("div",{}, (lv.nodes||[]).map(n=>el("div",{class:"node"},
        el("div",{html:"<b>"+esc(n.title)+"</b>"}),
        n.basis?el("small",{},"ฐานอำนาจ: "+n.basis):null,
        n.note?el("div",{class:"note",html:mark(n.note)}):null)))));
    if(idx<d.levels.length-1)tree.append(el("div",{class:"arrow"},"▼"));
  });
  $("#app").append(tree);
  (d.findings||[]).forEach(f=>$("#app").append(el("div",{class:"callout "+(f.tone||"")},
    el("h3",{},f.title),el("div",{html:mark(f.body)}))));
}

/* ---------- OPINIONS ---------- */
async function initOpinions(){
  head("ความเห็นและบันทึกทางกฎหมาย","คลังความเห็น/บันทึกตรวจสอบ (โครงสร้าง IRAC) เชื่อมกับฉบับที่เกี่ยวข้อง");
  let d;try{d=await getJSON("data/opinions.json")}catch(e){$("#app").append(el("p",{class:"count"},"ยังไม่มีข้อมูล"));return;}
  (d.items||[]).forEach(o=>$("#app").append(el("div",{class:"card",style:"margin-bottom:12px"},
    el("h3",{},o.title),
    el("div",{class:"meta"},o.ref?el("span",{class:"chip"},o.ref):null,o.date?el("span",{},o.date):null),
    o.summary?el("div",{class:"note",style:"margin-top:6px",html:mark(o.summary)}):null,
    o.file?el("p",{style:"margin:8px 0 0"},[el("span",{class:"disclaimer"},"เอกสาร: "),el("code",{},o.file)]):null)));
}

/* ---------- COMPARE ---------- */
async function initCompare(){
  head("เทียบตัวบท","เปรียบเทียบฉบับเดิมกับฉบับใหม่/ข้อเสนอ รายประเด็น");
  let idx;try{idx=await getJSON("data/compare/index.json")}catch(e){$("#app").append(el("p",{class:"count"},"ยังไม่มีชุดเทียบ"));return;}
  const sel=el("select",{id:"cmpsel"});sel.append(el("option",{value:""},"— เลือกเรื่องที่ต้องการเทียบ —"));
  idx.sets.forEach(s=>sel.append(el("option",{value:s.file},s.title)));
  $("#app").append(el("div",{class:"controls"},sel),el("div",{id:"cmpout"}));
  sel.addEventListener("change",async()=>{const f=sel.value;const out=$("#cmpout");out.innerHTML="";if(!f)return;
    const d=await getJSON("data/compare/"+f);
    out.append(el("div",{class:"callout"},el("h3",{},d.title),el("div",{html:mark(d.summary||"")})));
    const c=el("div",{class:"cmp"},
      el("div",{class:"col old"},el("div",{class:"colh"},d.oldLabel||"ฉบับเดิม")),
      el("div",{class:"col new"},el("div",{class:"colh"},d.newLabel||"ฉบับใหม่/ข้อเสนอ")));
    (d.rows||[]).forEach(r=>{
      c.children[0].append(el("div",{class:"row",style:"padding:9px 0",html:mark(r.old||"—")}));
      c.children[1].append(el("div",{class:"row",style:"padding:9px 0",html:mark(r.new||"—")}));});
    out.append(c);});
}

/* dispatch */
document.addEventListener("DOMContentLoaded",()=>{
  chrome();
  const p=document.body.dataset.page;
  const map={"index.html":initDashboard,"library.html":initLibrary,"instrument.html":initInstrument,
    "tracker.html":initTracker,"proposals.html":initProposals,"hierarchy.html":initHierarchy,
    "opinions.html":initOpinions,"compare.html":initCompare};
  (map[p]||initDashboard)().catch(e=>{$("#app").append(el("div",{class:"callout red"},el("h3",{},"เกิดข้อผิดพลาด"),el("div",{},String(e.message||e))));});
});
