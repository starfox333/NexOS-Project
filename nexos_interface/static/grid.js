/**
 * NexOS v3 -- Frontend Three.js
 * Visualisation 3D : ISOs, grille energetique, signaux, Minerve
 */

// ====================================================
//  SCENE THREE.JS
// ====================================================

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x000a12, 0.0015);

const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 1, 2000);
camera.position.set(250, 120, 400);
camera.lookAt(250, 0, 250);

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
const sceneEl = document.getElementById('scene');
renderer.setSize(sceneEl.clientWidth || window.innerWidth, sceneEl.clientHeight || window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x000508);
sceneEl.appendChild(renderer.domElement);

const ambient = new THREE.AmbientLight(0x003344, 0.6);
scene.add(ambient);
const dirLight = new THREE.DirectionalLight(0x00ffd5, 0.3);
dirLight.position.set(100, 200, 100);
scene.add(dirLight);

// ====================================================
//  SOL -- Grille Tron
// ====================================================

const GRID_SIZE = 500;
const GRID_CENTER = GRID_SIZE / 2;

const gridHelper = new THREE.GridHelper(GRID_SIZE, 50, 0x003322, 0x001a11);
gridHelper.position.set(GRID_CENTER, 0, GRID_CENTER);
scene.add(gridHelper);

const floorGeo = new THREE.PlaneGeometry(GRID_SIZE, GRID_SIZE);
const floorMat = new THREE.MeshStandardMaterial({
  color: 0x000a0a, metalness: 0.9, roughness: 0.2, transparent: true, opacity: 0.8
});
const floor = new THREE.Mesh(floorGeo, floorMat);
floor.rotation.x = -Math.PI / 2;
floor.position.set(GRID_CENTER, -0.1, GRID_CENTER);
scene.add(floor);

let tronFloorMesh = null;  // Sol GLB -- remplace le sol procedural apres chargement

function loadGridFloor() {
  if (typeof THREE.GLTFLoader === 'undefined') return;
  const loader = new THREE.GLTFLoader();
  loader.load('/models/tron_grid_floor.glb',
    (gltf) => {
      const model = gltf.scene;

      // Dimensionner pour couvrir exactement GRID_SIZE x GRID_SIZE
      const box = new THREE.Box3().setFromObject(model);
      const size = new THREE.Vector3();
      box.getSize(size);
      const scaleX = GRID_SIZE / (size.x || 1);
      const scaleZ = GRID_SIZE / (size.z || 1);
      const scale = Math.min(scaleX, scaleZ);  // uniforme -- garde les proportions
      model.scale.setScalar(scale);

      // Centrer sur le sol de la scene
      const box2 = new THREE.Box3().setFromObject(model);
      const center = new THREE.Vector3();
      box2.getCenter(center);
      model.position.x += GRID_CENTER - center.x;
      model.position.z += GRID_CENTER - center.z;
      model.position.y -= box2.min.y;  // poser au sol (y=0)

      scene.add(model);
      tronFloorMesh = model;

      // Masquer le sol procedural
      gridHelper.visible = false;
      floor.visible = false;

      console.log('[NexOS] Sol Tron GLB charge');
    },
    undefined,
    (err) => console.warn('[NexOS] Echec chargement sol Tron:', err.message || err)
  );
}

// ====================================================
//  CAMERA CONTROLS (ZQSD + orbit souris)
// ====================================================

let camAngle = 0;
let camRadius = 250;
let camHeight = 120;
let camCenterX = GRID_CENTER;
let camCenterZ = GRID_CENTER;
let autoRotate = true;
let mouseDown = false;
let lastMX = 0, lastMY = 0;

// Clavier ZQSD
const keysPressed = {};
window.addEventListener('keydown', (e) => {
  keysPressed[e.key.toLowerCase()] = true;
});
window.addEventListener('keyup', (e) => {
  keysPressed[e.key.toLowerCase()] = false;
});

// Souris : orbite (clic + drag)
renderer.domElement.addEventListener('mousedown', (e) => {
  mouseDown = true; lastMX = e.clientX; lastMY = e.clientY;
  autoRotate = false;
});
window.addEventListener('mouseup', () => mouseDown = false);
window.addEventListener('mousemove', (e) => {
  if (!mouseDown) return;
  camAngle += (e.clientX - lastMX) * 0.005;
  camHeight = Math.max(10, Math.min(250, camHeight - (e.clientY - lastMY) * 0.5));
  lastMX = e.clientX; lastMY = e.clientY;
});
renderer.domElement.addEventListener('wheel', (e) => {
  camRadius = Math.max(20, Math.min(800, camRadius + e.deltaY * 0.2));
});

function updateCamera() {
  // Ne pas bouger si on tape dans le chat
  const ci = document.getElementById('chat-input');
  if (ci && ci._focused) {
    if (autoRotate) camAngle += 0.002;
    camera.position.x = camCenterX + Math.cos(camAngle) * camRadius;
    camera.position.z = camCenterZ + Math.sin(camAngle) * camRadius;
    camera.position.y = camHeight;
    camera.lookAt(camCenterX, 0, camCenterZ);
    return;
  }
  // ZQSD deplacement du centre d'orbite
  const moveSpeed = 1.8;
  // Direction avant = de la camera vers le centre (projete en XZ)
  const fwdX = -Math.cos(camAngle);
  const fwdZ = -Math.sin(camAngle);
  // Direction droite = perpendiculaire (produit vectoriel)
  const rightX = Math.sin(camAngle);
  const rightZ = -Math.cos(camAngle);

  let moved = false;
  if (keysPressed['z'] || keysPressed['arrowup']) {
    camCenterX += fwdX * moveSpeed;
    camCenterZ += fwdZ * moveSpeed;
    moved = true;
  }
  if (keysPressed['s'] || keysPressed['arrowdown']) {
    camCenterX -= fwdX * moveSpeed;
    camCenterZ -= fwdZ * moveSpeed;
    moved = true;
  }
  if (keysPressed['q'] || keysPressed['arrowleft']) {
    camCenterX -= rightX * moveSpeed;
    camCenterZ -= rightZ * moveSpeed;
    moved = true;
  }
  if (keysPressed['d'] || keysPressed['arrowright']) {
    camCenterX += rightX * moveSpeed;
    camCenterZ += rightZ * moveSpeed;
    moved = true;
  }
  // Espace = monter, Shift = descendre
  if (keysPressed[' ']) { camHeight = Math.min(250, camHeight + 1.5); moved = true; }
  if (keysPressed['shift']) { camHeight = Math.max(10, camHeight - 1.5); moved = true; }

  if (moved) autoRotate = false;

  // Limites de la grille (avec marge)
  camCenterX = Math.max(-50, Math.min(GRID_SIZE + 50, camCenterX));
  camCenterZ = Math.max(-50, Math.min(GRID_SIZE + 50, camCenterZ));

  // Auto-rotation lente
  if (autoRotate) camAngle += 0.002;

  // Position orbitale autour du centre
  camera.position.x = camCenterX + Math.cos(camAngle) * camRadius;
  camera.position.z = camCenterZ + Math.sin(camAngle) * camRadius;
  camera.position.y = camHeight;
  camera.lookAt(camCenterX, 0, camCenterZ);
}

// ====================================================
//  ISO MESHES (pool reutilise)
// ====================================================

const isoGeo = new THREE.SphereGeometry(1, 12, 12);
const isoPool = [];
const isoMaterials = {};

function getIsoMaterial(energy, maxEnergy) {
  const ratio = energy / Math.max(1, maxEnergy);
  let color;
  if (ratio > 0.7) color = 0x00ffd5;
  else if (ratio > 0.4) color = 0xff8800;
  else color = 0xff4444;

  if (!isoMaterials[color]) {
    isoMaterials[color] = new THREE.MeshBasicMaterial({
      color: color, transparent: true, opacity: 0.85
    });
  }
  return isoMaterials[color];
}

