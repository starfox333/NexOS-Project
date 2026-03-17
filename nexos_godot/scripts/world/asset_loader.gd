extends Node
## NexOS v5 -- Asset Loader + Mod Manager
## Scanne assets/models/ (base game) + mods/ (mods utilisateur)
## Chaque mod = un dossier dans mods/ avec un mod.json
## Structure : mods/nom_du_mod/{buildings,vehicles,bodies,props}/*.glb
## Les mods peuvent etre actives/desactives via le mod manager UI

const BASE_DIRS := {
	"buildings":  "res://assets/models/buildings/",
	"vehicles":   "res://assets/models/vehicles/",
	"bodies":     "res://assets/models/bodies/",
	"cybercity":  "res://assets/models/cybercity/",
}

const MODS_DIR := "res://mods/"

# Modeles charges : category -> [{scene, template, nodes, file, source}]
var _models: Dictionary = {}
var _loaded := false

# Mod system
var _mods: Array[Dictionary] = []  # [{id, name, author, version, description, enabled, path, asset_count}]
var _mod_settings_path := "user://mod_settings.json"


func _ready() -> void:
	_load_mod_settings()
	_scan_base_assets()
	_scan_mods()
	_loaded = true
	_print_summary()


# ================================================================
#  BASE ASSETS SCAN
# ================================================================

func _scan_base_assets() -> void:
	"""Scanne les dossiers de base du jeu."""
	for category in BASE_DIRS:
		if not _models.has(category):
			_models[category] = []
		_scan_directory(category, BASE_DIRS[category], "base")


func _scan_directory(category: String, dir_path: String, source: String) -> int:
	"""Scanne un dossier pour des fichiers GLB. Retourne le nombre charge."""
	var count := 0
	var dir := DirAccess.open(dir_path)
	if not dir:
		return 0

	dir.list_dir_begin()
	var file_name: String = dir.get_next()
	while file_name != "":
		if file_name.ends_with(".glb") or file_name.ends_with(".gltf") or file_name.ends_with(".fbx"):
			var full_path: String = dir_path + file_name
			if _load_glb(category, full_path, file_name, source):
				count += 1
		file_name = dir.get_next()
	dir.list_dir_end()
	return count


# ================================================================
#  MOD SYSTEM
# ================================================================

func _scan_mods() -> void:
	"""Scanne le dossier mods/ pour trouver les mods installes."""
	var dir := DirAccess.open(MODS_DIR)
	if not dir:
		print("[ModManager] Dossier mods/ absent")
		return

	dir.list_dir_begin()
	var mod_folder: String = dir.get_next()
	while mod_folder != "":
		if dir.current_is_dir() and mod_folder != "." and mod_folder != "..":
			_load_mod(MODS_DIR + mod_folder + "/")
		mod_folder = dir.get_next()
	dir.list_dir_end()


func _load_mod(mod_path: String) -> void:
	"""Charge un mod depuis son dossier."""
	var json_path := mod_path + "mod.json"
	var mod_id := mod_path.get_slice("/", mod_path.get_slice_count("/") - 2)

	# Lire mod.json si present
	var mod_info := {
		"id": mod_id,
		"name": mod_id.capitalize().replace("_", " "),
		"author": "Inconnu",
		"version": "1.0",
		"description": "",
		"path": mod_path,
		"enabled": true,
		"asset_count": 0,
	}

	if FileAccess.file_exists(json_path):
		var file := FileAccess.open(json_path, FileAccess.READ)
		if file:
			var json := JSON.new()
			if json.parse(file.get_as_text()) == OK:
				var data: Dictionary = json.data
				mod_info["name"] = data.get("name", mod_info["name"])
				mod_info["author"] = data.get("author", mod_info["author"])
				mod_info["version"] = data.get("version", "1.0")
				mod_info["description"] = data.get("description", "")
			file.close()

	# Verifier si le mod est desactive dans les settings
	var saved := _get_mod_setting(mod_id)
	if saved.has("enabled"):
		mod_info["enabled"] = saved["enabled"]

	# Scanner les sous-dossiers du mod
	var total_assets := 0
	var categories: Array[String] = ["buildings", "vehicles", "bodies", "props"]
	for cat: String in categories:
		var cat_path: String = mod_path + cat + "/"
		if not _models.has(cat):
			_models[cat] = []
		if mod_info["enabled"]:
			var loaded: int = _scan_directory(cat, cat_path, mod_id)
			total_assets += loaded

	mod_info["asset_count"] = total_assets
	_mods.append(mod_info)

	var status := "ON" if mod_info["enabled"] else "OFF"
	print("[ModManager] Mod '%s' [%s] — %d assets" % [mod_info["name"], status, total_assets])


# ================================================================
#  MOD SETTINGS PERSISTENCE
# ================================================================

