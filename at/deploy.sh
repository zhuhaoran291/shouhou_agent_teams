#!/usr/bin/env bash
# =============================================================================
# AfterSales Zero Demo — 可复现部署脚本（团队即代码）
#
# 用法：
#   MOCK_TOOL_BASE_URL=http://172.18.0.1:18089 bash at/deploy.sh
#
# 说明：
#   - 把 at/manifests/aftersales-zero.yaml 模板中的 $MOCK_TOOL_BASE_URL / $AT_MODEL
#     渲染为实际值，再执行 `agt apply -f` 一次性创建 4 个业务 Worker、
#     1 个独立 TeamLeader Worker（merchant-aftersales-leader）和 1 个 Team。
#   - 想定向修改某个 Agent 的能力，编辑对应 Worker 的 soul 后重新运行本脚本即可。
#   - 仅依赖 bash 内建，不依赖 envsubst 等外部工具。
# =============================================================================
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPL="$DEMO_DIR/at/manifests/aftersales-zero.yaml"

# 工具网关地址：Worker 容器必须能访问到，单机 Docker 通常用 manager 网络 gateway。
if [[ -z "${MOCK_TOOL_BASE_URL:-}" ]]; then
  echo "错误：请先设置 MOCK_TOOL_BASE_URL（Worker 容器可访问的 mock 工具网关地址）。" >&2
  echo "示例： MOCK_TOOL_BASE_URL=http://172.18.0.1:18089 bash at/deploy.sh" >&2
  exit 1
fi

# 模型：优先用安装时配置的真实 LLM，否则回退到 qwen-plus。
: "${AT_MODEL:=${AGENTTEAMS_DEFAULT_MODEL:-qwen-plus}}"

TMP="$(mktemp -t aftersales-zero.XXXXXX.yaml)"
trap 'rm -f "$TMP"' EXIT

# 纯 bash 渲染模板（替换 $MOCK_TOOL_BASE_URL 与 $AT_MODEL 占位符）。
content="$(cat "$TMPL")"
content="${content//\$MOCK_TOOL_BASE_URL/$MOCK_TOOL_BASE_URL}"
content="${content//\$AT_MODEL/$AT_MODEL}"
printf '%s\n' "$content" > "$TMP"

echo ">> 渲染清单完成（model=$AT_MODEL, toolGateway=$MOCK_TOOL_BASE_URL）"
echo ">> 执行 agt apply -f 创建 Worker 与 Team ..."

# agt 在 Manager 容器内可用；若在宿主机执行需保证 agt 已配置 controller 地址。
agt apply -f "$TMP"

echo
echo ">> 创建请求已提交。接下来："
echo "   1. 在 Element Web 会话列表中找到名称以 'Team' 开头、对应 aftersales-zero-demo 的房间。"
echo "   2. 进入房间，先 @merchant-aftersales-leader，再粘贴 at/run_demo_task_message.md 中的案件任务。"
echo "   3. 一次只发一个案件，等报告输出后再发下一个。"
