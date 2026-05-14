<template>
  <div class="sa-page">
    <div class="sa-shell">
      <section class="sa-workspace" :class="{ 'is-detail-hidden': !detailPanelVisible }">
        <!-- 📌 左侧/中间 对话区-->
        <div class="sa-chat-panel" :class="{ 'is-detail-hidden': !detailPanelVisible }">
          <!-- 头部组件-->
          <ChatHeader
            :show-panel="detailPanelVisible"
            :dataset-name="currentDatasetLabel"
            :allow-toggle-panel="isFeatureEnabled('debug_execution_trace')"
            :allow-new-chat="isFeatureEnabled('smart_new_chat')"
            @toggle-panel="togglePanel"
            @new-chat="handleNewChat"
            @show-history="focusSidebarHistory"
          />

          <!-- 会话滚动区-->
          <div class="sa-chat-body" ref="chatBodyRef">
            <!-- 欢迎首屏 -->
            <WelcomeScreen
              v-if="messages.length === 0"
              :common-questions="commonQuestions"
              :common-questions-loading="commonQuestionsLoading"
              @quick-ask="quickAsk"
              @refresh-questions="refreshCommonQuestions"
            />

            <!-- 消息列表 -->
            <div class="sa-msg-list">
              <div v-for="msg in messages" :key="msg.id" class="sa-msg-wrap">
                <!-- 用户气泡 -->
                <UserBubble
                  v-if="msg.role === 'user'"
                  :content="msg.content"
                  :disabled="isRunning"
                  @copy="copyQuestion(msg)"
                  @edit="editQuestion(msg)"
                  @rerun="rerunQuestion(msg)"
                />

                <!-- AI 回复 -->
                <div v-else class="sa-ai-wrap">
                  <div class="sa-ai-meta">
                    <div class="sa-ai-avatar">DA</div>
                    <span class="sa-ai-name">经营分析顾问</span>
                  </div>
                  <div class="sa-ai-cards">
                    <!-- 加载中-->
                    <div v-if="msg.loading && !session.state.logs.length" class="sa-thinking-loading">
                      <div class="sa-dots">
                        <span></span><span></span><span></span>
                      </div>
                      <span class="sa-thinking-text">正在分析问题意图并规划路径...</span>
                    </div>

                    <!-- 执行进度卡-->
                    <LiveExecutionFeed
                      v-if="shouldShowLiveFeed(msg)"
                      :logs="session.state.logs"
                      :mode="msg.loading ? 'live' : 'completed'"
                      :max-items="6"
                      :elapsed-label="getMessageElapsedLabel(msg)"
                    />
                    <PlanCard :route="msg.data?.route" />

                    <!-- 思考过程卡（可折叠）-->
                    <ThinkingCard
                      v-if="shouldShowThinkingCard(msg)"
                      :steps="getThinkingSteps(msg)"
                      :loading="msg.loading"
                      :is-open="thinkingOpen[msg.id]"
                      @toggle="toggleThinking(msg.id)"
                    />

                    <!-- 确认口径卡-->
                    <div v-if="shouldShowResultHandoff(msg)" class="sa-flow-handoff">
                      <div class="sa-flow-handoff-kicker">执行已完成</div>
                      <div class="sa-flow-handoff-title">正在整理结果摘要与报告内容</div>
                      <div class="sa-flow-handoff-desc">
                        执行轨迹已经沉淀完成，下面将继续承接结果摘要、报告内容和附件产物。                      </div>
                    </div>

                    <div v-if="shouldShowConfirmationCard(msg)" class="sa-card sa-confirm-card">
                      <div class="sa-card-head">
                        <span class="sa-confirm-icon">💡</span>
                        <span class="sa-card-tag sa-tag-orange">需要确认</span>
                      </div>
                      <p class="sa-confirm-q">{{ msg.data.confirmation_question }}</p>
                      <div class="sa-confirm-impact">
                        <div class="sa-confirm-impact-row">
                          <span class="sa-confirm-impact-label">确认范围</span>
                          <span class="sa-confirm-impact-value">{{ getConfirmationScopeSummary(msg) }}</span>
                        </div>
                        <div class="sa-confirm-impact-row">
                          <span class="sa-confirm-impact-label">候选数据集</span>
                          <div class="sa-confirm-impact-chips">
                            <span
                              v-for="name in getConfirmationCandidateNames(msg)"
                              :key="name"
                              class="sa-confirm-chip"
                            >
                              {{ name }}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div v-if="isFeatureEnabled('smart_confirm_scope')" class="sa-confirm-opts">
                        <button
                          v-for="opt in msg.data.confirmation_options"
                          :key="getConfirmOptionKey(opt)"
                          class="sa-confirm-btn"
                          :disabled="isRunning"
                          @click="doConfirm(opt, msg)"
                        >
                          <span class="sa-confirm-btn-label">{{ getConfirmOptionLabel(opt) }}</span>
                          <span v-if="getConfirmOptionDescription(opt)" class="sa-confirm-btn-desc">
                            {{ getConfirmOptionDescription(opt) }}
                          </span>
                          <span v-if="getConfirmOptionDatasetNames(opt).length" class="sa-confirm-btn-meta">
                            命中数据集：{{ getConfirmOptionDatasetNames(opt).join(' / ') }}
                          </span>
                          <span v-if="getConfirmOptionMemberNames(opt).length" class="sa-confirm-btn-meta">
                            成员范围：{{ getConfirmOptionMemberNames(opt).join(' / ') }}
                          </span>
                          <span class="sa-confirm-btn-impact">{{ getConfirmOptionImpact(opt) }}</span>
                        </button>
                      </div>
                      <div class="sa-confirm-freeform">
                        <div class="sa-confirm-freeform-head">如果这些卡片都不合适，可以继续补充说明</div>
                        <textarea
                          v-model="confirmationDrafts[msg.id]"
                          class="sa-confirm-textarea"
                          :disabled="isRunning"
                          placeholder="例如：这里的东部分公司指华东区域，先按分公司口径继续分析。"
                          @keydown.enter.exact.prevent="handleConfirmationDraftEnter($event, msg)"
                        ></textarea>
                        <div class="sa-confirm-freeform-actions">
                          <span class="sa-confirm-freeform-hint">补充说明会直接作为老板确认内容继续推进问数流程。</span>
                          <button
                            v-if="isFeatureEnabled('smart_submit_note')"
                            class="sa-confirm-send"
                            :disabled="isRunning || !String(confirmationDrafts[msg.id] || '').trim()"
                            @click="submitConfirmationDraft(msg)"
                          >
                            发送补充说明
                          </button>
                        </div>
                      </div>
                    </div>

                    <div v-else-if="shouldShowConfirmationSubmitted(msg)" class="sa-card sa-confirm-submitted">
                      <div class="sa-confirm-submitted-head">
                        <span class="sa-confirm-submitted-dot"></span>
                        <span class="sa-confirm-submitted-title">已提交确认，正在继续执行</span>
                      </div>
                      <div class="sa-confirm-submitted-desc">
                        系统已收到老板确认口径，正在继续生成 SQL 与后续分析结果。                      </div>
                    </div>

                    <div
                      v-if="shouldShowResultChain(msg)"
                      class="sa-result-chain"
                    >
                    <ResultDigestCard
                      v-if="getReport(msg) || getPrimaryDataset(msg)"
                      :title="getResultTitle(msg)"
                      :question="msg.data?.question || session.state.question"
                      :report="getReport(msg)"
                      :dataset="getPrimaryDataset(msg)"
                      :datasets="getDatasets(msg)"
                      :route="msg.data?.route || null"
                      @view-details="openDetailPanel"
                    />

                    <div
                      v-if="getVisualPreviews(msg).length"
                      class="sa-inline-visuals"
                      :class="{ 'is-single': getVisualPreviews(msg).length === 1 }"
                    >
                      <div class="sa-inline-visuals-head">
                        <div>
                          <div class="sa-inline-visuals-kicker">REPORT VISUALS</div>
                          <div class="sa-inline-visuals-title">关键图表预览</div>
                          <div class="sa-inline-visuals-caption">按当前结果自动提取关键图表，保留最值得先看的那几张。</div>
                        </div>
                      </div>

                      <div class="sa-inline-visuals-grid" :class="{ 'is-single': getVisualPreviews(msg).length === 1 }">
                        <div
                          v-for="preview in getVisualPreviews(msg)"
                          :key="`inline-${msg.id}-${preview.key}`"
                          class="sa-inline-visual-card"
                        >
                          <div class="sa-inline-visual-card-head">
                            <div>
                              <div class="sa-inline-visual-card-title">{{ preview.chartSpec?.title || preview.dataset.dataset_name }}</div>
                              <div class="sa-inline-visual-card-subtitle">{{ preview.dataset.dataset_name }}</div>
                            </div>
                            <button v-if="isFeatureEnabled('chart_viewer')" class="sa-ghost-btn" @click="openChartViewer(preview.chartSpec, `${preview.dataset.dataset_name} 图表预览`)">
                              放大查看
                            </button>
                          </div>

                          <div v-if="preview.chartSpec?.chartType === 'metric'" class="sa-insight-metric">
                            <div class="sa-insight-metric-value">{{ preview.chartSpec.value }}</div>
                            <div class="sa-insight-metric-label">{{ preview.chartSpec.label }}</div>
                          </div>
                          <div
                            v-else-if="preview.chartSpec"
                            class="sa-inline-visual-chart"
                            :ref="el => initPreviewChart(el, preview.chartSpec, `inline-${msg.id}-${preview.key}`)"
                          ></div>
                        </div>
                      </div>
                    </div>

                    <!-- 错误卡-->
                    </div>
                    <div v-if="msg.data?.error" class="sa-card sa-error-card">
                      <span>❌</span>
                      <span>{{ msg.data.error }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 状态条 -->
          <transition name="sa-slide-up">
            <div v-if="isRunning || session.state.status === 'completed'" class="sa-status-bar" :class="session.state.status">
              <div class="sa-status-left">
                <span class="sa-status-dot"></span>
                <span class="sa-status-text">{{ statusBarText }}</span>
              </div>
              <div class="sa-status-right">
                <span v-if="isRunning" class="sa-timer">{{ elapsed }}s</span>
              </div>
            </div>
          </transition>

          <!-- 底部输入区-->
          <ComposerArea
            v-model:query="query"
            v-model:dataset-id="datasetId"
            v-model:model-id="modelId"
            :datasets="datasets"
            :ai-models="aiModels"
            :is-running="isRunning"
            :allow-send="isFeatureEnabled('smart_send_question')"
            :allow-stop="isFeatureEnabled('smart_stop_run')"
            @send="handleSend"
            @stop="handleStop"
            @dataset-change="loadQuestions"
          />
        </div>

        <!-- ██ 右侧 执行详情面板 -->
        <transition name="sa-panel-slide">
          <aside v-if="detailPanelVisible" class="sa-detail-panel">
            <div class="sa-panel-header">
              <div class="sa-panel-heading">
                <span class="sa-panel-eyebrow">执行事件详情</span>
                <div class="sa-panel-title-row">
                  <span class="sa-panel-title">Data Agent 执行轨迹</span>
                  <span class="sa-panel-state" :class="session.state.status">{{ detailPanelState }}</span>
                </div>
                <p class="sa-panel-desc">{{ detailPanelDesc }}</p>
              </div>

              <button class="sa-panel-close" @click="showPanel = false">×</button>
            </div>

            <div class="sa-panel-content" ref="panelRef">
              <LogTimeline
                :key="timelineKey"
                :logs="session.state.logs"
                :open-state="logOpen"
                @toggle="toggleLog"
              >
                <template #content="{ log, index }">
                  <div v-if="log.sql" class="sa-log-section">
                    <div class="sa-log-section-title">{{ log.sqlTitle || '生成 SQL' }}</div>
                    <SqlBlock :sql="log.sql" :allow-copy="isFeatureEnabled('smart_sql_copy')" />
                  </div>

                  <div v-if="log.chartData" class="sa-log-section">
                    <div class="sa-log-section-title">{{ log.chartTitle || '图表预览' }}</div>
                    <button v-if="isFeatureEnabled('chart_viewer')" class="sa-ghost-btn sa-log-inline-action" @click="openChartViewer(log.chartData, log.chartTitle || '图表预览')">放大查看</button>
                    <div class="sa-chart-embed" :ref="el => initLogChart(el, log.chartData, index)"></div>
                  </div>

                  <div v-if="log.tableRows?.length" class="sa-log-section">
                    <div class="sa-log-section-title">{{ log.tableTitle || '结果预览' }}</div>
                    <div class="sa-mini-table-wrap">
                      <el-table :data="log.tableRows.slice(0, 5)" size="small" border class="sa-mini-table">
                        <el-table-column v-for="c in log.tableColumns" :key="c" :prop="c" :label="c" min-width="100" show-overflow-tooltip />
                      </el-table>
                      <div v-if="log.tableRows.length > 5" class="sa-table-more">共 {{ log.tableRows.length }} 行</div>
                    </div>
                  </div>

                  <div v-if="log.markdown && !(log.kind === 'report-stage' && hasSideReport)" class="sa-log-section">
                    <div class="sa-log-section-title">{{ log.kind === 'report-stage' ? '报告内容' : '节点摘要' }}</div>
                    <div class="sa-log-markdown" v-html="renderMd(log.markdown)"></div>
                  </div>

                </template>
              </LogTimeline>

              <section v-if="hasSideReport" ref="sideReportRef" class="sa-side-report">
                <div class="sa-side-report-head">
                  <div ref="sideReportHeadRef" class="sa-side-report-titlebar">
                    <div>
                      <h3 class="sa-side-report-title">业绩分析报告</h3>
                    </div>
                    <button v-if="isFeatureEnabled('report_fullscreen')" class="sa-primary-btn sa-side-fullscreen-btn" @click="openFullScreenReport">
                      <span class="sa-btn-label">全屏报告</span>
                    </button>
                  </div>
                  <div v-if="sideConfidenceBadges.length" class="sa-side-confidence" aria-label="路由与结果可信度">
                    <span
                      v-for="badge in sideConfidenceBadges"
                      :key="badge.label"
                      class="sa-side-confidence-chip"
                      :class="`is-${badge.tone}`"
                    >
                      {{ badge.label }}：{{ badge.value }}
                    </span>
                  </div>
                </div>

                <section
                  v-if="businessDrillReport"
                  class="sa-side-section sa-business-report"
                  :class="{ 'is-single-focus': businessDrillReport.isSingleFocus }"
                >
                  <div
                    v-if="businessNarrativeSections.length"
                    class="sa-management-narrative"
                    :class="{ 'is-single-focus': businessDrillReport.isSingleFocus }"
                  >
                    <article
                      v-for="section in businessNarrativeSections"
                      :key="section.title"
                      class="sa-management-narrative-card"
                    >
                      <div class="sa-management-narrative-title">{{ section.title }}</div>
                      <div class="sa-report-md sa-report-md-compact sa-management-narrative-body" v-html="renderReportMd(section.body)"></div>
                    </article>
                  </div>
                  <div class="sa-business-summary">
                    <div>
                      <div class="sa-side-section-title">核心业绩看板</div>
                      <p class="sa-business-summary-text">{{ businessDrillReport.summary }}</p>
                    </div>
                    <span class="sa-business-risk-pill" :class="businessDrillReport.riskTone">{{ businessDrillReport.riskLabel }}</span>
                  </div>
                  <div class="sa-kpi-shelf sa-kpi-shelf-compact">
                    <div
                      v-for="metric in sideBusinessMetricCards"
                      :key="`${metric.subject || 'metric'}-${metric.label}`"
                      class="sa-kpi-card"
                      :class="[
                        { 'is-subject-metric': metric.subject, 'is-explained': metric.hint },
                        metric.tone ? `is-tone-${metric.tone}` : ''
                      ]"
                      :style="metric.accentStyle"
                    >
                      <div v-if="metric.subject" class="sa-kpi-subject">{{ metric.subject }}</div>
                      <div class="sa-kpi-value">{{ metric.value }}</div>
                      <div class="sa-kpi-label">{{ metric.label }}</div>
                      <div v-if="metric.hint" class="sa-kpi-hint">{{ metric.hint }}</div>
                    </div>
                  </div>
                  <div v-if="businessDrillReport.officeCompareSpec" class="sa-office-overview-card">
                    <div class="sa-office-overview-head">
                      <div>
                        <div class="sa-side-section-title">各{{ businessDrillReport.compareLevelLabel }}对比分析</div>
                        <p class="sa-chart-copy">{{ businessDrillReport.officeCompareText }}</p>
                      </div>
                    </div>
                    <div class="sa-compare-matrix is-compact">
                      <div class="sa-compare-row is-head">
                        <span>{{ businessDrillReport.compareLevelLabel }}</span>
                        <span>总任务</span>
                        <span>已完成</span>
                        <span>缺口</span>
                        <span>达成率</span>
                        <span>进度</span>
                        <span>标签</span>
                      </div>
                      <button
                        v-for="(office, officeIndex) in businessDrillReport.offices"
                        :key="`side-compare-row-${office.id}`"
                        class="sa-compare-row"
                        :style="getOfficeAccentStyle(office, officeIndex)"
                        type="button"
                        @click="toggleOfficeDrill(office.id)"
                      >
                        <span class="sa-detail-name">{{ office.name }}</span>
                        <span>{{ getOfficeKpiLabel(office, 'task') }}</span>
                        <span>{{ getOfficeKpiLabel(office, 'actual') }}</span>
                        <span>{{ getOfficeKpiLabel(office, 'remain') }}</span>
                        <span class="sa-detail-rate" :class="office.tone">{{ office.rateLabel }}</span>
                        <span class="sa-detail-progress">
                          <i class="sa-office-bar-track"><b class="is-rate" :class="office.tone" :style="{ width: `${office.progress}%` }"></b></i>
                        </span>
                        <span class="sa-detail-tag" :class="office.tone">{{ office.tag }}</span>
                      </button>
                    </div>
                  </div>
                  <div class="sa-office-card-list">
                    <article
                      v-for="(office, officeIndex) in businessDrillReport.offices"
                      :key="`side-office-${office.id}`"
                      class="sa-office-card"
                      :style="getOfficeAccentStyle(office, officeIndex)"
                    >
                      <button
                        class="sa-office-card-head"
                        type="button"
                        :aria-expanded="String(isOfficeExpanded(office.id))"
                        @click="toggleOfficeDrill(office.id)"
                      >
                        <div class="sa-office-head-main">
                          <div class="sa-office-name">{{ office.name }} <span class="sa-office-tag">{{ office.tag }}</span></div>
                          <div class="sa-office-subtitle">{{ office.childCount }} 个{{ businessDrillReport.detailLevelLabel }} · {{ office.parentName || '当前口径' }}</div>
                        </div>
                        <span class="sa-office-head-actions">
                          <span class="sa-office-rate" :class="office.tone">{{ office.rateLabel }}<small v-if="office.rankLabel">{{ office.rankLabel }}</small></span>
                          <span
                            class="sa-office-drill-toggle"
                            :class="{ 'is-open': isOfficeExpanded(office.id) }"
                            :title="isOfficeExpanded(office.id) ? '收起下钻明细' : `展开查看${office.childCount || 0}个${businessDrillReport.detailLevelLabel}`"
                          >
                            <span>{{ isOfficeExpanded(office.id) ? '收起' : '下钻' }}</span>
                            <i></i>
                          </span>
                        </span>
                      </button>
                      <div class="sa-office-kpis">
                        <span v-for="item in office.kpis" :key="item.label">{{ item.label }} {{ item.value }}</span>
                      </div>
                      <p class="sa-office-copy">{{ office.summary }}</p>
                      <div v-if="isOfficeExpanded(office.id)" class="sa-office-drill">
                        <div class="sa-drill-path">
                          <span>{{ office.name }}</span>
                          <i></i>
                          <strong>{{ businessDrillReport.detailLevelLabel }}</strong>
                        </div>
                        <div class="sa-drill-insight-grid">
                          <div class="sa-drill-insight-card is-good">
                            <span>下钻亮点</span>
                            <strong>{{ getDrillBestText(office) }}</strong>
                          </div>
                          <div class="sa-drill-insight-card is-risk">
                            <span>重点压力</span>
                            <strong>{{ getDrillWorstText(office) }}</strong>
                          </div>
                        </div>
                        <p class="sa-chart-copy sa-chart-copy-drill">{{ office.chartText }}</p>
                        <div v-if="office.detailRows?.length" class="sa-office-detail-wrap">
                          <div class="sa-drill-table-head">
                            <span>{{ businessDrillReport.detailLevelLabel }}明细</span>
                            <small>按达成率排序，点击上层卡片可收起</small>
                          </div>
                          <div class="sa-office-detail-table">
                            <div class="sa-office-detail-row is-head">
                              <span>{{ businessDrillReport.detailLevelLabel }}</span>
                              <span>任务/已完成</span>
                              <span>剩余缺口</span>
                              <span>达成率</span>
                              <span>达成进度</span>
                              <span>标签</span>
                            </div>
                            <div v-for="person in office.detailRows" :key="`${office.id}-${person.name}`" class="sa-office-detail-row">
                              <span class="sa-detail-name">{{ person.name }}</span>
                              <span>{{ person.taskLabel }} / {{ person.actualLabel }}</span>
                              <span>{{ person.remainLabel }}</span>
                              <span class="sa-detail-rate" :class="person.tone">{{ person.rateLabel }}</span>
                              <span class="sa-detail-progress">
                                <i class="sa-office-bar-track"><b class="is-rate" :class="person.tone" :style="{ width: `${person.progress}%` }"></b></i>
                              </span>
                              <span class="sa-detail-tag" :class="person.tone">{{ person.label }}</span>
                            </div>
                          </div>
                          <div v-if="office.drillGroups?.length" class="sa-rep-drill-list">
                            <div class="sa-rep-drill-title">继续下钻到业务员</div>
                            <article
                              v-for="group in office.drillGroups"
                              :key="`${office.id}-${group.id}`"
                              class="sa-rep-drill-card"
                            >
                              <button
                                class="sa-rep-drill-head"
                                type="button"
                                @click="toggleOfficeDrill(`rep-${office.id}-${group.id}`)"
                              >
                                <div class="sa-office-head-main">
                                  <div class="sa-rep-drill-name">{{ group.name }} <span class="sa-office-tag">{{ group.tag }}</span></div>
                                  <div class="sa-rep-drill-subtitle">{{ group.childCount }} 个{{ group.detailLevelLabel }} · {{ group.parentName || office.name }}</div>
                                </div>
                                <span class="sa-office-head-actions">
                                  <span class="sa-office-rate" :class="group.tone">{{ group.rateLabel }}</span>
                                  <span
                                    class="sa-office-drill-toggle is-small"
                                    :class="{ 'is-open': isOfficeExpanded(`rep-${office.id}-${group.id}`) }"
                                    :title="isOfficeExpanded(`rep-${office.id}-${group.id}`) ? '收起业务员明细' : '展开业务员明细'"
                                  >
                                    <span>{{ isOfficeExpanded(`rep-${office.id}-${group.id}`) ? '收起' : '业务员' }}</span>
                                    <i></i>
                                  </span>
                                </span>
                              </button>
                              <p v-if="group.summary" class="sa-rep-drill-summary">{{ group.summary }}</p>
                              <div v-if="isOfficeExpanded(`rep-${office.id}-${group.id}`)" class="sa-office-detail-table sa-rep-person-table">
                                <div class="sa-office-detail-row is-head">
                                  <span>{{ group.detailLevelLabel }}</span>
                                  <span>任务/已完成</span>
                                  <span>剩余缺口</span>
                                  <span>达成率</span>
                                  <span>达成进度</span>
                                  <span>标签</span>
                                </div>
                                <div v-for="person in group.detailRows" :key="`${office.id}-${group.id}-${person.name}`" class="sa-office-detail-row">
                                  <span class="sa-detail-name">{{ person.name }}</span>
                                  <span>{{ person.taskLabel }} / {{ person.actualLabel }}</span>
                                  <span>{{ person.remainLabel }}</span>
                                  <span class="sa-detail-rate" :class="person.tone">{{ person.rateLabel }}</span>
                                  <span class="sa-detail-progress">
                                    <i class="sa-office-bar-track"><b class="is-rate" :class="person.tone" :style="{ width: `${person.progress}%` }"></b></i>
                                  </span>
                                  <span class="sa-detail-tag" :class="person.tone">{{ person.label }}</span>
                                </div>
                              </div>
                            </article>
                          </div>
                        </div>
                        <div v-else class="sa-office-empty-drill">
                          当前 SQL 结果未返回 {{ businessDrillReport.detailLevelLabel }} 明细。请重新问“{{ office.name }}下{{ businessDrillReport.detailLevelLabel }}业绩明细”或检查 SQL 是否包含下级层级。
                        </div>
                      </div>
                    </article>
                  </div>
                </section>

                <section v-if="!businessDrillReport && sideReportCharts.length" class="sa-side-section sa-side-chart-gallery">
                  <div class="sa-side-section-head">
                    <div>
                      <div class="sa-side-section-title">图表分析</div>
                      <div class="sa-side-dataset-name">按报告配置拆出的独立图表</div>
                    </div>
                  </div>
                  <div class="sa-side-chart-grid">
                    <article
                      v-for="chart in sideReportCharts"
                      :key="chart.key"
                      class="sa-side-extra-chart-card"
                    >
                      <div class="sa-side-extra-chart-head">
                        <div class="sa-side-extra-chart-title">{{ chart.chartSpec.title || chart.caption }}</div>
                        <button v-if="isFeatureEnabled('chart_viewer')" class="sa-ghost-btn sa-side-extra-chart-action" @click="openChartViewer(chart.chartSpec, `${chart.dataset.dataset_name} ${chart.chartSpec.title || chart.caption}`)">
                          查看
                        </button>
                      </div>
                      <div
                        v-if="chart.chartSpec.chartType === 'metric'"
                        class="sa-insight-metric sa-insight-metric-compact"
                      >
                        <div class="sa-insight-metric-value">{{ chart.chartSpec.value }}</div>
                        <div class="sa-insight-metric-label">{{ chart.chartSpec.label }}</div>
                      </div>
                      <div
                        v-else
                        class="sa-side-extra-chart-canvas"
                        :ref="el => initPreviewChart(el, chart.chartSpec, chart.key)"
                      ></div>
                    </article>
                  </div>
                </section>

                <div
                  v-if="!businessDrillReport"
                  v-for="preview in resultPreviews"
                  :key="preview.key"
                  class="sa-side-section"
                  :class="{ 'sa-preview': preview.dataset.rows?.length }"
                >
                  <div class="sa-side-section-head">
                    <div>
                      <div class="sa-side-section-title">{{ preview.caption }}</div>
                      <div class="sa-side-dataset-name">{{ preview.dataset.dataset_name }}</div>
                    </div>
                    <div class="sa-side-meta">
                      <span class="sa-side-meta-chip">{{ preview.dataset.rows?.length || 0 }} 行</span>
                      <span class="sa-side-meta-chip">{{ preview.dataset.columns?.length || 0 }} 列</span>
                    </div>
                  </div>

                  <div v-if="preview.metricCards.length" class="sa-kpi-shelf">
                    <div v-for="metric in preview.metricCards" :key="metric.label" class="sa-kpi-card">
                      <div class="sa-kpi-value">{{ metric.value }}</div>
                      <div class="sa-kpi-label">{{ metric.label }}</div>
                    </div>
                  </div>

                  <div v-if="preview.chartSpec?.chartType === 'metric' && !preview.extraCharts?.length" class="sa-insight-metric">
                    <div class="sa-insight-metric-value">{{ preview.chartSpec.value }}</div>
                    <div class="sa-insight-metric-label">{{ preview.chartSpec.label }}</div>
                  </div>

                  <div v-else-if="preview.chartSpec" class="sa-main-chart" :ref="el => initPreviewChart(el, preview.chartSpec, preview.key)"></div>
                  <div v-if="preview.chartSpec" class="sa-chart-actions">
                    <button v-if="isFeatureEnabled('chart_viewer')" class="sa-ghost-btn" @click="openChartViewer(preview.chartSpec, `${preview.dataset.dataset_name} 图表预览`)">放大查看</button>
                  </div>

                  <div v-if="preview.extraCharts?.length" class="sa-side-extra-charts">
                    <article
                      v-for="(chartSpec, chartIndex) in preview.extraCharts.slice(0, 2)"
                      :key="`${preview.key}-extra-${chartIndex}`"
                      class="sa-side-extra-chart-card"
                    >
                      <div class="sa-side-extra-chart-head">
                        <div class="sa-side-extra-chart-title">{{ chartSpec.title || `图表 ${chartIndex + 1}` }}</div>
                        <button v-if="isFeatureEnabled('chart_viewer')" class="sa-ghost-btn sa-side-extra-chart-action" @click="openChartViewer(chartSpec, `${preview.dataset.dataset_name} ${chartSpec.title || `图表 ${chartIndex + 1}`}`)">
                          查看
                        </button>
                      </div>
                      <div
                        v-if="chartSpec.chartType === 'metric'"
                        class="sa-insight-metric sa-insight-metric-compact"
                      >
                        <div class="sa-insight-metric-value">{{ chartSpec.value }}</div>
                        <div class="sa-insight-metric-label">{{ chartSpec.label }}</div>
                      </div>
                      <div
                        v-else
                        class="sa-side-extra-chart-canvas"
                        :ref="el => initPreviewChart(el, chartSpec, `${preview.key}-extra-${chartIndex}`)"
                      ></div>
                    </article>
                  </div>

                  <div v-if="preview.dataset.rows?.length" class="sa-preview-table">
                    <el-table :data="preview.dataset.rows.slice(0, 6)" size="small" style="width:100%">
                      <el-table-column v-for="c in preview.dataset.columns" :key="c" :prop="c" :label="c" min-width="140" />
                    </el-table>
                  </div>
                </div>

                <div v-if="latestReport && !businessDrillReport" class="sa-side-section sa-report-view">
                  <div class="sa-side-section-title">完整报告</div>
                  <div class="sa-chart-actions">
                    <button v-if="isFeatureEnabled('report_fullscreen')" class="sa-ghost-btn" @click="openReportViewer">全屏查看</button>
                  </div>
                  <ul class="sa-report-bullet-list sa-report-bullet-list-compact">
                    <li v-for="(item, index) in reportSummaryBullets.slice(0, 4)" :key="index">{{ item }}</li>
                  </ul>
                  <div class="sa-report-sections">
                    <article
                      v-for="(section, index) in reportNarrativeSections.slice(0, 3)"
                      :key="`${section.title}-${index}`"
                      class="sa-report-section-card"
                    >
                      <div class="sa-report-section-title">{{ section.title }}</div>
                      <div class="sa-report-md sa-report-md-compact" v-html="renderReportMd(section.body)"></div>
                    </article>
                  </div>
                  <div v-if="reportTableBlocks.length" class="sa-report-table-stack">
                    <article
                      v-for="block in reportTableBlocks.slice(0, 2)"
                      :key="`side-${block.key}`"
                      class="sa-report-table-card"
                    >
                      <div class="sa-report-table-head">
                        <div>
                          <div class="sa-report-table-title">{{ block.title }}</div>
                          <div class="sa-report-table-desc">{{ block.description }}</div>
                        </div>
                        <span class="sa-side-meta-chip">{{ block.rows.length }} 行</span>
                      </div>
                      <div class="sa-preview-table sa-preview-table-report">
                        <el-table :data="block.rows.slice(0, 6)" size="small" style="width:100%">
                          <el-table-column
                            v-for="column in block.columns"
                            :key="column"
                            :prop="column"
                            :label="column"
                            min-width="120"
                          />
                        </el-table>
                      </div>
                    </article>
                  </div>
                  <div v-if="!reportNarrativeSections.length" class="sa-report-md" v-html="renderReportMd(latestReport)"></div>
                  <div class="sa-download-row">
                    <button v-if="isFeatureEnabled('report_fullscreen')" class="sa-secondary-btn" @click="openReportViewer">
                      <span class="sa-btn-label">查看大图</span>
                    </button>
                    <button v-if="isFeatureEnabled('smart_report_download')" class="sa-primary-btn" @click="downloadLatestReport">
                      <span class="sa-btn-label">下载报告</span>
                    </button>
                  </div>
                </div>
              </section>
            </div>
          </aside>
        </transition>
      </section>
    </div>

    <el-dialog
      v-model="reportViewerVisible"
      title=""
      :fullscreen="reportDialogFullscreen"
      :width="reportDialogFullscreen ? undefined : 'min(1280px, 94vw)'"
      top="4vh"
      class="sa-report-dialog"
      destroy-on-close
    >
      <div class="sa-report-dialog-body">
        <div class="sa-report-dialog-head">
          <div class="sa-report-dialog-title-block">
            <h3 class="sa-report-dialog-title">业绩分析报告</h3>
            <p v-if="reportViewerTitle" class="sa-report-dialog-subtitle">{{ reportViewerTitle }}</p>
          </div>
          <div class="sa-report-dialog-actions">
            <button class="sa-secondary-btn" @click="reportDialogFullscreen = !reportDialogFullscreen">
              <span class="sa-btn-label">{{ reportDialogFullscreen ? '退出全屏' : '全屏查看' }}</span>
            </button>
            <button class="sa-secondary-btn" @click="reportViewerVisible = false">
              <span class="sa-btn-label">关闭</span>
            </button>
          </div>
        </div>
        <div :class="['sa-report-dialog-content', `is-template-${reportSceneTemplate}`]">
          <div class="sa-report-dialog-overview">
            <section class="sa-report-stage-section sa-report-stage-summary">
              <div class="sa-report-stage-title">{{ reportOverviewTitle }}</div>
              <ul class="sa-report-bullet-list">
                <li v-for="(item, index) in reportSummaryBullets" :key="index">{{ item }}</li>
              </ul>
            </section>

            <section v-if="reportDialogMetricCards.length" class="sa-report-stage-section sa-report-stage-metrics">
              <div class="sa-report-stage-title">关键指标</div>
              <div class="sa-kpi-shelf">
                <div
                  v-for="metric in reportDialogMetricCards"
                  :key="metric.label"
                  class="sa-kpi-card"
                  :class="[
                    { 'is-subject-metric': metric.subject, 'is-explained': metric.hint },
                    metric.tone ? `is-tone-${metric.tone}` : ''
                  ]"
                  :style="metric.accentStyle"
                >
                  <div v-if="metric.subject" class="sa-kpi-subject">{{ metric.subject }}</div>
                  <div class="sa-kpi-value">{{ metric.value }}</div>
                  <div class="sa-kpi-label">{{ metric.label }}</div>
                  <div v-if="metric.hint" class="sa-kpi-hint">{{ metric.hint }}</div>
                </div>
              </div>
            </section>
          </div>

          <section v-if="dialogBusinessDrillReport && businessNarrativeSections.length" class="sa-report-stage-section sa-report-narrative-stage">
            <div class="sa-report-stage-title">经营解读</div>
            <div
              class="sa-management-narrative is-dialog"
              :class="{ 'is-single-focus': dialogBusinessDrillReport.isSingleFocus }"
            >
              <article
                v-for="section in businessNarrativeSections"
                :key="`dialog-narrative-${section.title}`"
                class="sa-management-narrative-card"
              >
                <div class="sa-management-narrative-title">{{ section.title }}</div>
                <div class="sa-report-md sa-report-md-compact sa-management-narrative-body" v-html="renderReportMd(section.body)"></div>
              </article>
            </div>
          </section>

          <section v-if="dialogBusinessDrillReport" class="sa-report-stage-section sa-office-report-stage">
            <div class="sa-report-stage-title">{{ dialogBusinessDrillReport.compareLevelLabel }}下钻分析</div>
            <div v-if="dialogCoreConclusion" class="sa-report-core-conclusion">
              <span>核心判断</span>
              <strong>{{ dialogCoreConclusion }}</strong>
            </div>
            <div v-if="dialogBusinessDrillReport.offices?.length" class="sa-report-chart-card sa-office-overview-dialog">
              <div class="sa-report-chart-head">
                <div>
                  <div class="sa-report-chart-title">各{{ dialogBusinessDrillReport.compareLevelLabel }}对比分析</div>
                  <div class="sa-report-chart-subtitle">{{ dialogBusinessDrillReport.officeCompareText }}</div>
                </div>
              </div>
              <div class="sa-compare-matrix">
                <div class="sa-compare-row is-head">
                  <span>{{ dialogBusinessDrillReport.compareLevelLabel }}</span>
                  <span>总任务</span>
                  <span>已完成</span>
                  <span>剩余缺口</span>
                  <span>达成率</span>
                  <span>达成进度</span>
                  <span>标签</span>
                </div>
                <button
                  v-for="(office, officeIndex) in dialogBusinessDrillReport.offices"
                  :key="`compare-row-${office.id}`"
                  class="sa-compare-row"
                  :style="getOfficeAccentStyle(office, officeIndex)"
                  type="button"
                  @click="toggleOfficeDrill(office.id)"
                >
                  <span class="sa-detail-name">{{ office.name }}</span>
                  <span>{{ getOfficeKpiLabel(office, 'task') }}</span>
                  <span>{{ getOfficeKpiLabel(office, 'actual') }}</span>
                  <span>{{ getOfficeKpiLabel(office, 'remain') }}</span>
                  <span class="sa-detail-rate" :class="office.tone">{{ office.rateLabel }}</span>
                  <span class="sa-detail-progress">
                    <i class="sa-office-bar-track"><b class="is-rate" :class="office.tone" :style="{ width: `${office.progress}%` }"></b></i>
                  </span>
                  <span class="sa-detail-tag" :class="office.tone">{{ office.tag }}</span>
                </button>
              </div>
            </div>
            <div class="sa-office-report-grid">
              <article
                v-for="(office, officeIndex) in dialogBusinessDrillReport.offices"
                :key="`dialog-office-${office.id}`"
                class="sa-office-card sa-office-card-dialog"
                :style="getOfficeAccentStyle(office, officeIndex)"
              >
                <button
                  class="sa-office-card-head"
                  type="button"
                  :aria-expanded="String(isOfficeExpanded(office.id))"
                  @click="toggleOfficeDrill(office.id)"
                >
                  <div class="sa-office-head-main">
                    <div class="sa-office-name">{{ office.name }} <span class="sa-office-tag">{{ office.tag }}</span></div>
                    <div class="sa-office-subtitle">{{ office.childCount }} 个{{ dialogBusinessDrillReport.detailLevelLabel }} · {{ office.parentName || '当前口径' }}</div>
                  </div>
                  <span class="sa-office-head-actions">
                    <span class="sa-office-rate" :class="office.tone">{{ office.rateLabel }}<small v-if="office.rankLabel">{{ office.rankLabel }}</small></span>
                    <span
                      class="sa-office-drill-toggle"
                      :class="{ 'is-open': isOfficeExpanded(office.id) }"
                      :title="isOfficeExpanded(office.id) ? '收起下钻明细' : `展开查看${office.childCount || 0}个${dialogBusinessDrillReport.detailLevelLabel}`"
                    >
                      <span>{{ isOfficeExpanded(office.id) ? '收起' : '下钻' }}</span>
                      <i></i>
                    </span>
                  </span>
                </button>
                <p class="sa-office-copy">{{ office.summary }}</p>
                <div v-if="isOfficeExpanded(office.id)" class="sa-office-drill is-dialog">
                  <div class="sa-drill-path">
                    <span>{{ office.name }}</span>
                    <i></i>
                    <strong>{{ dialogBusinessDrillReport.detailLevelLabel }}</strong>
                  </div>
                  <div class="sa-drill-insight-grid">
                    <div class="sa-drill-insight-card is-good">
                      <span>下钻亮点</span>
                      <strong>{{ getDrillBestText(office) }}</strong>
                    </div>
                    <div class="sa-drill-insight-card is-risk">
                      <span>重点压力</span>
                      <strong>{{ getDrillWorstText(office) }}</strong>
                    </div>
                  </div>
                  <p class="sa-chart-copy sa-chart-copy-drill">{{ office.chartText }}</p>
                  <div v-if="office.detailRows?.length" class="sa-office-detail-wrap is-dialog">
                    <div class="sa-drill-table-head">
                      <span>{{ dialogBusinessDrillReport.detailLevelLabel }}明细</span>
                      <small>按达成率排序，点击上层卡片可收起</small>
                    </div>
                    <div class="sa-office-detail-table">
                      <div class="sa-office-detail-row is-head">
                        <span>{{ dialogBusinessDrillReport.detailLevelLabel }}</span>
                        <span>任务/已完成</span>
                        <span>剩余缺口</span>
                        <span>达成率</span>
                        <span>达成进度</span>
                        <span>标签</span>
                      </div>
                      <div v-for="person in office.detailRows" :key="`${office.id}-${person.name}`" class="sa-office-detail-row">
                        <span class="sa-detail-name">{{ person.name }}</span>
                        <span>{{ person.taskLabel }} / {{ person.actualLabel }}</span>
                        <span>{{ person.remainLabel }}</span>
                        <span class="sa-detail-rate" :class="person.tone">{{ person.rateLabel }}</span>
                        <span class="sa-detail-progress">
                          <i class="sa-office-bar-track"><b class="is-rate" :class="person.tone" :style="{ width: `${person.progress}%` }"></b></i>
                        </span>
                        <span class="sa-detail-tag" :class="person.tone">{{ person.label }}</span>
                      </div>
                    </div>
                    <div v-if="office.drillGroups?.length" class="sa-rep-drill-list is-dialog">
                      <div class="sa-rep-drill-title">继续下钻到业务员</div>
                      <article
                        v-for="group in office.drillGroups"
                        :key="`${office.id}-${group.id}`"
                        class="sa-rep-drill-card"
                      >
                        <button
                          class="sa-rep-drill-head"
                          type="button"
                          @click="toggleOfficeDrill(`rep-${office.id}-${group.id}`)"
                        >
                          <div class="sa-office-head-main">
                            <div class="sa-rep-drill-name">{{ group.name }} <span class="sa-office-tag">{{ group.tag }}</span></div>
                            <div class="sa-rep-drill-subtitle">{{ group.childCount }} 个{{ group.detailLevelLabel }} · {{ group.parentName || office.name }}</div>
                          </div>
                          <span class="sa-office-head-actions">
                            <span class="sa-office-rate" :class="group.tone">{{ group.rateLabel }}</span>
                            <span
                              class="sa-office-drill-toggle is-small"
                              :class="{ 'is-open': isOfficeExpanded(`rep-${office.id}-${group.id}`) }"
                              :title="isOfficeExpanded(`rep-${office.id}-${group.id}`) ? '收起业务员明细' : '展开业务员明细'"
                            >
                              <span>{{ isOfficeExpanded(`rep-${office.id}-${group.id}`) ? '收起' : '业务员' }}</span>
                              <i></i>
                            </span>
                          </span>
                        </button>
                        <p v-if="group.summary" class="sa-rep-drill-summary">{{ group.summary }}</p>
                        <div v-if="isOfficeExpanded(`rep-${office.id}-${group.id}`)" class="sa-office-detail-table sa-rep-person-table">
                          <div class="sa-office-detail-row is-head">
                            <span>{{ group.detailLevelLabel }}</span>
                            <span>任务/已完成</span>
                            <span>剩余缺口</span>
                            <span>达成率</span>
                            <span>达成进度</span>
                            <span>标签</span>
                          </div>
                          <div v-for="person in group.detailRows" :key="`${office.id}-${group.id}-${person.name}`" class="sa-office-detail-row">
                            <span class="sa-detail-name">{{ person.name }}</span>
                            <span>{{ person.taskLabel }} / {{ person.actualLabel }}</span>
                            <span>{{ person.remainLabel }}</span>
                            <span class="sa-detail-rate" :class="person.tone">{{ person.rateLabel }}</span>
                            <span class="sa-detail-progress">
                              <i class="sa-office-bar-track"><b class="is-rate" :class="person.tone" :style="{ width: `${person.progress}%` }"></b></i>
                            </span>
                            <span class="sa-detail-tag" :class="person.tone">{{ person.label }}</span>
                          </div>
                        </div>
                      </article>
                    </div>
                  </div>
                  <div v-else class="sa-office-empty-drill">
                    当前 SQL 结果未返回 {{ dialogBusinessDrillReport.detailLevelLabel }} 明细。
                  </div>
                </div>
              </article>
            </div>
          </section>

          <section v-else-if="reportDialogCharts.length" class="sa-report-stage-section">
            <div class="sa-report-stage-title">图表分析</div>
            <div class="sa-report-chart-grid">
              <article v-for="block in reportDialogCharts" :key="block.key" class="sa-report-chart-card">
                <div class="sa-report-chart-head">
                  <div>
                    <div class="sa-report-chart-title">{{ block.dataset.dataset_name }}</div>
                    <div class="sa-report-chart-subtitle">{{ block.chartSpec.title || '图表预览' }}</div>
                  </div>
                  <button v-if="isFeatureEnabled('chart_viewer')" class="sa-ghost-btn" @click="openChartViewer(block.chartSpec, `${block.dataset.dataset_name} 图表预览`)">放大查看</button>
                </div>
                <div v-if="block.chartSpec.chartType === 'metric'" class="sa-insight-metric sa-insight-metric-report">
                  <div class="sa-insight-metric-value">{{ block.chartSpec.value }}</div>
                  <div class="sa-insight-metric-label">{{ block.chartSpec.label }}</div>
                </div>
                <div v-else class="sa-report-chart-canvas" :ref="el => initPreviewChart(el, block.chartSpec, `report-${block.key}`)"></div>
              </article>
            </div>
          </section>

          <section v-if="!dialogBusinessDrillReport && reportTableBlocks.length" class="sa-report-stage-section">
            <div class="sa-report-stage-title">数据表洞察</div>
            <div class="sa-report-table-grid">
              <article
                v-for="block in reportTableBlocks"
                :key="`dialog-${block.key}`"
                class="sa-report-table-card sa-report-table-card-dialog"
              >
                <div class="sa-report-table-head">
                  <div>
                    <div class="sa-report-table-title">{{ block.title }}</div>
                    <div class="sa-report-table-desc">{{ block.description }}</div>
                  </div>
                  <span class="sa-side-meta-chip">{{ block.rows.length }} 行</span>
                </div>
                <div class="sa-preview-table sa-preview-table-report sa-preview-table-report-dialog">
                  <el-table :data="block.rows" size="small" style="width:100%">
                    <el-table-column
                      v-for="column in block.columns"
                      :key="column"
                      :prop="column"
                      :label="column"
                      min-width="140"
                    />
                  </el-table>
                </div>
              </article>
            </div>
          </section>

          <section v-if="!dialogBusinessDrillReport" class="sa-report-stage-section">
            <div class="sa-report-stage-title">完整解读</div>
            <div class="sa-report-sections">
              <article
                v-for="(section, index) in reportNarrativeSections"
                :key="`${section.title}-${index}`"
                class="sa-report-section-card sa-report-section-card-dialog"
              >
                <div class="sa-report-section-title">{{ section.title }}</div>
                <div class="sa-report-md" v-html="renderReportMd(section.body)"></div>
              </article>
            </div>
            <div v-if="!reportNarrativeSections.length" class="sa-report-md" v-html="renderReportMd(reportViewerReport || latestReport)"></div>
          </section>
        </div>
      </div>
    </el-dialog>

    <el-dialog
      v-model="chartViewerVisible"
      :title="chartViewerTitle"
      width="min(980px, 92vw)"
      top="8vh"
      class="sa-chart-dialog"
      destroy-on-close
    >
      <div class="sa-chart-dialog-body">
        <div v-if="chartViewerHasTable" class="sa-chart-dialog-head">
          <div class="sa-chart-dialog-kicker">DETAIL VIEW</div>
          <div class="sa-chart-dialog-switch">
            <button
              type="button"
              class="sa-chart-switch-btn"
              :class="{ 'is-active': chartViewerMode === 'chart' }"
              @click="chartViewerMode = 'chart'"
            >
              图表
            </button>
            <button
              type="button"
              class="sa-chart-switch-btn"
              :class="{ 'is-active': chartViewerMode === 'table' }"
              @click="chartViewerMode = 'table'"
            >
              数据表
            </button>
          </div>
        </div>
        <div v-if="chartViewerMode === 'chart' && chartViewerSpec?.chartType === 'metric'" class="sa-insight-metric sa-insight-metric-large">
          <div class="sa-insight-metric-value">{{ chartViewerSpec.value }}</div>
          <div class="sa-insight-metric-label">{{ chartViewerSpec.label }}</div>
        </div>
        <div v-else-if="chartViewerMode === 'chart'" ref="chartDialogRef" class="sa-chart-dialog-canvas"></div>
        <div v-else class="sa-chart-dialog-table">
          <div class="sa-chart-dialog-table-meta">
            <span>{{ chartViewerTableColumns.length }} 列</span>
            <span>{{ chartViewerTableRows.length }} 行</span>
          </div>
          <el-table :data="chartViewerTableRows" size="small" border height="68vh" style="width: 100%">
            <el-table-column
              v-for="column in chartViewerTableColumns"
              :key="column"
              :prop="column"
              :label="column"
              min-width="140"
              show-overflow-tooltip
            />
          </el-table>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onActivated, onDeactivated, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import * as echarts from 'echarts'
