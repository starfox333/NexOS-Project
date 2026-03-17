extends Node3D
## Rendu 3D des super-entites : Minerve, Tron, Symmetra, Daedalus
## Chacune a une geometrie unique, un label flottant, et une aura.
## Echelle x10 pour proportions Sims 4 avec ISOs (scale x15).

const ENTITY_SCALE := 50.0  ## Facteur d'echelle global (continent 10000x10000)
const BEACON_HEIGHT := 800.0  ## Hauteur des piliers lumineux (visible de tres loin)

# ---- MINERVE (octahedron dore -- gardienne du savoir) ----
var _minerve_mesh: MeshInstance3D
var _minerve_aura: MeshInstance3D
var _minerve_label: Label3D
var _minerve_light: OmniLight3D

# ---- TRON (icosahedron cyan -- protecteur) ----
var _tron_mesh: MeshInstance3D
var _tron_aura: MeshInstance3D
var _tron_label: Label3D
var _tron_trail: MeshInstance3D
var _tron_trail_points: Array[Vector3] = []
var _tron_light: OmniLight3D

# ---- SYMMETRA (dodecahedron magenta -- batisseuse) ----
var _sym_mesh: MeshInstance3D
var _sym_aura: MeshInstance3D
var _sym_label: Label3D
var _sym_beam: MeshInstance3D  # Faisceau de construction hard-light
var _sym_light: OmniLight3D

# ---- DAEDALUS (icosahedron violet -- catalyseur d'innovation) ----
var _daedalus_mesh: MeshInstance3D
var _daedalus_aura: MeshInstance3D
var _daedalus_label: Label3D
var _daedalus_light: OmniLight3D
var _daedalus_trail: MeshInstance3D
var _daedalus_trail_points: Array[Vector3] = []

# ---- PILIERS LUMINEUX (beacons visibles de tres loin) ----
var _minerve_beacon: MeshInstance3D
var _tron_beacon: MeshInstance3D
var _sym_beacon: MeshInstance3D
var _daedalus_beacon: MeshInstance3D

# ---- MODELES FBX OPTIONNELS ----
var _tron_disc_model: Node3D = null  ## Disques d'identite (FBX charge)
var _tron_baton_model: Node3D = null  ## Baton Tron Legacy (FBX charge)


func _ready() -> void:
	_load_optional_models()
	_init_minerve()
	_init_tron()
	_init_symmetra()
	_init_daedalus()


func _load_optional_models() -> void:
	"""Charge les modeles FBX optionnels (disques Tron, baton)."""
	# Disques d'identite Tron
	var disc_path := "res://assets/models/TRON Identity Discs (All Colors).fbx"
	if ResourceLoader.exists(disc_path):
		var disc_scene: PackedScene = load(disc_path)
		if disc_scene:
			_tron_disc_model = disc_scene.instantiate()
			_tron_disc_model.visible = false
			add_child(_tron_disc_model)
			print("EntityRenderer: Disques Tron charges depuis FBX")

	# Baton Tron Legacy
	var baton_path := "res://assets/models/items/Baton .fbx"
	if ResourceLoader.exists(baton_path):
		var baton_scene: PackedScene = load(baton_path)
		if baton_scene:
			_tron_baton_model = baton_scene.instantiate()
			_tron_baton_model.visible = false
			add_child(_tron_baton_model)
			print("EntityRenderer: Baton Tron charge depuis FBX")


# ==================================================================
#  MINERVE
# ==================================================================

func _init_minerve() -> void:
	var container := Node3D.new()
	container.name = "Minerve"
	add_child(container)

	# Couleurs Minerve -- or/ambre, deesse de la sagesse
	var gold := Color(1.0, 0.843, 0.0)         # Or pur
	var gold_light := Color(1.0, 0.92, 0.5)    # Or clair (halo)
	var gold_warm := Color(0.95, 0.75, 0.1)    # Or chaud

	# Corps principal : prisme hexagonal elance -- PBR or metallique
	var body_mesh := _make_symmetra_prism(1.8, 5.5)
	_minerve_mesh = _create_pbr_mesh(body_mesh, Color(0.15, 0.12, 0.02, 0.95), gold, 2.5, 0.9, 0.15)
	container.add_child(_minerve_mesh)

	# Couronne / Halo divin flottant -- PBR or poli
	var crown := TorusMesh.new()
	crown.inner_radius = 2.2
	crown.outer_radius = 2.5
	crown.rings = 16
	crown.ring_segments = 8
	var crown_mi := _create_pbr_mesh(crown, Color(0.2, 0.16, 0.03, 0.95), gold_light, 2.5, 0.95, 0.1)
	crown_mi.name = "Crown"
	container.add_child(crown_mi)

	# Sceptre vertical -- PBR or metallique
	var staff_mesh := CylinderMesh.new()
	staff_mesh.top_radius = 0.1
	staff_mesh.bottom_radius = 0.12
	staff_mesh.height = 8.0
	staff_mesh.radial_segments = 6
	var staff := _create_pbr_mesh(staff_mesh, Color(0.12, 0.1, 0.02, 0.95), gold_warm, 1.5, 0.9, 0.15)
	staff.name = "Staff"
	container.add_child(staff)

	# Orbe au sommet du sceptre
	var orb_mesh := SphereMesh.new()
	orb_mesh.radius = 0.6
	orb_mesh.height = 1.2
	orb_mesh.radial_segments = 8
	orb_mesh.rings = 6
	var orb := _create_entity_mesh(orb_mesh, gold_light, 3.0)
	orb.name = "StaffOrb"
	container.add_child(orb)

	# 5 cristaux de savoir en orbite (un par domaine de connaissance)
	# physique, social, ecologie, logique, communication
	for i in range(5):
		var crystal_mesh := _make_octahedron(0.5)
		var crystal := _create_entity_mesh(crystal_mesh, gold_light, 1.8)
		crystal.name = "Crystal_%d" % i
		container.add_child(crystal)

	# Aura dorée (zone d'enseignement)
	_minerve_aura = _create_aura(16.0, Color(gold.r, gold.g, gold.b, 0.12))
	container.add_child(_minerve_aura)

	# Label
	_minerve_label = _create_label("MINERVE", gold)
	container.add_child(_minerve_label)

	# OmniLight3D dynamique -- projette une lumiere doree sur les environs
	_minerve_light = _create_entity_light(gold, 2.5, 200.0)
	_minerve_light.name = "MinerveLight"
	container.add_child(_minerve_light)

	# Pilier lumineux vertical -- repere visible de tres loin
	_minerve_beacon = _create_beacon(gold)
	container.add_child(_minerve_beacon)

	container.visible = false


