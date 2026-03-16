<template>
  <div>
    <!-- 标题和创建按钮 -->
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
      <h2 style="margin: 0;">知识库</h2>
      <el-button type="primary" @click="openCreateDialog">创建知识库</el-button>
    </div>

    <!-- 知识库卡片列表 -->
    <el-row :gutter="20">
      <el-col :span="6" v-for="kb in paginatedKbList" :key="kb.name" style="margin-bottom: 20px;">
        <el-card
          shadow="hover"
          style="border-radius: 8px; cursor: pointer;"
          @click="goToKbDetail(kb.name)"
        >
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <h3 style="margin: 0;">{{ kb.name }}</h3>
            <el-dropdown trigger="click" @click.stop>
              <el-button link :icon="MoreFilled" @click.stop />
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click.stop="editKb(kb.name)">编辑</el-dropdown-item>
                  <el-dropdown-item @click.stop="deleteKb(kb.name)">删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <div style="margin-top: 10px; color: #606266;">
            <div>{{ kb.fileCount }} 个文件</div>
            <div style="font-size: 13px;">{{ kb.updateTime }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 分页组件 -->
    <div style="margin-top: 20px; text-align: right;">
      <el-pagination
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        :page-size="pageSize"
        :current-page="currentPage"
        :page-sizes="[12, 24, 48]"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 创建知识库对话框 -->
    <el-dialog v-model="dialogVisible" title="创建知识库" width="400px">
      <el-input v-model="newKbName" placeholder="请输入知识库名称" />
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="createKb">创建</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MoreFilled } from '@element-plus/icons-vue'
import { listKb, createKb as apiCreateKb, deleteKb as apiDeleteKb } from '@/api/kb'
import { getDocList } from '@/api/document'

const router = useRouter()
const kbList = ref([])
const total = ref(0)
const pageSize = ref(12)
const currentPage = ref(1)
const dialogVisible = ref(false)
const newKbName = ref('')

// 计算当前页要显示的数据
const paginatedKbList = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return kbList.value.slice(start, end)
})

// 加载知识库列表
const loadKbList = async () => {
  try {
    const res = await listKb()
    const items = res.kb_list || []
    const enhancedList = []
    for (const item of items) {
      // 处理对象格式：{ collection_name, display_name }
      const collectionName = item.collection_name || item
      const displayName = item.display_name || collectionName

      let fileCount = 0
      let updateTime = '未知'
      try {
        const docRes = await getDocList(displayName)
        fileCount = docRes.documents?.length || 0
        if (docRes.documents && docRes.documents.length > 0) {
          const lastDoc = docRes.documents[docRes.documents.length - 1]
          updateTime = lastDoc.upload_time
            ? new Date(lastDoc.upload_time * 1000).toLocaleString()
            : '未知'
        } else {
          updateTime = '暂无文件'
        }
      } catch (e) {
        // 忽略错误
      }
      enhancedList.push({ name: displayName, fileCount, updateTime })
    }
    kbList.value = enhancedList
    total.value = enhancedList.length
    if (currentPage.value > Math.ceil(total.value / pageSize.value)) {
      currentPage.value = 1
    }
  } catch (error) {
    ElMessage.error('获取知识库列表失败')
  }
}

const goToKbDetail = (kbName) => {
  router.push({ name: 'KbDetail', params: { name: kbName } })
}

const createKb = async () => {
  if (!newKbName.value.trim()) {
    ElMessage.warning('请输入知识库名称')
    return
  }
  try {
    await apiCreateKb(newKbName.value)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    newKbName.value = ''
    loadKbList()
  } catch (error) {
    ElMessage.error('创建失败：' + error.message)
  }
}

const deleteKb = async (name) => {
  try {
    await ElMessageBox.confirm(`确认删除知识库 "${name}"？`, '提示')
    await apiDeleteKb(name)
    ElMessage.success('删除成功')
    loadKbList()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败：' + error.message)
  }
}

const editKb = (name) => {
  ElMessage.info('编辑功能暂未实现')
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
}

const handleCurrentChange = (val) => {
  currentPage.value = val
}

const openCreateDialog = () => {
  dialogVisible.value = true
}

onMounted(() => {
  loadKbList()
})
</script>

<style scoped>
.el-card {
  transition: all 0.3s;
}
.el-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
</style>