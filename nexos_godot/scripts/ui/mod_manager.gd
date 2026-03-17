extends CanvasLayer
## NexOS v5 -- Mod Manager UI (Sims 4 style)
## Panneau plein ecran pour gerer les mods installes
## Activer/desactiver, voir les details, compter les assets

var _panel: PanelContainer
var _mod_list: VBoxContainer
var _detail_panel: PanelContainer
var _detail_title: Label
var _detail_author: Label
var _detail_version: Label
var _detail_desc: RichTextLabel
var _detail_assets: Label
var _detail_toggle: Button
var _asset_loader: Node
var _selected_mod_id := ""
var _mod_entries: Dictionary = {}  # mod_id -> {panel, toggle_icon, name_label}

# === TRON COLORS ===
const C_CYAN := Color(0.0, 1.0, 0.835)
const C_GOLD := Color(1.0, 0.843, 0.0)
const C_MAGENTA := Color(1.0, 0.267, 1.0)
const C_GREEN := Color(0.0, 1.0, 0.533)
const C_RED := Color(1.0, 0.2, 0.2)
const C_BG := Color(0.0, 0.015, 0.025, 0.98)
const C_PANEL := Color(0.0, 0.025, 0.04, 0.95)
const C_BORDER := Color(0.0, 0.5, 0.4, 0.8)
const C_DARK := Color(0.0, 0.02, 0.04, 0.98)
const C_SELECTED := Color(0.0, 0.08, 0.06, 0.95)


func _ready() -> void:
	layer = 20  # Au dessus de tout
	visible = false
	_build_ui()


func open(loader: Node) -> void:
	"""Ouvre le mod manager avec reference au asset_loader."""
	_asset_loader = loader
	visible = true
	_refresh_mod_list()


func close() -> void:
	visible = false


# ================================================================
#  STYLES
# ================================================================

func _make_style(bg: Color, border: Color, bw: int = 1, radius: int = 4) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
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
	s.content_margin_top = 8.0
	s.content_margin_bottom = 8.0
	return s


func _make_btn(text: String, color: Color, min_w: float = 100) -> Button:
	var btn := Button.new()
	btn.text = text
	btn.custom_minimum_size = Vector2(min_w, 34)
	btn.add_theme_font_size_override("font_size", 13)
	btn.add_theme_color_override("font_color", color)
	btn.add_theme_color_override("font_hover_color", Color.WHITE)
	btn.add_theme_stylebox_override("normal", _make_style(C_DARK, color.darkened(0.4), 1, 3))
	btn.add_theme_stylebox_override("hover", _make_style(Color(0.0, 0.1, 0.08), color, 1, 3))
	btn.add_theme_stylebox_override("pressed", _make_style(color.darkened(0.7), color, 2, 3))
	btn.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	return btn


# ================================================================
#  BUILD UI
# ================================================================

