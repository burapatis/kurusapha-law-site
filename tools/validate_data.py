#!/usr/bin/env python3
"""ตรวจความสอดคล้องของข้อมูลและลิงก์ภายในก่อนเผยแพร่."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ERRORS: list[str] = []
WARNINGS: list[str] = []
ALLOWED_STATUSES = {"unverified", "in_force", "amended", "repealed", "reference", "draft"}
ALLOWED_VERIFICATION = {"unverified", "partial", "reviewed"}
ALLOWED_EVIDENCE = {"local_file", "local_reviewed", "official_online"}
INTERNAL_MARKERS = ("ร่างต้นแบบ", "บันทึกตรวจสอบ", "แผนแม่บทการสร้างเว็บไซต์", "รายงานความเห็นทางกฎหมาย")


def error(message: str) -> None:
    ERRORS.append(message)


def warning(message: str) -> None:
    WARNINGS.append(message)


def load_json(path: Path):
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception as exc:  # รายงานทุกไฟล์ในรอบเดียว
        error(f"{path.relative_to(ROOT)}: JSON ไม่ถูกต้อง: {exc}")
        return None


def validate_json_files() -> None:
    for path in sorted(DATA.rglob("*.json")):
        load_json(path)
        if "/Users/" in path.read_text("utf-8", errors="replace"):
            error(f"{path.relative_to(ROOT)}: พบพาธภายในเครื่องในข้อมูลสาธารณะ")


def validate_catalog() -> None:
    catalog = load_json(DATA / "catalog.json")
    coverage = load_json(DATA / "coverage.json")
    search = load_json(DATA / "search-index.json")
    if not all((catalog, coverage, search)):
        return
    items = catalog.get("items", [])
    ids = [item.get("id") for item in items]
    duplicates = [key for key, count in Counter(ids).items() if count > 1]
    if duplicates:
        error(f"catalog.json: id ซ้ำ {duplicates}")
    if catalog.get("meta", {}).get("count") != len(items):
        error("catalog.json: meta.count ไม่ตรงจำนวน items")
    if coverage.get("total") != len(items):
        error("coverage.json: total ไม่ตรงจำนวน catalog")

    seen_hashes: dict[str, str] = {}
    for item in items:
        label = f"{item.get('id')} {item.get('title')}"
        if any(marker in item.get("title", "") for marker in INTERNAL_MARKERS):
            error(f"{label}: ชื่อบ่งชี้ว่าเป็นร่าง/เอกสารภายใน")
        if item.get("status") not in ALLOWED_STATUSES:
            error(f"{label}: status ไม่รู้จัก")
        if item.get("verificationStatus") not in ALLOWED_VERIFICATION:
            error(f"{label}: verificationStatus ไม่รู้จัก")
        if item.get("evidenceLevel") not in ALLOWED_EVIDENCE:
            error(f"{label}: evidenceLevel ไม่รู้จัก")
        if not item.get("localCopyAvailable"):
            error(f"{label}: ไม่มีตัวบ่งชี้สำเนาในคลัง")
        if item.get("audience") != "public" or item.get("isDeliverable"):
            error(f"{label}: มีเอกสารภายในปะปนในแคตตาล็อกสาธารณะ")
        if item.get("status") in {"in_force", "amended", "repealed"}:
            if item.get("verificationStatus") != "reviewed":
                error(f"{label}: สถานะทางกฎหมายที่ยืนยันแล้วต้องมี verificationStatus=reviewed")
            if not item.get("statusBasis") or not item.get("verifiedAt") or not item.get("verifiedBy"):
                error(f"{label}: ขาดเหตุผล/วัน/ผู้ตรวจสถานะ")
        sources = item.get("sources") or []
        if not sources:
            error(f"{label}: ไม่มี sources")
        for source in sources:
            digest = source.get("sha256", "")
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                error(f"{label}: SHA-256 ไม่ถูกต้อง")
            elif digest in seen_hashes and seen_hashes[digest] != item.get("id"):
                error(f"{label}: ไฟล์ซ้ำยังแยกเป็นคนละรายการกับ {seen_hashes[digest]}")
            else:
                seen_hashes[digest] = item.get("id")
        official_url = (item.get("officialUrl") or "").rstrip("/")
        if official_url == "https://ratchakitcha.soc.go.th":
            error(f"{label}: officialUrl เป็นเพียงหน้าแรก ไม่ใช่ลิงก์ตรงของฉบับ")
        if item.get("evidenceLevel") == "official_online" and not item.get("officialUrl"):
            error(f"{label}: ระบุว่าพบแหล่งทางการออนไลน์แต่ไม่มี officialUrl")
        public_copy = item.get("publicCopyUrl")
        if public_copy:
            copy_path = (ROOT / public_copy).resolve()
            if not copy_path.is_relative_to(ROOT) or not copy_path.is_file():
                error(f"{label}: publicCopyUrl ไม่พบไฟล์หรือออกนอกเว็บไซต์")
        text_path = DATA / "text" / f"{item.get('id')}.txt"
        if item.get("hasText") and not text_path.exists():
            error(f"{label}: hasText=true แต่ไม่มีไฟล์ข้อความ")
        if not item.get("publicFulltext", True) and text_path.exists():
            error(f"{label}: ห้ามเผยแพร่ full text แต่ยังมีไฟล์ข้อความ")

    catalog_ids = set(ids)
    search_ids = [item.get("id") for item in search.get("items", [])]
    if len(search_ids) != len(set(search_ids)):
        error("search-index.json: id ซ้ำ")
    unknown_search = set(search_ids) - catalog_ids
    if unknown_search:
        error(f"search-index.json: มี id ที่ไม่อยู่ใน catalog {sorted(unknown_search)}")
    expected_search = {item["id"] for item in items if item.get("hasText")}
    if set(search_ids) != expected_search:
        error("search-index.json: รายการไม่ตรงกับ catalog ที่ hasText=true")

    text_ids = {path.stem for path in (DATA / "text").glob("*.txt")}
    orphans = text_ids - catalog_ids
    if orphans:
        error(f"data/text: มีไฟล์กำพร้า {sorted(orphans)}")

    by_status = dict(Counter(item["status"] for item in items))
    if coverage.get("byStatus") != dict(sorted(by_status.items())):
        error("coverage.json: byStatus ไม่ตรงกับ catalog")


def validate_internal_links() -> None:
    pages = list(ROOT.glob("*.html"))
    known = {path.name for path in pages}
    known.update({"assets/css/style.css", "assets/js/app.js", "assets/favicon.svg"})
    for page in pages:
        text = page.read_text("utf-8")
        for target in re.findall(r'(?:href|src)="([^"]+)"', text):
            clean = target.split("?", 1)[0].split("#", 1)[0]
            if not clean or clean.startswith(("http://", "https://", "mailto:")):
                continue
            if clean not in known and not (ROOT / clean).exists():
                error(f"{page.name}: ลิงก์ภายในไม่พบ {target}")


def main() -> int:
    validate_json_files()
    validate_catalog()
    validate_internal_links()
    for message in WARNINGS:
        print(f"WARNING: {message}")
    for message in ERRORS:
        print(f"ERROR: {message}")
    if ERRORS:
        print(f"ไม่ผ่าน: {len(ERRORS)} ข้อผิดพลาด")
        return 1
    print("ผ่าน: JSON, แคตตาล็อก, ดัชนีข้อความ และลิงก์ภายในสอดคล้องกัน")
    return 0


if __name__ == "__main__":
    sys.exit(main())
