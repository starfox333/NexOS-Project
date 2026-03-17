extends CanvasLayer
## NexOS v5 -- HUD Sims 4 Style x Tron Aesthetic
## Top bar: resources + speed controls
## Bottom bar: selected ISO portrait + needs bars
## Build panel: structure catalog (right side)
## Chat: bottom right overlay
## Minimap: bottom left corner

var _ws_client: Node

# --- UI References ---
# Top bar
var _top_bar: PanelContainer
var _pop_label: Label
var _gen_label: Label
var _energy_label: Label
var _time_label: Label
var _speed_buttons: Array[Button] = []
var _pause_btn: Button

# Bottom bar (selected ISO)
var _bottom_bar: PanelContainer
var _bottom_content: HBoxContainer
var _portrait_panel: PanelContainer
var _portrait_icon: Label
var _iso_name_label: Label
var _iso_info_label: RichTextLabel
var _needs_container: VBoxContainer
var _need_bars: Dictionary = {}
var _mood_label: Label
var _action_label: Label

# Build mode
var _build_panel: PanelContainer
var _build_buttons: Array[Button] = []
var _build_mode := false
var _build_type := "shelter"
var _build_indicator: Label

# Chat
var _chat_panel: PanelContainer
var _chat_output: RichTextLabel
var _chat_input: LineEdit
var _chat_tabs: HBoxContainer
var _current_chat_target := "system"
var _chat_visible := true

# Minimap
var _minimap_panel: PanelContainer
var _minimap_rect: ColorRect

# State
var _selected_iso_id := -1
var _selected_iso_data: Dictionary = {}
var _current_speed := 1.0
var _paused := false
var _last_state: Dictionary = {}
var chat_focused := false
var _ws_connected := false
var _frames_received := 0
var _last_data_time := 0.0
var _conn_label: Label

# === COULEURS TRON ===
const C_CYAN := Color(0.0, 1.0, 0.835)
const C_GOLD := Color(1.0, 0.843, 0.0)
const C_MAGENTA := Color(1.0, 0.267, 1.0)
const C_ORANGE := Color(1.0, 0.533, 0.0)
const C_GREEN := Color(0.0, 1.0, 0.533)
const C_BLUE := Color(0.267, 0.533, 1.0)
const C_RED := Color(1.0, 0.2, 0.2)
const C_BG := Color(0.0, 0.015, 0.03, 0.92)
const C_PANEL := Color(0.0, 0.03, 0.05, 0.95)
const C_BORDER := Color(0.0, 0.6, 0.5, 0.8)
const C_DARK := Color(0.0, 0.02, 0.04, 0.98)
const C_HOVER := Color(0.0, 0.15, 0.12, 0.95)

# Needs colors (Sims 4 inspired)
const NEED_COLORS := {
	'hunger': Color(0.2, 1.0, 0.4),     # Green
	'social': Color(0.3, 0.7, 1.0),     # Blue
	'fun': Color(1.0, 0.5, 0.8),        # Pink
	'comfort': Color(0.9, 0.7, 0.2),    # Gold
	'hygiene': Color(0.4, 0.9, 0.9),    # Cyan
}

const NEED_ICONS := {
	'hunger': "FAIM",
	'social': "SOCIAL",
	'fun': "FUN",
	'comfort': "CONFORT",
	'hygiene': "HYGIENE",
}

const MOOD_EMOTES := {
	'happy': "[color=#00ff88]HEUREUX[/color]",
	'neutral': "[color=#00ffd5]NEUTRE[/color]",
	'sad': "[color=#ff8800]TRISTE[/color]",
	'miserable': "[color=#ff3333]MISERABLE[/color]",
}


func _ready() -> void:
	layer = 5
	_build_top_bar()
	_build_bottom_bar()
	_build_build_panel()
	_build_chat_panel()
	_build_minimap()
	_build_mode_indicator()

	await get_tree().process_frame
	_ws_client = get_node_or_null("/root/NexOS/WSClient")


# ================================================================
#  STYLES HELPERS
# ================================================================

