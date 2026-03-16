import { defineStore } from 'pinia'
import { listSessions, createSession, deleteSession, getHistory } from '@/api/session'

export const useSessionStore = defineStore('session', {
  state: () => ({
    sessions: [],
    currentSessionId: null,
    messages: []
  }),
  actions: {
    async fetchSessions() {
      try {
        this.sessions = await listSessions()
      } catch (error) {
        console.error('获取会话列表失败', error)
      }
    },
    async createNewSession(name, kbId) {
      try {
        const newSession = await createSession({ name, kb_id: kbId })
        this.sessions.unshift(newSession)
        this.currentSessionId = newSession.id
        this.messages = []
        return newSession
      } catch (error) {
        console.error('创建会话失败', error)
        throw error
      }
    },
    async deleteSessionById(sessionId) {
      try {
        await deleteSession(sessionId)
        this.sessions = this.sessions.filter(s => s.id !== sessionId)
        if (this.currentSessionId === sessionId) {
          this.currentSessionId = null
          this.messages = []
        }
      } catch (error) {
        console.error('删除会话失败', error)
        throw error
      }
    },
    async switchSession(sessionId) {
      if (sessionId === this.currentSessionId) return
      this.currentSessionId = sessionId
      await this.loadHistory(sessionId)
    },
    async loadHistory(sessionId) {
      try {
        this.messages = await getHistory(sessionId)
      } catch (error) {
        console.error('加载历史失败', error)
      }
    },
    addMessage(message) {
      this.messages.push(message)
    }
  }
})