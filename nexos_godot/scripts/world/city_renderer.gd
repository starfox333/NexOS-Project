extends Node3D
## City Builder Renderer -- routes, zones, eclairage urbain, reseau
## Recoit les donnees de Symmetra via le state WebSocket
## Gere : routes lumineuses, contours de zones, lampadaires, lignes de reseau

# ---- ROUTES (rues CyberCity avec trottoirs) ----
var _road_container: Node3D
var _road_meshes: Array[MeshInstance3D] = []
var _road_mat: StandardMaterial3D
var _sidewalk_mat: StandardMaterial3D
var _road_line_mat: StandardMaterial3D

# ---- ZONES (contours colores) ----
var _zone_container: Node3D
var _zone_meshes: Array[MeshInstance3D] = []

# ---- BLOCS URBAINS (grille au sol) ----
var _block_container: Node3D
var _block_meshes: Array[MeshInstance3D] = []
var _last_block_count := 0

# ---- ECLAIRAGE URBAIN (lampadaires) ----
var _lamp_container: Node3D
var _lamp_pool: Array[Node3D] = []  # Pool de lampadaires
const MAX_LAMPS := 100

# ---- RESEAU INFRASTRUCTURE (lignes animees entre comm towers) ----
var _network_container: Node3D
var _network_mesh: MeshInstance3D
var _network_mat: ShaderMaterial

# Cache des donnees
var _last_road_count := 0
var _last_zone_count := 0
var _last_struct_count := 0

# Constantes alignees sur le backend Python
const BLOCK_SIZE := 40.0
const ROAD_WIDTH_VISUAL := 8.0
const SIDEWALK_WIDTH := 3.0


func _ready() -> void:
	_setup_roads()
	_setup_zones()
	_setup_blocks()
	_setup_lamps()
	_setup_network()


# ==================================================================
#  INIT
# ==================================================================

func _setup_roads() -> void:
	_road_container = Node3D.new()
	_road_container.name = "Roads"
	add_child(_road_container)

	# Material pour la chaussee (sombre, asphalte cyber)
	_road_mat = StandardMaterial3D.new()
	_road_mat.albedo_color = Color(0.025, 0.03, 0.045, 0.85)
	_road_mat.emission_enabled = true
	_road_mat.emission = Color(0.0, 0.15, 0.12)
	_road_mat.emission_energy_multiplier = 0.15
	_road_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_road_mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	_road_mat.metallic = 0.3
	_road_mat.roughness = 0.7
	_road_mat.cull_mode = BaseMaterial3D.CULL_DISABLED

	# Material pour les trottoirs (legerement plus clairs)
	_sidewalk_mat = StandardMaterial3D.new()
	_sidewalk_mat.albedo_color = Color(0.04, 0.045, 0.06, 0.8)
	_sidewalk_mat.emission_enabled = true
	_sidewalk_mat.emission = Color(0.0, 0.1, 0.08)
	_sidewalk_mat.emission_energy_multiplier = 0.1
	_sidewalk_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_sidewalk_mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	_sidewalk_mat.metallic = 0.2
	_sidewalk_mat.roughness = 0.8
	_sidewalk_mat.cull_mode = BaseMaterial3D.CULL_DISABLED

	# Material pour les lignes centrales (neon)
	_road_line_mat = StandardMaterial3D.new()
	_road_line_mat.albedo_color = Color(0.0, 0.8, 0.65, 0.9)
	_road_line_mat.emission_enabled = true
	_road_line_mat.emission = Color(0.0, 1.0, 0.8)
	_road_line_mat.emission_energy_multiplier = 1.5
	_road_line_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_road_line_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_road_line_mat.cull_mode = BaseMaterial3D.CULL_DISABLED


func _setup_zones() -> void:
	_zone_container = Node3D.new()
	_zone_container.name = "Zones"
	add_child(_zone_container)


func _setup_blocks() -> void:
	_block_container = Node3D.new()
	_block_container.name = "CityBlocks"
	add_child(_block_container)


func _setup_lamps() -> void:
	_lamp_container = Node3D.new()
	_lamp_container.name = "StreetLamps"
	add_child(_lamp_container)

	# Pre-allouer le pool de lampadaires
	for i in range(MAX_LAMPS):
		var lamp := _create_lamp()
		lamp.name = "Lamp_%d" % i
		lamp.visible = false
		_lamp_container.add_child(lamp)
		_lamp_pool.append(lamp)


