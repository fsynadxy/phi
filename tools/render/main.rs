//! Headless offline renderer for a Phira chart (autoplay), after TeamFlos/phira-render's render.rs.
//! Env: WEM_CHART (.pez or folder), WEM_ASSETS (phira assets dir), WEM_OUT (video, no audio),
//! WEM_W, WEM_H, WEM_FPS, WEM_MSAA, WEM_TAIL (seconds of result screen), WEM_MAXSEC (debug limit),
//! WEM_CRF, WEM_PRESET. Writes <WEM_OUT>.json with music / ending start times and note times for the mixer.
use anyhow::{Context, Result};
use macroquad::{miniquad::gl::GLuint, prelude::*};
use prpr::{
    config::{Config, Mods},
    core::{internal_id, MSRenderTarget, NoteKind},
    fs,
    scene::{BasicPlayer, GameMode, GameScene, LoadingScene},
    time::TimeManager,
    ui::{FontArc, TextPainter},
    Main,
};
use std::{
    cell::RefCell,
    io::Write,
    ops::DerefMut,
    path::PathBuf,
    process::{Command, Stdio},
    rc::Rc,
    sync::atomic::{AtomicBool, Ordering},
    time::Instant,
};

fn conf() -> Conf {
    Conf { window_title: "wem-render".to_string(), window_width: 640, window_height: 360, headless: true, ..Default::default() }
}

fn env<T: std::str::FromStr>(k: &str, d: T) -> T {
    std::env::var(k).ok().and_then(|v| v.parse().ok()).unwrap_or(d)
}

#[macroquad::main(conf)]
async fn main() {
    let rt = tokio::runtime::Builder::new_multi_thread().worker_threads(2).enable_all().build().unwrap();
    let _guard = rt.enter();
    if let Err(e) = run().await {
        eprintln!("{e:?}");
        std::process::exit(1);
    }
    std::process::exit(0);
}

