# -*- coding: utf-8 -*-
"""Compute (but do not write) the audit-confirmed fixes for PhiloVista-1800.

Prints a single JSON plan to stdout:
  {"writes": {"F####.json": <full updated item JSON>, ...},
   "log": {...summary...}}

The caller is responsible for applying the plan to the items directory.
Track A: caption corrections on 6 items (verified with a VLM against the image).
Track B: sync stale review.verdict=revise where reviewer issues are demonstrably
         absent from the current captions -> revised_after_review + resolution.
Track C: keep 5 items on revise (need fresh human/VLM review).
"""
import json
import re
import glob
import hashlib
import sys
from collections import Counter

ITEMS_DIR = r"D:\Project\哲学AI多模态论文\PhiloVista-1800-GitHub\annotation_workflow\drafts\api_en\items"
CHECKED_AT = "2026-09-08T00:00:00Z"
CHECKED_BY = "codex_post_audit_fix_20260908"

CAPTION_FIXES = [
    ("F0481", ("object", 0),
     "A biplane on the right features an inline engine with visible cylinders, a two-spar upper wing, and a tail skid instead of wheels.",
     "A biplane on the right features an exposed radial engine with cylinders arranged in a star pattern around the crankcase, a two-spar upper wing, and a tail skid instead of wheels.",
     "object[0]: corrected engine type from 'inline engine' to exposed radial engine after visual re-inspection (cylinders in star pattern)."),
    ("F1717", ("rationale", 0),
     "Uniforms match U.S. Air Force Operational Camouflage Pattern (OCP) with visible rank insignia on collars, suggesting active-duty status.",
     "The uniforms match the U.S. Air Force Airman Battle Uniform (ABU) digital tiger-stripe pattern in gray-green tones; no insignia or name tapes are legible, so the wearers' service status cannot be determined from the image alone.",
     "rationale[0]: corrected uniform pattern from OCP to ABU digital tiger-stripe and removed the unsupported active-duty status inference."),
    ("F1717", ("object", 0),
     "A man in center foreground wears a green knit cap, OCP uniform, and carries a red folder in his left hand while pulling a black rolling suitcase with his right hand.",
     "A man in center foreground wears a green knit cap, an ABU digital tiger-stripe uniform, and carries a red folder in his left hand while pulling a black rolling suitcase with his right hand.",
     "object[0]: corrected uniform pattern reference from OCP to ABU digital tiger-stripe."),
    ("F1717", ("anchor", None),
     "uniforms with name tapes",
     "uniforms without legible name tapes",
     "philosophy P1 visual anchor: name tapes are not legible in the image; anchor reworded accordingly."),
    ("F0753", ("rationale", 1),
     "The apparatus appears functional and actively engaged, given the hand placement and focused attention",
     "The hand placement on the cylinder and the group's focused attention suggest the apparatus is being inspected or demonstrated; whether it is currently running cannot be determined from the static image",
     "rationale[1]: replaced the unsupported 'functional and actively engaged' claim with an inspection/demonstration framing that flags the static-image limitation."),
    ("F1063", ("action", 2),
     "Sunlight filters through leaves, casting moving shadows across the ground and objects, implying a daytime scene with gentle breeze or leaf movement.",
     "Sunlight filters through leaves, casting a static pattern of dappled light and shadow across the ground and objects, indicating a daytime scene; any motion of leaves or shadows cannot be determined from a single still image.",
     "action[2]: removed the unsupported 'moving shadows' / breeze inference from the static image."),
    ("F1241", ("object", 4),
     "The trackpad features a green horizontal strip with black markings resembling circuit traces; text above it reads 'DELL' and 'OPTIPLEX', but other characters are illegible.",
     "The trackpad features a green horizontal strip with black markings resembling circuit traces; the small text above it is garbled, illegible pseudo-text typical of generated imagery and does not form readable brand names.",
     "object[4]: removed the unsupported brand reading 'DELL'/'OPTIPLEX'; the marking is illegible generative pseudo-text."),
    ("F1765", ("object", 3),
     "No other individuals are visible in the image; the candidate\u2019s claim of 'at least five other individuals' is incorrect",
     "No other individuals are visible anywhere else in the image; the rider is the only person in the frame",
     "object[3]: removed workflow meta-commentary from the image description."),
]

