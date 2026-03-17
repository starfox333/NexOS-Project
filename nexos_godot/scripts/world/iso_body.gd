extends RefCounted
## Generateur procedural de corps humanoides style Tron
## Cree un mesh unique combine (tete + torse + bras + jambes)
## Optimise pour MultiMeshInstance3D (1000+ instances)

## Trois variantes de corps pour varier les silhouettes
enum BodyType { STANDARD, SLIM, HEAVY }


static func create_humanoid_mesh(body_type: int = BodyType.STANDARD) -> ArrayMesh:
	"""Cree un mesh humanoide low-poly combine en un seul ArrayMesh."""
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)

	# Parametres selon le type de corps
	var torso_w: float  # largeur torse
	var torso_h: float  # hauteur torse
	var head_r: float   # rayon tete
	var arm_w: float    # largeur bras
	var leg_w: float    # largeur jambe

	match body_type:
		BodyType.SLIM:
			torso_w = 0.3
			torso_h = 0.7
			head_r = 0.14
			arm_w = 0.06
			leg_w = 0.07
		BodyType.HEAVY:
			torso_w = 0.5
			torso_h = 0.65
			head_r = 0.17
			arm_w = 0.1
			leg_w = 0.12
		_: # STANDARD
			torso_w = 0.38
			torso_h = 0.7
			head_r = 0.15
			arm_w = 0.07
			leg_w = 0.09

	# Offset pour centrer le mesh (pieds au sol = y=0, tete en haut)
	var total_h: float = torso_h + 0.7 + head_r * 2.0 + 0.05
	var base_y: float = -total_h * 0.3  # Centre de masse plus bas

	# ---- TETE (octahedron aplati -- style programme Tron) ----
	var head_y: float = base_y + torso_h + 0.7 + 0.05
	_add_octahedron(st, Vector3(0, head_y, 0), head_r, head_r * 1.1)

	# ---- TORSE (prisme octogonal -- corps geometrique Tron ameliore) ----
	var torso_y: float = base_y + 0.7  # base du torse
	_add_oct_prism(st, Vector3(0, torso_y + torso_h * 0.5, 0), torso_w, torso_h)

	# ---- BASSIN (prisme octogonal plus etroit) ----
	var pelvis_h: float = 0.2
	_add_oct_prism(st, Vector3(0, torso_y - pelvis_h * 0.5, 0), torso_w * 0.7, pelvis_h)

	# ---- EPAULES (octahedrons articulaires) ----
	var shoulder_x: float = torso_w + arm_w + 0.02
	var shoulder_y: float = torso_y + torso_h * 0.75
	_add_octahedron(st, Vector3(-shoulder_x, shoulder_y, 0), arm_w * 0.8, arm_w * 0.6)
	_add_octahedron(st, Vector3(shoulder_x, shoulder_y, 0), arm_w * 0.8, arm_w * 0.6)

	# ---- BRAS GAUCHE ----
	var arm_h: float = torso_h * 0.85
	_add_oct_prism(st, Vector3(-shoulder_x, torso_y + torso_h * 0.35, 0), arm_w, arm_h)

	# ---- BRAS DROIT ----
	_add_oct_prism(st, Vector3(shoulder_x, torso_y + torso_h * 0.35, 0), arm_w, arm_h)

	# ---- JAMBE GAUCHE ----
	var leg_h: float = 0.7
	var hip_x: float = torso_w * 0.4
	_add_oct_prism(st, Vector3(-hip_x, base_y + leg_h * 0.5, 0), leg_w, leg_h)

	# ---- JAMBE DROITE ----
	_add_oct_prism(st, Vector3(hip_x, base_y + leg_h * 0.5, 0), leg_w, leg_h)

	# ---- GENOUX (octahedrons articulaires) ----
	var knee_y: float = base_y + leg_h
	_add_octahedron(st, Vector3(-hip_x, knee_y, 0), leg_w * 0.7, leg_w * 0.5)
	_add_octahedron(st, Vector3(hip_x, knee_y, 0), leg_w * 0.7, leg_w * 0.5)

	# ---- CEINTURE LUMINEUSE (anneau fin a la taille) ----
	_add_belt_ring(st, Vector3(0, torso_y, 0), torso_w * 1.05, 0.02)

	# ---- LIGNES DE CIRCUIT (5 barres -- avant + laterales + dos) ----
	# Ligne centrale avant
	_add_thin_bar(st, Vector3(0, torso_y + torso_h * 0.5, torso_w * 0.98),
		0.015, torso_h * 0.9)
	# Lignes laterales avant
	_add_thin_bar(st, Vector3(-torso_w * 0.5, torso_y + torso_h * 0.5, torso_w * 0.85),
		0.012, torso_h * 0.7)
	_add_thin_bar(st, Vector3(torso_w * 0.5, torso_y + torso_h * 0.5, torso_w * 0.85),
		0.012, torso_h * 0.7)
	# Lignes dorsales
	_add_thin_bar(st, Vector3(-torso_w * 0.35, torso_y + torso_h * 0.5, -torso_w * 0.9),
		0.012, torso_h * 0.6)
	_add_thin_bar(st, Vector3(torso_w * 0.35, torso_y + torso_h * 0.5, -torso_w * 0.9),
		0.012, torso_h * 0.6)

	st.generate_normals()
	return st.commit()


