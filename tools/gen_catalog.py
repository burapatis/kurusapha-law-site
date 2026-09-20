#!/usr/bin/env python3
"""สร้างแคตตาล็อกสาธารณะจากคลังกฎหมายสามชุดอย่างระมัดระวัง

หลักสำคัญ: ชื่อไฟล์ช่วยระบุเมทาดาทาได้ แต่ใช้ยืนยันสถานะทางกฎหมายไม่ได้
ดังนั้นสถานะเริ่มต้นของทุกรายการคือ ``unverified`` และจะเปลี่ยนได้เฉพาะ
รายการที่มีข้อมูลตรวจทานใน VERIFIED_OVERRIDES เท่านั้น
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path


SITE = Path(__file__).resolve().parents[1]
DATA = SITE / "data"
TEXT_DIR = DATA / "text"
DOCUMENTS = SITE.parent.parent
DEFAULT_ROOTS = [
    SITE.parent,
    DOCUMENTS / "กฎหมายหลัก",
    DOCUMENTS / "กฎหมายหลักการศึกษา",
]
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "odt", "rtf", "txt", "jpg", "jpeg", "png"}
PRIMARY_EXTENSIONS = {"pdf", "doc", "docx", "odt", "rtf", "jpg", "jpeg", "png"}
SKIP_PREFIXES = ("._", ".ds", "_stg_", "_rc_", "_ap_")
INTERNAL_MARKERS = (
    "(ฉบับปรับปรุงรวม)", "(ฉบับจัดพิมพ์ตรวจทานแล้ว)", "(ถอด ocr",
    "(บันทึกตรวจสอบ)", "(สรุปฉบับจริง)", "(ร่างต้นแบบ)",
    "ทะเบียนอนุบัญญัติ", "รายงานความเห็นทางกฎหมาย", "แผนแม่บทการสร้างเว็บไซต์",
)
SENSITIVE_MARKERS = (
    "สัญญาจ้างรองเลขาธิการคุรุสภา",
    "ใบสมัครเข้ารับการสรรหาเพื่อแต่งตั้งให้ดำรงตำแหน่งเลขาธิการคุรุสภา",
)
# ไฟล์ข้อความเหล่านี้เป็น companion ของไฟล์หลักที่ซ้ำกับฉบับในคลังคุรุสภา
# หลังเก็บไฟล์หลักไว้เพียงฉบับเดียว ต้องยังผูกข้อความกับรายการหลัก ไม่สร้างรายการ .txt แยก
COMPANION_ALIASES = {
    (
        "education",
        "คำสั่งหัวหน้า คสช. 17-2560 แก้ไขคำสั่งคุรุสภา.txt",
    ): (
        "kurusapha",
        "06_คำสั่ง_มติ_หนังสือเวียน/คำสั่งหัวหน้า คสช. ที่ 17-2560 เรื่อง แก้ไขเพิ่มเติมคำสั่งหัวหน้า คสช. ที่ 7-2558.pdf",
    ),
    (
        "education",
        "พ.ร.บ. กองทุนเพื่อความเสมอภาคทางการศึกษา พ.ศ. 2561 ภาษาอังกฤษ.txt",
    ): (
        "kurusapha",
        "01_รัฐธรรมนูญและพระราชบัญญัติ/พระราชบัญญัติกองทุนเพื่อความเสมอภาคทางการศึกษา พ.ศ. 2561 - ภาษาอังกฤษ.pdf",
    ),
    (
        "education",
        "พ.ร.บ. โรงเรียนเอกชน พ.ศ. 2550 ภาษาอังกฤษ.txt",
    ): (
        "kurusapha",
        "01_รัฐธรรมนูญและพระราชบัญญัติ/พระราชบัญญัติโรงเรียนเอกชน พ.ศ. 2550 รวมแก้ไขฉบับที่ 2 พ.ศ. 2554 - ภาษาอังกฤษ.pdf",
    ),
    (
        "education",
        "แผนการศึกษาแห่งชาติ พ.ศ. 2560-2579 ฉบับเต็ม.txt",
    ): (
        "kurusapha",
        "09_แผน_สถิติ_รายงาน/แผนการศึกษาแห่งชาติ พ.ศ. 2560-2579.pdf",
    ),
}
NO_PUBLIC_FULLTEXT_MARKERS = (
    "ตำราหลักกฎหมาย", "คำอธิบายรายมาตรา", "สื่อการสอน",
)

CATEGORY_MAP = {
    "01_รัฐธรรมนูญและพระราชบัญญัติ": "รัฐธรรมนูญ/พระราชบัญญัติ",
    "02_กฎกระทรวง": "กฎกระทรวง",
    "03_ข้อบังคับ": "ข้อบังคับ",
    "04_ระเบียบ": "ระเบียบ",
    "05_ประกาศ": "ประกาศ",
    "06_คำสั่ง_มติ_หนังสือเวียน": "คำสั่ง/มติ/หนังสือเวียน",
    "07_ประมวลจริยธรรม": "ประมวลจริยธรรม",
    "08_คู่มือ_หลักเกณฑ์_แนวทาง_สรุป": "คู่มือ/หลักเกณฑ์/แนวทาง",
    "09_แผน_สถิติ_รายงาน": "แผน/สถิติ/รายงาน",
    "10_แบบฟอร์มและสัญญา": "แบบฟอร์ม/สัญญา",
    "11_ข้อความประกอบเอกสาร": "ข้อความประกอบ",
}

# รายการนี้เป็นข้อยกเว้นที่ตรวจทานเฉพาะประเด็นตามข้อความกำกับแล้วเท่านั้น
# URL หน้ารวมมิใช่ลิงก์ต้นฉบับรายฉบับ จึงไม่บันทึกเป็น officialUrl
VERIFIED_OVERRIDES = [
    (
        "พระราชบัญญัติสภาครูและบุคลากรทางการศึกษา พ.ศ. 2546",
        {
            "status": "amended",
            "verificationStatus": "reviewed",
            "verificationConfidence": "high",
            "verifiedAt": "2569-09-20",
            "verifiedBy": "ตรวจทานสำเนาในคลังเทียบกับแหล่งทางการและคำสั่งที่เกี่ยวข้อง",
            "effectiveDate": "2003-06-12",
            "reviewScope": "ตรวจชื่อฉบับ วันประกาศ วันใช้บังคับ และผลของคำสั่งหัวหน้า คสช. ที่กระทบองค์ประกอบหรือการปฏิบัติหน้าที่ขององค์กร ณ วันที่ 20 กันยายน 2569",
            "statusBasis": "ยังเป็นกฎหมายแม่บทของคุรุสภา แต่การใช้บทเกี่ยวกับองค์ประกอบและการปฏิบัติหน้าที่ของคณะกรรมการมีคำสั่งหัวหน้า คสช. ที่ 7/2558 ซึ่งแก้ไขโดยที่ 17/2560 และคำสั่งที่ 11/2561 เข้ามากระทบ จึงต้องอ่านร่วมกัน",
            "officialUrl": "https://elibrary.ksp.or.th/index.php?id=24016&lvl=notice_display",
            "gazette": "เล่ม 120 ตอนที่ 52 ก วันที่ 11 มิถุนายน 2546 หน้า 1–30",
            "reviewSources": [
                {"label": "สำเนาพระราชบัญญัติในคลังกฎหมายคุรุสภา", "type": "local_original", "accessedAt": "2569-09-20"},
                {"label": "หอสมุดคุรุสภา: พระราชบัญญัติสภาครูและบุคลากรทางการศึกษา พ.ศ. 2546", "url": "https://elibrary.ksp.or.th/index.php?id=24016&lvl=notice_display", "type": "official_agency", "accessedAt": "2569-09-20"},
            ],
            "legalRelations": [
                {"type": "affected_by", "targetId": "doc-bacc25b6", "label": "ถูกกระทบโดยคำสั่งหัวหน้า คสช. ที่ 7/2558", "basis": "กำหนดการปฏิบัติหน้าที่แทนคณะกรรมการบางชุด"},
                {"type": "affected_by", "targetId": "doc-b84ef957", "label": "คำสั่งที่ 7/2558 แก้ไขโดยคำสั่งหัวหน้า คสช. ที่ 17/2560", "basis": "ต้องอ่านผลของคำสั่งฉบับเดิมร่วมกับฉบับแก้ไข"},
                {"type": "affected_by", "targetId": "doc-6ad39c57", "label": "ถูกกระทบโดยคำสั่งหัวหน้า คสช. ที่ 11/2561", "basis": "แก้ไของค์ประกอบคณะกรรมการมาตรฐานวิชาชีพ"},
            ],
            "note": "ป้าย “มีแก้ไข” ในรายการนี้ครอบคลุมทั้งการแก้ตัวบทและบทพิเศษที่กระทบการใช้กฎหมายแม่บท ไม่ได้หมายความว่าคำสั่งทุกฉบับเป็นพระราชบัญญัติแก้ไขเพิ่มเติม",
        },
    ),
    (
        "มาตรฐานวิชาชีพ ฉบับที่ 6 พ.ศ. 2567",
        {
            "status": "in_force", "verificationStatus": "reviewed", "verificationConfidence": "high",
            "verifiedAt": "2569-09-20", "verifiedBy": "ตรวจทานตัวบทในคลังเทียบกับประกาศของคุรุสภา",
            "effectiveDate": "2025-01-10",
            "reviewScope": "ตรวจวันประกาศ วันใช้บังคับ และข้อที่แก้ไขในสายข้อบังคับมาตรฐานวิชาชีพถึงฉบับที่ 6 ณ วันที่ 20 กันยายน 2569",
            "statusBasis": "มีผลใช้บังคับตั้งแต่วันประกาศในราชกิจจานุเบกษา และแก้ข้อ 5 ข้อ 7 (ข) และข้อ 9 (ข) ของข้อบังคับฉบับฐาน โดยไม่พบบทเลิกหรือบทแทนที่ภายหลังในสายที่ตรวจ",
            "officialUrl": "https://www.ksp.or.th/2025/01/15/53816/",
            "gazette": "เล่ม 142 ตอนพิเศษ 7 ง วันที่ 10 มกราคม 2568 หน้า 27–29",
            "reviewSources": [
                {"label": "สำเนาราชกิจจานุเบกษาในคลังกฎหมายคุรุสภา", "type": "local_original", "accessedAt": "2569-09-20"},
                {"label": "คุรุสภา: ข้อบังคับมาตรฐานวิชาชีพ (ฉบับที่ 6) พ.ศ. 2567", "url": "https://www.ksp.or.th/2025/01/15/53816/", "type": "official_agency", "accessedAt": "2569-09-20"},
            ],
            "legalRelations": [
                {"type": "amends", "targetId": "doc-dfe7f088", "label": "แก้ไขข้อบังคับมาตรฐานวิชาชีพ พ.ศ. 2556", "basis": "แก้ข้อ 5 ข้อ 7 (ข) และข้อ 9 (ข)"},
            ],
            "reformCode": "ก-1", "reformStatus": "amend",
        },
    ),
    (
        "มาตรฐานวิชาชีพ ฉบับที่ 5 พ.ศ. 2563",
        {
            "status": "in_force", "verificationStatus": "reviewed", "verificationConfidence": "high",
            "verifiedAt": "2569-09-20", "verifiedBy": "ตรวจทานตัวบทในคลังเทียบกับหอสมุดคุรุสภา",
            "effectiveDate": "2020-11-16",
            "reviewScope": "ตรวจวันประกาศ วันใช้บังคับ บทแทนที่ข้อ 17 และฉบับภายหลังในสายมาตรฐานวิชาชีพถึงฉบับที่ 6 ณ วันที่ 20 กันยายน 2569",
            "statusBasis": "ใช้บังคับตั้งแต่วันประกาศและแทนที่ข้อ 17 ซึ่งแก้ไขโดยฉบับที่ 3 พ.ศ. 2561 โดยไม่พบบทภายหลังที่แทนที่ข้อ 17 ในสายที่ตรวจ",
            "officialUrl": "https://elibrary.ksp.or.th/index.php?id=24048&lvl=notice_display",
            "gazette": "เล่ม 137 ตอนพิเศษ 270 ง วันที่ 16 พฤศจิกายน 2563",
            "reviewSources": [
                {"label": "สำเนาราชกิจจานุเบกษาในคลังกฎหมายคุรุสภา", "type": "local_original", "accessedAt": "2569-09-20"},
                {"label": "หอสมุดคุรุสภา: ข้อบังคับมาตรฐานวิชาชีพ (ฉบับที่ 5) พ.ศ. 2563", "url": "https://elibrary.ksp.or.th/index.php?id=24048&lvl=notice_display", "type": "official_agency", "accessedAt": "2569-09-20"},
            ],
            "legalRelations": [
                {"type": "amends", "targetId": "doc-dfe7f088", "label": "แก้ไขข้อบังคับมาตรฐานวิชาชีพ พ.ศ. 2556", "basis": "แทนที่ข้อ 17"},
                {"type": "supersedes", "targetId": "doc-c80926ac", "label": "แทนที่ผลของฉบับที่ 3 พ.ศ. 2561", "basis": "ฉบับที่ 5 ระบุให้ยกเลิกความในข้อ 17 ซึ่งแก้ไขโดยฉบับที่ 3 และใช้ข้อความใหม่"},
            ],
            "reformCode": "ก-1", "reformStatus": "amend",
        },
    ),
    (
        "มาตรฐานวิชาชีพ ฉบับที่ 4 พ.ศ. 2562",
        {
            "status": "in_force", "verificationStatus": "reviewed", "verificationConfidence": "high",
            "verifiedAt": "2569-09-20", "verifiedBy": "ตรวจทานตัวบทในคลังเทียบกับสำเนาทางการของกระทรวงศึกษาธิการ",
            "effectiveDate": "2019-03-20",
            "reviewScope": "ตรวจวันประกาศ วันใช้บังคับ ข้อที่แก้ไข และฉบับภายหลังในสายมาตรฐานวิชาชีพถึงฉบับที่ 6 ณ วันที่ 20 กันยายน 2569",
            "statusBasis": "ใช้บังคับตั้งแต่วันประกาศ แก้บทนิยามในข้อ 4 และข้อ 6 ข้อ 10 ข้อ 11 โดยฉบับที่ 6 แก้คนละข้อและไม่พบบทเลิกฉบับนี้ในสายที่ตรวจ",
            "officialUrl": "https://www.moe.go.th/backend/wp-content/uploads/2021/03/3.2.4%E0%B8%82%E0%B9%89%E0%B8%AD%E0%B8%9A%E0%B8%B1%E0%B8%87%E0%B8%84%E0%B8%B1%E0%B8%9A%E0%B8%A1%E0%B8%B2%E0%B8%95%E0%B8%A3%E0%B8%90%E0%B8%B2%E0%B8%99%E0%B8%89%E0%B8%9A%E0%B8%B1%E0%B8%9A%E0%B8%97%E0%B8%B5%E0%B9%8842562.pdf",
            "gazette": "เล่ม 136 ตอนพิเศษ 68 ง วันที่ 20 มีนาคม 2562",
            "reviewSources": [
                {"label": "สำเนาราชกิจจานุเบกษาในคลังกฎหมายคุรุสภา", "type": "local_original", "accessedAt": "2569-09-20"},
                {"label": "กระทรวงศึกษาธิการ: ข้อบังคับมาตรฐานวิชาชีพ (ฉบับที่ 4) พ.ศ. 2562", "url": "https://www.moe.go.th/backend/wp-content/uploads/2021/03/3.2.4%E0%B8%82%E0%B9%89%E0%B8%AD%E0%B8%9A%E0%B8%B1%E0%B8%87%E0%B8%84%E0%B8%B1%E0%B8%9A%E0%B8%A1%E0%B8%B2%E0%B8%95%E0%B8%A3%E0%B8%90%E0%B8%B2%E0%B8%99%E0%B8%89%E0%B8%9A%E0%B8%B1%E0%B8%9A%E0%B8%97%E0%B8%B5%E0%B9%8842562.pdf", "type": "official_agency", "accessedAt": "2569-09-20"},
            ],
            "legalRelations": [
                {"type": "amends", "targetId": "doc-dfe7f088", "label": "แก้ไขข้อบังคับมาตรฐานวิชาชีพ พ.ศ. 2556", "basis": "แก้บทนิยามในข้อ 4 และข้อ 6 ข้อ 10 ข้อ 11"},
            ],
            "reformCode": "ก-1", "reformStatus": "amend",
        },
    ),
    (
        "มาตรฐานวิชาชีพ ฉบับที่ 3 พ.ศ. 2561",
        {
            "status": "superseded", "verificationStatus": "reviewed", "verificationConfidence": "high",
            "verifiedAt": "2569-09-20", "verifiedBy": "ตรวจทานตัวบทในคลังและสายข้อบังคับฉบับแก้ไข",
            "effectiveDate": "2018-11-26",
            "reviewScope": "ตรวจวันประกาศ วันใช้บังคับ บทแก้ข้อ 17 และบทแทนที่โดยฉบับที่ 5 ณ วันที่ 20 กันยายน 2569",
            "statusBasis": "ฉบับนี้เคยแทนที่ข้อ 17 ที่แก้โดยฉบับที่ 2 แต่ต่อมาข้อ 17 ตามฉบับนี้ถูกฉบับที่ 5 พ.ศ. 2563 แทนที่โดยชัดแจ้ง",
            "gazette": "เล่ม 135 ตอนพิเศษ 299 ง วันที่ 26 พฤศจิกายน 2561",
            "reviewSources": [
                {"label": "สำเนาราชกิจจานุเบกษาในคลังกฎหมายคุรุสภา", "type": "local_original", "accessedAt": "2569-09-20"},
                {"label": "หน้ารวมกฎหมายคุรุสภา (ใช้ยืนยันการเผยแพร่รายชื่อฉบับ)", "url": "https://www.ksp.or.th/laws/", "type": "official_index", "accessedAt": "2569-09-20"},
            ],
            "legalRelations": [
                {"type": "amends", "targetId": "doc-dfe7f088", "label": "แก้ไขข้อบังคับมาตรฐานวิชาชีพ พ.ศ. 2556", "basis": "แทนที่ข้อ 17"},
                {"type": "supersedes", "targetId": "doc-f58d7672", "label": "แทนที่ผลของฉบับที่ 2 พ.ศ. 2561", "basis": "ยกเลิกความในข้อ 17 ซึ่งแก้ไขโดยฉบับที่ 2 และใช้ข้อความใหม่"},
                {"type": "superseded_by", "targetId": "doc-cf3a1f2e", "label": "ถูกแทนที่โดยฉบับที่ 5 พ.ศ. 2563", "basis": "ฉบับที่ 5 ยกเลิกความในข้อ 17 ซึ่งแก้ไขโดยฉบับที่ 3 และใช้ข้อความใหม่"},
            ],
            "reformCode": "ก-1", "reformStatus": "amend",
            "note": "“ถูกแทนที่แล้ว” หมายถึงผลของข้อความแก้ไขในฉบับนี้ถูกแทนที่ ไม่ใช่การยกเลิกข้อบังคับฉบับฐานทั้งฉบับ",
        },
    ),
    (
        "มาตรฐานวิชาชีพ ฉบับที่ 2 พ.ศ. 2561",
        {
            "status": "superseded", "verificationStatus": "reviewed", "verificationConfidence": "high",
            "verifiedAt": "2569-09-20", "verifiedBy": "ตรวจทานตัวบทในคลังเทียบกับราชกิจจานุเบกษาและสายข้อบังคับฉบับแก้ไข",
            "effectiveDate": "2018-10-04",
            "reviewScope": "ตรวจวันประกาศ วันใช้บังคับ บทแก้ข้อ 17 และบทแทนที่โดยฉบับที่ 3 ณ วันที่ 20 กันยายน 2569",
            "statusBasis": "ฉบับนี้แก้ข้อ 17 ของฉบับฐาน แต่ข้อความดังกล่าวถูกฉบับที่ 3 พ.ศ. 2561 แทนที่โดยชัดแจ้ง",
            "officialUrl": "https://ratchakitcha.soc.go.th/documents/17060908.pdf",
            "gazette": "เล่ม 135 ตอนพิเศษ 247 ง วันที่ 4 ตุลาคม 2561",
            "reviewSources": [
                {"label": "สำเนาราชกิจจานุเบกษาในคลังกฎหมายคุรุสภา", "type": "local_original", "accessedAt": "2569-09-20"},
                {"label": "ราชกิจจานุเบกษา: ข้อบังคับมาตรฐานวิชาชีพ (ฉบับที่ 2) พ.ศ. 2561", "url": "https://ratchakitcha.soc.go.th/documents/17060908.pdf", "type": "official_gazette", "accessedAt": "2569-09-20"},
            ],
            "legalRelations": [
                {"type": "amends", "targetId": "doc-dfe7f088", "label": "แก้ไขข้อบังคับมาตรฐานวิชาชีพ พ.ศ. 2556", "basis": "แทนที่ข้อ 17"},
                {"type": "superseded_by", "targetId": "doc-c80926ac", "label": "ถูกแทนที่โดยฉบับที่ 3 พ.ศ. 2561", "basis": "ฉบับที่ 3 ยกเลิกความในข้อ 17 ซึ่งแก้ไขโดยฉบับที่ 2 และใช้ข้อความใหม่"},
            ],
            "reformCode": "ก-1", "reformStatus": "amend",
            "note": "“ถูกแทนที่แล้ว” หมายถึงผลของข้อความแก้ไขในฉบับนี้ถูกแทนที่ ไม่ใช่การยกเลิกข้อบังคับฉบับฐานทั้งฉบับ",
        },
    ),
    (
        "มาตรฐานวิชาชีพ พ.ศ. 2556",
        {
            "status": "amended", "verificationStatus": "reviewed", "verificationConfidence": "high",
            "verifiedAt": "2569-09-20", "verifiedBy": "ตรวจทานตัวบทในคลังเทียบกับราชกิจจานุเบกษาและฉบับแก้ไขที่ 2–6",
            "effectiveDate": "2013-10-04",
            "reviewScope": "ตรวจวันประกาศ วันใช้บังคับ และสายการแก้ไขตั้งแต่ฉบับที่ 2 ถึงฉบับที่ 6 ณ วันที่ 20 กันยายน 2569",
            "statusBasis": "เป็นข้อบังคับฉบับฐานที่ยังต้องใช้ประกอบ แต่ถูกแก้ไขหลายครั้งโดยฉบับที่ 2–6 และต้องอ่านฉบับที่ยังมีผลร่วมกัน",
            "officialUrl": "https://ratchakitcha.soc.go.th/documents/1986082.pdf",
            "gazette": "เล่ม 130 ตอนพิเศษ 130 ง วันที่ 4 ตุลาคม 2556",
            "reviewSources": [
                {"label": "สำเนาราชกิจจานุเบกษาในคลังกฎหมายคุรุสภา", "type": "local_original", "accessedAt": "2569-09-20"},
                {"label": "ราชกิจจานุเบกษา: ข้อบังคับมาตรฐานวิชาชีพ พ.ศ. 2556", "url": "https://ratchakitcha.soc.go.th/documents/1986082.pdf", "type": "official_gazette", "accessedAt": "2569-09-20"},
            ],
            "legalRelations": [
                {"type": "amended_by", "targetId": "doc-f58d7672", "label": "แก้ไขโดยฉบับที่ 2 พ.ศ. 2561", "basis": "แก้ข้อ 17; ผลถูกแทนที่ภายหลัง"},
                {"type": "amended_by", "targetId": "doc-c80926ac", "label": "แก้ไขโดยฉบับที่ 3 พ.ศ. 2561", "basis": "แก้ข้อ 17; ผลถูกแทนที่ภายหลัง"},
                {"type": "amended_by", "targetId": "doc-6d2f5d79", "label": "แก้ไขโดยฉบับที่ 4 พ.ศ. 2562", "basis": "แก้บทนิยามและข้อ 6 ข้อ 10 ข้อ 11"},
                {"type": "amended_by", "targetId": "doc-cf3a1f2e", "label": "แก้ไขโดยฉบับที่ 5 พ.ศ. 2563", "basis": "แก้ข้อ 17"},
                {"type": "amended_by", "targetId": "doc-8f55babb", "label": "แก้ไขโดยฉบับที่ 6 พ.ศ. 2567", "basis": "แก้ข้อ 5 ข้อ 7 (ข) และข้อ 9 (ข)"},
            ],
            "reformCode": "ก-1", "reformStatus": "amend",
        },
    ),
    (
        "จรรยาบรรณของวิชาชีพ พ.ศ. 2556",
        {
            "status": "in_force", "verificationStatus": "reviewed", "verificationConfidence": "high",
            "verifiedAt": "2569-09-20", "verifiedBy": "ตรวจทานตัวบทในคลังเทียบกับหอสมุดคุรุสภาและหน้ารวมกฎหมายปัจจุบัน",
            "effectiveDate": "2013-10-04",
            "reviewScope": "ตรวจวันประกาศ วันใช้บังคับ บทเลิกฉบับเดิม และการอ้างใช้ในกฎหมาย/ข้อมูลคุรุสภาภายหลัง ณ วันที่ 20 กันยายน 2569",
            "statusBasis": "ใช้บังคับตั้งแต่วันประกาศในราชกิจจานุเบกษา ไม่พบบทเลิกฉบับนี้ในการตรวจสายกฎหมาย และคุรุสภายังเผยแพร่เป็นกฎหมายอ้างอิงปัจจุบัน",
            "officialUrl": "https://elibrary.ksp.or.th/index.php?id=24053&lvl=notice_display",
            "gazette": "เล่ม 130 ตอนพิเศษ 130 ง วันที่ 4 ตุลาคม 2556",
            "reviewSources": [
                {"label": "สำเนาราชกิจจานุเบกษาในคลังกฎหมายคุรุสภา", "type": "local_original", "accessedAt": "2569-09-20"},
                {"label": "หอสมุดคุรุสภา: ข้อบังคับว่าด้วยจรรยาบรรณของวิชาชีพ พ.ศ. 2556", "url": "https://elibrary.ksp.or.th/index.php?id=24053&lvl=notice_display", "type": "official_agency", "accessedAt": "2569-09-20"},
                {"label": "หน้ารวมกฎหมายคุรุสภา", "url": "https://www.ksp.or.th/laws/", "type": "official_index", "accessedAt": "2569-09-20"},
            ],
            "legalRelations": [
                {"type": "read_with", "targetId": "doc-4ad435b5", "label": "อ่านร่วมกับแบบแผนพฤติกรรม พ.ศ. 2550", "basis": "ข้อ 3 รับช่วงการอ้างอิงจากข้อบังคับเดิม และข้อ 6 กำหนดให้ประพฤติตามแบบแผนพฤติกรรมตามจรรยาบรรณ"},
                {"type": "read_with", "targetId": "doc-110ae2b2", "label": "ใช้เป็นฐานสารบัญญัติของกระบวนพิจารณา พ.ศ. 2568", "basis": "ข้อบังคับ พ.ศ. 2568 กำหนดกระบวนการพิจารณาการฝ่าฝืนจรรยาบรรณตามฉบับนี้"},
            ],
            "reformCode": "ก-2", "reformStatus": "keep",
            "note": "ตรวจยืนยันสถานะของข้อบังคับสารบัญญัติฉบับนี้แยกจากข้อบังคับว่าด้วยกระบวนพิจารณาการประพฤติผิดจรรยาบรรณ",
        },
    ),
    (
        "ใบอนุญาตประกอบวิชาชีพ ฉบับที่ 2 พ.ศ. 2567",
        {
            "status": "in_force", "verificationStatus": "reviewed", "verificationConfidence": "high",
            "verifiedAt": "2569-09-20", "verifiedBy": "ตรวจทานตัวบทในคลังเทียบกับประกาศของคุรุสภา",
            "effectiveDate": "2024-03-14",
            "reviewScope": "ตรวจวันประกาศ วันใช้บังคับ และข้อที่แก้ไขในสายข้อบังคับใบอนุญาตประกอบวิชาชีพ พ.ศ. 2565 ณ วันที่ 20 กันยายน 2569",
            "statusBasis": "มีผลใช้บังคับในวันถัดจากวันประกาศในราชกิจจานุเบกษา และไม่พบบทเลิกหรือบทแทนที่ภายหลังในสายที่ตรวจ",
            "officialUrl": "https://www.ksp.or.th/2024/03/14/49940/",
            "gazette": "เล่ม 141 ตอนพิเศษ 73 ง วันที่ 13 มีนาคม 2567",
            "reviewSources": [
                {"label": "สำเนาราชกิจจานุเบกษาในคลังกฎหมายคุรุสภา", "type": "local_original", "accessedAt": "2569-09-20"},
                {"label": "คุรุสภา: ข้อบังคับใบอนุญาตประกอบวิชาชีพ (ฉบับที่ 2) พ.ศ. 2567", "url": "https://www.ksp.or.th/2024/03/14/49940/", "type": "official_agency", "accessedAt": "2569-09-20"},
            ],
            "legalRelations": [
                {"type": "amends", "targetId": "doc-616a1a43", "label": "แก้ไขข้อบังคับใบอนุญาตประกอบวิชาชีพ พ.ศ. 2565", "basis": "ต้องอ่านร่วมกับฉบับฐาน"},
            ],
            "reformCode": "ก-4", "reformStatus": "amend",
        },
    ),
    (
        "ใบอนุญาตประกอบวิชาชีพ พ.ศ. 2565",
        {
            "status": "amended", "verificationStatus": "reviewed", "verificationConfidence": "high",
            "verifiedAt": "2569-09-20", "verifiedBy": "ตรวจทานตัวบทในคลังเทียบกับประกาศของคุรุสภาและฉบับที่ 2 พ.ศ. 2567",
            "effectiveDate": "2023-03-15",
            "reviewScope": "ตรวจวันประกาศ วันใช้บังคับ และสายการแก้ไขโดยฉบับที่ 2 พ.ศ. 2567 ณ วันที่ 20 กันยายน 2569",
            "statusBasis": "ฉบับฐานมีผลเมื่อพ้น 90 วันนับแต่ประกาศในราชกิจจานุเบกษา และถูกแก้ไขโดยฉบับที่ 2 พ.ศ. 2567 จึงต้องอ่านร่วมกัน",
            "officialUrl": "https://www.ksp.or.th/2023/01/31/42355/",
            "gazette": "เล่ม 139 ตอนพิเศษ 292 ง วันที่ 15 ธันวาคม 2565",
            "reviewSources": [
                {"label": "สำเนาราชกิจจานุเบกษาในคลังกฎหมายคุรุสภา", "type": "local_original", "accessedAt": "2569-09-20"},
                {"label": "คุรุสภา: ข้อบังคับใบอนุญาตประกอบวิชาชีพ พ.ศ. 2565", "url": "https://www.ksp.or.th/2023/01/31/42355/", "type": "official_agency", "accessedAt": "2569-09-20"},
            ],
            "legalRelations": [
                {"type": "amended_by", "targetId": "doc-993bc739", "label": "แก้ไขโดยฉบับที่ 2 พ.ศ. 2567", "basis": "ต้องอ่านฉบับฐานร่วมกับฉบับแก้ไข"},
            ],
            "reformCode": "ก-4", "reformStatus": "amend",
        },
    ),
    (
        "อุทธรณ์คำวินิจฉัยผิดจรรยาบรรณ ฉบับที่ 2 2569",
        {
            "status": "in_force", "verificationStatus": "reviewed", "verificationConfidence": "high",
            "verifiedAt": "2569-09-20", "verifiedBy": "ตรวจทานภาพตัวบทครบทั้งฉบับจากสำเนาราชกิจจานุเบกษาในคลัง",
            "effectiveDate": "2026-04-09",
            "reviewScope": "ตรวจชื่อฉบับ วันประกาศ วันใช้บังคับ ข้อที่แก้ไข คุณสมบัติและวิธีสรรหาคณะอนุกรรมการ และบทเฉพาะกาล ณ วันที่ 20 กันยายน 2569",
            "statusBasis": "มีผลใช้บังคับในวันถัดจากวันประกาศในราชกิจจานุเบกษา แก้ข้อ 7 เพิ่มข้อ 7/1–7/3 และแทนที่ข้อ 9 ของฉบับ พ.ศ. 2549 โดยไม่พบบทเลิกภายหลังในสายที่ตรวจ",
            "gazette": "เล่ม 143 ตอนพิเศษ 93 ง วันที่ 8 เมษายน 2569 หน้า 28–30",
            "reviewSources": [
                {"label": "สำเนาราชกิจจานุเบกษาฉบับที่ 2 พ.ศ. 2569 ในคลังกฎหมายคุรุสภา", "type": "local_original", "accessedAt": "2569-09-20"},
            ],
            "legalRelations": [
                {"type": "amends", "targetId": "doc-8a85f030", "label": "แก้ไขข้อบังคับอุทธรณ์ พ.ศ. 2549", "basis": "แทนที่ข้อ 7 และข้อ 9 พร้อมเพิ่มข้อ 7/1–7/3"},
                {"type": "supersedes", "targetId": "doc-a00d287f", "label": "แทนที่หลักเกณฑ์การได้มาซึ่งอนุกรรมการ พ.ศ. 2553 ในสาระ", "basis": "ข้อ 7 และข้อ 7/3 ใหม่กำหนดองค์ประกอบ คุณสมบัติ และกระบวนการสรรหาใหม่โดยตรง ซึ่งไม่สอดคล้องกับองค์ประกอบเดิมตามประกาศ พ.ศ. 2553"},
            ],
            "hasText": False, "publicFulltext": False, "textSource": None, "textChars": None,
            "reformCode": "ก-9", "reformStatus": "done",
            "note": "ยังไม่พบลิงก์ตรงของฉบับนี้จากระบบค้นหาสาธารณะ จึงยืนยันจากภาพสำเนาราชกิจจานุเบกษาในคลังและระบุเลขเล่ม ตอน วันที่ และหน้าไว้ตรวจย้อนกลับ; งดเผยแพร่ข้อความ OCR เพราะอ่านเลขไทยคลาดเคลื่อน",
        },
    ),
    (
        "อุทธรณ์คำวินิจฉัยการประพฤติผิดจรรยาบรรณ 2549",
        {
            "status": "amended", "verificationStatus": "reviewed", "verificationConfidence": "high",
            "verifiedAt": "2569-09-20", "verifiedBy": "ตรวจทานตัวบทในคลังเทียบกับราชกิจจานุเบกษาและฉบับที่ 2 พ.ศ. 2569",
            "effectiveDate": "2006-12-15",
            "reviewScope": "ตรวจชื่อฉบับ วันประกาศ วันใช้บังคับ ฐานอำนาจ และสายการแก้ไขโดยฉบับที่ 2 พ.ศ. 2569 ณ วันที่ 20 กันยายน 2569",
            "statusBasis": "เป็นข้อบังคับฉบับฐานที่ใช้บังคับตั้งแต่วันประกาศ แต่ถูกแก้ไขเรื่ององค์ประกอบ คุณสมบัติ วิธีสรรหา และวาระของคณะอนุกรรมการโดยฉบับที่ 2 พ.ศ. 2569 จึงต้องอ่านร่วมกัน",
            "officialUrl": "https://ratchakitcha.soc.go.th/documents/204062.pdf",
            "gazette": "เล่ม 123 ตอนพิเศษ 129 ง วันที่ 15 ธันวาคม 2549 หน้า 41–48",
            "reviewSources": [
                {"label": "สำเนาราชกิจจานุเบกษาในคลังกฎหมายคุรุสภา", "type": "local_original", "accessedAt": "2569-09-20"},
                {"label": "ราชกิจจานุเบกษา: ข้อบังคับว่าด้วยการอุทธรณ์คำวินิจฉัย พ.ศ. 2549", "url": "https://ratchakitcha.soc.go.th/documents/204062.pdf", "type": "official_gazette", "accessedAt": "2569-09-20"},
            ],
            "legalRelations": [
                {"type": "amended_by", "targetId": "doc-b482076a", "label": "แก้ไขโดยฉบับที่ 2 พ.ศ. 2569", "basis": "แทนที่ข้อ 7 และข้อ 9 พร้อมเพิ่มข้อ 7/1–7/3"},
                {"type": "read_with", "targetId": "doc-110ae2b2", "label": "อ่านร่วมกับกระบวนพิจารณา พ.ศ. 2568", "basis": "ใช้ในชั้นอุทธรณ์ต่อจากคำวินิจฉัยตามกระบวนพิจารณาการประพฤติผิดจรรยาบรรณ"},
            ],
            "reformCode": "ก-9", "reformStatus": "amend",
        },
    ),
    (
        "แบบแผนพฤติกรรมตามจรรยาบรรณของวิชาชีพ พ.ศ. 2550",
        {
            "status": "in_force", "verificationStatus": "reviewed", "verificationConfidence": "high",
            "verifiedAt": "2569-09-20", "verifiedBy": "ตรวจทานตัวบทในคลังเทียบกับหอสมุดคุรุสภาและข้อบังคับจรรยาบรรณ พ.ศ. 2556",
            "effectiveDate": "2007-04-27",
            "reviewScope": "ตรวจวันประกาศ วันใช้บังคับ ขอบเขตแบบแผนพฤติกรรม บทรับช่วงการอ้างอิงใน พ.ศ. 2556 และรายการกฎหมายปัจจุบันของคุรุสภา ณ วันที่ 20 กันยายน 2569",
            "statusBasis": "ใช้บังคับตั้งแต่วันประกาศ ไม่พบบทเลิกฉบับนี้ และข้อ 3 กับข้อ 6 ของข้อบังคับจรรยาบรรณ พ.ศ. 2556 รับช่วงการอ้างอิงและกำหนดให้ผู้ประกอบวิชาชีพประพฤติตามแบบแผนพฤติกรรม",
            "officialUrl": "https://elibrary.ksp.or.th/index.php?id=24057&lvl=notice_display",
            "gazette": "เล่ม 124 ตอนพิเศษ 51 ง วันที่ 27 เมษายน 2550 หน้า 37–56",
            "reviewSources": [
                {"label": "สำเนาราชกิจจานุเบกษาในคลังกฎหมายคุรุสภา", "type": "local_original", "accessedAt": "2569-09-20"},
                {"label": "หอสมุดคุรุสภา: ข้อบังคับว่าด้วยแบบแผนพฤติกรรม พ.ศ. 2550", "url": "https://elibrary.ksp.or.th/index.php?id=24057&lvl=notice_display", "type": "official_agency", "accessedAt": "2569-09-20"},
                {"label": "หน้ารวมกฎหมายคุรุสภา", "url": "https://www.ksp.or.th/laws/", "type": "official_index", "accessedAt": "2569-09-20"},
            ],
            "legalRelations": [
                {"type": "read_with", "targetId": "doc-21622537", "label": "อ่านร่วมกับข้อบังคับจรรยาบรรณ พ.ศ. 2556", "basis": "ฉบับ พ.ศ. 2556 รับช่วงการอ้างอิงจากข้อบังคับเดิมและข้อ 6 กำหนดให้ประพฤติตามแบบแผนพฤติกรรม"},
            ],
            "reformCode": "ก-2", "reformStatus": "keep",
            "note": "ข้อบังคับนี้ยังอ้างถ้อยคำจากฉบับมาตรฐานและจรรยาบรรณ พ.ศ. 2548 จึงควรอ่านผ่านบทรับช่วงในข้อ 3 ของข้อบังคับจรรยาบรรณ พ.ศ. 2556",
        },
    ),
    (
        "การได้มาซึ่งอนุกรรมการอุทธรณ์จรรยาบรรณวิชาชีพ 2553",
        {
            "status": "superseded", "verificationStatus": "reviewed", "verificationConfidence": "high",
            "verifiedAt": "2569-09-20", "verifiedBy": "ตรวจทานภาพตัวบทในคลังเทียบกับราชกิจจานุเบกษาและข้อบังคับฉบับที่ 2 พ.ศ. 2569",
            "effectiveDate": None,
            "reviewScope": "ตรวจฐานอำนาจ องค์ประกอบ คุณสมบัติ วิธีคัดเลือก และความสอดคล้องกับข้อ 7 และข้อ 7/3 ใหม่ ณ วันที่ 20 กันยายน 2569",
            "statusBasis": "ประกาศนี้กำหนดวิธีได้มาซึ่งคณะอนุกรรมการตามข้อ 7 เดิม แต่ข้อบังคับฉบับที่ 2 พ.ศ. 2569 แทนที่ข้อ 7 และเพิ่มข้อ 7/3 กำหนดองค์ประกอบ คุณสมบัติ และวิธีสรรหาใหม่โดยตรง จึงถูกแทนที่ในสาระ แม้ไม่พบบทเลิกประกาศโดยใช้ถ้อยคำชัดแจ้ง",
            "officialUrl": "https://ratchakitcha.soc.go.th/documents/1826563.pdf",
            "gazette": "เล่ม 127 ตอนพิเศษ 39 ง วันที่ 26 มีนาคม 2553 หน้า 14–16",
            "reviewSources": [
                {"label": "สำเนาราชกิจจานุเบกษาและแบบท้ายประกาศในคลังกฎหมายคุรุสภา", "type": "local_original", "accessedAt": "2569-09-20"},
                {"label": "ราชกิจจานุเบกษา: หลักเกณฑ์และวิธีการได้มาซึ่งคณะอนุกรรมการอุทธรณ์", "url": "https://ratchakitcha.soc.go.th/documents/1826563.pdf", "type": "official_gazette", "accessedAt": "2569-09-20"},
            ],
            "legalRelations": [
                {"type": "issued_under", "targetId": "doc-8a85f030", "label": "ออกตามข้อ 7 ของข้อบังคับอุทธรณ์ พ.ศ. 2549", "basis": "ข้อ 7 เดิมมอบให้คณะกรรมการกำหนดหลักเกณฑ์และวิธีการได้มาซึ่งคณะอนุกรรมการ"},
                {"type": "superseded_by", "targetId": "doc-b482076a", "label": "ถูกแทนที่ในสาระโดยฉบับที่ 2 พ.ศ. 2569", "basis": "ข้อ 7 และข้อ 7/3 ใหม่กำหนดองค์ประกอบ คุณสมบัติ และกระบวนการสรรหาใหม่โดยตรง"},
            ],
            "hasText": False, "publicFulltext": False, "textSource": None, "textChars": None,
            "reformCode": "ก-9", "reformStatus": "repeal",
            "note": "สถานะ “ถูกแทนที่แล้ว” เป็นข้อสรุปเรื่องผลใช้ในสาระจากความขัดกันของหลักเกณฑ์ มิใช่การยืนยันว่ามีบทเลิกประกาศโดยชัดแจ้ง; งดเผยแพร่ข้อความ OCR เพราะคุณภาพไม่เพียงพอ",
        },
    ),
    (
        "การพิจารณาการประพฤติผิดจรรยาบรรณของวิชาชีพ พ.ศ. 2568",
        {
            "status": "in_force",
            "verificationStatus": "reviewed",
            "verificationConfidence": "high",
            "verifiedAt": "2569-09-20",
            "verifiedBy": "ตรวจทานภาพตัวบทในคลังและบทเลิกกฎหมายเดิม",
            "effectiveDate": "2025-07-31",
            "reviewScope": "ตรวจวันประกาศ วันใช้บังคับ บทเลิกฉบับ พ.ศ. 2553 และฉบับแก้ไข รวมทั้งความสัมพันธ์กับจรรยาบรรณและการอุทธรณ์ ณ วันที่ 20 กันยายน 2569",
            "statusBasis": "มีผลใช้บังคับในวันถัดจากวันประกาศ และยกเลิกข้อบังคับ พ.ศ. 2553 ฉบับที่ 2 พ.ศ. 2559 และฉบับที่ 3 พ.ศ. 2563 โดยชัดแจ้ง",
            "gazette": "เล่ม 142 ตอนพิเศษ 257 ง วันที่ 30 กรกฎาคม 2568 หน้า 22–45",
            "reviewSources": [
                {"label": "สำเนาราชกิจจานุเบกษา พ.ศ. 2568 ในคลังกฎหมายคุรุสภา", "type": "local_original", "accessedAt": "2569-09-20"},
                {"label": "คุรุสภา: มติเห็นชอบร่างและสาระสำคัญของการปรับปรุง", "url": "https://www.ksp.or.th/2025/05/30/57373/", "type": "official_agency", "accessedAt": "2569-09-20"},
            ],
            "legalRelations": [
                {"type": "repeals", "targetId": "doc-67da7463", "label": "ยกเลิกข้อบังคับ พ.ศ. 2553", "basis": "ข้อ 3 (1) ยกเลิกโดยชัดแจ้ง"},
                {"type": "repeals", "targetId": "doc-21140482", "label": "ยกเลิกฉบับที่ 2 พ.ศ. 2559", "basis": "ข้อ 3 (2) ยกเลิกโดยชัดแจ้ง"},
                {"type": "repeals", "targetId": "doc-a84da2e5", "label": "ยกเลิกฉบับที่ 3 พ.ศ. 2563", "basis": "ข้อ 3 (3) ยกเลิกโดยชัดแจ้ง"},
                {"type": "read_with", "targetId": "doc-21622537", "label": "อ่านร่วมกับข้อบังคับจรรยาบรรณ พ.ศ. 2556", "basis": "จรรยาบรรณ พ.ศ. 2556 เป็นฐานสารบัญญัติ ส่วนฉบับนี้กำหนดกระบวนพิจารณา"},
                {"type": "read_with", "targetId": "doc-8a85f030", "label": "อ่านต่อเนื่องกับข้อบังคับอุทธรณ์ พ.ศ. 2549 และฉบับแก้ไข", "basis": "กระบวนการอุทธรณ์ใช้ภายหลังคำวินิจฉัยตามข้อบังคับนี้"},
            ],
            "hasText": False, "publicFulltext": False, "textSource": None, "textChars": None,
            "reformCode": "ก-3",
            "reformStatus": "done",
            "note": "ตรวจยืนยันสถานะและโครงสร้างสายกฎหมายแล้ว แต่ข้อสรุปในคดีรายบุคคลยังต้องตรวจข้อเท็จจริง ขั้นตอน และกฎหมายวิธีปฏิบัติราชการทางปกครองประกอบ; งดเผยแพร่ข้อความ OCR เพราะอ่านตัวบทคลาดเคลื่อน",
        },
    ),
    (
        "การพิจารณาการประพฤติผิดจรรยาบรรณของวิชาชีพ พ.ศ. 2553",
        {
            "status": "repealed",
            "verificationStatus": "reviewed",
            "verificationConfidence": "high",
            "verifiedAt": "2569-09-20",
            "verifiedBy": "ตรวจทานบทเลิกในข้อบังคับ พ.ศ. 2568",
            "statusBasis": "ถูกยกเลิกโดยข้อบังคับ พ.ศ. 2568",
            "officialUrl": "https://elibrary.ksp.or.th/index.php?id=24056&lvl=notice_display",
            "legalRelations": [
                {"type": "repealed_by", "targetId": "doc-110ae2b2", "label": "ถูกยกเลิกโดยข้อบังคับ พ.ศ. 2568", "basis": "ข้อ 3 (1) ของฉบับ พ.ศ. 2568"},
            ],
            "reformCode": "ก-3",
            "reformStatus": "repeal",
        },
    ),
    (
        "พิจารณาการประพฤติผิดจรรยาบรรณ ฉบับที่ 2 2559",
        {
            "status": "repealed", "verificationStatus": "reviewed",
            "verificationConfidence": "high", "verifiedAt": "2569-09-20",
            "verifiedBy": "ตรวจทานบทเลิกในข้อบังคับ พ.ศ. 2568",
            "statusBasis": "ถูกยกเลิกโดยข้อบังคับ พ.ศ. 2568",
            "legalRelations": [
                {"type": "repealed_by", "targetId": "doc-110ae2b2", "label": "ถูกยกเลิกโดยข้อบังคับ พ.ศ. 2568", "basis": "ข้อ 3 (2) ของฉบับ พ.ศ. 2568"},
            ],
            "reformCode": "ก-3", "reformStatus": "repeal",
        },
    ),
    (
        "พิจารณาการประพฤติผิดจรรยาบรรณ ฉบับที่ 3 2563",
        {
            "status": "repealed", "verificationStatus": "reviewed",
            "verificationConfidence": "high", "verifiedAt": "2569-09-20",
            "verifiedBy": "ตรวจทานบทเลิกในข้อบังคับ พ.ศ. 2568",
            "statusBasis": "ถูกยกเลิกโดยข้อบังคับ พ.ศ. 2568",
            "officialUrl": "https://elibrary.ksp.or.th/index.php?id=24054&lvl=notice_display",
            "legalRelations": [
                {"type": "repealed_by", "targetId": "doc-110ae2b2", "label": "ถูกยกเลิกโดยข้อบังคับ พ.ศ. 2568", "basis": "ข้อ 3 (3) ของฉบับ พ.ศ. 2568"},
            ],
            "reformCode": "ก-3", "reformStatus": "repeal",
        },
    ),
]

REFORM_HINTS = [
    ("มาตรฐานวิชาชีพ พ.ศ. 2556", "ก-1", "amend"),
    ("จรรยาบรรณของวิชาชีพ พ.ศ. 2556", "ก-2", "keep"),
    ("ใบอนุญาตประกอบวิชาชีพ พ.ศ. 2565", "ก-4", "amend"),
    ("สรรหาเลขาธิการคุรุสภา", "ก-5", "amend"),
    ("อุทธรณ์คำวินิจฉัยการประพฤติผิดจรรยาบรรณ", "ก-9", "verify"),
    ("รับรองความรู้และประสบการณ์ทางวิชาชีพ", "ก-10", "verify"),
    ("ประมวลจริยธรรมของคณะกรรมการและพนักงานเจ้าหน้าที่ 2552", "ข-1", "verify"),
]


def clean_title(path: Path) -> str:
    return re.sub(r"[_]+", " ", path.stem).strip()


def infer_type(title: str) -> str:
    n = title.strip()
    if n.startswith("รัฐธรรมนูญ"):
        return "รัฐธรรมนูญ"
    if n.startswith(("พระราชบัญญัติ", "พ.ร.บ.")):
        return "พระราชบัญญัติ"
    if "พระราชกฤษฎีกา" in n or n.startswith("พ.ร.ฎ"):
        return "พระราชกฤษฎีกา"
    for prefix, label in (
        ("กฎกระทรวง", "กฎกระทรวง"), ("ข้อบังคับ", "ข้อบังคับ"),
        ("ระเบียบ", "ระเบียบ"), ("ประกาศ", "ประกาศ"),
        ("คำสั่ง", "คำสั่ง"), ("มติ", "มติ"), ("หนังสือ", "หนังสือเวียน"),
        ("ประมวลจริยธรรม", "ประมวลจริยธรรม"),
    ):
        if n.startswith(prefix):
            return label
    if any(x in n for x in ("คู่มือ", "หลักเกณฑ์", "แนวทาง", "สรุป")):
        return "คู่มือ/หลักเกณฑ์"
    return "อื่น ๆ"


def infer_issuer(title: str) -> str:
    if title.startswith(("ข้อบังคับคุรุสภา", "ระเบียบคุรุสภา")):
        return "คณะกรรมการคุรุสภา"
    if title.startswith(("ระเบียบสำนักงานคุรุสภา", "ประกาศสำนักงานคุรุสภา", "คำสั่งสำนักงานคุรุสภา")):
        return "สำนักงานเลขาธิการคุรุสภา"
    if title.startswith("ประกาศคุรุสภา"):
        return "คุรุสภา"
    if "กระทรวงศึกษาธิการ" in title:
        return "กระทรวงศึกษาธิการ"
    if "คสช" in title:
        return "คณะรักษาความสงบแห่งชาติ/หัวหน้า คสช."
    if title.startswith(("รัฐธรรมนูญ", "พระราชบัญญัติ", "พ.ร.บ.", "พระราชกฤษฎีกา")):
        return "รัฐ/ฝ่ายนิติบัญญัติ"
    return "ไม่ระบุ"


def infer_year(title: str) -> int | None:
    years = [int(y) for y in re.findall(r"25\d{2}", title)]
    years = [y for y in years if 2400 <= y <= 2600]
    return max(years) if years else None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def corpus_slug(root: Path, index: int) -> str:
    known = {"กฎหมายคุรุสภา": "kurusapha", "กฎหมายหลัก": "core", "กฎหมายหลักการศึกษา": "education"}
    return known.get(root.name, f"corpus-{index + 1}")


def record_id(slug: str, relative: str) -> str:
    # รักษา URL เดิมของคลังคุรุสภาไว้ ส่วนคลังใหม่ใส่ namespace ป้องกันชนกัน
    seed = relative if slug == "kurusapha" else f"{slug}:{relative}"
    return "doc-" + hashlib.md5(seed.encode("utf-8")).hexdigest()[:8]


def is_internal(name: str) -> bool:
    lower = name.lower()
    return any(marker in lower for marker in INTERNAL_MARKERS)


def is_sensitive(name: str) -> bool:
    """กันเอกสารที่ระบุว่ามีข้อมูลส่วนบุคคลออกจากข้อมูลสาธารณะเสมอ."""
    return any(marker in name for marker in SENSITIVE_MARKERS)


def allows_public_fulltext(title: str) -> bool:
    """กันงานอธิบาย/ตำราที่อาจมีลิขสิทธิ์ออกจากดัชนีข้อความสาธารณะ"""
    return not any(marker in title for marker in NO_PUBLIC_FULLTEXT_MARKERS)


def enrich(record: dict) -> None:
    title = record["title"]
    for key, code, reform_status in REFORM_HINTS:
        if key in title:
            record["reformCode"] = code
            record["reformStatus"] = reform_status
            break
    for key, values in VERIFIED_OVERRIDES:
        if key in title:
            record.update(values)
            break


def discover(roots: list[Path], include_internal: bool) -> list[dict]:
    old_sources = {}
    old_catalog = DATA / "catalog.json"
    if old_catalog.exists():
        try:
            old_sources = {x["id"]: x.get("textSource") for x in json.loads(old_catalog.read_text("utf-8"))["items"]}
        except (KeyError, json.JSONDecodeError):
            pass

    records: list[dict] = []
    by_hash: dict[str, dict] = {}
    by_location: dict[tuple[str, str], dict] = {}
    primary_by_title: dict[tuple[str, str], dict] = {}
    companion_text: dict[tuple[str, str], Path] = {}
    candidates: list[tuple[int, Path, Path, str, str]] = []

    for index, root in enumerate(roots):
        root = root.resolve()
        if not root.exists():
            print(f"WARNING: ไม่พบโฟลเดอร์ {root}")
            continue
        slug = corpus_slug(root, index)
        for path in root.rglob("*"):
            if not path.is_file() or SITE in path.parents:
                continue
            if any(part.startswith(".") for part in path.relative_to(root).parts):
                continue
            ext = path.suffix.lower().lstrip(".")
            if ext not in ALLOWED_EXTENSIONS or path.name.lower().startswith(SKIP_PREFIXES):
                continue
            if is_sensitive(path.name):
                continue
            if is_internal(path.name) and not include_internal:
                continue
            relative = path.relative_to(root).as_posix()
            key = (slug, str(Path(relative).with_suffix("")))
            if ext == "txt":
                companion_text[key] = path
            candidates.append((index, root, path, slug, relative))

    # เอกสารหลักมาก่อน .txt เพื่อให้ไฟล์ข้อความชื่อเดียวกันเป็น companion
    candidates.sort(key=lambda x: (x[2].suffix.lower() == ".txt", x[0], x[4].casefold()))
    for index, root, path, slug, relative in candidates:
        ext = path.suffix.lower().lstrip(".")
        key = (slug, str(Path(relative).with_suffix("")))
        if ext == "txt" and any(
            r.get("_companionKey") == key and r["ext"] in PRIMARY_EXTENSIONS for r in records
        ):
            continue

        digest = sha256(path)
        source = {
            "corpus": root.name,
            "path": relative,
            "ext": ext,
            "sha256": digest,
            "bytes": path.stat().st_size,
        }
        title = clean_title(path)
        title_key = (slug, title.casefold())
        alias_target = COMPANION_ALIASES.get((slug, relative))
        if alias_target:
            existing = by_location.get(alias_target)
            if not existing:
                raise RuntimeError(f"ไม่พบเอกสารหลักสำหรับ companion alias: {slug}:{relative}")
            existing["sources"].append(source)
            existing["sourceCorpora"] = sorted({s["corpus"] for s in existing["sources"]})
            existing["hasText"] = existing["publicFulltext"]
            by_hash[digest] = existing
            by_location[(slug, relative)] = existing
            continue
        # ลายนิ้วมือไฟล์ตรงกันมีน้ำหนักสูงกว่าการจับคู่จากชื่อไฟล์
        if digest in by_hash:
            existing = by_hash[digest]
            existing["sources"].append(source)
            existing["sourceCorpora"] = sorted({s["corpus"] for s in existing["sources"]})
            by_location[(slug, relative)] = existing
            if ext in PRIMARY_EXTENSIONS:
                primary_by_title.setdefault(title_key, existing)
            continue
        # ไฟล์ .txt ชื่อเดียวกับเอกสารหลักในคลังเดียวกันถือเป็นข้อความคู่ค้นหา
        # แต่ยังเก็บเป็น source อีกหนึ่งรายการเพื่อให้ตรวจย้อนกลับได้
        if ext == "txt" and title_key in primary_by_title:
            existing = primary_by_title[title_key]
            existing["sources"].append(source)
            existing["sourceCorpora"] = sorted({s["corpus"] for s in existing["sources"]})
            if allows_public_fulltext(title):
                existing["hasText"] = True
                existing["publicFulltext"] = True
                existing["textSource"] = existing.get("textSource") or "companion"
                existing["_companionPath"] = str(path)
            by_hash[digest] = existing
            by_location[(slug, relative)] = existing
            continue

        rid = record_id(slug, relative)
        top = Path(relative).parts[0] if len(Path(relative).parts) > 1 else ""
        category = CATEGORY_MAP.get(top, root.name)
        companion = companion_text.get(key)
        stored_text = TEXT_DIR / f"{rid}.txt"
        public_text = allows_public_fulltext(title)
        has_text = public_text and (stored_text.exists() or companion is not None or ext == "txt")
        text_source = old_sources.get(rid)
        if not text_source and has_text:
            text_source = "txt" if ext == "txt" else "companion"

        record = {
            "id": rid,
            "title": title,
            "file": relative,
            "category": category,
            "type": infer_type(title),
            "issuer": infer_issuer(title),
            "year": infer_year(title),
            "ext": ext,
            "sourceCorpus": root.name,
            "sourceCorpora": [root.name],
            "sources": [source],
            "isKurusapha": "คุรุสภา" in title or "จรรยาบรรณ" in title,
            "isDeliverable": False,
            "audience": "public",
            "localCopyAvailable": True,
            "evidenceLevel": "local_file",
            "publicCopyUrl": None,
            "status": "unverified",
            "verificationStatus": "unverified",
            "verificationConfidence": None,
            "verifiedAt": None,
            "verifiedBy": None,
            "statusBasis": "ยังไม่ได้ตรวจยืนยันกับต้นฉบับทางการและกฎหมายที่แก้ไขเพิ่มเติม",
            "officialUrl": None,
            "gazette": None,
            "effectiveDate": None,
            "reviewScope": None,
            "reviewSources": [],
            "legalRelations": [],
            "reformStatus": None,
            "reformCode": None,
            "note": None,
            "hasText": has_text,
            "publicFulltext": public_text,
            "textSource": text_source,
            "textChars": stored_text.stat().st_size if public_text and stored_text.exists() else None,
            "_companionKey": key,
            "_companionPath": str(companion) if companion else None,
        }
        enrich(record)
        if record.get("verificationStatus") == "reviewed":
            if not record.get("reviewScope"):
                record["reviewScope"] = "ตรวจสถานะตามเหตุผลและขอบเขตที่บันทึกไว้ในรายการ ณ วันที่ตรวจ"
            if not record.get("reviewSources"):
                record["reviewSources"] = [{
                    "label": "สำเนาตัวบทในคลังกฎหมายคุรุสภา",
                    "type": "local_original",
                    "accessedAt": record.get("verifiedAt"),
                }]
                if record.get("officialUrl"):
                    record["reviewSources"].append({
                        "label": "แหล่งทางการของฉบับนี้",
                        "url": record["officialUrl"],
                        "type": "official_agency",
                        "accessedAt": record.get("verifiedAt"),
                    })
        if record.get("officialUrl"):
            record["evidenceLevel"] = "official_online"
        elif record.get("verificationStatus") == "reviewed":
            record["evidenceLevel"] = "local_reviewed"
        public_copy = SITE / "documents" / f"{rid}.{ext}"
        if public_copy.exists():
            record["publicCopyUrl"] = public_copy.relative_to(SITE).as_posix()
        records.append(record)
        by_hash[digest] = record
        by_location[(slug, relative)] = record
        if ext in PRIMARY_EXTENSIONS:
            primary_by_title.setdefault(title_key, record)

    records.sort(key=lambda r: (r["category"], -(r["year"] or 0), r["title"].casefold()))
    return records


def materialize_text(records: list[dict]) -> None:
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    for record in records:
        target = TEXT_DIR / f"{record['id']}.txt"
        companion = record.pop("_companionPath", None)
        record.pop("_companionKey", None)
        if record.get("publicFulltext") and not target.exists() and companion:
            target.write_text(Path(companion).read_text("utf-8", errors="replace"), "utf-8")
        if record.get("publicFulltext") and target.exists():
            record["hasText"] = True
            record["textChars"] = len(target.read_text("utf-8", errors="replace"))


def write_outputs(records: list[dict], roots: list[Path]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    materialize_text(records)
    categories = sorted({r["category"] for r in records})
    types = sorted({r["type"] for r in records})
    status_counts = Counter(r["status"] for r in records)
    verification_counts = Counter(r["verificationStatus"] for r in records)
    corpus_counts = Counter(corpus for r in records for corpus in r.get("sourceCorpora", [r["sourceCorpus"]]))
    fulltext = sum(bool(r["hasText"]) for r in records)
    meta = {
        "generated": date.today().isoformat(),
        "schemaVersion": 3,
        "corpora": [r.name for r in roots],
        "count": len(records),
        "fulltextDocs": fulltext,
        "categories": categories,
        "types": types,
        "statusCounts": dict(status_counts),
        "verificationCounts": dict(verification_counts),
        "note": "สถานะเริ่มต้นเป็น 'ยังไม่ตรวจยืนยัน'; ชื่อไฟล์และโฟลเดอร์ใช้สร้างเมทาดาทาเบื้องต้นเท่านั้น",
    }
    (DATA / "catalog.json").write_text(
        json.dumps({"meta": meta, "items": records}, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )

    extension_counts = Counter(r["ext"] for r in records)
    duplicate_sources = sum(max(0, len(r["sources"]) - 1) for r in records)
    coverage = {
        "generated": meta["generated"],
        "total": len(records),
        "byExtension": dict(sorted(extension_counts.items())),
        "byCorpus": dict(sorted(corpus_counts.items())),
        "byStatus": dict(sorted(status_counts.items())),
        "byVerification": dict(sorted(verification_counts.items())),
        "fulltextDocs": fulltext,
        "deduplicatedCopies": duplicate_sources,
    }
    (DATA / "coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", "utf-8")

    text_sources = Counter((r.get("textSource") or "none") for r in records if r.get("hasText"))
    extract_report = {
        "generated": meta["generated"],
        "total": len(records),
        "fulltextDocs": fulltext,
        "withoutFulltext": len(records) - fulltext,
        "byTextSource": dict(sorted(text_sources.items())),
        "note": "ข้อความสกัด/OCR ใช้ช่วยค้นหาเท่านั้น และไม่ใช้แทนต้นฉบับทางการ",
    }
    (DATA / "extract-report.json").write_text(
        json.dumps(extract_report, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )

    search_items = []
    for record in records:
        text_file = TEXT_DIR / f"{record['id']}.txt"
        if not record["hasText"] or not text_file.exists():
            continue
        blob = text_file.read_text("utf-8", errors="replace")
        search_items.append({"id": record["id"], "blob": blob})
    search = {"meta": {"generated": meta["generated"], "count": len(search_items)}, "items": search_items}
    (DATA / "search-index.json").write_text(json.dumps(search, ensure_ascii=False) + "\n", "utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", type=Path, help="โฟลเดอร์คลัง (ระบุซ้ำได้)")
    parser.add_argument("--include-internal", action="store_true", help="รวมร่าง/เอกสารโครงการ (ไม่เหมาะกับเว็บสาธารณะ)")
    args = parser.parse_args()
    roots = [p.expanduser().resolve() for p in (args.root or DEFAULT_ROOTS)]
    records = discover(roots, args.include_internal)
    write_outputs(records, roots)
    print(f"สร้างแคตตาล็อก {len(records)} รายการ; ค้นเต็มข้อความได้ {sum(r['hasText'] for r in records)} รายการ")


if __name__ == "__main__":
    main()