function updateIsoMeshes(isos, minervePos, tronPos) {
  for (const m of isoPool) m.visible = false;

  for (let i = 0; i < isos.length; i++) {
    const iso = isos[i];
    let mesh;
    if (i < isoPool.length) {
      mesh = isoPool[i];
    } else {
      mesh = new THREE.Mesh(isoGeo, new THREE.MeshBasicMaterial({ color: 0x00ffd5 }));
      scene.add(mesh);
      isoPool.push(mesh);
    }

    mesh.visible = true;
    mesh.position.set(iso.x, 1.5 + Math.sin(Date.now() * 0.003 + iso.id) * 0.3, iso.z);
    mesh.material = getIsoMaterial(iso.energy, iso.max_energy || 200);

    // Taille selon generation
    const s = 0.8 + Math.min(iso.generation, 10) * 0.1;
    mesh.scale.set(s, s, s);

    // Boost d'eclat pres de Minerve (or)
    if (minervePos) {
      const dx = Math.abs(iso.x - minervePos.x);
      const dz = Math.abs(iso.z - minervePos.z);
      if (dx <= 15 && dz <= 15) {
        mesh.material = new THREE.MeshBasicMaterial({
          color: 0x00ffd5, transparent: true, opacity: 1.0
        });
        const sBoosted = s * 1.2;
        mesh.scale.set(sBoosted, sBoosted, sBoosted);
      }
    }

    // Halo cyan si protege par Tron
    if (tronPos) {
      const tdx = Math.abs(iso.x - tronPos.x);
      const tdz = Math.abs(iso.z - tronPos.z);
      if (tdx <= 12 && tdz <= 12) {
        mesh.material = new THREE.MeshBasicMaterial({
          color: 0x00e5ff, transparent: true, opacity: 0.95
        });
        const sProtected = s * 1.1;
        mesh.scale.set(sProtected, sProtected, sProtected);
      }
    }
  }
}

// ====================================================
//  ENERGY MAP (heatmap au sol)
// ====================================================

const energyDots = [];
const dotGeo = new THREE.PlaneGeometry(3.5, 3.5);

function updateEnergyMap(energyMap) {
  for (const d of energyDots) d.visible = false;

  for (let i = 0; i < energyMap.length; i++) {
    const cell = energyMap[i];
    let dot;
    if (i < energyDots.length) {
      dot = energyDots[i];
    } else {
      const mat = new THREE.MeshBasicMaterial({
        color: 0x00ffd5, transparent: true, opacity: 0.15, side: THREE.DoubleSide
      });
      dot = new THREE.Mesh(dotGeo, mat);
      dot.rotation.x = -Math.PI / 2;
      dot.position.y = 0.02;
      scene.add(dot);
      energyDots.push(dot);
    }

    dot.visible = true;
    dot.position.x = cell.x;
    dot.position.z = cell.z;
    const intensity = Math.min(1, cell.e / 150);
    dot.material.opacity = 0.03 + intensity * 0.15;
    const r = Math.round((1 - intensity) * 255);
    const g = Math.round(intensity * 255);
    dot.material.color.setRGB(r / 255, g / 255, 0.5);
  }
}

// ====================================================
//  SIGNALS (visualisation des communications)
// ====================================================

const signalMeshes = [];
const signalGeo = new THREE.RingGeometry(0.5, 2, 16);

const SIGNAL_COLORS = {
  'FOOD_HERE':  0x00ff00,
  'DANGER':     0xff4444,
  'COME_HERE':  0x00aaff,
  'NEED_HELP':  0xff8800,
  'WISDOM':     0xffd700,
  'PROTECTION': 0x00e5ff
};

function updateSignals(signals) {
  for (const m of signalMeshes) m.visible = false;
  if (!signals) return;

  for (let i = 0; i < signals.length; i++) {
    const sig = signals[i];
    let mesh;

    if (i < signalMeshes.length) {
      mesh = signalMeshes[i];
    } else {
      const mat = new THREE.MeshBasicMaterial({
        color: 0x00ff00, transparent: true, opacity: 0.4, side: THREE.DoubleSide
      });
      mesh = new THREE.Mesh(signalGeo, mat);
      mesh.rotation.x = -Math.PI / 2;
      scene.add(mesh);
      signalMeshes.push(mesh);
    }

    mesh.visible = true;
    mesh.position.set(sig.x, 0.5, sig.z);

    const color = SIGNAL_COLORS[sig.type] || 0xffffff;
    mesh.material.color.setHex(color);

    // Pulse animation
    const pulse = 0.3 + Math.sin(Date.now() * 0.01 + i) * 0.15;
    mesh.material.opacity = pulse * (sig.ttl / 20);

    const s = sig.radius / 5;
    mesh.scale.set(s, s, s);
  }
}

// ====================================================
//  MINERVE (cristal dore -- gardienne du savoir)
// ====================================================

let minerveMesh = null;
let minerveAura = null;
let minerveLabel = null;

function initMinerve() {
  // Corps : octahedron dore
  const geo = new THREE.OctahedronGeometry(3, 0);
  const mat = new THREE.MeshBasicMaterial({
    color: 0xffd700, transparent: true, opacity: 0.9
  });
  minerveMesh = new THREE.Mesh(geo, mat);
  minerveMesh.position.set(100, 5, 100);
  scene.add(minerveMesh);

  // Aura
  const auraGeo = new THREE.RingGeometry(2, 16, 32);
  const auraMat = new THREE.MeshBasicMaterial({
    color: 0xffd700, transparent: true, opacity: 0.12, side: THREE.DoubleSide
  });
  minerveAura = new THREE.Mesh(auraGeo, auraMat);
  minerveAura.rotation.x = -Math.PI / 2;
  minerveAura.position.set(100, 0.3, 100);
  scene.add(minerveAura);

  // Label "MINERVE"
  const canvas = document.createElement('canvas');
  canvas.width = 256; canvas.height = 64;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#ffd700';
  ctx.font = 'bold 28px monospace';
  ctx.textAlign = 'center';
  ctx.fillText('MINERVE', 128, 40);

  const tex = new THREE.CanvasTexture(canvas);
  const spMat = new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.8 });
  minerveLabel = new THREE.Sprite(spMat);
  minerveLabel.scale.set(12, 3, 1);
  minerveLabel.position.set(100, 12, 100);
  scene.add(minerveLabel);
}

function updateMinerve(minerveData) {
  if (!minerveData || !minerveData.enabled) {
    if (minerveMesh) minerveMesh.visible = false;
    if (minerveAura) minerveAura.visible = false;
    if (minerveLabel) minerveLabel.visible = false;
    return;
  }

  if (!minerveMesh) initMinerve();

  const mx = minerveData.x;
  const mz = minerveData.z;

  // Flottement + rotation
  const time = Date.now() * 0.001;
  const floatY = 5 + Math.sin(time) * 1.5;

  minerveMesh.visible = true;
  minerveMesh.position.set(mx, floatY, mz);
  minerveMesh.rotation.y = time * 0.5;
  minerveMesh.rotation.x = Math.sin(time * 0.3) * 0.2;

  // Aura pulse
  minerveAura.visible = true;
  minerveAura.position.set(mx, 0.3, mz);
  const auraScale = 1 + Math.sin(time * 2) * 0.15;
  minerveAura.scale.set(auraScale, auraScale, auraScale);
  minerveAura.material.opacity = 0.08 + Math.sin(time * 3) * 0.04;

  // Label
  minerveLabel.visible = true;
  minerveLabel.position.set(mx, floatY + 5, mz);
}

// ====================================================
//  TRON (icosahedron cyan -- protecteur des ISOs)
// ====================================================

let tronMesh = null;
let tronAura = null;
let tronLabel = null;
let tronTrailLine = null;
let tronTrailPositions = [];

function initTron() {
  // Corps : icosahedron cyan (armure facettee)
  const geo = new THREE.IcosahedronGeometry(2.5, 0);
  const mat = new THREE.MeshBasicMaterial({
    color: 0x00e5ff, transparent: true, opacity: 0.9
  });
  tronMesh = new THREE.Mesh(geo, mat);
  tronMesh.position.set(50, 4, 50);
  scene.add(tronMesh);

  // Aura de protection (anneau cyan)
  const auraGeo = new THREE.RingGeometry(2, 13, 32);
  const auraMat = new THREE.MeshBasicMaterial({
    color: 0x00e5ff, transparent: true, opacity: 0.10, side: THREE.DoubleSide
  });
  tronAura = new THREE.Mesh(auraGeo, auraMat);
  tronAura.rotation.x = -Math.PI / 2;
  tronAura.position.set(50, 0.3, 50);
  scene.add(tronAura);

  // Label "TRON"
  const canvas = document.createElement('canvas');
  canvas.width = 256; canvas.height = 64;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#00e5ff';
  ctx.font = 'bold 32px monospace';
  ctx.textAlign = 'center';
  ctx.fillText('TRON', 128, 42);

  const tex = new THREE.CanvasTexture(canvas);
  const spMat = new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.85 });
  tronLabel = new THREE.Sprite(spMat);
  tronLabel.scale.set(10, 2.5, 1);
  tronLabel.position.set(50, 10, 50);
  scene.add(tronLabel);

  // Lightcycle trail (ligne lumineuse)
  const trailMat = new THREE.LineBasicMaterial({
    color: 0x00e5ff, transparent: true, opacity: 0.6, linewidth: 2
  });
  const trailGeo = new THREE.BufferGeometry();
  trailGeo.setAttribute('position', new THREE.Float32BufferAttribute([], 3));
  tronTrailLine = new THREE.Line(trailGeo, trailMat);
  scene.add(tronTrailLine);
}

