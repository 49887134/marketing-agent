<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { baiduStatus, queryBaidu } from '../api/baiduReports'
import type { BaiduQuery, BaiduReport, BaiduStatus, BaiduReportKind } from '../types/baiduReports'

const start = ref('2026-05-01'), end = ref('2026-06-07'), pageSize = ref(200)
const loading = ref(false), checking = ref(false), error = ref(''), statusError = ref('')
const status = ref<BaiduStatus | null>(null), result = ref<BaiduReport | null>(null)
const report = ref<BaiduReportKind>('interest'), page = ref(1)
const tabs = [{ value: 'interest' as const, label: '新兴趣报表' }, { value: 'region' as const, label: '地域报表' }]
let controller: AbortController | null = null, statusController: AbortController | null = null
let serial = 0, statusSerial = 0
let lastAttempt: BaiduQuery | null = null
const text = (value: string | number | null | undefined) => value == null || value === '' ? '—' : String(value)

function amount(value: string | null) {
  if (value === null || value === '') return '—'
  const unit = result.value!.units.amount
  return (Number(value) / (unit === 'fen' ? 100 : 1)).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function ctr(value: string | null) {
  if (value === null || value === '') return '—'
  const unit = result.value!.units.ctr
  return unit === 'unknown' ? value : `${(Number(value) * (unit === 'ratio' ? 100 : 1)).toFixed(2)}%`
}
async function refreshStatus() {
  const id = ++statusSerial; statusController?.abort()
  const current = new AbortController(); statusController = current
  checking.value = true; statusError.value = ''
  const timer = window.setTimeout(() => current.abort(), 10000)
  try { const data = await baiduStatus(current.signal); if (id === statusSerial) status.value = data }
  catch { if (id === statusSerial) statusError.value = '配置状态读取失败，请检查后端服务。' }
  finally { window.clearTimeout(timer); if (id === statusSerial) checking.value = false }
}
function resetQuery() {
  ++serial; controller?.abort(); loading.value = false
  result.value = null; error.value = ''; page.value = 1; lastAttempt = null
}
watch([report, start, end, pageSize], resetQuery, { flush: 'sync' })
async function load(query: BaiduQuery) {
  if (loading.value) return
  lastAttempt = { ...query }
  const id = ++serial; controller?.abort()
  const current = new AbortController(); controller = current
  result.value = null; error.value = ''
  if (!query.start_date || !query.end_date || query.start_date > query.end_date) {
    error.value = '请填写日期，开始日期不能晚于结束日期。'; return
  }
  loading.value = true
  const timer = window.setTimeout(() => current.abort(), 65000)
  try {
    const data = await queryBaidu(query, current.signal)
    if (id !== serial) return
    result.value = data; page.value = data.page
  } catch (cause) {
    if (id === serial) error.value = current.signal.aborted ? '查询等待超时，请重试。' : cause instanceof Error ? cause.message : '查询失败，请重试。'
  } finally { window.clearTimeout(timer); if (id === serial) loading.value = false }
}
function submit() { page.value = 1; return load({ report: report.value, start_date: start.value, end_date: end.value, start_row: 0, page_size: pageSize.value }) }
function retry() { if (lastAttempt) return load(lastAttempt) }
function goTo(target: number) {
  if (result.value && target >= 1 && target <= result.value.total_pages) return load({ ...result.value.query, start_row: (target - 1) * result.value.query.page_size })
}
onMounted(refreshStatus)
onBeforeUnmount(() => { ++serial; ++statusSerial; controller?.abort(); statusController?.abort() })
</script>

<template>
  <section aria-label="百度投放数据">
    <div class="panel kb-status"><div><h2>百度投放数据 · {{ report === 'region' ? '地域报表' : '新兴趣报表' }}</h2>
      <p><strong>数据来源：百度 API</strong> · {{ result ? '本次查询成功' : '等待查询' }}</p>
      <p class="muted">{{ report === 'region' ? '按日期和省份查看投放表现。' : '一级兴趣（interestsName）是兴趣维度，不是推广计划。' }}</p>
      <p v-if="status">{{ status.configured ? '后端认证配置已填写，点击查询获取当前数据。' : '尚未配置百度营销认证，请在后端 .env 填写后重启。' }}</p>
      <p v-if="statusError" role="alert">{{ statusError }}</p>
    </div><button :disabled="checking || loading" @click="refreshStatus">刷新配置状态</button></div>
    <div class="tabs" role="tablist" aria-label="百度报表类型"><button v-for="tab in tabs" :key="tab.value" role="tab" :aria-selected="report === tab.value" :class="{ primary: report === tab.value }" @click="report = tab.value">{{ tab.label }}</button></div>
    <form class="panel filter-panel" @submit.prevent="submit">
      <label>开始日期<input v-model="start" type="date" required /></label>
      <label>结束日期<input v-model="end" type="date" required /></label>
      <label>每页条数<select v-model.number="pageSize"><option :value="20">20</option><option :value="50">50</option><option :value="200">200</option></select></label>
      <button class="primary" :disabled="loading">查询百度数据</button>
    </form>
    <p class="muted">金额显示两位小数；单位未确认时不换算或添加币种。地域 CTR 按小数转为百分比。切换报表或修改条件后回到第一页，请重新查询。</p>
    <div aria-live="polite" :aria-busy="loading">
      <div v-if="loading" class="panel state"><h2>正在查询百度 API…</h2><p>请等待本次查询完成。</p></div>
      <div v-else-if="error" class="panel state error" role="alert"><h2>百度数据查询失败</h2><p>{{ error }}</p><button @click="retry">重试查询</button></div>
      <section v-else-if="result" class="panel report-panel">
        <div class="report-heading"><div><h2>百度报告明细</h2><p>{{ result.query.start_date }} 至 {{ result.query.end_date }} · 数据来源：百度 API</p></div><span class="count">总记录数：{{ result.total_row_count }}</span></div>
        <div v-if="!result.rows.length" class="state"><h3>暂无数据</h3><p>百度 API 本次返回零条记录，请调整日期后重新查询。</p></div>
        <div v-else class="table-scroll"><table><thead><tr><th>日期</th><th>账户</th><th>{{ report === 'region' ? '省份' : '一级兴趣' }}</th><th>展现量</th><th>点击量</th><th>消耗（{{ result.units.amount === 'unknown' ? '单位待确认' : '元' }}）</th><th>CTR（{{ result.units.ctr === 'unknown' ? '原始值' : '%' }}）</th><th>CPC（{{ result.units.amount === 'unknown' ? '单位待确认' : '元' }}）</th><th>CPM（{{ result.units.amount === 'unknown' ? '单位待确认' : '元' }}）</th></tr></thead>
          <tbody><tr v-for="(row, index) in result.rows" :key="result.query.start_row + index"><td>{{ text(row.date) }}</td><td>{{ text(row.userName) }}</td><td>{{ text(report === 'region' ? row.provinceName : row.interestsName) }}</td><td>{{ text(row.impression) }}</td><td>{{ text(row.click) }}</td><td>{{ amount(row.cost) }}</td><td>{{ ctr(row.ctr) }}</td><td>{{ amount(row.cpc) }}</td><td>{{ amount(row.cpm) }}</td></tr></tbody></table></div>
        <div class="pager"><span>第 {{ page }} 页 / 共 {{ result.total_pages }} 页 · 本页 {{ result.row_count }} 条<span v-if="result.row_count"> · 第 {{ result.query.start_row + 1 }}–{{ result.query.start_row + result.row_count }} 条</span></span><button :disabled="loading || page <= 1" @click="goTo(1)">首页</button><button :disabled="loading || page <= 1" @click="goTo(page - 1)">上一页</button><button :disabled="loading || result.next_start_row === null" @click="goTo(page + 1)">下一页</button><button :disabled="loading || page >= result.total_pages" @click="goTo(result.total_pages)">末页</button></div>
        <p class="table-footnote">CTR：点击率；CPC：平均点击价格；CPM：千次展现消费。这里展示百度返回值，不对分页数据进行全量汇总。</p>
      </section>
    </div>
  </section>
</template>

<style scoped>
select { height: 40px; border: 1px solid #d9e0ea; border-radius: 5px; background: white; color: #344258; padding: 8px 12px; }
.pager { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; padding: 18px 22px; }
.pager span { margin-right: auto; }
td { overflow-wrap: anywhere; }
.tabs { display: flex; gap: 12px; margin-bottom: 18px; }
</style>
