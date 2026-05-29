export function escapeHtml(value = '') {
  // 所有渲染都经过转义，避免 v-html 引入 XSS。
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

export function renderAnnotatedText(text = '', annotations = []) {
  // renderer 只依赖原文坐标和 annotations，不关心业务是生词、术语还是实体。
  const positioned = annotations
    .map((annotation, index) => ({ ...annotation, index }))
    .filter(annotation => Number.isInteger(annotation.start_index) && Number.isInteger(annotation.end_index))
    .filter(annotation => annotation.start_index >= 0 && annotation.end_index > annotation.start_index)
    .filter(annotation => annotation.end_index <= text.length)
    .sort((a, b) => {
      // 同一起点优先渲染更长的 span，减少嵌套和重叠造成的 UI 混乱。
      if (a.start_index !== b.start_index) return a.start_index - b.start_index
      return (b.end_index - b.start_index) - (a.end_index - a.start_index)
    })

  const parts = []
  let cursor = 0

  for (const annotation of positioned) {
    // 与已渲染内容重叠的标注先跳过；详情数据仍保留在原始 annotations 中。
    if (annotation.start_index < cursor) continue
    parts.push(escapeHtml(text.slice(cursor, annotation.start_index)))
    const surface = text.slice(annotation.start_index, annotation.end_index)
    parts.push(
      `<button class="annotation-mark" data-annotation-index="${annotation.index}" data-type="${escapeHtml(annotation.type)}">` +
        `${escapeHtml(surface)}<span>${escapeHtml(annotation.label)}</span>` +
      '</button>'
    )
    cursor = annotation.end_index
  }

  parts.push(escapeHtml(text.slice(cursor)))

  return parts
    .join('')
    .split(/\n{2,}/)
    .map(paragraph => paragraph.trim())
    .filter(Boolean)
    .map(paragraph => `<p>${paragraph.replaceAll('\n', '<br>')}</p>`)
    .join('')
}
