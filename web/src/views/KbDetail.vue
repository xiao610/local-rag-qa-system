<template>
  <div>
    <!-- 面包屑导航 -->
    <el-breadcrumb separator="/" style="margin-bottom: 20px;">
      <el-breadcrumb-item :to="{ path: '/kb' }">知识库</el-breadcrumb-item>
      <el-breadcrumb-item>{{ kbName }}</el-breadcrumb-item>
    </el-breadcrumb>

    <!-- 顶部区域：知识库名称、统计、创建时间等 -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="24">
        <div style="display: flex; align-items: center;">
          <h2 style="margin: 0; margin-right: 20px;">{{ kbName }}</h2>
          <el-tag type="info">{{ fileCount }}个文件 {{ totalSize }}KB</el-tag>
          <span style="margin-left: 20px; color: #909399;">创建于 {{ createdAt }}</span>
        </div>
        <div style="margin-top: 10px;">
          <el-alert type="info" :closable="false" show-icon>
            解析成功后才能问答哦。
          </el-alert>
        </div>
      </el-col>
    </el-row>

    <!-- 文件列表操作栏（增加刷新按钮） -->
    <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索文件"
        prefix-icon="Search"
        style="width: 300px;"
        clearable
      />
      <div>
        <el-button @click="refreshFileList" :loading="refreshing">刷新</el-button>
        <el-button type="primary" @click="openUploadDialog">新增文件</el-button>
      </div>
    </div>

    <!-- 文件表格 -->
    <el-table :data="filteredFileList" stripe style="width: 100%">
      <el-table-column prop="name" label="名称" min-width="200" />
      <el-table-column prop="uploadDate" label="上传日期" width="160" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-switch v-model="row.enabled" @change="toggleEnable(row)" />
        </template>
      </el-table-column>
      <el-table-column prop="chunks" label="分块数" width="80" />
      <el-table-column label="解析状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.parseStatus === 'success' ? 'success' : 'info'">
            {{ row.parseStatus === 'success' ? '解析成功' : '解析中' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="动作" width="120">
        <template #default="{ row }">
          <el-dropdown trigger="click" @click.stop>
            <el-button link>
              操作<el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleRetrieve(row)">检索测试</el-dropdown-item>
                <el-dropdown-item @click="handleLog(row)">日志</el-dropdown-item>
                <el-dropdown-item @click="handleConfig(row)">配置</el-dropdown-item>
                <el-dropdown-item divided @click="handleDelete(row)">删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
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

    <!-- 上传文件对话框（保持不变） -->
    <el-dialog v-model="uploadDialogVisible" title="上传文件" width="500px">
      <el-form label-width="100px">
        <el-form-item label="选择文件">
          <el-upload
            ref="uploadRef"
            multiple
            :auto-upload="false"
            :file-list="selectedFiles"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
          >
            <el-button type="primary">点击选择文件</el-button>
            <template #tip>
              <div class="el-upload__tip">支持 pdf/txt/docx</div>
            </template>
          </el-upload>
        </el-form-item>

        <el-form-item label="文本块大小">
          <el-input-number v-model="chunkSize" :min="50" :step="1" placeholder="文本块大小" />
        </el-form-item>

        <el-form-item label="块重叠">
          <el-input-number v-model="chunkOverlap" :min="0" :step="1" placeholder="块重叠" />
        </el-form-item>

        <el-form-item label="自定义分隔符">
          <el-input v-model="separators" placeholder="自定义分隔符（可选）" />
        </el-form-item>

        <el-form-item label="切片模式">
          <el-radio-group v-model="chunkMode">
            <el-radio label="default">递归字符分块模式</el-radio>
            <el-radio label="article">文档结构分块模式</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="uploadDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitUpload" :loading="uploading">确定上传</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, Search } from '@element-plus/icons-vue'
import { getDocList, deleteDoc, uploadDocs } from '@/api/document'

const route = useRoute()
const router = useRouter()
const kbName = ref(route.params.name || '知识库')

const searchKeyword = ref('')
const fileList = ref([])
const total = ref(0)
const pageSize = ref(10)
const currentPage = ref(1)
const refreshing = ref(false)

// 上传对话框相关
const uploadDialogVisible = ref(false)
const selectedFiles = ref([])
const chunkSize = ref(512)
const chunkOverlap = ref(50)
const separators = ref('')
const chunkMode = ref('default')
const uploading = ref(false)
const uploadRef = ref(null)

// 统计信息
const fileCount = computed(() => fileList.value.length)
const totalSize = computed(() => {
  const totalBytes = fileList.value.reduce((sum, f) => sum + (f.size || 0), 0)
  return (totalBytes / 1024).toFixed(2)
})
const createdAt = ref('未知')

// 过滤文件列表
const filteredFileList = computed(() => {
  if (!searchKeyword.value) return fileList.value
  return fileList.value.filter(f => f.name.includes(searchKeyword.value))
})

// 加载文件列表
const loadFiles = async () => {
  refreshing.value = true
  try {
    const res = await getDocList(kbName.value)
    fileList.value = (res.documents || []).map(doc => ({
      name: doc.document,
      uploadDate: doc.upload_time ? new Date(doc.upload_time * 1000).toLocaleString() : '未知',
      enabled: true,
      chunks: doc.chunks || 0,
      // 根据块数判断解析状态：如果有块则成功，否则未完成
      parseStatus: doc.chunks > 0 ? 'success' : 'pending',
      size: doc.file_size || 0,
      raw: doc
    }))
    total.value = fileList.value.length
    if (res.documents && res.documents.length > 0 && res.documents[0].upload_time) {
      createdAt.value = new Date(res.documents[0].upload_time * 1000).toLocaleString()
    }
  } catch (error) {
    ElMessage.error('获取文件列表失败')
  } finally {
    refreshing.value = false
  }
}

// 手动刷新
const refreshFileList = () => {
  loadFiles()
}

// 打开上传对话框
const openUploadDialog = () => {
  selectedFiles.value = []
  chunkSize.value = 512
  chunkOverlap.value = 50
  separators.value = ''
  chunkMode.value = 'default'
  uploadDialogVisible.value = true
}

const handleFileChange = (file, fileList) => {
  selectedFiles.value = fileList
}

const handleFileRemove = (file, fileList) => {
  selectedFiles.value = fileList
}

const submitUpload = async () => {
  if (selectedFiles.value.length === 0) {
    ElMessage.warning('请至少选择一个文件')
    return
  }

  const formData = new FormData()
  selectedFiles.value.forEach(item => {
    formData.append('files', item.raw)
  })
  formData.append('kb_id', kbName.value)
  if (chunkSize.value) formData.append('chunk_size', chunkSize.value)
  if (chunkOverlap.value) formData.append('chunk_overlap', chunkOverlap.value)
  if (separators.value.trim()) formData.append('separators', separators.value.trim())
  formData.append('chunk_mode', chunkMode.value)

  uploading.value = true
  try {
    const res = await uploadDocs(formData)
    ElMessage.success(`上传成功，生成 ${res.chunks_generated} 个文本块`)
    uploadDialogVisible.value = false
    await loadFiles()
  } catch (error) {
    ElMessage.error('上传失败：' + error.message)
  } finally {
    uploading.value = false
  }
}

// 启用开关切换
const toggleEnable = (row) => {
  ElMessage.info(`切换文件 ${row.name} 启用状态为 ${row.enabled}`)
  // TODO: 调用后端接口
}

// 检索测试
const handleRetrieve = (row) => {
  ElMessage.info(`检索测试: ${row.name}`)
}

// 日志
const handleLog = (row) => {
  ElMessage.info(`查看日志: ${row.name}`)
}

// 配置
const handleConfig = (row) => {
  ElMessage.info(`配置: ${row.name}`)
}

// 删除文件
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除文件 "${row.name}"？`, '提示')
    await deleteDoc(kbName.value, row.name)
    ElMessage.success('删除成功')
    await loadFiles()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败：' + error.message)
  }
}

// 分页处理
const handleSizeChange = (val) => {
  pageSize.value = val
  // 可重新加载数据（后端分页需要）
}
const handleCurrentChange = (val) => {
  currentPage.value = val
}

onMounted(() => {
  loadFiles()
})
</script>

<style scoped>
/* 可自定义样式 */
</style>