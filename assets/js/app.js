/* คลังกฎหมายและข้อเสนอปฏิรูปคุรุสภา — public research interface */
"use strict";

const NAV = [
  ["index.html", "หน้าแรก"], ["library.html", "คลังกฎหมาย"],
  ["tracker.html", "ทะเบียนทบทวน"], ["compare.html", "เทียบตัวบท"],
  ["hierarchy.html", "ฐานอำนาจ"], ["opinions.html", "ประเด็นกฎหมาย"],
  ["proposals.html", "ข้อเสนอดำเนินงาน"], ["methodology.html", "วิธีจัดทำ"]
];
const RSMAP = {
  keep: ["เสนอคงไว้", "b-keep"], amend: ["เสนอแก้ไข", "b-amend"],
  repeal: ["เสนอทบทวน/ยกเลิก", "b-repeal"], verify: ["ต้องตรวจสอบ", "b-verify"],
  done: ["ดำเนินการแล้ว", "b-done"]
};
const STMAP = {
  in_force: ["ใช้บังคับ (ตรวจแล้ว)", "b-inforce"], amended: ["มีแก้ไข (ตรวจแล้ว)", "b-amended"],
  superseded: ["ถูกแทนที่แล้ว (ตรวจแล้ว)", "b-superseded"],
  repealed: ["ยกเลิกแล้ว (ตรวจแล้ว)", "b-repealed"], reference: ["เอกสารอ้างอิง", "b-reference"],
  draft: ["ร่าง", "b-draft"], unverified: ["ยังไม่ตรวจยืนยัน", "b-unverified"]
};
const VERIFYMAP = {
  reviewed: ["ตรวจทานแล้ว", "b-inforce"], partial: ["ตรวจบางส่วน", "b-amended"],
  unverified: ["ยังไม่ตรวจยืนยัน", "b-unverified"]
};
const EVIDENCEMAP = {
  official_online: ["พบแหล่งทางการออนไลน์", "b-inforce"],
  local_reviewed: ["ตรวจจากสำเนาในคลัง", "b-amended"],
  local_file: ["มีสำเนาในคลัง", "b-reference"]
};
const REVIEWSOURCEMAP = {
  local_original: "สำเนาในคลัง", official_gazette: "ราชกิจจานุเบกษา",
  official_agency: "หน่วยงานทางการ", official_index: "หน้ารวมของหน่วยงานทางการ"
};
const SRCLABEL = {
  pdf: "สกัดอัตโนมัติจาก PDF", ocr: "OCR อัตโนมัติ", docx: "สกัดจาก DOCX",
  txt: "ไฟล์ข้อความ", companion: "ไฟล์ข้อความคู่กับต้นฉบับ", need_ocr: "รอ OCR", none: "ไม่มีข้อความ"
};
const GAZETTE = "https://ratchakitcha.soc.go.th/";
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([key, value]) => {
    if (value === null || value === undefined || value === false) return;
    if (key === "class") node.className = value;
    else if (key === "html") node.innerHTML = value;
    else if (key === "text") node.textContent = value;
    else if (key === "checked") node.checked = Boolean(value);
    else node.setAttribute(key, value === true ? "" : String(value));
  });
  children.flat(Infinity).forEach(child => {
    if (child === null || child === undefined || child === false) return;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  });
  return node;
}

