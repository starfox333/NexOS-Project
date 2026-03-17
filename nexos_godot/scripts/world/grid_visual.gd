extends Node3D
## Grille Tron -- Sol avec shader anime + heatmap energetique
## Phase 1+2 : Terrain-aware (elevation PCB + glitch zones)

const GRID_SIZE := 5000.0
const GRID_CENTER := GRID_SIZE / 2.0

var _floor_mesh: MeshInstance3D
var _floor_material: ShaderMaterial
var _energy_multimesh: MultiMeshInstance3D
var _energy_mm: MultiMesh
var _max_energy_dots := 50000
var _terrain_loaded := false


func _ready() -> void:
	_create_tron_floor()
	_create_energy_heatmap()


func _create_tron_floor() -> void:
	var plane := PlaneMesh.new()
	plane.size = Vector2(GRID_SIZE, GRID_SIZE)
	# Subdivisions hautes pour le vertex displacement terrain
	plane.subdivide_width = 500
	plane.subdivide_depth = 500

	_floor_mesh = MeshInstance3D.new()
	_floor_mesh.name = "TronFloor"
	_floor_mesh.mesh = plane
	_floor_mesh.position = Vector3(GRID_CENTER, -0.05, GRID_CENTER)

	# Shader V2 -- grille avec terrain + glitch
	var shader := load("res://shaders/tron_grid_v2.gdshader") as Shader
	if not shader:
		shader = load("res://shaders/tron_grid.gdshader") as Shader

	if shader:
		_floor_material = ShaderMaterial.new()
		_floor_material.shader = shader
		_floor_material.set_shader_parameter("line_color", Color(0.0, 0.25, 0.16))
		_floor_material.set_shader_parameter("major_color", Color(0.0, 0.6, 0.4))
		_floor_material.set_shader_parameter("pulse_color", Color(0.0, 1.0, 0.835))
		_floor_material.set_shader_parameter("bg_color", Color(0.0, 0.012, 0.02))
		_floor_material.set_shader_parameter("grid_size", GRID_SIZE)
		_floor_material.set_shader_parameter("pulse_speed", 0.3)
		_floor_material.set_shader_parameter("pulse_intensity", 0.6)
		_floor_material.set_shader_parameter("fresnel_intensity", 0.4)
		# Terrain desactive tant qu'on n'a pas recu les donnees
		_floor_material.set_shader_parameter("terrain_enabled", false)
		_floor_material.set_shader_parameter("glitch_enabled", true)
		_floor_mesh.material_override = _floor_material
	else:
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(0.0, 0.04, 0.04, 0.8)
		mat.metallic = 0.9
		mat.roughness = 0.2
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		_floor_mesh.material_override = mat

	add_child(_floor_mesh)
	_create_grid_border()
	print("[GridVisual] Floor cree: %dx%d subdivisions" % [500, 500])


# ==================================================================
#  TERRAIN UPDATE -- recoit les donnees du backend Python
# ==================================================================

func update_terrain(terrain_data: Dictionary) -> void:
	"""Decode le terrain base64 et cree une texture pour le shader."""
	if _terrain_loaded or not _floor_material:
		return

	var b64_str: String = terrain_data.get("data", "")
	var resolution: int = int(terrain_data.get("resolution", 0))
	if b64_str.is_empty() or resolution <= 0:
		print("[GridVisual] Terrain invalide: pas de data ou resolution=0")
		return

	# Decoder base64 en bytes
	var raw_bytes: PackedByteArray = Marshalls.base64_to_raw(b64_str)
	if raw_bytes.size() != resolution * resolution:
		print("[GridVisual] Terrain taille incorrecte: %d octets (attendu %d)" % [
			raw_bytes.size(), resolution * resolution])
		return

	# Creer une Image R8 (chaque pixel = terrain_id 0/1/2)
	var img := Image.create(resolution, resolution, false, Image.FORMAT_R8)
	for z in range(resolution):
		for x in range(resolution):
			var idx: int = z * resolution + x
			var terrain_id: int = raw_bytes[idx]
			# Stocker directement la valeur (0, 1, ou 2) comme intensite 0-255
			img.set_pixel(x, z, Color(float(terrain_id) / 255.0, 0, 0, 1))

	var tex := ImageTexture.create_from_image(img)
	_floor_material.set_shader_parameter("terrain_texture", tex)
	_floor_material.set_shader_parameter("terrain_enabled", true)
	_terrain_loaded = true

	# Compter les terrains pour debug
	var fertile_count := 0
	var barren_count := 0
	for i in range(raw_bytes.size()):
		if raw_bytes[i] == 1: fertile_count += 1
		elif raw_bytes[i] == 2: barren_count += 1

	print("[GridVisual] Terrain charge: %dx%d | Fertile: %d | Barren: %d | Plain: %d" % [
		resolution, resolution, fertile_count, barren_count,
		resolution * resolution - fertile_count - barren_count])
	print("[GridVisual] >>> Elevation + Glitch actifs <<<")


