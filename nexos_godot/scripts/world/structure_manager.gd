extends Node3D
## Gestionnaire des structures Tron et des autoroutes suspendues (Lightways)
## 5 types : shelter, library, energy_plant, comm_tower, arena
## Utilise les modeles 3D GLB de la cite Tron isometrique (tron_iso_city.glb)

const STRUCT_COLORS := {
	"shelter":       Color(1.0, 0.267, 1.0),    # magenta
	"library":       Color(1.0, 0.843, 0.0),    # gold
	"energy_plant":  Color(0.0, 1.0, 0.533),    # vert neon
	"comm_tower":    Color(0.267, 0.533, 1.0),  # bleu
	"arena":         Color(1.0, 0.4, 0.2),      # orange
	"hex_monolith":  Color(0.4, 0.85, 1.0),     # ice blue / blanc-cyan
}

const DARK_COLOR := Color(0.02, 0.02, 0.06)

# Mapping type de structure -> noms des nodes GLB/FBX disponibles
# Priorite : CyberCity 2099 d'abord, puis Tron ISO City en fallback
const GLB_MODELS := {
	"shelter":      ["Buildings_0", "Buildings_1", "Buildings_2_0", "Buildings_3",
	                 "Building_Node_01", "Building_Node_02", "Building_Node_03",
	                 "Building_Node_04", "Building_Node_05"],
	"library":      ["Buildings_adds", "Buildings_0_1",
	                 "Tower_01", "Tower_02", "Tower_03", "Tower_04", "Tower_05"],
	"energy_plant": ["monolith", "Monolith", "Solar_panel", "Red_dish",
	                 "Tower_Construction_01", "Tower_Construction_02",
	                 "Tower_Construction_03", "Tower_Construction_04",
	                 "Tower_Construction_05"],
	"comm_tower":   ["Publicity_lights", "Holograms_2D",
	                 "Tower_06", "Tower_07", "Tower_08", "Tower_09", "Tower_10"],
	"arena":        ["play_garden", "Road_Ring_01", "Road_Ring_02"],
}

# Noms de nodes CyberCity pour les elements de voirie
const CYBERCITY_ROAD_NODES := ["Streets", "Streets_2", "Sidewalks"]
const CYBERCITY_BRIDGE_NODES := ["Bridge_base", "Bridge_support"]
const CYBERCITY_TERRAIN_NODES := ["Terrain1", "Terrain_base"]
const CYBERCITY_PROPS_NODES := ["Lamppost", "Trees_Base", "Trash_color"]

var _structure_nodes: Array[Node3D] = []
var _structure_types: Array[String] = []
var _lightway_container: Node3D

# GLB -- scene template chargee une seule fois
var _glb_scene: PackedScene = null
var _glb_template: Node3D = null
var _glb_loaded: bool = false

# Noms des nodes provenant des FBX CyberCity/Monolith
# Ces nodes gardent leurs textures originales (PAS de tinting)
var _cybercity_node_names: Dictionary = {}  # node_name -> true


func _ready() -> void:
	_lightway_container = Node3D.new()
	_lightway_container.name = "Lightways"
	add_child(_lightway_container)
	_load_glb_models()


# ==================================================================
#  GLB MODEL LOADER
# ==================================================================

func _load_glb_models() -> void:
	"""Charge tous les fichiers GLB de buildings comme templates."""
	# Container pour tous les modeles GLB
	_glb_template = Node3D.new()
	_glb_template.name = "GLBTemplates"
	_glb_template.visible = false
	add_child(_glb_template)

	# Liste de tous les GLB a charger
	var glb_files := [
		# CyberCity 2099 -- modele principal avec batiments, rues, ponts
		"res://assets/models/cybercity/Cyber_City_2099_ANIM.fbx",
		# Monolithe -- tour d'energie iconique
		"res://assets/models/cybercity/monolith/monolith.fbx",
		# Tron ISO City -- fallback
		"res://assets/models/buildings/tron_iso_city.glb",
		"res://assets/models/buildings/tron_buildings_1.glb",
		"res://assets/models/buildings/end_of_line_club.glb",
		"res://assets/models/buildings/tron_grid_floor.glb",
	]

	# FBX CyberCity/Monolith : on garde les textures originales
	var cybercity_paths := [
		"res://assets/models/cybercity/Cyber_City_2099_ANIM.fbx",
		"res://assets/models/cybercity/monolith/monolith.fbx",
	]

	var total_nodes := 0
	for glb_path in glb_files:
		if not ResourceLoader.exists(glb_path):
			print("[StructureManager] GLB absent : %s" % glb_path)
			continue
		var scene: PackedScene = load(glb_path)
		var is_cybercity: bool = glb_path in cybercity_paths
		if scene:
			var instance := scene.instantiate()
			instance.visible = false
			# Ajouter tous les enfants au template commun
			var children := instance.get_children()
			for child in children:
				instance.remove_child(child)
				_glb_template.add_child(child)
				total_nodes += 1
				# Enregistrer les nodes CyberCity pour skip le tinting
				if is_cybercity:
					_register_cybercity_nodes(child)
			instance.queue_free()
			var tag: String = " [CYBERCITY - textures originales]" if is_cybercity else ""
			print("[StructureManager] GLB charge : %s (%d nodes)%s" % [glb_path.get_file(), children.size(), tag])

	if total_nodes > 0:
		_glb_loaded = true
		# Lister tous les nodes disponibles pour le debug
		print("[StructureManager] %d nodes GLB au total. Noms :" % total_nodes)
		_print_node_tree(_glb_template, "  ")
	else:
		print("[StructureManager] Aucun GLB charge -- fallback procedural")


func _register_cybercity_nodes(node: Node) -> void:
	"""Enregistre recursivement tous les noms de nodes CyberCity/Monolith."""
	_cybercity_node_names[node.name] = true
	for child in node.get_children():
		_register_cybercity_nodes(child)


