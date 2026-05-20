<template>
  <div class="console-page">
    <section class="console-hero">
      <div class="hero-copy">
        <span class="hero-kicker">{{ activeHero.kicker }}</span>
        <h1>系统控制台</h1>
        <p>{{ activeHero.description }}</p>
      </div>
      <div class="hero-actions">
        <el-button plain @click="toggleAdminFloat">{{ adminFloatEnabled ? '关闭悬浮入口' : '开启悬浮入口' }}</el-button>
        <template v-if="activeConsoleTab === 'permissions' || activeConsoleTab === 'fields'">
          <el-button plain :loading="loading" @click="loadFlags">刷新</el-button>
          <el-button plain type="warning" :loading="resetting" @click="handleReset">恢复默认</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
        </template>
        <template v-else-if="activeConsoleTab === 'ask-flow'">
          <el-button plain :loading="askFlowLoading" @click="loadAskFlowConfig">刷新流程配置</el-button>
          <el-button plain type="warning" :loading="askFlowResetting" @click="handleAskFlowReset">恢复默认</el-button>
          <el-button type="primary" :loading="askFlowSaving" @click="handleAskFlowSave">保存流程配置</el-button>
        </template>
        <template v-else-if="activeConsoleTab === 'data'">
          <el-button plain :loading="dataPermissionLoading" @click="loadDataPermissions">刷新数据集权限</el-button>
          <el-button type="primary" :loading="dataPermissionSaving" @click="saveDataPermissionRules">保存数据集权限</el-button>
        </template>
        <template v-else-if="activeConsoleTab === 'logs' || activeConsoleTab === 'dashboard'">
          <el-button plain :loading="activeConsoleTab === 'dashboard' ? dashboardLoading : logLoading" @click="activeConsoleTab === 'dashboard' ? loadDashboardData() : loadLogData()">{{ activeConsoleTab === 'dashboard' ? '刷新看板' : '刷新日志' }}</el-button>
          <el-button v-if="activeConsoleTab === 'logs'" plain type="danger" :loading="logClearing" @click="handleClearLogs">清理查询日期内日志</el-button>
        </template>
      </div>
    </section>

    <section class="console-tabs">
      <button type="button" :class="{ active: activeConsoleTab === 'dashboard' }" @click="switchConsoleTab('dashboard')">管理看板</button>
      <button type="button" :class="{ active: activeConsoleTab === 'permissions' }" @click="switchConsoleTab('permissions')">功能权限控制</button>
      <button type="button" :class="{ active: activeConsoleTab === 'ask-flow' }" @click="switchConsoleTab('ask-flow')">问数流程控制</button>
      <button type="button" :class="{ active: activeConsoleTab === 'fields' }" @click="switchConsoleTab('fields')">字段显示权限</button>
      <button type="button" :class="{ active: activeConsoleTab === 'data' }" @click="switchConsoleTab('data')">数据集权限控制</button>
      <button type="button" :class="{ active: activeConsoleTab === 'logs' }" @click="switchConsoleTab('logs')">日志管理</button>
    </section>

    <section class="console-command-layout" :class="{ 'is-data-tab': activeConsoleTab === 'data' }">
      <main class="console-command-main">
    <template v-if="activeConsoleTab === 'dashboard'">
      <section class="dashboard-toolbar">
        <div>
          <span class="card-kicker">日期筛选</span>
          <strong>{{ dashboardRangeLabel }}</strong>
        </div>
        <el-date-picker
          v-model="dashboardDateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          :clearable="false"
          @change="loadDashboardData"
        />
        <div class="dashboard-toolbar-actions">
          <el-button plain @click="setDashboardToday">今天</el-button>
          <el-button plain @click="setDashboardLast7Days">近7天</el-button>
          <el-button type="primary" :loading="dashboardLoading" @click="loadDashboardData">查询</el-button>
        </div>
      </section>

      <section class="dashboard-grid">
        <button
          v-for="card in dashboardCards"
          :key="card.key"
          type="button"
          class="dashboard-card"
          :class="`is-${card.tone}`"
          @click="openLogsFromDashboard(card.filter)"
        >
          <span>{{ card.label }}</span>
          <strong>{{ card.value }}</strong>
          <small>{{ card.hint }}</small>
        </button>
      </section>

      <section class="dashboard-panels dashboard-rank-panels">
        <article v-for="panel in dashboardUserRankPanels" :key="panel.key" class="dashboard-panel dashboard-rank-panel">
          <header>
            <div>
              <span class="card-kicker">{{ panel.kicker }}</span>
              <h2>{{ panel.title }}</h2>
            </div>
            <el-button link type="primary" @click="openLogsFromDashboard(panel.filter)">看日志</el-button>
          </header>
          <el-table :data="panel.rows" border stripe class="dashboard-table" :empty-text="panel.emptyText">
            <el-table-column label="用户" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">
                <div class="dashboard-user-cell">
                  <strong>{{ userRankName(row) }}</strong>
                  <small>{{ roleLabel(row.user_role) }}</small>
                </div>
              </template>
            </el-table-column>
            <el-table-column :label="panel.metricLabel" width="116">
              <template #default="{ row }">
                <strong class="rank-metric" :class="`is-${panel.tone}`">{{ formatNumber(row[panel.metricKey] || 0) }}</strong>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="86">
              <template #default="{ row }">
                <el-button link type="primary" @click="jumpToUserLogs(row, panel.filter)">定位</el-button>
              </template>
            </el-table-column>
          </el-table>
        </article>
      </section>

      <section class="dashboard-panels">
        <article class="dashboard-panel">
          <header>
            <div>
              <span class="card-kicker">低置信度问题</span>
              <h2>需要补口径的问题</h2>
            </div>
            <el-button link type="primary" @click="openLogsFromDashboard({ category: 'low_confidence' })">全部日志</el-button>
          </header>
          <el-table :data="recentLowConfidenceLogs" border stripe class="dashboard-table" empty-text="暂无低置信度问题">
            <el-table-column label="时间" width="150">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="用户" width="120" show-overflow-tooltip>
              <template #default="{ row }">{{ row.user_name || row.username || '-' }}</template>
            </el-table-column>
            <el-table-column label="问题" min-width="220" show-overflow-tooltip>
              <template #default="{ row }">{{ row.question || whatHappened(row) }}</template>
            </el-table-column>
            <el-table-column label="置信度" width="120">
              <template #default="{ row }">{{ confidenceLabel(row.confidence) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="92">
              <template #default="{ row }">
                <el-button link type="primary" @click="jumpToLog(row)">看日志</el-button>
              </template>
            </el-table-column>
          </el-table>
        </article>

        <article class="dashboard-panel">
          <header>
            <div>
              <span class="card-kicker">错误问题</span>
              <h2>需要排查的异常</h2>
            </div>
                <el-button link type="primary" @click="openLogsFromDashboard({ category: 'error' })">全部日志</el-button>
          </header>
          <el-table :data="recentErrorLogs" border stripe class="dashboard-table" empty-text="暂无错误日志">
            <el-table-column label="时间" width="150">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="用户" width="120" show-overflow-tooltip>
              <template #default="{ row }">{{ row.user_name || row.username || '-' }}</template>
            </el-table-column>
            <el-table-column label="错误" min-width="240" show-overflow-tooltip>
              <template #default="{ row }">{{ row.error_message || whatHappened(row) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="92">
              <template #default="{ row }">
                <el-button link type="primary" @click="jumpToLog(row)">看日志</el-button>
              </template>
            </el-table-column>
          </el-table>
        </article>
      </section>
    </template>

    <template v-else-if="activeConsoleTab === 'ask-flow'">
      <section class="ask-flow-panel" v-loading="askFlowLoading">
        <section class="ask-flow-overview">
          <div class="ask-flow-overview-copy">
            <span class="card-kicker">问数流程控制</span>
            <h2>{{ isAdvancedFlowSelected ? '当前默认使用进阶流程' : '当前默认使用基础流程' }}</h2>
            <p>这里控制用户提问时默认进入哪套问数流程。基础流程保持现状，进阶流程用于后续 Skill、规划和工具能力灰度。</p>
          </div>
          <div class="ask-flow-overview-status">
            <strong>{{ askFlowDecision.flow === 'advanced' ? '进阶流程' : '基础流程' }}</strong>
            <span>{{ askFlowReasonText }}</span>
            <el-tag :type="isAdvancedFlowSelected ? 'success' : 'info'" effect="light">
              {{ isAdvancedFlowSelected ? '当前选择进阶' : '当前选择基础' }}
            </el-tag>
          </div>
        </section>

        <section class="flow-choice-shell">
          <div class="flow-section-head">
            <span>1</span>
            <div>
              <strong>选择默认问数流程</strong>
              <small>这是最主要的配置。选中后点击保存即可生效。</small>
            </div>
          </div>
          <div class="flow-choice-grid">
            <button
              type="button"
              class="flow-choice-card"
              :class="{ active: askFlowConfig.defaultFlow === 'basic' }"
              @click="selectAskFlow('basic')"
            >
              <span class="flow-choice-tag">稳定</span>
              <strong>基础流程</strong>
              <small>沿用当前四 Agent 链式问数，适合日常经营问数。</small>
              <i>{{ askFlowConfig.defaultFlow === 'basic' ? '当前使用' : '点击切换' }}</i>
            </button>

            <button
              type="button"
              class="flow-choice-card"
              :class="{ active: askFlowConfig.defaultFlow === 'advanced' }"
              @click="selectAskFlow('advanced')"
            >
              <span class="flow-choice-tag">升级</span>
              <strong>进阶流程</strong>
              <small>独立新流程入口。当前先镜像基础流程，后续逐步加入 Skill 和规划能力。</small>
              <i>{{ askFlowConfig.defaultFlow === 'advanced' ? '当前使用' : '点击切换' }}</i>
            </button>
          </div>
        </section>

        <section class="ask-flow-card">
          <div class="ask-flow-card-head">
            <div>
              <span class="card-kicker">保护策略</span>
              <h3>进阶流程控制</h3>
            </div>
            <el-button text type="primary" @click="askFlowAdvancedOpen = !askFlowAdvancedOpen">
              {{ askFlowAdvancedOpen ? '收起' : '展开设置' }}
            </el-button>
          </div>
          <div v-if="askFlowAdvancedOpen" class="flow-settings-grid">
            <label class="flow-setting-item">
              <span>异常自动回退</span>
              <small>进阶流程异常时自动切回基础流程。</small>
              <el-switch v-model="askFlowConfig.fallbackToBasicOnError" />
            </label>
            <label class="flow-setting-item">
              <span>问数界面显示流程标识</span>
              <small>问数完成后显示“基础流程 / 进阶流程”。</small>
              <el-switch v-model="askFlowConfig.attachMetadata" />
            </label>
            <div class="flow-setting-item is-wide">
              <span>允许使用进阶流程的角色</span>
              <small>这里是进阶流程灰度名单；账号必须同时拥有功能权限控制里的“使用进阶问数流程”。</small>
              <el-checkbox-group v-model="askFlowConfig.advancedRoles" class="flow-role-checks">
                <el-checkbox v-for="role in roles" :key="role.value" :label="role.value">{{ role.label }}</el-checkbox>
              </el-checkbox-group>
            </div>
          </div>
          <div v-else class="flow-collapsed-summary">
            <span>回退保护：{{ askFlowConfig.fallbackToBasicOnError ? '开启' : '关闭' }}</span>
            <span>流程标识：{{ askFlowConfig.attachMetadata ? '显示' : '隐藏' }}</span>
            <span>角色：{{ askFlowRoleSummary }}</span>
          </div>
        </section>

        <section class="ask-flow-card">
          <div class="ask-flow-card-head">
            <div>
              <span class="card-kicker">可选灰度</span>
              <h3>按数据集指定流程</h3>
            </div>
            <el-button text type="primary" @click="askFlowDatasetOpen = !askFlowDatasetOpen">
              {{ askFlowDatasetOpen ? '收起' : '展开灰度' }}
            </el-button>
          </div>
          <div v-if="askFlowDatasetOpen" class="flow-dataset-policy">
            <p>只在需要让某个数据集先试用进阶流程时配置。留空则全部跟随上面的默认流程。</p>
            <div v-for="(row, index) in askFlowDatasetPolicyRows" :key="row.key" class="flow-dataset-row">
              <el-input v-model="row.datasetId" placeholder="数据集 ID，例如 12" />
              <el-select v-model="row.flow" placeholder="流程">
                <el-option label="基础流程" value="basic" />
                <el-option label="进阶流程" value="advanced" />
              </el-select>
              <el-button plain type="danger" @click="removeAskFlowDatasetPolicy(index)">删除</el-button>
            </div>
            <el-button plain type="primary" @click="addAskFlowDatasetPolicy">添加数据集灰度</el-button>
          </div>
          <div v-else class="flow-collapsed-summary">
            <span>{{ askFlowDatasetPolicyRows.length ? `${askFlowDatasetPolicyRows.length} 个数据集单独指定` : '未单独指定数据集，全部跟随默认流程' }}</span>
          </div>
        </section>

        <div class="ask-flow-actions">
          <el-button plain :loading="askFlowLoading" @click="loadAskFlowConfig">刷新</el-button>
          <el-button plain type="warning" :loading="askFlowResetting" @click="handleAskFlowReset">恢复默认</el-button>
          <el-button type="primary" :loading="askFlowSaving" @click="handleAskFlowSave">保存流程配置</el-button>
        </div>
      </section>
    </template>

    <template v-else-if="activeConsoleTab === 'permissions' || activeConsoleTab === 'fields' || activeConsoleTab === 'data'">
    <section v-if="activeConsoleTab === 'permissions'" class="summary-strip">
      <div><strong>{{ navigationItems.length }}</strong><span>导航项</span></div>
      <div><strong>{{ buttonItems.length }}</strong><span>按钮项</span></div>
      <div><strong>{{ enabledButtonCount }}</strong><span>已开放按钮</span></div>
      <div><strong>{{ highRiskCount }}</strong><span>高风险项</span></div>
    </section>
    <section v-if="activeConsoleTab === 'fields'" class="summary-strip">
      <div><strong>{{ fieldItems.length }}</strong><span>字段项</span></div>
      <div><strong>{{ enabledFieldCount }}</strong><span>已开放字段</span></div>
      <div><strong>{{ fieldGroups.length }}</strong><span>覆盖模块</span></div>
      <div><strong>{{ highRiskFieldCount }}</strong><span>敏感字段</span></div>
    </section>

    <el-skeleton v-if="loading && !featureList.length" :rows="8" animated />

    <template v-else-if="activeConsoleTab === 'fields'">
      <section class="module-section">
        <div class="module-title">
          <div>
            <span class="card-kicker">字段显示权限</span>
            <h2>按页面模块控制字段可见性</h2>
          </div>
          <em>字段权限只控制显示；高敏字段后续会继续补后端裁剪。</em>
        </div>

        <section
          v-for="group in fieldGroups"
          :key="group.module"
          class="module-card"
          :class="{ 'is-open': isModuleOpen(group.module) }"
        >
          <button class="module-card-head" type="button" @click="toggleModule(group.module)">
            <div class="module-head-copy">
              <span class="module-scope">字段显示</span>
              <strong>{{ group.label }}</strong>
              <small>{{ group.description }}</small>
            </div>
            <div class="module-head-stats">
              <span>{{ group.enabledCount }}/{{ group.items.length }} 开放</span>
              <i>{{ group.riskCount }} 个敏感</i>
            </div>
          </button>

          <div v-show="isModuleOpen(group.module)" class="matrix-table compact">
            <div class="matrix-row matrix-head">
              <div class="feature-col">字段项</div>
              <label v-for="role in roles" :key="role.value" class="role-head" :class="{ checked: isRoleAllChecked(group.items, role.value) }">
                <input type="checkbox" :checked="isRoleAllChecked(group.items, role.value)" @change="toggleRoleAll(group.items, role.value, $event.target.checked)" />
                <span class="check-box"></span>
                <span class="role-name">{{ role.label }}</span>
                <small>全选</small>
              </label>
            </div>
            <div v-for="item in group.items" :key="item.key" class="matrix-row" :class="{ 'is-risk': item.risk === 'high' || item.risk === 'medium' }">
              <div class="feature-col">
                <span class="feature-tag">{{ item.risk === 'high' ? '高敏' : item.risk === 'medium' ? '敏感' : '字段' }}</span>
                <strong>{{ item.label }}</strong>
                <small>{{ item.description }}</small>
              </div>
              <label
                v-for="role in roles"
                :key="role.value"
                class="permission-check"
                :class="{ checked: hasRole(item, role.value), disabled: isFixedPermission(item, role.value) }"
              >
                <input
                  type="checkbox"
                  :checked="hasRole(item, role.value)"
                  :disabled="isFixedPermission(item, role.value)"
                  @change="setRole(item, role.value, $event.target.checked)"
                />
                <span class="check-box"></span>
              </label>
            </div>
          </div>
        </section>
      </section>
    </template>

    <template v-else-if="activeConsoleTab === 'data'">
      <section class="summary-strip data-summary-strip">
        <div><strong>{{ dataPermissionRows.length }}</strong><span>数据集</span></div>
        <div><strong>{{ orgScopedDatasetCount }}</strong><span>组织树控制</span></div>
        <div><strong>{{ dataPermissionTreeTypes.length }}</strong><span>组织树类型</span></div>
        <div><strong>{{ employeesWithOrgCount }}</strong><span>已授权员工</span></div>
      </section>

      <section class="data-permission-card" v-loading="dataPermissionLoading">
        <div class="data-permission-toolbar">
          <div>
            <span class="card-kicker">数据集权限控制</span>
            <h2>数据集绑定组织树与行级过滤</h2>
            <p>角色只控制功能板块；数据集按组织树和组织节点控制可见范围，员工在账号页选择组织节点后自动生效。</p>
          </div>
        </div>
        <el-table :data="dataPermissionDisplayRows" border stripe class="data-permission-table">
          <el-table-column label="数据集" min-width="190">
            <template #default="{ row }">
              <strong>{{ row.dataset_name }}</strong>
              <small>{{ row.business_domain || row.dataset_code }}</small>
            </template>
          </el-table-column>
          <el-table-column label="模式" width="108">
            <template #default="{ row }">
              <el-tag :type="dataModeTagType(row.rule.mode)" effect="plain">{{ dataModeLabel(row.rule.mode) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="组织树" min-width="220">
            <template #default="{ row }">
              <div class="dataset-scope-tags">
                <el-tag v-for="item in row._display.treeLabels" :key="item" size="small">{{ item }}</el-tag>
                <span v-if="!row._display.treeLabels.length" class="muted-text">未绑定</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="授权组织" min-width="260">
            <template #default="{ row }">
              <div class="dataset-scope-tags">
                <el-tag v-for="item in row._display.orgLabels.slice(0, 4)" :key="item" size="small" type="success">{{ item }}</el-tag>
                <el-tag v-if="row._display.orgLabels.length > 4" size="small">+{{ row._display.orgLabels.length - 4 }}</el-tag>
                <span v-if="!row._display.orgLabels.length" class="muted-text">未选择</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="命中员工" width="118">
            <template #default="{ row }">
              <button class="scope-summary scope-summary-button" type="button" @click="openScopedEmployeePreview(row)">
                <strong>{{ row._display.scopedEmployeeCount }}</strong>
                <span>人</span>
              </button>
            </template>
          </el-table-column>
          <el-table-column label="备注" min-width="150" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.rule.note || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="96" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDataRuleEditor(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </template>

    <template v-else>
      <section class="permission-card">
        <header class="card-head">
          <div>
            <span class="card-kicker">导航权限</span>
            <h2>左侧导航栏</h2>
            <p>只控制左侧菜单入口是否显示，不影响页面里的按钮。</p>
          </div>
          <em>{{ navigationEnabledCount }}/{{ navigationItems.length }} 开放</em>
        </header>
        <div class="matrix-table">
          <div class="matrix-row matrix-head">
            <div class="feature-col">功能项</div>
            <label v-for="role in roles" :key="role.value" class="role-head" :class="{ checked: isRoleAllChecked(navigationItems, role.value) }">
              <input type="checkbox" :checked="isRoleAllChecked(navigationItems, role.value)" @change="toggleRoleAll(navigationItems, role.value, $event.target.checked)" />
              <span class="check-box"></span>
              <span class="role-name">{{ role.label }}</span>
              <small>全选</small>
            </label>
          </div>
          <div v-for="item in navigationItems" :key="item.key" class="matrix-row">
            <div class="feature-col">
              <strong>{{ item.label }}</strong>
              <small>{{ item.description }}</small>
            </div>
            <label
              v-for="role in roles"
              :key="role.value"
              class="permission-check"
              :class="{ checked: hasRole(item, role.value), disabled: isFixedPermission(item, role.value) }"
            >
              <input
                type="checkbox"
                :checked="hasRole(item, role.value)"
                :disabled="isFixedPermission(item, role.value)"
                @change="setRole(item, role.value, $event.target.checked)"
              />
              <span class="check-box"></span>
            </label>
          </div>
        </div>
      </section>

      <section class="module-section">
        <div class="module-title">
          <div>
            <span class="card-kicker">按钮权限</span>
            <h2>按导航模块归属</h2>
          </div>
          <em>按钮只放在自己所属页面或全局区域中。</em>
        </div>

        <section
          v-for="group in buttonGroups"
          :key="group.module"
          class="module-card"
          :class="{ 'is-open': isModuleOpen(group.module) }"
        >
          <button class="module-card-head" type="button" @click="toggleModule(group.module)">
            <div class="module-head-copy">
              <span class="module-scope">{{ group.scopeLabel }}</span>
              <strong>{{ group.label }}</strong>
              <small>{{ group.description }}</small>
            </div>
            <div class="module-head-stats">
              <span>{{ group.enabledCount }}/{{ group.items.length }} 开放</span>
              <i>{{ group.riskCount }} 个高风险</i>
            </div>
          </button>

          <div v-show="isModuleOpen(group.module)" class="module-permission-body">
            <section v-for="section in group.sections" :key="section.key" class="permission-section">
              <div class="permission-section-head">
                <div>
                  <span>{{ section.label }}</span>
                  <small>{{ section.description }}</small>
                </div>
                <em>{{ section.enabledCount }}/{{ section.items.length }} 开放</em>
              </div>
              <div class="matrix-table compact">
                <div class="matrix-row matrix-head">
                  <div class="feature-col">功能项</div>
                  <label v-for="role in roles" :key="role.value" class="role-head" :class="{ checked: isRoleAllChecked(section.items, role.value) }">
                    <input type="checkbox" :checked="isRoleAllChecked(section.items, role.value)" @change="toggleRoleAll(section.items, role.value, $event.target.checked)" />
                    <span class="check-box"></span>
                    <span class="role-name">{{ role.label }}</span>
                    <small>全选</small>
                  </label>
                </div>
                <div v-for="item in section.items" :key="item.key" class="matrix-row" :class="{ 'is-risk': item.risk === 'high' }">
                  <div class="feature-col">
                    <span class="feature-tag">{{ item.subgroupLabel || section.label }}</span>
                    <strong>{{ item.label }}</strong>
                    <b v-if="item.risk === 'high'">高风险</b>
                    <small>{{ item.description }}</small>
                  </div>
                  <label
                    v-for="role in roles"
                    :key="role.value"
                    class="permission-check"
                    :class="{ checked: hasRole(item, role.value), disabled: isFixedPermission(item, role.value) }"
                  >
                    <input
                      type="checkbox"
                      :checked="hasRole(item, role.value)"
                      :disabled="isFixedPermission(item, role.value)"
                      @change="setRole(item, role.value, $event.target.checked)"
                    />
                    <span class="check-box"></span>
                  </label>
                </div>
              </div>
            </section>
          </div>
        </section>
      </section>
    </template>
    </template>

    <template v-else>
      <section class="summary-strip log-summary-strip">
        <div><strong>{{ logStats.last_24h || 0 }}</strong><span>24小时记录</span></div>
        <div><strong>{{ logStats.errors_7d || 0 }}</strong><span>7天报错</span></div>
        <div><strong>{{ logStats.low_confidence_7d || 0 }}</strong><span>7天低置信</span></div>
        <div><strong>{{ totalLogs }}</strong><span>当前筛选</span></div>
      </section>

      <section class="log-card">
        <div class="log-toolbar">
          <el-select v-model="logFilters.category" placeholder="日志类型" clearable style="width:180px" @change="loadLogs">
            <el-option label="全部" value="" />
            <el-option label="登录访问" value="auth" />
            <el-option label="接口访问" value="access" />
            <el-option label="报错" value="error" />
            <el-option label="低置信问答" value="low_confidence" />
            <el-option label="问答记录" value="qa_all" />
            <el-option label="数据集生成" value="dataset_generation" />
          </el-select>
          <el-select v-model="logFilters.level" placeholder="级别" clearable style="width:130px" @change="loadLogs">
            <el-option label="info" value="info" />
            <el-option label="warning" value="warning" />
            <el-option label="error" value="error" />
          </el-select>
          <el-date-picker
            v-model="logFilters.date_range"
            type="daterange"
            unlink-panels
            value-format="YYYY-MM-DD"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 280px"
          />
          <el-input v-model="logFilters.keyword" clearable placeholder="搜索用户、路径、问题、SQL、答案..." @keyup.enter="loadLogs" />
          <el-button type="primary" :loading="logLoading" @click="loadLogs">查询</el-button>
          <el-button plain :loading="logExporting" @click="exportFilteredLogs">导出</el-button>
        </div>

        <el-table :data="logs" border stripe v-loading="logLoading" class="log-table">
          <el-table-column prop="created_at" label="时间" width="178">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="类型" width="112">
            <template #default="{ row }"><el-tag :type="categoryTagType(row.category)" effect="plain">{{ categoryLabel(row.category) }}</el-tag></template>
          </el-table-column>
          <el-table-column label="级别" width="92">
            <template #default="{ row }"><el-tag :type="levelTagType(row.level)" effect="plain">{{ row.level }}</el-tag></template>
          </el-table-column>
          <el-table-column label="事件名称" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">{{ eventName(row) }}</template>
          </el-table-column>
          <el-table-column label="用户" width="150" show-overflow-tooltip>
            <template #default="{ row }">{{ row.user_name || row.username || '-' }}</template>
          </el-table-column>
          <el-table-column label="发生了什么" min-width="260" show-overflow-tooltip>
            <template #default="{ row }">{{ whatHappened(row) }}</template>
          </el-table-column>
          <el-table-column label="建议" min-width="260" show-overflow-tooltip>
            <template #default="{ row }">{{ actionSuggestion(row) }}</template>
          </el-table-column>
          <el-table-column label="置信度" width="110">
            <template #default="{ row }">{{ confidenceLabel(row.confidence) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openLogDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="log-pager">
          <span>共 {{ totalLogs }} 条</span>
          <el-pagination
            layout="prev, pager, next, sizes"
            :total="totalLogs"
            :current-page="logPage"
            :page-size="logPageSize"
            :page-sizes="[50, 100, 200]"
            @current-change="onLogPageChange"
            @size-change="onLogPageSizeChange"
          />
        </div>
      </section>

      <el-drawer v-model="logDetailVisible" size="64%" title="日志详情" destroy-on-close>
        <div v-if="selectedLog" class="log-detail">
          <div class="detail-grid">
            <div><span>类型</span><strong>{{ categoryLabel(selectedLog.category) }}</strong></div>
            <div><span>级别</span><strong>{{ selectedLog.level }}</strong></div>
            <div><span>用户</span><strong>{{ selectedLog.user_name || selectedLog.username || '-' }}</strong></div>
            <div><span>耗时</span><strong>{{ selectedLog.duration_ms ? `${selectedLog.duration_ms}ms` : '-' }}</strong></div>
          </div>
          <section class="detail-section detail-highlight">
            <h3>事件名称</h3>
            <p>{{ eventName(selectedLog) }}</p>
          </section>
          <section class="detail-section">
            <h3>发生了什么</h3>
            <p>{{ whatHappened(selectedLog) }}</p>
          </section>
          <section class="detail-section">
            <h3>建议怎么处理</h3>
            <p>{{ actionSuggestion(selectedLog) }}</p>
          </section>
          <section class="detail-section">
            <h3>建议检查的代码位置</h3>
            <pre>{{ codeHint(selectedLog) }}</pre>
          </section>
          <section v-if="selectedLog.request_path" class="detail-section">
            <h3>请求路径</h3>
            <pre>{{ selectedLog.request_method || '' }} {{ selectedLog.request_path }}</pre>
          </section>
          <section v-if="selectedLog.question" class="detail-section">
            <h3>问题</h3>
            <p>{{ selectedLog.question }}</p>
          </section>
          <section v-if="selectedLog.error_message" class="detail-section">
            <h3>错误</h3>
            <pre>{{ selectedLog.error_message }}</pre>
          </section>
          <section v-if="selectedLog.sql_text" class="detail-section">
            <h3>SQL</h3>
            <pre>{{ selectedLog.sql_text }}</pre>
          </section>
          <section v-if="selectedLog.answer_text" class="detail-section">
            <h3>答案</h3>
            <pre>{{ selectedLog.answer_text }}</pre>
          </section>
          <section class="detail-section">
            <h3>思考过程</h3>
            <el-timeline v-if="thinkingRows(selectedLog).length">
              <el-timeline-item v-for="(item, index) in thinkingRows(selectedLog)" :key="index" :timestamp="item.time || ''" :type="timelineType(item.status)">
                <strong>{{ item.stage || item.agent || '执行节点' }}</strong>
                <p v-if="item.detail">{{ item.detail }}</p>
                <p v-if="item.reasoning">{{ item.reasoning }}</p>
                <p v-if="item.stream">{{ item.stream }}</p>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无思考过程记录" :image-size="60" />
          </section>
          <section class="detail-section">
            <h3>原始详情</h3>
            <pre>{{ prettyJson({ confidence: selectedLog.confidence, details: selectedLog.details }) }}</pre>
          </section>
        </div>
      </el-drawer>
    </template>
      </main>

    </section>

    <div v-if="activeConsoleTab === 'permissions' || activeConsoleTab === 'fields' || activeConsoleTab === 'data'" class="console-floating-save">
      <el-button
        v-if="activeConsoleTab === 'permissions' || activeConsoleTab === 'fields'"
        type="primary"
        :loading="saving"
        :disabled="!featureList.length"
        @click="handleSave"
      >
        保存配置
      </el-button>
      <el-button
        v-else
        type="primary"
        :loading="dataPermissionSaving"
        :disabled="!dataPermissionRows.length"
        @click="saveDataPermissionRules"
      >
        保存数据集权限
      </el-button>
    </div>

    <el-dialog v-model="dataRuleDialog.visible" title="编辑数据集权限" width="720px" destroy-on-close>
      <el-form v-if="dataRuleForm" label-position="top" class="data-rule-form">
        <div class="data-rule-dataset">
          <span>数据集</span>
          <strong>{{ dataRuleForm.dataset_name }}</strong>
          <small>{{ dataRuleForm.business_domain || dataRuleForm.dataset_code }}</small>
        </div>
        <el-form-item label="权限模式">
          <el-radio-group v-model="dataRuleForm.rule.mode">
            <el-radio-button label="public">公开</el-radio-button>
            <el-radio-button label="org_tree">按组织树控制</el-radio-button>
            <el-radio-button label="disabled">停用</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="组织树类型">
          <el-select
            v-model="dataRuleForm.rule.tree_type_ids"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
            clearable
            :disabled="dataRuleForm.rule.mode !== 'org_tree'"
            placeholder="可选择多棵组织树"
            @change="onDataRuleTreeChange(dataRuleForm)"
          >
            <el-option v-for="item in dataPermissionTreeTypes" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="授权组织">
          <el-tree-select
            v-model="dataRuleForm.rule.organization_node_ids"
            :data="datasetOrganizationOptions(dataRuleForm.rule.tree_type_ids)"
            multiple
            collapse-tags
            collapse-tags-tooltip
            check-strictly
            filterable
            node-key="id"
            :props="{ label: 'label', value: 'id', children: 'children' }"
            :disabled="dataRuleForm.rule.mode !== 'org_tree' || !(dataRuleForm.rule.tree_type_ids || []).length"
            placeholder="选择具体组织节点"
          >
            <template #header>
              <div class="tree-select-panel-actions compact-actions" @click.stop>
                <el-button size="small" @click="selectDataRuleCurrentTree(dataRuleForm)">全选当前树</el-button>
                <el-button size="small" @click="completeDataRuleChildren(dataRuleForm)">补齐含下级</el-button>
                <el-button size="small" @click="clearDataRuleOrganizations(dataRuleForm)">全部清空</el-button>
              </div>
            </template>
          </el-tree-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="dataRuleForm.rule.note" placeholder="权限说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dataRuleDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="applyDataRuleEditor">应用</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="scopedEmployeeDrawer.visible"
      width="820px"
      top="7vh"
      title="命中员工明细"
      class="scoped-employee-dialog"
      destroy-on-close
    >
      <div v-if="scopedEmployeeDrawer.row" class="scoped-employee-panel">
        <section class="scoped-employee-head">
          <div>
            <span>数据集</span>
            <strong>{{ scopedEmployeeDrawer.row.dataset_name }}</strong>
            <small>{{ scopedEmployeeDrawer.row.business_domain || scopedEmployeeDrawer.row.dataset_code }}</small>
          </div>
          <div>
            <span>权限模式</span>
            <strong>{{ dataModeLabel(scopedEmployeeDrawer.row.rule.mode) }}</strong>
            <small>{{ scopedEmployeeCount(scopedEmployeeDrawer.row.rule) }} 人命中</small>
          </div>
        </section>
        <div class="scoped-employee-filter">
          <el-input
            v-model="scopedEmployeeDrawer.keyword"
            clearable
            placeholder="搜索姓名、账号、部门、岗位或组织"
          />
        </div>
        <el-table :data="filteredScopedEmployees" border stripe class="scoped-employee-table" max-height="430">
          <el-table-column label="员工" min-width="150">
            <template #default="{ row }">
              <strong>{{ row.name || row.account || row.id }}</strong>
              <small>{{ row.account || row.mobile || row.email || '-' }}</small>
            </template>
          </el-table-column>
          <el-table-column label="角色" width="112">
            <template #default="{ row }">
              <el-tag size="small" effect="plain">{{ roleLabel(row.role) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="部门 / 岗位" min-width="160">
            <template #default="{ row }">
              <strong>{{ row.department || '-' }}</strong>
              <small>{{ row.position || '-' }}</small>
            </template>
          </el-table-column>
          <el-table-column label="命中组织" min-width="220">
            <template #default="{ row }">
              <div class="dataset-scope-tags">
                <el-tag v-for="item in row.match_labels.slice(0, 2)" :key="item" size="small" type="success" :title="item">{{ item }}</el-tag>
                <el-tag v-if="row.match_labels.length > 2" size="small" :title="row.match_labels.slice(2).join('、')">+{{ row.match_labels.length - 2 }}</el-tag>
                <span v-if="!row.match_labels.length" class="muted-text">{{ row.match_reason }}</span>
              </div>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!filteredScopedEmployees.length" description="暂无命中员工" :image-size="72" />
        <p class="scoped-employee-note">超级管理员拥有系统全量访问，不计入组织树命中名单。</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import {
  clearSystemLogs,
  getAdminFeatureFlags,
  getAskFlowConfig,
  getDataPermissions,
  getSystemLogDetail,
  getSystemLogs,
  getSystemLogStats,
  resetAdminFeatureFlags,
  resetAskFlowConfig,
  saveDataPermissions,
  saveAskFlowConfig,
  saveAdminFeatureFlags,
} from '../api/index.js'

const route = useRoute()
const router = useRouter()
const roles = [
  { value: 'super_admin', label: '超管' },
  { value: 'admin', label: '管理员' },
  { value: 'business_admin', label: '业务管理员' },
  { value: 'user', label: '普通用户' }
]
const roleOrder = roles.map((item) => item.value)
const FEATURE_FLAGS_UPDATED_EVENT = 'smartask-feature-flags-updated'
const ADMIN_CONSOLE_LAST_ROUTE_KEY = 'smartask_admin_console_last_route'
const ADMIN_CONSOLE_FLOAT_HIDDEN_KEY = 'smartask_admin_console_float_hidden'
const ADMIN_CONSOLE_FLOAT_TOGGLE_EVENT = 'smartask-admin-console-float-toggle'
const consoleTabs = ['dashboard', 'permissions', 'ask-flow', 'fields', 'data', 'logs']

const loading = ref(false)
const saving = ref(false)
const resetting = ref(false)
const features = ref({})
const openModules = ref(['organization_tree_management', 'employee_permissions', 'runtime_migration'])
const activeConsoleTab = ref('dashboard')
const askFlowLoading = ref(false)
const askFlowSaving = ref(false)
const askFlowResetting = ref(false)
const askFlowDecision = ref({})
const askFlowAdvancedOpen = ref(false)
const askFlowDatasetOpen = ref(false)
const askFlowDatasetPolicyRows = ref([])
const askFlowConfig = ref({
  defaultFlow: 'basic',
  advancedEnabled: false,
  advancedRoles: ['super_admin'],
  datasetPolicies: {},
  fallbackToBasicOnError: true,
  attachMetadata: false,
})
const dataPermissionLoading = ref(false)
const dataPermissionSaving = ref(false)
const dataPermissionRows = ref([])
const dataRuleDialog = ref({ visible: false })
const dataRuleForm = ref(null)
const scopedEmployeeDrawer = ref({ visible: false, row: null, keyword: '' })
const dataPermissionEmployees = ref([])
const dataPermissionOrganizationTrees = ref({ tree_types: [], nodes: [], trees: {} })
const logs = ref([])
const logStats = ref({})
const totalLogs = ref(0)
const logLoading = ref(false)
const logClearing = ref(false)
const logExporting = ref(false)
const logPage = ref(1)
const logPageSize = ref(100)
const logDetailVisible = ref(false)
const selectedLog = ref(null)
const adminFloatEnabled = ref(false)
const allFetchedLogs = ref([])
const logFilters = ref({
  category: '',
  level: '',
  keyword: '',
  trace_id: '',
  date_range: [],
})
const formatDateValue = (date) => {
  const current = date instanceof Date ? date : new Date(date)
  if (Number.isNaN(current.getTime())) return ''
  const year = current.getFullYear()
  const month = String(current.getMonth() + 1).padStart(2, '0')
  const day = String(current.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
const todayDateValue = formatDateValue(new Date())
const dashboardDateRange = ref([todayDateValue, todayDateValue])
const dashboardLoading = ref(false)

const activeHero = computed(() => {
  if (activeConsoleTab.value === 'dashboard') {
    return {
      kicker: '管理看板',
      description: '集中查看访问、问数、token、报错和低置信度问题，并可直接跳转日志定位。'
    }
  }
  if (activeConsoleTab.value === 'fields') {
    return {
      kicker: '字段显示权限',
      description: '控制页面里的敏感字段是否展示，例如员工角色、组织、电话、SQL 和置信度。'
    }
  }
  if (activeConsoleTab.value === 'logs') {
    return {
      kicker: '日志审计',
      description: '集中查看登录访问、接口报错和低置信度问答，保留问题、思考过程、SQL 与答案。'
    }
  }
  if (activeConsoleTab.value === 'data') {
    return {
      kicker: '数据集权限控制',
      description: '按数据集绑定组织树和组织节点，员工在账号页选择组织节点后自动获得对应数据范围。'
    }
  }
  if (activeConsoleTab.value === 'ask-flow') {
    return {
      kicker: '问数流程控制',
      description: '配置基础流程和进阶流程的入口、灰度角色和回退策略，确保升级版问数可控发布。'
    }
  }
  return {
    kicker: '功能权限控制',
    description: '按角色勾选左侧导航和页面按钮权限；数据范围不在这里配置。'
  }
})

const askFlowReasonText = computed(() => {
  const reason = askFlowDecision.value?.reason || ''
  const map = {
    basic_selected: '当前选择基础流程。',
    advanced_disabled: '进阶流程总开关关闭，已回落基础流程。',
    advanced_role_denied: '当前角色不在进阶流程灰度范围内。',
    advanced_selected: '当前会进入进阶流程。',
    advanced_error_fallback: '进阶流程异常时已回退基础流程。'
  }
  return map[reason] || reason || '尚未加载流程判断。'
})

const isAdvancedFlowSelected = computed(() => askFlowConfig.value.defaultFlow === 'advanced')
const askFlowRoleSummary = computed(() => {
  const labels = (askFlowConfig.value.advancedRoles || [])
    .map(role => roles.find(item => item.value === role)?.label || role)
    .filter(Boolean)
  return labels.length ? labels.join('、') : '未选择'
})

const selectAskFlow = (flow) => {
  askFlowConfig.value.defaultFlow = flow === 'advanced' ? 'advanced' : 'basic'
}

const featureList = computed(() =>
  Object.entries(features.value || {})
    .map(([key, value]) => {
      value.key = key
      value.label = value.label || key
      value.description = value.description || ''
      value.module = value.module || (value.kind === 'navigation' ? 'navigation' : 'other')
      value.module_label = value.module_label || value.category || '其他'
      value.kind = value.kind || 'button'
      value.order = Number(value.order || 999)
      value.roles = Array.isArray(value.roles) ? value.roles : []
      value.enabled = value.roles.length > 0 && Boolean(value.enabled)
      value.risk = value.risk || ''
      return value
    })
    .sort((a, b) => a.order - b.order)
)

const navigationItems = computed(() => featureList.value.filter((item) => item.kind === 'navigation'))
const buttonItems = computed(() => featureList.value.filter((item) => item.kind === 'button'))
const fieldItems = computed(() => featureList.value.filter((item) => item.kind === 'field'))
const navigationEnabledCount = computed(() => navigationItems.value.filter((item) => item.enabled).length)
const enabledButtonCount = computed(() => buttonItems.value.filter((item) => item.enabled).length)
const enabledFieldCount = computed(() => fieldItems.value.filter((item) => item.enabled).length)
const highRiskCount = computed(() => buttonItems.value.filter((item) => item.risk === 'high').length)
const highRiskFieldCount = computed(() => fieldItems.value.filter((item) => ['high', 'medium'].includes(item.risk)).length)
const orgScopedDatasetCount = computed(() => dataPermissionRows.value.filter((item) => item.rule?.mode === 'org_tree').length)
const enabledDataPermissionEmployees = computed(() => dataPermissionEmployees.value.filter((item) => item.enabled !== false))
const dataPermissionTreeTypes = computed(() => dataPermissionOrganizationTrees.value?.tree_types || [])
const employeesWithOrgCount = computed(() => dataPermissionEmployees.value.filter((item) => (item.organization_node_ids || []).length > 0).length)
const dataPermissionNodeById = computed(() => new Map((dataPermissionOrganizationTrees.value?.nodes || []).map((node) => [node.id, node])))
const expandedNodeIdsCache = computed(() => {
  const nodes = dataPermissionOrganizationTrees.value?.nodes || []
  const nodeById = dataPermissionNodeById.value
  const cache = new Map()
  return (ids = [], treeTypeId = '') => {
    const selectedIds = (ids || []).filter(id => nodeById.has(id)).sort()
    const key = `${treeTypeId || '*'}::${selectedIds.join('|')}`
    if (cache.has(key)) return cache.get(key)
    const selected = new Set(selectedIds)
    if (!selected.size && !treeTypeId) {
      cache.set(key, [])
      return cache.get(key)
    }
    const result = []
    nodes.forEach((node) => {
      if (treeTypeId && node.tree_type_id !== treeTypeId) return
      const pathIds = Array.isArray(node.path_ids) ? node.path_ids : [node.id]
      if ((selected.size && (selected.has(node.id) || pathIds.some(id => selected.has(id)))) || (!selected.size && treeTypeId)) {
        result.push(node.id)
      }
    })
    const unique = uniqueList(result)
    cache.set(key, unique)
    return unique
  }
})
const moduleInfoMap = computed(() => {
  const map = new Map()
  for (const item of navigationItems.value) {
    map.set(item.key, {
      order: item.order,
      label: item.label,
      description: item.description,
      scopeLabel: '左侧导航模块'
    })
  }
  map.set('global_shell', {
    order: 5,
    label: '全局操作',
    description: '右上角账号菜单、左侧历史区等不属于单个页面的公共按钮。',
    scopeLabel: '全局区域'
  })
  return map
})

const permissionSectionRules = [
  { key: 'dataset-main', label: '数据集主操作', description: '创建、保存、删除、生成和补齐数据集。', match: /^dataset_(create|save|delete|prompt_generate|autofill)$/ },
  { key: 'dataset-question', label: '常见问题', description: '数据集常见问题的新增、编辑、删除。', match: /^dataset_question_/ },
  { key: 'dataset-regression', label: '标准题集', description: '回归题和标准问题维护。', match: /^dataset_regression_/ },
  { key: 'dataset-synonym', label: '路由词/别名', description: '路由词和业务别名维护。', match: /^dataset_synonym_/ },
  { key: 'dataset-lld', label: 'LLD 文档', description: 'LLD 文档新增、编辑、删除。', match: /^dataset_lld_/ },
  { key: 'dataset-dict', label: '数据字典', description: '字段字典维护和 DDL 提取字段。', match: /^dataset_dict_/ },
  { key: 'dataset-schema', label: 'DDL + 表关联', description: 'DDL、表结构、表关联和来源表导入。', match: /^dataset_(schema|relation|source_table)/ },
  { key: 'dataset-golden', label: 'Golden SQL', description: '训练实例和 Golden SQL 样例维护。', match: /^dataset_golden_/ },
  { key: 'dataset-prompt', label: 'Agent 提示片段', description: 'Agent 提示词片段维护。', match: /^dataset_prompt_(create|update|delete)$/ },
  { key: 'dataset-sql', label: 'SQL 调试台', description: '智能问数页 SQL 调试执行、复制和导出。', match: /^dataset_sql_preview_/ },
  { key: 'dataset-extcfg', label: '飞书/外部配置', description: '数据集外部配置维护。', match: /^dataset_extcfg_/ },
  { key: 'employee-account', label: '账号维护', description: '新增、编辑、启停、批量修改和删除账号。', match: /^employee_(create|update|status_update|bulk_update|delete)$/ },
  { key: 'employee-security', label: '账号安全', description: '密码重置等敏感账号操作。', match: /^employee_password_/ },
  { key: 'org-tree-type', label: '组织树类型', description: '组织树类型新增、编辑和删除。', match: /^organization_tree_type_/ },
  { key: 'org-tree-node', label: '组织节点', description: '组织节点新增、编辑和删除。', match: /^organization_tree_node_/ },
  { key: 'org-tree-import', label: '组织树导入', description: '导入预检和确认导入。', match: /^organization_tree_import_/ },
  { key: 'feishu-task', label: '同步任务', description: '同步任务新建、编辑和删除。', match: /^feishu_sync_(create|update|delete)$/ },
  { key: 'feishu-run', label: '同步执行', description: '立即同步、暂停和恢复。', match: /^feishu_sync_(start|pause|resume)$/ },
  { key: 'feishu-test', label: '测试与预览', description: '连接测试、链接解析和字段预览。', match: /^feishu_(connection_test|link_parse|schema_preview)$/ },
  { key: 'feishu-log', label: '同步日志', description: '查看、刷新和清空同步日志。', match: /^feishu_log_/ },
]

const sectionForFeature = (item) => {
  const matched = permissionSectionRules.find(rule => rule.match.test(item.key))
  if (matched) return matched
  return {
    key: item.category || item.module || 'other',
    label: item.category ? item.category.replace(/^按钮 · /, '') : (item.module_label || '其他功能'),
    description: item.module_label ? `${item.module_label}中的其他按钮。` : '未归入特定区域的按钮。'
  }
}

const buildPermissionSections = (items = []) => {
  const grouped = new Map()
  items.forEach((item) => {
    const section = sectionForFeature(item)
    item.subgroupLabel = section.label
    if (!grouped.has(section.key)) {
      grouped.set(section.key, { ...section, items: [] })
    }
    grouped.get(section.key).items.push(item)
  })
  return Array.from(grouped.values()).map(section => ({
    ...section,
    items: section.items.sort((a, b) => a.order - b.order),
    enabledCount: section.items.filter(item => item.enabled).length
  }))
}

const buttonGroups = computed(() => {
  const grouped = new Map()
  for (const item of buttonItems.value) {
    if (!grouped.has(item.module)) {
      grouped.set(item.module, { module: item.module, items: [] })
    }
    grouped.get(item.module).items.push(item)
  }
  return Array.from(grouped.values())
    .map((group) => {
      const info = moduleInfoMap.value.get(group.module) || {}
      const firstItem = group.items[0] || {}
      return {
        ...group,
        label: info.label || firstItem.module_label || '其他模块',
        description: info.description || `归属于 ${firstItem.module_label || '其他模块'} 的页面按钮。`,
        scopeLabel: info.scopeLabel || '页面模块',
        order: Number(info.order || Math.min(...group.items.map((item) => item.order || 999))),
        items: group.items.sort((a, b) => a.order - b.order),
        sections: buildPermissionSections(group.items),
        enabledCount: group.items.filter((item) => item.enabled).length,
        riskCount: group.items.filter((item) => item.risk === 'high').length
      }
    })
    .sort((a, b) => a.order - b.order)
})

const fieldGroups = computed(() => {
  const grouped = new Map()
  for (const item of fieldItems.value) {
    if (!grouped.has(item.module)) {
      grouped.set(item.module, { module: item.module, items: [] })
    }
    grouped.get(item.module).items.push(item)
  }
  return Array.from(grouped.values())
    .map((group) => {
      const info = moduleInfoMap.value.get(group.module) || {}
      const firstItem = group.items[0] || {}
      return {
        ...group,
        label: info.label || firstItem.module_label || '其他模块',
        description: info.description || `控制 ${firstItem.module_label || '页面'} 内字段是否显示。`,
        order: Number(info.order || Math.min(...group.items.map((item) => item.order || 999))),
        items: group.items.sort((a, b) => a.order - b.order),
        enabledCount: group.items.filter((item) => item.enabled).length,
        riskCount: group.items.filter((item) => ['high', 'medium'].includes(item.risk)).length
      }
    })
    .sort((a, b) => a.order - b.order)
})

const isModuleOpen = (module) => openModules.value.includes(module)
const toggleModule = (module) => {
  openModules.value = isModuleOpen(module)
    ? openModules.value.filter((item) => item !== module)
    : [...openModules.value, module]
}

const hasRole = (item, role) => Array.isArray(item.roles) && item.roles.includes(role)
const isFixedPermission = (item, role) => item.key === 'admin_console' && role === 'super_admin'

const setRole = (item, role, checked) => {
  if (isFixedPermission(item, role)) return
  const next = new Set(item.roles || [])
  if (checked) next.add(role)
  else next.delete(role)
  item.roles = roleOrder.filter((value) => next.has(value))
  item.enabled = item.roles.length > 0
}

const editableItems = (items, role) => items.filter((item) => !isFixedPermission(item, role))

const isRoleAllChecked = (items, role) => {
  const list = editableItems(items, role)
  return list.length > 0 && list.every((item) => hasRole(item, role))
}

const toggleRoleAll = (items, role, checked) => {
  editableItems(items, role).forEach((item) => setRole(item, role, checked))
}

const loadFlags = async () => {
  loading.value = true
  try {
    const res = await getAdminFeatureFlags()
    features.value = structuredClone(res?.data?.features || {})
  } catch (error) {
    showRequestError(error, '控制台配置加载失败')
  } finally {
    loading.value = false
  }
}

const buildPayload = () => {
  const payload = {}
  for (const item of featureList.value) {
    payload[item.key] = {
      enabled: item.roles.length > 0,
      roles: item.roles,
      experimental: item.experimental
    }
  }
  return payload
}

const handleSave = async () => {
  if (!featureList.value.length) {
    ElMessage.warning('暂无可保存的权限配置，请先刷新控制台')
    return
  }
  saving.value = true
  try {
    const res = await saveAdminFeatureFlags(buildPayload())
    features.value = structuredClone(res?.data?.features || {})
    window.dispatchEvent(new CustomEvent(FEATURE_FLAGS_UPDATED_EVENT, { detail: { source: 'admin-console', at: Date.now() } }))
    ElMessage.success('控制台配置已保存')
  } catch (error) {
    showRequestError(error, '控制台配置保存失败')
  } finally {
    saving.value = false
  }
}

const handleReset = async () => {
  await ElMessageBox.confirm('将恢复系统默认权限矩阵，当前自定义勾选会被覆盖。确认继续吗？', '恢复默认', {
    type: 'warning',
    confirmButtonText: '恢复默认',
    cancelButtonText: '取消'
  })
  resetting.value = true
  try {
    const res = await resetAdminFeatureFlags()
    features.value = structuredClone(res?.data?.features || {})
    window.dispatchEvent(new CustomEvent(FEATURE_FLAGS_UPDATED_EVENT, { detail: { source: 'admin-console-reset', at: Date.now() } }))
    ElMessage.success('已恢复默认权限矩阵')
  } catch (error) {
    showRequestError(error, '恢复默认权限失败')
  } finally {
    resetting.value = false
  }
}

const applyAskFlowConfig = (config = {}, decision = {}) => {
  const policies = config.datasetPolicies && typeof config.datasetPolicies === 'object' ? { ...config.datasetPolicies } : {}
  askFlowConfig.value = {
    defaultFlow: config.defaultFlow || 'basic',
    advancedEnabled: Boolean(config.advancedEnabled),
    advancedRoles: Array.isArray(config.advancedRoles) && config.advancedRoles.length ? [...config.advancedRoles] : ['super_admin'],
    datasetPolicies: policies,
    fallbackToBasicOnError: config.fallbackToBasicOnError !== false,
    attachMetadata: config.attachMetadata !== false,
  }
  askFlowDecision.value = decision || {}
  askFlowDatasetPolicyRows.value = Object.entries(policies).map(([datasetId, flow], index) => ({
    key: `${datasetId}-${index}-${Date.now()}`,
    datasetId,
    flow: flow === 'advanced' ? 'advanced' : 'basic',
  }))
}

const loadAskFlowConfig = async () => {
  askFlowLoading.value = true
  try {
    const res = await getAskFlowConfig()
    applyAskFlowConfig(res?.data?.config || {}, res?.data?.effectiveDecision || {})
  } catch (error) {
    showRequestError(error, '问数流程配置加载失败')
  } finally {
    askFlowLoading.value = false
  }
}

const buildAskFlowPayload = () => {
  const flow = askFlowConfig.value.defaultFlow === 'advanced' ? 'advanced' : 'basic'
  const datasetPolicies = {}
  for (const row of askFlowDatasetPolicyRows.value) {
    const datasetId = String(row.datasetId || '').trim()
    if (!datasetId) continue
    if (!/^\d+$/.test(datasetId)) throw new Error(`数据集 ID 只能填写数字：${datasetId}`)
    datasetPolicies[String(Number(datasetId))] = row.flow === 'advanced' ? 'advanced' : 'basic'
  }
  const hasAdvancedPolicy = Object.values(datasetPolicies).includes('advanced')
  return {
    defaultFlow: flow,
    advancedEnabled: flow === 'advanced' || hasAdvancedPolicy,
    advancedRoles: askFlowConfig.value.advancedRoles?.length ? askFlowConfig.value.advancedRoles : ['super_admin'],
    datasetPolicies,
    fallbackToBasicOnError: askFlowConfig.value.fallbackToBasicOnError !== false,
    attachMetadata: askFlowConfig.value.attachMetadata !== false,
  }
}

const addAskFlowDatasetPolicy = () => {
  askFlowDatasetPolicyRows.value.push({
    key: `new-${Date.now()}-${Math.random()}`,
    datasetId: '',
    flow: 'advanced',
  })
}

const removeAskFlowDatasetPolicy = (index) => {
  askFlowDatasetPolicyRows.value.splice(index, 1)
}

const handleAskFlowSave = async () => {
  askFlowSaving.value = true
  try {
    const res = await saveAskFlowConfig(buildAskFlowPayload())
    applyAskFlowConfig(res?.data?.config || {}, res?.data?.effectiveDecision || {})
    ElMessage.success('问数流程配置已保存')
  } catch (error) {
    if (error instanceof Error && !error.response) ElMessage.error(error.message)
    else showRequestError(error, '问数流程配置保存失败')
  } finally {
    askFlowSaving.value = false
  }
}

const handleAskFlowReset = async () => {
  await ElMessageBox.confirm('将恢复问数流程控制器默认配置：默认基础流程、关闭进阶流程。确认继续吗？', '恢复默认', {
    type: 'warning',
    confirmButtonText: '恢复默认',
    cancelButtonText: '取消'
  })
  askFlowResetting.value = true
  try {
    const res = await resetAskFlowConfig()
    applyAskFlowConfig(res?.data?.config || {}, res?.data?.effectiveDecision || {})
    ElMessage.success('问数流程配置已恢复默认')
  } catch (error) {
    showRequestError(error, '问数流程配置恢复失败')
  } finally {
    askFlowResetting.value = false
  }
}

const showRequestError = (error, fallback) => {
  const message = error?.response?.data?.error || error?.message || fallback
  ElMessage.error(message)
}

const clonePlain = (value) => JSON.parse(JSON.stringify(value ?? null))
const uniqueList = (items = []) => Array.from(new Set((items || []).filter(Boolean)))
const mapDatasetTreeOptions = (items = []) => items.map((node) => ({
  id: node.id,
  label: `${node.name}（${node.code}）`,
  children: mapDatasetTreeOptions(node.children || []),
}))
const selectedTreeTypeIds = (rule = {}) => Array.isArray(rule.tree_type_ids)
  ? rule.tree_type_ids
  : (rule.tree_type_id ? [rule.tree_type_id] : [])
const treeTypeName = (id) => dataPermissionTreeTypes.value.find(item => item.id === id)?.name || id
const dataRuleTreeLabels = (rule = {}) => selectedTreeTypeIds(rule).map(treeTypeName).filter(Boolean)
const dataRuleOrgLabels = (rule = {}) => (rule.organization_node_ids || [])
  .map(id => dataPermissionNodeById.value.get(id))
  .filter(Boolean)
  .map(node => `${node.name}（${node.code}）`)
const roleLabel = (role) => roles.find(item => item.value === role)?.label || role || '普通用户'
const dataModeLabel = (mode) => ({ public: '公开', org_tree: '组织树', disabled: '停用', restricted: '组织树' }[mode] || '公开')
const dataModeTagType = (mode) => ({ public: 'success', org_tree: 'primary', disabled: 'danger', restricted: 'primary' }[mode] || 'info')
const datasetOrganizationOptions = (treeTypeIds = []) => {
  const ids = Array.isArray(treeTypeIds) ? treeTypeIds : (treeTypeIds ? [treeTypeIds] : [])
  if (!ids.length) return []
  return ids.map((treeTypeId) => {
    const tree = dataPermissionTreeTypes.value.find(item => item.id === treeTypeId)
    return {
      id: `tree:${treeTypeId}`,
      label: tree?.name || treeTypeId,
      disabled: true,
      children: mapDatasetTreeOptions((dataPermissionOrganizationTrees.value?.trees || {})[treeTypeId] || []),
    }
  })
}
const expandDataPermissionNodeIds = (ids = [], treeTypeId = '') => {
  return expandedNodeIdsCache.value(ids, treeTypeId)
}
const organizationCodesFromDataNodeIds = (ids = [], treeTypeId = '') => expandDataPermissionNodeIds(ids, treeTypeId)
  .map(id => dataPermissionNodeById.value.get(id)?.code)
  .filter(Boolean)
const onDataRuleTreeChange = (row) => {
  row.rule.tree_type_id = selectedTreeTypeIds(row.rule)[0] || ''
  row.rule.organization_node_ids = []
  row.rule.organization_codes = []
}
const currentTreeTypeIdFromDataRule = (rule = {}) => {
  const selectedNode = (rule.organization_node_ids || [])
    .map(id => dataPermissionNodeById.value.get(id))
    .find(Boolean)
  if (selectedNode?.tree_type_id) return selectedNode.tree_type_id
  const ids = selectedTreeTypeIds(rule)
  return ids.length === 1 ? ids[0] : ''
}
const selectDataRuleCurrentTree = (row) => {
  const treeTypeId = currentTreeTypeIdFromDataRule(row.rule)
  if (row.rule.mode !== 'org_tree' || !treeTypeId) {
    ElMessage.warning('请先选择一个组织树类型，或在下方点选该组织树里的任意节点')
    return
  }
  const otherTreeNodeIds = (row.rule.organization_node_ids || []).filter((id) => dataPermissionNodeById.value.get(id)?.tree_type_id !== treeTypeId)
  row.rule.organization_node_ids = uniqueList([...otherTreeNodeIds, ...expandDataPermissionNodeIds([], treeTypeId)])
  row.rule.organization_codes = organizationCodesFromDataNodeIds(row.rule.organization_node_ids)
}
const completeDataRuleChildren = (row) => {
  if (!(row.rule.organization_node_ids || []).length) {
    ElMessage.warning('请先选择一个或多个组织节点')
    return
  }
  row.rule.organization_node_ids = expandDataPermissionNodeIds(row.rule.organization_node_ids)
  row.rule.organization_codes = organizationCodesFromDataNodeIds(row.rule.organization_node_ids)
}
const clearDataRuleOrganizations = (row) => {
  row.rule.organization_node_ids = []
  row.rule.organization_codes = []
}

const normalizeRule = (dataset, rule = {}) => ({
  dataset_id: Number(dataset.id || rule.dataset_id || 0),
  mode: ['public', 'org_tree', 'disabled', 'restricted'].includes(rule.mode) ? (rule.mode === 'restricted' ? 'org_tree' : rule.mode) : 'public',
  tree_type_id: (Array.isArray(rule.tree_type_ids) ? rule.tree_type_ids[0] : rule.tree_type_id) || '',
  tree_type_ids: Array.isArray(rule.tree_type_ids)
    ? rule.tree_type_ids
    : (rule.tree_type_id ? [rule.tree_type_id] : []),
  organization_node_ids: Array.isArray(rule.organization_node_ids) ? rule.organization_node_ids : [],
  organization_codes: Array.isArray(rule.organization_codes) ? rule.organization_codes : [],
  allowed_roles: [],
  allowed_departments: [],
  allowed_positions: [],
  allowed_employee_ids: [],
  allowed_union_ids: [],
  scope: {
    organization_field: rule.scope?.organization_field || '组织编码',
    organization_values: Array.isArray(rule.scope?.organization_values) ? rule.scope.organization_values : [],
    company_field: rule.scope?.company_field || '',
    company_values: Array.isArray(rule.scope?.company_values) ? rule.scope.company_values : [],
    row_filter_note: rule.scope?.row_filter_note || '',
  },
  note: rule.note || '',
})

const openDataRuleEditor = (row) => {
  dataRuleForm.value = clonePlain({
    ...row,
    rule: normalizeRule(row, row.rule),
  })
  dataRuleDialog.value.visible = true
}

const applyDataRuleEditor = () => {
  if (!dataRuleForm.value) return
  const edited = clonePlain(dataRuleForm.value)
  edited.rule = normalizeRule(edited, edited.rule)
  edited.rule.tree_type_id = selectedTreeTypeIds(edited.rule)[0] || ''
  edited.rule.organization_codes = organizationCodesFromDataNodeIds(edited.rule.organization_node_ids)
  edited.rule.scope.organization_field = '组织编码'
  dataPermissionRows.value = dataPermissionRows.value.map((row) => (
    row.id === edited.id ? { ...row, rule: edited.rule } : row
  ))
  dataRuleDialog.value.visible = false
  ElMessage.success('已应用，记得点击顶部保存数据集权限')
}

const loadDataPermissions = async () => {
  dataPermissionLoading.value = true
  try {
    const res = await getDataPermissions()
    const datasets = Array.isArray(res?.datasets) ? res.datasets : []
    const rules = res?.rules || {}
    dataPermissionEmployees.value = Array.isArray(res?.employees) ? res.employees : []
    dataPermissionOrganizationTrees.value = res?.organization_trees || { tree_types: [], nodes: [], trees: {} }
    dataPermissionRows.value = datasets.map((dataset) => ({
      ...dataset,
      rule: normalizeRule(dataset, rules[String(dataset.id)] || {}),
    }))
  } catch (error) {
    showRequestError(error, '数据集权限加载失败')
  } finally {
    dataPermissionLoading.value = false
  }
}

const ensureDataPermissionsLoaded = () => {
  if (!dataPermissionRows.value.length) loadDataPermissions()
}

const saveDataPermissionRules = async () => {
  dataPermissionSaving.value = true
  try {
    const rules = {}
    dataPermissionRows.value.forEach((row) => {
      const rule = normalizeRule(row, row.rule)
      rule.tree_type_id = selectedTreeTypeIds(rule)[0] || ''
      rule.organization_codes = organizationCodesFromDataNodeIds(rule.organization_node_ids)
      rule.scope.organization_field = '组织编码'
      rules[String(row.id)] = rule
    })
    const res = await saveDataPermissions(rules)
    const savedRules = res?.rules || rules
    dataPermissionRows.value = dataPermissionRows.value.map((row) => ({
      ...row,
      rule: normalizeRule(row, savedRules[String(row.id)] || row.rule),
    }))
    ElMessage.success('数据集权限已保存')
  } catch (error) {
    showRequestError(error, '数据集权限保存失败')
  } finally {
    dataPermissionSaving.value = false
  }
}

const employeeOptionLabel = (item) => {
  const parts = [item.name || item.account || item.id]
  if (item.department) parts.push(item.department)
  if (item.position) parts.push(item.position)
  return parts.join(' / ')
}

const nodeDisplayLabel = (nodeId) => {
  const node = dataPermissionNodeById.value.get(nodeId)
  if (!node) return ''
  return `${node.name}（${node.code}）`
}

const employeeOrgLabels = (employee = {}) => uniqueList(
  expandDataPermissionNodeIds(employee.organization_node_ids || [])
    .map(nodeDisplayLabel)
    .filter(Boolean)
)

const employeeMatchedOrgLabels = (employee = {}, ruleScopes = []) => {
  const directNodeIds = uniqueList(employee.organization_node_ids || [])
  const directMatches = []
  directNodeIds.forEach((nodeId) => {
    const matchesRule = ruleScopes.some(({ treeTypeId, nodeIds }) => (
      expandDataPermissionNodeIds([nodeId], treeTypeId).some(expandedId => nodeIds.has(expandedId))
    ))
    if (matchesRule) directMatches.push(nodeId)
  })
  const labels = uniqueList(directMatches.map(nodeDisplayLabel).filter(Boolean))
  if (labels.length) return labels

  const matchedNodeIds = []
  ruleScopes.forEach(({ treeTypeId, nodeIds }) => {
    expandDataPermissionNodeIds(directNodeIds, treeTypeId).forEach((nodeId) => {
      if (nodeIds.has(nodeId)) matchedNodeIds.push(nodeId)
    })
  })
  return uniqueList(matchedNodeIds.map(nodeDisplayLabel).filter(Boolean))
}

const buildScopedEmployeeMatcher = (rule = {}) => {
  const mode = rule?.mode || 'public'
  if (mode === 'disabled') return () => null
  if (mode === 'public') {
    return (employee = {}) => {
      if (employee?.enabled === false || employee?.role === 'super_admin') return null
      return {
        match_reason: '公开数据集',
        match_labels: employeeOrgLabels(employee),
      }
    }
  }

  const treeTypeIds = selectedTreeTypeIds(rule)
  if (!treeTypeIds.length || !(rule?.organization_node_ids || []).length) return () => null
  const ruleScopes = treeTypeIds
    .map((treeTypeId) => ({
      treeTypeId,
      nodeIds: new Set(expandDataPermissionNodeIds(rule.organization_node_ids, treeTypeId)),
    }))
    .filter(item => item.nodeIds.size)
  if (!ruleScopes.length) return () => null

  return (employee = {}) => {
    if (employee?.enabled === false || employee?.role === 'super_admin') return null
    const matchLabels = employeeMatchedOrgLabels(employee, ruleScopes)
    if (!matchLabels.length) return null
    return {
      match_reason: '组织树命中',
      match_labels: matchLabels,
    }
  }
}

const scopedEmployeeMatch = (employee, rule = {}) => {
  if (employee?.enabled === false) return null
  if (employee?.role === 'super_admin') return null
  const mode = rule?.mode || 'public'
  if (mode === 'disabled') return null
  if (mode === 'public') {
    return {
      match_reason: '公开数据集',
      match_labels: employeeOrgLabels(employee),
    }
  }
  const treeTypeIds = selectedTreeTypeIds(rule)
  if (!treeTypeIds.length || !(rule?.organization_node_ids || []).length) return null
  const ruleScopes = treeTypeIds
    .map((treeTypeId) => ({
      treeTypeId,
      nodeIds: new Set(expandDataPermissionNodeIds(rule.organization_node_ids, treeTypeId)),
    }))
    .filter(item => item.nodeIds.size)
  const matchLabels = employeeMatchedOrgLabels(employee, ruleScopes)
  if (!matchLabels.length) return null
  return {
    match_reason: '组织树命中',
    match_labels: matchLabels,
  }
}

const computeScopedEmployeesForRule = (rule) => {
  const matchEmployee = buildScopedEmployeeMatcher(rule)
  return enabledDataPermissionEmployees.value
    .map((employee) => {
      const match = matchEmployee(employee)
      return match ? { ...employee, ...match } : null
    })
    .filter(Boolean)
}

const scopedEmployeesByDatasetId = computed(() => {
  const map = new Map()
  dataPermissionRows.value.forEach((row) => {
    const datasetId = String(row?.id || row?.rule?.dataset_id || '')
    if (!datasetId) return
    map.set(datasetId, computeScopedEmployeesForRule(row.rule))
  })
  return map
})

const scopedEmployeesForRule = (rule) => {
  const datasetId = String(rule?.dataset_id || '')
  return scopedEmployeesByDatasetId.value.get(datasetId) || computeScopedEmployeesForRule(rule)
}

const scopedEmployeeCount = (rule) => scopedEmployeesForRule(rule).length

const dataPermissionDisplayRows = computed(() => dataPermissionRows.value.map((row) => {
  const datasetId = String(row?.id || row?.rule?.dataset_id || '')
  const scopedEmployees = scopedEmployeesByDatasetId.value.get(datasetId) || []
  return {
    ...row,
    _display: {
      treeLabels: dataRuleTreeLabels(row.rule),
      orgLabels: dataRuleOrgLabels(row.rule),
      scopedEmployeeCount: scopedEmployees.length,
    },
  }
}))

const openScopedEmployeePreview = (row) => {
  scopedEmployeeDrawer.value = {
    visible: true,
    row,
    keyword: '',
  }
}

const scopedEmployeesInDrawer = computed(() => scopedEmployeeDrawer.value.row
  ? scopedEmployeesForRule(scopedEmployeeDrawer.value.row.rule)
  : []
)

const filteredScopedEmployees = computed(() => {
  const keyword = String(scopedEmployeeDrawer.value.keyword || '').trim().toLowerCase()
  if (!keyword) return scopedEmployeesInDrawer.value
  return scopedEmployeesInDrawer.value.filter((employee) => [
    employee.name,
    employee.account,
    employee.mobile,
    employee.email,
    employee.department,
    employee.position,
    roleLabel(employee.role),
    ...(employee.match_labels || []),
  ].some(value => String(value || '').toLowerCase().includes(keyword)))
})

const syncAdminFloatState = () => {
  adminFloatEnabled.value = sessionStorage.getItem(ADMIN_CONSOLE_FLOAT_HIDDEN_KEY) === '0'
}

const adminConsoleRouteForQuery = (query = {}) => {
  const search = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (item !== undefined && item !== null && item !== '') search.append(key, String(item))
      })
    } else {
      search.set(key, String(value))
    }
  })
  const queryString = search.toString()
  return `/admin-console${queryString ? `?${queryString}` : ''}`
}

const persistAdminConsoleLocation = (query = {}) => {
  const tab = consoleTabs.includes(String(query.tab || activeConsoleTab.value))
    ? String(query.tab || activeConsoleTab.value)
    : 'dashboard'
  const nextQuery = { ...query, tab }
  const target = adminConsoleRouteForQuery(nextQuery)
  sessionStorage.setItem(ADMIN_CONSOLE_LAST_ROUTE_KEY, target)
  localStorage.setItem(ADMIN_CONSOLE_LAST_ROUTE_KEY, target)
  return nextQuery
}

const syncAdminConsoleRoute = async (query = {}) => {
  const nextQuery = persistAdminConsoleLocation(query)
  await router.replace({ query: nextQuery }).catch(() => {})
}

const switchConsoleTab = async (tab) => {
  if (!consoleTabs.includes(tab)) return
  activeConsoleTab.value = tab
  const keepQuery = tab === 'logs' ? {
    tab,
    category: logFilters.value.category || undefined,
    level: logFilters.value.level || undefined,
    keyword: logFilters.value.keyword || undefined,
    trace_id: logFilters.value.trace_id || undefined,
    ...dateRangeParams(logFilters.value.date_range),
  } : { tab }
  await syncAdminConsoleRoute(keepQuery)
  if (tab === 'dashboard') loadDashboardData()
  else if (tab === 'ask-flow') loadAskFlowConfig()
  else if (tab === 'data') ensureDataPermissionsLoaded()
  else if (tab === 'logs') ensureLogsLoaded()
}

const toggleAdminFloat = () => {
  const nextVisible = !adminFloatEnabled.value
  adminFloatEnabled.value = nextVisible
  sessionStorage.setItem(ADMIN_CONSOLE_FLOAT_HIDDEN_KEY, nextVisible ? '0' : '1')
  window.dispatchEvent(new CustomEvent(ADMIN_CONSOLE_FLOAT_TOGGLE_EVENT, { detail: { visible: nextVisible } }))
  ElMessage.success(nextVisible ? '已开启悬浮控制台入口' : '已关闭悬浮控制台入口')
}

const normalizeLogDate = (value) => {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

const dateRangeParams = (range) => {
  const values = Array.isArray(range) ? range : []
  if (values.length !== 2 || !values[0] || !values[1]) return {}
  return { date_from: values[0], date_to: values[1] }
}

const dashboardStatsParams = computed(() => dateRangeParams(dashboardDateRange.value))

const dashboardRangeLabel = computed(() => {
  const range = dashboardDateRange.value || []
  if (range.length !== 2 || !range[0] || !range[1]) return '今日'
  return range[0] === range[1] ? range[0] : `${range[0]} 至 ${range[1]}`
})

const setDashboardToday = () => {
  dashboardDateRange.value = [todayDateValue, todayDateValue]
  loadDashboardData()
}

const setDashboardLast7Days = () => {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - 6)
  dashboardDateRange.value = [formatDateValue(start), formatDateValue(end)]
  loadDashboardData()
}

const filterLogsByDateRange = (items) => {
  const range = Array.isArray(logFilters.value.date_range) ? logFilters.value.date_range : []
  if (range.length !== 2 || !range[0] || !range[1]) return items
  const start = normalizeLogDate(`${range[0]}T00:00:00`)
  const end = normalizeLogDate(`${range[1]}T23:59:59`)
  if (!start || !end) return items
  return items.filter((item) => {
    const current = normalizeLogDate(item?.created_at)
    return current && current >= start && current <= end
  })
}

const refreshLogTable = () => {
  const filtered = filterLogsByDateRange(allFetchedLogs.value)
  totalLogs.value = filtered.length
  const start = (logPage.value - 1) * logPageSize.value
  logs.value = filtered.slice(start, start + logPageSize.value)
}

const loadLogStats = async (params = dashboardStatsParams.value) => {
  try {
    const res = await getSystemLogStats(params)
    logStats.value = res?.stats || {}
  } catch (error) {
    showRequestError(error, '日志统计加载失败')
  }
}

const loadLogs = async () => {
  logLoading.value = true
  logPage.value = 1
  try {
    const res = await getSystemLogs({
      category: logFilters.value.category || undefined,
      level: logFilters.value.level || undefined,
      keyword: logFilters.value.keyword || undefined,
      trace_id: logFilters.value.trace_id || undefined,
      ...dateRangeParams(logFilters.value.date_range),
      limit: 'all',
      offset: 0,
    })
    allFetchedLogs.value = Array.isArray(res?.logs) ? res.logs : []
    refreshLogTable()
  } catch (error) {
    showRequestError(error, '系统日志加载失败')
  } finally {
    logLoading.value = false
  }
}

const loadDashboardData = async () => {
  dashboardLoading.value = true
  try {
    await loadLogStats(dashboardStatsParams.value)
  } finally {
    dashboardLoading.value = false
  }
}

const recentLowConfidenceLogs = computed(() => (
  Array.isArray(logStats.value.recent_low_confidence) ? logStats.value.recent_low_confidence : []
))

const recentErrorLogs = computed(() => (
  Array.isArray(logStats.value.recent_errors) ? logStats.value.recent_errors : []
))

const formatNumber = (value) => Number(value || 0).toLocaleString('zh-CN')
const userRankName = (row = {}) => row.display_name || row.user_name || row.username || '未知用户'
const topUsersByAccess = computed(() => Array.isArray(logStats.value.top_users_by_access) ? logStats.value.top_users_by_access : [])
const topUsersByTokens = computed(() => Array.isArray(logStats.value.top_users_by_tokens) ? logStats.value.top_users_by_tokens : [])
const topUsersByErrors = computed(() => Array.isArray(logStats.value.top_users_by_errors) ? logStats.value.top_users_by_errors : [])
const topUsersByLowConfidence = computed(() => Array.isArray(logStats.value.top_users_by_low_confidence) ? logStats.value.top_users_by_low_confidence : [])
const dashboardUserRankPanels = computed(() => [
  {
    key: 'access',
    kicker: '异常用户',
    title: '访问最多',
    metricLabel: '访问数',
    metricKey: 'access_count',
    tone: 'primary',
    rows: topUsersByAccess.value,
    emptyText: '暂无访问用户',
    filter: {},
  },
  {
    key: 'tokens',
    kicker: '资源用量',
    title: 'Token 最高',
    metricLabel: 'Token',
    metricKey: 'total_tokens',
    tone: 'success',
    rows: topUsersByTokens.value,
    emptyText: '暂无 token 用量',
    filter: { category: 'qa_all' },
  },
  {
    key: 'errors',
    kicker: '异常排查',
    title: '错误最多',
    metricLabel: '错误数',
    metricKey: 'error_count',
    tone: 'danger',
    rows: topUsersByErrors.value,
    emptyText: '暂无错误用户',
    filter: { category: 'error' },
  },
  {
    key: 'low_confidence',
    kicker: '口径治理',
    title: '低置信度最多',
    metricLabel: '问题数',
    metricKey: 'low_confidence_count',
    tone: 'warning',
    rows: topUsersByLowConfidence.value,
    emptyText: '暂无低置信度用户',
    filter: { category: 'low_confidence' },
  },
])

const dashboardCards = computed(() => [
  {
    key: 'range_access',
    label: '访问数',
    value: formatNumber(logStats.value.range_access || logStats.value.today_access || 0),
    hint: `${dashboardRangeLabel.value}，点击查看访问日志`,
    tone: 'info',
    filter: { category: 'access' },
  },
  {
    key: 'range_qa',
    label: '问数次数',
    value: formatNumber(logStats.value.range_qa || logStats.value.today_qa || 0),
    hint: `${dashboardRangeLabel.value}，点击查看问数日志`,
    tone: 'primary',
    filter: { category: 'qa_all' },
  },
  {
    key: 'range_tokens',
    label: 'Token 用量',
    value: formatNumber(logStats.value.range_tokens || logStats.value.today_tokens || 0),
    hint: `${dashboardRangeLabel.value}，基于日志用量字段汇总`,
    tone: 'success',
    filter: { category: 'qa_all' },
  },
  {
    key: 'range_errors',
    label: '错误数',
    value: formatNumber(logStats.value.range_errors || logStats.value.today_errors || 0),
    hint: `${dashboardRangeLabel.value}，点击查看错误日志`,
    tone: 'danger',
    filter: { category: 'error' },
  },
  {
    key: 'range_low_confidence',
    label: '低置信度',
    value: formatNumber(logStats.value.range_low_confidence || logStats.value.today_low_confidence || 0),
    hint: `${dashboardRangeLabel.value}，点击查看低置信度问题`,
    tone: 'warning',
    filter: { category: 'low_confidence' },
  },
])

const traceIdFromLog = (row = {}) => {
  const details = eventDetails(row)
  return details.trace_id
    || details.conversation_session_id
    || details.confirmation_session_id
    || details.session_id
    || ''
}

const openLogsFromDashboard = async (filter = {}) => {
  const rangeParams = dashboardStatsParams.value
  activeConsoleTab.value = 'logs'
  logFilters.value.category = filter.category || ''
  logFilters.value.level = filter.level || ''
  logFilters.value.keyword = filter.keyword || ''
  logFilters.value.trace_id = filter.trace_id || ''
  logFilters.value.date_range = rangeParams.date_from && rangeParams.date_to ? [rangeParams.date_from, rangeParams.date_to] : []
  logPage.value = 1
  await syncAdminConsoleRoute({ tab: 'logs', ...filter, ...rangeParams })
  await loadLogData()
}

const jumpToUserLogs = (row = {}, filter = {}) => {
  const keyword = row.username || row.user_name || row.display_name || ''
  return openLogsFromDashboard({ ...filter, keyword })
}

const jumpToLog = async (row) => {
  const traceId = traceIdFromLog(row)
  await openLogsFromDashboard({
    category: row?.category || '',
    level: row?.level === 'error' ? 'error' : '',
    trace_id: traceId,
    keyword: traceId ? '' : (row?.question || row?.error_message || row?.title || ''),
  })
  openLogDetail(row)
}

const exportFilteredLogs = async () => {
  logExporting.value = true
  try {
    const filtered = filterLogsByDateRange(allFetchedLogs.value)
    if (!filtered.length) {
      ElMessage.warning('当前筛选结果为空，暂无可导出的日志')
      return
    }
    const header = ['时间', '类型', '级别', '事件名称', '用户', '发生了什么', '建议', '请求路径', '问题', 'SQL', '答案', '错误']
    const escapeCell = (value) => `"${String(value ?? '').replace(/"/g, '""').replace(/\r?\n/g, ' ')}"`
    const rows = filtered.map((row) => ([
      formatTime(row.created_at),
      categoryLabel(row.category),
      row.level || '',
      eventName(row),
      row.user_name || row.username || '',
      whatHappened(row),
      actionSuggestion(row),
      row.request_path || '',
      row.question || '',
      row.sql_text || '',
      row.answer_text || '',
      row.error_message || '',
    ].map(escapeCell).join(',')))
    const csv = ['\ufeff' + header.join(','), ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `system-logs-${Date.now()}.csv`
    link.click()
    URL.revokeObjectURL(link.href)
    ElMessage.success(`已导出 ${filtered.length} 条日志`)
  } finally {
    logExporting.value = false
  }
}

const loadLogData = async () => {
  logLoading.value = true
  try {
    await Promise.all([loadLogStats(dateRangeParams(logFilters.value.date_range)), loadLogs()])
  } finally {
    logLoading.value = false
  }
}

const ensureLogsLoaded = () => {
  if (!logs.value.length) loadLogData()
}

const onLogPageChange = (page) => {
  logPage.value = page
  refreshLogTable()
}

const onLogPageSizeChange = (size) => {
  logPageSize.value = size
  logPage.value = 1
  refreshLogTable()
}

const openLogDetail = async (row) => {
  selectedLog.value = row
  logDetailVisible.value = true
  try {
    const res = await getSystemLogDetail(row.id)
    selectedLog.value = res?.log || row
  } catch (error) {
    showRequestError(error, '日志详情加载失败')
  }
}

const handleClearLogs = async () => {
  const range = Array.isArray(logFilters.value.date_range) ? logFilters.value.date_range : []
  const beforeDate = range[1] || ''
  if (!beforeDate) {
    ElMessage.warning('请先选择查询日期范围')
    return
  }
  const categoryText = logFilters.value.category ? `，日志类型为「${categoryLabel(logFilters.value.category)}」` : ''
  await ElMessageBox.confirm(`将清理 ${beforeDate} 及之前${categoryText}的系统日志。确认继续吗？`, '清理系统日志', {
    type: 'warning',
    confirmButtonText: '清理',
    cancelButtonText: '取消',
  })
  logClearing.value = true
  try {
    const res = await clearSystemLogs({
      category: logFilters.value.category,
      before_date: beforeDate,
    })
    ElMessage.success(`已清理 ${res?.deleted || 0} 条日志`)
    await loadLogData()
  } catch (error) {
    showRequestError(error, '清理系统日志失败')
  } finally {
    logClearing.value = false
  }
}

const categoryLabel = (category) => ({
  auth: '登录访问',
  access: '接口访问',
  error: '报错',
  low_confidence: '低置信',
  qa: '问答',
  dataset_generation: '数据集生成',
}[category] || category || '-')

const categoryTagType = (category) => ({
  auth: 'success',
  access: 'info',
  error: 'danger',
  low_confidence: 'warning',
  qa: 'primary',
  dataset_generation: 'warning',
}[category] || 'info')

const levelTagType = (level) => ({
  info: 'info',
  warning: 'warning',
  error: 'danger',
}[level] || 'info')

const eventTypeLabel = (eventType) => ({
  api_access: '接口访问',
  http_error: '接口报错',
  password_login_success: '密码登录成功',
  password_login_failed: '密码登录失败',
  admin_login_success: '管理员登录成功',
  admin_login_failed: '管理员登录失败',
  feishu_login_success: '飞书登录成功',
  feishu_login_failed: '飞书登录失败',
  logout: '退出登录',
  smart_chat_completed: '问答完成',
  smart_chat_low_confidence: '低置信问答',
  smart_chat_failed: '问答报错',
  dataset_generate_from_prompt_started: '开始提示词生成数据集',
  dataset_generate_from_prompt_completed: '提示词生成数据集完成',
  dataset_generate_from_prompt_failed: 'AI 生成数据集失败',
  dataset_generate_from_prompt_error: '提示词生成接口异常',
}[eventType] || eventType || '-')

const eventDetails = (row) => (row && typeof row.details === 'object' && row.details ? row.details : {})

const eventName = (row) => eventDetails(row).event_name || row?.title || eventTypeLabel(row?.event_type)

const whatHappened = (row) => (
  eventDetails(row).what_happened
  || row?.question
  || row?.error_message
  || row?.request_path
  || row?.title
  || '-'
)

const actionSuggestion = (row) => {
  const details = eventDetails(row)
  if (details.suggested_action) return details.suggested_action
  if (row?.category === 'low_confidence') return '建议把这条问题补进回归题集或 Golden SQL，并检查字段字典、同义词和 Agent2 SQL 生成提示词。'
  if (row?.category === 'error') return '建议先看详细错误和请求路径，再到对应 controller 搜索接口路径定位代码。'
  if (row?.category === 'auth') return '建议核对登录账号、角色和权限矩阵配置。'
  return '无需处理；这是正常访问记录。'
}

const codeHint = (row) => {
  const details = eventDetails(row)
  if (details.code_hint) return details.code_hint
  if (row?.request_path?.includes('/smart-chat')) return 'backend/controllers/smart_chat.py；backend/four_agent_ask.py；frontend/src/views/SmartAsk.vue。'
  if (row?.request_path?.includes('/bookshelves')) return 'backend/controllers/bookshelf.py；frontend/src/views/DatasetManagement.vue。'
  if (row?.request_path?.includes('/admin/system-logs')) return 'backend/controllers/system_logs.py；backend/system_log_store.py；frontend/src/views/AdminConsole.vue。'
  return 'backend/controllers/*.py 中搜索请求路径；frontend/src/api/index.js 中搜索对应 API 方法。'
}

const confidenceLabel = (confidence) => {
  const route = confidence?.route
  const result = confidence?.result
  const parts = []
  if (route?.score !== undefined) parts.push(`路由${route.score}`)
  if (result?.score !== undefined) parts.push(`结果${result.score}`)
  return parts.join(' / ') || '-'
}

const formatTime = (value) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('zh-CN', { hour12: false })
}

const thinkingRows = (item) => Array.isArray(item?.thinking_process) ? item.thinking_process : []
const timelineType = (status) => status === 'error' ? 'danger' : status === 'warning' ? 'warning' : status === 'success' ? 'success' : 'primary'
const prettyJson = (value) => {
  try { return JSON.stringify(value || {}, null, 2) } catch { return String(value || '') }
}

onMounted(() => {
  syncAdminFloatState()
  const savedRoute = localStorage.getItem(ADMIN_CONSOLE_LAST_ROUTE_KEY) || sessionStorage.getItem(ADMIN_CONSOLE_LAST_ROUTE_KEY) || ''
  let savedQuery = {}
  if (!route.query?.tab && savedRoute.startsWith('/admin-console')) {
    try {
      savedQuery = Object.fromEntries(new URL(savedRoute, window.location.origin).searchParams.entries())
    } catch {
      savedQuery = {}
    }
  }
  const initialQuery = route.query?.tab ? route.query : savedQuery
  const tab = String(initialQuery?.tab || '')
  if (consoleTabs.includes(tab)) {
    activeConsoleTab.value = tab
  }
  const queryDateRange = initialQuery?.date_from && initialQuery?.date_to
    ? [String(initialQuery.date_from), String(initialQuery.date_to)]
    : []
  if (queryDateRange.length === 2) {
    dashboardDateRange.value = queryDateRange
  }
  persistAdminConsoleLocation({ ...initialQuery, tab: activeConsoleTab.value })
  if (activeConsoleTab.value === 'logs') {
    logFilters.value.category = String(initialQuery?.category || '')
    logFilters.value.level = String(initialQuery?.level || '')
    logFilters.value.keyword = String(initialQuery?.keyword || '')
    logFilters.value.trace_id = String(initialQuery?.trace_id || '')
    logFilters.value.date_range = queryDateRange
    loadLogData()
  } else if (activeConsoleTab.value === 'dashboard') {
    loadDashboardData()
  } else if (activeConsoleTab.value === 'ask-flow') {
    loadAskFlowConfig()
  }
  loadFlags()
})
</script>

<style scoped>
.console-page {
  min-height: 100%;
  padding: 24px 28px 36px;
  color: #1f2937;
  background:
    radial-gradient(circle at 8% 6%, rgba(24, 144, 255, 0.12), transparent 28%),
    linear-gradient(135deg, #f6f9ff 0%, #f4f7fb 54%, #edf4ff 100%);
}

.ask-flow-panel { display: flex; flex-direction: column; gap: 16px; }

.ask-flow-overview {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 20px;
  padding: 22px;
  border: 1px solid #c7d2fe;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(255,255,255,0.96), rgba(239,246,255,0.9));
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.07);
}

.ask-flow-overview-copy h2 { margin: 6px 0 8px; font-size: 24px; color: #0f172a; }
.ask-flow-overview-copy p { margin: 0; max-width: 680px; color: #475569; line-height: 1.75; }

.ask-flow-overview-status {
  min-width: 220px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.ask-flow-overview-status strong { display: block; font-size: 22px; color: #111827; }
.ask-flow-overview-status span { display: block; margin: 8px 0 12px; color: #64748b; line-height: 1.6; }

.flow-choice-shell,
.ask-flow-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.045);
}

.flow-choice-shell { padding: 18px; }

.flow-section-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.flow-section-head > span {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 999px;
  background: #2563eb;
  color: #fff;
  font-weight: 800;
}

.flow-section-head strong { display: block; color: #111827; font-size: 17px; }
.flow-section-head small { display: block; margin-top: 3px; color: #64748b; }

.flow-choice-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }

.flow-choice-card {
  position: relative;
  display: flex;
  min-height: 150px;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  padding: 18px;
  text-align: left;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: #f8fafc;
  cursor: pointer;
  transition: border-color .16s ease, background .16s ease, box-shadow .16s ease;
}

.flow-choice-card:hover {
  border-color: #93c5fd;
  background: #ffffff;
}

.flow-choice-card.active {
  border-color: #2563eb;
  background: #eff6ff;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.10);
}

.flow-choice-card strong { font-size: 22px; color: #0f172a; }
.flow-choice-card small { color: #475569; line-height: 1.65; }
.flow-choice-card i { margin-top: auto; font-style: normal; color: #2563eb; font-weight: 700; }

.flow-choice-tag {
  padding: 3px 8px;
  border-radius: 999px;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 700;
}

.ask-flow-card {
  padding: 18px;
}

.ask-flow-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

.ask-flow-card h3 { margin: 6px 0 0; font-size: 17px; color: #111827; }
.ask-flow-card-head small { color: #94a3b8; line-height: 1.6; }

.flow-muted { margin: 10px 0 0; color: #64748b; font-size: 13px; line-height: 1.7; }

.flow-settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.flow-setting-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 4px 12px;
  align-items: center;
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}

.flow-setting-item > span { font-weight: 700; color: #111827; }
.flow-setting-item > small { grid-column: 1 / 2; color: #64748b; line-height: 1.55; }
.flow-setting-item :deep(.el-switch) { grid-row: 1 / 3; grid-column: 2; }
.flow-setting-item.is-wide { grid-template-columns: 1fr; grid-column: 1 / -1; }
.flow-setting-item.is-wide small { grid-column: auto; }

.flow-role-checks {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-top: 8px;
}

.flow-collapsed-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.flow-collapsed-summary span {
  padding: 6px 10px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  font-size: 13px;
}

.flow-dataset-policy p {
  margin: 0 0 12px;
  color: #64748b;
}

.flow-dataset-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 180px auto;
  gap: 10px;
  margin-bottom: 10px;
}

.ask-flow-actions {
  position: sticky;
  bottom: 14px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.10);
}

@media (max-width: 1080px) {
  .flow-choice-grid,
  .flow-settings-grid {
    grid-template-columns: 1fr;
  }
  .ask-flow-overview {
    flex-direction: column;
  }
  .flow-role-checks,
  .flow-dataset-row {
    grid-template-columns: 1fr;
  }
}

.console-page > * {
  max-width: 1440px;
  margin-left: auto;
  margin-right: auto;
}

.console-hero,
.summary-strip,
.permission-card,
.module-card {
  border: 1px solid rgba(203, 213, 225, 0.82);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.08);
}

.console-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 22px;
}

.hero-kicker,
.card-kicker {
  display: inline-flex;
  margin-bottom: 5px;
  color: #1677ff;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.06em;
}

.console-hero h1,
.card-head h2,
.module-title h2 {
  margin: 0;
  color: #0f172a;
  font-size: 22px;
  line-height: 1.25;
}

.console-hero h1 {
  font-size: 30px;
  letter-spacing: -0.02em;
}

.console-hero p,
.card-head p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 13px;
}

.hero-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.console-floating-save {
  position: fixed;
  right: 34px;
  bottom: 28px;
  z-index: 30;
  padding: 8px;
  border: 1px solid rgba(15, 118, 110, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.16);
  backdrop-filter: blur(12px);
}

.console-floating-save :deep(.el-button) {
  min-width: 118px;
  height: 38px;
  border-radius: 999px;
  box-shadow: 0 10px 22px rgba(15, 118, 110, 0.22);
}

.summary-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.dashboard-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  padding: 14px 16px;
  border: 1px solid rgba(203, 213, 225, 0.82);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
}

.dashboard-toolbar strong {
  display: block;
  margin-top: 3px;
  color: #0f172a;
  font-size: 16px;
}

.dashboard-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.dashboard-card {
  min-height: 112px;
  padding: 16px;
  border: 1px solid rgba(203, 213, 225, 0.82);
  border-radius: 14px;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
}

.dashboard-card span,
.dashboard-card small {
  display: block;
  color: #64748b;
  font-size: 12px;
}

.dashboard-card strong {
  display: block;
  margin: 8px 0 6px;
  color: #0f172a;
  font-size: 28px;
  line-height: 1;
}

.dashboard-card.is-danger strong {
  color: #dc2626;
}

.dashboard-card.is-warning strong {
  color: #d97706;
}

.dashboard-card.is-success strong {
  color: #059669;
}

.dashboard-card.is-primary strong {
  color: #1677ff;
}

.dashboard-panels {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.dashboard-rank-panels {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.dashboard-rank-panel {
  padding: 14px;
}

.dashboard-panel {
  padding: 16px;
  border: 1px solid rgba(203, 213, 225, 0.82);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.06);
}

.dashboard-panel header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.dashboard-panel h2 {
  margin: 0;
  color: #0f172a;
  font-size: 18px;
}

.dashboard-table :deep(.el-table__cell) {
  padding: 7px 0;
}

.dashboard-user-cell {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.dashboard-user-cell strong {
  overflow: hidden;
  color: #0f172a;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dashboard-user-cell small {
  color: #64748b;
  font-size: 12px;
}

.rank-metric {
  color: #0f172a;
  font-size: 14px;
}

.rank-metric.is-primary {
  color: #1677ff;
}

.rank-metric.is-success {
  color: #059669;
}

.rank-metric.is-danger {
  color: #dc2626;
}

.rank-metric.is-warning {
  color: #d97706;
}

.summary-strip div {
  padding: 13px 16px;
  border: 1px solid rgba(203, 213, 225, 0.76);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
}

.summary-strip strong {
  display: block;
  color: #0f766e;
  font-size: 21px;
  line-height: 1.1;
}

.summary-strip span {
  color: #64748b;
  font-size: 12px;
}

.console-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 14px;
  padding: 8px;
  border: 1px solid rgba(203, 213, 225, 0.82);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
}

.console-tabs button {
  min-width: 0;
  height: 42px;
  border: 0;
  border-radius: 10px;
  color: #475569;
  background: transparent;
  font-weight: 800;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.16s ease;
}

.console-tabs button.active {
  color: #ffffff;
  background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
  box-shadow: 0 10px 20px rgba(15, 118, 110, 0.22);
}

.console-command-layout {
  display: block;
  margin-top: 16px;
}

.console-command-main {
  min-width: 0;
}

.console-command-main > .summary-strip:first-child,
.console-command-main > .log-summary-strip:first-child {
  margin-top: 0;
}

.permission-card {
  margin-top: 16px;
  overflow: hidden;
}

.card-head,
.module-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px;
  border-bottom: 1px solid #edf2f7;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
}

.card-head em,
.module-title em,
.module-head-stats i,
.module-head-stats span {
  color: #64748b;
  font-size: 12px;
  font-style: normal;
  font-weight: 700;
}

.matrix-table {
  padding: 10px 14px 14px;
  overflow-x: auto;
}

.matrix-row {
  display: grid;
  grid-template-columns: minmax(320px, 1fr) repeat(4, minmax(122px, 138px));
  align-items: center;
  min-width: 760px;
  min-height: 48px;
  border-bottom: 1px solid #eef2f7;
}

.matrix-row:last-child {
  border-bottom: 0;
}

.matrix-head {
  min-height: 40px;
  margin-bottom: 4px;
  border: 0;
  border-radius: 10px;
  background: #f4f7fb;
  color: #475569;
}

.feature-col {
  min-width: 0;
  padding: 8px 12px;
}

.feature-col strong {
  display: inline-flex;
  align-items: center;
  color: #0f172a;
  font-size: 14px;
  font-weight: 800;
}

.feature-col small {
  display: block;
  margin-top: 3px;
  color: #718096;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.feature-col b {
  margin-left: 8px;
  padding: 2px 7px;
  border-radius: 999px;
  color: #dc2626;
  background: #fee2e2;
  font-size: 11px;
}

.role-head,
.permission-check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.role-head {
  gap: 5px;
  color: #334155;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  position: relative;
  white-space: nowrap;
}

.role-name {
  min-width: 0;
  text-align: left;
  white-space: nowrap;
}

.role-head small {
  padding: 1px 6px;
  border-radius: 999px;
  color: #64748b;
  background: #eef2f7;
  font-weight: 700;
  white-space: nowrap;
}

.role-head.checked small {
  color: #0f766e;
  background: #dff7f1;
}

.role-head input,
.permission-check input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.check-box {
  width: 17px;
  height: 17px;
  border: 1px solid #cbd5e1;
  border-radius: 5px;
  background: #fff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.role-head.checked .check-box,
.permission-check.checked .check-box {
  border-color: #0f766e;
  background: #0f766e;
  box-shadow: inset 0 0 0 3px #0f766e;
}

.role-head.checked .check-box::after,
.permission-check.checked .check-box::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 8px;
  height: 4px;
  border-left: 2px solid #fff;
  border-bottom: 2px solid #fff;
  transform: translate(-50%, -70%) rotate(-45deg);
}

.permission-check {
  position: relative;
  min-height: 34px;
  cursor: pointer;
}

.permission-check .check-box,
.role-head .check-box {
  position: relative;
  flex-shrink: 0;
}

.permission-check.disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.is-risk {
  background: linear-gradient(90deg, rgba(254, 242, 242, 0.78), transparent 52%);
}

.module-section {
  margin-top: 18px;
}

.module-title {
  padding: 0 2px 12px;
  border-bottom: 0;
  background: transparent;
}

.module-card {
  margin-bottom: 12px;
  overflow: hidden;
}

.module-card-head {
  width: 100%;
  min-height: 64px;
  padding: 0 18px;
  border: 0;
  border-bottom: 1px solid transparent;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  cursor: pointer;
  color: inherit;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
  user-select: none;
  text-align: left;
}

.module-card-head::before {
  content: '';
  width: 8px;
  height: 8px;
  border-right: 2px solid #64748b;
  border-bottom: 2px solid #64748b;
  flex-shrink: 0;
  transform: rotate(-45deg);
  transition: transform 0.18s ease;
}

.module-card.is-open .module-card-head::before {
  transform: rotate(45deg);
}

.module-permission-body {
  padding: 12px;
}

.permission-section {
  border: 1px solid #edf2f7;
  border-radius: 14px;
  background: #fff;
  overflow: hidden;
}

.permission-section + .permission-section {
  margin-top: 12px;
}

.permission-section-head {
  min-height: 48px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: #f8fafc;
  border-bottom: 1px solid #edf2f7;
}

.permission-section-head span {
  display: block;
  color: #0f172a;
  font-size: 13px;
  font-weight: 900;
}

.permission-section-head small {
  display: block;
  margin-top: 2px;
  color: #64748b;
  font-size: 12px;
}

.permission-section-head em {
  flex-shrink: 0;
  padding: 3px 8px;
  border-radius: 999px;
  background: #eafaf6;
  color: #0f766e;
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
}

.feature-tag {
  display: inline-flex;
  align-items: center;
  margin: 0 8px 3px 0;
  padding: 2px 7px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 11px;
  font-weight: 800;
  vertical-align: middle;
}

.module-head-copy {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 4px 10px;
}

.module-card-head strong {
  color: #0f172a;
  font-size: 15px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.module-head-copy small {
  grid-column: 1 / -1;
  color: #7b8798;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.45;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.module-scope {
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  color: #165dff;
  background: #edf4ff;
  font-size: 11px;
  font-weight: 800;
}

.module-head-stats {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.module-card.is-open .module-card-head {
  border-bottom: 1px solid #edf2f7;
}

.compact {
  padding-top: 6px;
}

.log-summary-strip strong {
  color: #7c3aed;
}

.data-summary-strip strong {
  color: #0f766e;
}

.data-permission-card {
  margin-top: 16px;
  padding: 14px;
  border: 1px solid rgba(203, 213, 225, 0.82);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
}

.data-permission-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 2px 2px 14px;
}

.data-permission-toolbar h2 {
  margin: 0;
  color: #0f172a;
  font-size: 18px;
}

.data-permission-toolbar p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 12px;
}

.data-permission-table small,
.data-permission-table strong {
  display: block;
}

.data-permission-table small {
  margin-top: 3px;
  color: #64748b;
  font-size: 12px;
}

.data-permission-table :deep(.el-table__cell) {
  vertical-align: top;
}

.data-permission-table :deep(.el-select),
.data-permission-table :deep(.el-input) {
  width: 100%;
}

.scope-fields {
  display: grid;
  grid-template-columns: minmax(88px, 0.8fr) minmax(130px, 1.2fr);
  gap: 8px;
}

.dataset-org-scope {
  display: grid;
  gap: 8px;
}

.log-card {
  margin-top: 16px;
  padding: 14px;
  border: 1px solid rgba(203, 213, 225, 0.82);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
}

.log-toolbar {
  display: grid;
  grid-template-columns: auto auto auto minmax(240px, 1fr) auto auto;
  gap: 10px;
  margin-bottom: 12px;
}

.log-table {
  width: 100%;
}

.log-pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 12px;
  color: #64748b;
  font-size: 12px;
}

.log-detail {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.detail-grid div {
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
}

.detail-grid span {
  display: block;
  color: #64748b;
  font-size: 12px;
}

.detail-grid strong {
  display: block;
  margin-top: 4px;
  color: #0f172a;
  font-size: 14px;
}

.detail-section {
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
}

.detail-highlight {
  border-color: #bfdbfe;
  background: #eff6ff;
}

.detail-section h3 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 15px;
}

.detail-section p {
  margin: 0 0 6px;
  color: #334155;
  line-height: 1.6;
}

.detail-section pre {
  max-height: 360px;
  margin: 0;
  padding: 10px;
  overflow: auto;
  border-radius: 8px;
  color: #1e293b;
  background: #f8fafc;
  font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.console-page {
  background: #f5f7fb;
}

.console-page > * {
  max-width: 1280px;
}

.console-hero {
  padding: 18px 22px;
  border-radius: 16px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(246, 250, 255, 0.96)),
    radial-gradient(circle at 0 0, rgba(22, 93, 255, 0.1), transparent 34%);
}

.console-hero h1 {
  font-size: 26px;
}

.summary-strip {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.summary-strip div {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 12px;
}

.summary-strip strong {
  display: inline;
  font-size: 19px;
}

.permission-card,
.module-card {
  border-radius: 14px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
}

.matrix-table {
  padding: 8px 14px 12px;
}

.matrix-row {
  grid-template-columns: minmax(340px, 1fr) repeat(4, minmax(128px, 144px));
  min-width: 852px;
  min-height: 50px;
}

.matrix-head {
  position: sticky;
  top: 0;
  z-index: 2;
  margin-bottom: 2px;
  background: #eef4ff;
}

.feature-col {
  padding: 9px 12px;
}

.feature-col strong {
  font-size: 13px;
  line-height: 1.35;
}

.feature-col small {
  margin-top: 2px;
  font-size: 11px;
  color: #7b8798;
  white-space: normal;
  line-height: 1.45;
}

.role-head {
  width: fit-content;
  min-width: 108px;
  height: 28px;
  margin: 0 auto;
  padding: 0 8px;
  border: 1px solid #d8e3f5;
  border-radius: 999px;
  background: #fff;
}

.role-head.checked {
  border-color: rgba(15, 118, 110, 0.24);
  background: #eefaf7;
}

.role-head small {
  padding: 0;
  background: transparent;
  color: #7b8798;
}

.permission-check {
  width: 100%;
}

.module-card-head {
  min-height: 58px;
  background: #fff;
}

.module-head-stats span {
  padding: 2px 8px;
  border-radius: 999px;
  background: #f1f5f9;
}

.module-head-stats i {
  min-width: 74px;
  text-align: right;
}

.scope-summary {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
  color: #64748b;
}

.scope-summary-button {
  border: 0;
  padding: 0;
  background: transparent;
  cursor: pointer;
}

.scope-summary-button:hover strong {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.scope-summary strong {
  color: #0f766e;
  font-size: 18px;
}

.scoped-employee-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
}

.scoped-employee-dialog :deep(.el-dialog__body) {
  padding-top: 10px;
  max-height: calc(86vh - 72px);
  overflow: auto;
}

.scoped-employee-head {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.scoped-employee-head div {
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
}

.scoped-employee-head span,
.scoped-employee-head small,
.scoped-employee-table small {
  display: block;
  color: #64748b;
  font-size: 12px;
}

.scoped-employee-head strong,
.scoped-employee-table strong {
  display: block;
  color: #0f172a;
}

.scoped-employee-filter {
  max-width: 420px;
}

.scoped-employee-table small {
  margin-top: 3px;
}

.scoped-employee-table :deep(.el-table__cell) {
  vertical-align: top;
}

.scoped-employee-table .dataset-scope-tags {
  gap: 5px;
}

.scoped-employee-table .dataset-scope-tags .el-tag {
  max-width: 170px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.scoped-employee-note {
  margin: 0;
  color: #64748b;
  font-size: 12px;
}

@media (max-width: 900px) {
  .console-page {
    padding: 14px;
  }

  .console-hero {
    flex-direction: column;
    align-items: stretch;
  }

  .summary-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .dashboard-toolbar-actions {
    justify-content: flex-start;
  }

  .dashboard-grid,
  .dashboard-panels,
  .dashboard-rank-panels {
    grid-template-columns: 1fr;
  }

  .log-toolbar {
    grid-template-columns: 1fr;
  }

  .detail-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .matrix-row {
    grid-template-columns: minmax(220px, 1fr) repeat(4, 112px);
    min-width: 668px;
  }

  .console-floating-save {
    right: 16px;
    bottom: 16px;
  }
}
</style>

<style>
.tree-select-panel-actions {
  display: grid;
  grid-template-columns: minmax(150px, 1fr) repeat(4, auto);
  gap: 6px;
  padding: 8px;
  border-bottom: 1px solid #eef2f7;
  background: #f8fafc;
}

.tree-select-panel-actions.compact-actions {
  grid-template-columns: repeat(3, auto);
  justify-content: start;
}

.tree-select-panel-actions .el-button {
  margin-left: 0;
}

@media (max-width: 720px) {
  .tree-select-panel-actions,
  .tree-select-panel-actions.compact-actions {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
