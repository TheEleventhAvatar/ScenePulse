/**
 * Scene builder: TextSceneSpec JSON → live Three.js scene.
 *
 * Deterministic, data-driven construction. Preserves semantic object IDs,
 * hierarchy, materials, lights, camera and environment. Exposes runtime
 * metadata on scene.userData.textToThree.
 *
 * No LLM-generated JavaScript is ever executed — this builder interprets
 * structured spec data only.
 */

import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { FresnelRimMaterial, HologramMaterial, createGradientBackground } from './shaders.js';

// ---------------------------------------------------------------------------
// Geometry factory
// ---------------------------------------------------------------------------

function makeGeometry(obj) {
  const dims = obj.dimensions ?? {};
  const num = (key, fallback) => (typeof dims[key] === 'number' ? dims[key] : fallback);
  switch (obj.type) {
    case 'box':
      return new THREE.BoxGeometry(num('width', 1), num('height', 1), num('depth', 1));
    case 'sphere':
      return new THREE.SphereGeometry(num('radius', 0.5), 48, 32);
    case 'ellipsoid': {
      const geo = new THREE.SphereGeometry(0.5, 48, 32);
      geo.scale(num('width', 1), num('height', 1), num('depth', 1));
      return geo;
    }
    case 'cylinder':
      return new THREE.CylinderGeometry(
        num('radius', 0.5), num('radius', 0.5), num('height', 1), 48,
      );
    case 'cone':
      return new THREE.ConeGeometry(num('radius', 0.5), num('height', 1), 48);
    case 'capsule':
      return new THREE.CapsuleGeometry(num('radius', 0.35), num('height', 0.7), 8, 24);
    case 'torus':
      return new THREE.TorusGeometry(num('radius', 0.45), Math.min(0.12, num('radius', 0.45) * 0.25), 24, 96);
    case 'plane':
      return new THREE.PlaneGeometry(num('width', 1), num('height', 1));
    case 'ring':
      return new THREE.RingGeometry(
        num('radius', 0.4) * 0.6, num('radius', 0.4), 64,
      );
    case 'circle':
      return new THREE.CircleGeometry(num('radius', 0.5), 64);
    case 'group':
      return null;
    default:
      // Unknown types fall back to a box rather than failing the whole scene.
      return new THREE.BoxGeometry(num('width', 1), num('height', 1), num('depth', 1));
  }
}

// ---------------------------------------------------------------------------
// Material factory
// ---------------------------------------------------------------------------

const TONE_MAP = {
  none: THREE.NoToneMapping,
  linear: THREE.LinearToneMapping,
  reinhard: THREE.ReinhardToneMapping,
  cineon: THREE.CineonToneMapping,
  aces: THREE.ACESFilmicToneMapping,
  agx: THREE.AgXToneMapping,
  neutral: THREE.NeutralToneMapping,
};

export function makeMaterial(materialSpec) {
  const spec = materialSpec ?? {};
  const color = new THREE.Color(spec.color ?? '#8a7a5f');
  const emissive = new THREE.Color(spec.emissive ?? '#000000');

  if (spec.shaderModel === 'fresnel-rim') {
    return new FresnelRimMaterial({
      baseColor: spec.color,
      rimColor: spec.emissive !== '#000000' ? spec.emissive : '#4a8aff',
      rimIntensity: spec.emissiveIntensity || 1.5,
    });
  }
  if (spec.shaderModel === 'hologram') {
    return new HologramMaterial({
      baseColor: spec.color,
      edgeColor: spec.emissive !== '#000000' ? spec.emissive : '#aaffdd',
      opacity: spec.opacity ?? 0.55,
    });
  }

  const material = new THREE.MeshPhysicalMaterial({
    color,
    roughness: clamp01(spec.roughness ?? 0.7),
    metalness: clamp01(spec.metalness ?? 0),
    emissive,
    emissiveIntensity: spec.emissiveIntensity ?? 0,
    clearcoat: clamp01(spec.clearcoat ?? 0),
    clearcoatRoughness: clamp01(spec.clearcoatRoughness ?? 0.25),
    transmission: clamp01(spec.transmission ?? 0),
    ior: spec.ior ?? 1.5,
    sheen: clamp01(spec.sheen ?? 0),
    iridescence: clamp01(spec.iridescence ?? 0),
    specularIntensity: spec.specularIntensity ?? 1,
    envMapIntensity: spec.envMapIntensity ?? 0.8,
    opacity: clamp01(spec.opacity ?? 1),
    transparent: spec.transparent === true || (spec.opacity ?? 1) < 1 || (spec.transmission ?? 0) > 0,
    wireframe: spec.wireframe === true,
    flatShading: spec.flatShading === true,
    side: spec.doubleSided ? THREE.DoubleSide : THREE.FrontSide,
  });
  material.userData.specId = spec.id;
  return material;
}

