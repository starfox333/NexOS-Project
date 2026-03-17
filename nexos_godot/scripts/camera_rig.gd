extends Node3D
## NexOS v5 -- Camera Sims 4 x Tron
## Mode ORBITAL : vue du dessus (defaut, Sims 4 classique)
## Mode FLY     : vue au sol premiere personne (Tab pour switch)
## Mode FOLLOW  : suit un ISO selectionne (F pour toggle)
## ZQSD : deplacement | Souris : rotation | Molette : zoom
## Tab : switch orbital/fly | Espace/Shift : monter/descendre

const GRID_SIZE := 5000.0
const GRID_CENTER := GRID_SIZE / 2.0

enum CamMode { ORBITAL, FLY, FOLLOW }

@export var move_speed := 3.0        # Vitesse adaptee camera proche Sims 4
@export var fly_speed := 2.5        # Vitesse pieton
@export var zoom_speed := 8.0
@export var auto_rotate_speed := 0.002
@export var mouse_sensitivity := 0.005
@export var fly_mouse_sensitivity := 0.003

# Orbital mode -- camera proche Sims 4 (on voit les details)
var cam_angle := 0.0
var cam_radius := 120.0       # Proche comme Sims 4
var cam_height := 60.0        # Bas pour voir les ISOs de pres
var cam_center := Vector3(GRID_CENTER, 0, GRID_CENTER)
var auto_rotate := true
var mouse_dragging := false
var last_mouse_pos := Vector2.ZERO

# Fly mode -- hauteur yeux humain (~25 units = tete ISO a scale x15)
var fly_position := Vector3(GRID_CENTER, 25.0, GRID_CENTER)
var fly_yaw := 0.0
var fly_pitch := -0.05

# Follow mode -- camera proche derriere l'ISO
var follow_target_pos := Vector3.ZERO
var follow_offset := Vector3(0, 30, 40)

# Follow mode -- camera proche derriere l'ISO
# Entity positions for teleport (updated from main.gd)
var entity_positions: Dictionary = {}  # "minerve" -> Vector3, "tron" -> Vector3, etc.
var iso_center: Vector3 = Vector3(GRID_CENTER, 0, GRID_CENTER)

# State
var mode: CamMode = CamMode.ORBITAL
var chat_focused := false
var camera: Camera3D
var _follow_iso_id := -1


func _ready() -> void:
	if not has_node("Camera3D"):
		camera = Camera3D.new()
		camera.name = "Camera3D"
		camera.fov = 60.0
		camera.far = 12000.0      # Distance de rendu pour grille 5000x5000
		add_child(camera)
		camera.current = true
	else:
		camera = $Camera3D
		camera.current = true
	_update_camera_pos()


func _unhandled_input(event: InputEvent) -> void:
	if chat_focused:
		return

	# Tab = switch mode
	if event is InputEventKey and event.pressed and event.keycode == KEY_TAB:
		_toggle_mode()
		return

	# Teleport vers les entites (touches numeriques)
	if event is InputEventKey and event.pressed and not event.shift_pressed and not event.ctrl_pressed:
		match event.keycode:
			KEY_1:
				_teleport_to_entity("minerve")
				return
			KEY_2:
				_teleport_to_entity("tron")
				return
			KEY_3:
				_teleport_to_entity("symmetra")
				return
			KEY_4:
				_teleport_to_entity("daedalus")
				return
			KEY_5:
				teleport_to(iso_center)
				print("[Camera] Teleport -> Centre ISOs (%.0f, %.0f)" % [iso_center.x, iso_center.z])
				return

	# F = toggle follow mode
	if event is InputEventKey and event.pressed and event.keycode == KEY_F:
		if mode == CamMode.FOLLOW:
			mode = CamMode.ORBITAL
			_follow_iso_id = -1
		else:
			# Get selected ISO from HUD
			var hud = get_node_or_null("/root/NexOS/HUD")
			if hud and hud.has_method("get_selected_iso_id"):
				var iso_id: int = hud.get_selected_iso_id()
				if iso_id > 0:
					mode = CamMode.FOLLOW
					_follow_iso_id = iso_id
		return

	# Mouse handling per mode
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mode == CamMode.ORBITAL:
			if mb.button_index == MOUSE_BUTTON_LEFT:
				mouse_dragging = mb.pressed
				if mb.pressed:
					last_mouse_pos = mb.position
					auto_rotate = false
			elif mb.button_index == MOUSE_BUTTON_WHEEL_UP:
				cam_radius = max(15.0, cam_radius - zoom_speed * 2.0)
				cam_height = max(8.0, cam_height - zoom_speed)
			elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
				cam_radius = min(1500.0, cam_radius + zoom_speed * 2.0)
				cam_height = min(600.0, cam_height + zoom_speed)
		elif mode == CamMode.FLY:
			if mb.button_index == MOUSE_BUTTON_LEFT:
				mouse_dragging = mb.pressed
				if mb.pressed:
					last_mouse_pos = mb.position
		elif mode == CamMode.FOLLOW:
			if mb.button_index == MOUSE_BUTTON_WHEEL_UP:
				follow_offset.y = max(8.0, follow_offset.y - 3.0)
				follow_offset.z = max(12.0, follow_offset.z - 3.0)
			elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
				follow_offset.y = min(120.0, follow_offset.y + 3.0)
				follow_offset.z = min(150.0, follow_offset.z + 3.0)

	elif event is InputEventMouseMotion and mouse_dragging:
		var mm := event as InputEventMouseMotion
		var delta_pos := mm.position - last_mouse_pos
		if mode == CamMode.ORBITAL:
			cam_angle += delta_pos.x * mouse_sensitivity
			cam_height = clamp(cam_height - delta_pos.y * 0.3, 8.0, 600.0)
		elif mode == CamMode.FLY:
			fly_yaw -= delta_pos.x * fly_mouse_sensitivity
			fly_pitch = clamp(fly_pitch - delta_pos.y * fly_mouse_sensitivity, -1.2, 1.2)
		last_mouse_pos = mm.position


