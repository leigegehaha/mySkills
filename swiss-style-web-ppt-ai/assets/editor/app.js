const DEFAULT_SOUND_CONFIG = Object.freeze({
  preset: "cyber-brush",
  intensity: 1,
  brightness: 1,
  tail: 1,
  chirp: 1,
  stereo: 1,
});

const SOUND_PRESETS = {
  classic: {
    noiseDuration: 0.24,
    masterPeak: 0.056,
    masterMid: 0.016,
    masterEndTime: 0.22,
    noisePeak: 0.76,
    noiseMid: 0.22,
    noiseEndTime: 0.2,
    chirpPeak: 0.012,
    chirpStartTime: 0.011,
    chirpPeakTime: 0.024,
    chirpEndTime: 0.1,
    tickPeak: 0.016,
    tickStartTime: 0.014,
    tickPeakTime: 0.02,
    tickEndTime: 0.05,
    tailPeak: 0.008,
    tailStartTime: 0.04,
    tailPeakTime: 0.064,
    tailEndTime: 0.16,
    forward: {
      highpassStart: 900,
      highpassEnd: 1440,
      lowpassStart: 6200,
      lowpassEnd: 1320,
      bandpassStart: 1880,
      bandpassEnd: 880,
      panStart: -0.12,
      panEnd: 0.12,
      playbackRate: 1.08,
      chirpStart: 2180,
      chirpEnd: 980,
      tickStart: 1640,
      tickEnd: 1340,
      tailStart: 1020,
      tailEnd: 680,
    },
    backward: {
      highpassStart: 780,
      highpassEnd: 1260,
      lowpassStart: 5800,
      lowpassEnd: 1180,
      bandpassStart: 1660,
      bandpassEnd: 780,
      panStart: 0.12,
      panEnd: -0.12,
      playbackRate: 1.01,
      chirpStart: 1960,
      chirpEnd: 900,
      tickStart: 1480,
      tickEnd: 1260,
      tailStart: 920,
      tailEnd: 640,
    },
  },
  brush: {
    noiseDuration: 0.29,
    masterPeak: 0.072,
    masterMid: 0.018,
    masterEndTime: 0.28,
    noisePeak: 0.92,
    noiseMid: 0.3,
    noiseEndTime: 0.24,
    chirpPeak: 0.015,
    chirpStartTime: 0.012,
    chirpPeakTime: 0.026,
    chirpEndTime: 0.12,
    tickPeak: 0.018,
    tickStartTime: 0.015,
    tickPeakTime: 0.021,
    tickEndTime: 0.052,
    tailPeak: 0.01,
    tailStartTime: 0.05,
    tailPeakTime: 0.074,
    tailEndTime: 0.18,
    forward: {
      highpassStart: 1040,
      highpassEnd: 1720,
      lowpassStart: 7000,
      lowpassEnd: 1500,
      bandpassStart: 2340,
      bandpassEnd: 1020,
      panStart: -0.18,
      panEnd: 0.18,
      playbackRate: 1.18,
      chirpStart: 2520,
      chirpEnd: 1080,
      tickStart: 1800,
      tickEnd: 1420,
      tailStart: 1200,
      tailEnd: 740,
    },
    backward: {
      highpassStart: 860,
      highpassEnd: 1460,
      lowpassStart: 6400,
      lowpassEnd: 1320,
      bandpassStart: 1940,
      bandpassEnd: 900,
      panStart: 0.18,
      panEnd: -0.18,
      playbackRate: 1.05,
      chirpStart: 2220,
      chirpEnd: 980,
      tickStart: 1620,
      tickEnd: 1320,
      tailStart: 1060,
      tailEnd: 680,
    },
  },
  "cyber-brush": {
    noiseDuration: 0.28,
    masterPeak: 0.07,
    masterMid: 0.018,
    masterEndTime: 0.26,
    noisePeak: 0.85,
    noiseMid: 0.28,
    noiseEndTime: 0.22,
    chirpPeak: 0.018,
    chirpStartTime: 0.012,
    chirpPeakTime: 0.026,
    chirpEndTime: 0.12,
    tickPeak: 0.022,
    tickStartTime: 0.016,
    tickPeakTime: 0.022,
    tickEndTime: 0.055,
    tailPeak: 0.012,
    tailStartTime: 0.05,
    tailPeakTime: 0.075,
    tailEndTime: 0.19,
    forward: {
      highpassStart: 980,
      highpassEnd: 1600,
      lowpassStart: 6800,
      lowpassEnd: 1550,
      bandpassStart: 2200,
      bandpassEnd: 980,
      panStart: -0.18,
      panEnd: 0.2,
      playbackRate: 1.16,
      chirpStart: 2680,
      chirpEnd: 1120,
      tickStart: 1860,
      tickEnd: 1460,
      tailStart: 1280,
      tailEnd: 760,
    },
    backward: {
      highpassStart: 820,
      highpassEnd: 1360,
      lowpassStart: 6200,
      lowpassEnd: 1380,
      bandpassStart: 1900,
      bandpassEnd: 860,
      panStart: 0.18,
      panEnd: -0.2,
      playbackRate: 1.02,
      chirpStart: 2240,
      chirpEnd: 980,
      tickStart: 1640,
      tickEnd: 1320,
      tailStart: 1120,
      tailEnd: 660,
    },
  },
  "sharp-scan": {
    noiseDuration: 0.22,
    masterPeak: 0.084,
    masterMid: 0.02,
    masterEndTime: 0.2,
    noisePeak: 1.04,
    noiseMid: 0.34,
    noiseEndTime: 0.18,
    chirpPeak: 0.022,
    chirpStartTime: 0.008,
    chirpPeakTime: 0.018,
    chirpEndTime: 0.09,
    tickPeak: 0.026,
    tickStartTime: 0.012,
    tickPeakTime: 0.018,
    tickEndTime: 0.042,
    tailPeak: 0.01,
    tailStartTime: 0.036,
    tailPeakTime: 0.054,
    tailEndTime: 0.14,
    forward: {
      highpassStart: 1320,
      highpassEnd: 2320,
      lowpassStart: 7600,
      lowpassEnd: 1820,
      bandpassStart: 2660,
      bandpassEnd: 1140,
      panStart: -0.24,
      panEnd: 0.24,
      playbackRate: 1.24,
      chirpStart: 3180,
      chirpEnd: 1320,
      tickStart: 2180,
      tickEnd: 1620,
      tailStart: 1440,
      tailEnd: 820,
    },
    backward: {
      highpassStart: 1160,
      highpassEnd: 1980,
      lowpassStart: 7000,
      lowpassEnd: 1640,
      bandpassStart: 2360,
      bandpassEnd: 1020,
      panStart: 0.24,
      panEnd: -0.24,
      playbackRate: 1.1,
      chirpStart: 2860,
      chirpEnd: 1220,
      tickStart: 1960,
      tickEnd: 1520,
      tailStart: 1320,
      tailEnd: 760,
    },
  },
};

const state = {
  decks: [],
  activeDeckIndex: 0,
  activeItemIndex: 0,
  activeDocument: null,
  activeWindow: null,
  selectedElements: [],
  primaryElement: null,
  selectionType: null,
  dirtyFiles: new Set(),
  soundConfig: { ...DEFAULT_SOUND_CONFIG },
  imageMode: "add",
  toastTimer: 0,
  frameLoadToken: 0,
  fileSessions: new Map(),
  transformAction: null,
  previewObjectUrl: "",
  historyUndoStack: [],
  historyRedoStack: [],
  isApplyingHistory: false,
};

const TEXT_SELECTORS = [
  ".brand-chip",
  ".page-chip",
  ".cover-title",
  ".start-button",
  ".eyebrow",
  ".slide-title",
  ".panel-title",
  ".lead",
  ".quote-text",
  ".note",
  ".card-title",
  ".card-copy",
  ".card-index",
  ".text-chip",
  ".mini-chip",
  ".media-tag",
  ".media-note",
  ".metric-value",
  ".metric-label",
  ".stamp",
  ".status-pill",
  ".swarm-core",
  ".swarm-node",
  ".route-caption",
  "strong",
  "p",
  "h1",
  "h2",
  "h3",
  "button",
  "span",
];

const BLOCK_SELECTORS = [
  "figure.media-frame",
  ".panel",
  ".quote-box",
  ".media-caption",
  ".metric-box",
  ".route-step",
  ".timeline-step",
  ".pixel-icon",
];

const ALL_SELECTABLE_QUERY = ["img", ...TEXT_SELECTORS, ...BLOCK_SELECTORS].join(", ");
const SNAP_THRESHOLD = 8;
const MIN_RESIZE = 40;

const isElementNode = (node) => Boolean(node) && node.nodeType === 1;

