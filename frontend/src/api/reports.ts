import type { Filters, ReportResponse } from '../types/reports'

const baseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export async function fetchReports(filters: Filters, signal: AbortSignal): Promise<ReportResponse> {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value.trim()) params.set(key, value.trim())
  }
  let response: Response
  try {
    response = await fetch(`${baseUrl}/api/reports/campaigns?${params}`, { signal })
  } catch (error) {
    if (signal.aborted) throw error
    throw new Error('无法连接报表服务，请确认后端已启动并检查请求地址。')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail
    const message = typeof detail === 'string' ? detail : '请检查日期及关键词（最多 100 字）。'
    throw new Error(response.status === 422 ? message : `报表请求失败（HTTP ${response.status}），请稍后重试。`)
  }
  return response.json() as Promise<ReportResponse>
}