import { getBookshelfDatasets, getCommonQuestions, getActiveAIModels } from '../api/index'
import { useSmartAskSession } from '../state/smartAskSession'
import { getSessionCache, setSessionCache } from '../state/sessionCache'
import { useFeatureFlags } from '../state/featureFlags'

defineOptions({ name: 'SmartAsk' })
import ChatHeader from '../components/smartask/ChatHeader.vue'
import WelcomeScreen from '../components/smartask/WelcomeScreen.vue'
import UserBubble from '../components/smartask/UserBubble.vue'
import PlanCard from '../components/smartask/PlanCard.vue'
import ThinkingCard from '../components/smartask/ThinkingCard.vue'
import LiveExecutionFeed from '../components/smartask/LiveExecutionFeed.vue'
import ResultDigestCard from '../components/smartask/ResultDigestCard.vue'
import ComposerArea from '../components/smartask/ComposerArea.vue'
import LogTimeline from '../components/smartask/LogTimeline.vue'
import SqlBlock from '../components/smartask/SqlBlock.vue'
import { useSmartAskHistory } from '../state/smartAskHistory'
import { buildOrgTree, getDefaultConfig as getDefaultReportTreeConfig } from '../composables/useOrgTree'
import '../styles/volcano-design.css'

const session = useSmartAskSession()
const { isFeatureEnabled, loadFeatureFlags } = useFeatureFlags()
const {
  pendingRestoreId,
  loadHistory,
  upsertHistory,
  findHistoryById,
  clearRestoreRequest,
  setActiveHistory,
} = useSmartAskHistory()
const query = ref('')
const datasetId = ref(null)
const modelId = ref(null)
const datasets = ref([])
const aiModels = ref([])
const commonQuestions = ref([])
const commonQuestionsLoading = ref(false)
const messages = reactive([])
const confirmationDrafts = reactive({})
const confirmationSubmitting = reactive({})
const showPanel = ref(true)
const chatBodyRef = ref(null)
const panelRef = ref(null)
const sideReportRef = ref(null)
const sideReportHeadRef = ref(null)
const chartDialogRef = ref(null)
const thinkingOpen = reactive({})
const logOpen = reactive({})
const timelineVersion = ref(0)
const reportViewerVisible = ref(false)
const reportViewerTitle = ref('')
const reportViewerReport = ref('')
const reportViewerDatasets = ref([])
const reportDialogFullscreen = ref(false)
const chartViewerVisible = ref(false)
const chartViewerTitle = ref('图表预览')
const chartViewerSpec = ref(null)
const chartViewerMode = ref('chart')
const officeDrillOpen = reactive({})
let activePrintFrame = null
let msgCounter = 0
let elapsed = ref(0)
let timerInst = null
let chatScrollTimer = null
let panelScrollTimer = null

const isRunning = computed(() => session.state.status === 'running')
const timelineKey = computed(() => `${session.state.conversationSessionId || 'fresh'}-${timelineVersion.value}`)
const detailPanelVisible = computed(() => showPanel.value && isFeatureEnabled('debug_execution_trace'))
const canViewCharts = computed(() => isFeatureEnabled('chart_viewer'))
const canViewFullscreenReport = computed(() => isFeatureEnabled('report_fullscreen'))

const statusBarText = computed(() => {
  const m = {
    running: session.state.logs.slice(-1)[0]?.title || '任务执行中',
    completed: '本轮问数已完成',
    error: '当前任务执行异常',
    waiting_confirmation: '等待确认统计口径'
  }
  return m[session.state.status] || ''
})

const latestDatasets = computed(() => (
  Array.isArray(session.state.result?.dataset_results) ? session.state.result.dataset_results : []
))

const mergeDatasetReports = (datasetResults) => (
  (datasetResults || [])
    .map((dataset, index) => {
      const analysis = String(dataset?.analysis || '').trim()
      if (!analysis) return ''
      const datasetName = dataset?.dataset_name || `数据集 ${dataset?.dataset_id || index + 1}`
      return datasetResults.length > 1 ? `## ${datasetName}\n\n${analysis}` : analysis
    })
    .filter(Boolean)
    .join('\n\n---\n\n')
)

const buildAggregateDataset = (datasetResults) => {
  if (!Array.isArray(datasetResults) || datasetResults.length === 0) return null
  if (datasetResults.length === 1) return datasetResults[0]

  const totalRows = datasetResults.reduce((sum, item) => sum + Number(item?.row_count || item?.rows?.length || 0), 0)
  const allColumns = Array.from(new Set(datasetResults.flatMap(item => item?.columns || [])))

  return {
    dataset_name: `共 ${datasetResults.length} 个数据集`,
    dataset_id: 'multi',
    row_count: totalRows,
    rows: { length: totalRows },
    columns: allColumns,
  }
}

