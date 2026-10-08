<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { analyze, metadata } from '../api/agent'
import type { AgentInput, AgentResult, Scope } from '../types/agent'
import MetricCards from './MetricCards.vue'
import ReportTable from './ReportTable.vue'
import { integer, money, percent } from '../format'

const examples = [
  { label: 'A · 知识规则', question: '为什么汇总 CTR 不能直接平均？' },
  { label: 'B · 综合分析', question: '分析演示日期范围内各计划的投放表现，结合知识库规则，说明哪些问题值得优先检查。' },
  { label: 'C · 能力边界', question: '哪个计划最赚钱？' },
]
const question = ref(examples[0]!.question)
const start = ref(''), end = ref(''), keyword = ref('')
const scope = ref<Scope | null>(null)
const loading = ref(false), checking = ref(false), error = ref(''), scopeError = ref('')
const result = ref<AgentResult | null>(null)
let controller: AbortController | null = null, scopeController: AbortController | null = null
let serial = 0, scopeSerial = 0, lastInput: AgentInput | null = null
const sections = [{ key: 'interpretation', title: '数据解读' }, { key: 'rules', title: '知识规则' }, { key: 'suggestions', title: '检查建议' }] as const
const citedIds = computed(() => new Set(result.value?.analysis ? sections.flatMap(s => result.value!.analysis![s.key].flatMap(i => i.citation_ids)) : []))
const citations = computed(() => result.value?.chunks.filter(c => citedIds.value.has(c.chunk_id)) || [])
const statusLabel = computed(() => ({ completed: '分析完成', partial: '部分完成', unsupported: '当前能力不足', needs_input: '请补充条件', no_data: '查询无数据', insufficient_evidence: '依据不足', error: '分析未完成' }[result.value?.status || ''] || '本次结果'))

async function refreshScope() {
  const id = ++scopeSerial
  scopeController?.abort()
  const current = new AbortController(); scopeController = current
  checking.value = true; scopeError.value = ''
  const timer = window.setTimeout(() => current.abort(), 25000)
  try {
    const data = await metadata(current.signal)
    if (id !== scopeSerial) return
    scope.value = data.scope
    start.value = data.scope.start_date || ''; end.value = data.scope.end_date || ''
  } catch { if (id === scopeSerial) scopeError.value = '无法获取演示范围，请检查后端或数据库并重试。' }
  finally { window.clearTimeout(timer); if (id === scopeSerial) checking.value = false }
}
async function submit(retry = false) {
  if (loading.value) return
  const input: AgentInput = retry && lastInput ? structuredClone(lastInput) : { question: question.value, filters: { start_date: start.value || null, end_date: end.value || null, keyword: keyword.value } }
  error.value = ''; result.value = null
  if (!input.question.trim() || (input.filters.start_date && input.filters.end_date && input.filters.start_date > input.filters.end_date)) {
    error.value = '请输入问题，并确保开始日期不晚于结束日期。'; return
  }
  lastInput = structuredClone(input)
  const id = ++serial; controller?.abort()
  const current = new AbortController(); controller = current
  loading.value = true
  const timer = window.setTimeout(() => current.abort(), 135000)
  try {
    const data = await analyze(input, current.signal)
    if (id === serial) result.value = data
  } catch (cause) {
    if (id === serial) error.value = current.signal.aborted ? '分析请求超时，请重试。' : cause instanceof Error ? cause.message : '请求失败，请检查后端服务。'
  } finally { window.clearTimeout(timer); if (id === serial) loading.value = false }
}
onMounted(refreshScope)
onBeforeUnmount(() => { ++serial; ++scopeSerial; controller?.abort(); scopeController?.abort() })
</script>

