from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
import zipfile
import zlib
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

from PIL import Image, ImageStat


WORKSPACE = Path(r"D:\Project\哲学AI多模态论文")
REPO = WORKSPACE / "PhiloVista-1800-GitHub"
IMAGES = WORKSPACE / "PhiloVista-1800-images"
UPSTREAM = WORKSPACE / "NewBenchmark" / "PhilosophyHL_v3"
EXTRACTED = UPSTREAM / "source_extracted"
ARCHIVES = UPSTREAM / "source_archives"
MANIFEST = REPO / "final_selection_1800" / "final_selection_manifest.csv"
ANNOTATIONS = (
    REPO
    / "annotation_workflow"
    / "drafts"
    / "api_en"
    / "exports"
    / "PhiloVista-1800_HL.csv"
)
ITEMS = REPO / "annotation_workflow" / "drafts" / "api_en" / "items"
OUT = Path(__file__).resolve().parent

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
SOURCE_PREFIX = {
    "HL Dataset": "HL",
    "HAIVMet": "HAIV",
    "IRFL": "IRFL",
    "MM-MoralBench": "MM",
}
EXPECTED_COUNTS = {"HL Dataset": 600, "HAIVMet": 550, "IRFL": 500, "MM-MoralBench": 150}
EXPECTED_REFS = {"scene": 3, "action": 3, "rationale": 3, "object": 5}

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "been", "being", "by", "for",
    "from", "has", "have", "he", "her", "his", "in", "into", "is", "it", "its", "of", "on",
    "or", "she", "that", "the", "their", "there", "they", "this", "to", "two", "was", "were",
    "with", "while", "who", "will", "would", "image", "picture", "illustration", "shows", "showing",
    "visible", "appears", "appear", "suggests", "suggesting", "scene", "person", "people", "figure",
}


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_stream(stream) -> str:
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        h.update(block)
    return h.hexdigest()


def crc32_file(path: Path) -> int:
    value = 0
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            value = zlib.crc32(block, value)
    return value & 0xFFFFFFFF


