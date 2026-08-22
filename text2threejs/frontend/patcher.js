/**
 * Natural-language scene editing (browser side).
 *
 * Patches an existing TextSceneSpec in place rather than regenerating it.
 * Mirrors the deterministic rules of the Python MockLLM provider so edits
 * behave identically offline. Returns a change report describing which
 * subsystems changed, so the app can update only what changed:
 *   - "animations" → rebuild timeline only
 *   - "materials"  → update materials in place
 *   - "camera"     → tween camera
 */

export function patchSpec(spec, instruction) {
  const patched = structuredClone(spec);
  const lowered = instruction.toLowerCase();
  const changed = new Set();

  if (/\b(rotate|spin|turn)\b/.test(lowered)) {
    applyRotation(patched, lowered);
    changed.add('animations');
  }

  if (/\b(slow|slower|slowly)\b/.test(lowered)) {
    scaleDurations(patched, 1.6);
    changed.add('animations');
  } else if (/\b(fast|faster|quickly)\b/.test(lowered)) {
    scaleDurations(patched, 0.6);
    changed.add('animations');
  }

  if (/camera (closer|nearer)|move the camera|push in|zoom in/.test(lowered)) {
    scaleCameraDistance(patched, 0.7);
    changed.add('camera');
  } else if (/camera (farther|further|back)|pull out|zoom out/.test(lowered)) {
    scaleCameraDistance(patched, 1.35);
    changed.add('camera');
  }

  const colorEdit = matchColorEdit(lowered);
  if (colorEdit) {
    applyMaterialEdit(patched, colorEdit);
    changed.add('materials');
  }

  return { spec: patched, changed: [...changed] };
}

// ---------------------------------------------------------------------------
// Edit rules
// ---------------------------------------------------------------------------

function applyRotation(spec, instruction) {
  const objects = spec.objects ?? [];
  if (!objects.length) return;
  // Prefer a named target mentioned in the instruction, else first object.
  let targetId = null;
  for (const obj of objects) {
    const name = String(obj.name ?? obj.id).toLowerCase();
    if (instruction.includes(name) && name.length > 2) {
      targetId = obj.id;
      break;
    }
  }
  targetId = targetId ?? objects[0].id;

  const fullTurn = /360|full|complete/.test(instruction);
  const animations = spec.animations ?? [];
  for (const anim of animations) {
    if (anim.object === targetId && String(anim.property).startsWith('rotation')) {
      if (fullTurn) anim.to = Math.PI * 2;
      return;
    }
  }
  animations.push({
    id: `${targetId}_rotate_${animations.length}`,
    object: targetId,
    property: 'rotation.y',
    from: 0,
    to: fullTurn ? Math.PI * 2 : Math.PI,
    duration: 4,
    easing: 'easeInOutCubic',
    delay: 0,
    loop: true,
    yoyo: false,
  });
  spec.animations = animations;
}

function scaleDurations(spec, factor) {
  for (const anim of spec.animations ?? []) {
    if (typeof anim.duration === 'number') {
      anim.duration = Math.max(0.05, +(anim.duration * factor).toFixed(3));
    }
  }
}

function scaleCameraDistance(spec, factor) {
  const camera = spec.camera;
  if (!camera || !Array.isArray(camera.position)) return;
  const target = Array.isArray(camera.target) ? camera.target : [0, 0, 0];
  camera.position = [
    round2(target[0] + (camera.position[0] - target[0]) * factor),
    round2(target[1] + (camera.position[1] - target[1]) * factor),
    round2(target[2] + (camera.position[2] - target[2]) * factor),
  ];
}

function matchColorEdit(instruction) {
  if (/glossy black|shiny black/.test(instruction)) {
    return { color: '#0a0a0a', roughness: 0.05, metalness: 0.9 };
  }
  if (/\bmatte\b/.test(instruction)) return { roughness: 0.85 };
  if (/\bglossy\b|\bshiny\b|\breflective\b/.test(instruction)) return { roughness: 0.08 };
  if (/\bred\b/.test(instruction)) return { color: '#e03434' };
  if (/\bblue\b/.test(instruction)) return { color: '#2266dd' };
  if (/\bgreen\b/.test(instruction)) return { color: '#22aa55' };
  if (/\bgold(en)?\b/.test(instruction)) return { color: '#d4af37', metalness: 1 };
  if (/\bblack\b/.test(instruction)) return { color: '#141414' };
  if (/\bwhite\b/.test(instruction)) return { color: '#f0f0f0' };
  return null;
}

function applyMaterialEdit(spec, edit) {
  const materials = spec.materials ?? [];
  if (!materials.length) return;
  Object.assign(materials[0], edit);
}

function round2(v) {
  return Math.round(v * 100) / 100;
}