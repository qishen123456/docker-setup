<template>
  <div style="display:flex;justify-content:center;align-items:center;height:60vh">
    <el-result icon="404" title="页面不存在" sub-title="您访问的页面不存在，请返回首页">
      <template #extra>
        <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
      </template>
    </el-result>
  </div>
</template>