func _setup_network() -> void:
	_network_container = Node3D.new()
	_network_container.name = "Network"
	add_child(_network_container)

	_network_mesh = MeshInstance3D.new()
	_network_mesh.name = "NetworkLines"

	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.2, 0.5, 1.0, 0.5)
	mat.emission_enabled = true
	mat.emission = Color(0.3, 0.6, 1.0)
	mat.emission_energy_multiplier = 1.2
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_network_mesh.material_override = mat

	_network_container.add_child(_network_mesh)


# ==================================================================
#  UPDATE DEPUIS STATE
# ==================================================================

func update_city(sym_data: Dictionary) -> void:
	"""Point d'entree principal -- appele depuis main.gd."""
	var roads: Array = sym_data.get("roads", [])
	var zones: Array = sym_data.get("zones", [])
	var structures: Array = sym_data.get("structures", sym_data.get("shelters", []))
	var city_blocks: Array = sym_data.get("city_blocks", [])

	# Ne regenerer que si les donnees changent (perf)
	if roads.size() != _last_road_count:
		_update_roads(roads)
		_last_road_count = roads.size()

	if zones.size() != _last_zone_count:
		_update_zones(zones)
		_last_zone_count = zones.size()

	if city_blocks.size() != _last_block_count:
		_update_city_blocks(city_blocks)
		_last_block_count = city_blocks.size()

	if structures.size() != _last_struct_count:
		_update_lamps(structures, roads)
		_update_network(structures)
		_last_struct_count = structures.size()

	# Animation du reseau (flux continu)
	_animate_network()


# ==================================================================
#  ROUTES LUMINEUSES
# ==================================================================

func _update_roads(roads: Array) -> void:
	"""Reconstruit les rues CyberCity (chaussee + trottoirs + neon)."""
	# Nettoyer les anciennes routes
	for mesh in _road_meshes:
		mesh.queue_free()
	_road_meshes.clear()

	for road in roads:
		var points: Array = road.get("points", [])
		if points.size() < 2:
			continue

		# Creer le groupe route complet (chaussee + trottoirs + lignes)
		var road_group := _create_road_mesh(points)
		_road_container.add_child(road_group)
		_road_meshes.append(road_group)


func _create_road_mesh(points: Array) -> Node3D:
	"""Cree un ensemble route CyberCity : chaussee + trottoirs + ligne centrale neon."""
	var group := Node3D.new()
	var y_road: float = 0.3
	var y_sidewalk: float = 0.5
	var y_line: float = 0.6

	# --- Chaussee principale ---
	var road_mi := _build_road_strip(points, ROAD_WIDTH_VISUAL, y_road)
	road_mi.material_override = _road_mat
	group.add_child(road_mi)

	# --- Trottoirs (de chaque cote) ---
	var sw_left := _build_road_strip(points, ROAD_WIDTH_VISUAL + SIDEWALK_WIDTH * 2.0, y_sidewalk)
	sw_left.material_override = _sidewalk_mat
	group.add_child(sw_left)

	# --- Ligne centrale neon ---
	var line_mi := _build_road_strip(points, 0.8, y_line)
	line_mi.material_override = _road_line_mat
	group.add_child(line_mi)

	# --- Lignes laterales neon (bords de trottoir) ---
	for side in [-1.0, 1.0]:
		var offset_pts: Array = _offset_points(points, (ROAD_WIDTH_VISUAL * 0.5 + SIDEWALK_WIDTH) * side)
		var edge := _build_road_strip(offset_pts, 0.4, y_line)
		edge.material_override = _road_line_mat
		group.add_child(edge)

	return group


func _build_road_strip(points: Array, width: float, y: float) -> MeshInstance3D:
	"""Construit un quad strip le long des points avec une largeur donnee."""
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)

	for i in range(points.size() - 1):
		var p1: Dictionary = points[i]
		var p2: Dictionary = points[i + 1]
		var x1: float = float(p1.get("x", 0))
		var z1: float = float(p1.get("z", 0))
		var x2: float = float(p2.get("x", 0))
		var z2: float = float(p2.get("z", 0))

		var dx: float = x2 - x1
		var dz: float = z2 - z1
		var len_seg: float = sqrt(dx * dx + dz * dz)
		if len_seg < 0.1:
			continue

		var nx: float = -dz / len_seg * width * 0.5
		var nz: float = dx / len_seg * width * 0.5

		var bl := Vector3(x1 + nx, y, z1 + nz)
		var br := Vector3(x1 - nx, y, z1 - nz)
		var tl := Vector3(x2 + nx, y, z2 + nz)
		var tr := Vector3(x2 - nx, y, z2 - nz)

		st.add_vertex(bl)
		st.add_vertex(tl)
		st.add_vertex(tr)
		st.add_vertex(bl)
		st.add_vertex(tr)
		st.add_vertex(br)

	st.generate_normals()
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	return mi


