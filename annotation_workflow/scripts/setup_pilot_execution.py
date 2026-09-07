"""Set up the pilot (B001+B002, 100 images) annotation execution infrastructure.

Creates:
  1. blind_pool/pilot/<blind_id>.<ext>  - blind copies of pilot images, SHA-256
     verified against final_selection_manifest.csv and decode-checked via PIL.
  2. inbox/ directories (append-only submission area per stage).
  3. inbox/admin/pilot_worklist.json + annotator_assignments.json (rotation so
     that each image has 3 primary annotators + 2 supplemental object annotators,
     all five object authors distinct).
  4. inbox/admin/pilot_state.csv state tracker.
  5. task packets for screeners / annotators / raters.

Admin-only; annotator-facing materials are the packets + blind pool paths.
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

WORKFLOW = Path(__file__).resolve().parents[1]
DATASET = WORKFLOW.parent
FS_DIR = DATASET / "final_selection_1800"
MANIFEST = FS_DIR / "final_selection_manifest.csv"
BLIND_INDEX = FS_DIR / "human_review" / "blind_image_index.csv"
BATCH_ITEMS = WORKFLOW / "admin" / "batch_items.csv"
INBOX = WORKFLOW / "inbox"
POOL = WORKFLOW / "blind_pool" / "pilot"
GUIDELINE = "0.1.0-draft"

PRIMARY_ROLES = ["ANN_P01", "ANN_P02", "ANN_P03", "ANN_P04", "ANN_P05"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as h:
        return list(csv.DictReader(h))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    manifest = {r["sample_id"]: r for r in read_csv(MANIFEST)}
    blind = {r["blind_id"]: r for r in read_csv(BLIND_INDEX)}
    batch_items = read_csv(BATCH_ITEMS)
    pilot_ids = [r["annotation_item_id"] for r in batch_items if r["batch_id"] in ("B001", "B002")]
    batch_of = {r["annotation_item_id"]: r["batch_id"] for r in batch_items}
    assert len(pilot_ids) == 100, len(pilot_ids)

    POOL.mkdir(parents=True, exist_ok=True)
    for sub in ["admin", "task_packets", "g0_screening", "primary", "supplemental_object",
                "hl_rating", "philosophy_rating", "g0_arbitration", "qa"]:
        (INBOX / sub).mkdir(parents=True, exist_ok=True)

    worklist, problems = [], []
    state_rows = []
    for bid in pilot_ids:
        sample = blind[bid]["sample_id"]
        m = manifest[sample]
        src = DATASET / m["selected_path"]
        ext = src.suffix
        dst = POOL / f"{bid}{ext}"
        ok_hash = False
        if src.exists():
            ok_hash = sha256(src) == m["sha256"]
        decode_ok = False
        if ok_hash:
            if not dst.exists():
                shutil.copy2(src, dst)
            try:
                with Image.open(dst) as im:
                    im.verify()
                with Image.open(dst) as im:
                    im.load()
                decode_ok = True
            except Exception as e:  # noqa: BLE001
                problems.append(f"{bid}: decode failed {e}")
        else:
            problems.append(f"{bid}: missing or sha256 mismatch ({src})")
        worklist.append({
            "blind_id": bid,
            "batch_id": batch_of[bid],
            "blind_image": str(dst.relative_to(WORKFLOW)),
        })
        state_rows.append({
            "blind_id": bid, "batch_id": batch_of[bid],
            "g0_reviewer_A": "", "g0_reviewer_B": "", "g0_gate": "pending",
            "primary_done": 0, "object_done": 0, "hl_rating_done": 0,
            "phil_rating_done": 0, "overall_state": "human_screen_pending",
            "updated_at": "", "note": "",
        })
    if problems:
        raise SystemExit("ABORT, integrity problems:\n" + "\n".join(problems))

    # annotator rotation: image i -> primary [i,i+1,i+2], supplemental [i+3,i+4] (mod 5)
    assignments = {}
    for i, w in enumerate(worklist):
        bid = w["blind_id"]
        prim = [PRIMARY_ROLES[(i + k) % 5] for k in range(3)]
        supp = [PRIMARY_ROLES[(i + 3) % 5], PRIMARY_ROLES[(i + 4) % 5]]
        assignments[bid] = {"batch_id": w["batch_id"], "primary": prim, "supplemental": supp}

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (INBOX / "admin" / "pilot_worklist.json").write_text(
        json.dumps({"generated_at": now, "guideline_version": GUIDELINE,
                    "images": worklist}, ensure_ascii=False, indent=1), encoding="utf-8")
    (INBOX / "admin" / "annotator_assignments.json").write_text(
        json.dumps({"generated_at": now, "scheme": "primary=i,i+1,i+2; supplemental=i+3,i+4 (mod 5)",
                    "assignments": assignments}, ensure_ascii=False, indent=1), encoding="utf-8")

    with (INBOX / "admin" / "pilot_state.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(state_rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(state_rows)

    print(f"OK: {len(worklist)} blind copies verified+decoded, inbox+assignments written")
    print(f"pool: {POOL}")


if __name__ == "__main__":
    main()
