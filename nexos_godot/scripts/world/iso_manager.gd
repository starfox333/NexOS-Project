extends Node3D
## Gestionnaire des ISOs -- Systeme Hybride LOD (Sims 4 x Tron)
## Males (id pair) : corps STANDARD, circuits cyan/bleu
## Femelles (id impair) : corps SLIM, circuits rose/magenta
## Tier 1 (proches) : ISOs animes avec squelette FBX (pool de 50)
## Tier 2 (lointains) : MultiMeshInstance3D procedural (bob + rotate)

const MAX_ISOS := 10000  ## Population max (grille 10000x10000)
const MAX_PER_GENDER := 5000  ## Max par MultiMesh (male ou femelle)
const ANIMATED_POOL_SIZE := 50  ## Nombre max d'ISOs animes simultanement
const LOD_DISTANCE := 500.0  ## Distance de bascule Tier1 <-> Tier2 (grille 5000)
const ISO_BASE_SCALE := 40.0  ## Echelle agrandie pour grille 5000x5000
const ISOBody := preload("res://scripts/world/iso_body.gd")

## --- Modele GLB 3D (priorite sur procedural) ---
var _glb_scene: PackedScene = null  ## Scene GLB chargee
var _glb_mesh_male: Mesh = null     ## Mesh extraite du GLB pour MultiMesh males
var _glb_mesh_female: Mesh = null   ## Mesh extraite du GLB pour MultiMesh femelles
var _use_glb := false               ## True si GLB charge avec succes

## --- MultiMesh (Tier 2 : ISOs lointains) ---
## Deux MultiMesh : males (STANDARD) et femelles (SLIM)
var _mm_male: MultiMesh
var _mmi_male: MultiMeshInstance3D
var _mm_female: MultiMesh
var _mmi_female: MultiMeshInstance3D
var _active_count := 0

## --- Pool anime (Tier 1 : ISOs proches) ---
var _animated_pool: Array[Node3D] = []  ## Pool d'instances animees pre-allouees
var _pool_anim_players: Array = []  ## AnimationPlayer par slot
var _pool_materials: Array[StandardMaterial3D] = []  ## Material par slot
var _pool_in_use: Array[bool] = []  ## Slot utilise ou libre
var _pool_iso_id: Array[int] = []  ## ID de l'ISO assigne a ce slot
var _pool_current_anim: Array[String] = []  ## Animation en cours par slot
var _pool_is_female: Array[bool] = []  ## Genre du slot

## --- Animation Loader ---
var _anim_loader: Node = null  ## Reference au ISOAnimationLoader

## --- Camera ---
var _camera_pos := Vector3(1000, 60, 1000)  ## Position camera pour calcul LOD

## --- Tracking ---
var _iso_to_pool: Dictionary = {}  ## iso_id -> pool_index


func _ready() -> void:
	_try_load_glb_characters()
	_setup_multimesh()
	# Si GLB dispo mais pas de loader d'animations, creer le pool directement
	if _use_glb:
		call_deferred("_setup_animated_pool_if_needed")


func set_animation_loader(loader: Node) -> void:
	"""Assigne le loader d'animations (appele depuis main.gd)."""
	_anim_loader = loader
	call_deferred("_setup_animated_pool")


func _setup_animated_pool_if_needed() -> void:
	"""Cree le pool anime si pas deja fait (appele quand GLB dispo sans anim_loader)."""
	if _animated_pool.size() > 0:
		return  # Deja cree
	_setup_animated_pool()


# ==================================================================
#  CHARGEMENT GLB CHARACTERS
# ==================================================================

func _try_load_glb_characters() -> void:
	"""Tente de charger le modele GLB de personnages 3D."""
	var glb_paths := [
		"res://assets/models/bodies/tron_catalyst_characters_wip.glb",
	]
	for path in glb_paths:
		if ResourceLoader.exists(path):
			var scene: PackedScene = load(path)
			if scene:
				_glb_scene = scene
				_use_glb = true
				print("[ISOManager] Modele GLB charge: %s" % path.get_file())
				# Extraire les meshes pour le MultiMesh
				_extract_glb_meshes()
				return
	print("[ISOManager] Aucun modele GLB personnage -- fallback procedural")


