extends Node3D
## NexOS v5.0 -- Controleur principal (Sims 4 x Tron)
## Interface Sims 4 + esthetique Tron, selection ISO, build mode, mods
## Construit la scene, gere les sous-systemes, route les donnees.

# Sous-systemes (crees dans _ready)
var ws_client: Node
var camera_rig: Node3D
var grid_visual: Node3D
var iso_manager: Node3D
var iso_anim_loader: Node  ## Chargeur d'animations FBX pour les ISOs
var entity_renderer: Node3D
var structure_manager: Node3D
var signal_renderer: Node3D
var asset_loader: Node
var vehicle_renderer: Node3D
var city_renderer: Node3D
var energy_flow: Node3D
var hud: CanvasLayer
var mod_manager: CanvasLayer
var daedalus_terminal: CanvasLayer

# Post-processing
var _post_process_rect: ColorRect

var last_state: Dictionary = {}
var _frame_count := 0

# Selection system
const GRID_SIZE := 5000.0


func _ready() -> void:
	print("NexOS v5.0 -- Demarrage (Sims 4 x Tron)...")
	_setup_environment()
	_setup_lighting()
	_create_subsystems()
	_setup_post_processing()

	# Connecter WebSocket
	ws_client.state_received.connect(_on_state_received)
	ws_client.chat_response_received.connect(_on_chat_response)
	ws_client.connection_changed.connect(_on_connection_changed)
	ws_client.terrain_received.connect(_on_terrain_received)
	ws_client.connect_to_server()

	print("NexOS v5.0 -- Pret. En attente du backend Python...")


# ==================================================================
#  SETUP SCENE -- Environnement ameliore
# ==================================================================

func _setup_environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.0, 0.012, 0.025)

	# Ambient light -- teinte Tron plus profonde
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.0, 0.12, 0.18)
	env.ambient_light_energy = 0.5

	# ---- GLOW / BLOOM (calibre PBR + neon) ----
	env.glow_enabled = true
	env.glow_intensity = 1.0
	env.glow_bloom = 0.4
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	env.glow_hdr_threshold = 0.8
	env.glow_hdr_scale = 2.5
	env.glow_hdr_luminance_cap = 12.0
	# Multi-niveaux de bloom pour halo large
	env.set_glow_level(0, true)   # Fin
	env.set_glow_level(1, true)   # Moyen-fin
	env.set_glow_level(2, true)   # Moyen
	env.set_glow_level(3, true)   # Large
	env.set_glow_level(4, false)
	env.set_glow_level(5, true)   # Tres large (halo lointain)
	env.set_glow_level(6, false)

	# ---- SSR (Screen Space Reflections -- reflets sol PBR) ----
	env.ssr_enabled = true
	env.ssr_max_steps = 96
	env.ssr_fade_in = 0.15
	env.ssr_fade_out = 2.0
	env.ssr_depth_tolerance = 0.2

	# ---- SSAO (ambient occlusion subtile) ----
	env.ssao_enabled = true
	env.ssao_radius = 2.0
	env.ssao_intensity = 0.8
	env.ssao_power = 1.5
	env.ssao_light_affect = 0.3

	# ---- FOG volumetrique (Phase 5) ----
	env.fog_enabled = false  # Remplace par le volumetric fog
	env.volumetric_fog_enabled = true
	env.volumetric_fog_density = 0.012
	env.volumetric_fog_albedo = Color(0.0, 0.06, 0.08)
	env.volumetric_fog_emission = Color(0.0, 0.03, 0.04)
	env.volumetric_fog_emission_energy = 0.5
	env.volumetric_fog_anisotropy = 0.6
	env.volumetric_fog_length = 200.0
	env.volumetric_fog_detail_spread = 2.0
	env.volumetric_fog_gi_inject = 0.5

	# ---- Tonemap ----
	env.tonemap_mode = 3  # ACES
	env.tonemap_exposure = 1.1

	# ---- Adjustments (contraste + saturation Tron) ----
	env.adjustment_enabled = true
	env.adjustment_contrast = 1.15
	env.adjustment_saturation = 1.2
	env.adjustment_brightness = 1.0

	var we := WorldEnvironment.new()
	we.name = "WorldEnv"
	we.environment = env
	add_child(we)