const dom = {
  deckSelect: document.querySelector("#deckSelect"),
  deckStatus: document.querySelector("#deckStatus"),
  slideList: document.querySelector("#slideList"),
  previewFrame: document.querySelector("#previewFrame"),
  viewportShell: document.querySelector("#viewportShell"),
  canvasOverlay: document.querySelector("#canvasOverlay"),
  guideLayer: document.querySelector("#guideLayer"),
  selectionOutlines: document.querySelector("#selectionOutlines"),
  selectionBox: document.querySelector("#selectionBox"),
  selectionTag: document.querySelector("#selectionTag"),
  interactionShield: document.querySelector("#interactionShield"),
  undoBtn: document.querySelector("#undoBtn"),
  redoBtn: document.querySelector("#redoBtn"),
  newPageBtn: document.querySelector("#newPageBtn"),
  duplicatePageBtn: document.querySelector("#duplicatePageBtn"),
  deletePageBtn: document.querySelector("#deletePageBtn"),
  selectionTypeLabel: document.querySelector("#selectionTypeLabel"),
  currentFileLabel: document.querySelector("#currentFileLabel"),
  saveBtn: document.querySelector("#saveBtn"),
  reloadBtn: document.querySelector("#reloadBtn"),
  openPlayerBtn: document.querySelector("#openPlayerBtn"),
  addTextBtn: document.querySelector("#addTextBtn"),
  addImageBtn: document.querySelector("#addImageBtn"),
  deleteBtn: document.querySelector("#deleteBtn"),
  metaTag: document.querySelector("#metaTag"),
  metaClass: document.querySelector("#metaClass"),
  offsetXInput: document.querySelector("#offsetXInput"),
  offsetYInput: document.querySelector("#offsetYInput"),
  widthInput: document.querySelector("#widthInput"),
  heightInput: document.querySelector("#heightInput"),
  textContentInput: document.querySelector("#textContentInput"),
  fontSizeInput: document.querySelector("#fontSizeInput"),
  fontWeightInput: document.querySelector("#fontWeightInput"),
  colorInput: document.querySelector("#colorInput"),
  textAlignInput: document.querySelector("#textAlignInput"),
  lineHeightInput: document.querySelector("#lineHeightInput"),
  letterSpacingInput: document.querySelector("#letterSpacingInput"),
  imageSrcInput: document.querySelector("#imageSrcInput"),
  imageAltInput: document.querySelector("#imageAltInput"),
  imageFitInput: document.querySelector("#imageFitInput"),
  imageOpacityInput: document.querySelector("#imageOpacityInput"),
  replaceImageBtn: document.querySelector("#replaceImageBtn"),
  soundPresetInput: document.querySelector("#soundPresetInput"),
  soundIntensityInput: document.querySelector("#soundIntensityInput"),
  soundBrightnessInput: document.querySelector("#soundBrightnessInput"),
  soundTailInput: document.querySelector("#soundTailInput"),
  soundChirpInput: document.querySelector("#soundChirpInput"),
  soundStereoInput: document.querySelector("#soundStereoInput"),
  previewPrevSoundBtn: document.querySelector("#previewPrevSoundBtn"),
  previewNextSoundBtn: document.querySelector("#previewNextSoundBtn"),
  saveSoundBtn: document.querySelector("#saveSoundBtn"),
  imagePicker: document.querySelector("#imagePicker"),
  toast: document.querySelector("#toast"),
  textControls: document.querySelector("#textControls"),
  imageControls: document.querySelector("#imageControls"),
};

const clampNumber = (value, min, max, fallback) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  return Math.min(max, Math.max(min, numeric));
};

const normalizeSoundConfig = (config = {}) => ({
  preset: SOUND_PRESETS[config?.preset] ? config.preset : DEFAULT_SOUND_CONFIG.preset,
  intensity: clampNumber(config?.intensity, 0.35, 2, DEFAULT_SOUND_CONFIG.intensity),
  brightness: clampNumber(config?.brightness, 0.35, 2, DEFAULT_SOUND_CONFIG.brightness),
  tail: clampNumber(config?.tail, 0.35, 2, DEFAULT_SOUND_CONFIG.tail),
  chirp: clampNumber(config?.chirp, 0, 2.5, DEFAULT_SOUND_CONFIG.chirp),
  stereo: clampNumber(config?.stereo, 0, 2, DEFAULT_SOUND_CONFIG.stereo),
});

const buildSoundProfile = (config, direction = 1) => {
  const soundConfig = normalizeSoundConfig(config);
  const preset = SOUND_PRESETS[soundConfig.preset] || SOUND_PRESETS[DEFAULT_SOUND_CONFIG.preset];
  const curve = direction >= 0 ? preset.forward : preset.backward;
  const intensity = soundConfig.intensity;
  const brightness = soundConfig.brightness;
  const tail = soundConfig.tail;
  const chirp = soundConfig.chirp;
  const stereo = soundConfig.stereo;
  return {
    noiseDuration: preset.noiseDuration * (0.88 + tail * 0.16),
    masterPeak: preset.masterPeak * intensity,
    masterMid: preset.masterMid * (0.84 + intensity * 0.16),
    masterAttackTime: 0.015,
    masterMidTime: 0.1 * (0.94 + tail * 0.08),
    masterEndTime: preset.masterEndTime * tail,
    highpassStart: curve.highpassStart * brightness,
    highpassEnd: curve.highpassEnd * brightness,
    lowpassStart: curve.lowpassStart * (0.82 + brightness * 0.18),
    lowpassEnd: curve.lowpassEnd * (0.8 + brightness * 0.2),
    bandpassStart: curve.bandpassStart * brightness,
    bandpassEnd: curve.bandpassEnd * brightness,
    panStart: curve.panStart * stereo,
    panEnd: curve.panEnd * stereo,
    noisePeak: preset.noisePeak * intensity,
    noiseMid: preset.noiseMid * (0.82 + intensity * 0.18),
    noiseAttackTime: 0.02,
    noiseMidTime: 0.08 * (0.9 + tail * 0.1),
    noiseEndTime: preset.noiseEndTime * tail,
    playbackRate: curve.playbackRate * (0.96 + brightness * 0.04),
    chirpPeak: preset.chirpPeak * intensity * chirp,
    chirpStartTime: preset.chirpStartTime,
    chirpPeakTime: preset.chirpPeakTime,
    chirpEndTime: preset.chirpEndTime * tail,
    chirpStartFrequency: curve.chirpStart * brightness * (0.92 + chirp * 0.08),
    chirpEndFrequency: curve.chirpEnd * brightness,
    tickPeak: preset.tickPeak * intensity,
    tickStartTime: preset.tickStartTime,
    tickPeakTime: preset.tickPeakTime,
    tickEndTime: preset.tickEndTime,
    tickStartFrequency: curve.tickStart * brightness,
    tickEndFrequency: curve.tickEnd * brightness,
    tailPeak: preset.tailPeak * intensity,
    tailStartTime: preset.tailStartTime,
    tailPeakTime: preset.tailPeakTime * (0.94 + tail * 0.06),
    tailEndTime: preset.tailEndTime * tail,
    tailStartFrequency: curve.tailStart * brightness,
    tailEndFrequency: curve.tailEnd * brightness,
  };
};

