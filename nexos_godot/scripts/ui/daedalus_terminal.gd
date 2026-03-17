extends CanvasLayer
## Terminal Daedalus -- Interface flottante style Claude Code
## Panneau draggable avec feed d'activite, stats temps reel, et chat.
## Couleur : violet #9d4edd / fond sombre

# Couleurs Daedalus
const COL_BG := Color(0.05, 0.05, 0.08, 0.95)
const COL_BG_DARK := Color(0.04, 0.03, 0.06, 0.98)
const COL_TITLEBAR := Color(0.1, 0.06, 0.15, 0.98)
const COL_PURPLE := Color(0.615, 0.306, 0.918)       # #9d4edd
const COL_PURPLE_DIM := Color(0.615, 0.306, 0.918, 0.4)
const COL_PURPLE_GLOW := Color(0.75, 0.5, 1.0)
const COL_TEXT := Color(0.72, 0.63, 0.83)             # Texte principal
const COL_TEXT_DIM := Color(0.55, 0.45, 0.65)         # Texte secondaire
const COL_TEXT_BRIGHT := Color(0.88, 0.82, 0.94)      # Texte lumineux
const COL_GREEN := Color(0.16, 0.78, 0.25)            # Dot actif
const COL_RED := Color(1.0, 0.37, 0.34)               # Dot fermer
const COL_YELLOW := Color(0.996, 0.737, 0.18)         # Dot minimiser
const COL_BORDER := Color(0.615, 0.306, 0.918, 0.25)

# Dimensions
const TERMINAL_W := 520.0
const TERMINAL_H := 400.0

# Nodes
var _panel: PanelContainer
var _feed: RichTextLabel
var _input: LineEdit
var _status_pos: Label
var _status_seekers: Label
var _status_inspired: Label
var _active_dot: ColorRect

# Etat
var _is_open := true
var _dragging := false
var _drag_offset := Vector2.ZERO
var _toggle_btn: Button
var _last_state: Dictionary = {}

# WebSocket client reference (set par main.gd)
var _ws_client: Node = null


func _ready() -> void:
	layer = 5  # Au dessus du HUD mais sous le post-process
	_build_ui()
	_build_toggle_button()


# ==================================================================
#  CONSTRUCTION UI
# ==================================================================

func _build_ui() -> void:
	# Panneau principal
	_panel = PanelContainer.new()
	_panel.name = "DaedalusPanel"
	_panel.custom_minimum_size = Vector2(TERMINAL_W, TERMINAL_H)
	_panel.size = Vector2(TERMINAL_W, TERMINAL_H)

	# Position en bas a droite
	var vp_size := get_viewport().get_visible_rect().size
	_panel.position = Vector2(vp_size.x - TERMINAL_W - 20, vp_size.y - TERMINAL_H - 50)

	# StyleBox fond
	var bg_style := StyleBoxFlat.new()
	bg_style.bg_color = COL_BG
	bg_style.border_color = COL_BORDER
	bg_style.set_border_width_all(1)
	bg_style.set_corner_radius_all(8)
	bg_style.shadow_color = Color(0.615, 0.306, 0.918, 0.12)
	bg_style.shadow_size = 20
	_panel.add_theme_stylebox_override("panel", bg_style)

	# Layout vertical
	var vbox := VBoxContainer.new()
	vbox.name = "VBox"
	_panel.add_child(vbox)

	# --- TITLEBAR ---
	_build_titlebar(vbox)

	# --- STATUS BAR ---
	_build_statusbar(vbox)

	# --- FEED (zone de log) ---
	_build_feed(vbox)

	# --- INPUT ROW ---
	_build_input(vbox)

	add_child(_panel)