const latestDataset = computed(() => buildAggregateDataset(latestDatasets.value))

const latestReport = computed(() => mergeDatasetReports(latestDatasets.value))

const currentDatasetLabel = computed(() => {
  const bySelected = datasets.value.find(item => item.id === datasetId.value)?.dataset_name
  const byResult = latestDataset.value?.dataset_name
  return bySelected || byResult || '自动路由数据集'
})

const datasetResults = computed(() => latestDatasets.value)
const hasSideReport = computed(() => resultPreviews.value.length > 0 || !!latestReport.value)
const sideReportHeading = computed(() => '业绩分析报告')
const sideReportTitle = computed(() => latestDataset.value?.dataset_name || '业绩分析报告')

const reportSceneTemplate = computed(() => {
  const sourceDatasets = reportViewerVisible.value ? reportViewerDatasets.value : latestDatasets.value
  const specTemplate = sourceDatasets.find(item => item?.report_spec?.layoutTemplate)?.report_spec?.layoutTemplate
  if (specTemplate) return specTemplate
  const questionText = String(session.state.question || query.value || '')
  if (/对比|比较|哪个|谁更|差异|和.+比|跟.+比|与.+比|\bvs\b/i.test(questionText)) return 'comparison'
  if (/排名|排行|前\s*\d+|Top\s*\d+|TOP\s*\d+|最好|最差|最高|最低/.test(questionText)) return 'ranking'
  return 'detail'
})

const reportSceneTemplateLabel = computed(() => ({
  comparison: '对比模板',
  ranking: '排名模板',
  detail: '详情模板',
}[reportSceneTemplate.value] || '详情模板'))

const normalizeConfidenceScore = (value, fallback = 0) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return fallback
  return Math.max(0, Math.min(100, Math.round(numeric)))
}

const buildRouteConfidenceMeta = (route = {}) => {
  const candidateCount = Array.isArray(route?.candidate_dataset_ids)
    ? route.candidate_dataset_ids.length
    : Array.isArray(route?.dataset_ids)
      ? route.dataset_ids.length
      : 0

  let score = normalizeConfidenceScore(route?.match_score, candidateCount <= 1 ? 78 : 64)
  if (candidateCount > 1) score -= Math.min(12, (candidateCount - 1) * 6)
  if (route?.requires_confirmation) score = Math.min(score, 60)
  if (route?.preferred_dataset_override) score = Math.max(score, 72)

  return {
    score,
    tone: score >= 82 ? 'success' : score >= 65 ? 'info' : 'warning',
    label: score >= 82 ? '路由把握' : score >= 65 ? '路由可用' : '路由待确认',
    value: `${score}`,
    candidateCount,
  }
}

const buildResultConfidenceMeta = (route = {}, datasets = []) => {
  const reviews = (datasets || []).map(item => item?.agent3_review).filter(Boolean)
  const approvedCount = reviews.filter(item => item?.approved !== false).length
  const riskCount = reviews.reduce((sum, item) => sum + (Array.isArray(item?.risks) ? item.risks.length : 0), 0)
  const datasetTotal = (datasets || []).length
  const rowsReady = (datasets || []).filter(item => Array.isArray(item?.rows) && item.rows.length > 0).length
  const analysesReady = (datasets || []).filter(item => String(item?.analysis || '').trim()).length

  let score = 55
  if (datasetTotal > 0) score += 8
  if (rowsReady === datasetTotal && datasetTotal > 0) score += 16
  else if (rowsReady > 0) score += 8
  if (reviews.length === datasetTotal && approvedCount === datasetTotal && datasetTotal > 0) score += 12
  else if (approvedCount > 0) score += 6
  if (analysesReady === datasetTotal && datasetTotal > 0) score += 8
  score -= Math.min(18, riskCount * 4)
  if (buildRouteConfidenceMeta(route).candidateCount > 1) score -= 5
  score = normalizeConfidenceScore(score, 60)

  return {
    score,
    tone: score >= 80 ? 'success' : score >= 62 ? 'info' : 'warning',
    label: score >= 80 ? '结果稳定' : score >= 62 ? '结果可用' : '结果谨慎',
    value: riskCount > 0 ? `${score} / ${riskCount} 风险` : `${score}`,
  }
}

const sideConfidenceBadges = computed(() => {
  const backendConfidence = session.state.result?.confidence || {}
  const routeMeta = backendConfidence?.route
    ? {
        score: Number(backendConfidence.route.score || 0),
        tone: backendConfidence.route.level === 'high' ? 'success' : backendConfidence.route.level === 'medium' ? 'info' : 'warning',
        label: '路由把握',
        value: `${backendConfidence.route.label || ''} ${backendConfidence.route.score || 0}`.trim(),
      }
    : buildRouteConfidenceMeta(session.state.result?.route || {})
  const resultMeta = backendConfidence?.result
    ? {
        score: Number(backendConfidence.result.score || 0),
        tone: backendConfidence.result.level === 'high' ? 'success' : backendConfidence.result.level === 'medium' ? 'info' : 'warning',
        label: '结果可信',
        value: `${backendConfidence.result.label || ''} ${backendConfidence.result.score || 0}`.trim(),
      }
    : buildResultConfidenceMeta(session.state.result?.route || {}, latestDatasets.value)
  return [routeMeta, resultMeta].filter(item => item?.score > 0)
})

const sideConfidenceNote = computed(() => {
  const routeConfidence = session.state.result?.confidence?.route
  if (routeConfidence?.summary) return routeConfidence.summary
  const route = session.state.result?.route || {}
  if (!route?.match_score) return ''
  const candidateCount = Array.isArray(route.candidate_dataset_ids) ? route.candidate_dataset_ids.length : 0
  if (route.requires_confirmation) return '当前命中仍存在不确定性，系统已暂停并等待确认。'
  if (candidateCount > 1) return `已比较 ${candidateCount} 个候选数据集，继续保留路由复核记录。`
  return '当前命中已完成语义复核，后续仍经过 SQL 生成、SQL 复核和报告口径核对。'
})

const detailPanelState = computed(() => {
  const m = {
    idle: '待命',
    running: '执行中',
    completed: '已完成',
    error: '异常',
    waiting_confirmation: '待确认',
  }
  return m[session.state.status] || '待命'
})

const detailPanelDesc = computed(() => {
  if (session.state.status === 'running') {
    return session.latestLog?.value?.summary || session.latestLog?.value?.title || session.state.logs.slice(-1)[0]?.detail || '正在持续更新本轮问数任务的执行进度。'
  }
  if (session.state.status === 'completed') {
    return '本轮问数已经完成，可以继续查看执行细节、结果数据和完整报告。'
  }
  if (session.state.status === 'waiting_confirmation') {
    return '当前任务等待确认统计口径，确认后会继续后续执行步骤。'
  }
  if (session.state.status === 'error') {
    return session.state.error || '当前任务执行异常，请查看节点详情后重新发起问数。'
  }
  return '发起问题后，这里会持续展示本轮任务的完整执行轨迹。'
})

const amountColumnPattern = /金额|开单|任务|销售|收入|成本|利润|缺口|剩余|回款|费用|价格|单价|amount|sales|revenue|cost|profit|remain/i
const rateColumnPattern = /率|percent|rate/i

const formatAmount = (value) => {
  const numeric = typeof value === 'number'
    ? value
    : Number(String(value ?? '').replace(/[^0-9.-]/g, ''))
  if (!Number.isFinite(numeric)) return '-'
  const absValue = Math.abs(numeric)
  if (absValue < 10000) return Number.isInteger(numeric) ? String(numeric) : String(numeric)
  if (absValue < 1000000) return `${(numeric / 10000).toFixed(1)}万`
  if (absValue < 100000000) return `${Math.round(numeric / 10000)}万`
  return `${(numeric / 100000000).toFixed(2)}亿`
}

const isAmountColumn = (column = '') => amountColumnPattern.test(String(column || ''))
const isRateColumn = (column = '') => rateColumnPattern.test(String(column || ''))

const formatDisplayValue = (value) => {
  if (typeof value === 'number') {
    if (Number.isInteger(value)) return value.toLocaleString()
    return value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
  }
  return String(value ?? '-')
}

const formatValueByColumn = (value, column = '') => {
  if (isAmountColumn(column)) return formatAmount(value)
  return formatDisplayValue(value)
}

const getLabelColumn = (dataset) => {
  const columns = dataset?.columns || []
  const firstRow = dataset?.rows?.[0] || {}
  return (
    columns.find(col => /日期|时间|城市|分公司|名称|水平|类型|标识/i.test(col)) ||
    columns.find(col => typeof firstRow[col] === 'string') ||
    columns[0]
  )
}

const getNumericColumns = (dataset) => {
  const columns = dataset?.columns || []
  const firstRow = dataset?.rows?.[0] || {}
  return columns.filter(col => typeof firstRow[col] === 'number')
}

const getMetricCards = (dataset) => {
  const rows = dataset?.rows || []
  if (!rows.length) return []

  const businessCards = getBusinessMetricCards(dataset)
  if (businessCards.length) return businessCards

  const firstRow = rows[0]
  const numericColumns = getNumericColumns(dataset)
  const cards = []

  numericColumns.slice(0, 3).forEach((column) => {
    const values = rows.map(row => row[column]).filter(value => typeof value === 'number')
    if (!values.length) return
    const displayValue = rows.length === 1 ? firstRow[column] : Math.max(...values)
    cards.push({ label: rows.length === 1 ? column : `最高${column}`, value: formatValueByColumn(displayValue, column) })
  })

  if (rows.length === 1 && cards.length === 0) {
    const labelColumn = getLabelColumn(dataset)
    if (labelColumn) cards.push({ label: labelColumn, value: formatDisplayValue(firstRow[labelColumn]) })
  }

  if (rows.length > 1) cards.push({ label: '数据行数', value: formatDisplayValue(rows.length) })
  return cards.slice(0, 3)
}

const toNumber = (value) => {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  const cleaned = String(value ?? '').replace(/[^0-9.-]/g, '')
  if (!cleaned) return null
  const numeric = Number(cleaned)
  return Number.isFinite(numeric) ? numeric : null
}

const pickColumn = (dataset, names) => {
  const columns = dataset?.columns || []
  return names.find(name => columns.includes(name)) || ''
}

const getDatasetReportConfig = (dataset) => (
  dataset?.report_config
  || session.state.result?.report_configs?.[String(dataset?.dataset_id)]
  || session.state.result?.report_config
  || getDefaultReportTreeConfig()
)

const getDatasetTreeModel = (dataset) => {
  const rows = Array.isArray(dataset?.rows) ? dataset.rows : []
  if (!rows.length) return null
  return buildOrgTree(rows, getDatasetReportConfig(dataset))
}

const sumBusinessColumn = (rows, column) => {
  if (!column) return null
  const values = rows.map(row => toNumber(row?.[column])).filter(value => value !== null)
  if (!values.length) return null
  return values.reduce((sum, value) => sum + value, 0)
}

const calcBusinessRate = (rows, taskCol, actualCol, rateCol) => {
  const task = sumBusinessColumn(rows, taskCol)
  const actual = sumBusinessColumn(rows, actualCol)
  if (task && actual !== null && task > 0) return Number((actual / task * 100).toFixed(2))
  const rates = rows.map(row => toNumber(row?.[rateCol])).filter(value => value !== null)
  if (!rates.length) return null
  return Number((rates.reduce((sum, value) => sum + value, 0) / rates.length).toFixed(2))
}

const formatBusinessAmount = (value) => {
  if (value === null || value === undefined) return '-'
  return formatAmount(value)
}

const formatMetricByDefinition = (value, metric = {}) => {
  if (value === null || value === undefined) return '-'
  if (metric.format === 'percent') return `${Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 })}%`
  if (metric.format === 'amount') return formatBusinessAmount(value)
  return formatDisplayValue(value)
}

const getMetricDefinition = (config, key, matcher) => {
  const metrics = config?.metrics || []
  return metrics.find(item => item.key === key)
    || metrics.find(item => matcher?.(item))
    || null
}

const getNodeMetricValue = (node, metric) => {
  if (!node || !metric) return null
  const direct = toNumber(node.metrics?.[metric.key])
  if (direct !== null) return direct
  return toNumber(node.raw?.[metric.column])
}

const getRateTone = (rate, benchmark = 15, risk = 10) => {
  const value = toNumber(rate)
  if (value === null) return 'neutral'
  if (value >= benchmark) return 'good'
  if (value >= risk) return 'warn'
  return 'danger'
}

const getToneLabel = (tone) => ({ good: '区域标杆', warn: '中等达成', danger: '低达成风险' }[tone] || '待观察')

const getRateTag = (rate, benchmark = 15, risk = 10, goodLabel = '标杆') => {
  const tone = getRateTone(rate, benchmark, risk)
  if (tone === 'good') return `✅ ${goodLabel}`
  if (tone === 'warn') return '🟡 中等'
  if (tone === 'danger') return '⚠️ 风险'
  return '未分级'
}

const subjectAccentPalette = [
  { accent: '#165dff', soft: 'rgba(22, 93, 255, 0.08)', border: 'rgba(22, 93, 255, 0.22)' },
  { accent: '#00a870', soft: 'rgba(0, 168, 112, 0.08)', border: 'rgba(0, 168, 112, 0.22)' },
  { accent: '#ff7d00', soft: 'rgba(255, 125, 0, 0.09)', border: 'rgba(255, 125, 0, 0.24)' },
  { accent: '#7b61ff', soft: 'rgba(123, 97, 255, 0.08)', border: 'rgba(123, 97, 255, 0.22)' },
]

const getSubjectAccent = (index = 0) => subjectAccentPalette[Math.abs(index) % subjectAccentPalette.length]

const getOfficeAccentStyle = (_office, index = 0) => {
  const color = getSubjectAccent(index)
  return {
    '--office-accent': color.accent,
    '--office-accent-soft': color.soft,
    '--office-accent-border': color.border,
  }
}

const decorateMetricCards = (kpis = [], offices = []) => (
  (kpis || []).map((item) => {
    const label = item.label || item.key || ''
    const officeIndex = offices.findIndex(office => label.startsWith(office.name))
    if (officeIndex < 0) {
      return {
        label,
        value: item.value ?? item.displayValue ?? formatDisplayValue(item.value),
      }
    }
    const office = offices[officeIndex]
    const color = getSubjectAccent(officeIndex)
    return {
      label: label.replace(office.name, ''),
      value: item.value ?? item.displayValue ?? formatDisplayValue(item.value),
      subject: office.name,
      accentStyle: {
        '--metric-accent': color.accent,
        '--metric-accent-soft': color.soft,
        '--metric-accent-border': color.border,
      },
    }
  }).filter(item => item.label)
)

const getOfficeKpiLabel = (office, type) => {
  const matchers = {
    task: /总任务|任务金额|目标/i,
    actual: /年度开单|开单|完成|实际|销售/i,
    remain: /剩余|缺口|差额|remain/i,
    rate: /达成率|percent|rate/i,
  }
  const matcher = matchers[type]
  const item = (office?.kpis || []).find(kpi => matcher?.test(kpi.label || ''))
  return item?.value || '-'
}

const getReportKpi = (report, type) => {
  const matchers = {
    task: /总任务|任务金额|目标/i,
    actual: /年度开单|开单|完成|实际|销售/i,
    remain: /剩余|缺口|差额|remain/i,
    rate: /达成率|percent|rate/i,
  }
  const matcher = matchers[type]
  return (report?.kpis || []).find(kpi => matcher?.test(kpi.label || '')) || null
}

const getReportKpiText = (report, type) => getReportKpi(report, type)?.value || '-'

const getSingleOrgCounts = (report) => {
  const offices = report?.offices || []
  const directCount = offices.length
  const detailCount = offices.reduce((sum, office) => (
    sum + Number(office.childCount || office.detailRows?.length || 0)
  ), 0)
  return {
    directCount,
    detailCount,
    directLabel: report?.compareLevelLabel || '下级节点',
    detailLabel: report?.detailLevelLabel || '明细节点',
  }
}

const getSingleOrgRateTone = (report) => {
  const rate = toNumber(getReportKpiText(report, 'rate'))
  if (rate === null) return 'neutral'
  return rate < 10 ? 'danger' : rate < 15 ? 'warn' : 'good'
}

const getSingleOrgConclusion = (report) => {
  if (!report) return ''
  const focusName = report.focusName || '当前组织'
  const task = getReportKpiText(report, 'task')
  const actual = getReportKpiText(report, 'actual')
  const rate = getReportKpiText(report, 'rate')
  const remain = getReportKpiText(report, 'remain')
  const remainText = remain && remain !== '-' ? `，剩余缺口 ${remain}` : ''
  const toneLabel = {
    good: '整体进度相对领先',
    warn: '整体进度偏滞后',
    danger: '整体进度明显滞后',
    neutral: '整体进度已形成初步判断',
  }[getSingleOrgRateTone(report)]
  return `${focusName}${toneLabel}，年度总任务 ${task}，当前开单 ${actual}，整体达成率 ${rate}${remainText}。`
}

const getSingleOrgRankContext = (report) => {
  const offices = report?.offices || []
  const ranked = [...offices].filter(item => item.rate !== null).sort((a, b) => (b.rate || 0) - (a.rate || 0))
  const best = ranked[0]
  const worst = ranked[ranked.length - 1]
  const diff = best && worst && best.rate !== null && worst.rate !== null
    ? Math.abs((best.rate || 0) - (worst.rate || 0)).toFixed(2).replace(/\.?0+$/, '')
    : ''
  return { best, worst, diff }
}

const enrichSingleOrgMetricCards = (cards = [], report) => (
  (cards || []).map((card) => {
    const label = card.label || ''
    let hint = ''
    let tone = ''
    if (/总任务|任务金额|目标/i.test(label)) {
      hint = `${report?.focusName || '当前组织'}年度目标总量`
    } else if (/年度开单|开单|完成|实际|销售/i.test(label)) {
      hint = '当前已完成金额'
    } else if (/达成率|percent|rate/i.test(label)) {
      tone = getSingleOrgRateTone(report)
      hint = tone === 'good' ? '高于标杆线，保持节奏' : tone === 'danger' ? '低于风险线，需重点干预' : '低于预期进度，需持续跟进'
    } else if (/剩余|缺口|差额|remain/i.test(label)) {
      tone = 'warn'
      hint = '后续需推进缺口金额'
    }
    return { ...card, hint, tone }
  })
)

const getDrillBestText = (office) => {
  const rows = Array.isArray(office?.detailRows) ? office.detailRows : []
  const best = rows.filter(item => item.rate !== null && item.rate !== undefined)
    .sort((left, right) => (right.rate || 0) - (left.rate || 0))[0]
  if (!best) return office?.highlight || '暂无下级明细'
  return `${best.name} ${best.rateLabel || '-'}`
}

const getDrillWorstText = (office) => {
  const rows = Array.isArray(office?.detailRows) ? office.detailRows : []
  const worst = rows.filter(item => item.rate !== null && item.rate !== undefined)
    .sort((left, right) => (left.rate || 0) - (right.rate || 0))[0]
  if (!worst) return office?.riskSummary || '暂无风险明细'
  return `${worst.name} ${worst.rateLabel || '-'}`
}

const findColumn = (columns = [], matcher) => columns.find(column => matcher(String(column || ''))) || ''

const buildOfficeDetailRows = (chartSpec = {}) => {
  const rows = Array.isArray(chartSpec.rows) ? chartSpec.rows : []
  const columns = Array.isArray(chartSpec.columns) && chartSpec.columns.length
    ? chartSpec.columns
    : Object.keys(rows[0] || {})
  const nameColumn = columns[0] || '名称'
  const rateColumn = findColumn(columns, column => isRateColumn(column)) || '达成率'
  const taskColumn = findColumn(columns, column => /任务|目标/i.test(column) && !/剩余|缺口/i.test(column))
  const actualColumn = findColumn(columns, column => /开单|完成|实际|销售/i.test(column))
  const remainColumn = findColumn(columns, column => /剩余|缺口|差额|remain/i.test(column))

  return rows.map((row) => {
    const rate = toNumber(row?.[rateColumn]) || 0
    const remain = toNumber(row?.[remainColumn]) || 0
    const task = toNumber(row?.[taskColumn]) || 0
    const actual = toNumber(row?.[actualColumn]) || 0
    const label = row?.标签 || getRateTag(rate, 20, 10)
    return {
      name: row?.[nameColumn] || row?.名称 || '-',
      rate,
      rateLabel: isRateColumn(rateColumn) ? `${rate.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}%` : formatDisplayValue(rate),
      task,
      taskLabel: taskColumn ? formatAmount(task) : '-',
      actual,
      actualLabel: actualColumn ? formatAmount(actual) : '-',
      remain,
      remainLabel: remainColumn ? formatAmount(remain) : '-',
      label,
      tone: label.includes('风险') ? 'danger' : label.includes('中等') ? 'warn' : label.includes('标杆') ? 'good' : getRateTone(rate, 20, 10),
      progress: Math.max(0, Math.min(100, rate)),
      gapProgress: 0,
    }
  }).map((row, _index, list) => {
    const maxRemain = Math.max(...list.map(item => item.remain || 0), 1)
    return {
      ...row,
      gapProgress: Math.max(0, Math.min(100, ((row.remain || 0) / maxRemain) * 100)),
    }
  })
}

const getDescendantNodes = (node) => {
  const output = []
  const walk = (current) => {
    ;(current?.children || []).forEach((child) => {
      output.push(child)
      walk(child)
    })
  }
  walk(node)
  return output
}

const isLeafNode = (node) => !Array.isArray(node?.children) || node.children.length === 0

const getLevelLabelFromNodes = (nodes = [], fallback = '层级') => {
  const values = Array.from(new Set(nodes.map(node => node?.levelValue || node?.levelName).filter(Boolean)))
  if (values.length === 1) return values[0]
  if (values.length > 1) return values.join(' / ')
  return fallback
}

const findQuestionFocusNode = (nodes = []) => {
  const questionText = String(session.state.question || query.value || '').trim()
  if (!questionText) return null
  return [...nodes]
    .filter(node => node?.name && questionText.includes(node.name) && Array.isArray(node.children) && node.children.length > 0)
    .sort((a, b) => String(b.name).length - String(a.name).length)[0] || null
}

const getComparisonNodes = (model) => {
  const focusNode = findQuestionFocusNode(model.flatNodes || [])
  if (focusNode?.children?.length) return focusNode.children
  const singleRoot = model.tree?.length === 1 ? model.tree[0] : null
  if (singleRoot?.children?.length) return singleRoot.children
  const parentNodes = (model.flatNodes || []).filter(node => Array.isArray(node.children) && node.children.length > 0)
  const maxParentDepth = Math.max(...parentNodes.map(node => Number(node.depth) || 0), 0)
  return parentNodes.filter(node => Number(node.depth) === maxParentDepth)
}

const getDetailNodes = (node) => {
  const directChildren = (node?.children || []).filter(item => item?.name)
  if (directChildren.length) return directChildren
  return getDescendantNodes(node).filter(item => item?.name)
}

const hasBusinessDrillDataset = (datasets) => (
  (datasets || []).some(dataset => Boolean(buildBusinessDrillReport(dataset)))
)

const buildBusinessDrillReportFromSpec = (dataset) => {
  const spec = dataset?.report_spec
  if (!spec || spec.version !== '2.0') return null
  const overviewChart = Array.isArray(spec.charts) ? spec.charts[0] : null
  const accordions = Array.isArray(spec.accordions) ? spec.accordions : []
  if (!overviewChart && !accordions.length) return null

  const compareLevelLabel = spec.scope?.compareLevelLabel || '下一层级'
  const detailLevelLabel = spec.scope?.detailLevelLabel || '明细层级'
  const offices = accordions.map((item) => {
    const rateKpi = (item.kpis || []).find(kpi => /率|percent|rate/i.test(kpi.label || ''))
    const chartRows = Array.isArray(item.chart?.rows) ? item.chart.rows : []
    const narrative = String(item.narrative || '').trim()
    const detailRows = buildOfficeDetailRows(item.chart)
    const drillGroups = (Array.isArray(item.drillGroups) ? item.drillGroups : [])
      .map((group) => {
        const groupRateKpi = (group.kpis || []).find(kpi => /率|percent|rate/i.test(kpi.label || ''))
        const groupRows = buildOfficeDetailRows(group.chart)
        return {
          id: group.id || `${item.id || item.title}-${group.title}`,
          name: group.title || '未命名下级节点',
          parentName: group.parentName || item.title || '',
          tone: group.tone || 'neutral',
          tag: group.tag || getRateTag(groupRateKpi?.value, 15, 10, '代表处标杆'),
          rate: toNumber(groupRateKpi?.value),
          rateLabel: groupRateKpi?.value || '-',
          progress: Math.max(0, Math.min(100, toNumber(groupRateKpi?.value) || 0)),
          childCount: groupRows.length,
          kpis: group.kpis || [],
          summary: String(group.narrative || '').trim(),
          chartText: group.detailNarrative || (groupRows.length ? `${group.title || '当前节点'}继续下钻到${group.detailLevelLabel || '业务员'}。` : ''),
          detailLevelLabel: group.detailLevelLabel || '业务员',
          detailRows: groupRows,
        }
      })
      .filter(group => group.detailRows.length > 0)
    const summaryText = narrative
      .split('\n')
      .map(line => line.trim())
      .filter(Boolean)
      .slice(0, 3)
      .join('；') || narrative
    return {
      id: item.id || item.title,
      name: item.title || '未命名节点',
      parentName: item.parentName || item.levelLabel || '',
      tone: item.tone || 'neutral',
      tag: item.tag || getRateTag(rateKpi?.value, 15, 10, '区域标杆'),
      highlight: item.highlight || '',
      rankLabel: item.rankLabel || '',
      rate: toNumber(rateKpi?.value),
      rateLabel: rateKpi?.value || '-',
      progress: Math.max(0, Math.min(100, toNumber(rateKpi?.value) || 0)),
      childCount: chartRows.length,
      kpis: item.kpis || [],
      summary: summaryText,
      chartText: item.detailNarrative || (detailRows.length ? '业务代表明细按达成率从高到低排序。' : ''),
      chartSpec: item.chart,
      detailRows,
      drillGroups,
    }
  })
  const riskCount = offices.filter(item => item.tone === 'danger').length
  const summary = Array.isArray(spec.narrative) && spec.narrative.length
    ? spec.narrative.join('；')
    : spec.sections?.find(section => section.key === 'overview')?.narrative || `本次结果覆盖 ${offices.length} 个${compareLevelLabel}。`

  return {
    dataset,
    analysisMode: spec.analysisMode || 'detail',
    focusName: spec.scope?.focusNode || '',
    isSingleFocus: Boolean(spec.scope?.focusNode && spec.analysisMode !== 'comparative'),
    kpis: (spec.kpis || []).map(item => ({
      label: item.label || item.key,
      value: item.displayValue ?? formatDisplayValue(item.value),
    })).filter(item => item.label),
    offices,
    compareLevelLabel,
    detailLevelLabel,
    officeCompareSpec: overviewChart,
    officeCompareText: spec.sections?.find(section => section.key === 'drill')?.narrative || '一行一个同层级对象，对齐展示任务、开单、缺口、达成率和进度条；展开后查看下一层级。',
    summary,
    riskTone: riskCount ? 'danger' : 'good',
    riskLabel: riskCount ? `风险 ${riskCount} 个` : '整体可控',
  }
}

