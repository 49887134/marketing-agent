import { test, expect, _electron as electron } from '@playwright/test'
import path from 'node:path'

test('智能分析真实课堂 A B C、动态范围与数据依据', async ({ page }) => {
  test.setTimeout(420000)
  await page.goto('/')
  await page.locator('.sidebar').getByRole('button', { name: '智能分析' }).click()
  const panel = page.getByRole('region', { name: '智能分析' })
  await expect(panel.getByText(/可查询范围：/)).toBeVisible({ timeout: 30000 })
  for (const example of ['A · 知识规则', 'B · 综合分析', 'C · 能力边界']) {
    await panel.getByRole('button', { name: example }).click()
    const response = page.waitForResponse(r => r.url().endsWith('/api/agent/analyze') && r.request().method() === 'POST', { timeout: 135000 })
    await panel.getByRole('button', { name: '开始分析' }).click()
    await expect(panel.getByRole('button', { name: '开始分析' })).toBeDisabled()
    const data = await (await response).json()
    if (example.startsWith('C')) {
      expect(['unsupported', 'needs_input']).toContain(data.status)
      await expect(panel.getByText(/收入/).first()).toBeVisible()
    } else {
      expect(data.status, JSON.stringify(data.errors)).toBe('completed')
      await expect(panel.getByRole('heading', { name: '知识引用', exact: true })).toBeVisible()
      if (example.startsWith('B')) await expect(panel.getByRole('heading', { name: '报表数据依据' })).toBeVisible()
    }
    await expect(panel.getByRole('heading', { name: '本次执行记录' })).toBeVisible()
    await page.screenshot({ path: `../artifacts/lesson3-browser-real-${example[0]}.png`, fullPage: true })
  }
})

test('智能分析异常替身：失败、重试与重复提交', async ({ page }) => {
  await page.route('**/api/agent/metadata', route => route.fulfill({ json: { scope: { start_date: '2026-09-01', end_date: '2026-09-21', rows: 61, simulated: true } } }))
  let requests = 0
  const questions: string[] = []
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/agent/analyze', async route => {
    requests++
    questions.push(route.request().postDataJSON().question)
    if (requests === 1) { await held; await route.abort() }
    else await route.fulfill({ json: { status: 'partial', message: '部分失败', notice: '', events: [{ id: 'x', name: 'query_report', arguments: {}, status: 'failed', summary: '数据库不可用', elapsed_ms: 1 }], reports: [], chunks: [], errors: [{ code: 'database_unavailable', message: '数据库不可用' }], analysis: null } })
  })
  await page.goto('/')
  const nav = page.locator('.sidebar').getByRole('button', { name: '智能分析' })
  await nav.click()
  const panel = page.getByRole('region', { name: '智能分析' })
  await panel.getByRole('button', { name: '开始分析' }).click()
  await expect(panel.getByRole('button', { name: '开始分析' })).toBeDisabled()
  await expect.poll(() => requests).toBe(1)
  release()
  await expect(panel.getByRole('button', { name: '重试分析' })).toBeVisible()
  await panel.getByLabel('分析需求').fill('编辑后的不同问题')
  await panel.getByRole('button', { name: '重试分析' }).click()
  await expect(panel.getByRole('heading', { name: '本次执行记录' })).toBeVisible()
  await expect(panel.getByText('query_report · 失败')).toBeVisible()
  expect(questions[1]).toBe(questions[0])
  // 卸载页面时请求中止，重新进入时只接收新请求。
  await page.locator('.sidebar').getByRole('button', { name: '知识问答' }).click()
  await nav.click()
  await expect(panel.getByRole('heading', { name: '本次执行记录' })).toHaveCount(0)
})

test('智能分析异常替身：卸载后的旧响应不覆盖新页面', async ({ page }) => {
  await page.route('**/api/agent/metadata', route => route.fulfill({ json: { scope: { start_date: '2026-09-01', end_date: '2026-09-21', rows: 61, simulated: true } } }))
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  let requests = 0
  await page.route('**/api/agent/analyze', async route => {
    const index = ++requests
    if (index === 1) await held
    await route.fulfill({ json: { status: 'unsupported', message: index === 1 ? '旧响应不应出现' : '新请求结果', notice: '', events: [], reports: [], chunks: [], errors: [], analysis: null } }).catch(() => {})
  })
  await page.goto('/')
  const nav = page.locator('.sidebar').getByRole('button', { name: '智能分析' })
  await nav.click()
  const panel = page.getByRole('region', { name: '智能分析' })
  await panel.getByRole('button', { name: '开始分析' }).click()
  await expect.poll(() => requests).toBe(1)
  await page.locator('.sidebar').getByRole('button', { name: '投放数据看板' }).click()
  await nav.click()
  await panel.getByRole('button', { name: '开始分析' }).click()
  await expect(panel.getByText('新请求结果', { exact: true })).toBeVisible()
  release()
  await expect(panel.getByText('旧响应不应出现', { exact: true })).toHaveCount(0)
  await expect(panel.getByText('新请求结果', { exact: true })).toBeVisible()
})

for (const mode of ['dev', 'built']) {
  test(`Electron ${mode} 智能分析真实调用`, async () => {
    test.setTimeout(160000)
    const env = { ...process.env }; delete env.ELECTRON_RUN_AS_NODE
    const app = await electron.launch({ args: [path.resolve('electron/main.cjs'), ...(mode === 'dev' ? ['--dev'] : [])], env })
    try {
      const window = await app.firstWindow()
      await window.locator('.sidebar').getByRole('button', { name: '智能分析' }).click()
      const panel = window.getByRole('region', { name: '智能分析' })
      await expect(panel.getByText(/可查询范围：/)).toBeVisible({ timeout: 30000 })
      await panel.getByRole('button', { name: 'A · 知识规则' }).click()
      await panel.getByRole('button', { name: '开始分析' }).click()
      await expect(panel.getByRole('heading', { name: '知识引用', exact: true })).toBeVisible({ timeout: 130000 })
      await expect(panel.getByText('search_knowledge · 成功')).toBeVisible()
      await window.screenshot({ path: `../artifacts/lesson3-electron-real-${mode}.png`, fullPage: true })
    } finally { await app.close() }
  })
}
