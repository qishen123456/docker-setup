# 前端审计报告（只读）

> 审计人：贾思敏 | 日期：2026-08-06 | 基线：frontend/src 46 文件 / 40483 行
>
> 审计方式：全程只读（Read / Grep / Glob / 只读 Bash）。未执行 npm install、npm run build，未修改 frontend/ backend/ 下任何文件。
> dist/ 相关数据来自 2026-08-06 10:10 的既有构建产物，非本次生成。
> 凡涉及运行时行为（内存增长、渲染掉帧、图表错位、断流表现）的判断，均已标注「（推断，未实证）」。

---

## 1. verdict

verdict: fail

判定依据：存在 2 条外部可控数据直入 `v-html` 且全链路无消毒的注入点（见 2.1、2.2），其中 1 条不经 markdown 渲染器，任何「加一层 Markdown 消毒」的方案都拦不住。此外存在 1 条「后端复核否决但前端零警示」的正确性展示缺陷（见 6.4），属于会误导业务决策的类别。

问题总数 29 条：P0 3 条 / P1 6 条 / P2 15 条 / P3 5 条。

---

## 2. 安全隐患（XSS 优先）

### 2.1 全仓 `v-html` 12 处逐条定级

全仓精确计数：`grep -rn 'v-html' src/ | wc -l` = 12，与体检报告一致。但分布与体检报告所述不同：体检报告称「SmartAsk.vue 内 8 处」，实测为 7 处，另 1 处在 ResultDigestCard.vue、4 处在 AIModels.vue（体检报告未提及后两者）。

定级原则：只有「外部可控数据 + 无 sanitize」才判 P0。数据来源分三档——
- A 档：用户或数据库直接可控，中间无 LLM（可控性最高，攻击者能精确构造 payload）
- B 档：经 LLM 生成，但 LLM 的输入含数据库业务字段（可控性中等，payload 需穿透模型复述）
- C 档：本地常量，外部数据无法穿透（不构成注入面）

| 编号 | 问题 | 证据(文件:行号) | 数据来源判定 | 可利用性 | 修复成本 | 是否实证 |
|---|---|---|---|---|---|---|
| XSS-01 | `renderMd(log.markdown)` 渲染的 markdown 中，直接插值了**用户原始提问文本** | 渲染点 `frontend/src/views/SmartAsk.vue:372`；渲染函数 `frontend/src/views/SmartAsk.vue:3851`；markdown 构造 `frontend/src/state/smartAskSession.js:1549`（`- 当前问题：${question || '未提供问题内容'}`）→ `:1577`（`markdown: buildFactMarkdown(question, route, datasetResults)`）→ 调用点 `:1650`（`buildFactEvent(data?.question \|\| state.question, route, datasetResults)`） | **A 档**：question 是输入框自由文本，无任何转义，中间不经 LLM | **高**。用户在问题框输入 `<img src=x onerror=...>` 即执行。单机看是 self-XSS，但该问题文本会随报告导出（`SmartAsk.vue:4787` `frameWindow.document.write(html)`）与飞书推送外流，构成跨用户路径 | S | **已实证**（数据流三跳全部读码确认） |
| XSS-02 | `secondaryDrillSummary` 把 SQL 结果字段拼进 HTML 字符串后 `v-html` 渲染，且不经 marked | 拼接 `frontend/src/components/smartask/ResultDigestCard.vue:2101-2105`（`parts.push(\`最高${best.name} ${best.rateText}\`)`、`parts.push(\`<span class="is-risk">${riskCount}个低于${riskThreshold.value}%预警线</span>\`)`）→ 消费 `frontend/src/components/smartask/ResultDigestCard.vue:118` | **A 档**：`best.name` / `worst.name` 来自 SQL 查询结果的维度值（组织名、人名、产品名），业务库内容非受控 | **高**。且该点**不经 markdown 渲染器**，无论消毒层放在前端还是后端 markdown 链路，都拦不住 | S | **已实证** |
| XSS-03 | `renderReportMd(section.body)` — 报告章节正文 | `frontend/src/views/SmartAsk.vue:458`；渲染函数 `:3852` | **B 档**：`analysis` 为 LLM 输出（`smartAskSession.js:1583` `String(dataset?.analysis \|\| '')`），同段还插值 `dataset_name`（`:1585` `## ${datasetName}`，DB 字段，A 档） | **中高**。LLM 复述业务字段时可能原样带出 payload；`dataset_name` 由管理员或数据导入写入，是稳定的 A 档旁路 | S | **已实证**（数据流已读码；「LLM 会原样复述 payload」这一环为推断，未实证） |
| XSS-04 | 同上，另一处报告章节 | `frontend/src/views/SmartAsk.vue:778` | 同 XSS-03，B 档（含 A 档旁路） | 中高 | S | 已实证 |
| XSS-05 | `renderReportMd(latestReport)` — 整篇报告 | `frontend/src/views/SmartAsk.vue:807` | 同 XSS-03 | 中高 | S | 已实证 |
| XSS-06 | 同上，报告章节 | `frontend/src/views/SmartAsk.vue:932` | 同 XSS-03 | 中高 | S | 已实证 |
| XSS-07 | 同上，报告章节 | `frontend/src/views/SmartAsk.vue:1173` | 同 XSS-03 | 中高 | S | 已实证 |
| XSS-08 | `renderReportMd(reportViewerReport \|\| latestReport)` — 全屏报告 | `frontend/src/views/SmartAsk.vue:1176` | 同 XSS-03 | 中高 | S | 已实证 |
| XSS-09 | `channelIconSvg(ch)` | `frontend/src/views/AIModels.vue:20` | **C 档**：内容来自本地常量 SVG 表。`channelIconKey`（`AIModels.vue:429-432`）→ `normalizeIconKey`（`:421-425`）把任意输入兜底回 `channelIconOptions` 白名单 key，DB 中的历史 emoji 由 `legacyEmojiIconMap`（`:403-419`）归一 | **无**。外部数据无法穿透白名单 | 不需修 | 已实证 |
| XSS-10 | `channelIconSvg(activeChannel)` | `frontend/src/views/AIModels.vue:50` | C 档，同上 | 无 | 不需修 | 已实证 |
| XSS-11 | `renderTechIcon(icon.key)` | `frontend/src/views/AIModels.vue:63` | C 档，同上 | 无 | 不需修 | 已实证 |
| XSS-12 | `channelIconSvg(activeChannel)` | `frontend/src/views/AIModels.vue:167` | C 档，同上 | 无 | 不需修 | 已实证 |

