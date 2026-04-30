<template>
  <div class="sa-page">
    <div class="sa-shell">
      <section class="sa-workspace" :class="{ 'is-detail-hidden': !showPanel }">
        <!-- 📌 左侧/中间 对话区-->
        <div class="sa-chat-panel" :class="{ 'is-detail-hidden': !showPanel }">
          <!-- 头部组件-->
          <ChatHeader
            :show-panel="showPanel"
            :dataset-name="currentDatasetLabel"
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
              @quick-ask="quickAsk"
            />

            <!-- 消息列表 -->
            <div class="sa-msg-list">
              <div v-for="msg in messages" :key="msg.id" class="sa-msg-wrap">
                <!-- 用户气泡 -->
                <UserBubble v-if="msg.role === 'user'" :content="msg.content" />

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
                      :max-items="msg.loading ? 6 : 4"
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
                      <div class="sa-confirm-opts">
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
                        ></textarea>
                        <div class="sa-confirm-freeform-actions">
                          <span class="sa-confirm-freeform-hint">补充说明会直接作为老板确认内容继续推进问数流程。</span>
                          <button
                            class="sa-confirm-send"
                            :disabled="isRunning || !String(confirmationDrafts[msg.id] || '').trim()"
                            @click="doConfirm(String(confirmationDrafts[msg.id] || '').trim(), msg)"
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
                            <button class="sa-ghost-btn" @click="openChartViewer(preview.chartSpec, `${preview.dataset.dataset_name} 图表预览`)">
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

                    <!-- 最终报告摘要-->
                    <ReportSummary
                      v-if="getReport(msg)"
                      :report="getReport(msg)"
                      :question="msg.data?.question"
                      @download="downloadReportForMessage(msg)"
                      @view="openReportViewerForMessage(msg)"
                    />

                    <ArtifactStrip
                      v-if="getReport(msg)"
                      :title="getResultTitle(msg)"
                      :dataset-name="getPrimaryDataset(msg)?.dataset_name || ''"
                      @download="downloadReportForMessage(msg)"
                      @view-details="openDetailPanel"
                    />

                    <!-- Agent 执行完毕 -->
                    <AgentDoneBar
                      v-if="isMessageExecutionComplete(msg)"
                      :title="getResultTitle(msg)"
                      @view-details="openDetailPanel"
                    />

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
            @send="handleSend"
            @stop="handleStop"
            @dataset-change="loadQuestions"
          />
        </div>

        <!-- ██ 右侧 执行详情面板 -->
        <transition name="sa-panel-slide">
          <aside v-if="showPanel" class="sa-detail-panel">
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
                :logs="session.state.logs"
                :open-state="logOpen"
                @toggle="toggleLog"
              >
                <template #content="{ log, index }">
                  <div v-if="log.sql" class="sa-log-section">
                    <div class="sa-log-section-title">{{ log.sqlTitle || '生成 SQL' }}</div>
                    <SqlBlock :sql="log.sql" />
                  </div>

                  <div v-if="log.chartData" class="sa-log-section">
                    <div class="sa-log-section-title">{{ log.chartTitle || '图表预览' }}</div>
                    <button class="sa-ghost-btn sa-log-inline-action" @click="openChartViewer(log.chartData, log.chartTitle || '图表预览')">放大查看</button>
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

                  <div v-if="log.markdown" class="sa-log-section">
                    <div class="sa-log-section-title">{{ log.kind === 'report-stage' ? '报告内容' : '节点摘要' }}</div>
                    <div class="sa-log-markdown" v-html="renderMd(log.markdown)"></div>
                  </div>

                  <div v-if="log.time" class="sa-log-time">
                    <span class="sa-log-time-label">更新时间</span>
                    <span>{{ log.time }}</span>
                  </div>
                </template>
              </LogTimeline>

              <section v-if="hasSideReport" class="sa-side-report">
                <div class="sa-side-report-head">
                  <span class="sa-side-report-kicker">执行结果汇总</span>
                  <h3 class="sa-side-report-title">{{ sideReportHeading }}</h3>
                  <p class="sa-side-report-desc">汇总当前任务的关键指标、图表预览、结果数据和完整报告内容。</p>
                </div>

                <div
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
                    <button class="sa-ghost-btn" @click="openChartViewer(preview.chartSpec, `${preview.dataset.dataset_name} 图表预览`)">放大查看</button>
                  </div>

                  <div v-if="preview.extraCharts?.length" class="sa-side-extra-charts">
                    <article
                      v-for="(chartSpec, chartIndex) in preview.extraCharts.slice(0, 2)"
                      :key="`${preview.key}-extra-${chartIndex}`"
                      class="sa-side-extra-chart-card"
                    >
                      <div class="sa-side-extra-chart-head">
                        <div class="sa-side-extra-chart-title">{{ chartSpec.title || `图表 ${chartIndex + 1}` }}</div>
                        <button class="sa-ghost-btn sa-side-extra-chart-action" @click="openChartViewer(chartSpec, `${preview.dataset.dataset_name} ${chartSpec.title || `图表 ${chartIndex + 1}`}`)">
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

                <div v-if="latestReport" class="sa-side-section sa-report-view">
                  <div class="sa-side-section-title">完整报告</div>
                  <div class="sa-chart-actions">
                    <button class="sa-ghost-btn" @click="openReportViewer">全屏查看</button>
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
                      <div class="sa-report-md sa-report-md-compact" v-html="renderMd(section.body)"></div>
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
                  <div v-if="!reportNarrativeSections.length" class="sa-report-md" v-html="renderMd(latestReport)"></div>
                  <div class="sa-download-row">
                    <button class="sa-secondary-btn" @click="openReportViewer">
                      <span class="sa-btn-label">查看大图</span>
                    </button>
                    <button class="sa-primary-btn" @click="downloadLatestReport">
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
      title="完整报告"
      width="min(1100px, 92vw)"
      top="4vh"
      class="sa-report-dialog"
      destroy-on-close
    >
      <div class="sa-report-dialog-body">
        <div class="sa-report-dialog-head">
          <div>
            <div class="sa-side-report-kicker">FULL REPORT</div>
            <h3 class="sa-report-dialog-title">{{ reportViewerTitle || sideReportHeading }}</h3>
          </div>
          <div class="sa-report-dialog-actions">
            <button class="sa-secondary-btn" @click="downloadLatestReport">
              <span class="sa-btn-label">导出 PDF</span>
            </button>
          </div>
        </div>
        <div class="sa-report-dialog-content">
          <div class="sa-report-dialog-overview">
            <section class="sa-report-stage-section sa-report-stage-summary">
              <div class="sa-report-stage-title">分析摘要</div>
              <ul class="sa-report-bullet-list">
                <li v-for="(item, index) in reportSummaryBullets" :key="index">{{ item }}</li>
              </ul>
            </section>

            <section v-if="reportDialogMetricCards.length" class="sa-report-stage-section sa-report-stage-metrics">
              <div class="sa-report-stage-title">关键指标</div>
              <div class="sa-kpi-shelf">
                <div v-for="metric in reportDialogMetricCards" :key="metric.label" class="sa-kpi-card">
                  <div class="sa-kpi-value">{{ metric.value }}</div>
                  <div class="sa-kpi-label">{{ metric.label }}</div>
                </div>
              </div>
            </section>
          </div>

          <section v-if="reportDialogCharts.length" class="sa-report-stage-section">
            <div class="sa-report-stage-title">图表分析</div>
            <div class="sa-report-chart-grid">
              <article v-for="block in reportDialogCharts" :key="block.key" class="sa-report-chart-card">
                <div class="sa-report-chart-head">
                  <div>
                    <div class="sa-report-chart-title">{{ block.dataset.dataset_name }}</div>
                    <div class="sa-report-chart-subtitle">{{ block.chartSpec.title || '图表预览' }}</div>
                  </div>
                  <button class="sa-ghost-btn" @click="openChartViewer(block.chartSpec, `${block.dataset.dataset_name} 图表预览`)">放大查看</button>
                </div>
                <div v-if="block.chartSpec.chartType === 'metric'" class="sa-insight-metric sa-insight-metric-report">
                  <div class="sa-insight-metric-value">{{ block.chartSpec.value }}</div>
                  <div class="sa-insight-metric-label">{{ block.chartSpec.label }}</div>
                </div>
                <div v-else class="sa-report-chart-canvas" :ref="el => initPreviewChart(el, block.chartSpec, `report-${block.key}`)"></div>
              </article>
            </div>
          </section>

          <section v-if="reportTableBlocks.length" class="sa-report-stage-section">
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

          <section class="sa-report-stage-section">
            <div class="sa-report-stage-title">完整解读</div>
            <div class="sa-report-sections">
              <article
                v-for="(section, index) in reportNarrativeSections"
                :key="`${section.title}-${index}`"
                class="sa-report-section-card sa-report-section-card-dialog"
              >
                <div class="sa-report-section-title">{{ section.title }}</div>
                <div class="sa-report-md" v-html="renderMd(section.body)"></div>
              </article>
            </div>
            <div v-if="!reportNarrativeSections.length" class="sa-report-md" v-html="renderMd(reportViewerReport || latestReport)"></div>
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