func _print_node_tree(node: Node, indent: String) -> void:
	"""Affiche l'arbre de nodes (debug) -- max 3 niveaux."""
	if indent.length() > 8:
		return
	for child in node.get_children():
		var type_str := child.get_class()
		print("%s%s [%s]" % [indent, child.name, type_str])
		_print_node_tree(child, indent + "  ")


func _find_glb_node(node_name: String) -> Node3D:
	"""Cherche un node dans le template GLB par nom (recherche recursive)."""
	if not _glb_template:
		return null
	# Essayer le nom exact d'abord, puis avec suffixes courants
	var result := _find_node_recursive(_glb_template, node_name)
	if not result:
		result = _find_node_recursive(_glb_template, node_name + ".smd")
	if not result:
		# Recherche partielle (le nom contient le prefixe)
		result = _find_node_partial(_glb_template, node_name)
	return result


func _find_node_partial(parent: Node, prefix: String) -> Node3D:
	"""Recherche un node dont le nom commence par prefix."""
	if parent.name.begins_with(prefix):
		return parent as Node3D
	for child in parent.get_children():
		var found := _find_node_partial(child, prefix)
		if found:
			return found
	return null


func _find_node_recursive(parent: Node, target_name: String) -> Node3D:
	"""Recherche recursive d'un node par nom."""
	if parent.name == target_name:
		return parent as Node3D
	for child in parent.get_children():
		var found := _find_node_recursive(child, target_name)
		if found:
			return found
	return null


func _clone_glb_structure(s_type: String, color: Color, radius: float) -> Node3D:
	"""Clone un modele GLB pour un type de structure donne."""
	if not _glb_loaded:
		return null

	var models: Array = GLB_MODELS.get(s_type, [])

	# Essayer les noms definis en premier
	var template_node: Node3D = null
	for model_name in models:
		template_node = _find_glb_node(model_name)
		if template_node:
			break

	# Fallback : chercher n'importe quel node mesh parmi tous les GLB
	if not template_node:
		var all_meshes := _collect_mesh_nodes(_glb_template)
		if all_meshes.size() > 0:
			# Choisir un mesh deterministe selon le type de structure
			var idx: int = s_type.hash() % all_meshes.size()
			template_node = all_meshes[idx]

	if not template_node:
		return null

	# Dupliquer le node et tous ses enfants
	var clone: Node3D = template_node.duplicate()
	clone.visible = true

	# Mettre a l'echelle selon le radius de la structure
	var scale_factor: float = radius / 8.0  # 8 = radius de base
	clone.scale = Vector3(scale_factor, scale_factor, scale_factor)

	# CyberCity/Monolith : garder les textures originales du FBX
	# Tron ISO City : appliquer le tinting colore
	var is_cybercity: bool = _cybercity_node_names.has(template_node.name)
	if not is_cybercity:
		_tint_glb_materials(clone, color)
	else:
		# Pour CyberCity, juste activer l'emission sur les surfaces existantes
		# pour qu'elles brillent un minimum dans la scene sombre
		_boost_cybercity_emission(clone, color)

	return clone


func _collect_mesh_nodes(node: Node, depth: int = 0) -> Array[Node3D]:
	"""Collecte tous les Node3D de premier niveau qui contiennent des MeshInstance3D."""
	var result: Array[Node3D] = []
	if depth == 0:
		for child in node.get_children():
			if _has_mesh_recursive(child):
				result.append(child as Node3D)
	return result


func _has_mesh_recursive(node: Node) -> bool:
	"""Verifie si un node ou ses enfants contiennent des meshes."""
	if node is MeshInstance3D:
		return true
	for child in node.get_children():
		if _has_mesh_recursive(child):
			return true
	return false


func _boost_cybercity_emission(node: Node, color: Color) -> void:
	"""Pour les modeles CyberCity : garde les textures originales,
	   ajoute juste un leger boost d'emission pour la scene sombre Tron."""
	if node is MeshInstance3D:
		var mi: MeshInstance3D = node as MeshInstance3D
		# Traiter material_override
		if mi.material_override:
			var mat: Material = mi.material_override.duplicate()
			mi.material_override = mat
			_apply_cybercity_boost(mat, color)
		elif mi.mesh:
			for s in range(mi.mesh.get_surface_count()):
				var orig_mat := mi.mesh.surface_get_material(s)
				if orig_mat:
					var mat := orig_mat.duplicate()
					mi.set_surface_override_material(s, mat)
					_apply_cybercity_boost(mat, color)

	for child in node.get_children():
		_boost_cybercity_emission(child, color)


func _apply_cybercity_boost(mat: Material, color: Color) -> void:
	"""Boost leger sur les materials CyberCity : garde albedo/textures, ajoute emission subtile."""
	if not mat is StandardMaterial3D:
		return
	var smat: StandardMaterial3D = mat as StandardMaterial3D

	# NE PAS toucher a albedo_color ni aux textures existantes
	# Juste activer/booster l'emission si elle n'est pas deja la
	if not smat.emission_enabled:
		smat.emission_enabled = true
		smat.emission = Color(color.r * 0.15, color.g * 0.15, color.b * 0.15)
		smat.emission_energy_multiplier = 0.3
	else:
		# L'emission existe deja -- la booster legerement avec la couleur de la structure
		smat.emission_energy_multiplier = maxf(smat.emission_energy_multiplier, 0.5)


func _tint_glb_materials(node: Node, color: Color) -> void:
	"""Applique la couleur de la structure sur les materials emissifs du modele GLB."""
	if node is MeshInstance3D:
		var mi: MeshInstance3D = node as MeshInstance3D
		# Dupliquer le material pour ne pas modifier le template
		if mi.material_override:
			var mat: Material = mi.material_override.duplicate()
			mi.material_override = mat
			_apply_tint(mat, color, node.name)
		elif mi.mesh:
			for s in range(mi.mesh.get_surface_count()):
				var orig_mat := mi.mesh.surface_get_material(s)
				if orig_mat:
					var mat := orig_mat.duplicate()
					mi.set_surface_override_material(s, mat)
					_apply_tint(mat, color, node.name)

	for child in node.get_children():
		_tint_glb_materials(child, color)