关于 XSS-09 至 XSS-12 的额外说明：这四处不是缺陷，反而是**把存量 emoji 图标迁移到矢量 SVG 的补救层**，方向正确。唯一遗留是数据库里仍存着 emoji 值（由 `legacyEmojiIconMap` 兜底），以及 CSS 类名残留 `cs-model-emoji`（`AIModels.vue:167`）。不建议把这四处计入 XSS 待办，会稀释真问题的优先级。

### 2.2 消毒层缺失的实证

- 全仓 `grep dompurify` 零命中；`frontend/package.json` dependencies 中无任何消毒库。
- `frontend/package.json` 声明 `"marked": "^17.0.5"`，marked 自 v5 起移除内置 `sanitize` 选项，v17 无内置消毒能力。
- 渲染出口只有两个：`frontend/src/views/SmartAsk.vue:3851`（`renderMd`）与 `:3852`（`renderReportMd`）。这是好消息——markdown 侧的消毒可以一处收口。
- 但 XSS-02 不走这两个出口，必须单独改模板结构。

### 2.3 非 v-html 的 HTML 注入面

| 编号 | 问题 | 证据(文件:行号) | 数据来源 | 可利用性 | 修复成本 | 是否实证 |
|---|---|---|---|---|---|---|
| XSS-13 | `frameWindow.document.write(html)` 导出报告 | `frontend/src/views/SmartAsk.vue:4787` | html 由 `buildReportHtml` 生成，内含 marked 渲染结果，与 XSS-03..08 同源 | 中高。修了 markdown 消毒后此处自动收敛 | 随 XSS-03 一并修 | 已实证 |
| XSS-14 | `ElMessageBox` 开启 `dangerouslyUseHTMLString` | `frontend/src/views/DatasetManagement.vue:1776`、`:1943`、`:1977`、`:1985`、`:1992` | 后端返回的错误信息与表名 | 中。管理员页面，触达面小 | S | 已实证 |

全仓 `innerHTML` / `outerHTML` / `eval(` / `new Function`：**零命中**（唯一动态 HTML 写入即 XSS-13）。

### 2.4 凭据与密钥

| 编号 | 问题 | 证据(文件:行号) | 说明 | 修复成本 | 是否实证 |
|---|---|---|---|---|---|
| SEC-01 | token 明文存 localStorage | `frontend/src/api/index.js:19-23`（`AUTH_TOKEN_KEY = 'auth_token'` + `localStorage.getItem`）；SSE 侧以自定义头下发 `frontend/src/api/index.js:205`（`'X-Auth-Token': token`） | 与 XSS-01/02 组合即完整会话劫持。注：使用自定义头而非 Cookie，反而规避了 CSRF，这个选择是对的 | M | 已实证 |
| SEC-02 | 前端无硬编码密钥（正面结论） | 扫描口径 `(api[_-]?key\|secret\|password\|token)\s*[:=]\s*['"][A-Za-z0-9_-]{12,}`，全仓唯一命中 `frontend/src/views/AIModels.vue:657`（`payload.api_key = 'inherit-channel'`），是哨兵值不是密钥 | 无需处理 | — | 已实证 |

---

## 3. SmartAsk.vue 上帝组件解剖

### 3.1 实测块边界与规模

| 块 | 行区间 | 行数 |
|---|---|---|
| `<template>` | 1 - 1236 | 1236 |
| `<script setup>` | 1238 - 5766 | 4529 |
| `<style scoped>` | 5768 - 9037 | 3270 |

体检报告的三个数字（1236 / 4529 / 3270）全部准确。

需要澄清的统计口径：`frontend/src/views/SmartAsk.vue:4713` 与 `:4736` 之间还有一对 `<style>` 标签，但那是 `buildReportHtml` 生成导出 HTML 字符串时的内联样式，不是 SFC 样式块，不应计入。

顶层声明数量实测：
- `grep -c '^const .*=>'` = **284**（体检报告称 232，低估 52 个）
- `grep -c '^const \|^let \|^function \|^async function '` = **342**（含非箭头函数的全部顶层声明）

### 3.2 script 段职责聚类（10 类）

