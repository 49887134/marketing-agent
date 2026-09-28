<script setup lang="ts">
import { reactive } from 'vue'
import type { Filters } from '../types/reports'

const props = defineProps<{ defaults: Filters }>()
const emit = defineEmits<{ query: [filters: Filters] }>()
const form = reactive({ ...props.defaults })
function submit() { emit('query', { ...form }) }
function reset() { Object.assign(form, props.defaults); submit() }
</script>

<template>
  <form class="filter-panel panel" @submit.prevent="submit">
    <label>开始日期<input v-model="form.start_date" type="date" aria-label="开始日期" /></label>
    <label>结束日期<input v-model="form.end_date" type="date" aria-label="结束日期" /></label>
    <label class="keyword">计划名称<input v-model="form.keyword" maxlength="100" placeholder="输入计划名称关键词" aria-label="计划名称关键词" /></label>
    <div class="filter-actions">
      <button type="submit" class="primary">查询</button>
      <button type="button" @click="reset">重置</button>
    </div>
  </form>
</template>