func _build_titlebar(parent: VBoxContainer) -> void:
	var titlebar := HBoxContainer.new()
	titlebar.name = "Titlebar"
	titlebar.custom_minimum_size.y = 32

	var tb_style := StyleBoxFlat.new()
	tb_style.bg_color = COL_TITLEBAR
	tb_style.content_margin_left = 10
	tb_style.content_margin_right = 10
	tb_style.content_margin_top = 4
	tb_style.content_margin_bottom = 4
	tb_style.set_corner_radius_all(0)
	tb_style.corner_radius_top_left = 8
	tb_style.corner_radius_top_right = 8
	titlebar.add_theme_constant_override("separation", 6)

	# Utiliser un PanelContainer pour le fond
	var tb_panel := PanelContainer.new()
	tb_panel.name = "TitlebarPanel"
	tb_panel.custom_minimum_size.y = 32
	tb_panel.add_theme_stylebox_override("panel", tb_style)

	var tb_inner := HBoxContainer.new()
	tb_inner.add_theme_constant_override("separation", 6)
	tb_panel.add_child(tb_inner)

	# Traffic light dots
	var dots_box := HBoxContainer.new()
	dots_box.add_theme_constant_override("separation", 5)

	for col in [COL_RED, COL_YELLOW, COL_GREEN]:
		var dot := ColorRect.new()
		dot.custom_minimum_size = Vector2(10, 10)
		dot.size = Vector2(10, 10)
		dot.color = col
		dots_box.add_child(dot)

	tb_inner.add_child(dots_box)

	# Spacer
	var spacer1 := Control.new()
	spacer1.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tb_inner.add_child(spacer1)

	# Titre
	var title := Label.new()
	title.text = "  DAEDALUS v1.0"
	title.add_theme_color_override("font_color", COL_PURPLE_GLOW)
	title.add_theme_font_size_override("font_size", 12)
	tb_inner.add_child(title)

	# Spacer
	var spacer2 := Control.new()
	spacer2.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tb_inner.add_child(spacer2)

	# Bouton minimiser
	var min_btn := Button.new()
	min_btn.text = "-"
	min_btn.custom_minimum_size = Vector2(22, 22)
	var btn_style := StyleBoxFlat.new()
	btn_style.bg_color = Color(0.615, 0.306, 0.918, 0.1)
	btn_style.border_color = COL_PURPLE_DIM
	btn_style.set_border_width_all(1)
	btn_style.set_corner_radius_all(3)
	min_btn.add_theme_stylebox_override("normal", btn_style)
	min_btn.add_theme_stylebox_override("hover", btn_style)
	min_btn.add_theme_color_override("font_color", COL_PURPLE)
	min_btn.add_theme_font_size_override("font_size", 14)
	min_btn.pressed.connect(_toggle_terminal)
	tb_inner.add_child(min_btn)

	parent.add_child(tb_panel)

	# Drag sur le titlebar
	tb_panel.gui_input.connect(_on_titlebar_input)


func _build_statusbar(parent: VBoxContainer) -> void:
	var status := HBoxContainer.new()
	status.name = "StatusBar"
	status.add_theme_constant_override("separation", 12)

	var sb_style := StyleBoxFlat.new()
	sb_style.bg_color = Color(0.615, 0.306, 0.918, 0.03)
	sb_style.content_margin_left = 10
	sb_style.content_margin_top = 4
	sb_style.content_margin_bottom = 4
	sb_style.border_color = Color(0.615, 0.306, 0.918, 0.08)
	sb_style.border_width_bottom = 1

	var sb_panel := PanelContainer.new()
	sb_panel.add_theme_stylebox_override("panel", sb_style)

	var sb_inner := HBoxContainer.new()
	sb_inner.add_theme_constant_override("separation", 14)

	# Dot actif
	var dot_box := HBoxContainer.new()
	dot_box.add_theme_constant_override("separation", 4)
	_active_dot = ColorRect.new()
	_active_dot.custom_minimum_size = Vector2(6, 6)
	_active_dot.color = COL_GREEN
	dot_box.add_child(_active_dot)
	var actif_label := Label.new()
	actif_label.text = "ACTIF"
	actif_label.add_theme_color_override("font_color", COL_TEXT_DIM)
	actif_label.add_theme_font_size_override("font_size", 9)
	dot_box.add_child(actif_label)
	sb_inner.add_child(dot_box)

	# Position
	_status_pos = Label.new()
	_status_pos.text = "POS (250, 125)"
	_status_pos.add_theme_color_override("font_color", COL_TEXT_DIM)
	_status_pos.add_theme_font_size_override("font_size", 9)
	sb_inner.add_child(_status_pos)

	# Seekers
	_status_seekers = Label.new()
	_status_seekers.text = "0 explorateurs"
	_status_seekers.add_theme_color_override("font_color", COL_TEXT_DIM)
	_status_seekers.add_theme_font_size_override("font_size", 9)
	sb_inner.add_child(_status_seekers)

	# Inspires
	_status_inspired = Label.new()
	_status_inspired.text = "0 inspires"
	_status_inspired.add_theme_color_override("font_color", COL_TEXT_DIM)
	_status_inspired.add_theme_font_size_override("font_size", 9)
	sb_inner.add_child(_status_inspired)

	sb_panel.add_child(sb_inner)
	parent.add_child(sb_panel)


func _build_feed(parent: VBoxContainer) -> void:
	_feed = RichTextLabel.new()
	_feed.name = "Feed"
	_feed.bbcode_enabled = true
	_feed.scroll_following = true
	_feed.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_feed.custom_minimum_size.y = 200
	_feed.add_theme_color_override("default_color", COL_TEXT)
	_feed.add_theme_font_size_override("normal_font_size", 11)

	# Fond transparent
	var feed_style := StyleBoxFlat.new()
	feed_style.bg_color = Color(0, 0, 0, 0)
	feed_style.content_margin_left = 10
	feed_style.content_margin_right = 10
	feed_style.content_margin_top = 6
	feed_style.content_margin_bottom = 6
	_feed.add_theme_stylebox_override("normal", feed_style)

	parent.add_child(_feed)

	# Messages initiaux
	_log_system("Terminal Daedalus initialise.")
	_log_system("Catalyseur d'innovation en ligne.")


