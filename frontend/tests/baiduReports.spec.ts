import { test, expect, _electron as electron, type Page } from '@playwright/test'
import path from 'node:path'

const query = { start_date: '2026-05-01', end_date: '2026-06-07', start_row: 0, page_size: 200 }
const units = { amount: 'unknown', ctr: 'unknown' }
const row = { date: '2026-05-22', userName: '示例账户', interestsName: '', impression: 4, click: 0, cost: '0', ctr: '0', cpc: '0', cpm: '0' }
const answer = (q = query, rows = [row], total = rows.length) => ({ source: 'baidu_api', report_type: 2521394, query: q, units, rows, row_count: rows.length, total_row_count: total, page: q.start_row / q.page_size + 1, total_pages: Math.ceil(total / q.page_size), next_start_row: q.start_row + q.page_size < total ? q.start_row + q.page_size : null })
async function setup(page: Page) {
  await page.route('**/api/baidu-reports/status', route => route.fulfill({ json: { configured: true, integration_status: 'pending_live_verification', units } }))
}
async function open(page: Page) {
  await page.locator('.sidebar').getByRole('button', { name: '百度投放数据' }).click()
  return page.getByRole('region', { name: '百度投放数据' })
}

test('百度页面替身：成功、默认日期、零值、分页与筛选快照', async ({ page }) => {
  await setup(page)
  const requests: typeof query[] = []
  await page.route('**/api/baidu-reports/query', route => {
    const q = route.request().postDataJSON(); requests.push(q)
    return route.fulfill({ json: answer(q, Array.from({length: Math.min(200, 201-q.start_row)}, (_, i) => ({ ...row, userName: `账户${q.start_row+i}` })), 201) })
  })
  await page.goto('/')
  const panel = await open(page)
  await expect(panel.getByLabel('开始日期')).toHaveValue('2026-05-01')
  await expect(panel.getByLabel('结束日期')).toHaveValue('2026-06-07')
  await panel.getByRole('button', { name: '查询百度数据' }).click()
  await expect(panel.getByText('总记录数：201')).toBeVisible()
  const cells = panel.locator('tbody tr').first().locator('td')
  await expect(cells.nth(2)).toHaveText('—')
  for (const index of [4, 6]) await expect(cells.nth(index)).toHaveText('0')
  for (const index of [5, 7, 8]) await expect(cells.nth(index)).toHaveText('0.00')
  await panel.getByRole('button', { name: '下一页' }).click()
  await expect(panel.getByText('账户200', { exact: true })).toBeVisible()
  expect(requests[1]!.end_date).toBe('2026-06-07')
  expect(requests[1]!.start_row).toBe(200)
  await expect(panel.getByRole('button', { name: '下一页' })).toBeDisabled()
  await panel.getByRole('button', { name: '上一页' }).click()
  await expect(panel.getByText('账户0', { exact: true })).toBeVisible()
  await panel.getByLabel('结束日期').fill('2026-06-01')
  await expect(panel.locator('table')).toHaveCount(0)
  await panel.getByRole('button', { name: '查询百度数据' }).click()
  await expect(panel.getByText('账户0', { exact: true })).toBeVisible()
  expect(requests.at(-1)!.start_row).toBe(0)
  expect(requests.at(-1)!.end_date).toBe('2026-06-01')
  await page.screenshot({ path: '../artifacts/baidu-browser-mock.png', fullPage: true })
})

test('百度页面替身：空结果、认证失败、失败不保留旧数据与重试', async ({ page }) => {
  await setup(page)
  let calls = 0
  const requests: typeof query[] = []
  await page.route('**/api/baidu-reports/query', route => {
    requests.push(route.request().postDataJSON()); calls++
    if (calls === 2) return route.fulfill({ status: 502, json: { detail: { code: 'baidu_auth_failed', message: '百度认证或权限校验失败' } } })
    return route.fulfill({ json: answer(requests[calls - 1], calls === 1 ? [row] : [], calls === 1 ? 1 : 0) })
  })
  await page.goto('/')
  const panel = await open(page)
  await panel.getByRole('button', { name: '查询百度数据' }).click()
  await expect(panel.getByText('示例账户', { exact: true })).toBeVisible()
  await panel.getByRole('button', { name: '查询百度数据' }).click()
  await expect(panel.getByText('百度认证或权限校验失败', { exact: true })).toBeVisible()
  await expect(panel.getByText('示例账户', { exact: true })).toHaveCount(0)
  await panel.getByRole('button', { name: '重试查询' }).click()
  await expect(panel.getByRole('heading', { name: '暂无数据' })).toBeVisible()
  expect(requests[2]).toEqual(requests[1])
  await panel.getByLabel('开始日期').fill('2026-07-01')
  await panel.getByRole('button', { name: '查询百度数据' }).click()
  await expect(panel.getByText('请填写日期，开始日期不能晚于结束日期。')).toBeVisible()
  expect(calls).toBe(3)
})

