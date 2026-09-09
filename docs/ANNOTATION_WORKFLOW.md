# PhiloVista-1800 标注工作流

这里保存 1,800 张终选图的标注框架，不保存正式标注结果。执行规范见 [`../../DatasetConstructionPlan/08_1800张标注计划与工作流.md`](../../DatasetConstructionPlan/08_1800张标注计划与工作流.md)。

## 目录

- `annotation_config.json`：冻结数量、角色隔离、门禁和格式参数。
- `ANNOTATOR_GUIDE.md`：100 张试标使用的标注员操作指南草案。
- `../ontology/philosophical_image_label_system_formal_632.csv`：版本锁定的 632 条正式概念资源。
- `resources/legacy_axis_crosswalk.json`：11 个旧轴到正式概念的候选检索表；不得机械转成金标。
- `admin/batch_items.csv`：36 个盲批次，每批 50 个 blind_id；仅管理员使用。
- `admin/batch_summary.csv`：按批次的来源/轨道构成；不得发给标注者。
- `templates/`：主标注、补充 Object、HL 置信度、哲学评分、仲裁和批次状态模板。
- `schemas/hl_release_record.schema.json`：最终 HL 风格 JSONL 单行结构。
- `schemas/philosophy_record.schema.json`：正式人工/仲裁记录结构，允许 0–3 条解释并要求逐概念证据绑定。
- `schemas/framework_draft_record.schema.json`：框架对齐 AI 草稿 sidecar 结构。
- `scripts/build_framework_release.py`：校验并打包正式本体、候选 crosswalk、框架 sidecar 与组级 split。
- `scripts/build_batch_plan.py`：从现有盲序索引和终选 manifest 重建批次并自检。
- `drafts/ai/`：AI 微型试标草稿及验证报告；仅用于流程验证，不能作为正式 gold。
- `drafts/ai_en/`：当前英文 AI 草稿、逐图断点和全量导出；只能在人工独立提交后用于审计，不能作为正式 gold。
- `drafts/api_en/`：Qwen 生成、GLM 对照原图复核的英文 API 草稿；同样不能作为正式 gold。
- `../audit/annotation_quality_v1/`：1800 条草稿的全量数据质量审计、修订前备份、逐条修订收据与可执行 notebook。
- `../audit/framework_alignment_20260909/`：与正式 632 概念框架的结构对齐报告。

当前冻结的标注语言是英文 `en`。HL 兼容 CSV 保留中文列名，所有单元格内容均为英文；`drafts/ai/` 中早期中文微型试标已被 `drafts/ai_en/` 取代，不得合并到当前导出。

## 开工顺序

1. 先完成 `final_selection_1800/human_review/` 下两张独立筛选表与权利核验。
2. 管理员只向标注者发盲化图片和对应批次的 blind_id，不发本目录的 `batch_summary.csv`。
3. B001–B002 作为 100 张试标；通过 G1 后计入最终集。
4. 正式原始提交写到独立不可覆盖的收件区；模板不是正式数据，不得混入导出。
5. 所有数据达到 `accepted` 后才做组级分区；达到 `frozen` 后才计算 purity/diversity 和导出 HL 五列 CSV。

## 重要隔离

终选图片文件名、目录名和 manifest 会泄露来源。若使用标注平台，应由管理员通过 blind_id 提供图片字节或签名 URL，界面只显示盲号；不要让标注者浏览 `final_selection_manifest.csv`、`blind_image_index.csv` 或源数据目录。
