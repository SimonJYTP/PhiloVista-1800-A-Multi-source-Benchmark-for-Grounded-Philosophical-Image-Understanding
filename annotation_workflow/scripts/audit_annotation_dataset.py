from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from PIL import Image


WORKFLOW = Path(__file__).resolve().parents[1]
V3_ROOT = WORKFLOW.parent
ITEM_DIR = WORKFLOW / "drafts" / "api_en" / "items"
EXPORT_DIR = WORKFLOW / "drafts" / "api_en" / "exports"
AUDIT_DIR = V3_ROOT / "audit" / "annotation_quality_v1"
BATCH_ITEMS = WORKFLOW / "admin" / "batch_items.csv"
BLIND_INDEX = V3_ROOT / "final_selection_1800" / "human_review" / "blind_image_index.csv"
MANIFEST = V3_ROOT / "final_selection_1800" / "final_selection_manifest.csv"

AXIS_COUNTS = {"scene": 3, "action": 3, "rationale": 3, "object": 5}
CONCEPTS = {
    "ethics_responsibility", "time_mortality", "social_existence",
    "identity_appearance", "knowledge_truth", "power_conflict",
    "choice_journey", "labor_technology", "freedom_constraint",
    "faith_meaning", "other_abstract_relation",
}
SUPPORTS = {"visual_support", "commonsense_inference", "insufficient_evidence", "not_applicable"}
SUFFICIENCY = {"supported", "plausible", "insufficient", "not_applicable"}
TEXT_DEPENDENCY = {"none", "low", "medium", "high"}
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
WINDOWS_PATH_RE = re.compile(r"(?i)\b[A-Z]:\\(?:[^\s\"']+\\)*[^\s\"']+")
SECRET_PATTERN_RE = re.compile(r"(?i)(?:bearer\s+[A-Za-z0-9._~+/-]{16,}|(?:api[_-]?key|secret|token)\s*[:=]\s*[A-Za-z0-9._~+/-]{12,}|\bsk-[A-Za-z0-9_-]{12,})")
PLACEHOLDER_SENTINEL_RE = re.compile(r"(?i)^\s*(?:todo|tbd|n/?a|unknown|placeholder|insert\s+text|lorem\s+ipsum|example\s+text)\s*[.!]?\s*$")
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)?")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit the completed 1,800-item English annotation draft.")
    parser.add_argument("--item-dir", type=Path, default=ITEM_DIR)
    parser.add_argument("--export-dir", type=Path, default=EXPORT_DIR)
    parser.add_argument("--audit-dir", type=Path, default=AUDIT_DIR)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def walk_strings(value: Any, prefix: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield prefix, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk_strings(item, f"{prefix}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else key
            yield from walk_strings(item, child)


def normalize_text(text: str) -> str:
    return " ".join(WORD_RE.findall(text.lower()))


def tokens(text: str) -> set[str]:
    return set(WORD_RE.findall(text.lower()))


def jaccard(left: str, right: str) -> float:
    a, b = tokens(left), tokens(right)
    return len(a & b) / len(a | b) if a and b else 0.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quantiles(values: list[int]) -> dict[str, float | int | None]:
    if not values:
        return {"min": None, "median": None, "p90": None, "max": None}
    ordered = sorted(values)
    p90_index = min(len(ordered) - 1, max(0, int(0.9 * len(ordered)) - 1))
    return {
        "min": ordered[0],
        "median": statistics.median(ordered),
        "p90": ordered[p90_index],
        "max": ordered[-1],
    }


def source_fragments(row: dict[str, str]) -> list[str]:
    fragments: list[str] = []
    for field in ("upstream_phrase", "upstream_annotation"):
        raw = row.get(field, "")
        if not raw:
            continue
        for part in re.split(r"\s*\|\|\s*|；", raw):
            part = part.strip()
            if len(WORD_RE.findall(part)) >= 6:
                fragments.append(part)
    return fragments


def main() -> None:
    args = parse_args()
    audit_dir = args.audit_dir.resolve()
    audit_dir.mkdir(parents=True, exist_ok=True)

    batch_rows = read_csv(BATCH_ITEMS)
    blind_rows = read_csv(BLIND_INDEX)
    manifest_rows = read_csv(MANIFEST)
    batch_by_id = {row["annotation_item_id"]: row for row in batch_rows}
    blind_by_id = {row["blind_id"]: row for row in blind_rows}
    manifest_by_sample = {row["sample_id"]: row for row in manifest_rows}
    expected_ids = [row["annotation_item_id"] for row in batch_rows]

    issues: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    length_by_axis: dict[str, list[int]] = defaultdict(list)
    exact_caption_occurrences: dict[tuple[str, str], list[str]] = defaultdict(list)
    method_counts: Counter[str] = Counter()
    verdict_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    track_counts: Counter[str] = Counter()
    text_dependency_counts: Counter[str] = Counter()
    sufficiency_counts: Counter[str] = Counter()
    top_level_shapes: Counter[tuple[str, ...]] = Counter()

    env_secrets: list[str] = []
    env_path = WORKFLOW / ".env.local"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8-sig").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                value = line.split("=", 1)[1].strip().strip("\"'")
                if len(value) >= 12:
                    env_secrets.append(value)

    def add(severity: str, code: str, item_id: str, field: str, detail: str, repairable: bool = False) -> None:
        issues.append({
            "severity": severity,
            "code": code,
            "annotation_item_id": item_id,
            "field": field,
            "detail": detail,
            "deterministically_repairable": repairable,
        })

    actual_files = {path.stem: path for path in args.item_dir.glob("*.json")}
    for missing in sorted(set(expected_ids) - set(actual_files)):
        add("critical", "missing_item", missing, "file", "Expected annotation JSON is absent.")
    for extra in sorted(set(actual_files) - set(expected_ids)):
        add("high", "unexpected_item", extra, "file", "Annotation JSON is not in the frozen batch plan.")

    for item_id in expected_ids:
        path = actual_files.get(item_id)
        if path is None:
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except Exception as error:
            add("critical", "invalid_json", item_id, "file", str(error))
            continue
        if not isinstance(record, dict):
            add("critical", "invalid_record_type", item_id, "record", "Top level must be an object.")
            continue
        records.append(record)
        top_level_shapes[tuple(sorted(record))] += 1

        batch = batch_by_id[item_id]
        blind = blind_by_id.get(item_id)
        if blind is None:
            add("critical", "missing_blind_mapping", item_id, "annotation_item_id", "No blind-index row exists.")
            continue
        manifest = manifest_by_sample.get(blind["sample_id"])
        if manifest is None:
            add("critical", "missing_manifest_mapping", item_id, "sample_id", "No final-selection manifest row exists.")
            continue
        source_counts[manifest["source"]] += 1
        track_counts[manifest["track"]] += 1

        expected_path = V3_ROOT / Path(blind["selected_path"])
        if not expected_path.is_file():
            expected_path = V3_ROOT / "images" / expected_path.name
        expected_values = {
            "annotation_item_id": item_id,
            "sample_id": blind["sample_id"],
            "file_name": expected_path.name,
            "batch_id": batch["batch_id"],
            "position_in_batch": int(batch["position_in_batch"]),
            "language": "en",
            "formal_gold": False,
            "needs_independent_human_annotation": True,
            "needs_independent_human_rating": True,
        }
        for field, expected in expected_values.items():
            if record.get(field) != expected:
                add("critical" if field in {"annotation_item_id", "sample_id", "file_name"} else "high", "mapping_or_status_mismatch", item_id, field, f"Expected {expected!r}; found {record.get(field)!r}.", True)

        if not expected_path.is_file():
            add("critical", "missing_image", item_id, "file_name", str(expected_path))
        else:
            try:
                with Image.open(expected_path) as image:
                    image.verify()
                actual_hash = sha256_file(expected_path)
                if actual_hash.lower() != manifest["sha256"].lower():
                    add("critical", "image_hash_mismatch", item_id, "file_name", "Image bytes differ from the frozen manifest.")
            except Exception as error:
                add("critical", "image_decode_failure", item_id, "file_name", str(error))

        method = record.get("method")
        method_counts[str(method)] += 1
        verdict = record.get("review", {}).get("verdict") if isinstance(record.get("review"), dict) else None
        verdict_counts[str(verdict)] += 1
        if method == "ai_agent_direct_visual_draft_non_independent" or verdict == "pending_cross_model_or_human_review":
            add("high", "manual_ai_fallback_pending_review", item_id, "review.verdict", "This item did not complete the standard two-model route and requires priority visual review.")

        captions = record.get("captions")
        if not isinstance(captions, dict):
            add("critical", "missing_captions", item_id, "captions", "Captions must be an object.")
            captions = {}
        for axis, expected_count in AXIS_COUNTS.items():
            values = captions.get(axis)
            if not isinstance(values, list) or len(values) != expected_count:
                add("critical", "caption_count", item_id, f"captions.{axis}", f"Expected {expected_count} strings; found {len(values) if isinstance(values, list) else 'non-list'}.")
                continue
            seen: Counter[str] = Counter()
            for index, value in enumerate(values):
                field = f"captions.{axis}[{index}]"
                if not isinstance(value, str) or not value.strip():
                    add("critical", "empty_caption", item_id, field, "Caption is empty or non-string.")
                    continue
                norm = normalize_text(value)
                seen[norm] += 1
                length_by_axis[axis].append(len(WORD_RE.findall(value)))
                exact_caption_occurrences[(axis, norm)].append(item_id)
                if len(WORD_RE.findall(value)) < 4:
                    add("medium", "caption_too_short", item_id, field, "Caption has fewer than four lexical tokens.")
                if len(WORD_RE.findall(value)) > 90:
                    add("medium", "caption_too_long", item_id, field, "Caption exceeds 90 lexical tokens.")
            for norm, count in seen.items():
                if norm and count > 1:
                    add("high", "within_axis_exact_duplicate", item_id, f"captions.{axis}", f"Normalized caption occurs {count} times.")
            for left in range(len(values)):
                for right in range(left + 1, len(values)):
                    if isinstance(values[left], str) and isinstance(values[right], str):
                        score = jaccard(values[left], values[right])
                        if score >= 0.88 and normalize_text(values[left]) != normalize_text(values[right]):
                            add("medium", "within_axis_near_duplicate", item_id, f"captions.{axis}", f"References {left + 1} and {right + 1} have token Jaccard {score:.2f}.")

        supports = record.get("rationale_support")
        if not isinstance(supports, list) or len(supports) != 3 or any(value not in SUPPORTS for value in supports):
            add("high", "invalid_rationale_support", item_id, "rationale_support", "Expected three allowed support labels.")
        text_dependency = record.get("text_dependency")
        text_dependency_counts[str(text_dependency)] += 1
        if text_dependency not in TEXT_DEPENDENCY:
            add("high", "invalid_text_dependency", item_id, "text_dependency", f"Found {text_dependency!r}.")

        phils = record.get("philosophy_interpretations")
        if not isinstance(phils, list) or len(phils) != 3:
            add("critical", "philosophy_count", item_id, "philosophy_interpretations", "Expected exactly three entries.")
            phils = []
        interpretations: list[str] = []
        for index, phil in enumerate(phils, 1):
            base = f"philosophy_interpretations[{index - 1}]"
            if not isinstance(phil, dict):
                add("critical", "invalid_philosophy_type", item_id, base, "Entry must be an object.")
                continue
            expected_candidate = f"AI_{item_id}_P{index}"
            if phil.get("candidate_id") != expected_candidate:
                add("high", "candidate_id_mismatch", item_id, f"{base}.candidate_id", f"Expected {expected_candidate!r}; found {phil.get('candidate_id')!r}.", True)
            list_rules = {
                "visual_anchors": (1, 3),
                "symbolic_mapping": (0, 2),
                "concept_ids": (1, 2),
                "alternative_interpretations": (1, 1),
                "limitations": (1, 1),
            }
            for field, (minimum, maximum) in list_rules.items():
                value = phil.get(field)
                if not isinstance(value, list) or not minimum <= len(value) <= maximum or any(not isinstance(entry, str) or not entry.strip() for entry in value):
                    add("high", "invalid_philosophy_list", item_id, f"{base}.{field}", f"Expected {minimum}-{maximum} non-empty strings.")
            concept_ids = phil.get("concept_ids", [])
            if isinstance(concept_ids, list) and (set(concept_ids) - CONCEPTS or len(concept_ids) != len(set(concept_ids))):
                add("high", "invalid_concept_id", item_id, f"{base}.concept_ids", "Contains an unknown or duplicate concept ID.")
            interpretation = phil.get("interpretation")
            if not isinstance(interpretation, str) or not interpretation.strip():
                add("critical", "empty_interpretation", item_id, f"{base}.interpretation", "Interpretation is empty.")
            else:
                interpretations.append(interpretation)
                if len(WORD_RE.findall(interpretation)) < 10:
                    add("medium", "interpretation_too_short", item_id, f"{base}.interpretation", "Interpretation has fewer than ten lexical tokens.")
            sufficiency = phil.get("sufficiency")
            sufficiency_counts[str(sufficiency)] += 1
            if sufficiency not in SUFFICIENCY:
                add("high", "invalid_sufficiency", item_id, f"{base}.sufficiency", f"Found {sufficiency!r}.")
        for left in range(len(interpretations)):
            for right in range(left + 1, len(interpretations)):
                score = jaccard(interpretations[left], interpretations[right])
                if score >= 0.72:
                    add("medium", "near_duplicate_philosophy", item_id, "philosophy_interpretations", f"Interpretations {left + 1} and {right + 1} have token Jaccard {score:.2f}.")

        if manifest["track"] == "boundary" and phils and all(isinstance(p, dict) and p.get("sufficiency") in {"supported", "plausible"} for p in phils):
            add("high", "boundary_without_insufficient_reading", item_id, "philosophy_interpretations", "Boundary item has no insufficient/not_applicable interpretation; possible systematic overinterpretation.")

        all_text = list(walk_strings(record))
        for field, text in all_text:
            if field.startswith("provenance") or field.startswith("review"):
                security_scope = True
            else:
                security_scope = False
            if CJK_RE.search(text) and (field.startswith("target_subject") or field.startswith("captions") or field.startswith("philosophy_interpretations")):
                add("high", "cjk_in_english_field", item_id, field, "English-only free text contains CJK characters.")
            if "；" in text and (field.startswith("target_subject") or field.startswith("captions") or field.startswith("philosophy_interpretations")):
                add("critical", "forbidden_fullwidth_semicolon", item_id, field, "U+FF1B would corrupt HL CSV reference boundaries.")
            if CONTROL_RE.search(text):
                add("high", "control_character", item_id, field, "String contains a forbidden control character.", True)
            if PLACEHOLDER_SENTINEL_RE.fullmatch(text) and (field.startswith("captions") or field.startswith("philosophy_interpretations") or field == "target_subject"):
                add("medium", "placeholder_language", item_id, field, "Text contains a placeholder-like token; inspect in context.")
            if security_scope and (WINDOWS_PATH_RE.search(text) or text.startswith("data:image") or SECRET_PATTERN_RE.search(text) or any(secret in text for secret in env_secrets)):
                add("critical", "sensitive_data_leak", item_id, field, "Provenance/review text contains a credential, image payload, or local absolute path.")

        candidate_texts = [text for field, text in all_text if field == "target_subject" or field.startswith("captions") or field.endswith(".interpretation")]
        for fragment in source_fragments(manifest):
            norm_fragment = normalize_text(fragment)
            for candidate in candidate_texts:
                norm_candidate = normalize_text(candidate)
                if norm_fragment and (norm_candidate == norm_fragment or (len(tokens(fragment)) >= 8 and jaccard(fragment, candidate) >= 0.94)):
                    add("high", "possible_upstream_text_leakage", item_id, "annotation_text", "A generated annotation is nearly identical to hidden upstream text.")
                    break
            else:
                continue
            break

    for (axis, norm), item_ids in exact_caption_occurrences.items():
        distinct = sorted(set(item_ids))
        if norm and len(distinct) >= 5:
            for item_id in distinct:
                add("medium", "cross_image_exact_reuse", item_id, f"captions.{axis}", f"The same normalized sentence appears in {len(distinct)} images.")

    # Validate the two release-oriented exports against the JSON truth source.
    expected_record_by_file = {record.get("file_name"): record for record in records if isinstance(record.get("file_name"), str)}
    hl_jsonl_path = args.export_dir / "PhiloVista-1800_HL.jsonl"
    philosophy_jsonl_path = args.export_dir / "PhiloVista-1800_philosophy.jsonl"
    csv_path = args.export_dir / "PhiloVista-1800_HL.csv"
    if not hl_jsonl_path.is_file() or not csv_path.is_file() or not philosophy_jsonl_path.is_file():
        add("critical", "missing_export", "__dataset__", "exports", "One or more expected export files are absent.")
    else:
        try:
            hl_rows = [json.loads(line) for line in hl_jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if len(hl_rows) != len(expected_ids):
                add("critical", "hl_jsonl_count", "__dataset__", "hl.jsonl", f"Expected {len(expected_ids)} rows; found {len(hl_rows)}.")
            for row in hl_rows:
                source = expected_record_by_file.get(row.get("file_name"))
                if source is None or row.get("captions") != source.get("captions"):
                    add("critical", "hl_jsonl_mismatch", "__dataset__", str(row.get("file_name")), "JSONL row differs from item truth source.")
        except Exception as error:
            add("critical", "hl_jsonl_parse", "__dataset__", "hl.jsonl", str(error))

        try:
            with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                csv_rows = list(csv.DictReader(handle))
                header = handle.seek(0)
            expected_header = ["图片文件名", "Scene场景描述", "Action动作描述", "Rationale理由描述", "Object物体描述"]
            with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                actual_header = next(csv.reader(handle))
            if actual_header != expected_header:
                add("critical", "csv_header", "__dataset__", "csv.header", f"Found {actual_header!r}.")
            if len(csv_rows) != len(expected_ids):
                add("critical", "csv_count", "__dataset__", "csv", f"Expected {len(expected_ids)} rows; found {len(csv_rows)}.")
            column_axis = dict(zip(expected_header[1:], AXIS_COUNTS))
            for row in csv_rows:
                source = expected_record_by_file.get(row[expected_header[0]])
                if source is None:
                    add("critical", "csv_unknown_file", "__dataset__", row[expected_header[0]], "CSV filename is absent from item records.")
                    continue
                for column, axis in column_axis.items():
                    reconstructed = row[column].split("；")
                    if reconstructed != source["captions"][axis]:
                        add("critical", "csv_roundtrip_mismatch", source["annotation_item_id"], f"captions.{axis}", "CSV split does not reproduce the source array byte-for-byte.")
        except Exception as error:
            add("critical", "csv_parse", "__dataset__", "csv", str(error))

        try:
            phil_rows = [json.loads(line) for line in philosophy_jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if len(phil_rows) != len(expected_ids):
                add("critical", "philosophy_jsonl_count", "__dataset__", "philosophy.jsonl", f"Expected {len(expected_ids)} rows; found {len(phil_rows)}.")
            by_id = {record["annotation_item_id"]: record for record in records}
            for row in phil_rows:
                source = by_id.get(row.get("annotation_item_id"))
                if source is None or row.get("interpretations") != source.get("philosophy_interpretations"):
                    add("critical", "philosophy_jsonl_mismatch", str(row.get("annotation_item_id")), "interpretations", "Sidecar row differs from item truth source.")
        except Exception as error:
            add("critical", "philosophy_jsonl_parse", "__dataset__", "philosophy.jsonl", str(error))

    issue_counts_by_severity = Counter(issue["severity"] for issue in issues)
    issue_counts_by_code = Counter(issue["code"] for issue in issues)
    affected_by_severity = {
        severity: len({issue["annotation_item_id"] for issue in issues if issue["severity"] == severity and issue["annotation_item_id"] != "__dataset__"})
        for severity in ("critical", "high", "medium", "low")
    }
    repair_log = audit_dir / "PhiloVista-1800_repair_log.jsonl"
    repaired_ids: set[str] = set()
    latest_repair_by_id: dict[str, dict[str, Any]] = {}
    if repair_log.is_file():
        for line in repair_log.read_text(encoding="utf-8").splitlines():
            if line.strip():
                repair = json.loads(line)
                repaired_ids.add(repair["annotation_item_id"])
                latest_repair_by_id[repair["annotation_item_id"]] = repair
    with (audit_dir / "PhiloVista-1800_priority_human_review.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        columns = ["annotation_item_id", "reason", "changed_fields", "backup"]
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for item_id in sorted(latest_repair_by_id):
            repair = latest_repair_by_id[item_id]
            writer.writerow({
                "annotation_item_id": item_id,
                "reason": repair["reason"],
                "changed_fields": " | ".join(repair["changed_fields"]),
                "backup": repair["backup"],
            })
    export_artifacts = {}
    for export_path in (hl_jsonl_path, csv_path, philosophy_jsonl_path):
        if export_path.is_file():
            export_artifacts[export_path.name] = {
                "bytes": export_path.stat().st_size,
                "sha256": sha256_file(export_path),
            }
    report = {
        "audit_version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": "PhiloVista-1800",
        "scope": "completed 1,800-item English AI annotation draft",
        "intended_grain": "one item JSON per frozen blind image",
        "expected_items": len(expected_ids),
        "parsed_items": len(records),
        "unique_annotation_item_ids": len({record.get("annotation_item_id") for record in records}),
        "source_distribution": dict(sorted(source_counts.items())),
        "track_distribution": dict(sorted(track_counts.items())),
        "method_distribution": dict(sorted(method_counts.items())),
        "review_verdict_distribution": dict(sorted(verdict_counts.items())),
        "text_dependency_distribution": dict(sorted(text_dependency_counts.items())),
        "philosophy_sufficiency_distribution": dict(sorted(sufficiency_counts.items())),
        "caption_word_length": {axis: quantiles(values) for axis, values in sorted(length_by_axis.items())},
        "schema_shape_variants": len(top_level_shapes),
        "checks": {
            "mapped_images_decoded_and_sha256_checked": len(records),
            "export_roundtrip_records_checked": len(records),
            "possible_upstream_text_leakage_matches": issue_counts_by_code["possible_upstream_text_leakage"],
            "sensitive_data_leakage_matches": issue_counts_by_code["sensitive_data_leak"],
            "forbidden_fullwidth_semicolon_matches": issue_counts_by_code["forbidden_fullwidth_semicolon"],
            "cjk_in_english_fields": issue_counts_by_code["cjk_in_english_field"],
        },
        "unique_repaired_items": len(repaired_ids),
        "export_artifacts": export_artifacts,
        "issues": {
            "total": len(issues),
            "by_severity": dict(sorted(issue_counts_by_severity.items())),
            "affected_items_by_severity": affected_by_severity,
            "by_code": dict(sorted(issue_counts_by_code.items())),
        },
        "release_readiness": "blocked" if issue_counts_by_severity["critical"] or issue_counts_by_severity["high"] else "conditionally_ready",
        "important_scope_note": "This audit assesses AI drafts. It does not convert them into independent human gold annotations or supply HL confidence/purity/diversity fields.",
    }

    (audit_dir / "PhiloVista-1800_quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (audit_dir / "PhiloVista-1800_remaining_issues.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        columns = ["severity", "code", "annotation_item_id", "field", "detail", "deterministically_repairable"]
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(issues)
    with (audit_dir / "PhiloVista-1800_remaining_issues.jsonl").open("w", encoding="utf-8", newline="") as handle:
        for issue in issues:
            handle.write(json.dumps(issue, ensure_ascii=False) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
