# คลังกฎหมายและข้อเสนอปฏิรูปอนุบัญญัติคุรุสภา (เว็บไซต์ v1)

เว็บไซต์ static (ไม่มีเซิร์ฟเวอร์หลังบ้าน) สำหรับทีมยกร่าง รวบรวมกฎหมายคุรุสภา + เครื่องมือบริหารการปฏิรูป
(คลังกฎหมาย+ค้นหา • ทะเบียนปฏิรูป • เทียบตัวบท • ผังลำดับศักดิ์ • ความเห็นกฎหมาย • ข้อเสนอดำเนินงาน)

## โครงสร้าง
```
kurusapha-law-site/
├─ index.html            หน้าแรก (ภาพรวม)
├─ library.html          คลังกฎหมาย + ค้นหา/กรอง
├─ instrument.html       หน้ารายฉบับ (?id=...)
├─ tracker.html          ทะเบียนปฏิรูป
├─ compare.html          เทียบตัวบท
├─ hierarchy.html        ผังลำดับศักดิ์
├─ opinions.html         ความเห็นกฎหมาย
├─ proposals.html        ข้อเสนอดำเนินงาน
├─ assets/css/style.css
├─ assets/js/app.js
├─ data/
│   ├─ catalog.json      แคตตาล็อกกฎหมาย (สร้างจากไปป์ไลน์)
│   ├─ coverage.json     รายงานชนิดไฟล์
│   ├─ register.json     ทะเบียนปฏิรูป
│   ├─ proposals.json    ข้อเสนอดำเนินงาน
│   ├─ hierarchy.json    ผังลำดับศักดิ์
│   ├─ opinions.json     ความเห็นกฎหมาย
│   └─ compare/          ชุดเทียบตัวบท
├─ tools/gen_catalog.py  สคริปต์สร้าง catalog.json ใหม่
└─ .nojekyll             ให้ GitHub Pages ไม่ประมวลผลด้วย Jekyll
```

## เปิดทดสอบในเครื่อง
ต้องเปิดผ่านเว็บเซิร์ฟเวอร์ (เพราะหน้าเว็บ `fetch` ไฟล์ JSON) — เปิดไฟล์ตรง ๆ ด้วย file:// จะไม่โหลดข้อมูล
```
cd kurusapha-law-site
python3 -m http.server 8080
# แล้วเปิด http://localhost:8080/
```

## อัปเดตข้อมูล
- **แคตตาล็อก:** วางไฟล์กฎหมายใหม่ในโฟลเดอร์คอร์ปัส แล้วรัน `python3 tools/gen_catalog.py` → `data/catalog.json` อัปเดต
- **ทะเบียน/ข้อเสนอ/ผัง/ความเห็น/เทียบ:** แก้ไฟล์ JSON ใน `data/` ได้โดยตรง แล้ว commit
- นโยบายไฟล์: เก็บเฉพาะ **ข้อความ + ลิงก์ราชกิจจานุเบกษา** ไม่ฝัง PDF ต้นฉบับในเว็บ (repo เบา)

## เผยแพร่ขึ้น GitHub Pages (บัญชี burapatis)
วิธีที่ 1 — เป็น **project site** (URL: `https://burapatis.github.io/kurusapha-law/`)
```
cd kurusapha-law-site
git init
git add -A
git commit -m "v1: คลังกฎหมายและข้อเสนอปฏิรูปคุรุสภา"
git branch -M main
git remote add origin https://github.com/burapatis/kurusapha-law.git
git push -u origin main
# GitHub → repo Settings → Pages → Source: Deploy from a branch → main / (root) → Save
```
วิธีที่ 2 — เป็น **user site หลัก** (URL: `https://burapatis.github.io/`) ให้ตั้งชื่อ repo ว่า `burapatis.github.io` แล้ว push เนื้อหานี้ที่ราก

> ทุกลิงก์ในเว็บใช้ path แบบสัมพัทธ์ จึงทำงานได้ทั้งสองแบบ (ราก หรือ subpath)

## หมายเหตุความถูกต้อง
เมทาดาทาในแคตตาล็อกส่วนใหญ่สังเคราะห์จากชื่อไฟล์/หมวดโฟลเดอร์ ส่วนฉบับสำคัญที่ทีมตรวจทานกับราชกิจจานุเบกษาแล้วจะมีหมายเหตุ/สถานะกำกับ — ก่อนอ้างอิงทางการควรตรวจกับต้นฉบับเสมอ การค้นหาปัจจุบันครอบคลุมชื่อ/เมทาดาทา (ค้นหาเต็มข้อความจะเพิ่มในเฟสถัดไป)
