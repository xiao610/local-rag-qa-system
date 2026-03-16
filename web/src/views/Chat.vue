<template>
  <div class="chat-container">
    <!-- 左侧会话列表（仿 DeepSeek） -->
    <div class="session-sidebar">
      <div class="new-chat-btn">
        <el-button type="primary" @click="createSession" style="width: 100%;">开启新对话</el-button>
      </div>

      <div class="session-groups" v-loading="loadingSessions">
        <!-- 今天 -->
        <div v-if="groupedSessions.today.length" class="session-group">
          <div class="group-title">今天</div>
          <div
            v-for="s in groupedSessions.today"
            :key="s.id"
            class="session-item"
            :class="{ active: s.id === currentSessionId }"
            @click="switchSession(s.id)"
          >
            <span class="session-name">{{ s.name }}</span>
            <el-icon class="delete-icon" @click.stop="deleteSession(s.id)"><Delete /></el-icon>
          </div>
        </div>

        <!-- 昨天 -->
        <div v-if="groupedSessions.yesterday.length" class="session-group">
          <div class="group-title">昨天</div>
          <div
            v-for="s in groupedSessions.yesterday"
            :key="s.id"
            class="session-item"
            :class="{ active: s.id === currentSessionId }"
            @click="switchSession(s.id)"
          >
            <span class="session-name">{{ s.name }}</span>
            <el-icon class="delete-icon" @click.stop="deleteSession(s.id)"><Delete /></el-icon>
          </div>
        </div>

        <!-- 7天内 -->
        <div v-if="groupedSessions.last7Days.length" class="session-group">
          <div class="group-title">7天内</div>
          <div
            v-for="s in groupedSessions.last7Days"
            :key="s.id"
            class="session-item"
            :class="{ active: s.id === currentSessionId }"
            @click="switchSession(s.id)"
          >
            <span class="session-name">{{ s.name }}</span>
            <el-icon class="delete-icon" @click.stop="deleteSession(s.id)"><Delete /></el-icon>
          </div>
        </div>

        <!-- 更早 -->
        <div v-if="groupedSessions.earlier.length" class="session-group">
          <div class="group-title">更早</div>
          <div
            v-for="s in groupedSessions.earlier"
            :key="s.id"
            class="session-item"
            :class="{ active: s.id === currentSessionId }"
            @click="switchSession(s.id)"
          >
            <span class="session-name">{{ s.name }}</span>
            <el-icon class="delete-icon" @click.stop="deleteSession(s.id)"><Delete /></el-icon>
          </div>
        </div>

        <!-- 无会话时显示提示 -->
        <div v-if="sessions.length === 0" class="empty-tip">
          暂无会话，点击上方按钮创建
        </div>
      </div>
    </div>

    <!-- 右侧聊天主区域（保持不变） -->
    <div class="chat-main">
      <!-- 聊天消息列表 -->
      <div class="message-list" ref="messageList">
        <div v-for="(msg, idx) in messages" :key="idx" class="message-wrapper" :class="msg.role">
          <el-card class="message-bubble" :class="msg.role" shadow="never">
            <div class="message-content">{{ msg.content }}</div>
            <div v-if="msg.sources" class="message-sources">
              来源: {{ JSON.stringify(msg.sources) }}
            </div>
          </el-card>
        </div>
      </div>

      <!-- 聊天设置面板（可折叠） -->
      <el-collapse v-model="activeSettings" class="settings-panel">
        <el-collapse-item title="聊天设置" name="settings">
          <el-form label-width="140px" size="small">
            <!-- 知识库选择：改为多选框 -->
            <el-form-item label="选择知识库（可多选）">
              <el-select
                v-model="selectedKbIds"
                multiple
                collapse-tags
                placeholder="请选择知识库"
                style="width: 100%;"
              >
                <el-option
                  v-for="kb in kbList"
                  :key="kb.collection_name"
                  :label="kb.display_name"
                  :value="kb.display_name"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="top_k">
              <el-slider v-model="chatParams.top_k" :min="1" :max="20" show-input />
            </el-form-item>
            <el-form-item label="相似度阈值">
              <el-slider v-model="chatParams.similarity_threshold" :min="0" :max="1" :step="0.05" show-input />
            </el-form-item>
            <el-form-item label="系统提示词">
              <el-input v-model="chatParams.system_prompt" type="textarea" :rows="2" placeholder="系统提示词" />
            </el-form-item>
            <el-form-item label="温度">
              <el-slider v-model="chatParams.temperature" :min="0" :max="2" :step="0.1" show-input />
            </el-form-item>
            <el-form-item label="top_p">
              <el-slider v-model="chatParams.top_p" :min="0" :max="1" :step="0.05" show-input />
            </el-form-item>
            <el-form-item label="存在惩罚">
              <el-slider v-model="chatParams.presence_penalty" :min="-2" :max="2" :step="0.1" show-input />
            </el-form-item>
            <el-form-item label="频率惩罚">
              <el-slider v-model="chatParams.frequency_penalty" :min="-2" :max="2" :step="0.1" show-input />
            </el-form-item>
            <el-form-item label="最大输出长度">
              <el-input-number v-model="chatParams.max_tokens" :min="1" :max="4096" :step="1" />
            </el-form-item>
          </el-form>
        </el-collapse-item>
      </el-collapse>

      <!-- 输入框和发送按钮 -->
      <div class="input-area">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="3"
          placeholder="请输入消息..."
          @keydown.enter.prevent="sendMessage"
        />
        <el-button type="primary" @click="sendMessage" :loading="sending" style="margin-left: 10px;">发送</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { useSessionStore } from '@/stores/session'
