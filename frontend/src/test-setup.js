import '@testing-library/jest-dom'

const storage = new Map()
const localStorageMock = {
  getItem: key => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, String(value)),
  removeItem: key => storage.delete(key),
  clear: () => storage.clear(),
}

Object.defineProperty(globalThis, 'localStorage', {
  configurable: true,
  value: localStorageMock,
})
Object.defineProperty(window, 'localStorage', {
  configurable: true,
  value: localStorageMock,
})