const soundPreview = (() => {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    return {
      unlock: async () => {},
      play: async () => {},
    };
  }
  let audioContext;
  let noiseBuffer;
  let noiseBufferDuration = 0;

  const getContext = () => {
    if (!audioContext) {
      audioContext = new AudioContextClass({ latencyHint: "interactive" });
    }
    return audioContext;
  };

  const getNoiseBuffer = (duration) => {
    const context = getContext();
    if (
      noiseBuffer &&
      noiseBuffer.sampleRate === context.sampleRate &&
      Math.abs(noiseBufferDuration - duration) < 0.004
    ) {
      return noiseBuffer;
    }
    const length = Math.max(1, Math.floor(context.sampleRate * duration));
    noiseBufferDuration = duration;
    noiseBuffer = context.createBuffer(1, length, context.sampleRate);
    const data = noiseBuffer.getChannelData(0);
    for (let index = 0; index < length; index += 1) {
      const fade = 1 - index / length;
      data[index] = (Math.random() * 2 - 1) * fade;
    }
    return noiseBuffer;
  };

  const unlock = async () => {
    const context = getContext();
    if (context.state === "suspended") {
      try {
        await context.resume();
      } catch (error) {
      }
    }
  };

  const play = async (direction = 1) => {
    const context = getContext();
    if (context.state === "suspended") {
      try {
        await context.resume();
      } catch (error) {
      }
    }
    if (context.state === "suspended") return;
    const profile = buildSoundProfile(state.soundConfig, direction);
    const start = context.currentTime + 0.01;
    const noise = context.createBufferSource();
    noise.buffer = getNoiseBuffer(profile.noiseDuration);
    noise.playbackRate.setValueAtTime(profile.playbackRate, start);

    const master = context.createGain();
    master.gain.setValueAtTime(0.0001, start);
    master.gain.exponentialRampToValueAtTime(profile.masterPeak, start + profile.masterAttackTime);
    master.gain.exponentialRampToValueAtTime(profile.masterMid, start + profile.masterMidTime);
    master.gain.exponentialRampToValueAtTime(0.0001, start + profile.masterEndTime);
    master.connect(context.destination);

    const highpass = context.createBiquadFilter();
    highpass.type = "highpass";
    highpass.frequency.setValueAtTime(profile.highpassStart, start);
    highpass.frequency.exponentialRampToValueAtTime(profile.highpassEnd, start + profile.noiseEndTime);

    const lowpass = context.createBiquadFilter();
    lowpass.type = "lowpass";
    lowpass.frequency.setValueAtTime(profile.lowpassStart, start);
    lowpass.frequency.exponentialRampToValueAtTime(profile.lowpassEnd, start + profile.masterEndTime);

    const bandpass = context.createBiquadFilter();
    bandpass.type = "bandpass";
    bandpass.frequency.setValueAtTime(profile.bandpassStart, start);
    bandpass.frequency.exponentialRampToValueAtTime(profile.bandpassEnd, start + profile.noiseEndTime);

    const panner = typeof context.createStereoPanner === "function" ? context.createStereoPanner() : null;
    if (panner) {
      panner.pan.setValueAtTime(profile.panStart, start);
      panner.pan.linearRampToValueAtTime(profile.panEnd, start + profile.noiseEndTime);
    }

    const noiseGain = context.createGain();
    noiseGain.gain.setValueAtTime(0.0001, start);
    noiseGain.gain.exponentialRampToValueAtTime(profile.noisePeak, start + profile.noiseAttackTime);
    noiseGain.gain.exponentialRampToValueAtTime(profile.noiseMid, start + profile.noiseMidTime);
    noiseGain.gain.exponentialRampToValueAtTime(0.0001, start + profile.noiseEndTime);

    noise.connect(highpass);
    highpass.connect(lowpass);
    lowpass.connect(bandpass);
    bandpass.connect(noiseGain);
    noiseGain.connect(panner || master);
    if (panner) {
      panner.connect(master);
    }

    const chirpGain = context.createGain();
    chirpGain.gain.setValueAtTime(0.0001, start + profile.chirpStartTime);
    chirpGain.gain.exponentialRampToValueAtTime(profile.chirpPeak, start + profile.chirpPeakTime);
    chirpGain.gain.exponentialRampToValueAtTime(0.0001, start + profile.chirpEndTime);
    chirpGain.connect(master);
    const chirpOsc = context.createOscillator();
    chirpOsc.type = "sawtooth";
    chirpOsc.frequency.setValueAtTime(profile.chirpStartFrequency, start + profile.chirpStartTime);
    chirpOsc.frequency.exponentialRampToValueAtTime(profile.chirpEndFrequency, start + profile.chirpEndTime);
    chirpOsc.connect(chirpGain);

    const tickGain = context.createGain();
    tickGain.gain.setValueAtTime(0.0001, start + profile.tickStartTime);
    tickGain.gain.exponentialRampToValueAtTime(profile.tickPeak, start + profile.tickPeakTime);
    tickGain.gain.exponentialRampToValueAtTime(0.0001, start + profile.tickEndTime);
    tickGain.connect(master);
    const tickOsc = context.createOscillator();
    tickOsc.type = "square";
    tickOsc.frequency.setValueAtTime(profile.tickStartFrequency, start + profile.tickStartTime);
    tickOsc.frequency.exponentialRampToValueAtTime(profile.tickEndFrequency, start + profile.tickEndTime);
    tickOsc.connect(tickGain);

    const tailGain = context.createGain();
    tailGain.gain.setValueAtTime(0.0001, start + profile.tailStartTime);
    tailGain.gain.exponentialRampToValueAtTime(profile.tailPeak, start + profile.tailPeakTime);
    tailGain.gain.exponentialRampToValueAtTime(0.0001, start + profile.tailEndTime);
    tailGain.connect(master);
    const tailOsc = context.createOscillator();
    tailOsc.type = "triangle";
    tailOsc.frequency.setValueAtTime(profile.tailStartFrequency, start + profile.tailStartTime);
    tailOsc.frequency.exponentialRampToValueAtTime(profile.tailEndFrequency, start + profile.tailEndTime);
    tailOsc.connect(tailGain);

    noise.start(start);
    chirpOsc.start(start + profile.chirpStartTime);
    tickOsc.start(start + profile.tickStartTime);
    tailOsc.start(start + Math.max(0.03, profile.tailStartTime - 0.02));

    noise.stop(start + profile.noiseEndTime);
    chirpOsc.stop(start + profile.chirpEndTime);
    tickOsc.stop(start + profile.tickEndTime);
    tailOsc.stop(start + profile.tailEndTime);
  };

  return { unlock, play };
})();

const showToast = (message) => {
  dom.toast.textContent = message;
  dom.toast.classList.remove("hidden");
  clearTimeout(state.toastTimer);
  state.toastTimer = window.setTimeout(() => {
    dom.toast.classList.add("hidden");
  }, 2200);
};

const requestJson = async (url, options = {}) => {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json();
};

const encodePathForFrame = (value) => {
  const [pathname, query = ""] = String(value).split("?");
  const encoded = pathname
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/");
  return query ? `${encoded}?${query}` : encoded;
};

const relativePath = (fromFile, toFile) => {
  const fromParts = fromFile.split("/").filter(Boolean);
  fromParts.pop();
  const toParts = toFile.split("/").filter(Boolean);
  while (fromParts.length && toParts.length && fromParts[0] === toParts[0]) {
    fromParts.shift();
    toParts.shift();
  }
  const output = [...Array(fromParts.length).fill(".."), ...toParts].join("/");
  return output || ".";
};

const currentDeck = () => state.decks[state.activeDeckIndex] || null;
const deckItems = (deck = currentDeck()) =>
  deck ? [{ kind: "cover", path: deck.indexFile, title: deck.title, label: "封面" }, ...deck.slides.map((slide) => ({ ...slide, kind: "slide" }))] : [];
const currentItem = () => deckItems()[state.activeItemIndex] || null;

const getFileSession = (filePath) => {
  if (!state.fileSessions.has(filePath)) {
    state.fileSessions.set(filePath, {
      savedHtml: "",
      currentHtml: "",
      undoStack: [],
      redoStack: [],
      pendingBefore: "",
      commitTimer: 0,
    });
  }
  return state.fileSessions.get(filePath);
};

const clearFileSession = (filePath) => {
  const session = state.fileSessions.get(filePath);
  if (session?.commitTimer) {
    clearTimeout(session.commitTimer);
  }
  state.fileSessions.delete(filePath);
  state.dirtyFiles.delete(filePath);
};

const syncDirtyState = (filePath, render = true) => {
  const session = getFileSession(filePath);
  const isDirty = Boolean(session.currentHtml) && session.currentHtml !== session.savedHtml;
  const wasDirty = state.dirtyFiles.has(filePath);
  if (isDirty) {
    state.dirtyFiles.add(filePath);
  } else {
    state.dirtyFiles.delete(filePath);
  }
  if (render && wasDirty !== isDirty) {
    renderSlideList();
  }
  return isDirty;
};

const pushHistoryEntry = (entry) => {
  if (!entry || state.isApplyingHistory) return;
  state.historyUndoStack.push(entry);
  if (state.historyUndoStack.length > 120) {
    state.historyUndoStack.shift();
  }
  state.historyRedoStack = [];
};

const updateUndoRedoButtons = () => {
  dom.undoBtn.disabled = !state.historyUndoStack.length;
  dom.redoBtn.disabled = !state.historyRedoStack.length;
};

const updatePageButtons = () => {
  const item = currentItem();
  const deck = currentDeck();
  const slideCount = deck?.slides?.length || 0;
  dom.newPageBtn.disabled = !deck;
  dom.duplicatePageBtn.disabled = !item || item.kind === "cover";
  dom.deletePageBtn.disabled = !item || item.kind === "cover" || slideCount <= 1;
  dom.deleteBtn.disabled = !state.selectedElements.length;
  dom.replaceImageBtn.disabled = !(state.selectedElements.length === 1 && activeImage());
};

const ensurePendingHistory = (filePath) => {
  const session = getFileSession(filePath);
  if (!session.pendingBefore) {
    session.pendingBefore = session.currentHtml || session.savedHtml || serializeDocument(state.activeDocument, filePath);
  }
  return session;
};

const commitHistory = (filePath, render = true) => {
  const session = getFileSession(filePath);
  if (session.commitTimer) {
    clearTimeout(session.commitTimer);
    session.commitTimer = 0;
  }
  if (!session.pendingBefore) {
    syncDirtyState(filePath, render);
    updateUndoRedoButtons();
    return false;
  }
  const before = session.pendingBefore;
  const current = session.currentHtml || before;
  session.pendingBefore = "";
  if (current !== before) {
    session.undoStack.push(before);
    if (session.undoStack.length > 80) {
      session.undoStack.shift();
    }
    session.redoStack = [];
    pushHistoryEntry({
      label: `页面编辑 · ${filePath}`,
      undo: async () => {
        await applyFileHistoryState(filePath, before);
      },
      redo: async () => {
        await applyFileHistoryState(filePath, current);
      },
    });
  }
  syncDirtyState(filePath, render);
  updateUndoRedoButtons();
  return current !== before;
};

const scheduleHistoryCommit = (filePath, delay = 260) => {
  const session = getFileSession(filePath);
  if (session.commitTimer) {
    clearTimeout(session.commitTimer);
  }
  session.commitTimer = window.setTimeout(() => {
    commitHistory(filePath);
  }, delay);
};

const serializeDocument = (doc, filePath) => {
  const clone = doc.documentElement.cloneNode(true);
  clone.querySelectorAll("#deck-editor-style").forEach((node) => node.remove());
  clone.querySelectorAll("base[data-editor-base]").forEach((node) => node.remove());
  clone.querySelectorAll("[contenteditable]").forEach((node) => node.removeAttribute("contenteditable"));
  clone.querySelectorAll('script[src^="chrome-extension://"]').forEach((node) => node.remove());
  clone.querySelectorAll('[id^="xl_chrome_ext_"], [class*="xl-chrome-ext-bar"]').forEach((node) => node.remove());
  clone.classList.remove("is-ready");
  clone.removeAttribute("style");
  if (!clone.className) {
    clone.removeAttribute("class");
  }
  const clonedBody = clone.querySelector("body");
  clonedBody?.classList.remove("is-playing");
  clonedBody?.removeAttribute("style");
  clone.querySelectorAll(".particle-canvas").forEach((node) => {
    node.removeAttribute("width");
    node.removeAttribute("height");
  });
  clone.querySelectorAll(".swarm-line").forEach((node) => node.remove());
  clone.querySelectorAll(".tilt-card").forEach((node) => {
    if (node.style.transform) {
      node.style.removeProperty("transform");
    }
  });
  const titleNode = clone.querySelector("title");
  const pageChip = clone.querySelector(".page-chip")?.textContent?.trim();
  const heading = clone.querySelector("h1, h2")?.textContent?.trim();
  const coverTitle = clone.querySelector(".cover-title")?.textContent?.trim();
  if (titleNode) {
    if (filePath.endsWith(".html") && filePath.includes("slide") && heading) {
      titleNode.textContent = pageChip ? `${pageChip} - ${heading}` : heading;
    } else if (coverTitle) {
      titleNode.textContent = coverTitle;
    }
  }
  return `<!DOCTYPE html>\n${clone.outerHTML}`;
};