func _setup_lighting() -> void:
	# Lumiere directionnelle principale -- teinte Tron cyan
	var dir_light := DirectionalLight3D.new()
	dir_light.name = "MainLight"
	dir_light.light_color = Color(0.0, 0.85, 0.7)
	dir_light.light_energy = 1.2
	dir_light.shadow_enabled = true
	dir_light.shadow_bias = 0.05
	dir_light.shadow_blur = 2.0
	dir_light.rotation_degrees = Vector3(-40, 45, 0)
	add_child(dir_light)

	# Lumiere de fill -- violet/indigo subtil
	var fill_light := DirectionalLight3D.new()
	fill_light.name = "FillLight"
	fill_light.light_color = Color(0.25, 0.1, 0.55)
	fill_light.light_energy = 0.6
	fill_light.shadow_enabled = true
	fill_light.shadow_blur = 1.0
	fill_light.rotation_degrees = Vector3(-20, -120, 0)
	add_child(fill_light)

	# Lumiere rim -- eclairage de contour depuis le bas
	var rim_light := DirectionalLight3D.new()
	rim_light.name = "RimLight"
	rim_light.light_color = Color(0.0, 0.5, 0.4)
	rim_light.light_energy = 0.5
	rim_light.shadow_enabled = false
	rim_light.rotation_degrees = Vector3(60, -90, 0)
	add_child(rim_light)

	# OmniLight au centre de la grille -- point focal (continent 10000x10000)
	var center_light := OmniLight3D.new()
	center_light.name = "CenterGlow"
	center_light.light_color = Color(0.0, 1.0, 0.835)
	center_light.light_energy = 3.0
	center_light.omni_range = 1000.0
	center_light.omni_attenuation = 1.5
	center_light.shadow_enabled = false
	center_light.position = Vector3(2500.0, 100.0, 2500.0)
	add_child(center_light)


func _setup_post_processing() -> void:
	# Overlay CanvasLayer pour scanlines CRT
	var post_layer := CanvasLayer.new()
	post_layer.name = "PostProcess"
	post_layer.layer = 10  # Au dessus de tout

	_post_process_rect = ColorRect.new()
	_post_process_rect.name = "ScanlineOverlay"
	_post_process_rect.anchors_preset = Control.PRESET_FULL_RECT
	_post_process_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE

	# Charger le shader scanline
	var shader := load("res://shaders/scanline_post.gdshader") as Shader
	if shader:
		var mat := ShaderMaterial.new()
		mat.shader = shader
		mat.set_shader_parameter("scanline_opacity", 0.05)
		mat.set_shader_parameter("vignette_intensity", 0.3)
		mat.set_shader_parameter("aberration_amount", 0.8)
		mat.set_shader_parameter("flicker_amount", 0.005)
		mat.set_shader_parameter("tint_color", Color(0.88, 0.96, 1.0))
		_post_process_rect.material = mat
		post_layer.add_child(_post_process_rect)
		add_child(post_layer)
		print("[PostProcess] Scanline overlay actif")
	else:
		print("[PostProcess] Shader non trouve, post-processing desactive")


# ==================================================================
#  CREATION DES SOUS-SYSTEMES
# ==================================================================

