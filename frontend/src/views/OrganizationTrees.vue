<template>
  <div class="org-page">
    <section class="org-hero">
      <div>
        <p class="eyebrow">权限治理</p>
        <h1>组织树管理</h1>
        <p>按业务线维护彼此隔离的组织树类型和树形节点，后续用于员工数据范围授权。</p>
      </div>
      <div class="hero-actions">
        <el-button :icon="Refresh" @click="loadData">刷新</el-button>
        <el-button @click="openImportDialog">合并/替换导入</el-button>
        <el-button type="primary" :icon="Plus" @click="startCreateType">新增组织树</el-button>
      </div>
    </section>

    <section class="stat-grid">
      <div class="stat-item">
        <span>组织树类型</span>
        <strong>{{ treeTypes.length }}</strong>
      </div>
      <div class="stat-item">
        <span>组织节点</span>
        <strong>{{ nodes.length }}</strong>
      </div>
      <div class="stat-item">
        <span>启用类型</span>
        <strong>{{ enabledTypeCount }}</strong>
      </div>
      <div class="stat-item">
        <span>最大层级</span>
        <strong>{{ maxDepth }}</strong>
      </div>
    </section>

    <section class="workspace">
      <aside class="type-panel">
        <div class="panel-head">
          <div>
            <h2>组织树类型</h2>
            <p>编码隔离，节点互不串用</p>
          </div>
        </div>
        <el-empty v-if="!treeTypes.length" description="暂无组织树" />
        <button
          v-for="item in treeTypes"
          :key="item.id"
          class="type-item"
          :class="{ active: item.id === selectedTypeId }"
          type="button"
          @click="selectType(item.id)"
        >
          <span>
            <strong>{{ item.name }}</strong>
            <small>{{ item.code }}</small>
          </span>
          <em>{{ item.node_count || 0 }} 节点</em>
        </button>
      </aside>

      <main class="detail-panel">
        <template v-if="selectedType">
          <div class="detail-head">
            <div>
              <div class="tree-tag">组织树</div>
              <h2>{{ selectedType.name }}</h2>
              <p>{{ selectedType.description || '未填写说明' }}</p>
            </div>
            <div class="detail-actions">
              <el-button :icon="Edit" @click="startEditType">编辑类型</el-button>
              <el-button :icon="Plus" type="primary" @click="startCreateNode()">新增根节点</el-button>
              <el-button :icon="Delete" type="danger" plain @click="removeType">删除类型</el-button>
            </div>
          </div>

          <div class="tree-layout">
            <div class="tree-box">
              <div class="box-head">
                <h3>树形层级</h3>
                <span>{{ currentTreeNodes.length }} 个根节点</span>
              </div>
              <el-empty v-if="!currentTreeNodes.length" description="暂无节点，先新增根节点" />
              <el-tree
                v-else
                :data="currentTreeNodes"
                node-key="id"
                default-expand-all
                :expand-on-click-node="false"
              >
                <template #default="{ data }">
                  <div class="tree-node-row">
                    <button type="button" :class="{ active: selectedNode?.id === data.id }" @click.stop="selectNode(data)">
                      <span class="node-title-line">
                        <strong>{{ data.name }}</strong>
                        <em class="node-level">L{{ data.level }}</em>
                      </span>
                      <small>{{ data.code }}</small>
                    </button>
                  </div>
                </template>
              </el-tree>
            </div>

            <div class="node-panel">
              <div class="box-head">
                <h3>{{ selectedNode ? '节点详情' : '节点操作' }}</h3>
                <span>{{ selectedNode?.path_names?.join(' / ') || '选择一个节点查看' }}</span>
              </div>
              <template v-if="selectedNode">
                <dl class="node-meta">
                  <div>
                    <dt>节点名称</dt>
                    <dd>{{ selectedNode.name }}</dd>
                  </div>
                  <div>
                    <dt>节点编码</dt>
                    <dd>{{ selectedNode.code }}</dd>
                  </div>
                  <div>
                    <dt>上级节点</dt>
                    <dd>{{ parentNodeName(selectedNode) }}</dd>
                  </div>
                  <div>
                    <dt>状态</dt>
                    <dd>{{ selectedNode.enabled ? '启用' : '停用' }}</dd>
                  </div>
                </dl>
                <div class="node-actions">
                  <el-button type="primary" :icon="Plus" @click="startCreateNode(selectedNode)">新增下级</el-button>
                  <el-button :icon="Edit" @click="startEditNode(selectedNode)">编辑节点</el-button>
                  <el-button type="danger" plain :icon="Delete" @click="removeNode(selectedNode)">删除节点</el-button>
                </div>
              </template>
              <el-empty v-else description="从左侧树中选择节点，或新增根节点" />
            </div>
          </div>
        </template>
        <el-empty v-else description="请先新增组织树类型" />
      </main>
    </section>

    <el-dialog v-model="typeDialog.visible" :title="typeDialog.mode === 'create' ? '新增组织树' : '编辑组织树'" width="520px">
      <el-form label-position="top">
        <el-form-item label="组织树名称">
          <el-input v-model="typeForm.name" placeholder="例如：消费者组织树" />
        </el-form-item>
        <el-form-item label="组织树编码">
          <el-input v-model="typeForm.code" placeholder="例如：consumer_org" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="typeForm.sort_order" :min="1" :max="9999" />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="typeForm.enabled" active-text="启用" inactive-text="停用" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="typeForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="typeDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveType">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="nodeDialog.visible" :title="nodeDialog.mode === 'create' ? '新增组织节点' : '编辑组织节点'" width="560px">
      <el-form label-position="top">
        <el-form-item label="节点名称">
          <el-input v-model="nodeForm.name" placeholder="例如：东部分公司" />
        </el-form-item>
        <el-form-item label="节点编码">
          <el-input v-model="nodeForm.code" placeholder="同一组织树下唯一，例如：east_branch" />
        </el-form-item>
        <el-form-item label="上级节点">
          <el-tree-select
            v-model="nodeForm.parent_id"
            :data="nodeParentOptions"
            clearable
            check-strictly
            node-key="id"
            :props="{ label: 'name', value: 'id', children: 'children' }"
            placeholder="不选则为根节点"
          />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="nodeForm.sort_order" :min="1" :max="9999" />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="nodeForm.enabled" active-text="启用" inactive-text="停用" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="nodeForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="nodeDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveNode">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importDialog.visible" title="导入组织树表格" width="980px" class="import-dialog">
      <div class="import-grid">
        <section class="import-config">
          <el-form label-position="top">
            <el-form-item label="导入方式">
              <el-radio-group v-model="importForm.mode">
                <el-radio-button label="merge">合并导入</el-radio-button>
                <el-radio-button label="replace">替换导入</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="目标组织树">
              <el-select v-model="importForm.tree_type_id" clearable placeholder="选择已有组织树">
                <el-option v-for="item in treeTypes" :key="item.id" :label="`${item.name}（${item.code}）`" :value="item.id" />
              </el-select>
            </el-form-item>
            <div class="new-tree-fields">
              <el-form-item label="新组织树名称">
                <el-input v-model.trim="importForm.tree_type_name" :disabled="!!importForm.tree_type_id" placeholder="不选已有组织树时填写" />
              </el-form-item>
              <el-form-item label="新组织树编码">
                <el-input v-model.trim="importForm.tree_type_code" :disabled="!!importForm.tree_type_id" placeholder="例如：angel_org" />
              </el-form-item>
            </div>
            <el-form-item label="Excel 表格内容">
              <el-input
                v-model="importForm.text"
                type="textarea"
                :rows="13"
                placeholder="从 Excel 复制包含表头的数据后粘贴到这里，例如：公司ID（0级） 公司名称（0级） 1级ID 1级名称 2级ID 2级名称"
              />
            </el-form-item>
          </el-form>
        </section>

        <section class="import-preview">
          <div class="preview-head">
            <div>
              <h3>变化预览</h3>
              <p>先预检，确认后才会写入组织树。</p>
            </div>
            <el-button type="primary" plain :loading="importPreviewing" @click="previewImport">预检导入</el-button>
          </div>

          <template v-if="importPreview">
            <div class="preview-stats">
              <div><span>新增</span><strong>{{ importPreview.stats?.create || 0 }}</strong></div>
              <div><span>更新</span><strong>{{ importPreview.stats?.update || 0 }}</strong></div>
              <div><span>不变</span><strong>{{ importPreview.stats?.unchanged || 0 }}</strong></div>
              <div><span>删除</span><strong>{{ importPreview.stats?.delete || 0 }}</strong></div>
              <div><span>去重</span><strong>{{ importPreview.stats?.duplicates || 0 }}</strong></div>
            </div>

            <el-alert
              v-if="importPreview.errors?.length"
              type="error"
              :closable="false"
              show-icon
              class="preview-alert"
            >
              <template #title>预检发现 {{ importPreview.errors.length }} 个问题</template>
              <ul>
                <li v-for="item in importPreview.errors.slice(0, 6)" :key="item">{{ item }}</li>
              </ul>
            </el-alert>

            <el-table :data="importPreview.changes || []" size="small" border max-height="320">
              <el-table-column label="动作" width="78">
                <template #default="{ row }">
                  <el-tag :type="changeTagType(row.action)" size="small">{{ changeLabel(row.action) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="code" label="编码" min-width="150" show-overflow-tooltip />
              <el-table-column prop="name" label="名称" min-width="150" show-overflow-tooltip />
              <el-table-column prop="parent_code" label="上级编码" min-width="120" show-overflow-tooltip>
                <template #default="{ row }">{{ row.parent_code || '根节点' }}</template>
              </el-table-column>
              <el-table-column label="变化" min-width="220" show-overflow-tooltip>
                <template #default="{ row }">{{ (row.diffs || []).join('；') || '-' }}</template>
              </el-table-column>
            </el-table>
            <p v-if="importPreview.change_count > (importPreview.changes || []).length" class="preview-more">
              仅展示前 {{ (importPreview.changes || []).length }} 条变化，共 {{ importPreview.change_count }} 条。
            </p>
          </template>
          <el-empty v-else description="粘贴表格后点击预检导入" />
        </section>
      </div>
      <template #footer>
        <el-button @click="importDialog.visible = false">取消</el-button>
        <el-button type="primary" :disabled="!importPreview?.can_apply" :loading="importApplying" @click="applyImport">确认导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus, Refresh } from '@element-plus/icons-vue'
import {
  applyOrganizationTreeImport,
  createOrganizationTreeNode,
  createOrganizationTreeType,
  deleteOrganizationTreeNode,
  deleteOrganizationTreeType,
  getOrganizationTrees,
  previewOrganizationTreeImport,
  updateOrganizationTreeNode,
  updateOrganizationTreeType,
} from '../api/index.js'

const treeTypes = ref([])
const nodes = ref([])
const trees = ref({})
const selectedTypeId = ref('')
const selectedNode = ref(null)
const saving = ref(false)

const typeDialog = reactive({ visible: false, mode: 'create' })
const nodeDialog = reactive({ visible: false, mode: 'create' })
const importDialog = reactive({ visible: false })
const importPreviewing = ref(false)
const importApplying = ref(false)
const importPreview = ref(null)
const typeForm = reactive({
  id: '',
  name: '',
  code: '',
  description: '',
  enabled: true,
  sort_order: 100,
})
const nodeForm = reactive({
  id: '',
  tree_type_id: '',
  parent_id: '',
  name: '',
  code: '',
  description: '',
  enabled: true,
  sort_order: 100,
})
const importForm = reactive({
  mode: 'merge',
  tree_type_id: '',
  tree_type_name: '',
  tree_type_code: '',
  text: '',
})

const selectedType = computed(() => treeTypes.value.find(item => item.id === selectedTypeId.value) || null)
const currentTreeNodes = computed(() => trees.value[selectedTypeId.value] || [])
const enabledTypeCount = computed(() => treeTypes.value.filter(item => item.enabled).length)
const maxDepth = computed(() => Math.max(0, ...treeTypes.value.map(item => Number(item.max_depth || 0))))
const nodeParentOptions = computed(() => {
  if (!nodeForm.id) return currentTreeNodes.value
  const stripSelf = (items = []) => items
    .filter(item => item.id !== nodeForm.id)
    .map(item => ({ ...item, children: stripSelf(item.children || []) }))
  return stripSelf(currentTreeNodes.value)
})

const resetTypeForm = (payload = {}) => {
  Object.assign(typeForm, {
    id: payload.id || '',
    name: payload.name || '',
    code: payload.code || '',
    description: payload.description || '',
    enabled: payload.enabled !== false,
    sort_order: Number(payload.sort_order || 100),
  })
}

const resetNodeForm = (payload = {}) => {
  Object.assign(nodeForm, {
    id: payload.id || '',
    tree_type_id: payload.tree_type_id || selectedTypeId.value || '',
    parent_id: payload.parent_id || '',
    name: payload.name || '',
    code: payload.code || '',
    description: payload.description || '',
    enabled: payload.enabled !== false,
    sort_order: Number(payload.sort_order || 100),
  })
}

const applyOverview = (payload = {}) => {
  treeTypes.value = payload.tree_types || []
  nodes.value = payload.nodes || []
  trees.value = payload.trees || {}
  if (!selectedTypeId.value || !treeTypes.value.some(item => item.id === selectedTypeId.value)) {
    selectedTypeId.value = treeTypes.value[0]?.id || ''
  }
  if (selectedNode.value && !nodes.value.some(item => item.id === selectedNode.value.id)) {
    selectedNode.value = null
  }
  if (selectedNode.value) {
    selectedNode.value = nodes.value.find(item => item.id === selectedNode.value.id) || null
  }
}

const loadData = async () => {
  const res = await getOrganizationTrees()
  applyOverview(res)
}

const selectType = (id) => {
  selectedTypeId.value = id
  selectedNode.value = null
}

const selectNode = (node) => {
  selectedNode.value = nodes.value.find(item => item.id === node.id) || node
}

const startCreateType = () => {
  resetTypeForm()
  typeDialog.mode = 'create'
  typeDialog.visible = true
}

const startEditType = () => {
  if (!selectedType.value) return
  resetTypeForm(selectedType.value)
  typeDialog.mode = 'edit'
  typeDialog.visible = true
}

const saveType = async () => {
  if (!typeForm.name.trim() || !typeForm.code.trim()) {
    ElMessage.warning('请填写组织树名称和编码')
    return
  }
  saving.value = true
  try {
    const payload = { ...typeForm }
    const res = typeDialog.mode === 'create'
      ? await createOrganizationTreeType(payload)
      : await updateOrganizationTreeType(typeForm.id, payload)
    applyOverview(res)
    selectedTypeId.value = res.tree_type?.id || selectedTypeId.value
    typeDialog.visible = false
    ElMessage.success('组织树已保存')
  } finally {
    saving.value = false
  }
}

const removeType = async () => {
  if (!selectedType.value) return
  await ElMessageBox.confirm(`确认删除组织树「${selectedType.value.name}」？`, '删除组织树', { type: 'warning' })
  const res = await deleteOrganizationTreeType(selectedType.value.id)
  applyOverview(res)
  ElMessage.success('组织树已删除')
}

const startCreateNode = (parent = null) => {
  if (!selectedTypeId.value) return
  resetNodeForm({ tree_type_id: selectedTypeId.value, parent_id: parent?.id || '' })
  nodeDialog.mode = 'create'
  nodeDialog.visible = true
}

const startEditNode = (node) => {
  resetNodeForm(node)
  nodeDialog.mode = 'edit'
  nodeDialog.visible = true
}

const saveNode = async () => {
  if (!nodeForm.name.trim() || !nodeForm.code.trim()) {
    ElMessage.warning('请填写节点名称和编码')
    return
  }
  saving.value = true
  try {
    const payload = { ...nodeForm, tree_type_id: selectedTypeId.value }
    const res = nodeDialog.mode === 'create'
      ? await createOrganizationTreeNode(payload)
      : await updateOrganizationTreeNode(nodeForm.id, payload)
    applyOverview(res)
    selectedNode.value = res.node || selectedNode.value
    nodeDialog.visible = false
    ElMessage.success('组织节点已保存')
  } finally {
    saving.value = false
  }
}

const removeNode = async (node) => {
  await ElMessageBox.confirm(`确认删除节点「${node.name}」？`, '删除组织节点', { type: 'warning' })
  const res = await deleteOrganizationTreeNode(node.id)
  applyOverview(res)
  ElMessage.success('组织节点已删除')
}

const parentNodeName = (node) => {
  if (!node?.parent_id) return '无上级'
  return nodes.value.find(item => item.id === node.parent_id)?.name || '无上级'
}

const importPayload = () => ({
  mode: importForm.mode,
  tree_type_id: importForm.tree_type_id,
  tree_type_name: importForm.tree_type_name,
  tree_type_code: importForm.tree_type_code,
  text: importForm.text,
})

const openImportDialog = () => {
  Object.assign(importForm, {
    mode: 'merge',
    tree_type_id: selectedTypeId.value || '',
    tree_type_name: '',
    tree_type_code: '',
    text: '',
  })
  importPreview.value = null
  importDialog.visible = true
}

const previewImport = async () => {
  if (!importForm.text.trim()) {
    ElMessage.warning('请先粘贴 Excel 表格内容')
    return
  }
  importPreviewing.value = true
  try {
    importPreview.value = await previewOrganizationTreeImport(importPayload())
  } finally {
    importPreviewing.value = false
  }
}

const applyImport = async () => {
  if (!importPreview.value?.can_apply) return
  await ElMessageBox.confirm(
    `${importForm.mode === 'replace' ? '替换导入会删除目标组织树中未出现在表格里的节点。' : '合并导入会保留目标组织树中未出现在表格里的节点。'}确认继续吗？`,
    '确认导入组织树',
    { type: 'warning' }
  )
  importApplying.value = true
  try {
    const res = await applyOrganizationTreeImport(importPayload())
    applyOverview(res)
    selectedTypeId.value = res.preview?.tree_type?.id || selectedTypeId.value
    importDialog.visible = false
    ElMessage.success('组织树导入完成')
  } finally {
    importApplying.value = false
  }
}

const changeLabel = (action) => ({ create: '新增', update: '更新', delete: '删除' }[action] || '不变')
const changeTagType = (action) => ({ create: 'success', update: 'warning', delete: 'danger' }[action] || 'info')

onMounted(loadData)
</script>

<style scoped>
.org-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.org-hero,
.workspace,
.stat-item {
  background: #fff;
  border: 1px solid #e5eaf3;
  border-radius: 8px;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.org-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 24px 28px;
}

.eyebrow {
  margin: 0 0 8px;
  color: #2563eb;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0;
}

.org-hero h1,
.detail-head h2,
.type-panel h2,
.box-head h3 {
  margin: 0;
  color: #0f172a;
}

.org-hero h1 {
  font-size: 28px;
}

.org-hero p,
.type-panel p,
.detail-head p,
.box-head span {
  margin: 8px 0 0;
  color: #64748b;
}

.hero-actions,
.detail-actions,
.node-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.stat-item {
  padding: 18px;
}

.stat-item span {
  display: block;
  color: #64748b;
  font-weight: 700;
}

.stat-item strong {
  display: block;
  margin-top: 8px;
  color: #0f172a;
  font-size: 28px;
}

.workspace {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  min-height: 620px;
  overflow: hidden;
}

.type-panel {
  border-right: 1px solid #e5eaf3;
  padding: 18px;
}

.panel-head,
.detail-head,
.box-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.type-item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
  padding: 14px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: #f8fafc;
  color: #0f172a;
  text-align: left;
  cursor: pointer;
}

