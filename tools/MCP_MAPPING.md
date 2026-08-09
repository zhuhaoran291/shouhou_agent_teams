# MCP Mapping Notes

初赛 demo 使用 HTTP mock 工具网关，让 AgentTeams 中的 Docker Worker 可以通过网络访问 mock 订单、支付、物流、库存、证据、政策、退款、审批、案件和消息工具。

当前工具网关不是 MCP Server，但每个 HTTP 工具都有明确的未来 MCP 映射。后续只需要把 HTTP endpoint 替换为真实 MCP Server 或 Higress MCP 代理，Agent 的 Prompt/Skill/工具契约可以保持稳定。

## HTTP 调用协议

```text
POST http://<MOCK_TOOL_BASE_URL>/tools/{scenario_id}/{tool_domain}.{function_name}
Content-Type: application/json
```

示例：

```bash
curl -X POST http://127.0.0.1:18089/tools/damaged_goods/order.get_detail \
  -H 'Content-Type: application/json' \
  -d '{"order_id": "SO-20260801-001"}'
```

## 工具映射

| HTTP mock tool | Demo function | Future MCP tool |
| --- | --- | --- |
| `aftersales` | `get_complaint`, `query_processing_rules` | `aftersales.complaint_and_rules` |
| `customer` | `get_profile` | `customer.profile` |
| `order` | `search`, `get_detail`, `check_reship_eligible`, `create_reship` | `order.query_and_fulfillment` |
| `payment` | `get_detail` | `payment.query` |
| `logistics` | `get_track`, `query_reship` | `logistics.track` |
| `inventory` | `query_available`, `reserve` | `inventory.available_and_reserve` |
| `evidence` | `list_submissions`, `verify` | `evidence.list_and_verify` |
| `policy` | `query_after_sales` | `policy.after_sales_query` |
| `refund` | `query_history`, `calc_max_amount`, `submit`, `query_status` | `refund.query_and_submit` |
| `approval` | `create_task`, `query_status` | `approval.create_and_query` |
| `case` | `create`, `update`, `update_status`, `close` | `case.create_and_update` |
| `message` | `notify_customer` | `message.notify` |
