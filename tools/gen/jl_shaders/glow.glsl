#version 100
// Just Love - soft bloom: bright areas bleed into their surroundings (13 taps on two rings).
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif

varying lowp vec2 uv;
uniform vec2 screenSize;
uniform sampler2D screenTexture;

uniform float strength; // %0.6%
uniform float radius; // %0.012%
uniform float threshold; // %0.55%

vec3 bright(vec2 q) {
  vec3 c = texture2D(screenTexture, clamp(q, vec2(0.0), vec2(1.0))).rgb;
  return max(c - vec3(threshold), vec3(0.0));
}

void main() {
  float aspect = screenSize.x / screenSize.y;
  vec2 r1 = vec2(radius / aspect, radius);
  vec2 r2 = r1 * 2.2;
  vec3 col = texture2D(screenTexture, uv).rgb;
  vec3 acc = bright(uv) * 0.16;
  acc += (bright(uv + r1 * vec2(1.0, 0.0)) + bright(uv + r1 * vec2(-1.0, 0.0)) + bright(uv + r1 * vec2(0.0, 1.0)) + bright(uv + r1 * vec2(0.0, -1.0))) * 0.12;
  acc += (bright(uv + r2 * vec2(0.7071, 0.7071)) + bright(uv + r2 * vec2(-0.7071, 0.7071)) + bright(uv + r2 * vec2(0.7071, -0.7071)) + bright(uv + r2 * vec2(-0.7071, -0.7071))) * 0.06;
  acc += (bright(uv + r2 * vec2(1.0, 0.0)) + bright(uv + r2 * vec2(-1.0, 0.0)) + bright(uv + r2 * vec2(0.0, 1.0)) + bright(uv + r2 * vec2(0.0, -1.0))) * 0.03;
  col = col + acc * strength / max(1.0 - threshold, 0.05);
  gl_FragColor = vec4(col, 1.0);
}
