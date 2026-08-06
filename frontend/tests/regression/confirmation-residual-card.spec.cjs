/**
 * Regression: 刷新残留"已提交确认"卡片 (BugFix 2026-08-06)
 *
 * 缺陷：SmartAsk.vue onMounted (L5678) 没清空 confirmationSubmitting 等 reactive，
 *       导致历史卡死时的 submitted 标记被带进新会话。
 *
 * 修复（L5715-5718）：onMounted 末尾增加 3 行清理：
 *   Object.keys(confirmationSubmitting).forEach(k => delete confirmationSubmitting[k])
 *   Object.keys(confirmationDrafts).forEach(k => delete confirmationDrafts[k])
 *   Object.keys(confirmExpanded).forEach(k => delete confirmExpanded[k])
 *
 * 验收依据：
 *   - .workbuddy/memory/2026-08-06.md（user-level memory: 测试真实性 / 区分代码推断 vs 实际跑过）
 *   - SmartAsk.vue:190-197（"已提交确认"卡片 DOM）
 *   - SmartAsk.vue:4165-4171（shouldShowConfirmationSubmitted 条件）
 *
 * 用例（每个用例显式区分代码推断 vs 实际跑过）：
 *   T1 核心：硬刷新后旧的"已提交确认"卡片不显示
 *   T2 兜底：清空后发新问数时能正常进入确认流
 *   T3 边界：多条残留不会被一起带入新会话
 *
 * 运行：
 *   node frontend/tests/regression/confirmation-residual-card.spec.js
 *
 * 重要：测试使用 page.route() mock SSE 响应 → 不依赖真实 LLM；
 *      模拟"卡死"通过劫持 confirm-by-boss/stream 让它 hang。
 */

const { chromium } = require('playwright-chromium');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:8888/smart-ask';
const SHOTS = '/Users/ltl123/smartask/sa1.0/smartask/.workbuddy/memory/qa-screenshots';
const AUTH_TOKEN = 'ezbhaD_poRnR5IpcFpDVpaZZ1g_J8CxZdVRgZ7UlRqY';

const SELECTORS = {
  // From SmartAsk.vue:131 — `<div v-if="shouldShowConfirmationCard(msg)" class="sa-card sa-confirm-card">`
  confirmCard: '.sa-confirm-card',
  // From SmartAsk.vue:190 — `<div v-else-if="shouldShowConfirmationSubmitted(msg)" class="sa-card sa-confirm-submitted">`
  confirmSubmitted: '.sa-confirm-submitted',
  // From SmartAsk.vue:193 — `.sa-confirm-submitted-title`
  confirmSubmittedTitle: '.sa-confirm-submitted-title',
};

function ensureShotDir() {
  if (!fs.existsSync(SHOTS)) fs.mkdirSync(SHOTS, { recursive: true });
}

function logEvidence(label, ok, detail) {
  const tag = ok ? 'PASS' : 'FAIL';
  const msg = `[${tag}] ${label} :: ${detail}`;
  console.log(msg);
  return msg;
}

/**
 * Build a fake SSE response body for the chat stream,
 * returning `requires_confirmation: true` as the final result so that
 * SmartAsk renders the "需要确认" card.
 */
function buildChatStreamFrames({ question = '上海的业绩', datasetId = 1 } = {}) {
  const encoder = (obj) => `data: ${JSON.stringify(obj)}\n\n`;
  const frames = [];
  frames.push(`event: ready\n${encoder({ ok: true, question })}`);
  // trace frames
  frames.push(`event: trace\n${encoder({
    type: 'trace', phase: 'clarify',
    label: '检测到意图歧义，需要确认',
    detail: '提问涉及多个可能的解读，需要您确认'
  })}`);
  // result frame with requires_confirmation
  const result = {
    requires_confirmation: true,
    session_id: 'regr-' + Date.now(),
    question,
    dataset_id: datasetId,
    route: {
      decision: 'clarify',
      confidence: 0.4,
      requires_confirmation: true,
    },
    confirmation_question: '请确认统计口径',
    confirmation_options: [
      { label: '口径 A：华东区', description: '按华东区分公司统计', score: 88, recommended: true },
      { label: '口径 B：全国', description: '按全国汇总统计', score: 75 },
      { label: '口径 C：上海单市', description: '仅上海地区', score: 65 },
    ],
  };
  frames.push(`event: result\n${encoder({ type: 'result', result })}`);
  frames.push(`event: done\n${encoder({ ok: true })}`);
  return frames.join('\n');
}

