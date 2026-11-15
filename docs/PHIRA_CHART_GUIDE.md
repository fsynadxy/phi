# 做可导入 Phira 的谱面：格式要点与避坑（给其他工作区 / 其他 Claude 会话）

目标：**一次生成就能导入、能播放**。以下全部来自本仓库做过的五张谱，规则取自 Phira 源码（prpr 的 `parse/rpe.rs`、`parse/extra.rs`、`info.rs`）和一个按它写的校验器。
**没有在真机上跑过**：下面标「已验证」的是校验器 + 预览器层面，不是真机结论。

## 0. 最快路径（照抄）

```bash
pip install numpy pillow pyyaml
cp tools/gen/example_minimal.py tools/gen/my_chart.py        # 改 make() / assets()
python tools/gen/build.py out --variant my_chart --song song.ogg --pez my.pez
python tools/gen/validate.py out                              # 必须 errors=0
RESPACK=<phira>/assets/respack python tools/gen/playcheck.py out   # 可选：可玩性检查
```

- `tools/gen/chartlib.py` 负责 JSON 细节（整数/浮点、Triple、默认值、事件不重叠），**不要手写 chart.json**。
- `example_minimal.py` 已验证：1 条线、16 个 note、1 个特效，`validate.py` 0 错误 0 警告。

## 1. 包结构（.pez = 普通 zip，文件放在压缩包根目录，不要套文件夹）

```
chart.json  info.yml  [extra.json]  song.ogg  illustration.jpg  [贴图.png]  [视频.mp4]  [自定义打击音.ogg]
```

- `info.yml` 里 `chart / music / illustration` 指向的文件必须存在；谱面里引用的每张贴图、每个视频、每个自定义 hitsound 也必须在包里（缺哪个都会加载失败）。
- 打包：json/yml 可压缩，音视频图片用 store 即可（`build.py --pez` 已这样做）。

## 2. info.yml（键名 camelCase）

必填：`name level charter composer chart music illustration`；常用：`difficulty previewStart previewEnd aspectRatio(1.7777778) backgroundDim lineLength(6.0) offset tip tags intro format: rpe`。
**务必显式写 `useRpe170Speed: false` 和 `useAttachUiFix: true`**，否则导入时会弹提示。

## 3. 音频

- **不要放 m4a / aac-in-mp4**：Phira 的解码器读不了 MP4 容器（读源码得出，未真机试）。先转：`ffmpeg -i in.m4a -vn -map_metadata -1 -c:a libvorbis -q:a 7 song.ogg`。
- OGG 无编码延迟；MP3 解码不会裁掉编码延迟，约多 25 ms，`offset` 要多加。
- `META.offset`（毫秒，**必须是整数**）= 谱面第 0 拍对应的音乐时间。分析出首拍在 0.2935 s、BPM 从第 0 拍开始 → 写 294。
- BPM 恒定就只写一项 `BPMList`（`extra.json` 里 `bpm` 也要写，必填）。

## 4. chart.json（RPE）硬规则

坐标：x ∈ ±675，y ∈ ±450，**+y 向上**；rotate 单位度，**正值顺时针**。时间一律 Triple `[整数, 分子, 分母]`，分母 > 0。

| 规则 | 违反的后果 |
|---|---|
| 每个事件数组**不能为空**（空数组会让 Phira 崩溃）；没有就别写这个 key | 崩溃 |
| **没有 alpha 事件的线完全透明**；每条要显示的线都要写 alpha | 线不显示 |
| **每条带 note 的线必须有 speed 事件，且从第 0 拍开始** | 所有 note 贴在线上 |
| 每个轨道在第 0 拍放一个关键帧（需要瞬变就用 1/96 拍的极短事件） | 首个关键帧之前会向后外推，值不对 |
| 同一轨道的事件**按时间排序且不重叠**；同一拍要跳变就用一个起止相同的极短事件 | 加载/播放错误 |
| note 的 `type above isFake` 为整数 `type`：1 tap、2 hold、3 flick、4 drag；`alpha` 为整数（u16）；`isCover` 整数 | 解析失败 |
| hold 的 `endTime` 必须大于 `startTime` | 无效 note |
| `META.offset` 整数 | 解析失败 |
| 有父线时：父线只传递位移和旋转，**不传递缩放** | 子线大小不跟随 |
| 带 `attachUI` 的线（`pause combonumber combo score bar name level`）：该 UI 跟随这条线的 alpha/位置；把 alpha 设 0 即可隐藏界面；这类线不参与绘制 | — |
| 想放纯演出谱（0 个 note）：准确率会是 0/0。放 **1 个** `alpha:0` 的 note，线挪到屏幕外，`hitsound` 指向一个**包内存在的**静音 ogg | 结算异常 |
| 纹理线：`Texture` 写文件名，文件须在包里；其 alpha 为 0 时不绘制；缩放单位 = 2/1350 世界单位每像素 | 缺文件加载失败 |
| 普通判定线 `line.png`：半长 = 3 × scaleX 世界单位（`scaleX` 被乘 0.5，`lineLength` 为 6） | 线长不对 |