func _make_panel_style(bg: Color = C_PANEL, border: Color = C_BORDER, bw: int = 1, radius: int = 6) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	# Fond semi-transparent (voit le 3D derriere)
	s.bg_color = Color(bg.r, bg.g, bg.b, minf(bg.a, 0.88))
	s.border_color = border
	s.border_width_left = bw
	s.border_width_top = bw
	s.border_width_right = bw
	s.border_width_bottom = bw
	s.corner_radius_top_left = radius
	s.corner_radius_top_right = radius
	s.corner_radius_bottom_left = radius
	s.corner_radius_bottom_right = radius
	s.content_margin_left = 10.0
	s.content_margin_right = 10.0
	s.content_margin_top = 6.0
	s.content_margin_bottom = 6.0
	# Ombre portee subtile
	s.shadow_color = Color(0, 0, 0, 0.4)
	s.shadow_offset = Vector2(2, 2)
	s.shadow_size = 4
	return s


func _make_button(text: String, color: Color, min_w: float = 80, font_size: int = 18) -> Button:
	var btn := Button.new()
	btn.text = text
	btn.custom_minimum_size = Vector2(min_w, 42)
	btn.add_theme_font_size_override("font_size", font_size)
	btn.add_theme_color_override("font_color", color)
	btn.add_theme_color_override("font_hover_color", Color.WHITE)
	# Normal : fond sombre, accent bottom-border seulement
	var normal := StyleBoxFlat.new()
	normal.bg_color = C_DARK
	normal.border_color = color.darkened(0.3)
	normal.border_width_bottom = 2
	normal.border_width_left = 0
	normal.border_width_right = 0
	normal.border_width_top = 0
	normal.corner_radius_top_left = 4
	normal.corner_radius_top_right = 4
	normal.corner_radius_bottom_left = 4
	normal.corner_radius_bottom_right = 4
	normal.content_margin_left = 8.0
	normal.content_margin_right = 8.0
	normal.content_margin_top = 4.0
	normal.content_margin_bottom = 4.0
	# Hover : bg eclairci + border complete
	var hover := StyleBoxFlat.new()
	hover.bg_color = Color(C_HOVER.r, C_HOVER.g, C_HOVER.b, 0.9)
	hover.border_color = color
	hover.border_width_left = 1
	hover.border_width_top = 1
	hover.border_width_right = 1
	hover.border_width_bottom = 2
	hover.corner_radius_top_left = 4
	hover.corner_radius_top_right = 4
	hover.corner_radius_bottom_left = 4
	hover.corner_radius_bottom_right = 4
	hover.content_margin_left = 8.0
	hover.content_margin_right = 8.0
	hover.content_margin_top = 4.0
	hover.content_margin_bottom = 4.0
	# Pressed : bg plus sombre + border vive
	var pressed := StyleBoxFlat.new()
	pressed.bg_color = color.darkened(0.7)
	pressed.border_color = color.lightened(0.2)
	pressed.border_width_left = 1
	pressed.border_width_top = 1
	pressed.border_width_right = 1
	pressed.border_width_bottom = 2
	pressed.corner_radius_top_left = 4
	pressed.corner_radius_top_right = 4
	pressed.corner_radius_bottom_left = 4
	pressed.corner_radius_bottom_right = 4
	pressed.content_margin_left = 8.0
	pressed.content_margin_right = 8.0
	pressed.content_margin_top = 4.0
	pressed.content_margin_bottom = 4.0
	btn.add_theme_stylebox_override("normal", normal)
	btn.add_theme_stylebox_override("hover", hover)
	btn.add_theme_stylebox_override("pressed", pressed)
	btn.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	return btn


# ================================================================
#  TOP BAR -- Resources + Speed Controls (Sims 4 style)
# ================================================================

