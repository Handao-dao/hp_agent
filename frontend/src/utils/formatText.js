const escapeHtml = (value = '') => {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

export const formatAnnotatedText = (
  annotatedText = '',
  masteredWords = new Set(),
  manuallyAnnotated = new Map()
) => {
  let text = escapeHtml(annotatedText ?? '')

  text = text.replace(
    /\[\[(.+?)\|(.+?)\]\]/g,
    (_, word, translation) => {
      if (masteredWords.has(word.toLowerCase())) {
        return `<span class="text-word" data-word="${word}">${word}</span>`
      }
      return `<span class="vocab-word" data-word="${word}">${word}</span><span class="translation">(${translation})</span>`
    }
  )

  const wrapPlain = (paragraphHtml) => {
    const parts = paragraphHtml.split(/(<[^>]+>)/g)
    return parts.map(part => {
      if (part.startsWith('<')) return part
      return part.replace(
        /\b([a-zA-Z]+(?:'[a-zA-Z]+)?)\b/g,
        (_, word) => {
          const key = word.toLowerCase()
          if (masteredWords.has(key)) {
            return `<span class="text-word" data-word="${word}">${word}</span>`
          }
          if (manuallyAnnotated.has(key)) {
            const trans = escapeHtml(manuallyAnnotated.get(key))
            return `<span class="vocab-word" data-word="${word}">${word}</span><span class="translation">(${trans})</span>`
          }
          return `<span class="text-word" data-word="${word}">${word}</span>`
        }
      )
    }).join('')
  }

  return text
    .split(/\n+/)
    .map(p => p.trim())
    .filter(Boolean)
    .map(p => `<p>${wrapPlain(p)}</p>`)
    .join('')
}