def tokens(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", text).lower()
    words = re.findall(r"[a-z][a-z'-]{2,}", normalized)
    return {w.strip("'-") for w in words if w.strip("'-") not in STOPWORDS}


def source_reference(row: dict[str, str]) -> str:
    if row["source"] in {"HL Dataset", "HAIVMet"}:
        return row["upstream_annotation"]
    if row["source"] == "IRFL":
        # IRFL's phrase/definition is semantic metadata rather than a literal caption.
        return " ".join([row["upstream_phrase"], row["upstream_annotation"]])
    return ""


def overlap_score(reference: str, caption_text: str) -> tuple[float | None, float | None]:
    ref = tokens(reference)
    cap = tokens(caption_text)
    if not ref or not cap:
        return None, None
    intersection = ref & cap
    return len(intersection) / len(ref), len(intersection) / len(ref | cap)


def fix_zip_name(info: zipfile.ZipInfo) -> str:
    if info.flag_bits & 0x800:
        return info.filename
    try:
        return info.orig_filename.encode("cp437").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return info.filename


def zip_lookup(path: Path) -> tuple[zipfile.ZipFile, dict[str, zipfile.ZipInfo]]:
    zf = zipfile.ZipFile(path)
    lookup: dict[str, zipfile.ZipInfo] = {}
    for info in zf.infolist():
        if info.is_dir() or "__MACOSX" in info.filename:
            continue
        lookup[fix_zip_name(info).replace("\\", "/")] = info
    return zf, lookup


def resolve_extracted(row: dict[str, str]) -> Path:
    member = Path(*PurePosixPath(row["original_member"].replace("\\", "/")).parts)
    if row["source"] == "HL Dataset":
        container = Path(*PurePosixPath(row["original_container"].replace("\\", "/")).parts)
        return EXTRACTED / container / member
    if row["source"] == "HAIVMet":
        return EXTRACTED / "haivmet" / member
    if row["source"] == "IRFL":
        return EXTRACTED / "irfl" / member
    if row["source"] == "MM-MoralBench":
        return EXTRACTED / "mm_moral" / member
    raise ValueError(row["source"])


def archive_path(row: dict[str, str]) -> Path | None:
    if not row["original_container"].startswith("source_archives/"):
        return None
    rel = Path(*PurePosixPath(row["original_container"]).parts[1:])
    return ARCHIVES / rel


def split_csv_refs(value: str) -> list[str]:
    return [part.strip() for part in value.split("；")]


def normalized_join(parts: list[str]) -> str:
    return "\n".join(re.sub(r"\s+", " ", x).strip() for x in parts)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_rows = load_csv(MANIFEST)
    annotation_rows = load_csv(ANNOTATIONS)
    image_files = sorted(p for p in IMAGES.iterdir() if p.is_file())
    image_by_name = {p.name: p for p in image_files}
    annotation_by_name = {r["图片文件名"]: r for r in annotation_rows}

    item_by_file: dict[str, dict] = {}
    item_id_by_file: dict[str, str] = {}
    item_parse_errors: list[str] = []
    for item_path in sorted(ITEMS.glob("*.json")):
        try:
            item = json.loads(item_path.read_text(encoding="utf-8"))
            item_by_file[item["file_name"]] = item
            item_id_by_file[item["file_name"]] = item["annotation_item_id"]
        except Exception as exc:  # pragma: no cover - audit evidence path
            item_parse_errors.append(f"{item_path.name}: {exc}")

    hl_rows: dict[str, dict[str, str]] = {}
    for split in ("train", "test"):
        p = EXTRACTED / "hl_dataset_export" / f"{split}_annotations.csv"
        for row in load_csv(p):
            hl_rows[row["图片文件名"]] = row

    zip_cache: dict[Path, tuple[zipfile.ZipFile, dict[str, zipfile.ZipInfo]]] = {}
    details: list[dict[str, object]] = []
    missing_images: list[str] = []
    orphan_images = sorted(set(image_by_name) - {
        Path(r["selected_path"]).name for r in manifest_rows
    })

    for row in manifest_rows:
        expected_name = Path(row["selected_path"]).name
        path = image_by_name.get(expected_name)
        ann = annotation_by_name.get(expected_name)
        item = item_by_file.get(expected_name)
        source = row["source"]
        expected_prefix = SOURCE_PREFIX.get(source, "UNKNOWN")
        filename_pattern_ok = bool(
            re.fullmatch(rf"PHL1800_{re.escape(expected_prefix)}_\d{{4}}\.(?:png|jpg|webp)", expected_name)
        )

        record: dict[str, object] = {
            "sample_id": row["sample_id"],
            "annotation_item_id": item_id_by_file.get(expected_name, ""),
            "file_name": expected_name,
            "source": source,
            "track": row["track"],
            "source_id": row["source_id"],
            "image_exists": path is not None,
            "annotation_exists": ann is not None,
            "item_json_exists": item is not None,
            "annotation_method": item.get("method", "") if item else "",
            "formal_gold": item.get("formal_gold") if item else None,
            "review_verdict": item.get("review", {}).get("verdict", "") if item else "",
            "review_issues": " | ".join(item.get("review", {}).get("issues", [])) if item else "",
            "filename_pattern_ok": filename_pattern_ok,
            "sample_id_matches_filename": Path(expected_name).stem == row["sample_id"],
            "decode_ok": False,
            "sha256_matches_manifest": False,
            "dimensions_match_manifest": False,
            "format_matches_manifest": False,
            "extracted_source_exists": False,
            "selected_matches_extracted_sha256": False,
            "archive_member_found": None,
            "archive_member_matches_size_crc": None,
            "archive_member_matches_sha256": None,
            "archive_member_match_method": "",
            "archive_resolved_member": "",
            "hl_annotation_row_found": None,
            "hl_upstream_annotation_exact": None,
            "csv_item_json_exact": False,
            "caption_shape_ok": False,
            "reference_coverage": None,
            "reference_jaccard": None,
            "semantic_risk_reasons": "",
        }
        if path is None:
            missing_images.append(expected_name)
            details.append(record)
            continue

        digest = sha256_file(path)
        record["actual_sha256"] = digest
        record["sha256_matches_manifest"] = digest.lower() == row["sha256"].lower()
        try:
            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:
                width, height = im.size
                fmt = (im.format or "").upper()
                gray = im.convert("L").resize((64, 64))
                stat = ImageStat.Stat(gray)
                record["mean_luma"] = round(stat.mean[0], 3)
                record["luma_stddev"] = round(stat.stddev[0], 3)
            record["decode_ok"] = True
            record["actual_width"] = width
            record["actual_height"] = height
            record["actual_format"] = fmt
            record["dimensions_match_manifest"] = (
                width == int(row["width"]) and height == int(row["height"])
            )
            expected_fmt = row["format"].upper()
            # Pillow reports JPEG while the release extension is .jpg.
            record["format_matches_manifest"] = fmt == expected_fmt
        except Exception as exc:
            record["decode_error"] = str(exc)

        extracted = resolve_extracted(row)
        record["extracted_source_exists"] = extracted.exists()
        if extracted.exists():
            extracted_digest = sha256_file(extracted)
            record["extracted_sha256"] = extracted_digest
            record["selected_matches_extracted_sha256"] = digest == extracted_digest

        arc = archive_path(row)
        if arc is not None:
            if arc not in zip_cache:
                zip_cache[arc] = zip_lookup(arc)
            _, lookup = zip_cache[arc]
            member_name = row["original_member"].replace("\\", "/")
            info = lookup.get(member_name)
            current_crc = crc32_file(path)
            if info is not None:
                record["archive_member_match_method"] = "manifest_member_name"
            else:
                # Some Advertisement member names in the manifest retain mojibake
                # from an earlier Windows extraction.  Resolve only when the
                # selected file's (size, CRC32) pair identifies one archive member.
                candidates = [
                    candidate
                    for candidate in lookup.values()
                    if candidate.file_size == path.stat().st_size and candidate.CRC == current_crc
                ]
                if len(candidates) == 1:
                    info = candidates[0]
                    record["archive_member_match_method"] = "unique_size_crc_fallback"
            record["archive_member_found"] = info is not None
            if info is not None:
                record["archive_resolved_member"] = fix_zip_name(info)
                record["archive_member_matches_size_crc"] = (
                    info.file_size == path.stat().st_size and info.CRC == current_crc
                )
                with zip_cache[arc][0].open(info, "r") as member_stream:
                    record["archive_member_matches_sha256"] = (
                        sha256_stream(member_stream) == digest
                    )

        if source == "HL Dataset":
            upstream = hl_rows.get(row["source_id"])
            record["hl_annotation_row_found"] = upstream is not None
            if upstream is not None:
                joined = " || ".join(
                    upstream[name]
                    for name in (
                        "Scene场景描述", "Action动作描述", "Rationale理由描述", "Object物体描述"
                    )
                )
                record["hl_upstream_annotation_exact"] = joined == row["upstream_annotation"]

        if ann is not None:
            refs = {
                "scene": split_csv_refs(ann["Scene场景描述"]),
                "action": split_csv_refs(ann["Action动作描述"]),
                "rationale": split_csv_refs(ann["Rationale理由描述"]),
                "object": split_csv_refs(ann["Object物体描述"]),
            }
            record["caption_shape_ok"] = all(
                len(refs[k]) == EXPECTED_REFS[k] and all(refs[k]) for k in EXPECTED_REFS
            )
            caption_text = " ".join(x for values in refs.values() for x in values)
            coverage, jaccard = overlap_score(source_reference(row), caption_text)
            record["reference_coverage"] = None if coverage is None else round(coverage, 4)
            record["reference_jaccard"] = None if jaccard is None else round(jaccard, 4)

            risk: list[str] = []
            if source == "HL Dataset" and coverage is not None and coverage < 0.18:
                risk.append("very_low_overlap_with_HL_human_captions")
            elif source == "HAIVMet" and coverage is not None and coverage < 0.16:
                risk.append("very_low_overlap_with_HAIV_prompt")
            elif source == "IRFL" and coverage is not None and coverage < 0.08:
                risk.append("low_overlap_with_IRFL_phrase_definition")
            if re.search(r"(?:word|text|sign|reads|written|label) ['\"]?[A-Z][A-Z0-9 -]{2,}", caption_text):
                risk.append("specific_OCR_claim")
            if re.search(r"\b(?:at least|exactly)\s+\d+\b|\b\d+\s+(?:people|persons|figures|cars|vehicles)\b", caption_text, re.I):
                risk.append("precise_count_claim")
            if re.search(r"\b(?:appears to be|possibly|may be|might be|could be|unclear|unreadable|not determinable)\b", caption_text, re.I):
                risk.append("explicit_visual_uncertainty")
            if re.search(r"\b(?:wants to|intends to|trying to|because (?:he|she|they)|in order to)\b", " ".join(refs["action"]), re.I):
                risk.append("action_contains_intent_inference")
            record["semantic_risk_reasons"] = ";".join(risk)

            if item is not None:
                item_caps = item.get("captions", {})
                record["csv_item_json_exact"] = all(
                    normalized_join(refs[k]) == normalized_join(item_caps.get(k, []))
                    for k in EXPECTED_REFS
                )

        details.append(record)

    for zf, _ in zip_cache.values():
        zf.close()

    # Duplicate checks are based on recomputed current bytes, not manifest claims.
    hash_groups: dict[str, list[str]] = defaultdict(list)
    for rec in details:
        if rec.get("actual_sha256"):
            hash_groups[str(rec["actual_sha256"])].append(str(rec["file_name"]))
    duplicate_groups = [names for names in hash_groups.values() if len(names) > 1]

    # Per-source numbering coverage.
    numbering: dict[str, dict[str, object]] = {}
    for source, prefix in SOURCE_PREFIX.items():
        rows = [r for r in manifest_rows if r["source"] == source]
        nums = sorted(
            int(re.search(r"_(\d{4})$", r["sample_id"]).group(1))
            for r in rows
            if re.search(r"_(\d{4})$", r["sample_id"])
        )
        numbering[source] = {
            "count": len(rows),
            "expected_count": EXPECTED_COUNTS[source],
            "min": min(nums) if nums else None,
            "max": max(nums) if nums else None,
            "missing_numbers": sorted(set(range(1, EXPECTED_COUNTS[source] + 1)) - set(nums)),
            "duplicate_numbers": sorted(n for n, c in Counter(nums).items() if c > 1),
        }

    def count_true(key: str) -> int:
        return sum(rec.get(key) is True for rec in details)

    def count_false(key: str) -> int:
        return sum(rec.get(key) is False for rec in details)

    per_source: dict[str, dict[str, object]] = {}
    for source in EXPECTED_COUNTS:
        subset = [r for r in details if r["source"] == source]
        per_source[source] = {
            "rows": len(subset),
            "image_exists": sum(r["image_exists"] is True for r in subset),
            "hash_matches_manifest": sum(r["sha256_matches_manifest"] is True for r in subset),
            "selected_matches_extracted": sum(r["selected_matches_extracted_sha256"] is True for r in subset),
            "archive_member_found": sum(r["archive_member_found"] is True for r in subset),
            "archive_member_matches_size_crc": sum(r["archive_member_matches_size_crc"] is True for r in subset),
            "archive_member_matches_sha256": sum(r["archive_member_matches_sha256"] is True for r in subset),
            "annotation_exists": sum(r["annotation_exists"] is True for r in subset),
            "caption_shape_ok": sum(r["caption_shape_ok"] is True for r in subset),
        }

    failures = []
    invariant_keys = [
        "image_exists", "annotation_exists", "item_json_exists", "filename_pattern_ok",
        "sample_id_matches_filename", "decode_ok", "sha256_matches_manifest",
        "dimensions_match_manifest", "format_matches_manifest", "csv_item_json_exact", "caption_shape_ok",
    ]
    for rec in details:
        bad = [k for k in invariant_keys if rec.get(k) is not True]
        if rec["source"] == "HL Dataset":
            if rec["extracted_source_exists"] is not True or rec["selected_matches_extracted_sha256"] is not True:
                bad.append("extracted_source_link")
        elif (
            rec["archive_member_found"] is not True
            or rec["archive_member_matches_size_crc"] is not True
            or rec["archive_member_matches_sha256"] is not True
        ):
            bad.append("archive_link")
        if rec["hl_annotation_row_found"] is False or rec["hl_upstream_annotation_exact"] is False:
            bad.append("hl_annotation_link")
        if bad:
            failures.append({"file_name": rec["file_name"], "source": rec["source"], "failed": bad})

    summary = {
        "audit_date": "2026-09-08",
        "scope": "independent read-only recomputation against current image directory, release manifest, item JSON, CSV, extracted upstream tree, and local source archives",
        "manifest_rows": len(manifest_rows),
        "annotation_rows": len(annotation_rows),
        "item_json_files": len(list(ITEMS.glob("*.json"))),
        "item_json_parse_errors": item_parse_errors,
        "image_files_total": len(image_files),
        "image_extension_counts": dict(Counter(p.suffix.lower() for p in image_files)),
        "orphan_images": orphan_images,
        "missing_images": missing_images,
        "duplicate_sha256_groups": duplicate_groups,
        "per_source": per_source,
        "numbering": numbering,
        "checks": {key: {"pass": count_true(key), "fail": count_false(key)} for key in invariant_keys},
        "archive_checks": {
            "applicable_rows": sum(r["archive_member_found"] is not None for r in details),
            "member_found": count_true("archive_member_found"),
            "member_missing": count_false("archive_member_found"),
            "size_crc_match": count_true("archive_member_matches_size_crc"),
            "size_crc_mismatch": count_false("archive_member_matches_size_crc"),
            "sha256_match": count_true("archive_member_matches_sha256"),
            "sha256_mismatch": count_false("archive_member_matches_sha256"),
            "note": "HL has no local source archive in this workspace; its extracted images and annotation CSV are checked instead.",
        },
        "hl_annotation_checks": {
            "row_found": count_true("hl_annotation_row_found"),
            "row_missing": count_false("hl_annotation_row_found"),
            "manifest_annotation_exact": count_true("hl_upstream_annotation_exact"),
            "manifest_annotation_mismatch": count_false("hl_upstream_annotation_exact"),
        },
        "structural_failures": failures,
        "semantic_candidate_counts": dict(
            Counter(
                reason
                for rec in details
                for reason in str(rec["semantic_risk_reasons"]).split(";")
                if reason
            )
        ),
        "review_verdict_counts": dict(Counter(str(r["review_verdict"]) for r in details)),
        "formal_gold_true": sum(r["formal_gold"] is True for r in details),
        "formal_gold_false": sum(r["formal_gold"] is False for r in details),
        "semantic_scope_note": "Heuristics prioritize visual review; they do not prove a caption is correct or incorrect.",
    }

    detail_fields = sorted({k for rec in details for k in rec})
    with (OUT / "file_audit_details.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=detail_fields)
        writer.writeheader()
        writer.writerows(details)

    semantic_candidates = [r for r in details if r["semantic_risk_reasons"]]
    source_priority = {"HL Dataset": 0, "HAIVMet": 1, "IRFL": 2, "MM-MoralBench": 3}
    semantic_candidates.sort(
        key=lambda r: (
            source_priority.get(str(r["source"]), 9),
            1.0 if r["reference_coverage"] is None else float(r["reference_coverage"]),
            str(r["file_name"]),
        )
    )
    with (OUT / "semantic_review_candidates.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = [
            "sample_id", "annotation_item_id", "file_name", "source", "track", "source_id",
            "reference_coverage", "reference_jaccard", "semantic_risk_reasons",
        ]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(semantic_candidates)

    review_flags = [r for r in details if r["review_verdict"] != "accept"]
    with (OUT / "internal_review_flags.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = [
            "sample_id", "annotation_item_id", "file_name", "source", "track",
            "review_verdict", "review_issues", "annotation_method", "formal_gold",
        ]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(review_flags)

    (OUT / "audit_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "manifest_rows": summary["manifest_rows"],
        "image_files_total": summary["image_files_total"],
        "per_source": summary["per_source"],
        "archive_checks": summary["archive_checks"],
        "hl_annotation_checks": summary["hl_annotation_checks"],
        "structural_failure_count": len(failures),
        "semantic_candidate_counts": summary["semantic_candidate_counts"],
        "review_verdict_counts": summary["review_verdict_counts"],
        "formal_gold_false": summary["formal_gold_false"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