func _build_top_bar() -> void:
	_top_bar = PanelContainer.new()
	_top_bar.name = "TopBar"
	_top_bar.add_theme_stylebox_override("panel", _make_panel_style(C_DARK, C_BORDER, 1, 0))
	_top_bar.set_anchors_preset(Control.PRESET_TOP_WIDE)
	_top_bar.size = Vector2(0, 70)
	add_child(_top_bar)

	var hbox := HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 20)
	hbox.alignment = BoxContainer.ALIGNMENT_CENTER
	_top_bar.add_child(hbox)

	# === LEFT: Logo ===
	var logo := Label.new()
	logo.text = "NexOS"
	logo.add_theme_font_size_override("font_size", 36)
	logo.add_theme_color_override("font_color", C_CYAN)
	hbox.add_child(logo)

	# Separator
	var sep1 := VSeparator.new()
	sep1.add_theme_constant_override("separation", 2)
	sep1.add_theme_color_override("separator", C_BORDER)
	hbox.add_child(sep1)

	# === POPULATION ===
	_pop_label = Label.new()
	_pop_label.text = "POP: 0"
	_pop_label.add_theme_font_size_override("font_size", 28)
	_pop_label.add_theme_color_override("font_color", C_CYAN)
	hbox.add_child(_pop_label)

	# === GENERATION ===
	_gen_label = Label.new()
	_gen_label.text = "GEN: 0"
	_gen_label.add_theme_font_size_override("font_size", 28)
	_gen_label.add_theme_color_override("font_color", C_GOLD)
	hbox.add_child(_gen_label)

	# === ENERGY ===
	_energy_label = Label.new()
	_energy_label.text = "E: 0"
	_energy_label.add_theme_font_size_override("font_size", 28)
	_energy_label.add_theme_color_override("font_color", C_GREEN)
	hbox.add_child(_energy_label)

	# Separator
	var sep2 := VSeparator.new()
	hbox.add_child(sep2)

	# === SPEED CONTROLS (Sims 4 style) ===
	var speed_box := HBoxContainer.new()
	speed_box.add_theme_constant_override("separation", 4)
	hbox.add_child(speed_box)

	# Pause
	_pause_btn = _make_button("II", C_CYAN, 50, 18)
	_pause_btn.pressed.connect(_on_pause_pressed)
	speed_box.add_child(_pause_btn)

	# Speed 1x
	var s1 := _make_button(">", C_CYAN, 50, 18)
	s1.pressed.connect(func(): _set_speed(1.0))
	speed_box.add_child(s1)
	_speed_buttons.append(s1)

	# Speed 2x
	var s2 := _make_button(">>", C_ORANGE, 55, 18)
	s2.pressed.connect(func(): _set_speed(2.0))
	speed_box.add_child(s2)
	_speed_buttons.append(s2)

	# Speed 3x
	var s3 := _make_button(">>>", C_RED, 60, 18)
	s3.pressed.connect(func(): _set_speed(3.0))
	speed_box.add_child(s3)
	_speed_buttons.append(s3)

	# Separator
	var sep3 := VSeparator.new()
	hbox.add_child(sep3)

	# === TIME ===
	_time_label = Label.new()
	_time_label.text = "00:00:00"
	_time_label.add_theme_font_size_override("font_size", 30)
	_time_label.add_theme_color_override("font_color", C_GOLD)
	hbox.add_child(_time_label)

	# === CONNECTION STATUS ===
	_conn_label = Label.new()
	_conn_label.text = "DECONNECTE"
	_conn_label.add_theme_font_size_override("font_size", 22)
	_conn_label.add_theme_color_override("font_color", C_RED)
	hbox.add_child(_conn_label)

	# === BUILD MODE TOGGLE ===
	var sep4 := VSeparator.new()
	hbox.add_child(sep4)

	var build_btn := _make_button("BUILD", C_MAGENTA, 90, 17)
	build_btn.pressed.connect(_toggle_build_mode)
	hbox.add_child(build_btn)

	# === CHAT TOGGLE ===
	var chat_btn := _make_button("CHAT", C_CYAN, 80, 17)
	chat_btn.pressed.connect(func(): _chat_panel.visible = !_chat_panel.visible)
	hbox.add_child(chat_btn)

	# === MODS BUTTON ===
	var mods_btn := _make_button("MODS", C_GOLD, 80, 17)
	mods_btn.pressed.connect(_open_mod_manager)
	hbox.add_child(mods_btn)


# ================================================================
#  BOTTOM BAR -- Selected ISO (Sims 4 style plumbbob)
# ================================================================

