import { ref } from 'vue'
import { fetchMasteredWords } from '../api/vocabulary'

const masteredWords = ref(new Set())
let loaded = false

export function useMasteredWords() {
  if (!loaded) {
    loaded = true
    fetchMasteredWords().then(s => { masteredWords.value = s })
  }
  return masteredWords
}