func _build_ui() -> void:
	# Fond semi-transparent plein ecran
	var bg := ColorRect.new()
	bg.name = "ModalBG"
	bg.anchors_preset = Control.PRESET_FULL_RECT
	bg.color = Color(0, 0, 0, 0.7)
	bg.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(bg)

	# Main panel (centre)
	_panel = PanelContainer.new()
	_panel.name = "ModManagerPanel"
	_panel.add_theme_stylebox_override("panel", _make_style(C_BG, C_CYAN, 2, 8))
	_panel.set_anchors_preset(Control.PRESET_CENTER)
	_panel.custom_minimum_size = Vector2(900, 550)
	_panel.size = Vector2(900, 550)
	_panel.position = Vector2(-450, -275)
	add_child(_panel)

	var main_vbox := VBoxContainer.new()
	main_vbox.add_theme_constant_override("separation", 12)
	_panel.add_child(main_vbox)

	# === HEADER ===
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 20)
	main_vbox.add_child(header)

	var title := Label.new()
	title.text = "GESTIONNAIRE DE MODS"
	title.add_theme_font_size_override("font_size", 20)
	title.add_theme_color_override("font_color", C_CYAN)
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(title)

	var close_btn := _make_btn("FERMER", C_RED, 80)
	close_btn.pressed.connect(close)
	header.add_child(close_btn)

	# Separator
	var sep := HSeparator.new()
	sep.add_theme_constant_override("separation", 2)
	main_vbox.add_child(sep)

	# === CONTENT (mod list + detail panel) ===
	var content := HBoxContainer.new()
	content.add_theme_constant_override("separation", 12)
	content.size_flags_vertical = Control.SIZE_EXPAND_FILL
	main_vbox.add_child(content)

	# --- LEFT: Mod List ---
	var list_container := PanelContainer.new()
	list_container.add_theme_stylebox_override("panel", _make_style(C_DARK, C_BORDER, 1, 4))
	list_container.custom_minimum_size = Vector2(380, 0)
	list_container.size_flags_vertical = Control.SIZE_EXPAND_FILL
	content.add_child(list_container)

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	list_container.add_child(scroll)

	_mod_list = VBoxContainer.new()
	_mod_list.add_theme_constant_override("separation", 4)
	_mod_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(_mod_list)

	# --- RIGHT: Detail Panel ---
	_detail_panel = PanelContainer.new()
	_detail_panel.add_theme_stylebox_override("panel", _make_style(C_DARK, C_BORDER, 1, 4))
	_detail_panel.custom_minimum_size = Vector2(460, 0)
	_detail_panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_detail_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	content.add_child(_detail_panel)

	var detail_vbox := VBoxContainer.new()
	detail_vbox.add_theme_constant_override("separation", 10)
	_detail_panel.add_child(detail_vbox)

	_detail_title = Label.new()
	_detail_title.text = "Selectionnez un mod"
	_detail_title.add_theme_font_size_override("font_size", 18)
	_detail_title.add_theme_color_override("font_color", C_CYAN)
	detail_vbox.add_child(_detail_title)

	var info_grid := GridContainer.new()
	info_grid.columns = 2
	info_grid.add_theme_constant_override("h_separation", 15)
	info_grid.add_theme_constant_override("v_separation", 8)
	detail_vbox.add_child(info_grid)

	# Author
	var lbl_author := Label.new()
	lbl_author.text = "AUTEUR"
	lbl_author.add_theme_font_size_override("font_size", 12)
	lbl_author.add_theme_color_override("font_color", Color(0.4, 0.6, 0.5))
	info_grid.add_child(lbl_author)
	_detail_author = Label.new()
	_detail_author.text = "—"
	_detail_author.add_theme_font_size_override("font_size", 13)
	_detail_author.add_theme_color_override("font_color", C_GOLD)
	info_grid.add_child(_detail_author)

	# Version
	var lbl_ver := Label.new()
	lbl_ver.text = "VERSION"
	lbl_ver.add_theme_font_size_override("font_size", 12)
	lbl_ver.add_theme_color_override("font_color", Color(0.4, 0.6, 0.5))
	info_grid.add_child(lbl_ver)
	_detail_version = Label.new()
	_detail_version.text = "—"
	_detail_version.add_theme_font_size_override("font_size", 13)
	_detail_version.add_theme_color_override("font_color", Color(0.6, 0.8, 0.7))
	info_grid.add_child(_detail_version)

	# Assets
	var lbl_assets := Label.new()
	lbl_assets.text = "ASSETS"
	lbl_assets.add_theme_font_size_override("font_size", 12)
	lbl_assets.add_theme_color_override("font_color", Color(0.4, 0.6, 0.5))
	info_grid.add_child(lbl_assets)
	_detail_assets = Label.new()
	_detail_assets.text = "0 fichiers"
	_detail_assets.add_theme_font_size_override("font_size", 13)
	_detail_assets.add_theme_color_override("font_color", C_GREEN)
	info_grid.add_child(_detail_assets)

	# Description
	_detail_desc = RichTextLabel.new()
	_detail_desc.bbcode_enabled = true
	_detail_desc.custom_minimum_size = Vector2(420, 120)
	_detail_desc.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_detail_desc.add_theme_font_size_override("normal_font_size", 12)
	_detail_desc.add_theme_color_override("default_color", Color(0.5, 0.7, 0.6))
	detail_vbox.add_child(_detail_desc)

	# Toggle button
	_detail_toggle = _make_btn("ACTIVER / DESACTIVER", C_CYAN, 200)
	_detail_toggle.pressed.connect(_toggle_selected_mod)
	detail_vbox.add_child(_detail_toggle)

	# === FOOTER ===
	var footer := HBoxContainer.new()
	footer.add_theme_constant_override("separation", 12)
	footer.alignment = BoxContainer.ALIGNMENT_CENTER
	main_vbox.add_child(footer)

	var info_label := Label.new()
	info_label.text = "Placez vos mods dans le dossier mods/ — chaque mod = un dossier avec mod.json"
	info_label.add_theme_font_size_override("font_size", 11)
	info_label.add_theme_color_override("font_color", Color(0.3, 0.5, 0.4))
	footer.add_child(info_label)

	var folder_btn := _make_btn("OUVRIR DOSSIER MODS", C_GOLD, 170)
	folder_btn.pressed.connect(_open_mods_folder)
	footer.add_child(folder_btn)


# ================================================================
#  MOD LIST REFRESH
# ================================================================

func _refresh_mod_list() -> void:
	# Clear existing
	for child in _mod_list.get_children():
		child.queue_free()
	_mod_entries.clear()

	if not _asset_loader or not _asset_loader.has_method("get_mods"):
		return

	var mods: Array = _asset_loader.get_mods()

	if mods.is_empty():
		var empty := Label.new()
		empty.text = "Aucun mod installe\nPlacez un dossier dans mods/"
		empty.add_theme_font_size_override("font_size", 13)
		empty.add_theme_color_override("font_color", Color(0.4, 0.5, 0.5))
		empty.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		_mod_list.add_child(empty)
		return

	for mod in mods:
		_add_mod_entry(mod)


