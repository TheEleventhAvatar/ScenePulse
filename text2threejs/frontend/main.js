/**
 * Text → Three.js — application wiring.
 *
 * Pipeline: prompt → (mock LLM / validated spec JSON) → buildScene() →
 * interactive viewport → data-driven timeline → natural-language patches.
 *
 * The browser never executes LLM-generated JavaScript. It interprets
 * validated TextSceneSpec data through deterministic builders only.
 */

import * as THREE from 'three';
import { Viewport } from './viewport.js';
import { Timeline } from './timeline.js';
import { buildScene, makeMaterial } from './scene_builder.js';
import { patchSpec } from './patcher.js';
import { createShaderTicker } from './shaders.js';
import { PerfStats } from './stats.js';

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------

const els = {
  promptInput: document.getElementById('promptInput'),
  generateBtn: document.getElementById('generateBtn'),
  editBtn: document.getElementById('editBtn'),
  demoList: document.getElementById('demoList'),
  treeRoot: document.getElementById('treeRoot'),
  inspectorBody: document.getElementById('inspectorBody'),
  playBtn: document.getElementById('playBtn'),
  timeCurrent: document.getElementById('timeCurrent'),
  timeDuration: document.getElementById('timeDuration'),
  speedSelect: document.getElementById('speedSelect'),
  clipCount: document.getElementById('clipCount'),
  timelineCanvas: document.getElementById('timelineCanvas'),
  hint: document.getElementById('viewportHint'),
  toast: document.getElementById('toast'),
  providerLabel: document.getElementById('providerLabel'),
};

const viewport = new Viewport(document.getElementById('viewport'));
const timeline = new Timeline();
const shaderTicker = createShaderTicker();
const stats = new PerfStats({
  fpsEl: document.getElementById('statFps'),
  frameTimeEl: document.getElementById('statFrameTime'),
  drawCallsEl: document.getElementById('statDrawCalls'),
  trianglesEl: document.getElementById('statTriangles'),
  objectsEl: document.getElementById('statObjects'),
});

let demoData = null;          // { key: { prompt, provider, spec } }
let currentSpec = null;       // active TextSceneSpec (patched in place)
let currentKey = null;        // active demo key
let selectedId = null;

// ---------------------------------------------------------------------------
// Frame loop (single rAF owned by Viewport)
// ---------------------------------------------------------------------------

viewport.onChange((event, payload) => {
  if (event === 'frame') {
    timeline.tick(payload.delta);
    shaderTicker.tick(payload.elapsed);
    stats.update(viewport.renderer, payload.delta);
    updateTimeDisplay();
  } else if (event === 'selection') {
    onSelectionChanged(payload);
  } else if (event === 'transform') {
    refreshInspectorValues();
  }
});

// ---------------------------------------------------------------------------
// Demo data + chips
// ---------------------------------------------------------------------------

async function loadDemoData() {
  const response = await fetch('./demo_specs.json');
  if (!response.ok) throw new Error(`demo_specs.json ${response.status}`);
  demoData = await response.json();

  const titles = {
    'cinematic-product-reveal': ['Cinematic Product Reveal', 'Futuristic watch · rim light · push-in'],
    'neon-cyberpunk': ['Neon Cyberpunk City', 'Glowing buildings · fog · drone'],
    'abstract-motion': ['Abstract Motion Graphics', 'Floating shapes · looping easing'],
    'futuristic-hud': ['Futuristic HUD', 'Holographic shader · rotating core'],
    'luxury-product': ['Minimal Luxury Product', 'Perfume bottle · studio softbox'],
  };

  for (const [key, entry] of Object.entries(demoData)) {
    const [name, desc] = titles[key] ?? [key, entry.prompt];
    const chip = document.createElement('button');
    chip.className = 'demo-chip';
    chip.dataset.key = key;
    chip.innerHTML = `<div class="name"></div><div class="desc"></div>`;
    chip.querySelector('.name').textContent = name;
    chip.querySelector('.desc').textContent = desc;
    chip.addEventListener('click', () => {
      els.promptInput.value = entry.prompt;
      generateScene(key);
    });
    els.demoList.appendChild(chip);
  }
}