async function getJSON(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`โหลด ${path} ไม่สำเร็จ (${response.status})`);
  return response.json();
}
async function getText(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`โหลด ${path} ไม่สำเร็จ (${response.status})`);
  return response.text();
}
function esc(value) {
  return (value == null ? "" : String(value)).replace(/[&<>]/g, char => ({"&": "&amp;", "<": "&lt;", ">": "&gt;"})[char]);
}
function mark(value) { return esc(value).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>"); }
function badge(map, key) {
  if (!key || !map[key]) return null;
  const [text, className] = map[key];
  return el("span", {class: `badge ${className}`}, text);
}
function stat(number, label, note) {
  return el("div", {class: "card stat"},
    el("span", {class: "n"}, String(number)), el("span", {class: "l"}, label),
    note ? el("span", {class: "s"}, note) : null);
}
function empty(message) { return el("p", {class: "empty-state"}, message); }
function thaiDate(isoDate) {
  if (!isoDate || !/^\d{4}-\d{2}-\d{2}$/.test(isoDate)) return "ยังไม่มีข้อมูล";
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Intl.DateTimeFormat("th-TH", {day: "numeric", month: "long", year: "numeric", timeZone: "UTC"})
    .format(new Date(Date.UTC(year, month - 1, day)));
}
function thaiRecordedDate(value) {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return value || "ยังไม่มีข้อมูล";
  let [year, month, day] = value.split("-").map(Number);
  if (year >= 2400) year -= 543;
  return thaiDate(`${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`);
}
function buildCitation(item) {
  const source = (item.sources || [])[0] || {corpus: item.sourceCorpus, path: item.file, sha256: ""};
  const parts = [item.title];
  if (item.gazette) parts.push(`ราชกิจจานุเบกษา ${item.gazette}`);
  parts.push(`สำเนาในคลัง “${source.corpus || "ไม่ระบุ"}/${source.path || item.file}”`);
  if (item.verifiedAt) parts.push(`ตรวจไฟล์เมื่อ ${thaiRecordedDate(item.verifiedAt)}`);
  if (source.sha256) parts.push(`SHA-256: ${source.sha256}`);
  if (!item.officialUrl) parts.push("ยังไม่พบลิงก์ต้นฉบับทางการออนไลน์");
  return `${parts.join(", ")}.`;
}
async function copyText(text, button, field) {
  let copied = false;
  try {
    await navigator.clipboard.writeText(text);
    copied = true;
  } catch (_) {}
  if (!copied && field) {
    field.focus(); field.select();
    copied = document.execCommand("copy");
  }
  const original = button.textContent;
  button.textContent = copied ? "คัดลอกแล้ว" : "เลือกข้อความแล้ว — กด Ctrl+C";
  setTimeout(() => { button.textContent = original; }, 1800);
}
async function hasLocalArchive() {
  if (!["localhost", "127.0.0.1", "::1"].includes(location.hostname)) return false;
  try {
    const response = await fetch("__local_source__/__health__", {cache: "no-store"});
    return response.ok;
  } catch (_) { return false; }
}

function chrome() {
  const page = document.body.dataset.page || "index.html";
  const nav = el("nav", {id: "site-nav", "aria-label": "เมนูหลัก"},
    NAV.map(([href, text]) => el("a", {
      href, class: page === href ? "active" : "", "aria-current": page === href ? "page" : null
    }, text)));
  const toggle = el("button", {
    class: "nav-toggle", type: "button", "aria-controls": "site-nav", "aria-expanded": "false"
  }, el("span", {"aria-hidden": "true"}, "☰"), el("span", {class: "nav-toggle-label"}, "เมนู"));
  toggle.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(open));
  });
  nav.addEventListener("click", event => {
    if (event.target.closest("a")) {
      nav.classList.remove("open");
      toggle.setAttribute("aria-expanded", "false");
    }
  });
  document.body.prepend(
    el("a", {class: "skip-link", href: "#main-content"}, "ข้ามไปยังเนื้อหา"),
    el("header", {class: "site"}, el("div", {class: "wrap header-inner"},
      el("a", {class: "brand", href: "index.html", "aria-label": "คลังกฎหมายคุรุสภา หน้าแรก"},
        el("span", {class: "dot", "aria-hidden": "true"}), "คลังกฎหมายคุรุสภา"),
      toggle, nav))
  );
  const main = $("main");
  if (main) {
    main.id = "main-content";
    main.setAttribute("tabindex", "-1");
  }
  document.body.append(el("footer", {class: "site"}, el("div", {class: "wrap"},
    el("p", {}, "ฐานข้อมูลเพื่อการศึกษาและสนับสนุนการทบทวนกฎหมาย • รุ่น 2.1"),
    el("p", {}, "ข้อมูลสถานะที่ยังไม่ตรวจยืนยันไม่ควรใช้แทนต้นฉบับทางการหรือความเห็นของผู้มีอำนาจ"),
    el("p", {}, el("a", {href: "methodology.html"}, "วิธีจัดทำและข้อจำกัด"), " · ",
      el("a", {href: GAZETTE, target: "_blank", rel: "noopener"}, "ราชกิจจานุเบกษา ↗")))));
}
function head(title, subtitle) {
  const area = $("#pagehead");
  if (!area) return;
  area.append(el("h1", {}, title));
  if (subtitle) area.append(el("p", {}, subtitle));
}