func _apply_tint(mat: Material, color: Color, node_name: String) -> void:
	"""Teinte un material selon son type (emissif, glass, marble, etc.)."""
	if not mat is StandardMaterial3D:
		return
	var smat: StandardMaterial3D = mat as StandardMaterial3D

	# Detecter le type par le nom du node
	var name_lower: String = node_name.to_lower()

	if "emissive" in name_lower or "glow" in name_lower or "rez_tower" in name_lower:
		# Surfaces emissives : couleur pleine de la structure
		smat.emission_enabled = true
		smat.emission = color
		smat.emission_energy_multiplier = 1.5
		smat.albedo_color = Color(color.r, color.g, color.b, 0.9)
		smat.metallic = 0.5

	elif "glass" in name_lower:
		# Surfaces vitrees : teinte legere + transparence
		smat.albedo_color = Color(color.r * 0.3, color.g * 0.3, color.b * 0.3, 0.25)
		smat.emission_enabled = true
		smat.emission = color
		smat.emission_energy_multiplier = 0.4
		smat.metallic = 0.1
		smat.roughness = 0.05

	elif "grid_tower" in name_lower:
		# Grille de construction : wireframe lumineux
		smat.emission_enabled = true
		smat.emission = color
		smat.emission_energy_multiplier = 0.8
		smat.albedo_color = Color(color.r * 0.2, color.g * 0.2, color.b * 0.2, 0.6)

	elif "marble" in name_lower or "ceramic" in name_lower:
		# Surfaces sombres : garder sombre avec leger reflet colore
		smat.albedo_color = Color(
			DARK_COLOR.r + color.r * 0.05,
			DARK_COLOR.g + color.g * 0.05,
			DARK_COLOR.b + color.b * 0.05,
			0.85
		)
		smat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
		smat.metallic = 0.8
		smat.roughness = 0.3

	elif "metal" in name_lower:
		# Metal : reflet colore subtil
		smat.albedo_color = Color(0.1 + color.r * 0.08, 0.1 + color.g * 0.08, 0.1 + color.b * 0.08, 0.9)
		smat.metallic = 0.85
		smat.roughness = 0.2

	# --- CyberCity 2099 materials ---
	elif "neon" in name_lower or "publicity" in name_lower:
		# Enseignes neon CyberCity : emission forte + couleur structure
		smat.emission_enabled = true
		smat.emission = color
		smat.emission_energy_multiplier = 2.0
		smat.albedo_color = Color(color.r, color.g, color.b, 0.95)
		smat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED

	elif "hologram" in name_lower:
		# Hologrammes : semi-transparent + emission pulsante
		smat.albedo_color = Color(color.r * 0.5, color.g * 0.5, color.b * 0.5, 0.3)
		smat.emission_enabled = true
		smat.emission = color
		smat.emission_energy_multiplier = 1.5
		smat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA

	elif "solar" in name_lower:
		# Panneaux solaires : reflet metallique + teinte subtile
		smat.albedo_color = Color(0.05, 0.05 + color.g * 0.1, 0.08, 0.9)
		smat.metallic = 0.9
		smat.roughness = 0.1
		smat.emission_enabled = true
		smat.emission = Color(color.r * 0.2, color.g * 0.3, color.b * 0.2)
		smat.emission_energy_multiplier = 0.3

	elif "bridge" in name_lower:
		# Ponts : structure sombre + lignes lumineuses
		smat.albedo_color = Color(0.04, 0.04 + color.g * 0.03, 0.06, 0.85)
		smat.metallic = 0.7
		smat.roughness = 0.35
		smat.emission_enabled = true
		smat.emission = color
		smat.emission_energy_multiplier = 0.4

	elif "street" in name_lower or "sidewalk" in name_lower:
		# Routes et trottoirs : sombres avec reflet leger
		smat.albedo_color = Color(0.03, 0.03, 0.05, 0.9)
		smat.metallic = 0.3
		smat.roughness = 0.7
		smat.emission_enabled = true
		smat.emission = Color(color.r * 0.1, color.g * 0.15, color.b * 0.1)
		smat.emission_energy_multiplier = 0.15

	elif "building" in name_lower:
		# Batiments CyberCity : corps sombre + reflets colores
		smat.albedo_color = Color(
			DARK_COLOR.r + color.r * 0.06,
			DARK_COLOR.g + color.g * 0.06,
			DARK_COLOR.b + color.b * 0.06,
			0.9
		)
		smat.metallic = 0.6
		smat.roughness = 0.35
		smat.emission_enabled = true
		smat.emission = color
		smat.emission_energy_multiplier = 0.25

	elif "lamp" in name_lower:
		# Lampadaires : lumiere forte
		smat.emission_enabled = true
		smat.emission = color
		smat.emission_energy_multiplier = 2.5
		smat.albedo_color = Color(color.r, color.g, color.b, 0.9)

	elif "monolith" in name_lower:
		# Monolithe : surface sombre avec emission energetique intense
		smat.albedo_color = Color(0.02, 0.02, 0.04, 0.95)
		smat.metallic = 0.9
		smat.roughness = 0.15
		smat.emission_enabled = true
		smat.emission = color
		smat.emission_energy_multiplier = 3.0

	elif "tree" in name_lower or "garden" in name_lower:
		# Vegetation : vert neon subtil
		smat.albedo_color = Color(0.02, 0.08 + color.g * 0.05, 0.03, 0.8)
		smat.emission_enabled = true
		smat.emission = Color(0.0, 0.3, 0.1)
		smat.emission_energy_multiplier = 0.3


# ==================================================================
#  STRUCTURES
# ==================================================================

