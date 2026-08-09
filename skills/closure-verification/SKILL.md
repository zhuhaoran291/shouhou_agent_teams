---
name: closure-verification
description: 验证执行结果（退款到账、补发物流），判断售后目标是否完成并关闭案件，供验证 Agent 使用。
metadata:
  version: "0.1.0"
  maturity: demo
---

# 收尾验证

## 用途

验证 Agent 收到执行结果后，用本技能验证退款是否到账、补发物流是否正常，判断售后目标是否完成，通过后更新并关闭案件。

## 输入

- 执行结果（executed_actions、failed_actions）。
- 验证要求（退款到账、补发签收等）。

## 步骤

1. 查询退款状态，确认退款到账或处理中。
2. 查询补发物流，确认已发货且运输正常。
3. 逐项判定验证项通过与否，附证据。
4. 全部通过则更新案件状态并关闭案件；未通过则返回原因，不关案。

## 输出契约

```json
{
  "case_id": "CS-1001",
  "verification": [{"item": "", "status": "通过/未通过", "detail": ""}],
  "closed": true,
  "closure_note": ""
}
```

## 护栏

- 验证不通过不关案。
- 不扩大动作范围；不能执行退款、补发等动作。
