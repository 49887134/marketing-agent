import type { Filters, Metrics, CampaignReport } from './reports'
import type { KnowledgeChunk } from './knowledge'

export interface Scope { start_date: string | null; end_date: string | null; rows: number; simulated: boolean }
export interface AgentInput { question: string; filters: { start_date: string | null; end_date: string | null; keyword: string } }
export interface Insight { text: string; fact_ids: string[]; citation_ids: string[] }
export interface AgentResult {
  status: string; message: string; mode: string; notice: string; scope: Scope
  events: { id: string; name: string; arguments: Record<string, unknown>; status: string; summary: string; elapsed_ms: number }[]
  reports: { filters: Filters; total: number; summary: Metrics; items: CampaignReport[]; facts: (Metrics & { fact_id: string; campaign_id: string; campaign_name: string })[] }[]
  chunks: KnowledgeChunk[]; errors: { code: string; message: string; tool?: string }[]
  analysis: { interpretation: Insight[]; rules: Insight[]; suggestions: Insight[]; limitations: string[] } | null
}
