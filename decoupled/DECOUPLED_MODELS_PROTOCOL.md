# 去耦合对照：模型家族 × 视图（test80）

日期：2026-11-23  
性质：**稳健性/解耦分析**。test80 已被使用；本实验不是新的未接触测试。  
目的：把“全轨迹单视图 vs 多视图”的结论与模型家族拆开，检查是否由 Qwen LQ 的弱表现造成。

## 1. 设计

现有 2×2 缺一个格子：

| 模型 | step-by-step | whole-trace |
|---|---|---|
| Qwen-plus | LQ（已有，30/80） | GQ（已有，42/80） |
| DeepSeek-chat | **LD（本实验）** | GD（已有，51/80） |

LD 规格：
- 模型 deepseek-chat；
- 与 Qwen LQ 相同的 `step_prompt`；
- 每步一次，首个 Yes 停止；exact 与 full scan 相同；
- 所有步都无 Yes 时 proposal 为空，按错误计入 80 条分母；
- 无 gold；输入 `test80_inputs.jsonl`；输出 `test80_ld_predictions.jsonl` + ledger。
- 实际结果：33/80 条为空；有 proposal 的 47 条中 18 条 exact（38.3%）。

## 2. 对照

| 方法 | 组成 | 作用 |
|---|---|---|
| QwenLQ | Qwen step | 模型内 step |
| LD | DeepSeek step | 模型内 step |
| GQ | Qwen whole | 模型内 whole |
| GD | DeepSeek whole | 模型内 whole |
| V2 | vote(GQ,GD) | 两个 whole-trace 视图，无 step |
| W3 | vote(GQ,GD,late) | 三个 whole-trace 视图，无 step |
| V3 | vote(QwenLQ,GQ,GD) | 原多视图 |
| DS2 | vote(LD,GD) | DeepSeek-only 两视图 |
| DS3 | vote(LD,GQ,GD) | 用 DeepSeek step 替换 Qwen step |
| DS4 | vote(LD,GQ,GD,late) | 四视图（LD 版） |

## 3. 指标

- exact、coverage（五视图）、相对 GD/V3 的 fixed/broken/net、McNemar exact。
- 分 domain（agentic/math）。
- 成本：LD 为实际早停请求/tokens/latency；V2/W3/V3/DS 按已记录视图成本相加。
- 不调 prompt/阈值/规则；不因结果改 test80。

## 4. 解释规则

- 若 QwenLQ < GQ 且 LD < GD：step < whole 在两种模型家族内都成立。
- 若 GQ < GD：whole-trace 单视图也受模型家族影响。
- 若 V2/W3/DS2/DS3/DS4 均不高于 GD：多视图不优于最佳 whole-trace 单视图的结论不是 Qwen LQ 造成的。
- 若某个多视图高于 GD：说明多视图结论依赖组合/模型，需要改写“多视图普遍无益”的表述。
- test80 已使用；结果只作稳健性，不作新独立测试或显著性主张之外的泛化。

## 5. 产物

| 文件 | 内容 |
|---|---|
| `test80_ld_predictions.jsonl` | LD 逐条 step |
| `test80_ld_cost_ledger.jsonl` | 逐请求 requests/tokens/latency |
| `decoupled_models.json` | 方法、配对、分域、成本 |
| `decoupled_models.md` | 可读表 |
| `../src/run_aftraj_ld.py` | LD 运行器 |
| `../audit/audit_decoupled_models.py` | 复算 |
