import type { AnswerResult, KnowledgeStatus, RetrievalResult } from '../types/knowledge'

const baseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

async function request<T>(path: string, signal: AbortSignal, body?: object): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${baseUrl}/api/knowledge/${path}`, {
      signal, method: body ? 'POST' : 'GET',
      ...(body ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}),
    })
  } catch (cause) {
    if (signal.aborted) throw cause
    throw new Error('无法连接知识服务，请检查后端是否运行。')
  }
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(data?.detail?.message || (response.status === 422 ? '请输入 1–1000 字的问题，top_k 为 1–6 的整数。' : `知识服务失败（HTTP ${response.status}）。`))
  }
  return data as T
}

export const fetchKnowledgeStatus = (signal: AbortSignal) => request<KnowledgeStatus>('status', signal)
export const askKnowledge = (question: string, top_k: number, signal: AbortSignal) => request<AnswerResult>('ask', signal, { question, top_k })
export const searchKnowledge = (question: string, top_k: number, signal: AbortSignal) => request<RetrievalResult>('search', signal, { question, top_k })
