<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { askKnowledge, fetchKnowledgeStatus, searchKnowledge } from '../api/knowledge'
import type { AnswerResult, KnowledgeStatus, RetrievalResult } from '../types/knowledge'

const examples = ['为什么汇总 CTR 不能直接平均各行 CTR？', '把每个计划的点击百分比加起来除以计划数，能代表整体表现吗？', '百度推广账户退款需要哪些材料、几个工作日到账？']
const question = ref(examples[0]!)
const topK = ref(3)
const status = ref<KnowledgeStatus | null>(null)
const statusError = ref('')
const checking = ref(false)
const loading = ref(false)
const error = ref('')
const answer = ref<AnswerResult | null>(null)
const retrieval = ref<RetrievalResult | null>(null)
let controller: AbortController | null = null
let statusController: AbortController | null = null
let requestId = 0
let statusId = 0
let lastMode: 'ask' | 'search' = 'ask'

async function refreshStatus() {
  const id = ++statusId
  statusController?.abort()
  const current = new AbortController()
  statusController = current
  checking.value = true
  statusError.value = ''
  const timeout = window.setTimeout(() => current.abort(), 30000)
  try {
    const result = await fetchKnowledgeStatus(current.signal)
    if (id === statusId) status.value = result
  } catch (cause) {
    if (id === statusId) { status.value = null; statusError.value = current.signal.aborted ? '状态检查超时，请重试。' : cause instanceof Error ? cause.message : '状态检查失败。' }
  } finally {
    window.clearTimeout(timeout)
    if (id === statusId) checking.value = false
  }
}

async function submit(mode: 'ask' | 'search' = 'ask') {
  const id = ++requestId
  controller?.abort()
  const current = new AbortController()
  controller = current
  lastMode = mode
  error.value = ''
  answer.value = null
  retrieval.value = null
  if (!question.value.trim() || !Number.isInteger(topK.value) || topK.value < 1 || topK.value > 6) {
    error.value = '请输入问题，并将 top_k 设为 1–6 的整数。'
    loading.value = false
    return
  }
  loading.value = true
  const timeout = window.setTimeout(() => current.abort(), 150000)
  try {
    if (mode === 'ask') {
      const result = await askKnowledge(question.value, topK.value, current.signal)
      if (id !== requestId) return
      answer.value = result
      retrieval.value = result
    } else {
      const result = await searchKnowledge(question.value, topK.value, current.signal)
      if (id !== requestId) return
      retrieval.value = result
    }
  } catch (cause) {
    if (id === requestId) error.value = current.signal.aborted ? '请求超时，请检查网络后重试。' : cause instanceof Error ? cause.message : '请求失败。'
  } finally {
    window.clearTimeout(timeout)
    if (id === requestId) loading.value = false
  }
}

onMounted(refreshStatus)
onBeforeUnmount(() => { ++requestId; ++statusId; controller?.abort(); statusController?.abort() })
</script>

<template>
  <section class="knowledge-panel" aria-label="知识问答">
    <div class="panel kb-status">
      <div><h2>知识库状态</h2><p v-if="checking">正在检查远程知识库…</p><p v-else-if="status">{{ status.ready ? '已就绪' : '未就绪' }} · {{ status.document_count }} 份文档 · {{ status.chunk_count }} 个片段</p><p v-if="status">{{ status.message }}</p><p v-if="statusError" role="alert">{{ statusError }}</p></div>
      <button @click="refreshStatus" :disabled="checking">刷新状态</button>
    </div>
    <form class="panel kb-form" @submit.prevent="submit('ask')">
      <h2>投放知识问答</h2><p class="muted">回答基于知识资料；当前账户实时数字请通过报表查询。</p>
      <label>你的问题<textarea v-model="question" maxlength="1000" rows="3" placeholder="输入投放知识问题"></textarea></label>
      <div class="examples"><button type="button" v-for="example in examples" :key="example" @click="question = example">{{ example }}</button></div>
      <div class="kb-actions"><label>检索片段数 top_k<input v-model.number="topK" type="number" min="1" max="6" step="1"></label><button class="primary" :disabled="loading || !question.trim()">提问</button><button type="button" :disabled="loading || !question.trim()" @click="submit('search')">仅检索</button></div>
    </form>
    <div aria-live="polite" :aria-busy="loading">
      <div class="panel state" v-if="loading"><span class="spinner"></span><h2>正在检索与处理…</h2><p>远程模型可能需要一些时间。</p></div>
      <div class="panel state error" v-else-if="error" role="alert"><h2>知识服务暂不可用</h2><p>{{ error }}</p><button @click="submit(lastMode)">重试知识请求</button></div>
      <template v-else>
        <article v-if="answer" class="panel kb-answer"><h2>{{ answer.status === 'answered' ? '回答' : '资料依据不足' }}</h2><p class="answer-text">{{ answer.answer }}</p>
          <h3 v-if="answer.citations.length">引用依据</h3>
          <div v-for="chunk in answer.citations" :key="chunk.chunk_id" class="citation"><strong>{{ chunk.title }} · {{ chunk.section }}</strong><p class="source">{{ chunk.source }} · {{ chunk.chunk_id }}</p><blockquote>{{ chunk.content }}</blockquote></div>
        </article>
        <details v-if="retrieval" class="panel kb-retrieval" open><summary>检索片段（{{ retrieval.chunks.length }}）</summary><p>本次问题：{{ retrieval.question }} · top_k={{ retrieval.top_k }} · 最低相似度={{ retrieval.min_similarity }}</p><p class="muted">相似度表示向量接近程度，不是答案可信度。以下是达到阈值的候选资料；引用依据是回答实际使用的片段。</p><p v-if="!retrieval.chunks.length">没有达到当前阈值的资料。</p>
          <details v-for="chunk in retrieval.chunks" :key="chunk.chunk_id" class="chunk"><summary>{{ chunk.title }} / {{ chunk.section }} · 相似度 {{ chunk.similarity.toFixed(3) }}</summary><p class="source">{{ chunk.source }} · 第 {{ chunk.ordinal }} 段 · {{ chunk.chunk_id }}</p><p class="answer-text">{{ chunk.content }}</p><p class="source">内容版本：{{ chunk.content_hash }}</p></details>
        </details>
      </template>
    </div>
  </section>
</template>
