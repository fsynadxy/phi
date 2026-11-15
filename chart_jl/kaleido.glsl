#version 100
// Just Love - snowflake kaleidoscope: folds the screen into mirrored sectors around a centre.
// sides = 6 turns anything on screen into a six-armed crystal.
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif

varying lowp vec2 uv;
uniform vec2 screenSize;
uniform sampler2D screenTexture;

uniform float amount; // %1.0%
uniform float sides; // %6.0%
uniform float angle; // %0.0%
uniform float source; // %90.0%
uniform float zoom; // %1.0%
uniform float centerX; // %0.5%
uniform float centerY; // %0.5%

void main() {
  float aspect = screenSize.x / screenSize.y;
  vec2 c = vec2(centerX, centerY);
  vec2 p = (uv - c) * vec2(aspect, 1.0);
  float r = length(p) / max(zoom, 0.05);
  float seg = 6.2831853 / max(sides, 1.0);
  float a = radians(angle);
  if (abs(p.x) + abs(p.y) > 0.000001) {
    a += atan(p.y, p.x);
  }
  a = mod(a, seg);
  a = abs(a - seg * 0.5);
  float b = radians(source) + a - seg * 0.25;
  vec2 q = r * vec2(cos(b), sin(b)) / vec2(aspect, 1.0) + c;
  q = abs(mod(q + vec2(1.0), 2.0) - vec2(1.0));
  vec3 k = texture2D(screenTexture, q).rgb;
  vec3 o = texture2D(screenTexture, uv).rgb;
  gl_FragColor = vec4(mix(o, k, clamp(amount, 0.0, 1.0)), 1.0);
}
