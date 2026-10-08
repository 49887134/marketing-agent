import type { BaiduQuery, BaiduReport, BaiduStatus } from '../types/baiduReports'
const base = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

async function request<T>(path: string, signal: AbortSignal, body?: BaiduQuery): Promise<T> {
  const response = await fetch(`${base}/api/baidu-reports/${path}`, {
    signal, method: body ? 'POST' : 'GET',
    ...(body ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}),
  })
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new Error(data?.detail?.message || (response.status === 422 ? '查询条件不合法：请检查日期顺序、731天范围限制及分页参数。' : '百度投放数据服务不可用，请重试。'))
  if (!data) throw new Error('后端未返回有效数据。')
  return data as T
}
export const baiduStatus = (signal: AbortSignal) => request<BaiduStatus>('status', signal)
export const queryBaidu = (query: BaiduQuery, signal: AbortSignal) => request<BaiduReport>('query', signal, query)