func _extract_glb_meshes() -> void:
	"""Extrait les meshes du GLB pour les utiliser dans le MultiMesh."""
	if not _glb_scene:
		return
	var instance: Node3D = _glb_scene.instantiate()
	# Debug : afficher l'arbre de nodes du GLB
	print("[ISOManager] Arbre GLB personnages:")
	_print_glb_tree(instance, 0)
	# Collecter toutes les MeshInstance3D
	var meshes := _collect_all_meshes(instance)
	if meshes.size() > 0:
		# Utiliser le premier mesh trouve pour males
		_glb_mesh_male = meshes[0].mesh
		# Si plusieurs meshes, le second pour femelles ; sinon meme mesh
		if meshes.size() > 1:
			_glb_mesh_female = meshes[1].mesh
		else:
			_glb_mesh_female = meshes[0].mesh
		print("[ISOManager] Meshes GLB extraits: %d trouves (male=%s, female=%s)" % [
			meshes.size(),
			_glb_mesh_male.get_class() if _glb_mesh_male else "null",
			_glb_mesh_female.get_class() if _glb_mesh_female else "null"])
	else:
		print("[ISOManager] Aucun mesh dans le GLB -- fallback procedural")
		_use_glb = false
	instance.queue_free()


func _print_glb_tree(node: Node, depth: int) -> void:
	"""Affiche l'arbre de nodes d'un GLB pour debug."""
	var indent := "  ".repeat(depth)
	var info := "%s%s [%s]" % [indent, node.name, node.get_class()]
	if node is MeshInstance3D:
		var mi: MeshInstance3D = node
		info += " mesh=%s" % (mi.mesh.get_class() if mi.mesh else "null")
		if mi.mesh:
			info += " surfaces=%d" % mi.mesh.get_surface_count()
	print(info)
	if depth < 4:  # Limiter la profondeur
		for child in node.get_children():
			_print_glb_tree(child, depth + 1)


func _collect_all_meshes(node: Node) -> Array[MeshInstance3D]:
	"""Collecte recursivement toutes les MeshInstance3D d'un arbre de nodes."""
	var result: Array[MeshInstance3D] = []
	if node is MeshInstance3D and node.mesh:
		result.append(node)
	for child in node.get_children():
		var child_meshes := _collect_all_meshes(child)
		result.append_array(child_meshes)
	return result


# ==================================================================
#  MULTIMESH SETUP -- Deux meshes genres
# ==================================================================

func _setup_multimesh() -> void:
	"""Configure les MultiMesh males et femelles (GLB ou procedural)."""
	# --- Males ---
	var male_mesh: Mesh
	if _use_glb and _glb_mesh_male:
		male_mesh = _glb_mesh_male
		print("[ISOManager] MultiMesh males: mesh GLB 3D")
	else:
		male_mesh = ISOBody.create_humanoid_mesh(ISOBody.BodyType.STANDARD)
		print("[ISOManager] MultiMesh males: mesh procedural")

	_mm_male = MultiMesh.new()
	_mm_male.transform_format = MultiMesh.TRANSFORM_3D
	_mm_male.use_colors = true
	_mm_male.mesh = male_mesh
	_mm_male.instance_count = MAX_PER_GENDER
	for i in range(MAX_PER_GENDER):
		_mm_male.set_instance_transform(i, Transform3D().scaled(Vector3.ZERO))
		_mm_male.set_instance_color(i, Color.TRANSPARENT)

	_mmi_male = MultiMeshInstance3D.new()
	_mmi_male.name = "ISOInstances_Males"
	_mmi_male.multimesh = _mm_male
	_mmi_male.material_override = _create_iso_material()
	add_child(_mmi_male)

	# --- Femelles ---
	var female_mesh: Mesh
	if _use_glb and _glb_mesh_female:
		female_mesh = _glb_mesh_female
		print("[ISOManager] MultiMesh femelles: mesh GLB 3D")
	else:
		female_mesh = ISOBody.create_humanoid_mesh(ISOBody.BodyType.SLIM)
		print("[ISOManager] MultiMesh femelles: mesh procedural")

	_mm_female = MultiMesh.new()
	_mm_female.transform_format = MultiMesh.TRANSFORM_3D
	_mm_female.use_colors = true
	_mm_female.mesh = female_mesh
	_mm_female.instance_count = MAX_PER_GENDER
	for i in range(MAX_PER_GENDER):
		_mm_female.set_instance_transform(i, Transform3D().scaled(Vector3.ZERO))
		_mm_female.set_instance_color(i, Color.TRANSPARENT)

	_mmi_female = MultiMeshInstance3D.new()
	_mmi_female.name = "ISOInstances_Females"
	_mmi_female.multimesh = _mm_female
	_mmi_female.material_override = _create_iso_material()
	add_child(_mmi_female)

	print("[ISOManager] Dual MultiMesh cree : %d males + %d femelles (GLB=%s)" % [
		MAX_PER_GENDER, MAX_PER_GENDER, "OUI" if _use_glb else "NON"])