func update_structures(structures: Array) -> void:
	"""Met a jour les batiments depuis les donnees Python."""
	# Ajuster le nombre de nodes
	while _structure_nodes.size() < structures.size():
		var node := Node3D.new()
		node.name = "Structure_%d" % _structure_nodes.size()
		add_child(node)
		_structure_nodes.append(node)
		_structure_types.append("")

	# Masquer les nodes en trop
	for i in range(structures.size(), _structure_nodes.size()):
		_structure_nodes[i].visible = false

	# Mettre a jour chaque structure
	for i in range(structures.size()):
		var s: Dictionary = structures[i]
		var s_type: String = s.get("type", "shelter")
		var color: Color = STRUCT_COLORS.get(s_type, STRUCT_COLORS["shelter"])
		var px: float = float(s.get("x", 0))
		var pz: float = float(s.get("z", 0))
		var radius: float = float(s.get("radius", 8))
		var health: float = float(s.get("health", 1.0))
		var name_str: String = s.get("name", s_type.to_upper())
		var isos_inside: int = int(s.get("isos_inside", 0))
		var sid: int = int(s.get("id", i))
		var level: int = int(s.get("level", 1))

		var node: Node3D = _structure_nodes[i]
		node.visible = true

		# Si le type a change, reconstruire le mesh
		if _structure_types[i] != s_type:
			_clear_children(node)
			_build_structure(node, s_type, color, radius)
			_structure_types[i] = s_type

		# Position
		node.position = Vector3(px, 0, pz)

		# Animation
		var t: float = Time.get_ticks_msec() / 1000.0
		var pulse: float = 1.0 + sin(t * 1.5 + float(i) * 0.7) * 0.04

		# Scale et effets selon le niveau
		var level_scale: float = 1.0 + (float(level) - 1.0) * 0.4  # 1.0, 1.4, 1.8
		var level_emission: float = 0.5 + float(level) * 0.3  # Plus lumineux a haut niveau

		# Rotation lente du batiment
		for child in node.get_children():
			if child.name == "Building":
				# Animation speciale pour hex_monolith
				if s_type == "hex_monolith":
					_animate_hex_monolith(child, t, i)
				else:
					child.scale = Vector3(pulse * level_scale, pulse * level_scale * 1.2, pulse * level_scale)
					child.rotation.y += 0.003
					if child is MeshInstance3D:
						var mat: StandardMaterial3D = child.material_override
						if mat:
							mat.emission_energy_multiplier = level_emission
			elif child.name == "Accent":
				child.rotation.y -= 0.005
			elif child.name == "Base":
				child.scale = Vector3(level_scale, 1.0, level_scale)

		# Indicateur de niveau (etoiles lumineuses au dessus)
		var level_indicator: Node3D = node.get_node_or_null("LevelStars")
		if not level_indicator and level > 1:
			level_indicator = _create_level_stars(level, color)
			level_indicator.name = "LevelStars"
			node.add_child(level_indicator)
		elif level_indicator:
			if level <= 1:
				level_indicator.visible = false
			else:
				level_indicator.visible = true
				for star_idx in range(level_indicator.get_child_count()):
					var star: Node3D = level_indicator.get_child(star_idx)
					star.rotation.y = t * 2.0 + float(star_idx) * TAU / float(level)
					star.position.y = 120.0 + float(level) * 20.0 + sin(t * 3.0 + float(star_idx)) * 4.0

		# Mettre a jour le label
		var label: Label3D = node.get_node_or_null("StructLabel")
		if label:
			var level_str: String = " ★".repeat(level) if level > 1 else ""
			label.text = "%s #%d%s\n%d ISOs | %d%%" % [name_str, sid, level_str, isos_inside, int(health * 100)]


func _build_structure(parent: Node3D, s_type: String, color: Color, radius: float) -> void:
	"""Construit le mesh 3D pour un type de structure.
	   Essaie d'abord les modeles GLB Tron, fallback procedural si indisponible.
	   Echelle realiste : batiments proportionnes aux ISOs (scale x15)."""
	# Facteur d'echelle realiste (batiments visibles, camera proche Sims 4)
	var build_scale := 10.0  # Multiplie toutes les dimensions des batiments

	# Base au sol : empreinte lumineuse
	var base := _create_ground_glow(radius * 1.5 * build_scale, color, 6 if s_type != "arena" else 8)
	base.name = "Base"
	parent.add_child(base)

	# Batiment principal -- GLB ou procedural
	var building: Node3D = _clone_glb_structure(s_type, color, radius * build_scale)
	if building:
		building.name = "Building"
		parent.add_child(building)
	else:
		# Fallback : generation procedurale (dimensions reelles)
		var proc_building: Node3D
		var scaled_radius: float = radius * build_scale
		match s_type:
			"shelter":
				proc_building = _build_shelter(color, scaled_radius)
			"library":
				proc_building = _build_library(color, scaled_radius)
			"energy_plant":
				proc_building = _build_energy_plant(color, scaled_radius)
			"comm_tower":
				proc_building = _build_comm_tower(color, scaled_radius)
			"arena":
				proc_building = _build_arena(color, scaled_radius)
			"hex_monolith":
				proc_building = _build_hex_monolith(color, scaled_radius)
			_:
				proc_building = _build_shelter(color, scaled_radius)
		proc_building.name = "Building"
		parent.add_child(proc_building)

	# Halo atmospherique (agrandi)
	var halo := _create_halo(radius * build_scale, color)
	halo.name = "Halo"
	parent.add_child(halo)

	# Label 3D (plus haut et plus grand pour batiments realistes)
	var label := Label3D.new()
	label.name = "StructLabel"
	label.position = Vector3(0, 120, 0)  # Au dessus du batiment (echelle x10)
	label.font_size = 64
	label.modulate = color
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.no_depth_test = true
	label.outline_size = 5
	label.outline_modulate = Color(0, 0, 0, 0.8)
	parent.add_child(label)


# ---- ABRI : hexagone bas avec toit cone ----

