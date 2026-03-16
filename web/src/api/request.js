import axios from 'axios'

const request = axios.create({
  baseURL: '/api',  // 使用代理，将请求转发到后端
  timeout: 60000
})

request.interceptors.request.use(
  config => config,
  error => Promise.reject(error)
)

request.interceptors.response.use(
  response => response.data,
  error => Promise.reject(error)
)

export default request