func _build_input(parent: VBoxContainer) -> void:
	var input_box := HBoxContainer.new()
	input_box.name = "InputRow"
	input_box.add_theme_constant_override("separation", 6)

	var ib_style := StyleBoxFlat.new()
	ib_style.bg_color = Color(0.615, 0.306, 0.918, 0.03)
	ib_style.content_margin_left = 10
	ib_style.content_margin_right = 10
	ib_style.content_margin_top = 6
	ib_style.content_margin_bottom = 6
	ib_style.border_color = Color(0.615, 0.306, 0.918, 0.12)
	ib_style.border_width_top = 1
	ib_style.set_corner_radius_all(0)
	ib_style.corner_radius_bottom_left = 8
	ib_style.corner_radius_bottom_right = 8

	var ib_panel := PanelContainer.new()
	ib_panel.add_theme_stylebox_override("panel", ib_style)

	var ib_inner := HBoxContainer.new()
	ib_inner.add_theme_constant_override("separation", 6)

	# Prompt
	var prompt := Label.new()
	prompt.text = "daedalus >"
	prompt.add_theme_color_override("font_color", COL_PURPLE)
	prompt.add_theme_font_size_override("font_size", 12)
	ib_inner.add_child(prompt)

	# Input
	_input = LineEdit.new()
	_input.placeholder_text = "Poser une question a Daedalus..."
	_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_input.add_theme_color_override("font_color", COL_TEXT_BRIGHT)
	_input.add_theme_color_override("font_placeholder_color", COL_PURPLE_DIM)
	_input.add_theme_color_override("caret_color", COL_PURPLE)
	_input.add_theme_font_size_override("font_size", 12)

	var input_style := StyleBoxFlat.new()
	input_style.bg_color = Color(0, 0, 0, 0)
	input_style.set_border_width_all(0)
	_input.add_theme_stylebox_override("normal", input_style)
	_input.add_theme_stylebox_override("focus", input_style)

	_input.text_submitted.connect(_on_input_submitted)
	_input.focus_entered.connect(func(): _set_camera_focus(true))
	_input.focus_exited.connect(func(): _set_camera_focus(false))
	ib_inner.add_child(_input)

	ib_panel.add_child(ib_inner)
	parent.add_child(ib_panel)


func _build_toggle_button() -> void:
	_toggle_btn = Button.new()
	_toggle_btn.name = "DaedalusToggle"
	_toggle_btn.text = "  DAEDALUS"
	_toggle_btn.visible = false

	var btn_style := StyleBoxFlat.new()
	btn_style.bg_color = Color(0.1, 0.06, 0.15, 0.95)
	btn_style.border_color = COL_PURPLE_DIM
	btn_style.set_border_width_all(1)
	btn_style.set_corner_radius_all(6)
	btn_style.content_margin_left = 12
	btn_style.content_margin_right = 12
	btn_style.content_margin_top = 4
	btn_style.content_margin_bottom = 4
	btn_style.shadow_color = Color(0.615, 0.306, 0.918, 0.1)
	btn_style.shadow_size = 10

	_toggle_btn.add_theme_stylebox_override("normal", btn_style)
	_toggle_btn.add_theme_stylebox_override("hover", btn_style)
	_toggle_btn.add_theme_color_override("font_color", COL_PURPLE)
	_toggle_btn.add_theme_font_size_override("font_size", 10)

	var vp_size := get_viewport().get_visible_rect().size
	_toggle_btn.position = Vector2(vp_size.x - 140, vp_size.y - 40)

	_toggle_btn.pressed.connect(_open_terminal)
	add_child(_toggle_btn)


# ==================================================================
#  INTERACTION
# ==================================================================

func _toggle_terminal() -> void:
	_is_open = false
	_panel.visible = false
	_toggle_btn.visible = true


func _open_terminal() -> void:
	_is_open = true
	_panel.visible = true
	_toggle_btn.visible = false


func is_terminal_open() -> bool:
	return _is_open


func _on_titlebar_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				_dragging = true
				_drag_offset = _panel.position - event.global_position
			else:
				_dragging = false
	elif event is InputEventMouseMotion and _dragging:
		_panel.position = event.global_position + _drag_offset