| # | 职责聚类 | 行区间 | 约行数 | 主要耦合点 | 切分建议 | 独立难度 | 拆分风险 |
|---|---|---|---|---|---|---|---|
| C1 | 导入 + 状态接线（session / history / taskView / featureFlags 四个 store 钩子；query / datasetId / modelId / datasets / aiModels / messages / confirmationDrafts 基础 ref；displayMessages / displayLogs / displayResult） | 1239-1415 | 177 | 全文件依赖，是根节点 | 保留在 SFC，作为唯一装配层 | — | — |
| C2 | 状态栏文案 + 报告结果 computed + 数据集选择 + 置信度徽章 + 路由决策 | 1419-1790 | 372 | 依赖 C1 的 `session.state` | 抽 `useSmartAskStatus.js` | 中 | 低 |
| C3 | 纯格式化与业务计算（formatAmount / formatValueByColumn / formatBusinessValueByColumn / toNumber / sumBusinessColumn / calcBusinessRate / 色调判断 / getMetricCards） | 1790-2201 内的格式化子集 | 约 250 | **零 Vue 依赖，纯函数** | 抽 `utils/businessFormat.js`，**第一优先** | 低 | 极低 |
| C4 | 问题语义解析（getQuestionText / getRequestedLevelValues / 排名策略判定） | 1790-2201 内的解析子集 | 约 160 | 依赖 C3 的 toNumber | 抽 `utils/questionParse.js`，可直接写单测 | 低 | 极低 |
| C5 | 组织 KPI / 报告助手（getOfficeKpiLabel / getReportKpi / 下钻 / buildBusinessDrillReport） | 2202-2412 | 211 | 依赖 C3 + C4 | 抽 `domain/officeKpi.js` | 中 | 低 |
| C6 | 图表 spec 构建（buildCollectionMetricCards / buildOfficeDetailRows / inferChartSpec / getDatasetChartSpecs / buildReportTableBlocks；resultPreviews / sideReportCharts / reportDialogCharts） | 2413-3238 | **826** | 依赖 C3 + C5，产出纯数据结构 | 抽 `domain/chartSpec.js`，**第二优先**（最大单块且输出可断言） | 低 | 极低 |
| C7 | 报告叙事 + buildReportHtml + renderMd / renderReportMd | 3239-3890 | 652 | 依赖 C5 + C6；`:3851` / `:3852` 是 XSS 出口 | 抽 `domain/reportNarrative.js` + `render/markdown.js`（消毒层落在后者，一处收口） | 中 | **改动与 XSS-01/03 修复同批，必须配测试** |
| C8 | UI 开关 / 弹窗控制 / messageDerivedCache(WeakMap) / 消息渲染助手 / 输入框交互 | 3896-4504 | 609 | 强耦合模板 ref | 留在 SFC，不动 | 高 | — |
| C9 | 问答主流程（handleSend / handleStop / resetForNewChat / handleNewChat / downloadLatestReport / quickAsk / 确认选项 / doConfirm） | 4505-4996 | 492 | 耦合 session + SSE + 计时器 | 抽 `useAskFlow.js`，但需连同 smartAskSession 一起设计边界 | 高 | 中 |
| C10 | 滚动控制 + 计时器 + ECharts 生命周期 + watch 群 + 五个生命周期钩子 | 4997-5765 | 769 | 直接操作 DOM 与 echarts | ECharts 部分抽 `useEChartsPool.js`（顺带修 PERF-02 / PERF-05 / PERF-06）；滚动抽 `useAutoScroll.js` | 中 | 低 |

### 3.3 建议落地顺序与拆分后风险

顺序：C3 → C4 → C6 → C5 → C7 → C10(ECharts 部分) → C2 → C9。C8 不动。

前四步是纯搬迁、零行为变更，可一次性把 script 从 4529 行降到约 3100 行，且让 C3 / C4 / C6 立刻具备可测性——这正好是「先补测试网再动刀」的入口。

拆分后的主要风险：
1. **C7 与 XSS 修复耦合**：报告渲染逻辑搬家的同时要插入消毒层，两件事叠加会让回归定位困难。建议先在原位插消毒层并验证，再搬家。
2. **样式无法跟随**：`<style scoped>` 3270 行目前是 scoped 的、暂不构成污染，但 script 拆走后样式仍留在 SFC，模块边界会不一致。建议按 C6 / C7 的边界同步切成 chat / result / report / chart 四个 CSS 文件。
3. **C9 的边界不在前端单侧**：`handleSend` 与 `state/smartAskSession.js` 的 `startAsk`（`:1831`）职责重叠，单拆前端会把耦合搬到另一个文件而非消除。需要与架构师先定 store 与 composable 的依赖方向（体检报告第 7 节「前端 composable 切分边界」标注架构师未回，这是卡点）。
4. **已有成功范式可参照**：`frontend/src/composables/useSmartAskReportHistory.js`（344 行）证明这条路走得通，但 `composables/` 目录至今只有 2 个文件、合计 607 行，拆分是半途而废而非能力问题。

---

## 4. 性能问题

### 4.1 首屏与打包体积（dist 静态度量，非运行时指标）

| 产物 | raw | gzip |
|---|---|---|
| `frontend/dist/assets/SmartAsk-BQnvpJDR.js` | 1427221 B | 458145 B |
| `frontend/dist/assets/api-DpucX-yP.js` | 1075048 B | 332795 B |
| `frontend/dist/assets/index-U8KItfw0.css` | 413210 B | 57774 B |
| `frontend/dist/assets/SmartAsk-VH8dA4fM.css` | 121944 B | 19760 B |
| `frontend/dist/assets/index-COCUTBX0.js` | 121816 B | 42033 B |
| `frontend/dist/angel-logowite.png` | 1909722 B | 44468 B |
| dist 总计 | 5.4 MB | — |

本节不提供 Lighthouse 分数或首屏耗时，因为本次审计未运行浏览器，任何此类数字都会是编造。

