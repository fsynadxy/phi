#version 100
// Just Love - soft bloom: bright areas bleed into their surroundings (13 taps on two rings).
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

uniform float strength; // %0.6%
uniform float radius; // %0.012%
uniform float threshold; // %0.55%

vec3 bright(vec2 q) {
  vec3 c = texture2D(screenTexture, clamp(q, toTex(vec2(0.0)), toTex(vec2(1.0)))).rgb;
  return max(c - vec3(threshold), vec3(0.0));
}

void main() {
  float aspect = chartAspect();
  vec2 r1 = vec2(radius / aspect, radius) * UVScale;
  vec2 r2 = r1 * 2.2;
  vec3 col = texture2D(screenTexture, uv).rgb;
  vec3 acc = bright(uv) * 0.16;
  acc += (bright(uv + r1 * vec2(1.0, 0.0)) + bright(uv + r1 * vec2(-1.0, 0.0)) + bright(uv + r1 * vec2(0.0, 1.0)) + bright(uv + r1 * vec2(0.0, -1.0))) * 0.12;
  acc += (bright(uv + r2 * vec2(0.7071, 0.7071)) + bright(uv + r2 * vec2(-0.7071, 0.7071)) + bright(uv + r2 * vec2(0.7071, -0.7071)) + bright(uv + r2 * vec2(-0.7071, -0.7071))) * 0.06;
  acc += (bright(uv + r2 * vec2(1.0, 0.0)) + bright(uv + r2 * vec2(-1.0, 0.0)) + bright(uv + r2 * vec2(0.0, 1.0)) + bright(uv + r2 * vec2(0.0, -1.0))) * 0.03;
  col = col + acc * strength / max(1.0 - threshold, 0.05);
  gl_FragColor = vec4(col, 1.0);
}