func _build_shelter(color: Color, radius: float) -> Node3D:
	var group := Node3D.new()

	# Corps sombre hexagonal
	var body_mesh := CylinderMesh.new()
	body_mesh.top_radius = radius * 0.6
	body_mesh.bottom_radius = radius * 0.7
	body_mesh.height = 5.0
	body_mesh.radial_segments = 6

	var body := _create_dark_mesh(body_mesh)
	body.position.y = 2.5
	group.add_child(body)

	# Wireframe neon
	var wire := _create_wireframe_mesh(body_mesh, color)
	wire.position.y = 2.5
	group.add_child(wire)

	# Bandes lumineuses horizontales
	for h in [1.0, 2.5, 4.0]:
		var ring := _create_neon_ring(radius * 0.62, radius * 0.6, color, 6)
		ring.position.y = h
		group.add_child(ring)

	# Toit cone
	var roof_mesh := CylinderMesh.new()
	roof_mesh.top_radius = 0.0
	roof_mesh.bottom_radius = radius * 0.5
	roof_mesh.height = 2.0
	roof_mesh.radial_segments = 6
	var accent := _create_neon_mesh(roof_mesh, color, 0.3)
	accent.name = "Accent"
	accent.position.y = 6.0
	group.add_child(accent)

	return group


# ---- BIBLIOTHEQUE : 4 piliers + plateforme + octaedre flottant ----

func _build_library(color: Color, radius: float) -> Node3D:
	var group := Node3D.new()

	# 4 piliers sombres
	for p in range(4):
		var angle: float = (float(p) / 4.0) * TAU + PI / 4.0
		var px: float = cos(angle) * radius * 0.45
		var pz: float = sin(angle) * radius * 0.45

		var pil_mesh := BoxMesh.new()
		pil_mesh.size = Vector3(1.2, 10.0, 1.2)

		var pil := _create_dark_mesh(pil_mesh)
		pil.position = Vector3(px, 5.0, pz)
		group.add_child(pil)

		var pil_wire := _create_wireframe_mesh(pil_mesh, color)
		pil_wire.position = Vector3(px, 5.0, pz)
		group.add_child(pil_wire)

		# Ligne lumineuse centrale
		var line_mesh := BoxMesh.new()
		line_mesh.size = Vector3(0.15, 10.0, 0.15)
		var line := _create_neon_mesh(line_mesh, color, 0.7)
		line.position = Vector3(px, 5.0, pz)
		group.add_child(line)

	# Plateforme
	var plat_mesh := BoxMesh.new()
	plat_mesh.size = Vector3(radius * 0.9, 0.3, radius * 0.9)
	var plat := _create_neon_mesh(plat_mesh, color, 0.15)
	plat.position.y = 8.0
	group.add_child(plat)

	# Octaedre flottant (cristal de savoir)
	var crystal := _create_neon_mesh(_make_octahedron_mesh(2.5), color, 0.6)
	crystal.name = "Accent"
	crystal.position.y = 12.0
	# Wireframe sur le cristal
	var crystal_wire := _create_wireframe_mesh(_make_octahedron_mesh(2.5), color)
	crystal_wire.position.y = 12.0
	group.add_child(crystal_wire)
	group.add_child(crystal)

	return group


# ---- CENTRALE : cylindre reacteur + torus rotatif ----

func _build_energy_plant(color: Color, radius: float) -> Node3D:
	var group := Node3D.new()

	# Cylindre reacteur sombre
	var core_mesh := CylinderMesh.new()
	core_mesh.top_radius = radius * 0.35
	core_mesh.bottom_radius = radius * 0.4
	core_mesh.height = 8.0
	core_mesh.radial_segments = 8

	var core := _create_dark_mesh(core_mesh)
	core.position.y = 4.0
	group.add_child(core)

	var core_wire := _create_wireframe_mesh(core_mesh, color)
	core_wire.position.y = 4.0
	group.add_child(core_wire)

	# Bandes de plasma
	for h in [1.0, 3.0, 5.0, 7.0]:
		var ring := _create_neon_ring(radius * 0.42, radius * 0.34, color, 8)
		ring.position.y = h
		group.add_child(ring)

	# Colonne de plasma centrale
	var plasma_mesh := CylinderMesh.new()
	plasma_mesh.top_radius = 0.4
	plasma_mesh.bottom_radius = 0.4
	plasma_mesh.height = 9.0
	plasma_mesh.radial_segments = 6
	var plasma := _create_neon_mesh(plasma_mesh, color, 0.6)
	plasma.position.y = 4.5
	group.add_child(plasma)

	# Torus rotatif
	var torus_mesh := TorusMesh.new()
	torus_mesh.inner_radius = radius * 0.5
	torus_mesh.outer_radius = radius * 0.5 + 0.5
	torus_mesh.rings = 12
	torus_mesh.ring_segments = 6
	var torus := _create_wireframe_mesh(torus_mesh, color)
	torus.name = "Accent"
	torus.position.y = 5.0
	group.add_child(torus)

	return group


# ---- TOUR COMM : gratte-ciel fin + sphere emettrice ----

func _build_comm_tower(color: Color, radius: float) -> Node3D:
	var group := Node3D.new()

	# Tour sombre haute
	var tower_mesh := BoxMesh.new()
	tower_mesh.size = Vector3(2.0, 18.0, 2.0)

	var tower := _create_dark_mesh(tower_mesh)
	tower.position.y = 9.0
	group.add_child(tower)

	var tower_wire := _create_wireframe_mesh(tower_mesh, color)
	tower_wire.position.y = 9.0
	group.add_child(tower_wire)

	# Lignes lumineuses sur les coins
	for c in range(4):
		var cx: float = (1.0 if c < 2 else -1.0) * 0.9
		var cz: float = (1.0 if c % 2 == 0 else -1.0) * 0.9
		var line_mesh := BoxMesh.new()
		line_mesh.size = Vector3(0.12, 18.0, 0.12)
		var line := _create_neon_mesh(line_mesh, color, 0.7)
		line.position = Vector3(cx, 9.0, cz)
		group.add_child(line)

	# Bandes horizontales
	for h in range(3, 17, 3):
		var band_mesh := BoxMesh.new()
		band_mesh.size = Vector3(2.3, 0.15, 2.3)
		var band := _create_neon_mesh(band_mesh, color, 0.3)
		band.position.y = float(h)
		group.add_child(band)

	# Sphere emettrice au sommet
	var sphere_mesh := SphereMesh.new()
	sphere_mesh.radius = 1.5
	sphere_mesh.height = 3.0
	sphere_mesh.radial_segments = 8
	sphere_mesh.rings = 8
	var sphere := _create_neon_mesh(sphere_mesh, color, 0.5)
	sphere.name = "Accent"
	sphere.position.y = 19.0
	group.add_child(sphere)

	return group