KEEP_REVISE = {
    "PHL1800_HL_0404",
    "PHL1800_HL_0385",
    "PHL1800_HL_0394",
    "PHL1800_HL_0309",
    "PHL1800_HL_0105",
    "PHL1800_IRFL_0441",
    "PHL1800_HL_0161",
    "PHL1800_IRFL_0248",
    "PHL1800_HL_0366",
}
TRACK_A_IDS = {"PHL1800_HL_0458", "PHL1800_HL_0278", "PHL1800_HL_0368",
               "PHL1800_HL_0006", "PHL1800_HAIV_0222", "PHL1800_HL_0531"}
MANUAL_REVIEWED = {
    "PHL1800_HL_0048", "PHL1800_HL_0464", "PHL1800_HAIV_0119", "PHL1800_HL_0357",
    "PHL1800_HL_0046", "PHL1800_HL_0052", "PHL1800_IRFL_0035", "PHL1800_HAIV_0223",
    "PHL1800_HL_0267", "PHL1800_HAIV_0450", "PHL1800_HL_0041", "PHL1800_HL_0297",
    "PHL1800_HL_0007", "PHL1800_HL_0045", "PHL1800_HL_0009", "PHL1800_HL_0351",
    "PHL1800_HL_0307", "PHL1800_HL_0067", "PHL1800_HL_0439", "PHL1800_HL_0130",
    "PHL1800_HL_0416", "PHL1800_HL_0356", "PHL1800_HL_0391", "PHL1800_HL_0071",
    "PHL1800_HL_0172", "PHL1800_MM_0034", "PHL1800_HL_0197", "PHL1800_HL_0471",
    "PHL1800_IRFL_0311",
    # mixed-quote items resolved by manual sentence review
    "PHL1800_HL_0462", "PHL1800_HL_0019", "PHL1800_HL_0352", "PHL1800_HL_0410",
    "PHL1800_HL_0119", "PHL1800_IRFL_0293", "PHL1800_HL_0182", "PHL1800_HL_0370",
    "PHL1800_HAIV_0121", "PHL1800_HL_0533", "PHL1800_IRFL_0324", "PHL1800_HL_0185",
    "PHL1800_HL_0434", "PHL1800_HAIV_0060", "PHL1800_HL_0375", "PHL1800_MM_0098",
    "PHL1800_HL_0504", "PHL1800_IRFL_0283", "PHL1800_IRFL_0062", "PHL1800_HL_0065",
    "PHL1800_HL_0310", "PHL1800_IRFL_0225", "PHL1800_HL_0420", "PHL1800_HL_0207",
    "PHL1800_HL_0399", "PHL1800_MM_0036", "PHL1800_HAIV_0445", "PHL1800_HL_0162",
}
NUMWORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}


def nums_in(t):
    vals = set()
    for w, n in NUMWORDS.items():
        if re.search(r"\b" + w + r"\b", t):
            vals.add(n)
    for d in re.findall(r"\b(\d{1,3})\b", t):
        vals.add(int(d))
    return vals