test('百度页面替身：加载防重与离开页面后的旧请求', async ({ page }) => {
  await setup(page)
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  let calls = 0
  await page.route('**/api/baidu-reports/query', async route => {
    const index = ++calls
    if (index === 1) await held
    await route.fulfill({ json: answer(query, [{ ...row, userName: index === 1 ? '旧请求账户' : '新请求账户' }]) }).catch(() => {})
  })
  await page.goto('/')
  let panel = await open(page)
  await panel.getByRole('button', { name: '查询百度数据' }).click()
  await expect(panel.getByRole('button', { name: '查询百度数据' })).toBeDisabled()
  await expect.poll(() => calls).toBe(1)
  await page.locator('.sidebar').getByRole('button', { name: '投放数据看板' }).click()
  panel = await open(page)
  await panel.getByRole('button', { name: '查询百度数据' }).click()
  await expect(panel.getByText('新请求账户', { exact: true })).toBeVisible()
  release()
  await expect(panel.getByText('旧请求账户', { exact: true })).toHaveCount(0)
})

for (const mode of ['dev', 'built']) {
  test(`Electron ${mode} 百度页面替身查询`, async () => {
    const env = { ...process.env }; delete env.ELECTRON_RUN_AS_NODE
    const app = await electron.launch({ args: [path.resolve('electron/main.cjs'), ...(mode === 'dev' ? ['--dev'] : [])], env })
    try {
      const page = await app.firstWindow()
      await setup(page)
      await page.route('**/api/baidu-reports/query', route => route.fulfill({ json: answer() }))
      const panel = await open(page)
      await panel.getByRole('button', { name: '查询百度数据' }).click()
      await expect(panel.getByText('示例账户', { exact: true })).toBeVisible()
      await expect(panel.getByRole('columnheader', { name: '一级兴趣' })).toBeVisible()
      await page.screenshot({ path: `../artifacts/baidu-electron-${mode}-mock.png`, fullPage: true })
    } finally { await app.close() }
  })
}

const regionRow = { date: '2026-05-23', userName: '示例账户', provinceName: '北京', impression: 248, click: 6,
  cost: '13.25', ctr: '0.024193548387096774', cpc: '2.2083333333333335', cpm: '53.42741935483871' }
function regionAnswer(q: typeof query) {
  const rows = Array.from({ length: Math.min(q.page_size, 763 - q.start_row) }, (_, i) => ({ ...regionRow, provinceName: q.start_row + i === 0 ? '北京' : `省份${q.start_row + i}` }))
  return { ...answer(q, [], 763), report_type: 2324048, units: { amount: 'unknown', ctr: 'ratio' }, rows, row_count: rows.length }
}

test('地域替身：第一页第二页末页、CTR、空省份和日期重置', async ({ page }) => {
  await setup(page)
  const offsets: number[] = []
  await page.route('**/api/baidu-reports/query', route => {
    const q = route.request().postDataJSON(); offsets.push(q.start_row)
    const data = regionAnswer(q)
    if (q.start_row === 0) data.rows[1] = { ...regionRow, provinceName: '', impression: 0, click: 0, cost: '0', ctr: '0', cpc: '0', cpm: '0' }
    return route.fulfill({ json: data })
  })
  await page.goto('/')
  const panel = await open(page)
  await panel.getByRole('tab', { name: '地域报表' }).click()
  await panel.getByRole('button', { name: '查询百度数据' }).click()
  await expect(panel.getByText('总记录数：763')).toBeVisible()
  const cells = panel.locator('tbody tr').first().locator('td')
  await expect(cells.nth(5)).toHaveText('13.25')
  await expect(cells.nth(6)).toHaveText('2.42%')
  await expect(cells.nth(7)).toHaveText('2.21')
  await expect(cells.nth(8)).toHaveText('53.43')
  await expect(panel.locator('tbody tr').nth(1).locator('td').nth(2)).toHaveText('—')
  await expect(panel.locator('tbody tr').nth(1).locator('td').nth(6)).toHaveText('0.00%')
  await panel.getByRole('button', { name: '下一页' }).click()
  await expect(panel.getByText('省份200', { exact: true })).toBeVisible()
  await panel.getByRole('button', { name: '末页' }).click()
  await expect(panel.locator('tbody tr')).toHaveCount(163)
  await expect(panel.getByText(/第 4 页 \/ 共 4 页/)).toBeVisible()
  expect(offsets).toEqual([0, 200, 600])
  await panel.getByLabel('开始日期').fill('2026-05-23')
  await expect(panel.locator('tbody')).toHaveCount(0)
  await panel.getByRole('button', { name: '查询百度数据' }).click()
  await expect(panel.getByText(/第 1 页 \/ 共 4 页/)).toBeVisible()
  expect(offsets.at(-1)).toBe(0)
})