func _load_mod_settings() -> void:
	"""Charge les preferences de mods depuis user://mod_settings.json."""
	if not FileAccess.file_exists(_mod_settings_path):
		return
	var file := FileAccess.open(_mod_settings_path, FileAccess.READ)
	if not file:
		return
	var json := JSON.new()
	json.parse(file.get_as_text())
	file.close()


func _save_mod_settings() -> void:
	"""Sauvegarde les preferences de mods."""
	var settings := {}
	for mod in _mods:
		settings[mod["id"]] = {"enabled": mod["enabled"]}
	var file := FileAccess.open(_mod_settings_path, FileAccess.WRITE)
	if file:
		file.store_string(JSON.stringify(settings, "\t"))
		file.close()


func _get_mod_setting(mod_id: String) -> Dictionary:
	"""Recupere le setting sauvegarde pour un mod."""
	if not FileAccess.file_exists(_mod_settings_path):
		return {}
	var file := FileAccess.open(_mod_settings_path, FileAccess.READ)
	if not file:
		return {}
	var json := JSON.new()
	if json.parse(file.get_as_text()) == OK:
		var data: Dictionary = json.data
		if data.has(mod_id):
			return data[mod_id]
	file.close()
	return {}


func set_mod_enabled(mod_id: String, enabled: bool) -> void:
	"""Active/desactive un mod (necessite relancement pour prendre effet)."""
	for mod in _mods:
		if mod["id"] == mod_id:
			mod["enabled"] = enabled
			break
	_save_mod_settings()


func get_mods() -> Array[Dictionary]:
	"""Retourne la liste de tous les mods installes."""
	return _mods


# ================================================================
#  GLB LOADING
# ================================================================

func _load_glb(category: String, path: String, file_name: String, source: String) -> bool:
	"""Charge un fichier GLB comme PackedScene et indexe ses nodes."""
	if not ResourceLoader.exists(path):
		return false

	var scene: PackedScene = load(path)
	if not scene:
		return false

	var template: Node3D = scene.instantiate()
	template.name = "Template_" + file_name.get_basename()
	template.visible = false

	# Indexer tous les nodes MeshInstance3D
	var node_names: Array[String] = []
	_index_nodes(template, node_names)

	_models[category].append({
		"scene": scene,
		"template": template,
		"nodes": node_names,
		"file": file_name,
		"source": source,
	})
	return true


func _index_nodes(node: Node, result: Array[String]) -> void:
	"""Indexe recursivement les noms des nodes MeshInstance3D."""
	if node is MeshInstance3D:
		result.append(node.name)
	for child in node.get_children():
		_index_nodes(child, result)


func _print_summary() -> void:
	var total := 0
	for cat in _models:
		total += _models[cat].size()
	print("[AssetLoader] %d fichiers GLB charges" % total)
	print("[ModManager] %d mods detectes" % _mods.size())


# ================================================================
#  PUBLIC API
# ================================================================

func get_random_model(category: String, filter_name: String = "") -> Node3D:
	"""Clone un modele aleatoire d'une categorie."""
	if not _models.has(category) or _models[category].is_empty():
		return null

	var candidates: Array = []
	for entry in _models[category]:
		var template: Node3D = entry["template"]
		for node_name in entry["nodes"]:
			if filter_name == "" or filter_name.to_lower() in node_name.to_lower():
				var found: Node3D = _find_node_recursive(template, node_name)
				if found:
					candidates.append(found)

	if candidates.is_empty():
		return null

	var chosen: Node3D = candidates[randi() % candidates.size()]
	var clone: Node3D = chosen.duplicate()
	clone.visible = true
	return clone


func find_node_in_category(category: String, node_name: String) -> Node3D:
	"""Trouve et clone un node specifique par nom exact."""
	if not _models.has(category):
		return null

	for entry in _models[category]:
		var template: Node3D = entry["template"]
		var found: Node3D = _find_node_recursive(template, node_name)
		if not found:
			found = _find_node_recursive(template, node_name + ".smd")
		if found:
			var clone: Node3D = found.duplicate()
			clone.visible = true
			return clone
	return null


func has_models(category: String) -> bool:
	return _models.has(category) and not _models[category].is_empty()


func get_node_count(category: String) -> int:
	if not _models.has(category):
		return 0
	var count := 0
	for entry in _models[category]:
		count += entry["nodes"].size()
	return count


func get_models_info() -> Dictionary:
	"""Retourne les infos sur tous les modeles charges (pour le UI)."""
	var info := {}
	for cat in _models:
		info[cat] = []
		for entry in _models[cat]:
			info[cat].append({
				"file": entry["file"],
				"source": entry["source"],
				"nodes": entry["nodes"].size(),
			})
	return info


func _find_node_recursive(parent: Node, target_name: String) -> Node3D:
	if parent.name == target_name:
		return parent as Node3D
	for child in parent.get_children():
		var found: Node3D = _find_node_recursive(child, target_name)
		if found:
			return found
	return null