func _create_iso_material() -> StandardMaterial3D:
	"""Material PBR metallique Tron commun aux MultiMesh."""
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.albedo_color = Color(0.06, 0.06, 0.08, 0.92)
	mat.metallic = 0.85
	mat.roughness = 0.25
	mat.emission_enabled = true
	mat.emission = Color(0.0, 0.9, 0.75)
	mat.emission_energy_multiplier = 2.5
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	mat.rim_enabled = true
	mat.rim = 0.4
	mat.rim_tint = 0.5
	return mat


# ==================================================================
#  ANIMATED POOL (Tier 1)
# ==================================================================

func _setup_animated_pool() -> void:
	"""Cree le pool d'ISOs animes (Tier 1)."""
	if not _anim_loader and not _use_glb:
		print("[ISOManager] Ni loader d'animations ni GLB, pool anime desactive")
		return
	if _anim_loader and not _anim_loader.is_loaded:
		for attempt in range(10):
			await get_tree().create_timer(0.5).timeout
			if _anim_loader and _anim_loader.is_loaded:
				break
		if _anim_loader and not _anim_loader.is_loaded:
			print("[ISOManager] Loader non pret apres 5s, utilisation GLB/procedural")
			# Continuer quand meme si on a le GLB

	var container := Node3D.new()
	container.name = "ISOInstances_Tier1"
	add_child(container)

	for i in range(ANIMATED_POOL_SIZE):
		var iso_node: Node3D
		var is_female: bool = (i % 2 == 1)  # Alternance male/femelle dans le pool

		if _anim_loader and _anim_loader.has_method("create_animated_iso"):
			iso_node = _anim_loader.create_animated_iso()
		else:
			iso_node = _create_pool_fallback(is_female)

		iso_node.name = "AnimISO_%d" % i
		iso_node.visible = false
		container.add_child(iso_node)

		_animated_pool.append(iso_node)
		_pool_in_use.append(false)
		_pool_iso_id.append(-1)
		_pool_current_anim.append("")
		_pool_is_female.append(is_female)

		var anim_player = null
		if _anim_loader and _anim_loader.has_method("_find_animation_player"):
			anim_player = _anim_loader._find_animation_player(iso_node)
		_pool_anim_players.append(anim_player)

		var mat := _find_or_create_material(iso_node)
		_pool_materials.append(mat)

	var has_anims: bool = _anim_loader != null and _anim_loader.get("available_anims") != null and _anim_loader.available_anims.size() > 0
	print("[ISOManager] Pool anime cree (%d slots, GLB=%s, FBX_Anims=%s)" % [
		ANIMATED_POOL_SIZE,
		"OUI" if _use_glb else "NON",
		"OUI" if has_anims else "NON"
	])


func _create_pool_fallback(is_female: bool) -> Node3D:
	"""Cree un ISO pour le pool anime : GLB 3D si dispo, sinon procedural."""
	# Essayer le modele GLB d'abord
	if _use_glb and _glb_scene:
		var glb_instance: Node3D = _glb_scene.instantiate()
		# Appliquer un material Tron emissif sur tous les meshes du GLB
		_apply_tron_material_recursive(glb_instance, is_female)
		return glb_instance

	# Fallback procedural
	var root := Node3D.new()
	var mesh_inst := MeshInstance3D.new()
	var body_type: int = ISOBody.BodyType.SLIM if is_female else ISOBody.BodyType.STANDARD
	mesh_inst.mesh = ISOBody.create_humanoid_mesh(body_type)

	var mat := _create_tron_body_material(is_female)
	mesh_inst.material_override = mat

	root.add_child(mesh_inst)
	return root


func _apply_tron_material_recursive(node: Node, is_female: bool) -> void:
	"""Applique un material Tron emissif a tous les MeshInstance3D d'un arbre."""
	if node is MeshInstance3D:
		var mat := _create_tron_body_material(is_female)
		node.material_override = mat
	for child in node.get_children():
		_apply_tron_material_recursive(child, is_female)


