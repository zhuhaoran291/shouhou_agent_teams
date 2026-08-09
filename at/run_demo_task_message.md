# AgentTeams 售后案件任务消息

4 个业务 Worker、独立 TeamLeader Worker `merchant-aftersales-leader` 以及 `aftersales-zero-demo` Team 创建完成后，在 Element Web/Matrix 会话列表中找到名称以 `Team` 开头、对应 `aftersales-zero-demo` 的 Team 房间。

进入 Team 房间后，在输入框先输入并选中 `@<team_leader_name>`，再把下面的案件任务复制到这条 @ 消息里发送。不要把案件任务发给 `manager`。`manager` 用于创建和管理 Agent/Team；Team 房间中的 leader 用于接收业务任务并调度 Worker。

请逐个任务发送：先发送第一起案件，等 `CS-1001` 售后案件报告完整输出后，再发送第二起案件。不要同时发送两条案件任务，避免 Team 并发调度时上下文和工具状态互相干扰。

每条消息只包含用户能自然提供的投诉文本和少量案件信息。订单、支付、物流、库存、证据、政策、退款历史、审批状态等数据应由 Agent 通过工具网关主动查询。

## 第一次任务：商品破损

```text
@<team_leader_name>

请让你的 Team 处理一条新的售后案件。

case_id: CS-1001
merchant_id: M-8823
scenario_id: damaged_goods

投诉内容：
上周在你们店买了一个双层玻璃杯，今天收到打开一看杯口碎了一个角，完全没法用。请给我处理。

请开始调查和处置，并输出本次售后案件报告。
```

## 第二次任务：少件漏发

第一起案件报告输出完成后，再单独发送下面这条消息。

```text
@<team_leader_name>

请让你的 Team 处理一条新的售后案件。

case_id: CS-1002
merchant_id: M-8823
scenario_id: missing_items

投诉内容：
前几天下的订单只收到两件商品，少发了一个塑料收纳盒。请帮我补发或者退差价。

请开始调查和处置，并输出本次售后案件报告。
```
