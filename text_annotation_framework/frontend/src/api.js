export async function fetchProfiles() {
  const response = await fetch('/api/profiles')
  if (!response.ok) throw new Error('Failed to load profiles')
  return response.json()
}

export async function annotateStream({ text, profile, onEvent }) {
  // 用 fetch + ReadableStream 读取 POST SSE，避免 EventSource 只能 GET 的限制。
  const response = await fetch('/api/annotate-stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ text, profile, options: {} })
  })

  if (!response.ok || !response.body) {
    throw new Error('Failed to start annotation stream')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''

    for (const rawEvent of events) {
      const line = rawEvent.split('\n').find(item => item.startsWith('data: '))
      if (!line) continue
      onEvent(JSON.parse(line.slice(6)))
    }
  }
}