func update_minerve(data: Dictionary) -> void:
	var container: Node3D = get_node_or_null("Minerve")
	if not container:
		return

	if data.is_empty() or not data.get("enabled", false):
		container.visible = false
		return

	container.visible = true
	var mx: float = float(data.get("x", 250))
	var mz: float = float(data.get("z", 250))
	var t: float = Time.get_ticks_msec() / 1000.0
	var students: int = int(data.get("current_students", 0))
	var ES: float = ENTITY_SCALE  # 4.0

	# Flottement majestueux + rotation lente (x4 hauteur)
	var float_y: float = (6.0 + sin(t * 0.7) * 1.2) * ES
	_minerve_mesh.position = Vector3(mx, float_y, mz)
	_minerve_mesh.rotation.y = t * 0.3
	_minerve_mesh.rotation.x = sin(t * 0.2) * 0.08
	_minerve_mesh.scale = Vector3(ES, ES, ES)

	# Couronne / Halo
	var crown: Node3D = container.get_node_or_null("Crown")
	if crown:
		crown.position = Vector3(mx, float_y + 3.8 * ES, mz)
		crown.rotation.y = -t * 0.6
		crown.rotation.x = PI / 2.0 + sin(t * 0.4) * 0.1
		crown.scale = Vector3(ES, ES, ES)

	# Sceptre
	var staff: Node3D = container.get_node_or_null("Staff")
	if staff:
		var staff_offset_x: float = cos(t * 0.3 + 1.0) * 0.3 * ES
		staff.position = Vector3(mx + 3.0 * ES + staff_offset_x, float_y - 0.5 * ES, mz)
		staff.rotation.z = sin(t * 0.5) * 0.08
		staff.scale = Vector3(ES, ES, ES)

	# Orbe au sommet du sceptre
	var orb: Node3D = container.get_node_or_null("StaffOrb")
	if orb:
		var orb_pulse: float = ES * (1.0 + sin(t * 3.0) * 0.15)
		orb.position = Vector3(mx + 3.0 * ES + cos(t * 0.3 + 1.0) * 0.3 * ES, float_y + 3.5 * ES, mz)
		orb.scale = Vector3(orb_pulse, orb_pulse, orb_pulse)

	# 5 cristaux de savoir en orbite
	for i in range(5):
		var crystal: Node3D = container.get_node_or_null("Crystal_%d" % i)
		if crystal:
			var angle: float = t * 0.8 + float(i) * TAU / 5.0
			var orbit_r: float = (5.0 + sin(t * 0.5 + float(i)) * 0.5) * ES
			var cy: float = float_y + sin(t * 1.5 + float(i) * 1.2) * 1.0 * ES
			crystal.position = Vector3(
				mx + cos(angle) * orbit_r,
				cy,
				mz + sin(angle) * orbit_r
			)
			crystal.rotation.y = t * 2.0 + float(i)
			crystal.rotation.x = t * 1.5
			crystal.scale = Vector3(ES, ES, ES)

	# Boost visuel quand Minerve enseigne
	var mat: StandardMaterial3D = _minerve_mesh.material_override
	if mat:
		if students > 0:
			mat.emission_energy_multiplier = 2.0 + minf(float(students), 10.0) * 0.3
		else:
			mat.emission_energy_multiplier = 2.0

	# Aura pulse (agrandie)
	_minerve_aura.position = Vector3(mx, 0.3, mz)
	var base_aura: float = ES * (1.0 + sin(t * 2.0) * 0.15)
	var teach_boost: float = 1.0 + minf(float(students), 10.0) * 0.05
	_minerve_aura.scale = Vector3(base_aura * teach_boost, 1.0, base_aura * teach_boost)

	# Label (plus haut)
	_minerve_label.position = Vector3(mx, float_y + 8.0 * ES, mz)
	_minerve_label.font_size = 48

	# Lumiere dynamique
	if _minerve_light:
		_minerve_light.position = Vector3(mx, float_y + 2.0 * ES, mz)
		var light_pulse: float = 1.2 + sin(t * 1.5) * 0.3
		if students > 0:
			light_pulse += minf(float(students), 10.0) * 0.1
		_minerve_light.light_energy = light_pulse * ES * 0.5
		_minerve_light.omni_range = 60.0 * ES

	# Pilier lumineux (beacon)
	if _minerve_beacon:
		_minerve_beacon.position = Vector3(mx, BEACON_HEIGHT / 2.0, mz)
		var beacon_pulse: float = 0.8 + sin(t * 0.5) * 0.2
		_minerve_beacon.scale.x = beacon_pulse
		_minerve_beacon.scale.z = beacon_pulse


# ==================================================================
#  TRON
# ==================================================================

