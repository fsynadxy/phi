#version 100
// Just Love - "lens": one always-on pass that carries the camera (zoom / roll / shift), a radial
// colour split, saturation, an impact-frame invert, a colour wash and a frosted edge.
// Everything is driven by keyframed uniforms, so the whole song needs a single program.
precision highp float;

varying lowp vec2 uv;
uniform vec2 screenSize;
uniform sampler2D screenTexture;

uniform float zoom; // %1.0%
uniform float roll; // %0.0%
uniform float shiftX; // %0.0%
uniform float shiftY; // %0.0%
uniform float split; // %0.0%
uniform float sat; // %1.0%
uniform float invert; // %0.0%
uniform float wash; // %0.0%
uniform float frost; // %0.0%
uniform vec4 washColor; // %1.0, 1.0, 1.0, 1.0%
uniform vec4 frostColor; // %0.80, 0.90, 1.0, 1.0%

vec2 mirrored(vec2 p) {
  return abs(mod(p + vec2(1.0), 2.0) - vec2(1.0));
}

void main() {
  float aspect = screenSize.x / screenSize.y;
  vec2 p = (uv - vec2(0.5)) * vec2(aspect, 1.0);
  float a = radians(roll);
  float cs = cos(a);
  float sn = sin(a);
  p = vec2(p.x * cs - p.y * sn, p.x * sn + p.y * cs) / max(zoom, 0.05);
  vec2 q = p / vec2(aspect, 1.0) + vec2(0.5 - shiftX, 0.5 - shiftY);
  vec2 d = (q - vec2(0.5)) * split;
  vec3 col;
  col.g = texture2D(screenTexture, mirrored(q)).g;
  if (abs(split) > 0.00001) {
    col.r = texture2D(screenTexture, mirrored(q + d)).r;
    col.b = texture2D(screenTexture, mirrored(q - d)).b;
  } else {
    vec3 c = texture2D(screenTexture, mirrored(q)).rgb;
    col.r = c.r;
    col.b = c.b;
  }
  float luma = dot(col, vec3(0.299, 0.587, 0.114));
  col = mix(vec3(luma), col, sat);
  col = mix(col, vec3(1.0) - col, clamp(invert, 0.0, 1.0));
  vec2 e = uv * (vec2(1.0) - uv);
  float edge = 1.0 - pow(clamp(e.x * e.y * 16.0, 0.0, 1.0), 0.35);
  col = mix(col, frostColor.rgb, clamp(frost * edge * frostColor.a, 0.0, 1.0));
  col = mix(col, washColor.rgb, clamp(wash * washColor.a, 0.0, 1.0));
  gl_FragColor = vec4(col, 1.0);
}
