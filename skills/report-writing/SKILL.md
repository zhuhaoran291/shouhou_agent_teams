---
name: report-writing
description: 汇总调查、方案、执行和验证结果，输出最终售后报告，供调查方案 Agent 使用。
metadata:
  version: "0.1.0"
  maturity: demo
---

# 报告撰写

## 用途

调查方案 Agent 在验证 Agent 完成验证后，用本技能依据实际结果补全最终售后报告：影响面、证据、方案、审批项、执行与验证结果。

## 输入

- 事实调查结果和证据链。
- 处理方案、风险等级和审批项。
- 执行结果（来自执行 Agent）。
- 验证结果（来自验证 Agent）。

## 步骤

1. 汇总调查事实和证据链。
2. 汇总方案、风险等级和审批项。
3. 汇总执行结果（已执行/失败动作）。
4. 汇总验证结果（退款到账、补发物流、案件关闭）。
5. 输出完整售后报告。

## 输出契约

```json
{
  "case_id": "CS-1001",
  "summary": "",
  "facts": [],
  "solution": {},
  "risk_level": "L0/L1/L2/L3",
  "approval_items": [],
  "execution_result": [],
  "verification_result": [],
  "closure": ""
}
```

## 护栏

- 报告必须基于实际执行和验证结果，不得虚构。
- 验证未完成时不输出最终结论。