func _build_bottom_bar() -> void:
	_bottom_bar = PanelContainer.new()
	_bottom_bar.name = "BottomBar"
	_bottom_bar.add_theme_stylebox_override("panel", _make_panel_style(C_DARK, C_BORDER, 2, 6))
	_bottom_bar.position = Vector2(250, 0)  # Will be repositioned in _process
	_bottom_bar.size = Vector2(900, 180)
	_bottom_bar.visible = false
	add_child(_bottom_bar)

	_bottom_content = HBoxContainer.new()
	_bottom_content.add_theme_constant_override("separation", 12)
	_bottom_bar.add_child(_bottom_content)

	# === LEFT: Portrait Panel ===
	_portrait_panel = PanelContainer.new()
	_portrait_panel.add_theme_stylebox_override("panel", _make_panel_style(C_DARK, C_CYAN, 2, 4))
	_portrait_panel.custom_minimum_size = Vector2(180, 180)
	_bottom_content.add_child(_portrait_panel)

	var portrait_vbox := VBoxContainer.new()
	portrait_vbox.alignment = BoxContainer.ALIGNMENT_CENTER
	_portrait_panel.add_child(portrait_vbox)

	_portrait_icon = Label.new()
	_portrait_icon.text = "ISO"
	_portrait_icon.add_theme_font_size_override("font_size", 48)
	_portrait_icon.add_theme_color_override("font_color", C_CYAN)
	_portrait_icon.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	portrait_vbox.add_child(_portrait_icon)

	_iso_name_label = Label.new()
	_iso_name_label.text = "ISO #0"
	_iso_name_label.add_theme_font_size_override("font_size", 22)
	_iso_name_label.add_theme_color_override("font_color", C_CYAN)
	_iso_name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	portrait_vbox.add_child(_iso_name_label)

	_mood_label = Label.new()
	_mood_label.text = ""
	_mood_label.add_theme_font_size_override("font_size", 20)
	_mood_label.add_theme_color_override("font_color", C_GREEN)
	_mood_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	portrait_vbox.add_child(_mood_label)

	# === CENTER: Needs Bars ===
	var center_vbox := VBoxContainer.new()
	center_vbox.custom_minimum_size = Vector2(500, 180)
	center_vbox.add_theme_constant_override("separation", 2)
	_bottom_content.add_child(center_vbox)

	_needs_container = VBoxContainer.new()
	_needs_container.add_theme_constant_override("separation", 3)
	center_vbox.add_child(_needs_container)

	# Create need bars
	for need_key in ['hunger', 'social', 'fun', 'comfort', 'hygiene']:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 8)
		_needs_container.add_child(row)

		var lbl := Label.new()
		lbl.text = NEED_ICONS[need_key]
		lbl.custom_minimum_size = Vector2(100, 0)
		lbl.add_theme_font_size_override("font_size", 20)
		lbl.add_theme_color_override("font_color", NEED_COLORS[need_key])
		row.add_child(lbl)

		# Progress bar -- fins, arrondis, style moderne
		var bar := ProgressBar.new()
		bar.custom_minimum_size = Vector2(320, 20)
		bar.max_value = 100.0
		bar.value = 50.0
		bar.show_percentage = false
		var bg_style := StyleBoxFlat.new()
		bg_style.bg_color = Color(0.02, 0.04, 0.06, 0.8)
		bg_style.border_color = NEED_COLORS[need_key].darkened(0.6)
		bg_style.border_width_bottom = 1
		bg_style.corner_radius_top_left = 4
		bg_style.corner_radius_top_right = 4
		bg_style.corner_radius_bottom_left = 4
		bg_style.corner_radius_bottom_right = 4
		bar.add_theme_stylebox_override("background", bg_style)
		var fill_style := StyleBoxFlat.new()
		fill_style.bg_color = NEED_COLORS[need_key].darkened(0.1)
		fill_style.corner_radius_top_left = 4
		fill_style.corner_radius_top_right = 4
		fill_style.corner_radius_bottom_left = 4
		fill_style.corner_radius_bottom_right = 4
		bar.add_theme_stylebox_override("fill", fill_style)
		row.add_child(bar)

		var val_lbl := Label.new()
		val_lbl.text = "50"
		val_lbl.custom_minimum_size = Vector2(50, 0)
		val_lbl.add_theme_font_size_override("font_size", 20)
		val_lbl.add_theme_color_override("font_color", Color(0.5, 0.7, 0.8))
		row.add_child(val_lbl)

		_need_bars[need_key] = {'bar': bar, 'label': val_lbl}

	# === RIGHT: Info + Action ===
	var right_vbox := VBoxContainer.new()
	right_vbox.custom_minimum_size = Vector2(300, 180)
	right_vbox.add_theme_constant_override("separation", 4)
	_bottom_content.add_child(right_vbox)

	_iso_info_label = RichTextLabel.new()
	_iso_info_label.bbcode_enabled = true
	_iso_info_label.custom_minimum_size = Vector2(290, 110)
	_iso_info_label.add_theme_font_size_override("normal_font_size", 20)
	_iso_info_label.add_theme_color_override("default_color", Color(0.5, 0.8, 0.7))
	right_vbox.add_child(_iso_info_label)

	_action_label = Label.new()
	_action_label.text = ""
	_action_label.add_theme_font_size_override("font_size", 18)
	_action_label.add_theme_color_override("font_color", C_ORANGE)
	right_vbox.add_child(_action_label)

	# Close button
	var close_btn := _make_button("X", C_RED, 28, 12)
	close_btn.pressed.connect(func(): _deselect_iso())
	right_vbox.add_child(close_btn)