func _create_subsystems() -> void:
	# Asset Loader (charge les GLB Sketchfab)
	asset_loader = Node.new()
	asset_loader.name = "AssetLoader"
	asset_loader.set_script(load("res://scripts/world/asset_loader.gd"))
	add_child(asset_loader)

	# WebSocket Client
	ws_client = Node.new()
	ws_client.name = "WSClient"
	ws_client.set_script(load("res://scripts/ws_client.gd"))
	add_child(ws_client)

	# Camera
	camera_rig = Node3D.new()
	camera_rig.name = "CameraRig"
	camera_rig.set_script(load("res://scripts/camera_rig.gd"))
	add_child(camera_rig)

	# Grille Tron (shader V2)
	grid_visual = Node3D.new()
	grid_visual.name = "GridVisual"
	grid_visual.set_script(load("res://scripts/world/grid_visual.gd"))
	add_child(grid_visual)

	# ISO Animation Loader (charge les FBX Mixamo)
	iso_anim_loader = Node.new()
	iso_anim_loader.name = "ISOAnimLoader"
	iso_anim_loader.set_script(load("res://scripts/world/iso_animation_loader.gd"))
	add_child(iso_anim_loader)

	# ISOs (Hybride : MultiMesh + pool anime LOD)
	iso_manager = Node3D.new()
	iso_manager.name = "ISOManager"
	iso_manager.set_script(load("res://scripts/world/iso_manager.gd"))
	add_child(iso_manager)
	# Connecter le loader d'animations au manager
	iso_manager.set_animation_loader(iso_anim_loader)

	# Super-entites (Minerve, Tron, Symmetra)
	entity_renderer = Node3D.new()
	entity_renderer.name = "EntityRenderer"
	entity_renderer.set_script(load("res://scripts/world/entity_renderer.gd"))
	add_child(entity_renderer)

	# Structures (batiments + lightways)
	structure_manager = Node3D.new()
	structure_manager.name = "StructureManager"
	structure_manager.set_script(load("res://scripts/world/structure_manager.gd"))
	add_child(structure_manager)

	# Signaux de communication
	signal_renderer = Node3D.new()
	signal_renderer.name = "SignalRenderer"
	signal_renderer.set_script(load("res://scripts/world/signal_renderer.gd"))
	add_child(signal_renderer)

	# Vehicle Renderer (Lightcycles avec trails lumineux)
	vehicle_renderer = Node3D.new()
	vehicle_renderer.name = "VehicleRenderer"
	vehicle_renderer.set_script(load("res://scripts/world/vehicle_renderer.gd"))
	add_child(vehicle_renderer)

	# City Renderer (routes, zones, eclairage urbain, reseau)
	city_renderer = Node3D.new()
	city_renderer.name = "CityRenderer"
	city_renderer.set_script(load("res://scripts/world/city_renderer.gd"))
	add_child(city_renderer)

	# Energy Flow Renderer (flux d'energie animes entre zones)
	energy_flow = Node3D.new()
	energy_flow.name = "EnergyFlowRenderer"
	energy_flow.set_script(load("res://scripts/world/energy_flow_renderer.gd"))
	add_child(energy_flow)

	# HUD (UI overlay -- Sims 4 style)
	hud = CanvasLayer.new()
	hud.name = "HUD"
	hud.set_script(load("res://scripts/ui/hud.gd"))
	add_child(hud)

	# Mod Manager (panneau plein ecran)
	mod_manager = CanvasLayer.new()
	mod_manager.name = "ModManager"
	mod_manager.set_script(load("res://scripts/ui/mod_manager.gd"))
	add_child(mod_manager)

	# Terminal Daedalus (interface flottante style Claude Code)
	daedalus_terminal = CanvasLayer.new()
	daedalus_terminal.name = "DaedalusTerminal"
	daedalus_terminal.set_script(load("res://scripts/ui/daedalus_terminal.gd"))
	add_child(daedalus_terminal)
	if daedalus_terminal.has_method("set_ws_client"):
		daedalus_terminal.set_ws_client(ws_client)


# ==================================================================
#  RECEPTION DES DONNEES
# ==================================================================