function clamp01(v) {
  return Math.max(0, Math.min(1, v));
}

// ---------------------------------------------------------------------------
// Scene builder
// ---------------------------------------------------------------------------

export function buildScene(spec, { renderer } = {}) {
  const scene = new THREE.Scene();

  // --- Environment ---------------------------------------------------------
  const env = spec.environment ?? {};
  scene.background = new THREE.Color(env.background ?? spec.scene?.background ?? '#0a0a12');

  const fog = env.fog ?? spec.scene?.fog;
  if (fog && fog.type === 'fog') {
    scene.fog = new THREE.Fog(new THREE.Color(fog.color ?? '#0a0a12'), fog.near ?? 10, fog.far ?? 30);
  } else if (fog && fog.type === 'fog-exp2') {
    scene.fog = new THREE.FogExp2(new THREE.Color(fog.color ?? '#0a0a12'), fog.density ?? 0.03);
  }

  // Procedural gradient backdrop for dark scenes (custom shader); plain color otherwise.
  const bgIsDark = isDarkColor(scene.background);
  let backgroundMesh = null;
  if (bgIsDark) {
    backgroundMesh = createGradientBackground(
      lighten(scene.background, 2.2),
      scene.background,
      accentFromScene(spec),
    );
    scene.add(backgroundMesh);
  }

  // Tone mapping
  if (renderer) {
    renderer.toneMapping = TONE_MAP[env.toneMapping] ?? THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = env.toneMappingExposure ?? 1;
  }

  // PMREM environment for PBR reflections (one-time cost per renderer)
  if (renderer && !renderer.userData?.__envTexture) {
    const pmrem = new THREE.PMREMGenerator(renderer);
    const envTexture = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    pmrem.dispose();
    renderer.userData = { ...(renderer.userData ?? {}), __envTexture: envTexture };
  }
  if (renderer?.userData?.__envTexture) {
    scene.environment = renderer.userData.__envTexture;
  }

  // --- Materials -----------------------------------------------------------
  const materialsById = new Map();
  for (const mat of spec.materials ?? []) {
    if (mat?.id) materialsById.set(mat.id, makeMaterial(mat));
  }

  // --- Objects (hierarchy preserved via parent ids) ------------------------
  const objectsRoot = new THREE.Group();
  objectsRoot.name = '__objects__';
  scene.add(objectsRoot);

  const nodesById = new Map();
  const meshesById = new Map();
  const pendingChildren = [];

  for (const obj of spec.objects ?? []) {
    const node = new THREE.Group();
    node.name = obj.id;
    applyTransform(node, obj);

    const geometry = makeGeometry(obj);
    if (geometry) {
      const material =
        (obj.material && materialsById.get(obj.material)) ||
        new THREE.MeshStandardMaterial({ color: 0x888888 });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.name = `${obj.id}__mesh`;
      mesh.castShadow = obj.castShadow !== false;
      mesh.receiveShadow = obj.receiveShadow !== false;
      mesh.userData.objectId = obj.id;
      node.add(mesh);
      meshesById.set(obj.id, mesh);
    }

    node.userData.spec = obj;
    nodesById.set(obj.id, node);
    pendingChildren.push(obj);
  }

  // Second pass: attach children to parents (parents first not guaranteed).
  for (const obj of pendingChildren) {
    const node = nodesById.get(obj.id);
    const parentNode = (obj.parent && nodesById.get(obj.parent)) || objectsRoot;
    parentNode.add(node);
  }

  // --- Lights ---------------------------------------------------------------
  const lightsGroup = new THREE.Group();
  lightsGroup.name = '__lights__';
  for (const light of spec.lights ?? []) {
    const lightObj = buildLight(light);
    if (lightObj) lightsGroup.add(lightObj);
  }
  scene.add(lightsGroup);

  // --- Camera ----------------------------------------------------------------
  const cam = spec.camera ?? {};
  const camera = new THREE.PerspectiveCamera(
    cam.fov ?? 50,
    16 / 9, // aspect corrected by viewport on first resize
    cam.near ?? 0.1,
    cam.far ?? 1000,
  );
  const pos = cam.position ?? [0, 2, 8];
  camera.position.set(pos[0], pos[1], pos[2]);
  const target = cam.target ?? [0, 0, 0];
  camera.lookAt(target[0], target[1], target[2]);

  // --- Runtime metadata -------------------------------------------------------
  scene.userData.textToThree = {
    schemaVersion: spec.schemaVersion,
    sceneName: spec.scene?.name ?? 'Untitled',
    description: spec.scene?.description ?? '',
    objectsById: Object.fromEntries(nodesById),
    meshesById: Object.fromEntries(meshesById),
    materialsById: Object.fromEntries(materialsById),
    animationTargets: collectAnimationTargets(spec, nodesById, meshesById),
    interactionTargets: collectInteractionTargets(spec, nodesById),
    lightsGroup,
    objectsRoot,
    backgroundMesh,
    cameraHome: {
      position: camera.position.clone(),
      target: new THREE.Vector3(target[0], target[1], target[2]),
    },
    dispose() {
      disposeObject(objectsRoot);
      disposeObject(lightsGroup);
      if (backgroundMesh) {
        backgroundMesh.geometry.dispose();
        backgroundMesh.material.dispose();
      }
    },
  };

  return { scene, camera };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function applyTransform(node, obj) {
  const p = obj.position ?? [0, 0, 0];
  const r = obj.rotation ?? [0, 0, 0];
  const s = obj.scale ?? [1, 1, 1];
  node.position.set(p[0], p[1], p[2]);
  node.rotation.set(r[0], r[1], r[2]);
  node.scale.set(s[0], s[1], s[2]);
}

function buildLight(light) {
  const color = new THREE.Color(light.color ?? '#ffffff');
  const intensity = light.intensity ?? 1;
  let lightObj;
  switch (light.type) {
    case 'ambient':
      lightObj = new THREE.AmbientLight(color, intensity);
      break;
    case 'directional': {
      lightObj = new THREE.DirectionalLight(color, intensity);
      const t = light.target;
      if (Array.isArray(t)) {
        lightObj.target.position.set(t[0], t[1], t[2]);
        lightObj.target.updateMatrixWorld();
      }
      break;
    }
    case 'point':
      lightObj = new THREE.PointLight(color, intensity, light.distance ?? 0, light.decay ?? 2);
      break;
    case 'spot':
      lightObj = new THREE.SpotLight(color, intensity, light.distance ?? 0, light.angle ?? 0.5, light.penumbra ?? 0, light.decay ?? 2);
      break;
    case 'hemisphere':
      lightObj = new THREE.HemisphereLight(color, new THREE.Color('#202028'), intensity);
      break;
    default:
      return null;
  }
  lightObj.name = light.id;
  const p = light.position ?? [0, 3, 0];
  lightObj.position.set(p[0], p[1], p[2]);
  if (lightObj.shadow && light.castShadow !== false && light.type !== 'ambient') {
    lightObj.castShadow = true;
    const size = light.shadowMapSize ?? 1024;
    lightObj.shadow.mapSize.set(size, size);
    lightObj.shadow.bias = light.shadowBias ?? -0.0005;
    lightObj.shadow.normalBias = light.shadowNormalBias ?? 0.02;
  } else if (lightObj.isDirectionalLight || lightObj.isPointLight || lightObj.isSpotLight) {
    lightObj.castShadow = false;
  }
  lightObj.visible = light.visible !== false;
  return lightObj;
}

function collectAnimationTargets(spec, nodesById, meshesById) {
  const targets = [];
  for (const anim of spec.animations ?? []) {
    const node = nodesById.get(anim.object);
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
      mesh: meshesById.get(anim.object) ?? null,
    });
  }
  return targets;
}

