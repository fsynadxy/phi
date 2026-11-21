# 离线渲染谱面视频（CPU）

用 Phira 自己的引擎（prpr）离线渲染 Autoplay 视频，渲染流程参照 TeamFlos/phira-render 的 `render.rs`，去掉了 Tauri 界面，改为命令行。
在没有显卡的 Linux 容器里用 Mesa llvmpipe（CPU 软件 OpenGL）+ Xvfb 渲染，1080p60、4×MSAA 约 6–9 帧/秒。

1. 克隆 Phira（在 `c53311c` 上验证过），打补丁并放入渲染器：

```bash
git clone https://github.com/TeamFlos/phira.git && cd phira
git apply ../tools/render/prpr.patch          # 记录音乐与结算画面开始的时刻，打印加载错误
mkdir -p tools/wem-render/src
cp ../tools/render/Cargo.toml tools/wem-render/ && cp ../tools/render/main.rs tools/wem-render/src/
sudo apt-get install pkg-config libasound2-dev libwayland-dev libgl1-mesa-dev xvfb
cargo build --release -p wem-render
```

2. 准备资源目录：复制 `phira/assets`，并放一个 `font.ttf`（Phira 的界面字体不在仓库里，这里用 Noto Sans SC，SIL OFL）。
   容器没有声卡时在 `~/.asoundrc` 写一个 null 设备（`pcm.!default { type null }`），渲染器已固定请求 48 kHz。

3. 渲染无声母带，再离线混音（音乐 + 打击音 + 结算音乐），最后压制：

```bash
WEM_CHART=world_execute_me.pez WEM_ASSETS=assets WEM_OUT=master.mp4 LIBGL_ALWAYS_SOFTWARE=1 \
  xvfb-run -a -s "-screen 0 1920x1080x24" phira/target/release/wem-render
python tools/render/mix.py master.mp4.json song.ogg assets mix.wav
```

环境变量：`WEM_W/WEM_H`（默认 1920×1080）、`WEM_FPS`（60）、`WEM_MSAA`（4）、`WEM_TAIL`（结算画面秒数，6）、`WEM_MAXSEC`（调试用的时长上限）。
渲染器会写出 `<输出>.json`：音乐开始时刻、结算画面开始时刻、谱面偏移与每个 note 的时间，混音脚本据此对齐。