/** Mirror of MockLLM._match_key so free-typed prompts resolve deterministically. */
function matchDemoKey(prompt) {
  const lowered = prompt.toLowerCase();
  const rules = [
    ['watch', 'cinematic-product-reveal'],
    ['product reveal', 'cinematic-product-reveal'],
    ['cinematic', 'cinematic-product-reveal'],
    ['cyberpunk', 'neon-cyberpunk'],
    ['neon', 'neon-cyberpunk'],
    ['abstract', 'abstract-motion'],
    ['motion', 'abstract-motion'],
    ['hud', 'futuristic-hud'],
    ['holographic', 'futuristic-hud'],
    ['luxury', 'luxury-product'],
    ['perfume', 'luxury-product'],
    ['bottle', 'luxury-product'],
  ];
  for (const [keyword, key] of rules) {
    if (lowered.includes(keyword)) return key;
  }
  return 'cinematic-product-reveal';
}

// ---------------------------------------------------------------------------
// Scene generation / replacement
// ---------------------------------------------------------------------------

function generateScene(key) {
  const entry = demoData[key];
  if (!entry) return;
  currentKey = key;
  loadSpec(structuredClone(entry.spec));
  markActiveChip(key);
  showToast(`Generated “${entry.spec.scene?.name ?? key}”`);
}

/** Build a Three.js scene from a validated spec and swap it into the viewport. */
function loadSpec(spec) {
  currentSpec = spec;

  // Full teardown of the previous scene's GPU resources before replacement.
  shaderTicker.dispose();
  const { scene, camera } = buildScene(spec, { renderer: viewport.renderer });

  // Register custom-shader materials for per-frame uniform updates.
  scene.traverse((child) => {
    if (child.material && typeof child.material.tick === 'function') {
      shaderTicker.register(child.material);
    }
  });

  viewport.setScene(scene, camera);
  timeline.load(scene.userData.textToThree.animationTargets);

  let objectCount = 0;
  scene.traverse(() => { objectCount++; });
  stats.setObjectCount(objectCount);

  rebuildTree();
  updateClipCount();
  updateTimeDisplay();
  els.editBtn.disabled = false;
  showHint();
  timeline.play();
}

// ---------------------------------------------------------------------------
// Natural-language editing (patch, don't regenerate)
// ---------------------------------------------------------------------------

function applyEdit(instruction) {
  if (!currentSpec) return;
  const { spec, changed } = patchSpec(currentSpec, instruction);
  if (changed.length === 0) {
    showToast('No matching edit found — try "rotate", "camera closer", "glossy black"…');
    return;
  }

  currentSpec = spec;
  const meta = viewport.scene.userData.textToThree;

  if (changed.includes('animations')) {
    // Rebuild only the timeline; the scene graph is untouched.
    meta.animationTargets = rebuildAnimationTargets(spec, meta);
    timeline.load(meta.animationTargets);
    updateClipCount();
  }

  if (changed.includes('materials')) {
    applyMaterialPatches(spec, meta);
  }

  if (changed.includes('camera')) {
    const cam = spec.camera;
    const target = cam.target ?? [0, 0, 0];
    meta.cameraHome.position.set(cam.position[0], cam.position[1], cam.position[2]);
    meta.cameraHome.target.set(target[0], target[1], target[2]);
    viewport.flyTo(meta.cameraHome.position, meta.cameraHome.target);
  }

  showToast(`Scene updated: ${changed.join(', ')}`);
}

/**
 * Recompute animation targets from a patched spec against the existing scene
 * graph — mirrors scene_builder.collectAnimationTargets without rebuilding.
 */
function rebuildAnimationTargets(spec, meta) {
  const targets = [];
  for (const anim of spec.animations ?? []) {
    const node = meta.objectsById[anim.object];
    if (!node) continue;
    targets.push({
      id: anim.id,
      objectId: anim.object,
      property: anim.property,
      from: anim.from,
      to: anim.to,
      duration: anim.duration ?? 1,
      delay: anim.delay ?? 0,
      easing: anim.easing ?? 'linear',
      loop: anim.loop === true,
      yoyo: anim.yoyo === true,
      node,
      mesh: meta.meshesById[anim.object] ?? null,
    });
  }
  return targets;
}

