export async function fetchSettings() {
  const res = await fetch('/api/settings')
  if (!res.ok) throw new Error(`获取设置失败: ${res.status}`)
  return res.json()
}

export async function saveSettings(payload) {
  const res = await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    throw new Error(err?.detail || `保存设置失败: ${res.status}`)
  }
  return res.json()
}
