// Run Phira effect shaders outside the game, in headless Chromium's WebGL 1 (GLSL ES 1.00, validated by
// ANGLE - stricter than most phone drivers, which is the point: a shader that fails to compile makes Phira
// refuse the whole chart).
//
//   node glfx.js validate a.glsl b.glsl ...     compile each with Phira's vertex shader, exit 1 on any error
//   node glfx.js serve                          the same jobs, one JSON object per stdin line (used by jl_preview.py)
//   node glfx.js run jobs.json                  {"jobs":[{"input":png,"output":png,"passes":[{"shader":path,
//                                                 "uniforms":{name: number | [x,y] | [r,g,b,a 0..1]},"time":s}]}]}
// In Phira's effect pass uv = (0,0) is the bottom-left of the chart area and uv.y grows upwards.
const fs = require('fs');
const { chromium } = require('playwright');

const VERT = `#version 100
attribute vec3 position;
attribute vec2 texcoord;
attribute vec4 color0;

varying vec2 uv;

uniform mat4 Model;
uniform mat4 Projection;
uniform vec2 UVScale;

void main() {
    gl_Position = Projection * Model * vec4(position, 1);
    uv = (texcoord - vec2(0.5)) * UVScale + vec2(0.5);
}`;

function pageMain() {
  window.glfx = {
    init(w, h) {
      const c = document.createElement('canvas');
      c.width = w; c.height = h;
      document.body.appendChild(c);
      const gl = c.getContext('webgl', { preserveDrawingBuffer: true, premultipliedAlpha: false, antialias: false, alpha: false });
      this.c = c; this.gl = gl; this.w = w; this.h = h; this.progs = {};
      const buf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      // x, y, z, u, v
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 0, 0, 0, 1, -1, 0, 1, 0, 1, 1, 0, 1, 1, -1, -1, 0, 0, 0, 1, 1, 0, 1, 1, -1, 1, 0, 0, 1]), gl.STATIC_DRAW);
      this.buf = buf;
      this.fb = [0, 1].map(() => {
        const t = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, t);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
        for (const [k, v] of [[gl.TEXTURE_MIN_FILTER, gl.LINEAR], [gl.TEXTURE_MAG_FILTER, gl.LINEAR], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k, v);
        const f = gl.createFramebuffer();
        gl.bindFramebuffer(gl.FRAMEBUFFER, f);
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
        return { t, f };
      });
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      return !!gl;
    },
    compile(vert, frag) {
      const gl = this.gl;
      const mk = (type, src) => {
        const s = gl.createShader(type);
        gl.shaderSource(s, src);
        gl.compileShader(s);
        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
        return s;
      };
      const p = gl.createProgram();
      gl.attachShader(p, mk(gl.VERTEX_SHADER, vert));
      gl.attachShader(p, mk(gl.FRAGMENT_SHADER, frag));
      gl.bindAttribLocation(p, 0, 'position');
      gl.bindAttribLocation(p, 1, 'texcoord');
      gl.linkProgram(p);
      if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
      return p;
    },
    check(vert, frag) {
      try { this.compile(vert, frag); return null; } catch (e) { return String(e.message || e); }
    },
    async run(vert, job, shaders) {
      const gl = this.gl;
      const img = new Image();
      await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = job.inputData; });
      const tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
      for (const [k, v] of [[gl.TEXTURE_MIN_FILTER, gl.LINEAR], [gl.TEXTURE_MAG_FILTER, gl.LINEAR], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k, v);
      let src = tex;
      const passes = job.passes.length ? job.passes : [{ shader: '__copy__', uniforms: {}, time: 0 }];
      shaders.__copy__ = '#version 100\nprecision mediump float;\nvarying lowp vec2 uv;\nuniform sampler2D screenTexture;\nvoid main(){gl_FragColor=vec4(texture2D(screenTexture,uv).rgb,1.0);}';
      passes.forEach((ps, i) => {
        const fsrc = shaders[ps.shader];
        if (!this.progs[ps.shader]) this.progs[ps.shader] = this.compile(vert, fsrc);
        const p = this.progs[ps.shader];
        gl.useProgram(p);
        const last = i === passes.length - 1;
        gl.bindFramebuffer(gl.FRAMEBUFFER, last ? null : this.fb[i % 2].f);
        gl.viewport(0, 0, this.w, this.h);
        gl.bindBuffer(gl.ARRAY_BUFFER, this.buf);
        gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 20, 0);
        gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 2, gl.FLOAT, false, 20, 12);
        const I = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
        const U = (n) => gl.getUniformLocation(p, n);
        gl.uniformMatrix4fv(U('Model'), false, I);
        gl.uniformMatrix4fv(U('Projection'), false, I);
        gl.uniform2f(U('UVScale'), 1, 1);
        // defaults from the "// %value%" comments, exactly as Phira reads them
        const re = /uniform\s+(\w+)\s+(\w+);\s+\/\/\s+%([^%]+)%/g;
        let m;
        const vals = {};
        while ((m = re.exec(fsrc))) vals[m[2]] = m[3].split(',').map((x) => parseFloat(x.trim()));
        for (const [k, v] of Object.entries(ps.uniforms || {})) vals[k] = Array.isArray(v) ? v : [v];
        vals.time = [ps.time || 0];
        vals.screenSize = [this.w, this.h];
        for (const [k, v] of Object.entries(vals)) {
          const loc = U(k);
          if (!loc) continue;
          if (v.length === 1) gl.uniform1f(loc, v[0]);
          else if (v.length === 2) gl.uniform2f(loc, v[0], v[1]);
          else if (v.length === 4) gl.uniform4f(loc, v[0], v[1], v[2], v[3]);
        }
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, src);
        gl.uniform1i(U('screenTexture'), 0);
        gl.drawArrays(gl.TRIANGLES, 0, 6);
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
        src = this.fb[i % 2].t;
      });
      gl.deleteTexture(tex);
      return this.c.toDataURL('image/png');
    },
  };
}