| 编号 | 问题 | 证据(文件:行号) | 影响 | 修复方向 | 成本 |
|---|---|---|---|---|---|
| PERF-01 | 三处全量引入：echarts 全量、Element Plus 全量 + 全量 CSS、循环注册全部 Element Plus 图标 | `frontend/src/views/SmartAsk.vue:1242`（`import * as echarts from 'echarts'`）；`frontend/src/main.js:2-3`；`frontend/src/main.js:15-17` | 直接对应上表的 1.39 MB / 1.05 MB / 403 KB 三块 | echarts 改 `echarts/core` + 按需 `use([...])`；Element Plus 换 unplugin-vue-components + ElementPlusResolver；图标改按名引入——`frontend/src/App.vue:428` 已经是按需写法，可直接作为范式 | M |
| PERF-02 | 内嵌 ECharts 实例从不 dispose | 创建 `frontend/src/views/SmartAsk.vue:5543`、`:5558`；唯一 dispose `frontend/src/views/SmartAsk.vue:5761-5764`（只覆盖 `chartDialogRef` 弹窗图表）；模板挂载点 `:268`、`:357`、`:688`、`:724`、`:751`、`:1129` | 每轮问答产生新图表 DOM，旧 DOM 被 v-if/v-for 销毁后 echarts 内部注册表仍持引用；页面又被 keep-alive 常驻，实例只增不减（推断，未实证——未做堆快照） | 加 `onBeforeUnmount` / watch 清理，或在 `resetForNewChat` 中遍历 `frontend/src/views/SmartAsk.vue:5527` 的现成选择器逐个 `getInstanceByDom(el)?.dispose()` | S |
| PERF-03 | 1.82 MB PNG 作为顶栏 logo，全站每页加载 | `frontend/public/angel-logowite.png` 1909722 B（PNG 1886x246 RGBA）；引用点 `frontend/src/App.vue:15`、`frontend/src/auth/AuthLogin.vue:5` | 未登录页与全站顶栏都吃这张图。gzip 后仅 44 KB，说明图像内容高度冗余，是导出参数问题而非内容问题 | 转 SVG（logo 天然矢量）或压到 30 KB 以内的 WebP。投入产出比最高的一条 | S |
| PERF-04 | vite 无 manualChunks、无产物分析、无压缩插件 | `frontend/vite.config.js` 全文仅 `vue()` 插件 + `@` alias + `/api` dev proxy | echarts / element-plus 与业务代码混在同一 chunk，任何业务改动都让用户重下 1.39 MB | 配 `rollupOptions.output.manualChunks` 拆出长缓存 vendor chunk | S |
| PERF-05 | 全文件无 window resize 监听，内嵌图表不随窗口或侧栏折叠重排 | `frontend/src/views/SmartAsk.vue` 全文件仅 1 处 addEventListener（`:5691`，自定义事件 `smartask-create-fresh-chat`）；`resizeRenderedCharts`（`:5524`）仅被 `:3894` openReportViewer、`:3910` openFullScreenReport、`:3996` openChartViewer 调用 | 侧栏折叠（App.vue collapsed）改变容器宽度、窗口缩放、分辨率切换时图表尺寸错位，需重新打开弹窗才恢复（推断，未实证） | debounce 后的 window resize → `resizeRenderedCharts`；或改 ResizeObserver 绑容器 | S |
| PERF-06 | onActivated 只刷数据不 resize 图表 | `frontend/src/views/SmartAsk.vue:5723-5737` | keep-alive 切回时若侧栏状态变了，图表保持切走前的尺寸 | onActivated 末尾补一次 `resizeRenderedCharts()` | S |
| PERF-07 | keep-alive 缓存「全部有权限页面」而非「需要保状态的页面」，且按同一名单 idle 预加载 | `frontend/src/App.vue:585-587`（`cachedPageNames` = 所有 availableMenuItems 对应组件名）；`frontend/src/App.vue:305`（`<keep-alive :include="cachedPageNames">`）；`frontend/src/App.vue:1006-1017` scheduleRoutePreload → `frontend/src/App.vue:1010` `preloadRouteComponents(cachedPageNames.value)` | 超管有 13 个菜单项（`App.vue:512-526`）→ 13 个页面组件全部下载且常驻不销毁，AdminConsole(3574 行) / DatasetManagement(2389 行) / FeishuSync(1990 行) 的 reactive 状态与定时器一并常驻（推断，未实证——未做内存测量）。路由懒加载（`frontend/src/router/index.js` 全量 `() => import()`）的收益被此处抵消大半 | `:include` 收敛到真正需要保状态的 2-3 个页面；预加载名单与缓存名单解耦 | S |
| PERF-08 | 两处 el-table 无行数上限且无虚拟滚动 | `frontend/src/views/SmartAsk.vue:1150`（`:data="block.rows"`，数据源 `frontend/src/views/SmartAsk.vue:3219` 直接透传 `dataset.rows`，未截断）；`frontend/src/views/SmartAsk.vue:1222`（`:data="chartViewerTableRows"`，数据源 `:3999-4001` 原样返回 `spec.rows`） | Element Plus el-table 即使设 `height` 也只做固定表头、不做行虚拟化，全部行渲染真实 DOM。SQL 返回上千行时首次展开长时间掉帧（推断，未实证——未压测）。其余表格均已 `slice(0,5)` / `slice(0,6)` 截断，风险面仅此 2 处 | 这 2 处换 el-table-v2 或加分页，不必全站改造 | M |
| PERF-09 | 递归 setTimeout 打字机无任何清理 | `frontend/src/components/smartask/WelcomeScreen.vue:93-104`（`const run = () => { …; setTimeout(run, 30) }`）；该文件生命周期仅 `:107` onMounted，无 onUnmounted / onBeforeUnmount | 欢迎屏在首次提问后被销毁，递归定时器继续以 30ms/字 写已卸载组件的 ref 直到文本跑完 | 存 timer id 并在 onBeforeUnmount 清；或改 rAF + 卸载标志位 | S |
| PERF-10 | axios 全局 timeout 600000 ms（10 分钟） | `frontend/src/api/index.js:6` | 任何挂死接口都让 UI 转圈 10 分钟才报错 | 普通接口降到 30-60 s，长任务接口单独放宽 | S |

### 4.2 响应式深监听与重复请求核查（结论：基本健康）

