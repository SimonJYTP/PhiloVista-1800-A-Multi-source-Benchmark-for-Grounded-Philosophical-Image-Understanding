# Philosophical Image Label System: formal 632

[Project overview](../README.md) · [中文说明](../README_ZH.md)

The canonical resource is [philosophical_image_label_system_formal_632.csv](philosophical_image_label_system_formal_632.csv), version **formal-632-20260909**. It contains 632 rows, 632 unique `PHC-xxx` IDs, and 16 columns. [formal_632.lock.json](formal_632.lock.json) records the byte-level SHA-256 and field distributions. Git preserves the CSV bytes across platforms.

## Representation and fields

| Field | Role |
|---|---|
| Concept ID | Stable concept identifier |
| Macro Dimension | Ontology, Epistemology, or Axiology |
| Subdomain | More specific organizational category |
| Tradition / School | Intellectual tradition or school association |
| Philosophical Concept | Conceptual layer: named philosophical concept |
| Symbolic Keywords | Concrete layer: semantic, symbolic, or relational cues |
| Visual Evidence Patterns | Concrete layer: general visual patterns that may instantiate the cues |
| Visual Inferability | Whether interpretation is symbol-mediated, context-heavy, or not image-decidable |
| Temporal Requirement | Snapshot, process, or longitudinal evidence requirement |
| Grounding Rule | Constraint on making a concept claim from the evidence |
| Maslow Relevance (Auxiliary) | Auxiliary motivation context, not a separate philosophical layer |
| SEP Relationship | Recorded relationship to the cited SEP entry |
| SEP Entry | Cited source title |
| SEP URL | Source link |
| Source Accessed | Recorded access date |
| Ontology Status | Current resource status, not dataset coverage |

Some Symbolic Keywords already express an interpretation. Treat their position on the concrete side as a representation convention, not a claim that every keyword is directly visible. Image-specific anchors must be separately recorded, and `symbolic_mapping` must explain the transition when needed.

The CSV supplies general cues, not image-level labels, bounding boxes, or a complete relation graph. SEP references provide philosophical context; they do not automatically validate the proposed visual associations. Detailed definitions, inclusion/exclusion criteria, and near-neighbor distinctions for the benchmark core still require expert annotation work.

## Resource statistics

| Field | Distribution |
|---|---|
| Macro Dimension | Ontology 158; Epistemology 132; Axiology 342 |
| Visual Inferability | symbol_mediated 404; context_heavy 196; not_image_decidable 32 |
| Temporal Requirement | snapshot 555; process 54; longitudinal 23 |
| Ontology Status | candidate 416; ontology_only 216 |

`snapshot` does not mean directly observable or conclusively inferable. Concepts requiring process, longitudinal, or external contextual evidence must remain qualified or insufficient when the image does not provide that evidence.

## Connection to PhiloVista-1800

The [legacy-axis crosswalk](../annotation_workflow/resources/legacy_axis_crosswalk.json) offers retrieval candidates for the 11 older themes. It currently references 29 distinct PHC IDs and is explicitly `candidate-only`; it does not establish that any image has those labels. `other_abstract_relation` has no default mapping.

The framework sidecar keeps formal `concept_claims` empty. Human mapping must bind each accepted PHC claim to its own actual anchors, sufficiency judgment, and limitations. Do not infer fine-grained labels from a coarse axis alone.

## Versioning and rebuild

From the repository root:

```bash
python annotation_workflow/scripts/build_framework_release.py
```

The builder uses this bundled CSV by default. An explicit `--ontology-csv PATH` imports another 632-row source and regenerates the lock and sidecar. A semantic resource change requires updating the version consistently in the builder, configuration, crosswalk, schemas, and documentation before release; regenerating a hash alone is not version management. Do not reuse a stable ID for a different concept.
