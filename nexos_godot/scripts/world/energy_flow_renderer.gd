extends Node3D
## Flux d'energie animes -- lignes de circuit entre zones haute-energie
## Style Tron : lignes en L (circuit imprime), pulse directionnel

const MAX_FLOWS := 40  ## Nombre max de lignes de flux simultanees
const FLOW_HEIGHT := 0.3  ## Hauteur au-dessus du sol
const FLOW_THICKNESS := 1.5  ## Epaisseur des lignes
const MIN_FLOW_LENGTH := 100.0  ## Distance minimum pour creer un flux
const RECALC_INTERVAL := 30  ## Recalculer les chemins toutes les N frames
const MACRO_CELL_SIZE := 200.0  ## Taille des macro-cellules pour clustering

var _flow_lines: Array[MeshInstance3D] = []
var _flow_materials: Array[ShaderMaterial] = []
var _shader: Shader
var _frame_count := 0
var _active_flows := 0

# Donnees recues du backend
var _energy_clusters: Array = []  # [{x, z, e}] top clusters
var _iso_positions: Array = []  # [{x, z}] positions ISOs
var _structure_positions: Array = []  # [{x, z}] positions structures


func _ready() -> void:
	_shader = load("res://shaders/energy_flow.gdshader") as Shader
	if not _shader:
		print("[EnergyFlow] Shader non trouve, desactive")
		return

	# Pre-allouer le pool de lignes
	for i in range(MAX_FLOWS):
		var mesh_inst := MeshInstance3D.new()
		mesh_inst.name = "Flow_%d" % i
		mesh_inst.visible = false
		mesh_inst.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

		var mat := ShaderMaterial.new()
		mat.shader = _shader
		mat.set_shader_parameter("phase_offset", randf())
		mat.set_shader_parameter("flow_speed", randf_range(1.5, 3.0))
		_flow_materials.append(mat)

		mesh_inst.material_override = mat
		add_child(mesh_inst)
		_flow_lines.append(mesh_inst)

	print("[EnergyFlow] Pool de %d lignes cree" % MAX_FLOWS)


func update_data(energy_map: Array, isos: Array, structures: Array) -> void:
	"""Recoit les donnees pour calculer les chemins de flux."""
	_frame_count += 1
	if _frame_count % RECALC_INTERVAL != 0:
		return

	# Extraire les clusters d'energie (macro-cellules)
	_compute_energy_clusters(energy_map)

	# Positions ISOs
	_iso_positions.clear()
	for iso in isos:
		if iso is Dictionary:
			_iso_positions.append(Vector2(
				float(iso.get("x", 0)),
				float(iso.get("z", 0))))

	# Positions structures
	_structure_positions.clear()
	for s in structures:
		if s is Dictionary:
			_structure_positions.append(Vector2(
				float(s.get("x", 0)),
				float(s.get("z", 0))))

	# Recalculer les lignes de flux
	_recalculate_flows()


func _compute_energy_clusters(energy_map: Array) -> void:
	"""Groupe les points d'energie en macro-cellules et garde les top N."""
	var buckets: Dictionary = {}  # {cell_key: {x, z, total_e, count}}

	for point in energy_map:
		if not (point is Dictionary):
			continue
		var px: float = float(point.get("x", 0))
		var pz: float = float(point.get("z", 0))
		var pe: float = float(point.get("e", 0))

		var cx: int = int(px / MACRO_CELL_SIZE)
		var cz: int = int(pz / MACRO_CELL_SIZE)
		var key := "%d_%d" % [cx, cz]

		if buckets.has(key):
			buckets[key]["total_e"] += pe
			buckets[key]["count"] += 1
		else:
			buckets[key] = {
				"x": (float(cx) + 0.5) * MACRO_CELL_SIZE,
				"z": (float(cz) + 0.5) * MACRO_CELL_SIZE,
				"total_e": pe,
				"count": 1
			}

	# Trier par energie totale et garder les top 30
	var sorted_clusters: Array = buckets.values()
	sorted_clusters.sort_custom(func(a, b): return a["total_e"] > b["total_e"])
	_energy_clusters = sorted_clusters.slice(0, 30)