test('地域替身：切换页签中止旧请求，旧结果不能覆盖新兴趣页签', async ({ page }) => {
  await setup(page)
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  let regionStarted = false
  await page.route('**/api/baidu-reports/query', async route => {
    const q = route.request().postDataJSON()
    if (q.report === 'region') { regionStarted = true; await held }
    await route.fulfill({ json: q.report === 'region' ? regionAnswer(q) : answer(q) }).catch(() => {})
  })
  await page.goto('/')
  const panel = await open(page)
  await panel.getByRole('tab', { name: '地域报表' }).click()
  await panel.getByRole('button', { name: '查询百度数据' }).click()
  await expect.poll(() => regionStarted).toBe(true)
  await panel.getByRole('tab', { name: '新兴趣报表' }).click()
  await expect(panel.getByRole('button', { name: '查询百度数据' })).toBeEnabled()
  await panel.getByRole('button', { name: '查询百度数据' }).click()
  await expect(panel.getByText('总记录数：1')).toBeVisible()
  release()
  await expect(panel.getByRole('columnheader', { name: '一级兴趣' })).toBeVisible()
  await expect(panel.getByRole('columnheader', { name: '省份', exact: true })).toHaveCount(0)
})

test('百度真实浏览器：两种报告、地域分页和日期变化', async ({ page }) => {
  test.skip(process.env.BAIDU_REPORT_LIVE !== '1', '仅显式启用时使用后端认证进行真实查询')
  test.setTimeout(120000)
  await page.goto('/')
  const panel = await open(page)
  async function click(name: string) {
    const waiting = page.waitForResponse(r => r.url().endsWith('/api/baidu-reports/query'))
    await panel.getByRole('button', { name, exact: true }).click()
    const response = await waiting
    expect(response.status()).toBe(200)
    return response.json()
  }
  const interest = await click('查询百度数据')
  expect(interest.report_type).toBe(2521394)
  await panel.getByRole('tab', { name: '地域报表' }).click()
  const first = await click('查询百度数据')
  expect(first.report_type).toBe(2324048)
  const second = await click('下一页')
  expect(second.query.start_row).toBe(200)
  const last = await click('末页')
  expect(last.query.start_row).toBe((first.total_pages - 1) * 200)
  expect(last.row_count).toBe(first.total_row_count - last.query.start_row)
  await panel.getByLabel('开始日期').fill('2026-05-23')
  await panel.getByLabel('结束日期').fill('2026-05-23')
  const day = await click('查询百度数据')
  expect(day.query.start_row).toBe(0)
  const beijing = panel.locator('tbody tr').filter({ has: page.getByRole('cell', { name: '北京', exact: true }) })
  await expect(beijing.locator('td').nth(6)).toHaveText('2.42%')
  await expect(beijing.locator('td').nth(7)).toHaveText('2.21')
})

test('Electron built 地域真实查询', async () => {
  test.skip(process.env.BAIDU_REPORT_LIVE !== '1', '仅显式启用时使用真实认证')
  test.setTimeout(90000)
  const env = { ...process.env }; delete env.ELECTRON_RUN_AS_NODE
  const app = await electron.launch({ args: [path.resolve('electron/main.cjs')], env })
  try {
    const page = await app.firstWindow()
    const panel = await open(page)
    await panel.getByRole('tab', { name: '地域报表' }).click()
    const waiting = page.waitForResponse(r => r.url().endsWith('/api/baidu-reports/query'))
    await panel.getByRole('button', { name: '查询百度数据' }).click()
    const response = await waiting
    expect(response.status()).toBe(200)
    const data = await response.json()
    expect(data.report_type).toBe(2324048)
    await expect(panel.locator('tbody tr')).toHaveCount(data.row_count)
    await expect(panel.getByRole('columnheader', { name: '省份', exact: true })).toBeVisible()
  } finally { await app.close() }
})
