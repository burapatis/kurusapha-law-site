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
const SRCLABEL={pdf:"สกัดจาก PDF (ยังไม่ตรวจทาน)",docx:"จากเอกสารโครงการ",txt:"จากไฟล์ข้อความ",need_ocr:"ต้อง OCR (ยังไม่มีข้อความ)",none:"—"};
const GAZETTE="https://ratchakitcha.soc.go.th/";
const $=(s,r=document)=>r.querySelector(s);
const $$=(s,r=document)=>[...r.querySelectorAll(s)];
function el(tag,attrs={},...kids){const e=document.createElement(tag);
  for(const k in attrs){if(k==="class")e.className=attrs[k];else if(k==="html")e.innerHTML=attrs[k];else e.setAttribute(k,attrs[k]);}
  kids.flat().forEach(k=>e.append(k&&k.nodeType?k:document.createTextNode(k==null?"":k)));return e;}
async function getJSON(p){const r=await fetch(p);if(!r.ok)throw new Error(p+" "+r.status);return r.json();}
async function getText(p){const r=await fetch(p);if(!r.ok)throw new Error(p+" "+r.status);return r.text();}
function badge(map,key){if(!key||!map[key])return null;const[t,c]=map[key];return el("span",{class:"badge "+c},t);}
function esc(s){return(s==null?"":String(s)).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));}
function mark(s){return esc(s).replace(/\*\*(.+?)\*\*/g,"<b>$1</b>");}

function chrome(){
  const page=document.body.dataset.page||"index.html";
  document.body.prepend(el("header",{class:"site"},
    el("div",{class:"wrap"},
      el("a",{class:"brand",href:"index.html"}, el("span",{class:"dot"}), "คลังกฎหมายคุรุสภา"),
      el("nav",{}, NAV.map(([h,t])=>el("a",{href:h,class:page===h?"active":""},t))))));
  document.body.append(el("footer",{class:"site"},
    el("div",{class:"wrap"},"ระบบภายในทีมยกร่าง • ฐานข้อมูลคอร์ปัสคุรุสภา • โครงการปรับปรุงอนุบัญญัติคุรุสภา • v1.1 (เฟส 1b — ค้นหาเต็มข้อความ)")));
}
function head(title,sub){const h=$("#pagehead");if(h){h.append(el("h1",{},title));if(sub)h.append(el("p",{},sub));}}

/* ---------- DASHBOARD ---------- */
async function initDashboard(){
  head("ภาพรวมระบบ","คลังกฎหมายและเครื่องมือบริหารการปฏิรูปอนุบัญญัติคุรุสภา");
  const cat=await getJSON("data/catalog.json");
  let reg={items:[]},prop={groups:[]};
  try{reg=await getJSON("data/register.json")}catch(e){}
  try{prop=await getJSON("data/proposals.json")}catch(e){}
  const items=cat.items;
  const inforce=items.filter(i=>i.status==="in_force").length;
  const deliver=items.filter(i=>i.isDeliverable).length;
  const ft=cat.meta.fulltextDocs||items.filter(i=>i.hasText).length;
  $("#app").append(el("div",{class:"grid g4"},
    stat(items.length,"เอกสารในคลัง","คอร์ปัสคุรุสภา"),
    stat(inforce,"ฉบับใช้บังคับ","สถานะ in force"),
    stat(ft,"ค้นเต็มข้อความได้","มีข้อความสกัดแล้ว"),
    stat(reg.items.length||"—","รายการในทะเบียนปฏิรูป","คงไว้/แก้ไข/ยกเลิก")));
  const rs={};(reg.items||[]).forEach(r=>{rs[r.status]=(rs[r.status]||0)+1});
  const sumCard=el("div",{class:"card"}, el("h3",{},"สรุปสถานะการปฏิรูป (ทะเบียน)"),
    el("div",{class:"pill-row"}, Object.keys(RSMAP).map(k=>rs[k]?el("span",{class:"chip"},[badge(RSMAP,k)," ",String(rs[k])+" รายการ"]):null).filter(Boolean)),
    el("a",{href:"tracker.html"},"ดูทะเบียนปฏิรูปทั้งหมด →"));
  const urg=(prop.groups||[]).find(g=>/เร่งด่วน/.test(g.title));
  const urgCard=el("div",{class:"card"}, el("h3",{},"งานเร่งด่วน"),
    urg?el("ul",{style:"margin:6px 0 0;padding-left:18px"},(urg.items||[]).slice(0,5).map(it=>el("li",{style:"margin-bottom:4px",html:mark(it.title)})))
        :el("p",{class:"count"},"—"),
    el("a",{href:"proposals.html"},"ดูข้อเสนอทั้งหมด →"));
  $("#app").append(el("div",{class:"grid g2",style:"margin-top:14px"},sumCard,urgCard));
  const byCat={};items.forEach(i=>{byCat[i.category]=(byCat[i.category]||0)+1});
  $("#app").append(el("div",{class:"card",style:"margin-top:14px"},el("h3",{},"จำนวนเอกสารแยกหมวด"),
    el("div",{}, Object.entries(byCat).sort((a,b)=>b[1]-a[1]).map(([c,n])=>
      el("a",{class:"chip",href:"library.html?cat="+encodeURIComponent(c)},c+" ("+n+")")))));
  $("#app").append(el("p",{class:"disclaimer",style:"margin-top:16px"},
    "ค้นหาเต็มข้อความครอบคลุม "+ft+" ฉบับที่สกัดข้อความได้ (อีกส่วนเป็น PDF ฟอนต์เก่า/สแกน รอทำ OCR); เมทาดาทาสังเคราะห์จากชื่อไฟล์ ตรวจกับต้นฉบับก่อนอ้างอิงทางการ"));
}
function stat(n,l,s){return el("div",{class:"card stat"},el("span",{class:"n"},String(n)),el("span",{class:"l"},l),s?el("span",{class:"s"},s):null);}

