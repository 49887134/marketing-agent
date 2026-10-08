import { test, expect, _electron as electron } from '@playwright/test'
import path from 'node:path'

const remoteReportTimeout = 15_000

test('浏览器真实接口、筛选、空数据、零分母、重置', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('报表数据', { exact: true })).toBeVisible()
  await expect(page.locator('tbody tr')).toHaveCount(21, { timeout: remoteReportTimeout })
  await expect(page.getByLabel('汇总指标')).toContainText('2,268.10')
  await page.getByLabel('开始日期').fill('2026-09-02')
  await page.getByLabel('结束日期').fill('2026-09-04')
  await page.getByLabel('计划名称关键词').fill('课程')
  await page.getByRole('button', { name: '查询', exact: true }).click()
  await expect(page.locator('tbody tr')).toHaveCount(3, { timeout: remoteReportTimeout })
  await expect(page.locator('tbody')).toContainText('课程咨询推广')
  await page.getByLabel('计划名称关键词').fill('不存在')
  await page.getByRole('button', { name: '查询', exact: true }).click()
  // 空结果也需要等待远程数据库，与同用例其他真实查询采用相同时限。
  await expect(page.getByText('暂无匹配数据')).toBeVisible({ timeout: remoteReportTimeout })
  await page.getByRole('button', { name: '重置', exact: true }).click()
  await expect(page.locator('tbody tr')).toHaveCount(21, { timeout: remoteReportTimeout })
  const zero = page.locator('tbody tr').filter({ hasText: '2026-09-05' }).filter({ hasText: '新客' })
  await expect(zero.locator('td').nth(7)).toHaveText('—')
  await expect(zero.locator('td').nth(8)).toHaveText('—')
  await page.screenshot({ path: '../artifacts/browser-dashboard.png', fullPage: true })
})

test('加载、网络失败及重试、前端日期校验', async ({ page }) => {
  let fail = true
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/reports/campaigns?**', async route => {
    if (fail) { await held; await route.abort() } else await route.continue()
  })
  await page.goto('/')
  await expect(page.getByText('正在加载报表…')).toBeVisible()
  release()
  await expect(page.getByRole('alert')).toContainText('无法连接报表服务')
  fail = false
  await page.getByRole('button', { name: '重试', exact: true }).click()
  await expect(page.locator('tbody tr')).toHaveCount(21, { timeout: remoteReportTimeout })
  await page.getByLabel('开始日期').fill('2026-09-08')
  await page.getByRole('button', { name: '查询', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('开始日期不能晚于结束日期')
})

test('连续查询时旧响应不会覆盖新结果', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('tbody tr')).toHaveCount(21, { timeout: remoteReportTimeout })
  let release!: () => void
  let started!: () => void
  let finished!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  const pending = new Promise<void>(resolve => { started = resolve })
  const done = new Promise<void>(resolve => { finished = resolve })
  await page.route('**/api/reports/campaigns?**', async route => {
    if (new URL(route.request().url()).searchParams.get('keyword') === '品牌') {
      const response = await route.fetch()
      started()
      await held
      await route.fulfill({ response }).catch(() => {})
      finished()
    } else await route.continue()
  })
  await page.getByLabel('计划名称关键词').fill('品牌')
  await page.getByRole('button', { name: '查询', exact: true }).click()
  await pending
  await page.getByLabel('计划名称关键词').fill('课程')
  await page.getByRole('button', { name: '查询', exact: true }).click()
  await expect(page.locator('tbody tr')).toHaveCount(7, { timeout: remoteReportTimeout })
  release()
  await done
  await expect(page.locator('tbody')).not.toContainText('品牌词推广')
  await expect(page.locator('tbody')).toContainText('课程咨询推广')
})

for (const mode of ['dev', 'built']) {
  test(`Electron ${mode} 加载真实数据及安全配置`, async () => {
    const env = { ...process.env }
    delete env.ELECTRON_RUN_AS_NODE
    const app = await electron.launch({ args: [path.resolve('electron/main.cjs'), ...(mode === 'dev' ? ['--dev'] : [])], env })
    try {
      const window = await app.firstWindow()
      await expect(window.locator('tbody tr')).toHaveCount(21, { timeout: remoteReportTimeout })
      await expect(window.getByLabel('汇总指标')).toContainText('2,268.10')
      expect(await window.evaluate(() => typeof (globalThis as any).require)).toBe('undefined')
      const preferences = await app.evaluate(({ BrowserWindow }) => {
        const prefs = BrowserWindow.getAllWindows()[0].webContents.getLastWebPreferences()
        return { contextIsolation: prefs?.contextIsolation, nodeIntegration: prefs?.nodeIntegration, sandbox: prefs?.sandbox }
      })
      expect(preferences).toEqual({ contextIsolation: true, nodeIntegration: false, sandbox: true })
      if (mode === 'built') expect(window.url()).toBe('app://dashboard/index.html')
      await window.screenshot({ path: `../artifacts/electron-${mode}.png`, fullPage: true })
    } finally { await app.close() }
  })
}