func _init_tron() -> void:
	var container := Node3D.new()
	container.name = "Tron"
	add_child(container)

	# Couleurs Tron -- armure sombre + circuits orange incandescents (Rinzler/Legacy)
	var tron_dark := Color(0.06, 0.06, 0.1)       # Corps sombre (armure noire)
	var tron_orange := Color(1.0, 0.55, 0.0)      # Orange circuits
	var tron_glow := Color(1.0, 0.65, 0.1)        # Orange lumineux (emission)

	# Corps principal : prisme guerrier -- PBR noir metallique
	var body_mesh := _make_symmetra_prism(2.0, 4.5)
	_tron_mesh = _create_pbr_mesh(body_mesh, Color(0.03, 0.03, 0.05, 0.95), tron_orange, 0.5, 0.9, 0.2)
	container.add_child(_tron_mesh)

	# DEUX DISQUES D'IDENTITE -- PBR metallique orange (reflets)
	for d in range(2):
		var disc_outer := TorusMesh.new()
		disc_outer.inner_radius = 2.2
		disc_outer.outer_radius = 2.6
		disc_outer.rings = 24
		disc_outer.ring_segments = 8
		var disc_mi := _create_pbr_mesh(disc_outer, Color(0.12, 0.06, 0.0, 0.95), tron_orange, 3.5, 0.95, 0.05)
		disc_mi.name = "IdentityDisc_%d" % d
		container.add_child(disc_mi)

		# Coeur du disque (cercle plein semi-transparent)
		var disc_core := PlaneMesh.new()
		disc_core.size = Vector2(4.4, 4.4)
		var core_mi := _create_entity_mesh(disc_core, tron_glow, 1.5)
		core_mi.name = "DiscCore_%d" % d
		var core_mat: StandardMaterial3D = core_mi.material_override
		if core_mat:
			core_mat.albedo_color.a = 0.12
			core_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
		container.add_child(core_mi)

	# Lignes de circuit orange sur le corps (comme les lignes du costume Tron)
	for i in range(6):
		var circuit := CylinderMesh.new()
		circuit.top_radius = 0.06
		circuit.bottom_radius = 0.06
		circuit.height = 4.5
		circuit.radial_segments = 4
		var c_mi := _create_entity_mesh(circuit, tron_orange, 3.0)
		c_mi.name = "Circuit_%d" % i
		container.add_child(c_mi)

	# Visiere du casque (arc lumineux au sommet)
	var visor := TorusMesh.new()
	visor.inner_radius = 0.8
	visor.outer_radius = 1.0
	visor.rings = 8
	visor.ring_segments = 4
	var visor_mi := _create_entity_mesh(visor, tron_orange, 2.5)
	visor_mi.name = "Visor"
	container.add_child(visor_mi)

	# Epaulettes lumineuses orange (2 arcs aux epaules)
	for side in range(2):
		var shoulder := TorusMesh.new()
		shoulder.inner_radius = 1.0
		shoulder.outer_radius = 1.3
		shoulder.rings = 8
		shoulder.ring_segments = 4
		var s_mi := _create_entity_mesh(shoulder, tron_orange, 2.0)
		s_mi.name = "Shoulder_%d" % side
		container.add_child(s_mi)

	# Aura de protection (orange au lieu de cyan)
	_tron_aura = _create_aura(13.0, Color(tron_orange.r, tron_orange.g, tron_orange.b, 0.10))
	container.add_child(_tron_aura)

	# Label (orange)
	_tron_label = _create_label("TRON", tron_orange)
	container.add_child(_tron_label)

	# Trail lightcycle (orange incandescent)
	_tron_trail = MeshInstance3D.new()
	_tron_trail.name = "TronTrail"
	var trail_mat := StandardMaterial3D.new()
	trail_mat.albedo_color = Color(tron_orange.r, tron_orange.g, tron_orange.b, 0.7)
	trail_mat.emission_enabled = true
	trail_mat.emission = tron_orange
	trail_mat.emission_energy_multiplier = 1.2
	trail_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	trail_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_tron_trail.material_override = trail_mat
	container.add_child(_tron_trail)

	# OmniLight3D dynamique -- projette une lumiere orange guerriere
	_tron_light = _create_entity_light(tron_orange, 2.5, 200.0)
	_tron_light.name = "TronLight"
	container.add_child(_tron_light)

	# Pilier lumineux
	_tron_beacon = _create_beacon(tron_orange)
	container.add_child(_tron_beacon)

	container.visible = false