/* ---------- LIBRARY ---------- */
let LIB=[], FTMAP=null, FTLOADING=false;
async function initLibrary(){
  head("คลังกฎหมาย","ค้นหาและกรองเอกสารกฎหมายในคอร์ปัสคุรุสภา");
  const cat=await getJSON("data/catalog.json");LIB=cat.items;
  const q=new URLSearchParams(location.search);
  const cats=cat.meta.categories, types=[...new Set(LIB.map(i=>i.type))].sort();
  const bar=el("div",{class:"controls"},
    el("input",{type:"search",id:"q",placeholder:"ค้นหาชื่อกฎหมาย / คำสำคัญ / ปี …"}),
    selOf("cat","— ทุกหมวด —",cats),
    selOf("type","— ทุกประเภท —",types),
    selOf("status","— ทุกสถานะ —",Object.keys(STMAP).map(k=>[k,STMAP[k][0]])));
  const ftlabel=el("label",{style:"display:flex;align-items:center;gap:6px;font-size:15px;color:var(--muted)"},
    el("input",{type:"checkbox",id:"ft"}),"ค้นในเนื้อความ (เต็มข้อความ)");
  bar.append(ftlabel, el("span",{class:"count",id:"cnt"}));
  $("#app").append(bar,el("div",{id:"list"}));
  if(q.get("cat"))$("#cat").value=q.get("cat");
  if(q.get("status"))$("#status").value=q.get("status");
  ["q","cat","type","status"].forEach(id=>$("#"+id).addEventListener("input",renderLib));
  $("#ft").addEventListener("change",async()=>{
    if($("#ft").checked && !FTMAP){await loadFT();}
    renderLib();
  });
  renderLib();
}
async function loadFT(){
  if(FTMAP||FTLOADING)return; FTLOADING=true;
  const c=$("#cnt"); if(c)c.textContent="กำลังโหลดดัชนีเต็มข้อความ…";
  try{const d=await getJSON("data/search-index.json");FTMAP={};d.items.forEach(x=>FTMAP[x.id]=x.blob);}
  catch(e){FTMAP={};}
  FTLOADING=false;
}
function selOf(id,ph,opts){const s=el("select",{id});s.append(el("option",{value:""},ph));
  opts.forEach(o=>{const[v,t]=Array.isArray(o)?o:[o,o];s.append(el("option",{value:v},t))});return s;}
