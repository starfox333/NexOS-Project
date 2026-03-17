shader_type spatial;
render_mode unshaded;

// Shader pour les aretes neon des batiments Tron
uniform vec4 neon_color : source_color = vec4(1.0, 0.27, 1.0, 1.0);
uniform float glow_intensity = 1.5;
uniform float pulse_speed = 2.0;
uniform float opacity = 0.8;
uniform float fresnel_power = 2.0;
uniform bool use_fresnel = true;
uniform bool animate = true;

void fragment() {
	float pulse = 1.0;
	if (animate) {
		pulse = 0.8 + sin(TIME * pulse_speed) * 0.2;
	}

	float fresnel = 1.0;
	if (use_fresnel) {
		fresnel = pow(1.0 - abs(dot(NORMAL, VIEW)), fresnel_power);
		fresnel = mix(0.3, 1.0, fresnel);
	}

	ALBEDO = neon_color.rgb * pulse;
	EMISSION = neon_color.rgb * glow_intensity * pulse * fresnel;
	ALPHA = opacity * fresnel;
}