const buildBusinessDrillReport = (dataset) => {
  const specReport = buildBusinessDrillReportFromSpec(dataset)
  if (specReport) return specReport

  const model = getDatasetTreeModel(dataset)
  if (!model?.flatNodes?.length) return null
  const config = model.config || getDatasetReportConfig(dataset)
  const taskMetric = getMetricDefinition(config, 'task', item => /任务|目标/i.test(item.label || item.column || ''))
  const actualMetric = getMetricDefinition(config, 'actual', item => /开单|完成|实际/i.test(item.label || item.column || ''))
  const rateMetric = getMetricDefinition(config, 'rate', item => item.format === 'percent' || /率|rate/i.test(item.label || item.column || ''))
  const remainMetric = getMetricDefinition(config, 'remain', item => /剩余|缺口|差额/i.test(item.label || item.column || ''))
  if (!rateMetric) return null

  const focusNode = findQuestionFocusNode(model.flatNodes || [])
  const isSingleFocus = Boolean(focusNode && !/对比|比较|哪个|谁更|差异|分别|各自|和.+比|跟.+比|与.+比|\bvs\b/i.test(session.state.question || query.value || ''))
  const officeNodes = getComparisonNodes(model)
    .filter(node => node?.name)

  if (!officeNodes.length) return null
  const compareLevelLabel = getLevelLabelFromNodes(officeNodes, '下一层级')
  const detailLevelLabel = getLevelLabelFromNodes(officeNodes.flatMap(getDetailNodes), '明细层级')

  const offices = officeNodes.map((office) => {
    const people = getDetailNodes(office)
    const directChildren = people.length ? people : office.children || []
    const sortedPeople = [...directChildren]
      .filter(item => item?.name)
      .sort((a, b) => (getNodeMetricValue(a, rateMetric) || 0) - (getNodeMetricValue(b, rateMetric) || 0))
    const sortedPeopleDesc = [...sortedPeople].sort((a, b) => (getNodeMetricValue(b, rateMetric) || 0) - (getNodeMetricValue(a, rateMetric) || 0))
    const rate = getNodeMetricValue(office, rateMetric)
    const tone = getRateTone(rate, 15, 10)
    const riskPeople = sortedPeople.filter(item => getRateTone(getNodeMetricValue(item, rateMetric), 20, 10) === 'danger')
    const bestPerson = sortedPeopleDesc[0]
    const worstPerson = sortedPeople[0]
    const formatPersonMetric = (person, metric) => (
      metric ? formatMetricByDefinition(getNodeMetricValue(person, metric), metric) : '-'
    )
    const describePerson = (person) => {
      if (!person) return ''
      const actualText = formatPersonMetric(person, actualMetric)
      const taskText = formatPersonMetric(person, taskMetric)
      const remainText = formatPersonMetric(person, remainMetric)
      const rateText = formatPersonMetric(person, rateMetric)
      return `${person.name}开单${actualText} / 任务${taskText}，达成率${rateText}${remainMetric ? `，剩余缺口${remainText}` : ''}`
    }
    const chartRows = sortedPeopleDesc.map(person => {
      const personRate = getNodeMetricValue(person, rateMetric) || 0
      return {
      名称: person.name,
      [rateMetric.label || rateMetric.column || '达成率']: personRate,
      [actualMetric?.label || actualMetric?.column || '完成']: getNodeMetricValue(person, actualMetric) || 0,
      [taskMetric?.label || taskMetric?.column || '任务']: getNodeMetricValue(person, taskMetric) || 0,
      ...(remainMetric ? { [remainMetric.label || remainMetric.column || '剩余']: getNodeMetricValue(person, remainMetric) || 0 } : {}),
      标签: getRateTag(personRate, 20, 10),
    }
    })
    const officeKpis = [
      taskMetric ? { label: taskMetric.label || taskMetric.column, value: formatMetricByDefinition(getNodeMetricValue(office, taskMetric), taskMetric) } : null,
      actualMetric ? { label: actualMetric.label || actualMetric.column, value: formatMetricByDefinition(getNodeMetricValue(office, actualMetric), actualMetric) } : null,
      { label: rateMetric.label || rateMetric.column || '达成率', value: formatMetricByDefinition(rate, rateMetric) },
      remainMetric ? { label: remainMetric.label || remainMetric.column, value: formatMetricByDefinition(getNodeMetricValue(office, remainMetric), remainMetric) } : null,
    ].filter(Boolean)

    return {
      id: office.id || office.name,
      name: office.name,
      parentName: office.parentName,
      tone,
      rate,
      rateLabel: formatMetricByDefinition(rate, rateMetric),
      progress: Math.max(0, Math.min(100, rate || 0)),
      childCount: sortedPeople.length,
      kpis: officeKpis,
      tag: getRateTag(rate, 15, 10, '区域标杆'),
      highlight: bestPerson ? `亮点：${bestPerson.name}达成率${formatPersonMetric(bestPerson, rateMetric)}` : '',
      rankLabel: '',
      summary: `${office.name}达成率${formatMetricByDefinition(rate, rateMetric)}，${getToneLabel(tone)}；任务${taskMetric ? formatMetricByDefinition(getNodeMetricValue(office, taskMetric), taskMetric) : '-'} / 已完成${actualMetric ? formatMetricByDefinition(getNodeMetricValue(office, actualMetric), actualMetric) : '-'}${remainMetric ? ` / 缺口${formatMetricByDefinition(getNodeMetricValue(office, remainMetric), remainMetric)}` : ''}。${bestPerson ? `亮点：${bestPerson.name}达成率${formatPersonMetric(bestPerson, rateMetric)}` : `暂无${detailLevelLabel}明细`}；${riskPeople.length ? `${riskPeople.length} 个${detailLevelLabel}低于10%风险线` : `暂无低于10%的风险${detailLevelLabel}`}。`,
      chartText: `${office.name}下钻到${detailLevelLabel}层：${bestPerson ? `最高为${describePerson(bestPerson)}` : `暂无${detailLevelLabel}明细`}；${worstPerson ? `最低为${describePerson(worstPerson)}。` : ''}`,
      chartSpec: {
        chartType: 'horizontalDrill',
        title: `${office.name}${detailLevelLabel}达成率与缺口`,
        columns: ['名称', actualMetric?.label || actualMetric?.column || '完成', taskMetric?.label || taskMetric?.column || '任务', remainMetric?.label || remainMetric?.column || '剩余', rateMetric.label || rateMetric.column || '达成率'].filter(Boolean),
        rows: chartRows,
      },
      detailRows: buildOfficeDetailRows({
        columns: ['名称', actualMetric?.label || actualMetric?.column || '完成', taskMetric?.label || taskMetric?.column || '任务', remainMetric?.label || remainMetric?.column || '剩余', rateMetric.label || rateMetric.column || '达成率'].filter(Boolean),
        rows: chartRows,
      }),
    }
  }).sort((a, b) => (b.rate || 0) - (a.rate || 0))

  const kpis = (config.metrics || []).map(metric => ({
    label: metric.label || metric.column || metric.key,
    value: formatMetricByDefinition(model.rootMetrics?.[metric.key], metric),
  })).filter(item => item.value !== '-')
  const bestOffice = offices[0]
  const worstOffice = [...offices].sort((a, b) => (a.rate || 0) - (b.rate || 0))[0]
  const riskCount = offices.filter(item => item.tone === 'danger').length
  const officeCompareRows = offices.map(office => ({
    名称: office.name,
    [actualMetric?.label || actualMetric?.column || '完成']: getNodeMetricValue(officeNodes.find(node => node.name === office.name), actualMetric) || 0,
    [taskMetric?.label || taskMetric?.column || '任务']: getNodeMetricValue(officeNodes.find(node => node.name === office.name), taskMetric) || 0,
    ...(remainMetric ? { [remainMetric.label || remainMetric.column || '剩余']: getNodeMetricValue(officeNodes.find(node => node.name === office.name), remainMetric) || 0 } : {}),
    [rateMetric.label || rateMetric.column || '达成率']: office.rate || 0,
  })).sort((a, b) => (b[rateMetric.label || rateMetric.column || '达成率'] || 0) - (a[rateMetric.label || rateMetric.column || '达成率'] || 0))
  const officeCompareSpec = {
    chartType: 'horizontalRateBar',
    title: `各${compareLevelLabel}达成率排序`,
    columns: ['名称', actualMetric?.label || actualMetric?.column || '完成', taskMetric?.label || taskMetric?.column || '任务', remainMetric?.label || remainMetric?.column || '剩余', rateMetric.label || rateMetric.column || '达成率'].filter(Boolean),
    rows: officeCompareRows,
  }
  return {
    dataset,
    analysisMode: isSingleFocus ? 'detail' : 'comparative',
    focusName: focusNode?.name || '',
    isSingleFocus,
    kpis: kpis.slice(0, 6),
    offices,
    compareLevelLabel,
    detailLevelLabel,
    officeCompareSpec,
    officeCompareText: `${bestOffice ? `${bestOffice.name}达成率最高，为${bestOffice.rateLabel}` : ''}${worstOffice ? `；${worstOffice.name}压力最大，为${worstOffice.rateLabel}` : ''}。一行一个同层级对象，对齐展示金额和进度条。`,
    summary: `本次结果覆盖 ${offices.length} 个${compareLevelLabel}。${bestOffice ? `${bestOffice.name}表现最好，达成率${bestOffice.rateLabel}` : ''}${worstOffice ? `；${worstOffice.name}当前压力最大，达成率${worstOffice.rateLabel}` : ''}。`,
    riskTone: riskCount ? 'danger' : 'good',
    riskLabel: riskCount ? `风险 ${riskCount} 个` : '整体可控',
  }
}

const getBusinessMetricCards = (dataset) => {
  const model = getDatasetTreeModel(dataset)
  if (!model?.levelSections?.length) return []
  const config = model.config || getDatasetReportConfig(dataset)
  const cards = []
  ;(config.metrics || []).forEach((metric) => {
    const value = model.rootMetrics?.[metric.key]
    if (value !== null && value !== undefined) {
      cards.push({ label: metric.label || metric.column || metric.key, value: formatMetricByDefinition(value, metric) })
    }
  })
  model.levelSections.slice(0, 2).forEach((section) => {
    cards.push({ label: `${section.levelName}数量`, value: formatDisplayValue(section.nodes.length) })
  })
  return cards.slice(0, 6)
}

const buildLayeredBusinessCharts = (dataset) => {
  const model = getDatasetTreeModel(dataset)
  if (!model?.levelSections?.length) return []
  const config = model.config || getDatasetReportConfig(dataset)
  const taskMetric = config.metrics?.find(item => item.key === 'task')
  const actualMetric = config.metrics?.find(item => item.key === 'actual')
  const rateMetric = config.metrics?.find(item => item.key === 'rate') || config.metrics?.find(item => item.format === 'percent')
  if (!rateMetric) return []

  return model.levelSections
    .map((section) => {
      const rows = section.nodes
        .map(node => ({
          名称: node.name,
          [taskMetric?.label || taskMetric?.column || '目标']: toNumber(node.raw?.[taskMetric?.column]) ?? 0,
          [actualMetric?.label || actualMetric?.column || '完成']: toNumber(node.raw?.[actualMetric?.column]) ?? 0,
          [rateMetric?.label || rateMetric?.column || '达成率']: toNumber(node.raw?.[rateMetric?.column]) ?? 0,
          signalTone: section.riskNodes.some(item => item.id === node.id) ? 'danger' : section.topNodes.some(item => item.id === node.id) ? 'good' : 'neutral',
        }))
        .filter(row => row.名称)
        .sort((a, b) => (b[rateMetric.label || rateMetric.column || '达成率'] || 0) - (a[rateMetric.label || rateMetric.column || '达成率'] || 0))
        .slice(0, 12)
      if (!rows.length) return null
      const titlePrefix = section.trackNames.length ? `${section.trackNames.join(' / ')}：` : ''
      const columns = [
        '名称',
        taskMetric?.label || taskMetric?.column,
        actualMetric?.label || actualMetric?.column,
        rateMetric?.label || rateMetric?.column,
      ].filter(Boolean)
      return {
        chartType: taskMetric && actualMetric ? 'combo' : 'bar',
        title: `${titlePrefix}${section.levelName}完成情况`,
        columns,
        rows,
      }
    })
    .filter(Boolean)
}

const inferChartSpec = (dataset) => {
  const rows = dataset?.rows || []
  if (!rows.length) return null

  const layeredCharts = buildLayeredBusinessCharts(dataset)
  if (layeredCharts.length) return layeredCharts[0]

  const labelColumn = getLabelColumn(dataset)
  const numericColumns = getNumericColumns(dataset)
  if (!labelColumn && !numericColumns.length) return null

  const firstRow = rows[0] || {}
  const nameText = `${dataset?.dataset_name || ''} ${(dataset?.analysis || '').slice(0, 80)}`

  if (rows.length === 1) {
    if (numericColumns.length > 0) {
      return {
        chartType: 'metric',
        title: dataset?.dataset_name || '关键指标',
        value: formatValueByColumn(firstRow[numericColumns[0]], numericColumns[0]),
        label: numericColumns[0],
      }
    }
    if (labelColumn) {
      return {
        chartType: 'metric',
        title: dataset?.dataset_name || '关键指标',
        value: formatDisplayValue(firstRow[labelColumn]),
        label: labelColumn,
      }
    }
  }

  if (/日期|时间/.test(labelColumn || '') && numericColumns.length > 0) {
    return {
      chartType: 'trend',
      title: '趋势组合图',
      columns: [labelColumn, ...numericColumns.slice(0, 2)],
      rows,
    }
  }

  if (/Top|TOP|股票|排名/i.test(nameText) || rows.length > 6) {
    return {
      chartType: 'bar',
      title: 'Top 结果分布',
      columns: [labelColumn, numericColumns[0]].filter(Boolean),
      rows,
    }
  }

  if (numericColumns.length > 0) {
    return {
      chartType: /城市|佣金|分布|占比/i.test(nameText) ? 'pie' : 'bar',
      title: /城市|佣金|分布|占比/i.test(nameText) ? '分类占比' : '分类对比',
      columns: [labelColumn, numericColumns[0]].filter(Boolean),
      rows,
    }
  }

  return null
}

const buildSingleRowMetricCharts = (dataset) => {
  const rows = dataset?.rows || []
  if (rows.length !== 1) return []

  const numericColumns = getNumericColumns(dataset)
  const firstRow = rows[0] || {}
  const datasetName = dataset?.dataset_name || '结果图表'
  const charts = []

  if (numericColumns.length >= 2) {
    charts.push({
      chartType: 'bar',
      title: '关键指标对比',
      columns: ['指标', '数值'],
      rows: numericColumns.slice(0, 6).map(column => ({
        指标: column,
        数值: Number(firstRow[column]) || 0,
      })),
    })
  }

  const completedKey = numericColumns.find(column => /开单|完成|达成|实际|已完成/i.test(column))
  const remainKey = numericColumns.find(column => /剩余|未完成|差额|缺口/i.test(column))
  if (completedKey && remainKey) {
    charts.push({
      chartType: 'pie',
      title: '完成与剩余结构',
      columns: ['分类', '数值'],
      rows: [
        { 分类: completedKey, 数值: Math.max(0, Number(firstRow[completedKey]) || 0) },
        { 分类: remainKey, 数值: Math.max(0, Number(firstRow[remainKey]) || 0) },
      ],
    })
  }

  return charts.map((chart, index) => ({
    key: `${dataset?.dataset_id || datasetName}-single-${index}`,
    caption: index === 0 ? '核心图表' : `衍生图表 ${index}`,
    dataset,
    metricCards: getMetricCards(dataset),
    chartSpec: chart,
  }))
}

const hasChartRows = (chartSpec) => Array.isArray(chartSpec?.rows) && chartSpec.rows.length > 0

const getReportSpecCharts = (dataset) => (
  Array.isArray(dataset?.report_spec?.charts)
    ? dataset.report_spec.charts.filter(Boolean)
    : []
)

const buildReportTableBlocks = (datasets = []) => {
  return (datasets || [])
    .filter(dataset => Array.isArray(dataset?.rows) && dataset.rows.length > 0 && Array.isArray(dataset?.columns) && dataset.columns.length > 0)
    .slice(0, 3)
    .map((dataset, index) => {
      const labelColumn = getLabelColumn(dataset)
      const numericColumns = getNumericColumns(dataset)
      const prioritizedColumns = [
        labelColumn,
        ...numericColumns,
        ...(dataset.columns || []),
      ].filter(Boolean)
      const columns = Array.from(new Set(prioritizedColumns)).slice(0, 5)
      const title = dataset.rows.length > 6
        ? `${dataset.dataset_name} 结果明细表`
        : `${dataset.dataset_name} 关键结果表`
      const description = dataset.rows.length > 6
        ? '补充展示图表对应的原始数据明细，方便继续核对与下钻。'
        : '提炼当前报告里的关键字段与结果值，便于快速核对。'

      return {
        key: `${dataset.dataset_id || index}-${dataset.dataset_name || 'table'}`,
        dataset,
        title,
        description,
        columns,
        rows: dataset.rows,
      }
    })
}

const resultPreviews = computed(() => (
  datasetResults.value.slice(0, 4).map((dataset, index) => {
    const specCharts = getReportSpecCharts(dataset)
    const derivedCharts = [
      ...specCharts.slice(1),
      ...buildLayeredBusinessCharts(dataset).slice(1),
      ...buildSingleRowMetricCharts(dataset).map(item => item.chartSpec),
    ]
      .filter(Boolean)

    return {
      key: `${dataset.dataset_id || index}-${dataset.dataset_name || 'dataset'}`,
      caption: index === 0 ? '主结果视图' : '结果视图',
      dataset,
      metricCards: getMetricCards(dataset),
      chartSpec: specCharts[0] || inferChartSpec(dataset),
      extraCharts: derivedCharts,
    }
  })
))

const sideReportCharts = computed(() => (
  latestDatasets.value
    .slice(0, 3)
    .flatMap((dataset, datasetIndex) => {
      const specCharts = getReportSpecCharts(dataset)
      const derivedCharts = specCharts.length
        ? specCharts
        : [
            inferChartSpec(dataset),
            ...buildLayeredBusinessCharts(dataset),
            ...buildSingleRowMetricCharts(dataset).map(item => item.chartSpec),
          ].filter(Boolean)
      return derivedCharts.slice(0, 3).map((chartSpec, chartIndex) => ({
        key: `side-report-chart-${dataset.dataset_id || datasetIndex}-${chartIndex}`,
        caption: chartSpec.title || `图表 ${chartIndex + 1}`,
        dataset,
        chartSpec,
      }))
    })
))

const reportDialogCharts = computed(() => {
  const sourceItems = reportViewerVisible.value
    ? reportViewerDatasets.value.slice(0, 4).flatMap((dataset, index) => {
        const primary = {
          key: `${dataset.dataset_id || index}-${dataset.dataset_name || 'dataset'}`,
          caption: index === 0 ? '主结果视图' : '结果视图',
          dataset,
          metricCards: getMetricCards(dataset),
          chartSpec: inferChartSpec(dataset),
        }
        const layered = buildLayeredBusinessCharts(dataset).slice(1).map((chartSpec, chartIndex) => ({
          key: `${dataset.dataset_id || index}-layer-${chartIndex}`,
          caption: `层级图表 ${chartIndex + 2}`,
          dataset,
          metricCards: getMetricCards(dataset),
          chartSpec,
        }))
        return [primary, ...layered, ...buildSingleRowMetricCharts(dataset)]
      })
    : resultPreviews.value.flatMap(item => (
        item?.dataset ? [item, ...buildSingleRowMetricCharts(item.dataset)] : [item]
      ))

  const deduped = []
  const seen = new Set()
  sourceItems.forEach((item) => {
    if (!item?.chartSpec) return
    const key = `${item.key}-${item.chartSpec.chartType}-${item.chartSpec.title || ''}`
    if (seen.has(key)) return
    seen.add(key)
    deduped.push(item)
  })
  return deduped
})

const reportDialogMetricCards = computed(() => {
  const source = reportViewerVisible.value ? reportViewerDatasets.value : latestDatasets.value
  const drillReport = source.map(buildBusinessDrillReport).find(Boolean)
  if (drillReport?.kpis?.length) {
    const cards = drillReport.isSingleFocus
      ? drillReport.kpis.slice(0, 4).map(item => ({
          label: item.label || item.key || '',
          value: item.value ?? item.displayValue ?? formatDisplayValue(item.value),
        }))
      : decorateMetricCards(drillReport.kpis, drillReport.offices).slice(0, 8)
    return drillReport.isSingleFocus ? enrichSingleOrgMetricCards(cards, drillReport) : cards
  }
  return (
    (reportViewerVisible.value
      ? (reportViewerDatasets.value[0] ? getMetricCards(reportViewerDatasets.value[0]) : [])
      : resultPreviews.value[0]?.metricCards
    ) || []
  )
})

const reportTableBlocks = computed(() => (
  buildReportTableBlocks(reportViewerVisible.value ? reportViewerDatasets.value : latestDatasets.value)
))

const businessDrillReport = computed(() => (
  latestDatasets.value.map(buildBusinessDrillReport).find(Boolean) || null
))

const sideBusinessMetricCards = computed(() => (
  businessDrillReport.value
    ? (
        businessDrillReport.value.isSingleFocus
          ? enrichSingleOrgMetricCards(
              businessDrillReport.value.kpis.slice(0, 4).map(item => ({
                label: item.label || item.key || '',
                value: item.value ?? item.displayValue ?? formatDisplayValue(item.value),
              })),
              businessDrillReport.value,
            )
          : decorateMetricCards(businessDrillReport.value.kpis, businessDrillReport.value.offices).slice(0, 8)
      )
    : []
))

const dialogBusinessDrillReport = computed(() => {
  const source = reportViewerVisible.value ? reportViewerDatasets.value : latestDatasets.value
  return source.map(buildBusinessDrillReport).find(Boolean) || null
})

const dialogCoreConclusion = computed(() => {
  const report = dialogBusinessDrillReport.value
  const offices = report?.offices || []
  if (offices.length >= 2) {
    const ranked = [...offices].filter(item => item.rate !== null).sort((a, b) => (b.rate || 0) - (a.rate || 0))
    const leader = ranked[0]
    const follower = ranked[1]
    if (leader && follower) {
      const diff = Math.abs((leader.rate || 0) - (follower.rate || 0)).toFixed(2).replace(/\.?0+$/, '')
      return `${leader.name}当前领先${follower.name}，达成率高${diff}个百分点；建议继续下钻代表处，定位差距来自哪些区域单元。`
    }
  }
  const reportText = String(reportViewerReport.value || latestReport.value || '').trim()
  const match = reportText.match(/(?:核心结论|结论)[:：]?\s*([^。\n]{12,120}。?)/)
  if (match?.[1]) return match[1].trim()
  return report?.summary || ''
})

const getOfficeMetricText = (office, type) => getOfficeKpiLabel(office, type) || '-'

const buildComparisonMetricTable = (offices = []) => {
  if (!offices.length) return ''
  const displayOffices = offices.length <= 4
    ? offices
    : [offices[0], offices[1], offices[offices.length - 2], offices[offices.length - 1]]
        .filter((item, index, list) => item && list.findIndex(row => row.name === item.name) === index)
  const header = ['指标', ...displayOffices.map(item => item.name)]
  const rows = [
    ['总任务金额', ...displayOffices.map(item => getOfficeMetricText(item, 'task'))],
    ['已完成金额', ...displayOffices.map(item => getOfficeMetricText(item, 'actual'))],
    ['整体达成率', ...displayOffices.map(item => getOfficeMetricText(item, 'rate'))],
    ['剩余缺口金额', ...displayOffices.map(item => getOfficeMetricText(item, 'remain'))],
  ]
  const table = [
    `| ${header.join(' | ')} |`,
    `| ${header.map(() => '---').join(' | ')} |`,
    ...rows.map(row => `| ${row.join(' | ')} |`),
  ].join('\n')
  const levelLabel = dialogBusinessDrillReport.value?.compareLevelLabel || businessDrillReport.value?.compareLevelLabel || '对象'
  const note = offices.length > 4 ? `\n\n本次对象较多，表内展示最高/次高/次低/最低摘要，完整 ${offices.length} 个${levelLabel}见下方对比分析表。` : ''
  return `${table}${note}`
}

const buildRankMetricTable = (items = [], title = '对象') => {
  if (!items.length) return ''
  return [
    `| ${title} | 任务 | 完成 | 达成率 | 缺口 |`,
    '| --- | ---: | ---: | ---: | ---: |',
    ...items.map(item => (
      `| ${item.name} | ${getOfficeMetricText(item, 'task')} | ${getOfficeMetricText(item, 'actual')} | ${getOfficeMetricText(item, 'rate')} | ${getOfficeMetricText(item, 'remain')} |`
    )),
  ].join('\n')
}

const getRateDistribution = (items = []) => {
  const source = items.filter(item => item?.rate !== null && item?.rate !== undefined)
  const total = source.length || 0
  const buckets = [
    { label: '20%以下', count: 0, matcher: rate => rate < 20 },
    { label: '20%-40%', count: 0, matcher: rate => rate >= 20 && rate < 40 },
    { label: '40%以上', count: 0, matcher: rate => rate >= 40 },
  ]
  source.forEach((item) => {
    const bucket = buckets.find(part => part.matcher(Number(item.rate)))
    if (bucket) bucket.count += 1
  })
  return buckets.map(item => ({
    ...item,
    pct: total ? `${Math.round(item.count / total * 100)}%` : '0%',
  }))
}

const buildRateDistributionText = (items = []) => (
  getRateDistribution(items).map(item => `${item.label}：${item.count}个（${item.pct}）`).join('；')
)

const getTrendProgressText = (report) => {
  const kpis = Array.isArray(report?.kpis) ? report.kpis : []
  const trendItems = kpis
    .filter(item => /同比|环比|较上期|较同期|增长|变化/i.test(`${item?.label || ''}${item?.key || ''}`))
    .map(item => `${item.label || item.key}：${item.value ?? item.displayValue ?? '-'}`)
  if (trendItems.length) return trendItems.join('；')
  return '本次 SQL 结果未返回同比/环比字段，当前以达成率、缺口和分布判断进度；建议后续在数据集中补充同期/上期指标列。'
}