defineOptions({ name: 'SmartAsk' })
import ChatHeader from '../components/smartask/ChatHeader.vue'
import WelcomeScreen from '../components/smartask/WelcomeScreen.vue'
import UserBubble from '../components/smartask/UserBubble.vue'
import PlanCard from '../components/smartask/PlanCard.vue'
import ThinkingCard from '../components/smartask/ThinkingCard.vue'
import LiveExecutionFeed from '../components/smartask/LiveExecutionFeed.vue'
import AgentDoneBar from '../components/smartask/AgentDoneBar.vue'
import ArtifactStrip from '../components/smartask/ArtifactStrip.vue'
import ResultDigestCard from '../components/smartask/ResultDigestCard.vue'
import ReportSummary from '../components/smartask/ReportSummary.vue'
import ComposerArea from '../components/smartask/ComposerArea.vue'
import LogTimeline from '../components/smartask/LogTimeline.vue'
import SqlBlock from '../components/smartask/SqlBlock.vue'
import { useSmartAskHistory } from '../state/smartAskHistory'
import '../styles/volcano-design.css'

const session = useSmartAskSession()
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
const messages = reactive([])
const confirmationDrafts = reactive({})
const confirmationSubmitting = reactive({})
const showPanel = ref(true)
const chatBodyRef = ref(null)
const panelRef = ref(null)
const chartDialogRef = ref(null)
const thinkingOpen = reactive({})
const logOpen = reactive({})
const reportViewerVisible = ref(false)
const reportViewerTitle = ref('')
const reportViewerReport = ref('')
const reportViewerDatasets = ref([])
const chartViewerVisible = ref(false)
const chartViewerTitle = ref('图表预览')
const chartViewerSpec = ref(null)
const chartViewerMode = ref('chart')
let activePrintFrame = null
let msgCounter = 0
let elapsed = ref(0)
let timerInst = null
let chatScrollTimer = null
let panelScrollTimer = null