/* Dashboard */
async function initDashboard() {
  head("ภาพรวมคลังกฎหมาย", "ค้นคว้า ติดตาม และตรวจสอบข้อเสนอปรับปรุงกฎหมายที่เกี่ยวกับคุรุสภาและวิชาชีพทางการศึกษา");
  const [catalog, register, proposals] = await Promise.all([
    getJSON("data/catalog.json"), getJSON("data/register.json").catch(() => ({items: []})),
    getJSON("data/proposals.json").catch(() => ({groups: []}))
  ]);
  const items = catalog.items || [];
  const reviewed = items.filter(item => item.verificationStatus === "reviewed").length;
  const unverified = items.filter(item => item.verificationStatus !== "reviewed").length;
  const fulltext = catalog.meta.fulltextDocs || items.filter(item => item.hasText).length;
  $("#app").append(
    el("div", {class: "notice"}, el("strong", {}, "อ่านสถานะอย่างระมัดระวัง: "),
      "ระบบไม่อนุมานว่าเอกสารยังใช้บังคับจากชื่อไฟล์ รายการที่ไม่มีหลักฐานยืนยันจะแสดงว่า “ยังไม่ตรวจยืนยัน”"),
    el("div", {class: "grid g4"},
      stat(items.length, "รายการหลังรวมไฟล์ซ้ำ", "จากคลังกฎหมาย 3 ชุด"),
      stat(reviewed, "ตรวจทานสถานะแล้ว", "มีขอบเขตและหลักฐานกำกับ"),
      stat(unverified, "รอตรวจยืนยัน", "ต้องเทียบต้นฉบับและฉบับแก้ไข"),
      stat(fulltext, "ค้นเนื้อความได้", "ข้อความสกัดอาจคลาดเคลื่อน"))
  );

  const reformCounts = {};
  (register.items || []).forEach(item => { reformCounts[item.status] = (reformCounts[item.status] || 0) + 1; });
  const summary = el("div", {class: "card"}, el("h2", {}, "ทะเบียนประเด็นทบทวน"),
    el("div", {class: "pill-row"}, Object.keys(RSMAP).map(key => reformCounts[key]
      ? el("span", {class: "chip"}, badge(RSMAP, key), ` ${reformCounts[key]} รายการ`) : null)),
    el("a", {class: "text-link", href: "tracker.html"}, "ดูทะเบียนทั้งหมด →"));
  const urgentGroup = (proposals.groups || []).find(group => /เร่งด่วน|ลำดับ 1/.test(group.title)) || (proposals.groups || [])[0];
  const urgent = el("div", {class: "card"}, el("h2", {}, "ประเด็นที่ควรตรวจสอบก่อน"),
    urgentGroup ? el("ul", {class: "compact-list"}, (urgentGroup.items || []).slice(0, 5)
      .map(item => el("li", {html: mark(item.title)}))) : empty("ยังไม่มีข้อมูล"),
    el("a", {class: "text-link", href: "proposals.html"}, "ดูข้อเสนอพร้อมเหตุผล →"));
  $("#app").append(el("div", {class: "grid g2 section-gap"}, summary, urgent));

  const corpusCounts = {};
  items.forEach(item => (item.sourceCorpora || [item.sourceCorpus || "ไม่ระบุ"]).forEach(corpus => {
    corpusCounts[corpus] = (corpusCounts[corpus] || 0) + 1;
  }));
  $("#app").append(el("section", {class: "card section-gap", "aria-labelledby": "scope-title"},
    el("h2", {id: "scope-title"}, "ขอบเขตข้อมูล"),
    el("div", {class: "scope-grid"}, Object.entries(corpusCounts).sort((a, b) => b[1] - a[1])
      .map(([name, count]) => el("a", {class: "scope-item", href: `library.html?corpus=${encodeURIComponent(name)}`},
        el("strong", {}, count), el("span", {}, name)))),
    el("p", {class: "fine-print"}, `ปรับปรุงข้อมูลล่าสุด ${catalog.meta.generated || "—"} • ตัดสำเนาไฟล์ซ้ำด้วย SHA-256`)));
}