func _on_state_received(state: Dictionary) -> void:
	last_state = state
	_frame_count += 1

	# Debug : afficher les cles recues pour diagnostiquer
	if _frame_count == 1:
		print("")
		print("======================================================")
		print("[STATE] PREMIERE RECEPTION DE DONNEES DU BACKEND")
		print("[STATE] Cles recues: ", state.keys())
		var isos_check = state.get("isos", [])
		var iso_count: int = isos_check.size() if isos_check is Array else 0
		print("[STATE] Nombre d'ISOs recus: ", iso_count)
		if iso_count > 0 and isos_check is Array:
			var first: Dictionary = isos_check[0]
			print("[STATE] Premier ISO: id=%s x=%s z=%s energy=%s" % [
				first.get("id", "?"), first.get("x", "?"), first.get("z", "?"), first.get("energy", "?")])
		if state.has("error"):
			print("[STATE] !!! ERREUR BACKEND: ", state.get("error", ""))
		if state.has("minerve"):
			print("[STATE] Minerve present, enabled=", state["minerve"].get("enabled", "???"))
		else:
			print("[STATE] Minerve ABSENT du state")
		if state.has("tron"):
			print("[STATE] Tron present, enabled=", state["tron"].get("enabled", "???"))
		else:
			print("[STATE] Tron ABSENT du state")
		if state.has("daedalus"):
			print("[STATE] Daedalus present, enabled=", state["daedalus"].get("enabled", "???"))
		else:
			print("[STATE] Daedalus ABSENT du state")
		var time_check: Dictionary = state.get("time", {})
		print("[STATE] Temps: cycles=%s formatted=%s" % [
			time_check.get("cycles", "?"), time_check.get("virtual_formatted", "?")])
		print("======================================================")
		print("")
	# Log periodique toutes les 100 frames
	if _frame_count % 100 == 0 and _frame_count > 1:
		var isos_arr = state.get("isos", [])
		var pop_data: Dictionary = state.get("population", {})
		print("[STATE] Frame %d | ISOs: %d | Alive: %s | Cycle: %s" % [
			_frame_count,
			isos_arr.size() if isos_arr is Array else 0,
			pop_data.get("alive", "?"),
			state.get("time", {}).get("cycles", "?")])

	# Positions des entites pour effets de proximite
	var minerve_pos: Dictionary = state.get("minerve", {})
	var tron_pos: Dictionary = state.get("tron", {})

	# Update ISOs (passer position camera pour le LOD animation)
	var isos: Array = state.get("isos", [])
	if camera_rig and camera_rig.has_method("get_camera_position"):
		iso_manager.update_camera_pos(camera_rig.get_camera_position())
	elif camera_rig:
		iso_manager.update_camera_pos(camera_rig.global_position)
	if iso_manager.has_method("update_isos"):
		iso_manager.update_isos(isos, minerve_pos, tron_pos)

	# Update Energy Map (pas a chaque frame pour la perf)
	var energy_map: Array = state.get("energy_map", [])
	if _frame_count % 3 == 0:
		if grid_visual.has_method("update_energy"):
			grid_visual.update_energy(energy_map)

	# Update Energy Flows (flux animes entre zones haute-energie)
	if energy_flow and energy_flow.has_method("update_data"):
		var sym_structs: Array = state.get("symmetra", {}).get("structures", [])
		energy_flow.update_data(energy_map, isos, sym_structs)

	# Update entites
	if entity_renderer.has_method("update_minerve"):
		entity_renderer.update_minerve(minerve_pos)
	if entity_renderer.has_method("update_tron"):
		entity_renderer.update_tron(tron_pos)
	var sym_data: Dictionary = state.get("symmetra", {})
	if entity_renderer.has_method("update_symmetra"):
		entity_renderer.update_symmetra(sym_data)
	var daedalus_data: Dictionary = state.get("daedalus", {})
	if entity_renderer.has_method("update_daedalus"):
		entity_renderer.update_daedalus(daedalus_data)
	if daedalus_terminal and daedalus_terminal.has_method("update_from_state"):
		daedalus_terminal.update_from_state(daedalus_data)

	# Update structures
	var structures: Array = sym_data.get("structures", sym_data.get("shelters", []))
	if structure_manager.has_method("update_structures"):
		structure_manager.update_structures(structures)
	if _frame_count % 5 == 0:
		if structure_manager.has_method("update_lightways"):
			structure_manager.update_lightways(structures)

	# Update vehicules (Lightcycles)
	var vehicles: Array = state.get("vehicles", [])
	if vehicle_renderer.has_method("update_vehicles"):
		vehicle_renderer.update_vehicles(vehicles)

	# Update city (routes, zones, eclairage, reseau) -- pas a chaque frame
	if _frame_count % 5 == 0:
		if city_renderer.has_method("update_city"):
			city_renderer.update_city(sym_data)

	# Update signaux
	var signals_data: Array = state.get("signals", [])
	if signal_renderer.has_method("update_signals"):
		signal_renderer.update_signals(signals_data)

	# Update camera entity positions (pour teleport touches 1-5)
	if _frame_count % 10 == 0 and camera_rig.has_method("update_entity_positions"):
		camera_rig.update_entity_positions(minerve_pos, tron_pos, sym_data, daedalus_data, isos)

	# Update HUD
	if hud.has_method("update_from_state"):
		hud.update_from_state(state)


