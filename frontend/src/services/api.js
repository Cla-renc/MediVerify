import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT to every request if present
api.interceptors.request.use(config => {
  const token = localStorage.getItem('mv_access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-refresh on 401
api.interceptors.response.use(
  res => res,
  async err => {
    const original = err.config
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem('mv_refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post(`${BASE_URL}/auth/refresh/`, { refresh })
          localStorage.setItem('mv_access_token', data.access)
          original.headers.Authorization = `Bearer ${data.access}`
          return api(original)
        } catch (_) {
          localStorage.removeItem('mv_access_token')
          localStorage.removeItem('mv_refresh_token')
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(err)
  }
)

// ── Auth ────────────────────────────────────────────────────
export const login = (data) => api.post('/auth/login/', data)
export const register = (data) => api.post('/auth/register/', data)
export const getMe = () => api.get('/auth/me/')
export const getPublicStatistics = () => api.get('/reports/stats/')
export const getVerificationReceipt = (scanId) => api.get(`/verify/receipt/${scanId}/`, {
  responseType: 'blob',
})

export const getCloneAlertSocketURL = () => {
  const apiUrl = new URL(BASE_URL, window.location.origin)
  apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
  apiUrl.pathname = '/ws/clone-alerts/'
  apiUrl.search = ''
  apiUrl.hash = ''
  return apiUrl.toString()
}

// ── Verification ────────────────────────────────────────────
export const verifyCode = (data) => api.post('/verify/', data)

// ── Products & Batches ──────────────────────────────────────
export const getManufacturers = () => api.get('/products/manufacturers/')
export const getProducts = () => api.get('/products/catalog/')
export const createProduct = (data) => api.post('/products/catalog/', data)
export const getBatches = () => api.get('/products/batches/')
export const createBatch = (data) => api.post('/products/batches/', data)
export const generateCodes = (id, qty) => api.post(`/products/batches/${id}/generate_codes/`, { quantity: qty })
export const exportPDF = (id) => api.get(`/products/batches/${id}/export_pdf/`, { responseType: 'blob' })
export const exportCSV = (id) => api.get(`/products/batches/${id}/export_csv/`, { responseType: 'blob' })
export const recallBatch = (id, reason) => api.post(`/products/batches/${id}/recall/`, { reason })

// ── Pharmacy & Inventory ────────────────────────────────────
export const getPharmacies = () => api.get('/pharmacy/pharmacies/')
export const getPharmacyTrustRatings = () => api.get('/pharmacy/pharmacies/trust_ratings/')
export const getInventory = () => api.get('/pharmacy/stock/')
export const addStockByCode = (data) => api.post('/pharmacy/stock/add_by_code/', data)
export const getPharmacyAlerts = () => api.get('/pharmacy/stock/alerts_and_expiry/')

// ── Clone Alerts ────────────────────────────────────────────
export const getCloneAlerts = () => api.get('/verify/clones/alerts/')
export const resolveCloneAlert = (id, status) => api.post(`/verify/clones/alerts/${id}/resolve/`, { status })
export const getCloneModel = () => api.get('/verify/clones/model/')
export const retrainCloneModel = () => api.post('/verify/clones/model/')

// AI features
export const scanPack = (formData) => api.post('/ocr/pack/', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
})
export const askMedicineQuestion = (data) => api.post('/chat/', data)

// ── Reports ─────────────────────────────────────────────────
export const submitReport = (formData) => api.post('/reports/suspicious/', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
})
export const getReports = () => api.get('/reports/suspicious/')
export const getHeatmapData = () => api.get('/reports/heatmap/')
export const getSystemSettings = () => api.get('/reports/settings/')
export const updateSystemSettings = (data) => api.post('/reports/settings/', data)

// ── SMS/USSD Gateway ────────────────────────────────────────
export const simulateUSSD = (text) => api.post('/gateway/ussd/', { text, sessionId: 'sim-001', serviceCode: '*384#', phoneNumber: '+254700000000' })
export const simulateSMS = (text) => api.post('/gateway/sms/', { from: '+254700000000', text })

export default api
