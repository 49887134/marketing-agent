export const integer = (value: number) => value.toLocaleString('zh-CN')
export const money = (value: string | null) => value === null ? '—' : Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
export const percent = (value: number | null) => value === null ? '—' : `${(value * 100).toFixed(2)}%`
