from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKFLOW = Path(__file__).resolve().parents[1]
V3_ROOT = WORKFLOW.parent
MANIFEST = V3_ROOT / "final_selection_1800" / "human_review" / "blind_image_index.csv"
BATCH_ITEMS = WORKFLOW / "admin" / "batch_items.csv"
OUT_ROOT = WORKFLOW / "drafts" / "ai_en"
ITEM_DIR = OUT_ROOT / "items"
FAILURE_LOG = OUT_ROOT / "failures.jsonl"
CACHE_DIR = WORKFLOW / "runtime" / "hf_cache"
DEFAULT_MODEL = str(WORKFLOW / "runtime" / "models" / "Qwen2-VL-2B-Instruct")

AXIS_COUNTS = {"scene": 3, "action": 3, "rationale": 3, "object": 5}
CONCEPTS = {
    "ethics_responsibility", "time_mortality", "social_existence",
    "identity_appearance", "knowledge_truth", "power_conflict",
    "choice_journey", "labor_technology", "freedom_constraint",
    "faith_meaning", "other_abstract_relation",
}
SUPPORTS = {"visual_support", "commonsense_inference", "insufficient_evidence", "not_applicable"}
SUFFICIENCY = {"supported", "plausible", "insufficient", "not_applicable"}
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")