func _process(delta: float) -> void:
	match mode:
		CamMode.ORBITAL:
			_process_orbital(delta)
		CamMode.FLY:
			_process_fly(delta)
		CamMode.FOLLOW:
			_process_follow(delta)


func _process_orbital(delta: float) -> void:
	if chat_focused:
		if auto_rotate:
			cam_angle += auto_rotate_speed
		_update_camera_pos()
		return

	var fwd := Vector3(-cos(cam_angle), 0, -sin(cam_angle))
	var right := Vector3(sin(cam_angle), 0, -cos(cam_angle))
	var moved := false

	if Input.is_action_pressed("move_forward"):
		cam_center += fwd * move_speed; moved = true
	if Input.is_action_pressed("move_back"):
		cam_center -= fwd * move_speed; moved = true
	if Input.is_action_pressed("move_left"):
		cam_center -= right * move_speed; moved = true
	if Input.is_action_pressed("move_right"):
		cam_center += right * move_speed; moved = true
	if Input.is_action_pressed("cam_up"):
		cam_height = min(600.0, cam_height + 2.0); moved = true
	if Input.is_action_pressed("cam_down"):
		cam_height = max(8.0, cam_height - 2.0); moved = true

	if moved:
		auto_rotate = false

	cam_center.x = clamp(cam_center.x, -50.0, GRID_SIZE + 50.0)
	cam_center.z = clamp(cam_center.z, -50.0, GRID_SIZE + 50.0)

	if auto_rotate:
		cam_angle += auto_rotate_speed

	_update_camera_pos()


func _process_fly(_delta: float) -> void:
	if chat_focused:
		return

	var fwd := Vector3(-sin(fly_yaw), 0, -cos(fly_yaw))
	var right := Vector3(-cos(fly_yaw), 0, sin(fly_yaw))

	if Input.is_action_pressed("move_forward"):
		fly_position += fwd * fly_speed
	if Input.is_action_pressed("move_back"):
		fly_position -= fwd * fly_speed
	if Input.is_action_pressed("move_left"):
		fly_position -= right * fly_speed
	if Input.is_action_pressed("move_right"):
		fly_position += right * fly_speed
	if Input.is_action_pressed("cam_up"):
		fly_position.y = min(200.0, fly_position.y + 1.5)
	if Input.is_action_pressed("cam_down"):
		fly_position.y = max(3.0, fly_position.y - 1.5)

	# Clamp to grid
	fly_position.x = clamp(fly_position.x, -20.0, GRID_SIZE + 20.0)
	fly_position.z = clamp(fly_position.z, -20.0, GRID_SIZE + 20.0)

	if camera:
		camera.global_position = fly_position
		camera.rotation = Vector3(fly_pitch, fly_yaw, 0)