.type-item.active {
  border-color: #14b8a6;
  background: #f0fdfa;
}

.type-item strong,
.type-item small {
  display: block;
}

.type-item small,
.type-item em {
  margin-top: 4px;
  color: #64748b;
  font-style: normal;
}

.detail-panel {
  padding: 22px;
  min-width: 0;
}

.tree-tag {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 800;
}

.tree-layout {
  display: grid;
  grid-template-columns: minmax(360px, 1fr) 360px;
  gap: 16px;
  margin-top: 18px;
}

.tree-box,
.node-panel {
  border: 1px solid #e5eaf3;
  border-radius: 8px;
  padding: 16px;
  min-height: 480px;
}

.tree-box :deep(.el-tree) {
  margin-top: 12px;
  min-height: 390px;
  background: transparent;
}

.tree-box :deep(.el-tree-node__content) {
  height: auto;
  min-height: 46px;
  align-items: flex-start;
  padding: 4px 0;
}

.tree-box :deep(.el-tree-node__expand-icon) {
  margin-top: 9px;
}

.tree-box :deep(.el-tree-node__children) {
  overflow: visible;
}

.tree-node-row {
  width: 100%;
  min-width: 0;
}

.tree-node-row button {
  display: block;
  width: 100%;
  min-width: 0;
  padding: 6px 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #0f172a;
  text-align: left;
  cursor: pointer;
  transition: background .16s ease;
}

