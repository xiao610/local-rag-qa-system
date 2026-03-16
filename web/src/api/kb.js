import request from './request'

export const createKb = (kbId) => request.post('/kb/create', null, { params: { kb_id: kbId } })
export const listKb = () => request.get('/kb/list')
export const deleteKb = (kbId) => request.delete(`/kb/${kbId}`)