<template>
  <el-container style="height: 100vh;">
    <!-- 顶部导航栏 -->
    <el-header style="padding: 0; background-color: #fff; border-bottom: 1px solid #dcdfe6;">
      <div style="display: flex; align-items: center; height: 100%; padding: 0 20px;">
        <!-- 左上角：LocalRAG（不可点击） + 多知识库标签 -->
        <div style="display: flex; align-items: center;">
          <span style="font-size: 20px; font-weight: 600; color: #303133;">LocalRAG</span>
          <el-tag size="small" type="info" style="margin-left: 8px;">多知识库</el-tag>
        </div>

        <!-- 中间导航菜单 -->
        <el-menu
          :default-active="$route.path"
          mode="horizontal"
          router
          style="border-bottom: none; margin-left: 40px; flex: 1;"
        >
          <el-menu-item index="/kb">
            <el-icon><Folder /></el-icon>
            <span>知识库</span>
          </el-menu-item>
          <el-menu-item index="/chat">
            <el-icon><ChatDotRound /></el-icon>
            <span>聊天</span>
          </el-menu-item>
          <el-menu-item index="/documents">
            <el-icon><Document /></el-icon>
            <span>文件管理</span>
          </el-menu-item>
        </el-menu>

        <!-- 右上角气泡框（下拉菜单） -->
        <el-dropdown trigger="click" placement="bottom-end">
          <el-button link style="border: none; padding: 8px;">
            <el-icon size="20"><MoreFilled /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item>
                <el-icon><Message /></el-icon>简体中文
              </el-dropdown-item>
              <el-dropdown-item disabled>
                <el-icon><Message /></el-icon>English
              </el-dropdown-item>
              <el-dropdown-item divided>
                <el-icon><QuestionFilled /></el-icon>帮助
              </el-dropdown-item>
              <el-dropdown-item>
                <el-icon><Setting /></el-icon>设置
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <!-- 主要内容区域 -->
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import {
  Folder,
  ChatDotRound,
  Document,
  MoreFilled,
  Message,
  QuestionFilled,
  Setting
} from '@element-plus/icons-vue'
</script>

<style scoped>
.el-dropdown-link {
  cursor: pointer;
  display: flex;
  align-items: center;
}
.el-button.is-link {
  --el-button-bg-color: transparent;
}
</style>