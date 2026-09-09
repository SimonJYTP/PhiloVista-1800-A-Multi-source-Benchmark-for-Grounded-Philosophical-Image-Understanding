# 核心概念候选包与校准工作表使用说明

生成日期：2026-09-09。对应框架文档第 9 节第 1–3 步中可以程序化完成的部分；产物全部是供人工复核的工作底稿，不构成正式 gold，也不表示任何概念已进入最终核心评测集。

## 分层规则

核心概念候选包只覆盖当前 crosswalk 可检索到的 29 个正式概念（10 个已映射轴；`other_abstract_relation` 不做默认映射）。分层依据是正式概念表自身的约束字段，规则完全公开：

| 层级 | 规则 | 数量 |
|---|---|---:|
| A_core_recommended | symbol_mediated 且 snapshot 且 ontology_status=candidate | 14 |
| B_context_dependent | candidate 状态但需要 context_heavy 或 process 证据 | 10 |
| C_excluded_from_core_v1 | not_image_decidable 或 longitudinal 或 ontology_only | 5 |

排除原因逐条记录在 `exclusion_reason` 列：`visual_inferability_not_image_decidable`（1）、`temporal_longitudinal_unsupported`（1）、`ontology_status_ontology_only`（3）。

`reachable_image_count` 表示该概念经所属轴在 1,800 张图中可被检索到的图片数。由于 crosswalk 按轴整组给候选，该数值反映轴流行度，不是概念级证据强度，不能用于宣称覆盖。

## 产物

- `annotation_workflow/resources/core_concept_candidates_v1.csv`：29 个可检索概念的分层底稿，含 Symbolic Keywords、Visual Evidence Patterns、Grounding Rule 全文。
- `annotation_workflow/resources/core_concept_neighbor_pairs_v1.csv`：24 个非排除概念的近邻区分对（共 164 行）。每个概念有 5–7 个近邻，来自三路信号，按优先级排序：
  1. `same_axis_retrieval`：同一 legacy 轴的共检索竞争者。检索该轴时这些概念必然同时出现，是最先需要写区分规则的配对（例如 PHC-417 Negative Liberty 与 PHC-418 Positive Liberty）。
  2. `same_subdomain`：同 CSV Subdomain 内词元重叠最高的概念。
  3. `lexical_overlap`：全表词元级词汇重叠近邻。
- `annotation_workflow/calibration/v1/calibration_mapping_worksheet_v1.csv`：180 张校准图的盲映射工作表，只含 blind_id、image_path 和待填列。
- `annotation_workflow/calibration/v1/calibration_image_key_v1.csv`：分析用密钥表，含 sample_id、group_id、track、benchmark_axis_id 与 AI 候选概念。
- `audit/core_concept_pack_20260909/core_concept_pack_report.json`：规则定义、计数与结构校验结果。

## 人工流程要求

1. 独立映射阶段不得向标注者出示 key 文件或 sidecar 中的 AI 候选；工作表刻意不含任何 AI 建议，防止锚定。
2. `human_phc_claims` 使用格式：`PHC-317:supported; PHC-136:plausible`；无法支持任何哲学主张时填写 `none:insufficient_evidence`。充分性等级沿用 supported / plausible / insufficient 三档，判定须对照该概念在正式表中的 Grounding Rule。
3. 至少两名标注者独立完成后，先按图片为单位计算映射一致性并保留分歧，再进入仲裁；仲裁通过的概念-图片配对才可写入 `concept_claims`。
4. 近邻区分规则写入 `core_concept_neighbor_pairs_v1.csv` 的 `human_discrimination_rule` 列，并署名 `reviewer_id`。优先完成全部 `same_axis_retrieval` 对。
5. A 层概念是核心评测集的第一候选；B 层概念需先在校准中证明能获得足够区分度与样本；C 层概念在 v1 中不进入核心集，理由已逐条记录。

## 明确边界

- 分层与近邻对均由规则和词面信号生成，未经人工确认，不得写成"已确定的核心概念集"。
- AI 候选概念（key 文件、sidecar）只是检索提示，不得机械转换为 PHC 标签或用于计算细概念分类指标。
- 本包不修改 1,800 个原始草稿；一切人工结论回写时须保持 `formal_gold` 与 `annotation_source` 如实标注。

## 复现

从仓库根目录运行：

```bash
python annotation_workflow/scripts/build_core_concept_pack.py
```

脚本会校验本体 CSV 的 SHA-256 与 `ontology/formal_632.lock.json` 一致后才生成产物；正式 CSV 若有变更须先更新 lock 文件。