/* Library */
let LIB = [], FTMAP = null, FTLOADING = false;
function labeledControl(labelText, control) {
  return el("label", {class: "field"}, el("span", {class: "field-label"}, labelText), control);
}
function selectOf(id, options, ariaLabel) {
  const select = el("select", {id, "aria-label": ariaLabel});
  options.forEach(option => {
    const [value, text] = Array.isArray(option) ? option : [option, option];
    select.append(el("option", {value}, text));
  });
  return select;
}
async function initLibrary() {
  head("คลังกฎหมาย", "ค้นจากชื่อ เมทาดาทา หรือเนื้อความที่สกัด และกรองตามสถานะที่ตรวจยืนยันแล้ว");
  const catalog = await getJSON("data/catalog.json");
  LIB = catalog.items || [];
  const params = new URLSearchParams(location.search);
  const categories = [...new Set(LIB.map(item => item.category))].sort();
  const types = [...new Set(LIB.map(item => item.type))].sort();
  const corpora = [...new Set(LIB.flatMap(item => item.sourceCorpora || [item.sourceCorpus]).filter(Boolean))].sort();
  const controls = el("div", {class: "controls", role: "search"},
    labeledControl("คำค้น", el("input", {type: "search", id: "q", placeholder: "ชื่อกฎหมาย คำสำคัญ หรือปี", autocomplete: "off"})),
    labeledControl("คลังต้นทาง", selectOf("corpus", [["", "ทุกคลัง"], ...corpora], "คลังต้นทาง")),
    labeledControl("หมวด", selectOf("cat", [["", "ทุกหมวด"], ...categories], "หมวด")),
    labeledControl("ประเภท", selectOf("type", [["", "ทุกประเภท"], ...types], "ประเภท")),
    labeledControl("สถานะ", selectOf("status", [["", "ทุกสถานะ"], ...Object.entries(STMAP).map(([key, value]) => [key, value[0]])], "สถานะ")),
    labeledControl("หลักฐาน", selectOf("evidence", [["", "ทุกระดับหลักฐาน"], ...Object.entries(EVIDENCEMAP).map(([key, value]) => [key, value[0]])], "ระดับหลักฐาน")),
    el("label", {class: "check-field"}, el("input", {type: "checkbox", id: "ft"}), "ค้นในเนื้อความ"),
    el("button", {type: "button", class: "button secondary", id: "clear-filters"}, "ล้างตัวกรอง"),
    el("span", {class: "result-count", id: "cnt", "aria-live": "polite"})
  );
  $("#app").append(
    el("div", {class: "notice subtle"}, "สถานะ “ยังไม่ตรวจยืนยัน” หมายถึงระบบยังไม่ได้ตรวจต้นฉบับทางการ ฉบับแก้ไข และบทเลิกกฎหมายครบถ้วน"),
    controls, el("div", {id: "list"})
  );
  ["corpus", "cat", "type", "status", "evidence"].forEach(id => { if (params.get(id)) $(`#${id}`).value = params.get(id); });
  ["q", "corpus", "cat", "type", "status", "evidence"].forEach(id => $(`#${id}`).addEventListener("input", renderLibrary));
  $("#ft").addEventListener("change", async () => {
    if ($("#ft").checked && !FTMAP) await loadFulltext();
    renderLibrary();
  });
  $("#clear-filters").addEventListener("click", () => {
    ["q", "corpus", "cat", "type", "status", "evidence"].forEach(id => { $(`#${id}`).value = ""; });
    $("#ft").checked = false;
    history.replaceState(null, "", "library.html");
    renderLibrary();
    $("#q").focus();
  });
  renderLibrary();
}
async function loadFulltext() {
  if (FTMAP || FTLOADING) return;
  FTLOADING = true;
  $("#cnt").textContent = "กำลังโหลดดัชนี…";
  try {
    const data = await getJSON("data/search-index.json");
    FTMAP = Object.fromEntries((data.items || []).map(item => [item.id, item.blob]));
  } catch (_) { FTMAP = {}; }
  FTLOADING = false;
}
function snippet(blob, token) {
  const index = blob.toLowerCase().indexOf(token);
  if (index < 0) return null;
  const start = Math.max(0, index - 65), end = Math.min(blob.length, index + token.length + 95);
  const sample = `${start ? "…" : ""}${blob.slice(start, end)}${end < blob.length ? "…" : ""}`;
  const safeToken = token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return esc(sample).replace(new RegExp(`(${safeToken})`, "ig"), "<mark>$1</mark>");
}
function renderLibrary() {
  const query = $("#q").value.trim().toLowerCase();
  const corpus = $("#corpus").value, category = $("#cat").value, type = $("#type").value, status = $("#status").value;
  const evidence = $("#evidence").value;
  const useFulltext = $("#ft").checked && FTMAP;
  const tokens = query.split(/\s+/).filter(Boolean);
  const output = [];
  LIB.forEach(item => {
    if (corpus && !(item.sourceCorpora || [item.sourceCorpus]).includes(corpus)) return;
    if (category && item.category !== category) return;
    if (type && item.type !== type) return;
    if (status && item.status !== status) return;
    if (evidence && item.evidenceLevel !== evidence) return;
    const relationText = (item.legalRelations || []).flatMap(relation => [relation.label, relation.basis]);
    const reviewSourceText = (item.reviewSources || []).map(source => source.label);
    const haystack = [item.title, item.issuer, item.note, item.year, item.reformCode, item.sourceCorpus,
      item.statusBasis, item.reviewScope, ...relationText, ...reviewSourceText].join(" ").toLowerCase();
    let found = tokens.every(token => haystack.includes(token));
    let sample = null;
    if (!found && useFulltext && FTMAP[item.id]) {
      const blob = FTMAP[item.id].toLowerCase();
      found = tokens.every(token => haystack.includes(token) || blob.includes(token));
      if (found && tokens.length) sample = snippet(FTMAP[item.id], tokens[0]);
    }
    if (!tokens.length || found) output.push([item, sample]);
  });
  $("#cnt").textContent = `พบ ${output.length} รายการ${useFulltext ? " (รวมเนื้อความ)" : ""}`;
  const list = $("#list");
  list.replaceChildren();
  if (!output.length) { list.append(empty("ไม่พบเอกสารที่ตรงกับเงื่อนไข ลองลดคำค้นหรือล้างตัวกรอง")); return; }
  output.slice(0, 500).forEach(([item, sample]) => list.append(libraryItem(item, sample)));
}
function libraryItem(item, sample) {
  const metadata = el("div", {class: "meta"},
    badge(STMAP, item.status), badge(EVIDENCEMAP, item.evidenceLevel || "local_file"), el("span", {}, item.type), item.year ? el("span", {}, `พ.ศ. ${item.year}`) : null,
    el("span", {}, item.sourceCorpus || item.category), item.reformStatus ? badge(RSMAP, item.reformStatus) : null,
    item.hasText ? el("span", {class: "chip"}, "มีข้อความ") : null);
  return el("article", {class: "item"},
    el("h2", {}, el("a", {href: `instrument.html?id=${encodeURIComponent(item.id)}`}, item.title)), metadata,
    item.note ? el("p", {class: "note"}, item.note) : null,
    sample ? el("p", {class: "search-snippet", html: `พบในเนื้อความ: ${sample}`}) : null);
}