/** Update existing material instances in place; swap only if the model changed. */
function applyMaterialPatches(spec, meta) {
  for (const matSpec of spec.materials ?? []) {
    if (!matSpec?.id) continue;
    const existing = meta.materialsById[matSpec.id];
    const wantsCustom = matSpec.shaderModel === 'fresnel-rim' || matSpec.shaderModel === 'hologram';
    const isCustom = existing && (existing.isFresnelRimMaterial || existing.isHologramMaterial);

    if (!existing || (wantsCustom !== Boolean(isCustom))) {
      // Model change requires a new material — swap it onto dependent meshes.
      const replacement = makeMaterial(matSpec);
      if (typeof replacement.tick === 'function') shaderTicker.register(replacement);
      for (const mesh of Object.values(meta.meshesById)) {
        if (mesh.material === existing || mesh.userData.materialId === matSpec.id) {
          disposeMaterial(mesh.material);
          mesh.material = replacement;
        }
      }
      meta.materialsById[matSpec.id] = replacement;
      continue;
    }

    // In-place property update — no reallocation, no shader recompile.
    if (matSpec.color && existing.color) existing.color.set(matSpec.color);
    if (matSpec.emissive && existing.emissive) existing.emissive.set(matSpec.emissive);
    if (typeof matSpec.roughness === 'number' && 'roughness' in existing) existing.roughness = matSpec.roughness;
    if (typeof matSpec.metalness === 'number' && 'metalness' in existing) existing.metalness = matSpec.metalness;
    if (typeof matSpec.opacity === 'number') {
      existing.opacity = matSpec.opacity;
      existing.transparent = existing.transparent || matSpec.opacity < 1;
    }
    if (typeof matSpec.emissiveIntensity === 'number') existing.emissiveIntensity = matSpec.emissiveIntensity;
    if (existing.uniforms?.uBaseColor && matSpec.color) existing.uniforms.uBaseColor.value.set(matSpec.color);
    if (existing.uniforms?.uRimColor && matSpec.emissive) existing.uniforms.uRimColor.value.set(matSpec.emissive);
    if (existing.uniforms?.uOpacity && typeof matSpec.opacity === 'number') {
      existing.uniforms.uOpacity.value = matSpec.opacity;
    }
  }
  refreshInspectorValues();
}

function disposeMaterial(material) {
  if (!material) return;
  shaderTicker.unregister(material);
  material.dispose();
}

// ---------------------------------------------------------------------------
// Hierarchy tree
// ---------------------------------------------------------------------------

function rebuildTree() {
  els.treeRoot.innerHTML = '';
  const objects = currentSpec.objects ?? [];
  const childrenOf = new Map();
  const roots = [];
  for (const obj of objects) {
    if (obj.parent && objects.some((o) => o.id === obj.parent)) {
      if (!childrenOf.has(obj.parent)) childrenOf.set(obj.parent, []);
      childrenOf.get(obj.parent).push(obj);
    } else {
      roots.push(obj);
    }
  }

  const append = (obj, depth) => {
    const item = document.createElement('div');
    item.className = 'tree-item';
    item.dataset.id = obj.id;
    item.style.paddingLeft = `${8 + depth * 16}px`;
    const icon = obj.type === 'group' ? '▢' : '◆';
    item.innerHTML = `<span>${icon}</span><span class="name"></span><span class="type-tag"></span>`;
    item.querySelector('.name').textContent = obj.name ?? obj.id;
    item.querySelector('.type-tag').textContent = obj.type;
    item.addEventListener('click', () => viewport.select(obj.id));
    els.treeRoot.appendChild(item);
    for (const child of childrenOf.get(obj.id) ?? []) append(child, depth + 1);
  };
  for (const root of roots) append(root, 0);
}

function markActiveChip(key) {
  for (const chip of els.demoList.querySelectorAll('.demo-chip')) {
    chip.classList.toggle('active', chip.dataset.key === key);
  }
}

// ---------------------------------------------------------------------------
// Inspector
// ---------------------------------------------------------------------------

function onSelectionChanged(objectId) {
  selectedId = objectId;
  for (const item of els.treeRoot.querySelectorAll('.tree-item')) {
    item.classList.toggle('selected', item.dataset.id === objectId);
  }
  renderInspector();
}

