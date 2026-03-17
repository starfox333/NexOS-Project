shader_type spatial;
render_mode unshaded;

// Shader pour les ISOs -- couleur dynamique selon energie
uniform vec4 color_high : source_color = vec4(0.0, 1.0, 0.835, 1.0);   // cyan
uniform vec4 color_mid : source_color = vec4(1.0, 0.533, 0.0, 1.0);    // orange
uniform vec4 color_low : source_color = vec4(1.0, 0.267, 0.267, 1.0);  // rouge
uniform float energy_ratio = 1.0;
uniform float glow = 0.5;
uniform float pulse_speed = 3.0;

void fragment() {
	// Gradient de couleur selon l'energie
	vec3 col;
	if (energy_ratio > 0.7) {
		col = color_high.rgb;
	} else if (energy_ratio > 0.4) {
		float t = (energy_ratio - 0.4) / 0.3;
		col = mix(color_mid.rgb, color_high.rgb, t);
	} else {
		float t = energy_ratio / 0.4;
		col = mix(color_low.rgb, color_mid.rgb, t);
	}

	// Pulse subtil
	float pulse = 0.9 + sin(TIME * pulse_speed + VERTEX.y * 2.0) * 0.1;

	// Fresnel pour effet de bord lumineux
	float fresnel = pow(1.0 - abs(dot(NORMAL, VIEW)), 2.0);

	ALBEDO = col * pulse;
	EMISSION = col * (glow + fresnel * 0.3) * pulse;
	ALPHA = 0.85 + fresnel * 0.15;
}
