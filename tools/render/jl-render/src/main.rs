// SPDX-License-Identifier: GPL-3.0-only
// Adapted from the `render` subcommand of TeamFlos/phira-render (Apache-2.0) and linked against prpr
// (TeamFlos/phira, GPL-3.0), hence GPL-3.0. Build it as a member of a phira checkout; see render.sh.
//! Offline renderer for one Phira chart, frame by frame on a manual clock (after TeamFlos/phira-render's
//! `render` subcommand, ported to the current prpr). Video only; the audio is mixed separately.
//!
//! jl-render <assets_dir> <chart_dir> <out.mp4> <width> <height> <fps> <first_frame> <frame_count> [msaa] [crf]
//!
//! Frames before <first_frame> are simulated (update only) so the scene switches happen on exactly the
//! same frames as in a full render; rendering starts one second before <first_frame> so that particles
//! from earlier hits are in place.

use anyhow::{Context, Result};
use macroquad::prelude::*;
use prpr::{
    config::{Config, Mods},
    core::{internal_id, MSRenderTarget, BOLD_FONT, PGR_FONT},
    fs,
    info::ChartInfo,
    scene::{BasicPlayer, GameMode, LoadingScene},
    time::TimeManager,
    ui::{FontArc, TextPainter},
    Main,
};
use std::{
    cell::RefCell,
    io::Write,
    path::Path,
    process::{Command, Stdio},
    rc::Rc,
    sync::atomic::{AtomicBool, Ordering},
    time::Instant,
};

/// poll a future on this thread until it is done (tokio-backed futures must not wake macroquad's executor)
fn block<R>(fut: impl std::future::Future<Output = R>) -> R {
    let mut fut = Box::pin(fut);
    loop {
        if let Some(r) = prpr::ext::poll_future(fut.as_mut()) {
            return r;
        }
        std::thread::sleep(std::time::Duration::from_millis(1));
    }
}

fn conf() -> Conf {
    Conf { window_title: "jl-render".to_owned(), window_width: 640, window_height: 360, headless: true, ..Default::default() }
}

#[macroquad::main(conf)]
async fn main() {
    let rt = tokio::runtime::Builder::new_multi_thread().worker_threads(4).enable_all().build().unwrap();
    let _guard = rt.enter();
    if let Err(err) = run().await {
        eprintln!("{err:?}");
        std::process::exit(1);
    }
    std::process::exit(0);
}

