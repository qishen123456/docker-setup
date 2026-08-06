<template>
  <div class="sa-page">
    <div class="sa-shell">
      <section class="sa-workspace" :class="{ 'is-detail-hidden': !detailPanelVisible }">
        <!-- 📌 左侧/中间 对话区-->
        <div class="sa-chat-panel" :class="{ 'is-detail-hidden': !detailPanelVisible }">
          <!-- 头部组件-->
          <div class="sa-content-track sa-header-track">
            <ChatHeader
              :show-panel="detailPanelVisible"
              :allow-toggle-panel="featureAccess.debug_execution_trace"
              :allow-new-chat="featureAccess.smart_new_chat"
              @toggle-panel="togglePanel"
              @new-chat="handleNewChat"
              @show-history="focusSidebarHistory"
            />
          </div>

          <!-- 只读视图提示：正在查看历史，后台有任务执行中/待确认/已完成/失败 -->
          <div v-if="isViewingReadonly && runningTaskStatus !== 'idle'" class="sa-readonly-banner" :class="`banner-${runningTaskStatus}`" @click="handleReturnToRunning">
            <span v-if="runningTaskStatus === 'running'" class="sa-readonly-banner-icon sa-spin-ring-small">
              <span class="sa-spin-ring-track-small"></span>
              <span class="sa-spin-ring-bar-small"></span>
            </span>
            <span v-else-if="runningTaskStatus === 'pending_confirmation'" class="sa-readonly-banner-icon">⚠️</span>
            <span v-else-if="runningTaskStatus === 'completed'" class="sa-readonly-banner-icon">✅</span>
            <span v-else class="sa-readonly-banner-icon">❌</span>
            <span class="sa-readonly-banner-text">
              <template v-if="runningTaskStatus === 'running'">正在查看历史任务，后台有任务正在执行中，点击此处跳回执行中的任务</template>
              <template v-else-if="runningTaskStatus === 'pending_confirmation'">后台任务需要确认口径，点击此处返回确认</template>
              <template v-else-if="runningTaskStatus === 'completed'">后台任务已执行完成，点击此处查看结果</template>
              <template v-else>后台任务执行失败，点击此处查看详情</template>
            </span>
            <!-- i18n: smartask.task.readonlyBanner -->
          </div>

          <!-- 会话滚动区-->
          <div class="sa-chat-body" ref="chatBodyRef">
            <div class="sa-content-track sa-chat-content">
            <!-- 欢迎首屏 -->
            <WelcomeScreen
              v-if="messages.length === 0"
              :common-questions="commonQuestions"
              :common-questions-loading="commonQuestionsLoading"
              :allow-quick-ask="featureAccess.smart_quick_ask"
              :allow-refresh-questions="featureAccess.smart_quick_refresh"
              @quick-ask="quickAsk"
              @refresh-questions="refreshCommonQuestions"
            />

            <!-- 消息列表 -->
            <div class="sa-msg-list">
              <div v-for="msg in displayMessages" :key="msg.id" class="sa-msg-wrap">
                <!-- 用户气泡 -->
                <UserBubble
                  v-if="msg.role === 'user'"
                  :content="msg.content"
                  :disabled="isRunning"
                  :allow-copy="featureAccess.smart_question_copy"
                  :allow-edit="featureAccess.smart_question_edit"
                  :allow-rerun="featureAccess.smart_question_rerun"
                  @copy="copyQuestion(msg)"
                  @edit="editQuestion(msg)"
                  @rerun="rerunQuestion(msg)"
                />

                <!-- AI 回复 -->
                <div v-else class="sa-ai-wrap">
                  <div class="sa-ai-meta">
                    <div class="sa-ai-avatar" aria-label="安吉尔经营分析助手头像">
                      <svg class="sa-ai-avatar-svg" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">
                        <defs>
                          <linearGradient id="aiAuraChat" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stop-color="#F51F19" />
                            <stop offset="100%" stop-color="#FFA07A" />
                          </linearGradient>
                          <linearGradient id="innerBgChatAi" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stop-color="#FFFFFF" />
                            <stop offset="100%" stop-color="#F8FAFC" />
                          </linearGradient>
                        </defs>
                        <circle cx="50" cy="50" r="45" stroke="url(#aiAuraChat)" stroke-width="2.5" />
                        <circle cx="50" cy="50" r="40" fill="url(#innerBgChatAi)" />
                        <circle cx="50" cy="50" r="32" stroke="#E2E8F0" stroke-width="1" stroke-dasharray="2 2" />
                        <path d="M50 31 L25 73 L37 73 L50 52 L63 73 L75 73 Z" fill="#F51F19" />
                      </svg>
                    </div>
                    <span class="sa-ai-name">安吉尔经营分析顾问</span>
                  </div>
                  <div class="sa-ai-cards">
                    <!-- 加载中-->
                    <div v-if="msg.loading && !displayLogs.length" class="sa-thinking-loading">
                      <div class="sa-dots">
                        <span></span><span></span><span></span>
                      </div>
                      <span class="sa-thinking-text">正在分析问题意图并规划路径...</span>
                    </div>

                    <!-- 执行进度卡-->
                    <LiveExecutionFeed
                      v-if="shouldShowLiveFeed(msg)"
                      :logs="displayLogs"
                      :mode="getLiveFeedMode(msg)"
                      :max-items="6"
                      :elapsed-label="getMessageElapsedLabel(msg)"
                      :force-expanded="isViewingReadonly"
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
                      <div class="sa-flow-handoff-top">
                        <div class="sa-flow-handoff-kicker">执行已完成</div>
                        <span v-if="getAskFlowLabel(msg)" class="sa-flow-badge" :class="getAskFlowClass(msg)">
                          {{ getAskFlowLabel(msg) }}
                        </span>
                      </div>
                      <div class="sa-flow-handoff-title">正在整理结果摘要与报告内容</div>
                      <div class="sa-flow-handoff-desc">
                        执行轨迹已经沉淀完成，下面将继续承接结果摘要、报告内容和附件产物。                      </div>
                    </div>

                    <div v-if="shouldShowConfirmationCard(msg)" class="sa-card sa-confirm-card">
                      <div class="sa-confirm-header">
                        <span class="sa-confirm-badge">需要确认</span>
                        <span class="sa-confirm-q">{{ msg.data.confirmation_question }}</span>
                      </div>
                      <div class="sa-confirm-opts">
                        <div class="sa-confirm-list">
                          <button
                            v-for="(opt, idx) in visibleConfirmationOptions(msg)"
                            :key="getConfirmOptionKey(opt)"
                            class="sa-confirm-row"
                            :class="{ 'sa-confirm-row-top': idx === 0 }"
                            :disabled="isRunning || confirmationSubmitting[msg.id]"
                            @click.stop.prevent="doConfirm(opt, msg)"
                          >
                            <span class="sa-confirm-rank">{{ idx + 1 }}</span>
                            <span class="sa-confirm-info">
                              <span class="sa-confirm-row-label">
                                {{ getConfirmOptionLabel(opt) }}
                                <span v-if="idx === 0" class="sa-confirm-recommended">推荐</span>
                              </span>
                              <span v-if="getConfirmOptionDescription(opt)" class="sa-confirm-row-desc">
                                {{ getConfirmOptionDescription(opt) }}
                              </span>
                            </span>
                            <span class="sa-confirm-spacer"></span>
                            <span v-if="shouldShowConfirmOptionScore(msg, opt)" class="sa-confirm-score">
                              {{ getConfirmOptionScore(opt) }}分
                            </span>
                          </button>
                        </div>
                        <button
                          v-if="(msg.data.confirmation_options || []).length > 4"
                          class="sa-confirm-toggle"
                          :disabled="isRunning || confirmationSubmitting[msg.id]"
                          @click.stop.prevent="toggleConfirmOptions(msg.id)"
                        >
                          {{ confirmExpanded[msg.id] ? '收起' : `展开更多 (${msg.data.confirmation_options.length - 4})` }}
                        </button>
                      </div>
                      <div class="sa-confirm-freeform">
                        <textarea
                          v-model="confirmationDrafts[msg.id]"
                          class="sa-confirm-textarea"
                          :disabled="isRunning || confirmationSubmitting[msg.id]"
                          placeholder="都不合适？补充说明继续分析，例如：按华东区域分公司口径。"
                          @keydown.enter.exact.prevent="handleConfirmationDraftEnter($event, msg)"
                          @click.stop
                        ></textarea>
                        <button
                          class="sa-confirm-send"
                          :disabled="isRunning || confirmationSubmitting[msg.id] || !String(confirmationDrafts[msg.id] || '').trim()"
                          @click.stop.prevent="submitConfirmationDraft(msg)"
                        >
                          发送补充说明
                        </button>
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
                      :ref="el => setResultChainRef(msg.id, el)"
                    >
                    <ResultDigestCard
                      v-if="getReport(msg) || getPrimaryDataset(msg)"
                      :title="getResultTitle(msg)"
                      :display-title="msg.data?.display_title || ''"
                      :question="msg.data?.question || session.state.question"
                      :report="getReport(msg)"
                      :dataset="getPrimaryDataset(msg)"
                      :datasets="getDatasets(msg)"
                      :route="msg.data?.route || null"
                      :flow-label="getAskFlowLabel(msg)"
                      :flow-class="getAskFlowClass(msg)"
                      :flow-hint="getAskFlowHint(msg)"
                      :show-details-button="featureAccess.smart_report_details"
                      @view-details="openDetailPanel(msg)"
                    />

                    <div
                      v-else-if="shouldShowResultChain(msg)"
                      class="sa-result-empty"
                    >
                      <div class="sa-result-empty-icon">📭</div>
                      <div class="sa-result-empty-title">未查询到可用数据</div>
                      <div class="sa-result-empty-desc">
                        执行链路已完成，但当前结果中没有可展示的数据。可能原因：当前账号权限范围未覆盖该对象、问题条件未命中任何记录，或数据集配置已变更。可尝试切换账号、调整问题范围，或联系管理员检查数据权限。
                      </div>
                    </div>

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
                            <button v-if="featureAccess.chart_viewer" class="sa-ghost-btn" @click="openChartViewer(preview.chartSpec, `${preview.dataset.dataset_name} 图表预览`)">
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

                    <!-- 状态提示卡-->
                    </div>
                    <div v-if="msg.data?.aborted" class="sa-card sa-cancel-card">
                      <span class="sa-cancel-icon" aria-hidden="true">
                        <span class="sa-cancel-icon-core"></span>
                      </span>
                      <div class="sa-cancel-copy">
                        <div class="sa-cancel-kicker">FLOW INTERRUPTED</div>
                        <div class="sa-cancel-title">本轮问数已取消</div>
                        <div class="sa-cancel-desc">执行链路已关闭，不会继续生成 SQL、图表或报告。</div>
                      </div>
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
          </div>

          <!-- 底部输入区-->
          <div class="sa-content-track sa-composer-track">
            <ComposerArea
              :class="{ 'sa-composer-narrow': !detailPanelVisible }"
              v-model:query="query"
              v-model:dataset-id="datasetId"
              v-model:model-id="modelId"
              :datasets="datasets"
              :ai-models="aiModels"
              :is-running="isRunning"
              :disabled="isViewingReadonly"
              :allow-send="featureAccess.smart_send_question"
              :allow-stop="featureAccess.smart_stop_run"
              :allow-dataset-select="featureAccess.smart_dataset_select"
              :allow-model-select="featureAccess.smart_model_select"
              :status-text="isRunning || session.state.status === 'completed' ? statusBarText : ''"
              :status-elapsed="isRunning ? `${elapsed}s` : ''"
              :status-tone="session.state.status"
              :status-flow-label="activeAskFlowLabel"
              :status-flow-class="activeAskFlowClass"
              :status-flow-hint="activeAskFlowLabel ? activeAskFlowHint : ''"
              @send="handleSend"
              @stop="handleStop"
              @dataset-change="handleDatasetChange"
            />
          </div>
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
                :logs="displayLogs"
                :open-state="logOpen"
                @toggle="toggleLog"
              >
                <template #content="{ log, index }">
                  <div v-if="log.sql" class="sa-log-section">
                    <div class="sa-log-section-title">{{ log.sqlTitle || '生成 SQL' }}</div>
                    <SqlBlock :sql="log.sql" :allow-copy="featureAccess.smart_sql_copy" />
                  </div>

                  <div v-if="log.chartData" class="sa-log-section">
                    <div class="sa-log-section-title">{{ log.chartTitle || '图表预览' }}</div>
                    <button v-if="featureAccess.chart_viewer" class="sa-ghost-btn sa-log-inline-action" @click="openChartViewer(log.chartData, log.chartTitle || '图表预览')">放大查看</button>
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
                      <div v-if="activeAskFlowLabel" class="sa-side-flow-line">
                        <span :class="['sa-flow-badge', activeAskFlowClass]">{{ activeAskFlowLabel }}</span>
                        <small>{{ activeAskFlowHint }}</small>
                      </div>
                    </div>
                    <button v-if="featureAccess.report_fullscreen" class="sa-primary-btn sa-side-fullscreen-btn" @click="openFullScreenReport">
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
                  <div v-if="routeDecisionDetail" class="sa-route-decision">
                    {{ routeDecisionDetail }}
                  </div>
                </div>

                <section
                  v-if="businessDrillReport"
                  class="sa-side-section sa-business-report"
                  :class="{ 'is-single-focus': businessDrillReport.isSingleFocus }"
                >
                  <div v-if="businessDrillReport.primaryAnswer" class="sa-filter-answer-card">
                    <div class="sa-filter-answer-head">
                      <div>
                        <div class="sa-side-section-title">{{ businessDrillReport.primaryAnswer.title || '主回答' }}</div>
                        <p class="sa-business-summary-text">{{ businessDrillReport.primaryAnswer.text }}</p>
                      </div>
                      <span class="sa-business-risk-pill" :class="businessDrillReport.answerMode === 'ranking' ? 'good' : 'warn'">
                        {{ businessDrillReport.primaryAnswer.targetLevel || businessDrillReport.compareLevelLabel }}
                      </span>
                    </div>
                  </div>
                  <div v-if="businessDrillReport.filterAnswer" class="sa-filter-answer-card">
                    <div class="sa-filter-answer-head">
                      <div>
                        <div class="sa-side-section-title">{{ businessDrillReport.filterAnswer.title || '命中结果' }}</div>
                        <p class="sa-business-summary-text">{{ businessDrillReport.filterAnswer.text }}</p>
                      </div>
                      <span class="sa-business-risk-pill" :class="businessDrillReport.filterAnswer.nodes?.length ? 'warn' : 'good'">
                        {{ businessDrillReport.filterAnswer.nodes?.length || 0 }} 个
                      </span>
                    </div>
                    <div v-if="businessDrillReport.filterAnswer.nodes?.length" class="sa-filter-answer-list">
                      <button
                        v-for="node in businessDrillReport.filterAnswer.nodes"
                        :key="`filter-answer-${node.id}`"
                        class="sa-filter-answer-row"
                        type="button"
                        @click="toggleOfficeDrill(node.id)"
                      >
                        <span class="sa-filter-answer-name">{{ node.name }}</span>
                        <span class="sa-filter-answer-metric">{{ node.metricLabel }} {{ node.metricValue }}</span>
                        <span v-if="node.tag" class="sa-detail-tag" :class="node.tone">{{ node.tag }}</span>
                      </button>
                    </div>
                  </div>
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
                      <p class="sa-business-summary-text">{{ sideBusinessSummaryText }}</p>
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
                        @click="canToggleOffice(office) && toggleOfficeDrill(office.id)"
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
                        @click="canToggleOffice(office) && toggleOfficeDrill(office.id)"
                      >
                        <div class="sa-office-head-main">
                          <div class="sa-office-name">{{ office.name }} <span class="sa-office-tag">{{ office.tag }}</span></div>
                          <div class="sa-office-subtitle">{{ getOfficeSubtitle(office, businessDrillReport) }}</div>
                        </div>
                        <span class="sa-office-head-actions">
                          <span class="sa-office-rate" :class="office.tone">{{ office.rateLabel }}<small v-if="office.rankLabel">{{ office.rankLabel }}</small></span>
                          <span
                            v-if="canToggleOffice(office)"
                            class="sa-office-drill-toggle"
                            :class="{ 'is-open': isOfficeExpanded(office.id) }"
                            :title="isOfficeExpanded(office.id) ? '收起明细' : getOfficeToggleTitle(office, businessDrillReport)"
                          >
                            <span>{{ isOfficeExpanded(office.id) ? '收起' : '下钻' }}</span>
                            <i></i>
                          </span>
                          <span v-else class="sa-office-leaf-pill">当前最细层</span>
                        </span>
                      </button>
                      <div class="sa-office-kpis">
                        <span v-for="item in office.kpis" :key="item.label">{{ item.label }} {{ item.value }}</span>
                      </div>
                      <p class="sa-office-copy">{{ office.summary }}</p>
                      <div v-if="canToggleOffice(office) && isOfficeExpanded(office.id)" class="sa-office-drill">
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
                          {{ getOfficeEmptyDrillText(office, businessDrillReport) }}
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
                        <button v-if="featureAccess.chart_viewer" class="sa-ghost-btn sa-side-extra-chart-action" @click="openChartViewer(chart.chartSpec, `${chart.dataset.dataset_name} ${chart.chartSpec.title || chart.caption}`)">
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
                    <button v-if="featureAccess.chart_viewer" class="sa-ghost-btn" @click="openChartViewer(preview.chartSpec, `${preview.dataset.dataset_name} 图表预览`)">放大查看</button>
                  </div>

                  <div v-if="preview.extraCharts?.length" class="sa-side-extra-charts">
                    <article
                      v-for="(chartSpec, chartIndex) in preview.extraCharts.slice(0, 2)"
                      :key="`${preview.key}-extra-${chartIndex}`"
                      class="sa-side-extra-chart-card"
                    >
                      <div class="sa-side-extra-chart-head">
                        <div class="sa-side-extra-chart-title">{{ chartSpec.title || `图表 ${chartIndex + 1}` }}</div>
                        <button v-if="featureAccess.chart_viewer" class="sa-ghost-btn sa-side-extra-chart-action" @click="openChartViewer(chartSpec, `${preview.dataset.dataset_name} ${chartSpec.title || `图表 ${chartIndex + 1}`}`)">
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
                    <button v-if="featureAccess.report_fullscreen" class="sa-ghost-btn" @click="openReportViewer">全屏查看</button>
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
                    <button v-if="featureAccess.report_fullscreen" class="sa-secondary-btn" @click="openReportViewer">
                      <span class="sa-btn-label">查看大图</span>
                    </button>
                    <button v-if="featureAccess.smart_report_download" class="sa-primary-btn" @click="downloadLatestReport">
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

          <section v-if="dialogBusinessDrillReport?.primaryAnswer" class="sa-report-stage-section">
            <div class="sa-filter-answer-card">
              <div class="sa-filter-answer-head">
                <div>
                  <div class="sa-report-stage-title">{{ dialogBusinessDrillReport.primaryAnswer.title || '主回答' }}</div>
                  <p class="sa-business-summary-text">{{ dialogBusinessDrillReport.primaryAnswer.text }}</p>
                </div>
                <span class="sa-business-risk-pill" :class="dialogBusinessDrillReport.answerMode === 'ranking' ? 'good' : 'warn'">
                  {{ dialogBusinessDrillReport.primaryAnswer.targetLevel || dialogBusinessDrillReport.compareLevelLabel }}
                </span>
              </div>
            </div>
          </section>

          <section v-if="dialogBusinessDrillReport?.filterAnswer" class="sa-report-stage-section">
            <div class="sa-filter-answer-card">
              <div class="sa-filter-answer-head">
                <div>
                  <div class="sa-report-stage-title">{{ dialogBusinessDrillReport.filterAnswer.title || '命中结果' }}</div>
                  <p class="sa-business-summary-text">{{ dialogBusinessDrillReport.filterAnswer.text }}</p>
                </div>
                <span class="sa-business-risk-pill" :class="dialogBusinessDrillReport.filterAnswer.nodes?.length ? 'warn' : 'good'">
                  {{ dialogBusinessDrillReport.filterAnswer.nodes?.length || 0 }} 个
                </span>
              </div>
              <div v-if="dialogBusinessDrillReport.filterAnswer.nodes?.length" class="sa-filter-answer-list">
                <button
                  v-for="node in dialogBusinessDrillReport.filterAnswer.nodes"
                  :key="`dialog-filter-answer-${node.id}`"
                  class="sa-filter-answer-row"
                  type="button"
                  @click="toggleOfficeDrill(node.id)"
                >
                  <span class="sa-filter-answer-name">{{ node.name }}</span>
                  <span class="sa-filter-answer-metric">{{ node.metricLabel }} {{ node.metricValue }}</span>
                  <span v-if="node.tag" class="sa-detail-tag" :class="node.tone">{{ node.tag }}</span>
                </button>
              </div>
            </div>
          </section>

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

          <section v-if="dialogBusinessDrillReport && reportHasDrillableOffices(dialogBusinessDrillReport)" class="sa-report-stage-section sa-office-report-stage">
            <div class="sa-report-stage-title">{{ dialogReportStageTitle }}</div>
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
                  @click="canToggleOffice(office) && toggleOfficeDrill(office.id)"
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
                  @click="canToggleOffice(office) && toggleOfficeDrill(office.id)"
                >
                  <div class="sa-office-head-main">
                    <div class="sa-office-name">{{ office.name }} <span class="sa-office-tag">{{ office.tag }}</span></div>
                    <div class="sa-office-subtitle">{{ getOfficeSubtitle(office, dialogBusinessDrillReport) }}</div>
                  </div>
                  <span class="sa-office-head-actions">
                    <span class="sa-office-rate" :class="office.tone">{{ office.rateLabel }}<small v-if="office.rankLabel">{{ office.rankLabel }}</small></span>
                    <span
                      v-if="canToggleOffice(office)"
                      class="sa-office-drill-toggle"
                      :class="{ 'is-open': isOfficeExpanded(office.id) }"
                      :title="isOfficeExpanded(office.id) ? '收起明细' : getOfficeToggleTitle(office, dialogBusinessDrillReport)"
                    >
                      <span>{{ isOfficeExpanded(office.id) ? '收起' : '下钻' }}</span>
                      <i></i>
                    </span>
                    <span v-else class="sa-office-leaf-pill">当前最细层</span>
                  </span>
                </button>
                <p class="sa-office-copy">{{ office.summary }}</p>
                <div v-if="canToggleOffice(office) && isOfficeExpanded(office.id)" class="sa-office-drill is-dialog">
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
                    {{ getOfficeEmptyDrillText(office, dialogBusinessDrillReport) }}
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
                  <button v-if="featureAccess.chart_viewer" class="sa-ghost-btn" @click="openChartViewer(block.chartSpec, `${block.dataset.dataset_name} 图表预览`)">放大查看</button>
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
import { useSmartAskTaskView } from '../state/smartAskTaskView'
import { useSmartAskReportHistory } from '../composables/useSmartAskReportHistory'
import { buildOrgTree, getDefaultConfig as getDefaultReportTreeConfig } from '../composables/useOrgTree'