const getPressureDiagnosis = (item, detailLabel = '下级节点') => {
  if (!item) return ''
  const task = toNumber(getOfficeMetricText(item, 'task'))
  const actual = toNumber(getOfficeMetricText(item, 'actual'))
  const remain = toNumber(getOfficeMetricText(item, 'remain'))
  const rate = toNumber(getOfficeMetricText(item, 'rate'))
  const detailCount = Number(item.childCount || item.detailRows?.length || 0)
  const signals = []
  if (task !== null && remain !== null && task > 0 && remain / task >= 0.5) {
    signals.push('任务体量或缺口压力偏大')
  }
  if (rate !== null && rate < 20) {
    signals.push('整体转化进度偏慢')
  }
  if (actual !== null && task !== null && task > 0 && actual / task < 0.25) {
    signals.push('客户转化或项目落单不足')
  }
  if (detailCount > 0) {
    signals.push(`需继续下钻${detailCount}个${detailLabel}确认项目阶段`)
  }
  return signals.length
    ? `${item.name}可能由${signals.join('、')}共同造成，优先用下级明细验证。`
    : `${item.name}需要补充项目阶段、客户转化和资源投入字段后再做归因。`
}

const buildBusinessNarrativeSections = (report) => {
  const offices = report?.offices || []
  if (!report || !offices.length) return []
  const ranked = [...offices].filter(item => item.rate !== null).sort((a, b) => (b.rate || 0) - (a.rate || 0))
  const best = ranked[0] || offices[0]
  const worst = ranked[ranked.length - 1] || offices[offices.length - 1]
  const top3 = ranked.slice(0, 3)
  const bottom3 = [...ranked].reverse().slice(0, 3)
  const diff = best?.rate !== null && worst?.rate !== null
    ? Math.abs((best.rate || 0) - (worst.rate || 0)).toFixed(2).replace(/\.?0+$/, '')
    : ''
  const visibleNames = offices.length <= 4
    ? offices.map(item => item.name).join('、')
    : `${offices.length} 个${report.compareLevelLabel}`
  const riskOffices = offices.filter(item => item.tone === 'danger')
  const riskText = riskOffices.length
    ? `${riskOffices.slice(0, 3).map(item => item.name).join('、')}处于低达成风险${riskOffices.length > 3 ? `等 ${riskOffices.length} 个对象` : ''}`
    : '当前同层级对象暂无低达成风险'
  const distributionText = buildRateDistributionText(offices)
  const trendText = getTrendProgressText(report)
  const topBottomTable = [
    'Top3：',
    buildRankMetricTable(top3, report.compareLevelLabel || '对象'),
    '',
    '末3：',
    buildRankMetricTable(bottom3, report.compareLevelLabel || '对象'),
  ].filter(Boolean).join('\n\n')

  if (report.isSingleFocus) {
    const focusName = report.focusName || '当前组织'
    const counts = getSingleOrgCounts(report)
    const rankContext = getSingleOrgRankContext(report)
    const overallRate = getReportKpiText(report, 'rate')
    const tableRows = offices.length <= 6
      ? offices
      : [
          ...ranked.slice(0, 3),
          ...ranked.slice(-2),
        ].filter((item, index, list) => item && list.findIndex(row => row.name === item.name) === index)
    const comparisonRows = tableRows.map((office) => {
      const diffValue = office.rate !== null && toNumber(overallRate) !== null ? (office.rate - toNumber(overallRate)) : null
      const diffText = diffValue === null
        ? '-'
        : `${diffValue >= 0 ? '高于大盘' : '低于大盘'} ${Math.abs(diffValue).toFixed(2).replace(/\.?0+$/, '')}pct`
      return `| ${office.name} | ${office.rateLabel} | ${diffText} | ${office.tag || '-'} |`
    })
    const comparisonTable = [
      `数据为${focusName}下${counts.directCount}个${counts.directLabel}摘要，完整明细见下方附表。`,
      '',
      '| 对象 | 达成率 | 与大盘对比 | 标签 |',
      '| --- | --- | --- | --- |',
      ...comparisonRows,
    ].join('\n')
    return [
      {
        title: `一、${focusName}核心结论`,
        body: [
          `1. 当前进度：${getSingleOrgConclusion(report)}`,
          rankContext.diff
            ? `2. 头尾差异：${rankContext.best.name}达成率${rankContext.best.rateLabel}领跑，${rankContext.worst.name}达成率${rankContext.worst.rateLabel}承压，首尾差距${rankContext.diff}个百分点。`
            : report.summary,
          `3. 风险信号：${riskText}；${distributionText}。`,
        ].filter(Boolean).slice(0, 3).join('\n'),
      },
      {
        title: `二、${focusName}关键指标与二级拆解`,
        body: [
          `事业部/主体大盘：总任务金额 ${getReportKpiText(report, 'task')}，年度开单金额 ${getReportKpiText(report, 'actual')}，整体达成率 ${overallRate}，剩余任务金额 ${getReportKpiText(report, 'remain')}。`,
          `同比/环比进度：${trendText}`,
          `达成率分布：${distributionText}`,
          comparisonTable,
        ].filter(Boolean).join('\n\n'),
      },
      {
        title: `三、${counts.directLabel}Top3/末3对比`,
        body: topBottomTable,
      },
      {
        title: '四、结构看板与问题溯源',
        body: [
          `标杆分析：${rankContext.best ? `${rankContext.best.name}是当前标杆，任务 ${getOfficeMetricText(rankContext.best, 'task')}，完成 ${getOfficeMetricText(rankContext.best, 'actual')}，达成率 ${rankContext.best.rateLabel}；建议复盘其目标拆解、客户推进和项目转化节奏。` : '当前未识别稳定标杆。'}`,
          `压力节点：${rankContext.worst ? getPressureDiagnosis(rankContext.worst, counts.detailLabel) : '当前未识别明显压力节点。'}`,
          `分层归因：事业部层面关注头部贡献与尾部拖累是否过度分化；${counts.directLabel}层面重点比较标杆和末位在任务体量、项目阶段、客户转化和资源投入上的差异。`,
        ].join('\n\n'),
      },
      {
        title: '五、动作落地',
        body: [
          rankContext.best ? `标杆经验推广：由${rankContext.best.name}输出可复制动作清单，两周内同步给达成率低于20%的${counts.directLabel}。` : '',
          rankContext.worst ? `压力节点帮扶：围绕${rankContext.worst.name}建立下钻清单，责任方为业务负责人+经营分析；输出项目阶段、客户转化、缺口金额三张明细表。` : '',
          `整体优化：按${counts.directLabel}建立红黄绿看板，低于20%周度复盘，20%-40%专项推进，高于40%沉淀打法并横向复制。`,
        ].filter(Boolean).join('\n'),
      },
    ]
  }
  return [
    {
      title: '一、核心结论',
      body: [
        diff
          ? `1. 当前对比覆盖${visibleNames}，${best.name}达成率${best.rateLabel}领先，${worst.name}达成率${worst.rateLabel}承压，首尾差${diff}个百分点。`
          : `1. ${report.summary}`,
        `2. 头部/尾部差异：Top3为${top3.map(item => `${item.name}(${item.rateLabel})`).join('、') || '暂无'}；末3为${bottom3.map(item => `${item.name}(${item.rateLabel})`).join('、') || '暂无'}。`,
        `3. 核心风险信号：${riskText}；${distributionText}。`,
      ].join('\n'),
    },
    {
      title: '二、关键指标与分层拆解',
      body: [
        buildComparisonMetricTable(offices),
        `同比/环比进度：${trendText}`,
        `分布看板：${distributionText}`,
      ].join('\n\n'),
    },
    {
      title: `三、${report.compareLevelLabel}Top3/末3对比`,
      body: topBottomTable,
    },
    {
      title: '四、结构看板与问题溯源',
      body: [
        `标杆分析：${best.name}任务 ${getOfficeMetricText(best, 'task')}，完成 ${getOfficeMetricText(best, 'actual')}，达成率 ${best.rateLabel}；优先复盘其目标拆解、客户推进和项目转化动作。`,
        `压力节点：${getPressureDiagnosis(worst, report.detailLevelLabel)}`,
        `分层归因：事业部层面看头部贡献、尾部拖累和任务分配合理性；${report.compareLevelLabel}层面看任务体量、项目阶段、客户转化和资源投入差异。`,
      ].join('\n\n'),
    },
    {
      title: '五、动作落地',
      body: [
        `标杆经验推广：由${best.name}沉淀关键动作，覆盖${bottom3.map(item => item.name).join('、') || '低达成节点'}，两周内完成打法复盘和任务拆解。`,
        `压力节点帮扶：围绕${worst.name}下钻${report.detailLevelLabel}，责任方为业务负责人+经营分析；输出项目阶段、客户转化、缺口金额三类问题清单。`,
        `整体优化：按达成率分布配置资源，低于20%节点进入周度专项，20%-40%节点做过程纠偏，高于40%节点提炼可复制打法。`,
      ].join('\n'),
    },
  ]
}

const reportOverviewTitle = computed(() => {
  const sourceDatasets = reportViewerVisible.value ? reportViewerDatasets.value : latestDatasets.value
  const drillReport = sourceDatasets.map(buildBusinessDrillReport).find(Boolean)
  return drillReport?.isSingleFocus
    ? `${drillReport.focusName || '当前组织'}业绩核心结论`
    : '分析摘要'
})

const reportSummaryBullets = computed(() => {
  const bullets = []
  const sourceDatasets = reportViewerVisible.value ? reportViewerDatasets.value : latestDatasets.value
  const primary = sourceDatasets[0]
  const drillReport = sourceDatasets.map(buildBusinessDrillReport).find(Boolean)
  const names = sourceDatasets.map(item => item.dataset_name).filter(Boolean)
  if (drillReport?.isSingleFocus) {
    const counts = getSingleOrgCounts(drillReport)
    const rankContext = getSingleOrgRankContext(drillReport)
    bullets.push(getSingleOrgConclusion(drillReport))
    bullets.push(`覆盖范围：${counts.directCount}个${counts.directLabel}${counts.detailCount ? `，${counts.detailCount}个${counts.detailLabel}` : ''}。`)
    if (rankContext.best && rankContext.worst && rankContext.diff) {
      bullets.push(`${rankContext.best.name}达成率最高，为${rankContext.best.rateLabel}；${rankContext.worst.name}压力最大，为${rankContext.worst.rateLabel}，首尾差距${rankContext.diff}个百分点。`)
    }
    if (names.length) bullets.push(`命中数据集：${names.join('、')}`)
    return bullets.filter(Boolean)
  }
  if (drillReport?.offices?.length) {
    const ranked = [...drillReport.offices]
      .filter(item => item.rate !== null && item.rate !== undefined)
      .sort((a, b) => (b.rate || 0) - (a.rate || 0))
    const best = ranked[0] || drillReport.offices[0]
    const worst = ranked[ranked.length - 1] || drillReport.offices[drillReport.offices.length - 1]
    const gap = best?.rate !== null && worst?.rate !== null && best?.name !== worst?.name
      ? Math.abs((best.rate || 0) - (worst.rate || 0)).toFixed(2).replace(/\.?0+$/, '')
      : ''
    const riskCount = drillReport.offices.filter(item => item.tone === 'danger').length
    bullets.push(`当前覆盖 ${drillReport.offices.length} 个${drillReport.compareLevelLabel}，先横向比较再下钻${drillReport.detailLevelLabel}。`)
    if (best && worst) {
      bullets.push(gap
        ? `${best.name}达成率${best.rateLabel}领先，${worst.name}达成率${worst.rateLabel}承压，首尾差${gap}个百分点。`
        : `${best.name}表现靠前，${worst.name}需要优先下钻复核。`)
    }
    bullets.push(riskCount
      ? `风险信号：${riskCount}个${drillReport.compareLevelLabel}处于低达成风险，需按缺口和项目阶段拆解责任。`
      : `风险信号：暂无明显低达成${drillReport.compareLevelLabel}，继续保持周度过程跟踪。`)
    return bullets.filter(Boolean).slice(0, 3)
  }
  if (session.state.question) bullets.push(`原始问题：${session.state.question}`)
  bullets.push(`报告模板：${reportSceneTemplateLabel.value}`)
  if (drillReport) {
    const nextLevelText = drillReport.offices?.some(item => item.drillGroups?.length)
      ? `，再从${drillReport.detailLevelLabel}继续下钻到业务员`
      : ''
    bullets.push(`分析口径：先横向比较 ${drillReport.offices.length} 个${drillReport.compareLevelLabel}，再纵向展开${drillReport.detailLevelLabel}${nextLevelText}。`)
  }
  if (names.length) bullets.push(`命中数据集：${names.join('、')}`)
  if (sourceDatasets.length) {
    const totalRows = sourceDatasets.reduce((sum, item) => sum + Number(item?.row_count || item?.rows?.length || 0), 0)
    bullets.push(`数据结果：共返回 ${sourceDatasets.length} 份结果，累计 ${totalRows} 行数据。`)
  }
  const reviewSummary = primary?.agent3_review?.review_summary
  if (reviewSummary) bullets.push(`SQL 复核结论：${reviewSummary}`)
  const sample = primary?.rows?.[0]
  const columns = primary?.columns || []
  if (!drillReport && sample && columns.length) {
    const snippet = columns.slice(0, 3).map(column => `${column}=${sample[column]}`).join('；')
    if (snippet) bullets.push(`样例结果：${snippet}`)
  }
  if (!bullets.length && (reportViewerReport.value || latestReport.value)) {
    bullets.push('本轮报告已生成，可继续查看下方图表分析与完整解读。')
  }
  return bullets
})

const reportNarrativeSections = computed(() => {
  const raw = String((reportViewerVisible.value ? reportViewerReport.value : latestReport.value) || '').trim()
  if (!raw) return []

  const sections = splitReportSections(raw)

  if (!sections.length) {
    return [{
      title: reportViewerTitle.value || sideReportHeading.value,
      body: normalizeReportMarkdown(raw),
    }]
  }

  return sections
})

const businessNarrativeSections = computed(() => {
  const generated = buildBusinessNarrativeSections(dialogBusinessDrillReport.value || businessDrillReport.value)
  if (generated.length) return generated
  return reportNarrativeSections.value
    .filter(section => !/^业绩分析报告$/.test(section.title))
    .slice(0, 4)
})

// 方法
const renderMd = (text) => marked.parse(text || '')
const renderReportMd = (text) => marked.parse(normalizeReportMarkdown(text))