- `v-for` 缺 key：**零命中**。全仓 118 处 `v-for`，用多行窗口（前后各 3 行）精确核查后缺 key 数为 0。单行 grep 会报出 55 处假阳性，因为 `:key` 常写在下一行。**这条不是问题，特此澄清，避免被当成待办。**
- 重复请求：`frontend/src/state/featureFlags.js` 有 `loadingPromise` 请求去重，`frontend/src/router/index.js:136-149` `preloadRouteComponents` 有 `preloadCache` 去重，两处设计正确。
- `onMounted`（`SmartAsk.vue:5690-5720`）与 `onActivated`（`:5723-5737`）都会拉 `getBookshelfDatasets` + `getActiveAIModels`，首次进入页面时两个钩子的触发关系未做去重（推断：keep-alive 首次挂载不触发 onActivated，故实际不重复；未实证）。

---

## 5. SSE 前端消费链路

### 5.1 帧处理机制

- 传输层：不使用 `EventSource`，而是 `fetch` + `response.body.getReader()` 手动解析。实现位于 `frontend/src/api/index.js:197-285`（`sendSseRequest`）。按 `\n\n` 拆帧，解析 `event:` / `data:` 后 `JSON.parse`。
- 鉴权：`frontend/src/api/index.js:205` 以 `X-Auth-Token` 自定义头下发（EventSource 无法自定义头，这是选择 fetch 方案的合理动因）。
- 帧分派：`frontend/src/state/smartAskSession.js:1869-1882`，按 `trace` / `heartbeat` / `result` 三类分派；`result` 帧仅暂存到 `finalPayload`，不立即渲染。
- 竞态防护：`runToken`（`frontend/src/state/smartAskSession.js:1834` 自增，`:1870`、`:1886`、`:1948` 校验）确保旧轮次的迟到帧不会污染新轮次。这个设计是对的。

### 5.2 前端自有节奏层（直接回答「后端 sleep 能否单独拆除」）

**结论：前端不依赖后端的人为延迟。后端拆掉 `four_agent_ask.py:8070-8074` 的 `time.sleep(random.uniform(2.0, 3.0))`，前端不会出现闪烁、步骤条跳步或动画来不及播。**

依据是前端自己实现了一套独立且更强的节奏兜底层：

1. **每阶段最小可见时长表**：`frontend/src/state/smartAskSession.js:354-362`

   | 阶段 key | 最小可见时长 |
   |---|---|
   | trace-route | 3200 ms |
   | trace-context | 3200 ms |
   | trace-agent2 | 4600 ms |
   | trace-agent3 | 3600 ms |
   | trace-execute | 3200 ms |
   | trace-agent4 | 5200 ms |
   | result-final-check | 3600 ms |

2. **后端过快时前端主动压住**：`frontend/src/state/smartAskSession.js:1009-1011` 计算 `shouldDelaySuccess = 状态为 success && 该阶段在节奏名单内 && 实际耗时 < 最小可见时长`。命中时 `:1041` 把状态强制写回 `'running'`，并由 `:1061-1066` 交给 `settlePacedTraceKey`（`:394-415`）挂一个 `setTimeout` 补足差额后再落 success。

   即：**后端越快，前端补的越多，总时长恒定不变。** 后端那 2-3 秒 sleep 落在前端 3200-5200 ms 的地板之下，被完全吸收。

3. **节奏是串行的，不是并行**：`shouldQueueTraceEvent`（`frontend/src/state/smartAskSession.js:369-376`）在已有节奏计时器且新事件属于不同阶段时，把事件推入 `traceEventQueue`；`flushQueuedTraceEvents`（`:378-392`）仅在 `tracePacingTimers.size === 0` 时才出队。因此同一时刻只有一个阶段在「播放」，阶段之间不会重叠、不会跳步。

4. **结果展示还有一道独立地板**：`frontend/src/state/smartAskSession.js:1928-1941`。收到 result 帧后先 `await waitForTracePacing()`（`:1930`）排空节奏队列，再插入 `result-final-check` 节点，然后 `await wait(Math.max(3600, 4200 - elapsedMs))`（`:1941`，常量见 `:470` `MIN_ANALYSIS_VISIBLE_MS = 4200`）。也就是说**结果最快也要在 result 帧之后再等 3600 ms 才显示**。

5. **UI 动画同样是前端本地时序，与后端无关**：
   - 逐节点揭示动画：`frontend/src/components/smartask/LogTimeline.vue:400-440`，全部为本地常量 80 / 120 / 140 / 180 / 190 / 240 ms。
   - 打字机：`frontend/src/components/smartask/TypewriterLine.vue:50-58`，`setInterval` 步进 `Math.max(8, props.speed || 18)` ms。
   - 欢迎屏打字机：`frontend/src/components/smartask/WelcomeScreen.vue:99`，固定 30 ms/字。
   - 无后端帧时的兜底相位推进：`frontend/src/state/smartAskSession.js:488`（`phaseTimer` setInterval），在完全收不到 trace 帧时也能让步骤条自行前进。

**给团队的直接结论（这条影响 P0 止血的排期）**：后端那 2-3 秒 sleep 是**冗余的双重填充**，可以单独删除、无需前端配合改动。但同时要认识到——**删除它对用户感知的提速接近于零**，因为前端地板（每阶段 3.2-5.2 s 串行 + 结果尾部 3.6 s）才是 Golden SQL 直取路径的真正约束。若目标是「让最快路径真的快」，必须同时给前端节奏层加一个「快路径豁免」开关，否则后端优化在 UI 上不可见（推断：具体端到端时长取决于该路径实际发出哪些 trace 阶段，未实证）。

建议的前端配合项（不阻塞后端止血）：在 `getTraceMinVisibleMs`（`frontend/src/state/smartAskSession.js:354`）与 `MIN_ANALYSIS_VISIBLE_MS`（`:470`）上加一个由后端 result 帧标记（如 `fast_path: true`）驱动的缩放系数，Golden 命中时整体缩到 1/4。

### 5.3 断线重连与错误态

