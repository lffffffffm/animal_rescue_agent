<template>
  <div class="sidebar-wrapper">
    <aside class="sidebar" :class="{ collapsed }">
      <div class="sidebar-content">
        <div class="sidebar-top">
          <button class="new-btn" @click="$emit('new-chat')">
            <span class="plus">+</span>
            <span>新建会话</span>
          </button>

          <div class="search">
            <input v-model.trim="search" type="text" placeholder="搜索历史会话..." />
            <svg class="search-ico" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          </div>
        </div>

        <div class="sidebar-scroll">
          <div class="group">
            <div class="group-hd">
              <div class="group-title">会话记录</div>
              <button class="clear" v-if="filteredRecent.length" @click="$emit('clear-group', 'recent')">清空</button>
            </div>

            <div class="list">
              <button
                v-for="c in filteredRecent"
                :key="c.id"
                class="item"
                :class="{ active: c.id === activeId }"
                @click="$emit('select-chat', c.id)"
              >
                <svg class="item-ico" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <template v-if="editingId === c.id">
                  <input
                    class="title-edit"
                    :value="c.draftTitle ?? c.title"
                    autofocus
                    @click.stop
                    @input="$emit('edit-input', { id: c.id, title: $event.target.value })"
                    @keydown.enter.prevent="$emit('edit-commit', { id: c.id, title: $event.target.value })"
                    @keydown.esc.prevent="$emit('edit-cancel')"
                    @blur="$emit('edit-commit', { id: c.id, title: $event.target.value })"
                  />
                </template>
                <template v-else>
                  <span class="txt">{{ c.title }}</span>
                </template>
                <span class="actions" @click.stop>
                  <button class="icon-btn edit" @click="$emit('edit-chat', c.id)" aria-label="edit">
                    <svg class="icon-svg" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.828 2.828 0 0 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg>
                  </button>
                  <button class="icon-btn danger" @click="$emit('delete-chat', c.id)" aria-label="delete">
                    <svg class="icon-svg" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                  </button>
                </span>
              </button>
            </div>
          </div>

          <div class="group" style="margin-top: 14px;">
            <div class="group-hd">
              <div class="group-title">一周前</div>
            </div>

            <div class="list">
              <button
                v-for="c in filteredLast7"
                :key="c.id"
                class="item"
                :class="{ active: c.id === activeId }"
                @click="$emit('select-chat', c.id)"
              >
                <svg class="item-ico" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <span class="txt">{{ c.title }}</span>
                <span class="actions" @click.stop>
                  <button class="icon-btn" @click="$emit('edit-chat', c.id)">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.828 2.828 0 0 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg>
                  </button>
                  <button class="icon-btn danger" @click="$emit('delete-chat', c.id)" aria-label="delete">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                  </button>
                </span>
              </button>
            </div>
          </div>
        </div>

        <div class="footer">
          <button class="user" type="button">
            <img class="avatar" :src="user.avatar" alt="avatar" @error="onAvatarError" />
            <span class="name">{{ user.name }}</span>
          </button>

          <button class="logout" type="button" @click="$emit('logout')">
            登出
          </button>
        </div>
      </div>
    </aside>

    <button class="collapse-btn" @click="$emit('toggle-collapse')">
      <svg v-if="collapsed" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
      <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
    </button>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  user: { type: Object, required: true },
  recent: { type: Array, default: () => [] },
  last7Days: { type: Array, default: () => [] },
  activeId: { type: [Number, String], default: null },
  editingId: { type: [Number, String], default: null },
  collapsed: { type: Boolean, default: false }
})

defineEmits([
  'new-chat',
  'select-chat',
  'edit-chat',
  'delete-chat',
  'clear-group',
  'logout',
  'edit-input',
  'edit-commit',
  'edit-cancel',
  'toggle-collapse'
])

const search = ref('')

function onAvatarError(e) {
  if (!e?.target) return
  e.target.src = `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(props.user?.name || 'user')}`
}

const filterList = (items) => {
  if (!search.value) return items
  const q = search.value.toLowerCase()
  return items.filter(i => String(i.title ?? '').toLowerCase().includes(q))
}

const filteredRecent = computed(() => filterList(props.recent))
const filteredLast7 = computed(() => filterList(props.last7Days))
</script>

<style scoped>
.sidebar-wrapper {
  position: relative;
}

.sidebar {
  width: 300px;
  height: 100vh;
  background: #ffffff;
  color: #0f172a;
  border-right: 1px solid #e5e7eb;
  padding: 18px 20px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  position: relative;
  transition: width 0.25s ease, padding 0.25s ease;
}

.sidebar.collapsed {
  width: 0;
  padding: 18px 0;
  overflow: hidden;
}