func update_tron(data: Dictionary) -> void:
	var container: Node3D = get_node_or_null("Tron")
	if not container:
		return

	if data.is_empty() or not data.get("enabled", false):
		container.visible = false
		return

	container.visible = true
	var tx: float = float(data.get("x", 125))
	var tz: float = float(data.get("z", 125))
	var t: float = Time.get_ticks_msec() / 1000.0
	var mode: String = data.get("mode", "patrol")
	var protected_count: int = int(data.get("current_protected", 0))
	var ES: float = ENTITY_SCALE

	# Corps -- rotation rapide guerriere (x4)
	var float_y: float = (4.5 + sin(t * 1.5) * 0.8) * ES
	_tron_mesh.position = Vector3(tx, float_y, tz)
	_tron_mesh.rotation.y = t * 1.0
	_tron_mesh.rotation.x = sin(t * 0.5) * 0.15
	_tron_mesh.scale = Vector3(ES, ES, ES)

	# DEUX DISQUES D'IDENTITE
	for d in range(2):
		var disc: Node3D = container.get_node_or_null("IdentityDisc_%d" % d)
		var dcore: Node3D = container.get_node_or_null("DiscCore_%d" % d)
		if disc:
			var phase: float = float(d) * PI
			var disc_angle: float = t * 2.0 + phase
			var disc_orbit: float = 3.5 * ES
			var disc_y: float = float_y + sin(t * 1.8 + phase) * 1.2 * ES

			if mode == "emergency":
				disc_angle = t * 5.0 + phase
				disc_orbit = 5.5 * ES
				disc_y = float_y + sin(t * 3.0 + phase * 0.7) * 2.0 * ES

			disc.position = Vector3(
				tx + cos(disc_angle) * disc_orbit,
				disc_y,
				tz + sin(disc_angle) * disc_orbit
			)
			disc.rotation.y = t * 4.0 * (1.0 if d == 0 else -1.0)
			disc.rotation.x = PI / 2.0 + sin(t + phase) * 0.3
			disc.scale = Vector3(ES, ES, ES)

		if dcore and disc:
			dcore.position = disc.position
			dcore.rotation = disc.rotation
			dcore.scale = Vector3(ES, ES, ES)

	# Lignes de circuit lumineuses
	for i in range(4):
		var circuit: Node3D = container.get_node_or_null("Circuit_%d" % i)
		if circuit:
			var c_angle: float = float(i) / 4.0 * TAU
			circuit.position = Vector3(tx + cos(c_angle) * 1.2 * ES, float_y, tz + sin(c_angle) * 1.2 * ES)
			circuit.rotation.y = c_angle
			circuit.scale = Vector3(ES, ES, ES)

	# Epaulettes
	for side in range(2):
		var shoulder: Node3D = container.get_node_or_null("Shoulder_%d" % side)
		if shoulder:
			var s_offset: float = 2.5 * ES * (1.0 if side == 0 else -1.0)
			shoulder.position = Vector3(tx + s_offset, float_y + 1.5 * ES, tz)
			shoulder.rotation.z = PI / 2.0
			shoulder.rotation.y = t * 0.5 * (1.0 if side == 0 else -1.0)
			shoulder.scale = Vector3(ES, ES, ES)

	# Mode urgence
	var mat: StandardMaterial3D = _tron_mesh.material_override
	if mode == "emergency":
		var pulse: float = 0.7 + sin(t * 6.0) * 0.3
		if mat:
			mat.albedo_color.a = pulse
			mat.emission_energy_multiplier = 3.5
		_tron_mesh.scale = Vector3(ES * 1.3, ES * 1.3, ES * 1.3)
	else:
		if mat:
			mat.emission_energy_multiplier = 2.0

	# Aura de protection (agrandie)
	_tron_aura.position = Vector3(tx, 0.3, tz)
	var base_aura: float = ES * (1.0 + sin(t * 3.0) * 0.2)
	var prot_boost: float = 1.0 + minf(float(protected_count), 10.0) * 0.05
	_tron_aura.scale = Vector3(base_aura * prot_boost, 1.0, base_aura * prot_boost)

	# Label
	_tron_label.position = Vector3(tx, float_y + 7.0 * ES, tz)
	_tron_label.font_size = 48

	# Lumiere dynamique
	if _tron_light:
		_tron_light.position = Vector3(tx, float_y + 1.0 * ES, tz)
		if mode == "emergency":
			_tron_light.light_energy = (2.5 + sin(t * 6.0) * 1.0) * ES * 0.5
			_tron_light.omni_range = 50.0 * ES
		else:
			_tron_light.light_energy = (1.5 + sin(t * 2.0) * 0.3) * ES * 0.5
			_tron_light.omni_range = 35.0 * ES

	# Trail (lightcycle) -- world space, not scaled
	var trail: Array = data.get("trail", [])
	_update_trail(trail, tx, tz)

	# Pilier lumineux (beacon)
	if _tron_beacon:
		_tron_beacon.position = Vector3(tx, BEACON_HEIGHT / 2.0, tz)
		var beacon_pulse: float = 0.8 + sin(t * 0.7) * 0.2
		_tron_beacon.scale.x = beacon_pulse
		_tron_beacon.scale.z = beacon_pulse


func _update_trail(trail: Array, tx: float, tz: float) -> void:
	if trail.size() < 2:
		_tron_trail.visible = false
		return

	_tron_trail.visible = true
	var im := ImmediateMesh.new()
	im.surface_begin(Mesh.PRIMITIVE_LINE_STRIP)
	for point in trail:
		var px: float = float(point.get("x", 0))
		var pz: float = float(point.get("z", 0))
		im.surface_add_vertex(Vector3(px, 1.5, pz))
	im.surface_add_vertex(Vector3(tx, 1.5, tz))
	im.surface_end()
	_tron_trail.mesh = im


# ==================================================================
#  SYMMETRA
# ==================================================================