const buildFrameBaseHref = (filePath) => {
  const encoded = encodePathForFrame(filePath);
  const parts = encoded.split("/").filter(Boolean);
  parts.pop();
  return `${window.location.origin}/${parts.length ? `${parts.join("/")}/` : ""}`;
};

const injectEditorBase = (html, filePath) => {
  const baseTag = `<base data-editor-base="true" href="${buildFrameBaseHref(filePath)}" />`;
  if (/<head[^>]*>/i.test(html)) {
    return html.replace(/<head([^>]*)>/i, `<head$1>\n    ${baseTag}`);
  }
  return `<!DOCTYPE html><html><head>${baseTag}</head><body>${html}</body></html>`;
};

const updateSessionCurrentFromDocument = (filePath, renderDirty = true) => {
  if (!state.activeDocument) return "";
  const html = serializeDocument(state.activeDocument, filePath);
  const session = getFileSession(filePath);
  session.currentHtml = html;
  syncDirtyState(filePath, renderDirty);
  return html;
};

const recordDomMutation = (mode = "debounce") => {
  const item = currentItem();
  if (!item || !state.activeDocument) return;
  ensurePendingHistory(item.path);
  updateSessionCurrentFromDocument(item.path);
  if (mode === "instant") {
    commitHistory(item.path);
  } else {
    scheduleHistoryCommit(item.path);
  }
  updateUndoRedoButtons();
  updatePageButtons();
};

const ensureDocStyles = (doc) => {
  if (doc.getElementById("deck-editor-style")) return;
  const style = doc.createElement("style");
  style.id = "deck-editor-style";
  style.textContent = `
    * { user-select: none !important; -webkit-user-drag: none !important; }
    body { cursor: crosshair !important; }
    [contenteditable="true"] {
      outline: 2px dashed rgba(216, 23, 32, 0.7) !important;
      background: rgba(255, 255, 255, 0.92) !important;
      user-select: text !important;
      cursor: text !important;
    }
  `;
  doc.head.appendChild(style);
};

const maybeTextTarget = (node) => {
  if (!isElementNode(node)) return null;
  const bulletItem = node.closest(".bullet-item");
  if (bulletItem) {
    return bulletItem.querySelector("span:last-child") || bulletItem;
  }
  return node.closest(TEXT_SELECTORS.join(", "));
};

const resolveSelectableElement = (node) => {
  if (!isElementNode(node)) return null;
  const image = node.closest("img");
  if (image) return image;
  const textTarget = maybeTextTarget(node);
  if (textTarget) return textTarget;
  return node.closest(BLOCK_SELECTORS.join(", "));
};

const selectionKind = (element) => {
  if (!element) return null;
  if (element.tagName === "IMG") return "image";
  if (element.matches(TEXT_SELECTORS.join(", "))) return "text";
  return "block";
};

const getTargetBlockForSizing = (element) => {
  if (!element) return null;
  if (element.tagName === "IMG") {
    return element.closest("figure, .media-frame") || element;
  }
  return element;
};

const currentComputedRect = (element) => {
  const target = getTargetBlockForSizing(element);
  return target ? target.getBoundingClientRect() : null;
};

const readInlineNumber = (element, propertyName) => {
  const raw = element?.style?.[propertyName] || "";
  const numeric = Number.parseFloat(raw);
  return Number.isFinite(numeric) ? numeric : 0;
};

const activeImage = () => {
  if (state.selectedElements.length !== 1) return null;
  const element = state.primaryElement;
  if (!element) return null;
  if (element.tagName === "IMG") return element;
  return element.querySelector("img");
};

const normalizeSelection = (elements) => {
  const filtered = [];
  elements.forEach((element) => {
    if (!isElementNode(element) || !state.activeDocument?.contains(element)) return;
    const duplicate = filtered.find((current) => current === element);
    if (duplicate) return;
    const parentIndex = filtered.findIndex((current) => current.contains(element));
    if (parentIndex >= 0) {
      filtered.splice(parentIndex, 1, element);
      return;
    }
    if (filtered.some((current) => element.contains(current))) {
      return;
    }
    filtered.push(element);
  });
  return filtered;
};

const getSelectionTargets = () => {
  const unique = [];
  state.selectedElements.forEach((element) => {
    const target = getTargetBlockForSizing(element);
    if (target && !unique.includes(target)) {
      unique.push(target);
    }
  });
  return unique;
};

const getCanvasBoundsForTarget = (target) => {
  if (!target || !state.activeWindow) return null;
  const rect = target.getBoundingClientRect();
  return {
    target,
    left: rect.left,
    top: rect.top,
    width: rect.width,
    height: rect.height,
    right: rect.right,
    bottom: rect.bottom,
    centerX: rect.left + rect.width / 2,
    centerY: rect.top + rect.height / 2,
  };
};

const combineBounds = (bounds) => {
  if (!bounds.length) return null;
  const left = Math.min(...bounds.map((item) => item.left));
  const top = Math.min(...bounds.map((item) => item.top));
  const right = Math.max(...bounds.map((item) => item.right));
  const bottom = Math.max(...bounds.map((item) => item.bottom));
  return {
    left,
    top,
    right,
    bottom,
    width: right - left,
    height: bottom - top,
    centerX: left + (right - left) / 2,
    centerY: top + (bottom - top) / 2,
  };
};

const selectedCanvasBounds = () => getSelectionTargets().map((target) => getCanvasBoundsForTarget(target)).filter(Boolean);

const renderGuides = (guides = []) => {
  dom.guideLayer.innerHTML = "";
  guides.forEach((guide) => {
    const line = document.createElement("div");
    line.className = `guide-line ${guide.orientation}`;
    if (guide.orientation === "vertical") {
      line.style.left = `${guide.position}px`;
    } else {
      line.style.top = `${guide.position}px`;
    }
    dom.guideLayer.appendChild(line);
  });
};

const clearGuides = () => renderGuides([]);

const selectionLabel = () => {
  if (!state.selectedElements.length) return "未选中";
  if (state.selectedElements.length > 1) return `${state.selectedElements.length} 个对象`;
  const element = state.primaryElement;
  return `${element.tagName.toLowerCase()}${element.className ? ` · ${element.className}` : ""}`;
};

const populateTextControls = (element) => {
  if (!state.activeWindow) return;
  const styles = state.activeWindow.getComputedStyle(element);
  dom.textContentInput.value = element.textContent?.trim() || "";
  dom.fontSizeInput.value = Number.parseFloat(styles.fontSize).toFixed(1);
  dom.fontWeightInput.value = element.style.fontWeight || "";
  dom.colorInput.value = rgbToHex(styles.color);
  dom.textAlignInput.value = element.style.textAlign || "";
  dom.lineHeightInput.value =
    Number.parseFloat(styles.lineHeight) && !Number.isNaN(Number.parseFloat(styles.lineHeight))
      ? String((Number.parseFloat(styles.lineHeight) / Number.parseFloat(styles.fontSize)).toFixed(2))
      : "";
  dom.letterSpacingInput.value = element.style.letterSpacing
    ? String(Number.parseFloat(element.style.letterSpacing) / Number.parseFloat(styles.fontSize))
    : "";
};

const populateImageControls = (element) => {
  if (!state.activeWindow) return;
  const image = element.tagName === "IMG" ? element : element.querySelector("img");
  if (!image) return;
  const target = getTargetBlockForSizing(image);
  const styles = state.activeWindow.getComputedStyle(image);
  dom.imageSrcInput.value = image.getAttribute("src") || "";
  dom.imageAltInput.value = image.getAttribute("alt") || "";
  dom.imageFitInput.value = image.style.objectFit || "";
  dom.imageOpacityInput.value = image.style.opacity || styles.opacity || "1";
  if (target) {
    const rect = target.getBoundingClientRect();
    dom.widthInput.value = target.style.width ? String(Math.round(Number.parseFloat(target.style.width))) : String(Math.round(rect.width));
    dom.heightInput.value = target.style.height ? String(Math.round(Number.parseFloat(target.style.height))) : String(Math.round(rect.height));
  }
};

const applyPositionControlsFromSelection = () => {
  const bounds = combineBounds(selectedCanvasBounds());
  if (!bounds) {
    dom.offsetXInput.value = "0";
    dom.offsetYInput.value = "0";
    dom.widthInput.value = "";
    dom.heightInput.value = "";
    return;
  }
  if (state.selectedElements.length === 1) {
    const target = getTargetBlockForSizing(state.primaryElement);
    const rect = currentComputedRect(state.primaryElement);
    dom.offsetXInput.value = String(readInlineNumber(target, "left"));
    dom.offsetYInput.value = String(readInlineNumber(target, "top"));
    dom.widthInput.value = target?.style?.width ? String(Math.round(Number.parseFloat(target.style.width))) : rect ? String(Math.round(rect.width)) : "";
    dom.heightInput.value = target?.style?.height ? String(Math.round(Number.parseFloat(target.style.height))) : rect ? String(Math.round(rect.height)) : "";
    return;
  }
  dom.offsetXInput.value = String(Math.round(bounds.left));
  dom.offsetYInput.value = String(Math.round(bounds.top));
  dom.widthInput.value = String(Math.round(bounds.width));
  dom.heightInput.value = String(Math.round(bounds.height));
};

