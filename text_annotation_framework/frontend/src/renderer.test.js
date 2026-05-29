import { describe, expect, it } from 'vitest'
import { escapeHtml, renderAnnotatedText } from './renderer'

describe('renderer', () => {
  it('escapes html', () => {
    expect(escapeHtml('<script>"x"</script>')).toBe('&lt;script&gt;&quot;x&quot;&lt;/script&gt;')
  })

  it('renders positioned annotations as clickable marks', () => {
    const html = renderAnnotatedText('A resilient framework.', [
      {
        surface: 'resilient',
        label: '有韧性的',
        type: 'keyword',
        start_index: 2,
        end_index: 11
      }
    ])

    expect(html).toContain('annotation-mark')
    expect(html).toContain('data-annotation-index="0"')
    expect(html).toContain('有韧性的')
  })

  it('skips overlapping annotations', () => {
    const html = renderAnnotatedText('technical framework', [
      { surface: 'technical framework', label: '技术框架', type: 'phrase', start_index: 0, end_index: 19 },
      { surface: 'framework', label: '框架', type: 'keyword', start_index: 10, end_index: 19 }
    ])

    expect(html.match(/annotation-mark/g)).toHaveLength(1)
  })
})
