(() => {
  const root = document.documentElement;
  const body = document.body;
  const mode = body.dataset.mode || "slide";

  const updatePointer = (event) => {
    const x = ((event.clientX || window.innerWidth / 2) / window.innerWidth) * 100;
    const y = ((event.clientY || window.innerHeight / 2) / window.innerHeight) * 100;
    root.style.setProperty("--mouse-x", `${x}%`);
    root.style.setProperty("--mouse-y", `${y}%`);
  };

  const initPointer = () => {
    updatePointer({ clientX: window.innerWidth / 2, clientY: window.innerHeight / 2 });
    window.addEventListener("mousemove", updatePointer, { passive: true });
  };

  const initTilt = () => {
    document.querySelectorAll(".tilt-card").forEach((card) => {
      card.addEventListener("mousemove", (event) => {
        const rect = card.getBoundingClientRect();
        const px = ((event.clientX - rect.left) / rect.width - 0.5) * 2;
        const py = ((event.clientY - rect.top) / rect.height - 0.5) * 2;
        card.style.transform = `perspective(1000px) rotateX(${-py * 4}deg) rotateY(${px * 5}deg) translate(-4px, -4px)`;
      });
      card.addEventListener("mouseleave", () => {
        card.style.transform = "";
      });
    });
  };

  const initReveal = () => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        root.classList.add("is-ready");
      });
    });
  };

  const replayReveal = () => {
    root.classList.remove("is-ready");
    void body.offsetWidth;
    root.classList.add("is-ready");
  };

  const initPageSound = () => {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) {
      return {
        unlock: async () => {},
        play: async () => {},
      };
    }

    let audioContext;
    let noiseBuffer;

    const getContext = () => {
      if (!audioContext) {
        audioContext = new AudioContextClass({ latencyHint: "interactive" });
      }
      return audioContext;
    };

    const getNoiseBuffer = () => {
      const context = getContext();
      if (noiseBuffer && noiseBuffer.sampleRate === context.sampleRate) {
        return noiseBuffer;
      }
      const length = Math.max(1, Math.floor(context.sampleRate * 0.34));
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

      const isForward = direction >= 0;
      const start = context.currentTime + 0.01;
      const noise = context.createBufferSource();
      noise.buffer = getNoiseBuffer();

      const master = context.createGain();
      master.gain.setValueAtTime(0.0001, start);
      master.gain.exponentialRampToValueAtTime(0.064, start + 0.018);
      master.gain.exponentialRampToValueAtTime(0.02, start + 0.12);
      master.gain.exponentialRampToValueAtTime(0.0001, start + 0.32);
      master.connect(context.destination);

      const highpass = context.createBiquadFilter();
      highpass.type = "highpass";
      highpass.frequency.setValueAtTime(isForward ? 220 : 200, start);
      highpass.frequency.exponentialRampToValueAtTime(isForward ? 540 : 480, start + 0.24);
      highpass.Q.setValueAtTime(0.9, start);

      const lowpass = context.createBiquadFilter();
      lowpass.type = "lowpass";
      lowpass.frequency.setValueAtTime(isForward ? 2600 : 2400, start);
      lowpass.frequency.exponentialRampToValueAtTime(isForward ? 760 : 700, start + 0.3);
      lowpass.Q.setValueAtTime(0.92, start);

      const bandpass = context.createBiquadFilter();
      bandpass.type = "bandpass";
      bandpass.frequency.setValueAtTime(isForward ? 720 : 640, start);
      bandpass.frequency.exponentialRampToValueAtTime(isForward ? 380 : 340, start + 0.24);
      bandpass.Q.setValueAtTime(1.06, start);

      const panner = typeof context.createStereoPanner === "function" ? context.createStereoPanner() : null;
      if (panner) {
        panner.pan.setValueAtTime(isForward ? -0.08 : 0.08, start);
        panner.pan.linearRampToValueAtTime(isForward ? 0.08 : -0.08, start + 0.24);
      }

      const noiseGain = context.createGain();
      noiseGain.gain.setValueAtTime(0.0001, start);
      noiseGain.gain.exponentialRampToValueAtTime(0.98, start + 0.025);
      noiseGain.gain.exponentialRampToValueAtTime(0.42, start + 0.11);
      noiseGain.gain.exponentialRampToValueAtTime(0.0001, start + 0.3);

      noise.playbackRate.setValueAtTime(isForward ? 0.92 : 0.88, start);
      noise.connect(highpass);
      highpass.connect(lowpass);
      lowpass.connect(bandpass);
      bandpass.connect(noiseGain);
      noiseGain.connect(panner || master);
      if (panner) {
        panner.connect(master);
      }

      const chirpGain = context.createGain();
      chirpGain.gain.setValueAtTime(0.0001, start + 0.014);
      chirpGain.gain.exponentialRampToValueAtTime(0.004, start + 0.028);
      chirpGain.gain.exponentialRampToValueAtTime(0.0001, start + 0.14);
      chirpGain.connect(master);

      const chirpOsc = context.createOscillator();
      chirpOsc.type = "triangle";
      chirpOsc.frequency.setValueAtTime(isForward ? 640 : 580, start + 0.014);
      chirpOsc.frequency.exponentialRampToValueAtTime(isForward ? 300 : 260, start + 0.14);
      chirpOsc.connect(chirpGain);

      const tickGain = context.createGain();
      tickGain.gain.setValueAtTime(0.0001, start + 0.018);
      tickGain.gain.exponentialRampToValueAtTime(0.006, start + 0.03);
      tickGain.gain.exponentialRampToValueAtTime(0.0001, start + 0.06);
      tickGain.connect(master);

      const tickOsc = context.createOscillator();
      tickOsc.type = "sine";
      tickOsc.frequency.setValueAtTime(isForward ? 420 : 360, start + 0.018);
      tickOsc.frequency.exponentialRampToValueAtTime(isForward ? 240 : 220, start + 0.06);
      tickOsc.connect(tickGain);

      const tailGain = context.createGain();
      tailGain.gain.setValueAtTime(0.0001, start + 0.04);
      tailGain.gain.exponentialRampToValueAtTime(0.018, start + 0.09);
      tailGain.gain.exponentialRampToValueAtTime(0.0001, start + 0.28);
      tailGain.connect(master);

      const tailOsc = context.createOscillator();
      tailOsc.type = "triangle";
      tailOsc.frequency.setValueAtTime(isForward ? 240 : 220, start + 0.04);
      tailOsc.frequency.exponentialRampToValueAtTime(isForward ? 120 : 110, start + 0.28);
      tailOsc.connect(tailGain);

      noise.start(start);
      chirpOsc.start(start + 0.014);
      tickOsc.start(start + 0.018);
      tailOsc.start(start + 0.03);

      noise.stop(start + 0.3);
      chirpOsc.stop(start + 0.14);
      tickOsc.stop(start + 0.06);
      tailOsc.stop(start + 0.28);
    };

    return { unlock, play };
  };

  const connectSwarm = () => {
    document.querySelectorAll(".swarm-board").forEach((board) => {
      const core = board.querySelector(".swarm-core");
      if (!core) return;
      const coreRect = core.getBoundingClientRect();
      const boardRect = board.getBoundingClientRect();
      const coreX = coreRect.left + coreRect.width / 2 - boardRect.left;
      const coreY = coreRect.top + coreRect.height / 2 - boardRect.top;

      board.querySelectorAll(".swarm-line").forEach((line) => line.remove());

      board.querySelectorAll(".swarm-node").forEach((node) => {
        const nodeRect = node.getBoundingClientRect();
        const nodeX = nodeRect.left + nodeRect.width / 2 - boardRect.left;
        const nodeY = nodeRect.top + nodeRect.height / 2 - boardRect.top;
        const deltaX = nodeX - coreX;
        const deltaY = nodeY - coreY;
        const length = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
        const angle = Math.atan2(deltaY, deltaX) * 180 / Math.PI;
        const line = document.createElement("div");
        line.className = "swarm-line";
        line.style.left = `${coreX}px`;
        line.style.top = `${coreY}px`;
        line.style.width = `${length}px`;
        line.style.transform = `rotate(${angle}deg)`;
        board.appendChild(line);
      });
    });
  };

  const initParticles = ({ activeByDefault = true } = {}) => {
    const canvas = document.querySelector(".particle-canvas");
    if (!canvas) {
      return { setActive() {} };
    }

    const context = canvas.getContext("2d");
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let active = activeByDefault;
    let frame = 0;
    let rafId = 0;
    let particles = [];

    const resize = () => {
      const width = Math.max(canvas.clientWidth, window.innerWidth);
      const height = Math.max(canvas.clientHeight, window.innerHeight);
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
      const total = Math.max(18, Math.min(36, Math.round((width * height) / 65000)));
      particles = Array.from({ length: total }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        size: Math.random() * 3 + 1,
        speedX: (Math.random() - 0.5) * 0.35,
        speedY: (Math.random() - 0.5) * 0.35,
        alpha: Math.random() * 0.5 + 0.16,
      }));
    };

    const draw = () => {
      const width = canvas.width / dpr;
      const height = canvas.height / dpr;
      context.clearRect(0, 0, width, height);
      frame += 0.005;

      particles.forEach((particle, index) => {
        particle.x += particle.speedX + Math.sin(frame + index) * 0.08;
        particle.y += particle.speedY + Math.cos(frame + index) * 0.08;

        if (particle.x < -10) particle.x = width + 10;
        if (particle.x > width + 10) particle.x = -10;
        if (particle.y < -10) particle.y = height + 10;
        if (particle.y > height + 10) particle.y = -10;

        context.fillStyle = `rgba(216, 23, 32, ${particle.alpha})`;
        context.fillRect(particle.x, particle.y, particle.size, particle.size);
      });
    };

    const loop = () => {
      if (!active) {
        rafId = 0;
        return;
      }
      draw();
      rafId = requestAnimationFrame(loop);
    };

    const setActive = (next) => {
      active = next;
      if (active && !rafId) {
        loop();
      }
    };

    resize();
    setActive(active);
    window.addEventListener("resize", () => {
      resize();
      connectSwarm();
    });

    return { setActive };
  };

  const initShell = () => {
    const frames = Array.from(document.querySelectorAll(".deck-slide"));
    const startButton = document.querySelector("[data-start]");
    const counter = document.querySelector("[data-counter]");
    const shutter = document.querySelector("[data-shutter]");
    const particles = initParticles({ activeByDefault: true });
    const pageSound = initPageSound();
    let current = -1;

    const updateCounter = () => {
      if (!counter || current < 0) return;
      counter.textContent = `${String(current + 1).padStart(2, "0")} / ${String(frames.length).padStart(2, "0")}`;
    };

    const pulseShutter = () => {
      if (!shutter) return;
      shutter.classList.remove("is-pulsing");
      void shutter.offsetWidth;
      shutter.classList.add("is-pulsing");
    };

    const broadcastState = (direction = 1) => {
      frames.forEach((frame, index) => {
        const active = index === current;
        frame.setAttribute("aria-hidden", String(!active));
        if (frame.contentWindow) {
          frame.contentWindow.postMessage({ type: "deck-visibility", active, direction }, "*");
        }
      });
      updateCounter();
    };

    const goTo = (nextIndex) => {
      const clamped = Math.max(0, Math.min(frames.length - 1, nextIndex));
      if (clamped === current) return;
      const previousIndex = current;
      const direction = previousIndex === -1 || clamped > previousIndex ? 1 : -1;
      const incoming = frames[clamped];
      const outgoing = previousIndex >= 0 ? frames[previousIndex] : null;

      frames.forEach((frame) => {
        frame.classList.remove("is-enter-next", "is-enter-prev", "is-exit-next", "is-exit-prev");
      });

      incoming.classList.add(direction > 0 ? "is-enter-next" : "is-enter-prev");
      incoming.setAttribute("aria-hidden", "false");

      requestAnimationFrame(() => {
        if (outgoing) {
          outgoing.classList.remove("is-active");
          outgoing.classList.add(direction > 0 ? "is-exit-next" : "is-exit-prev");
          setTimeout(() => {
            outgoing.classList.remove("is-exit-next", "is-exit-prev");
          }, 380);
        }
        incoming.classList.add("is-active");
        incoming.classList.remove("is-enter-next", "is-enter-prev");
        current = clamped;
        pulseShutter();
        pageSound.play(direction);
        broadcastState(direction);
      });

      body.classList.add("is-playing");
    };

    const start = async () => {
      await pageSound.unlock();
      try {
        if (!document.fullscreenElement) {
          await document.documentElement.requestFullscreen();
        }
      } catch (error) {
      }
      goTo(0);
    };

    startButton?.addEventListener("click", start);
    window.addEventListener("pointerdown", () => {
      pageSound.unlock();
    }, { passive: true });

    window.addEventListener("keydown", (event) => {
      pageSound.unlock();
      if (!body.classList.contains("is-playing")) return;
      if (event.key === "ArrowRight" || event.key === "PageDown" || event.key === " ") {
        event.preventDefault();
        goTo(current + 1);
      }
      if (event.key === "ArrowLeft" || event.key === "PageUp") {
        event.preventDefault();
        goTo(current - 1);
      }
    });

    window.addEventListener("message", (event) => {
      if (event.data?.type === "deck-nav") {
        goTo(current + Number(event.data.direction || 0));
      }
    });

    frames.forEach((frame) => {
      frame.addEventListener("load", () => {
        if (current >= 0) {
          const active = frames.indexOf(frame) === current;
          frame.contentWindow?.postMessage({ type: "deck-visibility", active, direction: 1 }, "*");
        }
      });
    });

    initPointer();
    initReveal();
    particles.setActive(true);
  };

  const initSlide = () => {
    const particles = initParticles({ activeByDefault: window.top === window.self });
    initPointer();
    initTilt();
    initReveal();
    connectSwarm();

    window.addEventListener("keydown", (event) => {
      if (window.parent === window) return;
      if (event.key === "ArrowRight" || event.key === "PageDown" || event.key === " ") {
        window.parent.postMessage({ type: "deck-nav", direction: 1 }, "*");
      }
      if (event.key === "ArrowLeft" || event.key === "PageUp") {
        window.parent.postMessage({ type: "deck-nav", direction: -1 }, "*");
      }
    });

    window.addEventListener("message", (event) => {
      if (event.data?.type === "deck-visibility") {
        const active = Boolean(event.data.active);
        particles.setActive(active);
        if (active) {
          replayReveal();
          setTimeout(connectSwarm, 50);
        }
      }
    });
  };

  if (mode === "shell") {
    initShell();
  } else {
    initSlide();
  }
})();
