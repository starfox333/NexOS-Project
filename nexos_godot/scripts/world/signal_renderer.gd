extends Node3D
## Rendu des signaux de communication ISO
## Anneaux animes avec couleurs par type de signal.

const SIGNAL_COLORS := {
	"FOOD_HERE":  Color(0.0, 1.0, 0.0),
	"DANGER":     Color(1.0, 0.267, 0.267),
	"COME_HERE":  Color(0.0, 0.667, 1.0),
	"NEED_HELP":  Color(1.0, 0.533, 0.0),
	"WISDOM":     Color(1.0, 0.843, 0.0),
	"PROTECTION": Color(0.0, 0.898, 1.0),
}

const MAX_SIGNALS := 200

var _signal_meshes: Array[MeshInstance3D] = []
var _signal_mats: Array[StandardMaterial3D] = []
var _ring_mesh: TorusMesh


func _ready() -> void:
	_ring_mesh = TorusMesh.new()
	_ring_mesh.inner_radius = 5.0
	_ring_mesh.outer_radius = 15.0
	_ring_mesh.rings = 16
	_ring_mesh.ring_segments = 6

	# Pre-allouer le pool de signaux
	for i in range(MAX_SIGNALS):
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(0, 1, 0, 0.4)
		mat.emission_enabled = true
		mat.emission = Color(0, 1, 0)
		mat.emission_energy_multiplier = 0.5
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		mat.cull_mode = BaseMaterial3D.CULL_DISABLED
		_signal_mats.append(mat)

		var mi := MeshInstance3D.new()
		mi.mesh = _ring_mesh
		mi.material_override = mat
		mi.rotation.x = PI / 2.0
		mi.visible = false
		add_child(mi)
		_signal_meshes.append(mi)


func update_signals(signals: Array) -> void:
	var count := mini(signals.size(), MAX_SIGNALS)
	var t := Time.get_ticks_msec() / 1000.0

	for i in range(count):
		var sig: Dictionary = signals[i]
		var sx: float = float(sig.get("x", 0))
		var sz: float = float(sig.get("z", 0))
		var sig_type: String = sig.get("type", "FOOD_HERE")
		var sig_radius: float = float(sig.get("radius", 10))
		var ttl: float = float(sig.get("ttl", 20))

		var mi := _signal_meshes[i]
		mi.visible = true
		mi.position = Vector3(sx, 5.0, sz)

		# Couleur selon type
		var color: Color = SIGNAL_COLORS.get(sig_type, Color.WHITE)
		var mat := _signal_mats[i]
		mat.albedo_color = Color(color.r, color.g, color.b, 0.0)
		mat.emission = color

		# Pulse animation
		var pulse: float = 0.3 + sin(t * 3.0 + float(i)) * 0.15
		mat.albedo_color.a = pulse * (ttl / 20.0)

		# Scale selon rayon
		var s: float = sig_radius / 1.5  # Echelle x10 Sims 4
		mi.scale = Vector3(s, s, s)

	# Masquer le reste
	for i in range(count, MAX_SIGNALS):
		_signal_meshes[i].visible = false
