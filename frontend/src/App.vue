<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import ReportFilters from './components/ReportFilters.vue'
import MetricCards from './components/MetricCards.vue'
import ReportTable from './components/ReportTable.vue'
import { fetchReports } from './api/reports'
import type { Filters, ReportResponse } from './types/reports'

const defaults: Filters = { start_date: '2026-09-01', end_date: '2026-09-07', keyword: '' }
const result = ref<ReportResponse | null>(null)
const loading = ref(false)
const error = ref('')
const applied = ref({ ...defaults })
let lastQuery = { ...defaults }
let controller: AbortController | null = null
let requestId = 0

async function query(filters: Filters) {
  const id = ++requestId
  controller?.abort()
  const current = new AbortController()
  controller = current
  lastQuery = { ...filters }
  error.value = ''
  result.value = null
  loading.value = false
  if (filters.start_date && filters.end_date && filters.start_date > filters.end_date) {
    error.value = '开始日期不能晚于结束日期'
    return
  }
  loading.value = true
  const timeout = window.setTimeout(() => current.abort(), 15000)
  try {
    const data = await fetchReports(filters, current.signal)
    if (id !== requestId) return
    result.value = data
    applied.value = { ...filters }
  } catch (cause) {
    if (id !== requestId) return
    error.value = current.signal.aborted ? '请求超时，请检查服务后重试。' : cause instanceof Error ? cause.message : '请求失败，请重试。'
  } finally {
    window.clearTimeout(timeout)
    if (id === requestId) loading.value = false
  }
}

onMounted(() => query(defaults))
onBeforeUnmount(() => { ++requestId; controller?.abort() })
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand-mark">M<span>·</span></div>
      <div class="sidebar-title">营销运营工作台<small>MARKETING AGENT</small></div>
      <div class="nav-label">运营管理</div>
      <div class="nav-active">▦ <span>投放数据看板</span></div>
    </aside>
    <div class="workspace">
      <header class="topbar"><span>工作台 / 投放报表</span><span class="environment"><i></i> 本地运行环境</span></header>
      <main>
        <div class="page-heading"><div><p class="eyebrow">CAMPAIGN OVERVIEW</p><h1>百度营销智能运营 Agent</h1><p class="subtitle">查看计划每日表现，理解投放数据与核心指标。</p></div><span class="demo-badge">本地数据</span></div>
        <ReportFilters :defaults="defaults" @query="query" />
        <div aria-live="polite" :aria-busy="loading">
          <div v-if="loading" class="panel state"><span class="spinner"></span><h2>正在加载报表…</h2><p>正在获取所选范围内的投放数据</p></div>
          <div v-else-if="error" class="panel state error" role="alert"><h2>报表暂未加载</h2><p>{{ error }}</p><button class="primary" @click="query(lastQuery)">重试</button></div>
          <template v-else-if="result">
            <MetricCards :summary="result.summary" />
            <section class="panel report-panel">
              <div class="report-heading"><div><h2>计划投放明细</h2><p>{{ applied.start_date || '不限开始日期' }} — {{ applied.end_date || '不限结束日期' }}<span v-if="applied.keyword"> · 关键词：{{ applied.keyword }}</span></p></div><span class="count">共 {{ result.total }} 条记录</span></div>
              <div v-if="!result.items.length" class="state"><h2>暂无匹配数据</h2><p>请调整日期或计划名称关键词，或点击重置恢复默认数据范围。</p></div>
              <ReportTable v-else :items="result.items" />
              <div class="table-footnote">一条记录对应一个计划一天的数据。点击率 = 点击量 / 展现量；平均点击成本 = 消费 / 点击量，分母为 0 时显示“—”。</div>
            </section>
          </template>
        </div>
        <footer>数据来源：本地报表服务。</footer>
      </main>
    </div>
  </div>
</template>
