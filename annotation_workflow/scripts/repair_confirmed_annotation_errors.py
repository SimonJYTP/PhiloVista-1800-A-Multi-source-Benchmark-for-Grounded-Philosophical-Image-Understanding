from __future__ import annotations

import hashlib
import json
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKFLOW = Path(__file__).resolve().parents[1]
V3_ROOT = WORKFLOW.parent
ITEM_DIR = WORKFLOW / "drafts" / "api_en" / "items"
AUDIT_DIR = V3_ROOT / "audit" / "annotation_quality_v1"
BACKUP_DIR = AUDIT_DIR / "original_items_before_repair"
REVISION_LOG = AUDIT_DIR / "PhiloVista-1800_repair_log.jsonl"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def philosophy(
    item_id: str,
    index: int,
    anchors: list[str],
    mappings: list[str],
    concepts: list[str],
    interpretation: str,
    alternative: str,
    limitation: str,
    sufficiency: str,
) -> dict[str, Any]:
    return {
        "candidate_id": f"AI_{item_id}_P{index}",
        "visual_anchors": anchors,
        "symbolic_mapping": mappings,
        "concept_ids": concepts,
        "interpretation": interpretation,
        "alternative_interpretations": [alternative],
        "limitations": [limitation],
        "sufficiency": sufficiency,
    }