/**
 * Hang SSE — never completes. Used to simulate 卡死 in confirm-by-boss/stream.
 * Plays out one heartbeat every second then keeps the connection open.
 */
function buildHangingStream() {
  // Triggers `confirmationSubmitting[id]=true` initially, then hangs.
  // The frontend will see the connection open, receive keep-alive, and
  // the `submitted` card will stay visible.
  return new Promise(() => {}); // never resolves in Page Route
}

/**
 * Inject real-time answers for all matching routes.
 * - `/api/smart-chat/stream` → fake "requires_confirmation" SSE
 * - `/api/smart-chat/confirm-by-boss/stream` → hang (so `submitted` stays)
 * - `/api/auth/me` → minimal user info (so Vue mount goes through)
 * - other less critical endpoints → default route
 */
async function installRoutes(page, { hangConfirm = true, chatQuestion = '上海的业绩' } = {}) {
  page.on('request', (req) => {
    if (req.url().includes('/api/smart-chat/')) {
      console.log('[route]', req.method(), req.url());
    }
  });

  await page.route('**/api/smart-chat/stream', async (route) => {
    const body = buildChatStreamFrames({ question: chatQuestion });
    console.log('[mock /smart-chat/stream] sending frames len=', body.length);
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      headers: {
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
      },
      body,
    });
  });

  await page.route('**/api/smart-chat/confirm-by-boss/stream', async (route) => {
    if (hangConfirm) {
      // Stream that emits a "started" frame and then heartbeats forever (hangs the page).
      // The user clicks confirm → this hangs → confirmationSubmitting[id] = true.
      // The frontend will see this connection open and keep `submitted` card visible.
      const encoder = new TextEncoder();
      const stream = new ReadableStream({
        start(controller) {
          // Send `ready` so the frontend confirms the listener is in place
          controller.enqueue(encoder.encode(`event: ready\ndata: ${JSON.stringify({ ok: true })}\n\n`));
          // Hang — never close
        }
      });
      console.log('[mock /confirm-by-boss/stream] hanging');
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        headers: {
          'Cache-Control': 'no-cache',
          'X-Accel-Buffering': 'no',
        },
        body: stream,
      });
    } else {
      await route.continue();
    }
  });

  // Auth: do NOT mock /api/auth/me — real backend must validate token.
  // Other endpoints are mocked for the regression flow.

  await page.route('**/api/bookshelves/active-ai-models', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ models: [{ id: 'mock-1', name: 'Mock Model', is_default: true }] }),
    });
  });

  await page.route('**/api/bookshelves/datasets**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        datasets: [{ id: 1, name: '测试数据集', tables: ['t_sales'] }],
      }),
    });
  });

  await page.route('**/api/smart-chat/report-history**', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [] }),
      });
    } else {
      await route.continue();
    }
  });
}

async function gotoSmartAsk(page) {
  await page.goto('http://localhost:8888/', { waitUntil: 'domcontentloaded' });
  await page.evaluate(t => localStorage.setItem('auth_token', t), AUTH_TOKEN);
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  // Wait for SmartAsk to render fully (textarea must be visible).
  // If something broke, capture debug info.
  try {
    await page.waitForSelector('textarea.sa-textarea', { timeout: 20000 });
  } catch (e) {
    const dbg = await page.evaluate(() => ({
      url: location.href,
      appHTML: document.querySelector('#app') ? document.querySelector('#app').innerHTML.length : 'no-app',
      ta: !!document.querySelector('textarea.sa-textarea'),
      anyTa: document.querySelectorAll('textarea').length,
      bodyClass: document.body.className,
      hasLogin: !!document.querySelector('.auth-login-page'),
    }));
    console.log('[DEBUG gotoSmartAsk]', JSON.stringify(dbg));
    throw e;
  }
  await page.waitForTimeout(800);
}

