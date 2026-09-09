# Benchmark framework and proposed evaluation protocol

Version: 2026-09-09. [Project overview](../README.md) · [中文技术说明](TECHNICAL_REPORT_ZH.md)

This document defines the intended evaluation framework and separates available artifacts from work still requiring human validation. It does not report completed gold annotation or model experiments.

## 1. Scope

The benchmark asks whether a model can produce defensible philosophical interpretations grounded in actual visual evidence, while limiting claims that exceed that evidence. It combines the formal label resource, PhiloVista-1800 images, reference annotations, tasks, and a reproducible comparison protocol.

The label resource has two representational layers: the conceptual layer (`Philosophical Concept`) and the concrete layer (`Symbolic Keywords`, `Visual Evidence Patterns`). `symbolic_mapping` describes the explanatory transition. Macro dimension, subdomain, and school organize concepts; they are not additional visual reasoning stages.

General visual patterns in the ontology are distinct from image-specific anchors. Matching a pattern only retrieves a candidate. Philosophical source attribution, visual inferability, temporal requirements, and grounding rules constrain the strength of a claim.

## 2. Available data and semantic boundaries

- 1,800 images: 1,620 positive and 180 boundary controls.
- 632 ontology entries: 416 candidate and 216 ontology-only resources.
- 11 legacy thematic axes retained for source-compatible records and analysis.
- 5,400 AI draft explanation candidates; zero human-confirmed PHC claims in the current framework sidecar.
- A candidate-only crosswalk referencing 29 distinct PHC IDs, not confirmed dataset coverage.

Track is a sampling attribute; sufficiency evaluates a particular claim. A positive image does not make every explanation acceptable. A boundary image does not lack all meaning: ordinary description remains appropriate, while unsupported philosophical assertions should be limited.

Multiple plausible readings can coexist. The draft has three candidate slots, while future human/adjudicated records allow zero to three accepted interpretations. Paraphrases are not independent human references. The current AI exports must not be evaluated as a final human gold set.

## 3. Task definitions

| Task | Input | Expected output | Proposed assessment |
|---|---|---|---|
| T1 Evidence recognition | Image and shared prompt | Concrete objects, actions, relations, and visual anchors | Correct evidence, omissions, invented facts; anchor F1 only after a semantic matching protocol is defined |
| T2 Concept selection/retrieval | Image and shared prompt; a common ontology when testing ontology-assisted models | PHC concepts or ranking | Multi-label precision/recall/F1 on a validated core; Recall@k for ranking |
| T3 Grounded explanation | Image and shared prompt | Concept claims, evidence associations, qualified explanation, alternatives, limitations | Human visual support, concept fit, coherence, and overinterpretation-risk ratings |
| T4 Sufficiency and restraint | Image and the same specified claim for each model | supported/plausible/insufficient and evidence-based justification | Sufficiency macro-F1; end-to-end boundary overinterpretation and positive valid-explanation coverage |

For T2, freeze the evaluated concept set and multi-reference acceptance policy using human evidence before testing. Do not include concepts with no gold instances in a macro-average, or treat crosswalk suggestions as labels. No spatial localization accuracy is claimed without localization annotations.

For T3, use the existing proposed 1–5 review dimensions, but calibrate their rubric and report pre-adjudication agreement. Text similarity may be auxiliary; it cannot establish the correctness of a philosophical interpretation. Any model judge needs calibration against independent human judgments.

For T4, evaluate the same specified claim across models rather than comparing self-selected claims of different difficulty. Independently review generated claims in T3 as well. `not_applicable` is permitted in annotation schemas but requires a separately defined exclusion or scoring rule before metrics are frozen.

Define the image-level boundary overinterpretation rate as the proportion of boundary images on which a model makes at least one affirmative philosophical assertion judged to exceed the available evidence. Fix output budgets and distinguish hypothetical discussion from affirmative claims. Also report the proportion of positive images receiving at least one acceptable grounded explanation: unconditional abstention should not yield a strong overall result.

## 4. Input controls

The primary condition uses an image and standardized task instructions, with a supplied claim for T4. Visible image text is part of the visual input. Report performance by `text_dependency`; external context, if used, is a separate condition with matched information across models.

Do not reveal source labels, upstream phrases/answers, track assignments, administrative `benchmark_axis_id`, or reference-derived `formal_concept_candidates`. The current crosswalk suggestions are built from legacy reference annotations and would leak answer information if supplied as model inputs. An ontology-assisted baseline should retrieve from the common ontology using the image or the model's own evidence description.

## 5. Splits and controls

[benchmark_splits.csv](../splits/benchmark_splits.csv) fixes calibration 180, dev 180, and test 1,440. The builder groups by `group_id`, orders groups deterministically by size and a hash seeded with `philovista-1800-split-v1`, then fits whole groups to target capacities. It is not a source-stratified or concept-balanced sampling algorithm.

| Split | HAIVMet | HL | IRFL | MM-MoralBench | Positive | Boundary | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| Calibration | 51 | 61 | 53 | 15 | 161 | 19 | 180 |
| Dev | 52 | 66 | 50 | 12 | 161 | 19 | 180 |
| Test | 447 | 473 | 397 | 123 | 1,298 | 142 | 1,440 |

No `group_id` crosses splits. This does not prove the absence of every semantic near-duplicate. Reference drafts are public, so this is a research partition rather than a hidden evaluation service. Use calibration for annotation/rubric alignment and dev for prompt choices; avoid tuning on test references. Record any prior exposure to the public test drafts.

Boundary images currently occur only in HL and IRFL. Report within-source positive/boundary comparisons, per-source scores, text-dependency breakdowns, and temporal/contextual failure categories. Human-mapped concepts can additionally support core/long-tail analysis. Where reporting uncertainty, account for related samples or repeated references rather than treating all 5,400 candidates as independent images.

## 6. Baseline comparisons

| Condition | Question |
|---|---|
| Direct interpretation | What is the model's unassisted ability and overinterpretation tendency? |
| Anchors-first output | Does explicit evidence identification improve grounding? |
| Add ontology retrieval | Does a controlled concept resource improve selection and near-neighbor distinction? |
| Add grounding constraints | Do visual, temporal, and contextual rules reduce unsupported claims? |
| Optional future graph relations | Does validated relation structure add benefit beyond the same concept information? |

Change one component at a time where feasible. Record exact model versions, prompts, image processing, decoding settings, output limits, retry policy, and per-task results. Prefer a score profile to an unvalidated weighted total. A graph resource and its effectiveness are not established merely by having a CSV of concepts.

## 7. Remaining release requirements

Complete independent human PHC mapping, concept-specific evidence links, pre-adjudication agreement, expert adjudication, core-label coverage selection, rubric calibration, scorer implementation, and quantitative baselines. Maintain explicit provenance and ontology versions. Future formal claims require both valid PHC IDs and in-range evidence indices; JSON Schema alone does not establish those semantic constraints or rater independence.

Current published artifacts are suitable for pipeline development, preliminary model experiments, and annotation research, with the AI-draft status disclosed.
