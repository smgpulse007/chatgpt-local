import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader";
import { pickBlendshapeWeights, type VisemeEventPayload } from "./viseme-mapping";
import type { RealtimeSession } from "./webrtc";

export class AvatarController {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private clock: THREE.Clock;
  private model: THREE.Object3D | null = null;
  private morphMeshes: THREE.SkinnedMesh[] = [];
  private visemeSchedule: VisemeEventPayload[] = [];
  private visemeStart = 0;
  private speaking = false;
  private captionEl: HTMLDivElement;
  private session: RealtimeSession | null = null;

  constructor(canvas: HTMLCanvasElement, captionEl: HTMLDivElement) {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x020617);
    this.camera = new THREE.PerspectiveCamera(35, canvas.clientWidth / canvas.clientHeight, 0.1, 100);
    this.camera.position.set(0, 1.5, 3);

    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.setSize(canvas.clientWidth, canvas.clientHeight);

    const light = new THREE.DirectionalLight(0xffffff, 1.2);
    light.position.set(1, 2, 2);
    this.scene.add(light);
    this.scene.add(new THREE.AmbientLight(0x404040));

    this.clock = new THREE.Clock();
    this.captionEl = captionEl;

    window.addEventListener("resize", () => this.onResize(canvas));

    this.loadAvatar();
  }

  attachSession(session: RealtimeSession) {
    this.session = session;
  }

  detachSession() {
    this.session = null;
    this.queueVisemes([]);
  }

  private async loadAvatar() {
    const loader = new GLTFLoader();
    try {
      const gltf = await loader.loadAsync("/avatar.glb");
      this.model = gltf.scene;
      this.scene.add(gltf.scene);
      gltf.scene.traverse((obj) => {
        const mesh = obj as THREE.Mesh;
        if ((mesh as any).morphTargetDictionary) {
          this.morphMeshes.push(mesh as THREE.SkinnedMesh);
        }
      });
    } catch (err) {
      console.error("Failed to load avatar.glb", err);
    }
  }

  queueVisemes(events: VisemeEventPayload[]) {
    if (!events.length) {
      this.visemeSchedule = [
        { t: 0, viseme: "REST", weight: 0, blendshapes: {} }
      ];
    } else {
      this.visemeSchedule = events;
    }
    this.visemeStart = performance.now();
  }

  setCaption(text: string) {
    this.captionEl.textContent = text;
  }

  setSpeaking(active: boolean) {
    this.speaking = active;
  }

  start() {
    const tick = () => {
      requestAnimationFrame(tick);
      this.update();
      this.renderer.render(this.scene, this.camera);
    };
    tick();
  }

  private update() {
    const elapsed = (performance.now() - this.visemeStart) / 1000;
    const weights = pickBlendshapeWeights(this.visemeSchedule, elapsed);
    if (this.morphMeshes.length) {
      this.morphMeshes.forEach((mesh) => {
        const dict = mesh.morphTargetDictionary ?? {};
        const influences = mesh.morphTargetInfluences ?? [];
        Object.entries(dict).forEach(([key, index]) => {
          const target = weights[key] ?? 0;
          influences[index] = THREE.MathUtils.lerp(influences[index] ?? 0, target, 0.6);
        });
      });
    }
    this.applyIdleMotion();
  }

  private applyIdleMotion() {
    if (!this.model) {
      return;
    }
    const time = this.clock.getElapsedTime();
    const intensity = this.speaking ? 1.5 : 1.0;
    const bob = Math.sin(time * 1.2 * intensity) * 0.01;
    this.model.position.y = bob;
  }

  private onResize(canvas: HTMLCanvasElement) {
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    this.camera.aspect = width / Math.max(height, 1);
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }
}
