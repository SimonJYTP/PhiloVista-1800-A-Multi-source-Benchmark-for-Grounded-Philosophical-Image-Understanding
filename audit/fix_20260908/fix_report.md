# PhiloVista-1800 审查问题修正报告（2026-09-08）

依据 `audit/independent_image_audit_20260908/confirmed_findings.csv` 所列的已确认问题，
对标注、清单与 QA 状态执行修正。所有被修改文件均有修正前备份。

## 修正总览

| 审查发现 | 修正动作 | 数量 | 结果 |
|---|---|---|---|
| captions 语义错误（confirmed） | 视觉复核后改正文，verdict → `revised_by_audit_visual_inspection` | 5 项 | 完成 |
| （修正过程中新发现）caption 内嵌工作流元评述 | 清理为纯图片描述 | 1 项 | 完成 |
| HAIV manifest `DALL┬╖E` 乱码路径 | 回填 ZIP 真实成员名（`DALL·E`，U+00B7） | 20 行 | 完成，1200/1200 直接命中 |
| 213 项陈旧 `review.verdict=revise` | 判定后同步状态并附 `resolution` 证据 | 201 项同步 / 9 项保留 | 完成 |
| 导出与 manifest 一致性 | CSV/JSONL/validation_report 同步 + 全量重审 | 1800 项 | 0 失败 |

修正后 review verdict 分布（1800 项合计）：

| verdict | 修正前 | 修正后 | 含义 |
|---|---|---|---|
| accept | 1581 | 1578 | 双 API 复核通过（3 项转视觉修正） |
| revised_by_audit_visual_inspection | 6 | 12 | 视觉审计后修正正文（6 项原有 + 本次 6 项） |
| revised_after_review | 0 | 201 | 复核 issue 所指错误已在当前正文解决（新状态） |
| revise | 213 | 9 | 仍需人工/视觉复核（真实未解决项） |

## 一、captions 正文修正（6 项，均经图片视觉复核）

| sample_id | 字段 | 修正前 → 修正后（要点） |
|---|---|---|
| PHL1800_HL_0458 (F0481) | object[0] | `inline engine` → `exposed radial engine with cylinders arranged in a star pattern`（视觉复核确认星形排列气缸） |
| PHL1800_HL_0278 (F1717) | rationale[0] | `OCP … suggesting active-duty status` → `ABU digital tiger-stripe … service status cannot be determined`（视觉复核确认 ABU 数字虎纹、无可辨徽标） |
| PHL1800_HL_0278 (F1717) | object[0] | `OCP uniform` → `ABU digital tiger-stripe uniform` |
| PHL1800_HL_0278 (F1717) | 哲学 P1 anchor | `uniforms with name tapes` → `uniforms without legible name tapes` |
| PHL1800_HL_0368 (F0753) | rationale[1] | `functional and actively engaged` → `being inspected or demonstrated; whether it is currently running cannot be determined from the static image`（视觉复核确认无运转证据） |
| PHL1800_HL_0006 (F1063) | action[2] | `moving shadows … gentle breeze or leaf movement` → `static pattern of dappled light and shadow … cannot be determined from a single still image` |
| PHL1800_HAIV_0222 (F1241) | object[4] | `text … reads 'DELL' and 'OPTIPLEX'` → `garbled, illegible pseudo-text … does not form readable brand names`（视觉复核确认生成式伪文字） |
| PHL1800_HL_0531 (F1765) | object[3] | 删除内嵌元评述 `the candidate's claim … is incorrect`，改为纯描述 |

前 5 项即审查确认问题；HL_0531 为本次复核 213 项时新发现（修正流程把评述文字写进了图片描述）。

## 二、213 项陈旧 revise 状态的同步

reviewer（glm-4.6v）的 issue 均针对初版 candidate 文本；生成流程其后已将修正并入正文，
但 verdict/issue 未同步。本次按三级证据逐项判定 issue 所指错误是否仍存在于当前正文：

1. `issue_referenced_error_absent_from_captions`（79 项）：issue 引用的错误原句已从正文消失；
2. `issue_count_values_absent_from_captions`（65 项）：issue 指认的错误计数值已从正文消失
   （正文中已无该数字或已改用 reviewer 给出的正确值/去计数表述）；