function updateTron(tronData) {
  if (!tronData || !tronData.enabled) {
    if (tronMesh) tronMesh.visible = false;
    if (tronAura) tronAura.visible = false;
    if (tronLabel) tronLabel.visible = false;
    if (tronTrailLine) tronTrailLine.visible = false;
    return;
  }

  if (!tronMesh) initTron();

  const tx = tronData.x;
  const tz = tronData.z;
  const time = Date.now() * 0.001;

  // Corps -- rotation rapide (guerrier)
  const floatY = 4 + Math.sin(time * 1.5) * 0.8;
  tronMesh.visible = true;
  tronMesh.position.set(tx, floatY, tz);
  tronMesh.rotation.y = time * 1.2;
  tronMesh.rotation.x = time * 0.4;

  // Pulse couleur en urgence
  if (tronData.mode === 'emergency') {
    const pulse = 0.7 + Math.sin(time * 6) * 0.3;
    tronMesh.material.opacity = pulse;
    tronMesh.scale.set(1.3, 1.3, 1.3);
  } else {
    tronMesh.material.opacity = 0.9;
    tronMesh.scale.set(1, 1, 1);
  }

  // Aura de protection -- pulse rapide
  tronAura.visible = true;
  tronAura.position.set(tx, 0.3, tz);
  const auraPulse = 1 + Math.sin(time * 3) * 0.2;
  tronAura.scale.set(auraPulse, auraPulse, auraPulse);
  tronAura.material.opacity = 0.06 + Math.sin(time * 4) * 0.04;

  // Label
  tronLabel.visible = true;
  tronLabel.position.set(tx, floatY + 5, tz);

  // Lightcycle trail
  const trail = tronData.trail || [];
  if (trail.length > 1) {
    const verts = [];
    for (let i = 0; i < trail.length; i++) {
      verts.push(trail[i].x, 1.5, trail[i].z);
    }
    // Ajouter position actuelle a la fin
    verts.push(tx, 1.5, tz);

    tronTrailLine.visible = true;
    const posAttr = new THREE.Float32BufferAttribute(verts, 3);
    tronTrailLine.geometry.setAttribute('position', posAttr);
    tronTrailLine.geometry.attributes.position.needsUpdate = true;
  } else {
    tronTrailLine.visible = false;
  }
}

// ====================================================
//  SYMMETRA (dodecahedron magenta -- batisseuse d'abris)
// ====================================================

let symmetraMesh = null;
let symmetraAura = null;
let symmetraLabel = null;
const structureMeshes = [];

// Correspondance type de structure -> modele GLB Tron
const MODEL_MAP = {
  shelter:      'tron_buildings_1.glb',    // Architecture Tron generique
  library:      'tron_iso_city.glb',       // Cite ISO = temple du savoir
  energy_plant: 'tron_disk.glb',           // Disque identite = source d'energie
  comm_tower:   'tron_buildings_1.glb',    // Batiments Tron (tour de comm)
  arena:        'end_of_line_club.glb',    // End of Line Club = arene parfaite
};
const gltfModels = {};  // cache: filename -> THREE.Group (template normalise)

// Couleurs par type de structure (Tron style)
const STRUCT_COLORS = {
  shelter:      0xff44ff,  // magenta
  library:      0xffd700,  // gold (Minerve)
  energy_plant: 0x00ff88,  // vert neon
  comm_tower:   0x4488ff,  // bleu
  arena:        0xff6633,  // orange
};

function initSymmetra() {
  // Corps : dodecahedron magenta (12 faces -- architecte)
  const geo = new THREE.DodecahedronGeometry(2.5, 0);
  const mat = new THREE.MeshBasicMaterial({
    color: 0xff44ff, transparent: true, opacity: 0.9
  });
  symmetraMesh = new THREE.Mesh(geo, mat);
  symmetraMesh.position.set(150, 5, 150);
  scene.add(symmetraMesh);

  // Aura de construction
  const auraGeo = new THREE.RingGeometry(2, 13, 6); // Hexagonal
  const auraMat = new THREE.MeshBasicMaterial({
    color: 0xff44ff, transparent: true, opacity: 0.10, side: THREE.DoubleSide
  });
  symmetraAura = new THREE.Mesh(auraGeo, auraMat);
  symmetraAura.rotation.x = -Math.PI / 2;
  symmetraAura.position.set(150, 0.3, 150);
  scene.add(symmetraAura);

  // Label "SYMMETRA"
  const canvas = document.createElement('canvas');
  canvas.width = 320; canvas.height = 64;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#ff44ff';
  ctx.font = 'bold 28px monospace';
  ctx.textAlign = 'center';
  ctx.fillText('SYMMETRA', 160, 42);

  const tex = new THREE.CanvasTexture(canvas);
  const spMat = new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.85 });
  symmetraLabel = new THREE.Sprite(spMat);
  symmetraLabel.scale.set(12, 3, 1);
  symmetraLabel.position.set(150, 12, 150);
  scene.add(symmetraLabel);
}

function updateSymmetra(symData) {
  if (!symData || !symData.enabled) {
    if (symmetraMesh) symmetraMesh.visible = false;
    if (symmetraAura) symmetraAura.visible = false;
    if (symmetraLabel) symmetraLabel.visible = false;
    return;
  }

  if (!symmetraMesh) initSymmetra();

  const sx = symData.x;
  const sz = symData.z;
  const time = Date.now() * 0.001;

  // Corps -- rotation lente methodique
  const floatY = 5 + Math.sin(time * 0.8) * 1.0;
  symmetraMesh.visible = true;
  symmetraMesh.position.set(sx, floatY, sz);
  symmetraMesh.rotation.y = time * 0.3;
  symmetraMesh.rotation.z = Math.sin(time * 0.2) * 0.15;

  // Mode building = pulse
  if (symData.mode === 'building') {
    const pulse = 0.7 + Math.sin(time * 5) * 0.3;
    symmetraMesh.material.opacity = pulse;
    symmetraMesh.scale.set(1.3, 1.3, 1.3);
  } else {
    symmetraMesh.material.opacity = 0.9;
    symmetraMesh.scale.set(1, 1, 1);
  }

  // Aura
  symmetraAura.visible = true;
  symmetraAura.position.set(sx, 0.3, sz);
  const auraPulse = 1 + Math.sin(time * 2) * 0.15;
  symmetraAura.scale.set(auraPulse, auraPulse, auraPulse);

  // Label
  symmetraLabel.visible = true;
  symmetraLabel.position.set(sx, floatY + 5, sz);

  // Structures -- batiments Tron-style
  const structList = symData.structures || symData.shelters || [];
  updateStructures(structList);

  // Autoroutes suspendues entre structures
  updateLightways(structList);
}

// ====================================================
//  DAEDALUS (icosahedron violet -- catalyseur d'innovation)
// ====================================================

let daedalusMesh = null;
let daedalusAura = null;
let daedalusLabel = null;
let daedalusSpiralLine = null;