func _on_chat_response(data: Dictionary) -> void:
	if hud.has_method("show_chat_response"):
		hud.show_chat_response(data)
	# Router les reponses Daedalus vers le terminal
	if data.get("target", "") == "daedalus" and daedalus_terminal and daedalus_terminal.has_method("show_chat_response"):
		daedalus_terminal.show_chat_response(data.get("response", ""))


func _on_connection_changed(connected: bool) -> void:
	if connected:
		print("[NexOS] >>> BACKEND CONNECTE -- les donnees arrivent <<<")
	else:
		print("[NexOS] >>> BACKEND DECONNECTE -- pas de donnees <<<")
	if hud and hud.has_method("set_ws_connected"):
		hud.set_ws_connected(connected)


func _on_terrain_received(terrain_data: Dictionary) -> void:
	print("[NexOS] Terrain recu: res=%s grid=%s" % [
		terrain_data.get("resolution", "?"), terrain_data.get("grid_size", "?")])
	if grid_visual and grid_visual.has_method("update_terrain"):
		grid_visual.update_terrain(terrain_data)


# ==================================================================
#  INPUT GLOBAL
# ==================================================================

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("toggle_pause"):
		ws_client.send_pause()
	elif event.is_action_pressed("toggle_hud"):
		if hud:
			hud.visible = !hud.visible
	elif event is InputEventKey and event.pressed and event.keycode == KEY_P and event.shift_pressed:
		# Toggle post-processing (Shift+P)
		if _post_process_rect:
			_post_process_rect.visible = !_post_process_rect.visible
	elif event is InputEventKey and event.pressed and event.keycode == KEY_F5:
		# Ouvrir le gestionnaire de mods
		if mod_manager and mod_manager.has_method("open"):
			mod_manager.open(asset_loader)
	elif event is InputEventKey and event.pressed and event.keycode == KEY_F2:
		# Toggle terminal Daedalus (F2)
		if daedalus_terminal and daedalus_terminal.has_method("is_terminal_open"):
			if daedalus_terminal.is_terminal_open():
				daedalus_terminal._toggle_terminal()
			else:
				daedalus_terminal._open_terminal()
	elif event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		# ESC deselects or exits build mode
		if hud and hud.has_method("is_build_mode") and hud.is_build_mode():
			hud._toggle_build_mode()
		elif hud and hud.has_method("get_selected_iso_id") and hud.get_selected_iso_id() > 0:
			hud._deselect_iso()

	# Click-to-select ISO or place building
	elif event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_RIGHT:
		_handle_world_click(event.position)


func _handle_world_click(screen_pos: Vector2) -> void:
	"""Raycast from camera to ground plane for selection/building."""
	var cam := get_viewport().get_camera_3d()
	if not cam:
		return

	var from := cam.project_ray_origin(screen_pos)
	var dir := cam.project_ray_normal(screen_pos)

	# Intersect with ground plane (y=0)
	if abs(dir.y) < 0.001:
		return
	var t := -from.y / dir.y
	if t < 0:
		return
	var hit := from + dir * t
	var world_x := int(clampf(hit.x, 0, GRID_SIZE - 1))
	var world_z := int(clampf(hit.z, 0, GRID_SIZE - 1))

	# Build mode: place structure
	if hud and hud.has_method("is_build_mode") and hud.is_build_mode():
		if hud.has_method("place_structure_at"):
			hud.place_structure_at(world_x, world_z)
		return

	# Selection mode: find closest ISO
	var isos: Array = last_state.get("isos", [])
	var closest_id := -1
	var closest_dist := 15.0  # Max selection radius
	for iso_data in isos:
		var ix := float(iso_data.get("x", 0))
		var iz := float(iso_data.get("z", 0))
		var dist := sqrt((ix - world_x) ** 2 + (iz - world_z) ** 2)
		if dist < closest_dist:
			closest_dist = dist
			closest_id = int(iso_data.get("id", -1))

	if closest_id > 0 and hud and hud.has_method("select_iso"):
		hud.select_iso(closest_id)
