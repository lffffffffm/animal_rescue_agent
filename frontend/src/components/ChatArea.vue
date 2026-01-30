<template>
  <main class="chat">
    <header class="chat-header">
      <div class="brand">
        <span class="brand-badge">
          <img class="brand-animal cat" :src="CatIcon" alt="" />
        </span>
        <span class="brand-text">PawPal</span>
      </div>
      <div class="chat-title" v-if="activeThread">{{ activeThread.title }}</div>
    </header>

    <section class="chat-body">
      <div class="thread">
        <div v-if="!activeThread" class="empty">选择左侧会话或点击 New 开始</div>

        <template v-else>
          <div class="msgs" ref="msgsRef">
            <div v-for="m in messages" :key="m.id" class="msg" :class="m.role">
              <div class="bubble">
                <div class="name" v-if="m.role === 'assistant'">PawPal</div>
                <div class="text" v-html="format(m.content)"></div>
              </div>
            </div>

            <div v-if="loading" class="msg assistant">
              <div class="bubble">
                <div class="name">PawPal</div>
                <div class="text">正在思考...</div>
              </div>
            </div>

            <div v-if="error" class="error">{{ error }}</div>
          </div>

          <div class="composer">
            <div class="deepseek-box">
              <div v-if="imagePreview" class="image-preview">
                <img :src="imagePreview" alt="preview" />
                <button class="remove" type="button" @click="clearImage" aria-label="remove">
                  ×
                </button>
              </div>

              <div class="deepseek-top">
                <textarea
                  v-model="draft"
                  class="input"
                  placeholder="给 PawPal 发送消息"
                  rows="1"
                  @keydown.enter.prevent="onSend"
                ></textarea>

                <input
                  ref="fileRef"
                  class="file"
                  type="file"
                  accept="image/*"
                  @change="onPickImage"
                />

                <button class="icon" type="button" aria-label="upload" @click.stop="openFile">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>
                </button>

                <button class="send" type="button" @click="onSend" :disabled="loading || (!draft.trim() && !imageFile)" aria-label="send">
                  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5"/><path d="M5 12l7-7 7 7"/></svg>
                </button>
              </div>

              <div class="deepseek-bottom">
                <button class="pill" type="button" :class="{ on: enableWeb }" @click.stop="$emit('update:enableWeb', !enableWeb)">
                  <svg class="pill-ico" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
                  <span>联网</span>
                </button>

                <button class="pill" type="button" :class="{ on: enableMap }" @click.stop="$emit('update:enableMap', !enableMap)">
                  <svg class="pill-ico" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" x2="9" y1="3" y2="18"/><line x1="15" x2="15" y1="6" y2="21"/></svg>
                  <span>地图</span>
                </button>
              </div>
            </div>
          </div>
        </template>
      </div>
    </section>
  </main>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import CatIcon from '../assets/cat3.svg'


const props = defineProps({
  user: { type: Object, required: true },
  activeThread: { type: Object, default: null },
  messages: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  enableWeb: { type: Boolean, default: false },
  enableMap: { type: Boolean, default: false }
})

const emit = defineEmits(['send', 'edit-current', 'update:enableWeb', 'update:enableMap'])

const draft = ref('')
const msgsRef = ref(null)

const fileRef = ref(null)
const imageFile = ref(null)
const imagePreview = ref('')

function openFile() {
  fileRef.value?.click()
}

function clearImage() {
  imageFile.value = null
  imagePreview.value = ''
  if (fileRef.value) fileRef.value.value = ''
}

function onPickImage(e) {
  const f = e?.target?.files?.[0]
  if (!f) return
  imageFile.value = f

  const url = URL.createObjectURL(f)
  imagePreview.value = url
}

function escapeHtml(str) {
  return String(str)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
}

function format(text) {
  const safe = escapeHtml(text)
  return safe
    .replaceAll('\n', '<br />')
    .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
}

function onSend() {
  const text = draft.value.trim()
  if (props.loading) return
  if (!text && !imageFile.value) return

  // 不改后端：图片先作为占位文本发送（你要后端支持 multipart 再接）
  const payload = imageFile.value ? `[image] ${text}`.trim() : text

  draft.value = ''
  clearImage()
  emit('send', payload)
}

