from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path


WORKFLOW_DIR = Path(__file__).resolve().parents[1]
DATASET_DIR = WORKFLOW_DIR.parent
BLIND_INDEX = DATASET_DIR / "final_selection_1800" / "human_review" / "blind_image_index.csv"
MANIFEST = DATASET_DIR / "final_selection_1800" / "final_selection_manifest.csv"
ADMIN_DIR = WORKFLOW_DIR / "admin"
BATCH_SIZE = 50


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    blind_rows = read_csv(BLIND_INDEX)
    manifest_rows = read_csv(MANIFEST)
    if len(blind_rows) != 1800 or len(manifest_rows) != 1800:
        raise ValueError("Expected exactly 1,800 rows in both inputs")

    manifest_by_sample = {row["sample_id"]: row for row in manifest_rows}
    if len(manifest_by_sample) != 1800:
        raise ValueError("sample_id is not unique in the final manifest")

    pilot_blind_rows = [
        row for row in blind_rows if manifest_by_sample[row["sample_id"]]["prior_pilot_sample_id"]
    ]
    production_blind_rows = [
        row for row in blind_rows if not manifest_by_sample[row["sample_id"]]["prior_pilot_sample_id"]
    ]
    if len(pilot_blind_rows) != 100:
        raise ValueError(f"Expected exactly 100 prior pilot images, found {len(pilot_blind_rows)}")
    ordered_blind_rows = pilot_blind_rows + production_blind_rows

    item_rows: list[dict[str, object]] = []
    summary_counts: dict[str, Counter[tuple[str, str]]] = defaultdict(Counter)
    seen_blind: set[str] = set()
    seen_sample: set[str] = set()

    for index, blind in enumerate(ordered_blind_rows):
        blind_id = blind["blind_id"]
        sample_id = blind["sample_id"]
        if blind_id in seen_blind or sample_id in seen_sample:
            raise ValueError(f"Duplicate blind or sample ID near {blind_id}")
        seen_blind.add(blind_id)
        seen_sample.add(sample_id)

        manifest = manifest_by_sample.get(sample_id)
        if manifest is None:
            raise ValueError(f"Missing sample in manifest: {sample_id}")
        if blind["source"] != manifest["source"] or blind["track"] != manifest["track"]:
            raise ValueError(f"Blind index mismatch for {sample_id}")

        batch_number = index // BATCH_SIZE + 1
        batch_id = f"B{batch_number:03d}"
        phase = "pilot" if batch_number <= 2 else "production"
        wave = "W0" if phase == "pilot" else f"W{((batch_number - 3) // 9) + 1}"
        item_rows.append(
            {
                "batch_id": batch_id,
                "phase": phase,
                "wave": wave,
                "position_in_batch": index % BATCH_SIZE + 1,
                "annotation_item_id": blind_id,
            }
        )
        summary_counts[batch_id][(manifest["source"], manifest["track"])] += 1

    write_csv(
        ADMIN_DIR / "batch_items.csv",
        ["batch_id", "phase", "wave", "position_in_batch", "annotation_item_id"],
        item_rows,
    )

    summary_rows: list[dict[str, object]] = []
    for batch_number in range(1, 37):
        batch_id = f"B{batch_number:03d}"
        counts = summary_counts[batch_id]
        summary_rows.append(
            {
                "batch_id": batch_id,
                "phase": "pilot" if batch_number <= 2 else "production",
                "wave": "W0" if batch_number <= 2 else f"W{((batch_number - 3) // 9) + 1}",
                "item_count": sum(counts.values()),
                "hl_positive": counts[("HL Dataset", "positive")],
                "hl_boundary": counts[("HL Dataset", "boundary")],
                "mm_positive": counts[("MM-MoralBench", "positive")],
                "haivmet_positive": counts[("HAIVMet", "positive")],
                "irfl_positive": counts[("IRFL", "positive")],
                "irfl_boundary": counts[("IRFL", "boundary")],
                "status": "blocked_by_G0",
            }
        )
    if any(row["item_count"] != 50 for row in summary_rows):
        raise ValueError("Every batch must contain exactly 50 data items")

    write_csv(
        ADMIN_DIR / "batch_summary.csv",
        [
            "batch_id",
            "phase",
            "wave",
            "item_count",
            "hl_positive",
            "hl_boundary",
            "mm_positive",
            "haivmet_positive",
            "irfl_positive",
            "irfl_boundary",
            "status",
        ],
        summary_rows,
    )
    print("Built 36 batches and validated 1,800 unique blind/sample mappings.")


if __name__ == "__main__":
    main()
