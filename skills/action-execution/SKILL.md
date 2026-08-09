---
name: action-execution
description: 执行方案中已允许（L0/L1）或已审批（L2）的售后动作并记录结果，供执行 Agent 使用。
metadata:
  version: "0.1.0"
  maturity: demo
---

# 动作执行

## 用途

执行 Agent 收到调查方案 Agent 的处理方案后，用本技能执行已允许或已审批的动作：提交退款、预留库存、创建补发单、通知消费者，并记录执行结果。

## 输入

- 处理方案（recommended_action、auto_actions、approval_actions）。
- 风险等级和审批结果。

## 步骤

1. 执行前查询审批状态，确认 L2 动作已审批通过、L0/L1 动作在自动执行范围内。
2. 按方案逐项执行动作，每个写操作携带幂等键。
3. 记录每个动作的执行结果（已执行/失败，附单据引用）。
4. 执行失败时停止并返回错误，不无限重试。
5. L3 动作不实际执行，只确认人工审批任务已生成。

## 输出契约

```json
{
  "case_id": "CS-1001",
  "executed_actions": [{"action": "", "status": "已执行/失败", "ref": ""}],
  "failed_actions": [],
  "approval_actions": []
}
```

## 护栏

- 只执行方案中明确允许的动作。
- 执行前必须验证审批。
- 写操作带幂等键，防止重复退款、重复补发。
- 执行失败即停，不重试、不绕过工作流。