func _init_symmetra() -> void:
	var container := Node3D.new()
	container.name = "Symmetra"
	add_child(container)

	# Couleurs Symmetra (Overwatch reference -- cyan/turquoise + accents or)
	var sym_cyan := Color(0.0, 0.85, 0.95)        # Turquoise clair (corps)
	var sym_accent := Color(0.4, 0.95, 1.0)       # Cyan lumineux (hard-light)
	var sym_gold := Color(0.95, 0.78, 0.15)       # Or/ambre (accents Vishkar)
	var sym_dark := Color(0.05, 0.05, 0.08)       # Noir mecanisme

	# Corps principal : prisme geometrique -- PBR turquoise metallique
	var body_mesh := _make_symmetra_prism(2.0, 5.0)
	_sym_mesh = _create_pbr_mesh(body_mesh, Color(0.02, 0.08, 0.1, 0.95), sym_cyan, 2.0, 0.85, 0.15)
	container.add_child(_sym_mesh)

	# Accents dores -- PBR or metallique poli
	for i in range(4):
		var gold_line := CylinderMesh.new()
		gold_line.top_radius = 0.06
		gold_line.bottom_radius = 0.06
		gold_line.height = 5.0
		gold_line.radial_segments = 4
		var gl_mi := _create_pbr_mesh(gold_line, Color(0.15, 0.12, 0.02, 0.95), sym_gold, 2.5, 0.95, 0.1)
		gl_mi.name = "GoldLine_%d" % i
		container.add_child(gl_mi)

	# Visiere / casque (arc lumineux cyan -- comme la visiere Overwatch)
	var visor := TorusMesh.new()
	visor.inner_radius = 0.7
	visor.outer_radius = 0.9
	visor.rings = 8
	visor.ring_segments = 4
	var visor_mi := _create_entity_mesh(visor, sym_accent, 3.0)
	visor_mi.name = "SymVisor"
	container.add_child(visor_mi)

	# Anneau orbital turquoise (photon projector)
	var orbit_ring := TorusMesh.new()
	orbit_ring.inner_radius = 3.0
	orbit_ring.outer_radius = 3.3
	orbit_ring.rings = 6
	orbit_ring.ring_segments = 16
	var ring_mi := _create_entity_mesh(orbit_ring, sym_accent, 1.0)
	ring_mi.name = "SymOrbit"
	container.add_child(ring_mi)

	# Anneau dore secondaire (accent Vishkar / shield generator)
	var gold_ring := TorusMesh.new()
	gold_ring.inner_radius = 3.8
	gold_ring.outer_radius = 4.0
	gold_ring.rings = 6
	gold_ring.ring_segments = 12
	var gold_ring_mi := _create_entity_mesh(gold_ring, sym_gold, 1.5)
	gold_ring_mi.name = "GoldRing"
	container.add_child(gold_ring_mi)

	# Petites spheres hard-light en orbite (turrets sentinelles)
	for i in range(3):
		var turret := SphereMesh.new()
		turret.radius = 0.4
		turret.height = 0.8
		turret.radial_segments = 6
		turret.rings = 4
		var t_mi := _create_entity_mesh(turret, sym_accent, 2.0)
		t_mi.name = "Turret_%d" % i
		container.add_child(t_mi)

	# Construct hard-light flottant (cube cristallin rotatif dans la main)
	var hardlight := BoxMesh.new()
	hardlight.size = Vector3(0.8, 0.8, 0.8)
	var hl_mi := _create_entity_mesh(hardlight, sym_accent, 3.5)
	hl_mi.name = "HardLightConstruct"
	container.add_child(hl_mi)

	# Particules hexagonales autour du construct (3 petits hexagones)
	for i in range(3):
		var hex_mesh := _make_symmetra_prism(0.2, 0.1)
		var hex_mi := _create_entity_mesh(hex_mesh, sym_gold, 2.0)
		hex_mi.name = "HexParticle_%d" % i
		container.add_child(hex_mi)

	# Faisceau de construction hard-light (visible uniquement en mode building)
	var beam_mesh := CylinderMesh.new()
	beam_mesh.top_radius = 0.15
	beam_mesh.bottom_radius = 0.4
	beam_mesh.height = 10.0
	beam_mesh.radial_segments = 6
	_sym_beam = _create_entity_mesh(beam_mesh, sym_accent, 2.5)
	_sym_beam.name = "BuildBeam"
	_sym_beam.visible = false
	container.add_child(_sym_beam)

	# Aura hexagonale (shield generator)
	_sym_aura = _create_aura(13.0, Color(sym_cyan.r, sym_cyan.g, sym_cyan.b, 0.10))
	container.add_child(_sym_aura)

	# Label
	_sym_label = _create_label("SYMMETRA", sym_cyan)
	container.add_child(_sym_label)

	# OmniLight3D dynamique -- projette une lumiere cyan de construction
	_sym_light = _create_entity_light(sym_cyan, 2.5, 200.0)
	_sym_light.name = "SymLight"
	container.add_child(_sym_light)

	# Pilier lumineux
	_sym_beacon = _create_beacon(sym_cyan)
	container.add_child(_sym_beacon)

	container.visible = false