function initDaedalus() {
  // Corps : icosahedron violet (innovation)
  const geo = new THREE.IcosahedronGeometry(3.5, 2);
  const mat = new THREE.MeshBasicMaterial({
    color: 0x9d4edd, transparent: true, opacity: 0.9
  });
  daedalusMesh = new THREE.Mesh(geo, mat);
  daedalusMesh.position.set(250, 5, 125);
  scene.add(daedalusMesh);

  // Aura spiralée (innovation)
  const auraGeo = new THREE.TorusGeometry(4, 0.5, 16, 100);
  const auraMat = new THREE.MeshBasicMaterial({
    color: 0x9d4edd, transparent: true, opacity: 0.12, side: THREE.DoubleSide
  });
  daedalusAura = new THREE.Mesh(auraGeo, auraMat);
  daedalusAura.rotation.x = -Math.PI / 2;
  daedalusAura.position.set(250, 0.3, 125);
  scene.add(daedalusAura);

  // Label "DAEDALUS"
  const canvas = document.createElement('canvas');
  canvas.width = 256; canvas.height = 64;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#9d4edd';
  ctx.font = 'bold 32px Arial';
  ctx.textAlign = 'center';
  ctx.fillText('DAEDALUS', 128, 40);

  const tex = new THREE.CanvasTexture(canvas);
  const spMat = new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.9 });
  daedalusLabel = new THREE.Sprite(spMat);
  daedalusLabel.scale.set(14, 3.5, 1);
  daedalusLabel.position.set(250, 12, 125);
  scene.add(daedalusLabel);

  // Spiral trail
  const spiralMat = new THREE.LineBasicMaterial({
    color: 0x9d4edd, transparent: true, opacity: 0.5, linewidth: 1
  });
  const spiralGeo = new THREE.BufferGeometry();
  spiralGeo.setAttribute('position', new THREE.Float32BufferAttribute([], 3));
  daedalusSpiralLine = new THREE.Line(spiralGeo, spiralMat);
  scene.add(daedalusSpiralLine);
}

function updateDaedalus(daedalusData) {
  if (!daedalusData || !daedalusData.enabled) {
    if (daedalusMesh) daedalusMesh.visible = false;
    if (daedalusAura) daedalusAura.visible = false;
    if (daedalusLabel) daedalusLabel.visible = false;
    if (daedalusSpiralLine) daedalusSpiralLine.visible = false;
    return;
  }

  if (!daedalusMesh) initDaedalus();

  const dx = daedalusData.x;
  const dz = daedalusData.z;
  const time = Date.now() * 0.001;

  // Corps -- rotation rapide (innovation)
  const floatY = 5 + Math.sin(time * 1.3) * 1.2;
  daedalusMesh.visible = true;
  daedalusMesh.position.set(dx, floatY, dz);
  daedalusMesh.rotation.y = time * 0.8;
  daedalusMesh.rotation.x = Math.sin(time * 0.4) * 0.25;
  daedalusMesh.rotation.z = Math.cos(time * 0.5) * 0.2;

  // Aura spirale -- pulse
  daedalusAura.visible = true;
  daedalusAura.position.set(dx, 0.3, dz);
  const auraPulse = 1 + Math.sin(time * 2.5) * 0.2;
  daedalusAura.scale.set(auraPulse, auraPulse, auraPulse);
  daedalusAura.rotation.z = time * 0.3;
  daedalusAura.material.opacity = 0.08 + Math.sin(time * 3) * 0.05;

  // Label
  daedalusLabel.visible = true;
  daedalusLabel.position.set(dx, floatY + 6, dz);

  // Spiral trail (historique de mouvement)
  if (!window.daedalusTrail) {
    window.daedalusTrail = [];
  }
  window.daedalusTrail.push(dx, floatY, dz);
  // Garder seulement les 100 derniers points
  if (window.daedalusTrail.length > 300) {
    window.daedalusTrail = window.daedalusTrail.slice(-300);
  }

  if (window.daedalusTrail.length > 2) {
    daedalusSpiralLine.visible = true;
    const posAttr = new THREE.Float32BufferAttribute(window.daedalusTrail, 3);
    daedalusSpiralLine.geometry.setAttribute('position', posAttr);
    daedalusSpiralLine.geometry.attributes.position.needsUpdate = true;
  }
}

/**
 * Cree le mesh d'une structure a partir d'un modele GLB Tron charge.
 * Garde les elements visuels de base (halo, label) de la version procedurale.
 */
function _createStructureMeshFromGLB(sType, color, radius) {
  const modelFile = MODEL_MAP[sType];
  const template = gltfModels[modelFile];

  // Empreinte lumineuse au sol
  const baseGeo = new THREE.CircleGeometry(radius * 1.2, sType === 'arena' ? 8 : 6);
  const baseMat = new THREE.MeshBasicMaterial({
    color: color, transparent: true, opacity: 0.08, side: THREE.DoubleSide
  });
  const base = new THREE.Mesh(baseGeo, baseMat);
  base.rotation.x = -Math.PI / 2;
  base.position.y = 0.15;
  scene.add(base);

  // Clone du modele GLB (geometries partagees, transforms independants)
  const building = template.clone(true);

  // Dimensionner : faire tenir le modele dans radius * 2 unites
  const box1 = new THREE.Box3().setFromObject(building);
  const size = new THREE.Vector3();
  box1.getSize(size);
  const maxDim = Math.max(size.x, size.y, size.z);
  if (maxDim > 0) {
    building.scale.multiplyScalar((radius * 2.0) / maxDim);
  }

  // Centrer sur le sol (X/Z centre, Y = pose au sol)
  const box2 = new THREE.Box3().setFromObject(building);
  const center = new THREE.Vector3();
  box2.getCenter(center);
  building.position.x -= center.x;
  building.position.z -= center.z;
  building.position.y -= box2.min.y;

  // Transparence + teinte neon Tron sur chaque mesh enfant
  building.traverse(child => {
    if (child.isMesh && child.material) {
      child.material = child.material.clone();
      child.material.transparent = true;
      child.material.opacity = 0.85;
      if (child.material.emissive !== undefined) {
        child.material.emissive.setHex(color);
        child.material.emissiveIntensity = 0.15;
      }
    }
  });

  // Interface .material.opacity pour updateStructures() (Group n'a pas de .material natif)
  const virtualMat = { _opacity: 0.85 };
  Object.defineProperty(virtualMat, 'opacity', {
    get() { return virtualMat._opacity; },
    set(val) {
      virtualMat._opacity = val;
      building.traverse(child => {
        if (child.isMesh && child.material) child.material.opacity = val;
      });
    }
  });
  building.material = virtualMat;

  scene.add(building);

  // Halo atmospherique (identique a la version procedurale)
  const glowGeo = new THREE.SphereGeometry(radius, 16, 8);
  const glowMat = new THREE.MeshBasicMaterial({
    color: color, transparent: true, opacity: 0.04
  });
  const glow = new THREE.Mesh(glowGeo, glowMat);
  glow.position.y = 4;
  scene.add(glow);

  // Label sprite
  const canvas = document.createElement('canvas');
  canvas.width = 160; canvas.height = 80;
  const ctx = canvas.getContext('2d');
  const tex = new THREE.CanvasTexture(canvas);
  const spMat = new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.7 });
  const label = new THREE.Sprite(spMat);
  label.scale.set(8, 4, 1);
  scene.add(label);

  return { base, building, accent: null, glow, label, canvas, ctx, tex, _type: sType };
}

/**
 * Cree le mesh 3D Tron-style pour un type de structure.
 * Buildings sombres avec aretes neon lumineuses.
 * Inspire des cites de la Grille de Tron.
 */
