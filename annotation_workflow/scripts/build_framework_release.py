from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / "annotation_workflow"
ITEM_DIR = WORKFLOW / "drafts" / "api_en" / "items"
MANIFEST = ROOT / "final_selection_1800" / "final_selection_manifest.csv"
BLIND_INDEX = ROOT / "final_selection_1800" / "human_review" / "blind_image_index.csv"
CROSSWALK = WORKFLOW / "resources" / "legacy_axis_crosswalk.json"
ONTOLOGY_VERSION = "formal-632-20260909"
TARGETS = {"calibration": 180, "dev": 180, "test": 1440}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build framework-aligned PhiloVista-1800 release artifacts.")
    parser.add_argument(
        "--ontology-csv",
        type=Path,
        default=ROOT / "ontology" / "philosophical_image_label_system_formal_632.csv",
        help="Formal CSV; defaults to the version included in this repository.",
    )
    parser.add_argument("--seed", default="philovista-1800-split-v1")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_key(seed: str, value: str) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode()).hexdigest()


def load_ontology(path: Path) -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
    rows = read_csv(path)
    required = {
        "Concept ID", "Philosophical Concept", "Macro Dimension", "Visual Inferability",
        "Temporal Requirement", "Grounding Rule", "Ontology Status",
    }
    if len(rows) != 632 or not rows or not required <= rows[0].keys():
        raise ValueError("Formal ontology must contain 632 rows and all required columns.")
    by_id = {row["Concept ID"]: row for row in rows}
    if len(by_id) != 632 or any(not concept_id.startswith("PHC-") for concept_id in by_id):
        raise ValueError("Formal ontology Concept IDs must be 632 unique PHC IDs.")
    return rows, by_id


def load_crosswalk(ontology: dict[str, dict[str, str]]) -> tuple[dict[str, list[str]], str]:
    data = json.loads(CROSSWALK.read_text(encoding="utf-8"))
    axes = data["axes"]
    expected_axes = {
        "choice_journey", "ethics_responsibility", "faith_meaning", "freedom_constraint",
        "identity_appearance", "knowledge_truth", "labor_technology", "other_abstract_relation",
        "power_conflict", "social_existence", "time_mortality",
    }
    if set(axes) != expected_axes:
        raise ValueError("Crosswalk must cover exactly the 11 legacy axes.")
    mapped: dict[str, list[str]] = {}
    for axis, candidates in axes.items():
        ids = [candidate["concept_id"] for candidate in candidates]
        if len(ids) != len(set(ids)) or any(concept_id not in ontology for concept_id in ids):
            raise ValueError(f"{axis}: duplicate or unknown formal concept candidate.")
        for candidate in candidates:
            official_name = ontology[candidate["concept_id"]]["Philosophical Concept"]
            if candidate["concept"] != official_name:
                raise ValueError(f"{candidate['concept_id']}: crosswalk name differs from ontology.")
        mapped[axis] = ids
    return mapped, data["crosswalk_version"]


def assign_splits(rows: list[dict[str, str]], seed: str) -> dict[str, str]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row["group_id"]].append(row)
    ordered = sorted(groups.items(), key=lambda item: (-len(item[1]), stable_key(seed, item[0])))
    counts = Counter()
    assignments: dict[str, str] = {}
    for group_id, members in ordered:
        size = len(members)
        eligible = [split for split, target in TARGETS.items() if counts[split] + size <= target]
        if not eligible:
            raise ValueError(f"Cannot place group {group_id!r} of size {size} within split targets.")
        split = min(eligible, key=lambda name: ((counts[name] + size) / TARGETS[name], stable_key(seed, f"{group_id}:{name}")))
        assignments[group_id] = split
        counts[split] += size
    if dict(counts) != TARGETS:
        raise ValueError(f"Split counts differ from targets: {dict(counts)}")
    return assignments


