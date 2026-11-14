#version 100
// Just Love - heart iris: everything outside a heart is covered (cover), with a glowing rim.
precision highp float;

varying lowp vec2 uv;
uniform vec2 screenSize;
uniform sampler2D screenTexture;

uniform float size; // %0.5%
uniform float cover; // %1.0%
uniform float feather; // %0.006%
uniform float rim; // %0.0%
uniform float centerX; // %0.5%
uniform float centerY; // %0.5%
uniform vec4 color; // %1.0, 1.0, 1.0, 1.0%
uniform vec4 rimColor; // %1.0, 0.72, 0.84, 1.0%

float dot2(vec2 v) {
  return dot(v, v);
}

// exact distance to a heart whose tip is at the origin and whose top is at y = 1 (after iq)
float sdHeart(vec2 p) {
  p.x = abs(p.x);
  if (p.y + p.x > 1.0) {
    return sqrt(dot2(p - vec2(0.25, 0.75))) - 0.35355339;
  }
  return sqrt(min(dot2(p - vec2(0.0, 1.0)), dot2(p - 0.5 * max(p.x + p.y, 0.0)))) * sign(p.x - p.y);
}

void main() {
  float aspect = screenSize.x / screenSize.y;
  vec2 p = (uv - vec2(centerX, centerY)) * vec2(aspect, 1.0);
  float s = max(size, 0.0001);
  float d = sdHeart(p / s + vec2(0.0, 0.55)) * s;
  vec3 col = texture2D(screenTexture, uv).rgb;
  float outside = smoothstep(-feather, feather, d);
  col = mix(col, color.rgb, clamp(outside * cover * color.a, 0.0, 1.0));
  float glow = exp(-abs(d) * 70.0) * rim;
  col = col + rimColor.rgb * glow * rimColor.a;
  gl_FragColor = vec4(col, 1.0);
}
