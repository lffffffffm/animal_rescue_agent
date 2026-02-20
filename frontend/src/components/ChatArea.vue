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
              <!-- 纯图片消息：不包裹气泡，直接展示图片块 -->
              <template v-if="m.images && m.images.length && !m.content">
                <div class="media-content" :class="m.role">
                  <div class="images-grid">
                    <img v-for="(src, idx) in m.images" :key="`${m.id}:${idx}`" :src="resolveImg(src)" alt="uploaded image" class="clickable-img" @click.stop="openPreview(m.images, idx)" />
                  </div>
                </div>
              </template>

              <template v-else>
                <div class="bubble" :class="{ assistant: m.role === 'assistant', user: m.role === 'user' }">
                <div class="name" v-if="m.role === 'assistant'">PawPal</div>

                                <button
                  v-if="m.role === 'assistant' && m.content"
                  class="copy"
                  type="button"
                  @click.stop="copyText(m.id, m.content)"
                  aria-label="copy"
                >
                  <svg v-if="copiedId === m.id" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                  <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                </button>

                <div class="text">
                  <div v-if="m.images && m.images.length" class="images">
                    <img v-for="(src, idx) in m.images" :key="`${m.id}:${idx}`" :src="resolveImg(src)" alt="uploaded image" class="clickable-img" @click.stop="openPreview(m.images, idx)" />
                  </div>

                  <div v-if="m.role === 'assistant' && !m.content && loading">正在思考...</div>
                  <div v-else-if="m.content" v-html="format(m.content)" @click="handleCiteClick"></div>

                  <details
                    v-if="m.role === 'assistant' && m.meta && Array.isArray(m.meta.evidences) && m.meta.evidences.length"
                    class="evidence"
                    @click.stop
                  >
                    <summary>
                      <span class="evidence-summary-title">参考资料</span>
                      <span class="evidence-summary-count">{{ m.meta.evidences.length }}</span>
                      <span class="evidence-summary-hint">点击展开</span>
                    </summary>

                    <div class="evidence-list">
                      <div
                        v-for="(ev, idx) in m.meta.evidences"
                        :key="idx"
                        class="evidence-item"
                        :data-index="idx + 1"
                      >
                        <div class="evidence-title">
                          <span class="t">{{ pickTitle(ev) }}</span>
                          <div class="tags-row">
                            <span v-if="pickSpecies(ev)" class="tag species">{{ pickSpecies(ev) }}</span>
                            <span
                              v-if="pickUrgency(ev)"
                              class="tag urgency"
                              :class="String(pickUrgency(ev)).toLowerCase()"
                            >
                              {{ pickUrgency(ev) }}
                            </span>
                          </div>
                        </div>

                        <div class="evidence-meta-row">
                          <div v-if="pickPlatform(ev)" class="meta-item">
                            <span class="label">来源</span>
                            <span class="val">{{ pickPlatform(ev) }}</span>
                          </div>
                          <div v-if="pickCategory(ev)" class="meta-item">
                            <span class="label">分类</span>
                            <span class="val">{{ pickCategory(ev) }}</span>
                          </div>

                          <a
                            v-if="pickUrl(ev)"
                            class="evidence-link"
                            :href="pickUrl(ev)"
                            target="_blank"
                            rel="noopener noreferrer"
                            @click.stop
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                            查看原文
                          </a>
                        </div>

                        <div v-if="pickSnippet(ev)" class="evidence-snippet">{{ pickSnippet(ev) }}</div>
                      </div>
                    </div>
                  </details>
                </div>
              </div>
              </template>
            </div>


            <div v-if="error" class="error">{{ error }}</div>
          </div>

          <div class="composer">
            <div class="deepseek-box">
              <div v-if="imagePreviews.length" class="image-preview">
                <div v-for="(src, idx) in imagePreviews" :key="src" class="thumb">
                  <img :src="resolveImg(src)" alt="preview" />
                  <button class="remove" type="button" @click="removeImage(idx)" aria-label="remove">
                    ×
                  </button>
                </div>
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
                  multiple
                  @change="onPickImage"
                />

                <button class="icon" type="button" aria-label="upload" @click.stop="openFile">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>
                </button>

                <button class="send" type="button" @click="onSend" :disabled="loading || (!draft.trim() && !imageFiles.length)" aria-label="send">
                  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5"/><path d="M5 12l7-7 7 7"/></svg>
                </button>
              </div>

              <div class="deepseek-bottom">
                <button class="pill" type="button" :class="{ on: enableWeb }" @click.stop="$emit('update:enableWeb', !enableWeb)">
                  <svg class="pill-ico" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
                  <span>联网</span>
                </button>

                <button class="pill" type="button" :class="{ on: enableMap }" title="开启后可获取附近医疗资源" @click.stop="$emit('update:enableMap', !enableMap)">
                  <svg class="pill-ico" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" x2="9" y1="3" y2="18"/><line x1="15" x2="15" y1="6" y2="21"/></svg>
                  <span>地图</span>
                </button>
              </div>
            </div>
          </div>

          <div v-if="previewOpen" class="img-modal" @click.self="closePreview">
            <button class="img-modal-close" type="button" @click.stop="closePreview" aria-label="close">×</button>
            <button v-if="previewImages.length > 1" class="img-modal-nav prev" type="button" @click.stop="prevPreview" aria-label="prev">‹</button>
            <img class="img-modal-img" :src="previewImages[previewIndex]" alt="preview" />
            <button v-if="previewImages.length > 1" class="img-modal-nav next" type="button" @click.stop="nextPreview" aria-label="next">›</button>
          </div>
        </template>
      </div>
    </section>
  </main>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import CatIcon from '../assets/cat3.svg'

