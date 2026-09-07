# PhiloVista-1800

**A Multi-source Benchmark for Grounded Philosophical Image Understanding**

PhiloVista-1800 is a research benchmark containing English multi-reference annotations for 1,800 images selected from four source datasets. It is designed to evaluate whether a vision-language system can distinguish visually grounded philosophical or abstract interpretations from unsupported overinterpretation.

> **Release status: research preview.** The annotations in this repository are reviewed AI drafts, not independent human gold annotations. Image binaries are not distributed in this repository while per-image redistribution rights are being reviewed.

## Dataset overview

| Property | Value |
|---|---:|
| Images / annotation records | 1,800 |
| Positive-track records | 1,620 |
| Insufficient-evidence boundary controls | 180 |
| Scene references per image | 3 |
| Action references per image | 3 |
| Rationale references per image | 3 |
| Object references per image | 5 |
| Philosophical interpretations per image | 3 |
| Annotation language | English |

### Source composition

| Source | Records |
|---|---:|
| HL Dataset | 600 |
| HAIVMet | 550 |
| IRFL | 500 |
| MM-MoralBench | 150 |
| **Total** | **1,800** |

The positive track contains images with visible evidence that may support philosophical, moral, abstract, or figurative reasoning. The boundary track contains valid images for which strong philosophical claims are intentionally unsupported, providing controls for measuring overinterpretation.

## Annotation structure

Each file under `annotation_workflow/drafts/api_en/items/` contains one record with:

- stable annotation and sample identifiers;
- English Scene, Action, Rationale, and Object references;
- evidence-support labels and text-dependency level;
- three philosophical interpretations with visual anchors, symbolic mappings, concept identifiers, alternatives, limitations, and sufficiency judgments;
- model/review provenance and explicit non-gold status.

The main HL-compatible JSONL record has the following form:

```json
{
  "file_name": "PHL1800_HAIV_0475.png",
  "captions": {
    "scene": ["...", "...", "..."],
    "action": ["...", "...", "..."],
    "rationale": ["...", "...", "..."],
    "object": ["...", "...", "...", "...", "..."]
  }
}
```

The CSV export follows the five-column HL layout. Its headers retain the original HL-compatible names, while all annotation text is English.

## Repository layout

```text
.
├── annotation_workflow/
│   ├── annotation_config.json
│   ├── admin/batch_items.csv
│   ├── drafts/api_en/
│   │   ├── items/                         # 1,800 reviewed item JSON files
│   │   └── exports/
│   │       ├── PhiloVista-1800_HL.csv
│   │       ├── PhiloVista-1800_HL.jsonl
│   │       ├── PhiloVista-1800_philosophy.jsonl
│   │       └── PhiloVista-1800_validation_report.json
│   ├── schemas/
│   └── scripts/
├── audit/annotation_quality_v1/
├── docs/
└── final_selection_1800/
    ├── final_selection_manifest.csv
    └── human_review/blind_image_index.csv
```

## Quick start

Read the HL JSONL export:

```python
import json
from pathlib import Path

path = Path("annotation_workflow/drafts/api_en/exports/PhiloVista-1800_HL.jsonl")
records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

print(len(records))                  # 1800
print(records[0]["file_name"])
print(records[0]["captions"]["scene"])
```

Read the HL-compatible CSV:

```python
import pandas as pd

df = pd.read_csv(
    "annotation_workflow/drafts/api_en/exports/PhiloVista-1800_HL.csv",
    encoding="utf-8-sig",
)
print(df.shape)  # (1800, 5)
```

Rebuild the exports from the item JSON files:

```bash
python annotation_workflow/scripts/export_english_api_drafts.py
```

The full image-integrity audit additionally requires reconstructing the image tree referenced by `final_selection_1800/final_selection_manifest.csv`.

## Quality and audit status

The current automated audit reports:

- 1,800 parsed records and 1,800 unique annotation IDs;
- zero critical and zero high-severity findings;
- zero CJK text in English annotation fields;
- zero forbidden separator or sensitive-data findings;
- exact CSV/JSONL round-trip consistency;
- 33 uniquely repaired records with retained revision receipts;
- 17 medium-severity human-review reminders: 16 repeated but accurate no-readable-text statements and one mirrored-action lexical-overlap case.

See `audit/annotation_quality_v1/PhiloVista-1800_quality_report.json` and `PhiloVista-1800_annotation_audit.ipynb` for details.

## Annotation provenance and limitations

The draft annotations were generated through a vision-API workflow using Qwen as the primary generator and GLM as the primary visual reviewer, with recorded DeepSeek fallbacks for a small number of requests. Six records were directly reannotated after visual audit. The exact method used for every item is retained in its provenance fields.

All records intentionally retain:

```json
"formal_gold": false,
"needs_independent_human_annotation": true,
"needs_independent_human_rating": true
```

Consequently, this preview is suitable for annotation-method research, pipeline development, error analysis, and preliminary model experiments. It should not yet be described as a finalized human-gold benchmark.

## Images, rights, and upstream data

This repository does **not** redistribute the 1,800 image files. The manifest records source membership, hashes, dimensions, and provenance references so that authorized researchers can reconstruct and verify the image set from the respective upstream datasets.

Each upstream dataset remains subject to its own license and terms. In particular, IRFL images require per-image rights review before redistribution. Repository availability does not grant rights to upstream image content or metadata.

No license for the PhiloVista-1800 annotation release has been declared yet. Until one is added, do not assume permission beyond viewing and evaluating the repository content under applicable law and the upstream terms.

## Documentation

- `docs/ANNOTATOR_GUIDE.md`: annotation instructions and evidence boundaries.
- `docs/ANNOTATION_WORKFLOW.md`: workflow structure and quality gates.
- `docs/ANNOTATION_PLAN_ZH.md`: Chinese annotation plan for the 1,800-image collection.
- `annotation_workflow/schemas/`: machine-readable release schemas.

## Citation

If you use this research preview, cite the repository:

```bibtex
@misc{philovista1800_2026,
  title        = {PhiloVista-1800: A Multi-source Benchmark for Grounded Philosophical Image Understanding},
  author       = {SimonJYTP},
  year         = {2026},
  howpublished = {GitHub repository},
  url          = {https://github.com/SimonJYTP/PhiloVista-1800-A-Multi-source-Benchmark-for-Grounded-Philosophical-Image-Understanding}
}
```

## 中文说明

PhiloVista-1800 是一个包含 1,800 张图片对应英文多参考标注的哲学视觉理解研究数据集。本仓库当前发布标注、数据清单、Schema、审计结果和复现脚本，不直接分发原始图片。当前标注属于经过复核的 AI 草稿，尚需独立人工标注、评分及版权核验后才能作为正式人类金标准发布。

Questions and corrections can be submitted through GitHub Issues.
