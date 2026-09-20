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
        "การพิจารณาการประพฤติผิดจรรยาบรรณของวิชาชีพ พ.ศ. 2568",
        {
            "status": "in_force",
            "verificationStatus": "reviewed",
            "verificationConfidence": "high",
            "verifiedAt": "2569-09-20",
            "verifiedBy": "ตรวจทานกับตัวบทที่เก็บในคลัง",
            "statusBasis": "ข้อบังคับกำหนดวันใช้บังคับและมีข้อมูลประกาศในราชกิจจานุเบกษา",
            "gazette": "เล่ม 142 ตอนพิเศษ 257 ง วันที่ 30 กรกฎาคม 2568",
            "reformCode": "ก-3",
            "reformStatus": "done",
            "note": "ตรวจยืนยันเฉพาะสถานะและบทเลิกกฎหมายเดิม ควรตรวจต้นฉบับราชกิจจานุเบกษาก่อนใช้อ้างอิงในคดีหรือคำวินิจฉัย",
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
        "schemaVersion": 2,
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