(async () => {
  const mode = process.argv[2];
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage();
  await page.evaluate(pageMain);
  let failed = 0;
  if (mode === 'validate') {
    await page.evaluate(() => window.glfx.init(64, 36));
    for (const f of process.argv.slice(3)) {
      const src = fs.readFileSync(f, 'utf8');
      const err = await page.evaluate(([v, s]) => window.glfx.check(v, s), [VERT, src]);
      const nonAscii = /[^\x00-\x7f]/.test(src);
      if (err || nonAscii) failed++;
      console.log(`${err || nonAscii ? 'FAIL' : 'ok  '} ${f}${err ? '\n' + err : ''}${nonAscii ? '\n  non-ASCII characters in shader source' : ''}`);
    }
  } else if (mode === 'run') {
    const spec = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
    const shaders = {};
    for (const j of spec.jobs) for (const p of j.passes) if (!(p.shader in shaders)) shaders[p.shader] = fs.readFileSync(p.shader, 'utf8');
    await page.evaluate(([w, h]) => window.glfx.init(w, h), [spec.width, spec.height]);
    for (const j of spec.jobs) {
      const inputData = 'data:image/png;base64,' + fs.readFileSync(j.input).toString('base64');
      const out = await page.evaluate(([v, job, sh]) => window.glfx.run(v, job, sh), [VERT, { passes: j.passes, inputData }, shaders]);
      fs.writeFileSync(j.output, Buffer.from(out.split(',')[1], 'base64'));
    }
    console.log(`rendered ${spec.jobs.length} frame(s)`);
  } else if (mode === 'serve') {
    // one JSON job per stdin line: {"width","height","input","output","passes"}; answers "done" / "error ..."
    const rl = require('readline').createInterface({ input: process.stdin });
    const shaders = {};
    let size = '';
    for await (const line of rl) {
      if (!line.trim()) continue;
      try {
        const j = JSON.parse(line);
        if (size !== `${j.width}x${j.height}`) {
          await page.evaluate(([w, h]) => { document.body.innerHTML = ''; return window.glfx.init(w, h); }, [j.width, j.height]);
          size = `${j.width}x${j.height}`;
        }
        for (const p of j.passes) if (!(p.shader in shaders)) shaders[p.shader] = fs.readFileSync(p.shader, 'utf8');
        const inputData = 'data:image/png;base64,' + fs.readFileSync(j.input).toString('base64');
        const out = await page.evaluate(([v, job, sh]) => window.glfx.run(v, job, sh), [VERT, { passes: j.passes, inputData }, shaders]);
        fs.writeFileSync(j.output, Buffer.from(out.split(',')[1], 'base64'));
        console.log('done');
      } catch (e) {
        console.log('error ' + String(e.message || e).replace(/\n/g, ' | '));
      }
    }
  } else {
    console.error('usage: node glfx.js validate <glsl...> | run <jobs.json> | serve');
    failed = 1;
  }
  await browser.close();
  process.exit(failed ? 1 : 0);
})();