func _on_input_submitted(text: String) -> void:
	if text.strip_edges().is_empty():
		return
	_input.clear()

	# Afficher le message utilisateur
	_log_user(text)

	# Envoyer via WebSocket
	if _ws_client and _ws_client.has_method("send_chat"):
		_ws_client.send_chat("daedalus", text)
	else:
		_log_reply("(Pas de connexion au backend)")


func set_ws_client(client: Node) -> void:
	_ws_client = client


# ==================================================================
#  FEED -- LOGGING
# ==================================================================

func _log_system(text: String) -> void:
	_feed.append_text("[color=#%s][i][systeme] %s[/i][/color]\n" % [COL_TEXT_DIM.to_html(false), text])

func _log_action(text: String) -> void:
	_feed.append_text("[color=#%s]> %s[/color]\n" % [COL_TEXT.to_html(false), text])

func _log_inspire(text: String) -> void:
	_feed.append_text("[color=#%s]* %s[/color]\n" % [COL_PURPLE_GLOW.to_html(false), text])

func _log_move(text: String) -> void:
	_feed.append_text("[color=#%s]%s[/color]\n" % [COL_TEXT_DIM.to_html(false), text])

func _log_user(text: String) -> void:
	_feed.append_text("[color=#%s]vous > %s[/color]\n" % [COL_TEXT_BRIGHT.to_html(false), text])

func _log_reply(text: String) -> void:
	_feed.append_text("[color=#%s]daedalus > %s[/color]\n" % [COL_PURPLE.to_html(false), text])


# ==================================================================
#  MISE A JOUR DEPUIS L'ETAT
# ==================================================================

func update_from_state(daedalus_data: Dictionary) -> void:
	if daedalus_data.is_empty() or not daedalus_data.get("enabled", false):
		return

	# Status bar
	var x: int = int(daedalus_data.get("x", 250))
	var z: int = int(daedalus_data.get("z", 125))
	var seekers: int = int(daedalus_data.get("current_seekers", 0))
	var inspired: int = int(daedalus_data.get("total_inspired", 0))

	if _status_pos:
		_status_pos.text = "POS (%d, %d)" % [x, z]
	if _status_seekers:
		_status_seekers.text = "%d explorateurs" % seekers
	if _status_inspired:
		_status_inspired.text = "%d inspires" % inspired

	# Messages d'activite contextuels
	if not _last_state.is_empty():
		var prev_x: int = int(_last_state.get("x", 0))
		var prev_z: int = int(_last_state.get("z", 0))
		var prev_inspired: int = int(_last_state.get("total_inspired", 0))
		var prev_questions: int = int(_last_state.get("total_questions_asked", 0))

		# Deplacement significatif
		if abs(x - prev_x) > 8 or abs(z - prev_z) > 8:
			_log_move("Deplacement vers zone (%d, %d)" % [x, z])

		# Nouvelles inspirations
		var new_inspired: int = inspired - prev_inspired
		if new_inspired > 0 and seekers > 0:
			_log_inspire("%d ISOs dans le rayon -- curiosite stimulee (+%d)" % [seekers, new_inspired])

		# Nouvelles questions
		var curr_q: int = int(daedalus_data.get("total_questions_asked", 0))
		var new_q: int = curr_q - prev_questions
		var cycles: int = int(daedalus_data.get("cycles_active", 0))
		if new_q > 10 and cycles % 30 == 0:
			_log_action("%d nouvelles questions posees aux ISOs proches" % new_q)

		# Changement de cible
		var curr_target: Dictionary = daedalus_data.get("target", {})
		var prev_target: Dictionary = _last_state.get("target", {})
		if not curr_target.is_empty() and not prev_target.is_empty():
			if curr_target.get("x", 0) != prev_target.get("x", 0) or curr_target.get("z", 0) != prev_target.get("z", 0):
				_log_action("Nouvelle cible detectee : zone stagnante (%d, %d)" % [int(curr_target.get("x", 0)), int(curr_target.get("z", 0))])

		# Jalons
		if inspired >= 100 and prev_inspired < 100:
			_log_system("Jalon : 100 ISOs inspires !")
		if inspired >= 500 and prev_inspired < 500:
			_log_system("Jalon : 500 ISOs inspires !")
		if inspired >= 1000 and prev_inspired < 1000:
			_log_system("Jalon : 1000 ISOs inspires !")

	_last_state = daedalus_data.duplicate(true)


func show_chat_response(response: String) -> void:
	_log_reply(response)


# ==================================================================
#  INPUT -- Empecher la camera de bouger en tapant
# ==================================================================

func is_input_focused() -> bool:
	if _input and _input.has_focus():
		return true
	return false


func _set_camera_focus(focused: bool) -> void:
	var cam_rig = get_node_or_null("/root/NexOS/CameraRig")
	if cam_rig:
		cam_rig.chat_focused = focused
