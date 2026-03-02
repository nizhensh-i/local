use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::Manager;

struct BackendState(Mutex<Option<Child>>);

fn backend_candidates(app: &tauri::AppHandle) -> Vec<PathBuf> {
  let mut candidates: Vec<PathBuf> = Vec::new();

  if cfg!(debug_assertions) {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    candidates.push(manifest_dir.join("resources").join("app.exe"));
  }

  if let Ok(resource_dir) = app.path().resource_dir() {
    candidates.push(resource_dir.join("app.exe"));
    candidates.push(resource_dir.join("resources").join("app.exe"));
  }

  candidates
}

fn start_backend(app: &tauri::AppHandle) -> Result<Child, String> {
  let candidates = backend_candidates(app);
  let exe_path = candidates
    .iter()
    .find(|path| path.exists())
    .cloned()
    .ok_or_else(|| {
      let checked = candidates
        .iter()
        .map(|path| path.display().to_string())
        .collect::<Vec<String>>()
        .join(", ");
      format!("未找到后端可执行文件 app.exe，已检查: {checked}")
    })?;

  let child = Command::new(&exe_path)
    .spawn()
    .map_err(|error| format!("启动后端失败 {}: {}", exe_path.display(), error))?;

  log::info!("后端已启动: {}", exe_path.display());
  Ok(child)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .setup(|app| {
      let child = start_backend(app.handle()).map_err(|message| {
        Box::<dyn std::error::Error>::from(std::io::Error::new(std::io::ErrorKind::NotFound, message))
      })?;
      app.manage(BackendState(Mutex::new(Some(child))));

      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .on_window_event(|window, event| {
      if let tauri::WindowEvent::CloseRequested { .. } = event {
        let app_handle = window.app_handle();
        {
          let state = app_handle.state::<BackendState>();
          if let Ok(mut guard) = state.0.lock() {
            if let Some(mut child) = guard.take() {
              let _ = child.kill();
            }
          }
        }
      }
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