| 编号 | 问题 | 证据(文件:行号) | 影响 | 修复方向 | 成本 |
|---|---|---|---|---|---|
| SSE-01 | 无重连、无空闲超时判活 | `frontend/src/api/index.js:197-285`，异常分支只区分用户主动取消（`:181-195` `isAbortLikeError` / `createUserAbortError`），无 reconnect，无基于 heartbeat 的超时判定 | 后端已发 heartbeat 帧、前端也有 `applyHeartbeatEvent`（`frontend/src/state/smartAskSession.js:1876`），但不据此判活。网络抖动导致流静默中断时，前端停在「运行中」不报错（推断，未实证——未做断网实验） | 加空闲计时器：N 秒无帧判定断流并提示；至少支持一次自动重连 | M |
| SSE-02 | 流结束但无 result 帧时才抛错，属事后发现 | `frontend/src/state/smartAskSession.js:1887-1889`（`if (!finalPayload) throw new Error('后端实时执行流已结束，但没有返回最终结果。')`） | 这条兜底是对的，但只在流正常结束时生效；流被中间设备静默掐断时不触发（配合 SSE-01） | 与 SSE-01 一并修 | M |
| SSE-03 | 错误态展示完整（正面结论） | `frontend/src/state/smartAskSession.js:1799-1818`（error 分支清节奏、置 status、追加 `request-error` 日志节点并展开 diagnostics）；`:1959-1963`（异常时把所有 running 节点翻成 error） | 错误可见性做得好，不是问题 | — | — |

### 5.4 SSE 相关内存增长

- 每轮 trace 帧持续 append 到 `state.logs`（`frontend/src/state/smartAskSession.js:436-467`），且 `persist()`（`:282-288`）会把 state 写入 localStorage（键 `smart-ask-session-v1`，`:4`）。长对话下单条 session 体积随帧数线性增长（推断，未实证——未测量实际字节数）。
- `liveThoughtLines` 有上限保护：`frontend/src/state/smartAskSession.js:1032` `.slice(-MAX_LIVE_THOUGHT_LINES)`，这处设计正确。
- delta 帧不落盘：`frontend/src/state/smartAskSession.js:1055` `persist: !isDelta`，避免高频写 localStorage，这处设计也正确。
- history 侧有配额保护：`frontend/src/state/smartAskHistory.js:231`（quota 超限告警）、`:262`（兜底 removeItem）。

---

## 6. 代码质量与可维护性

### 6.1 工程化门禁缺失

| 编号 | 问题 | 证据(文件:行号) | 影响 | 成本 |
|---|---|---|---|---|
| QA-01 | 无 ESLint / Prettier / TypeScript / typecheck | `frontend/package.json` devDependencies 仅 `@vitejs/plugin-vue` + `vite`；scripts 仅 dev / build / preview / test:dataset-autofill；无 `.eslintrc`、无 `tsconfig.json` | 40483 行 JS 无任何静态门禁。漏 import、拼错属性名、未处理 Promise 全部靠运行时暴露；跨 40 余文件的重命名或删除无法安全进行 | M |
| QA-02 | 唯一的测试是孤儿脚本 | `frontend/tests/regression/confirmation-residual-card.spec.cjs`（git 已跟踪）；但无 `playwright.config`，`package.json` 无对应 script，playwright 未声明在 devDependencies（其依赖被塞在 `frontend/tests/regression/node_modules/` 且未被 git 跟踪） | 任何人 clone 后都跑不起来，CI 不会执行。**体检报告称「零测试」，实质属实但表述需修正**——不是没人写过，是写了没接进工程 | S |
| QA-03 | 双 lockfile 并存且不同步，生产构建不可复现 | `frontend/package-lock.json`（59508 B，Aug 4）与 `frontend/pnpm-lock.yaml`（34792 B，Jul 1）均被 git 跟踪；`frontend/Dockerfile:11`（只 COPY pnpm-lock.yaml）、`:13`（`pnpm install --no-frozen-lockfile`）、`:17`（`rm -f pnpm-workspace.yaml` 后才 build） | 本地 npm 装 8/4 的依赖树，生产 pnpm 装 7/1 的树且允许自行改写解析——线上跑的依赖树没有任何一份 lockfile 能精确还原。这是「本地能跑生产炸」的结构性成因。`rm workspace.yaml` 是绕开配置冲突的 hack | S |

### 6.2 样式架构

| 编号 | 问题 | 证据(文件:行号) | 影响 | 成本 |
|---|---|---|---|---|
| QA-04 | App.vue 的 `<style>` 未加 scoped，1876 行全局 CSS 泄漏到全站 | `frontend/src/App.vue:1095`（`<style>`，无 scoped）至 `:2970`；代码内已有自认注释 `frontend/src/App.vue:1533`「注意：`<style>` 非 scoped，:deep() 无效，必须用普通选择器」 | **这解答了「App.vue 为何 2971 行」**：script 段只有 `:424-1093` 共 670 行，相当克制；63% 的体积是无归宿的全局样式。任何组件的类名都可能被这 1876 行意外命中，是「改 A 崩 B」的主要来源 | M |
| QA-05 | 另有两个非 scoped 全局样式块 | `frontend/src/views/AdminConsole.vue:3549-3574`；`frontend/src/views/EmployeePermissions.vue:727-747` | 同上，规模较小 | S |

### 6.3 组件耦合与复用