func update_symmetra(data: Dictionary) -> void:
	var container: Node3D = get_node_or_null("Symmetra")
	if not container:
		return

	if data.is_empty() or not data.get("enabled", false):
		container.visible = false
		return

	container.visible = true
	var sx: float = float(data.get("x", 375))
	var sz: float = float(data.get("z", 375))
	var t: float = Time.get_ticks_msec() / 1000.0
	var mode: String = data.get("mode", "idle")
	var ES: float = ENTITY_SCALE

	# Flottement elegant (x4)
	var float_y: float = (5.0 + sin(t * 0.8) * 1.0) * ES
	_sym_mesh.position = Vector3(sx, float_y, sz)
	_sym_mesh.rotation.y = t * 0.4
	_sym_mesh.rotation.x = sin(t * 0.3) * 0.1
	_sym_mesh.scale = Vector3(ES, ES, ES)

	# Accents dores
	for i in range(4):
		var gl: Node3D = container.get_node_or_null("GoldLine_%d" % i)
		if gl:
			var gl_angle: float = float(i) / 4.0 * TAU + t * 0.4
			var gl_r: float = 1.3 * ES
			gl.position = Vector3(sx + cos(gl_angle) * gl_r, float_y, sz + sin(gl_angle) * gl_r)
			gl.rotation.y = gl_angle
			gl.scale = Vector3(ES, ES, ES)

	# Visiere
	var visor: Node3D = container.get_node_or_null("SymVisor")
	if visor:
		visor.position = Vector3(sx, float_y + 3.2 * ES, sz)
		visor.rotation.x = PI / 2.0
		visor.rotation.y = t * 0.6
		visor.scale = Vector3(ES, ES, ES)

	# Anneau orbital cyan
	var orbit_ring: Node3D = container.get_node_or_null("SymOrbit")
	if orbit_ring:
		orbit_ring.position = Vector3(sx, float_y, sz)
		orbit_ring.rotation.y = -t * 0.8
		orbit_ring.rotation.x = sin(t * 0.5) * 0.3
		orbit_ring.scale = Vector3(ES, ES, ES)

	# Anneau dore secondaire
	var gold_ring: Node3D = container.get_node_or_null("GoldRing")
	if gold_ring:
		gold_ring.position = Vector3(sx, float_y - 0.5 * ES, sz)
		gold_ring.rotation.y = t * 0.5
		gold_ring.rotation.z = sin(t * 0.4) * 0.2
		gold_ring.rotation.x = cos(t * 0.3) * 0.15
		gold_ring.scale = Vector3(ES, ES, ES)

	# Construct hard-light rotatif
	var hardlight: Node3D = container.get_node_or_null("HardLightConstruct")
	if hardlight:
		var hl_angle: float = t * 1.5
		var hl_orbit: float = 3.5 * ES
		var hl_y: float = float_y + (1.5 + sin(t * 2.0) * 0.5) * ES
		hardlight.position = Vector3(sx + cos(hl_angle) * hl_orbit, hl_y, sz + sin(hl_angle) * hl_orbit)
		hardlight.rotation.y = t * 3.0
		hardlight.rotation.x = t * 2.0
		hardlight.rotation.z = t * 1.5
		var hl_pulse: float = ES * (1.0 + sin(t * 4.0) * 0.15)
		hardlight.scale = Vector3(hl_pulse, hl_pulse, hl_pulse)

	# Particules hexagonales
	for i in range(3):
		var hex_p: Node3D = container.get_node_or_null("HexParticle_%d" % i)
		if hex_p and hardlight:
			var hex_a: float = t * 3.0 + float(i) * TAU / 3.0
			var hex_r: float = (1.2 + sin(t * 2.0 + float(i)) * 0.3) * ES
			hex_p.position = Vector3(
				hardlight.position.x + cos(hex_a) * hex_r,
				hardlight.position.y + sin(t * 4.0 + float(i)) * 0.5 * ES,
				hardlight.position.z + sin(hex_a) * hex_r
			)
			hex_p.rotation.y = t * 5.0
			hex_p.scale = Vector3(ES, ES, ES)

	# Turrets hard-light
	var is_building: bool = mode == "building"
	for i in range(3):
		var turret: Node3D = container.get_node_or_null("Turret_%d" % i)
		if turret:
			var angle: float = t * 1.2 + float(i) * TAU / 3.0
			var orbit_r: float = (7.0 if is_building else 4.5) * ES
			var ty: float
			if is_building:
				ty = (2.0 + sin(t * 3.0 + float(i)) * 0.5) * ES
				angle = t * 2.5 + float(i) * TAU / 3.0
			else:
				ty = float_y + sin(t * 2.0 + float(i)) * 0.8 * ES
			turret.position = Vector3(sx + cos(angle) * orbit_r, ty, sz + sin(angle) * orbit_r)
			turret.scale = Vector3(ES, ES, ES)
			if is_building:
				var turret_mat: StandardMaterial3D = turret.material_override
				if turret_mat:
					turret_mat.emission_energy_multiplier = 3.0 + sin(t * 5.0 + float(i)) * 1.0

	# Mode building
	if is_building:
		var pulse: float = 0.7 + sin(t * 5.0) * 0.3
		var mat: StandardMaterial3D = _sym_mesh.material_override
		if mat:
			mat.albedo_color.a = pulse
			mat.emission_energy_multiplier = 2.5
		_sym_mesh.scale = Vector3(ES * 1.2, ES * 1.4, ES * 1.2)

		_sym_beam.visible = true
		_sym_beam.position = Vector3(sx, float_y - 3.0 * ES, sz)
		_sym_beam.rotation.x = PI
		var beam_pulse: float = (0.8 + sin(t * 8.0) * 0.2) * ES
		_sym_beam.scale = Vector3(beam_pulse, ES * (1.0 + sin(t * 3.0) * 0.2), beam_pulse)
		var beam_mat: StandardMaterial3D = _sym_beam.material_override
		if beam_mat:
			beam_mat.emission_energy_multiplier = 2.0 + sin(t * 6.0) * 1.5
	else:
		var mat: StandardMaterial3D = _sym_mesh.material_override
		if mat:
			mat.emission_energy_multiplier = 1.8
		_sym_beam.visible = false

	# Aura (agrandie)
	_sym_aura.position = Vector3(sx, 0.3, sz)
	var aura_s: float = ES * (1.0 + sin(t * 2.0) * 0.15)
	if is_building:
		aura_s *= 1.3
	_sym_aura.scale = Vector3(aura_s, 1.0, aura_s)

	# Label
	_sym_label.position = Vector3(sx, float_y + 7.0 * ES, sz)
	_sym_label.font_size = 48

	# Lumiere dynamique
	if _sym_light:
		_sym_light.position = Vector3(sx, float_y + 1.5 * ES, sz)
		if is_building:
			_sym_light.light_energy = (2.0 + sin(t * 4.0) * 0.8) * ES * 0.5
			_sym_light.omni_range = 55.0 * ES
		else:
			_sym_light.light_energy = (1.0 + sin(t * 1.5) * 0.2) * ES * 0.5
			_sym_light.omni_range = 40.0 * ES

	# Pilier lumineux (beacon)
	if _sym_beacon:
		_sym_beacon.position = Vector3(sx, BEACON_HEIGHT / 2.0, sz)
		var beacon_pulse: float = 0.8 + sin(t * 0.6) * 0.2
		_sym_beacon.scale.x = beacon_pulse
		_sym_beacon.scale.z = beacon_pulse


# ==================================================================
#  DAEDALUS
# ==================================================================

