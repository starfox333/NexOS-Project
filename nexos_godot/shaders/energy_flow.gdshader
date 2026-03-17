shader_type spatial;
render_mode unshaded, cull_disabled, blend_add;

// Flux d'energie anime -- lignes de circuit entre zones haute-energie
uniform vec3 flow_color : source_color = vec3(0.0, 1.0, 0.6);
uniform float flow_speed = 2.0;
uniform float pulse_length = 0.12;
uniform float glow_intensity = 1.8;
uniform float phase_offset = 0.0;  // Decalage par ligne pour varier

void fragment() {
	// UV.x = progression le long de la ligne (0..1)
	float progress = UV.x + phase_offset;
	float t = fract(TIME * flow_speed - progress);

	// Pulse gaussien qui se deplace le long de la ligne
	float pulse = exp(-pow((t - 0.5) / pulse_length, 2.0));

	// Base glow + pulse bright
	float base = 0.12;
	float brightness = base + pulse * 0.88;

	ALBEDO = flow_color * brightness * glow_intensity;
	ALPHA = (0.15 + brightness * 0.85) * 0.7;
}
