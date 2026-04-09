const state = { mode: 'text', items: [] };

const form = document.querySelector('#generateForm');
const promptInput = document.querySelector('#prompt');
const imagePathInput = document.querySelector('#imagePath');
const imageFileInput = document.querySelector('#imageFile');
const aspectRatioInput = document.querySelector('#aspectRatio');
const secondsInput = document.querySelector('#seconds');
const statusText = document.querySelector('#statusText');
const historyGrid = document.querySelector('#historyGrid');
const jobCount = document.querySelector('#jobCount');
const totalGenerationTime = document.querySelector('#totalGenerationTime');
const refreshButton = document.querySelector('#refreshButton');
const modeButtons = [...document.querySelectorAll('.mode-chip')];
const imageOnlyFields = [...document.querySelectorAll('.image-only')];

function setMode(mode) {
  state.mode = mode;
  modeButtons.forEach((button) => button.classList.toggle('active', button.dataset.mode === mode));
  imageOnlyFields.forEach((field) => field.classList.toggle('hidden', mode !== 'image'));
}

function escapeHtml(value) {
  return String(value || '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
}

function prettyStatus(status) {
  return { submitting: 'Submitting', processing: 'Processing', completed: 'Completed', failed: 'Failed' }[status] || status;
}

function getElapsedSeconds(item) {
  if (Number.isFinite(Number(item.totalElapsedSeconds))) return Number(item.totalElapsedSeconds);
  if (item.status !== 'completed' || !item.createdAt) return null;
  const started = new Date(item.createdAt).getTime();
  const ended = new Date(item.completedAt || item.updatedAt || item.createdAt).getTime();
  if (!Number.isFinite(started) || !Number.isFinite(ended) || ended < started) return null;
  return Math.round((ended - started) / 1000);
}

function render() {
  jobCount.textContent = String(state.items.length);
  const totalSeconds = state.items.reduce((sum, item) => sum + (getElapsedSeconds(item) || 0), 0);
  totalGenerationTime.textContent = `${totalSeconds} 秒`;
  if (!state.items.length) {
    historyGrid.innerHTML = '<div class="placeholder">还没有历史记录。提交一次任务，卡片会像剪辑瀑布流一样铺开。</div>';
    return;
  }

  historyGrid.innerHTML = state.items.map((item) => {
    const hasVideo = item.videoPath;
    const elapsedSeconds = getElapsedSeconds(item);
    const imagePreview = item.mode === 'image' && item.imagePath && !/^https?:\/\//i.test(item.imagePath)
      ? `<img class="thumb" src="/api/preview?path=${encodeURIComponent(item.imagePath)}" alt="input">`
      : item.mode === 'image' && item.imagePath
        ? `<img class="thumb" src="${escapeHtml(item.imagePath)}" alt="input">`
        : '<div class="thumb" style="min-height:180px;display:grid;place-items:center;color:var(--muted)">Text to Video</div>';

    return `
      <article class="card status-${escapeHtml(item.status)}">
        <div class="card-media">
          ${hasVideo ? `<video src="${escapeHtml(item.videoPath)}" controls preload="metadata"></video>` : imagePreview}
          <span class="card-badge">${escapeHtml(prettyStatus(item.status))}</span>
        </div>
        <div class="card-body">
          <h3>${item.mode === 'image' ? 'Image to Video' : 'Text to Video'}</h3>
          <p class="prompt">${escapeHtml(item.prompt)}</p>
          <div class="meta">
            <span>比例 · ${escapeHtml(item.aspectRatio)}</span>
            <span>时长 · ${escapeHtml(item.seconds || 5)} 秒</span>
            ${elapsedSeconds != null ? `<span>生成耗时 · ${escapeHtml(elapsedSeconds)} 秒</span>` : ''}
            <span>模型 · ${escapeHtml(item.model || 'veo_3_1-fast-4K')}</span>
            ${item.taskId ? `<span>任务 ID · ${escapeHtml(item.taskId)}</span>` : ''}
            ${item.error ? `<span style="color:var(--danger)">错误 · ${escapeHtml(item.error)}</span>` : ''}
            ${item.localPath ? `<span>本地文件 · ${escapeHtml(item.localPath)}</span>` : ''}
          </div>
          <div class="progress"><div class="progress-bar" style="width:${Number(item.progress || 0)}%"></div></div>
          <div class="card-actions">
            <button class="card-action" data-action="reuse" data-job-id="${escapeHtml(item.jobId)}">复用提示词</button>
            <button class="card-action danger" data-action="delete" data-job-id="${escapeHtml(item.jobId)}">删除记录</button>
          </div>
        </div>
      </article>
    `;
  }).join('');
}

async function loadHistory() {
  const response = await fetch('/api/history');
  const data = await response.json();
  state.items = data.items || [];
  render();
}

function upsertItem(item) {
  const index = state.items.findIndex((existing) => existing.jobId === item.jobId);
  if (index === -1) state.items.unshift(item);
  else state.items[index] = item;
  state.items.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
  render();
}

function removeItem(jobId) {
  state.items = state.items.filter((item) => item.jobId !== jobId);
  render();
}

function reuseItem(jobId) {
  const item = state.items.find((entry) => entry.jobId === jobId);
  if (!item) return;
  setMode(item.mode || 'text');
  promptInput.value = item.prompt || '';
  aspectRatioInput.value = item.aspectRatio || '16:9';
  secondsInput.value = String(item.seconds || 5);
  imagePathInput.value = item.mode === 'image' && item.imagePath && /^https?:\/\//i.test(item.imagePath) ? item.imagePath : '';
  statusText.textContent = `已载入历史提示词 · ${item.taskId || item.jobId}`;
  promptInput.focus();
}

async function deleteItem(jobId) {
  const response = await fetch('/api/history/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jobId }),
  });
  const data = await response.json();
  if (!response.ok) {
    statusText.textContent = data.error || '删除失败';
    return;
  }
  removeItem(jobId);
  statusText.textContent = '已删除历史记录';
}

async function submit(event) {
  event.preventDefault();
  statusText.textContent = '正在提交…';

  let imageDataUrl = '';
  let imageFileName = '';
  const file = imageFileInput.files?.[0];
  if (state.mode === 'image' && file) {
    imageDataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(new Error('图片读取失败'));
      reader.readAsDataURL(file);
    });
    imageFileName = file.name;
  }

  const payload = {
    mode: state.mode,
    prompt: promptInput.value.trim(),
    aspectRatio: aspectRatioInput.value,
    seconds: secondsInput.value,
    imagePath: imagePathInput.value.trim(),
    imageDataUrl,
    imageFileName,
  };

  const response = await fetch('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    statusText.textContent = data.error || '提交失败';
    return;
  }
  statusText.textContent = `已提交 · ${data.taskId}`;
  if (state.mode === 'text') promptInput.value = '';
  if (state.mode === 'image') imageFileInput.value = '';
}

function connectEvents() {
  const source = new EventSource('/api/events');
  source.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.item) upsertItem(payload.item);
    if (payload.type === 'history:delete' && payload.jobId) removeItem(payload.jobId);
  };
}

modeButtons.forEach((button) => button.addEventListener('click', () => setMode(button.dataset.mode)));
refreshButton.addEventListener('click', loadHistory);
form.addEventListener('submit', submit);
historyGrid.addEventListener('click', (event) => {
  const button = event.target.closest('[data-action]');
  if (!button) return;
  if (button.dataset.action === 'reuse') return reuseItem(button.dataset.jobId);
  if (button.dataset.action === 'delete') deleteItem(button.dataset.jobId);
});

setMode('text');
loadHistory();
connectEvents();