function pickTitle(ev) {
  return ev?.metadata?.title || ev?.title || ev?.metadata?.source_info?.url || ev?.metadata?.url || ev?.url || '未命名资料'
}

function pickSpecies(ev) {
  return ev?.metadata?.species || ev?.species || ''
}

function pickUrgency(ev) {
  return ev?.metadata?.urgency || ev?.urgency || ''
}

function pickCategory(ev) {
  return ev?.metadata?.category || ev?.category || ''
}

function pickPlatform(ev) {
  return ev?.metadata?.source_info?.platform || ev?.metadata?.platform || ev?.platform || ''
}

function pickUrl(ev) {
  return ev?.metadata?.source_info?.url || ev?.metadata?.url || ev?.url || ''
}

function pickSnippet(ev) {
  // 兼容你给的结构：page_content + metadata
  const pc = ev?.page_content || ev?.content || ev?.text || ''
  if (!pc) return ''
  // 简单截断，避免撑爆 UI
  return String(pc).replace(/\s+/g, ' ').slice(0, 160) + (String(pc).length > 160 ? '…' : '')
}

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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

function resolveImg(src) {
  if (!src) return src
  const s = String(src)
  // 预览/内联资源不应拼接后端地址
  if (/^(blob:|data:|file:)/i.test(s)) return s
  // 若 src 已含 http(s)，直接返回
  if (/^https?:\/\//i.test(s)) return s
  // 否则拼接后端地址
  return `${API_BASE_URL}${s}`
}

const previewOpen = ref(false)
const previewImages = ref([])
const previewIndex = ref(0)

function openPreview(images, idx = 0) {
  previewImages.value = (images || []).map(resolveImg)
  previewIndex.value = idx
  previewOpen.value = true
}

function closePreview() {
  previewOpen.value = false
}

function nextPreview() {
  if (!previewImages.value.length) return
  previewIndex.value = (previewIndex.value + 1) % previewImages.value.length
}

function prevPreview() {
  if (!previewImages.value.length) return
  previewIndex.value = (previewIndex.value - 1 + previewImages.value.length) % previewImages.value.length
}

const draft = ref('')
const msgsRef = ref(null)

const fileRef = ref(null)
const imageFiles = ref([])
const imagePreviews = ref([])

function openFile() {
  if (imageFiles.value.length >= 4) {
    // 可以在这里加一个提示，比如 alert('最多上传4张图片')
    return
  }
  fileRef.value?.click()
}

function removeImage(index) {
  imageFiles.value.splice(index, 1)
  const [removedUrl] = imagePreviews.value.splice(index, 1)
  if (removedUrl) URL.revokeObjectURL(removedUrl)
  // 清空 file input 的值，以便可以重新选择相同的文件
  if (fileRef.value) fileRef.value.value = ''
}

function clearImages() {
  imagePreviews.value.forEach(URL.revokeObjectURL)
  imageFiles.value = []
  imagePreviews.value = []
  if (fileRef.value) fileRef.value.value = ''
}

function onPickImage(e) {
  const files = e.target.files
  if (!files) return

  const remainingSlots = 4 - imageFiles.value.length
  const filesToTake = Array.from(files).slice(0, remainingSlots)

  for (const f of filesToTake) {
    imageFiles.value.push(f)
    imagePreviews.value.push(URL.createObjectURL(f))
  }

  // 清空 file input 的值
  if (fileRef.value) fileRef.value.value = ''
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
    .replace(/\[(\d+)\]/g, (match, num) => {
      return `<a class="cite-anchor" href="javascript:void(0)" data-num="${num}">[${num}]</a>`
    })
}

const copiedId = ref(null)
let copiedTimer = null

function handleCiteClick(e) {
  const anchor = e.target.closest('.cite-anchor')
  if (!anchor) return

  const numStr = anchor.getAttribute('data-num')
  const num = Number(numStr)
  if (!Number.isFinite(num) || num <= 0) return

  // 关键：只在“当前这条消息气泡”内查找 evidence，避免总是命中第一个
  const bubble = anchor.closest('.bubble')
  const evidenceDetails = bubble?.querySelector('.evidence')
  if (!evidenceDetails) return

  evidenceDetails.open = true

  const item = evidenceDetails.querySelector(`.evidence-item:nth-child(${num})`)
  if (!item) return

  item.scrollIntoView({ behavior: 'smooth', block: 'center' })
  item.classList.remove('highlight-flash')
  // 强制 reflow 以便重复点击也能触发动画
  void item.offsetWidth
  item.classList.add('highlight-flash')
}

async function copyText(id, text) {
  const t = String(text || '')
  if (!t) return

  try {
    await navigator.clipboard.writeText(t)
  } catch (e) {
    // fallback
    const ta = document.createElement('textarea')
    ta.value = t
    ta.style.position = 'fixed'
    ta.style.left = '-9999px'
    document.body.appendChild(ta)
    ta.focus()
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }

  copiedId.value = id
  if (copiedTimer) clearTimeout(copiedTimer)
  copiedTimer = setTimeout(() => {
    copiedId.value = null
  }, 1200)
}

function onSend() {
  const text = draft.value.trim()
  if (props.loading) return
  if (!text && !imageFiles.value.length) return

  const textToSend = draft.value.trim()
  const filesToSend = [...imageFiles.value]
  const previewsToSend = [...imagePreviews.value]

  if (props.loading) return
  if (!textToSend && !filesToSend.length) return

  // 调试：打印将要发送的数据
  console.log('ChatArea emitting send event with previews:', previewsToSend);

  // 先 emit，再清空
  emit('send', { text: textToSend, files: filesToSend, previews: previewsToSend.map(resolveImg) })

  draft.value = ''
  clearImages()


}

async function scrollToBottom() {
  await nextTick()
  const el = msgsRef.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

watch(
  () => props.messages,
  () => {
    scrollToBottom()
  },
  { deep: true }
)
</script>

<style scoped>
.clickable-img {
  cursor: zoom-in;
}

.img-modal {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.72);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 24px;
}

.img-modal-img {
  max-width: min(92vw, 1100px);
  max-height: 86vh;
  object-fit: contain;
  border-radius: 12px;
  box-shadow: 0 18px 60px rgba(0, 0, 0, 0.45);
  background: #fff;
}

.img-modal-close,
.img-modal-nav {
  position: absolute;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.25);
  background: rgba(15, 23, 42, 0.6);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.img-modal-close {
  top: 20px;
  right: 20px;
  font-size: 32px;
  padding-bottom: 4px; /* 微调 '×' 的垂直位置 */
}

.img-modal-nav {
  font-size: 28px;
  padding-bottom: 2px; /* 微调 '‹' '›' 的垂直位置 */
}

.img-modal-nav {
  top: 50%;
  transform: translateY(-50%);
}

.img-modal-nav.prev {
  left: 20px;
}

.img-modal-nav.next {
  right: 20px;
}

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
  max-width: 500px; 
  white-space: nowrap; 
  overflow: hidden; 
  text-overflow: ellipsis;
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
  margin: 24px 0;
  width: 100%;
}

