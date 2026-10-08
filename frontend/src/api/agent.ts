import type { AgentInput, AgentResult, Scope } from '../types/agent'
const base = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
async function request<T>(path: string, signal: AbortSignal, body?: AgentInput): Promise<T> {
  const response = await fetch(`${base}/api/agent/${path}`, { signal, method: body ? 'POST' : 'GET',
    ...(body ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}) })
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new Error(data?.detail?.message || (response.status === 422 ? '问题或日期条件不合法，请检查输入。' : '智能分析服务不可用。'))
  return data as T
}
export const metadata = (signal: AbortSignal) => request<{ scope: Scope }>('metadata', signal)
export const analyze = (input: AgentInput, signal: AbortSignal) => request<AgentResult>('analyze', signal, input)