const normalizeReportMarkdown = (text) => (
  String(text || '')
    .replace(/\r\n/g, '\n')
    .replace(/^#\s+/gm, '## ')
    .replace(/\n---\n/g, '\n\n')
    .replace(/[ \t]+•[ \t]*/g, '\n- ')
    .replace(/^•[ \t]*/gm, '- ')
    .replace(/([。！？；;])\s*(?=##|###)/g, '$1\n\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
)

const splitReportSections = (text) => {
  const normalized = normalizeReportMarkdown(text).replace(/^##\s*业绩分析报告\s*/i, '').trim()
  if (!normalized) return []

  const headingPattern = /^#{2,3}\s+(.+)$/gm
  const matches = Array.from(normalized.matchAll(headingPattern))
  if (!matches.length) {
    return [{ title: '核心结论', body: normalized }]
  }

  const sections = []
  const leading = normalized.slice(0, matches[0].index).trim()
  if (leading) sections.push({ title: '核心结论', body: leading })

  matches.forEach((match, index) => {
    const title = String(match[1] || '').trim()
    const start = Number(match.index || 0) + match[0].length
    const end = index + 1 < matches.length ? Number(matches[index + 1].index || normalized.length) : normalized.length
    const body = normalized.slice(start, end).trim()
    if (!title || /^业绩分析报告$/.test(title)) return
    if (body) sections.push({ title, body })
  })

  return sections
}

const togglePanel = () => { showPanel.value = !showPanel.value }
const toggleThinking = (id) => { thinkingOpen[id] = !thinkingOpen[id] }
const toggleLog = (i) => { logOpen[i] = !logOpen[i] }
const openDetailPanel = () => {
  showPanel.value = true
  scrollPanelToReportTop()
}

const scrollPanelToReportTop = () => nextTick(() => {
  const panel = panelRef.value
  const report = sideReportRef.value
  const reportHead = sideReportHeadRef.value
  if (!panel) return
  if (!report) {
    panel.scrollTo({ top: 0, behavior: 'auto' })
    return
  }
  const target = reportHead || report
  const panelRect = panel.getBoundingClientRect()
  const targetRect = target.getBoundingClientRect()
  const top = panel.scrollTop + targetRect.top - panelRect.top - 12
  panel.scrollTo({ top: Math.max(0, top), behavior: 'auto' })
})

const clearExecutionPanelState = () => {
  Object.keys(logOpen).forEach(k => delete logOpen[k])
  timelineVersion.value += 1
  nextTick(() => {
    if (panelRef.value) panelRef.value.scrollTop = 0
  })
}

const clearChatUiState = () => {
  Object.keys(thinkingOpen).forEach(k => delete thinkingOpen[k])
  Object.keys(confirmationDrafts).forEach(k => delete confirmationDrafts[k])
  Object.keys(confirmationSubmitting).forEach(k => delete confirmationSubmitting[k])
  Object.keys(officeDrillOpen).forEach(k => delete officeDrillOpen[k])
  reportViewerVisible.value = false
  chartViewerVisible.value = false
  elapsed.value = 0
  stopTimer()
  clearExecutionPanelState()
}

const isUiEventLike = (value) => Boolean(
  value
  && typeof value === 'object'
  && (
    typeof value.preventDefault === 'function'
    || typeof value.stopPropagation === 'function'
    || value.type
  )
)

const openReportViewer = (report = latestReport.value, title = sideReportHeading.value, datasetsForReport = latestDatasets.value) => {
  if (isUiEventLike(report)) {
    report = latestReport.value
    title = sideReportHeading.value
    datasetsForReport = latestDatasets.value
  }
  if (!report) {
    ElMessage.warning('当前还没有可查看的完整报告')
    return
  }
  reportViewerReport.value = report
  reportViewerTitle.value = normalizeReportTitle(title)
  reportViewerDatasets.value = Array.isArray(datasetsForReport) ? datasetsForReport : []
  reportDialogFullscreen.value = false
  reportViewerVisible.value = true
}
const openFullScreenReport = () => {
  openReportViewer(latestReport.value, sideReportHeading.value, latestDatasets.value)
  reportDialogFullscreen.value = true
}
const openChartViewer = (spec, title = '图表预览') => {
  if (!spec) return
  chartViewerSpec.value = spec
  chartViewerTitle.value = title
  chartViewerMode.value = 'chart'
  chartViewerVisible.value = true
}

const isOfficeExpanded = (id) => officeDrillOpen[String(id)] === true
const toggleOfficeDrill = (id) => {
  const key = String(id)
  officeDrillOpen[key] = !isOfficeExpanded(key)
  nextTick(() => {
    window.setTimeout(() => {
      Object.values(document.querySelectorAll('.sa-office-chart')).forEach((el) => {
        const chart = echarts.getInstanceByDom(el)
        if (chart) chart.resize()
      })
    }, 40)
  })
}

const chartViewerTableRows = computed(() => (
  Array.isArray(chartViewerSpec.value?.rows) ? chartViewerSpec.value.rows : []
))

const chartViewerTableColumns = computed(() => (
  Array.isArray(chartViewerSpec.value?.columns) ? chartViewerSpec.value.columns : []
))

const chartViewerHasTable = computed(() => (
  chartViewerTableRows.value.length > 0 && chartViewerTableColumns.value.length > 0
))

const getPlanSteps = (msg) => {
  const route = msg.data?.route
  if (!route) return []
  const text = typeof route === 'string' ? route : (route.route_desc || JSON.stringify(route))
  return text.split('\n').filter(l => l.trim().match(/^步骤\d|^\d+[\.、]/)).map(s => s.replace(/^(步骤\d+[:：]?|\d+[\.、\s]*)/i, '').trim()).filter(Boolean)
}

const getThinkingSteps = (msg) => {
  const mapStatus = (status) => ({
    success: 'completed',
    completed: 'completed',
    running: 'running',
    pending: 'pending',
    warning: 'warning',
    error: 'error',
  }[status] || 'completed')

  const toStep = (step) => ({
    text: step?.text || step?.title || step?.detail || '执行步骤',
    detail: step?.detail && step?.detail !== step?.title ? step.detail : '',
    status: mapStatus(step?.status),
  })

  if (msg.loading) return session.state.logs.map(toStep)
  if (!msg.data) return []

  const isCurrentResult =
    msg.data?.question &&
    session.state.question &&
    msg.data.question === session.state.question &&
    session.state.logs.length > 0

  if (isCurrentResult) {
    return session.state.logs.map((step) => ({
      text: step?.title || step?.summary || '执行步骤',
      detail: step?.summary || step?.detailLines?.[0] || '',
      status: mapStatus(step?.status),
      statusText: step?.status === 'warning' ? '待确认' : undefined,
    }))
  }

  const steps = []
  if (msg.data.route) {
    steps.push({
      text: '已完成问题理解与执行规划',
      detail: '系统已经确定查询路径与分析重点。',
      status: 'completed',
    })
  }
  ;(msg.data.dataset_results || []).forEach((r) => {
    steps.push({
      text: `已完成数据检索 ${r.dataset_name || '目标数据集'}`,
      detail: r.rows?.length ? `已返回 ${r.rows.length} 行结果数据。` : '已拿到可分析的数据结果。',
      status: 'completed',
    })
  })
  if (msg.data.dataset_results?.[0]?.analysis) {
    steps.push({
      text: '已生成经营分析报告',
      detail: '报告摘要已经同步写入左侧回复区与右侧结果区。',
      status: 'completed',
    })
  }
  if (msg.data.requires_confirmation) {
    steps.push({
      text: '等待确认统计口径',
      detail: msg.data.confirmation_question || '需要先确认业务口径再继续执行。',
      status: 'warning',
    })
  }
  if (msg.data.error) {
    steps.push({
      text: '执行过程中发生异常',
      detail: msg.data.error,
      status: 'error',
    })
  }
  return steps
}

const isCurrentSessionMessage = (msg) => {
  return Boolean(
    msg?.data?.question &&
    session.state.question &&
    msg.data.question === session.state.question &&
    session.state.logs.length > 0
  )
}

const latestAiMessage = computed(() => (
  [...messages].reverse().find(item => item?.role === 'ai') || null
))

const isLatestAiMessage = (msg) => latestAiMessage.value?.id === msg?.id

const syncPendingConfirmationMessage = () => {
  const result = session.state.result
  if (session.state.status !== 'waiting_confirmation' || !result?.requires_confirmation) return

  const msg = latestAiMessage.value
  if (!msg || msg.role !== 'ai') return
  if (msg.data?.requires_confirmation) return
  if (!msg.loading && msg.data && !msg.data.aborted) return

  msg.loading = false
  msg.data = result
  thinkingOpen[msg.id] = false
  if (!(msg.id in confirmationDrafts)) confirmationDrafts[msg.id] = ''
  stopTimer()
  scheduleChatScroll(36, 'smooth')
}

const shouldShowLiveFeed = (msg) => {
  if (msg?.loading) return true
  if (!session.state.logs.length) return false
  if (msg?.data?.requires_confirmation) return false
  return Boolean(
    isCurrentSessionMessage(msg) ||
    (isLatestAiMessage(msg) && ['completed', 'error'].includes(session.state.status))
  )
}

const shouldShowThinkingCard = (msg) => {
  if (msg?.loading) return !session.state.logs.length
  return false
}

const shouldShowConfirmationCard = (msg) => Boolean(
  msg?.data?.requires_confirmation && !confirmationSubmitting[msg.id]
)

const shouldShowConfirmationSubmitted = (msg) => Boolean(
  msg?.data?.requires_confirmation && confirmationSubmitting[msg.id] && !msg?.loading
)

const isMessageExecutionComplete = (msg) => {
  if (!msg?.data || msg?.loading || msg?.data?.error || msg?.data?.requires_confirmation) return false
  if (!isCurrentSessionMessage(msg)) return true
  return session.state.status === 'completed'
}

const shouldShowResultHandoff = (msg) => {
  return Boolean(
    isMessageExecutionComplete(msg) &&
    isCurrentSessionMessage(msg) &&
    (getReport(msg) || getPrimaryDataset(msg))
  )
}

const shouldShowResultChain = (msg) => Boolean(
  isMessageExecutionComplete(msg) &&
  (getReport(msg) || getPrimaryDataset(msg) || (msg.data && !msg.data.error))
)

const getDatasets = (msg) => (
  Array.isArray(msg?.data?.dataset_results) ? msg.data.dataset_results : []
)
const getReport = (msg) => mergeDatasetReports(getDatasets(msg))
const getPrimaryDataset = (msg) => buildAggregateDataset(getDatasets(msg))
const getResultTitle = (msg) => {
  const raw = msg.data?.question || session.state.question || '本月公司经营表现分析'
  return raw.length > 20 ? `${raw.slice(0, 20)}...` : raw
}

const formatElapsedLabel = (seconds) => {
  const totalSeconds = Math.max(0, Math.round(Number(seconds) || 0))
  const minutes = Math.floor(totalSeconds / 60)
  const remain = totalSeconds % 60
  if (minutes <= 0) return `${remain}s`
  return `${minutes}m ${remain}s`
}

const getMessageElapsedLabel = (msg) => {
  if (msg?.loading && isCurrentSessionMessage(msg)) {
    return formatElapsedLabel(elapsed.value)
  }
  const totalDuration = Number(msg?.data?.total_duration || 0)
  if (totalDuration > 0) {
    return formatElapsedLabel(totalDuration > 120 ? totalDuration / 1000 : totalDuration)
  }
  return ''
}

const getVisualPreviews = (msg) => (
  hasBusinessDrillDataset(getDatasets(msg)) ? [] : getDatasets(msg)
    .slice(0, 3)
    .map((dataset, index) => ({
      key: `${dataset.dataset_id || index}-${dataset.dataset_name || 'dataset'}`,
      dataset,
      chartSpec: inferChartSpec(dataset),
    }))
    .filter(item => item.chartSpec)
)

const focusComposer = (selectAll = false) => nextTick(() => {
  const textarea = document.querySelector('.sa-textarea')
  if (!(textarea instanceof HTMLTextAreaElement)) return
  textarea.focus()
  const end = textarea.value.length
  textarea.setSelectionRange(selectAll ? 0 : end, end)
})

const writeClipboard = async (text) => {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', 'readonly')
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  document.body.removeChild(textarea)
}

const copyQuestion = async (msg) => {
  const text = String(msg?.content || '').trim()
  if (!text) return
  try {
    await writeClipboard(text)
    ElMessage.success('问题已复制')
  } catch {
    ElMessage.warning('复制失败，请手动复制')
  }
}

const editQuestion = (msg) => {
  const text = String(msg?.content || '').trim()
  if (!text) return
  if (isRunning.value) {
    ElMessage.warning('当前正在执行，停止后再修改问题')
    return
  }
  query.value = text
  focusComposer(true)
  ElMessage.success('已放入输入框，修改后按 Enter 发送')
}

const clearMessageRuntimeState = (items = []) => {
  items.forEach((item) => {
    if (!item?.id) return
    delete thinkingOpen[item.id]
    delete confirmationDrafts[item.id]
    delete confirmationSubmitting[item.id]
  })
}

const rerunQuestion = async (msg) => {
  const text = String(msg?.content || '').trim()
  if (!text || isRunning.value) return

  const userIndex = messages.findIndex(item => item.id === msg.id)
  if (userIndex < 0) return

  const removed = messages.splice(userIndex + 1)
  clearMessageRuntimeState(removed)
  session.resetSession()
  clearChatUiState()

  const aid = ++msgCounter
  const aiMsg = { id: aid, role: 'ai', loading: true, data: null }
  messages.splice(userIndex + 1, 0, aiMsg)
  thinkingOpen[aid] = true

  query.value = ''
  showPanel.value = true
  scheduleChatScroll(24, 'smooth')
  startTimer()

  try {
    const res = await session.startAsk(text, datasetId.value, modelId.value)
    if (res) {
      aiMsg.loading = false
      aiMsg.data = res
    } else if (!aiMsg.data) {
      aiMsg.loading = false
      aiMsg.data = { aborted: true }
    } else {
      aiMsg.loading = false
    }
    thinkingOpen[aid] = false
    scheduleChatScroll(48, 'smooth')
  } catch (err) {
    if (aiMsg.data?.requires_confirmation && session.state.status === 'waiting_confirmation') {
      aiMsg.loading = false
      thinkingOpen[aid] = false
      scheduleChatScroll(36, 'smooth')
      return
    }
    aiMsg.loading = false
    aiMsg.data = { error: err.response?.data?.error || err.message || '系统繁忙' }
    query.value = text
    scheduleChatScroll(36, 'smooth')
  } finally {
    stopTimer()
  }
}

const handleSend = async () => {
  const text = query.value.trim()
  if (!text || isRunning.value) return

  const uid = ++msgCounter
  messages.push({ id: uid, role: 'user', content: text })
  const aid = ++msgCounter
  const aiMsg = { id: aid, role: 'ai', loading: true, data: null }
  messages.push(aiMsg)
  thinkingOpen[aid] = true

  showPanel.value = true
  clearExecutionPanelState()
  scheduleChatScroll(24, 'smooth')
  startTimer()

  try {
    const res = await session.startAsk(text, datasetId.value, modelId.value)
    if (res) {
      aiMsg.loading = false
      aiMsg.data = res
    } else if (!aiMsg.data) {
      aiMsg.loading = false
      aiMsg.data = { aborted: true }
    } else {
      aiMsg.loading = false
    }
    query.value = ''
    thinkingOpen[aid] = false
    scheduleChatScroll(48, 'smooth')
  } catch (err) {
    if (aiMsg.data?.requires_confirmation && session.state.status === 'waiting_confirmation') {
      aiMsg.loading = false
      thinkingOpen[aid] = false
      scheduleChatScroll(36, 'smooth')
      return
    }
    aiMsg.loading = false
    aiMsg.data = { error: err.response?.data?.error || err.message || '系统繁忙' }
    query.value = text
    scheduleChatScroll(36, 'smooth')
  } finally {
    stopTimer()
  }
}

const handleStop = () => {
  session.stopAsk()
  stopTimer()
  ElMessage.warning('已停止执行')
}

const resetForNewChat = () => {
  saveCurrentToHistory()
  messages.splice(0, messages.length)
  query.value = ''
  clearRestoreRequest()
  setActiveHistory('')
  clearChatUiState()
  session.resetSession()
  showPanel.value = true
  nextTick(() => {
    scheduleChatScroll(20, 'auto')
    schedulePanelScroll(20, 'auto', true)
  })
}

const handleNewChat = async () => {
  if (messages.length === 0) {
    resetForNewChat()
    return
  }

  try {
    await ElMessageBox.confirm(
      '开始新会话后，当前执行记录会被清空，并自动归档到历史对话中。',
      '开始新会话',
      {
        type: 'info',
        confirmButtonText: '开始新会话',
        cancelButtonText: '暂不切换',
        distinguishCancelAndClose: true,
        customClass: 'sa-message-box',
      }
    )
    resetForNewChat()
  } catch {
    // user cancelled
  }
}

const focusSidebarHistory = () => {
  window.dispatchEvent(new CustomEvent('smartask-history-focus'))
}

const datasetNameMap = computed(() => new Map(
  (datasets.value || []).map(item => [Number(item.id), item.dataset_name])
))

const normalizeReportTitle = () => '业绩分析报告'

const buildDownloadFilename = (title) => {
  const base = String(normalizeReportTitle(title))
    .replace(/[\\/:*?"<>|]+/g, '-')
    .replace(/\s+/g, ' ')
    .trim()
  return `${base || '业绩分析报告'}.pdf`
}

const buildReportHtml = (title, report) => `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${normalizeReportTitle(title)}</title>
  <style>
    @page { size: A4; margin: 16mm 14mm; }
    :root { --primary: #1890ff; --page-bg: #f0f2f5; --card-bg: #ffffff; --text: #1d2129; }
    body { margin: 0; font-family: var(--font-sans, "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", sans-serif); background: var(--page-bg); color: var(--text); }
    .page { max-width: 960px; margin: 0 auto; padding: 40px 24px 72px; }
    .card { background: var(--card-bg); border-radius: 8px; padding: 28px 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    .eyebrow { font-size: 12px; color: var(--primary); font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
    h1 { margin: 12px 0 8px; font-size: 28px; line-height: 1.25; }
    h2 { margin: 28px 0 12px; font-size: 20px; }
    h3 { margin: 20px 0 10px; font-size: 16px; }
    p, li { font-size: 14px; line-height: 1.8; color: #4e5969; }
    hr { border: none; border-top: 1px solid #e5e6eb; margin: 24px 0; }
    code { background: #f2f3f5; padding: 2px 6px; border-radius: 6px; }
    table { width: 100%; border-collapse: collapse; margin: 16px 0; }
    th, td { border: 1px solid #e5e6eb; padding: 10px 12px; text-align: left; font-size: 13px; }
    th { background: #f7f8fa; color: #1d2129; }
    .print-tip { margin-top: 20px; font-size: 12px; color: #86909c; }
    @media print {
      body { background: #ffffff; }
      .page { max-width: none; padding: 0; }
      .card { border: none; border-radius: 0; padding: 0; box-shadow: none; }
      .print-tip { display: none; }
    }
  </style>
</head>
<body>
  <main class="page">
    <section class="card">
      <div class="eyebrow">Data Agent Report</div>
      <h1>${normalizeReportTitle(title)}</h1>
      <article>${renderMd(report)}</article>
      <div class="print-tip">请在打印对话框中选择“另存为 PDF”</div>
    </section>
  </main>
</body>
</html>`

const downloadLatestReport = (report = latestReport.value, title = sideReportHeading.value) => {
  if (!report) {
    ElMessage.warning('当前还没有可导出的报告内容')
    return
  }

  const exportTitle = normalizeReportTitle(title)
  if (activePrintFrame?.parentNode) {
    activePrintFrame.parentNode.removeChild(activePrintFrame)
    activePrintFrame = null
  }

  const frame = document.createElement('iframe')
  frame.style.position = 'fixed'
  frame.style.right = '0'
  frame.style.bottom = '0'
  frame.style.width = '0'
  frame.style.height = '0'
  frame.style.border = '0'
  frame.style.opacity = '0'
  frame.setAttribute('aria-hidden', 'true')
  document.body.appendChild(frame)
  activePrintFrame = frame

  const html = buildReportHtml(exportTitle, report)
  let printed = false
  const triggerPrint = () => {
    if (printed) return
    printed = true
    const frameWindow = frame.contentWindow
    if (!frameWindow) {
      ElMessage.warning('当前无法打开打印窗口，请稍后重试')
      return
    }

    try {
      frameWindow.document.open()
      frameWindow.document.write(html)
      frameWindow.document.close()
      frameWindow.document.title = buildDownloadFilename(exportTitle)
      frameWindow.focus()
      window.setTimeout(() => {
        frameWindow.print()
      }, 260)
      ElMessage.success('已准备好报告，请在打印对话框中选择“另存为 PDF”')
    } catch (error) {
      ElMessage.warning('当前无法导出 PDF，请稍后重试')
    }
  }

  frame.onload = triggerPrint
  window.setTimeout(triggerPrint, 40)
}
const handleDownloadReport = () => {
  ElMessage.info('报告下载功能开发中...')
}

const buildHistoryTitle = () => {
  const firstUser = messages.find(m => m.role === 'user')
  const q = firstUser?.content || session.state.question || '未命名对话'
  return String(q).slice(0, 24)
}

const saveCurrentToHistory = () => {
  if (messages.length === 0) return

  loadHistory()
  const id = `${Date.now()}_${Math.random().toString(16).slice(2)}`
  const d = datasets.value.find(x => x.id === datasetId.value)
  const payload = {
    id,
    title: buildHistoryTitle(),
    datasetId: datasetId.value,
    datasetName: d?.dataset_name || '自动路由数据集',
    updatedAt: new Date().toLocaleString(),
    messages: JSON.parse(JSON.stringify(messages)),
    sessionState: JSON.parse(JSON.stringify(session.state)),
    showPanel: showPanel.value,
    thinkingOpen: JSON.parse(JSON.stringify(thinkingOpen)),
    logOpen: JSON.parse(JSON.stringify(logOpen)),
  }
  return upsertHistory(payload)
}

const restoreHistory = (item) => {
  if (!item) return
  if (isRunning.value) {
    ElMessage.warning('正在执行中，无法恢复历史对话')
    return false
  }

  setActiveHistory(item.id)
  messages.splice(0, messages.length, ...JSON.parse(JSON.stringify(item.messages || [])))
  session.state.question = item.sessionState?.question || ''
  session.state.selectedDatasetId = item.sessionState?.selectedDatasetId || null
  session.state.status = item.sessionState?.status || 'idle'
  session.state.result = item.sessionState?.result || null
  session.state.error = item.sessionState?.error || ''
  session.state.logs = item.sessionState?.logs || []
  session.state.startedAt = item.sessionState?.startedAt || ''
  session.state.updatedAt = item.sessionState?.updatedAt || ''
  session.state.currentSessionId = item.sessionState?.currentSessionId || ''

  datasetId.value = item.datasetId
  showPanel.value = !!item.showPanel

  Object.keys(thinkingOpen).forEach(k => delete thinkingOpen[k])
  Object.assign(thinkingOpen, item.thinkingOpen || {})
  Object.keys(logOpen).forEach(k => delete logOpen[k])
  Object.assign(logOpen, item.logOpen || {})
  timelineVersion.value += 1

  nextTick(() => {
    scrollChat('auto')
    scrollPanel('auto')
  })
  return true
}

const quickAsk = (item) => {
  const text = typeof item === 'string' ? item : String(item?.question_text || '').trim()
  if (!text) return
  const nextDatasetId = typeof item === 'string' ? null : Number(item?.dataset_id || 0)
  if (nextDatasetId) {
    datasetId.value = nextDatasetId
  }
  query.value = text
  nextTick(() => {
    const textarea = document.querySelector('.sa-textarea')
    if (textarea instanceof HTMLTextAreaElement) {
      textarea.focus()
      textarea.setSelectionRange(textarea.value.length, textarea.value.length)
    }
  })
  const datasetName = typeof item === 'string' ? '' : String(item?.dataset_name || item?.dataset_tag || '').trim()
  ElMessage({
    message: datasetName ? `已切换到「${datasetName}」并填入问题` : '已填入，按 Enter 发送',
    type: 'success',
    duration: 1800,
    showClose: false,
    customClass: 'sa-toast-modern'
  })
}

const handleExternalFreshChat = () => {
  resetForNewChat()
}

const getConfirmOptionKey = (opt) => (typeof opt === 'string' ? opt : (opt?.id || opt?.label || JSON.stringify(opt)))
const getConfirmOptionLabel = (opt) => (typeof opt === 'string' ? opt : (opt?.label || opt?.name || '确认选项'))

const getConfirmOptionDescription = (opt) => (typeof opt === 'string' ? '' : String(opt?.description || '').trim())
const getConfirmOptionDatasetNames = (opt) => {
  if (typeof opt === 'string') return []
  const ids = Array.isArray(opt?.dataset_ids) ? opt.dataset_ids : []
  return ids.map(id => datasetNameMap.value.get(Number(id)) || `数据集 ${id}`)
}
const getConfirmOptionMemberNames = (opt) => {
  if (typeof opt === 'string') return []
  return (Array.isArray(opt?.resolved_members) ? opt.resolved_members : [])
    .map(item => String(item || '').trim())
    .filter(Boolean)
}
const getConfirmOptionImpact = (opt) => {
  if (typeof opt === 'string') return '确认后将继续执行当前问数任务。'
  const optionType = String(opt?.option_type || '')
  if (optionType === 'cross_dataset') return '确认后将以多数据集汇总方式继续生成结果和报告。'
  if (optionType === 'dataset_scope') return '确认后将采用该数据集口径，并继续生成 SQL 与分析报告。'
  if (optionType === 'dataset_disambiguation') return '确认后将采用具体数据集口径，并继续生成后续分析结果。'
  if (optionType === 'member_set_confirmation') {
    return String(opt?.scope_mode || '') === 'compare'
      ? '确认后将按成员逐个对比，再输出结论和报告。'
      : '确认后将先按该成员集合汇总，再继续生成分析结果。'
  }
  return '确认后将按照当前选定口径继续执行。'
}
const getConfirmationCandidateNames = (msg) => {
  const ids = msg?.data?.route?.candidate_dataset_ids || []
  return ids.map(id => datasetNameMap.value.get(Number(id)) || `数据集 ${id}`)
}
const getConfirmationScopeSummary = (msg) => {
  const route = msg?.data?.route || {}
  const confirmationType = String(route?.confirmation_type || '')
  const candidateCount = Array.isArray(route?.candidate_dataset_ids) ? route.candidate_dataset_ids.length : 0
  if (confirmationType === 'member_set_confirmation') {
    const memberCount = Array.isArray(route?.resolved_entities_preview) ? route.resolved_entities_preview.length : 0
    return memberCount > 0
      ? `当前需要确认集合口径，涉及 ${memberCount} 个成员，确认后会继续执行分析。`
      : '当前需要确认集合口径，确认后会继续执行分析。'
  }
  if (confirmationType === 'dataset_disambiguation') {
    return '当前命中了多个可能的数据集口径，确认后会采用对应执行范围。'
  }
  if (candidateCount > 1) return `当前存在 ${candidateCount} 个候选口径，确认后会采用对应执行范围。`
  return '当前需要先确认业务口径，确认后才会继续执行查询与报告生成。'
}

const doConfirm = async (opt, msg) => {
  startTimer()
  if (msg?.id) confirmationSubmitting[msg.id] = true
  const originalData = msg?.data ? JSON.parse(JSON.stringify(msg.data)) : null
  if (msg) {
    msg.loading = true
    msg.data = {
      ...(msg.data || {}),
      requires_confirmation: false,
      error: '',
      question: msg?.data?.question || session.state.question,
    }
  }
  try {
    const res = await session.submitBossConfirmation(opt, {
      candidateDatasetIds: msg?.data?.route?.candidate_dataset_ids || msg?.data?.route?.dataset_ids || [],
      originalQuestion: msg?.data?.question || session.state.question,
    })
    const last = [...messages].reverse().find(m => m.role === 'ai')
    if (last) {
      last.loading = false
      last.data = res
    }
    if (msg?.id && typeof opt === 'string') confirmationDrafts[msg.id] = ''
    scheduleChatScroll(36, 'smooth')
  } catch (error) {
    if (msg) {
      msg.loading = false
      if (originalData?.requires_confirmation) {
        msg.data = {
          ...originalData,
          requires_confirmation: true,
          error: '',
        }
      }
    }
    if (msg?.id) confirmationSubmitting[msg.id] = false
    ElMessage.error(error?.response?.data?.error || error?.message || '提交失败')
    scheduleChatScroll(36, 'smooth')
  }
  finally { stopTimer() }
}

const scrollChat = (behavior = 'smooth') => nextTick(() => {
  if (chatBodyRef.value) {
    chatBodyRef.value.scrollTo({ top: chatBodyRef.value.scrollHeight, behavior })
  }
})

const forceScrollChatToBottom = (behavior = 'auto') => {
  ;[0, 60, 180, 360].forEach((delay) => {
    window.setTimeout(() => scrollChat(behavior), delay)
  })
}
const isPanelNearBottom = () => {
  const el = panelRef.value
  if (!el) return true
  return el.scrollHeight - el.scrollTop - el.clientHeight < 120
}

const shouldFollowPanelBottom = () => ['running', 'waiting_confirmation'].includes(session.state.status)

const scrollPanel = (behavior = 'auto', force = false) => nextTick(() => {
  if (panelRef.value && (force || shouldFollowPanelBottom() || isPanelNearBottom())) {
    panelRef.value.scrollTo({ top: panelRef.value.scrollHeight, behavior })
  }
})

const scheduleChatScroll = (delay = 40, behavior = 'smooth') => {
  if (chatScrollTimer) clearTimeout(chatScrollTimer)
  chatScrollTimer = window.setTimeout(() => {
    scrollChat(behavior)
  }, delay)
}

const schedulePanelScroll = (delay = 150, behavior = 'auto', force = false) => {
  if (panelScrollTimer) clearTimeout(panelScrollTimer)
  panelScrollTimer = window.setTimeout(() => {
    scrollPanel(behavior, force)
  }, delay)
}

const startTimer = () => {
  elapsed.value = 0
  clearInterval(timerInst)
  timerInst = setInterval(() => elapsed.value++, 1000)
}

const submitConfirmationDraft = (msg) => {
  const text = String(confirmationDrafts[msg?.id] || '').trim()
  if (!text || isRunning.value) return
  doConfirm(text, msg)
}

const handleConfirmationDraftEnter = (event, msg) => {
  if (event?.isComposing) return
  submitConfirmationDraft(msg)
}
const stopTimer = () => clearInterval(timerInst)

const loadQuestions = async () => {
  commonQuestionsLoading.value = true
  try {
    const res = await getCommonQuestions(null, { random: 1, limit: 4, t: Date.now() })
    commonQuestions.value = (res.questions || res.common_questions || []).slice(0, 4)
  } catch {
    commonQuestions.value = []
  } finally {
    commonQuestionsLoading.value = false
  }
}

const refreshCommonQuestions = async () => {
  if (commonQuestionsLoading.value) return
  await loadQuestions()
}

const getStatusColor = (rate) => {
  const value = toNumber(rate)
  if (value === null) return '#1890ff'
  if (value >= 15) return '#00b42a'
  if (value >= 10) return '#faad14'
  return '#f5222d'
}

const getMetricColor = (column) => {
  const text = String(column || '')
  if (/任务|目标/i.test(text)) return '#1890ff'
  if (/开单|完成|实际|销售/i.test(text)) return '#00b42a'
  if (/剩余|缺口|差额/i.test(text)) return '#faad14'
  if (/率|percent|rate/i.test(text)) return '#f59e0b'
  return '#597ef7'
}

const sortRowsByCompletionRate = (rows = [], columns = []) => {
  const rateColumn = columns.find(column => isRateColumn(column)) || Object.keys(rows[0] || {}).find(column => isRateColumn(column))
  if (!rateColumn) return rows
  return [...rows].sort((a, b) => (toNumber(b?.[rateColumn]) || 0) - (toNumber(a?.[rateColumn]) || 0))
}

const renderChartSpec = (chart, data) => {
  const labelColumn = data.columns?.[0]
  const numericColumns = data.columns?.slice(1) || []
  const sortedRows = sortRowsByCompletionRate(data.rows || [], data.columns || [])
  const colorPalette = ['#1890ff', '#00b42a', '#faad14', '#f5222d', '#06b6d4', '#597ef7']
  const shortSeriesName = (name) => String(name || '')
    .replace(/^年度/, '')
    .replace(/^总/, '')
    .replace('任务金额', '任务')
    .replace('开单金额', '开单')
    .replace('剩余任务金额', '剩余缺口')

  if (data.chartType === 'trend') {
    chart.setOption({
      backgroundColor: 'transparent',
      color: colorPalette,
      tooltip: { trigger: 'axis' },
      legend: { top: 0, textStyle: { color: '#4e5969', fontSize: 11 } },
      grid: { left: 34, right: 18, top: 34, bottom: 28, containLabel: true },
      xAxis: {
        type: 'category',
        data: sortedRows.map(row => row[labelColumn]),
        axisLabel: { color: '#86909c', fontSize: 11, hideOverlap: true },
        axisLine: { lineStyle: { color: '#e5e6eb' } },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#86909c', fontSize: 11 },
        splitLine: { lineStyle: { color: '#f2f3f5', type: 'dashed' } },
      },
      series: numericColumns.map((column, columnIndex) => ({
        name: column,
        type: columnIndex === 0 ? 'bar' : 'line',
        smooth: true,
        barMaxWidth: 18,
        symbolSize: columnIndex === 0 ? 0 : 6,
        itemStyle: { borderRadius: columnIndex === 0 ? [4, 4, 0, 0] : 0 },
        data: sortedRows.map(row => row[column]),
      })),
    })
    return
  }

  if (data.chartType === 'combo') {
    const categoryRows = sortedRows.slice(0, 12)
    const rateColumn = numericColumns.find(column => /率|percent|rate/i.test(column)) || numericColumns[numericColumns.length - 1]
    const barColumns = numericColumns
      .filter(column => column !== rateColumn && !/剩余|缺口|remain/i.test(column))
      .slice(0, 2)
    chart.setOption({
      backgroundColor: 'transparent',
      color: colorPalette,
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: {
        type: 'scroll',
        top: 2,
        left: 8,
        right: 8,
        itemWidth: 10,
        itemHeight: 8,
        icon: 'roundRect',
        formatter: shortSeriesName,
        textStyle: { color: '#4e5969', fontSize: 10 },
      },
      grid: { left: 42, right: 38, top: 68, bottom: 44, containLabel: true },
      xAxis: {
        type: 'category',
        data: categoryRows.map(row => row[labelColumn]),
        axisLabel: { color: '#86909c', fontSize: 11, interval: 0, rotate: categoryRows.length > 4 ? 24 : 0, hideOverlap: true, margin: 12 },
        axisLine: { lineStyle: { color: '#e5e6eb' } },
      },
      yAxis: [
        {
          type: 'value',
          axisLabel: { color: '#86909c', fontSize: 11, formatter: value => formatAmount(value) },
          splitLine: { lineStyle: { color: '#f2f3f5', type: 'dashed' } },
        },
        {
          type: 'value',
          axisLabel: { color: '#86909c', fontSize: 11, formatter: '{value}%' },
          splitLine: { show: false },
        },
      ],
      series: [
        ...barColumns.map((column) => ({
          name: column,
          type: 'bar',
          barMaxWidth: 18,
          itemStyle: { borderRadius: [4, 4, 0, 0], color: getMetricColor(column) },
          data: categoryRows.map(row => ({
            value: row[column],
          })),
        })),
        {
          name: rateColumn,
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          symbolSize: 6,
          lineStyle: { width: 2.5, color: getMetricColor(rateColumn) },
          label: {
            show: true,
            position: 'top',
            color: '#4e5969',
            fontSize: 10,
            distance: 6,
            formatter: ({ value }) => `${formatDisplayValue(value)}%`,
          },
          data: categoryRows.map(row => ({
            value: row[rateColumn],
            itemStyle: { color: getStatusColor(row[rateColumn]) },
          })),
        },
      ],
    })
    return
  }

  if (data.chartType === 'horizontalRateBar' || data.chartType === 'horizontalDrill') {
    const categoryRows = sortedRows.slice(0, 12).reverse()
    const rateColumn = numericColumns.find(column => isRateColumn(column)) || numericColumns[numericColumns.length - 1]
    const remainColumn = numericColumns.find(column => /剩余|缺口|remain/i.test(column))
    const series = [
      {
        name: rateColumn,
        type: 'bar',
        barMaxWidth: 14,
        itemStyle: { borderRadius: [0, 5, 5, 0] },
        label: {
          show: true,
          position: 'right',
          color: '#4e5969',
          fontSize: 10,
          formatter: ({ value }) => `${formatDisplayValue(value)}%`,
        },
        data: categoryRows.map(row => ({
          value: row[rateColumn],
          itemStyle: { color: getStatusColor(row[rateColumn]) },
        })),
      },
    ]
    if (data.chartType === 'horizontalDrill' && remainColumn) {
      series.push({
        name: remainColumn,
        type: 'bar',
        barMaxWidth: 10,
        itemStyle: { borderRadius: [0, 4, 4, 0], color: '#ff9a2e' },
        label: {
          show: true,
          position: 'right',
          color: '#86909c',
          fontSize: 10,
          formatter: ({ value }) => formatAmount(value),
        },
        data: categoryRows.map(row => row[remainColumn]),
      })
    }
    chart.setOption({
      backgroundColor: 'transparent',
      color: colorPalette,
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: {
        show: series.length > 1,
        top: 2,
        right: 8,
        itemWidth: 10,
        itemHeight: 8,
        textStyle: { color: '#4e5969', fontSize: 10 },
      },
      grid: { left: 78, right: 58, top: series.length > 1 ? 34 : 14, bottom: 18, containLabel: true },
      xAxis: {
        type: 'value',
        axisLabel: { color: '#86909c', fontSize: 11, formatter: value => `${value}%` },
        splitLine: { lineStyle: { color: '#f2f3f5', type: 'dashed' } },
      },
      yAxis: {
        type: 'category',
        data: categoryRows.map(row => row[labelColumn]),
        axisLabel: { color: '#4e5969', fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series,
    })
    return
  }

  if (data.chartType === 'bar') {
    const valueColumn = numericColumns[0]
    chart.setOption({
      backgroundColor: 'transparent',
      color: [colorPalette[0]],
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 34, right: 18, top: 18, bottom: 48, containLabel: true },
      xAxis: {
        type: 'category',
        data: sortedRows.slice(0, 8).map(row => row[labelColumn]),
        axisLabel: { color: '#86909c', fontSize: 11, interval: 0, rotate: sortedRows.length > 5 ? 18 : 0 },
        axisLine: { lineStyle: { color: '#e5e6eb' } },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#86909c', fontSize: 11, formatter: value => isAmountColumn(valueColumn) ? formatAmount(value) : value },
        splitLine: { lineStyle: { color: '#f2f3f5', type: 'dashed' } },
      },
      series: [{
        type: 'bar',
        barMaxWidth: 22,
        itemStyle: { borderRadius: [5, 5, 0, 0] },
        label: {
          show: true,
          position: 'top',
          color: '#4e5969',
          fontSize: 11,
          fontWeight: 600,
          formatter: ({ value }) => formatDisplayValue(value),
        },
        data: sortedRows.slice(0, 8).map(row => ({
          value: row[valueColumn],
          itemStyle: { color: isRateColumn(valueColumn) ? getStatusColor(row[valueColumn]) : colorPalette[0] },
        })),
      }],
    })
    return
  }

  const valueColumn = numericColumns[0]
  chart.setOption({
    color: colorPalette,
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['48%', '74%'],
      center: ['50%', '52%'],
      avoidLabelOverlap: true,
      label: {
        show: true,
        color: '#4e5969',
        fontSize: 11,
        lineHeight: 16,
        formatter: ({ name, percent, value }) => `${name}\n${formatDisplayValue(value)} · ${percent}%`,
      },
      labelLine: {
        show: true,
        length: 10,
        length2: 8,
        lineStyle: {
          color: 'rgba(134, 144, 156, 0.7)',
        },
      },
      data: sortedRows.slice(0, 6).map(row => ({ name: row[labelColumn], value: row[valueColumn] })),
    }],
  })
}

const initPreviewChart = (el, data, key) => {
  if (!el || !data?.rows?.length || !data?.columns?.length) return
  nextTick(() => {
    const chart = echarts.getInstanceByDom(el) || echarts.init(el)
    renderChartSpec(chart, data)
  })
}

const initLogChart = (el, data, key) => {
  if (!el || !data?.rows?.length || !data?.columns?.length) return
  nextTick(() => {
    const chart = echarts.getInstanceByDom(el) || echarts.init(el)
    renderChartSpec(chart, data)
  })
}

const renderDialogChart = () => {
  if (!chartViewerVisible.value || chartViewerMode.value !== 'chart' || !chartDialogRef.value || !chartViewerSpec.value) return
  if (chartViewerSpec.value.chartType === 'metric') return
  nextTick(() => {
    const chart = echarts.getInstanceByDom(chartDialogRef.value) || echarts.init(chartDialogRef.value)
    renderChartSpec(chart, chartViewerSpec.value)
    chart.resize()
  })
}

// 监听日志更新，自动展开最新节点
watch(() => session.state.logs.length, (len) => {
  if (len > 0) {
    logOpen[len - 1] = true
    scheduleChatScroll(26, 'smooth')
    schedulePanelScroll(60, 'auto', shouldFollowPanelBottom())
  }
}, { flush: 'post' })

watch(() => session.state.logs.map(log => log.pulseText || '').join('|'), (signature) => {
  if (!signature) return
  scheduleChatScroll(26, 'smooth')
  schedulePanelScroll(60, 'auto', shouldFollowPanelBottom())
}, { flush: 'post' })

watch(() => session.state.status, (s) => {
  syncPendingConfirmationMessage()
  if (s === 'completed') {
    nextTick(() => {
      forceScrollChatToBottom('auto')
      if (hasSideReport.value) scrollPanelToReportTop()
    })
  }
  if (s === 'waiting_confirmation') {
    scheduleChatScroll(26, 'smooth')
    schedulePanelScroll(60, 'auto', true)
  }
})

watch(() => session.state.result, () => {
  syncPendingConfirmationMessage()
}, { flush: 'post' })

watch(() => hasSideReport.value, (ready) => {
  if (ready && session.state.status === 'completed') {
    scrollPanelToReportTop()
    forceScrollChatToBottom('auto')
  }
}, { flush: 'post' })

watch(() => [chartViewerVisible.value, chartViewerSpec.value, chartViewerMode.value], ([visible]) => {
  if (visible) {
    renderDialogChart()
    return
  }

  if (chartDialogRef.value) {
    const chart = echarts.getInstanceByDom(chartDialogRef.value)
    if (chart) chart.dispose()
  }

  chartViewerMode.value = 'chart'
}, { flush: 'post' })

watch(() => chartViewerMode.value, (mode) => {
  if (mode === 'chart') {
    renderDialogChart()
    return
  }

  if (chartDialogRef.value) {
    const chart = echarts.getInstanceByDom(chartDialogRef.value)
    if (chart) chart.dispose()
  }
})

watch(() => messages.length, () => {
  scheduleChatScroll(24, 'smooth')
}, { flush: 'post' })

watch(() => pendingRestoreId.value, (historyId) => {
  if (!historyId) return
  const item = findHistoryById(historyId)
  if (!item) {
    ElMessage.warning('未找到对应的历史对话记录')
    clearRestoreRequest()
    return
  }
  restoreHistory(item)
  clearRestoreRequest()
}, { flush: 'post', immediate: true })

watch(canViewCharts, (allowed) => {
  if (!allowed) {
    chartViewerVisible.value = false
  }
})

watch(canViewFullscreenReport, (allowed) => {
  if (!allowed) {
    reportViewerVisible.value = false
  }
})

onMounted(async () => {
  window.addEventListener('smartask-create-fresh-chat', handleExternalFreshChat)
  loadFeatureFlags()
  loadHistory()

  // 从 sessionStorage 还原输入状态
  const cached = getSessionCache()
  if (cached.query) query.value = cached.query
  if (cached.datasetId !== undefined) datasetId.value = cached.datasetId
  if (cached.modelId !== undefined) modelId.value = cached.modelId

  try {
    const res = await getBookshelfDatasets()
    datasets.value = res.datasets || []
    await loadQuestions()
  } catch {}

  try {
    const modelRes = await getActiveAIModels()
    aiModels.value = modelRes.models || []
  } catch {}

  if (session.state.selectedDatasetId) datasetId.value = session.state.selectedDatasetId

  // 页面重新打开时不自动回灌旧结果；历史恢复仍通过显式操作触发。
  if (session.state.result || session.state.question || session.state.logs?.length) {
    session.clearRecoveredSessionResult()
  }
})

// keep-alive 重新激活时刷新引用数据（数据集、模型可能在其他页面被修改）
onActivated(async () => {
  try {
    const res = await getBookshelfDatasets()
    datasets.value = res.datasets || []
  } catch {}
  try {
    const modelRes = await getActiveAIModels()
    aiModels.value = modelRes.models || []
  } catch {}
  loadHistory()
})

// 将关键输入状态持久化到 sessionStorage，页面跳转后还原
watch([query, datasetId, modelId], ([q, d, m]) => {
  setSessionCache({ query: q, datasetId: d, modelId: m })
}, { flush: 'post' })

onDeactivated(() => {
  // keep-alive 停用时的轻量清理（不销毁组件状态）
  if (chatScrollTimer) clearTimeout(chatScrollTimer)
  if (panelScrollTimer) clearTimeout(panelScrollTimer)
})

onUnmounted(() => {
  window.removeEventListener('smartask-create-fresh-chat', handleExternalFreshChat)
  stopTimer()
  if (chatScrollTimer) clearTimeout(chatScrollTimer)
  if (panelScrollTimer) clearTimeout(panelScrollTimer)
  if (activePrintFrame?.parentNode) {
    activePrintFrame.parentNode.removeChild(activePrintFrame)
    activePrintFrame = null
  }
  if (chartDialogRef.value) {
    const chart = echarts.getInstanceByDom(chartDialogRef.value)
    if (chart) chart.dispose()
  }
})
</script>

<style scoped>
/* ===== 页面布局 ===== */
.sa-page {
  height: 100%;
  background:
    radial-gradient(circle at top left, rgba(22, 93, 255, 0.12), transparent 30%),
    linear-gradient(180deg, #f7f9fc 0%, #eef2f8 100%);
  overflow: hidden;
  font-family: var(--font-sans, 'Microsoft YaHei UI', 'Microsoft YaHei', 'PingFang SC', sans-serif);
  font-size: 14px;
  color: var(--text-title);
  padding: 16px;
  box-sizing: border-box;
}

.sa-page :is(button, div, span) {
  transition:
    color 0.2s cubic-bezier(0.4, 0, 0.2, 1),
    background-color 0.2s cubic-bezier(0.4, 0, 0.2, 1),
    border-color 0.2s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.2s cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 0.2s cubic-bezier(0.4, 0, 0.2, 1),
    transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.sa-shell {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.sa-workspace {
  flex: 1;
  min-height: 0;
  display: flex;
  overflow: hidden;
  border: 1px solid rgba(29, 33, 41, 0.08);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(14px);
}

/* ===== 对话区 ===== */
.sa-chat-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: transparent;
}

/* 聊天区 */
.sa-chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 22px 22px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sa-chat-panel.is-detail-hidden .sa-chat-body {
  padding-left: 28px;
  padding-right: 28px;
}

/* 消息 */
.sa-msg-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
}
.sa-msg-wrap {
  animation: sa-fadein 0.3s ease-out;
  max-width: 920px;
}

.sa-chat-panel.is-detail-hidden .sa-msg-list {
  max-width: 1220px;
  margin: 0 auto;
}

.sa-chat-panel.is-detail-hidden .sa-msg-wrap {
  max-width: 1160px;
}
@keyframes sa-fadein {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

/* AI回复包装 */
.sa-ai-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sa-ai-meta {
  display: flex;
  align-items: center;
  gap: 9px;
}
.sa-ai-avatar {
  width: 30px;
  height: 30px;
  background: linear-gradient(180deg, #2a6cff 0%, #165dff 100%);
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}
.sa-ai-name {
  font-size: 13px;
  font-weight: 600;
  color: #1d2129;
}
.sa-ai-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-left: 39px;
  max-width: 760px;
}

.sa-chat-panel.is-detail-hidden .sa-ai-cards {
  max-width: 980px;
}

.sa-result-chain {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  padding-top: 10px;
  margin-top: 1px;
  border-top: 1px dashed rgba(22, 93, 255, 0.12);
  animation: sa-curtain-open 0.32s cubic-bezier(0.4, 0, 0.2, 1);
  transform-origin: top center;
}

.sa-result-chain > * {
  width: 100%;
}

.sa-chat-panel.is-detail-hidden .sa-result-chain,
.sa-chat-panel.is-detail-hidden .sa-inline-visuals,
.sa-chat-panel.is-detail-hidden .sa-flow-handoff,
.sa-chat-panel.is-detail-hidden .sa-confirm-card {
  max-width: 980px;
}

.sa-inline-visuals {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  padding: 14px;
  border-radius: 14px;
  border: 1px solid rgba(22, 93, 255, 0.1);
  background: linear-gradient(180deg, #fcfdff 0%, #ffffff 100%);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.035);
}

.sa-inline-visuals.is-single {
  width: 100%;
}

.sa-inline-visuals-head {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.sa-inline-visuals-kicker {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #165dff;
}

.sa-inline-visuals-title {
  margin-top: 5px;
  font-size: 16px;
  font-weight: 600;
  color: #1d2129;
}

.sa-inline-visuals-caption {
  margin-top: 4px;
  font-size: 11px;
  line-height: 1.65;
  color: #86909c;
}

.sa-inline-visuals-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.sa-inline-visuals-grid.is-single {
  grid-template-columns: minmax(0, 420px);
  justify-content: start;
}

.sa-inline-visual-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  background: #ffffff;
}

.sa-inline-visual-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.sa-inline-visual-card-title {
  font-size: 13px;
  font-weight: 600;
  color: #1d2129;
  line-height: 1.5;
}

.sa-inline-visual-card-subtitle {
  margin-top: 3px;
  font-size: 11px;
  color: #86909c;
}

.sa-inline-visual-chart {
  height: 200px;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
  border: 1px solid rgba(29, 33, 41, 0.06);
}

/* 加载动画 */
.sa-thinking-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  background: linear-gradient(180deg, #f7fbff 0%, #f2f7ff 100%);
  border: 1px solid rgba(22, 93, 255, 0.1);
  border-radius: 14px;
  width: fit-content;
  min-width: 320px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}
.sa-dots {
  display: flex;
  gap: 4px;
}
.sa-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  animation: dot-pulse 1.2s ease-in-out infinite;
}
.sa-dots span:nth-child(2) { animation-delay: 0.2s; }
.sa-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dot-pulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}
.sa-thinking-text {
  font-size: 13px;
  color: #4e5969;
}

/* 确认区 */
.sa-flow-handoff {
  width: 100%;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(22, 93, 255, 0.1);
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.035);
}

.sa-flow-handoff-kicker {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #165dff;
}

.sa-flow-handoff-title {
  margin-top: 5px;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.55;
  color: #1d2129;
}

.sa-flow-handoff-desc {
  margin-top: 5px;
  font-size: 12px;
  line-height: 1.65;
  color: #4e5969;
}

.sa-confirm-card {
  border: 1px solid rgba(255, 125, 0, 0.16);
  border-radius: 16px;
  overflow: hidden;
  background: #fff;
  width: 100%;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}
.sa-confirm-card .sa-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid rgba(255, 125, 0, 0.12);
  background: #fffaf2;
}
.sa-confirm-icon {
  font-size: 20px;
}
.sa-confirm-card .sa-card-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}
.sa-tag-orange {
  background: #fff7e8;
  color: var(--warning);
}
.sa-confirm-q {
  padding: 14px 14px 12px;
  font-size: 14px;
  color: var(--text-title);
  line-height: 1.7;
}
.sa-confirm-impact {
  margin: 0 14px 12px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #fffaf2;
  border: 1px solid rgba(255, 125, 0, 0.12);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sa-confirm-impact-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.sa-confirm-impact-label {
  min-width: 60px;
  font-size: 11px;
  font-weight: 700;
  color: #86909c;
}
.sa-confirm-impact-value {
  font-size: 12px;
  line-height: 1.6;
  color: #4e5969;
}
.sa-confirm-impact-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.sa-confirm-chip {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 9px;
  border-radius: 999px;
  background: #ffffff;
  color: #ff7d00;
  border: 1px solid rgba(255, 125, 0, 0.12);
  font-size: 11px;
  font-weight: 600;
}
.sa-confirm-opts {
  display: flex;
  gap: 10px;
  padding: 0 14px 14px;
  flex-wrap: wrap;
}
.sa-confirm-btn {
  width: 100%;
  text-align: left;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--color-primary);
  color: #165dff;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.sa-confirm-btn:hover {
  background: #f7fbff;
  border-color: rgba(22, 93, 255, 0.32);
}
.sa-confirm-btn-label {
  font-size: 13px;
  font-weight: 700;
  color: #165dff;
}
.sa-confirm-btn-desc,
.sa-confirm-btn-meta,
.sa-confirm-btn-impact {
  font-size: 11px;
  line-height: 1.55;
  color: #4e5969;
}

.sa-confirm-freeform {
  margin: 0 14px 14px;
  padding: 12px;
  border-radius: 12px;
  border: 1px dashed rgba(22, 93, 255, 0.18);
  background: linear-gradient(180deg, rgba(240, 245, 255, 0.75) 0%, #ffffff 100%);
}

.sa-confirm-freeform-head {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 700;
  color: #1d2129;
}

.sa-confirm-textarea {
  width: 100%;
  min-height: 92px;
  resize: vertical;
  padding: 11px 12px;
  border-radius: 12px;
  border: 1px solid rgba(22, 93, 255, 0.12);
  background: rgba(255, 255, 255, 0.95);
  font-size: 13px;
  line-height: 1.6;
  color: #1d2129;
  outline: none;
  box-sizing: border-box;
}

.sa-confirm-textarea:focus {
  border-color: rgba(22, 93, 255, 0.34);
  box-shadow: 0 0 0 3px rgba(22, 93, 255, 0.08);
}

.sa-confirm-textarea::placeholder {
  color: #a9b1bc;
}

.sa-confirm-freeform-actions {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sa-confirm-freeform-hint {
  flex: 1;
  font-size: 11px;
  line-height: 1.6;
  color: #86909c;
}

.sa-confirm-send {
  height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(22, 93, 255, 0.2);
  background: #165dff;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 8px 18px rgba(22, 93, 255, 0.18);
}

.sa-confirm-send:disabled,
.sa-confirm-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.sa-confirm-submitted {
  max-width: 760px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(22, 93, 255, 0.14);
  background: linear-gradient(180deg, rgba(240, 245, 255, 0.78) 0%, #ffffff 100%);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.035);
}

.sa-confirm-submitted-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.sa-confirm-submitted-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #165dff;
  box-shadow: 0 0 0 5px rgba(22, 93, 255, 0.08);
}

.sa-confirm-submitted-title {
  font-size: 13px;
  font-weight: 700;
  color: #165dff;
}

.sa-confirm-submitted-desc {
  font-size: 12px;
  line-height: 1.65;
  color: #4e5969;
}

/* 错误区 */
.sa-error-card {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 12px 16px;
  background: #fff5f5;
  border: 1px solid #ffccc7;
  color: var(--error);
  border-radius: 14px;
  max-width: 760px;
}

/* 状态栏 */
.sa-status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 20px;
  font-size: 12px;
  border-top: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.96);
  flex-shrink: 0;
}
.sa-status-left {
  display: flex;
  align-items: center;
  gap: 7px;
}
.sa-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-primary);
  animation: pulse 1.2s ease-in-out infinite;
}
.sa-status-bar.completed .sa-status-dot {
  background: var(--success);
  animation: none;
}
.sa-status-bar.error .sa-status-dot {
  background: var(--error);
  animation: none;
}
.sa-status-text {
  color: var(--text-body);
  font-weight: 500;
  line-height: 1.5;
}
.sa-status-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.sa-timer {
  color: var(--text-muted);
  font-size: 11px;
}

.sa-link-btn {
  background: none;
  border: none;
  color: #165dff;
  cursor: pointer;
  font-size: 12px;
  padding: 4px 5px;
}

.sa-link-btn:hover {
  text-decoration: underline;
}

.sa-link-btn.danger {
  color: #f53f3f;
}

/* ===== 右侧面板 ===== */
.sa-detail-panel {
  width: clamp(360px, 34vw, 440px);
  max-width: 42vw;
  height: 100%;
  max-height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-left: 1px solid rgba(29, 33, 41, 0.08);
  background: rgba(255, 255, 255, 0.92);
  flex-shrink: 0;
}
.sa-panel-header {
  padding: 16px 16px 12px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.sa-panel-heading {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}
.sa-panel-eyebrow {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #165dff;
}
.sa-panel-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.sa-panel-title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}
.sa-panel-state {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  background: #f2f3f5;
  color: #4e5969;
}
.sa-panel-state.running {
  background: #e8f3ff;
  color: #165dff;
}
.sa-panel-state.completed {
  background: #e8ffea;
  color: #00b42a;
}
.sa-panel-state.error {
  background: #fff1f0;
  color: #f53f3f;
}
.sa-panel-state.waiting_confirmation {
  background: #fff7e8;
  color: #ff7d00;
}
.sa-panel-desc {
  margin: 0;
  font-size: 11px;
  line-height: 1.55;
  color: #86909c;
}
.sa-panel-close {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  background: #fff;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.sa-panel-close:hover {
  color: #165dff;
  border-color: rgba(22, 93, 255, 0.24);
  background: #f7fbff;
}
.sa-panel-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-bottom: 10px;
  overscroll-behavior: contain;
}

