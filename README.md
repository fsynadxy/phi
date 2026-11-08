# 星轨 · Phira 观赏谱

为你提供的歌曲制作的 Phira 观赏谱（RPE 格式），以「夜空与星轨」为主题，按歌曲本身的结构编排成十二个乐章。

- 时长 5:47，BPM 123（全曲恒定，按节拍网格对齐），1238 个物量，137 条判定线，25 段着色器特效
- 难度标为 `SP Lv.?`，建议开启 Autoplay 观看

![storyboard](preview/storyboard.jpg)

<sub>上图由仓库内的预览器按 Phira 的渲染规则绘制，仅作示意，与游戏内画面会有细微差别。</sub>

## 导入

这个仓库是公开的，所以**仓库里没有放音频**。可直接导入的完整包 `orbit_showcase.pez`（含音乐）已在对话中单独发给你，在 Phira 中选择「导入谱面」即可。

如需自己打包：把你的 mp3 和 `chart/` 目录里的全部文件一起压缩成 zip（文件位于压缩包根目录，mp3 命名为 `song.mp3`），后缀改为 `.pez`；或运行：

```bash
pip install numpy pillow pyyaml
python tools/gen/build.py out --song 你的歌曲.mp3 --pez orbit_showcase.pez
```

## 十二乐章

| 乐章 | 开始 | 画面 |
|---|---|---|
| I 序 Prelude | 0:01 | 一点微光落下第一个音符，化作判定线；星辰闪烁，月环缓缓升起，第二条线在上方应答 |
| II 升 Ascent | 0:54 | 线沉到底部再一路上升，光束上涌、暗角收紧、音符加速，旋转一周后静止一拍 |
| III 绽 Bloom | 1:08 | 闪白与冲击波，六片花瓣绕发光的核心旋转，音符从中心向外绽放 |
| IV 息 Breath | 1:25 | 暖色单线缓慢转动，长条落在和弦上 |
| V 律 Pulse | 1:33 | 随鼓点跳动的双线，背后是由歌曲真实频谱驱动的均衡器 |
| VI 回响 Echo | 2:28 | 摆动的钟摆线与残影，重拍音符带拖尾 |
| VII 环 Orbit | 2:59 | 时针、分针、逐拍跳动的秒针；行星沿轨道运行 |
| VIII 幻 Mirage | 3:46 | 隐形判定线与汇聚的音符、线的翻转、只在近处显形的音符，伴随故障特效 |
| IX 极 Zenith | 4:25 | 六臂星芒旋转变色，鱼眼脉冲 |
| X 忆 Memory | 4:56 | 在灰阶中重演「升」，色彩在最后一拍回来 |
| XI 终 Finale | 5:12 | 八瓣花、均衡器与底线同时出现，全曲最密集的段落 |
| XII 尾声 Coda | 5:29 | 回到一条线、一个光点，月环重现，fin. |

## 说明

- **时间对齐**：谱面偏移为 354 ms，其中约 25 ms 用于抵消 Phira 解码 MP3 时多出的编码延迟。若在你的设备上感觉整体偏早或偏晚，可在 Phira 的谱面信息里微调「偏移」。
- **曲名**：上传时文件名丢失了，曲名和曲师暂写为「未命名曲目 / 未知」，导入后可在 Phira 中编辑。
- **兼容性**：用到了 RPE 扩展事件（文字、颜色、缩放）、父子判定线、posControl / alphaControl，以及 Phira 内置着色器（shockwave、radialBlur、chromatic、vignette、grayscale、fisheye、noise、glitch）。建议使用较新版本的 Phira；设备性能较弱时可在设置中关闭特效。
- **验证方式**：谱面按 Phira 源码（prpr）中的解析结构逐字段校验，并用按其渲染规则编写的预览器逐段检查了画面与音符可读性；没有在真实的 Phira 客户端中运行过。

## 目录

- `chart/`：谱面包内容（不含音频）
- `tools/gen/showcase.py`：全部编排（每个乐章一个函数）；`chartlib.py` 为 RPE 写入库，`validate.py` 为校验器，`preview.py` 为预览器（需设置 `RESPACK` 为 Phira 的 `assets/respack`）
- `tools/data/`：对歌曲的节拍、起音与频谱分析结果；`tools/analysis/` 为生成这些数据的脚本（需 librosa）