# ================================================================
#  BUILD MODE PANEL (Right side -- Sims 4 catalog)
# ================================================================

func _build_build_panel() -> void:
	_build_panel = PanelContainer.new()
	_build_panel.name = "BuildPanel"
	_build_panel.add_theme_stylebox_override("panel", _make_panel_style(C_DARK, C_MAGENTA, 2, 6))
	_build_panel.size = Vector2(220, 380)
	_build_panel.visible = false
	add_child(_build_panel)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 8)
	_build_panel.add_child(vbox)

	# Title
	var title := Label.new()
	title.text = "MODE CONSTRUCTION"
	title.add_theme_font_size_override("font_size", 20)
	title.add_theme_color_override("font_color", C_MAGENTA)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(title)

	var sep := HSeparator.new()
	sep.add_theme_color_override("separator", C_MAGENTA.darkened(0.5))
	vbox.add_child(sep)

	# Structure buttons
	var struct_data := [
		['shelter', 'ABRI', C_MAGENTA, 'Zone protegee'],
		['library', 'BIBLIO', C_GOLD, 'Boost connaissance'],
		['energy_plant', 'CENTRALE', C_GREEN, 'Regen grille'],
		['comm_tower', 'TOUR COMM', C_BLUE, 'Signaux x2'],
		['arena', 'ARENE', C_ORANGE, 'Boost fitness'],
	]

	for data in struct_data:
		var btn_container := VBoxContainer.new()
		btn_container.add_theme_constant_override("separation", 2)
		vbox.add_child(btn_container)

		var btn := _make_button(data[1], data[2], 190, 14)
		var stype: String = data[0]
		btn.pressed.connect(func(): _select_build_type(stype))
		btn_container.add_child(btn)
		_build_buttons.append(btn)

		var desc := Label.new()
		desc.text = data[3]
		desc.add_theme_font_size_override("font_size", 14)
		desc.add_theme_color_override("font_color", Color(0.4, 0.5, 0.5))
		desc.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		btn_container.add_child(desc)

	# Cancel button
	var cancel := _make_button("ANNULER", C_RED, 190, 13)
	cancel.pressed.connect(func(): _toggle_build_mode())
	vbox.add_child(cancel)


func _build_mode_indicator() -> void:
	_build_indicator = Label.new()
	_build_indicator.text = ""
	_build_indicator.add_theme_font_size_override("font_size", 24)
	_build_indicator.add_theme_color_override("font_color", C_MAGENTA)
	_build_indicator.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_build_indicator.position = Vector2(800, 50)
	_build_indicator.visible = false
	add_child(_build_indicator)


# ================================================================
#  CHAT PANEL (Bottom right -- compact)
# ================================================================