function renderInspector() {
  const body = els.inspectorBody;
  if (!selectedId || !currentSpec) {
    body.innerHTML = '<div class="inspector-empty">Nothing selected.</div>';
    return;
  }
  const obj = currentSpec.objects.find((o) => o.id === selectedId);
  if (!obj) {
    body.innerHTML = '<div class="inspector-empty">Object not in spec.</div>';
    return;
  }
  const matSpec = obj.material
    ? currentSpec.materials?.find((m) => m.id === obj.material)
    : null;

  body.innerHTML = `
    <div class="inspector-row"><span class="label">id</span><span class="value">${escapeHtml(obj.id)}</span></div>
    <div class="inspector-row"><span class="label">type</span><span class="value">${escapeHtml(obj.type)}</span></div>
    <div class="inspector-row"><span class="label">parent</span><span class="value">${escapeHtml(obj.parent ?? '—')}</span></div>
    <div class="inspector-row"><span class="label">position</span><span class="value" id="inspPos"></span></div>
    <div class="inspector-row"><span class="label">rotation</span><span class="value" id="inspRot"></span></div>
    <div class="inspector-row"><span class="label">scale</span><span class="value" id="inspScale"></span></div>
    ${matSpec ? `
      <div class="inspector-row"><span class="label">material</span>
        <span class="value"><span class="color-swatch" style="background:${escapeHtml(matSpec.color ?? '#888')}"></span>${escapeHtml(matSpec.id)}</span></div>
      <div class="inspector-row"><span class="label">roughness</span><span class="value">${fmtNum(matSpec.roughness)}</span></div>
      <div class="inspector-row"><span class="label">metalness</span><span class="value">${fmtNum(matSpec.metalness)}</span></div>
      ${matSpec.shaderModel ? `<div class="inspector-row"><span class="label">shader</span><span class="value">${escapeHtml(matSpec.shaderModel)}</span></div>` : ''}
    ` : ''}
  `;
  refreshInspectorValues();
}

/** Live-update numeric fields without re-rendering the whole inspector. */
function refreshInspectorValues() {
  if (!selectedId) return;
  const node = viewport.scene?.userData.textToThree?.objectsById[selectedId];
  if (!node) return;
  const pos = document.getElementById('inspPos');
  const rot = document.getElementById('inspRot');
  const scl = document.getElementById('inspScale');
  if (pos) pos.textContent = fmtVec(node.position);
  if (rot) rot.textContent = fmtVec(node.rotation);
  if (scl) scl.textContent = fmtVec(node.scale);
}

// ---------------------------------------------------------------------------
// Timeline UI (canvas)
// ---------------------------------------------------------------------------

const tlCanvas = els.timelineCanvas;
const tlCtx = tlCanvas.getContext('2d');
const ROW_H = 20;
const GUTTER = 96;
let tlDpr = 1;

new ResizeObserver(resizeTimelineCanvas).observe(tlCanvas.parentElement);

function resizeTimelineCanvas() {
  const wrap = tlCanvas.parentElement;
  tlDpr = Math.min(window.devicePixelRatio, 2);
  tlCanvas.width = Math.max(1, wrap.clientWidth * tlDpr);
  tlCanvas.height = Math.max(1, wrap.clientHeight * tlDpr);
  drawTimeline();
}

function updateClipCount() {
  els.clipCount.textContent =
    timeline.clips.length > 0 ? `${timeline.clips.length} clip${timeline.clips.length === 1 ? '' : 's'}` : 'no animation clips';
  els.timeDuration.textContent = timeline.duration.toFixed(2);
}

function updateTimeDisplay() {
  els.timeCurrent.textContent = timeline.time.toFixed(2);
  drawTimeline();
}