func _create_tron_body_material(is_female: bool) -> StandardMaterial3D:
	"""Cree un material PBR Tron pour un corps d'ISO."""
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.06, 0.06, 0.08, 0.92)
	mat.metallic = 0.85
	mat.roughness = 0.25
	mat.emission_enabled = true
	mat.emission = Color(0.0, 0.9, 0.75) if not is_female else Color(0.9, 0.2, 0.7)
	mat.emission_energy_multiplier = 2.5
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	mat.rim_enabled = true
	mat.rim = 0.4
	mat.rim_tint = 0.5
	return mat


func update_camera_pos(cam_pos: Vector3) -> void:
	"""Met a jour la position camera pour le calcul LOD."""
	_camera_pos = cam_pos


# ==================================================================
#  UPDATE PRINCIPAL
# ==================================================================

var _debug_logged := false  ## Flag pour log unique

func update_isos(isos: Array, minerve_pos: Dictionary = {}, tron_pos: Dictionary = {}) -> void:
	"""Met a jour toutes les instances ISO (hybride Tier1 + Tier2 genres)."""
	var time_val: float = Time.get_ticks_msec() / 1000.0
	_active_count = mini(isos.size(), MAX_ISOS)

	# Debug unique
	if not _debug_logged and isos.size() > 0:
		_debug_logged = true
		print("[ISOManager] Premier update: %d ISOs recus (scale x%.1f)" % [isos.size(), ISO_BASE_SCALE])
		print("[ISOManager] Pool anime: %d slots | MultiMesh: %d males + %d femelles" % [
			_animated_pool.size(), MAX_PER_GENDER, MAX_PER_GENDER])
		if isos.size() > 0:
			var first: Dictionary = isos[0]
			print("[ISOManager] Exemple ISO: id=%s x=%s z=%s energy=%s" % [
				first.get("id", "?"), first.get("x", "?"), first.get("z", "?"), first.get("energy", "?")])

	# Positions des entites pour effets de proximite
	var has_minerve: bool = not minerve_pos.is_empty() and minerve_pos.get("enabled", false)
	var mx: float = float(minerve_pos.get("x", 0)) if has_minerve else 0.0
	var mz: float = float(minerve_pos.get("z", 0)) if has_minerve else 0.0
	var has_tron: bool = not tron_pos.is_empty() and tron_pos.get("enabled", false)
	var tx: float = float(tron_pos.get("x", 0)) if has_tron else 0.0
	var tz: float = float(tron_pos.get("z", 0)) if has_tron else 0.0

	# --- Phase 1 : Trier par distance ---
	var iso_distances: Array = []
	for i in range(_active_count):
		var iso: Dictionary = isos[i]
		var x: float = float(iso.get("x", 0))
		var z: float = float(iso.get("z", 0))
		var dist: float = Vector2(x - _camera_pos.x, z - _camera_pos.z).length()
		iso_distances.append({"idx": i, "dist": dist, "data": iso})
	iso_distances.sort_custom(func(a, b): return a["dist"] < b["dist"])

	# --- Phase 2 : Repartir Tier 1 vs Tier 2 ---
	var animated_isos: Array = []
	var multimesh_isos: Array = []
	var pool_available: bool = _animated_pool.size() > 0
	for entry in iso_distances:
		if pool_available and entry["dist"] < LOD_DISTANCE and animated_isos.size() < ANIMATED_POOL_SIZE:
			animated_isos.append(entry)
		else:
			multimesh_isos.append(entry)

	# --- Phase 3 : Liberer les slots inutilises ---
	var new_animated_ids: Dictionary = {}
	for entry in animated_isos:
		var iso_id: int = int(entry["data"].get("id", entry["idx"]))
		new_animated_ids[iso_id] = true
	for slot_idx in range(_animated_pool.size()):
		if _pool_in_use[slot_idx]:
			if _pool_iso_id[slot_idx] not in new_animated_ids:
				_release_pool_slot(slot_idx)

	# --- Phase 4 : Mettre a jour les ISOs animes (Tier 1) ---
	for entry in animated_isos:
		var iso: Dictionary = entry["data"]
		var iso_id: int = int(iso.get("id", entry["idx"]))
		var x: float = float(iso.get("x", 0))
		var z: float = float(iso.get("z", 0))
		var energy: float = float(iso.get("energy", 100))
		var max_energy: float = float(iso.get("max_energy", 200))
		var gen: int = int(iso.get("generation", 0))
		var action: String = str(iso.get("last_action", "idle"))
		var is_female: bool = (iso_id % 2 == 1)

		var slot_idx: int = _get_or_assign_slot(iso_id)
		if slot_idx < 0:
			multimesh_isos.append(entry)
			continue

		var iso_node: Node3D = _animated_pool[slot_idx]

		# Scale : base x5 + bonus generation
		var gen_bonus: float = 1.0 + minf(float(gen), 10.0) * 0.06
		var gender_scale: float = 0.88 if is_female else 1.0  # Femelles un peu plus petites
		var s: float = ISO_BASE_SCALE * gen_bonus * gender_scale

		iso_node.position = Vector3(x, 0.0, z)
		iso_node.scale = Vector3(s, s, s)

		# Rotation douce
		var rot_y: float = float(iso_id) * 1.37 + sin(time_val * 0.5 + float(iso_id)) * 0.3
		iso_node.rotation.y = rot_y
		iso_node.visible = true

		# Couleur genree selon energie
		var ratio: float = energy / maxf(1.0, max_energy)
		var color: Color = _get_gendered_color(ratio, is_female)

		# Boosts de proximite
		if has_minerve and absf(x - mx) <= 20.0 and absf(z - mz) <= 20.0:
			color = Color(1.0, 0.92, 0.5, 1.0) if not is_female else Color(1.0, 0.85, 0.6, 1.0)
			iso_node.scale *= 1.15
		if has_tron and absf(x - tx) <= 15.0 and absf(z - tz) <= 15.0:
			color = Color(0.0, 0.898, 1.0, 0.95) if not is_female else Color(0.6, 0.2, 1.0, 0.95)
			iso_node.scale *= 1.1

		# Appliquer couleur
		if slot_idx < _pool_materials.size() and _pool_materials[slot_idx]:
			_pool_materials[slot_idx].emission = color
			_pool_materials[slot_idx].emission_energy_multiplier = 2.5
			_pool_materials[slot_idx].albedo_color = Color(color.r * 0.15, color.g * 0.15, color.b * 0.15, 0.92)

		# Animation
		if energy < 10:
			action = "dying"
		_play_animation_for_action(slot_idx, action, iso_id)

	# --- Phase 5 : MultiMesh genres (Tier 2) ---
	var mm_male_idx := 0
	var mm_female_idx := 0

	for entry in multimesh_isos:
		var iso: Dictionary = entry["data"]
		var x: float = float(iso.get("x", 0))
		var z: float = float(iso.get("z", 0))
		var energy: float = float(iso.get("energy", 100))
		var max_energy: float = float(iso.get("max_energy", 200))
		var gen: int = int(iso.get("generation", 0))
		var id: int = int(iso.get("id", entry["idx"]))
		var is_female: bool = (id % 2 == 1)

		var bob_y: float = 0.5 + sin(time_val * 2.0 + float(id) * 0.7) * 0.3
		var gen_bonus: float = 1.0 + minf(float(gen), 10.0) * 0.06
		var gender_scale: float = 0.88 if is_female else 1.0
		var s: float = ISO_BASE_SCALE * gen_bonus * gender_scale
		var rot_y: float = float(id) * 1.37 + sin(time_val * 0.5 + float(id)) * 0.3

		var ratio: float = energy / maxf(1.0, max_energy)
		var color: Color = _get_gendered_color(ratio, is_female)

		if has_minerve and absf(x - mx) <= 20.0 and absf(z - mz) <= 20.0:
			color = Color(1.0, 0.92, 0.5, 1.0) if not is_female else Color(1.0, 0.85, 0.6, 1.0)
			s *= 1.15
		if has_tron and absf(x - tx) <= 15.0 and absf(z - tz) <= 15.0:
			color = Color(0.0, 0.898, 1.0, 0.95) if not is_female else Color(0.6, 0.2, 1.0, 0.95)
			s *= 1.1

		var xform := Transform3D()
		xform = xform.scaled(Vector3(s, s, s))
		xform = xform.rotated(Vector3.UP, rot_y)
		xform.origin = Vector3(x, bob_y, z)

		if is_female:
			if mm_female_idx < MAX_PER_GENDER:
				_mm_female.set_instance_transform(mm_female_idx, xform)
				_mm_female.set_instance_color(mm_female_idx, color)
				mm_female_idx += 1
		else:
			if mm_male_idx < MAX_PER_GENDER:
				_mm_male.set_instance_transform(mm_male_idx, xform)
				_mm_male.set_instance_color(mm_male_idx, color)
				mm_male_idx += 1

	# Masquer les instances inutilisees
	for i in range(mm_male_idx, MAX_PER_GENDER):
		_mm_male.set_instance_transform(i, Transform3D().scaled(Vector3.ZERO))
		_mm_male.set_instance_color(i, Color.TRANSPARENT)
	for i in range(mm_female_idx, MAX_PER_GENDER):
		_mm_female.set_instance_transform(i, Transform3D().scaled(Vector3.ZERO))
		_mm_female.set_instance_color(i, Color.TRANSPARENT)