async function scrollToBottom() {
  await nextTick()
  const el = msgsRef.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

watch(
  () => [props.activeThread?.id, props.messages.length, props.loading],
  () => {
    scrollToBottom()
  }
)
</script>

<style scoped>
.chat {
  flex: 1;
  height: 100vh;
  background: #ffffff;
  display: flex;
  flex-direction: column;
}

.chat-header {
  position: relative;
  height: 54px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  color: #94a3b8;
  font-size: 12px;
  font-weight: 700;
}

.chat-title {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  color: #94a3b8;
  font-size: 14px;
  font-weight: 700;
}

.brand {
  display: inline-flex;
  align-items: center;
  font-size: 15px;
  gap: 8px;
  position: absolute;
  left: 22px;
  top: 50%;
  transform: translateY(-50%);
  color: #2563eb;
}

.brand-badge {
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: start;
  position: relative;
  flex: 0 0 auto;
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.18);
}

.brand-animal {
  display: block;
  position: absolute;
  left: 50%;
  top: 50%;
  color: #1d4ed8;
  scale: 1.5;
  margin-left: 20px;
  margin-top: 15px;
}

.brand-animal.cat {
  transform: translate(-56%, -52%) ;
  width: 30px;
  height: 30px;
  stroke-width: 5%;
}

.brand-text {
  margin-left: 25px;
  margin-top: 15px;
  font-size: 20px;
  letter-spacing: 0.2px;
}

.chat-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  justify-content: center;
}

.thread {
  width: min(920px, 92%);
  height: 100%;
  display: flex;
  flex-direction: column;
}

.empty {
  margin-top: 120px;
  color: #94a3b8;
  text-align: center;
  font-weight: 700;
}

.thread-title {
  margin-top: 18px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.title {
  font-weight: 800;
  color: #0f172a;
  font-size: 15px;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.msgs {
  margin-top: 18px;
  flex: 1;
  overflow-y: auto;
  padding: 0 2px;
}

.msgs::-webkit-scrollbar {
  width: 6px;
}

.msgs::-webkit-scrollbar-thumb {
  background: #e5e7eb;
  border-radius: 999px;
}

.msg {
  display: flex;
  margin: 12px 0;
}

.msg.user {
  justify-content: flex-start;
}

.msg.assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 760px;
  border-radius: 10px;
  padding: 12px 14px;
  border: 1px solid #eef2f7;
  background: #ffffff;
}

.msg.user .bubble {
  border-color: transparent;
  background: transparent;
  padding: 0;
}

.msg.user .text {
  color: #0f172a;
  font-weight: 600;
}

.name {
  color: #2563eb;
  font-weight: 800;
  font-size: 12px;
  margin-bottom: 8px;
}

.text {
  color: #334155;
  font-size: 14px;
  line-height: 1.8;
}

.composer {
  padding: 18px 0 26px;
  position: relative;
  z-index: 10;
}

.deepseek-box {
  border: 1px solid #e5e7eb;
  border-radius: 20px;
  background: #ffffff;
  box-shadow: 0 16px 40px rgba(2, 6, 23, 0.08);
  padding: 12px;
  position: relative;
}

.image-preview {
  display: inline-flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 10px;
}

.image-preview img {
  width: 120px;
  height: 80px;
  object-fit: cover;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
}

.image-preview .remove {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  color: #64748b;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.deepseek-top {
  display: flex;
  align-items: center;
  gap: 10px;
}

.input {
  resize: none;
  flex: 1;
  border: none;
  outline: none;
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  padding: 8px 6px;
  background: transparent;
}

.input::placeholder {
  color: #94a3b8;
  font-weight: 700;
}

.file {
  display: none;
}

.icon {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
}

.send {
  width: 44px;
  height: 44px;
  border-radius: 999px;
  border: none;
  background: #2563eb;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
}

.send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.deepseek-bottom {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  position: relative;
  z-index: 2;
}

.pill {
  height: 34px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  color: #0f172a;
  font-weight: 800;
  font-size: 12px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.pill-ico {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
}

.pill.on {
  border-color: #c7d2fe;
  background: #eef2ff;
  color: #1d4ed8;
}

.pill.on .pill-ico {
  stroke: #1d4ed8;
}

.error {
  margin-top: 8px;
  color: #ef4444;
  font-weight: 700;
  font-size: 12px;
}
</style>
