extends Node3D
## Rendu des Lightcycles -- motos de lumiere Tron
## Chaque Lightcycle a un corps + mur de lumiere (trail)

const MAX_VEHICLES := 30

# Pool de nodes vehicules pre-alloues
var _vehicle_nodes: Array[Node3D] = []
var _trail_meshes: Array[MeshInstance3D] = []
var _vehicle_lights: Array[OmniLight3D] = []
var _active_count := 0

# Modele FBX optionnel (Lightcars de Sketchfab)
var _fbx_lightcars: PackedScene = null
var _use_fbx_model := false

# Couleurs Tron par type
var _colors := {
	"cyan": Color(0.0, 1.0, 0.835),
	"orange": Color(1.0, 0.55, 0.0),
	"gold": Color(1.0, 0.843, 0.0),
}


func _ready() -> void:
	_try_load_fbx_model()
	_create_vehicle_pool()


func _try_load_fbx_model() -> void:
	"""Tente de charger un modele 3D vehicule. Priorite : GLB > FBX."""
	# Essayer les GLB en priorite (importes automatiquement par Godot)
	var glb_paths := [
		"res://assets/models/vehicles/tron_uprising_-_argoncity_light_cycle.glb",
		"res://assets/models/vehicles/tron_catalyst_vehicles.glb",
		"res://assets/models/vehicles/Lightcars.fbx",
	]
	for path in glb_paths:
		if ResourceLoader.exists(path):
			var scene: PackedScene = load(path)
			if scene:
				_fbx_lightcars = scene
				_use_fbx_model = true
				print("VehicleRenderer: Modele 3D charge depuis %s" % path.get_file())
				return
	print("VehicleRenderer: Aucun modele 3D vehicule -- fallback procedural")


func _create_vehicle_pool() -> void:
	"""Pre-alloue un pool de nodes pour les vehicules."""
	for i in range(MAX_VEHICLES):
		var container := Node3D.new()
		container.name = "Lightcycle_%d" % i
		container.visible = false

		# Corps du Lightcycle (FBX ou procedural)
		var body: Node3D
		if _use_fbx_model and _fbx_lightcars:
			body = _fbx_lightcars.instantiate()
			body.scale = Vector3(8.0, 8.0, 8.0)  # Taille realiste pour Sims 4 scale x10
		else:
			body = _create_lightcycle_body()
		body.name = "Body"
		container.add_child(body)

		# Roue avant (torus fin lumineux)
		var wheel_f := _create_wheel()
		wheel_f.name = "WheelFront"
		container.add_child(wheel_f)

		# Roue arriere
		var wheel_r := _create_wheel()
		wheel_r.name = "WheelRear"
		container.add_child(wheel_r)

		add_child(container)
		_vehicle_nodes.append(container)

		# Trail (mur de lumiere) -- mesh regenere a chaque frame
		var trail := MeshInstance3D.new()
		trail.name = "Trail_%d" % i
		trail.visible = false
		var trail_mat := StandardMaterial3D.new()
		trail_mat.emission_enabled = true
		trail_mat.emission = Color(0.0, 1.0, 0.835)
		trail_mat.emission_energy_multiplier = 1.8
		trail_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		trail_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		trail_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
		trail.material_override = trail_mat
		add_child(trail)
		_trail_meshes.append(trail)

		# Lumiere dynamique du Lightcycle
		var light := OmniLight3D.new()
		light.name = "LightcycleLight_%d" % i
		light.light_energy = 5.0
		light.omni_range = 200.0
		light.omni_attenuation = 1.5
		light.shadow_enabled = false
		light.light_bake_mode = Light3D.BAKE_DISABLED
		light.visible = false
		add_child(light)
		_vehicle_lights.append(light)