function _createStructureMesh(sType, color, radius) {
  // Utiliser le modele GLB Tron si disponible, sinon geometrie procedurale
  if (MODEL_MAP[sType] && gltfModels[MODEL_MAP[sType]]) {
    return _createStructureMeshFromGLB(sType, color, radius);
  }

  let base, building, accent, glow;

  // Couleur sombre pour le corps du batiment (10% de la couleur neon)
  const darkColor = 0x050510;

  // --- Base au sol : empreinte lumineuse ---
  const baseGeo = new THREE.CircleGeometry(radius * 1.2, sType === 'arena' ? 8 : 6);
  const baseMat = new THREE.MeshBasicMaterial({
    color: color, transparent: true, opacity: 0.08, side: THREE.DoubleSide
  });
  base = new THREE.Mesh(baseGeo, baseMat);
  base.rotation.x = -Math.PI / 2;
  base.position.y = 0.15;
  scene.add(base);

  if (sType === 'shelter') {
    // ABRI : bloc hexagonal bas avec toit -- refuge compact
    const group = new THREE.Group();
    // Corps sombre
    const bodyGeo = new THREE.CylinderGeometry(radius * 0.6, radius * 0.7, 5, 6);
    const bodyMat = new THREE.MeshBasicMaterial({ color: darkColor, transparent: true, opacity: 0.7 });
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    body.position.y = 2.5;
    group.add(body);
    // Aretes neon (wireframe par-dessus)
    const edgeMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.5, wireframe: true });
    const edge = new THREE.Mesh(bodyGeo.clone(), edgeMat);
    edge.position.y = 2.5;
    group.add(edge);
    // Bandes lumineuses horizontales
    for (let h = 1; h <= 4; h += 1.5) {
      const ringGeo = new THREE.RingGeometry(radius * 0.59, radius * 0.62, 6);
      const ringMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.4, side: THREE.DoubleSide });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = -Math.PI / 2;
      ring.position.y = h;
      group.add(ring);
    }
    scene.add(group);
    building = group;

    // Toit cone lumineux
    const roofGeo = new THREE.ConeGeometry(radius * 0.5, 2, 6);
    const roofMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.2 });
    accent = new THREE.Mesh(roofGeo, roofMat);
    accent.position.y = 6;
    scene.add(accent);

  } else if (sType === 'library') {
    // BIBLIOTHEQUE : tour elegante avec octaedre flottant -- temple du savoir
    const group = new THREE.Group();
    // 4 piliers sombres avec aretes dorées
    for (let p = 0; p < 4; p++) {
      const angle = (p / 4) * Math.PI * 2 + Math.PI / 4;
      const px = Math.cos(angle) * radius * 0.45;
      const pz = Math.sin(angle) * radius * 0.45;
      // Pilier sombre
      const pilGeo = new THREE.BoxGeometry(1.2, 10, 1.2);
      const pilMat = new THREE.MeshBasicMaterial({ color: darkColor, transparent: true, opacity: 0.7 });
      const pil = new THREE.Mesh(pilGeo, pilMat);
      pil.position.set(px, 5, pz);
      group.add(pil);
      // Aretes neon
      const pilEdge = new THREE.Mesh(pilGeo.clone(), new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.5, wireframe: true }));
      pilEdge.position.set(px, 5, pz);
      group.add(pilEdge);
      // Ligne lumineuse sur le pilier
      const lineGeo = new THREE.BoxGeometry(0.15, 10, 0.15);
      const lineMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.7 });
      const line = new THREE.Mesh(lineGeo, lineMat);
      line.position.set(px, 5, pz);
      group.add(line);
    }
    // Plateforme entre les piliers
    const platGeo = new THREE.BoxGeometry(radius * 0.9, 0.3, radius * 0.9);
    const platMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.15 });
    const plat = new THREE.Mesh(platGeo, platMat);
    plat.position.y = 8;
    group.add(plat);
    scene.add(group);
    building = group;

    // Octaedre flottant au sommet (cristal de savoir)
    const crystalGeo = new THREE.OctahedronGeometry(2.5, 0);
    const crystalMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.6, wireframe: true });
    accent = new THREE.Mesh(crystalGeo, crystalMat);
    accent.position.y = 12;
    scene.add(accent);

  } else if (sType === 'energy_plant') {
    // CENTRALE : reacteur cylindrique avec torus rotatif
    const group = new THREE.Group();
    // Cylindre sombre (reacteur)
    const coreGeo = new THREE.CylinderGeometry(radius * 0.35, radius * 0.4, 8, 8);
    const coreMat = new THREE.MeshBasicMaterial({ color: darkColor, transparent: true, opacity: 0.7 });
    const core = new THREE.Mesh(coreGeo, coreMat);
    core.position.y = 4;
    group.add(core);
    // Aretes neon
    const coreEdge = new THREE.Mesh(coreGeo.clone(), new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.5, wireframe: true }));
    coreEdge.position.y = 4;
    group.add(coreEdge);
    // Bandes lumineuses de plasma
    for (let h = 1; h <= 7; h += 2) {
      const bandGeo = new THREE.RingGeometry(radius * 0.34, radius * 0.42, 8);
      const bandMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.5, side: THREE.DoubleSide });
      const band = new THREE.Mesh(bandGeo, bandMat);
      band.rotation.x = -Math.PI / 2;
      band.position.y = h;
      group.add(band);
    }
    // Colonne de plasma centrale
    const plasmaGeo = new THREE.CylinderGeometry(0.4, 0.4, 9, 6);
    const plasmaMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.6 });
    const plasma = new THREE.Mesh(plasmaGeo, plasmaMat);
    plasma.position.y = 4.5;
    group.add(plasma);
    scene.add(group);
    building = group;

    // Torus rotatif autour du reacteur
    const torusGeo = new THREE.TorusGeometry(radius * 0.5, 0.5, 6, 12);
    const torusMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.35, wireframe: true });
    accent = new THREE.Mesh(torusGeo, torusMat);
    accent.position.y = 5;
    scene.add(accent);

  } else if (sType === 'comm_tower') {
    // TOUR COMM : gratte-ciel fin avec antenne et sphere emettrice
    const group = new THREE.Group();
    // Tour sombre haute
    const towerGeo = new THREE.BoxGeometry(2, 18, 2);
    const towerMat = new THREE.MeshBasicMaterial({ color: darkColor, transparent: true, opacity: 0.7 });
    const tower = new THREE.Mesh(towerGeo, towerMat);
    tower.position.y = 9;
    group.add(tower);
    // Aretes neon
    const towerEdge = new THREE.Mesh(towerGeo.clone(), new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.5, wireframe: true }));
    towerEdge.position.y = 9;
    group.add(towerEdge);
    // Lignes lumineuses verticales sur les coins
    for (let c = 0; c < 4; c++) {
      const cx = (c < 2 ? 1 : -1) * 0.9;
      const cz = (c % 2 === 0 ? 1 : -1) * 0.9;
      const lineGeo = new THREE.BoxGeometry(0.12, 18, 0.12);
      const lineMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.7 });
      const line = new THREE.Mesh(lineGeo, lineMat);
      line.position.set(cx, 9, cz);
      group.add(line);
    }
    // Bandes horizontales clignotantes
    for (let h = 3; h <= 16; h += 3) {
      const bandGeo = new THREE.BoxGeometry(2.3, 0.15, 2.3);
      const bandMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.3 });
      const band = new THREE.Mesh(bandGeo, bandMat);
      band.position.y = h;
      group.add(band);
    }
    scene.add(group);
    building = group;

    // Sphere emettrice au sommet
    const sphereGeo = new THREE.SphereGeometry(1.5, 8, 8);
    const sphereMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.5 });
    accent = new THREE.Mesh(sphereGeo, sphereMat);
    accent.position.y = 19;
    scene.add(accent);

  } else if (sType === 'arena') {
    // ARENE : colisee octogonal avec murs et zone combat
    const group = new THREE.Group();
    // Murs sombres octogonaux
    const wallGeo = new THREE.CylinderGeometry(radius * 0.7, radius * 0.75, 5, 8, 1, true);
    const wallMat = new THREE.MeshBasicMaterial({ color: darkColor, transparent: true, opacity: 0.6 });
    const wall = new THREE.Mesh(wallGeo, wallMat);
    wall.position.y = 2.5;
    group.add(wall);
    // Aretes neon
    const wallEdge = new THREE.Mesh(wallGeo.clone(), new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.4, wireframe: true }));
    wallEdge.position.y = 2.5;
    group.add(wallEdge);
    // Bandes lumineuses sur les murs
    for (let h = 1; h <= 4; h += 1.5) {
      const rGeo = new THREE.RingGeometry(radius * 0.69, radius * 0.72, 8);
      const rMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.45, side: THREE.DoubleSide });
      const r = new THREE.Mesh(rGeo, rMat);
      r.rotation.x = -Math.PI / 2;
      r.position.y = h;
      group.add(r);
    }
    // Sol de l'arene lumineux
    const floorGeo = new THREE.CircleGeometry(radius * 0.65, 8);
    const floorMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.08, side: THREE.DoubleSide });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = 0.3;
    group.add(floor);
    scene.add(group);
    building = group;

    // Anneau flottant au-dessus (hologramme)
    const ringGeo = new THREE.TorusGeometry(radius * 0.5, 0.3, 6, 8);
    const ringMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.3, wireframe: true });
    accent = new THREE.Mesh(ringGeo, ringMat);
    accent.rotation.x = Math.PI / 2;
    accent.position.y = 6;
    scene.add(accent);
  }

  // --- Halo lumineux atmospherique (style Tron) ---
  const glowGeo = new THREE.SphereGeometry(radius, 16, 8);
  const glowMat = new THREE.MeshBasicMaterial({
    color: color, transparent: true, opacity: 0.04
  });
  glow = new THREE.Mesh(glowGeo, glowMat);
  glow.position.y = 4;
  scene.add(glow);

  // --- Label sprite ---
  const canvas = document.createElement('canvas');
  canvas.width = 160; canvas.height = 80;
  const ctx = canvas.getContext('2d');
  const tex = new THREE.CanvasTexture(canvas);
  const spMat = new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.7 });
  const label = new THREE.Sprite(spMat);
  label.scale.set(8, 4, 1);
  scene.add(label);

  return { base, building, accent, glow, label, canvas, ctx, tex, _type: sType };
}

