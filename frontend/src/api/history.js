const BASE = '/api/history'

export async function fetchHistoryList({ limit = 20, offset = 0 } = {}) {
  const params = new URLSearchParams()
  params.set('limit', String(limit))
  params.set('offset', String(offset))

  const res = await fetch(`${BASE}?${params}`)
  if (!res.ok) throw new Error(`获取历史列表失败: ${res.status}`)
  return res.json()
}

export async function fetchHistoryDetail(taskId) {
  const res = await fetch(`${BASE}/${taskId}`)
  if (!res.ok) throw new Error(`获取历史详情失败: ${res.status}`)
  return res.json()
}

export async function deleteHistory(taskId) {
  const res = await fetch(`${BASE}/${taskId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`删除历史记录失败: ${res.status}`)
  return res.json()
}