## 5. extra.json（特效 / 视频）

```json
{"bpm":[{"time":[0,0,1],"bpm":160.0}],
 "effects":[{"start":[0,0,1],"end":[20,0,1],"shader":"vignette","vars":{"extend":0.2,"radius":18.0},"global":false}],
 "videos":[{"path":"clip.mp4","time":[73,0,1],"scale":"cropCenter","alpha":1.0,"dim":0.0}]}
```

- 内置 shader 与可用变量：`chromatic{sampleCount,power}` `circleBlur{size}` `fisheye{power}` `glitch{power,rate,speed,blockCount,colorRate}` `grayscale{factor}` `noise{seed,power}` `pixel{size}` `radialBlur{centerX,centerY,power,sampleCount}` `shockwave{progress,centerX,centerY,width,distortion,expand}` `vignette{color,extend,radius}`。写了不存在的变量会被校验器拦下。
- **颜色变量必须是 4 个整数 `[0..255]`**。写成 `[0.0,0.0,0.0,1.0]` 会报 “data did not match any variant of untagged enum Variable”（我们第一版就栽在这）。不需要颜色就别写。
- 变量用关键帧时，每个关键帧**必须带 `easingType`**。
- 视频：`path` 必须在包内（缺失报 video-load-failed）；`scale` 只能是 `cropCenter / inside / fit`；视频画在所有判定线下面，只在 `[time, time+时长)` 内显示；建议 H.264、yuv420p、1280×720、去掉音轨（`ffmpeg -an`）。视频功能依赖 Phira 构建带 video 特性，旧版/自编译可能没有。
- `noise` 是静态抖动，长时间开会把细线和文字磨糊；做长段特效优先用 `chromatic / shockwave / radialBlur`。
- 特效会叠加后期开销，低端机上提示用户可关特效。

## 5b. 自定义着色器（读 prpr 与 prpr-macroquad 源码得出，未真机试）

- extra.json 里写 `"shader": "/lens.glsl"`（斜杠开头 = 包内文件）。**任何一个着色器编译失败，整个 extra.json 解析失败，谱面无法加载**（`Effect::new` 的错误会一路传上去）。交付前用 `node tools/gen/glfx.js validate *.glsl` 在无头 Chromium 的 WebGL 1（ANGLE，GLSL ES 1.00，比多数手机驱动严格）里编译一遍；源码只用 ASCII。
- Phira 提供：`varying vec2 uv;`、`uniform sampler2D screenTexture;`、`uniform vec2 screenSize;`、`uniform float time;`（秒）。自定义变量在声明行末写默认值：`uniform float zoom; // %1.0%`、`uniform vec4 tint; // %0.8, 0.9, 1.0, 1.0%`（Phira 用正则读这个注释；vec4 默认值是 0..1 浮点，而 extra.json 里的颜色仍要写 4 个整数）。
- 精度：`#ifdef GL_FRAGMENT_PRECISION_HIGH` 选 highp，否则 mediump。`uv` 可以不写 `lowp`（片元与顶点着色器里的 varying 精度不必一致），写 `lowp` 在部分手机上只有 8 位，采样会成块。
- **方向：`uv = (0,0)` 是谱面左下角，y 向上**。推导：prpr-macroquad 的 Camera2D 不做渲染目标翻转；谱面以模型矩阵 (1,-1) 加相机 `zoom.y = -aspect` 画进渲染目标，特效矩形左下角顶点的纹理坐标是 (0,0)，经同样的变换落在底部，特效通道保持图像方向。
- **用多条线拼几何图形（六边形、星形、带绳子的秋千）时，在 info.yml 写 `forceAspectRatio: true`**。不写的话，在比 16:9 更窄的屏幕（iPad 等 4:3）上 Phira 会把谱面纵向拉伸：线的 y 坐标按屏幕比例放大，但线的角度和长度不变，拼好的图形会散开。写了之后窄屏上下留黑边，画面与 16:9 一致。
- 着色器里用 `uniform vec2 UVScale;` 把 uv 换算成谱面坐标：`(uv - 0.5) / UVScale + 0.5`，采样前再乘回去；谱面宽高比是 `screenSize * UVScale` 的比值（`jl_shaders/*.glsl` 开头的 `toChart / toTex / chartAspect`）。16:9 屏幕上 UVScale 为 (1,1)，结果不变。
- 非 16:9 屏幕：渲染目标是整个屏幕大小，谱面区域居中，`uv` 是整屏纹理中的坐标（`UVScale` = 谱面区域 / 屏幕），`screenSize` 是整屏大小。所以以 (0.5, 0.5) 为中心的效果最稳；用 `screenSize` 算宽高比画出的形状不会变形，但离开中心的横向位置会随屏幕宽度略有偏移。
- 每个特效是一个全屏通道。镜头类动画（推拉、滚转、色散、闪白）用**一个常驻着色器 + 关键帧变量**做，比开很多短特效省（`jl_core.Lens` 会把这些轨道烘焙成关键帧，缓动用 easingLeft/Right 截取）。
- 玩家可以在设置里关掉特效，或开 NO_SHADER 模组：画面在没有特效时也要能看。可以像 `just_love.py` 那样同时出一个只用内置着色器的 lite 包。
- 预览：`tools/gen/jl_preview.py <包目录> out.png 节拍,节拍,...`，用 glfx.js 跑真实着色器（内置着色器取自 `PHIRA_SRC` 指向的 phira 源码）。