func _build_chat_panel() -> void:
	_chat_panel = PanelContainer.new()
	_chat_panel.name = "ChatPanel"
	_chat_panel.add_theme_stylebox_override("panel", _make_panel_style(C_DARK, C_CYAN, 1, 4))
	_chat_panel.size = Vector2(450, 420)
	add_child(_chat_panel)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 4)
	_chat_panel.add_child(vbox)

	# Title
	var title_bar := HBoxContainer.new()
	vbox.add_child(title_bar)
	var title := Label.new()
	title.text = "CHAT IA"
	title.add_theme_font_size_override("font_size", 26)
	title.add_theme_color_override("font_color", C_CYAN)
	title_bar.add_child(title)

	# Tabs
	_chat_tabs = HBoxContainer.new()
	_chat_tabs.add_theme_constant_override("separation", 4)
	vbox.add_child(_chat_tabs)
	var targets := ["system", "minerve", "tron", "symmetra", "daedalus"]
	var tab_colors := [C_CYAN, C_GOLD, C_CYAN, C_MAGENTA, Color(0.615, 0.306, 0.918)]
	for i in range(targets.size()):
		var btn := _make_button(targets[i].to_upper(), tab_colors[i], 78, 13)
		var target: String = targets[i]
		btn.pressed.connect(func(): _set_chat_target(target))
		_chat_tabs.add_child(btn)

	# Output
	_chat_output = RichTextLabel.new()
	_chat_output.bbcode_enabled = true
	_chat_output.custom_minimum_size = Vector2(500, 300)
	_chat_output.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_chat_output.add_theme_font_size_override("normal_font_size", 20)
	_chat_output.add_theme_color_override("default_color", C_CYAN)
	_chat_output.scroll_following = true
	vbox.add_child(_chat_output)

	# Input -- style moderne avec placeholder dim
	_chat_input = LineEdit.new()
	_chat_input.placeholder_text = "Message..."
	_chat_input.custom_minimum_size = Vector2(500, 48)
	_chat_input.add_theme_font_size_override("font_size", 20)
	_chat_input.add_theme_color_override("font_placeholder_color", C_CYAN.darkened(0.5))
	# Bottom border accent
	var input_style := StyleBoxFlat.new()
	input_style.bg_color = Color(0.01, 0.02, 0.04, 0.9)
	input_style.border_color = C_CYAN.darkened(0.3)
	input_style.border_width_bottom = 2
	input_style.corner_radius_bottom_left = 4
	input_style.corner_radius_bottom_right = 4
	input_style.content_margin_left = 8.0
	input_style.content_margin_right = 8.0
	input_style.content_margin_top = 4.0
	input_style.content_margin_bottom = 4.0
	_chat_input.add_theme_stylebox_override("normal", input_style)
	var input_focus := input_style.duplicate()
	input_focus.border_color = C_CYAN
	input_focus.border_width_bottom = 2
	_chat_input.add_theme_stylebox_override("focus", input_focus)
	_chat_input.text_submitted.connect(_on_chat_submit)
	_chat_input.focus_entered.connect(func(): _set_camera_focus(true))
	_chat_input.focus_exited.connect(func(): _set_camera_focus(false))
	vbox.add_child(_chat_input)


# ================================================================
#  MINIMAP (Bottom left)
# ================================================================

func _build_minimap() -> void:
	_minimap_panel = PanelContainer.new()
	_minimap_panel.name = "Minimap"
	# Double border neon + fond tres sombre
	_minimap_panel.add_theme_stylebox_override("panel", _make_panel_style(Color(0.0, 0.01, 0.02, 0.95), C_CYAN.darkened(0.4), 2, 4))
	_minimap_panel.size = Vector2(220, 220)
	add_child(_minimap_panel)

	_minimap_rect = ColorRect.new()
	_minimap_rect.custom_minimum_size = Vector2(200, 200)
	_minimap_rect.color = Color(0.0, 0.015, 0.03)
	_minimap_panel.add_child(_minimap_rect)


# ================================================================
#  LAYOUT (responsive positioning)
# ================================================================

func _process(_delta: float) -> void:
	var vp := get_viewport()
	if not vp:
		return
	var screen := vp.get_visible_rect().size

	# Top bar -- full width
	if _top_bar:
		_top_bar.size.x = screen.x

	# Bottom bar -- center bottom
	if _bottom_bar and _bottom_bar.visible:
		_bottom_bar.position = Vector2(
			(screen.x - _bottom_bar.size.x) / 2.0,
			screen.y - _bottom_bar.size.y - 10
		)

	# Build panel -- right side
	if _build_panel:
		_build_panel.position = Vector2(
			screen.x - _build_panel.size.x - 10,
			60
		)

	# Chat panel -- bottom right
	if _chat_panel:
		_chat_panel.position = Vector2(
			screen.x - _chat_panel.size.x - 10,
			screen.y - _chat_panel.size.y - 10
		)
		# Move up if bottom bar is visible
		if _bottom_bar and _bottom_bar.visible:
			_chat_panel.position.y -= _bottom_bar.size.y + 5

	# Minimap -- bottom left
	if _minimap_panel:
		_minimap_panel.position = Vector2(
			10,
			screen.y - _minimap_panel.size.y - 10
		)

	# Build indicator
	if _build_indicator and _build_indicator.visible:
		_build_indicator.position.x = (screen.x - 300) / 2.0


# ================================================================
#  STATE UPDATE FROM WEBSOCKET
# ================================================================

func set_ws_connected(connected: bool) -> void:
	_ws_connected = connected
	if _conn_label:
		if connected:
			_conn_label.text = "CONNECTE"
			_conn_label.add_theme_color_override("font_color", C_GREEN)
		else:
			_conn_label.text = "DECONNECTE"
			_conn_label.add_theme_color_override("font_color", C_RED)