<template>
  <section aria-label="智能分析">
    <div class="panel kb-status"><div><h2>模拟数据 · AI Agent 投放分析助手</h2>
      <p v-if="scope">可查询范围：{{ scope.start_date || '无数据' }} 至 {{ scope.end_date || '无数据' }} · {{ scope.rows }} 条日报</p>
      <p v-if="scope && !scope.simulated" role="alert">数据源已发生变化，请先确认数据性质；本课按模拟数据演示。</p>
      <p v-if="checking">正在读取演示范围…</p><p v-if="scopeError" role="alert">{{ scopeError }}</p>
      <p class="muted">仅查询报表与知识。最近七天按当前日期计算，超出演示范围会提示，不会自动改日期。</p>
    </div><button :disabled="checking || loading" @click="refreshScope">刷新演示范围</button></div>
    <form class="panel kb-form" @submit.prevent="submit()">
      <label>分析需求<textarea v-model="question" :disabled="loading" rows="3" maxlength="1000" /></label>
      <div class="examples"><button v-for="example in examples" :key="example.label" type="button" :disabled="loading" @click="question = example.question">{{ example.label }}</button></div>
      <div class="agent-filters">
        <label>分析开始日期<input v-model="start" type="date" :disabled="loading" /></label>
        <label>分析结束日期<input v-model="end" type="date" :disabled="loading" /></label>
        <label>分析计划名称<input v-model="keyword" maxlength="100" :disabled="loading" placeholder="留空查询所有计划" /></label>
        <button class="primary" :disabled="loading || !question.trim()">开始分析</button>
      </div>
      <p class="muted">问题中的明确日期优先；没有日期时使用表单条件。知识问题不需要报表日期。</p>
    </form>
    <div aria-live="polite" :aria-busy="loading">
      <div v-if="loading" class="panel state"><h2>正在执行分析请求…</h2><p>最多等待两分钟。执行记录在请求完成后一次性返回。</p></div>
      <div v-if="error" class="panel state error" role="alert"><p>{{ error }}</p><button @click="submit(true)">重试分析</button></div>
      <template v-if="result">
        <article class="panel kb-answer"><h2>{{ statusLabel }}</h2><p>{{ result.message }}</p><p class="muted">{{ result.notice }}</p>
          <div v-for="err in result.errors" :key="err.code + err.tool" role="alert"><strong>{{ err.tool || '分析流程' }} · {{ err.code }}</strong><p>{{ err.message }}</p></div>
          <button v-if="['error','partial'].includes(result.status)" :disabled="loading" @click="submit(true)">重试分析</button>
          <template v-if="result.analysis"><section v-for="group in sections" :key="group.key"><h3>{{ group.title }}</h3>
            <p v-if="!result.analysis[group.key].length" class="muted">本次没有可验证的相关结论。</p>
            <div v-for="(item, i) in result.analysis[group.key]" :key="i"><p class="answer-text">{{ item.text }}</p><p class="source">事实依据：{{ item.fact_ids.join('、') || '无' }} · 知识引用：{{ item.citation_ids.join('、') || '无' }}</p></div>
          </section><h3>限制与待补充信息</h3><p v-for="item in result.analysis.limitations" :key="item">{{ item }}</p></template>
        </article>
        <section class="panel kb-answer"><h2>本次执行记录</h2><p class="muted">原生工具调用；仅显示实际执行事件，不包含内部思维链。</p>
          <p v-if="!result.events.length">本次未执行工具。</p>
          <div v-for="event in result.events" :key="event.id" class="citation"><strong>{{ event.name }} · {{ event.status === 'success' ? '成功' : '失败' }}</strong>
            <pre>{{ JSON.stringify(event.arguments, null, 2) }}</pre><p>{{ event.summary }}</p><small>耗时 {{ event.elapsed_ms }} ms</small></div>
        </section>
        <section v-for="(report, i) in result.reports" :key="i" class="panel kb-answer"><h2>报表数据依据</h2><p>{{ report.filters.start_date }} 至 {{ report.filters.end_date }} · {{ report.filters.keyword || '所有计划' }} · {{ report.total }} 条</p>
          <MetricCards :summary="report.summary" /><p v-if="!report.total">查询无数据，请调整计划名称或日期条件。</p>
          <div class="table-scroll"><table><caption>计划汇总（后端计算）</caption><thead><tr><th>事实 ID / 计划</th><th>展现</th><th>点击</th><th>消费</th><th>转化</th><th>CTR</th><th>CPC</th></tr></thead>
            <tbody><tr v-for="fact in report.facts" :key="fact.fact_id"><td class="fact-label"><strong>{{ fact.campaign_name }}</strong><small>{{ fact.fact_id }}</small></td><td>{{ integer(fact.impressions) }}</td><td>{{ integer(fact.clicks) }}</td><td>{{ money(fact.cost) }}</td><td>{{ integer(fact.conversions) }}</td><td>{{ percent(fact.ctr) }}</td><td>{{ money(fact.cpc) }}</td></tr></tbody></table></div>
          <details><summary>核对原始日报</summary><ReportTable :items="report.items" /></details>
        </section>
        <section v-if="citations.length" class="panel kb-answer"><h2>知识引用</h2><article v-for="chunk in citations" :key="chunk.chunk_id" class="citation"><strong>{{ chunk.title }} · {{ chunk.section }}</strong><p class="source">{{ chunk.source }} · {{ chunk.chunk_id }} · 相似度 {{ chunk.similarity.toFixed(3) }}（不是正确率）</p><blockquote>{{ chunk.content }}</blockquote></article></section>
        <details v-if="result.chunks.length" class="panel kb-retrieval"><summary>本次全部候选资料（{{ result.chunks.length }}）</summary><article v-for="chunk in result.chunks" :key="chunk.chunk_id"><p>{{ chunk.title }} · {{ chunk.section }}</p><p class="source">{{ chunk.source }} · {{ chunk.chunk_id }}</p><blockquote>{{ chunk.content }}</blockquote></article></details>
      </template>
    </div>
  </section>
</template>

<style scoped>
.agent-filters { display: flex; flex-wrap: wrap; gap: 16px; align-items: end; }
.agent-filters label { flex: 1; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #f7f9fc; padding: 12px; }
h3 { margin-top: 24px; }
.fact-label { min-width: 170px; max-width: 250px; white-space: normal; overflow-wrap: anywhere; }
.fact-label small { display: block; margin-top: 6px; color: #65748b; }
</style>
