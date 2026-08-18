#!/usr/bin/env node
/**
 * SmartAsk 关键场景前端层回归检查（独立于后端 runner）。
 *
 * 用法：node front_render_check.js <URL> <问题文本> [输出截图]
 * 环境：npm install puppeteer（或项目已有 puppeteer），并设置 CHROME_PATH 指向现有 Chrome。
 */
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

const [url, question, output = 'smartask-front.png'] = process.argv.slice(2);
if (!url || !question) {
  console.error('用法: node front_render_check.js <URL> <问题文本> [输出截图]');
  process.exit(2);
}

(async () => {
  let browser;
  try {
    const executablePath = process.env.CHROME_PATH || process.env.PUPPETEER_EXECUTABLE_PATH;
    browser = await puppeteer.launch({
      headless: true,
      executablePath: executablePath || undefined,
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });
    const page = await browser.newPage();
    await page.setViewport({width: 1440, height: 1000});
    await page.goto(url, {waitUntil: 'networkidle2', timeout: 60000});
    const input = await page.$('input[placeholder*="问"], textarea[placeholder*="问"]');
    if (!input) throw new Error('未找到 SmartAsk 输入框');
    await input.click({clickCount: 3});
    await input.type(question);
    const submit = await page.$('button');
    if (!submit) throw new Error('未找到提交按钮');
    await Promise.all([
      page.waitForResponse((response) => response.url().includes('/ask') || response.status() === 200, {timeout: 60000}).catch(() => null),
      submit.click(),
    ]);
    await page.waitForSelector('[class*="report"], [class*="card"], [data-testid*="report"]', {timeout: 60000});
    const dom = await page.evaluate(() => ({
      bodyText: document.body.innerText || '',
      kpiCards: document.querySelectorAll('[class*="kpi"], [data-testid*="kpi"]').length,
      reportRoots: document.querySelectorAll('[class*="report"], [data-testid*="report"]').length,
    }));
    if (!dom.reportRoots && !dom.kpiCards && !dom.bodyText.includes('业绩')) {
      throw new Error('请求完成但未发现报告/卡片 DOM');
    }
    const target = path.resolve(process.cwd(), output);
    await page.screenshot({path: target, fullPage: true});
    console.log(JSON.stringify({url, question, screenshot: target, ...dom}, null, 2));
  } finally {
    if (browser) await browser.close();
  }
})().catch((err) => {
  console.error(`前端回归检查失败: ${err.message}`);
  process.exit(1);
});