/* Instrument detail */
async function initInstrument() {
  const id = new URLSearchParams(location.search).get("id");
  const catalog = await getJSON("data/catalog.json");
  const item = (catalog.items || []).find(candidate => candidate.id === id);
  $("#app").append(el("a", {class: "backlink", href: "library.html"}, "← กลับคลังกฎหมาย"));
  if (!item) { head("ไม่พบเอกสาร", "ตรวจสอบลิงก์หรือกลับไปค้นจากคลังกฎหมาย"); return; }
  document.title = `${item.title} | คลังกฎหมายคุรุสภา`;
  head(item.title, `${item.type}${item.year ? ` • พ.ศ. ${item.year}` : ""}`);
  const localArchive = await hasLocalArchive();
  const rows = [
    ["สถานะทางกฎหมาย", badge(STMAP, item.status)],
    ["การตรวจยืนยัน", badge(VERIFYMAP, item.verificationStatus)],
    ["หลักฐานที่มี", badge(EVIDENCEMAP, item.evidenceLevel || "local_file")],
    ["เหตุผลของสถานะ", item.statusBasis || "ยังไม่มีข้อมูล"],
    ["วันเริ่มใช้บังคับ", thaiDate(item.effectiveDate)],
    ["ขอบเขตที่ตรวจ", item.reviewScope || "ยังไม่ได้กำหนดขอบเขตการตรวจ"],
    ["ตรวจเมื่อ/โดย", [item.verifiedAt ? thaiRecordedDate(item.verifiedAt) : null, item.verifiedBy].filter(Boolean).join(" • ") || "ยังไม่ตรวจยืนยัน"],
    ["ประเภท", item.type], ["หมวด", item.category], ["ผู้ออก/ผู้ตรา", item.issuer || "ไม่ระบุ"],
    ["ปี (พ.ศ.)", item.year || "ไม่ระบุ"], ["ราชกิจจานุเบกษา", item.gazette || "ยังไม่มีข้อมูลอ้างอิง"],
    ["สถานะข้อเสนอ", item.reformStatus ? `${RSMAP[item.reformStatus][0]}${item.reformCode ? ` (${item.reformCode})` : ""}` : "ไม่มีข้อเสนอผูกกับรายการนี้"],
    ["แหล่งข้อความ", SRCLABEL[item.textSource] || "ยังไม่ระบุ"]
  ];
  const table = el("table", {class: "detail-table"});
  rows.forEach(([label, value]) => table.append(el("tr", {}, el("th", {scope: "row"}, label), el("td", {}, value))));
  $("#app").append(el("div", {class: "card"}, table));
  if (item.verificationStatus !== "reviewed") {
    $("#app").append(el("div", {class: "callout warning", role: "note"}, el("h2", {}, "ยังไม่ควรอ้างสถานะนี้เป็นข้อยุติ"),
      el("p", {}, "ควรตรวจต้นฉบับราชกิจจานุเบกษา กฎหมายแก้ไขเพิ่มเติม บทเฉพาะกาล และกฎหมายที่ออกภายหลังก่อนนำไปใช้")));
  }
  if (item.note) $("#app").append(el("div", {class: "callout teal"}, el("h2", {}, "หมายเหตุการตรวจ"), el("p", {}, item.note)));

  if ((item.legalRelations || []).length) {
    const relations = el("section", {class: "card section-gap"}, el("h2", {}, "สายสัมพันธ์ทางกฎหมาย"),
      el("p", {class: "fine-print"}, "แสดงความสัมพันธ์ที่ตรวจพบในขอบเขตของรายการนี้ เพื่อช่วยอ่านฉบับฐานและฉบับแก้ไขร่วมกัน"));
    relations.append(el("ul", {class: "relation-list"}, item.legalRelations.map(relation => {
      const target = (catalog.items || []).find(candidate => candidate.id === relation.targetId);
      const heading = target
        ? el("a", {href: `instrument.html?id=${encodeURIComponent(target.id)}`}, relation.label)
        : el("strong", {}, relation.label);
      return el("li", {}, heading, el("p", {}, relation.basis));
    })));
    $("#app").append(relations);
  }

  if ((item.reviewSources || []).length) {
    const reviewCard = el("section", {class: "card section-gap"}, el("h2", {}, "หลักฐานที่ใช้ตรวจสถานะ"));
    reviewCard.append(el("ul", {class: "source-list"}, item.reviewSources.map(source => el("li", {},
      source.url
        ? el("a", {href: source.url, target: "_blank", rel: "noopener"}, source.label, " ↗")
        : el("strong", {}, source.label),
      el("span", {class: "source-kind"}, ` — ${REVIEWSOURCEMAP[source.type] || source.type || "ไม่ระบุประเภท"}${source.accessedAt ? ` • ตรวจเมื่อ ${thaiRecordedDate(source.accessedAt)}` : ""}`)
    ))));
    $("#app").append(reviewCard);
  }

  const sourceCard = el("section", {class: "card section-gap"}, el("h2", {}, "สำเนาในคลังและแหล่งทางการ"));
  const sources = item.sources || [{corpus: item.sourceCorpus, path: item.file, ext: item.ext}];
  sourceCard.append(el("ul", {class: "source-list"}, sources.map(source => el("li", {},
    el("strong", {}, source.corpus || "คลัง"), ` — ${source.path}`, source.sha256 ? el("code", {}, `SHA-256 ${source.sha256.slice(0, 12)}…`) : null))));
  const actions = el("div", {class: "action-row"});
  if (item.publicCopyUrl) actions.append(el("a", {class: "button", href: item.publicCopyUrl, target: "_blank", rel: "noopener"}, "เปิดสำเนาที่เผยแพร่ในเว็บไซต์ ↗"));
  if (localArchive && item.localCopyAvailable) actions.append(el("a", {class: "button", href: `__local_source__/${item.id}`, target: "_blank", rel: "noopener"}, "เปิดไฟล์ต้นฉบับในเครื่อง ↗"));
  if (item.officialUrl) actions.append(el("a", {class: "button secondary", href: item.officialUrl, target: "_blank", rel: "noopener"}, "เปิดแหล่งทางการของฉบับนี้ ↗"));
  if (actions.children.length) sourceCard.append(actions);
  if (!item.officialUrl) sourceCard.append(el("p", {class: "fine-print"},
    "ยังไม่มีลิงก์ตรงไปยังต้นฉบับทางการของฉบับนี้ สำเนาในคลังใช้เป็นหลักฐานทำงานโดยระบุที่มาและลายนิ้วมือไฟล์ ",
    el("a", {href: GAZETTE, target: "_blank", rel: "noopener"}, "ค้นต่อที่ราชกิจจานุเบกษา ↗")));
  if (!localArchive && !item.publicCopyUrl) sourceCard.append(el("p", {class: "fine-print"},
    "เว็บไซต์สาธารณะแสดงข้อมูลอ้างอิงของไฟล์ แต่ไม่ส่งไฟล์จากคอมพิวเตอร์ขึ้นอินเทอร์เน็ต เปิดเว็บไซต์ด้วย tools/serve_local.py เพื่อใช้ปุ่มเปิดไฟล์ในเครื่อง"));
  $("#app").append(sourceCard);

  const citation = buildCitation(item);
  const citationField = el("textarea", {class: "citation-box", readonly: true, rows: "5", "aria-label": "ข้อความอ้างอิงสำเนาในคลัง"});
  citationField.value = citation;
  const copyButton = el("button", {class: "button secondary", type: "button"}, "คัดลอกข้อความอ้างอิง");
  copyButton.addEventListener("click", () => copyText(citation, copyButton, citationField));
  $("#app").append(el("section", {class: "card section-gap"}, el("h2", {}, "ข้อความอ้างอิงสำเนาในคลัง"),
    citationField, copyButton,
    el("p", {class: "fine-print"}, "ข้อความนี้ระบุสำเนาที่ใช้ตรวจอย่างโปร่งใส และไม่เรียกสำเนาว่าเป็นต้นฉบับทางการเมื่อยังไม่มีหลักฐานยืนยัน")));

  if (item.hasText) {
    const fulltextBox = el("section", {class: "card section-gap"}, el("h2", {}, "ข้อความสำหรับช่วยค้นหา"),
      el("p", {class: "fine-print"}, "ข้อความอาจมาจากการสกัดหรือ OCR และอาจคลาดเคลื่อน ห้ามใช้แทนภาพต้นฉบับทางการ"),
      el("div", {id: "ftext", class: "loading", "aria-live": "polite"}, "กำลังโหลดข้อความ…"));
    $("#app").append(fulltextBox);
    getText(`data/text/${item.id}.txt`).then(text => {
      const display = text.slice(0, 60000) + (text.length > 60000 ? "\n\n…(แสดงเฉพาะ 60,000 อักขระแรก)" : "");
      $("#ftext").replaceChildren(el("pre", {class: "fulltext", tabindex: "0"}, display));
    }).catch(() => { $("#ftext").replaceChildren(empty("ไม่พบไฟล์ข้อความ โปรดตรวจการสร้างดัชนี")); });
  } else {
    $("#app").append(el("div", {class: "callout"}, el("h2", {}, "ยังค้นเนื้อความไม่ได้"),
      el("p", {}, "รายการนี้ยังไม่มีไฟล์ข้อความหรือผล OCR แต่ยังค้นจากชื่อและเมทาดาทาได้")));
  }
}

