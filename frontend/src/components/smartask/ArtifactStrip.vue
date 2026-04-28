<template>
  <section class="sa-artifact-strip">
    <button class="sa-artifact-main" @click="$emit('download')">
      <span class="sa-artifact-icon" aria-hidden="true"></span>
      <span class="sa-artifact-copy">
        <span class="sa-artifact-name">{{ title }}.PDF</span>
        <span class="sa-artifact-desc">报告文件已整理完成，可导出为 PDF</span>
      </span>
      <span class="sa-artifact-action">导出</span>
    </button>

    <div class="sa-artifact-list">
      <button class="sa-artifact-chip" @click="$emit('viewDetails')">
        <span class="sa-chip-type is-log" aria-hidden="true"></span>
        <span class="sa-chip-name">执行轨迹</span>
      </button>
      <button v-if="datasetName" class="sa-artifact-chip" @click="$emit('viewDetails')">
        <span class="sa-chip-type is-data" aria-hidden="true"></span>
        <span class="sa-chip-name">{{ datasetName }}</span>
      </button>
      <button class="sa-artifact-chip" @click="$emit('viewDetails')">
        <span class="sa-chip-type is-view" aria-hidden="true"></span>
        <span class="sa-chip-name">结果总览</span>
      </button>
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: '分析报告',
  },
  datasetName: {
    type: String,
    default: '',
  },
})

defineEmits(['download', 'viewDetails'])
</script>

<style scoped>
.sa-artifact-strip {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.sa-artifact-main {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 13px;
  border-radius: 13px;
  border: 1px solid rgba(22, 93, 255, 0.12);
  background: linear-gradient(180deg, #f4f8ff 0%, #fbfdff 100%);
  cursor: pointer;
  transition: all 0.18s ease;
}

.sa-artifact-main:hover {
  border-color: rgba(22, 93, 255, 0.28);
  transform: translateY(-1px);
}

.sa-artifact-icon {
  position: relative;
  min-width: 36px;
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: linear-gradient(180deg, #ffffff 0%, #eef5ff 100%);
  border: 1px solid rgba(22, 93, 255, 0.12);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.sa-artifact-icon::before {
  content: '';
  width: 14px;
  height: 16px;
  border-radius: 4px;
  border: 1.5px solid #165dff;
  background: linear-gradient(180deg, rgba(22, 93, 255, 0.08) 0%, rgba(22, 93, 255, 0.02) 100%);
}

.sa-artifact-icon::after {
  content: '';
  position: absolute;
  top: 10px;
  right: 10px;
  width: 5px;
  height: 5px;
  border-top: 1.5px solid #165dff;
  border-right: 1.5px solid #165dff;
  transform: rotate(45deg);
}

.sa-artifact-copy {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  text-align: left;
}

.sa-artifact-name {
  font-size: 12px;
  font-weight: 600;
  color: #1d2129;
}

.sa-artifact-desc {
  font-size: 11px;
  color: #86909c;
}

.sa-artifact-action {
  font-size: 11px;
  font-weight: 600;
  color: #165dff;
}

.sa-artifact-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sa-artifact-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  background: #ffffff;
  cursor: pointer;
  transition: all 0.18s ease;
}

.sa-artifact-chip:hover {
  border-color: rgba(22, 93, 255, 0.24);
  background: #f8fbff;
}

.sa-chip-type {
  position: relative;
  width: 18px;
  height: 18px;
  border-radius: 6px;
  background: #f6f8fb;
  border: 1px solid rgba(29, 33, 41, 0.08);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sa-chip-type::before,
.sa-chip-type::after {
  content: '';
  position: absolute;
}

.sa-chip-type.is-log::before {
  width: 9px;
  height: 7px;
  border-left: 1.5px solid #165dff;
  border-right: 1.5px solid #165dff;
  border-bottom: 1.5px solid #165dff;
  bottom: 4px;
}

.sa-chip-type.is-log::after {
  width: 9px;
  height: 1.5px;
  background: #165dff;
  top: 5px;
  box-shadow: 0 3px 0 #165dff;
}

.sa-chip-type.is-data::before {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1.5px solid #165dff;
  top: 2px;
}

.sa-chip-type.is-data::after {
  width: 10px;
  height: 5px;
  border: 1.5px solid #165dff;
  border-top: none;
  border-radius: 0 0 7px 7px;
  bottom: 2px;
}

.sa-chip-type.is-view::before {
  width: 10px;
  height: 6px;
  border: 1.5px solid #165dff;
  border-radius: 8px;
}

.sa-chip-type.is-view::after {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #165dff;
}

.sa-chip-name {
  font-size: 11px;
  color: #1d2129;
}
</style>