# ---- ARENE : colisee octogonal + anneau flottant ----

func _build_arena(color: Color, radius: float) -> Node3D:
	var group := Node3D.new()

	# Murs octogonaux (cylindre ouvert)
	var wall_mesh := CylinderMesh.new()
	wall_mesh.top_radius = radius * 0.7
	wall_mesh.bottom_radius = radius * 0.75
	wall_mesh.height = 5.0
	wall_mesh.radial_segments = 8

	var wall := _create_dark_mesh(wall_mesh)
	wall.position.y = 2.5
	group.add_child(wall)

	var wall_wire := _create_wireframe_mesh(wall_mesh, color)
	wall_wire.position.y = 2.5
	group.add_child(wall_wire)

	# Bandes lumineuses sur les murs
	for h in [1.0, 2.5, 4.0]:
		var ring := _create_neon_ring(radius * 0.72, radius * 0.69, color, 8)
		ring.position.y = h
		group.add_child(ring)

	# Sol de l'arene lumineux
	var floor_mesh := PlaneMesh.new()
	floor_mesh.size = Vector2(radius * 1.3, radius * 1.3)
	var floor_mi := _create_neon_mesh(floor_mesh, color, 0.08)
	floor_mi.position.y = 0.3
	group.add_child(floor_mi)

	# Anneau flottant (hologramme)
	var ring_mesh := TorusMesh.new()
	ring_mesh.inner_radius = radius * 0.5
	ring_mesh.outer_radius = radius * 0.5 + 0.3
	ring_mesh.rings = 8
	ring_mesh.ring_segments = 6
	var ring := _create_wireframe_mesh(ring_mesh, color)
	ring.name = "Accent"
	ring.position.y = 6.0
	ring.rotation.x = PI / 2.0
	group.add_child(ring)

	return group


# ---- MONOLITHE HEXAGONAL : pylone + panneaux orbitaux + core + faisceau ----

func _build_hex_monolith(color: Color, radius: float) -> Node3D:
	var group := Node3D.new()
	var is_floating: bool = randf() > 0.65  # 35% flottent
	var float_y: float = randf_range(20.0, 60.0) if is_floating else 0.0

	# --- Plateforme hexagonale au sol ---
	var platform_mesh := CylinderMesh.new()
	platform_mesh.top_radius = radius * 1.2
	platform_mesh.bottom_radius = radius * 1.3
	platform_mesh.height = 1.0
	platform_mesh.radial_segments = 6
	var platform := _create_dark_mesh(platform_mesh)
	platform.position.y = 0.5 + float_y
	group.add_child(platform)

	# Bord neon de la plateforme
	var plat_wire := _create_wireframe_mesh(platform_mesh, color)
	plat_wire.position.y = 0.5 + float_y
	group.add_child(plat_wire)

	# --- Pylone hexagonal central (2 segments empiles avec gap) ---
	var pylon_h := 12.0
	for seg in range(2):
		var seg_mesh := CylinderMesh.new()
		seg_mesh.top_radius = radius * 0.3
		seg_mesh.bottom_radius = radius * 0.35
		seg_mesh.height = pylon_h
		seg_mesh.radial_segments = 6

		var seg_mi := _create_dark_mesh(seg_mesh)
		seg_mi.position.y = float_y + 1.0 + pylon_h * 0.5 + float(seg) * (pylon_h + 2.0)
		group.add_child(seg_mi)

		# Aretes neon
		var seg_wire := _create_wireframe_mesh(seg_mesh, color)
		seg_wire.position.y = seg_mi.position.y
		group.add_child(seg_wire)

		# Anneaux neon horizontaux
		for h_off in [pylon_h * 0.25, pylon_h * 0.5, pylon_h * 0.75]:
			var ring := _create_neon_ring(radius * 0.36, radius * 0.32, color, 6)
			ring.position.y = float_y + 1.0 + float(seg) * (pylon_h + 2.0) + h_off
			group.add_child(ring)

	# --- Core d'energie au sommet (octahedron pulsant) ---
	var core_y := float_y + 1.0 + 2.0 * pylon_h + 2.0 + 1.5
	var core_mesh := SphereMesh.new()
	core_mesh.radius = radius * 0.25
	core_mesh.height = radius * 0.5
	core_mesh.radial_segments = 6
	core_mesh.rings = 4
	var core := _create_neon_mesh(core_mesh, color, 2.5)
	core.name = "Core"
	core.position.y = core_y
	group.add_child(core)

	# --- Panneaux hexagonaux orbitaux (3-5) ---
	var panel_count: int = randi_range(3, 5)
	for i in range(panel_count):
		var panel_container := Node3D.new()
		panel_container.name = "PanelOrbit_%d" % i

		var panel_mesh := CylinderMesh.new()
		panel_mesh.top_radius = radius * 0.4
		panel_mesh.bottom_radius = radius * 0.4
		panel_mesh.height = 0.3
		panel_mesh.radial_segments = 6

		var panel := _create_neon_mesh(panel_mesh, color, 0.8)
		panel.name = "Panel"

		# Position orbitale differente par panneau
		var orbit_r := radius * 0.9
		var angle := float(i) * TAU / float(panel_count)
		var panel_y := float_y + 5.0 + float(i) * 5.5

		panel_container.position = Vector3(
			cos(angle) * orbit_r,
			panel_y,
			sin(angle) * orbit_r
		)
		# Inclinaison aleatoire
		panel_container.rotation.x = randf_range(-0.3, 0.3)
		panel_container.rotation.z = randf_range(-0.3, 0.3)
		panel_container.add_child(panel)
		group.add_child(panel_container)

	# --- Faisceau vertical d'energie (sol → core) ---
	var beam_mesh := CylinderMesh.new()
	beam_mesh.top_radius = radius * 0.05
	beam_mesh.bottom_radius = radius * 0.08
	beam_mesh.height = core_y
	beam_mesh.radial_segments = 6
	var beam := _create_neon_mesh(beam_mesh, color, 1.5)
	beam.name = "Beam"
	beam.position.y = core_y * 0.5
	group.add_child(beam)

	# --- Lumiere ponctuelle ---
	var light := OmniLight3D.new()
	light.name = "MonolithLight"
	light.light_color = color
	light.light_energy = 2.0
	light.omni_range = radius * 4.0
	light.shadow_enabled = false
	light.position.y = core_y
	group.add_child(light)

	return group