## 6. 避坑清单（真实踩过的）

1. 颜色变量写成浮点 → 整个 extra.json 解析失败。
2. 空事件数组、缺 alpha 事件、缺 speed 事件 → 崩溃 / 线消失 / note 不下落。
3. 事件重叠或乱序（同一拍两个跳变）→ 用 `chartlib` 的 `TL.jump/to` 按时间顺序写。
4. m4a 直接当音乐 → 无法解码；转 OGG。
5. 谱面引用了贴图/视频/hitsound 但没打进包 → 加载失败。`validate.py` 会逐个检查。
6. 0 个 note → 结算 0/0。放 1 个隐藏 note。
7. note 落在屏幕外 / 隐形线上 / 太近重叠；一瞬间超过两个触点（`playcheck.py` 可查）。
8. 判定线数量别无节制：每帧可见几十条没问题，几百条常驻会卡。长演出用「线池」复用（见 `madlib.py` 的 `Engine`）。
9. 想要简洁的字体效果，直接用预渲染文字贴图（`tools/gen/dust_assets.py` 的 `render_text`），不要依赖文字线（Phira 文字线用内置 UI 字体，且字号固定）。
10. 会转动的判定线上，离中心远的 note 容易从屏幕边缘切入、只露出零点几秒。按 note 实际入场路径逐帧模拟，选择从画面内侧落下的一面（`jl_core.Notes` 的 `auto=True`）。
11. `useRpe170Speed: false` 时速度事件只按线性解读，变速请写线性缓动。
12. 鼓点瞬态要在时域上测：长窗口的谱通量会比真实起音早 20 ms 以上（`tools/analysis/jl_steps.py` 开头有做法）。

## 7. 交付前自检

- [ ] `validate.py` → `errors=0`
- [ ] 解开 .pez 再跑一遍 `validate.py`（确认文件真的在包里）
- [ ] 音频是 ogg/mp3/wav/flac，不是 m4a
- [ ] `info.yml` 写了 `useRpe170Speed` 和 `useAttachUiFix`
- [ ] 带 note 的线都有 speed；要显示的线都有 alpha；0 note 的演出谱有隐藏 note
- [ ] 想看效果：`preview.py` / `sheets.py` 渲染接触表（需 `RESPACK` 指向 Phira 的 `assets/respack`）
- [ ] 如实告诉用户「没在真机上跑过」

## 8. 公开仓库的注意

仓库是公开的：**不要提交音频、用户的封面、别人的视频素材**（`.gitignore` 已排除 `*.ogg *.mp3 *.mp4 *.pez`）。把「完整包」直接发给用户，仓库里只放不含音视频的谱面和生成器。
