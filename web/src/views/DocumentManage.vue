<template>
  <div>
    <!-- 面包屑导航 -->
    <el-breadcrumb separator="/" style="margin-bottom: 20px;">
      <el-breadcrumb-item :to="{ path: '/documents' }">文件管理</el-breadcrumb-item>
      <el-breadcrumb-item v-if="currentKbName">{{ currentKbName }}</el-breadcrumb-item>
    </el-breadcrumb>

    <!-- 知识库选择 -->
    <div style="margin-bottom: 20px;">
      <el-select v-model="kbId" placeholder="选择知识库" @change="handleKbChange" style="width: 300px;">
        <el-option
          v-for="kb in kbList"
          :key="kb.collection_name"
          :label="kb.display_name"
          :value="kb.display_name"
        />
      </el-select>
    </div>

    <!-- 文件列表操作栏 -->
    <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索文件"
        prefix-icon="Search"
        style="width: 300px;"
        clearable
      />
    </div>

    <!-- 文件表格 -->
    <el-table :data="filteredFileList" stripe style="width: 100%">
      <el-table-column prop="name" label="名称" min-width="200" />
      <el-table-column prop="uploadDate" label="上传日期" width="160" />
      <el-table-column prop="size" label="大小" width="100">
        <template #default="{ row }">{{ formatSize(row.size) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button-group>
            <el-button type="primary" size="small" :icon="Download" @click="handleDownload(row)" />
            <el-button type="danger" size="small" :icon="Delete" @click="handleDelete(row)" />
          </el-button-group>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div style="margin-top: 20px; text-align: right;">
      <el-pagination
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 上传文件对话框（代码保持不变，请保留原有内容） -->
    <el-dialog v-model="uploadDialogVisible" title="上传文件" width="500px">
      <!-- 原有上传对话框内容，包括文件选择、切片参数等 -->
      <!-- 此处省略，请保留您之前的代码 -->
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Delete, Search } from '@element-plus/icons-vue'
import { getDocList, deleteDoc, uploadDocs, downloadDoc } from '@/api/document'
import { listKb } from '@/api/kb'

// 知识库列表
const kbList = ref([])
const kbId = ref('')
const currentKbName = ref('')

// 文件列表
const fileList = ref([])
const searchKeyword = ref('')
const total = ref(0)
const pageSize = ref(10)
const currentPage = ref(1)

// 上传对话框（请确保原有变量和函数完整）
const uploadDialogVisible = ref(false)
// ... 其他上传相关变量（chunkSize, chunkOverlap 等）请保留

// 过滤文件列表
const filteredFileList = computed(() => {
  if (!searchKeyword.value) return fileList.value
  return fileList.value.filter(f => f.name.includes(searchKeyword.value))
})

// 加载知识库列表
const loadKbList = async () => {
  try {
    const res = await listKb()
    kbList.value = res.kb_list || []
    if (kbList.value.length > 0 && !kbId.value) {
      kbId.value = kbList.value[0].display_name
      currentKbName.value = kbId.value
    }
  } catch (error) {
    ElMessage.error('获取知识库列表失败')
  }
}

// 知识库切换
const handleKbChange = (val) => {
  currentKbName.value = val
  loadFiles()
}

// 加载文件列表
const loadFiles = async () => {
  if (!kbId.value) return
  try {
    const res = await getDocList(kbId.value)
    fileList.value = (res.documents || []).map(doc => ({
      name: doc.document,
      uploadDate: doc.upload_time ? new Date(doc.upload_time * 1000).toLocaleString() : '未知',
      size: doc.file_size || 0,
      raw: doc
    }))
    total.value = fileList.value.length
  } catch (error) {
    ElMessage.error('获取文件列表失败')
  }
}

// 格式化文件大小
const formatSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 下载文件（关键修改）
const handleDownload = async (row) => {
  try {
    // 调用下载 API，获取 blob 数据
    const response = await downloadDoc(kbId.value, row.name)
    // 注意：downloadDoc 返回的是 axios 响应，数据在 response.data 中
    const blob = new Blob([response.data], { type: 'application/octet-stream' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = row.name  // 设置文件名
    link.click()
    URL.revokeObjectURL(link.href)
  } catch (error) {
    console.error('下载失败:', error)
    ElMessage.error('下载失败：' + (error.response?.data?.detail || error.message))
  }
}

// 删除文件
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除文件 "${row.name}"？`, '提示')
    await deleteDoc(kbId.value, row.name)
    ElMessage.success('删除成功')
    await loadFiles()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败：' + error.message)
  }
}

// 打开上传对话框（保留原有逻辑）
const openUploadDialog = () => {
  // 重置参数，然后打开对话框
  // selectedFiles.value = []
  // chunkSize.value = 512
  // ...
  uploadDialogVisible.value = true
}

// 分页处理
const handleSizeChange = (val) => {
  pageSize.value = val
}
const handleCurrentChange = (val) => {
  currentPage.value = val
}

onMounted(async () => {
  await loadKbList()
  await loadFiles()
})
</script>

<style scoped>
/* 可自定义样式 */
</style>