function updateStructures(structures) {
  // Masquer les anciens
  for (const m of structureMeshes) {
    if (m.base) m.base.visible = false;
    if (m.building) m.building.visible = false;
    if (m.accent) m.accent.visible = false;
    if (m.glow) m.glow.visible = false;
    if (m.label) m.label.visible = false;
  }

  for (let i = 0; i < structures.length; i++) {
    const s = structures[i];
    const sType = s.type || 'shelter';
    const color = STRUCT_COLORS[sType] || 0xff44ff;
    const colorHex = s.color || '#ff44ff';
    let group;

    if (i < structureMeshes.length) {
      group = structureMeshes[i];
      // Si le type a change, reconstruire
      if (group._type !== sType) {
        if (group.base) scene.remove(group.base);
        if (group.building) scene.remove(group.building);
        if (group.accent) scene.remove(group.accent);
        if (group.glow) scene.remove(group.glow);
        if (group.label) scene.remove(group.label);
        group = null;
        structureMeshes[i] = null;
      }
    }

    if (!group) {
      group = _createStructureMesh(sType, color, s.radius || 8);
      group._type = sType;
      if (i < structureMeshes.length) {
        structureMeshes[i] = group;
      } else {
        structureMeshes.push(group);
      }
    }

    // Rendre visible
    if (group.base) group.base.visible = true;
    if (group.building) group.building.visible = true;
    if (group.accent) group.accent.visible = true;
    if (group.glow) group.glow.visible = true;
    if (group.label) group.label.visible = true;

    // Positionner
    const px = s.x, pz = s.z;
    if (group.base) { group.base.position.x = px; group.base.position.z = pz; }
    if (group.building) { group.building.position.x = px; group.building.position.z = pz; }
    if (group.accent) { group.accent.position.x = px; group.accent.position.z = pz; }
    if (group.glow) { group.glow.position.set(px, 3, pz); }
    if (group.label) { group.label.position.set(px, 12, pz); }

    // Sante = opacite + scale
    const health = s.health || 1;
    if (group.base) group.base.material.opacity = 0.05 + health * 0.1;
    if (group.building) group.building.material.opacity = 0.15 + health * 0.35;
    if (group.accent) group.accent.material.opacity = 0.2 + health * 0.4;
    if (group.glow) group.glow.material.opacity = 0.05 + health * 0.15;

    // Animation
    const time = Date.now() * 0.001;
    const pulse = 1 + Math.sin(time * 1.5 + i * 0.7) * 0.04;
    if (group.building) {
      group.building.scale.set(pulse, pulse, pulse);
      group.building.rotation.y += 0.003;
    }
    if (group.accent) {
      group.accent.rotation.y -= 0.005;
    }

    // Label
    group.ctx.clearRect(0, 0, 160, 80);
    group.ctx.fillStyle = colorHex;
    group.ctx.font = 'bold 16px monospace';
    group.ctx.textAlign = 'center';
    group.ctx.fillText((s.name || sType.toUpperCase()) + ' #' + s.id, 80, 22);
    group.ctx.font = '13px monospace';
    group.ctx.fillText(s.isos_inside + ' ISOs | ' + Math.round(health * 100) + '%', 80, 45);
    // Barre de vie
    group.ctx.fillStyle = '#222';
    group.ctx.fillRect(20, 55, 120, 6);
    group.ctx.fillStyle = colorHex;
    group.ctx.fillRect(20, 55, Math.round(120 * health), 6);
    group.tex.needsUpdate = true;
  }
}

// ====================================================
//  LIGHTWAYS -- Autoroutes suspendues Tron
// ====================================================

const lightwayMeshes = [];

function updateLightways(structures) {
  // Supprimer les anciens lightways
  for (const lw of lightwayMeshes) {
    if (lw.road) scene.remove(lw.road);
    if (lw.rail1) scene.remove(lw.rail1);
    if (lw.rail2) scene.remove(lw.rail2);
    for (const p of (lw.pillars || [])) scene.remove(p);
  }
  lightwayMeshes.length = 0;

  if (structures.length < 2) return;

  // Connecter chaque structure a sa plus proche voisine (max 150 unites)
  const maxDist = 150;
  const connected = new Set();

  for (let i = 0; i < structures.length; i++) {
    const a = structures[i];
    // Trouver les 2 plus proches
    const dists = [];
    for (let j = 0; j < structures.length; j++) {
      if (i === j) continue;
      const b = structures[j];
      const dx = b.x - a.x, dz = b.z - a.z;
      const dist = Math.sqrt(dx * dx + dz * dz);
      if (dist < maxDist) {
        dists.push({ j, dist, b });
      }
    }
    dists.sort((x, y) => x.dist - y.dist);

    for (const { j, dist, b } of dists.slice(0, 2)) {
      const key = Math.min(i, j) + '-' + Math.max(i, j);
      if (connected.has(key)) continue;
      connected.add(key);

      _createLightway(a.x, a.z, b.x, b.z, dist);
    }
  }
}

function _createLightway(x1, z1, x2, z2, dist) {
  const midX = (x1 + x2) / 2;
  const midZ = (z1 + z2) / 2;
  const dx = x2 - x1, dz = z2 - z1;
  const angle = Math.atan2(dz, dx);
  const roadHeight = 6;
  const roadWidth = 1.8;

  // Route principale (bande sombre avec bords lumineux)
  const roadGeo = new THREE.BoxGeometry(dist, 0.25, roadWidth);
  const roadMat = new THREE.MeshBasicMaterial({
    color: 0x050510, transparent: true, opacity: 0.6
  });
  const road = new THREE.Mesh(roadGeo, roadMat);
  road.position.set(midX, roadHeight, midZ);
  road.rotation.y = -angle;
  scene.add(road);

  // Rails lumineux (bords de l'autoroute)
  const railGeo = new THREE.BoxGeometry(dist, 0.12, 0.12);
  const railMat = new THREE.MeshBasicMaterial({
    color: 0x00e5ff, transparent: true, opacity: 0.6
  });
  const rail1 = new THREE.Mesh(railGeo, railMat);
  rail1.position.set(midX, roadHeight + 0.15, midZ);
  rail1.rotation.y = -angle;
  // Decaler sur le cote
  rail1.position.x += Math.sin(angle) * (roadWidth / 2);
  rail1.position.z -= Math.cos(angle) * (roadWidth / 2);
  scene.add(rail1);

  const rail2 = new THREE.Mesh(railGeo.clone(), railMat.clone());
  rail2.position.set(midX, roadHeight + 0.15, midZ);
  rail2.rotation.y = -angle;
  rail2.position.x -= Math.sin(angle) * (roadWidth / 2);
  rail2.position.z += Math.cos(angle) * (roadWidth / 2);
  scene.add(rail2);

  // Piliers de soutien
  const pillars = [];
  const nPillars = Math.max(2, Math.floor(dist / 25));
  for (let p = 0; p <= nPillars; p++) {
    const t = p / nPillars;
    const px = x1 + dx * t;
    const pz = z1 + dz * t;

    // Pilier sombre
    const pilGeo = new THREE.BoxGeometry(0.6, roadHeight, 0.6);
    const pilMat = new THREE.MeshBasicMaterial({
      color: 0x050510, transparent: true, opacity: 0.5
    });
    const pil = new THREE.Mesh(pilGeo, pilMat);
    pil.position.set(px, roadHeight / 2, pz);
    scene.add(pil);
    pillars.push(pil);

    // Ligne lumineuse sur le pilier
    const lineGeo = new THREE.BoxGeometry(0.1, roadHeight, 0.1);
    const lineMat = new THREE.MeshBasicMaterial({
      color: 0x00e5ff, transparent: true, opacity: 0.5
    });
    const line = new THREE.Mesh(lineGeo, lineMat);
    line.position.set(px, roadHeight / 2, pz);
    scene.add(line);
    pillars.push(line);
  }

  lightwayMeshes.push({ road, rail1, rail2, pillars });
}