/* Review tracker */
async function initTracker() {
  head("ทะเบียนประเด็นทบทวน", "ข้อเสนอเชิงนโยบายแยกจากสถานะทางกฎหมาย และต้องผ่านการตรวจหลักฐาน/รับฟังความคิดเห็นก่อนตัดสินใจ");
  const register = await getJSON("data/register.json").catch(() => ({items: []}));
  if (!(register.items || []).length) { $("#app").append(empty("ยังไม่มีข้อมูลทะเบียน")); return; }
  const filters = el("div", {class: "pill-row", role: "group", "aria-label": "กรองสถานะข้อเสนอ"},
    el("button", {class: "pill on", type: "button", "data-filter": "", "aria-pressed": "true"}, "ทั้งหมด"),
    Object.entries(RSMAP).map(([key, value]) => el("button", {class: "pill", type: "button", "data-filter": key, "aria-pressed": "false"}, value[0])));
  const output = el("div", {id: "tracker-output"});
  $("#app").append(el("div", {class: "notice subtle"}, "คำว่า “เสนอแก้ไข/เสนอทบทวน” เป็นสถานะของข้อเสนอ มิใช่ข้อยุติว่าสภาพบังคับของกฎหมายเดิมสิ้นสุดแล้ว"), filters, output);
  function draw(filter) {
    output.replaceChildren();
    const groups = {};
    register.items.forEach(row => { (groups[row.group] ||= []).push(row); });
    Object.entries(groups).forEach(([group, rows]) => {
      const filtered = rows.filter(row => !filter || row.status === filter);
      if (!filtered.length) return;
      const table = el("table", {class: "tbl"}, el("thead", {}, el("tr", {},
        el("th", {scope: "col"}, "รหัส"), el("th", {scope: "col"}, "เรื่อง"),
        el("th", {scope: "col"}, "ฐานอำนาจที่ต้องตรวจ"), el("th", {scope: "col"}, "ข้อเสนอ"), el("th", {scope: "col"}, "เหตุผล/งานถัดไป"))));
      const body = el("tbody");
      filtered.forEach(row => body.append(el("tr", {}, el("td", {"data-label": "รหัส"}, row.code),
        el("td", {"data-label": "เรื่อง", html: mark(row.title)}), el("td", {"data-label": "ฐานอำนาจ"}, row.authority || "—"),
        el("td", {"data-label": "ข้อเสนอ"}, badge(RSMAP, row.status) || row.status),
        el("td", {"data-label": "เหตุผล/งานถัดไป", html: mark(row.note || "")}))));
      table.append(body);
      output.append(el("section", {class: "tracker-group"}, el("h2", {}, group), el("div", {class: "table-scroll", tabindex: "0", role: "region", "aria-label": `ตาราง ${group}`}, table)));
    });
    if (!output.children.length) output.append(empty("ไม่มีรายการในสถานะนี้"));
  }
  filters.addEventListener("click", event => {
    const button = event.target.closest("button[data-filter]");
    if (!button) return;
    $$("button", filters).forEach(item => { item.classList.remove("on"); item.setAttribute("aria-pressed", "false"); });
    button.classList.add("on"); button.setAttribute("aria-pressed", "true"); draw(button.dataset.filter);
  });
  draw("");
}