func update_from_state(state: Dictionary) -> void:
	_last_state = state
	_frames_received += 1
	_last_data_time = Time.get_ticks_msec() / 1000.0
	var pop: Dictionary = state.get("population", {})
	var time_data: Dictionary = state.get("time", {})
	var ctrl: Dictionary = state.get("control", {})

	# Update connection indicator with frame count
	if _conn_label and _ws_connected:
		var alive := int(pop.get("alive", 0))
		var cycles := int(time_data.get("cycles", 0))
		_conn_label.text = "LIVE [%d]" % cycles
		_conn_label.add_theme_color_override("font_color", C_GREEN)

	# Top bar stats
	if _pop_label:
		var alive := int(pop.get("alive", 0))
		_pop_label.text = "POP: %d" % alive
	if _gen_label:
		_gen_label.text = "GEN: %d" % int(pop.get("max_generation", 0))
	if _energy_label:
		_energy_label.text = "E: %.0f" % float(pop.get("avg_energy", 0))
	if _time_label:
		_time_label.text = time_data.get("virtual_formatted", "00:00:00")

	# Speed state
	_paused = ctrl.get("paused", false)
	_current_speed = float(ctrl.get("speed", 1.0))
	if _pause_btn:
		_pause_btn.text = ">" if _paused else "II"
		_pause_btn.add_theme_color_override("font_color", C_ORANGE if _paused else C_CYAN)

	# Update selected ISO from isos array
	if _selected_iso_id > 0:
		var isos: Array = state.get("isos", [])
		for iso_data in isos:
			if int(iso_data.get("id", -1)) == _selected_iso_id:
				_update_selected_iso(iso_data)
				break

	# Update minimap
	_update_minimap(state)


func _update_selected_iso(data: Dictionary) -> void:
	_selected_iso_data = data

	if _iso_name_label:
		_iso_name_label.text = "ISO #%d" % int(data.get("id", 0))

	if _mood_label:
		var mood_key: String = data.get("mood_label", "neutral")
		_mood_label.text = mood_key.to_upper()
		match mood_key:
			"happy": _mood_label.add_theme_color_override("font_color", C_GREEN)
			"neutral": _mood_label.add_theme_color_override("font_color", C_CYAN)
			"sad": _mood_label.add_theme_color_override("font_color", C_ORANGE)
			"miserable": _mood_label.add_theme_color_override("font_color", C_RED)

	# Update need bars
	var needs: Dictionary = data.get("needs", {})
	for key in _need_bars:
		if needs.has(key):
			var val: float = float(needs[key])
			var bar_data: Dictionary = _need_bars[key]
			var bar: ProgressBar = bar_data['bar']
			var lbl: Label = bar_data['label']
			bar.value = val
			lbl.text = "%d" % int(val)
			# Color the bar based on level
			var fill_style := bar.get_theme_stylebox("fill") as StyleBoxFlat
			if fill_style:
				if val > 60:
					fill_style.bg_color = NEED_COLORS[key]
				elif val > 30:
					fill_style.bg_color = C_ORANGE
				else:
					fill_style.bg_color = C_RED

	# Action
	if _action_label:
		var action: String = data.get("last_action", "idle")
		_action_label.text = action.to_upper().replace("_", " ")

	# Info
	if _iso_info_label:
		var age := int(data.get("age", 0))
		var gen := int(data.get("generation", 0))
		var energy := float(data.get("energy", 0))
		var max_e := float(data.get("max_energy", 200))
		var children := int(data.get("children", 0))
		var harvested := float(data.get("total_harvested", 0))

		var text := ""
		text += "[color=#00ffd5]Energie:[/color] %.0f/%.0f\n" % [energy, max_e]
		text += "[color=#aabbcc]Age:[/color] %d cycles\n" % age
		text += "[color=#ffd700]Gen:[/color] %d\n" % gen
		text += "[color=#ff44ff]Enfants:[/color] %d\n" % children
		text += "[color=#00ff88]Recolte:[/color] %.0f" % harvested
		_iso_info_label.text = text

	# Portrait color based on mood
	if _portrait_panel:
		var mood_val := float(data.get("mood", 50))
		var border_color := C_CYAN
		if mood_val > 70:
			border_color = C_GREEN
		elif mood_val < 30:
			border_color = C_RED
		elif mood_val < 50:
			border_color = C_ORANGE
		var style := _portrait_panel.get_theme_stylebox("panel") as StyleBoxFlat
		if style:
			style.border_color = border_color