// ====================================================
//  HUD -- Stats
// ====================================================

function updateHUD(data) {
  const t = data.time || {};
  const p = data.population || {};
  const g = data.grid || {};

  setText('stat-time', t.virtual_formatted || '--');
  setText('stat-cycles', t.cycles || 0);
  setText('stat-isos', p.alive || 0);
  setText('stat-born-died', (p.total_born || 0) + ' / ' + (p.total_died || 0));
  setText('stat-gen', p.max_generation || 0);
  setText('stat-energy', (p.avg_energy || 0).toFixed(0));
  setText('stat-fitness', (p.avg_fitness || 0).toFixed(1));
  setText('stat-grid-energy', (g.avg_energy || 0).toFixed(0));
  setText('stat-knowledge', (p.avg_knowledge || 0).toFixed(2));
  setText('stat-intelligence', (p.avg_intelligence || 0).toFixed(2));

  const sigStats = p.signals || {};
  setText('stat-signals', sigStats.active_signals || 0);

  // Tron stats
  const tron = data.tron || {};
  setText('stat-tron-protected', tron.current_protected || 0);
  setText('stat-tron-saved', tron.total_saved || 0);
  setText('stat-tron-mode', tron.mode ? tron.mode.toUpperCase() : '--');

  // Minerve stats
  const minerve = data.minerve || {};
  setText('stat-minerve-students', (minerve.current_students || 0) + ' eleves');

  // Symmetra stats
  const sym = data.symmetra || {};
  setText('stat-sym-structures', (sym.active_structures || sym.active_shelters || 0) + ' structures');
  const bTypes = sym.builds_by_type || {};
  const typeSummary = Object.entries(bTypes)
    .filter(([k, v]) => v > 0)
    .map(([k, v]) => v + ' ' + k.replace('_', ' '))
    .join(', ') || 'aucune';
  setText('stat-sym-built', typeSummary);

  // Daedalus stats
  const daedalus = data.daedalus || {};
  setText('stat-daedalus-inspired', daedalus.total_inspired || 0);
  setText('stat-daedalus-seekers', daedalus.current_seekers || 0);

  // Pause overlay
  const ctrl = data.control || {};
  const pauseOverlay = document.getElementById('paused-overlay');
  if (pauseOverlay) pauseOverlay.style.display = ctrl.paused ? 'block' : 'none';
  const btnPause = document.getElementById('btn-pause');
  if (btnPause) {
    btnPause.textContent = ctrl.paused ? 'PLAY' : 'PAUSE';
    btnPause.classList.toggle('active', ctrl.paused);
  }

  updateIsoList(data.isos || []);
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function updateIsoList(isos) {
  const panel = document.getElementById('iso-list');
  if (!panel) return;

  const sorted = isos.slice(0, 15).sort((a, b) => b.energy - a.energy);
  panel.innerHTML = sorted.map(iso => {
    const pct = Math.round((iso.energy / (iso.max_energy || 200)) * 100);
    const barClass = pct < 25 ? 'low' : (pct < 50 ? 'mid' : '');
    const kTotal = iso.knowledge ? iso.knowledge.total.toFixed(1) : '0.0';
    return `<div class="iso-entry">
      <span class="iso-id">#${iso.id}</span>
      G${iso.generation} | ${iso.energy.toFixed(0)}E | K:${kTotal} | ${iso.last_action || '--'}
      <span class="iso-energy-bar ${barClass}" style="width:${pct}px"></span>
    </div>`;
  }).join('');
}

// ====================================================
//  FETCH DATA
// ====================================================

let lastMinervePos = null;
let lastTronPos = null;

async function fetchState() {
  try {
    const resp = await fetch('/api/state');
    const data = await resp.json();
    updateHUD(data);

    // Minerve
    const minerveData = data.minerve || null;
    lastMinervePos = minerveData;
    updateMinerve(minerveData);

    // Tron
    const tronData = data.tron || null;
    lastTronPos = tronData;
    updateTron(tronData);

    // Symmetra + abris
    updateSymmetra(data.symmetra || null);

    // Daedalus
    updateDaedalus(data.daedalus || null);
    updateDaedalusTerminal(data.daedalus || null);

    // ISOs (avec positions Minerve + Tron pour boost visuel)
    updateIsoMeshes(data.isos || [], lastMinervePos, lastTronPos);
    updateEnergyMap(data.energy_map || []);
    updateSignals(data.signals || []);
  } catch (e) {
    console.warn('Fetch error:', e);
  }
}

// ====================================================
//  ANIMATION
// ====================================================

function animate() {
  requestAnimationFrame(animate);

  // Camera ZQSD + orbite
  updateCamera();

  // Minerve rotation continue
  if (minerveMesh && minerveMesh.visible) {
    const t = Date.now() * 0.001;
    minerveMesh.rotation.y = t * 0.5;
  }

  // Tron rotation rapide
  if (tronMesh && tronMesh.visible) {
    const t = Date.now() * 0.001;
    tronMesh.rotation.y = t * 1.2;
    tronMesh.rotation.x = t * 0.4;
  }

  // Symmetra rotation lente
  if (symmetraMesh && symmetraMesh.visible) {
    const t = Date.now() * 0.001;
    symmetraMesh.rotation.y = t * 0.3;
  }

  renderer.render(scene, camera);
}

/**
 * Charge les modeles GLB Tron depuis le serveur.
 * Les structures existantes sont reconstruites une fois tous les modeles charges.
 */
function loadStructureModels() {
  if (typeof THREE.GLTFLoader === 'undefined') {
    console.warn('[NexOS] GLTFLoader indisponible -- geometrie procedurale utilisee');
    return;
  }
  const loader = new THREE.GLTFLoader();
  const filesToLoad = [...new Set(Object.values(MODEL_MAP))];
  let remaining = filesToLoad.length;

  filesToLoad.forEach(file => {
    loader.load('/models/' + file,
      (gltf) => {
        gltfModels[file] = gltf.scene;
        console.log('[NexOS] Modele GLB charge :', file);
        remaining--;
        if (remaining === 0) {
          // Reconstruire toutes les structures avec les vrais modeles Tron
          for (const m of structureMeshes) {
            if (!m) continue;
            if (m.base)     scene.remove(m.base);
            if (m.building) scene.remove(m.building);
            if (m.accent)   scene.remove(m.accent);
            if (m.glow)     scene.remove(m.glow);
            if (m.label)    scene.remove(m.label);
          }
          structureMeshes.length = 0;
          console.log('[NexOS] Structures reconstruites avec modeles Tron GLB');
        }
      },
      undefined,
      (err) => {
        console.warn('[NexOS] Echec chargement GLB :', file, err.message || err);
        remaining--;
      }
    );
  });
}

animate();
loadStructureModels();
loadGridFloor();
setInterval(fetchState, 1000);
setInterval(fetchLogs, 3000);
fetchState();

function resizeRenderer() {
  const el = document.getElementById('scene');
  if (!el) return;
  const w = el.clientWidth || window.innerWidth;
  const h = el.clientHeight || window.innerHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
}
window.addEventListener('resize', resizeRenderer);
setTimeout(resizeRenderer, 100);

// ====================================================
//  UI CONTROLS (pause, speed, reset, chat, console)
// ====================================================

// Pause
async function togglePause() {
  try {
    await fetch('/api/control/pause', { method: 'POST' });
  } catch(e) { console.warn(e); }
}

// Reset
async function resetSim() {
  if (!confirm('Reinitialiser la simulation ?')) return;
  try {
    await fetch('/api/control/reset', { method: 'POST' });
  } catch(e) { console.warn(e); }
}

// Speed slider
const speedSlider = document.getElementById('speed-slider');
const speedValue = document.getElementById('speed-value');
if (speedSlider) {
  speedSlider.addEventListener('input', async () => {
    const v = parseFloat(speedSlider.value) / 10;
    speedValue.textContent = 'x' + v.toFixed(1);
    try {
      await fetch('/api/control/speed', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ speed: v })
      });
    } catch(e) {}
  });
}

// Screenshot
function exportScreenshot() {
  const link = document.createElement('a');
  link.download = 'NexOS_screenshot.png';
  link.href = renderer.domElement.toDataURL('image/png');
  link.click();
}

// Chat IA
let currentChatTarget = 'system';
const chatHistory = document.getElementById('chat-history');
const chatInput = document.getElementById('chat-input');

// Onglets chat
document.querySelectorAll('.chat-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.chat-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    currentChatTarget = tab.dataset.target;
  });
});