function drawTimeline() {
  const w = tlCanvas.width;
  const h = tlCanvas.height;
  tlCtx.clearRect(0, 0, w, h);
  if (w < 10) return;

  const css = getComputedStyle(document.documentElement);
  const cBorder = css.getPropertyValue('--border').trim() || '#232838';
  const cDim = css.getPropertyValue('--text-dim').trim() || '#8a92a6';
  const cAccent = css.getPropertyValue('--accent').trim() || '#4ecdc4';

  const duration = Math.max(timeline.duration, 0.001);
  const trackW = w - GUTTER * tlDpr;
  const xFor = (t) => GUTTER * tlDpr + (t / duration) * trackW;

  // Ruler: second ticks
  tlCtx.strokeStyle = cBorder;
  tlCtx.fillStyle = cDim;
  tlCtx.lineWidth = 1;
  tlCtx.font = `${10 * tlDpr}px system-ui`;
  const stepSec = niceStep(duration);
  for (let t = 0; t <= duration + 1e-6; t += stepSec) {
    const x = xFor(t);
    tlCtx.beginPath();
    tlCtx.moveTo(x, 14 * tlDpr);
    tlCtx.lineTo(x, h);
    tlCtx.globalAlpha = 0.35;
    tlCtx.stroke();
    tlCtx.globalAlpha = 1;
    tlCtx.fillText(`${trimNum(t)}s`, x + 3 * tlDpr, 11 * tlDpr);
  }

  // Clip rows grouped by object
  const rows = [];
  const rowIndex = new Map();
  for (const clip of timeline.clips) {
    if (!rowIndex.has(clip.objectId)) {
      rowIndex.set(clip.objectId, rows.length);
      rows.push({ objectId: clip.objectId, clips: [] });
    }
    rows[rowIndex.get(clip.objectId)].clips.push(clip);
  }

  const palette = ['#4ecdc4', '#c792ea', '#f4d03f', '#58d68d', '#ff9f6b', '#6bb5ff'];
  rows.forEach((row, i) => {
    const y = (22 + i * ROW_H) * tlDpr;
    if (y > h) return;

    // Row label
    tlCtx.fillStyle = cDim;
    tlCtx.font = `${10 * tlDpr}px system-ui`;
    tlCtx.fillText(truncate(row.objectId, 14), 6 * tlDpr, y + 12 * tlDpr);

    const color = palette[i % palette.length];
    for (const clip of row.clips) {
      const x0 = xFor(clip.delay);
      const barW = Math.max(3, xFor(Math.min(clip.delay + clip.duration, duration)) - x0);
      const barY = y + 3 * tlDpr;
      const barH = (ROW_H - 7) * tlDpr;

      tlCtx.fillStyle = color;
      tlCtx.globalAlpha = 0.85;
      roundRect(x0, barY, barW, barH, 3 * tlDpr);
      tlCtx.fill();
      tlCtx.globalAlpha = 1;

      // Loop indicator: dashes extending to horizon
      if (clip.loop && clip.delay + clip.duration < duration) {
        tlCtx.strokeStyle = color;
        tlCtx.globalAlpha = 0.45;
        tlCtx.setLineDash([3 * tlDpr, 3 * tlDpr]);
        tlCtx.beginPath();
        tlCtx.moveTo(x0 + barW + 2 * tlDpr, barY + barH / 2);
        tlCtx.lineTo(xFor(duration), barY + barH / 2);
        tlCtx.stroke();
        tlCtx.setLineDash([]);
        tlCtx.globalAlpha = 1;
      }

      // Property label inside bar when it fits
      tlCtx.fillStyle = '#06231f';
      tlCtx.font = `600 ${9 * tlDpr}px system-ui`;
      const label = `${clip.property}${clip.yoyo ? ' ⇄' : ''}`;
      if (tlCtx.measureText(label).width < barW - 6 * tlDpr) {
        tlCtx.fillText(label, x0 + 4 * tlDpr, barY + barH - 3 * tlDpr);
      }
    }
  });

  drawPlayhead(cAccent);
}

/** Draws only the playhead on top of the already-rendered timeline content. */
function drawPlayhead(accentOverride) {
  const w = tlCanvas.width;
  const h = tlCanvas.height;
  const css = getComputedStyle(document.documentElement);
  const accent = accentOverride ?? (css.getPropertyValue('--accent').trim() || '#4ecdc4');
  const duration = Math.max(timeline.duration, 0.001);
  const trackW = w - GUTTER * tlDpr;
  const x = GUTTER * tlDpr + (timeline.time / duration) * trackW;

  tlCtx.strokeStyle = accent;
  tlCtx.lineWidth = 1.5 * tlDpr;
  tlCtx.beginPath();
  tlCtx.moveTo(x, 0);
  tlCtx.lineTo(x, h);
  tlCtx.stroke();

  // Playhead handle
  tlCtx.fillStyle = accent;
  tlCtx.beginPath();
  tlCtx.moveTo(x - 5 * tlDpr, 0);
  tlCtx.lineTo(x + 5 * tlDpr, 0);
  tlCtx.lineTo(x, 7 * tlDpr);
  tlCtx.closePath();
  tlCtx.fill();
}

// Scrubbing
let scrubbing = false;
tlCanvas.addEventListener('pointerdown', (e) => {
  scrubbing = true;
  tlCanvas.setPointerCapture(e.pointerId);
  seekFromPointer(e);
});
tlCanvas.addEventListener('pointermove', (e) => {
  if (scrubbing) seekFromPointer(e);
});
tlCanvas.addEventListener('pointerup', () => { scrubbing = false; });

