/**
 * Data-driven animation timeline.
 *
 * Every TextSceneSpec animation clip is evaluated deterministically from a
 * single global time value — play, pause, seek and scrub are all just "set t".
 * No per-object hard-coded behavior; the timeline interprets spec data.
 *
 * Property paths supported: position[.x|.y|.z], rotation[.x|.y|.z],
 * scale[.x|.y|.z], opacity, material.color, material.emissive,
 * material.emissiveIntensity, material.roughness, material.metalness,
 * material.opacity, visible.
 */

import * as THREE from 'three';
import { getEasing } from './easing.js';

export class Timeline {
  constructor() {
    this.clips = [];
    this.time = 0;
    this.duration = 0; // display duration (non-looping horizon)
    this.playing = false;
    this.speed = 1;
    this._listeners = new Set();
  }

  /** Rebuild clips from scene.userData.textToThree.animationTargets. */
  load(animationTargets) {
    this.clips = [];
    let maxEnd = 0;
    for (const target of animationTargets ?? []) {
      const clip = {
        id: target.id,
        objectId: target.objectId,
        property: target.property,
        from: target.from,
        to: target.to,
        duration: Math.max(0.001, target.duration),
        delay: target.delay ?? 0,
        easing: getEasing(target.easing),
        easingName: target.easing ?? 'linear',
        loop: target.loop === true,
        yoyo: target.yoyo === true,
        apply: makeApplier(target),
      };
      this.clips.push(clip);
      if (!clip.loop) {
        maxEnd = Math.max(maxEnd, clip.delay + clip.duration);
      }
    }
    // Display horizon: longest non-looping clip, or a sensible default when
    // everything loops so the timeline still shows something scrubbable.
    this.duration = maxEnd > 0 ? maxEnd : defaultHorizon(this.clips);
    this.time = 0;
    this.evaluate(0);
    this._emit('load');
  }

  play() {
    this.playing = true;
    this._emit('play');
  }

  pause() {
    this.playing = false;
    this._emit('pause');
  }

  toggle() {
    if (this.playing) this.pause();
    else this.play();
  }

  stop() {
    this.pause();
    this.seek(0);
  }

  seek(t) {
    this.time = clamp(t, 0, this.duration);
    this.evaluate(this.time);
    this._emit('seek');
  }

  tick(deltaSeconds) {
    if (!this.playing) return;
    let next = this.time + deltaSeconds * this.speed;
    if (next >= this.duration) {
      next = this.duration;
      this.time = next;
      this.evaluate(next);
      this.playing = false;
      this._emit('ended');
      return;
    }
    this.time = next;
    this.evaluate(next);
  }

  /** Apply every clip at global time t. Deterministic and allocation-free. */
  evaluate(t) {
    for (let i = 0; i < this.clips.length; i++) {
      const clip = this.clips[i];
      const local = t - clip.delay;
      if (local <= 0) {
        clip.apply(clip.from);
        continue;
      }
      let p;
      if (clip.loop) {
        p = local / clip.duration;
        p -= Math.floor(p); // wrap forever
        if (clip.yoyo) {
          const cycle = Math.floor(local / clip.duration) % 2;
          if (cycle === 1) p = 1 - p;
        }
      } else {
        p = clamp(local / clip.duration, 0, 1);
        if (clip.yoyo && p > 0.5) {
          // Non-looping yoyo plays forward then back once.
          p = 1 - p;
        }
      }
      const eased = clip.easing(p);
      clip.apply(lerpValue(clip.from, clip.to, eased));
    }
  }

  onChange(listener) {
    this._listeners.add(listener);
    return () => this._listeners.delete(listener);
  }

  _emit(event) {
    for (const listener of this._listeners) listener(event, this);
  }
}

function defaultHorizon(clips) {
  let max = 4;
  for (const clip of clips) max = Math.max(max, clip.delay + clip.duration * 2);
  return max;
}

function clamp(v, min, max) {
  return v < min ? min : v > max ? max : v;
}

// ---------------------------------------------------------------------------
// Property appliers — resolve a dotted property path onto a Three.js object
// ---------------------------------------------------------------------------

function makeApplier(target) {
  const { property, node, mesh } = target;

  // Vector component e.g. position.x / rotation.y / scale.z
  const vectorMatch = /^(position|rotation|scale)\.(x|y|z)$/.exec(property);
  if (vectorMatch) {
    const [, group, axis] = vectorMatch;
    const vec = node[group];
    return (value) => {
      vec[axis] = value;
    };
  }

  // Whole vector e.g. position / scale
  if (property === 'position' || property === 'scale') {
    const vec = node[property];
    return (value) => {
      if (Array.isArray(value)) vec.set(value[0], value[1], value[2]);
    };
  }

  // Material scalar properties
  if (mesh?.material) {
    const material = mesh.material;
    switch (property) {
      case 'material.emissiveIntensity':
        return (value) => {
          material.emissiveIntensity = value;
        };
      case 'material.roughness':
        return (value) => {
          material.roughness = clamp01(value);
        };
      case 'material.metalness':
        return (value) => {
          material.metalness = clamp01(value);
        };
      case 'material.opacity':
      case 'opacity': {
        if (!material.transparent && property === 'opacity') material.transparent = true;
        return (value) => {
          material.opacity = clamp01(value);
        };
      }
      case 'material.color': {
        const color = material.color ?? new THREE.Color();
        return (value) => {
          if (typeof value === 'string') color.set(value);
          else if (Array.isArray(value)) color.setRGB(value[0], value[1], value[2]);
          else color.setScalar(value);
        };
      }
      case 'material.emissive': {
        const emissive = material.emissive ?? new THREE.Color();
        return (value) => {
          if (typeof value === 'string') emissive.set(value);
          else if (Array.isArray(value)) emissive.setRGB(value[0], value[1], value[2]);
        };
      }
    }
  }

  if (property === 'visible') {
    return (value) => {
      node.visible = Boolean(value);
    };
  }

  // Unknown property: no-op applier keeps the timeline robust to partial specs.
  return () => {};
}

function lerpValue(from, to, t) {
  if (typeof from === 'number' && typeof to === 'number') return from + (to - from) * t;
  if (Array.isArray(from) && Array.isArray(to)) {
    return [
      from[0] + ((to[0] ?? from[0]) - from[0]) * t,
      from[1] + ((to[1] ?? from[1]) - from[1]) * t,
      from[2] + ((to[2] ?? from[2]) - from[2]) * t,
    ];
  }
  return t < 1 ? from : to;
}

function clamp01(v) {
  return Math.max(0, Math.min(1, v));
}