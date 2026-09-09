# PhiloVista-1800 与正式 632 概念框架对齐说明

更新日期：2026-09-09。

## 已完成

| 框架要求 | 数据集实现 |
|---|---|
| 锁定正式概念资源 | `ontology/philosophical_image_label_system_formal_632.csv`，并以 `formal_632.lock.json` 记录行数、字段分布和 SHA-256 |
| 区分旧轴与正式概念 | manifest 预分层保留为 `benchmark_axis_id`；旧解释的 `concept_ids` 在新 sidecar 中改名为 `legacy_axis_ids` |
| 11 轴只作候选检索 | `legacy_axis_crosswalk.json` 标为 `candidate-only`；`other_abstract_relation` 不做默认映射 |
| 每概念证据关联 | 正式 Schema 增加 `concept_claims`，每条包含 PHC ID、主张、锚点索引、象征映射索引、充分性和限制 |
| 允许没有有效哲学答案 | 正式 Schema 将每图解释数量改为 0–3 |
| 本体与标注来源版本化 | 记录 `ontology_version`、本体 SHA-256、生成/复核方法组成的 `annotation_source` 与 `formal_gold` |
| 固定组级切分 | `splits/benchmark_splits.csv` 按 `group_id` 分配为 180/180/1,440，跨 split 组数为 0 |
| 不伪造人工金标 | 1,800 条框架 sidecar 均保留 `formal_gold=false`，5,400 条解释的 `concept_claims` 均为空 |

## 产物

- `annotation_workflow/drafts/api_en/exports/PhiloVista-1800_framework.jsonl`：兼容现有草稿的框架对齐 sidecar。
- `splits/benchmark_splits.csv`：固定 calibration/dev/test 分区。
- `audit/framework_alignment_20260909/framework_alignment_report.json`：结构校验、分区分布及剩余限制。
- `annotation_workflow/schemas/philosophy_record.schema.json`：未来人工独立标注与仲裁的正式结构。
- 核心概念候选包与 180 张校准图的盲映射工作表见 `docs/CORE_CONCEPT_AND_CALIBRATION_ZH.md`。

框架 sidecar 中的 `formal_concept_candidates` 是检索提示，不是标签。特别是 `Visual Inferability=not_image_decidable`、`Temporal Requirement=process/longitudinal` 的概念，必须满足正式概念表中的 `Grounding Rule` 才能进入 `concept_claims`。

## 尚不能自动完成

仍需人工逐图完成 PHC 映射、独立评分、分歧仲裁及核心概念覆盖筛选。当前 1,800 条记录是经复核 AI 草稿，不能描述为正式人类 gold；候选 crosswalk 也不能用于直接计算细概念分类指标。

## 复现

从仓库根目录运行：

```bash
python annotation_workflow/scripts/build_framework_release.py
```

若正式概念 CSV 不在项目默认位置，使用 `--ontology-csv PATH` 指定。脚本只重建派生产物，不修改 1,800 个原始逐图草稿。