func _offset_points(points: Array, offset: float) -> Array:
	"""Decale les points d'une route lateralement pour creer les bords."""
	var result: Array = []
	for i in range(points.size()):
		var p: Dictionary = points[i]
		var x: float = float(p.get("x", 0))
		var z: float = float(p.get("z", 0))

		# Calculer la normale du segment
		var nx: float = 0.0
		var nz: float = 0.0
		if i < points.size() - 1:
			var p2: Dictionary = points[i + 1]
			var dx: float = float(p2.get("x", 0)) - x
			var dz: float = float(p2.get("z", 0)) - z
			var len_seg: float = sqrt(dx * dx + dz * dz)
			if len_seg > 0.1:
				nx = -dz / len_seg
				nz = dx / len_seg
		elif i > 0:
			var p0: Dictionary = points[i - 1]
			var dx: float = x - float(p0.get("x", 0))
			var dz: float = z - float(p0.get("z", 0))
			var len_seg: float = sqrt(dx * dx + dz * dz)
			if len_seg > 0.1:
				nx = -dz / len_seg
				nz = dx / len_seg

		result.append({"x": x + nx * offset, "z": z + nz * offset})
	return result


# ==================================================================
#  ZONES URBAINES (contours colores)
# ==================================================================

func _update_zones(zones: Array) -> void:
	"""Reconstruit les contours des zones."""
	for mesh in _zone_meshes:
		mesh.queue_free()
	_zone_meshes.clear()

	for zone in zones:
		var cx: float = float(zone.get("center_x", 0))
		var cz: float = float(zone.get("center_z", 0))
		var radius: float = float(zone.get("radius", 20))
		var color_hex: String = str(zone.get("color", "#00ffcc"))

		# Convertir couleur hex
		var color := Color.html(color_hex)

		# Creer un contour hexagonal lumineux au sol
		var zone_mi := _create_zone_contour(cx, cz, radius, color)
		_zone_container.add_child(zone_mi)
		_zone_meshes.append(zone_mi)


func _create_zone_contour(cx: float, cz: float, radius: float, color: Color) -> MeshInstance3D:
	"""Cree un contour hexagonal lumineux pour une zone."""
	var im := ImmediateMesh.new()

	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(color.r, color.g, color.b, 0.4)
	mat.emission_enabled = true
	mat.emission = color
	mat.emission_energy_multiplier = 0.6
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED

	var y: float = 0.2
	var segments: int = 24  # Nombre de segments du contour

	im.surface_begin(Mesh.PRIMITIVE_LINE_STRIP, mat)
	for i in range(segments + 1):
		var angle: float = float(i) / float(segments) * TAU
		var px: float = cx + cos(angle) * radius
		var pz: float = cz + sin(angle) * radius
		im.surface_add_vertex(Vector3(px, y, pz))
	im.surface_end()

	# Second contour interieur (double trait Tron)
	var inner_r: float = radius * 0.9
	im.surface_begin(Mesh.PRIMITIVE_LINE_STRIP, mat)
	for i in range(segments + 1):
		var angle: float = float(i) / float(segments) * TAU
		var px: float = cx + cos(angle) * inner_r
		var pz: float = cz + sin(angle) * inner_r
		im.surface_add_vertex(Vector3(px, y, pz))
	im.surface_end()

	var mi := MeshInstance3D.new()
	mi.mesh = im
	return mi


# ==================================================================
#  BLOCS URBAINS (empreinte au sol des quartiers)
# ==================================================================

