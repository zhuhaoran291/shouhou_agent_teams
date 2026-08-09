# 使用 AgentTeams 运行电商售后多 Agent 系统 Demo

这份手册面向第一次试运行 demo 的参赛者。运行机器可以是本地 Mac、Linux 服务器或云主机；mock 工具网关和 AgentTeams 都部署在同一台机器上。

核心流程：

1. 启动 HTTP mock 工具网关。
2. 安装 AgentTeams，并按安装器引导完成 LLM 配置。
3. 找到 Docker Worker 可访问的工具网关地址。
4. 在 `manager` 房间创建 4 个业务 Worker，并在创建 Team 时生成独立 TeamLeader Worker。
5. 在 Matrix 会话列表中进入名称以 `Team` 开头的 Team 房间，通过 `@<team_leader_name>` 分别发送两条售后案件。

## 1. 准备运行机器

需要：

- Docker 或兼容运行时。
- Python 3。
- 一个 AgentTeams 可使用的 LLM API Key。

检查：

```bash
python3 --version
docker --version
```

如果没有 Docker，按系统查看官方安装文档：

| 系统 | 官方安装入口 |
| --- | --- |
| Mac | https://docs.docker.com/desktop/setup/install/mac-install/ |
| Ubuntu | https://docs.docker.com/engine/install/ubuntu/ |
| Debian | https://docs.docker.com/engine/install/debian/ |
| CentOS | https://docs.docker.com/engine/install/centos/ |
| RHEL | https://docs.docker.com/engine/install/rhel/ |
| 其他 Linux | https://docs.docker.com/engine/install/ |
| Linux 免 sudo 后置配置 | https://docs.docker.com/engine/install/linux-postinstall/ |

安装完成后验证：

```bash
docker run hello-world
```

## 2. 启动 Mock 工具网关

在一个终端中启动服务，并保持它运行：

```bash
cd <DEMO_DIR>
python3 tools/mock_tool_server.py --host 0.0.0.0 --port 18089
```

另开一个终端验证：

```bash
curl http://127.0.0.1:18089/health
curl http://127.0.0.1:18089/scenarios
curl -X POST http://127.0.0.1:18089/tools/damaged_goods/order.get_detail \
  -H 'Content-Type: application/json' \
  -d '{"order_id": "SO-20260801-001"}'
```

这一步只验证宿主机本机访问。后面还需要验证 Docker 容器访问。

## 3. 安装 AgentTeams

执行安装脚本：

```bash
bash <(curl -sSL https://higress.ai/hiclaw/install.sh)
```

安装器会引导完成语言、安装模式、版本、LLM、API Key、API 联通性测试、Embedding、Manager/Worker 运行时、端口、域名、E2EE、Docker API 安全代理和共享目录等配置。按引导操作即可，关键是看到模型 API 联通性测试通过。

可参考的 demo 样例：

| 引导项 | 样例值 |
| --- | --- |
| 语言 | 中文 |
| 版本 | 最新稳定版，例如 `v1.1.2` |
| LLM | 使用已有 API Key 的模型服务，例如 `qwen3.7-plus` |
| API 联通性 | 必须测试通过 |
| Embedding | 可启用；失败后接受自动禁用也可以 |
| Manager/Worker 运行时 | `qwenpow`（`copow`/`QwenPaw`） |
| Element Web 端口 | 默认 `18088` |
| Matrix E2EE | 建议禁用 |
| Docker API 安全代理 | 建议启用 |
| 共享主机目录 | 可保持默认；本 demo 不依赖共享目录读取文件 |

安装完成后检查：

```bash
docker ps | grep hiclaw
```

打开 Element Web：

```text
http://<AGENTTEAMS_HOST>:18088
```

在运行机器本机访问时通常是：

```text
http://127.0.0.1:18088
```

安装配置通常保存到当前用户 HOME 下的 `hiclaw-manager.env`，后续需要调整模型或端口时从这里排查。

## 4. 确定工具网关地址

Worker 在 Docker 容器中运行，不能直接使用 `http://127.0.0.1:18089` 访问宿主机上的 mock 工具网关。单机 Docker 部署优先使用 `hiclaw-manager` 所在网络的 gateway 地址。

先找到 manager 容器名：

```bash
docker ps --format '{{.Names}}' | grep manager
```

如果容器名是 `hiclaw-manager`，查看 gateway：

```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{println .Gateway}}{{end}}' hiclaw-manager
```

假设输出是 `172.18.0.1`，则 `<MOCK_TOOL_BASE_URL>` 使用：

```text
http://172.18.0.1:18089
```

从容器内验证：

```bash
docker exec -it hiclaw-manager curl http://172.18.0.1:18089/health
```

如果这条命令返回 `{"ok": true, ...}`，说明后续 Worker 可以访问工具网关。

`host.docker.internal` 只在部分 Docker Desktop 环境可用。如果容器里报 `Could not resolve host: host.docker.internal`，就使用上面的 gateway 地址。

## 5. 创建 Agent 和 Team

进入 Element Web 的 `manager` 房间。

打开 [create_agents_messages.md](create_agents_messages.md)，先把文件中的 `<MOCK_TOOL_BASE_URL>` 全部替换为第 4 步确认的地址，例如：