# ==================================================================
#  GRID BORDER
# ==================================================================

func _create_grid_border() -> void:
	var im := ImmediateMesh.new()
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.0, 1.0, 0.835, 0.6)
	mat.emission_enabled = true
	mat.emission = Color(0.0, 1.0, 0.835)
	mat.emission_energy_multiplier = 0.5
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED

	var y := 0.1
	im.surface_begin(Mesh.PRIMITIVE_LINE_STRIP, mat)
	im.surface_add_vertex(Vector3(0, y, 0))
	im.surface_add_vertex(Vector3(GRID_SIZE, y, 0))
	im.surface_add_vertex(Vector3(GRID_SIZE, y, GRID_SIZE))
	im.surface_add_vertex(Vector3(0, y, GRID_SIZE))
	im.surface_add_vertex(Vector3(0, y, 0))
	im.surface_end()

	var border := MeshInstance3D.new()
	border.name = "GridBorder"
	border.mesh = im
	add_child(border)


# ==================================================================
#  ENERGY HEATMAP
# ==================================================================

func _create_energy_heatmap() -> void:
	var dot_mesh := PlaneMesh.new()
	dot_mesh.size = Vector2(8.0, 8.0)

	_energy_mm = MultiMesh.new()
	_energy_mm.transform_format = MultiMesh.TRANSFORM_3D
	_energy_mm.use_colors = true
	_energy_mm.mesh = dot_mesh
	_energy_mm.instance_count = _max_energy_dots

	for i in range(_max_energy_dots):
		_energy_mm.set_instance_transform(i, Transform3D().scaled(Vector3.ZERO))
		_energy_mm.set_instance_color(i, Color(0, 0, 0, 0))

	_energy_multimesh = MultiMeshInstance3D.new()
	_energy_multimesh.name = "EnergyHeatmap"
	_energy_multimesh.multimesh = _energy_mm

	var mat := StandardMaterial3D.new()
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.vertex_color_use_as_albedo = true
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	_energy_multimesh.material_override = mat

	add_child(_energy_multimesh)


func update_energy(energy_map: Array) -> void:
	"""Met a jour la heatmap energetique depuis les donnees Python."""
	var count: int = mini(energy_map.size(), _max_energy_dots)

	for i in range(count):
		var cell: Dictionary = energy_map[i]
		var x: float = float(cell.get("x", 0))
		var z: float = float(cell.get("z", 0))
		var e: float = float(cell.get("e", 0))

		var xform := Transform3D()
		xform.origin = Vector3(x, 0.05, z)
		_energy_mm.set_instance_transform(i, xform)

		var intensity: float = clamp(e / 150.0, 0.0, 1.0)
		var r: float = (1.0 - intensity)
		var g: float = intensity
		var alpha: float = 0.03 + intensity * 0.15
		_energy_mm.set_instance_color(i, Color(r, g, 0.5, alpha))

	for i in range(count, _max_energy_dots):
		_energy_mm.set_instance_transform(i, Transform3D().scaled(Vector3.ZERO))