func _create_lightcycle_body() -> MeshInstance3D:
	"""Cree le corps procedural du Lightcycle (forme aerodynamique)."""
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)

	# Corps allonge -- prisme horizontal (moto Tron stylisee) -- echelle x10
	var length: float = 25.0  # Longueur (2.5 x10)
	var width: float = 3.0    # Largeur (0.3 x10)
	var height: float = 8.0   # Hauteur (0.8 x10)

	# 6 points : pointe avant, corps central, arriere
	var front := Vector3(length * 0.6, 0, 0)
	var back := Vector3(-length * 0.4, 0, 0)
	var top := Vector3(0, height, 0)

	# Section centrale (hexagonale en coupe)
	var pts: Array[Vector3] = []
	for i in range(6):
		var angle: float = float(i) / 6.0 * TAU
		pts.append(Vector3(0, sin(angle) * height * 0.5 + height * 0.3,
			cos(angle) * width))

	# Faces avant (du centre vers la pointe)
	for i in range(6):
		var n: int = (i + 1) % 6
		st.add_vertex(front)
		st.add_vertex(pts[i])
		st.add_vertex(pts[n])

	# Faces arriere
	for i in range(6):
		var n: int = (i + 1) % 6
		st.add_vertex(back)
		st.add_vertex(pts[n])
		st.add_vertex(pts[i])

	st.generate_normals()
	var mesh: ArrayMesh = st.commit()

	var mi := MeshInstance3D.new()
	mi.mesh = mesh

	# PBR metallique noir -- carrosserie Lightcycle
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.04, 0.04, 0.07, 0.95)
	mat.metallic = 0.9
	mat.roughness = 0.15
	mat.emission_enabled = true
	mat.emission = Color(0.0, 1.0, 0.835)
	mat.emission_energy_multiplier = 0.5
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	mat.rim_enabled = true
	mat.rim = 0.25
	mat.rim_tint = 0.4
	mi.material_override = mat

	return mi


func _create_wheel() -> MeshInstance3D:
	"""Cree une roue lumineuse (torus fin) -- PBR metallique."""
	var torus := TorusMesh.new()
	torus.inner_radius = 2.5   # 0.25 x10
	torus.outer_radius = 3.5   # 0.35 x10
	torus.rings = 8
	torus.ring_segments = 6

	var mi := MeshInstance3D.new()
	mi.mesh = torus

	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.08, 0.08, 0.1, 0.9)
	mat.metallic = 0.85
	mat.roughness = 0.2
	mat.emission_enabled = true
	mat.emission = Color(0.0, 1.0, 0.835)
	mat.emission_energy_multiplier = 2.0
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	mi.material_override = mat

	return mi


