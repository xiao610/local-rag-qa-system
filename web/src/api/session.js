import request from './request'

export const createSession = (data) => request.post('/sessions', data)
export const listSessions = () => request.get('/sessions')
export const deleteSession = (sessionId) => request.delete(`/sessions/${sessionId}`)
export const getHistory = (sessionId) => request.get(`/sessions/${sessionId}/history`)