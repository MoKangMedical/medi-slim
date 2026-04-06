(function () {
  const canvas = document.getElementById('filmCanvas');
  const voiceover = document.getElementById('filmVoiceover');
  if (!canvas || !voiceover) {
    return;
  }

  const ctx = canvas.getContext('2d');
  const WIDTH = canvas.width;
  const HEIGHT = canvas.height;
  const FPS = 24;
  const voiceoverUrl = voiceover.getAttribute('src');
  const sceneList = document.getElementById('filmSceneList');
  const currentSubtitle = document.getElementById('filmCurrentSubtitle');
  const timeNode = document.getElementById('filmTime');
  const sceneIndexNode = document.getElementById('filmSceneIndex');
  const playButton = document.getElementById('filmPlayButton');
  const audioButton = document.getElementById('filmAudioButton');
  const restartButton = document.getElementById('filmRestartButton');
  const params = new URLSearchParams(window.location.search);

  const state = {
    manifest: null,
    sceneNodes: [],
    assets: new Map(),
    ready: null,
    audioArrayBuffer: null,
    audioEnabled: params.get('voice') === '1',
    playing: false,
    currentTime: 0,
    startedAt: 0,
    rafId: 0,
    lastSceneId: '',
  };

  const assetUrls = {
    glp1: '/static/media/products/glp1.svg',
    sleep: '/static/media/products/sleep.svg',
    skin: '/static/media/products/skin.svg',
    hospitalJd: '/static/media/partners/jd-health.svg',
    hospitalWe: '/static/media/partners/wedoctor.svg',
    pharmacyDs: '/static/media/partners/dashenlin.svg',
    pharmacyYf: '/static/media/partners/yifeng.svg',
    portraitPhone: '/static/media/demo/portraits/woman-phone.jpg',
    portraitWindow: '/static/media/demo/portraits/woman-window.jpg',
  };

  const scenePalettes = {
    intro: {
      top: '#f3ede4',
      bottom: '#cdbfb1',
      accentA: 'rgba(15, 143, 111, 0.24)',
      accentB: 'rgba(245, 123, 66, 0.22)',
    },
    imbalance: {
      top: '#f6efe4',
      bottom: '#dbc9bd',
      accentA: 'rgba(15, 143, 111, 0.22)',
      accentB: 'rgba(245, 123, 66, 0.22)',
    },
    scan: {
      top: '#eef4ef',
      bottom: '#dae7df',
      accentA: 'rgba(15, 143, 111, 0.18)',
      accentB: 'rgba(63, 94, 251, 0.12)',
    },
    data: {
      top: '#f4f7f5',
      bottom: '#dfe8e3',
      accentA: 'rgba(15, 143, 111, 0.22)',
      accentB: 'rgba(245, 123, 66, 0.18)',
    },
    plan: {
      top: '#f8f1e8',
      bottom: '#e6d4c7',
      accentA: 'rgba(15, 143, 111, 0.18)',
      accentB: 'rgba(245, 123, 66, 0.24)',
    },
    network: {
      top: '#eef5f1',
      bottom: '#dce6df',
      accentA: 'rgba(15, 143, 111, 0.2)',
      accentB: 'rgba(22, 54, 48, 0.12)',
    },
    outcome: {
      top: '#faf4eb',
      bottom: '#e6ddcf',
      accentA: 'rgba(245, 123, 66, 0.2)',
      accentB: 'rgba(15, 143, 111, 0.18)',
    },
    outro: {
      top: '#173630',
      bottom: '#0f201c',
      accentA: 'rgba(15, 143, 111, 0.3)',
      accentB: 'rgba(245, 123, 66, 0.18)',
    },
  };

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function ease(value) {
    const t = clamp(value, 0, 1);
    return t * t * (3 - 2 * t);
  }

  function easeOut(value) {
    const t = clamp(value, 0, 1);
    return 1 - Math.pow(1 - t, 3);
  }

  function wait(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  function formatTime(seconds) {
    const total = Math.max(0, Math.floor(seconds));
    const mins = String(Math.floor(total / 60)).padStart(2, '0');
    const secs = String(total % 60).padStart(2, '0');
    return `${mins}:${secs}`;
  }

  function roundedRect(pathCtx, x, y, width, height, radius) {
    const r = Math.min(radius, width / 2, height / 2);
    pathCtx.beginPath();
    pathCtx.moveTo(x + r, y);
    pathCtx.arcTo(x + width, y, x + width, y + height, r);
    pathCtx.arcTo(x + width, y + height, x, y + height, r);
    pathCtx.arcTo(x, y + height, x, y, r);
    pathCtx.arcTo(x, y, x + width, y, r);
    pathCtx.closePath();
  }

  function fillRoundRect(pathCtx, x, y, width, height, radius, fillStyle) {
    pathCtx.save();
    roundedRect(pathCtx, x, y, width, height, radius);
    pathCtx.fillStyle = fillStyle;
    pathCtx.fill();
    pathCtx.restore();
  }

  function strokeRoundRect(pathCtx, x, y, width, height, radius, strokeStyle, lineWidth) {
    pathCtx.save();
    roundedRect(pathCtx, x, y, width, height, radius);
    pathCtx.strokeStyle = strokeStyle;
    pathCtx.lineWidth = lineWidth;
    pathCtx.stroke();
    pathCtx.restore();
  }

  function wrapText(text, maxWidth, font) {
    ctx.save();
    ctx.font = font;
    const lines = [];
    const paragraphs = String(text || '').split('\n');

    paragraphs.forEach((paragraph) => {
      let current = '';
      paragraph.split('').forEach((char) => {
        const trial = current + char;
        if (!current || ctx.measureText(trial).width <= maxWidth) {
          current = trial;
        } else {
          lines.push(current);
          current = char;
        }
      });
      if (current) {
        lines.push(current);
      }
    });
    ctx.restore();
    return lines;
  }

  function drawTextBlock(text, x, y, maxWidth, font, fillStyle, lineHeight) {
    const lines = wrapText(text, maxWidth, font);
    ctx.save();
    ctx.font = font;
    ctx.fillStyle = fillStyle;
    lines.forEach((line, index) => {
      ctx.fillText(line, x, y + index * lineHeight);
    });
    ctx.restore();
  }

  function drawGradientBackground(palette) {
    const gradient = ctx.createLinearGradient(0, 0, 0, HEIGHT);
    gradient.addColorStop(0, palette.top);
    gradient.addColorStop(1, palette.bottom);
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, WIDTH, HEIGHT);

    ctx.save();
    ctx.filter = 'blur(70px)';
    ctx.fillStyle = palette.accentA;
    ctx.beginPath();
    ctx.arc(240, 120, 170, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = palette.accentB;
    ctx.beginPath();
    ctx.arc(WIDTH - 160, HEIGHT - 120, 180, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  function drawTopChrome(scene, sceneIndex, time) {
    fillRoundRect(ctx, 48, 34, 158, 40, 20, 'rgba(255,255,255,0.56)');
    ctx.fillStyle = '#115442';
    ctx.font = '700 18px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText('MediSlim Film', 72, 60);

    ctx.save();
    ctx.textAlign = 'right';
    ctx.fillStyle = 'rgba(23,54,48,0.7)';
    ctx.font = '600 17px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText(`镜头 ${String(sceneIndex + 1).padStart(2, '0')} / ${String(state.manifest.scenes.length).padStart(2, '0')}`, WIDTH - 52, 58);
    ctx.restore();

    const progress = state.manifest.duration ? clamp(time / state.manifest.duration, 0, 1) : 0;
    fillRoundRect(ctx, 48, 94, WIDTH - 96, 6, 999, 'rgba(23,54,48,0.08)');
    const progressGradient = ctx.createLinearGradient(48, 0, WIDTH - 48, 0);
    progressGradient.addColorStop(0, '#0f8f6f');
    progressGradient.addColorStop(1, '#f57b42');
    fillRoundRect(ctx, 48, 94, (WIDTH - 96) * progress, 6, 999, progressGradient);

    ctx.save();
    ctx.fillStyle = '#173630';
    ctx.font = '700 52px "Iowan Old Style", "Georgia", "STSong", serif';
    drawTextBlock(scene.headline || scene.title, 62, 180, 520, ctx.font, '#173630', 58);
    ctx.restore();

    ctx.save();
    ctx.fillStyle = 'rgba(23,54,48,0.66)';
    ctx.font = '500 24px "Avenir Next", "PingFang SC", sans-serif';
    drawTextBlock(scene.summary || '', 66, 312, 500, ctx.font, 'rgba(23,54,48,0.66)', 34);
    ctx.restore();
  }

  function drawGlassCard(x, y, width, height, radius) {
    fillRoundRect(ctx, x, y, width, height, radius, 'rgba(255,255,255,0.72)');
    strokeRoundRect(ctx, x, y, width, height, radius, 'rgba(255,255,255,0.44)', 1);
  }

  function drawImageCover(image, x, y, width, height, options) {
    if (!image) {
      return;
    }
    const opts = options || {};
    const focusX = typeof opts.focusX === 'number' ? opts.focusX : 0.5;
    const focusY = typeof opts.focusY === 'number' ? opts.focusY : 0.5;
    const zoom = typeof opts.zoom === 'number' ? opts.zoom : 1;
    const scale = Math.max(width / image.width, height / image.height) * zoom;
    const drawWidth = image.width * scale;
    const drawHeight = image.height * scale;
    const offsetX = x + (width - drawWidth) * focusX;
    const offsetY = y + (height - drawHeight) * focusY;
    ctx.drawImage(image, offsetX, offsetY, drawWidth, drawHeight);
  }

  function drawPhotoPanel(x, y, width, height, image, options) {
    const opts = options || {};
    const radius = typeof opts.radius === 'number' ? opts.radius : 36;
    const border = opts.border || 'rgba(255,255,255,0.34)';
    const shadow = opts.shadow || 'rgba(23,54,48,0.14)';
    ctx.save();
    ctx.shadowColor = shadow;
    ctx.shadowBlur = 26;
    ctx.shadowOffsetY = 18;
    roundedRect(ctx, x, y, width, height, radius);
    ctx.fillStyle = opts.background || '#e8dfd4';
    ctx.fill();
    ctx.restore();

    ctx.save();
    roundedRect(ctx, x, y, width, height, radius);
    ctx.clip();
    drawImageCover(image, x, y, width, height, {
      focusX: opts.focusX,
      focusY: opts.focusY,
      zoom: opts.zoom,
    });

    const overlay = ctx.createLinearGradient(x, y, x + width, y + height);
    overlay.addColorStop(0, opts.overlayFrom || 'rgba(15, 32, 28, 0.08)');
    overlay.addColorStop(1, opts.overlayTo || 'rgba(15, 32, 28, 0.42)');
    ctx.fillStyle = overlay;
    ctx.fillRect(x, y, width, height);

    if (opts.highlight) {
      const glow = ctx.createRadialGradient(x + width * 0.78, y + height * 0.16, 18, x + width * 0.78, y + height * 0.16, width * 0.44);
      glow.addColorStop(0, opts.highlight);
      glow.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.fillStyle = glow;
      ctx.fillRect(x, y, width, height);
    }
    ctx.restore();

    strokeRoundRect(ctx, x, y, width, height, radius, border, 1);

    if (opts.label) {
      drawBadge(opts.label, x + 22, y + 20, opts.labelWidth || 104);
    }
  }

  function drawBadge(label, x, y, width) {
    fillRoundRect(ctx, x, y, width, 34, 18, 'rgba(255,255,255,0.78)');
    ctx.save();
    ctx.fillStyle = '#173630';
    ctx.font = '700 16px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText(label, x + 14, y + 22);
    ctx.restore();
  }

  function drawFigure(cx, cy, scale, options) {
    const skin = options.skin || '#f0d7c0';
    const clothing = options.clothing || '#1b5b4c';
    const posture = options.posture || 0;
    const faceGlow = options.faceGlow || 'rgba(255,255,255,0.18)';

    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(scale, scale);

    ctx.fillStyle = 'rgba(17,37,32,0.14)';
    ctx.beginPath();
    ctx.ellipse(0, 190, 118, 26, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = skin;
    ctx.beginPath();
    ctx.arc(0, -78, 68, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = faceGlow;
    ctx.beginPath();
    ctx.arc(18, -92, 34, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#283c35';
    ctx.beginPath();
    ctx.ellipse(-4, -104, 72, 52, -0.18, Math.PI, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = clothing;
    roundedRect(ctx, -86, -8 + posture, 172, 188, 84);
    ctx.fill();

    ctx.fillStyle = skin;
    roundedRect(ctx, -112, 22 + posture * 0.4, 40, 124, 20);
    ctx.fill();
    roundedRect(ctx, 72, 28 + posture * 0.2, 40, 116, 20);
    ctx.fill();

    ctx.fillStyle = '#f4e6da';
    roundedRect(ctx, -44, 44 + posture * 0.25, 88, 104, 34);
    ctx.fill();

    ctx.restore();
  }

  function drawSignalChip(x, y, label, value, accent) {
    drawGlassCard(x, y, 156, 60, 20);
    ctx.save();
    ctx.fillStyle = accent;
    ctx.font = '700 16px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText(label, x + 18, y + 22);
    ctx.fillStyle = '#173630';
    ctx.font = '700 24px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText(value, x + 18, y + 46);
    ctx.restore();
  }

  function drawLogoMark(cx, cy, progress, options) {
    const opts = options || {};
    const accentA = opts.accentA || '#0f8f6f';
    const accentB = opts.accentB || '#f57b42';
    const scale = lerp(0.76, 1, easeOut(progress));
    const glow = lerp(0.12, 0.38, ease(progress));

    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(scale, scale);
    ctx.globalAlpha = lerp(0.18, 1, easeOut(progress));

    ctx.strokeStyle = `rgba(255,255,255,${glow})`;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(0, 0, 84, 0, Math.PI * 2);
    ctx.stroke();

    ctx.strokeStyle = 'rgba(255,255,255,0.14)';
    ctx.beginPath();
    ctx.arc(0, 0, 112, 0, Math.PI * 2);
    ctx.stroke();

    fillRoundRect(ctx, -38, -60, 28, 118, 16, accentA);
    fillRoundRect(ctx, 12, -44, 28, 88, 16, accentB);
    fillRoundRect(ctx, -4, -18, 28, 36, 14, 'rgba(255,255,255,0.94)');

    ctx.fillStyle = 'rgba(255,255,255,0.18)';
    ctx.beginPath();
    ctx.arc(-60, -72, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(64, 72, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  function drawPhoneShell(x, y, width, height) {
    fillRoundRect(ctx, x, y, width, height, 38, '#182d28');
    fillRoundRect(ctx, x + 16, y + 18, width - 32, height - 36, 28, 'rgba(255,255,255,0.04)');
    fillRoundRect(ctx, x + width / 2 - 44, y + 14, 88, 8, 8, 'rgba(255,255,255,0.18)');
  }

  function drawRadar(centerX, centerY, radius, progress) {
    ctx.save();
    ctx.translate(centerX, centerY);
    ctx.strokeStyle = 'rgba(255,255,255,0.2)';
    ctx.lineWidth = 1;
    for (let ring = 1; ring <= 4; ring += 1) {
      ctx.beginPath();
      ctx.arc(0, 0, (radius / 4) * ring, 0, Math.PI * 2);
      ctx.stroke();
    }
    for (let i = 0; i < 6; i += 1) {
      const angle = (-Math.PI / 2) + (Math.PI * 2 * i) / 6;
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(Math.cos(angle) * radius, Math.sin(angle) * radius);
      ctx.stroke();
    }

    const values = [0.8, 0.62, 0.54, 0.7, 0.42, 0.58].map((value, index) => clamp(value * easeOut(progress + index * 0.02), 0, 1));
    ctx.beginPath();
    values.forEach((value, index) => {
      const angle = (-Math.PI / 2) + (Math.PI * 2 * index) / 6;
      const px = Math.cos(angle) * radius * value;
      const py = Math.sin(angle) * radius * value;
      if (index === 0) {
        ctx.moveTo(px, py);
      } else {
        ctx.lineTo(px, py);
      }
    });
    ctx.closePath();
    ctx.fillStyle = 'rgba(245,123,66,0.28)';
    ctx.fill();
    ctx.strokeStyle = '#f57b42';
    ctx.lineWidth = 3;
    ctx.stroke();
    ctx.restore();
  }

  function drawLineChart(x, y, width, height, points, progress, color, fillColor) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(x, y, width, height);
    ctx.clip();

    ctx.strokeStyle = 'rgba(23,54,48,0.1)';
    ctx.lineWidth = 1;
    for (let row = 0; row <= 4; row += 1) {
      const yy = y + (height / 4) * row;
      ctx.beginPath();
      ctx.moveTo(x, yy);
      ctx.lineTo(x + width, yy);
      ctx.stroke();
    }

    const reveal = clamp(progress, 0, 1);
    const visible = Math.max(2, Math.ceil(points.length * reveal));
    const rendered = points.slice(0, visible);
    const max = Math.max.apply(null, rendered);
    const min = Math.min.apply(null, rendered);
    const range = Math.max(1, max - min);

    const toX = (index) => x + (width * index) / (points.length - 1);
    const toY = (value) => y + height - ((value - min) / range) * height;

    const area = new Path2D();
    area.moveTo(toX(0), y + height);
    rendered.forEach((value, index) => {
      area.lineTo(toX(index), toY(value));
    });
    area.lineTo(toX(rendered.length - 1), y + height);
    area.closePath();

    ctx.fillStyle = fillColor;
    ctx.fill(area);

    ctx.beginPath();
    rendered.forEach((value, index) => {
      const px = toX(index);
      const py = toY(value);
      if (index === 0) {
        ctx.moveTo(px, py);
      } else {
        ctx.lineTo(px, py);
      }
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = 4;
    ctx.stroke();

    const lastIndex = rendered.length - 1;
    const lx = toX(lastIndex);
    const ly = toY(rendered[lastIndex]);
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(lx, ly, 7, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  function drawBars(x, y, width, labels, values, progress, accent) {
    const barGap = 14;
    const barHeight = 16;
    ctx.save();
    ctx.font = '600 16px "Avenir Next", "PingFang SC", sans-serif';
    labels.forEach((label, index) => {
      const top = y + index * 54;
      ctx.fillStyle = 'rgba(23,54,48,0.72)';
      ctx.fillText(label, x, top + 16);
      fillRoundRect(ctx, x, top + 28, width, barHeight, 999, 'rgba(23,54,48,0.1)');
      fillRoundRect(ctx, x, top + 28, width * clamp(values[index] * easeOut(progress), 0, 1), barHeight, 999, accent);
      ctx.fillStyle = '#173630';
      ctx.fillText(`${Math.round(values[index] * 100)}`, x + width + 18, top + 42);
    });
    ctx.restore();
  }

  function drawProductCard(x, y, width, height, image, name, price, highlight) {
    drawGlassCard(x, y, width, height, 28);
    fillRoundRect(ctx, x + 18, y + 18, width - 36, height * 0.55, 22, '#faf1e7');
    if (image) {
      const boxW = width - 60;
      const boxH = height * 0.48;
      const scale = Math.min(boxW / image.width, boxH / image.height);
      const drawW = image.width * scale;
      const drawH = image.height * scale;
      ctx.drawImage(image, x + (width - drawW) / 2, y + 30 + (boxH - drawH) / 2, drawW, drawH);
    }
    ctx.save();
    ctx.fillStyle = '#173630';
    ctx.font = '700 22px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText(name, x + 20, y + height - 56);
    ctx.fillStyle = highlight ? '#0f8f6f' : 'rgba(23,54,48,0.7)';
    ctx.font = '700 18px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText(price, x + 20, y + height - 26);
    ctx.restore();
  }

  function drawLogoTile(x, y, width, height, image, label, emphasis) {
    drawGlassCard(x, y, width, height, 22);
    if (image) {
      const scale = Math.min((width - 28) / image.width, 38 / image.height);
      const drawW = image.width * scale;
      const drawH = image.height * scale;
      ctx.drawImage(image, x + (width - drawW) / 2, y + 18, drawW, drawH);
    }
    ctx.save();
    ctx.fillStyle = emphasis ? '#0f8f6f' : 'rgba(23,54,48,0.72)';
    ctx.font = '600 15px "Avenir Next", "PingFang SC", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(label, x + width / 2, y + height - 18);
    ctx.restore();
  }

  function drawRing(cx, cy, radius, progress, label, value) {
    ctx.save();
    ctx.lineWidth = 18;
    ctx.strokeStyle = 'rgba(23,54,48,0.12)';
    ctx.beginPath();
    ctx.arc(cx, cy, radius, -Math.PI / 2, Math.PI * 1.5);
    ctx.stroke();

    ctx.strokeStyle = '#0f8f6f';
    ctx.beginPath();
    ctx.arc(cx, cy, radius, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * clamp(progress, 0, 1));
    ctx.stroke();

    ctx.fillStyle = '#173630';
    ctx.font = '700 30px "Avenir Next", "PingFang SC", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(value, cx, cy + 6);
    ctx.fillStyle = 'rgba(23,54,48,0.64)';
    ctx.font = '600 16px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText(label, cx, cy + 34);
    ctx.restore();
  }

  function drawSubtitle(scene) {
    const subtitle = scene.subtitle || scene.narration || '';
    const lines = wrapText(subtitle, WIDTH - 240, '600 30px "PingFang SC", "Microsoft YaHei", sans-serif');
    const lineHeight = 38;
    const boxHeight = 46 + lines.length * lineHeight;
    const boxY = HEIGHT - boxHeight - 38;
    fillRoundRect(ctx, 80, boxY, WIDTH - 160, boxHeight, 26, 'rgba(17, 31, 28, 0.66)');
    strokeRoundRect(ctx, 80, boxY, WIDTH - 160, boxHeight, 26, 'rgba(255,255,255,0.1)', 1);
    ctx.save();
    ctx.font = '600 30px "PingFang SC", "Microsoft YaHei", sans-serif';
    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'center';
    lines.forEach((line, index) => {
      ctx.fillText(line, WIDTH / 2, boxY + 40 + index * lineHeight);
    });
    ctx.restore();
  }

  function drawSceneIntro(progress) {
    drawPhotoPanel(0, 0, WIDTH, HEIGHT, state.assets.get('portraitWindow'), {
      radius: 0,
      focusX: 0.12,
      focusY: 0.46,
      zoom: lerp(1.14, 1.04, ease(progress)),
      overlayFrom: 'rgba(15, 28, 26, 0.78)',
      overlayTo: 'rgba(15, 28, 26, 0.16)',
      highlight: 'rgba(245,123,66,0.16)',
      border: 'rgba(255,255,255,0.06)',
      shadow: 'rgba(0,0,0,0)',
    });

    drawLogoMark(170, 152, progress);

    ctx.save();
    ctx.globalAlpha = easeOut(progress);
    ctx.fillStyle = '#ffffff';
    ctx.font = '700 82px "Iowan Old Style", "Georgia", "STSong", serif';
    ctx.fillText('MediSlim', 86, 294);
    ctx.font = '600 22px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillStyle = 'rgba(255,255,255,0.76)';
    ctx.fillText('AI 体质评估 · 医审承接 · 订阅复购', 90, 336);
    ctx.font = '500 28px "Avenir Next", "PingFang SC", sans-serif';
    drawTextBlock('把减重、睡眠和皮肤管理，放回一条可持续的生活轨道。', 88, 404, 460, ctx.font, 'rgba(255,255,255,0.94)', 40);
    ctx.restore();

    ['减重优先级', '睡眠修复度', '皮肤波动值'].forEach((label, index) => {
      drawBadge(label, 88 + index * 136, 504, 118 + (index === 2 ? 16 : 0));
    });

    drawGlassCard(850, 420, 252, 108, 28);
    ctx.save();
    ctx.fillStyle = '#173630';
    ctx.font = '700 20px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText('成片 Demo', 878, 458);
    ctx.fillStyle = 'rgba(23,54,48,0.68)';
    ctx.font = '500 16px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText('半真实镜头 + 数据可视化', 878, 490);
    ctx.fillText('把评估、履约和复购讲成一条连续体验。', 878, 516);
    ctx.restore();
  }

  function drawSceneImbalance(progress) {
    drawPhotoPanel(664, 112, 486, 472, state.assets.get('portraitWindow'), {
      radius: 42,
      focusX: 0.14,
      focusY: 0.46,
      zoom: lerp(1.08, 1.02, ease(progress)),
      overlayFrom: 'rgba(18, 32, 29, 0.22)',
      overlayTo: 'rgba(18, 32, 29, 0.48)',
      highlight: 'rgba(245,123,66,0.12)',
      label: '真实生活切片',
      labelWidth: 126,
    });

    drawSignalChip(694, 146, '睡眠评分', '49 / 100', '#f57b42');
    drawSignalChip(970, 210, '体重波动', '+6.8 kg', '#0f8f6f');
    drawSignalChip(716, 424, '皮肤状态', '敏感反复', '#173630');

    drawGlassCard(878, 456, 244, 96, 24);
    drawLineChart(900, 482, 196, 44, [63, 58, 52, 49], progress, '#f57b42', 'rgba(245,123,66,0.14)');
    ctx.save();
    ctx.fillStyle = '#173630';
    ctx.font = '700 16px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText('夜间修复指数', 900, 474);
    ctx.restore();
  }

  function drawSceneScan(progress) {
    const x = 748;
    const y = 96;
    drawPhoneShell(x, y, 370, 534);
    drawRadar(x + 186, y + 204, 118, progress);

    fillRoundRect(ctx, x + 38, y + 334, 294, 86, 22, 'rgba(255,255,255,0.08)');
    ctx.save();
    ctx.fillStyle = '#ffffff';
    ctx.font = '700 24px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText('AI 评估中', x + 62, y + 368);
    ctx.fillStyle = 'rgba(255,255,255,0.72)';
    ctx.font = '500 16px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText('体重 / 睡眠 / 皮肤 / 九型体质', x + 62, y + 396);
    ctx.restore();

    drawBars(x + 54, y + 440, 214, ['气郁倾向', '湿热指数', '睡眠修复'], [0.72, 0.64, 0.48], progress, 'rgba(245,123,66,0.92)');
  }

  function drawSceneData(progress) {
    drawGlassCard(676, 112, 510, 454, 34);
    ctx.save();
    ctx.fillStyle = '#173630';
    ctx.font = '700 24px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText('评估后的第一张趋势图', 710, 156);
    ctx.fillStyle = 'rgba(23,54,48,0.64)';
    ctx.font = '500 16px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText('不是泛泛建议，而是把优先级和变化幅度看成一张图。', 710, 184);
    ctx.restore();

    drawLineChart(712, 214, 442, 160, [74, 73.6, 72.5, 71.8, 70.4, 69.6, 68.8], progress, '#0f8f6f', 'rgba(15,143,111,0.16)');
    drawBars(712, 410, 300, ['睡眠修复', '皮肤炎症', '复购意愿'], [0.78, 0.54, 0.86], progress, 'rgba(245,123,66,0.9)');

    fillRoundRect(ctx, 1032, 410, 120, 116, 22, 'rgba(247, 241, 232, 0.94)');
    ctx.save();
    ctx.fillStyle = '#0f8f6f';
    ctx.font = '700 34px "Avenir Next", "PingFang SC", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('-5.2', 1092, 460);
    ctx.fillStyle = 'rgba(23,54,48,0.72)';
    ctx.font = '600 16px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText('阶段减重 / kg', 1092, 496);
    ctx.restore();
  }

  function drawScenePlan(progress) {
    const products = [
      { key: 'glp1', name: 'GLP-1 减重', price: '¥399 起' },
      { key: 'sleep', name: '助眠调理', price: '¥199 起' },
      { key: 'skin', name: '皮肤管理', price: '¥299 起' },
    ];

    products.forEach((item, index) => {
      const cardWidth = index === 0 ? 308 : 248;
      const cardHeight = index === 0 ? 280 : 236;
      const x = index === 0 ? 656 : 990;
      const y = index === 0 ? 116 : 126 + (index - 1) * 250;
      drawProductCard(
        x,
        y + lerp(24, 0, ease(progress + index * 0.08)),
        cardWidth,
        cardHeight,
        state.assets.get(item.key),
        item.name,
        item.price,
        index === 0
      );
    });

    drawGlassCard(678, 420, 278, 142, 28);
    ctx.save();
    ctx.fillStyle = '#173630';
    ctx.font = '700 22px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText('推荐顺序', 706, 458);
    ctx.font = '500 16px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillStyle = 'rgba(23,54,48,0.64)';
    ctx.fillText('减重先行，睡眠同步修复，皮肤放到第二阶段。', 706, 492);
    ctx.fillStyle = '#0f8f6f';
    ctx.font = '700 18px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText('先月体验，再进订阅。', 706, 528);
    ctx.restore();
  }

  function drawSceneNetwork(progress) {
    const nodes = [
      { x: 712, y: 218, label: 'AI 评估' },
      { x: 890, y: 164, label: '合作医院' },
      { x: 1084, y: 240, label: '合规药房' },
      { x: 1010, y: 456, label: '物流配送' },
      { x: 776, y: 488, label: '复购跟踪' },
    ];

    ctx.save();
    ctx.strokeStyle = 'rgba(15,143,111,0.32)';
    ctx.lineWidth = 4;
    ctx.setLineDash([10, 12]);
    ctx.beginPath();
    ctx.moveTo(nodes[0].x, nodes[0].y);
    nodes.slice(1).forEach((node) => ctx.lineTo(node.x, node.y));
    ctx.stroke();
    ctx.restore();

    nodes.forEach((node, index) => {
      fillRoundRect(ctx, node.x - 88, node.y - 34, 176, 68, 24, 'rgba(255,255,255,0.74)');
      ctx.beginPath();
      ctx.arc(node.x - 60, node.y, 10, 0, Math.PI * 2);
      ctx.fillStyle = index < 4 ? '#0f8f6f' : 'rgba(245,123,66,0.92)';
      ctx.fill();
      ctx.save();
      ctx.fillStyle = '#173630';
      ctx.font = '700 18px "Avenir Next", "PingFang SC", sans-serif';
      ctx.fillText(node.label, node.x - 36, node.y + 6);
      ctx.restore();
    });

    const logos = [
      { key: 'hospitalJd', label: '京东健康', x: 670, y: 354, emphasis: true },
      { key: 'hospitalWe', label: '微医', x: 870, y: 354, emphasis: true },
      { key: 'pharmacyDs', label: '大参林', x: 670, y: 556, emphasis: false },
      { key: 'pharmacyYf', label: '益丰', x: 870, y: 556, emphasis: false },
    ];

    logos.forEach((logo) => {
      drawLogoTile(logo.x, logo.y, 172, 112, state.assets.get(logo.key), logo.label, logo.emphasis);
    });
  }

  function drawSceneOutcome(progress) {
    drawPhotoPanel(640, 108, 520, 488, state.assets.get('portraitPhone'), {
      radius: 46,
      focusX: 0.56,
      focusY: 0.24,
      zoom: lerp(1.12, 1.03, ease(progress)),
      overlayFrom: 'rgba(18, 32, 29, 0.18)',
      overlayTo: 'rgba(18, 32, 29, 0.42)',
      highlight: 'rgba(255,255,255,0.18)',
      label: '完成第 2 月',
      labelWidth: 118,
    });

    drawRing(1044, 226, 76, lerp(0.2, 0.84, ease(progress)), '睡眠回升', '84');

    drawGlassCard(680, 440, 444, 138, 28);
    drawLineChart(706, 476, 316, 72, [72, 71.4, 70.9, 70.2, 69.8, 69.5, 69.2], progress, '#0f8f6f', 'rgba(15,143,111,0.14)');
    fillRoundRect(ctx, 1036, 470, 64, 36, 18, 'rgba(15,143,111,0.12)');
    ctx.save();
    ctx.fillStyle = '#173630';
    ctx.font = '700 24px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText('不是更激进，而是重新稳定。', 706, 466);
    ctx.fillStyle = '#0f8f6f';
    ctx.font = '700 18px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText('复购中', 1050, 494);
    ctx.fillStyle = 'rgba(23,54,48,0.64)';
    ctx.font = '500 16px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText('体重、睡眠和执行力开始一起回到生活里。', 706, 566);
    ctx.fillText('下一次提醒不是催促，而是更平顺的续接。', 706, 588);
    ctx.restore();
  }

  function drawSceneOutro(progress) {
    const outroProgress = easeOut(progress);
    drawPhotoPanel(0, 0, WIDTH, HEIGHT, state.assets.get('portraitPhone'), {
      radius: 0,
      focusX: 0.64,
      focusY: 0.3,
      zoom: lerp(1.16, 1.06, outroProgress),
      overlayFrom: 'rgba(12, 24, 22, 0.86)',
      overlayTo: 'rgba(12, 24, 22, 0.72)',
      highlight: 'rgba(15,143,111,0.12)',
      border: 'rgba(255,255,255,0.05)',
      shadow: 'rgba(0,0,0,0)',
    });

    ctx.save();
    ctx.globalAlpha = lerp(0.2, 1, outroProgress);
    ctx.translate(WIDTH / 2, HEIGHT / 2 - 86);
    drawLogoMark(0, 0, outroProgress, {
      accentA: '#17a37e',
      accentB: '#f2a16f',
    });
    ctx.restore();

    ctx.save();
    ctx.textAlign = 'center';
    ctx.globalAlpha = outroProgress;
    ctx.fillStyle = '#ffffff';
    ctx.font = '700 84px "Iowan Old Style", "Georgia", "STSong", serif';
    ctx.fillText('MediSlim', WIDTH / 2, HEIGHT / 2 + 72);
    ctx.fillStyle = 'rgba(255,255,255,0.74)';
    ctx.font = '600 24px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText('从评估到履约，把健康管理做得更稳一点。', WIDTH / 2, HEIGHT / 2 + 116);
    ctx.fillStyle = 'rgba(255,255,255,0.6)';
    ctx.font = '500 18px "Avenir Next", "PingFang SC", sans-serif';
    ctx.fillText('medislim.cloud', WIDTH / 2, HEIGHT / 2 + 156);
    ctx.restore();
  }

  function renderAt(seconds, options) {
    const renderOptions = options || {};
    if (!state.manifest) {
      return;
    }

    const time = clamp(seconds, 0, state.manifest.duration);
    const sceneIndex = state.manifest.scenes.findIndex((scene) => time >= scene.start && time < scene.end);
    const activeIndex = sceneIndex === -1 ? state.manifest.scenes.length - 1 : sceneIndex;
    const scene = state.manifest.scenes[activeIndex];
    const localTime = time - scene.start;
    const progress = scene.duration ? clamp(localTime / scene.duration, 0, 1) : 0;
    const palette = scenePalettes[scene.id] || scenePalettes.imbalance;
    const cinematicScene = scene.id === 'intro' || scene.id === 'outro';

    ctx.clearRect(0, 0, WIDTH, HEIGHT);
    drawGradientBackground(palette);
    if (!cinematicScene) {
      drawTopChrome(scene, activeIndex, time);
    }

    if (scene.id === 'intro') {
      drawSceneIntro(progress);
    } else if (scene.id === 'imbalance') {
      drawSceneImbalance(progress);
    } else if (scene.id === 'scan') {
      drawSceneScan(progress);
    } else if (scene.id === 'data') {
      drawSceneData(progress);
    } else if (scene.id === 'plan') {
      drawScenePlan(progress);
    } else if (scene.id === 'network') {
      drawSceneNetwork(progress);
    } else if (scene.id === 'outcome') {
      drawSceneOutcome(progress);
    } else if (scene.id === 'outro') {
      drawSceneOutro(progress);
    }

    drawSubtitle(scene);

    if (!renderOptions.silent) {
      state.currentTime = time;
      timeNode.textContent = formatTime(time);
      sceneIndexNode.textContent = String(activeIndex + 1).padStart(2, '0');
      currentSubtitle.innerHTML = (scene.subtitle || '').replace(/\n/g, '<br>');
      if (state.lastSceneId !== scene.id) {
        state.lastSceneId = scene.id;
        state.sceneNodes.forEach((node, index) => {
          node.classList.toggle('is-active', index === activeIndex);
        });
      }
    }
  }

  function tick() {
    if (!state.playing) {
      return;
    }

    const sourceTime = state.audioEnabled ? voiceover.currentTime : (performance.now() - state.startedAt) / 1000;
    renderAt(sourceTime);
    if (sourceTime >= state.manifest.duration) {
      pause(true);
      return;
    }
    state.rafId = window.requestAnimationFrame(tick);
  }

  function syncButtons() {
    playButton.textContent = state.playing ? '暂停成片' : '播放成片';
    audioButton.textContent = state.audioEnabled ? '关闭中文旁白' : '开启中文旁白';
  }

  function pause(ended) {
    state.playing = false;
    if (state.rafId) {
      window.cancelAnimationFrame(state.rafId);
      state.rafId = 0;
    }
    if (!voiceover.paused) {
      voiceover.pause();
    }
    if (ended) {
      state.currentTime = state.manifest.duration;
    } else if (!state.audioEnabled) {
      state.currentTime = clamp((performance.now() - state.startedAt) / 1000, 0, state.manifest.duration);
    } else {
      state.currentTime = clamp(voiceover.currentTime, 0, state.manifest.duration);
    }
    renderAt(state.currentTime);
    syncButtons();
  }

  async function play() {
    await state.ready;
    if (state.playing) {
      pause(false);
      return;
    }
    state.playing = true;
    state.startedAt = performance.now() - state.currentTime * 1000;
    if (state.audioEnabled) {
      voiceover.currentTime = state.currentTime;
      try {
        await voiceover.play();
      } catch (error) {
        state.audioEnabled = false;
      }
    }
    syncButtons();
    tick();
  }

  async function toggleAudio() {
    await state.ready;
    state.audioEnabled = !state.audioEnabled;
    if (!state.audioEnabled) {
      if (!voiceover.paused) {
        voiceover.pause();
      }
    } else if (state.playing) {
      voiceover.currentTime = state.currentTime;
      try {
        await voiceover.play();
      } catch (error) {
        state.audioEnabled = false;
      }
    }
    syncButtons();
  }

  function restart() {
    const wasPlaying = state.playing;
    pause(false);
    state.currentTime = 0;
    voiceover.currentTime = 0;
    renderAt(0);
    if (wasPlaying) {
      play().catch(() => {});
    }
  }

  function buildSceneList() {
    sceneList.innerHTML = state.manifest.scenes.map((scene, index) => `
      <article class="film-scene-item${index === 0 ? ' is-active' : ''}" data-scene-index="${index}">
        <div class="film-scene-num">${String(index + 1).padStart(2, '0')}</div>
        <div class="film-scene-copy">
          <strong>${scene.title}</strong>
          <span>${scene.summary}</span>
        </div>
        <div class="film-scene-time">${formatTime(scene.duration)}</div>
      </article>
    `).join('');

    state.sceneNodes = Array.from(sceneList.querySelectorAll('.film-scene-item'));
    state.sceneNodes.forEach((node, index) => {
      node.addEventListener('click', () => {
        const scene = state.manifest.scenes[index];
        const wasPlaying = state.playing;
        pause(false);
        state.currentTime = scene.start;
        voiceover.currentTime = state.currentTime;
        renderAt(state.currentTime);
        if (wasPlaying) {
          play().catch(() => {});
        }
      });
    });
  }

  async function loadImage(url) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      image.decoding = 'async';
      image.onload = () => resolve(image);
      image.onerror = reject;
      image.src = url;
    });
  }

  async function ensureAudioBuffer() {
    if (!state.audioArrayBuffer) {
      state.audioArrayBuffer = await window.fetch(voiceoverUrl).then((response) => response.arrayBuffer());
    }
    return state.audioArrayBuffer;
  }

  async function ensureReady() {
    if (state.ready) {
      return state.ready;
    }

    state.ready = (async () => {
      const manifest = await window.fetch('/static/media/demo/medislim-film-manifest.json').then((response) => response.json());
      state.manifest = manifest;
      const assets = await Promise.all(Object.entries(assetUrls).map(async ([key, url]) => [key, await loadImage(url)]));
      assets.forEach(([key, image]) => {
        state.assets.set(key, image);
      });
      await ensureAudioBuffer();
      buildSceneList();
      renderAt(0);
      syncButtons();
    })();

    return state.ready;
  }

  function mediaRecorderType() {
    const candidates = [
      'video/webm;codecs=vp9,opus',
      'video/webm;codecs=vp8,opus',
      'video/webm',
    ];
    return candidates.find((candidate) => window.MediaRecorder && window.MediaRecorder.isTypeSupported(candidate)) || 'video/webm';
  }

  async function exportBase64() {
    await ensureReady();
    pause(false);
    renderAt(0, { silent: true });

    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    const audioContext = new AudioCtx();
    await audioContext.resume();
    const arrayBuffer = await ensureAudioBuffer();
    const decoded = await audioContext.decodeAudioData(arrayBuffer.slice(0));
    const destination = audioContext.createMediaStreamDestination();
    const source = audioContext.createBufferSource();
    source.buffer = decoded;
    source.connect(destination);

    const stream = canvas.captureStream(FPS);
    const mixedStream = new MediaStream([
      ...stream.getVideoTracks(),
      ...destination.stream.getAudioTracks(),
    ]);
    const mimeType = mediaRecorderType();
    const recorder = new window.MediaRecorder(mixedStream, {
      mimeType,
      videoBitsPerSecond: 5600000,
      audioBitsPerSecond: 160000,
    });
    const chunks = [];

    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size) {
        chunks.push(event.data);
      }
    };

    const blobPromise = new Promise((resolve) => {
      recorder.onstop = () => resolve(new Blob(chunks, { type: mimeType }));
    });

    recorder.start(1000);
    source.start(audioContext.currentTime + 0.05);
    await wait(70);

    const renderStart = performance.now();
    while ((performance.now() - renderStart) / 1000 < state.manifest.duration) {
      const elapsed = (performance.now() - renderStart) / 1000;
      renderAt(Math.min(state.manifest.duration, elapsed), { silent: true });
      await wait(1000 / FPS);
    }
    renderAt(state.manifest.duration, { silent: true });

    recorder.stop();
    const blob = await blobPromise;
    source.disconnect();
    await audioContext.close();
    const base64 = await new Promise((resolve) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const result = String(reader.result);
        const marker = 'base64,';
        resolve(result.slice(result.indexOf(marker) + marker.length));
      };
      reader.readAsDataURL(blob);
    });

    renderAt(0);
    return {
      base64,
      mimeType,
      duration: state.manifest.duration,
      width: WIDTH,
      height: HEIGHT,
    };
  }

  async function exportPosterBase64(time) {
    await ensureReady();
    const imbalanceScene = state.manifest.scenes.find((scene) => scene.id === 'imbalance');
    const targetTime = typeof time === 'number' ? time : (imbalanceScene ? imbalanceScene.start : (state.manifest.scenes[1]?.start || 0)) + 1.1;
    renderAt(targetTime, { silent: true });
    return canvas.toDataURL('image/png').split(',')[1];
  }

  window.MediSlimFilm = {
    ready: ensureReady,
    play,
    pause: () => pause(false),
    restart,
    toggleAudio,
    renderAt,
    exportBase64,
    exportPosterBase64,
    seek(time) {
      state.currentTime = clamp(time, 0, state.manifest ? state.manifest.duration : 0);
      voiceover.currentTime = state.currentTime;
      renderAt(state.currentTime);
    },
    getState() {
      return {
        playing: state.playing,
        currentTime: state.currentTime,
        duration: state.manifest ? state.manifest.duration : 0,
      };
    },
  };

  playButton.addEventListener('click', () => {
    play().catch(() => {});
  });
  audioButton.addEventListener('click', () => {
    toggleAudio().catch(() => {});
  });
  restartButton.addEventListener('click', () => restart());

  ensureReady().then(() => {
    const autoplay = params.get('autoplay') === '1';
    if (autoplay && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      play().catch(() => {});
    }
  }).catch(() => {
    if (currentSubtitle) {
      currentSubtitle.textContent = '成片脚本加载失败，请检查导出素材。';
    }
  });
})();
