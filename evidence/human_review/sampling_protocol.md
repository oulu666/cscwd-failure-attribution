# AFTraj 模型标签人工核查协议（A4）

日期：2026-11-10  
性质：对 test80 的 **盲法标签核查**，不是新的独立测试集；没有真实回复前不生成结果。

## 1. 目的

AFTraj 的 `mistake_step` 是 multi-LLM-judge 标签。本核查回答：

- 两位独立人类标注者是否能判断同一定义下的 `mistake_step`；
- 人工标签与模型标签的一致程度；
- 在人工标签下重评已冻结预测，结果是否改变。

**不能**用本核查把 test80 变成“人类独立测试”；它是对现有测试的标签敏感性分析，也不能据此调模型。

## 2. 样本

- 来源：`split/test80.csv` 的 80 条 test80（pipeline-unseen）。
- 抽样 40 条：30 agentic + 10 math；按 `n_steps` 三分位分层（agentic 10/12/8，math 4/3/3）。
- 抽样只看 domain 和长度，**不看 GD/V3 是否正确**，不按模型预测筛样本。
- 冻结 salt：`aftraj-label-audit-20261110`。
- 参与者文件：`aftraj_label_audit_participant.jsonl`（无 gold、无模型预测）。
- 组织者文件：`aftraj_label_audit_sample.csv`（含 gold，仅组织者）。

## 3. 目标定义

- **Mistake step**：最早一步，其中 mistake agent 首次做出了导致最终错误答案的错误；0-based。
- 如果信息不足或无法判断，标记 `unknown=1`，不要强行给精确步。
- 只使用参与者看到的 question/history；不使用外部答案、模型预测或原标签。

## 4. 流程

1. 两位标注者独立完成 40 条；先做 5 条试标（不计入正式一致率）。
2. 每条填：step、evidence_step、confidence 1–5、unknown 0/1、notes。
3. 组织者回收后做仲裁；原始双标与仲裁分开报告。
4. 与模型标签比较：exact、within-1、unknown rate、可判断率；报告人工-模型分歧。
5. 在人工标签子集上重评冻结的 GD/V3/maj4/gd_supported 预测；同时保留原模型标签结果。
6. 若人工标签与模型标签差异大，按标签敏感性报告，不改模型、不覆盖原预测。

## 5. 角色与工作量

- 两位独立标注者（可与 E6 不同人；若同一人，需分开记录任务和顺序）。
- 40 条 × 10–20 分钟 ≈ 7–13 小时/人；试标 5 条另计。
- 仲裁由第三人或有明确规则的组织者完成。

## 6. 交付

| 文件 | 内容 |
|---|---|
| `aftraj_label_audit_participant.jsonl` | 40 条参与者输入（无 gold/预测） |
| `aftraj_label_audit_sample.csv` | 组织者 key（含 gold） |
| `aftraj_label_audit_responses.csv` | 待真实回复；字段：case_id, annotator_id, step, evidence_step, confidence, unknown, notes |
| `aftraj_label_audit_analysis.json` | 待真实回复后生成；不预填结果 |

## 7. 诚实规则

- 不伪造标注者、不生成假回复、不把模型输出当人工标签。
- 不按 GD/V3 正确性抽样；样本在标注前冻结。
- 不因分歧删除案例；unknown 保留在分母。
- 本核查不是新独立测试，不能写成“人类外部 cohort”。