func _animate_hex_monolith(building: Node3D, t: float, idx: int) -> void:
	"""Anime les panneaux orbitaux, le core et le faisceau d'un monolithe."""
	for child in building.get_children():
		if child.name.begins_with("PanelOrbit_"):
			# Panneaux orbitent autour du pylone
			var orbit_speed: float = 0.3 + float(child.name.get_slice("_", 1).to_int()) * 0.15
			child.rotation.y = t * orbit_speed + float(idx) * 1.2
			# Leger mouvement vertical
			child.position.y += sin(t * 1.5 + float(child.name.get_slice("_", 1).to_int()) * 0.8) * 0.02
		elif child.name == "Core":
			# Pulse du core
			var core_pulse: float = 1.0 + sin(t * 2.5 + float(idx)) * 0.15
			child.scale = Vector3(core_pulse, core_pulse, core_pulse)
		elif child.name == "Beam":
			# Flicker du faisceau
			if child is MeshInstance3D and child.material_override:
				var beam_mat = child.material_override
				if beam_mat is StandardMaterial3D:
					beam_mat.emission_energy_multiplier = 1.0 + sin(t * 5.0 + float(idx) * 2.0) * 0.4


# ==================================================================
#  LIGHTWAYS (autoroutes suspendues Tron)
# ==================================================================

func update_lightways(structures: Array) -> void:
	"""Connecte les structures proches par des autoroutes suspendues."""
	# Nettoyer les anciens
	_clear_children(_lightway_container)

	if structures.size() < 2:
		return

	var max_dist := 150.0
	var connected := {}  # "i-j" -> true

	for i in range(structures.size()):
		var a: Dictionary = structures[i]
		var ax: float = float(a.get("x", 0))
		var az: float = float(a.get("z", 0))

		# Trouver les 2 plus proches
		var dists: Array = []
		for j in range(structures.size()):
			if i == j:
				continue
			var b: Dictionary = structures[j]
			var bx: float = float(b.get("x", 0))
			var bz: float = float(b.get("z", 0))
			var dx: float = bx - ax
			var dz: float = bz - az
			var dist: float = sqrt(dx * dx + dz * dz)
			if dist < max_dist:
				dists.append({"j": j, "dist": dist, "bx": bx, "bz": bz})

		dists.sort_custom(func(x, y): return x["dist"] < y["dist"])

		for d in dists.slice(0, 2):
			var j: int = d["j"]
			var key: String = "%d-%d" % [mini(i, j), maxi(i, j)]
			if connected.has(key):
				continue
			connected[key] = true
			_create_lightway(ax, az, d["bx"], d["bz"], d["dist"])


func _create_lightway(x1: float, z1: float, x2: float, z2: float, dist: float) -> void:
	var mid_x: float = (x1 + x2) / 2.0
	var mid_z: float = (z1 + z2) / 2.0
	var dx: float = x2 - x1
	var dz: float = z2 - z1
	var angle: float = atan2(dz, dx)
	var road_height: float = 60.0  # Plus haut pour batiments realistes (echelle x10)
	var road_width: float = 15.0   # Plus large
	var rail_color := Color(0.0, 0.898, 1.0)

	var lw := Node3D.new()

	# Essayer d'utiliser le pont GLB Building_Bridge
	var bridge_glb := _clone_glb_bridge(dist, angle, rail_color)
	if bridge_glb:
		bridge_glb.position = Vector3(mid_x, road_height, mid_z)
		lw.add_child(bridge_glb)
	else:
		# Fallback procedural
		var road_mesh := BoxMesh.new()
		road_mesh.size = Vector3(dist, 0.8, road_width)
		var road := _create_dark_mesh(road_mesh)
		road.position = Vector3(mid_x, road_height, mid_z)
		road.rotation.y = -angle
		lw.add_child(road)

		var rail_mesh := BoxMesh.new()
		rail_mesh.size = Vector3(dist, 0.4, 0.4)
		for side in [-1.0, 1.0]:
			var rail := _create_neon_mesh(rail_mesh, rail_color, 0.6)
			rail.position = Vector3(mid_x, road_height + 0.15, mid_z)
			rail.rotation.y = -angle
			rail.position.x += sin(angle) * (road_width / 2.0) * side
			rail.position.z -= cos(angle) * (road_width / 2.0) * side
			lw.add_child(rail)

	# Piliers de soutien (proportionnes aux batiments)
	var n_pillars: int = maxi(2, int(dist / 40.0))
	for p in range(n_pillars + 1):
		var t: float = float(p) / float(n_pillars)
		var px: float = x1 + dx * t
		var pz: float = z1 + dz * t

		var pil_mesh := BoxMesh.new()
		pil_mesh.size = Vector3(5.0, road_height, 5.0)
		var pil := _create_dark_mesh(pil_mesh)
		pil.position = Vector3(px, road_height / 2.0, pz)
		lw.add_child(pil)

		var line_mesh := BoxMesh.new()
		line_mesh.size = Vector3(1.0, road_height, 1.0)
		var line := _create_neon_mesh(line_mesh, rail_color, 0.5)
		line.position = Vector3(px, road_height / 2.0, pz)
		lw.add_child(line)

	_lightway_container.add_child(lw)


