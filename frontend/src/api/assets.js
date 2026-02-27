import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const getAssets = (params = {}) => api.get('/assets', { params }).then(r => r.data)

export const addAsset = (data) => api.post('/assets', data).then(r => r.data)

export const checkoutAsset = (id, data) => api.patch(`/assets/${id}/checkout`, data).then(r => r.data)

export const returnAsset = (id, data) => api.patch(`/assets/${id}/return`, data).then(r => r.data)

export const lockAsset = (id, data) => api.patch(`/assets/${id}/lock`, data).then(r => r.data)

export const bulkUpdateNotes = (ids, notes) =>
  api.patch('/assets/notes', { ids, notes }).then(r => r.data)
