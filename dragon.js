/* Optional workshop decoration. Delete its script tag to remove it entirely.
 * No chat dependencies: a CDN/WebGL failure leaves the original emoji visible.
 */
(async () => {
  const ENABLE_DRAGON = true; // TRY IT: false restores the emoji, without loading Three.js.
  const COLORS = { skin: 0x86bd54, belly: 0xe7d69b, wing: 0x42684a, horn: 0xffe7bd };
  const host = document.querySelector('.big-dragon');
  if (!ENABLE_DRAGON || !host) return;

  let renderer;
  let observer;
  let resizeObserver;
  let scene;
  let disposed = false;
  const motion = matchMedia('(prefers-reduced-motion: reduce)');

  // GPU resources need explicit cleanup when the welcome panel is removed.
  function dispose() {
    if (disposed) return;
    disposed = true;
    renderer?.setAnimationLoop(null);
    observer?.disconnect();
    resizeObserver?.disconnect();
    document.removeEventListener('visibilitychange', updateMotion);
    motion.removeEventListener('change', updateMotion);
    window.removeEventListener('pagehide', dispose);
    scene?.traverse(object => {
      object.geometry?.dispose();
      if (object.material) object.material.dispose();
    });
    renderer?.dispose();
    renderer?.domElement.remove();
    host.classList.remove('dragon-ready');
  }

  let renderFrame = () => {};
  function updateMotion() {
    renderer?.setAnimationLoop(document.hidden || motion.matches ? null : renderFrame);
    if (!document.hidden) renderFrame(0);
  }

  try {
    // Pinned CDN module: no npm/build step. Internet access is needed for 3D.
    const THREE = await import('https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js');
    if (!host.isConnected) return;
    scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 100);
    camera.position.set(0, 1.7, 8.5);
    camera.lookAt(0, 0.5, 0);
    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.domElement.setAttribute('aria-hidden', 'true');
    scene.add(new THREE.HemisphereLight(0xfff5dc, 0x243620, 2.6));
    const light = new THREE.DirectionalLight(0xffddae, 3);
    light.position.set(-3, 5, 4);
    scene.add(light);
    const rim = new THREE.PointLight(0xb7ef72, 25);
    rim.position.set(3, 1, -2);
    scene.add(rim);

    const dragon = new THREE.Group();
    dragon.rotation.y = -0.22;
    scene.add(dragon);
    // Each part gets a material so disposing the scene is straightforward.
    function part(geometry, color, position, scale = [1, 1, 1], parent = dragon) {
      const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color, roughness: 0.65, flatShading: true }));
      mesh.position.set(...position);
      mesh.scale.set(...scale);
      parent.add(mesh);
      return mesh;
    }
    const ball = () => new THREE.SphereGeometry(1, 20, 14);
    part(ball(), COLORS.skin, [0, 0, 0], [0.7, 0.87, 0.55]);
    part(ball(), COLORS.belly, [0, -0.05, 0.44], [0.46, 0.63, 0.17]);
    const head = new THREE.Group();
    head.position.set(0, 1.02, 0.12);
    dragon.add(head);
    part(ball(), COLORS.skin, [0, 0, 0], [0.76, 0.65, 0.61], head);
    part(ball(), COLORS.skin, [0, -0.24, 0.5], [0.6, 0.32, 0.43], head);
    part(ball(), COLORS.belly, [0, -0.4, 0.49], [0.48, 0.09, 0.32], head);
    for (const side of [-1, 1]) {
      part(ball(), 0xfff9df, [side * 0.37, 0.1, 0.5], [0.23, 0.26, 0.12], head);
      part(ball(), 0x152416, [side * 0.36, 0.1, 0.605], [0.075, 0.16, 0.04], head);
      part(ball(), 0xffffff, [side * 0.36 - 0.025, 0.17, 0.64], [0.028, 0.04, 0.015], head);
      part(ball(), 0x304528, [side * 0.23, -0.18, 0.87], [0.055, 0.045, 0.02], head);
      const horn = part(new THREE.ConeGeometry(0.17, 0.65, 7), COLORS.horn, [side * 0.5, 0.65, -0.08], [1, 1, 1], head);
      horn.rotation.z = -side * 0.3;
      part(ball(), COLORS.skin, [side * 0.52, -0.7, 0.2], [0.32, 0.22, 0.43]);
      const arm = part(ball(), COLORS.skin, [side * 0.64, 0.05, 0.28], [0.2, 0.45, 0.23]);
      arm.rotation.z = side * 0.4;
    }
    // Wings are editable 2D outlines extruded into thin 3D membranes.
    const wings = [];
    for (const side of [-1, 1]) {
      const wing = new THREE.Group();
      wing.position.set(side * 0.48, 0.42, -0.25);
      wing.scale.x = side;
      dragon.add(wing);
      const shape = new THREE.Shape();
      shape.moveTo(0, 0);
      shape.lineTo(0.75, 1.05);
      shape.lineTo(1.7, 0.65);
      shape.quadraticCurveTo(1.05, 0.48, 1.4, -0.12);
      shape.quadraticCurveTo(0.7, 0.18, 0.67, -0.52);
      shape.lineTo(0, -0.2);
      const geometry = new THREE.ExtrudeGeometry(shape, { depth: 0.055, bevelEnabled: false });
      part(geometry, COLORS.wing, [0, 0, 0], [1, 1, 1], wing);
      wings.push(wing);
    }
    const tailCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(0, -0.55, -0.3), new THREE.Vector3(0.8, -0.7, -0.8),
      new THREE.Vector3(1.25, -0.55, -0.7), new THREE.Vector3(1.45, -0.15, -0.5)
    ]);
    part(new THREE.TubeGeometry(tailCurve, 20, 0.14, 8, false), COLORS.skin, [0, 0, 0]);
    part(new THREE.ConeGeometry(0.23, 0.4, 4), COLORS.horn, [1.45, 0, -0.5]);

    // Small emissive particles provide the ember glow without postprocessing.
    const embers = Array.from({ length: 16 }, (_, i) => {
      const mesh = new THREE.Mesh(new THREE.SphereGeometry(0.025, 6, 6),
        new THREE.MeshBasicMaterial({ color: i % 2 ? 0xffc574 : 0xb7ef72 }));
      scene.add(mesh);
      return mesh;
    });
    renderFrame = milliseconds => {
      const t = motion.matches ? 0 : milliseconds * 0.001;
      dragon.position.y = Math.sin(t * 1.6) * 0.07;
      head.rotation.z = Math.sin(t * 0.8) * 0.045;
      wings.forEach((wing, i) => { wing.rotation.y = (i ? -1 : 1) * (0.25 + Math.sin(t * 2) * 0.15); });
      embers.forEach((ember, i) => {
        const phase = i * 2.4;
        ember.position.set(Math.sin(phase + t * 0.2) * 2.2, ((i * 0.31 + t * 0.24) % 3.4) - 1, Math.cos(phase) * 1.3);
      });
      renderer.render(scene, camera);
    };
    host.appendChild(renderer.domElement);
    host.classList.add('dragon-ready');
    const resize = () => {
      const width = host.clientWidth;
      const height = host.clientHeight;
      if (!width || !height) return;
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderFrame(0);
    };
    resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(host);
    // The existing chat removes the hero on the first message; release the GPU.
    observer = new MutationObserver(() => { if (!host.isConnected) dispose(); });
    observer.observe(document.getElementById('messages'), { childList: true });
    renderer.domElement.addEventListener('webglcontextlost', event => { event.preventDefault(); dispose(); });
    document.addEventListener('visibilitychange', updateMotion);
    motion.addEventListener('change', updateMotion);
    window.addEventListener('pagehide', dispose);
    resize();
    updateMotion();
  } catch (error) {
    dispose();
    console.info('Optional dragon unavailable; using emoji.', error);
  }
})();
