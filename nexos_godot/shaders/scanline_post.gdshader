shader_type canvas_item;
// Post-processing Tron : scanlines + vignette + aberration chromatique
// Compatible Godot 4.x (hint_screen_texture)

uniform sampler2D screen_texture : hint_screen_texture, repeat_disable, filter_linear;

uniform float scanline_opacity : hint_range(0.0, 1.0) = 0.06;
uniform float scanline_scale : hint_range(0.5, 8.0) = 2.0;
uniform float vignette_intensity : hint_range(0.0, 1.0) = 0.35;
uniform float vignette_smoothness : hint_range(0.0, 1.0) = 0.4;
uniform float aberration_amount : hint_range(0.0, 5.0) = 1.2;
uniform float flicker_speed : hint_range(0.0, 10.0) = 0.5;
uniform float flicker_amount : hint_range(0.0, 0.1) = 0.008;
uniform vec3 tint_color : source_color = vec3(0.85, 0.95, 1.0);

void fragment() {
	vec2 uv = SCREEN_UV;

	// Aberration chromatique
	vec2 aberr = (uv - 0.5) * aberration_amount * 0.001;
	float r = texture(screen_texture, uv + aberr).r;
	float g = texture(screen_texture, uv).g;
	float b = texture(screen_texture, uv - aberr).b;
	vec3 color = vec3(r, g, b);

	// Scanlines horizontales
	float screen_h = 1.0 / SCREEN_PIXEL_SIZE.y;
	float scanline = sin(uv.y * screen_h * 3.14159 * scanline_scale) * 0.5 + 0.5;
	scanline = 1.0 - scanline * scanline_opacity;
	color *= scanline;

	// Flicker subtil (scintillement CRT)
	float flicker = 1.0 - flicker_amount * sin(TIME * flicker_speed * 6.283);
	color *= flicker;

	// Vignette (bords sombres)
	vec2 vig_uv = uv * (1.0 - uv);
	float vig = vig_uv.x * vig_uv.y * 15.0;
	vig = pow(vig, vignette_smoothness);
	vig = clamp(vig, 1.0 - vignette_intensity, 1.0);
	color *= vig;

	// Teinte Tron subtile
	color *= tint_color;

	COLOR = vec4(color, 1.0);
}
