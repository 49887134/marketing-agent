export interface Filters {
  start_date: string
  end_date: string
  keyword: string
}

export interface Metrics {
  impressions: number
  clicks: number
  cost: string // 人民币元，后端 Decimal 序列化为字符串
  conversions: number
  ctr: number | null
  cpc: string | null
}

export interface CampaignReport extends Metrics {
  date: string
  campaign_id: string
  campaign_name: string
}

export interface ReportResponse {
  items: CampaignReport[]
  summary: Metrics
  total: number
}
