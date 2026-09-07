from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1]
ITEM_DIR = WORKFLOW / "drafts" / "ai_en" / "items"
EXPORT_DIR = WORKFLOW / "drafts" / "ai_en" / "exports"
BATCH_ITEMS = WORKFLOW / "admin" / "batch_items.csv"
SEPARATOR = "；"
COLUMNS = ["图片文件名", "Scene场景描述", "Action动作描述", "Rationale理由描述", "Object物体描述"]
AXIS_COUNTS = {"scene": 3, "action": 3, "rationale": 3, "object": 5}
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def load_expected() -> list[str]:
    with BATCH_ITEMS.open(encoding="utf-8-sig", newline="") as handle:
        return [row["annotation_item_id"] for row in csv.DictReader(handle)]


def main() -> None:
    expected = load_expected()
    records = []
    errors: list[str] = []
    warnings: list[str] = []
    for blind_id in expected:
        path = ITEM_DIR / f"{blind_id}.json"
        if not path.is_file():
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except Exception as error:
            errors.append(f"{blind_id}: unreadable JSON: {error}")
            continue
        if record.get("annotation_item_id") != blind_id:
            errors.append(f"{blind_id}: annotation_item_id mismatch")
        if record.get("language") != "en":
            errors.append(f"{blind_id}: language is not en")
        if record.get("formal_gold") is not False:
            errors.append(f"{blind_id}: formal_gold must be false")
        captions = record.get("captions", {})
        for axis, count in AXIS_COUNTS.items():
            values = captions.get(axis)
            if not isinstance(values, list) or len(values) != count:
                errors.append(f"{blind_id}.{axis}: expected {count} references")
                continue
            for index, value in enumerate(values, 1):
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{blind_id}.{axis}[{index}]: empty")
                elif SEPARATOR in value:
                    errors.append(f"{blind_id}.{axis}[{index}]: contains separator")
                elif CJK_RE.search(value):
                    errors.append(f"{blind_id}.{axis}[{index}]: contains CJK")
            normalized = [re.sub(r"\W+", "", value.lower()) for value in values if isinstance(value, str)]
            if len(set(normalized)) != len(normalized):
                errors.append(f"{blind_id}.{axis}: duplicate references")
        phils = record.get("philosophy_interpretations")
        if not isinstance(phils, list) or len(phils) != 3:
            errors.append(f"{blind_id}: expected 3 philosophy interpretations")
        records.append(record)

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    with (EXPORT_DIR / "all_english_ai_draft_hl.jsonl").open("w", encoding="utf-8", newline="") as handle:
        for record in records:
            handle.write(json.dumps({"file_name": record["file_name"], "captions": record["captions"]}, ensure_ascii=False) + "\n")

    with (EXPORT_DIR / "all_english_ai_draft_HL_five_columns.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
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

    with (EXPORT_DIR / "all_english_ai_draft_philosophy.jsonl").open("w", encoding="utf-8", newline="") as handle:
        for record in records:
            handle.write(json.dumps({
                "annotation_item_id": record["annotation_item_id"],
                "file_name": record["file_name"],
                "method": record["method"],
                "target_subject": record["target_subject"],
                "text_dependency": record["text_dependency"],
                "interpretations": record["philosophy_interpretations"],
                "needs_independent_human_annotation": True,
                "needs_independent_human_rating": True,
            }, ensure_ascii=False) + "\n")

    report = {
        "scope": "all_1800_images_english_ai_draft",
        "language": "en",
        "expected_records": len(expected),
        "exported_records": len(records),
        "missing_records": len(expected) - len(records),
        "formal_gold": False,
        "independent_human_generation_complete": False,
        "independent_confidence_rating_complete": False,
        "errors": errors,
        "warnings": warnings,
        "batch_distribution": dict(Counter(record["batch_id"] for record in records)),
        "status": "complete_ai_draft_pending_human_review" if len(records) == len(expected) and not errors else "partial_or_invalid_ai_draft",
    }
    (EXPORT_DIR / "all_english_ai_draft_validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
