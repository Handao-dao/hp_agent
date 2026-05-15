const escapeHtml = (value = '') => {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

export const formatAnnotatedText = (annotatedText = '', masteredWords = new Set()) => {
  let text = escapeHtml(annotatedText ?? '')

  text = text.replace(
    /\[\[(.+?)\|(.+?)\]\]/g,
    (_, word, translation) => {
      if (masteredWords.has(word.toLowerCase())) {
        return word
      }
      return `<span class="vocab-word" data-word="${word}">${word}</span><span class="translation">(${translation})</span>`
    }
  )

  return text
    .split(/\n+/)
    .map(p => p.trim())
    .filter(Boolean)
    .map(p => `<p>${p}</p>`)
    .join('')
}