REPAIRS: dict[str, dict[str, Any]] = {
    "F0571": {
        "target_subject": "two mixed-martial-arts fighters exchanging strikes inside a fenced arena",
        "captions": {
            "scene": [
                "Two shirtless fighters compete at close range inside a fenced combat arena.",
                "The canvas floor carries several colored sponsor marks and boundary lines.",
                "A referee or official is partly visible behind the fighters near the cage.",
            ],
            "action": [
                "The fighter on the right drives a gloved fist toward the other fighter's head.",
                "The fighter on the left bends forward while extending an arm across his opponent's upper body.",
                "Both fighters lean into the exchange while keeping their other hands close to their bodies.",
            ],
            "rationale": [
                "Their gloves, posture, and close contact indicate that they are actively competing rather than posing.",
                "The fenced enclosure and marked canvas are consistent with an organized combat-sports match.",
                "The lowered head may be an attempt to evade, brace, or close distance, but the exact tactic is not visually certain.",
            ],
            "object": [
                "Two muscular shirtless men wearing padded gloves and dark shorts occupy the center of the frame.",
                "One fighter's fist is positioned beside the other fighter's face during the exchange.",
                "A black chain-link fence forms the boundary of the competition area behind them.",
                "Bright red, blue, black, and white logos are printed across the pale canvas floor.",
                "Only the lower legs of a dark-clothed official are visible in the background.",
            ],
        },
        "rationale_support": ["visual_support", "commonsense_inference", "insufficient_evidence"],
        "text_dependency": "low",
        "philosophy_interpretations": [
            philosophy("F0571", 1, ["two fighters exchanging blows", "fenced competition area"], ["fence and rules → bounded conflict"], ["power_conflict", "freedom_constraint"], "The image presents aggression inside an agreed structure, suggesting that social rules can contain conflict without eliminating its force.", "It can be read simply as a documentary sports photograph without a broader claim about social order.", "The image does not show the competitors' consent, rules, or events before and after this instant.", "plausible"),
            philosophy("F0571", 2, ["one fighter bent forward", "a fist near his head"], ["exposed posture → bodily vulnerability"], ["ethics_responsibility", "power_conflict"], "The unequal positions captured in this instant foreground how power is experienced through bodily vulnerability and the capacity to cause harm.", "The apparent imbalance may last only a fraction of a second and may not represent the match as a whole.", "A still frame cannot establish dominance, injury, or either fighter's moral intent.", "plausible"),
            philosophy("F0571", 3, ["both fighters leaning into contact", "gloved hands"], ["protective gloves → restraint within risk"], ["choice_journey", "ethics_responsibility"], "The protective equipment alongside deliberate physical risk can be interpreted as a negotiated balance between personal choice and responsibility for harm.", "The gloves may be required equipment with no intended symbolic significance.", "The photograph alone cannot establish why either person chose to participate.", "insufficient"),
        ],
    },
    "F0793": {
        "target_subject": "a smiling man standing behind a white duck in a decorated kitchen",
        "captions": {
            "scene": [
                "A digitally rendered kitchen is decorated with a small Christmas tree and holiday ornaments.",
                "A man in a red shirt and green festive apron stands behind a countertop beside a white duck.",
                "A large speech bubble above the man contains explicit English text about sexual intent toward the bird.",
            ],
            "action": [
                "The man stands with his hands near his hips and smiles toward the viewer.",
                "The duck stands upright on the countertop in front of the man's apron.",
                "The speech bubble attributes an explicit statement about the duck to the man.",
            ],
            "rationale": [
                "The apron, food, and kitchen setting suggest a staged food-preparation scene, although no cooking action is visible.",
                "The Christmas decorations establish a holiday theme around the otherwise incongruous placement of a live bird on the counter.",
                "The explicit text supplies the scenario's disturbing intent, which cannot be inferred from the man's pose alone.",
            ],
            "object": [
                "A muscular dark-haired man wears a red polo shirt and a green apron decorated with a small Santa figure.",
                "A white duck with an orange bill and orange feet stands on the kitchen counter.",
                "A small decorated Christmas tree with a white star stands at the left side of the counter.",
                "A shallow white dish holds a mound of white granular material near the duck.",
                "A white speech bubble contains explicit black English text concerning sexual contact with the animal.",
            ],
        },
        "rationale_support": ["commonsense_inference", "visual_support", "visual_support"],
        "text_dependency": "high",
        "philosophy_interpretations": [
            philosophy("F0793", 1, ["explicit speech bubble", "live duck beside the man"], ["stated intent toward an animal → disregard for nonhuman agency"], ["ethics_responsibility", "power_conflict"], "The text-image combination raises an ethical question about power over a nonhuman being whose consent is impossible within the depicted scenario.", "The image may be constructed as an intentionally offensive test case rather than a representation of an intended act.", "The ethical reading depends strongly on the speech-bubble text and not on visible physical conduct.", "plausible"),
            philosophy("F0793", 2, ["smiling frontal pose", "festive kitchen decorations", "explicit text"], ["cheerful appearance versus harmful statement → conflict between surface and meaning"], ["identity_appearance", "knowledge_truth"], "The contrast between a polished cheerful appearance and the explicit statement illustrates how outward presentation can conceal or normalize troubling content.", "The visual contrast may be generated for shock or absurd humor rather than to characterize a real person.", "The subject is synthetic-looking, and the image provides no reliable evidence about a real identity or belief.", "plausible"),
            philosophy("F0793", 3, ["digitally rendered surfaces", "speech bubble", "holiday props"], ["assembled visual cues → manufactured moral scenario"], ["knowledge_truth", "other_abstract_relation"], "The obviously constructed scene shows how images and text can manufacture a moral proposition that viewers may mistake for evidence about an event.", "It can also function only as a provocative meme whose content is not meant literally.", "Without provenance, the creator's aim and the degree of generative manipulation remain unknown.", "insufficient"),
        ],
    },
    "F1104": {
        "target_subject": "pedestrians gathered at and moving across a striped urban crosswalk",
        "captions": {
            "scene": [
                "A black-and-white street photograph shows a broad striped crosswalk in front of crowded storefronts.",
                "Numerous pedestrians occupy the curb and street beneath shop signs containing East Asian characters.",
                "Two light-colored umbrellas stand out among the people in the busy commercial setting.",
            ],
            "action": [
                "Several pedestrians stand near the curb facing the crosswalk.",
                "Other people walk laterally along the storefronts and across the edge of the street.",
                "Two pedestrians hold open umbrellas while waiting or moving with the crowd.",
            ],
            "rationale": [
                "The alignment of people at the curb suggests that some are waiting for a safe or permitted moment to cross.",
                "The dense shop signs and foot traffic indicate an active commercial street rather than an isolated roadway.",
                "The umbrellas may provide shade or protection from weather, but their exact purpose is not visible.",
            ],
            "object": [
                "Wide alternating dark and light stripes fill the foreground crosswalk.",
                "A row of adults in varied casual clothing stands across the middle of the image.",
                "Two open pale umbrellas are held above pedestrians near the left and center-right.",
                "Storefronts behind the crowd display many vertical and horizontal signs with East Asian writing.",
                "The monochrome photograph contains people walking in both directions at the sides of the waiting group.",
            ],
        },
        "rationale_support": ["commonsense_inference", "visual_support", "insufficient_evidence"],
        "text_dependency": "medium",
        "philosophy_interpretations": [
            philosophy("F1104", 1, ["people aligned at the curb", "striped crosswalk"], ["crosswalk → shared rule for coordinated movement"], ["social_existence", "freedom_constraint"], "The crowd's relation to the crosswalk suggests how individual movement becomes coordinated through common spatial rules.", "The people may not all be waiting to cross, and the alignment may be accidental.", "A still image does not show the traffic signal or whether anyone is following a rule.", "plausible"),
            philosophy("F1104", 2, ["many pedestrians", "faces oriented in different directions", "dense storefronts"], ["crowd → coexistence among strangers"], ["social_existence", "identity_appearance"], "The scene can be read as urban coexistence in which strangers share a space while remaining socially separate and visually anonymous.", "It may simply document ordinary pedestrian traffic without commenting on anonymity.", "The photograph gives no access to relationships or subjective feelings among the people.", "plausible"),
            philosophy("F1104", 3, ["commercial signs", "people moving beneath them"], ["advertising field → attention shaped by commerce"], ["labor_technology", "power_conflict"], "The visual density of shop signs around the pedestrians permits a reading of public attention as structured by commercial messages.", "The signs may only identify shops and need not dominate anyone's attention.", "Most text is not readable at this resolution, so its content and influence cannot be established.", "insufficient"),
        ],
    },
    "F1347": {
        "target_subject": "a seated passenger beside a bus window overlooking congested city traffic",
        "captions": {
            "scene": [
                "The photograph is taken from inside a bus or similar public vehicle looking through a large side window.",
                "Cars and minibuses queue between tall buildings on a bright urban street.",
                "A passenger's head and the back of a fabric-covered seat occupy the left foreground.",
            ],
            "action": [
                "The passenger leans forward with their head close to the seat back or window frame.",
                "Multiple vehicles wait or move slowly in dense traffic outside.",
                "The camera looks past the resting passenger toward the road and high-rise buildings.",
            ],
            "rationale": [
                "The closely spaced vehicles and limited gaps indicate congestion or slow traffic.",
                "The passenger's lowered head may indicate resting or looking downward, but the exact activity is unclear.",
                "The elevated viewpoint, interior seat, and window frame support the interpretation that the image was taken from public transport.",
            ],
            "object": [
                "A person's dark hair and partially hidden face appear above a pink patterned seat in the left foreground.",
                "A thick vertical window frame divides the vehicle interior from the street view.",
                "Several white vans, minibuses, and passenger cars fill multiple lanes below.",
                "Tall residential and commercial buildings rise closely along both sides of the road.",
                "Visible signs include a Shell logo and a high building sign reading 'CARITAS.'",
            ],
        },
        "rationale_support": ["visual_support", "insufficient_evidence", "visual_support"],
        "text_dependency": "low",
        "philosophy_interpretations": [
            philosophy("F1347", 1, ["passenger separated by a window", "dense traffic outside"], ["window → separation between observer and urban flow"], ["social_existence", "identity_appearance"], "The passenger's partial concealment beside the window can be read as a private moment occurring within the impersonal movement of a crowded city.", "The person may simply be looking down during an ordinary trip.", "The face and activity are mostly obscured, so isolation or introspection cannot be confirmed.", "plausible"),
            philosophy("F1347", 2, ["vehicles packed into lanes", "bus interior"], ["traffic queue → constrained collective mobility"], ["freedom_constraint", "labor_technology"], "The congested road illustrates how technologies designed for mobility can collectively restrict movement when many users depend on them at once.", "Traffic conditions may be temporary and do not by themselves represent a general technological paradox.", "A single frame cannot establish speed, duration, or the cause of congestion.", "plausible"),
            philosophy("F1347", 3, ["resting passenger", "high-rise corridor", "vehicle queue"], ["commute → time spent in transit"], ["time_mortality", "choice_journey"], "The juxtaposition of a resting passenger and slow traffic permits a reflection on everyday time consumed by necessary travel.", "The passenger's trip may be voluntary, brief, or recreational rather than burdensome.", "The image contains no timing information or evidence about the trip's purpose.", "insufficient"),
        ],
    },
    "F1661": {
        "target_subject": "a smiling man holding a white bird in a kitchen beneath an explicit speech bubble",
        "captions": {
            "scene": [
                "A digitally rendered kitchen scene shows a young man in an apron holding a large white bird.",
                "Cooked food, vegetables, and kitchen fixtures surround the man at a countertop.",
                "A speech bubble contains explicit English text suggesting sexual intent toward the bird.",
            ],
            "action": [
                "The man supports the bird horizontally with both hands and smiles toward the viewer.",
                "The bird holds its head upright while one leg hangs below its body.",
                "The speech bubble attributes an explicit proposal concerning the animal to the man.",
            ],
            "rationale": [
                "The apron and food-covered counter frame the subject as part of a staged kitchen scenario.",
                "Holding the live bird above prepared food creates a deliberate visual incongruity rather than showing an ordinary cooking step.",
                "The sexual meaning comes from the written statement and cannot be inferred from the pose alone.",
            ],
            "object": [
                "A young dark-haired man wears a blue shirt and brown apron in a wood-paneled kitchen.",
                "He holds a large white domestic bird with both hands at chest height.",
                "A platter of browned cooked food rests on the counter directly in front of him.",
                "Green vegetables, mushrooms, and an onion are arranged around the countertop.",
                "A white speech bubble above the man contains explicit black English text about sexual contact with the bird.",
            ],
        },
        "rationale_support": ["visual_support", "commonsense_inference", "visual_support"],
        "text_dependency": "high",
        "philosophy_interpretations": [
            philosophy("F1661", 1, ["man holding a bird", "explicit speech bubble"], ["stated sexual intent toward an animal → abuse of human power"], ["ethics_responsibility", "power_conflict"], "The explicit text turns an otherwise ambiguous hold into a scenario about the ethical limits of human power over an animal.", "The scene may be an intentionally offensive synthetic test image rather than a literal plan or event.", "No sexual act is visible, and the interpretation depends almost entirely on the text.", "plausible"),
            philosophy("F1661", 2, ["smiling expression", "polished kitchen", "disturbing text"], ["pleasant surface versus harmful statement → unreliable appearance"], ["identity_appearance", "knowledge_truth"], "The mismatch between a friendly visual presentation and the disturbing statement highlights why moral judgment cannot rely on appearance alone.", "The expression and composition may have been generated without coherent emotional intent.", "The image provides no evidence about a real person's character, beliefs, or actions.", "plausible"),
            philosophy("F1661", 3, ["live bird", "cooked food on counter", "synthetic rendering"], ["animal beside prepared meal → shifting status between subject and object"], ["ethics_responsibility", "other_abstract_relation"], "The placement of a living bird beside prepared food invites a question about when humans regard animals as subjects and when they reduce them to objects.", "The bird and meal may be juxtaposed only to create absurdity or shock.", "The creator's purpose and the relationship between the live bird and the food are not established.", "insufficient"),
        ],
    },
    "F1670": {
        "target_subject": "four women seated together on a couch during an informal indoor gathering",
        "captions": {
            "scene": [
                "Four women sit closely on a patterned couch in a warmly lit living room.",
                "Their bathrobe, hair towel, sleepwear, and casual poses suggest an informal at-home gathering.",
                "A framed landscape painting, plants, and a stained-glass lamp decorate the room behind them.",
            ],
            "action": [
                "The woman at the left reclines with her head tilted back while holding a bottle.",
                "The woman in the red robe holds a cigarette near her mouth while the center woman looks at an open laptop.",
                "The woman at the right lifts the hem of her pink polka-dot garment while holding a cigarette in her other hand.",
            ],
            "rationale": [
                "The relaxed clothing and shared couch suggest a private social gathering rather than a formal event.",
                "The laptop gives the center of the group a shared point of attention, although not everyone is looking at it.",
                "The bottle, cigarettes, and theatrical poses may indicate staged humor, but the participants' exact intentions are unknown.",
            ],
            "object": [
                "Four adult women occupy a brown patterned couch across the width of the image.",
                "The second woman wears a red robe and has a white towel wrapped around her hair.",
                "A gray Dell laptop is open on the lap of the dark-haired woman at the center.",
                "The woman at the right wears a pink polka-dot dress with dark lace trim and a matching hair accessory.",
                "A framed landscape painting hangs above the couch between a leafy plant and a stained-glass floor lamp.",
            ],
        },
        "rationale_support": ["commonsense_inference", "visual_support", "insufficient_evidence"],
        "text_dependency": "none",
        "philosophy_interpretations": [
            philosophy("F1670", 1, ["four women sharing a couch", "different postures and activities"], ["shared couch → coexistence without identical attention"], ["social_existence", "identity_appearance"], "The group embodies social togetherness without uniform behavior, suggesting that participation in a community does not require identical attention or self-presentation.", "The different poses may be arranged for a photograph rather than expressing distinct forms of participation.", "The image does not reveal the relationships among the women or whether the gathering is spontaneous.", "plausible"),
            philosophy("F1670", 2, ["open laptop at the center", "people looking in different directions"], ["screen → partial focus within face-to-face company"], ["labor_technology", "social_existence"], "The centrally placed laptop can be read as technology organizing a shared space while also dividing the group's attention.", "The laptop may be part of a shared activity and therefore increase rather than reduce social connection.", "Only one instant is visible, so the device's role in the gathering cannot be determined.", "plausible"),
            philosophy("F1670", 3, ["bathrobe and sleepwear", "cigarettes and bottle", "posed gestures"], ["domestic clothing → relaxed public self-presentation"], ["identity_appearance", "freedom_constraint"], "The casual dress and exaggerated poses permit a reading of private space as allowing forms of self-presentation that public settings might constrain.", "The scene may be staged entertainment whose clothing and gestures were selected by a photographer.", "The image alone cannot establish whether anyone feels free, constrained, or authentic.", "insufficient"),
        ],
    },
}


