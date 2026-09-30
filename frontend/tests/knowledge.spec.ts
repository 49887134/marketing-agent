import { test, expect, _electron as electron, type Page } from '@playwright/test'
import path from 'node:path'

// UI 合约测试使用明确的替身响应，不证明远程数据库或模型成功。
const chunk = { chunk_id: 'mock-chunk', document_id: 'lesson2/mock', title: '测试资料', source: 'data/knowledge/mock.md', section: '汇总 CTR', ordinal: 1, content: '汇总 CTR 使用总点击除以总展现。', content_hash: 'test-hash', document_hash: 'test-doc-hash', similarity: 0.82 }
const response = { question: '汇总 CTR', top_k: 3, min_similarity: 0.35, chunks: [chunk], status: 'answered', answer: '汇总 CTR 使用总点击除以总展现。', citations: [chunk] }

async function mockStatus(page: Page) {
  await page.route('**/api/knowledge/status', route => route.fulfill({ json: { ready: true, code: 'ready', message: '测试替身状态', document_count: 4, chunk_count: 12, embedding_model: 'mock', dimensions: 3 } }))
}

test('知识 UI Mock：引用、原文、top_k、依据不足及失败重试', async ({ page }) => {
  await mockStatus(page)
  let mode = 'answered'
  await page.route('**/api/knowledge/ask', async route => {
    if (mode === 'failed') return route.fulfill({ status: 502, json: { detail: { code: 'model_unavailable', message: '模型调用失败，请重试。' } } })
    await route.fulfill({ json: mode === 'insufficient' ? { ...response, status: 'insufficient_evidence', answer: '现有资料依据不足。', citations: [] } : response })
  })
  await page.route('**/api/knowledge/search', route => {
    expect(route.request().postDataJSON().top_k).toBe(1)
    return route.fulfill({ json: { ...response, top_k: 1 } })
  })
  await page.goto('/')
  await page.locator('.sidebar').getByRole('button', { name: '知识问答' }).click()
  await expect(page.getByText('已就绪 · 4 份文档 · 12 个片段')).toBeVisible()
  await page.getByRole('button', { name: '提问', exact: true }).click()
  await expect(page.getByRole('heading', { name: '引用依据' })).toBeVisible()
  await expect(page.locator('blockquote')).toHaveText(chunk.content)
  await page.getByLabel('检索片段数 top_k').fill('1')
  await page.getByRole('button', { name: '仅检索' }).click()
  await expect(page.getByText(/本次问题：.*top_k=1/)).toBeVisible()
  await expect(page.getByRole('heading', { name: '回答', exact: true })).toHaveCount(0)
  mode = 'insufficient'
  await page.getByRole('button', { name: '提问', exact: true }).click()
  await expect(page.getByRole('heading', { name: '资料依据不足' })).toBeVisible()
  mode = 'failed'
  await page.getByRole('button', { name: '提问', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('模型调用失败')
  mode = 'answered'
  await page.getByRole('button', { name: '重试知识请求' }).click()
  await expect(page.locator('blockquote')).toBeVisible()
  await page.screenshot({ path: '../artifacts/lesson-2-browser-mock.png', fullPage: true })
})

test('知识 UI Mock：未就绪、加载、纯文本转义', async ({ page }) => {
  await page.route('**/api/knowledge/status', route => route.fulfill({ json: { ready: false, code: 'knowledge_not_ready', message: '知识库为空，请由教师入库。', document_count: 0, chunk_count: 0, embedding_model: null, dimensions: null } }))
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/knowledge/ask', async route => {
    await held
    await route.fulfill({ json: { ...response, answer: '<img src=x onerror="window.injected=true">' } })
  })
  await page.goto('/')
  await page.locator('.sidebar').getByRole('button', { name: '知识问答' }).click()
  await expect(page.getByText('未就绪 · 0 份文档 · 0 个片段')).toBeVisible()
  await page.getByRole('button', { name: '提问', exact: true }).click()
  await expect(page.getByRole('heading', { name: '正在检索与处理…' })).toBeVisible()
  release()
  await expect(page.locator('.kb-answer .answer-text')).toContainText('<img')
  expect(await page.evaluate(() => (window as any).injected)).toBeUndefined()
  await expect(page.locator('.kb-answer img')).toHaveCount(0)
})

test('Electron built 知识 UI Mock：问答及引用原文', async () => {
  const env = { ...process.env }
  delete env.ELECTRON_RUN_AS_NODE
  const app = await electron.launch({ args: [path.resolve('electron/main.cjs')], env })
  try {
    const page = await app.firstWindow()
    await mockStatus(page)
    await page.route('**/api/knowledge/ask', route => route.fulfill({ json: response }))
    await page.locator('.sidebar').getByRole('button', { name: '知识问答' }).click()
    await page.getByRole('button', { name: '提问', exact: true }).click()
    await expect(page.locator('blockquote')).toHaveText(chunk.content)
    expect(page.url()).toBe('app://dashboard/index.html')
    await page.screenshot({ path: '../artifacts/lesson-2-electron-mock.png', fullPage: true })
  } finally { await app.close() }
})