function seekFromPointer(event) {
  const rect = tlCanvas.getBoundingClientRect();
  const trackX = event.clientX - rect.left - GUTTER;
  const trackW = rect.width - GUTTER;
  if (trackW <= 0) return;
  timeline.seek((trackX / trackW) * timeline.duration);
}

// ---------------------------------------------------------------------------
// Transport controls
// ---------------------------------------------------------------------------

els.playBtn.addEventListener('click', () => timeline.toggle());
timeline.onChange((event) => {
  if (event === 'play' || event === 'pause' || event === 'ended') {
    els.playBtn.textContent = timeline.playing ? '⏸' : '▶';
  }
});
els.speedSelect.addEventListener('change', () => {
  timeline.speed = parseFloat(els.speedSelect.value);
});

// ---------------------------------------------------------------------------
// Gizmo toolbar
// ---------------------------------------------------------------------------

const toolButtons = {
  translate: document.getElementById('toolTranslate'),
  rotate: document.getElementById('toolRotate'),
  scale: document.getElementById('toolScale'),
};
for (const [mode, btn] of Object.entries(toolButtons)) {
  btn.addEventListener('click', () => setGizmoMode(mode));
}
document.getElementById('toolFrame').addEventListener('click', () => viewport.frameSelected());
document.getElementById('toolResetCam').addEventListener('click', () => viewport.resetCamera());

function setGizmoMode(mode) {
  viewport.transformControls.setMode(mode);
  for (const [m, btn] of Object.entries(toolButtons)) {
    btn.classList.toggle('active', m === mode);
  }
}

// ---------------------------------------------------------------------------
// Keyboard shortcuts
// ---------------------------------------------------------------------------

window.addEventListener('keydown', (event) => {
  const typing = document.activeElement === els.promptInput;
  if (typing) {
    if (event.key === 'Enter') els.generateBtn.click();
    return;
  }
  switch (event.key) {
    case ' ': event.preventDefault(); timeline.toggle(); break;
    case 'w': case 'W': setGizmoMode('translate'); break;
    case 'e': case 'E': setGizmoMode('rotate'); break;
    case 'r': case 'R': setGizmoMode('scale'); break;
    case 'f': case 'F': viewport.frameSelected(); break;
    case 'Home': viewport.resetCamera(); break;
    case 'Escape': viewport.clearSelection(); break;
  }
});

// ---------------------------------------------------------------------------
// Generate / Edit buttons
// ---------------------------------------------------------------------------

els.generateBtn.addEventListener('click', () => {
  const prompt = els.promptInput.value.trim();
  if (!prompt) { showToast('Type a prompt first.'); return; }
  generateScene(matchDemoKey(prompt));
});

els.editBtn.addEventListener('click', () => {
  const instruction = els.promptInput.value.trim();
  if (!instruction) { showToast('Type an edit instruction.'); return; }
  applyEdit(instruction);
});

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

let toastTimer = null;
function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => els.toast.classList.remove('show'), 2600);
}

let hintTimer = null;
function showHint() {
  els.hint.classList.add('visible');
  clearTimeout(hintTimer);
  hintTimer = setTimeout(() => els.hint.classList.remove('visible'), 4200);
}

function niceStep(duration) {
  if (duration <= 6) return 0.5;
  if (duration <= 15) return 1;
  if (duration <= 40) return 5;
  return 10;
}

function trimNum(n) {
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

function fmtVec(vec) {
  return `[${vec.x.toFixed(2)}, ${vec.y.toFixed(2)}, ${vec.z.toFixed(2)}]`;
}

function fmtNum(v) {
  return typeof v === 'number' ? v.toFixed(2) : '—';
}

function truncate(text, max) {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = String(text);
  return div.innerHTML;
}

function roundRect(x, y, w, h, r) {
  tlCtx.beginPath();
  tlCtx.moveTo(x + r, y);
  tlCtx.arcTo(x + w, y, x + w, y + h, r);
  tlCtx.arcTo(x + w, y + h, x, y + h, r);
  tlCtx.arcTo(x, y + h, x, y, r);
  tlCtx.arcTo(x, y, x + w, y, r);
  tlCtx.closePath();
}

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

loadDemoData()
  .then(() => {
    // Auto-load the flagship demo so the first paint is already impressive.
    generateScene('cinematic-product-reveal');
  })
  .catch((error) => {
    showToast(`Failed to load demo specs: ${error.message}`);
    console.error(error);
  });

viewport.start();