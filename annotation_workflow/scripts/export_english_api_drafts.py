from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter
from pathlib import Path

import generate_all_english_ai_drafts as schema


WORKFLOW = Path(__file__).resolve().parents[1]
ITEM_DIR = WORKFLOW / "drafts" / "api_en" / "items"
EXPORT_DIR = WORKFLOW / "drafts" / "api_en" / "exports"
BATCH_ITEMS = WORKFLOW / "admin" / "batch_items.csv"
SEPARATOR = "；"
COLUMNS = ["图片文件名", "Scene场景描述", "Action动作描述", "Rationale理由描述", "Object物体描述"]
AXIS_COUNTS = {"scene": 3, "action": 3, "rationale": 3, "object": 5}
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
DATASET_NAME = "PhiloVista-1800"
HL_JSONL_NAME = f"{DATASET_NAME}_HL.jsonl"
HL_CSV_NAME = f"{DATASET_NAME}_HL.csv"
PHILOSOPHY_JSONL_NAME = f"{DATASET_NAME}_philosophy.jsonl"
VALIDATION_REPORT_NAME = f"{DATASET_NAME}_validation_report.json"


def write_atomic(path: Path, text: str, encoding: str = "utf-8") -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding=encoding, newline="")
    temporary.replace(path)


def main() -> None:
    with BATCH_ITEMS.open(encoding="utf-8-sig", newline="") as handle:
        batch_rows = list(csv.DictReader(handle))
    expected = [row["annotation_item_id"] for row in batch_rows]
    batch_by_id = {row["annotation_item_id"]: row for row in batch_rows}
    with schema.MANIFEST.open(encoding="utf-8-sig", newline="") as handle:
        blind_by_id = {row["blind_id"]: row for row in csv.DictReader(handle)}
    records: list[dict] = []
    errors: list[str] = []
    seen_files: set[str] = set()
    for blind_id in expected:
        path = ITEM_DIR / f"{blind_id}.json"
        if not path.is_file():
            errors.append(f"{blind_id}: missing item file")
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            batch = batch_by_id[blind_id]
            blind = blind_by_id[blind_id]
            image_path = schema.V3_ROOT / Path(blind["selected_path"])
            expected_item = {
                "blind_id": blind_id,
                "sample_id": blind["sample_id"],
                "file_name": image_path.name,
                "batch_id": batch["batch_id"],
                "position_in_batch": batch["position_in_batch"],
            }
            schema.validate_and_normalize(record, expected_item)
            captions = record["captions"]
            if record.get("annotation_item_id") != blind_id or record.get("sample_id") != blind["sample_id"] or record.get("file_name") != image_path.name:
                errors.append(f"{blind_id}: ID or image mapping mismatch")
            if record.get("language") != "en" or record.get("formal_gold") is not False or record.get("needs_independent_human_annotation") is not True or record.get("needs_independent_human_rating") is not True:
                errors.append(f"{blind_id}: invalid language or gold status")
            if record["file_name"] in seen_files:
                errors.append(f"{blind_id}: duplicate file_name")
            seen_files.add(record["file_name"])
            for axis, count in AXIS_COUNTS.items():
                values = captions.get(axis)
                if not isinstance(values, list) or len(values) != count:
                    errors.append(f"{blind_id}.{axis}: expected {count}")
                elif any(not isinstance(value, str) or not value.strip() or SEPARATOR in value or CJK_RE.search(value) for value in values):
                    errors.append(f"{blind_id}.{axis}: invalid English reference")
            if len(record.get("philosophy_interpretations", [])) != 3:
                errors.append(f"{blind_id}: expected 3 philosophy interpretations")
            free_text = schema.walk_strings({
                "target_subject": record.get("target_subject"),
                "captions": record.get("captions"),
                "philosophy_interpretations": record.get("philosophy_interpretations"),
            })
            if any(CJK_RE.search(text) or SEPARATOR in text for text in free_text):
                errors.append(f"{blind_id}: invalid English free text or forbidden separator")
            records.append(record)
        except Exception as error:
            errors.append(f"{blind_id}: {error}")

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    if len(records) != len(expected):
        errors.append(f"dataset: expected {len(expected)} valid records, found {len(records)}")

    hl_lines = [json.dumps({"file_name": record["file_name"], "captions": record["captions"]}, ensure_ascii=False) for record in records]
    philosophy_lines = [
        json.dumps({
                "annotation_item_id": record["annotation_item_id"],
                "file_name": record["file_name"],
                "method": record["method"],
                "target_subject": record["target_subject"],
                "text_dependency": record["text_dependency"],
                "interpretations": record["philosophy_interpretations"],
                "review": record.get("review", {}),
                "needs_independent_human_annotation": True,
                "needs_independent_human_rating": True,
        }, ensure_ascii=False)
        for record in records
    ]
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    for record in records:
        captions = record["captions"]
        writer.writerow({
            COLUMNS[0]: record["file_name"],
            COLUMNS[1]: SEPARATOR.join(captions["scene"]),
            COLUMNS[2]: SEPARATOR.join(captions["action"]),
            COLUMNS[3]: SEPARATOR.join(captions["rationale"]),
            COLUMNS[4]: SEPARATOR.join(captions["object"]),
        })

    # Verify the in-memory CSV before any existing export is replaced.
    roundtrip_rows = list(csv.DictReader(io.StringIO(csv_buffer.getvalue(), newline="")))
    for record, row in zip(records, roundtrip_rows, strict=True):
        for column, axis in zip(COLUMNS[1:], AXIS_COUNTS, strict=True):
            if row[column].split(SEPARATOR) != record["captions"][axis]:
                errors.append(f"{record['annotation_item_id']}.{axis}: in-memory CSV round-trip mismatch")

    report = {
        "dataset": DATASET_NAME,
        "scope": "all_1800_images_reviewed_english_ai_draft",
        "expected_records": len(expected),
        "exported_records": len(records),
        "missing_records": len(expected) - len(records),
        "formal_gold": False,
        "errors": errors,
        "method_distribution": dict(Counter(record.get("method", "missing") for record in records)),
        "review_verdicts": dict(Counter(record.get("review", {}).get("verdict", "missing") for record in records)),
        "batch_distribution": dict(Counter(record["batch_id"] for record in records)),
        "status": "complete_ai_draft_pending_independent_human_annotation_and_rating" if len(records) == len(expected) and not errors else "partial_or_invalid_ai_draft",
    }
    write_atomic(EXPORT_DIR / VALIDATION_REPORT_NAME, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(2)

    write_atomic(EXPORT_DIR / HL_JSONL_NAME, "\n".join(hl_lines) + "\n")
    write_atomic(EXPORT_DIR / HL_CSV_NAME, csv_buffer.getvalue(), encoding="utf-8-sig")
    write_atomic(EXPORT_DIR / PHILOSOPHY_JSONL_NAME, "\n".join(philosophy_lines) + "\n")


if __name__ == "__main__":
    main()
