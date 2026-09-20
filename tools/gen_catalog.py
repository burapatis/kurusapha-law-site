# -*- coding: utf-8 -*-
import os, re, json, hashlib
ROOT = os.path.expanduser("~/mnt/กฎหมายคุรุสภา")
OUT  = os.path.join(ROOT, "kurusapha-law-site", "data")
CATMAP = {
 "01_รัฐธรรมนูญและพระราชบัญญัติ":"รัฐธรรมนูญ/พระราชบัญญัติ",
 "02_กฎกระทรวง":"กฎกระทรวง","03_ข้อบังคับ":"ข้อบังคับ","04_ระเบียบ":"ระเบียบ",
 "05_ประกาศ":"ประกาศ","06_คำสั่ง_มติ_หนังสือเวียน":"คำสั่ง/มติ/หนังสือเวียน",
 "07_ประมวลจริยธรรม":"ประมวลจริยธรรม","08_คู่มือ_หลักเกณฑ์_แนวทาง_สรุป":"คู่มือ/หลักเกณฑ์/แนวทาง",
 "09_แผน_สถิติ_รายงาน":"แผน/สถิติ/รายงาน","10_แบบฟอร์มและสัญญา":"แบบฟอร์ม/สัญญา",
 "11_ข้อความประกอบเอกสาร":"ข้อความประกอบ",
}
def typ(name):
    n=name
    if n.startswith("รัฐธรรมนูญ"): return "รัฐธรรมนูญ"
    if n.startswith("พระราชบัญญัติ") or n.startswith("พ.ร.บ."): return "พระราชบัญญัติ"
    if "พระราชกฤษฎีกา" in n or n.startswith("พ.ร.ฎ"): return "พระราชกฤษฎีกา"
    if n.startswith("กฎกระทรวง"): return "กฎกระทรวง"
    if n.startswith("ข้อบังคับ"): return "ข้อบังคับ"
    if n.startswith("ระเบียบ"): return "ระเบียบ"
    if n.startswith("ประกาศ"): return "ประกาศ"
    if n.startswith("คำสั่ง"): return "คำสั่ง"
    if n.startswith("มติ"): return "มติ"
    if n.startswith("หนังสือ"): return "หนังสือเวียน"
    if n.startswith("ประมวลจริยธรรม"): return "ประมวลจริยธรรม"
    if "หลักเกณฑ์" in n or n.startswith("คู่มือ") or n.startswith("กฎบัตร") or n.startswith("แนวทาง") or n.startswith("คำถาม") or n.startswith("สรุป"): return "คู่มือ/หลักเกณฑ์"
    if n.startswith("แผน") or "สถิติ" in n or "สถานการณ์" in n or n.startswith("ร่างแผน"): return "แผน/สถิติ"
    if n.startswith("สัญญา") or n.startswith("ใบสมัคร") or n.startswith("ชุดแบบ"): return "แบบฟอร์ม/สัญญา"
    return "อื่น ๆ"
def issuer(name):
    if name.startswith("ข้อบังคับคุรุสภา"): return "คณะกรรมการคุรุสภา"
    if name.startswith("ระเบียบคุรุสภา"): return "คณะกรรมการคุรุสภา"
    if name.startswith("ระเบียบสำนักงานคุรุสภา"): return "สำนักงานเลขาธิการคุรุสภา"
    if name.startswith("ประกาศคุรุสภา"): return "คุรุสภา"
    if name.startswith("ประกาศสำนักงานคุรุสภา"): return "สำนักงานเลขาธิการคุรุสภา"
    if name.startswith("ประกาศอนุกรรมการคุรุสภา"): return "อนุกรรมการคุรุสภา"
    if name.startswith("ประกาศกระทรวงศึกษาธิการ"): return "กระทรวงศึกษาธิการ"
    if name.startswith("ระเบียบกระทรวงศึกษาธิการ"): return "กระทรวงศึกษาธิการ"
    if name.startswith("ระเบียบกระทรวงการคลัง") or name.startswith("หลักเกณฑ์กระทรวงการคลัง"): return "กระทรวงการคลัง"
    if name.startswith("ระเบียบ ก.ม.จ."): return "ก.ม.จ."
    if name.startswith("ระเบียบว่าด้วยการบริหารงบประมาณ") or name.startswith("ระเบียบสำนักนายก"): return "สำนักนายกรัฐมนตรี"
    if "คสช" in name: return "หัวหน้า คสช."
    if name.startswith("คำสั่งสำนักงานคุรุสภา"): return "สำนักงานเลขาธิการคุรุสภา"
    if name.startswith("มติ ครม"): return "คณะรัฐมนตรี"
    if name.startswith("หนังสือ ก.พ.ร"): return "ก.พ.ร."
    if name.startswith("ประมวลจริยธรรมองค์การมหาชน"): return "ก.ม.จ./องค์การมหาชน"
    if name.startswith("รัฐธรรมนูญ") or name.startswith("พระราชบัญญัติ") or name.startswith("พ.ร.บ.") or name.startswith("พระราชกฤษฎีกา"): return "ฝ่ายนิติบัญญัติ/รัฐบาล"
    return "-"
