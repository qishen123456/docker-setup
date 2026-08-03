#!/usr/bin/env bash
# ===========================================================================
# sync-from-expert-pack.sh
# 将 WorkBuddy 专家包 fullstack-dev-team 的变更同步到项目级 .ai-team/ 资产
# ===========================================================================
set -euo pipefail

EXPERT_PACK="${EXPERT_PACK:-$HOME/.workbuddy/plugins/marketplaces/my-experts/plugins/fullstack-dev-team}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$PROJECT_DIR/.ai-team"

if [ ! -d "$EXPERT_PACK/agents" ]; then
  echo "✗ 专家包未找到: $EXPERT_PACK"
  echo "  设置 EXPERT_PACK 环境变量或检查专家包是否已安装"
  exit 1
fi

echo "源头: $EXPERT_PACK"
echo "目标: $TARGET"
echo ""

# 1. 同步 agent prompt（去 WorkBuddy frontmatter）
echo "→ 同步角色 prompt..."
python3 << 'PYEOF'
import re, os, sys
src = os.path.expanduser(os.environ.get("EXPERT_PACK", "")) or os.path.expanduser(
    "~/.workbuddy/plugins/marketplaces/my-experts/plugins/fullstack-dev-team"
)
src_agents = os.path.join(src, "agents")
dst_agents = os.path.join(".ai-team", "agents")
os.makedirs(dst_agents, exist_ok=True)
count = 0
for f in sorted(os.listdir(src_agents)):
    if not f.endswith(".md"):
        continue
    text = open(os.path.join(src_agents, f)).read()
    body = re.sub(r'^---\n.*?\n---\n', '', text, count=1, flags=re.DOTALL)
    open(os.path.join(dst_agents, f), 'w').write(body)
    count += 1
    print(f"  ✓ {f}")
print(f"同步 {count} 个角色 prompt")
PYEOF

# 2. 提示 team-config.yaml 需手动核对
echo ""
echo "→ team-config.yaml 需手动核对："
echo "  - 新增/删除角色时，更新 members 列表"
echo "  - SOP 变更时，更新 sop.phases"
echo "  - 路由变更时，更新 routing_table"
echo ""
echo "✓ 同步完成。请用 git diff 检查变更。"