const isRunning = computed(() => session.state.status === 'running')

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
const sideReportHeading = computed(() => (
  latestDatasets.value.length > 1
    ? '跨数据集经营分析报告'
    : (latestDataset.value?.dataset_name || '经营分析报告')
))
const sideReportTitle = computed(() => latestDataset.value?.dataset_name || '经营分析报告')

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

const formatDisplayValue = (value) => {
  if (typeof value === 'number') {
    if (Number.isInteger(value)) return value.toLocaleString()
    return value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
  }
  return String(value ?? '-')
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
  const firstRow = rows[0]
  const numericColumns = getNumericColumns(dataset)
  const cards = []

  numericColumns.slice(0, 3).forEach((column) => {
    const values = rows.map(row => row[column]).filter(value => typeof value === 'number')
    if (!values.length) return
    const displayValue = rows.length === 1 ? firstRow[column] : Math.max(...values)
    cards.push({ label: rows.length === 1 ? column : `最高${column}`, value: formatDisplayValue(displayValue) })
  })

  if (rows.length === 1 && cards.length === 0) {
    const labelColumn = getLabelColumn(dataset)
    if (labelColumn) cards.push({ label: labelColumn, value: formatDisplayValue(firstRow[labelColumn]) })
  }

  if (rows.length > 1) cards.push({ label: '数据行数', value: formatDisplayValue(rows.length) })
  return cards.slice(0, 3)
}

const inferChartSpec = (dataset) => {
  const rows = dataset?.rows || []
  if (!rows.length) return null

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
        value: formatDisplayValue(firstRow[numericColumns[0]]),
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
    const derivedCharts = buildSingleRowMetricCharts(dataset)
      .map(item => item.chartSpec)
      .filter(Boolean)

    return {
      key: `${dataset.dataset_id || index}-${dataset.dataset_name || 'dataset'}`,
      caption: index === 0 ? '主结果视图' : 结果视图 ,
      dataset,
      metricCards: getMetricCards(dataset),
      chartSpec: inferChartSpec(dataset),
      extraCharts: derivedCharts,
    }
  })
))