const session = useSmartAskSession()
const { isFeatureEnabled, loadFeatureFlags } = useFeatureFlags()
const smartFeatureKeys = [
  'debug_execution_trace',
  'smart_new_chat',
  'smart_quick_ask',
  'smart_quick_refresh',
  'smart_question_copy',
  'smart_question_edit',
  'smart_question_rerun',
  'smart_confirm_scope',
  'smart_submit_note',
  'chart_viewer',
  'smart_report_details',
  'smart_send_question',
  'smart_stop_run',
  'smart_dataset_select',
  'smart_model_select',
  'smart_sql_copy',
  'report_fullscreen',
  'smart_report_download',
  'smart_chart_auto_infer',
]
const featureAccess = computed(() => smartFeatureKeys.reduce((map, key) => {
  map[key] = isFeatureEnabled(key)
  return map
}, {}))
const canUseFeature = (key) => Boolean(featureAccess.value[key])
const {
  historySessions,
  pendingRestoreId,
  loadHistory,
  upsertHistory,
  findHistoryById,
  clearRestoreRequest,
  setActiveHistory,
  takePendingRestoreOptions,
} = useSmartAskHistory()
const {
  runningSessionId,
  viewingTaskId,
  isViewingReadonly,
  readonlySnapshot,
  runningTaskStatus,
  completedTaskId,
  pendingTaskId,
  setRunningSessionId,
  clearRunningSessionId,
  markRunningTaskPending,
  markRunningTaskCompleted,
  markRunningTaskFailed,
  switchViewToRunning,
  switchViewToDefault,
} = useSmartAskTaskView()
const query = ref('')
const datasetId = ref(null)
const modelId = ref(null)
const datasets = ref([])
const aiModels = ref([])
// 数据集就绪信号：登录后 getBookshelfDatasets 为异步，历史恢复的权限过滤必须等它就绪，
// 否则 datasets.value 仍为空会被 isDatasetVisible 全部误判为无权限（首次点历史误报）。
const datasetsLoaded = ref(false)
let datasetsLoadedResolve = null
const ensureDatasetsReady = () => {
  if (datasetsLoaded.value) return Promise.resolve()
  return new Promise((resolve) => {
    datasetsLoadedResolve = resolve
    // 兜底超时放行：后端 GET 已做权限过滤，前端仅为二次校验，超时不再阻塞恢复。
    setTimeout(() => {
      if (datasetsLoadedResolve) { datasetsLoadedResolve(); datasetsLoadedResolve = null }
    }, 2500)
  })
}
const markDatasetsLoaded = () => {
  datasetsLoaded.value = true
  if (datasetsLoadedResolve) { datasetsLoadedResolve(); datasetsLoadedResolve = null }
}
const commonQuestions = ref([])
const commonQuestionsLoading = ref(false)
const messages = reactive([])
const confirmationDrafts = reactive({})
const confirmationSubmitting = reactive({})
const confirmExpanded = reactive({})

// keep-alive 切回 / 刷新都会调：先看是否有残留 stale，再清掉 session.result + 全部 UI 卡片状态
// hasActiveAsk 守卫：本页正在执行的问数不清（误杀会导致 result 帧被忽略、显示已取消）
const clearStaleSessionState = () => {
  const hasStaleRecovered = session.state.result || session.state.question || session.state.logs?.length
  if (!hasStaleRecovered || session.hasActiveAsk?.()) return
  session.clearRecoveredSessionResult()
  clearChatUiState()
}
const showPanel = ref(true)
const chatBodyRef = ref(null)
const panelRef = ref(null)
const sideReportRef = ref(null)
const sideReportHeadRef = ref(null)
const chartDialogRef = ref(null)
const resultChainRefs = new Map()
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
const detailReportResult = ref(null)
const officeDrillOpen = reactive({})
const messageDerivedCache = new WeakMap()
const datasetChartSpecCache = new WeakMap()
const chartElementCache = new WeakMap()
let activePrintFrame = null
let msgCounter = 0
let elapsed = ref(0)
let timerInst = null
let chatScrollTimer = null
let panelScrollTimer = null
let reportTopScrollTimers = []
const activeRequestAiMessageId = ref(null)
const pendingQuickDataset = ref(null)
const isDatasetManuallySelected = ref(false)

const isRunning = computed(() => session.state.status === 'running')

const displayMessages = computed(() => {
  if (isViewingReadonly.value && readonlySnapshot.value?.messages) {
    return readonlySnapshot.value.messages
  }
  return messages
})

const displayLogs = computed(() => {
  if (isViewingReadonly.value && readonlySnapshot.value?.logs) {
    return readonlySnapshot.value.logs
  }
  return session.state.logs
})

const displayResult = computed(() => {
  if (isViewingReadonly.value && readonlySnapshot.value?.result) {
    return readonlySnapshot.value.result
  }
  return session.state.result
})

const timelineKey = computed(() => `${session.state.conversationSessionId || 'fresh'}-${timelineVersion.value}`)
const detailPanelVisible = computed(() => showPanel.value && canUseFeature('debug_execution_trace'))
const canViewCharts = computed(() => canUseFeature('chart_viewer'))
const canViewFullscreenReport = computed(() => canUseFeature('report_fullscreen'))

const statusBarText = computed(() => {
  const m = {
    running: session.state.logs.slice(-1)[0]?.title || '任务执行中',
    completed: '',
    canceled: '本轮问数已取消',
    error: '当前任务执行异常',
    waiting_confirmation: '等待确认统计口径'
  }
  return m[session.state.status] || ''
})

const activeReportResult = computed(() => {
  if (isViewingReadonly.value && displayResult.value) {
    return displayResult.value
  }
  return detailReportResult.value || session.state.result || null
})
const latestSessionError = computed(() => {
  const msg = activeRequestAiMessage.value || currentSessionAiMessage.value
  return String(msg?.data?.error || session.state.result?.error || '').trim()
})
const showAskFlowBadge = ref(true)

const activeAskFlowMeta = computed(() => {
  if (!showAskFlowBadge.value) return null
  const meta = activeReportResult.value?.ask_flow || activeReportResult.value?.diagnostics?.ask_flow || null
  return meta && typeof meta === 'object' ? meta : null
})

const activeAskFlowLabel = computed(() => {
  const flow = String(activeAskFlowMeta.value?.flow || '').toLowerCase()
  if (flow === 'advanced') return '进阶流程'
  if (flow === 'basic') return '基础流程'
  return ''
})

const activeAskFlowClass = computed(() => String(activeAskFlowMeta.value?.flow || '').toLowerCase() === 'advanced' ? 'is-advanced' : 'is-basic')

const activeAskFlowHint = computed(() => {
  const reason = String(activeAskFlowMeta.value?.reason || '')
  const map = {
    basic_selected: '当前问数由基础流程执行',
    advanced_selected: '当前问数由进阶流程执行',
    advanced_disabled: '进阶未启用，已回落基础流程',
    advanced_role_denied: '当前角色未进入进阶灰度',
    advanced_error_fallback: '进阶异常，已回退基础流程',
  }
  return map[reason] || '当前问数流程'
})