async fn run() -> Result<()> {
    let chart_path = PathBuf::from(std::env::var("WEM_CHART")?);
    set_pc_assets_folder(&std::env::var("WEM_ASSETS")?);
    let out = std::env::var("WEM_OUT")?;
    let (vw, vh): (u32, u32) = (env("WEM_W", 1920), env("WEM_H", 1080));
    let fps: u32 = env("WEM_FPS", 60);
    let msaa: u32 = env("WEM_MSAA", 4);
    let tail: f64 = env("WEM_TAIL", 6.0);
    let maxsec: f64 = env("WEM_MAXSEC", 1e9);

    let mut fs = fs::fs_from_file(&chart_path)?;
    let info = fs::load_info(fs.deref_mut()).await?;
    let font = FontArc::try_from_vec(load_file("font.ttf").await?)?;
    let mut painter = TextPainter::new(font, None);

    let (chart, ..) = GameScene::load_chart(fs.deref_mut(), &info).await.context("load chart")?;
    let notes: Vec<(f64, u8)> = chart
        .lines
        .iter()
        .flat_map(|it| it.notes.iter())
        .filter(|it| !it.fake)
        .map(|n| (n.time, match n.kind { NoteKind::Click | NoteKind::Hold { .. } => 0, NoteKind::Drag => 1, NoteKind::Flick => 2 }))
        .collect();
    let chart_offset = chart.offset;
    drop(chart);

    let mut config = Config::default();
    config.sample_count = msaa;
    config.preferred_sample_rate = Some(48000);
    config.player_name = "Autoplay".to_owned();
    config.mods = Mods::AUTOPLAY;
    config.volume_music = 0.0;
    config.volume_sfx = 0.0;
    config.particle = true;

    let mst = Rc::new(MSRenderTarget::new((vw, vh), msaa));
    let my_time: Rc<RefCell<f64>> = Rc::new(RefCell::new(0.));
    let tm = TimeManager::manual(Box::new({
        let my_time = Rc::clone(&my_time);
        move || *(*my_time).borrow()
    }));
    static MSAA: AtomicBool = AtomicBool::new(false);
    let player = BasicPlayer { avatar: None, id: 0, rks: 0., historic_best: 0 };
    let mut main = Main::new(
        Box::new(LoadingScene::new(GameMode::Normal, info.clone(), config, fs, Some(player), None, None, None, None).await?),
        tm,
        {
            let mut cnt = 0;
            let mst = Rc::clone(&mst);
            move || {
                cnt += 1;
                if cnt == 1 || cnt == 3 {
                    MSAA.store(true, Ordering::SeqCst);
                    Some(mst.input())
                } else {
                    MSAA.store(false, Ordering::SeqCst);
                    Some(mst.output())
                }
            }
        },
    )
    .await?;
    main.top_level = false;
    main.viewport = Some((0, 0, vw as _, vh as _));

    let crf = std::env::var("WEM_CRF").unwrap_or_else(|_| "10".to_owned());
    let preset = std::env::var("WEM_PRESET").unwrap_or_else(|_| "veryfast".to_owned());
    let mut proc = Command::new("ffmpeg")
        .args(["-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", &format!("{vw}x{vh}"), "-r", &fps.to_string(), "-i", "-"])
        .args(["-vf", "vflip", "-c:v", "libx264", "-preset", &preset, "-crf", &crf, "-pix_fmt", "yuv420p", &out])
        .stdin(Stdio::piped())
        .spawn()
        .context("run ffmpeg")?;
    let mut input = proc.stdin.take().unwrap();
    let byte_size = vw as usize * vh as usize * 4;

    let mut gl = unsafe { get_internal_gl() };
    const N: usize = 3;
    let mut pbos: [GLuint; N] = [0; N];
    unsafe {
        use miniquad::gl::*;
        glGenBuffers(N as _, pbos.as_mut_ptr());
        for pbo in pbos {
            glBindBuffer(GL_PIXEL_PACK_BUFFER, pbo);
            glBufferData(GL_PIXEL_PACK_BUFFER, (vw as u64 * vh as u64 * 4) as _, std::ptr::null(), GL_STREAM_READ);
        }
        glBindBuffer(GL_PIXEL_PACK_BUFFER, 0);
    }

    let start = Instant::now();
    let mut frame: u64 = 0;
    let mut written: u64 = 0;
    let mut end_time = f64::INFINITY;
    loop {
        let t = (frame as f64 + 0.5) / fps as f64;
        let ending = f64::from_bits(prpr::WEM_ENDING_START.load(Ordering::SeqCst));
        if prpr::WEM_ENDING_START.load(Ordering::SeqCst) != u64::MAX && end_time.is_infinite() {
            end_time = ending + tail;
        }
        if t > end_time || t > maxsec {
            break;
        }
        *my_time.borrow_mut() = t;
        gl.quad_gl.render_pass(Some(mst.output().render_pass));
        clear_background(BLACK);
        main.viewport = Some((0, 0, vw as _, vh as _));
        main.update()?;
        main.render(&mut painter)?;
        draw_rectangle(0., 0., 0., 0., Color::default());
        gl.flush();
        if MSAA.load(Ordering::SeqCst) {
            mst.blit();
        }
        unsafe {
            use miniquad::gl::*;
            let tex = mst.output().texture.raw_miniquad_texture_handle();
            glBindFramebuffer(GL_READ_FRAMEBUFFER, internal_id(mst.output()));
            glBindBuffer(GL_PIXEL_PACK_BUFFER, pbos[frame as usize % N]);
            glReadPixels(0, 0, tex.width as _, tex.height as _, GL_RGBA, GL_UNSIGNED_BYTE, std::ptr::null_mut());
            glBindBuffer(GL_PIXEL_PACK_BUFFER, pbos[(frame + 1) as usize % N]);
            let src = glMapBuffer(GL_PIXEL_PACK_BUFFER, 0x88B8);
            if !src.is_null() {
                if frame >= (N as u64 - 1) {
                    input.write_all(std::slice::from_raw_parts(src as *const u8, byte_size))?;
                    written += 1;
                }
                glUnmapBuffer(GL_PIXEL_PACK_BUFFER);
            }
        }
        frame += 1;
        if frame % 600 == 0 {
            let el = start.elapsed().as_secs_f64();
            eprintln!("frame {frame} (t={t:.1}s) {:.1} fps", frame as f64 / el);
        }
    }
    drop(input);
    proc.wait()?;
    let music_start = f64::from_bits(prpr::WEM_MUSIC_START.load(Ordering::SeqCst));
    let ending_start = f64::from_bits(prpr::WEM_ENDING_START.load(Ordering::SeqCst));
    let meta = serde_json::json!({
        "fps": fps, "frames_rendered": frame, "frames_written": written, "pbo_lag": N - 1,
        "music_start": music_start, "ending_start": ending_start, "chart_offset": chart_offset,
        "notes": notes, "elapsed": start.elapsed().as_secs_f64(),
    });
    std::fs::write(format!("{out}.json"), serde_json::to_string(&meta)?)?;
    eprintln!("done: {frame} frames in {:.1}s", start.elapsed().as_secs_f64());
    Ok(())
}
