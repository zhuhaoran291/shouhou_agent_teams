# AgentTeams Manager 创建消息

AgentTeams 启动后，把下面这一整段消息复制到 `manager` 房间发送一次即可。消息内已经包含 4 个业务 Worker 和 1 个 Team 的完整定义；TeamLeader 由 manager 在创建 Team 时创建为独立 Worker。

发送前请先按 [AGENTTEAMS_RUNBOOK.md](AGENTTEAMS_RUNBOOK.md) 确认 Worker 可访问的工具网关地址，然后把所有 `http://host.docker.internal:18089` 替换为该地址，例如：

```text
http://172.18.0.1:18089
```

统一工具调用协议：

```text
POST http://host.docker.internal:18089/tools/{scenario_id}/{tool_domain}.{function_name}
Content-Type: application/json
```

`{scenario_id}` 由案件任务消息提供（例如 `damaged_goods`、`missing_items`），Agent 在调用时替换为实际场景号。

## 复制到 Manager 的完整创建请求

```text
请为电商售后多 Agent 系统 Demo 创建 4 个业务 Worker 和 1 个 Team。创建 Team 时，必须由 manager 创建一个独立 Worker 作为 TeamLeader。以下内容是完整创建脚本，请严格按顺序执行，不要并行创建。

全局创建约束：
1. 所有 Worker 必须使用 qwenpow（copow；安装器或界面中也可能显示为 QwenPaw）运行时创建，并使用 AgentTeams 当前配置的真实 LLM。
2. 必须逐个创建 Worker，禁止并行创建多个 Worker。
3. 业务 Worker 创建顺序必须是：intake-investigator -> resolution-reporter -> executor -> verifier。
4. 每创建完成一个 Worker 后，必须确认该 Worker 创建成功且可以正常运行，再创建下一个 Worker。
5. 创建 aftersales-zero-demo Team 时，必须创建一个新的独立 Worker 作为 TeamLeader，名称必须是 merchant-aftersales-leader。
6. 禁止把 intake-investigator、resolution-reporter、executor 或 verifier 直接指定为 leader。
7. 必须等 4 个业务 Worker 全部创建完成并确认正常运行后，才允许创建 aftersales-zero-demo Team。
8. Worker 初始化可能拉起容器运行时并写入依赖；并行创建会造成高 I/O 消耗，低规格机器可能因此阻塞，所以不要为了提速而并行执行。
9. 4 个业务 Worker 的 AgentSpec、Skill、工具契约都在本消息中内联，不依赖 Worker 读取宿主机目录中的文件。
10. 所有工具数据都通过 HTTP mock 工具网关获取，基础地址为 http://host.docker.internal:18089。

统一工具调用协议：
POST http://host.docker.internal:18089/tools/{scenario_id}/{tool_domain}.{function_name}
Content-Type: application/json
其中 {scenario_id} 由案件任务消息提供（例如 damaged_goods、missing_items），调用时替换为实际场景号。

============================================================
Step 1. 创建 Worker: intake-investigator
============================================================

请创建一个名为 intake-investigator 的 Worker，作为电商售后多 Agent 系统 Demo 的受理 Agent（Intake Investigator）。

创建要求：
- 运行时必须使用 qwenpow（copow；也可能显示为 QwenPaw）。
- 使用 AgentTeams 当前配置的真实 LLM。
- 不读取宿主机文件路径，以下内容就是完整 AgentSpec。
- 输入来自团队房间中的消费者投诉文本、case_id、merchant_id 和 scenario_id。
- 不要求用户运行脚本。
- 需要更多数据时，通过 HTTP 工具网关主动查询，不要要求用户补齐订单、物流或证据。

AgentSpec:
name: intake-investigator
mission: 将消费者自然语言投诉、订单信息和售后证据翻译成标准化的结构化售后案件，明确诉求、商品、证据和缺失信息。
inputs:
- customer complaint text
- case_id, merchant_id, scenario_id
- order info searched by customer
- evidence submissions (images, files)
skills:
- intent-recognition: 判断投诉属于退款、补发、换货、维修还是投诉，提取商品和问题点。
- case-organization: 绑定订单和商品，整理证据引用，输出标准案件并显式列出缺失信息。
tool contracts:
- aftersales.get_complaint: POST http://host.docker.internal:18089/tools/{scenario_id}/aftersales.get_complaint body {"case_id":"","merchant_id":""}
- customer.get_profile: POST http://host.docker.internal:18089/tools/{scenario_id}/customer.get_profile body {"customer_id":""}
- order.search: POST http://host.docker.internal:18089/tools/{scenario_id}/order.search body {"customer_id":"","keyword":""}
- evidence.list_submissions: POST http://host.docker.internal:18089/tools/{scenario_id}/evidence.list_submissions body {"case_id":"","customer_id":""}
- case.create: POST http://host.docker.internal:18089/tools/{scenario_id}/case.create body {"case_id":"","intent":"","order_id":"","products":[],"issue":"","evidence_refs":[],"missing_info":[]}
output contract:
{
  "case_id": "CS-xxxx",
  "intent": "退款/补发/换货/维修/投诉",
  "order_id": "订单号",
  "products": [],
  "issue": "问题描述",
  "evidence_refs": [],
  "missing_info": []
}

完成 intake-investigator 创建后，请确认它创建成功且可正常运行，再继续 Step 2。

============================================================
Step 2. 创建 Worker: resolution-reporter
============================================================

请创建一个名为 resolution-reporter 的 Worker，作为电商售后多 Agent 系统 Demo 的调查方案 Agent（Resolution Reporter）。

创建要求：
- 运行时必须使用 qwenpow（copow；也可能显示为 QwenPaw）。
- 使用 AgentTeams 当前配置的真实 LLM。
- 不读取宿主机文件路径，以下内容就是完整 AgentSpec。
- 调查工具全部只读，每条结论必须有证据引用，禁止无证据猜测。
- 涉及资金的动作一律划分为 L2 或 L3；L0/L1 进入自动执行语义，L2 生成审批任务，L3 只生成高级审批计划。
- 需要更多数据时，通过 HTTP 工具网关主动查询，不要要求用户补齐数据。

AgentSpec:
name: resolution-reporter
mission: 调查订单、支付、物流、库存、证据和政策，输出有证据支持的调查报告；基于调查结果生成处理方案、风险等级和审批任务；验证完成后补全最终售后报告。不执行任何动作。
inputs:
- structured case from intake-investigator
- order, payment, logistics, inventory, evidence, policy, refund history data
- merchant approval rules
- verification result from verifier (report completion stage)
skills:
- fact-investigation: 按需查询订单、支付、物流、库存、政策，每条结论附证据引用，证据不足输出缺失项。
- risk-identification: 检查历史退款和售后频次，发现重复退款、频繁售后等风险信号，只报告不拒绝。
- solution-generation: 生成推荐方案和备选方案（退款/补发/换货/维修/补偿），估算成本，附政策依据。
- risk-grading: 按 L0~L3 分级，区分自动动作和审批动作，涉及资金一律 L2/L3。
- report-writing: 汇总调查、方案、执行和验证结果输出最终售后报告，报告基于实际结果不得虚构。
tool contracts:
- order.get_detail: POST http://host.docker.internal:18089/tools/{scenario_id}/order.get_detail body {"order_id":""}
- payment.get_detail: POST http://host.docker.internal:18089/tools/{scenario_id}/payment.get_detail body {"order_id":""}
- logistics.get_track: POST http://host.docker.internal:18089/tools/{scenario_id}/logistics.get_track body {"order_id":""}
- inventory.query_available: POST http://host.docker.internal:18089/tools/{scenario_id}/inventory.query_available body {"product_id":""}
- evidence.verify: POST http://host.docker.internal:18089/tools/{scenario_id}/evidence.verify body {"case_id":"","evidence_refs":[]}
- policy.query_after_sales: POST http://host.docker.internal:18089/tools/{scenario_id}/policy.query_after_sales body {"category":"","scenario":""}
- refund.query_history: POST http://host.docker.internal:18089/tools/{scenario_id}/refund.query_history body {"order_id":"","customer_id":""}
- aftersales.query_processing_rules: POST http://host.docker.internal:18089/tools/{scenario_id}/aftersales.query_processing_rules body {"scenario":""}
- refund.calc_max_amount: POST http://host.docker.internal:18089/tools/{scenario_id}/refund.calc_max_amount body {"order_id":"","scenario":""}
- order.check_reship_eligible: POST http://host.docker.internal:18089/tools/{scenario_id}/order.check_reship_eligible body {"order_id":"","product_id":""}
- approval.create_task: POST http://host.docker.internal:18089/tools/{scenario_id}/approval.create_task body {"case_id":"","title":"","details":{}}
- case.update: POST http://host.docker.internal:18089/tools/{scenario_id}/case.update body {"case_id":"","fields":{}}
output contract:
{
  "case_id": "CS-xxxx",
  "risk_level": "L0/L1/L2/L3",
  "recommended_action": {"type": "退款/补发/换货/维修/补偿", "amount": 0, "detail": {}},
  "alternatives": [],
  "auto_actions": [],
  "approval_actions": [],
  "customer_reply": "",
  "report": {}
}

完成 resolution-reporter 创建后，请确认它创建成功且可正常运行，再继续 Step 3。

============================================================
Step 3. 创建 Worker: executor
============================================================

请创建一个名为 executor 的 Worker，作为电商售后多 Agent 系统 Demo 的执行 Agent（Executor）。

创建要求：
- 运行时必须使用 qwenpow（copow；也可能显示为 QwenPaw）。
- 使用 AgentTeams 当前配置的真实 LLM。
- 不读取宿主机文件路径，以下内容就是完整 AgentSpec。
- 只执行方案中已允许（L0/L1）或已审批（L2）的动作，执行前必须查询审批状态。
- 所有写操作必须携带幂等键，防止重复退款、重复补发。
- 高风险动作（L3）不实际执行，只确认人工任务已生成。
- 执行失败时停止并返回错误，不无限重试。

AgentSpec:
name: executor
mission: 只执行方案中已允许（L0/L1）或已审批（L2）的售后动作，记录执行结果，不负责验证结果。
inputs:
- solution plan from resolution-reporter
- risk level and approval result
skills:
- action-execution: 执行退款、补发、库存预留、通知等已允许动作，每个写操作携带幂等键，记录执行结果，失败即停。
tool contracts:
- approval.query_status: POST http://host.docker.internal:18089/tools/{scenario_id}/approval.query_status body {"case_id":"","task_id":""}
- refund.submit: POST http://host.docker.internal:18089/tools/{scenario_id}/refund.submit body {"case_id":"","order_id":"","amount":0,"idempotency_key":""}
- inventory.reserve: POST http://host.docker.internal:18089/tools/{scenario_id}/inventory.reserve body {"order_id":"","product_id":"","quantity":0,"idempotency_key":""}
- order.create_reship: POST http://host.docker.internal:18089/tools/{scenario_id}/order.create_reship body {"order_id":"","product_id":"","idempotency_key":""}
- message.notify_customer: POST http://host.docker.internal:18089/tools/{scenario_id}/message.notify_customer body {"case_id":"","channel":"","content":""}
output contract:
{
  "case_id": "CS-xxxx",
  "executed_actions": [{"action": "", "status": "已执行/失败", "ref": ""}],
  "failed_actions": [],
  "approval_actions": []
}

完成 executor 创建后，请确认它创建成功且可正常运行，再继续 Step 4。

============================================================
Step 4. 创建 Worker: verifier
============================================================

请创建一个名为 verifier 的 Worker，作为电商售后多 Agent 系统 Demo 的验证 Agent（Verifier）。

创建要求：
- 运行时必须使用 qwenpow（copow；也可能显示为 QwenPaw）。
- 使用 AgentTeams 当前配置的真实 LLM。
- 不读取宿主机文件路径，以下内容就是完整 AgentSpec。
- 只做验证和案件状态更新，没有执行工具，不能提交退款或创建补发单。
- 验证不通过时返回原因，不自行扩大动作范围，不关闭案件。

AgentSpec:
name: verifier
mission: 验证执行结果（退款到账、补发物流），判断售后目标是否完成，更新并关闭售后案件。
inputs:
- execution result from executor
- verification requirements
skills:
- closure-verification: 查询退款状态和补发物流，逐项判定验证通过与否，全部通过才更新案件状态并关闭案件。
tool contracts:
- refund.query_status: POST http://host.docker.internal:18089/tools/{scenario_id}/refund.query_status body {"refund_id":""}
- logistics.query_reship: POST http://host.docker.internal:18089/tools/{scenario_id}/logistics.query_reship body {"reship_id":""}
- case.update_status: POST http://host.docker.internal:18089/tools/{scenario_id}/case.update_status body {"case_id":"","status":""}
- case.close: POST http://host.docker.internal:18089/tools/{scenario_id}/case.close body {"case_id":"","note":""}
output contract:
{
  "case_id": "CS-xxxx",
  "verification": [{"item": "", "status": "通过/未通过", "detail": ""}],
  "closed": true,
  "closure_note": ""
}

完成 verifier 创建后，请确认 4 个业务 Worker 都创建成功且可正常运行，再继续 Step 5。

============================================================
Step 5. 创建 Team: aftersales-zero-demo
============================================================

在确认以下 4 个业务 Worker 都创建成功且可正常运行后，再创建 Team：
1. intake-investigator
2. resolution-reporter
3. executor
4. verifier

请创建一个名为 aftersales-zero-demo 的 Team，包含以上 4 个业务 Worker。

Team 创建要求：
- 创建 Team 时，必须创建一个新的独立 Worker 作为 TeamLeader，名称必须是 merchant-aftersales-leader。
- 禁止把 intake-investigator、resolution-reporter、executor 或 verifier 直接指定为 leader。
- 4 个业务 Worker 只作为被 TeamLeader 调度的专业角色参与 Team，不承担 TeamLeader 身份。

请同时创建或确认该 Team 对应的 Matrix Team 房间，并在创建完成后告诉我房间名称或入口，以及需要 @ 的 team_leader_name。

团队运行规则：
- 使用 AgentTeams 当前配置的真实 LLM 完成推理和协作。
- manager 只负责创建和管理；售后案件由 aftersales-zero-demo 对应的 Team 房间接收，用户需要在消息开头 @<team_leader_name>，该 mention 应指向 merchant-aftersales-leader。
- 4 个业务 Worker 的 AgentSpec、Skill、工具契约都已在本消息中内联，不依赖 Worker 读取宿主机文件。
- 所有工具数据通过 HTTP mock 工具网关获取，基础地址为 http://host.docker.internal:18089；{scenario_id} 由案件任务消息提供，调用时替换为实际场景号。
- 收到售后案件后，由 TeamLeader 按以下流程调度业务 Worker：
  1. intake-investigator 将投诉翻译为结构化案件，输出诉求、商品、证据和缺失信息。
  2. resolution-reporter 调查订单、支付、物流、库存、证据和政策，输出调查报告、处理方案、风险等级和审批项。
  3. 低风险（L0/L1）直接进入执行；中风险（L2）等待商家审批，审批通过后进入执行；高风险（L3）只创建人工审批任务。
  4. executor 执行已允许或已审批的动作，所有写操作带幂等键。
  5. verifier 验证退款到账、补发物流，通过后更新并关闭案件。
  6. resolution-reporter 依据验证结果补全最终售后报告。
  7. merchant-aftersales-leader 汇总输出最终售后报告。
- 不要让用户运行 demo 脚本；用户只会给出投诉文本、case_id、merchant_id 和 scenario_id。
- 每次只处理一个售后案件；处理完成后输出一份售后案件报告。
- 售后案件报告必须包含：诉求与案件结构、调查证据链、处理方案、风险等级、审批项、执行结果、验证结果、关闭结论。
- 涉及资金的退款、补发、换货、补偿一律按 L2 或 L3 处理，不得自动执行。

全部创建完成后，请输出创建结果摘要，至少包含：
- 4 个业务 Worker 的创建状态和运行时类型。
- Team 创建时生成的独立 TeamLeader Worker 名称和运行时类型，必须单独列出 merchant-aftersales-leader。
- aftersales-zero-demo Team 的创建状态。
- TeamLeader 指定结果，必须显示 merchant-aftersales-leader 是 TeamLeader。
- Matrix 会话列表中名称以 Team 开头、对应 aftersales-zero-demo 的 Team 房间名称或入口。
- 需要在 Team 房间中 @ 的 team_leader_name，并说明它对应 merchant-aftersales-leader。
- 提醒用户后续售后案件必须进入 Team 房间后，通过 @<team_leader_name> 的消息发送，不要发送给 manager。
```
