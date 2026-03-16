import request from './request'
import axios from 'axios'  // 下载需使用原生 axios 以获取 blob

// 上传文档
export const uploadDocs = (formData) => request.post('/docs/upload', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
})

// 获取文档列表
export const getDocList = (kbId) => request.get('/docs/list', { params: { kb_id: kbId } })

// 删除文档
export const deleteDoc = (kbId, docName) => request.delete('/docs/delete', { params: { kb_id: kbId, doc_name: docName } })

// 获取知识库状态
export const getKbStatus = (kbId) => request.get('/docs/status', { params: { kb_id: kbId } })

// 下载文档（使用原生 axios，避免响应拦截器干扰 blob）
export const downloadDoc = (kbId, docName) => {
  return axios.get('/api/docs/download', {
    params: { kb_id: kbId, doc_name: docName },
    responseType: 'blob',
    baseURL: ''  // 如果配置了代理，可留空；否则填写完整后端地址
  })
}