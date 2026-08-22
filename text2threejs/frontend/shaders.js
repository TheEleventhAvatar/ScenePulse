/**
 * Custom GLSL shader effects for the Text-to-Three.js viewport.
 *
 * Hand-written GLSL — not library-only effects:
 *  - FresnelRimMaterial: view-dependent rim glow (fresnel term in fragment shader)
 *  - HologramMaterial: animated scanlines + fresnel edge + flicker
 *  - GradientBackground: fullscreen procedural gradient with subtle noise dithering
 */

import * as THREE from 'three';

// ---------------------------------------------------------------------------
// Fresnel rim glow
// ---------------------------------------------------------------------------

const FRESNEL_VERT = /* glsl */ `
varying vec3 vWorldNormal;
varying vec3 vViewDir;
void main() {
  vec4 worldPos = modelMatrix * vec4(position, 1.0);
  vWorldNormal = normalize(mat3(modelMatrix) * normal);
  vViewDir = normalize(cameraPosition - worldPos.xyz);
  gl_Position = projectionMatrix * viewMatrix * worldPos;
}
`;

const FRESNEL_FRAG = /* glsl */ `
uniform vec3 uBaseColor;
uniform vec3 uRimColor;
uniform float uRimPower;
uniform float uRimIntensity;
uniform float uTime;
varying vec3 vWorldNormal;
varying vec3 vViewDir;

// Cheap hash noise for subtle shimmer
float hash(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void main() {
  float fresnel = pow(1.0 - max(dot(vWorldNormal, vViewDir), 0.0), uRimPower);
  // Subtle time-based shimmer so the rim feels alive without being noisy
  float shimmer = 0.94 + 0.06 * sin(uTime * 2.0 + vWorldNormal.y * 4.0);
  vec3 color = uBaseColor + uRimColor * fresnel * uRimIntensity * shimmer;
  gl_FragColor = vec4(color, 1.0);
}
`;

export class FresnelRimMaterial extends THREE.ShaderMaterial {
  constructor({ baseColor = '#111118', rimColor = '#4a8aff', rimPower = 3.0, rimIntensity = 1.5 } = {}) {
    super({
      vertexShader: FRESNEL_VERT,
      fragmentShader: FRESNEL_FRAG,
      uniforms: {
        uBaseColor: { value: new THREE.Color(baseColor) },
        uRimColor: { value: new THREE.Color(rimColor) },
        uRimPower: { value: rimPower },
        uRimIntensity: { value: rimIntensity },
        uTime: { value: 0 },
      },
    });
    this.isFresnelRimMaterial = true;
  }

  tick(time) {
    this.uniforms.uTime.value = time;
  }
}

// ---------------------------------------------------------------------------
// Holographic scanline material (transparent)
// ---------------------------------------------------------------------------

const HOLO_FRAG = /* glsl */ `
uniform vec3 uBaseColor;
uniform vec3 uEdgeColor;
uniform float uTime;
uniform float uScanDensity;
uniform float uOpacity;
varying vec3 vWorldNormal;
varying vec3 vViewDir;
varying float vWorldPos;

void main() {
  float fresnel = pow(1.0 - max(dot(vWorldNormal, vViewDir), 0.0), 2.0);
  // Animated horizontal scanlines in object space
  float scan = 0.5 + 0.5 * sin(vWorldPos.y * uScanDensity - uTime * 6.0);
  scan = smoothstep(0.35, 0.65, scan);
  float flicker = 0.92 + 0.08 * sin(uTime * 23.0);
  vec3 color = mix(uBaseColor, uEdgeColor, fresnel);
  float alpha = uOpacity * (0.35 + 0.45 * scan + 0.35 * fresnel) * flicker;
  gl_FragColor = vec4(color, alpha);
}
`;

const HOLO_VERT = /* glsl */ `
varying vec3 vWorldNormal;
varying vec3 vViewDir;
varying float vWorldPos;
void main() {
  vec4 worldPos = modelMatrix * vec4(position, 1.0);
  vWorldNormal = normalize(mat3(modelMatrix) * normal);
  vViewDir = normalize(cameraPosition - worldPos.xyz);
  vWorldPos = worldPos.y;
  gl_Position = projectionMatrix * viewMatrix * worldPos;
}
`;

export class HologramMaterial extends THREE.ShaderMaterial {
  constructor({ baseColor = '#00ff88', edgeColor = '#aaffdd', opacity = 0.55, scanDensity = 40.0 } = {}) {
    super({
      vertexShader: HOLO_VERT,
      fragmentShader: HOLO_FRAG,
      uniforms: {
        uBaseColor: { value: new THREE.Color(baseColor) },
        uEdgeColor: { value: new THREE.Color(edgeColor) },
        uTime: { value: 0 },
        uScanDensity: { value: scanDensity },
        uOpacity: { value: opacity },
      },
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending,
    });
    this.isHologramMaterial = true;
  }

  tick(time) {
    this.uniforms.uTime.value = time;
  }
}

// ---------------------------------------------------------------------------
// Procedural gradient background (fullscreen triangle)
// ---------------------------------------------------------------------------

const BG_FRAG = /* glsl */ `
uniform vec3 uTopColor;
uniform vec3 uBottomColor;
uniform vec3 uAccentColor;
uniform float uTime;
varying vec2 vUv;

float hash(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void main() {
  // Vertical gradient with a soft radial accent glow
  vec3 base = mix(uBottomColor, uTopColor, vUv.y);
  vec2 center = vec2(0.5, 0.42);
  float dist = length((vUv - center) * vec2(1.6, 1.0));
  float glow = exp(-dist * 3.2);
  base += uAccentColor * glow * 0.22;
  // Ordered-ish dithering kills banding on dark gradients
  float dither = (hash(vUv * 913.7 + fract(uTime)) - 0.5) / 255.0;
  gl_FragColor = vec4(base + dither, 1.0);
}
`;

const BG_VERT = /* glsl */ `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = vec4(position.xy, 0.9999, 1.0);
}
`;

export function createGradientBackground(topColor, bottomColor, accentColor) {
  const material = new THREE.ShaderMaterial({
    vertexShader: BG_VERT,
    fragmentShader: BG_FRAG,
    uniforms: {
      uTopColor: { value: new THREE.Color(topColor ?? '#101024') },
      uBottomColor: { value: new THREE.Color(bottomColor ?? '#050508') },
      uAccentColor: { value: new THREE.Color(accentColor ?? '#334466') },
      uTime: { value: 0 },
    },
    depthWrite: false,
    depthTest: false,
  });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material);
  mesh.frustumCulled = false;
  mesh.renderOrder = -1000;
  mesh.name = '__gradient_background__';
  return mesh;
}

/** Tick every registered custom-shader material once per frame. */
export function createShaderTicker() {
  const materials = [];
  return {
    register(material) {
      if (material && typeof material.tick === 'function') materials.push(material);
    },
    unregister(material) {
      const index = materials.indexOf(material);
      if (index >= 0) materials.splice(index, 1);
    },
    tick(time) {
      for (let i = 0; i < materials.length; i++) materials[i].tick(time);
    },
    dispose() {
      materials.length = 0;
    },
  };
}