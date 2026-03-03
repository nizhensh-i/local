use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::{Emitter, Manager};

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

  // Also check the current exe directory as a fallback
  if let Ok(current_exe) = std::env::current_exe() {
    if let Some(exe_dir) = current_exe.parent() {
      candidates.push(exe_dir.join("app.exe"));
      candidates.push(exe_dir.join("resources").join("app.exe"));
    }
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
        .join("\n  ");
      let message = format!("后端服务未找到。已检查以下位置:\n  {}\n\n请确保已运行 'npm run backend:build' 打包后端。", checked);
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
      // Try to start backend with retry logic
      let mut backend_started = false;
      let mut last_error = String::new();
      
      for attempt in 1..=3 {
        match start_backend(app.handle()) {
          Ok(child) => {
            app.manage(BackendState(Mutex::new(Some(child))));
            backend_started = true;
            log::info!("Backend started successfully on attempt {}", attempt);
            break;
          }
          Err(message) => {
            last_error = message;
            log::warn!("Backend start attempt {} failed: {}", attempt, last_error);
            if attempt < 3 {
              std::thread::sleep(std::time::Duration::from_millis(500 * attempt));
            }
          }
        }
      }
      
      if !backend_started {
        log::error!("All backend start attempts failed: {}", last_error);
        // Only emit error event if we have a window
        if let Some(win) = app.get_webview_window("main") {
          let _ = win.emit("backend-error", last_error);
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