/* 数据预览 */
.sa-preview {
  gap: 14px;
}

/* 汇总报告 */
.sa-report-view {
  padding: 0;
}
.sa-report-full {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.sa-kpi-shelf {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.sa-side-section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}
.sa-side-dataset-name {
  margin-top: 4px;
  font-size: 14px;
  font-weight: 600;
  color: #1d2129;
}
.sa-side-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.sa-side-meta-chip {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 9px;
  border-radius: 999px;
  background: #f7f8fa;
  color: #4e5969;
  font-size: 10px;
  font-weight: 600;
}
.sa-kpi-card {
  flex: 1;
  min-width: 120px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  border-radius: 12px;
  padding: 12px;
  text-align: center;
  background: #fff;
}

.sa-kpi-card.is-explained {
  min-height: 92px;
  padding: 12px 14px;
  text-align: left;
}

.sa-kpi-card.is-subject-metric {
  position: relative;
  overflow: hidden;
  border-color: var(--metric-accent-border);
  background: linear-gradient(180deg, var(--metric-accent-soft) 0%, #ffffff 72%);
}

.sa-kpi-card.is-subject-metric::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: var(--metric-accent);
}

.sa-kpi-subject {
  margin-bottom: 4px;
  color: var(--metric-accent);
  font-size: 11px;
  font-weight: 800;
  line-height: 1.2;
}

.sa-kpi-card.is-subject-metric .sa-kpi-value {
  color: var(--metric-accent);
}

.sa-kpi-card.is-tone-good .sa-kpi-value {
  color: #00b42a;
}

.sa-kpi-card.is-tone-warn .sa-kpi-value {
  color: #ff7d00;
}

.sa-kpi-card.is-tone-danger .sa-kpi-value {
  color: #f53f3f;
}

.sa-kpi-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-primary);
  line-height: 1.2;
}
.sa-kpi-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
}