def caption_sha256(caps):
    blob = json.dumps(caps, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def quoted_phrases(issue_text):
    q = [a or b for a, b in re.findall(r"'([^']{3,60})'|\"([^\"]{3,60})\"", issue_text)]
    return [x for x in q if x]


def classify(j):
    sid = j["sample_id"]
    if sid in MANUAL_REVIEWED:
        return "manual_sentence_review"
    il = " ".join(j["review"]["issues"]).lower()
    bl = " ".join(" ".join(v) for v in j["captions"].values()).lower()
    q = quoted_phrases(il)
    if q:
        present = [x for x in q if x.lower() in bl]
        absent = [x for x in q if x.lower() not in bl]
        if absent and not present:
            return "issue_referenced_error_absent_from_captions"
        return None
    inums, bnums = nums_in(il), nums_in(bl)
    if inums and (inums - bnums):
        return "issue_count_values_absent_from_captions"
    return None


def load_items():
    by_sid = {}
    for fname in sorted(glob.glob(ITEMS_DIR + "\\*.json")):
        base = fname.rsplit("\\", 1)[-1]
        if not re.fullmatch(r"F\d{4}\.json", base):
            continue
        with open(fname, encoding="utf-8") as fh:
            j = json.load(fh)
        by_sid[j["sample_id"]] = (base, j)
    return by_sid


def main():
    log = {"caption_fixes": [], "verdict_updates": [], "kept_revise": [],
           "unchanged": 0, "checked_at": CHECKED_AT, "checked_by": CHECKED_BY}
    by_sid = load_items()

    fix_notes = {}
    for item_id, field, old, new, note in CAPTION_FIXES:
        hit = next(((fn, jj) for fn, jj in by_sid.values()
                    if jj["annotation_item_id"] == item_id), None)
        assert hit, item_id
        fname, j = hit
        if field[1] is None:
            anchors = j["philosophy_interpretations"][0]["visual_anchors"]
            idx = next(i for i, a in enumerate(anchors) if a == old)
            anchors[idx] = new
        else:
            cap = j["captions"][field[0]][field[1]]
            assert cap == old, (item_id, field, cap[:80])
            j["captions"][field[0]][field[1]] = new
        fix_notes.setdefault(item_id, []).append(note)
        log["caption_fixes"].append(
            {"item": item_id, "sample_id": j["sample_id"], "field": str(field),
             "old": old, "new": new})

    for sid in TRACK_A_IDS:
        fname, j = by_sid[sid]
        j["review"] = {
            "reviewer_model": "codex_visual_audit",
            "verdict": "revised_by_audit_visual_inspection",
            "issues": ["Post-audit fix (2026-09-08): " + " ".join(fix_notes[j["annotation_item_id"]])],
            "resolution": {
                "status": "captions_corrected_after_visual_reinspection",
                "checked_by": CHECKED_BY,
                "method": "visual_reverification_with_vlm",
                "checked_at_utc": CHECKED_AT,
                "caption_sha256": caption_sha256(j["captions"]),
            },
        }

    writes = {}
    for sid, (fname, j) in by_sid.items():
        if sid in TRACK_A_IDS:
            writes[fname] = j
            continue
        if j["review"]["verdict"] != "revise":
            log["unchanged"] += 1
            continue
        if sid in KEEP_REVISE:
            log["kept_revise"].append(sid)
            continue
        m = classify(j)
        if m is None:
            log["kept_revise"].append(sid + " (UNCLASSIFIED)")
            continue
        j["review"]["verdict"] = "revised_after_review"
        j["review"]["resolution"] = {
            "status": "reviewer_issues_resolved_in_current_captions",
            "checked_by": CHECKED_BY,
            "method": m,
            "checked_at_utc": CHECKED_AT,
            "caption_sha256": caption_sha256(j["captions"]),
        }
        writes[fname] = j
        log["verdict_updates"].append({"sample_id": sid, "method": m})

    print(json.dumps({"writes": writes, "log": log}, ensure_ascii=False))
    sys.stderr.write("caption_fixes=%d verdict_updates=%d kept=%d unchanged=%d methods=%s\n" % (
        len(log["caption_fixes"]), len(log["verdict_updates"]), len(log["kept_revise"]),
        log["unchanged"], Counter(u["method"] for u in log["verdict_updates"])))


if __name__ == "__main__":
    main()
