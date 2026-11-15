#version 100
// Just Love - breaking ice: a Voronoi crack network that grows from the impact point (crack),
// then every shard slides, refracts and finally drops out (power).
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

uniform float crack; // %0.0%
uniform float power; // %0.0%
uniform float cells; // %6.0%
uniform float seed; // %0.0%
uniform float centerX; // %0.5%
uniform float centerY; // %0.5%
uniform vec4 lineColor; // %0.86, 0.94, 1.0, 1.0%
uniform vec4 voidColor; // %1.0, 1.0, 1.0, 1.0%

vec2 hash2(vec2 p) {
  vec2 k = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
  return fract(sin(k + vec2(seed)) * 43758.5453);
}

void main() {
  float aspect = chartAspect();
  vec2 cu = toChart(uv);
  vec2 sp = vec2(cu.x * aspect, cu.y);
  vec2 p = sp * cells;
  vec2 ip = floor(p);
  vec2 fp = fract(p);
  float d1 = 9.0;
  float d2 = 9.0;
  vec2 id = vec2(0.0);
  vec2 cen = vec2(0.0);
  for (int j = -1; j <= 1; j++) {
    for (int i = -1; i <= 1; i++) {
      vec2 g = vec2(float(i), float(j));
      vec2 o = hash2(ip + g);
      vec2 r = g + o - fp;
      float d = dot(r, r);
      if (d < d1) {
        d2 = d1;
        d1 = d;
        id = ip + g;
        cen = (ip + g + o) / cells;
      } else if (d < d2) {
        d2 = d;
      }
    }
  }
  float edge = sqrt(d2) - sqrt(d1);
  vec2 h = hash2(id + vec2(3.7, 9.1));
  vec2 centre = vec2(centerX * aspect, centerY);
  vec2 away = cen - centre;
  float dist = length(sp - centre);
  // the crack front travels outwards; lines behind it are visible
  float reach = crack * 2.2;
  float behind = 1.0 - smoothstep(reach - 0.18, reach, dist);
  float width = 0.030 + 0.16 * power;
  float line = (1.0 - smoothstep(0.0, width, edge)) * behind;
  // shards refract (offset lookup), slide away from the centre and spin a little
  float k = power * behind;
  float ang = (h.x - 0.5) * 1.2 * k;
  float cs = cos(ang);
  float sn = sin(ang);
  vec2 rel = sp - cen;
  rel = vec2(rel.x * cs - rel.y * sn, rel.x * sn + rel.y * cs) * (1.0 + 0.25 * k);
  vec2 src = cen + rel - away * (0.10 + 0.25 * h.y) * k - (h - vec2(0.5)) * 0.05 * k;
  vec2 q = vec2(src.x / aspect, src.y);
  q = abs(mod(q + vec2(1.0), 2.0) - vec2(1.0));
  vec3 col = texture2D(screenTexture, toTex(q)).rgb;
  // facets catch the light differently
  col *= 1.0 + (h.y - 0.5) * 0.5 * k;
  // shards drop out one after another once power passes 0.5
  float gone = smoothstep(h.x * 0.45 + 0.50, h.x * 0.45 + 0.56, power) * behind;
  col = mix(col, voidColor.rgb, gone * voidColor.a);
  col = mix(col, lineColor.rgb, clamp(line * lineColor.a * (1.0 - 0.6 * gone), 0.0, 1.0));
  gl_FragColor = vec4(col, 1.0);
}
