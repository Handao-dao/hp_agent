import { computed, ref } from 'vue'

const busySources = ref(new Set())

export function useAppBusy() {
  const isAppBusy = computed(() => busySources.value.size > 0)

  function setBusy(source, busy) {
    const key = String(source || '').trim()
    if (!key) return

    const next = new Set(busySources.value)
    if (busy) {
      next.add(key)
    } else {
      next.delete(key)
    }
    busySources.value = next
  }

  return {
    isAppBusy,
    setBusy,
  }
}
