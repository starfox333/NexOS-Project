shader_type spatial;
render_mode blend_mix, cull_disabled;

// Couleurs de la grille Tron
uniform vec3 line_color : source_color = vec3(0.0, 0.25, 0.16);
uniform vec3 major_color : source_color = vec3(0.0, 0.6, 0.4);
uniform vec3 pulse_color : source_color = vec3(0.0, 1.0, 0.835);
uniform vec3 bg_color : source_color = vec3(0.0, 0.012, 0.02);
uniform float grid_size = 5000.0;
uniform float time_scale = 1.0;

// Parametres de la grille
uniform float minor_spacing = 10.0;
uniform float major_spacing = 50.0;
uniform float line_width = 0.08;
uniform float major_line_width = 0.15;

// Pulse radial
uniform float pulse_speed = 0.3;
uniform float pulse_width = 30.0;
uniform float pulse_intensity = 0.6;

// Fresnel / bord
uniform float fresnel_power = 3.0;
uniform float fresnel_intensity = 0.4;

// === TERRAIN (Phase 1) ===
uniform sampler2D terrain_texture : filter_nearest, repeat_disable;
uniform bool terrain_enabled = false;
uniform float elevation_fertile = 3.5;
uniform float elevation_barren = -2.0;

// Couleurs terrain
uniform vec3 fertile_tint : source_color = vec3(0.0, 0.4, 0.15);
uniform vec3 barren_tint : source_color = vec3(0.4, 0.08, 0.0);

// === GLITCH (Phase 2) ===
uniform bool glitch_enabled = true;
uniform float glitch_intensity = 1.0;

varying vec3 world_pos;
varying vec3 world_normal;
varying float terrain_type;  // 0=plain, 1=fertile, 2=barren

// ---- Hash / noise helpers ----
float hash11(float p) {
	return fract(sin(p * 127.1) * 43758.5453);
}

float hash21(vec2 p) {
	return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

vec2 hash22(vec2 p) {
	return fract(sin(vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)))) * 43758.5453);
}

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_normal = (MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz;

	// === Elevation par terrain ===
	if (terrain_enabled) {
		vec2 terrain_uv = clamp(world_pos.xz / grid_size, 0.0, 1.0);
		float t_sample = texture(terrain_texture, terrain_uv).r;
		int t_id = int(t_sample * 255.0 + 0.5);
		terrain_type = float(t_id);

		float y_offset = 0.0;
		if (t_id == 1) {
			y_offset = elevation_fertile;
		} else if (t_id == 2) {
			y_offset = elevation_barren;
		}

		// Transition douce avec les voisins (moyenne 3x3)
		float pixel_size = 1.0 / textureSize(terrain_texture, 0).x;
		float sum_y = y_offset;
		float count = 1.0;
		for (int dx = -1; dx <= 1; dx++) {
			for (int dz = -1; dz <= 1; dz++) {
				if (dx == 0 && dz == 0) continue;
				vec2 neighbor_uv = terrain_uv + vec2(float(dx), float(dz)) * pixel_size;
				float n_sample = texture(terrain_texture, clamp(neighbor_uv, 0.0, 1.0)).r;
				int n_id = int(n_sample * 255.0 + 0.5);
				float n_y = 0.0;
				if (n_id == 1) n_y = elevation_fertile;
				else if (n_id == 2) n_y = elevation_barren;
				sum_y += n_y;
				count += 1.0;
			}
		}
		VERTEX.y += sum_y / count;
		world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	} else {
		terrain_type = 0.0;
	}
}

float grid_line(float coord, float spacing, float width) {
	float half_w = width * 0.5;
	float mod_val = mod(coord, spacing);
	float dist = min(mod_val, spacing - mod_val);
	return 1.0 - smoothstep(0.0, half_w, dist);
}

