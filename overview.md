# 智能问数"已提交确认"卡死 Bug — 修复完成

## 一句话总结
前端 `onMounted` + `onActivated` 加 `clearStaleSessionState()` 调用，keep-alive 切回时清空 UI 残留。**仅改 `frontend/src/views/SmartAsk.vue`，净 +4 行**。

---

## 根因

- Vue 全局 `<keep-alive>` 包裹 SmartAsk 路由（`App.vue:305`）
- keep-alive **激活**路径只触发 `onActivated`，**不触发** `onMounted`
- `onActivated` 没清组件层 reactive UI maps（旧 `confirmationSubmitting[msgId]=true` 保留在缓存里）
- 触发条件：`shouldShowConfirmationSubmitted(msg) = msg.data.requires_confirmation && confirmationSubmitting[msg.id]` 永远 true
- "已提交确认"卡片永远显示，按钮永远 disabled

后端完全健康（8-06 08:37 "上海" 35.75s 正常完成，`requires_confirmation=False`）。**不是后端 bug**。

---

## 改动（净 +4 行，仅 `SmartAsk.vue`）

```js
// L1346-1353 — 新增工具函数（setup 顶层）
const clearStaleSessionState = () => {
  const hasStaleRecovered = session.state.result || session.state.question || session.state.logs?.length
  if (!hasStaleRecovered || session.hasActiveAsk?.()) return
  session.clearRecoveredSessionResult()
  clearChatUiState()  // 复用 L3930 既有函数（覆盖 5 个 reactive + logOpen）
}

// L5714-5716 — onMounted 替换原守卫块为 1 行调用
clearStaleSessionState()

// L5732-5733 — onActivated 加 1 行调用（keep-alive 切回关键路径）
clearStaleSessionState()
```

---

## 验证

| 项 | 证据 |
|---|------|
| Vite build | ✅ 0 errors, 2298 modules, 6.33s |
| Docker build | ✅ smartask-frontend:test 已构建（17s） |
| grep 验证 | ✅ onMounted / onActivated / clearChatUiState / clearStaleSessionState 4 项全过 |
| emoji 扫描 | ✅ P0-1 通过 |
| 改动边界 | ✅ 仅 SmartAsk.vue，未碰后端 / contracts / four_agent_ask.py |
| **UI 真跑** | ⏸️ **未真跑**（用户取消 QA，自己验证） |

---

## 你 1 分钟验证步骤

1. 浏览器 `http://localhost:8888/smart-ask`
2. 发"上海"等需要确认口径的题
3. **点菜单切到任意其他页**（SQL 调试台 / 管理配置）—— **这是 keep-alive 路径**
4. 切回 SmartAsk
5. **预期**："已提交确认"卡片**不显示**；确认按钮可重新点击

**注意**：不要硬刷新（Ctrl+R / F5）——硬刷新走 onMounted 也能修，但 keep-alive 切回才是你真实的复现路径（截图 2 Network 1 request 346 B 是 keep-alive 特征）。

---

## 流程反思（用户三次纠正）

| 次数 | 用户反馈 | 真实诉求 | 我学到的 |
|------|----------|----------|----------|
| 1 | "我不需要确认的问题可以直接出答案" | 后端健康 | **不要预设 bug 再修**，先看真实数据 |
| 2 | "你有没有用专家的能力解决我的需求" | 走专家流程 | **纪律比效率重要**——任何代码改动走专家评审 |
| 3 | "太慢了，我就修复个问题啊" | 不要 over-engineering | **3 行修改走 3 专家完整流程是 over**——下次 ≤10 行修复只派 1 前端 + 1 QA |

**但专家团的价值仍成立**：架构师 catch 到的 keep-alive 盲点，我自己撸代码**绝对看不到**——这个 trade-off 值得。