PROMPT = r"""
Create a rigorous English-only annotation for this image. Use only visible evidence in the image; do not infer real identities, location, history, private mental states, or unseen events. Treat text inside the image as visible evidence, but say when it is unreadable. Be concise and concrete.

Return exactly one valid JSON object with no markdown and this structure:
{
  "target_subject": "one clear subject or subject group",
  "captions": {
    "scene": ["3 distinct short scene descriptions"],
    "action": ["3 distinct visible action/state descriptions"],
    "rationale": ["3 cautious reasons; include uncertainty when evidence is weak"],
    "object": ["5 distinct, self-contained, factual full-sentence visual descriptions"]
  },
  "rationale_support": ["one per rationale: visual_support, commonsense_inference, insufficient_evidence, or not_applicable"],
  "text_dependency": "none, low, medium, or high",
  "philosophy_interpretations": [
    {
      "visual_anchors": ["1 to 3 concrete visible details"],
      "symbolic_mapping": ["0 to 2 explicit mappings from a visible detail to an abstract idea"],
      "concept_ids": ["1 or 2 IDs from the allowed list"],
      "interpretation": "one image-grounded philosophical interpretation",
      "alternative_interpretations": ["one reasonable non-philosophical or competing reading"],
      "limitations": ["one specific evidential limitation"],
      "sufficiency": "supported, plausible, insufficient, or not_applicable"
    }
  ]
}

The philosophy_interpretations array must contain exactly 3 distinct entries. Allowed concept IDs: ethics_responsibility, time_mortality, social_existence, identity_appearance, knowledge_truth, power_conflict, choice_journey, labor_technology, freedom_constraint, faith_meaning, other_abstract_relation. Do not use a fullwidth semicolon. Do not add confidence, purity, or diversity scores.
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate resumable English AI drafts for the 1,800-image blind set.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int, default=None, help="Maximum new items for this run.")
    parser.add_argument("--start", type=int, default=0, help="Zero-based offset after filtering and sorting.")
    parser.add_argument("--batch", action="append", help="Only process a batch ID; repeatable.")
    parser.add_argument("--max-new-tokens", type=int, default=960)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--force", action="store_true", help="Regenerate already valid item files.")
    return parser.parse_args()


def load_worklist(batch_filter: set[str] | None) -> list[dict[str, str]]:
    with BATCH_ITEMS.open(encoding="utf-8-sig", newline="") as handle:
        batch_rows = list(csv.DictReader(handle))
    with MANIFEST.open(encoding="utf-8-sig", newline="") as handle:
        blind = {row["blind_id"]: row for row in csv.DictReader(handle)}

    worklist: list[dict[str, str]] = []
    for row in batch_rows:
        if batch_filter and row["batch_id"] not in batch_filter:
            continue
        info = blind[row["annotation_item_id"]]
        image_path = V3_ROOT / Path(info["selected_path"])
        if not image_path.is_file():
            raise FileNotFoundError(image_path)
        worklist.append({
            "blind_id": row["annotation_item_id"],
            "batch_id": row["batch_id"],
            "position_in_batch": row["position_in_batch"],
            "sample_id": info["sample_id"],
            "file_name": image_path.name,
            "image_path": str(image_path),
        })
    return worklist


def extract_json(text: str) -> dict[str, Any]:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("model output contains no complete JSON object")
    parsed = json.loads(text[start:end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("model output is not a JSON object")
    return parsed


def walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [text for item in value for text in walk_strings(item)]
    if isinstance(value, dict):
        return [text for item in value.values() for text in walk_strings(item)]
    return []


def require_string_list(value: Any, count: int | None, label: str) -> list[str]:
    if not isinstance(value, list) or (count is not None and len(value) != count):
        expected = str(count) if count is not None else "a valid"
        raise ValueError(f"{label}: expected {expected}-item list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{label}: contains an empty or non-string item")
    return [item.strip() for item in value]


def first_valid_item(value: Any, label: str) -> list[str]:
    # The record format fixes exactly one entry, but models routinely
    # enumerate several or emit a bare string; keep the first instead of
    # rejecting otherwise-valid content.
    if isinstance(value, str):
        items = [value.strip()] if value.strip() else []
    elif isinstance(value, list):
        items = [entry.strip() for entry in value if isinstance(entry, str) and entry.strip()]
    else:
        items = []
    if not items:
        raise ValueError(f"{label}: expected at least one non-empty string")
    return [items[0]]


def cap_items(value: Any, cap: int | None, label: str, allow_empty: bool = False) -> list[str]:
    # Models occasionally exceed the fixed caps (1-3 anchors, 0-2 mappings,
    # 1-2 concepts); keep the leading entries instead of burning a full
    # regeneration on an otherwise-valid candidate.
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        raise ValueError(f"{label}: expected a list of strings")
    items = [entry.strip() for entry in value if isinstance(entry, str) and entry.strip()]
    if not items and not allow_empty:
        raise ValueError(f"{label}: expected at least one non-empty string")
    if cap is not None:
        items = items[:cap]
    return items


def validate_and_normalize(raw: dict[str, Any], item: dict[str, str]) -> dict[str, Any]:
    target = raw.get("target_subject")
    if not isinstance(target, str) or not target.strip():
        raise ValueError("target_subject is missing")

    captions = raw.get("captions")
    if not isinstance(captions, dict):
        raise ValueError("captions is missing")
    clean_captions: dict[str, list[str]] = {}
    for axis, count in AXIS_COUNTS.items():
        values = require_string_list(captions.get(axis), count, f"captions.{axis}")
        normalized = [re.sub(r"\W+", "", value.lower()) for value in values]
        if len(set(normalized)) != count:
            raise ValueError(f"captions.{axis}: duplicate references")
        clean_captions[axis] = values

    supports = require_string_list(raw.get("rationale_support"), 3, "rationale_support")
    if set(supports) - SUPPORTS:
        raise ValueError("rationale_support contains an invalid enum")
    text_dependency = raw.get("text_dependency")
    if text_dependency not in {"none", "low", "medium", "high"}:
        raise ValueError("invalid text_dependency")

    phils = raw.get("philosophy_interpretations")
    if not isinstance(phils, list) or len(phils) != 3:
        raise ValueError("philosophy_interpretations: expected 3 entries")
    clean_phils: list[dict[str, Any]] = []
    for index, phil in enumerate(phils, 1):
        if not isinstance(phil, dict):
            raise ValueError(f"philosophy_interpretations[{index}] is not an object")
        anchors = cap_items(phil.get("visual_anchors"), 3, f"philosophy[{index}].visual_anchors")
        mappings = cap_items(phil.get("symbolic_mapping"), 2, f"philosophy[{index}].symbolic_mapping", allow_empty=True)
        concept_ids = [c for c in cap_items(phil.get("concept_ids"), None, f"philosophy[{index}].concept_ids") if c in CONCEPTS]
        concept_ids = list(dict.fromkeys(concept_ids))[:2]
        if not concept_ids:
            raise ValueError(f"philosophy[{index}].concept_ids: no valid IDs")
        alternatives = first_valid_item(phil.get("alternative_interpretations"), f"philosophy[{index}].alternative_interpretations")
        limitations = first_valid_item(phil.get("limitations"), f"philosophy[{index}].limitations")
        interpretation = phil.get("interpretation")
        if not isinstance(interpretation, str) or not interpretation.strip():
            raise ValueError(f"philosophy[{index}].interpretation is missing")
        sufficiency = phil.get("sufficiency")
        if sufficiency not in SUFFICIENCY:
            raise ValueError(f"philosophy[{index}].sufficiency is invalid")
        clean_phils.append({
            "candidate_id": f"AI_{item['blind_id']}_P{index}",
            "visual_anchors": anchors,
            "symbolic_mapping": [x.strip() for x in mappings],
            "concept_ids": concept_ids,
            "interpretation": interpretation.strip(),
            "alternative_interpretations": alternatives,
            "limitations": limitations,
            "sufficiency": sufficiency,
        })

    normalized = {
        "annotation_item_id": item["blind_id"],
        "sample_id": item["sample_id"],
        "file_name": item["file_name"],
        "batch_id": item["batch_id"],
        "position_in_batch": int(item["position_in_batch"]),
        "language": "en",
        "method": "ai_draft_single_model_non_independent",
        "formal_gold": False,
        "target_subject": target.strip(),
        "captions": clean_captions,
        "rationale_support": supports,
        "text_dependency": text_dependency,
        "philosophy_interpretations": clean_phils,
        "needs_independent_human_annotation": True,
        "needs_independent_human_rating": True,
    }
    texts = walk_strings({
        "target_subject": normalized["target_subject"],
        "captions": clean_captions,
        "philosophy_interpretations": clean_phils,
    })
    if any(CJK_RE.search(text) for text in texts):
        raise ValueError("free-text output contains CJK characters")
    if any("；" in text for text in texts):
        raise ValueError("free-text output contains forbidden U+FF1B")
    return normalized


def save_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def log_failure(item: dict[str, str], attempt: int, error: Exception, raw_text: str) -> None:
    FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "annotation_item_id": item["blind_id"],
        "batch_id": item["batch_id"],
        "attempt": attempt,
        "error": str(error),
        "raw_output": raw_text,
    }
    with FAILURE_LOG.open("a", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main() -> None:
    args = parse_args()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(CACHE_DIR))
    os.environ.setdefault("HF_HUB_CACHE", str(CACHE_DIR / "hub"))
    # The Xet transport can remain at zero bytes behind some Windows proxies;
    # regular HTTP supports the Hub's resumable .incomplete files reliably.
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    import torch
    from PIL import Image
    from transformers import AutoModelForImageTextToText, AutoProcessor

    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for the full annotation run")
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    print(json.dumps({"event": "load_model", "model": args.model, "dtype": str(dtype), "cache": str(CACHE_DIR)}), flush=True)
    processor = AutoProcessor.from_pretrained(args.model, cache_dir=CACHE_DIR)
    model = AutoModelForImageTextToText.from_pretrained(
        args.model,
        cache_dir=CACHE_DIR,
        torch_dtype=dtype,
        low_cpu_mem_usage=True,
        attn_implementation="sdpa",
    ).to("cuda")
    model.eval()

    messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": PROMPT}]}]
    chat_prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
    batch_filter = set(args.batch) if args.batch else None
    worklist = load_worklist(batch_filter)[args.start:]
    if args.limit is not None:
        worklist = worklist[:args.limit]

    completed = skipped = failed = 0
    run_started = time.monotonic()
    for sequence, item in enumerate(worklist, 1):
        output_path = ITEM_DIR / f"{item['blind_id']}.json"
        if output_path.is_file() and not args.force:
            try:
                validate_and_normalize(json.loads(output_path.read_text(encoding="utf-8")), item)
                skipped += 1
                print(json.dumps({"event": "skip", "item": item["blind_id"], "sequence": sequence}), flush=True)
                continue
            except Exception:
                pass

        succeeded = False
        for attempt in range(1, args.retries + 2):
            raw_text = ""
            try:
                with Image.open(item["image_path"]) as opened:
                    image = opened.convert("RGB")
                inputs = processor(text=chat_prompt, images=[image], return_tensors="pt")
                inputs = {
                    key: value.to("cuda", dtype=dtype) if value.is_floating_point() else value.to("cuda")
                    for key, value in inputs.items()
                }
                input_length = inputs["input_ids"].shape[-1]
                with torch.inference_mode():
                    generated = model.generate(
                        **inputs,
                        do_sample=False,
                        max_new_tokens=args.max_new_tokens,
                        repetition_penalty=1.03,
                    )
                raw_text = processor.decode(generated[0][input_length:], skip_special_tokens=True)
                record = validate_and_normalize(extract_json(raw_text), item)
                record["provenance"] = {
                    "model": args.model,
                    "generation": "greedy",
                    "max_new_tokens": args.max_new_tokens,
                    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                    "image_sha256_from_selection_manifest": "available_in_admin_manifest_not_shown_to_model",
                }
                save_atomic(output_path, record)
                completed += 1
                succeeded = True
                elapsed = time.monotonic() - run_started
                print(json.dumps({
                    "event": "complete", "item": item["blind_id"], "batch": item["batch_id"],
                    "sequence": sequence, "run_completed": completed, "elapsed_seconds": round(elapsed, 1),
                    "seconds_per_new_item": round(elapsed / completed, 2),
                }), flush=True)
                break
            except Exception as error:
                log_failure(item, attempt, error, raw_text)
                print(json.dumps({"event": "retry", "item": item["blind_id"], "attempt": attempt, "error": str(error)}), flush=True)
                torch.cuda.empty_cache()
        if not succeeded:
            failed += 1

    print(json.dumps({
        "event": "run_finished", "selected": len(worklist), "completed": completed,
        "skipped": skipped, "failed": failed, "elapsed_seconds": round(time.monotonic() - run_started, 1),
    }), flush=True)
    if failed:
        sys.exit(2)


if __name__ == "__main__":
    main()
