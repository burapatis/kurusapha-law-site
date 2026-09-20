#!/usr/bin/env python3
"""ย้ายไฟล์อ่อนไหวและสำเนาซ้ำออกจากคลัง โดยเก็บสำรองพร้อม manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path


SITE = Path(__file__).resolve().parents[1]
DOCUMENTS = SITE.parent.parent
ROOTS = [
    SITE.parent,
    DOCUMENTS / "กฎหมายหลัก",
    DOCUMENTS / "กฎหมายหลักการศึกษา",
]
SENSITIVE_RELATIVE_PATHS = {
    "10_แบบฟอร์มและสัญญา/ใบสมัครเข้ารับการสรรหาเพื่อแต่งตั้งให้ดำรงตำแหน่งเลขาธิการคุรุสภา.docx",
    "10_แบบฟอร์มและสัญญา/สัญญาจ้างรองเลขาธิการคุรุสภา พ.ศ. 2565 - หน้า 01.jpg",
    "10_แบบฟอร์มและสัญญา/สัญญาจ้างรองเลขาธิการคุรุสภา พ.ศ. 2565 - หน้า 02.jpg",
    "10_แบบฟอร์มและสัญญา/สัญญาจ้างรองเลขาธิการคุรุสภา พ.ศ. 2565 - หน้า 03.jpg",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover() -> list[tuple[int, Path, Path]]:
    files = []
    for root_index, root in enumerate(ROOTS):
        for path in root.rglob("*"):
            if not path.is_file() or SITE == path or SITE in path.parents:
                continue
            relative = path.relative_to(root)
            if any(part.startswith(".") for part in relative.parts):
                continue
            files.append((root_index, root, path))
    return files


def canonical_rank(item: tuple[int, Path, Path]) -> tuple:
    root_index, root, path = item
    relative = path.relative_to(root)
    name = path.name
    malformed_abbreviation = name.startswith("พ.ร.บ.") and not name.startswith("พ.ร.บ. ")
    leading_space_parts = sum(len(part) - len(part.lstrip()) for part in relative.parts)
    return (root_index, malformed_abbreviation, leading_space_parts, len(relative.as_posix()), relative.as_posix())


def build_plan() -> tuple[list[dict], list[dict]]:
    files = discover()
    by_hash: dict[str, list[tuple[int, Path, Path]]] = defaultdict(list)
    digests: dict[Path, str] = {}
    for item in files:
        path = item[2]
        digest = sha256(path)
        digests[path] = digest
        by_hash[digest].append(item)

    removals: list[dict] = []
    duplicate_groups: list[dict] = []
    sensitive_found = set()
    for _, root, path in files:
        relative = path.relative_to(root).as_posix()
        if root == ROOTS[0] and relative in SENSITIVE_RELATIVE_PATHS:
            sensitive_found.add(relative)
            removals.append({
                "original": str(path),
                "root": root.name,
                "relative": relative,
                "sha256": digests[path],
                "bytes": path.stat().st_size,
                "reason": "sensitive_personal_data",
                "canonicalKept": None,
            })

    sensitive_paths = {Path(item["original"]) for item in removals}
    for digest, group in sorted(by_hash.items()):
        if len(group) < 2:
            continue
        canonical = min(group, key=canonical_rank)
        kept_path = canonical[2]
        duplicate_groups.append({
            "sha256": digest,
            "canonicalKept": str(kept_path),
            "copies": len(group),
        })
        for _, root, path in group:
            if path == kept_path or path in sensitive_paths:
                continue
            removals.append({
                "original": str(path),
                "root": root.name,
                "relative": path.relative_to(root).as_posix(),
                "sha256": digest,
                "bytes": path.stat().st_size,
                "reason": "exact_duplicate",
                "canonicalKept": str(kept_path),
            })
    removals.sort(key=lambda item: (item["reason"], item["original"]))
    return removals, duplicate_groups


def destination_for(quarantine: Path, item: dict) -> Path:
    section = "removed-sensitive" if item["reason"] == "sensitive_personal_data" else "removed-duplicates"
    return quarantine / section / item["root"] / item["relative"]


def write_manifest(quarantine: Path, removals: list[dict], duplicate_groups: list[dict]) -> None:
    manifest = {
        "createdAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "mode": "recoverable_move",
        "summary": {
            "sensitiveFiles": sum(item["reason"] == "sensitive_personal_data" for item in removals),
            "duplicateCopies": sum(item["reason"] == "exact_duplicate" for item in removals),
            "duplicateGroups": len(duplicate_groups),
            "totalMoved": len(removals),
        },
        "duplicateGroups": duplicate_groups,
        "files": removals,
    }
    (quarantine / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    summary = manifest["summary"]
    readme = (
        "# บัญชีไฟล์ที่ย้ายออกจากคลังกฎหมาย\n\n"
        "การดำเนินการนี้เป็นการย้ายแบบกู้คืนได้ ไม่ใช่การลบทิ้งถาวร\n\n"
        f"- ไฟล์ข้อมูลส่วนบุคคล: {summary['sensitiveFiles']} ไฟล์\n"
        f"- สำเนาซ้ำแบบตรงกันทุกไบต์: {summary['duplicateCopies']} ไฟล์\n"
        f"- กลุ่มไฟล์ซ้ำ: {summary['duplicateGroups']} กลุ่ม\n"
        f"- รวมย้ายออก: {summary['totalMoved']} ไฟล์\n\n"
        "รายละเอียดพาธเดิม ลายนิ้วมือ SHA-256 และไฟล์หลักที่เก็บไว้ อยู่ใน `manifest.json`\n"
    )
    (quarantine / "README.md").write_text(readme, "utf-8")


def execute(quarantine: Path, removals: list[dict], duplicate_groups: list[dict]) -> None:
    if quarantine.exists():
        raise RuntimeError(f"โฟลเดอร์สำรองมีอยู่แล้ว: {quarantine}")
    quarantine.mkdir(parents=True)
    try:
        for item in removals:
            source = Path(item["original"])
            if not source.is_file() or sha256(source) != item["sha256"]:
                raise RuntimeError(f"ไฟล์เปลี่ยนแปลงระหว่างตรวจและย้าย: {source}")
            destination = destination_for(quarantine, item)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise RuntimeError(f"ปลายทางซ้ำ: {destination}")
            shutil.move(str(source), str(destination))
            item["quarantine"] = str(destination)
        write_manifest(quarantine, removals, duplicate_groups)
    except Exception:
        # ย้อนกลับไฟล์ที่ย้ายสำเร็จแล้ว หากกระบวนการไม่จบครบชุด
        for item in reversed(removals):
            destination = Path(item.get("quarantine", ""))
            source = Path(item["original"])
            if destination.is_file() and not source.exists():
                source.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(destination), str(source))
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="ย้ายจริง; หากไม่ระบุจะแสดงแผนเท่านั้น")
    parser.add_argument("--quarantine", type=Path, help="โฟลเดอร์สำรองนอกคลัง (จำเป็นเมื่อ --execute)")
    args = parser.parse_args()
    removals, duplicate_groups = build_plan()
    counts = {
        "sensitive": sum(item["reason"] == "sensitive_personal_data" for item in removals),
        "duplicateCopies": sum(item["reason"] == "exact_duplicate" for item in removals),
        "duplicateGroups": len(duplicate_groups),
        "total": len(removals),
    }
    print(json.dumps(counts, ensure_ascii=False, indent=2))
    if args.execute:
        if not args.quarantine:
            parser.error("ต้องระบุ --quarantine เมื่อใช้ --execute")
        quarantine = args.quarantine.expanduser().resolve()
        if any(quarantine == root or root in quarantine.parents for root in ROOTS):
            parser.error("โฟลเดอร์สำรองต้องอยู่นอกคลังต้นฉบับทั้งสาม")
        execute(quarantine, removals, duplicate_groups)
        print(f"ย้ายออกสำเร็จ {len(removals)} ไฟล์ ไปยัง {quarantine}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