async function sendChat() {
  if (!chatInput) return;
  const msg = chatInput.value.trim();
  if (!msg) return;

  // Message utilisateur
  const userDiv = document.createElement('div');
  userDiv.className = 'chat-msg user';
  userDiv.textContent = msg;
  chatHistory.appendChild(userDiv);

  chatInput.value = '';

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ target: currentChatTarget, message: msg })
    });
    const data = await resp.json();

    const aiDiv = document.createElement('div');
    aiDiv.className = 'chat-msg ai ' + currentChatTarget;
    aiDiv.textContent = data.response;
    chatHistory.appendChild(aiDiv);
  } catch(e) {
    const errDiv = document.createElement('div');
    errDiv.className = 'chat-msg ai';
    errDiv.textContent = '[Erreur de communication]';
    chatHistory.appendChild(errDiv);
  }

  chatHistory.scrollTop = chatHistory.scrollHeight;
}

if (chatInput) {
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      sendChat();
    }
  });
}

// Empecher ZQSD de bouger la camera quand on tape dans le chat
if (chatInput) {
  chatInput.addEventListener('focus', () => { chatInput._focused = true; });
  chatInput.addEventListener('blur', () => { chatInput._focused = false; });
}

// Console Debug
let consoleOpen = false;
function toggleConsole() {
  consoleOpen = !consoleOpen;
  const content = document.getElementById('console-content');
  const toggle = document.getElementById('console-toggle');
  if (content) content.classList.toggle('open', consoleOpen);
  if (toggle) toggle.textContent = consoleOpen ? 'v' : '^';
}

async function fetchLogs() {
  try {
    const resp = await fetch('/api/logs');
    const logs = await resp.json();
    const content = document.getElementById('console-content');
    if (!content) return;
    content.innerHTML = logs.map(l =>
      `<div class="log-entry ${l.level}"><span class="log-time">${l.time}</span>${l.msg}</div>`
    ).join('');
    content.scrollTop = content.scrollHeight;
  } catch(e) {}
}

// ====================================================
//  DAEDALUS TERMINAL -- Interface flottante
// ====================================================

const daedalusTerminal = document.getElementById('daedalus-terminal');
const daedalusFeed = document.getElementById('daedalus-feed');
const daedalusInputEl = document.getElementById('daedalus-input');
const daedalusToggleBtn = document.getElementById('daedalus-toggle-btn');

let daedalusTerminalOpen = true;
let _lastDaedalusState = null;
let _daedalusFeedCount = 2; // 2 lignes initiales dans le HTML

// -- Drag du terminal --
(function initDaedalusDrag() {
  const titlebar = document.getElementById('daedalus-titlebar');
  if (!titlebar || !daedalusTerminal) return;
  let dragging = false, startX = 0, startY = 0, origLeft = 0, origTop = 0;

  titlebar.addEventListener('mousedown', (e) => {
    if (e.target.tagName === 'BUTTON') return;
    dragging = true;
    const rect = daedalusTerminal.getBoundingClientRect();
    startX = e.clientX; startY = e.clientY;
    origLeft = rect.left; origTop = rect.top;
    daedalusTerminal.style.right = 'auto';
    daedalusTerminal.style.bottom = 'auto';
    daedalusTerminal.style.left = origLeft + 'px';
    daedalusTerminal.style.top = origTop + 'px';
    e.preventDefault();
  });
  window.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    daedalusTerminal.style.left = (origLeft + dx) + 'px';
    daedalusTerminal.style.top = (origTop + dy) + 'px';
  });
  window.addEventListener('mouseup', () => { dragging = false; });
})();

// -- Toggle terminal --
function toggleDaedalusTerminal() {
  daedalusTerminalOpen = false;
  if (daedalusTerminal) daedalusTerminal.classList.add('hidden');
  if (daedalusToggleBtn) daedalusToggleBtn.style.display = 'block';
}
function openDaedalusTerminal() {
  daedalusTerminalOpen = true;
  if (daedalusTerminal) daedalusTerminal.classList.remove('hidden');
  if (daedalusToggleBtn) daedalusToggleBtn.style.display = 'none';
}

// -- Ajouter une ligne au feed --
function daedalusLog(text, type) {
  if (!daedalusFeed) return;
  type = type || 'action';
  const line = document.createElement('div');
  line.className = 'daedalus-feed-line ' + type;
  line.textContent = text;
  daedalusFeed.appendChild(line);
  _daedalusFeedCount++;
  daedalusFeed.scrollTop = daedalusFeed.scrollHeight;
}

// -- Mise a jour du terminal avec les donnees Daedalus --
function updateDaedalusTerminal(daedalusData) {
  if (!daedalusData || !daedalusData.enabled) return;

  // Status bar
  var posEl = document.getElementById('dterm-pos');
  var seekEl = document.getElementById('dterm-seekers');
  var inspEl = document.getElementById('dterm-inspired');
  if (posEl) posEl.textContent = 'POS (' + daedalusData.x + ', ' + daedalusData.z + ')';
  if (seekEl) seekEl.textContent = daedalusData.current_seekers + ' explorateurs';
  if (inspEl) inspEl.textContent = daedalusData.total_inspired + ' inspires';

  // Messages d'activite contextuels
  if (_lastDaedalusState) {
    var prev = _lastDaedalusState;
    var curr = daedalusData;

    // Deplacement significatif
    var moveDx = Math.abs(curr.x - prev.x);
    var moveDz = Math.abs(curr.z - prev.z);
    if (moveDx > 8 || moveDz > 8) {
      daedalusLog('Deplacement vers zone (' + curr.x + ', ' + curr.z + ')', 'move');
    }

    // Nouvelles inspirations
    var newInspired = curr.total_inspired - prev.total_inspired;
    if (newInspired > 0 && curr.current_seekers > 0) {
      daedalusLog(curr.current_seekers + ' ISOs dans le rayon -- curiosite stimulee (+' + newInspired + ')', 'inspire');
    }

    // Nouvelles questions
    var newQ = curr.total_questions_asked - prev.total_questions_asked;
    if (newQ > 10 && curr.cycles_active % 30 === 0) {
      daedalusLog(newQ + ' nouvelles questions posees aux ISOs proches', 'action');
    }

    // Changement de cible
    if (curr.target && prev.target) {
      if (curr.target.x !== prev.target.x || curr.target.z !== prev.target.z) {
        daedalusLog('Nouvelle cible detectee : zone stagnante (' + curr.target.x + ', ' + curr.target.z + ')', 'action');
      }
    }

    // Jalons
    if (curr.total_inspired >= 100 && prev.total_inspired < 100) {
      daedalusLog('Jalon : 100 ISOs inspires !', 'system');
    }
    if (curr.total_inspired >= 500 && prev.total_inspired < 500) {
      daedalusLog('Jalon : 500 ISOs inspires !', 'system');
    }
    if (curr.total_inspired >= 1000 && prev.total_inspired < 1000) {
      daedalusLog('Jalon : 1000 ISOs inspires !', 'system');
    }
  }

  _lastDaedalusState = {
    x: daedalusData.x, z: daedalusData.z,
    total_inspired: daedalusData.total_inspired,
    total_questions_asked: daedalusData.total_questions_asked,
    current_seekers: daedalusData.current_seekers,
    cycles_active: daedalusData.cycles_active,
    target: daedalusData.target ? { x: daedalusData.target.x, z: daedalusData.target.z } : null
  };
}

// -- Envoi de message a Daedalus --
async function sendDaedalusMessage() {
  if (!daedalusInputEl) return;
  var msg = daedalusInputEl.value.trim();
  if (!msg) return;

  daedalusLog(msg, 'user-msg');
  daedalusInputEl.value = '';

  try {
    var resp = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ target: 'daedalus', message: msg })
    });
    var data = await resp.json();
    daedalusLog(data.response, 'daedalus-reply');
  } catch(e) {
    daedalusLog('[Erreur de communication]', 'system');
  }
}

// Events input Daedalus
if (daedalusInputEl) {
  daedalusInputEl.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      sendDaedalusMessage();
    }
  });
  daedalusInputEl.addEventListener('focus', function() {
    daedalusInputEl._focused = true;
    if (chatInput) chatInput._focused = true;
  });
  daedalusInputEl.addEventListener('blur', function() {
    daedalusInputEl._focused = false;
    if (chatInput) chatInput._focused = false;
  });
}