# ==================================================================
#  GESTION DU POOL ANIME
# ==================================================================

func _get_or_assign_slot(iso_id: int) -> int:
	"""Retourne le slot existant pour cet ISO, ou en assigne un nouveau."""
	if iso_id in _iso_to_pool:
		return _iso_to_pool[iso_id]
	for i in range(_animated_pool.size()):
		if not _pool_in_use[i]:
			_pool_in_use[i] = true
			_pool_iso_id[i] = iso_id
			_pool_current_anim[i] = ""
			_iso_to_pool[iso_id] = i
			return i
	return -1


func _release_pool_slot(slot_idx: int) -> void:
	"""Libere un slot du pool anime."""
	if slot_idx < 0 or slot_idx >= _animated_pool.size():
		return
	var old_id: int = _pool_iso_id[slot_idx]
	_animated_pool[slot_idx].visible = false
	_pool_in_use[slot_idx] = false
	_pool_iso_id[slot_idx] = -1
	_pool_current_anim[slot_idx] = ""
	if old_id in _iso_to_pool:
		_iso_to_pool.erase(old_id)


func _play_animation_for_action(slot_idx: int, action: String, iso_id: int) -> void:
	"""Joue l'animation correspondant a l'action sur le slot donne."""
	if not _anim_loader:
		return
	var target_anim: String = _anim_loader.get_anim_for_action(action, iso_id)
	if target_anim.is_empty():
		return
	if _pool_current_anim[slot_idx] == target_anim:
		return
	_pool_current_anim[slot_idx] = target_anim
	if slot_idx < _pool_anim_players.size() and _pool_anim_players[slot_idx]:
		var anim_player: AnimationPlayer = _pool_anim_players[slot_idx]
		if anim_player.has_animation(target_anim):
			anim_player.play(target_anim)
		elif anim_player.has_animation("iso/" + target_anim):
			anim_player.play("iso/" + target_anim)