async fn run() -> Result<()> {
    let a: Vec<String> = std::env::args().collect();
    if a.len() < 9 {
        anyhow::bail!("usage: jl-render <assets> <chart_dir> <out.mp4> <w> <h> <fps> <first_frame> <frame_count> [msaa] [crf]");
    }
    set_pc_assets_folder(&a[1]);
    let chart_dir = Path::new(&a[2]);
    let out = &a[3];
    let (vw, vh): (u32, u32) = (a[4].parse()?, a[5].parse()?);
    let fps: u64 = a[6].parse()?;
    let first: u64 = a[7].parse()?;
    let count: u64 = a[8].parse()?;
    let msaa: u32 = a.get(9).map(|s| s.parse()).transpose()?.unwrap_or(1);
    let crf: String = a.get(10).cloned().unwrap_or_else(|| "16".to_owned());

    let pgr = FontArc::try_from_vec(load_file("phigros.ttf").await?)?;
    PGR_FONT.with(move |it| *it.borrow_mut() = Some(TextPainter::new(pgr, None)));
    let bold = FontArc::try_from_vec(load_file("bold.ttf").await?)?;
    BOLD_FONT.with(move |it| *it.borrow_mut() = Some(TextPainter::new(bold, None)));
    let font = FontArc::try_from_vec(load_file("font.ttf").await?)?;
    let mut painter = TextPainter::new(font, None);

    let info: ChartInfo = serde_yaml::from_str(&std::fs::read_to_string(chart_dir.join("info.yml"))?)?;
    let chart_fs = fs::fs_from_file(chart_dir)?;
    let mut config = Config::default();
    config.mods = Mods::AUTOPLAY;
    config.sample_count = msaa;
    config.particle = true;
    config.fxaa = false;
    config.player_name = "AUTO".to_owned();
    config.preferred_sample_rate = Some(44100); // a null audio device reports an absurd maximum rate
    let player = BasicPlayer { avatar: None, id: 0, rks: 0., historic_best: 0 };

    if std::env::var("JL_DEBUG").is_ok() {
        let fs2 = fs::fs_from_file(chart_dir)?;
        let tex: prpr::ext::SafeTexture = Texture2D::from_rgba8(1, 1, &[0, 0, 0, 255]).into();
        let r = block(prpr::scene::GameScene::new(GameMode::Normal, info.clone(), config.clone(), fs2, None, tex.clone(), tex, None, None, None));
        match r {
            Ok(_) => eprintln!("DEBUG: GameScene::new ok"),
            Err(e) => eprintln!("DEBUG: GameScene::new failed: {e:?}"),
        }
        return Ok(());
    }
    let mst = Rc::new(MSRenderTarget::new((vw, vh), msaa));
    let clock: Rc<RefCell<f64>> = Rc::new(RefCell::new(0.));
    let tm = TimeManager::manual(Box::new({
        let clock = Rc::clone(&clock);
        move || *clock.borrow()
    }));
    static MSAA: AtomicBool = AtomicBool::new(false);
    let mut main = Main::new(
        Box::new(block(LoadingScene::new(GameMode::Normal, info, config, chart_fs, Some(player), None, None, None, None))?),
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

    let mut ff = Command::new("ffmpeg")
        .args(["-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", &format!("{vw}x{vh}"), "-r", &fps.to_string(), "-i", "-"])
        .args(["-vf", "vflip", "-c:v", "libx264", "-preset", "medium", "-crf", &crf, "-pix_fmt", "yuv420p", "-movflags", "+faststart", out])
        .stdin(Stdio::piped())
        .spawn()
        .context("failed to run ffmpeg")?;
    let mut sink = std::io::BufWriter::with_capacity(1 << 24, ff.stdin.take().unwrap());
    let mut buf = vec![0u8; vw as usize * vh as usize * 4];
    let mut gl = unsafe { get_internal_gl() };
    let warm = first.saturating_sub(fps); // render (and discard) one second before the first kept frame
    let started = Instant::now();
    for frame in 0..first + count {
        *clock.borrow_mut() = frame as f64 / fps as f64;
        gl.quad_gl.render_pass(Some(mst.output().render_pass));
        main.viewport = Some((0, 0, vw as _, vh as _));
        main.update()?;
        if frame < warm {
            continue;
        }
        clear_background(BLACK);
        main.render(&mut painter)?;
        draw_rectangle(0., 0., 0., 0., Color::default()); // as in phira-render: flushes the last batch
        gl.flush();
        if MSAA.load(Ordering::SeqCst) {
            mst.blit();
        }
        if frame < first {
            continue;
        }
        unsafe {
            use macroquad::miniquad::gl::*;
            glBindFramebuffer(GL_READ_FRAMEBUFFER, internal_id(mst.output()));
            glPixelStorei(0x0D05, 1); // GL_PACK_ALIGNMENT
            glReadPixels(0, 0, vw as _, vh as _, GL_RGBA, GL_UNSIGNED_BYTE, buf.as_mut_ptr() as *mut _);
        }
        sink.write_all(&buf)?;
        let done = frame + 1 - first;
        if done % 300 == 0 || done == count {
            let el = started.elapsed().as_secs_f64();
            eprintln!("frame {done}/{count}  {:.2} fps", done as f64 / el);
        }
    }
    drop(sink);
    ff.wait()?;
    Ok(())
}
