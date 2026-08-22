/**
 * Viewport: renderer, orbit/pan/zoom controls, object selection with an
 * inverted-hull outline highlight, transform gizmos, smooth camera framing.
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { TransformControls } from 'three/addons/controls/TransformControls.js';

const OUTLINE_VERT = /* glsl */ `
uniform float uThickness;
void main() {
  vec3 inflated = position + normal * uThickness;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(inflated, 1.0);
}
`;

const OUTLINE_FRAG = /* glsl */ `
uniform vec3 uColor;
uniform float uPulse;
void main() {
  gl_FragColor = vec4(uColor * (0.85 + 0.15 * uPulse), 1.0);
}
`;

export class Viewport {
  constructor(container) {
    this.container = container;

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(this.renderer.domElement);

    this.scene = null;
    this.camera = null;

    // Placeholder camera until a scene provides its own; shared by both
    // control systems so they always agree on the active camera.
    this._activeCamera = new THREE.PerspectiveCamera();

    // Orbit / pan / zoom
    this.controls = new OrbitControls(this._activeCamera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.screenSpacePanning = true;

    // Transform gizmo (r169+: the controls are not an Object3D; the visual
    // gizmo is a separate helper that must be added to the scene instead)
    this.transformControls = new TransformControls(this._activeCamera, this.renderer.domElement);
    this.transformControls.setSize(0.85);
    this.transformHelper = this.transformControls.getHelper();
    this.transformControls.addEventListener('dragging-changed', (event) => {
      this.controls.enabled = !event.value;
    });
    this.transformControls.addEventListener('objectChange', () => {
      this._emit('transform');
    });

    // Selection outline (inverted hull)
    this.outlineMesh = new THREE.Mesh(
      new THREE.BufferGeometry(),
      new THREE.ShaderMaterial({
        vertexShader: OUTLINE_VERT,
        fragmentShader: OUTLINE_FRAG,
        uniforms: {
          uColor: { value: new THREE.Color('#4ecdc4') },
          uThickness: { value: 0.02 },
          uPulse: { value: 0 },
        },
        side: THREE.BackSide,
      }),
    );
    this.outlineMesh.visible = false;
    this.outlineMesh.name = '__selection_outline__';
    this.outlineTarget = null;

    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.selectedId = null;

    this._listeners = new Set();
    this._clock = new THREE.Clock();
    this._running = false;
    this._resizeObserver = new ResizeObserver(() => this.resize());
    this._resizeObserver.observe(container);

    this._bindPointerEvents();
  }

  /** Replace the scene; disposes the previous one fully. */
  setScene(scene, camera) {
    if (this.scene) {
      const meta = this.scene.userData.textToThree;
      if (meta?.dispose) meta.dispose();
      this.scene.remove(this.transformHelper);
      this.scene.remove(this.outlineMesh);
    }
    this.scene = scene;
    this.camera = camera;

    this._activeCamera = camera;
    this.controls.object = camera;
    this.transformControls.camera = camera;
    this.controls.target.copy(scene.userData.textToThree.cameraHome.target);
    this.controls.update();

    scene.add(this.outlineMesh);
    scene.add(this.transformHelper);

    this.clearSelection();
    this.resize();
  }

  select(objectId) {
    const meta = this.scene?.userData.textToThree;
    if (!meta) return;
    const mesh = objectId ? meta.meshesById[objectId] : null;
    this.selectedId = objectId ?? null;

    if (!mesh) {
      this.outlineMesh.visible = false;
      this.outlineTarget = null;
      this.transformControls.detach();
      this._emit('selection', null);
      return;
    }

    // Reuse geometry for the outline hull — no duplication.
    this.outlineMesh.geometry = mesh.geometry;
    this.outlineTarget = mesh;
    this.outlineMesh.visible = true;
    this.transformControls.attach(mesh);
    this._emit('selection', objectId);
  }

  clearSelection() {
    this.select(null);
  }

  frameSelected() {
    const target = this.outlineTarget ?? this.scene?.userData.textToThree?.objectsRoot;
    if (!target) return;
    this.frameObject(target);
  }

  resetCamera() {
    const home = this.scene?.userData.textToThree?.cameraHome;
    if (!home) return;
    this.flyTo(home.position, home.target);
  }

  /** Smooth GSAP-free fly-to with critically-damped interpolation. */
  flyTo(position, target, durationMs = 900) {
    const startPos = this.camera.position.clone();
    const startTarget = this.controls.target.clone();
    const endPos = position.clone ? position.clone() : new THREE.Vector3(...position);
    const endTarget = target.clone ? target.clone() : new THREE.Vector3(...target);
    const start = performance.now();

    const step = () => {
      const t = Math.min(1, (performance.now() - start) / durationMs);
      // easeInOutCubic
      const e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      this.camera.position.lerpVectors(startPos, endPos, e);
      this.controls.target.lerpVectors(startTarget, endTarget, e);
      if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  frameObject(object) {
    const box = new THREE.Box3().setFromObject(object);
    if (box.isEmpty()) return;
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = (this.camera.fov * Math.PI) / 180;
    const distance = (maxDim / 2) / Math.tan(fov / 2) + maxDim * 0.35;
    const direction = this.camera.position.clone().sub(this.controls.target).normalize();
    this.flyTo(center.clone().addScaledVector(direction, distance), center);
  }

  resize() {
    const width = this.container.clientWidth || 1;
    const height = this.container.clientHeight || 1;
    this.renderer.setSize(width, height, false);
    if (this.camera) {
      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
    }
  }

  start() {
    if (this._running) return;
    this._running = true;
    const loop = () => {
      if (!this._running) return;
      requestAnimationFrame(loop);
      // Nothing to render until a scene is loaded — skip cleanly.
      if (!this.scene || !this.camera) return;
      const delta = this._clock.getDelta();
      const elapsed = this._clock.elapsedTime;
      this._emit('frame', { delta, elapsed });
      this.controls.update();
      // Pulse the selection outline
      if (this.outlineMesh.visible) {
        this.outlineMesh.material.uniforms.uPulse.value =
          0.5 + 0.5 * Math.sin(elapsed * 5.0);
        this.outlineMesh.position.copy(this.outlineTarget.getWorldPosition(_tmpVec));
        this.outlineMesh.quaternion.copy(
          this.outlineTarget.getWorldQuaternion(_tmpQuat),
        );
        this.outlineMesh.scale.copy(
          this.outlineTarget.getWorldScale(_tmpScale),
        );
      }
      this.renderer.render(this.scene, this.camera);
    };
    requestAnimationFrame(loop);
  }

  stop() {
    this._running = false;
  }

  onChange(listener) {
    this._listeners.add(listener);
    return () => this._listeners.delete(listener);
  }

  _emit(event, payload) {
    for (const listener of this._listeners) listener(event, payload);
  }

  _bindPointerEvents() {
    const dom = this.renderer.domElement;
    let downPos = null;

    dom.addEventListener('pointerdown', (event) => {
      downPos = [event.clientX, event.clientY];
    });

    dom.addEventListener('pointerup', (event) => {
      // Distinguish click from drag so orbiting never deselects.
      if (!downPos) return;
      const dx = event.clientX - downPos[0];
      const dy = event.clientY - downPos[1];
      downPos = null;
      if (dx * dx + dy * dy > 25) return; // was a drag
      if (event.button !== 0) return;

      const rect = dom.getBoundingClientRect();
      this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      this.raycaster.setFromCamera(this.pointer, this.camera);

      const meta = this.scene?.userData.textToThree;
      if (!meta) return;
      const meshes = Object.values(meta.meshesById);
      const hits = this.raycaster.intersectObjects(meshes, false);
      if (hits.length > 0) {
        this.select(hits[0].object.userData.objectId);
      } else {
        this.clearSelection();
      }
    });

    dom.addEventListener('pointermove', (event) => {
      // Hover feedback via cursor only — cheap, no raycast per move.
      dom.style.cursor = this.transformControls.dragging ? 'grabbing' : 'default';
    });
  }
}

const _tmpVec = new THREE.Vector3();
const _tmpQuat = new THREE.Quaternion();
const _tmpScale = new THREE.Vector3();