| 编号 | 问题 | 证据 | 影响 | 成本 |
|---|---|---|---|---|
| QA-06 | 13 个组件全部只有 1 个引用方，复用度为 0 | `components/smartask/` 下 ChatHeader / ComposerArea / LiveExecutionFeed / LogTimeline / PlanCard / ResultDigestCard / SqlBlock / ThinkingCard / UserBubble / WelcomeScreen 均只被 `frontend/src/views/SmartAsk.vue` 引用；TypewriterLine 只被 `frontend/src/components/smartask/LiveExecutionFeed.vue` 引用；SqlDebugFloat / TaskStatusIndicator 只被 `frontend/src/App.vue` 引用 | 这些不是「组件」而是「SmartAsk.vue 的模板切片」，没有独立契约。**`ResultDigestCard.vue` 已达 3863 行，比大多数页面还大，它是下一个 SmartAsk.vue** | L |
| QA-07 | API 层有旁路，封装不统一 | `frontend/src/api/index.js` 导出 107 个函数，但 `frontend/src/api/index.js:142` 在 404 fallback 中直接用裸 `axios.post`（绕过实例拦截器与 timeout）；`frontend/src/views/DatasetReportConfig.vue:365` 直接 `import axios from 'axios'` 自行发请求 | 旁路请求不走统一错误提示与鉴权头，鉴权策略变更时会漏改 | S |
| QA-08 | 空 catch 吞异常 | `frontend/src/views/SmartAsk.vue:5706`、`:5711`（onMounted 内 `catch {}`）；`:5729`、`:5733`（onActivated 内同款） | 数据集 / 模型加载失败时页面静默呈现空列表，用户无从判断是「没有数据」还是「请求挂了」 | S |
| QA-09 | featureFlags 模块级 addEventListener 无对应 removeEventListener | `frontend/src/state/featureFlags.js:55`（该文件 addEventListener 计数 1 / removeEventListener 计数 0） | 模块单例、SPA 生命周期内只绑一次，实际影响可忽略；HMR 下会重复绑定 | S |
| QA-10 | emoji 当功能图标 | UI 图标：`frontend/src/views/SmartAsk.vue:25`、`:26`、`:27`、`:225`、`:287`；`frontend/src/views/DatasetReportConfig.vue:305`（三个 el-option label）。业务文案：`frontend/src/views/SmartAsk.vue:2027-2029`（`getRateTag` 返回带 emoji 前缀）、`:2051-2053`（`getOfficeRateTag` 同款）。符号字符当图标：`frontend/src/components/smartask/LiveExecutionFeed.vue:30`、`frontend/src/components/smartask/ThinkingCard.vue:7`、`frontend/src/views/FeishuSync.vue:725` | `:2027-2053` 那 6 处最严重：它们进入报告正文，会被 buildReportHtml 导出并推送飞书，等于把 emoji 固化进对外业务产物 | S |

### 6.4 Agent3 复核被否决时的前端展示（重点核查项）

**结论：当 `agent3_review.approved === false` 但后端仍返回数据时，前端界面上没有任何显式警示。用户看到的和复核通过时几乎一样。**

逐条证据：

1. **全仓只有一处读 `approved`，且只用于扣分**：`frontend/src/views/SmartAsk.vue:1672`（`const approvedCount = reviews.filter(item => item?.approved !== false).length`），消费于 `:1682`（全部通过时 `score += 12`）与 `:1683`（部分通过时 `score += 6`）。也就是说 approved 为 false 的唯一后果，是信心分少加 6 到 12 分。

2. **这唯一的扣分逻辑还可能根本不执行**：`buildResultConfidenceMeta` 只在 `frontend/src/views/SmartAsk.vue:1718` 被调用，而该调用处于三元表达式的 **else 分支**——`:1711` 判断 `backendConfidence?.result` 存在时，走 `:1712-1717` 的后端分数分支，前端**完全不读 `agent3_review.approved`**。即：只要后端返回了 `result.confidence.result` 字段，否决状态在前端连扣分都不会发生。

3. **界面上唯一相关的徽章不体现否决**：`sideConfidenceBadges`（`frontend/src/views/SmartAsk.vue:1697-1757`）渲染于 `frontend/src/views/SmartAsk.vue:392-401`，输出形如「结果稳定：85」的文字 chip。tone 只由分数阈值决定（`:1691` `score >= 80 ? 'success' : score >= 62 ? 'info' : 'warning'`），与 approved 无关。分数只要过 80，被否决的结果照样显示绿色「结果稳定」。

4. **结果卡里的复核状态文案是死代码，且逻辑本身也不看 approved**：`frontend/src/components/smartask/ResultDigestCard.vue:283-287` 定义了 `reviewStatusText`，返回「已完成」/「N 项风险」/「SQL通过」。两个问题——
   - 它只统计 `risks` 数组长度（`:279`），**不读 `approved`**。若后端否决但 risks 为空，它会返回字面量 **「SQL通过」**，把被否决的结果标成通过。
   - 更关键的是：全仓 grep `reviewStatusText` 只有定义处 3 行命中，模板中零引用，该组件也无 `defineExpose`。**这个 computed 从未被渲染**，属死代码。也就是说连这个（本就不正确的）弱提示都没有出现在界面上。

5. **唯一可能透出信息的地方是一行普通正文**：`frontend/src/views/SmartAsk.vue:3812-3813`，若 `primary?.agent3_review?.review_summary` 存在，则把它作为一条普通 bullet 追加进报告摘要，无任何警示样式、无颜色、无图标、不置顶。用户注意不到（推断：未做用户测试，但从代码看该 bullet 与「命中数据集」「数据结果」等中性信息并列，无视觉区分——这部分是实证）。

6. **风险项文案存在但只在执行日志里**：`frontend/src/state/smartAskSession.js:776-777`（`if (Array.isArray(payload.risks) && payload.risks.length > 0) lines.push('识别风险：' + payload.risks.join('；'))`）。这条进入右侧执行详情的日志行，不在结果区、不在报告正文。

**修复建议（优先级建议 P0，与 XSS 同批）**：
- 在 `frontend/src/views/SmartAsk.vue:1711-1718` 的分支外，独立计算 `hasRejectedReview = datasets.some(d => d?.agent3_review?.approved === false)`，不受后端 confidence 字段有无影响。
- 命中时在结果区顶部渲染显式警示条（可复用 `frontend/src/views/SmartAsk.vue:24-27` 的只读横幅结构，但图标要按 QA-10 换成 SVG），文案需明确「该结果未通过 SQL 复核，仅供参考」。
- 修正 `frontend/src/components/smartask/ResultDigestCard.vue:283-287` 的判定逻辑（增加 approved 判断），并把它真正渲染出来，或直接删掉这段死代码避免误导后续维护者。
- 成本：S（1 天内）。

