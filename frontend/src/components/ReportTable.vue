<script setup lang="ts">
import type { CampaignReport } from '../types/reports'
import { integer, money, percent } from '../format'
defineProps<{ items: CampaignReport[] }>()
</script>

<template>
  <div class="table-scroll">
    <table>
      <caption class="sr-only">广告计划每日投放数据</caption>
      <thead><tr><th>日期</th><th>计划 ID</th><th>计划名称</th><th class="numeric">展现量</th><th class="numeric">点击量</th><th class="numeric">消费（元）</th><th class="numeric">转化数</th><th class="numeric">点击率</th><th class="numeric">平均点击成本（元）</th></tr></thead>
      <tbody>
        <tr v-for="row in items" :key="`${row.date}-${row.campaign_id}`">
          <td>{{ row.date }}</td><td class="muted">{{ row.campaign_id }}</td><td class="campaign-name">{{ row.campaign_name }}</td>
          <td class="numeric">{{ integer(row.impressions) }}</td><td class="numeric">{{ integer(row.clicks) }}</td><td class="numeric">{{ money(row.cost) }}</td>
          <td class="numeric">{{ integer(row.conversions) }}</td><td class="numeric">{{ percent(row.ctr) }}</td><td class="numeric">{{ money(row.cpc) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