.sa-kpi-hint {
  margin-top: 7px;
  color: #667085;
  font-size: 11px;
  line-height: 1.45;
}
.sa-main-chart {
  height: 208px;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
  border: 1px solid rgba(29, 33, 41, 0.08);
}
.sa-insight-metric {
  min-height: 164px;
  border-radius: 12px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  background: linear-gradient(180deg, #fbfdff 0%, #f5f9ff 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 18px;
}
.sa-insight-metric-value {
  font-size: 25px;
  line-height: 1.2;
  font-weight: 700;
  color: #165dff;
}
.sa-insight-metric-label {
  margin-top: 7px;
  font-size: 11px;
  color: #86909c;
}
.sa-preview-table {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(29, 33, 41, 0.06);
}
.sa-report-md {
  font-size: 13px;
  line-height: 1.72;
  color: var(--text-title);
}
.sa-report-md :deep(h1),
.sa-report-md :deep(h2) {
  color: var(--color-primary);
  margin: 14px 0 7px;
}
.sa-report-md :deep(table) {
  width: 100%;
  border-collapse: collapse;
}
.sa-report-md :deep(td),
.sa-report-md :deep(th) {
  border: 1px solid var(--border);
  padding: 5px 8px;
  font-size: 12px;
  text-align: left;
  vertical-align: top;
}
.sa-report-md :deep(th) {
  background: var(--bg-muted);
  font-weight: 600;
}
.sa-download-row {
  text-align: center;
  padding-top: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}
.sa-primary-btn {
  height: 34px;
  padding: 0 16px;
  border-radius: 999px;
  background: linear-gradient(180deg, #2f6dff 0%, var(--color-primary) 100%);
  color: #fff;
  border: 1px solid rgba(22, 93, 255, 0.12);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow:
    0 10px 18px rgba(22, 93, 255, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.22);
}
.sa-primary-btn:hover {
  transform: translateY(-1px) scale(1.01);
  box-shadow:
    0 12px 22px rgba(22, 93, 255, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.26);
}

.sa-primary-btn:active {
  transform: scale(0.94);
}

.sa-secondary-btn,
.sa-ghost-btn {
  height: 34px;
  padding: 0 15px;
  border-radius: 999px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  background: rgba(255, 255, 255, 0.92);
  color: #4e5969;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
}

.sa-btn-label {
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}

.sa-btn-icon {
  position: relative;
  width: 14px;
  height: 14px;
  display: inline-flex;
  flex-shrink: 0;
}

.sa-btn-icon-stem,
.sa-btn-icon-head,
.sa-btn-icon-tray {
  position: absolute;
  box-sizing: border-box;
}

.sa-btn-icon-stem {
  left: 6px;
  top: 1px;
  width: 2px;
  height: 6px;
  background: currentColor;
  border-radius: 999px;
}

.sa-btn-icon-head {
  left: 4px;
  top: 5px;
  width: 6px;
  height: 6px;
  border-right: 2px solid currentColor;
  border-bottom: 2px solid currentColor;
  transform: rotate(45deg);
}

.sa-btn-icon-tray {
  position: absolute;
  left: 1px;
  right: 1px;
  bottom: 0;
  height: 4px;
  border: 2px solid currentColor;
  border-top: none;
  border-radius: 0 0 3px 3px;
  box-sizing: border-box;
}

.sa-secondary-btn:hover,
.sa-ghost-btn:hover {
  border-color: rgba(22, 93, 255, 0.18);
  background: rgba(240, 243, 255, 0.92);
  color: #255ee8;
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.05);
}

.sa-secondary-btn:active,
.sa-ghost-btn:active,
.sa-panel-close:active,
.sa-link-btn:active,
.sa-confirm-btn:active {
  transform: scale(0.96);
}

.sa-side-report {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 0 14px 14px;
  padding: 14px;
  border: 1px solid rgba(22, 93, 255, 0.12);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(240, 245, 255, 0.72) 0%, #ffffff 100%);
}

.sa-side-report-head {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.sa-side-report-titlebar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.sa-side-fullscreen-btn {
  flex-shrink: 0;
  height: 32px;
  padding: 0 12px;
}

.sa-side-confidence {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.sa-side-confidence-chip {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid rgba(29, 33, 41, 0.08);
  background: #ffffff;
  color: #4e5969;
}

.sa-side-confidence-chip.is-success {
  background: #e8ffea;
  border-color: rgba(0, 180, 42, 0.16);
  color: #00b42a;
}

.sa-side-confidence-chip.is-info {
  background: #edf4ff;
  border-color: rgba(22, 93, 255, 0.16);
  color: #165dff;
}

.sa-side-confidence-chip.is-warning {
  background: #fff7e8;
  border-color: rgba(255, 125, 0, 0.16);
  color: #ff7d00;
}

.sa-route-review-note {
  margin: 0;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(22, 93, 255, 0.06);
  color: #4e5969;
  font-size: 12px;
  line-height: 1.55;
}

.sa-side-report-kicker {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #165dff;
}

.sa-side-report-title {
  margin: 0;
  font-size: 16px;
  line-height: 1.4;
  color: #1d2129;
}

.sa-side-report-desc {
  margin: 0;
  font-size: 12px;
  line-height: 1.65;
  color: #4e5969;
}

.sa-business-report {
  gap: 12px;
}

.sa-management-narrative {
  display: grid;
  gap: 10px;
}

.sa-management-narrative.is-dialog {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.sa-management-narrative.is-single-focus,
.sa-management-narrative.is-dialog.is-single-focus {
  grid-template-columns: minmax(0, 1fr);
}

.sa-management-narrative-card {
  padding: 12px 14px;
  border: 1px solid #e8eefc;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.sa-management-narrative.is-single-focus .sa-management-narrative-card {
  border-radius: 8px;
  background: #ffffff;
}

.sa-management-narrative-title {
  margin-bottom: 8px;
  color: #165dff;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.35;
}

.sa-management-narrative.is-single-focus .sa-management-narrative-title {
  font-size: 14px;
}

.sa-management-narrative-body {
  color: #344054;
  font-size: 13px;
  line-height: 1.75;
}

.sa-management-narrative-body :deep(p) {
  margin: 0 0 8px;
}

.sa-management-narrative-body :deep(ul) {
  margin: 0;
  padding-left: 18px;
}

.sa-management-narrative-body :deep(li) {
  margin: 4px 0;
}

.sa-business-summary {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.sa-business-summary-text {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.75;
  color: #1d2129;
}

.sa-business-risk-pill,
.sa-office-rate {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  padding: 0 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.sa-business-risk-pill.good,
.sa-office-rate.good {
  color: #00b42a;
  background: #e8ffea;
}

.sa-business-risk-pill.warn,
.sa-office-rate.warn {
  color: #ff7d00;
  background: #fff7e8;
}

.sa-business-risk-pill.danger,
.sa-office-rate.danger {
  color: #f53f3f;
  background: #ffece8;
}

.sa-business-risk-pill.neutral,
.sa-office-rate.neutral {
  color: #4e5969;
  background: #f2f3f5;
}

.sa-office-rate {
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  line-height: 1.1;
}

.sa-office-rate small {
  font-size: 9px;
  font-weight: 600;
  color: currentColor;
  opacity: 0.8;
}

.sa-office-tag {
  margin-left: 6px;
  color: #4e5969;
  font-size: 11px;
  font-weight: 700;
}

.sa-kpi-shelf-compact .sa-kpi-card {
  min-width: calc(50% - 4px);
  padding: 10px;
}

.sa-office-overview-card {
  padding: 12px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  border-radius: 12px;
  background: #ffffff;
}

.sa-office-overview-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.sa-office-overview-chart {
  width: 100%;
  height: 320px;
  overflow: hidden;
}

.sa-office-overview-dialog {
  margin-bottom: 16px;
}

.sa-office-card-list,
.sa-office-report-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sa-office-report-grid {
  gap: 14px;
}

.sa-office-card {
  border: 1px solid var(--office-accent-border, rgba(29, 33, 41, 0.08));
  border-radius: 12px;
  background: #ffffff;
  overflow: hidden;
}

.sa-office-card-dialog {
  border-radius: 14px;
  border-color: var(--office-accent-border, rgba(29, 33, 41, 0.08));
}

.sa-office-card-head {
  width: 100%;
  min-height: 58px;
  border: none;
  background: #fbfcff;
  padding: 12px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  text-align: left;
  cursor: pointer;
}

.sa-office-card .sa-office-card-head {
  background: linear-gradient(90deg, var(--office-accent-soft, #fbfcff) 0%, #fbfcff 72%);
  border-left: 4px solid var(--office-accent, transparent);
}

.sa-office-card-dialog .sa-office-card-head {
  background: linear-gradient(90deg, var(--office-accent-soft, #fbfcff) 0%, #fbfcff 72%);
  border-left: 4px solid var(--office-accent, transparent);
}

.sa-office-card-head:hover {
  background: #f7faff;
}

.sa-office-head-main {
  flex: 1 1 auto;
  min-width: 0;
}

.sa-office-head-actions {
  flex: 0 0 auto;
  display: inline-flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  min-width: 0;
}

.sa-office-drill-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 48px;
  min-height: 24px;
  padding: 0 8px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.62);
  color: #4e5969;
  line-height: 1;
  opacity: 0.82;
  transition: border-color 0.18s ease, color 0.18s ease, background 0.18s ease, opacity 0.18s ease;
}

.sa-office-card-head:hover .sa-office-drill-toggle,
.sa-rep-drill-head:hover .sa-office-drill-toggle,
.sa-office-drill-toggle.is-open {
  border-color: var(--office-accent-border, rgba(22, 93, 255, 0.18));
  background: #ffffff;
  color: var(--office-accent, #165dff);
  opacity: 1;
}

.sa-office-drill-toggle span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
  font-weight: 800;
}

.sa-office-drill-toggle i {
  width: 6px;
  height: 6px;
  margin-top: -2px;
  border-right: 2px solid currentColor;
  border-bottom: 2px solid currentColor;
  transform: rotate(45deg);
  transition: transform 0.18s ease;
}

.sa-office-drill-toggle.is-open {
  background: var(--office-accent-soft, #f7faff);
}

.sa-office-drill-toggle.is-open i {
  margin-top: 2px;
  transform: rotate(225deg);
}

.sa-office-drill-toggle.is-small {
  min-width: 54px;
  min-height: 22px;
  padding: 0 7px;
}

.sa-office-drill-toggle.is-small span {
  font-size: 10px;
}

.sa-office-card .sa-office-card-head:hover {
  background: linear-gradient(90deg, var(--office-accent-soft, #f7faff) 0%, #f7faff 72%);
}

.sa-office-card-dialog .sa-office-card-head:hover {
  background: linear-gradient(90deg, var(--office-accent-soft, #f7faff) 0%, #f7faff 72%);
}

.sa-office-name {
  font-size: 14px;
  line-height: 1.4;
  font-weight: 700;
  color: #1d2129;
}

.sa-office-subtitle {
  margin-top: 4px;
  font-size: 11px;
  line-height: 1.45;
  color: #86909c;
}

.sa-office-kpis {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  padding: 10px 12px 0;
}

.sa-office-kpis span {
  min-width: 0;
  padding: 7px 8px;
  border-radius: 8px;
  background: #f7f8fa;
  color: #4e5969;
  font-size: 11px;
  line-height: 1.45;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sa-office-copy,
.sa-chart-copy {
  margin: 0;
  color: #4e5969;
  font-size: 12px;
  line-height: 1.75;
}

.sa-office-copy {
  padding: 10px 12px 12px;
}

.sa-office-drill {
  margin: 0 12px 12px;
  position: relative;
  padding: 12px 0 0 14px;
  border-top: 1px dashed rgba(29, 33, 41, 0.1);
}

.sa-office-drill::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 13px;
  bottom: 4px;
  width: 3px;
  border-radius: 999px;
  background: var(--office-accent-soft, rgba(22, 93, 255, 0.12));
  border: 1px solid var(--office-accent-border, rgba(22, 93, 255, 0.16));
}

.sa-drill-path {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: var(--office-accent-soft, #f7faff);
  color: #4e5969;
  font-size: 12px;
  font-weight: 700;
}

.sa-drill-path i {
  width: 18px;
  height: 1px;
  background: var(--office-accent, #165dff);
  position: relative;
}

.sa-drill-path i::after {
  content: '';
  position: absolute;
  right: -1px;
  top: -3px;
  width: 6px;
  height: 6px;
  border-top: 1px solid var(--office-accent, #165dff);
  border-right: 1px solid var(--office-accent, #165dff);
  transform: rotate(45deg);
}

.sa-drill-path strong {
  color: var(--office-accent, #165dff);
}

.sa-drill-insight-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.sa-drill-insight-card {
  min-width: 0;
  padding: 9px 10px;
  border-radius: 8px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  background: #ffffff;
}

.sa-drill-insight-card span {
  display: block;
  margin-bottom: 4px;
  color: #86909c;
  font-size: 11px;
  font-weight: 700;
}

.sa-drill-insight-card strong {
  display: block;
  color: #1d2129;
  font-size: 13px;
  line-height: 1.35;
}

.sa-drill-insight-card.is-good {
  border-color: rgba(0, 180, 42, 0.16);
  background: #f7fff9;
}

.sa-drill-insight-card.is-risk {
  border-color: rgba(245, 63, 63, 0.14);
  background: #fffafa;
}

.sa-chart-copy-drill {
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #fbfcff;
}

.sa-drill-table-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: -4px;
  color: #1d2129;
}

.sa-drill-table-head span {
  font-size: 13px;
  font-weight: 800;
}

.sa-drill-table-head small {
  color: #86909c;
  font-size: 11px;
  font-weight: 500;
}

.sa-office-drill-actions {
  display: flex;
  justify-content: flex-end;
  margin: 8px 0;
}

.sa-office-chart-open {
  height: 28px;
  padding: 0 10px;
  font-size: 11px;
}

.sa-office-chart {
  width: 100%;
  height: 260px;
  overflow: hidden;
  border-radius: 10px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  background: #fff;
}

.sa-office-empty-drill {
  margin-top: 8px;
  padding: 14px;
  border: 1px dashed rgba(24, 144, 255, 0.28);
  border-radius: 12px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  color: #64748b;
  font-size: 12px;
  line-height: 1.7;
}

.sa-office-chart-dialog {
  height: 320px;
}

.sa-office-detail-wrap {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
  margin-top: 10px;
}

.sa-office-detail-wrap.is-dialog {
  grid-template-columns: minmax(0, 1fr);
}

.sa-office-detail-table {
  overflow: hidden;
  border: 1px solid rgba(29, 33, 41, 0.08);
  border-radius: 8px;
  background: #ffffff;
}

.sa-office-detail-row {
  display: grid;
  grid-template-columns: minmax(82px, 1fr) minmax(118px, 1.12fr) minmax(78px, 0.78fr) minmax(66px, 0.64fr) minmax(124px, 1fr) minmax(74px, 0.74fr);
  gap: 8px;
  align-items: center;
  min-height: 36px;
  padding: 7px 10px;
  color: #344054;
  font-size: 11px;
  line-height: 1.35;
}

.sa-office-detail-row:nth-child(odd):not(.is-head) {
  background: #fbfcfd;
}

.sa-office-detail-row.is-head {
  min-height: 32px;
  color: #86909c;
  background: #f7f8fa;
  font-weight: 700;
}

.sa-detail-name {
  color: #1d2129;
  font-weight: 700;
}

.sa-detail-rate,
.sa-detail-tag {
  font-weight: 700;
}

.sa-detail-progress {
  min-width: 0;
}

.sa-detail-rate.good,
.sa-detail-tag.good {
  color: #00b42a;
}

.sa-detail-rate.warn,
.sa-detail-tag.warn {
  color: #ff7d00;
}

.sa-detail-rate.danger,
.sa-detail-tag.danger {
  color: #f53f3f;
}

.sa-office-bars {
  display: grid;
  gap: 8px;
  align-content: start;
}

.sa-office-bar-row {
  display: grid;
  grid-template-columns: minmax(54px, 74px) minmax(0, 1fr) minmax(48px, 64px);
  gap: 8px;
  align-items: center;
  color: #4e5969;
  font-size: 11px;
  line-height: 1.35;
}

.sa-office-bar-row span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sa-office-bar-row strong {
  color: #1d2129;
  font-size: 11px;
  text-align: right;
}

.sa-office-bar-row.is-gap {
  margin-top: -2px;
}

.sa-office-bar-track {
  display: block;
  position: relative;
  height: 8px;
  width: 100%;
  overflow: hidden;
  border-radius: 999px;
  background: #eef2f7;
}

.sa-office-bar-track i,
.sa-office-bar-track b {
  position: absolute;
  inset: 0 auto 0 0;
  min-width: 2px;
  border-radius: inherit;
}

.sa-office-bar-track .is-rate.good {
  background: #00b42a;
}

.sa-office-bar-track .is-rate.warn {
  background: #ffb020;
}

.sa-office-bar-track .is-rate.danger {
  background: #f53f3f;
}

.sa-office-bar-track .is-gap {
  background: #ff9a2e;
}

.sa-compare-matrix {
  overflow: hidden;
  border: 1px solid rgba(29, 33, 41, 0.08);
  border-radius: 8px;
  background: #ffffff;
}

.sa-compare-row {
  position: relative;
  width: 100%;
  display: grid;
  grid-template-columns: minmax(110px, 1.05fr) minmax(88px, 0.8fr) minmax(88px, 0.8fr) minmax(88px, 0.8fr) minmax(70px, 0.65fr) minmax(220px, 1.4fr) minmax(82px, 0.75fr);
  gap: 10px;
  align-items: center;
  min-height: 44px;
  padding: 9px 12px;
  border: 0;
  border-bottom: 1px solid rgba(29, 33, 41, 0.06);
  background: transparent;
  color: #344054;
  font-size: 12px;
  line-height: 1.35;
  text-align: left;
}

.sa-compare-row:not(.is-head) {
  background: linear-gradient(90deg, var(--office-accent-soft, transparent) 0%, #ffffff 46%);
}

.sa-compare-row:not(.is-head)::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: var(--office-accent);
}

.sa-compare-row:last-child {
  border-bottom: 0;
}

button.sa-compare-row {
  cursor: pointer;
}

button.sa-compare-row:hover {
  background: linear-gradient(90deg, var(--office-accent-soft, #f8fbff) 0%, #f8fbff 70%);
}

.sa-compare-row.is-head {
  min-height: 36px;
  color: #86909c;
  background: #f7f8fa;
  font-weight: 700;
}

.sa-compare-row span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sa-compare-matrix.is-compact .sa-compare-row {
  grid-template-columns: minmax(78px, 1fr) minmax(64px, 0.75fr) minmax(64px, 0.75fr) minmax(62px, 0.75fr) minmax(58px, 0.7fr) minmax(92px, 1fr) minmax(70px, 0.72fr);
  min-height: 38px;
  padding: 8px 10px;
  gap: 7px;
  font-size: 11px;
}

.sa-compare-matrix.is-compact .sa-compare-row.is-head {
  min-height: 32px;
}

.sa-compare-matrix.is-compact .sa-office-bar-track {
  height: 7px;
}

.sa-compare-row .sa-detail-name {
  color: var(--office-accent);
}

.sa-compare-row .sa-detail-rate {
  color: var(--office-accent);
}

.sa-compare-row .sa-office-bar-track .is-rate {
  background: var(--office-accent);
}

.sa-rep-drill-list {
  grid-column: 1 / -1;
  display: grid;
  gap: 8px;
  margin-top: 2px;
  padding-top: 10px;
  border-top: 1px solid rgba(29, 33, 41, 0.08);
}

.sa-rep-drill-list.is-dialog {
  margin-top: 4px;
}

.sa-rep-drill-title {
  color: #4e5969;
  font-size: 12px;
  font-weight: 700;
}

.sa-rep-drill-card {
  overflow: hidden;
  border: 1px solid rgba(29, 33, 41, 0.08);
  border-radius: 8px;
  background: #fbfcff;
}

.sa-rep-drill-head {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 9px 10px;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.sa-rep-drill-head:hover {
  background: rgba(24, 144, 255, 0.05);
}

.sa-rep-drill-name {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #1d2129;
  font-size: 13px;
  font-weight: 800;
}

.sa-rep-drill-subtitle {
  margin-top: 2px;
  color: #86909c;
  font-size: 11px;
}

.sa-rep-drill-summary {
  margin: 0;
  padding: 0 10px 9px;
  color: #4e5969;
  font-size: 12px;
  line-height: 1.6;
}

.sa-rep-person-table {
  margin: 0 10px 10px;
}

@media (max-width: 900px) {
  .sa-office-detail-wrap,
  .sa-office-detail-wrap.is-dialog {
    grid-template-columns: minmax(0, 1fr);
  }

  .sa-drill-insight-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .sa-drill-table-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 3px;
  }

  .sa-office-detail-table {
    overflow-x: auto;
  }

  .sa-office-detail-row {
    min-width: 760px;
  }

  .sa-compare-matrix {
    overflow-x: auto;
  }

  .sa-compare-row {
    min-width: 860px;
  }

  .sa-management-narrative.is-dialog {
    grid-template-columns: minmax(0, 1fr);
  }
}

.sa-wide-btn {
  width: 100%;
}

.sa-side-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid rgba(29, 33, 41, 0.08);
}

.sa-side-section-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #86909c;
}

/* 内嵌图表 */
.sa-chart-embed {
  height: 188px;
  margin: 6px 0;
  border-radius: 6px;
  overflow: hidden;
  background: #fff;
  border: 1px solid rgba(29, 33, 41, 0.08);
}

.sa-chart-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

/* mini 表格 */
.sa-mini-table-wrap {
  margin: 0;
}
.sa-mini-table {
  border-radius: 6px;
  overflow: hidden;
}
.sa-table-more {
  text-align: center;
  padding: 5px;
  font-size: 11px;
  color: var(--text-muted);
}

.sa-mini-table :deep(.el-table__header-wrapper th) {
  background: #f7f8fa;
  color: #4e5969;
  font-size: 11px;
  font-weight: 600;
  height: 34px;
  text-align: left;
}

.sa-mini-table :deep(.el-table__body-wrapper td) {
  font-size: 11px;
  color: #1d2129;
  text-align: left;
}

.sa-mini-table :deep(.el-table__row:nth-child(even) td) {
  background: #fbfcfd;
}

.sa-mini-table :deep(.el-table__inner-wrapper::before) {
  display: none;
}

.sa-preview :deep(.el-table__header-wrapper th) {
  background: #f7f8fa;
  color: #4e5969;
  font-size: 11px;
  font-weight: 600;
  height: 34px;
  text-align: left;
}

.sa-preview :deep(.el-table__body-wrapper td) {
  font-size: 11px;
  color: #1d2129;
  text-align: left;
}

.sa-preview :deep(.el-table__row:nth-child(even) td) {
  background: #fbfcfd;
}

.sa-preview :deep(.el-table__inner-wrapper::before) {
  display: none;
}

.sa-side-extra-charts {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
  margin-top: 12px;
}

.sa-side-chart-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
}

.sa-side-extra-chart-card {
  padding: 12px 12px 10px;
  border-radius: 14px;
  border: 1px solid rgba(22, 93, 255, 0.08);
  background: #fbfcff;
}

.sa-side-extra-chart-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.sa-side-extra-chart-title {
  font-size: 13px;
  font-weight: 700;
  color: #1d2129;
}

.sa-side-extra-chart-action {
  height: 26px;
  padding: 0 10px;
  font-size: 11px;
}

.sa-side-extra-chart-canvas {
  width: 100%;
  height: 220px;
}

.sa-insight-metric-compact {
  min-height: 180px;
}

/* 日志时间 */
.sa-log-time {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: #f7f8fa;
  color: var(--text-muted);
  font-size: 12px;
  margin-top: 8px;
}

.sa-log-time-label {
  color: #4e5969;
  font-weight: 600;
}

.sa-log-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}

.sa-log-section-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #86909c;
}

.sa-log-inline-action {
  align-self: flex-end;
}

.sa-log-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.sa-log-markdown {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  background: #fbfcfe;
  font-size: 12px;
  line-height: 1.8;
  color: #1d2129;
}

.sa-log-markdown :deep(h1),
.sa-log-markdown :deep(h2),
.sa-log-markdown :deep(h3) {
  margin: 0 0 8px;
  color: #165dff;
  font-size: 13px;
}

.sa-log-markdown :deep(p),
.sa-log-markdown :deep(ul),
.sa-log-markdown :deep(ol) {
  margin: 0 0 8px;
}

.sa-log-markdown :deep(ul),
.sa-log-markdown :deep(ol) {
  padding-left: 18px;
}

.sa-report-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

:deep(.sa-report-dialog .el-dialog__header) {
  display: none;
}

.sa-report-dialog-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 2px 2px 12px;
  border-bottom: 1px solid rgba(29, 33, 41, 0.08);
}

.sa-report-dialog-title-block {
  min-width: 0;
  flex: 1;
}

.sa-report-dialog-title {
  margin: 6px 0 0;
  font-size: 24px;
  line-height: 1.22;
  font-weight: 700;
  color: #1d2129;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sa-report-dialog-subtitle {
  margin: 7px 0 0;
  max-width: min(980px, 72vw);
  color: #4e5969;
  font-size: 14px;
  line-height: 1.45;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sa-report-dialog-content {
  max-height: 72vh;
  overflow-y: auto;
  padding: 2px 6px 8px 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sa-report-dialog-overview {
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  gap: 14px;
}

.sa-report-dialog-content.is-template-comparison .sa-report-dialog-overview {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.sa-report-dialog-content.is-template-ranking .sa-report-chart-grid {
  grid-template-columns: minmax(0, 1fr);
}

.sa-report-dialog-content.is-template-detail .sa-report-dialog-overview {
  grid-template-columns: minmax(0, 1fr);
}

.sa-report-dialog-content.is-template-detail .sa-report-stage-metrics .sa-kpi-shelf {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.sa-report-stage-section {
  max-width: 1120px;
  width: 100%;
  margin: 0 auto;
  padding: 16px 18px 16px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.sa-report-stage-summary {
  background: linear-gradient(180deg, #ffffff 0%, #fbfcff 100%);
}

.sa-report-stage-metrics {
  align-self: stretch;
}

.sa-report-stage-metrics .sa-kpi-shelf {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.sa-report-stage-metrics .sa-kpi-card {
  min-width: 0;
}

.sa-report-stage-title {
  margin-bottom: 12px;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.25;
  color: #1d2129;
}

.sa-report-core-conclusion {
  display: grid;
  gap: 5px;
  margin: 0 0 12px;
  padding: 12px 14px;
  border: 1px solid rgba(22, 93, 255, 0.14);
  border-radius: 8px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.sa-report-core-conclusion span {
  color: #165dff;
  font-size: 12px;
  font-weight: 800;
}

.sa-report-core-conclusion strong {
  color: #1d2129;
  font-size: 15px;
  line-height: 1.7;
  font-weight: 800;
}

.sa-report-bullet-list {
  margin: 0;
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #1d2129;
  font-size: 14px;
  line-height: 1.8;
}

.sa-report-bullet-list-compact {
  gap: 6px;
  font-size: 13px;
  line-height: 1.7;
  margin-bottom: 12px;
}

.sa-report-sections {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sa-report-section-card {
  padding: 12px 14px 12px;
  border-radius: 8px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  background: #fbfcff;
}

.sa-report-section-card-dialog {
  padding: 16px 18px 16px;
  border-radius: 8px;
  background: #ffffff;
}

.sa-report-section-title {
  margin-bottom: 10px;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.35;
  color: #1d2129;
}

.sa-report-chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.sa-report-chart-card {
  padding: 14px 14px 12px;
  border-radius: 8px;
  border: 1px solid rgba(22, 93, 255, 0.1);
  background: #ffffff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.sa-report-chart-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.sa-report-chart-title {
  font-size: 16px;
  font-weight: 700;
  color: #1d2129;
}

.sa-report-chart-subtitle {
  margin-top: 3px;
  font-size: 12px;
  color: #86909c;
}

.sa-report-chart-canvas {
  width: 100%;
  height: 280px;
}

.sa-report-table-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 10px;
}

.sa-report-table-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.sa-report-table-card {
  padding: 14px 14px 12px;
  border-radius: 16px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  background: #fbfcff;
}

.sa-report-table-card-dialog {
  background: #ffffff;
}

.sa-report-table-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.sa-report-table-title {
  font-size: 16px;
  font-weight: 700;
  color: #1d2129;
}

.sa-report-table-desc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.7;
  color: #86909c;
}

.sa-preview-table-report {
  margin-top: 2px;
}

.sa-preview-table-report :deep(.el-table__header-wrapper th) {
  background: #f7f8fa;
  color: #4e5969;
  font-size: 11px;
  font-weight: 600;
  height: 34px;
  text-align: left;
}

.sa-preview-table-report :deep(.el-table__body-wrapper td) {
  font-size: 11px;
  color: #1d2129;
  text-align: left;
}

.sa-preview-table-report :deep(.el-table__row:nth-child(even) td) {
  background: #fbfcfd;
}

.sa-preview-table-report :deep(.el-table__inner-wrapper::before) {
  display: none;
}

.sa-preview-table-report-dialog :deep(.el-table__body-wrapper) {
  max-height: 360px;
  overflow-y: auto;
}

.sa-insight-metric-report {
  min-height: 280px;
}

.sa-report-md-compact {
  font-size: 12px;
  line-height: 1.8;
}

@media (max-width: 1100px) {
  .sa-report-dialog-overview {
    grid-template-columns: 1fr;
  }

  .sa-report-chart-grid {
    grid-template-columns: 1fr;
  }

  .sa-report-table-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .sa-report-dialog-title {
    font-size: 21px;
  }

  .sa-report-stage-section {
    padding: 14px 14px 14px;
  }

  .sa-report-stage-title {
    font-size: 18px;
  }

  .sa-report-bullet-list {
    font-size: 13px;
  }

  .sa-report-chart-grid {
    grid-template-columns: 1fr;
  }

  .sa-report-chart-canvas,
  .sa-insight-metric-report {
    height: 240px;
    min-height: 240px;
  }
}

.sa-chart-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 420px;
}

@keyframes sa-curtain-open {
  from {
    opacity: 0;
    clip-path: inset(0 0 100% 0 round 18px);
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    clip-path: inset(0 0 0 0 round 18px);
    transform: translateY(0);
  }
}

@keyframes sa-stop-beam {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.sa-chart-dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sa-chart-dialog-kicker {
  font-size: 11px;
  letter-spacing: 0.08em;
  color: #86909c;
}

.sa-chart-dialog-switch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px;
  border-radius: 999px;
  background: #f2f3f5;
}

.sa-chart-switch-btn {
  border: none;
  background: transparent;
  color: #4e5969;
  font-size: 12px;
  line-height: 1;
  padding: 8px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.sa-chart-switch-btn.is-active {
  background: #ffffff;
  color: #165dff;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
}

.sa-chart-dialog-canvas {
  width: 100%;
  height: 68vh;
  min-height: 420px;
}

.sa-chart-dialog-table {
  border: 1px solid rgba(29, 33, 41, 0.08);
  border-radius: 16px;
  overflow: hidden;
  background: #ffffff;
}

.sa-chart-dialog-table-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  font-size: 12px;
  color: #86909c;
  background: #f7f8fa;
  border-bottom: 1px solid rgba(29, 33, 41, 0.06);
}

.sa-insight-metric-large {
  min-height: 420px;
}

/* 动画 */
.sa-collapse-enter-active,
.sa-collapse-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}
.sa-collapse-enter-from,
.sa-collapse-leave-to {
  opacity: 0;
  max-height: 0;
}
.sa-collapse-enter-to,
.sa-collapse-leave-from {
  opacity: 1;
  max-height: 800px;
}

.sa-slide-up-enter-active,
.sa-slide-up-leave-active {
  transition: all 0.2s ease;
}
.sa-slide-up-enter-from,
.sa-slide-up-leave-to {
  transform: translateY(10px);
  opacity: 0;
}

.sa-panel-slide-enter-active,
.sa-panel-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.sa-panel-slide-enter-from,
.sa-panel-slide-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

/* 滚动区 */
.sa-chat-body::-webkit-scrollbar,
.sa-panel-content::-webkit-scrollbar {
  width: 5px;
}
.sa-chat-body::-webkit-scrollbar-thumb,
.sa-panel-content::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 10px;
}

@media (max-width: 1280px) {
  .sa-page {
    padding: 16px;
  }

  .sa-detail-panel {
    width: 400px;
    max-width: 42vw;
  }
}

@media (max-width: 1080px) {
  .sa-page {
    height: 100%;
    min-height: 0;
  }

  .sa-workspace {
    flex-direction: column;
  }

  .sa-detail-panel {
    width: 100%;
    max-width: none;
    border-left: none;
    border-top: 1px solid rgba(29, 33, 41, 0.08);
    min-height: 320px;
    max-height: 42vh;
  }
}
</style>