.msg.user {
  justify-content: flex-end;
}

.msg.assistant {
  justify-content: flex-start;
}

/* ===== 图片独立块（不进气泡） ===== */
.media-content {
  width: 100%;
  display: flex;
  margin: 6px 0 2px;
}

.media-content.user {
  justify-content: flex-end;
}

.media-content.assistant {
  justify-content: flex-start;
}

.images-grid {
  display: grid;
  gap: 8px;
  max-width: 340px;
}

/* 图片自适应展示：不定死每个框的宽高，按比例显示 */
.images-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-width: min(340px, 72vw);
}

.images-grid img {
  width: auto;
  height: auto;
  max-width: min(220px, 60vw);
  max-height: 180px;
  object-fit: contain; /* 完整展示，不裁切 */
  border-radius: 14px;
  border: 1px solid #e5e7eb;
  background: #fff;
}

.bubble {
  max-width: 85%;
  border-radius: 18px;
  padding: 16px 20px;
  position: relative;
  line-height: 1.6;
  transition: all 0.2s ease;
}

.bubble.user {
  background: #2563eb;
  color: #ffffff;
  border-radius: 18px 18px 2px 18px;
  box-shadow: 0 4px 15px rgba(37, 99, 235, 0.15);
  border: none;
}

.bubble.assistant {
  background: #ffffff;
  color: #1e293b;
  border-radius: 18px 18px 18px 2px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
}

