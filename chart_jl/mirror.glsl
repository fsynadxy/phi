#version 100
// Just Love - frozen lake: everything above the horizon is reflected below it, with slow ripples.
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif

varying lowp vec2 uv;
uniform vec2 screenSize;
uniform sampler2D screenTexture;
uniform float time;

uniform float horizon; // %0.30%
uniform float amount; // %0.6%
uniform float ripple; // %0.004%
uniform float depth; // %1.0%
uniform vec4 tint; // %0.75, 0.86, 1.0, 1.0%

void main() {
  vec3 col = texture2D(screenTexture, uv).rgb;
  if (uv.y < horizon) {
    float d = horizon - uv.y;
    float wob = sin(d * 140.0 - time * 2.2) + 0.6 * sin(d * 61.0 + time * 1.3 + uv.x * 9.0);
    vec2 q = vec2(uv.x + wob * ripple * (0.4 + d * 5.0), horizon + d * depth);
    q = abs(mod(q + vec2(1.0), 2.0) - vec2(1.0));
    vec3 refl = texture2D(screenTexture, q).rgb * tint.rgb;
    float k = amount * (1.0 - 0.75 * smoothstep(0.0, max(horizon, 0.001), d));
    col = col + refl * k * (vec3(1.0) - col * 0.6);
  }
  gl_FragColor = vec4(col, 1.0);
}
