from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1]
V3_ROOT = WORKFLOW.parent
ITEM_DIR = WORKFLOW / "drafts" / "api_en" / "items"
BLIND_INDEX = V3_ROOT / "final_selection_1800" / "human_review" / "blind_image_index.csv"
AUDIT_DIR = V3_ROOT / "audit" / "annotation_quality_v1"
BACKUP_DIR = AUDIT_DIR / "original_items_before_repair"
REVISION_LOG = AUDIT_DIR / "PhiloVista-1800_repair_log.jsonl"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    with BLIND_INDEX.open(encoding="utf-8-sig", newline="") as handle:
        boundary_ids = {row["blind_id"] for row in csv.DictReader(handle) if row["track"] == "boundary"}

    timestamp = datetime.now(timezone.utc).isoformat()
    repaired = 0
    for item_id in sorted(boundary_ids):
        path = ITEM_DIR / f"{item_id}.json"
        original_bytes = path.read_bytes()
        record = json.loads(original_bytes.decode("utf-8"))
        interpretations = record.get("philosophy_interpretations", [])
        if len(interpretations) != 3 or any(entry.get("sufficiency") in {"insufficient", "not_applicable"} for entry in interpretations):
            continue

        backup_path = BACKUP_DIR / path.name
        if not backup_path.exists():
            shutil.copy2(path, backup_path)
        target = record["target_subject"].strip().rstrip(".")
        previous = interpretations[2]
        concepts = previous.get("concept_ids") or ["other_abstract_relation"]
        anchors = previous.get("visual_anchors") or [target]
        interpretations[2] = {
            "candidate_id": f"AI_{item_id}_P3",
            "visual_anchors": anchors[:3],
            "symbolic_mapping": [],
            "concept_ids": concepts[:2],
            "interpretation": f"A literal description of {target} is visually supported, but the image alone does not establish a specific philosophical claim; any determinate abstract meaning would require context outside the frame.",
            "alternative_interpretations": [f"A viewer may use {target} as a metaphor, but that association would be projected onto the scene rather than demonstrated by it."],
            "limitations": ["No explicit philosophical text, confirmed symbolic convention, or contextual metadata links the visible scene to one determinate abstract meaning."],
            "sufficiency": "insufficient",
        }
        record.setdefault("provenance", {}).setdefault("audit_revisions", []).append({
            "timestamp_utc": timestamp,
            "reason_code": "boundary_track_overinterpretation_guard",
            "changed_field": "philosophy_interpretations[2]",
            "previous_sufficiency": previous.get("sufficiency"),
            "source_backup": str(backup_path.relative_to(V3_ROOT)).replace("\\", "/"),
            "formal_gold": False,
        })
        new_bytes = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        temporary = path.with_suffix(".json.tmp")
        temporary.write_bytes(new_bytes)
        temporary.replace(path)
        with REVISION_LOG.open("a", encoding="utf-8", newline="") as handle:
            handle.write(json.dumps({
                "timestamp_utc": timestamp,
                "annotation_item_id": item_id,
                "reason": "Added an explicit insufficient-evidence reading to a boundary-track item whose three readings were all asserted as plausible.",
                "changed_fields": ["philosophy_interpretations[2]", "provenance.audit_revisions"],
                "original_sha256": sha256(original_bytes),
                "revised_sha256": sha256(new_bytes),
                "backup": str(backup_path.relative_to(V3_ROOT)).replace("\\", "/"),
            }, ensure_ascii=False) + "\n")
        repaired += 1
        print(json.dumps({"event": "boundary_repaired", "annotation_item_id": item_id}, ensure_ascii=False))
    print(json.dumps({"event": "complete", "repaired_items": repaired}, ensure_ascii=False))


if __name__ == "__main__":
    main()