def year(name):
    yrs=re.findall(r'(25\d\d)', name)
    yrs=[int(y) for y in yrs if 2540<=int(y)<=2575]
    return max(yrs) if yrs else None
def is_ksp(name, cat):
    return ("คุรุสภา" in name) or ("จรรยาบรรณ" in name) or ("วิชาชีพ" in name and "ครู" in name) or cat in ("ข้อบังคับ",)
# enrichment overrides keyed by substring in filename
OV = [
 ("มาตรฐานวิชาชีพ พ.ศ. 2556", dict(reformCode="ก-1",reformStatus="amend",status="amended",note="ฉบับฐาน — มีฉบับรวมถึงฉบับที่ 6 (เอกสารส่งมอบ #10)")),
 ("มาตรฐานวิชาชีพ ฉบับที่ 6 พ.ศ. 2567", dict(reformCode="ก-1",reformStatus="amend",status="in_force",note="ฉบับแก้ไขล่าสุด")),
 ("จรรยาบรรณของวิชาชีพ พ.ศ. 2556", dict(reformCode="ก-2",reformStatus="keep",status="in_force")),
 ("การพิจารณาการประพฤติผิดจรรยาบรรณของวิชาชีพ พ.ศ. 2568", dict(reformCode="ก-3",reformStatus="done",status="in_force",gazette="เล่ม 142 ตอนพิเศษ 257 ง (30 ก.ค. 2568)",note="ประกาศใช้แล้ว ยกเลิก 2553/2559/2563 — ตรวจทานแล้ว (เอกสาร #14)")),
 ("การพิจารณาการประพฤติผิดจรรยาบรรณของวิชาชีพ พ.ศ. 2553", dict(reformCode="ก-3",reformStatus="repeal",status="repealed",note="ยกเลิกโดยฉบับ 2568")),
 ("พิจารณาการประพฤติผิดจรรยาบรรณ ฉบับที่ 2 2559", dict(reformCode="ก-3",reformStatus="repeal",status="repealed",note="ยกเลิกโดยฉบับ 2568")),
 ("พิจารณาการประพฤติผิดจรรยาบรรณ ฉบับที่ 3 2563", dict(reformCode="ก-3",reformStatus="repeal",status="repealed",note="ยกเลิกโดยฉบับ 2568")),
 ("ใบอนุญาตประกอบวิชาชีพ พ.ศ. 2565", dict(reformCode="ก-4",reformStatus="amend",status="in_force")),
 ("ใบอนุญาตประกอบวิชาชีพ ฉบับที่ 2 พ.ศ. 2567", dict(reformCode="ก-4",reformStatus="amend",status="in_force")),
 ("สรรหาเลขาธิการคุรุสภา พ.ศ. 2547", dict(reformCode="ก-5",reformStatus="amend",status="amended",note="ฉบับฐาน — ฉบับรวมถึงฉบับที่ 4 (เอกสาร #12)")),
 ("สรรหาเลขาธิการคุรุสภา ฉบับที่ 4 2569", dict(reformCode="ก-5",reformStatus="amend",status="in_force")),
 ("อุทธรณ์คำวินิจฉัยการประพฤติผิดจรรยาบรรณ 2549", dict(reformCode="ก-9",reformStatus="keep",status="amended",note="ฐาน — แก้โดยฉบับที่ 2/2569; สอดคล้อง 2568 ข้อ 64 (เอกสาร #16)")),
 ("อุทธรณ์คำวินิจฉัยผิดจรรยาบรรณ ฉบับที่ 2 2569", dict(reformCode="ก-9",reformStatus="keep",status="in_force")),
 ("รับรองความรู้และประสบการณ์ทางวิชาชีพ 2567", dict(reformCode="ก-10",reformStatus="amend",status="in_force",note="ฐานรุ่นที่ 2 — ฉบับรวมถึง 2/2569 (เอกสาร #15)")),
 ("รับรองความรู้และประสบการณ์ทางวิชาชีพ ฉบับที่ 2 2569", dict(reformCode="ก-10",reformStatus="amend",status="in_force")),
 ("รับรองความรู้และประสบการณ์วิชาชีพ 2550", dict(reformCode="ก-10",reformStatus="repeal",status="repealed")),
 ("รับรองความรู้และประสบการณ์วิชาชีพ ฉบับที่ 2 2565", dict(reformCode="ก-10",reformStatus="repeal",status="repealed")),
 ("ประมวลจริยธรรมของคณะกรรมการและพนักงานเจ้าหน้าที่ 2552", dict(reformCode="ข-1",reformStatus="repeal",status="repealed",note="ฐาน รธน.2550 สิ้นผล — แทนด้วยข้อกำหนดจริยธรรมอิง พ.ร.บ.2562")),
 ("สภาครูและบุคลากรทางการศึกษา พ.ศ. 2546", dict(reformStatus="keep",status="in_force",note="กฎหมายแม่ (ฐานอำนาจอนุบัญญัติทั้งหมด)")),
]
def overrides(name):
    for key,val in OV:
        if key in name: return val
    return {}

