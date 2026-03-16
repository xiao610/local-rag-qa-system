import request from './request'

export const chat = (data) => request.post('/chat', data)