func _recalculate_flows() -> void:
	"""Calcule les chemins de flux entre clusters et sinks (ISOs/structures)."""
	# Cacher toutes les lignes
	for line in _flow_lines:
		line.visible = false
	_active_flows = 0

	if _energy_clusters.is_empty():
		return

	# Collecter tous les sinks (ISOs + structures)
	var sinks: Array[Vector2] = []
	sinks.append_array(_iso_positions.slice(0, 20))  # Max 20 ISOs comme sinks
	sinks.append_array(_structure_positions)

	if sinks.is_empty():
		return

	# Pour chaque cluster, trouver le sink le plus proche
	for cluster in _energy_clusters:
		if _active_flows >= MAX_FLOWS:
			break

		var source := Vector2(cluster["x"], cluster["z"])
		var best_sink: Vector2 = sinks[0]
		var best_dist: float = source.distance_to(sinks[0])

		for sink in sinks:
			var d: float = source.distance_to(sink)
			if d < best_dist:
				best_dist = d
				best_sink = sink

		if best_dist < MIN_FLOW_LENGTH or best_dist > 2000.0:
			continue

		# Creer un chemin en L (style circuit imprime)
		_create_l_path(source, best_sink, _active_flows)
		_active_flows += 1


func _create_l_path(from: Vector2, to: Vector2, flow_index: int) -> void:
	"""Cree un chemin en L entre deux points (2 segments de BoxMesh)."""
	if flow_index >= MAX_FLOWS:
		return

	# Decider la direction du L : horizontal puis vertical, ou l'inverse
	var mid: Vector2
	if randf() > 0.5:
		mid = Vector2(to.x, from.y)  # Horizontal d'abord
	else:
		mid = Vector2(from.x, to.y)  # Vertical d'abord

	# Creer un mesh avec les deux segments
	var im := ImmediateMesh.new()
	im.surface_begin(Mesh.PRIMITIVE_TRIANGLE_STRIP, null)

	# Segment 1 : from -> mid
	_add_flow_segment(im, from, mid)
	im.surface_end()

	# Segment 2 : mid -> to
	im.surface_begin(Mesh.PRIMITIVE_TRIANGLE_STRIP, null)
	_add_flow_segment(im, mid, to)
	im.surface_end()

	var line := _flow_lines[flow_index]
	line.mesh = im
	line.visible = true

	# Varier la couleur selon l'energie
	var mat := _flow_materials[flow_index]
	var hue_shift: float = randf() * 0.1  # Leger shift cyan->vert
	mat.set_shader_parameter("flow_color", Color(0.0, 0.9 + hue_shift * 0.1, 0.5 + hue_shift * 0.5))


func _add_flow_segment(im: ImmediateMesh, from: Vector2, to: Vector2) -> void:
	"""Ajoute un segment rectangulaire (triangle strip) au mesh."""
	var dir := (to - from).normalized()
	var perp := Vector2(-dir.y, dir.x) * FLOW_THICKNESS * 0.5
	var length := from.distance_to(to)

	if length < 1.0:
		# Segment trop court, skip
		im.surface_add_vertex(Vector3(from.x, FLOW_HEIGHT, from.y))
		im.surface_set_uv(Vector2(0.0, 0.0))
		im.surface_add_vertex(Vector3(from.x, FLOW_HEIGHT, from.y))
		im.surface_set_uv(Vector2(0.0, 1.0))
		im.surface_add_vertex(Vector3(from.x, FLOW_HEIGHT, from.y))
		im.surface_set_uv(Vector2(1.0, 0.0))
		im.surface_add_vertex(Vector3(from.x, FLOW_HEIGHT, from.y))
		im.surface_set_uv(Vector2(1.0, 1.0))
		return

	var p1 := from + perp
	var p2 := from - perp
	var p3 := to + perp
	var p4 := to - perp

	# UV.x = progression le long de la ligne (pour le shader pulse)
	im.surface_set_uv(Vector2(0.0, 0.0))
	im.surface_add_vertex(Vector3(p1.x, FLOW_HEIGHT, p1.y))
	im.surface_set_uv(Vector2(0.0, 1.0))
	im.surface_add_vertex(Vector3(p2.x, FLOW_HEIGHT, p2.y))
	im.surface_set_uv(Vector2(1.0, 0.0))
	im.surface_add_vertex(Vector3(p3.x, FLOW_HEIGHT, p3.y))
	im.surface_set_uv(Vector2(1.0, 1.0))
	im.surface_add_vertex(Vector3(p4.x, FLOW_HEIGHT, p4.y))
