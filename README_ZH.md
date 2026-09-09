# PhiloVista-1800

**面向有据哲学图像理解的多源评测基准**

[English](README.md) · [技术说明](docs/TECHNICAL_REPORT_ZH.md) · [评测框架](docs/BENCHMARK_FRAMEWORK.md) · [正式标签体系](ontology/README.md)

研究问题：多模态模型能否从图像中的具体证据出发，提出合理、可追溯的哲学解释，并判断哪些结论超出了图像能够支持的范围？

本项目由 **632 条正式概念资源、PhiloVista-1800 数据集、标注规范、评测任务与实验协议**共同组成。PhiloVista-1800 是其中的数据集，标签体系提供概念与证据约束，benchmark 规定如何公平评测模型。

> **当前版本：2026-09-09 框架对齐研究预览版。** 1,800 条标注全部是经复核的 AI 草稿，保持 `formal_gold=false`。已提供正式概念表、框架导出、Schema 和组级数据切分。独立人工 PHC 映射、金标准、一致性评分及模型基线结果仍待完成。仓库已包含 `images/` 图片目录；逐图权利状态继续保留在 manifest 中。

## 1. 正式标签体系

按照“概念层—具象层”组织：

| 层次/作用 | CSV 字段 | 含义 |
|---|---|---|
| 概念层 | `Philosophical Concept`、`Concept ID` | 需要识别和区分的哲学概念 |
| 具象层：关键词线索 | `Symbolic Keywords` | 与概念相关的语义、象征或关系线索 |
| 具象层：视觉证据模式 | `Visual Evidence Patterns` | 可能实现这些线索的对象、动作、构图和关系模式 |
| 分类组织 | `Macro Dimension`、`Subdomain`、`Tradition / School` | 宏观维度、子领域及学派背景 |
| 证据约束 | `Visual Inferability`、`Temporal Requirement`、`Grounding Rule` | 视觉可推断性、时间要求和证据规则 |

632 个唯一 PHC ID 分布为本体论 158、认识论 132、价值论 342。资源状态为 `candidate` 416、`ontology_only` 216；并不表示 632 个概念都已经具有可评分的图片金标。

关键词中有些内容已经包含抽象解释，例如“公平分配”。因此必须区分“图中可见锚点”和“由锚点引出的解释”。实际链条是：图像锚点 → 视觉模式与关键词 → 候选概念 → 充分性判断。`symbolic_mapping` 保留映射过程，无需另建独立象征层标签。

标签表中的通用模式不能替代逐图证据。即使图中出现天平，也不能自动认定它表达某种特定正义理论。字段与版本详见 [ontology 说明](ontology/README.md)。

## 2. 数据集

| 来源 | 正向轨 | 边界轨 | 总数 |
|---|---:|---:|---:|
| HL Dataset | 500 | 100 | 600 |
| HAIVMet | 550 | 0 | 550 |
| IRFL | 420 | 80 | 500 |
| MM-MoralBench | 150 | 0 | 150 |
| 合计 | 1,620 | 180 | 1,800 |

正向轨测试合理哲学解释，边界轨测试证据不足时的解释克制。边界图也应得到准确的普通视觉描述；正向图上的某个候选解释仍可能证据不足。边界样本仅来自 HL 和 IRFL，需要报告这两个来源内部的对照表现。

每图具有 Scene、Action、Rationale 各 3 条参考，Object 5 条参考，以及 3 个哲学解释候选。当前是 AI 多参考文本，不能称为三名独立人工的共识。未来人工/仲裁结构允许每图接受 0–3 条解释。

## 3. 评测任务

| 任务 | 评测问题 | 建议指标 |
|---|---|---|
| T1 视觉证据识别 | 模型实际看到了什么？ | 锚点准确性、关系正确性、虚构事实 |
| T2 哲学概念识别/检索 | 哪些正式概念与图像相符？ | 人工确认核心概念集上的多标签 F1、Recall@k |
| T3 有据哲学解释 | 为什么可以作出该解释？ | 视觉支持、概念契合、连贯性、过度解读风险 |
| T4 充分性与解释克制 | 该主张能推到多远？ | 充分性 Macro-F1、边界过度解读率、正向有效解释覆盖率 |

这些是待正式冻结的评测规则；当前未发布模型评分器、基线分数或图谱增强收益。主评测输入为图像与统一任务提示，T4 额外提供各模型相同的待判断主张。来源、轨道、上游答案与从参考标注派生的候选概念不得混入测试输入。