func update_vehicles(vehicles: Array) -> void:
	"""Met a jour les Lightcycles depuis les donnees Python."""
	var time_val: float = Time.get_ticks_msec() / 1000.0
	_active_count = mini(vehicles.size(), MAX_VEHICLES)

	for i in range(_active_count):
		var data: Dictionary = vehicles[i]
		var vx: float = float(data.get("x", 0))
		var vz: float = float(data.get("z", 0))
		var direction: int = int(data.get("direction", 0))
		var speed: float = float(data.get("speed", 3.0))
		var color_name: String = str(data.get("color", "cyan"))
		var trail: Array = data.get("trail", [])

		var container: Node3D = _vehicle_nodes[i]
		container.visible = true

		# Couleur selon le type
		var color: Color = _colors.get(color_name, _colors["cyan"])

		# Position et rotation selon la direction
		var rot_y: float = 0.0
		match direction:
			0: rot_y = 0.0         # Nord
			1: rot_y = -PI / 2.0   # Est
			2: rot_y = PI          # Sud
			3: rot_y = PI / 2.0    # Ouest

		# Hauteur de flottement (les Lightcycles planent) -- echelle x10
		var hover_y: float = 6.0 + sin(time_val * 8.0 + float(i)) * 0.5
		container.position = Vector3(vx, hover_y, vz)
		container.rotation.y = rot_y

		# Mise a jour de la couleur du corps
		var body: Node3D = container.get_node_or_null("Body")
		if body and body is MeshInstance3D:
			var mat: StandardMaterial3D = body.material_override
			if mat:
				mat.emission = color
				mat.emission_energy_multiplier = 0.5 + sin(time_val * 4.0) * 0.2

		# Roues : positionnees devant/derriere, rotation animee
		var wheel_f: Node3D = container.get_node_or_null("WheelFront")
		if wheel_f:
			wheel_f.position = Vector3(12.0, -1.0, 0)
			wheel_f.rotation.z = time_val * speed * 2.0
			if wheel_f is MeshInstance3D:
				var wmat: StandardMaterial3D = wheel_f.material_override
				if wmat:
					wmat.emission = color

		var wheel_r: Node3D = container.get_node_or_null("WheelRear")
		if wheel_r:
			wheel_r.position = Vector3(-10.0, -1.0, 0)
			wheel_r.rotation.z = time_val * speed * 2.0
			if wheel_r is MeshInstance3D:
				var wmat: StandardMaterial3D = wheel_r.material_override
				if wmat:
					wmat.emission = color

		# Lumiere dynamique
		var light: OmniLight3D = _vehicle_lights[i]
		light.visible = true
		light.position = Vector3(vx, hover_y + 10.0, vz)
		light.light_color = color
		light.light_energy = 5.0 + sin(time_val * 3.0 + float(i)) * 1.5

		# Trail (mur de lumiere) -- reconstruit chaque frame
		_update_trail(i, trail, color)

	# Cacher les vehicules inactifs
	for i in range(_active_count, MAX_VEHICLES):
		_vehicle_nodes[i].visible = false
		_trail_meshes[i].visible = false
		_vehicle_lights[i].visible = false


func _update_trail(index: int, trail: Array, color: Color) -> void:
	"""Reconstruit le mesh du mur de lumiere."""
	var trail_mi: MeshInstance3D = _trail_meshes[index]

	if trail.size() < 2:
		trail_mi.visible = false
		return

	trail_mi.visible = true

	# Mur de lumiere vertical : pour chaque segment, un quad vertical
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)

	var wall_height: float = 25.0  # Hauteur du mur de lumiere (2.5 x10)
	var wall_y_base: float = 1.0   # Base au sol (0.1 x10)

	for j in range(trail.size() - 1):
		var p1: Dictionary = trail[j]
		var p2: Dictionary = trail[j + 1]
		var x1: float = float(p1.get("x", 0))
		var z1: float = float(p1.get("z", 0))
		var x2: float = float(p2.get("x", 0))
		var z2: float = float(p2.get("z", 0))

		# Opacite degradee (plus vieux = plus transparent)
		var alpha: float = float(j) / float(trail.size()) * 0.6 + 0.2

		# 4 coins du quad vertical
		var bl := Vector3(x1, wall_y_base, z1)
		var tl := Vector3(x1, wall_y_base + wall_height * alpha, z1)
		var br := Vector3(x2, wall_y_base, z2)
		var tr := Vector3(x2, wall_y_base + wall_height * alpha, z2)

		# Face avant
		st.add_vertex(bl)
		st.add_vertex(tr)
		st.add_vertex(tl)

		st.add_vertex(bl)
		st.add_vertex(br)
		st.add_vertex(tr)

		# Face arriere (pour double-face)
		st.add_vertex(bl)
		st.add_vertex(tl)
		st.add_vertex(tr)

		st.add_vertex(bl)
		st.add_vertex(tr)
		st.add_vertex(br)

	st.generate_normals()
	trail_mi.mesh = st.commit()

	# Mettre a jour la couleur du trail
	var mat: StandardMaterial3D = trail_mi.material_override
	if mat:
		mat.albedo_color = Color(color.r, color.g, color.b, 0.5)
		mat.emission = color
