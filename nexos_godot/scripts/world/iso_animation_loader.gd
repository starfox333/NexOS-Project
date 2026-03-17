extends Node
## Chargeur d'animations FBX pour les ISOs
## Scanne assets/animations/, charge les FBX Mixamo,
## cree un template de scene clonable avec AnimationPlayer.
## Fournit le mapping action_ISO -> animation_name.

## Mapping action Python -> nom d'animation interne
const ACTION_ANIMS := {
	"idle": "breathing_idle",
	"rest": "laying_idle",
	"explore": "walking",
	"move_to_energy": "walking",
	"harvest": "standup_sitdown",
	"reproduce": "idle_basic",
	"signal": "disc_draw",
	"share_energy": "walking_stairs",
	"cooperate": "butterfly_twirl",
	"dying": "falling",
}

## Variantes de marche (choisies aleatoirement pour varier)
const WALK_VARIANTS := ["walking", "happy_walk", "swagger_walk"]

## Variantes d'esquive / combat (pour Tron)
const COMBAT_ANIMS := ["butterfly_twirl", "aerial_evade", "macaco_side", "esquiva", "au_to_role"]

## Mapping fichier FBX -> nom interne
const FBX_MAP := {
	"Breathing Idle": "breathing_idle",
	"Idle": "idle_basic",
	"Walking": "walking",
	"Happy Walk": "happy_walk",
	"Swagger Walk": "swagger_walk",
	"Walking Up The Stairs": "walking_stairs",
	"Climbing": "climbing",
	"Falling": "falling",
	"Falling To Roll": "falling_roll",
	"Run To Rolling": "run_rolling",
	"Laying Idle": "laying_idle",
	"Lying Down": "lying_down",
	"Male Laying Pose": "male_laying",
	"Female Laying Pose": "female_laying",
	"standup_sitdown": "standup_sitdown",
	"Put Back Rifle Behind Shoulder": "disc_draw",
	"Butterfly Twirl": "butterfly_twirl",
	"Aerial Evade": "aerial_evade",
	"Macaco Side": "macaco_side",
	"Esquiva 2": "esquiva",
	"Au To Role": "au_to_role",
}

## Scene template chargee (le premier FBX avec squelette)
var _template_scene: PackedScene = null

## AnimationLibrary combinee avec toutes les anims
var _anim_library: AnimationLibrary = null

## Indique si le chargement est termine
var is_loaded := false

## Liste des animations disponibles
var available_anims: Array[String] = []


func _ready() -> void:
	_load_animations()


func _load_animations() -> void:
	"""Charge tous les FBX d'animation et construit la library."""
	var anim_dir := "res://assets/animations/"
	var dir := DirAccess.open(anim_dir)
	if not dir:
		push_warning("[AnimLoader] Dossier animations introuvable: " + anim_dir)
		is_loaded = true
		return

	_anim_library = AnimationLibrary.new()
	var first_skeleton_scene: Node = null
	var fbx_count := 0
	var load_errors := 0

	dir.list_dir_begin()
	var file_name := dir.get_next()
	while file_name != "":
		# Godot importe les FBX en .fbx.import -> charge via le nom original
		if file_name.ends_with(".fbx"):
			fbx_count += 1
			var base_name := file_name.get_basename()  # Sans extension
			var internal_name: String = FBX_MAP.get(base_name, base_name.to_snake_case())
			var full_path := anim_dir + file_name

			# Verifier si le fichier .import existe (= Godot a importe le FBX)
			var import_path := full_path + ".import"
			if not FileAccess.file_exists(import_path):
				if fbx_count <= 3:  # Log seulement les premiers pour pas spammer
					print("[AnimLoader] ATTENTION: Pas de .import pour '%s'" % file_name)
					print("  -> Ouvrir le projet dans l'editeur Godot pour importer les FBX")
				load_errors += 1
				file_name = dir.get_next()
				continue

			var scene: PackedScene = load(full_path) as PackedScene
			if scene:
				var instance := scene.instantiate()

				# Chercher l'AnimationPlayer dans la scene FBX
				var anim_player := _find_animation_player(instance)
				if anim_player:
					for lib_name in anim_player.get_animation_list():
						var anim := anim_player.get_animation(lib_name)
						if anim:
							_anim_library.add_animation(internal_name, anim.duplicate())
							available_anims.append(internal_name)
							print("[AnimLoader] OK '%s' depuis %s" % [internal_name, file_name])

				# Garder le premier FBX avec squelette comme template
				if first_skeleton_scene == null:
					var skeleton := _find_skeleton(instance)
					if skeleton:
						first_skeleton_scene = instance
						var packed := PackedScene.new()
						packed.pack(instance)
						_template_scene = packed
						print("[AnimLoader] Template squelette depuis %s (hauteur ~Sims)" % file_name)

				if instance != first_skeleton_scene:
					instance.queue_free()
			else:
				load_errors += 1
				if load_errors <= 3:
					print("[AnimLoader] ECHEC load('%s') -- null" % full_path)

		file_name = dir.get_next()
	dir.list_dir_end()

	if load_errors > 0:
		print("[AnimLoader] %d FBX trouves, %d erreurs d'import" % [fbx_count, load_errors])
		if load_errors == fbx_count:
			print("[AnimLoader] AUCUN FBX importe ! Ouvre le projet dans l'editeur Godot pour importer.")
			print("[AnimLoader] Fallback : personnages proceduraux (iso_body.gd)")
	print("[AnimLoader] %d animations chargees, template=%s" % [
		available_anims.size(),
		"OUI (FBX squelette)" if _template_scene else "NON (procedural)"])
	is_loaded = true