const latestDatasets = computed(() => (
  Array.isArray(activeReportResult.value?.dataset_results) ? activeReportResult.value.dataset_results : []
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

const parseMetricNumber = (value) => {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  const text = String(value || '').trim()
  const numeric = Number(text.replace(/[^0-9.-]/g, ''))
  if (!Number.isFinite(numeric)) return null
  if (text.includes('亿')) return numeric * 100000000
  if (text.includes('万')) return numeric * 10000
  return numeric
}

const findDatasetKpiNumber = (dataset, matcher) => {
  const kpis = Array.isArray(dataset?.report_spec?.kpis) ? dataset.report_spec.kpis : []
  const item = kpis.find(kpi => matcher.test(`${kpi?.key || ''}${kpi?.label || ''}`))
  if (!item) return null
  return parseMetricNumber(item.value ?? item.displayValue)
}

const findDatasetRowNumber = (dataset, matcher) => {
  const rows = Array.isArray(dataset?.rows) ? dataset.rows : []
  const row = rows.find(item => item && typeof item === 'object') || {}
  const key = Object.keys(row).find(name => matcher.test(name))
  return key ? parseMetricNumber(row[key]) : null
}

const inferSubjectLevel = (name) => {
  const text = String(name || '')
  if (text.includes('事业部')) return '事业部'
  if (text.includes('分公司')) return '分公司'
  if (text.includes('业务部')) return '业务部'
  if (text.includes('代表处')) return '代表处'
  return '对象'
}

const buildDatasetComparisonRow = (dataset) => {
  const subjectName = dataset?.comparison_subject_name || dataset?.dataset_name || `数据集 ${dataset?.dataset_id || ''}`.trim()
  const overview = dataset?.cross_dataset_subject_overview || {}
  const task = parseMetricNumber(overview?.task)
    ?? findDatasetKpiNumber(dataset, /总任务|任务金额|目标|task/i)
    ?? findDatasetRowNumber(dataset, /总任务|任务金额|目标/i)
  const actual = parseMetricNumber(overview?.actual)
    ?? findDatasetKpiNumber(dataset, /年度开单|开单金额|开单|完成|实际|actual/i)
    ?? findDatasetRowNumber(dataset, /年度开单|开单金额|开单|完成|实际/i)
  const rate = parseMetricNumber(overview?.rate)
    ?? findDatasetKpiNumber(dataset, /达成率|完成率|rate|percent/i)
    ?? findDatasetRowNumber(dataset, /达成率|完成率/i)
    ?? (task ? (Number(actual || 0) / task) * 100 : null)
  const remain = parseMetricNumber(overview?.remain)
    ?? findDatasetKpiNumber(dataset, /剩余|缺口|差额|remain|gap/i)
    ?? findDatasetRowNumber(dataset, /剩余|缺口|差额/i)
    ?? (task !== null && actual !== null ? task - actual : null)
  return {
    节点名称: subjectName,
    层级: overview?.level || dataset?.comparison_subject_level || inferSubjectLevel(subjectName),
    总任务金额: task,
    年度开单金额: actual,
    达成率: rate,
    剩余任务金额: remain,
  }
}

const collectResolvedNamesFromDatasets = (datasetResults) => {
  const names = []
  const add = (value) => {
    const text = String(value || '').trim()
    if (text && !names.includes(text)) names.push(text)
  }
  ;(datasetResults || []).forEach((dataset) => {
    const resolved = dataset?.resolved_entities || {}
    ;(resolved.all_members || []).forEach(add)
    ;(resolved.entities || []).forEach((entity) => {
      ;(entity?.members || []).forEach(add)
    })
  })
  return names
}

const datasetRowsContainAnyName = (dataset, names = []) => {
  if (!names.length) return false
  return (dataset?.rows || []).some((row) => {
    const text = Object.values(row || {}).map(value => String(value ?? '')).join(' ')
    return names.some(name => text.includes(name))
  })
}

const buildAggregateDataset = (datasetResults) => {
  if (!Array.isArray(datasetResults) || datasetResults.length === 0) return null
  if (datasetResults.length === 1) return datasetResults[0]

  const resolvedNames = collectResolvedNamesFromDatasets(datasetResults)
  if (resolvedNames.length === 1) {
    const matching = datasetResults.filter(dataset => datasetRowsContainAnyName(dataset, resolvedNames))
    if (matching.length === 1) return matching[0]
  }

  const totalRows = datasetResults.reduce((sum, item) => sum + Number(item?.row_count || item?.rows?.length || 0), 0)
  const allColumns = Array.from(new Set(datasetResults.flatMap(item => item?.columns || [])))
  const comparisonRows = datasetResults.map(buildDatasetComparisonRow).filter(item => item.节点名称)

  return {
    dataset_name: `共 ${datasetResults.length} 个数据集`,
    dataset_id: 'multi',
    row_count: totalRows,
    rows: comparisonRows,
    columns: Array.from(new Set([...allColumns, '节点名称', '层级', '总任务金额', '年度开单金额', '达成率', '剩余任务金额'])),
  }
}

const latestDataset = computed(() => buildAggregateDataset(latestDatasets.value))

const latestReport = computed(() => mergeDatasetReports(latestDatasets.value))

const isDatasetVisible = (id) => {
  const value = Number(id)
  if (!Number.isFinite(value)) return false
  return datasets.value.some(item => Number(item?.id) === value)
}

const sanitizeDatasetSelection = () => {
  if (datasetId.value && !isDatasetVisible(datasetId.value)) {
    datasetId.value = null
    isDatasetManuallySelected.value = false
  }
  if (session.state.selectedDatasetId && !isDatasetVisible(session.state.selectedDatasetId)) {
    session.state.selectedDatasetId = null
  }
  if (pendingQuickDataset.value?.datasetId && !isDatasetVisible(pendingQuickDataset.value.datasetId)) {
    pendingQuickDataset.value = null
  }
}

const datasetResults = computed(() => latestDatasets.value)
const hasSideReport = computed(() => {
  if (latestSessionError.value) return false
  return resultPreviews.value.length > 0 || !!latestReport.value
})
const sideReportHeading = computed(() => '业绩分析报告')

const reportSceneTemplate = computed(() => {
  const sourceDatasets = reportViewerVisible.value ? reportViewerDatasets.value : latestDatasets.value
  const specTemplate = sourceDatasets.find(item => item?.report_spec?.layoutTemplate)?.report_spec?.layoutTemplate
  if (specTemplate) return specTemplate
  const answerMode = String(sourceDatasets.find(item => item?.report_spec?.answerMode)?.report_spec?.answerMode || '').trim()
  if (answerMode === 'comparison') return 'comparison'
  if (answerMode === 'ranking') return 'ranking'
  if (answerMode === 'drilldown' || answerMode === 'filter') return 'detail'
  const questionText = String(activeReportResult.value?.question || session.state.question || query.value || '')
  if (/对比|比较|哪个|谁更|差异|和.+比|跟.+比|与.+比|\bvs\b/i.test(questionText)) return 'comparison'
  if (/排名|排行|前\s*(?:\d+|[一二两三四五六七八九十]+)|Top\s*\d+|TOP\s*\d+|最好|最差|最高|最低/.test(questionText)) return 'ranking'
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
  const advanced = activeReportResult.value?.diagnostics?.advanced || {}
  const evidenceVote = advanced?.evidence_vote || {}
  const templatePolicy = advanced?.template_policy || {}
  const routeGuard = advanced?.route_guard || {}
  const backendConfidence = activeReportResult.value?.confidence || {}
  const routeMeta = backendConfidence?.route
    ? {
        score: Number(backendConfidence.route.score || 0),
        tone: backendConfidence.route.level === 'high' ? 'success' : backendConfidence.route.level === 'medium' ? 'info' : 'warning',
        label: '路由把握',
        value: `${backendConfidence.route.label || ''} ${backendConfidence.route.score || 0}`.trim(),
      }
    : buildRouteConfidenceMeta(activeReportResult.value?.route || {})
  const resultMeta = backendConfidence?.result
    ? {
        score: Number(backendConfidence.result.score || 0),
        tone: backendConfidence.result.level === 'high' ? 'success' : backendConfidence.result.level === 'medium' ? 'info' : 'warning',
        label: '结果可信',
        value: `${backendConfidence.result.label || ''} ${backendConfidence.result.score || 0}`.trim(),
      }
    : buildResultConfidenceMeta(activeReportResult.value?.route || {}, latestDatasets.value)
  const advancedVoteMeta = evidenceVote?.decision
    ? {
        score: Number(evidenceVote.confidence_score || 0),
        tone: evidenceVote.decision === 'accept' ? 'success' : evidenceVote.decision === 'accept_with_caution' ? 'info' : 'warning',
        label: '进阶择优',
        value: `${({
          accept: '可采信',
          accept_with_caution: '谨慎采信',
          review_required: '需复核',
        }[evidenceVote.decision] || evidenceVote.decision)} ${evidenceVote.confidence_score || 0}`.trim(),
      }
    : null
  const templateMeta = templatePolicy?.expected_top_n
    ? {
        score: Number(templatePolicy.expected_top_n || 0),
        tone: Number(templatePolicy.warning_count || 0) > 0 ? 'warning' : 'success',
        label: '模板策略',
        value: `Top${templatePolicy.expected_top_n}`,
      }
    : null
  const routeGuardLabel = {
    auto_lock: '自动锁定',
    cross_dataset_compare: '跨集对比',
    manual_respected: '手动优先',
    manual_mismatch: '手动错配',
    needs_confirmation: '待确认',
    no_candidate: '无候选',
    observe: '观察',
  }[routeGuard.action] || routeGuard.action
  const guardMeta = routeGuard?.action
    ? {
        score: Number(routeGuard.confidence || 0),
        tone: routeGuard.action === 'auto_lock' || routeGuard.action === 'manual_respected' ? 'success' : 'warning',
        label: '路由守门',
        value: routeGuardLabel,
      }
    : null
  return [routeMeta, resultMeta, advancedVoteMeta, templateMeta, guardMeta].filter(item => item?.score > 0)
})

const routeDecisionDetail = computed(() => {
  const result = activeReportResult.value || {}
  const advanced = result?.diagnostics?.advanced || {}
  const route = result.route || {}
  const summary = String(result.confidence?.route?.summary || '').trim()
  const reason = String(result.confidence?.route?.reason || route.arbiter_reason || '').trim()
  const reasonLabel = {
    profile_scope_resolved: '组织画像命中',
    explicit_dataset_alias: '同义词命中',
    organization_tree_name_resolved: '组织树命中',
    top_candidate_score_clear: '候选分数领先',
    high_confidence: '高置信语义匹配',
    low_similarity_requires_boss_confirm: '相似命中待确认',
  }[reason] || ''
  const ids = Array.isArray(route.dataset_ids) ? route.dataset_ids : []
  const names = ids.map(id => datasetNameMap.value.get(Number(id)) || `数据集 ${id}`).filter(Boolean)
  const routeGuard = advanced?.route_guard || {}
  const evidenceVote = advanced?.evidence_vote || {}
  const advancedLines = [
    routeGuard?.reason ? `进阶守门：${routeGuard.reason}` : '',
    evidenceVote?.recommended_action ? `采信建议：${evidenceVote.recommended_action}` : '',
  ].filter(Boolean)
  if (!summary && !reasonLabel && !names.length && !advancedLines.length) return ''
  return [
    names.length ? `自动路由：${names.join('、')}` : '',
    reasonLabel ? `依据：${reasonLabel}` : '',
    summary,
    ...advancedLines,
  ].filter(Boolean).join('；')
})

const detailPanelState = computed(() => {
  const m = {
    idle: '待命',
    running: '执行中',
    completed: '已完成',
    canceled: '已取消',
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
  if (session.state.status === 'canceled') {
    return '你已手动取消本轮问数，执行链路已停止。'
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

const formatAmount = (value, metric = {}) => {
  const numeric = typeof value === 'number'
    ? value
    : Number(String(value ?? '').replace(/[^0-9.-]/g, ''))
  if (!Number.isFinite(numeric)) return '-'

  const unit = String(metric.unit || '').trim()
  const scale = Number(metric.scale) || 1
  const display = numeric / scale
  const absDisplay = Math.abs(display)

  const fmt = (num, digits = 2) => {
    if (Number.isInteger(num)) return String(num)
    return Number(num).toFixed(digits).replace(/\.?0+$/, '')
  }

  if (unit === '万元') {
    if (absDisplay < 10000) return `${fmt(display)}万`
    return `${fmt(display / 10000)}亿`
  }

  // 默认按 "元" 口径展示
  if (absDisplay < 10000) return fmt(display)
  if (absDisplay < 1000000) return `${(display / 10000).toFixed(1).replace(/\.?0+$/, '')}万`
  if (absDisplay < 100000000) return `${Math.round(display / 10000)}万`
  return `${(display / 100000000).toFixed(2).replace(/\.?0+$/, '')}亿`
}

const resolveAmountMetric = (metric = {}, dataset = null, column = '') => {
  const nextMetric = { ...(metric || {}) }
  if (String(nextMetric.unit || '').trim()) return nextMetric

  const reportSpec = dataset?.report_spec || {}
  const reportUnit = String(reportSpec.amountUnit || '').trim()
  const metricColumn = String(nextMetric.column || column || '').trim()

  if (reportUnit && isAmountColumn(metricColumn || nextMetric.label || nextMetric.key || '')) {
    nextMetric.unit = reportUnit
    nextMetric.scale = Number(nextMetric.scale) || 1
    return nextMetric
  }

  return nextMetric
}

const formatChartAmount = (value, dataset = null, column = '') => (
  formatAmount(value, resolveAmountMetric({ format: 'amount', column }, dataset, column))
)

const isAmountColumn = (column = '') => amountColumnPattern.test(String(column || ''))
const isRateColumn = (column = '') => rateColumnPattern.test(String(column || ''))

const formatDisplayValue = (value) => {
  if (typeof value === 'number') {
    if (Number.isInteger(value)) return value.toLocaleString()
    return value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
  }
  return String(value ?? '-')
}

const formatValueByColumn = (value, column = '', dataset = null) => {
  if (isAmountColumn(column)) {
    const metric = resolveAmountMetric({}, dataset, column)
    const col = String(column || '')
    if (/_万元$/.test(col) || /万元$/.test(col)) {
      metric.unit = '万元'
      metric.scale = 1
    }
    return formatAmount(value, metric)
  }
  return formatDisplayValue(value)
}

const formatBusinessValueByColumn = (value, column = '', dataset = null) => {
  const rawText = String(value ?? '').trim()
  if (rawText && /[万亿%]/.test(rawText)) return rawText
  return formatValueByColumn(value, column, dataset)
}

const getLabelColumn = (dataset) => {
  const columns = dataset?.columns || []
  const firstRow = dataset?.rows?.[0] || {}
  return (
    columns.find(col => /组织路径|归属组织|组织归属|管理链路|路径/i.test(col)) ||
    columns.find(col => /日期|时间|城市|分公司|代表处|业务部|名称|水平|类型|标识/i.test(col)) ||
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
    cards.push({ label: rows.length === 1 ? column : `最高${column}`, value: formatValueByColumn(displayValue, column, dataset) })
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
  || activeReportResult.value?.report_configs?.[String(dataset?.dataset_id)]
  || activeReportResult.value?.report_config
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

const formatMetricByDefinition = (value, metric = {}, dataset = null) => {
  if (value === null || value === undefined) return '-'
  if (metric.format === 'percent') return `${Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 })}%`
  if (metric.format === 'amount' || metric.format === 'currency') return formatAmount(value, resolveAmountMetric(metric, dataset))
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

const getOfficeThresholds = (config = {}) => {
  const risk = toNumber(config?.officeRiskThreshold ?? config?.riskThreshold) ?? 10
  const configuredBenchmark = toNumber(config?.officeBenchmarkThreshold ?? config?.benchmarkThreshold)
  return {
    risk,
    benchmark: configuredBenchmark ?? 15,
  }
}

const getOfficeRateTone = (rate, config = {}) => {
  const { benchmark, risk } = getOfficeThresholds(config)
  return getRateTone(rate, benchmark, risk)
}

const getOfficeToneLabel = (tone) => ({ good: '区域标杆', warn: '需推进', danger: '低达成风险' }[tone] || '待观察')

const getOfficeRateTag = (rate, config = {}, goodLabel = '区域标杆') => {
  const tone = getOfficeRateTone(rate, config)
  if (tone === 'good') return `✅ ${goodLabel}`
  if (tone === 'warn') return '🟠 需推进'
  if (tone === 'danger') return '⚠️ 风险'
  return '未分级'
}

const getToneFromDisplayTag = (label = '', fallback = 'neutral') => {
  const text = String(label || '')
  if (/风险|重点风险/.test(text)) return 'danger'
  if (/承压|第三梯队/.test(text)) return 'danger'
  if (/推进|第二梯队|稳定|中位/.test(text)) return 'warn'
  if (/标杆|领先|第一梯队/.test(text)) return 'good'
  return fallback
}

const requestedLevelTokens = ['城市分公司', '城市公司', '事业部', '业务部', '分公司', '代表处', '业务代表', '业务员', '部门', '条线']

const canonicalRequestedLevel = (value) => {
  const text = String(value || '').trim()
  if (text === '城市分公司') return '城市公司'
  return text
}

const getQuestionText = () => String(session.state.question || query.value || '').trim()

const getRequestedLevelValues = (questionText = getQuestionText(), config = {}) => {
  const values = []
  const configuredValues = (config?.levels || [])
    .flatMap(level => level?.values || [])
    .map(value => String(value || '').trim())
    .filter(Boolean)
  ;[...configuredValues, ...requestedLevelTokens].forEach((value) => {
    const canonical = canonicalRequestedLevel(value)
    if (value && questionText.includes(value) && !values.includes(canonical)) values.push(canonical)
  })
  return values
}

const isNegativeRankingQuestion = (questionText = getQuestionText()) => (
  /完成.*不好|不好|差|最差|最低|落后|承压|风险|低于|倒数|垫底|未完成|缺口/.test(questionText || '')
)

const isRateRankingQuestion = (questionText = getQuestionText()) => (
  /达成率|完成率|完成|进度|不好|最低|最差|排名|排行|承压|风险/.test(questionText || '')
)

const isAmountRankingQuestion = (questionText = getQuestionText()) => (
  /排名|排行|Top\s*\d+|TOP\s*\d+|前\s*(?:\d+|[一二两三四五六七八九十]+)|最高|最低|最好|最差/.test(questionText || '')
  && /年度开单|开单金额|开单|实际|销售/.test(questionText || '')
)

const getQuestionRankingMetricLabel = (questionText = getQuestionText()) => {
  const text = String(questionText || '')
  if (!/排名|排行|Top\s*\d+|TOP\s*\d+|前\s*(?:\d+|[一二两三四五六七八九十]+)|最高|最低|最好|最差/.test(text)) return ''
  if (/年度开单|开单金额|开单|实际|销售/.test(text)) return '年度开单金额'
  if (/总任务|任务金额|目标/.test(text)) return '总任务金额'
  if (/剩余|缺口|差额|待完成/.test(text)) return '剩余任务金额'
  if (/达成率|完成率|进度|完成/.test(text)) return '达成率'
  return ''
}

const getRankingPolicy = (config = {}) => (
  config?.intentPolicies?.ranking && typeof config.intentPolicies.ranking === 'object'
    ? config.intentPolicies.ranking
    : {}
)

const getConfiguredTopN = (report = null) => {
  const config = report?.dataset ? getDatasetReportConfig(report.dataset) : getDefaultReportTreeConfig()
  const intentTopN = toNumber(report?.dataset?.report_spec?.debug?.query_intent?.top_n)
  const policy = getRankingPolicy(config)
  const defaultTopN = toNumber(policy.defaultTopN) ?? 3
  const maxTopN = toNumber(policy.maxTopN) ?? 20
  if (report?.answerMode === 'ranking' && intentTopN === null) {
    return Math.max(1, Array.isArray(report?.offices) && report.offices.length ? report.offices.length : defaultTopN)
  }
  const value = intentTopN ?? defaultTopN
  return Math.max(1, Math.min(maxTopN, value))
}

const sortNodesForQuestion = (nodes = [], rateMetric = null) => {
  const lowFirst = isNegativeRankingQuestion()
  return [...nodes].sort((left, right) => {
    const leftValue = getNodeMetricValue(left, rateMetric) || 0
    const rightValue = getNodeMetricValue(right, rateMetric) || 0
    return lowFirst ? leftValue - rightValue : rightValue - leftValue
  })
}

const normalizeOfficeCompareSpec = (chartSpec = {}, config = {}) => {
  if (!chartSpec || typeof chartSpec !== 'object') return chartSpec
  const rows = Array.isArray(chartSpec.rows) ? chartSpec.rows : []
  const columns = Array.isArray(chartSpec.columns) && chartSpec.columns.length
    ? [...chartSpec.columns]
    : Object.keys(rows[0] || {})
  const rateColumn = findColumn(columns, column => isRateColumn(column)) || '达成率'
  const nextColumns = columns.includes('标签') ? columns : [...columns, '标签']
  return {
    ...chartSpec,
    columns: nextColumns,
    sortColumn: chartSpec.sortColumn || '',
    rows: rows.map(row => ({
      ...row,
      标签: row?.标签 || getOfficeRateTag(row?.[rateColumn], config),
    })),
  }
}

const subjectAccentPalette = [
  { accent: '#1A1A1A', soft: 'rgba(26, 26, 26, 0.06)', border: 'rgba(26, 26, 26, 0.18)' },
  { accent: '#10B981', soft: 'rgba(16, 185, 129, 0.08)', border: 'rgba(16, 185, 129, 0.22)' },
  { accent: '#F59E0B', soft: 'rgba(245, 158, 11, 0.09)', border: 'rgba(245, 158, 11, 0.24)' },
  { accent: '#6B7280', soft: 'rgba(107, 114, 128, 0.08)', border: 'rgba(107, 114, 128, 0.22)' },
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

const getKnownChildLevelLabel = (levelLabel = '') => {
  const text = String(levelLabel || '').trim()
  if (/分公司/.test(text) && !/城市/.test(text)) return '城市公司'
  if (/代表处|业务部/.test(text)) return '业务代表'
  return ''
}

const getOfficeSubtitle = (office, report) => {
  if (office?.isLeafLevel) {
    return `${office.leafLabel || '当前最细层'} · ${office.parentName || '当前口径'}`
  }
  return `${office?.childCount || 0} 个${report?.detailLevelLabel || office?.detailLevelLabel || '明细层级'} · ${office?.parentName || '当前口径'}`
}

const getOfficeToggleTitle = (office, report) => (
  office?.isLeafLevel
    ? `查看${office.name || '当前对象'}当前层指标`
    : `展开查看${office?.childCount || 0}个${report?.detailLevelLabel || office?.detailLevelLabel || '明细层级'}`
)

const getOfficeEmptyDrillText = (office, report) => (
  office?.isLeafLevel
    ? `${office.name || '当前对象'}已到当前最细层，暂无可继续下钻的下级明细。`
    : `当前 SQL 结果未返回 ${report?.detailLevelLabel || office?.detailLevelLabel || '明细层级'} 明细。请重新问“${office?.name || '当前对象'}下${report?.detailLevelLabel || office?.detailLevelLabel || '明细层级'}业绩明细”或检查 SQL 是否包含下级层级。`
)

const reportHasDrillableOffices = (report) => (
  Array.isArray(report?.offices) && report.offices.some(office => !office?.isLeafLevel)
)

const isLeafOnlyReport = (report) => (
  Array.isArray(report?.offices) && report.offices.length > 0 && report.offices.every(office => office?.isLeafLevel)
)

const canToggleOffice = (office) => !office?.isLeafLevel

const getReportRiskCount = (report) => {
  const offices = Array.isArray(report?.offices) ? report.offices : []
  if (!offices.length) return 0
  const threshold = report?.answerMode === 'ranking' || report?.answerMode === 'filter' ? 10 : 15
  return offices.filter(item => {
    const rate = toNumber(item?.rate)
    return rate !== null && rate < threshold
  }).length
}

const getMetricValueFromOffice = (office, label = '') => {
  const metricText = String(label || '')
  const kpis = Array.isArray(office?.kpis) ? office.kpis : []
  const direct = kpis.find(item => {
    const itemLabel = String(item?.label || '')
    return itemLabel && (itemLabel.includes(metricText) || metricText.includes(itemLabel))
  })
  const directValue = toNumber(direct?.value)
  if (directValue !== null) return directValue
  if (isRateMetricLabel(metricText)) return toNumber(office?.rate)
  if (/开单|完成|实际|销售/i.test(metricText)) return toNumber(getOfficeKpiLabel(office, 'actual'))
  if (/任务|目标/i.test(metricText)) return toNumber(getOfficeKpiLabel(office, 'task'))
  if (/剩余|缺口|差额|remain/i.test(metricText)) return toNumber(getOfficeKpiLabel(office, 'remain'))
  return toNumber(office?.rate)
}

const getReportSortSpec = (report = null) => {
  const datasetSortSpec = report?.dataset?.report_spec?.sortSpec
  const directSortSpec = report?.sortSpec
  const source = (datasetSortSpec && typeof datasetSortSpec === 'object' ? datasetSortSpec : directSortSpec) || {}
  const explicitMetricLabel = getQuestionRankingMetricLabel()
  if (!explicitMetricLabel || report?.answerMode !== 'ranking') return source
  return {
    ...source,
    metricLabel: explicitMetricLabel,
    direction: source.direction || (isNegativeRankingQuestion() ? 'asc' : 'desc'),
  }
}

const getSortMetricLabel = (report = null, fallback = '达成率') => (
  (report?.answerMode === 'ranking' ? getQuestionRankingMetricLabel() : '')
  || getReportSortSpec(report).metricLabel
  || report?.primaryAnswer?.metricLabel
  || report?.filterAnswer?.metricLabel
  || fallback
)

const normalizeRankingPrimaryAnswer = (report, offices = []) => {
  const answer = report?.primaryAnswer || {}
  if (report?.answerMode !== 'ranking') return answer
  const metricLabel = getQuestionRankingMetricLabel() || getReportSortSpec(report).metricLabel || answer?.metricLabel || '达成率'
  const levelLabel = report?.compareLevelLabel || answer?.targetLevel || '对象'
  const count = offices.length || Number(answer?.count || answer?.total || 0) || 0
  return {
    ...answer,
    title: answer?.title || '排名结果',
    text: `已按${metricLabel}输出${count ? ` ${count} 个` : ''}${levelLabel}的排序结果`,
    metricLabel,
    targetLevel: levelLabel,
    direction: getReportSortSpec(report).direction || answer?.direction || (isNegativeRankingQuestion() ? 'asc' : 'desc'),
  }
}

const sortOfficesByAnswerMetric = (offices = [], report = null) => {
  if (!Array.isArray(offices) || !offices.length) return []
  const sortSpec = getReportSortSpec(report)
  const metricLabel = getSortMetricLabel(report, '')
  if (!metricLabel) return [...offices]
  const lowFirst = (sortSpec.direction || report?.primaryAnswer?.direction || '').toLowerCase() === 'asc'
  return [...offices].sort((left, right) => {
    const leftValue = getMetricValueFromOffice(left, metricLabel)
    const rightValue = getMetricValueFromOffice(right, metricLabel)
    if (leftValue === null && rightValue === null) return 0
    if (leftValue === null) return 1
    if (rightValue === null) return -1
    return lowFirst ? leftValue - rightValue : rightValue - leftValue
  })
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

const getReportMetricContext = (report) => {
  const metricLabel = getSortMetricLabel(report, '达成率')
  const sortSpec = getReportSortSpec(report)
  const lowFirst = String(sortSpec.direction || report?.primaryAnswer?.direction || '').toLowerCase() === 'asc'
  const ranked = sortOfficesByAnswerMetric(
    (report?.offices || []).filter(item => getMetricValueFromOffice(item, metricLabel) !== null),
    report,
  )
  const best = ranked[0] || null
  const worst = ranked[ranked.length - 1] || null
  const bestValue = best ? getMetricValueFromOffice(best, metricLabel) : null
  const worstValue = worst ? getMetricValueFromOffice(worst, metricLabel) : null
  const diff = bestValue !== null && worstValue !== null && best?.name !== worst?.name
    ? (isRateMetricLabel(metricLabel)
      ? `${Math.abs(bestValue - worstValue).toFixed(2).replace(/\.?0+$/, '')}个百分点`
      : formatAmount(Math.abs(bestValue - worstValue)))
    : ''
  return { metricLabel, lowFirst, ranked, best, worst, diff }
}

const isCollectionAnswerMode = (report) => ['filter', 'ranking', 'drilldown'].includes(report?.answerMode || '')
const isRateMetricLabel = (label = '') => /达成率|完成率|rate|percent/i.test(String(label || ''))
const isAmountMetricLabel = (label = '') => /开单|金额|任务|销售|完成|实际/i.test(String(label || ''))
const findOfficeMetricValueByLabel = (office, label = '') => {
  const kpis = Array.isArray(office?.kpis) ? office.kpis : []
  const text = String(label || '')
  if (!text) return ''
  const direct = kpis.find(item => {
    const itemLabel = String(item?.label || '')
    return itemLabel && (itemLabel.includes(text) || text.includes(itemLabel))
  })
  if (direct?.value) return direct.value
  if (isRateMetricLabel(text)) return office?.rateLabel || ''
  if (/开单|完成|实际|销售/i.test(text)) return getOfficeKpiLabel(office, 'actual')
  if (/任务|目标/i.test(text)) return getOfficeKpiLabel(office, 'task')
  if (/剩余|缺口|差额|remain/i.test(text)) return getOfficeKpiLabel(office, 'remain')
  return ''
}

const buildCollectionMetricCards = (report) => {
  const offices = sortOfficesByAnswerMetric(report?.offices, report)
  if (!offices.length) return []
  const leader = offices[0] || null
  const tail = offices[offices.length - 1] || null
  const metricLabel = getSortMetricLabel(report, '指标')
  const metricValue = (office) => (
    findOfficeMetricValueByLabel(office, metricLabel)
    || (isAmountMetricLabel(metricLabel) ? getOfficeKpiLabel(office, 'actual') : '')
    || office?.rateLabel
    || '-'
  )
  const riskCount = getReportRiskCount(report)
  return [
    {
      label: report?.answerMode === 'filter' ? '命中数量' : '结果数量',
      value: `${offices.length} 个`,
      hint: `${report?.compareLevelLabel || '对象'}结果集合`,
      tone: 'neutral',
    },
    leader ? {
      label: report?.answerMode === 'ranking' ? '榜首结果' : '最高结果',
      value: leader.name,
      hint: `${metricLabel} ${metricValue(leader)}`,
      tone: 'good',
    } : null,
    tail ? {
      label: report?.answerMode === 'ranking' ? '末位结果' : '边界结果',
      value: tail.name,
      hint: `${metricLabel} ${metricValue(tail)}`,
      tone: report?.answerMode === 'ranking' ? 'warn' : 'neutral',
    } : null,
    {
      label: '风险节点',
      value: `${riskCount} 个`,
      hint: riskCount ? '存在明显滞后对象，建议继续下钻' : '当前结果内暂无明显风险节点',
      tone: riskCount ? 'danger' : 'good',
    },
  ].filter(Boolean)
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

const buildOfficeDetailRows = (chartSpec = {}, config = {}) => {
  const rows = Array.isArray(chartSpec.rows) ? chartSpec.rows : []
  const columns = Array.isArray(chartSpec.columns) && chartSpec.columns.length
    ? chartSpec.columns
    : Object.keys(rows[0] || {})
  const dataset = chartSpec?.dataset || null
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
    const label = row?.标签 || getOfficeRateTag(rate, config, '标杆')
    return {
      name: row?.[nameColumn] || row?.名称 || '-',
      rate,
      rateLabel: isRateColumn(rateColumn) ? `${rate.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}%` : formatDisplayValue(rate),
      task,
      taskLabel: taskColumn ? formatAmount(task, resolveAmountMetric({ format: 'amount', column: taskColumn }, dataset, taskColumn)) : '-',
      actual,
      actualLabel: actualColumn ? formatAmount(actual, resolveAmountMetric({ format: 'amount', column: actualColumn }, dataset, actualColumn)) : '-',
      remain,
      remainLabel: remainColumn ? formatAmount(remain, resolveAmountMetric({ format: 'amount', column: remainColumn }, dataset, remainColumn)) : '-',
      label,
      tone: getToneFromDisplayTag(label, getOfficeRateTone(rate, config)),
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
  const requestedLevels = getRequestedLevelValues(getQuestionText(), model.config || {})
  if (requestedLevels.length) {
    const scopedNodes = focusNode ? getDescendantNodes(focusNode) : (model.flatNodes || [])
    const levelNodes = scopedNodes.filter(node => (
      node?.name
      && (
        requestedLevels.includes(canonicalRequestedLevel(node.levelValue))
        || requestedLevels.includes(canonicalRequestedLevel(node.levelName))
        || requestedLevels.some(value => value && String(node.name || '').includes(value))
      )
    ))
    if (levelNodes.length) return levelNodes
  }
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
  const rawAccordions = Array.isArray(spec.accordions) ? spec.accordions : []
  const overviewRows = Array.isArray(overviewChart?.rows) ? overviewChart.rows : []
  if (!overviewChart && !rawAccordions.length) return null

  const config = getDatasetReportConfig(dataset)
  const requestedLevels = getRequestedLevelValues(getQuestionText(), config)
  const compareLevelLabel = requestedLevels[0] || spec.scope?.compareLevelLabel || '下一层级'
  const detailLevelLabel = spec.scope?.detailLevelLabel || '明细层级'
  const inferredDetailLevelLabel = getKnownChildLevelLabel(compareLevelLabel) || detailLevelLabel
  const accordions = rawAccordions.length
    ? rawAccordions
    : overviewRows.map((row, index) => {
        const name = row?.名称 || row?.name || row?.[overviewChart?.columns?.[0]] || `当前层对象 ${index + 1}`
        return {
          id: `overview-${index}-${name}`,
          title: name,
          parentName: spec.scope?.focusNode || '',
          levelLabel: compareLevelLabel,
          detailLevelLabel: inferredDetailLevelLabel,
          isLeafLevel: !getKnownChildLevelLabel(compareLevelLabel),
          leafLabel: getKnownChildLevelLabel(compareLevelLabel) ? '' : '当前最细层',
          childCount: 0,
          tag: row?.标签 || '',
          kpis: Object.entries(row || {})
            .filter(([key]) => !['名称', 'name', '标签'].includes(key))
            .map(([key, value]) => ({ label: key, value })),
          narrative: `${name}已是当前结果的最细层级。`,
          detailNarrative: `${name}已是当前结果的最细层级，右侧展示该节点当前指标。`,
          chart: {
            chartType: overviewChart?.chartType || 'horizontalDrill',
            title: `${name}当前层指标`,
            columns: overviewChart?.columns || Object.keys(row || {}),
            rows: [row],
            dataset,
          },
          drillGroups: [],
        }
      })
  const matchedAccordions = requestedLevels.length
    ? accordions.filter(item => (
        requestedLevels.includes(item?.levelLabel)
        || requestedLevels.some(value => value && String(item?.title || '').includes(value))
      ))
    : []
  const sourceAccordions = requestedLevels.length && matchedAccordions.length ? matchedAccordions : accordions
  const mappedOffices = sourceAccordions.map((item) => {
    const itemLevelLabel = item.levelLabel || compareLevelLabel
    const knownChildLevelLabel = getKnownChildLevelLabel(itemLevelLabel)
    const itemDetailLevelLabel = item.detailLevelLabel || knownChildLevelLabel || detailLevelLabel
    const rateKpi = (item.kpis || []).find(kpi => /率|percent|rate/i.test(kpi.label || ''))
    const rateValue = toNumber(rateKpi?.value)
    const chartRows = Array.isArray(item.chart?.rows) ? item.chart.rows : []
    const narrative = String(item.narrative || '').trim()
    const detailRows = buildOfficeDetailRows({ ...(item.chart || {}), dataset }, config)
    const drillGroups = (Array.isArray(item.drillGroups) ? item.drillGroups : [])
      .map((group) => {
        const groupRateKpi = (group.kpis || []).find(kpi => /率|percent|rate/i.test(kpi.label || ''))
        const groupRateValue = toNumber(groupRateKpi?.value)
        const groupRows = buildOfficeDetailRows({ ...(group.chart || {}), dataset }, config)
        const groupTag = group.tag || getOfficeRateTag(groupRateValue, config, '代表处标杆')
        return {
          id: group.id || `${item.id || item.title}-${group.title}`,
          name: group.title || '未命名下级节点',
          parentName: group.parentName || item.title || '',
          tone: getToneFromDisplayTag(groupTag, getOfficeRateTone(groupRateValue, config)),
          tag: groupTag,
          rate: groupRateValue,
          rateLabel: groupRateKpi?.value || '-',
          progress: Math.max(0, Math.min(100, groupRateValue || 0)),
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
    const itemTag = item.tag || getOfficeRateTag(rateValue, config, '区域标杆')
    return {
      id: item.id || item.title,
      name: item.title || '未命名节点',
      parentName: item.parentName || item.levelLabel || '',
      tone: getToneFromDisplayTag(itemTag, getOfficeRateTone(rateValue, config)),
      tag: itemTag,
      highlight: item.highlight || '',
      rankLabel: item.rankLabel || '',
      rate: rateValue,
      rateLabel: rateKpi?.value || '-',
      progress: Math.max(0, Math.min(100, rateValue || 0)),
      childCount: Number.isFinite(Number(item.childCount)) ? Number(item.childCount) : chartRows.length,
      isLeafLevel: knownChildLevelLabel ? false : Boolean(item.isLeafLevel),
      leafLabel: knownChildLevelLabel ? '' : (item.leafLabel || ''),
      kpis: item.kpis || [],
      summary: summaryText,
      chartText: item.detailNarrative || '',
      chartSpec: item.chart,
      detailRows,
      drillGroups,
      detailLevelLabel: itemDetailLevelLabel,
    }
  })
  const answerMode = spec.answerMode || spec.analysisMode || 'detail'
  const answerSummary = spec.answerSummary || {}
  const reportContext = {
    dataset,
    sortSpec: spec.sortSpec || {},
    answerMode,
    primaryAnswer: ['ranking', 'drilldown'].includes(answerMode) ? answerSummary : null,
    filterAnswer: answerMode === 'filter' ? answerSummary : null,
  }
  const offices = sortOfficesByAnswerMetric(mappedOffices, reportContext).map((office, index) => {
    if (answerMode !== 'ranking') return office
    const childLevelLabel = getKnownChildLevelLabel(compareLevelLabel)
    const summary = childLevelLabel
      ? `${office.name}${office.tag ? ` ${office.tag}` : ''}；总任务金额 ${getOfficeKpiLabel(office, 'task')}，年度开单金额 ${getOfficeKpiLabel(office, 'actual')}，达成率 ${getOfficeKpiLabel(office, 'rate')}，剩余任务金额 ${getOfficeKpiLabel(office, 'remain')}。可继续下钻查看${childLevelLabel}明细。`
      : String(office.summary || '').replace(/（排序第\d+）/g, '')
    return {
      ...office,
      rankLabel: `排序第${index + 1}`,
      summary,
    }
  })
  const riskCount = getReportRiskCount({ ...reportContext, offices })
  const officeNames = new Set(offices.map(item => item.name))
  const filteredOverviewChart = overviewChart && officeNames.size
    ? {
        ...overviewChart,
        rows: (overviewChart.rows || []).filter(row => officeNames.has(row?.名称 || row?.name || row?.[overviewChart.columns?.[0]])),
      }
    : overviewChart
  const summary = Array.isArray(spec.narrative) && spec.narrative.length
    ? spec.narrative.join('；')
    : spec.sections?.find(section => section.key === 'overview')?.narrative || `本次结果覆盖 ${offices.length} 个${compareLevelLabel}。`
  const matchedNodes = Array.isArray(spec.matchedNodes) ? spec.matchedNodes : []
  const filterAnswer = spec.answerMode === 'filter'
    ? {
        ...spec.answerSummary,
        nodes: matchedNodes.map((node) => {
          const office = offices.find(item => item.name === node.name)
          const metric = node.metric || {}
          return {
            id: office?.id || node.id || node.name,
            name: node.name || '未命名对象',
            levelLabel: node.levelLabel || compareLevelLabel,
            tag: node.tag || office?.tag || '',
            tone: office?.tone || getOfficeRateTone(toNumber(metric.rawValue), config),
            metricLabel: metric.label || spec.answerSummary?.metricLabel || '指标',
            metricValue: metric.value ?? formatDisplayValue(metric.rawValue),
            kpis: Array.isArray(node.kpis) ? node.kpis : [],
          }
        }),
      }
    : null
  let primaryAnswer = ['ranking', 'drilldown'].includes(spec.answerMode)
    ? {
        ...spec.answerSummary,
      }
    : null

  const sortMetricLabel = getSortMetricLabel({ ...reportContext, primaryAnswer, filterAnswer }, '达成率')
  primaryAnswer = normalizeRankingPrimaryAnswer({ ...reportContext, primaryAnswer, filterAnswer, compareLevelLabel }, offices)

  return {
    dataset,
    sortSpec: spec.sortSpec || {},
    analysisMode: spec.analysisMode || 'detail',
    answerMode,
    primaryAnswer,
    filterAnswer,
    focusName: spec.scope?.focusNode || '',
    isSingleFocus: Boolean(spec.scope?.focusNode && spec.analysisMode !== 'comparative'),
    kpis: (spec.kpis || []).map(item => ({
      label: item.label || item.key,
      value: item.displayValue ?? formatDisplayValue(item.value),
    })).filter(item => item.label),
    offices,
    compareLevelLabel,
    detailLevelLabel: inferredDetailLevelLabel,
    officeCompareSpec: normalizeOfficeCompareSpec(filteredOverviewChart, config),
    officeCompareText: getKnownChildLevelLabel(compareLevelLabel)
      ? `当前结果按${compareLevelLabel}展示；${compareLevelLabel}下级为${inferredDetailLevelLabel}，可继续下钻查看${inferredDetailLevelLabel}明细。`
      : spec.sections?.find(section => section.key === 'drill')?.narrative || `一行一个同层级对象，按${sortMetricLabel}排序；对齐展示任务、开单、缺口、达成率和进度条，必要时继续下钻。`,
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
  const rankingMetric = isAmountRankingQuestion() ? (actualMetric || rateMetric) : rateMetric
  const rankingMetricLabel = rankingMetric?.label || rankingMetric?.column || '达成率'
  const rankingChartType = isAmountRankingQuestion() ? 'bar' : 'horizontalRateBar'

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
      .sort((a, b) => (getNodeMetricValue(a, rankingMetric) || 0) - (getNodeMetricValue(b, rankingMetric) || 0))
    const sortedPeopleDesc = [...sortedPeople].sort((a, b) => (getNodeMetricValue(b, rateMetric) || 0) - (getNodeMetricValue(a, rateMetric) || 0))
    const rate = getNodeMetricValue(office, rateMetric)
    const tone = getOfficeRateTone(rate, config)
    const riskPeople = sortedPeople.filter(item => getRateTone(getNodeMetricValue(item, rateMetric), 20, 10) === 'danger')
    const bestPerson = sortedPeopleDesc[0]
    const worstPerson = sortedPeople[0]
    const formatPersonMetric = (person, metric) => (
      metric ? formatMetricByDefinition(getNodeMetricValue(person, metric), metric, dataset) : '-'
    )
    const describePerson = (person) => {
      if (!person) return ''
      const actualText = formatPersonMetric(person, actualMetric)
      const taskText = formatPersonMetric(person, taskMetric)
      const remainText = formatPersonMetric(person, remainMetric)
      const rateText = formatPersonMetric(person, rateMetric)
      return `${person.name}开单${actualText} / 任务${taskText}，达成率${rateText}${remainMetric ? `，剩余缺口${remainText}` : ''}`
    }
    const chartPeople = isNegativeRankingQuestion() ? sortedPeople : [...directChildren]
      .filter(item => item?.name)
      .sort((a, b) => (getNodeMetricValue(b, rankingMetric) || 0) - (getNodeMetricValue(a, rankingMetric) || 0))
    const chartRows = chartPeople.map(person => {
      const personRate = getNodeMetricValue(person, rateMetric) || 0
      return {
      名称: person.name,
      [rateMetric.label || rateMetric.column || '达成率']: personRate,
      [actualMetric?.label || actualMetric?.column || '完成']: getNodeMetricValue(person, actualMetric) || 0,
      [taskMetric?.label || taskMetric?.column || '任务']: getNodeMetricValue(person, taskMetric) || 0,
      ...(remainMetric ? { [remainMetric.label || remainMetric.column || '剩余']: getNodeMetricValue(person, remainMetric) || 0 } : {}),
      标签: getOfficeRateTag(personRate, config, '标杆'),
    }
    })
    const officeKpis = [
      taskMetric ? { label: taskMetric.label || taskMetric.column, value: formatMetricByDefinition(getNodeMetricValue(office, taskMetric), taskMetric, dataset) } : null,
      actualMetric ? { label: actualMetric.label || actualMetric.column, value: formatMetricByDefinition(getNodeMetricValue(office, actualMetric), actualMetric, dataset) } : null,
      { label: rateMetric.label || rateMetric.column || '达成率', value: formatMetricByDefinition(rate, rateMetric, dataset) },
      remainMetric ? { label: remainMetric.label || remainMetric.column, value: formatMetricByDefinition(getNodeMetricValue(office, remainMetric), remainMetric, dataset) } : null,
    ].filter(Boolean)

    return {
      id: office.id || office.name,
      name: office.name,
      parentName: office.parentName,
      tone,
      rate,
      rateLabel: formatMetricByDefinition(rate, rateMetric, dataset),
      progress: Math.max(0, Math.min(100, rate || 0)),
      childCount: sortedPeople.length,
      isLeafLevel: sortedPeople.length === 0,
      leafLabel: sortedPeople.length === 0 ? '当前最细层' : '',
      kpis: officeKpis,
      tag: getOfficeRateTag(rate, config, '区域标杆'),
      highlight: bestPerson ? `亮点：${bestPerson.name}达成率${formatPersonMetric(bestPerson, rateMetric)}` : '',
      rankLabel: '',
      summary: `${office.name}达成率${formatMetricByDefinition(rate, rateMetric, dataset)}，${getOfficeToneLabel(tone)}；任务${taskMetric ? formatMetricByDefinition(getNodeMetricValue(office, taskMetric), taskMetric, dataset) : '-'} / 已完成${actualMetric ? formatMetricByDefinition(getNodeMetricValue(office, actualMetric), actualMetric, dataset) : '-'}${remainMetric ? ` / 缺口${formatMetricByDefinition(getNodeMetricValue(office, remainMetric), remainMetric, dataset)}` : ''}。${bestPerson ? `亮点：${bestPerson.name}达成率${formatPersonMetric(bestPerson, rateMetric)}` : `暂无${detailLevelLabel}明细`}；${riskPeople.length ? `${riskPeople.length} 个${detailLevelLabel}低于10%风险线` : `暂无低于10%的风险${detailLevelLabel}`}。`,
      chartText: `${office.name}下钻到${detailLevelLabel}层：${bestPerson ? `最高为${describePerson(bestPerson)}` : `暂无${detailLevelLabel}明细`}；${worstPerson ? `最低为${describePerson(worstPerson)}。` : ''}`,
      chartSpec: {
        chartType: 'horizontalDrill',
        title: `${office.name}${detailLevelLabel}达成率与缺口`,
        columns: ['名称', actualMetric?.label || actualMetric?.column || '完成', taskMetric?.label || taskMetric?.column || '任务', remainMetric?.label || remainMetric?.column || '剩余', rateMetric.label || rateMetric.column || '达成率'].filter(Boolean),
        rows: chartRows,
        dataset,
      },
      detailRows: buildOfficeDetailRows({
        columns: ['名称', actualMetric?.label || actualMetric?.column || '完成', taskMetric?.label || taskMetric?.column || '任务', remainMetric?.label || remainMetric?.column || '剩余', rateMetric.label || rateMetric.column || '达成率'].filter(Boolean),
        rows: chartRows,
      }, config),
    }
  }).sort((a, b) => {
    const left = getMetricValueFromOffice(a, rankingMetricLabel) || 0
    const right = getMetricValueFromOffice(b, rankingMetricLabel) || 0
    return isNegativeRankingQuestion() ? left - right : right - left
  })

  const kpis = (config.metrics || []).map(metric => ({
    label: metric.label || metric.column || metric.key,
    value: formatMetricByDefinition(model.rootMetrics?.[metric.key], metric, dataset),
  })).filter(item => item.value !== '-')
  const bestOffice = offices[0]
  const worstOffice = offices[offices.length - 1]
  const riskCount = offices.filter(item => item.tone === 'danger').length
  const officeCompareRows = offices.map(office => ({
    名称: office.name,
    [actualMetric?.label || actualMetric?.column || '完成']: getNodeMetricValue(officeNodes.find(node => node.name === office.name), actualMetric) || 0,
    [taskMetric?.label || taskMetric?.column || '任务']: getNodeMetricValue(officeNodes.find(node => node.name === office.name), taskMetric) || 0,
    ...(remainMetric ? { [remainMetric.label || remainMetric.column || '剩余']: getNodeMetricValue(officeNodes.find(node => node.name === office.name), remainMetric) || 0 } : {}),
    [rateMetric.label || rateMetric.column || '达成率']: office.rate || 0,
    标签: office.tag,
  })).sort((a, b) => {
    const key = rankingMetric.label || rankingMetric.column || '达成率'
    return isNegativeRankingQuestion()
      ? (a[key] || 0) - (b[key] || 0)
      : (b[key] || 0) - (a[key] || 0)
  })
  const officeCompareSpec = {
    chartType: rankingChartType,
    title: `各${compareLevelLabel}${rankingMetricLabel}排序`,
    columns: ['名称', actualMetric?.label || actualMetric?.column || '完成', taskMetric?.label || taskMetric?.column || '任务', remainMetric?.label || remainMetric?.column || '剩余', rateMetric.label || rateMetric.column || '达成率', '标签'].filter(Boolean),
    rows: officeCompareRows,
    sortColumn: rankingMetricLabel,
    lowFirst: isNegativeRankingQuestion(),
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
    officeCompareText: isNegativeRankingQuestion()
      ? `${worstOffice ? `${worstOffice.name}达成率最低，为${worstOffice.rateLabel}` : ''}${bestOffice ? `；最高为${bestOffice.name}，${bestOffice.rateLabel}` : ''}。按低达成率优先展示，便于定位承压节点。`
      : `${bestOffice ? `${bestOffice.name}${rankingMetricLabel}最高，为${findOfficeMetricValueByLabel(bestOffice, rankingMetricLabel) || '-'}` : ''}${worstOffice ? `；${worstOffice.name}${rankingMetricLabel}最低，为${findOfficeMetricValueByLabel(worstOffice, rankingMetricLabel) || '-'}` : ''}。一行一个同层级对象，对齐展示金额和进度条。`,
    summary: isNegativeRankingQuestion()
      ? `本次结果覆盖 ${offices.length} 个${compareLevelLabel}，已按低达成率优先排序。${worstOffice ? `${worstOffice.name}当前完成最弱，达成率${worstOffice.rateLabel}` : ''}${bestOffice ? `；最高为${bestOffice.name}，达成率${bestOffice.rateLabel}` : ''}。`
      : `本次结果覆盖 ${offices.length} 个${compareLevelLabel}。${bestOffice ? `${bestOffice.name}${rankingMetricLabel}最高，为${findOfficeMetricValueByLabel(bestOffice, rankingMetricLabel) || '-'}` : ''}${worstOffice ? `；${worstOffice.name}${rankingMetricLabel}最低，为${findOfficeMetricValueByLabel(worstOffice, rankingMetricLabel) || '-'}` : ''}。`,
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
      cards.push({ label: metric.label || metric.column || metric.key, value: formatMetricByDefinition(value, metric, dataset) })
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
  const requestedLevels = getRequestedLevelValues(getQuestionText(), config)

  return model.levelSections
    .filter(section => (
      !requestedLevels.length
      || requestedLevels.some(value => section.levelValues?.includes(value) || section.levelName?.includes(value))
    ))
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
        .sort((a, b) => {
          const key = rateMetric.label || rateMetric.column || '达成率'
          return isNegativeRankingQuestion()
            ? (a[key] || 0) - (b[key] || 0)
            : (b[key] || 0) - (a[key] || 0)
        })
        .slice(0, 12)
      if (!rows.length) return null
      const titlePrefix = section.trackNames.length ? `${section.trackNames.join(' / ')}：` : ''
      const rateFocused = requestedLevels.length || isRateRankingQuestion()
      const columns = rateFocused
        ? ['名称', rateMetric?.label || rateMetric?.column].filter(Boolean)
        : [
            '名称',
            taskMetric?.label || taskMetric?.column,
            actualMetric?.label || actualMetric?.column,
            rateMetric?.label || rateMetric?.column,
          ].filter(Boolean)
      return {
        chartType: rateFocused ? 'horizontalRateBar' : taskMetric && actualMetric ? 'combo' : 'bar',
        title: `${titlePrefix}${section.levelName}完成情况`,
        columns,
        rows,
        dataset,
        lowFirst: isNegativeRankingQuestion(),
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

const dedupeChartSpecs = (charts = []) => {
  const seen = new Set()
  const result = []
  charts.filter(Boolean).forEach((chart) => {
    const columns = Array.isArray(chart.columns) ? chart.columns.join('|') : ''
    const key = `${chart.chartType || ''}-${chart.title || ''}-${columns}`
    if (seen.has(key)) return
    seen.add(key)
    result.push(chart)
  })
  return result
}

const getDatasetChartSpecs = (dataset, { includeFallback = true } = {}) => {
  if (!dataset || typeof dataset !== 'object') return []
  if (dataset?.report_spec?.scope?.focusNodeIsLeaf) {
    const value = []
    datasetChartSpecCache.set(dataset, { key: [getQuestionText(), includeFallback ? 'fallback' : 'strict', 'leaf-focus-none'].join('|'), value })
    return value
  }
  const cacheKey = [
    getQuestionText(),
    includeFallback ? 'fallback' : 'strict',
    canUseFeature('smart_chart_auto_infer') ? 'infer-on' : 'infer-off',
  ].join('|')
  const cached = datasetChartSpecCache.get(dataset)
  if (cached?.key === cacheKey) return cached.value
  const specCharts = getReportSpecCharts(dataset)
  const value = specCharts.length
    ? dedupeChartSpecs(specCharts)
    : (!includeFallback || !canUseFeature('smart_chart_auto_infer')) ? []
    : dedupeChartSpecs([
    ...buildLayeredBusinessCharts(dataset),
    inferChartSpec(dataset),
    ...buildSingleRowMetricCharts(dataset).map(item => item.chartSpec),
  ])
  datasetChartSpecCache.set(dataset, { key: cacheKey, value })
  return value
}

const buildReportTableBlocks = (datasets = []) => {
  return (datasets || [])
    .filter(dataset => Array.isArray(dataset?.rows) && dataset.rows.length > 0 && Array.isArray(dataset?.columns) && dataset.columns.length > 0)
    .slice(0, 3)
    .map((dataset, index) => {
      const labelColumn = getLabelColumn(dataset)
      const numericColumns = getNumericColumns(dataset)
      const pathColumns = (dataset.columns || []).filter(column => /组织路径|归属组织|组织归属|管理链路|路径|上级名称|分公司|代表处|业务部/.test(column))
      const prioritizedColumns = [
        labelColumn,
        ...pathColumns,
        ...numericColumns,
        ...(dataset.columns || []),
      ].filter(Boolean)
      const columns = Array.from(new Set(prioritizedColumns)).slice(0, 6)
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
    const chartSpecs = getDatasetChartSpecs(dataset)

    return {
      key: `${dataset.dataset_id || index}-${dataset.dataset_name || 'dataset'}`,
      caption: index === 0 ? '主结果视图' : '结果视图',
      dataset,
      metricCards: getMetricCards(dataset),
      chartSpec: chartSpecs[0] || null,
      extraCharts: chartSpecs.slice(1),
    }
  })
))

const sideReportCharts = computed(() => (
  latestDatasets.value
    .slice(0, 3)
    .flatMap((dataset, datasetIndex) => {
      const chartSpecs = getDatasetChartSpecs(dataset)
      return chartSpecs.slice(0, 3).map((chartSpec, chartIndex) => ({
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
        const chartSpecs = getDatasetChartSpecs(dataset)
        return chartSpecs.map((chartSpec, chartIndex) => ({
          key: `${dataset.dataset_id || index}-${dataset.dataset_name || 'dataset'}-${chartIndex}`,
          caption: chartSpec.title || (chartIndex === 0 ? '主结果视图' : `图表 ${chartIndex + 1}`),
          dataset,
          metricCards: getMetricCards(dataset),
          chartSpec,
        }))
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
  const source = reportSourceDatasets.value
  const drillReport = activeBusinessDrillReport.value
  if (drillReport && isCollectionAnswerMode(drillReport)) {
    return buildCollectionMetricCards(drillReport)
  }
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
  buildReportTableBlocks(reportSourceDatasets.value)
))

const reportSourceDatasets = computed(() => (
  reportViewerVisible.value ? reportViewerDatasets.value : latestDatasets.value
))

const findBusinessDrillReport = (datasets = []) => {
  const reports = (datasets || [])
    .map(buildBusinessDrillReport)
    .filter(Boolean)
  if (!reports.length) return null
  // 修 4（渲染侧优先级）：优先使用有明确 answerMode 的报告。
  // 用户问 ranking/TopN 问题时，ranking 报告的 offices 是业务代表层级；
  // 若无优先级，dataset_results[0] 若为 Overview 报告（业务部层级）会被误取，
  // 导致 offices 全是业务部/代表处节点而不是业务代表。
  const INTENT_MODES = ['ranking', 'filter', 'drilldown', 'comparison']
  const intentful = reports.find(r => INTENT_MODES.includes(String(r.answerMode || '').trim()))
  if (intentful) return intentful
  const withOffices = reports.find(r => Array.isArray(r.offices) && r.offices.length > 0)
  if (withOffices) return withOffices
  return reports[0]
}

const businessDrillReport = computed(() => (
  findBusinessDrillReport(latestDatasets.value)
))

const activeBusinessDrillReport = computed(() => (
  reportViewerVisible.value
    ? findBusinessDrillReport(reportViewerDatasets.value)
    : businessDrillReport.value
))

const sideBusinessSummaryText = computed(() => (
  businessDrillReport.value?.primaryAnswer?.text
  || businessDrillReport.value?.filterAnswer?.text
  || businessDrillReport.value?.summary
  || ''
))

const sideBusinessMetricCards = computed(() => (
  businessDrillReport.value
    ? (
        isCollectionAnswerMode(businessDrillReport.value)
          ? buildCollectionMetricCards(businessDrillReport.value)
          : businessDrillReport.value.isSingleFocus
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

const dialogBusinessDrillReport = computed(() => activeBusinessDrillReport.value)

const dialogCoreConclusion = computed(() => {
  const report = dialogBusinessDrillReport.value
  if (report?.answerMode === 'ranking') {
    const metricContext = getReportMetricContext(report)
    const leader = metricContext.best
    const follower = metricContext.ranked[1] || null
    if (leader) {
      const leaderText = findOfficeMetricValueByLabel(leader, metricContext.metricLabel) || '-'
      const followerText = follower ? (findOfficeMetricValueByLabel(follower, metricContext.metricLabel) || '-') : ''
      const diffText = metricContext.diff ? `，较${follower?.name}${metricContext.lowFirst ? '更低' : '更高'}${metricContext.diff}` : ''
      return `${leader.name}当前位于首位，${metricContext.metricLabel}${leaderText}${follower ? `${diffText}` : ''}；建议继续下钻定位差距来自哪些下级单元。`
    }
  }
  if (report?.primaryAnswer?.text) return report.primaryAnswer.text
  if (report?.filterAnswer?.text) return report.filterAnswer.text
  const offices = report?.offices || []
  if (offices.length >= 2) {
    const metricLabel = getSortMetricLabel(report, '达成率')
    const lowFirst = (getReportSortSpec(report).direction || '').toLowerCase() === 'asc'
    const ranked = sortOfficesByAnswerMetric(
      offices.filter(item => getMetricValueFromOffice(item, metricLabel) !== null),
      report,
    )
    const leader = ranked[0]
    const follower = ranked[1]
    if (leader && follower) {
      const leaderValue = getMetricValueFromOffice(leader, metricLabel)
      const followerValue = getMetricValueFromOffice(follower, metricLabel)
      const diff = leaderValue !== null && followerValue !== null
        ? Math.abs(leaderValue - followerValue)
        : null
      const diffText = diff === null
        ? ''
        : isRateMetricLabel(metricLabel)
        ? `${diff.toFixed(2).replace(/\.?0+$/, '')} 个百分点`
        : formatAmount(diff)
      const relationText = lowFirst ? '更低' : '更高'
      return `${leader.name}当前位于首位，较${follower.name}${metricLabel}${relationText}${diffText ? ` ${diffText}` : ''}；建议继续下钻定位差距来自哪些下级单元。`
    }
  }
  const reportText = String(reportViewerReport.value || latestReport.value || '').trim()
  const match = reportText.match(/(?:核心结论|结论)[:：]?\s*([^。\n]{12,120}。?)/)
  if (match?.[1]) return match[1].trim()
  return report?.summary || ''
})

const dialogReportStageTitle = computed(() => {
  const report = dialogBusinessDrillReport.value
  if (!report) return '下钻分析'
  if (report.answerMode === 'ranking') return isLeafOnlyReport(report) ? `${report.compareLevelLabel}排名列表` : `${report.compareLevelLabel}排名结果`
  if (report.answerMode === 'filter') return isLeafOnlyReport(report) ? `${report.compareLevelLabel}命中列表` : `${report.compareLevelLabel}命中结果`
  if (report.answerMode === 'drilldown') return `${report.compareLevelLabel}下钻分析`
  return isLeafOnlyReport(report) ? `${report.compareLevelLabel}结果列表` : `${report.compareLevelLabel}下钻分析`
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

const getQuestionTargetLevel = (questionText = getQuestionText()) => {
  const hit = requestedLevelTokens.find(token => token && questionText.includes(token))
  return hit || ''
}

const getDirectAnswerFromRows = (report) => {
  const dataset = report?.dataset
  const rows = Array.isArray(dataset?.rows) ? dataset.rows : []
  if (!rows.length) return null
  const questionText = getQuestionText()
  const targetLevel = getQuestionTargetLevel(questionText)
  if (!targetLevel) return null
  const columns = dataset?.columns || Object.keys(rows[0] || {})
  const levelColumn = findColumn(columns, column => /层级|级别|level/i.test(column))
  const nameColumn = findColumn(columns, column => /节点名称|名称|分公司|城市公司|组织/i.test(column)) || columns[0]
  const rateColumn = findColumn(columns, column => isRateColumn(column)) || '达成率'
  const taskColumn = findColumn(columns, column => /总任务|任务金额|目标/i.test(column) && !/剩余|缺口|差额/i.test(column))
  const actualColumn = findColumn(columns, column => /年度开单|开单|完成|实际|销售/i.test(column))
  const remainColumn = findColumn(columns, column => /剩余|缺口|差额|remain/i.test(column))
  const candidates = rows
    .filter(row => {
      const levelText = String(row?.[levelColumn] || '')
      const nameText = String(row?.[nameColumn] || '')
      return levelText.includes(targetLevel) || nameText.includes(targetLevel)
    })
    .map(row => ({
      name: row?.[nameColumn] || row?.节点名称 || row?.名称 || '-',
      level: targetLevel,
      rate: toNumber(row?.[rateColumn]),
      rateLabel: rateColumn ? formatBusinessValueByColumn(row?.[rateColumn], rateColumn, dataset) : '-',
      task: toNumber(row?.[taskColumn]),
      taskLabel: taskColumn ? formatBusinessValueByColumn(row?.[taskColumn], taskColumn, dataset) : '-',
      actual: toNumber(row?.[actualColumn]),
      actualLabel: actualColumn ? formatBusinessValueByColumn(row?.[actualColumn], actualColumn, dataset) : '-',
      remain: toNumber(row?.[remainColumn]),
      remainLabel: remainColumn ? formatBusinessValueByColumn(row?.[remainColumn], remainColumn, dataset) : '-',
    }))
    .filter(item => item.name && item.rate !== null)
  if (!candidates.length) return null
  const lowFirst = isNegativeRankingQuestion(questionText)
  const winner = [...candidates].sort((left, right) => (
    lowFirst ? (left.rate || 0) - (right.rate || 0) : (right.rate || 0) - (left.rate || 0)
  ))[0]
  const metricText = /线下/.test(questionText) ? '线下业务' : '当前口径'
  const directionText = lowFirst ? '完成最弱' : '完成最好'
  const riskText = winner.rate !== null && winner.rate < 60
    ? `但达成率低于60%红线，仍需关注任务缺口和后续转化。`
    : '当前未触发60%红线。'
  return {
    ...winner,
    targetLevel,
    sentence: `${metricText}${directionText}的${targetLevel}是${winner.name}，达成率${winner.rateLabel}，总任务${winner.taskLabel}，实际开单${winner.actualLabel}，任务缺口${winner.remainLabel}；${riskText}`,
  }
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
  if (report.answerMode === 'ranking') {
    const metricContext = getReportMetricContext(report)
    const configuredTopN = getConfiguredTopN(report)
    const ranked = metricContext.ranked.length ? metricContext.ranked : offices
    const topItems = ranked.slice(0, configuredTopN)
    const bottomItems = [...ranked].reverse().slice(0, configuredTopN)
    const riskCount = offices.filter(item => item.tone === 'danger').length
    const metricTable = buildComparisonMetricTable(ranked)
    return [
      {
        title: '一、核心结论',
        body: [
          report.primaryAnswer?.text || report.summary,
          metricContext.best && metricContext.worst && metricContext.best.name !== metricContext.worst.name
            ? `${metricContext.best.name}${metricContext.metricLabel}${findOfficeMetricValueByLabel(metricContext.best, metricContext.metricLabel) || '-'}位于榜首；${metricContext.worst.name}${metricContext.metricLabel}${findOfficeMetricValueByLabel(metricContext.worst, metricContext.metricLabel) || '-'}位于末位${metricContext.diff ? `，首尾相差${metricContext.diff}` : ''}。`
            : '',
          riskCount
            ? `风险信号：当前结果中有${riskCount}个对象处于低达成风险，排名领先不代表进度无风险。`
            : '风险信号：当前结果内暂无明显低达成风险对象。',
        ].filter(Boolean).join('\n'),
      },
      {
        title: '二、关键指标与排序结果',
        body: [
          metricTable,
          `当前按${metricContext.metricLabel}${metricContext.lowFirst ? '由低到高' : '由高到低'}排序；右侧列表、图表与摘要已统一使用这一指标。`,
        ].filter(Boolean).join('\n\n'),
      },
      {
        title: `三、${report.compareLevelLabel}Top${configuredTopN}/末${configuredTopN}`,
        body: [
          `Top${configuredTopN}：`,
          buildRankMetricTable(topItems, report.compareLevelLabel || '对象'),
          '',
          `末${configuredTopN}：`,
          buildRankMetricTable(bottomItems, report.compareLevelLabel || '对象'),
        ].filter(Boolean).join('\n\n'),
      },
      {
        title: '四、后续动作',
        body: [
          metricContext.best ? `榜首复盘：优先复盘${metricContext.best.name}在${metricContext.metricLabel}上的领先做法，并核对其达成率与缺口是否同步健康。` : '',
          metricContext.worst ? `末位下钻：围绕${metricContext.worst.name}继续下钻${report.detailLevelLabel}，确认是任务体量、项目阶段还是客户转化拖累。` : '',
          '统一口径：排名按问题中的指标排序，风险继续看达成率与缺口，避免把“排位”和“健康度”混为一谈。',
        ].filter(Boolean).join('\n'),
      },
    ]
  }
  const ranked = [...offices].filter(item => item.rate !== null).sort((a, b) => (b.rate || 0) - (a.rate || 0))
  const best = ranked[0] || offices[0]
  const worst = ranked[ranked.length - 1] || offices[offices.length - 1]
  const configuredTopN = getConfiguredTopN(report)
  const topItems = ranked.slice(0, configuredTopN)
  const bottomItems = [...ranked].reverse().slice(0, configuredTopN)
  const directAnswer = getDirectAnswerFromRows(report)
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
    `Top${configuredTopN}：`,
    buildRankMetricTable(topItems, report.compareLevelLabel || '对象'),
    '',
    `末${configuredTopN}：`,
    buildRankMetricTable(bottomItems, report.compareLevelLabel || '对象'),
  ].filter(Boolean).join('\n\n')

  if (report.isSingleFocus) {
    const focusName = report.focusName || '当前组织'
    const counts = getSingleOrgCounts(report)
    const rankContext = getSingleOrgRankContext(report)
    const overallRate = getReportKpiText(report, 'rate')
    const tableRows = offices.length <= 6
      ? offices
      : [
          ...ranked.slice(0, configuredTopN),
          ...ranked.slice(-Math.min(2, configuredTopN)),
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
          directAnswer
            ? `1. ${directAnswer.sentence}`
            : `1. 当前进度：${getSingleOrgConclusion(report)}`,
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
        title: `三、${counts.directLabel}Top${configuredTopN}/末${configuredTopN}对比`,
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
        directAnswer
          ? `1. ${directAnswer.sentence}`
          : diff
          ? `1. 当前对比覆盖${visibleNames}，${best.name}达成率${best.rateLabel}领先，${worst.name}达成率${worst.rateLabel}承压，首尾差${diff}个百分点。`
          : `1. ${report.summary}`,
        `2. 头部/尾部差异：Top${configuredTopN}为${topItems.map(item => `${item.name}(${item.rateLabel})`).join('、') || '暂无'}；末${configuredTopN}为${bottomItems.map(item => `${item.name}(${item.rateLabel})`).join('、') || '暂无'}。`,
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
      title: `三、${report.compareLevelLabel}Top${configuredTopN}/末${configuredTopN}对比`,
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
        `标杆经验推广：由${directAnswer?.name || best.name}沉淀关键动作，覆盖${bottomItems.map(item => item.name).join('、') || '低达成节点'}，两周内完成打法复盘和任务拆解。`,
        `压力节点帮扶：围绕${worst.name}下钻${report.detailLevelLabel}，责任方为业务负责人+经营分析；输出项目阶段、客户转化、缺口金额三类问题清单。`,
        `整体优化：按达成率分布配置资源，低于20%节点进入周度专项，20%-40%节点做过程纠偏，高于40%节点提炼可复制打法。`,
      ].join('\n'),
    },
  ]
}

const reportOverviewTitle = computed(() => {
  const drillReport = activeBusinessDrillReport.value
  return drillReport?.isSingleFocus
    ? `${drillReport.focusName || '当前组织'}业绩核心结论`
    : '分析摘要'
})

const reportSummaryBullets = computed(() => {
  const bullets = []
  const sourceDatasets = reportSourceDatasets.value
  const primary = sourceDatasets[0]
  const drillReport = activeBusinessDrillReport.value
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
    const metricContext = getReportMetricContext(drillReport)
    const best = metricContext.best || drillReport.offices[0]
    const worst = metricContext.worst || drillReport.offices[drillReport.offices.length - 1]
    const riskCount = drillReport.offices.filter(item => item.tone === 'danger').length
    bullets.push(`当前覆盖 ${drillReport.offices.length} 个${drillReport.compareLevelLabel}，先横向比较再下钻${drillReport.detailLevelLabel}。`)
    if (best && worst) {
      bullets.push(metricContext.diff
        ? `${best.name}${metricContext.metricLabel}${findOfficeMetricValueByLabel(best, metricContext.metricLabel) || '-'}领先，${worst.name}${metricContext.metricLabel}${findOfficeMetricValueByLabel(worst, metricContext.metricLabel) || '-'}位于末位，首尾差${metricContext.diff}。`
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

const togglePanel = () => {
  showPanel.value = !showPanel.value
  nextTick(resizeRenderedCharts)
}
const toggleThinking = (id) => { thinkingOpen[id] = !thinkingOpen[id] }
const toggleLog = (i) => { logOpen[i] = !logOpen[i] }
const setResultChainRef = (id, el) => {
  if (!id) return
  if (el) resultChainRefs.set(id, el)
  else resultChainRefs.delete(id)
}
const openDetailPanel = (msg = null) => {
  if (msg?.data && !msg.data.error && !msg.data.requires_confirmation) {
    detailReportResult.value = JSON.parse(JSON.stringify(msg.data))
  } else {
    detailReportResult.value = null
  }
  showPanel.value = true
  nextTick(resizeRenderedCharts)
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
  detailReportResult.value = null
  Object.keys(logOpen).forEach(k => delete logOpen[k])
  // S1 信号重置：开始新一轮执行即脱离"历史快照恢复"状态
  if (session?.state) session.state.isHistoricalSnapshot = false
  timelineVersion.value += 1
  nextTick(() => {
    if (panelRef.value) panelRef.value.scrollTop = 0
  })
}

const clearChatUiState = () => {
  Object.keys(thinkingOpen).forEach(k => delete thinkingOpen[k])
  Object.keys(confirmationDrafts).forEach(k => delete confirmationDrafts[k])
  Object.keys(confirmationSubmitting).forEach(k => delete confirmationSubmitting[k])
  Object.keys(confirmExpanded).forEach(k => delete confirmExpanded[k])
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
  nextTick(resizeRenderedCharts)
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
    !session.state.isHistoricalSnapshot &&
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

const currentSessionAiMessage = computed(() => (
  [...messages].reverse().find(item => item?.role === 'ai' && isCurrentSessionMessage(item)) || latestAiMessage.value || null
))

const activeRequestAiMessage = computed(() => (
  messages.find(item => item?.id === activeRequestAiMessageId.value) || null
))

const syncPendingConfirmationMessage = () => {
  const result = session.state.result
  if (session.state.status !== 'waiting_confirmation' || !result?.requires_confirmation) return

  const msg = activeRequestAiMessage.value || currentSessionAiMessage.value
  if (!msg || msg.role !== 'ai') return
  if (msg.data?.requires_confirmation) return

  msg.loading = false
  msg.data = JSON.parse(JSON.stringify(result))
  thinkingOpen[msg.id] = false
  if (!(msg.id in confirmationDrafts)) confirmationDrafts[msg.id] = ''
  stopTimer()
  scheduleChatScroll(36, 'smooth')
}

const syncCompletedResultMessage = () => {
  const result = session.state.result
  if (session.state.status !== 'completed' || !result || result?.requires_confirmation || result?.error) return

  const msg = activeRequestAiMessage.value || currentSessionAiMessage.value
  if (!msg || msg.role !== 'ai') return

  const sameQuestion = !result.question || !session.state.question || result.question === session.state.question
  if (!sameQuestion) return

  const needsSync = msg.loading || !msg.data || !Array.isArray(msg.data?.dataset_results)
  if (!needsSync) return

  msg.loading = false
  msg.data = JSON.parse(JSON.stringify(result))
  thinkingOpen[msg.id] = false
  stopTimer()
  scheduleChatReportTop(48, 'smooth')
}

const shouldShowLiveFeed = (msg) => {
  if (msg?.loading) return true
  if (!session.state.logs.length) return false
  if (msg?.data?.requires_confirmation) return false
  if (msg?.data?.aborted) return isLatestAiMessage(msg) || isCurrentSessionMessage(msg)
  return Boolean(
    isCurrentSessionMessage(msg) ||
    (isLatestAiMessage(msg) && ['completed', 'canceled', 'error'].includes(session.state.status))
  )
}

const getLiveFeedMode = (msg) => {
  if (msg?.data?.aborted || session.state.status === 'canceled') return 'canceled'
  if (!msg?.data?.aborted && session.state.status === 'completed' && (isCurrentSessionMessage(msg) || isLatestAiMessage(msg))) {
    return 'completed'
  }
  if (msg?.loading) return 'live'
  return 'completed'
}

const shouldShowThinkingCard = (msg) => {
  if (msg?.loading) return !session.state.logs.length
  return false
}

const shouldShowConfirmationCard = (msg) => Boolean(
  !isViewingReadonly.value && msg?.data?.requires_confirmation && !confirmationSubmitting[msg.id] && !msg?.loading
)

const shouldShowConfirmationSubmitted = (msg) => Boolean(
  !isViewingReadonly.value && msg?.data?.requires_confirmation && confirmationSubmitting[msg.id]
)

const isMessageExecutionComplete = (msg) => {
  if (!msg?.data || msg?.loading || msg?.data?.error || msg?.data?.requires_confirmation) return false
  if (isViewingReadonly.value) return true
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

const getMessageDerived = (msg) => {
  if (!msg || typeof msg !== 'object') return null
  const data = msg.data || null
  const datasetResults = data?.dataset_results || null
  const questionKey = getQuestionText()
  const cached = messageDerivedCache.get(msg)
  if (cached?.data === data && cached?.datasetResults === datasetResults && cached?.questionKey === questionKey) {
    return cached
  }
  const entry = {
    data,
    datasetResults,
    questionKey,
    datasets: null,
    report: undefined,
    primaryDataset: undefined,
    visualPreviews: undefined,
  }
  messageDerivedCache.set(msg, entry)
  return entry
}

const getDatasets = (msg) => {
  const cache = getMessageDerived(msg)
  if (cache?.datasets) return cache.datasets
  const raw = Array.isArray(msg?.data?.dataset_results) ? msg.data.dataset_results : []
  if (!raw.length) {
    if (cache) cache.datasets = []
    return []
  }
  const subjectByDatasetId = new Map()
  const orgRoute = msg?.data?.diagnostics?.advanced?.route_guard?.organization_route || {}
  ;(orgRoute.organization_mentions || []).forEach((item) => {
    const subjectName = String(item?.node_name || '').trim()
    if (!subjectName) return
    ;(item?.dataset_ids || []).forEach((id) => {
      const numericId = Number(id)
      if (Number.isFinite(numericId)) {
        subjectByDatasetId.set(numericId, subjectName)
      }
    })
  })
  const enriched = raw.map((dataset) => {
    const subjectName = subjectByDatasetId.get(Number(dataset?.dataset_id))
    return subjectName
      ? { ...dataset, comparison_subject_name: subjectName, comparison_subject_level: inferSubjectLevel(subjectName) }
      : dataset
  })
  const visible = enriched.filter(dataset => isDatasetVisible(dataset?.dataset_id))
  const datasetsForMessage = visible.length ? visible : enriched
  if (cache) cache.datasets = datasetsForMessage
  return datasetsForMessage
}
const getReport = (msg) => {
  const cache = getMessageDerived(msg)
  if (cache && cache.report !== undefined) return cache.report
  const report = mergeDatasetReports(getDatasets(msg))
  if (cache) cache.report = report
  return report
}
const getPrimaryDataset = (msg) => {
  const cache = getMessageDerived(msg)
  if (cache && cache.primaryDataset !== undefined) return cache.primaryDataset
  const dataset = buildAggregateDataset(getDatasets(msg))
  if (cache) cache.primaryDataset = dataset
  return dataset
}
const getResultTitle = (msg) => {
  if (msg.data?.display_title) {
    return msg.data.display_title.length > 20 ? `${msg.data.display_title.slice(0, 20)}...` : msg.data.display_title
  }
  const raw = msg.data?.question || session.state.question || '本月公司经营表现分析'
  const normalized = normalizeReportTitle(raw)
  return normalized.length > 20 ? `${normalized.slice(0, 20)}...` : normalized
}

const formatElapsedLabel = (seconds) => {
  const totalSeconds = Math.max(0, Math.round(Number(seconds) || 0))
  const minutes = Math.floor(totalSeconds / 60)
  const remain = totalSeconds % 60
  if (minutes <= 0) return `${remain}s`
  return `${minutes}m ${remain}s`
}

const isAbortLikeInteractionError = (error) => {
  const text = `${error?.name || ''} ${error?.code || ''} ${error?.message || ''}`
  return Boolean(
    error?.isUserAbort ||
    /AbortError|CanceledError|ERR_CANCELED|aborted|cancelled|canceled|BodyStreamBuffer/i.test(text)
  )
}

const getMessageElapsedLabel = (msg) => {
  if (msg?.loading && isCurrentSessionMessage(msg)) {
    return formatElapsedLabel(elapsed.value)
  }
  return ''
}

const getAskFlowMeta = (msg) => {
  if (!showAskFlowBadge.value) return null
  const meta = msg?.data?.ask_flow || msg?.data?.diagnostics?.ask_flow || null
  return meta && typeof meta === 'object' ? meta : null
}

const getAskFlowLabel = (msg) => {
  const flow = String(getAskFlowMeta(msg)?.flow || '').toLowerCase()
  if (flow === 'advanced') return '进阶流程'
  if (flow === 'basic') return '基础流程'
  return ''
}

const getAskFlowClass = (msg) => {
  const flow = String(getAskFlowMeta(msg)?.flow || '').toLowerCase()
  return flow === 'advanced' ? 'is-advanced' : 'is-basic'
}

const getAskFlowHint = (msg) => {
  const reason = String(getAskFlowMeta(msg)?.reason || '')
  const map = {
    basic_selected: '由基础流程执行',
    advanced_selected: '由进阶流程执行',
    advanced_disabled: '进阶未启用，已回落基础流程',
    advanced_role_denied: '当前角色未进入进阶灰度',
    advanced_error_fallback: '进阶异常，已回退基础流程',
  }
  return map[reason] || ''
}

const getVisualPreviews = (msg) => {
  const cache = getMessageDerived(msg)
  if (cache && cache.visualPreviews !== undefined) return cache.visualPreviews
  const sourceDatasets = getDatasets(msg)
  const previews = hasBusinessDrillDataset(sourceDatasets) ? [] : sourceDatasets
    .slice(0, 2)
    .map((dataset, index) => ({
      key: `${dataset.dataset_id || index}-${dataset.dataset_name || 'dataset'}`,
      dataset,
      chartSpec: getDatasetChartSpecs(dataset)[0] || null,
    }))
    .filter(item => item.chartSpec && (item.chartSpec.chartType === 'metric' || hasChartRows(item.chartSpec)))
  if (cache) cache.visualPreviews = previews
  return previews
}

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
  if (!canUseFeature('smart_question_copy')) return
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
  if (!canUseFeature('smart_question_edit')) return
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
    delete confirmExpanded[item.id]
  })
}

const rerunQuestion = async (msg) => {
  if (!canUseFeature('smart_question_rerun')) return
  const text = String(msg?.content || '').trim()
  if (!text || isRunning.value) return

  // 重问创建新的任务条目
  const createShellId = () => {
    if (typeof window !== 'undefined' && window.crypto?.randomUUID) {
      return `history-report-${window.crypto.randomUUID()}`
    }
    return `history-report-${Date.now()}-${Math.random().toString(16).slice(2)}`
  }
  const shellId = createShellId()

  const runningShell = {
    id: shellId,
    title: String(text).slice(0, 24),
    question: text,
    datasetId: datasetId.value || null,
    datasetName: datasets.value.find(d => d.id === datasetId.value)?.name || '',
    updatedAt: new Date().toISOString(),
    status: 'running',
    reportSnapshot: null,
  }
  upsertHistory(runningShell)
  setActiveHistory(shellId)
  setRunningSessionId(shellId)
  switchViewToDefault()

  session.resetSession()
  clearChatUiState()
  messages.splice(0, messages.length)
  const uid = ++msgCounter
  messages.push({ id: uid, role: 'user', content: text })
  const aid = ++msgCounter
  const aiMsg = { id: aid, role: 'ai', loading: true, data: null }
  messages.push(aiMsg)
  activeRequestAiMessageId.value = aid
  thinkingOpen[aid] = true

  query.value = ''
  showPanel.value = true
  clearExecutionPanelState()
  scheduleChatScroll(24, 'smooth')
  startTimer()

  try {
    const datasetInput = getDatasetInputForQuestion(text)
    const res = await session.startAsk(text, datasetInput, getModelInputForQuestion())
    clearPendingQuickDataset()
    if (res) {
      aiMsg.loading = false
      aiMsg.data = res
      if (res?.requires_confirmation) {
        markRunningTaskPending(shellId)
        upsertHistory({ ...runningShell, status: 'pending_confirmation' })
      } else if (!res?.error) {
        saveCurrentToHistory(res, { preferId: shellId })
        markRunningTaskCompleted(shellId)
      } else {
        markRunningTaskFailed(shellId)
      }
    } else if (!aiMsg.data) {
      aiMsg.loading = false
      aiMsg.data = { aborted: true }
      markRunningTaskFailed(shellId)
    } else {
      aiMsg.loading = false
      markRunningTaskFailed(shellId)
    }
    thinkingOpen[aid] = false
    if (res && !res?.requires_confirmation && !res?.error) scheduleChatReportTop(48, 'smooth')
    else scheduleChatScroll(48, 'smooth')
  } catch (err) {
    if (isAbortLikeInteractionError(err)) {
      aiMsg.loading = false
      aiMsg.data = { aborted: true, question: text }
      thinkingOpen[aid] = false
      scheduleChatScroll(36, 'smooth')
      markRunningTaskFailed(shellId)
      return
    }
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
  if (!canUseFeature('smart_send_question')) return
  const text = query.value.trim()
  if (!text || isRunning.value) return

  const createShellId = () => {
    if (typeof window !== 'undefined' && window.crypto?.randomUUID) {
      return `history-report-${window.crypto.randomUUID()}`
    }
    return `history-report-${Date.now()}-${Math.random().toString(16).slice(2)}`
  }
  const shellId = createShellId()

  const runningShell = {
    id: shellId,
    title: String(text).slice(0, 24),
    question: text,
    datasetId: datasetId.value || null,
    datasetName: datasets.value.find(d => d.id === datasetId.value)?.name || '',
    updatedAt: new Date().toISOString(),
    status: 'running',
    reportSnapshot: null,
  }
  upsertHistory(runningShell)
  setActiveHistory(shellId)
  setRunningSessionId(shellId)
  switchViewToDefault()

  const uid = ++msgCounter
  messages.push({ id: uid, role: 'user', content: text })
  const aid = ++msgCounter
  const aiMsg = { id: aid, role: 'ai', loading: true, data: null }
  messages.push(aiMsg)
  activeRequestAiMessageId.value = aid
  thinkingOpen[aid] = true

  showPanel.value = true
  clearExecutionPanelState()
  scheduleChatScroll(24, 'smooth')
  startTimer()

  try {
    const datasetInput = getDatasetInputForQuestion(text)
    const res = await session.startAsk(text, datasetInput, getModelInputForQuestion())
    clearPendingQuickDataset()
    if (res) {
      aiMsg.loading = false
      aiMsg.data = res
      if (res?.requires_confirmation) {
        markRunningTaskPending(shellId)
        upsertHistory({ ...runningShell, status: 'pending_confirmation' })
      } else if (!res?.error) {
        saveCurrentToHistory(res, { preferId: shellId })
        markRunningTaskCompleted(shellId)
      } else {
        markRunningTaskFailed(shellId)
      }
    } else if (!aiMsg.data) {
      aiMsg.loading = false
      aiMsg.data = { aborted: true }
      markRunningTaskFailed(shellId)
    } else {
      aiMsg.loading = false
      markRunningTaskCompleted(shellId)
    }
    query.value = ''
    thinkingOpen[aid] = false
    if (res && !res?.requires_confirmation && !res?.error) scheduleChatReportTop(48, 'smooth')
    else scheduleChatScroll(48, 'smooth')
  } catch (err) {
    if (isAbortLikeInteractionError(err)) {
      aiMsg.loading = false
      aiMsg.data = { aborted: true, question: text }
      thinkingOpen[aid] = false
      scheduleChatScroll(36, 'smooth')
      markRunningTaskFailed(shellId)
      return
    }
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
    markRunningTaskFailed(shellId)
  } finally {
    stopTimer()
  }
}

const handleStop = () => {
  if (!canUseFeature('smart_stop_run')) return
  session.stopAsk()
  const msg = latestAiMessage.value
  if (msg?.role === 'ai' && msg.loading) {
    msg.loading = false
    msg.data = {
      ...(msg.data || {}),
      aborted: true,
      question: session.state.question || query.value.trim(),
    }
    thinkingOpen[msg.id] = false
  }
  stopTimer()
  if (runningSessionId.value) {
    markRunningTaskFailed(runningSessionId.value)
  }
  ElMessage({
    message: '已停止执行',
    type: 'warning',
    duration: 1500,
    showClose: false,
    customClass: 'sa-toast-modern sa-toast-stop',
  })
}

const resetForNewChat = () => {
  // 修 1（reset 保存 guard）：只有完整、正确的结果才保存，避免把 requires_confirmation 中间态
  // （业务部 Overview 层级）当成正式历史保存；也避免旧会话残留的脏 result 被保存。
  const cur = session.state.result || null
  const isCompleteResult = Boolean(
    cur &&
    typeof cur === 'object' &&
    !cur.requires_confirmation &&
    !cur.error &&
    Array.isArray(cur.dataset_results) &&
    cur.dataset_results.length > 0
  )
  if (isCompleteResult) saveCurrentToHistory(cur)
  messages.splice(0, messages.length)
  activeRequestAiMessageId.value = null
  query.value = ''
  clearRestoreRequest()
  setActiveHistory('')
  clearChatUiState()
  session.resetSession()
  showPanel.value = true
  nextTick(() => {
    scheduleChatScroll(20, 'auto')
    schedulePanelScroll(20, 'auto', true)
    focusComposer()
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

const normalizeReportTitle = (text) => {
  let s = String(text ?? '').trim()
  if (!s) return '业绩分析报告'
  s = s.replace(
    /^(?:我说的是|我说的是|我说|我的问题是|我想问|我想知道|请问|问一下|看一下|查一下|看下|查下|请|麻烦|帮我|给我|告诉我|咨询一下|了解一下|看看)(?:[，,：:\s]+)?/,
    ''
  )
  s = s.replace(/[？?！!。]+$/g, '').trim()
  if (s.endsWith('的')) {
    s = s.slice(0, -1).trim()
  }
  return s || '业绩分析报告'
}

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
    :root { --primary: #1A1A1A; --page-bg: #F8F9FA; --card-bg: #ffffff; --text: #111827; }
    body { margin: 0; font-family: var(--font-sans, "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", sans-serif); background: var(--page-bg); color: var(--text); }
    .page { max-width: 960px; margin: 0 auto; padding: 40px 24px 72px; }
    .card { background: var(--card-bg); border-radius: 8px; padding: 28px 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    .eyebrow { font-size: 12px; color: var(--primary); font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
    h1 { margin: 12px 0 8px; font-size: 28px; line-height: 1.25; }
    h2 { margin: 28px 0 12px; font-size: 20px; }
    h3 { margin: 20px 0 10px; font-size: 16px; }
    p, li { font-size: 14px; line-height: 1.8; color: #6B7280; }
    hr { border: none; border-top: 1px solid #E5E7EB; margin: 24px 0; }
    code { background: #F3F4F6; padding: 2px 6px; border-radius: 6px; }
    table { width: 100%; border-collapse: collapse; margin: 16px 0; }
    th, td { border: 1px solid #E5E7EB; padding: 10px 12px; text-align: left; font-size: 13px; }
    th { background: #F8F9FA; color: #111827; }
    .print-tip { margin-top: 20px; font-size: 12px; color: #9CA3AF; }
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
const quickAsk = (item) => {
  if (!canUseFeature('smart_quick_ask')) return
  const text = typeof item === 'string' ? item : String(item?.question_text || '').trim()
  if (!text) return
  const nextDatasetId = typeof item === 'string' ? null : Number(item?.dataset_id || 0)
  datasetId.value = null
  isDatasetManuallySelected.value = false
  pendingQuickDataset.value = nextDatasetId ? { datasetId: nextDatasetId, question: text } : null
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
    message: datasetName ? `问题已填入 · ${datasetName}` : '问题已填入',
    type: 'success',
    duration: 1500,
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
const getConfirmOptionScore = (opt) => {
  if (typeof opt === 'string') return null
  const raw = opt?.score
  if (raw === null || raw === undefined || raw === '') return null
  const n = Number(raw)
  return Number.isFinite(n) ? Math.round(n) : null
}
const shouldShowConfirmOptionScore = () => false
const getConfirmOptionScorePct = (opt) => {
  const score = getConfirmOptionScore(opt)
  return score == null ? 0 : Math.min(100, Math.max(0, score))
}
const sortedConfirmationOptions = (msg) => {
  const opts = msg?.data?.confirmation_options || []
  const copy = opts.map((opt, idx) => ({ opt, idx }))
  copy.sort((a, b) => {
    const sa = getConfirmOptionScore(a.opt)
    const sb = getConfirmOptionScore(b.opt)
    if (sa != null && sb != null) return sb - sa
    if (sa != null) return -1
    if (sb != null) return 1
    return a.idx - b.idx
  })
  return copy.map(item => item.opt)
}
const visibleConfirmationOptions = (msg) => {
  const opts = sortedConfirmationOptions(msg)
  if (confirmExpanded[msg?.id]) return opts
  return opts.slice(0, 4)
}
const toggleConfirmOptions = (msgId) => {
  confirmExpanded[msgId] = !confirmExpanded[msgId]
}
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
  // 第一时间设置提交状态，立即禁用按钮，防止重复点击或事件冒泡干扰
  if (msg?.id) confirmationSubmitting[msg.id] = true
  // 用户确认后，全局状态从待确认变回执行中，同步顶部banner和左侧任务状态
  if (runningTaskStatus.value === 'pending_confirmation' && runningSessionId.value) {
    runningTaskStatus.value = 'running'
    pendingTaskId.value = null
    const currentShell = historySessions.value.find(h => h.id === runningSessionId.value)
    if (currentShell) {
      upsertHistory({ ...currentShell, status: 'running' })
    }
  }
  startTimer()
  detailReportResult.value = null
  const originalData = msg?.data ? JSON.parse(JSON.stringify(msg.data)) : null
  if (msg) {
    msg.loading = true
  }
  try {
    const res = await session.submitBossConfirmation(opt, {
      candidateDatasetIds: msg?.data?.route?.candidate_dataset_ids || msg?.data?.route?.dataset_ids || [],
      originalQuestion: msg?.data?.question || session.state.question,
      sessionId: msg?.data?.session_id,
    })
    const last = [...messages].reverse().find(m => m.role === 'ai')
    if (!res) {
      if (last) {
        last.loading = false
        last.data = { aborted: true, question: session.state.question }
      }
      if (msg?.id) confirmationSubmitting[msg.id] = false
      if (runningSessionId.value) markRunningTaskFailed(runningSessionId.value)
      scheduleChatScroll(36, 'smooth')
      return
    }
    if (last) {
      last.loading = false
      last.data = res
      activeRequestAiMessageId.value = last.id
    }
    if (!res?.requires_confirmation && !res?.error) {
      saveCurrentToHistory(res, { preferId: runningSessionId.value })
      markRunningTaskCompleted(runningSessionId.value)
    } else if (res?.requires_confirmation) {
      markRunningTaskPending(runningSessionId.value)
      const currentShell = historySessions.value.find(h => h.id === runningSessionId.value)
      if (currentShell) {
        upsertHistory({ ...currentShell, status: 'pending_confirmation' })
      }
    } else {
      markRunningTaskFailed(runningSessionId.value)
    }
    if (msg?.id && typeof opt === 'string') confirmationDrafts[msg.id] = ''
    if (!res?.requires_confirmation && !res?.error) scheduleChatReportTop(36, 'smooth')
    else scheduleChatScroll(36, 'smooth')
  } catch (error) {
    if (isAbortLikeInteractionError(error)) {
      if (msg) {
        msg.loading = false
        msg.data = { aborted: true, question: session.state.question }
      }
      if (msg?.id) confirmationSubmitting[msg.id] = false
      scheduleChatScroll(36, 'smooth')
      return
    }
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

const scrollChatToReportTop = (behavior = 'auto') => nextTick(() => {
  const container = chatBodyRef.value
  if (!container) return
  const latestId = latestAiMessage.value?.id
  const allResultChains = Array.from(container.querySelectorAll('.sa-result-chain'))
  const target = (latestId && resultChainRefs.get(latestId))
    || allResultChains[allResultChains.length - 1]
  if (!target) {
    scrollChat(behavior)
    return
  }
  const containerRect = container.getBoundingClientRect()
  const targetRect = target.getBoundingClientRect()
  const top = container.scrollTop + targetRect.top - containerRect.top - 12
  container.scrollTo({ top: Math.max(0, top), behavior })
})

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

const {
  saveCurrentToHistory,
  restoreHistory,
} = useSmartAskReportHistory({
  session,
  messages,
  datasetId,
  datasets,
  isRunning,
  isDatasetVisible,
  ensureDatasetsReady,
  loadHistory,
  upsertHistory,
  setActiveHistory,
  detailReportResult,
  showPanel,
  thinkingOpen,
  logOpen,
  timelineVersion,
  scrollChat,
  scrollPanel,
  createMessageId: () => ++msgCounter,
})

const scheduleChatScroll = (delay = 40, behavior = 'smooth') => {
  if (isViewingReadonly.value) return
  if (chatScrollTimer) clearTimeout(chatScrollTimer)
  chatScrollTimer = window.setTimeout(() => {
    scrollChat(behavior)
  }, delay)
}

const clearReportTopScrollTimers = () => {
  reportTopScrollTimers.forEach(timer => clearTimeout(timer))
  reportTopScrollTimers = []
}

const scheduleChatReportTop = (delay = 40, behavior = 'auto') => {
  if (isViewingReadonly.value) return
  if (chatScrollTimer) clearTimeout(chatScrollTimer)
  clearReportTopScrollTimers()
  ;[delay, delay + 90, delay + 240].forEach((timeout) => {
    reportTopScrollTimers.push(window.setTimeout(() => {
      scrollChatToReportTop(behavior)
    }, timeout))
  })
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

const compactQuestionText = (value) => String(value || '').replace(/\s+/g, '').toLowerCase()

const isConsumerDatasetMeta = (dataset = {}) => {
  const text = compactQuestionText(`${dataset.dataset_code || ''}${dataset.dataset_name || ''}${dataset.business_domain || ''}${dataset.description || ''}`)
  return text.includes('consumer') || text.includes('消费者') || text.includes('消费事业部')
}

const datasetAliasScore = (text, dataset) => {
  const question = compactQuestionText(text)
  if (!question || !dataset) return 0
  const aliases = [
    dataset.dataset_name,
    dataset.business_domain,
    ...(Array.isArray(dataset.synonyms) ? dataset.synonyms : []),
  ].map(compactQuestionText).filter(Boolean)
  let score = 0
  const suffixes = ['事业部', '分公司', '业务部', '代表处', '数据集', '销售业绩分析', '业绩分析']
  aliases.forEach((alias) => {
    if (alias.length < 2 || ['业绩', '分析', '数据', '指标', '结果'].includes(alias)) return
    if (question.includes(alias)) score = Math.max(score, 95)
    suffixes.forEach((suffix) => {
      if (!alias.includes(suffix)) return
      const prefix = alias.split(suffix, 1)[0]
      if (prefix.length >= 2 && question.includes(prefix)) score = Math.max(score, 90)
    })
  })
  if (isConsumerDatasetMeta(dataset)) {
    const consumerBranchAliases = ['粤桂琼分公司', '粤桂琼', '山东分公司']
    if (consumerBranchAliases.some(alias => question.includes(compactQuestionText(alias)))) {
      score = Math.max(score, 94)
    }
  }
  return score
}

const shouldReleaseSelectedDatasetForQuestion = (text, selectedId) => {
  if (!selectedId) return false
  const selected = datasets.value.find(item => Number(item.id) === Number(selectedId))
  if (!selected) return false
  const selectedScore = datasetAliasScore(text, selected)
  const bestOther = datasets.value
    .filter(item => Number(item.id) !== Number(selectedId))
    .map(item => ({ dataset: item, score: datasetAliasScore(text, item) }))
    .sort((left, right) => right.score - left.score)[0]
  return Boolean(bestOther && bestOther.score >= 90 && bestOther.score >= selectedScore + 12)
}

const getDatasetInputForQuestion = (text) => {
  if (!canUseFeature('smart_dataset_select')) return null
  const pending = pendingQuickDataset.value
  if (pending?.datasetId && String(pending.question || '').trim() === String(text || '').trim()) {
    if (shouldReleaseSelectedDatasetForQuestion(text, pending.datasetId)) return null
    return pending.datasetId
  }
  if (datasetId.value && isDatasetManuallySelected.value) {
    return datasetId.value
  }
  return null
}

const getModelInputForQuestion = () => (
  canUseFeature('smart_model_select') ? modelId.value : null
)

const clearPendingQuickDataset = () => {
  pendingQuickDataset.value = null
}

const submitConfirmationDraft = (msg) => {
  if (!canUseFeature('smart_submit_note')) return
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

const handleDatasetChange = async () => {
  if (!canUseFeature('smart_dataset_select')) {
    datasetId.value = null
    isDatasetManuallySelected.value = false
    clearPendingQuickDataset()
    return
  }
  isDatasetManuallySelected.value = Boolean(datasetId.value)
  clearPendingQuickDataset()
  await loadQuestions()
}

const refreshCommonQuestions = async () => {
  if (!canUseFeature('smart_quick_refresh')) return
  if (commonQuestionsLoading.value) return
  await loadQuestions()
}

const getStatusColor = (rate) => {
  const value = toNumber(rate)
  if (value === null) return '#E61F24'
  if (value >= 15) return '#10B981'
  if (value >= 10) return '#F59E0B'
  return '#E61F24'
}

const getMetricColor = (column) => {
  const text = String(column || '')
  if (/任务|目标/i.test(text)) return '#E61F24'
  if (/开单|完成|实际|销售/i.test(text)) return '#10B981'
  if (/剩余|缺口|差额/i.test(text)) return '#F59E0B'
  if (/率|percent|rate/i.test(text)) return '#f59e0b'
  return '#6B7280'
}

const sortRowsForChart = (rows = [], columns = [], lowFirst = false, preferredColumn = '') => {
  const targetColumn = preferredColumn
    || columns.find(column => isRateColumn(column))
    || Object.keys(rows[0] || {}).find(column => isRateColumn(column))
  if (!targetColumn) return rows
  return [...rows].sort((a, b) => {
    const left = toNumber(a?.[targetColumn]) || 0
    const right = toNumber(b?.[targetColumn]) || 0
    return lowFirst ? left - right : right - left
  })
}

const renderChartSpec = (chart, data) => {
  const labelColumn = data.columns?.[0]
  const numericColumns = data.columns?.slice(1) || []
  const dataset = data?.dataset || null
  const preferredSortColumn = data.sortColumn || ''
  const sortedRows = sortRowsForChart(data.rows || [], data.columns || [], Boolean(data.lowFirst), preferredSortColumn)
  const colorPalette = ['#1A1A1A', '#10B981', '#F59E0B', '#E61F24', '#9CA3AF', '#6B7280']
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
      legend: { top: 0, textStyle: { color: '#6B7280', fontSize: 11 } },
      grid: { left: 34, right: 18, top: 34, bottom: 28, containLabel: true },
      xAxis: {
        type: 'category',
        data: sortedRows.map(row => row[labelColumn]),
        axisLabel: { color: '#9CA3AF', fontSize: 11, hideOverlap: true },
        axisLine: { lineStyle: { color: '#E5E7EB' } },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#9CA3AF', fontSize: 11 },
        splitLine: { lineStyle: { color: '#F3F4F6', type: 'dashed' } },
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
        textStyle: { color: '#6B7280', fontSize: 10 },
      },
      grid: { left: 42, right: 38, top: 68, bottom: 44, containLabel: true },
      xAxis: {
        type: 'category',
        data: categoryRows.map(row => row[labelColumn]),
        axisLabel: { color: '#9CA3AF', fontSize: 11, interval: 0, rotate: categoryRows.length > 4 ? 24 : 0, hideOverlap: true, margin: 12 },
        axisLine: { lineStyle: { color: '#E5E7EB' } },
      },
      yAxis: [
        {
          type: 'value',
          axisLabel: {
            color: '#9CA3AF',
            fontSize: 11,
            formatter: value => {
              const axisColumn = barColumns.find(column => isAmountColumn(column)) || barColumns[0] || ''
              return formatChartAmount(value, dataset, axisColumn)
            },
          },
          splitLine: { lineStyle: { color: '#F3F4F6', type: 'dashed' } },
        },
        {
          type: 'value',
          axisLabel: { color: '#9CA3AF', fontSize: 11, formatter: '{value}%' },
          splitLine: { show: false },
        },
      ],
      series: [
        ...barColumns.map((column) => ({
          name: column,
          type: 'bar',
          barMaxWidth: 18,
          itemStyle: { borderRadius: [4, 4, 0, 0], color: getMetricColor(column) },
          label: isAmountColumn(column) ? {
            show: true,
            position: 'top',
            color: '#6B7280',
            fontSize: 10,
            formatter: ({ value }) => formatChartAmount(value, dataset, column),
          } : undefined,
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
            color: '#6B7280',
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
          color: '#6B7280',
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
        itemStyle: { borderRadius: [0, 4, 4, 0], color: '#F59E0B' },
        label: {
          show: true,
          position: 'right',
          color: '#9CA3AF',
          fontSize: 10,
          formatter: ({ value }) => formatChartAmount(value, dataset, remainColumn),
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
        textStyle: { color: '#6B7280', fontSize: 10 },
      },
      grid: { left: 78, right: 58, top: series.length > 1 ? 34 : 14, bottom: 18, containLabel: true },
      xAxis: {
        type: 'value',
        axisLabel: { color: '#9CA3AF', fontSize: 11, formatter: value => `${value}%` },
        splitLine: { lineStyle: { color: '#F3F4F6', type: 'dashed' } },
      },
      yAxis: {
        type: 'category',
        data: categoryRows.map(row => row[labelColumn]),
        axisLabel: { color: '#6B7280', fontSize: 11 },
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
        axisLabel: { color: '#9CA3AF', fontSize: 11, interval: 0, rotate: sortedRows.length > 5 ? 18 : 0 },
        axisLine: { lineStyle: { color: '#E5E7EB' } },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          color: '#9CA3AF',
          fontSize: 11,
          formatter: value => isAmountColumn(valueColumn) ? formatChartAmount(value, dataset, valueColumn) : value,
        },
        splitLine: { lineStyle: { color: '#F3F4F6', type: 'dashed' } },
      },
      series: [{
        type: 'bar',
        barMaxWidth: 22,
        itemStyle: { borderRadius: [5, 5, 0, 0] },
        label: {
          show: true,
          position: 'top',
          color: '#6B7280',
          fontSize: 11,
          fontWeight: 600,
          formatter: ({ value }) => (isAmountColumn(valueColumn) ? formatChartAmount(value, dataset, valueColumn) : formatDisplayValue(value)),
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
        color: '#6B7280',
        fontSize: 11,
        lineHeight: 16,
        formatter: ({ name, percent, value }) => `${name}\n${formatDisplayValue(value)} · ${percent}%`,
      },
      labelLine: {
        show: true,
        length: 10,
        length2: 8,
        lineStyle: {
          color: 'rgba(0, 0, 0, 0.7)',
        },
      },
      data: sortedRows.slice(0, 6).map(row => ({ name: row[labelColumn], value: row[valueColumn] })),
    }],
  })
}

const chartRenderSignature = (data, key = '') => [
  key,
  data?.chartType || '',
  data?.title || '',
  Array.isArray(data?.columns) ? data.columns.join('|') : '',
  Array.isArray(data?.rows) ? data.rows.length : 0,
  data?.lowFirst ? 'low' : 'high',
].join('::')

const scheduleChartResize = (chart) => {
  if (!chart) return
  requestAnimationFrame(() => chart.resize())
}

const resizeRenderedCharts = () => {
  requestAnimationFrame(() => {
    document
      .querySelectorAll('.sa-inline-visual-chart, .sa-main-chart, .sa-side-extra-chart-canvas, .sa-report-chart-canvas, .sa-office-chart')
      .forEach((el) => {
        const chart = echarts.getInstanceByDom(el)
        if (chart) chart.resize()
      })
    if (chartDialogRef.value) {
      const dialogChart = echarts.getInstanceByDom(chartDialogRef.value)
      if (dialogChart) dialogChart.resize()
    }
  })
}

const initPreviewChart = (el, data, key) => {
  if (!el || !data?.rows?.length || !data?.columns?.length) return
  const signature = chartRenderSignature(data, key)
  nextTick(() => {
    const chart = echarts.getInstanceByDom(el) || echarts.init(el)
    const cached = chartElementCache.get(el)
    if (cached?.signature === signature && cached?.data === data) {
      return
    }
    renderChartSpec(chart, data)
    chartElementCache.set(el, { signature, data })
    scheduleChartResize(chart)
  })
}

const initLogChart = (el, data, key) => {
  if (!el || !data?.rows?.length || !data?.columns?.length) return
  const signature = chartRenderSignature(data, key)
  nextTick(() => {
    const chart = echarts.getInstanceByDom(el) || echarts.init(el)
    const cached = chartElementCache.get(el)
    if (cached?.signature === signature && cached?.data === data) {
      return
    }
    renderChartSpec(chart, data)
    chartElementCache.set(el, { signature, data })
    scheduleChartResize(chart)
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
  syncCompletedResultMessage()
  if (s === 'completed') {
    nextTick(() => {
      scheduleChatReportTop(0, 'auto')
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
  syncCompletedResultMessage()
}, { flush: 'post' })

watch(() => hasSideReport.value, (ready) => {
  if (ready && session.state.status === 'completed') {
    scrollPanelToReportTop()
    scheduleChatReportTop(0, 'auto')
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

const handleReturnToRunning = () => {
  switchViewToRunning()
  const targetId = runningSessionId.value || completedTaskId.value
  if (targetId) {
    setActiveHistory(targetId)
  } else {
    setActiveHistory(null)
  }
}

watch(() => pendingRestoreId.value, async (historyId) => {
  if (!historyId) return
  const item = findHistoryById(historyId)
  if (!item) {
    ElMessage.warning('未找到对应的历史对话记录')
    clearRestoreRequest()
    return
  }
  const options = takePendingRestoreOptions()
  await restoreHistory(item, options)
  if (!options?.readonly) {
    datasetId.value = null
    isDatasetManuallySelected.value = false
  }
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
  if (cached.modelId !== undefined) modelId.value = cached.modelId

  try {
    const res = await getBookshelfDatasets()
    datasets.value = res.datasets || []
    markDatasetsLoaded()
    sanitizeDatasetSelection()
    await loadQuestions()
  } catch {}

  try {
    const modelRes = await getActiveAIModels()
    aiModels.value = modelRes.models || []
  } catch {}

  if (session.state.selectedDatasetId && !isDatasetVisible(session.state.selectedDatasetId)) {
    session.state.selectedDatasetId = null
  }

  // 页面重新打开时不自动回灌旧结果；历史恢复仍通过显式操作触发。
  // 守卫细节见 clearStaleSessionState 定义处（L1346 区域）。
  clearStaleSessionState()
})

// keep-alive 重新激活时刷新引用数据（数据集、模型可能在其他页面被修改）
onActivated(async () => {
  try {
    const res = await getBookshelfDatasets()
    datasets.value = res.datasets || []
    markDatasetsLoaded()
    sanitizeDatasetSelection()
  } catch {}
  try {
    const modelRes = await getActiveAIModels()
    aiModels.value = modelRes.models || []
  } catch {}
  loadHistory()
  // keep-alive 切回也会复用旧实例上的 reactive 状态；同样需要清掉刷新/上一次卡死时的残留
  clearStaleSessionState()
})

// 将关键输入状态持久化到 sessionStorage，页面跳转后还原
watch([query, datasetId, modelId, isDatasetManuallySelected], ([q, d, m, manual]) => {
  setSessionCache({ query: q, datasetId: manual ? d : null, modelId: m })
}, { flush: 'post' })

onDeactivated(() => {
  // keep-alive 停用时的轻量清理（不销毁组件状态）
  if (chatScrollTimer) clearTimeout(chatScrollTimer)
  if (panelScrollTimer) clearTimeout(panelScrollTimer)
  clearReportTopScrollTimers()
})

onUnmounted(() => {
  window.removeEventListener('smartask-create-fresh-chat', handleExternalFreshChat)
  stopTimer()
  if (chatScrollTimer) clearTimeout(chatScrollTimer)
  if (panelScrollTimer) clearTimeout(panelScrollTimer)
  clearReportTopScrollTimers()
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
  background: #F4F5F7;
  overflow: hidden;
  font-family: var(--font-sans, 'Microsoft YaHei UI', 'Microsoft YaHei', 'PingFang SC', sans-serif);
  font-size: 14px;
  color: var(--text-title);
  padding: 14px;
  box-sizing: border-box;
  --sa-content-width: 960px;
  --sa-content-gutter: 24px;
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
  gap: 0;
  border: 1px solid rgba(17, 24, 39, 0.06);
  border-radius: 24px;
  background: #FFFFFF;
  box-shadow: 0 18px 46px rgba(15, 23, 42, 0.055);
  backdrop-filter: none;
}

.sa-workspace.is-detail-hidden {
  max-width: min(1560px, 100%);
  width: 100%;
  margin: 0 auto;
}

/* ===== 对话区 ===== */
.sa-chat-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #FFFFFF;
  border-radius: 24px 0 0 24px;
}

.sa-chat-panel.is-detail-hidden {
  max-width: none;
  width: 100%;
  margin: 0 auto;
  border-radius: 24px;
}

.sa-content-track {
  width: min(100% - calc(var(--sa-content-gutter) * 2), var(--sa-content-width));
  max-width: var(--sa-content-width);
  margin-left: auto;
  margin-right: auto;
  box-sizing: border-box;
}

.sa-header-track {
  flex: 0 0 auto;
}

.sa-header-track :deep(.sa-header) {
  width: 100%;
  padding-left: 0;
  padding-right: 0;
}

.sa-chat-content {
  flex: 1 0 auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sa-composer-track {
  flex: 0 0 auto;
}

/* 只读视图提示条 */
.sa-readonly-banner {
  flex: 0 0 auto;
  padding: 12px 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13.5px;
  line-height: 1.5;
  cursor: pointer;
  margin: 0 20px 12px;
  border-radius: 10px;
  transition: all 0.2s ease;
}

.sa-readonly-banner:hover {
  transform: translateY(-1px);
}

.sa-readonly-banner.banner-running {
  background: linear-gradient(90deg, rgba(230, 31, 36, 0.06) 0%, rgba(230, 31, 36, 0.02) 100%);
  border-left: 4px solid #E61F24;
  color: #C41E24;
  box-shadow: 0 3px 10px rgba(230, 31, 36, 0.08);
}

.sa-readonly-banner.banner-running:hover {
  background: linear-gradient(90deg, rgba(230, 31, 36, 0.1) 0%, rgba(230, 31, 36, 0.04) 100%);
  box-shadow: 0 4px 14px rgba(230, 31, 36, 0.14);
}

.sa-readonly-banner.banner-completed {
  background: linear-gradient(90deg, rgba(82, 196, 26, 0.06) 0%, rgba(82, 196, 26, 0.02) 100%);
  border-left: 4px solid #52c41a;
  color: #389e0d;
  box-shadow: 0 3px 10px rgba(82, 196, 26, 0.08);
}

.sa-readonly-banner.banner-completed:hover {
  background: linear-gradient(90deg, rgba(82, 196, 26, 0.1) 0%, rgba(82, 196, 26, 0.04) 100%);
  box-shadow: 0 4px 14px rgba(82, 196, 26, 0.14);
}

.sa-readonly-banner.banner-pending_confirmation {
  background: linear-gradient(90deg, rgba(250, 173, 20, 0.06) 0%, rgba(250, 173, 20, 0.02) 100%);
  border-left: 4px solid #faad14;
  color: #d48806;
  box-shadow: 0 3px 10px rgba(250, 173, 20, 0.08);
}

.sa-readonly-banner.banner-pending_confirmation:hover {
  background: linear-gradient(90deg, rgba(250, 173, 20, 0.1) 0%, rgba(250, 173, 20, 0.04) 100%);
  box-shadow: 0 4px 14px rgba(250, 173, 20, 0.14);
}

.sa-readonly-banner.banner-failed {
  background: linear-gradient(90deg, rgba(255, 77, 79, 0.06) 0%, rgba(255, 77, 79, 0.02) 100%);
  border-left: 4px solid #ff4d4f;
  color: #cf1322;
  box-shadow: 0 3px 10px rgba(255, 77, 79, 0.08);
}

.sa-readonly-banner.banner-failed:hover {
  background: linear-gradient(90deg, rgba(255, 77, 79, 0.1) 0%, rgba(255, 77, 79, 0.04) 100%);
  box-shadow: 0 4px 14px rgba(255, 77, 79, 0.14);
}

.sa-spin-ring-small {
  position: relative;
  width: 16px;
  height: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.sa-spin-ring-track-small {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid currentColor;
  opacity: 0.25;
}
.sa-spin-ring-bar-small {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid transparent;
  border-top-color: currentColor;
  animation: sa-ring-spin-small 0.8s linear infinite;
}
@keyframes sa-ring-spin-small {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.sa-readonly-banner-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.sa-readonly-banner-text {
  flex: 1;
  line-height: 1.4;
}

/* 聊天区 */
.sa-chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 0 0 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #FFFFFF;
}

.sa-chat-panel.is-detail-hidden .sa-chat-body {
  padding-left: 0;
  padding-right: 0;
}

/* 消息 */
.sa-msg-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}
.sa-msg-wrap {
  animation: sa-fadein 0.3s ease-out;
  width: 100%;
  max-width: var(--sa-content-width);
}

.sa-chat-panel.is-detail-hidden .sa-msg-list {
  width: 100%;
  align-items: stretch;
}

.sa-chat-panel.is-detail-hidden .sa-msg-wrap {
  width: 100%;
  max-width: var(--sa-content-width);
}

.sa-chat-panel :deep(.sa-composer) {
  width: 100%;
  max-width: none;
  margin: 0 0 14px;
}

.sa-chat-panel.is-detail-hidden :deep(.sa-side-dataset-card),
.sa-chat-panel.is-detail-hidden :deep(.sa-textarea-wrap) {
  min-height: 88px;
}

.sa-chat-panel.is-detail-hidden :deep(.sa-side-dataset-label) {
  font-size: 15px;
}

.sa-chat-panel.is-detail-hidden :deep(.sa-textarea) {
  font-size: 14px;
}

.sa-chat-panel.is-detail-hidden :deep(.sa-textarea::placeholder) {
  font-size: 14px;
}
@keyframes sa-fadein {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

/* AI回复包装 */
.sa-ai-wrap {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin: 20px 0;
}
.sa-ai-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}
.sa-ai-avatar {
  width: 40px;
  height: 40px;
  position: relative;
  overflow: visible;
  background: transparent;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 0;
  box-shadow: none;
  padding: 0;
}

.sa-ai-avatar::before {
  content: none;
}

.sa-ai-avatar::after {
  content: '';
  position: absolute;
  right: 1px;
  bottom: 1px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #10B981;
  box-shadow:
    0 0 0 3px #FFFFFF,
    0 4px 9px rgba(16, 185, 129, 0.18);
}

.sa-ai-avatar-img {
  display: none;
}

.sa-ai-avatar-svg {
  width: 40px;
  height: 40px;
  display: block;
}
.sa-ai-name {
  font-size: 14.5px;
  font-weight: 700;
  color: #1E293B;
  letter-spacing: 0.2px;
}
.sa-ai-cards {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-left: 52px;
  max-width: 900px;
}

.sa-chat-panel.is-detail-hidden .sa-ai-cards {
  max-width: 880px;
}

/* 通用卡片样式优化 */
.sa-card {
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  box-shadow: 
    0 1px 3px rgba(15, 23, 42, 0.04),
    0 4px 12px rgba(15, 23, 42, 0.03);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.sa-card:hover {
  box-shadow: 
    0 2px 6px rgba(15, 23, 42, 0.05),
    0 8px 20px rgba(15, 23, 42, 0.06);
}

.sa-result-chain {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  padding-top: 14px;
  margin-top: 1px;
  border-top: 1px dashed rgba(17, 24, 39, 0.1);
  animation: sa-curtain-open 0.32s cubic-bezier(0.4, 0, 0.2, 1);
  transform-origin: top center;
}

.sa-result-chain > * {
  width: 100%;
}

.sa-result-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  max-width: 720px;
  padding: 30px 24px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92) 0%, rgba(248, 249, 250, 0.88) 100%);
  border: 1px dashed rgba(17, 24, 39, 0.1);
  box-shadow: 0 16px 28px rgba(15, 23, 42, 0.04);
  text-align: center;
}

.sa-result-empty-icon {
  font-size: 32px;
  line-height: 1;
  opacity: 0.85;
}

.sa-result-empty-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-title, #111827);
}

.sa-result-empty-desc {
  font-size: 13px;
  line-height: 1.75;
  color: var(--text-secondary, #6B7280);
  max-width: 520px;
}

.sa-chat-panel.is-detail-hidden .sa-result-chain,
.sa-chat-panel.is-detail-hidden .sa-inline-visuals,
.sa-chat-panel.is-detail-hidden .sa-flow-handoff,
.sa-chat-panel.is-detail-hidden .sa-confirm-card {
  max-width: 880px;
}

.sa-inline-visuals {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  max-width: 980px;
  padding: 14px;
  border-radius: 14px;
  border: 1px solid rgba(230, 31, 36, 0.1);
  background: linear-gradient(180deg, #FEF2F2 0%, #ffffff 100%);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.035);
}

.sa-inline-visuals.is-single {
  width: min(100%, 980px);
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
  color: #E61F24;
}

.sa-inline-visuals-title {
  margin-top: 5px;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.sa-inline-visuals-caption {
  margin-top: 4px;
  font-size: 11px;
  line-height: 1.65;
  color: #9CA3AF;
}

.sa-inline-visuals-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.sa-inline-visuals-grid.is-single {
  grid-template-columns: minmax(0, 1fr);
  justify-content: start;
}

.sa-inline-visual-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
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
  color: #111827;
  line-height: 1.5;
}

.sa-inline-visual-card-subtitle {
  margin-top: 3px;
  font-size: 11px;
  color: #9CA3AF;
}

.sa-inline-visual-chart {
  height: 320px;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.sa-inline-visuals-grid.is-single .sa-inline-visual-chart {
  height: 360px;
}

/* 加载动画 */
.sa-thinking-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  background: #FFFFFF;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 14px;
  width: fit-content;
  min-width: 320px;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.04);
}
.sa-dots {
  display: flex;
  gap: 4px;
}
.sa-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #1A1A1A;
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
  color: #6B7280;
}

/* 确认区 */
.sa-flow-handoff {
  width: 100%;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: linear-gradient(180deg, #F8F9FA 0%, #ffffff 100%);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.035);
}

.sa-flow-handoff-kicker {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #1A1A1A;
}

.sa-flow-handoff-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.sa-flow-badge {
  flex: none;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid rgba(26, 26, 26, 0.12);
  background: #F3F4F6;
  color: #1A1A1A;
}

.sa-flow-badge.is-advanced {
  border-color: rgba(16, 185, 129, 0.22);
  background: #ecfdf5;
  color: #10B981;
}

.sa-flow-handoff-title {
  margin-top: 5px;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.55;
  color: #111827;
}

.sa-flow-handoff-desc {
  margin-top: 5px;
  font-size: 12px;
  line-height: 1.65;
  color: #6B7280;
}

.sa-confirm-card {
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 12px;
  background: #fff;
  width: 100%;
  padding: 12px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.04);
}
.sa-confirm-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.sa-confirm-badge {
  flex: 0 0 auto;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  background: #FFFBEB;
  color: #F59E0B;
}
.sa-confirm-q {
  flex: 1 1 auto;
  font-size: 13px;
  color: var(--text-title);
  line-height: 1.5;
}
.sa-confirm-opts {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.sa-confirm-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.sa-confirm-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 48px;
  text-align: left;
  padding: 7px 10px;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  color: #111827;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.12s;
}
.sa-confirm-row:hover {
  background: #F3F4F6;
  border-color: rgba(26, 26, 26, 0.2);
}
.sa-confirm-row-top {
  border-color: rgba(26, 26, 26, 0.24);
  background: #F3F4F6;
  font-weight: 600;
}
.sa-confirm-row-top .sa-confirm-rank {
  background: #1A1A1A;
  color: #fff;
}
.sa-confirm-row-top .sa-confirm-score {
  background: rgba(26, 26, 26, 0.1);
  color: #1A1A1A;
  font-weight: 700;
}
.sa-confirm-rank {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 5px;
  background: rgba(26, 26, 26, 0.06);
  color: #1A1A1A;
  font-size: 10px;
  font-weight: 700;
}
.sa-confirm-info {
  flex: 0 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.sa-confirm-row-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}
.sa-confirm-row-desc {
  font-size: 11px;
  line-height: 1.4;
  color: #9CA3AF;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sa-confirm-recommended {
  flex: 0 0 auto;
  padding: 1px 5px;
  border-radius: 4px;
  background: #E61F24;
  color: #fff;
  font-size: 10px;
  font-weight: 600;
}
.sa-confirm-spacer {
  flex: 1 0 auto;
}
.sa-confirm-score {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 48px;
  height: 20px;
  padding: 0 7px;
  border-radius: 999px;
  background: rgba(26, 26, 26, 0.06);
  color: #1A1A1A;
  font-size: 11px;
  font-weight: 600;
}
.sa-confirm-toggle {
  margin-top: 4px;
  width: 100%;
  height: 32px;
  border-radius: 8px;
  border: 1px dashed rgba(26, 26, 26, 0.2);
  background: #fff;
  color: #1A1A1A;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.sa-confirm-toggle:hover {
  background: #F3F4F6;
}

.sa-confirm-freeform {
  margin-top: 10px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.sa-confirm-textarea {
  flex: 1 1 auto;
  min-width: 0;
  min-height: 36px;
  height: 36px;
  resize: none;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: #fff;
  font-size: 12px;
  line-height: 1.5;
  color: #111827;
  outline: none;
  box-sizing: border-box;
}

.sa-confirm-textarea:focus {
  border-color: rgba(26, 26, 26, 0.35);
  box-shadow: 0 0 0 2px rgba(26, 26, 26, 0.06);
}

.sa-confirm-textarea::placeholder {
  color: #9CA3AF;
}

.sa-confirm-send {
  flex: 0 0 auto;
  height: 36px;
  padding: 0 14px;
  border-radius: 8px;
  border: none;
  background: #E61F24;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.sa-confirm-send:disabled,
.sa-confirm-row:disabled,
.sa-confirm-toggle:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.sa-confirm-submitted {
  max-width: 760px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: linear-gradient(180deg, #F8F9FA 0%, #ffffff 100%);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.035);
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
  background: #E61F24;
  box-shadow: 0 0 0 5px rgba(230, 31, 36, 0.08);
}

.sa-confirm-submitted-title {
  font-size: 13px;
  font-weight: 700;
  color: #E61F24;
}

.sa-confirm-submitted-desc {
  font-size: 12px;
  line-height: 1.65;
  color: #6B7280;
}

/* 状态提示区 */
.sa-error-card,
.sa-cancel-card {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 12px 16px;
  border-radius: 14px;
  max-width: 760px;
}

.sa-error-card {
  background: #FEF2F2;
  border: 1px solid #FEF2F2;
  color: var(--error);
}

.sa-cancel-card {
  align-items: flex-start;
  position: relative;
  overflow: hidden;
  gap: 12px;
  padding: 14px 16px;
  background:
    linear-gradient(90deg, rgba(0, 0, 0, 0.035) 1px, transparent 1px),
    linear-gradient(180deg, rgba(0, 0, 0, 0.035) 1px, transparent 1px),
    radial-gradient(circle at 12% 18%, rgba(230, 31, 36, 0.16), transparent 30%),
    linear-gradient(135deg, #F8F9FA 0%, #FEF2F2 54%, #FEF2F2 100%);
  background-size: 18px 18px, 18px 18px, auto, auto;
  border: 1px solid rgba(230, 31, 36, 0.22);
  color: #111827;
  box-shadow:
    0 12px 28px rgba(230, 31, 36, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.84);
}

.sa-cancel-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  border-left: 3px solid #E61F24;
  pointer-events: none;
}

.sa-cancel-card::after {
  content: '';
  position: absolute;
  right: 14px;
  top: 13px;
  width: 58px;
  height: 16px;
  border-top: 1px solid rgba(230, 31, 36, 0.2);
  border-right: 1px solid rgba(230, 31, 36, 0.42);
  transform: skewX(-24deg);
  pointer-events: none;
}

.sa-cancel-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  position: relative;
  margin-top: 2px;
  border-radius: 50%;
  background:
    radial-gradient(circle, rgba(255, 255, 255, 0.96) 0 30%, transparent 31%),
    conic-gradient(from 210deg, rgba(230, 31, 36, 0.18), rgba(230, 31, 36, 0.85), rgba(230, 31, 36, 0.18));
  box-shadow:
    0 0 0 4px rgba(230, 31, 36, 0.06),
    0 0 18px rgba(230, 31, 36, 0.28);
  flex: 0 0 auto;
}

.sa-cancel-icon::before,
.sa-cancel-icon::after {
  content: '';
  position: absolute;
  background: #E61F24;
  border-radius: 999px;
}

.sa-cancel-icon::before {
  width: 14px;
  height: 2px;
  transform: rotate(45deg);
}

.sa-cancel-icon::after {
  width: 14px;
  height: 2px;
  transform: rotate(-45deg);
}

.sa-cancel-icon-core {
  position: absolute;
  inset: 7px;
  border-radius: 50%;
  border: 1px solid rgba(230, 31, 36, 0.28);
}

.sa-cancel-copy {
  position: relative;
  z-index: 1;
  min-width: 0;
}

.sa-cancel-kicker {
  margin-bottom: 3px;
  color: #E61F24;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.sa-cancel-title {
  font-size: 14px;
  font-weight: 780;
  color: #111827;
}

.sa-cancel-desc {
  margin-top: 3px;
  font-size: 12px;
  line-height: 1.6;
  color: #6B7280;
}

.sa-link-btn {
  background: none;
  border: none;
  color: #1A1A1A;
  cursor: pointer;
  font-size: 12px;
  padding: 4px 5px;
}

.sa-link-btn:hover {
  text-decoration: underline;
}

.sa-link-btn.danger {
  color: #E61F24;
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
  border-left: 1px solid rgba(17, 24, 39, 0.07);
  background: #FFFFFF;
  box-shadow: none;
  flex-shrink: 0;
}
.sa-panel-header {
  padding: 28px 28px 24px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid rgba(17, 24, 39, 0.07);
  background: #FFFFFF;
  flex-shrink: 0;
}
.sa-panel-heading {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
.sa-panel-eyebrow {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: none;
  color: #E61F24;
}
.sa-panel-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.sa-panel-title {
  font-size: 21px;
  font-weight: 800;
  color: #111827;
}
.sa-panel-state {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  background: rgba(17, 24, 39, 0.06);
  color: #6B7280;
  box-shadow: inset 0 0 0 1px rgba(17, 24, 39, 0.05);
}
.sa-panel-state.running {
  background: rgba(17, 24, 39, 0.88);
  color: rgba(255, 255, 255, 0.96);
}
.sa-panel-state.completed {
  background: rgba(16, 185, 129, 0.12);
  color: #059669;
}
.sa-panel-state.canceled {
  background: rgba(245, 158, 11, 0.12);
  color: #B45309;
}
.sa-panel-state.error {
  background: rgba(230, 31, 36, 0.1);
  color: #E61F24;
}
.sa-panel-state.waiting_confirmation {
  background: rgba(245, 158, 11, 0.12);
  color: #F59E0B;
}
.sa-panel-desc {
  margin: 0;
  font-size: 14px;
  line-height: 1.65;
  color: #7B8491;
  max-width: 360px;
}
.sa-panel-close {
  width: 38px;
  height: 38px;
  border-radius: 14px;
  border: 1px solid rgba(17, 24, 39, 0.06);
  background: rgba(255, 255, 255, 0.92);
  cursor: pointer;
  color: var(--text-muted);
  font-size: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: none;
}

.sa-panel-close:hover {
  color: #1A1A1A;
  border-color: rgba(230, 31, 36, 0.14);
  background: rgba(255, 255, 255, 1);
}
.sa-panel-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 6px 0 14px;
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
  gap: 10px;
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
  color: #111827;
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
  background: rgba(255, 255, 255, 0.88);
  color: #6B7280;
  font-size: 10px;
  font-weight: 600;
  box-shadow: inset 0 0 0 1px rgba(17, 24, 39, 0.06);
}
.sa-kpi-card {
  flex: 1;
  min-width: 120px;
  border: 1px solid rgba(17, 24, 39, 0.08);
  border-radius: 16px;
  padding: 14px;
  text-align: center;
  background: linear-gradient(180deg, rgba(255, 255, 255, 1) 0%, rgba(251, 252, 253, 0.96) 100%);
  box-shadow:
    0 14px 24px rgba(15, 23, 42, 0.035),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
}

.sa-kpi-card.is-explained {
  min-height: 92px;
  padding: 14px 16px;
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
  color: #10B981;
}

.sa-kpi-card.is-tone-warn .sa-kpi-value {
  color: #F59E0B;
}

.sa-kpi-card.is-tone-danger .sa-kpi-value {
  color: #E61F24;
}

.sa-kpi-value {
  font-size: 22px;
  font-weight: 800;
  color: rgba(17, 24, 39, 0.92);
  line-height: 1.2;
}
.sa-kpi-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 6px;
}

.sa-kpi-hint {
  margin-top: 8px;
  color: #6B7280;
  font-size: 11px;
  line-height: 1.55;
}
.sa-main-chart {
  height: 208px;
  border-radius: 16px;
  overflow: hidden;
  background: #fff;
  border: 1px solid rgba(17, 24, 39, 0.08);
}
.sa-insight-metric {
  min-height: 164px;
  border-radius: 16px;
  border: 1px solid rgba(17, 24, 39, 0.08);
  background: linear-gradient(180deg, #FFFFFF 0%, #F8F9FA 100%);
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
  font-weight: 800;
  color: rgba(17, 24, 39, 0.92);
}
.sa-insight-metric-label {
  margin-top: 7px;
  font-size: 12px;
  color: #6B7280;
}
.sa-preview-table {
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(17, 24, 39, 0.06);
}
.sa-report-md {
  font-size: 13px;
  line-height: 1.72;
  color: var(--text-title);
}
.sa-report-md :deep(h1),
.sa-report-md :deep(h2) {
  color: #111827;
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
  background: rgba(17, 24, 39, 0.9);
  color: #fff;
  border: 1px solid rgba(17, 24, 39, 0.14);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow:
    0 10px 18px rgba(15, 23, 42, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.14);
}
.sa-primary-btn:hover {
  transform: translateY(-1px) scale(1.01);
  box-shadow:
    0 12px 22px rgba(15, 23, 42, 0.14),
    inset 0 1px 0 rgba(255, 255, 255, 0.18);
}

.sa-primary-btn:active {
  transform: scale(0.94);
}

.sa-secondary-btn,
.sa-ghost-btn {
  height: 34px;
  padding: 0 15px;
  border-radius: 999px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: rgba(255, 255, 255, 0.92);
  color: #6B7280;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
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
  border-color: rgba(26, 26, 26, 0.14);
  background: rgba(243, 244, 246, 0.92);
  color: #1A1A1A;
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.05);
}

.sa-secondary-btn:active,
.sa-ghost-btn:active,
.sa-panel-close:active,
.sa-link-btn:active,
.sa-confirm-row:active {
  transform: scale(0.985);
}

.sa-side-report {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 0 14px 14px;
  padding: 14px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 14px;
  background: linear-gradient(180deg, #F8F9FA 0%, #ffffff 100%);
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
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #ffffff;
  color: #6B7280;
}

.sa-side-confidence-chip.is-success {
  background: #ECFDF5;
  border-color: rgba(16, 185, 129, 0.16);
  color: #10B981;
}

.sa-side-confidence-chip.is-info {
  background: #F3F4F6;
  border-color: rgba(26, 26, 26, 0.1);
  color: #1A1A1A;
}

.sa-side-confidence-chip.is-warning {
  background: #FFFBEB;
  border-color: rgba(245, 158, 11, 0.16);
  color: #F59E0B;
}

.sa-route-decision {
  margin-top: 4px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #F8F9FA;
  color: #6B7280;
  font-size: 12px;
  line-height: 1.6;
}

.sa-route-review-note {
  margin: 0;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(26, 26, 26, 0.04);
  color: #6B7280;
  font-size: 12px;
  line-height: 1.55;
}

.sa-side-report-kicker {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #1A1A1A;
}

.sa-side-report-title {
  margin: 0;
  font-size: 16px;
  line-height: 1.4;
  color: #111827;
}

.sa-side-report-desc {
  margin: 0;
  font-size: 12px;
  line-height: 1.65;
  color: #6B7280;
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
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #F8F9FA 100%);
}

.sa-management-narrative.is-single-focus .sa-management-narrative-card {
  border-radius: 8px;
  background: #ffffff;
}

.sa-management-narrative-title {
  margin-bottom: 8px;
  color: #111827;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.35;
}

.sa-management-narrative.is-single-focus .sa-management-narrative-title {
  font-size: 14px;
}

.sa-management-narrative-body {
  color: #374151;
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
  color: #111827;
}

.sa-filter-answer-card {
  padding: 14px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 10px;
  background: linear-gradient(180deg, #F8F9FA, rgba(255, 255, 255, 0.96));
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.04);
}

.sa-filter-answer-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.sa-filter-answer-list {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.sa-filter-answer-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 38px;
  padding: 8px 10px;
  border: 1px solid rgba(0, 0, 0, 0.22);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.82);
  color: #111827;
  text-align: left;
  cursor: pointer;
}

.sa-filter-answer-row:hover {
  border-color: rgba(26, 26, 26, 0.2);
  background: #fff;
}

.sa-filter-answer-name {
  min-width: 0;
  overflow: hidden;
  font-size: 13px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sa-filter-answer-metric {
  color: #1A1A1A;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
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
  color: #10B981;
  background: #ECFDF5;
}

.sa-business-risk-pill.warn,
.sa-office-rate.warn {
  color: #F59E0B;
  background: #FFFBEB;
}

.sa-business-risk-pill.danger,
.sa-office-rate.danger {
  color: #E61F24;
  background: #FEF2F2;
}

.sa-business-risk-pill.neutral,
.sa-office-rate.neutral {
  color: #6B7280;
  background: #F3F4F6;
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
  color: #6B7280;
  font-size: 11px;
  font-weight: 700;
}

.sa-kpi-shelf-compact .sa-kpi-card {
  min-width: calc(50% - 4px);
  padding: 10px;
}

.sa-office-overview-card {
  padding: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
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
  border: 1px solid var(--office-accent-border, rgba(0, 0, 0, 0.08));
  border-radius: 12px;
  background: #ffffff;
  overflow: hidden;
}

.sa-office-card-dialog {
  border-radius: 14px;
  border-color: var(--office-accent-border, rgba(0, 0, 0, 0.08));
}

.sa-office-card-head {
  width: 100%;
  min-height: 58px;
  border: none;
  background: #FFFFFF;
  padding: 12px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  text-align: left;
  cursor: pointer;
}

.sa-office-card .sa-office-card-head {
  background: linear-gradient(90deg, var(--office-accent-soft, #FFFFFF) 0%, #FFFFFF 72%);
  border-left: 4px solid var(--office-accent, transparent);
}

.sa-office-card-dialog .sa-office-card-head {
  background: linear-gradient(90deg, var(--office-accent-soft, #FFFFFF) 0%, #FFFFFF 72%);
  border-left: 4px solid var(--office-accent, transparent);
}

.sa-office-card-head:hover {
  background: #F8F9FA;
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

.sa-office-leaf-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: rgba(255, 255, 255, 0.92);
  color: #111827;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
}

.sa-office-drill-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 48px;
  min-height: 24px;
  padding: 0 8px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.62);
  color: #6B7280;
  line-height: 1;
  opacity: 0.82;
  transition: border-color 0.18s ease, color 0.18s ease, background 0.18s ease, opacity 0.18s ease;
}

.sa-office-card-head:hover .sa-office-drill-toggle,
.sa-rep-drill-head:hover .sa-office-drill-toggle,
.sa-office-drill-toggle.is-open {
  border-color: var(--office-accent-border, rgba(230, 31, 36, 0.18));
  background: #ffffff;
  color: var(--office-accent, #E61F24);
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
  background: var(--office-accent-soft, #F8F9FA);
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
  background: linear-gradient(90deg, var(--office-accent-soft, #F8F9FA) 0%, #F8F9FA 72%);
}

.sa-office-card-dialog .sa-office-card-head:hover {
  background: linear-gradient(90deg, var(--office-accent-soft, #F8F9FA) 0%, #F8F9FA 72%);
}

.sa-office-name {
  font-size: 14px;
  line-height: 1.4;
  font-weight: 700;
  color: #111827;
}

.sa-office-subtitle {
  margin-top: 4px;
  font-size: 11px;
  line-height: 1.45;
  color: #9CA3AF;
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
  background: #F8F9FA;
  color: #6B7280;
  font-size: 11px;
  line-height: 1.45;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sa-office-copy,
.sa-chart-copy {
  margin: 0;
  color: #6B7280;
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
  border-top: 1px dashed rgba(0, 0, 0, 0.1);
}

.sa-office-drill::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 13px;
  bottom: 4px;
  width: 3px;
  border-radius: 999px;
  background: var(--office-accent-soft, rgba(230, 31, 36, 0.12));
  border: 1px solid var(--office-accent-border, rgba(230, 31, 36, 0.16));
}

.sa-drill-path {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: var(--office-accent-soft, #F8F9FA);
  color: #6B7280;
  font-size: 12px;
  font-weight: 700;
}

.sa-drill-path i {
  width: 18px;
  height: 1px;
  background: var(--office-accent, #E61F24);
  position: relative;
}

.sa-drill-path i::after {
  content: '';
  position: absolute;
  right: -1px;
  top: -3px;
  width: 6px;
  height: 6px;
  border-top: 1px solid var(--office-accent, #E61F24);
  border-right: 1px solid var(--office-accent, #E61F24);
  transform: rotate(45deg);
}

.sa-drill-path strong {
  color: var(--office-accent, #E61F24);
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
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #ffffff;
}

.sa-drill-insight-card span {
  display: block;
  margin-bottom: 4px;
  color: #9CA3AF;
  font-size: 11px;
  font-weight: 700;
}

.sa-drill-insight-card strong {
  display: block;
  color: #111827;
  font-size: 13px;
  line-height: 1.35;
}

.sa-drill-insight-card.is-good {
  border-color: rgba(16, 185, 129, 0.16);
  background: #ECFDF5;
}

.sa-drill-insight-card.is-risk {
  border-color: rgba(230, 31, 36, 0.14);
  background: #FEF2F2;
}

.sa-chart-copy-drill {
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #FFFFFF;
}

.sa-drill-table-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: -4px;
  color: #111827;
}

.sa-drill-table-head span {
  font-size: 13px;
  font-weight: 800;
}

.sa-drill-table-head small {
  color: #9CA3AF;
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
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #fff;
}

.sa-office-empty-drill {
  margin-top: 8px;
  padding: 14px;
  border: 1px dashed rgba(230, 31, 36, 0.28);
  border-radius: 12px;
  background: linear-gradient(180deg, #F8F9FA 0%, #ffffff 100%);
  color: #6B7280;
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
  border: 1px solid rgba(0, 0, 0, 0.08);
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
  color: #374151;
  font-size: 11px;
  line-height: 1.35;
}

.sa-office-detail-row:nth-child(odd):not(.is-head) {
  background: #F8F9FA;
}

.sa-office-detail-row.is-head {
  min-height: 32px;
  color: #9CA3AF;
  background: #F8F9FA;
  font-weight: 700;
}

.sa-detail-name {
  color: #111827;
  font-weight: 700;
}

.sa-detail-rate,
.sa-detail-tag {
  font-weight: 700;
}

.sa-detail-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 22px;
  width: fit-content;
  max-width: 100%;
  padding: 0 8px;
  border-radius: 999px;
  background: #F3F4F6;
  line-height: 1;
}

.sa-detail-progress {
  min-width: 0;
}

.sa-detail-rate.good,
.sa-detail-tag.good {
  color: #10B981;
  background: #ECFDF5;
}

.sa-detail-rate.warn,
.sa-detail-tag.warn {
  color: #F59E0B;
  background: #FFFBEB;
}

.sa-detail-rate.danger,
.sa-detail-tag.danger {
  color: #E61F24;
  background: #FEF2F2;
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
  color: #6B7280;
  font-size: 11px;
  line-height: 1.35;
}

.sa-office-bar-row span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sa-office-bar-row strong {
  color: #111827;
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
  background: #F3F4F6;
}

.sa-office-bar-track i,
.sa-office-bar-track b {
  position: absolute;
  inset: 0 auto 0 0;
  min-width: 2px;
  border-radius: inherit;
}

.sa-office-bar-track .is-rate.good {
  background: #10B981;
}

.sa-office-bar-track .is-rate.warn {
  background: #F59E0B;
}

.sa-office-bar-track .is-rate.danger {
  background: #E61F24;
}

.sa-office-bar-track .is-gap {
  background: #F59E0B;
}

.sa-compare-matrix {
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.08);
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
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  background: transparent;
  color: #374151;
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
  background: linear-gradient(90deg, var(--office-accent-soft, #F8F9FA) 0%, #F8F9FA 70%);
}

.sa-compare-row.is-head {
  min-height: 36px;
  color: #9CA3AF;
  background: #F8F9FA;
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

.sa-compare-row .sa-office-bar-track .is-rate {
  background: var(--office-accent);
}

.sa-rep-drill-list {
  grid-column: 1 / -1;
  display: grid;
  gap: 8px;
  margin-top: 2px;
  padding-top: 10px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

.sa-rep-drill-list.is-dialog {
  margin-top: 4px;
}

.sa-rep-drill-title {
  color: #6B7280;
  font-size: 12px;
  font-weight: 700;
}

.sa-rep-drill-card {
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  background: #FFFFFF;
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
  background: rgba(26, 26, 26, 0.04);
}

.sa-rep-drill-name {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #111827;
  font-size: 13px;
  font-weight: 800;
}

.sa-rep-drill-subtitle {
  margin-top: 2px;
  color: #9CA3AF;
  font-size: 11px;
}

.sa-rep-drill-summary {
  margin: 0;
  padding: 0 10px 9px;
  color: #6B7280;
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
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.sa-side-section-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #9CA3AF;
}

/* 内嵌图表 */
.sa-chart-embed {
  height: 188px;
  margin: 6px 0;
  border-radius: 6px;
  overflow: hidden;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.08);
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
  background: #F8F9FA;
  color: #6B7280;
  font-size: 11px;
  font-weight: 600;
  height: 34px;
  text-align: left;
}

.sa-mini-table :deep(.el-table__body-wrapper td) {
  font-size: 11px;
  color: #111827;
  text-align: left;
}

.sa-mini-table :deep(.el-table__row:nth-child(even) td) {
  background: #F8F9FA;
}

.sa-mini-table :deep(.el-table__inner-wrapper::before) {
  display: none;
}

.sa-preview :deep(.el-table__header-wrapper th) {
  background: #F8F9FA;
  color: #6B7280;
  font-size: 11px;
  font-weight: 600;
  height: 34px;
  text-align: left;
}

.sa-preview :deep(.el-table__body-wrapper td) {
  font-size: 11px;
  color: #111827;
  text-align: left;
}

.sa-preview :deep(.el-table__row:nth-child(even) td) {
  background: #F8F9FA;
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
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #FFFFFF;
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
  color: #111827;
}

.sa-side-extra-chart-action {
  height: 26px;
  padding: 0 10px;
  font-size: 11px;
}

.sa-side-extra-chart-canvas {
  width: 100%;
  height: 280px;
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
  background: #F8F9FA;
  color: var(--text-muted);
  font-size: 12px;
  margin-top: 8px;
}

.sa-log-time-label {
  color: #6B7280;
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
  color: #9CA3AF;
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
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #FFFFFF;
  font-size: 12px;
  line-height: 1.8;
  color: #111827;
}

.sa-log-markdown :deep(h1),
.sa-log-markdown :deep(h2),
.sa-log-markdown :deep(h3) {
  margin: 0 0 8px;
  color: #111827;
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
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
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
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sa-report-dialog-subtitle {
  margin: 7px 0 0;
  max-width: min(980px, 72vw);
  color: #6B7280;
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
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.sa-report-stage-summary {
  background: linear-gradient(180deg, #ffffff 0%, #FFFFFF 100%);
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
  color: #111827;
}

.sa-report-core-conclusion {
  display: grid;
  gap: 5px;
  margin: 0 0 12px;
  padding: 12px 14px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  background: linear-gradient(180deg, #F8F9FA 0%, #ffffff 100%);
}

.sa-report-core-conclusion span {
  color: #1A1A1A;
  font-size: 12px;
  font-weight: 800;
}

.sa-report-core-conclusion strong {
  color: #111827;
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
  color: #111827;
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
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #FFFFFF;
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
  color: #111827;
}

.sa-report-chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.sa-report-chart-card {
  padding: 14px 14px 12px;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #ffffff;
  box-shadow: 0 8px 22px rgba(0, 0, 0, 0.06);
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
  color: #111827;
}

.sa-report-chart-subtitle {
  margin-top: 3px;
  font-size: 12px;
  color: #9CA3AF;
}

.sa-report-chart-canvas {
  width: 100%;
  height: 340px;
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
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #FFFFFF;
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
  color: #111827;
}

.sa-report-table-desc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.7;
  color: #9CA3AF;
}

.sa-preview-table-report {
  margin-top: 2px;
}

.sa-preview-table-report :deep(.el-table__header-wrapper th) {
  background: #F8F9FA;
  color: #6B7280;
  font-size: 11px;
  font-weight: 600;
  height: 34px;
  text-align: left;
}

.sa-preview-table-report :deep(.el-table__body-wrapper td) {
  font-size: 11px;
  color: #111827;
  text-align: left;
}

.sa-preview-table-report :deep(.el-table__row:nth-child(even) td) {
  background: #F8F9FA;
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
  color: #9CA3AF;
}

.sa-chart-dialog-switch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px;
  border-radius: 999px;
  background: #F3F4F6;
}

.sa-chart-switch-btn {
  border: none;
  background: transparent;
  color: #6B7280;
  font-size: 12px;
  line-height: 1;
  padding: 8px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.sa-chart-switch-btn.is-active {
  background: #ffffff;
  color: #1A1A1A;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.sa-chart-dialog-canvas {
  width: 100%;
  height: 68vh;
  min-height: 420px;
}

.sa-chart-dialog-table {
  border: 1px solid rgba(0, 0, 0, 0.08);
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
  color: #9CA3AF;
  background: #F8F9FA;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.sa-insight-metric-large {
  min-height: 420px;
}

:global(.sa-toast-modern.el-message) {
  min-width: 0;
  width: auto;
  max-width: min(420px, calc(100vw - 32px));
  padding: 9px 13px;
  border: 1px solid rgba(230, 31, 36, 0.12);
  border-radius: 10px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 249, 250, 0.98));
  box-shadow:
    0 10px 28px rgba(0, 0, 0, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(10px);
}

:global(.sa-toast-modern .el-message__content) {
  color: #374151;
  font-size: 12px;
  font-weight: 760;
  line-height: 1.35;
}

:global(.sa-toast-modern .el-message__icon) {
  margin-right: 8px;
  font-size: 14px;
}

:global(.sa-toast-modern.el-message--success) {
  border-color: rgba(16, 185, 129, 0.16);
}

:global(.sa-toast-modern.el-message--success .el-message__icon) {
  color: #10B981;
}

:global(.sa-toast-stop.el-message) {
  border-color: rgba(245, 158, 11, 0.18);
  background:
    linear-gradient(180deg, rgba(255, 251, 235, 0.98), rgba(255, 251, 235, 0.98));
}

:global(.sa-toast-stop .el-message__content) {
  color: #B45309;
}

:global(.sa-toast-stop .el-message__icon) {
  color: #B45309;
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
    padding: 10px;
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
    border-top: 1px solid rgba(0, 0, 0, 0.08);
    min-height: 320px;
    max-height: 42vh;
  }
}
</style>
