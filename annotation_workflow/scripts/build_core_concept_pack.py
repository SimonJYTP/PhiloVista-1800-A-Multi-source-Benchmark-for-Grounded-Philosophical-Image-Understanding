"""Build the core-concept candidate pack and calibration worksheets.

Reads the locked framework artifacts (formal ontology CSV + lock, legacy axis
crosswalk, framework sidecar, benchmark splits) and emits:

1. annotation_workflow/resources/core_concept_candidates_v1.csv
   Rule-based evidence tiers for every formal concept reachable through the
   mapped legacy axes. Tiers come from the ontology's own constraint fields
   (Visual Inferability, Temporal Requirement, Ontology Status); they are a
   review worksheet for the human calibration round, not a final core set.

2. annotation_workflow/resources/core_concept_neighbor_pairs_v1.csv
   Top nearest neighbours (keyword/pattern overlap + shared subdomain) for
   each non-excluded concept, with the distinguishing evidence fields left
   for human completion.

3. annotation_workflow/calibration/v1/calibration_mapping_worksheet_v1.csv
   Blind human-mapping instrument for the 180 calibration images. Contains no
   AI suggestions so independent mappers are not anchored.

4. annotation_workflow/calibration/v1/calibration_image_key_v1.csv
   Analysis-only key linking blind IDs to metadata and AI candidate concepts.
   Must not be shown to mappers before their independent mapping is submitted.

5. audit/core_concept_pack_20260909/core_concept_pack_report.json
   Rule definitions, counts, and structural checks.

The script never edits the 1,800 per-image drafts and never marks anything as
human gold.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / "annotation_workflow"
SIDECAR = WORKFLOW / "drafts" / "api_en" / "exports" / "PhiloVista-1800_framework.jsonl"
CROSSWALK = WORKFLOW / "resources" / "legacy_axis_crosswalk.json"
ONTOLOGY_LOCK = ROOT / "ontology" / "formal_632.lock.json"
SPLITS = ROOT / "splits" / "benchmark_splits.csv"
IMAGES_DIR = ROOT / "images"
PACK_DATE = "20260909"
PACK_VERSION = "core-concept-pack-v1"

CANDIDATES_OUT = WORKFLOW / "resources" / "core_concept_candidates_v1.csv"
NEIGHBORS_OUT = WORKFLOW / "resources" / "core_concept_neighbor_pairs_v1.csv"
WORKSHEET_DIR = WORKFLOW / "calibration" / "v1"
WORKSHEET_OUT = WORKSHEET_DIR / "calibration_mapping_worksheet_v1.csv"
WORKSHEET_KEY_OUT = WORKSHEET_DIR / "calibration_image_key_v1.csv"
REPORT_OUT = ROOT / "audit" / f"core_concept_pack_{PACK_DATE}" / "core_concept_pack_report.json"

TIER_RULES = {
    "A_core_recommended": "symbol_mediated AND snapshot AND ontology_status=candidate",
    "B_context_dependent": "candidate status, not excluded, but context_heavy and/or process evidence required",
    "C_excluded_from_core_v1": "not_image_decidable OR longitudinal OR ontology_status=ontology_only",
}

CLAIM_FORMAT = "PHC-<id>:supported|plausible|insufficient (semicolon-separated; use 'none:insufficient_evidence' when no philosophical claim is supportable)"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build core-concept pack and calibration worksheets.")
    parser.add_argument(
        "--ontology-csv",
        type=Path,
        default=ROOT / "ontology" / "philosophical_image_label_system_formal_632.csv",
        help="Formal CSV; defaults to the version included in this repository.",
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def split_phrases(value: str) -> list[str]:
    parts = [part.strip().lower() for part in (value or "").split(";")]
    return [part for part in parts if part]


def candidate_id(entry: object) -> str:
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return str(entry.get("concept_id") or entry.get("id") or "")
    return ""


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


STOPWORDS = {
    "and", "of", "the", "in", "for", "to", "a", "an", "or", "with", "from",
    "by", "on", "at", "into", "over", "under", "as", "is", "are",
}


def tokens(row: dict[str, str]) -> set[str]:
    words: set[str] = set()
    for phrase in split_phrases(row["Symbolic Keywords"]) + split_phrases(row["Visual Evidence Patterns"]):
        words.update(word for word in phrase.replace(",", " ").split() if len(word) > 2 and word not in STOPWORDS)
    return words


def main() -> None:
    args = parse_args()
    ontology_rows = read_csv(args.ontology_csv)
    if len(ontology_rows) != 632:
        raise ValueError("Formal ontology must contain 632 rows.")
    by_id = {row["Concept ID"]: row for row in ontology_rows}
    if len(by_id) != 632:
        raise ValueError("Formal ontology Concept IDs must be unique.")

    lock = json.loads(ONTOLOGY_LOCK.read_text(encoding="utf-8"))
    ontology_sha = sha256(args.ontology_csv)
    if lock["sha256"] != ontology_sha:
        raise ValueError("Ontology CSV SHA-256 does not match formal_632.lock.json; refusing to build.")

    crosswalk = json.loads(CROSSWALK.read_text(encoding="utf-8"))
    axis_concepts: dict[str, list[str]] = {}
    concept_axes: dict[str, set[str]] = defaultdict(set)
    for axis, entries in crosswalk["axes"].items():
        ids = [candidate_id(entry) for entry in entries]
        if any(cid not in by_id for cid in ids):
            raise ValueError(f"{axis}: crosswalk references unknown concept IDs.")
        axis_concepts[axis] = ids
        for cid in ids:
            concept_axes[cid].add(axis)

    # Retrieval statistics from the sidecar: how often each concept is
    # retrievable through the axes actually used by the draft interpretations.
    reachable_images: dict[str, set[str]] = defaultdict(set)
    reachable_interpretations: dict[str, int] = defaultdict(int)
    sidecar_by_sample: dict[str, dict] = {}
    with SIDECAR.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            sidecar_by_sample[record["sample_id"]] = record
            for interp in record.get("interpretations", []):
                seen = {candidate_id(entry) for entry in interp.get("formal_concept_candidates", [])}
                for cid in seen:
                    if cid:
                        reachable_images[cid].add(record["sample_id"])
                        reachable_interpretations[cid] += 1
    if len(sidecar_by_sample) != 1800:
        raise ValueError("Sidecar must contain exactly 1,800 records.")

    def tier_for(row: dict[str, str]) -> tuple[str, str]:
        inferability = row["Visual Inferability"]
        temporal = row["Temporal Requirement"]
        status = row["Ontology Status"]
        if inferability == "not_image_decidable":
            return "C_excluded_from_core_v1", "visual_inferability_not_image_decidable"
        if temporal == "longitudinal":
            return "C_excluded_from_core_v1", "temporal_longitudinal_unsupported"
        if status == "ontology_only":
            return "C_excluded_from_core_v1", "ontology_status_ontology_only"
        if inferability == "symbol_mediated" and temporal == "snapshot":
            return "A_core_recommended", ""
        return "B_context_dependent", "context_heavy_or_process_evidence_required"

    candidate_rows: list[dict[str, str]] = []
    tier_counts: dict[str, int] = defaultdict(int)
    exclusion_reasons: dict[str, int] = defaultdict(int)
    tier_of: dict[str, str] = {}
    for cid in sorted(concept_axes):
        row = by_id[cid]
        tier, reason = tier_for(row)
        tier_of[cid] = tier
        tier_counts[tier] += 1
        if reason:
            exclusion_reasons[reason] += 1
        candidate_rows.append({
            "concept_id": cid,
            "philosophical_concept": row["Philosophical Concept"],
            "macro_dimension": row["Macro Dimension"],
            "subdomain": row["Subdomain"],
            "tradition_school": row["Tradition / School"],
            "visual_inferability": row["Visual Inferability"],
            "temporal_requirement": row["Temporal Requirement"],
            "ontology_status": row["Ontology Status"],
            "evidence_tier": tier,
            "exclusion_reason": reason,
            "reachable_via_axes": ";".join(sorted(concept_axes[cid])),
            "reachable_image_count": str(len(reachable_images.get(cid, set()))),
            "reachable_interpretation_count": str(reachable_interpretations.get(cid, 0)),
            "symbolic_keywords": row["Symbolic Keywords"],
            "visual_evidence_patterns": row["Visual Evidence Patterns"],
            "grounding_rule": row["Grounding Rule"],
        })
    tier_rank = {"A_core_recommended": 0, "B_context_dependent": 1, "C_excluded_from_core_v1": 2}
    candidate_rows.sort(key=lambda r: (tier_rank[r["evidence_tier"]], -int(r["reachable_image_count"]), r["concept_id"]))
    write_csv(
        CANDIDATES_OUT,
        [
            "concept_id", "philosophical_concept", "macro_dimension", "subdomain", "tradition_school",
            "visual_inferability", "temporal_requirement", "ontology_status", "evidence_tier",
            "exclusion_reason", "reachable_via_axes", "reachable_image_count",
            "reachable_interpretation_count", "symbolic_keywords", "visual_evidence_patterns",
            "grounding_rule",
        ],
        candidate_rows,
    )

    # Nearest-neighbour discrimination pairs for non-excluded concepts, from
    # three signals: (1) same-axis retrieval competitors are deterministic --
    # a mapper retrieving that axis always faces all of its candidates; (2)
    # same-subdomain conceptual family; (3) token-level lexical overlap across
    # the whole ontology. Keyword phrases are paraphrastic, so whole-phrase
    # matching alone would miss crucial pairs (e.g. Berlin's two liberties).
    keywords_by_id = {cid: set(split_phrases(row["Symbolic Keywords"])) for cid, row in by_id.items()}
    patterns_by_id = {cid: set(split_phrases(row["Visual Evidence Patterns"])) for cid, row in by_id.items()}
    subdomain_by_id = {cid: row["Subdomain"] for cid, row in by_id.items()}
    tokens_by_id = {cid: tokens(row) for cid, row in by_id.items()}

    def pair_row(cid: str, other: str, source: str, rank: int, score: str) -> dict[str, str]:
        shared_kw = sorted(keywords_by_id[cid] & keywords_by_id[other])
        concept_only = sorted(patterns_by_id[cid] - patterns_by_id[other])
        neighbor_only = sorted(patterns_by_id[other] - patterns_by_id[cid])
        shared_axes = sorted(concept_axes[cid] & concept_axes.get(other, set()))
        return {
            "concept_id": cid,
            "concept": by_id[cid]["Philosophical Concept"],
            "evidence_tier": tier_of[cid],
            "neighbor_source": source,
            "neighbor_rank": str(rank),
            "neighbor_id": other,
            "neighbor_concept": by_id[other]["Philosophical Concept"],
            "neighbor_subdomain": subdomain_by_id[other],
            "similarity_score": score,
            "shared_axis": ";".join(shared_axes),
            "shared_symbolic_keywords": ";".join(shared_kw),
            "concept_only_visual_patterns": ";".join(concept_only),
            "neighbor_only_visual_patterns": ";".join(neighbor_only),
            "concept_grounding_rule": by_id[cid]["Grounding Rule"],
            "neighbor_grounding_rule": by_id[other]["Grounding Rule"],
            "human_discrimination_rule": "",
            "reviewer_id": "",
        }

    neighbor_rows: list[dict[str, str]] = []
    for cid in sorted(tier_of):
        if tier_of[cid].startswith("C_"):
            continue
        listed: set[str] = set()
        rank = 1
        for axis in sorted(concept_axes[cid]):
            for other in sorted(axis_concepts[axis]):
                if other != cid and other not in listed:
                    listed.add(other)
                    neighbor_rows.append(pair_row(cid, other, "same_axis_retrieval", rank, ""))
                    rank += 1
        subdomain_peers = sorted(
            (other for other in by_id if other != cid and other not in listed and subdomain_by_id[other] == subdomain_by_id[cid]),
            key=lambda other: (-jaccard(tokens_by_id[cid], tokens_by_id[other]), other),
        )
        for other in subdomain_peers[:3]:
            listed.add(other)
            neighbor_rows.append(pair_row(cid, other, "same_subdomain", rank, f"{jaccard(tokens_by_id[cid], tokens_by_id[other]):.3f}"))
            rank += 1
        lexical_peers = sorted(
            (other for other in by_id if other != cid and other not in listed and jaccard(tokens_by_id[cid], tokens_by_id[other]) > 0),
            key=lambda other: (-jaccard(tokens_by_id[cid], tokens_by_id[other]), other),
        )
        for other in lexical_peers[:2]:
            listed.add(other)
            neighbor_rows.append(pair_row(cid, other, "lexical_overlap", rank, f"{jaccard(tokens_by_id[cid], tokens_by_id[other]):.3f}"))
            rank += 1
    write_csv(
        NEIGHBORS_OUT,
        [
            "concept_id", "concept", "evidence_tier", "neighbor_source", "neighbor_rank",
            "neighbor_id", "neighbor_concept", "neighbor_subdomain", "similarity_score",
            "shared_axis", "shared_symbolic_keywords", "concept_only_visual_patterns",
            "neighbor_only_visual_patterns", "concept_grounding_rule",
            "neighbor_grounding_rule", "human_discrimination_rule", "reviewer_id",
        ],
        neighbor_rows,
    )

    # Blind calibration worksheet + analysis key for the calibration split.
    split_rows = read_csv(SPLITS)
    calibration = [row for row in split_rows if row["split"] == "calibration"]
    if len(calibration) != 180:
        raise ValueError(f"Calibration split must contain 180 rows, found {len(calibration)}.")
    worksheet_rows: list[dict[str, str]] = []
    key_rows: list[dict[str, str]] = []
    missing_images: list[str] = []
    for row in sorted(calibration, key=lambda item: sidecar_by_sample[item["sample_id"]]["annotation_item_id"]):
        sample_id = row["sample_id"]
        record = sidecar_by_sample.get(sample_id)
        if record is None:
            raise ValueError(f"{sample_id}: calibration sample missing from sidecar.")
        blind_id = record["annotation_item_id"]
        image_rel = f"images/{record['file_name']}"
        if not (IMAGES_DIR / record["file_name"]).exists():
            missing_images.append(record["file_name"])
        ai_candidates = sorted({
            candidate_id(entry)
            for interp in record.get("interpretations", [])
            for entry in interp.get("formal_concept_candidates", [])
        } - {""})
        worksheet_rows.append({
            "blind_id": blind_id,
            "image_path": image_rel,
            "human_phc_claims": "",
            "mapper_id": "",
            "mapping_date": "",
            "notes": "",
        })
        key_rows.append({
            "blind_id": blind_id,
            "annotation_item_id": blind_id,
            "sample_id": sample_id,
            "file_name": record["file_name"],
            "image_path": image_rel,
            "split": row["split"],
            "group_id": row["group_id"],
            "source": row["source"],
            "track": row["track"],
            "benchmark_axis_id": record.get("benchmark_axis_id", ""),
            "ai_candidate_concept_ids": ";".join(ai_candidates),
        })
    if missing_images:
        raise ValueError(f"{len(missing_images)} calibration image files missing under images/, e.g. {missing_images[0]}.")
    if len({r["blind_id"] for r in worksheet_rows}) != 180:
        raise ValueError("Calibration blind IDs must be unique.")
    write_csv(WORKSHEET_OUT, ["blind_id", "image_path", "human_phc_claims", "mapper_id", "mapping_date", "notes"], worksheet_rows)
    write_csv(
        WORKSHEET_KEY_OUT,
        [
            "blind_id", "annotation_item_id", "sample_id", "file_name", "image_path",
            "split", "group_id", "source", "track", "benchmark_axis_id",
            "ai_candidate_concept_ids",
        ],
        key_rows,
    )

    group_split = defaultdict(set)
    for row in split_rows:
        group_split[row["group_id"]].add(row["split"])
    report = {
        "pack_version": PACK_VERSION,
        "date": PACK_DATE,
        "ontology": {"sha256": ontology_sha, "rows": len(ontology_rows)},
        "tier_rules": TIER_RULES,
        "claim_format": CLAIM_FORMAT,
        "tier_counts": dict(tier_counts),
        "exclusion_reasons": dict(exclusion_reasons),
        "candidate_file": str(CANDIDATES_OUT.relative_to(ROOT)).replace("\\", "/"),
        "neighbor_file": str(NEIGHBORS_OUT.relative_to(ROOT)).replace("\\", "/"),
        "worksheet_file": str(WORKSHEET_OUT.relative_to(ROOT)).replace("\\", "/"),
        "worksheet_key_file": str(WORKSHEET_KEY_OUT.relative_to(ROOT)).replace("\\", "/"),
        "neighbor_pair_count": len(neighbor_rows),
        "concepts_with_neighbors": len({r["concept_id"] for r in neighbor_rows}),
        "calibration": {
            "rows": len(worksheet_rows),
            "unique_blind_ids": len({r["blind_id"] for r in worksheet_rows}),
            "image_files_verified": len(worksheet_rows) - len(missing_images),
        },
        "checks": {
            "ontology_sha_matches_lock": lock["sha256"] == ontology_sha,
            "all_crosswalk_ids_exist": True,
            "all_neighbor_ids_exist": all(r["neighbor_id"] in by_id for r in neighbor_rows),
            "group_ids_cross_splits": sum(1 for splits in group_split.values() if len(splits) > 1),
            "worksheet_free_of_ai_suggestions": True,
        },
        "limitations": [
            "Tiers are rule-based worksheets from ontology constraint fields; human calibration must confirm the core set.",
            "Reachable counts reflect axis-level retrieval, not concept-level evidence; candidates are retrieval aids only.",
            "Neighbor pairs are retrieved from three signals (same-axis retrieval, same subdomain, lexical overlap); human_discrimination_rule is left empty by design.",
        ],
    }
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({
        "tier_counts": dict(tier_counts),
        "neighbor_pairs": len(neighbor_rows),
        "calibration_rows": len(worksheet_rows),
        "report": str(REPORT_OUT.relative_to(ROOT)).replace("\\", "/"),
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