```text
http://172.18.0.1:18089
```

然后将 [create_agents_messages.md](create_agents_messages.md) 中“复制到 Manager 的完整创建请求”整段发送给 `manager`。这段请求已经包含 4 个业务 Worker 和 1 个 Team 的完整定义，并明确要求：

1. 所有 Worker 使用 `qwenpow`（`copow`/`QwenPaw`）运行时。
2. `manager` 必须逐个创建 Worker，不能并行创建。
3. 必须确认前一个 Worker 创建成功且正常运行后，再创建下一个 Worker。
4. 创建 Team 时必须生成新的独立 Worker `merchant-aftersales-leader` 作为 TeamLeader，不能把 4 个业务 Worker 中的任何一个直接指定为 leader。

Worker 初始化会拉起运行时并写入依赖，低规格机器上并发创建可能造成高 I/O 消耗甚至阻塞。因此不要手动把 Worker 创建任务拆开并并行发送。

注意：

- `manager` 只负责创建和管理。
- 售后案件后续发给 Matrix 会话列表中名称以 `Team` 开头的 Team 房间，并在消息里 `@<team_leader_name>`，不发给 `manager`。
- 4 个业务 Worker 的 AgentSpec、Skill 和工具契约已经内联在创建消息中。
- Worker 不需要读取宿主机上的 `agents/...` 或 `skills/*/SKILL.md` 文件。
- `skills/*/SKILL.md` 主要用于评审、PPT/文档追溯和后续 Registry 替换。

## 6. 发送售后案件

打开 [run_demo_task_message.md](run_demo_task_message.md)。

在 Element Web/Matrix 会话列表中找到名称以 `Team` 开头、对应 `aftersales-zero-demo` 的 Team 房间。通常 `manager` 在创建完成摘要里会告诉你 Team 房间名称和 `team_leader_name`。

进入 Team 房间后，在输入框先输入并选中 leader mention：

```text
@<team_leader_name>
```

然后把第一条案件任务复制到这条 @ 消息里发送。必须逐个任务发送：等 `CS-1001` 报告完整输出后，再用同样方式 `@<team_leader_name>` 并发送第二条案件消息。不要同时发送两起案件，避免 Team 并发调度时上下文和工具状态互相干扰。

如果你只看到 `manager` 房间，可以先问：

```text
aftersales-zero-demo 对应的 Team 房间在哪里？请告诉我 Matrix 会话列表中名称以 Team 开头的房间名称，以及需要 @ 的 team_leader_name。
```

案件消息只包含投诉文本和少量案件信息（case_id、merchant_id、scenario_id）。订单、支付、物流、库存、证据、政策、退款历史、审批状态等数据应由 Agent 通过 HTTP 工具网关主动查询。

## 7. 判断是否跑通

`CS-1001 / damaged_goods`（商品破损）应包含：

| 检查项 | 期望信号 |
| --- | --- |
| 诉求识别 | intent 为退款或补发，绑定订单和商品（双层玻璃杯） |
| 案件结构 | 标准案件含 order_id、products、issue、evidence_refs、missing_info |
| 调查证据链 | 订单已签收、支付实付金额、物流签收记录、破损照片证据核实 |
| 方案与风险 | L2 退款（实付金额）或补发，附政策依据（破损包赔/质保） |
| 审批 | 审批任务已通过 `approval.create_task` 创建 |
| 执行 | 审批通过后通过 `refund.submit` 提交退款，写操作带幂等键 |
| 验证 | 退款到账状态验证通过（`refund.query_status`） |
| 报告 | 完整售后报告：诉求/证据链/方案/审批项/执行结果/验证结果/关闭结论 |

`CS-1002 / missing_items`（少件漏发）应包含：

| 检查项 | 期望信号 |
| --- | --- |
| 诉求识别 | intent 为补发或退差价 |
| 调查证据链 | 订单商品数量与实发数量不一致，定位少件商品 |
| 方案与风险 | L2 补发少件商品（或退差价），附政策依据 |
| 审批 | 审批任务已通过 `approval.create_task` 创建 |
| 执行 | 审批通过后通过 `order.create_reship` 创建补发单 |
| 验证 | 补发物流正常（`logistics.query_reship`） |
| 报告 | 完整售后报告（同上） |

如果团队要求你人工提供完整订单、物流、证据或政策数据，可以提醒：

```text
请通过已配置的 HTTP mock 工具网关主动查询，不要让我人工收集完整证据。
```

## 后续替换点

| 当前内容 | 后续替换方向 |
| --- | --- |
| HTTP mock 工具网关 | 真实 MCP Server 或 Higress MCP 代理 |
| `scenarios/*.json` | 真实订单、支付、物流、库存、证据、政策、退款、审批、案件、消息数据源 |
| `at/create_agents_messages.md` 中 4 个业务 Worker 的内联 AgentSpec/Skill | Nacos AI Registry 中的 Prompt、Skill、AgentSpec、AgentTeam Spec |
| `skills/*/SKILL.md` 评审材料 | 发布到 Nacos AI Registry 或 AgentTeams Skill Registry，由 Worker 按版本/标签动态加载 |