func _init_daedalus() -> void:
	var container := Node3D.new()
	container.name = "Daedalus"
	add_child(container)

	# Couleurs Daedalus -- violet/pourpre (innovation, creativite)
	var daedalus_purple := Color(0.615, 0.306, 0.918)    # #9d4edd
	var daedalus_light := Color(0.75, 0.5, 1.0)          # Violet clair
	var daedalus_deep := Color(0.4, 0.15, 0.7)           # Violet profond

	# Corps principal : icosahedron -- PBR violet metallique profond
	var body_mesh := SphereMesh.new()
	body_mesh.radius = 2.5
	body_mesh.height = 5.0
	body_mesh.radial_segments = 5   # Facettes icosahedriques
	body_mesh.rings = 3
	_daedalus_mesh = _create_pbr_mesh(body_mesh, Color(0.06, 0.02, 0.1, 0.95), daedalus_purple, 2.8, 0.8, 0.25)
	container.add_child(_daedalus_mesh)

	# Anneau d'innovation en orbite (torus violet)
	var ring := TorusMesh.new()
	ring.inner_radius = 3.5
	ring.outer_radius = 3.8
	ring.rings = 16
	ring.ring_segments = 12
	var ring_mi := _create_entity_mesh(ring, daedalus_light, 2.0)
	ring_mi.name = "InnovationRing"
	container.add_child(ring_mi)

	# Deuxieme anneau perpendiculaire (spirale d'idees)
	var ring2 := TorusMesh.new()
	ring2.inner_radius = 4.5
	ring2.outer_radius = 4.7
	ring2.rings = 12
	ring2.ring_segments = 8
	var ring2_mi := _create_entity_mesh(ring2, daedalus_deep, 1.5)
	ring2_mi.name = "SpiralRing"
	container.add_child(ring2_mi)

	# 4 particules d'idees (octahedrons en orbite -- questions/inspiration)
	for i in range(4):
		var idea_mesh := _make_octahedron(0.4)
		var idea := _create_entity_mesh(idea_mesh, daedalus_light, 3.0)
		idea.name = "Idea_%d" % i
		container.add_child(idea)

	# Aura violette (zone d'influence)
	_daedalus_aura = _create_aura(16.0, Color(daedalus_purple.r, daedalus_purple.g, daedalus_purple.b, 0.10))
	container.add_child(_daedalus_aura)

	# Label
	_daedalus_label = _create_label("DAEDALUS", daedalus_purple)
	container.add_child(_daedalus_label)

	# Trail d'innovation (trace violette)
	_daedalus_trail = MeshInstance3D.new()
	_daedalus_trail.name = "DaedalusTrail"
	var trail_mat := StandardMaterial3D.new()
	trail_mat.albedo_color = Color(daedalus_purple.r, daedalus_purple.g, daedalus_purple.b, 0.5)
	trail_mat.emission_enabled = true
	trail_mat.emission = daedalus_purple
	trail_mat.emission_energy_multiplier = 1.0
	trail_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	trail_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_daedalus_trail.material_override = trail_mat
	container.add_child(_daedalus_trail)

	# OmniLight3D -- lumiere violette d'innovation
	_daedalus_light = _create_entity_light(daedalus_purple, 2.5, 200.0)
	_daedalus_light.name = "DaedalusLight"
	container.add_child(_daedalus_light)

	# Pilier lumineux
	_daedalus_beacon = _create_beacon(daedalus_purple)
	container.add_child(_daedalus_beacon)

	container.visible = false


func update_daedalus(data: Dictionary) -> void:
	var container: Node3D = get_node_or_null("Daedalus")
	if not container:
		return

	if data.is_empty() or not data.get("enabled", false):
		container.visible = false
		return

	container.visible = true
	var dx: float = float(data.get("x", 250))
	var dz: float = float(data.get("z", 125))
	var t: float = Time.get_ticks_msec() / 1000.0
	var seekers: int = int(data.get("current_seekers", 0))
	var ES: float = ENTITY_SCALE

	# Corps (x4)
	var float_y: float = (5.5 + sin(t * 1.1) * 1.5) * ES
	_daedalus_mesh.position = Vector3(dx, float_y, dz)
	_daedalus_mesh.rotation.y = t * 0.7
	_daedalus_mesh.rotation.x = sin(t * 0.4) * 0.2
	_daedalus_mesh.rotation.z = cos(t * 0.5) * 0.15
	_daedalus_mesh.scale = Vector3(ES, ES, ES)

	# Anneau d'innovation
	var ring: Node3D = container.get_node_or_null("InnovationRing")
	if ring:
		ring.position = Vector3(dx, float_y, dz)
		ring.rotation.y = -t * 0.9
		ring.rotation.x = sin(t * 0.6) * 0.3
		var ring_pulse: float = ES * (1.0 + minf(float(seekers), 10.0) * 0.03)
		ring.scale = Vector3(ring_pulse, ring_pulse, ring_pulse)

	# Anneau spirale perpendiculaire
	var ring2: Node3D = container.get_node_or_null("SpiralRing")
	if ring2:
		ring2.position = Vector3(dx, float_y, dz)
		ring2.rotation.z = t * 0.5
		ring2.rotation.y = cos(t * 0.3) * 0.4
		ring2.scale = Vector3(ES, ES, ES)

	# 4 particules d'idees
	for i in range(4):
		var idea: Node3D = container.get_node_or_null("Idea_%d" % i)
		if idea:
			var angle: float = t * 1.2 + float(i) * TAU / 4.0
			var orbit_r: float = (6.0 + sin(t * 0.8 + float(i)) * 1.0) * ES
			var iy: float = float_y + sin(t * 2.0 + float(i) * 1.5) * 1.5 * ES
			idea.position = Vector3(
				dx + cos(angle) * orbit_r,
				iy,
				dz + sin(angle) * orbit_r
			)
			idea.rotation.y = t * 3.0 + float(i)
			idea.rotation.x = t * 2.0
			idea.scale = Vector3(ES, ES, ES)

	# Boost emission
	var mat: StandardMaterial3D = _daedalus_mesh.material_override
	if mat:
		if seekers > 0:
			mat.emission_energy_multiplier = 2.5 + minf(float(seekers), 10.0) * 0.3
		else:
			mat.emission_energy_multiplier = 2.5

	# Aura (agrandie)
	_daedalus_aura.position = Vector3(dx, 0.3, dz)
	var base_aura: float = ES * (1.0 + sin(t * 2.5) * 0.15)
	var seek_boost: float = 1.0 + minf(float(seekers), 10.0) * 0.04
	_daedalus_aura.scale = Vector3(base_aura * seek_boost, 1.0, base_aura * seek_boost)

	# Label
	_daedalus_label.position = Vector3(dx, float_y + 7.5 * ES, dz)
	_daedalus_label.font_size = 48

	# Lumiere dynamique
	if _daedalus_light:
		_daedalus_light.position = Vector3(dx, float_y + 1.5 * ES, dz)
		var light_pulse: float = (1.0 + sin(t * 1.8) * 0.3) * ES * 0.5
		if seekers > 0:
			light_pulse += minf(float(seekers), 10.0) * 0.1
		_daedalus_light.light_energy = light_pulse
		_daedalus_light.omni_range = 50.0 * ES

	# Trail (world space -- pas scale)
	_daedalus_trail_points.append(Vector3(dx, 2.0, dz))
	if _daedalus_trail_points.size() > 80:
		_daedalus_trail_points = _daedalus_trail_points.slice(-80)
	if _daedalus_trail_points.size() >= 2:
		_daedalus_trail.visible = true
		var im := ImmediateMesh.new()
		im.surface_begin(Mesh.PRIMITIVE_LINE_STRIP)
		for pt in _daedalus_trail_points:
			im.surface_add_vertex(pt)
		im.surface_end()
		_daedalus_trail.mesh = im
	else:
		_daedalus_trail.visible = false

	# Pilier lumineux (beacon)
	if _daedalus_beacon:
		_daedalus_beacon.position = Vector3(dx, BEACON_HEIGHT / 2.0, dz)
		var beacon_pulse: float = 0.8 + sin(t * 0.8) * 0.2
		_daedalus_beacon.scale.x = beacon_pulse
		_daedalus_beacon.scale.z = beacon_pulse