static func _add_oct_prism(st: SurfaceTool, center: Vector3, radius: float, height: float) -> void:
	"""Ajoute un prisme octogonal (8 faces laterales + top + bottom) -- plus lisse que hex."""
	var top_y: float = center.y + height * 0.5
	var bot_y: float = center.y - height * 0.5
	var pts_top: Array[Vector3] = []
	var pts_bot: Array[Vector3] = []

	for i in range(8):
		var angle: float = float(i) / 8.0 * TAU
		var px: float = center.x + cos(angle) * radius
		var pz: float = center.z + sin(angle) * radius
		pts_top.append(Vector3(px, top_y, pz))
		pts_bot.append(Vector3(px, bot_y, pz))

	# Faces laterales (8 quads = 16 triangles)
	for i in range(8):
		var n: int = (i + 1) % 8
		st.add_vertex(pts_bot[i])
		st.add_vertex(pts_top[i])
		st.add_vertex(pts_top[n])
		st.add_vertex(pts_bot[i])
		st.add_vertex(pts_top[n])
		st.add_vertex(pts_bot[n])

	# Face du haut (fan triangulaire)
	var top_center := Vector3(center.x, top_y, center.z)
	for i in range(8):
		var n: int = (i + 1) % 8
		st.add_vertex(top_center)
		st.add_vertex(pts_top[i])
		st.add_vertex(pts_top[n])

	# Face du bas
	var bot_center := Vector3(center.x, bot_y, center.z)
	for i in range(8):
		var n: int = (i + 1) % 8
		st.add_vertex(bot_center)
		st.add_vertex(pts_bot[n])
		st.add_vertex(pts_bot[i])


static func _add_belt_ring(st: SurfaceTool, center: Vector3, radius: float, width: float) -> void:
	"""Ajoute un anneau fin horizontal (ceinture lumineuse)."""
	var inner_r: float = radius - width
	var outer_r: float = radius + width
	var y: float = center.y
	var segments := 8

	for i in range(segments):
		var a1: float = float(i) / float(segments) * TAU
		var a2: float = float(i + 1) / float(segments) * TAU
		var inner1 := Vector3(center.x + cos(a1) * inner_r, y, center.z + sin(a1) * inner_r)
		var inner2 := Vector3(center.x + cos(a2) * inner_r, y, center.z + sin(a2) * inner_r)
		var outer1 := Vector3(center.x + cos(a1) * outer_r, y, center.z + sin(a1) * outer_r)
		var outer2 := Vector3(center.x + cos(a2) * outer_r, y, center.z + sin(a2) * outer_r)
		# Quad (2 triangles)
		st.add_vertex(inner1)
		st.add_vertex(outer1)
		st.add_vertex(outer2)
		st.add_vertex(inner1)
		st.add_vertex(outer2)
		st.add_vertex(inner2)


static func _add_hex_prism(st: SurfaceTool, center: Vector3, radius: float, height: float) -> void:
	"""Ajoute un prisme hexagonal (6 faces + top + bottom)."""
	var top_y: float = center.y + height * 0.5
	var bot_y: float = center.y - height * 0.5
	var pts_top: Array[Vector3] = []
	var pts_bot: Array[Vector3] = []

	for i in range(6):
		var angle: float = float(i) / 6.0 * TAU
		var px: float = center.x + cos(angle) * radius
		var pz: float = center.z + sin(angle) * radius
		pts_top.append(Vector3(px, top_y, pz))
		pts_bot.append(Vector3(px, bot_y, pz))

	# Faces laterales (6 quads = 12 triangles)
	for i in range(6):
		var n: int = (i + 1) % 6
		# Triangle 1
		st.add_vertex(pts_bot[i])
		st.add_vertex(pts_top[i])
		st.add_vertex(pts_top[n])
		# Triangle 2
		st.add_vertex(pts_bot[i])
		st.add_vertex(pts_top[n])
		st.add_vertex(pts_bot[n])

	# Face du haut (fan triangulaire)
	var top_center := Vector3(center.x, top_y, center.z)
	for i in range(6):
		var n: int = (i + 1) % 6
		st.add_vertex(top_center)
		st.add_vertex(pts_top[i])
		st.add_vertex(pts_top[n])

	# Face du bas
	var bot_center := Vector3(center.x, bot_y, center.z)
	for i in range(6):
		var n: int = (i + 1) % 6
		st.add_vertex(bot_center)
		st.add_vertex(pts_bot[n])
		st.add_vertex(pts_bot[i])


static func _add_octahedron(st: SurfaceTool, center: Vector3, radius: float, height: float) -> void:
	"""Ajoute un octahedron (8 faces) pour la tete."""
	var top := center + Vector3(0, height, 0)
	var bot := center + Vector3(0, -height * 0.6, 0)
	var pts: Array[Vector3] = [
		center + Vector3(radius, 0, 0),
		center + Vector3(0, 0, radius),
		center + Vector3(-radius, 0, 0),
		center + Vector3(0, 0, -radius),
	]

	# 4 faces du haut
	for i in range(4):
		var n: int = (i + 1) % 4
		st.add_vertex(top)
		st.add_vertex(pts[i])
		st.add_vertex(pts[n])

	# 4 faces du bas
	for i in range(4):
		var n: int = (i + 1) % 4
		st.add_vertex(bot)
		st.add_vertex(pts[n])
		st.add_vertex(pts[i])


static func _add_thin_bar(st: SurfaceTool, center: Vector3, width: float, height: float) -> void:
	"""Ajoute une barre fine (circuit lumineux) -- quad vertical."""
	var hw: float = width * 0.5
	var hh: float = height * 0.5

	# Face avant
	var tl := center + Vector3(-hw, hh, 0)
	var tr := center + Vector3(hw, hh, 0)
	var bl := center + Vector3(-hw, -hh, 0)
	var br := center + Vector3(hw, -hh, 0)

	st.add_vertex(bl)
	st.add_vertex(tr)
	st.add_vertex(tl)

	st.add_vertex(bl)
	st.add_vertex(br)
	st.add_vertex(tr)
