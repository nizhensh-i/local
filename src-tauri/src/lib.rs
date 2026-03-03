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
      let message = format!("未找到后端可执行文件 app.exe，已检查: {checked}");
      message
    })?;

  let mut command = Command::new(&exe_path);

  if let Ok(app_data_dir) = app.path().app_data_dir() {
    let config_path = app_data_dir.join("video_folder.json");
    command.env("LOCAL_V_CONFIG_PATH", config_path);
  }

  let child = command
    .spawn()
    .map_err(|error| {
      let message = format!("启动后端失败 {}: {}", exe_path.display(), error);
      message
    })?;

  log::info!("后端已启动: {}", exe_path.display());
  Ok(child)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_fs::init())
    .setup(|app| {
      match start_backend(app.handle()) {
        Ok(child) => {
          app.manage(BackendState(Mutex::new(Some(child))));
        }
        Err(message) => {
          log::error!("backend start error: {}", message);
          // emit a JS event so front‑end can display a nice message instead of
          // relying on native dialogs. the window will exist at this point.
          if let Some(win) = app.get_window("main") {
            let _ = win.emit("backend-error", message.clone());
          }
          // continue without a backend; the front-end will show an alert
          // and API calls will simply fail.
        }
      }

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
          let mut guard = match state.0.lock() {
            Ok(guard) => guard,
            Err(_) => return,
          };
          if let Some(mut child) = guard.take() {
            let _ = child.kill();
          }
        }
      }
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
