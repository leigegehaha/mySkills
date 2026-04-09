const state = { items: [] };

const form = document.querySelector('#generateForm');
const sceneInput = document.querySelector('#scene');
const dialogueInput = document.querySelector('#dialogue');
const imagePathInput = document.querySelector('#imagePath');
const imageFileInput = document.querySelector('#imageFile');
const shotStyleInput = document.querySelector('#shotStyle');
const aspectRatioInput = document.querySelector('#aspectRatio');
const sizeInput = document.querySelector('#size');
const durationInput = document.querySelector('#duration');
const statusText = document.querySelector('#statusText');
const historyGrid = document.querySelector('#historyGrid');
const jobCount = document.querySelector('#jobCount');
const totalGenerationTime = document.querySelector('#totalGenerationTime');
const refreshButton = document.querySelector('#refreshButton');

function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function getElapsedSeconds(item) {
  if (Number.isFinite(Number(item.totalElapsedSeconds))) return Number(item.totalElapsedSeconds);
  if (!item.createdAt) return null;
  const started = new Date(item.createdAt).getTime();
  const ended = new Date(item.completedAt || item.updatedAt || item.createdAt).getTime();
  if (!Number.isFinite(started) || !Number.isFinite(ended) || ended < started) return null;
  return Math.round((ended - started) / 1000);
}

function prettyStatus(item) {
  if (item.status === 'failed') return 'Failed';
  if (item.status === 'completed') return 'Completed';
  const map = {
    queued: 'Queued',
    image: 'Image',
    image_completed: 'Image Ready',
    video_submitting: 'Submitting Video',
    video: 'Video',
    completed: 'Completed',
  };
  return map[item.stage] || item.status || 'Processing';
}

function shotStyleLabel(style) {
  const map = {
    selfie: 'iPhone 自拍',
    'rear-fixed': '后置固定',
    'rear-handheld': '后置手持',
    cinematic: '电影感',
  };
  return map[style] || style;
}

function render() {
  jobCount.textContent = String(state.items.length);
  const totalSeconds = state.items.reduce((sum, item) => sum + (getElapsedSeconds(item) || 0), 0);
  totalGenerationTime.textContent = `${totalSeconds} 秒`;

  if (!state.items.length) {
    historyGrid.innerHTML = '<div class="placeholder">还没有历史记录。先上传照片跑一条试试。</div>';
    return;
  }

  historyGrid.innerHTML = state.items.map((item) => `
    <article class="card status-${escapeHtml(item.status)}">
      <div class="card-media stack">
        ${item.generatedVideoPath
          ? `<video src="${escapeHtml(item.generatedVideoPath)}" controls preload="metadata"></video>`
          : item.generatedImagePath
            ? `<img class="thumb" src="${escapeHtml(item.generatedImagePath)}" alt="generated image">`
            : item.sourceImagePath
              ? `<img class="thumb" src="/api/preview?path=${encodeURIComponent(item.sourceImagePath)}" alt="source image">`
              : '<div class="thumb empty">Waiting</div>'}
        <span class="card-badge">${escapeHtml(prettyStatus(item))}</span>
      </div>
      <div class="card-body">
        <h3>${escapeHtml(shotStyleLabel(item.shotStyle))}</h3>
        <p class="prompt">${escapeHtml(item.scene)}</p>
        ${item.dialogue ? `<p class="dialogue">台词：${escapeHtml(item.dialogue)}</p>` : ''}
        ${item.generatedImagePath ? `<img class="mini-thumb" src="${escapeHtml(item.generatedImagePath)}" alt="keyframe">` : ''}
        <div class="meta">
          <span>比例 · ${escapeHtml(item.aspectRatio)}</span>
          <span>清晰度 · ${escapeHtml(item.size)}</span>
          <span>时长 · ${escapeHtml(item.duration)} 秒</span>
          <span>模型 · ${escapeHtml(item.model || '-')}</span>
          ${getElapsedSeconds(item) != null ? `<span>耗时 · ${escapeHtml(getElapsedSeconds(item))} 秒</span>` : ''}
          ${item.taskId ? `<span>任务 ID · ${escapeHtml(item.taskId)}</span>` : ''}
          ${item.error ? `<span class="error">错误 · ${escapeHtml(item.error)}</span>` : ''}
        </div>
        <details class="details">
          <summary>查看提示词</summary>
          ${item.imagePrompt ? `<p><strong>图片提示词：</strong>${escapeHtml(item.imagePrompt)}</p>` : ''}
          ${item.videoPrompt ? `<p><strong>视频提示词：</strong>${escapeHtml(item.videoPrompt)}</p>` : ''}
        </details>
        <div class="progress"><div class="progress-bar" style="width:${Number(item.progress || 0)}%"></div></div>
        <div class="card-actions">
          <button class="card-action" data-action="reuse" data-job-id="${escapeHtml(item.jobId)}">复用配置</button>
          <button class="card-action danger" data-action="delete" data-job-id="${escapeHtml(item.jobId)}">删除记录</button>
        </div>
      </div>
    </article>
  `).join('');
}

async function loadHistory() {
  const response = await fetch('/api/history');
  const data = await response.json();
  state.items = data.items || [];
  render();
}

function upsertItem(item) {
  const index = state.items.findIndex((entry) => entry.jobId === item.jobId);
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
  sceneInput.value = item.scene || '';
  dialogueInput.value = item.dialogue || '';
  imagePathInput.value = item.sourceImagePath || '';
  shotStyleInput.value = item.shotStyle || 'selfie';
  aspectRatioInput.value = item.aspectRatio || '9:16';
  sizeInput.value = item.size || '720P';
  durationInput.value = String(item.duration || 6);
  statusText.textContent = `已载入历史配置 · ${item.jobId}`;
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
  if (file) {
    imageDataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(new Error('图片读取失败'));
      reader.readAsDataURL(file);
    });
    imageFileName = file.name;
  }

  const payload = {
    scene: sceneInput.value.trim(),
    dialogue: dialogueInput.value.trim(),
    imagePath: imagePathInput.value.trim(),
    imageDataUrl,
    imageFileName,
    shotStyle: shotStyleInput.value,
    aspectRatio: aspectRatioInput.value,
    size: sizeInput.value,
    duration: durationInput.value,
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

  statusText.textContent = `已提交 · ${data.jobId}`;
  imageFileInput.value = '';
}

function connectEvents() {
  const source = new EventSource('/api/events');
  source.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.item) upsertItem(payload.item);
    if (payload.type === 'history:delete' && payload.jobId) removeItem(payload.jobId);
  };
}

refreshButton.addEventListener('click', loadHistory);
form.addEventListener('submit', submit);
historyGrid.addEventListener('click', (event) => {
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const { action, jobId } = button.dataset;
  if (action === 'reuse') reuseItem(jobId);
  if (action === 'delete') deleteItem(jobId);
});

loadHistory();
connectEvents();