def write_splits(rows: list[dict[str, str]], assignments: dict[str, str]) -> tuple[Path, dict[str, dict[str, int]]]:
    out = ROOT / "splits" / "benchmark_splits.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["sample_id", "split", "group_id", "source", "track"]
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in sorted(rows, key=lambda item: item["sample_id"]):
            writer.writerow({**{field: row[field] for field in fields if field != "split"}, "split": assignments[row["group_id"]]})
    distribution: dict[str, dict[str, int]] = {}
    for split in TARGETS:
        subset = [row for row in rows if assignments[row["group_id"]] == split]
        distribution[split] = {
            "total": len(subset),
            **{f"source:{key}": value for key, value in sorted(Counter(row["source"] for row in subset).items())},
            **{f"track:{key}": value for key, value in sorted(Counter(row["track"] for row in subset).items())},
        }
    return out, distribution


def build_sidecar(
    manifest_rows: list[dict[str, str]],
    ontology: dict[str, dict[str, str]],
    ontology_hash: str,
    crosswalk: dict[str, list[str]],
) -> tuple[Path, dict[str, object]]:
    manifest_by_sample = {row["sample_id"]: row for row in manifest_rows}
    blind_rows = read_csv(BLIND_INDEX)
    if len(blind_rows) != 1800 or len(manifest_by_sample) != 1800:
        raise ValueError("Manifest and blind index must each contain 1,800 unique samples.")
    output_rows = []
    legacy_counts: Counter[str] = Counter()
    candidate_counts: Counter[str] = Counter()
    review_verdicts: Counter[str] = Counter()
    framework_visual_repairs: list[str] = []
    for blind in sorted(blind_rows, key=lambda row: row["blind_id"]):
        record = json.loads((ITEM_DIR / f"{blind['blind_id']}.json").read_text(encoding="utf-8"))
        manifest = manifest_by_sample[record["sample_id"]]
        review_verdicts[record.get("review", {}).get("verdict", "missing")] += 1
        if record.get("review", {}).get("resolution", {}).get("checked_by") == "codex_framework_alignment_20260909":
            framework_visual_repairs.append(record["annotation_item_id"])
        interpretations = []
        for source in record["philosophy_interpretations"]:
            legacy_ids = source["concept_ids"]
            if any(axis not in crosswalk for axis in legacy_ids):
                raise ValueError(f"{blind['blind_id']}: unknown legacy axis.")
            candidates = list(dict.fromkeys(concept_id for axis in legacy_ids for concept_id in crosswalk[axis]))
            legacy_counts.update(legacy_ids)
            candidate_counts.update(candidates)
            interpretations.append({
                "candidate_id": source["candidate_id"],
                "visual_anchors": source["visual_anchors"],
                "symbolic_mapping": source["symbolic_mapping"],
                "legacy_axis_ids": legacy_ids,
                "formal_concept_candidates": candidates,
                "concept_claims": [],
                "interpretation": source["interpretation"],
                "alternative_interpretations": source["alternative_interpretations"],
                "limitations": source["limitations"],
                "sufficiency": source["sufficiency"],
            })
        output_rows.append({
            "annotation_item_id": record["annotation_item_id"],
            "sample_id": record["sample_id"],
            "file_name": record["file_name"],
            "track": manifest["track"],
            "benchmark_axis_id": manifest["philosophical_axis"],
            "ontology_version": ONTOLOGY_VERSION,
            "ontology_sha256": ontology_hash,
            "annotation_source": {
                "kind": "reviewed_ai_draft",
                "method": record["method"],
                "review_verdict": record.get("review", {}).get("verdict", "missing"),
            },
            "formal_gold": False,
            "mapping_status": "pending_independent_human_mapping",
            "needs_independent_human_annotation": True,
            "needs_independent_human_rating": True,
            "interpretations": interpretations,
        })
    if len(output_rows) != 1800 or any(interp["concept_claims"] for row in output_rows for interp in row["interpretations"]):
        raise ValueError("Framework sidecar must keep all formal concept claims empty until human review.")
    out = WORKFLOW / "drafts" / "api_en" / "exports" / "PhiloVista-1800_framework.jsonl"
    out.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in output_rows), encoding="utf-8")
    stats = {
        "records": len(output_rows),
        "interpretations": sum(len(row["interpretations"]) for row in output_rows),
        "formal_concept_claims": 0,
        "distinct_legacy_axes": len(legacy_counts),
        "distinct_formal_candidates": len(candidate_counts),
        "not_image_decidable_candidate_mentions": sum(
            count for concept_id, count in candidate_counts.items()
            if ontology[concept_id]["Visual Inferability"] == "not_image_decidable"
        ),
        "review_verdicts": dict(sorted(review_verdicts.items())),
        "framework_visual_repairs": sorted(framework_visual_repairs),
    }
    return out, stats


