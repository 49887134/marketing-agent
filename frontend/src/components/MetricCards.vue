<script setup lang="ts">
import type { Metrics } from '../types/reports'
import { integer, money } from '../format'
defineProps<{ summary: Metrics }>()
</script>

<template>
  <section class="metrics" aria-label="汇总指标">
    <article class="panel metric"><span>展现量</span><strong>{{ integer(summary.impressions) }}</strong><small>次展现</small></article>
    <article class="panel metric"><span>点击量</span><strong>{{ integer(summary.clicks) }}</strong><small>次点击</small></article>
    <article class="panel metric accent"><span>消费金额</span><strong>¥ {{ money(summary.cost) }}</strong><small>人民币元</small></article>
    <article class="panel metric"><span>转化数</span><strong>{{ integer(summary.conversions) }}</strong><small>次转化</small></article>
  </section>
</template>