3. `manual_sentence_review`（57 项）：逐句人工比对正文与 issue 判定
   （含引号混合项——issue 引号中既有错误表述也有"正确答案引用"，需区分）。

同步方式：`verdict` → `revised_after_review`，原 issues 保留，并新增
`review.resolution`（status/method/checked_by/checked_at_utc/caption_sha256）。
`caption_sha256` 为当前 captions 规范化 JSON 的 SHA-256，可用于将来检测状态是否再次陈旧。

### 仍保留 `revise` 的 9 项（无法在本次修正中证实已解决）

| sample_id | 保留原因 |
|---|---|
| PHL1800_IRFL_0441 | 正文仍保留 issue 指为 speculative 的断言（period-style clothing 等） |
| PHL1800_IRFL_0248 | issue 指为不可见的对象（signature/beams/stance）仍被正文断言 |
| PHL1800_HL_0404 / HL_0385 / HL_0394 / HL_0366 | issue 为概括性描述，无具体引用可比对 |
| PHL1800_HL_0309 | 正文各 jersey 计数合计 6 人，与 reviewer（5 人）及本次独立视觉计数（5 人）矛盾 |
| PHL1800_HL_0105 | "at least three" 后列举 4 个个体，与 issue 的 actual=3 分歧未解 |
| PHL1800_HL_0161 | issue 指其人数/位置误述，正文仍保留相同计数的表述 |

这 9 项需要新一次人工或视觉复核后再改状态；不宜机械置为已解决。

## 三、manifest 20 条 DALL·E 路径回填

`final_selection_1800/final_selection_manifest.csv` 中 HAIVMet 20 行的 `original_member`
把 `DALL·E`（U+00B7）误编码为 `DALL┬╖E`（U+252C U+2556，Windows 解包乱码）。
以独立审计按 (size, CRC32) 唯一定位出的 ZIP 真实成员名回填，写前逐行校验回填值与
真实成员名一致（反斜杠↔正斜杠归一后完全相等），写后复验 1800 行完整、仅 20 行变化。

验证（postfix 审计）：归档成员命中方式 `manifest_member_name` 1200/1200
（修正前为 1180 直接命中 + 20 fallback），无 size/CRC/SHA-256 不匹配。

## 四、导出同步与全量回归验证

同步范围：`exports/PhiloVista-1800_HL.csv`（captions）、`PhiloVista-1800_HL.jsonl`（captions）、
`PhiloVista-1800_philosophy.jsonl`（review/interpretations）、`PhiloVista-1800_validation_report.json`
（review_verdicts、method_distribution，并记录 post_audit_fix 与保留 revise 清单）。

全量重审（`audit/postfix_verification_20260908/`，不覆盖原审计快照）：

- 12 项一致性不变量全部 1800 pass / 0 fail（含 csv_item_json_exact、caption_shape_ok、
  sha256_matches_manifest、archive/HL 来源链）；
- structural_failures = 0；duplicate_sha256_groups = 0；无孤儿/缺失图片；
- HL 上游标注链 600/600 精确一致。

## 五、备份与产物

- `backup_items_pre_fix/`：修正前 207 个 item JSON
- `backup_exports_pre_fix/`：修正前 3 个导出文件
- `backup_final_selection_manifest.csv`：修正前 manifest
- `fix_log.json`：机器可读修正日志（8 处正文修正前后全文、201 项 verdict 更新及判定方法）
- `fix_plan.py`：可复跑的判定/生成逻辑（dry-run 输出计划）
- `plan.json`：dry-run 计划快照（含 207 项修正后全文）

## 六、局限

- `revised_after_review` 表示"reviewer 指出的错误已不在当前正文"，是文本级证据结论，
  不等于新正文通过了新的视觉复核；数据集整体仍是 `formal_gold=false` 的 research preview。
- 9 项保留 revise 与 confirmed_findings 中已修正的 5 项之外，审计报告中的
  语义风险启发式（OCR/计数/低重合等）仍建议随人工终审流程消化。