func _update_city_blocks(blocks: Array) -> void:
	"""Dessine les empreintes des blocs urbains au sol."""
	for mesh in _block_meshes:
		mesh.queue_free()
	_block_meshes.clear()

	for block in blocks:
		var cx: float = float(block.get("cx", 0))
		var cz: float = float(block.get("cz", 0))
		var btype: String = str(block.get("type", "shelter"))

		# Couleur du bloc selon le type de structure
		var color: Color = Color(0.0, 0.5, 0.4)
		match btype:
			"shelter":
				color = Color(1.0, 0.267, 1.0, 0.06)
			"library":
				color = Color(1.0, 0.843, 0.0, 0.06)
			"energy_plant":
				color = Color(0.0, 1.0, 0.533, 0.06)
			"comm_tower":
				color = Color(0.267, 0.533, 1.0, 0.06)
			"arena":
				color = Color(1.0, 0.4, 0.2, 0.06)

		# Contour du bloc (rectangle)
		var half := BLOCK_SIZE * 0.5
		var block_mi := _create_block_outline(cx, cz, half, color)
		_block_container.add_child(block_mi)
		_block_meshes.append(block_mi)


func _create_block_outline(cx: float, cz: float, half: float, color: Color) -> MeshInstance3D:
	"""Cree un contour rectangulaire lumineux pour un bloc urbain."""
	var im := ImmediateMesh.new()
	var y: float = 0.15

	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(color.r, color.g, color.b, 0.3)
	mat.emission_enabled = true
	mat.emission = Color(color.r, color.g, color.b)
	mat.emission_energy_multiplier = 0.4
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED

	# Rectangle lumineux
	im.surface_begin(Mesh.PRIMITIVE_LINE_STRIP, mat)
	im.surface_add_vertex(Vector3(cx - half, y, cz - half))
	im.surface_add_vertex(Vector3(cx + half, y, cz - half))
	im.surface_add_vertex(Vector3(cx + half, y, cz + half))
	im.surface_add_vertex(Vector3(cx - half, y, cz + half))
	im.surface_add_vertex(Vector3(cx - half, y, cz - half))
	im.surface_end()

	var mi := MeshInstance3D.new()
	mi.mesh = im
	return mi


# ==================================================================
#  ECLAIRAGE URBAIN (lampadaires le long des routes)
# ==================================================================

func _update_lamps(structures: Array, roads: Array) -> void:
	"""Place des lampadaires le long des routes et pres des structures."""
	var lamp_index := 0

	# Lampadaires sur chaque structure
	for struct in structures:
		if lamp_index >= MAX_LAMPS:
			break

		var sx: float = float(struct.get("x", 0))
		var sz: float = float(struct.get("z", 0))
		var level: int = int(struct.get("level", 1))
		var color_hex: String = str(struct.get("color", "#00ffcc"))
		var color := Color.html(color_hex)

		# Un lampadaire par structure (plus pour les niveaux eleves)
		var num_lamps: int = level  # 1, 2 ou 3 lampadaires
		for j in range(num_lamps):
			if lamp_index >= MAX_LAMPS:
				break

			var lamp: Node3D = _lamp_pool[lamp_index]
			lamp.visible = true

			# Position autour de la structure
			var angle: float = float(j) / float(num_lamps) * TAU + 0.5
			var offset: float = 50.0 + float(level) * 20.0  # Plus eloigne pour gros batiments (echelle x10)
			lamp.position = Vector3(
				sx + cos(angle) * offset,
				0,
				sz + sin(angle) * offset
			)

			# Mise a jour de la couleur de la lumiere
			var light: OmniLight3D = lamp.get_node_or_null("Light")
			if light:
				light.light_color = color
				light.light_energy = 0.8 + float(level) * 0.4

			lamp_index += 1

	# Cacher les lampadaires non utilises
	for i in range(lamp_index, MAX_LAMPS):
		_lamp_pool[i].visible = false