# ==================================================================
#  COULEURS GENREES
# ==================================================================

func _get_gendered_color(ratio: float, is_female: bool) -> Color:
	"""Couleur selon energie + genre. Males = cyan/bleu, Femelles = rose/magenta."""
	if is_female:
		if ratio > 0.7:
			return Color(1.0, 0.3, 0.75, 0.9)   # Rose vif
		elif ratio > 0.4:
			return Color(0.85, 0.4, 0.85, 0.85)  # Magenta
		else:
			return Color(0.8, 0.15, 0.3, 0.8)    # Rouge rosace
	else:
		if ratio > 0.7:
			return Color(0.0, 0.9, 1.0, 0.9)     # Cyan vif
		elif ratio > 0.4:
			return Color(0.2, 0.6, 1.0, 0.85)    # Bleu electrique
		else:
			return Color(1.0, 0.3, 0.2, 0.8)     # Rouge deresolution


# ==================================================================
#  UTILITAIRES
# ==================================================================

func _find_or_create_material(node: Node) -> StandardMaterial3D:
	"""Trouve le premier material modifiable ou en cree un."""
	if node is MeshInstance3D and node.material_override:
		return node.material_override
	for child in node.get_children():
		var mat := _find_or_create_material(child)
		if mat:
			return mat
	return null


func get_active_count() -> int:
	return _active_count


func get_animated_count() -> int:
	"""Retourne le nombre d'ISOs actuellement animes (Tier 1)."""
	var count := 0
	for in_use in _pool_in_use:
		if in_use:
			count += 1
	return count
