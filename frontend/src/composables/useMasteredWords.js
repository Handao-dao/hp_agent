import { ref } from 'vue'
import { fetchMasteredWords } from '../api/vocabulary'

const masteredWords = ref(new Set())
let loaded = false

export function useMasteredWords() {
  if (!loaded) {
    loaded = true
    fetchMasteredWords().then(s => {
      masteredWords.value = s
    })
  }
  return masteredWords
}

export function addMasteredWord(word) {
  const key = String(word || '').trim().toLowerCase()
  if (!key) return
  const next = new Set(masteredWords.value)
  next.add(key)
  masteredWords.value = next
}

export function removeMasteredWord(word) {
  const key = String(word || '').trim().toLowerCase()
  if (!key) return
  const next = new Set(masteredWords.value)
  next.delete(key)
  masteredWords.value = next
}