.collapse-btn {
  position: absolute;
  left: 300px;
  top: 50%;
  transform: translateY(-50%) translateX(-50%);
  width: 32px;
  height: 32px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  color: #94a3b8;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  padding: 0;
  transition: all 0.25s ease;
}

.collapse-btn:hover {
  background-color: #f8fafc;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-50%) translateX(-50%) scale(1.05);
}

.collapse-btn:active {
  transform: translateY(-50%) translateX(-50%) scale(0.95);
  box-shadow: none;
}

.collapse-btn svg {
  transition: transform 0.25s ease;
}

.sidebar.collapsed + .collapse-btn {
  left: 24px;
}

.sidebar.collapsed .sidebar-content {
  opacity: 0;
  transform: translateX(-20px);
  pointer-events: none;
}

.sidebar-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  transition: opacity 0.3s ease-in-out, transform 0.3s ease-in-out;
  min-width: 260px;
}

.sidebar-top {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sidebar-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-top: 14px;
}

.sidebar-scroll::-webkit-scrollbar {
  width: 6px;
}

.sidebar-scroll::-webkit-scrollbar-thumb {
  background: #e5e7eb;
  border-radius: 999px;
}

.new-btn {
  width: 100%;
  height: 44px;
  border: none;
  border-radius: 12px;
  background: #2563eb;
  color: #fff;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  cursor: pointer;
}

.plus {
  width: 22px;
  height: 22px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  line-height: 1;
}

.search {
  position: relative;
}

.search input {
  width: 100%;
  height: 42px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #f8fafc;
  padding: 0 42px 0 14px;
  box-sizing: border-box;
  font-size: 14px;
  color: #0f172a;
  outline: none;
}

.search input::placeholder {
  color: #94a3b8;
  font-weight: 600;
}

.search-ico {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
}

.group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.group-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px;
}

.group-title {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 700;
}

.clear {
  border: none;
  background: none;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.item {
  width: 100%;
  height: 54px;
  border: none;
  background: transparent;
  border-radius: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 14px;
  box-sizing: border-box;
  cursor: pointer;
  color: #64748b;
  position: relative;
}

.item:hover {
  background: #f8fafc;
}

.item.active {
  background: #f3f4f6;
}

.item-ico {
  color: #94a3b8;
  flex: 0 0 auto;
}

.item.active .item-ico {
  color: #2563eb;
}

.txt {
  flex: 1;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.2px;
  padding-right: 2px;
}

.title-edit {
  flex: 1;
  height: 34px;
  max-width: calc(100%);
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  background: transparent;
  padding: 0 10px;
  margin: 0;
  outline: none;
  font-size: 14px;
  font-weight: 500;
  color: inherit;
  box-shadow: none;
}

.title-edit:focus {
  border-color: #cbd5e1;
  background: #ffffff;
}

.item:has(.title-edit) {
  background: inherit;
}

.actions {
  display: inline-flex;
  align-items: center;
  gap: 0;
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.16s ease;
  z-index: 2;
}

.item:hover .actions {
  opacity: 1;
  pointer-events: auto;
}

.item:has(.title-edit) .actions {
  display: none;
  pointer-events: none;
}


.item:hover .txt {
  padding-right: 54px;
}

.icon-btn {
  width: 28px;
  height: 34px;
  border-radius: 10px;
  border: none;
  background: transparent;
  color: currentColor;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: color 0.18s ease, transform 0.18s ease, background 0.18s ease;
  padding: 0;
}

.icon-svg {
  display: block;
  width: 18px;
  height: 18px;
  stroke: #94a3b8;
}

.item.active .txt {
  color: #2563eb;
}

.icon-btn:hover {
  background: rgba(148, 163, 184, 0.12);
  transform: translateY(-1px);
}

.icon-btn:active {
  transform: translateY(0);
}

.icon-btn.danger:hover {
  background: rgba(239, 68, 68, 0.14);
}

.icon-btn.edit:hover {
  background: rgba(37, 99, 235, 0.12);
}


.footer {
  margin-top: auto;
  padding-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.user {
  width: 100%;
  height: 56px;
  border-radius: 16px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 12px;
  box-sizing: border-box;
}

.logout {
  width: 100%;
  height: 44px;
  border-radius: 14px;
  border: 1px solid #e5e7eb;
  background: #f8fafc;
  color: #0f172a;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease, color 0.18s ease;
}

.logout:hover {
  background: #ffffff;
  border-color: #cbd5e1;
  box-shadow: 0 6px 16px rgba(2, 6, 23, 0.08);
  transform: translateY(-1px);
}

.logout:active {
  transform: translateY(0);
  box-shadow: none;
}

.avatar {
  width: 34px;
  height: 34px;
  border-radius: 999px;
}

.name {
  font-weight: 700;
  color: #0f172a;
}
</style>