func _clone_glb_bridge(dist: float, angle: float, color: Color) -> Node3D:
	"""Clone le modele de pont GLB, etire et oriente pour connecter deux structures."""
	if not _glb_loaded:
		return null
	var template := _find_glb_node("Building_Bridge")
	if not template:
		return null
	var clone: Node3D = template.duplicate()
	clone.visible = true
	# Etirer le pont selon la distance (le modele est a echelle 1)
	var stretch: float = dist / 20.0  # 20 = longueur estimee du modele de base
	clone.scale = Vector3(stretch, 0.8, 0.8)
	clone.rotation.y = -angle
	# CyberCity bridges : garder textures originales
	if _cybercity_node_names.has(template.name):
		_boost_cybercity_emission(clone, color)
	else:
		_tint_glb_materials(clone, color)
	return clone


# ==================================================================
#  UTILITAIRES
# ==================================================================

func _create_dark_mesh(mesh: Mesh) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(DARK_COLOR.r, DARK_COLOR.g, DARK_COLOR.b, 0.7)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	mat.metallic = 0.8
	mat.roughness = 0.3
	mi.material_override = mat
	return mi


func _create_neon_mesh(mesh: Mesh, color: Color, opacity: float) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(color.r, color.g, color.b, opacity)
	mat.emission_enabled = true
	mat.emission = color
	mat.emission_energy_multiplier = 0.8
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mi.material_override = mat
	return mi


func _create_wireframe_mesh(mesh: Mesh, color: Color) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(color.r, color.g, color.b, 0.5)
	mat.emission_enabled = true
	mat.emission = color
	mat.emission_energy_multiplier = 1.0
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	# Wireframe look via no_depth_test (Godot 4 n'a pas mat.wireframe)
	mat.no_depth_test = true
	mi.material_override = mat
	return mi


func _create_ground_glow(radius: float, color: Color, segments: int) -> MeshInstance3D:
	var disc := PlaneMesh.new()
	disc.size = Vector2(radius * 2.0, radius * 2.0)
	var mi := MeshInstance3D.new()
	mi.mesh = disc
	mi.position.y = 0.15
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(color.r, color.g, color.b, 0.08)
	mat.emission_enabled = true
	mat.emission = color
	mat.emission_energy_multiplier = 0.2
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mi.material_override = mat
	return mi


func _create_halo(radius: float, color: Color) -> MeshInstance3D:
	var sphere := SphereMesh.new()
	sphere.radius = radius
	sphere.height = radius * 2.0
	sphere.radial_segments = 16
	sphere.rings = 8
	var mi := MeshInstance3D.new()
	mi.mesh = sphere
	mi.position.y = 4.0
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(color.r, color.g, color.b, 0.04)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mi.material_override = mat
	return mi


func _create_neon_ring(outer_r: float, inner_r: float, color: Color, segments: int) -> MeshInstance3D:
	"""Cree un anneau neon horizontal."""
	var torus := TorusMesh.new()
	torus.inner_radius = (outer_r + inner_r) / 2.0
	torus.outer_radius = torus.inner_radius + (outer_r - inner_r) / 2.0
	torus.rings = segments
	torus.ring_segments = 4
	var mi := _create_neon_mesh(torus, color, 0.45)
	mi.rotation.x = PI / 2.0
	return mi


func _make_octahedron_mesh(size: float) -> Mesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var top := Vector3(0, size, 0)
	var bot := Vector3(0, -size, 0)
	var pts: Array[Vector3] = [
		Vector3(size, 0, 0), Vector3(0, 0, size),
		Vector3(-size, 0, 0), Vector3(0, 0, -size)
	]
	for i in range(4):
		st.add_vertex(top)
		st.add_vertex(pts[i])
		st.add_vertex(pts[(i + 1) % 4])
	for i in range(4):
		st.add_vertex(bot)
		st.add_vertex(pts[(i + 1) % 4])
		st.add_vertex(pts[i])
	st.generate_normals()
	return st.commit()


func _create_level_stars(level: int, color: Color) -> Node3D:
	"""Cree des etoiles lumineuses au-dessus du batiment pour indiquer le niveau."""
	var container := Node3D.new()
	var star_count: int = level

	for i in range(star_count):
		var star_mesh := _make_star_mesh(3.5)  # Etoiles grandes (echelle x10)
		var star := MeshInstance3D.new()
		star.mesh = star_mesh
		star.position.y = 120.0 + float(level) * 20.0

		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(color.r, color.g, color.b, 0.95)
		mat.emission_enabled = true
		mat.emission = color
		mat.emission_energy_multiplier = 2.5 + float(level) * 0.5
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		star.material_override = mat

		container.add_child(star)

	return container


func _make_star_mesh(size: float) -> Mesh:
	"""Cree un mesh d'etoile (octahedron lumineux)."""
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)

	var top := Vector3(0, size, 0)
	var bot := Vector3(0, -size, 0)
	var pts: Array[Vector3] = [
		Vector3(size, 0, 0), Vector3(0, 0, size),
		Vector3(-size, 0, 0), Vector3(0, 0, -size)
	]

	for i in range(4):
		var n: int = (i + 1) % 4
		st.add_vertex(top)
		st.add_vertex(pts[i])
		st.add_vertex(pts[n])

	for i in range(4):
		var n: int = (i + 1) % 4
		st.add_vertex(bot)
		st.add_vertex(pts[n])
		st.add_vertex(pts[i])

	st.generate_normals()
	return st.commit()


func _clear_children(node: Node) -> void:
	for child in node.get_children():
		child.queue_free()
