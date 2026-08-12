# AfterSales Zero Demo AgentTeam

这个文件描述 demo 使用的 Team 形态。主运行路径是 **声明式「团队即代码」**：用 `at/deploy.sh` 渲染 `at/manifests/aftersales-zero.yaml` 并调用 `agt apply -f` 构建，结果可复现、可版本化。

## AgentTeams 运行时

| AgentTeams 概念 | Demo 设计 |
| --- | --- |
| 构建方式 | `MOCK_TOOL_BASE_URL=<网关地址> bash at/deploy.sh` → `agt apply -f aftersales-zero.yaml`（幂等，可重复运行） |
| Team 房间 | Matrix 会话列表中名称以 `Team` 开头；用户通过 `@merchant-aftersales-leader` 发送售后案件 |
| TeamLeader Worker | 清单中独立定义的 Worker `merchant-aftersales-leader`，角色 `team_leader` |
| Worker 房间 | 运行 4 个角色明确的业务 LLM Agent |
| Worker 运行时 | 统一使用 `qwenpow`（`copow`/`QwenPaw`） |
| 创建策略 | 清单按序声明 5 个 Worker（4 业务 + 1 leader）与 1 个 Team；`agt apply` 顺序创建；禁止把业务 Worker 指定为 leader |
| AgentSpec | 4 个业务 Worker 的 mission / skills / 工具契约 / 边界内联在清单各 Worker 的 `soul` 字段 |
| 案件输入 | `at/run_demo_task_message.md` 中的投诉文本和案件信息 |
| 工具调用 | HTTP mock 工具网关 |
| 定向改能力 | 编辑清单中对应 Worker 的 `soul` 后重新运行 `at/deploy.sh` 即可，不影响其它 Worker |
| Skill Registry | 当前运行时使用 `soul` 中的内联 Skill 语义；`skills/*/SKILL.md` 和 `at/nacos_registry_mock.json` 用于评审和后续替换 |

AgentTeams 组件经常运行在 Docker 中，因此运行时不依赖宿主机上的项目目录路径。Worker 通过 HTTP 地址访问工具网关，并根据 `scenario_id` 查询对应案件数据。当前 demo 不要求 Worker 读取宿主机上的 `skills/*/SKILL.md`；后续可把这些 Skill 发布到 Nacos AI Registry 或 AgentTeams Skill Registry，再由 Worker 按版本/标签动态加载。

## 工作流

1. TeamLeader `merchant-aftersales-leader` 接收 Team 房间中的售后案件，提取 `case_id`、`scenario_id` 和用户描述，并调度业务 Worker。
2. `Intake Investigator Agent` 将投诉翻译为结构化案件，输出诉求、商品、证据和缺失信息。
3. `Resolution Reporter Agent` 主动查询订单、支付、物流、库存、证据和政策，输出调查报告、处理方案、风险等级和审批项。
4. `Executor Agent` 执行已允许或已审批的动作，所有写操作带幂等键。
5. `Verifier Agent` 验证退款到账、补发物流，通过后更新并关闭案件。
6. `Resolution Reporter Agent` 依据验证结果补全最终售后报告。
7. `merchant-aftersales-leader` 汇总输出最终售后报告。

## Demo 场景

| 场景 | 问题 | 安全策略 |
| --- | --- | --- |
| `damaged_goods` | 双层玻璃杯杯口破损，诉求退款或补发。 | 退款/补发涉及资金，按 L2 审批。 |
| `missing_items` | 订单少件漏发，诉求补发或退差价。 | 补发/退差价涉及资金，按 L2 审批。 |