func _create_lamp() -> Node3D:
	"""Cree un lampadaire (poteau + lumiere)."""
	var container := Node3D.new()

	# Poteau vertical (taille realiste)
	var pole_mesh := CylinderMesh.new()
	pole_mesh.top_radius = 0.5
	pole_mesh.bottom_radius = 0.8
	pole_mesh.height = 50.0
	pole_mesh.radial_segments = 6

	var pole := MeshInstance3D.new()
	pole.name = "Pole"
	pole.mesh = pole_mesh
	pole.position = Vector3(0, 25.0, 0)

	var pole_mat := StandardMaterial3D.new()
	pole_mat.albedo_color = Color(0.15, 0.15, 0.2)
	pole_mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	pole_mat.metallic = 0.9
	pole_mat.roughness = 0.4
	pole.material_override = pole_mat
	container.add_child(pole)

	# Sphere lumineuse au sommet
	var bulb_mesh := SphereMesh.new()
	bulb_mesh.radius = 2.0
	bulb_mesh.height = 4.0
	bulb_mesh.radial_segments = 6
	bulb_mesh.rings = 4

	var bulb := MeshInstance3D.new()
	bulb.name = "Bulb"
	bulb.mesh = bulb_mesh
	bulb.position = Vector3(0, 51.0, 0)

	var bulb_mat := StandardMaterial3D.new()
	bulb_mat.albedo_color = Color(0.0, 1.0, 0.835, 0.9)
	bulb_mat.emission_enabled = true
	bulb_mat.emission = Color(0.0, 1.0, 0.835)
	bulb_mat.emission_energy_multiplier = 2.0
	bulb_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	bulb.material_override = bulb_mat
	container.add_child(bulb)

	# OmniLight3D
	var light := OmniLight3D.new()
	light.name = "Light"
	light.light_color = Color(0.0, 1.0, 0.835)
	light.light_energy = 3.0
	light.omni_range = 150.0
	light.omni_attenuation = 1.5
	light.shadow_enabled = false
	light.light_bake_mode = Light3D.BAKE_DISABLED
	light.position = Vector3(0, 50.0, 0)
	container.add_child(light)

	return container


# ==================================================================
#  RESEAU INFRASTRUCTURE (lignes animees entre comm towers)
# ==================================================================

func _update_network(structures: Array) -> void:
	"""Dessine des lignes de connexion entre les tours de communication."""
	var comm_towers: Array = []
	for struct in structures:
		if str(struct.get("type", "")) == "comm_tower":
			comm_towers.append(struct)

	if comm_towers.size() < 2:
		_network_mesh.visible = false
		return

	_network_mesh.visible = true

	# Creer les lignes entre toutes les paires de comm towers
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)

	var line_width: float = 3.0  # Lignes plus visibles (echelle x10)
	var line_y: float = 90.0  # Lignes aereiennes (au-dessus des batiments)

	for i in range(comm_towers.size()):
		for j in range(i + 1, comm_towers.size()):
			var t1: Dictionary = comm_towers[i]
			var t2: Dictionary = comm_towers[j]
			var x1: float = float(t1.get("x", 0))
			var z1: float = float(t1.get("z", 0))
			var x2: float = float(t2.get("x", 0))
			var z2: float = float(t2.get("z", 0))

			var dist: float = sqrt((x2 - x1) ** 2 + (z2 - z1) ** 2)
			if dist > 600:
				continue  # Trop loin

			# Ligne comme un quad etroit horizontal
			var dx: float = x2 - x1
			var dz: float = z2 - z1
			var len_seg: float = sqrt(dx * dx + dz * dz)
			if len_seg < 0.1:
				continue
			var nx: float = -dz / len_seg * line_width * 0.5
			var nz: float = dx / len_seg * line_width * 0.5

			# Arc leger (catenary) -- point milieu plus bas
			var mid_y: float = line_y - dist * 0.02

			var bl := Vector3(x1 + nx, line_y, z1 + nz)
			var br := Vector3(x1 - nx, line_y, z1 - nz)
			var ml := Vector3((x1 + x2) * 0.5 + nx, mid_y, (z1 + z2) * 0.5 + nz)
			var mr := Vector3((x1 + x2) * 0.5 - nx, mid_y, (z1 + z2) * 0.5 - nz)
			var tl := Vector3(x2 + nx, line_y, z2 + nz)
			var tr := Vector3(x2 - nx, line_y, z2 - nz)

			# Premier segment (debut -> milieu)
			st.add_vertex(bl)
			st.add_vertex(ml)
			st.add_vertex(mr)
			st.add_vertex(bl)
			st.add_vertex(mr)
			st.add_vertex(br)

			# Second segment (milieu -> fin)
			st.add_vertex(ml)
			st.add_vertex(tl)
			st.add_vertex(tr)
			st.add_vertex(ml)
			st.add_vertex(tr)
			st.add_vertex(mr)

	st.generate_normals()
	_network_mesh.mesh = st.commit()


func _animate_network() -> void:
	"""Anime les lignes de reseau (pulse lumineux)."""
	var t: float = Time.get_ticks_msec() / 1000.0
	var mat: StandardMaterial3D = _network_mesh.material_override
	if mat:
		var pulse: float = 0.8 + sin(t * 3.0) * 0.4
		mat.emission_energy_multiplier = pulse
		mat.albedo_color.a = 0.3 + sin(t * 2.0) * 0.15
