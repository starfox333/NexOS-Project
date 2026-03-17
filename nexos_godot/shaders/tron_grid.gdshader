shader_type spatial;
render_mode unshaded, cull_disabled;

uniform vec4 line_color : source_color = vec4(0.0, 0.2, 0.13, 1.0);
uniform vec4 major_color : source_color = vec4(0.0, 0.4, 0.26, 1.0);
uniform vec4 bg_color : source_color = vec4(0.0, 0.015, 0.02, 1.0);
uniform float major_spacing = 50.0;
uniform float minor_spacing = 10.0;
uniform float major_width = 0.4;
uniform float minor_width = 0.12;
uniform float pulse_speed = 0.3;
uniform float pulse_intensity = 0.2;
uniform float grid_size = 500.0;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 pos = world_pos.xz;

	// Lignes mineures (tous les 10 units)
	vec2 minor_grid = abs(fract(pos / minor_spacing + 0.5) - 0.5) * minor_spacing;
	float minor_line = min(minor_grid.x, minor_grid.y);
	float minor_mask = 1.0 - smoothstep(minor_width * 0.5, minor_width, minor_line);

	// Lignes majeures (tous les 50 units)
	vec2 major_grid = abs(fract(pos / major_spacing + 0.5) - 0.5) * major_spacing;
	float major_line = min(major_grid.x, major_grid.y);
	float major_mask = 1.0 - smoothstep(major_width * 0.5, major_width, major_line);

	// Pulse qui se deplace sur la grille
	float wave = sin(TIME * pulse_speed + (pos.x + pos.y) * 0.008) * pulse_intensity;
	float radial_pulse = sin(TIME * 0.2 + length(pos - vec2(grid_size * 0.5)) * 0.02) * 0.1;
	float pulse = 1.0 + wave + radial_pulse;

	// Distance fade (bords de la grille)
	float edge_x = smoothstep(0.0, 30.0, pos.x) * smoothstep(grid_size, grid_size - 30.0, pos.x);
	float edge_z = smoothstep(0.0, 30.0, pos.y) * smoothstep(grid_size, grid_size - 30.0, pos.y);
	float edge_fade = edge_x * edge_z;

	// Combiner
	float combined_line = max(minor_mask * 0.35, major_mask * 0.7);
	combined_line *= edge_fade;

	vec3 line_col = mix(line_color.rgb, major_color.rgb, major_mask);
	ALBEDO = mix(bg_color.rgb, line_col * pulse, combined_line);
	EMISSION = line_col * combined_line * 0.4 * pulse;
	ALPHA = 0.92;
}