import { useKbStore } from '@/stores/kb'
import { chat } from '@/api/chat'

const sessionStore = useSessionStore()
const kbStore = useKbStore()

// 会话和知识库状态
const sessions = ref([])
const currentSessionId = ref('')
const currentKbId = ref('default')        // 默认知识库（用于创建会话等）
const selectedKbIds = ref([])              // 用户多选的知识库列表
const messages = ref([])
const inputText = ref('')
const sending = ref(false)
const kbList = ref([])
const loadingSessions = ref(false)

// 聊天设置参数
const chatParams = ref({
  top_k: 5,
  similarity_threshold: 0.2,
  system_prompt: '',
  temperature: 0,
  top_p: 1,
  presence_penalty: 0,
  frequency_penalty: 0,
  max_tokens: 2048
})

// 设置面板折叠状态（默认展开）
const activeSettings = ref(['settings'])

// 监听 store 变化
watch(() => sessionStore.sessions, (val) => { sessions.value = val }, { immediate: true })
watch(() => sessionStore.currentSessionId, (val) => { currentSessionId.value = val })
watch(() => sessionStore.messages, (val) => { messages.value = val })
watch(() => kbStore.kbList, (val) => { kbList.value = val })
watch(() => kbStore.currentKbId, (val) => { currentKbId.value = val })

// 创建新会话
const createSession = async () => {
  // 使用默认知识库（currentKbId）创建新会话
  await sessionStore.createNewSession('新对话', currentKbId.value)
  // 创建后可选：清空多选框？不清空，保持用户选择
}

// 切换会话
const switchSession = async (id) => {
  await sessionStore.switchSession(id)
}