function collectInteractionTargets(spec, nodesById) {
  const targets = [];
  for (const interaction of spec.interactions ?? []) {
    const node = nodesById.get(interaction.object);
    if (!node) continue;
    targets.push({ ...interaction, node });
  }
  return targets;
}

/** Deep-dispose geometries and materials under an object. */
export function disposeObject(root) {
  root.traverse((child) => {
    if (child.geometry) child.geometry.dispose();
    const material = child.material;
    if (!material) return;
    const list = Array.isArray(material) ? material : [material];
    for (const m of list) {
      for (const key of Object.keys(m)) {
        const value = m[key];
        if (value && value.isTexture) value.dispose();
      }
      m.dispose();
    }
  });
}

function isDarkColor(color) {
  const c = color instanceof THREE.Color ? color : new THREE.Color(color);
  return c.getHSL({ h: 0, s: 0, l: 0 }).l < 0.25;
}

function lighten(color, factor) {
  const c = color.clone();
  const hsl = c.getHSL({ h: 0, s: 0, l: 0 });
  c.setHSL(hsl.h, hsl.s, Math.min(1, hsl.l * factor + 0.04));
  return c;
}

function accentFromScene(spec) {
  const firstEmissive = (spec.materials ?? []).find((m) => m.emissive && m.emissive !== '#000000');
  return firstEmissive?.emissive ?? '#334466';
}