records=[]; cov={"txt":0,"pdf":0,"docx":0,"jpg":0,"other":0,"deliverable":0}
DELIVER = ["(ฉบับ","(ร่างต้นแบบ","(สรุปฉบับจริง","(ถอด OCR","(บันทึกตรวจสอบ","ทะเบียนอนุบัญญัติ","รายงานความเห็นทางกฎหมาย","แผนแม่บทการสร้างเว็บไซต์"]
for dirpath,_,files in os.walk(os.path.join(ROOT)):
    if "kurusapha-law-site" in dirpath: continue
    for fn in sorted(files):
        if fn.startswith(("._","_stg_","_rc_","_ap_",".DS")): continue
        ext=fn.rsplit(".",1)[-1].lower() if "." in fn else ""
        if ext not in ("pdf","docx","txt","jpg","json","csv","md","py"): continue
        rel=os.path.relpath(os.path.join(dirpath,fn),ROOT)
        top=rel.split(os.sep)[0] if os.sep in rel else ""
        cat=CATMAP.get(top,"เอกสารโครงการ" if any(fn.startswith(d) for d in DELIVER) else "อื่น ๆ")
        base=fn.rsplit(".",1)[0]
        is_deliv=any(fn.startswith(d) for d in DELIVER)
        if is_deliv: cov["deliverable"]+=1
        cov[ext if ext in cov else "other"]=cov.get(ext,0)+1
        rid="doc-"+hashlib.md5(rel.encode("utf-8")).hexdigest()[:8]
        rec=dict(id=rid, title=base, file=rel, category=cat,
                 type=("เอกสารโครงการ" if is_deliv else typ(base)),
                 issuer=("โครงการ (จัดทำโดยทีมยกร่าง)" if is_deliv else issuer(base)),
                 year=year(base), ext=ext,
                 isKurusapha=bool(is_deliv or is_ksp(base,cat)),
                 isDeliverable=is_deliv,
                 status="reference" if is_deliv else "in_force",
                 reformStatus=None, reformCode=None, gazette=None, note=None,
                 hasText=(ext=="txt"))
        rec.update(overrides(base))
        records.append(rec)
records.sort(key=lambda r:(r["category"], -(r["year"] or 0), r["title"]))
os.makedirs(OUT,exist_ok=True)
meta=dict(generated="2569-09-20", corpus="กฎหมายคุรุสภา", count=len(records),
          categories=sorted(set(r["category"] for r in records)),
          types=sorted(set(r["type"] for r in records)),
          note="เมทาดาทาสังเคราะห์จากชื่อไฟล์/หมวดโฟลเดอร์ + เสริมข้อมูลตรวจทานสำหรับฉบับสำคัญ; ตัวบทเต็มยังไม่ดัชนี (เฟส 1b)")
json.dump(dict(meta=meta,items=records), open(os.path.join(OUT,"catalog.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(cov, open(os.path.join(OUT,"coverage.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("RECORDS", len(records))
print("COVERAGE", json.dumps(cov,ensure_ascii=False))
print("CATEGORIES", json.dumps(meta["categories"],ensure_ascii=False))
enr=[r for r in records if r["reformCode"]]
print("ENRICHED", len(enr))