async function askAndWaitForConfirm(page) {
  // Find input box and submit
  const input = page.locator('textarea.sa-textarea').first();
  await input.waitFor({ state: 'visible', timeout: 15000 });
  await input.fill('上海的业绩');
  // Press the send button (sa-send-btn with aria-label 发送问题)
  const sendBtn = page.locator('button.sa-send-btn, [aria-label="发送问题"]').first();
  await sendBtn.waitFor({ state: 'visible', timeout: 5000 });
  await sendBtn.click();
  // Wait for either confirm card to appear
  await page.waitForSelector(SELECTORS.confirmCard, { timeout: 12000 }).catch(() => {});
}

async function clickConfirm(page) {
  // First confirm option (button.confirm-row) inside confirm-card.
  // After click, confirmationSubmitting[id]=true; submitted card should appear.
  const optBtn = page.locator('.sa-confirm-card .sa-confirm-row').first();
  await optBtn.waitFor({ state: 'visible', timeout: 5000 }).catch(() => null);
  if (await optBtn.count() === 0) return false;
  await optBtn.click();
  return true;
}

(async () => {
  ensureShotDir();
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const results = [];
  let browser = null;
  let totalObservations = 0;

  try {
    browser = await chromium.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-dev-shm-usage'],
    });

    // ==============================================================
    // 用例 T1 (核心)：硬刷新后，旧的"已提交确认"卡片不显示
    // ==============================================================
    {
      const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
      const page = await ctx.newPage();
      page.on('console', msg => {
        if (msg.type() === 'error') console.log('[browser-err]', msg.text().slice(0, 200));
      });
      try {
        await installRoutes(page, { hangConfirm: true });
        await gotoSmartAsk(page);
        await askAndWaitForConfirm(page);
        const submitClicked = await clickConfirm(page);
        if (!submitClicked) {
          results.push(logEvidence('T1 (核心) 硬刷新后旧的"已提交确认"卡片不显示', false,
            '无法点击确认按钮——mock 未生效'));
          await ctx.close();
        } else {
          // Wait for "已提交确认" card
          await page.waitForSelector(SELECTORS.confirmSubmitted, { timeout: 6000 }).catch(() => {});
          const beforeReload = await page.locator(SELECTORS.confirmSubmitted).count();
          totalObservations += 1;
          await page.screenshot({ path: path.join(SHOTS, `t1-before-reload-${stamp}.png`), fullPage: false });

          // 硬刷新
          await page.reload({ waitUntil: 'domcontentloaded' });
          // Wait for re-mount
          await page.waitForSelector('main, .el-container, .app-shell', { timeout: 15000 });
          await page.waitForTimeout(1500); // settle re-mount + history fetch

          const afterReload = await page.locator(SELECTORS.confirmSubmitted).count();
          totalObservations += 1;
          await page.screenshot({ path: path.join(SHOTS, `t1-after-reload-${stamp}.png`), fullPage: false });

          const ok = beforeReload >= 1 && afterReload === 0;
          results.push(logEvidence(
            `T1 (核心) 硬刷新后旧的"已提交确认"卡片不显示`,
            ok,
            `刷新前 DOM 中提交卡数=${beforeReload}，刷新后 DOM 中提交卡数=${afterReload}（期望 0）；观察样本=2（刷新前+刷新后），周期=1 次硬刷新`
          ));
        }
      } catch (e) {
        results.push(logEvidence('T1', false, `异常: ${e.message}`));
      } finally {
        await ctx.close();
      }
    }

    // ==============================================================
    // 用例 T2 (兜底)：刷新后能正常进入新的确认流
    // ==============================================================
    {
      const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
      const page = await ctx.newPage();
      try {
        await installRoutes(page, { hangConfirm: true });
        await gotoSmartAsk(page);
        await askAndWaitForConfirm(page);
        await clickConfirm(page);
        await page.waitForSelector(SELECTORS.confirmSubmitted, { timeout: 6000 }).catch(() => {});

        // 硬刷新
        await page.reload({ waitUntil: 'domcontentloaded' });
        await page.waitForSelector('main, .el-container, .app-shell', { timeout: 15000 });
        await page.waitForTimeout(1500);

        // 重新发问 → 期待看到 "需要确认" 卡片（而不是 "已提交确认"）
        await askAndWaitForConfirm(page);
        const hasConfirmCard = await page.locator(SELECTORS.confirmCard).count();
        const hasSubmitted = await page.locator(SELECTORS.confirmSubmitted).count();
        totalObservations += 2;
        await page.screenshot({ path: path.join(SHOTS, `t2-after-new-flow-${stamp}.png`), fullPage: false });

        const ok = hasConfirmCard >= 1 && hasSubmitted === 0;
        results.push(logEvidence(
          `T2 (兜底) 清空后能正常进入新的确认流`,
          ok,
          `发新问后 DOM：需要确认卡=${hasConfirmCard} 张（期望 ≥1），已提交卡=${hasSubmitted} 张（期望 0）；观察样本=2，周期=1 次刷新+1 次重发问`
        ));
      } catch (e) {
        results.push(logEvidence('T2', false, `异常: ${e.message}`));
      } finally {
        await ctx.close();
      }
    }

    // ==============================================================
    // 用例 T3 (边界)：多条残留不会被一起带入新会话
    // ==============================================================
    {
      const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
      const page = await ctx.newPage();
      try {
        await installRoutes(page, { hangConfirm: true });
        await gotoSmartAsk(page);

        // 模拟多轮「卡死」：每轮发问 → 等确认 → 点确认（全部立即 hang）
        for (let i = 0; i < 3; i++) {
          await askAndWaitForConfirm(page);
          await clickConfirm(page);
          await page.waitForSelector(SELECTORS.confirmSubmitted, { timeout: 6000 }).catch(() => {});
          await page.waitForTimeout(500);
        }
        const beforeReload = await page.locator(SELECTORS.confirmSubmitted).count();
        totalObservations += 1;
        await page.screenshot({ path: path.join(SHOTS, `t3-before-reload-multi-${stamp}.png`), fullPage: false });

        // 硬刷新
        await page.reload({ waitUntil: 'domcontentloaded' });
        await page.waitForSelector('main, .el-container, .app-shell', { timeout: 15000 });
        await page.waitForTimeout(1500);

        const afterReload = await page.locator(SELECTORS.confirmSubmitted).count();
        totalObservations += 1;
        await page.screenshot({ path: path.join(SHOTS, `t3-after-reload-multi-${stamp}.png`), fullPage: false });

        const ok = beforeReload >= 1 && afterReload === 0;
        results.push(logEvidence(
          `T3 (边界) 多条残留不会被一起带入新会话`,
          ok,
          `连续 3 轮卡死后 DOM 提交卡数=${beforeReload}，硬刷新后=${afterReload}（期望 0）；观察样本=2（注入+清零），周期=1 次硬刷新`
        ));
      } catch (e) {
        results.push(logEvidence('T3', false, `异常: ${e.message}`));
      } finally {
        await ctx.close();
      }
    }
  } finally {
    if (browser) await browser.close();
  }

  console.log('\n=== Regression Test Summary ===');
  for (const r of results) console.log(r);
  console.log(`Total observations: ${totalObservations}`);
  const passCount = results.filter(r => r.startsWith('[PASS]')).length;
  console.log(`${passCount}/${results.length} cases passed`);
  process.exit(passCount === results.length ? 0 : 1);
})().catch(e => {
  console.error('FATAL', e);
  process.exit(2);
});