function snippet(blob,tok){const i=blob.toLowerCase().indexOf(tok);if(i<0)return null;
  const a=Math.max(0,i-55),b=Math.min(blob.length,i+tok.length+75);
  let s=(a>0?"…":"")+blob.slice(a,b)+(b<blob.length?"…":"");
  return esc(s).replace(new RegExp("("+tok.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")+")","ig"),"<mark>$1</mark>");}
function renderLib(){
  const q=$("#q").value.trim().toLowerCase(),c=$("#cat").value,t=$("#type").value,st=$("#status").value,ft=$("#ft").checked&&FTMAP;
  const toks=q.split(/\s+/).filter(Boolean);
  let out=[];
  LIB.forEach(i=>{
    if(c&&i.category!==c)return; if(t&&i.type!==t)return; if(st&&i.status!==st)return;
    let snip=null;
    if(toks.length){
      const hay=(i.title+" "+(i.issuer||"")+" "+(i.note||"")+" "+(i.year||"")+" "+(i.reformCode||"")).toLowerCase();
      let ok=toks.every(k=>hay.includes(k));
      if(!ok && ft && FTMAP[i.id]){const blob=FTMAP[i.id].toLowerCase();
        ok=toks.every(k=>hay.includes(k)||blob.includes(k));
        if(ok){const s=snippet(FTMAP[i.id],toks[0]);if(s)snip=s;}}
      if(!ok)return;
    }
    out.push([i,snip]);
  });
  $("#cnt").textContent="พบ "+out.length+" ฉบับ"+(ft?" (รวมค้นเนื้อความ)":"");
  const list=$("#list");list.innerHTML="";
  if(!out.length){list.append(el("p",{class:"count"},"ไม่พบเอกสารที่ตรงเงื่อนไข"));return;}
  out.slice(0,400).forEach(([i,snip])=>list.append(libItem(i,snip)));
}
function libItem(i,snip){
  const meta=el("div",{class:"meta"},
    el("span",{},i.type), i.year?el("span",{},"พ.ศ. "+i.year):null, el("span",{},i.category),
    i.issuer&&i.issuer!=="-"?el("span",{},i.issuer):null,
    badge(STMAP,i.status), i.reformStatus?badge(RSMAP,i.reformStatus):null,
    i.reformCode?el("span",{class:"chip"},i.reformCode):null,
    i.hasText?el("span",{class:"chip"},"มีข้อความ"):null);
  const node=el("div",{class:"item"},
    el("h4",{}, el("a",{href:"instrument.html?id="+i.id},i.title)),
    meta, i.note?el("div",{class:"note"},i.note):null);
  if(snip)node.append(el("div",{class:"note",html:"…พบในเนื้อความ: "+snip}));
  return node;
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
    ["สถานะปฏิรูป",i.reformStatus?(RSMAP[i.reformStatus][0]+(i.reformCode?" ("+i.reformCode+")"):""):"—"],
    ["แหล่งข้อความ",SRCLABEL[i.textSource]||"—"]];
  const tbl=el("table",{class:"tbl"});rows.forEach(([k,v])=>tbl.append(el("tr",{},el("th",{style:"width:190px"},k),el("td",{},String(v)))));
  $("#app").append(el("div",{class:"card"},tbl));
  if(i.note)$("#app").append(el("div",{class:"callout teal"},el("h3",{},"หมายเหตุ/ข้อสังเกต"),el("div",{},i.note)));
  $("#app").append(el("div",{class:"card",style:"margin-top:14px"},el("h3",{},"ต้นฉบับและไฟล์"),
    el("p",{},[el("span",{},"ไฟล์ในคลัง: "),el("code",{},i.file)]),
    el("p",{},[el("a",{href:GAZETTE,target:"_blank",rel:"noopener"},"เปิดค้นราชกิจจานุเบกษา (ต้นทาง) ↗")," ",
      el("span",{class:"disclaimer"},"— นโยบายเก็บเฉพาะข้อความ+ลิงก์ต้นทาง ไม่ฝังไฟล์ PDF")])));
  // extracted full text
  if(i.hasText){
    const box=el("div",{class:"card",style:"margin-top:14px"},
      el("h3",{},"ข้อความที่สกัดได้"),
      el("p",{class:"disclaimer"}, i.textSource==="pdf"?"สกัดอัตโนมัติจาก PDF — ยังไม่ตรวจทานกับต้นฉบับ ควรใช้ประกอบการค้นหา มิใช่อ้างอิงทางการ":"จากเอกสาร/ไฟล์ข้อความของโครงการ"),
      el("div",{id:"ftext",class:"count"},"กำลังโหลดข้อความ…"));
    $("#app").append(box);
    getText("data/text/"+i.id+".txt").then(t=>{
      const pre=el("div",{style:"white-space:pre-wrap;font-size:15px;line-height:1.6;max-height:520px;overflow:auto;border-top:1px solid var(--line);padding-top:10px;margin-top:8px"});
      pre.textContent=t.slice(0,60000)+(t.length>60000?"\n\n…(ตัดแสดงบางส่วน)":"");
      const w=$("#ftext");w.textContent="";w.classList.remove("count");w.append(pre);
    }).catch(()=>{$("#ftext").textContent="ไม่พบไฟล์ข้อความ";});
  } else {
    $("#app").append(el("div",{class:"callout"},el("h3",{},"ยังไม่มีข้อความสกัด"),
      el("div",{},"ไฟล์นี้เป็น PDF ฟอนต์เก่า/สแกน หรือรูปภาพ — รอทำ OCR ในเฟสถัดไป (ค้นได้จากชื่อ/เมทาดาทา)")));
  }
  if(i.reformCode){const rel=cat.items.filter(x=>x.reformCode===i.reformCode&&x.id!==i.id);
    if(rel.length)$("#app").append(el("div",{class:"card",style:"margin-top:14px"},
      el("h3",{},"ฉบับที่เกี่ยวข้อง (รหัส "+i.reformCode+")"),
      el("div",{},rel.map(x=>el("div",{class:"item"},el("a",{href:"instrument.html?id="+x.id},x.title)," ",badge(STMAP,x.status))))));}
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

document.addEventListener("DOMContentLoaded",()=>{
  chrome();
  const p=document.body.dataset.page;
  const map={"index.html":initDashboard,"library.html":initLibrary,"instrument.html":initInstrument,
    "tracker.html":initTracker,"proposals.html":initProposals,"hierarchy.html":initHierarchy,
    "opinions.html":initOpinions,"compare.html":initCompare};
  (map[p]||initDashboard)().catch(e=>{$("#app").append(el("div",{class:"callout red"},el("h3",{},"เกิดข้อผิดพลาด"),el("div",{},String(e.message||e))));});
});