## 4. 正式概念与旧标注的衔接

旧逐图 JSON 和 `PhiloVista-1800_philosophy.jsonl` 的 `concept_ids` 仍表示 11 个粗粒度主题。新版 [框架导出](annotation_workflow/drafts/api_en/exports/PhiloVista-1800_framework.jsonl) 将其明确写为：

- `legacy_axis_ids`：保留旧主题轴；
- `formal_concept_candidates`：由候选 crosswalk 给出的 PHC 检索建议；
- `concept_claims`：正式逐概念主张，人工逐图确认前保持 `[]`；
- `ontology_version`、`ontology_sha256`：锁定标签资源版本；
- `annotation_source`、`formal_gold`：保留 AI 草稿来源与状态。

候选 crosswalk 当前涉及 29 个不同 PHC ID，这不是已确认的概念覆盖数。候选不能机械转成金标，也不能直接用于细概念分类评分。

为推进人工衔接，仓库另提供[核心概念候选包](annotation_workflow/resources/core_concept_candidates_v1.csv)：29 个可检索概念按正式表约束字段分层——A 层推荐核心 14（symbol_mediated + snapshot + candidate）、B 层依赖语境 10、v1 排除 5（not_image_decidable / longitudinal / ontology_only，逐条记录原因）。配套的[近邻区分工作表](annotation_workflow/resources/core_concept_neighbor_pairs_v1.csv)为每个非排除概念列出同轴共检索、同子域与词汇重叠三类近邻；[校准盲映射工作表](annotation_workflow/calibration/v1/calibration_mapping_worksheet_v1.csv)覆盖 180 张校准图，不含任何 AI 建议。使用规则见[核心概念与校准说明](docs/CORE_CONCEPT_AND_CALIBRATION_ZH.md)。

## 5. 获取与复现

在仓库根目录运行，使用 Python 3.10 或以上：

```bash
python annotation_workflow/scripts/export_english_api_drafts.py
python annotation_workflow/scripts/build_framework_release.py
python annotation_workflow/scripts/build_core_concept_pack.py
python -m pip install -r requirements.txt
python annotation_workflow/scripts/audit_annotation_dataset.py
```

框架构建默认读取仓库内 `ontology/philosophical_image_label_system_formal_632.csv`，无需作者本机外部目录。`--ontology-csv PATH` 可显式指定替换来源；发布修改后的概念资源时应同步版本管理。

图片通过 `images/<file_name>` 获取。清单中的历史路径保留原始选图布局，来源和权利状态以逐图记录为依据。仓库提供图片不等于已经完成全部权利核验，也不自动授予上游数据的额外使用权限。

文件索引、读取示例与引用格式见 [English README](README.md)。

## 6. 已验证与待完成

当前导出为 1,800/1,800 条，零导出错误；自动审计为零 critical/high、17 条 medium 复核提醒。此结果是结构与数据一致性检查，不替代哲学语义的人工验证。

[组级切分](splits/benchmark_splits.csv) 已实现 calibration 180 / dev 180 / test 1,440，`group_id` 跨集合数为零。它不是隐藏测试服务，现有 AI 参考公开可见；同组不跨集合也不等于穷尽所有潜在近重复。

下一阶段需要完成独立人工 PHC 映射、仲裁前一致性统计、专家仲裁、核心概念筛选、评分规则校准与模型基线。提示策略、概念检索、证据约束和未来知识图谱可作为逐项比较的方法。

## 文档导航

- [技术说明与现有统计](docs/TECHNICAL_REPORT_ZH.md)
- [Benchmark 框架与实验协议](docs/BENCHMARK_FRAMEWORK.md)
- [正式 632 概念字段说明](ontology/README.md)
- [框架对齐说明](docs/FRAMEWORK_ALIGNMENT_ZH.md)
- [核心概念包与校准工作表说明](docs/CORE_CONCEPT_AND_CALIBRATION_ZH.md)
- [标注员指南](docs/ANNOTATOR_GUIDE.md)
- [人工工作流](docs/ANNOTATION_WORKFLOW.md)
- [人工执行计划](docs/ANNOTATION_PLAN_ZH.md)
- [框架校验报告](audit/framework_alignment_20260909/framework_alignment_report.json)
- [数据质量报告](audit/annotation_quality_v1/PhiloVista-1800_quality_report.json)