const updateInspector = () => {
  if (!state.selectedElements.length) {
    dom.selectionTypeLabel.textContent = "未选中";
    dom.metaTag.textContent = "—";
    dom.metaClass.textContent = "—";
    dom.textControls.style.display = "none";
    dom.imageControls.style.display = "none";
    applyPositionControlsFromSelection();
    updatePageButtons();
    return;
  }
  if (state.selectedElements.length > 1) {
    dom.selectionTypeLabel.textContent = `多选 ${state.selectedElements.length}`;
    dom.metaTag.textContent = `${state.selectedElements.length} 个元素`;
    dom.metaClass.textContent = "Shift+点击可增减";
    dom.textControls.style.display = "none";
    dom.imageControls.style.display = "none";
    applyPositionControlsFromSelection();
    updatePageButtons();
    return;
  }
  const element = state.primaryElement;
  state.selectionType = selectionKind(element);
  dom.selectionTypeLabel.textContent = state.selectionType || "未选中";
  dom.metaTag.textContent = element.tagName.toLowerCase();
  dom.metaClass.textContent = element.className || "—";
  dom.textControls.style.display = state.selectionType === "text" ? "grid" : "none";
  dom.imageControls.style.display = activeImage() ? "grid" : "none";
  applyPositionControlsFromSelection();
  if (state.selectionType === "text") {
    populateTextControls(element);
  }
  if (activeImage()) {
    populateImageControls(element);
  }
  updatePageButtons();
};

const renderSelectionOverlay = () => {
  dom.selectionOutlines.innerHTML = "";
  const boundsList = selectedCanvasBounds();
  if (!boundsList.length) {
    dom.selectionBox.classList.add("hidden");
    clearGuides();
    return;
  }
  boundsList.forEach((bounds) => {
    const outline = document.createElement("div");
    const isPrimary = getTargetBlockForSizing(state.primaryElement) === bounds.target;
    outline.className = `selection-outline${isPrimary ? " primary" : ""}`;
    outline.style.left = `${bounds.left}px`;
    outline.style.top = `${bounds.top}px`;
    outline.style.width = `${bounds.width}px`;
    outline.style.height = `${bounds.height}px`;
    dom.selectionOutlines.appendChild(outline);
  });
  const groupBounds = combineBounds(boundsList);
  dom.selectionBox.style.left = `${groupBounds.left}px`;
  dom.selectionBox.style.top = `${groupBounds.top}px`;
  dom.selectionBox.style.width = `${groupBounds.width}px`;
  dom.selectionBox.style.height = `${groupBounds.height}px`;
  dom.selectionBox.classList.remove("hidden");
  dom.selectionBox.classList.toggle("single", state.selectedElements.length === 1);
  dom.selectionBox.classList.toggle("multi", state.selectedElements.length > 1);
  dom.selectionTag.textContent = selectionLabel();
};

const clearSelection = () => {
  state.selectedElements = [];
  state.primaryElement = null;
  state.selectionType = null;
  dom.selectionOutlines.innerHTML = "";
  dom.selectionBox.classList.add("hidden");
  clearGuides();
  updateInspector();
  updateUndoRedoButtons();
};

const setSelection = (elements, primary = elements[elements.length - 1] || null) => {
  state.selectedElements = normalizeSelection(elements);
  state.primaryElement = state.selectedElements.includes(primary) ? primary : state.selectedElements[0] || null;
  state.selectionType = state.selectedElements.length === 1 ? selectionKind(state.primaryElement) : "multi";
  updateInspector();
  renderSelectionOverlay();
};

const toggleSelection = (element) => {
  if (state.selectedElements.includes(element)) {
    setSelection(state.selectedElements.filter((current) => current !== element));
    return;
  }
  setSelection([...state.selectedElements, element], element);
};

const rgbToHex = (rgbValue) => {
  const match = rgbValue.match(/\d+/g);
  if (!match || match.length < 3) return "#131313";
  return `#${match.slice(0, 3).map((item) => Number(item).toString(16).padStart(2, "0")).join("")}`;
};

const toDocRelativeAssetPath = (assetPath) => {
  const item = currentItem();
  if (!item) return assetPath;
  return relativePath(item.path, assetPath);
};

const isEditableContext = (target) => {
  if (!target) return false;
  return Boolean(
    target.closest?.("input, textarea, select, button") ||
      target.isContentEditable
  );
};

const setInteractionShield = (active, cursor = "move") => {
  dom.interactionShield.classList.toggle("hidden", !active);
  dom.interactionShield.classList.toggle("active", active);
  dom.interactionShield.style.cursor = active ? cursor : "";
};