func create_animated_iso() -> Node3D:
	"""Cree une instance d'ISO anime a partir du template FBX.
	Retourne un Node3D avec un Skeleton3D et AnimationPlayer."""
	if _template_scene == null:
		# Fallback: creer un mesh procedural basique
		return _create_fallback_iso()

	var instance := _template_scene.instantiate()

	# Ajouter la library d'animations combinee
	var anim_player := _find_animation_player(instance)
	if anim_player and _anim_library:
		# Ajouter toutes les animations chargees
		for anim_name in available_anims:
			var anim := _anim_library.get_animation(anim_name)
			if anim and not anim_player.has_animation(anim_name):
				# Creer une library si necessaire
				if not anim_player.has_animation_library("iso"):
					anim_player.add_animation_library("iso", AnimationLibrary.new())
				var lib := anim_player.get_animation_library("iso")
				lib.add_animation(anim_name, anim.duplicate())

	# Appliquer le material PBR Tron sur tous les MeshInstance3D
	_apply_tron_material(instance)

	return instance


func get_anim_for_action(action: String, iso_id: int = 0) -> String:
	"""Retourne le nom d'animation correspondant a une action ISO."""
	# Cas special: mourir
	if action == "dying":
		return "falling" if "falling" in available_anims else "breathing_idle"

	# Variantes de marche selon l'ID de l'ISO
	if action in ["explore", "move_to_energy"]:
		var variant_idx := iso_id % WALK_VARIANTS.size()
		var variant: String = WALK_VARIANTS[variant_idx]
		if variant in available_anims:
			return variant

	# Mapping standard
	var anim_name: String = ACTION_ANIMS.get(action, "breathing_idle")
	if anim_name in available_anims:
		return anim_name

	# Fallback: idle
	if "breathing_idle" in available_anims:
		return "breathing_idle"
	if "idle_basic" in available_anims:
		return "idle_basic"

	return ""


func get_random_combat_anim() -> String:
	"""Retourne une animation de combat/esquive aleatoire (pour Tron)."""
	var available: Array[String] = []
	for anim in COMBAT_ANIMS:
		if anim in available_anims:
			available.append(anim)
	if available.is_empty():
		return ""
	return available[randi() % available.size()]


func _find_animation_player(node: Node) -> AnimationPlayer:
	"""Cherche un AnimationPlayer dans l'arbre de la scene."""
	if node is AnimationPlayer:
		return node
	for child in node.get_children():
		var result := _find_animation_player(child)
		if result:
			return result
	return null


func _find_skeleton(node: Node) -> Skeleton3D:
	"""Cherche un Skeleton3D dans l'arbre de la scene."""
	if node is Skeleton3D:
		return node
	for child in node.get_children():
		var result := _find_skeleton(child)
		if result:
			return result
	return null


func _apply_tron_material(node: Node) -> void:
	"""Applique un material PBR Tron (sombre + circuits neon) sur les meshes."""
	if node is MeshInstance3D:
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(0.06, 0.06, 0.08, 0.92)
		mat.metallic = 0.85
		mat.roughness = 0.25
		mat.emission_enabled = true
		mat.emission = Color(0.0, 0.9, 0.75)
		mat.emission_energy_multiplier = 1.8
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
		mat.rim_enabled = true
		mat.rim = 0.3
		mat.rim_tint = 0.4
		node.material_override = mat

	for child in node.get_children():
		_apply_tron_material(child)


func _create_fallback_iso() -> Node3D:
	"""Cree un ISO procedural basique si aucun FBX n'est disponible."""
	var root := Node3D.new()
	var mesh_inst := MeshInstance3D.new()
	var ISOBody := preload("res://scripts/world/iso_body.gd")
	mesh_inst.mesh = ISOBody.create_humanoid_mesh(ISOBody.BodyType.STANDARD)

	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.06, 0.06, 0.08, 0.92)
	mat.metallic = 0.85
	mat.roughness = 0.25
	mat.emission_enabled = true
	mat.emission = Color(0.0, 0.9, 0.75)
	mat.emission_energy_multiplier = 1.8
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	mesh_inst.material_override = mat

	root.add_child(mesh_inst)
	return root
