import { defineStore } from 'pinia'
import { listKb } from '@/api/kb'

export const useKbStore = defineStore('kb', {
  state: () => ({
    kbList: ['default'],
    currentKbId: 'default'
  }),
  actions: {
    async fetchKbList() {
      try {
        const res = await listKb()
        this.kbList = res.kb_list || ['default']
      } catch (error) {
        console.error('获取知识库列表失败', error)
      }
    },
    setCurrentKb(kbId) {
      this.currentKbId = kbId
    }
  }
})