def main() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()

    repairs = deepcopy(REPAIRS)
    # This item is visually correct but contains one 113-word action caption and
    # an unnecessarily brittle exact-person count. Replace only those fields.
    repairs["F1036"] = {
        "captions.action": [
            "Several pedestrians stand in a loose group near the building entrance and along the sidewalk.",
            "A woman in a patterned skirt stands behind the low hedge near the red barrier.",
            "Other pedestrians walk past the group at the right edge of the frame.",
        ],
        "captions.object[4]": "People in summer clothing gather and pass along the sidewalk in front of the building.",
    }

    for item_id, patch in repairs.items():
        path = ITEM_DIR / f"{item_id}.json"
        original_bytes = path.read_bytes()
        record = json.loads(original_bytes.decode("utf-8"))

        if item_id == "F1036":
            if record.get("captions", {}).get("action") == patch["captions.action"] and record.get("captions", {}).get("object", [None] * 5)[4] == patch["captions.object[4]"]:
                print(json.dumps({"event": "skipped_already_repaired", "annotation_item_id": item_id}, ensure_ascii=False))
                continue
        elif record.get("method") == "ai_agent_direct_visual_reannotation_after_audit_non_independent" and record.get("provenance", {}).get("audit_revision", {}).get("reason_code") == "cross_image_annotation_mismatch":
            print(json.dumps({"event": "skipped_already_repaired", "annotation_item_id": item_id}, ensure_ascii=False))
            continue

        backup_path = BACKUP_DIR / path.name
        if not backup_path.exists():
            shutil.copy2(path, backup_path)

        if item_id == "F1036":
            record["captions"]["action"] = patch["captions.action"]
            record["captions"]["object"][4] = patch["captions.object[4]"]
            reason = "Replaced a 113-word action caption and brittle exact-person count after direct image inspection."
            changed_fields = ["captions.action", "captions.object[4]"]
        else:
            for field in ("target_subject", "captions", "rationale_support", "text_dependency", "philosophy_interpretations"):
                record[field] = patch[field]
            record["method"] = "ai_agent_direct_visual_reannotation_after_audit_non_independent"
            record["review"] = {
                "reviewer_model": "codex_visual_audit",
                "verdict": "revised_by_audit_visual_inspection",
                "issues": ["Previous fallback annotation described a different image; all semantic annotation fields were replaced after direct inspection of the mapped image."],
            }
            record.setdefault("provenance", {})["audit_revision"] = {
                "timestamp_utc": timestamp,
                "reason_code": "cross_image_annotation_mismatch",
                "source_backup": str(backup_path.relative_to(V3_ROOT)).replace("\\", "/"),
                "formal_gold": False,
            }
            reason = "Corrected a confirmed cross-image semantic mismatch after direct image inspection."
            changed_fields = ["target_subject", "captions", "rationale_support", "text_dependency", "philosophy_interpretations", "method", "review", "provenance.audit_revision"]

        new_bytes = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        temporary = path.with_suffix(".json.tmp")
        temporary.write_bytes(new_bytes)
        temporary.replace(path)
        log_entry = {
            "timestamp_utc": timestamp,
            "annotation_item_id": item_id,
            "reason": reason,
            "changed_fields": changed_fields,
            "original_sha256": digest(original_bytes),
            "revised_sha256": digest(new_bytes),
            "backup": str(backup_path.relative_to(V3_ROOT)).replace("\\", "/"),
        }
        with REVISION_LOG.open("a", encoding="utf-8", newline="") as handle:
            handle.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        print(json.dumps({"event": "repaired", "annotation_item_id": item_id, "changed_fields": changed_fields}, ensure_ascii=False))


if __name__ == "__main__":
    main()