const reportDialogCharts = computed(() => {
  const sourceItems = reportViewerVisible.value
    ? reportViewerDatasets.value.slice(0, 4).flatMap((dataset, index) => {
        const primary = {
          key: `${dataset.dataset_id || index}-${dataset.dataset_name || 'dataset'}`,
          caption: index === 0 ? '主结果视图' : 结果视图 ,
          dataset,
          metricCards: getMetricCards(dataset),
          chartSpec: inferChartSpec(dataset),
        }
        return [primary, ...buildSingleRowMetricCharts(dataset)]
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

const reportDialogMetricCards = computed(() => (
  (reportViewerVisible.value
    ? (reportViewerDatasets.value[0] ? getMetricCards(reportViewerDatasets.value[0]) : [])
    : resultPreviews.value[0]?.metricCards
  ) || []
))

const reportTableBlocks = computed(() => (
  buildReportTableBlocks(reportViewerVisible.value ? reportViewerDatasets.value : latestDatasets.value)
))

const reportSummaryBullets = computed(() => {
  const bullets = []
  const sourceDatasets = reportViewerVisible.value ? reportViewerDatasets.value : latestDatasets.value
  const primary = sourceDatasets[0]
  const names = sourceDatasets.map(item => item.dataset_name).filter(Boolean)
  if (session.state.question) bullets.push(`原始问题：${session.state.question}`)
  if (names.length) bullets.push(`命中数据集：${names.join('、')}`)
  if (sourceDatasets.length) {
    const totalRows = sourceDatasets.reduce((sum, item) => sum + Number(item?.row_count || item?.rows?.length || 0), 0)
    bullets.push(`数据结果：共返回 ${sourceDatasets.length} 份结果，累计 ${totalRows} 行数据。`)
  }
  const reviewSummary = primary?.agent3_review?.review_summary
  if (reviewSummary) bullets.push(`SQL 复核结论：${reviewSummary}`)
  const sample = primary?.rows?.[0]
  const columns = primary?.columns || []
  if (sample && columns.length) {
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

  const normalized = raw
    .replace(/\r\n/g, '\n')
    .replace(/^#\s+/gm, '## ')
    .replace(/\n---\n/g, '\n\n')

  const parts = normalized.split(/\n(?=##\s+)/).map(item => item.trim()).filter(Boolean)
  const sections = parts.map((part, index) => {
    const lines = part.split('\n')
    const heading = String(lines[0] || '').replace(/^##\s*/, '').trim()
    const body = lines.slice(1).join('\n').trim()
    return {
      title: heading || `分析段落 ${index + 1}`,
      body: body || part,
    }
  })

  if (sections.length <= 1) {
    return [{
      title: reportViewerTitle.value || sideReportHeading.value,
      body: raw,
    }]
  }

  return sections
})

// 方法
const renderMd = (text) => marked.parse(text || '')

const togglePanel = () => { showPanel.value = !showPanel.value }
const toggleThinking = (id) => { thinkingOpen[id] = !thinkingOpen[id] }
const toggleLog = (i) => { logOpen[i] = !logOpen[i] }
const openDetailPanel = () => {
  showPanel.value = true
  schedulePanelScroll(80, 'smooth')
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
  reportViewerTitle.value = title || '经营分析报告'
  reportViewerDatasets.value = Array.isArray(datasetsForReport) ? datasetsForReport : []
  reportViewerVisible.value = true
}
const openReportViewerForMessage = (msg) => openReportViewer(getReport(msg), getPrimaryDataset(msg)?.dataset_name || getResultTitle(msg), getDatasets(msg))
const openChartViewer = (spec, title = '图表预览') => {
  if (!spec) return
  chartViewerSpec.value = spec
  chartViewerTitle.value = title
  chartViewerMode.value = 'chart'
  chartViewerVisible.value = true
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

const shouldShowLiveFeed = (msg) => {
  return Boolean(session.state.logs.length > 0 && (msg?.loading || isCurrentSessionMessage(msg)))
}

const shouldShowThinkingCard = (msg) => {
  if (msg?.loading) return !session.state.logs.length
  if (!msg?.data) return false
  return !shouldShowLiveFeed(msg)
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
  getDatasets(msg)
    .slice(0, 3)
    .map((dataset, index) => ({
      key: `${dataset.dataset_id || index}-${dataset.dataset_name || 'dataset'}`,
      dataset,
      chartSpec: inferChartSpec(dataset),
    }))
    .filter(item => item.chartSpec)
)

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
  scheduleChatScroll(24, 'smooth')
  startTimer()

  try {
    const res = await session.startAsk(text, datasetId.value, modelId.value)
    aiMsg.loading = false
    aiMsg.data = res || { aborted: true }
    query.value = ''
    thinkingOpen[aid] = false
    scheduleChatScroll(48, 'smooth')
    schedulePanelScroll(160, 'smooth')
    if (res?.dataset_results?.length) nextTick(() => schedulePanelScroll(260, 'smooth'))
  } catch (err) {
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
  setActiveHistory('')
  session.resetSession()
  showPanel.value = true
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

const buildDownloadFilename = (title) => {
  const base = String(title || sideReportHeading.value || '经营分析报告')
    .replace(/[\\/:*?"<>|]+/g, '-')
    .replace(/\s+/g, ' ')
    .trim()
  return `${base || '经营分析报告'}.pdf`
}

const buildReportHtml = (title, report) => `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${title}</title>
  <style>
    @page { size: A4; margin: 16mm 14mm; }
    body { margin: 0; font-family: "PingFang SC", "Microsoft YaHei", sans-serif; background: #f7f8fa; color: #1d2129; }
    .page { max-width: 960px; margin: 0 auto; padding: 40px 24px 72px; }
    .card { background: #fff; border: 1px solid #e5e6eb; border-radius: 20px; padding: 28px 32px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05); }
    .eyebrow { font-size: 12px; color: #165dff; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
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
      <h1>${title}</h1>
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

  const exportTitle = title || '经营分析报告'
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
const downloadReportForMessage = (msg) => downloadLatestReport(getReport(msg), getPrimaryDataset(msg)?.dataset_name || getResultTitle(msg))

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

  nextTick(() => {
    scrollChat('auto')
    scrollPanel('auto')
  })
  return true
}

const quickAsk = (text) => {
  query.value = text
  nextTick(() => {
    const textarea = document.querySelector('.sa-textarea')
    if (textarea instanceof HTMLTextAreaElement) {
      textarea.focus()
      textarea.setSelectionRange(textarea.value.length, textarea.value.length)
    }
  })
  ElMessage({ message: '已填入，按 Enter 发送', type: 'success', duration: 1800, showClose: false, customClass: 'sa-toast-modern' })
}

const handleExternalFreshChat = () => {
  if (isRunning.value) return
  handleNewChat()
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
  if (optionType === 'dataset_scope') return '确认后将锁定该数据集口径，并继续生成 SQL 与分析报告。'
  if (optionType === 'dataset_disambiguation') return '确认后将锁定具体数据集口径，并继续生成后续分析结果。'
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
    return '当前命中了多个可能的数据集口径，确认后会锁定后续执行范围。'
  }
  if (candidateCount > 1) return `当前存在 ${candidateCount} 个候选口径，确认后会锁定后续执行范围。`
  return '当前需要先确认业务口径，确认后才会继续执行查询与报告生成。'
}

const doConfirm = async (opt, msg) => {
  startTimer()
  if (msg?.id) confirmationSubmitting[msg.id] = true
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
    if (msg) msg.loading = false
    if (msg?.id) confirmationSubmitting[msg.id] = false
    ElMessage.error(error?.response?.data?.error || '提交失败')
  }
  finally { stopTimer() }
}

const scrollChat = (behavior = 'smooth') => nextTick(() => {
  if (chatBodyRef.value) {
    chatBodyRef.value.scrollTo({ top: chatBodyRef.value.scrollHeight, behavior })
  }
})
const scrollPanel = (behavior = 'smooth') => nextTick(() => {
  if (panelRef.value) {
    panelRef.value.scrollTo({ top: panelRef.value.scrollHeight, behavior })
  }
})

const scheduleChatScroll = (delay = 40, behavior = 'smooth') => {
  if (chatScrollTimer) clearTimeout(chatScrollTimer)
  chatScrollTimer = window.setTimeout(() => {
    scrollChat(behavior)
  }, delay)
}

const schedulePanelScroll = (delay = 150, behavior = 'smooth') => {
  if (panelScrollTimer) clearTimeout(panelScrollTimer)
  panelScrollTimer = window.setTimeout(() => {
    scrollPanel(behavior)
  }, delay)
}

const startTimer = () => {
  elapsed.value = 0
  clearInterval(timerInst)
  timerInst = setInterval(() => elapsed.value++, 1000)
}
const stopTimer = () => clearInterval(timerInst)

const loadQuestions = async () => {
  try {
    const res = await getCommonQuestions(datasetId.value)
    commonQuestions.value = (res.questions || res.common_questions || []).slice(0, 4)
  } catch { commonQuestions.value = [] }
}

const renderChartSpec = (chart, data) => {
  const labelColumn = data.columns?.[0]
  const numericColumns = data.columns?.slice(1) || []
  const colorPalette = ['#165dff', '#00b42a', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']

  if (data.chartType === 'trend') {
    chart.setOption({
      backgroundColor: 'transparent',
      color: colorPalette,
      tooltip: { trigger: 'axis' },
      legend: { top: 0, textStyle: { color: '#4e5969', fontSize: 11 } },
      grid: { left: 34, right: 18, top: 34, bottom: 28 },
      xAxis: {
        type: 'category',
        data: data.rows.map(row => row[labelColumn]),
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
        data: data.rows.map(row => row[column]),
      })),
    })
    return
  }

  if (data.chartType === 'bar') {
    const valueColumn = numericColumns[0]
    chart.setOption({
      backgroundColor: 'transparent',
      color: [colorPalette[0]],
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 34, right: 18, top: 18, bottom: 48 },
      xAxis: {
        type: 'category',
        data: data.rows.slice(0, 8).map(row => row[labelColumn]),
        axisLabel: { color: '#86909c', fontSize: 11, interval: 0, rotate: data.rows.length > 5 ? 18 : 0 },
        axisLine: { lineStyle: { color: '#e5e6eb' } },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#86909c', fontSize: 11 },
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
        data: data.rows.slice(0, 8).map(row => row[valueColumn]),
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
      data: data.rows.slice(0, 6).map(row => ({ name: row[labelColumn], value: row[valueColumn] })),
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
    schedulePanelScroll(140, 'smooth')
  }
}, { flush: 'post' })

watch(() => session.state.status, (s) => {
  if (s === 'completed') {
    nextTick(() => {
      scheduleChatScroll(40, 'smooth')
      schedulePanelScroll(180, 'smooth')
    })
  }
  if (s === 'waiting_confirmation') {
    scheduleChatScroll(26, 'smooth')
    schedulePanelScroll(140, 'smooth')
  }
})

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

onMounted(async () => {
  window.addEventListener('smartask-create-fresh-chat', handleExternalFreshChat)
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
  font-family: 'PingFang SC', 'Helvetica Neue', 'Inter', Arial, sans-serif;
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
  width: 458px;
  display: flex;
  flex-direction: column;
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
  overflow-y: auto;
  padding-bottom: 10px;
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
.sa-kpi-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-primary);
}
.sa-kpi-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
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
}

.sa-mini-table :deep(.el-table__body-wrapper td) {
  font-size: 11px;
  color: #1d2129;
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
}

.sa-preview :deep(.el-table__body-wrapper td) {
  font-size: 11px;
  color: #1d2129;
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

.sa-report-dialog-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 2px 2px 12px;
  border-bottom: 1px solid rgba(29, 33, 41, 0.08);
}

.sa-report-dialog-title {
  margin: 6px 0 0;
  font-size: 24px;
  line-height: 1.22;
  font-weight: 700;
  color: #1d2129;
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

.sa-report-stage-section {
  max-width: 1120px;
  width: 100%;
  margin: 0 auto;
  padding: 16px 18px 16px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  border-radius: 16px;
  background: #ffffff;
  box-shadow: 0 6px 22px rgba(15, 23, 42, 0.035);
}

.sa-report-stage-summary {
  background: linear-gradient(180deg, #ffffff 0%, #fbfcff 100%);
}

.sa-report-stage-metrics {
  align-self: stretch;
}

.sa-report-stage-title {
  margin-bottom: 12px;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.25;
  color: #1d2129;
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
  border-radius: 14px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  background: #fbfcff;
}

.sa-report-section-card-dialog {
  padding: 16px 18px 16px;
  border-radius: 16px;
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
  border-radius: 16px;
  border: 1px solid rgba(22, 93, 255, 0.1);
  background: #fbfcff;
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
}

.sa-preview-table-report :deep(.el-table__body-wrapper td) {
  font-size: 11px;
  color: #1d2129;
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
    width: 420px;
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
    border-left: none;
    border-top: 1px solid rgba(29, 33, 41, 0.08);
    min-height: 360px;
  }
}
</style>

