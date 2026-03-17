shader_type spatial;
render_mode unshaded;

// Shader entite ameliore avec Fresnel, pulse et variation
uniform vec3 base_color : source_color = vec3(0.0, 1.0, 0.835);
uniform vec3 emission_color : source_color = vec3(0.0, 1.0, 0.835);
uniform float emission_energy : hint_range(0.0, 10.0) = 2.0;
uniform float fresnel_power : hint_range(0.5, 8.0) = 2.5;
uniform float fresnel_intensity : hint_range(0.0, 3.0) = 1.5;
uniform float pulse_speed : hint_range(0.0, 10.0) = 2.0;
uniform float pulse_amount : hint_range(0.0, 1.0) = 0.3;
uniform float alpha : hint_range(0.0, 1.0) = 0.9;
uniform float energy_ratio : hint_range(0.0, 1.0) = 1.0;

void fragment() {
	// Fresnel : contour lumineux
	float fresnel = pow(1.0 - abs(dot(NORMAL, VIEW)), fresnel_power);
	fresnel *= fresnel_intensity;

	// Pulse temporel
	float pulse = 1.0 + sin(TIME * pulse_speed) * pulse_amount;

	// Couleur dynamique selon l'energie
	vec3 color = base_color;
	if (energy_ratio < 0.4) {
		// Basse energie : rouge
		color = mix(vec3(1.0, 0.2, 0.2), base_color, energy_ratio / 0.4);
	} else if (energy_ratio < 0.7) {
		// Moyenne : orange vers base
		color = mix(vec3(1.0, 0.5, 0.0), base_color, (energy_ratio - 0.4) / 0.3);
	}

	// Composition
	vec3 final_color = color * emission_energy * pulse;
	final_color += emission_color * fresnel;

	ALBEDO = final_color;
	ALPHA = alpha;
}
