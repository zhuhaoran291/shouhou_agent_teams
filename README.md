# 电商售后多 Agent 系统最小 Demo（Aftersales Zero）

这是一个面向初赛提交的最小可运行 demo。用户只提供投诉文本和少量案件信息，AgentTeams 中的 4 个业务 LLM Agent 通过 HTTP mock 工具网关主动查询订单、支付、物流、库存、证据、政策、退款、审批、案件和消息数据；创建 Team 时由 manager 创建独立 TeamLeader Worker `merchant-aftersales-leader` 负责调度协作，完成受理 → 调查 → 方案 → 审批 → 执行 → 验证 → 报告的售后闭环。

完整运行手册见 [at/AGENTTEAMS_RUNBOOK.md](at/AGENTTEAMS_RUNBOOK.md)。

## Demo 要证明什么

1. AgentTeams 可以创建并管理 4 个职责明确的业务 LLM Agent（受理 / 调查方案 / 执行 / 验证），并在创建 Team 时生成 1 个独立 TeamLeader Worker（售后总调度）。
2. Worker 在 Docker 中也能通过 HTTP 工具网关主动取证（订单、物流、政策、证据、审批状态），不依赖宿主机目录。
3. 两个售后案件分两次独立处理，贴近真实售后节奏。
4. 低风险动作（L0/L1）进入自动化执行语义；涉及资金动作（L2）必须先通过商家审批再执行；高风险（L3）只生成审批计划。第一版所有涉及资金的动作均划分为 L2 或 L3。

## Demo 场景

| 场景 ID | 售后类型 | 预期处置 |
| --- | --- | --- |
| `damaged_goods` | 商品破损，用户要求退款或补发 | 受理结构化案件 → 调查证据链（订单/物流/照片）→ L2 方案（退款或补发）→ 创建审批任务 → 审批通过后提交退款 → 验证退款到账 → 最终报告 |
| `missing_items` | 少件漏发，用户要求补发或退差价 | 受理结构化案件 → 调查发货记录 → L2 方案（补发少件商品）→ 创建审批任务 → 审批通过后创建补发单 → 验证补发物流 → 最终报告 |

## 核心 Agent

| Agent | 作用 | 关键 Skill | 工具域 |
| --- | --- | --- | --- |
| 售后总调度 `merchant-aftersales-leader` | 创建 Team 时由 manager 生成的独立 Worker，接收案件、调度 Worker、控制审批、汇总报告 | 由 manager 创建 | 无直接工具调用 |
| 受理 Agent `intake-investigator` | 将用户投诉翻译为结构化案件 | `intent-recognition`, `case-organization` | `aftersales`, `customer`, `order`, `evidence`, `case` |
| 调查方案 Agent `resolution-reporter` | 调查事实 → 出方案 + 出报告（不执行） | `fact-investigation`, `risk-identification`, `solution-generation`, `risk-grading`, `report-writing` | `order`, `payment`, `logistics`, `inventory`, `evidence`, `policy`, `refund`, `aftersales`, `approval`, `case` |
| 执行 Agent `executor` | 只执行已允许/已审批的动作（写操作集中地） | `action-execution` | `approval`, `refund`, `inventory`, `order`, `message` |
| 验证 Agent `verifier` | 只验证结果 + 关闭案件（无执行能力） | `closure-verification` | `refund`, `logistics`, `case` |

一句话边界：**受理只管翻译，调查只算不做，执行只做不查，验证只验不做。**

## 最短运行流程

1. 启动 mock 工具网关：

```bash
cd <DEMO_DIR>
python3 tools/mock_tool_server.py --host 0.0.0.0 --port 18089
```

2. 安装 AgentTeams，并按安装器引导完成 LLM/API Key/端口/运行时配置：

```bash
bash <(curl -sSL https://higress.ai/hiclaw/install.sh)
```

3. 找到 Docker 容器访问工具网关的地址（详见运行手册第 4 节）。

4. 在 Element Web 打开 `manager` 房间，把 [at/create_agents_messages.md](at/create_agents_messages.md) 里的 `<MOCK_TOOL_BASE_URL>` 替换成 Worker 可访问的网关地址后，将完整创建请求复制给 `manager`。创建请求已要求所有 Worker 使用 `qwenpow`（`copow`/`QwenPaw`）运行时，并由 `manager` 严格串行创建 4 个业务 Worker；创建 Team 时再生成独立 TeamLeader Worker `merchant-aftersales-leader`。

5. 在 Element Web/Matrix 会话列表中找到名称以 `Team` 开头、对应 `aftersales-zero-demo` 的 Team 房间。进入房间后，在输入框先 `@<team_leader_name>` 选中带 leader 名字的成员，再把 [at/run_demo_task_message.md](at/run_demo_task_message.md) 中的第一条案件任务复制到这条 @ 消息里发送；等报告输出完成后，再用同样方式发送第二条。案件任务不要发给 `manager`。

## 工具域速查

工具网关协议：`POST /tools/{scenario_id}/{工具域}.{函数名}`，共 12 个工具域 26 个函数，完整目录见 [tools/tool_catalog.json](tools/tool_catalog.json)。

| 工具域 | 函数 | 主要使用 Agent |
| --- | --- | --- |
| `aftersales` | `get_complaint`, `query_processing_rules` | 受理、调查方案 |
| `customer` | `get_profile` | 受理 |
| `order` | `search`, `get_detail`, `check_reship_eligible`, `create_reship` | 受理、调查方案、执行 |
| `payment` | `get_detail` | 调查方案 |
| `logistics` | `get_track`, `query_reship` | 调查方案、验证 |
| `inventory` | `query_available`, `reserve` | 调查方案、执行 |
| `evidence` | `list_submissions`, `verify` | 受理、调查方案 |
| `policy` | `query_after_sales` | 调查方案 |
| `refund` | `query_history`, `calc_max_amount`, `submit`, `query_status` | 调查方案、执行、验证 |
| `approval` | `create_task`, `query_status` | 调查方案、执行 |
| `case` | `create`, `update`, `update_status`, `close` | 受理、调查方案、验证 |
| `message` | `notify_customer` | 执行 |

## 后续替换点

| 当前内容 | 后续替换方向 |
| --- | --- |
| HTTP mock 工具网关 | 真实 MCP Server 或 Higress MCP 代理 |
| `scenarios/*.json` | 真实订单、支付、物流、库存、证据、政策、退款、审批、案件、消息数据源 |
| 4 个业务 Worker 的内联 AgentSpec/Skill | Nacos AI Registry 中的 Prompt、Skill、AgentSpec、AgentTeam Spec |
| `skills/*/SKILL.md` 评审材料 | 发布到 Nacos AI Registry 或 AgentTeams Skill Registry，由 Worker 按版本/标签动态加载 |