const fetchFileHtml = async (filePath) => {
  const response = await fetch(`/${encodePathForFrame(filePath)}?editorTs=${Date.now()}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`加载失败: ${filePath}`);
  }
  return response.text();
};

const revokePreviewObjectUrl = () => {
  if (state.previewObjectUrl) {
    URL.revokeObjectURL(state.previewObjectUrl);
    state.previewObjectUrl = "";
  }
};

const loadHtmlIntoFrame = (html, filePath, useDraft = false) => {
  const token = Date.now();
  state.frameLoadToken = token;
  dom.deckStatus.textContent = "iframe 加载中";
  dom.previewFrame.removeAttribute("srcdoc");
  revokePreviewObjectUrl();
  if (useDraft) {
    const blob = new Blob([injectEditorBase(html, filePath)], { type: "text/html" });
    state.previewObjectUrl = URL.createObjectURL(blob);
    dom.previewFrame.src = state.previewObjectUrl;
  } else {
    dom.previewFrame.src = `/${encodePathForFrame(filePath)}?editorTs=${Date.now()}`;
  }
  window.setTimeout(() => {
    if (state.frameLoadToken !== token) return;
    const doc = dom.previewFrame.contentDocument;
    const bodyText = doc?.body?.textContent?.trim() || "";
    if (!doc || !bodyText) {
      dom.deckStatus.textContent = "iframe 未加载成功";
      showToast("当前 iframe 没有正常渲染内容。优先用无扩展窗口测试，或确认你是通过 http://127.0.0.1:4321/editor/ 打开的。");
    }
  }, 2200);
};

const resolveItemHtml = async (item, forceDisk = false) => {
  const session = getFileSession(item.path);
  if (!forceDisk && session.currentHtml && session.currentHtml !== session.savedHtml) {
    return {
      html: session.currentHtml,
      useDraft: true,
    };
  }
  const html = await fetchFileHtml(item.path);
  session.savedHtml = html;
  if (!session.currentHtml || forceDisk || session.currentHtml === session.savedHtml) {
    session.currentHtml = html;
  }
  session.pendingBefore = "";
  if (!forceDisk) {
    session.undoStack = session.undoStack || [];
    session.redoStack = session.redoStack || [];
  }
  syncDirtyState(item.path, false);
  return {
    html: session.currentHtml || html,
    useDraft: Boolean(session.currentHtml && session.currentHtml !== session.savedHtml),
  };
};

const flushCurrentEditingState = () => {
  const item = currentItem();
  if (!item || !state.activeDocument) return;
  if (state.transformAction) {
    finishTransformAction();
  }
  updateSessionCurrentFromDocument(item.path, false);
  commitHistory(item.path, true);
};

const loadItem = async (index, options = {}) => {
  const previousItem = currentItem();
  if (previousItem?.path && state.activeDocument) {
    flushCurrentEditingState();
  }
  state.activeItemIndex = index;
  renderSlideList();
  const item = currentItem();
  if (!item) return;
  clearSelection();
  dom.currentFileLabel.textContent = item.path;
  updatePageButtons();
  updateUndoRedoButtons();
  const { html, useDraft } = await resolveItemHtml(item, options.forceDisk);
  loadHtmlIntoFrame(html, item.path, useDraft);
};

const renderDeckOptions = () => {
  dom.deckSelect.innerHTML = state.decks.map((deck, index) => `<option value="${index}">${deck.title}</option>`).join("");
  dom.deckSelect.value = String(state.activeDeckIndex);
};

const renderSlideList = () => {
  const items = deckItems();
  dom.slideList.innerHTML = "";
  items.forEach((item, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `slide-item${index === state.activeItemIndex ? " active" : ""}`;
    button.innerHTML = `
      <div class="slide-label">
        <span>${index === 0 ? "COVER" : `SLIDE ${String(index).padStart(2, "0")}`}</span>
        ${state.dirtyFiles.has(item.path) ? '<span class="dirty-pill">未保存</span>' : ""}
      </div>
      <div class="slide-title">${item.title || item.label || item.path}</div>
    `;
    button.addEventListener("click", () => {
      loadItem(index);
    });
    dom.slideList.appendChild(button);
  });
};

const applyDeckPayload = async (payload, preferredDeckPath, preferredItemPath) => {
  state.decks = payload.decks || [];
  if (!state.decks.length) {
    clearSelection();
    dom.deckStatus.textContent = "未发现 deck";
    return;
  }
  const deckIndex = Math.max(0, state.decks.findIndex((deck) => deck.indexFile === preferredDeckPath));
  state.activeDeckIndex = deckIndex;
  renderDeckOptions();
  const items = deckItems(state.decks[deckIndex]);
  const selectedIndex = Math.max(0, items.findIndex((item) => item.path === preferredItemPath));
  state.activeItemIndex = selectedIndex >= 0 ? selectedIndex : 0;
  renderSlideList();
  await loadItem(state.activeItemIndex);
};

const loadDecks = async () => {
  const payload = await requestJson("/api/decks");
  state.decks = payload.decks || [];
  if (!state.decks.length) {
    dom.deckStatus.textContent = "未发现 deck";
    return;
  }
  renderDeckOptions();
  renderSlideList();
  await loadItem(0);
  dom.deckStatus.textContent = `${state.decks.length} 套 deck`;
};

const loadSoundConfig = async () => {
  const payload = await requestJson("/api/sound-config");
  state.soundConfig = normalizeSoundConfig(payload.config || DEFAULT_SOUND_CONFIG);
  syncSoundInputs();
};

const syncSoundConfigFromInputs = () => {
  state.soundConfig = normalizeSoundConfig({
    preset: dom.soundPresetInput.value,
    intensity: dom.soundIntensityInput.value,
    brightness: dom.soundBrightnessInput.value,
    tail: dom.soundTailInput.value,
    chirp: dom.soundChirpInput.value,
    stereo: dom.soundStereoInput.value,
  });
};

const cloneSoundConfig = (config) => normalizeSoundConfig({ ...config });

const syncSoundInputs = () => {
  dom.soundPresetInput.value = state.soundConfig.preset;
  dom.soundIntensityInput.value = String(state.soundConfig.intensity);
  dom.soundBrightnessInput.value = String(state.soundConfig.brightness);
  dom.soundTailInput.value = String(state.soundConfig.tail);
  dom.soundChirpInput.value = String(state.soundConfig.chirp);
  dom.soundStereoInput.value = String(state.soundConfig.stereo);
};

const saveSoundConfigState = async (config, { announce = false } = {}) => {
  state.soundConfig = cloneSoundConfig(config);
  syncSoundInputs();
  await requestJson("/api/sound-config", {
    method: "POST",
    body: JSON.stringify({ config: state.soundConfig }),
  });
  if (announce) {
    showToast("翻页音效已保存");
  }
};

const saveSoundConfig = async () => {
  const before = cloneSoundConfig(state.soundConfig);
  syncSoundConfigFromInputs();
  const after = cloneSoundConfig(state.soundConfig);
  const changed = JSON.stringify(before) !== JSON.stringify(after);
  await saveSoundConfigState(after, { announce: true });
  if (changed) {
    pushHistoryEntry({
      label: "翻页音效",
      undo: async () => {
        await saveSoundConfigState(before);
      },
      redo: async () => {
        await saveSoundConfigState(after);
      },
    });
    updateUndoRedoButtons();
  }
};

const saveCurrentFile = async () => {
  const item = currentItem();
  if (!item || !state.activeDocument) return;
  updateSessionCurrentFromDocument(item.path, false);
  commitHistory(item.path, false);
  const session = getFileSession(item.path);
  const content = session.currentHtml || serializeDocument(state.activeDocument, item.path);
  await requestJson("/api/save-file", {
    method: "POST",
    body: JSON.stringify({
      path: item.path,
      content,
    }),
  });
  session.savedHtml = content;
  session.currentHtml = content;
  syncDirtyState(item.path);
  updateUndoRedoButtons();
  renderSlideList();
  showToast(`已保存：${item.path}`);
};

const reloadCurrent = async () => {
  const item = currentItem();
  if (!item) return;
  clearFileSession(item.path);
  await loadItem(state.activeItemIndex, { forceDisk: true });
  showToast("已重新加载当前页面");
};

const openPlayer = () => {
  const deck = currentDeck();
  if (!deck) return;
  window.open(`/${encodePathForFrame(deck.indexFile)}`, "_blank");
};

const findDeckItemLocation = (filePath) => {
  for (let deckIndex = 0; deckIndex < state.decks.length; deckIndex += 1) {
    const items = deckItems(state.decks[deckIndex]);
    const itemIndex = items.findIndex((item) => item.path === filePath);
    if (itemIndex >= 0) {
      return { deckIndex, itemIndex };
    }
  }
  return null;
};

const applyFileHistoryState = async (filePath, html) => {
  const session = getFileSession(filePath);
  if (session.commitTimer) {
    clearTimeout(session.commitTimer);
    session.commitTimer = 0;
  }
  session.pendingBefore = "";
  session.currentHtml = html;
  syncDirtyState(filePath, true);
  renderSlideList();

  const location = findDeckItemLocation(filePath);
  if (!location) {
    updateUndoRedoButtons();
    return;
  }

  const current = currentItem();
  if (current?.path === filePath) {
    clearSelection();
    loadHtmlIntoFrame(session.currentHtml, filePath, session.currentHtml !== session.savedHtml);
    updateUndoRedoButtons();
    updatePageButtons();
    return;
  }

  state.activeDeckIndex = location.deckIndex;
  renderDeckOptions();
  await loadItem(location.itemIndex);
  updateUndoRedoButtons();
};

const appendTextBlock = () => {
  if (!state.activeDocument) return;
  const target =
    state.primaryElement?.closest(".content-stack, .copy-stack, .list-stack, .media-stack, .panel, main") ||
    state.activeDocument.querySelector(".panel .content-stack, .panel, main");
  if (!target) return;
  const paragraph = state.activeDocument.createElement("p");
  paragraph.className = "lead";
  paragraph.textContent = "在这里填写新文本。";
  paragraph.style.position = "relative";
  target.appendChild(paragraph);
  setSelection([paragraph], paragraph);
  recordDomMutation("instant");
};

const appendImageBlock = (assetPath) => {
  if (!state.activeDocument) return;
  const target =
    state.primaryElement?.closest(".media-stack, .content-stack, .copy-stack, .list-stack, .panel, main") ||
    state.activeDocument.querySelector(".panel .content-stack, .panel, main");
  if (!target) return;
  const figure = state.activeDocument.createElement("figure");
  figure.className = "media-frame compact tilt-card hover-card";
  figure.innerHTML = `
    <img src="${toDocRelativeAssetPath(assetPath)}" alt="新增图片" />
    <div class="image-tint"></div>
    <div class="scan"></div>
  `;
  figure.style.position = "relative";
  target.appendChild(figure);
  setSelection([figure.querySelector("img")], figure.querySelector("img"));
  recordDomMutation("instant");
};

const deleteSelected = () => {
  if (!state.selectedElements.length) return;
  const targets = getSelectionTargets();
  targets.forEach((target) => target.remove());
  clearSelection();
  recordDomMutation("instant");
};

const uploadImage = async (file) => {
  const dataUrl = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
  const payload = await requestJson("/api/upload-image", {
    method: "POST",
    body: JSON.stringify({
      filename: file.name,
      dataUrl,
    }),
  });
  return payload.path;
};

const applyOffset = () => {
  if (!state.selectedElements.length) return;
  const targets = getSelectionTargets();
  if (state.selectedElements.length > 1) {
    const bounds = combineBounds(selectedCanvasBounds());
    if (!bounds) return;
    const nextX = Number.isFinite(Number(dom.offsetXInput.value)) ? Number(dom.offsetXInput.value) : bounds.left;
    const nextY = Number.isFinite(Number(dom.offsetYInput.value)) ? Number(dom.offsetYInput.value) : bounds.top;
    const deltaX = nextX - bounds.left;
    const deltaY = nextY - bounds.top;
    targets.forEach((target) => {
      target.style.position = target.style.position || "relative";
      target.style.left = `${readInlineNumber(target, "left") + deltaX}px`;
      target.style.top = `${readInlineNumber(target, "top") + deltaY}px`;
    });
    renderSelectionOverlay();
    updateInspector();
    recordDomMutation("debounce");
    return;
  }
  const target = targets[0];
  const widthValue = Number(dom.widthInput.value);
  const heightValue = Number(dom.heightInput.value);
  target.style.position = target.style.position || "relative";
  target.style.left = `${Number(dom.offsetXInput.value || 0)}px`;
  target.style.top = `${Number(dom.offsetYInput.value || 0)}px`;
  target.style.width = Number.isFinite(widthValue) && widthValue > 0 ? `${widthValue}px` : "";
  target.style.height = Number.isFinite(heightValue) && heightValue > 0 ? `${heightValue}px` : "";
  renderSelectionOverlay();
  updateInspector();
  recordDomMutation("debounce");
};

const applyTextContent = () => {
  if (state.selectedElements.length !== 1 || state.selectionType !== "text") return;
  state.primaryElement.textContent = dom.textContentInput.value;
  renderSelectionOverlay();
  updateInspector();
  recordDomMutation("debounce");
};

const applyTextStyle = () => {
  if (state.selectedElements.length !== 1 || state.selectionType !== "text") return;
  const element = state.primaryElement;
  element.style.fontSize = dom.fontSizeInput.value ? `${Number(dom.fontSizeInput.value)}px` : "";
  element.style.fontWeight = dom.fontWeightInput.value || "";
  element.style.color = dom.colorInput.value || "";
  element.style.textAlign = dom.textAlignInput.value || "";
  element.style.lineHeight = dom.lineHeightInput.value ? String(Number(dom.lineHeightInput.value)) : "";
  element.style.letterSpacing = dom.letterSpacingInput.value ? `${Number(dom.letterSpacingInput.value)}em` : "";
  renderSelectionOverlay();
  updateInspector();
  recordDomMutation("debounce");
};

const applyImageContent = () => {
  const image = activeImage();
  if (!image) return;
  image.setAttribute("src", dom.imageSrcInput.value.trim());
  image.setAttribute("alt", dom.imageAltInput.value.trim());
  renderSelectionOverlay();
  updateInspector();
  recordDomMutation("debounce");
};

const applyImageStyle = () => {
  const image = activeImage();
  if (!image) return;
  image.style.objectFit = dom.imageFitInput.value || "";
  image.style.opacity = dom.imageOpacityInput.value || "";
  renderSelectionOverlay();
  updateInspector();
  recordDomMutation("debounce");
};

const openInlineEditing = (element) => {
  if (!element || selectionKind(element) !== "text") return;
  element.setAttribute("contenteditable", "true");
  element.focus();
  const range = element.ownerDocument.createRange();
  range.selectNodeContents(element);
  const selection = element.ownerDocument.getSelection();
  selection.removeAllRanges();
  selection.addRange(range);
  const onInput = () => {
    dom.textContentInput.value = element.textContent?.trim() || "";
    renderSelectionOverlay();
    recordDomMutation("debounce");
  };
  const finish = () => {
    element.removeAttribute("contenteditable");
    element.removeEventListener("input", onInput);
    element.removeEventListener("blur", finish);
    dom.textContentInput.value = element.textContent?.trim() || "";
    renderSelectionOverlay();
    updateInspector();
    recordDomMutation("instant");
  };
  element.addEventListener("input", onInput);
  element.addEventListener("blur", finish);
};

const cursorForResize = (direction) => {
  if (direction === "nw" || direction === "se") return "nwse-resize";
  return "nesw-resize";
};

const allSelectableTargets = () => {
  if (!state.activeDocument) return [];
  const unique = new Set();
  state.activeDocument.querySelectorAll(ALL_SELECTABLE_QUERY).forEach((node) => {
    const selectable = resolveSelectableElement(node);
    const target = getTargetBlockForSizing(selectable);
    if (target) {
      unique.add(target);
    }
  });
  return [...unique];
};

const findBestSnap = (points, candidates) => {
  let best = null;
  points.forEach((point) => {
    candidates.forEach((candidate) => {
      const diff = candidate - point;
      const distance = Math.abs(diff);
      if (distance > SNAP_THRESHOLD) return;
      if (!best || distance < best.distance) {
        best = { offset: diff, candidate, distance };
      }
    });
  });
  return best;
};

const computeSnapAdjustment = (bounds, deltaX, deltaY, excludedTargets) => {
  const candidateTargets = allSelectableTargets().filter((target) => {
    if (excludedTargets.includes(target)) return false;
    return !excludedTargets.some((selected) => selected.contains(target) || target.contains(selected));
  });
  const width = dom.previewFrame.clientWidth;
  const height = dom.previewFrame.clientHeight;
  const moved = {
    left: bounds.left + deltaX,
    right: bounds.right + deltaX,
    top: bounds.top + deltaY,
    bottom: bounds.bottom + deltaY,
    centerX: bounds.centerX + deltaX,
    centerY: bounds.centerY + deltaY,
  };
  const vertical = [0, width / 2, width];
  const horizontal = [0, height / 2, height];
  candidateTargets.forEach((target) => {
    const item = getCanvasBoundsForTarget(target);
    if (!item) return;
    vertical.push(item.left, item.centerX, item.right);
    horizontal.push(item.top, item.centerY, item.bottom);
  });
  const snappedX = findBestSnap([moved.left, moved.centerX, moved.right], vertical);
  const snappedY = findBestSnap([moved.top, moved.centerY, moved.bottom], horizontal);
  const guides = [];
  if (snappedX) {
    guides.push({ orientation: "vertical", position: snappedX.candidate });
  }
  if (snappedY) {
    guides.push({ orientation: "horizontal", position: snappedY.candidate });
  }
  return {
    deltaX: deltaX + (snappedX?.offset || 0),
    deltaY: deltaY + (snappedY?.offset || 0),
    guides,
  };
};

const beginMoveAction = (clientX, clientY) => {
  const targets = getSelectionTargets();
  if (!targets.length) return;
  const bounds = combineBounds(selectedCanvasBounds());
  if (!bounds) return;
  state.transformAction = {
    kind: "move",
    phase: "pending",
    startClientX: clientX,
    startClientY: clientY,
    baseBounds: bounds,
    entries: targets.map((target) => ({
      target,
      left: readInlineNumber(target, "left"),
      top: readInlineNumber(target, "top"),
    })),
  };
};

const beginResizeAction = (direction, clientX, clientY) => {
  if (state.selectedElements.length !== 1 || !state.primaryElement) return;
  const target = getTargetBlockForSizing(state.primaryElement);
  const rect = currentComputedRect(state.primaryElement);
  if (!target || !rect) return;
  const item = currentItem();
  if (!item) return;
  ensurePendingHistory(item.path);
  state.transformAction = {
    kind: "resize",
    phase: "active",
    direction,
    startClientX: clientX,
    startClientY: clientY,
    entry: {
      target,
      left: readInlineNumber(target, "left"),
      top: readInlineNumber(target, "top"),
      width: rect.width,
      height: rect.height,
    },
  };
  setInteractionShield(true, cursorForResize(direction));
};

const applyMoveAction = (action, clientX, clientY) => {
  const rawDeltaX = clientX - action.startClientX;
  const rawDeltaY = clientY - action.startClientY;
  const snap = computeSnapAdjustment(action.baseBounds, rawDeltaX, rawDeltaY, action.entries.map((entry) => entry.target));
  action.entries.forEach((entry) => {
    entry.target.style.position = entry.target.style.position || "relative";
    entry.target.style.left = `${Math.round(entry.left + snap.deltaX)}px`;
    entry.target.style.top = `${Math.round(entry.top + snap.deltaY)}px`;
  });
  renderGuides(snap.guides);
  renderSelectionOverlay();
  updateInspector();
};

const applyResizeAction = (action, clientX, clientY) => {
  const dx = clientX - action.startClientX;
  const dy = clientY - action.startClientY;
  const { direction, entry } = action;
  let nextLeft = entry.left;
  let nextTop = entry.top;
  let nextWidth = entry.width;
  let nextHeight = entry.height;
  if (direction.includes("e")) {
    nextWidth = entry.width + dx;
  }
  if (direction.includes("s")) {
    nextHeight = entry.height + dy;
  }
  if (direction.includes("w")) {
    nextWidth = entry.width - dx;
    nextLeft = entry.left + dx;
  }
  if (direction.includes("n")) {
    nextHeight = entry.height - dy;
    nextTop = entry.top + dy;
  }
  if (nextWidth < MIN_RESIZE) {
    if (direction.includes("w")) {
      nextLeft -= MIN_RESIZE - nextWidth;
    }
    nextWidth = MIN_RESIZE;
  }
  if (nextHeight < MIN_RESIZE) {
    if (direction.includes("n")) {
      nextTop -= MIN_RESIZE - nextHeight;
    }
    nextHeight = MIN_RESIZE;
  }
  entry.target.style.position = entry.target.style.position || "relative";
  entry.target.style.left = `${Math.round(nextLeft)}px`;
  entry.target.style.top = `${Math.round(nextTop)}px`;
  entry.target.style.width = `${Math.round(nextWidth)}px`;
  entry.target.style.height = `${Math.round(nextHeight)}px`;
  clearGuides();
  renderSelectionOverlay();
  updateInspector();
};

const finishTransformAction = () => {
  if (!state.transformAction) return;
  const active = state.transformAction.phase === "active";
  state.transformAction = null;
  setInteractionShield(false);
  clearGuides();
  renderSelectionOverlay();
  updateInspector();
  if (active) {
    const item = currentItem();
    if (item) {
      updateSessionCurrentFromDocument(item.path, false);
      commitHistory(item.path);
    }
  }
};

const handleTransformMove = (event) => {
  const action = state.transformAction;
  if (!action) return;
  const distance = Math.hypot(event.clientX - action.startClientX, event.clientY - action.startClientY);
  if (action.phase === "pending" && distance < 3) {
    return;
  }
  if (action.phase === "pending") {
    const item = currentItem();
    if (!item) return;
    ensurePendingHistory(item.path);
    action.phase = "active";
    setInteractionShield(true, "move");
  }
  if (action.kind === "move") {
    applyMoveAction(action, event.clientX, event.clientY);
  } else if (action.kind === "resize") {
    applyResizeAction(action, event.clientX, event.clientY);
  }
};

const handleDocMouseDown = (event) => {
  if (event.button !== 0) return;
  if (isEditableContext(event.target)) return;
  const selectable = resolveSelectableElement(event.target);
  if (!selectable) {
    clearSelection();
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  if (event.shiftKey) {
    toggleSelection(selectable);
    return;
  }
  if (!state.selectedElements.includes(selectable)) {
    setSelection([selectable], selectable);
  } else {
    setSelection(state.selectedElements, selectable);
  }
  if (event.detail > 1) return;
  beginMoveAction(event.clientX, event.clientY);
};

const handleDocDoubleClick = (event) => {
  const selectable = resolveSelectableElement(event.target);
  if (selectable && selectionKind(selectable) === "text") {
    event.preventDefault();
    event.stopPropagation();
    setSelection([selectable], selectable);
    openInlineEditing(selectable);
  }
};

const setupDocumentForEditing = () => {
  const frame = dom.previewFrame;
  const doc = frame.contentDocument;
  if (!doc) {
    dom.deckStatus.textContent = "iframe 不可访问";
    return;
  }
  ensureDocStyles(doc);
  doc.addEventListener("mousedown", handleDocMouseDown, true);
  doc.addEventListener("dblclick", handleDocDoubleClick, true);
  doc.addEventListener("mousemove", handleTransformMove, true);
  doc.addEventListener("mouseup", finishTransformAction, true);
  doc.addEventListener("dragstart", (event) => event.preventDefault(), true);
  state.activeDocument = doc;
  state.activeWindow = frame.contentWindow;
  state.frameLoadToken = 0;
  const bodyText = doc.body?.textContent?.trim() || "";
  dom.deckStatus.textContent = bodyText ? "iframe 已加载" : "iframe 内容为空";
  clearSelection();
  updateUndoRedoButtons();
  updatePageButtons();
};

const performUndo = async () => {
  const item = currentItem();
  if (item && state.activeDocument) {
    updateSessionCurrentFromDocument(item.path, false);
    commitHistory(item.path, false);
  }
  const entry = state.historyUndoStack.pop();
  if (!entry) return;
  state.isApplyingHistory = true;
  try {
    await entry.undo();
    state.historyRedoStack.push(entry);
  } finally {
    state.isApplyingHistory = false;
    updateUndoRedoButtons();
  }
  showToast(`已撤销：${entry.label}`);
};

const performRedo = async () => {
  const item = currentItem();
  if (item && state.activeDocument) {
    updateSessionCurrentFromDocument(item.path, false);
    commitHistory(item.path, false);
  }
  const entry = state.historyRedoStack.pop();
  if (!entry) return;
  state.isApplyingHistory = true;
  try {
    await entry.redo();
    state.historyUndoStack.push(entry);
  } finally {
    state.isApplyingHistory = false;
    updateUndoRedoButtons();
  }
  showToast(`已重做：${entry.label}`);
};

const ensureSavedForPageMutation = async (saveCurrentSlide = false) => {
  const item = currentItem();
  if (!item) return;
  if (!state.dirtyFiles.has(item.path)) return;
  if (item.kind === "cover" || saveCurrentSlide) {
    await saveCurrentFile();
  }
};

const createPage = async () => {
  try {
    const deck = currentDeck();
    const item = currentItem();
    if (!deck) return;
    await ensureSavedForPageMutation(false);
    const afterPath = item?.kind === "slide" ? item.path : deck.slides.at(-1)?.path;
    const payload = await requestJson("/api/page-create", {
      method: "POST",
      body: JSON.stringify({
        deck: deck.indexFile,
        afterPath,
      }),
    });
    clearFileSession(deck.indexFile);
    await applyDeckPayload(payload, deck.indexFile, payload.path);
    showToast("已新建一页");
  } catch (error) {
    showToast(error.message || "新建页面失败");
  }
};

const duplicatePage = async () => {
  try {
    const deck = currentDeck();
    const item = currentItem();
    if (!deck || !item || item.kind === "cover") {
      showToast("封面不能复制");
      return;
    }
    await ensureSavedForPageMutation(true);
    const payload = await requestJson("/api/page-duplicate", {
      method: "POST",
      body: JSON.stringify({
        deck: deck.indexFile,
        sourcePath: item.path,
      }),
    });
    clearFileSession(deck.indexFile);
    await applyDeckPayload(payload, deck.indexFile, payload.path);
    showToast("已复制当前页");
  } catch (error) {
    showToast(error.message || "复制页面失败");
  }
};

const deletePage = async () => {
  try {
    const deck = currentDeck();
    const item = currentItem();
    if (!deck || !item || item.kind === "cover") {
      showToast("封面不能删除");
      return;
    }
    const items = deckItems();
    const fallback = items[state.activeItemIndex + 1]?.path || items[state.activeItemIndex - 1]?.path || deck.indexFile;
    const payload = await requestJson("/api/page-delete", {
      method: "POST",
      body: JSON.stringify({
        deck: deck.indexFile,
        path: item.path,
      }),
    });
    clearFileSession(item.path);
    clearFileSession(deck.indexFile);
    await applyDeckPayload(payload, deck.indexFile, fallback);
    showToast("已删除当前页");
  } catch (error) {
    showToast(error.message || "删除页面失败");
  }
};

const handleGlobalKeydown = (event) => {
  if (isEditableContext(event.target) || state.activeDocument?.activeElement?.isContentEditable) {
    return;
  }
  const modifier = event.metaKey || event.ctrlKey;
  if (modifier && event.key.toLowerCase() === "z") {
    event.preventDefault();
    if (event.shiftKey) {
      performRedo();
    } else {
      performUndo();
    }
    return;
  }
  if (modifier && event.key.toLowerCase() === "y") {
    event.preventDefault();
    performRedo();
    return;
  }
  if ((event.key === "Backspace" || event.key === "Delete") && state.selectedElements.length) {
    event.preventDefault();
    deleteSelected();
  }
};

const bindControls = () => {
  dom.deckSelect.addEventListener("change", () => {
    state.activeDeckIndex = Number(dom.deckSelect.value || 0);
    state.activeItemIndex = 0;
    renderSlideList();
    loadItem(0);
  });

  dom.previewFrame.addEventListener("load", setupDocumentForEditing);
  dom.undoBtn.addEventListener("click", performUndo);
  dom.redoBtn.addEventListener("click", performRedo);
  dom.saveBtn.addEventListener("click", saveCurrentFile);
  dom.reloadBtn.addEventListener("click", reloadCurrent);
  dom.openPlayerBtn.addEventListener("click", openPlayer);
  dom.newPageBtn.addEventListener("click", createPage);
  dom.duplicatePageBtn.addEventListener("click", duplicatePage);
  dom.deletePageBtn.addEventListener("click", deletePage);
  dom.addTextBtn.addEventListener("click", appendTextBlock);
  dom.addImageBtn.addEventListener("click", () => {
    state.imageMode = "add";
    dom.imagePicker.click();
  });
  dom.deleteBtn.addEventListener("click", deleteSelected);
  dom.replaceImageBtn.addEventListener("click", () => {
    state.imageMode = "replace";
    dom.imagePicker.click();
  });
  dom.imagePicker.addEventListener("change", async (event) => {
    const [file] = event.target.files || [];
    if (!file) return;
    try {
      const uploadedPath = await uploadImage(file);
      if (state.imageMode === "replace" && activeImage()) {
        const image = activeImage();
        image.setAttribute("src", toDocRelativeAssetPath(uploadedPath));
        populateImageControls(state.primaryElement);
        renderSelectionOverlay();
        recordDomMutation("instant");
      } else {
        appendImageBlock(uploadedPath);
      }
      showToast("图片已上传");
    } catch (error) {
      showToast(error.message || "图片上传失败");
    }
    dom.imagePicker.value = "";
  });

  [dom.offsetXInput, dom.offsetYInput, dom.widthInput, dom.heightInput].forEach((input) => {
    input.addEventListener("input", applyOffset);
  });

  dom.textContentInput.addEventListener("input", applyTextContent);
  [
    dom.fontSizeInput,
    dom.fontWeightInput,
    dom.colorInput,
    dom.textAlignInput,
    dom.lineHeightInput,
    dom.letterSpacingInput,
  ].forEach((input) => input.addEventListener("input", applyTextStyle));

  [dom.imageSrcInput, dom.imageAltInput].forEach((input) => input.addEventListener("input", applyImageContent));
  [dom.imageFitInput, dom.imageOpacityInput].forEach((input) => input.addEventListener("input", applyImageStyle));

  [
    dom.soundPresetInput,
    dom.soundIntensityInput,
    dom.soundBrightnessInput,
    dom.soundTailInput,
    dom.soundChirpInput,
    dom.soundStereoInput,
  ].forEach((input) => input.addEventListener("input", syncSoundConfigFromInputs));

  dom.saveSoundBtn.addEventListener("click", saveSoundConfig);
  dom.previewPrevSoundBtn.addEventListener("click", async () => {
    await soundPreview.unlock();
    syncSoundConfigFromInputs();
    soundPreview.play(-1);
  });
  dom.previewNextSoundBtn.addEventListener("click", async () => {
    await soundPreview.unlock();
    syncSoundConfigFromInputs();
    soundPreview.play(1);
  });

  dom.selectionBox.querySelectorAll("[data-resize]").forEach((handle) => {
    handle.addEventListener("mousedown", (event) => {
      event.preventDefault();
      event.stopPropagation();
      beginResizeAction(handle.dataset.resize, event.clientX, event.clientY);
    });
  });

  dom.interactionShield.addEventListener("mousemove", handleTransformMove);
  dom.interactionShield.addEventListener("mouseup", finishTransformAction);
  window.addEventListener("mousemove", handleTransformMove);
  window.addEventListener("mouseup", finishTransformAction);
  window.addEventListener("resize", renderSelectionOverlay);
  window.addEventListener("keydown", handleGlobalKeydown);
  window.addEventListener(
    "pointerdown",
    () => {
      soundPreview.unlock();
    },
    { passive: true }
  );
};

const bootstrap = async () => {
  bindControls();
  dom.textControls.style.display = "none";
  dom.imageControls.style.display = "none";
  updatePageButtons();
  updateUndoRedoButtons();
  try {
    await Promise.all([loadDecks(), loadSoundConfig()]);
    showToast("编辑器已准备好");
  } catch (error) {
    dom.deckStatus.textContent = "加载失败";
    showToast(error.message || "编辑器启动失败");
  }
};

bootstrap();