void fragment() {
	float t = TIME * time_scale;
	int t_id = int(terrain_type + 0.5);

	float wx = world_pos.x;
	float wz = world_pos.z;

	// === Glitch UV distorsion pour zones barren ===
	float glitch_offset_x = 0.0;
	float glitch_offset_z = 0.0;
	float barren_flicker = 1.0;
	float spark = 0.0;
	float broken_mask = 1.0;

	if (glitch_enabled && t_id == 2) {
		float gi = glitch_intensity;

		// Distorsion UV horizontale (scan glitch)
		float scan_line = floor(wz / 8.0);
		float scan_hash = hash11(scan_line + floor(t * 4.0) * 0.1);
		if (scan_hash > 0.85) {
			glitch_offset_x = (scan_hash - 0.85) * 40.0 * gi * sin(t * 12.0);
		}

		// Lignes cassees (segments manquants)
		vec2 cell_id = floor(world_pos.xz / minor_spacing);
		float break_hash = hash21(cell_id);
		if (break_hash > 0.6) {
			broken_mask = 0.0;  // Segment de ligne manquant
		}

		// Clignotement par blocs
		vec2 block_id = floor(world_pos.xz / 50.0);
		float flicker_hash = hash21(block_id + vec2(floor(t * 8.0), 0.0));
		barren_flicker = 0.5 + 0.5 * step(0.3, flicker_hash);

		// Sparks rares
		float spark_hash = hash21(floor(world_pos.xz / 30.0) + vec2(floor(t * 17.0)));
		spark = step(0.995, spark_hash) * 3.0;
	}

	// Coordonnees avec glitch offset
	float gx = wx + glitch_offset_x;
	float gz = wz + glitch_offset_z;

	// Lignes mineures
	float minor_x = grid_line(gx, minor_spacing, line_width);
	float minor_z = grid_line(gz, minor_spacing, line_width);
	float minor = max(minor_x, minor_z) * broken_mask;

	// Lignes majeures
	float major_x = grid_line(gx, major_spacing, major_line_width);
	float major_z = grid_line(gz, major_spacing, major_line_width);
	float major = max(major_x, major_z);  // Majeures pas cassees

	// Pulse radial depuis le centre
	float center_x = grid_size * 0.5;
	float center_z = grid_size * 0.5;
	float dist_from_center = length(vec2(wx - center_x, wz - center_z));
	float pulse_phase = dist_from_center - t * pulse_speed * grid_size;
	float pulse = exp(-pow(mod(pulse_phase, grid_size * 0.5) / pulse_width, 2.0));
	pulse *= pulse_intensity;

	// Second pulse
	float pulse2_phase = dist_from_center + t * pulse_speed * 0.7 * grid_size;
	float pulse2 = exp(-pow(mod(pulse2_phase, grid_size * 0.6) / (pulse_width * 1.5), 2.0));
	pulse2 *= pulse_intensity * 0.4;

	// Fresnel
	vec3 view_dir = normalize(CAMERA_POSITION_WORLD - world_pos);
	float fresnel = pow(1.0 - max(dot(normalize(world_normal), view_dir), 0.0), fresnel_power);
	fresnel *= fresnel_intensity;

	// === Couleurs par terrain ===
	vec3 base_line = line_color;
	vec3 base_major = major_color;
	vec3 base_pulse = pulse_color;
	float line_brightness = 1.0;

	if (terrain_enabled) {
		if (t_id == 1) {
			// FERTILE : lignes plus brillantes, teinte verte
			base_line = mix(line_color, fertile_tint, 0.3);
			base_major = mix(major_color, vec3(0.0, 1.0, 0.5), 0.25);
			base_pulse = mix(pulse_color, vec3(0.0, 1.0, 0.6), 0.2);
			line_brightness = 1.5;
		} else if (t_id == 2) {
			// BARREN : lignes sombres, teinte rouge/ambre
			base_line = mix(line_color, barren_tint, 0.5);
			base_major = mix(major_color, vec3(0.5, 0.15, 0.0), 0.4);
			base_pulse = mix(pulse_color, vec3(0.6, 0.1, 0.0), 0.3);
			line_brightness = 0.4;
		}
	}

	// Composition des couleurs
	vec3 color = bg_color;

	// Lignes mineures
	color = mix(color, base_line * line_brightness, minor * 0.7);

	// Lignes majeures
	color = mix(color, base_major * line_brightness, major);

	// Pulse sur les lignes
	float line_mask = max(minor, major);
	color += base_pulse * pulse * line_mask;
	color += base_pulse * pulse2 * line_mask * 0.5;

	// Pulse subtil hors lignes
	color += base_pulse * pulse * 0.03;

	// Fresnel edge
	color += base_pulse * fresnel * 0.15;

	// === Glitch effets couleur (barren) ===
	if (glitch_enabled && t_id == 2) {
		// Color fringing RGB
		float noise_r = hash21(world_pos.xz * 0.1 + vec2(t * 3.0, 0.0)) * 0.12;
		float noise_g = hash21(world_pos.xz * 0.1 + vec2(0.0, t * 5.0)) * 0.08;
		color.r += noise_r * glitch_intensity;
		color.g -= noise_g * glitch_intensity;

		// Appliquer flicker
		color *= barren_flicker;

		// Sparks
		color += vec3(spark) * pulse_color;
	}

	// Opacite
	float alpha = max(0.6, line_mask * 0.9 + fresnel * 0.3);

	// Fade aux bords de la grille
	float edge_fade = 1.0;
	float border = 15.0;
	edge_fade *= smoothstep(0.0, border, wx) * smoothstep(0.0, border, grid_size - wx);
	edge_fade *= smoothstep(0.0, border, wz) * smoothstep(0.0, border, grid_size - wz);
	alpha *= edge_fade;

	// Sol PBR
	ALBEDO = mix(vec3(0.01, 0.01, 0.02), color * 0.3, line_mask);
	METALLIC = 0.9;
	ROUGHNESS = mix(0.12, 0.4, line_mask);
	EMISSION = color;
	ALPHA = alpha;
}