---

## 7. 技术债偿还建议

### 7.1 分级统计

| 级别 | 数量 | 条目 |
|---|---|---|
| P0 | 3 | XSS-01（用户提问直入 v-html）、XSS-02（SQL 字段拼 HTML 后 v-html）、QA-11（Agent3 否决零警示，即 6.4） |
| P1 | 6 | SEC-01（token 存 localStorage）、PERF-01（三处全量引入）、PERF-02（ECharts 不 dispose）、PERF-07（keep-alive 全缓存）、QA-01（零静态门禁）、QA-03（构建不可复现） |
| P2 | 15 | XSS-03..08（报告 markdown 六处）、XSS-13、XSS-14、PERF-03、PERF-04、PERF-05、PERF-08、QA-04、SSE-01、QA-06 |
| P3 | 5 | PERF-06、PERF-09、PERF-10、QA-05、QA-07 / QA-08 / QA-09 / QA-10 归并计 |

（XSS-09..12 判定为非问题，不计入。）

### 7.2 偿还顺序

**第一批（本周，止血）**
1. XSS-02：`ResultDigestCard.vue:2101-2105` 拆成文本走插值、高亮走模板结构，彻底不用 v-html。成本 S。
2. XSS-01 + XSS-03..08 + XSS-13：引入 DOMPurify，在 `SmartAsk.vue:3851` / `:3852` 两个出口统一 `DOMPurify.sanitize(marked.parse(x))`，allowlist 只放 markdown 需要的标签。**两个出口即全部收口，改动面极小。** 成本 S。
3. QA-11（6.4）：加显式否决警示条。成本 S。
4. QA-03：二选一锁死包管理器、删掉另一份 lockfile、Dockerfile 改 `--frozen-lockfile`。需与运维协同。成本 S。

关于消毒层选型的立场（对应体检报告第 7 节「Markdown 消毒层选型，架构师未回」）：**前端 DOMPurify 是必须项且今天就能落，不要等后端方案。** 后端消毒可作为第二层慢慢做。且 XSS-02 不经 markdown，无论消毒层放哪都拦不住，必须单独改模板——这一条不能被「等架构师定方案」阻塞。

**第二批（下周，止损）**
5. PERF-03：logo 转 SVG 或压缩。半天，收益立竿见影。
6. PERF-02 + PERF-05 + PERF-06：抽 `useEChartsPool.js`，一次性解决实例泄漏、无 resize 监听、切回不重排三件事——它们本质是同一个缺失（没有实例生命周期的归属人）。成本 S。
7. PERF-07：`keep-alive :include` 收敛。成本 S。
8. QA-01 第一步：装 eslint + eslint-plugin-vue，只开 `vue3-essential` + `no-undef` + `no-unused-vars` + `no-empty`，先跑成 warning 不 fail。目的只有一个——把「漏 import」「拼错变量名」挡在运行时之前。半天。

**第三批（两周内，减债）**
9. PERF-01 + PERF-04：按需引入 + manualChunks。成本 M。
10. SSE-01：加空闲超时判活 + 一次自动重连。成本 M。
11. SmartAsk.vue 拆分第一阶段：C3 → C4 → C6 → C5（纯搬迁，零行为变更），script 从 4529 行降到约 3100 行。同步用 vitest 给这三个纯函数模块补单测。成本 M。
12. QA-04：App.vue 全局样式抽到 `src/styles/`，按 Element Plus 覆盖 / 布局 / 主题分文件。成本 M。

**明确不做的事**
- 不引入 TypeScript 全量改造：40483 行 .vue 迁移成本远超收益。改为 `jsconfig.json` + `// @ts-check` 只覆盖 `utils/` 与 `state/` 两个纯 JS 目录。
- 不为复用而重构 `components/smartask/` 下的 13 个组件（QA-06）。它们只有一个引用方是事实，但拆开不会产生价值。唯一例外是 `ResultDigestCard.vue` 3863 行必须再拆。
- 不追求测试覆盖率数字。测试的目的是给 C3/C4/C6 的搬迁提供回归保护，不是刷指标。
- 不为 P3 问题设 CI 门禁。

### 7.3 与后端 P0 止血的协同结论

后端 `four_agent_ask.py:8070-8074` 的 `time.sleep(random.uniform(2.0, 3.0))` **可以单独删除，无需前端配合**，理由见 5.2。但需同步认知：删除后用户感知的提速接近于零，因为前端节奏地板（每阶段 3.2-5.2 s 串行 + 结果尾部 3.6 s）才是 Golden 直取路径的真正约束。若要让最快路径真的变快，需要前端在 `frontend/src/state/smartAskSession.js:354` 与 `:470` 增加快路径豁免系数——这项可以排在后端止血之后，不构成阻塞。

---

## 附：审计范围与方法声明

- 只读工具：Read / Grep / Glob / 只读 Bash（wc、ls、file、du、gzip -c 计量、git ls-files）。
- 未执行：npm install、npm run build、npm run dev、任何写操作（本文件除外）。
- emoji 扫描口径：Unicode 区间 `U+1F300-1FAFF`、`U+2600-27BF`、`U+2B00-2BFF`、`U+FE0F`、`U+2190-21FF`，全仓命中 42 处，其中作功能图标使用的见 QA-10。
- v-for key 核查口径：以每处 `v-for` 前后各 3 行为窗口检索 `:key` / `key=`，118 处全部命中，缺失数为 0。
- 本报告未使用任何未经实读的行号，未引用任何未验证的 API，未提供任何未实测的运行时性能数字。