// 删除会话
const deleteSession = async (id) => {
  try {
    await ElMessageBox.confirm('确认删除该会话？', '提示', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await sessionStore.deleteSessionById(id)
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败：' + error.message)
  }
}

// 发送消息
const sendMessage = async () => {
  if (!inputText.value.trim() || !currentSessionId.value) {
    ElMessage.warning('请先选择或创建会话')
    return
  }
  let kbIds = selectedKbIds.value.length > 0 ? selectedKbIds.value : [currentKbId.value]
  if (kbIds.length === 0) {
    ElMessage.warning('请至少选择一个知识库')
    return
  }

  const question = inputText.value
  sessionStore.addMessage({ role: 'user', content: question })
  inputText.value = ''
  sending.value = true

  try {
    const res = await chat({
      query: question,
      kb_id: kbIds,
      session_id: currentSessionId.value,
      ...chatParams.value
    })

    // 添加助手回复
    sessionStore.addMessage({ role: 'assistant', content: res.answer, sources: res.sources })

    // 如果返回的 session_id 与当前不同，说明后端新建了会话（理论上不会发生，因为传了 session_id）
    // 但为了安全，可以处理
    if (res.session_id && res.session_id !== currentSessionId.value) {
      sessionStore.setCurrentSessionId(res.session_id)
    }

    // 延迟刷新会话列表，以便后台任务生成的标题被获取
    setTimeout(async () => {
      await sessionStore.fetchSessions()
    }, 2000) // 等待2秒，可根据实际情况调整

  } catch (error) {
    ElMessage.error('请求失败：' + error.message)
    sessionStore.addMessage({ role: 'assistant', content: '❌ 请求出错，请稍后重试。' })
  } finally {
    sending.value = false
    nextTick(() => {
      const container = document.querySelector('.message-list')
      if (container) container.scrollTop = container.scrollHeight
    })
  }
}

// 会话分组计算属性
const groupedSessions = computed(() => {
  const groups = {
    today: [],
    yesterday: [],
    last7Days: [],
    earlier: []
  }
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  const sevenDaysAgo = new Date(today)
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)

  sessions.value.forEach(s => {
    const created = new Date(s.created_at)
    if (created >= today) {
      groups.today.push(s)
    } else if (created >= yesterday) {
      groups.yesterday.push(s)
    } else if (created >= sevenDaysAgo) {
      groups.last7Days.push(s)
    } else {
      groups.earlier.push(s)
    }
  })
  return groups
})

// 初始加载
onMounted(async () => {
  loadingSessions.value = true
  await kbStore.fetchKbList()
  await sessionStore.fetchSessions()
  if (sessionStore.sessions.length > 0 && !sessionStore.currentSessionId) {
    await sessionStore.switchSession(sessionStore.sessions[0].id)
  }
  loadingSessions.value = false
})
</script>

<style scoped>
.chat-container {
  display: flex;
  height: 100%;
  gap: 20px;
}
.session-sidebar {
  width: 280px;
  border-right: 1px solid #dcdfe6;
  padding-right: 10px;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
.new-chat-btn {
  padding: 10px 0 15px 0;
}
.session-groups {
  flex: 1;
  overflow-y: auto;
  padding-right: 5px;
}
.session-group {
  margin-bottom: 20px;
}
.group-title {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
  padding-left: 5px;
}
.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  margin: 2px 0;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
}
.session-item:hover {
  background-color: #f5f7fa;
}
.session-item.active {
  background-color: #ecf5ff;
  color: #409EFF;
}
.session-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}
.delete-icon {
  display: none;
  color: #909399;
  cursor: pointer;
  font-size: 16px;
}
.session-item:hover .delete-icon {
  display: inline-block;
}
.delete-icon:hover {
  color: #f56c6c;
}
.empty-tip {
  color: #909399;
  font-size: 14px;
  text-align: center;
  margin-top: 30px;
}
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.message-list {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 20px;
  padding: 10px;
}
.message-wrapper {
  margin-bottom: 15px;
}
.message-wrapper.user {
  display: flex;
  justify-content: flex-end;
}
.message-wrapper.assistant {
  display: flex;
  justify-content: flex-start;
}
.message-bubble {
  max-width: 70%;
  padding: 10px 15px;
  border-radius: 8px;
  word-wrap: break-word;
}
.message-bubble.user {
  background-color: #ecf5ff;
  border: 1px solid #b3d8ff;
}
.message-bubble.assistant {
  background-color: #f4f4f5;
  border: 1px solid #e9e9eb;
}
.message-content {
  white-space: pre-wrap;
}
.message-sources {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}
.settings-panel {
  margin-bottom: 15px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}
.input-area {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}
</style>