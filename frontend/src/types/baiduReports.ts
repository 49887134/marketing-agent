export type BaiduReportKind = 'interest' | 'region'
export interface BaiduQuery { report?: BaiduReportKind; start_date: string; end_date: string; start_row: number; page_size: number }
export interface BaiduUnits { amount: 'unknown' | 'yuan' | 'fen'; ctr: 'unknown' | 'ratio' | 'percent' }
export interface BaiduRow {
  date: string | null; userName: string | null; interestsName?: string | null; provinceName?: string | null
  impression: number | null; click: number | null
  cost: string | null; ctr: string | null; cpc: string | null; cpm: string | null
}
export interface BaiduReport {
  source: 'baidu_api'; report_type: number; query: BaiduQuery; units: BaiduUnits
  rows: BaiduRow[]; row_count: number; total_row_count: number; next_start_row: number | null
  page: number; total_pages: number
}
export interface BaiduStatus { configured: boolean; integration_status: string; units: BaiduUnits }