/* Proposals */
async function initProposals() {
  head("ข้อเสนอดำเนินงาน", "กรอบงานที่ต้องพิสูจน์ด้วยฐานอำนาจ หลักฐาน ผลกระทบ และการรับฟังผู้เกี่ยวข้อง");
  const data = await getJSON("data/proposals.json").catch(() => ({groups: []}));
  $("#app").append(el("div", {class: "notice subtle"}, "รายการต่อไปนี้เป็นข้อเสนอเพื่อการศึกษา ไม่ใช่คำวินิจฉัยว่ากฎหมายใดชอบหรือไม่ชอบด้วยกฎหมาย"));
  (data.groups || []).forEach(group => {
    const section = el("section", {class: "card proposal-group"}, el("h2", {}, group.title));
    (group.items || []).forEach(item => {
      const article = el("article", {class: "proposal-item"}, el("h3", {html: mark(item.title)}),
        el("div", {class: "meta"}, item.ref ? el("span", {class: "chip"}, item.ref) : null, badge(RSMAP, item.status)),
        item.detail ? el("p", {html: mark(item.detail)}) : null);
      const fields = [
        ["ประเด็นกฎหมาย", item.issue], ["หลักฐานที่ต้องตรวจ", item.evidence],
        ["เกณฑ์ตรวจสอบ", item.legalTests], ["ทางเลือก", item.alternatives], ["ผลกระทบ/การรับฟัง", item.impact]
      ].filter(([, value]) => value);
      if (fields.length) article.append(el("dl", {class: "proposal-details"}, fields.map(([term, value]) => [el("dt", {}, term), el("dd", {html: mark(value)}, )])));
      section.append(article);
    });
    $("#app").append(section);
  });
}

/* Legal authority map */
async function initHierarchy() {
  head("ฐานอำนาจและความสัมพันธ์ของกฎหมาย", "แผนที่สำหรับตั้งคำถามว่าแต่ละตราสารอาศัยอำนาจใด มีขอบเขตเพียงใด และสัมพันธ์กับกฎหมายอื่นอย่างไร");
  const data = await getJSON("data/hierarchy.json").catch(() => ({levels: [], findings: []}));
  $("#app").append(el("div", {class: "notice subtle"}, "ผังนี้เป็นเครื่องมือวิเคราะห์เบื้องต้น ไม่ใช่ข้อสรุปว่าตราสารระดับหนึ่งย่อมขัดกับอีกระดับหนึ่งโดยอัตโนมัติ ต้องพิจารณาฐานอำนาจ เนื้อหา เวลา และบทเฉพาะกาลเป็นรายกรณี"));
  const tree = el("div", {class: "tree"});
  (data.levels || []).forEach((level, index) => {
    tree.append(el("section", {class: "level"}, el("h2", {}, level.name),
      (level.nodes || []).map(node => el("article", {class: "node"}, el("h3", {}, node.title),
        node.basis ? el("p", {class: "basis"}, el("strong", {}, "ฐานที่ต้องตรวจ: "), node.basis) : null,
        node.note ? el("p", {html: mark(node.note)}) : null))));
    if (index < data.levels.length - 1) tree.append(el("div", {class: "arrow", "aria-hidden": "true"}, "↓"));
  });
  $("#app").append(tree);
  (data.findings || []).forEach(finding => $("#app").append(el("div", {class: `callout ${finding.tone || ""}`},
    el("h2", {}, finding.title), el("p", {html: mark(finding.body)}),
    finding.confidence ? el("p", {class: "fine-print"}, `ระดับข้อสรุป: ${finding.confidence}`) : null)));
}

