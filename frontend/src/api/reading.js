// 创建任务接口

export async function createProcessTask(text, level = 'intermediate') {
  const res = await fetch('/api/create-process-task', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ text, level })
  })

  if (!res.ok) {
    const err = await res.json().catch(() => null)
    throw new Error(err?.detail || '创建处理任务失败')
  }

  return await res.json()
}