# ==================================================================
#  UTILITAIRES
# ==================================================================

func _make_symmetra_prism(radius: float, height: float) -> Mesh:
	"""Cree un prisme hexagonal allonge (diamant hard-light Symmetra)."""
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)

	var top := Vector3(0, height * 0.6, 0)
	var bot := Vector3(0, -height * 0.4, 0)
	var mid_pts: Array[Vector3] = []

	# 6 points au milieu (hexagone aplati)
	for i in range(6):
		var angle: float = float(i) / 6.0 * TAU
		mid_pts.append(Vector3(cos(angle) * radius, 0, sin(angle) * radius))

	# 6 faces vers le haut
	for i in range(6):
		st.add_vertex(top)
		st.add_vertex(mid_pts[i])
		st.add_vertex(mid_pts[(i + 1) % 6])

	# 6 faces vers le bas
	for i in range(6):
		st.add_vertex(bot)
		st.add_vertex(mid_pts[(i + 1) % 6])
		st.add_vertex(mid_pts[i])

	st.generate_normals()
	return st.commit()


func _make_octahedron(size: float) -> Mesh:
	"""Cree un octahedron (8 faces) en mesh."""
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)

	var top := Vector3(0, size, 0)
	var bot := Vector3(0, -size, 0)
	var pts: Array[Vector3] = [
		Vector3(size, 0, 0), Vector3(0, 0, size),
		Vector3(-size, 0, 0), Vector3(0, 0, -size)
	]

	# 4 faces du haut
	for i in range(4):
		st.add_vertex(top)
		st.add_vertex(pts[i])
		st.add_vertex(pts[(i + 1) % 4])

	# 4 faces du bas
	for i in range(4):
		st.add_vertex(bot)
		st.add_vertex(pts[(i + 1) % 4])
		st.add_vertex(pts[i])

	st.generate_normals()
	return st.commit()


func _create_entity_mesh(mesh: Mesh, color: Color, emission_energy: float) -> MeshInstance3D:
	"""Cree un MeshInstance3D avec material neon unshaded (pour elements lumineux purs)."""
	var mi := MeshInstance3D.new()
	mi.mesh = mesh

	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(color.r, color.g, color.b, 0.9)
	mat.emission_enabled = true
	mat.emission = color
	mat.emission_energy_multiplier = emission_energy
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mi.material_override = mat

	return mi


func _create_pbr_mesh(mesh: Mesh, albedo_color: Color, emission_color: Color, emission_energy: float, metallic_val: float = 0.8, roughness_val: float = 0.2) -> MeshInstance3D:
	"""Cree un MeshInstance3D PBR metallique avec emission neon (pour corps solides)."""
	var mi := MeshInstance3D.new()
	mi.mesh = mesh

	var mat := StandardMaterial3D.new()
	mat.albedo_color = albedo_color
	mat.metallic = metallic_val
	mat.roughness = roughness_val
	mat.emission_enabled = true
	mat.emission = emission_color
	mat.emission_energy_multiplier = emission_energy
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	mat.rim_enabled = true
	mat.rim = 0.3
	mat.rim_tint = 0.5
	mi.material_override = mat

	return mi


func _create_aura(radius: float, color: Color) -> MeshInstance3D:
	"""Cree un disque d'aura au sol."""
	var disc := PlaneMesh.new()
	disc.size = Vector2(radius * 2.0, radius * 2.0)

	var mi := MeshInstance3D.new()
	mi.name = "Aura"
	mi.mesh = disc

	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.emission_enabled = true
	mat.emission = Color(color.r, color.g, color.b)
	mat.emission_energy_multiplier = 0.3
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mi.material_override = mat

	return mi


func _create_label(text: String, color: Color) -> Label3D:
	"""Cree un label 3D flottant au-dessus d'une entite -- visible de loin."""
	var label := Label3D.new()
	label.name = "Label"
	label.text = text
	label.font_size = 128
	label.pixel_size = 0.5
	label.modulate = color
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.no_depth_test = true
	label.outline_size = 10
	label.outline_modulate = Color(0, 0, 0, 0.9)
	return label


func _create_entity_light(color: Color, energy: float, light_range: float) -> OmniLight3D:
	"""Cree un OmniLight3D colore pour eclairer dynamiquement les environs."""
	var light := OmniLight3D.new()
	light.light_color = color
	light.light_energy = energy
	light.omni_range = light_range
	light.omni_attenuation = 1.5
	light.shadow_enabled = false  # Perf: pas d'ombres dynamiques par entite
	light.light_bake_mode = Light3D.BAKE_DISABLED
	return light


func _create_beacon(color: Color) -> MeshInstance3D:
	"""Cree un pilier lumineux vertical geant -- visible a des km sur la grille 10000."""
	var beam_mesh := CylinderMesh.new()
	beam_mesh.top_radius = 3.0
	beam_mesh.bottom_radius = 8.0
	beam_mesh.height = BEACON_HEIGHT
	beam_mesh.radial_segments = 6
	var mi := MeshInstance3D.new()
	mi.mesh = beam_mesh
	mi.name = "Beacon"
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(color.r, color.g, color.b, 0.15)
	mat.emission_enabled = true
	mat.emission = color
	mat.emission_energy_multiplier = 3.0
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.no_depth_test = true
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mi.material_override = mat
	return mi