.msg.user .text {
  color: #ffffff;
  font-weight: 500;
}

.name {
  color: #64748b;
  font-weight: 700;
  font-size: 11px;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.text {
  font-size: 15px;
}

.copy {
  position: absolute;
  right: -40px;
  top: 0;
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s ease;
}

.msg.assistant:hover .copy {
  opacity: 1;
}

.copy:hover {
  color: #2563eb;
  border-color: #2563eb;
  background: #eff6ff;
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
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 10px;
}

.thumb {
  position: relative;
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

.images {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.images img {
  max-width: 150px;
  max-height: 150px;
  border-radius: 12px;
  object-fit: cover;
  border: 1px solid #e5e7eb;
}

/* 1) 引用锚点上标样式（v-html 注入的 a，需要 :deep） */
:deep(.cite-anchor) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(37, 99, 235, 0.1);
  color: #2563eb;
  font-size: 10px;
  font-weight: 800;
  width: 16px;
  height: 16px;
  border-radius: 4px;
  text-decoration: none;
  margin: 0 2px;
  vertical-align: top;
  position: relative;
  top: -2px;
  cursor: pointer;
  transition: all 0.2s ease;
}

:deep(.cite-anchor:hover) {
  background: #2563eb;
  color: #ffffff;
  transform: scale(1.1);
}

/* 2) 参考资料容器整体（作为“助手气泡内附录区”） */
.evidence {
  margin-top: 18px;
  border: none;
  border-top: 1px solid #eef2f7;
  border-radius: 0;
  background: transparent;
  overflow: visible;
  transition: none;
}

.evidence[open] {
  background: transparent;
  box-shadow: none;
}

.evidence > summary {
  padding: 14px 0 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  list-style: none;
  user-select: none;
}

.evidence > summary::-webkit-details-marker {
  display: none;
}

.evidence-summary-title {
  font-weight: 900;
  color: #64748b;
  font-size: 12px;
  margin-right: 8px;
}

.evidence-summary-count {
  background: #f1f5f9;
  color: #64748b;
  font-size: 11px;
  font-weight: 900;
  padding: 1px 8px;
  border-radius: 999px;
}

.evidence-summary-hint {
  margin-left: auto;
  font-size: 11px;
  color: #94a3b8;
  font-weight: 700;
}

.evidence[open] .evidence-summary-hint {
  display: none;
}

/* 3) 列表与条目（轻量、与正文融合） */
.evidence-list {
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0;
  max-height: none;
  overflow: visible;
}

.evidence-item {
  position: relative;
  border: none;
  border-top: 1px solid #f1f5f9;
  border-radius: 0;
  padding: 14px 0;
  background: transparent;
  transition: background 0.15s ease;
}

.evidence-item:hover {
  border-color: #f1f5f9;
  background: rgba(248, 250, 252, 0.6);
  transform: none;
}

/* 编号改为与正文引用一致的 [n]，更像“引文” */
.evidence-item::before {
  content: "[" attr(data-index) "]";
  position: static;
  display: inline-block;
  margin-right: 8px;
  color: #2563eb;
  font-size: 12px;
  font-weight: 900;
}

.evidence-title {
  display: inline-flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
  vertical-align: top;
}

.evidence-title .t {
  font-weight: 900;
  color: #1e293b;
  font-size: 14px;
  line-height: 1.4;
  padding-right: 34px;
}

.tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  font-size: 10px;
  font-weight: 900;
  padding: 2px 8px;
  border-radius: 6px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.tag.species { background: #f1f5f9; color: #475569; }
.tag.urgency.critical { background: #fee2e2; color: #dc2626; }
.tag.urgency.common { background: #f0fdf4; color: #166534; }
.tag.urgency.info { background: #e0f2fe; color: #0369a1; }

.evidence-meta-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.meta-item .label {
  font-size: 10px;
  color: #94a3b8;
  font-weight: 700;
}

.meta-item .val {
  font-size: 12px;
  color: #475569;
  font-weight: 800;
}

.evidence-link {
  margin-left: auto;
  font-size: 12px;
  font-weight: 900;
  color: #2563eb;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.evidence-link:hover {
  text-decoration: underline;
}

.evidence-snippet {
  margin-top: 10px;
  font-size: 13px;
  color: #64748b;
  line-height: 1.7;
  padding: 10px 12px;
  background: transparent;
  border-left: 3px solid #cbd5e1;
}

@keyframes evidence-flash {
  0% {
    background-color: transparent;
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0);
  }
  30% {
    background-color: rgba(59, 130, 246, 0.10);
    box-shadow: 0 0 0 6px rgba(59, 130, 246, 0.14);
  }
  100% {
    background-color: transparent;
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0);
  }
}

/* 高亮时做“内缩 + 圆角 + 外发光”，避免颜色贴边 */
.highlight-flash {
  position: relative;
  animation: evidence-flash 1.6s ease-out;
}

/* 用伪元素做高亮，不改变布局（避免与其它条目对不齐） */
.highlight-flash::after {
  content: "";
  position: absolute;
  inset: -6px -8px;
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.10);
  box-shadow: 0 0 0 6px rgba(59, 130, 246, 0.14);
  pointer-events: none;
  z-index: -1;
}
</style>