/* Legal issues/opinions */
async function initOpinions() {
  head("ประเด็นและความเห็นทางกฎหมาย", "สรุปแบบ Issue–Rule–Analysis–Conclusion พร้อมระดับการตรวจสอบและสิ่งที่ต้องหาหลักฐานเพิ่ม");
  const data = await getJSON("data/opinions.json").catch(() => ({items: []}));
  if (!(data.items || []).length) { $("#app").append(empty("ยังไม่มีความเห็นที่เผยแพร่ได้")); return; }
  (data.items || []).forEach(opinion => {
    const article = el("article", {class: "card opinion"}, el("h2", {}, opinion.title),
      el("div", {class: "meta"}, opinion.ref ? el("span", {class: "chip"}, opinion.ref) : null,
        opinion.reviewStatus ? el("span", {class: "badge b-unverified"}, opinion.reviewStatus) : null,
        opinion.date ? el("span", {}, opinion.date) : null));
    if (opinion.summary) article.append(el("p", {class: "lead", html: mark(opinion.summary)}));
    const sections = [["ประเด็น", opinion.issue], ["หลักกฎหมาย/ฐานอำนาจ", opinion.rule],
      ["วิเคราะห์เบื้องต้น", opinion.analysis], ["ข้อสรุปชั่วคราว", opinion.conclusion],
      ["หลักฐานหรือความเห็นที่ยังต้องเพิ่ม", opinion.nextEvidence]];
    sections.filter(([, value]) => value).forEach(([title, value]) => article.append(el("section", {}, el("h3", {}, title), el("p", {html: mark(value)}))));
    if (opinion.sources && opinion.sources.length) article.append(el("h3", {}, "แหล่งอ้างอิง"),
      el("ul", {class: "source-list"}, opinion.sources.map(source => el("li", {}, source.url
        ? el("a", {href: source.url, target: "_blank", rel: "noopener"}, `${source.label} ↗`) : source.label))));
    $("#app").append(article);
  });
}

/* Compare */
async function initCompare() {
  head("เทียบตัวบท", "เปรียบเทียบถ้อยคำเดิม ฉบับใหม่ หรือข้อเสนอรายประเด็น โดยต้องตรวจต้นฉบับก่อนนำไปอ้างอิง");
  const index = await getJSON("data/compare/index.json").catch(() => ({sets: []}));
  const select = selectOf("compare-select", [["", "เลือกเรื่องที่ต้องการเทียบ"], ...(index.sets || []).map(set => [set.file, set.title])], "เลือกชุดเทียบตัวบท");
  $("#app").append(labeledControl("ชุดเปรียบเทียบ", select), el("div", {id: "compare-output", class: "section-gap"}));
  select.addEventListener("change", async () => {
    const output = $("#compare-output"); output.replaceChildren(); if (!select.value) return;
    const data = await getJSON(`data/compare/${select.value}`);
    output.append(el("div", {class: "callout"}, el("h2", {}, data.title), el("p", {html: mark(data.summary || "")})));
    const comparison = el("div", {class: "cmp"},
      el("section", {class: "col old"}, el("h2", {class: "colh"}, data.oldLabel || "ฉบับเดิม")),
      el("section", {class: "col new"}, el("h2", {class: "colh"}, data.newLabel || "ฉบับใหม่/ข้อเสนอ")));
    (data.rows || []).forEach(row => {
      comparison.children[0].append(el("div", {class: "row", html: mark(row.old || "—")}));
      comparison.children[1].append(el("div", {class: "row", html: mark(row.new || "—")}));
    });
    output.append(comparison);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  chrome();
  const initializers = {
    "index.html": initDashboard, "library.html": initLibrary, "instrument.html": initInstrument,
    "tracker.html": initTracker, "proposals.html": initProposals, "hierarchy.html": initHierarchy,
    "opinions.html": initOpinions, "compare.html": initCompare
  };
  const run = initializers[document.body.dataset.page];
  if (run) run().catch(error => $("#app").append(el("div", {class: "callout red", role: "alert"},
    el("h2", {}, "โหลดข้อมูลไม่สำเร็จ"), el("p", {}, String(error.message || error)))));
});