func _update_minimap(state: Dictionary) -> void:
	# Minimap is a simple visual indicator - just update color overlay
	if not _minimap_rect:
		return
	var pop: Dictionary = state.get("population", {})
	var alive := int(pop.get("alive", 0))
	var density := clampf(float(alive) / 500.0, 0.0, 1.0)
	_minimap_rect.color = Color(0.0, 0.03 + density * 0.1, 0.06 + density * 0.05)


# ================================================================
#  ISO SELECTION
# ================================================================

func select_iso(iso_id: int) -> void:
	_selected_iso_id = iso_id
	_bottom_bar.visible = true
	_portrait_icon.text = "#%d" % iso_id

	# Request detailed data
	if _ws_client and _ws_client.has_method("send_command"):
		_ws_client.send_command("select_iso", {"id": iso_id})


func _deselect_iso() -> void:
	_selected_iso_id = -1
	_bottom_bar.visible = false
	_selected_iso_data = {}


func get_selected_iso_id() -> int:
	return _selected_iso_id


# ================================================================
#  SPEED CONTROLS
# ================================================================

func _on_pause_pressed() -> void:
	if _ws_client and _ws_client.has_method("send_pause"):
		_ws_client.send_pause()


func _set_speed(speed: float) -> void:
	_current_speed = speed
	if _ws_client and _ws_client.has_method("send_speed"):
		_ws_client.send_speed(speed)

	# Highlight active speed button
	for i in range(_speed_buttons.size()):
		var btn := _speed_buttons[i]
		var target_speed := float(i + 1)
		if abs(speed - target_speed) < 0.1:
			btn.add_theme_color_override("font_color", Color.WHITE)
		else:
			var colors := [C_CYAN, C_ORANGE, C_RED]
			btn.add_theme_color_override("font_color", colors[i])


# ================================================================
#  BUILD MODE
# ================================================================

func _toggle_build_mode() -> void:
	_build_mode = !_build_mode
	_build_panel.visible = _build_mode
	_build_indicator.visible = _build_mode
	if _build_mode:
		_build_indicator.text = "CLICK POUR PLACER: %s" % _build_type.to_upper()
	else:
		_build_indicator.text = ""


func _select_build_type(stype: String) -> void:
	_build_type = stype
	_build_indicator.text = "CLICK POUR PLACER: %s" % stype.to_upper()


func is_build_mode() -> bool:
	return _build_mode


func get_build_type() -> String:
	return _build_type


func place_structure_at(world_x: int, world_z: int) -> void:
	"""Called by main.gd when clicking in build mode."""
	if _ws_client and _ws_client.has_method("send_command"):
		_ws_client.send_command("place_structure", {
			"structure_type": _build_type,
			"x": world_x,
			"z": world_z
		})


# ================================================================
#  CHAT
# ================================================================

func _set_chat_target(target: String) -> void:
	_current_chat_target = target
	_chat_input.placeholder_text = "Parler a %s..." % target.to_upper()


func _on_chat_submit(text: String) -> void:
	if text.strip_edges().is_empty():
		return
	_chat_input.clear()
	var color := _get_target_color(_current_chat_target)
	_chat_output.append_text("\n[color=#666666][VOUS][/color] %s" % text)
	if _ws_client and _ws_client.has_method("send_chat"):
		_ws_client.send_chat(_current_chat_target, text)


func show_chat_response(data: Dictionary) -> void:
	var response: String = data.get("response", "...")
	var target: String = data.get("target", "system")
	var color := _get_target_color(target)
	_chat_output.append_text("\n[color=%s][b][%s][/b][/color] %s" % [
		color, target.to_upper(), response
	])


func _get_target_color(target: String) -> String:
	match target:
		"minerve": return "#ffd700"
		"tron": return "#00e5ff"
		"symmetra": return "#ff44ff"
		_: return "#00ffd5"


# ================================================================
#  CONNECTION + CAMERA
# ================================================================

func set_connection_status(connected: bool) -> void:
	# Connection status shown in top bar via color
	pass


func _set_camera_focus(focused: bool) -> void:
	chat_focused = focused
	var cam_rig = get_node_or_null("/root/NexOS/CameraRig")
	if cam_rig:
		cam_rig.chat_focused = focused


func _open_mod_manager() -> void:
	var mm = get_node_or_null("/root/NexOS/ModManager")
	var al = get_node_or_null("/root/NexOS/AssetLoader")
	if mm and mm.has_method("open") and al:
		mm.open(al)
