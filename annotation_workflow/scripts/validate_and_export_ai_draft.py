from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1]
SOURCE = WORKFLOW / "drafts" / "ai" / "B001_micro_pilot_10.source.json"
POOL = WORKFLOW / "blind_pool" / "pilot"
OUT_DIR = WORKFLOW / "drafts" / "ai" / "exports"
SEPARATOR = "；"
AXIS_COUNTS = {"scene": 3, "action": 3, "rationale": 3, "object": 5}
CONCEPTS = {
    "ethics_responsibility", "time_mortality", "social_existence",
    "identity_appearance", "knowledge_truth", "power_conflict",
    "choice_journey", "labor_technology", "freedom_constraint",
    "faith_meaning", "other_abstract_relation",
}


def main() -> None:
    records = json.loads(SOURCE.read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []
    ids = [record.get("annotation_item_id") for record in records]
    if len(records) != 10:
        errors.append(f"expected 10 records, found {len(records)}")
    if len(set(ids)) != len(ids):
        errors.append("duplicate annotation_item_id")

    image_names: dict[str, str] = {}
    for record in records:
        item_id = record.get("annotation_item_id", "")
        matches = list(POOL.glob(f"{item_id}.*"))
        if len(matches) != 1:
            errors.append(f"{item_id}: expected one blind image, found {len(matches)}")
        else:
            image_names[item_id] = matches[0].name
        captions = record.get("captions", {})
        all_texts: list[str] = []
        for axis, expected in AXIS_COUNTS.items():
            values = captions.get(axis)
            if not isinstance(values, list) or len(values) != expected:
                errors.append(f"{item_id}.{axis}: expected {expected} strings")
                continue
            for index, value in enumerate(values, 1):
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{item_id}.{axis}[{index}]: empty or non-string")
                elif SEPARATOR in value:
                    errors.append(f"{item_id}.{axis}[{index}]: contains forbidden separator")
                all_texts.append(value.strip() if isinstance(value, str) else "")
            normalized = ["".join(v.lower().split()) for v in values if isinstance(v, str)]
            if len(set(normalized)) != len(normalized):
                warnings.append(f"{item_id}.{axis}: normalized duplicate reference")
        if len(set(all_texts)) != len(all_texts):
            warnings.append(f"{item_id}: exact text reused across axes")
        supports = record.get("rationale_support")
        if not isinstance(supports, list) or len(supports) != 3:
            errors.append(f"{item_id}.rationale_support: expected 3 values")
        phils = record.get("philosophy_interpretations")
        if not isinstance(phils, list) or len(phils) != 3:
            errors.append(f"{item_id}.philosophy_interpretations: expected 3 values")
            continue
        for pindex, phil in enumerate(phils, 1):
            if not phil.get("visual_anchors"):
                errors.append(f"{item_id}.philosophy[{pindex}]: no visual anchors")
            if not phil.get("limitations"):
                errors.append(f"{item_id}.philosophy[{pindex}]: no limitations")
            unknown = set(phil.get("concept_ids", [])) - CONCEPTS
            if unknown:
                errors.append(f"{item_id}.philosophy[{pindex}]: unknown concepts {sorted(unknown)}")
            if phil.get("sufficiency") not in {"supported", "plausible", "insufficient", "not_applicable"}:
                errors.append(f"{item_id}.philosophy[{pindex}]: invalid sufficiency")

    report = {
        "batch_id": "B001",
        "scope": "first_10_items_ai_draft",
        "record_count": len(records),
        "method": "single_model_visual_review_ai_draft",
        "formal_gold": False,
        "independent_human_generation_complete": False,
        "independent_confidence_rating_complete": False,
        "errors": errors,
        "warnings": warnings,
        "axis_reference_totals": {
            axis: len(records) * count for axis, count in AXIS_COUNTS.items()
        },
        "philosophy_candidate_total": len(records) * 3,
        "text_dependency_distribution": dict(Counter(r["text_dependency"] for r in records)),
        "status": "valid_ai_draft_pending_human_G0_and_independent_annotation" if not errors else "invalid",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "B001_micro_pilot_10_validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if errors:
        raise SystemExit("Validation failed:\n" + "\n".join(errors))

    with (OUT_DIR / "B001_micro_pilot_10_hl_draft.jsonl").open("w", encoding="utf-8", newline="") as h:
        for record in records:
            release_core = {
                "file_name": image_names[record["annotation_item_id"]],
                "captions": record["captions"],
            }
            h.write(json.dumps(release_core, ensure_ascii=False) + "\n")

    columns = ["图片文件名", "Scene场景描述", "Action动作描述", "Rationale理由描述", "Object物体描述"]
    with (OUT_DIR / "B001_micro_pilot_10_HL五列草稿.csv").open("w", encoding="utf-8", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for record in records:
            captions = record["captions"]
            writer.writerow({
                columns[0]: image_names[record["annotation_item_id"]],
                columns[1]: SEPARATOR.join(captions["scene"]),
                columns[2]: SEPARATOR.join(captions["action"]),
                columns[3]: SEPARATOR.join(captions["rationale"]),
                columns[4]: SEPARATOR.join(captions["object"]),
            })

    with (OUT_DIR / "B001_micro_pilot_10_philosophy_draft.jsonl").open("w", encoding="utf-8", newline="") as h:
        for record in records:
            sidecar = {
                "annotation_item_id": record["annotation_item_id"],
                "file_name": image_names[record["annotation_item_id"]],
                "method": "ai_draft_single_model_non_independent",
                "target_subject": record["target_subject"],
                "text_dependency": record["text_dependency"],
                "interpretations": record["philosophy_interpretations"],
                "needs_independent_human_annotation": True,
                "needs_independent_human_rating": True,
            }
            h.write(json.dumps(sidecar, ensure_ascii=False) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

