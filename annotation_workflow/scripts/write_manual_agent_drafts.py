from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
spec = importlib.util.spec_from_file_location("schema", Path(__file__).resolve().parent / "generate_all_english_ai_drafts.py")
schema = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schema)

OUT_DIR = Path(__file__).resolve().parents[1] / "drafts" / "api_en" / "items"

MANUAL_DRAFTS: dict[str, dict] = {
    "F1670": {
        "target_subject": "an orange tabby cat balancing on a low dividing wall",
        "captions": {
            "scene": [
                "A low wall separates a paved courtyard with potted plants from an area with a whitewashed surface.",
                "An orange tabby cat stands on the wall under soft daylight.",
                "Plants in containers line one side of the wall, adding green tones to the muted background.",
            ],
            "action": [
                "The cat rises on its hind legs with front paws resting on the top of the wall.",
                "The cat turns its head toward the far side of the wall, apparently inspecting it.",
                "Its tail extends behind for balance while the body leans slightly forward.",
            ],
            "rationale": [
                "The raised paws and forward lean suggest the cat is preparing to cross the wall.",
                "The alert head orientation is consistent with curiosity about the opposite side.",
                "The posture may also reflect routine territorial patrol behavior, though intent is not visually knowable.",
            ],
            "object": [
                "An orange tabby cat with visible stripes stands with its front paws on a low wall.",
                "Several potted plants stand on shelves along one side of the courtyard.",
                "The wall has a rough light-colored surface with a flat narrow top.",
                "The paved ground shows rectangular tiles of muted tone.",
                "Soft daylight illuminates the scene without strong shadows.",
            ],
        },
        "rationale_support": ["visual_support", "commonsense_inference", "insufficient_evidence"],
        "text_dependency": "none",
        "philosophy_interpretations": [
            {
                "visual_anchors": ["cat poised on the wall", "two contrasting sides"],
                "symbolic_mapping": ["wall as a boundary between two worlds"],
                "concept_ids": ["choice_journey", "freedom_constraint"],
                "interpretation": "The cat poised on a dividing wall evokes the existential moment of choosing between two worlds, freedom exercised at the edge of a constraint.",
                "alternative_interpretations": ["The scene may simply record a pet exploring its usual surroundings without symbolic meaning."],
                "limitations": ["No narrative context confirms that the cat's crossing carries any intent beyond ordinary movement."],
                "sufficiency": "plausible",
            },
            {
                "visual_anchors": ["potted plants on one side", "whitewashed surface on the other"],
                "symbolic_mapping": [],
                "concept_ids": ["social_existence"],
                "interpretation": "The contrast between cultivated greenery and blank plaster can be read as the human ordering of nature into tamed and neutralized zones.",
                "alternative_interpretations": ["The two sides may result from ordinary maintenance choices rather than any statement about nature."],
                "limitations": ["The image shows only a fragment of the environment, so the contrast may be coincidental."],
                "sufficiency": "plausible",
            },
            {
                "visual_anchors": ["balanced posture", "extended tail"],
                "symbolic_mapping": ["balance to a temporarily held equilibrium"],
                "concept_ids": ["time_mortality", "other_abstract_relation"],
                "interpretation": "The cat's suspended balance on a narrow ledge briefly freezes motion into stillness, a quiet emblem of transience held between one step and the next.",
                "alternative_interpretations": ["The posture is an ordinary physical accommodation with no temporal symbolism."],
                "limitations": ["A single photographic frame cannot establish anything about duration or change."],
                "sufficiency": "insufficient",
            },
        ],
    },
    "F0571": {
        "target_subject": "two people sharing a meal at a food-laden restaurant table",
        "captions": {
            "scene": [
                "An indoor dining space with wooden furniture and warm-toned walls contains a table covered with many shared dishes.",
                "Woven baskets and shelves suggest a rustic or home-style eatery.",
                "Two diners sit close together at the near side of the table during the meal.",
            ],
            "action": [
                "One person pours water or another drink into a cup.",
                "Another person holds food in one hand while eating.",
                "An empty high chair stands at the table, unoccupied at this moment.",
            ],
            "rationale": [
                "The shared dishes and close seating indicate a communal meal rather than separate orders.",
                "The pouring gesture suggests hospitality or customary drink service during dining.",
                "The empty high chair implies a child may belong to the group, though this cannot be confirmed from the image.",
            ],
            "object": [
                "A wooden dining table holds many plates and bowls of food arranged for sharing.",
                "A person pours liquid from a vessel into a cup at table level.",
                "A second person holds a piece of food raised toward the mouth.",
                "A woven basket rests against the warm-toned wall of the eatery.",
                "An empty child's high chair stands beside the table.",
            ],
        },
        "rationale_support": ["visual_support", "commonsense_inference", "insufficient_evidence"],
        "text_dependency": "none",
        "philosophy_interpretations": [
            {
                "visual_anchors": ["shared dishes", "two diners close together"],
                "symbolic_mapping": ["shared table to communal bond"],
                "concept_ids": ["social_existence", "ethics_responsibility"],
                "interpretation": "The table crowded with shared dishes images the primal scene of human community, where nourishment becomes a visible act of mutual dependence.",
                "alternative_interpretations": ["The arrangement may simply reflect the restaurant's family-style service."],
                "limitations": ["The relationships among the diners and their intentions are not visually knowable."],
                "sufficiency": "supported",
            },
            {
                "visual_anchors": ["pouring gesture", "held food"],
                "symbolic_mapping": [],
                "concept_ids": ["ethics_responsibility"],
                "interpretation": "The small courtesies of pouring and passing embody everyday ethics, responsibility practiced at the scale of a single meal.",
                "alternative_interpretations": ["Each person may merely be attending to their own drink and food."],
                "limitations": ["A frozen gesture cannot reveal whether the act was directed at the other diner."],
                "sufficiency": "plausible",
            },
            {
                "visual_anchors": ["empty high chair"],
                "symbolic_mapping": ["empty seat to absent presence"],
                "concept_ids": ["time_mortality", "faith_meaning"],
                "interpretation": "The empty high chair amid abundance quietly marks absence within presence, a reminder that gatherings are shadowed by those not at the table.",
                "alternative_interpretations": ["The chair may simply be spare furniture moved aside by staff."],
                "limitations": ["Nothing in the image establishes who the chair was placed for."],
                "sufficiency": "insufficient",
            },
        ],
    },
    "F0793": {
        "target_subject": "a woman holding an infant while photographing themselves with a phone",
        "captions": {
            "scene": [
                "An indoor room with plain surfaces and partial furniture frames a close, casual moment.",
                "A woman sits in the foreground with an infant held against her body.",
                "The viewpoint is intimate, consistent with a self-taken photograph at close range.",
            ],
            "action": [
                "The woman holds a white smartphone toward herself to capture the moment.",
                "She supports the infant with her other arm close to her chest.",
                "Both faces are turned toward the camera in a frontal pose.",
            ],
            "rationale": [
                "The phone held at this angle indicates the image is a self-portrait taken by the woman herself.",
                "The supported hold and bodily closeness are consistent with caregiving behavior.",
                "The purpose of taking the photo, keepsake or sharing, cannot be determined from the image alone.",
            ],
            "object": [
                "A woman in indoor clothing holds a white smartphone toward the camera.",
                "An infant is cradled against the woman's body with one supporting arm.",
                "The room wall behind them is plain and evenly lit.",
                "A piece of furniture is partly visible in the lower foreground.",
                "The overall lighting is soft and diffuse, without harsh shadows.",
            ],
        },
        "rationale_support": ["visual_support", "visual_support", "insufficient_evidence"],
        "text_dependency": "none",
        "philosophy_interpretations": [
            {
                "visual_anchors": ["phone held toward self", "infant in arm"],
                "symbolic_mapping": ["self-capture to constituting memory"],
                "concept_ids": ["time_mortality", "knowledge_truth"],
                "interpretation": "Photographing herself with the infant enacts the wish to arrest time, converting a fleeting stage of life into a durable image.",
                "alternative_interpretations": ["The photo may be a routine casual snapshot with no reflective intent."],
                "limitations": ["Interior motivation for taking the picture is not visually accessible."],
                "sufficiency": "plausible",
            },
            {
                "visual_anchors": ["supporting arm", "bodily closeness"],
                "symbolic_mapping": ["embrace to primal responsibility"],
                "concept_ids": ["ethics_responsibility"],
                "interpretation": "The image condenses the ethical structure of care, a vulnerable life held by another whose attention is divided between the child and the record of the moment.",
                "alternative_interpretations": ["The pose may simply be the most practical way to hold both infant and phone."],
                "limitations": ["Emotional states cannot be read reliably from posture alone."],
                "sufficiency": "plausible",
            },
            {
                "visual_anchors": ["camera-directed gaze", "intimate framing"],
                "symbolic_mapping": ["screen mediation to a mediated self-relation"],
                "concept_ids": ["identity_appearance", "other_abstract_relation"],
                "interpretation": "The mediated self-view suggests how identity is now staged through the device, presence experienced partly as its future image.",
                "alternative_interpretations": ["The frontal gaze may result only from following the phone screen."],
                "limitations": ["A single frame cannot support claims about the subject's self-understanding."],
                "sufficiency": "insufficient",
            },
        ],
    },
    "F1104": {
        "target_subject": "a large fishbone graffiti with a red eye painted on a wall",
        "captions": {
            "scene": [
                "A large stylized fish skeleton is painted across a long light-colored wall bordering a paved street.",
                "The wall fills much of the frame, with open sky above and pavement below.",
                "The street appears quiet and empty of people in daytime light.",
            ],
            "action": [
                "The painted fish skeleton lies horizontally, its eye rendered in red.",
                "The pavement surface reflects light faintly, suggesting recent rain.",
                "No human activity is visible, leaving the artwork to stand alone.",
            ],
            "rationale": [
                "The absence of passersby and the centered framing indicate the wall itself is the subject.",
                "The reflective ground and muted tones are consistent with wet conditions.",
                "The artist's intent in choosing a fish skeleton cannot be known from the image alone.",
            ],
            "object": [
                "A large fish skeleton is painted in dark outline across a light wall.",
                "The fish's single eye is rendered in red pigment.",
                "The wall runs parallel to a paved street with a smooth surface.",
                "Open sky occupies the upper band of the frame.",
                "The pavement shows a faint sheen consistent with moisture.",
            ],
        },
        "rationale_support": ["visual_support", "visual_support", "insufficient_evidence"],
        "text_dependency": "none",
        "philosophy_interpretations": [
            {
                "visual_anchors": ["fish skeleton", "red eye"],
                "symbolic_mapping": ["skeleton to remains after consumption"],
                "concept_ids": ["time_mortality", "labor_technology"],
                "interpretation": "The immense discarded skeleton evokes what remains after appetite has passed, abundance reduced to residue in a depopulated street.",
                "alternative_interpretations": ["The fishbone may be a purely decorative motif chosen for its graphic shape."],
                "limitations": ["Without the artist's statement any reading of intent remains speculative."],
                "sufficiency": "plausible",
            },
            {
                "visual_anchors": ["empty street", "mute wall"],
                "symbolic_mapping": ["empty street to public silence"],
                "concept_ids": ["social_existence", "freedom_constraint"],
                "interpretation": "The artwork addresses an absent public, speech fixed in paint while its audience is nowhere in sight, an image of expression without reception.",
                "alternative_interpretations": ["The street may be empty only at this moment of capture."],
                "limitations": ["A single frame cannot establish whether the area is usually frequented."],
                "sufficiency": "insufficient",
            },
            {
                "visual_anchors": ["red eye detail"],
                "symbolic_mapping": ["red eye to a persistent witness"],
                "concept_ids": ["knowledge_truth", "other_abstract_relation"],
                "interpretation": "The lone red eye staring from otherwise bleached remains suggests observation outlasting life, a gaze that survives its own body.",
                "alternative_interpretations": ["The red eye may serve simply as a focal accent in the composition."],
                "limitations": ["Color symbolism is inherently underdetermined by visual evidence."],
                "sufficiency": "insufficient",
            },
        ],
    },
    "F1347": {
        "target_subject": "a signboard with red Japanese characters standing among rocks on a mountain path",
        "captions": {
            "scene": [
                "A rectangular signboard with red Japanese script stands on a wooden support in a rocky landscape.",
                "Boulders and gravel form a sloping natural corridor around the sign.",
                "Sparse vegetation appears at the edges of the stony ground under daylight.",
            ],
            "action": [
                "The signboard stands tilted slightly on uneven rocky terrain.",
                "Loose stones and boulders form the path surface leading past the sign.",
                "No people are present, leaving the sign as the only human-made object.",
            ],
            "rationale": [
                "The wooden support and placement suggest the sign marks a route or boundary for travelers.",
                "The worn setting indicates an established trail through the rocks.",
                "The specific meaning of the text cannot be confirmed since it is not translated in this annotation.",
            ],
            "object": [
                "A rectangular signboard carries red Japanese characters on a pale surface.",
                "A wooden post and frame support the signboard upright.",
                "Large boulders and smaller stones dominate the surrounding ground.",
                "A narrow stony path passes beside the sign.",
                "Patches of low vegetation grow between the rocks.",
            ],
        },
        "rationale_support": ["visual_support", "commonsense_inference", "insufficient_evidence"],
        "text_dependency": "medium",
        "philosophy_interpretations": [
            {
                "visual_anchors": ["sign among rocks", "path passing beside it"],
                "symbolic_mapping": ["sign to institutional order in wild terrain"],
                "concept_ids": ["knowledge_truth", "choice_journey"],
                "interpretation": "A sign planted in wild stone marks the human need to fix meaning at crossroads, knowledge posted precisely where the path becomes uncertain.",
                "alternative_interpretations": ["The sign may convey a mundane warning or place name without deeper significance."],
                "limitations": ["The text's actual content is unreadable in this annotation, so its function remains assumed."],
                "sufficiency": "plausible",
            },
            {
                "visual_anchors": ["wooden support", "rocky slope"],
                "symbolic_mapping": ["fragile wood against stone to impermanence"],
                "concept_ids": ["time_mortality"],
                "interpretation": "The modest wooden stand set among ancient boulders contrasts human transience with geological permanence.",
                "alternative_interpretations": ["Wood may have been chosen simply for availability and cost."],
                "limitations": ["Material choices alone cannot carry a claim about mortality."],
                "sufficiency": "insufficient",
            },
            {
                "visual_anchors": ["empty trail"],
                "symbolic_mapping": ["unpeopled path to solitary passage"],
                "concept_ids": ["choice_journey", "faith_meaning"],
                "interpretation": "The vacant trail with its solitary sign evokes the quiet structure of pilgrimage, a way marked for travelers who are always elsewhere.",
                "alternative_interpretations": ["The emptiness may reflect an off-peak moment on an ordinary hiking route."],
                "limitations": ["No evidence identifies the trail as religious or ceremonial."],
                "sufficiency": "insufficient",
            },
        ],
    },
    "F1661": {
        "target_subject": "a fashion doll lying in a sink filled with dark liquid",
        "captions": {
            "scene": [
                "A doll with blonde hair lies in a white sink basin filled with dark liquid.",
                "The setting is a plain indoor room with even, shadowless lighting.",
                "The glossy plastic body contrasts sharply with the dark surrounding liquid.",
            ],
            "action": [
                "The doll's body rests partly submerged in the still liquid.",
                "Its wet hair spreads across the surface in strands.",
                "The limbs rest in fixed positions, giving the arrangement a staged stillness.",
            ],
            "rationale": [
                "The deliberate placement and wet hair indicate the arrangement was constructed rather than accidental.",
                "The contrast of materials suggests an artistic or staged photograph rather than a documentary one.",
                "The creator's intended meaning cannot be determined from the image alone.",
            ],
            "object": [
                "A fashion doll with blonde hair lies in a white sink basin.",
                "Dark liquid fills the basin around the doll's body.",
                "The doll's glossy plastic limbs are visible above the liquid surface.",
                "The white basin sits against a plain interior background.",
                "Even indoor lighting leaves the scene without strong shadows.",
            ],
        },
        "rationale_support": ["visual_support", "commonsense_inference", "insufficient_evidence"],
        "text_dependency": "none",
        "philosophy_interpretations": [
            {
                "visual_anchors": ["doll in dark liquid", "staged stillness"],
                "symbolic_mapping": ["defaced toy to corrupted innocence"],
                "concept_ids": ["identity_appearance", "time_mortality"],
                "interpretation": "The submerged doll stages the corruption of an idealized figure, childhood's polished surface swallowed by an opaque medium.",
                "alternative_interpretations": ["The image may be a cleaning photograph or material experiment with no symbolic aim."],
                "limitations": ["Without authorial context the intent behind the staging is unknowable."],
                "sufficiency": "plausible",
            },
            {
                "visual_anchors": ["white basin", "dark contents"],
                "symbolic_mapping": ["white container to a sanitized facade"],
                "concept_ids": ["knowledge_truth", "power_conflict"],
                "interpretation": "The clinical whiteness of the basin holding darkness suggests how orderly surfaces can conceal what they contain, purity as containment.",
                "alternative_interpretations": ["The color pairing may follow from ordinary bathroom fixtures."],
                "limitations": ["Color contrast alone underdetermines any claim about concealment."],
                "sufficiency": "insufficient",
            },
            {
                "visual_anchors": ["frozen limbs", "spread hair"],
                "symbolic_mapping": ["stillness to arrested life"],
                "concept_ids": ["time_mortality"],
                "interpretation": "The doll's suspended posture mimics aftermath, an object imitating mortality while remaining untouched by it.",
                "alternative_interpretations": ["The posture may simply follow from how the doll settled in the liquid."],
                "limitations": ["Reading aftermath into an arrangement of plastic projects meaning the object cannot confirm."],
                "sufficiency": "insufficient",
            },
        ],
    },
}


def main() -> None:
    worklist = {w["blind_id"]: w for w in schema.load_worklist(None)}
    for blind_id, raw in MANUAL_DRAFTS.items():
        item = worklist[blind_id]
        record = schema.validate_and_normalize(raw, item)
        record.update({
            "method": "ai_agent_direct_visual_draft_non_independent",
            "formal_gold": False,
            "review": {
                "reviewer_model": "none_yet",
                "verdict": "pending_cross_model_or_human_review",
                "issues": ["created by direct AI-agent visual drafting after qwen, glm, and deepseek pipeline retries were exhausted"],
            },
            "provenance": {
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "generator": "zcode_ai_agent_manual_visual",
                "reviewer": "none",
                "image_input": "direct_local_view_by_ai_agent",
            },
        })
        path = OUT_DIR / f"{blind_id}.json"
        schema.save_atomic(path, record)
        print(json.dumps({"event": "manual_draft_written", "item": blind_id, "method": record["method"]}))


if __name__ == "__main__":
    main()