.tree-node-row button:hover {
  background: #f1f5f9;
}

.tree-node-row button.active {
  background: #ecfdf5;
  box-shadow: inset 3px 0 0 #14b8a6;
}

.node-title-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.tree-node-row strong,
.tree-node-row small {
  display: block;
}

.tree-node-row strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-node-row small {
  margin-top: 2px;
  color: #64748b;
  font-size: 12px;
}

.node-level {
  flex: 0 0 auto;
  padding: 1px 6px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 11px;
  font-style: normal;
  font-weight: 800;
}

.node-meta {
  display: grid;
  gap: 10px;
  margin: 18px 0;
}

.node-meta div {
  padding: 12px;
  border: 1px solid #edf2f7;
  border-radius: 8px;
  background: #f8fafc;
}

.node-meta dt {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.node-meta dd {
  margin: 6px 0 0;
  color: #0f172a;
  font-weight: 800;
}

.import-grid {
  display: grid;
  grid-template-columns: minmax(360px, 0.9fr) minmax(420px, 1.1fr);
  gap: 16px;
}

.import-config,
.import-preview {
  min-width: 0;
}

.new-tree-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.preview-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.preview-head h3 {
  margin: 0;
  color: #0f172a;
  font-size: 18px;
}

.preview-head p,
.preview-more {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 12px;
}

.preview-stats {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

.preview-stats div {
  padding: 10px;
  border: 1px solid #e5eaf3;
  border-radius: 8px;
  background: #f8fafc;
}

.preview-stats span {
  display: block;
  color: #64748b;
  font-size: 12px;
}

.preview-stats strong {
  display: block;
  margin-top: 4px;
  color: #0f172a;
  font-size: 20px;
}

.preview-alert {
  margin-bottom: 12px;
}

.preview-alert ul {
  margin: 6px 0 0;
  padding-left: 18px;
}

@media (max-width: 1180px) {
  .workspace,
  .tree-layout,
  .import-grid {
    grid-template-columns: 1fr;
  }

  .type-panel {
    border-right: 0;
    border-bottom: 1px solid #e5eaf3;
  }
}
</style>