def main() -> None:
    args = parse_args()
    ontology_rows, ontology = load_ontology(args.ontology_csv)
    crosswalk, crosswalk_version = load_crosswalk(ontology)
    ontology_hash = sha256(args.ontology_csv)

    ontology_dir = ROOT / "ontology"
    ontology_dir.mkdir(exist_ok=True)
    ontology_copy = ontology_dir / "philosophical_image_label_system_formal_632.csv"
    if args.ontology_csv.resolve() != ontology_copy.resolve():
        shutil.copyfile(args.ontology_csv, ontology_copy)
    lock = {
        "ontology_version": ONTOLOGY_VERSION,
        "rows": len(ontology_rows),
        "sha256": ontology_hash,
        "macro_dimensions": dict(sorted(Counter(row["Macro Dimension"] for row in ontology_rows).items())),
        "visual_inferability": dict(sorted(Counter(row["Visual Inferability"] for row in ontology_rows).items())),
        "temporal_requirement": dict(sorted(Counter(row["Temporal Requirement"] for row in ontology_rows).items())),
        "ontology_status": dict(sorted(Counter(row["Ontology Status"] for row in ontology_rows).items())),
    }
    lock_path = ontology_dir / "formal_632.lock.json"
    lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest_rows = read_csv(MANIFEST)
    if len(manifest_rows) != 1800 or len({row["sample_id"] for row in manifest_rows}) != 1800:
        raise ValueError("Release manifest must contain 1,800 unique sample IDs.")
    assignments = assign_splits(manifest_rows, args.seed)
    split_path, split_distribution = write_splits(manifest_rows, assignments)
    sidecar_path, sidecar_stats = build_sidecar(manifest_rows, ontology, ontology_hash, crosswalk)

    report = {
        "framework_version": "2026-09-09",
        "status": "framework_aligned_ai_preview_pending_human_gold",
        "ontology": lock,
        "crosswalk_version": crosswalk_version,
        "crosswalk_policy": "candidate_retrieval_only",
        "split_seed": args.seed,
        "sidecar": sidecar_stats,
        "splits": split_distribution,
        "checks": {
            "ontology_ids_unique": True,
            "crosswalk_ids_exist_in_ontology": True,
            "legacy_axes_separated_from_formal_concepts": True,
            "formal_claims_not_mechanically_inferred": True,
            "group_ids_cross_splits": 0,
            "split_counts_match_targets": True,
        },
        "artifacts": {
            "ontology_csv": str(ontology_copy.relative_to(ROOT)).replace("\\", "/"),
            "ontology_lock": str(lock_path.relative_to(ROOT)).replace("\\", "/"),
            "framework_sidecar": str(sidecar_path.relative_to(ROOT)).replace("\\", "/"),
            "splits": str(split_path.relative_to(ROOT)).replace("\\", "/"),
        },
        "limitations": [
            "All 1,800 records remain AI drafts with formal_gold=false.",
            "Formal concept candidates are retrieval aids, not PHC labels or gold answers.",
            "Independent per-image PHC mapping, rating, and adjudication remain required.",
        ],
    }
    report_dir = ROOT / "audit" / "framework_alignment_20260909"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "framework_alignment_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