func _add_mod_entry(mod: Dictionary) -> void:
	var entry := PanelContainer.new()
	var is_enabled: bool = mod.get("enabled", true)
	var border_color := C_CYAN if is_enabled else Color(0.3, 0.3, 0.3)
	entry.add_theme_stylebox_override("panel", _make_style(C_DARK, border_color, 1, 3))
	entry.custom_minimum_size = Vector2(350, 50)
	_mod_list.add_child(entry)

	var hbox := HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 10)
	entry.add_child(hbox)

	# Toggle indicator
	var toggle_icon := Label.new()
	toggle_icon.text = "[ON]" if is_enabled else "[OFF]"
	toggle_icon.add_theme_font_size_override("font_size", 11)
	toggle_icon.add_theme_color_override("font_color", C_GREEN if is_enabled else C_RED)
	toggle_icon.custom_minimum_size = Vector2(40, 0)
	hbox.add_child(toggle_icon)

	# Mod info
	var info_vbox := VBoxContainer.new()
	info_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hbox.add_child(info_vbox)

	var name_label := Label.new()
	name_label.text = mod.get("name", "Mod inconnu")
	name_label.add_theme_font_size_override("font_size", 14)
	name_label.add_theme_color_override("font_color", C_CYAN if is_enabled else Color(0.4, 0.4, 0.4))
	info_vbox.add_child(name_label)

	var sub_label := Label.new()
	sub_label.text = "%s — %d assets" % [mod.get("author", "?"), int(mod.get("asset_count", 0))]
	sub_label.add_theme_font_size_override("font_size", 10)
	sub_label.add_theme_color_override("font_color", Color(0.4, 0.5, 0.5))
	info_vbox.add_child(sub_label)

	# Click to select
	var click_btn := Button.new()
	click_btn.flat = true
	click_btn.anchors_preset = Control.PRESET_FULL_RECT
	click_btn.mouse_filter = Control.MOUSE_FILTER_STOP
	click_btn.add_theme_stylebox_override("normal", StyleBoxEmpty.new())
	click_btn.add_theme_stylebox_override("hover", _make_style(Color(0, 0.06, 0.04, 0.5), C_CYAN.darkened(0.3), 1, 3))
	click_btn.add_theme_stylebox_override("pressed", StyleBoxEmpty.new())
	click_btn.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	var mod_id: String = mod.get("id", "")
	click_btn.pressed.connect(func(): _select_mod(mod_id))
	entry.add_child(click_btn)

	_mod_entries[mod.get("id", "")] = {
		"panel": entry,
		"toggle_icon": toggle_icon,
		"name_label": name_label,
	}


func _select_mod(mod_id: String) -> void:
	_selected_mod_id = mod_id
	if not _asset_loader:
		return

	var mods: Array = _asset_loader.get_mods()
	for mod in mods:
		if mod.get("id", "") == mod_id:
			_detail_title.text = mod.get("name", "?")
			_detail_author.text = mod.get("author", "Inconnu")
			_detail_version.text = "v%s" % mod.get("version", "1.0")
			_detail_assets.text = "%d fichiers" % int(mod.get("asset_count", 0))
			var desc: String = mod.get("description", "Aucune description")
			if desc.is_empty():
				desc = "Aucune description fournie."
			_detail_desc.text = "[color=#88aaaa]%s[/color]" % desc

			var is_enabled: bool = mod.get("enabled", true)
			_detail_toggle.text = "DESACTIVER" if is_enabled else "ACTIVER"
			_detail_toggle.add_theme_color_override("font_color", C_RED if is_enabled else C_GREEN)
			break

	# Highlight selected in list
	for entry_id in _mod_entries:
		var entry_data: Dictionary = _mod_entries[entry_id]
		var panel: PanelContainer = entry_data["panel"]
		if entry_id == mod_id:
			panel.add_theme_stylebox_override("panel", _make_style(C_SELECTED, C_CYAN, 2, 3))
		else:
			var enabled := true
			for m in mods:
				if m.get("id", "") == entry_id:
					enabled = m.get("enabled", true)
					break
			var bc := C_BORDER if enabled else Color(0.3, 0.3, 0.3)
			panel.add_theme_stylebox_override("panel", _make_style(C_DARK, bc, 1, 3))


func _toggle_selected_mod() -> void:
	if _selected_mod_id.is_empty() or not _asset_loader:
		return

	var mods: Array = _asset_loader.get_mods()
	for mod in mods:
		if mod.get("id", "") == _selected_mod_id:
			var new_state: bool = !mod.get("enabled", true)
			_asset_loader.set_mod_enabled(_selected_mod_id, new_state)
			_refresh_mod_list()
			_select_mod(_selected_mod_id)
			break


func _open_mods_folder() -> void:
	var path := ProjectSettings.globalize_path("res://mods/")
	OS.shell_open(path)


func _unhandled_input(event: InputEvent) -> void:
	if not visible:
		return
	if event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		close()
		get_viewport().set_input_as_handled()
