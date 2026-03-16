<template>
  <div>
    <h2>会话管理</h2>
    <el-card>
      <template #header>创建会话</template>
      <el-input v-model="newSessionName" placeholder="会话名称" style="width: 200px; margin-right: 10px;" />
      <el-select v-model="newSessionKb" placeholder="知识库" style="width: 200px; margin-right: 10px;">
        <el-option v-for="kb in kbList" :key="kb" :label="kb" :value="kb" />
      </el-select>
      <el-button type="primary" @click="createSession">创建</el-button>
    </el-card>
    <el-card style="margin-top: 20px;">
      <template #header>所有会话</template>
      <el-table :data="sessions" stripe>
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="message_count" label="消息数" width="100" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button size="small" @click="viewHistory(row.id)">历史</el-button>
            <el-button type="danger" size="small" @click="deleteSession(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-drawer v-model="drawerVisible" title="历史消息" size="50%">
        <div v-for="msg in historyMessages" :key="msg.timestamp" style="margin-bottom: 10px;">
          <strong>{{ msg.role }}:</strong> {{ msg.content }}
        </div>
      </el-drawer>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listSessions, createSession, deleteSession, getHistory } from '@/api/session'
import { listKb } from '@/api/kb'

const sessions = ref([])
const kbList = ref(['default'])
const newSessionName = ref('新对话')
const newSessionKb = ref('default')
const drawerVisible = ref(false)
const historyMessages = ref([])

const loadSessions = async () => {
  try {
    sessions.value = await listSessions()
  } catch (error) {
    ElMessage.error('获取会话列表失败')
  }
}

const loadKbList = async () => {
  try {
    const res = await listKb()
    kbList.value = res.kb_list || ['default']
  } catch (error) {
    ElMessage.error('获取知识库列表失败')
  }
}

const createSession = async () => {
  try {
    await createSession({ name: newSessionName.value, kb_id: newSessionKb.value })
    ElMessage.success('创建成功')
    loadSessions()
  } catch (error) {
    ElMessage.error('创建失败：' + error.message)
  }
}

const deleteSession = async (id) => {
  try {
    await ElMessageBox.confirm('确认删除该会话？', '提示')
    await deleteSession(id)
    ElMessage.success('删除成功')
    loadSessions()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败：' + error.message)
  }
}

const viewHistory = async (id) => {
  try {
    historyMessages.value = await getHistory(id)
    drawerVisible.value = true
  } catch (error) {
    ElMessage.error('获取历史失败')
  }
}

onMounted(() => {
  loadKbList()
  loadSessions()
})
</script>