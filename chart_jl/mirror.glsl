#version 100
// Just Love - frozen lake: everything above the horizon is reflected below it, with slow ripples.
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif

varying vec2 uv;
uniform vec2 screenSize;
uniform sampler2D screenTexture;
uniform vec2 UVScale;

// Phira gives uv in the coordinates of the whole render target; when the chart is letterboxed or
// pillarboxed it covers only the middle UVScale of it. Positions are worked out in chart coordinates
// (0..1 across the chart, y up) and converted back for texture lookups.
vec2 toChart(vec2 t) {
  return (t - vec2(0.5)) / UVScale + vec2(0.5);
}

vec2 toTex(vec2 c) {
  return (c - vec2(0.5)) * UVScale + vec2(0.5);
}

float chartAspect() {
  return screenSize.x * UVScale.x / (screenSize.y * UVScale.y);
}
uniform float time;

uniform float horizon; // %0.30%
uniform float amount; // %0.6%
uniform float ripple; // %0.004%
uniform float depth; // %1.0%
uniform vec4 tint; // %0.75, 0.86, 1.0, 1.0%

void main() {
  vec3 col = texture2D(screenTexture, uv).rgb;
  vec2 c = toChart(uv);
  if (c.y < horizon) {
    float d = horizon - c.y;
    float wob = sin(d * 140.0 - time * 2.2) + 0.6 * sin(d * 61.0 + time * 1.3 + c.x * 9.0);
    vec2 q = vec2(c.x + wob * ripple * (0.4 + d * 5.0), horizon + d * depth);
    q = abs(mod(q + vec2(1.0), 2.0) - vec2(1.0));
    vec3 refl = texture2D(screenTexture, toTex(q)).rgb * tint.rgb;
    float k = amount * (1.0 - 0.75 * smoothstep(0.0, max(horizon, 0.001), d));
    col = col + refl * k * (vec3(1.0) - col * 0.6);
  }
  gl_FragColor = vec4(col, 1.0);
}