func _process_follow(_delta: float) -> void:
	if not camera:
		return

	# Get ISO position from last state
	var main_node = get_node_or_null("/root/NexOS")
	if main_node and main_node.has_method("get") and _follow_iso_id > 0:
		var last_state: Dictionary = main_node.get("last_state") if main_node.get("last_state") is Dictionary else {}
		var isos: Array = last_state.get("isos", [])
		for iso in isos:
			if int(iso.get("id", -1)) == _follow_iso_id:
				var tx := float(iso.get("x", 0))
				var tz := float(iso.get("z", 0))
				follow_target_pos = follow_target_pos.lerp(Vector3(tx, 0, tz), 0.08)
				break

	camera.global_position = follow_target_pos + follow_offset
	camera.look_at(follow_target_pos + Vector3(0, 12, 0), Vector3.UP)


func _update_camera_pos() -> void:
	if not camera:
		return
	camera.global_position = Vector3(
		cam_center.x + cos(cam_angle) * cam_radius,
		cam_height,
		cam_center.z + sin(cam_angle) * cam_radius
	)
	camera.look_at(cam_center, Vector3.UP)


func _toggle_mode() -> void:
	if mode == CamMode.ORBITAL:
		# Switch to FLY mode at current look position
		mode = CamMode.FLY
		fly_position = cam_center + Vector3(0, 25, 0)
		fly_yaw = cam_angle + PI
		fly_pitch = -0.15
		mouse_dragging = false
		print("[Camera] Mode FLY (vue au sol)")
	else:
		# Switch back to ORBITAL
		mode = CamMode.ORBITAL
		cam_center = Vector3(fly_position.x, 0, fly_position.z)
		auto_rotate = false
		mouse_dragging = false
		_follow_iso_id = -1
		print("[Camera] Mode ORBITAL (vue du dessus)")


func get_mode_name() -> String:
	match mode:
		CamMode.ORBITAL: return "ORBITAL"
		CamMode.FLY: return "FLY"
		CamMode.FOLLOW: return "FOLLOW"
	return "?"


func get_camera_position() -> Vector3:
	"""Retourne la position globale de la camera (pour LOD animations)."""
	if camera:
		return camera.global_position
	return Vector3(1000, 60, 1000)


func teleport_to(target: Vector3) -> void:
	"""Teleporte la camera vers une position cible."""
	if mode == CamMode.ORBITAL:
		cam_center = Vector3(target.x, 0, target.z)
		cam_radius = 150.0
		cam_height = 80.0
		auto_rotate = false
	elif mode == CamMode.FLY:
		fly_position = Vector3(target.x, 50.0, target.z)
	_update_camera_pos()


func _teleport_to_entity(entity_name: String) -> void:
	"""Teleporte vers une entite par nom."""
	if entity_positions.has(entity_name):
		var pos: Vector3 = entity_positions[entity_name]
		teleport_to(pos)
		print("[Camera] Teleport -> %s (%.0f, %.0f)" % [entity_name.to_upper(), pos.x, pos.z])
	else:
		print("[Camera] Entite '%s' introuvable" % entity_name)


func update_entity_positions(minerve: Dictionary, tron: Dictionary, symmetra: Dictionary, daedalus: Dictionary, isos: Array) -> void:
	"""Met a jour les positions des entites pour teleportation."""
	if not minerve.is_empty() and minerve.get("enabled", false):
		entity_positions["minerve"] = Vector3(float(minerve.get("x", 0)), 0, float(minerve.get("z", 0)))
	if not tron.is_empty() and tron.get("enabled", false):
		entity_positions["tron"] = Vector3(float(tron.get("x", 0)), 0, float(tron.get("z", 0)))
	if not symmetra.is_empty() and symmetra.get("enabled", false):
		entity_positions["symmetra"] = Vector3(float(symmetra.get("x", 0)), 0, float(symmetra.get("z", 0)))
	if not daedalus.is_empty() and daedalus.get("enabled", false):
		entity_positions["daedalus"] = Vector3(float(daedalus.get("x", 0)), 0, float(daedalus.get("z", 0)))

	# Centre des ISOs
	if isos.size() > 0:
		var sum_x := 0.0
		var sum_z := 0.0
		var count := 0
		# Echantillonner max 100 ISOs pour la perf
		var step := maxi(1, isos.size() / 100)
		for i in range(0, isos.size(), step):
			sum_x += float(isos[i].get("x", 0))
			sum_z += float(isos[i].get("z", 0))
			count += 1
		if count > 0:
			iso_center = Vector3(sum_x / count, 0, sum_z / count)
